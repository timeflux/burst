import numpy as np
from nodes.accumulate import AccumulateAbstract
from scipy.stats import pearsonr, ConstantInputWarning

# Capture Pearson correlation warnings and throw exceptions
import warnings
warnings.filterwarnings("error", category=ConstantInputWarning)


class Pearson(AccumulateAbstract):
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

    def correlation(self):
        """ Compute the Pearson correlation coefficient
        """
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
        return correlations, pvalues

    def decide(self):

        # Compute the Pearson correlation coefficient
        correlations, pvalues = self.correlation()

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


class Steady(Pearson):
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
        correlations, pvalues = self.correlation()

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

        if self._target_acc >= self.min_frames_pred:
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
