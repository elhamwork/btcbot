"""
models/baseline.py -- Strategy A: minimal heuristic/logistic model.

Uses ONLY {strike_distance_pct, minutes_remaining, realized_vol_5m} as
specified. If there isn't enough data to fit a stable logistic regression
(documented check), falls back to a closed-form heuristic: a driftless
Brownian-motion barrier probability P(BTC finishes above strike | current
distance, time remaining, recent realized vol), i.e. the same family of
formula used to generate the synthetic fair price -- but re-estimated
independently from the *feature columns only* (never reads fair_yes_prob_model
or settled_yes), so this is a legitimate model input->output mapping, not
a leak of the synthetic generator's ground truth.
"""

import math
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import config

FEATURES = config.BASELINE_FEATURES  # ["strike_distance_pct","minutes_remaining","realized_vol_5m"]
_COLMAP = {"realized_vol_5m": "vol_5m"}  # dataframe column name mapping


def _cols(df):
    return [_COLMAP.get(f, f) for f in FEATURES]


def heuristic_prob(row):
    """Closed-form no-fit fallback: Normal CDF barrier-touch probability."""
    dist_pct = row["strike_distance_pct"]
    minutes = max(row["minutes_remaining"], 1e-6)
    vol_5m = max(row["vol_5m"], 1e-6)  # per-minute realized vol estimate (std of 1m log returns over trailing 5m)
    sigma_t = vol_5m * math.sqrt(minutes)
    if sigma_t <= 0:
        return 1.0 if dist_pct > 0 else 0.0
    d = dist_pct / sigma_t
    return 0.5 * (1.0 + math.erf(d / math.sqrt(2.0)))


class BaselineModel:
    """Strategy A. Fits sklearn LogisticRegression on the 3 minimal features
    if there is enough data (>= min_train_rows and >=2 classes present in
    training split); otherwise documents the fallback and uses the
    closed-form heuristic instead of overfitting a model to a tiny sample."""

    def __init__(self, min_train_rows=200):
        self.min_train_rows = min_train_rows
        self.clf = None
        self.mode = None  # "logistic" or "heuristic"

    def fit(self, train_df):
        cols = _cols(train_df)
        y = train_df["settled_yes"].astype(int)
        n = len(train_df)
        n_classes = y.nunique()
        if n >= self.min_train_rows and n_classes >= 2:
            X = train_df[cols].values
            self.clf = LogisticRegression(max_iter=1000)
            self.clf.fit(X, y)
            self.mode = "logistic"
            print(f"[baseline] Fit logistic regression on {n} training rows "
                  f"(features={FEATURES}).")
        else:
            self.mode = "heuristic"
            print(f"[baseline] Training data too small/insufficiently varied "
                  f"(n={n}, classes={n_classes}) for a stable fit -- falling back "
                  f"to closed-form barrier-probability heuristic on the same "
                  f"3 features. This is documented, not a silently degraded model.")
        return self

    def predict_proba(self, df):
        cols = _cols(df)
        if self.mode == "logistic":
            return self.clf.predict_proba(df[cols].values)[:, 1]
        else:
            return df.apply(heuristic_prob, axis=1).values
