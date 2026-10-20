#!/usr/bin/env python3
"""Amendment A3 (docs/EXTENSION_A3.md), Expanse login node: run the planned batches b12-b14 and keep a job journal.

  run                    for each of b12 b13 b14, submit whatever is missing: the 498-task array (production8_a3.slurm,
                         only for a batch whose array is not journaled yet: then no c8a3 job of the batch may exist, and
                         the batch must be untouched and equal to the export record) and the merge job (merge8_a3.slurm,
                         --dependency=afterok on the array; only if no merge is journaled and none exists). Resumable.
  resubmit LABEL I...    rerun elements whose every journaled attempt ended FAILED, TIMEOUT, NODE_FAIL or OUT_OF_MEMORY,
                         fewer than 3 attempts each (complete accounting required; no task of the batch may be pending
                         or running); committed checkpoints are validated and skipped, so only missing work is computed
  merge LABEL            submit the merge of one batch by hand (its array must be journaled, no array task or merge of the
                         batch unfinished, every planned checkpoint present; not after a stop)
  status                 checkpoint completeness, merge state and journaled jobs of each batch
  stop                   the durable stop barrier runs/ext1/A3_STOP (no-clobber): from then on run, resubmit and merge refuse and
                         every element task that starts exits without work (then scancel the unfinished jobs by hand)
Journal: runs/ext1/a3_jobs.jsonl, one JSON object per submitted job, written (fsync) right after sbatch answers.
Admission: run, resubmit, merge and stop hold the submit lock runs/ext1/A3_SUBMIT.lock (created exclusively; removed on
exit; a lock left by a killed command is removed by hand after inspection), so checks, submission and journaling of one
command never interleave with another's, and no submission is accepted after stop returns.
Scheduler queries remove every SQUEUE_* variable and list all states; a failed query stops the command (UNKNOWN is
never read as "no job"). sbatch runs with SBATCH_* and inherited C8_* variables removed and the C8 pins given explicitly.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

E=Path('/expanse/lustre/scratch/zzheng8/temp_project/c8_hpc');C=E/'code'/'c0ffa63';X=C/'bin'/'c8_integrate';R=E/'runs'/'ext1'
HERE=Path(__file__).resolve().parent;TOP=HERE.parent.parent;LOGS=E/'logs';JOURNAL=R/'a3_jobs.jsonl'
LABELS=('b12','b13','b14');NTASK=498;STOP=R/'A3_STOP';SLOCK=R/'A3_SUBMIT.lock'
XSHA='ffb200d40026a25f6337bdf778f8652a73a02b4730c8f2e8c91232b6ebc7db8b'
TERMINAL={'COMPLETED','CANCELLED','FAILED','TIMEOUT','NODE_FAIL','BOOT_FAIL','DEADLINE','OUT_OF_MEMORY','REVOKED'} # as lane8: every other state (held, requeued, preempted) may still run
RETRY={'FAILED','TIMEOUT','NODE_FAIL','OUT_OF_MEMORY'};MAX_ATTEMPTS=3
sys.path.insert(0,str(TOP/'tools'));sys.path.insert(0,str(HERE))
import a3_tree # noqa: E402

def now()->str:return time.strftime('%Y-%m-%dT%H:%M:%S%z')
def die(msg:str,code:int=64):print('A3:',msg,file=sys.stderr);sys.exit(code)
def sha(p:Path)->str:return a3_tree.sha(p)

def squeue_jobs()->list:
    env={k:v for k,v in os.environ.items() if not k.startswith('SQUEUE_')}
    try:r=subprocess.run(['squeue','-h','-u',os.environ['USER'],'-t','all','-o','%i|%j|%T'],capture_output=True,text=True,timeout=120,env=env)
    except (OSError,subprocess.TimeoutExpired,KeyError) as e:die(f'squeue failed: {e}',65)
    if r.returncode:die('squeue failed: '+r.stderr.strip(),65)
    out=[]
    for line in r.stdout.splitlines():
        if not line.strip():continue
        t=line.split('|')
        if len(t)!=3 or not re.fullmatch(r'\d+(_\S+)?',t[0]) or not t[1] or not t[2]:die(f'malformed squeue line {line!r}',65)
        out.append((t[0],t[1],t[2]))
    return out

def unfinished(names:set)->list:return [f'{j} {n} {st}' for j,n,st in squeue_jobs() if n in names and st not in TERMINAL]

def journal()->list:
    if not JOURNAL.exists():return []
    return [json.loads(l) for l in JOURNAL.read_text().splitlines() if l.strip()]

def record(e:dict)->None:
    try:
        with open(JOURNAL,'a') as f:f.write(json.dumps(e)+'\n');f.flush();os.fsync(f.fileno())
    except OSError as x:die(f'JOB {e["job"]} WAS SUBMITTED but the journal write failed ({x}): add {json.dumps(e)} to {JOURNAL} by hand',66)

def sbatch(args:list,pins:dict)->str:
    env={k:v for k,v in os.environ.items() if not k.startswith('SBATCH_') and not (k.startswith('C8_') and k!='C8_PYTHON')}
    exp='ALL,'+','.join(f'{k}={v}' for k,v in pins.items())
    try:r=subprocess.run(['sbatch','--parsable','--export='+exp,*args],capture_output=True,text=True,timeout=300,env=env)
    except (OSError,subprocess.TimeoutExpired) as e:die(f'sbatch failed: {e} (check squeue for a job that may have been accepted)',66)
    j=r.stdout.strip()
    if r.returncode or not re.fullmatch(r'\d+',j):die(f'sbatch failed (rc {r.returncode}, out {j!r}, err {r.stderr.strip()!r})',66)
    return j

PINS={'C8_ENV_SETUP':str(E/'env.sh'),'C8_ROOT':str(C)}
class admission:
    """The submit lock (exclusive create; held for the whole command). Its directory is created first, so stop also
    works before the first export."""
    def __enter__(self):
        R.mkdir(parents=True,exist_ok=True)
        try:fd=os.open(SLOCK,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
        except FileExistsError:die(f'{SLOCK} exists ({SLOCK.read_text().strip()}): another A3 command runs, or one was killed (inspect, then remove it)')
        os.write(fd,f'{os.getpid()} {os.uname().nodename} {now()}\n'.encode());os.fsync(fd);os.close(fd);return self
    def __exit__(self,*x):os.unlink(SLOCK)

def not_stopped()->None:
    if STOP.exists():die(f'stop barrier {STOP} exists: no submission')

def submit_array(lab:str,indices:str,kind:str)->str:
    not_stopped()
    j=sbatch([f'--array={indices}',f'--job-name=c8a3-{lab}','-o',str(LOGS/'%x-%A_%a.out'),str(HERE/'production8_a3.slurm')],
             {**PINS,'C8_EXECUTABLE':str(X),'C8_PRODUCTION':str(R/lab),'C8_A3_STOP':str(STOP)})
    record({'label':lab,'kind':kind,'job':j,'indices':indices,'time':now()});print(f'{lab}: {kind} {j} indices {indices}');return j

def submit_merge(lab:str,dep:str|None,kind:str)->str:
    not_stopped() # a merge after a stop belongs to the separately reviewed stopped-close procedure
    j=sbatch(([f'--dependency=afterok:{dep}'] if dep else [])+[f'--job-name=c8a3-merge-{lab}','-o',str(LOGS/'%x-%j.out'),str(HERE/'merge8_a3.slurm')],
             {**PINS,'C8_A3':str(HERE),'C8_PRODUCTION':str(R/lab)})
    record({'label':lab,'kind':kind,'job':j,'after':dep,'time':now()});print(f'{lab}: {kind} {j}'+(f' (afterok {dep})' if dep else ''));return j

def preflight()->None:
    if os.environ.get('SLURM_JOB_ID'):die('run from the login node')
    if sha(X)!=XSHA:die('executable sha256 differs from the planned one')
    for f in ('tools/production8.py','tools/campaign.py'):
        if (C/f).read_bytes()!=(TOP/f).read_bytes():die(f'{C/f} differs from the A3 commit')

def run(a)->None:
    with admission():_run()

def _run()->None:
    preflight();not_stopped()
    ex=R/'A3_export.json'
    if not ex.is_file():die('no export record '+str(ex))
    rec=json.loads(ex.read_text())
    for lab in LABELS:
        J=[e for e in journal() if e['label']==lab];arr=[e for e in J if e['kind']=='array']
        if arr:print(f'{lab}: array {arr[0]["job"]} already journaled');a_job=arr[0]['job']
        else:
            busy=unfinished({f'c8a3-{lab}',f'c8a3-merge-{lab}'})
            if busy:die(f'{lab}: jobs exist that the journal does not list: {busy}')
            a3_tree.planned_only(R/lab,lab)
            if hashlib.sha256(a3_tree.text(a3_tree.tree(R/lab)).encode()).hexdigest()!=rec['manifest_sha256'][lab]:die(f'{lab}: differs from the export record')
            a_job=submit_array(lab,f'0-{NTASK-1}','array')
        if any(e['kind'] in ('merge','merge-manual') for e in J):print(f'{lab}: merge already journaled');continue
        busy=unfinished({f'c8a3-merge-{lab}'})
        if busy:die(f'{lab}: merge jobs exist that the journal does not list: {busy}')
        submit_merge(lab,a_job,'merge')

def attempts(lab:str,i:int)->list:
    """States of every journaled attempt of element i (array and resubmissions); complete accounting required."""
    out=[]
    for e in journal():
        if e['label']!=lab or e['kind'] not in ('array','resubmit'):continue
        if e['kind']=='array':covered=0<=i<NTASK
        else:covered=i in {int(x) for x in e['indices'].split(',')}
        if not covered:continue
        r=subprocess.run(['sacct','-X','-n','-P','-j',e['job'],'-o','JobID,State','-S','2026-10-12','-E','now'],capture_output=True,text=True,timeout=120)
        if r.returncode:die('sacct failed: '+r.stderr.strip(),65)
        st=[l.split('|')[1].split()[0] for l in r.stdout.splitlines() if l.split('|')[0]==f'{e["job"]}_{i}']
        if len(st)!=1:die(f'{lab} #{i}: job {e["job"]} has {len(st)} accounting lines for this element (need exactly 1)')
        out.append(st[0])
    return out

def missing(lab:str,i:int)->list:
    """Planned checkpoint identities of element i that are absent."""
    import campaign # noqa: E402 (the A3 commit's tools, byte-identical to the frozen ones for campaign.py)
    b=R/lab;j=json.loads((b/'production.json').read_text())['jobs'][i];d=b/j['campaign'];m=json.loads((d/'manifest.json').read_text())
    return [campaign.identity(sh['id'],part,N) for sh,part,_,_ in campaign.blocks(d,m,j['index']) for N in m['degrees']
            if not (d/'checkpoints'/(campaign.identity(sh['id'],part,N)+'.json')).is_file()]

def resubmit(a)->None:
    with admission():_resubmit(a)

def _resubmit(a)->None:
    preflight();not_stopped();lab=a.label
    if lab not in LABELS:die('label must be b12, b13 or b14')
    if not any(e['label']==lab and e['kind']=='array' for e in journal()):die(f'{lab}: no journaled array')
    busy=unfinished({f'c8a3-{lab}'})
    if busy:die(f'{lab}: array tasks pending or running: {busy}')
    idx=sorted(set(a.indices))
    for i in idx:
        if not 0<=i<NTASK:die(f'bad index {i}')
        st=attempts(lab,i)
        if not st or any(s not in RETRY for s in st):die(f'{lab} #{i}: attempt states {st}: only {sorted(RETRY)} are rerun automatically')
        if not missing(lab,i):die(f'{lab} #{i}: no planned checkpoint is missing: nothing to rerun')
        if len(st)>=MAX_ATTEMPTS:die(f'{lab} #{i}: {len(st)} failed attempts: diagnose by hand')
    j=submit_array(lab,','.join(map(str,idx)),'resubmit')
    with open(R/'A3_RESUBMISSIONS.txt','a') as f:f.write(f'{now()} {lab} indices {idx} resubmitted as {j} (previous attempts all failed)\n')

def merge(a)->None:
    with admission():_merge(a)

def _merge(a)->None:
    preflight();lab=a.label
    if lab not in LABELS:die('label must be b12, b13 or b14')
    if not any(e['label']==lab and e['kind']=='array' for e in journal()):die(f'{lab}: no journaled array: run first')
    busy=unfinished({f'c8a3-{lab}',f'c8a3-merge-{lab}'})
    if busy:die(f'{lab}: unfinished jobs: {busy}')
    st=batch_state(lab)
    if not st['complete']:die(f'{lab}: {st["checkpoints_present"]}/{st["checkpoints_planned"]} checkpoints: nothing is merged before the batch is complete')
    submit_merge(lab,None,'merge-manual')

def batch_state(lab:str)->dict:
    import lane8 # noqa: E402 (the A3 commit's tools: checkpoints_complete reads the manifests and task plans)
    b=R/lab;complete,have,need=lane8.checkpoints_complete(b);prod=json.loads((b/'production.json').read_text())
    m=R/f'{lab}.expanse_manifest.txt'
    return {'complete':complete,'checkpoints_present':have,'checkpoints_planned':need,'completed_fraction':round(have/need,6),
            'merged':all((b/c/'merged'/'audit.json').is_file() for c in prod['campaigns']),
            'manifest_sha256':sha(m) if m.is_file() else None}

def status(a)->None:
    for lab in LABELS:print(lab,json.dumps(batch_state(lab)),[f"{e['kind']} {e['job']}" for e in journal() if e['label']==lab])

def stop(a)->None:
    with admission():
        try:
            with open(STOP,'x') as f:f.write(json.dumps({'time':now(),'by':os.environ.get('USER')})+'\n')
        except FileExistsError:die(f'{STOP} exists')
    print('stop barrier published',STOP,'; now scancel the unfinished c8a3 jobs:',unfinished({f'c8a3-{l}' for l in LABELS}|{f'c8a3-merge-{l}' for l in LABELS}))

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='action',required=True)
    s.add_parser('run');t=s.add_parser('resubmit');t.add_argument('label');t.add_argument('indices',type=int,nargs='+')
    t=s.add_parser('merge');t.add_argument('label');s.add_parser('status');s.add_parser('stop')
    a=p.parse_args();{'run':run,'resubmit':resubmit,'merge':merge,'status':status,'stop':stop}[a.action](a)

if __name__=='__main__':main()
