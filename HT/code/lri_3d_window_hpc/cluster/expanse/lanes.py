"""Lane runner: cutoff continuation inside one Slurm array task (one lane = one x).

A frozen lane manifest (schema ht3d-lanes-v1, written by campaign.py freeze) lists
ordered steps. Each step is one ordinary one-writer point (code/hpc_run.py) run as a
child process with --resume, so an existing valid output is reused by the driver's
own checks. A step may take --seed and/or --basis from an earlier step's output:

* After a child returns 0 its output is read ONCE into a byte snapshot, which is
  checked (checksum, acceptance, numerical gates, and request digest recomputed
  independently from the frozen argv). Only that snapshot's sha256 is handed on.
* Consumers receive the hashes in HT3D_FROZEN_INPUTS; the point driver re-hashes
  the bytes it actually reads, so a file changed in between fails closed.
* The interpreter's runtime identity must equal the one the manifest copied from a
  passing Expanse validation receipt.

Stops (USR1/TERM/INT): children (cluster/expanse/child.py wrapping the unmodified
ht3d.hpc.main) start with SIGUSR1 ignored, record a stop that arrives before the
driver's handler exists and hand it over when that handler is installed, and ignore
stop signals again after the driver returns; there is no window in which a stop
signal has its default (killing) action. While a stop is pending the runner re-sends
SIGUSR1 every few seconds (covering the brief inherited-SIG_IGN startup window), and
it never starts a step after a stop. Exit codes: 0 lane complete; 75 safe stop; 73 a step
output is claimed by another writer; 74 manifest/release/runtime mismatch; other
codes are step failures, recorded under <campaign>/lane_failures/.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,signal,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'code'))
from ht3d.hpc import atomic_json,digest,parser,source_hash,validate_record  # noqa: E402

SCHEMA='ht3d-lanes-v1'
CHAIN_FLAGS=('--seed','--basis','--output','--resume')
STOP_SIGNALS=(signal.SIGUSR1,signal.SIGTERM,signal.SIGINT)


class Refused(ValueError):
    """Manifest, release, runtime or input binding failure (exit 74)."""


def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
    return h.hexdigest()


def release_fingerprint(root=ROOT):
    """sha256 of RELEASE.sha256, after verifying every file it lists (fails closed)."""
    listing=Path(root)/'RELEASE.sha256'
    if not listing.is_file():raise Refused('RELEASE.sha256 missing: not an installed release')
    for line in listing.read_text().splitlines():
        expected,name=line.split('  ',1)
        p=Path(root)/name
        if not p.is_file() or file_hash(p)!=expected:raise Refused(f'Release file missing or changed: {name}')
    return file_hash(listing)


RUNTIME_MODULES=('numpy','scipy','scipy.linalg','scipy.sparse','scipy.sparse.linalg','numba','llvmlite','threadpoolctl')


def runtime_identity():
    """Interpreter, dependency and BLAS identity (no paths or thread counts).

    threadpoolctl reports the native libraries LOADED so far, and SciPy loads its BLAS
    consumers lazily; the full numerical backend set the driver uses is therefore imported
    first, so the identity is the same whenever it is computed (receipt, freeze, runner)."""
    import importlib
    for name in RUNTIME_MODULES:importlib.import_module(name)
    import numpy,scipy,numba,llvmlite,threadpoolctl
    from importlib.metadata import version
    blas=[]
    for lib in threadpoolctl.threadpool_info():
        blas.append({k:lib.get(k) for k in ('user_api','internal_api','prefix','version','threading_layer','architecture')})
    blas.sort(key=lambda d:json.dumps(d,sort_keys=True))
    from ht3d.operators import SPARSE_PARALLEL_MIN_WORK       # env-settable; changes request digests (IR08)
    return {'python':platform.python_version(),'implementation':platform.python_implementation(),
            'sparse_parallel_min_work':SPARSE_PARALLEL_MIN_WORK,
            'machine':platform.machine(),'numpy':numpy.__version__,'scipy':scipy.__version__,
            'numba':numba.__version__,'llvmlite':llvmlite.__version__,'threadpoolctl':version('threadpoolctl'),
            'blas':blas}


def expected_request(argv,input_bytes):
    """Recompute ht3d.hpc.run's request digest for a frozen argv (mirrors hpc.run exactly).

    input_bytes maps 'seed'/'basis' to the bytes the consumer will read.
    """
    import numpy as np,scipy,numba
    from ht3d.operators import SPARSE_PARALLEL_MIN_WORK
    args=parser().parse_args(argv)
    configuration={k:str(v.resolve()) if isinstance(v,Path) else v for k,v in vars(args).items()
                   if k not in ('resume','check_only','output')}
    for key in ('basis','seed'):
        if getattr(args,key):configuration[key+'_sha256']=hashlib.sha256(input_bytes[key]).hexdigest()
    configuration['source_sha256']=source_hash()
    configuration['sparse_parallel_min_work']=SPARSE_PARALLEL_MIN_WORK
    configuration['runtime']={'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
                              'numba':numba.__version__,'machine':platform.machine()}
    return digest(configuration)


def load_manifest(path):
    m=json.loads(Path(path).read_text());sig=m.pop('sha256',None)
    if sig!=digest(m) or m.get('schema')!=SCHEMA:raise Refused('Lane manifest checksum/schema failure')
    return m


def check_effective_inputs(step,argv,frozen):
    """The parsed argv's seed/basis must be exactly the frozen inputs, by resolved path (R20)."""
    a=parser().parse_args(argv)
    used={str(Path(getattr(a,k)).resolve()) for k in ('seed','basis') if getattr(a,k) is not None}
    if used!={str(Path(p).resolve()) for p in frozen}:
        raise Refused(f'Step {step["name"]}: effective seed/basis {sorted(used)} differ from frozen inputs {sorted(frozen)}')


def resolve_inputs(step,produced):
    """Seed/basis for one step, by role: chained (`<role>_from` = step index whose validated
    snapshot is in `produced`) or external (`<role>_external` = {path, sha256} frozen at
    freeze time, read once here and checked). Returns (inputs, frozen-hash map)."""
    inputs={};frozen={}
    for key in ('seed','basis'):
        j=step.get(key+'_from');ext=step.get(key+'_external')
        if j is not None and ext is not None:raise Refused(f'Step {step["name"]}: {key} is both chained and external')
        if j is not None:
            if j not in produced:raise Refused(f'Step {step["name"]}: predecessor {j} not completed')
            path,sha,data=produced[j]
        elif ext is not None:
            path=ext['path'];data=Path(path).read_bytes();sha=hashlib.sha256(data).hexdigest()
            if sha!=ext['sha256']:raise Refused(f'Step {step["name"]}: external {key} changed: {path}')
        else:continue
        inputs[key]=data;inputs[key+'_path']=path;frozen[path]=sha
    return inputs,frozen


def validate_output(step,inputs):
    """Read a step output once and validate it fully against the frozen argv and inputs.
    Returns (path, sha256 of the validated bytes, bytes); raises Refused otherwise."""
    path=step['output']
    data=Path(path).read_bytes()
    try:row=json.loads(data)
    except ValueError as exc:raise Refused(f'Step {step["name"]}: output is not JSON') from exc
    if not isinstance(row,dict):raise Refused(f'Step {step["name"]}: output failed validation: not a JSON object')
    want=expected_request(Runner.step_argv(step,inputs),inputs)
    try:validate_record(row,want)
    except (ValueError,KeyError,TypeError,AttributeError,IndexError) as exc:
        raise Refused(f'Step {step["name"]}: output failed validation: {type(exc).__name__}: {exc}') from exc
    return path,hashlib.sha256(data).hexdigest(),data


def validated_snapshots(lane,upto=None):
    """Validated byte snapshots {step index: (path, sha256, bytes)} for a COMPLETE prefix of a
    lane, in chain order (the runner's own checks). Raises Refused if any needed step is
    missing or invalid. Used to freeze continuation campaigns from validated records only."""
    produced={}
    for k,step in enumerate(lane['steps']):
        if upto is not None and k>upto:break
        if not Path(step['output']).exists():raise Refused(f'Step {step["name"]}: output missing')
        inputs,_=resolve_inputs(step,produced)
        produced[k]=validate_output(step,inputs)
    return produced


def lane_states(lane):
    """Per-step 'done' | 'invalid: <why>' | 'claimed' | 'checkpoint' | 'pending' | 'blocked',
    with the same full validation the runner applies (status/resubmit decisions)."""
    produced={};out=[]
    for k,step in enumerate(lane['steps']):
        p=Path(step['output'])
        if p.exists():
            try:
                inputs,_=resolve_inputs(step,produced)
                produced[k]=validate_output(step,inputs);out.append('done');continue
            except (Refused,OSError,ValueError) as exc:out.append(f'invalid: {exc}');continue
        if Path(str(p)+'.claim').exists():out.append('claimed')
        elif Path(str(p)+'.checkpoint.json').exists():out.append('checkpoint')
        else:out.append('pending')
    return out


def _ignore_stops():
    """preexec_fn: the child starts with every stop signal ignored (child.py then records them)."""
    for sig in STOP_SIGNALS:signal.signal(sig,signal.SIG_IGN)


class Runner:
    def __init__(self,manifest_path,lane,child=None,release_check=True,forward_interval=10.0,log=print):
        self.stop=False;self.child=None
        for sig in STOP_SIGNALS:signal.signal(sig,self.on_signal)      # before any loading (R23)
        self.path=Path(manifest_path).resolve();self.m=load_manifest(self.path)
        if not 0<=lane<len(self.m['lanes']):raise Refused('Lane index outside the frozen manifest')
        self.lane=self.m['lanes'][lane];self.index=lane;self.log=log
        self.child_cmd=list(child) if child else [sys.executable,str(HERE/'child.py')]
        self.release_check=release_check;self.forward_interval=forward_interval
        self.campaign=self.path.parent
        self.journal=self.campaign/'journal'/f'lane_{lane:03d}.jsonl'

    # -- bookkeeping -------------------------------------------------------
    def note(self,**event):
        event.update(time=time.time(),lane=self.index,job=os.environ.get('SLURM_JOB_ID'),
                     task=os.environ.get('SLURM_ARRAY_TASK_ID'))
        self.journal.parent.mkdir(parents=True,exist_ok=True)
        with open(self.journal,'a') as f:f.write(json.dumps(event,sort_keys=True)+'\n')
        self.log(json.dumps(event,sort_keys=True),flush=True)

    def on_signal(self,signum,frame):
        self.stop=True;self.forward()

    def forward(self):
        c=self.child
        if c is not None and c.poll() is None:
            try:c.send_signal(signal.SIGUSR1)
            except ProcessLookupError:pass

    # -- checks ------------------------------------------------------------
    def retire_failure(self,k):
        """A recorded failure of step k is history once step k has a validated output (IR03)."""
        f=self.campaign/'lane_failures'/f'lane_{self.index:03d}.json'
        try:rec=json.loads(f.read_text()) if f.exists() else None
        except (OSError,ValueError):return
        if isinstance(rec,dict) and rec.get('step')==k:
            dest=self.campaign/'lane_failures'/'retired'/f'lane_{self.index:03d}.{int(time.time())}.{os.getpid()}.json'
            dest.parent.mkdir(parents=True,exist_ok=True);f.rename(dest);self.note(event='failure_retired',step=k,to=str(dest))

    def check_bindings(self):
        name=os.environ.get('SLURM_JOB_NAME')
        if os.environ.get('SLURM_JOB_ID') and name:
            # Inside Slurm the job must be one this campaign journaled before sbatch (IR07):
            # a stale HT3D_MANIFEST cannot run campaign A under campaign B's submission.
            j=self.campaign/'SUBMITTED.jsonl'
            names={json.loads(l).get('name') for l in j.read_text().splitlines() if l.strip()} if j.exists() else set()
            if name not in names:raise Refused(f'Slurm job name {name!r} is not journaled for campaign {self.campaign}')
        if self.m['source_sha256']!=source_hash():raise Refused('Numerical source differs from the frozen manifest')
        if self.release_check and self.m['release_sha256']!=release_fingerprint():
            raise Refused('Release differs from the frozen manifest')
        rt=runtime_identity()
        if rt!=self.m['runtime']:
            raise Refused('Runtime differs from the validated receipt: '+json.dumps({'now':rt,'frozen':self.m['runtime']},sort_keys=True))

    def snapshot(self,k,inputs):
        """Read step k's output once, validate it fully, return (path, sha of those bytes, bytes)."""
        return validate_output(self.lane['steps'][k],inputs)

    @staticmethod
    def step_argv(step,inputs_by_flag):
        argv=list(step['argv'])
        for key,flag in (('seed','--seed'),('basis','--basis')):
            if key in inputs_by_flag:argv+=[flag,inputs_by_flag[key+'_path']]
        return argv+['--output',step['output'],'--resume']

    # -- main loop -----------------------------------------------------------
    def run(self):
        self.check_bindings()
        produced={}   # step index -> (path, sha256, bytes)
        for k,step in enumerate(self.lane['steps']):
            if self.stop:self.note(event='stop_between_steps',step=k);return 75
            inputs,frozen=resolve_inputs(step,produced)
            argv=self.step_argv(step,inputs)
            check_effective_inputs(step,argv,frozen)
            env=dict(os.environ,HT3D_FROZEN_SOURCE=self.m['source_sha256'],HT3D_FROZEN_INPUTS=json.dumps(frozen,sort_keys=True),
                     NUMBA_NUM_THREADS=str(max(int(os.environ.get('NUMBA_NUM_THREADS','1')),int(step['threads']))))
            self.note(event='step_start',step=k,name=step['name'],output=step['output'])
            if self.stop:self.note(event='stop_before_launch',step=k);return 75     # recheck after preparation (IR10)
            t=time.perf_counter()
            self.child=subprocess.Popen([*self.child_cmd,*argv],env=env,
                                        preexec_fn=_ignore_stops)
            if self.stop:self.forward()
            while True:
                try:rc=self.child.wait(timeout=self.forward_interval);break
                except subprocess.TimeoutExpired:
                    if self.stop:self.forward()
            self.child=None
            self.note(event='step_end',step=k,name=step['name'],rc=rc,seconds=time.perf_counter()-t)
            if rc==75:return 75
            if rc==73:return 73
            if rc!=0:
                atomic_json(self.campaign/'lane_failures'/f'lane_{self.index:03d}.json',
                            {'lane':self.index,'step':k,'name':step['name'],'rc':rc,'time':time.time(),
                             'job':os.environ.get('SLURM_JOB_ID'),'task':os.environ.get('SLURM_ARRAY_TASK_ID')})
                return rc
            produced[k]=self.snapshot(k,inputs)
            self.retire_failure(k)
            if self.stop and k+1<len(self.lane['steps']):self.note(event='stop_between_steps',step=k+1);return 75
        self.note(event='lane_complete')
        return 0


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='cmd',required=True)
    r=sub.add_parser('run');r.add_argument('--manifest',required=True);r.add_argument('--lane',type=int)
    sub.add_parser('runtime',help='print this interpreter runtime identity as JSON')
    a=p.parse_args(argv)
    if a.cmd=='runtime':print(json.dumps(runtime_identity(),sort_keys=True));return 0
    lane=a.lane if a.lane is not None else int(os.environ['SLURM_ARRAY_TASK_ID'])
    try:return Runner(a.manifest,lane).run()
    except Refused as exc:print(f'lane refused: {exc}',file=sys.stderr);return 74
    finally:
        # CPython resets Python handlers to SIG_DFL at shutdown; a stop re-forwarded by the
        # batch shell then must not kill the finished runner (R23).
        for sig in STOP_SIGNALS:signal.signal(sig,signal.SIG_IGN)

if __name__=='__main__':raise SystemExit(main())
