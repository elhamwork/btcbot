# What the bot has learned

Written 28 Oct 2026 8:19pm California time by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$867.69** (started $1,000, -13.2%) |
| best / worst it has been | $1,014.03 / $867.69 |
| fees paid | $7.21 |
| contracts looked at | 53 |
| of those, settled and learned from | 52 |
| actual calls (graded GOOD) | 6 |
| calls that have settled | 6 |
| alerts that reached the phone | 6 of 6 |
| calls right | 4 of 6 (67%) |
| break-even needed | 82% |
| paper P&L | -18.9% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 52 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 15-20% | 0.167 | 0.194 | 1 (1 hit) | +0.027 ** |
| 25-30% | 0.238 | 0.230 | 1 (0 hit) | -0.008 |
| 30-35% | 0.286 | 0.252 | 4 (0 hit) | -0.034 ** |
| 35-40% | 0.354 | 0.312 | 4 (0 hit) | -0.042 ** |
| 40-45% | 0.384 | 0.373 | 9 (3 hit) | -0.012 |
| 45-50% | 0.497 | 0.524 | 8 (5 hit) | +0.027 ** |
| 50-55% | 0.558 | 0.604 | 6 (5 hit) | +0.046 ** |
| 55-60% | 0.605 | 0.583 | 8 (4 hit) | -0.022 ** |
| 60-65% | 0.678 | 0.676 | 6 (4 hit) | -0.002 |
| 65-70% | 0.738 | 0.692 | 2 (0 hit) | -0.046 ** |
| 70-75% | 0.814 | 0.820 | 1 (1 hit) | +0.006 |
| 75-80% | 0.836 | 0.841 | 1 (1 hit) | +0.005 |
| 85-90% | 0.920 | 0.891 | 1 (0 hit) | -0.030 ** |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 16 |
| WEAK (50-70c) | 13 |
| BAD (cheap side) | 9 |
| WEAK (small disagreement) | 7 |
| GOOD | 6 |
| ALMOST (not confirmed yet) | 2 |

Leaned YES 33 times, NO 20 times. Over 63 days of history the
split is 49.5% YES, so anything near half and half is normal.

## Every call it has made

| placed | closed | side | price | BTC vs target | min left | result | paid | account after |
|---|---|---|---|---|---|---|---|---|
| 19:34 | 2026-10-28 19:45 | YES | 0.87 | +139 | 10 | RIGHT | +14.03 | $1,014.03 |
| 20:02 | 2026-10-28 20:15 | YES | 0.84 | +150 | 12 | **wrong** | -102.54 | $911.49 |
| 21:49 | 2026-10-28 22:00 | YES | 0.86 | +116 | 10 | RIGHT | +13.94 | $925.43 |
| 01:04 | 2026-10-29 01:15 | NO | 0.77 | -91 | 11 | RIGHT | +26.15 | $951.58 |
| 01:33 | 2026-10-29 01:45 | NO | 0.86 | -179 | 11 | RIGHT | +14.55 | $966.13 |
| 03:04 | 2026-10-29 03:15 | YES | 0.73 | +71 | 11 | **wrong** | -98.44 | $867.69 |

"BTC vs target" is how many dollars above (+) or below (-) the
target BTC was when the call was made. That number, the minutes
left, and how fast BTC had been moving are the whole basis of every
call -- so a losing row with a small gap and a lot of time left is
the bot being unlucky, and one with a big gap is it being wrong.

## Why the losses happened

| closed | side | price | edge | BTC vs target | min left |
|---|---|---|---|---|---|
| 10-28 20:15 | YES | 0.84 | 8% | +150 | 12 |
| 10-29 03:15 | YES | 0.73 | 11% | +70 | 11 |

| | n | avg price | avg edge | avg min left |
|---|---|---|---|---|
| won | 4 | 0.84 | 12% | 11 |
| lost | 2 | 0.78 | 10% | 12 |

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
