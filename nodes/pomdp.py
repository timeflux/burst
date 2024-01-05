import pomdp_py

from timeflux.core.node import Node

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

        data_len: float (default 0.5)
            Length (in seconds) of the data window used for each time-step.

        time_step: float (default 0.1)
            Time (in seconds) between POMDP steps.

        solving_n: int (default 8)
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
        problem: pomdp_py Problem object
            POMDP instance holding both agent and environment. This object
            contains all the inner elements (states, actions and observations)
            as well as the functions (transition, observation and policy functions)
            that define the POMDP. See [2] for more information.

        policy: pomdp_py AlphaVectorPolicy
            The policy obtained by solving the POMDP using SARSOP [3]. It takes
            the problem's agent and outputs the optimal action given the current
            belief state.

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

    def __init__(self, solver_path, data_len=0.5, time_step=0.1, solving_n=8, solving_timeout=60, 
                 norm_value=0.3, hit_reward=10, miss_cost=-100, wait_cost=-1, gamma=0.99):
        pass

    def update(self):
        pass

