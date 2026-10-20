#!/usr/bin/env python3
"""Pinned, independent serial chains on one allocated node. Scheduler agnostic.

Signals USR1/TERM/INT stop queue admission and checkpoint all running children.
Use disjoint global task shards across clusters. This is ensemble parallelism,
not a distributed union-find for one lattice.
"""
from __future__ import annotations
import argparse,json,os,signal,subprocess,time
from pathlib import Path
from run_task import command

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('campaign',type=Path)
    p.add_argument('--workers',type=int,default=1);p.add_argument('--shards',type=int,default=1);p.add_argument('--shard',type=int,default=0)
    p.add_argument('--plan',type=Path);p.add_argument('--slot',type=int,default=0);p.add_argument('--measurements',type=int)
    p.add_argument('--checkpoint-seconds',type=float,default=600);p.add_argument('--max-seconds',type=float,default=0)
    p.add_argument('--no-pin',action='store_true');a=p.parse_args();root=a.campaign.resolve()
    if a.measurements is not None and a.measurements<=0:p.error('measurement target must be positive')
    if a.checkpoint_seconds<=0 or a.max_seconds<0:p.error('invalid checkpoint/time limit')
    if a.workers<1 or not 0<=a.shard<a.shards:p.error('invalid worker count or shard')
    manifest=json.loads((root/'manifest.json').read_text());tasks=manifest['tasks']
    if a.plan:
        plan=json.loads(a.plan.read_text())
        if plan['campaign_id']!=manifest['campaign_id']:p.error('launch plan belongs to a different campaign')
        ids=plan['slots'][a.slot]
    else:ids=[t['id'] for t in tasks if t['id']%a.shards==a.shard]
    cpus=sorted(os.sched_getaffinity(0))
    if not a.no_pin and a.workers>len(cpus):p.error('more workers than CPUs in allocation affinity mask')
    # Big tasks first so smaller tasks can fill spare slots later.
    ids.sort(key=lambda i:tasks[i]['N']*(tasks[i]['measurements']+tasks[i]['warmup']),reverse=True)
    stop=False;hard_failure=False;running={};idle=list(range(a.workers));started=time.monotonic()
    def request(signum,frame):
        nonlocal stop
        stop=True
        for child,fh in running.values():
            try:child.send_signal(signal.SIGUSR1)
            except ProcessLookupError:pass
    for sig in (signal.SIGUSR1,signal.SIGTERM,signal.SIGINT):signal.signal(sig,request)
    os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    while ids or running:
        if a.max_seconds and time.monotonic()-started>a.max_seconds and not stop:request(None,None)
        while idle and ids and not stop:
            slot=idle.pop();tid=ids.pop(0);t=tasks[tid];dr=root/t['directory'];dr.mkdir(parents=True,exist_ok=True)
            cmd=command(root,tid,a.measurements,a.checkpoint_seconds,0)
            # command() verifies binary identity before a fast completed-chain skip.
            target=a.measurements if a.measurements is not None else t['measurements']
            marker=dr/'DONE.json'
            if marker.exists() and json.loads(marker.read_text())['measurements_done']>=target:
                idle.append(slot);continue
            fh=(dr/'runner.log').open('a',buffering=1)
            affinity=None if a.no_pin else (lambda cpu=cpus[slot]:os.sched_setaffinity(0,{cpu}))
            child=subprocess.Popen(cmd,stdout=fh,stderr=subprocess.STDOUT,preexec_fn=affinity)
            running[slot]=(child,fh);print(json.dumps(dict(task=tid,pid=child.pid,cpu=None if a.no_pin else cpus[slot])),flush=True)
        for slot,(child,fh) in list(running.items()):
            rc=child.poll()
            if rc is None:continue
            fh.close();del running[slot];idle.append(slot)
            if rc not in (0,75):hard_failure=True;request(None,None)
            elif rc==75:request(None,None)
        if stop and not running:break
        time.sleep(.1)
    raise SystemExit(1 if hard_failure else 75 if stop else 0)
if __name__=='__main__':main()
