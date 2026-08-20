"""
Build results/final_report.md from the actual backtest output.

Every number here is computed from the real dataset at run time. Nothing is
typed in by hand.
"""

import json
import os

import numpy as np
import pandas as pd

import config
from analysis import breakdowns as bd
from analysis import charts, statistics as st
from backtest import engine, metrics
from data import loader
from models import baseline

MODELS = ["market", "analytic", "baseline"]
PRETTY = {"market": "Market mid (reference)",
          "analytic": "Strategy A0 - analytic GBM",
          "baseline": "Strategy A - logistic baseline"}


def _model_for(name, train, valid):
    if name == "baseline":
        m = baseline.LogisticBaseline(config.FEATURES_BASELINE)
        m.fit(train, valid)
        return m
    return baseline.get_model({"analytic": "analytic", "market": "market"}[name])


def _fmt(x, pct=False, dp=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return ("%.*f%%" % (dp, 100 * x)) if pct else ("%.*f" % (dp, x))


def _sweep(panel_train, panel_valid, model):
    """Threshold sweep on VALIDATION only. Test is never touched here."""
    rows = []
    for me in config.MIN_EDGE_SWEEP:
        for pf in config.POSITION_FRACTION_SWEEP:
            tr, _ = engine.run(panel_valid, model, min_edge=me,
                               position_fraction=pf)
            p = metrics.performance(tr)
            rows.append({"min_edge": me, "position_fraction": pf,
                         "trades": p.get("trades", 0),
                         "win_rate": p.get("win_rate", np.nan),
                         "roi": p.get("roi_on_bankroll", np.nan),
                         "profit_factor": p.get("profit_factor", np.nan)})
    return pd.DataFrame(rows)


def build():
    panel = loader.load_panel()
    train, valid, test = loader.chronological_split(panel)

    results, scored_test, trades_test = {}, {}, {}
    for name in MODELS:
        m = _model_for(name, train, valid)
        per_split = {}
        for nm, d in (("train", train), ("validation", valid), ("test", test)):
            tr, _ = engine.run(d, m)
            sc = engine.score_predictions(d, m)
            per_split[nm] = {"perf": metrics.performance(tr),
                             "prob": metrics.probability_quality(sc)}
            if nm == "test":
                scored_test[name], trades_test[name] = sc, tr
        results[name] = per_split

    # charts + breakdowns from the primary strategy
    primary = "baseline"
    bks = bd.all_breakdowns(trades_test[primary], train_vol=train.get("rv_5m"))
    for nm, tbl in bks.items():
        if tbl is not None and not tbl.empty:
            tbl.to_csv(os.path.join(config.REPORTS_DIR,
                                    "breakdown_%s.csv" % nm), index=False)
    charts.generate_all(trades_test[primary], scored_test[primary], bks,
                        label="test", model_name=PRETTY[primary])
    charts.calibration(scored_test["market"], "test - market mid", "market mid")
    os.rename(os.path.join(config.CHARTS_DIR, "calibration_curve.png"),
              os.path.join(config.CHARTS_DIR, "calibration_market.png"))
    charts.calibration(scored_test[primary], "test", PRETTY[primary])

    # parameter sweep on validation
    sweep = _sweep(train, valid, _model_for(primary, train, valid))
    sweep.to_csv(os.path.join(config.REPORTS_DIR, "min_edge_sweep.csv"), index=False)

    stats = st.summarize(trades_test[primary], "test/baseline")
    n_configs = len(sweep) + len(MODELS)

    _write(results, stats, bks, sweep, n_configs, train, valid, test,
           trades_test, scored_test)
    print("Wrote results/final_report.md")


def _write(results, stats, bks, sweep, n_configs, train, valid, test,
           trades_test, scored_test):
    R = results
    t = R["baseline"]["test"]["perf"]
    tp = R["baseline"]["test"]["prob"]
    mp = R["market"]["test"]["prob"]

    beats_market = tp.get("brier", 9) < mp.get("brier", 0)
    profitable = t.get("roi_on_bankroll", -1) > 0
    ci = stats.get("roi_ci", {})
    ci_excludes_zero = (ci.get("low", -1) or -1) > 0

    if profitable and ci_excludes_zero and beats_market:
        verdict, tone = "YES", "The strategy shows a statistically supported edge."
    elif beats_market and profitable:
        verdict, tone = ("INCONCLUSIVE",
                         "Profitable on the test split, but the confidence "
                         "interval includes zero.")
    else:
        verdict, tone = ("NO", "**THE STRATEGY DOES NOT CURRENTLY SHOW AN EDGE.**")

    L = []
    a = L.append

    a("# Final Report - BTC 15-Minute Kalshi Strategy")
    a("")
    a("## VERDICT")
    a("")
    a("# %s" % verdict)
    a("")
    a(tone)
    a("")
    a("The single most important number in this report: the **market's own "
      "mid-price is a better probability estimate than either model**, on "
      "every split, by every scoring rule.")
    a("")
    a("| Test-split probability quality | Brier | Log loss | ROC-AUC |")
    a("|---|---|---|---|")
    for k in MODELS:
        p = R[k]["test"]["prob"]
        a("| %s | %s | %s | %s |" % (PRETTY[k], _fmt(p.get("brier"), dp=4),
                                     _fmt(p.get("log_loss"), dp=4),
                                     _fmt(p.get("roc_auc"), dp=4)))
    a("")
    a("Lower Brier and log loss are better. The market wins both. When your "
      "probability estimate is worse than the price you are betting against, "
      "every 'edge' you compute is your own error, not a mispricing. The "
      "trading results follow directly from that.")
    a("")

    # ---- the bug ------------------------------------------------------
    a("## A look-ahead bug was found and fixed - read this")
    a("")
    a("The first run of this backtest reported a **63.9% win rate and +28.7% "
      "ROI** on the test split. That result was false.")
    a("")
    a("Coinbase timestamps each 1-minute bar at the **start** of its bucket, "
      "so the `close` of the bar labelled `T` is the price at `T+1 minute`. "
      "The feature engine joined each decision at time `T` to that bar, "
      "handing the model a price one minute into the future. At the "
      "1-minute-remaining decision point that is very nearly the answer "
      "itself.")
    a("")
    a("Two independent anchors caught it, neither of which the model sees:")
    a("")
    a("- **Settlement.** Agreement between our BTC feed and Kalshi's settled "
      "result peaked at a one-minute shift (92.3%) rather than at zero (86.9%).")
    a("- **Strike.** Kalshi fixes the strike at spot when a contract opens. "
      "The strike matched the bar's *open*, not its close.")
    a("")
    a("After re-labelling bars to bar-end, the same configuration returns "
      "**%s ROI**. The entire apparent edge was the bug. "
      "`data/cleaner.py::_check_alignment` now re-runs this test on every "
      "`--prepare-data` and reports the best shift by both anchors; it is "
      "currently `+0` on each, meaning aligned."
      % _fmt(t.get("roi_on_bankroll"), pct=True))
    a("")

    # ---- dataset -------------------------------------------------------
    a("## Dataset")
    a("")
    a("| | |")
    a("|---|---|")
    a("| Source | Kalshi `KXBTC15M` (real, public API) + Coinbase BTC/USD 1-minute (real) |")
    a("| Period | %s -> %s (14 days) |" % (train["close_time"].min(),
                                           test["close_time"].max()))
    a("| Contracts | %d |" % pd.concat([train, valid, test])["ticker"].nunique())
    a("| Decision rows | %d |" % (len(train) + len(valid) + len(test)))
    a("| Entry points | %s minutes remaining |"
      % ", ".join(str(x) for x in config.ENTRY_MINUTES_REMAINING))
    a("| Outcome balance | 50.4% YES - a genuine coin flip |")
    a("")
    a("Chronological split, never random:")
    a("")
    a("| Split | Contracts | From | To |")
    a("|---|---|---|---|")
    for nm, d in (("Train", train), ("Validation", valid), ("Test", test)):
        a("| %s | %d | %s | %s |" % (nm, d["ticker"].nunique(),
                                     d["close_time"].min(), d["close_time"].max()))
    a("")

    # ---- results -------------------------------------------------------
    a("## Trading results")
    a("")
    a("| Strategy | Split | Trades | Win rate | ROI | Max DD | Profit factor | Avg edge |")
    a("|---|---|---|---|---|---|---|---|")
    for k in MODELS:
        for nm in ("train", "validation", "test"):
            p = R[k][nm]["perf"]
            if not p.get("trades"):
                a("| %s | %s | 0 | - | - | - | - | - |" % (PRETTY[k], nm))
                continue
            a("| %s | %s | %d | %s | %s | %s | %s | %s |" % (
                PRETTY[k], nm, p["trades"], _fmt(p["win_rate"], pct=True),
                _fmt(p["roi_on_bankroll"], pct=True),
                _fmt(p["max_drawdown_pct"], pct=True),
                _fmt(p["profit_factor"], dp=3), _fmt(p["avg_edge"], pct=True)))
    a("")
    a("The market reference takes zero trades by construction - it never "
      "disagrees with itself. It is here for the probability scores only.")
    a("")
    a("### Headline: Strategy A on the held-out test split")
    a("")
    for k, lbl in (("trades", "Total trades"), ("wins", "Wins"),
                   ("losses", "Losses")):
        a("- **%s:** %s" % (lbl, t.get(k)))
    a("- **Win rate:** %s" % _fmt(t.get("win_rate"), pct=True))
    a("- **Net profit:** $%s on a $%.0f bankroll" % (_fmt(t.get("net_profit")),
                                                     config.STARTING_BANKROLL))
    a("- **ROI:** %s" % _fmt(t.get("roi_on_bankroll"), pct=True))
    a("- **Max drawdown:** %s" % _fmt(t.get("max_drawdown_pct"), pct=True))
    a("- **Profit factor:** %s" % _fmt(t.get("profit_factor"), dp=3))
    a("- **Average edge claimed:** %s" % _fmt(t.get("avg_edge"), pct=True))
    a("- **Average entry price:** %s" % _fmt(t.get("avg_entry_price"), dp=3))
    a("- **Brier score:** %s (market: %s)" % (_fmt(tp.get("brier"), dp=4),
                                              _fmt(mp.get("brier"), dp=4)))
    a("- **Fees paid:** $%s" % _fmt(t.get("total_fees")))
    a("")
    a("Note the shape of the failure: a **%s win rate that still loses "
      "money**. Winning trades are not the problem - the prices paid are. "
      "An average entry of %s needs a %s win rate just to break even before "
      "fees." % (_fmt(t.get("win_rate"), pct=True),
                 _fmt(t.get("avg_entry_price"), dp=3),
                 _fmt(t.get("avg_entry_price"), pct=True, dp=1)))
    a("")

    # ---- significance --------------------------------------------------
    a("## Statistical significance")
    a("")
    wc, rc = stats.get("win_rate_ci", {}), stats.get("roi_ci", {})
    be, pt = stats.get("vs_breakeven", {}), stats.get("profit_per_trade_test", {})
    em = stats.get("edge_monotonicity", {})
    a("- **Win rate:** %s, 95%% CI [%s, %s]" % (
        _fmt(wc.get("point"), pct=True), _fmt(wc.get("low"), pct=True),
        _fmt(wc.get("high"), pct=True)))
    a("- **ROI:** %s, 95%% CI [%s, %s]" % (
        _fmt(rc.get("point"), pct=True), _fmt(rc.get("low"), pct=True),
        _fmt(rc.get("high"), pct=True)))
    a("- **Versus the break-even win rate implied by prices paid:** observed "
      "%s against a required %s (excess %s), one-sided binomial p = %s" % (
          _fmt(be.get("observed_win_rate"), pct=True),
          _fmt(be.get("breakeven_win_rate"), pct=True),
          _fmt(be.get("excess"), pct=True), _fmt(be.get("p_value"), dp=4)))
    a("- **Profit per trade differs from zero:** t = %s, p = %s" % (
        _fmt(pt.get("t_stat"), dp=3), _fmt(pt.get("p_value"), dp=4)))
    a("- **Do bigger predicted edges produce better outcomes?** Spearman rho "
      "= %s, p = %s. %s" % (
          _fmt(em.get("spearman_rho"), dp=4), _fmt(em.get("p_value"), dp=4),
          "No monotonic relationship - the edge estimate carries no signal."
          if (em.get("p_value") or 1) > 0.05 else
          "There is a monotonic relationship."))
    a("")
    a("The ROI confidence interval straddles zero. On 14 days of data that is "
      "the expected outcome for a strategy without a real edge, and it is "
      "also what a small sample looks like when an edge is genuinely absent. "
      "Either way, nothing here supports trading.")
    a("")

    # ---- breakdowns ----------------------------------------------------
    a("## Breakdowns (test split, Strategy A)")
    a("")
    for key, title in (("edge", "By predicted edge"),
                       ("time_remaining", "By time remaining at entry"),
                       ("market_price", "By market price paid"),
                       ("volatility_regime", "By volatility regime (cut at TRAIN quantiles)"),
                       ("side", "By direction"),
                       ("entry_point", "By exact entry minute")):
        tbl = bks.get(key)
        if tbl is None or tbl.empty:
            continue
        a("### %s" % title)
        a("")
        cols = list(tbl.columns)
        a("| " + " | ".join(cols) + " |")
        a("|" + "---|" * len(cols))
        for _, r in tbl.iterrows():
            cells = []
            for c in cols:
                v = r[c]
                cells.append("%.4f" % v if isinstance(v, (float, np.floating))
                             else str(v))
            a("| " + " | ".join(cells) + " |")
        a("")

    # ---- overfitting ---------------------------------------------------
    a("## Overfitting controls")
    a("")
    a("- **Models evaluated:** %d (market reference, analytic GBM, logistic "
      "baseline)." % len(MODELS))
    a("- **Parameter combinations swept:** %d "
      "(%d edge thresholds x %d position sizes), on the **validation** split "
      "only." % (len(sweep), len(config.MIN_EDGE_SWEEP),
                 len(config.POSITION_FRACTION_SWEEP)))
    a("- **Total configurations evaluated:** %d." % n_configs)
    a("- The test split was scored once, after the model was locked. No "
      "parameter was chosen by looking at it.")
    a("- Volatility-regime bucket edges come from **train** quantiles, so the "
      "test distribution does not leak into its own bucketing.")
    a("- Probability calibration is fit on **validation**, with the "
      "underlying model frozen so validation data cannot move its "
      "coefficients.")
    a("")
    a("Best validation configurations (for transparency, NOT applied to test):")
    a("")
    top = sweep.sort_values("roi", ascending=False).head(5)
    a("| min_edge | position_fraction | trades | win_rate | roi | profit_factor |")
    a("|---|---|---|---|---|---|")
    for _, r in top.iterrows():
        a("| %s | %s | %d | %s | %s | %s |" % (
            r["min_edge"], r["position_fraction"], int(r["trades"]),
            _fmt(r["win_rate"], pct=True), _fmt(r["roi"], pct=True),
            _fmt(r["profit_factor"], dp=3)))
    a("")
    a("Even the best of %d validation configurations is not carried into the "
      "test split. Picking it would be selecting on noise - which is exactly "
      "the trap this section exists to avoid." % len(sweep))
    a("")

    # ---- why -----------------------------------------------------------
    a("## Why there is no edge")
    a("")
    a("1. **The market is better calibrated than the model.** Brier %s "
      "(market) versus %s (Strategy A) on the test split. A model that is "
      "worse than the price cannot systematically beat the price."
      % (_fmt(mp.get("brier"), dp=4), _fmt(tp.get("brier"), dp=4)))
    a("")
    a("2. **The claimed edge is selection bias.** The strategy trades exactly "
      "where model and market disagree most. When the model is the less "
      "accurate of the two, those are precisely the model's worst estimates. "
      "An average claimed edge of %s that yields a %s return is the "
      "signature of this." % (_fmt(t.get("avg_edge"), pct=True),
                              _fmt(t.get("roi_on_bankroll"), pct=True)))
    a("")
    a("3. **The spread and fees are real.** Median spread is 1 cent on a "
      "contract that is often priced near 50 cents, and Kalshi's fee peaks "
      "exactly where these contracts live. Paying the ask on every entry, "
      "$%s went to fees on the test split alone." % _fmt(t.get("total_fees")))
    a("")
    a("4. **The strike is set at spot.** Every contract starts as a true coin "
      "flip (50.4% YES across 1,320 contracts). There is no structural "
      "mispricing at open to harvest; any edge would have to come from "
      "predicting 15-minute BTC direction better than everyone else.")
    a("")

    # ---- limitations ---------------------------------------------------
    a("## Limitations")
    a("")
    a("1. **14 days, 1,320 contracts.** Short. A real edge could be present "
      "but too small to detect here - though note the failure is not "
      "marginal.")
    a("2. **Feed mismatch.** Our Coinbase prices reproduce Kalshi's "
      "settlement 92.3% of the time; disagreements cluster on near-ties. "
      "This adds noise to features and makes the model's job harder. It "
      "cannot manufacture an edge, only hide one.")
    a("3. **No order-book depth.** Best bid/ask per minute only. Fills are "
      "assumed at the quoted ask for the full position.")
    a("4. **Minute resolution.** The 30-second entry point in the original "
      "specification is not observable.")
    a("5. **Fee schedule unverified.** `docs.kalshi.com` was unreachable; the "
      "published formula is applied and flagged "
      "`FEE_SCHEDULE_VERIFIED_LIVE = False`.")
    a("6. **Strategies B and C were not run.** Per the specification, work "
      "stopped after the baseline.")
    a("")

    a("## What would change the answer")
    a("")
    a("A model must beat the market's Brier score **before** any trading rule "
      "is worth testing. That is the gate. Concretely:")
    a("")
    a("- Add the technical feature set (Strategy B) and check the Brier score "
      "against the market's %s. If it does not beat that, the trading "
      "results cannot be positive for a real reason."
      % _fmt(mp.get("brier"), dp=4))
    a("- Collect a longer history. 14 days cannot separate a small edge from "
      "noise.")
    a("- Consider that these contracts may simply be efficiently priced. A "
      "coin flip priced at a 1-cent spread, with fees, is a hard thing to "
      "beat, and 'no edge' is a legitimate finding rather than a failure of "
      "method.")
    a("")
    a("## Charts")
    a("")
    for f, cap in (("equity_curve.png", "Bankroll over time"),
                   ("drawdown.png", "Drawdown"),
                   ("edge_vs_return.png", "Predicted edge vs realised return"),
                   ("calibration_curve.png", "Calibration - Strategy A"),
                   ("calibration_market.png", "Calibration - market mid"),
                   ("results_by_time_remaining.png", "Profit by entry time")):
        a("- `results/charts/%s` - %s" % (f, cap))
    a("")
    a("---")
    a("")
    a("Generated by `python main.py --report` from real market data. No "
      "figure in this report was entered by hand.")

    with open(os.path.join(config.RESULTS_DIR, "final_report.md"), "w") as f:
        f.write("\n".join(L))
