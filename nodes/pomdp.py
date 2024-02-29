import pomdp_py

import numpy as np

from timeflux.core.node import Node
from sklearn.metrics import confusion_matrix

class POMDP(Node):
    """ Partially Observable Markov Decission Process module

    This node uses a POMDP to accumulate predictions from single-trial classifications from a ML node.
    When the belief state for a certain class reaches the model's threshold, a final prediction is made.

    The POMDP needs to be solved after the ML pipeline is trained. This entails:
        - Collecting a second batch of calibration data
        - Get class predictions from said data from the pipeline, as well as the true labels
        - Generate a confusion matrix using this predicted data, normalized across rows (each row
          adds up to 1)
        - Create a Problem instance, which encapsulates all the POMDP model's logic and parameters
        - Compute the POMDP's policy

    Once the policy is obtained, both the Problem object and the obtained policy are used for the
    evaluation. For each trial, the POMDP performs the following steps:
        - An action is selected according to the policy and current belief
        - If the selected action corresponds to a decision:
          - The trial ends and the final prediction is made 
          - The belief is restarted to the initial belief

        - If not:
          - The model checks if the current time step is the last one of the current trial
          - If it is:
            - The model outputs a "no-action" prediction, meaning that no decision was made
              within the time limit of the model. The trial ends
            - The belief is restarted to the initial belief
          If not:
            - The ML algorithm's prediction corresponding to this time step is retrieved
            - This label is transformed into a POMDP observation
            - The belief state is updated according to the executed action and the obtained
              observation. The trial continues

    Args:
        solver_path: str or path object
            Path to the solver binary file.

        event_start_evaluation: str (?)
            Event that sets the 'mode' parameter to 'evaluation'

        n_targets: int
            Number of BCI targets

        data_len: float (default 0.5)
            Length (in seconds) of the data window used for each time-step.

        epoch_len: float (default 1.)
            Maximum duration (in seconds) for each trial.

        time_step: float (default 0.1)
            Time (in seconds) between POMDP steps.

        n_steps: int (default 6)
            Number of time steps before            

        eval_n: int (default 8)
            Number of blocks used for the POMDPs solving step.

        solving_timeout: int (default 60)
            Maximum time for the POMDP solver to converge to the optimal policy.

        norm_value: float (default 0.3)
            Value to use to "normalize" the obtained confusion matrix, as done in.
            [1] (equation 4)

        hit_reward: int (default 10)
            POMDP reward for correct decision.

        miss_cost: int (default -100)
            POMDP reward for incorrect decision.

        wait_cost: int (default -1)
            POMDP reward for the 'wait' action.

        gamma: float (default 0.99)
            Discount factor for POMDP.

    Attributes:
        mode: str, default ''
            Operation mode of the node. It starts as an empty string, meaning the node will 
            remain inactive until an operation mode is specified. The event set to the parameter 
            'event_start_accumulation' sets this attr to 'accumulation', in which the node will 
            accumulate data. Upon receiving the event set to the parameter 'mode_start_solving', 
            the mode is set to 'solving' and the POMDP policy is computed (see above). After the 
            evaluation phase is completed, the node will enter 'testing' mode until operation is 
            finished.

        eval_pred: list of int, default []
            List preserving predicted labels for evaluation

        eval_true: list or int, default []
            List preserving true labels for evaluation

        current_cue: int or None
            Current cue to add to eval_true
            
        problem: pomdp_py Problem object
            POMDP instance holding both agent and environment. This object
            contains all the inner elements (states, actions and observations)
            as well as the functions (transition, observation and policy functions)
            that define the POMDP. See [2] for more information.

        policy: pomdp_py AlphaVectorPolicy
            The policy obtained by solving the POMDP using SARSOP [3]. It takes
            the problem's agent and outputs the optimal action given the current
            belief state.

        n_steps: int
            Number of steps for each POMDP trial. It is equal to the number of
            data windows that can be used per trial considering data_len, epoch_len
            and time_step, plus one extra step for the POMDP to decide after all trial
            data has been used.

        i: port 
            Default input, expects DataFrame

        o: port
            Default Output, expects DataFrame

    References:
        [1] - J. J. T. Tresols, C. P. C. Chanel and F. Dehais, 
              "POMDP-BCI: A Benchmark of (re)active BCI using POMDP to Issue Commands," 
              in IEEE Transactions on Biomedical Engineering, doi: 10.1109/TBME.2023.3318578.

        [2] - https://h2r.github.io/pomdp-py/html/design_principles.html

        [3] - https://github.com/AdaCompNUS/sarsop
    """

    def __init__(self, solver_path, event_start_accumulation, event_start_solving,
                 n_targets, data_len=0.5, epoch_len=1.0, time_step=0.1, eval_n=8, 
                 solving_timeout=60, norm_value=0.3, hit_reward=10, miss_cost=-100, 
                 wait_cost=-1, gamma=0.99):
        self.solver_path = solver_path
        self.event_start_accumulation = event_start_accumulation
        self.event_start_solving = event_start_solving
        self.n_targets = n_targets
        self.data_len = data_len
        self.epoch_len = epoch_len
        self.time_step = time_step
        self.eval_n = eval_n 
        self.solving_timeout = solving_timeout
        self.norm_value = norm_value
        self.hit_reward = hit_reward
        self.miss_cost = miss_cost
        self.wait_cost = wait_cost
        self.gamma = gamma
        self.mode = ''
        self.eval_pred = []
        self.eval_true = []
        self.current_cue = None
        self.problem = None
        self.policy = None
    
    @property
    def n_steps(self):
        time_steps = list(np.round(np.arange(0, self.epoch_len + 0.01, self.time_step), 2))
        n_steps = len(time_steps)
    
        return n_steps

    def _normalize_conf_matrix(self, conf_matrix):
        """Normalize confusion matrix by mixing it with the uniform distribution [1]"""
        copy_matrix = conf_matrix.copy()
        n_class = copy_matrix.shape[0]

        regu_matrix = (1 - self.norm_value) * copy_matrix + self.norm_value * 1 / n_class

        return regu_matrix

    def _make_conf_matrix(self):
        """Create and normalize confusion matrix"""
        raw_conf_matrix = confusion_matrix(self.eval_true, self.eval_pred, normalize='true')
        norm_conf_matrix = self._normalize_conf_matrix(raw_conf_matrix)

        return norm_conf_matrix

    def _get_all_states(self):
        pass

    def _get_init_belief(self):
        pass

    def _create_problem(self, conf_matrix):
        """Create problem object for the POMDP model"""
        # Create a list of all possible states, and a list of all the possible initial states
        all_states, all_init_states = self_.get_all_states()
        init_true_state = random.choice(all_init_states)

        # Get initial belief (uniform across initial states)
        init_belief = self._get_init_belief(all_states, all_init_states)

        self.problem = TDProblem(init_belief, init_true_state, n_targets=self.n_targets,
                                 n_steps=self.pomdp_steps, conf_matrix=conf_matrix,
                                 hit_reward=self.hit_reward, miss_cost=self.miss_cost,
                                 wait_cost=self.wait_cost, td_observations=False)

    def _compute_policy(self):
        """Compute POMDP policy"""
        self.policy = sarsop(self.problem.agent, solver_path=self.solver_path,
                             discount_factor=self.gamma, timeout=self.solving_timeout,
                             memory=4096, precision=0.001)

    def update(self):
        if not self.i_events.ready():
            return

        if self.i_events.data['label'].values.any() == 'cue':
            self.current_cue = self.i_events.data

        if self.i_obs.ready():
            observation = self.i_obs.data
            self.logger.debug(f"POMDP: {self.current_cue}")
            self.logger.debug(f"POMDP {observation}")

        



        
        #         if self.i_event.ready():
        #             if self.i_event.data == self.event_start_accumulation:
        #                 self.mode = 'accumulation' 
        # 
        #         if self.mode == 'accumulation':
        #             # Start accumulating events (I don't know how to access events)
        #             if not self.i_event.ready():
        #                 return
        #             # Listen to the last cued event
        #             if self.i_cue.ready():
        #                 self.current_cue = self.i_cue.data
        #             pred = self.i_evaluation.data
        # 
        #             self.eval_pred.append(pred)
        #             self.eval_true.append(self.current_cue)
        # 
        #             if self.i_event_data == self.event_start_solving:
        #                 self.mode = 'solving'
        # 
        #         # Start evaluating when the necessary events are accumulated
        #         if self.mode == 'solving':
        #             conf_matrix = self._make_conf_matrix()
        #             self._create_problem(conf_matrix)
        #             self._compute_policy()
        #             self.mode = 'testing'
        # 
        #         if self.mode == 'testing':
        #             # Main POMDP body
        #             pass
        # 
