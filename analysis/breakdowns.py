"""
Result breakdowns.

A single aggregate win rate hides everything interesting. These cuts are where
a strategy either shows structure or reveals itself as noise.
"""

import numpy as np
import pandas as pd

import config


def _agg(g):
    return pd.Series({
        "trades": len(g),
        "win_rate": g["won"].mean(),
        "net_profit": g["profit_loss"].sum(),
        "profit_per_trade": g["profit_loss"].mean(),
        "avg_edge": g["edge"].mean(),
        "avg_entry": g["entry_price"].mean(),
        "roi_on_turnover": (g["profit_loss"].sum() /
                            (g["stake"].sum() + g["fees"].sum())
                            if (g["stake"].sum() + g["fees"].sum()) else np.nan),
    })


def _by(trades, col):
    if trades.empty:
        return pd.DataFrame()
    out = trades.groupby(col, observed=True).apply(_agg, include_groups=False)
    return out.reset_index()


def by_edge(trades):
    if trades.empty:
        return pd.DataFrame()
    t = trades.copy()
    t["edge_bucket"] = pd.cut(t["edge"], config.EDGE_BUCKETS,
                              labels=config.EDGE_LABELS, include_lowest=True)
    return _by(t, "edge_bucket")


def by_time_remaining(trades):
    if trades.empty:
        return pd.DataFrame()
    t = trades.copy()
    t["time_bucket"] = pd.cut(t["minutes_remaining"], config.TIME_BUCKETS,
                              labels=config.TIME_LABELS, include_lowest=True)
    return _by(t, "time_bucket")


def by_price(trades):
    if trades.empty:
        return pd.DataFrame()
    t = trades.copy()
    t["price_bucket"] = pd.cut(t["entry_price"], config.PRICE_BUCKETS,
                               labels=config.PRICE_LABELS, include_lowest=True)
    return _by(t, "price_bucket")


def by_volatility(trades, train_vol=None):
    """Volatility regimes cut at TRAIN quantiles -- never at test quantiles,
    which would leak the test distribution into the bucketing."""
    if trades.empty or "rv_5m" not in trades:
        return pd.DataFrame()
    t = trades.copy()
    ref = train_vol if train_vol is not None else t["rv_5m"]
    qs = ref.quantile(config.VOL_REGIME_QUANTILES).tolist()
    edges = [-np.inf] + qs + [np.inf]
    t["vol_regime"] = pd.cut(t["rv_5m"], edges, labels=config.VOL_REGIME_LABELS)
    return _by(t, "vol_regime")


def by_side(trades):
    return _by(trades, "side") if not trades.empty else pd.DataFrame()


def by_entry_point(trades):
    return _by(trades, "minutes_remaining") if not trades.empty else pd.DataFrame()


def all_breakdowns(trades, train_vol=None):
    return {
        "edge": by_edge(trades),
        "time_remaining": by_time_remaining(trades),
        "market_price": by_price(trades),
        "volatility_regime": by_volatility(trades, train_vol),
        "side": by_side(trades),
        "entry_point": by_entry_point(trades),
    }
