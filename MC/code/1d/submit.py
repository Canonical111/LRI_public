#!/usr/bin/env python3
"""Submit one Slurm array; use --dry-run to inspect all commands first."""
from __future__ import annotations
import argparse, json, math, os, shlex, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('campaign',type=Path);p.add_argument('--concurrency',type=int,default=64)
    p.add_argument('--tasks-per-slot',type=int,default=4)
    p.add_argument('--time',default='08:00:00');p.add_argument('--mem',default='2G')
    p.add_argument('--account');p.add_argument('--partition');p.add_argument('--constraint')
    p.add_argument('--measurements',type=int,help='extend each chain to this total count')
    p.add_argument('--auto-requeue',action='store_true');p.add_argument('--dry-run',action='store_true')
    a=p.parse_args();root=a.campaign.resolve()
    if min(a.concurrency,a.tasks_per_slot)<1:p.error('concurrency and packing must be positive')
    n=len(json.loads((root/'manifest.json').read_text())['tasks']);slots=math.ceil(n/a.tasks_per_slot)
    if slots>1000:print('WARNING: verify site MaxArraySize or increase --tasks-per-slot')
    env=os.environ.copy();env.update(LRI_ROOT=str(ROOT),LRI_CAMPAIGN=str(root),LRI_TASK_COUNT=str(n),
        LRI_TASKS_PER_SLOT=str(a.tasks_per_slot),LRI_AUTOREQUEUE=str(int(a.auto_requeue)))
    if a.measurements:env['LRI_MEASUREMENTS']=str(a.measurements)
    else:env.pop('LRI_MEASUREMENTS',None)
    cmd=['sbatch','--export=ALL',f'--array=0-{slots-1}%{a.concurrency}',f'--time={a.time}',f'--mem={a.mem}',
         f'--output={root}/logs/%A_%a.out',f'--error={root}/logs/%A_%a.err']
    for key in ('account','partition','constraint'):
        if getattr(a,key):cmd.append(f'--{key}={getattr(a,key)}')
    cmd.append(str(ROOT/'array.slurm'))
    print(f'{n} chains; {slots} array slots; up to {min(a.concurrency,slots)} simultaneous single-core chains')
    print(shlex.join(cmd))
    if not a.dry_run:subprocess.run(cmd,env=env,check=True)
if __name__=='__main__':main()
