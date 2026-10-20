import json, numpy as np, mpmath as mp
from fitwin import fit, F
rows=json.load(open('dC5_table.json')); D={r['L']:r for r in rows}
Ls=sorted(D)
bases={'c':['1','lg','L-.5','lgL-.5','1/L','lg/L','1/L2'],'c2':['1','lg','L-.5','lgL-.5','lg2L-.5','1/L','lg/L','1/L2'],
       'n':['1','L-.5','lgL-.5','1/L','lg/L','1/L2'],'n2':['1','L-.5','lgL-.5','lg2L-.5','1/L','lg/L','1/L2'],
       'cl2':['1','lg','lg2','L-.5','lgL-.5','1/L','lg/L']}
for q in ('dC5_Dconn','dC5_g2D','dC5_rows4','dC5_rows5','dC4_Dconn'):
    print('---',q, 'L<=',Ls[-1])
    for lo in (24,40,60):
        sel=[L for L in Ls if L>=lo]
        for bn,b in bases.items():
            p,res=fit(sel,[D[L][q] for L in sel],[F[x] for x in b])
            lgc=p[b.index('lg')] if 'lg' in b else 0.
            print(f'lo={lo} {bn:3s} res={res:.1e} const={p[0]:+.6f} log={lgc:+.3e}  L^-.5={p[b.index("L-.5")]:+.4f}')
