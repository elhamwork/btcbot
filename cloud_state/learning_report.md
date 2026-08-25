# What the bot has learned

Written 2026-08-25 05:26 UTC by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$970.88** (started $1,000, -2.9%) |
| best / worst it has been | $1,099.47 / $926.64 |
| fees paid | $22.05 |
| contracts looked at | 141 |
| retired (old rule, not counted) | 10 |
| of those, settled and learned from | 140 |
| actual calls (graded GOOD) | 16 |
| calls that have settled | 16 |
| calls right | 13 of 16 (81%) |
| break-even needed | 81% |
| paper P&L | +0.7% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 140 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.019 | 0.018 | 2 (0 hit) | -0.001 |
| 5-10% | 0.044 | 0.042 | 1 (0 hit) | -0.001 |
| 15-20% | 0.167 | 0.194 | 1 (1 hit) | +0.027 ** |
| 20-25% | 0.178 | 0.173 | 1 (0 hit) | -0.006 |
| 25-30% | 0.238 | 0.223 | 2 (0 hit) | -0.015 |
| 30-35% | 0.286 | 0.299 | 2 (1 hit) | +0.013 |
| 35-40% | 0.354 | 0.324 | 12 (3 hit) | -0.030 ** |
| 40-45% | 0.384 | 0.345 | 15 (4 hit) | -0.039 ** |
| 45-50% | 0.497 | 0.498 | 24 (12 hit) | +0.001 |
| 50-55% | 0.558 | 0.538 | 29 (15 hit) | -0.020 |
| 55-60% | 0.605 | 0.655 | 13 (10 hit) | +0.050 ** |
| 60-65% | 0.678 | 0.691 | 11 (8 hit) | +0.013 |
| 65-70% | 0.738 | 0.694 | 12 (7 hit) | -0.044 ** |
| 70-75% | 0.814 | 0.836 | 4 (4 hit) | +0.022 ** |
| 75-80% | 0.836 | 0.796 | 4 (2 hit) | -0.040 ** |
| 80-85% | 0.885 | 0.892 | 2 (2 hit) | +0.007 |
| 85-90% | 0.920 | 0.894 | 2 (1 hit) | -0.026 ** |
| 95-100% | 0.990 | 0.991 | 2 (2 hit) | +0.001 |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 55 |
| WEAK (50-70c) | 37 |
| BAD (cheap side) | 18 |
| WEAK (small disagreement) | 9 |
| GOOD | 8 |
| BAD (last 5 min) | 8 |
| WEAK (5-10 min) | 3 |
| ALMOST (not confirmed yet) | 3 |

Leaned YES 84 times, NO 57 times. Over 63 days of history the
split is 49.5% YES, so anything near half and half is normal.

## Every call it has made

| placed | closed | side | price | BTC vs target | min left | result | paid | account after |
|---|---|---|---|---|---|---|---|---|
| 04:00 | 2026-08-24 04:15 | YES | 0.79 | +42 | 14 | RIGHT | +25.11 | $1,025.11 |
| 04:15 | 2026-08-24 04:30 | YES | 0.80 | +60 | 14 | RIGHT | +24.19 | $1,049.30 |
| 06:30 | 2026-08-24 06:45 | NO | 0.74 | -2 | 14 | RIGHT | +34.96 | $1,084.26 |
| 06:45 | 2026-08-24 07:00 | YES | 0.87 | +54 | 14 | RIGHT | +15.21 | $1,099.47 |
| 07:45 | 2026-08-24 08:00 | YES | 0.73 | -17 | 15 | **wrong** | -112.03 | $987.44 |
| 09:00 | 2026-08-24 09:15 | YES | 0.86 | -2 | 14 | RIGHT | +15.10 | $1,002.54 |
| 12:45 | 2026-08-24 13:00 | YES | 0.84 | +47 | 15 | RIGHT | +17.98 | $1,020.52 |
| 13:30 | 2026-08-24 13:45 | NO | 0.75 | -39 | 15 | RIGHT | +32.23 | $1,052.75 |
| 14:00 | 2026-08-24 14:15 | YES | 0.80 | +68 | 14 | RIGHT | +24.85 | $1,077.60 |
| 17:02 | 2026-08-24 17:15 | NO | 0.88 | -421 | 12 | **wrong** | -108.67 | $968.93 |
| 18:03 | 2026-08-24 18:15 | YES | 0.76 | +139 | 11 | RIGHT | +28.97 | $997.90 |
| 19:19 | 2026-08-24 19:30 | NO | 0.85 | -339 | 11 | RIGHT | +16.56 | $1,014.46 |
| 00:19 | 2026-08-25 00:30 | NO | 0.85 | -183 | 10 | RIGHT | +16.83 | $1,031.29 |
| 01:04 | 2026-08-25 01:15 | YES | 0.79 | +194 | 10 | **wrong** | -104.65 | $926.64 |
| 03:33 | 2026-08-25 03:45 | YES | 0.80 | +172 | 11 | RIGHT | +21.86 | $948.50 |
| 05:04 | 2026-08-25 05:15 | YES | 0.80 | +147 | 10 | RIGHT | +22.38 | $970.88 |

**The 11 rows above dated before 24 Aug 19:00 UTC may show a stale
"BTC vs target".** Until then a contract first seen as a decline
kept the distance from that first look, not from the moment it was
called -- so a call made once BTC had crossed the line can appear
to have been made well short of it. The side, price, result and
money on those rows are correct; only the distance and the minutes
may be from a few minutes earlier. Rows after that are recorded at
the moment of the call.

"BTC vs target" is how many dollars above (+) or below (-) the
target BTC was when the call was made. That number, the minutes
left, and how fast BTC had been moving are the whole basis of every
call -- so a losing row with a small gap and a lot of time left is
the bot being unlucky, and one with a big gap is it being wrong.

## Why the losses happened

| closed | side | price | edge | BTC vs target | min left |
|---|---|---|---|---|---|
| 08-24 08:00 | YES | 0.73 | 9% | -16 | 15 |
| 08-24 17:15 | NO | 0.88 | 8% | -420 | 12 |
| 08-25 01:15 | YES | 0.79 | 10% | +193 | 10 |

| | n | avg price | avg edge | avg min left |
|---|---|---|---|---|
| won | 13 | 0.81 | 11% | 13 |
| lost | 3 | 0.80 | 9% | 12 |

**Read this as a thermometer, not a filter.** A rule fitted to
avoid these particular losses was built and measured: it reached a
100% win rate on the losses it had studied and did *worse than
nothing* on new trades. It memorised them; it did not learn from
them. Losing trades in the 63-day study had, if anything, slightly
*more* edge than winners -- 11.6 points against 11.4 -- and the
biggest signals ever taken include two losses. They are not
distinguishable in advance, and that is not a gap in the bot: a
contract trades at 80c precisely because nobody knows which fifth
of them fail.

What this table is for is spotting a pattern that is *large and
persistent* -- losses clustered at one price, one time of day, one
side -- over dozens of trades, not three. If one appears here and
holds up, it is worth acting on. Until then it is a thermometer.

## What would change the conclusion

The backtest says setups like these hit 89.3% against an 81.3%
break-even. To tell whether that is real rather than 63 lucky days,
this needs roughly 100 settled calls. At about 6 a day that is two to
three weeks of leaving `--loop` running. Below that number, a good
run and a bad run look identical.

## About the paper account

$1,000 to start, 10% of whatever it is worth on each call. Imaginary.
Nothing is sent to Kalshi and there is no account behind it.

Run over the 272 confirmed trades from the 63-day study, in the order
they happened, $1,000 at 10% a call ends at **$13,187**, dipping to
$899 on the way -- a 29% drawdown. Two reasons not to plan around that:

1. The price window and the confirmation rule were both chosen after
   looking at all three periods. Some of that 12x is the choosing.
2. It is not fillable. A 15-minute market trades on the order of ten
   thousand contracts in its entire life. A few hundred contracts is
   fine; a few thousand moves the price against you. Past roughly
   $10,000 the arithmetic stops describing anything that could happen.

A first week -- about 40 calls -- lands between $814 and $1,908 in the
same simulation, and finishes below $1,000 about 17 times in 100.
That spread is what a week actually looks like.

Nothing here has been traded with real money.
