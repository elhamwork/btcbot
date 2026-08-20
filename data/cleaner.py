"""
data/cleaner.py
================
Data-quality checks + cleaning for both the BTC price series and the Kalshi
contract series. Nothing is silently dropped: every removal/adjustment is
counted and written into results/reports/data_quality_report.md.

Checks implemented (per project spec):
  - missing timestamps / gaps
  - duplicate timestamps/rows
  - incorrect / non-monotonic strikes
  - impossible prices (negative, or > $1 for probability-priced Kalshi legs;
    negative/zero for BTC price)
  - missing settlements
  - gaps in BTC data
  - overlapping contracts (same ticker rows outside its own window)
  - bad expiration times (window_end <= window_start, or wrong duration)
  - timezone issues (non-UTC / unparsable timestamps)
"""

import os
import pandas as pd
import numpy as np

import config


def _log(lines, msg):
    print(f"[cleaner] {msg}")
    lines.append(msg)


def clean_btc_minute(df, lines):
    n0 = len(df)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    bad_ts = df["timestamp"].isna().sum()
    if bad_ts:
        _log(lines, f"BTC minute data: dropped {bad_ts} rows with unparsable/non-UTC timestamps.")
        df = df[df["timestamp"].notna()]

    dupes = df.duplicated(subset=["timestamp"]).sum()
    if dupes:
        _log(lines, f"BTC minute data: dropped {dupes} duplicate-timestamp rows (kept first).")
        df = df.drop_duplicates(subset=["timestamp"], keep="first")

    df = df.sort_values("timestamp").reset_index(drop=True)

    impossible = df[(df["close"] <= 0) | (df["open"] <= 0) | (df["high"] <= 0) | (df["low"] <= 0)]
    if len(impossible):
        _log(lines, f"BTC minute data: dropped {len(impossible)} rows with impossible (<=0) prices.")
        df = df.drop(impossible.index)

    # OHLC consistency: high must be >= max(open,close), low <= min(open,close)
    bad_ohlc = df[(df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))]
    if len(bad_ohlc):
        _log(lines, f"BTC minute data: found {len(bad_ohlc)} rows with inconsistent OHLC "
                     f"(high<max(open,close) or low>min(open,close)); clipped high/low to fix rather than drop.")
        df.loc[bad_ohlc.index, "high"] = df.loc[bad_ohlc.index, ["open", "close", "high"]].max(axis=1)
        df.loc[bad_ohlc.index, "low"] = df.loc[bad_ohlc.index, ["open", "close", "low"]].min(axis=1)

    # Gap detection (expected 1-minute cadence)
    diffs = df["timestamp"].diff().dropna()
    expected = pd.Timedelta(seconds=config.SYNTHETIC_MINUTE_INTERVAL_SECONDS)
    gaps = diffs[diffs > expected]
    if len(gaps):
        total_missing = int((gaps / expected).sum() - len(gaps))
        _log(lines, f"BTC minute data: found {len(gaps)} gaps totalling ~{total_missing} missing minute bars "
                     f"(NOT backfilled/fabricated -- left as real gaps).")
    else:
        _log(lines, "BTC minute data: no timestamp gaps detected (continuous minute cadence).")

    _log(lines, f"BTC minute data: {n0} raw rows -> {len(df)} cleaned rows.")
    return df


def clean_kalshi_contracts(df, lines):
    n0 = len(df)
    for col in ["timestamp", "window_start", "window_end"]:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    bad_ts = df[["timestamp", "window_start", "window_end"]].isna().any(axis=1).sum()
    if bad_ts:
        _log(lines, f"Kalshi contracts: dropped {bad_ts} rows with unparsable timestamps.")
        df = df[df[["timestamp", "window_start", "window_end"]].notna().all(axis=1)]

    dupes = df.duplicated(subset=["ticker", "timestamp"]).sum()
    if dupes:
        _log(lines, f"Kalshi contracts: dropped {dupes} duplicate (ticker,timestamp) rows.")
        df = df.drop_duplicates(subset=["ticker", "timestamp"], keep="first")

    # Impossible prices: Kalshi contracts are priced in probability space (0,1) i.e. 1c-99c.
    price_cols = ["yes_bid", "yes_ask", "no_bid", "no_ask"]
    impossible = df[(df[price_cols] < 0).any(axis=1) | (df[price_cols] > 1).any(axis=1)]
    if len(impossible):
        _log(lines, f"Kalshi contracts: dropped {len(impossible)} rows with impossible prices "
                     f"(negative, or >$1 on a $0-$1 contract).")
        df = df.drop(impossible.index)

    # Bad expiration / duration
    dur = (df["window_end"] - df["window_start"]).dt.total_seconds() / 60.0
    bad_dur = df[(df["window_end"] <= df["window_start"]) | (dur.round(3) != config.CONTRACT_DURATION_MINUTES)]
    if len(bad_dur):
        _log(lines, f"Kalshi contracts: dropped {len(bad_dur)} rows with bad expiration "
                     f"(window_end<=window_start or duration != {config.CONTRACT_DURATION_MINUTES}m).")
        df = df.drop(bad_dur.index)

    # Overlapping contracts: a row's timestamp must fall within its own [window_start, window_end)
    outside = df[(df["timestamp"] < df["window_start"]) | (df["timestamp"] >= df["window_end"])]
    if len(outside):
        _log(lines, f"Kalshi contracts: dropped {len(outside)} rows whose timestamp fell outside "
                     f"their own contract window (overlap/misalignment).")
        df = df.drop(outside.index)

    # Missing settlement
    missing_settle = df["settled_yes"].isna().sum()
    if missing_settle:
        _log(lines, f"Kalshi contracts: {missing_settle} rows missing settlement -- dropped "
                     f"(cannot backtest an unresolved contract).")
        df = df[df["settled_yes"].notna()]

    # Non-monotonic / incorrect strike within a single contract ticker (strike should be constant per window)
    strike_nunique = df.groupby("ticker")["strike"].nunique()
    bad_tickers = strike_nunique[strike_nunique > 1].index
    if len(bad_tickers):
        _log(lines, f"Kalshi contracts: {len(bad_tickers)} tickers had a non-constant strike within "
                     f"their own window -- dropped all rows for those tickers.")
        df = df[~df["ticker"].isin(bad_tickers)]

    df = df.sort_values(["ticker", "timestamp"]).reset_index(drop=True)
    _log(lines, f"Kalshi contracts: {n0} raw rows -> {len(df)} cleaned rows across {df['ticker'].nunique()} contracts.")
    return df


def run():
    os.makedirs(config.PROCESSED_DIR, exist_ok=True)
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    lines = []
    lines.append("# Data Quality Report\n")
    lines.append(f"Generated by `data/cleaner.py`. DATA_MODE = `{config.DATA_MODE}`.\n")
    lines.append(
        "**IMPORTANT: this report covers a SYNTHETIC demo dataset, not real Kalshi "
        "market data.** See README.md \"Data Sources & Limitations\" for why: Kalshi's "
        "API and every public crypto-exchange API tried were blocked by this "
        "environment's network egress policy, and Alpha Vantage's intraday endpoints "
        "are premium-gated on the available key. Only real DAILY BTC/USD data "
        "(data/raw/btc_daily_real.csv) was obtainable; everything at minute/15-minute "
        "resolution here is a documented, seeded, reproducible synthetic generation, "
        "clearly flagged `is_synthetic=True` in every row.\n"
    ) if config.DATA_MODE == "synthetic_demo" else None

    btc_raw_path = config.BTC_MINUTE_SYNTHETIC_CSV if config.DATA_MODE == "synthetic_demo" else config.BTC_DAILY_REAL_CSV
    kalshi_raw_path = config.KALSHI_CONTRACTS_SYNTHETIC_CSV

    lines.append("## BTC price data\n")
    btc = pd.read_csv(btc_raw_path)
    btc_clean = clean_btc_minute(btc, lines) if "timestamp" in btc.columns else btc
    btc_clean.to_csv(config.BTC_PROCESSED_CSV, index=False)

    lines.append("\n## Kalshi contract data\n")
    kalshi = pd.read_csv(kalshi_raw_path)
    kalshi_clean = clean_kalshi_contracts(kalshi, lines)
    kalshi_clean.to_csv(config.CONTRACTS_PROCESSED_CSV, index=False)

    lines.append("\n## Summary\n")
    lines.append(f"- BTC rows: {len(btc)} raw -> {len(btc_clean)} cleaned")
    lines.append(f"- Kalshi contract-rows: {len(kalshi)} raw -> {len(kalshi_clean)} cleaned")
    lines.append(f"- Distinct Kalshi contracts (windows): {kalshi_clean['ticker'].nunique()}")

    with open(config.DATA_QUALITY_REPORT, "w") as f:
        f.write("\n".join(str(l) for l in lines if l is not None) + "\n")
    print(f"[cleaner] Wrote {config.DATA_QUALITY_REPORT}")
    return btc_clean, kalshi_clean


if __name__ == "__main__":
    run()
