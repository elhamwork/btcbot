# Final Report -- BTC 15-Minute Kalshi Strategy Backtest

Generated: 2026-08-20T01:50:59.421857+00:00

## VERDICT

**NO EDGE OBSERVED (on this sample)**

- Test-split ROI was negative (-33.77%).
- CRITICALLY: this entire dataset is SYNTHETIC DEMO DATA, not real Kalshi market history (see 'Data Sources & Limitations' below). No conclusion here generalizes to real markets.

## Data Sources & Limitations (READ THIS FIRST)

**This backtest runs on SYNTHETIC DEMO DATA, not real historical Kalshi market data.** In the sandboxed environment this project was built in, the network egress proxy blocked every attempt to reach Kalshi's API (api.elections.kalshi.com, trading-api.kalshi.com, docs.kalshi.com -- HTTP 403 on CONNECT) and every public crypto-exchange/price API tried (Binance, Coinbase, CoinGecko, Kraken, Bitstamp, Gemini, Yahoo Finance, stooq.com -- all HTTP 403 on CONNECT). Alpha Vantage's MCP integration was reachable, but its intraday endpoints (CRYPTO_INTRADAY, TIME_SERIES_INTRADAY) returned a 'premium endpoint' rate_limit error on every interval tried (1min/5min/15min/60min) -- gated behind a paid tier not available here.

The **only real, verified market data obtainable was daily BTC/USD OHLCV** via Alpha Vantage's DIGITAL_CURRENCY_DAILY endpoint (free tier), saved untouched at `data/raw/btc_daily_real.csv` (raw API response also saved at `data/raw/_alphavantage_btc_daily_raw_response.json`). That real daily series was used only to CALIBRATE (drift/volatility) a seeded, reproducible, geometric-Brownian-motion synthetic minute-level BTC price path (`data/raw/btc_1min_SYNTHETIC.csv`), from which synthetic Kalshi-style 15-minute contract quotes were derived using a documented barrier-probability formula (`data/raw/kalshi_15min_contracts_SYNTHETIC.csv`). Every synthetic row is tagged `is_synthetic=True` and every synthetic filename carries a `_SYNTHETIC` suffix.

**No part of this backtest's numeric results (win rate, ROI, edge, etc.) should be interpreted as evidence about real Kalshi markets.** The sole purpose of this run is to demonstrate the pipeline (download -> clean -> feature-engineer -> walk-forward backtest -> report) is architected and wired correctly end-to-end, ready to be pointed at real data the moment it's obtainable (e.g. from a network environment that can reach Kalshi's API and a non-premium intraday crypto price source).

Synthetic sample size: **7 days**, 10080 synthetic minute bars, 672 synthetic 15-minute contract windows.

Execution assumption: no real limit-order-book data exists (real or synthetic) -- entries transact at the modeled `yes_ask`/`no_ask` (fair probability +/- half a 0.02-wide modeled spread). Kalshi fee formula (fee = ceil(0.07 * C * P * (1-P)) per side) is from general knowledge of Kalshi's public fee schedule and is **UNVERIFIED-LIVE** in this environment since docs.kalshi.com was network-blocked -- flagged in config.py (`FEE_SCHEDULE_VERIFIED_LIVE = False`).

## Dataset

- Period (synthetic): 2026-08-13T00:00:00Z + 7 days
- Contracts (15-min windows): 672
- Chronological split: train=403, validation=134, test=135 contracts
- Entry decision points used: [14, 12, 10, 8, 6, 5, 4, 3, 2, 1, 0.5] minutes-remaining (0.5m unavailable at minute resolution -- see engine log / README)

## Baseline Model (Strategy A)

- Mode: **logistic** (features: ['strike_distance_pct', 'minutes_remaining', 'realized_vol_5m'])

## Test-Split Results (primary, out-of-sample)

| Metric | Value |
|---|---|
| # Trades | 135 |
| Win rate | 26.67% |
| Avg PnL/trade | $-2.50 |
| Net profit | $-337.66 |
| ROI | -33.77% |
| Max drawdown | $-389.23 (-37.75%) |
| Drawdown duration (trades) | 122 |
| Worst losing streak | 8 |
| Best winning streak | 2 |
| Avg edge | 14.73% |
| Median edge | 13.60% |
| Profit factor | 0.6045 |
| Brier score | 0.2503 |
| Log loss | 0.6938 |

- Bootstrap 95% CI on win rate: [19.26%, 34.07%] (2000 resamples)
- Bootstrap 95% CI on per-trade PnL mean: [$-4.23, $-0.57]
- Binomial test win rate vs 50%: n=135, wins=36, p-value=0.0000

## Train / Validation Results (for comparison, overfitting check)

- **train**: n=403, win_rate=36.48%, roi=-6.78%, brier=0.2497
- **validation**: n=134, win_rate=31.34%, roi=-17.71%, brier=0.2506

## Parameter Sweeps (multiple-testing disclosure)

MIN_EDGE sweep tried **7 combinations**: [0.05, 0.06, 0.07, 0.08, 0.1, 0.12, 0.15]. Position-size sweep tried **4 combinations**: [0.005, 0.01, 0.02, 0.05]. Both sweeps were run on the SAME test split as the headline result above -- picking the best-performing threshold from this sweep post-hoc would be a multiple-testing / data-snooping error; the headline result above uses the pre-registered config defaults (MIN_EDGE=0.05, position_fraction=0.01), not the sweep's best value.

MIN_EDGE sweep (test split):

|   min_edge |   n_trades |   win_rate |       roi |   profit_factor |
|-----------:|-----------:|-----------:|----------:|----------------:|
|       0.05 |        135 |   0.266667 | -0.337657 |        0.604473 |
|       0.06 |        135 |   0.259259 | -0.337437 |        0.616524 |
|       0.07 |        135 |   0.281481 | -0.248088 |        0.72267  |
|       0.08 |        135 |   0.281481 | -0.209836 |        0.770753 |
|       0.1  |        135 |   0.274074 | -0.19908  |        0.790478 |
|       0.12 |        135 |   0.266667 | -0.196    |        0.800364 |
|       0.15 |        135 |   0.244444 | -0.214851 |        0.783953 |

Position-size sweep (test split):

|   position_fraction |   n_trades |   win_rate |       roi |   max_drawdown_pct |
|--------------------:|-----------:|-----------:|----------:|-------------------:|
|               0.005 |        135 |   0.266667 | -0.184015 |          -0.209419 |
|               0.01  |        135 |   0.266667 | -0.337657 |          -0.377528 |
|               0.02  |        135 |   0.266667 | -0.571307 |          -0.619518 |
|               0.05  |        135 |   0.266667 | -0.89882  |          -0.922261 |

## Breakdowns

### By edge bucket

| bucket      |   n |   win_rate |        roi |   avg_edge |
|:------------|----:|-----------:|-----------:|-----------:|
| [0.05,0.07) |  21 |   0.380952 | -0.0375831 |  0.0604835 |
| [0.07,0.10) |  21 |   0.333333 | -0.0521775 |  0.081608  |
| [0.10,0.15) |  33 |   0.272727 | -0.0893994 |  0.124828  |
| [0.15,1.00) |  60 |   0.2      | -0.158497  |  0.213082  |

### By time remaining

|   bucket |   n |   win_rate |         roi |   avg_edge |
|---------:|----:|-----------:|------------:|-----------:|
|        8 |   1 |   1        |  0.0118465  |   0.162495 |
|       10 |  17 |   0.294118 |  0.00321028 |   0.151485 |
|       12 |  30 |   0.333333 | -0.0367218  |   0.135815 |
|       14 |  87 |   0.229885 | -0.315992   |   0.150298 |

### By market price bucket

| bucket    |   n |   win_rate |        roi |   avg_edge |
|:----------|----:|-----------:|-----------:|-----------:|
| [0.0,0.2) |   5 |   0.2      |  0.0215944 |  0.32332   |
| [0.2,0.4) |  85 |   0.235294 | -0.240457  |  0.176157  |
| [0.4,0.6) |  45 |   0.333333 | -0.118794  |  0.0732933 |

### By volatility regime

| bucket   |   n |   win_rate |        roi |   avg_edge |
|:---------|----:|-----------:|-----------:|-----------:|
| low      |  45 |   0.333333 | -0.0744076 |   0.114019 |
| mid      |  45 |   0.222222 | -0.117515  |   0.158439 |
| high     |  45 |   0.244444 | -0.145734  |   0.1695   |

### By side

| bucket   |   n |   win_rate |       roi |   avg_edge |
|:---------|----:|-----------:|----------:|-----------:|
| NO       |  72 |   0.25     | -0.211656 |   0.153012 |
| YES      |  63 |   0.285714 | -0.126    |   0.140814 |

## Charts

See `results/charts/`: equity_curve.png, drawdown.png, edge_vs_return.png, calibration_curve.png, results_by_time_remaining.png.

## Overfitting Concerns

- Sample size is tiny (7 synthetic days, ~670 contracts, ~135 test trades); any apparent edge or lack thereof carries wide statistical uncertainty (see bootstrap CIs).
- The baseline model was fit on synthetic data generated from a probability formula that is structurally similar to the heuristic fallback in models/baseline.py -- on synthetic data a model can appear well-calibrated almost by construction, which would NOT transfer to real markets with real microstructure, fees, latency, and adverse selection. This is a fundamental reason results here are demo-only.
- Parameter sweeps were run on the same test split as headline metrics (see 'Parameter Sweeps' above) -- reported for transparency, not used to cherry-pick the headline result.

## Next Steps (deliberately NOT done in this pass)

- Strategy B (`models/logistic.py`, full-feature calibrated logistic regression) and Strategy C (`models/ml_models.py`, random forest / gradient boosting, currently a stub that raises NotImplementedError) are intentionally not run. Per project instructions, the pipeline stops after this baseline pass for user review.
- Before any of this is meaningful, this project needs: (1) real Kalshi historical market/trade data from a network environment that can reach Kalshi's API, and (2) real intraday (1-minute or better) BTC price data from a non-premium source.

