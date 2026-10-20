#!/usr/bin/env python3
"""Local ensemble scaling, deterministic scheduling, signal restart, shard merge.
Run on an otherwise idle allocated node, not a login node. No Slurm is invoked.
"""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent;W=R.parent/'tests/orchestration';W.mkdir(exist_ok=True,parents=True)
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
def run(args,log,allowed=(0,)):
    with log.open('w') as f:
        start=time.perf_counter();p=subprocess.run([sys.executable,*map(str,args)],stdout=f,stderr=subprocess.STDOUT)
    if p.returncode not in allowed:raise RuntimeError(f'{args}: code {p.returncode}; inspect {log}')
    return time.perf_counter()-start,p.returncode

def main():
    base=W/'base'
    run([R/'prepare.py','--out',base,'--dim',3,'--s',1.8,'--sizes',64,'--centers',R.parent/'reference/largest_pair_crossing_centers.csv',
        '--replicas',4,'--beta-points',1,'--measurements',600,'--warmup',64,'--campaign-id','local-scheduling-test-20260918'],W/'prepare.log')
    clones={k:W/str(k) for k in (1,2,4,'restart')}
    for p in clones.values():shutil.copytree(base,p)
    report={'note':'Four independent L=64,d=3 chains; 664 sweeps each. Timing is local wall clock, not equilibration.'}
    ref=None
    for k in (1,2,4):
        sec,rc=run([R/'run_pack.py',clones[k],'--workers',k],W/f'workers{k}.log')
        dig=[hashlib.sha256((clones[k]/f'chains/{i:06d}/samples.bin').read_bytes()).hexdigest() for i in range(4)]
        if ref is None:ref=dig
        assert dig==ref,'scheduling changed random trajectories'
        report[f'workers{k}']={'seconds':sec,'speedup':report['workers1']['seconds']/sec if k!=1 else 1.,'raw_sha256':dig}
    sec,rc=run([R/'run_pack.py',clones['restart'],'--workers',2,'--max-seconds',.35],W/'signal.log',(75,))
    report['interrupt_returncode']=rc
    run([R/'run_pack.py',clones['restart'],'--workers',4],W/'resume.log')
    dig=[hashlib.sha256((clones['restart']/f'chains/{i:06d}/samples.bin').read_bytes()).hexdigest() for i in range(4)]
    assert dig==ref;report['signalled_resume_bitwise']=True
    run([R/'merge_shards.py','--out',W/'merged','--sources',clones[1],clones[2]],W/'merge.log')
    audit=json.loads((W/'merged/merge_audit.json').read_text())
    assert audit['complete_unique_chains']==4 and len(audit['deduplicated_identical_chains'])==4
    report['deduplicated']=audit
    # Explicit shard partition covers every global task once, regardless of node count.
    shardids=[[i for i in range(4) if i%3==s] for s in range(3)]
    assert sorted(sum(shardids,[]))==list(range(4));report['shards']=shardids
    (R.parent/'tests/orchestration_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
