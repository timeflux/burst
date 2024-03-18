import numpy as np
import random
import json
import pomdp_py

from timeflux.helpers.port import make_event
from nodes.accumulation.simple import AccumulationSteadyPred
from pomdp_py import sarsop
from bci_pomdp.problem import BaseProblem
from bci_pomdp.domain import BCIObservation, BCIState
from sklearn.metrics import confusion_matrix

class AccumulationPOMDP(AccumulationSteadyPred):
    def __init__(
        self,
        codes,
        min_buffer_size=30,
        max_buffer_size=200,
        min_frames_pred=30,
        max_frames_pred=300,
        pomdp_step=6,
        norm_value=0.3,
        hit_reward=10,
        miss_cost=-100,
        wait_cost=-1,
        solver_path=None,
        discount_factor=0.8,
        timeout=30,
        memory=4096,
        precision=0.001,
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

        self._pomdp_step = pomdp_step
        self._norm_value = norm_value
        self._hit_reward = hit_reward
        self._miss_cost = miss_cost
        self._wait_cost = wait_cost
        self._solver_path = solver_path
        self._discount_factor = discount_factor,
        self._timeout = timeout,
        self._memory = memory,
        self._precision = precision,

        self._problem = None
        self._policy = None
        self._pomdp_status = None
        self._current_cue = None
        self._pomdp_preds = []
        self._pomdp_trues = []

    def _normalize_conf_matrix(self, conf_matrix):
        """Normalize confusion matrix by mixing it with the uniform distribution [1]"""
        copy_matrix = conf_matrix.copy()
        n_class = copy_matrix.shape[0]

        regu_matrix = (
            1 - self._norm_value
        ) * copy_matrix + self._norm_value * 1 / n_class

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
        init_belief = self._get_init_belief(all_states, all_init_states)

        self._problem = BaseProblem(
            init_belief,
            init_true_state,
            n_targets=len(self.codes),
            conf_matrix=conf_matrix,
            hit_reward=self._hit_reward,
            miss_cost=self._miss_cost,
            wait_cost=self._wait_cost,
        )

    def _compute_policy(self):
        self._policy = sarsop(
            self._problem.agent,
            pomdpsol_path=self._solver_path,
            discount_factor=0.8,
            timeout=30,
            memory=4096,
            precision=0.001,
        )

    def decision(self, timestamp):
        # Compute another correlation for POMDP
        if self._pomdp_status and self._frames % self._pomdp_step == 0:
            # POMDP works with data windows that must have the same size, so we slice _probas
            pomdp_probas = self._probas[-self.min_buffer_size :]
            pomdp_indices = self._indices[-self.min_buffer_size :]
            pomdp_corrs, _ = self.correlation(x=pomdp_probas, indices=pomdp_indices)

            # Save the highest correlation with the current cue
            sorted_corrs = np.flip(np.argsort(pomdp_corrs))
            pomdp_target = int(sorted_corrs[0])

            if self._pomdp_status == "solved":
                # Print current belief
                cur_belief = self._problem.agent.cur_belief
                self.logger.debug(f"Current belief at frame {self._frames}:")
                self.logger.debug(cur_belief)

                # Get action and max belief when action is taken
                action = self._policy.plan(self._problem.agent)
                max_b = cur_belief[cur_belief.mpe()]

                # Get observation
                observation = BCIObservation(pomdp_target)

                # Update belief
                new_belief = pomdp_py.update_histogram_belief(
                    self._problem.agent.cur_belief,
                    action,
                    observation,
                    self._problem.agent.observation_model,
                    self._problem.agent.transition_model,
                    static_transition=False,
                )
                self._problem.agent.set_belief(new_belief)

                # If no prediction is done, print and continue
                if action.name == "a_wait":
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
                self.logger.debug(
                    f"POMDP prediction: {pomdp_target}\tTrue label: {self._current_cue}"
                    f"\tFrame: {self._frames}\tUsed {len(pomdp_probas)} probas and "
                    f"{len(pomdp_indices)} indices"
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
