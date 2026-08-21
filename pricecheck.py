#!/usr/bin/env python3
"""
pricecheck.py -- is our BTC price actually right?

    python3 pricecheck.py

check.py reads BTC from Coinbase 1-minute candles and drops the still-forming
bar, so its number can be up to ~2 minutes old. If BTC moves fast, that is
enough to be badly wrong -- and being wrong about spot is being wrong about
everything, because distance-from-strike is most of the model.

This prints, side by side:

  * what check.py would use          (Coinbase 1-min candle, forming bar dropped)
  * Coinbase's live ticker           (right now, no candles involved)
  * Kraken's live ticker             (a second, independent exchange)
  * Kalshi's own implied price       (backed out of the live contract price)

If the candle number disagrees with the live tickers, check.py is running on
stale data. If the live tickers agree with each other but disagree with
Kalshi's implied price, that is the index difference we already know about
(Kalshi settles on CF Benchmarks BRTI, not Coinbase).

Standard library only. Reads public data, changes nothing.
"""

import json
import math
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
CB_CANDLES = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
CB_TICKER = "https://api.exchange.coinbase.com/products/BTC-USD/ticker"
KRAKEN = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"


def get(url, params=None, timeout=20):
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "User-Agent": "btcbot-pricecheck/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl.create_default_context()) as r:
            return json.loads(r.read().decode("utf-8", errors="replace")), None
    except Exception as e:                                    # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def norm_ppf(p):
    """Inverse normal CDF, Acklam's rational approximation."""
    p = min(max(p, 1e-6), 1 - 1e-6)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def candle_price():
    """Exactly what check.py uses."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=125)
    d, err = get(CB_CANDLES, {"granularity": 60, "start": start.isoformat(),
                              "end": end.isoformat()})
    if err or not isinstance(d, list) or len(d) < 3:
        return None, None, err or "no candles"
    rows = sorted(d, key=lambda x: x[0])
    used = rows[:-1][-1]                    # forming bar dropped
    age = (datetime.now(timezone.utc)
           - datetime.fromtimestamp(used[0], timezone.utc)).total_seconds()
    closes = [float(r[4]) for r in rows[:-1]]
    seg = closes[-16:]
    rets = [math.log(b / a) for a, b in zip(seg, seg[1:]) if a > 0]
    vol = None
    if len(rets) > 2:
        m = sum(rets) / len(rets)
        vol = math.sqrt(sum((x - m) ** 2 for x in rets) / (len(rets) - 1))
    return float(used[4]), (age, vol), None


def main():
    print()
    print("  " + "=" * 66)
    print("  IS OUR BTC PRICE RIGHT?")
    print("  " + "=" * 66)

    cp, meta, err = candle_price()
    if err:
        print("  candle price: FAILED (%s)" % err[:50])
    else:
        age, vol = meta
        print("  what check.py uses      $%10s   (bar started %.0fs ago)"
              % (format(round(cp, 2), ",.2f"), age))

    d, err = get(CB_TICKER)
    cb_live = float(d["price"]) if (d and d.get("price")) else None
    print("  Coinbase live ticker    $%10s"
          % (format(round(cb_live, 2), ",.2f") if cb_live else "unavailable"))

    d, err = get(KRAKEN)
    kr = None
    try:
        kr = float(list(d["result"].values())[0]["c"][0])
    except Exception:                                         # noqa: BLE001
        pass
    print("  Kraken live ticker      $%10s"
          % (format(round(kr, 2), ",.2f") if kr else "unavailable"))

    # ---- what Kalshi's own price implies -----------------------------
    d, _ = get(KALSHI + "/markets",
               {"series_ticker": "KXBTC15M", "status": "open", "limit": 50})
    now = datetime.now(timezone.utc)
    best = None
    for m in (d or {}).get("markets") or []:
        ct = m.get("close_time")
        if not ct:
            continue
        cd = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
        mins = (cd - now).total_seconds() / 60.0
        if 0.5 <= mins <= 15.5 and (best is None or mins < best[1]):
            best = (m, mins)

    print()
    if not best:
        print("  No live contract to compare against right now.")
        print()
        return
    m, mins = best
    strike = float(m["floor_strike"])
    yb, ya = float(m["yes_bid_dollars"]), float(m["yes_ask_dollars"])
    mid = (yb + ya) / 2.0
    print("  contract   %s" % m.get("ticker"))
    print("  target     $%s      %.1f min left     Kalshi YES %.0fc"
          % (format(round(strike, 2), ",.2f"), mins, 100 * mid))

    implied = None
    if meta and meta[1] and 0.01 < mid < 0.99 and mins > 0:
        sigma = meta[1] * math.sqrt(mins)
        implied = strike * math.exp(norm_ppf(mid) * sigma)
        print("  Kalshi's price implies  $%10s   <- where the market thinks"
              % format(round(implied, 2), ",.2f"))
        print("                                        BTC is right now")

    print()
    print("  " + "-" * 66)
    ref = cb_live or kr
    if cp and ref:
        gap = cp - ref
        print("  candle vs live ticker      %+8.2f" % gap)
        if abs(gap) > 50:
            print("     -> STALE. check.py is reading a price that is out of date.")
        else:
            print("     -> fine, the candle is current enough.")
    if implied and ref:
        gap2 = ref - implied
        print("  live ticker vs Kalshi      %+8.2f" % gap2)
        if abs(gap2) > 150:
            print("     -> big gap. Either volatility is being mis-estimated, or")
            print("        Kalshi's index has genuinely diverged from Coinbase.")
        else:
            print("     -> normal. Kalshi settles on a different index (BRTI).")
    print()


if __name__ == "__main__":
    main()
