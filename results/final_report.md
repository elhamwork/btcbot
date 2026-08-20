# Final Report - BTC 15-Minute Kalshi Strategy

## VERDICT

# NO

**THE STRATEGY DOES NOT CURRENTLY SHOW AN EDGE.**

The single most important number in this report: the **market's own mid-price is a better probability estimate than either model**, on every split, by every scoring rule.

| Test-split probability quality | Brier | Log loss | ROC-AUC |
|---|---|---|---|
| Market mid (reference) | 0.1388 | 0.4218 | 0.8848 |
| Strategy A0 - analytic GBM | 0.1537 | 0.5411 | 0.8647 |
| Strategy A - logistic baseline | 0.1487 | 0.4793 | 0.8674 |

Lower Brier and log loss are better. The market wins both. When your probability estimate is worse than the price you are betting against, every 'edge' you compute is your own error, not a mispricing. The trading results follow directly from that.

## A look-ahead bug was found and fixed - read this

The first run of this backtest reported a **63.9% win rate and +28.7% ROI** on the test split. That result was false.

Coinbase timestamps each 1-minute bar at the **start** of its bucket, so the `close` of the bar labelled `T` is the price at `T+1 minute`. The feature engine joined each decision at time `T` to that bar, handing the model a price one minute into the future. At the 1-minute-remaining decision point that is very nearly the answer itself.

Two independent anchors caught it, neither of which the model sees:

- **Settlement.** Agreement between our BTC feed and Kalshi's settled result peaked at a one-minute shift (92.3%) rather than at zero (86.9%).
- **Strike.** Kalshi fixes the strike at spot when a contract opens. The strike matched the bar's *open*, not its close.

After re-labelling bars to bar-end, the same configuration returns **-29.30% ROI**. The entire apparent edge was the bug. `data/cleaner.py::_check_alignment` now re-runs this test on every `--prepare-data` and reports the best shift by both anchors; it is currently `+0` on each, meaning aligned.

## Dataset

| | |
|---|---|
| Source | Kalshi `KXBTC15M` (real, public API) + Coinbase BTC/USD 1-minute (real) |
| Period | 2026-06-17 20:00:00+00:00 -> 2026-08-20 04:45:00+00:00 (14 days) |
| Contracts | 5987 |
| Decision rows | 59860 |
| Entry points | 14, 12, 10, 8, 6, 5, 4, 3, 2, 1 minutes remaining |
| Outcome balance | 50.4% YES - a genuine coin flip |

Chronological split, never random:

| Split | Contracts | From | To |
|---|---|---|---|
| Train | 3593 | 2026-06-17 20:00:00+00:00 | 2026-07-25 21:15:00+00:00 |
| Validation | 1197 | 2026-07-25 21:30:00+00:00 | 2026-08-07 14:30:00+00:00 |
| Test | 1197 | 2026-08-07 14:45:00+00:00 | 2026-08-20 04:45:00+00:00 |

## Trading results

| Strategy | Split | Trades | Win rate | ROI | Max DD | Profit factor | Avg edge |
|---|---|---|---|---|---|---|---|
| Market mid (reference) | train | 0 | - | - | - | - | - |
| Market mid (reference) | validation | 0 | - | - | - | - | - |
| Market mid (reference) | test | 0 | - | - | - | - | - |
| Strategy A0 - analytic GBM | train | 3448 | 49.88% | -87.71% | -89.69% | 0.889 | 9.92% |
| Strategy A0 - analytic GBM | validation | 1139 | 48.99% | -38.49% | -47.91% | 0.908 | 9.96% |
| Strategy A0 - analytic GBM | test | 1160 | 50.69% | -35.16% | -45.74% | 0.917 | 12.17% |
| Strategy A - logistic baseline | train | 3457 | 62.83% | -38.72% | -58.55% | 0.970 | 11.53% |
| Strategy A - logistic baseline | validation | 1133 | 60.55% | -25.21% | -38.00% | 0.930 | 10.56% |
| Strategy A - logistic baseline | test | 1167 | 57.50% | -29.30% | -39.31% | 0.929 | 12.28% |

The market reference takes zero trades by construction - it never disagrees with itself. It is here for the probability scores only.

### Headline: Strategy A on the held-out test split

- **Total trades:** 1167
- **Wins:** 671
- **Losses:** 496
- **Win rate:** 57.50%
- **Net profit:** $-292.97 on a $1000 bankroll
- **ROI:** -29.30%
- **Max drawdown:** -39.31%
- **Profit factor:** 0.929
- **Average edge claimed:** 12.28%
- **Average entry price:** 0.567
- **Brier score:** 0.1487 (market: 0.1388)
- **Fees paid:** $287.79

Note the shape of the failure: a **57.50% win rate that still loses money**. Winning trades are not the problem - the prices paid are. An average entry of 0.567 needs a 56.7% win rate just to break even before fees.

## Statistical significance

- **Win rate:** 57.50%, 95% CI [54.58%, 60.33%]
- **ROI:** -29.30%, 95% CI [-83.21%, 24.09%]
- **Versus the break-even win rate implied by prices paid:** observed 57.50% against a required 56.75% (excess 0.75%), one-sided binomial p = 0.3130
- **Profit per trade differs from zero:** t = -1.089, p = 0.2766
- **Do bigger predicted edges produce better outcomes?** Spearman rho = 0.1140, p = 0.0001. There is a monotonic relationship.

The ROI confidence interval straddles zero. On 14 days of data that is the expected outcome for a strategy without a real edge, and it is also what a small sample looks like when an edge is genuinely absent. Either way, nothing here supports trading.

## Breakdowns (test split, Strategy A)

### By predicted edge

| edge_bucket | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| 5-7.5% | 312.0000 | 0.5609 | -67.2420 | -0.2155 | 0.0630 | 0.5539 | -0.0263 |
| 7.5-10% | 241.0000 | 0.5602 | -78.3390 | -0.3251 | 0.0875 | 0.5597 | -0.0399 |
| 10-15% | 327.0000 | 0.5872 | -196.1600 | -0.5999 | 0.1233 | 0.5922 | -0.0738 |
| 15%+ | 287.0000 | 0.5889 | 48.7700 | 0.1699 | 0.2167 | 0.5606 | 0.0207 |

### By time remaining at entry

| time_bucket | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| 1-3m | 10.0000 | 0.2000 | -30.8640 | -3.0864 | 0.1118 | 0.2822 | -0.3725 |
| 3-5m | 17.0000 | 0.4706 | 37.5780 | 2.2105 | 0.0948 | 0.4404 | 0.2602 |
| 5-8m | 78.0000 | 0.5000 | -112.3250 | -1.4401 | 0.0927 | 0.5063 | -0.1722 |
| 8-12m | 385.0000 | 0.6338 | 106.5400 | 0.2767 | 0.1140 | 0.5958 | 0.0338 |
| 12-15m | 677.0000 | 0.5583 | -293.9000 | -0.4341 | 0.1321 | 0.5658 | -0.0534 |

### By market price paid

| price_bucket | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| 0-10c | 9.0000 | 0.0000 | -78.8510 | -8.7612 | 0.0874 | 0.0823 | -1.0000 |
| 10-20c | 26.0000 | 0.1154 | -31.3000 | -1.2038 | 0.0785 | 0.1515 | -0.1336 |
| 20-30c | 17.0000 | 0.2353 | -30.2300 | -1.7782 | 0.1193 | 0.2665 | -0.1999 |
| 30-40c | 109.0000 | 0.4037 | 26.5200 | 0.2433 | 0.0868 | 0.3633 | 0.0282 |
| 40-50c | 180.0000 | 0.4222 | -202.8100 | -1.1267 | 0.1319 | 0.4670 | -0.1345 |
| 50-60c | 292.0000 | 0.5822 | 9.1800 | 0.0314 | 0.1621 | 0.5621 | 0.0039 |
| 60-70c | 375.0000 | 0.6667 | 15.8200 | 0.0422 | 0.1137 | 0.6489 | 0.0053 |
| 70-80c | 127.0000 | 0.7559 | -5.6300 | -0.0443 | 0.0987 | 0.7443 | -0.0056 |
| 80-90c | 25.0000 | 0.8800 | 8.8000 | 0.3520 | 0.0929 | 0.8324 | 0.0460 |
| 90-100c | 7.0000 | 0.8571 | -4.4700 | -0.6386 | 0.0559 | 0.9347 | -0.0821 |

### By volatility regime (cut at TRAIN quantiles)

| vol_regime | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| LOW | 727.0000 | 0.5640 | -196.5690 | -0.2704 | 0.1347 | 0.5533 | -0.0327 |
| NORMAL | 229.0000 | 0.6070 | 50.2800 | 0.2196 | 0.0985 | 0.5723 | 0.0272 |
| HIGH | 129.0000 | 0.5271 | -139.1020 | -1.0783 | 0.0978 | 0.5890 | -0.1343 |
| EXTREME | 82.0000 | 0.6585 | -7.5800 | -0.0924 | 0.1243 | 0.6460 | -0.0121 |

### By direction

| side | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| NO | 728.0000 | 0.5536 | -199.2220 | -0.2737 | 0.1252 | 0.5549 | -0.0337 |
| YES | 439.0000 | 0.6105 | -93.7490 | -0.2136 | 0.1189 | 0.5883 | -0.0259 |

### By exact entry minute

| minutes_remaining | trades | win_rate | net_profit | profit_per_trade | avg_edge | avg_entry | roi_on_turnover |
|---|---|---|---|---|---|---|---|
| 2.0000 | 5.0000 | 0.4000 | 11.7040 | 2.3408 | 0.1073 | 0.1932 | 0.2905 |
| 3.0000 | 5.0000 | 0.0000 | -42.5680 | -8.5136 | 0.1164 | 0.3712 | -1.0000 |
| 4.0000 | 8.0000 | 0.5000 | -15.2440 | -1.9055 | 0.1016 | 0.4619 | -0.2267 |
| 5.0000 | 9.0000 | 0.4444 | 52.8220 | 5.8691 | 0.0887 | 0.4213 | 0.6844 |
| 6.0000 | 27.0000 | 0.4815 | -20.5110 | -0.7597 | 0.0938 | 0.4549 | -0.0894 |
| 8.0000 | 51.0000 | 0.5098 | -91.8140 | -1.8003 | 0.0922 | 0.5336 | -0.2171 |
| 10.0000 | 120.0000 | 0.5417 | -56.0600 | -0.4672 | 0.1131 | 0.5670 | -0.0564 |
| 12.0000 | 265.0000 | 0.6755 | 162.6000 | 0.6136 | 0.1144 | 0.6088 | 0.0755 |
| 14.0000 | 677.0000 | 0.5583 | -293.9000 | -0.4341 | 0.1321 | 0.5658 | -0.0534 |

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
| 0.1 | 0.005 | 830 | 56.39% | -7.89% | 0.958 |
| 0.06 | 0.005 | 1090 | 60.37% | -8.44% | 0.956 |
| 0.15 | 0.005 | 394 | 50.25% | -10.62% | 0.893 |
| 0.05 | 0.005 | 1133 | 60.55% | -12.14% | 0.938 |
| 0.08 | 0.005 | 978 | 57.87% | -14.99% | 0.922 |

Even the best of 28 validation configurations is not carried into the test split. Picking it would be selecting on noise - which is exactly the trap this section exists to avoid.

## Why there is no edge

1. **The market is better calibrated than the model.** Brier 0.1388 (market) versus 0.1487 (Strategy A) on the test split. A model that is worse than the price cannot systematically beat the price.

2. **The claimed edge is selection bias.** The strategy trades exactly where model and market disagree most. When the model is the less accurate of the two, those are precisely the model's worst estimates. An average claimed edge of 12.28% that yields a -29.30% return is the signature of this.

3. **The spread and fees are real.** Median spread is 1 cent on a contract that is often priced near 50 cents, and Kalshi's fee peaks exactly where these contracts live. Paying the ask on every entry, $287.79 went to fees on the test split alone.

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

- Add the technical feature set (Strategy B) and check the Brier score against the market's 0.1388. If it does not beat that, the trading results cannot be positive for a real reason.
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