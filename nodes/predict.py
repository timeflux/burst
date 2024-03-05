import numpy as np
import random
import json
from scipy.stats import pearsonr
from timeflux.helpers.port import make_event
from timeflux.core.node import Node

import pomdp_py
from pomdp_py import sarsop
from bci_pomdp.problem import BaseProblem
from bci_pomdp.domain import BCIObservation, BCIState
from sklearn.metrics import confusion_matrix

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
        norm_value (float): Parameter used to normalize POMDP's confusion matrix (default: 0.3).
        problem (pomdp_py POMDP): POMDP problem object (defualt: None).
        policy (pomdp_py AlphaVectorPolicy): POMDP policy (default: None).
        pomdp_status (str or None): Starts at None. It is set to 'solving' when the cued task starts. It is set to
        'solved' when the policy is computed (default: None). 

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
        self.norm_value = 0.3
        self.hit_reward = 10
        self.miss_cost = -100
        self.wait_cost = -1
        self.solver_path = "/home/dcas/j.torre-tresols/gitrepos/sarsop/src/pomdpsol"
        self.problem = None
        self.policy = None
        self._pomdp_status = None
        self._current_cue = None
        self._pomdp_preds = []
        self._pomdp_trues = []
        self.reset()

    def _get_correlations(self, x=None, indices=None):
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
            y = [code[i] for i in indices]
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

    def _normalize_conf_matrix(self, conf_matrix):
        """Normalize confusion matrix by mixing it with the uniform distribution [1]"""
        copy_matrix = conf_matrix.copy()
        n_class = copy_matrix.shape[0]

        regu_matrix = (1 - self.norm_value) * copy_matrix + self.norm_value * 1 / n_class

        return regu_matrix

    def _make_conf_matrix(self):
        """Create and normalize confusion matrix"""
        raw_conf_matrix = confusion_matrix(self._pomdp_trues, self._pomdp_preds, normalize='true')
        norm_conf_matrix = self._normalize_conf_matrix(raw_conf_matrix)

        return norm_conf_matrix

    def _get_all_states(self):
        n_targets = len(self.codes)
        all_states = [BCIState(int(target)) for target in range(n_targets)]
        all_init_states = all_states.copy()

        return all_states, all_init_states

    def _get_init_belief(self, states, init_states):
        n_init_states = len(init_states)
        init_belief = pomdp_py.Histogram({state: 1 / n_init_states if state in init_states else 0 for 
                                          state in states})

        return init_belief

    def _create_problem(self, conf_matrix):
        """Create problem object for the POMDP model"""
        # Create a list of all possible states, and a list of all the possible initial states
        all_states, all_init_states = self._get_all_states()
        init_true_state = random.choice(all_init_states)

        # Get initial belief (uniform across initial states)
        init_belief = self._get_init_belief(all_states, all_init_states)

        self.problem = BaseProblem(init_belief, init_true_state, n_targets=len(self.codes),
                                   conf_matrix=conf_matrix, hit_reward=self.hit_reward, 
                                   miss_cost=self.miss_cost, wait_cost=self.wait_cost)

    def _compute_policy(self):
        self.policy = sarsop(self.problem.agent, pomdpsol_path=self.solver_path,
                             discount_factor=0.8, timeout=30,
                             memory=4096, precision=0.001)
    def update(self):
        if self.i_events.ready():
            # Keep track of the last cue (used for POMDP solving)
            if self.i_events.data['label'].values.any() == 'cue':
                self._current_cue = json.loads(self.i_events.data['data'].iloc[0])['target']

            # When the cued task starts, start POMDP Accumulation
            if not self._pomdp_status and self.i_events.data['label'].values.any() == 'task_begins':
                event = "POMDP start accumulation"
                self.logger.debug(event)
                self.o_pub.data = make_event(event, False)
                self._pomdp_status = 'solving'

            # When the cued task ends, start POMDP solving
            if self._pomdp_status == 'solving' and self.i_events.data['label'].values.any() == 'task_ends':
                event = "POMDP start solving"
                self.logger.debug(event)
                self.o_pub.data = make_event(event, False)

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
                self._pomdp_status = 'solved'
                 
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

                # Compute another correlation for POMDP
                if self._pomdp_status and self._frames % self.pomdp_step == 0:
                    # POMDP works with data windows that must have the same size, so we slice _probas
                    pomdp_probas = self._probas[-self.min_buffer_size:]
                    pomdp_indices = self._indices[-self.min_buffer_size:]
                    pomdp_corrs, _ = self._get_correlations(x=pomdp_probas, indices=pomdp_indices)

                    # Save the highest correlation with the current cue
                    sorted_corrs = np.flip(np.argsort(pomdp_corrs))
                    pomdp_target = int(sorted_corrs[0])

                    if self._pomdp_status == 'solved':
                        # Print current belief
                        cur_belief = self.problem.agent.cur_belief
                        self.logger.debug(f"Current belief at frame {self._frames}:")
                        self.logger.debug(cur_belief)

                        # Get action and max belief when action is taken
                        action = self.policy.plan(self.problem.agent)
                        max_b = cur_belief[cur_belief.mpe()]

                        # Get observation 
                        observation = BCIObservation(pomdp_target)

                        # Update belief
                        new_belief = pomdp_py.update_histogram_belief(self.problem.agent.cur_belief,
                                                                      action, observation, 
                                                                      self.problem.agent.observation_model,
                                                                      self.problem.agent.transition_model,
                                                                      static_transition=False)
                        self.problem.agent.set_belief(new_belief)

                        # If no prediction is done, print and continue
                        if action.name == 'a_wait':
                            self.logger.debug(f"Action: {action}\t Observation: {pomdp_target}")
                        else:
                            meta = {"timestamp": timestamp, "target": action.id, 
                                    "score": max_b, "frames": self._frames}

                    else:  # self._pomdp_status == 'solving'
                        self._pomdp_preds.append(pomdp_target)
                        self._pomdp_trues.append(self._current_cue)
                        self.logger.debug(f"POMDP prediction: {pomdp_target}\tTrue label: {self._current_cue}" \
                                          f"\tFrame: {self._frames}\tUsed {len(pomdp_probas)} probas and " \
                                          f"{len(pomdp_indices)} indices")

                if self._pomdp_status != 'solved':  # Used before and during POMDP accumulation
                    # Compute the Pearson correlation coefficient
                    correlations, pvalues = self._get_correlations(x=self._probas, indices=self._indices)

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
                    
                    # Make pred if the thresholds are passed
                    meta = {"timestamp": timestamp, "target": target, "score": correlation, "frames": self._frames}

                try:
                    # Send prediction
                    self.o_pub.data = make_event("predict", meta, True)
                    self.logger.debug(meta)
                    self.reset()
                    self._recovery = timestamp
                except UnboundLocalError:
                    # Frames where POMDP is not updated
                    self.logger.debug(f"POMDP waiting, frame {self._frames}")
                    continue


    def reset(self):
        self._probas = []
        self._indices = []
        self._recovery = False
        self._frames = 0

