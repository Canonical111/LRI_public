#!/usr/bin/env python3
"""Test driver: the admission engine of tools/slurm_submit.py (Call) with the job sets of `lanes N` and `submit`.

Stage 0 delivers the engine, `raw` and the spec builders (slurm_submit.lane_specs, array_specs); Stage 3 wires the
campaign entry points to them. Until then the A-ORC-11/17 cases that the plan states for `lanes N` and `submit` run
through this driver, which builds exactly those job sets from scheduler data (the live lane workers and pending merges
of the campaign come from the admission's own snapshot, inside the session lock).

  driver.py lanes N --dir D [--lane-time T] [--dry-run]
  driver.py submit --dir D --window OFF:RANGE [--window ...]
Scripts: FAKE_SCRIPTS (a directory holding worker.sh, merge.sh and work.sh).
"""
from __future__ import annotations
import argparse,os,shlex,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools')]
import slurm_submit as ss,ledger
from common import Refuse

def base_role(q)->str:return ss.budget.base_role(q.info['role'])

def lanes_call(env:dict,cdir:Path,n:int,lane_time:str,scripts:Path):
    site=shlex.split(env.get('C8_SBATCH_ARGS','-A yun124 -p compute'));merge=shlex.split(env.get('C8_MERGE_SBATCH_ARGS','-A yun124 -p shared -c 24 --mem=48G -t 01:00:00'))
    mem=env.get('C8_LANE_MEM','240G');line=ss.budget_line(env);c=ledger.dir_sha12(cdir)
    w,m=str(scripts/'worker.sh'),str(scripts/'merge.sh')
    xs=ss.amd_exclusions(ss.budget.profile(env),env)   # as slurm_submit.py lanes N: before the session lock (64, nothing written)
    last={}
    def plan(snap):
        mine=[q for q in snap.live_lines()if q.ours and q.info['c']==c]
        arrays=sorted({q.jobid for q in mine if base_role(q).startswith('off')})
        if arrays:raise Refuse(65,f'array element(s) {",".join(arrays)} of this campaign are live: lane mode and array mode are not mixed')
        live=sorted({q.jobid for q in mine if base_role(q)=='lane'})
        sup=sorted({q.jobid for q in mine if base_role(q)=='merge'and q.state=='PENDING'})
        last['specs']=ss.lane_specs(cdir,n,lane_time,site,mem,merge,env,line,live,w,m,live_partitions=sorted({q.partition for q in mine if base_role(q)=='lane'}),exclude=xs)
        return last['specs'],sup
    # The job sets of k < N workers come from the planned specs (no script is read again during the rules, A-ORC-11's spy).
    family=lambda k:[sp for sp in last['specs']if sp.kind=='lane'][:k]+[sp for sp in last['specs']if sp.kind=='merge']
    return plan,family

def submit_call(env:dict,cdir:Path,windows:list,scripts:Path):
    site=shlex.split(env.get('C8_SBATCH_ARGS','-A yun124 -p shared -c 32 --mem=64G -t 01:00:00'))   # the scripts add --nodes=1 (D.10)
    merge=shlex.split(env.get('C8_MERGE_SBATCH_ARGS','-A yun124 -p shared -c 24 --mem=48G -t 01:00:00'));line=ss.budget_line(env)
    last={};xs=ss.amd_exclusions(ss.budget.profile(env),env)
    def plan(snap):
        last['specs']=ss.array_specs(cdir,windows,site,merge,env,line,str(scripts/'work.sh'),str(scripts/'merge.sh'),exclude=xs);return last['specs'],[]
    family=lambda k:([sp for sp in last['specs']if sp.kind=='array'][:k]+[sp for sp in last['specs']if sp.kind=='merge'])if k else[]
    return plan,family

def main(argv=None,env=None)->int:
    env=dict(os.environ)if env is None else env
    p=argparse.ArgumentParser();sp=p.add_subparsers(dest='cmd',required=True)
    q=sp.add_parser('lanes');q.add_argument('n',type=int);q.add_argument('--dir',required=True);q.add_argument('--lane-time',default='01:00:00');q.add_argument('--dry-run',action='store_true')
    q=sp.add_parser('submit');q.add_argument('--dir',required=True);q.add_argument('--window',action='append',required=True)
    a=p.parse_args(argv);scripts=Path(env['FAKE_SCRIPTS'])
    try:
        call=ss.Call(env,f'{a.cmd} (driver)');cdir=Path(os.path.realpath(a.dir))
        if a.cmd=='lanes':
            plan,fam=lanes_call(env,cdir,a.n,a.lane_time,scripts);return call.run(plan,family=fam,nmax=a.n,dry_run=a.dry_run)
        ws=[(int(w.split(':')[0]),w.split(':',1)[1])for w in a.window]
        plan,fam=submit_call(env,cdir,ws,scripts);return call.run(plan,family=fam,nmax=len(ws))
    except Refuse as r:print('C8: '+str(r),file=sys.stderr);return r.code

if __name__=='__main__':sys.exit(main())
