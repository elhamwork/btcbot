"""
The backtest engine.

Contracts are processed in strict chronological order of close time. Within a
contract, decision points are visited from the earliest (14 minutes remaining)
to the latest (1 minute). The FIRST decision point that clears every gate
becomes the trade; the rest of that contract is then skipped when
ONE_TRADE_PER_CONTRACT is set. This prevents a single contract from spawning
ten correlated trades.

Bankroll is updated only at settlement, and stake is sized from the bankroll
as it stood BEFORE the trade -- no future information reaches sizing.
"""

import numpy as np
import pandas as pd

import config
from backtest import execution


def run(panel, model, min_edge=None, position_fraction=None,
        entry_points=None, starting_bankroll=None, one_per_contract=None):
    min_edge = config.MIN_EDGE if min_edge is None else min_edge
    frac = config.POSITION_FRACTION if position_fraction is None else position_fraction
    entries = entry_points or config.ENTRY_MINUTES_REMAINING
    bankroll = config.STARTING_BANKROLL if starting_bankroll is None else starting_bankroll
    one_per = config.ONE_TRADE_PER_CONTRACT if one_per_contract is None else one_per_contract

    df = panel[panel["minutes_remaining"].isin(entries)].copy()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df["p_yes"] = model.predict_proba_yes(df)
    df["p_no"] = 1.0 - df["p_yes"]

    # Edge is measured against what we would actually PAY, not the mid.
    df["edge_yes"] = df["p_yes"] - df["yes_ask"]
    df["edge_no"] = df["p_no"] - df["no_ask"]

    # earliest decision first within each contract
    df = df.sort_values(["close_time", "ticker",
                         "minutes_remaining"], ascending=[True, True, False])

    trades = []
    skipped = {"no_edge": 0, "spread": 0, "price_band": 0,
               "volume": 0, "no_spread": 0, "bankrupt": 0}
    traded_tickers = set()

    for row in df.itertuples(index=False):
        r = row._asdict()
        if one_per and r["ticker"] in traded_tickers:
            continue

        if r["edge_yes"] >= r["edge_no"]:
            side, edge, market_p = "YES", r["edge_yes"], r["yes_ask"]
            model_p = r["p_yes"]
        else:
            side, edge, market_p = "NO", r["edge_no"], r["no_ask"]
            model_p = r["p_no"]

        if not np.isfinite(edge) or edge < min_edge:
            skipped["no_edge"] += 1
            continue

        ok, reason = execution.tradeable(r)
        if not ok:
            skipped[reason] += 1
            continue

        px = execution.entry_price(r, side)
        if px is None:
            skipped["no_spread"] += 1
            continue

        stake_target = bankroll * frac
        contracts = int(stake_target // px)
        if contracts < 1 or bankroll <= 0:
            skipped["bankrupt"] += 1
            continue

        cost = contracts * px
        fees = execution.fee(contracts, px)
        if cost + fees > bankroll:
            skipped["bankrupt"] += 1
            continue

        pnl, won = execution.settle(side, r["result"], contracts, cost, fees)
        bankroll_before = bankroll
        bankroll += pnl

        trades.append({
            "timestamp": r["ts"],
            "ticker": r["ticker"],
            "close_time": r["close_time"],
            "side": side,
            "minutes_remaining": r["minutes_remaining"],
            "entry_price": px,
            "contracts": contracts,
            "stake": cost,
            "fees": fees,
            "model_probability": model_p,
            "market_probability": market_p,
            "edge": edge,
            "p_yes": r["p_yes"],
            "y": r["y"],
            "result": r["result"],
            "won": int(won),
            "profit_loss": pnl,
            "bankroll_before": bankroll_before,
            "bankroll": bankroll,
            "spread": r["spread"],
            "mid": r["mid"],
            "rv_5m": r.get("rv_5m", np.nan),
            "dist_pct": r["dist_pct"],
        })
        traded_tickers.add(r["ticker"])

    tdf = pd.DataFrame(trades)
    sdf = pd.DataFrame([skipped])
    return tdf, sdf


def score_predictions(panel, model):
    """Probability quality on every decision row, independent of trading."""
    df = panel.copy()
    df["p_yes"] = model.predict_proba_yes(df)
    return df
