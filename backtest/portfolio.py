"""Bankroll bookkeeping.

The engine updates the bankroll inline as trades settle in chronological
order; this module reconstructs the equity path for reporting. Sizing at
trade i uses `bankroll_before`, which is the bankroll after trades 1..i-1 and
nothing later -- future information never reaches a past sizing decision.
"""

import pandas as pd

import config


def equity_curve(trades, starting_bankroll=None):
    b0 = config.STARTING_BANKROLL if starting_bankroll is None else starting_bankroll
    if trades is None or trades.empty:
        return pd.DataFrame(columns=["close_time", "bankroll", "peak",
                                     "drawdown", "drawdown_pct"])
    t = trades.sort_values("close_time").reset_index(drop=True)
    eq = pd.DataFrame({
        "close_time": pd.concat(
            [pd.Series([t["close_time"].iloc[0]]), t["close_time"]],
            ignore_index=True),
        "bankroll": pd.concat([pd.Series([b0]), t["bankroll"]],
                              ignore_index=True),
    })
    eq["peak"] = eq["bankroll"].cummax()
    eq["drawdown"] = eq["bankroll"] - eq["peak"]
    eq["drawdown_pct"] = eq["drawdown"] / eq["peak"]
    return eq


def verify_causality(trades):
    """Assert each trade's stake came from the bankroll before it, not after."""
    if trades is None or trades.empty:
        return True, "no trades"
    t = trades.sort_values("close_time").reset_index(drop=True)
    prev = config.STARTING_BANKROLL
    for i, r in t.iterrows():
        if abs(r["bankroll_before"] - prev) > 1e-6:
            return False, "trade %d: bankroll_before=%.4f expected %.4f" % (
                i, r["bankroll_before"], prev)
        prev = r["bankroll"]
    return True, "ok"
