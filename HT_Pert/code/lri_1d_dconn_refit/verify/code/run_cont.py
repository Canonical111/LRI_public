import numpy as np, json, sys, time
from myload import *
from mycont import run, summarize
D=load(); dC=D['dC678']
SQ={6:6e-11,7:5e-10,8:2.5e-8}; SS={6:3.5e-10,7:1.0e-8,8:1.6e-7}
Lpred=list(range(74,119,2))
res={}
for k in (6,7,8):
    t=time.time()
    seq={L:dC[L][k] for L in dC if k in dC[L] and L<=72}
    sig={L:(SQ[k] if L<=44 else SS[k]) for L in seq}
    mem=run(seq,sig,72,Lpred)
    s=summarize(mem,Lpred)
    res[k]=dict(summary=s,members=[{kk:v for kk,v in m.items()} for m in mem])
    i92=Lpred.index(92); i118=Lpred.index(118); i74=0
    print('dC%d kept %d/%d (%.1fs)'%(k,s['nkept'],s['nall'],time.time()-t))
    for i,L in ((i74,74),(Lpred.index(80),80),(i92,92),(i118,118)):
        print('  L=%d median %.10f  p16-84 [%.10f, %.10f] std %.2e minmax half %.2e'%(L,s['median'][i],s['p16'][i],s['p84'][i],s['std'][i],(s['max'][i]-s['min'][i])/2))
json.dump(res,open('../out/mycont_dC678.json','w'))
