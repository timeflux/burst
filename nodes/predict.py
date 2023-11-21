import numpy as np
from timeflux.core.node import Node

class Meta(Node):
    """A quick hack to remove unserializable meta data

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """
    def update(self):
        if self.i.ready():
            self.o = self.i
            self.o.meta = {}
