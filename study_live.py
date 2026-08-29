#!/usr/bin/env python3
"""
Ask the live record whether losses share anything.

Every filter tried on this project failed the same way: fitted to a handful
of losses, then worse on trades it had not seen. This exists so the question
can eventually be asked with enough calls to answer it, and so that the
answer is computed the same way every time rather than re-argued.

    CHECK_STATE_DIR=cloud_state python3 study_live.py

It prints a split for every recorded field and, next to each, how often a gap
that large happens by chance if every call came from one process. Read the
last column first. Anything under 20% on a sample this size is a story.
"""

import os
import random
import sys

import check

random.seed(0)
TRIALS = 20000


def by_chance(rows, key, cut):
    """How often pure luck produces a win-rate gap this large."""
    a = [r for r in rows if r.get(key) is not None and r[key] < cut]
    b = [r for r in rows if r.get(key) is not None and r[key] >= cut]
    if len(a) < 5 or len(b) < 5:
        return None
    real = abs(sum(r["correct"] for r in a) / len(a)
               - sum(r["correct"] for r in b) / len(b))
    p = sum(r["correct"] for r in rows) / len(rows)
    hits = 0
    na = len(a)
    for _ in range(TRIALS):
        s = [random.random() < p for _ in range(len(rows))]
        x, y = s[:na], s[na:]
        if abs(sum(x) / len(x) - sum(y) / len(y)) >= real:
            hits += 1
    return a, b, 100.0 * hits / TRIALS


def show(rows, key, cut, label):
    got = by_chance(rows, key, cut)
    if not got:
        return
    a, b, chance = got
    for g, side in ((a, "below"), (b, "at/above")):
        w = sum(r["correct"] for r in g)
        be = 100 * sum(r["price"] for r in g) / len(g)
        print("  %-22s %-9s %3d  %2d-%-2d  %5.1f%%  be %4.1f%%  margin %+5.1f"
              % (label if side == "below" else "", side, len(g), w, len(g) - w,
                 100 * w / len(g), be, 100 * w / len(g) - be))
    print("  %-22s %s by chance: %.0f%%\n"
          % ("", " " * 9, chance))


def main():
    mem = check.load_memory()
    rows = [r for r in (mem.get("predictions") or [])
            if r.get("answered") and not r.get("retired")
            and r.get("correct") is not None]
    if not rows:
        sys.exit("  No settled calls yet.")
    have = [r for r in rows if r.get("cross_15") is not None]
    w = sum(r["correct"] for r in rows)
    print("\n  %d settled calls, %d-%d (%.1f%%)"
          % (len(rows), w, len(rows) - w, 100 * w / len(rows)))
    print("  %d of them carry the extra context fields\n" % len(have))
    if len(have) < 20:
        print("  Not enough yet. These fields started being recorded on")
        print("  2026-08-29; every call from now on carries them. Come back")
        print("  at a few hundred and this will mean something.\n")
        if not have:
            return
    for key, cut, label in (("cross_15", 3, "crossings (15m) <3"),
                            ("cross_30", 6, "crossings (30m) <6"),
                            ("vol_ratio", 1.0, "vol vs its own median"),
                            ("spread", 0.02, "spread <2c"),
                            ("hour_utc", 12, "hour before/after 12 UTC"),
                            ("bid_size", 1000, "bid size <$1000"),
                            ("edge", 0.10, "edge <10%"),
                            ("price", 0.80, "price <80c")):
        show(have, key, cut, label)
    print("  A reminder of why the last column is there: nine separate")
    print("  filters have looked convincing on small samples and every one")
    print("  did worse on data it had not seen.\n")


if __name__ == "__main__":
    main()
