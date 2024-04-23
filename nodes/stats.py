import sys
import json
import pandas as pd
import numpy as np

fname = sys.argv[1]
predictions = pd.read_hdf(fname, "predictions")
events = pd.read_hdf(fname, "events")
config = json.loads(events.loc[events["label"] == "session_begins"]["data"][0])
print(config, "\n\n")


def stats(results):
    results = np.array(results)
    hits = results[:, 0]
    decisions = results[:, 1]
    accuracy = np.count_nonzero(hits) * 100 / len(results)
    decision_time_mean = np.mean(decisions)
    decision_time_std = np.std(decisions)
    print(results)
    print(f"Accuracy: {accuracy}")
    print(f"Decision time (mean): {decision_time_mean}")
    print(f"Decision time (std): {decision_time_std}")
    print("\n")


def task_cue():
    start = events.loc[
        (events["label"] == "task_begins") & (events["data"] == '{"task":"cue"}')
    ].index[-1]
    stop = events.loc[(events["label"] == "task_ends") & (events.index > start)].index[
        0
    ]
    targets = config["task"]["cue"]["targets"]
    print(f'* Task "CUE" starts at {start} and ends at {stop}.')
    preds = predictions.loc[predictions.index > start][0 : len(targets)]["data"]
    results = []
    for index, pred in enumerate(preds):
        pred = json.loads(pred)
        target = pred["target"]
        frames = pred["frames"]
        hit = int(target) == targets[index]
        decision = int(frames) * (1 / 60)
        results.append([hit, decision])
    stats(results)


def task_sequence():
    start = events.loc[
        (events["label"] == "task_begins") & (events["data"] == '{"task":"sequence"}')
    ].index[-1]
    stop = events.loc[(events["label"] == "task_ends") & (events.index > start)].index[
        0
    ]
    sequences = config["task"]["sequence"]["sequences"]
    targets = [x for sequence in sequences for x in sequence]
    print(f'* Task "SEQUENCE" starts at {start} and ends at {stop}.')
    preds = predictions.loc[(predictions.index > start) & (predictions.index < stop)][
        "data"
    ]
    results = []
    index = 0
    for pred in preds:
        pred = json.loads(pred)
        target = pred["target"]
        frames = pred["frames"]
        hit = int(target) == targets[index]
        if hit:
            index += 1
        decision = int(frames) * (1 / 60)
        results.append([hit, decision])
    stats(results)


task_cue()
task_sequence()
