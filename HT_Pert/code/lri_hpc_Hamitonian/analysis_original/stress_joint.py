#!/usr/bin/env python3
"""Cutoff-window, subleading-basis, exponent-input and arithmetic stress tests.
Ranges are tested-model spreads, not probabilities or rigorous enclosures.
"""
from analyze_joint import *
if __name__=='__main__':
 gmods=json.loads((D/'gap_extrapolations.json').read_text())
 gr=next(r for r in gmods if r['scheme']=='raw' and r['model']=='A' and r['lo']==16 and not r['free_leading_log'])
 w={int(k):v for k,v in json.loads((D/'final_summary.json').read_text())['gap_reference'].items()}
 th=load(['prior_c7/C7_completed_runs.json','C7_extension.json']);L=np.array([r['cutoff'] for r in th],float);C=np.array([r['C'] for r in th])
 rows=[]
 for name in ('minimal','A','B','C','D','E','F'):
  for lo in (12,16,20,24):
   for shift in (-2,0,2):
    m=L>=lo
    try:mod=ThermalModel(MODELS[name],w,shift=shift).fit(L[m],C[m])
    except ValueError:continue
    rows.append(dict(model=name,lo=lo,shift=shift,C=mod.lim,diagnostics=mod.diag))
 (D/'thermal_stress.json').write_text(json.dumps(rows,indent=2)+'\n')
 # Propagate every computed raw gap fit through the three fixed thermal bases.
 inp=[]
 for gap in gmods:
  if gap['scheme']!='raw' or gap['model']=='minimal':continue
  wi={1:3.5,**{int(k):v for k,v in gap['omega'].items()}}
  for name in ('A','B','C'):
   m=L>=16
   mod=ThermalModel(MODELS[name],wi).fit(L[m],C[m])
   inp.append(dict(gap_model=gap['model'],gap_lo=gap['lo'],gap_free_log=gap['free_leading_log'],thermal_model=name,C=mod.lim))
 (D/'gap_input_propagation.json').write_text(json.dumps(inp,indent=2)+'\n')
 # No target C7 is used in perturbation tests.
 rng=np.random.default_rng(93802);noise=[];err=np.array([0,0,5e-13,1e-11,1e-10,5e-9,5e-8,5e-7])
 for name in ('A','B','C'):
  m=L>=16;base=ThermalModel(MODELS[name],w).fit(L[m],C[m])
  high=ThermalModel(MODELS[name],w,mpqr=True).fit(L[m],C[m])
  differences=[]
  for j in range(128):
   cp=C[m]+rng.uniform(-1,1,C[m].shape)*err
   pert=ThermalModel(MODELS[name],w).fit(L[m],cp)
   differences.append([pert.lim[k]-base.lim[k] for k in range(4,8)])
  noise.append(dict(model=name,bounded_input_perturbations=err.tolist(),replicates=128,
                    max_output_change=np.max(abs(np.array(differences)),axis=0).tolist(),
                    high_precision_output=[high.lim[k] for k in range(4,8)],
                    float_vs_mpqr=[base.lim[k]-high.lim[k] for k in range(4,8)]))
 (D/'arithmetic_stress.json').write_text(json.dumps(noise,indent=2)+'\n')
 summary={}
 for label,rs in [('all_subleading_variations',rows),('ABC_shifts_windows',[r for r in rows if r['model'] in ('A','B','C')]),('ABC_unshifted',[r for r in rows if r['model'] in ('A','B','C') and r['shift']==0]),('gap_input_variations',inp)]:
  summary[label]={str(k):[min(r['C'][k] for r in rs),max(r['C'][k] for r in rs)] for k in range(4,8)}
 summary['arithmetic']=noise
 (D/'stress_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
