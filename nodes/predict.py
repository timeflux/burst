import numpy as np
import random
import json
from scipy.stats import pearsonr
from timeflux.helpers.port import make_event
from timeflux.core.node import Node

class Accumulate(Node):
    """ Accumulation of probabilities

    This node accumulates the probabilities of single-trial classifications from a ML node.
    When enough confidence is reached for a specific class, a final prediction is made.

    Args:
        codes (list): The list of burst codes, one for each target.
        min_buffer_size (int): Minimum number of predictions to accumulate before emitting a prediction (default: 30).
        max_buffer_size (int): Maximum number of predictions to accumulate for each class (default: 200).
        threshold (float): Minimum value to reach according to the Pearson correlation coefficient (default: .75).
        delta (float): Minimum difference percentage to reach between the p-values of the two best candidates (default: .5).
        recovery (int): Minimum duration in ms required between two consecutive epochs after a prediction (default: 300).

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, codes, min_buffer_size=30, max_buffer_size=200, threshold=.75, delta=.5, recovery=300):
        self.codes = [[int(bit) for bit in code] for code in codes]
        self.min_buffer_size = min_buffer_size
        self.max_buffer_size = max_buffer_size
        self.recovery = recovery
        self.threshold = threshold
        self.delta = delta
        self._probas = []
        self._indices = []
        self._recovery = False
        self._frames = 0

    def update(self):

        # Make sure we have data to work with
        if not self.i.ready():
            return

        # Get an iterator over epochs, if any
        if "epochs" in self.i.meta:
            epochs = iter(self.i.meta["epochs"])

        # Loop through the model events
        for timestamp, row in self.i.data.iterrows():

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

                # Compute the Pearson correlation coefficient
                correlations = []
                pvalues = []
                x = self._probas
                for code in self.codes:
                    y = [code[i] for i in self._indices]
                    correlation, pvalue = pearsonr(x, y)
                    correlations.append(correlation)
                    pvalues.append(pvalue)

                # Make a decision
                indices = np.flip(np.argsort(correlations))
                target = int(indices[0])
                correlation = correlations[indices[0]]
                delta = (pvalues[indices[1]] - pvalues[indices[0]]) / pvalues[indices[0]]
                self.logger.debug(f"Candidate: {target}\tCorrelation: {correlation:.4f}\tDelta: {delta:.4f}\tFrame: {self._frames}")
                if correlation < self.threshold:
                    continue
                if delta < self.delta:
                    continue

                # Send prediction
                meta = {"timestamp": timestamp, "target": target, "score": correlation, "frames": self._frames}
                self.o.data = make_event("predict", meta, True)
                self.logger.debug(meta)
                self._frames = 0
                self._probas = []
                self._indices = []
                self._recovery = timestamp
