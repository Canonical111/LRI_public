#!/usr/bin/env python3
"""Packaging entry points for analyses previously recorded without a CLI.

No proposed C2 is used. All writes are to this staged working directory.
The original scientific solver modules are otherwise retained.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent

def refresh_large() -> None:
    from analyze_fine import analyze
    from analyze_leading_tail import fits_with_tail
    path=ROOT/'large_lambda_k3_a0.5.json'
    if not path.exists(): return
    old=json.loads(path.read_text()); data=old.get('data',old)
    analysis=analyze(data)
    tails=json.loads((ROOT/'exact_leading_tail.json').read_text())
    matching=[t for t in tails if t['order']==analysis['order'] and t['lam']==analysis['lam']]
    if not matching:
        raise ValueError('Missing analytic leading-tail input for the large-lambda record')
    tail=max(matching,key=lambda t:t['N'])
    fitted=fits_with_tail(analysis['sequence'],tail['asymptotic_tail_coefficient'])
    path.write_text(json.dumps({'data':data,'analysis':analysis,'tail_fits':fitted},indent=2)+'\n')

def magnetic() -> None:
    # beta_improved.py computes the uncorrected planar result; the cylinder
    # thermal term contributes pi*c_cyl*lambda to the magnetic gap.
    import mpmath as mp
    from improved_regulator import curvature_thermal
    mp.mp.dps=40
    b0=float(9*mp.pi**2/8*(mp.gamma(mp.mpf(3)/4)/mp.gamma(mp.mpf(1)/4))**2)
    rows=[]
    for row in json.loads((ROOT/'beta_improved.json').read_text()):
        k=row['order']; lam=row['lam']
        if k<1: continue
        c=curvature_thermal(k,512)['thermal_lambda_coefficient']
        value=row['beta_planar']+np.pi*c*lam
        rows.append(dict(order=k,lam=lam,magnetic_g2_coefficient=float(value),error=float(value-b0)))
    (ROOT/'magnetic_calibration_improved.json').write_text(json.dumps(rows,indent=2)+'\n')

def coupling() -> None:
    from final_analysis import fit
    data=json.loads((ROOT/'FINAL_NUMERICAL_RESULTS.json').read_text()); b0=float(data['b0'])
    points=data['data_points']; rows=[]
    for order in [1,2,3]:
        base=[p for p in points if p['order']==order]
        for name,kind in [('included logarithm','included'),('omit logarithm','omit'),('reference scale e','scale')]:
            changed=[]
            for p in base:
                raw=json.loads((ROOT/p['data_file']).read_text()); raw=raw.get('data',raw)
                x2=raw['two_point']['X2']; lam=p['lam']
                shift=0. if kind=='included' else (2*b0*np.log(lam)*x2 if kind=='omit' else 2*b0*x2)
                changed.append(dict(p,h_estimate=p['h_estimate']+shift))
            z=fit(changed,['2','2log','3'],False)
            rows.append(dict(order=order,convention=name,h0=z['h0']))
    (ROOT/'coupling_scheme_recheck.json').write_text(json.dumps(rows,indent=2)+'\n')

def tables() -> None:
    d=json.loads((ROOT/'FINAL_NUMERICAL_RESULTS.json').read_text())
    def write(name,rows,keys):
        with (ROOT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
    write('fixed_regulator.csv',d['data_points'],['order','lam','coefficient_cutoff','h_estimate','spectral_model_half_spread','data_file'])
    write('continuum_estimates.csv',d['representative_regulator_fits'],['order','h0','C2','number_of_points','number_of_parameters','max_residual','condition','spectral_half_spread_linear_L1'])
    ranges=[]
    for k in [1,2,3]:
        vals=[x['C2'] for x in d['model_sensitivity'] if x['order']==k and not x['weighted'] and x['terms'] in [['2','2log','3'],['2','2log','4']]]
        ranges.append(dict(order=k,minimum=min(vals),maximum=max(vals),status='Selected model spread, not an error interval'))
    write('selected_model_ranges.csv',ranges,['order','minimum','maximum','status'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['refresh-large','magnetic','coupling','tables'])
    a=p.parse_args();{'refresh-large':refresh_large,'magnetic':magnetic,'coupling':coupling,'tables':tables}[a.action]()
if __name__=='__main__': main()
