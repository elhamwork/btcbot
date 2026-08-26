"""
Does Kalshi's price lag BTC?

The claim found in the wild: Kalshi contract prices reprice 3-7 seconds
behind spot, so a fast reader can buy before the book catches up.

Tested at one-minute resolution -- the finest the historical data allows.
If the lag is really 3-7 seconds this test CANNOT see it. What it can see is
whether any lag survives to the one-minute scale, which is the only scale a
bot polling every fifteen seconds and alerting a phone could ever act on.
"""
import numpy as np, pandas as pd, csv
from collections import defaultdict

btc = pd.read_csv('/home/user/btcbot/real_data/btc_1min.csv')
tcol = [c for c in btc.columns if 'time' in c.lower() or c == 'ts'][0]
ccol = [c for c in btc.columns if c.lower() in ('close','price','c')][0]
btc['ts'] = pd.to_datetime(btc[tcol], utc=True, errors='coerce')
btc = btc.dropna(subset=['ts']).sort_values('ts')
# bar-END convention, as established
btc['ts'] = btc['ts'] + pd.Timedelta(minutes=1)
unix = (btc.ts - pd.Timestamp('1970-01-01', tz='UTC')).dt.total_seconds().astype('int64')
bmap = dict(zip(unix, btc[ccol].astype(float)))

rows = defaultdict(list)
with open('/home/user/btcbot/real_data/kalshi_15m_candlesticks.csv') as f:
    for r in csv.DictReader(f):
        try:
            t = int(r["end_period_ts"])
            b = float(r["yes_bid_close_dollars"]); a = float(r["yes_ask_close_dollars"])
        except (ValueError, TypeError):
            continue
        if 0 < b < 1 and 0 < a < 1:
            rows[r["ticker"]].append((t, (a + b) / 2.0))

pairs = []
for tk, seq in rows.items():
    seq.sort()
    for i in range(1, len(seq) - 1):
        t0, m0 = seq[i - 1]; t1, m1 = seq[i]; t2, m2 = seq[i + 1]
        if t1 - t0 != 60 or t2 - t1 != 60:
            continue
        p0, p1, p2 = bmap.get(t0), bmap.get(t1), bmap.get(t2)
        if None in (p0, p1, p2):
            continue
        pairs.append((np.log(p1 / p0), np.log(p2 / p1), m1 - m0, m2 - m1))
d = np.array(pairs)
print("  %s usable minute triples across %d contracts\n" % (format(len(d), ",d"), len(rows)))
btc_now, btc_next, k_now, k_next = d[:,0], d[:,1], d[:,2], d[:,3]

def corr(a, b): return np.corrcoef(a, b)[0, 1]
print("  IF KALSHI LAGS, BTC's move THIS minute should predict")
print("  Kalshi's move NEXT minute.\n")
print("  %-46s %8s"%("correlation","value"))
print("  %-46s %+8.4f"%("BTC this minute  vs  Kalshi this minute", corr(btc_now, k_now)))
print("  %-46s %+8.4f  <-- THE LAG CLAIM"%("BTC this minute  vs  Kalshi NEXT minute", corr(btc_now, k_next)))
print("  %-46s %+8.4f"%("Kalshi this minute vs BTC NEXT minute", corr(k_now, btc_next)))
print()
# how much of Kalshi's next move is explained by BTC's last move?
r = corr(btc_now, k_next)
print("  R-squared of the lag effect: %.4f  (%.2f%% of next-minute movement)"
      % (r*r, 100*r*r))
