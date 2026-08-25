#!/usr/bin/env python3
"""
bookwatch.py -- collect Kalshi order-book depth, which no history exists for.

    python3 bookwatch.py            # collect
    python3 bookwatch.py --status   # how much has been gathered
    python3 bookwatch.py --settle   # attach outcomes to what has settled

WHY THIS EXISTS
===============
Everything the bot does today uses two numbers from the book: the best bid and
the best ask. Kalshi publishes the whole thing -- how much size is stacked at
every price, on both sides. That is the largest genuinely unexplored signal
left, and order-book imbalance is a real effect in real markets.

It cannot be backtested. Kalshi's historical endpoints return prices and
volume, never depth, and the size fields on settled contracts read zero
because the book empties at settlement. The only way to find out is to record
it going forward.

So this is a two-week investment before it can answer anything. It is
deliberately greedy about what it saves -- re-collecting costs another two
weeks, so it captures more than the first hypothesis needs:

  * the full book, both sides, every level
  * best bid/ask and the size resting at each
  * total size within 5c and 10c of the touch
  * imbalance, and a size-weighted mid
  * BTC at that instant, and the strike and time remaining
  * the settlement outcome, attached later by --settle

WHAT IT DOES NOT DO
===================
It does not trade, predict, or advise. It is a tape recorder. Nothing in the
bot changes until there is enough data to test a hypothesis honestly, and the
test may well come back negative like most of the others have.

Standard library only. No account, no API key, read-only.
"""

import argparse
import csv
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
COINBASE_TICKER = "https://api.exchange.coinbase.com/products/BTC-USD/ticker"

POLL_SECONDS = 20
DEPTH = 30                      # levels per side to request

HERE = os.path.dirname(os.path.abspath(__file__))
# Overridable so the cloud runner can point it at a folder that gets committed
# back to the repo. Without that every run would collect for an hour and throw
# it away, and this signal needs weeks.
OUT_DIR = os.environ.get("BOOK_OUT_DIR") or os.path.join(HERE, "forward_test")
BOOK_DIR = os.path.join(OUT_DIR, "orderbook")
RAW_SAMPLE = os.path.join(OUT_DIR, "orderbook_raw_sample.json")


def book_csv(day=None):
    """
    One file per UTC day.

    A single growing file would be re-stored by git on every hourly commit.
    At 20-second polls that is about 900KB a day, so three weeks of hourly
    commits would put hundreds of megabytes of near-duplicate snapshots in
    the repository. Sharding by day means each commit only rewrites today.
    """
    d = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(BOOK_DIR, "%s.csv" % d)


def book_files():
    """Every day file, oldest first."""
    try:
        return sorted(os.path.join(BOOK_DIR, f)
                      for f in os.listdir(BOOK_DIR) if f.endswith(".csv"))
    except OSError:
        return []

FIELDS = [
    "observed_at", "ticker", "close_time", "minutes_remaining", "strike",
    "btc", "yes_bid", "yes_bid_size", "yes_ask", "yes_ask_size",
    "yes_depth_5c", "no_depth_5c", "yes_depth_10c", "no_depth_10c",
    "yes_total", "no_total", "imbalance_touch", "imbalance_5c",
    "weighted_mid", "mid", "spread", "n_yes_levels", "n_no_levels",
    "volume", "open_interest", "outcome",
]


def get(url, params=None, timeout=20):
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-bookwatch/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8", errors="replace")), None
    except Exception as e:                                    # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def btc_now():
    d, err = get(COINBASE_TICKER, timeout=10)
    if err or not isinstance(d, dict):
        return None
    try:
        return float(d.get("price"))
    except (TypeError, ValueError):
        return None


def live_contract():
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
        if 0.2 <= mins <= 15.5 and (best is None or mins < best[1]):
            best = (m, mins)
    return best, None


def parse_levels(raw):
    """
    Kalshi returns each side as [[price_cents, size], ...]. Tolerate dicts and
    missing pieces rather than crashing -- a shape change mid-collection would
    otherwise silently end a two-week run.
    """
    out = []
    for lv in raw or []:
        try:
            if isinstance(lv, dict):
                p = float(lv.get("price", lv.get("yes_price", 0)))
                s = float(lv.get("size", lv.get("quantity", 0)))
            else:
                p, s = float(lv[0]), float(lv[1])
        except (TypeError, ValueError, IndexError):
            continue
        if p > 1.5:              # cents -> dollars
            p /= 100.0
        if 0.0 < p < 1.0 and s > 0:
            out.append((p, s))
    return out


def summarise(yes, no):
    """Turn two ladders into the numbers worth testing later."""
    yes = sorted(yes, key=lambda x: -x[0])     # best YES bid first
    no = sorted(no, key=lambda x: -x[0])       # best NO bid first

    y_best, y_size = (yes[0] if yes else (None, 0.0))
    n_best, n_size = (no[0] if no else (None, 0.0))

    # A NO bid at p is a YES offer at 1-p.
    yes_bid = y_best
    yes_ask = (1.0 - n_best) if n_best is not None else None

    def within(levels, best, c):
        return sum(s for p, s in levels if best is not None and best - p <= c)

    y5, n5 = within(yes, y_best, 0.05), within(no, n_best, 0.05)
    y10, n10 = within(yes, y_best, 0.10), within(no, n_best, 0.10)
    y_tot = sum(s for _, s in yes)
    n_tot = sum(s for _, s in no)

    def imb(a, b):
        return (a - b) / (a + b) if (a + b) > 0 else None

    wmid = None
    if yes_bid is not None and yes_ask is not None and (y_size + n_size) > 0:
        # Size-weighted: heavy resting size on one side pulls the fair price
        # toward the OTHER side, since that is where the pressure is absorbed.
        wmid = (yes_bid * n_size + yes_ask * y_size) / (y_size + n_size)

    mid = ((yes_bid + yes_ask) / 2.0
           if yes_bid is not None and yes_ask is not None else None)

    return {
        "yes_bid": yes_bid, "yes_bid_size": y_size,
        "yes_ask": yes_ask, "yes_ask_size": n_size,
        "yes_depth_5c": y5, "no_depth_5c": n5,
        "yes_depth_10c": y10, "no_depth_10c": n10,
        "yes_total": y_tot, "no_total": n_tot,
        "imbalance_touch": imb(y_size, n_size),
        "imbalance_5c": imb(y5, n5),
        "weighted_mid": wmid, "mid": mid,
        "spread": (yes_ask - yes_bid
                   if yes_bid is not None and yes_ask is not None else None),
        "n_yes_levels": len(yes), "n_no_levels": len(no),
    }


def fetch_book(ticker, save_raw=False):
    d, err = get(KALSHI + "/markets/%s/orderbook" % ticker, {"depth": DEPTH})
    if err:
        return None, err
    ob = (d or {}).get("orderbook") or {}
    if save_raw and not os.path.exists(RAW_SAMPLE):
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(RAW_SAMPLE, "w") as f:
            json.dump(d, f, indent=1)
    return summarise(parse_levels(ob.get("yes")),
                     parse_levels(ob.get("no"))), None


# ---------------------------------------------------------------------------

def _open_day(day):
    """Append to that day's file, writing the header if it is new."""
    os.makedirs(BOOK_DIR, exist_ok=True)
    path = book_csv(day)
    fresh = not os.path.exists(path)
    fh = open(path, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
    if fresh:
        w.writeheader()
    return fh, w, path


def collect(hours=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    stop_at = (time.time() + hours * 3600.0) if hours else None
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fh, w, BOOK_CSV = _open_day(day)

    print("=" * 70)
    print("  Kalshi order-book collector -- %s" % SERIES)
    print("=" * 70)
    print("  Recording depth every %ds to %s" % (POLL_SECONDS, BOOK_CSV))
    print("  No history exists for this, so it has to be gathered forward.")
    print("  Two weeks or so before it can answer anything. Ctrl-C to stop.")
    print()

    rows = 0
    first = True
    while True:
        if stop_at and time.time() >= stop_at:
            print("  %d snapshots this run. Stopping as asked." % rows)
            break
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != day:                       # roll over at UTC midnight
            fh.close()
            day = today
            fh, w, BOOK_CSV = _open_day(day)
            print("  new day, now writing %s" % BOOK_CSV)
        try:
            got, err = live_contract()
            if err or not got:
                print("  %s  no live contract (%s)"
                      % (datetime.now().strftime("%H:%M:%S"),
                         (err or "between contracts")[:40]), flush=True)
                time.sleep(POLL_SECONDS)
                continue
            m, mins = got
            book, err = fetch_book(m.get("ticker"), save_raw=first)
            first = False
            if err or not book:
                print("  book unavailable (%s)" % (err or "empty")[:50], flush=True)
                time.sleep(POLL_SECONDS)
                continue

            rec = dict(book)
            rec.update({
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "ticker": m.get("ticker"), "close_time": m.get("close_time"),
                "minutes_remaining": round(mins, 2),
                "strike": m.get("floor_strike"), "btc": btc_now(),
                "volume": m.get("volume_fp") or m.get("volume"),
                "open_interest": m.get("open_interest_fp") or m.get("open_interest"),
                "outcome": "",
            })
            w.writerow(rec)
            fh.flush()
            rows += 1

            if rows % 5 == 0 or rows == 1:
                print("  %s  %s  %.1fmin  bid %s/%s ask %s/%s  imbalance %s  (%d rows)"
                      % (datetime.now().strftime("%H:%M:%S"),
                         m.get("ticker", "")[-8:], mins,
                         _f(book["yes_bid"]), _i(book["yes_bid_size"]),
                         _f(book["yes_ask"]), _i(book["yes_ask_size"]),
                         _f(book["imbalance_touch"], 2), rows), flush=True)
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            fh.close()
            print("\n  Stopped. %d rows in %s" % (rows, BOOK_CSV))
            print("  Run --settle later to attach outcomes.")
            return
        except Exception as e:                                # noqa: BLE001
            print("  error (continuing): %s" % str(e)[:80], flush=True)
            time.sleep(POLL_SECONDS)


def _f(x, nd=2):
    return "-" if x is None else ("%.*f" % (nd, x))


def _i(x):
    return "-" if x is None else "%d" % x


def read_rows():
    """Every snapshot ever collected, across all day files."""
    out = []
    for path in book_files():
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["_file"] = path
                out.append(r)
    return out


def settle():
    rows = read_rows()
    if not rows:
        sys.exit("Nothing collected yet.")
    pending = sorted({r["ticker"] for r in rows if not r.get("outcome")})
    now = datetime.now(timezone.utc)
    done = {}
    print("Looking up %d contracts..." % len(pending))
    for i, t in enumerate(pending, 1):
        ct = next((r["close_time"] for r in rows if r["ticker"] == t), None)
        try:
            if ct and now < datetime.fromisoformat(
                    str(ct).replace("Z", "+00:00")) + timedelta(minutes=2):
                continue
        except Exception:                                     # noqa: BLE001
            pass
        d, _ = get(KALSHI + "/markets/" + t)
        res = ((d or {}).get("market") or {}).get("result")
        if res in ("yes", "no"):
            done[t] = res
        if i % 25 == 0:
            print("  %d/%d" % (i, len(pending)), flush=True)
        time.sleep(0.1)

    for r in rows:
        if not r.get("outcome") and r["ticker"] in done:
            r["outcome"] = done[r["ticker"]]

    by_file = {}
    for r in rows:
        by_file.setdefault(r["_file"], []).append(r)
    for path, group in by_file.items():
        tmp = path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            wr.writeheader()
            wr.writerows(group)
        os.replace(tmp, path)
    print("Attached outcomes to %d contracts." % len(done))
    status()


def status():
    rows = read_rows()
    print()
    print("=" * 70)
    print("  ORDER-BOOK COLLECTION")
    print("=" * 70)
    if not rows:
        print("  Nothing yet. Run  python3 bookwatch.py  to start.")
        print()
        return
    tickers = {r["ticker"] for r in rows}
    settled = {r["ticker"] for r in rows if r.get("outcome")}
    times = sorted(r["observed_at"] for r in rows)
    span = 0.0
    try:
        span = (datetime.fromisoformat(times[-1])
                - datetime.fromisoformat(times[0])).total_seconds() / 86400
    except Exception:                                         # noqa: BLE001
        pass
    print("  snapshots        %d" % len(rows))
    print("  contracts        %d  (%d settled)" % (len(tickers), len(settled)))
    print("  collecting for   %.1f days" % span)
    print()
    need = 300
    if len(settled) < need:
        print("  %d settled contracts so far. Around %d are needed before"
              % (len(settled), need))
        print("  imbalance can be tested without fooling ourselves -- roughly")
        print("  %.0f more days at this rate."
              % max((need - len(settled)) / max(len(settled) / max(span, 0.01), 1), 0)
              if span > 0.01 and settled else "  a few more days.")
    else:
        print("  Enough to test. The question to ask of it:")
        print("    does imbalance predict the outcome BEYOND what the price")
        print("    already says? Split by period, and require it to hold in")
        print("    all of them -- same bar as everything else here.")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--settle", action="store_true")
    ap.add_argument("--hours", type=float, default=None,
                    help="stop after this long (the cloud runner uses it)")
    a = ap.parse_args()
    if a.status:
        status()
    elif a.settle:
        settle()
    else:
        collect(a.hours)


if __name__ == "__main__":
    main()
