#!/usr/bin/env python3
"""
discover_series.py -- find out what BTC markets Kalshi actually runs.

The first download grabbed series KXBTCD, but inspection showed those are
HOURLY contracts (open 60 minutes before close), not 15-minute ones, and each
hourly event carries ~167 strikes, so a 1500-contract cap covered only ~8
hours of calendar time instead of 14 days.

This script answers, from the live API rather than by guessing:
  1. Which BTC/crypto series does Kalshi publish?
  2. For each, how long does a contract actually live (15 min? 60 min?)
  3. How many strikes per event, and how are they spaced?

It downloads almost nothing and finishes in well under a minute. Output goes
to ./discovery/ -- send that folder back.

Standard library only. No account, no key, read-only.
"""

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

BASE = "https://api.elections.kalshi.com/trade-api/v2"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discovery")
PAUSE = 0.15
RAW = {}


def say(m):
    print(m, flush=True)


def get(path, params=None, tag=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-research/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=30, context=ssl.create_default_context()) as r:
            body = r.read().decode("utf-8", errors="replace")
            if tag and tag not in RAW:
                RAW[tag] = body[:20000]
            return json.loads(body), None
    except urllib.error.HTTPError as e:
        try:
            d = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            d = ""
        return None, "HTTP %s %s" % (e.code, d)
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
    finally:
        time.sleep(PAUSE)


def iso_to_dt(v):
    if v is None:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


# ---------------------------------------------------------------------------

def list_all_series():
    """Enumerate series across categories; keep anything BTC-flavoured."""
    say("\n[1/3] Listing Kalshi series...")
    hits = {}
    for cat in ["Crypto", "Financials", "Economics", None]:
        data, err = get("/series", {"category": cat}, tag="series_%s" % cat)
        if err:
            say("    category=%-11s -> %s" % (cat, err[:60]))
            continue
        series = (data or {}).get("series") or []
        say("    category=%-11s -> %d series" % (cat, len(series)))
        for s in series:
            blob = json.dumps(s).upper()
            if "BTC" in blob or "BITCOIN" in blob:
                t = s.get("ticker")
                if t:
                    hits[t] = s.get("title") or ""
    return hits


def probe_series(ticker):
    """Fetch a few settled markets and characterise contract duration."""
    data, err = get("/markets", {"series_ticker": ticker,
                                 "status": "settled", "limit": 200}, tag="mkts_" + ticker)
    if err:
        return {"ticker": ticker, "error": err[:120]}

    markets = (data or {}).get("markets") or []
    if not markets:
        return {"ticker": ticker, "error": "no settled markets"}

    durations, by_event, closes = [], defaultdict(int), []
    for m in markets:
        ot, ct = iso_to_dt(m.get("open_time")), iso_to_dt(m.get("close_time"))
        if ot and ct:
            durations.append(round((ct - ot).total_seconds() / 60))
        by_event[m.get("event_ticker")] += 1
        if ct:
            closes.append(ct)

    strikes = sorted(
        float(m["floor_strike"]) for m in markets
        if m.get("floor_strike") not in (None, ""))
    gaps = [round(b - a) for a, b in zip(strikes, strikes[1:]) if b > a]

    # spacing between distinct close times = the market cadence
    uniq_closes = sorted(set(closes))
    cadence = [round((b - a).total_seconds() / 60)
               for a, b in zip(uniq_closes, uniq_closes[1:])]

    return {
        "ticker": ticker,
        "sample_markets": len(markets),
        "duration_minutes_common": Counter(durations).most_common(3),
        "cadence_minutes_common": Counter(cadence).most_common(3),
        "strikes_per_event_common": Counter(by_event.values()).most_common(3),
        "strike_gap_common": Counter(gaps).most_common(3),
        "example_ticker": markets[0].get("ticker"),
        "example_title": markets[0].get("title"),
        "example_subtitle": markets[0].get("yes_sub_title"),
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    say("=" * 68)
    say("  What BTC markets does Kalshi actually run?")
    say("=" * 68)

    found = list_all_series()

    # Always probe the ones we already know about, plus plausible 15-min names.
    candidates = set(found) | {
        "KXBTCD", "KXBTC", "KXBTC15M", "KXBTCMIN", "KXBTCQ", "KXBTC15",
        "KXBTCH", "KXBTCHOURLY", "KXBTCRANGE", "KXBTCMAXY", "KXBTCMINY",
    }

    say("\n[2/3] Characterising %d candidate series..." % len(candidates))
    results = []
    for t in sorted(candidates):
        r = probe_series(t)
        results.append(r)
        if r.get("error"):
            say("    %-14s -- %s" % (t, r["error"]))
        else:
            say("    %-14s live=%s  cadence=%s  strikes/event=%s  gap=%s"
                % (t,
                   r["duration_minutes_common"][:1],
                   r["cadence_minutes_common"][:1],
                   r["strikes_per_event_common"][:1],
                   r["strike_gap_common"][:1]))
            say("                   e.g. %s | %s" % (r["example_ticker"], r["example_subtitle"]))

    say("\n[3/3] Saving...")
    with open(os.path.join(OUT_DIR, "series_report.json"), "w") as f:
        json.dump({"btc_series_found": found, "probes": results,
                   "generated": datetime.now(timezone.utc).isoformat()}, f, indent=2)
    with open(os.path.join(OUT_DIR, "raw_responses.json"), "w") as f:
        json.dump(RAW, f, indent=2)

    say("\n" + "=" * 68)
    say("  DONE -- send back the 'discovery' folder")
    say("=" * 68)
    live15 = [r for r in results
              if not r.get("error")
              and r["duration_minutes_common"]
              and r["duration_minutes_common"][0][0] in (15, 16, 14)]
    if live15:
        say("  Found a 15-minute series: %s" % ", ".join(r["ticker"] for r in live15))
    else:
        say("  No 15-minute series found in this sample. The shortest BTC")
        say("  contract Kalshi appears to run may be hourly -- the report has")
        say("  the details either way.")
    say("")


if __name__ == "__main__":
    main()
