# What the research says, and what survived contact with our data

Searched August 2026. Every claim below was re-tested against our own 6,000
KXBTC15M contracts rather than taken on trust.

## 1. Favourite–longshot bias — CONFIRMED, and we are already exploiting it

The best-documented edge in prediction markets. An analysis of 300,000+ Kalshi
contracts finds low-priced contracts win far less often than break-even, while
high-priced contracts win slightly more often. It replicates cleanly in our
data — every contract at 10 minutes left, buying YES at the ask:

| price paid | n | won | break-even | edge |
|---|---|---|---|---|
| 10-20c | 524 | 11.1% | 16.3% | **-5.2** |
| 20-30c | 676 | 20.9% | 25.8% | -4.9 |
| 40-50c | 794 | 42.4% | 46.3% | -3.9 |
| 60-70c | 730 | 66.2% | 66.2% | -0.0 |
| 70-80c | 667 | 75.9% | 75.5% | **+0.4** |
| 80-90c | 557 | 86.0% | 85.2% | **+0.8** |
| 90-98c | 279 | 93.9% | 92.9% | **+1.0** |

Our 70–90c window was chosen empirically before this search. It lands exactly
on the profitable side of a bias the literature independently documents. That
is the strongest external support this project has.

**But note the size.** The structural bias in 70–90c is worth about +0.6
points. Our filtered strategy claims +8. So roughly nine tenths of our claimed
edge comes from the model, not from the bias — and the model's contribution is
the part with no external corroboration.

## 2. Takers lose to makers — a warning we cannot test

An analysis of 72.1 million Kalshi trades finds a persistent transfer from
liquidity takers to makers: makers earn roughly +2.5% per trade, takers lose
about the same. The same work notes financial markets on Kalshi are more
efficient than sports and entertainment, where the bias is largest.

**We are takers.** Every trade in this project buys at the ask. The spread cost
is already inside our numbers, but the adverse-selection component — that a
resting order fills preferentially when the taker is wrong — is not, and cannot
be measured from historical quotes. This remains the single largest
unquantified risk, and the literature says it is real and systematic.

## 3. HAR-RV volatility forecasting — TESTED, REJECTED

Papers on Bitcoin realized volatility report that HAR models, which blend
short, medium and long horizons, beat single-window estimates at short
horizons. Our model uses one window (15 minutes), so this was the most
promising concrete import.

Fitted on the training period, predicting the realised move to settlement from
rv_1m, rv_5m, rv_15m and ATR:

| volatility estimate | train | unseen |
|---|---|---|
| rv_15m only (current) | 89.8%, +10.33% | **88.7%, +10.38%** |
| HAR blend | 88.5%, +9.00% | 86.3%, +7.15% |
| half and half | 91.0%, +12.61% | 85.7%, +6.62% |

Worse on unseen data both ways. The fitted HAR gave rv_15m a *negative*
coefficient, a collinearity signature; and "half and half" scoring best on
train and worst on unseen is the textbook overfit pattern. Not adopted.

## 3b. Signed semi-variance — TESTED, REJECTED

The same volatility literature reports that separating upward from downward
realized variance beats a single symmetric number for crypto at short
horizons. It is principled here too: a YES bet only fears downward moves, a
NO bet only fears upward ones, and we currently price both with one
symmetric volatility.

Built from the 1-minute bars (bar-end aligned, same look-ahead fix as
everywhere else), using downside semi-deviation to price YES and upside to
price NO:

| volatility | train | unseen | overall |
|---|---|---|---|
| symmetric (current) | 89.8%, +10.33% | **88.7%, +10.38%** | 89.3%, +10.35% |
| directional, 15 min | 85.8%, +3.61% | 88.7%, +7.84% | 86.9%, +5.31% |
| directional, 30 min | 88.0%, +6.82% | 84.6%, +2.97% | 86.6%, +5.20% |
| half symmetric, half signed | 87.8%, +6.62% | 86.2%, +5.56% | 87.2%, +6.20% |

Worse in every variant. It also more than doubles the trade count (597 vs
272), which is the tell: the asymmetric estimate is smaller on one side, so
it manufactures confidence and lets marginal setups through. Not adopted.

## 4. Intraday momentum and reversal — consistent with what we already found

Papers report intraday momentum and reversal in crypto at intraday
frequencies, varying with jumps, announcements and liquidity. We tested
momentum drift and every technical indicator available earlier in this project
and all degraded validation performance. The literature's horizons are hours,
ours is fifteen minutes; the effects it documents are probably real and
probably not reachable here.

## 5. On a 90% win rate

Achievable, and cheaply — but it is not what you want.

Buying **every** contract in a band, no model at all:

| band | per day | win rate | return/$ | $1,000 over 63 days |
|---|---|---|---|---|
| 70-90c | 19 | 80.5% | +0.67% | $422 |
| **85-95c** | 8 | **91.5%** | +1.79% | $1,878 |
| 90-98c | 4 | 93.9% | +1.09% | $1,224 |
| our strategy | 4.3 | 89.3% | **+10.35%** | **$13,187** |

A 91.5% win rate is available today by buying dear contracts blindly. It earns
a sixth as much. Win rate is a function of the price paid, not of skill, and
optimising for it means paying more for less.

Also worth noting: buying all of 70–90c blindly *loses* money at 10% staking.
The band alone is not the strategy; the filter is doing the work.

## Sources

- Becker, *The Microstructure of Wealth Transfer in Prediction Markets* (72.1M Kalshi trades)
- *Makers or Takers: The Economics of the Kalshi Prediction Market*, GWU
- *Intraday return predictability in the cryptocurrency markets: Momentum, reversal, or both*
- *Forecasting Bitcoin realized volatility by exploiting measurement error under model uncertainty*
- *Stylized Facts of High-Frequency Bitcoin Time Series*
