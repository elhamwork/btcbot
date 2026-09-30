# What the bot has learned

Written 30 Sep 2026 4:58pm California time by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$1,167.50** (started $1,000, +16.8%) |
| best / worst it has been | $1,211.12 / $650.62 |
| fees paid | $83.18 |
| contracts looked at | 382 |
| of those, settled and learned from | 381 |
| actual calls (graded GOOD) | 59 |
| calls that have settled | 59 |
| alerts that reached the phone | 59 of 59 |
| calls right | 48 of 59 (81%) |
| break-even needed | 78% |
| paper P&L | +4.5% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 381 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.019 | 0.019 | 1 (0 hit) | -0.001 |
| 10-15% | 0.071 | 0.067 | 2 (0 hit) | -0.004 |
| 15-20% | 0.167 | 0.188 | 2 (1 hit) | +0.021 ** |
| 20-25% | 0.178 | 0.167 | 2 (0 hit) | -0.011 |
| 25-30% | 0.238 | 0.198 | 6 (0 hit) | -0.040 ** |
| 30-35% | 0.286 | 0.279 | 15 (4 hit) | -0.006 |
| 35-40% | 0.354 | 0.410 | 30 (14 hit) | +0.056 ** |
| 40-45% | 0.384 | 0.399 | 49 (20 hit) | +0.015 |
| 45-50% | 0.497 | 0.499 | 76 (38 hit) | +0.002 |
| 50-55% | 0.558 | 0.518 | 66 (33 hit) | -0.040 ** |
| 55-60% | 0.605 | 0.645 | 57 (38 hit) | +0.040 ** |
| 60-65% | 0.678 | 0.621 | 35 (20 hit) | -0.057 ** |
| 65-70% | 0.738 | 0.711 | 18 (12 hit) | -0.027 ** |
| 70-75% | 0.814 | 0.785 | 10 (7 hit) | -0.028 ** |
| 75-80% | 0.836 | 0.826 | 4 (3 hit) | -0.010 |
| 80-85% | 0.885 | 0.861 | 2 (1 hit) | -0.024 ** |
| 85-90% | 0.920 | 0.925 | 2 (2 hit) | +0.005 |
| 90-95% | 0.953 | 0.924 | 2 (1 hit) | -0.028 ** |
| 95-100% | 0.990 | 0.991 | 2 (2 hit) | +0.001 |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 141 |
| BAD (cheap side) | 82 |
| WEAK (50-70c) | 70 |
| GOOD | 59 |
| WEAK (small disagreement) | 24 |
| ALMOST (not confirmed yet) | 5 |
| WEAK (5-10 min) | 1 |

Leaned YES 255 times, NO 127 times. Over 63 days of history the
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
| 00:18 | 2026-09-29 00:30 | NO | 0.87 | -112 | 12 | **wrong** | -75.73 | $674.64 |
| 01:18 | 2026-09-29 01:30 | NO | 0.74 | -108 | 11 | RIGHT | +22.47 | $697.11 |
| 04:19 | 2026-09-29 04:30 | YES | 0.71 | +84 | 10 | RIGHT | +27.05 | $724.16 |
| 04:49 | 2026-09-29 05:00 | NO | 0.78 | -70 | 10 | **wrong** | -73.54 | $650.62 |
| 06:34 | 2026-09-29 06:45 | YES | 0.71 | +86 | 11 | RIGHT | +25.24 | $675.86 |
| 08:02 | 2026-09-29 08:15 | YES | 0.75 | +95 | 13 | RIGHT | +21.34 | $697.20 |
| 09:34 | 2026-09-29 09:45 | YES | 0.85 | +118 | 11 | RIGHT | +11.56 | $708.76 |
| 11:49 | 2026-09-29 12:00 | YES | 0.79 | +117 | 10 | RIGHT | +17.79 | $726.55 |
| 15:03 | 2026-09-29 15:15 | NO | 0.74 | -141 | 12 | RIGHT | +24.20 | $750.75 |
| 16:18 | 2026-09-29 16:30 | YES | 0.71 | +114 | 11 | RIGHT | +29.14 | $779.89 |
| 16:33 | 2026-09-29 16:45 | NO | 0.75 | -86 | 12 | RIGHT | +24.63 | $804.52 |
| 19:49 | 2026-09-29 20:00 | YES | 0.72 | +124 | 11 | RIGHT | +29.71 | $834.23 |
| 21:04 | 2026-09-29 21:15 | NO | 0.77 | -72 | 10 | RIGHT | +23.57 | $857.80 |
| 21:19 | 2026-09-29 21:30 | NO | 0.82 | -75 | 10 | RIGHT | +17.74 | $875.54 |
| 21:49 | 2026-09-29 22:00 | NO | 0.81 | -90 | 11 | RIGHT | +19.37 | $894.91 |
| 22:03 | 2026-09-29 22:15 | YES | 0.80 | +84 | 12 | RIGHT | +21.11 | $916.02 |
| 23:03 | 2026-09-29 23:15 | YES | 0.79 | +89 | 11 | RIGHT | +23.00 | $939.02 |
| 23:47 | 2026-09-30 00:00 | YES | 0.78 | +74 | 12 | RIGHT | +25.03 | $964.05 |
| 00:19 | 2026-09-30 00:30 | NO | 0.83 | -108 | 10 | **wrong** | -97.56 | $866.49 |
| 01:33 | 2026-09-30 01:45 | NO | 0.77 | -117 | 12 | RIGHT | +24.48 | $890.97 |
| 03:19 | 2026-09-30 03:30 | NO | 0.76 | -125 | 11 | RIGHT | +26.64 | $917.61 |
| 03:49 | 2026-09-30 04:00 | NO | 0.75 | -69 | 10 | RIGHT | +28.98 | $946.59 |
| 05:32 | 2026-09-30 05:45 | YES | 0.75 | +86 | 12 | RIGHT | +29.89 | $976.48 |
| 06:47 | 2026-09-30 07:00 | NO | 0.72 | -103 | 12 | RIGHT | +36.05 | $1,012.53 |
| 07:19 | 2026-09-30 07:30 | YES | 0.90 | +156 | 11 | RIGHT | +10.54 | $1,023.07 |
| 08:34 | 2026-09-30 08:45 | NO | 0.76 | -67 | 10 | RIGHT | +30.59 | $1,053.66 |
| 10:03 | 2026-09-30 10:15 | YES | 0.74 | +100 | 11 | RIGHT | +35.10 | $1,088.76 |
| 14:19 | 2026-09-30 14:30 | NO | 0.86 | -284 | 10 | RIGHT | +16.65 | $1,105.41 |
| 19:19 | 2026-09-30 19:30 | NO | 0.74 | -63 | 11 | RIGHT | +36.82 | $1,142.23 |
| 20:32 | 2026-09-30 20:45 | NO | 0.81 | -100 | 12 | RIGHT | +25.27 | $1,167.50 |

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
| 09-29 00:30 | NO | 0.87 | 9% | -112 | 12 |
| 09-29 05:00 | NO | 0.78 | 15% | -70 | 10 |
| 09-30 00:30 | NO | 0.83 | 10% | -108 | 10 |

| | n | avg price | avg edge | avg min left |
|---|---|---|---|---|
| won | 48 | 0.77 | 12% | 11 |
| lost | 11 | 0.80 | 10% | 11 |

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
