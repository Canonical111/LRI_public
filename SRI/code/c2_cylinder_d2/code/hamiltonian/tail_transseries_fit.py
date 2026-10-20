"""Exploratory tail fits with independently derived leading power fixed.
Exponential terms reflect the known improved-chi kernel singularity at e^lambda.
No delta fit or asserted C2 input. Stability, not residuals alone, is relevant.
"""
import json,numpy as np
from pathlib import Path
from resummed import ROOT
from analyze_fine import analyze
from exact_leading_tail import evaluate,configured_tail_cutoff
TAIL_N=configured_tail_cutoff()  # historical default 2048; see exact_leading_tail.py
rows=[];ts=json.loads((ROOT/'exact_leading_tail.json').read_text())
for fn in sorted(ROOT.glob('fine_k*.json')):
    d=analyze(json.loads(fn.read_text()));k=d['order'];lam=d['lam'];N=d['N'];y=np.array(d['sequence'])
    tt=[t for t in ts if t['order']==k and t['lam']==lam and t['N']==TAIL_N]
    if not tt:
       t=evaluate(lam,k,TAIL_N);ts.append(t);(ROOT/'exact_leading_tail.json').write_text(json.dumps(ts,indent=2))
    else:t=tt[0]
    at=t['asymptotic_tail_coefficient'];fs=[]
    for ps in [[2.75,3.75],[2.75,3.75,4.75],[2.75,3.5,3.75,4.75]]:
     for ex in [0,1,2,3]:
      for nmin in [96,128,160,192]:
       n=np.arange(nmin,N+1);u=n/N
       yy=y[n-1]+at*n.astype(float)**(-1.75)
       cols=[np.ones_like(u)]+[u**(-p) for p in ps]
       if ex:
        for j in range(ex):cols.append(np.exp(-lam*(n-nmin))*u**(k-1-j))
        for j in range(ex):cols.append(np.exp(-2*lam*(n-nmin))*u**(2*k+.75-j))
       A=np.array(cols).T;sc=np.linalg.norm(A,axis=0);AA=A/sc
       cf=np.linalg.lstsq(AA,yy,rcond=1e-13)[0];res=AA@cf-yy
       fs.append(dict(powers=ps,exponential_order=ex,Nmin=nmin,limit=float(cf[0]/sc[0]),max_residual=float(np.max(abs(res))),condition=float(np.linalg.cond(AA))))
    row=dict(order=k,lam=lam,tail=t,fits=fs);rows.append(row)
    print('\n',k,lam,flush=True)
    for f in fs:
       if f['exponential_order']==2 and f['Nmin'] in [128,160,192]:print(f['powers'],f['Nmin'],f['limit'],f['max_residual'],f['condition'],flush=True)
    (ROOT/'tail_transseries_fits.json').write_text(json.dumps(rows,indent=2))
