# What the bot has learned

Written 02 Sep 2026 4:12am California time by `check.py --report`.

## The short version

| | |
|---|---|
| **paper account** | **$797.29** (started $1,000, -20.3%) |
| best / worst it has been | $1,511.25 / $797.29 |
| fees paid | $222.52 |
| contracts looked at | 847 |
| retired (old rule, not counted) | 10 |
| of those, settled and learned from | 846 |
| actual calls (graded GOOD) | 137 |
| calls that have settled | 137 |
| alerts that reached the phone | 85 of 85 |
| calls made before delivery was recorded | 52 |
| calls right | 110 of 137 (80%) |
| break-even needed | 79% |
| paper P&L | +1.4% per dollar staked |

## What it is actually learning

Only one thing: **calibration**. When the formula says 78%, how often
does that really happen? It is a bent ruler being straightened. It is
not learning to see further ahead, and no amount of it will make the
bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's
own price is the better forecast. The bot's only claim is a narrow
band where its disagreement with Kalshi has been worth something.

The 63-day study is worth 30 observations per row below. So 846 live
results spread over 20 rows moves things very little, on purpose --
three lucky wins should not rewrite the table.

## The table it is straightening

| formula says | started at | now says | live results | moved |
|---|---|---|---|---|
| 0-5% | 0.019 | 0.017 | 3 (0 hit) | -0.002 |
| 5-10% | 0.044 | 0.040 | 3 (0 hit) | -0.004 |
| 15-20% | 0.167 | 0.212 | 3 (2 hit) | +0.045 ** |
| 20-25% | 0.178 | 0.157 | 4 (0 hit) | -0.021 ** |
| 25-30% | 0.238 | 0.268 | 19 (6 hit) | +0.030 ** |
| 30-35% | 0.286 | 0.288 | 31 (9 hit) | +0.002 |
| 35-40% | 0.354 | 0.345 | 53 (18 hit) | -0.009 |
| 40-45% | 0.384 | 0.359 | 105 (37 hit) | -0.025 ** |
| 45-50% | 0.497 | 0.458 | 162 (73 hit) | -0.039 ** |
| 50-55% | 0.558 | 0.529 | 185 (97 hit) | -0.029 ** |
| 55-60% | 0.605 | 0.537 | 121 (63 hit) | -0.068 ** |
| 60-65% | 0.678 | 0.612 | 67 (39 hit) | -0.066 ** |
| 65-70% | 0.738 | 0.677 | 47 (30 hit) | -0.061 ** |
| 70-75% | 0.814 | 0.796 | 17 (13 hit) | -0.018 |
| 75-80% | 0.836 | 0.822 | 9 (7 hit) | -0.013 |
| 80-85% | 0.885 | 0.869 | 4 (3 hit) | -0.016 |
| 85-90% | 0.920 | 0.878 | 6 (4 hit) | -0.042 ** |
| 90-95% | 0.953 | 0.955 | 2 (2 hit) | +0.003 |
| 95-100% | 0.990 | 0.992 | 4 (4 hit) | +0.001 |

## How it graded what it saw

| grade | times |
|---|---|
| NONE (no disagreement) | 384 |
| WEAK (50-70c) | 158 |
| GOOD | 129 |
| BAD (cheap side) | 101 |
| WEAK (small disagreement) | 54 |
| BAD (last 5 min) | 11 |
| WEAK (5-10 min) | 5 |
| ALMOST (not confirmed yet) | 5 |

Leaned YES 466 times, NO 381 times. Over 63 days of history the
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
| 13:33 | 2026-08-26 13:45 | YES | 0.71 | +166 | 11 | RIGHT | +41.87 | $1,120.67 |
| 16:48 | 2026-08-26 17:00 | YES | 0.81 | +179 | 12 | RIGHT | +24.79 | $1,145.46 |
| 17:18 | 2026-08-26 17:30 | YES | 0.87 | +164 | 11 | RIGHT | +16.07 | $1,161.53 |
| 19:49 | 2026-08-26 20:00 | YES | 0.75 | +62 | 10 | RIGHT | +36.68 | $1,198.21 |
| 22:04 | 2026-08-26 22:15 | YES | 0.72 | +85 | 10 | RIGHT | +44.25 | $1,242.46 |
| 22:19 | 2026-08-26 22:30 | YES | 0.76 | +155 | 11 | RIGHT | +37.15 | $1,279.61 |
| 04:33 | 2026-08-27 04:45 | NO | 0.72 | -63 | 12 | **wrong** | -130.47 | $1,149.14 |
| 04:49 | 2026-08-27 05:00 | NO | 0.84 | -84 | 11 | RIGHT | +20.60 | $1,169.74 |
| 05:48 | 2026-08-27 06:00 | YES | 0.75 | +110 | 11 | RIGHT | +36.94 | $1,206.68 |
| 15:48 | 2026-08-27 16:00 | NO | 0.80 | -191 | 12 | RIGHT | +28.48 | $1,235.16 |
| 16:34 | 2026-08-27 16:45 | NO | 0.75 | -97 | 10 | **wrong** | -125.69 | $1,109.47 |
| 17:03 | 2026-08-27 17:15 | NO | 0.81 | -157 | 12 | **wrong** | -112.43 | $997.04 |
| 17:19 | 2026-08-27 17:30 | YES | 0.81 | +180 | 10 | RIGHT | +22.06 | $1,019.10 |
| 18:03 | 2026-08-27 18:15 | NO | 0.70 | -86 | 11 | RIGHT | +41.53 | $1,060.63 |
| 00:17 | 2026-08-28 00:30 | YES | 0.83 | +169 | 12 | RIGHT | +20.45 | $1,081.08 |
| 01:03 | 2026-08-28 01:15 | YES | 0.76 | +189 | 12 | RIGHT | +32.32 | $1,113.40 |
| 02:18 | 2026-08-28 02:30 | NO | 0.80 | -222 | 12 | RIGHT | +26.27 | $1,139.68 |
| 04:18 | 2026-08-28 04:30 | YES | 0.72 | +103 | 12 | **wrong** | -116.21 | $1,023.47 |
| 04:34 | 2026-08-28 04:45 | NO | 0.72 | -84 | 10 | RIGHT | +37.79 | $1,061.26 |
| 08:47 | 2026-08-28 09:00 | NO | 0.82 | -145 | 12 | RIGHT | +21.96 | $1,083.22 |
| 10:33 | 2026-08-28 10:45 | YES | 0.72 | +67 | 12 | RIGHT | +39.99 | $1,123.21 |
| 10:49 | 2026-08-28 11:00 | YES | 0.73 | +48 | 11 | RIGHT | +39.41 | $1,162.62 |
| 11:04 | 2026-08-28 11:15 | YES | 0.89 | +144 | 10 | RIGHT | +13.47 | $1,176.09 |
| 12:17 | 2026-08-28 12:30 | YES | 0.84 | +150 | 13 | RIGHT | +21.08 | $1,197.17 |
| 13:49 | 2026-08-28 14:00 | YES | 0.86 | +221 | 11 | RIGHT | +18.31 | $1,215.48 |
| 16:03 | 2026-08-28 16:15 | NO | 0.87 | -324 | 11 | RIGHT | +17.05 | $1,232.53 |
| 16:48 | 2026-08-28 17:00 | YES | 0.71 | +118 | 12 | **wrong** | -125.76 | $1,106.77 |
| 21:33 | 2026-08-28 21:45 | YES | 0.82 | +110 | 11 | RIGHT | +22.90 | $1,129.67 |
| 22:02 | 2026-08-28 22:15 | YES | 0.75 | +67 | 13 | RIGHT | +35.68 | $1,165.35 |
| 23:17 | 2026-08-28 23:30 | NO | 0.72 | -62 | 12 | RIGHT | +43.03 | $1,208.38 |
| 00:34 | 2026-08-29 00:45 | NO | 0.85 | -106 | 10 | RIGHT | +20.05 | $1,228.43 |
| 02:18 | 2026-08-29 02:30 | NO | 0.82 | -65 | 12 | RIGHT | +25.41 | $1,253.84 |
| 03:03 | 2026-08-29 03:15 | YES | 0.72 | +48 | 11 | RIGHT | +46.30 | $1,300.14 |
| 03:49 | 2026-08-29 04:00 | NO | 0.77 | -71 | 11 | RIGHT | +36.73 | $1,336.87 |
| 06:33 | 2026-08-29 06:45 | YES | 0.74 | +59 | 11 | RIGHT | +44.53 | $1,381.40 |
| 07:04 | 2026-08-29 07:15 | YES | 0.82 | +49 | 10 | RIGHT | +28.57 | $1,409.97 |
| 08:02 | 2026-08-29 08:15 | NO | 0.85 | -75 | 12 | RIGHT | +23.39 | $1,433.36 |
| 12:18 | 2026-08-29 12:30 | YES | 0.83 | +49 | 12 | **wrong** | -145.05 | $1,288.31 |
| 13:49 | 2026-08-29 14:00 | YES | 0.77 | +50 | 10 | RIGHT | +36.40 | $1,324.71 |
| 14:48 | 2026-08-29 15:00 | YES | 0.84 | +191 | 12 | RIGHT | +23.74 | $1,348.45 |
| 15:48 | 2026-08-29 16:00 | YES | 0.86 | +89 | 11 | RIGHT | +20.62 | $1,369.07 |
| 16:18 | 2026-08-29 16:30 | YES | 0.72 | +67 | 12 | **wrong** | -139.60 | $1,229.47 |
| 17:18 | 2026-08-29 17:30 | YES | 0.75 | +67 | 12 | **wrong** | -125.11 | $1,104.36 |
| 18:01 | 2026-08-29 18:15 | YES | 0.73 | +90 | 13 | RIGHT | +38.76 | $1,143.12 |
| 20:33 | 2026-08-29 20:45 | NO | 0.73 | -58 | 11 | RIGHT | +40.11 | $1,183.23 |
| 21:03 | 2026-08-29 21:15 | NO | 0.76 | -65 | 12 | **wrong** | -120.31 | $1,062.92 |
| 00:18 | 2026-08-30 00:30 | YES | 0.85 | +146 | 12 | RIGHT | +17.64 | $1,080.56 |
| 01:18 | 2026-08-30 01:30 | NO | 0.72 | -69 | 11 | RIGHT | +39.90 | $1,120.46 |
| 01:47 | 2026-08-30 02:00 | YES | 0.72 | +50 | 12 | RIGHT | +41.38 | $1,161.84 |
| 02:04 | 2026-08-30 02:15 | YES | 0.74 | +51 | 10 | RIGHT | +38.70 | $1,200.54 |
| 03:34 | 2026-08-30 03:45 | YES | 0.80 | +83 | 10 | RIGHT | +28.32 | $1,228.86 |
| 04:04 | 2026-08-30 04:15 | YES | 0.84 | +73 | 10 | RIGHT | +22.03 | $1,250.89 |
| 10:48 | 2026-08-30 11:00 | YES | 0.76 | +40 | 12 | RIGHT | +37.39 | $1,288.28 |
| 13:49 | 2026-08-30 14:00 | YES | 0.88 | +142 | 10 | RIGHT | +16.48 | $1,304.76 |
| 15:04 | 2026-08-30 15:15 | NO | 0.78 | -70 | 10 | RIGHT | +34.79 | $1,339.55 |
| 16:04 | 2026-08-30 16:15 | YES | 0.87 | +155 | 10 | RIGHT | +18.80 | $1,358.35 |
| 17:18 | 2026-08-30 17:30 | NO | 0.83 | -170 | 12 | RIGHT | +26.20 | $1,384.55 |
| 18:32 | 2026-08-30 18:45 | YES | 0.81 | +172 | 13 | RIGHT | +30.63 | $1,415.18 |
| 20:03 | 2026-08-30 20:15 | YES | 0.80 | +59 | 12 | RIGHT | +33.39 | $1,448.57 |
| 20:32 | 2026-08-30 20:45 | NO | 0.81 | -100 | 12 | RIGHT | +32.05 | $1,480.62 |
| 21:03 | 2026-08-30 21:15 | NO | 0.82 | -216 | 12 | RIGHT | +30.63 | $1,511.25 |
| 22:04 | 2026-08-30 22:15 | YES | 0.76 | +117 | 11 | **wrong** | -153.66 | $1,357.59 |
| 23:48 | 2026-08-31 00:00 | NO | 0.88 | -322 | 11 | **wrong** | -136.91 | $1,220.68 |
| 04:04 | 2026-08-31 04:15 | NO | 0.90 | -124 | 11 | RIGHT | +12.70 | $1,233.38 |
| 06:19 | 2026-08-31 06:30 | YES | 0.71 | +104 | 10 | **wrong** | -125.85 | $1,107.53 |
| 07:19 | 2026-08-31 07:30 | YES | 0.73 | +116 | 11 | RIGHT | +38.86 | $1,146.39 |
| 10:04 | 2026-08-31 10:15 | NO | 0.78 | -83 | 11 | RIGHT | +30.56 | $1,176.95 |
| 13:03 | 2026-08-31 13:15 | YES | 0.77 | +145 | 12 | RIGHT | +33.26 | $1,210.21 |
| 17:18 | 2026-08-31 17:30 | NO | 0.87 | -225 | 12 | RIGHT | +16.97 | $1,227.18 |
| 18:02 | 2026-08-31 18:15 | NO | 0.72 | -63 | 12 | **wrong** | -125.13 | $1,102.05 |
| 19:18 | 2026-08-31 19:30 | NO | 0.85 | -145 | 12 | RIGHT | +18.29 | $1,120.34 |
| 20:19 | 2026-08-31 20:30 | YES | 0.88 | +131 | 10 | **wrong** | -112.98 | $1,007.36 |
| 23:04 | 2026-08-31 23:15 | NO | 0.85 | -189 | 11 | RIGHT | +16.72 | $1,024.08 |
| 00:33 | 2026-09-01 00:45 | NO | 0.84 | -102 | 11 | RIGHT | +18.36 | $1,042.44 |
| 01:02 | 2026-09-01 01:15 | YES | 0.75 | +90 | 12 | **wrong** | -106.07 | $936.37 |
| 03:19 | 2026-09-01 03:30 | YES | 0.70 | +68 | 11 | RIGHT | +38.16 | $974.53 |
| 03:32 | 2026-09-01 03:45 | YES | 0.79 | +158 | 12 | RIGHT | +24.46 | $998.99 |
| 05:04 | 2026-09-01 05:15 | YES | 0.87 | +174 | 10 | RIGHT | +14.02 | $1,013.01 |
| 06:19 | 2026-09-01 06:30 | NO | 0.84 | -114 | 11 | RIGHT | +18.16 | $1,031.17 |
| 08:48 | 2026-09-01 09:00 | YES | 0.71 | +68 | 12 | **wrong** | -105.22 | $925.95 |
| 10:03 | 2026-09-01 10:15 | YES | 0.70 | +47 | 11 | **wrong** | -94.55 | $831.40 |
| 12:03 | 2026-09-01 12:15 | NO | 0.76 | -81 | 11 | RIGHT | +24.85 | $856.25 |
| 12:33 | 2026-09-01 12:45 | NO | 0.74 | -86 | 12 | RIGHT | +28.52 | $884.77 |
| 13:04 | 2026-09-01 13:15 | NO | 0.86 | -164 | 10 | RIGHT | +13.53 | $898.30 |
| 14:03 | 2026-09-01 14:15 | YES | 0.75 | +184 | 12 | RIGHT | +28.36 | $926.66 |
| 15:02 | 2026-09-01 15:15 | NO | 0.86 | -277 | 12 | RIGHT | +14.18 | $940.84 |
| 21:19 | 2026-09-01 21:30 | NO | 0.85 | -200 | 11 | **wrong** | -95.07 | $845.77 |
| 22:47 | 2026-09-01 23:00 | YES | 0.73 | +84 | 13 | RIGHT | +29.68 | $875.45 |
| 23:34 | 2026-09-01 23:45 | YES | 0.71 | +73 | 10 | RIGHT | +33.98 | $909.43 |
| 03:02 | 2026-09-02 03:15 | YES | 0.74 | +82 | 12 | RIGHT | +30.29 | $939.72 |
| 04:04 | 2026-09-02 04:15 | NO | 0.76 | -60 | 10 | RIGHT | +28.09 | $967.81 |
| 04:34 | 2026-09-02 04:45 | YES | 0.77 | +60 | 11 | RIGHT | +27.35 | $995.16 |
| 05:03 | 2026-09-02 05:15 | NO | 0.80 | -73 | 11 | **wrong** | -100.92 | $894.24 |
| 05:19 | 2026-09-02 05:30 | YES | 0.71 | +62 | 10 | RIGHT | +34.70 | $928.94 |
| 06:34 | 2026-09-02 06:45 | NO | 0.80 | -107 | 10 | **wrong** | -94.20 | $834.74 |
| 08:32 | 2026-09-02 08:45 | NO | 0.80 | -176 | 12 | RIGHT | +19.70 | $854.44 |
| 09:19 | 2026-09-02 09:30 | NO | 0.82 | -87 | 10 | RIGHT | +17.68 | $872.12 |
| 09:33 | 2026-09-02 09:45 | NO | 0.84 | -203 | 12 | RIGHT | +15.63 | $887.75 |
| 10:34 | 2026-09-02 10:45 | NO | 0.73 | -88 | 10 | **wrong** | -90.46 | $797.29 |

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
| 08-27 04:45 | NO | 0.72 | 9% | -62 | 12 |
| 08-27 16:45 | NO | 0.75 | 8% | -97 | 10 |
| 08-27 17:15 | NO | 0.81 | 12% | -157 | 12 |
| 08-28 04:30 | YES | 0.72 | 12% | +102 | 12 |
| 08-28 17:00 | YES | 0.71 | 13% | +117 | 12 |
| 08-29 12:30 | YES | 0.83 | 7% | +49 | 12 |
| 08-29 16:30 | YES | 0.72 | 11% | +66 | 12 |
| 08-29 17:30 | YES | 0.75 | 12% | +67 | 12 |
| 08-29 21:15 | NO | 0.76 | 22% | -64 | 12 |
| 08-30 22:15 | YES | 0.76 | 8% | +117 | 11 |
| 08-31 00:00 | NO | 0.88 | 8% | -322 | 11 |
| 08-31 06:30 | YES | 0.71 | 11% | +104 | 10 |
| 08-31 18:15 | NO | 0.72 | 11% | -63 | 12 |
| 08-31 20:30 | YES | 0.88 | 11% | +131 | 10 |
| 09-01 01:15 | YES | 0.75 | 7% | +90 | 12 |
| 09-01 09:00 | YES | 0.71 | 10% | +68 | 12 |
| 09-01 10:15 | YES | 0.70 | 11% | +47 | 11 |
| 09-01 21:30 | NO | 0.85 | 8% | -199 | 11 |
| 09-02 05:15 | NO | 0.80 | 13% | -73 | 11 |
| 09-02 06:45 | NO | 0.80 | 16% | -107 | 10 |
| 09-02 10:45 | NO | 0.73 | 20% | -87 | 10 |

| | n | avg price | avg edge | avg min left |
|---|---|---|---|---|
| won | 110 | 0.80 | 12% | 11 |
| lost | 27 | 0.77 | 11% | 11 |

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
