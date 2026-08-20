#!/usr/bin/env python3
"""
alert_bot.py -- live monitor and FORWARD TEST recorder for Kalshi KXBTC15M.

    python3 alert_bot.py                 # watch, alert, and record
    python3 alert_bot.py --quiet         # record only, no notifications
    python3 alert_bot.py --score         # score past predictions vs outcomes

WHAT THIS IS
============
It watches live BTC 15-minute contracts, estimates a probability, compares it
to the price, and writes every single observation to disk BEFORE the outcome
exists. Later it fetches the settlements and scores itself.

That last part is the point. A backtest can be fooled by look-ahead, by
overfitting, by a subtle bug in how timestamps line up -- this project already
hit exactly that, and a one-minute misalignment turned a real -7.8% into a
fake +28.7%. A forward test cannot be fooled that way, because the prediction
is on disk with a timestamp before the answer is knowable.

WHAT THIS IS NOT
================
It places no orders. There is no Kalshi login, no API key, no money involved.

And it is NOT a signal to trade. Across 105 strategy configurations on 14 days
of real data, exactly as many looked profitable as pure chance predicts (24%
against ~25% expected). No validated edge exists yet. Every alert therefore
carries a NOT VALIDATED banner, and it stays there until forward-test scoring
earns its removal.

Run it for a few weeks. If `--score` shows it genuinely beating the market's
own Brier score on data that did not exist when the model was built, that is
worth something real. If it does not, you have saved yourself the tuition.

Standard library only. No account, no installs.
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
from collections import deque
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
SERIES = "KXBTC15M"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
COINBASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

POLL_SECONDS = 20
MIN_EDGE = 0.05           # alert threshold
ALERT_MINUTES = (14, 12, 10, 8, 6, 5, 4, 3, 2, 1)
MIN_PRICE, MAX_PRICE = 0.05, 0.95
MAX_SPREAD = 0.05

# ---------------------------------------------------------------------------
# One alert per contract, and only for a signal that holds
# ---------------------------------------------------------------------------
# You can only take one position per 15-minute contract, so the bot should
# only ever interrupt you once per contract. It fires at most one alert per
# ticker, for the whole life of that contract.
#
# That raises the question of WHICH moment to fire on. The bot cannot see the
# future, so it cannot wait for "the best" reading -- that would be
# look-ahead. What it can do is refuse to fire on a single flicker.
#
# CONFIRM_POLLS requires the same side to stay above the threshold for that
# many consecutive polls before alerting. At a 20-second poll, 3 means the
# edge has to survive a full minute. This matters because of what we measured:
# an apparent 12% edge turned out to be $13 of price-feed lag between Coinbase
# and Kalshi's index. Lag-driven edges collapse within a poll or two. A real
# mispricing should still be there a minute later.
ONE_ALERT_PER_CONTRACT = True
CONFIRM_POLLS = 3

# No edge has survived out-of-sample testing. Until one does, every alert is
# labelled. Do not flip this by hand -- let --score earn it.
EDGE_VALIDATED = False

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "forward_test")
PRED_LOG = os.path.join(LOG_DIR, "predictions.csv")
SCORE_OUT = os.path.join(LOG_DIR, "forward_test_score.md")

# ---------------------------------------------------------------------------
# Phone alerts via ntfy.sh
# ---------------------------------------------------------------------------
# Put your topic below (or set the NTFY_TOPIC environment variable), install
# the ntfy app, and subscribe to the same topic. No account, no signup.
#
# SECURITY: ntfy.sh topics are PUBLIC. Anyone who guesses or brute-forces the
# name receives your alerts. Use a long random string, not "btc" or your name.
# `python3 alert_bot.py --setup` prints a fresh random one.
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")

# Optional Telegram, if you prefer it. Leave blank to disable.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT", "")

PRED_FIELDS = [
    "observed_at", "ticker", "close_time", "minutes_remaining", "strike",
    "btc_price", "realized_vol_5m", "model_p_yes", "yes_bid", "yes_ask",
    "no_ask", "mid", "spread", "edge_yes", "edge_no", "best_side",
    "best_edge", "alerted", "volume", "open_interest",
]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def get(url, params=None, timeout=20):
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-forwardtest/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8", errors="replace")), None
    except Exception as e:                                    # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


# ---------------------------------------------------------------------------
# Probability model -- the analytic one, deliberately
# ---------------------------------------------------------------------------
# On the 14-day sample this scored Brier 0.1418 against the fitted logistic
# model's 0.1483. The simpler model was the better one, and it needs no
# dependencies and cannot overfit -- it has no parameters to fit. The market
# itself still beat both (0.1353), which is the whole problem.

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def model_probability(spot, strike, minutes_left, vol_per_min):
    """P(BTC >= strike at expiry) under a driftless random walk."""
    if minutes_left <= 0 or vol_per_min <= 0 or spot <= 0 or strike <= 0:
        return 1.0 if spot >= strike else 0.0
    z = math.log(spot / strike) / (vol_per_min * math.sqrt(minutes_left))
    return min(max(norm_cdf(z), 1e-6), 1 - 1e-6)


class PriceTracker:
    """Trailing BTC 1-minute closes, for realized volatility."""

    def __init__(self, window=30):
        self.bars = deque(maxlen=window)
        self.last_fetch = 0.0

    def refresh(self, force=False):
        if not force and time.time() - self.last_fetch < 45:
            return
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=self.bars.maxlen + 2)
        data, err = get(COINBASE, {"granularity": 60,
                                   "start": start.isoformat(),
                                   "end": end.isoformat()})
        self.last_fetch = time.time()
        if err or not isinstance(data, list) or not data:
            return
        # Coinbase buckets are labelled at their START; the close of bucket T
        # is the price at T+60s. Sorting ascending and taking closes gives a
        # trailing series whose last value is the most recent completed minute.
        for c in sorted(data, key=lambda x: x[0]):
            self.bars.append((int(c[0]), float(c[4])))

    @property
    def spot(self):
        return self.bars[-1][1] if self.bars else None

    def vol_per_minute(self, lookback=5):
        if len(self.bars) < lookback + 2:
            return None
        closes = [b[1] for b in self.bars][-(lookback + 1):]
        rets = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0]
        if len(rets) < 2:
            return None
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        return math.sqrt(var) or None


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def _ascii(s):
    """ntfy sends the title as an HTTP header, which must be latin-1 safe."""
    return s.encode("ascii", "replace").decode("ascii")


def send_ntfy(title, body, tags="chart_with_upwards_trend", priority="default"):
    """POST to ntfy.sh. Returns (ok, detail)."""
    if not NTFY_TOPIC:
        return False, "no topic configured"
    url = "%s/%s" % (NTFY_SERVER.rstrip("/"), NTFY_TOPIC)
    req = urllib.request.Request(
        url, data=body.encode("utf-8"), method="POST",
        headers={"Title": _ascii(title), "Tags": tags,
                 "Priority": priority, "Markdown": "no"})
    try:
        with urllib.request.urlopen(
                req, timeout=10, context=ssl.create_default_context()) as r:
            return r.status < 300, "HTTP %s" % r.status
    except Exception as e:                                    # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)


def notify(title, message):
    banner = message if EDGE_VALIDATED else ("[NOT VALIDATED] " + message)
    print("\n  *** %s -- %s\n" % (title, banner), flush=True)

    send_ntfy(title, banner)

    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["osascript", "-e",
                 'display notification %s with title %s sound name "Submarine"'
                 % (json.dumps(banner), json.dumps(title))],
                check=False, capture_output=True, timeout=5)
        except Exception:                                     # noqa: BLE001
            pass

    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        get("https://api.telegram.org/bot%s/sendMessage" % TELEGRAM_TOKEN,
            {"chat_id": TELEGRAM_CHAT, "text": "%s\n%s" % (title, banner)})


def cmd_setup():
    """Print a fresh random topic and the steps to use it."""
    import secrets
    topic = "btcbot-" + secrets.token_urlsafe(12).replace("-", "").replace("_", "")
    print("=" * 68)
    print("  ntfy setup")
    print("=" * 68)
    print()
    print("  1. Install the 'ntfy' app (App Store / Google Play).")
    print()
    print("  2. In the app: tap +, and subscribe to this topic:")
    print()
    print("        %s" % topic)
    print()
    print("  3. Open alert_bot.py, find the line starting NTFY_TOPIC, and")
    print("     put the topic between the quotes:")
    print()
    print('        NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "%s")' % topic)
    print()
    print("  4. Test it:   python3 alert_bot.py --test-alert")
    print()
    print("  Topics on ntfy.sh are PUBLIC -- anyone who knows the name can")
    print("  read your alerts. That is why this one is random. Do not")
    print("  shorten it to something memorable.")
    print()


def cmd_test_alert():
    print("Configured topic: %s" % (NTFY_TOPIC or "(none -- run --setup)"))
    ok, detail = send_ntfy(
        "btcbot test",
        "If this reached your phone, alerts are working.",
        tags="white_check_mark")
    print("  ntfy:      %s (%s)" % ("sent" if ok else "FAILED", detail))
    if sys.platform == "darwin":
        notify_ok = True
        try:
            subprocess.run(["osascript", "-e",
                            'display notification "Alerts are working." '
                            'with title "btcbot test" sound name "Submarine"'],
                           check=False, capture_output=True, timeout=5)
        except Exception as e:                                # noqa: BLE001
            notify_ok = False
            print("  mac alert: FAILED (%s)" % e)
        if notify_ok:
            print("  mac alert: sent (check the top-right of your screen)")
    if not ok and not NTFY_TOPIC:
        print("\n  Run `python3 alert_bot.py --setup` first.")


# ---------------------------------------------------------------------------
# Live loop
# ---------------------------------------------------------------------------

def open_markets():
    out, cursor = [], None
    while True:
        data, err = get(KALSHI + "/markets", {
            "series_ticker": SERIES, "status": "open", "limit": 200,
            "cursor": cursor})
        if err or not data:
            return out, err
        out.extend(data.get("markets") or [])
        cursor = data.get("cursor")
        if not cursor or len(out) > 400:
            return out, None


def _num(m, *keys, default=None):
    for k in keys:
        v = m.get(k)
        if v is not None:
            return float(v)
    return default


def watch(quiet=False):
    os.makedirs(LOG_DIR, exist_ok=True)
    new_file = not os.path.exists(PRED_LOG)
    fh = open(PRED_LOG, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(fh, fieldnames=PRED_FIELDS, extrasaction="ignore")
    if new_file:
        writer.writeheader()
        fh.flush()

    tracker = PriceTracker()
    alerted = set()        # tickers already alerted on -- never twice
    streaks = {}           # ticker -> [side, consecutive_polls, peak_edge]
    seen = 0

    print("=" * 72)
    print("  KXBTC15M live monitor + forward test")
    print("=" * 72)
    print("  Recording every observation to %s" % PRED_LOG)
    print("  Alert threshold: %.0f%% edge, held for %d consecutive polls "
          "(%d sec)" % (100 * MIN_EDGE, CONFIRM_POLLS,
                        CONFIRM_POLLS * POLL_SECONDS))
    print("  Alert limit:     one per contract (one trade per 15 min)")
    print("  Phone alerts:    %s"
          % ("ntfy topic '%s'" % NTFY_TOPIC if NTFY_TOPIC
             else "off  (run --setup to enable)"))
    if not EDGE_VALIDATED:
        print()
        print("  NO VALIDATED EDGE EXISTS. Across 105 configurations on 14 days")
        print("  of real data, 24% looked profitable against ~25% expected by")
        print("  chance. Alerts are labelled accordingly. This is a measuring")
        print("  instrument, not a trading signal.")
    print("  Ctrl-C to stop.\n")

    while True:
        try:
            tracker.refresh()
            spot, vol = tracker.spot, tracker.vol_per_minute()
            if spot is None or vol is None:
                print("  waiting for BTC price data...", flush=True)
                time.sleep(POLL_SECONDS)
                continue

            markets, err = open_markets()
            if err:
                print("  kalshi error: %s" % err[:70], flush=True)
                time.sleep(POLL_SECONDS)
                continue

            now = datetime.now(timezone.utc)
            live = 0
            for m in markets:
                ct = m.get("close_time")
                if not ct:
                    continue
                close_dt = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
                mins = (close_dt - now).total_seconds() / 60.0
                if not (0.5 <= mins <= 15.5):
                    continue

                strike = _num(m, "floor_strike")
                yes_bid = _num(m, "yes_bid_dollars", default=None)
                yes_ask = _num(m, "yes_ask_dollars", default=None)
                if strike is None or yes_bid is None or yes_ask is None:
                    continue
                if not (0 <= yes_bid <= 1 and 0 < yes_ask <= 1):
                    continue

                live += 1
                p_yes = model_probability(spot, strike, mins, vol)
                no_ask = 1.0 - yes_bid
                mid = (yes_bid + yes_ask) / 2.0
                spread = yes_ask - yes_bid
                edge_yes = p_yes - yes_ask
                edge_no = (1.0 - p_yes) - no_ask
                side = "YES" if edge_yes >= edge_no else "NO"
                best = max(edge_yes, edge_no)

                nearest = min(ALERT_MINUTES, key=lambda x: abs(x - mins))
                tradeable = (best >= MIN_EDGE
                             and spread <= MAX_SPREAD
                             and MIN_PRICE <= mid <= MAX_PRICE
                             and abs(mins - nearest) < 0.5)

                tkr = m.get("ticker")

                # --- confirmation streak ---------------------------------
                st = streaks.get(tkr)
                if tradeable:
                    if st and st[0] == side:
                        st[1] += 1
                        st[2] = max(st[2], best)
                    else:
                        streaks[tkr] = [side, 1, best]
                    st = streaks[tkr]
                else:
                    # signal broke -- most likely it was feed lag, not an edge
                    streaks.pop(tkr, None)
                    st = None

                already = ONE_ALERT_PER_CONTRACT and tkr in alerted
                confirmed = st is not None and st[1] >= CONFIRM_POLLS
                fire = confirmed and not already and not quiet

                if st and not confirmed and not already:
                    print("      %s %s edge %.0f%% -- confirming %d/%d"
                          % (tkr, side, 100 * best, st[1], CONFIRM_POLLS),
                          flush=True)

                if fire:
                    alerted.add(tkr)
                    notify("%s %s  edge %.0f%%" % (tkr, side, 100 * best),
                           "model %.0f%% vs price %.0f%%  |  %.0f min left  |  "
                           "BTC $%.0f vs strike $%.0f  |  held %d polls (peak "
                           "%.0f%%)"
                           % (100 * (p_yes if side == "YES" else 1 - p_yes),
                              100 * (yes_ask if side == "YES" else no_ask),
                              mins, spot, strike, st[1], 100 * st[2]))

                writer.writerow({
                    "observed_at": now.isoformat(),
                    "ticker": m.get("ticker"), "close_time": ct,
                    "minutes_remaining": round(mins, 2), "strike": strike,
                    "btc_price": spot, "realized_vol_5m": vol,
                    "model_p_yes": round(p_yes, 6),
                    "yes_bid": yes_bid, "yes_ask": yes_ask, "no_ask": no_ask,
                    "mid": mid, "spread": round(spread, 4),
                    "edge_yes": round(edge_yes, 6), "edge_no": round(edge_no, 6),
                    "best_side": side, "best_edge": round(best, 6),
                    "alerted": int(fire),
                    "volume": _num(m, "volume_fp", "volume", default=0),
                    "open_interest": _num(m, "open_interest_fp",
                                          "open_interest", default=0),
                })
                seen += 1

            fh.flush()
            live_tickers = {m.get("ticker") for m in markets}
            for gone in [t for t in streaks if t not in live_tickers]:
                streaks.pop(gone, None)
            if len(alerted) > 500:
                alerted.clear()

            print("  %s  BTC $%.0f  vol %.5f/min  %d live  "
                  "%d observations  %d alerts sent"
                  % (now.strftime("%H:%M:%S"), spot, vol, live, seen,
                     len(alerted)),
                  flush=True)
            time.sleep(POLL_SECONDS)

        except KeyboardInterrupt:
            fh.close()
            print("\n  Stopped. %d observations in %s" % (seen, PRED_LOG))
            print("  Run `python3 alert_bot.py --score` once they have settled.")
            return


# ---------------------------------------------------------------------------
# Scoring -- the part that cannot be faked
# ---------------------------------------------------------------------------

def score():
    if not os.path.exists(PRED_LOG):
        sys.exit("No predictions yet. Run `python3 alert_bot.py` first.")

    with open(PRED_LOG, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)]
    if not rows:
        sys.exit("Prediction log is empty.")

    tickers = sorted({r["ticker"] for r in rows})
    print("Fetching settlements for %d contracts..." % len(tickers))

    settled = {}
    for i, t in enumerate(tickers, 1):
        d, err = get(KALSHI + "/markets/" + t)
        mk = (d or {}).get("market") or {}
        if mk.get("result") in ("yes", "no"):
            settled[t] = 1 if mk["result"] == "yes" else 0
        if i % 25 == 0:
            print("  %d/%d" % (i, len(tickers)), flush=True)
        time.sleep(0.1)

    scored = [r for r in rows if r["ticker"] in settled]
    if not scored:
        sys.exit("Nothing has settled yet. Wait, then re-run --score.")

    def brier(pred_key):
        s = 0.0
        for r in scored:
            y = settled[r["ticker"]]
            s += (float(r[pred_key]) - y) ** 2
        return s / len(scored)

    b_model, b_market = brier("model_p_yes"), brier("mid")

    alerts = [r for r in scored if r["alerted"] == "1"]
    wins = pnl = 0.0
    for r in alerts:
        y = settled[r["ticker"]]
        if r["best_side"] == "YES":
            px, won = float(r["yes_ask"]), y == 1
        else:
            px, won = float(r["no_ask"]), y == 0
        fee = math.ceil(0.07 * px * (1 - px) * 100) / 100
        pnl += (1.0 - px - fee) if won else (-px - fee)
        wins += won

    lines = [
        "# Forward Test Results",
        "",
        "Generated %s" % datetime.now(timezone.utc).isoformat(),
        "",
        "Every prediction below was written to disk **before its outcome "
        "existed**. No look-ahead is possible, by construction.",
        "",
        "| | |",
        "|---|---|",
        "| Observations recorded | %d |" % len(rows),
        "| Settled and scorable | %d |" % len(scored),
        "| Contracts | %d |" % len(settled),
        "",
        "## The gate: does the model beat the market's own price?",
        "",
        "| | Brier score |",
        "|---|---|",
        "| Model | **%.4f** |" % b_model,
        "| Market mid-price | **%.4f** |" % b_market,
        "",
    ]
    if b_model < b_market:
        lines += [
            "**The model beat the market by %.4f.** That is the first genuinely "
            "encouraging result in this project. Keep collecting -- a lead this "
            "small needs a few thousand observations before it means anything."
            % (b_market - b_model), ""]
    else:
        lines += [
            "**The market wins by %.4f.** The model is the worse forecaster, "
            "so any edge it reports is its own error. This matches the "
            "backtest exactly. Do not trade these alerts."
            % (b_model - b_market), ""]

    if alerts:
        lines += [
            "## Alerts that fired",
            "",
            "| | |",
            "|---|---|",
            "| Alerts | %d |" % len(alerts),
            "| Win rate | %.1f%% |" % (100 * wins / len(alerts)),
            "| P&L per contract | $%+.4f |" % (pnl / len(alerts)),
            "| Total P&L (1 contract each) | $%+.2f |" % pnl,
            "",
            "Win rate on its own means nothing here -- buying 95c contracts "
            "wins 95% of the time and still loses money. The P&L line is the "
            "one that counts.",
            "",
        ]
    else:
        lines += ["## Alerts", "", "None fired yet.", ""]

    os.makedirs(LOG_DIR, exist_ok=True)
    with open(SCORE_OUT, "w") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines))
    print("Saved to %s" % SCORE_OUT)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true",
                    help="record without notifications")
    ap.add_argument("--score", action="store_true",
                    help="fetch settlements and score past predictions")
    ap.add_argument("--setup", action="store_true",
                    help="generate an ntfy topic and print setup steps")
    ap.add_argument("--test-alert", action="store_true",
                    help="send one test notification and report what worked")
    a = ap.parse_args()
    if a.setup:
        cmd_setup()
    elif a.test_alert:
        cmd_test_alert()
    elif a.score:
        score()
    else:
        watch(a.quiet)


if __name__ == "__main__":
    main()
