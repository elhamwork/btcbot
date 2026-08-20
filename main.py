#!/usr/bin/env python3
"""
BTC 15-minute Kalshi strategy backtester.

    python main.py --prepare-data
    python main.py --backtest baseline
    python main.py --report

Data collection runs OUTSIDE this CLI, via the standalone scripts
(fetch_15m.py, fetch_btc_prices.py), because the machine doing the analysis
may not be the machine that can reach Kalshi. `--download` explains this.
"""

import argparse
import json
import os
import sys

import pandas as pd

import config


def cmd_download():
    print(__doc__)
    print("Data collection scripts (run where Kalshi is reachable):")
    print("  python3 fetch_15m.py        -> real_data/kalshi_15m_*.csv")
    print("  python3 fetch_btc_prices.py -> real_data/btc_1min.csv")
    print()
    for p, what in ((config.CONTRACTS_CSV, "contracts"),
                    (config.CANDLES_CSV, "candles"),
                    (config.BTC_CSV, "BTC 1-minute")):
        print("  [%s] %-14s %s" % ("ok" if os.path.exists(p) else "MISSING",
                                   what, p))


def cmd_prepare():
    from data import cleaner, loader
    from features import feature_engine

    print("Cleaning + auditing...")
    summary = cleaner.clean()
    for k, v in summary.items():
        print("  %-24s %s" % (k, v))

    contracts, candles, btc = loader.load_clean()

    print("\nVerifying no look-ahead in the feature engine...")
    n, bad, worst = feature_engine.verify_no_lookahead(btc, n_samples=150)
    print("  checked %d timestamps, %d mismatches, worst rel-diff %.2e"
          % (n, bad, worst))
    if bad:
        sys.exit("LOOK-AHEAD DETECTED -- refusing to continue.")

    print("\nBuilding decision panel...")
    panel = feature_engine.build_panel(contracts, candles, btc)
    panel.to_parquet(config.PANEL, index=False)
    print("  %d decision rows over %d contracts"
          % (len(panel), panel["ticker"].nunique()))
    print("  entry points: %s"
          % sorted(panel["minutes_remaining"].unique(), reverse=True))
    print("\nWrote %s" % config.PANEL)
    print("Wrote %s/data_quality_report.md" % config.REPORTS_DIR)


def _fit_model(name, train, valid):
    from models import baseline
    if name == "baseline":
        m = baseline.LogisticBaseline(config.FEATURES_BASELINE)
        m.fit(train, valid)
        return m, "logistic-baseline"
    if name == "analytic":
        return baseline.AnalyticBaseline(), "analytic"
    if name == "market":
        return baseline.MarketBaseline(), "market-mid"
    if name == "technical":
        from models import baseline as _b
        m = _b.LogisticBaseline(config.FEATURES_TECHNICAL)
        m.fit(train, valid)
        return m, "logistic-technical"
    if name == "ml":
        from models import ml_models
        m = ml_models.DirectClassifier("gb", config.FEATURES_TECHNICAL)
        m.fit(train, valid)
        return m, "gradient-boosting"
    if name == "residual":
        from models import ml_models
        m = ml_models.ResidualModel("gb", config.FEATURES_TECHNICAL, shrink=0.5)
        m.fit(train, valid)
        return m, "residual-gb"
    sys.exit("unknown strategy: %s" % name)


def cmd_backtest(strategy):
    from analysis import breakdowns as bd
    from backtest import engine, metrics, portfolio
    from data import loader

    panel = loader.load_panel()
    train, valid, test = loader.chronological_split(panel)
    print("Split (chronological, by contract close time):")
    for nm, d in (("train", train), ("validation", valid), ("test", test)):
        print("  %-11s %6d rows  %4d contracts  %s -> %s"
              % (nm, len(d), d["ticker"].nunique(),
                 d["close_time"].min(), d["close_time"].max()))

    model, model_name = _fit_model(strategy, train, valid)
    print("\nModel: %s" % model_name)

    out = {}
    for nm, d in (("train", train), ("validation", valid), ("test", test)):
        trades, skipped = engine.run(d, model)
        scored = engine.score_predictions(d, model)
        ok, msg = portfolio.verify_causality(trades)
        if not ok:
            sys.exit("BANKROLL CAUSALITY VIOLATION: %s" % msg)

        perf = metrics.performance(trades)
        prob = metrics.probability_quality(scored)
        out[nm] = {"performance": perf, "probability": prob,
                   "skipped": skipped.to_dict("records")[0] if not skipped.empty else {}}

        if not trades.empty:
            trades.to_csv(os.path.join(
                config.TRADES_DIR, "%s_trades_%s.csv" % (strategy, nm)), index=False)

        print("\n[%s] %d trades" % (nm.upper(), perf.get("trades", 0)))
        if perf.get("trades"):
            print("  win rate %.2f%%   ROI %.2f%%   profit factor %.3f"
                  % (100 * perf["win_rate"], 100 * perf["roi_on_bankroll"],
                     perf["profit_factor"]))
            print("  net $%.2f   max DD %.2f%%   avg edge %.2f%%"
                  % (perf["net_profit"], 100 * perf["max_drawdown_pct"],
                     100 * perf["avg_edge"]))
        print("  Brier %.4f  log-loss %.4f  AUC %.4f  (n=%d)"
              % (prob.get("brier", float("nan")), prob.get("log_loss", float("nan")),
                 prob.get("roc_auc", float("nan")), prob.get("n", 0)))

    # breakdowns on the test set
    test_trades, _ = engine.run(test, model)
    bks = bd.all_breakdowns(test_trades, train_vol=train.get("rv_5m"))
    for nm, tbl in bks.items():
        if tbl is not None and not tbl.empty:
            tbl.to_csv(os.path.join(config.REPORTS_DIR,
                                    "breakdown_%s.csv" % nm), index=False)

    with open(os.path.join(config.REPORTS_DIR,
                           "backtest_%s.json" % strategy), "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("\nWrote results/reports/backtest_%s.json" % strategy)


def cmd_report():
    from analysis import report_builder
    report_builder.build()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download", action="store_true",
                    help="show data-collection status and instructions")
    ap.add_argument("--prepare-data", action="store_true",
                    help="clean, audit, verify causality, build decision panel")
    ap.add_argument("--backtest", metavar="STRATEGY",
                    help="baseline | analytic | market | technical | ml")
    ap.add_argument("--report", action="store_true",
                    help="charts, statistics, and results/final_report.md")
    ap.add_argument("--search", action="store_true",
                    help="systematic strategy search with the Brier gate "
                         "and cross-period stability requirement")
    a = ap.parse_args()

    if a.download:
        cmd_download()
    elif a.prepare_data:
        cmd_prepare()
    elif a.backtest:
        cmd_backtest(a.backtest)
    elif a.report:
        cmd_report()
    elif a.search:
        from analysis import search as _s
        df, mb = _s.evaluate()
        _s.report(df, mb)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
