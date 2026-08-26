#!/usr/bin/env python3
"""
Download as much KXBTC15M history as Kalshi will serve.

fetch_15m.py stopped at 6,000 contracts. That number was chosen when the
window was 14 days ("~1344 expected") and never raised when the window went
to 90, so the study's 63 days is the cap, not Kalshi's memory. This has no
cap, resumes where it left off, and shards its output by month so a partial
run is still useful and git only rewrites what changed.

    python3 fetch_15m_deep.py --days 400
    python3 fetch_15m_deep.py --days 400 --minutes 300   # stop after 5h
    python3 fetch_15m_deep.py --status

Output, all under real_data/kalshi15m/:

    contracts_YYYY-MM.csv    one row per settled contract
    candles_YYYY-MM.csv      per-minute bid/ask for each of them
    progress.json            which contracts already have candles

Re-running is safe and cheap: contracts already fetched are skipped, so a
run that dies halfway costs only the contracts it had not reached. That
matters because a year is roughly 35,000 contracts and one request each.

Standard library only. No account, no key, read-only.
"""

import argparse
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

SERIES = "KXBTC15M"
BASE = "https://api.elections.kalshi.com/trade-api/v2"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "real_data", "kalshi15m")
PROGRESS = os.path.join(OUT, "progress.json")
PAUSE = 0.10
MAX_RETRIES = 4


def say(m):
    print(m, flush=True)


def get(path, params=None, attempt=1):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-fetch/2.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=30, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8", "replace")), None
    except urllib.error.HTTPError as e:
        # 429 and 5xx are worth waiting out; a 404 is not.
        if e.code in (429, 500, 502, 503, 504) and attempt <= MAX_RETRIES:
            time.sleep(min(2 ** attempt, 30))
            return get(path, params, attempt + 1)
        return None, "HTTP %s" % e.code
    except Exception as e:                                    # noqa: BLE001
        if attempt <= MAX_RETRIES:
            time.sleep(min(2 ** attempt, 30))
            return get(path, params, attempt + 1)
        return None, "%s: %s" % (type(e).__name__, e)


def to_ts(s):
    if not s:
        return None
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00"))
                   .timestamp())
    except ValueError:
        return None


def flatten(d, prefix=""):
    out = {}
    for k, v in (d or {}).items():
        key = prefix + k
        if isinstance(v, (dict, list)):
            out[key] = json.dumps(v, separators=(",", ":"))
        else:
            out[key] = v
    return out


def month_of(iso):
    return str(iso)[:7] if iso else "unknown"


def load_progress():
    try:
        with open(PROGRESS) as f:
            p = json.load(f)
            p["done"] = set(p.get("done") or [])
            return p
    except Exception:                                         # noqa: BLE001
        return {"done": set()}


def save_progress(p):
    os.makedirs(OUT, exist_ok=True)
    tmp = PROGRESS + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"done": sorted(p["done"]),
                   "updated": datetime.now(timezone.utc).isoformat()}, f)
    os.replace(tmp, PROGRESS)


def append_rows(path, rows):
    """Append, writing a header only if the file is new. Union of columns."""
    if not rows:
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            existing = next(csv.reader(f), [])
    fields = list(existing)
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    if fields != existing and existing:
        # A new column appeared. Rewrite the file rather than silently
        # dropping it -- this is a one-off cost and losing a column quietly
        # is exactly the kind of thing that poisons a study months later.
        with open(path, newline="", encoding="utf-8") as f:
            old = list(csv.DictReader(f))
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(old)
    fresh = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if fresh:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def list_contracts(days):
    """Every settled contract in the window. Pages until Kalshi stops."""
    start = datetime.now(timezone.utc) - timedelta(days=days)
    say("  window starts %s" % start.date())
    out, cursor, page = [], None, 0
    seen = set()
    while True:
        d, err = get("/markets", {
            "series_ticker": SERIES, "status": "settled", "limit": 1000,
            "min_close_ts": int(start.timestamp()), "cursor": cursor,
        })
        if err:
            say("  stopped paging: %s" % err)
            break
        markets = (d or {}).get("markets") or []
        new = [m for m in markets if m.get("ticker") not in seen]
        for m in new:
            seen.add(m.get("ticker"))
        out.extend(new)
        page += 1
        cursor = (d or {}).get("cursor")
        say("    page %d -> %d new (total %d)" % (page, len(new), len(out)))
        if not cursor or not markets or not new:
            break
        time.sleep(PAUSE)
    return out


def status():
    p = load_progress()
    say("  contracts with candles: %d" % len(p["done"]))
    if not os.path.isdir(OUT):
        say("  nothing downloaded yet")
        return
    months = {}
    for f in sorted(os.listdir(OUT)):
        if not f.endswith(".csv"):
            continue
        n = sum(1 for _ in open(os.path.join(OUT, f))) - 1
        kind, mon = f.rsplit("_", 1)
        months.setdefault(mon[:-4], {})[kind] = n
    say("  %-10s %12s %12s" % ("month", "contracts", "candles"))
    for mon in sorted(months):
        m = months[mon]
        say("  %-10s %12s %12s" % (mon,
                                   format(m.get("contracts", 0), ",d"),
                                   format(m.get("candles", 0), ",d")))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=400,
                    help="how far back to ask for (default 400)")
    ap.add_argument("--minutes", type=float, default=None,
                    help="stop cleanly after this long, then resume next run")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status:
        return status()

    deadline = time.time() + a.minutes * 60 if a.minutes else None
    os.makedirs(OUT, exist_ok=True)

    say("[1/2] Listing settled contracts...")
    contracts = list_contracts(a.days)
    if not contracts:
        sys.exit("  Nothing returned. Kalshi unreachable, or no history.")
    closes = sorted(c.get("close_time") for c in contracts if c.get("close_time"))
    span = (datetime.fromisoformat(closes[-1].replace("Z", "+00:00"))
            - datetime.fromisoformat(closes[0].replace("Z", "+00:00"))).days
    say("  %d contracts, %s -> %s (%d days)"
        % (len(contracts), closes[0][:10], closes[-1][:10], span))
    if span < a.days * 0.8:
        say("  NOTE: shorter than the %d days asked for. That is Kalshi's"
            % a.days)
        say("  retention, not a cap in this script. Reported, not hidden.")

    by_month = {}
    for c in contracts:
        by_month.setdefault(month_of(c.get("close_time")), []).append(c)
    for mon, group in sorted(by_month.items()):
        path = os.path.join(OUT, "contracts_%s.csv" % mon)
        if not os.path.exists(path):
            append_rows(path, [flatten(c) for c in group])

    say("\n[2/2] Downloading per-minute bid/ask...")
    prog = load_progress()
    todo = [c for c in contracts if c.get("ticker") not in prog["done"]]
    say("  %d already done, %d to fetch" % (len(prog["done"]), len(todo)))
    pending, got, empty = {}, 0, 0
    for i, m in enumerate(todo, 1):
        if deadline and time.time() > deadline:
            say("  time budget reached -- stopping cleanly at %d/%d"
                % (i - 1, len(todo)))
            break
        tkr = m.get("ticker")
        d, err = get("/series/%s/markets/%s/candlesticks" % (SERIES, tkr), {
            "start_ts": to_ts(m.get("open_time")),
            "end_ts": to_ts(m.get("close_time")),
            "period_interval": 1,
        })
        rows = (d or {}).get("candlesticks") or []
        if not rows and not err:
            empty += 1
        for c in rows:
            r = flatten(c)
            r["ticker"] = tkr
            pending.setdefault(month_of(m.get("close_time")), []).append(r)
        got += len(rows)
        if not err:
            prog["done"].add(tkr)
        if i % 250 == 0 or i == len(todo):
            for mon, rws in pending.items():
                append_rows(os.path.join(OUT, "candles_%s.csv" % mon), rws)
            pending = {}
            save_progress(prog)
            say("    %d/%d contracts, %s candles (%d empty)"
                % (i, len(todo), format(got, ",d"), empty))
        time.sleep(PAUSE)

    for mon, rws in pending.items():
        append_rows(os.path.join(OUT, "candles_%s.csv" % mon), rws)
    save_progress(prog)
    say("\nDone this run: %s candles over %d contracts."
        % (format(got, ",d"), len(prog["done"])))
    status()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\nStopped. Re-run to resume.")
        sys.exit(1)
