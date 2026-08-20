"""
Technical indicators over BTC 1-minute bars.

EVERY function here is causal: the value at row i uses only rows <= i.
Rolling windows are trailing, EMAs are recursive, and nothing is shifted
backwards. A row's value is what a trader would have known at that bar's
close -- never later.
"""

import numpy as np
import pandas as pd


def log_returns(close):
    return np.log(close).diff()


def realized_vol(close, window):
    """Trailing realized volatility of 1-minute log returns, in return units."""
    return log_returns(close).rolling(window, min_periods=window).std()


def ema(series, span):
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def rsi(close, period=14):
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    roll_up = up.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    roll_dn = dn.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = roll_up / roll_dn.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.fillna(50.0).where(close.notna())


def atr(high, low, close, period=14):
    prev = close.shift(1)
    tr = pd.concat([(high - low).abs(),
                    (high - prev).abs(),
                    (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rolling_vwap(close, volume, window):
    """Trailing VWAP. Not session-anchored -- a session anchor would need a
    definition of 'session' that 24/7 BTC does not have."""
    pv = (close * volume).rolling(window, min_periods=1).sum()
    v = volume.rolling(window, min_periods=1).sum()
    return pv / v.replace(0.0, np.nan)


def relative_volume(volume, window):
    avg = volume.rolling(window, min_periods=window).mean()
    return volume / avg.replace(0.0, np.nan)


def volume_acceleration(volume, window):
    """Short-run volume versus the longer trailing average."""
    fast = volume.rolling(max(window // 4, 2), min_periods=2).mean()
    slow = volume.rolling(window, min_periods=window).mean()
    return fast / slow.replace(0.0, np.nan)


def pct_return(close, minutes):
    return close.pct_change(minutes)
