#!/usr/bin/env python3
"""
fetch_bitstamp.py -- add a second exchange to the BTC price history.

    python3 fetch_bitstamp.py

WHY
    Kalshi settles on CF Benchmarks' BRTI, which blends order books from
    several exchanges -- Bitstamp, Coinbase, Kraken, itBit, Gemini, Bullish.
    We read BTC from Coinbase alone, and our reading sits about $14 away from
    Kalshi's index. That gap is the largest measured error left in the model,
    and these contracts are decided by tens of dollars.

    Bitstamp is a genuine constituent and the only other one that will serve
    63 days of 1-minute bars from a public endpoint. Kraken keeps roughly 720
    minutes; Gemini and itBit are similar. So this gets us from one venue of
    six to two of six, which should shrink the gap -- if it does not, that is
    a real answer too and the idea gets dropped like the others.

WHAT IT DOES
    Reads real_data/btc_1min.csv to find the window already covered, then
    pulls Bitstamp 1-minute bars over exactly that window and writes
    real_data/btc_1min_bitstamp.csv. Nothing else is touched.

    About 90 requests, roughly two minutes. Safe to re-run: it starts over
    from scratch each time and overwrites its own output only.

    Standard library only. Reads public data, sends nothing.
"""

import csv
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://www.bitstamp.net/api/v2/ohlc/btcusd/"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "real_data", "btc_1min.csv")
OUT = os.path.join(HERE, "real_data", "btc_1min_bitstamp.csv")
STEP = 60          # seconds per bar
LIMIT = 1000       # bars per request (Bitstamp maximum)


def get(url, params, tries=4):
    q = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(q, headers={
                "User-Agent": "btcbot-bitstamp/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(
                    req, timeout=30, context=ssl.create_default_context()) as r:
                return json.loads(r.read().decode("utf-8", errors="replace")), None
        except Exception as e:                                # noqa: BLE001
            if attempt == tries - 1:
                return None, "%s: %s" % (type(e).__name__, e)
            time.sleep(2 ** attempt)
    return None, "gave up"


def window():
    """The exact period our Coinbase file already covers."""
    if not os.path.exists(SOURCE):
        sys.exit("  Cannot find %s -- run this from the btcbot folder." % SOURCE)
    first = last = None
    with open(SOURCE) as f:
        for row in csv.DictReader(f):
            t = row["timestamp"]
            if first is None:
                first = t
            last = t
    def parse(t):
        return int(datetime.fromisoformat(t.replace("Z", "+00:00"))
                   .replace(tzinfo=timezone.utc).timestamp())
    return parse(first), parse(last)


def main():
    start, end = window()
    total = (end - start) // STEP + 1
    print()
    print("  Bitstamp 1-minute bars")
    print("  from %s" % datetime.fromtimestamp(start, timezone.utc))
    print("  to   %s" % datetime.fromtimestamp(end, timezone.utc))
    print("  %s bars, about %d requests" % (format(total, ","), total // LIMIT + 1))
    print()

    rows = {}
    cursor = start
    reqs = 0
    empty_runs = 0
    while cursor <= end:
        chunk_end = min(cursor + STEP * LIMIT, end)
        d, err = get(API, {"step": STEP, "limit": LIMIT,
                           "start": cursor, "end": chunk_end})
        reqs += 1
        if err:
            print("  request %d failed: %s" % (reqs, err[:70]))
            cursor = chunk_end + STEP
            continue
        ohlc = ((d or {}).get("data") or {}).get("ohlc") or []
        if not ohlc:
            empty_runs += 1
            if empty_runs >= 5:
                print("  five empty responses in a row -- stopping early.")
                break
        else:
            empty_runs = 0
            for c in ohlc:
                try:
                    ts = int(c["timestamp"])
                except (KeyError, ValueError):
                    continue
                if start <= ts <= end:
                    rows[ts] = c
        pct = 100.0 * (cursor - start) / max(end - start, 1)
        print("\r  %5.1f%%   %s bars   %d requests"
              % (pct, format(len(rows), ","), reqs), end="", flush=True)
        cursor = chunk_end + STEP
        time.sleep(0.25)                   # be polite

    print()
    if not rows:
        sys.exit("\n  Got nothing. Bitstamp may be unreachable from here.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for ts in sorted(rows):
            c = rows[ts]
            w.writerow([
                datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                c.get("open"), c.get("high"), c.get("low"),
                c.get("close"), c.get("volume")])

    have = len(rows)
    print()
    print("  DONE")
    print("  wrote    %s" % OUT)
    print("  bars     %s of %s possible  (%.1f%% coverage)"
          % (format(have, ","), format(total, ","), 100.0 * have / total))
    print()
    print("  NOTE: Bitstamp timestamps a bar by its START, same as Coinbase.")
    print("  The one-minute shift that fix needs is applied in the analysis,")
    print("  not here, and it gets re-verified against real settlements before")
    print("  anything is trusted.")
    print()
    print("  Send me this file and I will measure whether blending the two")
    print("  actually moves us closer to Kalshi's index. If it does not, the")
    print("  idea gets dropped.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Stopped.")
        sys.exit(1)
