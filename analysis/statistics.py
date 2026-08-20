"""
Statistical significance.

Making money over 14 days is not evidence of an edge. These routines ask
whether the observed result is distinguishable from luck.
"""

import numpy as np
import pandas as pd
from scipy import stats

import config


def bootstrap_ci(values, statistic=np.mean, n=None, alpha=0.05, seed=None):
    values = np.asarray(pd.Series(values).dropna(), dtype=float)
    if len(values) < 2:
        return {"point": float(values[0]) if len(values) else np.nan,
                "low": np.nan, "high": np.nan, "n": len(values)}
    n = n or config.BOOTSTRAP_SAMPLES
    rng = np.random.default_rng(config.RANDOM_SEED if seed is None else seed)
    idx = rng.integers(0, len(values), size=(n, len(values)))
    dist = statistic(values[idx], axis=1)
    return {
        "point": float(statistic(values)),
        "low": float(np.percentile(dist, 100 * alpha / 2)),
        "high": float(np.percentile(dist, 100 * (1 - alpha / 2))),
        "n": len(values),
    }


def win_rate_ci(trades, alpha=0.05):
    return bootstrap_ci(trades["won"].astype(float), np.mean, alpha=alpha)


def roi_ci(trades, starting_bankroll=None, alpha=0.05):
    """Bootstrap ROI by resampling trade P&L (order-independent)."""
    b0 = config.STARTING_BANKROLL if starting_bankroll is None else starting_bankroll
    pnl = trades["profit_loss"].to_numpy(float)
    if len(pnl) < 2:
        return {"point": np.nan, "low": np.nan, "high": np.nan, "n": len(pnl)}
    rng = np.random.default_rng(config.RANDOM_SEED)
    idx = rng.integers(0, len(pnl), size=(config.BOOTSTRAP_SAMPLES, len(pnl)))
    dist = pnl[idx].sum(axis=1) / b0
    return {
        "point": float(pnl.sum() / b0),
        "low": float(np.percentile(dist, 2.5)),
        "high": float(np.percentile(dist, 97.5)),
        "n": len(pnl),
    }


def profit_per_trade_test(trades):
    """One-sample t-test: is mean P&L per trade different from zero?"""
    pnl = trades["profit_loss"].to_numpy(float)
    if len(pnl) < 3:
        return {"note": "too few trades"}
    t, p = stats.ttest_1samp(pnl, 0.0)
    return {"mean": float(pnl.mean()), "t_stat": float(t), "p_value": float(p),
            "n": len(pnl)}


def win_rate_vs_breakeven(trades):
    """
    A binomial test against the win rate implied by the prices actually paid.

    Paying an average of P cents means breaking even requires winning P% of
    the time. Beating 50% is irrelevant; beating the paid price is the bar.
    """
    if trades.empty:
        return {"note": "no trades"}
    breakeven = float(trades["entry_price"].mean())
    wins = int(trades["won"].sum())
    n = len(trades)
    res = stats.binomtest(wins, n, breakeven, alternative="greater")
    return {
        "observed_win_rate": wins / n,
        "breakeven_win_rate": breakeven,
        "excess": wins / n - breakeven,
        "p_value": float(res.pvalue),
        "n": n,
    }


def edge_monotonicity(trades):
    """
    Does a larger predicted edge actually produce a better outcome?

    Spearman correlation between predicted edge and realised P&L per dollar
    staked. A real edge should trend positive; noise will not.
    """
    if len(trades) < 10:
        return {"note": "too few trades"}
    per_dollar = trades["profit_loss"] / trades["stake"].replace(0, np.nan)
    d = pd.DataFrame({"edge": trades["edge"], "ret": per_dollar}).dropna()
    if len(d) < 10:
        return {"note": "too few trades"}
    rho, p = stats.spearmanr(d["edge"], d["ret"])
    return {"spearman_rho": float(rho), "p_value": float(p), "n": len(d)}


def summarize(trades, label=""):
    if trades is None or trades.empty:
        return {"label": label, "note": "no trades"}
    return {
        "label": label,
        "win_rate_ci": win_rate_ci(trades),
        "roi_ci": roi_ci(trades),
        "profit_per_trade_test": profit_per_trade_test(trades),
        "vs_breakeven": win_rate_vs_breakeven(trades),
        "edge_monotonicity": edge_monotonicity(trades),
    }
