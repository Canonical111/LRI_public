import sys, json, numpy as np
sys.dont_write_bytecode=True
sys.path.insert(0,'<PROJECT>/lri_hpc_Hamitonian/analysis/extended')
from analyze_joint import load
from fitlib import load as myload
rows={r['cutoff']:r for r in load(['thermal_new.json','prior_c7/C7_completed_runs.json','C7_extension.json'])}
R=myload()
mx=0
for L,d in R.items():
    if L in rows:
        a=np.array(rows[L]['C'][:5]); b=np.array(d['variants']['raw']['C'][:5])
        rel=np.max(np.abs(a-b)/np.maximum(1,np.abs(a))); mx=max(mx,rel)
        if L%16==0: print(L,'campaign C0..4',a,' mine',b,' maxrel %.1e'%rel)
print('max rel diff C0..C4 over L=4..64: %.2e'%mx)
