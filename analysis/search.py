"""
Systematic strategy search, with the discipline built in.

TWO RULES THIS ENFORCES
=======================
1. THE BRIER GATE. A model must beat the market's own mid-price as a
   probability estimate before its trading results mean anything. A model
   worse than the price it bets against can only win by luck.

2. STABILITY OVER PEAK. A candidate is ranked by its WORST split, not its
   best. A configuration that earns +22% on test and -29% on train is noise,
   and ranking by test would promote exactly that. Requiring every period to
   agree is the cheapest defence against fooling ourselves on a short sample.

Every configuration evaluated is written to results/reports/search_log.csv so
the number of things tried is on the record, not hidden.
"""

import itertools
import os

import numpy as np
import pandas as pd

import config
from backtest import engine, metrics
from data import loader
from models import baseline, ml_models


def candidates():
    """Every model configuration to evaluate. Kept explicit and countable."""
    out = [
        ("market-mid (reference)", lambda: baseline.MarketBaseline()),
        ("A0 analytic GBM", lambda: baseline.AnalyticBaseline()),
        ("A logistic (baseline feats)",
         lambda: baseline.LogisticBaseline(config.FEATURES_BASELINE)),
        ("B logistic (technical feats)",
         lambda: baseline.LogisticBaseline(config.FEATURES_TECHNICAL)),
        ("C gradient boosting",
         lambda: ml_models.DirectClassifier("gb", config.FEATURES_TECHNICAL)),
        ("C random forest",
         lambda: ml_models.DirectClassifier("rf", config.FEATURES_TECHNICAL)),
    ]
    for kind in ("ridge", "gb", "rf"):
        for shrink in (1.0, 0.5, 0.25):
            out.append((
                "R residual-%s shrink=%.2f" % (kind, shrink),
                (lambda k=kind, s=shrink: ml_models.ResidualModel(
                    k, config.FEATURES_TECHNICAL, shrink=s))))
    return out


def evaluate(min_edges=None, position_fraction=None):
    panel = loader.load_panel()
    train, valid, test = loader.chronological_split(panel)
    min_edges = min_edges or config.MIN_EDGE_SWEEP
    pf = position_fraction or config.POSITION_FRACTION

    market_brier = {}
    for nm, d in (("train", train), ("validation", valid), ("test", test)):
        sc = engine.score_predictions(d, baseline.MarketBaseline())
        market_brier[nm] = metrics.probability_quality(sc)["brier"]

    rows = []
    for label, make in candidates():
        model = make()
        try:
            model.fit(train, valid)
        except Exception as exc:                       # noqa: BLE001
            rows.append({"model": label, "error": str(exc)[:120]})
            continue

        briers = {}
        for nm, d in (("train", train), ("validation", valid), ("test", test)):
            sc = engine.score_predictions(d, model)
            briers[nm] = metrics.probability_quality(sc).get("brier", np.nan)

        beats_gate = all(briers[k] < market_brier[k]
                         for k in ("train", "validation", "test"))

        for me in min_edges:
            r = {"model": label, "min_edge": me, "position_fraction": pf,
                 "brier_train": briers["train"],
                 "brier_validation": briers["validation"],
                 "brier_test": briers["test"],
                 "market_brier_test": market_brier["test"],
                 "beats_market_brier_everywhere": beats_gate}
            rois, trades = [], []
            for nm, d in (("train", train), ("validation", valid), ("test", test)):
                tr, _ = engine.run(d, model, min_edge=me, position_fraction=pf)
                p = metrics.performance(tr)
                r["roi_%s" % nm] = p.get("roi_on_bankroll", np.nan)
                r["trades_%s" % nm] = p.get("trades", 0)
                r["winrate_%s" % nm] = p.get("win_rate", np.nan)
                rois.append(p.get("roi_on_bankroll", np.nan))
                trades.append(p.get("trades", 0))
            r["worst_split_roi"] = np.nanmin(rois) if any(trades) else np.nan
            r["all_splits_positive"] = bool(
                all(t > 0 for t in trades) and all((x or -1) > 0 for x in rois))
            r["min_trades"] = min(trades)
            rows.append(r)

    df = pd.DataFrame(rows)
    df.to_csv(config.SEARCH_LOG, index=False)
    return df, market_brier


def report(df, market_brier):
    print("=" * 78)
    print("  STRATEGY SEARCH -- %d configurations evaluated" % len(df))
    print("=" * 78)

    print("\nGATE 1 -- beat the market's own Brier score on every split")
    print("  market Brier:  train %.4f | validation %.4f | test %.4f"
          % (market_brier["train"], market_brier["validation"],
             market_brier["test"]))
    print()
    per_model = df.drop_duplicates("model")
    for _, r in per_model.iterrows():
        if "brier_test" not in r or pd.isna(r.get("brier_test")):
            continue
        mark = "PASS" if r["beats_market_brier_everywhere"] else "fail"
        print("  [%s] %-32s train %.4f  val %.4f  test %.4f"
              % (mark, r["model"], r["brier_train"],
                 r["brier_validation"], r["brier_test"]))

    passed = df[df["beats_market_brier_everywhere"].fillna(False)]
    print("\n  %d of %d models clear the gate."
          % (passed["model"].nunique(), per_model["model"].nunique()))

    print("\nGATE 2 -- profitable on ALL THREE periods (not just the best one)")
    stable = df[df["all_splits_positive"].fillna(False) & (df["min_trades"] >= 20)]
    if stable.empty:
        print("  Nothing. No configuration is profitable on train, validation")
        print("  and test simultaneously with at least 20 trades per split.")
    else:
        s = stable.sort_values("worst_split_roi", ascending=False).head(10)
        print("  %-32s %6s  %8s %8s %8s" % ("model", "edge", "train", "valid", "test"))
        for _, r in s.iterrows():
            print("  %-32s %5.0f%%  %+7.2f%% %+7.2f%% %+7.2f%%"
                  % (r["model"], 100 * r["min_edge"], 100 * r["roi_train"],
                     100 * r["roi_validation"], 100 * r["roi_test"]))

    print("\nFor contrast -- ranked by TEST ROI alone (the wrong way to choose):")
    t = df.dropna(subset=["roi_test"]).sort_values("roi_test", ascending=False).head(5)
    for _, r in t.iterrows():
        print("  %-32s edge %2.0f%%  test %+7.2f%%  but train %+7.2f%%"
              % (r["model"], 100 * r["min_edge"], 100 * r["roi_test"],
                 100 * r["roi_train"]))
    print("\n  Picking from that list is how backtests lie.")
    print("\nFull log: %s" % config.SEARCH_LOG)
    return stable
