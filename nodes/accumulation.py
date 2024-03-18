import numpy as np
import random
import json
from scipy.stats import pearsonr
from timeflux.helpers.port import make_event
from timeflux.core.node import Node
from abc import ABC, abstractmethod

import pomdp_py
from pomdp_py import sarsop
from bci_pomdp.problem import BaseProblem
from bci_pomdp.domain import BCIObservation, BCIState
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
                self.logger.debug(f"RC: {''.join(list(map(str, self._probas)))}")
                for cnt, c in enumerate(self.codes):
                    self.logger.debug(
                        f"C{cnt}: {''.join(list(map(str, c[:len(self._probas)])))}"
                    )

                self.decision(timestamp)

    def decision(self): ...

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
            if counts[best[0]] > 1.1 / len(code):
                self.logger.debug(
                    f"Candidate: {values[best[0]]}\t Ratio: {counts[best[0]]/len(code)}\tFrame: {self._frames}\tCounts: {list(zip(values, counts))}\tMinmax: {min(self._probas)}/{max(self._probas)}"
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
                    f"Default Candidate: {values[best[0]]}\t Best: {counts[best[0]]/len(code)}\tFrame: {self._frames}\tCounts: {list(zip(values, counts))}\tMinmax: {min(self._probas)}/{max(self._probas)}"
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


class AccumulationPOMDP(AccumulationSteadyPred):
    def __init__(
        self,
        codes,
        min_buffer_size=30,
        max_buffer_size=200,
        min_frames_pred=30,
        max_frames_pred=300,
        recovery=300,
    ):
        AccumulationSteadyPred.__init__(
            self,
            codes,
            min_buffer_size,
            max_buffer_size,
            min_frames_pred,
            max_frames_pred,
            recovery,
        )

        self.pomdp_step = 6
        self.norm_value = 0.3
        self.hit_reward = 10
        self.miss_cost = -100
        self.wait_cost = -1
        self.solver_path = "/home/dcas/j.torre-tresols/gitrepos/sarsop/src/pomdpsol"
        self.problem = None
        self.policy = None
        self.finite_horizon = False
        self._pomdp_status = None
        self._current_cue = None
        self._pomdp_preds = []
        self._pomdp_trues = []
        self._init_belief = None

    def _normalize_conf_matrix(self, conf_matrix):
        """Normalize confusion matrix by mixing it with the uniform distribution [1]"""
        copy_matrix = conf_matrix.copy()
        n_class = copy_matrix.shape[0]

        regu_matrix = (
            1 - self.norm_value
        ) * copy_matrix + self.norm_value * 1 / n_class

        return regu_matrix

    def _make_conf_matrix(self):
        """Create and normalize confusion matrix"""
        raw_conf_matrix = confusion_matrix(
            self._pomdp_trues, self._pomdp_preds, normalize="true"
        )
        norm_conf_matrix = self._normalize_conf_matrix(raw_conf_matrix)

        return norm_conf_matrix

    def _get_all_states(self):
        n_targets = len(self.codes)
        all_states = [BCIState(int(target)) for target in range(n_targets)]
        all_init_states = all_states.copy()

        return all_states, all_init_states

    def _get_init_belief(self, states, init_states):
        n_init_states = len(init_states)
        init_belief = pomdp_py.Histogram(
            {
                state: 1 / n_init_states if state in init_states else 0
                for state in states
            }
        )

        return init_belief

    def _create_problem(self, conf_matrix):
        """Create problem object for the POMDP model"""
        # Create a list of all possible states, and a list of all the possible initial states
        all_states, all_init_states = self._get_all_states()
        init_true_state = random.choice(all_init_states)

        # Get initial belief (uniform across initial states)
        self._init_belief = self._get_init_belief(all_states, all_init_states)

        self.problem = BaseProblem(
            self._init_belief,
            init_true_state,
            n_targets=len(self.codes),
            conf_matrix=conf_matrix,
            hit_reward=self.hit_reward,
            miss_cost=self.miss_cost,
            wait_cost=self.wait_cost,
        )

    def _compute_policy(self):
        self.policy = sarsop(
            self.problem.agent,
            pomdpsol_path=self.solver_path,
            discount_factor=0.8,
            timeout=30,
            memory=4096,
            precision=0.001,
        )

    def decision(self, timestamp):
        # Compute another correlation for POMDP
        if self._pomdp_status and self._frames % self.pomdp_step == 0:
            # POMDP works with data windows that must have the same size, so we slice _probas
            pomdp_probas = self._probas[-self.min_buffer_size :]
            pomdp_indices = self._indices[-self.min_buffer_size :]
            pomdp_corrs, _ = self.correlation(x=pomdp_probas, indices=pomdp_indices)

            # Save the highest correlation with the current cue
            sorted_corrs = np.flip(np.argsort(pomdp_corrs))
            pomdp_target = int(sorted_corrs[0])

            if self._pomdp_status == "solved":
                # Print current belief
                cur_belief = self.problem.agent.cur_belief
                self.logger.debug(f"Current belief at frame {self._frames}:")
                self.logger.debug(cur_belief)

                # Get action and max belief when action is taken
                action = self.policy.plan(self.problem.agent)
                cur_candidate = cur_belief.mpe()
                max_b = cur_belief[cur_candidate]

                # Get observation
                observation = BCIObservation(pomdp_target)

                # Update belief
                new_belief = pomdp_py.update_histogram_belief(
                    self.problem.agent.cur_belief,
                    action,
                    observation,
                    self.problem.agent.observation_model,
                    self.problem.agent.transition_model,
                    static_transition=False,
                )
                self.problem.agent.set_belief(new_belief)

                # If the maximum duration of the trial is reached, end without action
                if self.finite_horizon and self._frames >= self._max_frames_pred:
                    self.logger.debug("Action: No Action.\t Trial maximum reached")
                    meta = {
                        "timestamp": timestamp,
                        "target": 0,
                        "Best candidate": cur_candidate.id,
                        "Score": max_b,
                        "frames": self._frames,
                    }

                # If no prediction is done, print and continue
                elif action.name == "a_wait":
                    self.logger.debug(f"Action: {action}\t Observation: {pomdp_target}")

                else:
                    meta = {
                        "timestamp": timestamp,
                        "target": action.id,
                        "score": max_b,
                        "frames": self._frames,
                    }

            else:  # self._pomdp_status == 'solving'
                self._pomdp_preds.append(pomdp_target)
                self._pomdp_trues.append(self._current_cue)
                self._pomdp_pred_n += 1

                self.logger.debug(
                    f"POMDP prediction: {pomdp_target}\tTrue label: {self._current_cue}"
                    f"\tFrame: {self._frames}\tPOMDP pred number: {self._pomdp_pred_n}"
                    f"\tUsed {len(pomdp_probas)} probas and {len(pomdp_indices)} indices"
                )

        if self._pomdp_status != "solved":  # Used before and during POMDP accumulation
            # Compute the Pearson correlation coefficient
            correlations, _ = self.correlation(x=self._probas, indices=self._indices)

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
                    f"Candidate: {self._current_target}\tFrame: {self._frames}\t "
                    f"Counts: [{','.join([str(c[0])+'=>'+str(c[1]) for c in self._preds.items()])}]"
                )
                meta = {
                    "timestamp": timestamp,
                    "target": str(self._current_target),
                    "frames": str(self._frames),
                }

            elif self._frames >= self._max_frames_pred:
                max_target = max(self._preds, key=self._preds.get)
                self.logger.debug(
                    f"Default Candidate: {max_target}\t"
                    f"Counts: [{','.join([str(c[0])+'=>'+str(c[1]) for c in self._preds.items()])}]"
                )
                meta = {
                    "timestamp": timestamp,
                    "target": str(max_target),
                    "frames": str(self._frames),
                }

        try:
            # Send prediction
            self.o.data = make_event("predict", meta, True)
            self.logger.debug(meta)
            self.reset()
            self._recovery = timestamp
        except UnboundLocalError:
            if self._pomdp_status == "solved":
                self.logger.debug(f"POMDP waiting, frame {self._frames}")
            else:
                pass

    def update(self):
        # Keep track of the last cue (used for POMDP solving)
        if self.i_events.ready():
            if self.i_events.data["label"].values.any() == "cue":
                self._current_cue = json.loads(self.i_events.data["data"].iloc[0])[
                    "target"
                ]

            # When the cued task starts, start POMDP Accumulation
            if (
                not self._pomdp_status
                and self.i_events.data["label"].values.any() == "task_begins"
            ):
                event = "POMDP start accumulation"
                self.logger.debug(event)
                self.o.data = make_event(event, False)
                self._pomdp_status = "solving"

            # When the cued task ends, start POMDP solving
            if (
                self._pomdp_status == "solving"
                and self.i_events.data["label"].values.any() == "task_ends"
            ):
                event = "POMDP start solving"
                self.logger.debug(event)
                self.o.data = make_event(event, False)

                # Make and regularize confusion matrix
                pomdp_cm = self._make_conf_matrix()

                # Create Problem object
                self._create_problem(pomdp_cm)
                event = "POMDP problem created"
                self.logger.debug(event)

                # Compute POMDP policy
                self._compute_policy()
                event = "SARSOP policy computed"
                self.logger.debug(event)
                self._pomdp_status = "solved"

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

                self.logger.debug(f"RC: {''.join(list(map(str, self._probas)))}")
                for cnt, c in enumerate(self.codes):
                    self.logger.debug(
                        f"C{cnt}: {''.join(list(map(str, c[:len(self._probas)])))}"
                    )

                self.decision(timestamp)

    def reset(self):
        AccumulationSteadyPred.reset(self)
        self._pomdp_pred_n = 0
        # Reinitialize belief for finite-horizon problem
        if self.finite_horizon:
            self.agent.set_belief(self._init_belief)
