"""Performance and probability-quality metrics."""

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

import config


def performance(trades, starting_bankroll=None):
    b0 = config.STARTING_BANKROLL if starting_bankroll is None else starting_bankroll
    if trades is None or trades.empty:
        return {"trades": 0, "note": "no trades generated"}

    t = trades.sort_values("close_time").reset_index(drop=True)
    pnl = t["profit_loss"]
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]

    equity = pd.concat([pd.Series([b0]), t["bankroll"]], ignore_index=True)
    peak = equity.cummax()
    dd = equity - peak
    dd_pct = dd / peak

    # longest stretch below a previous peak
    under = (dd < 0).astype(int)
    dur, best_dur = 0, 0
    for u in under:
        dur = dur + 1 if u else 0
        best_dur = max(best_dur, dur)

    streak_w = streak_l = cur_w = cur_l = 0
    for w in t["won"]:
        if w:
            cur_w, cur_l = cur_w + 1, 0
        else:
            cur_l, cur_w = cur_l + 1, 0
        streak_w, streak_l = max(streak_w, cur_w), max(streak_l, cur_l)

    gross_win = wins.sum()
    gross_loss = -losses.sum()
    invested = t["stake"].sum() + t["fees"].sum()

    return {
        "trades": len(t),
        "wins": int(t["won"].sum()),
        "losses": int((~t["won"].astype(bool)).sum()),
        "win_rate": float(t["won"].mean()),
        "avg_profit": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "net_profit": float(pnl.sum()),
        "roi_on_bankroll": float(pnl.sum() / b0),
        "roi_on_turnover": float(pnl.sum() / invested) if invested else 0.0,
        "final_bankroll": float(t["bankroll"].iloc[-1]),
        "max_drawdown_dollars": float(dd.min()),
        "max_drawdown_pct": float(dd_pct.min()),
        "drawdown_duration_trades": int(best_dur),
        "return_volatility": float(pnl.std()),
        "worst_losing_streak": int(streak_l),
        "best_winning_streak": int(streak_w),
        "avg_entry_price": float(t["entry_price"].mean()),
        "avg_edge": float(t["edge"].mean()),
        "median_edge": float(t["edge"].median()),
        "avg_holding_minutes": float(t["minutes_remaining"].mean()),
        "profit_per_trade": float(pnl.mean()),
        "profit_factor": float(gross_win / gross_loss) if gross_loss > 0 else np.inf,
        "total_fees": float(t["fees"].sum()),
        "turnover": float(invested),
    }


def probability_quality(df, p_col="p_yes", y_col="y"):
    d = df[[p_col, y_col]].dropna()
    if d.empty or d[y_col].nunique() < 2:
        return {"n": len(d), "note": "insufficient variation"}
    p, y = d[p_col].to_numpy(float), d[y_col].to_numpy(int)
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    return {
        "n": len(d),
        "brier": float(brier_score_loss(y, pc)),
        "log_loss": float(log_loss(y, pc)),
        "roc_auc": float(roc_auc_score(y, pc)),
        "accuracy": float(((pc >= 0.5).astype(int) == y).mean()),
        "base_rate": float(y.mean()),
        "mean_prediction": float(pc.mean()),
    }


def calibration_table(df, p_col="p_yes", y_col="y", bins=10):
    d = df[[p_col, y_col]].dropna().copy()
    if d.empty:
        return pd.DataFrame()
    d["bin"] = pd.cut(d[p_col], np.linspace(0, 1, bins + 1),
                      include_lowest=True)
    g = d.groupby("bin", observed=True).agg(
        n=(y_col, "size"),
        predicted=(p_col, "mean"),
        actual=(y_col, "mean"),
    ).reset_index()
    g["gap"] = g["actual"] - g["predicted"]
    return g
