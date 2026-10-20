# fit-based noise estimates: residuals of flexible smooth fits over long windows, rms split by L<=44 and 46..72
import numpy as np, json
from myload import *
from mycont import forms, cols_for
from mylsq import solve
from flint import arb
D=load(); dC=D['dC678']; th=D['th']; c8=D['c8']; rc=D['rc']
d7=json.load(open(D7))
out={}
for k in (6,7,8):
    seq={L:dC[L][k] for L in dC if k in dC[L]}
    for lo in (16,20,24):
        Ltr=[L for L in range(lo,73,2)]
        y=[arb(seq[L]) for L in Ltr]
        best=[]
        for name,terms in forms(len(Ltr)-6):
            if len(terms)<6: continue
            r=solve(cols_for(Ltr,terms),y)
            res=r['res']; Lt=np.array(Ltr)
            a=np.sqrt(np.mean(res[Lt<=44]**2)); b=np.sqrt(np.mean(res[Lt>=46]**2))
            best.append((np.sqrt(np.mean(res**2)),a,b,name,len(terms)))
        best.sort()
        print('dC%d lo=%d best fits (rms_all, rms<=44, rms46..72):'%(k,lo), ['%.1e %.1e %.1e %s'%(x[0],x[1],x[2],x[3]) for x in best[:4]])
    # model-free: fd on 46..72 only, and residual sign pattern of the best fit
    Ltr=list(range(20,73,2)); y=[arb(seq[L]) for L in Ltr]
    nm,terms=[f for f in forms(30) if f[0]==best[0][3]][0]
    r=solve(cols_for(Ltr,terms),y)
    print('   residual signs 46..72 best(lo=20):',''.join('+' if v>0 else '-' for v in r['res'][np.array(Ltr)>=46]), ' values:',' '.join('%.1e'%v for v in r['res'][np.array(Ltr)>=40]))
# raw data (thermal_d7) residual vs smooth fit across 30..118 for C6,C7: noise of raw at 46..72?
