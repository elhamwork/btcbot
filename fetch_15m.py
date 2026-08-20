#!/usr/bin/env python3
"""
fetch_15m.py -- download the REAL Kalshi BTC 15-minute series (KXBTC15M).

Supersedes the KXBTCD portion of fetch_real_data.py. Discovery against the
live API (discover_series.py) established:

    KXBTC15M   contract lifetime 15 min, new event every 15 min,
               exactly ONE strike per event, e.g.
               KXBTC15M-26AUG200000-00 | "Target Price: $69,107.63"

That is the series this study is actually about. KXBTCD, downloaded first, is
the HOURLY series with ~167 strikes per event, which is why 1500 contracts
covered only 8 hours.

This script pulls every settled KXBTC15M contract in the window plus its full
per-minute bid/ask candlestick history. At ~96 contracts/day, 14 days is
roughly 1,344 contracts -- a few minutes of downloading.

It does NOT touch btc_1min.csv. The BTC price data already collected (20,161
bars, 100% coverage of the same window) is reused as-is.

Standard library only. No account, no key, read-only.
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
from collections import Counter
from datetime import datetime, timedelta, timezone

SERIES = "KXBTC15M"
DAYS_BACK = 14
MAX_CONTRACTS = 6000          # generous headroom; ~1344 expected
BASE = "https://api.elections.kalshi.com/trade-api/v2"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_data")
PAUSE = 0.12
MAX_RETRIES = 3

CONTRACTS_CSV = os.path.join(OUT_DIR, "kalshi_15m_contracts.csv")
CANDLES_CSV = os.path.join(OUT_DIR, "kalshi_15m_candlesticks.csv")
DIAG_JSON = os.path.join(OUT_DIR, "diagnostics_15m.json")

DIAG = {"errors": [], "samples": {}}


def say(m):
    print(m, flush=True)


def get(path, params=None, tag=None, attempt=1):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-research/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=30, context=ssl.create_default_context()) as r:
            body = r.read().decode("utf-8", errors="replace")
            if tag and tag not in DIAG["samples"]:
                DIAG["samples"][tag] = body[:6000]
            return json.loads(body), None
    except Exception as e:
        detail = "%s: %s" % (type(e).__name__, e)
        if attempt < MAX_RETRIES:
            time.sleep(2 ** attempt)
            return get(path, params, tag, attempt + 1)
        DIAG["errors"].append({"path": path, "params": params, "error": detail[:200]})
        return None, detail
    finally:
        time.sleep(PAUSE)


def flatten(d):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out["%s_%s" % (k, k2)] = v2
        elif isinstance(v, list):
            out[k] = json.dumps(v)
        else:
            out[k] = v
    return out


def to_ts(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    try:
        return int(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def write_csv(path, rows):
    if not rows:
        say("    nothing to write for %s" % os.path.basename(path))
        return 0
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=DAYS_BACK)

    say("=" * 68)
    say("  Kalshi %s -- the real 15-minute BTC series" % SERIES)
    say("=" * 68)
    say("Window: %s -> %s (%d days)" % (start.date(), now.date(), DAYS_BACK))
    say("Expecting roughly %d contracts (96/day)\n" % (DAYS_BACK * 96))

    # ---- contracts -------------------------------------------------------
    say("[1/2] Downloading settled contracts...")
    contracts, cursor, page = [], None, 0
    while len(contracts) < MAX_CONTRACTS:
        data, err = get("/markets", {
            "series_ticker": SERIES, "status": "settled", "limit": 1000,
            "min_close_ts": int(start.timestamp()), "cursor": cursor,
        }, tag="markets")
        if err:
            say("    stopped: %s" % err[:90])
            break
        markets = (data or {}).get("markets") or []
        contracts.extend(markets)
        page += 1
        cursor = (data or {}).get("cursor")
        say("    page %d -> %d (total %d)" % (page, len(markets), len(contracts)))
        if not cursor or not markets:
            break

    if not contracts:
        say("\nNo contracts returned. Nothing written. Send diagnostics back.")
        with open(DIAG_JSON, "w") as f:
            json.dump(DIAG, f, indent=2)
        sys.exit(1)

    closes = sorted(x for x in (c.get("close_time") for c in contracts) if x)
    say("    earliest close: %s" % closes[0])
    say("    latest close:   %s" % closes[-1])
    durs = Counter()
    for c in contracts:
        o, cl = to_ts(c.get("open_time")), to_ts(c.get("close_time"))
        if o and cl:
            durs[round((cl - o) / 60)] += 1
    say("    contract lifetimes (min): %s" % durs.most_common(3))

    # ---- candlesticks ----------------------------------------------------
    say("\n[2/2] Downloading per-minute bid/ask history...")
    candles, missing = [], 0
    total = len(contracts)
    for i, m in enumerate(contracts, 1):
        tkr = m.get("ticker")
        d, err = get("/series/%s/markets/%s/candlesticks" % (SERIES, tkr), {
            "start_ts": to_ts(m.get("open_time")),
            "end_ts": to_ts(m.get("close_time")),
            "period_interval": 1,
        }, tag="candlesticks")
        got = (d or {}).get("candlesticks") or []
        if not got:
            missing += 1
        for c in got:
            row = flatten(c)
            row["ticker"] = tkr
            candles.append(row)
        if i % 50 == 0 or i == total:
            say("    %d/%d contracts, %d candles (%d empty)"
                % (i, total, len(candles), missing))

    # ---- save ------------------------------------------------------------
    say("\nWriting...")
    n_c = write_csv(CONTRACTS_CSV, [flatten(c) for c in contracts])
    n_k = write_csv(CANDLES_CSV, candles)
    DIAG["summary"] = {
        "series": SERIES, "days_back": DAYS_BACK,
        "window_start": start.isoformat(), "window_end": now.isoformat(),
        "contracts": n_c, "candles": n_k, "contracts_without_candles": missing,
        "earliest_close": closes[0], "latest_close": closes[-1],
        "lifetimes_minutes": dict(durs),
    }
    with open(DIAG_JSON, "w") as f:
        json.dump(DIAG, f, indent=2)

    say("\n" + "=" * 68)
    say("  DONE")
    say("=" * 68)
    say("  Contracts .............. %d" % n_c)
    say("  Candles ................ %d" % n_k)
    say("  Contracts w/o candles .. %d" % missing)
    say("  Covers ................. %s  ->  %s" % (closes[0], closes[-1]))
    say("")
    days = (datetime.fromisoformat(closes[-1].replace("Z", "+00:00"))
            - datetime.fromisoformat(closes[0].replace("Z", "+00:00"))).total_seconds() / 86400
    say("  That is %.1f days of calendar coverage." % days)
    if days < DAYS_BACK * 0.6:
        say("  NOTE: shorter than requested -- Kalshi may not retain settled")
        say("  15-minute markets for the full window. Reported, not papered over.")
    say("\n  Re-zip the real_data folder and send it back.")
    say("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\nStopped by user.")
        sys.exit(1)
