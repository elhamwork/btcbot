"""
Strategy B - full technical feature set.

NOT YET RUN. Per the project specification, work stopped after the baseline
so the results could be reviewed before adding complexity.

The machinery is already in place: `config.FEATURES_TECHNICAL` lists the
feature set, and `models.baseline.LogisticBaseline` accepts any feature list,
so Strategy B is:

    from models.baseline import LogisticBaseline
    model = LogisticBaseline(config.FEATURES_TECHNICAL)

THE GATE IT MUST CLEAR FIRST
============================
On the test split the market's own mid-price scored a Brier of 0.1353, and
the baseline scored 0.1483 -- worse. A model that is less accurate than the
price it is betting against cannot beat that price for any reason other than
luck.

So Strategy B should be judged on its Brier and log loss against the market
BEFORE any trading rule is applied to it. If it does not beat 0.1353, the
trading results are noise regardless of what the equity curve does.
"""
