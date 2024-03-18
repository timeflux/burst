from nodes.accumulation.base import AbstractAccumulation
from timeflux.helpers.port import make_event
import numpy as np

class AccumulationPrevalentTarget(AbstractAccumulation):

    def __init__(
        self,
        codes,
        min_buffer_size=30,
        max_buffer_size=200,
        min_frames_pred=30,
        max_frames_pred=300,
        recovery=300,
    ):
        AbstractAccumulation.__init__(
            self,
            codes,
            min_buffer_size,
            max_buffer_size,
            min_frames_pred,
            max_frames_pred,
            recovery,
        )
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
            values, counts = np.unique(self._accu, return_counts=True)
            best = np.flip(np.argsort(counts))
            if counts[best[0]] > 1.1 / len(self.codes):
                self.logger.debug(
                    f"Candidate: {values[best[0]]}\t Ratio: {counts[best[0]]/len(self.codes)}\tFrame: {self._frames}\tCounts: {list(zip(values, counts))}\tMinmax: {min(self._probas)}/{max(self._probas)}"
                )
                meta = {
                    "timestamp": timestamp,
                    "target": str(values[best[0]]),
                    "frames": str(self._frames),
                }
                self.o.data = make_event("predict", meta, True)
                self.logger.debug(meta)
                self.reset()
                self._recovery = timestamp
            elif len(self._accu) >= self._max_frames_pred:
                self.logger.debug(
                    f"Default Candidate: {values[best[0]]}\t Best: {counts[best[0]]/len(self.codes)}\tFrame: {self._frames}\tCounts: {list(zip(values, counts))}\tMinmax: {min(self._probas)}/{max(self._probas)}"
                )
                meta = {
                    "timestamp": timestamp,
                    "target": str(values[best[0]]),
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
        self._accu = []


class AccumulationSteadyPred(AbstractAccumulation):

    def __init__(
        self,
        codes,
        min_buffer_size=30,
        max_buffer_size=200,
        min_frames_pred=30,
        max_frames_pred=300,
        recovery=300,
    ):
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

        self._preds.update(
            {self._current_target: self._preds[self._current_target] + 1}
        )

        if self._target_acc > self._min_frames_pred:
            self.logger.debug(f"DEBUG : {self._target_acc} {self._min_frames_pred}")
            self.logger.debug(
                f"Candidate: {self._current_target}\tFrame: {self._frames}\t Counts: [{','.join([str(c[0])+'=>'+str(c[1]) for c in self._preds.items()])}]"
            )
            meta = {
                "timestamp": timestamp,
                "target": str(self._current_target),
                "frames": str(self._frames),
            }
            self.o.data = make_event("predict", meta, True)
            self.logger.debug(meta)
            self.reset()
            self._recovery = timestamp

        elif self._frames >= self._max_frames_pred:
            max_target = max(self._preds, key=self._preds.get)
            self.logger.debug(
                f"Default Candidate: {max_target}\t Counts: [{','.join([str(c[0])+'=>'+str(c[1]) for c in self._preds.items()])}]"
            )
            meta = {
                "timestamp": timestamp,
                "target": str(max_target),
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
        self._preds = {c: 0 for c in range(len(self.codes))}
        self._current_target = -1
        self._target_acc = 0

