#!/usr/bin/env python3
"""
fetch_btc_prices.py -- BTC 1-minute price history from Coinbase only.

Companion to fetch_real_data.py, for the case where Binance is geo-blocked
(HTTP 451) and Kraken's ~720-bar limit is too short to cover the backtest
period. Coinbase serves 300 bars per request and paginates cleanly, so it can
cover the full window.

Run it AFTER fetch_real_data.py has finished. It only rewrites the BTC price
file; the Kalshi data already downloaded is left untouched.

    python3 fetch_btc_prices.py

Standard library only. No account, no key, public endpoint, read-only.
"""

import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

DAYS_BACK = 14  # must match fetch_real_data.py
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_data")
OUT_CSV = os.path.join(OUT_DIR, "btc_1min.csv")

COINBASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
CHUNK_MINUTES = 300           # Coinbase's per-request maximum
PAUSE = 0.25                  # stay well under the public rate limit
MAX_RETRIES = 4


def say(m):
    print(m, flush=True)


def get(url, params, attempt=1):
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={
        "User-Agent": "btcbot-research/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=30, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8", errors="replace")), None
    except Exception as e:
        detail = "%s: %s" % (type(e).__name__, e)
        if attempt < MAX_RETRIES:
            wait = 2 ** attempt
            say("      retry %d in %ds (%s)" % (attempt, wait, detail[:60]))
            time.sleep(wait)
            return get(url, params, attempt + 1)
        return None, detail


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now - timedelta(days=DAYS_BACK)

    say("=" * 68)
    say("  BTC 1-minute prices from Coinbase")
    say("=" * 68)
    say("Period: %s -> %s" % (start.isoformat(), now.isoformat()))
    expected = int((now - start).total_seconds() // 60)
    say("Expecting roughly %d one-minute bars\n" % expected)

    rows = {}
    cur = start
    chunk_no = 0
    total_chunks = (expected // CHUNK_MINUTES) + 1
    failures = 0

    while cur < now:
        chunk_end = min(cur + timedelta(minutes=CHUNK_MINUTES), now)
        chunk_no += 1

        data, err = get(COINBASE, {
            "granularity": 60,
            "start": cur.isoformat(),
            "end": chunk_end.isoformat(),
        })

        if err or not isinstance(data, list):
            failures += 1
            say("  chunk %d/%d FAILED: %s" % (chunk_no, total_chunks, (err or "bad payload")[:70]))
        else:
            for c in data:
                # Coinbase candle: [time, low, high, open, close, volume]
                ts = int(c[0])
                rows[ts] = {
                    "timestamp": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                    "open": c[3], "high": c[2], "low": c[1], "close": c[4],
                    "volume": c[5],
                }

        if chunk_no % 10 == 0 or chunk_end >= now:
            pct = 100.0 * chunk_no / max(total_chunks, 1)
            say("  %d/%d chunks (%.0f%%) -- %d bars so far"
                % (chunk_no, total_chunks, pct, len(rows)))

        cur = chunk_end
        time.sleep(PAUSE)

    ordered = [rows[k] for k in sorted(rows)]

    if not ordered:
        say("\nNo data retrieved. Nothing written -- no placeholder created.")
        say("Send the terminal output back so this can be diagnosed.")
        sys.exit(1)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        w.writeheader()
        w.writerows(ordered)

    coverage = 100.0 * len(ordered) / max(expected, 1)
    say("\n" + "=" * 68)
    say("  DONE")
    say("=" * 68)
    say("  Bars written ..... %d" % len(ordered))
    say("  Expected ......... ~%d" % expected)
    say("  Coverage ......... %.1f%%" % coverage)
    say("  First bar ........ %s" % ordered[0]["timestamp"])
    say("  Last bar ......... %s" % ordered[-1]["timestamp"])
    say("  Failed chunks .... %d" % failures)
    say("  Saved to ......... %s" % OUT_CSV)
    if coverage < 90:
        say("\n  Coverage is below 90%. Gaps will be reported honestly in the")
        say("  data-quality report rather than filled in. Send it back as is.")
    say("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\nStopped by user.")
        sys.exit(1)
