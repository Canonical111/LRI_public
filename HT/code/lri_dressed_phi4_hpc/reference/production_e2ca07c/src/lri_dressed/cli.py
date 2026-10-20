"""One solver process per point, or serial continuation lanes per bath cutoff.

Threads parallelize row-owned kernels. Slurm arrays or the node-packing launcher
(scripts/pack_node.py) distribute independent points/lanes over nodes. Multi-rank
launch of this serial eigensolver is rejected.

Exit codes: 0 done, 75 stopped at a safe Newton boundary (checkpointed),
73 an item is claimed by a live owner elsewhere, 1 failure.
"""
from __future__ import annotations
import argparse,json,os,signal,sys,time,resource,math
from pathlib import Path
from .io import atomic_json,claim,digest,envelope,read_envelope,source_fingerprint,runtime,validate_result
from .planning import plan,guard
from .lease import Claimed

GRID=[.2499,.249,.2475,.245,.24,.235,.23,.225,.22,.21,.20,.19,.18,.175,.17,.16,.15,.14,.13,.125,.12,.11,.10,.09,.08,.075,.07,.06,.05,.04,.03,.025,.02,.015,.0125,.01,.0075,.005,.003,.002,.001,.0005,.0002,.0001]
STOP=False
EXIT_STOPPED=75;EXIT_CLAIMED=73
class InterruptedRun(RuntimeError):pass

def request_stop(signum,frame):
    global STOP
    STOP=True

def setup_runtime(threads):
    if threads<1:raise ValueError('threads must be positive')
    for var in ('OMPI_COMM_WORLD_SIZE','PMI_SIZE','PMIX_SIZE','MV2_COMM_WORLD_SIZE','SLURM_NTASKS'):
        if int(os.environ.get(var,'1'))>1:
            raise RuntimeError('One solver process per item is supported. Use Slurm arrays, not multi-rank mpiexec/srun.')
    # Numba is imported by planning; launcher must set NUMBA_NUM_THREADS >= threads.
    os.environ.setdefault('NUMBA_NUM_THREADS',str(threads))
    from numba import set_num_threads
    from threadpoolctl import threadpool_limits
    set_num_threads(threads);threadpool_limits(1)
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):signal.signal(sig,request_stop)
    # A launcher may start us with these signals blocked (pack_node), so that a stop request
    # during interpreter/Numba start-up stays pending instead of killing us; deliver it now.
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT,signal.SIGUSR1})

def configuration(args,delta,planned):
    return {'bath_cut':args.bath_cut,'nz':args.nz,'osc':args.osc,'delta':float(delta),
       'reflection':0,'zero_scale':args.zero_scale,'eig_tol':args.eig_tol,
       'residual_tol':args.residual_tol,'tuning_tol':args.tuning_tol,'maxiter':args.maxiter,
       'ncv':args.ncv,'max_eig_iter':args.max_eig_iter,'resolved_backend':planned['backend'],
       'window':args.window,'window_mode':args.window_mode if args.window!='none' else None,
       'window_tol':args.window_tol if args.window!='none' else None,
       'window_maxiter':args.window_maxiter if args.window!='none' else None,
       'dtype':'float64','fastmath':False,'source_sha256':source_fingerprint(),'runtime':runtime()}

def seed_theta(path,delta):
    row=json.loads(Path(path).read_text())
    if row.get('schema'):
        row=read_envelope(path,kind='result')['payload']
    if not math.isfinite(row.get('delta',float('nan'))) or abs(row['delta']-delta)>1e-12:
        raise ValueError('Seed delta differs from requested delta; use --guess for intentional continuation')
    theta=row.get('theta')
    if not isinstance(theta,list) or len(theta)!=2 or not all(math.isfinite(v) for v in theta):raise ValueError('Invalid seed')
    if row.get('tuning_residual',float('inf'))>1e-7:raise ValueError('Unaccepted seed')
    return theta

def execute(args):
    setup_runtime(args.threads)
    from .solver import DressedSolver
    deltas=sorted(set(args.deltas),reverse=True)
    if not deltas or any(not math.isfinite(d) or not 0<d<.25 for d in deltas):raise ValueError('All delta values must lie strictly between 0 and 1/4')
    if args.seed and len(deltas)!=1:raise ValueError('--seed is for one exact delta; use --seed-dir for a scan')
    planned=plan(args.bath_cut,args.nz,args.osc,args.backend,args.ncv,args.window)
    previous=None;solver=None;run_start=time.perf_counter()
    for delta in deltas:
        cfg=configuration(args,delta,planned);key=f'N{args.bath_cut}_z{args.nz}_o{args.osc}_x{delta:.12g}_{digest(cfg)[:16]}'
        base=Path(args.output_dir);path=base/(key+'.json');cp=base/'checkpoints'/(key+'.json')
        with claim(base/'claims'/(key+'.lock')):
            if path.exists():
                if not args.resume:raise FileExistsError(f'Output exists: {path}; use --resume')
                row=read_envelope(path,'result',cfg)['payload'];validate_result(row,cfg);previous=row
                print(json.dumps({'status':'reused','path':str(path),'Delta_thermal':row['Delta_thermal']}),flush=True);continue
            guess=args.guess if args.guess is not None else (None if previous is None else previous['theta'])
            source='guess' if args.guess is not None else ('continuation' if previous is not None else 'initial')
            seed_used=None
            if args.seed:seed_used=Path(args.seed)
            if args.seed_dir:
                candidates=[]
                for pp in Path(args.seed_dir).glob('*.json'):
                    try:
                        raw=json.loads(pp.read_text());r=raw.get('payload',raw)
                        if abs(r.get('delta',-1)-delta)<1e-12 and r.get('tuning_residual',1)<1e-8:
                            candidates.append((abs(r.get('bath_cut',-100)-args.bath_cut),-r.get('nz_per_parity',0),str(pp)))
                    except (OSError,ValueError,TypeError):continue
                if candidates:seed_used=Path(min(candidates)[2])
            if seed_used:guess=seed_theta(seed_used,delta);source='seed'

            recovered=False
            if cp.exists() and args.resume:
                saved=read_envelope(cp,'checkpoint',cfg)['payload'];guess=saved['theta'];recovered=True;source='checkpoint'
            guard(planned,args.memory_limit_gib)
            if solver is None:
                solver=DressedSolver(args.bath_cut,args.nz,args.osc,eig_tol=args.eig_tol,
                  zero_scale=args.zero_scale,backend=planned['backend'],ncv=args.ncv,
                  max_eig_iter=args.max_eig_iter,residual_tol=args.residual_tol,window=args.window,
                  window_mode=args.window_mode,window_tol=args.window_tol,window_maxiter=args.window_maxiter)
            bridges=[]
            if guess is None and delta<.23:
                for mid in [x for x in GRID if x>delta][::2]:
                    solver.checkpoint=None;solver.set_delta(mid)
                    rr=solver.solve(guess,tol=args.tuning_tol,maxiter=args.maxiter)
                    guess=rr['theta'];source='bridge';bridges.append({'delta':mid,'theta':guess,'tuning_residual':rr['tuning_residual']})
                    if STOP:raise InterruptedRun('Stopped after continuation bridge; no target result published')
            solver.set_delta(delta)
            # Source behaviour: very weak coupling always restarts from the perturbative guess.
            if 1-4*delta<.04 and not recovered:guess=solver.initial(1-4*delta);source='initial_override' if source!='initial' else source
            def checkpoint(theta,history):
                atomic_json(cp,envelope('checkpoint',cfg,{'theta':theta.tolist(),'history':history}))
                if STOP:raise InterruptedRun('Checkpointed at safe Newton boundary')
            solver.checkpoint=checkpoint
            try:
                row=solver.solve(guess,tol=args.tuning_tol,maxiter=args.maxiter)
                row['execution']={'threads':args.threads,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                     'seed':str(seed_used) if seed_used else None,'checkpoint_recovered':recovered,'guess_source':source,
                     'continuation_bridges':bridges,'lane_elapsed_seconds':time.perf_counter()-run_start}
                validate_result(row,cfg);atomic_json(path,envelope('result',cfg,row));previous=row
                print(json.dumps({'status':'completed','path':str(path),'Delta_thermal':row['Delta_thermal'],'seconds':row['seconds']}),flush=True)
            except InterruptedRun:raise
            except Exception as exc:
                atomic_json(base/'failures'/(key+'.json'),envelope('failure',cfg,{'type':type(exc).__name__,'error':str(exc)}))
                raise

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    run=sub.add_parser('run');pl=sub.add_parser('plan');ex=sub.add_parser('export');status=sub.add_parser('status')
    ident=sub.add_parser('identities',help='Descendant-identity diagnostic for an accepted result record')
    for pp in (run,pl):
        pp.add_argument('--bath-cut',type=int,required=True);pp.add_argument('--nz',type=int,default=24);pp.add_argument('--osc',type=int,default=192)
        pp.add_argument('--backend',choices=['auto','tensor','ladder'],default='auto');pp.add_argument('--ncv',type=int,default=28)
        pp.add_argument('--window',choices=['none','vacuum'],default='none',help='opt-in full-vacuum window correction')
    run.add_argument('--window-mode',choices=['consistent','literal'],default='consistent')
    run.add_argument('--window-tol',type=float,default=1e-12);run.add_argument('--window-maxiter',type=int,default=50)
    ident.add_argument('--result',required=True);ident.add_argument('--output',required=True)
    ident.add_argument('--k',type=int,default=12);ident.add_argument('--threads',type=int,default=1)
    run.add_argument('--deltas',type=float,nargs='+',required=True);run.add_argument('--threads',type=int,default=1)
    run.add_argument('--output-dir',default='results');run.add_argument('--seed');run.add_argument('--seed-dir');run.add_argument('--guess',type=float,nargs=2)
    run.add_argument('--resume',action='store_true');run.add_argument('--memory-limit-gib',type=float)
    run.add_argument('--zero-scale',type=float,default=1.);run.add_argument('--eig-tol',type=float,default=3e-11)
    run.add_argument('--residual-tol',type=float,default=2e-7);run.add_argument('--tuning-tol',type=float,default=5e-10)
    run.add_argument('--maxiter',type=int,default=30);run.add_argument('--max-eig-iter',type=int,default=10000)
    for pp in (ex,status):pp.add_argument('--input-dir',required=True)
    ex.add_argument('--output',required=True)
    args=p.parse_args(argv)
    try:
        if args.cmd=='plan':print(json.dumps(plan(args.bath_cut,args.nz,args.osc,args.backend,args.ncv,args.window),indent=2));return 0
        if args.cmd=='identities':
            setup_runtime(args.threads)
            from .identities import diagnose
            r=read_envelope(args.result,'result');validate_result(r['payload'],r['config'])
            atomic_json(args.output,diagnose(r['payload'],r['config'],k=args.k,record_sha256=r['sha256']));return 0
        if args.cmd in ('status','export'):
            rows=[];errors=[]
            for path in sorted(Path(args.input_dir).glob('*.json')):
                try:
                    r=read_envelope(path,'result');validate_result(r['payload'],r['config']);rows.append(r)
                except Exception as exc:errors.append({'path':str(path),'error':str(exc)})
            if args.cmd=='status':print(json.dumps({'accepted':len(rows),'rejected':errors},indent=2));return int(bool(errors))
            if errors:raise ValueError('Refusing export with rejected records: '+str(errors))
            atomic_json(args.output,[dict(r['payload'],provenance=r['config'],record_sha256=r['sha256']) for r in rows]);return 0
        execute(args);return 0
    except InterruptedRun as exc:print(str(exc),file=sys.stderr);return EXIT_STOPPED
    except Claimed as exc:print(str(exc),file=sys.stderr);return EXIT_CLAIMED

if __name__=='__main__':sys.exit(main())
