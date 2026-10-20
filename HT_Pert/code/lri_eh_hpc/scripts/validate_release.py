#!/usr/bin/env python3
"""Issue a source/dependency-bound receipt only after tests and smoke gates pass."""
import argparse,os,sys,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--threads',type=int,default=4);a=ap.parse_args()
if a.threads<4:raise ValueError('Validation suite includes a four-thread test; request at least four CPUs')
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['NUMBA_NUM_THREADS']=str(a.threads)
os.environ['PYTHONPATH']=str(ROOT)+os.pathsep+os.environ.get('PYTHONPATH','')
from lri_eh.runtime import claim,atomic_json,seal,fingerprint,config,environment
from lri_eh.runner import run
with claim(a.output.with_suffix('.lock')):
    if a.output.exists():raise FileExistsError(a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    logfile=a.output.with_suffix('.tests.log')
    with logfile.open('x') as f:
        p=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'tests')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError('Tests failed; no validation receipt was issued. Read '+str(logfile))
    smoke=run(20,7,a.output.with_suffix('.smoke'),a.threads,3.)
    receipt=seal(dict(kind='lri-eh-validation',passed=True,source_sha256=fingerprint(),
                      dependencies=config(4,7)['dependencies'],environment=environment(),time=time.time(),
                      tests_log=str(logfile.resolve()),smoke_payload_sha256=smoke['payload_sha256'],
                      limits='Local test gates only; not evidence of multi-node speedup or complete physical matching.'))
    atomic_json(a.output,receipt)
    print('PASS:',a.output,receipt['source_sha256'])
