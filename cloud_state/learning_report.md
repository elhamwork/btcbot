# What the bot has learned

Written 2026-08-24 12:37 UTC by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$1,002.54** (started $1,000, +0.3%) |
| best / worst it has been | $1,099.47 / $987.44 |
| fees paid | $8.86 |
| contracts looked at | 74 |
| retired (old rule, not counted) | 10 |
| of those, settled and learned from | 73 |
| actual calls (graded GOOD) | 6 |
| calls that have settled | 6 |
| calls right | 5 of 6 (83%) |
| break-even needed | 80% |
| paper P&L | +4.4% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 73 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.019 | 0.019 | 1 (0 hit) | -0.001 |
| 15-20% | 0.167 | 0.194 | 1 (1 hit) | +0.027 ** |
| 20-25% | 0.178 | 0.173 | 1 (0 hit) | -0.006 |
| 25-30% | 0.238 | 0.230 | 1 (0 hit) | -0.008 |
| 30-35% | 0.286 | 0.276 | 1 (0 hit) | -0.009 |
| 35-40% | 0.354 | 0.341 | 7 (2 hit) | -0.013 |
| 40-45% | 0.384 | 0.358 | 5 (1 hit) | -0.026 ** |
| 45-50% | 0.497 | 0.476 | 16 (7 hit) | -0.021 ** |
| 50-55% | 0.558 | 0.539 | 14 (7 hit) | -0.018 |
| 55-60% | 0.605 | 0.622 | 4 (3 hit) | +0.017 |
| 60-65% | 0.678 | 0.676 | 6 (4 hit) | -0.002 |
| 65-70% | 0.738 | 0.714 | 8 (5 hit) | -0.024 ** |
| 70-75% | 0.814 | 0.820 | 1 (1 hit) | +0.006 |
| 75-80% | 0.836 | 0.790 | 3 (1 hit) | -0.046 ** |
| 85-90% | 0.920 | 0.894 | 2 (1 hit) | -0.026 ** |
| 95-100% | 0.990 | 0.991 | 1 (1 hit) | +0.000 |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 25 |
| WEAK (50-70c) | 21 |
| BAD (cheap side) | 12 |
| BAD (last 5 min) | 6 |
| WEAK (small disagreement) | 5 |
| WEAK (5-10 min) | 2 |
| ALMOST (not confirmed yet) | 2 |
| GOOD | 1 |

Leaned YES 44 times, NO 30 times. Over 63 days of history the
split is 49.5% YES, so anything near half and half is normal.

## Every call it has made

| closed | side | price | BTC vs target | min left | result | paid | account after |
|---|---|---|---|---|---|---|---|
| 2026-08-24 04:15 | YES | 0.79 | +42 | 14 | RIGHT | +25.11 | $1,025.11 |
| 2026-08-24 04:30 | YES | 0.80 | +60 | 14 | RIGHT | +24.19 | $1,049.30 |
| 2026-08-24 06:45 | NO | 0.74 | -2 | 14 | RIGHT | +34.96 | $1,084.26 |
| 2026-08-24 07:00 | YES | 0.87 | +54 | 14 | RIGHT | +15.21 | $1,099.47 |
| 2026-08-24 08:00 | YES | 0.73 | -17 | 15 | **wrong** | -112.03 | $987.44 |
| 2026-08-24 09:15 | YES | 0.86 | -2 | 14 | RIGHT | +15.10 | $1,002.54 |

"BTC vs target" is how many dollars above (+) or below (-) the
target BTC was when the call was made. That number, the minutes
left, and how fast BTC had been moving are the whole basis of every
call -- so a losing row with a small gap and a lot of time left is
the bot being unlucky, and one with a big gap is it being wrong.

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
