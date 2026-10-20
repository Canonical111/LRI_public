#!/usr/bin/env python3
"""Assemble completed direct-coefficient data and artificial-regulator fits.

No proposed value of C2 is an input. Model spreads are numerical diagnostics,
not certified uncertainty intervals. Run after analyze_extended.py to include
new larger-cutoff checks; their recorded fits are retained in the archive.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import mpmath as mp
from regulator_extrapolation import pick_current,basis
ROOT=Path(__file__).parent

def fit(points,terms,weighted=False):
    x=np.array([p['lam'] for p in points]);y=np.array([p['h_estimate'] for p in points])
    s=np.array([max(1e-4,p['spectral_model_half_spread']) for p in points])
    A=np.array([np.ones_like(x)]+[basis(x,t) for t in terms]).T
    B=A/s[:,None] if weighted else A;b=y/s if weighted else y
    c=np.linalg.lstsq(B,b,rcond=None)[0];res=A@c-y
    # Linear sensitivities of h0 to each finite-regulator input.
    influence=np.linalg.pinv(B)[0]/s if weighted else np.linalg.pinv(B)[0]
    # This is a propagation diagnostic, not a statistical standard deviation.
    sensitivity=float(np.sum(abs(influence)*np.array([p['spectral_model_half_spread'] for p in points])))
    return dict(order=points[0]['order'],lambdas=x.tolist(),terms=terms,weighted=weighted,
                h0=float(c[0]),coefficients=c.tolist(),max_residual=float(np.max(abs(res))),
                condition=float(np.linalg.cond(B)),number_of_points=len(x),number_of_parameters=len(c),
                spectral_half_spread_linear_L1=sensitivity)

def main():
    mp.mp.dps=50
    b0=9*mp.pi**2/8*(mp.gamma(mp.mpf(3)/4)/mp.gamma(mp.mpf(1)/4))**2
    a1=-mp.pi**2/4
    points=pick_current()
    for p in points:p['coefficient_cutoff']=256;p['data_file']=f"fine_k{p['order']}_a{p['lam']}.json"
    ext=ROOT/'extended_analysis.json'
    if ext.exists():
      for r in json.loads(ext.read_text()):
        p=dict(order=r['order'],lam=r['lam'],h_estimate=r['selected']['median'],
               spectral_model_half_spread=r['selected']['half_spread'],coefficient_cutoff=r['N'],
               data_file=f"extended_k{r['order']}_a{r['lam']}.json",cauchy_grid_comparison=r.get('cauchy_grid_comparison'))
        points=[x for x in points if (x['order'],x['lam'])!=(p['order'],p['lam'])];points.append(p)
    # The optional large-lambda check is lower cutoff and labelled separately.
    extra=ROOT/'large_lambda_k3_a0.5.json'
    if extra.exists():
        z=json.loads(extra.read_text())
        # Saved structure is inspected below; no reference coefficient is used.
        f=z['tail_fits'];v=np.array([x['limit'] for x in f if len(x['powers'])>=3 and x['Nmin']>=80])
        if not len(v):raise ValueError('No saved large-lambda tail fits selected.')
        points.append(dict(order=3,lam=.5,h_estimate=float(np.median(v)),spectral_model_half_spread=float((max(v)-min(v))/2),
                           coefficient_cutoff=128,data_file=extra.name))
    points.sort(key=lambda p:(p['order'],p['lam']))
    models=[];preferred=[]
    for k in sorted(set(p['order'] for p in points)):
        rr=[p for p in points if p['order']==k]
        for lo in [0,1]:
          for n in range(3,len(rr)-lo+1):
            pp=rr[lo:lo+n]
            for terms in [['2','2log'],['2','3'],['2','2log','3'],['2','2log','4'],['2','3','4'],['2','2log','3','4']]:
              if len(terms)+1>len(pp):continue
              for weighted in [False,True]:
                out=fit(pp,terms,weighted)
                out['C2']=float(a1/b0+mp.mpf(out['h0'])/b0**2);models.append(out)
        out=fit(rr,['2','2log','3'],False)
        out['C2']=float(a1/b0+mp.mpf(out['h0'])/b0**2);preferred.append(out)
    result=dict(convention='delta=(7/4-s)/2; Delta_epsilon=1+C2*delta^2+...',
                method='Direct g^4 Hamiltonian energy sums; only artificial cutoffs are extrapolated.',
                b0=str(b0),a1=str(a1),a1_over_b0=str(a1/b0),
                data_points=points,representative_regulator_fits=preferred,model_sensitivity=models,
                uncertainty_status='Model and cutoff sensitivity, not a rigorous enclosure or statistical confidence interval.',
                claimed_precision='Approximate curvature only; no many-digit independent verification is claimed.')
    (ROOT/'FINAL_NUMERICAL_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    for p in points:print('POINT',p['order'],p['lam'],p['coefficient_cutoff'],p['h_estimate'],p['spectral_model_half_spread'])
    for p in preferred:print('CONTINUUM',p['order'],p['h0'],p['C2'],p['max_residual'],p['spectral_half_spread_linear_L1'])

if __name__=='__main__':main()
