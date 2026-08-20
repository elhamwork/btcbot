"""
Data collection is deliberately NOT part of this package.

The machine that can reach Kalshi is often not the machine running the
analysis (the research environment used to build this project had Kalshi and
every public crypto exchange blocked by its egress proxy). Collection
therefore lives in standalone, dependency-free scripts that can be handed to
any machine with ordinary internet access:

    fetch_15m.py         Kalshi KXBTC15M settled contracts + per-minute
                         yes_bid/yes_ask candlesticks. No account, no API key.
    fetch_btc_prices.py  BTC/USD 1-minute OHLCV from Coinbase, paginated over
                         the full window.
    discover_series.py   Probes Kalshi to identify which BTC series exist and
                         what their real contract cadence is.

Each writes into real_data/ and is standard-library only.

`python main.py --download` prints the current status of those files.
"""

import os

import config


def status():
    return {name: os.path.exists(path) for name, path in (
        ("contracts", config.CONTRACTS_CSV),
        ("candles", config.CANDLES_CSV),
        ("btc_1min", config.BTC_CSV),
    )}
