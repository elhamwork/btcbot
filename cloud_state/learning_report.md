# What the bot has learned

Written 26 Aug 2026 3:29am California time by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$1,078.80** (started $1,000, +7.9%) |
| best / worst it has been | $1,214.01 / $926.62 |
| fees paid | $55.41 |
| contracts looked at | 257 |
| retired (old rule, not counted) | 10 |
| of those, settled and learned from | 256 |
| actual calls (graded GOOD) | 38 |
| calls that have settled | 38 |
| calls right | 32 of 38 (84%) |
| break-even needed | 81% |
| paper P&L | +4.6% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 256 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.019 | 0.018 | 2 (0 hit) | -0.001 |
| 5-10% | 0.044 | 0.042 | 1 (0 hit) | -0.001 |
| 15-20% | 0.167 | 0.194 | 1 (1 hit) | +0.027 ** |
| 20-25% | 0.178 | 0.173 | 1 (0 hit) | -0.006 |
| 25-30% | 0.238 | 0.210 | 4 (0 hit) | -0.028 ** |
| 30-35% | 0.286 | 0.266 | 6 (1 hit) | -0.020 |
| 35-40% | 0.354 | 0.339 | 25 (8 hit) | -0.015 |
| 40-45% | 0.384 | 0.378 | 27 (10 hit) | -0.007 |
| 45-50% | 0.497 | 0.492 | 43 (21 hit) | -0.005 |
| 50-55% | 0.558 | 0.521 | 54 (27 hit) | -0.037 ** |
| 55-60% | 0.605 | 0.553 | 39 (20 hit) | -0.052 ** |
| 60-65% | 0.678 | 0.687 | 20 (14 hit) | +0.009 |
| 65-70% | 0.738 | 0.699 | 16 (10 hit) | -0.039 ** |
| 70-75% | 0.814 | 0.836 | 4 (4 hit) | +0.022 ** |
| 75-80% | 0.836 | 0.802 | 5 (3 hit) | -0.034 ** |
| 80-85% | 0.885 | 0.892 | 2 (2 hit) | +0.007 |
| 85-90% | 0.920 | 0.897 | 3 (2 hit) | -0.023 ** |
| 95-100% | 0.990 | 0.991 | 2 (2 hit) | +0.001 |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 106 |
| WEAK (50-70c) | 69 |
| GOOD | 30 |
| BAD (cheap side) | 27 |
| WEAK (small disagreement) | 11 |
| BAD (last 5 min) | 8 |
| WEAK (5-10 min) | 3 |
| ALMOST (not confirmed yet) | 3 |

Leaned YES 154 times, NO 103 times. Over 63 days of history the
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
| 12:45 | 2026-08-24 13:00 | YES | 0.84 | +47 | 15 | RIGHT | +17.97 | $1,020.51 |
| 13:30 | 2026-08-24 13:45 | NO | 0.75 | -39 | 15 | RIGHT | +32.23 | $1,052.74 |
| 14:00 | 2026-08-24 14:15 | YES | 0.80 | +68 | 14 | RIGHT | +24.84 | $1,077.58 |
| 17:02 | 2026-08-24 17:15 | NO | 0.88 | -421 | 12 | **wrong** | -108.67 | $968.91 |
| 18:03 | 2026-08-24 18:15 | YES | 0.76 | +139 | 11 | RIGHT | +28.97 | $997.88 |
| 19:19 | 2026-08-24 19:30 | NO | 0.85 | -339 | 11 | RIGHT | +16.56 | $1,014.44 |
| 00:19 | 2026-08-25 00:30 | NO | 0.85 | -183 | 10 | RIGHT | +16.83 | $1,031.27 |
| 01:04 | 2026-08-25 01:15 | YES | 0.79 | +194 | 10 | **wrong** | -104.65 | $926.62 |
| 03:33 | 2026-08-25 03:45 | YES | 0.80 | +172 | 11 | RIGHT | +21.86 | $948.49 |
| 05:04 | 2026-08-25 05:15 | YES | 0.80 | +147 | 10 | RIGHT | +22.38 | $970.87 |
| 05:34 | 2026-08-25 05:45 | YES | 0.74 | +115 | 10 | RIGHT | +32.34 | $1,003.21 |
| 07:03 | 2026-08-25 07:15 | YES | 0.75 | +134 | 12 | RIGHT | +31.68 | $1,034.89 |
| 08:18 | 2026-08-25 08:30 | YES | 0.79 | +118 | 12 | RIGHT | +25.98 | $1,060.87 |
| 08:49 | 2026-08-25 09:00 | NO | 0.84 | -181 | 11 | RIGHT | +19.02 | $1,079.89 |
| 09:03 | 2026-08-25 09:15 | NO | 0.83 | -128 | 12 | RIGHT | +20.83 | $1,100.72 |
| 09:47 | 2026-08-25 10:00 | NO | 0.78 | -152 | 12 | RIGHT | +29.35 | $1,130.07 |
| 10:47 | 2026-08-25 11:00 | YES | 0.90 | +191 | 12 | RIGHT | +11.76 | $1,141.83 |
| 11:34 | 2026-08-25 11:45 | YES | 0.74 | +99 | 11 | **wrong** | -116.26 | $1,025.57 |
| 12:04 | 2026-08-25 12:15 | NO | 0.84 | -179 | 10 | RIGHT | +18.39 | $1,043.96 |
| 12:49 | 2026-08-25 13:00 | YES | 0.82 | +136 | 10 | RIGHT | +21.60 | $1,065.56 |
| 16:34 | 2026-08-25 16:45 | YES | 0.88 | +190 | 10 | RIGHT | +13.63 | $1,079.19 |
| 18:34 | 2026-08-25 18:45 | NO | 0.81 | -99 | 10 | RIGHT | +23.87 | $1,103.06 |
| 23:03 | 2026-08-25 23:15 | YES | 0.70 | +83 | 12 | RIGHT | +44.96 | $1,148.02 |
| 23:49 | 2026-08-26 00:00 | NO | 0.75 | -83 | 10 | RIGHT | +36.26 | $1,184.28 |
| 01:04 | 2026-08-26 01:15 | YES | 0.79 | +155 | 10 | RIGHT | +29.73 | $1,214.01 |
| 01:19 | 2026-08-26 01:30 | YES | 0.75 | +112 | 10 | **wrong** | -123.53 | $1,090.48 |
| 01:33 | 2026-08-26 01:45 | YES | 0.88 | +183 | 12 | RIGHT | +13.95 | $1,104.43 |
| 03:19 | 2026-08-26 03:30 | NO | 0.83 | -75 | 10 | RIGHT | +21.30 | $1,125.73 |
| 04:03 | 2026-08-26 04:15 | NO | 0.79 | -117 | 11 | RIGHT | +28.26 | $1,153.99 |
| 04:48 | 2026-08-26 05:00 | NO | 0.77 | -131 | 12 | RIGHT | +32.61 | $1,186.60 |
| 09:17 | 2026-08-26 09:30 | NO | 0.89 | -271 | 12 | RIGHT | +13.75 | $1,200.35 |
| 10:04 | 2026-08-26 10:15 | NO | 0.82 | -127 | 10 | **wrong** | -121.55 | $1,078.80 |

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
| 08-25 11:45 | YES | 0.74 | 10% | +98 | 11 |
| 08-26 01:30 | YES | 0.75 | 14% | +111 | 10 |
| 08-26 10:15 | NO | 0.82 | 14% | -126 | 10 |

| | n | avg price | avg edge | avg min left |
|---|---|---|---|---|
| won | 32 | 0.81 | 11% | 12 |
| lost | 6 | 0.79 | 11% | 11 |

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
