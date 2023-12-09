import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin, ClassifierMixin
from sklearn.cross_decomposition import CCA

class Scale(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        self.std = X.std(axis=0)
        print(X.shape, self.std.shape)
        return self

    def transform(self, X):
        return X / self.std #+ 1e-8

    def fit_transform(self, X, y=None):
        return self.fit(X).transform(X)


class MCCA(BaseEstimator, ClassifierMixin):

    def __init__(self):
        self._cca = CCA(n_components=1, max_iter=1000)
        self._templates = {}

    def fit(self, X, y, sample_weight=None):
        trained = np.unique(y)
        for template_id in trained:
            indices = np.where(y == template_id)
            self._templates[template_id] = X[indices].mean(axis=0)
        return self

    def predict(self, X):
        y = []
        for x in X:
            correlations = {}
            for template_id in self._templates:
                x_score, y_score = self._cca.fit_transform(x.T, self._templates[template_id].T)
                correlations[template_id] = np.corrcoef(x_score.T, y_score.T)[0, 1]
            y.append(max(correlations, key=lambda k: correlations[k]))
        return y

    def predict_proba(self, X):
        P = np.zeros(shape=(len(X), len(self._templates)))
        for i, x in enumerate(X):
            for j, template_id in enumerate(self._templates):
                x_score, y_score = self._cca.fit_transform(x.T, self._templates[template_id].T)
                P[i, j] = np.corrcoef(x_score.T, y_score.T)[0, 1]
        return P / np.resize(P.sum(axis=1), P.T.shape).T