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


class ERP(Node):
    """Accumulate epochs and compute the event-related potentials (ERPs) from epoched data.
    Output is a DataFrame containing the ERP for each electrode.
    The size of the time series is determined by the length of epochs in the input data.

    Inputs are expected to be epoched data. Continuous data are handled but are not intended for this node.
    This node is best used after the Sample node from timeflux.epoch.

    The accumulation is triggered by the event_start_accumulation and stopped by the event_stop_accumulation. 
    These events are expected to be the same as the ones used in Accumulation node in a classification pipeline.
    
    The input epochs are stacked if they match the target_label. 
    The ERP is computed by averaging the epochs for each electrode.
    
    Attributes:
        i (Port): Continuous data input, expects DataFrame.
        i_* (Port): Epoched data input, expects DataFrame.
        i_events (Port): Event input, expects DataFrame.
        o (Port): Accumulated and processed data output, provides DataFrame.

    Args:
        meta_label (tuple): Labels for different types of meta information. Defaults to ("epoch", "context", "target").
        target_label (str): Label used to identify the target variable in the data. Defaults to "target".
        event_start_accumulation (str): Label for indicating the start of accumulation. Defaults to "accumulation_starts".
        event_stop_accumulation (str): Label for indicating the stop of accumulation. Defaults to "accumulation_stops".
        event_reset (str): Label for indicating reset event. Defaults to "reset".
        buffer_size (str): Size of the buffer. Defaults to 2 seconds.
        sliding_window (int): Size of the sliding window in number of samples. Defaults to 100.
        passthrough (bool): Whether to pass data through without any transformation. Defaults to False.
        verbose (bool): Whether to display verbose output. Defaults to False.
    """

    def __init__(
        self,
        meta_label=("epoch", "context", "target"),
        target_label="target",
        non_target_label="non_target",
        event_start_accumulation="accumulation_starts",
        event_stop_accumulation="accumulation_stops",
        event_reset="reset",
        buffer_size="2s",
        sliding_window=100,
        passthrough=False,
        verbose=False,
    ):
        self.event_start_accumulation = event_start_accumulation
        self.event_stop_accumulation = event_stop_accumulation
        self.event_reset = event_reset
        self.meta_label = meta_label
        self.target_label = target_label
        self.non_target_label = non_target_label
        self.passthrough = passthrough
        self._buffer_size = pd.Timedelta(buffer_size)
        self._sliding_window = sliding_window
        self.verbose = verbose
        self._reset()

    def _reset(self):
        self._status = IDLE
        self._X_target = None
        self._X_non_target = None
        self._y = None
        self._X_indices = np.array([], dtype=np.datetime64)
        self._X_indices_non_target = np.array([], dtype=np.datetime64)
        self._X_meta = None
        self._shape = None
        self._dimensions = None
        self._accumulation_start = None
        self._accumulation_stop = None
        self._electrodes = None

    def update(self):
        """Update the node.
        It checks for reset events, starts and stops accumulation, and accumulates data.
        After the accumulation, data are processed and sent.
        """
        # Reset
        if self.event_reset:
            matches = match_events(self.i_events, self.event_reset)
            if matches is not None:
                self.logger.debug("Reset")
                self._reset()
                self.o_events.data = make_event("reset")

        # Are we dealing with continuous data or epochs? Epochs are intended.
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
                if self.verbose:
                    self.logger.debug("Start accumulation")
        if self._accumulation_stop is None:
            matches = match_events(self.i_events, self.event_stop_accumulation)
            if matches is not None:
                self._accumulation_stop = matches.index.values[0]
                if self.verbose:
                    self.logger.debug("Stop accumulation")

        # Set the electrodes layout
        if self._electrodes is None:
            if self._dimensions == 3:
                for _, _, port in self.iterate("i_*"):
                    # Check if the port name is not i_events
                    if port != self.i_events:
                        if port.ready():
                            self._electrodes = port.data.columns.tolist()
                            break
            else:
                self.logger.warning(
                    "Non epoched data found during accumulation. Ignoring."
                )

        # Always buffer a few seconds, in case the start event is coming late
        if self._status == IDLE:
            start = (now() - self._buffer_size).to_datetime64()
            stop = max_time()
            self._accumulate(start, stop)
            # Set output streams
            self._send()

        # Accumulate
        if self._status == ACCUMULATING:
            start = self._accumulation_start
            stop = self._accumulation_stop if self._accumulation_stop else max_time()
            self._accumulate(start, stop)
            # Set output streams
            self._send()

    def _accumulate(self, start, stop):
        # Set defaults
        if self.i.ready() and self.verbose:
            self.logger.debug(f"Accumulating from {start} to {stop}")
            self.logger.debug(f"Dimensions: {self._dimensions}")
        indices_target = np.array([], dtype=np.datetime64)
        indices_non_target = np.array([], dtype=np.datetime64)
        # Accumulate epoched data
        if self._dimensions == 3:
            for _, _, port in self.iterate("i_*"):
                if port.ready():
                    index = port.data.index.values[0]
                    if index >= start and index < stop:
                        data = port.data.values
                        label = get_meta(port, self.meta_label)
                        if label is not None:
                            # Check if label is a target
                            if label == self.target_label:
                                if self._X_target is None:
                                    self._X_target = np.array([data])
                                    self._shape = self._X_target.shape[1:]
                                else:
                                    self._X_target = np.vstack((self._X_target, [data]))
                                indices_target = np.append(indices_target, index)
                                if self._y is None:
                                    self._y = np.array([label])
                                else:
                                    self._y = np.append(self._y, [label])
                            elif label == self.non_target_label:
                                if self._X_non_target is None:
                                    self._X_non_target = np.array([data])
                                else:
                                    self._X_non_target = np.vstack((self._X_non_target, [data]))
                                indices_non_target = np.append(indices_non_target, index)
        else:
            self.logger.warning("Non epoched data found during accumulation. Ignoring.")

        # Store indices_target
        if indices_target.size != 0:
            self._X_indices = np.append(self._X_indices, indices_target)
        if indices_non_target.size != 0:
            self._X_indices_non_target = np.append(self._X_indices_non_target, indices_non_target)

        # Trim
        if self._X_target is not None:
            mask = (self._X_indices >= start) & (self._X_indices < stop)
            self._X_target = self._X_target[mask]
            self._X_indices = self._X_indices[mask]
            if self._y is not None:
                self._y = self._y[mask]
        if self._X_non_target is not None:
            mask = (self._X_indices_non_target >= start) & (self._X_indices_non_target < stop)
            self._X_non_target = self._X_non_target[mask]

    def _send(self):
        """
        Processes all the data to compute the event-related potentials (ERPs) for each electrode.
        Sends the dataframe containing the ERP for each electrode on the default port.
        """
        try:
            meta = self._X_meta if self._dimensions == 2 else {"epochs": self._X_meta}
            data = self._X_target
            data_non_target = self._X_non_target

            if data is not None and data.size != 0 and data_non_target is not None and data_non_target.size != 0:
                # Compute ERP for each electrode
                self.logger.debug(f"Computing ERP for {data.shape[0]} epochs")
                erp_target = np.mean(data, axis=0)
                erp_non_target = np.mean(data_non_target, axis=0)
                erp_sliding = np.mean(data[-self._sliding_window:], axis=0)
                # Create DataFrame for ERPs with electrode labels as columns
                df_non_target = pd.DataFrame(data=erp_non_target, columns=self._electrodes)
                df = pd.DataFrame(data=erp_target, columns=self._electrodes)
                df_sliding = pd.DataFrame(data=erp_sliding, columns=self._electrodes)
                
                # Modify timestamps to match live streaming
                df.index = now() + pd.to_timedelta(df.index, unit="s")
                df_non_target.index = now() + pd.to_timedelta(df_non_target.index, unit="s")
                df_sliding.index = now() + pd.to_timedelta(df_sliding.index, unit="s")             
                
                # Update output events
                self.o.data = df
                self.o_non_target.data = df_non_target
                self.o_sliding.data = df_sliding
                self.o.meta = meta
                self.o_non_target.meta = meta
                self.o_sliding.meta = meta
        except Exception as e:
            self.logger.error(f"Error sending data: {e}")