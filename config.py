"""
Central configuration for the BTC 15-minute Kalshi backtester.

IMPORTANT — DATA MODE
======================
This project was built inside a sandboxed research/execution environment whose
network egress proxy allowlists only a small set of domains (Anthropic infra,
PyPI, npm, GitHub, JSR, crates.io, Go proxy). All attempts to reach:
  - Kalshi's API (api.elections.kalshi.com, trading-api.kalshi.com,
    docs.kalshi.com) -> blocked by the egress proxy (HTTP 403 on CONNECT).
  - Binance, Coinbase, CoinGecko, Kraken, Bitstamp, Gemini, Yahoo Finance,
    stooq.com -> all blocked by the egress proxy (HTTP 403 on CONNECT).
  - Alpha Vantage's *intraday* crypto/equity endpoints (CRYPTO_INTRADAY,
    TIME_SERIES_INTRADAY) -> reachable, but gated as premium-tier and refuse
    to return data on the provided API key ("premium endpoint" rate_limit
    error on every interval tried: 1min, 5min, 15min, 60min).
were made and documented (see README.md "Data Sources & Limitations" and
results/reports/data_quality_report.md for the exact commands/errors).

The ONLY real, verifiable market data obtainable in this environment is
**daily** BTC/USD OHLCV via Alpha Vantage's DIGITAL_CURRENCY_DAILY endpoint
(free tier), covering 2010-07-17 through the present. That data IS used, and
IS real (see data/raw/_alphavantage_btc_daily_raw_response.json for the raw
API response actually retrieved).

Kalshi's 15-minute BTC markets require MINUTE-level BTC price data and real
Kalshi contract quotes/trades/settlements, neither of which is retrievable
here. Per the project's explicit instructions, we do NOT fabricate data and
present it as real. Instead, DATA_MODE below controls two honestly-labeled
paths:

  DATA_MODE = "real_daily_only"  -> only the real daily BTC series is loaded;
       no 15-minute backtest is possible from it alone (daily bars cannot
       support 14-minutes-to-0.5-minutes-remaining decision points).

  DATA_MODE = "synthetic_demo"   -> (used for the actual pipeline run) minute
       resolution BTC paths are SYNTHESIZED via a documented, seeded
       geometric Brownian motion calibrated to the REAL realized daily
       volatility/drift measured from the Alpha Vantage series, and Kalshi
       15-minute contract quotes are SYNTHESIZED from that synthetic path
       using a simple, documented, no-look-ahead probability model plus a
       modeled bid/ask spread. Every synthetic file is named with a
       "_SYNTHETIC" suffix, every row is tagged is_synthetic=True, and every
       report generated from this data prominently states, in bold, that
       results are NOT based on real Kalshi market data and must not be
       interpreted as evidence of a real trading edge.

This is a demo/placeholder mode whose sole purpose is to prove the pipeline
(download -> clean -> feature-engineer -> backtest -> report) is architected
correctly end-to-end, exactly as instructed when real data is unavailable.
"""

import os
from datetime import time

# ---------------------------------------------------------------------------
# Data mode
# ---------------------------------------------------------------------------
DATA_MODE = os.environ.get("BTCBOT_DATA_MODE", "synthetic_demo")  # or "real_daily_only"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
REPORTS_DIR = os.path.join(RESULTS_DIR, "reports")
CHARTS_DIR = os.path.join(RESULTS_DIR, "charts")
TRADES_DIR = os.path.join(RESULTS_DIR, "trades")

REFERENCE_DIR = os.path.join(BASE_DIR, "data", "reference")
# Real data actually fetched once via the Alpha Vantage MCP tool during this
# project's research phase (no direct MCP-calling capability exists from a
# standalone python process in this environment), checked into the repo
# under data/reference/ (NOT gitignored, unlike data/raw/) so `--download`
# is reproducible without needing a live MCP session. See README.
ALPHAVANTAGE_DAILY_RAW_REFERENCE = os.path.join(REFERENCE_DIR, "alphavantage_btc_daily_raw_response.json")
ALPHAVANTAGE_DAILY_RAW = os.path.join(RAW_DIR, "_alphavantage_btc_daily_raw_response.json")
BTC_DAILY_REAL_CSV = os.path.join(RAW_DIR, "btc_daily_real.csv")
BTC_MINUTE_SYNTHETIC_CSV = os.path.join(RAW_DIR, "btc_1min_SYNTHETIC.csv")
KALSHI_CONTRACTS_SYNTHETIC_CSV = os.path.join(RAW_DIR, "kalshi_15min_contracts_SYNTHETIC.csv")

BTC_PROCESSED_CSV = os.path.join(PROCESSED_DIR, "btc_1min_cleaned.csv")
CONTRACTS_PROCESSED_CSV = os.path.join(PROCESSED_DIR, "kalshi_contracts_cleaned.csv")
FEATURES_PROCESSED_CSV = os.path.join(PROCESSED_DIR, "features.csv")

DATA_QUALITY_REPORT = os.path.join(REPORTS_DIR, "data_quality_report.md")
FINAL_REPORT = os.path.join(RESULTS_DIR, "final_report.md")

# ---------------------------------------------------------------------------
# Synthetic data generation parameters (ONLY used when DATA_MODE == synthetic_demo)
# ---------------------------------------------------------------------------
SYNTHETIC_RANDOM_SEED = 42
SYNTHETIC_START = "2026-08-13T00:00:00Z"   # 7 days of synthetic minute data (small sample)
SYNTHETIC_DAYS = 7
SYNTHETIC_MINUTE_INTERVAL_SECONDS = 60
# Bid/ask spread modeled around the fair YES probability, in probability points.
SYNTHETIC_SPREAD_CENTS = 0.02  # i.e. 2 cents wide market on a $0-$1 contract, typical of liquid Kalshi 15m markets

# ---------------------------------------------------------------------------
# Kalshi 15-minute market mechanics
# ---------------------------------------------------------------------------
CONTRACT_DURATION_MINUTES = 15
# Entry decision points, expressed as minutes-remaining-in-contract at which the
# strategy is allowed to evaluate/enter a trade. No look-ahead: only data with
# timestamp <= (window_close - minutes_remaining) may be used at each point.
ENTRY_MINUTES_REMAINING = [14, 12, 10, 8, 6, 5, 4, 3, 2, 1, 0.5]

# ---------------------------------------------------------------------------
# Kalshi fee schedule
# ---------------------------------------------------------------------------
# Per Kalshi's published general fee schedule (documented in README.md ->
# "Fee schedule" section; NOTE: could not be re-verified live in this
# environment because docs.kalshi.com is network-blocked here, so this is
# taken from Alpha's general knowledge of Kalshi's public fee schedule as of
# its knowledge cutoff and clearly flagged as UNVERIFIED-LIVE in README).
# Kalshi's standard trading fee formula: fee = round_up(0.07 * C * P * (1-P))
# per contract, where C = number of contracts, P = price paid (in dollars,
# 0 < P < 1). Applied on both entry and exit (maker rebates ignored here).
KALSHI_FEE_RATE = 0.07
KALSHI_FEE_ROUND_TO_CENT = True
FEE_SCHEDULE_VERIFIED_LIVE = False  # see README limitations section

# ---------------------------------------------------------------------------
# Strategy / execution assumptions
# ---------------------------------------------------------------------------
MIN_EDGE = 0.05                      # minimum model-vs-market edge required to trade
MIN_EDGE_SWEEP = [0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15]
POSITION_SIZE_FRACTIONS = [0.005, 0.01, 0.02, 0.05]   # fixed-fractional bankroll sizing options tested
DEFAULT_POSITION_SIZE_FRACTION = 0.01
STARTING_BANKROLL = 1000.0

# Execution price assumption: we only have last/mid trade-derived synthetic
# quotes (see limitation above) rather than a real limit order book, so YES
# entries transact at the synthetic yes_ask and NO entries at the synthetic
# no_ask (ask = fair_prob +/- half spread), documented in README.
USE_ASK_FOR_ENTRY = True

# ---------------------------------------------------------------------------
# Train / validation / test chronological split (fractions of *time*, not rows)
# ---------------------------------------------------------------------------
TRAIN_FRACTION = 0.6
VALIDATION_FRACTION = 0.2
TEST_FRACTION = 0.2

# ---------------------------------------------------------------------------
# Baseline model features (Strategy A: heuristic/logistic on minimal features)
# ---------------------------------------------------------------------------
BASELINE_FEATURES = ["strike_distance_pct", "minutes_remaining", "realized_vol_5m"]

RANDOM_SEED = 1337
