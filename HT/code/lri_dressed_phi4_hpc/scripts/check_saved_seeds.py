#!/usr/bin/env python3
"""Recompute selected supplied spectra; this is regression, not physical matching."""
import argparse,json,sys,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
p=argparse.ArgumentParser();p.add_argument('--output',default=str(ROOT/'results/saved_seed_regression.json'));p.add_argument('--threads',type=int,default=4)
a=p.parse_args()
from threadpoolctl import threadpool_limits
from numba import set_num_threads
import numpy as np
from lri_dressed.solver import DressedSolver
threadpool_limits(1);set_num_threads(a.threads)
allrows=[];out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
for N,z,o,ds in [(16,24,192,[.24,.2,.1,.05,.01]),(12,20,160,[.001,.0001])]:
    h=DressedSolver(N,z,o,backend='tensor')
    for d in ds:
        name=f'N{N}_z{z}_o{o}_d{d:.8f}.json'
        ref=json.loads((ROOT/'inputs'/name).read_text());h.set_delta(d)
        got=h.solve(ref['theta'])
        diff=max(float(np.max(abs(np.asarray(got[k])-ref[k]))) for k in ('even_gaps','odd_gaps'))
        np.testing.assert_allclose(got['even_gaps'],ref['even_gaps'],rtol=2e-9,atol=2e-9)
        np.testing.assert_allclose(got['odd_gaps'],ref['odd_gaps'],rtol=2e-9,atol=2e-9)
        allrows.append({'reference':name,'max_gap_difference':diff,'thermal_difference':got['Delta_thermal']-ref['Delta_thermal'],'result':got})
        print(name,'maxgapdiff',diff,'seconds',got['seconds'],flush=True)
        out.write_text(json.dumps(allrows,indent=2,allow_nan=False))
