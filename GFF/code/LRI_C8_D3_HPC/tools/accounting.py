#!/usr/bin/env python3
"""Allocated SU of a campaign (PLAN D.12, A-ORC-9): the sum of the billing value (HD17's billing function) x
ElapsedRaw/3600 over every `sacct -X --duplicates` attempt (requeues included) of every c8d3- job whose name carries the
campaign's C, or that a `register` record of the ledger links to it (a plan or sweep job of another --dir).

  accounting.py RUN [--json]

eta_node = allocated core-seconds of the work roles (lane workers, array windows) / busy core-seconds (the sum of the
checkpoint row seconds); plan, sweep and merge jobs are reported as overhead. Each attempt carries sacct's Submit and
Start (the pilot report's queue latency, E.7) and its allocated CPUs (alloc_cpus: sacct's AllocTRES cpu, None when sacct
has no TRES; tools/thru_report.py's busy = row seconds / (alloc_cpus x elapsed)). A checkpoint whose fingerprint names a job
id that sacct does not show as one of these jobs refuses ("allocation unknown", 69). Reads the ledger without the lock
(provenance only) and the scheduler through tools/budget.py's queries (both sacct queries, a failure refuses 69). It
never opens a campaign's scheduling copies (prior_cost_model.json, synthetic_cost_model.json; D.5, S3-R2-006).
"""
from __future__ import annotations
import argparse,json,os,sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,load
import budget,ledger
import production as prod

WORK_ROLES=('lane',)

def role_class(role:str)->str:
    r=budget.base_role(role)   # pilot_lane, prod_lane -> lane
    if r=='lane'or r.startswith('off'):return 'work'
    if r=='merge':return 'merge'
    if r in('plan','sweep'):return r
    return 'other'

def account(run:Path,env:dict)->dict:
    # D.5 (S3-R2-006): the accounting reads the campaign's data only, never a scheduling copy (prior_cost_model.json,
    # synthetic_cost_model.json): it is a cost consumer's path (design_fallback's eta_node, pilot_report's eta and latency)
    run=Path(run).resolve();m,_,_,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,scheduling_copies=False)
    c=ledger.dir_sha12(run);s=ledger.Settings(env);led=ledger.Ledger(s);led.read(writer=False)
    linked={r['job_id']for r in led.records if r['kind']=='register'and os.path.realpath(r.get('dir',''))==str(run)}
    rows=budget.union_rows(budget.q_sacct(env,False),budget.q_sacct(env,True))
    mine=[r for r in rows if r.ours and (r.info['c']==c or r.base in linked or r.jobid in linked)]
    per=defaultdict(float);attempts=[];alloc_core=defaultdict(float)
    for r in mine:
        if r.live:continue
        b=budget.tres_billing(r.partition,r.tres(),budget.profile(env))
        if b is None:b=128.0
        su=b*r.elapsed/3600.0;k=role_class(r.info['role']or'');per[k]+=su
        ac=(r.tres()or{}).get('cpu');cpus=ac or(128 if 'compute'in r.partition else 1);alloc_core[k]+=cpus*r.elapsed
        attempts.append({'job':r.jobid,'name':r.name,'state':r.state,'elapsed':r.elapsed,'billing':b,'su':su,'class':k,'submit':r.submit,'start':r.start,
                         'alloc_cpus':ac})   # sacct's AllocTRES cpu (AllocCPUS), None without TRES: thru_report's busy denominator
    jobs={r.base for r in mine}|{r.jobid for r in mine}
    busy=0.;unknown=set()
    for j in m['jobs']:
        d=run/'groups'/j['group']/'checkpoints'
        for k in range(j['blocks']):
            f=d/f'{prod.block_name(j["shard"],k)}.json'
            if not f.exists():continue
            doc=load(f);fp=(doc.get('runtime')or{}).get('fingerprint')or{};sl=fp.get('slurm')or{}
            jid=sl.get('SLURM_ARRAY_JOB_ID')or sl.get('SLURM_JOB_ID')
            if jid and str(jid)not in jobs:unknown.add(str(jid))
            busy+=sum(float(r['seconds'])for r in doc['native']['rows'])
    if unknown:raise Refuse(69,f'allocation unknown: checkpoint(s) name job id(s) {sorted(unknown)} that sacct does not show as c8d3- jobs of this campaign')
    eta=alloc_core['work']/busy if busy>0 else None
    return {'campaign':str(run),'c':c,'su_total':sum(per.values()),'su_by_class':dict(per),'attempts':attempts,'registered_jobs':sorted(linked),
            'busy_core_seconds':busy,'allocated_work_core_seconds':alloc_core['work'],'eta_node':eta,
            'note':'eta_node = allocated work core-seconds / busy core-seconds; plan, sweep and merge jobs are overhead'}

def main(argv=None,env=None)->int:
    env=dict(os.environ)if env is None else env
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path);p.add_argument('--json',action='store_true')
    a=p.parse_args(argv)
    try:r=account(a.run,env)
    except Refuse as e:print(f'accounting: {e}',file=sys.stderr);return e.code
    print(json.dumps(r,indent=None if a.json else 1));return 0
if __name__=='__main__':sys.exit(main())
