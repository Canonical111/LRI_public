import sys, json, numpy as np
sys.dont_write_bytecode=True
sys.path.insert(0,'<PROJECT>/lri_hpc_Hamitonian/analysis/extended')
sys.path.insert(0,'<PROJECT>/lri_eh_hpc/lri_eh')
from analyze_joint import load, ThermalModel, MODELS
from exact import fast
from fitlib import basis_cols
rows=load(['thermal_new.json','prior_c7/C7_completed_runs.json','C7_extension.json'])
L=np.array([r['cutoff'] for r in rows],float); C=np.array([r['C'][:8] for r in rows])
w={int(k):v for k,v in json.load(open('<PROJECT>/lri_hpc_Hamitonian/analysis/extended/extended_summary.json'))['gap_reference']['extended'].items()}
sh=json.load(open('shift_all.json')); Sd=dict(zip([int(x) for x in sh['L']],sh['shift'])); cf=np.array(sh['fit_1_1l_2_2l_Lmin24'])
def shift(l):
    if int(l) in Sd: return Sd[int(l)]
    return float(basis_cols(np.array([l]),[(1,0),(1,1),(2,0),(2,1)])@cf)
dC4=np.array([fast(int(l)) for l in L]); s=np.array([shift(l) for l in L])
C4ex=45.42488010356
print('basis lo |   raw C4   | +g2D (dC4) | +Dfull_c (dC4+shift) | intercept shift from Dfull_c-g2D | miss(+g2D) miss(+Dfull_c) | resid raw/g2D/Dfull')
out=[]
for name in ['A','B','D','E','F']:
  for lo in [40,52,60]:
    m=L>=lo; vals=[];resl=[]
    try:
      for add in [0,dC4,dC4+s]:
        CC=C.copy(); CC[:,4]=CC[:,4]+add
        mod=ThermalModel(MODELS[name],w).fit(L[m],CC[m],maxorder=4)
        vals.append(mod.lim[4]); resl.append(mod.diag[4]['residual'])
    except ValueError as e:
      print(name,lo,'skip',e); continue
    out.append(dict(basis=name,lo=lo,raw=vals[0],g2D=vals[1],Dfull_c=vals[2]))
    print(f"{name}  {lo:3d} | {vals[0]:.5f} | {vals[1]:.5f} | {vals[2]:.5f} | {vals[2]-vals[1]:+.6f} | {vals[1]-C4ex:+.4f} {vals[2]-C4ex:+.4f} | {resl[0]:.1e} {resl[1]:.1e} {resl[2]:.1e}")
json.dump(out,open('refit_c4.json','w'),indent=1)
