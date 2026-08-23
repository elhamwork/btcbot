#!/usr/bin/env python3
"""
check.py -- ask once, get one answer.

    python3 check.py

Looks at the BTC 15-minute contract open right now and answers YES, NO, or
CAN'T SAY. Then it exits. Nothing runs in the background.

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
On 63 days of history, setups passing all these filters won 87.7% of the time
against an 82.0% break-even, across 414 independent contracts (p=0.0012).
A ~5.7 point edge, positive in all three test periods: 87.6 / 87.7 / 87.9.

The last filter -- confirmation -- is what lifted it from 81.9% to 87.7%. It
costs volume: about 6 setups a day instead of 20. `--wait` does the waiting.

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

MIN_EDGE = 0.05
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
#   confirmed      242  87.6% +6.5%    65  87.7% +7.0%   107  87.9% +8.4%   87.7%
#   NOT confirmed  414  82.1% +3.8%   139  82.0% +3.2%   156  81.4% +3.6%   81.9%
#
# 414 confirmed trades, 363 right, against a break-even of 82.0%: one-sided
# p = 0.0012. The win rate is 87.6 / 87.7 / 87.9 across three chronological
# periods -- about as stable as anything measured here.
#
# It is not free. Confirmation throws away roughly a third of the setups, so
# there are about 6 or 7 a day instead of 20.
#
# Checked at other entry times too (12/14, 8/10, 6/8): confirmation raised the
# win rate in 11 of the 12 period-cells. Entry at 10 confirmed at 12 is the
# strongest and the only one positive in all three periods, so that is the one
# wired in. The gap is measured at 2 minutes; 1.5 is allowed here because
# --wait polls every 30 seconds and will not land exactly on the minute.
CONFIRM_GAP_MIN = 1.5

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

# Calibration measured over 63 days: what the formula says, versus what really
# happened. The formula is systematically under-confident; this corrects it.
CAL_X = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
         0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
CAL_Y = [0.001, 0.050, 0.080, 0.141, 0.198, 0.266, 0.299, 0.344, 0.441,
         0.506, 0.576, 0.635, 0.682, 0.763, 0.835, 0.856, 0.898, 0.934,
         0.957, 0.987, 0.998]

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
MEMORY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "forward_test", "check_memory.json")
N_BINS = 20
PRIOR_STRENGTH = 30.0


def bin_of(p):
    return min(int(p * N_BINS), N_BINS - 1)


def prior_for(b):
    """The 63-day calibration, read at the centre of bin b."""
    centre = (b + 0.5) / N_BINS
    lo = CAL_Y[0]
    for i in range(1, len(CAL_X)):
        if centre <= CAL_X[i]:
            x0, x1, y0, y1 = CAL_X[i - 1], CAL_X[i], CAL_Y[i - 1], CAL_Y[i]
            lo = y0 + (y1 - y0) * (centre - x0) / (x1 - x0)
            break
    else:
        lo = CAL_Y[-1]
    return lo


def load_memory():
    blank = {"predictions": [], "bins_n": [0.0] * N_BINS,
             "bins_wins": [0.0] * N_BINS, "polls": {}}
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
    confirmed = any(q["qual"] and q["side"] == side
                    and q["mins"] >= mins + CONFIRM_GAP_MIN for q in seen)
    seen.append({"mins": round(mins, 2), "side": side, "qual": bool(qualified)})
    polls[ticker] = seen[-40:]
    # Contracts live 15 minutes; anything not touched in this run and already
    # holding a full history is finished. Keep the file from growing forever.
    if len(polls) > 200:
        for k in list(polls)[:-100]:
            if k != ticker:
                del polls[k]
    return confirmed


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
    if checked and not quiet:
        bits = ["learned from %d settled contract%s" % (checked, "" if checked == 1 else "s")]
        if right or wrong:
            bits.append("%d of my calls right, %d wrong" % (right, wrong))
        print("  (%s)" % "; ".join(bits))
    return checked


def show_record(mem):
    answered = [r for r in mem["predictions"]
                if r.get("answered") and r.get("correct") is not None]
    print()
    line("=")
    print("  TRACK RECORD")
    line("=")
    if not answered:
        seen = sum(mem["bins_n"])
        calls = sum(1 for r in mem["predictions"] if r.get("answered"))
        pend = sum(1 for r in mem["predictions"]
                   if r.get("answered") and r.get("outcome") is None)
        print("  contracts watched   %d" % len(mem["predictions"]))
        print("  learned from        %d settled" % int(seen))
        print("  actual calls made   %d%s"
              % (calls, "  (%d still open)" % pend if pend else ""))
        print()
        if not calls:
            print("  It has been learning from contracts it DECLINED. Those")
            print("  still teach it how often the formula is right, which is")
            print("  most of what there is to learn -- but they are not calls,")
            print("  so there is no win/loss record yet.")
            print()
            print("  A call means it graded a setup GOOD and said YES or NO.")
            print("  A setup now has to appear twice, two minutes apart, so")
            print("  roughly 1 run in 75 gets there on its own. Use:")
            print("      python3 check.py --wait")
        else:
            print("  %d call%s made, none settled yet. Each takes ~15 minutes."
                  % (calls, "" if calls == 1 else "s"))
        print()
        return
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
                        "there two minutes later hit 87.7%; ones that were not",
                        "hit 81.9%. Re-run in 2 minutes -- if it still says",
                        "the same thing, it upgrades to GOOD."],
                "stats": (708, 81.9, "+3.8% / +3.3% / +3.6%")}
    return {"label": "GOOD -- confirmed, the zone that held up",
            "short": "GOOD", "trade": True,
            "why": ["%.0fc entry, %.0f minutes left, %.0f-point edge, and the"
                    % (100 * price, mins, 100 * edge),
                    "same call was already standing two minutes ago.",
                    "The only combination positive in all three periods."],
            "stats": (414, 87.7, "+6.5% / +7.0% / +8.4%")}


def evaluate(mem, a):
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

    # ---- the readout -------------------------------------------------
    print()
    line("=")
    print("  %s" % m.get("ticker"))
    line("=")
    print("  BTC now      $%s   (%s)" % (format(round(spot, 2), ",.2f"), spot_src))
    print("  Target       $%s" % format(round(strike, 2), ",.2f"))
    print("  Difference   %s$%s" % ("+" if spot >= strike else "-",
                                    format(abs(round(spot - strike, 2)), ",.2f")))
    print("  Time left    %.1f minutes" % mins)
    print("  Kalshi       YES %.0fc  /  NO %.0fc" % (100 * ya, 100 * no_ask))

    if a.why:
        r = rsi(closes)
        e9, e21 = ema(closes, 9), ema(closes, 21)
        print()
        print("  volatility   %.4f%% per minute" % (100 * v))
        print("  raw model    %.1f%%   ->  calibrated %.1f%%" % (100 * raw, 100 * p))
        if r is not None:
            print("  RSI(14)      %.1f" % r)
        if e9 and e21:
            print("  EMA 9 v 21   %s" % ("above" if e9 > e21 else "below"))
        print("  spread       %.0fc" % (100 * spread))

    def remember(answered):
        prev = next((r for r in mem["predictions"]
                     if r["ticker"] == m.get("ticker")), None)
        if prev is not None:
            # --wait looks at the same contract many times. The first look is
            # what teaches calibration, so leave it -- but if a later look is
            # the one that became an actual call, the record has to say so,
            # otherwise confirmed trades never show up in the track record.
            if answered and not prev.get("answered"):
                prev.update({"answered": True, "side": side, "price": price,
                             "edge": edge})
                save_memory(mem)
            return
        mem["predictions"].append({
            "asked": datetime.now(timezone.utc).isoformat(),
            "ticker": m.get("ticker"), "close_time": m.get("close_time"),
            "raw": raw, "p": p, "side": side, "price": price,
            "edge": edge, "answered": bool(answered), "outcome": None})
        mem["predictions"] = mem["predictions"][-2000:]
        save_memory(mem)

    # ---- grade it ------------------------------------------------------
    # "Qualifying" here is everything grade_of asks for EXCEPT confirmation,
    # so a look that qualifies on its own merits is what a later look gets to
    # confirm against. Confirmation confirming itself would be worthless.
    qualifies = (mins >= MIN_MINUTES_LEFT and MIN_PRICE <= price <= MAX_PRICE
                 and edge >= MIN_EDGE and spread <= MAX_SPREAD)
    confirmed = note_poll(mem, m.get("ticker"), mins, side, qualifies)
    g = grade_of(price, edge, mins, spread, confirmed)
    remember(g["trade"])
    save_memory(mem)          # note_poll changed the memory either way
    if WAITING and not g["trade"]:
        # --wait holds out for a GOOD grade. Everything else is reported as a
        # reason and the loop carries on.
        raise NoSetup("%s  (%s at %.0fc, %.0f min)"
                      % (g["short"], side, 100 * price, mins))

    answer(side)
    print()
    print("  Buy %s at %.0f cents" % (side, 100 * price))
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
    a = ap.parse_args()

    mem = load_memory()

    if a.record:
        settle_pending(mem, quiet=True)
        save_memory(mem)
        show_record(mem)
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

    evaluate(mem, a)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
