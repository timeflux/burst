import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin, ClassifierMixin

class Scale(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        self.std = X.std(axis=0)
        return self

    def transform(self, X):
        return X / self.std

    def fit_transform(self, X, y=None):
        return self.fit(X).transform(X)

