import sys, json, numpy as np
from mytabs import get
from mymi import run_family, analyze
L,raw,T=get()
cl=(L>=46)&(L<=72)
real=(T['fmean']-T['s46'])[cl]
mode=sys.argv[1]; nrep=int(sys.argv[2])
res=[]
for s in range(nrep):
    rng=np.random.default_rng(5000+s)
    Tn=T['s46'].copy()
    for k in (6,7,8):
        r=real[:,k]
        if mode=='perm': x=rng.permutation(r)*rng.choice([-1,1],size=len(r))
        elif mode=='flip': x=r*rng.choice([-1,1],size=len(r))
        elif mode=='ramp':
            sd=np.sqrt(np.mean(r**2)); w=np.linspace(0.4,1.6,len(r)); w/=np.sqrt(np.mean(w**2)); x=rng.normal(size=len(r))*sd*w
        Tn[cl,k]+=x
    a=analyze(run_family(L,Tn,92))
    res.append((a['C8']['uncal'],a['C8']['calib'],a['C8']['ncal'],a['C6']['calib'],a['C7']['calib']))
    print(mode,s,'C8 uncal %.0f cal %.0f ncal %d | C6 cal %.2f C7 cal %.0f'%res[-1],flush=True)
json.dump(res,open('../out/mi_noise_mc2_%s.json'%mode,'w'))
