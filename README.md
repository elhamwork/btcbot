# BTC 15-Minute Kalshi Strategy Backtester

A research backtester for Kalshi's `KXBTC15M` series (BTC 15-minute binary
contracts). Its only purpose is to answer one question honestly:

> Does a BTC 15-minute Kalshi strategy have a statistically meaningful edge
> after real prices, spreads, fees, and execution assumptions?

**Current answer: no.** See [`results/final_report.md`](results/final_report.md).

This is not a trading bot. There is no order execution code and none should be
added until a strategy clears the gate described below.

<!-- LIVE:BEGIN -->

## Live paper account

**$926.64** &nbsp; -7.3% since $1,000 &nbsp;&middot;&nbsp; updated 25 Aug 04:07 UTC

| calls settled | won / lost | win rate | break-even it must beat |
|---|---|---|---|
| 14 | 11 / 3 | 78.6% | 80.8% |

Best $1,099.47, worst $926.64, fees paid $19.42.

### Last 8 calls

| closed | result | paid | account after | side | price |
|---|---|---|---|---|---|
| 25 Aug 01:15 | **LOST** | -104.65 | $926.64 | YES | 0.79 |
| 25 Aug 00:30 | won | +16.83 | $1,031.29 | NO | 0.85 |
| 24 Aug 19:30 | won | +16.56 | $1,014.46 | NO | 0.85 |
| 24 Aug 18:15 | won | +28.97 | $997.90 | YES | 0.76 |
| 24 Aug 17:15 | **LOST** | -108.67 | $968.93 | NO | 0.88 |
| 24 Aug 14:15 | won | +24.85 | $1,077.60 | YES | 0.80 |
| 24 Aug 13:45 | won | +32.23 | $1,052.75 | NO | 0.75 |
| 24 Aug 13:00 | won | +17.98 | $1,020.52 | YES | 0.84 |

1 call open right now.

14 of the roughly 100 settled calls needed before this win rate
means much. Two or three losses in the first dozen is ordinary;
four or more in twenty would say the model is wrong.

Paper only: no broker, no account, no orders. Full history in
[`cloud_state/learning_report.md`](cloud_state/learning_report.md).
Rebuilt each time the cloud watcher saves, about once an hour.

<!-- LIVE:END -->

---

## The headline result

| Test split, probability quality | Brier | Log loss | ROC-AUC |
|---|---|---|---|
| **Market mid-price** | **0.1353** | **0.4155** | 0.8901 |
| Analytic GBM baseline | 0.1418 | 0.4594 | 0.8820 |
| Logistic baseline (Strategy A) | 0.1483 | 0.5730 | 0.8657 |

The market's own price is a better probability estimate than either model, on
every split, by every scoring rule. When your estimate is worse than the price
you are betting against, every "edge" you compute is your own error.

Trading follows directly: 263 trades, 60.08% win rate, **−7.79% ROI**, profit
factor 0.92. The break-even win rate implied by the prices actually paid was
60.65%. The strategy won 60.08% of the time. It lost by almost exactly the
spread.

**The gate:** a model must beat a Brier of 0.1353 before any trading rule
built on it is worth testing.

---

## A look-ahead bug was found and fixed

The first run reported a 63.9% win rate and **+28.7% ROI**. That was false.

Coinbase timestamps each 1-minute bar at the **start** of its bucket, so the
`close` of the bar labelled `T` is the price at `T+1`. Joining a decision at
time `T` to that bar fed the model a price one minute into the future — nearly
the answer itself at the 1-minute decision point.

Two independent anchors caught it, neither visible to the model:

- **Settlement** agreement peaked at a one-minute shift (92.3%) rather than at
  zero (86.9%).
- **The strike**, which Kalshi fixes at spot on open, matched the bar's *open*
  rather than its close.

Bars are now re-labelled to bar-end (`config.BTC_BAR_SHIFT_MINUTES`), and
`data/cleaner.py::_check_alignment` re-runs both tests on every
`--prepare-data`, reporting the best shift by each anchor. Both currently read
`+0`.

The whole apparent edge was the bug. This is worth stating plainly because it
is the normal failure mode of backtests, and it produced a result that looked
excellent rather than obviously broken.

---

## Data

Everything is real. Nothing is simulated, interpolated, or back-filled.

| | |
|---|---|
| Kalshi | `KXBTC15M`, public REST API, **no account required** |
| | 1,320 settled contracts, 19,845 per-minute bid/ask candles |
| BTC price | Coinbase `BTC-USD`, 1-minute OHLCV, 20,161 bars, 100% coverage |
| Period | 2026-08-06 → 2026-08-20 (14 days) |
| Outcome balance | 50.4% YES — a genuine coin flip |

`KXBTC15M` runs one contract every 15 minutes with **one strike per event**,
set at spot when the contract opens. That makes every contract a near
coin-flip and avoids the deep in/out-of-the-money strike ladder of Kalshi's
hourly `KXBTCD` series.

### Collecting it

Collection is separate from analysis, because the machine that can reach
Kalshi is often not the machine running the analysis. Each script is
standard-library only — no `pip install`, no API key, read-only:

```bash
python3 discover_series.py     # which BTC series exist, and their real cadence
python3 fetch_15m.py           # Kalshi contracts + per-minute bid/ask
python3 fetch_btc_prices.py    # BTC 1-minute OHLCV from Coinbase
```

They write to `real_data/`. See [`HOW_TO_GET_DATA.md`](HOW_TO_GET_DATA.md) for
step-by-step instructions.

---

## Usage

```bash
pip install -r requirements.txt

python main.py --download          # status of the collected data files
python main.py --prepare-data      # clean, audit, verify causality, build panel
python main.py --backtest baseline # Strategy A (logistic)
python main.py --backtest analytic # no-fit GBM null
python main.py --backtest market   # market mid reference (scores only)
python main.py --report            # charts, statistics, final_report.md
```

`--backtest technical` and `--backtest ml` intentionally refuse to run. See
"Not done yet" below.

---

## How look-ahead bias is prevented

The rule: at a decision made at time `T`, only information available at `T`.

1. **Causal indicators.** Every function in `features/indicators.py` uses
   trailing windows and recursive EMAs. Nothing is shifted backwards.
2. **Tested, not asserted.** `verify_no_lookahead()` rebuilds features from a
   truncated history at 150 random timestamps and compares against the
   full-series computation. Any peeking shows up as a mismatch. It currently
   reports a worst relative difference of exactly `0.00e+00`, and
   `--prepare-data` aborts if that changes.
3. **Clock alignment.** `_check_alignment()` independently verifies the BTC
   clock against settlement and strike-at-open — the check that caught the bug
   above.
4. **Quotes are as-of.** A decision at `T` uses the candle whose period *ends*
   at `T`. Nothing later in the contract's life is visible.
5. **Bankroll causality.** `portfolio.verify_causality()` asserts every trade's
   stake was sized from the bankroll as it stood before that trade. The
   backtest aborts on violation.
6. **Labels are for scoring only.** The settled result never enters a feature.

---

## Execution assumptions

Pessimistic where there is doubt. All configurable in `config.py`.

- YES buys pay `yes_ask`; NO buys pay `1 − yes_bid`. **Never the mid.**
- Kalshi fee `ceil(0.07 × contracts × P × (1−P))` charged on entry.
  ⚠️ `FEE_SCHEDULE_VERIFIED_LIVE = False` — `docs.kalshi.com` was unreachable
  from the build environment, so this is the published formula, unconfirmed.
- Skip if spread > 5¢, or price outside 5¢–95¢.
- One trade per contract, so a single contract cannot spawn ten correlated
  trades.
- Fixed-fractional sizing, 1% of bankroll, from $1,000.

---

## Overfitting controls

- Chronological splits only: train 60% / validation 20% / test 20%, by contract
  close time. Never random.
- 3 models × 28 parameter combinations swept **on validation only**.
- The test split was scored once, after the model was locked.
- Calibration is fit on validation with the underlying model frozen.
- Volatility-regime buckets are cut at **train** quantiles.
- The best validation configuration was deliberately *not* carried into test.

---

## Project layout

```
config.py                  all assumptions and thresholds
main.py                    CLI
fetch_15m.py               standalone Kalshi collector
fetch_btc_prices.py        standalone Coinbase collector
discover_series.py         standalone series discovery
data/       loader, cleaner (audit), downloader (docs)
features/   indicators (causal), feature_engine (panel + verification)
models/     baseline (analytic / logistic / market), logistic + ml (stubs)
backtest/   engine, execution, portfolio, metrics
analysis/   breakdowns, statistics, charts, report_builder
results/    final_report.md, reports/, charts/, trades/
```

---

## Known limitations

1. **14 days, 1,320 contracts.** Short. A small real edge could hide here —
   though the observed failure is not marginal.
2. **Feed mismatch.** Coinbase reproduces Kalshi's settlement 92.3% of the
   time; disagreements cluster on near-ties, where the two indices differ by a
   few dollars. This adds feature noise, making the model's job *harder* — it
   cannot manufacture an edge, only hide one.
3. **No order-book depth.** Best bid/ask per minute only; fills assumed at the
   quoted ask for the full position.
4. **Minute resolution.** The 30-second entry point in the original spec is not
   observable and is not faked.
5. **Fee schedule unverified.** See above.

---

## Not done yet

Strategy B (technical features) and Strategy C (ML) are stubs. Per the
specification, work stopped after the baseline so results could be reviewed
first. Both stubs document the gate they must clear: **beat a Brier of
0.1353**, the market's own score, before any trading rule is worth testing.

Before adding model complexity, consider the simpler explanation: a coin flip
priced with a 1-cent spread plus fees may simply be efficiently priced. "No
edge" is a legitimate finding, not a failure of method.
