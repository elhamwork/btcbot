#!/usr/bin/env python3
"""
Fold one order-book collection into another without losing snapshots.

Two collectors overlap on every handover: the incoming cloud run starts while
the outgoing one is still recording, and both hold their own copy of today's
file. The save resets to the branch and would otherwise overwrite one side
outright -- the same failure merge_state.py exists to prevent for the paper
account.

A snapshot is identified by (observed_at, ticker). Same key, same instant,
same contract, so either copy will do -- except that one may have had its
outcome attached by --settle and the other not, and a row with an outcome is
strictly better. Rows are unioned per day file and written back in time order.

    python3 merge_books.py MINE THEIRS OUT

Directories, each holding orderbook/YYYY-MM-DD.csv. OUT may be either input.
Standard library only.
"""

import csv
import os
import sys


def read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def day_files(root):
    d = os.path.join(root, "orderbook")
    try:
        return {f for f in os.listdir(d) if f.endswith(".csv")}
    except OSError:
        return set()


def better(a, b):
    """Prefer the copy that already knows how the contract settled."""
    if (a.get("outcome") or "") and not (b.get("outcome") or ""):
        return a
    if (b.get("outcome") or "") and not (a.get("outcome") or ""):
        return b
    return a


def merge_day(mine, theirs):
    rows = {}
    for r in theirs + mine:
        k = (r.get("observed_at"), r.get("ticker"))
        rows[k] = better(r, rows[k]) if k in rows else r
    return [rows[k] for k in sorted(rows, key=lambda k: (k[0] or "", k[1] or ""))]


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    mine, theirs, out = sys.argv[1:4]
    names = day_files(mine) | day_files(theirs)
    if not names:
        print("  nothing to merge")
        return
    os.makedirs(os.path.join(out, "orderbook"), exist_ok=True)
    total = 0
    for name in sorted(names):
        a = read(os.path.join(mine, "orderbook", name))
        b = read(os.path.join(theirs, "orderbook", name))
        rows = merge_day(a, b)
        # Take the field order from whichever copy has one, so a column added
        # to bookwatch.py later does not silently drop on the next merge.
        fields = list((a or b)[0].keys()) if (a or b) else []
        dst = os.path.join(out, "orderbook", name)
        tmp = dst + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, dst)
        total += len(rows)
        print("  %s  %d + %d -> %d" % (name, len(a), len(b), len(rows)))
    print("  %d snapshots across %d day%s"
          % (total, len(names), "" if len(names) == 1 else "s"))


if __name__ == "__main__":
    main()
