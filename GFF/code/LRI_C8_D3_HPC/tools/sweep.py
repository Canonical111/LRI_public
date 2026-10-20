#!/usr/bin/env python3
"""The cost sweep and the calibration refresh (PLAN D.14): a standalone runner on one exclusive compute node.

  sweep.py RUN --seed S [--refresh PREV [--refresh-bootstrap]] --output MODEL [--report REPORT]
           [--forbid-seeds-from FILE] [--reserve-seed LOG] [--scratch DIR] [--plan-only | --choose-only]

It plans RUN as a test-only campaign `--pilot --points 512 --replicates 2 --test-graphs all`, both campaigns, gmp,
`--mp-check on`, with --reserve-seed LOG ($C8_SEEDS) the seed rechecked and reserved in the seed log by the plan itself,
before anything is built or run (HD6, S2-002: a sweep killed later keeps its registration; required with
--forbid-seeds-from, 65 otherwise), registers its allocation in
the ledger (inside a job), runs every index heaviest first as one
`production.py run --index` process per lane (lanes pinned to the job's NUMA domains: C8_LANES, default numa), merges,
then runs make_cost_model.py.
  * J-SWEEP-1 (no --refresh): --plan-role cost_sweep on the bootstrap basis (--bootstrap-chunk 512 --shards 32).
  * --refresh PREV (J-SWEEP-2 and every refresh after a binary change): the plan's role is cost_refresh. sweep.py
    builds nothing; it hashes bin/c8d3_gmp and picks the basis from PREV's identity:
      the same executable sha256                          -> the measured basis (--cost-model PREV), a re-measurement;
      another sha256, every other HD11 field qualifying   -> the prior-model basis (--prior-cost-model PREV, F = 2);
      otherwise (CPU model, rates identity, mp_check, a missing key) or --refresh-bootstrap -> the bootstrap basis.
    Under the prior-model basis the fit check runs before any index: the factor-inflated integration wall
    (sum of prior-model task seconds / (lanes x lane width x 0.9)) must not exceed half of the job's remaining time
    (squeue %L); otherwise it refuses, naming both numbers.
  * The scheduling model never feeds the fresh one (make_cost_model.py copies no number from it); its provenance
    scheduled_with names PREV's sha256 and executable sha256; --report writes refresh_report.json (D.14).
--choose-only prints the basis choice and exits; --plan-only stops after the plan (tests run and merge themselves).
"""
from __future__ import annotations
import argparse,json,math,os,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,Refuse,cpu_model,digest
import production as prod
POINTS=512;REPLICATES=2;BOOT_CHUNK=512;BOOT_SHARDS=32;PRIOR_FACTOR=2.0

def choose(prev:Path|None,exe_sha:str,force_bootstrap:bool,mp_check:str='on',backend='gmp')->dict:
    """The basis of a sweep (D.14)."""
    if prev is None:return {'role':'cost_sweep','basis':'bootstrap','why':'first sweep (no previous model)'}
    if force_bootstrap:return {'role':'cost_refresh','basis':'bootstrap','why':'--refresh-bootstrap'}
    try:pm,_=prod.read_cost_model(prev,backend)
    except ValueError as e:return {'role':'cost_refresh','basis':'bootstrap','why':f'the previous model does not qualify ({e})'}
    prob=prod.identity_problems(pm,exe_sha,cpu_model(),mp_check)
    if not prob:return {'role':'cost_refresh','basis':'measured','why':'the same executable: a re-measurement'}
    if set(prob)=={'executable_sha256'}:return {'role':'cost_refresh','basis':'prior_model','why':f'another executable ({pm.get("executable_sha256","")[:12]} -> {exe_sha[:12]}), every other HD11 field qualifies'}
    return {'role':'cost_refresh','basis':'bootstrap','why':'the previous model does not qualify: '+', '.join(sorted(k for k in prob if k!='executable_sha256'))}

def plan_args(ch:dict,prev:Path|None,threads:int)->list:
    a=['--pilot','--points',POINTS,'--replicates',REPLICATES,'--test-graphs','all','--backend','gmp','--mp-check','on','--threads',threads,'--plan-role',ch['role']]
    if ch['basis']=='bootstrap':a+=['--bootstrap-chunk',BOOT_CHUNK,'--shards',BOOT_SHARDS]
    elif ch['basis']=='prior_model':a+=['--prior-cost-model',prev,'--prior-factor',PRIOR_FACTOR]
    else:a+=['--cost-model',prev]
    return [str(x)for x in a]

def tool(script:str,*args,check=True):
    cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools'/script),*map(str,args)],capture_output=True,text=True)
    if check and cp.returncode:raise RuntimeError(f'{script} {" ".join(map(str,args))} failed ({cp.returncode}): {(cp.stderr or cp.stdout)[-2000:]}')
    return cp

def remaining_seconds()->float:
    import lanes
    job=os.environ.get('SLURM_JOB_ID')
    if not job:
        v=os.environ.get('C8_LANE_SECONDS')
        if v and v.isdigit():return float(v)
        return math.inf
    return lanes.remaining_seconds(job,dict(os.environ))[0]

def lane_plan()->list:
    import lanes
    try:cpus=sorted(os.sched_getaffinity(0))
    except AttributeError:cpus=list(range(os.cpu_count()or 1))
    return lanes.cpu_lanes(cpus,os.environ.get('C8_LANES')or None)

def fit_check(m:dict,nlanes:int,width:int)->dict:
    """Prior-model basis: refuse when the factor-inflated wall exceeds half of the job's remaining time (D.14)."""
    tot=sum(j['est_core_seconds']or 0. for j in m['jobs']);wall=tot/(nlanes*width*prod.EFFICIENCY);left=remaining_seconds()
    if wall>left/2:raise Refuse(65,f'calibration refresh fit check: the prior-model wall {wall:.0f} s (x{m["prior_factor"]:g}) exceeds half of the job\'s remaining {left:.0f} s; '
                                   'nothing run (D.14): submit a longer sweep job or use --refresh-bootstrap')
    return {'wall_seconds':wall,'remaining_seconds':left}

def run_indices(run:Path,m:dict,lanes_cpus:list,scratch:str|None)->None:
    order=sorted(m['jobs'],key=lambda j:(-(j['est_core_seconds']if j['est_core_seconds']is not None else j['est_proxy_seconds']or 0.),j['id']))
    q=list(order);lock=threading.Lock();errors=[]
    def lane(cpus):
        while True:
            with lock:
                if not q or errors:return
                j=q.pop(0)
            def pin(c=cpus):
                try:os.sched_setaffinity(0,c)
                except (AttributeError,OSError):pass
            env={**os.environ,'OMP_NUM_THREADS':str(len(cpus)),'OMP_PROC_BIND':'close','OMP_PLACES':'cores'}
            cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools/production.py'),'run',str(run),'--index',str(j['id']),'--threads',str(len(cpus))]+(['--scratch',scratch]if scratch else[]),
                              capture_output=True,text=True,env=env,preexec_fn=pin)
            if cp.returncode:
                with lock:errors.append(f'index {j["id"]}: {(cp.stderr or cp.stdout)[-800:]}')
    th=[threading.Thread(target=lane,args=(c,))for c in lanes_cpus]
    for t in th:t.start()
    for t in th:t.join()
    if errors:raise RuntimeError('sweep indices failed: '+'; '.join(errors[:3]))

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--refresh',type=Path);p.add_argument('--refresh-bootstrap',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--forbid-seeds-from',type=Path,action='append');p.add_argument('--reserve-seed',type=Path);p.add_argument('--scratch');p.add_argument('--threads',type=int)
    p.add_argument('--plan-only',action='store_true');p.add_argument('--choose-only',action='store_true');a=p.parse_args(argv)
    try:
        if a.forbid_seeds_from and not a.reserve_seed:   # S2-002: a seed check goes with its reservation (production.py plan refuses it too)
            raise Refuse(65,'a sweep that checks its seed (--forbid-seeds-from) must reserve it in the same log: add --reserve-seed $C8_SEEDS (HD6, S2-002); nothing was planned')
        exe=prod.exe_for('gmp');exe_sha=digest(exe)
        ch=choose(a.refresh,exe_sha,a.refresh_bootstrap)
        print(json.dumps({'sweep':'refresh'if a.refresh else'first','executable_sha256':exe_sha,'previous_model':str(a.refresh)if a.refresh else None,
                          'previous_executable_sha256':(json.loads(a.refresh.read_bytes()).get('executable_sha256')if a.refresh else None),**ch}),flush=True)
        if a.choose_only:return 0
        if not a.output and not a.plan_only:raise Refuse(64,'give --output MODEL (or --plan-only)')
        lp=lane_plan();width=a.threads or max(len(l)for l in lp)
        args=plan_args(ch,a.refresh,width)
        for f in a.forbid_seeds_from or[]:args+=['--forbid-seeds-from',str(f)]
        if a.reserve_seed:args+=['--reserve-seed',str(a.reserve_seed)]   # HD6 before execution (S2-002)
        scratch=a.scratch or os.environ.get('C8_SCRATCH')
        tool('production.py','plan',a.run,'--seed',a.seed,*args,*(['--scratch',scratch]if scratch else[]))
        m=prod.load(a.run/'manifest.json')
        if os.environ.get('SLURM_JOB_ID'):tool('ledger.py','register',a.run,'--role','sweep')
        if ch['basis']=='prior_model':print(json.dumps({'fit_check':fit_check(m,len(lp),width)}),flush=True)
        if a.plan_only:return 0
        run_indices(a.run.resolve(),m,lp,scratch)
        tool('production.py','merge',a.run,'--jobs',max(1,min(8,os.cpu_count()or 1)),*(['--scratch',scratch]if scratch else[]))
        extra=['--previous',a.refresh,'--refresh-report',a.report or a.output.with_name('refresh_report.json')]if a.refresh else[]
        print(tool('make_cost_model.py',a.run,a.output,*extra).stdout.strip())
        return 0
    except Refuse as e:print(f'sweep: {e}',file=sys.stderr);return e.code
    except (RuntimeError,ValueError,OSError)as e:print(f'sweep: {e}',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
