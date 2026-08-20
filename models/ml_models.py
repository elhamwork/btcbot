"""
Strategy C models, plus the RESIDUAL family.

THE GATE
========
On the test split the market's own mid-price scored a Brier of 0.1353. Any
model here that does not beat that number cannot beat the market for any
reason other than luck, no matter what its equity curve looks like. Brier is
checked first; trading is checked second.

THE RESIDUAL IDEA
=================
Estimating P(YES) from scratch means competing with a price that already
aggregates everyone else's information -- and losing, as Strategy A did. The
residual models instead take the market price as the starting point and learn
only the CORRECTION:

    P(YES) = market_mid + f(features)

If the market is efficient given our features, f learns nothing and the model
collapses to the market price -- which is the correct answer, and still beats
trying to out-forecast it. If there is a systematic mispricing, f finds it
directly, using far fewer effective parameters than rebuilding the whole
probability from raw inputs.
"""

import numpy as np
from sklearn.ensemble import (GradientBoostingClassifier,
                              GradientBoostingRegressor, RandomForestClassifier,
                              RandomForestRegressor)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import config


def _mat(df, features):
    X = df[features].to_numpy(float)
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


class DirectClassifier:
    """Predict P(YES) from features directly. Calibrated on validation."""

    def __init__(self, kind="gb", features=None, **kw):
        self.kind = kind
        self.features = features or config.FEATURES_TECHNICAL
        self.kw = kw
        self.name = "direct-%s" % kind
        self.pipe = None

    def _base(self):
        if self.kind == "gb":
            return GradientBoostingClassifier(
                random_state=config.RANDOM_SEED,
                n_estimators=self.kw.get("n_estimators", 150),
                max_depth=self.kw.get("max_depth", 3),
                learning_rate=self.kw.get("learning_rate", 0.05))
        if self.kind == "rf":
            return RandomForestClassifier(
                random_state=config.RANDOM_SEED,
                n_estimators=self.kw.get("n_estimators", 300),
                max_depth=self.kw.get("max_depth", 6),
                min_samples_leaf=self.kw.get("min_samples_leaf", 40),
                n_jobs=-1)
        raise ValueError(self.kind)

    def fit(self, train_df, valid_df=None):
        base = self._base()
        base.fit(_mat(train_df, self.features), train_df["y"].to_numpy(int))
        if valid_df is not None and len(valid_df) >= 200 and valid_df["y"].nunique() > 1:
            self.pipe = CalibratedClassifierCV(FrozenEstimator(base),
                                               method="isotonic")
            self.pipe.fit(_mat(valid_df, self.features),
                          valid_df["y"].to_numpy(int))
        else:
            self.pipe = base
        return self

    def predict_proba_yes(self, df):
        p = self.pipe.predict_proba(_mat(df, self.features))[:, 1]
        return np.clip(p, 1e-6, 1 - 1e-6)


class ResidualModel:
    """
    P(YES) = market_mid + shrink * f(features), where f is fit on
    (outcome - market_mid).

    `shrink` < 1 pulls the correction back toward the market. With a short
    sample and a market that is already well calibrated, shrinking is the
    honest prior: it takes a lot of evidence to justify moving far from a
    price that thousands of participants agreed on.
    """

    def __init__(self, kind="ridge", features=None, shrink=1.0, **kw):
        self.kind = kind
        self.features = features or config.FEATURES_TECHNICAL
        self.shrink = shrink
        self.kw = kw
        self.name = "residual-%s(s=%.2f)" % (kind, shrink)
        self.model = None

    def _base(self):
        if self.kind == "ridge":
            return Pipeline([("s", StandardScaler()),
                             ("m", Ridge(alpha=self.kw.get("alpha", 10.0)))])
        if self.kind == "gb":
            return GradientBoostingRegressor(
                random_state=config.RANDOM_SEED,
                n_estimators=self.kw.get("n_estimators", 150),
                max_depth=self.kw.get("max_depth", 3),
                learning_rate=self.kw.get("learning_rate", 0.05))
        if self.kind == "rf":
            return RandomForestRegressor(
                random_state=config.RANDOM_SEED,
                n_estimators=self.kw.get("n_estimators", 300),
                max_depth=self.kw.get("max_depth", 6),
                min_samples_leaf=self.kw.get("min_samples_leaf", 40),
                n_jobs=-1)
        raise ValueError(self.kind)

    def fit(self, train_df, valid_df=None):
        self.model = self._base()
        target = (train_df["y"] - train_df["mid"]).to_numpy(float)
        self.model.fit(_mat(train_df, self.features), target)
        return self

    def predict_proba_yes(self, df):
        corr = self.model.predict(_mat(df, self.features))
        p = df["mid"].to_numpy(float) + self.shrink * corr
        return np.clip(p, 1e-6, 1 - 1e-6)
