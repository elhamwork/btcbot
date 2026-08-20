"""
Strategy C - random forest / gradient boosting.

NOT YET RUN, and deliberately so.

Two reasons beyond the specification's instruction to stop after the baseline:

1. The same gate applies. The market's mid-price scored a Brier of 0.1353 on
   the test split. A gradient-boosted model that cannot beat that number is
   not a trading strategy, however good its accuracy looks.

2. Sample size. 1,320 contracts over 14 days, split chronologically, leaves
   roughly 790 training contracts. That is enough to fit a flexible model and
   nowhere near enough to trust it. Fitting one now would mostly measure how
   well it memorises two weeks of August.

If this is revisited, collect a longer history first, keep the chronological
split, calibrate on validation only, and report the number of configurations
tried in results/reports/search_log.csv.
"""
