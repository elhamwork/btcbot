# BTC 15-Minute Kalshi Strategy Backtester

A research-grade backtesting pipeline to determine, from historical data and
without look-ahead bias, whether a simple BTC-15-minute Kalshi strategy shows
a statistically meaningful edge. **This is not a live trading bot.**

## READ THIS FIRST: Data Sources & Limitations

This project was built inside a sandboxed execution environment whose network
egress proxy allowlists only a small set of domains. Every attempt to reach
real market-data sources was documented, not skipped:

| Source tried | Result |
|---|---|
| Kalshi API (`api.elections.kalshi.com`, `trading-api.kalshi.com`, `docs.kalshi.com`) | **Blocked** — HTTP 403 on the proxy CONNECT tunnel for all three domains. Not an auth failure — a network policy block. |
| Binance, Coinbase, CoinGecko, Kraken, Bitstamp, Gemini | **Blocked** — same HTTP 403 CONNECT pattern for every domain. |
| Yahoo Finance, stooq.com | **Blocked** — same. |
| Alpha Vantage MCP — `CRYPTO_INTRADAY`, `TIME_SERIES_INTRADAY` (1min/5min/15min/60min, crypto and equity symbols both tried) | **Reachable but refused**: every call returned `{"error":{"type":"rate_limit","message":"...premium endpoint..."}}`. Gated behind Alpha Vantage's paid tier; not available on the key configured here. |
| Alpha Vantage MCP — `DIGITAL_CURRENCY_DAILY` | **Works.** Real daily BTC/USD OHLCV, 2010-07-17 through present (free tier). |

**Consequence:** no real Kalshi contract data, and no real intraday (minute-
resolution or finer) BTC price data, could be obtained in this environment.
The *only* real, verifiable market data obtainable was **daily** BTC/USD
OHLCV.

Per this project's explicit fallback instructions ("never fabricate data and
present it as real; if genuinely unobtainable, build the pipeline correctly
and demonstrate it against whatever real data IS obtainable, using clearly-
labeled synthetic data only as an honestly-flagged placeholder"), this
project runs in **`DATA_MODE = "synthetic_demo"`** (see `config.py`):

1. **Real** daily BTC/USD data is downloaded and saved untouched:
   `data/raw/btc_daily_real.csv` (raw API response also kept at
   `data/raw/_alphavantage_btc_daily_raw_response.json`).
2. That real series is used *only* to measure real daily drift/volatility,
   which calibrates a **seeded, reproducible geometric Brownian motion**
   that generates a **SYNTHETIC** minute-resolution BTC price path:
   `data/raw/btc_1min_SYNTHETIC.csv`.
3. **SYNTHETIC** Kalshi-style 15-minute up/down contract quotes are derived
   from that synthetic path using a documented, no-look-ahead
   Brownian-barrier probability formula plus a modeled bid/ask spread:
   `data/raw/kalshi_15min_contracts_SYNTHETIC.csv`.

Every synthetic row carries `is_synthetic=True`; every synthetic filename
carries a `_SYNTHETIC` suffix; every report this pipeline produces
(`results/reports/data_quality_report.md`, `results/final_report.md`) states
this in bold, up front.

**No numeric result in this repository (win rate, ROI, edge, etc.) is
evidence about real Kalshi markets.** The sole purpose of this pass is to
prove the pipeline — download → clean → feature-engineer → walk-forward
backtest → report — is architected and wired correctly end-to-end, ready to
be re-pointed at real data (`DATA_MODE = "real_daily_only"` plus a real
Kalshi/intraday-BTC downloader) the moment a network environment that can
reach those APIs is available.

### Execution & fee assumptions (also documented in `config.py`)

- No real limit-order-book data exists (real or synthetic) here — YES
  entries transact at the modeled `yes_ask`, NO entries at the modeled
  `no_ask` (fair probability ± half a small modeled spread).
- Kalshi's fee formula used (`fee = ceil(0.07 * contracts * price * (1-price))`
  per side) is taken from general knowledge of Kalshi's public fee schedule.
  **It is UNVERIFIED-LIVE** in this environment, since `docs.kalshi.com` was
  network-blocked and could not be re-checked (`config.FEE_SCHEDULE_VERIFIED_LIVE
  = False`). Verify against Kalshi's current published fee schedule before
  relying on this for anything beyond architecture demonstration.
- Entry decision points requested were minutes-remaining
  `[14,12,10,8,6,5,4,3,2,1,0.5]`. The `0.5` mark is **not available** at
  minute resolution in this synthetic dataset (would require sub-minute
  bars, which were not generated) — the backtest engine logs this and
  proceeds with the 10 whole-minute marks that do exist.

## Project structure

```
config.py                    All configurable assumptions (fees, edge, sizing, entry points, paths)
main.py                      CLI entry point
data/
  downloader.py               Fetches real daily BTC data + generates labeled synthetic minute/contract data
  cleaner.py                  Data-quality checks + cleaning -> data_quality_report.md
  loader.py                   Load processed CSVs into pandas
  raw/                        Raw downloaded/generated data (gitignored)
  processed/                  Cleaned data + engineered features (gitignored)
features/
  indicators.py                EMA/RSI/ATR/VWAP/realized-vol helpers (all causal/backward-looking)
  feature_engine.py            Builds the full feature set per decision row + look-ahead spot-check
models/
  baseline.py                  Strategy A: heuristic/logistic on {strike distance, time remaining, vol}
  logistic.py                  Strategy B scaffolding: full-feature calibrated logistic regression (not run yet)
  ml_models.py                 Strategy C: stub only, raises NotImplementedError (sample too small / synthetic)
backtest/
  engine.py                    Walk-forward simulation, chronological train/val/test split
  execution.py                 Entry pricing + Kalshi fee model
  portfolio.py                 Bankroll/trade/equity tracking
  metrics.py                   Win rate, ROI, drawdown, streaks, profit factor, Brier score, log loss, bootstrap CI
analysis/
  breakdowns.py                Results by edge/time/price/vol-regime/side
  statistics.py                Bootstrap CIs, binomial significance test, MIN_EDGE + position-size sweeps
  charts.py                    matplotlib charts -> results/charts/
  report_builder.py            Orchestrates the above -> results/final_report.md
results/
  reports/                     data_quality_report.md, breakdown CSVs, sweep CSVs
  charts/                      equity curve, drawdown, edge-vs-return, calibration, results-by-time
  trades/                      Per-trade CSVs for train/validation/test splits
  final_report.md              The headline deliverable
```

## Setup

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env   # optional; only needed if pointing at real APIs later
```

## Running the pipeline

```bash
python main.py --download        # fetch real daily BTC data + generate labeled synthetic minute/contract data
python main.py --prepare-data    # clean data, write data_quality_report.md, build features
python main.py --backtest baseline   # run Strategy A end-to-end, print + save per-split metrics
python main.py --backtest technical  # NOT IMPLEMENTED in this pass -- exits with an explanation (see below)
python main.py --backtest ml         # NOT IMPLEMENTED in this pass -- exits with an explanation (see below)
python main.py --report          # breakdowns, charts, bootstrap CIs, parameter sweeps -> results/final_report.md
```

## Why `--backtest technical` and `--backtest ml` are not implemented yet

Per this project's explicit instructions: **stop after the first baseline
backtest completes successfully end-to-end, so the user can review results
before continuing to the technical (Strategy B) and ML (Strategy C) variants.**
`models/logistic.py` is written and ready to be wired in; `models/ml_models.py`
is a deliberate stub (raises `NotImplementedError`) because the available
sample (7 days, ~670 contracts) is both too small for a trustworthy random
forest / gradient boosting fit and — more importantly — synthetic, so any
apparent ML "edge" would be doubly meaningless. See `results/final_report.md`
→ "Next Steps".

## No-look-ahead guarantees

- `features/feature_engine.py` merges each Kalshi decision-row with BTC
  indicators using `pd.merge_asof(..., direction="backward")` — a decision
  row can only see BTC data at or before its own timestamp.
- All rolling/EWM indicators (`features/indicators.py`) are backward-looking
  by construction (pandas `.rolling()` / `.ewm()`).
- `backtest/engine.py` reads `settled_yes` / `settle_price` **only** at
  trade-close time to compute PnL — never to decide whether/when to enter.
- `feature_engine.py` runs an automated spot-check
  (`_assert_no_lookahead`) after building features, comparing a sample of
  rows against BTC data restricted to `timestamp <= decision_timestamp`, and
  the pipeline run in this repo passed it (0 mismatches on 200 sampled rows).

## Baseline backtest results (synthetic demo data — see limitations above)

See `results/final_report.md` for the full breakdown. Headline (test split,
out-of-sample, `MIN_EDGE=0.05`, `position_fraction=0.01`, `$1000` starting
bankroll):

- 135 trades, win rate 26.7%, ROI **-33.8%**, profit factor 0.60, Brier
  score 0.250, bootstrap 95% CI on win rate **[19.3%, 34.1%]**.
- **Verdict: NO EDGE OBSERVED on this sample** — and, critically, this
  sample is synthetic demo data, so this result says nothing about real
  Kalshi markets either way. See `results/final_report.md` for the full
  reasoning, breakdowns, and overfitting discussion.

## Honest caveats

- **Sample size is tiny** (7 synthetic days). All statistics carry wide
  confidence intervals; nothing here should be read as a strong conclusion,
  positive or negative.
- **All 15-minute/minute-level data is synthetic**, clearly labeled
  throughout. Real Kalshi data and real intraday BTC data were both
  genuinely unobtainable in this environment (see table above) — this was
  not a shortcut taken for convenience.
- **The Kalshi fee schedule used is unverified-live** in this environment.
- Parameter sweeps (`MIN_EDGE`, position sizing) were run on the same test
  split as the headline metrics and are reported for transparency only —
  the headline result uses pre-registered `config.py` defaults, not the
  sweep's best value, to avoid a multiple-testing/data-snooping error.
