#!/usr/bin/env python3
"""
check.py -- ask once, or leave it watching.

    python3 check.py            asks which you want
    python3 check.py --once     one answer, then stop
    python3 check.py --loop     watch all day, alert your phone
    python3 check.py --alerts   set up phone alerts (30 seconds, once)

Looks at the BTC 15-minute contract open right now and answers YES, NO, or
CAN'T SAY. In --loop it keeps doing that every 30 seconds, pings your phone
when there is a call, and pings again when that call settles so you find out
whether it was right without opening Kalshi.

WHY "CAN'T SAY" IS THE DEFAULT
==============================
Most of the time Kalshi's price is right and there is nothing to say. A tool
that always produces an answer is not being clever, it is being dishonest --
it just relabels a coin flip as a recommendation.

So this refuses to answer unless the setup matches the conditions that were
actually profitable across 63 days and 6,000 real contracts:

    price outside 70-90c            the edge only held in that window
    the last 5 minutes              lost 8%
    a wide spread                   costs more than the edge is worth
    no disagreement with Kalshi     nothing to trade
    seen only once                  has to still be there 2 minutes later

Any of those and it says CAN'T SAY. Expect that most of the time. Silence is
the honest answer far more often than YES or NO.

HOW ACCURATE IS IT WHEN IT DOES ANSWER
======================================
On 63 days of history, setups passing all these filters won 89.3% of the time
against an 81.3% break-even, across 272 independent contracts (p=0.0002).
An 8-point edge, positive in all three test periods: 89.8 / 89.2 / 88.5.

Every figure in this file is measured by running the code in this file --
not the model it was fitted from. Those used to differ: the calibration
shipped as a 21-point approximation and quietly cost a point of win rate
and a fifth of the return. The full model now ships exactly, so the two
agree again. See the CAL_X block.

The last filter -- confirmation -- is what lifted it from 80.5% to 89.3%. It
costs volume, and so does the 7-point minimum: about 4 setups a day out of
96 contracts, which is why --loop exists -- leave it running rather than
checking by hand.

That is the strongest result in this project, and it still is not proof. It
has never been tested on live money, and the high win rate is mostly just the
price -- an 80c contract wins 80% of the time by definition. Every answer
prints the caveat.

No account, no API key, no orders, no money. Standard library only.
"""

import argparse
import json
import time
import math
import os
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SERIES = "KXBTC15M"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
COINBASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
COINBASE_TICKER = "https://api.exchange.coinbase.com/products/BTC-USD/ticker"

# How far we have to disagree with Kalshi before it is worth acting on.
#
# Raised from 5 points to 7 after measuring it. Inside the GOOD band, with
# the threshold applied to the confirming look as well as the entry:
#
#     threshold   pooled   return   per day
#      5 points    87.7%    +7.05%     6.6
#      6 points    88.1%    +8.21%     5.3
#      7 points    89.3%   +10.35%     4.3   <- chosen
#      8 points    89.4%   +11.32%     3.3
#      9 points    88.9%   +11.25%     2.6
#     10 points    86.6%    +9.35%     1.9
#
# Return per dollar goes +7.05% -> +10.35%, and p drops from 0.0012 to
# 0.0002. The 5-to-7 point trades that get dropped were the weak ones:
# 86.0% against an 84% break-even, +1.8% -- inside the noise.
#
# 7 over 8 because 8 is only better on train (91.4%) and worse on both
# periods it had not seen, which is what curve-fitting looks like. 7 is the
# steadiest reading: 89.8 / 89.2 / 88.5.
#
# Honest caveat: six thresholds were tried and the best-looking one picked.
# Some of the gain is that choosing. The three periods agreeing this closely
# is the reason to believe most of it is real, not proof that all of it is.
#
# Cost: about 4 calls a day instead of 6.6.
MIN_EDGE = 0.07
# Price window, chosen on the data rather than intuition.
#
# The obvious guess -- trade the coin-flips near 50c -- is wrong. Buying YES
# when both our formula and the market sit near 50c returned -3.1% on train
# and -10.1% on validation. Our calibration does lift at-the-money contracts
# (the formula says 50%, reality is ~57%), but the market has already priced
# that, so there is nothing left to take.
#
# The zone that holds up is where the market is ALREADY fairly confident and
# our model is more confident still. Return per dollar, edge >= 5%, 10+ min:
#
#     0.50-0.80   +1.09%   +2.12%   +3.42%
#     0.60-0.80   +1.12%   +3.03%   +0.58%
#     0.65-0.85   +2.65%   +3.24%   +2.03%
#     0.70-0.90   +3.46%   +2.00%   +4.27%   <- chosen
#     0.75-0.90   +3.55%   +4.70%   +4.31%
#
# Every window tested is positive in all three periods -- 21 of 21 cells --
# so this is a broad effect, not one lucky cell. 0.70-0.90 is picked over the
# slightly stronger 0.75-0.90 because it is wider and less curve-fitted.
#
# One trade per contract in this window: n=1250, 84.9% win rate against 80.4%
# break-even, p<0.0001, roughly 20 qualifying setups a day.
MIN_PRICE = 0.70
MAX_PRICE = 0.90
MIN_MINUTES_LEFT = 10.0
MAX_SPREAD = 0.05
MIN_VOL = 0.0001

# ---------------------------------------------------------------------------
# Confirmation: the setup has to still be there two minutes later
# ---------------------------------------------------------------------------
# A single reading can qualify on noise -- one jumpy minute of BTC, or a
# momentarily stale quote on one side of the book. Requiring the SAME side to
# have already qualified on an earlier look filters those out, and it is the
# only filter tested so far that improves every period at once.
#
# Entries at 10 minutes left, 70-90c, edge >= 5%, split by whether the same
# side also qualified at 12 minutes left:
#
#                       train              valid               test      pooled
#   confirmed      157  89.8% +10.3%   37  89.2% +9.6%    78  88.5% +10.7%  89.3%
#   NOT confirmed  298  80.2%  +1.8%   97  81.4% +3.1%   127  80.3%  +2.8%  80.5%
#
# 272 confirmed trades, 243 right, against a break-even of 81.3%: one-sided
# p = 0.0002. The win rate is 89.8 / 89.2 / 88.5 across three chronological
# periods -- about as stable as anything measured here.
#
# It is not free. Confirmation throws away roughly half the setups, so there
# are about 4 a day instead of 20.
#
# Checked at other entry times too (12/14, 8/10, 6/8): confirmation raised the
# win rate in 11 of the 12 period-cells. Entry at 10 confirmed at 12 is the
# strongest and the only one positive in all three periods, so that is the one
# wired in. The gap is measured at 2 minutes; 1.5 is allowed here because
# --wait polls every 30 seconds and will not land exactly on the minute.
CONFIRM_GAP_MIN = 1.5

# ---------------------------------------------------------------------------
# The paper account
# ---------------------------------------------------------------------------
# $1,000 of imaginary money, 10% of whatever the account is worth on each
# call. Nothing is ever sent to Kalshi; this is a scoreboard.
#
# 10% compounding is aggressive. Run over the 272 confirmed trades in the
# 63-day study, in the order they actually happened:
#
#     stake    ends at    worst dip   max drawdown
#      2%       $1,740       $980          6%
#      5%       $3,857       $949         15%
#     10%      $13,187       $899         29%      <- this setting
#     20%     $103,476       $797         53%
#     50%     $657,023       $494         94%
#    100%        WIPED         $0        101%   one loss ends it
#
# The 20% and 50% rows are arithmetic, not a suggestion. They assume every
# order fills at the quoted price, and six figures of stake in a market that
# trades ten thousand contracts a life does not fill at all. Read them as
# what compounding does on paper, and read the drawdown column as what it
# costs.
#
# Two things that number is not. It is not a forecast: the price window and
# the confirmation rule were both chosen by looking at all three periods, so
# some of that 12x is the choosing. And the size ceiling is real, though
# further out than this file used to claim. MEASURED from 3,130 live
# order-book snapshots across 78 contracts: the median size resting at the
# best price is $3,062 and the median spread is one cent.
#
#     order size   fills at the best price   fills within 5c of it
#     $250                     86%                    100%
#     $1,000                   73%                    100%
#     $2,500                   56%                     99%
#     $5,000                   31%                     97%
#
# At 10% of the account that is: $1,100 account fills 90% of the time,
# $10,000 account fills 73%, $25,000 account fills 56% and always within a
# couple of cents. So friction starts around $2,500 a bet -- an account near
# $25,000 -- not the $10,000 previously asserted here, which was a guess from
# total contract volume rather than a measurement of the book.
#
# Over a first week (about 40 calls) the same simulation ends between $814
# and $1,908, and finishes below $1,000 seventeen times in a hundred. That
# spread, not the 12x, is what a week actually looks like.
# TESTED AND REJECTED: gap-to-volatility as a tell for which calls lose.
#
# Two contracts, both $99 from the target, one lost and one won. The losing
# one sat in a market moving $118 per ten minutes and the winning one in a
# market moving $58 -- so the cushion was under one ordinary swing in the
# first case and nearly two in the second. A clean story, and it was told as
# the mechanism before it was checked. It is wrong.
#
# Over 329 trades the ratio does not distinguish them at all:
#
#                            losses      wins
#     gap / typical swing      1.20      1.17
#     gap to target             $67       $65
#     typical swing             $62       $58
#     price paid               0.79      0.80
#     edge                    12.0%     11.3%
#     minutes left             10.5      10.4
#
# Losses carried MORE edge than wins, again. Win rate by ratio, five equal
# buckets: 87.9, 87.9, 92.3, 86.4, 87.9. Flat.
#
# What the ratio governs is the PRICE, not the outcome:
#
#     gap / swing    trades   win rate   break-even   margin
#     0.50 - 0.80        66     87.9%       72.8%      +15.0
#     0.80 - 1.04        66     87.9%       77.6%      +10.3
#     1.04 - 1.24        65     92.3%       79.7%      +12.6
#     1.24 - 1.54        66     86.4%       83.8%       +2.6
#     1.54 - 2.26        66     87.9%       85.7%       +2.2
#
# The market reads the ratio correctly -- break-even climbs from 73% to 86%
# in step with it -- while our win rate stays near 88% throughout. So the
# margin is LARGEST where the cushion is thinnest, the opposite of the
# intuition. The trades that look frightening are the ones worth taking, and
# the comfortable ones are priced so there is nothing left in them.
#
# Fifth angle tried on separating losses in advance, after the loss
# classifier, early exits, drawdown throttling and the price bands. All five
# agree. An 88% model loses 12% of the time and there is no tell in the data
# available before the call.
#
# Recorded here mainly as a caution about method: the ratio story was built
# from two contracts and sounded mechanistic. Two contracts will support any
# story. Nothing goes in this file on fewer than a few hundred.
# WATCHED, NOT ACTED ON: the 80-85c band is the weak one, not the cheap end.
#
# Asked after four live losses whether the low end of the band -- around 70c
# -- is where it goes wrong. Live it certainly looks that way: 2 of 4 in
# 70-75c, against 10 of 10 in 80-85c.
#
# The 63 days say the reverse. Splitting the 329 full-window trades by the
# price paid:
#
#     band     trades   win rate   break-even   margin    per $
#     70-75c       81     86.4%       72.0%      +14.4   +20.01%
#     75-80c       66     95.5%       77.0%      +18.5   +24.04%
#     80-85c       96     81.2%       82.3%       -1.0    -1.27%
#     85-91c       86     93.0%       87.0%       +6.1    +6.97%
#
# The cheap end is the second best band in the book. What is priced at 72c
# has to win 72% of the time, and it wins 86%. 80-85c is the only band that
# does not clear its own break-even, and it is consistent about it across all
# three periods -- 84.2%, 76.5%, 83.3% against an 82.3% requirement. The
# chance of a band that good going 78-of-96 is 0.3%.
#
# Live's 2 of 4 is 4 calls. If the true rate there is 86.4%, two or fewer
# wins in four happens 9% of the time.
#
# SO WHY IS IT NOT CUT? Because dropping 80-85c is a slice chosen after
# seeing the answer, and the out-of-sample column says so:
#
#                            all 63 days              unseen fifth
#     keep everything     +10.68%   $18,331        +12.22%   $2,516
#     drop 80-85c         +15.82%   $26,220        +14.96%   $2,477
#
# In-sample the return per dollar jumps by half. On unseen data it gains 2.7
# points per dollar and the account ends slightly LOWER, because the trades
# it removes were paying for themselves in volume. Large in the window it was
# found in, marginal outside it: the exact signature that got Bitstamp and
# the 55-70c band rejected, and it gets the same answer here.
#
# Four bands were sliced, so roughly one in four chance of one looking bad
# by luck alone. The period consistency is what makes this worth recording
# rather than dismissing -- but recording is all it gets until the live count
# is large enough to split without inventing patterns.
#
# The thing to watch: 80-85c below break-even in live trading too. It is
# currently 10 of 10 there, which is luck in the other direction.
# MEASURED AND CORRECTED: the study looked at one minute, the bot uses six.
#
# The 89.3% quoted throughout this file came from a study that evaluated a
# single instant -- 10 minutes left, confirmed against 12. The shipped rule
# allows a call any time from 15 minutes down to 10, and live, three quarters
# of calls happen at other times. So the headline number described a narrower
# rule than the one running.
#
# Re-run across the real window, taking the first confirmed setup per
# contract exactly as the bot does (study_window.py):
#
#     rule                     trades   win%   break-even   63d at 10%
#     10-min snapshot (old)       272   89.3%     80.2%       $13,187
#     full 10-15 min window       329   88.4%     79.9%       $18,331
#       unseen fifth only          89   88.8%     79.1%        $2,516
#
# The rule holds. 88.4% against 89.3% is the same number, on 21% more trades,
# and the unseen fifth agrees at 88.8%. Nothing here needs changing.
#
# WHAT THE RE-RUN EXPOSED IS WORSE THAN WHAT IT WAS LOOKING FOR. The trade
# rate still does not reconcile: live takes 17.5 calls a day, this study 5.2.
# Calibration drift was checked first and is not it -- the largest bin has
# moved 0.034 and most have moved DOWN, which would mean fewer trades. The
# cause is in the data:
#
#     minutes present in decision_panel.parquet, per contract
#         14 min   100% of contracts
#         12 min   100%
#         10 min   100%
#         every other minute   absent
#
# The panel holds three moments per contract. The live bot polls every 15
# seconds and sees about 24. It therefore acts on setups that appear at
# minute 13, or 11, or 15 -- which no version of this study can evaluate,
# because those rows do not exist.
#
# So roughly two thirds of what the bot does is unmeasured. Not wrong:
# unmeasured. The live record is the only evidence covering those calls, and
# it is 28 calls long.
#
# The fix is available. real_data/kalshi_15m_candlesticks.csv holds every
# minute, about 15 rows per contract; the panel was downsampled when it was
# built. Rebuilding it at full resolution and re-running would put the study
# and the bot on the same footing for the first time. Until then, every
# figure in this file describes a sample of the bot's behaviour rather than
# all of it, and this comment is here so that is not forgotten.
# TESTED AND REJECTED: one all-in bet on a sure thing, then back to 10%.
#
# The idea: wait for a call it is certain about, stake the whole account once
# to clear the ground it keeps losing, then resume at 10%. Three separate
# reasons it fails, in order of how badly.
#
# FIRST, there is no call it is certain about. Sorting the 272 trades by the
# model's own confidence:
#
#     model's confidence   trades   actually won   avg price
#     under 85%               52        80.8%        0.73
#     85-90%                  34        97.1%        0.76
#     90-95%                  81        92.6%        0.80
#     95-99%                  83        86.7%        0.85
#     99% and over            22        95.5%        0.86
#
# The highest confidence it ever produced was 99.0%, and the 99%+ bucket lost
# one of twenty-two. The top decile by confidence lost 3 of 30. Note also
# that the ordering is not monotone -- 95-99% did worse than 85-90%. The
# calibration is good on average and cannot single out a certainty, because
# there isn't one to single out.
#
# SECOND, staking everything is past the point where growth stops. Kelly at
# 89.3% and an 80c price is 46% of the account; growth per bet goes NEGATIVE
# above 92%. A 100% bet is not aggressive, it is beyond the maximum, and it
# carries an 11% chance of ending at zero, which no later win rate repairs.
#
# THIRD -- the one that settles it -- the plan is beaten by simply staking a
# bit more every time. Over 40 calls, 40,000 runs:
#
#     first bet                     median   5th pct   ends at zero
#     10% always (what we do)       $1,484      $920       0.0%
#     100% once, then 10%           $1,740        $0      10.7%
#     15% always                    $1,772      $853       0.0%
#     20% always                    $2,055      $766       0.0%
#
# Staking 15% every time beats the all-in plan on the median AND cannot wipe
# out. The heroic bet buys nothing that patience does not buy more safely.
# Leverage lives in the ongoing fraction, never in one bet.
#
# ON THE $1,140 CEILING that prompted this. It is not a ceiling, it is the
# shape of 10% staking at 80c: a win adds 2.4% of the account and a loss
# costs 10.1%, so it takes 4.3 wins to undo one loss and losses arrive about
# every 9 calls. The account climbs in small steps and falls in big ones
# while still going up. That is a sawtooth, not a wall.
#
# WHAT WOULD ACTUALLY BE WORTH DOING, and why it is not done yet. Kelly is
# violently sensitive to the true win rate at these prices:
#
#     if the true win rate is   Kelly says stake
#     89.3% (the 63-day study)        46.5%
#     85.0%                           25.0%
#     83.0%                           15.0%
#     81.2% (live, 16 calls)           6.0%
#     80.0%                        nothing at all
#
# Break-even after fees is 80.7%. The whole strategy sits a couple of points
# above the line, and the optimal stake swings from half the account to zero
# across that gap. 10% is the honest hedge between the backtest and the live
# record while they disagree. It moves when the win rate is known, not before.
# TESTED AND REJECTED: a time-of-day volatility term.
#
# The literature is firm that BTC volatility runs on a daily cycle tracking
# US and European market hours, and our volatility input is trailing, which
# cannot see a cycle coming. It looked like a real gap.
#
# The cycle is there and it is big. Median rv_15m by UTC hour, train only,
# against its own median: 0.79 at 10h, 2.04 at 14h -- twice normal at the
# New York equity open, exactly where the research puts it.
#
# But the question is whether a trailing estimator MISSES it, and it does
# not. Measured on train only, the size of the move that actually followed
# against what rv_15m predicted, by hour, ranges 0.81 to 1.19 with no shape:
# 12h and 13h run hot, 14h does not, and 16h is the coldest hour of the day
# sitting between two warm ones. Adjacent hours disagree, which a real cycle
# does not. The periodicity is in the LEVEL of volatility, and a trailing
# fifteen-minute estimate tracks the level by construction -- by 13:35 the
# 14h regime is already inside it. The cycle is absorbed, not missed.
#
# Fitted anyway, calibration refit on train only:
#
#                            trades   win rate    per $    63-day end
#     no time term (current)    272     89.3%    +11.35%      $13,187
#     with hour multiplier      287     86.4%     +7.44%       $4,527
#     -- unseen fifth --
#     no time term (current)     78     88.5%    +11.81%       $2,143
#     with hour multiplier       77     84.4%     +6.63%       $1,350
#
# Worse on both windows, and the trade count rises over 63 days -- the same
# signature as signed semi-variance. A noisier volatility input manufactures
# confident disagreements with the market rather than better ones.
#
# Weekday effects are smaller still: Thursday 0.91, Friday 1.08, the rest
# flat within 0.03.
#
# Detail in results/reports/literature_review.md, addendum 2.
# TESTED AND REJECTED: trading differently after a drawdown.
#
# Asked for: once the account is $200 down, trade less, and take bets that
# pay more when they win. Both halves were measured on the 63-day sequence,
# switching modes at the same moments in time rather than gluing two
# separate backtests together.
#
# First half -- a defensive mode triggered $200 below the running peak:
#
#     defensive mode              63-day end   worst    trades   win rate
#     do nothing (current)           $13,187    $899       272     89.3%
#     stricter edge 10%               $3,373    $899       172     86.6%
#     stricter edge 12%               $2,842    $899       127     87.4%
#     price band 60-75c               $2,269    $899       117     85.5%
#     half stake                      $7,074    $899       272     89.3%
#     edge 10% + half stake           $3,001    $899       170     87.1%
#
# Every variant is worse, and the worst point is $899 in all of them --
# identical to doing nothing. That column is the whole finding. The account
# has to fall $200 before the brake engages, so the fall that hurt has
# already happened; afterwards the brake only sits on the recovery. It costs
# return and protects nothing. Repeated on the unseen fifth alone: same
# ordering, doing nothing wins.
#
# There is a reason this cannot work, beyond the measurement. The model's
# inputs are BTC's distance from the target, the minutes left and how fast
# it has been moving. The account balance is not among them and must not be:
# a drawdown says nothing whatever about the next contract. Trading smaller
# after losses is the gambler's fallacy with a spreadsheet.
#
# Second half -- "bigger wins", which means buying cheaper, as the main rule:
#
#     price band    trades   win rate   break-even   per $     63-day end
#     55-70c           154     72.1%       64.2%    +12.3%        $3,035
#     60-75c           197     74.6%       68.6%     +8.8%        $2,324
#     65-80c           216     83.8%       73.1%    +14.7%       $11,642
#     70-90c (ours)    272     89.3%       80.2%    +11.3%       $13,187
#     75-90c           134     91.0%       83.0%     +9.6%        $2,874
#     80-95c            60     93.3%       85.6%     +9.0%        $1,572
#
# Bigger wins cost exactly what they are worth. Every cent of extra payoff
# is paid for in win rate, in both directions -- 80-95c wins 93.3% of the
# time and returns less; 55-70c pays double and wins 72.1%. The market
# prices this correctly, which is what a market is.
#
# 55-70c does look strong on the unseen fifth alone (+25.1%). Over all 63
# days it is +12.3% with a worst point of $657 against our $899. Taking it
# on the strength of the flattering window is the mistake refused over
# Bitstamp, and it is refused here.
#
# What is true: the losses are large because the stake is 10% of a grown
# account, not because the calls are bad. The only honest lever on the size
# of a loss is the size of the bet, and that lowers the wins by the same
# factor. See the staking table above.
# TESTED AND REJECTED: learning from the losses to avoid future ones.
#
# The natural request -- study the trades that lost, find what they had in
# common, refuse those in future. Built it: a gradient-boosted classifier
# over price, edge, minutes left, z-score, three volatility windows, four
# return horizons, RSI, ATR, VWAP, two EMAs, relative volume, spread and
# distance, trained on the training period to predict which confirmed
# trades lose, then used to veto trades on data it had never seen.
#
#                            win rate   return
#     no veto      train       89.8%   +10.33%
#                  unseen      88.7%   +10.38%
#     with veto    train      100.0%   +23.01%   <- perfect
#                  unseen      88.0%    +9.48%   <- worse than nothing
#
# It removed every loss it had already been shown, and on new trades it was
# worse than not having it. It did not learn why trades lose; it memorised
# sixteen particular losses and then vetoed innocent trades that resembled
# them. Logistic regression, being too simple to memorise, dropped almost
# nothing and changed nothing -- which is its own kind of answer.
#
# There is a reason this cannot work. If a losing trade were identifiable in
# advance, the market would have priced it. A contract trades at 80c because
# nobody knows which fifth of them fail. The edge here is a property of the
# aggregate, not of any single trade, and no amount of studying individual
# losses will make it otherwise.
#
# This is also the standard way a backtest is fooled: a rule fitted to avoid
# past losses always looks flawless on the past.

# TESTED AND REJECTED: cutting a losing trade early.
#
# Kalshi lets you sell before settlement, so the obvious way to lose less is
# to bail out when a position turns. Measured over the same 272 confirmed
# trades, using the real per-minute book for each contract -- selling YES at
# the bid, NO at one minus the ask:
#
#                        train    unseen   overall
#     hold to the end   +10.33%   +10.38%  +10.35%   <- what we do
#     stop at  -5%       +3.71%    +3.70%   +3.70%
#     stop at -10%       +4.75%    +4.31%   +4.57%
#     stop at -20%       +6.73%    +1.87%   +4.67%
#     stop at -30%       +6.72%    +5.04%   +6.01%
#     take profit 92c    +8.18%    +7.73%   +7.99%
#     take profit 95c    +9.97%   +10.41%  +10.16%
#
# Every stop-loss roughly halves the return, and the tighter the worse. A
# 15-minute contract thrashes -- one real example went 0.80, 0.71, 0.78,
# 0.81, 0.80, 0.87, 0.91, 0.87, 0.97 and settled a winner. Any stop is hit
# by that noise and converts winners into realised losses.
#
# Taking profit early is also worse: the last few cents on the winners are
# what pay for the losers.
#
# So the answer to "can we lose less on the bad ones" is: not this way. The
# losses are the price of the wins, in the most literal sense.

PAPER_START = 1000.0
PAPER_STAKE = 0.10

# Kalshi's fee: 0.07 x contracts x price x (1 - price), charged on entry.
FEE_RATE = 0.07

# ---------------------------------------------------------------------------
# Coinbase -> Kalshi index correction
# ---------------------------------------------------------------------------
# Kalshi does not settle on Coinbase. It settles on CF Benchmarks' BRTI, which
# blends several venues, averaged over the final 60 seconds. Every settled
# contract carries the real BRTI value in `expiration_value`, so the gap is
# measurable rather than guessable.
#
# Across 5,998 settled contracts, Coinbase sits BELOW BRTI:
#
#     mean       -6.56        std dev        14.42
#     median     -5.97        |gap| median    8.29
#                             |gap| 90th     24.36
#
# and it is below in all ten weeks measured, ranging -4.56 to -10.54. A
# persistent one-sided bias like that is worth removing; the remaining +/-$14
# of scatter is not removable without the real BRTI feed.
#
# This matters more than its size suggests. These contracts are decided by
# tens of dollars, so a systematic $6 error is a systematic error in every
# probability the tool produces.
COINBASE_TO_BRTI = 5.97

# TESTED AND REJECTED: anchoring to the strike.
#
# The strike of each contract is EXACTLY Kalshi's index at open -- verified,
# 5,982 consecutive pairs, 100% exact match to the penny. So Kalshi hands us
# its own index for free every 15 minutes, and the obvious move is to anchor
# to it and let Coinbase supply only the change since:
#
#     estimate = strike + (coinbase_now - coinbase_at_open)
#
# It is worse. Measured against 5,992 real settlements:
#
#     raw Coinbase                      RMS 15.85    outcome match 94.01%
#     Coinbase + fixed offset (used)    RMS 14.44                  94.74%
#     anchored to the strike            RMS 19.53                  93.01%
#
# 35% worse. The reason: the Coinbase-to-BRTI gap does not persist. Its
# correlation between contract open and 15 minutes later is 0.083 -- it
# resets constantly. Anchoring therefore freezes whichever random gap
# happened to exist at open and carries it for the whole contract, replacing
# one noisy reading with two.
#
# Blending the two helps by 0.05 of RMS at w=0.10, which is nothing, and
# costs real complexity. Not taken.

# Calibration: what the formula says, versus what really happened.
#
# FITTED ON THE TRAINING PERIOD ONLY (17 Jun - 25 Jul), and shipped EXACTLY.
#
# Two corrections live in this block, both found late.
#
# The first: the table shipped before this was fitted on all 63 days,
# validation and test included -- a leak, since the live tool was then tuned
# on the data used to judge it. Refitting honestly moved every row down, by
# as much as 8.7 points. Over-confidence inflates the edge, and the edge is
# what decides whether to trade, so the tool was calling setups that do not
# meet its own rule.
#
# The second: even after refitting, this was stored as 21 evenly spaced
# points, and that approximation was quietly expensive --
#
#     grid          trades   win rate   return    63 days at 10 percent
#     21 points      267      88.0        +8.20        $6,981
#     101 points     273      88.6        +9.29        $9,867
#     201 points     275      89.5       +10.35       $13,590
#     the model      272      89.3       +10.35       $13,187
#
# -- a fifth of the return, thrown away by rounding a curve. Isotonic
# regression is a step function with finitely many breakpoints, so there is
# no need to approximate it at all: the 164 knots below reproduce the fitted
# model to the last decimal (verified, max difference 0.00e+00). This is not
# extra fitting. It is the same model, copied properly.
CAL_X = [
    0, 5.3462e-06, 5.36853e-06, 0.000364103, 0.000365189, 0.0053352,
    0.0053473, 0.0096232, 0.00963275, 0.0308979, 0.0309066, 0.0332223,
    0.0332424, 0.0354375, 0.035441, 0.0800849, 0.0801172, 0.0828338,
    0.0829501, 0.0899102, 0.0900576, 0.13242, 0.132454, 0.133462, 0.133464,
    0.142046, 0.142057, 0.166829, 0.166841, 0.173925, 0.173939, 0.193367,
    0.193368, 0.228731, 0.228733, 0.245923, 0.246006, 0.264451, 0.264463,
    0.28751, 0.287537, 0.288391, 0.288401, 0.337502, 0.337521, 0.339286,
    0.339306, 0.340097, 0.340102, 0.346136, 0.346148, 0.349085, 0.349094,
    0.35972, 0.359727, 0.405151, 0.4052, 0.409042, 0.409058, 0.426546,
    0.426564, 0.432823, 0.432868, 0.432945, 0.432958, 0.438906, 0.438939,
    0.447034, 0.447057, 0.461909, 0.461916, 0.463759, 0.463782, 0.466349,
    0.466365, 0.497253, 0.497261, 0.50289, 0.50293, 0.515756, 0.515767,
    0.516198, 0.516245, 0.524241, 0.524256, 0.525631, 0.525639, 0.528045,
    0.528077, 0.564621, 0.564638, 0.590261, 0.590271, 0.613082, 0.613121,
    0.6136, 0.613641, 0.617714, 0.61786, 0.653651, 0.65378, 0.654003,
    0.654005, 0.677496, 0.677558, 0.68756, 0.687577, 0.69559, 0.69566,
    0.698011, 0.698015, 0.700335, 0.700339, 0.700486, 0.700571, 0.709481,
    0.709494, 0.745016, 0.745082, 0.752084, 0.752094, 0.784722, 0.78485,
    0.787257, 0.787296, 0.797108, 0.797171, 0.833027, 0.833034, 0.834793,
    0.834831, 0.877918, 0.878126, 0.883325, 0.883341, 0.88955, 0.889615,
    0.899099, 0.899123, 0.936553, 0.936588, 0.93796, 0.937993, 0.940678,
    0.940765, 0.941582, 0.94163, 0.94364, 0.943657, 0.948224, 0.948257,
    0.950537, 0.950558, 0.95247, 0.952499, 0.990821, 0.990828, 0.993447,
    0.993455, 0.998684, 0.998685, 0.999834, 0.999837, 1]
CAL_Y = [
    0, 0, 0.00298063, 0.00298063, 0.0077821, 0.0077821, 0.0124378, 0.0124378,
    0.0191304, 0.0191304, 0.0294118, 0.0294118, 0.0353982, 0.0353982,
    0.0435069, 0.0435069, 0.0632911, 0.0632911, 0.0673077, 0.0673077,
    0.0709957, 0.0709957, 0.09375, 0.09375, 0.0988142, 0.0988142, 0.101749,
    0.101749, 0.122995, 0.122995, 0.166667, 0.166667, 0.178378, 0.178378,
    0.215321, 0.215321, 0.226236, 0.226236, 0.237856, 0.237856, 0.277778,
    0.277778, 0.285521, 0.285521, 0.288136, 0.288136, 0.307692, 0.307692,
    0.324176, 0.324176, 0.325581, 0.325581, 0.325779, 0.325779, 0.354086,
    0.354086, 0.365517, 0.365517, 0.384375, 0.384375, 0.395833, 0.395833, 0.4,
    0.4, 0.408451, 0.408451, 0.420195, 0.420195, 0.450161, 0.450161, 0.460317,
    0.460317, 0.487805, 0.487805, 0.496764, 0.496764, 0.51, 0.51, 0.523517,
    0.523517, 0.529412, 0.529412, 0.547059, 0.547059, 0.557692, 0.557692,
    0.57732, 0.57732, 0.593864, 0.593864, 0.604978, 0.604978, 0.639726,
    0.639726, 0.666667, 0.666667, 0.673203, 0.673203, 0.677998, 0.677998,
    0.714286, 0.714286, 0.73785, 0.73785, 0.756272, 0.756272, 0.772093,
    0.772093, 0.777778, 0.777778, 0.779661, 0.779661, 0.8, 0.8, 0.80786,
    0.80786, 0.813877, 0.813877, 0.824176, 0.824176, 0.835801, 0.835801,
    0.866667, 0.866667, 0.86692, 0.86692, 0.885017, 0.885017, 0.92, 0.92,
    0.920379, 0.920379, 0.928571, 0.928571, 0.930556, 0.930556, 0.943548,
    0.943548, 0.952525, 0.952525, 0.955556, 0.955556, 0.961538, 0.961538,
    0.962963, 0.962963, 0.971429, 0.971429, 0.97351, 0.97351, 0.977528,
    0.977528, 0.987179, 0.987179, 0.990419, 0.990419, 0.990476, 0.990476,
    0.995929, 0.995929, 0.996139, 0.996139, 1, 1]

W = 64


class NoSetup(Exception):
    """Raised instead of printing, when running in --wait mode."""


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------
# Every answer is written down. The next time you run this, it looks up how
# the earlier contracts actually settled and adjusts. Kalshi publishes the
# result, so it checks its own homework -- you do not have to tell it.
#
# What it adjusts is CALIBRATION: the mapping from "the formula says 78%" to
# "78% really means 84%". That is a real thing to learn and it is what the
# 63-day study showed was off.
#
# It does NOT learn to see the future. If Kalshi's price is the better
# forecast, no amount of self-correction changes that. Learning straightens a
# bent ruler; it does not make the ruler longer.
#
# The 63-day table below counts as PRIOR_STRENGTH observations per bin, so a
# handful of live results nudges it rather than throwing it out. Three lucky
# wins should not convince it that a bin is a certainty.
# Where the memory lives. Overridable so a cloud runner can point it at a
# folder that gets committed back to the repo -- otherwise every run would
# start from nothing and learn the same first lesson forever.
STATE_DIR = os.environ.get("CHECK_STATE_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "forward_test")
MEMORY = os.path.join(STATE_DIR, "check_memory.json")
CONFIG = os.path.join(STATE_DIR, "check_config.json")
N_BINS = 20
PRIOR_STRENGTH = 30.0


# ---------------------------------------------------------------------------
# Phone alerts
# ---------------------------------------------------------------------------
# ntfy.sh: install the app, subscribe to a topic name, and anything posted to
# that name arrives on your phone. No account, no key, no signup.
#
# SECURITY: topics on ntfy.sh are PUBLIC. Anyone who guesses the name sees
# your alerts. That is why the setup generates a long random one rather than
# letting you pick "btc". Nothing secret is ever sent -- the alerts contain a
# contract ticker and a price, both public information -- but a guessable
# topic still lets a stranger read when you trade.
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")


def where_am_i():
    """
    A short name for this copy, stamped on every alert.

    The laptop and the cloud runner post to the same topic, so without this
    an alert says a call hit but not whose paper account just moved.
    """
    name = os.environ.get("CHECK_LABEL")
    if name:
        return name[:20]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "cloud"
    try:
        import socket
        host = socket.gethostname().split(".")[0]
        return (host.replace("-", " ").split()[0] or "here")[:20]
    except Exception:                                         # noqa: BLE001
        return "here"


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except Exception:                                         # noqa: BLE001
        return {}


def save_config(c):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f, indent=1)
    os.replace(tmp, CONFIG)


def ntfy_topic():
    return os.environ.get("NTFY_TOPIC") or load_config().get("ntfy_topic") or ""


def send_ntfy(title, body, tags="chart_with_upwards_trend", priority="default"):
    """POST to ntfy.sh. Returns (ok, detail). Never raises."""
    topic = ntfy_topic()
    if not topic:
        return False, "no topic set"
    title = "[%s] %s" % (where_am_i(), title)
    req = urllib.request.Request(
        "%s/%s" % (NTFY_SERVER.rstrip("/"), topic),
        data=body.encode("utf-8"), method="POST",
        headers={"Title": title.encode("ascii", "replace").decode("ascii"),
                 "Tags": tags, "Priority": priority, "Markdown": "no"})
    try:
        with urllib.request.urlopen(
                req, timeout=10, context=ssl.create_default_context()) as r:
            return r.status < 300, "HTTP %s" % r.status
    except Exception as e:                                    # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)


def ntfy_setup():
    """Make a random topic, save it, and print the two steps to hook it up."""
    import secrets
    cfg = load_config()
    # An NTFY_TOPIC in the environment overrides the saved file everywhere
    # else, so it has to win here too. Otherwise this prints one topic, you
    # subscribe the phone to it, and every run posts to a different one.
    env = os.environ.get("NTFY_TOPIC")
    if env:
        print()
        line("=")
        print("  PHONE ALERTS")
        line("=")
        print("  The environment variable NTFY_TOPIC is set, and it beats the")
        print("  saved file. Everything posts to:")
        print()
        print("      %s" % env)
        print()
        print("  Subscribe your phone to THAT one. The saved file says %s,"
              % (cfg.get("ntfy_topic") or "nothing"))
        print("  which is being ignored. To use the saved one instead, run:")
        print("      unset NTFY_TOPIC")
        print()
        ok, detail = send_ntfy("btcbot connected",
                               "If you can read this, alerts are working.",
                               tags="white_check_mark")
        print("  Test alert: %s (%s)" % ("sent -- check your phone" if ok
                                         else "FAILED", detail))
        print()
        return
    topic = cfg.get("ntfy_topic")
    fresh = not topic
    if fresh:
        topic = "btcbot-" + secrets.token_urlsafe(12).replace("-", "").replace("_", "")
        cfg["ntfy_topic"] = topic
        save_config(cfg)
    print()
    line("=")
    print("  PHONE ALERTS")
    line("=")
    print("  Your topic%s:" % ("" if fresh else " (already set)"))
    print("  Saved in %s" % CONFIG)
    print()
    print("      %s" % topic)
    print()
    print("  1. Install the free app 'ntfy' from the App Store or Play Store.")
    print("  2. Open it, tap +, and paste that topic in.")
    print()
    print("  That is it. Saved to forward_test/check_config.json, so you only")
    print("  do this once.")
    print()
    ok, detail = send_ntfy("btcbot connected",
                           "If you can read this, alerts are working.",
                           tags="white_check_mark")
    print("  Test alert: %s (%s)" % ("sent -- check your phone" if ok
                                     else "FAILED", detail))
    print()
    print("  Note: ntfy topics are public. Anyone who knows that name can")
    print("  read your alerts, so do not post it anywhere.")
    print()


def bin_of(p):
    return min(int(p * N_BINS), N_BINS - 1)


def calibrated(raw):
    """Read the fitted curve at `raw`. Linear between knots, clipped outside."""
    if raw <= CAL_X[0]:
        return CAL_Y[0]
    if raw >= CAL_X[-1]:
        return CAL_Y[-1]
    lo, hi = 0, len(CAL_X) - 1
    while hi - lo > 1:                       # 164 knots; binary search
        mid = (lo + hi) // 2
        if CAL_X[mid] <= raw:
            lo = mid
        else:
            hi = mid
    x0, x1 = CAL_X[lo], CAL_X[hi]
    y0, y1 = CAL_Y[lo], CAL_Y[hi]
    if x1 <= x0:                             # isotonic knots can repeat an x
        return y1
    return y0 + (y1 - y0) * (raw - x0) / (x1 - x0)


def prior_for(b):
    """The calibration, read at the centre of bin b."""
    return calibrated((b + 0.5) / N_BINS)


def load_memory():
    blank = {"predictions": [], "bins_n": [0.0] * N_BINS,
             "bins_wins": [0.0] * N_BINS, "polls": {},
             "bank": {"cash": PAPER_START, "start": PAPER_START,
                      "peak": PAPER_START, "low": PAPER_START,
                      "settled": 0, "fees": 0.0}}
    try:
        with open(MEMORY) as f:
            m = json.load(f)
        for k, v in blank.items():
            m.setdefault(k, v)
        return m
    except Exception:                                         # noqa: BLE001
        return blank


def save_memory(m):
    os.makedirs(os.path.dirname(MEMORY), exist_ok=True)
    tmp = MEMORY + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f, indent=1)
    os.replace(tmp, MEMORY)      # atomic; a crash cannot corrupt the memory


def learned(mem, raw):
    """Prior blended with whatever this tool has since observed."""
    b = bin_of(raw)
    n, w = mem["bins_n"][b], mem["bins_wins"][b]
    p = (prior_for(b) * PRIOR_STRENGTH + w) / (PRIOR_STRENGTH + n)
    return min(max(p, 0.001), 0.999)


def bank_of(mem):
    b = mem.setdefault("bank", {})
    for k, v in (("cash", PAPER_START), ("start", PAPER_START),
                 ("peak", PAPER_START), ("low", PAPER_START),
                 ("settled", 0), ("fees", 0.0)):
        b.setdefault(k, v)
    return b


def plan_stake(mem, price):
    """What this call would risk, and what it would win. Nothing is sent."""
    b = bank_of(mem)
    stake = round(b["cash"] * PAPER_STAKE, 2)
    contracts = stake / max(price, 0.01)
    fee = round(FEE_RATE * contracts * price * (1 - price), 2)
    return {"stake": stake, "contracts": round(contracts, 1), "fee": fee,
            "to_win": round(contracts * (1 - price) - fee, 2),
            "bank_before": round(b["cash"], 2)}


def apply_settle(mem, rec, won):
    """Move the paper money once a call has settled. Idempotent."""
    if rec.get("paid") is not None or not rec.get("bet"):
        return None
    b = bank_of(mem)
    bet = rec["bet"]
    paid = (bet["contracts"] - bet["stake"] - bet["fee"]) if won \
        else (-bet["stake"] - bet["fee"])
    b["cash"] = round(b["cash"] + paid, 2)
    b["peak"] = round(max(b["peak"], b["cash"]), 2)
    b["low"] = round(min(b["low"], b["cash"]), 2)
    b["settled"] += 1
    b["fees"] = round(b["fees"] + bet["fee"], 2)
    rec["paid"] = round(paid, 2)
    rec["bank_after"] = b["cash"]
    return paid


def note_poll(mem, ticker, mins, side, qualified):
    """
    Write down what this look at the contract saw, and say whether an earlier
    look already saw the same thing.

    Only qualifying looks count as confirmation -- a contract that was a
    coin-flip three minutes ago and is a signal now has not been confirmed,
    it has just moved.
    """
    polls = mem.setdefault("polls", {})
    seen = polls.setdefault(ticker, [])
    confirmed = False
    for i, q in enumerate(seen):
        if not (q["qual"] and q["side"] == side
                and q["mins"] >= mins + CONFIRM_GAP_MIN):
            continue
        # ... and it has not changed its mind in between. The 12-then-10
        # backtest could not see intermediate looks, so this extra guard is
        # NOT separately measured. It is kept because it can only ever refuse
        # trades, never add them, and a lean that flipped and flipped back is
        # the definition of the noise confirmation exists to filter.
        if all(later["side"] == side for later in seen[i + 1:]):
            confirmed = True
            break
    before = list(seen)
    seen.append({"mins": round(mins, 2), "side": side, "qual": bool(qualified)})
    polls[ticker] = seen[-40:]
    # Contracts live 15 minutes; anything not touched in this run and already
    # holding a full history is finished. Keep the file from growing forever.
    if len(polls) > 200:
        for k in list(polls)[:-100]:
            if k != ticker:
                del polls[k]
    return confirmed, before


def settle_pending(mem, quiet=False):
    """Look up how earlier calls turned out, and learn from them."""
    now = datetime.now(timezone.utc)
    checked = right = wrong = 0
    for rec in mem["predictions"]:
        if rec.get("outcome") is not None:
            continue
        try:
            ct = datetime.fromisoformat(str(rec["close_time"]).replace("Z", "+00:00"))
        except Exception:                                     # noqa: BLE001
            continue
        if now < ct + timedelta(minutes=2):
            continue
        d, _ = get(KALSHI + "/markets/" + rec["ticker"])
        res = ((d or {}).get("market") or {}).get("result")
        if res not in ("yes", "no"):
            continue
        y = 1 if res == "yes" else 0
        rec["outcome"] = y
        b = bin_of(rec["raw"])
        mem["bins_n"][b] += 1.0
        mem["bins_wins"][b] += 1.0 if y == 1 else 0.0
        checked += 1
        if rec.get("answered"):
            ok = (rec["side"] == "YES" and y == 1) or (rec["side"] == "NO" and y == 0)
            rec["correct"] = bool(ok)
            right += ok
            wrong += not ok
            # This is the alert that matters: not "here is an idea" but "the
            # idea you were given settled, and here is what happened".
            paid = apply_settle(mem, rec, ok)
            b = bank_of(mem)
            money = ("\n%s$%s. Paper account now $%s."
                     % ("Won " if paid and paid > 0 else "Lost ",
                        format(abs(round(paid or 0, 2)), ",.2f"),
                        format(round(b["cash"], 2), ",.2f"))) if paid is not None else ""
            send_ntfy(
                ("WON %+.0f  -  $%s" % (paid, format(round(b["cash"]), ",d")))
                if paid is not None and ok else
                ("LOST %.0f  -  $%s" % (abs(paid or 0),
                                        format(round(b["cash"]), ",d")))
                if paid is not None else
                ("%s settled %s" % (rec["side"], res.upper())),
                "%s %.0fc  -  settled %s"
                % (rec["side"], 100 * rec["price"], res.upper()),
                tags="tada" if ok else "x",
                priority="high" if ok else "default")
    if checked and not quiet:
        bits = ["learned from %d settled contract%s" % (checked, "" if checked == 1 else "s")]
        if right or wrong:
            bits.append("%d of my calls right, %d wrong" % (right, wrong))
        print("  (%s)" % "; ".join(bits))
    return checked


def side_breakdown(mem):
    """
    Every look it has taken, split YES vs NO and by grade.

    This exists because "it always says NO" is easy to believe and hard to
    check by memory. Over 63 days of history the split is 49.5% YES, and
    among setups that actually qualify it is 62% YES -- so if your own runs
    look one-sided, this is where to see whether they really are.
    """
    recs = mem.get("predictions") or []
    if not recs:
        return
    y = sum(1 for r in recs if r.get("side") == "YES")
    n = len(recs)
    print("  which way it leaned")
    print("    YES  %3d   (%.0f%%)" % (y, 100 * y / n))
    print("    NO   %3d   (%.0f%%)" % (n - y, 100 * (n - y) / n))
    print("    63-day expectation: about half and half")
    grades = {}
    for r in recs:
        grades[r.get("grade") or "(not recorded)"] = \
            grades.get(r.get("grade") or "(not recorded)", 0) + 1
    print()
    print("  what it graded them")
    for k, v in sorted(grades.items(), key=lambda kv: -kv[1]):
        print("    %-28s %3d" % (k, v))
    if "(not recorded)" in grades:
        print("    ((not recorded) = looked at before this tool started")
        print("     writing the grade down. They fade as you keep running.)")
    print()
    print("  Note: \"NONE (no disagreement)\" is not the answer NO. It means")
    print("  there is no trade. The YES/NO above is the lean; the grade is")
    print("  whether the lean is worth money.")
    print()


def digest(mem):
    """
    One message a day: where the paper account stands and how far off proof
    it still is.

    Worth its own mode because the interesting number moves slowly. The
    per-call alerts say what just happened; this says whether any of it adds
    up yet, which is the only question that matters and the easiest one to
    lose track of between individual wins.
    """
    settle_pending(mem, quiet=True)
    save_memory(mem)
    b = bank_of(mem)
    recs = mem.get("predictions") or []
    done = [r for r in recs if r.get("answered") and not r.get("retired")
            and r.get("correct") is not None]
    w = sum(1 for r in done if r["correct"])
    grow = 100 * (b["cash"] / b["start"] - 1) if b["start"] else 0
    lines = []
    if done:
        be = 100 * sum(r["price"] for r in done) / len(done)
        lines.append("%d of %d right (%.0f%%), break-even %.0f%%."
                     % (w, len(done), 100 * w / len(done), be))
        lines.append("peak $%s  low $%s"
                     % (format(round(b["peak"]), ",d"),
                        format(round(b["low"]), ",d")))
        left = max(0, 100 - len(done))
        lines.append("%d of ~100 calls%s"
                     % (len(done),
                        " - about %d days to go" % round(left / 4.0)
                        if left else " - enough to judge now"))
    else:
        lines.append("no calls yet, %d contracts watched" % len(recs))
    live_now = sum(1 for r in recs if r.get("answered") and not r.get("retired")
                   and r.get("correct") is None)
    if live_now:
        lines.append("%d call%s open right now."
                     % (live_now, "" if live_now == 1 else "s"))
    lines.append("paper only")
    body = "\n".join(lines)
    print()
    for ln in lines:
        print("  " + ln)
    print()
    ok, detail = send_ntfy("$%s  %+.1f%%"
                           % (format(round(b["cash"]), ",d"), grow),
                           body, tags="bar_chart")
    print("  phone: %s (%s)" % ("sent" if ok else "not sent", detail))
    print()


def local_stamp(when=None):
    """
    Now, in California time. Storage stays UTC; reading does not.

    Falls back to UTC and says so rather than shifting by nothing, because a
    timestamp that is silently wrong by seven hours is worse than one that
    admits which clock it is on.
    """
    d = when or datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        d = d.astimezone(ZoneInfo("America/Los_Angeles"))
        name = "California time"
    except Exception:                                         # noqa: BLE001
        name = "UTC"
    return "%s %d:%02d%s %s" % (d.strftime("%d %b %Y"), (d.hour % 12) or 12,
                                d.minute, "am" if d.hour < 12 else "pm", name)


def write_report(mem):
    """
    Write down, in a file, everything it has learned so far.

    --record prints a summary. This is the long version, kept on disk so you
    can watch it change week to week instead of trusting a number that
    scrolls past.
    """
    path = os.path.join(os.path.dirname(MEMORY), "learning_report.md")
    recs = mem.get("predictions") or []
    settled = [r for r in recs if r.get("outcome") is not None]
    # A retired call was made under a rule that no longer exists. It still
    # teaches calibration -- the raw formula did not change and the outcome
    # is real -- but counting it as a call would average two different bots
    # into one track record.
    calls = [r for r in recs if r.get("answered") and not r.get("retired")]
    done = [r for r in calls if r.get("correct") is not None]
    retired = [r for r in recs if r.get("retired")]
    L = []
    A = L.append
    A("# What the bot has learned")
    A("")
    A("Written %s by `check.py --report`." % local_stamp())
    A("")
    A("## The short version")
    A("")
    A("| | |")
    A("|---|---|")
    b = bank_of(mem)
    A("| **paper account** | **$%s** (started $%s, %+.1f%%) |"
      % (format(round(b["cash"], 2), ",.2f"),
         format(round(b["start"]), ",d"),
         100 * (b["cash"] / b["start"] - 1) if b["start"] else 0))
    A("| best / worst it has been | $%s / $%s |"
      % (format(round(b["peak"], 2), ",.2f"),
         format(round(b["low"], 2), ",.2f")))
    A("| fees paid | $%s |" % format(round(b["fees"], 2), ",.2f"))
    A("| contracts looked at | %d |" % len(recs))
    if retired:
        A("| retired (old rule, not counted) | %d |" % len(retired))
    A("| of those, settled and learned from | %d |" % len(settled))
    A("| actual calls (graded GOOD) | %d |" % len(calls))
    A("| calls that have settled | %d |" % len(done))
    if done:
        w = sum(1 for r in done if r["correct"])
        stake = sum(r["price"] for r in done)
        pnl = sum((1.0 - r["price"]) if r["correct"] else -r["price"] for r in done)
        A("| calls right | %d of %d (%.0f%%) |" % (w, len(done), 100 * w / len(done)))
        A("| break-even needed | %.0f%% |" % (100 * stake / len(done)))
        A("| paper P&L | %+.1f%% per dollar staked |"
          % (100 * pnl / stake if stake else 0))
    A("")

    A("## What it is actually learning")
    A("")
    A("Only one thing: **calibration**. When the formula says 78%, how often")
    A("does that really happen? It is a bent ruler being straightened. It is")
    A("not learning to see further ahead, and no amount of it will make the")
    A("bot a better forecaster than Kalshi -- measured over 63 days, Kalshi's")
    A("own price is the better forecast. The bot's only claim is a narrow")
    A("band where its disagreement with Kalshi has been worth something.")
    A("")
    A("The 63-day study is worth %g observations per row below. So %d live"
      % (PRIOR_STRENGTH, len(settled)))
    A("results spread over 20 rows moves things very little, on purpose --")
    A("three lucky wins should not rewrite the table.")
    A("")
    A("## The table it is straightening")
    A("")
    A("| formula says | started at | now says | live results | moved |")
    A("|---|---|---|---|---|")
    moved_any = False
    for b in range(N_BINS):
        n = mem["bins_n"][b]
        if not n:
            continue
        cur = (prior_for(b) * PRIOR_STRENGTH + mem["bins_wins"][b]) / \
              (PRIOR_STRENGTH + n)
        d = cur - prior_for(b)
        if abs(d) > 0.02:
            moved_any = True
        A("| %.0f-%.0f%% | %.3f | %.3f | %d (%d hit) | %+.3f%s |"
          % (100 * b / N_BINS, 100 * (b + 1) / N_BINS, prior_for(b), cur,
             int(n), int(mem["bins_wins"][b]), d, " **" if abs(d) > 0.02 else ""))
    if not moved_any:
        A("")
        A("Nothing has moved more than 0.02 yet. That is the expected state")
        A("early on and is not a fault.")
    A("")

    grades = {}
    for r in recs:
        k = r.get("grade") or "(not recorded)"
        grades[k] = grades.get(k, 0) + 1
    if grades:
        A("## How it graded what it saw")
        A("")
        A("| grade | times |")
        A("|---|---|")
        for k, v in sorted(grades.items(), key=lambda kv: -kv[1]):
            A("| %s | %d |" % (k, v))
        A("")
        y = sum(1 for r in recs if r.get("side") == "YES")
        A("Leaned YES %d times, NO %d times. Over 63 days of history the"
          % (y, len(recs) - y))
        A("split is 49.5% YES, so anything near half and half is normal.")
        A("")

    open_now = [r for r in calls if r.get("correct") is None]
    if open_now:
        A("## Open right now")
        A("")
        A("| placed | contract | side | price | risking | to win |")
        A("|---|---|---|---|---|---|")
        for r in open_now:
            bet = r.get("bet") or {}
            A("| %s | %s | %s | %.2f | $%s | $%s |"
              % (str(r.get("asked"))[11:16], r["ticker"], r["side"], r["price"],
                 format(bet.get("stake", 0), ",.2f"),
                 format(bet.get("to_win", 0), ",.2f")))
        A("")
        A("These have been called but have not settled yet. A 15-minute")
        A("contract takes about that long, plus a minute or two for Kalshi to")
        A("publish the result, so this list is usually empty.")
        A("")

    if done:
        A("## Every call it has made")
        A("")
        A("| placed | closed | side | price | BTC vs target | min left | result | paid | account after |")
        A("|---|---|---|---|---|---|---|---|---|")
        for r in done:
            dist = r.get("dist")
            A("| %s | %s | %s | %.2f | %s | %s | %s | %s | %s |"
              % (str(r.get("asked"))[11:16] if r.get("asked") else "-",
                 str(r["close_time"])[:16].replace("T", " "), r["side"],
                 r["price"],
                 ("%+.0f" % dist) if dist is not None else "-",
                 ("%.0f" % r["mins"]) if r.get("mins") is not None else "-",
                 "RIGHT" if r["correct"] else "**wrong**",
                 ("%+.2f" % r["paid"]) if r.get("paid") is not None else "-",
                 ("$%s" % format(round(r["bank_after"], 2), ",.2f"))
                 if r.get("bank_after") is not None else "-"))
        A("")
        stale = [r for r in done
                 if str(r.get("close_time", "")) < "2026-08-24T19"
                 and r.get("dist") is not None]
        if stale:
            A("**The %d row%s above dated before 24 Aug 19:00 UTC may show a stale"
              % (len(stale), "" if len(stale) == 1 else "s"))
            A("\"BTC vs target\".** Until then a contract first seen as a decline")
            A("kept the distance from that first look, not from the moment it was")
            A("called -- so a call made once BTC had crossed the line can appear")
            A("to have been made well short of it. The side, price, result and")
            A("money on those rows are correct; only the distance and the minutes")
            A("may be from a few minutes earlier. Rows after that are recorded at")
            A("the moment of the call.")
            A("")
        A("\"BTC vs target\" is how many dollars above (+) or below (-) the")
        A("target BTC was when the call was made. That number, the minutes")
        A("left, and how fast BTC had been moving are the whole basis of every")
        A("call -- so a losing row with a small gap and a lot of time left is")
        A("the bot being unlucky, and one with a big gap is it being wrong.")
        A("")
    if done and any(not r["correct"] for r in done):
        # NB: the report's line buffer is already called L in this function,
        # so these must not be.
        lost = [r for r in done if not r["correct"]]
        wonr = [r for r in done if r["correct"]]
        A("## Why the losses happened")
        A("")
        A("| closed | side | price | edge | BTC vs target | min left |")
        A("|---|---|---|---|---|---|")
        for r in lost:
            A("| %s | %s | %.2f | %.0f%% | %s | %s |"
              % (str(r["close_time"])[5:16].replace("T", " "), r["side"],
                 r["price"], 100 * r.get("edge", 0),
                 ("%+d" % r["dist"]) if r.get("dist") is not None else "-",
                 ("%.0f" % r["mins"]) if r.get("mins") is not None else "-"))
        A("")

        def avg(rows, k):
            v = [rw[k] for rw in rows if rw.get(k) is not None]
            return sum(v) / len(v) if v else None

        A("| | n | avg price | avg edge | avg min left |")
        A("|---|---|---|---|---|")
        for lab, rows in (("won", wonr), ("lost", lost)):
            ap, ae, am = avg(rows, "price"), avg(rows, "edge"), avg(rows, "mins")
            A("| %s | %d | %s | %s | %s |"
              % (lab, len(rows),
                 "%.2f" % ap if ap else "-",
                 "%.0f%%" % (100 * ae) if ae else "-",
                 "%.0f" % am if am else "-"))
        A("")
        A("**Read this as a thermometer, not a filter.** A rule fitted to")
        A("avoid these particular losses was built and measured: it reached a")
        A("100% win rate on the losses it had studied and did *worse than")
        A("nothing* on new trades. It memorised them; it did not learn from")
        A("them. Losing trades in the 63-day study had, if anything, slightly")
        A("*more* edge than winners -- 11.6 points against 11.4 -- and the")
        A("biggest signals ever taken include two losses. They are not")
        A("distinguishable in advance, and that is not a gap in the bot: a")
        A("contract trades at 80c precisely because nobody knows which fifth")
        A("of them fail.")
        A("")
        A("What this table is for is spotting a pattern that is *large and")
        A("persistent* -- losses clustered at one price, one time of day, one")
        A("side -- over dozens of trades, not three. If one appears here and")
        A("holds up, it is worth acting on. Until then it is a thermometer.")
        A("")
    A("## What would change the conclusion")
    A("")
    A("The backtest says setups like these hit 89.3% against an 81.3%")
    A("break-even. To tell whether that is real rather than 63 lucky days,")
    A("this needs roughly 100 settled calls. At about 6 a day that is two to")
    A("three weeks of leaving `--loop` running. Below that number, a good")
    A("run and a bad run look identical.")
    A("")
    A("## About the paper account")
    A("")
    A("$1,000 to start, 10% of whatever it is worth on each call. Imaginary.")
    A("Nothing is sent to Kalshi and there is no account behind it.")
    A("")
    A("Run over the 272 confirmed trades from the 63-day study, in the order")
    A("they happened, $1,000 at 10% a call ends at **$13,187**, dipping to")
    A("$899 on the way -- a 29% drawdown. Two reasons not to plan around that:")
    A("")
    A("1. The price window and the confirmation rule were both chosen after")
    A("   looking at all three periods. Some of that 12x is the choosing.")
    A("2. Size eventually bites, though later than once claimed. Measured")
    A("   from 3,130 live order-book snapshots, the median size at the best")
    A("   price is $3,062 and the median spread is 1c. A $1,000 order fills")
    A("   at the quoted price 73% of the time and within 5c always; a $2,500")
    A("   order fills at the quote 56% of the time. So the arithmetic holds")
    A("   to roughly a $25,000 account, not the $10,000 asserted before the")
    A("   book was actually recorded.")
    A("")
    A("A first week -- about 40 calls -- lands between $814 and $1,908 in the")
    A("same simulation, and finishes below $1,000 about 17 times in 100.")
    A("That spread is what a week actually looks like.")
    A("")
    A("Nothing here has been traded with real money.")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    return path, len(recs), len(settled), len(done)


def show_record(mem):
    answered = [r for r in mem["predictions"]
                if r.get("answered") and r.get("correct") is not None
                and not r.get("retired")]
    print()
    line("=")
    print("  TRACK RECORD")
    line("=")
    b = bank_of(mem)
    grow = 100 * (b["cash"] / b["start"] - 1) if b["start"] else 0
    print("  PAPER ACCOUNT   $%s   (%+.1f%% from $%s)"
          % (format(round(b["cash"], 2), ",.2f"), grow,
             format(round(b["start"]), ",d")))
    if b["settled"]:
        print("    %d settled call%s, best $%s, worst $%s, fees $%s"
              % (b["settled"], "" if b["settled"] == 1 else "s",
                 format(round(b["peak"], 2), ",.2f"),
                 format(round(b["low"], 2), ",.2f"),
                 format(round(b["fees"], 2), ",.2f")))
    else:
        print("    Nothing settled yet, so it has not moved.")
    print("    Imaginary money. 10% of the account per call.")
    print()
    side_breakdown(mem)
    if not answered:
        seen = sum(mem["bins_n"])
        calls = sum(1 for r in mem["predictions"]
                    if r.get("answered") and not r.get("retired"))
        gone = sum(1 for r in mem["predictions"] if r.get("retired"))
        pend = sum(1 for r in mem["predictions"]
                   if r.get("answered") and r.get("outcome") is None)
        print("  contracts watched   %d" % len(mem["predictions"]))
        print("  learned from        %d settled" % int(seen))
        print("  actual calls made   %d%s"
              % (calls, "  (%d still open)" % pend if pend else ""))
        if gone:
            print("  retired             %d  (made under the old calibration,"
                  % gone)
            print("                         still teaching, no longer counted)")
        print()
        if not calls:
            print("  It has been learning from contracts it DECLINED. Those")
            print("  still teach it how often the formula is right, which is")
            print("  most of what there is to learn -- but they are not calls,")
            print("  so there is no win/loss record yet.")
            print()
            print("  A call means it graded a setup GOOD and said YES or NO.")
            print("  A setup now has to appear twice, two minutes apart, so")
            print("  roughly 1 run in 75 gets there on its own. Leave it")
            print("  watching instead:")
            print("      python3 check.py --loop")
        else:
            print("  %d call%s made, none settled yet. Each takes ~15 minutes."
                  % (calls, "" if calls == 1 else "s"))
        print()
        return
    live_now = [r for r in mem["predictions"]
                if r.get("answered") and not r.get("retired")
                and r.get("correct") is None]
    if live_now:
        print("  OPEN RIGHT NOW")
        for r in live_now:
            bet = r.get("bet") or {}
            print("    %s  %-3s @ %.2f   risking $%s to win $%s"
                  % (str(r.get("asked"))[11:16], r["side"], r["price"],
                     format(bet.get("stake", 0), ",.2f"),
                     format(bet.get("to_win", 0), ",.2f")))
        print("    (called, not settled yet -- about 15 minutes each)")
        print()

    n = len(answered)
    w = sum(1 for r in answered if r["correct"])
    stake = sum(r["price"] for r in answered)
    pnl = sum((1.0 - r["price"]) if r["correct"] else -r["price"] for r in answered)
    print("  calls answered   %d" % n)
    print("  right / wrong    %d / %d   (%.0f%%)" % (w, n - w, 100 * w / n))
    print("  break-even was   %.0f%%" % (100 * stake / n))
    print("  paper P&L        %+.2f per $1 staked  (%+.1f%%)"
          % (pnl / n, 100 * pnl / stake if stake else 0))
    print()
    print("  last 10:")
    for r in answered[-10:]:
        print("    %s  %-3s @ %.2f  ->  %s"
              % (str(r["close_time"])[:16].replace("T", " "), r["side"],
                 r["price"], "RIGHT" if r["correct"] else "wrong"))
    moved = [b for b in range(N_BINS) if mem["bins_n"][b] > 0]
    if moved:
        print()
        print("  what it has adjusted:")
        for b in moved:
            cur = (prior_for(b) * PRIOR_STRENGTH + mem["bins_wins"][b]) / \
                  (PRIOR_STRENGTH + mem["bins_n"][b])
            flag = "  <- moved" if abs(cur - prior_for(b)) > 0.02 else ""
            print("    formula %.2f-%.2f : %.3f -> %.3f  (%d live)%s"
                  % (b / N_BINS, (b + 1) / N_BINS, prior_for(b), cur,
                     int(mem["bins_n"][b]), flag))
    print()


def get(url, params=None, timeout=20):
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-check/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8", errors="replace")), None
    except Exception as e:                                    # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def calibrate(p):
    if p <= CAL_X[0]:
        return CAL_Y[0]
    if p >= CAL_X[-1]:
        return CAL_Y[-1]
    for i in range(1, len(CAL_X)):
        if p <= CAL_X[i]:
            x0, x1, y0, y1 = CAL_X[i - 1], CAL_X[i], CAL_Y[i - 1], CAL_Y[i]
            return y0 + (y1 - y0) * (p - x0) / (x1 - x0)
    return CAL_Y[-1]


def bars():
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=125)
    data, err = get(COINBASE, {"granularity": 60, "start": start.isoformat(),
                               "end": end.isoformat()})
    if err:
        return None, None, err
    if not isinstance(data, list) or len(data) < 40:
        return None, None, "only %d bars returned" % (len(data) if data else 0)
    rows = sorted(data, key=lambda x: x[0])[:-1]     # drop the forming bar
    return [float(r[4]) for r in rows], [float(r[5]) for r in rows], None


def live_spot():
    """
    BTC right now, from the live ticker rather than the last closed candle.

    Candles are 1-minute buckets and the forming one has to be dropped, so a
    candle-derived price can be nearly two minutes old. Measured live during a
    fast move, that was $26 off -- material when the whole edge is 4.5 points,
    and it grows exactly when BTC is moving, which is when it matters most.

    Volatility still comes from the candles; only spot comes from here.
    Returns None on failure and the caller falls back to the candle.
    """
    d, err = get(COINBASE_TICKER, timeout=10)
    if err or not isinstance(d, dict):
        return None
    try:
        px = float(d.get("price"))
    except (TypeError, ValueError):
        return None
    return px if 1000.0 < px < 10_000_000.0 else None


def vol_per_min(closes, look=15):
    seg = closes[-(look + 1):]
    rets = [math.log(b / a) for a, b in zip(seg, seg[1:]) if a > 0]
    if len(rets) < 3:
        return None
    m = sum(rets) / len(rets)
    return math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1)) or None


def ema(v, span):
    if len(v) < span:
        return None
    k = 2.0 / (span + 1.0)
    e = sum(v[:span]) / span
    for x in v[span:]:
        e = x * k + e * (1 - k)
    return e


def rsi(c, period=14):
    if len(c) < period + 2:
        return None
    g = l = 0.0
    for a, b in zip(c[:period], c[1:period + 1]):
        d = b - a
        g += max(d, 0.0)
        l += max(-d, 0.0)
    ag, al = g / period, l / period
    for a, b in zip(c[period:-1], c[period + 1:]):
        d = b - a
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
    if al == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def refetch(ticker):
    """Read one contract's book again, right now. None if it is unusable."""
    d, err = get(KALSHI + "/markets/" + str(ticker))
    mk = (d or {}).get("market") or {}
    ya, yb, ct = (mk.get("yes_ask_dollars"), mk.get("yes_bid_dollars"),
                  mk.get("close_time"))
    if err or ya is None or yb is None or not ct:
        return None
    try:
        mins = (datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
                - datetime.now(timezone.utc)).total_seconds() / 60.0
    except Exception:                                         # noqa: BLE001
        return None
    ya, yb = float(ya), float(yb)
    if not (0.0 < ya < 1.0) or not (0.0 <= yb < ya):
        return None
    return ya, yb, mins


def live():
    d, err = get(KALSHI + "/markets",
                 {"series_ticker": SERIES, "status": "open", "limit": 50})
    if err:
        return None, err
    now = datetime.now(timezone.utc)
    best = None
    for m in (d or {}).get("markets") or []:
        ct = m.get("close_time")
        if not ct:
            continue
        cd = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
        mins = (cd - now).total_seconds() / 60.0
        if 0.0 < mins <= 15.5 and (best is None or mins < best[1]):
            best = (m, mins)
    if not best:
        return None, "no BTC 15-minute contract is open right now"
    return best, None


def line(ch="-"):
    print("  " + ch * W)


def answer(verdict, colour_note=""):
    print()
    print("  " + "=" * W)
    print("  ANSWER:   %s%s" % (verdict, colour_note))
    print("  " + "=" * W)


WAITING = False


def cant(reason, detail="", normal=True):
    """normal=True means 'no edge here'. False means 'no data / market shut'."""
    if WAITING:
        raise NoSetup(reason)
    answer("CAN'T SAY")
    print()
    print("  %s" % reason)
    if detail:
        words, cur = detail.split(), ""
        for w in words:
            if len(cur) + len(w) + 1 > W:
                print("  %s" % cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            print("  %s" % cur)
    print()
    if normal:
        print("  This is the normal outcome. Kalshi is usually priced")
        print("  correctly, and most of the time there is genuinely")
        print("  nothing to say.")
    else:
        print("  Nothing is wrong with the tool -- there is just no market")
        print("  to look at. Try again shortly.")
    print()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------
# Two numbers that must never be confused:
#
#   CHANCE IT HITS -- how often this call comes true. An 80c contract hits
#                     about 80% of the time. That is arithmetic, not skill,
#                     and it says nothing about whether the trade is good.
#
#   TRADE GRADE    -- whether setups like this actually made money. Measured
#                     over 63 days and 59,860 decision points, per dollar
#                     staked, on train / validation / test separately.
#
# The 'above 90c' row is the clearest illustration of why both are needed: a
# 95.5% hit rate, and not a trade worth making.
#
#     grade                     n     hits    train    valid     test
#     GOOD 70-90c, 10+ min   2,344   82.3%   +3.46%   +2.00%   +4.27%
#     WEAK 50-70c            3,458   62.3%   -0.22%   +1.75%   +2.85%
#     WEAK 5-10 min left     3,577   77.7%   +0.35%   +2.73%   +1.36%
#     WEAK above 90c            89   95.5%   too few to judge
#     NONE no disagreement  14,665   75.4%   -2.41%   -2.40%   +0.85%
#     BAD  cheap side       11,787   27.5%   -9.84%   -9.11%  -11.20%
#     BAD  last 5 minutes   23,940   39.9%   -3.03%   -1.59%   -3.23%

def grade_of(price, edge, mins, spread, confirmed):
    """Grade this setup against what setups like it actually returned."""
    if mins < 5:
        return {"label": "BAD -- do not trade", "short": "BAD (last 5 min)",
                "trade": False,
                "why": ["Only %.1f minutes left. Late entries lose." % mins],
                "stats": (23940, 39.9, "-3.0% / -1.6% / -3.2%")}
    if price < 0.50:
        return {"label": "BAD -- do not trade", "short": "BAD (cheap side)",
                "trade": False,
                "why": ["This is the cheap side at %.0fc. Cheap contracts lose"
                        % (100 * price),
                        "badly and consistently -- the worst category measured."],
                "stats": (11787, 27.5, "-9.8% / -9.1% / -11.2%")}
    if spread > MAX_SPREAD:
        return {"label": "BAD -- spread too wide", "short": "BAD (wide spread)",
                "trade": False,
                "why": ["The spread is %.0f cents. Getting in costs more than"
                        % (100 * spread),
                        "the edge is worth."],
                "stats": None}
    if edge < MIN_EDGE:
        if edge >= 0.05:
            return {"label": "WEAK -- disagreement too small",
                    "short": "WEAK (small disagreement)", "trade": False,
                    "why": ["I disagree with Kalshi by %.0f points. That used to"
                            % (100 * edge),
                            "be enough; measuring it showed it is not. Setups",
                            "in the 5-to-7 point range won 86.0%% against an 84%%",
                            "break-even -- inside the noise. 7 points is the line."],
                    "stats": (107, 86.0, "+0.2% / +3.3% / +5.6%")}
        return {"label": "NO EDGE -- skip", "short": "NONE (no disagreement)",
                "trade": False,
                "why": ["Kalshi's price already matches my estimate, so there",
                        "is nothing to take. This is the usual outcome."],
                "stats": (14665, 75.4, "-2.4% / -2.4% / +0.9%")}
    if mins < MIN_MINUTES_LEFT:
        return {"label": "WEAK -- small size only", "short": "WEAK (5-10 min)",
                "trade": False,
                "why": ["%.1f minutes left. Positive on average but shaky --"
                        % mins,
                        "barely above break-even in training."],
                "stats": (3577, 77.7, "+0.4% / +2.7% / +1.4%")}
    if price > MAX_PRICE:
        return {"label": "WEAK -- poor payoff", "short": "WEAK (above 90c)",
                "trade": False,
                "why": ["At %.0fc there is almost nothing to win." % (100 * price),
                        "Only 89 of these in 63 days -- too few to trust."],
                "stats": None}
    if price < MIN_PRICE:
        return {"label": "WEAK -- small size only", "short": "WEAK (50-70c)",
                "trade": False,
                "why": ["At %.0fc this is closer to a coin flip." % (100 * price),
                        "It was NEGATIVE in training, positive after. Unproven."],
                "stats": (3458, 62.3, "-0.2% / +1.8% / +2.9%")}
    if not confirmed:
        return {"label": "ALMOST -- look again in 2 minutes",
                "short": "ALMOST (not confirmed yet)", "trade": False,
                "why": ["%.0fc, %.0f min left, %.0f-point edge -- the right shape."
                        % (100 * price, mins, 100 * edge),
                        "But I have only seen it once. Setups that were still",
                        "there two minutes later hit 89.3%; ones that were not",
                        "hit 80.5%. Re-run in 2 minutes -- if it still says",
                        "the same thing, it upgrades to GOOD."],
                "stats": (522, 80.5, "+1.8% / +3.1% / +2.8%")}
    return {"label": "GOOD -- confirmed, the zone that held up",
            "short": "GOOD", "trade": True,
            "why": ["%.0fc entry, %.0f minutes left, %.0f-point edge, and the"
                    % (100 * price, mins, 100 * edge),
                    "same call was already standing two minutes ago.",
                    "The only combination positive in all three periods."],
            "stats": (272, 89.3, "+10.3% / +9.6% / +10.7%")}


def evaluate(mem, a):
    # In --wait and --loop this runs every 30 seconds for hours. Printing the
    # full readout each time buries the one line that matters and, on a cloud
    # runner, produces a log nobody will scroll. So the readout is buffered
    # and only actually printed when there is something to say.
    out = []
    say = out.append

    def sayline(ch="-"):
        out.append("  " + ch * W)

    def flush():
        for t in out:
            print(t)
        del out[:]

    if not WAITING:
        print()
        print("  Checking the BTC 15-minute contract...")
    settle_pending(mem)

    got, err = live()
    if err:
        if "no BTC" in err:
            now = datetime.now(timezone.utc)
            hint = ""
            # Kalshi pauses trading 03:00-05:00 ET for weekly maintenance,
            # which is 07:00-09:00 UTC on eastern daylight time.
            if 7 <= now.hour < 9:
                hint = ("Kalshi runs scheduled maintenance 3-5 AM ET "
                        "(you are inside that window now). Trading is paused.")
            else:
                hint = ("There is a short gap between one contract closing "
                        "and the next opening. Wait a minute and re-run.")
            cant("No BTC 15-minute contract is open right now.", hint,
                 normal=False)
        cant("Cannot reach Kalshi.", err[:70], normal=False)
    m, mins = got

    closes, vols, err = bars()
    if err:
        cant("Cannot get a reliable BTC price.", err[:70], normal=False)

    strike = m.get("floor_strike")
    yb, ya = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
    if strike is None or yb is None or ya is None:
        cant("Kalshi is not quoting this contract right now.",
             "The market exists but has no bid or ask yet.", normal=False)
    strike, yb, ya = float(strike), float(yb), float(ya)

    # An empty order book reports 0 for everything. That is not a price of
    # zero, it is the absence of a price -- during Kalshi's 3-5 AM ET
    # maintenance pause, and briefly when a contract first opens, the book is
    # empty. Without this check the arithmetic treats "buy YES for 0c" as a
    # free lottery ticket and reports an enormous fake edge.
    if not (0.0 < ya < 1.0) or not (0.0 <= yb < ya):
        now = datetime.now(timezone.utc)
        why = ("Kalshi runs maintenance 3-5 AM ET and the order book empties "
               "out. You are inside that window now."
               if 7 <= now.hour < 9 else
               "The order book is empty -- nobody is quoting this contract "
               "yet. It usually fills in within a minute of opening.")
        cant("Every price on this contract is showing 0.", why, normal=False)

    spot = closes[-1]
    tick = live_spot()
    spot_src = "last closed minute"
    if tick is not None:
        # Sanity-gate the ticker against the candle. A wild disagreement means
        # one of them is broken, and the candle is the more trustworthy of the
        # two, so keep it rather than trade on a number we cannot corroborate.
        if abs(tick - spot) / spot < 0.01:
            spot, spot_src = tick, "live ticker"
        else:
            spot_src = "last closed minute (ticker disagreed by %.0f%%, ignored)" \
                       % (100 * abs(tick - spot) / spot)
    spot += COINBASE_TO_BRTI          # shift onto Kalshi's index
    spot_src += " +$%.2f to Kalshi index" % COINBASE_TO_BRTI
    v = max(vol_per_min(closes) or MIN_VOL, MIN_VOL)
    raw = norm_cdf(math.log(spot / strike) / (v * math.sqrt(max(mins, 0.05))))
    p = learned(mem, raw)

    no_ask = 1.0 - yb
    spread = ya - yb

    # The ANSWER is simply which way the model leans, so the confidence shown
    # is always the probability of the thing being asserted. Reporting "NO,
    # 46% chance" -- which the earlier version could do when the two sides had
    # similar edge -- reads as a contradiction and is no use to anybody.
    #
    # The TRADE is then judged on buying that same side: whether the price of
    # the direction we favour is worth paying.
    side = "YES" if p >= 0.5 else "NO"
    conf = p if side == "YES" else 1.0 - p
    price = ya if side == "YES" else no_ask
    edge = conf - price

    # ---- write this look down ------------------------------------------
    # "Qualifying" here is everything grade_of asks for EXCEPT confirmation,
    # so a look that qualifies on its own merits is what a later look gets to
    # confirm against. Confirmation confirming itself would be worthless.
    qualifies = (mins >= MIN_MINUTES_LEFT and MIN_PRICE <= price <= MAX_PRICE
                 and edge >= MIN_EDGE and spread <= MAX_SPREAD)
    confirmed, earlier = note_poll(mem, m.get("ticker"), mins, side, qualifies)

    # ---- the readout -------------------------------------------------
    say("")
    sayline("=")
    say("  %s" % m.get("ticker"))
    sayline("=")
    say("  BTC now      $%s   (%s)" % (format(round(spot, 2), ",.2f"), spot_src))
    say("  Target       $%s" % format(round(strike, 2), ",.2f"))
    say("  Difference   %s$%s" % ("+" if spot >= strike else "-",
                                    format(abs(round(spot - strike, 2)), ",.2f")))
    say("  Time left    %.1f minutes" % mins)
    say("  Kalshi       YES %.0fc  /  NO %.0fc" % (100 * ya, 100 * no_ask))

    # If we have looked at this contract before, say what we said, because a
    # lean that flips between looks is the single most confusing thing this
    # tool does -- and it is not a bug. Near the strike the answer genuinely
    # is a coin flip, and a coin flip flips. Measured over 63 days, same
    # contract at 12 minutes then 10 minutes:
    #
    #     confidence 50-55%   flipped 44% of the time
    #                55-65%           29%
    #                65-75%           18%
    #                75-85%            9%
    #                  85%+            3%
    #
    # So a flipping answer is the tool telling you it does not know. That is
    # exactly the case confirmation now refuses to trade.
    if earlier:
        seq = "".join("Y" if q["side"] == "YES" else "N" for q in earlier[-8:])
        seq += "Y" if side == "YES" else "N"
        flips = sum(1 for x, y in zip(seq, seq[1:]) if x != y)
        say("  Looks so far %s   (%d look%s, %d change%s of mind)"
              % (seq, len(seq), "" if len(seq) == 1 else "s",
                 flips, "" if flips == 1 else "s"))
        if flips:
            say("               A changing answer means it is close to the")
            say("               line and does not know. Flip rate at %.0f%%"
                  % (100 * min(conf, 0.99)))
            say("               confidence is about %s."
                  % ("44%" if conf < 0.55 else "29%" if conf < 0.65 else
                     "18%" if conf < 0.75 else "9%" if conf < 0.85 else "3%"))

    if a.why:
        r = rsi(closes)
        e9, e21 = ema(closes, 9), ema(closes, 21)
        say("")
        say("  volatility   %.4f%% per minute" % (100 * v))
        say("  raw model    %.1f%%   ->  calibrated %.1f%%" % (100 * raw, 100 * p))
        if r is not None:
            say("  RSI(14)      %.1f" % r)
        if e9 and e21:
            say("  EMA 9 v 21   %s" % ("above" if e9 > e21 else "below"))
        say("  spread       %.0fc" % (100 * spread))

    def remember(answered):
        prev = next((r for r in mem["predictions"]
                     if r["ticker"] == m.get("ticker")), None)
        if prev is not None:
            # --loop looks at the same contract many times. Which look counts
            # depends on what the field is for.
            #
            # raw and p stay from the FIRST look: they feed the calibration
            # bins, and that wants one observation per contract, taken before
            # anything was decided.
            #
            # Everything describing the CALL is refreshed to the moment the
            # call was made. It used to keep the first look's spot, strike,
            # distance, minutes and timestamp, which made the record lie: a
            # contract declined at 14 minutes with BTC $17 the wrong side,
            # then called four minutes later once BTC had crossed, was
            # recorded as a call made $17 the wrong side. Reading the record
            # back, the bot looked like it bet on reversals. It does not: the
            # calibration curve crosses 0.5 at raw 0.4973, which at a typical
            # volatility over twelve minutes is BTC about sixty cents below
            # the target -- so a YES call needs BTC essentially at or past the
            # line, and $17 short of it is not reachable. The number was
            # stale, not the behaviour. All 272 backtest trades are on the
            # side they bet.
            if answered and not prev.get("answered"):
                prev.update({"answered": True, "side": side, "price": price,
                             "edge": edge, "bet": plan_stake(mem, price),
                             "asked": datetime.now(timezone.utc).isoformat(),
                             "grade": grade_short, "mins": round(mins, 1),
                             "spot": round(spot, 2), "strike": round(strike, 2),
                             "dist": round(spot - strike, 2),
                             "vol": round(v, 6)})
                save_memory(mem)
            return
        mem["predictions"].append({
            "asked": datetime.now(timezone.utc).isoformat(),
            "ticker": m.get("ticker"), "close_time": m.get("close_time"),
            "raw": raw, "p": p, "side": side, "price": price,
            "edge": edge, "grade": grade_short, "mins": round(mins, 1),
            # What the call was actually looking at. Without these a past
            # call cannot be checked -- "why did it say YES?" has no answer
            # once the moment has gone, and an unauditable record is not
            # much of a record.
            "spot": round(spot, 2), "strike": round(strike, 2),
            "dist": round(spot - strike, 2), "vol": round(v, 6),
            "answered": bool(answered), "outcome": None,
            "bet": plan_stake(mem, price) if answered else None})
        mem["predictions"] = mem["predictions"][-2000:]
        save_memory(mem)

    # ---- grade it ------------------------------------------------------
    g = grade_of(price, edge, mins, spread, confirmed)

    # A quote goes stale between reading it and acting on it. The check takes
    # a second or two, the alert takes a moment to arrive, and you take longer
    # than that to open Kalshi -- and a 15-minute contract can move 9 cents in
    # a minute (measured: two copies of this bot, one minute apart, quoted the
    # same contract at 72c and 81c).
    #
    # So before committing to a call, read the price one more time and redo
    # the arithmetic on it. If it still qualifies, the number you are given is
    # the fresh one. If it has moved out of the rules, say so instead of
    # sending you after a price that no longer exists.
    if g["trade"]:
        fresh = refetch(m.get("ticker"))
        if fresh is None:
            g = {"label": "GONE -- lost the quote while checking",
                 "short": "GONE (no quote)", "trade": False,
                 "why": ["It qualified, then Kalshi stopped quoting it before",
                         "I could confirm the price. Not acting on a stale one."],
                 "stats": None}
        else:
            fya, fyb, fmins = fresh
            ftick = live_spot()
            base = spot - COINBASE_TO_BRTI
            fspot = (ftick + COINBASE_TO_BRTI) if (
                ftick and abs(ftick - base) / max(base, 1) < 0.01) else spot
            fraw = norm_cdf(math.log(fspot / strike)
                            / (v * math.sqrt(max(fmins, 0.05))))
            fp = learned(mem, fraw)
            fside = "YES" if fp >= 0.5 else "NO"
            fconf = fp if fside == "YES" else 1.0 - fp
            fprice = fya if fside == "YES" else 1.0 - fyb
            fedge = fconf - fprice
            fspread = fya - fyb
            moved = abs(fprice - price)
            g2 = grade_of(fprice, fedge, fmins, fspread, confirmed) \
                if fside == side else None
            if g2 is None or not g2["trade"]:
                was = "%.0fc" % (100 * price)
                now = ("%s at %.0fc" % (fside, 100 * fprice)) if fside != side \
                    else "%.0fc" % (100 * fprice)
                g = {"label": "GONE -- it moved while I was checking",
                     "short": "GONE (moved)", "trade": False,
                     "why": ["It qualified at %s, and by the time I re-read the"
                             % was,
                             "book it was %s. That is no longer a trade." % now,
                             "Chasing a price that has already gone is how a",
                             "measured edge turns into a real loss."],
                     "stats": None}
            else:
                # Fresh numbers win: everything reported from here is what the
                # book says now, not what it said when the check started.
                side, conf, price, edge = fside, fconf, fprice, fedge
                mins, spread, spot, raw, p, g = fmins, fspread, fspot, fraw, fp, g2
                if moved >= 0.01:
                    g["why"] = list(g["why"]) + [
                        "(re-checked just now: price moved %.0f cent%s, still good.)"
                        % (100 * moved, "" if round(100 * moved) == 1 else "s")]
    grade_short = g["short"]
    remember(g["trade"])

    # A confirmed setup stays confirmed for the rest of the contract, so a
    # 30-second loop would re-announce the same call twenty times. One call
    # per contract: that is also how it was counted in the backtest.
    called = mem.setdefault("alerted", [])
    already = m.get("ticker") in called
    if g["trade"] and not already:
        called.append(m.get("ticker"))
        mem["alerted"] = called[-200:]
    save_memory(mem)          # note_poll changed the memory either way
    if WAITING and g["trade"] and already:
        raise NoSetup("already called %s at %.0fc on this contract"
                      % (side, 100 * price))
    if WAITING and not g["trade"]:
        # --wait holds out for a GOOD grade. Everything else is reported as a
        # reason and the loop carries on.
        raise NoSetup("%s  (%s at %.0fc, %.0f min)"
                      % (g["short"], side, 100 * price, mins))

    flush()
    answer(side)
    if g["trade"] and not already:
        # Short on purpose. The detail lives in --report; a phone alert has
        # one job, which is to say what to buy and for how much.
        bet = next((r["bet"] for r in mem["predictions"]
                    if r["ticker"] == m.get("ticker") and r.get("bet")), None)
        send_ntfy("%s %.0fc  -  %.0f min" % (side, 100 * price, mins),
                  "$%s at %.0fc.  edge %.0f  -  paper $%s"
                  % (format(bet["stake"], ",.0f") if bet else "?",
                     100 * price, 100 * edge,
                     format(round(bet["bank_before"]), ",d") if bet else "?"),
                  tags="rotating_light", priority="high")
    print()
    print("  Buy %s at %.0f cents" % (side, 100 * price))
    if g["trade"]:
        bet = next((r["bet"] for r in mem["predictions"]
                    if r["ticker"] == m.get("ticker") and r.get("bet")), None)
        if bet:
            print()
            print("  PAPER ACCOUNT  $%s"
                  % format(round(bet["bank_before"], 2), ",.2f"))
            print("    risks       $%s  (10%%, %.0f contracts, $%.2f fee)"
                  % (format(bet["stake"], ",.2f"), bet["contracts"], bet["fee"]))
            print("    to win      $%s" % format(bet["to_win"], ",.2f"))
            print("    No money is sent anywhere. This is a scoreboard.")
    print()
    print("  CHANCE IT HITS      %.0f%%" % (100 * min(conf, 0.99)))
    print("  TRADE GRADE         %s" % g["label"])
    print()
    for ln in g["why"]:
        print("  %s" % ln)
    print()
    line()
    if g["stats"]:
        n, wr, rets = g["stats"]
        print("  Setups graded %s over 63 days: %d of them." % (g["short"], n))
        print("  They hit %.1f%% of the time and returned %s per dollar" % (wr, rets))
        print("  across the three test periods.")
    else:
        print("  Too few of these in 63 days to say anything reliable.")
    print()
    if g["trade"]:
        print("  Read the hit rate carefully: an 80c contract hits ~80% of the")
        print("  time by definition. What makes this one worth taking is the")
        print("  %.0f-point gap between my estimate and the price -- not the %.0f%%."
              % (100 * edge, 100 * min(conf, 0.99)))
    else:
        print("  A high chance of hitting is NOT the same as a good trade. At")
        ratio = price / max(1 - price, 0.01)
        many = "%.1f" % ratio if ratio < 10 else "%d" % round(ratio)
        print("  %.0fc you risk %.0fc to win %.0fc, so one miss undoes %s %s."
              % (100 * price, 100 * price, 100 * (1 - price), many,
                 "win" if many == "1.0" else "wins"))
    print()
    print("  Never tested with live money. Size small or not at all.")
    print()
    n_live = sum(mem["bins_n"])
    if n_live:
        print("  It has learned from %d settled contract%s of its own so far."
              % (int(n_live), "" if n_live == 1 else "s"))
        print("  Run  python3 check.py --record  for its track record.")
        print()


def wait_loop(mem, a):
    """
    Poll until a setup appears, then print it once and stop.

    Only about 4% of random moments look right, and a setup now has to look
    right twice, two minutes apart, before it counts -- so roughly 1 run in 75
    lands a call by hand. This waits for you instead. Because it polls every
    30 seconds it sees the same contract repeatedly, which is exactly what
    confirmation needs, and it exits the moment one is confirmed.
    """
    global WAITING
    WAITING = True
    print()
    print("  Waiting for a setup that shows up twice, two minutes apart.")
    print("  Roughly 6 a day, so this may take a while. Ctrl-C to stop.")
    print()
    settle_pending(mem)
    checks = 0
    last_reason = None
    started = datetime.now(timezone.utc)
    while True:
        checks += 1
        try:
            # WAITING stays True throughout: cant() raises instead of exiting,
            # so a decline sends us round the loop. If evaluate() returns
            # normally it has already printed a real answer, and we are done.
            evaluate(mem, a)
            return
        except NoSetup as e:
            reason = str(e)
            if reason != last_reason:
                print("  %s  %s" % (datetime.now().strftime("%H:%M:%S"), reason))
                last_reason = reason
            elif checks % 10 == 0:
                mins = (datetime.now(timezone.utc) - started).total_seconds() / 60
                print("  %s  still waiting (%d checks, %.0f min)"
                      % (datetime.now().strftime("%H:%M:%S"), checks, mins))
        except KeyboardInterrupt:
            print("\n  Stopped after %d checks." % checks)
            return
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n  Stopped after %d checks." % checks)
            return


def run_forever(mem, a):
    """
    Watch continuously. Alert on every confirmed setup, and again when it
    settles. Never exits on its own.

    Unlike --wait, this does not stop after a hit: a setup is roughly 6 a day,
    so stopping after one means restarting it a dozen times. The settle alert
    is the point of leaving it up -- it tells you whether the call was right
    without you checking Kalshi.
    """
    global WAITING
    WAITING = True
    print()
    line("=")
    print("  WATCHING -- Ctrl-C to stop")
    line("=")
    if ntfy_topic():
        # Printed in full, not truncated. Two copies of the project in two
        # folders means two config files and two topics, and a half-printed
        # topic makes that impossible to notice -- you subscribe the phone to
        # one and the bot posts to the other, and nothing ever arrives.
        print("  Alerts go to ntfy topic:  %s" % ntfy_topic())
        print("  Tagged [%s] so you can tell it from the other copy."
              % where_am_i())
        print("  (from %s)" % (("environment variable NTFY_TOPIC")
                               if os.environ.get("NTFY_TOPIC") else CONFIG))
    else:
        print("  No phone alerts set up. Run  python3 check.py --alerts")
        print("  to switch them on. Everything still prints here.")
    print()
    print("  A setup has to appear twice, two minutes apart. About 4 a day,")
    print("  so most of the time nothing will happen. That is normal.")
    print()
    print("  Left up for a day it sees about 96 contracts and learns from all")
    print("  of them, not just the ones it trades.")
    if sys.platform == "darwin":
        print()
        print("  A sleeping Mac stops this dead. To keep it awake, quit and")
        print("  restart it as:")
        print("      caffeinate -i python3 check.py --loop")
    print()
    checks = hits = 0
    last_reason = None
    started = datetime.now(timezone.utc)
    stop_at = (started + timedelta(hours=a.hours)) if a.hours else None
    if stop_at:
        print("  Will stop by itself in %.1f hours." % a.hours)
        print()
    while True:
        if stop_at and datetime.now(timezone.utc) >= stop_at:
            print("  %s  time is up." % datetime.now().strftime("%H:%M:%S"))
            break
        checks += 1
        try:
            evaluate(mem, a)          # prints the whole readout and alerts
            hits += 1
            print("  %s  that is call %d. Still watching."
                  % (datetime.now().strftime("%H:%M:%S"), hits))
            last_reason = None
        except NoSetup as e:
            reason = str(e)
            if reason != last_reason:
                print("  %s  %s" % (datetime.now().strftime("%H:%M:%S"), reason))
                last_reason = reason
            elif checks % 40 == 0:
                up = (datetime.now(timezone.utc) - started).total_seconds() / 60
                print("  %s  still watching (%d checks, %.0f min, %d call%s)"
                      % (datetime.now().strftime("%H:%M:%S"), checks, up,
                         hits, "" if hits == 1 else "s"))
        except KeyboardInterrupt:
            break
        except Exception as e:                                # noqa: BLE001
            # A dropped connection must not end an overnight run.
            print("  %s  hiccup (%s) -- retrying"
                  % (datetime.now().strftime("%H:%M:%S"),
                     ("%s: %s" % (type(e).__name__, e))[:60]))
        try:
            # 15 seconds, not 30. A contract lives 15 minutes and can move
            # several cents in one of them; half the wait means half the
            # staleness, and the confirmation gap is measured in minutes so
            # it is unaffected.
            time.sleep(15)
        except KeyboardInterrupt:
            break
    up = (datetime.now(timezone.utc) - started).total_seconds() / 60
    print("\n  Stopped after %d check%s over %.0f minutes, %d call%s."
          % (checks, "" if checks == 1 else "s", up,
             hits, "" if hits == 1 else "s"))


def choose_mode():
    """Ask once, up front, instead of making the user remember a flag."""
    print()
    line("=")
    print("  HOW DO YOU WANT TO RUN IT?")
    line("=")
    print("    1   Once  --  check right now, print the answer, stop.")
    print()
    print("    2   Keep running  --  watch all day, alert my phone every")
    print("        time there is a call and again when it settles.")
    print("        Ctrl-C to stop.")
    print()
    while True:
        try:
            pick = input("  1 or 2 ? ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if pick in ("1", "2"):
            return pick
        print("  Type 1 or 2.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--why", action="store_true",
                    help="show every number behind the answer")
    ap.add_argument("--wait", action="store_true",
                    help="keep checking until a setup appears, then stop")
    ap.add_argument("--record", action="store_true",
                    help="show the track record and what it has learned")
    ap.add_argument("--confirm", metavar="YES|NO",
                    help="manually tell it how the last contract settled")
    ap.add_argument("--loop", action="store_true",
                    help="keep watching and alerting until you stop it")
    ap.add_argument("--once", action="store_true",
                    help="check now and stop, without asking")
    ap.add_argument("--alerts", action="store_true",
                    help="set up phone alerts (ntfy) and send a test")
    ap.add_argument("--digest", action="store_true",
                    help="send one summary of the whole record to your phone")
    ap.add_argument("--report", action="store_true",
                    help="write a full report of what it has learned")
    ap.add_argument("--reset-bank", action="store_true",
                    help="set the paper account back to $1,000")
    ap.add_argument("--hours", type=float, default=0,
                    help="with --loop, stop cleanly after this many hours")
    a = ap.parse_args()

    if a.alerts:
        return ntfy_setup()

    mem = load_memory()

    if a.record:
        settle_pending(mem, quiet=True)
        save_memory(mem)
        show_record(mem)
        return

    if getattr(a, "reset_bank", False):
        mem["bank"] = {"cash": PAPER_START, "start": PAPER_START,
                       "peak": PAPER_START, "low": PAPER_START,
                       "settled": 0, "fees": 0.0}
        # Retire the old calls, do not merely unhook their money. Zeroing the
        # bank alone left a record reading "8 calls, 7 right" beside "$1,000,
        # fees $0.00" -- a win rate with no money behind it, which is worse
        # than either number alone. A call whose result no longer counts is
        # not a call. They stay for calibration: the raw formula is unchanged
        # and the outcomes are real observations.
        gone = 0
        for r in mem["predictions"]:
            r.pop("paid", None)
            r.pop("bank_after", None)
            r.pop("bet", None)
            if r.get("answered") and not r.get("retired"):
                r["retired"] = ("reset by hand on %s"
                                % datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                gone += 1
        save_memory(mem)
        print("  Paper account reset to $%s." % format(round(PAPER_START), ",d"))
        if gone:
            print("  %d earlier call%s retired -- still teaching calibration,"
                  % (gone, "" if gone == 1 else "s"))
            print("  no longer counted in the win/loss record.")
        return

    if a.digest:
        return digest(mem)

    if a.report:
        settle_pending(mem, quiet=True)
        save_memory(mem)
        path, seen, settled, done = write_report(mem)
        print()
        print("  Wrote %s" % path)
        print("    %d contracts looked at, %d settled and learned from,"
              % (seen, settled))
        print("    %d calls settled." % done)
        if done < 100:
            print()
            print("    %d of the ~100 settled calls needed before the win rate"
                  % done)
            print("    means anything. Leave --loop running.")
        print()
        return

    if a.confirm:
        v = a.confirm.strip().upper()
        if v not in ("YES", "NO"):
            sys.exit("  --confirm takes YES or NO")
        pend = [r for r in mem["predictions"] if r.get("outcome") is None]
        if not pend:
            sys.exit("  Nothing waiting to be confirmed.")
        rec = pend[-1]
        y = 1 if v == "YES" else 0
        rec["outcome"] = y
        b = bin_of(rec["raw"])
        mem["bins_n"][b] += 1.0
        mem["bins_wins"][b] += 1.0 if y == 1 else 0.0
        if rec.get("answered"):
            rec["correct"] = bool((rec["side"] == "YES") == (y == 1))
            print("  Recorded: %s settled %s -- my call was %s."
                  % (rec["ticker"], v, "RIGHT" if rec["correct"] else "WRONG"))
        else:
            print("  Recorded: %s settled %s." % (rec["ticker"], v))
        save_memory(mem)
        return

    if a.wait:
        return wait_loop(mem, a)
    if a.loop:
        return run_forever(mem, a)
    if a.once:
        return evaluate(mem, a)

    # No mode asked for: ask. Only when there is somebody there to answer --
    # piped into a script or run from cron, fall back to a single check.
    if sys.stdin.isatty() and choose_mode() == "2":
        return run_forever(mem, a)
    evaluate(mem, a)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
