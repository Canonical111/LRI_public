import json, numpy as np, mpmath as mp
mp.mp.dps=40
def load(f):
    return [json.loads(l) for l in open(f)]
def noise_est(e):
    """white + random-walk decomposition from residual increments"""
    d=np.diff(e); v=d.var(); c1=np.mean((d[:-1]-d.mean())*(d[1:]-d.mean()))
    sw2=max(-c1,0.0); sinc2=max(v-2*sw2,0.0)
    return np.sqrt(sw2), np.sqrt(sinc2)
def sig_corr(r, sw, sinc):
    p=np.array(r['p']); L=np.arange(r['Lfirst'],r['Llast']+1,2); s=L//2
    w=sw**2*np.sum(p**2)
    T=np.cumsum(p[::-1])[::-1]       # T at s_i: sum_{i'>=i} p
    # steps k from 1..s_max: for k<=s_0 T=sum p; for s_{i-1}<k<=s_i, T=T_i (with steps of 2 in L -> 1 in s)
    rw=s[0]*T[0]**2+np.sum(T[1:]**2*np.diff(s))
    return np.sqrt(w+sinc**2*rw)
