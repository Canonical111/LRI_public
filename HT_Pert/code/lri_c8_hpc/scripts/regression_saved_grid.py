#!/usr/bin/env python3
"""Replay ALL retained raw and isolated-vacuum C8 points, not continuum fitting."""
import os
for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ.setdefault(k,'1')
import argparse,json,time,sys
from pathlib import Path
import numpy as np,numba
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_c8.engine import compute
from lri_c8.io import source_digest
# The default output is outside the manifest; benchmarks/REGRESSION_GRID.json is the
# bundled cross-stack reference and is only read (--compare).
p=argparse.ArgumentParser();p.add_argument('--threads',type=int,default=4);p.add_argument('--output',type=Path,default=ROOT/'validation/regression_grid.json')
p.add_argument('--compare',type=Path,help='earlier grid file; C8 must agree within atol 1e-7 + rtol 2e-11');a=p.parse_args()
numba.set_num_threads(a.threads);rows=[]
for scheme in ('raw','vacuum_only'):
 for path in sorted((ROOT/'inputs'/scheme).glob('*.json'),key=lambda p:json.loads(p.read_text())['cutoff']):
  b=json.loads(path.read_text());L=b['cutoff'];r=compute(L,scheme)
  residuals={k:float(np.max(abs(np.array(r[k])-b[k]))) for k in ('C','r','g','energies')}
  for k in residuals:np.testing.assert_allclose(r[k],b[k],atol=1e-7,rtol=2e-11)
  row={'cutoff':L,'scheme':scheme,'max_abs':residuals,'C8':r['C'][8],
       'shell':r['second_order_shell_residual'],'tuning':r['tuning_residual'],'seconds':r['seconds']}
  rows.append(row);print(scheme,L,residuals,flush=True)
  a.output.parent.mkdir(parents=True,exist_ok=True)
  a.output.write_text(json.dumps({'source_sha256':source_digest(),'records':rows,'completed':False},indent=2)+'\n')
summary={'source_sha256':source_digest(),'records':rows,'completed':True}
if a.compare:
 old={(x['scheme'],x['cutoff']):x['C8'] for x in json.loads(a.compare.read_text())['records']}
 if set(old)!={(x['scheme'],x['cutoff']) for x in rows}:raise SystemExit('Compared grid has different points')
 diff=[abs(x['C8']-old[x['scheme'],x['cutoff']]) for x in rows]
 bad=[x for x,d in zip(rows,diff) if d>1e-7+2e-11*abs(old[x['scheme'],x['cutoff']])]
 summary['comparison']={'file':str(a.compare),'max_abs_C8':max(diff),'bitwise_equal':sum(d==0 for d in diff),'points':len(rows),'outside_tolerance':len(bad)}
 print(summary['comparison'],flush=True)
a.output.write_text(json.dumps(summary,indent=2)+'\n')
if a.compare and summary['comparison']['outside_tolerance']:raise SystemExit('C8 differs from the compared grid')
