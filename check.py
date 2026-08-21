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

Any of those and it says CAN'T SAY. Expect that most of the time. Silence is
the honest answer far more often than YES or NO.

HOW ACCURATE IS IT WHEN IT DOES ANSWER
======================================
On 63 days of history, setups passing all these filters won 84.9% of the time
against an 80.4% break-even, across 1,250 independent contracts (p<0.0001).
A ~4.5 point edge, positive in all three test periods.

That is the strongest result in this project, and it still is not proof. It
has never been tested on live money, and the high win rate is mostly just the
price -- an 80c contract wins 80% of the time by definition. Every answer
prints the caveat.

No account, no API key, no orders, no money. Standard library only.
"""

import argparse
import json
import math
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SERIES = "KXBTC15M"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
COINBASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

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

# Calibration measured over 63 days: what the formula says, versus what really
# happened. The formula is systematically under-confident; this corrects it.
CAL_X = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
         0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
CAL_Y = [0.001, 0.050, 0.080, 0.141, 0.198, 0.266, 0.299, 0.344, 0.441,
         0.506, 0.576, 0.635, 0.682, 0.763, 0.835, 0.856, 0.898, 0.934,
         0.957, 0.987, 0.998]

W = 64


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


def cant(reason, detail=""):
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
    print("  This is the normal outcome. Kalshi is usually priced correctly,")
    print("  and most of the time there is genuinely nothing to say.")
    print()
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--why", action="store_true",
                    help="show every number behind the answer")
    a = ap.parse_args()

    print()
    print("  Checking the BTC 15-minute contract...")

    got, err = live()
    if err:
        cant("Cannot reach the market.", err[:70])
    m, mins = got

    closes, vols, err = bars()
    if err:
        cant("Cannot get a reliable BTC price.", err[:70])

    strike = m.get("floor_strike")
    yb, ya = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
    if strike is None or yb is None or ya is None:
        cant("Kalshi is not quoting this contract right now.")
    strike, yb, ya = float(strike), float(yb), float(ya)

    spot = closes[-1]
    v = max(vol_per_min(closes) or MIN_VOL, MIN_VOL)
    raw = norm_cdf(math.log(spot / strike) / (v * math.sqrt(max(mins, 0.05))))
    p = calibrate(raw)

    no_ask = 1.0 - yb
    ey, en = p - ya, (1.0 - p) - no_ask
    side = "YES" if ey >= en else "NO"
    edge = max(ey, en)
    price = ya if side == "YES" else no_ask
    conf = p if side == "YES" else 1.0 - p
    spread = ya - yb

    # ---- the readout -------------------------------------------------
    print()
    line("=")
    print("  %s" % m.get("ticker"))
    line("=")
    print("  BTC now      $%s" % format(round(spot, 2), ",.2f"))
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

    # ---- the gates ---------------------------------------------------
    if mins < MIN_MINUTES_LEFT:
        cant("Too late in the contract -- only %.1f minutes left." % mins,
             "Entries under 10 minutes lost 8%% across 63 days. Wait for the "
             "next one.")

    if spread > MAX_SPREAD:
        cant("The spread is %.0f cents." % (100 * spread),
             "Too wide -- the cost of getting in eats the edge.")

    if edge < MIN_EDGE:
        cant("Kalshi's price already matches my estimate.",
             "I say %.0f%%, the market says %.0f%%. Difference of %.0f points "
             "is not enough to trade." % (100 * conf, 100 * price, 100 * edge))

    if price < MIN_PRICE:
        cant("The entry price would be %.0f cents." % (100 * price),
             "Only 70-90c held up across all three test periods. Below that, "
             "including the coin-flip zone near 50c, the edge vanished -- the "
             "market has already priced it.")

    if price > MAX_PRICE:
        cant("The price is already %.0f cents." % (100 * price),
             "You would risk %.0fc to win %.0fc -- one loss undoes %d wins. "
             "Not worth the shape." % (100 * price, 100 * (1 - price),
                                       int(price / max(1 - price, 0.01))))

    # ---- an actual answer --------------------------------------------
    answer(side)
    print()
    print("  Buy %s at %.0f cents" % (side, 100 * price))
    shown = min(conf, 0.99)
    print("  I think it is %s%.0f%% -- Kalshi says %.0f%%  (edge +%.0f points)"
          % (">" if conf > 0.99 else "", 100 * shown, 100 * price, 100 * edge))
    print()
    if spot >= strike:
        print("  BTC is $%s ABOVE target with %.0f minutes to go."
              % (format(abs(round(spot - strike, 2)), ",.2f"), mins))
    else:
        print("  BTC is $%s BELOW target with %.0f minutes to go."
              % (format(abs(round(spot - strike, 2)), ",.2f"), mins))
    print()
    line()
    print("  HOW MUCH TO TRUST THIS")
    line()
    print("  Over 63 days, setups passing every filter above won 84.9% of")
    print("  the time against an 80.4% break-even -- 1,250 contracts,")
    print("  p < 0.0001, positive in all three test periods.")
    print()
    print("  Read that win rate carefully: an 80c contract wins ~80% of the")
    print("  time by definition. The edge is the 4.5 point gap, not the 85%.")
    print()
    print("  Never tested with live money. Treat it as a leaning, not a")
    print("  certainty, and size small.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
