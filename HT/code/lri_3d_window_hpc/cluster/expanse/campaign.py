"""Expanse campaign tool for ht3d lanes (login node, inside the release venv). Subcommands:

  freeze    --spec SPEC.json --receipt RECEIPT.json --release-tar TAR --release-tar-sha256 SHA --out DIR
  submit    DIR [--lanes I ...] [--throttle N] [--dry-run]
  status    DIR [--json]
  recover   DIR [--dry-run]
  resubmit  DIR [--throttle N] [--include-failed] [--dry-run]

freeze writes DIR/manifest.json (schema ht3d-lanes-v1); it never overwrites, and every
output path must stay inside DIR/results. submit, recover and resubmit run under the
campaign admin lock DIR/.admin.lock (atomic mkdir, never broken automatically).

Submissions: an intent with a unique Slurm job name is journaled (fsync) BEFORE sbatch;
liveness is then decided by job NAME through squeue, so an accepted job whose id was
never journaled still blocks duplicates. recover only tombstones an output claim whose
owner job is confirmed terminal by sacct AND absent from squeue, rechecking the owner
token and directory identity immediately before the rename. Completion and validity use
the runner's full validation (lanes.lane_states). Nothing resubmits on its own.
"""
from __future__ import annotations
import argparse,contextlib,datetime as dt,getpass,json,os,re,shlex,socket,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(HERE))
from ht3d.hpc import atomic_json,digest,parser,source_hash  # noqa: E402
import lanes  # noqa: E402

TERMINAL={'COMPLETED','FAILED','TIMEOUT','CANCELLED','NODE_FAIL','OUT_OF_MEMORY','PREEMPTED','BOOT_FAIL','DEADLINE'}
# Expanse accounting (verified 2026-10-07: `scontrol show partition shared` -> TRESBillingWeights=cpu=3600,
# mem=1800.00G with PriorityFlags=MAX_TRES; jobs 54739260 (8 cpu, 32G) -> billing=57600 and 54739261 (1 cpu, 128G)
# -> billing=230400). Hence SU per hour = billing/3600 = max(cpus, mem_GB/2).
BILLING_PER_SU_HOUR=3600.0
CORE_MB=2048.0                # memory equivalent of one core in the shared estimate (2 GB)
# large-shared (verified 2026-10-08: TRESBillingWeights=cpu=14400,mem=900.00G, MAX_TRES):
# SU per hour = max(4*cpus, mem_GB/4).
MAX_MEM_GIB={'shared':243,'compute':240,'debug':240,'large-shared':2000}


def su_per_hour(partition,cpus,mem_mb):
    """Estimated SU/h for one allocation (the measured value is billing/3600)."""
    if partition=='compute':return 128.0
    if partition=='large-shared':return max(4.0*cpus,(mem_mb or 0)/1024/4)
    return max(float(cpus),(mem_mb or 0)/CORE_MB)
SBATCH_SCRIPT=HERE/'lane.sbatch'
RESOURCE_KEYS=('partition','cpus','mem_gib','wall','lead_s')
NAME_RE=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}')
PER_L_KEYS={'nz','diagnostics','max_bath_states','memory_limit_gib','extra_argv'}
WINDOW_KEYS=PER_L_KEYS
TEACHER_KEYS={'L','nz','osc','keep','diagnostics','max_bath_states','memory_limit_gib','extra_argv'}
RUNNER_OWNED=('seed','basis','output','resume','check_only')


class LockHeld(RuntimeError):pass


def utc():return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def simple_name(s,what):
    if not isinstance(s,str) or not NAME_RE.fullmatch(s) or '..' in s:
        raise ValueError(f'{what} {s!r}: use letters, digits, _ . - (a single path component)')
    return s


# ---------------------------------------------------------------- admin lock
@contextlib.contextmanager
def admin_lock(campaign):
    lock=Path(campaign)/'.admin.lock'
    try:lock.mkdir()
    except FileExistsError as exc:
        owner=(lock/'owner.json').read_text() if (lock/'owner.json').exists() else '(no owner file)'
        raise LockHeld(f'Campaign admin lock held: {lock} owner {owner}. Remove it by hand only after confirming that process is gone.') from exc
    token=os.urandom(16).hex()
    try:
        atomic_json(lock/'owner.json',{'token':token,'host':socket.gethostname(),'pid':os.getpid(),
                                       'user':getpass.getuser(),'time':utc()})
        yield
    finally:
        with contextlib.suppress(FileNotFoundError,ValueError):
            if json.loads((lock/'owner.json').read_text()).get('token')==token:
                (lock/'owner.json').unlink();lock.rmdir()


# ---------------------------------------------------------------- slurm queries
def run_query(cmd,retries=3,pause=5.0):
    """Return stdout, or None when every attempt failed (UNKNOWN). Runs with TZ=UTC so that
    sacct/squeue time arguments and outputs are UTC like everything we journal (R24)."""
    for i in range(retries):
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=120,env=dict(os.environ,TZ='UTC'))
            if p.returncode==0:return p.stdout
        except (OSError,subprocess.TimeoutExpired):pass
        if i+1<retries:time.sleep(pause)
    return None


def squeue_rows(selector,retries=3,pause=5.0):
    """Rows '%i|%j|%A|%K' of NON-terminal jobs squeue lists for `selector` (['-j', id] or
    ['-n', name,...]). All states are requested explicitly (`-t all`, overriding any inherited
    filter, so SUSPENDED/STOPPED/REQUEUED/... jobs count as live, IR02); terminal ones are
    dropped. [] when nothing live is listed (squeue's 'Invalid job id' for departed ids is a
    positive 'not listed'); None when the query failed (UNKNOWN)."""
    for i in range(retries):
        try:
            p=subprocess.run(['squeue','-h','-r','-t','all',*selector,'-o','%i|%j|%A|%K|%T'],capture_output=True,text=True,timeout=120,
                             env={k:v for k,v in dict(os.environ,TZ='UTC').items() if not k.startswith('SQUEUE_')})
            if p.returncode==0:
                return ['|'.join(ln.split('|')[:4]) for ln in p.stdout.splitlines()
                        if ln.strip() and ln.split('|')[-1].strip() not in TERMINAL]
            if 'Invalid job id' in (p.stderr+p.stdout):return []
        except (OSError,subprocess.TimeoutExpired):pass
        if i+1<retries:time.sleep(pause)
    return None


def job_state(job_id,retries=3,pause=5.0):
    """('TERMINAL'|'LIVE'|'UNKNOWN', detail) for one INDIVIDUAL job id (exact JobIDRaw match)."""
    if not re.fullmatch(r'\d+',str(job_id or '')):return 'UNKNOWN',f'no individual job id ({job_id!r})'
    listed=squeue_rows(['-j',str(job_id)],retries,pause)
    if listed is None:return 'UNKNOWN','squeue failed'
    if listed:return 'LIVE','listed by squeue'
    s=run_query(['sacct','-X','-n','-P','-j',str(job_id),'-o','JobIDRaw,State'],retries,pause)
    if s is None:return 'UNKNOWN','sacct query failed'
    states=[ln.split('|')[1].split()[0] for ln in s.splitlines() if ln.split('|')[0]==str(job_id)]
    if len(states)!=1:return 'UNKNOWN',f'sacct returned {len(states)} exact records'
    state=states[0].rstrip('+')
    if state not in TERMINAL:return 'LIVE',f'sacct state {state}'
    listed=squeue_rows(['-j',str(job_id)],retries,pause)     # positive absence after the terminal record
    if listed is None:return 'UNKNOWN','squeue failed after sacct'
    if listed:return 'LIVE','listed by squeue after sacct'
    return 'TERMINAL',state


# ---------------------------------------------------------------- spec -> manifest
def _fmt(x):return repr(float(x))


def continuation_inputs(cont,x):
    """Validated teacher/seed snapshots for x from an earlier FROZEN campaign (R21): the earlier
    lane is re-validated in chain order (checksums, gates, recomputed request digests), and
    the external references carry the hashes of exactly those validated bytes."""
    src=Path(cont['campaign_dir']).resolve();old=lanes.load_manifest(src/'manifest.json')
    if old['runtime']!=lanes.runtime_identity():raise ValueError('continue_from campaign ran under a different runtime')
    if old['source_sha256']!=source_hash():raise ValueError('continue_from campaign used a different numerical source')
    group=simple_name(cont['group'],'continue_from group')
    cand=[ln for ln in old['lanes'] if ln['group']==group and abs(ln['x']-float(x))<1e-15]
    if len(cand)!=1:raise ValueError(f'continue_from: {len(cand)} lanes for group {group} x={x}')
    lane=cand[0];names=[s['name'] for s in lane['steps']]
    want={}
    for role in ('teacher','seed'):
        name=simple_name(cont[role],f'continue_from {role} step')
        if name not in names:raise ValueError(f'continue_from: no step {name} in that lane')
        want[role]=names.index(name)
    try:snaps=lanes.validated_snapshots(lane,upto=max(want.values()))
    except lanes.Refused as exc:raise ValueError(f'continue_from x={x}: {exc}') from exc
    ref=lambda k:{'path':snaps[k][0],'sha256':snaps[k][1]}
    return {'basis_external':ref(want['teacher'])},{'seed_external':ref(want['seed'])}


def check_group(g):
    """Resources must be concrete (templates with FILL_* placeholders are refused)."""
    ok=(isinstance(g.get('cpus'),int) and 1<=g['cpus']<=128 and isinstance(g.get('mem_gib'),int) and not isinstance(g['mem_gib'],bool)
        and g.get('partition') in MAX_MEM_GIB and 1<=g['mem_gib']<=MAX_MEM_GIB[g['partition']]
        and isinstance(g.get('lead_s'),int) and g['lead_s']>0
        and isinstance(g.get('wall'),str) and re.fullmatch(r'(\d+-)?\d{1,2}:\d{2}:\d{2}',g['wall']))
    if not ok:raise ValueError(f'group {g.get("name")}: resources must be concrete (cpus 1..128, integer mem_gib up to the partition limit {MAX_MEM_GIB}, wall [D-]HH:MM:SS, lead_s, partition): {g}')
    guard_cap(g)


def guard_cap(g):
    """Largest --memory-limit-gib a step of this group may carry. Default: the allocation (mem_gib).
    The driver's guard is a planning heuristic (hpc.py), not an RSS bound; when it is known to overstate
    the measured peak, a group may opt in to a higher guard with guard_cap_gib plus a written guard_cap_reason
    (e.g. L20 scalar-only: guard 258 GiB, measured RSS far below the 240G allocation)."""
    cap=g.get('guard_cap_gib')
    if cap is None:return float(g['mem_gib'])
    if isinstance(cap,bool) or not isinstance(cap,(int,float)) or not cap>g['mem_gib']:
        raise ValueError(f'group {g.get("name")}: guard_cap_gib must be a number above mem_gib {g["mem_gib"]}, got {cap!r}')
    if not isinstance(g.get('guard_cap_reason'),str) or not g['guard_cap_reason'].strip():
        raise ValueError(f'group {g.get("name")}: guard_cap_gib requires a non-empty guard_cap_reason')
    return float(cap)


def build_lanes(spec,out_dir):
    """Expand a spec into lanes. Validates names, per-cutoff overrides and output containment."""
    out=Path(out_dir).resolve();results=(out/'results').resolve();lanes_=[]
    window=spec['window'];per_L={}
    bad=set(window)-WINDOW_KEYS
    if bad:raise ValueError(f'window: unsupported keys {sorted(bad)} (allowed {sorted(WINDOW_KEYS)})')
    if spec.get('teacher') is not None and set(spec['teacher'])-TEACHER_KEYS:
        raise ValueError(f'teacher: unsupported keys {sorted(set(spec["teacher"])-TEACHER_KEYS)}')
    for k,v in spec.get('per_L',{}).items():
        bad=set(v)-PER_L_KEYS
        if bad:raise ValueError(f'per_L[{k}]: unsupported keys {sorted(bad)} (allowed {sorted(PER_L_KEYS)})')
        per_L[int(k)]=v
    common=['--window','vacuum','--window-mode','consistent','--backend',spec.get('backend','tensor')]
    if spec.get('cache_dir') and not Path(spec['cache_dir']).is_absolute():raise ValueError('cache_dir must be an absolute path')
    cache=['--cache-dir',str(Path(spec['cache_dir']).resolve())] if spec.get('cache_dir') else []
    cont=spec.get('continue_from')
    teacher=spec.get('teacher')
    if (teacher is None)==(cont is None):raise ValueError('give exactly one of "teacher" or "continue_from"')
    for k,v in per_L.items():
        for key in ('max_bath_states','memory_limit_gib','nz'):
            if key in v and (isinstance(v[key],bool) or not isinstance(v[key],(int,float)) or v[key]<=0):
                raise ValueError(f'per_L[{k}].{key} must be a positive number, got {v[key]!r}')
    for g in spec['groups']:
        simple_name(g['name'],'group name');check_group(g)
        res={k:g[k] for k in RESOURCE_KEYS}
        threads=int(g.get('threads',g['cpus']))
        if threads>int(g['cpus']) or threads<1:raise ValueError(f'group {g["name"]}: threads must be 1..cpus')
        for x in g.get('x',spec['x']):
            xs=_fmt(x);base=results/g['name']/f'x{xs}'
            def limits(L,d):
                mem=float(d.get('memory_limit_gib',g['mem_gib']*0.9))
                if mem>guard_cap(g):raise ValueError(f'L{L}: memory_limit_gib {mem} above the lane allocation {g["mem_gib"]}G (guard cap {guard_cap(g)})')
                return ['--memory-limit-gib',repr(mem),'--max-bath-states',str(int(d.get('max_bath_states',2_000_000)))]
            def wargv(L):
                d={**window,**per_L.get(L,{})}                     # window defaults, then per-cutoff (R19)
                return ['--L',str(L),'--x',xs,'--nz',str(d['nz']),*common,'--diagnostics',d.get('diagnostics','first'),
                        '--threads',str(threads),*limits(L,d),*d.get('extra_argv',[])]
            steps=[]
            if teacher is not None:
                tL=int(teacher['L'])
                steps.append({'name':f'teacher_L{tL}','L':tL,'x':float(x),'threads':threads,'output':str(base/f'teacher_L{tL}.json'),
                              'argv':['--L',str(tL),'--x',xs,'--nz',str(teacher['nz']),'--osc',str(teacher['osc']),*common,
                                      '--train-keep',str(teacher['keep']),'--diagnostics',teacher.get('diagnostics','first'),
                                      '--threads',str(threads),*limits(tL,{**teacher,**per_L.get(tL,{})}),*teacher.get('extra_argv',[])]})
                basis={'basis_from':0};prev={'seed_from':0}
            else:
                basis,prev=continuation_inputs(cont,x)
            for L in spec['ladder']:
                steps.append({'name':f'window_L{L}','L':int(L),'x':float(x),'threads':threads,'output':str(base/f'window_L{L}.json'),
                              **prev,**basis,'argv':wargv(L)})
                prev={'seed_from':len(steps)-1}
                for s in spec.get('side',[]):
                    if int(s['after_L'])!=L:continue
                    raw=bool(s.get('raw'));simple_name(s['name'],'side step name')
                    argv=['--L',str(L),'--x',xs,*s['argv'],'--threads',str(threads),*limits(L,{**window,**per_L.get(L,{})})]
                    argv+=(['--window','none'] if raw else common)
                    step={'name':s['name'],'L':int(L),'x':float(x),'threads':threads,'output':str(base/f'{s["name"]}.json'),'argv':argv}
                    if not raw:step.update(prev);step.update(basis)
                    steps.append(step)
            for st in steps:
                try:pre=_free_parser().parse_args(st['argv'])
                except SystemExit as exc:raise ValueError(f'{st["name"]}: argv does not parse: {st["argv"]}') from exc
                if pre.cache_dir is not None:
                    raise ValueError(f'{st["name"]}: --cache-dir may only come from the spec "cache_dir" (any spelling in argv is refused)')
                st['argv']=[*st['argv'],*cache]          # the single canonical absolute cache option (IR04)
                check_step(st,g,cache)
                o=Path(st['output']).resolve()
                if results not in o.parents:raise ValueError(f'{st["name"]}: output {o} escapes {results}')
            lanes_.append({'group':g['name'],'x':float(x),'resources':res,'steps':steps})
    outs=[s['output'] for ln in lanes_ for s in ln['steps']]
    if len(set(outs))!=len(outs):raise ValueError('Duplicate step outputs in the campaign')
    return lanes_


def _free_parser():
    p=parser()
    for act in p._actions:
        if act.dest=='output':act.required=False
    return p


def check_step(st,g,cache):
    """Validate the EFFECTIVE parsed configuration of a step (R20): every spelling/abbreviation
    of a runner-owned option is rejected, threads and memory guard fit the lane allocation."""
    try:a=_free_parser().parse_args(st['argv'])
    except SystemExit as exc:raise ValueError(f'{st["name"]}: argv does not parse: {st["argv"]}') from exc
    owned=[k for k in RUNNER_OWNED if getattr(a,k) not in (None,False)]
    if owned:raise ValueError(f'{st["name"]}: argv may not set runner-owned options {owned}')
    if a.L!=int(st['L']) or float(a.x)!=float(st['x']):                     # cutoff and x are owned by expansion (IR09)
        raise ValueError(f'{st["name"]}: effective --L {a.L} / --x {a.x} differ from the declared L{st["L"]} x={st["x"]}')
    if a.threads!=int(st['threads']) or a.threads>int(g['cpus']):raise ValueError(f'{st["name"]}: --threads {a.threads} vs step {st["threads"]}, cpus {g["cpus"]}')
    if a.memory_limit_gib>guard_cap(g):raise ValueError(f'{st["name"]}: effective --memory-limit-gib {a.memory_limit_gib} above the lane allocation {g["mem_gib"]}G (guard cap {guard_cap(g)})')
    want_cache=Path(cache[1]).resolve() if cache else None
    if (a.cache_dir.resolve() if a.cache_dir else None)!=want_cache:raise ValueError(f'{st["name"]}: --cache-dir differs from the campaign cache_dir')
    if a.train_keep and (st.get('seed_from') is not None or st.get('basis_from') is not None or st.get('seed_external') or st.get('basis_external')):
        raise ValueError(f'{st["name"]}: a teacher step takes no seed/basis')


def freeze(a):
    out=Path(a.out).resolve()
    if (out/'manifest.json').exists():raise FileExistsError(f'{out}/manifest.json exists; freeze a new campaign directory')
    spec=json.loads(Path(a.spec).read_text())
    simple_name(spec['campaign'],'campaign id')
    receipt=json.loads(Path(a.receipt).read_text())
    rel=lanes.release_fingerprint(ROOT)
    if receipt.get('passed') is not True:raise ValueError('Validation receipt did not pass')
    if receipt['source_sha256']!=source_hash() or receipt['release_sha256']!=rel:
        raise ValueError('Receipt belongs to a different source/release than this installation')
    if receipt['runtime']!=lanes.runtime_identity():raise ValueError('This interpreter differs from the receipt runtime')
    tar=Path(a.release_tar).resolve()
    if lanes.file_hash(tar)!=a.release_tar_sha256:raise ValueError('Release tarball checksum mismatch')
    out.mkdir(parents=True,exist_ok=True)
    with admin_lock(out):
        return _freeze_locked(a,out,spec,receipt,rel,tar)


def _freeze_locked(a,out,spec,receipt,rel,tar):
    if (out/'manifest.json').exists():raise FileExistsError(f'{out}/manifest.json exists; freeze a new campaign directory')
    for d in ('results','logs','journal','tombstones','lane_failures'):(out/d).mkdir(exist_ok=True)
    m={'schema':lanes.SCHEMA,'campaign':spec['campaign'],'created':utc(),'source_sha256':source_hash(),
       'release_sha256':rel,'release_tar':str(tar),'release_tar_sha256':a.release_tar_sha256,
       'receipt':str(Path(a.receipt).resolve()),'receipt_sha256':lanes.file_hash(a.receipt),
       'runtime':receipt['runtime'],'account':spec.get('account','yun124'),'throttle':int(spec.get('throttle',64)),
       'spec':spec,'lanes':build_lanes(spec,out)}
    m['sha256']=digest(m)
    tmp=out/f'.manifest.{os.getpid()}.{os.urandom(4).hex()}.json'
    atomic_json(tmp,m)
    try:os.link(tmp,out/'manifest.json')          # atomic, never overwrites an existing manifest (R22)
    finally:tmp.unlink(missing_ok=True)
    groups={}
    for i,ln in enumerate(m['lanes']):groups.setdefault(json.dumps(ln['resources'],sort_keys=True),[]).append(i)
    print(f'{len(m["lanes"])} lanes, {sum(len(ln["steps"]) for ln in m["lanes"])} steps, {len(groups)} resource group(s) -> {out/"manifest.json"}')
    return 0


# ---------------------------------------------------------------- journal of submissions
def journal(campaign):
    """Merged submissions: one dict per intent (job name), with array_job_id once known."""
    p=Path(campaign)/'SUBMITTED.jsonl';subs={}
    if not p.exists():return []
    for line in p.read_text().splitlines():
        if not line.strip():continue
        r=json.loads(line);subs.setdefault(r['name'],{}).update(r)
    return list(subs.values())


def _append(campaign,rec):
    with open(Path(campaign)/'SUBMITTED.jsonl','a') as f:
        f.write(json.dumps(rec,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())


def sbatch_argv(m,campaign,res,indices,throttle,name,script=SBATCH_SCRIPT):
    logs=Path(campaign).resolve()/'logs'
    return ['sbatch','--parsable','-A',m['account'],'-p',res['partition'],'--nodes=1','--ntasks-per-node=1',
            f'--cpus-per-task={int(res["cpus"])}',f'--mem={int(res["mem_gib"])}G','-t',res['wall'],
            f'--signal=B:USR1@{int(res["lead_s"])}','-J',name,'-o',str(logs/'%x_%A_%a.out'),
            f'--array={",".join(map(str,sorted(indices)))}%{int(throttle)}',
            '--export',f'ALL,HT3D_MANIFEST={Path(campaign).resolve()/"manifest.json"},HT3D_RELEASE_TAR={m["release_tar"]},'
                       f'HT3D_RELEASE_TAR_SHA256={m["release_tar_sha256"]}',
            str(script)]


def survey(partition):
    s=run_query(['sinfo','-h','-p',partition,'-o','%t %D %C'],1,0)
    q=run_query(['squeue','-A','yun124','-h','-o','%u %T'],1,0)
    lines=[]
    if s is not None:
        idle=sum(int(c.split('/')[1]) for st,_,c in (ln.split() for ln in s.splitlines()) if st in ('idle','mix'))
        lines.append(f'{partition}: {idle} idle CPUs on idle/mix nodes (small requests usually start at once)')
    else:lines.append(f'{partition}: sinfo failed (start time unknown)')
    if q is not None:
        from collections import Counter
        c=Counter(x for x in q.split('\n') if x);lines.append('yun124 queue: '+', '.join(f'{k} x{v}' for k,v in sorted(c.items())))
    return lines


def _submit(campaign,m,indices,throttle,dry):
    groups={}
    for i in indices:groups.setdefault(json.dumps(m['lanes'][i]['resources'],sort_keys=True),[]).append(i)
    records=[]
    for key,idx in groups.items():
        res=json.loads(key);name=f'ht3d-{m["campaign"]}-{os.urandom(3).hex()}'
        argv=sbatch_argv(m,campaign,res,idx,throttle,name)
        for ln in survey(res['partition']):print(ln)
        print(' '.join(shlex.quote(x) for x in argv))
        if dry:continue
        logs=Path(campaign).resolve()/'logs'
        _append(campaign,{'name':name,'lanes':idx,'resources':res,'throttle':throttle,'intent_time':utc(),'argv':argv,
                          'log_pattern':str(logs/f'{name}_<array>_<lane>.out')})       # intent BEFORE sbatch (R11)
        env=dict(os.environ,HT3D_MANIFEST=str(Path(campaign).resolve()/'manifest.json'),HT3D_RELEASE_TAR=m['release_tar'],
                 HT3D_RELEASE_TAR_SHA256=m['release_tar_sha256'])        # inherited values can never win (IR07)
        p=subprocess.run(argv,capture_output=True,text=True,env=env)
        if p.returncode!=0:
            _append(campaign,{'name':name,'sbatch_failed':p.stderr.strip()[:500]})
            raise RuntimeError(f'sbatch failed: {p.stderr.strip()}')
        jid=p.stdout.strip().split(';')[0]
        if not re.fullmatch(r'\d+',jid):raise RuntimeError(f'unexpected sbatch output {p.stdout!r}; job name {name}')
        _append(campaign,{'name':name,'array_job_id':jid,'submit_time':utc()})
        log=str(logs/f'{name}_{jid}_{idx[0]}.out')
        print(f'submitted array {jid} ({name}) lanes {idx}\n  tail -f {log}')
        records.append({'name':name,'array_job_id':jid,'lanes':idx})
    return records


def live_lanes(campaign):
    """Lane indices with a pending/running element of any journaled submission, found by
    job NAME (so an id that never reached the journal still counts). None = UNKNOWN."""
    names=[r['name'] for r in journal(campaign) if not r.get('sbatch_failed')]
    if not names:return set()
    rows=squeue_rows(['-u',getpass.getuser(),'-n',','.join(names)])
    if rows is None:return None
    live=set()
    for ln in rows:
        _,name,arr,task=ln.split('|')
        if name in names and task.strip().isdigit():live.add(int(task))
    return live


def submit(a):
    campaign=Path(a.dir).resolve();m=lanes.load_manifest(campaign/'manifest.json')
    indices=a.lanes if a.lanes else list(range(len(m['lanes'])))
    if any(not 0<=i<len(m['lanes']) for i in indices):raise ValueError('lane index outside the manifest')
    with admin_lock(campaign):
        live=live_lanes(campaign)
        if live is None:raise RuntimeError('squeue failed: live jobs UNKNOWN; refusing to submit')
        dup=sorted(set(indices)&live)
        if dup:raise RuntimeError(f'lanes {dup} already have a pending/running job; not submitting duplicates')
        _submit(campaign,m,indices,a.throttle or m['throttle'],a.dry_run)
    return 0


# ---------------------------------------------------------------- status / charges
def _mem_mb(s):
    m=re.fullmatch(r'([\d.]+)([KMGT]?)n?c?',str(s or ''))
    if not m:return None
    return float(m.group(1))*{'K':1/1024,'':1,'M':1,'G':1024,'T':1024**2}[m.group(2)]


def charges(campaign):
    """Per execution attempt (requeues included via --duplicates): measured SU (billing TRES /
    3600 x hours, see BILLING_PER_SU_HOUR) when Slurm reports billing, and the memory-aware
    shared estimate max(cpus, mem_GB/2) x hours. Attempts are
    restricted to this campaign's journaled job names and de-duplicated by (JobIDRaw, Start)."""
    names=[r['name'] for r in journal(campaign) if not r.get('sbatch_failed')]
    if not names:return []
    created=lanes.load_manifest(Path(campaign)/'manifest.json')['created']
    start=dt.datetime.strptime(created,'%Y%m%dT%H%M%SZ').strftime('%Y-%m-%dT%H:%M:%S')
    s=run_query(['sacct','-n','-P','-X','--duplicates','-u',getpass.getuser(),'--name',','.join(names),'-S',start,'-E','now',
                 '-o','JobIDRaw,JobID,JobName,State,Start,ElapsedRaw,AllocTRES,AllocCPUS,ReqMem,Partition'],1,0)
    if s is None:return [{'error':'sacct failed: charges UNKNOWN'}]
    rows=[];seen=set()
    for ln in s.splitlines():
        raw,jid,name,state,startt,el,tres,cpus,reqmem,part=ln.split('|')
        if name not in names or (raw,startt) in seen:continue
        seen.add((raw,startt))
        hours=int(el or 0)/3600;t=dict(kv.split('=',1) for kv in tres.split(',') if '=' in kv)
        mem_mb=_mem_mb(t.get('mem',reqmem))
        est=hours*su_per_hour(part,int(cpus or 0),mem_mb)
        rows.append({'job':raw,'array_element':jid,'name':name,'state':state,'start':startt,'hours':hours,'cpus':int(cpus or 0),
                     'mem_mb':mem_mb,'billing':float(t['billing']) if 'billing' in t else None,
                     'su_measured':hours*float(t['billing'])/BILLING_PER_SU_HOUR if 'billing' in t else None,'su_estimated':est})
    return rows


def active_failure(campaign,i,states):
    """The recorded lane failure, only while its step still has no validated output (IR03)."""
    f=Path(campaign)/'lane_failures'/f'lane_{i:03d}.json'
    try:rec=json.loads(f.read_text()) if f.exists() else None
    except (OSError,ValueError):return {'step':None,'name':'?','rc':'unreadable failure record'}
    if not isinstance(rec,dict):return None
    k=rec.get('step')
    if isinstance(k,int) and 0<=k<len(states) and states[k]=='done':return None
    return rec


def step_detail(step,query=None):
    """Checkpoint/claim/owner detail of one step (IR06); owner Slurm state only if `query` is given."""
    out=Path(step['output']);c=Path(str(out)+'.claim');d={'checkpoint':Path(str(out)+'.checkpoint.json').exists(),'claim':None}
    if c.exists():
        try:owner=json.loads((c/'owner.json').read_text())
        except (OSError,ValueError):owner={}
        d['claim']={'job':owner.get('slurm_job_id'),'host':owner.get('host'),'pid':owner.get('pid')}
        if query and owner.get('slurm_job_id'):d['claim']['state']=query(owner['slurm_job_id'])
    return d


def lane_report(campaign,m,query=None):
    out=[]
    for i,ln in enumerate(m['lanes']):
        st=lanes.lane_states(ln)
        out.append({'lane':i,'group':ln['group'],'x':ln['x'],'done':st.count('done'),'steps':len(st),
                    'current':next((s['name'] for s,t in zip(ln['steps'],st) if t!='done'),None),'states':st,
                    'invalid':[s['name'] for s,t in zip(ln['steps'],st) if t.startswith('invalid')],
                    'detail':{s['name']:step_detail(s,query) for s,t in zip(ln['steps'],st) if t!='done'},
                    'failure':active_failure(campaign,i,st)})
    return out


def _check_runtime(m):
    if lanes.runtime_identity()!=m['runtime']:
        raise RuntimeError('This interpreter differs from the campaign runtime; source the release env.sh first')


def status(a):
    campaign=Path(a.dir).resolve();m=lanes.load_manifest(campaign/'manifest.json');_check_runtime(m)
    out=lane_report(campaign,m,query=lambda j:job_state(j,retries=2,pause=2.0));ch=charges(campaign)
    if a.json:print(json.dumps({'lanes':out,'charges':ch},indent=1));return 0
    for r in out:
        print(f"lane {r['lane']:3d} {r['group']:>8} x={r['x']:<8g} {r['done']}/{r['steps']} current={r['current']}"
              +(f" FAILED rc={r['failure']['rc']} at {r['failure']['name']}" if r['failure'] else '')
              +(f" INVALID {r['invalid']}" if r['invalid'] else ''))
        for name,d in r['detail'].items():
            if d['checkpoint'] or d['claim']:
                c=d['claim'];print(f"      {name}: checkpoint={'yes' if d['checkpoint'] else 'no'}"
                                   +(f" claim job={c['job']} host={c['host']} owner={'/'.join(c['state']) if c.get('state') else '?'}" if c else ' no claim'))
    jobs=[c for c in ch if 'job' in c]
    if any('error' in c for c in ch):print('charges: UNKNOWN (sacct failed); not reporting a total');return 0
    print(f'charges over {len(jobs)} execution attempts: measured {sum(c["su_measured"] or 0 for c in jobs):.1f} SU (billing TRES; '
          f'{sum(1 for c in jobs if c["billing"] is None)} attempts without billing), estimated {sum(c["su_estimated"] for c in jobs):.1f} SU')
    return 0


# ---------------------------------------------------------------- recover / resubmit
def claims(m,lane_indices=None):
    for i,ln in enumerate(m['lanes']):
        if lane_indices is not None and i not in lane_indices:continue
        for s in ln['steps']:
            c=Path(str(s['output'])+'.claim')
            if c.exists():yield i,c


def recover_claim(campaign,claim,dry,log,query=job_state):
    """Tombstone one stale claim if its owner job is confirmed terminal. Caller holds the admin lock."""
    try:
        owner=json.loads((claim/'owner.json').read_text());st=os.stat(claim)
    except (OSError,ValueError) as exc:
        log(claim=str(claim),action='refuse',reason=f'unreadable owner: {exc}');return False
    jid=owner.get('slurm_job_id')
    if not jid:log(claim=str(claim),action='refuse',reason='claim has no slurm_job_id');return False
    state,detail=query(jid)
    if state!='TERMINAL':log(claim=str(claim),action='refuse',reason=f'{state}: {detail}',job=jid);return False
    try:                                   # recheck identity immediately before the rename (R02)
        again=json.loads((claim/'owner.json').read_text());st2=os.stat(claim)
    except (OSError,ValueError) as exc:
        log(claim=str(claim),action='refuse',reason=f'owner changed/unreadable at recheck: {exc}');return False
    if again.get('token')!=owner.get('token') or (st2.st_dev,st2.st_ino)!=(st.st_dev,st.st_ino):
        log(claim=str(claim),action='refuse',reason='claim replaced since first read',job=jid);return False
    dest=Path(campaign)/'tombstones'/f'{utc()}-{os.urandom(3).hex()}-{claim.name}'
    if dry:log(claim=str(claim),action='would_tombstone',job=jid,state=detail,dest=str(dest));return True
    claim.rename(dest)
    log(claim=str(claim),action='tombstoned',job=jid,state=detail,dest=str(dest));return True


def _logger(campaign):
    def log(**ev):
        ev['time']=utc()
        with open(Path(campaign)/'recover.jsonl','a') as f:f.write(json.dumps(ev,sort_keys=True)+'\n')
        print(json.dumps(ev,sort_keys=True))
    return log


def recover(a):
    campaign=Path(a.dir).resolve();m=lanes.load_manifest(campaign/'manifest.json');log=_logger(campaign)
    with admin_lock(campaign):
        for _,c in claims(m):recover_claim(campaign,c,a.dry_run,log)
    return 0


def resubmit(a):
    campaign=Path(a.dir).resolve();m=lanes.load_manifest(campaign/'manifest.json');_check_runtime(m);log=_logger(campaign)
    with admin_lock(campaign):
        live=live_lanes(campaign)
        if live is None:raise RuntimeError('squeue failed: live jobs UNKNOWN; refusing to resubmit')
        todo=[]
        for r in lane_report(campaign,m):
            i=r['lane']
            if i in live or r['done']==r['steps']:continue
            if r['invalid']:print(f'lane {i}: invalid outputs {r["invalid"]}; quarantine them by hand first');continue
            if r['failure'] and not a.include_failed:
                print(f'lane {i}: recorded failure rc={r["failure"]["rc"]} at {r["failure"]["name"]}; skipped (use --include-failed after inspecting it)');continue
            todo.append(i)
        blocked=set()
        for i,c in claims(m,set(todo)):
            if not recover_claim(campaign,c,a.dry_run,log):blocked.add(i)
        todo=[i for i in todo if i not in blocked]
        if blocked:print(f'lanes {sorted(blocked)} keep a claim that could not be recovered; not resubmitted')
        if not todo:print('nothing to resubmit');return 0
        _submit(campaign,m,todo,a.throttle or m['throttle'],a.dry_run)
    return 0


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    f=sub.add_parser('freeze');f.add_argument('--spec',required=True);f.add_argument('--receipt',required=True)
    f.add_argument('--release-tar',required=True);f.add_argument('--release-tar-sha256',required=True);f.add_argument('--out',required=True)
    s=sub.add_parser('submit');s.add_argument('dir');s.add_argument('--lanes',type=int,nargs='+')
    s.add_argument('--throttle',type=int);s.add_argument('--dry-run',action='store_true')
    t=sub.add_parser('status');t.add_argument('dir');t.add_argument('--json',action='store_true')
    r=sub.add_parser('recover');r.add_argument('dir');r.add_argument('--dry-run',action='store_true')
    u=sub.add_parser('resubmit');u.add_argument('dir');u.add_argument('--throttle',type=int)
    u.add_argument('--include-failed',action='store_true');u.add_argument('--dry-run',action='store_true')
    a=p.parse_args(argv)
    return {'freeze':freeze,'submit':submit,'status':status,'recover':recover,'resubmit':resubmit}[a.cmd](a)

if __name__=='__main__':raise SystemExit(main())
