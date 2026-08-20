"""Charts. Saved to results/charts/."""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import config
from backtest import metrics, portfolio

INK = "#1c1c1c"
ACCENT = "#2b6cb0"
WARN = "#c05621"
GRID = "#d8d8d8"


def _style(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=12, color=INK, pad=10)
    ax.set_xlabel(xlabel, fontsize=9, color=INK)
    ax.set_ylabel(ylabel, fontsize=9, color=INK)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8, colors=INK)


def _save(fig, name):
    path = os.path.join(config.CHARTS_DIR, name)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def equity_curve(trades, label="test"):
    eq = portfolio.equity_curve(trades)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    if eq.empty:
        ax.text(.5, .5, "no trades", ha="center", transform=ax.transAxes)
    else:
        ax.plot(eq["close_time"], eq["bankroll"], color=ACCENT, linewidth=1.6)
        ax.axhline(config.STARTING_BANKROLL, color=INK, linewidth=.9,
                   linestyle="--", alpha=.6)
    _style(ax, "Bankroll over time (%s)" % label, "", "Bankroll ($)")
    fig.autofmt_xdate()
    return _save(fig, "equity_curve.png")


def drawdown(trades, label="test"):
    eq = portfolio.equity_curve(trades)
    fig, ax = plt.subplots(figsize=(9, 3.4))
    if not eq.empty:
        ax.fill_between(eq["close_time"], eq["drawdown_pct"] * 100, 0,
                        color=WARN, alpha=.35)
        ax.plot(eq["close_time"], eq["drawdown_pct"] * 100, color=WARN, linewidth=1.1)
    _style(ax, "Drawdown (%s)" % label, "", "Drawdown (%)")
    fig.autofmt_xdate()
    return _save(fig, "drawdown.png")


def edge_vs_return(trades, label="test"):
    fig, ax = plt.subplots(figsize=(7, 4.4))
    if not trades.empty:
        per = trades["profit_loss"] / trades["stake"].replace(0, np.nan)
        ax.scatter(trades["edge"] * 100, per * 100, s=16, alpha=.45,
                   color=ACCENT, edgecolors="none")
        t = trades.copy()
        t["b"] = np.floor(t["edge"] * 100 / 2.5) * 2.5
        g = t.groupby("b").apply(
            lambda d: (d["profit_loss"].sum() / d["stake"].sum()) * 100,
            include_groups=False)
        ax.plot(g.index + 1.25, g.values, color=WARN, linewidth=1.8,
                marker="o", markersize=4, label="mean return per bucket")
        ax.axhline(0, color=INK, linewidth=.9, alpha=.6)
        ax.legend(fontsize=8, frameon=False)
    _style(ax, "Predicted edge vs realised return (%s)" % label,
           "Predicted edge (%)", "Return per dollar staked (%)")
    return _save(fig, "edge_vs_return.png")


def calibration(scored, label="test", model_name="model"):
    tab = metrics.calibration_table(scored)
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    ax.plot([0, 1], [0, 1], color=INK, linestyle="--", linewidth=.9, alpha=.6,
            label="perfect")
    if not tab.empty:
        ax.plot(tab["predicted"], tab["actual"], marker="o", markersize=5,
                color=ACCENT, linewidth=1.6, label=model_name)
        for _, r in tab.iterrows():
            ax.annotate("%d" % r["n"], (r["predicted"], r["actual"]),
                        textcoords="offset points", xytext=(4, -9),
                        fontsize=6.5, color="#666")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    _style(ax, "Calibration (%s)" % label,
           "Predicted P(YES)", "Actual frequency")
    return _save(fig, "calibration_curve.png")


def results_by_time(breakdown, label="test"):
    fig, ax = plt.subplots(figsize=(7.5, 4))
    if breakdown is not None and not breakdown.empty:
        x = np.arange(len(breakdown))
        vals = breakdown["profit_per_trade"].to_numpy(float)
        ax.bar(x, vals, color=[ACCENT if v >= 0 else WARN for v in vals],
               width=.62)
        ax.set_xticks(x)
        ax.set_xticklabels(breakdown.iloc[:, 0].astype(str), fontsize=8)
        ax.axhline(0, color=INK, linewidth=.9)
        for xi, v, n in zip(x, vals, breakdown["trades"]):
            ax.annotate("n=%d" % n, (xi, v), ha="center", fontsize=7,
                        color="#555",
                        xytext=(0, 4 if v >= 0 else -11),
                        textcoords="offset points")
    _style(ax, "Profit per trade by time remaining (%s)" % label,
           "Minutes remaining at entry", "Profit per trade ($)")
    return _save(fig, "results_by_time_remaining.png")


def generate_all(trades, scored, breakdowns, label="test", model_name="model"):
    return [
        equity_curve(trades, label),
        drawdown(trades, label),
        edge_vs_return(trades, label),
        calibration(scored, label, model_name),
        results_by_time(breakdowns.get("time_remaining"), label),
    ]
