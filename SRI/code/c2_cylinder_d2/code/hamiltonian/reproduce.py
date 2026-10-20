#!/usr/bin/env python3
"""Recompute direct g^4 spectral coefficients at specified artificial cutoffs.

Example (small demonstration, not a continuum result):
  OPENBLAS_NUM_THREADS=1 python reproduce.py --cutoff 64 --order 1 --lam .25

The physical delta is not sampled. Run validate.py for independent finite checks.
Large coefficient grids require substantial memory and disk; see README.md.
"""
from __future__ import annotations
import argparse,json,os,time,gc,multiprocessing as mp
from pathlib import Path
import numpy as np

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cutoff',type=int,default=64)
    p.add_argument('--order',type=int,choices=[1,2,3],default=1)
    p.add_argument('--lam',type=float,nargs='+',default=[.25])
    p.add_argument('--mixed-cutoff',type=int,default=4096)
    p.add_argument('--collapsed-cutoff',type=int,default=800000)
    p.add_argument('--oversample',type=int,default=5)
    p.add_argument('--radius-cost',type=float,default=4.)
    p.add_argument('--workers',type=int,default=1)
    p.add_argument('--coefficients',type=Path)
    p.add_argument('--output-prefix',default='recomputed')
    p.add_argument('--tail-cutoff',type=int,default=None,
                   help='Two-index cutoff of the diagnostic leading-tail sidecar (default: LRI_TAIL_CUTOFF or 2048).')
    a=p.parse_args()
    if a.cutoff<4 or a.mixed_cutoff<16 or a.collapsed_cutoff<1000:
        p.error('Cutoffs are too small for the implemented checks.')
    if any(x<=0 for x in a.lam) or a.oversample<3 or a.radius_cost<=0 or a.workers<1:
        p.error('Lambda, radius cost and worker count must be positive; oversampling must be >=3.')
    os.environ.setdefault('LRI_FFT_WORKERS',str(a.workers))
    from resummed import ROOT
    from lowmemory import raw_sequence
    import resummed_improved as ri
    from mixed_sequence import run as mixed_run,extrapolate as mixed_extrap
    from improved_regulator import planar_constants,curvature_thermal
    from exact_leading_tail import evaluate as leading_tail,configured_tail_cutoff
    from analyze_fine import analyze
    from analyze_leading_tail import fits_with_tail
    try:tail_cutoff=configured_tail_cutoff() if a.tail_cutoff is None else a.tail_cutoff
    except ValueError as e:p.error(str(e))
    if tail_cutoff<64:p.error('--tail-cutoff must be >= 64.')
    ri.ORDER=a.order
    if a.coefficients is not None:
        if not a.coefficients.is_file():p.error(f'Coefficient file not found: {a.coefficients}')
        fn=a.coefficients
    else:
        K=a.cutoff+1
        if a.workers>1 and 'fork' in mp.get_all_start_methods():
            from parallel_coefficients import compute
            fn=ROOT/f'parallel_coeff4_K{K}_o{a.oversample}_r{a.radius_cost}.npy'
            if not (fn.is_file() and fn.with_suffix('.json').is_file()):
                fn=Path(compute(K,a.oversample,a.radius_cost,a.workers)[0])
        else:
            from fast_coefficients import compute
            fn=ROOT/f'fast_coeff4_K{K}_o{a.oversample}_r{a.radius_cost}.npy'
            if not (fn.is_file() and fn.with_suffix('.json').is_file()):
                fn=Path(compute(K,a.oversample,a.radius_cost)[0])
    base=np.load(fn,mmap_mode='r')
    if base.shape!=(6,a.cutoff+1,a.cutoff+1,a.cutoff+1):
        p.error(f'Expected coefficient shape {(6,)+(a.cutoff+1,)*3}; found {base.shape}.')
    ct=planar_constants(a.order,512);cv=curvature_thermal(a.order,512)
    for lam in a.lam:
        start=time.time();mix=mixed_run(lam,a.order,a.mixed_cutoff);mix['fits']=mixed_extrap(mix['Xmixed'])
        b=ri.two_point(lam,a.collapsed_cutoff);gc.collect();raw=raw_sequence(base,lam,a.order)
        row=dict(order=a.order,lam=lam,N=a.cutoff,raw=raw,two_point=b,mixed=mix,planar=ct,curvature=cv,
                 coefficient_file=fn.name,seconds=time.time()-start,physical_C2_claimed=False)
        # A fixed-lambda row is not the physical coefficient. Numerical tails are diagnostic.
        dest=ROOT/f'{a.output_prefix}_k{a.order}_a{lam}_N{a.cutoff}.json'
        dest.write_text(json.dumps(row,indent=2)+'\n')
        if a.mixed_cutoff>=4096:
            an=analyze(row);tail=leading_tail(lam,a.order,tail_cutoff,b)
            an['leading_tail']=tail;an['fixed_leading_tail_fits']=fits_with_tail(an['sequence'],tail['asymptotic_tail_coefficient'])
            dest.with_name(dest.stem+'_analysis.json').write_text(json.dumps(an,indent=2)+'\n')
            print('Saved',dest.name,'finite-cutoff h =',an['last'],flush=True)
        else:print('Saved',dest.name,flush=True)
    print('These are coefficients at fixed regulator. The lambda -> 0 analysis is separate.')

if __name__=='__main__':
    main()
