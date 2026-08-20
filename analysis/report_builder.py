"""analysis/report_builder.py -- runs the baseline backtest (test split as
primary evidence), builds breakdowns, charts, statistical significance
checks, and writes results/final_report.md."""

import os
from datetime import datetime, timezone

import pandas as pd

import config
from backtest import engine, metrics
from analysis import breakdowns, statistics as stats_mod, charts


def _fmt(x, pct=False, money=False):
    if x is None:
        return "N/A"
    if isinstance(x, float) and (x != x):
        return "N/A"
    if pct:
        return f"{x*100:.2f}%"
    if money:
        return f"${x:,.2f}"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)


def run():
    model, results, features, (train_t, val_t, test_t) = engine.run_baseline_backtest()

    test_pf = results["test"]
    test_trades = test_pf.to_frame()
    test_metrics = metrics.compute_metrics(test_trades, test_pf.starting_bankroll)
    win_ci = metrics.bootstrap_ci(test_trades, metric="win_rate")
    roi_ci = metrics.bootstrap_ci(test_trades, metric="roi")
    sig = stats_mod.win_rate_significance(test_trades)

    bks = breakdowns.all_breakdowns(test_trades, test_pf.starting_bankroll)

    sweep_df, n_edge_combos = stats_mod.min_edge_sweep(
        features, model, test_t, config.DEFAULT_POSITION_SIZE_FRACTION, config.STARTING_BANKROLL)
    size_df, n_size_combos = stats_mod.position_size_sweep(
        features, model, test_t, config.MIN_EDGE, config.STARTING_BANKROLL)

    os.makedirs(config.CHARTS_DIR, exist_ok=True)
    time_bk = bks.get("time_remaining")
    charts.make_all_charts(test_trades, test_pf.starting_bankroll, time_bk)

    for name, bdf in bks.items():
        bdf.to_csv(os.path.join(config.REPORTS_DIR, f"breakdown_{name}.csv"), index=False)
    sweep_df.to_csv(os.path.join(config.REPORTS_DIR, "min_edge_sweep.csv"), index=False)
    size_df.to_csv(os.path.join(config.REPORTS_DIR, "position_size_sweep.csv"), index=False)

    # ---- verdict logic (honest, sample-size aware) ----
    n_trades = test_metrics["n_trades"]
    roi = test_metrics["roi"]
    win_rate = test_metrics["win_rate"]
    verdict = "INCONCLUSIVE"
    reasoning = []
    if n_trades < 100:
        verdict = "INCONCLUSIVE"
        reasoning.append(
            f"Only {n_trades} test-split trades were generated from the small "
            f"({config.SYNTHETIC_DAYS}-day) demo sample -- far too few for statistical "
            f"confidence in either direction."
        )
    elif roi is not None and roi > 0 and win_ci[0] is not None and win_ci[0] > 0.5:
        verdict = "PRELIMINARY YES (requires real-data confirmation)"
    elif roi is not None and roi < 0:
        verdict = "NO EDGE OBSERVED (on this sample)"
        reasoning.append(f"Test-split ROI was negative ({_fmt(roi, pct=True)}).")
    reasoning.append(
        "CRITICALLY: this entire dataset is SYNTHETIC DEMO DATA, not real Kalshi "
        "market history (see 'Data Sources & Limitations' below). No conclusion here "
        "generalizes to real markets."
    )

    lines = []
    lines.append("# Final Report -- BTC 15-Minute Kalshi Strategy Backtest\n")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
    lines.append("## VERDICT\n")
    lines.append(f"**{verdict}**\n")
    for r in reasoning:
        lines.append(f"- {r}")
    lines.append("")

    lines.append("## Data Sources & Limitations (READ THIS FIRST)\n")
    if config.DATA_MODE == "synthetic_demo":
        lines.append(
            "**This backtest runs on SYNTHETIC DEMO DATA, not real historical Kalshi "
            "market data.** In the sandboxed environment this project was built in, the "
            "network egress proxy blocked every attempt to reach Kalshi's API "
            "(api.elections.kalshi.com, trading-api.kalshi.com, docs.kalshi.com -- "
            "HTTP 403 on CONNECT) and every public crypto-exchange/price API tried "
            "(Binance, Coinbase, CoinGecko, Kraken, Bitstamp, Gemini, Yahoo Finance, "
            "stooq.com -- all HTTP 403 on CONNECT). Alpha Vantage's MCP integration was "
            "reachable, but its intraday endpoints (CRYPTO_INTRADAY, TIME_SERIES_INTRADAY) "
            "returned a 'premium endpoint' rate_limit error on every interval tried "
            "(1min/5min/15min/60min) -- gated behind a paid tier not available here.\n\n"
            "The **only real, verified market data obtainable was daily BTC/USD OHLCV** "
            "via Alpha Vantage's DIGITAL_CURRENCY_DAILY endpoint (free tier), saved "
            "untouched at `data/raw/btc_daily_real.csv` (raw API response also saved at "
            "`data/raw/_alphavantage_btc_daily_raw_response.json`). That real daily series "
            "was used only to CALIBRATE (drift/volatility) a seeded, reproducible, "
            "geometric-Brownian-motion synthetic minute-level BTC price path "
            "(`data/raw/btc_1min_SYNTHETIC.csv`), from which synthetic Kalshi-style 15-"
            "minute contract quotes were derived using a documented barrier-probability "
            "formula (`data/raw/kalshi_15min_contracts_SYNTHETIC.csv`). Every synthetic "
            "row is tagged `is_synthetic=True` and every synthetic filename carries a "
            "`_SYNTHETIC` suffix.\n\n"
            "**No part of this backtest's numeric results (win rate, ROI, edge, etc.) "
            "should be interpreted as evidence about real Kalshi markets.** The sole "
            "purpose of this run is to demonstrate the pipeline (download -> clean -> "
            "feature-engineer -> walk-forward backtest -> report) is architected and "
            "wired correctly end-to-end, ready to be pointed at real data the moment "
            "it's obtainable (e.g. from a network environment that can reach Kalshi's "
            "API and a non-premium intraday crypto price source).\n"
        )
    lines.append(
        f"Synthetic sample size: **{config.SYNTHETIC_DAYS} days**, "
        f"{config.SYNTHETIC_DAYS*1440} synthetic minute bars, "
        f"{features['ticker'].nunique()} synthetic 15-minute contract windows.\n"
    )
    lines.append(
        "Execution assumption: no real limit-order-book data exists (real or synthetic) "
        "-- entries transact at the modeled `yes_ask`/`no_ask` (fair probability +/- half "
        f"a {config.SYNTHETIC_SPREAD_CENTS:.2f}-wide modeled spread). Kalshi fee formula "
        f"(fee = ceil(0.07 * C * P * (1-P)) per side) is from general knowledge of "
        "Kalshi's public fee schedule and is **UNVERIFIED-LIVE** in this environment "
        "since docs.kalshi.com was network-blocked -- flagged in config.py "
        "(`FEE_SCHEDULE_VERIFIED_LIVE = False`).\n"
    )

    lines.append("## Dataset\n")
    lines.append(f"- Period (synthetic): {config.SYNTHETIC_START} + {config.SYNTHETIC_DAYS} days")
    lines.append(f"- Contracts (15-min windows): {features['ticker'].nunique()}")
    lines.append(f"- Chronological split: train={len(train_t)}, validation={len(val_t)}, test={len(test_t)} contracts")
    lines.append(f"- Entry decision points used: {config.ENTRY_MINUTES_REMAINING} minutes-remaining "
                 f"(0.5m unavailable at minute resolution -- see engine log / README)\n")

    lines.append("## Baseline Model (Strategy A)\n")
    lines.append(f"- Mode: **{model.mode}** (features: {config.BASELINE_FEATURES})\n")

    lines.append("## Test-Split Results (primary, out-of-sample)\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| # Trades | {test_metrics['n_trades']} |")
    lines.append(f"| Win rate | {_fmt(test_metrics['win_rate'], pct=True)} |")
    lines.append(f"| Avg PnL/trade | {_fmt(test_metrics['avg_pnl'], money=True)} |")
    lines.append(f"| Net profit | {_fmt(test_metrics['net_profit'], money=True)} |")
    lines.append(f"| ROI | {_fmt(test_metrics['roi'], pct=True)} |")
    lines.append(f"| Max drawdown | {_fmt(test_metrics['max_drawdown'], money=True)} ({_fmt(test_metrics['max_drawdown_pct'], pct=True)}) |")
    lines.append(f"| Drawdown duration (trades) | {test_metrics['drawdown_duration_trades']} |")
    lines.append(f"| Worst losing streak | {test_metrics['worst_losing_streak']} |")
    lines.append(f"| Best winning streak | {test_metrics['best_winning_streak']} |")
    lines.append(f"| Avg edge | {_fmt(test_metrics['avg_edge'], pct=True)} |")
    lines.append(f"| Median edge | {_fmt(test_metrics['median_edge'], pct=True)} |")
    lines.append(f"| Profit factor | {_fmt(test_metrics['profit_factor'])} |")
    lines.append(f"| Brier score | {_fmt(test_metrics['brier_score'])} |")
    lines.append(f"| Log loss | {_fmt(test_metrics['log_loss'])} |")
    lines.append("")
    lines.append(f"- Bootstrap 95% CI on win rate: [{_fmt(win_ci[0], pct=True)}, {_fmt(win_ci[1], pct=True)}] (2000 resamples)")
    lines.append(f"- Bootstrap 95% CI on per-trade PnL mean: [${win_ci[0] if False else roi_ci[0]:.2f}, ${roi_ci[1]:.2f}]" if roi_ci[0] is not None else "- Bootstrap CI on PnL: N/A (no trades)")
    lines.append(f"- Binomial test win rate vs 50%: n={sig['n']}, wins={sig['wins']}, p-value={_fmt(sig['p_value'])}\n")

    lines.append("## Train / Validation Results (for comparison, overfitting check)\n")
    for split_name in ["train", "validation"]:
        pf = results[split_name]
        m = metrics.compute_metrics(pf.to_frame(), pf.starting_bankroll)
        lines.append(f"- **{split_name}**: n={m['n_trades']}, win_rate={_fmt(m['win_rate'], pct=True)}, "
                     f"roi={_fmt(m['roi'], pct=True)}, brier={_fmt(m['brier_score'])}")
    lines.append("")

    lines.append("## Parameter Sweeps (multiple-testing disclosure)\n")
    lines.append(f"MIN_EDGE sweep tried **{n_edge_combos} combinations**: {config.MIN_EDGE_SWEEP}. "
                 f"Position-size sweep tried **{n_size_combos} combinations**: {config.POSITION_SIZE_FRACTIONS}. "
                 f"Both sweeps were run on the SAME test split as the headline result above -- "
                 f"picking the best-performing threshold from this sweep post-hoc would be a "
                 f"multiple-testing / data-snooping error; the headline result above uses the "
                 f"pre-registered config defaults (MIN_EDGE={config.MIN_EDGE}, "
                 f"position_fraction={config.DEFAULT_POSITION_SIZE_FRACTION}), not the sweep's best value.\n")
    lines.append("MIN_EDGE sweep (test split):\n")
    lines.append(sweep_df[["min_edge", "n_trades", "win_rate", "roi", "profit_factor"]].to_markdown(index=False))
    lines.append("\nPosition-size sweep (test split):\n")
    lines.append(size_df[["position_fraction", "n_trades", "win_rate", "roi", "max_drawdown_pct"]].to_markdown(index=False))
    lines.append("")

    lines.append("## Breakdowns\n")
    for name, bdf in bks.items():
        lines.append(f"### By {name.replace('_',' ')}\n")
        cols = [c for c in ["bucket", "n", "win_rate", "roi", "avg_edge"] if c in bdf.columns]
        lines.append(bdf[cols].to_markdown(index=False) if len(bdf) else "_no trades in this split_")
        lines.append("")

    lines.append("## Charts\n")
    lines.append("See `results/charts/`: equity_curve.png, drawdown.png, edge_vs_return.png, "
                 "calibration_curve.png, results_by_time_remaining.png.\n")

    lines.append("## Overfitting Concerns\n")
    lines.append(
        "- Sample size is tiny (7 synthetic days, ~670 contracts, ~135 test trades); any "
        "apparent edge or lack thereof carries wide statistical uncertainty (see bootstrap CIs).\n"
        "- The baseline model was fit on synthetic data generated from a probability formula "
        "that is structurally similar to the heuristic fallback in models/baseline.py -- on "
        "synthetic data a model can appear well-calibrated almost by construction, which would "
        "NOT transfer to real markets with real microstructure, fees, latency, and adverse "
        "selection. This is a fundamental reason results here are demo-only.\n"
        "- Parameter sweeps were run on the same test split as headline metrics (see 'Parameter "
        "Sweeps' above) -- reported for transparency, not used to cherry-pick the headline result.\n"
    )

    lines.append("## Next Steps (deliberately NOT done in this pass)\n")
    lines.append(
        "- Strategy B (`models/logistic.py`, full-feature calibrated logistic regression) and "
        "Strategy C (`models/ml_models.py`, random forest / gradient boosting, currently a stub "
        "that raises NotImplementedError) are intentionally not run. Per project instructions, "
        "the pipeline stops after this baseline pass for user review.\n"
        "- Before any of this is meaningful, this project needs: (1) real Kalshi historical "
        "market/trade data from a network environment that can reach Kalshi's API, and (2) "
        "real intraday (1-minute or better) BTC price data from a non-premium source.\n"
    )

    with open(config.FINAL_REPORT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[report_builder] Wrote {config.FINAL_REPORT}")


if __name__ == "__main__":
    run()
