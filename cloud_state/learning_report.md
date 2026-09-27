# What the bot has learned

Written 27 Sep 2026 11:25am California time by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$1,134.24** (started $1,000, +13.4%) |
| best / worst it has been | $1,154.38 / $1,000.00 |
| fees paid | $15.23 |
| contracts looked at | 74 |
| of those, settled and learned from | 73 |
| actual calls (graded GOOD) | 11 |
| calls that have settled | 10 |
| alerts that reached the phone | 11 of 11 |
| calls right | 9 of 10 (90%) |
| break-even needed | 80% |
| paper P&L | +12.9% per dollar staked |

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
| 10-15% | 0.071 | 0.069 | 1 (0 hit) | -0.002 |
| 25-30% | 0.238 | 0.230 | 1 (0 hit) | -0.008 |
| 30-35% | 0.286 | 0.276 | 1 (0 hit) | -0.009 |
| 35-40% | 0.354 | 0.361 | 5 (2 hit) | +0.007 |
| 40-45% | 0.384 | 0.409 | 8 (4 hit) | +0.024 ** |
| 45-50% | 0.497 | 0.540 | 18 (11 hit) | +0.043 ** |
| 50-55% | 0.558 | 0.585 | 14 (9 hit) | +0.027 ** |
| 55-60% | 0.605 | 0.604 | 10 (6 hit) | -0.001 |
| 60-65% | 0.678 | 0.719 | 8 (7 hit) | +0.041 ** |
| 70-75% | 0.814 | 0.800 | 3 (2 hit) | -0.013 |
| 75-80% | 0.836 | 0.815 | 2 (1 hit) | -0.021 ** |
| 80-85% | 0.885 | 0.856 | 1 (0 hit) | -0.029 ** |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 26 |
| BAD (cheap side) | 19 |
| WEAK (50-70c) | 12 |
| GOOD | 11 |
| WEAK (small disagreement) | 5 |
| WEAK (5-10 min) | 1 |

Leaned YES 55 times, NO 19 times. Over 63 days of history the
split is 49.5% YES, so anything near half and half is normal.

## Open right now

| placed | contract | side | price | risking | to win |
|---|---|---|---|---|---|
| 18:19 | KXBTC15M-26SEP271430-30 | YES | 0.75 | $113.42 | $35.82 |

These have been called but have not settled yet. A 15-minute
contract takes about that long, plus a minute or two for Kalshi to
publish the result, so this list is usually empty.

## Every call it has made

| placed | closed | side | price | BTC vs target | min left | result | paid | account after |
|---|---|---|---|---|---|---|---|---|
| 01:47 | 2026-09-27 02:00 | YES | 0.75 | +53 | 13 | RIGHT | +31.57 | $1,031.57 |
| 04:32 | 2026-09-27 04:45 | NO | 0.83 | -66 | 12 | RIGHT | +19.90 | $1,051.47 |
| 05:33 | 2026-09-27 05:45 | YES | 0.87 | +76 | 12 | RIGHT | +14.75 | $1,066.22 |
| 09:03 | 2026-09-27 09:15 | NO | 0.81 | -56 | 11 | RIGHT | +23.59 | $1,089.81 |
| 09:34 | 2026-09-27 09:45 | YES | 0.74 | +83 | 11 | RIGHT | +36.30 | $1,126.11 |
| 12:03 | 2026-09-27 12:15 | YES | 0.79 | +62 | 12 | RIGHT | +28.27 | $1,154.38 |
| 13:32 | 2026-09-27 13:45 | YES | 0.90 | +159 | 12 | **wrong** | -116.25 | $1,038.13 |
| 17:19 | 2026-09-27 17:30 | YES | 0.78 | +66 | 10 | RIGHT | +27.68 | $1,065.81 |
| 17:33 | 2026-09-27 17:45 | YES | 0.76 | +46 | 11 | RIGHT | +31.86 | $1,097.67 |
| 17:48 | 2026-09-27 18:00 | YES | 0.74 | +47 | 12 | RIGHT | +36.57 | $1,134.24 |

"BTC vs target" is how many dollars above (+) or below (-) the
target BTC was when the call was made. That number, the minutes
left, and how fast BTC had been moving are the whole basis of every
call -- so a losing row with a small gap and a lot of time left is
the bot being unlucky, and one with a big gap is it being wrong.

## Why the losses happened

| closed | side | price | edge | BTC vs target | min left |
|---|---|---|---|---|---|
| 09-27 13:45 | YES | 0.90 | 9% | +158 | 12 |

| | n | avg price | avg edge | avg min left |
|---|---|---|---|---|
| won | 9 | 0.79 | 13% | 11 |
| lost | 1 | 0.90 | 9% | 12 |

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
