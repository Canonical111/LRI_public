import json, numpy as np, mpmath as mp
from fitwin import fit, F
rr=json.load(open('rowresp_4_118.json'))
Ls=sorted(int(k) for k in rr)
y={L: rr[str(L)]['rowB4']['dC'][5] for L in Ls}
yA={L: rr[str(L)]['rowA4']['dC'][5] for L in Ls}
print('rho5A + 3 rho5B max |.|:', max(abs(yA[L]+3*y[L]) for L in Ls))
g={L: rr[str(L)]['g2D']['dC'][5] for L in Ls}
g4={L: rr[str(L)]['g2D']['dC'][4] for L in Ls}
g3={L: rr[str(L)]['g2D+g3W']['dC'][5]-rr[str(L)]['g2D']['dC'][5] for L in Ls}
print('max |dC5_g3W + 2 dC4_g2D| =', max(abs(g3[L]+2*g4[L]) for L in Ls))
bases={'a':['1','lg','1/L','lg/L','1/L2','lg/L2'],'b':['1','1/L','lg/L','lg2/L','1/L2','lg/L2','1/L3'],
       'c':['1','lg','L-.5','lgL-.5','1/L','lg/L','1/L2'],'d':['1','lg','lg2','L-.5','lgL-.5','1/L','lg/L'],'e':['1','L-.5','lgL-.5','1/L','lg/L','1/L2'],
       'f':['1','lg','L-.5','lgL-.5','lg2L-.5','1/L','lg/L','1/L2']}
for name,data in (('rho5B',y),('dC5_g2D',g)):
    print('---',name)
    for lo in (24,40,60):
        sel=[L for L in Ls if L>=lo]
        for bn,b in bases.items():
            p,res=fit(sel,[data[L] for L in sel],[F[x] for x in b])
            print(f'lo={lo} {bn} res={res:.1e} '+' '.join(f'{n}={v:+.6g}' for n,v in zip(b,p)))
