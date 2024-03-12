import numpy as np
import random
import json
from scipy.stats import pearsonr
from timeflux.helpers.port import make_event
from timeflux.core.node import Node
from abc import ABC, abstractmethod

# Capture Pearson correlation warnings and throw exceptions
import warnings
warnings.filterwarnings("error", module="scipy.stats")

class AbstractAccumulation(Node):
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

    def __init__(self, codes, min_buffer_size=30, max_buffer_size=200, min_frames_pred=30, max_frames_pred=300, recovery=300):
        self.codes = [[int(bit) for bit in code] for code in codes]
        self.min_buffer_size = min_buffer_size
        self.max_buffer_size = max_buffer_size
        self._min_frames_pred = min_frames_pred
        self._max_frames_pred = max_frames_pred
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
                self.logger.debug(f"RC: {''.join(list(map(str, self._probas)))}")
                for cnt, c in enumerate(self.codes):
                    self.logger.debug(f"C{cnt}: {''.join(list(map(str, c[:len(self._probas)])))}")
                
                self.decision(timestamp)
                
    def decision(self):
        ...

    def correlation(self, x:list[int], indices:list[int]):
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
                # If one input is constant, the standard deviation will be 0, the correlation will not be computed,
                # and NaN will be returned. In this case, we force the correlation value to 0.
                correlation = 0
                pvalue = 1e-8
            else:
                correlation, pvalue = pearsonr(x, y)

            correlations.append(correlation)
            pvalues.append(pvalue)
        
        return correlations, pvalues

    def reset(self):
        self._probas = []
        self._indices = []
        self._recovery = False
        self._frames = 0

class AccumulationPrevalentTarget(AbstractAccumulation):

    def __init__(self, codes, min_buffer_size=30, max_buffer_size=200, min_frames_pred=30, max_frames_pred=300, recovery=300):
        AbstractAccumulation.__init__(self,codes, min_buffer_size, max_buffer_size, min_frames_pred, max_frames_pred, recovery)
        self._accu = []
    
    def decision(self, timestamp):
        # Compute the Pearson correlation coefficient
        correlations, indices = self.correlation(x=self._probas, indices=self._indices)

        # Make a decision
        indices = np.flip(np.argsort(correlations))
        target = int(indices[0])
        self._accu.append(target)
        self.logger.debug(f"Acculen:{self._accu}")

        if len(self._accu) > self._min_frames_pred:
            values, counts = np.unique(self._accu, return_counts = True)
            best = np.flip(np.argsort(counts))
            if counts[best[0]] > 1.1/len(code) :
                self.logger.debug(f"Candidate: {values[best[0]]}\t Ratio: {counts[best[0]]/len(code)}\tFrame: {self._frames}\tCounts: {list(zip(values, counts))}\tMinmax: {min(self._probas)}/{max(self._probas)}")      
                meta = {"timestamp": timestamp, "target": str(values[best[0]]), "frames": str(self._frames)}
                self.o.data = make_event("predict", meta, True)
                self.logger.debug(meta)
                self.reset()
                self._recovery = timestamp  
            elif len(self._accu) >= self._max_frames_pred:
                self.logger.debug(f"Default Candidate: {values[best[0]]}\t Best: {counts[best[0]]/len(code)}\tFrame: {self._frames}\tCounts: {list(zip(values, counts))}\tMinmax: {min(self._probas)}/{max(self._probas)}")
                meta = {"timestamp": timestamp, "target": str(values[best[0]]), "frames": str(self._frames)}
                self.o.data = make_event("predict", meta, True)
                self.logger.debug(meta)
                self.reset()
                self._recovery = timestamp 
            else:
                # skip for more data
                ...

    def reset(self):
        AbstractAccumulation.reset(self)
        self._accu = []

class AccumulationSteadyPred(AbstractAccumulation):

    def __init__(self, codes, min_buffer_size=30, max_buffer_size=200, min_frames_pred=30, max_frames_pred=300, recovery=300):
        AbstractAccumulation.__init__(self,codes, min_buffer_size, max_buffer_size, min_frames_pred, max_frames_pred, recovery)
        self._current_target = 0
        self._target_acc = 0
        self._preds = {c:0 for c in range(len(self.codes))}

    def decision(self, timestamp):
        # Compute the Pearson correlation coefficient
        correlations, pvalues = self.correlation(x=self._probas, indices=self._indices)

        # Make a decision
        indices = np.flip(np.argsort(correlations))
        target = int(indices[0])
        if target == self._current_target:
            self._target_acc += 1
        else:
            self._current_target = target
            self._target_acc = 1

        self._preds.update({self._current_target: self._preds[self._current_target]+1})


        if self._target_acc > self._min_frames_pred:
            self.logger.debug(f"DEBUG : {self._target_acc} {self._min_frames_pred}")
            self.logger.debug(f"Candidate: {self._current_target}\tFrame: {self._frames}\t Counts: [{','.join([str(c[0])+'=>'+str(c[1]) for c in self._preds.items()])}]")      
            meta = {"timestamp": timestamp, "target": str(self._current_target), "frames": str(self._frames)}
            self.o.data = make_event("predict", meta, True)
            self.logger.debug(meta)
            self.reset()
            self._recovery = timestamp

        elif self._frames >= self._max_frames_pred:
            max_target = max(self._preds, key=self._preds.get)
            self.logger.debug(f"Default Candidate: {max_target}\t Counts: [{','.join([str(c[0])+'=>'+str(c[1]) for c in self._preds.items()])}]")
            meta = {"timestamp": timestamp, "target": str(max_target), "frames": str(self._frames)}
            self.o.data = make_event("predict", meta, True)
            self.logger.debug(meta)
            self.reset()
            self._recovery = timestamp 
        else:
            # skip for more data
                ...

    def reset(self):
        AbstractAccumulation.reset(self)
        self._preds = {c:0 for c in range(len(self.codes))}
        self._current_target = -1
        self._target_acc = 0
