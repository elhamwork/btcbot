"""
backtest/engine.py
===================
Walk-forward backtest engine. For each contract (ticker), walks through its
decision points in chronological order (14m,12m,...,0.5m remaining) and, at
each point, uses ONLY that row's own features (already guaranteed causal by
feature_engine.py) to get a model probability, compares it to the market's
implied probability from the ask price, and enters a trade the first time
the edge clears MIN_EDGE for that contract (one position per contract, no
re-entry/averaging -- keeps trade attribution unambiguous per contract).

No look-ahead: settlement (settled_yes) is read ONLY at trade-close time to
compute PnL, never to decide whether/when to enter.
"""

import numpy as np
import pandas as pd

import config
from backtest import execution, portfolio
from models.baseline import BaselineModel


def chronological_split(features_df):
    """Split by contract window start time (not randomly), respecting
    TRAIN/VALIDATION/TEST fractions from config."""
    tickers_in_order = (
        features_df.drop_duplicates("ticker")[["ticker", "window_start"]]
        .sort_values("window_start")["ticker"].tolist()
    )
    n = len(tickers_in_order)
    n_train = int(n * config.TRAIN_FRACTION)
    n_val = int(n * config.VALIDATION_FRACTION)
    train_tickers = set(tickers_in_order[:n_train])
    val_tickers = set(tickers_in_order[n_train:n_train + n_val])
    test_tickers = set(tickers_in_order[n_train + n_val:])
    return train_tickers, val_tickers, test_tickers


def _available_entry_minutes(features_df):
    have = set(features_df["minutes_remaining"].unique())
    avail = [m for m in config.ENTRY_MINUTES_REMAINING if m in have]
    missing = [m for m in config.ENTRY_MINUTES_REMAINING if m not in have]
    if missing:
        print(f"[engine] NOTE: entry points {missing} not present in this minute-"
              f"resolution dataset (only whole-minute marks 1..15 exist here; "
              f"a 0.5-minute mark would require sub-minute data, which this "
              f"synthetic demo dataset does not include) -- documented limitation, "
              f"backtest proceeds using the available marks: {avail}.")
    return avail


def simulate(features_df, model, min_edge, position_fraction, starting_bankroll, tickers_filter=None):
    """Runs the walk-forward simulation over `tickers_filter` (or all
    tickers if None) and returns a Portfolio."""
    df = features_df if tickers_filter is None else features_df[features_df["ticker"].isin(tickers_filter)]
    entry_minutes = _available_entry_minutes(df)

    df = df.copy()
    df["model_prob_yes"] = model.predict_proba(df)

    pf = portfolio.Portfolio(starting_bankroll)
    positioned_tickers = set()

    for ticker, group in df.groupby("ticker", sort=False):
        group = group.sort_values("minutes_remaining", ascending=False)  # 15m remaining -> 0.5m remaining
        for m in entry_minutes:
            rows = group[group["minutes_remaining"] == m]
            if rows.empty or ticker in positioned_tickers:
                continue
            row = rows.iloc[0]
            p_model = row["model_prob_yes"]

            yes_ask, no_ask = row["yes_ask"], row["no_ask"]
            edge_yes = p_model - yes_ask
            edge_no = (1 - p_model) - no_ask

            side, price, edge = None, None, 0.0
            if edge_yes >= min_edge and edge_yes >= edge_no:
                side, price, edge = "YES", yes_ask, edge_yes
            elif edge_no >= min_edge:
                side, price, edge = "NO", no_ask, edge_no
            if side is None:
                continue

            stake_dollars = pf.bankroll * position_fraction
            if price <= 0 or not pf.can_afford(stake_dollars):
                continue
            n_contracts = stake_dollars / price
            entry_fee = execution.kalshi_fee(price, n_contracts)
            payout_per_contract = execution.settle_payout(row, side)
            gross_pnl = n_contracts * (payout_per_contract - price)
            exit_fee = execution.kalshi_fee(1.0 if payout_per_contract > 0 else 0.0, n_contracts) if payout_per_contract > 0 else 0.0
            pnl = gross_pnl - entry_fee - exit_fee

            pf.record_trade({
                "ticker": ticker,
                "timestamp": row["timestamp"],
                "minutes_remaining": m,
                "side": side,
                "entry_price": price,
                "model_prob": p_model,
                "market_prob_implied": price,
                "edge": edge,
                "n_contracts": n_contracts,
                "stake_dollars": stake_dollars,
                "fees": entry_fee + exit_fee,
                "won": bool(payout_per_contract > 0),
                "pnl": pnl,
                "strike": row["strike"],
                "btc_price_at_entry": row["btc_price"],
                "vol_5m": row["vol_5m"],
            })
            positioned_tickers.add(ticker)

    return pf


def run_baseline_backtest():
    from data import loader
    features = loader.load_features()
    train_t, val_t, test_t = chronological_split(features)
    print(f"[engine] Chronological split: train={len(train_t)} val={len(val_t)} test={len(test_t)} contracts.")

    model = BaselineModel().fit(features[features["ticker"].isin(train_t)])

    results = {}
    for split_name, tset in [("train", train_t), ("validation", val_t), ("test", test_t)]:
        pf = simulate(features, model, config.MIN_EDGE, config.DEFAULT_POSITION_SIZE_FRACTION,
                       config.STARTING_BANKROLL, tickers_filter=tset)
        results[split_name] = pf

    return model, results, features, (train_t, val_t, test_t)


if __name__ == "__main__":
    run_baseline_backtest()
