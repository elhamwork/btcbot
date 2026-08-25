# btcbot

A bot that watches Kalshi's 15-minute Bitcoin contracts, and when it thinks
the price is wrong, tells my phone. It bets paper money so we can find out
whether it is right.

**It does not trade.** There is no account, no key, no order. It reads public
prices and sends notifications.

<!-- LIVE:BEGIN -->

## Live paper account

**$1,103.08** &nbsp; +10.3% since $1,000 &nbsp;&middot;&nbsp; updated 25 Aug 3:16pm California time

| calls settled | won / lost | win rate | break-even it must beat |
|---|---|---|---|
| 28 | 24 / 4 | 85.7% | 80.8% |

Best $1,141.86, worst $926.64, fees paid $38.96.

### Last 8 calls

| closed | result | paid | account after | side | price |
|---|---|---|---|---|---|
| 25 Aug 11:45am | won | +23.87 | $1,103.08 | NO | 0.81 |
| 25 Aug 9:45am | won | +13.63 | $1,079.21 | YES | 0.88 |
| 25 Aug 6:00am | won | +21.60 | $1,065.58 | YES | 0.82 |
| 25 Aug 5:15am | won | +18.39 | $1,043.98 | NO | 0.84 |
| 25 Aug 4:45am | **LOST** | -116.27 | $1,025.59 | YES | 0.74 |
| 25 Aug 4:00am | won | +11.77 | $1,141.86 | YES | 0.90 |
| 25 Aug 3:00am | won | +29.35 | $1,130.09 | NO | 0.78 |
| 25 Aug 2:15am | won | +20.83 | $1,100.74 | NO | 0.83 |

28 of the roughly 100 settled calls needed before this win rate
means much. Two or three losses in the first dozen is ordinary;
four or more in twenty would say the model is wrong.

Collecting in the background: 2,793 order-book snapshots over 1 day (needs about three weeks).

Paper only: no broker, no account, no orders. Full history in
[`cloud_state/learning_report.md`](cloud_state/learning_report.md).
Rebuilt each time the cloud watcher saves, about once an hour.

<!-- LIVE:END -->

---

## What it actually does

Every 15 minutes Kalshi opens a contract: *will Bitcoin be higher in fifteen
minutes than it is right now?* You can buy YES or NO at whatever the market is
charging, and it pays $1 if you are right and nothing if you are wrong.

The bot works out its own answer from three things: how far Bitcoin is from
the target, how many minutes are left, and how fast it has been moving. If its
answer disagrees with the price by at least 7 cents, and the price is between
70c and 90c, and the disagreement is still there two minutes later, it calls
it and your phone buzzes.

It passes on almost everything. Over 63 days of history it found about four
calls a day out of ninety-six contracts.

## Is it working?

The numbers above are the only honest answer, and there are not enough of them
yet. Roughly 100 settled calls are needed before a win rate means anything.

The 63-day study it was built on: **329 trades, 88.4% right against a 79.9%
break-even.** Whether that survives contact with the live market is exactly
what the account above is testing.

One caveat that belongs next to that number. The historical data holds only
three moments per contract, while the bot polls every fifteen seconds and
sees about twenty-four. So it makes roughly three times as many calls as the
study could evaluate, at instants the data does not contain. Those calls are
not wrong, they are unmeasured, and the live record above is the only
evidence covering them.

Two or three losses in the first dozen calls is ordinary. Four or more in
twenty would say the model is wrong, and I would take it apart rather than
defend it.

## Why it might not work

- **63 days is 63 days.** The edge may not persist.
- **We take the offer.** Someone chose to leave it there. That cost cannot be
  measured from historical prices.
- **Size.** These contracts trade a few hundred dollars over their whole life.
  Past about $10,000 the paper account stops describing anything real.
- **The market is a better forecaster than we are.** Measured, over the same
  63 days. The bot's only claim is one narrow band where its disagreement has
  been worth something.

## What has been tried and thrown away

About 130 ideas. Three survived: the 70-90c band, the 7-cent threshold, and
the two-minute confirmation. The rejections are written down with their
numbers rather than forgotten -- in the header of `check.py` and in
[the literature review](results/reports/literature_review.md).

A few worth knowing about, because they are the obvious things to suggest:

| idea | verdict |
|---|---|
| Learn from past losses and avoid them | 100% on the losses it studied, worse than nothing on new trades |
| Cut a losing trade early | Worse |
| Trade smaller after a drawdown | Worse, and the worst point did not move |
| Buy cheaper for bigger wins | Costs exactly what it is worth in win rate |
| A second price feed (Bitstamp) | 26% more accurate. Made no better trades |
| Time-of-day volatility | The cycle is real and already absorbed by the model |
| One all-in bet on a sure thing | There is no sure thing, and 15% every time beats it |

## Where things are

| | |
|---|---|
| [`cloud_state/learning_report.md`](cloud_state/learning_report.md) | full history: every call, the calibration table, why the losses happened |
| `check.py` | the whole bot, and the reasoning, in the file header |
| `bookwatch.py` | records the order book -- the one untested idea, three weeks from an answer |
| [`docs/RESEARCH.md`](docs/RESEARCH.md) | the original 14-day study, the look-ahead bug, and how look-ahead is prevented |
| [`results/reports/literature_review.md`](results/reports/literature_review.md) | what the published research says, re-tested on our own data |
| `real_data/` | the raw Kalshi and Bitcoin data, so any of this can be re-checked |

## Running it

It runs itself, on GitHub's machines, every hour. Nothing to install and
nothing to keep awake. To run it yourself:

```
python3 check.py            # look once, or keep watching
python3 check.py --report   # write the full history
python3 check.py --alerts   # hook up phone notifications
```

Standard library only. No account, no API key, read-only.
