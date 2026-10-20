#!/usr/bin/env python3
"""Compute-node validation of a staged release (run by cluster/job.sbatch with LRI_COEFF_JOB=validate).

1. software stack equals the tested pins;
2. the solver source equals the one that produced the archived L=22 pilot (results/scale_pilot);
3. tests/run_all.py (native/JIT warmup, then the whole pytest suite) passes with exactly EXPECTED_TESTS tests
   passed and nothing failed, skipped or deselected (inherited PYTEST_* settings are removed first);
4. a fresh L=22 replay (consistent d8, consistent d7, raw d8; no graph cache) agrees with the archived
   pilot results to RTOL in C, r, g, energies and vacuum_coefficients.
Writes RECEIPT_BASE/<release sha256[:16]>_<site>_<jobid>/receipt.json (passed true/false). Exit 0 only if
every check passed. submit.py campaign requires such a passing receipt for the same release tar and site.
"""
from pathlib import Path
import argparse,json,os,platform,re,shutil,socket,subprocess,sys,tempfile,time,datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
from stack import stack,pin_problems
from lri_coeff.storage import source_digest,read_envelope

ARCHIVED=ROOT/'results/scale_pilot'
REPLAY=[('consistent',8),('consistent',7),('raw',8)]
KEYS=('C','r','g','energies','vacuum_coefficients')
RTOL=1e-10
EXPECTED_TESTS=61   # the full inventory of tests/ in this release (update when tests change)

def now():return datetime.datetime.now().astimezone().isoformat(timespec='seconds')
def relerr(a,b):
    import numpy as np
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    if a.shape!=b.shape:return float('inf')
    return float(np.max(np.abs(a-b)/np.maximum(1,np.abs(b)))) if a.size else 0.0
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
    with os.fdopen(fd,'w') as f:f.write(json.dumps(obj,indent=1,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--receipt-base',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
    site=os.environ['LRI_COEFF_SITE'];sha=os.environ['LRI_COEFF_RELEASE_SHA256'];job=os.environ.get('SLURM_JOB_ID','nojob')
    threads=int(os.environ['LRI_COEFF_THREADS']);out=a.receipt_base/f'{sha[:16]}_{site}_{job}';a.work.mkdir(parents=True,exist_ok=True)
    cpu=next((l.split(':',1)[1].strip() for l in open('/proc/cpuinfo') if l.startswith('model name')),platform.processor())
    st=stack();checks={}
    receipt=dict(kind='lri-coeff-validation-receipt-v1',passed=False,site=site,release=os.environ['LRI_COEFF_RELEASE'],release_sha256=sha,
                 source_digest=source_digest(),stack=st,host=socket.gethostname(),cpu=cpu,threads=threads,started=now(),
                 slurm={k:os.environ.get(k) for k in ('SLURM_JOB_ID','SLURM_JOB_PARTITION','SLURM_JOB_NODELIST','SLURM_CPUS_ON_NODE','SLURM_MEM_PER_NODE')},checks=checks)
    bad=pin_problems(st);checks['stack_pins']=dict(ok=not bad,problems=bad)
    ref=read_envelope(ARCHIVED/'consistent_L22_d8.json')
    checks['source_matches_pilot']=dict(ok=receipt['source_digest']==ref['source_digest'],pilot=ref['source_digest'])
    print('VALIDATE stack',json.dumps(st),flush=True)

    # Tests in the staged copy; run_all.py fixes 4 threads and keeps the job's node-local caches.
    env={k:v for k,v in os.environ.items() if not k.startswith('PYTEST_') and k not in ('LRI_COEFF_MANIFEST_SHA256','LRI_COEFF_THREADS','LRI_COEFF_LOCAL_CHECKPOINT')}
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
    t=time.monotonic();r=subprocess.run([sys.executable,str(ROOT/'tests/run_all.py')],env=env,cwd=ROOT,capture_output=True,text=True)
    tail=(r.stdout+r.stderr)[-6000:];print(tail,flush=True)
    summary=next((l for l in reversed(r.stdout.splitlines()) if re.search(r'\d+ (passed|failed|error)',l)),'')
    counts={k:int(n) for n,k in re.findall(r'(\d+) (passed|failed|errors?|skipped|deselected|xfailed|xpassed)',summary)}
    checks['tests']=dict(ok=r.returncode==0 and counts=={'passed':EXPECTED_TESTS},expected=EXPECTED_TESTS,
                         returncode=r.returncode,counts=counts,summary=summary,seconds=round(time.monotonic()-t,1))
    if (ROOT/'results/validation.json').exists():shutil.copy(ROOT/'results/validation.json',a.work/'tests.json')

    # Replay of the archived pilot with this node's compiler and thread count.
    replay=[]
    for scheme,degree in REPLAY:
        name=f'{scheme}_L22_d{degree}.json';dest=a.work/'replay'/name
        cmd=[sys.executable,'-m','lri_coeff','run','--cutoff','22','--degree',str(degree),'--scheme',scheme,'--threads',str(threads),
             '--max-states','6500000','--memory-gib','8','--output',str(dest)]
        e=dict(env,PYTHONPATH=str(ROOT/'src'));t=time.monotonic()
        r=subprocess.run(cmd,env=e,cwd=a.work,capture_output=True,text=True);row=dict(name=name,returncode=r.returncode,seconds=round(time.monotonic()-t,1))
        if r.returncode==0:
            new=read_envelope(dest);old=read_envelope(ARCHIVED/name)
            errs={k:relerr(new['result'][k],old['result'][k]) for k in KEYS}
            row.update(errors=errs,ok=max(errs.values())<=RTOL and new['configuration']==old['configuration'],C=new['result']['C'],
                       solver_seconds=new['execution']['seconds'],peak_rss_GiB=round(new['execution']['peak_rss_KiB']/2**20,3),threads=new['execution']['threads'])
        else:row.update(ok=False,stderr=r.stderr[-3000:])
        print('VALIDATE replay',json.dumps(row),flush=True);replay.append(row)
    checks['replay']=dict(ok=all(x['ok'] for x in replay),rtol=RTOL,runs=replay)

    receipt.update(passed=all(c['ok'] for c in checks.values()),finished=now())
    write(out/'receipt.json',receipt)
    if (a.work/'tests.json').exists():shutil.copy(a.work/'tests.json',out/'tests.json')
    print('VALIDATE',('PASSED' if receipt['passed'] else 'FAILED'),{k:c['ok'] for k,c in checks.items()},'receipt',out/'receipt.json',flush=True)
    return 0 if receipt['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
