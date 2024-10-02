# Starburst - Experience with 11 classes and new features

This Timeflux application is the Starburst BCI with 11 classes featuring ERP plots, correlation plots and gating with Momentum-Decay.

## Installation

First install Timeflux and its depedencies in a new environment:

```bash
conda create --name timeflux python=3.10 pip pytables
conda activate timeflux
pip install timeflux timeflux_ui timeflux_dsp pyriemann imblearn
timeflux -v
```

Then simply clone this repository:

```bash
git clone https://github.com/timeflux/burst.git
```

To launch the application, get into a terminal and type:
```bash
conda activate timeflux
timeflux -d main.yaml
```

## Procedure

The typical experiment with the Starburst is made of the following steps

- The calibration procedure 
- Training of the model
- Training task
- Pinpad task

## Configuration

The application can be fine-tuned in a number of ways.

### Environment

The `.env` file provides high-level configuration. Parameters are explained in commentary and can be modified in msot cases.

## Application schema

![Application schema](doc/schema.png)

## Analysing

If anything goes wrong, logs can be found in the `log` folder.

For further analysis, data and events are recorded in the `data` folder.

### Load EEG data, events and metadata

