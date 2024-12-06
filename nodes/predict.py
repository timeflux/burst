import numpy as np
import random
import json
import sys
from scipy.stats import pearsonr, ConstantInputWarning
from timeflux.helpers.port import make_event
from timeflux.core.node import Node

# Capture Pearson correlation warnings and throw exceptions
import warnings
warnings.filterwarnings("error", category=ConstantInputWarning)


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
        self.accumulator = getattr(sys.modules[__name__], method)(**kwargs)

    def update(self):

        # Update
        if self.i_rpc.ready():
            # Get the last RPC message and reinstantiate
            payload = json.loads(self.i_rpc.data.loc[self.i_rpc.data.label == "accumulate", :]["data"].values[-1])
            self.logger.debug(payload)
            self.accumulator = getattr(sys.modules[__name__], payload["method"])(**payload["args"])

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


class AccumulateRandom(AccumulateAbstract):
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


class AccumulatePearson(AccumulateAbstract):
    """ Accumulation of probabilities

    This node accumulates the probabilities of single-trial classifications from a ML node,
    and computes the Pearson correlation for each code.
    When enough confidence is reached for a specific class, a final prediction is made.
    The decision is based on the `threshold` and `delta` parameters.

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
        self.reset()

    def decide(self):

        # Compute the Pearson correlation coefficient
        correlations = []
        pvalues = []
        x = self._probas
        for code in self.codes:
            y = [code[i] for i in self._indices]
            try:
                correlation, pvalue = pearsonr(x, y)
            except:
                # If one input is constant, the standard deviation will be 0, the correlation will not be computed,
                # and NaN will be returned. In this case, we force the correlation value to 0.
                correlation = 0
                pvalue = 1e-8
            correlations.append(correlation)
            pvalues.append(pvalue)

        # Make a decision
        indices = np.flip(np.argsort(correlations))
        target = int(indices[0])
        correlation = correlations[indices[0]]
        delta = (pvalues[indices[1]] - pvalues[indices[0]]) / pvalues[indices[0]]
        #self.logger.debug(f"Candidate: {target}\tCorrelation: {correlation:.4f}\tDelta: {delta:.4f}\tFrame: {self._frames}")
        if correlation < self.threshold:
            return False
        if delta < self.delta:
            return False

        # Return target and score
        return {"target": target, "score": correlation}


class AccumulateSteady(AccumulateAbstract):
    """ Accumulation of probabilities

    This node accumulates the probabilities of single-trial classifications from a ML node.
    Based on the Pearson correlation method above, it uses a different decision process.

    Args:
        codes (list): The list of burst codes, one for each target.
        min_buffer_size (int): Minimum number of predictions to accumulate before emitting a prediction (default: 30).
        max_buffer_size (int): Maximum number of predictions to accumulate for each class (default: 200).
        min_frames_pred (int): Minimum number of times the current candidate must have been detected to emit a prediction (default: 50).
        max_frames_pred (int): Maximum number of frames after which the best performing candidate is chosen (default: 200).
        recovery (int): Minimum duration in ms required between two consecutive epochs after a prediction (default: 300).

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, codes, min_buffer_size=30, max_buffer_size=200, min_frames_pred=50, max_frames_pred=200, recovery=300):
        self.codes = [[int(bit) for bit in code] for code in codes]
        self.min_buffer_size = min_buffer_size
        self.max_buffer_size = max_buffer_size
        self.recovery = recovery
        self.min_frames_pred = min_frames_pred
        self.max_frames_pred = max_frames_pred
        self.reset()

    def decide(self):

        # Compute the Pearson correlation coefficient
        correlations = []
        pvalues = []
        x = self._probas
        for code in self.codes:
            y = [code[i] for i in self._indices]
            try:
                correlation, pvalue = pearsonr(x, y)
            except:
                # If one input is constant, the standard deviation will be 0, the correlation will not be computed,
                # and NaN will be returned. In this case, we force the correlation value to 0.
                correlation = 0
                pvalue = 1e-8
            correlations.append(correlation)
            pvalues.append(pvalue)

        # Make a decision
        indices = np.flip(np.argsort(correlations))
        target = int(indices[0])
        diff_corr = correlations[indices[0]] - correlations[indices[1]]
        if target == self._current_target and correlations[indices[0]] > 0.0 and diff_corr > 0.0:
            self._target_acc += 1
        else:
            self._current_target = target
            self._target_acc = 1

        self._preds.update({self._current_target: self._preds[self._current_target] + 1})

        if self._target_acc > self.min_frames_pred:
            target = self._current_target
        elif self._frames >= self.max_frames_pred:
            target = max(self._preds, key=self._preds.get)
        else:
            return False

        # Return target and score
        return {"target": target, "score": self._target_acc}

    def reset(self):
        super().reset()
        self._preds = {c:0 for c in range(len(self.codes))}
        self._current_target = -1
        self._target_acc = 0
