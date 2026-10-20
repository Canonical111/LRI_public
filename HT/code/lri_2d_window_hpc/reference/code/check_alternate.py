#!/usr/bin/env python3
"""Evaluate the alternate root's parameters in an independent larger local space.
No retuning and no thermal target. This distinguishes another finite-parent root
from an artifact of using the learned span far from its training couplings.
"""
from pathlib import Path
import time,json
from ht2d.solver import DressedSolver
from run import atomic_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    r=json.loads((ROOT/'results/alternate_L12_x0.150.json').read_text());t=time.perf_counter()
    s=DressedSolver(12,32,256,window='vacuum',eig_tol=1e-12,ncv=48,residual_tol=1e-8)
    s.set_delta(.15);f,info,out,U=s.spectrum(r['theta'],k=5,diagnostics=True)
    E0=out[0][0][0]
    data={'x':.15,'L':12,'nz':32,'osc':256,'theta_fixed':r['theta'],
          'scope':'Independent larger-space fixed-coupling check of alternate numerical root; not a retuned curve point',
          'primary_residual':f.tolist(),'Delta_thermal':float(out[0][0][1]-E0),
          'even_gaps':(out[0][0]-E0).tolist(),'odd_gaps':(out[1][0]-E0).tolist(),
          'info':info,'seconds':time.perf_counter()-t}
    atomic_json(ROOT/'validation/alternate_root_reference.json',data);print(json.dumps(data,indent=2),flush=True)
if __name__=='__main__':main()
