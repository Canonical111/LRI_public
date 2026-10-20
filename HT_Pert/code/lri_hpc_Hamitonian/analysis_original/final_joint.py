#!/usr/bin/env python3
from analyze_joint import *
# Reference omega3 chosen from a separate gap-only fit with a high-cutoff holdout test.
gap3=json.loads((D/'omega3_extended_fits.json').read_text())
ref3=next(r for r in gap3 if r['model']=='B' and r['lo']==24 and r['hi']==128 and not r['free_log'])
w3=ref3['omega3']
gap=load(['phi6_validation.json','phi6_production.json','phi6_extension.json'])
L=np.array([r['cutoff'] for r in gap],float);Y=np.array([r['raw']['D6'] for r in gap])
ref=GapModel(MODELS['A'],fixed_omega3=w3).fit(L[L>=16],Y[L>=16])
w={1:3.5,**ref.lim}
th=load(['prior_c7/C7_completed_runs.json','C7_extension.json']);LL=np.array([r['cutoff'] for r in th],float);C=np.array([r['C'] for r in th])
rows=[]
for name,terms in MODELS.items():
 for lo in (12,16,20,24):
  for hi in (40,44,48,50):
   for shift in (-2,0,2):
    m=(LL>=lo)&(LL<=hi)
    try:mod=ThermalModel(terms,w,shift=shift).fit(LL[m],C[m])
    except ValueError:continue
    h=LL>hi;err=np.max(abs(mod.predict(LL[h],C[h,2],C[h,3])-C[h,4:8]),axis=0).tolist() if h.any() else None
    rows.append(dict(model=name,lo=lo,hi=hi,shift=shift,C=mod.lim,diagnostics=mod.diag,heldout=err))
(D/'final_joint_models.json').write_text(json.dumps(rows,indent=2)+'\n')
selected=[r for r in rows if r['model'] in ('A','B','C') and r['lo']==16 and r['hi']==50 and not r['shift']]
summary=dict(omega3_reference=ref3,gap_reference={str(k):v for k,v in w.items()},selected_models=selected,
             ranges={label:{str(k):[min(r['C'][k] for r in rs),max(r['C'][k] for r in rs)] for k in range(4,8)} for label,rs in [('all_shifted_models',[r for r in rows if r['hi']==50]),('ABC_shifted',[r for r in rows if r['hi']==50 and r['model'] in ('A','B','C')]),('ABC_unshifted',[r for r in rows if r['hi']==50 and r['model'] in ('A','B','C') and not r['shift']])]})
(D/'final_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
