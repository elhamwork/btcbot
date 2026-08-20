#!/usr/bin/env python3
"""
main.py -- CLI entry point.

    python main.py --download
    python main.py --prepare-data
    python main.py --backtest baseline
    python main.py --backtest technical   (NOT IMPLEMENTED YET -- see README)
    python main.py --backtest ml          (NOT IMPLEMENTED YET -- see README)
    python main.py --report
"""

import argparse
import os
import sys

import config


def cmd_download(args):
    from data import downloader
    downloader.run()


def cmd_prepare_data(args):
    from data import cleaner
    cleaner.run()
    from features import feature_engine
    feature_engine.run()


def cmd_backtest(args):
    if args.backtest == "baseline":
        _run_baseline_backtest()
    elif args.backtest == "technical":
        print("[main] Strategy B (technical, full-feature logistic) is NOT run in this "
              "pass, per project instructions: stop after the baseline backtest completes "
              "and let the user review before continuing. models/logistic.py is written "
              "and ready but not wired into a `--backtest technical` run yet.")
        sys.exit(2)
    elif args.backtest == "ml":
        print("[main] Strategy C (ML models) is a documented stub -- see models/ml_models.py. "
              "Not implemented in this pass (sample too small / synthetic data).")
        sys.exit(2)


def _run_baseline_backtest():
    import pandas as pd
    from backtest import engine, metrics

    model, results, features, splits = engine.run_baseline_backtest()
    os.makedirs(config.TRADES_DIR, exist_ok=True)

    print("\n" + "=" * 70)
    print("BASELINE BACKTEST RESULTS (Strategy A)")
    print("=" * 70)
    for split_name, pf in results.items():
        tdf = pf.to_frame()
        m = metrics.compute_metrics(tdf, pf.starting_bankroll)
        print(f"\n--- {split_name.upper()} split ---")
        for k, v in m.items():
            print(f"  {k}: {v}")
        out_csv = os.path.join(config.TRADES_DIR, f"baseline_trades_{split_name}.csv")
        tdf.to_csv(out_csv, index=False)
        print(f"  (trades saved -> {out_csv})")

    print("\n[main] Baseline backtest complete. Run `python main.py --report` for full "
          "breakdowns, charts, and the final report.")


def cmd_report(args):
    from analysis import report_builder
    report_builder.run()


def main():
    parser = argparse.ArgumentParser(description="BTC 15-min Kalshi strategy backtester")
    parser.add_argument("--download", action="store_true", help="Download/generate data")
    parser.add_argument("--prepare-data", action="store_true", help="Clean data + build features")
    parser.add_argument("--backtest", choices=["baseline", "technical", "ml"], help="Run a backtest")
    parser.add_argument("--report", action="store_true", help="Generate breakdowns/charts/final report")
    args = parser.parse_args()

    if not any([args.download, args.prepare_data, args.backtest, args.report]):
        parser.print_help()
        return

    if args.download:
        cmd_download(args)
    if args.prepare_data:
        cmd_prepare_data(args)
    if args.backtest:
        cmd_backtest(args)
    if args.report:
        cmd_report(args)


if __name__ == "__main__":
    main()
