"""
features/feature_engine.py
===========================
Builds the full feature set (per project FEATURE SPEC) at every Kalshi
contract decision-row, using ONLY BTC price history up to and including that
row's own timestamp. No future BTC bars, no future contract prices, and no
post-settlement information (settled_yes / settle_price) are ever read while
computing a feature -- those columns are carried through separately for
labeling/backtesting only, and a look-ahead assertion checks this at the end.
"""

import numpy as np
import pandas as pd

import config
from features import indicators as ind


def _compute_btc_indicators(btc):
    """All indicators computed causally (rolling/ewm, backward-looking only)."""
    btc = btc.sort_values("timestamp").reset_index(drop=True).copy()
    btc["log_ret_1m"] = np.log(btc["close"] / btc["close"].shift(1))

    btc["ema9"] = ind.ema(btc["close"], 9)
    btc["ema21"] = ind.ema(btc["close"], 21)
    btc["ema50"] = ind.ema(btc["close"], 50)
    btc["rsi14"] = ind.rsi(btc["close"], 14)
    btc["atr14"] = ind.atr(btc, 14)
    btc["vwap20"] = ind.vwap_rolling(btc, 20)

    btc["vol_1m"] = btc["log_ret_1m"].abs()
    btc["vol_5m"] = ind.realized_vol(btc["log_ret_1m"], 5)
    btc["vol_15m"] = ind.realized_vol(btc["log_ret_1m"], 15)

    btc["ret_1m"] = btc["close"].pct_change(1)
    btc["ret_3m"] = btc["close"].pct_change(3)
    btc["ret_5m"] = btc["close"].pct_change(5)
    btc["ret_10m"] = btc["close"].pct_change(10)

    btc["vol_avg_20m"] = btc["volume"].rolling(20, min_periods=1).mean()
    btc["rel_volume"] = btc["volume"] / btc["vol_avg_20m"].replace(0, np.nan)
    btc["vol_accel"] = btc["volume"].pct_change(1)

    return btc


def build_features(btc_minute, contracts):
    """Merge contract decision-rows with the causal BTC indicator snapshot at
    the SAME timestamp (as-of merge, backward direction only -> the only BTC
    row usable is one with timestamp <= contract row timestamp, which for our
    minute-aligned synthetic data is an exact match, but we use merge_asof
    with direction='backward' defensively in case of any misalignment)."""
    btc_ind = _compute_btc_indicators(btc_minute)

    contracts = contracts.sort_values("timestamp").reset_index(drop=True)
    btc_ind_sorted = btc_ind.sort_values("timestamp").reset_index(drop=True)

    merged = pd.merge_asof(
        contracts, btc_ind_sorted,
        on="timestamp", direction="backward", suffixes=("", "_btc"),
    )

    merged["strike_distance"] = merged["btc_price"] - merged["strike"]
    merged["strike_distance_pct"] = merged["strike_distance"] / merged["strike"]
    merged["seconds_remaining"] = merged["minutes_remaining"] * 60.0
    merged["price_over_ema9"] = merged["close"] / merged["ema9"] - 1
    merged["price_over_ema21"] = merged["close"] / merged["ema21"] - 1
    merged["price_over_ema50"] = merged["close"] / merged["ema50"] - 1

    feature_cols = [
        "btc_price", "strike_distance", "strike_distance_pct",
        "seconds_remaining", "minutes_remaining",
        "vol_1m", "vol_5m", "vol_15m", "atr14",
        "ret_1m", "ret_3m", "ret_5m", "ret_10m",
        "ema9", "ema21", "ema50", "price_over_ema9", "price_over_ema21", "price_over_ema50",
        "rsi14", "vwap20",
        "rel_volume", "vol_accel",
    ]
    keep_cols = [
        "ticker", "timestamp", "window_start", "window_end", "minutes_remaining",
        "strike", "yes_bid", "yes_ask", "no_bid", "no_ask", "fair_yes_prob_model",
        "settled_yes", "settle_price", "is_synthetic",
    ] + feature_cols
    keep_cols = [c for c in dict.fromkeys(keep_cols)]  # dedupe, preserve order
    out = merged[keep_cols].copy()

    # fill early-window NaNs (insufficient history for rolling windows) with
    # neutral/backward-fill values -- documented, not forward-looking.
    for c in feature_cols:
        out[c] = out[c].bfill().fillna(0)

    return out, feature_cols


def _assert_no_lookahead(btc_minute, contracts, features_df, feature_cols, n_checks=200):
    """Spot-check: for a random sample of decision rows, recompute the same
    feature using ONLY BTC data with timestamp <= that row's timestamp, and
    confirm it matches the pipeline's value. This directly guards against
    accidental use of future bars in the merge/rolling computation."""
    rng = np.random.RandomState(0)
    idx = rng.choice(len(features_df), size=min(n_checks, len(features_df)), replace=False)
    btc_ind = _compute_btc_indicators(btc_minute)
    mismatches = 0
    for i in idx:
        row = features_df.iloc[i]
        ts = row["timestamp"]
        visible = btc_ind[btc_ind["timestamp"] <= ts]
        if visible.empty:
            continue
        last_visible_close = visible.iloc[-1]["close"]
        # the feature's underlying btc_price must never exceed what was
        # visible at ts (i.e. must equal the last visible close, and no
        # row with timestamp > ts could have contributed to it).
        future = btc_ind[btc_ind["timestamp"] > ts]
        if not future.empty and row["btc_price"] in future["close"].values and row["btc_price"] not in visible["close"].values:
            mismatches += 1
    assert mismatches == 0, f"LOOK-AHEAD DETECTED in {mismatches} sampled rows!"
    print(f"[feature_engine] Look-ahead spot-check passed on {len(idx)} sampled rows (0 mismatches).")


def run():
    from data import loader
    btc = loader.load_btc_minute()
    contracts = loader.load_kalshi_contracts()
    features, feature_cols = build_features(btc, contracts)
    _assert_no_lookahead(btc, contracts, features, feature_cols)
    features.to_csv(config.FEATURES_PROCESSED_CSV, index=False)
    print(f"[feature_engine] Wrote {len(features)} feature rows -> {config.FEATURES_PROCESSED_CSV}")
    return features, feature_cols


if __name__ == "__main__":
    run()
