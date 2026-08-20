"""backtest/execution.py -- order pricing & fee model."""

import math
import config


def kalshi_fee(price, contracts):
    """Kalshi's published per-contract trading fee formula:
    fee = round_up(0.07 * C * P * (1-P)), applied per side (documented
    UNVERIFIED-LIVE in README because docs.kalshi.com is network-blocked in
    this environment; taken from general knowledge of Kalshi's public fee
    schedule)."""
    raw = config.KALSHI_FEE_RATE * contracts * price * (1 - price)
    if config.KALSHI_FEE_ROUND_TO_CENT:
        return math.ceil(raw * 100) / 100.0
    return raw


def entry_price(row, side):
    """No real order-book data is available (see README) -- entries transact
    at the modeled ask (yes_ask for YES, no_ask for NO), per config.USE_ASK_FOR_ENTRY."""
    if side == "YES":
        return row["yes_ask"]
    else:
        return row["no_ask"]


def settle_payout(row, side):
    """$1 per contract if the side won, else $0 (Kalshi binary settlement)."""
    won = (row["settled_yes"] == 1 and side == "YES") or (row["settled_yes"] == 0 and side == "NO")
    return 1.0 if won else 0.0
