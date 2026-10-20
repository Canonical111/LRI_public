"""Shared helpers for the Expanse campaign layer (spec, steps, seeds, sacct, claims).

Nothing here changes the Hamiltonian or the numerical driver. The point driver
(code/hpc_run.py) is executed unchanged as a subprocess for every step.
"""
from __future__ import annotations
import hashlib,json,math,os,subprocess,sys,time
from pathlib import Path

RELEASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(RELEASE/'code'))
from ht2d.hpc import atomic_json,canonical_json,digest,file_hash,source_hash,validate_record  # noqa: E402

SPEC_SCHEMA='ht2d-expanse-campaign-v1'
TERMINAL={'COMPLETED','FAILED','CANCELLED','TIMEOUT','NODE_FAIL','OUT_OF_MEMORY','PREEMPTED','BOOT_FAIL','DEADLINE'}
ALIVE={'PENDING','RUNNING','REQUEUED','RESIZING','SUSPENDED','CONFIGURING','COMPLETING','STOPPED','SIGNALING','REQUEUE_HOLD','REQUEUE_FED','SPECIAL_EXIT'}
EXIT_SEED=65      # seed/predecessor refused
EXIT_MAIN=66      # a main (ladder) step failed; successors cannot run
EXIT_STAGE=74     # release/spec/environment verification failed
EXIT_CLAIMED=73   # another writer owns the chain or a point
EXIT_STOP=75      # safe stop; resumable


class SpecError(ValueError):pass


def load_json(path):return json.loads(Path(path).read_text())


def load_spec(path,expected_sha=None):
    """Load and verify a frozen campaign spec (internal digest, optional file sha256)."""
    raw=Path(path).read_bytes()
    if expected_sha is not None and hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise SpecError('Spec file sha256 differs from the submitted value')
    spec=json.loads(raw);body=dict(spec);sig=body.pop('sha256',None)
    if spec.get('schema')!=SPEC_SCHEMA or sig!=digest(body):raise SpecError('Spec schema/checksum failure')
    return spec


def chain_dir(spec,chain):return Path(spec['root'])/'chains'/chain


def step_output(spec,chain,L,nz):return chain_dir(spec,chain)/f'L{L}_z{nz}.json'


def steps(spec,chain):
    """Ordered steps of one chain: for each L the main step, then that L's checks.

    Each step: role ('main'|'check'), L, nz, argv (without --seed/--output/--resume),
    output path, seed source {'kind': 'initial'|'step', ...}.
    """
    c=spec['chains'][chain];out=[];main=c['main'];common=c['common']
    for i,L in enumerate(c['ladder']):
        if i==0:
            seed=({'kind':'step',**c['seed_from']} if c.get('seed_from') else
                  {'kind':'initial'} if c.get('initial_seed') else {'kind':'none'})
        else:
            seed={'kind':'step','chain':chain,'L':c['ladder'][i-1],'nz':main['nz']}
        out.append(dict(role='main',L=L,nz=main['nz'],argv=_argv(c,common,main,L),
                        output=str(step_output(spec,chain,L,main['nz'])),seed=seed))
        for chk in c.get('checks',[]):
            if chk['L']=='all' or L in chk['L']:
                out.append(dict(role='check',L=L,nz=chk['nz'],argv=_argv(c,common,chk,L),
                                output=str(step_output(spec,chain,L,chk['nz'])),
                                seed={'kind':'step','chain':chain,'L':L,'nz':main['nz']}))
    return out


def _argv(c,common,part,L):
    a=['--L',str(L),'--x',repr(float(c['x'])),'--nz',str(part['nz']),'--osc',str(part.get('osc',192)),
       '--backend',common['backend'],'--threads',str(common['threads']),
       '--window','vacuum','--window-mode','consistent',
       '--diagnostics',part['diagnostics'],'--memory-limit-gib',repr(float(common['memory_limit_gib'])),
       '--max-bath-states',str(c['max_bath_states'][str(L)]),
       '--eig-tol',repr(float(common['eig_tol'])),'--residual-tol',repr(float(common['residual_tol'])),
       '--tuning-tol',repr(float(common['tuning_tol'])),'--ncv',str(common['ncv']),'--maxiter',str(common['maxiter'])]
    if part.get('train_keep'):a+=['--train-keep',str(part['train_keep'])]
    if part.get('guess') is not None:a+=['--guess',*(repr(float(v)) for v in part['guess'])]
    if c.get('basis'):a+=['--basis',c['basis']['path']]
    return a


def find_step(spec,chain,L,nz):
    for s in steps(spec,chain):
        if s['L']==L and s['nz']==nz:return s
    raise SpecError(f'No step chain={chain} L={L} nz={nz} in the spec')


def seed_path(spec,chain,step):
    """Path of the seed file a step uses according to the frozen spec (no validation)."""
    kind=step['seed']['kind']
    if kind=='none':return None
    if kind=='initial':return Path(spec['chains'][chain]['initial_seed']['path'])
    ref=step['seed'];return Path(find_step(spec,ref['chain'],ref['L'],ref['nz'])['output'])


def full_argv(spec,chain,step):
    a=list(step['argv']);sp=seed_path(spec,chain,step)
    if sp is not None:a+=['--seed',str(sp)]
    return a+['--output',step['output']]


def frozen_inputs(spec,chain,step,seed_sha):
    """HT2D_FROZEN_INPUTS for a step: basis hash from the spec; seed hash = the VALIDATED value
    (frozen spec hash for initial seeds, validated predecessor bytes otherwise). Never re-hashed here (F13, F15)."""
    c=spec['chains'][chain];inp={}
    if c.get('basis') and '--basis' in step['argv']:inp[str(Path(c['basis']['path']).resolve())]=c['basis']['sha256']
    sp=seed_path(spec,chain,step)
    if sp is not None:
        if not seed_sha:raise SpecError('A validated seed hash is required')
        inp[str(sp.resolve())]=seed_sha
    return inp


def load_object(path,what):
    """Read a persisted JSON object ONCE: (bytes, sha256, dict). Read/decode/shape failures -> SpecError (IR-04)."""
    try:data=Path(path).read_bytes()
    except OSError as exc:raise SpecError(f'{what} unreadable: {exc}') from exc
    try:row=json.loads(data)
    except ValueError as exc:raise SpecError(f'{what} is not JSON: {exc}') from exc
    if not isinstance(row,dict):raise SpecError(f'{what} is not a JSON object')
    return data,hashlib.sha256(data).hexdigest(),row


def check_initial_seed(spec,chain):
    """Frozen initial seed with a declared origin (F1, F9). Returns (path, sha256 of the validated bytes).

    reference_same_L: shipped reference record (old schema allowed), bath_cut == L0.
    teacher_L0m2:     stage-T teacher record, bath_cut == L0-2, identical to the chain's basis
                      file and carrying basis_artifact.training_L == L0-2.
    """
    c=spec['chains'][chain];info=c['initial_seed'];path=Path(info['path'])
    data,sha,row=load_object(path,'Initial seed')
    if sha!=info['sha256']:raise SpecError(f'Initial seed changed: {path}')
    theta=row.get('theta')
    if not (isinstance(theta,list) and len(theta)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in theta)):
        raise SpecError('Initial seed has no finite two-component theta')
    d=row.get('delta')
    if not isinstance(d,(int,float)) or isinstance(d,bool) or not math.isfinite(d) or abs(float(d)-float(c['x']))>1e-12:
        raise SpecError('Initial seed belongs to another x (or has a non-finite delta)')
    L0=c['ladder'][0];origin=info.get('origin')
    if origin=='reference_same_L':
        if row.get('bath_cut')!=L0:raise SpecError(f'Reference seed bath_cut {row.get("bath_cut")} != L0={L0}')
    elif origin=='teacher_L0m2':
        if row.get('bath_cut')!=L0-2:raise SpecError(f'Teacher seed bath_cut {row.get("bath_cut")} != L0-2={L0-2}')
        if not c.get('basis') or c['basis']['sha256']!=sha:raise SpecError('Teacher seed is not the chain basis file')
        art=row.get('basis_artifact')
        if not isinstance(art,dict) or art.get('training_L')!=L0-2:raise SpecError('Teacher seed lacks a matching basis_artifact')
    else:raise SpecError(f'Unknown initial-seed origin {origin!r}')
    return path,sha


class EnvUnavailable(RuntimeError):
    """The frozen validation environment/release is not usable here (distinct from an invalid record)."""


def require_frozen_env(spec,run=subprocess.run):
    """Exact validation must run with the frozen env and the verified release (F20)."""
    if source_hash()!=spec['release']['source_sha256']:
        raise EnvUnavailable('This release tree is not the frozen release (source_sha256 differs)')
    py=spec['env']['python']
    try:p=run([py,'-E','-s',str(RELEASE/'cluster/expanse/envcheck.py'),'--expect',spec['env']['env_id']],capture_output=True,text=True)
    except OSError as exc:raise EnvUnavailable(f'Frozen interpreter {py} not runnable: {exc}') from exc
    if p.returncode!=0:raise EnvUnavailable(f'Frozen environment {spec["env"]["env_id"]} unavailable: {p.stderr.strip()}')
    return py


def check_receipt(spec):
    """The frozen receipt must be unchanged, passed, and cover this release and environment (IR-03)."""
    r=spec['receipt']
    data,sha,rec=load_object(r['path'],'Receipt')
    if sha!=r['sha256']:raise SpecError('Receipt changed since the spec was frozen')
    if not (rec.get('passed') is True and rec.get('tar_sha256')==spec['release']['tar_sha256']
            and rec.get('manifest_sha256')==spec['release']['manifest_sha256']
            and rec.get('source_sha256')==spec['release']['source_sha256'] and rec.get('env_id')==spec['env']['env_id']):
        raise SpecError('Receipt does not cover this release (tar, manifest, source) and environment')


def verify_release_tree(spec):
    """The EXECUTING tree must be the frozen release: its own files hash to the frozen manifest, which
    itself hashes to the spec value (IR2-02: covers cluster/expanse, not only the numerical source)."""
    rel=spec['release']
    try:data=Path(rel['manifest']).read_bytes()
    except OSError as exc:raise EnvUnavailable(f'Release manifest unreadable: {exc}') from exc
    if hashlib.sha256(data).hexdigest()!=rel['manifest_sha256']:raise EnvUnavailable('Release manifest changed')
    checked=0
    for line in data.decode().splitlines():
        h,_,name=line.partition('  ')
        if not name.startswith('ht2d/'):raise EnvUnavailable(f'Unexpected manifest entry {name!r}')
        if name.startswith(('ht2d/code/','ht2d/cluster/','ht2d/inputs/')):
            try:got=hashlib.sha256((RELEASE/name[len('ht2d/'):]).read_bytes()).hexdigest()
            except OSError as exc:raise EnvUnavailable(f'Release file missing: {name}') from exc
            if got!=h:raise EnvUnavailable(f'Executing release differs from the frozen manifest: {name}')
            checked+=1
    if not checked:raise EnvUnavailable('Release manifest lists no executable files')
    return checked


def verify_runtime(spec):
    """Every entry point (chain, continuation, submit, status, collect) runs only on the frozen release
    tree (manifest-verified), with the frozen interpreter/environment, under a passing receipt."""
    check_receipt(spec)
    verify_release_tree(spec)
    return require_frozen_env(spec)


def exact_request_valid(spec,chain,step,seed_sha,output_sha=None,run=subprocess.run):
    """Validate a record against the COMPLETE frozen request (F15) with the driver's own --check-only,
    run by the FROZEN interpreter (F20), with input hashes from validated dependencies only."""
    c=spec['chains'][chain]
    env={**os.environ,'HT2D_FROZEN_SOURCE':spec['release']['source_sha256'],
         'HT2D_FROZEN_INPUTS':json.dumps(frozen_inputs(spec,chain,step,seed_sha),sort_keys=True),
         'NUMBA_NUM_THREADS':str(c['common']['threads']),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
         'HT2D_EXPECT_OUTPUT_SHA256':output_sha or ''}     # the child validates exactly our snapshot (IR-01)
    p=run([spec['env']['python'],'-E','-s',str(RELEASE/'code/hpc_run.py'),*full_argv(spec,chain,step),'--check-only'],
          env=env,capture_output=True,text=True)
    return p.returncode==0 and 'VALID' in p.stdout,p.stderr.strip().splitlines()[-1:] if p.returncode else []


def validate_step(spec,chain,L,nz,cache=None,exact=True):
    """Validate the record of a frozen step and, recursively, its seed lineage (F15).

    Returns (path, sha256 of the validated bytes). The seed hash used for the exact request is the
    frozen initial-seed hash or the hash returned by validating the predecessor step itself."""
    key=(chain,int(L),int(nz))
    if cache is not None and key in cache:return cache[key]
    step=find_step(spec,chain,L,nz);path=Path(step['output'])
    if not path.exists():raise SpecError(f'Record missing: {path}')
    data,sha,row=load_object(path,f'Record {path}')
    if not isinstance(row.get('request_digest'),str) or not isinstance(row.get('configuration'),dict):
        raise SpecError('Record is not an accepted-record envelope')
    try:validate_record(row,row['request_digest'])
    except (ValueError,KeyError,TypeError,AttributeError) as exc:raise SpecError(f'Record {path} invalid: {exc}') from exc
    cfg=row['configuration'];c=spec['chains'][chain];common=c['common']
    want={'L':int(L),'x':float(c['x']),'nz':int(nz),'backend':common['backend'],'window':'vacuum',
          'window_mode':'consistent','source_sha256':spec['release']['source_sha256']}
    for k,v in want.items():
        if cfg.get(k)!=v:raise SpecError(f'Record {path} has {k}={cfg.get(k)!r}, expected {v!r}')
    want_basis=c['basis']['sha256'] if (c.get('basis') and '--basis' in step['argv']) else None   # from the step's args
    if cfg.get('basis_sha256')!=want_basis:raise SpecError('Record used another basis (or none was expected)')
    if row.get('bath_cut')!=int(L) or row.get('nz_per_parity')!=int(nz):raise SpecError('Record identity mismatch')
    if exact:
        kind=step['seed']['kind'];seed_sha=None
        if kind=='initial':seed_sha=check_initial_seed(spec,chain)[1]
        elif kind=='step':
            ref=step['seed'];seed_sha=validate_step(spec,ref['chain'],ref['L'],ref['nz'],cache,exact)[1]
        if cfg.get('seed_sha256')!=seed_sha:raise SpecError(f'Record {path} was seeded from other bytes than its validated lineage')
        ok,why=exact_request_valid(spec,chain,step,seed_sha,output_sha=sha)
        if not ok:raise SpecError(f'Record {path} is not the exact frozen request: {why}')
    if cache is not None:cache[key]=(path,sha)
    return path,sha


def check_predecessor(spec,ref,exact=True,cache=None):
    """A production predecessor must be the accepted record of EXACTLY the frozen step, with a
    validated lineage. Returns (path, sha256 of the validated bytes)."""
    return validate_step(spec,ref['chain'],ref['L'],ref['nz'],cache,exact)


def sacct_state(jobid,tries=5,pause=30,run=subprocess.run):
    """Terminal/alive state of a job, or None (UNKNOWN) after bounded retries. Never guesses."""
    for k in range(tries):
        try:
            p=run(['sacct','-j',str(jobid),'-X','-n','-P','-o','State'],capture_output=True,text=True,timeout=60)
            if p.returncode==0:
                lines=[l.strip() for l in p.stdout.splitlines() if l.strip()]
                if lines:return lines[0].split()[0]
        except (OSError,subprocess.TimeoutExpired):pass
        if k<tries-1:time.sleep(pause)
    return None


def claims_under(scope):
    """Active claim directories (archived ones under claims_archive/ are excluded)."""
    scope=Path(scope)
    return sorted(p for p in scope.rglob('*.claim') if p.is_dir() and 'claims_archive' not in p.relative_to(scope).parts)
