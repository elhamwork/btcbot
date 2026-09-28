# What the bot has learned

Written 28 Sep 2026 4:14pm California time by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$750.37** (started $1,000, -25.0%) |
| best / worst it has been | $1,211.12 / $662.33 |
| fees paid | $42.73 |
| contracts looked at | 189 |
| of those, settled and learned from | 188 |
| actual calls (graded GOOD) | 29 |
| calls that have settled | 29 |
| alerts that reached the phone | 29 of 29 |
| calls right | 21 of 29 (72%) |
| break-even needed | 78% |
| paper P&L | -7.3% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 188 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.019 | 0.019 | 1 (0 hit) | -0.001 |
| 10-15% | 0.071 | 0.069 | 1 (0 hit) | -0.002 |
| 15-20% | 0.167 | 0.194 | 1 (1 hit) | +0.027 ** |
| 25-30% | 0.238 | 0.210 | 4 (0 hit) | -0.028 ** |
| 30-35% | 0.286 | 0.273 | 5 (1 hit) | -0.012 |
| 35-40% | 0.354 | 0.458 | 15 (10 hit) | +0.104 ** |
| 40-45% | 0.384 | 0.474 | 26 (15 hit) | +0.089 ** |
| 45-50% | 0.497 | 0.514 | 36 (19 hit) | +0.017 |
| 50-55% | 0.558 | 0.590 | 34 (21 hit) | +0.032 ** |
| 55-60% | 0.605 | 0.574 | 26 (14 hit) | -0.031 ** |
| 60-65% | 0.678 | 0.632 | 18 (10 hit) | -0.046 ** |
| 65-70% | 0.738 | 0.696 | 9 (5 hit) | -0.042 ** |
| 70-75% | 0.814 | 0.812 | 5 (4 hit) | -0.002 |
| 75-80% | 0.836 | 0.820 | 3 (2 hit) | -0.015 |
| 80-85% | 0.885 | 0.861 | 2 (1 hit) | -0.024 ** |
| 85-90% | 0.920 | 0.923 | 1 (1 hit) | +0.003 |
| 90-95% | 0.953 | 0.922 | 1 (0 hit) | -0.031 ** |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 66 |
| WEAK (50-70c) | 39 |
| BAD (cheap side) | 38 |
| GOOD | 29 |
| WEAK (small disagreement) | 15 |
| WEAK (5-10 min) | 1 |
| ALMOST (not confirmed yet) | 1 |

Leaned YES 133 times, NO 56 times. Over 63 days of history the
split is 49.5% YES, so anything near half and half is normal.

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
| 18:19 | 2026-09-27 18:30 | YES | 0.75 | +47 | 10 | RIGHT | +35.82 | $1,170.06 |
| 23:04 | 2026-09-27 23:15 | YES | 0.73 | +50 | 10 | RIGHT | +41.06 | $1,211.12 |
| 00:03 | 2026-09-28 00:15 | YES | 0.79 | +103 | 11 | **wrong** | -122.90 | $1,088.22 |
| 00:18 | 2026-09-28 00:30 | YES | 0.85 | +135 | 11 | RIGHT | +18.05 | $1,106.27 |
| 02:34 | 2026-09-28 02:45 | NO | 0.83 | -152 | 10 | RIGHT | +21.34 | $1,127.61 |
| 03:02 | 2026-09-28 03:15 | YES | 0.74 | +79 | 12 | RIGHT | +37.56 | $1,165.17 |
| 04:04 | 2026-09-28 04:15 | NO | 0.72 | -92 | 10 | **wrong** | -118.81 | $1,046.36 |
| 04:49 | 2026-09-28 05:00 | NO | 0.72 | -56 | 10 | **wrong** | -106.70 | $939.66 |
| 05:34 | 2026-09-28 05:45 | NO | 0.85 | -164 | 10 | **wrong** | -94.96 | $844.70 |
| 07:04 | 2026-09-28 07:15 | YES | 0.72 | +69 | 10 | **wrong** | -86.13 | $758.57 |
| 07:19 | 2026-09-28 07:30 | YES | 0.78 | +74 | 10 | **wrong** | -77.03 | $681.54 |
| 08:48 | 2026-09-28 09:00 | YES | 0.70 | +55 | 11 | RIGHT | +27.77 | $709.31 |
| 10:18 | 2026-09-28 10:30 | YES | 0.71 | +79 | 12 | RIGHT | +27.53 | $736.84 |
| 11:49 | 2026-09-28 12:00 | NO | 0.84 | -76 | 10 | **wrong** | -74.51 | $662.33 |
| 12:47 | 2026-09-28 13:00 | YES | 0.74 | +93 | 12 | RIGHT | +22.06 | $684.39 |
| 13:03 | 2026-09-28 13:15 | NO | 0.85 | -163 | 11 | RIGHT | +11.36 | $695.75 |
| 21:02 | 2026-09-28 21:15 | YES | 0.73 | +87 | 12 | RIGHT | +24.42 | $720.17 |
| 21:19 | 2026-09-28 21:30 | NO | 0.80 | -72 | 10 | RIGHT | +16.99 | $737.16 |
| 22:34 | 2026-09-28 22:45 | YES | 0.84 | +81 | 10 | RIGHT | +13.21 | $750.37 |

"BTC vs target" is how many dollars above (+) or below (-) the
target BTC was when the call was made. That number, the minutes
left, and how fast BTC had been moving are the whole basis of every
call -- so a losing row with a small gap and a lot of time left is
the bot being unlucky, and one with a big gap is it being wrong.

## Why the losses happened

| closed | side | price | edge | BTC vs target | min left |
|---|---|---|---|---|---|
| 09-27 13:45 | YES | 0.90 | 9% | +158 | 12 |
| 09-28 00:15 | YES | 0.79 | 13% | +103 | 11 |
| 09-28 04:15 | NO | 0.72 | 11% | -91 | 10 |
| 09-28 05:00 | NO | 0.72 | 9% | -55 | 10 |
| 09-28 05:45 | NO | 0.85 | 11% | -164 | 10 |
| 09-28 07:15 | YES | 0.72 | 10% | +68 | 10 |
| 09-28 07:30 | YES | 0.78 | 8% | +74 | 10 |
| 09-28 12:00 | NO | 0.84 | 9% | -76 | 10 |

| | n | avg price | avg edge | avg min left |
|---|---|---|---|---|
| won | 21 | 0.78 | 12% | 11 |
| lost | 8 | 0.79 | 10% | 11 |

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
