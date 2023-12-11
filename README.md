# Burst VEP

This Timeflux application is a proof-of-concept of the Burst VEP method.

## Installation

First install Timeflux and its depedencies in a new environment:

```bash
conda create --name timeflux python=3.10 pip pytables
conda activate timeflux
pip install timeflux timeflux_dsp pyriemann imblearn
timeflux -v
```

Then simply clone this repository:

```bash
git clone https://github.com/timeflux/burst.git
```

## Configuration

The application can be fine-tuned in a number of ways.

### Environment

The [`.env`](https://github.com/timeflux/burst/blob/main/.env) file provides high-level configuration.

By default, a random signal is used in place of EEG data, so you can try the application without any additional hardware. For real EEG acquisition, you must provide your own `DEVICE.yaml` graph in the [`graphs`](https://github.com/timeflux/burst/tree/main/graphs) folder.

Currently, only the `riemann` machine learning pipeline is available.

| Setting | Description  | Default |
|---------|--------------|---------|
| DEVICE | EEG device | dummy |
| EPOCH | Epoch length, in seconds, used for classification | 0.25 |
| PIPELINE | Classification pipeline (riemann, eegnet) | riemann |

Note that you can also set up environment variables [outside of an .env file](https://doc.timeflux.io/en/stable/usage/getting_started.html#environment).

### Burst codes

Burst codes are defined in a [hook](https://github.com/timeflux/burst/blob/main/hooks/pre.py). This allows the codes to be stored in an environment variable that can be reused in the graphs. In future versions, this will also allow to generate dynamic burst codes.

### Preprocessing

The default preprocessing consists of the following:

- Average rereferencement
- Notch filter at 50 Hz (IIR, order 3)
- Bandpass filter between 1 and 40 Hz (IIR, order 2)

It can be modified in the [`main.yaml`](https://github.com/timeflux/burst/blob/main/main.yaml) graph.

Individual epochs are scaled using the standard deviation of the training set. Class imbalance is handled through random undersampling.

### User interface

The application expects an dictionary of settings.

| Setting | Description  | Default |
|---------|--------------|---------|
| targets | A list of burst code (one per target) | See `main.yaml` |
| training.blocks | The number of rounds for each target during calibration | 3 |
| training.repetitions | The number of repetitions for each target during each block | 2 |
| training.duration_rest | The rest period before a new target is presented, in ms | 2000 |
| training.duration_cue_on | The duration of the cue | 1500 |
| training.duration_cue_off | The duration of the pause before the code starts flashing | 500 |
| task.enabled | `true` if the cued task must be enabled, `false` otherwise | `true` |
| task.targets | The number of random targets or the list of targets to be cued | 5 |
| validation.duration_rest | The rest period before the free run begins, in ms | 2000 |
| validation.duration_lock_on | The duration of the feedback when a prediction is received | 1500 |
| validation.duration_lock_off | The rest period after the feedback | 500 |
| stim.type | The stimulus type ('gabord', 'ricker', 'face', 'plain') | gabor |
| stim.depth | The stimulus opacity (between 0 and 1) | 0.8 |
| colors.background | The background color | #202020 |
| colors.text | The text color | #FFFFFF |
| colors.cross | The fixation cross color | #FFFFFF |
| colors.target_off | The target color during the off-state | #797979 |
| colors.target_on | The target color during the on-state, if stim.type is 'plain' | #FFFFFF |
| colors.target_border | The border color | #000000 |
| colors.target_cue | The cue border color | blue |
| colors.target_success | The target color when the task is successful | green |
| colors.target_failure | The target color when the task failed | red |
| colors.target_lock | The prediction color | blue |

The default settings can be changed in the [`main.yaml`](https://github.com/timeflux/burst/blob/main/main.yaml) graph. Also see [`app.js`](https://github.com/timeflux/burst/blob/main/www/assets/js/app.js) for details.

#### HTML

Targets can be freely added in [`index.html`](https://github.com/timeflux/burst/blob/main/www/index.html). Each target must have a `target` class. Targets will be identified in DOM order (i.e. the first target in `index.html` will have the `0` id). There must be as many HTML elements as there are burst codes.

#### CSS

The shape, position, and colors of the targets can be further adjusted in [`custom.css`](https://github.com/timeflux/burst/blob/main/www/assets/css/custom.css).

#### Images

To create a new stimulus type, simply add a new image in [this folder](https://github.com/timeflux/burst/blob/main/www/assets/img/).

### Predictions

The application classifies single flashes. Epochs are triggered at each frame on 250ms windows. The classification pipeline computes xdawn covariances projected on the tangent space followed by a linear discriminant analysis. The resulting probabilities are [accumulated](https://github.com/timeflux/burst/blob/main/nodes/predict.py) in a circular buffer on which correlation analysis is performed. When enough confidence is reached for a specific target, a final prediction is made.

The accumulation engine is [configurable](https://github.com/timeflux/burst/blob/main/graphs/classification.yaml).

| Setting | Description  | Default |
|---------|--------------|---------|
| codes | The list of burst codes, one for each target | |
| min_buffer_size | Minimum number of predictions to accumulate before emitting a prediction | 30 |
| max_buffer_size | Maximum number of predictions to accumulate for each class | 200 |
| threshold | Minimum value to reach according to the Pearson correlation coefficient | .75 |
| delta | Minimum difference percentage to reach between the p-values of the two best candidates | .5 |
| recovery | Minimum duration in ms required between two consecutive epochs after a prediction | 300 |

Please note that default values are reasonnably suitable for random data. For real EEG data, the threshold should probably be raised.

## Running

Run the following:

```bash
timeflux -d main.yaml
```

You can monitor the EEG signal [here](http://localhost:8000/monitor/). The application is accessible at [this address](http://localhost:8000/bvep/).


Maximize your browser window to avoid distractions, and follow the instructions. The session includes the following steps:

- Fixation cross (to ensure that the monitor is directly facing the user)
- Calibration stage (required to compute the model)
- Evaluation task (optional)
- Free selection

When you are done, close the browser tab, and send the `Ctrl+C` command to Timeflux.

## Analysing

If anything goes wrong, logs can be found in the `log` folder.

For further analysis, data and events are recorded in the `data` folder.

### Load EEG data, events and metadata

```python
import pandas as pd
fname = "data/20231121-090341.hdf5"
raw = pd.read_hdf(fname, "raw")
filtered = pd.read_hdf(fname, "filtered")
predictions = pd.read_hdf(fname, "predictions")
events = pd.read_hdf(fname, "events")
config = events.loc[events['label'] == "session_begins"]["data"][0]
score = events.loc[events['label'] == "score"]["data"][0]
```

