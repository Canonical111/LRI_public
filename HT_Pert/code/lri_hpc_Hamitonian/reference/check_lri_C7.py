#!/usr/bin/env python3
"""Seventh-order finite-cutoff coefficients of the supplied two-coupling LRI Hamiltonian.

This computes bare Hamiltonian-cutoff coefficients, NOT a matched physical C7.
Third-order wavefunctions give a Rayleigh quotient accurate through eps^7:
its first possible error is O(eps^8). The P<=15 cap is exact at this order.
The u_n(eps) jets must nevertheless be retained through eps^6.

Run next to check_lri_hamiltonian.py:
    OPENBLAS_NUM_THREADS=1 python check_lri_C7.py --cutoffs 4 8 12 16 24 32
Use --validate at cutoffs <=8 for comparison with a full seventh-order recursion.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
import numpy as np
from check_lri_hamiltonian import FockSpace, initial_wavefunctions, quotient_components


def compute(cutoff: int, validate: bool = False) -> dict:
    if cutoff < 2 or cutoff % 2:
        raise ValueError('Use an even cutoff >=2.')
    if validate and cutoff > 8:
        raise ValueError('Full-recursion validation is limited to cutoff <=8.')
    t = time.perf_counter()
    degree = 7
    from compute_phi6 import GapSpace
    space = GapSpace(cutoff, pmax=15, degree=degree-1, qmax=12)
    psi, E3, r3, g3 = initial_wavefunctions(space, order=3)
    F, M, V = (np.zeros((4, degree+1)) for _ in range(3))
    for p in range(4):
        F[p], M[p], V[p] = quotient_components(space, psi[p], degree=degree)
    r = np.zeros(degree+1)
    g = np.zeros(degree+1)
    E = F.copy()
    for k in range(1, degree+1):
        for p in range(4):
            E[p,k] += sum(r[j]*M[p,k-j]+g[j]*V[p,k-j] for j in range(1,k))
        r[k] = ((-.25 if k == 1 else 0.)-(E[1,k]-E[0,k]))/2
        g[k] = ((.25 if k == 1 else 0.)-(E[3,k]-E[0,k])-6*r[k])/3
        E[:,k] += r[k]*M[:,0]+g[k]*V[:,0]
    C = E[2]-E[0]
    target1 = np.zeros(degree+1); target1[:2] = [.25,-.25]
    target3 = np.zeros(degree+1); target3[:2] = [.75,.25]
    out = dict(cutoff=cutoff, C=C.tolist(), r=r.tolist(), g=g.tolist(),
               basis_dimension=space.dim, particle_cap=15,
               low_order_residual=float(max(np.max(abs(E[:,:4]-E3)), np.max(abs(r[:4]-r3)), np.max(abs(g[:4]-g3)))),
               tuning_residual=float(max(np.max(abs(E[1]-E[0]-target1)),np.max(abs(E[3]-E[0]-target3)))),
               seconds=time.perf_counter()-t,
               scope='Finite-cutoff coefficients of the unmodified two-coupling Hamiltonian; no continuum C7 is asserted.')
    if validate:
        full = FockSpace(cutoff, pmax=4*cutoff, degree=degree-1)
        _, Er, rr, gr = initial_wavefunctions(full, order=degree)
        out['full_recursion_max_abs_residual'] = float(max(np.max(abs(C-(Er[2]-Er[0]))),np.max(abs(r-rr)),np.max(abs(g-gr))))
    return out

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cutoffs', nargs='+', type=int, default=[4,8,12,16,24,32])
    p.add_argument('--validate', action='store_true')
    p.add_argument('--output', type=Path, default=Path('C7_finite_cutoffs.json'))
    args=p.parse_args(); rows=[]
    for cutoff in args.cutoffs:
        row=compute(cutoff,args.validate); rows.append(row)
        print(json.dumps(row),flush=True)
        args.output.write_text(json.dumps(rows,indent=2)+'\n')
