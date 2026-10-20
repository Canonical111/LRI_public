#!/usr/bin/env python3
"""Original retained C8 solver versus the optimized engine (stored and ranked) at one
cutoff beyond the saved grid, both prescriptions. Same caps P<=19,Q<=16 in both."""
import os
for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ.setdefault(k,'1')
import argparse,json,resource,sys,time
from pathlib import Path
import numpy as np,numba
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'reference/original_code')]
from lri_c8.engine import compute
from lri_c8.io import source_digest
import c8_solver
p=argparse.ArgumentParser();p.add_argument('--cutoff',type=int,default=60);p.add_argument('--threads',type=int,default=4)
p.add_argument('--output',type=Path,required=True);a=p.parse_args()
numba.set_num_threads(a.threads);rows=[];ok=True
for scheme in ('raw','vacuum_only'):
    t=time.time();o=c8_solver.compute(a.cutoff,8,scheme);t_orig=time.time()-t;new={}
    for backend in ('stored','ranked'):
        t=time.time();new[backend]=compute(a.cutoff,scheme,backend);new[backend+'_seconds']=time.time()-t
    s=new['stored'];row={'cutoff':a.cutoff,'scheme':scheme,'seconds':{'original':t_orig,'stored':new['stored_seconds'],
                         'ranked':new['ranked_seconds']},'C8_original':o['C'][8],'C8_new':s['C'][8]}
    row['stored_equals_ranked']=all(np.array_equal(s[k],new['ranked'][k]) for k in ('C','r','g','energies'))
    row['max_abs']={k:float(np.max(abs(np.array(s[k])-np.array(o[k])))) for k in ('C','r','g','energies')}
    try:
        for k in ('C','r','g','energies'):np.testing.assert_allclose(s[k],o[k],atol=1e-7,rtol=2e-11)
        row['within_tolerance']=True
    except AssertionError as e:row['within_tolerance']=False;row['error']=str(e)[:500]
    ok&=row['within_tolerance'] and row['stored_equals_ranked'];rows.append(row);print(json.dumps(row),flush=True)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps({'source_sha256':source_digest(),'threads':a.threads,'records':rows,'pass':ok,
                                'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2)+'\n')
raise SystemExit(0 if ok else 1)
