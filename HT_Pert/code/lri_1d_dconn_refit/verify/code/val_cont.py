import numpy as np, json, sys, time
from myload import *
from mycont import run, summarize
D=load(); dC=D['dC678']; th=D['th']; c8=D['c8']; vac=D['vac']; rc=D['rc']
d7={int(k):v for k,v in json.load(open(D7)).items()}
SQ={6:6e-11,7:5e-10,8:2.5e-8}; SS={6:3.5e-10,7:1.0e-8,8:1.6e-7}
rng=np.random.default_rng(1)
def g2d(k):
    out={}
    for L in range(2,119,2):
        if k<=7 and L in d7: out[L]=d7[L]['delta_C'][k]
        elif L in vac and L in c8: out[L]=vac[L][k]-c8[L][k]
    return out
tests=[]
for k in (6,7,8):
    tests.append(('g2D%d'%k,g2d(k),k))
tests.append(('dC4',{L:rc[L]['dC4_Dconn'] for L in rc},6))
tests.append(('dC5',{L:rc[L]['dC5_Dconn'] for L in rc},7))
for name,seq,kn in tests:
    Ls=sorted(L for L in seq if L%2==0)
    for seed in range(3):
        tr={L:seq[L]+(rng.normal()*SS[kn] if 46<=L<=72 and seed>0 else 0.) for L in Ls if L<=72}
        sig={L:(SQ[kn] if L<=44 else SS[kn]) for L in tr}
        if seed==0: sig={L:SQ[kn] for L in tr}  # noiseless truth, quiet sigma everywhere
        Lp=[L for L in range(74,119,2) if L in seq]
        mem=run(tr,sig,72,Lp)
        s=summarize(mem,Lp,truth=seq)
        e=np.array(s['err_median']); sd=np.array(s['std']); p16=np.array(s['p16']); p84=np.array(s['p84']); t=np.array([seq[L] for L in Lp])
        inside=(t>=p16)&(t<=p84)
        z=np.abs(e)/sd
        print('%-5s seed%d(noise k=%d) kept %3d  Lmax=%d  max|err|/std %.2f  median|err|/std %.2f  frac in p16-84 %.2f  in minmax %s  |err|@last %.1e std@last %.1e'%(name,seed,kn,s['nkept'],Lp[-1],z.max(),np.median(z),inside.mean(),s['inside_minmax'],abs(e[-1]),sd[-1]))
# holdouts on dC6..8 themselves: train to 56/60, predict to 72
for k in (6,7,8):
    seq={L:dC[L][k] for L in dC if k in dC[L]}
    for hi in (56,60):
        tr={L:seq[L] for L in seq if L<=hi}
        sig={L:(SQ[k] if L<=44 else SS[k]) for L in tr}
        Lp=list(range(hi+2,73,2))
        mem=run(tr,sig,hi,Lp)
        s=summarize(mem,Lp,truth=seq)
        e=np.array(s['err_median']); sd=np.array(s['std'])
        print('hold dC%d hi=%d kept %d: err@72 %.2e std@72 %.2e |err|/std %.2f; noise %.1e'%(k,hi,s['nkept'],e[-1],sd[-1],abs(e[-1])/sd[-1],SS[k]))
