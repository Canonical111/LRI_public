#!/usr/bin/env python3
"""Separate phi6 cubic-coefficient fits and genuinely held-out larger cutoffs."""
from analyze_joint import *
if __name__=='__main__':
    gaps=load(['phi6_validation.json','phi6_production.json','phi6_extension.json','phi6_thin3.json','phi6_thin3_extension.json'])
    L=np.array([r['cutoff'] for r in gaps],float)
    Y=np.array([r['raw']['D6'][:4] for r in gaps]);rows=[]
    for name,ts in MODELS.items():
     for lo in [12,16,20,24,28,32]:
      for free in (False,True):
       for hi in (58,80,96,112,128):
        m=(L>=lo)&(L<=hi)
        try:mo=GapModel(ts,'raw',free).fit(L[m],Y[m],3)
        except ValueError:continue
        h=L>hi;err=float(max(abs(mo.predict(L[h],Y[h,2]).ravel()-Y[h,3]))) if h.any() else None
        rows.append(dict(model=name,lo=lo,hi=hi,free_log=free,omega3=mo.lim[3],diagnostics=mo.diag[3],actual_log_coefficient_over_x=float(mo.par[3][2]-3.5) if free else -3.5,heldout_error=err))
    (D/'omega3_extended_fits.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('Wrote',len(rows),'gap-only fits.')
