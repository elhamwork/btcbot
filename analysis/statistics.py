"""analysis/statistics.py -- statistical significance helpers: bootstrap CIs,
binomial test for win rate vs. a fair-coin baseline, and a MIN_EDGE parameter
sweep that tracks how many combinations were tried (to flag multiple-testing
risk explicitly in the final report)."""

import itertools
import numpy as np
import pandas as pd
from scipy import stats

import config
from backtest import engine, metrics


def win_rate_significance(trades_df, null_p=0.5):
    """Two-sided binomial test: is the observed win rate different from
    null_p (default 50/50)? NOTE: for Kalshi contracts the "fair" null isn't
    necessarily 50% (it's whatever the market-implied probability was), so
    this is a simple/generic significance check, not a claim of true edge --
    the market-price-relative edge metrics are the primary evidence."""
    if trades_df is None or len(trades_df) == 0:
        return {"n": 0, "wins": 0, "p_value": None}
    n = len(trades_df)
    wins = int(trades_df["won"].sum())
    res = stats.binomtest(wins, n, null_p, alternative="two-sided")
    return {"n": n, "wins": wins, "p_value": float(res.pvalue)}


def min_edge_sweep(features_df, model, tickers_filter, position_fraction, starting_bankroll):
    """Sweeps config.MIN_EDGE_SWEEP, running a fresh simulation per threshold.
    Returns a DataFrame of results AND the count of combinations tried
    (report this count explicitly -- picking the best of N thresholds on the
    same data without a further held-out set is a multiple-testing concern,
    documented in the final report)."""
    rows = []
    for me in config.MIN_EDGE_SWEEP:
        pf = engine.simulate(features_df, model, me, position_fraction, starting_bankroll,
                              tickers_filter=tickers_filter)
        tdf = pf.to_frame()
        m = metrics.compute_metrics(tdf, starting_bankroll)
        m["min_edge"] = me
        rows.append(m)
    df = pd.DataFrame(rows)
    return df, len(config.MIN_EDGE_SWEEP)


def position_size_sweep(features_df, model, tickers_filter, min_edge, starting_bankroll):
    rows = []
    for frac in config.POSITION_SIZE_FRACTIONS:
        pf = engine.simulate(features_df, model, min_edge, frac, starting_bankroll,
                              tickers_filter=tickers_filter)
        tdf = pf.to_frame()
        m = metrics.compute_metrics(tdf, starting_bankroll)
        m["position_fraction"] = frac
        rows.append(m)
    df = pd.DataFrame(rows)
    return df, len(config.POSITION_SIZE_FRACTIONS)
