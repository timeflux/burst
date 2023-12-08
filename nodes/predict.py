import numpy as np
import random
import json
from timeflux.helpers.port import make_event
from timeflux.core.node import Node

class Accumulate(Node):
    """ Accumulation of probabilities

    This node accumulates the probabilities of single-trial classifications from a ML node.
    When enough confidence is reached for a specific class, a final prediction is made.

    Args:
        min_buffer_size (int): Minimum number of predictions to accumulate before emitting a prediction (default: 100).
        max_buffer_size (int): Maximum number of predictions to accumulate for each class (default: 200).
        recovery (int): Minumum duration in ms required between two consecutive epochs after a prediction (default: 300).

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, min_buffer_size=100, max_buffer_size=200, recovery=300):
        self.min_buffer_size = min_buffer_size
        self.max_buffer_size = max_buffer_size
        self.recovery = recovery
        self._buffer = []
        self._recovery = False

    def update(self):

        # Loop through the model events
        if self.i.ready():

            # Debug
            # self.logger.debug(self.i.data)
            # self.logger.debug(self.i.meta)

            # Get an iterator over epochs, if any
            if "epochs" in self.i.meta:
                epochs = iter(self.i.meta["epochs"])
            else:
                epochs = None

            for timestamp, row in self.i.data.iterrows():

                # Check if the model is fitted and forward the event
                if row.label == "ready":
                    self.o.data = make_event("ready", False)
                    return

                # Check probabilities
                elif row.label == "predict_proba":

                    # Use the epoch timestamp if available, otherwise use the event timestamp
                    onset = next(epochs)["epoch"]["onset"]
                    timestamp = onset.value / 1e6

                    # Ignore stale epochs
                    if self._recovery:
                        if (timestamp - self._recovery) > self.recovery:
                            self._recovery = False
                        else:
                            self._recovery = timestamp
                            continue

                    # Append to buffer
                    proba = json.loads(row["data"])["result"]
                    self._buffer.append(proba)
                    if len(self._buffer) > self.max_buffer_size:
                        self._buffer.pop(0)
                    if len(self._buffer) < self.min_buffer_size:
                        continue

                    # TODO: do something with the buffer!
                    # In this example, we simply output a random target when the minimum buffer size is reached
                    score = random.random()
                    target = random.randint(0, 4)
                    meta = {"timestamp": timestamp, "target": target, "score": score}
                    self.o.data = make_event("predict", meta, False)
                    self.logger.debug(meta)
                    self._buffer = []
                    self._recovery = timestamp
