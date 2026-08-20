"""analysis/breakdowns.py -- results sliced by edge bucket, time-remaining
bucket, market price bucket, volatility regime, and side."""

import numpy as np
import pandas as pd

from backtest.metrics import compute_metrics


def _bucket_summary(trades_df, bucket_col, starting_bankroll):
    rows = []
    for b, g in trades_df.groupby(bucket_col, observed=True):
        m = compute_metrics(g, starting_bankroll)
        m["bucket"] = str(b)
        m["n"] = len(g)
        rows.append(m)
    return pd.DataFrame(rows)


def by_edge_bucket(trades_df, starting_bankroll, bins=(0.05, 0.07, 0.10, 0.15, 1.0)):
    t = trades_df.copy()
    labels = [f"[{bins[i]:.2f},{bins[i+1]:.2f})" for i in range(len(bins) - 1)]
    t["edge_bucket"] = pd.cut(t["edge"], bins=bins, labels=labels, include_lowest=True)
    return _bucket_summary(t, "edge_bucket", starting_bankroll)


def by_time_remaining(trades_df, starting_bankroll):
    return _bucket_summary(trades_df, "minutes_remaining", starting_bankroll)


def by_market_price_bucket(trades_df, starting_bankroll, bins=(0, 0.2, 0.4, 0.6, 0.8, 1.0)):
    t = trades_df.copy()
    labels = [f"[{bins[i]:.1f},{bins[i+1]:.1f})" for i in range(len(bins) - 1)]
    t["price_bucket"] = pd.cut(t["market_prob_implied"], bins=bins, labels=labels, include_lowest=True)
    return _bucket_summary(t, "price_bucket", starting_bankroll)


def by_volatility_regime(trades_df, starting_bankroll):
    t = trades_df.copy()
    try:
        t["vol_regime"] = pd.qcut(t["vol_5m"], 3, labels=["low", "mid", "high"], duplicates="drop")
    except ValueError:
        t["vol_regime"] = "all"
    return _bucket_summary(t, "vol_regime", starting_bankroll)


def by_side(trades_df, starting_bankroll):
    return _bucket_summary(trades_df, "side", starting_bankroll)


def all_breakdowns(trades_df, starting_bankroll):
    if trades_df is None or len(trades_df) == 0:
        return {}
    return {
        "edge_bucket": by_edge_bucket(trades_df, starting_bankroll),
        "time_remaining": by_time_remaining(trades_df, starting_bankroll),
        "market_price_bucket": by_market_price_bucket(trades_df, starting_bankroll),
        "volatility_regime": by_volatility_regime(trades_df, starting_bankroll),
        "side": by_side(trades_df, starting_bankroll),
    }
