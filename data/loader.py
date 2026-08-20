"""Load the real Kalshi KXBTC15M + Coinbase BTC datasets."""

import os
import pandas as pd

import config


def load_raw_contracts():
    df = pd.read_csv(config.CONTRACTS_CSV)
    for col in ("open_time", "close_time", "expiration_time", "settlement_ts"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


def load_raw_candles():
    df = pd.read_csv(config.CANDLES_CSV)
    df["ts"] = pd.to_datetime(df["end_period_ts"], unit="s", utc=True)
    return df


def load_raw_btc():
    """
    BTC 1-minute bars, RE-LABELLED TO BAR-END.

    Coinbase timestamps each bucket at its START: the bar labelled T covers
    [T, T+60s), so its `close` is the price at T+60s. Joining a decision made
    at T to that row would hand the model a price one minute in the future --
    a full minute of look-ahead, and near-perfect information at the 1-minute
    decision point.

    Shifting the label forward by one minute makes the row labelled T mean
    "the bar that ENDED at T", whose close is the last price observable at T.
    Every rolling indicator built on this frame is then causal at T.

    Verified against two independent anchors (see
    data/cleaner.py::_check_alignment):
      * the strike, which Kalshi fixes at spot when the contract opens
      * the settled result, which depends on spot at expiry
    Both favour this convention decisively.
    """
    df = pd.read_csv(config.BTC_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp"] = df["timestamp"] + pd.Timedelta(minutes=config.BTC_BAR_SHIFT_MINUTES)
    df = df.sort_values("timestamp").reset_index(drop=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _require(path, what):
    if not os.path.exists(path):
        raise SystemExit(
            "Missing %s (%s).\nRun `python main.py --prepare-data` first."
            % (what, path))


def load_clean():
    """Cleaned contracts / candles / BTC produced by --prepare-data."""
    _require(config.CLEAN_CONTRACTS, "cleaned contracts")
    return (pd.read_parquet(config.CLEAN_CONTRACTS),
            pd.read_parquet(config.CLEAN_CANDLES),
            pd.read_parquet(config.CLEAN_BTC))


def load_panel():
    """The decision-point panel: one row per (contract, minutes_remaining)."""
    _require(config.PANEL, "decision panel")
    return pd.read_parquet(config.PANEL)


def chronological_split(df, time_col="close_time"):
    """Split by time, never randomly. Returns (train, validation, test)."""
    df = df.sort_values(time_col).reset_index(drop=True)
    cuts = sorted(df[time_col].unique())
    n = len(cuts)
    t_end = cuts[int(n * config.TRAIN_FRAC)]
    v_end = cuts[int(n * (config.TRAIN_FRAC + config.VALIDATION_FRAC))]
    train = df[df[time_col] <= t_end]
    val = df[(df[time_col] > t_end) & (df[time_col] <= v_end)]
    test = df[df[time_col] > v_end]
    return train.copy(), val.copy(), test.copy()
