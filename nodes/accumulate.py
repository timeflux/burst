import numpy as np
import random
import json
import sys
from importlib import import_module
from timeflux.helpers.port import make_event
from timeflux.core.node import Node


class Accumulate(Node):
    """ Accumulation of probabilities

    This node allows to select an accumulation and scoring method and to change it dynamically.
    This node is listening to the RPC input for the "accumulate" call.

    Args:
        method (str): The method name. A corresponding class must exist.
        **kwargs: Arbitrary parameters for this method.

    Attributes:
        i (Port): Default input, expects DataFrame.
        i_rpc (Port): RPC input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, method, **kwargs):

        # Initialize the accumulator with default parameters
        self.accumulator = self._load(method, kwargs)

    def _load(self, method, args):
        if "." in method:
            path = method.split(".")
            module = import_module(".".join(path[0:-1]))
            method = path[-1]
        else:
            module = sys.modules[__name__]
        return getattr(module, method)(**args)

    def update(self):

        # Update
        if self.i_rpc.ready():
            # Get the last RPC message and reinstantiate
            payload = json.loads(self.i_rpc.data.loc[self.i_rpc.data.label == "accumulate", :]["data"].values[-1])
            self.logger.debug(payload)
            self.accumulator = self._load(payload["method"], payload["args"])

        # Run
        self.accumulator.i = self.i
        self.accumulator.o.clear()
        self.accumulator.update()
        self.o = self.accumulator.o


class AccumulateAbstract(Node):
    """ Accumulation of probabilities

    This node accumulates the probabilities of single-trial classifications from a ML node.
    The `decide()` method is called on each frame until final prediction is made.
    This node is an abstract class, and should not be used as is.

    Args:
        min_buffer_size (int): Minimum number of predictions to accumulate before emitting a prediction (default: 30).
        max_buffer_size (int): Maximum number of predictions to accumulate for each class (default: 200).
        recovery (int): Minimum duration in ms required between two consecutive epochs after a prediction (default: 300).

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, min_buffer_size=30, max_buffer_size=200, recovery=300):
        self.min_buffer_size = min_buffer_size
        self.max_buffer_size = max_buffer_size
        self.recovery = recovery
        self.reset()

    def update(self):

        # Make sure we have data to work with
        if not self.i.ready():
            return

        # Get an iterator over epochs, if any
        if "epochs" in self.i.meta:
            epochs = iter(self.i.meta["epochs"])

        # Loop through the model events
        for timestamp, row in self.i.data.iterrows():

            # Reset on event
            if row.label == "reset":
                self.logger.debug("Reset")
                self.reset()

            # Check if the model is fitted and forward the event
            if row.label == "ready":
                self.o.data = make_event("ready", False)
                return

            # Check probabilities
            if row.label == "predict_proba":

                # Extract proba
                proba = json.loads(row["data"])["result"][1]

                # Extract epoch meta information
                epoch = next(epochs)
                onset = epoch["epoch"]["onset"]
                index = epoch["epoch"]["context"]["index"]
                timestamp = onset.value / 1e6

                # Ignore stale epochs
                if self._recovery:
                    if (timestamp - self._recovery) > self.recovery:
                        self._recovery = False
                    else:
                        self._recovery = timestamp
                        continue

                # Keep track of the number of iterations
                self._frames += 1

                # Append to the circular buffers
                self._probas.append(proba)
                self._indices.append(index)
                if len(self._probas) > self.max_buffer_size:
                    self._probas.pop(0)
                    self._indices.pop(0)
                if len(self._probas) < self.min_buffer_size:
                    continue

                # Compute the score and make a decision
                decision = self.decide()
                if decision == False: continue

                # Send prediction
                meta = {"timestamp": timestamp, "target": decision["target"], "score": decision["score"], "frames": self._frames}
                self.o.data = make_event("predict", meta, True)
                self.logger.debug(meta)
                self.reset()
                self._recovery = timestamp

    def reset(self):
        self._probas = []
        self._indices = []
        self._recovery = False
        self._frames = 0

    def decide(self):
        return False


class Random(AccumulateAbstract):
    """ Random decision

    This node accumulates the probabilities of single-trial classifications from a ML node.
    When the buffer size reaches `min_buffer_size`, a random target between 0 and `n_targets` is predicted.
    This node has no practical use except for demonstrating how to extend the base `AccumulateAbstract` class.

    Args:
        n_targets (int): The number of targets.
        min_buffer_size (int): Minimum number of predictions to accumulate before emitting a prediction (default: 30).
        max_buffer_size (int): Maximum number of predictions to accumulate for each class (default: 200).
        recovery (int): Minimum duration in ms required between two consecutive epochs after a prediction (default: 300).

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, n_targets, min_buffer_size=30, max_buffer_size=200, recovery=300):
        self.n_targets = n_targets
        super().__init__(min_buffer_size, max_buffer_size, recovery)

    def decide(self):
        return {"target": random.randint(0, self.n_targets - 1), "score": 42}

