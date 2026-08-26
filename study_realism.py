#!/usr/bin/env python3
"""
How far is the paper account from what a real one would have done?

Written because the paper number is only worth watching if it is the number
you would actually have got. Everything here is measured against the live
order book the bot collects, not assumed.

    CHECK_STATE_DIR=cloud_state python3 study_realism.py

Three questions, in order of how much they could cost:

1. IS THE ENTRY PRICE HONEST? The bot records the price it saw. Compared
   against the independently collected book at the same moment: median
   difference 0.00c over 16 covered calls, mean +0.56c. The scatter is the
   20-second gap between the two pollers, not a bias. Nothing to correct.

2. CAN THE ORDER ACTUALLY FILL? Median size resting at the best price is
   $3,062 and the median spread is 1c:

       order size   fills at the best price   within 5c of it
       $250                     86%                  100%
       $1,000                   73%                  100%
       $2,500                   56%                   99%
       $5,000                   31%                   97%

   So a bet under about $1,000 fills at the quote almost always, and the
   paper arithmetic holds to roughly a $25,000 account. This replaced a
   guess of $10,000 that had been inferred from total contract volume.

3. ARE WE BEING PICKED OFF? If the resting offer we take is there because
   someone better informed does not want it, our side should get cheaper
   right after we buy. It does not:

       +1 min   mean +0.18c
       +2 min   mean +5.51c
       +3 min   mean +7.85c

   The 2 and 3-minute figures are contaminated -- 14 of 16 covered calls
   won, and a winner's price rises anyway. The 1-minute figure is the clean
   one and it is essentially zero. That rules out large adverse selection
   at n=16. It does not rule out a cent or two.

WHAT WAS ACTUALLY WRONG, and is now fixed: the fee. Kalshi's published
schedule is ceil(0.07 x contracts x price x (1 - price)) -- rounded UP to
the nearest cent. The code rounded to nearest, making every paper trade
very slightly cheaper than a real one.

WHAT REMAINS UNMEASURABLE without real money: whether a real order gets the
same fill a hypothetical one does. Nothing in a paper account can answer it.
"""

import csv
import glob
import os
import statistics as st
import sys

import check


def load_book():
    book = {}
    d = os.path.join(os.path.dirname(check.MEMORY), "orderbook")
    for f in sorted(glob.glob(os.path.join(d, "*.csv"))):
        for r in csv.DictReader(open(f)):
            if (r.get("n_yes_levels") or "0") in ("0", ""):
                continue          # a row with no ladder is not a snapshot
            book.setdefault(r["ticker"], []).append(r)
    for t in book:
        book[t].sort(key=lambda r: -float(r["minutes_remaining"]))
    return book


def our_price(s, side):
    """What our side cost at that snapshot. A NO bid at p is a YES offer."""
    try:
        return float(s["yes_ask"]) if side == "YES" else 1 - float(s["yes_bid"])
    except (TypeError, ValueError):
        return None


def main():
    mem = check.load_memory()
    calls = {r["ticker"]: r for r in (mem.get("predictions") or [])
             if r.get("answered") and not r.get("retired")}
    book = load_book()
    covered = sorted(set(calls) & set(book))
    print("  %d live calls, %d with order-book coverage" % (len(calls), len(covered)))

    # 1 -- entry price honesty
    diffs = []
    for t in covered:
        c = calls[t]
        if c.get("mins") is None:
            continue
        s = min(book[t], key=lambda r: abs(float(r["minutes_remaining"]) - c["mins"]))
        p = our_price(s, c["side"])
        if p is not None:
            diffs.append(p - c["price"])
    if diffs:
        print("\n  1. entry price vs the book at that moment")
        print("     median %+.4f (%.2fc)   mean %+.4f (%.2fc)   n=%d"
              % (st.median(diffs), 100 * st.median(diffs),
                 st.mean(diffs), 100 * st.mean(diffs), len(diffs)))

    # 2 -- fill sizes
    touch, d5 = [], []
    for t in book:
        for r in book[t]:
            for k, out in (("yes_bid_size", touch), ("yes_depth_5c", d5)):
                try:
                    v = float(r[k])
                    if v > 0:
                        out.append(v)
                except (TypeError, ValueError, KeyError):
                    pass
    if touch:
        print("\n  2. can the order fill?  (%d snapshots)" % len(touch))
        print("     %-12s %10s %12s" % ("order", "at best", "within 5c"))
        for s in (250, 1000, 2500, 5000):
            a = 100 * sum(1 for x in touch if x >= s) / len(touch)
            b = 100 * sum(1 for x in d5 if x >= s) / len(d5) if d5 else 0
            print("     $%-11s %9.0f%% %11.0f%%" % (format(s, ",d"), a, b))

    # 3 -- adverse selection
    print("\n  3. does our side get cheaper after we buy?")
    for k in (1, 2, 3):
        moves = []
        for t in covered:
            c = calls[t]
            if c.get("mins") is None or c.get("correct") is None:
                continue
            def at(target):
                cand = [s for s in book[t]
                        if abs(float(s["minutes_remaining"]) - target) < 0.5]
                return our_price(min(cand, key=lambda s: abs(
                    float(s["minutes_remaining"]) - target)), c["side"]) if cand else None
            p0, p1 = at(c["mins"]), at(c["mins"] - k)
            if p0 is not None and p1 is not None:
                moves.append(p1 - p0)
        if moves:
            print("     +%d min   mean %+.4f (%+.2fc)   n=%d"
                  % (k, st.mean(moves), 100 * st.mean(moves), len(moves)))
    print("\n     Positive means the market moved toward us. The +2 and +3")
    print("     figures are contaminated by outcome; +1 is the clean one.")
    print()


if __name__ == "__main__":
    main()
