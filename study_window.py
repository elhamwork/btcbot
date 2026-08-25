"""
Re-run the 63-day study across the window the bot actually uses.

The shipped rule allows a call any time from 15 minutes left down to 10. The
study that produced 89.3% looked at one instant -- 10 minutes left, confirmed
against 12 -- while three quarters of live calls happen at other times. This
walks each contract down through the window and takes the FIRST confirmed
setup, which is what the bot does.

    python3 study_window.py

Needs data/processed/decision_panel.parquet, so run `python main.py
--prepare-data` first if it is missing.

RESULT (August 2026):

    rule                     trades   win%   break-even   63d at 10%
    10-min snapshot (old)       272   89.3%     80.2%       $13,187
    full 10-15 min window       329   88.4%     79.9%       $18,331
      unseen fifth only          89   88.8%     79.1%        $2,516

The rule holds across the whole window. Slightly lower win rate, more trades,
higher end value, and the unseen fifth agrees.

THE LIMITATION THIS EXPOSED, which matters more than the result. The panel
contains exactly three moments per contract -- 14, 12 and 10 minutes left --
and nothing in between. The live bot polls every 15 seconds and sees about
24. So it acts on setups appearing at minute 13, or 11, or 15, which no
version of this study can evaluate. That, not any difference in the rule,
is why live takes 17.5 calls a day against this study's 5.2.

The raw candles in real_data/kalshi_15m_candlesticks.csv hold every minute --
about 15 rows per contract. Rebuilding the panel at full resolution would put
the study and the bot on the same footing for the first time. Until that is
done, roughly two thirds of what the bot actually does is unmeasured.
"""
import numpy as np, pandas as pd
from math import erf, sqrt
from sklearn.isotonic import IsotonicRegression

d = pd.read_parquet('/home/user/btcbot/data/processed/decision_panel.parquet') \
      .sort_values('ts').reset_index(drop=True)
d = d[(d.rv_15m>0)&d.yes_ask.notna()&d.yes_bid.notna()].copy()
def phi(x): return .5*(1+np.vectorize(erf)(x/sqrt(2)))
z=np.log((d.btc_price+5.97)/d.floor_strike)/(d.rv_15m*np.sqrt(d.minutes_remaining.clip(lower=.05)))
n=len(d); i1=int(.6*n); i2=int(.8*n)
CUT=d.ts.iloc[i2]
iso=IsotonicRegression(out_of_bounds='clip').fit(phi(z[:i1]),d.y[:i1])
d['p']=iso.predict(phi(z)); sy=d.p>=.5
d['side']=np.where(sy,'Y','N'); d['conf']=np.where(sy,d.p,1-d.p)
d['price']=np.where(sy,d.yes_ask,d.no_ask); d['edge']=d.conf-d.price
d['win']=np.where(sy,d.y==1,d.y==0)
d['ok']=(d.edge>=.07)&(d.price>=.70)&(d.price<=.90)&(d.spread<=.05)

CONFIRM_GAP = 1.5      # minutes, as shipped

def window_trades(lo=10, hi=15):
    """
    Walk each contract minute by minute from hi down to lo, exactly as the
    live bot does: take the FIRST moment that qualifies and has a qualifying
    look on the same side at least CONFIRM_GAP minutes earlier. One trade per
    contract, first come first served -- so a later, better-looking setup on
    the same contract is not cherry-picked.
    """
    w = d[(d.minutes_remaining>=lo)&(d.minutes_remaining<=hi)].copy()
    w = w.sort_values(['ticker','minutes_remaining'], ascending=[True,False])
    out=[]
    for tk, g in w.groupby('ticker', sort=False):
        g=g.reset_index(drop=True)
        for i in range(len(g)):
            r=g.iloc[i]
            if not r.ok: continue
            earlier=g.iloc[:i]
            conf=earlier[(earlier.ok)&(earlier.side==r.side)
                         &(earlier.minutes_remaining>=r.minutes_remaining+CONFIRM_GAP)]
            if len(conf):
                out.append(r); break
    return pd.DataFrame(out).sort_values('ts') if out else pd.DataFrame()

FEE=.07
def path(t,f=.10,b=1000.0):
    for _,r in t.iterrows():
        pr,w=float(r.price),bool(r.win); st=b*f; c=st/pr
        b += (c-st-FEE*c*pr*(1-pr)) if w else (-st-FEE*c*pr*(1-pr))
        if b<1: return 0
    return b

def show(lbl,t):
    for scope,sel in (("all 63 days",lambda x:x),("unseen fifth",lambda x:x[x.ts>=CUT])):
        s=sel(t)
        if len(s)<5: continue
        pnl=100*((1-s.price)*s.win-s.price*(~s.win)).sum()/s.price.sum()
        print("  %-34s %6d %8.1f%% %8.1f%% %+8.2f%% %11s"
              %(lbl+" / "+scope,len(s),100*s.win.mean(),100*s.price.mean(),pnl,
                "$"+format(round(path(s)),",d")))

print("  %-34s %6s %8s %8s %9s %11s"%("","trades","win%","break-even","per $","63d at 10%"))
# the old study, for comparison, rebuilt here
piv={m:d[d.minutes_remaining==m].set_index('ticker') for m in (10,12)}
e=piv[10][piv[10].ok].copy(); o=piv[12].reindex(e.index)
e['c']=o.ok.fillna(False).values&(o.side.values==e.side.values)
show("10-min snapshot (the old study)", e[e.c].sort_values('ts'))
for lo,hi in ((10,15),(10,13),(10,12)):
    show("window %d-%d min (what runs)"%(lo,hi), window_trades(lo,hi))
