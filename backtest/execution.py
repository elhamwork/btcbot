"""
Execution assumptions. Deliberately pessimistic where there is doubt.

  * A YES purchase pays `yes_ask`. A NO purchase pays `1 - yes_bid`.
    We never assume a mid-price fill and never assume price improvement.
  * Optional fixed slippage is added on top of the quoted ask.
  * Kalshi's published fee formula is charged on entry.
  * Settlement pays $1 per winning contract, $0 per loser.
"""

import math

import config


def entry_price(row, side):
    """Cost per contract, including slippage. None if unquotable."""
    px = row["yes_ask"] if side == "YES" else row["no_ask"]
    if px is None or not (0.0 < px < 1.0):
        return None
    return min(px + config.SLIPPAGE, 0.99)


def fee(contracts, price):
    """Kalshi trading fee in dollars: ceil(rate * C * P * (1-P)) cents.

    UNVERIFIED-LIVE -- see config.FEE_SCHEDULE_VERIFIED_LIVE.
    """
    if not config.APPLY_FEES or contracts <= 0:
        return 0.0
    cents = math.ceil(config.FEE_RATE * contracts * price * (1.0 - price) * 100.0)
    return cents / 100.0


def tradeable(row):
    """Liquidity / sanity gates. Returns (ok, reason)."""
    if row["spread"] > config.MAX_SPREAD:
        return False, "spread"
    if not (config.MIN_PRICE <= row["mid"] <= config.MAX_PRICE):
        return False, "price_band"
    if config.MIN_VOLUME_FP and row.get("candle_volume", 0) < config.MIN_VOLUME_FP:
        return False, "volume"
    if row["yes_ask"] <= row["yes_bid"]:
        return False, "no_spread"
    return True, ""


def settle(side, result, contracts, cost_basis, fees):
    """Realised P&L in dollars for a settled position."""
    won = (side == "YES" and result == "yes") or (side == "NO" and result == "no")
    payout = contracts * 1.0 if won else 0.0
    return payout - cost_basis - fees, won
