import numpy as np
from imblearn.under_sampling import RandomUnderSampler

class UnderSample():

    def run(self, data):
        if not data["fitted"]:
            rus = RandomUnderSampler()
            counter = np.array(range(0, len(data["y"]))).reshape(-1, 1)
            index, _ = rus.fit_resample(counter, data["y"][:])
            data["X"] = np.squeeze(data["X"][index,:,:], axis=1)
            data["y"] = np.squeeze(data["y"][index])
        return data
