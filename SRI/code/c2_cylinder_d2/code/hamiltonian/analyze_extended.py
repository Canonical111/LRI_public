"""Analysis of completed larger-cutoff runs. No proposed C2 used."""
import json,numpy as np
from resummed import ROOT
from analyze_fine import analyze
from exact_leading_tail import evaluate,configured_tail_cutoff
TAIL_N=configured_tail_cutoff()  # historical default 2048; see exact_leading_tail.py
rows=[]
for fn in sorted(ROOT.glob('extended_k*.json')):
    dat=json.loads(fn.read_text());d=analyze(dat);k=d['order'];lam=d['lam'];N=d['N'];y=np.array(d['sequence'])
    tailfn=ROOT/f'leading_N384_k{k}_a{lam}.json'
    t=json.loads(tailfn.read_text()) if tailfn.exists() else None
    if t is None or t.get('N')!=TAIL_N:
        t=evaluate(lam,k,TAIL_N,two_point=dat['two_point']);tailfn.write_text(json.dumps(t,indent=2))
    at=t['asymptotic_tail_coefficient'];fs=[]
    for ps in [[2.75,3.75],[2.75,3.75,4.75],[2.75,3.5,3.75,4.75],[2.75,3.5,3.75,4.75,5.5]]:
      for ex in [0,1,2,3]:
       for nmin in [N//2,5*N//8,3*N//4,7*N//8]:
        n=np.arange(nmin,N+1);u=n/N
        yy=y[n-1]+at*n.astype(float)**(-1.75)
        cols=[np.ones_like(u)]+[u**(-p) for p in ps]
        if ex:
         for j in range(ex):cols.append(np.exp(-lam*(n-nmin))*u**(k-1-j))
         for j in range(ex):cols.append(np.exp(-2*lam*(n-nmin))*u**(2*k+.75-j))
        A=np.array(cols).T;sc=np.linalg.norm(A,axis=0);AA=A/sc
        cf=np.linalg.lstsq(AA,yy,rcond=1e-13)[0];res=AA@cf-yy
        fs.append(dict(powers=ps,exponential_order=ex,Nmin=nmin,limit=float(cf[0]/sc[0]),max_residual=float(np.max(abs(res))),condition=float(np.linalg.cond(AA))))
    row=dict(order=k,lam=lam,N=N,last=d['last'],mixed_spread=d['mixed_spread'],tail=t,fits=fs,cauchy_grid_comparison=dat.get('cauchy_grid_comparison'))
    selected=[f for f in fs if len(f['powers']) in [3,4] and f['exponential_order'] in [1,2] and f['Nmin'] in [240,288]]
    v=np.array([f['limit'] for f in selected]);row['selected']=dict(median=float(np.median(v)),minimum=float(min(v)),maximum=float(max(v)),half_spread=float((max(v)-min(v))/2),values=v.tolist())
    print('\nEXT',k,lam,'last',d['last'],'tail',at,'mixed_spread',d['mixed_spread'],'selected',row['selected'],flush=True)
    for f in fs:
       if len(f['powers']) in [3,4] and f['exponential_order'] in [0,2] and f['Nmin'] in [192,240,288]:print(f,flush=True)
    rows.append(row)
(ROOT/'extended_analysis.json').write_text(json.dumps(rows,indent=2))
