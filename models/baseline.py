"""
Strategy A -- the baseline probability model.

Two variants, both using ONLY distance-from-strike, time remaining, and
volatility:

  AnalyticBaseline  no fitting at all. Assumes driftless GBM over the
                    remaining window and reads P(finish above strike) straight
                    off the normal CDF. This is the honest null: if a fitted
                    model cannot beat it, the fitting is adding nothing.

  LogisticBaseline  logistic regression on the same three inputs plus their
                    natural combination (the z-score), fit on TRAIN only and
                    probability-calibrated on VALIDATION.

Both output calibrated P(YES); P(NO) = 1 - P(YES).
"""

import numpy as np
from scipy.stats import norm
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import config


class AnalyticBaseline:
    """P(S_T >= K) under driftless GBM. No parameters are learned."""

    name = "analytic"

    def fit(self, X, y=None):
        return self

    def predict_proba_yes(self, df):
        S = df["btc_price"].to_numpy(float)
        K = df["floor_strike"].to_numpy(float)
        T = df["minutes_remaining"].to_numpy(float)
        sigma = df["rv_5m"].to_numpy(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            denom = sigma * np.sqrt(T)
            z = np.log(S / K) / denom
            p = norm.cdf(z)
        # If volatility is undefined or zero, fall back to the sign of the
        # distance -- the only defensible answer without a vol estimate.
        p = np.where(np.isfinite(p), p, (S >= K).astype(float))
        return np.clip(p, 1e-6, 1 - 1e-6)


class LogisticBaseline:
    """Calibrated logistic regression on the baseline feature set."""

    name = "logistic"

    def __init__(self, features=None, C=1.0):
        self.features = features or config.FEATURES_BASELINE
        self.C = C
        self.pipe = None

    def _matrix(self, df):
        X = df[self.features].to_numpy(float)
        return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    def fit(self, train_df, valid_df=None):
        base = Pipeline([
            ("scale", StandardScaler()),
            ("lr", LogisticRegression(C=self.C, max_iter=2000)),
        ])
        Xtr, ytr = self._matrix(train_df), train_df["y"].to_numpy(int)

        if valid_df is not None and len(valid_df) >= 100 and valid_df["y"].nunique() > 1:
            # Fit on TRAIN, then calibrate on VALIDATION only. Freezing the
            # fitted pipeline keeps the calibrator from refitting it and
            # letting validation data influence the coefficients.
            base.fit(Xtr, ytr)
            self.pipe = CalibratedClassifierCV(
                FrozenEstimator(base), method="isotonic")
            self.pipe.fit(self._matrix(valid_df), valid_df["y"].to_numpy(int))
        else:
            base.fit(Xtr, ytr)
            self.pipe = base
        return self

    def predict_proba_yes(self, df):
        p = self.pipe.predict_proba(self._matrix(df))[:, 1]
        return np.clip(p, 1e-6, 1 - 1e-6)


class MarketBaseline:
    """
    The market's own mid-price as the probability estimate.

    Included as a reference point: by construction it generates zero edge, so
    it measures how well the market itself is calibrated. If the market's
    Brier score beats every model, that is the finding.
    """

    name = "market"

    def fit(self, X, y=None):
        return self

    def predict_proba_yes(self, df):
        return np.clip(df["mid"].to_numpy(float), 1e-6, 1 - 1e-6)


def get_model(name):
    return {"analytic": AnalyticBaseline,
            "logistic": LogisticBaseline,
            "market": MarketBaseline}[name]()
