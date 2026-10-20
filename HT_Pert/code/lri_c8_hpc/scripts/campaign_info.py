#!/usr/bin/env python3
"""Campaign bookkeeping for the submit wrapper (login node, light).

  campaign_info.py todo   MANIFEST OUTDIR [--retry-failed]  -> "<array list or -> <campaign16>"
  campaign_info.py status MANIFEST OUTDIR

An item is done only if its accepted output reads back, passes the numerical gates and
matches the frozen item (source, cutoff, scheme, references, backend, threads, stack,
threading layer). A lane with an item that is not done is "todo", except that it is HELD
(reported, not resubmitted) when
  - an existing output is unreadable or does not match the frozen item (move it aside), or
  - its last attempt failed for real (exit not 0/73/75), or ended without an exit record
    and Slurm does not report an interruption (TIMEOUT, CANCELLED, NODE_FAIL, PREEMPTED,
    ...), or the lane's latest submitted array task (OUTDIR/submissions.txt) wrote no
    attempt at all and Slurm does not report an interruption (e.g. it failed in the
    environment setup); --retry-failed overrides this second rule.
`todo` is meant to run only when no job of this output directory is queued or running
(submit_defq.sh checks that first), so an attempt without an exit record is a dead one.
`todo` also refuses (exit 1) a campaign frozen for another source, stack or Numba layer,
so such a campaign never reaches sbatch.
"""
import argparse,json,os,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_c8 import io
from lri_c8.engine import validate_result
INTERRUPTED=('TIMEOUT','CANCELLED','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE')
LIVE=('PENDING','RUNNING','REQUEUED','SUSPENDED','CONFIGURING','COMPLETING','RESIZING','STAGE_OUT','SIGNALING')
ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['todo','status']);ap.add_argument('manifest',type=Path)
ap.add_argument('outdir',type=Path);ap.add_argument('--retry-failed',action='store_true');a=ap.parse_args()
m=io.read(a.manifest);cid=json.loads(a.manifest.read_text())['sha256'][:16]
if a.mode=='todo':
    import numpy,numba,scipy
    stack={'python':platform.python_version(),'numpy':numpy.__version__,'numba':numba.__version__,'scipy':scipy.__version__}
    layer=os.environ.get('NUMBA_THREADING_LAYER','default')
    if m['source_sha256']!=io.source_digest():raise SystemExit(f'campaign {cid} was frozen for another source; rebuild it')
    if m.get('stack')!=stack or m.get('threading_layer')!=layer:
        raise SystemExit(f'campaign {cid} stack {m.get("stack")}/{m.get("threading_layer")} differs from {stack}/{layer}')

def stem(item):return f"{item['scheme']}_L{item['cutoff']}_d8"+('' if item['reference'] is None else f"_ref{item['reference']}")
def check(item):
    """'done', 'missing' or an explanation why the existing output is unusable."""
    path=a.outdir/'accepted'/(stem(item)+'.json')
    if not path.exists():return 'missing'
    try:r=io.read(path)
    except (OSError,ValueError) as e:return f'unreadable output {path}: {e}'
    c=r.get('config',{});rt=c.get('runtime',{})
    want={'source_sha256':m['source_sha256'],'cutoff':item['cutoff'],'scheme':item['scheme'],'outer_backend':item['outer_backend'],
          'threads':item['threads'],'references':[0,1,3,2] if item['reference'] is None else [item['reference']],
          'stack':m['stack']}
    have={'source_sha256':c.get('source_sha256'),'cutoff':c.get('cutoff'),'scheme':c.get('scheme'),'outer_backend':c.get('outer_backend'),
          'threads':rt.get('threads'),'references':r.get('references'),'stack':{k:rt.get(k) for k in m['stack']}}
    bad=[k for k in want if want[k]!=have[k]]
    if m.get('threading_layer') not in (None,'default') and rt.get('threading_layer')!=m['threading_layer']:bad.append('threading_layer')
    if bad:return f'output {path} does not match the frozen item in {bad}'
    try:
        if item['reference'] is None:validate_result(r)
        elif str(item['reference']) not in r.get('components',{}):return f'output {path} lacks its reference component'
    except Exception as e:return f'output {path} fails the numerical gates: {e!r}'
    return 'done'
def slurm_state(job):
    """State of exactly this job or array task ('<array>_<task>'); None if unknown. A bare
    id can match a whole array (one task's id equals the array id), so only the accounting
    row whose JobID equals the query counts."""
    try:p=subprocess.run(['sacct','-j',str(job),'-n','-X','-P','-o','JobID,State'],capture_output=True,text=True,timeout=120)
    except (OSError,subprocess.TimeoutExpired):return None
    if p.returncode!=0:return None
    rows=[l.split('|') for l in p.stdout.splitlines() if l.strip()]
    states=[r[1].split()[0] for r in rows if len(r)>=2 and r[0]==str(job) and r[1].strip()]
    return states[0] if len(states)==1 else None
def task_id(attempt):
    # Array tasks are classified by '<array>_<task>', never by their bare job id.
    arr,task=attempt.get('slurm_array_job_id'),attempt.get('slurm_array_task_id')
    return f'{arr}_{task}' if arr and task is not None else attempt.get('slurm_job_id')
def latest_submissions():
    # submit_defq.sh appends "<jobid> <name ending -campaign16> <time> lanes=<list>".
    latest={};path=a.outdir/'submissions.txt'
    if path.exists():
        for line in path.read_text().splitlines():
            f=line.split();spec=[x for x in f if x.startswith('lanes=')]
            if len(f)>=2 and f[1].endswith('-'+cid) and spec:
                for k in spec[0][6:].split(','):latest[int(k)]=f[0]
    return latest
def last_attempt(k):
    path=a.outdir/'journals'/cid/f'lane_{k}.json'
    if not path.exists():return None
    return io.read(path)['attempts'][-1]  # a corrupt journal is an error, not "never ran"

todo=[];rows=[];submitted=latest_submissions()
for k,items in enumerate(m['lanes']):
    states={stem(i):check(i) for i in items}
    left=[s for s,v in states.items() if v!='done'];unusable=[v for v in states.values() if v not in ('done','missing')]
    last=last_attempt(k);exit_code=None if last is None else last.get('exit')
    hold=None;retryable=False  # retryable: --retry-failed would release the hold
    sub=submitted.get(k)
    if unusable:hold='; '.join(unusable)+' (move it aside to recompute)'
    elif left and sub and (last is None or str(last.get('slurm_array_job_id'))!=sub):
        # The latest submission of this lane left no attempt: it never started, or failed
        # before run_lane could record anything (environment, binding, source check).
        task=f'{sub}_{k}';state=slurm_state(task)
        if state in LIVE:hold=f'array task {task} is still {state}'
        elif state not in INTERRUPTED and not a.retry_failed:
            hold=f'array task {task} ended {state or "UNKNOWN"} without a journal attempt (see its Slurm log)';retryable=True
    elif left and last is not None and exit_code is None:
        job=task_id(last);state=slurm_state(job) if job else None
        if state in LIVE:hold=f'job {job} is still {state}'
        elif state not in INTERRUPTED and not a.retry_failed:
            hold=f'last attempt (job {job}) ended without an exit record; Slurm state {state or "UNKNOWN"}';retryable=True
    elif left and exit_code not in (None,0,73,75) and not a.retry_failed:
        hold=f'last attempt failed (exit {exit_code}: {last.get("reason")})';retryable=True
    rows.append({'lane':k,'items':len(items),'left':left,'last_exit':exit_code,'held':hold,
                 'last_reason':None if last is None else last.get('reason'),'last_job':None if last is None else last.get('slurm_job_id')})
    if left and hold:print(f'lane {k} held: {hold}'+(' (C8_RETRY_FAILED=1 / --retry-failed to resubmit)' if retryable else ''),file=sys.stderr)
    elif left:todo.append(k)
if a.mode=='todo':print((','.join(map(str,todo)) or '-')+' '+cid)
else:
    print(f'campaign {cid}: {len(m["lanes"])} lanes, {sum(len(r["left"])==0 for r in rows)} complete, '
          f'{sum(bool(r["left"] and r["held"]) for r in rows)} held')
    for r in rows:print(json.dumps(r))
