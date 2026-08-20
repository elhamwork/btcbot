"""data/loader.py -- thin helpers to load cleaned/processed data into pandas."""

import pandas as pd
import config


def load_btc_minute():
    df = pd.read_csv(config.BTC_PROCESSED_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values("timestamp").reset_index(drop=True)


def load_kalshi_contracts():
    df = pd.read_csv(config.CONTRACTS_PROCESSED_CSV)
    for c in ["timestamp", "window_start", "window_end"]:
        df[c] = pd.to_datetime(df[c], utc=True)
    return df.sort_values(["ticker", "timestamp"]).reset_index(drop=True)


def load_features():
    df = pd.read_csv(config.FEATURES_PROCESSED_CSV)
    for c in ["timestamp", "window_start", "window_end"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True)
    return df
