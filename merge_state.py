#!/usr/bin/env python3
"""
merge_state.py -- combine two copies of the bot's memory.

    python3 merge_state.py MINE THEIRS OUT

Two watchers can hold the memory at once: a scheduled cloud run that started
before the previous one saved, a laptop and a runner, a re-run after a
cancel. Whichever committed last used to win outright, so a real settled call
could vanish -- which is exactly what happened on 2026-08-23, when a run that
had reached $1,038.77 was about to be overwritten by one that started from a
stale $1,000 checkout.

The fix is to stop treating the derived numbers as facts. The only fact is
`predictions`: one record per contract, keyed by ticker. Everything else --
the calibration bins, the paper account, every stake -- is recomputed from
that list here. Two forks of the memory then merge cleanly: union the
predictions, replay, done. Order no longer decides who wins.

Standard library only.
"""

import json
import sys

N_BINS = 20
PAPER_START = 1000.0
PAPER_STAKE = 0.10
FEE_RATE = 0.07


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:                                         # noqa: BLE001
        return {}


def better(a, b):
    """Of two records for the same contract, keep the one that knows more."""
    if a is None:
        return b
    if b is None:
        return a
    # A deliberate retirement beats everything. When the rule changes, old
    # calls are struck from the money record on purpose -- and a watcher
    # still running the previous code must not quietly reinstate them by
    # merging its own copy back in.
    if a.get("retired") != b.get("retired"):
        return a if a.get("retired") else b
    # A settled record beats an unsettled one; a call beats a decline.
    for key in ("outcome", "answered"):
        av, bv = a.get(key), b.get(key)
        if bool(av) != bool(bv) or (av is None) != (bv is None):
            return a if (av is not None and av is not False) else b
    return a


def rebuild(preds):
    """Recompute the bins and the paper account from the predictions alone."""
    bins_n = [0.0] * N_BINS
    bins_wins = [0.0] * N_BINS
    bank = {"cash": PAPER_START, "start": PAPER_START, "peak": PAPER_START,
            "low": PAPER_START, "settled": 0, "fees": 0.0}

    def when(r):
        return str(r.get("close_time") or r.get("asked") or "")

    for rec in sorted(preds, key=when):
        y = rec.get("outcome")
        if y is None:
            rec.pop("paid", None)
            rec.pop("bank_after", None)
            continue
        # A recovered record is one reconstructed by hand from an alert after
        # its memory was lost. The settled side, price and outcome are all
        # verifiable, so it counts for the paper account and the call log --
        # but the raw pre-calibration number is NOT recoverable from an alert,
        # and guessing it would quietly corrupt the calibration table with a
        # made-up value. Recovered records therefore teach nothing.
        if not rec.get("recovered"):
            b = min(int(float(rec.get("raw", 0.0)) * N_BINS), N_BINS - 1)
            bins_n[b] += 1.0
            bins_wins[b] += 1.0 if y == 1 else 0.0
        if not rec.get("answered") or rec.get("retired"):
            continue
        price = float(rec.get("price") or 0.0)
        if not 0.0 < price < 1.0:
            continue
        won = bool(rec.get("correct"))
        stake = round(bank["cash"] * PAPER_STAKE, 2)
        contracts = stake / price
        fee = round(FEE_RATE * contracts * price * (1 - price), 2)
        rec["bet"] = {"stake": stake, "contracts": round(contracts, 1),
                      "fee": fee, "to_win": round(contracts * (1 - price) - fee, 2),
                      "bank_before": round(bank["cash"], 2)}
        paid = (contracts - stake - fee) if won else (-stake - fee)
        bank["cash"] = round(bank["cash"] + paid, 2)
        bank["peak"] = round(max(bank["peak"], bank["cash"]), 2)
        bank["low"] = round(min(bank["low"], bank["cash"]), 2)
        bank["settled"] += 1
        bank["fees"] = round(bank["fees"] + fee, 2)
        rec["paid"] = round(paid, 2)
        rec["bank_after"] = bank["cash"]
    return bins_n, bins_wins, bank


def merge(mine, theirs):
    by_ticker = {}
    for src in (theirs, mine):        # mine second so it wins ties
        for rec in src.get("predictions") or []:
            t = rec.get("ticker")
            if not t:
                continue
            by_ticker[t] = better(by_ticker.get(t), rec)
    preds = sorted(by_ticker.values(),
                   key=lambda r: str(r.get("close_time") or r.get("asked") or ""))
    bins_n, bins_wins, bank = rebuild(preds)
    out = dict(mine)
    out["predictions"] = preds[-2000:]
    out["bins_n"], out["bins_wins"], out["bank"] = bins_n, bins_wins, bank
    out["polls"] = mine.get("polls") or {}
    seen = set(mine.get("alerted") or []) | set(theirs.get("alerted") or [])
    out["alerted"] = sorted(seen)[-200:]
    return out


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__.strip())
    mine, theirs, out = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
    merged = merge(mine, theirs)
    with open(out, "w") as f:
        json.dump(merged, f, indent=1)
    b = merged["bank"]
    print("  merged %d + %d -> %d contracts, %d settled calls, account $%s"
          % (len(mine.get("predictions") or []),
             len(theirs.get("predictions") or []),
             len(merged["predictions"]), b["settled"],
             format(round(b["cash"], 2), ",.2f")))


if __name__ == "__main__":
    main()
