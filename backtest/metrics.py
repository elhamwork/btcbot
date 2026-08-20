"""backtest/metrics.py -- performance & calibration metrics."""

import numpy as np
import pandas as pd


def compute_metrics(trades_df, starting_bankroll):
    if trades_df is None or len(trades_df) == 0:
        return {
            "n_trades": 0, "win_rate": None, "avg_pnl": None, "net_profit": 0.0,
            "roi": 0.0, "max_drawdown": 0.0, "max_drawdown_pct": 0.0,
            "drawdown_duration_trades": 0, "worst_losing_streak": 0,
            "best_winning_streak": 0, "avg_edge": None, "median_edge": None,
            "profit_factor": None, "brier_score": None, "log_loss": None,
        }

    n_trades = len(trades_df)
    wins = trades_df["won"]
    win_rate = wins.mean()
    avg_pnl = trades_df["pnl"].mean()
    net_profit = trades_df["pnl"].sum()
    roi = net_profit / starting_bankroll

    equity = starting_bankroll + trades_df["pnl"].cumsum()
    running_max = equity.cummax()
    drawdown = equity - running_max
    max_dd = drawdown.min()
    max_dd_pct = (drawdown / running_max).min()

    in_dd = drawdown < 0
    dd_duration = 0
    cur = 0
    for v in in_dd:
        cur = cur + 1 if v else 0
        dd_duration = max(dd_duration, cur)

    streak, best_win, worst_loss = 0, 0, 0
    cur_win_streak, cur_loss_streak = 0, 0
    for w in wins:
        if w:
            cur_win_streak += 1
            cur_loss_streak = 0
        else:
            cur_loss_streak += 1
            cur_win_streak = 0
        best_win = max(best_win, cur_win_streak)
        worst_loss = max(worst_loss, cur_loss_streak)

    avg_edge = trades_df["edge"].mean()
    median_edge = trades_df["edge"].median()

    gross_win = trades_df.loc[trades_df["pnl"] > 0, "pnl"].sum()
    gross_loss = -trades_df.loc[trades_df["pnl"] < 0, "pnl"].sum()
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (np.inf if gross_win > 0 else None)

    # Brier score & log loss: model_prob for the side taken vs. outcome (1=won,0=lost)
    p = trades_df.apply(lambda r: r["model_prob"] if r["side"] == "YES" else 1 - r["model_prob"], axis=1)
    y = wins.astype(int)
    brier = float(np.mean((p - y) ** 2))
    eps = 1e-9
    pc = p.clip(eps, 1 - eps)
    logloss = float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc)))

    return {
        "n_trades": n_trades,
        "win_rate": float(win_rate),
        "avg_pnl": float(avg_pnl),
        "net_profit": float(net_profit),
        "roi": float(roi),
        "max_drawdown": float(max_dd),
        "max_drawdown_pct": float(max_dd_pct) if pd.notna(max_dd_pct) else 0.0,
        "drawdown_duration_trades": int(dd_duration),
        "worst_losing_streak": int(worst_loss),
        "best_winning_streak": int(best_win),
        "avg_edge": float(avg_edge),
        "median_edge": float(median_edge),
        "profit_factor": float(profit_factor) if profit_factor not in (None, np.inf) else profit_factor,
        "brier_score": brier,
        "log_loss": logloss,
    }


def bootstrap_ci(trades_df, metric="win_rate", n_boot=2000, ci=0.95, seed=0):
    """Bootstrap confidence interval on win_rate or roi across trades."""
    if trades_df is None or len(trades_df) == 0:
        return (None, None)
    rng = np.random.RandomState(seed)
    n = len(trades_df)
    vals = trades_df["won"].astype(int).values if metric == "win_rate" else trades_df["pnl"].values
    boot_stats = []
    for _ in range(n_boot):
        sample = vals[rng.randint(0, n, n)]
        boot_stats.append(sample.mean())
    lo = np.percentile(boot_stats, (1 - ci) / 2 * 100)
    hi = np.percentile(boot_stats, (1 + ci) / 2 * 100)
    return (float(lo), float(hi))
