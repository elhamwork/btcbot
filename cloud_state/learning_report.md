# What the bot has learned

Written 2026-08-24 01:29 UTC by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$1,142.11** (started $1,000, +14.2%) |
| best / worst it has been | $1,234.28 / $1,000.00 |
| fees paid | $16.90 |
| contracts looked at | 29 |
| of those, settled and learned from | 28 |
| actual calls (graded GOOD) | 10 |
| calls that have settled | 10 |
| calls right | 9 of 10 (90%) |
| break-even needed | 78% |
| paper P&L | +14.9% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 28 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.026 | 0.025 | 1 (0 hit) | -0.001 |
| 25-30% | 0.283 | 0.273 | 1 (0 hit) | -0.009 |
| 35-40% | 0.393 | 0.399 | 2 (1 hit) | +0.007 |
| 40-45% | 0.473 | 0.475 | 2 (1 hit) | +0.002 |
| 45-50% | 0.541 | 0.492 | 5 (1 hit) | -0.049 ** |
| 50-55% | 0.605 | 0.557 | 8 (3 hit) | -0.049 ** |
| 60-65% | 0.723 | 0.717 | 3 (2 hit) | -0.005 |
| 65-70% | 0.799 | 0.817 | 3 (3 hit) | +0.018 |
| 75-80% | 0.877 | 0.849 | 1 (0 hit) | -0.028 ** |
| 85-90% | 0.946 | 0.915 | 1 (0 hit) | -0.030 ** |

## How it graded what it saw

| grade | times |
|---|---|
| WEAK (50-70c) | 13 |
| NONE (no disagreement) | 7 |
| BAD (cheap side) | 5 |
| WEAK (5-10 min) | 1 |
| GOOD | 1 |
| BAD (last 5 min) | 1 |
| ALMOST (not confirmed yet) | 1 |

Leaned YES 18 times, NO 11 times. Over 63 days of history the
split is 49.5% YES, so anything near half and half is normal.

## Every call it has made

| closed | side | price | BTC vs target | min left | result | paid | account after |
|---|---|---|---|---|---|---|---|
| 2026-08-23 18:45 | NO | 0.71 | - | 14 | RIGHT | +38.82 | $1,038.82 |
| 2026-08-23 19:30 | YES | 0.76 | - | 11 | RIGHT | +31.05 | $1,069.87 |
| 2026-08-23 20:15 | NO | 0.72 | - | 14 | RIGHT | +39.51 | $1,109.38 |
| 2026-08-23 21:15 | YES | 0.89 | - | 14 | RIGHT | +12.86 | $1,122.24 |
| 2026-08-23 21:30 | YES | 0.88 | - | 15 | RIGHT | +14.36 | $1,136.60 |
| 2026-08-23 22:00 | YES | 0.74 | - | 14 | RIGHT | +37.86 | $1,174.46 |
| 2026-08-23 23:15 | NO | 0.86 | - | 14 | RIGHT | +17.97 | $1,192.43 |
| 2026-08-23 23:30 | YES | 0.73 | - | 14 | RIGHT | +41.85 | $1,234.28 |
| 2026-08-23 23:45 | YES | 0.78 | - | 14 | **wrong** | -125.33 | $1,108.95 |
| 2026-08-24 00:00 | YES | 0.76 | - | 15 | RIGHT | +33.16 | $1,142.11 |

"BTC vs target" is how many dollars above (+) or below (-) the
target BTC was when the call was made. That number, the minutes
left, and how fast BTC had been moving are the whole basis of every
call -- so a losing row with a small gap and a lot of time left is
the bot being unlucky, and one with a big gap is it being wrong.

## What would change the conclusion

The backtest says setups like these hit 89.3% against an 81.7%
break-even. To tell whether that is real rather than 63 lucky days,
this needs roughly 100 settled calls. At about 6 a day that is two to
three weeks of leaving `--loop` running. Below that number, a good
run and a bad run look identical.

## About the paper account

$1,000 to start, 10% of whatever it is worth on each call. Imaginary.
Nothing is sent to Kalshi and there is no account behind it.

Run over the 414 confirmed trades from the 63-day study, in the order
they happened, $1,000 at 10% a call ends at **$12,613**, dipping to
$727 on the way. Two reasons not to plan around that:

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
