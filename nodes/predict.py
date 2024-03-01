import numpy as np
import random
import json
from scipy.stats import pearsonr
from timeflux.helpers.port import make_event
from timeflux.core.node import Node

# Capture Pearson correlation warnings and throw exceptions
import warnings
warnings.filterwarnings("error", module="scipy.stats")

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
        pomdp_step (int): Frames to wait between POMDP updates, starting a min_buffer size (default: 6).

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
        self.pomdp_step = 6
        self._probas = []
        self._indices = []
        self._recovery = False
        self._frames = 0
        self._current_cue = None
        self._pomdp_preds = []
        self._pomdp_trues = []

    def _get_correlations(self, x=None):
        """
        Compute correlations and p_values on a given array x

        Returns
        -------
        correlations: list
            Array of correlations, with each element representing the correlation between
            x and one of the true codes

        pvalues: list
            Array of p-values between x and one of the true codes. Elements from this list
            correspond to elements in correlations 
        """
        correlations = []
        pvalues = []

        for code in self.codes:
            # Slice the codes according to current position of our x array
            y = [code[i] for i in self._indices]
            try:
                correlation, pvalue = pearsonr(x, y)
            except:
                # If one input is constant, the standard deviation will be 0, the correlation will not be computed,
                # and NaN will be returned. In this case, we force the correlation value to 0 and a very small
                # p-value.
                correlation = 0
                pvalue = 1e-8

            correlations.append(correlation)
            pvalues.append(pvalue)
        
        return correlations, pvalues

    def pomdp_accumulation(self):
        """Compute correlations, get candidate and save it for POMDP solving"""
        # POMDP works with data windows that must have the same size, so we slice _probas
        pomdp_probas = self._probas[-self.min_buffer_size:]
        correlations, pvalues = self._get_correlations(x=pomdp_probas)



    def update(self):

        # Keep track of the last cue (used for POMDP solving)
        if self.i_events.ready():
            if self.i_events.data['label'].values.any() == 'cue':
                self._current_cue = json.loads(self.i_events.data['data'].iloc[0])['target']
                 
        # Make sure we have data to work with
        if not self.i_clf.ready():
            return

        # Get an iterator over epochs, if any
        if "epochs" in self.i_clf.meta:
            epochs = iter(self.i_clf.meta["epochs"])

        # Loop through the model events
        for timestamp, row in self.i_clf.data.iterrows():

            # Check if the model is fitted and forward the event
            if row.label == "ready":
                self.o_pub.data = make_event("ready", False)
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
                correlations, pvalues = self._get_correlations(x=self._probas)

                # Compute another correlation for POMDP
                if self._frames % self.pomdp_step == 0:
                    # POMDP works with data windows that must have the same size, so we slice _probas
                    pomdp_probas = self._probas[-self.min_buffer_size:]
                    pomdp_corrs, _ = self._get_correlations(x=pomdp_probas)

                    # Save the highest correlation with the current cue
                    indices = np.flip(np.argsort(pomdp_corrs))
                    target = int(indices[0])
                    self._pomdp_preds.append(target)
                    self._pomdp_trues.append(self._current_cue)
                    self.logger.debug(f"POMDP prediction: {target}\tTrue label: {self._current_cue}" \
                                      f"\tFrame: {self._frames}")

                # Make a decision
                indices = np.flip(np.argsort(correlations))
                target = int(indices[0])
                correlation = correlations[indices[0]]
                delta = (pvalues[indices[1]] - pvalues[indices[0]]) / pvalues[indices[0]]
                self.logger.debug(f"Candidate: {target}\tCorrelation: {correlation:.4f}\tDelta: " \
                                  f"{delta:.4f}\tFrame: {self._frames}\tTrue: {self._current_cue}")
                if correlation < self.threshold:
                    continue
                if delta < self.delta:
                    continue

                # Send prediction
                meta = {"timestamp": timestamp, "target": target, "score": correlation, "frames": self._frames}
                self.o_pub.data = make_event("predict", meta, True)
                self.logger.debug(meta)
                self._frames = 0
                self._probas = []
                self._indices = []
                self._recovery = timestamp
