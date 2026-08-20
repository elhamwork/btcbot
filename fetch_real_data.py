#!/usr/bin/env python3
"""
fetch_real_data.py -- STANDALONE real-data downloader.

Run this on a machine with normal internet access. It needs NOTHING installed
beyond Python 3.8+ (standard library only -- no pip install, no API key, no
Kalshi account).

    python3 fetch_real_data.py

It writes real data into ./real_data/ and prints a summary. Zip that folder
and hand it back, and the backtester can run on real market data.

WHAT IT DOWNLOADS
-----------------
  1. Kalshi BTC 15-minute contracts that have already SETTLED (real strikes,
     real open/close times, real settlement outcomes).
  2. For each contract: real candlestick history if Kalshi serves it without
     auth, otherwise real executed trade prints.
  3. Real 1-minute BTC/USD price history from Binance (falls back to Kraken,
     then Coinbase) covering the same period.
  4. A diagnostics file recording exactly which endpoints worked, which
     failed, and one raw sample response per endpoint -- so field names can be
     verified against reality instead of guessed.

NOTE: this script was written without live access to Kalshi's API (the build
environment blocks it), so endpoint shapes come from Kalshi's documented v2
API. It is deliberately defensive: it probes several candidate series tickers,
saves raw responses, and keeps going when something 404s. If part of it fails,
the diagnostics file says why and that is enough to fix it quickly.

Nothing here is fabricated -- if an endpoint returns no data, the script says
so and writes no rows.
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

# ---------------------------------------------------------------------------
# Settings you may want to change
# ---------------------------------------------------------------------------

DAYS_BACK = 14          # how many days of history to pull
MAX_CONTRACTS = 1500    # safety cap on number of Kalshi contracts
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_data")

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Kalshi renames series occasionally. Probe each; keep whichever returns data.
CANDIDATE_SERIES = ["KXBTCD", "KXBTC", "KXBTC15", "KXBTCUSD", "BTCD", "BTC"]

USER_AGENT = "btcbot-research/1.0 (backtest data collection)"
REQUEST_PAUSE = 0.12    # be polite to public endpoints

DIAGNOSTICS = {"attempts": [], "samples": {}, "started": None, "finished": None}


# ---------------------------------------------------------------------------
# Tiny HTTP helper (stdlib only)
# ---------------------------------------------------------------------------

def http_get_json(url, params=None, timeout=30, tag=None):
    """GET a URL, return (parsed_json_or_None, error_string_or_None)."""
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        url = url + "?" + urllib.parse.urlencode(clean)

    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })

    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            _record(tag or url, "ok", None, url)
            if tag and tag not in DIAGNOSTICS["samples"]:
                DIAGNOSTICS["samples"][tag] = body[:4000]
            return data, None
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        err = "HTTP %s %s" % (e.code, detail)
        _record(tag or url, "http_error", err, url)
        return None, err
    except Exception as e:
        err = "%s: %s" % (type(e).__name__, e)
        _record(tag or url, "error", err, url)
        return None, err
    finally:
        time.sleep(REQUEST_PAUSE)


def _record(tag, status, error, url):
    DIAGNOSTICS["attempts"].append({
        "tag": tag, "status": status, "error": error, "url": url,
        "ts": datetime.now(timezone.utc).isoformat(),
    })


def say(msg):
    print(msg, flush=True)


def write_csv(path, rows, fieldnames=None):
    if not rows:
        say("    (no rows -- nothing written to %s)" % os.path.basename(path))
        return 0
    if fieldnames is None:
        seen = []
        for r in rows:
            for k in r:
                if k not in seen:
                    seen.append(k)
        fieldnames = seen
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Step 1 -- connectivity probe
# ---------------------------------------------------------------------------

def probe_connectivity():
    say("\n[1/5] Checking what this machine can reach...")
    targets = [
        ("kalshi", KALSHI_BASE + "/exchange/status"),
        ("binance", "https://api.binance.com/api/v3/time"),
        ("kraken", "https://api.kraken.com/0/public/Time"),
        ("coinbase", "https://api.exchange.coinbase.com/time"),
    ]
    reachable = {}
    for name, url in targets:
        data, err = http_get_json(url, tag="probe_" + name)
        reachable[name] = err is None
        say("    %-9s %s" % (name, "OK" if err is None else "UNREACHABLE (%s)" % err[:70]))

    if not reachable.get("kalshi"):
        say("\n    !! Kalshi is unreachable from this machine too.")
        say("       Nothing else will work. Check your connection/VPN/firewall.")
    return reachable


# ---------------------------------------------------------------------------
# Step 2 -- find the BTC 15-minute series
# ---------------------------------------------------------------------------

def find_btc_series():
    say("\n[2/5] Finding Kalshi's BTC 15-minute market series...")
    found = []

    for ticker in CANDIDATE_SERIES:
        data, err = http_get_json(
            KALSHI_BASE + "/markets",
            {"series_ticker": ticker, "limit": 10, "status": "settled"},
            tag="series_probe_" + ticker,
        )
        markets = (data or {}).get("markets") or []
        if markets:
            say("    FOUND series '%s' (%d sample settled markets)" % (ticker, len(markets)))
            found.append(ticker)
        else:
            say("    '%s' -> nothing" % ticker)

    if not found:
        say("\n    None of the guessed series tickers worked. Listing what")
        say("    crypto series Kalshi actually publishes right now...")
        for cat in ("Crypto", "Financials", None):
            data, err = http_get_json(
                KALSHI_BASE + "/series", {"category": cat}, tag="series_list_%s" % cat)
            for s in (data or {}).get("series", []) or []:
                blob = json.dumps(s).upper()
                if "BTC" in blob or "BITCOIN" in blob:
                    t = s.get("ticker")
                    if t and t not in found:
                        found.append(t)
                        say("    discovered: %s  (%s)" % (t, s.get("title", "")))
    return found


# ---------------------------------------------------------------------------
# Step 3 -- download settled contracts
# ---------------------------------------------------------------------------

def fetch_settled_markets(series_tickers, min_close_ts):
    say("\n[3/5] Downloading settled BTC contracts (last %d days)..." % DAYS_BACK)
    all_rows = []

    for series in series_tickers:
        cursor = None
        pages = 0
        got_for_series = 0
        while len(all_rows) < MAX_CONTRACTS:
            data, err = http_get_json(
                KALSHI_BASE + "/markets",
                {"series_ticker": series, "status": "settled", "limit": 1000,
                 "min_close_ts": min_close_ts, "cursor": cursor},
                tag="markets_" + series,
            )
            if err or not data:
                say("    %s: stopped (%s)" % (series, (err or "no data")[:80]))
                break

            markets = data.get("markets") or []
            for m in markets:
                m["_series_ticker"] = series
                all_rows.append(m)
                got_for_series += 1

            pages += 1
            cursor = data.get("cursor")
            say("    %s: page %d -> %d contracts (running total %d)"
                % (series, pages, len(markets), len(all_rows)))
            if not cursor or not markets:
                break

        say("    %s: %d settled contracts" % (series, got_for_series))

    return all_rows[:MAX_CONTRACTS]


# ---------------------------------------------------------------------------
# Step 4 -- per-contract price history (candlesticks preferred, trades fallback)
# ---------------------------------------------------------------------------

def fetch_contract_history(markets):
    """Try candlesticks (gives bid/ask over time). Fall back to trade prints."""
    say("\n[4/5] Downloading per-contract price history...")
    if not markets:
        say("    no contracts -- skipping")
        return [], []

    probe = markets[0]
    series = probe.get("_series_ticker")
    tkr = probe.get("ticker")
    open_ts = _to_ts(probe.get("open_time"))
    close_ts = _to_ts(probe.get("close_time"))

    say("    Testing whether candlesticks are public (no account needed)...")
    data, err = http_get_json(
        "%s/series/%s/markets/%s/candlesticks" % (KALSHI_BASE, series, tkr),
        {"start_ts": open_ts, "end_ts": close_ts, "period_interval": 1},
        tag="candlesticks_probe",
    )
    candles_public = bool(data and data.get("candlesticks"))

    candles, trades = [], []

    if candles_public:
        say("    YES -- candlesticks are public. Using them (best quality:")
        say("    real bid/ask through each contract's life).")
        for i, m in enumerate(markets, 1):
            d, e = http_get_json(
                "%s/series/%s/markets/%s/candlesticks"
                % (KALSHI_BASE, m.get("_series_ticker"), m.get("ticker")),
                {"start_ts": _to_ts(m.get("open_time")),
                 "end_ts": _to_ts(m.get("close_time")),
                 "period_interval": 1},
                tag="candlesticks",
            )
            for c in (d or {}).get("candlesticks", []) or []:
                c["ticker"] = m.get("ticker")
                candles.append(_flatten(c))
            if i % 25 == 0 or i == len(markets):
                say("      %d/%d contracts, %d candles" % (i, len(markets), len(candles)))
    else:
        say("    NO -- candlesticks need an account (%s)." % (err or "empty")[:60])
        say("    Falling back to public trade prints. Usable, but we will only")
        say("    know prices people actually traded at, not the full bid/ask.")
        for i, m in enumerate(markets, 1):
            cursor = None
            while True:
                d, e = http_get_json(
                    KALSHI_BASE + "/markets/trades",
                    {"ticker": m.get("ticker"), "limit": 1000, "cursor": cursor},
                    tag="trades",
                )
                if e or not d:
                    break
                batch = d.get("trades") or []
                for t in batch:
                    trades.append(_flatten(t))
                cursor = d.get("cursor")
                if not cursor or not batch:
                    break
            if i % 25 == 0 or i == len(markets):
                say("      %d/%d contracts, %d trades" % (i, len(markets), len(trades)))

    return candles, trades


def _flatten(d):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out["%s_%s" % (k, k2)] = v2
        else:
            out[k] = v
    return out


def _to_ts(value):
    """Kalshi returns ISO8601 strings; convert to unix seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        s = str(value).replace("Z", "+00:00")
        return int(datetime.fromisoformat(s).timestamp())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Step 5 -- real 1-minute BTC price history
# ---------------------------------------------------------------------------

def fetch_btc_minutes(start_ms, end_ms, reachable):
    say("\n[5/5] Downloading real 1-minute BTC price history...")

    # Order matters: Binance and Coinbase both paginate over an arbitrary
    # window, so they can cover the whole period. Kraken caps at ~720 recent
    # 1-minute bars (~12h), so it is a last resort only -- it must never be
    # preferred over Coinbase just because it answered first.
    needed = int((end_ms - start_ms) / 60_000)

    if reachable.get("binance"):
        rows = _binance_klines(start_ms, end_ms)
        if rows:
            return rows, "binance"
        say("    Binance returned nothing (geo-restricted?). Trying Coinbase.")
    if reachable.get("coinbase"):
        rows = _coinbase_candles(start_ms, end_ms)
        if rows:
            return rows, "coinbase"
    if reachable.get("kraken"):
        rows = _kraken_ohlc(start_ms)
        if rows:
            say("    WARNING: only Kraken was available. It serves ~720 recent")
            say("    1m bars (%d of the ~%d needed). Coverage will be short and"
                % (len(rows), needed))
            say("    the gap will be reported, not filled in.")
            return rows, "kraken"

    say("    No BTC price source reachable. No price file written.")
    return [], None


def _binance_klines(start_ms, end_ms):
    say("    Source: Binance (free, 1-minute bars)")
    rows, cur = [], start_ms
    while cur < end_ms:
        data, err = http_get_json(
            "https://api.binance.com/api/v3/klines",
            {"symbol": "BTCUSDT", "interval": "1m",
             "startTime": cur, "endTime": end_ms, "limit": 1000},
            tag="binance_klines",
        )
        if err or not data:
            say("    stopped: %s" % (err or "empty")[:80])
            break
        for k in data:
            rows.append({
                "timestamp": datetime.fromtimestamp(k[0] / 1000, timezone.utc).isoformat(),
                "open": k[1], "high": k[2], "low": k[3], "close": k[4],
                "volume": k[5],
            })
        cur = data[-1][0] + 60_000
        if len(rows) % 10000 < 1000:
            say("      %d bars..." % len(rows))
    say("    got %d one-minute bars" % len(rows))
    return rows


def _kraken_ohlc(start_ms):
    say("    Source: Kraken (fallback)")
    data, err = http_get_json(
        "https://api.kraken.com/0/public/OHLC",
        {"pair": "XBTUSD", "interval": 1, "since": int(start_ms / 1000)},
        tag="kraken_ohlc",
    )
    rows = []
    for key, series in ((data or {}).get("result") or {}).items():
        if key == "last" or not isinstance(series, list):
            continue
        for c in series:
            rows.append({
                "timestamp": datetime.fromtimestamp(c[0], timezone.utc).isoformat(),
                "open": c[1], "high": c[2], "low": c[3], "close": c[4],
                "volume": c[6],
            })
    say("    got %d one-minute bars" % len(rows))
    return rows


def _coinbase_candles(start_ms, end_ms):
    say("    Source: Coinbase (fallback, 300 bars per request)")
    rows = []
    cur = start_ms
    while cur < end_ms:
        chunk_end = min(cur + 300 * 60_000, end_ms)
        data, err = http_get_json(
            "https://api.exchange.coinbase.com/products/BTC-USD/candles",
            {"granularity": 60,
             "start": datetime.fromtimestamp(cur / 1000, timezone.utc).isoformat(),
             "end": datetime.fromtimestamp(chunk_end / 1000, timezone.utc).isoformat()},
            tag="coinbase_candles",
        )
        if err or not isinstance(data, list):
            break
        for c in sorted(data, key=lambda x: x[0]):
            rows.append({
                "timestamp": datetime.fromtimestamp(c[0], timezone.utc).isoformat(),
                "low": c[1], "high": c[2], "open": c[3], "close": c[4],
                "volume": c[5],
            })
        cur = chunk_end
    say("    got %d one-minute bars" % len(rows))
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DIAGNOSTICS["started"] = datetime.now(timezone.utc).isoformat()
    os.makedirs(OUT_DIR, exist_ok=True)

    say("=" * 68)
    say("  Kalshi BTC 15-minute -- REAL data download")
    say("  No account needed. Nothing to install. Just let it run.")
    say("=" * 68)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=DAYS_BACK)
    say("\nPeriod: %s  ->  %s  (%d days)"
        % (start.date(), now.date(), DAYS_BACK))

    reachable = probe_connectivity()

    markets, candles, trades, price_rows, price_src = [], [], [], [], None

    if reachable.get("kalshi"):
        series = find_btc_series()
        if series:
            markets = fetch_settled_markets(series, int(start.timestamp()))
            candles, trades = fetch_contract_history(markets)
        else:
            say("\n    Could not identify a BTC series. See diagnostics.json --")
            say("    the raw /series response is saved there.")

    price_rows, price_src = fetch_btc_minutes(
        int(start.timestamp() * 1000), int(now.timestamp() * 1000), reachable)

    # ---- write everything ----
    say("\nWriting files to: %s" % OUT_DIR)
    n_m = write_csv(os.path.join(OUT_DIR, "kalshi_contracts.csv"),
                    [_flatten(m) for m in markets])
    n_c = write_csv(os.path.join(OUT_DIR, "kalshi_candlesticks.csv"), candles)
    n_t = write_csv(os.path.join(OUT_DIR, "kalshi_trades.csv"), trades)
    n_p = write_csv(os.path.join(OUT_DIR, "btc_1min.csv"), price_rows,
                    ["timestamp", "open", "high", "low", "close", "volume"])

    DIAGNOSTICS["finished"] = datetime.now(timezone.utc).isoformat()
    DIAGNOSTICS["summary"] = {
        "days_back": DAYS_BACK,
        "period_start": start.isoformat(),
        "period_end": now.isoformat(),
        "reachable": reachable,
        "contracts": n_m, "candlesticks": n_c, "trades": n_t,
        "btc_minute_bars": n_p, "btc_source": price_src,
    }
    with open(os.path.join(OUT_DIR, "diagnostics.json"), "w", encoding="utf-8") as f:
        json.dump(DIAGNOSTICS, f, indent=2)

    say("\n" + "=" * 68)
    say("  DONE")
    say("=" * 68)
    say("  Kalshi contracts .... %d" % n_m)
    say("  Kalshi candlesticks . %d" % n_c)
    say("  Kalshi trades ....... %d" % n_t)
    say("  BTC 1-minute bars ... %d   (source: %s)" % (n_p, price_src or "none"))
    say("")

    if n_m and n_p and (n_c or n_t):
        say("  Looks good. Zip the 'real_data' folder and send it back.")
    else:
        say("  Something came back empty. Send the folder back ANYWAY --")
        say("  diagnostics.json records exactly what failed, which is what's")
        say("  needed to fix it. Nothing was invented to fill the gap.")
    say("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\nStopped by user. Partial files (if any) are in %s" % OUT_DIR)
        sys.exit(1)
