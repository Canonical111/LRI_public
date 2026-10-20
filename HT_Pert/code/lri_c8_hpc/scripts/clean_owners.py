#!/usr/bin/env python3
"""Move stale owner files of an output directory aside (run by slurm/submit_defq.sh under
its submission mutex, after its own live-job check).

Owner files: OUTDIR/owners/**.owner (lane supervisors) and OUTDIR/accepted/**.owner
(solvers: outputs and checkpoints). An owner is stale only if it records a Slurm job id whose job is not in a
non-terminal state for this user. If any owner belongs to a live job, records no Slurm job
(a direct run outside Slurm), cannot be read, or squeue fails, NOTHING is moved and the
script exits 3. Exit 0: nothing to move, or every owner was moved to OUTDIR/owners_stale/<time>/.
"""
import json,os,subprocess,sys,time
from pathlib import Path
TERMINAL=('COMPLETED','CANCELLED','FAILED','TIMEOUT','NODE_FAIL','OUT_OF_MEMORY','BOOT_FAIL','DEADLINE','PREEMPTED','REVOKED')
out=Path(sys.argv[1]).resolve()
owners=sorted([*(out/'owners').rglob('*.owner'),*(out/'accepted').rglob('*.owner')])
if not owners:print('no owner files');raise SystemExit(0)
env={k:v for k,v in os.environ.items() if not k.startswith('SQUEUE_')}
q=subprocess.run(['squeue','-h','-u',os.environ['USER'],'--states=all','-o','%A %T'],capture_output=True,text=True,env=env)
if q.returncode!=0:print(f'squeue failed: {q.stderr.strip()}',file=sys.stderr);raise SystemExit(3)
live={f[0]:f[-1] for f in (l.split() for l in q.stdout.splitlines()) if len(f)>=2 and not f[-1].startswith(TERMINAL)}
problems=[]
for p in owners:
    try:o=json.loads(p.read_text())
    except (OSError,ValueError) as e:problems.append(f'{p}: unreadable ({e})');continue
    job=o.get('slurm_job_id')
    if not job:problems.append(f'{p}: no Slurm job recorded (host {o.get("host")}, pid {o.get("pid")})')
    elif job in live:problems.append(f'{p}: job {job} is {live[job]}')
if problems:
    print('owner files are not provably stale; nothing moved:\n  '+'\n  '.join(problems),file=sys.stderr);raise SystemExit(3)
dest=out/'owners_stale'/time.strftime('%Y%m%dT%H%M%S')
for p in owners:
    d=dest/p.relative_to(out);d.parent.mkdir(parents=True,exist_ok=True);os.rename(p,d)
print(f'moved {len(owners)} stale owner files to {dest}')
