"""One-writer, restartable HPC point driver; independent Slurm array tasks.

No new Hamiltonian terms or tuning conditions are introduced. Claim directories
fail closed after a crash: never guess that a remote owner is dead. The optional
Slurm array scales independent points, not a single ARPACK diagonalization.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,platform,signal,socket,sys,time,uuid,resource
from pathlib import Path
from contextlib import contextmanager

ROOT=Path(__file__).resolve().parents[2]


def canonical_json(data):
    return json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(data):return hashlib.sha256(canonical_json(data)).hexdigest()
def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hash():
    h=hashlib.sha256()
    paths=sorted((ROOT/'code').rglob('*.py'))+[ROOT/'inputs/prior_2d_points.json']
    for p in paths:
        h.update(str(p.relative_to(ROOT)).encode());h.update(p.read_bytes())
    return h.hexdigest()


def atomic_json(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with tmp.open('wb') as f:
            f.write(canonical_json(data)+b'\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        fd=os.open(str(path.parent),os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        tmp.unlink(missing_ok=True)


class Claimed(RuntimeError):pass
class SafeStop(RuntimeError):pass
class IntegrityError(ValueError):
    """Changed/corrupt inputs, checkpoint or existing output (exit 65; never a numerical failure)."""


@contextmanager
def claim(output, request_hash):
    """Atomic mkdir is required on the shared filesystem; no flock dependency."""
    lock=Path(str(output)+'.claim');lock.parent.mkdir(parents=True,exist_ok=True)
    token=uuid.uuid4().hex
    try:lock.mkdir()
    except FileExistsError as exc:raise Claimed(f'Output claimed: {lock}; inspect owner and confirm job death before offline recovery') from exc
    try:
        atomic_json(lock/'owner.json',{'token':token,'request_digest':request_hash,'host':socket.gethostname(),'pid':os.getpid(),
                    'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'slurm_array_task_id':os.environ.get('SLURM_ARRAY_TASK_ID'),'created_unix':time.time()})
        yield
    finally:
        try:
            owner=json.loads((lock/'owner.json').read_text())
            if isinstance(owner,dict) and owner.get('token')==token:
                (lock/'owner.json').unlink();lock.rmdir()
        except (OSError,ValueError):pass   # a damaged owner record leaves the claim fail-closed


def validate_record(row, request):
    if not row.get('accepted') or row.get('request_digest')!=request:
        raise ValueError('Result is incomplete or belongs to another configuration')
    data=dict(row);signature=data.pop('record_sha256',None)
    if signature!=digest(data):raise ValueError('Result checksum failed')
    cfg=row['configuration']
    if row['tuning_residual']>max(1e-10,5*cfg['tuning_tol']):raise ValueError('Tuning gate')
    if row['max_eigenvector_residual']>cfg['residual_tol'] or row['max_orthogonality_residual']>1e-9:
        raise ValueError('Scalar eigenvector/orthogonality gate')
    if row['window']!='none':
        W=row['window_correction']
        if max([W['top_fixed_point_residual'],*W['sublevel_fixed_point_residuals'].values()])>1e-11:
            raise ValueError('Vacuum fixed-point gate')
    return row


PERSISTED_ERRORS=(OSError,ValueError,KeyError,TypeError,AttributeError,IndexError)


def existing_record(path,request,expected_sha256=None):
    """Validate an existing output for reuse/check-only; any defect is an integrity failure.

    With expected_sha256 the bytes are read ONCE, must hash to that value, and are the bytes
    validated (a caller's validated snapshot cannot be swapped underneath it)."""
    try:
        data=Path(path).read_bytes()
        if expected_sha256 is not None and hashlib.sha256(data).hexdigest()!=expected_sha256:
            raise IntegrityError('Output bytes differ from the expected snapshot')
        row=json.loads(data)
        if not isinstance(row,dict):raise TypeError('record is not a JSON object')
        return validate_record(row,request)
    except PERSISTED_ERRORS as exc:raise IntegrityError(f'Existing output invalid: {exc}') from exc


def finite_theta(value,what):
    if not (isinstance(value,list) and len(value)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in value)):
        raise IntegrityError(f'{what} has no finite two-component theta')
    return [float(v) for v in value]


def load_checkpoint(path,request):
    """Checkpoint read/decode/shape/signature failures are all integrity failures (exit 65)."""
    try:
        cp=json.loads(Path(path).read_text())
        if not isinstance(cp,dict):raise TypeError('checkpoint is not a JSON object')
        saved=dict(cp);sig=saved.pop('checkpoint_sha256',None)
        if sig!=digest(saved) or cp.get('request_digest')!=request:raise IntegrityError('Incompatible/corrupt checkpoint')
        return finite_theta(cp.get('theta'),'checkpoint')
    except IntegrityError:raise
    except PERSISTED_ERRORS as exc:raise IntegrityError(f'Corrupt checkpoint: {exc}') from exc


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--L',type=int,required=True);p.add_argument('--x',type=float,required=True)
    p.add_argument('--nz',type=int,default=16);p.add_argument('--osc',type=int,default=192)
    p.add_argument('--backend',choices=['auto','tensor','gram','ladder'],default='auto')
    p.add_argument('--window',choices=['none','vacuum'],default='vacuum')
    p.add_argument('--window-mode',choices=['consistent','literal'],default='consistent')
    p.add_argument('--basis',type=Path);p.add_argument('--seed',type=Path)
    p.add_argument('--guess',nargs=2,type=float);p.add_argument('--train-keep',type=int,default=0)
    p.add_argument('--threads',type=int,default=1);p.add_argument('--ncv',type=int,default=40)
    p.add_argument('--eig-tol',type=float,default=1e-12);p.add_argument('--residual-tol',type=float,default=1e-8)
    p.add_argument('--tuning-tol',type=float,default=3e-11);p.add_argument('--maxiter',type=int,default=50)
    p.add_argument('--diagnostics',choices=['none','first','all'],default='all')
    p.add_argument('--max-bath-states',type=int,default=2_000_000)
    p.add_argument('--memory-limit-gib',type=float,default=8.)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--resume',action='store_true')
    p.add_argument('--check-only',action='store_true',help='Validate an existing record without eigensolves')
    return p


def run(args):
    # Set environment BEFORE numerical imports: do not oversubscribe local BLAS.
    for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS','BLIS_NUM_THREADS'):
        os.environ[key]='1'
    os.environ.setdefault('NUMBA_NUM_THREADS',str(args.threads))
    import numpy as np,scipy,numba
    from numba import set_num_threads
    from threadpoolctl import threadpool_limits
    from .solver import DressedSolver
    from .density import DensitySolver,select_density_basis
    from .diagnostics import diagnose
    # x = 1/8 (s = s* = 7/4) is admitted as the short-range crossover benchmark; the scan is 1/8 < x < 1/2.
    if not .125<=args.x<.5:raise ValueError('This direct 2D scan requires 1/8 <= x < 1/2')
    if args.threads<1 or args.memory_limit_gib<=0:raise ValueError('Invalid resources')
    set_num_threads(args.threads)
    if args.basis and (args.window!='vacuum' or args.window_mode!='consistent' or args.train_keep):
        raise ValueError('Saved optimized bases require the consistent window and cannot be teachers')
    if args.train_keep and (args.window!='vacuum' or args.window_mode!='consistent'):
        raise ValueError('Training requires the consistent full-vacuum window')
    try:input_bytes={key:getattr(args,key).read_bytes() for key in ('basis','seed') if getattr(args,key)}
    except OSError as exc:raise IntegrityError(f'Unreadable input: {exc}') from exc
    configuration={k:str(v.resolve()) if isinstance(v,Path) else v for k,v in vars(args).items()
                   if k not in ('resume','check_only','output')}
    # Bind file CONTENT as well as path; input mutation cannot silently reuse a result.
    for key in ('basis','seed'):
        path=getattr(args,key)
        if path:configuration[key+'_sha256']=hashlib.sha256(input_bytes[key]).hexdigest()
    configuration['source_sha256']=source_hash()
    # The array launcher supplies expectations; verify the SAME bytes used below,
    # not just an earlier read in another process (input TOCTOU protection).
    expected_source=os.environ.get('HT2D_FROZEN_SOURCE')
    if expected_source and expected_source!=configuration['source_sha256']:
        raise IntegrityError('Source changed since the frozen array manifest')
    expected_inputs=json.loads(os.environ.get('HT2D_FROZEN_INPUTS','{}'))
    loaded_hashes={str(getattr(args,k).resolve()):hashlib.sha256(b).hexdigest() for k,b in input_bytes.items()}
    if expected_inputs and loaded_hashes!=expected_inputs:
        raise IntegrityError('Inputs changed since the frozen array manifest')
    from .operators import SPARSE_PARALLEL_MIN_WORK
    configuration['sparse_parallel_min_work']=SPARSE_PARALLEL_MIN_WORK
    configuration['runtime']={'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
                              'numba':numba.__version__,'machine':platform.machine()}
    request=digest(configuration)
    if args.check_only:
        existing_record(args.output,request,os.environ.get('HT2D_EXPECT_OUTPUT_SHA256') or None);print('VALID',args.output);return 0
    stop={'requested':False}
    def on_signal(sig,frame):stop['requested']=True
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):signal.signal(sig,on_signal)
    checkpoint=Path(str(args.output)+'.checkpoint.json')
    with claim(args.output,request),threadpool_limits(limits=1,user_api='blas'):
        if args.output.exists():
            if not args.resume:raise ValueError('Output exists; use --resume with identical configuration')
            existing_record(args.output,request);print('REUSE',args.output);return 0
        seed=args.guess
        if args.seed:
            try:seed_row=json.loads(input_bytes['seed'])
            except ValueError as exc:raise IntegrityError(f'Seed is not JSON: {exc}') from exc
            seed=finite_theta(seed_row.get('theta') if isinstance(seed_row,dict) else None,'seed')
        teacher=None;artifact=None
        if args.basis:
            try:
                teacher=json.loads(input_bytes['basis']);artifact=teacher['basis_artifact']
                ax,aw=artifact['x'],artifact.get('window')
                u=np.asarray(artifact['isometry'],np.float64);scale=artifact['scale']
                # Whole-artifact integrity (IR3-03): the same properties FixedLocal requires of the slice,
                # checked on ALL saved columns so corruption outside nz16 is still an integrity failure.
                if u.ndim!=2 or u.shape[1]%2 or not np.all(np.isfinite(u)):raise ValueError('isometry shape/finiteness')
                if isinstance(scale,bool) or not isinstance(scale,(int,float)) or not math.isfinite(scale) or scale<=0:
                    raise ValueError('primitive scale')
                cap=u.shape[1]//2
                if np.max(np.abs(u.T@u-np.eye(2*cap)))>2e-10:raise ValueError('isometry is not orthonormal')
                if max(np.max(np.abs(u[1::2,:cap])),np.max(np.abs(u[::2,cap:])))>1e-12:raise ValueError('isometry violates field parity')
            except PERSISTED_ERRORS as exc:raise IntegrityError(f'Malformed basis artifact: {exc}') from exc
            if ax!=args.x or aw!='vacuum':raise ValueError('Basis dimension/prescription mismatch')
            if args.nz>cap:raise ValueError('Requested local count exceeds saved basis capacity')
            u=u[:,list(range(args.nz))+list(range(cap,cap+args.nz))]
            if seed is None:seed=finite_theta(teacher.get('theta'),'basis teacher')
        if checkpoint.exists():
            if not args.resume:raise ValueError('Checkpoint exists; use --resume or a fresh path')
            seed=load_checkpoint(checkpoint,request)
        if seed is None:
            rows=json.loads((ROOT/'inputs/prior_2d_points.json').read_text())
            candidates=[r for r in rows if abs(r['delta']-args.x)<1e-10]
            if candidates:seed=min(candidates,key=lambda r:abs(r['bath_cut']-args.L))['theta']
        def save_checkpoint(theta,history):
            cp={'request_digest':request,'configuration':configuration,'theta':np.asarray(theta).tolist(),
                'history':history,'phase':'Newton boundary','saved_unix':time.time()}
            cp['checkpoint_sha256']=digest(cp);atomic_json(checkpoint,cp)
            if stop['requested']:raise SafeStop('Checkpointed at a Newton boundary; rerun identical request with --resume')
        kw=dict(window=args.window,window_mode=args.window_mode,backend=args.backend,ncv=args.ncv,eig_tol=args.eig_tol,
                residual_tol=args.residual_tol,max_eig_iter=10000,checkpoint=save_checkpoint,max_bath_states=args.max_bath_states,max_basis_bytes=int(args.memory_limit_gib*1024**3/4))
        start=time.perf_counter()
        if artifact is None:s=DressedSolver(args.L,args.nz,args.osc,**kw)
        else:s=DensitySolver(args.L,u,artifact['scale'],**kw)
        s.set_delta(args.x)
        ops=[s.op]+([] if s.win is None else list(s.win.ops.values()))
        storage=sum(op.nbytes for op in ops)
        # Conservative planning heuristic, NOT a certified allocator/RSS bound.
        estimate=512*1024**2+6*storage+16*sum(op.dim for op in ops)*(max(args.ncv,24)+10)
        if estimate>args.memory_limit_gib*1024**3:
            raise MemoryError(f'Estimated {estimate/1024**3:.2f} GiB exceeds requested budget. Increase budget or explicitly choose a smaller problem; no automatic cap reduction.')
        row=s.solve(seed,tol=args.tuning_tol,maxiter=args.maxiter)
        # Stop here only if expensive work (training/diagnostics) remains; a finished
        # solve with nothing left to compute is published instead of discarded.
        if stop['requested'] and (args.train_keep or args.diagnostics!='none'):
            raise SafeStop('Stopped after scalar solve; Newton checkpoint retained')
        if args.train_keep:
            if args.basis:raise ValueError('Training takes a moving-local teacher, not an existing compressed artifact')
            u,t,meta=select_density_basis(s,row['theta'],args.train_keep)
            row['basis_artifact']={'x':args.x,'training_L':args.L,'nz_teacher':args.nz,'osc':args.osc,'keep':args.train_keep,
                                   'scale':t,'isometry':u.tolist(),'metadata':meta,'source_hash':configuration['source_sha256'],'window':args.window}
        if args.diagnostics!='none':row['diagnostics']=diagnose(s,row['theta'],k=6,second=args.diagnostics=='all')
        # A stop requested while the (uninterruptible) diagnostics ran is honoured by
        # publishing the now complete record: discarding finished work would only force
        # a full recomputation on resume. The caller sees exit 0 and stops before its next point.
        row.update(accepted=True,configuration=configuration,request_digest=request,
                   implementation='ht2d-performance-0.2.0rc1',elapsed_total_seconds=time.perf_counter()-start,
                   stop_requested_at_publication=bool(stop['requested']),
                   peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   memory_estimate_bytes=estimate,operator_storage_bytes_all=storage)
        if artifact is not None:row['basis_input']={'sha256':configuration['basis_sha256'],'artifact':artifact,'retained':args.nz}
        row['record_sha256']=digest(row);validate_record(row,request);atomic_json(args.output,row)
        print(json.dumps({k:row[k] for k in ('delta','bath_cut','Delta_thermal','tuning_residual','elapsed_total_seconds')}),flush=True)
    return 0


def main(argv=None):
    args=parser().parse_args(argv)
    try:return run(args)
    except Claimed as exc:print(str(exc),file=sys.stderr);return 73
    except SafeStop as exc:print(str(exc),file=sys.stderr);return 75
    except IntegrityError as exc:print(f'INTEGRITY: {exc}',file=sys.stderr);return 65

if __name__=='__main__':raise SystemExit(main())
