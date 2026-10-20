#!/usr/bin/env python3
"""Relocated runtime, member staging and frozen cost-model smoke test with the REAL native worker, for every built
backend (PLAN component F; C7(2)'s staging.py with 24 groups and member staging, A-ORC-7).
A test-only plan (tests/fixtures/inputs_mini, --test-graphs 1); tools/stage_runtime.py stages index 0 of the largest
L7 group (only the members of its blocks, at their offsets in a sparse pack); `production.py run` from the staged
copy commits its blocks; a rerun from the package with another thread count leaves them unchanged; a whole-pack copy
is refused above the 1 GB limit (the free L7 pack at a lowered limit); tools/make_cost_model.py on the finished and
merged campaign gives a cost model that a second plan freezes (measured basis, its sha256 in the manifest).
The record goes only to --output.
Usage: python3 -B tests/staging.py [--output FILE]"""
from pathlib import Path
import argparse,json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import digest,dump,environment_record,load

def call(args,ok=True):
    e=dict(os.environ,OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',C8_INPUTS=str(ROOT/'tests/fixtures/inputs_mini'))
    for k in [k for k in e if k.startswith(('SLURM_','SBATCH_','SQUEUE_'))]:e.pop(k)
    p=subprocess.run([sys.executable,'-B',*map(str,args)],capture_output=True,text=True,env=e)
    if ok and p.returncode:raise RuntimeError(f'{args}: exit {p.returncode}\n{p.stderr[-3000:]}')
    if not ok and not p.returncode:raise AssertionError(f'accepted: {args}')
    return p

def run(t:Path,backend:str)->dict:
    run=t/'run';stage=t/'stage';P=ROOT/'tools/production.py'
    call([P,'plan',run,'--seed',816613,'--pilot','--points',8,'--replicates',2,'--test-graphs',1,'--bootstrap-chunk',8,'--shards',1,'--threads',1,'--checkpoint-tasks',8,'--backend',backend])
    m=load(run/'manifest.json');j=next(x for x in m['jobs']if x['group']=='a_free_L7')
    call([ROOT/'tools/stage_runtime.py',run,stage,'--index',j['id']])
    pack=stage/'inputs/packs/free_L7.pack';full=ROOT/'inputs/packs/free_L7.pack'
    assert pack.stat().st_size==full.stat().st_size and not (stage/'vendor').exists()and not (stage/'reference').exists()
    inv={r['id']:r for r in load(ROOT/'tests/fixtures/inputs_mini/inventory.json')['free']['7']}
    gids={int(l.split()[2])for l in (run/j['tasks_file']).read_text().splitlines()}
    data=pack.read_bytes();src=full.read_bytes()
    for g in gids:r=inv[g];assert data[r['offset']:r['offset']+r['length']]==src[r['offset']:r['offset']+r['length']]
    other=[r for g,r in inv.items()if g not in gids][:50];assert all(not any(data[r['offset']:r['offset']+r['length']])for r in other),'a non-member was staged'
    call([stage/'tools/production.py','run',run,'--index',j['id'],'--scratch',t])
    files=sorted((run/'groups/a_free_L7/checkpoints').glob(f's{j["shard"]:06d}_p*.json'));before={p.name:digest(p)for p in files}
    if not files:raise AssertionError('the staged run committed nothing')
    call([P,'run',run,'--index',j['id'],'--threads',2])
    if before!={p.name:digest(p)for p in files}:raise AssertionError('a relocated restart changed data')
    r=subprocess.run([sys.executable,'-B','-c','import sys;sys.path.insert(0,sys.argv[1]);import stage_runtime as s;s.WHOLE_PACK_LIMIT=1000\n'
                      'try:s.stage(__import__("pathlib").Path(sys.argv[2]),__import__("pathlib").Path(sys.argv[3]),int(sys.argv[4]),True)\n'
                      'except ValueError as e:print("REFUSED",e);sys.exit(3)',str(ROOT/'tools'),str(run),str(t/'stage_whole'),str(j['id'])],capture_output=True,text=True,
                     env=dict(os.environ,C8_INPUTS=str(ROOT/'tests/fixtures/inputs_mini'),PYTHONDONTWRITEBYTECODE='1'))
    assert r.returncode==3 and '> 1 GB'in r.stdout,(r.stdout,r.stderr[-500:])
    for x in m['jobs']:call([P,'run',run,'--index',x['id'],'--threads',2,'--scratch',t])
    call([P,'merge',run,'--jobs',2]);call([ROOT/'tools/make_cost_model.py',run,t/'costs.json'])
    call([P,'plan',t/'plan2','--seed',816614,'--pilot','--points',8,'--replicates',2,'--test-graphs',1,'--shards',2,'--threads',2,'--backend',backend,'--cost-model',t/'costs.json'])
    m2=load(t/'plan2/manifest.json')
    if m2.get('cost_model_sha256')!=digest(t/'costs.json')or m2.get('cost_basis')!='measured':raise AssertionError('the cost model was not frozen')
    return dict(backend=backend,status='passed',members_staged=len(gids),pack_members=len(inv),relocated_worker_verified=True,vendor_and_reference_not_staged=True,
                whole_pack_above_limit_refused=True,cost_model_frozen=True,resume_across_staged_and_shared_unchanged=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path,help='write the JSON record here');a=ap.parse_args();res=[]
    for backend in (b for b in ('decimal','gmp')if (ROOT/f'bin/c8d2_{b}').exists()):
        with tempfile.TemporaryDirectory(prefix='c8d2_stage_',dir=os.environ.get('TMPDIR'))as temp:res.append(run(Path(temp),backend))
    if not res:raise SystemExit('build bin/c8d2_decimal and bin/c8d2_gmp (make && make gmp) first')
    rec={'status':'passed','tests':res,'environment':environment_record()}
    if a.output:dump(a.output,rec)
    print(json.dumps(rec,indent=2,default=str))
