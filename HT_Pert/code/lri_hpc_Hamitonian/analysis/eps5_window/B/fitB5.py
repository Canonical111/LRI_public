import json, numpy as np, mpmath as mp, sys
from fitwin import fit, F
top={}
for l in open('top5.jsonl'):
    r=json.loads(l); top[r['L']]=r
Ls=sorted(top)
bases={'a+':['1','lg','1/L','lg/L','1/L2','lg/L2','1/L3'],'b+':['1','1/L','lg/L','lg2/L','1/L2','lg/L2','1/L3'],
       'c':['1','lg','L-.5','1/L','lg/L','1/L2'],'d':['1','lg','lg2/L','lg/L','1/L','1/L2','lg/L2'],
       'e':['1','lg','lg2','1/L','lg/L','1/L2','lg/L2'],'f':['1','L-.5','lgL-.5','1/L','lg/L','1/L2'],
       'g':['1','lg','lg2/L','lg/L','1/L','lg2/L2','lg/L2','1/L2'], 'h':['1','lg2/L','lg/L','1/L','lg2/L2','lg/L2','1/L2']}
for q in ('A5','B5','top6_5','A4','B4'):
    data={L:(top[L][q] if q!='top6_5' else top[L]['B5']-top[L]['A5']) for L in Ls}
    print(f'--- {q} (L up to {Ls[-1]}); value at Lmax {data[Ls[-1]]:.12f}')
    for lo in (40,64,80):
        sel=[L for L in Ls if L>=lo]
        for bn,b in bases.items():
            if len(sel)<len(b)+4: continue
            p,res=fit(sel,[data[L] for L in sel],[F[x] for x in b])
            lgc = p[b.index('lg')] if 'lg' in b else 0.
            pred = {LL: sum(pi*float(F[x](mp.mpf(LL))) for pi,x in zip(p,b)) for LL in (1000,)}
            print(f'lo={lo:2d} {bn:3s} res={res:.1e} const={p[0]:+.7f} logcoef={lgc:+.2e}  value@L=1000 {pred[1000]:+.6f}')
