import json, sys, glob
import numpy as np
sys.path.insert(0,'<PROJECT>/lri_hpc_Hamitonian/analysis/extended')
sys.dont_write_bytecode=True
from analyze_joint import load
import os
os.chdir('<PROJECT>/lri_hpc_Hamitonian/analysis/extended')
rows={r['cutoff']:r for r in load(['thermal_new.json','prior_c7/C7_completed_runs.json','C7_extension.json'])}
os.chdir('<TMP>/scratchpad/eps5/B')
d5=json.load(open('<PROJECT>/lri_hpc_Hamitonian/analysis/eh_addon_review/physics-impact/d5_all.json'))
for f in sorted(glob.glob('full5_c*.json'), key=lambda x:int(x[7:-5])):
    o=json.load(open(f)); c4=o['cut4']
    if c4%4: continue
    L=c4//4
    v=o['variants']; t=rows.get(L)
    s=f'L={L:3d}'
    if t:
        rr=np.array(v['raw']['r']); gg=np.array(v['raw']['g']); C=np.array(v['raw']['C'])
        dr=np.max(np.abs(rr[:6]-np.array(t['r'][:6]))/np.maximum(1,np.abs(rr[:6])))
        dg=np.max(np.abs(gg[:6]-np.array(t['g'][:6]))/np.maximum(1,np.abs(gg[:6])))
        dc=np.max(np.abs(C[:6]-np.array(t['C'][:6]))/np.maximum(1,np.abs(C[:6])))
        s+=f' raw vs thermal: r {dr:.1e} g {dg:.1e} C {dc:.1e} (C5={C[5]:.12f} pkg {t["C"][5]:.12f})'
    if str(L) in d5:
        dC=np.array(v['g2D']['C'])-np.array(v['raw']['C']); p=np.array(d5[str(L)]['delta_C'])
        s+=f' | dC4 {dC[4]:.13f} pkg {p[4]:.13f} dC5 {dC[5]:.12f} pkg {p[5]:.12f} diff {abs(dC[5]-p[5]):.1e}'
    print(s)
