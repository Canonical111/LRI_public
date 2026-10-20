import sys, time, pickle, json, numpy as np
from mytabs import get
from mymi import run_family, analyze
L,raw,T=get()
cl=(L>=46)&(L<=72)
real=T['fmean']-T['s46']
sig={k:float(np.sqrt(np.mean(real[cl,k]**2))) for k in (6,7,8)}
seed0=int(sys.argv[1]); nrep=int(sys.argv[2]); scale=float(sys.argv[3]) if len(sys.argv)>3 else 1.0
print('realized rms (exact - floor-mean curve) at 46..72:',{k:'%.2e'%v for k,v in sig.items()},'scale',scale)
res=[]
for s in range(seed0,seed0+nrep):
    rng=np.random.default_rng(1000+s)
    Tn=T['s46'].copy()
    for k in (6,7,8):
        Tn[cl,k]+=rng.normal(size=cl.sum())*sig[k]*scale
    a=analyze(run_family(L,Tn,92))
    res.append((a['C8']['uncal'],a['C8']['calib'],a['C8']['ncal'],a['C6']['calib'],a['C7']['calib']))
    print(s,'C8 uncal %.0f cal %.0f ncal %d | C6 cal %.2f C7 cal %.0f'%res[-1],flush=True)
json.dump(res,open('../out/mi_noise_mc_%d_%d_%g.json'%(seed0,nrep,scale),'w'))
