#!/usr/bin/env python3
"""Tiny full-workflow tests with the REAL native worker (PLAN component F; C7(2)'s workflow.py with 24 groups), for every
built backend (bin/c8d2_decimal, bin/c8d2_gmp). The plans are test-only (tests/fixtures/inputs_mini, --test-graphs 1),
never physics. The campaign path holds '#', '?', '%' and a space (A-URI).
Covers: a merge of an incomplete campaign refused ("Incomplete campaign"); the job-private runtime removed after every
run; a deleted checkpoint recomputed with another thread count, its scientific fields unchanged; a corrupt checkpoint
rejected by run (the skip validates it) and merge; merge --jobs 2, an idempotent re-merge and an idempotent assembly; the test-only result
keys (no physical number at the top level, values under test_partial); merged data of the wrong sector rejected by
assemble. The record goes only to --output.
Usage: python3 -B tests/workflow.py [--output FILE]"""
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import digest,dump,environment_record,load
SCIENTIFIC=('uid','rep','graph','begin','end','total','values','quad','mp','max_abs','tail_top','tail_sum','tail_argmax')

def call(*args,ok=True,env=None):
    e=dict(os.environ,OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',C8_INPUTS=str(ROOT/'tests/fixtures/inputs_mini'),**(env or{}))
    for k in [k for k in e if k.startswith(('SLURM_','SBATCH_','SQUEUE_'))]:e.pop(k)
    p=subprocess.run([sys.executable,'-B',*map(str,args)],capture_output=True,text=True,env=e)
    if ok and p.returncode:raise RuntimeError(f'{args}: exit {p.returncode}\n{p.stderr[-4000:]}')
    if not ok and not p.returncode:raise AssertionError('Bad input accepted: '+' '.join(map(str,args)))
    return p

def sci(doc):return [{k:r[k]for k in SCIENTIFIC}for r in doc['native']['rows']]

def run(tmp:Path,backend:str)->dict:
    P=ROOT/'tools/production.py';t=tmp/f'{backend} #?%41 dir';scratch=tmp/f'scratch_{backend}';scratch.mkdir()
    call(P,'plan',t,'--seed',7611824,'--pilot','--points',16,'--replicates',2,'--test-graphs',1,'--shards',1,'--threads',2,'--checkpoint-tasks',8,
         '--bootstrap-chunk',8,'--backend',backend)
    m=load(t/'manifest.json');assert m['test_only']and m['backend']==backend and len(m['groups'])==24
    # one block of the first index: an incomplete campaign is refused by merge
    call(P,'run',t,'--index',0,'--threads',2,'--max-blocks',1,'--scratch',scratch)
    r=call(P,'merge',t,ok=False);assert 'Incomplete campaign'in r.stderr,r.stderr[-400:]
    for j in m['jobs']:call(P,'run',t,'--index',j['id'],'--threads',2,'--scratch',scratch)
    assert not any(scratch.iterdir()),'a job-private runtime directory was left behind'
    call(P,'status',t)
    # a deleted checkpoint is recomputed with another thread count; its scientific fields are unchanged
    j=max(m['jobs'],key=lambda j:j['blocks']);ck=sorted((t/'groups'/j['group']/'checkpoints').glob(f's{j["shard"]:06d}_p*.json'))[0]
    before=load(ck);ck.unlink();call(P,'run',t,'--index',j['id'],'--threads',1,'--scratch',scratch);after=load(ck)
    assert sci(before)==sci(after)and after['native']['threads']==1,'the recomputed block differs'
    # a corrupt checkpoint is rejected by run (which validates every existing block) and merge, then restored
    good=ck.read_bytes();doc=json.loads(good);doc['native']['rows'][0]['values'][0]=str(float(doc['native']['rows'][0]['values'][0])+1.0);ck.write_text(json.dumps(doc))
    r=call(P,'run',t,'--index',j['id'],'--threads',2,'--scratch',scratch,ok=False);r2=call(P,'merge',t,ok=False);ck.write_bytes(good)
    assert all('payload corruption'in x.stderr for x in (r,r2)),(r.stderr[-300:],r2.stderr[-300:])
    # merge, idempotent re-merge, idempotent assembly
    call(P,'merge',t,'--jobs',2);snap={str(p.relative_to(t)):digest(p)for p in sorted((t/'groups').rglob('merged.json'))}
    call(P,'merge',t,'--jobs',2);assert snap=={str(p.relative_to(t)):digest(p)for p in sorted((t/'groups').rglob('merged.json'))}
    call(ROOT/'tools/assemble.py',t,'--bootstrap',16);res=t/'C8_test_result.json';h=digest(res)
    r=call(ROOT/'tools/assemble.py',t,'--bootstrap',16);assert digest(res)==h
    x=load(res);assert x['test_only']is True and x.get('C8_full')is None and isinstance(x['test_partial']['C8_full'],float),sorted(x)
    # merged data of the wrong sector: a free group's merged.json in the power group of the same loop is rejected
    bad=tmp/f'{backend}_wrong_sector';shutil.copytree(t,bad)
    src=bad/'groups/a_free_L5/merged.json';dst=bad/'groups/a_power_L5/merged.json';dst.write_bytes(src.read_bytes())
    r=call(ROOT/'tools/assemble.py',bad,'--bootstrap',0,'--output',tmp/f'{backend}_wrong.json',ok=False)
    return dict(backend=backend,status='passed',jobs=len(m['jobs']),incomplete_merge_refused=True,runtime_removed=True,recomputed_block_identical=True,
                corrupt_checkpoint_rejected=True,idempotent_merge_and_assembly=True,test_only_result_keys=True,wrong_sector_rejected=True,
                wrong_sector_message=(r.stderr.strip().splitlines()or[''])[-1][:200])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path,help='write the JSON record here');a=ap.parse_args()
    backends=[b for b in ('decimal','gmp')if (ROOT/f'bin/c8d2_{b}').exists()]
    if not backends:raise SystemExit('build bin/c8d2_decimal and bin/c8d2_gmp (make && make gmp) first')
    res=[]
    with tempfile.TemporaryDirectory(prefix='c8d2_workflow_',dir=os.environ.get('TMPDIR'))as tmp:
        for b in backends:res.append(run(Path(tmp),b))
    rec={'status':'passed','tests':res,'environment':environment_record()}
    if a.output:dump(a.output,rec)
    print(json.dumps(rec,indent=2,default=str))
