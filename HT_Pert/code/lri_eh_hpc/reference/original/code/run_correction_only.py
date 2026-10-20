#!/usr/bin/env python3
"""Compute exact paired partial-matching corrections without repeating full C7.

Through degree d, any difference contains at least one g^2 D insertion (cost 2).
The remaining closed walk has weight <=d-2 and changes P by at most 4 per unit.
It reaches at most 4 floor((d-2)/2) particles beyond the reference, and that many
nonzero-mode quanta. At d=7 this gives P<=11,Q<=8 instead of P<=15,Q<=12.
The two reduced spectra separately are NOT complete raw/modified C6,C7 values.
Only their paired delta C,delta r,delta g is exported for use on campaign data.
"""
import argparse,json,hashlib
from pathlib import Path
from numba import set_num_threads
import numpy as np
from run_vacuum_matched import compute
from lri_hpc.solver import atomic_json

def correction(L,degree=7,memory_limit_gib=3.2):
    raw=compute(L,degree,False,memory_limit_gib,True)
    vac=compute(L,degree,True,memory_limit_gib,True)
    out=dict(cutoff=L,degree=degree,prescription_change='raw -> isolated g(eps)^2 D(eps), both primary gaps retuned',
         scope='Complete paired difference for this ONE matched contribution; not full high-order Hamiltonian matching',
         particle_cap=raw['particle_cap'],nonzero_particle_cap=raw['nonzero_particle_cap'],basis_dimension=raw['basis_dimension'])
    for k in ('C','r','g'):out['delta_'+k]=(np.array(vac[k])-np.array(raw[k])).tolist()
    out['validation']=dict(max_raw_vacuum_shell_residual=max(abs(raw['shell_residual']),abs(vac['shell_residual'])),
                          max_tuning_residual=max(raw['tuning_residual'],vac['tuning_residual']))
    if max(abs(x) for x in out['delta_C'][:4])>1e-10:raise ArithmeticError('lower order invariance failed')
    if not np.all(np.isfinite(out['delta_C'])):raise ArithmeticError('nonfinite')
    out.update(source_sha256=raw['source_sha256'],driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               seconds=raw['seconds']+vac['seconds'],peakrss_kib=max(raw['maxrss_kib'],vac['maxrss_kib']))
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cutoffs',type=int,nargs='+',required=True)
    ap.add_argument('--degree',type=int,default=7);ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--memory-limit-gib',type=float,default=3.2)
    ap.add_argument('--output-dir',type=Path,default=Path('results/correction_only'))
    a=ap.parse_args();set_num_threads(a.threads)
    for L in a.cutoffs:
        path=a.output_dir/f'vacuum_delta_L{L}_d{a.degree}.json'
        if path.exists():raise FileExistsError(path)
        result=correction(L,a.degree,a.memory_limit_gib);atomic_json(path,result);print(json.dumps(result),flush=True)
