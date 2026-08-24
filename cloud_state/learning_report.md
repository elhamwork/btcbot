# What the bot has learned

Written 2026-08-24 02:23 UTC by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$1,000.00** (started $1,000, +0.0%) |
| best / worst it has been | $1,000.00 / $1,000.00 |
| fees paid | $0.00 |
| contracts looked at | 29 |
| retired (old rule, not counted) | 10 |
| of those, settled and learned from | 28 |
| actual calls (graded GOOD) | 0 |
| calls that have settled | 0 |

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
| 0-5% | 0.022 | 0.021 | 1 (0 hit) | -0.001 |
| 25-30% | 0.256 | 0.248 | 1 (0 hit) | -0.008 |
| 35-40% | 0.340 | 0.350 | 2 (1 hit) | +0.010 |
| 40-45% | 0.402 | 0.408 | 2 (1 hit) | +0.006 |
| 45-50% | 0.480 | 0.440 | 5 (1 hit) | -0.040 ** |
| 50-55% | 0.552 | 0.515 | 8 (3 hit) | -0.037 ** |
| 60-65% | 0.659 | 0.660 | 3 (2 hit) | +0.001 |
| 65-70% | 0.729 | 0.754 | 3 (3 hit) | +0.025 ** |
| 75-80% | 0.855 | 0.827 | 1 (0 hit) | -0.028 ** |
| 85-90% | 0.936 | 0.906 | 1 (0 hit) | -0.030 ** |

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
