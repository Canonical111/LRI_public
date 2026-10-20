#!/usr/bin/env python3
"""Whole-node lane mode (port of LRI_C7_D3_HPC@a6ce987 tools/lanes.py with the d-independent changes of C62d's
design, D2PLAN:687-722; PLAN D.9): one Slurm job = one node = one or more lanes, each lane claiming job indices of a
planned campaign and running `production.py run --index` on them with its own CPU set.

  lanes.py queue RUN                      rebuild RUN/lanes/queue.txt under the session lock: completeness from the
                                          checkpoint blocks, done markers of incomplete indices removed and logged
  lanes.py release-stale RUN [--dry-run]  release claims of finished owner jobs (session lock + squeue snapshot)
  lanes.py worker RUN                     inside slurm/lane_worker.sh: reclaim own claims, split CPUs, run the lanes
  lanes.py lane RUN --lane K --cpus LIST --deadline EPOCH|inf --job ID [--restart N] [--stop-seconds S]
                                          one lane (started by the worker)

Lane mode runs only plans of role `campaign` on the measured basis (D.5, HD11): a validation plan, any other
non-measured role (cost_sweep, cost_refresh, flag_check) and any plan without per-index time estimates are refused
(65) before any claim, drill mode included.

Files under RUN/lanes/:
  queue.txt                       '# c8d3-lanes-queue generation=<g> ...' then '<index> <est core-seconds>', heaviest
                                  first; every rebuild writes a new generation
  claims/<index>.json             a running (or crashed) claim, published atomically WITH its owner record (no-clobber
                                  hard link, the checkpoint primitive); removed after the run
  done/<index>                    done marker: a HINT that lets lanes skip a complete index without stat-ing its blocks;
                                  never evidence (status and merge count checkpoint blocks only, A-ORC-4)
  done_invalidated.jsonl          one line per marker removed (queue rebuild, or the holder of a claim on an index whose
                                  blocks are missing)
  failures/<index>.<job>.<restart>.<lane>.<ns>.json   one record per failed attempt
  logs/idx<index>.<job>.<restart>.<lane>.<ns>.log     output of each `production.py run` attempt (C7I-13)
A lane skips an index that is done (marker), claimed, has C8_LANE_MAX_FAILURES (2) failure records, or does not fit the
job's remaining time: est x f_class / (T x 0.9) x C8_LANE_SAFETY (1.5) + C8_LANE_MARGIN (300 s), f_class the
campaign cost model's CPU-class factor of the host (1.5 unknown). A lane stops after
C8_LANE_MAX_CONSECUTIVE_FAILURES (3) failed runs in a row. Lanes are never wider than checkpoint_tasks. Per scan a lane
stats queue.txt once (re-reading it only when its inode, mtime or size changes), lists claims/ and failures/ once,
and lists done/ at most every 60 s and at once on a new queue generation; block counts come from the manifest.
C8_LANES: numa (default on AMD: one lane per NUMA node of the job's CPUs), numa:<k> (k adjacent NUMA nodes per lane),
socket (default elsewhere) or n (equal contiguous parts). Drill mode (C8_LANE_DRILL=1, test-only plans on shared or
debug): the job's affinity set is split into C8_LANES equal parts (default 1). The worker reduces the lane count, or
refuses (64), when lanes x the largest est_peak_bytes exceeds 0.85 x the job's memory limit (cgroup, else
SLURM_MEM_PER_NODE).
Stop signals (F7, ported from C62d; A-ORC-8a): on SIGTERM, SIGINT or SIGHUP (scancel, the wall limit) the worker
forwards SIGTERM to its lanes and each lane to its `production.py run` child (started in its own session), which stops
its native worker and removes its job-private runtime; the lane then removes its scratch directory and exits 128+signal,
leaving its claim stale (released by the next `release-stale` or `lanes N`) and writing no failure record. Every wait
of the shutdown counts from the stop signal toward ONE absolute deadline (S2-R2-005; S = C8_LANE_STOP_SECONDS, 25 s by
default, below Slurm's KillWait of 30 s): a lane's deadline for its run is 0.7 S (the run's session, its native worker
included, killed at 0.95 x 0.7 S = 0.665 S if still running, then reaped until 0.7 S), after which the lane removes its
scratch; the worker waits for its lanes until 0.836 S, then kills every lane still running, all of them before it waits
on any, reaps them until 0.88 S and keeps the last 0.12 S (3 s at the default; 8 s before KillWait) to remove any lane
scratch directory of its job left behind and exit 128+signal. A child not reaped by its deadline (delayed in I/O) is not
waited for longer.
"""
from __future__ import annotations
import argparse,json,math,os,re,shutil,signal,subprocess,sys,tempfile,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,Refuse,host_info,load,publish,scheduler_user,utc
EFFICIENCY=0.9;UNKNOWN_CLASS_FACTOR=1.5;MEM_FRACTION=0.85;DONE_LIST_SECONDS=60.
QUEUE_HEADER='# c8d3-lanes-queue'
HELD_REASON='launch failed requeued held'
STOP_SIGNALS=(signal.SIGTERM,signal.SIGINT,signal.SIGHUP);STOP_SECONDS=25.
# S2-R2-005, fractions of S = C8_LANE_STOP_SECONDS after the stop signal: a lane's deadline for its run; the last share of
# each drain kept for reaping the children it killed; the worker's cleanup reserve (scratch removal and exit) before S
LANE_STOP_FRACTION=0.7;REAP_FRACTION=0.05;CLEANUP_FRACTION=0.12

class Stopped(BaseException):
    """A stop signal reached a lane worker or a lane while it waited for its children (F7)."""
    def __init__(self,signum):super().__init__(f'stopped by signal {signum}');self.signum=signum

class StopGuard:
    """Stop-signal handling of a lane worker or a lane (F7, C62d's). The first SIGTERM, SIGINT or SIGHUP is recorded and
    forwarded as SIGTERM to every registered child that is still running; a later one is forwarded again. It unwinds
    (Stopped) only out of wait(), so a signal that arrives while a child is being started or a claim is being published
    is acted on at the next safe point (wait(), or a check of `signum`). The first signal's monotonic time `t0` is the
    origin of the shutdown deadline (drain). Installed only in the main thread; uninstall() restores the previous
    handlers."""
    def __init__(self):self.signum=None;self.t0=None;self.children=[];self.waiting=False;self.old={}
    def install(self):
        if threading.current_thread()is threading.main_thread():self.old={s:signal.signal(s,self._handler)for s in STOP_SIGNALS}
        return self
    def uninstall(self):
        for s,h in self.old.items():signal.signal(s,h)
        self.old={}
    def _handler(self,signum,frame):
        first=self.signum is None
        if first:self.signum=signum;self.t0=time.monotonic()
        self.forward()
        if first and self.waiting:raise Stopped(signum)
    def forward(self):
        for c in self.children:
            if c.poll()is None:
                try:c.send_signal(signal.SIGTERM)
                except OSError:pass
    def add(self,child):
        self.children.append(child)
        if self.signum is not None:self.forward()
        return child
    def wait(self,child)->int:
        """The child's exit status; Stopped when a stop signal arrived before or during the wait."""
        if self.signum is not None:raise Stopped(self.signum)
        self.waiting=True
        try:return child.wait()
        finally:self.waiting=False
    def drain(self,seconds:float,kill)->list:
        """One absolute deadline, `seconds` after the first stop signal (t0; S2-R2-005): wait for the registered children
        until the grace end (the deadline less REAP_FRACTION x seconds), then kill(child) EVERY one still running, all of
        them before waiting on any, then reap them until the deadline. Never waits past it: a killed child not reaped by
        then (delayed in I/O) is left behind. Returns the children that had to be killed."""
        s=max(0.,seconds);end=(self.t0 if self.t0 is not None else time.monotonic())+s;grace=end-REAP_FRACTION*s
        for c in self.children:
            try:c.wait(timeout=max(0.,grace-time.monotonic()))
            except subprocess.TimeoutExpired:pass
        killed=[c for c in self.children if c.poll()is None]
        for c in killed:kill(c)
        for c in killed:
            try:c.wait(timeout=max(0.,end-time.monotonic()))
            except subprocess.TimeoutExpired:pass
        return killed

def stop_seconds(env:dict)->float:
    v=env.get('C8_LANE_STOP_SECONDS',str(STOP_SECONDS))
    try:x=float(v)
    except ValueError:x=-1.
    if not 0<x<3600:raise Refuse(64,f'C8_LANE_STOP_SECONDS must be a number of seconds in (0, 3600) (got {v!r}); keep it below the site\'s KillWait')
    return x

def scratch_base(env:dict)->Path:return Path(env.get('C8_SCRATCH')or env.get('SLURM_TMPDIR')or env.get('TMPDIR')or'/tmp')
def lane_scratch_prefix(job:str)->str:return f'c8d3_lane_{job}_'

def kill_session(child)->None:
    """SIGKILL a run started in its own session, with every process of that session's group (its native worker)."""
    try:os.killpg(child.pid,signal.SIGKILL)
    except OSError:
        try:child.kill()
        except OSError:pass

def lanes_dir(run:Path)->Path:return Path(run)/'lanes'
def claim_path(run:Path,idx:int)->Path:return lanes_dir(run)/'claims'/f'{idx}.json'
def done_path(run:Path,idx:int)->Path:return lanes_dir(run)/'done'/str(idx)
def sysfs()->Path:return Path(os.environ.get('C8_SYSFS','/sys'))
def procfs()->Path:return Path(os.environ.get('C8_PROC','/proc'))

def _listdir(d:Path)->list[str]:
    try:return os.listdir(d)
    except FileNotFoundError:return []

def read_claims(run:Path)->list[dict]:
    out=[];d=lanes_dir(run)/'claims'
    for n in sorted(_listdir(d)):
        if not n.endswith('.json')or not n[:-5].isdigit():continue
        f=d/n
        try:c=json.loads(f.read_text());c['index']=int(n[:-5]);c['path']=str(f);out.append(c)
        except (OSError,ValueError):out.append({'index':int(n[:-5]),'path':str(f),'corrupt':True})
    return out

def failure_counts(run:Path,names=None)->dict:
    out={}
    for f in (names if names is not None else _listdir(lanes_dir(run)/'failures')):
        idx=f.split('.',1)[0]
        if idx.isdigit()and f.endswith('.json'):out[int(idx)]=out.get(int(idx),0)+1
    return out

def claims_summary(run:Path)->dict:
    """For production.py status: claims and failure records only (done markers are never read there, A-ORC-4)."""
    c=read_claims(run);f=failure_counts(run)
    return {'claims':len(c),'claimed':sorted(x['index']for x in c),'owners':sorted({str(x.get('job','?'))for x in c}),'failures':sum(f.values()),'failed':sorted(f)}

def claim(run:Path,idx:int,owner:dict)->bool:
    try:publish(claim_path(run,idx),json.dumps({**owner,'index':idx,'start_epoch':time.time()})+'\n');return True
    except FileExistsError:return False

def release(run:Path,idx:int)->None:
    try:claim_path(run,idx).unlink()
    except FileNotFoundError:pass

def publish_done(run:Path,idx:int,owner:dict)->bool:
    try:publish(done_path(run,idx),json.dumps({'index':idx,'job':owner.get('job'),'lane':owner.get('lane'),'utc':utc()})+'\n');return True
    except FileExistsError:return False

def invalidate_done(run:Path,idx:int,why:str)->bool:
    """Remove the done marker of an incomplete index and log it (lanes/done_invalidated.jsonl). True if one existed."""
    try:done_path(run,idx).unlink()
    except FileNotFoundError:return False
    with (lanes_dir(run)/'done_invalidated.jsonl').open('a')as f:f.write(json.dumps({'index':idx,'utc':utc(),'reason':why,'pid':os.getpid()})+'\n')
    return True

def parse_timeleft(text:str):
    """Seconds from squeue %L ('[days-]hours:minutes:seconds', 'minutes:seconds'); math.inf for 'UNLIMITED'; None when
    unparseable ('INVALID', empty)."""
    t=text.strip()
    if t=='UNLIMITED':return math.inf
    m=re.fullmatch(r'(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)',t)
    if not m:return None
    d,h,mi,s=(int(x)if x else 0 for x in m.groups());return ((d*24+h)*60+mi)*60+s

def lane_refusal(m:dict)->str|None:
    """Why lane mode refuses a plan (D.5, D.9, HD11), or None."""
    if m.get('plan_role')!='campaign':
        return (f'this plan has --plan-role {m.get("plan_role")!r}: lane mode runs only role campaign on an identity-matching measured model (HD11); '
                'validation and the other non-measured roles (cost_sweep, cost_refresh, flag_check) run in array mode or in-process (D.5)')
    if m.get('cost_basis')!='measured'or any(j.get('est_core_seconds')is None for j in m['jobs']):
        return f'this plan has no measured per-index time estimates (cost basis {m.get("cost_basis")!r}); lane mode needs them for its time guard (D.5)'
    return None

def queue_entries(run:Path,m:dict,prog:dict)->list[tuple[int,float]]:
    why=lane_refusal(m)
    if why:raise Refuse(65,why)
    todo=[(j['id'],float(j['est_core_seconds']))for j in m['jobs']if prog[j['id']][0]<prog[j['id']][1]]
    return sorted(todo,key=lambda t:(-t[1],t[0]))

def write_queue(run:Path,entries,generation:int|None=None)->tuple[Path,int]:
    q=lanes_dir(run)/'queue.txt';q.parent.mkdir(parents=True,exist_ok=True)
    gen=generation if generation is not None else time.time_ns()
    fd,tmp=tempfile.mkstemp(prefix='queue.txt.tmp.',dir=q.parent)
    with os.fdopen(fd,'w')as f:
        f.write(f'{QUEUE_HEADER} generation={gen} built={utc()} entries={len(entries)}\n'+''.join(f'{i} {e:.1f}\n'for i,e in entries));f.flush();os.fsync(f.fileno())
    os.replace(tmp,q);return q,gen

def parse_queue_text(text:str)->tuple[int|None,list[tuple[int,float]]]:
    gen=None;entries=[]
    for line in text.splitlines():
        if line.startswith('#'):
            m=re.search(r'generation=(\d+)',line)
            if m:gen=int(m.group(1))
            continue
        if line.strip():a,b=line.split();entries.append((int(a),float(b)))
    return gen,entries

def read_queue(run:Path)->list[tuple[int,float]]:
    q=lanes_dir(run)/'queue.txt'
    return parse_queue_text(q.read_text())[1]if q.exists()else[]

def rebuild_queue(run:Path,m:dict)->tuple[list,list]:
    """The queue rebuild (caller holds the session lock): completeness from the checkpoint blocks (production.job_progress),
    the done marker of every incomplete index removed and logged, the incomplete indices written with a new generation."""
    import production as prod
    prog=prod.job_progress(run,m);entries=queue_entries(run,m,prog);inc={i for i,_ in entries};bad=[]
    for n in _listdir(lanes_dir(run)/'done'):
        if n.isdigit()and int(n)in inc and invalidate_done(run,int(n),'queue rebuild: checkpoint blocks missing'):bad.append(int(n))
    write_queue(run,entries);return entries,sorted(bad)

def stale_decision(run:Path,queue_text:str,snapshot_epoch:float,margin:float=300.)->dict:
    """Classify every claim by its owner job in a squeue snapshot ('%200k|%K|%T|%i', -r): keep (live), release (terminal,
    or absent from squeue and claimed before the snapshot), or uncertain (refuse)."""
    import production as prod
    states={}
    for line in queue_text.splitlines():
        parts=[x.strip()for x in line.split('|')]
        if len(parts)==4:states[parts[3]]=parts[2]
    keep=[];rel=[];unc=[]
    for c in read_claims(run):
        job=str(c.get('job',''))
        if c.get('corrupt')or not job:unc.append((c['index'],'unreadable claim'));continue
        st=states.get(job)
        if st in prod.LIVE_STATES:keep.append((c['index'],job,st))
        elif st in prod.TERMINAL_STATES:rel.append((c['index'],job,st))
        elif st is None:
            if float(c.get('start_epoch',snapshot_epoch))<snapshot_epoch-margin:rel.append((c['index'],job,'absent'))
            else:unc.append((c['index'],f'job {job} absent from squeue but claimed within {margin:.0f} s of the snapshot'))
        else:unc.append((c['index'],f'job {job} is {st}'))
    return {'keep':keep,'release':rel,'uncertain':unc}

def release_stale(run:Path,queue_text:str,snapshot_epoch:float,dry_run=False)->dict:
    d=stale_decision(run,queue_text,snapshot_epoch)
    if d['uncertain']:raise Refuse(69,'lane claims in an uncertain state, nothing released: '+'; '.join(f'index {i}: {why}'for i,why in d['uncertain'])+'. Rerun later')
    if not dry_run:
        for idx,_,_ in d['release']:release(run,idx)
    return d

def snapshot(env:dict)->tuple[str,float]:
    """The claim-owner snapshot of the real uid's jobs (never $USER): 'squeue --all --states=all -u <user> -h -r'."""
    e={k:v for k,v in env.items()if not k.startswith('SQUEUE_')};t=time.time()
    try:cp=subprocess.run(['squeue','--all','--states=all','-u',scheduler_user(),'-h','-r','-o','%200k|%K|%T|%i'],capture_output=True,text=True,env=e,timeout=60)
    except (OSError,subprocess.SubprocessError)as x:raise Refuse(69,f'squeue failed ({x}); job state unknown, nothing changed')
    if cp.returncode:raise Refuse(69,'squeue failed; job state unknown, nothing changed')
    return cp.stdout,t

def held_jobs(queue_text:str)->list[dict]:
    """c8d3- jobs pending with the reason `launch failed requeued held` (F40) in a '%i|%T|%r|%j' snapshot (D.9)."""
    out=[]
    for line in queue_text.splitlines():
        p=[x.strip()for x in line.split('|')]
        if len(p)>=4 and p[3].startswith('c8d3-')and p[1]in('PENDING','REQUEUE_HOLD','SPECIAL_EXIT')and HELD_REASON in p[2].lower():out.append({'jobid':p[0],'state':p[1],'reason':p[2],'name':p[3]})
    return out

def session_lock(command:str):
    """The C8 session lock ($C8_ROOT/locks/c8d3.lock, tools/ledger.py), which replaces the inherited campaign lock
    for `queue` and `release-stale` (D.11 "Who takes it"); 75 while another process holds it."""
    import ledger
    return ledger.SessionLock(ledger.Settings(dict(os.environ)),command)

def cmd_queue(a):
    import production as prod
    run=a.directory.resolve();m,_,_,_=prod.verify_base(run,check_executable=False)
    with session_lock('lanes queue'):entries,bad=rebuild_queue(run,m)
    print(json.dumps({'queue':str(lanes_dir(run)/'queue.txt'),'incomplete':len(entries),'estimated_core_hours':round(sum(e for _,e in entries)/3600,2),'done_markers_invalidated':bad}))

def cmd_release(a):
    import production as prod
    run=a.directory.resolve();prod.verify_base(run,check_executable=False)
    with session_lock('lanes release-stale'):
        text,t=(Path(a.queue).read_text(),Path(a.queue).stat().st_mtime)if a.queue else snapshot(dict(os.environ))
        d=release_stale(run,text,t,a.dry_run)
    print(json.dumps({'dry_run':a.dry_run,**d}))

# ---------------------------------------------------------------- CPU sets: physical cores, NUMA nodes, sockets
def topology(c:int)->tuple[int,int]:
    """(socket, physical core) of logical CPU c from sysfs; (0, c) when unavailable."""
    base=sysfs()/f'devices/system/cpu/cpu{c}/topology'
    try:return int((base/'physical_package_id').read_text()),int((base/'core_id').read_text())
    except (OSError,ValueError):return 0,c

def parse_cpulist(text:str)->list[int]:
    out=[]
    for part in text.strip().split(','):
        if not part:continue
        lo,_,hi=part.partition('-');out.extend(range(int(lo),int(hi or lo)+1))
    return out

def numa_nodes()->dict[int,list[int]]:
    out={};d=sysfs()/'devices/system/node'
    for p in sorted(d.glob('node[0-9]*'),key=lambda x:int(x.name[4:]))if d.is_dir()else[]:
        try:out[int(p.name[4:])]=parse_cpulist((p/'cpulist').read_text())
        except (OSError,ValueError):continue
    return out

def cpu_vendor()->str:
    try:return next((l for l in (procfs()/'cpuinfo').read_text().splitlines()if l.startswith('vendor_id')),'')
    except OSError:return ''

def physical(cpus:list[int],topo=topology)->list[tuple[tuple[int,int],int]]:
    """One logical CPU per physical core (SMT siblings are left idle), as ((socket, core), cpu), socket-major."""
    seen={}
    for c in sorted(cpus):
        key=topo(c)
        if key not in seen:seen[key]=c
    return sorted(seen.items())

def equal_parts(cores:list[int],n:int)->list[list[int]]:
    if n<1 or n>len(cores):raise Refuse(64,f'C8_LANES={n} must be between 1 and the {len(cores)} available cores')
    k,r=divmod(len(cores),n);out=[];i=0
    for j in range(n):w=k+(j<r);out.append(cores[i:i+w]);i+=w
    return out

LANES_RE=re.compile(r'numa(?::([1-9][0-9]*))?|socket|[1-9][0-9]*')

def cpu_lanes(cpus:list[int],spec:str|None,topo=topology,vendor:str|None=None,nodes:dict|None=None,drill:bool=False)->list[list[int]]:
    """Lanes of PHYSICAL cores of the job's CPU set (D.9): 'numa' (one lane per NUMA node from
    /sys/devices/system/node/node*/cpulist intersected with the job's affinity; the default on AMD), 'numa:k' (k adjacent
    NUMA nodes per lane), 'socket' (one per socket; the default elsewhere), or n equal contiguous parts. Drill mode
    splits the job's own affinity set into n parts (default 1), whatever the NUMA layout."""
    cores=physical(cpus,topo)
    if spec is not None and not LANES_RE.fullmatch(spec):raise Refuse(64,f'C8_LANES={spec!r} must be numa, numa:<k>, socket or a positive integer')
    if drill:
        if spec and not spec.isdigit():raise Refuse(64,'drill mode splits the job\'s CPUs into C8_LANES equal parts (an integer)')
        return equal_parts([c for _,c in cores],int(spec)if spec else 1)
    if spec is None:spec='numa'if 'AMD'in(vendor if vendor is not None else cpu_vendor())else'socket'
    if spec.isdigit():return equal_parts([c for _,c in cores],int(spec))
    if spec=='socket':
        sockets={}
        for (s,_),c in cores:sockets.setdefault(s,[]).append(c)
        return [sockets[s]for s in sorted(sockets)]
    k=int(spec.split(':')[1])if ':'in spec else 1
    nodes=numa_nodes()if nodes is None else nodes;where={c:n for n,cl in nodes.items()for c in cl};per={}
    for _,c in cores:per.setdefault(where.get(c,-1),[]).append(c)
    order=sorted(per);out=[]
    for i in range(0,len(order),k):out.append(sorted(c for n in order[i:i+k]for c in per[n]))
    return out

def cgroup_memory_limit()->int|None:
    """The job's memory limit in bytes: the cgroup's memory.max (v2) or memory.limit_in_bytes (v1) of this process,
    walking up to the first finite limit; None when no limit is visible."""
    try:lines=(procfs()/'self/cgroup').read_text().splitlines()
    except OSError:return None
    best=None
    for line in lines:
        try:hid,ctrl,path=line.split(':',2)
        except ValueError:continue
        if ctrl=='':cands=[(sysfs()/'fs/cgroup'/path.lstrip('/'),'memory.max')]
        elif 'memory'in ctrl.split(','):cands=[(sysfs()/'fs/cgroup/memory'/path.lstrip('/'),'memory.limit_in_bytes')]
        else:continue
        for base,name in cands:
            p=base
            while True:
                try:
                    v=(p/name).read_text().strip()
                    if v and v!='max'and int(v)<2**60:best=int(v)if best is None else min(best,int(v));break
                except (OSError,ValueError):pass
                if p==p.parent or p==sysfs()/'fs/cgroup'or p==sysfs()/'fs/cgroup/memory':break
                p=p.parent
    return best

def memory_limit(env:dict)->tuple[int|None,str]:
    lim=cgroup_memory_limit()
    if lim is not None:return lim,'cgroup'
    v=env.get('SLURM_MEM_PER_NODE','')
    if v.isdigit():return int(v)*2**20,'SLURM_MEM_PER_NODE'
    return None,'none'

def memory_guard(nlanes:int,peak:int,limit:int|None)->int:
    """Lanes that fit: nlanes, or fewer when nlanes x peak > 0.85 x limit; Refuse(64) if not even one fits (D.9)."""
    if limit is None or peak<=0:return nlanes
    fit=int(MEM_FRACTION*limit//peak)
    if fit<1:raise Refuse(64,f'one lane needs about {peak/2**30:.1f} GiB (largest est_peak_bytes) > {MEM_FRACTION} x the job memory limit {limit/2**30:.1f} GiB; '
                             'raise C8_LANE_MEM (or --mem) or re-plan with smaller blocks (--checkpoint-tasks, --block-seconds)')
    return min(nlanes,fit)

def class_factor(cost_model:dict|None,cpu:str|None,campaign:str,sector:str,L:int)->float:
    """CPU-class factor of the lane deadline: 1 on the cost model's reference CPU model, the measured factor of the
    host's class (per campaign, sector and L >= 6; loops below 6 take the class's L6 factor), else 1.5 (unknown). Only
    the campaign's identity-matching cost_model.json is read (never a scheduling basis, D.5)."""
    if not cost_model or not cpu:return UNKNOWN_CLASS_FACTOR
    cpu=' '.join(cpu.split());ref={' '.join(str(x).split())for x in ([cost_model.get('cpu_model')]+list(cost_model.get('cpu_models')or[]))if x}
    if cpu in ref:return 1.0
    t=(cost_model.get('cpu_class_factors')or{}).get(cpu)
    if not t:return UNKNOWN_CLASS_FACTOR
    row=((t.get(campaign)or{}).get(sector)or{})
    v=row.get(str(L))or row.get('6')
    if v is None:vals=[float(x)for c in t.values()for s in c.values()for x in s.values()];v=max(vals)if vals else UNKNOWN_CLASS_FACTOR
    return float(v)

def remaining_seconds(job:str,env:dict)->tuple[float,str]:
    """(seconds left, source): Slurm's own answer (squeue %L, inherited SQUEUE_* filters removed; C7I-15). Under
    C8_TIME_POLICY=unlimited an UNLIMITED job has no deadline (inf); under the finite policy UNLIMITED or no answer falls
    back to C8_LANE_SECONDS (C7I-16), else refuses (69)."""
    e={k:v for k,v in env.items()if not k.startswith('SQUEUE_')};policy=env.get('C8_TIME_POLICY')or'finite'
    if policy not in('finite','unlimited'):raise Refuse(64,f'C8_TIME_POLICY must be finite or unlimited (got {policy!r})')
    try:cp=subprocess.run(['squeue','--all','-h','-j',job,'-o','%L'],capture_output=True,text=True,timeout=60,env=e)
    except (OSError,subprocess.SubprocessError):cp=None
    left=parse_timeleft(cp.stdout)if cp and cp.returncode==0 else None
    if left==math.inf and policy=='unlimited':return math.inf,'squeue UNLIMITED (C8_TIME_POLICY=unlimited: no deadline)'
    if left is not None and left!=math.inf:return float(left),'squeue'
    if env.get('C8_LANE_SECONDS'):
        v=env['C8_LANE_SECONDS']
        if not v.isdigit():raise Refuse(64,'C8_LANE_SECONDS must be a non-negative integer')
        return float(v),'C8_LANE_SECONDS (squeue gave no finite remaining time)'
    said=repr(cp.stdout.strip())if cp is not None and cp.returncode==0 else'no answer (squeue failed)'
    raise Refuse(69,f'cannot read a finite remaining time of job {job} (squeue %L: {said}); set C8_LANE_SECONDS as a fallback, '
                    'or C8_TIME_POLICY=unlimited where the site has no wall limit')

def cmd_worker(a):
    import production as prod
    run=a.directory.resolve();env=dict(os.environ);m,_,_,_=prod.verify_base(run)
    why=lane_refusal(m)
    if why:raise Refuse(65,why)
    job=env.get('SLURM_JOB_ID')or env.get('C8_LANE_JOB_ID')
    if not job:raise Refuse(64,'lane workers run inside a Slurm job (SLURM_JOB_ID)')
    restart=env.get('SLURM_RESTART_COUNT','0')
    drill=env.get('C8_LANE_DRILL')=='1'
    if drill and not m['test_only']:raise Refuse(64,'C8_LANE_DRILL=1 is for test-only plans only (the lane drills)')
    left,source=remaining_seconds(job,env);deadline=time.time()+left
    for c in read_claims(run):   # requeue safety: claims of this job id were left by an earlier incarnation of this job
        if str(c.get('job'))==job:release(run,c['index']);print(f'released own stale claim {c["index"]} (job {job}, restart {c.get("restart")}; now restart {restart})',flush=True)
    try:cpus=sorted(os.sched_getaffinity(0))
    except AttributeError:cpus=list(range(os.cpu_count()or 1))
    spec=env.get('C8_LANES')or None
    plan=cpu_lanes(cpus,spec,drill=drill);T=m['checkpoint_tasks']
    if max(len(l)for l in plan)>T:
        if spec and spec.isdigit():raise Refuse(64,f'C8_LANES={spec} gives lanes of up to {max(len(l)for l in plan)} cores, more than the plan\'s checkpoint_tasks={T}; '
                                                f'use C8_LANES >= {-(-sum(len(l)for l in plan)//T)} or re-plan with a larger --checkpoint-tasks')
        plan=[part for lane in plan for part in equal_parts(lane,-(-len(lane)//T))];print(f'C8 lanes: lanes split to at most checkpoint_tasks={T} cores',flush=True)
    q=read_queue(run);incomplete=[i for i,_ in q]if q else[j['id']for j in m['jobs']]
    peak=max((m['jobs'][i]['est_peak_bytes']for i in incomplete),default=0)
    limit,lsrc=memory_limit(env);n=memory_guard(len(plan),peak,limit)
    if n<len(plan):print(f'C8 lanes: memory guard: {len(plan)} lanes x {peak/2**30:.1f} GiB > {MEM_FRACTION} x {limit/2**30:.1f} GiB ({lsrc}); running {n} lanes',flush=True);plan=plan[:n]
    host=host_info();wait=stop_seconds(env)
    print(f'C8 lanes: job {job} (restart {restart}) on {host["node"]} ({host["cpu_model"]}); {len(plan)} lane(s) of {[len(x)for x in plan]} CPUs; '
          f'{"no deadline" if left==math.inf else f"{int(left)} s left"} ({source}); memory limit {limit and round(limit/2**30,1)} GiB ({lsrc}), largest index peak {peak/2**30:.2f} GiB',flush=True)
    guard=StopGuard().install()   # F7: a scancel or the wall limit reaches the worker (lane_worker.sh execs it); forwarded to the lanes
    try:
        for k,c in enumerate(plan):
            if guard.signum is not None:break
            guard.add(subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'lane',str(run),'--lane',str(k),'--cpus',','.join(map(str,c)),
                                        '--deadline','inf'if left==math.inf else repr(deadline),'--job',job,'--restart',restart,'--stop-seconds',repr(wait)]))
        codes=[guard.wait(p)for p in guard.children]
    except Stopped as st:
        reap=(1-CLEANUP_FRACTION)*wait;at=(1-REAP_FRACTION)*reap   # S2-R2-005: one deadline from the signal; the last CLEANUP_FRACTION x wait is the cleanup's
        print(f'C8 lanes: job {job} stopping on signal {st.signum}: SIGTERM forwarded to {len(guard.children)} lane(s); waiting at most {wait:g} s in all '
              f'(lanes still running killed at {at:g} s, reaped until {reap:g} s, then {wait-reap:g} s for cleanup)',flush=True)
        killed=guard.drain(reap,lambda c:c.kill())
        left_over=sorted(scratch_base(env).glob(lane_scratch_prefix(job)+'*'))
        for x in left_over:shutil.rmtree(x,ignore_errors=True)
        print(f'C8 lanes: job {job} stopped (signal {st.signum}); lane exit codes {[c.returncode for c in guard.children]}'+
              (f'; {len(killed)} lane(s) killed at {at:g} s'if killed else'')+(f'; removed {len(left_over)} lane scratch director(ies) left behind'if left_over else''),flush=True)
        return 128+st.signum
    finally:guard.uninstall()
    print(f'C8 lanes: job {job} done, lane exit codes {codes}',flush=True)
    return 0 if all(c==0 for c in codes)else 3

class LaneView:
    """A lane's in-memory view, refreshed once per scan with a bounded number of filesystem calls: one stat of queue.txt
    (re-read on a changed inode, mtime or size), one listing each of claims/ and failures/, and a listing of done/ at
    most every 60 s and at once on a new queue generation (the done set is replaced, never merged)."""
    def __init__(self,run:Path,clock=time.time):
        self.run=run;self.q=lanes_dir(run)/'queue.txt';self.key=None;self.gen=None;self.entries=[];self.done=set();self.done_t=-math.inf;self.clock=clock
        self.claimed=set();self.fails={}
    def refresh(self):
        now=self.clock()
        try:st=os.stat(self.q);key=(st.st_ino,st.st_mtime_ns,st.st_size)
        except FileNotFoundError:key=None
        newgen=False
        if key!=self.key:
            gen,entries=parse_queue_text(self.q.read_text())if key else(None,[])
            newgen=gen!=self.gen;self.gen=gen;self.entries=entries;self.key=key
        if newgen or now-self.done_t>=DONE_LIST_SECONDS:
            self.done={int(n)for n in _listdir(lanes_dir(self.run)/'done')if n.isdigit()};self.done_t=now
        self.claimed={int(n[:-5])for n in _listdir(lanes_dir(self.run)/'claims')if n.endswith('.json')and n[:-5].isdigit()}
        self.fails=failure_counts(self.run,_listdir(lanes_dir(self.run)/'failures'))
    def candidates(self,maxfail:int):
        for idx,est in self.entries:
            if idx in self.done or idx in self.claimed or self.fails.get(idx,0)>=maxfail:continue
            yield idx,est

def blocks_present(run:Path,j:dict)->bool:
    import production as prod
    d=Path(run)/'groups'/j['group']/'checkpoints'
    return all((d/f'{prod.block_name(j["shard"],k)}.json').exists()for k in range(j['blocks']))

def attempt(run:Path,m:dict,idx:int,est:float,owner:dict,view,T:int,scratch:Path,child:dict,logs:Path,job:str,restart:str,lane,guard=None,stop_wait:float=20.)->str|None:
    """One claimed index (the claim is held): a complete index gets its done marker; otherwise a stale marker of it is
    removed and logged, `production.py run --index` runs, and a done marker or a failure record follows. Returns
    'done', 'complete', 'failed' (the claim is released by the caller). The run is started in its own session and
    registered with the lane's StopGuard (F7): on a stop signal it gets SIGTERM and has until stop_wait seconds after the
    lane's signal (its session killed at 0.95 x that, then reaped until it; S2-R2-005); Stopped is raised with the claim
    held (left stale) and no failure record."""
    j=m['jobs'][idx];g=guard if guard is not None else StopGuard()
    if blocks_present(run,j):publish_done(run,idx,owner);view.done.add(idx);return 'complete'
    if invalidate_done(run,idx,f'claim holder (job {job}, lane {lane}): checkpoint blocks missing'):view.done.discard(idx)
    tag=f'{idx}.{job}.{restart}.{lane}.{time.time_ns()}';log=logs/f'idx{tag}.log'
    with log.open('x')as fh:
        proc=g.add(subprocess.Popen([sys.executable,'-B',str(ROOT/'tools/production.py'),'run',str(run),'--index',str(idx),'--threads',str(T),'--scratch',str(scratch)],
                                    stdout=fh,stderr=subprocess.STDOUT,env=child,start_new_session=True))
        try:rc=g.wait(proc)
        except Stopped as st:
            killed=g.drain(stop_wait,kill_session)
            print(f'lane {lane}: index {idx} stopped by signal {st.signum} (run exit {proc.returncode}'+(f', its session killed at {(1-REAP_FRACTION)*stop_wait:g} s'if killed else'')+
                  f'); claim left for release-stale; log {log.name}',flush=True)
            raise
        finally:g.children.remove(proc)
    if rc==0 and blocks_present(run,j):publish_done(run,idx,owner);view.done.add(idx);return 'done'
    publish(lanes_dir(run)/'failures'/f'{tag}.json',json.dumps({**owner,'index':idx,'exit_code':rc,'log':str(log),'end_epoch':time.time()})+'\n')
    print(f'lane {lane}: index {idx} FAILED (exit {rc}); log {log}',flush=True);return 'failed'

def cmd_lane(a):
    run=a.directory.resolve();env=dict(os.environ);m=load(run/'manifest.json');cpus=[int(x)for x in a.cpus.split(',')];T=len(cpus)
    why=lane_refusal(m)
    if why:raise Refuse(65,why)
    cm=load(run/'cost_model.json')if m.get('cost_model_sha256')and (run/'cost_model.json').exists()else None
    try:os.sched_setaffinity(0,cpus)
    except (AttributeError,OSError):pass
    def num(name,default,kind=float):
        try:return kind(env.get(name,default))
        except ValueError:raise Refuse(64,f'{name} must be a number')
    safety=num('C8_LANE_SAFETY',1.5);margin=num('C8_LANE_MARGIN',300.);maxfail=num('C8_LANE_MAX_FAILURES',2,int);maxrow=num('C8_LANE_MAX_CONSECUTIVE_FAILURES',3,int)
    deadline=math.inf if a.deadline=='inf'else float(a.deadline);inrow=0
    given=getattr(a,'stop_seconds',None);wait=LANE_STOP_FRACTION*(float(given)if given is not None else stop_seconds(env))
    guard=StopGuard().install()   # F7: before the scratch exists, so that a stop signal can never leave it behind
    scratch=Path(tempfile.mkdtemp(prefix=f'{lane_scratch_prefix(a.job)}{a.lane}_',dir=scratch_base(env)))
    child={**env,'OMP_NUM_THREADS':str(T),'OMP_PROC_BIND':'close','OMP_PLACES':'cores','OMP_DYNAMIC':'FALSE','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    host=host_info();owner={'job':a.job,'restart':a.restart,'lane':a.lane,**host,'pid':os.getpid(),'threads':T,'user':scheduler_user()};ran=0;failed=0;stopped=None
    logs=lanes_dir(run)/'logs';logs.mkdir(parents=True,exist_ok=True);(lanes_dir(run)/'done').mkdir(exist_ok=True);(lanes_dir(run)/'claims').mkdir(exist_ok=True)
    view=LaneView(run)
    try:
        while guard.signum is None:
            view.refresh();started=False
            for idx,est in view.candidates(maxfail):
                j=m['jobs'][idx];f=class_factor(cm,host['cpu_model'],j['campaign'],j['sector'],j['L'])
                need=est*f/(T*EFFICIENCY)*safety+margin
                if need>deadline-time.time():continue
                if not claim(run,idx,owner):continue
                if guard.signum is not None:release(run,idx);break   # stopped before anything ran: the claim is released
                t0=time.time()
                try:r=attempt(run,m,idx,est,owner,view,T,scratch,child,logs,a.job,a.restart,a.lane,guard,wait)
                except Stopped as st:stopped=st.signum;break   # the claim stays (stale) and no failure record is written (F7)
                if r=='done':ran+=1;inrow=0;print(f'lane {a.lane}: index {idx} done in {time.time()-t0:.0f} s (estimate {est*f/(T*EFFICIENCY):.0f} s, class factor {f:g})',flush=True)
                elif r=='failed':inrow+=1;failed+=1
                release(run,idx);started=True;break
            if stopped is not None or not started:break
            if inrow>=maxrow:print(f'lane {a.lane}: stopping after {inrow} consecutive failures (C8_LANE_MAX_CONSECUTIVE_FAILURES); see lanes/failures/',flush=True);break
    finally:
        shutil.rmtree(scratch,ignore_errors=True);guard.uninstall()
    sig=stopped if stopped is not None else guard.signum
    if sig is not None:
        print(f'lane {a.lane}: stopped by signal {sig}, {ran} indices run, {failed} failed; scratch removed',flush=True);return 128+sig
    print(f'lane {a.lane}: finished, {ran} indices run, {failed} failed',flush=True)
    return 0 if failed==0 else 3

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('queue');q.add_argument('directory',type=Path);q.set_defaults(func=cmd_queue)
    q=s.add_parser('release-stale');q.add_argument('directory',type=Path);q.add_argument('--dry-run',action='store_true');q.add_argument('--queue',help='squeue snapshot file (tests); default: run squeue');q.set_defaults(func=cmd_release)
    q=s.add_parser('worker');q.add_argument('directory',type=Path);q.set_defaults(func=cmd_worker)
    q=s.add_parser('lane');q.add_argument('directory',type=Path);q.add_argument('--lane',type=int,required=True);q.add_argument('--cpus',required=True)
    q.add_argument('--deadline',required=True);q.add_argument('--job',required=True);q.add_argument('--restart',default='0')
    q.add_argument('--stop-seconds',help='the worker\'s C8_LANE_STOP_SECONDS (default: the environment\'s); the lane\'s run has until 0.7 x that after the signal');q.set_defaults(func=cmd_lane)
    a=p.parse_args(argv)
    try:return a.func(a)or 0
    except Refuse as r:print('C8: '+str(r),file=sys.stderr);return r.code
    except ValueError as e:print(f'C8: {e}',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
