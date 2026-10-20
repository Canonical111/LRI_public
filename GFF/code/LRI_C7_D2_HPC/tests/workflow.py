#!/usr/bin/env python3
"""Tiny full-workflow tests. Graph subsets are labelled test-only, never physics."""
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import load,dump,digest

def call(*args,ok=True):
    p=subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
    if ok and p.returncode:raise RuntimeError(p.stderr[-4000:])
    if not ok and not p.returncode:raise AssertionError('Bad input accepted')
    return p

out=[]
with tempfile.TemporaryDirectory(prefix='c7d2_workflow_')as tmp:
 for mode in ('recompute','retained'):
    t=Path(tmp)/mode;backend='gmp'if(ROOT/'bin/c7d2_gmp').exists()else'decimal'
    call(ROOT/'tools/production.py','plan',t,'--seed',7611824,'--replicates',4,'--points',16,'--test-graphs',1,'--shards',1,'--threads',2,'--checkpoint-tasks',8,'--chunk-points',7,'--backend',backend,'--primitive-mode',mode)
    m=load(t/'manifest.json')
    call(ROOT/'tools/production.py','merge',t,ok=False)
    call(ROOT/'tools/production.py','run',t,'--index',0)
    ck=list((t/'groups'/m['jobs'][0]['group']/'checkpoints').glob('*.json'));hashes={p.name:digest(p)for p in ck}
    call(ROOT/'tools/production.py','run',t,'--index',0,'--threads',1)
    if hashes!={p.name:digest(p)for p in ck}:raise AssertionError('Restart rewrote checkpoint')
    p=ck[0];original=p.read_text();bad=json.loads(original);bad['native']['rows'][0]['values'][0]='0';p.write_text(json.dumps(bad))
    call(ROOT/'tools/production.py','run',t,'--index',0,ok=False);p.write_text(original)
    for i in range(1,len(m['jobs'])):call(ROOT/'tools/production.py','run',t,'--index',i)
    call(ROOT/'tools/production.py','merge',t)
    call(ROOT/'tools/assemble.py',t,'--bootstrap',64)
    r=load(t/'C7_result.json')
    if r['C7_full']is not None or not r['test_only']:raise AssertionError('Incomplete test presented as physical value')
    if (r['shared_reference_se']>0)!=(mode=='retained'):raise AssertionError('Wrong primitive covariance')
    if len(r['merged_sha256'])!=20:raise AssertionError('Incomplete group assembly')
    call(ROOT/'tools/assemble.py',t,'--bootstrap',64,ok=False)
    # Wrong-dimensional aggregate data are rejected even if otherwise parseable.
    gp=t/'groups'/m['groups'][0]['name']/'merged.json';saved=gp.read_text();d=load(gp);d['sector']='other';gp.write_text(json.dumps(d));call(ROOT/'tools/assemble.py',t,'--bootstrap',0,'--output',t/'bad.json',ok=False);gp.write_text(saved)
    out.append(dict(mode=mode,status='passed',backend=backend,groups=20,jobs=len(m['jobs']),checkpoint_restart_unchanged=True,corruption_rejected=True,incomplete_merge_rejected=True,result_no_clobber=True,shared_primitive_se=r['shared_reference_se'],test_result_full_C7_null=True))
p=ROOT/'benchmarks/workflow.json'
if p.exists():print(json.dumps(out,indent=2))
else:dump(p,out)
