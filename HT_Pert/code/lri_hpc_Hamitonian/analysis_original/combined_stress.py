#!/usr/bin/env python3
"""Cartesian-product gap/basis/window/cutoff-coordinate sensitivity test."""
from analyze_joint import *
if __name__=='__main__':
    gs=[r for r in json.loads((D/'gap_extrapolations.json').read_text()) if r['scheme']=='raw' and r['model']!='minimal']
    data=load(['prior_c7/C7_completed_runs.json','C7_extension.json'])
    L=np.array([r['cutoff'] for r in data],float);C=np.array([r['C'] for r in data]);out=[]
    for gr in gs:
      w={1:3.5,**{int(k):v for k,v in gr['omega'].items()}}
      for name,terms in MODELS.items():
       for lo in (12,16,20,24):
        for shift in (-2,0,2):
         m=L>=lo
         try:mod=ThermalModel(terms,w,shift=shift).fit(L[m],C[m])
         except ValueError:continue
         out.append(dict(gap_model=gr['model'],gap_lo=gr['lo'],gap_free_log=gr['free_leading_log'],thermal_model=name,lo=lo,shift=shift,C6=mod.lim[6],C7=mod.lim[7]))
    summary=dict(tested_combinations=len(out),ranges={key:[min(r[key] for r in out),max(r[key] for r in out)] for key in ('C6','C7')},extreme_C7_records=[min(out,key=lambda r:r['C7']),max(out,key=lambda r:r['C7'])])
    (D/'combined_stress_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (D/'combined_stress_results.json').write_text(json.dumps(out)+'\n')
    print(json.dumps(summary,indent=2))
