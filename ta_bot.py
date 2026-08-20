#!/usr/bin/env python3
"""
ta_bot.py -- live technical analysis on BTC for the current 15-minute contract.

    python3 ta_bot.py              # continuous live readout + alerts
    python3 ta_bot.py --once       # print one reading and exit
    python3 ta_bot.py --quiet      # no notifications, just the screen

WHAT IT DOES
============
Every 20 seconds it pulls live BTC 1-minute bars, computes a full technical
picture -- RSI, EMA 9/21/50, MACD, momentum over 1/3/5/10 minutes, VWAP,
relative volume, realized volatility -- and turns that into a probability that
the CURRENT Kalshi 15-minute contract settles YES. It then compares that
probability to the live market price and shows you the difference.

Everything is computed from live data at the moment you see it. Nothing is
looked up from a backtest.

HOW THE PROBABILITY IS BUILT
============================
Two parts, deliberately separated so you can see which is doing the work:

  1. BASE -- distance from strike, time remaining, and current volatility.
     Over a 15-minute window this is most of the answer. If BTC is $40 above
     the strike with 2 minutes left, no oscillator changes that much.

  2. TECHNICAL TILT -- the indicators vote bullish or bearish, and the base
     probability is nudged by at most TECH_MAX_TILT.

The screen prints both, so you can always see how much of the call came from
physics and how much from the indicators.

HONEST NOTE
===========
On 63 days of real history, technical indicators did NOT beat the market's own
price as a forecast (Brier 0.1488 for the full technical feature set versus
0.1388 for the market). That is measured, not assumed. This bot shows you the
technical picture in real time because that is genuinely useful to watch and
to learn from -- but the indicators have not earned the right to be traded on
blind. Alerts carry a NOT VALIDATED banner for that reason.

Standard library only. No account, no API key, no installs. Places no orders.
"""

import argparse
import csv
import json
import math
import os
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
SERIES = "KXBTC15M"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
COINBASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

POLL_SECONDS = 20
BARS_NEEDED = 120          # enough history for EMA50 + MACD to settle

MIN_EDGE = 0.05
CONFIRM_POLLS = 3
ONE_ALERT_PER_CONTRACT = True
MIN_PRICE, MAX_PRICE = 0.05, 0.95
MAX_SPREAD = 0.05

# How far the indicators may move the base probability, in probability points.
# Kept modest on purpose: measured against 63 days of history, technicals did
# not beat the market price, so letting them swing the call by 30 points would
# be asserting something the data does not support.
TECH_MAX_TILT = 0.08

# Floor on the per-minute volatility estimate: the 1st percentile observed
# across 63 days. Prevents a flat stretch of bars from producing a near-zero
# estimate and a fake 0%/100% probability. See analyse().
MIN_VOL = 0.0001

EDGE_VALIDATED = False

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "forward_test")
TA_LOG = os.path.join(LOG_DIR, "ta_readings.csv")

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def get(url, params=None, timeout=20):
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-ta/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8", errors="replace")), None
    except Exception as e:                                    # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


# ---------------------------------------------------------------------------
# Indicators -- pure Python, all causal (value at bar i uses bars <= i)
# ---------------------------------------------------------------------------

def ema(values, span):
    if len(values) < span:
        return None
    k = 2.0 / (span + 1.0)
    e = sum(values[:span]) / span
    for v in values[span:]:
        e = v * k + e * (1 - k)
    return e


def ema_series(values, span):
    if len(values) < span:
        return []
    k = 2.0 / (span + 1.0)
    e = sum(values[:span]) / span
    out = [e]
    for v in values[span:]:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for a, b in zip(closes[1:period + 1], closes[2:period + 2]) if False else \
            zip(closes[:period], closes[1:period + 1]):
        d = b - a
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    ag, al = gains / period, losses / period
    for a, b in zip(closes[period:-1], closes[period + 1:]):
        d = b - a
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return 100.0 - (100.0 / (1.0 + rs))


def macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return None, None, None
    f, s = ema_series(closes, fast), ema_series(closes, slow)
    n = min(len(f), len(s))
    line = [a - b for a, b in zip(f[-n:], s[-n:])]
    sig = ema_series(line, signal)
    if not sig:
        return None, None, None
    return line[-1], sig[-1], line[-1] - sig[-1]


def realized_vol(closes, lookback=5):
    if len(closes) < lookback + 2:
        return None
    seg = closes[-(lookback + 1):]
    rets = [math.log(b / a) for a, b in zip(seg, seg[1:]) if a > 0]
    if len(rets) < 2:
        return None
    m = sum(rets) / len(rets)
    var = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) or None


def pct_change(closes, n):
    if len(closes) < n + 1 or closes[-(n + 1)] == 0:
        return None
    return closes[-1] / closes[-(n + 1)] - 1.0


def vwap(closes, volumes, window=20):
    if len(closes) < window:
        return None
    c, v = closes[-window:], volumes[-window:]
    tot = sum(v)
    return sum(a * b for a, b in zip(c, v)) / tot if tot else None


def rel_volume(volumes, window=20):
    if len(volumes) < window:
        return None
    avg = sum(volumes[-window:]) / window
    return volumes[-1] / avg if avg else None


# ---------------------------------------------------------------------------
# Calibration table
# ---------------------------------------------------------------------------
# The raw formula ranks well but is systematically UNDER-confident. Measured
# across 63 days, and stable in all three time periods independently:
#
#     model says   actually happens     train / valid / test
#       0.0-0.2         ~7%              6.3%   5.9%   8.8%
#       0.2-0.4         ~32%            32.3%  30.0%  32.7%
#       0.4-0.6         ~56%            56.0%  53.8%  58.0%
#       0.6-0.8         ~80%            80.4%  80.4%  79.3%
#       0.8-1.0         ~96%            97.1%  96.6%  95.8%
#
# The 0.6-0.8 row is the clearest: the model says 70, reality is 80. This is
# not a directional bet sneaking in -- the overall YES rate is 49.7 / 48.6 /
# 51.0 per period, essentially even. The formula is simply too timid.
#
# Fitted with isotonic regression on train+validation; the test split was not
# used to build it. Applying it improves the test Brier from 0.1481 to 0.1451.
CAL_X = [0.0000, 0.0250, 0.0500, 0.0750, 0.1000, 0.1250, 0.1500, 0.1750,
         0.2000, 0.2250, 0.2500, 0.2750, 0.3000, 0.3250, 0.3500, 0.3750,
         0.4000, 0.4250, 0.4500, 0.4750, 0.5000, 0.5250, 0.5500, 0.5750,
         0.6000, 0.6250, 0.6500, 0.6750, 0.7000, 0.7250, 0.7500, 0.7750,
         0.8000, 0.8250, 0.8500, 0.8750, 0.9000, 0.9250, 0.9500, 0.9750,
         1.0000]
CAL_Y = [0.0011, 0.0365, 0.0495, 0.0627, 0.0795, 0.1092, 0.1406, 0.1757,
         0.1977, 0.2338, 0.2663, 0.2950, 0.2991, 0.3439, 0.3439, 0.3800,
         0.4412, 0.4412, 0.5057, 0.5057, 0.5761, 0.5836, 0.6354, 0.6555,
         0.6815, 0.7307, 0.7631, 0.7826, 0.8345, 0.8433, 0.8557, 0.8933,
         0.8980, 0.9106, 0.9340, 0.9441, 0.9567, 0.9712, 0.9872, 0.9872,
         0.9984]


def calibrate(p):
    """Map a raw model probability onto what actually happened historically."""
    if p <= CAL_X[0]:
        return CAL_Y[0]
    if p >= CAL_X[-1]:
        return CAL_Y[-1]
    for i in range(1, len(CAL_X)):
        if p <= CAL_X[i]:
            x0, x1 = CAL_X[i - 1], CAL_X[i]
            y0, y1 = CAL_Y[i - 1], CAL_Y[i]
            return y0 + (y1 - y0) * (p - x0) / (x1 - x0)
    return CAL_Y[-1]


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

def fetch_bars(n=BARS_NEEDED):
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=n + 5)
    data, err = get(COINBASE, {"granularity": 60,
                               "start": start.isoformat(),
                               "end": end.isoformat()})
    if err or not isinstance(data, list) or not data:
        return None, None, err or "no data"
    rows = sorted(data, key=lambda x: x[0])
    # Coinbase labels a bucket at its START, so the close of bucket T is the
    # price at T+60s. The last bucket may still be forming; drop it so every
    # bar we use is complete.
    if len(rows) > 1:
        rows = rows[:-1]
    closes = [float(r[4]) for r in rows]
    vols = [float(r[5]) for r in rows]
    return closes, vols, None


def current_contract():
    data, err = get(KALSHI + "/markets",
                    {"series_ticker": SERIES, "status": "open", "limit": 50})
    if err or not data:
        return None, err
    now = datetime.now(timezone.utc)
    best = None
    for m in data.get("markets") or []:
        ct = m.get("close_time")
        if not ct:
            continue
        close_dt = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
        mins = (close_dt - now).total_seconds() / 60.0
        if 0.2 <= mins <= 15.5 and (best is None or mins < best[1]):
            best = (m, mins)
    return best, None


# ---------------------------------------------------------------------------
# The read
# ---------------------------------------------------------------------------

def analyse(closes, vols, strike, minutes_left):
    """Return (base_p, tech_p, signals, stats)."""
    spot = closes[-1]
    # Volatility over 15 minutes, not 5.
    #
    # Measured on 63 days: a 5-minute estimate badly understates what happens
    # next when the market is quiet. In the calmest fifth of readings, BTC
    # actually moved 1.98x further than a 5-minute estimate predicted. That
    # made the model wildly overconfident in exactly those moments -- it would
    # print "98% NO" while the market said 67%, and the market was right.
    #
    # Tested alternatives on validation: 15-minute realised (0.1312) beat
    # 5-minute (0.1326), and beat every blend with a long-run average, which
    # made things worse. So recent volatility IS informative; the 5-minute
    # window was simply too short a sample.
    #
    # This narrows the gap to the market (test Brier 0.1537 -> 0.1496) but does
    # not close it: the market still scores 0.1388.
    vol = realized_vol(closes, 15) or realized_vol(closes, 10) or realized_vol(closes, 5)

    # Safety floor, not a performance tweak. A dead-flat stretch of bars can
    # drive the estimate to ~0, and the probability then divides by it and
    # snaps to 0% or 100% -- certainty manufactured out of a rounding error.
    # The floor is the 1st percentile of observed 15-minute volatility across
    # 63 days. On validation it costs 0.0001 of Brier (0.1312 -> 0.1313),
    # which is worth paying to never print a fake certainty.
    if vol is None or vol < MIN_VOL:
        vol = MIN_VOL

    # ---- part 1: the physics ------------------------------------------
    if vol and minutes_left > 0 and strike > 0:
        z = math.log(spot / strike) / (vol * math.sqrt(minutes_left))
        raw = norm_cdf(z)
    else:
        raw = 1.0 if spot >= strike else 0.0
    base = calibrate(raw)

    # ---- part 2: the indicators ---------------------------------------
    r = rsi(closes, 14)
    e9, e21, e50 = ema(closes, 9), ema(closes, 21), ema(closes, 50)
    ml, ms, mh = macd(closes)
    r1, r3, r5, r10 = (pct_change(closes, n) for n in (1, 3, 5, 10))
    vw = vwap(closes, vols, 20)
    rv = rel_volume(vols, 20)

    signals = []

    def sig(name, value, bull, display):
        signals.append({"name": name, "value": value, "bull": bull,
                        "display": display})

    if r is not None:
        sig("RSI(14)", r, 1 if r > 55 else (-1 if r < 45 else 0), "%.1f" % r)
    if e9 and e21:
        sig("EMA 9 vs 21", e9 - e21, 1 if e9 > e21 else -1,
            "%s" % ("9 above 21" if e9 > e21 else "9 below 21"))
    if e50:
        sig("Price vs EMA50", spot - e50, 1 if spot > e50 else -1,
            "%+.0f" % (spot - e50))
    if ml is not None:
        # Vote on the MACD LINE (fast EMA minus slow EMA), not the histogram.
        # On a smooth trend the signal line converges toward the MACD line, so
        # the histogram decays through zero and flips sign while the trend is
        # still intact -- verified: a steadily falling series prints a POSITIVE
        # histogram. The line keeps the correct sign in both directions.
        sig("MACD", ml, 1 if ml > 0 else -1,
            "%+.2f (%s)" % (ml, "above zero" if ml > 0 else "below zero"))
    if r5 is not None:
        sig("5-min momentum", r5, 1 if r5 > 0.0002 else (-1 if r5 < -0.0002 else 0),
            "%+.3f%%" % (100 * r5))
    if r10 is not None:
        sig("10-min momentum", r10, 1 if r10 > 0.0003 else (-1 if r10 < -0.0003 else 0),
            "%+.3f%%" % (100 * r10))
    if vw:
        sig("Price vs VWAP", spot - vw, 1 if spot > vw else -1,
            "%+.0f" % (spot - vw))

    votes = [s["bull"] for s in signals if s["bull"] != 0]
    score = sum(votes) / len(votes) if votes else 0.0     # -1 .. +1
    tech = min(max(base + TECH_MAX_TILT * score, 0.001), 0.999)

    stats = {"spot": spot, "vol": vol, "rsi": r, "ema9": e9, "ema21": e21,
             "ema50": e50, "macd": ml, "macd_sig": ms, "macd_hist": mh,
             "ret_1m": r1, "ret_5m": r5, "ret_10m": r10, "vwap": vw,
             "rel_volume": rv, "score": score,
             "bull": sum(1 for v in votes if v > 0),
             "bear": sum(1 for v in votes if v < 0)}
    return base, tech, signals, stats


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

BAR = "-" * 72


def render(m, mins, base, tech, signals, st):
    strike = float(m.get("floor_strike"))
    yb, ya = float(m.get("yes_bid_dollars")), float(m.get("yes_ask_dollars"))
    no_ask = 1.0 - yb
    edge_yes, edge_no = tech - ya, (1.0 - tech) - no_ask
    side = "YES" if edge_yes >= edge_no else "NO"
    edge = max(edge_yes, edge_no)

    print("\n" + BAR)
    print("  %s        %.1f min left" % (m.get("ticker"), mins))
    print(BAR)
    print("  BTC $%,.2f          strike $%,.2f          diff %+.2f"
          .replace(",", "") % (st["spot"], strike, st["spot"] - strike))
    print("  volatility %.4f%%/min" % (100 * (st["vol"] or 0)))
    print()
    print("  INDICATORS")
    for s in signals:
        mark = "BULL" if s["bull"] > 0 else ("BEAR" if s["bull"] < 0 else " -- ")
        print("    %-18s %-16s %s" % (s["name"], s["display"], mark))
    if st["rel_volume"]:
        print("    %-18s %-16s" % ("Relative volume", "%.2fx" % st["rel_volume"]))
    print()
    print("  Vote: %d bullish / %d bearish   ->  tilt %+.1f points"
          % (st["bull"], st["bear"], 100 * TECH_MAX_TILT * st["score"]))
    print()
    print("  PROBABILITY")
    print("    from distance+time+vol   %5.1f%%  (calibrated)" % (100 * base))
    print("    after technical tilt     %5.1f%%" % (100 * tech))
    print()
    print("  MARKET")
    print("    YES  bid %.2f / ask %.2f      NO ask %.2f" % (yb, ya, no_ask))
    print()
    if edge >= MIN_EDGE:
        print("  >> %s looks %+.1f points cheap" % (side, 100 * edge))
    else:
        print("  >> no edge (best %s %+.1f pts, need %+.0f)"
              % (side, 100 * edge, 100 * MIN_EDGE))
    print(BAR)
    return side, edge, ya, no_ask, yb


def send_ntfy(title, body):
    if not NTFY_TOPIC:
        return
    try:
        req = urllib.request.Request(
            "%s/%s" % (NTFY_SERVER.rstrip("/"), NTFY_TOPIC),
            data=body.encode("utf-8"), method="POST",
            headers={"Title": title.encode("ascii", "replace").decode("ascii"),
                     "Tags": "chart_with_upwards_trend"})
        urllib.request.urlopen(req, timeout=10,
                               context=ssl.create_default_context())
    except Exception:                                         # noqa: BLE001
        pass


def notify(title, message):
    banner = message if EDGE_VALIDATED else ("[NOT VALIDATED] " + message)
    print("\n  *** %s -- %s\n" % (title, banner), flush=True)
    send_ntfy(title, banner)
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e",
                            'display notification %s with title %s sound name "Submarine"'
                            % (json.dumps(banner), json.dumps(title))],
                           check=False, capture_output=True, timeout=5)
        except Exception:                                     # noqa: BLE001
            pass


FIELDS = ["observed_at", "ticker", "minutes_remaining", "strike", "btc_price",
          "vol", "rsi", "ema9", "ema21", "ema50", "macd_hist", "ret_1m",
          "ret_5m", "ret_10m", "vwap", "rel_volume", "bull_votes",
          "bear_votes", "base_p", "tech_p", "yes_bid", "yes_ask", "no_ask",
          "best_side", "best_edge", "alerted"]


def one_pass(writer, state, quiet):
    closes, vols, err = fetch_bars()
    if err or not closes or len(closes) < 60:
        print("  waiting for BTC data (%s)" % (err or "too few bars"), flush=True)
        return
    got, err = current_contract()
    if err or not got:
        print("  no live contract in window (%s)" % (err or "none open"), flush=True)
        return
    m, mins = got
    strike = m.get("floor_strike")
    yb, ya = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
    if strike is None or yb is None or ya is None:
        print("  contract missing quotes", flush=True)
        return
    strike, yb, ya = float(strike), float(yb), float(ya)

    base, tech, signals, st = analyse(closes, vols, strike, mins)
    side, edge, ya_, no_ask, yb_ = render(m, mins, base, tech, signals, st)

    tkr = m.get("ticker")
    spread = ya - yb
    mid = (ya + yb) / 2.0
    ok = (edge >= MIN_EDGE and spread <= MAX_SPREAD
          and MIN_PRICE <= mid <= MAX_PRICE)

    sk = state["streak"]
    if ok:
        if sk.get("ticker") == tkr and sk.get("side") == side:
            sk["n"] += 1
        else:
            state["streak"] = sk = {"ticker": tkr, "side": side, "n": 1}
    else:
        state["streak"] = sk = {}

    fire = (sk.get("n", 0) >= CONFIRM_POLLS
            and not (ONE_ALERT_PER_CONTRACT and tkr in state["alerted"])
            and not quiet)
    if sk.get("n", 0) and sk["n"] < CONFIRM_POLLS:
        print("     confirming %d/%d" % (sk["n"], CONFIRM_POLLS))
    if fire:
        state["alerted"].add(tkr)
        notify("%s %s  %+.0f pts" % (tkr, side, 100 * edge),
               "RSI %.0f, %d bull / %d bear | model %.0f%% vs price %.0f%% | "
               "%.0f min | BTC $%.0f vs $%.0f"
               % (st["rsi"] or 0, st["bull"], st["bear"],
                  100 * (tech if side == "YES" else 1 - tech),
                  100 * (ya if side == "YES" else no_ask),
                  mins, st["spot"], strike))

    writer.writerow({
        "observed_at": datetime.now(timezone.utc).isoformat(), "ticker": tkr,
        "minutes_remaining": round(mins, 2), "strike": strike,
        "btc_price": st["spot"], "vol": st["vol"], "rsi": st["rsi"],
        "ema9": st["ema9"], "ema21": st["ema21"], "ema50": st["ema50"],
        "macd_hist": st["macd_hist"], "ret_1m": st["ret_1m"],
        "ret_5m": st["ret_5m"], "ret_10m": st["ret_10m"], "vwap": st["vwap"],
        "rel_volume": st["rel_volume"], "bull_votes": st["bull"],
        "bear_votes": st["bear"], "base_p": round(base, 6),
        "tech_p": round(tech, 6), "yes_bid": yb, "yes_ask": ya,
        "no_ask": no_ask, "best_side": side, "best_edge": round(edge, 6),
        "alerted": int(fire)})


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="one reading, then exit")
    ap.add_argument("--quiet", action="store_true", help="no notifications")
    a = ap.parse_args()

    os.makedirs(LOG_DIR, exist_ok=True)
    new = not os.path.exists(TA_LOG)
    fh = open(TA_LOG, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
    if new:
        writer.writeheader()

    print("=" * 72)
    print("  Live technical analysis -- BTC 15-minute Kalshi contracts")
    print("=" * 72)
    print("  RSI, EMA 9/21/50, MACD, momentum, VWAP, volume -- computed live")
    print("  Alerts: %d%% edge held for %d polls, one per contract"
          % (100 * MIN_EDGE, CONFIRM_POLLS))
    print("  Phone:  %s" % ("ntfy '%s'" % NTFY_TOPIC if NTFY_TOPIC else "off"))
    if not EDGE_VALIDATED:
        print()
        print("  Measured on 63 days: technical indicators did NOT beat the")
        print("  market price as a forecast (Brier 0.1488 vs 0.1388). Shown")
        print("  live because it is worth watching, not because it is proven.")
    print()

    state = {"streak": {}, "alerted": set()}
    try:
        while True:
            one_pass(writer, state, a.quiet)
            fh.flush()
            if a.once:
                break
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\n  Stopped. Readings logged to %s" % TA_LOG)
    finally:
        fh.close()


if __name__ == "__main__":
    main()
