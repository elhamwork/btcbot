import numpy as np, pandas as pd
from math import erf, sqrt, comb
from sklearn.isotonic import IsotonicRegression
d=pd.read_parquet('/home/user/btcbot/data/processed/decision_panel.parquet').sort_values('ts').reset_index(drop=True)
d=d[(d.rv_15m>0)&d.yes_ask.notna()&d.yes_bid.notna()].copy()
def phi(x): return .5*(1+np.vectorize(erf)(x/sqrt(2)))
z=np.log((d.btc_price+5.97)/d.floor_strike)/(d.rv_15m*np.sqrt(d.minutes_remaining.clip(lower=.05)))
n=len(d); i1=int(.6*n); i2=int(.8*n); CUT=d.ts.iloc[i2]
iso=IsotonicRegression(out_of_bounds='clip').fit(phi(z[:i1]),d.y[:i1])
d['p']=iso.predict(phi(z)); sy=d.p>=.5
d['side']=np.where(sy,'Y','N'); d['conf']=np.where(sy,d.p,1-d.p)
d['price']=np.where(sy,d.yes_ask,d.no_ask); d['edge']=d.conf-d.price
d['win']=np.where(sy,d.y==1,d.y==0)
d['ok']=(d.edge>=.07)&(d.price>=.70)&(d.price<=.90)&(d.spread<=.05)
G=1.5
def window(lo=10,hi=15):
    w=d[(d.minutes_remaining>=lo)&(d.minutes_remaining<=hi)].sort_values(['ticker','minutes_remaining'],ascending=[True,False])
    out=[]
    for tk,g in w.groupby('ticker',sort=False):
        g=g.reset_index(drop=True)
        for i in range(len(g)):
            r=g.iloc[i]
            if not r.ok: continue
            e=g.iloc[:i]
            if len(e[(e.ok)&(e.side==r.side)&(e.minutes_remaining>=r.minutes_remaining+G)]):
                out.append(r); break
    return pd.DataFrame(out).sort_values('ts')
t=window()
print("  63 DAYS, full window rule -- %d trades, split by price paid"%len(t))
print("  %-9s %7s %7s %11s %9s %10s"%("band","trades","win%","break-even","margin","per $"))
for lo,hi in ((.70,.75),(.75,.80),(.80,.85),(.85,.91)):
    g=t[(t.price>=lo)&(t.price<hi)]
    if len(g)<3: continue
    wr=100*g.win.mean(); be=100*g.price.mean()
    pnl=100*((1-g.price)*g.win-g.price*(~g.win)).sum()/g.price.sum()
    print("  %2.0f-%2.0fc     %7d %6.1f%% %10.1f%% %+8.1f  %+9.2f%%"
          %(100*lo,100*hi,len(g),wr,be,wr-be,pnl))
print()
print("  same split, UNSEEN FIFTH only")
u=t[t.ts>=CUT]
for lo,hi in ((.70,.75),(.75,.80),(.80,.85),(.85,.91)):
    g=u[(u.price>=lo)&(u.price<hi)]
    if len(g)<3: continue
    wr=100*g.win.mean(); be=100*g.price.mean()
    pnl=100*((1-g.price)*g.win-g.price*(~g.win)).sum()/g.price.sum()
    print("  %2.0f-%2.0fc     %7d %6.1f%% %10.1f%% %+8.1f  %+9.2f%%"
          %(100*lo,100*hi,len(g),wr,be,wr-be,pnl))
# is live's 2/4 surprising given the backtest rate for that band?
g=t[(t.price>=.70)&(t.price<.75)]
p=g.win.mean()
print()
print("  live went 2 of 4 in the 70-75c band. If the true rate there is %.1f%%,"%(100*p))
print("  P(2 or fewer wins in 4) = %.0f%%"%(100*sum(comb(4,i)*p**i*(1-p)**(4-i) for i in range(0,3))))
