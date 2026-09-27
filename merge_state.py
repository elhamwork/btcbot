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
import os
import sys
import math

N_BINS = 20
PAPER_START = 1000.0
PAPER_STAKE = 0.10
LOOK_CAP = 2000   # must match check.py
REVENGE_FRACTION = 0.50   # must match check.py
FEE_RATE = 0.07


def load(path):
    """
    Read one copy of the memory.

    A MISSING file is legitimately empty -- the first run ever, or a side
    that has nothing yet -- and merges as {}. A file that EXISTS but will
    not parse is something else entirely, and must never be treated as
    "no trades": on 2026-09-27 it was, and it cost the whole account.

    What happened: merge_state.py wrote its output with a plain open(w),
    which is not atomic, so a shorter write over a longer file left 662
    bytes of the previous file's tail dangling after the new JSON ended.
    The next run read that, hit "Extra data", quietly returned {} here,
    merged nothing with nothing, replayed an empty ledger, and published a
    brand-new $1,000 account over a real $3,012 one with 430 settled calls.
    Recovered from git, but only because git happened to have it.

    So: a corrupt file is fatal now. Stop, say so, touch nothing. A crashed
    merge leaves the branch alone; a silent one overwrites history.
    """
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        text = f.read()
    try:
        return json.loads(text)
    except ValueError as e:
        sys.exit("  REFUSING TO MERGE: %s is corrupt (%s).\n"
                 "  Not overwriting anything. The good copy is still on the\n"
                 "  branch and in git history; fix or delete this file."
                 % (path, e))


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
        # A revenge trade (see check.py, REVENGE_FRACTION) has no raw/p of
        # its own -- it shares a ticker with that contract's normal look,
        # which already feeds the bins once. Skip it here too, same as
        # check.py's settle_pending does, or the contract gets double-counted.
        if not rec.get("recovered") and rec.get("raw") is not None:
            b = min(int(float(rec["raw"]) * N_BINS), N_BINS - 1)
            bins_n[b] += 1.0
            bins_wins[b] += 1.0 if y == 1 else 0.0
        if not rec.get("answered") or rec.get("retired"):
            continue
        price = float(rec.get("price") or 0.0)
        if not 0.0 < price < 1.0:
            continue
        won = bool(rec.get("correct"))
        # A revenge trade stakes REVENGE_FRACTION of the bank, not the normal
        # PAPER_STAKE -- must match check.py's plan_stake_fraction() or this
        # replay silently erases the 50%-after-a-loss rule and restates
        # every revenge trade as if it had only risked the normal 10%.
        fraction = REVENGE_FRACTION if rec.get("revenge") else PAPER_STAKE
        stake = round(bank["cash"] * fraction, 2)
        contracts = stake / price
        # Kalshi rounds the fee UP to the nearest cent, not to nearest.
        fee = math.ceil(FEE_RATE * contracts * price * (1 - price) * 100) / 100
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


def trim_predictions(preds):
    """
    Cap the never-traded look history; never cap the actual trade ledger.

    Only about 1 look in 8 becomes an actual bet, so a flat "keep the last
    LOOK_CAP records" cap -- which is what this used to be -- quietly
    deletes real trade history once the bot has run longer than the cap
    covers in look-volume. On 2026-09-22 that had already happened: 296
    settled calls on 2026-09-16 had become 259 on 2026-09-22, with the
    oldest real trades pushed out of this very list by newer declines on
    each merge, silently turning "every trade ever made" into a rolling
    ~20-day window. Every stat this project reports depends on that
    history actually accumulating, not resetting.
    """
    bets = [p for p in preds if p.get("bet")]
    looks = [p for p in preds if not p.get("bet")]
    looks.sort(key=lambda r: str(r.get("close_time") or r.get("asked") or ""))
    kept = bets + looks[-LOOK_CAP:]
    kept.sort(key=lambda r: str(r.get("close_time") or r.get("asked") or ""))
    return kept


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
    out["predictions"] = trim_predictions(preds)
    out["bins_n"], out["bins_wins"], out["bank"] = bins_n, bins_wins, bank
    out["polls"] = mine.get("polls") or {}
    seen = set(mine.get("alerted") or []) | set(theirs.get("alerted") or [])
    out["alerted"] = sorted(seen)[-200:]
    return out


def bet_count(state):
    return sum(1 for r in (state.get("predictions") or []) if r.get("bet"))


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__.strip())
    mine, theirs, out = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
    merged = merge(mine, theirs)

    # A merge is a union: it can only ever learn about MORE trades, never
    # fewer. If the result knows about fewer than either side walked in
    # with, something upstream is wrong and writing it would destroy the
    # ledger -- which is exactly the shape of the 2026-09-27 wipe. Refuse.
    # (Belt and braces: load() already makes the corrupt-input case fatal.)
    have = bet_count(merged)
    for name, side in (("mine", mine), ("theirs", theirs)):
        if have < bet_count(side):
            sys.exit("  REFUSING TO WRITE: merge produced %d trades but %s "
                     "already had %d.\n  A merge can only add trades. Not "
                     "overwriting %s." % (have, name, bet_count(side), out))

    # Atomically, so a short write can never leave the tail of the old file
    # dangling after the new JSON -- see load().
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(merged, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, out)
    b = merged["bank"]
    print("  merged %d + %d -> %d contracts, %d settled calls, account $%s"
          % (len(mine.get("predictions") or []),
             len(theirs.get("predictions") or []),
             len(merged["predictions"]), b["settled"],
             format(round(b["cash"], 2), ",.2f")))


if __name__ == "__main__":
    main()
