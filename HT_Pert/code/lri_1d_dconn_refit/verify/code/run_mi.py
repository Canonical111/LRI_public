import sys, time, pickle, numpy as np
from mytabs import get
from mymi import run_family, analyze
L,raw,T=get()
M=np.load('../out/mitabs.npz')
tabs={'fmed':M['fmed'],'old':M['old'],'mimed':M['mimed'],'s46':T['s46'],'fmean':T['fmean'],'mine':T['mine']}
name=sys.argv[1]; hi=int(sys.argv[2])
t=time.time()
F=run_family(L,tabs[name],hi)
pickle.dump(F,open('../out/mi_%s_hi%d.pkl'%(name,hi),'wb'))
a=analyze(F)
print(name,hi,'%.1fs'%(time.time()-t),'floors',{n:'%.1e'%v for n,v in a['floors'].items()})
if 'C8' in a: print('  C8 nadq %d ncal %d uncal %.0f cal %.0f adq-median %.0f bias(x1e3) %s'%(a['C8']['nadq'],a['C8']['ncal'],a['C8']['uncal'] or np.nan,a['C8']['calib'] or np.nan,a['C8']['adq_median'] or np.nan,[round(x*1e3,3) for x in a['C8']['bias_med']] if a['C8']['bias_med'] else None))
for n in (6,7): print('  C%d nadq %d ncal %d uncal %s cal %s'%(n,a['C%d'%n]['nadq'],a['C%d'%n]['ncal'],a['C%d'%n]['uncal'],a['C%d'%n]['calib']))
