import numpy as np
import pandas as pd
from collections import deque
from timeflux.core.node import Node

class Erp(Node):
    """ Sliding ERP mean computation

    This node accumulates ERP with a buffer from epoched data.
    It keeps trace of the number of epochs and computes the mean ERP.

    Args:
        buffer_size (int): Number of epochs to accumulate in the buffer (default: 20).
        
    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, buffer_size=20):
        self.buffer_size = buffer_size
        self.reset()

    def reset(self):
        self.epoch_buffer = deque(maxlen=self.buffer_size)
        self.mean_erp = None

    def update_mean_erp(self):
        if len(self.epoch_buffer) > 0:
            concatenated_epochs = pd.concat(self.epoch_buffer)
            if isinstance(concatenated_epochs, pd.Series):
                concatenated_epochs = concatenated_epochs.to_frame().T  # Convert Series to DataFrame
            self.mean_erp = concatenated_epochs.mean(axis=0)

    def update(self):
        if not self.i.ready():
            return

        self.o = self.i

        self.epoch_buffer.append(self.o.data)
        
        self.update_mean_erp()
        
        if self.mean_erp is not None:
            # Preserve datetime index of the original data
            self.o.data = pd.DataFrame(data=self.mean_erp.values.reshape(1, -1), index=[self.o.data.index[-1]])

    def terminate(self):
        self.reset()
