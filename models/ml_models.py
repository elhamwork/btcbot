"""
models/ml_models.py -- scaffolding for Strategy C (random forest / gradient
boosting). STUB ONLY -- intentionally not trained or invoked in this pass.

Per project instructions: "if the sample is too small for ML on this first
pass, document that honestly rather than overfitting a model to a tiny
sample." Our baseline synthetic sample is 672 contracts / ~10k contract-minute
rows across only 7 days -- nowhere near enough for a trustworthy random
forest / gradient boosting fit with proper train/val/test separation
(withholding enough data for validation+test would leave a few hundred
training rows for a high-capacity model prone to overfitting noise, and the
data itself is synthetic demo data, not real Kalshi history, so any ML
"edge" found here would be doubly meaningless).

TODO (next phase, pending user review of baseline results and, ideally,
access to real Kalshi + real intraday BTC data):
  - RandomForestClassifier / GradientBoostingClassifier (or XGBoost/LightGBM)
    over the full feature set in features/feature_engine.py.
  - Nested time-series cross-validation (walk-forward, not k-fold) for
    hyperparameter selection to avoid leakage across the chronological split.
  - Feature importance / SHAP analysis to sanity-check the model isn't
    keying off a synthetic-data artifact.
  - Only proceed once a genuinely larger, real dataset is obtainable.
"""


class MLModelStub:
    """Deliberately unimplemented. Calling fit()/predict_proba() raises,
    so that `python main.py --backtest ml` fails loudly rather than silently
    producing meaningless results from an undersized/synthetic sample."""

    def __init__(self, *args, **kwargs):
        pass

    def fit(self, *args, **kwargs):
        raise NotImplementedError(
            "models/ml_models.py is a stub. Strategy C (ML models) is deliberately "
            "not implemented in this pass -- the available sample (7 days of "
            "SYNTHETIC demo data) is too small and not real Kalshi data, so fitting "
            "a random forest / gradient boosting model here would overfit noise and "
            "produce a misleading result. This is a TODO for the next phase after "
            "baseline review, ideally with real data. See README.md and "
            "results/final_report.md."
        )

    def predict_proba(self, *args, **kwargs):
        raise NotImplementedError("See fit() docstring -- Strategy C is not implemented yet.")
