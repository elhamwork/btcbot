# What the bot has learned

Written 2026-08-23 17:56 UTC by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$1,000.00** (started $1,000, +0.0%) |
| best / worst it has been | $1,000.00 / $1,000.00 |
| fees paid | $0.00 |
| contracts looked at | 1 |
| of those, settled and learned from | 0 |
| actual calls (graded GOOD) | 0 |
| calls that have settled | 0 |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 0 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|

Nothing has moved more than 0.02 yet. That is the expected state
early on and is not a fault.

## How it graded what it saw

| grade | times |
|---|---|
| WEAK (5-10 min) | 1 |

Leaned YES 1 times, NO 0 times. Over 63 days of history the
split is 49.5% YES, so anything near half and half is normal.

## What would change the conclusion

The backtest says setups like these hit 87.7% against an 82.0%
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
