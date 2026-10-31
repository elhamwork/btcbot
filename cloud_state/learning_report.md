# What the bot has learned

Written 31 Oct 2026 3:00pm California time by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$821.84** (started $1,000, -17.8%) |
| best / worst it has been | $1,061.12 / $821.84 |
| fees paid | $41.24 |
| contracts looked at | 306 |
| of those, settled and learned from | 304 |
| actual calls (graded GOOD) | 33 |
| calls that have settled | 33 |
| alerts that reached the phone | 33 of 33 |
| calls right | 26 of 33 (79%) |
| break-even needed | 81% |
| paper P&L | -3.0% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 304 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.019 | 0.019 | 1 (0 hit) | -0.001 |
| 5-10% | 0.044 | 0.074 | 1 (1 hit) | +0.031 ** |
| 10-15% | 0.071 | 0.069 | 1 (0 hit) | -0.002 |
| 15-20% | 0.167 | 0.194 | 1 (1 hit) | +0.027 ** |
| 20-25% | 0.178 | 0.167 | 2 (0 hit) | -0.011 |
| 25-30% | 0.238 | 0.254 | 6 (2 hit) | +0.016 |
| 30-35% | 0.286 | 0.338 | 19 (8 hit) | +0.053 ** |
| 35-40% | 0.354 | 0.437 | 24 (13 hit) | +0.083 ** |
| 40-45% | 0.384 | 0.375 | 54 (20 hit) | -0.009 |
| 45-50% | 0.497 | 0.460 | 59 (26 hit) | -0.037 ** |
| 50-55% | 0.558 | 0.526 | 55 (28 hit) | -0.031 ** |
| 55-60% | 0.605 | 0.536 | 43 (21 hit) | -0.069 ** |
| 60-65% | 0.678 | 0.719 | 15 (12 hit) | +0.041 ** |
| 65-70% | 0.738 | 0.721 | 9 (6 hit) | -0.016 |
| 70-75% | 0.814 | 0.800 | 8 (6 hit) | -0.013 |
| 75-80% | 0.836 | 0.802 | 5 (3 hit) | -0.034 ** |
| 85-90% | 0.920 | 0.891 | 1 (0 hit) | -0.030 ** |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 115 |
| WEAK (50-70c) | 62 |
| BAD (cheap side) | 57 |
| WEAK (small disagreement) | 34 |
| GOOD | 33 |
| ALMOST (not confirmed yet) | 3 |
| BAD (last 5 min) | 2 |

Leaned YES 151 times, NO 155 times. Over 63 days of history the
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
| 05:04 | 2026-10-29 05:15 | YES | 0.72 | +55 | 10 | RIGHT | +32.03 | $899.72 |
| 15:04 | 2026-10-29 15:15 | YES | 0.71 | +115 | 11 | RIGHT | +34.92 | $934.64 |
| 19:32 | 2026-10-29 19:45 | YES | 0.85 | +122 | 12 | RIGHT | +15.50 | $950.14 |
| 23:04 | 2026-10-29 23:15 | NO | 0.83 | -183 | 11 | RIGHT | +18.32 | $968.46 |
| 23:48 | 2026-10-30 00:00 | NO | 0.86 | -395 | 12 | RIGHT | +14.82 | $983.28 |
| 01:18 | 2026-10-30 01:30 | NO | 0.77 | -202 | 12 | RIGHT | +27.78 | $1,011.06 |
| 01:48 | 2026-10-30 02:00 | NO | 0.87 | -316 | 11 | RIGHT | +14.18 | $1,025.24 |
| 03:03 | 2026-10-30 03:15 | YES | 0.82 | +201 | 12 | RIGHT | +21.20 | $1,046.44 |
| 03:33 | 2026-10-30 03:45 | YES | 0.87 | +159 | 12 | RIGHT | +14.68 | $1,061.12 |
| 06:49 | 2026-10-30 07:00 | NO | 0.82 | -99 | 10 | **wrong** | -107.45 | $953.67 |
| 07:19 | 2026-10-30 07:30 | YES | 0.76 | +55 | 11 | RIGHT | +28.51 | $982.18 |
| 10:04 | 2026-10-30 10:15 | NO | 0.86 | -194 | 10 | RIGHT | +15.02 | $997.20 |
| 13:33 | 2026-10-30 13:45 | NO | 0.78 | -206 | 11 | RIGHT | +26.59 | $1,023.79 |
| 15:18 | 2026-10-30 15:30 | YES | 0.90 | +350 | 12 | **wrong** | -103.10 | $920.69 |
| 18:04 | 2026-10-30 18:15 | NO | 0.84 | -158 | 10 | RIGHT | +16.50 | $937.19 |
| 03:34 | 2026-10-31 03:45 | NO | 0.84 | -57 | 11 | RIGHT | +16.80 | $953.99 |
| 04:34 | 2026-10-31 04:45 | NO | 0.88 | -100 | 10 | RIGHT | +12.20 | $966.19 |
| 05:32 | 2026-10-31 05:45 | NO | 0.75 | -66 | 13 | **wrong** | -98.32 | $867.87 |
| 06:03 | 2026-10-31 06:15 | YES | 0.86 | +111 | 11 | RIGHT | +13.27 | $881.14 |
| 08:34 | 2026-10-31 08:45 | NO | 0.83 | -98 | 10 | RIGHT | +17.00 | $898.14 |
| 09:02 | 2026-10-31 09:15 | YES | 0.79 | +51 | 13 | RIGHT | +22.54 | $920.68 |
| 11:18 | 2026-10-31 11:30 | YES | 0.82 | +40 | 11 | RIGHT | +19.04 | $939.72 |
| 11:48 | 2026-10-31 12:00 | YES | 0.71 | +50 | 12 | RIGHT | +36.47 | $976.19 |
| 13:49 | 2026-10-31 14:00 | YES | 0.80 | +48 | 10 | **wrong** | -98.99 | $877.20 |
| 17:47 | 2026-10-31 18:00 | YES | 0.80 | +75 | 12 | RIGHT | +20.70 | $897.90 |
| 20:02 | 2026-10-31 20:15 | YES | 0.83 | +47 | 12 | RIGHT | +17.32 | $915.22 |
| 20:19 | 2026-10-31 20:30 | YES | 0.71 | +22 | 10 | **wrong** | -93.38 | $821.84 |

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
| 10-30 07:00 | NO | 0.82 | 11% | -99 | 10 |
| 10-30 15:30 | YES | 0.90 | 9% | +350 | 12 |
| 10-31 05:45 | NO | 0.75 | 18% | -66 | 13 |
| 10-31 14:00 | YES | 0.80 | 15% | +48 | 10 |
| 10-31 20:30 | YES | 0.71 | 9% | +22 | 10 |

| | n | avg price | avg edge | avg min left |
|---|---|---|---|---|
| won | 26 | 0.82 | 11% | 11 |
| lost | 7 | 0.79 | 12% | 11 |

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
