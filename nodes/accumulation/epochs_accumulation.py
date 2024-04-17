import pandas as pd
import numpy as np
from timeflux.core.node import Node
from timeflux.core.exceptions import ValidationError, WorkerInterrupt
from timeflux.helpers.background import Task
from timeflux.helpers.port import make_event, match_events, get_meta
from timeflux.helpers.clock import now, min_time, max_time

# Statuses
IDLE = 0
ACCUMULATING = 1

class AccumulateEpochs(Node):
    """Accumulates epochs into a DataFrame without double samples."""

    def __init__(self,
        meta_label=("epoch", "context", "target"),
        event_start_accumulation="accumulation_starts",
        event_stop_accumulation="accumulation_stops",
        event_reset="reset",
        buffer_size="5s",
        passthrough=False,):
        self.event_start_accumulation = event_start_accumulation
        self.event_stop_accumulation = event_stop_accumulation
        self.event_reset = event_reset
        self.meta_label = meta_label
        self.passthrough = passthrough
        self._buffer_size = pd.Timedelta(buffer_size)
        self._reset()

    def _reset(self):
        self._status = IDLE
        self._X = None
        self._y = None
        self._X_indices = np.array([], dtype=np.datetime64)
        self._X_meta = None
        self._shape = None
        self._dimensions = None
        self._accumulation_start = None
        self._accumulation_stop = None
        

    def update(self):

        # Reset
        if self.event_reset:
            matches = match_events(self.i_events, self.event_reset)
            if matches is not None:
                self.logger.debug("Reset")
                self._reset()
                self.o_events.data = make_event("reset")

        # Are we dealing with continuous data or epochs?
        if self._dimensions is None:
            port_name = "i"
            if getattr(self, port_name).ready():
                self._dimensions = 2
            elif len(list(self.iterate(port_name + "_*"))) > 0:
                self._dimensions = 3
            self.logger.debug(f"Dimensions: {self._dimensions}")

        # Set the accumulation boundaries
        if self._accumulation_start is None:
            matches = match_events(self.i_events, self.event_start_accumulation)
            if matches is not None:
                self._accumulation_start = matches.index.values[0]
                self._status = ACCUMULATING
                self.logger.debug("Start accumulation")
        if self._accumulation_stop is None:
            matches = match_events(self.i_events, self.event_stop_accumulation)
            if matches is not None:
                self._accumulation_stop = matches.index.values[0]
                self.logger.debug("Stop accumulation")

        # Always buffer a few seconds, in case the start event is coming late
        if self._status == IDLE:
            start = (now() - self._buffer_size).to_datetime64()
            stop = max_time()
            self._accumulate(start, stop)
            #self.logger.debug(f"X shape after idle: {self._X.shape if self._X is not None else None}")
            # Set output streams
            self._send()
            
        # Accumulate
        if self._status == ACCUMULATING:
            start = self._accumulation_start    
            stop = self._accumulation_stop if self._accumulation_stop else max_time()
            self._accumulate(start, stop)
            #self.logger.debug(f"X shape after accumulation: {self._X.shape if self._X is not None else None}")
            # Set output streams
            self._send()
    
    def _accumulate(self, start, stop):
        # Set defaults
        if self.i.ready():
            self.logger.debug(f"Accumulating from {start} to {stop}")
            self.logger.debug(f"Dimensions: {self._dimensions}")
            self.logger.debug(f"Shape: {self.i.data.shape if self.i.data is not None else None}")
        indices = np.array([], dtype=np.datetime64)
        # Accumulate continuous data
        if self._dimensions == 2:
            if self.i.ready():
                data = self.i.data
                mask = (data.index >= start) & (data.index < stop)
                data = data[mask]
                if not data.empty:
                    if self._X is None:
                        self._X = data.values
                        self._shape = self._X.shape[1]
                        indices = data.index.values
                    else:
                        if data.shape[1] == self._shape:
                            self._X = np.vstack((self._X, data.values))
                            indices = data.index.values
                        else:
                            self.logger.warning("Invalid shape")

        # Accumulate epoched data
        if self._dimensions == 3:
            for _, _, port in self.iterate("i_*"):
                if port.ready():
                    index = port.data.index.values[0]
                    if index >= start and index < stop:
                        data = port.data.values
                        #self.logger.debug(f"Data shape: {data.shape}")
                        label = get_meta(port, self.meta_label)
                        #if self._shape and (data.shape != self._shape):
                        #    self.logger.warning("Invalid shape")
                        #    continue
                        #if self.meta_label is not None and label is None:
                        #    self.logger.debug(label)
                        #    self.logger.warning("Invalid label")
                        #    continue
                        if self._X is None:
                            self._X = np.array([data])
                            self._shape = self._X.shape[1:]
                        else:
                            self._X = np.vstack((self._X, [data]))
                        indices = np.append(indices, index)
                        if label is not None:
                            if self._y is None:
                                self._y = np.array([label])
                            else:
                                self._y = np.append(self._y, [label])

        # Store indices
        if indices.size != 0:
            self._X_indices = np.append(self._X_indices, indices)

        # Trim
        if self._X is not None:
            mask = (self._X_indices >= start) & (self._X_indices < stop)
            self._X = self._X[mask]
            self._X_indices = self._X_indices[mask]
            if self._y is not None:
                self._y = self._y[mask]
    
    def _send(self):
        meta = self._X_meta if self._dimensions == 2 else {"epochs": self._X_meta}
        data = self._X
        
        if data is not None and data.size != 0:  # Check if data is not None and not empty
            # Calculate mean value of time series
            mean_value = np.nan if np.isnan(data.mean()) else data.mean().mean() * (10 ** 9)

            # Calculate mean time series
            mean_time_series = np.zeros(data.shape[1])  # Initialize with zeros
            if not np.all(np.isnan(data.mean(axis=(0, 2)))):  # Check if mean contains NaN values
                mean_time_series = data.mean(axis=(0, 2)) / max(data.mean(axis=(0, 2)))

            # Calculate standard deviation
            std = data.std(axis=(0, 2))

            # Create DataFrame
            df = pd.DataFrame({
                "Mean_Time_Series": mean_time_series,
                "Standard_Deviation": std
            })

            # Pad mean value to match the length of mean time series
            mean_value_padded = np.repeat(mean_value, len(df))

            # Add mean value column to DataFrame
            df["Mean_Value"] = mean_value_padded

            # Update output events
            if self.o_events.ready():
                self.o.data = pd.concat([self.o_events.data, df])
            else:
                self.o.data = df
                self.o.meta = meta
            
    def _reindex(self, data, times, columns):
        if data is None:
            return
        if len(data) != len(times):
            if self.resample:
                # Resample at a specific frequency
                kwargs = {"periods": len(data)}
                if self.resample_rate is None:
                    kwargs["freq"] = pd.infer_freq(times)
                    kwargs["freq"] = pd.tseries.frequencies.to_offset(kwargs["freq"])
                else:
                    kwargs["freq"] = pd.DateOffset(seconds=1 / self.resample_rate)
                if self.resample_direction == "right":
                    kwargs["start"] = times[0]
                elif self.resample_direction == "left":
                    kwargs["end"] = times[-1]
                else:

                    def middle(a):
                        return int(np.ceil(len(a) / 2)) - 1

                    kwargs["start"] = times[middle(times)] - (
                        middle(data) * kwargs["freq"]
                    )
                times = pd.date_range(**kwargs)

            else:
                # Linearly arange between first and last
                times = pd.date_range(start=times[0], end=times[-1], periods=len(data))

        return pd.DataFrame(data, times, columns)
                
    def _clear(self):
        self._X = None
        self._y = None
        self._X_indices = np.array([], dtype=np.datetime64)
        self._X_meta = None
        self._shape = None
        self._dimensions = None
        self._accumulation_start = None
        self._accumulation_stop = None
        self._status = IDLE
        