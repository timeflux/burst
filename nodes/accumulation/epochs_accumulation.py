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
    """Accumulates epochs into a DataFrame without double samples.
    Output is a dataframe with three columns, containing the mean time series, standard deviation, and mean value.
    The size of the time series is determined by the length of epochs in the input data.

    Inputs are expected to be epoched data. Continuous data are handled but are not intended for this node.
    This node is best used after the Sample node from timeflux.epoch.

    This node accumulate data and process all the accumulated epochs to deliver the output dataframe.
    The processing consists of calculating the mean epochs (time series), standard deviation at each point, and mean value of the accumulated epochs.

    Attributes:
        i (Port): Continuous data input, expects DataFrame.
        i_* (Port): Epoched data input, expects DataFrame.
        i_events (Port): Event input, expects DataFrame.
        o (Port): Accumulated and processed data output, provides DataFrame.

    Args:
        meta_label (tuple): Tuple containing labels for epoch, context, and target.
        event_start_accumulation (str): Event marking the start of accumulation.
        event_stop_accumulation (str): Event marking the end of accumulation.
        event_reset (str): Event triggering the reset of accumulation.
        buffer_size (str): Buffer size for accumulation duration.
        passthrough (bool): Flag indicating whether to pass data through without accumulation.

    """

    def __init__(
        self,
        meta_label=("epoch", "context", "target"),
        target_label="target",
        event_start_accumulation="accumulation_starts",
        event_stop_accumulation="accumulation_stops",
        event_reset="reset",
        buffer_size="2s",
        passthrough=False,
        verbose=False,
    ):
        self.event_start_accumulation = event_start_accumulation
        self.event_stop_accumulation = event_stop_accumulation
        self.event_reset = event_reset
        self.meta_label = meta_label
        self.target_label = target_label
        self.passthrough = passthrough
        self._buffer_size = pd.Timedelta(buffer_size)
        self.verbose = verbose
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
            if self._dimensions == 2:
                if self.i.ready():
                    self._electrodes = self.i.data.columns
            elif self._dimensions == 3:
                for _, _, port in self.iterate("i_*"):
                    #Check if the port name is not i_events
                    if port != self.i_events:
                        if port.ready():
                            self._electrodes = port.data.columns.tolist()
                            break

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
        indices = np.array([], dtype=np.datetime64)
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
                                if self._X is None:
                                    self._X = np.array([data])
                                    self._shape = self._X.shape[1:]
                                else:
                                    self._X = np.vstack((self._X, [data]))
                                indices = np.append(indices, index)
                                if self._y is None:
                                    self._y = np.array([label])
                                else:
                                    self._y = np.append(self._y, [label])
        else:
            self.logger.warning("Non epoched data found during accumulation. Ignoring.")

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
        """
        Processes all the data to compute the event-related potentials (ERPs) for each electrode.
        Sends the dataframe containing the ERP for each electrode on the default port.
        """
        meta = self._X_meta if self._dimensions == 2 else {"epochs": self._X_meta}
        data = self._X

        if data is not None and data.size != 0:
            # Compute ERP for each electrode
            erp = np.mean(data, axis=0)
            # Create DataFrame for ERPs with electrode labels as columns
            df = pd.DataFrame(data=erp, columns=self._electrodes)
            
            # Modify timestamps to match live streaming
            df.index = now() + pd.to_timedelta(df.index, unit="s")

            # Update output events
            self.o.data = df
            self.o.meta = meta