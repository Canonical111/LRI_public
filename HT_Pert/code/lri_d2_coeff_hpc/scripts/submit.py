#!/usr/bin/env python3
"""Submit validation or coefficient-task jobs to Expanse or symmetry. Dry run unless --submit.

Run on a login node from the unpacked release whose tar is given by --release, after
`LRI_COEFF_SITE=<site> source cluster/site.sh`. Standard library only.

  submit.py validate --release $LRI_COEFF_DATA/releases/lri2d_coeff-<commit>.tar [--partition P] [--submit]
  submit.py campaign --release ... --manifest $LRI_COEFF_DATA/campaigns/<name>/campaign.json
                     [--tasks 0-3,7] [--partition P] [--time HH:MM:SS] [--cpus N] [--submit]

validate: one job that runs the test suite and an L=22 replay of the archived pilot on a compute node and
writes $LRI_COEFF_DATA/validation/<sha16>_<site>_<jobid>/receipt.json.
campaign: one job per selected task that is not finished, queued/running or locked, and only when a passing
receipt exists for the same release tar and site. Running the same command again resumes interrupted tasks
from their checkpoints and skips finished ones. A task is finished only if its output verifies and carries the
identity the validated stack would give it. Outputs are reserved by path: no output gets a second live job,
whichever manifest it comes from.
"""
from pathlib import Path
import argparse,datetime,getpass,hashlib,json,math,os,re,shlex,socket,subprocess,sys,tarfile

ROOT=Path(__file__).resolve().parents[1]
PREFIX='lri_d2_coeff_hpc/'
RECEIPT_KIND='lri-coeff-validation-receipt-v1'
# squeue --states=all also lists recently ended jobs; anything else (pending, running, suspended,
# requeued, held, completing, ...) counts as live.
TERMINAL={'BOOT_FAIL','CANCELLED','COMPLETED','DEADLINE','FAILED','NODE_FAIL','OUT_OF_MEMORY','PREEMPTED','REVOKED','TIMEOUT'}
GiB_MB=1024
SITES={
 # Expanse charges the larger of cores and memory/(node memory/128) on the shared partitions.
 'expanse':dict(account='yun124',wall_h=48,exclusive=False,data='/expanse/lustre/scratch/{user}/temp_project/lri2d_coeff',auto=['shared','large-shared'],
   partitions={'shared':dict(mem=243,node_mb=249325,cores=128),'large-shared':dict(mem=2000,node_mb=2055652,cores=128)},
   validate=dict(partition='shared',cpus=16,mem=30,time='01:00:00')),
 # symmetry partitions are whole-node EXCLUSIVE; threads = all physical cores of the node. amdq first (user rule);
 # defq and the debug queues only on request (--partition).
 'symmetry':dict(account=None,wall_h=24,exclusive=True,data='/mnt/beegfs/{user}/lri2d_coeff',auto=['amdq','largememq'],
   partitions={'amdq':dict(mem=245),'defq':dict(mem=180),'largememq':dict(mem=370),'amddebugq':dict(mem=245,wall_h=1),'debugq':dict(mem=180,wall_h=1)},
   validate=dict(partition='amdq',mem=64,time='01:00:00')),
}

def die(msg):raise SystemExit('submit: '+msg)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def sha_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()
def now():return datetime.datetime.now().astimezone().isoformat(timespec='seconds')
def under(path,root):
    return Path(os.path.realpath(path)).is_relative_to(Path(os.path.realpath(root)))

def parse_time(s):
    m=re.fullmatch(r'(?:(\d+)-)?(\d+):(\d\d):(\d\d)',s)
    if not m:die(f'--time {s!r}: use HH:MM:SS or D-HH:MM:SS')
    d,h,mi,se=(int(x or 0) for x in m.groups())
    return ((d*24+h)*60+mi)*60+se
def fmt_time(sec):
    h,r=divmod(int(sec),3600);return f'{h:02d}:{r//60:02d}:{r%60:02d}'

def release_info(path,data):
    """Check the release tar: location, checksum, safe members, and that this tree is its unpacked copy."""
    tar=Path(path)
    if not tar.is_absolute():die('--release must be an absolute path')
    if not tar.is_file():die(f'no release tar {tar}')
    if not under(tar,data/'releases'):die(f'release tar must be under {data}/releases (jobs read it there)')
    sha=sha_file(tar);side=tar.with_name(tar.name+'.sha256')
    if side.exists() and side.read_text().split()[0]!=sha:die(f'{tar} does not match {side}')
    src={};files={}
    with tarfile.open(tar) as t:
        for m in t.getmembers():
            n=m.name
            if not (n==PREFIX.rstrip('/') or n.startswith(PREFIX)) or '..' in Path(n).parts or not (m.isfile() or m.isdir()):
                die(f'unexpected member {n!r} in {tar}')
            if m.isfile():files[n]=m
        def read(n):
            if n not in files:die(f'{tar} has no {n}')
            return t.extractfile(files[n]).read()
        for n in files:
            parts=n.split('/')
            if len(parts)==4 and parts[1:3]==['src','lri_coeff'] and Path(n).suffix in ('.py','.cpp'):src[parts[3]]=sha_bytes(read(n))
        mbytes=read(PREFIX+'MANIFEST.sha256');jbytes=read(PREFIX+'cluster/job.sbatch')
    if (ROOT/'MANIFEST.sha256').read_bytes()!=mbytes or (ROOT/'cluster/job.sbatch').read_bytes()!=jbytes:
        die(f'run submit.py from the unpacked copy of {tar.name} (MANIFEST.sha256 or cluster/job.sbatch differ)')
    return dict(path=str(tar),name=tar.name,sha256=sha,source_digest=sha_bytes(canonical(dict(sorted(src.items())))))

def find_receipt(data,site,release):
    best=None
    for f in sorted((data/'validation').glob(f"{release['sha256'][:16]}_{site}_*/receipt.json")):
        try:r=json.loads(f.read_text())
        except (OSError,ValueError):continue
        if r.get('kind')==RECEIPT_KIND and r.get('passed') is True and r.get('site')==site and r.get('release_sha256')==release['sha256'] \
           and r.get('source_digest')==release['source_digest'] and isinstance(r.get('stack'),dict) \
           and all(k in r['stack'] for k in ('python','numpy','scipy','numba','longdouble_nmant','machine')) and (best is None or r.get('finished','')>best[1].get('finished','')):best=(f,r)
    return best

def live_jobs(data):
    """Non-terminal jobs of this user. Returns ({name: id}, {output realpath: id}); names and outputs also come
    from submissions.jsonl records whose job id is live (so renamed jobs count). squeue failure aborts."""
    env={k:v for k,v in os.environ.items() if not k.startswith('SQUEUE_')}
    try:p=subprocess.run(['squeue','-h','-u',getpass.getuser(),'--states=all','-o','%i|%j|%T'],env=env,capture_output=True,text=True,timeout=120)
    except (OSError,subprocess.TimeoutExpired) as exc:die(f'squeue failed ({exc}); job state UNKNOWN, nothing submitted')
    if p.returncode:die(f'squeue failed ({p.stderr.strip()}); job state UNKNOWN, nothing submitted')
    names={};ids=set();outputs={}
    for line in p.stdout.splitlines():
        jid,name,state=(line.split('|')+['',''])[:3]
        st=state.split()[0] if state.strip() else ''
        if st and st not in TERMINAL:names[name]=jid;ids.add(jid)
    rec=data/'submissions.jsonl'
    if rec.exists():
        for line in rec.read_text().splitlines():
            try:r=json.loads(line)
            except ValueError:continue
            jid=str(r.get('job_id'))
            if jid in ids:
                names.setdefault(r.get('name'),jid)
                if r.get('output'):outputs.setdefault(r['output'],jid)
    return names,outputs

def load_manifest(path,data,release):
    m=Path(path)
    if not m.is_absolute() or not m.is_file():die('--manifest must be an existing absolute path')
    if not under(m,data):die(f'manifest must be under {data}')
    raw=m.read_bytes();wrap=json.loads(raw);payload=wrap.get('payload')
    if wrap.get('schema')!='lri-coeff-v1' or sha_bytes(canonical(payload))!=wrap.get('sha256'):die('invalid manifest checksum')
    if payload.get('kind')!='lri-2d-coefficient-array-v1':die('not a coefficient campaign manifest')
    if payload['source_digest']!=release['source_digest']:die('manifest was made from different solver source than the release')
    for i,t in enumerate(payload['tasks']):
        if sha_bytes(canonical({k:v for k,v in t.items() if k!='task_digest'}))!=t['task_digest']:die(f'task {i}: digest mismatch')
        if t.get('cache'):die(f'task {i}: shared graph cache {t["cache"]}; cluster jobs build graphs in memory (make the manifest with --cache-mode none)')
        for k in ('output','checkpoint'):
            # Absolute only: the submitter's and the job's working directories differ.
            if t.get(k) and not Path(t[k]).is_absolute():die(f'task {i}: {k} {t[k]} is not an absolute path')
            if t.get(k) and not under(t[k],data):die(f'task {i}: {k} {t[k]} is outside {data}')
    return dict(path=str(m),sha256=sha_bytes(raw),cid=wrap['sha256'][:8],source_digest=payload['source_digest'],tasks=payload['tasks'])

def expected_identity(t,source,stack):
    """The solver's result identity (cli.py) for task t, run from `source` on the validated `stack`."""
    cfg=dict(L=t['cutoff'],degree=t['degree'],scheme=t['scheme'],pmax=None,full_order=False,backend=t['backend'])
    runtime=dict(python='.'.join(stack['python'].split('.')[:2]),numpy=stack['numpy'],scipy=stack['scipy'],numba=stack['numba'],
                 longdouble_bits=int(stack['longdouble_nmant']),machine=stack['machine'])
    return sha_bytes(canonical(dict(configuration=cfg,source=source,runtime=runtime))),cfg

def output_problem(t,source,stack):
    """None if t's output is a complete result with the expected identity, else the reason it is not."""
    try:
        w=json.loads(Path(t['output']).read_text());p=w['payload']
        if w.get('schema')!='lri-coeff-v1' or sha_bytes(canonical(p))!=w.get('sha256'):return 'checksum/schema invalid'
        ident,cfg=expected_identity(t,source,stack)
        if p.get('configuration')!=cfg or p.get('source_digest')!=source:return 'other configuration or solver source'
        if p.get('identity')!=ident:return 'identity differs from the validated stack (other Python/numpy/scipy/numba/machine)'
        r=p['result'];x=p['execution'];n=t['degree']+1
        if (r['scheme'],r['cutoff'],r['degree'])!=(t['scheme'],t['cutoff'],t['degree']):return 'result metadata differ from the task'
        # engine.py: energies are the 4 primary channels, vacuum_coefficients one row per vacuum cutoff
        # (0,2,...,L for the windowed schemes, L alone for raw); every row has degree+1 coefficients.
        nv=1 if t['scheme']=='raw' else t['cutoff']//2+1
        rows=[r['C'],r['r'],r['g'],*r['energies'],*r['vacuum_coefficients']]
        if len(r['energies'])!=4 or len(r['vacuum_coefficients'])!=nv or any(not isinstance(v,list) or len(v)!=n or not all(number(z) for z in v) for v in rows):
            return 'incomplete or non-numeric result arrays'
        if not (isinstance(x['threads'],int) and x['threads']>=1 and number(x['seconds']) and number(x['peak_rss_KiB'])):return 'incomplete execution record'
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:return f'unreadable ({type(exc).__name__})'
    return None

def number(z):return isinstance(z,(int,float)) and not isinstance(z,bool) and math.isfinite(z)

def task_job_name(t):
    """Job name derived from the output file alone: a live job for an output is found by name, whichever
    manifest (and configuration) submitted it and even if submissions.jsonl was not written."""
    return f"lri2dc-o{sha_bytes(os.path.realpath(t['output']).encode())[:12]}"

def task_state(t,source,stack,name,live,reserved):
    if name in live:return 'live',f'job {live[name]}'
    key=os.path.realpath(t['output'])
    if key in reserved:return 'live',f'output reserved by job {reserved[key]}'
    out=Path(t['output']);lock=Path(t['output']+'.lock')
    if out.exists():
        why=output_problem(t,source,stack)
        return ('done','') if why is None else ('conflict',f'existing output: {why}; move it away')
    if lock.exists():
        try:owner=(lock/'owner.json').read_text().strip()
        except OSError:owner='(no owner.json)'
        return 'locked',f'stale? {lock} owner {owner}; remove it only after sacct shows that job ended'
    return 'todo',''

def est_seconds(t):
    """Rough wall time at 4 threads: 50 s for the consistent L=22 degree-8 pilot, x3.5 per +2 in L."""
    f=(0.6 if t['scheme']=='raw' else 1.0)*0.4**max(0,8-t['degree'])
    return 50.0*f*3.5**((t['cutoff']-22)/2)

def resources(site,mem,partition,cpus,time_s=None,est_s=0.0):
    """Partition, memory, CPUs and wall time for a job needing `mem` GiB. time_s None: 4x the estimate est_s
    plus 30 min, at least 1 h, capped by the chosen partition's limit; an explicit time_s is never capped."""
    S=SITES[site];parts=S['partitions']
    if partition is None:
        fits=[p for p in S['auto'] if mem<=parts[p]['mem']]
        if not fits:return None,f'needs {mem} GiB; no {site} partition offers it'
        partition=fits[0]
    P=parts.get(partition)
    if P is None:return None,f'partition {partition} is not one of {sorted(parts)}'
    if mem>P['mem']:return None,f'needs {mem} GiB > {partition} limit {P["mem"]} GiB'
    cap=P.get('wall_h',S['wall_h'])*3600
    if time_s is None:time_s=min(cap,max(3600,math.ceil((4*est_s+1800)/3600)*3600))
    elif time_s>cap:return None,f'--time {fmt_time(time_s)} > {partition} limit {fmt_time(cap)}'
    r=dict(partition=partition,need=mem,time=fmt_time(time_s))
    # Whole nodes: ask for all of the node's memory (more headroom at no cost).
    if S['exclusive']:r.update(mem=P['mem'],cpus='node',charge=None)
    else:
        per=P['node_mb']/P['cores'];c=min(P['cores'],max(cpus,math.ceil(mem*GiB_MB/per)))
        r.update(mem=mem,cpus=c,charge=round(max(c,mem*GiB_MB/per)*time_s/3600,1))
    return r,''

def sbatch_args(site,name,r,data):
    S=SITES[site];a=[f'--job-name={name}',f'--partition={r["partition"]}','--nodes=1','--ntasks=1']
    a+=['--exclusive'] if S['exclusive'] else [f'--cpus-per-task={r["cpus"]}']
    if S['account']:a.append(f'--account={S["account"]}')
    return a+[f'--mem={r["mem"]}G',f'--time={r["time"]}','--signal=B:USR1@900','--no-requeue',
              f'--output={data}/logs/%x_%j.out',f'--chdir={data}','--export=ALL']

def job_env(fields):
    # Inherited SBATCH_* would override these options; inherited job settings must not leak in.
    keep={k:v for k,v in os.environ.items() if not k.startswith(('SBATCH_','SQUEUE_','PYTHON','NUMBA_','OMP_')) and not (k.startswith('LRI_COEFF_') and k!='LRI_COEFF_VENV')}
    keep.update(fields);return keep

def submit_one(args,env,record,data,dry):
    cmd=['sbatch','--parsable',*args,str(ROOT/'cluster/job.sbatch')]
    print('  '+' '.join(f'{k}={shlex.quote(v)}' for k,v in env.items() if k.startswith('LRI_COEFF_'))+' \\\n    '+shlex.join(cmd))
    if dry:return None
    p=subprocess.run(cmd,env=env,capture_output=True,text=True)
    if p.returncode:die('sbatch failed: '+p.stderr.strip())
    jid=p.stdout.strip().split(';')[0]
    if not jid.isdigit():die('unexpected sbatch output: '+p.stdout.strip())
    record.update(job_id=jid,time=now(),submit_host=socket.gethostname())
    print(f'  submitted {jid}; log {data}/logs/{record["name"]}_{jid}.out',flush=True)
    try:
        with open(data/'submissions.jsonl','a') as f:f.write(json.dumps(record,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    except OSError as exc:
        die(f'job {jid} ({record["name"]}) was submitted but recording it in submissions.jsonl failed ({exc}); '
            'stopping here. Its job name still marks its output as taken.')
    return jid

class Mutex:
    """Cross-node submission mutex (mkdir is atomic on Lustre and BeeGFS). Never stolen automatically."""
    def __init__(self,path):self.path=path;self.held=False
    def __enter__(self):
        try:self.path.mkdir()
        except FileExistsError:die(f'another submission holds {self.path}; remove it only if no submit.py is running')
        self.held=True;(self.path/'owner').write_text(f'{socket.gethostname()} {os.getpid()} {now()}\n');return self
    def __exit__(self,*exc):
        if self.held:
            (self.path/'owner').unlink(missing_ok=True);self.path.rmdir()

def select(spec,n):
    if not spec:return list(range(n))
    out=set()
    for part in spec.split(','):
        m=re.fullmatch(r'(\d+)(?:-(\d+))?',part.strip())
        if not m:die(f'--tasks {spec!r}: use e.g. 0-3,7')
        lo=int(m[1]);hi=int(m[2] or lo)
        if hi<lo or hi>=n:die(f'--tasks {part}: outside 0..{n-1}')
        out.update(range(lo,hi+1))
    return sorted(out)

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=p.add_subparsers(dest='mode',required=True)
    for name in ('validate','campaign'):
        s=sub.add_parser(name);s.add_argument('--site',choices=sorted(SITES),default=os.environ.get('LRI_COEFF_SITE'))
        s.add_argument('--data',type=Path,help='data root (default $LRI_COEFF_DATA, else the site default)')
        s.add_argument('--release',required=True,help='absolute path of the release tar under DATA/releases')
        s.add_argument('--partition');s.add_argument('--submit',action='store_true',help='really submit (default: dry run)')
    v=sub.choices['validate'];v.add_argument('--again',action='store_true',help='validate even if a passing receipt exists')
    c=sub.choices['campaign'];c.add_argument('--manifest',required=True);c.add_argument('--tasks',help='indices, e.g. 0-3,7 (default all)')
    c.add_argument('--time',help='wall time for every selected task (default: per-task estimate, capped by the partition)')
    c.add_argument('--cpus',type=int,default=16,help='Expanse: minimum CPUs per task (memory may imply more; default 16)')
    c.add_argument('--mem-scale',type=float,default=1.0,help='multiply the planned memory (e.g. after an OOM)')
    c.add_argument('--max-new',type=int,help='submit at most this many tasks')
    a=p.parse_args()
    if a.site not in SITES:p.error('--site (or LRI_COEFF_SITE) must be expanse or symmetry')
    S=SITES[a.site];data=a.data or Path(os.environ.get('LRI_COEFF_DATA') or S['data'].format(user=getpass.getuser()))
    if not data.is_absolute() or not data.is_dir():die(f'data root {data} must be an existing absolute directory')
    release=release_info(a.release,data);dry=not a.submit
    print(f"site {a.site}  data {data}\nrelease {release['name']} sha256 {release['sha256']}\nsolver source {release['source_digest']}")
    if a.submit:(data/'logs').mkdir(exist_ok=True)
    base=dict(LRI_COEFF_SITE=a.site,LRI_COEFF_DATA=str(data),LRI_COEFF_RELEASE=release['path'],LRI_COEFF_RELEASE_SHA256=release['sha256'])
    if a.mode=='validate':
        name=f"lri2dc-val-{release['sha256'][:8]}-{a.site}"
        r,why=resources(a.site,S['validate']['mem'],a.partition or S['validate']['partition'],S['validate'].get('cpus',1),parse_time(S['validate']['time']))
        if r is None:die(why)
        with (Mutex(data/'.submit.lock') if a.submit else _Null()):
            live,_=live_jobs(data)
            if name in live:die(f'validation {name} is already queued/running (job {live[name]})')
            old=find_receipt(data,a.site,release)
            if old and not a.again:die(f'passing receipt exists: {old[0]} (use --again to validate once more)')
            print(f"validation job {name}: {r['partition']} cpus {r['cpus']} mem {r['mem']}G time {r['time']}" + (f" (<= {r['charge']} SU)" if r['charge'] else ''))
            submit_one(sbatch_args(a.site,name,r,data),job_env(dict(base,LRI_COEFF_JOB='validate',LRI_COEFF_RECEIPT_BASE=str(data/'validation'))),
                       dict(kind='validate',name=name,site=a.site,release_sha256=release['sha256'],**r),data,dry)
            print('receipt will be', data/'validation'/f"{release['sha256'][:16]}_{a.site}_<jobid>"/'receipt.json')
    else:
        if a.cpus<1 or a.mem_scale<=0:die('--cpus and --mem-scale must be positive')
        found=find_receipt(data,a.site,release)
        if not found:die(f"no passing validation receipt for {release['name']} on {a.site} under {data}/validation; run `submit.py validate` first")
        receipt,rdata=found;print('validation receipt',receipt)
        man=load_manifest(a.manifest,data,release);idx=select(a.tasks,len(man['tasks']))
        print(f"manifest {man['path']} ({len(man['tasks'])} tasks, campaign {man['cid']})")
        with (Mutex(data/'.submit.lock') if a.submit else _Null()):
            live,reserved=live_jobs(data);new=0;su=0.0;counts={}
            for i in idx:
                t=man['tasks'][i];name=task_job_name(t)
                state,info=task_state(t,man['source_digest'],rdata['stack'],name,live,reserved)
                m=t['memory_gib']*a.mem_scale;mem=math.ceil(m+max(4,0.05*m))
                r,why=resources(a.site,mem,a.partition,a.cpus,parse_time(a.time) if a.time else None,est_seconds(t))
                if state=='todo' and r is None:state,info='refused',why
                if state=='todo' and a.max_new is not None and new>=a.max_new:state,info='deferred','--max-new reached'
                counts[state]=counts.get(state,0)+1
                desc=f"[{i}] {name} L={t['cutoff']} d={t['degree']} {t['scheme']:<10} {state:<8}"
                if r:desc+=f" {r['partition']} cpus {r['cpus']} mem {r['mem']}G (needs {r['need']}) time {r['time']}"+(f" <= {r['charge']} SU" if r['charge'] else '')
                print(desc+(f'  {info}' if info else ''))
                if state!='todo':continue
                new+=1;su+=r['charge'] or 0;key=os.path.realpath(t['output'])
                fields=dict(base,LRI_COEFF_JOB='task',LRI_COEFF_MANIFEST=man['path'],LRI_COEFF_MANIFEST_SHA256=man['sha256'],LRI_COEFF_INDEX=str(i),LRI_COEFF_RECEIPT=str(receipt))
                jid=submit_one(sbatch_args(a.site,name,r,data),job_env(fields),dict(kind='task',name=name,site=a.site,release_sha256=release['sha256'],
                           manifest=man['path'],manifest_sha256=man['sha256'],index=i,output=key,cutoff=t['cutoff'],degree=t['degree'],scheme=t['scheme'],**r),data,dry)
                reserved[key]=jid or 'this dry run'   # a later task of this call with the same output is not submitted
            print('summary:',', '.join(f'{k} {v}' for k,v in sorted(counts.items())),f'| {"would submit" if dry else "submitted"} {new}'+(f', at most {su:.0f} SU charged up front' if su else ''))
    if dry:print('dry run: nothing submitted (add --submit)')

class _Null:
    def __enter__(self):return self
    def __exit__(self,*exc):return False

if __name__=='__main__':main()
