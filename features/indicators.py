"""features/indicators.py -- standard technical indicators computed causally
(rolling windows only look backward from each row, never forward)."""

import numpy as np
import pandas as pd


def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def atr(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def realized_vol(returns, window):
    """Rolling std of log returns over `window` bars (causal, backward-looking)."""
    return returns.rolling(window, min_periods=max(2, window // 2)).std()


def vwap_rolling(df, window):
    """Rolling VWAP over `window` bars (causal)."""
    pv = (df["close"] * df["volume"]).rolling(window, min_periods=1).sum()
    v = df["volume"].rolling(window, min_periods=1).sum().replace(0, np.nan)
    return (pv / v).fillna(df["close"])
