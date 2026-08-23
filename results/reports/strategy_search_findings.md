# Strategy Search — Everything Tested

An exhaustive search for a positive-expectancy strategy on Kalshi `KXBTC15M`,
using 1,320 real settled contracts, 19,845 real per-minute bid/ask quotes, and
20,161 real BTC 1-minute bars over 14 days.

Every test below reports **all three time periods** (train / validation /
test). A result that appears in one period and not the others is noise, and
ranking by the best period is how backtests lie.

---

## Summary

| # | Idea tested | Verdict |
|---|---|---|
| 1 | 105 model configurations (logistic, GBM, RF, residual) | **Chance** — 24% positive on val+test vs ~25% expected |
| 2 | Market lag / stale quotes | **No lag** — Kalshi tracks spot in real time |
| 3 | Residual modelling (predict market error) | **Negative** out-of-sample R² |
| 4 | Entry-window timing (10 windows) | **Noise** — best window is worst in train |
| 5 | RSI conditional miscalibration | **Unstable** — in val/test, absent in train |
| 6 | Favourite–longshot bias | **REAL and large**, but not capturable |
| 7 | Passive liquidity provision (limit orders) | **Inverts** under realistic fills |
| 8 | Informed order flow (volume, signed flow) | **No pattern** — signs flip |

---

## 6. Favourite–longshot bias — the one real effect found

Buying the cheap side loses in **every band, every period**:

| Longshot price | Train | Validation | Test |
|---|---|---|---|
| 0.01–0.10 | −24.50% | −15.01% | −7.24% |
| 0.10–0.20 | −2.48% | −6.23% | −15.72% |
| 0.20–0.30 | −13.48% | +0.07% | −27.18% |
| 0.30–0.40 | −15.64% | −13.85% | −6.79% |
| 0.40–0.50 | −9.78% | −22.17% | −17.94% |

Fourteen of fifteen cells negative, many severely. This is the
favourite–longshot bias — one of the most replicated findings in the
prediction-market literature — and it is unmistakably present here.

**It is still not a strategy.** The mirror trade (buying the favourite) is
only break-even:

| Favourite price | Train | Validation | Test |
|---|---|---|---|
| 0.50–0.60 | −1.03% | +5.60% | +1.96% |
| 0.60–0.70 | −0.25% | +0.58% | +0.34% |
| 0.70–0.80 | −0.40% | −3.69% | +1.51% |
| 0.80–0.90 | −3.57% | −2.22% | −0.54% |
| 0.90–0.99 | −1.08% | −1.68% | −2.13% |

The longshot buyer's loss does not become the favourite buyer's gain, because
**both sides pay their own ask**. The spread plus Kalshi's fee absorbs almost
exactly the mispricing. The bias is real; the arbitrage is eaten by costs.

**Actionable conclusion:** never buy a contract priced under 50¢ on this
series. That is a genuine, stable, large finding — it just prevents losses
rather than producing gains.

---

## 7. Passive liquidity provision — the near-miss

The literature names this as one of the few durable retail edges, and on first
pass it looked like the answer. Buying the favourite via a **limit order at
the bid** rather than paying the ask:

| Favourite price | Train | Validation | Test |
|---|---|---|---|
| 0.50–0.60 | +0.83% | +7.55% | +3.84% |
| **0.60–0.70** | **+1.34%** | **+2.18%** | **+1.90%** |
| 0.70–0.80 | +0.96% | −2.34% | +2.87% |

The 0.60–0.70 band is positive in all three periods within a tight range — the
most stable positive result anywhere in this project.

### Then the fill assumption was tested

That table assumes **every limit order fills**. In reality a resting bid only
fills when someone sells into it — and people sell when the price is about to
fall. Restricting to cases where the bid was actually touched:

| Favourite price | Assumption | Train | Validation | Test |
|---|---|---|---|---|
| 0.50–0.60 | always filled | +0.32% | +8.65% | +4.66% |
| 0.50–0.60 | **actually filled** | **−26.06%** | **−16.30%** | **−25.77%** |
| 0.60–0.70 | always filled | +1.09% | +2.36% | +2.64% |
| 0.60–0.70 | **actually filled** | **−25.36%** | **−16.02%** | **−21.71%** |
| 0.70–0.80 | always filled | +1.12% | −2.67% | +2.55% |
| 0.70–0.80 | **actually filled** | **−18.00%** | **−22.54%** | **−17.01%** |

A +2% edge becomes **−22%**. This is adverse selection, and it is the single
largest effect measured in this entire study — far larger than any signal.

The fills you *want* are the ones you don't get. The fills you *get* are the
ones you don't want. Roughly 43% of resting bids are touched, and they are
overwhelmingly the wrong 43%.

This is why naive market-making backtests are dangerous: they look like the
holy grail and they are precisely inverted.

---

## What would still be worth trying

Not tested here, and not testable with this dataset:

1. **Sub-second data.** All of the above runs on 1-minute resolution. The
   real competition at 1–2 minutes to expiry happens far faster. If an edge
   exists it likely lives below our sampling rate — and belongs to whoever has
   the lowest latency, which is an infrastructure race, not a modelling one.

2. **Cross-market arbitrage.** Kalshi's hourly `KXBTCD` series overlaps in
   time with `KXBTC15M`. Genuine arbitrage would require both books
   simultaneously with matched strikes. Worth exploring; requires new data
   collection.

3. **A longer history.** Everything here rests on 14 days. It cannot separate
   a 1–2 point edge from noise.

---

## The honest bottom line

The favourite–longshot bias is real and measurable in this market. Passive
liquidity provision looks profitable and is not, once fills are modelled
honestly. Everything else tested is indistinguishable from chance.

No positive-expectancy strategy was found. The market prices these contracts
efficiently enough that the spread and fee absorb the one genuine mispricing
present.

## Confirmation filter (added after the baseline report)

Three further ideas were tested against the same 63-day panel, on the same
chronological 60/20/20 split, with all fitting done on train only.

**1. Blending the model probability with Kalshi's price — rejected as the
answer, but it settles a question.** Brier score, model weight vs market
weight:

| model / market | train | valid | test |
|---|---|---|---|
| 0% / 100% | 0.12727 | 0.12585 | 0.13874 |
| 10% / 90% | 0.12711 | **0.12583** | **0.13863** |
| 50% / 50% | 0.12717 | 0.12669 | 0.14055 |
| 100% / 0% | 0.12885 | 0.12985 | 0.14822 |

Kalshi's own price is a better forecast than our model in every period. The
best blend puts only 10-20% weight on the model and improves on the market by
about 0.1% — nothing. This is worth stating plainly: **the model is not a
better predictor of BTC than the market.** What it has is a narrow band
(70-90c, 10+ minutes) where its disagreement with the market is informative;
that is a different and much smaller claim, and blending destroys it (at 20%
model weight, one qualifying trade survives in 63 days).

**2. Horizon-aware volatility scaling — rejected.** Fitting a separate
z-divisor per minutes-remaining on train (0.56 at 1 minute rising to ~0.95 at
10+) improved Brier slightly on train and validation and made it worse on
test, and cut the trade rule's test return from +4.13% to +2.76%. The gain is
already captured by the global calibration curve.

**3. Requiring the setup to persist — accepted.** Entries at 10 minutes left
in the 70-90c window with edge >= 5%, split by whether the same side also
qualified at 12 minutes left:

| | train | valid | test | pooled |
|---|---|---|---|---|
| confirmed | 242, 87.6%, +6.5% | 65, 87.7%, +7.0% | 107, 87.9%, +8.4% | 414, 87.7%, +7.05% |
| not confirmed | 414, 82.1%, +3.8% | 139, 82.0%, +3.2% | 156, 81.4%, +3.6% | 708, 81.9%, +3.57% |

414 confirmed trades, 363 correct, break-even 82.0%, one-sided binomial
p = 0.0012. Checked at three other entry/confirm pairs (12/14, 8/10, 6/8):
confirmation raised the win rate in 11 of the 12 period-cells. Entry at 10
confirmed at 12 is both the strongest and the only pair positive in all three
periods, so that is the one wired into `check.py`.

Cost: roughly a third of the setups are discarded, about 6 a day rather than
20. Triple confirmation (12 and 14) was also tested and is too thin to judge
(n = 9 in validation).

Strategies tested to date: 105 in the model search, plus 11 direct
price-prediction variants, plus these 3. Nothing here changes the headline
conclusion — the edge is small, unproven on live money, and rests on the
market being the better forecaster in general.
