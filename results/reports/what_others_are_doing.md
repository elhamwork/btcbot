# What everyone else is doing, and what their claims survive

Searched August 2026. Every testable claim below was re-tested against our
own 329-trade dataset rather than taken on trust.

---

## 1. We are not alone. Not remotely.

At least five public bots target this exact series:

| project | approach |
|---|---|
| `reedjacobp/kalshi-trading-bot` | KXBTC15M, live dashboard |
| `brandononchain/kalshibot` | multi-strategy autonomous agent |
| `hamad-khawaja/kalshi-trading-bot` | KXBTC15M + KXETH15M, 16-signal model |
| `Bh-Ayush/Kalshi-CryptoBot` | 15-min and hourly BTC |
| polypulse, turbinefi, kalshibacktest | commercial scalpers and backtest services |

Combined daily volume on ultra-short crypto prediction contracts across
Kalshi and Polymarket is reported around $70 million, with HFT firms active
and the platforms adjusting microstructure to curb bots.

**What this means for us.** The "someone left that offer there" problem is
not hypothetical. Some of the size we trade against is other bots. That does
not make our edge fake -- it makes adverse selection a live question rather
than a theoretical one, and it is the one thing we still cannot measure.

---

## 2. The most useful number found: 4,904 strategies, 102 profitable

TurbineFi backtested 4,904 distinct strategies over 30 days of KXBTC15M --
about 2,831 markets each, 13.9 million strategy-market pairings, 41.8 million
simulated trades.

    profitable          102  (2.1%)
    not profitable    4,802
    median ROI       -14.53%  on $10,000 notional

**This is the single best piece of context in the whole search.** Two in a
hundred plausible strategies made money, and the typical one lost 15%. It is
independent confirmation of what this project found the hard way over roughly
130 rejected ideas: almost everything that sounds reasonable here loses.

It also sharpens the warning about our own result. If you test 4,904
strategies, about 245 will look profitable by chance alone at p=0.05. Their
102 winners are *fewer* than pure noise would produce. Our own count is ~130
ideas tested and three kept, which is the same hazard at smaller scale, and
is exactly why every survivor here had to hold across three chronological
periods and on unseen data.

---

## 3. The latency claim -- TESTED, does not survive to a scale we could use

Widely repeated: *Kalshi contract prices reprice with a 3-7 second lag behind
spot, so a fast reader can buy before the book catches up.* Some sources
stretch this to a 30-90 second stale window.

Tested on 69,122 minute-triples across 5,994 contracts:

    BTC's move this minute  vs  Kalshi's move this minute     +0.7007
    BTC's move this minute  vs  Kalshi's move NEXT minute     -0.0071
    Kalshi's move this minute vs BTC's move NEXT minute       +0.0026

Kalshi tracks BTC at +0.70 *within* the same minute and predicts nothing at
all about the next one. R-squared of the lag effect: 0.0001 -- one hundredth
of one percent.

So the 30-90 second claim is simply false at this resolution. The 3-7 second
claim may well be true, but it dies entirely inside one minute, and a bot
polling every fifteen seconds and alerting a phone can never touch it. That
is a race against colocated infrastructure, and not one to enter.

This also confirms, with data rather than assertion, that faster price feeds
would not help us.

---

## 4. Another bot trades the opposite end of the book -- and that band works too

`hamad-khawaja/kalshi-trading-bot` documents its rules in detail. Compared
with ours:

| | theirs | ours |
|---|---|---|
| price band | **25-60c** | **70-90c** |
| edge threshold | 5% | 7% |
| confirmation | 2 consecutive cycles | 2 looks, 1.5 min apart |
| sizing | 0.20 Kelly | ~0.5 Kelly at the live win rate |
| features | 33, across 16 signals | 3 |
| stop-loss | 20%, trailing take-profit | tested, rejected |
| published results | none | this repo |

Their band is the opposite end of the same market. Run through our model on
the same 63 days:

    band / rule                trades   win rate   break-even   margin   63d at 10%
    ours: 70-90c, edge 7%         329     88.4%      79.9%       +8.5     $18,321
    theirs: 25-60c, edge 5%       404     59.2%      52.8%       +6.4      $3,515
    25-60c, edge 7%               271     59.8%      52.2%       +7.5      $3,697
    40-60c, edge 5%               399     59.9%      53.0%       +6.9      $5,881
    25-45c, edge 5%                11     27.3%      40.3%      -13.0        $635

**Their band also has a positive margin.** That is worth more than it looks.
An independent developer, working separately, chose a completely different
slice of the price range, and our model finds an edge there too -- smaller
per trade, and far worse after compounding because cheap contracts carry more
variance drag, but real.

Two independent slices both showing positive margin is mild evidence that the
disagreement between this model and the market is a property of the market
rather than a quirk of where we happened to look.

Note also what they do that we tested and rejected: 33 features (our 15
indicators showed zero significance), a 20% stop-loss (worse), and trailing
take-profits (worse). And they publish no results, with "use at your own
risk" at the top.

---

## 5. Academic work: adjacent, not applicable

*Do Prediction Markets Forecast Cryptocurrency Volatility? Evidence from
Kalshi Macro Contracts* (Mohanty & Krishnamachari, arXiv 2604.01431) covers
ten Kalshi series and six assets, Jan 2023 - Mar 2026. It finds Fed-rate
repricing on KXFED predicts BTC volatility (t = 3.63, p < 0.001) and CPI
repricing predicts altcoin volatility, both surviving Benjamini-Hochberg
correction.

Real work, wrong question. It is about *macro contracts forecasting
volatility over days*, not about direction over fifteen minutes. Nothing in
it transfers.

No academic paper on 15-minute crypto binary direction was found. The
literature simply has not caught up to a contract type this new.

---

## What actually changed as a result of this search

Nothing in the model. Three things in what we know:

1. **The field is crowded and mostly loses.** 2.1% of 4,904 strategies made
   money. Our 130-idea rejection rate is normal, not pessimism.
2. **Speed is settled.** The lag claim fails at any scale we could act on,
   measured, not argued.
3. **Our band is not the only one that works**, which is weak independent
   support for the edge being real -- and our band is the better of the two.

The gap that remains is the one no amount of searching closes: 34 live calls,
and roughly 66 to go before the win rate means anything.

## Sources

- https://github.com/hamad-khawaja/kalshi-trading-bot
- https://github.com/reedjacobp/kalshi-trading-bot
- https://github.com/brandononchain/kalshibot
- https://github.com/Bh-Ayush/Kalshi-CryptoBot
- https://www.turbinefi.com/blog/5000-strategy-backtest-kalshi-btc-15m
- https://arxiv.org/abs/2604.01431
- https://crypto.news/on-polymarket-and-kalshi-five-minute-crypto-bets-now-dominate-prediction-flows/
