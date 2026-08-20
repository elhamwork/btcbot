# Data Quality Report

Dataset: **real** Kalshi `KXBTC15M` (BTC 15-minute binaries) + **real** Coinbase BTC/USD 1-minute OHLCV.

| | in | out | removed |
|---|---|---|---|
| Contracts | 1326 | 1323 | 3 |
| Candles | 19890 | 19845 | 45 |
| BTC minutes | 20161 | 20161 | 0 |

Period: `2026-08-06 04:30:00+00:00` -> `2026-08-20 04:15:00+00:00`

Outcome balance: **50.42% YES** -- consistent with a strike set at spot when the contract opens, i.e. a genuine coin flip.

## Checks

| Check | Detail | Rows | Action |
|---|---|---|---|
| BTC duplicate timestamps | identical minute repeated | 0 | none found |
| BTC gaps | 0 breaks totalling 0 missing minutes | 0 | left as gaps; NOT interpolated (would invent prices) |
| BTC impossible prices | non-positive or null OHLC | 0 | none found |
| BTC ordering | out-of-order timestamps | 0 | already sorted |
| Contract duplicates | same ticker twice | 0 | none found |
| Missing settlement | result not yes/no | 0 | none found |
| Non-finalized status | status != finalized | 0 | none found |
| Invalid strikes | null or non-positive floor_strike | 3 | removed |
| Contract duration | lifetime != 15 minutes | 0 | all exactly 15 min |
| Overlapping contracts | two contracts sharing a close time | 0 | none found |
| Contract cadence gaps | 5 breaks in the 15-min schedule, ~21 contracts absent from Kalshi | 21 | left as gaps; nothing invented to fill them |
| Timezone | all timestamps tz-aware UTC | 0 | verified UTC end to end |
| Candle duplicates | same ticker+minute twice | 0 | none found |
| Negative prices | bid or ask < 0 | 0 | none found |
| Prices above $1 | bid or ask > 1 | 0 | none found |
| Crossed quotes | ask < bid | 0 | none found |
| Null quotes | missing bid or ask | 0 | none found |
| Candles per contract | contracts without exactly 15 candles | 0 | every contract has all 15 |
| Contracts without quotes | no candle rows at all | 0 | none found |
| Settlement vs our BTC feed | Coinbase close at expiry reproduces Kalshi's result 92.28% of the time | 102 | NOT corrected -- Kalshi's `result` is the label; the feed difference is real measurement noise and is left in |
| BTC/Kalshi clock alignment | best shift by settlement = +0 min; best shift by strike-at-open = +0 min (0 = correctly aligned) | 0 | verified aligned |
| BTC coverage at expiry | contracts whose close time has no BTC bar | 1 | excluded from the panel |
| Strike vs spot at open | median |strike - BTC at open| = $6.10 (strike is set at spot) | 0 | informational |

## Known limitations

1. **Settlement source differs from our price feed.** Coinbase's close at expiry reproduces Kalshi's settled result only **92.28%** of the time. Disagreements cluster where the outcome is nearly tied (median |BTC - strike| of $7.70 on disagreements versus $32.97 overall), so this is a feed/index difference on coin-flip cases, not an error. Kalshi's `result` is always used as the label; the mismatch enters as irreducible feature noise, which makes the model's task harder rather than easier. It cannot manufacture an edge -- it can only hide one.

2. **No order-book depth.** Candlesticks give best bid and best ask per minute, not full depth or resting size. Fills are assumed at the quoted ask for the whole position. Large sizes would move the market; position sizes here are small enough that this is a modest assumption, but it is an assumption.

3. **Minute resolution.** The 30-second decision point in the original specification is not observable. Entry points run 14 down to 1 minute.

4. **14 days.** 1,326 contracts is a real but short sample. Every result carries a bootstrap confidence interval for this reason.

5. **Fee schedule unverified.** Kalshi's published formula `ceil(0.07 x C x P x (1-P))` is applied on entry, but `docs.kalshi.com` was unreachable from the build environment, so it is flagged `FEE_SCHEDULE_VERIFIED_LIVE = False` in `config.py`.

Nothing was interpolated, back-filled, or synthesised. Gaps stay gaps.
