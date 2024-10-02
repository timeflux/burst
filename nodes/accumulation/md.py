import numpy as np
import random
import json
from scipy.stats import pearsonr
from timeflux.helpers.port import make_event
from timeflux.core.node import Node
from abc import ABC, abstractmethod
import pandas as pd
from timeflux.helpers.clock import now, min_time, max_time



from sklearn.metrics import confusion_matrix

# Capture Pearson correlation warnings and throw exceptions
import warnings

warnings.filterwarnings("error", module="scipy.stats")


class AbstractAccumulation(Node):
    """Accumulation of probabilities

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

    def __init__(
        self,
        codes,
        min_buffer_size=30,
        max_buffer_size=200,
        min_frames_pred=30,
        max_frames_pred=300,
        recovery=300,
    ):
        self.codes = [[int(bit) for bit in code] for code in codes]
        self.min_buffer_size = min_buffer_size
        self.max_buffer_size = max_buffer_size
        self._min_frames_pred = min_frames_pred
        self._max_frames_pred = max_frames_pred
        self.recovery = recovery
        self.reset()

    def update(self):

        # Make sure we have data to work with
        if not self.i_clf.ready():
            return

        # Get an iterator over epochs, if any
        if "epochs" in self.i_clf.meta:
            epochs = iter(self.i_clf.meta["epochs"])

        # Loop through the model events
        for timestamp, row in self.i_clf.data.iterrows():

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
                # Extract bin
                # proba = json.loads(row["data"])["result"]

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
                # self.logger.debug(f"RC: {''.join(list(map(str, self._probas)))}")
                # for cnt, c in enumerate(self.codes):
                #     self.logger.debug(
                #         f"C{cnt}: {''.join(list(map(str, c[:len(self._probas)])))}"
                #     )

                self.decision(timestamp)

    def decision(self, timestamp):
        ...

    def correlation(self, x: list[int], indices: list[int]):
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
            y = [code[i] for i in indices]
            if np.all((np.array(x) == 0) | (np.array(x) == 1)):
            #if np.all((np.array(x) == 0) | (np.array(x) == 1)) or np.all((np.array(y) == 0) | (np.array(y) == 1)):
                # If one input is constant, the standard deviation will be 0, the correlation will not be computed,
                # and NaN will be returned. In this case, we force the correlation value to 0.
                correlation = 0
                pvalue = 1e-8
            else:
                correlation, pvalue = pearsonr(x, y)

            correlations.append(correlation)
            pvalues.append(pvalue)
        ##self.logger.debug("Correlations:"+str(correlations))
        return correlations, pvalues

    def reset(self):
        self._probas = []
        self._indices = []
        self._recovery = False
        self._frames = 0


class AccumulationMDPred(AbstractAccumulation):
    def __init__(
        self,
        codes,
        min_buffer_size=30,
        max_buffer_size=200,
        min_frames_pred=20,
        max_frames_pred=300,
        recovery=300,
        momentum_threshold=1,
        correlation_threshold=0.0,
        momentum_floor=0.0,
    ):
        self._momentum_floor = momentum_floor
        AbstractAccumulation.__init__(
            self,
            codes,
            min_buffer_size,
            max_buffer_size,
            min_frames_pred,
            max_frames_pred,
            recovery,
        )
        self._current_target = 0
        self._target_acc = 0
        self._preds = {c: 0 for c in range(len(self.codes))}
        self._consec = np.zeros(len(self.codes))
        self._momentum = np.zeros(len(self.codes))
        self._momentum_threshold = momentum_threshold
        self._correlation_threshold = correlation_threshold
        self._tooclose_threshold = 0.05
        

    def decision(self, timestamp):
        
        # Binary + Count ones method
        x = self._probas
        x = [round(b) for b in x]

        # Convert sequences of ones leaving only the first one
        countOnes = 0
        for i in range(len(x)):
            if x[i]:
                countOnes += 1
                if countOnes >= self._numOneFrames:
                    x[i - countOnes + 2:i + 1] = [0] * (countOnes - 1)
            else:
                countOnes = 0

        correlations, pvalues = self.correlation(x=x, indices=self._indices)
        
        
        # Compute the Pearson correlation coefficient
        correlations, pvalues = self.correlation(x=self._probas, indices=self._indices)
        # Make a decision
        indices = np.flip(np.argsort(correlations))
        target = int(indices[0])

        # Accumulation: In AccumulatedSteadyPred,forcing to wait for a finite consecutive amount of predictions X might
        # nullify the informative value of receiving even X-1 consecutive predictions. With this strategy we resort to
        # this issue by defining a "momentum" function that exponentially increases with consecutive predictions.
        # Receiving a prediction of a different target will not reset the momentum, but only the consecutive predictions
        # counter to stop the exponential increase, still preserving the value carried by past coherent predictions.
        # The momentum function is M(x) = (2^(x/m))-1 defined in [0, 1] where x is the count of consecutive predictions
        # and m is the number of consecutive prediction to reach M(m) = 1 (ex: _min_frames_pred).
        # At each increase c -> c+1 of the consecutive predictions counter of a target, the momentum of a target is
        # increased by M(c) - M(c-1), until it exceeds a threshold to output the accumulated decision. At the same time,
        # the momentum is decreased by the same quantity for all the other targets.

        if target != self._current_target:
            self._consec = np.zeros(len(self.codes))

        self._current_target = target
        self._consec[target] += 1

        # Actualize Momentum
        for i in range(len(self._momentum)):

            # FRED HERE !
            ### CORRELATION THRESHOLD FOR MOMENTUM
            if i == target and correlations[indices[0]] > self._correlation_threshold:  # Momentum
                self._momentum[i] += pow(
                    2, self._consec[i] / self._min_frames_pred
                ) - pow(2, (self._consec[i] - 1) / self._min_frames_pred)
            else:  # Decay
                if self._momentum[i] >= self._momentum_floor :
                    self._momentum[i] -= pow(
                        2, self._consec[target] / self._min_frames_pred
                    ) - pow(2, (self._consec[target] - 1) / self._min_frames_pred)
                
                
        if self._momentum_accumulated is None:
            self._momentum_accumulated = np.array([self._momentum])
        else:
            self._momentum_accumulated = np.vstack([self._momentum_accumulated, np.array([self._momentum])])       
    
        # Accumulate Momentum data
        df = pd.DataFrame(np.array(self._momentum_accumulated))
        df.index = now() + pd.to_timedelta(df.index, unit='s')
        self.o_correlations.data = pd.DataFrame(df)

        self._preds.update(
            {self._current_target: self._preds[self._current_target] + 1}
        )

        if (
            self._momentum[target]
            > self._momentum_threshold 
           and self._consec[target]> self._min_frames_pred
        ):
            res_momentum = self._momentum / np.sum(self._momentum)
            res_momentum = (res_momentum[target] - res_momentum)[
                res_momentum[target] - res_momentum > 0
            ]
            if any(res_momentum <= self._tooclose_threshold):
                self._momentum = self._momentum / 2
                self.logger.debug(
                    f"Prediction uncertain: Momentum: [{', '.join([str(ind)+'=>'+str(count) for ind, count in zip(range(len(self._consec)), self._momentum)])}]\t Prob: [{', '.join([str(ind)+'=>'+str(p) for ind, p in zip(range(len(self._consec)), self._momentum/np.sum(self._momentum))])}] -- RESET"
                )

            else:
                self.logger.debug(
                    f"Candidate: {self._current_target}\tFrame: {self._frames}\t Momentum: [{', '.join([str(ind)+'=>'+str(count) for ind, count in zip(range(len(self._consec)), self._momentum)])}]\t Prob: [{', '.join([str(ind)+'=>'+str(p) for ind, p in zip(range(len(self._consec)), self._momentum/np.sum(self._momentum))])}]"
                )
                meta = {
                    "timestamp": timestamp,
                    "target": self._current_target,
                    "frames": str(self._frames),
                    "decoded": "".join(list(map(str, self._probas))),
                }
                meta = {
                    "timestamp": timestamp,
                    "target": str(self._current_target),
                    "frames": str(self._frames),
                }
                self.o.data = make_event("predict", meta, True)
                self.logger.debug(meta)
                self.reset()
                self._recovery = timestamp

        else:
            # skip for more data
            ...

    def reset(self):
        AbstractAccumulation.reset(self)
        self._current_target = -1
        self._target_acc = 0
        self._momentum = self._momentum_floor*np.ones(len(self.codes))

        self._momentum_accumulated = None
