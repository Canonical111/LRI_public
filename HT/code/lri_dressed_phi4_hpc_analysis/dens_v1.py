"""Cutoff extrapolation of the density-basis campaign dens_v1.

Input: dens_v1_rows.json, produced on symmetry by
campaigns/dump_dens_v1.py. The campaign used the 16-state density basis (keep-24 artifacts trained at L=24,
teacher nz48, osc384) with the consistent window, at even N=12..40 for all 13 Δσ, plus 24-state controls.
Fits are the same F1/F2/F3 x Nmin family and acceptance as extrapolate.py. The quoted value is stable only if
n_fits>=5, omega>=0.45 and spread<=2e-3, as in compare_nrg.py.
Outputs: a markdown table on stdout and dens_v1_extrapolation.json.
"""
import json,io,math,contextlib
from pathlib import Path
import numpy as np
D=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    import extrapolate as E
rows=json.load(open(D/'dens_v1_rows.json'))
nrg={round(r['ds'],6):r for r in json.load(open(D/'nrg/ds13_final.json'))}
old={(r['delta'],r['prescription']):r for r in json.load(open(D/'extrapolation.json'))['results']}
GRID=[0.249,0.24,0.225,0.2,0.175,0.15,0.125,0.1,0.075,0.05,0.025,0.01,0.001]

def ser(d,nz):
    return dict(sorted((r['N'],r['Delta_thermal']) for r in rows if abs(r['delta']-d)<1e-12 and r['nz']==nz))

def stable(sm):return bool(sm) and sm['n_fits']>=5 and sm['omega_median']>=0.45 and sm['spread_half']<=2e-3

out=[]
print('| Δσ | N range | Δ(N_max) | dΔ/dlnN at N_max | D∞ (dens16) | ω | n_fits | old window D∞ | NRG ± | D∞ − NRG | ε-series (≤ε⁷) |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for d in GRID:
    s=ser(d,16)
    if len(s)<6:continue
    Ns=list(s);y=list(s.values())
    slope=(y[-1]-y[-2])/math.log(Ns[-1]/Ns[-2])
    fl=E.fits(s);sm=E.summarize(fl,y[-1])
    ok=stable(sm)
    o=old.get((d,'window'),{});of=o.get('fit')
    n=nrg.get(d)
    es=E.eps_series(d,7) if d>=0.24 else None
    val=sm['D_inf'] if ok else None
    print('| %g | %d–%d | %.6f | %+.2e | %s | %s | %s | %s | %s | %s | %s |'%(d,Ns[0],Ns[-1],y[-1],slope,
        ('%.6f ± %.6f'%(sm['D_inf'],sm['spread_half'])) if ok else ('(%.5f ± %.4f, unstable)'%(sm['D_inf'],sm['spread_half']) if sm else '—'),
        '%.2f'%sm['omega_median'] if sm else '—',sm['n_fits'] if sm else 0,
        '%.6f'%of['D_inf'] if of else '—',('%.5f ± %.5f'%(n['Delta_E'],n['total_uncertainty'])) if n else '—',
        ('%+.5f'%(val-n['Delta_E'])) if (val is not None and n) else '—','%.7f'%es if es else ''))
    out.append(dict(delta=d,cuts=Ns,values=y,slope_lnN=slope,fit=sm,stable=ok,fits=fl,nrg=n,old_window=of,eps_series7=es))

print('\n24-state controls (dens24 − dens16):')
for r in sorted([r for r in rows if r['nz']==24],key=lambda r:(-r['delta'],r['N'])):
    s16=ser(r['delta'],16)
    if r['N'] in s16:print('  Δσ=%-6g N=%d  %+.2e'%(r['delta'],r['N'],r['Delta_thermal']-s16[r['N']]))
json.dump(out,open(D/'dens_v1_extrapolation.json','w'),indent=1)
