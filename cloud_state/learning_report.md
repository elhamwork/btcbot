# What the bot has learned

Written 26 Sep 2026 7:54pm California time by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$1,031.57** (started $1,000, +3.2%) |
| best / worst it has been | $1,031.57 / $1,000.00 |
| fees paid | $1.76 |
| contracts looked at | 12 |
| of those, settled and learned from | 11 |
| actual calls (graded GOOD) | 1 |
| calls that have settled | 1 |
| alerts that reached the phone | 1 of 1 |
| calls right | 1 of 1 (100%) |
| break-even needed | 75% |
| paper P&L | +33.3% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 11 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.019 | 0.019 | 1 (0 hit) | -0.001 |
| 40-45% | 0.384 | 0.372 | 1 (0 hit) | -0.012 |
| 45-50% | 0.497 | 0.528 | 2 (2 hit) | +0.031 ** |
| 50-55% | 0.558 | 0.554 | 2 (1 hit) | -0.004 |
| 55-60% | 0.605 | 0.585 | 1 (0 hit) | -0.020 |
| 60-65% | 0.678 | 0.667 | 2 (1 hit) | -0.011 |
| 70-75% | 0.814 | 0.788 | 1 (0 hit) | -0.026 ** |
| 75-80% | 0.836 | 0.841 | 1 (1 hit) | +0.005 |

## How it graded what it saw

| grade | times |
|---|---|
| BAD (cheap side) | 4 |
| NONE (no disagreement) | 4 |
| WEAK (50-70c) | 2 |
| WEAK (5-10 min) | 1 |
| GOOD | 1 |

Leaned YES 9 times, NO 3 times. Over 63 days of history the
split is 49.5% YES, so anything near half and half is normal.

## Every call it has made

| placed | closed | side | price | BTC vs target | min left | result | paid | account after |
|---|---|---|---|---|---|---|---|---|
| 01:47 | 2026-09-27 02:00 | YES | 0.75 | +53 | 13 | RIGHT | +31.57 | $1,031.57 |

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
2. Size eventually bites, though later than once claimed. Measured
   from 3,130 live order-book snapshots, the median size at the best
   price is $3,062 and the median spread is 1c. A $1,000 order fills
   at the quoted price 73% of the time and within 5c always; a $2,500
   order fills at the quote 56% of the time. So the arithmetic holds
   to roughly a $25,000 account, not the $10,000 asserted before the
   book was actually recorded.

A first week -- about 40 calls -- lands between $814 and $1,908 in the
same simulation, and finishes below $1,000 about 17 times in 100.
That spread is what a week actually looks like.

Nothing here has been traded with real money.
