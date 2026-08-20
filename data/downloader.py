"""
data/downloader.py
===================
Downloads (or, where genuinely unobtainable, honestly generates clearly
labeled synthetic placeholder data for) the two data sets this project needs:

  1. Real historical BTC/USD price data.
  2. Real historical Kalshi 15-minute BTC up/down contract data.

WHAT ACTUALLY HAPPENED (documented here + in README.md + data_quality_report.md):

  * Kalshi API (api.elections.kalshi.com/trade-api/v2/..., trading-api.kalshi.com,
    docs.kalshi.com): every attempt (curl, WebFetch) was rejected at the network
    egress proxy with HTTP 403 on the CONNECT tunnel, i.e. the sandboxed
    execution environment's outbound network policy does not allow reaching
    Kalshi's domains at all -- not an auth failure, a network policy block.
    See results/reports/data_quality_report.md for the raw curl/WebFetch
    transcripts. NO Kalshi historical market/trade data could be retrieved.

  * Public crypto exchange REST APIs (Binance, Coinbase, CoinGecko, Kraken,
    Bitstamp, Gemini) and Yahoo Finance / stooq.com: same result, HTTP 403 on
    CONNECT at the egress proxy for every domain tried.

  * Alpha Vantage MCP server: reachable (goes over a different channel than
    the blocked HTTP egress). CRYPTO_INTRADAY and TIME_SERIES_INTRADAY (even
    for a plain equity symbol, to rule out a crypto-specific gate) both
    return `{"error": {"type": "rate_limit", "message": "...premium
    endpoint..."}}` regardless of interval (1min/5min/15min/60min tried) --
    these intraday endpoints are gated behind Alpha Vantage's paid tier and
    are not accessible on the key configured for this environment.

  * Alpha Vantage DIGITAL_CURRENCY_DAILY: WORKS, and returns real, genuine
    daily BTC/USD OHLCV data (2010-07-17 through today). This is the only
    real market data source obtainable in this environment. The raw response
    actually retrieved is saved at
    data/raw/_alphavantage_btc_daily_raw_response.json.

CONSEQUENCE: this environment cannot obtain real intraday (minute-level) BTC
price data, nor any real Kalshi contract data. Building an honest, non-
fabricated 15-minute walk-forward backtest against REAL Kalshi data is
therefore not possible here. Per the project's explicit fallback
instructions, this downloader:

  (a) Saves the REAL daily BTC data untouched (data/raw/btc_daily_real.csv).
  (b) Generates a clearly-labeled SYNTHETIC minute-resolution BTC price path,
      seeded and calibrated to the REAL realized daily log-return mean/vol
      measured from (a) -- documented, reproducible, NOT fabricated to look
      like real trade data (every row has is_synthetic=True and every
      filename carries a _SYNTHETIC suffix).
  (c) Generates clearly-labeled SYNTHETIC Kalshi 15-minute contract quotes
      derived from (b) using a simple documented probability model, again
      flagged is_synthetic=True / _SYNTHETIC filename.

This lets the rest of the pipeline (cleaning, feature engineering, backtest
engine, metrics, reporting) be built and exercised end-to-end, while every
report this project produces states in bold, up front, that results are
based on synthetic demo data and are NOT evidence of a real trading edge.
"""

import json
import math
import os
import random
from datetime import datetime, timedelta, timezone

import config


def load_real_daily_btc():
    """Parse the real Alpha Vantage DIGITAL_CURRENCY_DAILY response into a
    small CSV of real daily BTC/USD OHLCV.

    The raw response was fetched once, live, via the Alpha Vantage MCP tool
    during this project's research phase (this standalone script has no
    direct MCP-calling capability), and is checked into the repo at
    data/reference/alphavantage_btc_daily_raw_response.json (NOT gitignored)
    so this download step is reproducible offline. It is copied into
    data/raw/ (gitignored, like all raw data) on each --download run."""
    os.makedirs(config.RAW_DIR, exist_ok=True)
    if not os.path.exists(config.ALPHAVANTAGE_DAILY_RAW):
        with open(config.ALPHAVANTAGE_DAILY_RAW_REFERENCE) as src, open(config.ALPHAVANTAGE_DAILY_RAW, "w") as dst:
            dst.write(src.read())
    with open(config.ALPHAVANTAGE_DAILY_RAW) as f:
        raw = json.load(f)
    ts = raw["Time Series (Digital Currency Daily)"]
    rows = []
    for date_str in sorted(ts.keys()):
        d = ts[date_str]
        rows.append({
            "date": date_str,
            "open": float(d["1. open"]),
            "high": float(d["2. high"]),
            "low": float(d["3. low"]),
            "close": float(d["4. close"]),
            "volume": float(d["5. volume"]),
            "source": "alphavantage_digital_currency_daily",
            "is_synthetic": False,
        })
    os.makedirs(config.RAW_DIR, exist_ok=True)
    with open(config.BTC_DAILY_REAL_CSV, "w") as f:
        f.write("date,open,high,low,close,volume,source,is_synthetic\n")
        for r in rows:
            f.write(f"{r['date']},{r['open']},{r['high']},{r['low']},{r['close']},{r['volume']},{r['source']},{r['is_synthetic']}\n")
    print(f"[downloader] Saved {len(rows)} REAL daily BTC/USD rows -> {config.BTC_DAILY_REAL_CSV}")
    return rows


def _measure_daily_stats(daily_rows, lookback_days=365):
    """Measure real realized daily log-return mean/std from the real data, to
    calibrate the synthetic minute-path generator (documented, not arbitrary)."""
    closes = [r["close"] for r in daily_rows[-lookback_days:]]
    log_rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    n = len(log_rets)
    mean = sum(log_rets) / n
    var = sum((x - mean) ** 2 for x in log_rets) / (n - 1)
    std = math.sqrt(var)
    return mean, std, closes[-1]


def generate_synthetic_minute_btc(daily_rows):
    """Generate a SYNTHETIC minute-resolution BTC price path via seeded GBM,
    calibrated to real measured daily drift/vol. Clearly labeled as synthetic
    in every row and the filename. NOT real trade data."""
    mu_daily, sigma_daily, last_close = _measure_daily_stats(daily_rows)
    # Convert daily drift/vol to per-minute (1440 minutes/day), standard GBM scaling.
    n_minutes_per_day = 1440
    mu_min = mu_daily / n_minutes_per_day
    sigma_min = sigma_daily / math.sqrt(n_minutes_per_day)

    rng = random.Random(config.SYNTHETIC_RANDOM_SEED)
    start_dt = datetime.fromisoformat(config.SYNTHETIC_START.replace("Z", "+00:00"))
    n_minutes = config.SYNTHETIC_DAYS * n_minutes_per_day

    price = last_close
    rows = []
    t = start_dt
    for i in range(n_minutes):
        # Box-Muller for a normal draw from two uniforms (no numpy dependency here).
        u1, u2 = rng.random(), rng.random()
        u1 = max(u1, 1e-12)
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)
        ret = (mu_min - 0.5 * sigma_min ** 2) + sigma_min * z
        price = price * math.exp(ret)
        vol = abs(rng.gauss(1.0, 0.4)) * 0.15  # synthetic per-minute traded volume, BTC units
        rows.append({
            "timestamp": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "open": price / math.exp(ret),
            "high": price * (1 + abs(rng.gauss(0, sigma_min * 0.5))),
            "low": price * (1 - abs(rng.gauss(0, sigma_min * 0.5))),
            "close": price,
            "volume": round(vol, 6),
            "is_synthetic": True,
            "synthetic_method": "seeded_gbm_calibrated_to_real_daily_vol",
        })
        t += timedelta(seconds=config.SYNTHETIC_MINUTE_INTERVAL_SECONDS)

    os.makedirs(config.RAW_DIR, exist_ok=True)
    with open(config.BTC_MINUTE_SYNTHETIC_CSV, "w") as f:
        f.write("timestamp,open,high,low,close,volume,is_synthetic,synthetic_method\n")
        for r in rows:
            f.write(f"{r['timestamp']},{r['open']:.2f},{r['high']:.2f},{r['low']:.2f},{r['close']:.2f},{r['volume']},{r['is_synthetic']},{r['synthetic_method']}\n")
    print(f"[downloader] Generated {len(rows)} SYNTHETIC minute BTC rows "
          f"(seed={config.SYNTHETIC_RANDOM_SEED}, mu_daily={mu_daily:.6f}, "
          f"sigma_daily={sigma_daily:.6f}) -> {config.BTC_MINUTE_SYNTHETIC_CSV}")
    return rows


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def generate_synthetic_kalshi_contracts(minute_rows):
    """Generate SYNTHETIC Kalshi-style 15-minute up/down contracts from the
    synthetic minute price path. Fair YES probability at each minute is
    computed with a Brownian-motion barrier formula (P[final price > strike |
    current price, time remaining, vol]) using ONLY information available at
    that minute (no look-ahead) -- ask/bid are the fair probability +/- half
    a modeled spread. Contract settlement is the REAL simulated close of the
    synthetic window (known only after the window ends). Clearly labeled
    synthetic; NOT real Kalshi quotes."""
    _, sigma_daily, _ = _measure_daily_stats(load_real_daily_btc())  # reuse real vol calibration
    sigma_min = sigma_daily / math.sqrt(1440)

    dur = config.CONTRACT_DURATION_MINUTES
    rows = []
    n_windows = len(minute_rows) // dur
    for w in range(n_windows):
        window = minute_rows[w * dur:(w + 1) * dur]
        if len(window) < dur:
            break
        strike = window[0]["open"]  # strike = price at window open, standard Kalshi BTC 15m convention
        settle_price = window[-1]["close"]
        settle_yes = 1 if settle_price > strike else 0
        window_start = window[0]["timestamp"]
        window_end_dt = datetime.strptime(window[-1]["timestamp"], "%Y-%m-%dT%H:%M:%SZ") + timedelta(minutes=1)
        ticker = f"KXBTC15M-SYNTH-{w:05d}"

        for i, bar in enumerate(window):
            minutes_remaining = dur - i  # info available AT this bar's close, no future bars used
            t_years = (minutes_remaining / 1440.0) / 365.0
            current_price = bar["close"]
            if t_years <= 0 or sigma_min <= 0:
                fair_yes = 1.0 if current_price > strike else 0.0
            else:
                # log-price is ~ Normal(log(S), sigma^2 * t); P(S_T > K) under
                # driftless (risk-neutral-ish) assumption for a short 15m horizon.
                sigma_t = sigma_min * math.sqrt(minutes_remaining)
                if sigma_t <= 0:
                    fair_yes = 1.0 if current_price > strike else 0.0
                else:
                    d = math.log(current_price / strike) / sigma_t
                    fair_yes = _norm_cdf(d)
            fair_yes = min(max(fair_yes, 0.01), 0.99)
            half_spread = config.SYNTHETIC_SPREAD_CENTS / 2
            yes_bid = max(0.01, fair_yes - half_spread)
            yes_ask = min(0.99, fair_yes + half_spread)
            no_bid = max(0.01, (1 - fair_yes) - half_spread)
            no_ask = min(0.99, (1 - fair_yes) + half_spread)

            rows.append({
                "ticker": ticker,
                "timestamp": bar["timestamp"],
                "window_start": window_start,
                "window_end": window_end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "minutes_remaining": minutes_remaining,
                "strike": round(strike, 2),
                "btc_price": round(current_price, 2),
                "yes_bid": round(yes_bid, 4),
                "yes_ask": round(yes_ask, 4),
                "no_bid": round(no_bid, 4),
                "no_ask": round(no_ask, 4),
                "fair_yes_prob_model": round(fair_yes, 4),
                "settled_yes": settle_yes,
                "settle_price": round(settle_price, 2),
                "is_synthetic": True,
            })

    os.makedirs(config.RAW_DIR, exist_ok=True)
    cols = ["ticker", "timestamp", "window_start", "window_end", "minutes_remaining",
            "strike", "btc_price", "yes_bid", "yes_ask", "no_bid", "no_ask",
            "fair_yes_prob_model", "settled_yes", "settle_price", "is_synthetic"]
    with open(config.KALSHI_CONTRACTS_SYNTHETIC_CSV, "w") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(str(r[c]) for c in cols) + "\n")
    print(f"[downloader] Generated {len(rows)} SYNTHETIC Kalshi contract-minute rows "
          f"across {n_windows} synthetic 15m windows -> {config.KALSHI_CONTRACTS_SYNTHETIC_CSV}")
    return rows


def run(small_sample=True):
    """Entry point for `python main.py --download`. Always runs the small
    sample first (per project rules) -- SYNTHETIC_DAYS in config.py controls
    the size; keep it small (a handful of days) until the pipeline has been
    manually inspected."""
    print("=" * 70)
    print("DATA DOWNLOAD")
    print("=" * 70)
    print(f"DATA_MODE = {config.DATA_MODE}")
    daily_rows = load_real_daily_btc()
    if config.DATA_MODE == "synthetic_demo":
        minute_rows = generate_synthetic_minute_btc(daily_rows)
        generate_synthetic_kalshi_contracts(minute_rows)
    else:
        print("[downloader] DATA_MODE=real_daily_only: skipping synthetic generation. "
              "No 15-minute backtest is possible from daily bars alone.")
    print("[downloader] Done.")


if __name__ == "__main__":
    run()
