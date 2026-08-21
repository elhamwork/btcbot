#!/usr/bin/env python3
"""
learner.py -- self-correcting paper trader for Kalshi BTC 15-minute contracts.

    python3 learner.py              # run continuously
    python3 learner.py --report     # show what it has learned so far
    python3 learner.py --reset      # wipe memory and start over

WHAT IT DOES
============
Every 15-minute contract, it decides, records a PAPER position, and waits.
When the contract settles it fetches the real outcome, scores its own
prediction, and updates its calibration from what happened. Right or wrong,
each settled contract makes the next prediction slightly better informed.

It starts from the calibration measured over 63 days of history rather than
from nothing, then moves as live evidence accumulates.

WHAT "LEARNING" HONESTLY MEANS HERE
===================================
It learns CALIBRATION: the mapping from "the formula says 70%" to "70% means
80% in reality". That is a real and useful thing to learn, and it is what the
63-day study showed was broken.

It does NOT learn to see the future. If Kalshi's price is already a better
forecast than the formula -- which it was, 0.1388 against 0.1449 -- then no
amount of self-correction turns the formula into a money machine. Learning
fixes a biased ruler. It does not make the ruler longer.

The honest test is built in: every report compares the bot's Brier score
against the market's on the SAME settled contracts. If the bot is genuinely
learning something the market does not know, that gap closes. Watch that
number, not the win rate.

SAFETY
======
Paper only. No account, no API key, no orders, no money. Standard library.
Survives restarts -- state is written to disk after every change.
"""

import argparse
import json
import math
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SERIES = "KXBTC15M"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
COINBASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

POLL_SECONDS = 30
BARS_NEEDED = 60

# Entry rules, measured over 63 days (see results/reports/).
MIN_EDGE = 0.05
MIN_PRICE = 0.50            # favourites only; the cheap side lost 13%
MAX_PRICE = 0.95
MIN_MINUTES_LEFT = 10       # last-5-minute entries lost 8%
MAX_SPREAD = 0.05
MIN_VOL = 0.0001

STAKE = 10.0                # paper dollars per trade
FEE_RATE = 0.07

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "forward_test", "learner_state.json")

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")

# Prior calibration from 63 days / 6,000 contracts. 20 bins of width 0.05.
# PRIOR_STRENGTH is how many observations each bin is "worth" at the start:
# live evidence has to accumulate before it can move a bin much. Without this,
# the first few outcomes in a bin would swing it wildly and the bot would
# chase noise -- learning fast and learning wrong.
PRIOR = [0.02, 0.05, 0.08, 0.13, 0.20, 0.26, 0.30, 0.34, 0.42, 0.48,
         0.55, 0.60, 0.65, 0.71, 0.77, 0.81, 0.86, 0.90, 0.95, 0.99]
PRIOR_STRENGTH = 40.0
N_BINS = 20


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def get(url, params=None, timeout=20):
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-learner/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8", errors="replace")), None
    except Exception as e:                                    # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def notify(title, body):
    if NTFY_TOPIC:
        try:
            req = urllib.request.Request(
                "%s/%s" % (NTFY_SERVER.rstrip("/"), NTFY_TOPIC),
                data=body.encode("utf-8"), method="POST",
                headers={"Title": title.encode("ascii", "replace").decode("ascii")})
            urllib.request.urlopen(req, timeout=10,
                                   context=ssl.create_default_context())
        except Exception:                                     # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def blank_state():
    return {
        "bins_wins": [0.0] * N_BINS,      # live wins observed per bin
        "bins_n": [0.0] * N_BINS,         # live observations per bin
        "open": {},                        # ticker -> paper position
        "closed": [],                      # settled trades
        "started": datetime.now(timezone.utc).isoformat(),
        "seen_contracts": [],
    }


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                s = json.load(f)
            for k, v in blank_state().items():
                s.setdefault(k, v)
            return s
        except Exception:                                     # noqa: BLE001
            print("  state file unreadable; starting fresh")
    return blank_state()


def save_state(s):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE_PATH)     # atomic: a crash mid-write cannot corrupt


# ---------------------------------------------------------------------------
# The learned calibration
# ---------------------------------------------------------------------------

def bin_of(p):
    return min(int(p * N_BINS), N_BINS - 1)


def calibrated(state, raw):
    """Blend the 63-day prior with what this bot has seen live."""
    b = bin_of(raw)
    n = state["bins_n"][b]
    w = state["bins_wins"][b]
    p = (PRIOR[b] * PRIOR_STRENGTH + w) / (PRIOR_STRENGTH + n)
    return min(max(p, 0.001), 0.999)


def learn(state, raw, outcome):
    b = bin_of(raw)
    state["bins_n"][b] += 1.0
    state["bins_wins"][b] += 1.0 if outcome else 0.0


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fetch_bars():
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=BARS_NEEDED + 5)
    data, err = get(COINBASE, {"granularity": 60, "start": start.isoformat(),
                               "end": end.isoformat()})
    if err or not isinstance(data, list) or len(data) < 20:
        return None, err or "too few bars"
    rows = sorted(data, key=lambda x: x[0])[:-1]   # drop the forming bar
    return [float(r[4]) for r in rows], None


def realized_vol(closes, lookback=15):
    if len(closes) < lookback + 2:
        return None
    seg = closes[-(lookback + 1):]
    rets = [math.log(b / a) for a, b in zip(seg, seg[1:]) if a > 0]
    if len(rets) < 2:
        return None
    m = sum(rets) / len(rets)
    return math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1)) or None


def live_contract():
    data, err = get(KALSHI + "/markets",
                    {"series_ticker": SERIES, "status": "open", "limit": 50})
    if err or not data:
        return None
    now = datetime.now(timezone.utc)
    best = None
    for m in data.get("markets") or []:
        ct = m.get("close_time")
        if not ct:
            continue
        cd = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
        mins = (cd - now).total_seconds() / 60.0
        if 0.2 <= mins <= 15.5 and (best is None or mins < best[1]):
            best = (m, mins)
    return best


def settle_result(ticker):
    d, _ = get(KALSHI + "/markets/" + ticker)
    r = ((d or {}).get("market") or {}).get("result")
    return 1 if r == "yes" else (0 if r == "no" else None)


# ---------------------------------------------------------------------------
# Trading loop
# ---------------------------------------------------------------------------

def consider(state):
    got = live_contract()
    if not got:
        return "no live contract"
    m, mins = got
    tkr = m.get("ticker")
    if tkr in state["open"] or tkr in state["seen_contracts"]:
        return None
    if mins < MIN_MINUTES_LEFT:
        return None

    strike = m.get("floor_strike")
    yb, ya = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
    if strike is None or yb is None or ya is None:
        return None
    strike, yb, ya = float(strike), float(yb), float(ya)

    closes, err = fetch_bars()
    if err:
        return "btc: %s" % err
    vol = max(realized_vol(closes) or MIN_VOL, MIN_VOL)
    spot = closes[-1]

    z = math.log(spot / strike) / (vol * math.sqrt(mins))
    raw = min(max(norm_cdf(z), 1e-4), 1 - 1e-4)
    p = calibrated(state, raw)

    no_ask = 1.0 - yb
    ey, en = p - ya, (1.0 - p) - no_ask
    side = "YES" if ey >= en else "NO"
    edge = max(ey, en)
    px = ya if side == "YES" else no_ask

    if edge < MIN_EDGE or not (MIN_PRICE <= px <= MAX_PRICE) or (ya - yb) > MAX_SPREAD:
        state["seen_contracts"].append(tkr)
        state["seen_contracts"] = state["seen_contracts"][-500:]
        return None

    contracts = max(int(STAKE // px), 1)
    fee = math.ceil(FEE_RATE * contracts * px * (1 - px) * 100) / 100.0
    state["open"][tkr] = {
        "opened": datetime.now(timezone.utc).isoformat(),
        "close_time": m.get("close_time"), "side": side, "price": px,
        "contracts": contracts, "cost": contracts * px, "fee": fee,
        "raw": raw, "p": p, "market_mid": (ya + yb) / 2.0,
        "edge": edge, "minutes_left": mins, "spot": spot, "strike": strike,
    }
    state["seen_contracts"].append(tkr)
    return "OPENED %s %s @ %.2f  (model %.0f%% vs market %.0f%%, edge %+.0f pts)" % (
        tkr, side, px, 100 * (p if side == "YES" else 1 - p), 100 * px, 100 * edge)


def settle_due(state):
    msgs = []
    now = datetime.now(timezone.utc)
    for tkr in list(state["open"]):
        pos = state["open"][tkr]
        ct = datetime.fromisoformat(str(pos["close_time"]).replace("Z", "+00:00"))
        if now < ct + timedelta(minutes=2):
            continue
        y = settle_result(tkr)
        if y is None:
            continue
        won = (pos["side"] == "YES" and y == 1) or (pos["side"] == "NO" and y == 0)
        pnl = (pos["contracts"] * 1.0 if won else 0.0) - pos["cost"] - pos["fee"]

        learn(state, pos["raw"], y == 1)

        rec = dict(pos)
        rec.update({"ticker": tkr, "outcome": y, "won": bool(won),
                    "pnl": pnl, "settled": now.isoformat()})
        state["closed"].append(rec)
        del state["open"][tkr]
        msgs.append("SETTLED %s %s -> %s  P&L %+.2f  (learned: bin %d now %d obs)"
                    % (tkr, pos["side"], "WIN" if won else "loss", pnl,
                       bin_of(pos["raw"]), int(state["bins_n"][bin_of(pos["raw"])])))
    return msgs


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def report(state):
    c = state["closed"]
    print("=" * 70)
    print("  LEARNER REPORT")
    print("=" * 70)
    print("  running since   %s" % state["started"][:19])
    print("  open positions  %d" % len(state["open"]))
    print("  settled trades  %d" % len(c))
    if not c:
        print("\n  Nothing settled yet. Each contract takes ~15 minutes.")
        return
    wins = sum(1 for t in c if t["won"])
    pnl = sum(t["pnl"] for t in c)
    stake = sum(t["cost"] + t["fee"] for t in c)
    be = sum(t["price"] for t in c) / len(c)
    print()
    print("  win rate        %.1f%%   (break-even needs %.1f%%)"
          % (100 * wins / len(c), 100 * be))
    print("  paper P&L       $%+.2f on $%.2f staked  (%+.2f%%)"
          % (pnl, stake, 100 * pnl / stake if stake else 0))
    bm = sum((t["p"] - t["outcome"]) ** 2 for t in c) / len(c)
    mk = sum((t["market_mid"] - t["outcome"]) ** 2 for t in c) / len(c)
    print()
    print("  THE TEST THAT MATTERS -- Brier score, lower is better")
    print("    this bot       %.4f" % bm)
    print("    Kalshi price   %.4f" % mk)
    if bm < mk:
        print("    -> the bot is AHEAD by %.4f on live data" % (mk - bm))
    else:
        print("    -> Kalshi is ahead by %.4f; the bot has not caught up" % (bm - mk))
    print()
    print("  WHAT IT HAS LEARNED  (bins with live evidence)")
    print("    %-14s %8s %10s %10s"
          % ("formula says", "live n", "prior", "now"))
    for b in range(N_BINS):
        n = state["bins_n"][b]
        if n < 1:
            continue
        cur = (PRIOR[b] * PRIOR_STRENGTH + state["bins_wins"][b]) / (PRIOR_STRENGTH + n)
        print("    %.2f-%.2f      %8d %10.3f %10.3f%s"
              % (b / N_BINS, (b + 1) / N_BINS, int(n), PRIOR[b], cur,
                 "  (moved)" if abs(cur - PRIOR[b]) > 0.02 else ""))
    print()
    days = max((datetime.now(timezone.utc)
                - datetime.fromisoformat(state["started"])).days, 1)
    print("  %d settled in %d day(s) -- about %.0f/day."
          % (len(c), days, len(c) / days))
    print("  Two weeks at this rate is roughly %d trades, enough to see a"
          % (14 * len(c) / days))
    print("  1-2 point edge if one is there.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()

    if a.reset:
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)
        print("Memory wiped.")
        return
    state = load_state()
    if a.report:
        report(state)
        return

    print("=" * 70)
    print("  Self-correcting paper trader -- Kalshi %s" % SERIES)
    print("=" * 70)
    print("  Paper money only. No account, no orders.")
    print("  Trades every qualifying contract, then learns from the result.")
    print("  Resuming with %d settled trades, %d open."
          % (len(state["closed"]), len(state["open"])))
    print("  Ctrl-C to stop. Progress is saved; just start it again.\n")

    last_report = 0
    while True:
        try:
            for msg in settle_due(state):
                print("  %s" % msg, flush=True)
            msg = consider(state)
            if msg and msg.startswith("OPENED"):
                print("  %s" % msg, flush=True)
            save_state(state)

            if time.time() - last_report > 1800:
                last_report = time.time()
                n = len(state["closed"])
                if n:
                    w = sum(1 for t in state["closed"] if t["won"])
                    pnl = sum(t["pnl"] for t in state["closed"])
                    line = "%d trades | %.0f%% wins | paper P&L $%+.2f" % (
                        n, 100 * w / n, pnl)
                    print("  --- %s ---" % line, flush=True)
                    notify("btcbot learner", line)
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            save_state(state)
            print("\n  Saved. %d settled, %d open. Run --report to see progress."
                  % (len(state["closed"]), len(state["open"])))
            return
        except Exception as e:                                # noqa: BLE001
            print("  error (continuing): %s" % str(e)[:100], flush=True)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
