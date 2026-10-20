#!/usr/bin/env python3
"""Retuned thermal coefficients through epsilon^7 with ONLY g(eps)^2 D(eps).
This is partial matching, not a complete effective Hamiltonian. Separate outputs
and fingerprints prevent accidentally resuming a raw production checkpoint.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, resource
from pathlib import Path
import numpy as np
from numba import set_num_threads
from lri_hpc.operators import Space, quotient_components
from lri_hpc.solver import calibrate, fixed_wave, vacuum_quotient, vacuum_table, extract, second_order_shell_value, atomic_json, source_fingerprint

def compute(cutoff: int, degree: int=7, corrected: bool=True, memory_limit_gib: float=3.2, difference_basis: bool=False):
    if degree not in (4,5,6,7): raise ValueError('degree 4,5,6,7 only')
    if cutoff<4 or cutoff%2: raise ValueError('even cutoff >=4 required')
    start=time.perf_counter();order=degree//2
    reach=(degree-2)//2 if difference_basis else order
    space=Space(cutoff,3+4*reach,4*reach,degree-1,memory_limit_gib=memory_limit_gib)
    psis,elow,r,g=calibrate(space,order)
    # D_j vanish on ALL primary reference states p=0,1,2,3. Therefore tuning
    # and wavefunctions up to second order do not change. At wave order three
    # the only change is R'_0 g1^2 D0 psi1. It must NOT be omitted for C6,C7.
    if corrected and order>=3:
        sums=vacuum_table(cutoff,0)
        upper=np.maximum(0,(4*cutoff-4*space.N-space.P)//4)
        D0=-(sums[cutoff,0]-sums[upper,0])/6
    else:D0=None
    components={}
    for p in (0,1,3,2):
        psi=psis.pop(p) if p in psis else fixed_wave(space,p,order,r,g)[0]
        if D0 is not None:
            den=p/4-space.Efree
            sel=(space.N%2==0)&(space.P%2==p%2)&(den!=0)
            psi[sel,3]+=g[1]**2*D0[sel]*psi[sel,1]/den[sel]
        F,M,V=quotient_components(space,psi,degree,parity=p%2)
        c={'F':F.tolist(),'M':M.tolist(),'V':V.tolist()}
        if corrected:c['K']=vacuum_quotient(space,psi,degree-2).tolist()
        components[p]=c
        del psi
    out,_=extract(components,[0,1,3,2],degree,corrected)
    residual=out['C'][2]-second_order_shell_value(cutoff)
    if not np.all(np.isfinite(out['C']+out['r']+out['g'])):raise ArithmeticError('nonfinite')
    if abs(residual)>1e-10 or out['tuning_residual']>1e-6:raise ArithmeticError('acceptance failed')
    out.update(cutoff=cutoff,degree=degree,prescription='isolated_vacuum_matched' if corrected else 'raw',
        matching_scope='ONLY g(eps)^2 D(eps), retuned at all orders; not complete order-g^3 or higher matching',
        particle_cap=3+4*reach,nonzero_particle_cap=4*reach,basis_dimension=space.global_dim,
        difference_basis=difference_basis,
        coefficient_scope=("Reduced-basis coefficients: use only paired differences" if difference_basis else "Complete coefficients for the stated finite-cutoff prescription"),
        shell_residual=residual,seconds=time.perf_counter()-start,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        source_sha256=source_fingerprint(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cutoffs',type=int,nargs='+',required=True)
    ap.add_argument('--degree',type=int,default=7)
    ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--memory-limit-gib',type=float,default=3.2)
    ap.add_argument('--output-dir',type=Path,default=Path('results/vacuum_matched'))
    ap.add_argument('--raw',action='store_true')
    args=ap.parse_args();set_num_threads(args.threads)
    for cutoff in args.cutoffs:
        r=compute(cutoff,args.degree,not args.raw,args.memory_limit_gib)
        path=args.output_dir/f'{r["prescription"]}_L{cutoff}_d{args.degree}.json'
        if path.exists():raise FileExistsError(f'{path}; use a fresh output directory')
        atomic_json(path,r);print(json.dumps(r),flush=True)
if __name__=='__main__':main()
