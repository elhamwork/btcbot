"""
models/logistic.py -- full-feature logistic regression with probability
calibration, for use by the (not-yet-run) technical strategy variant
("Strategy B"). Included per project structure; NOT invoked by the baseline
backtest (`--backtest baseline` uses models/baseline.py only), left ready
for the next phase after user review of baseline results.
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

import config


class LogisticFullFeatureModel:
    def __init__(self, feature_cols, min_train_rows=500, calibrate=True):
        self.feature_cols = feature_cols
        self.min_train_rows = min_train_rows
        self.calibrate = calibrate
        self.clf = None
        self.mode = None

    def fit(self, train_df):
        y = train_df["settled_yes"].astype(int)
        n = len(train_df)
        if n < self.min_train_rows or y.nunique() < 2:
            self.mode = "insufficient_data"
            print(f"[logistic] Only {n} training rows / {y.nunique()} classes -- "
                  f"insufficient for a full-feature calibrated fit. Skipping "
                  f"(document in report; use baseline model instead for this sample size).")
            return self
        X = train_df[self.feature_cols].values
        base = LogisticRegression(max_iter=2000)
        if self.calibrate and n >= 5 * self.min_train_rows:
            self.clf = CalibratedClassifierCV(base, cv=3, method="sigmoid")
        else:
            self.clf = base
            if self.calibrate:
                print(f"[logistic] n={n} too small for a held-out calibration fold "
                      f"without further starving the fit -- using uncalibrated "
                      f"logistic regression and documenting this in the report.")
        self.clf.fit(X, y)
        self.mode = "fit"
        return self

    def predict_proba(self, df):
        if self.mode != "fit":
            raise RuntimeError("LogisticFullFeatureModel not fit (insufficient data) -- "
                                "not usable for prediction in this run.")
        return self.clf.predict_proba(df[self.feature_cols].values)[:, 1]
