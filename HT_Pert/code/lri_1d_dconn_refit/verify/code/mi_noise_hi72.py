import numpy as np, json
from mytabs import get
from mymi import run_family, analyze
L,raw,T=get(); cl=(L>=46)&(L<=72)
real=T['fmean']-T['s46']; sig={k:float(np.sqrt(np.mean(real[cl,k]**2))) for k in (6,7,8)}
b=analyze(run_family(L,T['s46'],72))
print('s46 hi72 cal %.0f uncal %.0f'%(b['C8']['calib'],b['C8']['uncal']))
res=[]
for s in range(14):
    rng=np.random.default_rng(1000+s); Tn=T['s46'].copy()
    for k in (6,7,8): Tn[cl,k]+=rng.normal(size=cl.sum())*sig[k]
    a=analyze(run_family(L,Tn,72)); res.append((a['C8']['uncal']-b['C8']['uncal'],a['C8']['calib']-b['C8']['calib']))
r=np.array(res); print('hi72 noise MC shift vs s46: uncal mean %+.0f std %.0f [%+.0f,%+.0f]; cal mean %+.0f std %.0f [%+.0f,%+.0f]'%(r[:,0].mean(),r[:,0].std(),r[:,0].min(),r[:,0].max(),r[:,1].mean(),r[:,1].std(),r[:,1].min(),r[:,1].max()))
print('actual fmed hi72 - s46: uncal %+.0f cal %+.0f'%(8061280-b['C8']['uncal'],8065130-b['C8']['calib']))
