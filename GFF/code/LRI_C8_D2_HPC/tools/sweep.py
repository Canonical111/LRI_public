#!/usr/bin/env python3
"""The cost-model sweep (PLAN component D, P5; J-SWEEP-1/2): a standalone runner, not lane mode, because lane mode
needs per-index estimates that do not exist before the first L8 measurement.

  sweep.py RUN --seed S [--points 512] [--replicates 2] [--threads T] [--procs N] [--backend gmp]
           (--bootstrap-chunk 512 --shards 8 | --cost-model MODEL) [--rates FILE --approved-numerics-change TEXT]
           [--numerics PROFILE --approved-numerics-change TEXT --calibration FILE]
           [--cost-model-out FILE] [--calibration FILE] [--merge-jobs J] [--scratch DIR] [--plan-only] [--seeds-log FILE]

1. plans an ordinary TEST-ONLY campaign: --pilot --points P --replicates R --test-graphs all, both campaigns (rates .8
   and .9, or the frozen map under --rates), the given backend and numerics (--numerics P: an opt-in profile, a
   numerics change that needs --approved-numerics-change, measured with bin/c8d2_gmp_<P>; route (b): the cost model of
   an approved profile, whose numerics identity is P, for design.py freeze --numerics P). The first sweep (J-SWEEP-1) has no measured cost
   model and no campaign-keyed calibration row: it plans with --bootstrap-chunk 512 --shards 8 (fixed 512-point tasks,
   the 120 s bound checked against the labelled preliminary proxy, no time estimate; R13). Later sweeps plan with the
   first sweep's cost model. An existing RUN of the same arguments is continued (requeue-safe); one planned with other
   arguments is refused before anything runs (Y12): the seed, backend, numerics, threads, points, replicates, the rates
   identity ('default', or the sha256 of the --rates map), the cost basis (--bootstrap-chunk and --shards, or the
   --cost-model's sha256 and --shards) and the checkpoint tasks must all be the frozen plan's;
2. registers the campaign's base seed in the forbidden-seed log (--seeds-log, default $C8_SEEDS; tools/seeds.py's
   add, idempotent, source = RUN as `seeds.py add RUN` writes it) right after the plan is published or the existing
   plan is validated, before any index runs, so that a sweep stopped or failing later still forbids its seed (D9; Y13).
   Inside a Slurm job a sweep without a seed log is refused before anything is planned; outside a job (local tests)
   it runs unregistered with a note. The log must exist (tools/seeds.py init);
   it then registers its own enclosing allocation in the campaign ledger, before any index runs
   (tools/ledger.py register RUN --role sweep; idempotent, a requeue adds an attempt note; R10);
3. runs every index itself, heaviest first (proxy units in the bootstrap, measured seconds otherwise), as N
   `production.py run --index` processes of T threads in the controlled OpenMP environment (common.omp_child_env; the
   claim gives its worker the same and watches its team, Y2), each pinned to its own CPU set (by default the lane mode's
   default lanes at width T: on AMD the NUMA nodes split into lanes of at most T cores, R5b; C8_LANES as in lane mode);
   no deadline logic: size the job to fit;
4. merges normally (production.py merge --jobs J), then writes the cost model (tools/make_cost_model.py: every
   campaign:sector:L:graph key, R05; it records the campaign's numerics and rates identity) and the campaign-keyed
   calibration rows (tools/calibrate.py --update, L8 included). W11 (Stage-6 fix round 4): a calibration file holds
   the rows of one measurement identity (numerics, rates identity), and tools/calibration.json only the exact path's
   default-rate rows, so a sweep under --numerics P or --rates FILE must name its own --calibration file, and a
   --calibration file of another identity is refused; both checked before anything is planned (except with
   --plan-only, which writes no rows; the full run checks again before it plans or runs anything).
Seeds (W20's class, Stage-6 fix round 4): a new sweep's seed is checked against the log before planning, and the
registration is one locked check-and-append (tools/seeds.py reserve): a seed another campaign registered (under
another source) is refused before any index runs.
Every step resumes (O09): a rerun in the same directory continues the plan, skips committed blocks and merged groups,
keeps an existing cost model that is this campaign's (equal to the one recomputed from its merged tables, apart from
its time stamp and note; make_cost_model.py --reuse-identical) and refuses an incompatible one by name, then completes
the calibration; a completed sweep reruns to the same model.
slurm/sweep.sh adds the seed again after the sweep (tools/seeds.py add RUN: 'present'); the three-log synchronization
(benchmarks/symmetry_2026-10-c8/stage5/scripts/seedsync.sh) then carries it to the other site's log and the mirror.
"""
from __future__ import annotations
import argparse,json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,digest,load,omp_child_env,utc
PY=[sys.executable,'-B']

def tool(name,*args,check=True,**kw):
    cp=subprocess.run([*PY,str(ROOT/'tools'/name),*map(str,args)],**kw)
    if check and cp.returncode:raise SystemExit(f'sweep: {name} {" ".join(map(str,args))} failed (exit {cp.returncode})')
    return cp

def plan_args(a)->list:
    args=['--pilot','--points',a.points,'--replicates',a.replicates,'--test-graphs','all','--backend',a.backend,'--threads',a.threads,'--seed',a.seed]
    if a.bootstrap_chunk:args+=['--bootstrap-chunk',a.bootstrap_chunk,'--shards',a.shards]
    elif a.cost_model:args+=['--cost-model',a.cost_model]+(['--shards',a.shards]if a.shards else[])
    else:raise SystemExit('sweep: give --bootstrap-chunk P --shards N (the first sweep) or --cost-model MODEL')
    if a.checkpoint_tasks:args+=['--checkpoint-tasks',a.checkpoint_tasks]
    if (a.rates or a.numerics!='exact')and not a.approved_numerics_change:
        raise SystemExit('sweep: --rates and --numerics other than exact are numerics changes: they need --approved-numerics-change (A-FLAG-2)')
    if a.rates:args+=['--rates',a.rates]
    if a.numerics!='exact':args+=['--numerics',a.numerics]
    if a.rates or a.numerics!='exact':args+=['--approved-numerics-change',a.approved_numerics_change]
    for f in a.forbid_seeds_from or[]:args+=['--forbid-seeds-from',f]
    return [str(x)for x in args]

def requested_identity(a)->dict:
    """What the plan of these arguments freezes (Y12): every manifest field a resumed sweep must match. The rates
    identity is 'default' without --rates, else the sha256 of the map file (production.py plan's rates identity); the
    cost basis is the bootstrap (chunk and shards) or the cost model's sha256 (and --shards, if given); the checkpoint
    tasks default as production.py plan's: max(16 x threads, 256)."""
    want={'seed':a.seed,'backend':a.backend,'numerics':a.numerics,'threads':a.threads,'test_only':True,'test_graphs':'all',
          'points':a.points,'replicates':a.replicates,'rates_identity':digest(a.rates)if a.rates else'default',
          'checkpoint_tasks':a.checkpoint_tasks if a.checkpoint_tasks else max(16*a.threads,256),'shards':a.shards}
    if a.bootstrap_chunk:want.update(cost_basis='bootstrap',bootstrap_chunk=a.bootstrap_chunk,cost_model_sha256=None)
    elif a.cost_model:want.update(cost_basis='measured',bootstrap_chunk=None,cost_model_sha256=digest(a.cost_model))
    else:raise SystemExit('sweep: give --bootstrap-chunk P --shards N (the first sweep) or --cost-model MODEL')
    return want

def frozen_identity(m:dict)->dict:
    """The same fields from an existing sweep campaign's manifest."""
    al=m.get('allocation')or{}
    return {'seed':m.get('seed'),'backend':m.get('backend'),'numerics':m.get('numerics'),'threads':m.get('threads'),'test_only':m.get('test_only'),
            'test_graphs':m.get('test_graphs'),'points':al.get('points'),'replicates':al.get('replicates'),'rates_identity':m.get('rates_identity'),
            'checkpoint_tasks':m.get('checkpoint_tasks'),'shards':(m.get('index_sizing')or{}).get('shards'),'cost_basis':m.get('cost_basis'),
            'bootstrap_chunk':(m.get('chunking')or{}).get('bootstrap_chunk'),'cost_model_sha256':m.get('cost_model_sha256')}

def check_existing(run:Path,a)->None:
    """Continue an existing sweep campaign only when it was planned with these arguments (Y12, S6D-R2-04): a sweep
    resumed with another --rates map (or without the map it was planned with), another cost basis, shard count or
    checkpoint size would measure the frozen plan, not the request. Refused, naming every difference."""
    m=load(run/'manifest.json');want=requested_identity(a);got=frozen_identity(m)
    diff=[f'{k}: requested {want[k]!r}, planned {got[k]!r}'for k in want if want[k]!=got[k]]
    if diff:raise SystemExit(f'sweep: {run} exists with other arguments ({"; ".join(diff)}); it measures what it was planned with, not this request: '
                             'use a new directory (Y12)')
    print(f'sweep: continuing the existing plan {run}',flush=True)

def seed_log(a,env:dict)->Path|None:
    """The forbidden-seed log the sweep registers its seed in (Y13): --seeds-log, else $C8_SEEDS; it must exist. None
    only outside a Slurm job (local tests); inside one a sweep without a log is refused before anything is planned."""
    log=a.seeds_log or (Path(env['C8_SEEDS'])if env.get('C8_SEEDS')else None)
    if log is None:
        if env.get('SLURM_JOB_ID'):raise SystemExit('sweep: a sweep in a Slurm job registers its seed in the forbidden-seed log before any index runs (D9, Y13): '
                                                     'give --seeds-log FILE or set C8_SEEDS (tools/seeds.py init creates the log); nothing planned')
        return None
    if not Path(log).is_file():raise SystemExit(f'sweep: the seed log {log} does not exist (tools/seeds.py init creates it); nothing planned')
    return Path(log)

def seed_check(seed:int,source:str,log:Path):
    """W20's class (Stage-6 fix round 4): check(doc) for tools/seeds.py reserve: why `seed` may not be this sweep's, given
    the seed log doc (read under its lock) without the sweep's own entries (seed, RUN): production.seed_refusal (an
    archived or used base seed, a forbidden seed, a derived C8 group seed of one, or one of its own group seeds equal to
    one)."""
    import production as prod
    def check(doc):
        mine={'schema':doc.get('schema'),'seeds':[e for e in doc['seeds']if (e['seed'],e.get('source'))!=(seed,source)]}
        why=prod.seed_refusal(seed,prod.seed_entries(mine,log))
        return [why]if why else[]
    return check

def precheck_seed(seed:int,source:str,log:Path|None)->None:
    """Before a new sweep is planned: its seed against the log as it is now (no lock; reserve re-checks under the lock),
    so a seed a campaign already registered is refused before anything is created."""
    if log is None:return
    import seeds
    try:why=seed_check(seed,source,log)(seeds.read_log(log))
    except (ValueError,OSError)as e:raise SystemExit(f'sweep: the seed log {log} cannot be read ({e}); nothing planned')
    if why:raise SystemExit(f'sweep: {why[0]}; choose a fresh random seed (python3 -c "import secrets;print(secrets.randbits(63))"); nothing planned (D9, W20)')

def register_seed(run:Path,log:Path|None)->None:
    """Y13 (S6R2-F-01): the campaign's base seed into the log, as `tools/seeds.py add RUN` writes it (source = RUN, so
    the job script's add after the sweep is 'present'), right after the plan is published or validated and before any
    index runs. W20's class (Stage-6 fix round 4): in ONE transaction under the log's lock (tools/seeds.py reserve): the
    log is re-read and the seed checked against it (seed_check) before it is appended, so a seed another campaign
    registered after this sweep's plan read its forbidden list (or a sweep without --forbid-seeds-from) is refused, and
    no index runs; the sweep's own earlier entry (a resumed sweep) is 'present'."""
    seed=int(load(run/'manifest.json')['seed'])
    if log is None:
        print(f'sweep: not inside a Slurm job and no seed log (--seeds-log, C8_SEEDS): seed {seed} is NOT registered (local work)',flush=True);return
    import seeds
    try:st=seeds.reserve(log,[(seed,str(run))],seed_check(seed,str(run),log),f'tools/sweep.py: register seed {seed}')
    except (seeds.Refuse,ValueError,RuntimeError,OSError)as r:raise SystemExit(f'sweep: the seed {seed} could not be registered in {log} ({r}); no index was run')
    state='added'if st['added']else'present'
    print(f'sweep: seed {seed} {state} in {log} (before any index runs, one locked check and append; D9, Y13, W20)',flush=True)

def run_indices(run:Path,a,env)->list:
    import lanes
    m=load(run/'manifest.json');jobs=sorted(m['jobs'],key=lambda j:(-(j['est_core_seconds']if j['est_core_seconds']is not None else j['est_proxy_units']),j['id']))
    try:cpus=sorted(os.sched_getaffinity(0))
    except AttributeError:cpus=list(range(os.cpu_count()or 1))
    spec=env.get('C8_LANES')or None
    sets=lanes.cpu_lanes(cpus,spec,width=a.threads)if a.procs is None else lanes.equal_parts([c for _,c in lanes.physical(cpus)],a.procs)
    sets=[s[:a.threads]for s in sets if len(s)>=1]
    logs=run/'sweep_logs';logs.mkdir(exist_ok=True);job=env.get('SLURM_JOB_ID','local');restart=env.get('SLURM_RESTART_COUNT','0')
    print(f'sweep: {len(jobs)} indices on {len(sets)} process slots of {[len(s)for s in sets]} CPUs ({spec or "default lanes"}), heaviest first',flush=True)
    free=list(range(len(sets)));running={};failed=[];t0=time.time();todo=list(jobs)
    while todo or running:
        while todo and free:
            slot=free.pop(0);j=todo.pop(0);cs=sets[slot];log=(logs/f'idx{j["id"]}.{job}.{restart}.{time.time_ns()}.log').open('x')
            pre=(lambda cs=cs:os.sched_setaffinity(0,cs))if hasattr(os,'sched_setaffinity')else None
            p=subprocess.Popen([*PY,str(ROOT/'tools/production.py'),'run',str(run),'--index',str(j['id']),'--threads',str(len(cs))]+(['--scratch',a.scratch]if a.scratch else[]),
                               stdout=log,stderr=subprocess.STDOUT,env=omp_child_env(len(cs),env),preexec_fn=pre)  # Y2
            running[p.pid]=(p,slot,j,log,time.time())
        time.sleep(0.2)
        for pid,(p,slot,j,log,ts)in list(running.items()):
            rc=p.poll()
            if rc is None:continue
            running.pop(pid);log.close();free.append(slot)
            print(f'sweep: index {j["id"]} ({j["group"]} shard {j["shard"]}) exit {rc} after {time.time()-ts:.0f} s; {len(todo)} queued, {len(running)} running, {time.time()-t0:.0f} s elapsed',flush=True)
            if rc:failed.append(j['id'])
    return failed

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--points',type=int,default=512);p.add_argument('--replicates',type=int,default=2);p.add_argument('--threads',type=int,default=8)
    p.add_argument('--procs',type=int,help='process slots (default: one per lane of C8_LANES; unset: NUMA nodes in lanes of at most --threads cores on AMD)');p.add_argument('--backend',default='gmp')
    p.add_argument('--bootstrap-chunk',type=int);p.add_argument('--shards',type=int);p.add_argument('--cost-model',type=Path);p.add_argument('--checkpoint-tasks',type=int)
    p.add_argument('--rates',type=Path);p.add_argument('--approved-numerics-change');p.add_argument('--forbid-seeds-from',type=Path,action='append')
    p.add_argument('--numerics',default='exact',help='opt-in numerics profile to measure under (a numerics change: needs --approved-numerics-change; route (b) cost models)')
    p.add_argument('--cost-model-out',type=Path);p.add_argument('--calibration',type=Path,default=ROOT/'tools/calibration.json');p.add_argument('--merge-jobs',type=int,default=8)
    p.add_argument('--scratch');p.add_argument('--plan-only',action='store_true')
    p.add_argument('--seeds-log',type=Path,help='forbidden-seed log to register the base seed in before any index runs (default $C8_SEEDS; required in a Slurm job)')
    a=p.parse_args(argv)
    run=a.run.resolve();env=dict(os.environ)
    import calibrate
    if a.rates and not Path(a.rates).is_file():raise SystemExit(f'sweep: --rates {a.rates} does not exist; nothing planned')
    ident={'numerics':a.numerics,'rates_identity':digest(a.rates)if a.rates else'default'}  # what this sweep's rows are measured under
    if not a.plan_only:  # W11: before anything is planned (calibrate.update, the writer, checks it again; --plan-only writes no rows)
        try:calibrate.check_destination(a.calibration,ident)
        except ValueError as e:raise SystemExit(f'sweep: {e}; nothing planned')
    log=seed_log(a,env)  # Y13: before anything is planned
    if (run/'manifest.json').exists():check_existing(run,a)
    else:precheck_seed(a.seed,str(run),log);tool('production.py','plan',run,*plan_args(a))  # W20's class: a logged seed refused first
    register_seed(run,log)  # Y13: the seed is forbidden before any index runs
    reg=tool('ledger.py','register',run,'--role','sweep',check=False,capture_output=True,text=True)
    if reg.returncode:
        if env.get('SLURM_JOB_ID'):raise SystemExit(f'sweep: ledger registration failed: {reg.stderr.strip()}')
        print('sweep: not inside a Slurm job; nothing registered in the ledger (local work is reported as unaccounted)',flush=True)
    else:print('sweep: ledger '+reg.stdout.strip(),flush=True)
    if a.plan_only:return 0
    failed=run_indices(run,a,env)
    if failed:raise SystemExit(f'sweep: {len(failed)} indices failed ({failed[:10]}); rerun the sweep in the same directory to retry them')
    tool('production.py','status',run,'--fast',stdout=subprocess.DEVNULL)
    sc=['--scratch',a.scratch]if a.scratch else[]
    tool('production.py','merge',run,'--jobs',a.merge_jobs,*sc)
    out=a.cost_model_out or run/'cost_model_measured.json'
    tool('make_cost_model.py',run,out,'--note',f'sweep {run.name} ({utc()})','--reuse-identical')  # O09: a restart keeps this campaign's model
    tool('calibrate.py',run,'--update',a.calibration,stdout=subprocess.DEVNULL)
    print(json.dumps({'sweep':str(run),'cost_model':str(out),'calibration':str(a.calibration)}),flush=True);return 0
if __name__=='__main__':sys.exit(main())
