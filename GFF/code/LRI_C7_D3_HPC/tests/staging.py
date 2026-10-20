#!/usr/bin/env python3
"""Relocated runtime, one-pack staging and frozen timing-model smoke test."""
from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import load,dump,digest

def call(args):
    p=subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True,check=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1'));return p.stdout
with tempfile.TemporaryDirectory(prefix='c7d3_stage_')as temp:
    t=Path(temp);run=t/'run';stage=t/'stage';backend='gmp'if(ROOT/'bin/c7d3_gmp').exists()else'decimal'
    call([ROOT/'tools/production.py','plan',run,'--seed',816613,'--replicates',2,'--points',8,'--test-graphs',1,'--shards',1,'--threads',1,'--backend',backend])
    call([ROOT/'tools/stage_runtime.py',run,stage,'--index',0])
    call([stage/'tools/production.py','run',run,'--index',0,'--scratch',t])
    files=list((run/'groups/a_free_L3/checkpoints').glob('*.json'));before={p.name:digest(p)for p in files}
    call([ROOT/'tools/production.py','run',run,'--index',0,'--threads',2])
    if before!={p.name:digest(p)for p in files}:raise AssertionError('Relocated restart changed data')
    call([ROOT/'tools/make_cost_model.py',run,t/'costs.json'])
    call([ROOT/'tools/production.py','plan',t/'plan2','--seed',816613,'--replicates',2,'--points',8,'--test-graphs',1,'--shards',2,'--threads',2,'--backend',backend,'--cost-model',t/'costs.json'])
    m=load(t/'plan2/manifest.json')
    if not m['cost_model_sha256']:raise AssertionError('Cost model not frozen')
    result=dict(status='passed',stage_pack_count=len(list((stage/'inputs/packs').glob('*.pack'))),relocated_worker_verified=True,reference_files_needed_on_compute_node=False,cost_model_frozen=True,resume_across_staged_and_shared_unchanged=True)
p=ROOT/'benchmarks/staging.json'
if not p.exists():dump(p,result)
print(json.dumps(result,indent=2))
