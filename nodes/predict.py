import numpy as np
from nodes.accumulate import AccumulateAbstract
from scipy.stats import pearsonr, ConstantInputWarning

# Capture Pearson correlation warnings and throw exceptions
import warnings
warnings.filterwarnings("error", category=ConstantInputWarning)


class Pearson(AccumulateAbstract):
    """ The Pearson prediction engine

    This node accumulates the probabilities of single-trial classifications from a ML node,
    and computes the Pearson correlation for each code.
    When enough confidence is reached for a specific class, a final prediction is made.
    The decision is based on the `threshold` and `delta` parameters.

    Args:
        codes (list): The list of burst codes, one for each target.
        threshold (float): Minimum value to reach according to the Pearson correlation coefficient (default: .75).
        delta (float): Minimum difference percentage to reach between the p-values of the two best candidates (default: .5).
        min_buffer_size (int): Minimum number of predictions to accumulate before emitting a prediction (default: 30).
        max_buffer_size (int): Maximum number of predictions to accumulate for each class (default: 200).
        recovery (int): Minimum duration in ms required between two consecutive epochs after a prediction (default: 300).
        feedback (bool): Provide continuous score feedback (default: True).

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, codes, threshold=.75, delta=.5, min_buffer_size=30, max_buffer_size=200, recovery=300, feedback=True):
        super().__init__(min_buffer_size, max_buffer_size, recovery, feedback)
        self.codes = [[int(bit) for bit in code] for code in codes]
        self.threshold = threshold
        self.delta = delta

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

        # Update scores
        self._scores = correlations

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

    def scores(self):
        return self._scores


class Steady(Pearson):
    """ The Steady prediction engine

    This node accumulates the probabilities of single-trial classifications from a ML node.
    Based on the Pearson correlation method above, it uses a different decision process.

    Args:
        codes (list): The list of burst codes, one for each target.
        min_frames_pred (int): Minimum number of consecutive times the current candidate must have been detected (default: 50).
        max_frames_pred (int): Maximum number of frames after which the best performing candidate is chosen (default: 200).
        min_buffer_size (int): Minimum number of predictions to accumulate before emitting a prediction (default: 30).
        max_buffer_size (int): Maximum number of predictions to accumulate for each class (default: 200).
        recovery (int): Minimum duration in ms required between two consecutive epochs after a prediction (default: 300).
        feedback (bool): Provide continuous score feedback (default: True).

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, codes, min_frames_pred=50, max_frames_pred=200, min_buffer_size=30, max_buffer_size=200, recovery=300, feedback=True):
        self.codes = [[int(bit) for bit in code] for code in codes]
        self.min_frames_pred = min_frames_pred
        self.max_frames_pred = max_frames_pred
        AccumulateAbstract.__init__(self, min_buffer_size, max_buffer_size, recovery, feedback)

    def decide(self):

        # Compute the Pearson correlation coefficient
        correlations, pvalues = self.correlation()

        # Get the best candidate
        indices = np.flip(np.argsort(correlations))
        target = int(indices[0])

        # Update scores
        diff_corr = correlations[indices[0]] - correlations[indices[1]]
        if target == self._current_target and correlations[indices[0]] > 0.0 and diff_corr > 0.0:
            self._target_acc += 1
        else:
            self._current_target = target
            self._target_acc = 1
        self._scores[target] += 1

        # Make a decision
        if self._target_acc >= self.min_frames_pred:
            target = self._current_target
        elif self._frames >= self.max_frames_pred:
            target = int(np.argmax(self._scores))
        else:
            return False

        # Return target and score
        return {"target": target, "score": self._scores[target]}

    def reset(self):
        AccumulateAbstract.reset(self)
        self._scores = [0] * len(self.codes)
        self._current_target = -1
        self._target_acc = 0

    def scores(self):
        return self._scores


class Momentum(Pearson):
    """ The Momentum prediction engine

    In 'Steady', forcing to wait for a finite consecutive amount of predictions X might
    nullify the informative value of receiving even X-1 consecutive predictions. With this strategy we resort to
    this issue by defining a "momentum" function that exponentially increases with consecutive predictions.
    Receiving a prediction of a different target will not reset the momentum, but only the consecutive predictions
    counter to stop the exponential increase, still preserving the value carried by past coherent predictions.
    The momentum function is M(x) = (2^(x/m))-1 defined in [0, 1] where x is the count of consecutive predictions
    and m is the number of consecutive prediction to reach M(m) = 1 (ex: min_frames_pred).
    At each increase c -> c+1 of the consecutive predictions counter of a target, the momentum of a target is
    increased by M(c) - M(c-1), until it exceeds a threshold to output the accumulated decision. At the same time,
    the momentum is decreased by the same quantity for all the other targets.

    Args:
        codes (list): The list of burst codes, one for each target.
        min_frames_pred (int): Minimum number of consecutive times the current candidate must have been detected (default: 20).
        momentum_threshold (float): Minimum momentum value to reach to trigger a prediction (default: 1).
        correlation_threshold (float): Minimum correlation required to update the momementum (default: 0).
        momentum_floor (float): Initial momentum value (default: 0).
        min_buffer_size (int): Minimum number of predictions to accumulate before emitting a prediction (default: 30).
        max_buffer_size (int): Maximum number of predictions to accumulate for each class (default: 200).
        recovery (int): Minimum duration in ms required between two consecutive epochs after a prediction (default: 300).
        feedback (bool): Provide continuous score feedback (default: True).

    Attributes:
        i (Port): Default input, expects DataFrame.
        o (Port): Default output, provides DataFrame
    """

    def __init__(self, codes, min_frames_pred=20, momentum_threshold=1, correlation_threshold=0.0, momentum_floor=0.0, min_buffer_size=30, max_buffer_size=200, recovery=300, feedback=True):
        self.codes = [[int(bit) for bit in code] for code in codes]
        self.min_frames_pred = min_frames_pred
        self.momentum_threshold = momentum_threshold
        self.correlation_threshold = correlation_threshold
        self.momentum_floor = momentum_floor
        AccumulateAbstract.__init__(self, min_buffer_size, max_buffer_size, recovery, feedback)
        self._tooclose_threshold = 0.05

    def decide(self):

        # Compute the Pearson correlation coefficient
        correlations, pvalues = self.correlation()

        # Get the best candidate
        indices = np.flip(np.argsort(correlations))
        target = int(indices[0])

        # Count the number of consecutive predictions
        if target != self._current_target:
            self._consec = 0
            self._current_target = target
        self._consec += 1

        # Actualize Momentum
        for i in range(len(self._momentum)):
            if i == target and correlations[indices[0]] > self.correlation_threshold:  # Momentum
                self._momentum[i] += pow(
                    2, self._consec / self.min_frames_pred
                ) - pow(2, (self._consec - 1) / self.min_frames_pred)
            else:  # Decay
                if self._momentum[i] >= self.momentum_floor :
                    self._momentum[i] -= pow(
                        2, self._consec / self.min_frames_pred
                    ) - pow(2, (self._consec - 1) / self.min_frames_pred)

        # Make a decision
        if (self._momentum[target] > self.momentum_threshold and self._consec > self.min_frames_pred):
            res_momentum = self._momentum / np.sum(self._momentum)
            res_momentum = (res_momentum[target] - res_momentum)[res_momentum[target] - res_momentum > 0]
            if any(res_momentum <= self._tooclose_threshold):
                self._momentum = self._momentum / 2
            else:
                # Return target and score
                return {"target": target, "score": self._momentum[target]}

        return False

    def reset(self):
        AccumulateAbstract.reset(self)
        self._current_target = -1
        self._momentum = self.momentum_floor * np.ones(len(self.codes))

    def scores(self):
        return self._momentum

