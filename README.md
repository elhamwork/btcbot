# btcbot

A bot that watches Kalshi's 15-minute Bitcoin contracts, and when it thinks
the price is wrong, tells my phone. It bets paper money so we can find out
whether it is right.

**It does not trade.** There is no account, no key, no order. It reads public
prices and sends notifications.

<!-- LIVE:BEGIN -->

## Live paper account

**$1,169.74** &nbsp; +17.0% since $1,000 &nbsp;&middot;&nbsp; updated 26 Aug 10:21pm California time

| calls settled | won / lost | win rate | break-even it must beat |
|---|---|---|---|
| 46 | 39 / 7 | 84.8% | 80.0% |

Best $1,279.61, worst $926.62, fees paid $70.43.

### Last 8 calls

| closed | result | paid | account after | side | price |
|---|---|---|---|---|---|
| 26 Aug 10:00pm | won | +20.60 | $1,169.74 | NO | 0.84 |
| 26 Aug 9:45pm | **LOST** | -130.47 | $1,149.14 | NO | 0.72 |
| 26 Aug 3:30pm | won | +37.15 | $1,279.61 | YES | 0.76 |
| 26 Aug 3:15pm | won | +44.25 | $1,242.46 | YES | 0.72 |
| 26 Aug 1:00pm | won | +36.68 | $1,198.21 | YES | 0.75 |
| 26 Aug 10:30am | won | +16.07 | $1,161.53 | YES | 0.87 |
| 26 Aug 10:00am | won | +24.79 | $1,145.46 | YES | 0.81 |
| 26 Aug 6:45am | won | +41.87 | $1,120.67 | YES | 0.71 |

46 of the roughly 100 settled calls needed before this win rate
means much. Two or three losses in the first dozen is ordinary;
four or more in twenty would say the model is wrong.

Collecting in the background: 7,119 order-book snapshots over 3 days (needs about three weeks).

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
| Chart indicators (RSI, EMA, MACD...) | 0 of 15 significant across 329 trades |
| Kalshi lagging spot by 3-7 seconds | Dies inside one minute; unreachable |
| Adding at the dip when it falls to 10c | 3 of 41 recovered. The market prices it right |
| One all-in bet on a sure thing | There is no sure thing, and 15% every time beats it |

## Where things are

| | |
|---|---|
| [`cloud_state/learning_report.md`](cloud_state/learning_report.md) | full history: every call, the calibration table, why the losses happened |
| `check.py` | the whole bot, and the reasoning, in the file header |
| `bookwatch.py` | records the order book -- the one untested idea, three weeks from an answer |
| [`docs/RESEARCH.md`](docs/RESEARCH.md) | the original 14-day study, the look-ahead bug, and how look-ahead is prevented |
| [`results/reports/literature_review.md`](results/reports/literature_review.md) | what the published research says, re-tested on our own data |
| [`results/reports/what_others_are_doing.md`](results/reports/what_others_are_doing.md) | the other bots on this market, and which of their claims survive |
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
