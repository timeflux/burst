import numpy as np
from timeflux.core.node import Node


class Mean(Node):
    """Rereference the incoming EEG signal using the mean of all electrodes

    Attributes:
        i (Port): EEG signal, expects DataFrame.
        o (Port): Rereferenced EEG signal, provides DataFrame
    """

    def update(self):
        if self.i.ready():
            self.o = self.i
            self.o.data = self.o.data.subtract(self.o.data.mean(axis=1), axis=0)


class Channel(Node):
    """Rereference the incoming EEG signal against a specific electrode

    Attributes:
        i (Port): EEG signal, expects DataFrame.
        o (Port): Rereferenced EEG signal, provides DataFrame
    """

    def __init__(self, channel):
        self._channel = channel

    def update(self):
        if self.i.ready():
            self.o = self.i
            self.o.data = self.o.data.subtract(self.o.data[self._channel], axis=0)
            self.o.data.drop(self._channel, axis=1, inplace=True)
