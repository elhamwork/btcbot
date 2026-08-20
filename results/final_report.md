# Final Report - BTC 15-Minute Kalshi Strategy

## VERDICT

# NO

**THE STRATEGY DOES NOT CURRENTLY SHOW AN EDGE.**

The single most important number in this report: the **market's own mid-price is a better probability estimate than either model**, on every split, by every scoring rule.

| Test-split probability quality | Brier | Log loss | ROC-AUC |
|---|---|---|---|
| Market mid (reference) | 0.1353 | 0.4155 | 0.8901 |
| Strategy A0 - analytic GBM | 0.1418 | 0.4594 | 0.8820 |
| Strategy A - logistic baseline | 0.1483 | 0.5730 | 0.8657 |

Lower Brier and log loss are better. The market wins both. When your probability estimate is worse than the price you are betting against, every 'edge' you compute is your own error, not a mispricing. The trading results follow directly from that.

## A look-ahead bug was found and fixed - read this

The first run of this backtest reported a **63.9% win rate and +28.7% ROI** on the test split. That result was false.

Coinbase timestamps each 1-minute bar at the **start** of its bucket, so the `close` of the bar labelled `T` is the price at `T+1 minute`. The feature engine joined each decision at time `T` to that bar, handing the model a price one minute into the future. At the 1-minute-remaining decision point that is very nearly the answer itself.

Two independent anchors caught it, neither of which the model sees:

- **Settlement.** Agreement between our BTC feed and Kalshi's settled result peaked at a one-minute shift (92.3%) rather than at zero (86.9%).
- **Strike.** Kalshi fixes the strike at spot when a contract opens. The strike matched the bar's *open*, not its close.

After re-labelling bars to bar-end, the same configuration returns **-7.79% ROI**. The entire apparent edge was the bug. `data/cleaner.py::_check_alignment` now re-runs this test on every `--prepare-data` and reports the best shift by both anchors; it is currently `+0` on each, meaning aligned.

## Dataset

| | |
|---|---|
| Source | Kalshi `KXBTC15M` (real, public API) + Coinbase BTC/USD 1-minute (real) |
| Period | 2026-08-06 05:15:00+00:00 -> 2026-08-20 04:15:00+00:00 (14 days) |
| Contracts | 1320 |
| Decision rows | 13190 |
| Entry points | 14, 12, 10, 8, 6, 5, 4, 3, 2, 1 minutes remaining |
| Outcome balance | 50.4% YES - a genuine coin flip |

Chronological split, never random:

| Split | Contracts | From | To |
|---|---|---|---|
| Train | 793 | 2026-08-06 05:15:00+00:00 | 2026-08-14 16:30:00+00:00 |
| Validation | 264 | 2026-08-14 16:45:00+00:00 | 2026-08-17 10:30:00+00:00 |
| Test | 263 | 2026-08-17 10:45:00+00:00 | 2026-08-20 04:15:00+00:00 |

## Trading results

| Strategy | Split | Trades | Win rate | ROI | Max DD | Profit factor | Avg edge |
|---|---|---|---|---|---|---|---|
| Market mid (reference) | train | 0 | - | - | - | - | - |
| Market mid (reference) | validation | 0 | - | - | - | - | - |
| Market mid (reference) | test | 0 | - | - | - | - | - |
| Strategy A0 - analytic GBM | train | 764 | 50.79% | -22.30% | -44.33% | 0.934 | 11.44% |
| Strategy A0 - analytic GBM | validation | 260 | 51.54% | -14.13% | -21.92% | 0.877 | 15.06% |
| Strategy A0 - analytic GBM | test | 252 | 50.79% | 5.07% | -17.49% | 1.041 | 10.45% |
| Strategy A - logistic baseline | train | 789 | 58.68% | -25.78% | -26.68% | 0.908 | 16.30% |
| Strategy A - logistic baseline | validation | 263 | 58.17% | 3.39% | -12.90% | 1.030 | 13.28% |
| Strategy A - logistic baseline | test | 263 | 60.08% | -7.79% | -15.11% | 0.922 | 18.86% |

The market reference takes zero trades by construction - it never disagrees with itself. It is here for the probability scores only.

### Headline: Strategy A on the held-out test split

- **Total trades:** 263
- **Wins:** 158
- **Losses:** 105
- **Win rate:** 60.08%
- **Net profit:** $-77.94 on a $1000 bankroll
- **ROI:** -7.79%
- **Max drawdown:** -15.11%
- **Profit factor:** 0.922
- **Average edge claimed:** 18.86%
- **Average entry price:** 0.607
- **Brier score:** 0.1483 (market: 0.1353)
- **Fees paid:** $68.31

Note the shape of the failure: a **60.08% win rate that still loses money**. Winning trades are not the problem - the prices paid are. An average entry of 0.607 needs a 60.7% win rate just to break even before fees.

## Statistical significance

- **Win rate:** 60.08%, 95% CI [53.99%, 65.78%]
- **ROI:** -7.79%, 95% CI [-32.36%, 16.36%]
- **Versus the break-even win rate implied by prices paid:** observed 60.08% against a required 60.65% (excess -0.57%), one-sided binomial p = 0.6017
- **Profit per trade differs from zero:** t = -0.623, p = 0.5340
- **Do bigger predicted edges produce better outcomes?** Spearman rho = -0.0452, p = 0.4658. No monotonic relationship - the edge estimate carries no signal.

The ROI confidence interval straddles zero. On 14 days of data that is the expected outcome for a strategy without a real edge, and it is also what a small sample looks like when an edge is genuinely absent. Either way, nothing here supports trading.

## Breakdowns (test split, Strategy A)

### By predicted edge

| edge_bucket | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| 5-7.5% | 16.0000 | 0.5625 | 9.3600 | 0.5850 | 0.0635 | 0.5300 | 0.0605 |
| 7.5-10% | 19.0000 | 0.4737 | -26.4100 | -1.3900 | 0.0845 | 0.5484 | -0.1456 |
| 10-15% | 52.0000 | 0.6538 | 30.2800 | 0.5823 | 0.1240 | 0.5962 | 0.0611 |
| 15%+ | 176.0000 | 0.6023 | -91.1700 | -0.5180 | 0.2303 | 0.6228 | -0.0548 |

### By time remaining at entry

| time_bucket | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| 5-8m | 1.0000 | 0.0000 | -10.1500 | -10.1500 | 0.1150 | 0.4900 | -1.0000 |
| 8-12m | 17.0000 | 0.5882 | -15.1900 | -0.8935 | 0.1502 | 0.6429 | -0.0948 |
| 12-15m | 245.0000 | 0.6041 | -52.6000 | -0.2147 | 0.1916 | 0.6044 | -0.0226 |

### By market price paid

| price_bucket | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| 40-50c | 26.0000 | 0.5385 | 15.0000 | 0.5769 | 0.1146 | 0.4835 | 0.0598 |
| 50-60c | 108.0000 | 0.5278 | -73.4400 | -0.6800 | 0.1820 | 0.5545 | -0.0710 |
| 60-70c | 95.0000 | 0.6737 | 20.4000 | 0.2147 | 0.2203 | 0.6488 | 0.0228 |
| 70-80c | 31.0000 | 0.6452 | -44.6200 | -1.4394 | 0.1808 | 0.7381 | -0.1546 |
| 80-90c | 3.0000 | 1.0000 | 4.7200 | 1.5733 | 0.1443 | 0.8433 | 0.1730 |

### By volatility regime (cut at TRAIN quantiles)

| vol_regime | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| LOW | 28.0000 | 0.6786 | 50.4200 | 1.8007 | 0.1346 | 0.5443 | 0.1877 |
| NORMAL | 68.0000 | 0.5588 | -33.2400 | -0.4888 | 0.1557 | 0.5878 | -0.0514 |
| HIGH | 70.0000 | 0.5286 | -120.6700 | -1.7239 | 0.1811 | 0.6130 | -0.1826 |
| EXTREME | 97.0000 | 0.6598 | 25.5500 | 0.2634 | 0.2328 | 0.6329 | 0.0277 |

### By direction

| side | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| NO | 157.0000 | 0.5860 | -56.4500 | -0.3596 | 0.1655 | 0.5919 | -0.0378 |
| YES | 106.0000 | 0.6226 | -21.4900 | -0.2027 | 0.2229 | 0.6281 | -0.0214 |

### By exact entry minute

| minutes_remaining | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| 8.0000 | 1.0000 | 0.0000 | -10.1500 | -10.1500 | 0.1150 | 0.4900 | -1.0000 |
| 12.0000 | 17.0000 | 0.5882 | -15.1900 | -0.8935 | 0.1502 | 0.6429 | -0.0948 |
| 14.0000 | 245.0000 | 0.6041 | -52.6000 | -0.2147 | 0.1916 | 0.6044 | -0.0226 |

## Overfitting controls

- **Models evaluated:** 3 (market reference, analytic GBM, logistic baseline).
- **Parameter combinations swept:** 28 (7 edge thresholds x 4 position sizes), on the **validation** split only.
- **Total configurations evaluated:** 31.
- The test split was scored once, after the model was locked. No parameter was chosen by looking at it.
- Volatility-regime bucket edges come from **train** quantiles, so the test distribution does not leak into its own bucketing.
- Probability calibration is fit on **validation**, with the underlying model frozen so validation data cannot move its coefficients.

Best validation configurations (for transparency, NOT applied to test):

| min_edge | position_fraction | trades | win_rate | roi | profit_factor |
|---|---|---|---|---|---|
| 0.1 | 0.05 | 245 | 59.18% | 394.94% | 1.207 |
| 0.12 | 0.05 | 234 | 58.12% | 379.87% | 1.194 |
| 0.1 | 0.02 | 245 | 59.18% | 111.49% | 1.313 |
| 0.12 | 0.02 | 234 | 58.12% | 110.82% | 1.309 |
| 0.15 | 0.05 | 200 | 54.00% | 70.28% | 1.067 |

Even the best of 28 validation configurations is not carried into the test split. Picking it would be selecting on noise - which is exactly the trap this section exists to avoid.

## Why there is no edge

1. **The market is better calibrated than the model.** Brier 0.1353 (market) versus 0.1483 (Strategy A) on the test split. A model that is worse than the price cannot systematically beat the price.

2. **The claimed edge is selection bias.** The strategy trades exactly where model and market disagree most. When the model is the less accurate of the two, those are precisely the model's worst estimates. An average claimed edge of 18.86% that yields a -7.79% return is the signature of this.

3. **The spread and fees are real.** Median spread is 1 cent on a contract that is often priced near 50 cents, and Kalshi's fee peaks exactly where these contracts live. Paying the ask on every entry, $68.31 went to fees on the test split alone.

4. **The strike is set at spot.** Every contract starts as a true coin flip (50.4% YES across 1,320 contracts). There is no structural mispricing at open to harvest; any edge would have to come from predicting 15-minute BTC direction better than everyone else.

## Limitations

1. **14 days, 1,320 contracts.** Short. A real edge could be present but too small to detect here - though note the failure is not marginal.
2. **Feed mismatch.** Our Coinbase prices reproduce Kalshi's settlement 92.3% of the time; disagreements cluster on near-ties. This adds noise to features and makes the model's job harder. It cannot manufacture an edge, only hide one.
3. **No order-book depth.** Best bid/ask per minute only. Fills are assumed at the quoted ask for the full position.
4. **Minute resolution.** The 30-second entry point in the original specification is not observable.
5. **Fee schedule unverified.** `docs.kalshi.com` was unreachable; the published formula is applied and flagged `FEE_SCHEDULE_VERIFIED_LIVE = False`.
6. **Strategies B and C were not run.** Per the specification, work stopped after the baseline.

## What would change the answer

A model must beat the market's Brier score **before** any trading rule is worth testing. That is the gate. Concretely:

- Add the technical feature set (Strategy B) and check the Brier score against the market's 0.1353. If it does not beat that, the trading results cannot be positive for a real reason.
- Collect a longer history. 14 days cannot separate a small edge from noise.
- Consider that these contracts may simply be efficiently priced. A coin flip priced at a 1-cent spread, with fees, is a hard thing to beat, and 'no edge' is a legitimate finding rather than a failure of method.

## Charts

- `results/charts/equity_curve.png` - Bankroll over time
- `results/charts/drawdown.png` - Drawdown
- `results/charts/edge_vs_return.png` - Predicted edge vs realised return
- `results/charts/calibration_curve.png` - Calibration - Strategy A
- `results/charts/calibration_market.png` - Calibration - market mid
- `results/charts/results_by_time_remaining.png` - Profit by entry time

---

Generated by `python main.py --report` from real market data. No figure in this report was entered by hand.