"""
Central configuration for the BTC 15-minute Kalshi backtester.

DATA
====
This project runs on REAL market data:

  * Kalshi series KXBTC15M -- the genuine BTC 15-minute binary series.
    One strike per event, set at spot when the contract opens, 96 contracts
    per day. Collected via the public (no-account) Kalshi REST API:
    settled contract metadata plus per-minute yes_bid / yes_ask candlesticks
    for every contract's full 15-minute life.

  * BTC/USD 1-minute OHLCV from Coinbase (public API).

Both cover 2026-08-06 -> 2026-08-20. See results/reports/data_quality_report.md
for the full audit and KNOWN LIMITATIONS.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REAL_DIR = os.path.join(BASE_DIR, "real_data")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
REPORTS_DIR = os.path.join(RESULTS_DIR, "reports")
CHARTS_DIR = os.path.join(RESULTS_DIR, "charts")
TRADES_DIR = os.path.join(RESULTS_DIR, "trades")

CONTRACTS_CSV = os.path.join(REAL_DIR, "kalshi_15m_contracts.csv")
CANDLES_CSV = os.path.join(REAL_DIR, "kalshi_15m_candlesticks.csv")
BTC_CSV = os.path.join(REAL_DIR, "btc_1min.csv")

CLEAN_CONTRACTS = os.path.join(PROCESSED_DIR, "contracts_clean.parquet")
CLEAN_CANDLES = os.path.join(PROCESSED_DIR, "candles_clean.parquet")
CLEAN_BTC = os.path.join(PROCESSED_DIR, "btc_1min_clean.parquet")
PANEL = os.path.join(PROCESSED_DIR, "decision_panel.parquet")

for _d in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR, CHARTS_DIR, TRADES_DIR):
    os.makedirs(_d, exist_ok=True)

SERIES_TICKER = "KXBTC15M"

# ---------------------------------------------------------------------------
# Decision points -- minutes remaining before contract close.
# Candles are 1-minute, so 0.5 minutes is NOT observable. Documented, not faked.
# ---------------------------------------------------------------------------
ENTRY_MINUTES_REMAINING = [14, 12, 10, 8, 6, 5, 4, 3, 2, 1]
UNAVAILABLE_ENTRY_POINTS = [0.5]  # would require sub-minute data

# ---------------------------------------------------------------------------
# Chronological split (never random -- this is time series)
# ---------------------------------------------------------------------------
TRAIN_FRAC = 0.60
VALIDATION_FRAC = 0.20
# remainder is the held-out TEST set, untouched while tuning

# ---------------------------------------------------------------------------
# Strategy / execution assumptions
# ---------------------------------------------------------------------------
MIN_EDGE = 0.05
MIN_EDGE_SWEEP = [0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15]

STARTING_BANKROLL = 1000.0
POSITION_FRACTION = 0.01
POSITION_FRACTION_SWEEP = [0.005, 0.01, 0.02, 0.05]

# Execution: we BUY, so we pay the ask.
#   YES costs yes_ask
#   NO  costs (1 - yes_bid)     [selling YES at the bid == buying NO]
# No mid-price fills. No assumption of price improvement.
MAX_SPREAD = 0.05          # skip if ask-bid wider than this
MIN_PRICE = 0.05           # avoid lottery tickets and near-certainties
MAX_PRICE = 0.95
MIN_VOLUME_FP = 0.0        # candle volume filter (0 = off; data has 0% empty)
SLIPPAGE = 0.00            # extra cents paid beyond the quoted ask
ONE_TRADE_PER_CONTRACT = True

# Kalshi trading fee: ceil(0.07 * contracts * P * (1-P)) in cents, charged on
# entry. UNVERIFIED-LIVE: docs.kalshi.com was unreachable from the build
# environment, so this comes from Kalshi's published general fee formula and
# has not been confirmed against the live fee schedule. Settlement is assumed
# free. Raise FEE_RATE to stress-test.
FEE_RATE = 0.07
FEE_SCHEDULE_VERIFIED_LIVE = False
APPLY_FEES = True

# ---------------------------------------------------------------------------
# Feature engine
# ---------------------------------------------------------------------------
VOL_WINDOWS = [1, 5, 15]
MOMENTUM_WINDOWS = [1, 3, 5, 10]
EMA_SPANS = [9, 21, 50]
RSI_PERIOD = 14
ATR_PERIOD = 14
REL_VOLUME_WINDOW = 20
WARMUP_MINUTES = 60        # BTC history required before a decision is usable

# Volatility regime cut points (quantiles of realized 5m vol, fit on TRAIN only)
VOL_REGIME_QUANTILES = [0.25, 0.50, 0.75]
VOL_REGIME_LABELS = ["LOW", "NORMAL", "HIGH", "EXTREME"]

# ---------------------------------------------------------------------------
# Feature sets per strategy
# ---------------------------------------------------------------------------
FEATURES_BASELINE = [        # Strategy A: distance, time, volatility only
    "dist_pct", "minutes_remaining", "rv_5m", "z_score",
]

FEATURES_TECHNICAL = FEATURES_BASELINE + [   # Strategy B
    "ret_1m", "ret_3m", "ret_5m", "ret_10m",
    "ema9_rel", "ema21_rel", "ema50_rel",
    "rsi", "vwap_rel", "rel_volume", "volume_accel",
    "rv_1m", "rv_15m", "atr_pct",
]

# ---------------------------------------------------------------------------
# Analysis buckets
# ---------------------------------------------------------------------------
EDGE_BUCKETS = [0.0, 0.05, 0.075, 0.10, 0.15, 1.0]
EDGE_LABELS = ["0-5%", "5-7.5%", "7.5-10%", "10-15%", "15%+"]

TIME_BUCKETS = [0, 1, 3, 5, 8, 12, 15]
TIME_LABELS = ["0-1m", "1-3m", "3-5m", "5-8m", "8-12m", "12-15m"]

PRICE_BUCKETS = [0.0, .10, .20, .30, .40, .50, .60, .70, .80, .90, 1.0]
PRICE_LABELS = ["0-10c", "10-20c", "20-30c", "30-40c", "40-50c",
                "50-60c", "60-70c", "70-80c", "80-90c", "90-100c"]

BOOTSTRAP_SAMPLES = 10000
RANDOM_SEED = 7

# ---------------------------------------------------------------------------
# Overfitting ledger -- every configuration evaluated gets counted.
# ---------------------------------------------------------------------------
SEARCH_LOG = os.path.join(REPORTS_DIR, "search_log.csv")

# ---------------------------------------------------------------------------
# BTC bar clock convention
# ---------------------------------------------------------------------------
# Coinbase labels each 1-minute bucket at its START. Adding one minute
# re-labels bars to BAR-END, so the row labelled T is the bar that ended at T
# and its close is the last price observable at T. Without this the feature
# engine reads a price one minute into the future.
# data/cleaner.py::_check_alignment verifies this against settlement and
# strike-at-open and fails loudly if it is wrong.
BTC_BAR_SHIFT_MINUTES = 1
