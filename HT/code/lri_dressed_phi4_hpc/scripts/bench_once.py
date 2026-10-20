#!/usr/bin/env python3
"""Fresh-process benchmark; times exclude Numba warmup, include solver setup."""
import os,sys,json,time,resource,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'src'),str(root/'reference')]
p=argparse.ArgumentParser();p.add_argument('--impl',choices=['reference','tensor','ladder'],required=True);p.add_argument('--N',type=int,default=12);p.add_argument('--nz',type=int,default=20);p.add_argument('--osc',type=int,default=160);p.add_argument('--delta',type=float,default=.1);p.add_argument('--threads',type=int,default=1);p.add_argument('--seed',required=True);p.add_argument('--out',required=True);a=p.parse_args()
import numpy as np
from numba import set_num_threads
from threadpoolctl import threadpool_limits,threadpool_info
set_num_threads(a.threads);threadpool_limits(1)
warm=0.
if a.impl!='reference':
 from lri_dressed.solver import DressedSolver
 t=time.perf_counter();hh=DressedSolver(4,3,24,backend=a.impl);hh.set_delta(.2);hh.spectrum(hh.initial(.2),k=3);hh.response_jacobian(hh.initial(.2),hh.spectrum(hh.initial(.2),k=3)[2],hh.spectrum(hh.initial(.2),k=3)[3]);del hh;warm=time.perf_counter()-t
else:
 from fast_response import FastDressedZero
seed=np.array(json.loads(Path(a.seed).read_text())['theta'])+np.array([.03,.001])
t=time.perf_counter()
if a.impl=='reference':h=FastDressedZero(a.N,a.nz,a.osc)
else:h=DressedSolver(a.N,a.nz,a.osc,backend=a.impl)
h.set_delta(a.delta);row=h.solve(seed);wall=time.perf_counter()-t
r={'implementation':a.impl,'N':a.N,'nz':a.nz,'osc':a.osc,'delta':a.delta,'threads':a.threads,'wall_setup_and_solve_seconds':wall,'jit_warmup_seconds':warm,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'result':row,'threadpools':threadpool_info()}
Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(r,indent=2,allow_nan=False))
print(a.impl,a.threads,a.N,'wall',wall,'rss',r['peak_rss_mib'],'DE',row['Delta_thermal'],'calls',row['spectral_evaluations'])
