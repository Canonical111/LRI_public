#!/usr/bin/env python3
"""Pin and compare the unchanged none/consistent/literal paths against e2ca07c.

Compares numerical arrays bit-for-bit in independent subprocesses. It does not
compare timings, provenance hashes (intentionally new), or physical accuracy.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from baseline_equality import tree_fingerprint
from lri_dressed.io import atomic_json
PIN='1faa8a83557e5855531b46e8dac25c4ab8dd3d784adf848642bf786269525bfd'
CHILD=r'''
import json,sys
from numba import set_num_threads
from threadpoolctl import threadpool_limits
from lri_dressed.solver import DressedSolver
from lri_dressed.io import source_fingerprint
threadpool_limits(1);set_num_threads(int(sys.argv[5]))
x=float(sys.argv[1]);mode=sys.argv[2];theta=json.load(open(sys.argv[3]))['theta']
s=DressedSolver(8,24,192,backend='tensor',window='none' if mode=='none' else 'vacuum',window_mode='consistent' if mode=='none' else mode)
s.set_delta(x);row=s.solve(theta)
keys=['theta','even_gaps','odd_gaps','Delta_thermal']
out={k:row[k] for k in keys}
if mode!='none':out['D_by_N']=row['window_correction']['D_by_N'];out['Ev']=row['window_correction']['Ev']
print(json.dumps({'numbers':out,'source':source_fingerprint(),'module':__import__('lri_dressed.solver',fromlist=['a']).__file__}))
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',default=str(ROOT/'reference/production_e2ca07c'))
    p.add_argument('--output',required=True);p.add_argument('--threads',type=int,default=1)
    a=p.parse_args();old=Path(a.baseline).resolve()
    if tree_fingerprint(old)!=PIN or old==ROOT:
        raise ValueError('Not the pinned e2ca07c numerical source tree')
    rows=[];start=time.perf_counter()
    for x,mode in ((.24,'none'),(.1,'none'),(.1,'consistent'),(.05,'consistent'),(.01,'consistent'),(.1,'literal')):
        seed=ROOT/'inputs'/f'N16_z24_o192_d{x:.8f}.json'
        got=[]
        for root,sha in ((old,PIN),(ROOT,tree_fingerprint(ROOT))):
            env=dict(os.environ,PYTHONPATH=str(root/'src'),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS=str(a.threads))
            proc=subprocess.run([sys.executable,'-c',CHILD,repr(x),mode,str(seed),'unused',str(a.threads)],cwd=root,env=env,capture_output=True,text=True)
            if proc.returncode:raise RuntimeError(proc.stderr[-4000:])
            value=json.loads(proc.stdout.splitlines()[-1])
            if value['source']!=sha or not Path(value['module']).resolve().is_relative_to(root/'src'):
                raise RuntimeError('Subprocess imported an unexpected solver')
            got.append(value)
        equal=got[0]['numbers']==got[1]['numbers']
        rows.append({'delta':x,'window_mode':mode,'bit_equal':equal,'reference':got[0],'candidate':got[1]})
        print(x,mode,'numerically bit equal:',equal,flush=True)
    passed=all(r['bit_equal'] for r in rows)
    atomic_json(a.output,{'passed':passed,'reference_source_sha256':PIN,'seconds':time.perf_counter()-start,'records':rows})
    return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
