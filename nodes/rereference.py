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

class ElectrodeReref(Node):

    def __init__(self, electrode:int):
        self._reref_electrode = electrode

    """Rereference the incoming EEG signal using the specified electrode

    Attributes:
        i (Port): EEG signal, expects DataFrame.
        o (Port): Rereferenced EEG signal, provides DataFrame
    """

    def update(self):
        if self.i.ready():
            self.o.meta = self.i.meta
            self.o.data = self.i.data
            self.o.data = self.o.data.subtract(self.o.data[self._reref_electrode], axis=0)
            self.o.data.drop(self._reref_electrode, axis=1, inplace=True)
