"""
Build the decision panel: one row per (contract, minutes_remaining).

LOOK-AHEAD DISCIPLINE
=====================
Indicators are computed once over the full BTC series, then a decision at
timestamp T is joined to the BTC row at exactly T. Because every indicator in
indicators.py is causal, the BTC row at T contains only information from bars
<= T.

The contract-side quote at a decision is the candle whose period ENDS at T,
i.e. the last fully observed minute. Nothing from later in the contract's life
touches the row. The label is the contract's settled result, which is used for
scoring only -- never as an input.

verify_no_lookahead() re-derives a sample of rows from a truncated history and
asserts the values match, so the discipline is tested rather than asserted.
"""

import numpy as np
import pandas as pd

import config
from features import indicators as ind


# ---------------------------------------------------------------------------
# BTC-side features
# ---------------------------------------------------------------------------

def build_btc_features(btc):
    df = btc.sort_values("timestamp").reset_index(drop=True).copy()
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    for w in config.VOL_WINDOWS:
        df["rv_%dm" % w] = ind.realized_vol(c, w if w > 1 else 2)

    for w in config.MOMENTUM_WINDOWS:
        df["ret_%dm" % w] = ind.pct_return(c, w)

    for span in config.EMA_SPANS:
        e = ind.ema(c, span)
        df["ema%d" % span] = e
        df["ema%d_rel" % span] = c / e - 1.0

    df["rsi"] = ind.rsi(c, config.RSI_PERIOD)
    df["atr"] = ind.atr(h, l, c, config.ATR_PERIOD)
    df["atr_pct"] = df["atr"] / c

    df["vwap"] = ind.rolling_vwap(c, v, config.REL_VOLUME_WINDOW)
    df["vwap_rel"] = c / df["vwap"] - 1.0

    df["rel_volume"] = ind.relative_volume(v, config.REL_VOLUME_WINDOW)
    df["volume_accel"] = ind.volume_acceleration(v, config.REL_VOLUME_WINDOW)

    df["btc_price"] = c
    df["bars_seen"] = np.arange(len(df))
    return df


BTC_FEATURE_COLS = None


def _btc_cols(bf):
    global BTC_FEATURE_COLS
    if BTC_FEATURE_COLS is None:
        BTC_FEATURE_COLS = [c for c in bf.columns
                            if c not in ("timestamp", "open", "high", "low",
                                         "close", "volume")]
    return BTC_FEATURE_COLS


# ---------------------------------------------------------------------------
# Decision panel
# ---------------------------------------------------------------------------

def build_panel(contracts, candles, btc):
    bf = build_btc_features(btc)
    bf_idx = bf.set_index("timestamp")

    cand = candles.copy()
    cand["ts"] = pd.to_datetime(cand["ts"], utc=True)

    con = contracts[["ticker", "open_time", "close_time", "floor_strike",
                     "result", "volume_fp", "open_interest_fp"]].copy()

    m = cand.merge(con, on="ticker", how="inner")

    # minutes remaining at the close of this candle's minute
    m["minutes_remaining"] = (
        (m["close_time"] - m["ts"]).dt.total_seconds() / 60.0).round().astype(int)
    m = m[m["minutes_remaining"].isin(config.ENTRY_MINUTES_REMAINING)]

    # join BTC state as of exactly this timestamp
    joined = m.join(bf_idx[_btc_cols(bf)], on="ts")

    # require enough BTC warm-up for indicators to be defined
    joined = joined[joined["bars_seen"] >= config.WARMUP_MINUTES]

    # ---- contract-relative features ------------------------------------
    S = joined["btc_price"]
    K = joined["floor_strike"]
    joined["dist_abs"] = S - K
    joined["dist_pct"] = S / K - 1.0
    joined["seconds_remaining"] = joined["minutes_remaining"] * 60.0

    # z-score under a driftless GBM over the remaining window: the natural
    # coordinate for "will spot finish above the strike". Built from the three
    # baseline inputs (distance, time, volatility) -- no extra information.
    T = joined["minutes_remaining"].clip(lower=1e-9)
    sigma = joined["rv_5m"].replace(0.0, np.nan)
    joined["z_score"] = np.log(S / K) / (sigma * np.sqrt(T))
    joined["z_score"] = joined["z_score"].replace([np.inf, -np.inf], np.nan)

    # ---- market quotes --------------------------------------------------
    joined["yes_bid"] = joined["yes_bid_close_dollars"]
    joined["yes_ask"] = joined["yes_ask_close_dollars"]
    joined["no_bid"] = 1.0 - joined["yes_ask"]
    joined["no_ask"] = 1.0 - joined["yes_bid"]
    joined["mid"] = (joined["yes_bid"] + joined["yes_ask"]) / 2.0
    joined["spread"] = joined["yes_ask"] - joined["yes_bid"]
    joined["candle_volume"] = joined["volume_fp_x"] if "volume_fp_x" in joined \
        else joined["volume_fp"]

    # ---- label (scoring only) -------------------------------------------
    joined["y"] = (joined["result"] == "yes").astype(int)

    keep = ([
        "ticker", "ts", "close_time", "open_time", "minutes_remaining",
        "seconds_remaining", "floor_strike", "btc_price", "dist_abs",
        "dist_pct", "z_score", "yes_bid", "yes_ask", "no_bid", "no_ask",
        "mid", "spread", "candle_volume", "open_interest_fp", "y", "result",
    ] + [c for c in _btc_cols(bf) if c not in ("btc_price", "bars_seen")])

    panel = joined[[c for c in keep if c in joined.columns]].copy()
    panel = panel.sort_values(["close_time", "minutes_remaining"]).reset_index(drop=True)
    return panel


# ---------------------------------------------------------------------------
# Look-ahead verification
# ---------------------------------------------------------------------------

def verify_no_lookahead(btc, n_samples=200, seed=7):
    """
    Recompute features using ONLY history up to T and compare with the
    full-series computation. Any indicator that peeked at future bars would
    disagree. Returns (n_checked, n_mismatched, worst_abs_diff).
    """
    rng = np.random.default_rng(seed)
    full = build_btc_features(btc)
    cols = [c for c in _btc_cols(full) if c != "bars_seen"]

    idx = rng.choice(np.arange(config.WARMUP_MINUTES + 60, len(full)),
                     size=min(n_samples, len(full) - config.WARMUP_MINUTES - 60),
                     replace=False)

    mismatched, worst = 0, 0.0
    for i in idx:
        truncated = build_btc_features(btc.iloc[: i + 1])
        a = full.iloc[i][cols].astype(float)
        b = truncated.iloc[-1][cols].astype(float)
        both = a.notna() & b.notna()
        if not both.any():
            continue
        diff = (a[both] - b[both]).abs()
        scale = a[both].abs().clip(lower=1e-9)
        rel = (diff / scale).max()
        worst = max(worst, float(rel))
        if rel > 1e-8:
            mismatched += 1
    return len(idx), mismatched, worst
