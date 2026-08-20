"""analysis/charts.py -- matplotlib charts saved to results/charts/."""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

WATERMARK = "SYNTHETIC DEMO DATA -- not real Kalshi market data" if config.DATA_MODE == "synthetic_demo" else None


def _watermark(fig):
    if WATERMARK:
        fig.text(0.5, 0.5, WATERMARK, fontsize=22, color="red", alpha=0.18,
                  ha="center", va="center", rotation=30)


def equity_curve(trades_df, starting_bankroll, out_path):
    fig, ax = plt.subplots(figsize=(9, 5))
    if trades_df is not None and len(trades_df):
        equity = starting_bankroll + trades_df["pnl"].cumsum()
        ax.plot(range(len(equity)), equity, color="#2b6cb0")
        ax.axhline(starting_bankroll, color="gray", linestyle="--", linewidth=1)
    ax.set_title("Equity Curve (Baseline Strategy, Test Split)")
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Bankroll ($)")
    _watermark(fig)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def drawdown_curve(trades_df, starting_bankroll, out_path):
    fig, ax = plt.subplots(figsize=(9, 5))
    if trades_df is not None and len(trades_df):
        equity = starting_bankroll + trades_df["pnl"].cumsum()
        running_max = equity.cummax()
        dd = equity - running_max
        ax.fill_between(range(len(dd)), dd, 0, color="#c53030", alpha=0.6)
    ax.set_title("Drawdown Over Time (Baseline Strategy, Test Split)")
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Drawdown ($)")
    _watermark(fig)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def edge_vs_return_scatter(trades_df, out_path):
    fig, ax = plt.subplots(figsize=(7, 6))
    if trades_df is not None and len(trades_df):
        colors = np.where(trades_df["pnl"] >= 0, "#2f855a", "#c53030")
        ax.scatter(trades_df["edge"], trades_df["pnl"], c=colors, alpha=0.6, s=20)
    ax.axhline(0, color="gray", linewidth=1)
    ax.set_title("Edge vs. Trade Return")
    ax.set_xlabel("Model Edge (model_prob - market_ask)")
    ax.set_ylabel("PnL ($)")
    _watermark(fig)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def calibration_curve(trades_df, out_path, n_bins=10):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="perfect calibration")
    if trades_df is not None and len(trades_df):
        p = trades_df.apply(lambda r: r["model_prob"] if r["side"] == "YES" else 1 - r["model_prob"], axis=1)
        y = trades_df["won"].astype(int)
        bins = np.linspace(0, 1, n_bins + 1)
        idx = np.digitize(p, bins) - 1
        xs, ys = [], []
        for b in range(n_bins):
            mask = idx == b
            if mask.sum() > 0:
                xs.append(p[mask].mean())
                ys.append(y[mask].mean())
        ax.plot(xs, ys, "o-", color="#2b6cb0", label="model")
    ax.set_title("Calibration Curve")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.legend()
    _watermark(fig)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def results_by_time_remaining(breakdown_df, out_path):
    fig, ax = plt.subplots(figsize=(8, 5))
    if breakdown_df is not None and len(breakdown_df):
        d = breakdown_df.sort_values("bucket")
        ax.bar(d["bucket"].astype(str), d["roi"].fillna(0), color="#805ad5")
    ax.set_title("ROI by Minutes-Remaining-At-Entry")
    ax.set_xlabel("Minutes remaining at entry")
    ax.set_ylabel("ROI")
    _watermark(fig)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def make_all_charts(trades_df, starting_bankroll, time_breakdown_df):
    os.makedirs(config.CHARTS_DIR, exist_ok=True)
    equity_curve(trades_df, starting_bankroll, os.path.join(config.CHARTS_DIR, "equity_curve.png"))
    drawdown_curve(trades_df, starting_bankroll, os.path.join(config.CHARTS_DIR, "drawdown.png"))
    edge_vs_return_scatter(trades_df, os.path.join(config.CHARTS_DIR, "edge_vs_return.png"))
    calibration_curve(trades_df, os.path.join(config.CHARTS_DIR, "calibration_curve.png"))
    results_by_time_remaining(time_breakdown_df, os.path.join(config.CHARTS_DIR, "results_by_time_remaining.png"))
    print(f"[charts] Wrote 5 charts -> {config.CHARTS_DIR}")
