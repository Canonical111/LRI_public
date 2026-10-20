#!/usr/bin/env python3
"""Lane runner for extension batches on whole-node clusters (symmetry; amendment A1, docs/EXTENSION_A1.md).

A queue directory holds order.json: the planned elements {batch, label, index, cost} in processing order (batch by
batch, largest predicted cost first), written by `lane8.py queue`. Workers (one per CPU set, several per node) own
work through numbered ATTEMPT files, published atomically (temporary file, fsync, no-clobber hard link in the same
directory, as campaign.py publishes checkpoints; flock is node-local on symmetry's BeeGFS and is not used):
  claims/<element>.<n>   attempt n of an element; its mtime is a heartbeat refreshed while the attempt runs
  failed/<element>.<n>   attempt n ended with an error (a signal kill records nothing: the attempt just goes stale)
  done/<element>         the element is complete
  merge/<batch>.<n>, merge/<batch>.<n>.failed, merge/<batch>.ok   the same scheme for merging a finished batch
The current owner of an element is its highest attempt. A worker resumes its own current attempts (a requeued Slurm
job keeps its job id; the slot identifies the worker), then walks the queue IN ORDER and, at the first element that
needs work, claims it (no attempt yet), retries it (current attempt failed, fewer than MAX_FAILURES failures) or takes
it over (current attempt stale: heartbeat older than STALE_SECONDS, or squeue answered and the owning job is not
RUNNING; a failed squeue query never counts as gone). Taking over creates attempt n+1, so ownership moves and the
old owner never resumes it. Earlier batches are therefore always recovered before later work starts.
Each element is `production8.py run BATCH --index I` of the frozen production tools: committed checkpoints are
validated and skipped, so a re-run resumes, and a concurrent duplicate is published once and never counted twice.
Merges are deterministic and no-clobber (identical outputs are verified), so a duplicate merge is harmless too.
A worker that receives SIGTERM records no failure for the interrupted attempt (the frozen tools report a killed child
as exit 2, so the lane decides from the signal it received itself). A wave deadline (deadline.json, published once before submission) is enforced by every worker before each claim,
like STOP: after it, workers finish their current element, reconcile merges and exit.
When nothing is claimable but unfinished elements or pending merges are held by other workers, a worker waits and
rescans (so a dead sibling's attempt is taken over once stale) until all work is done or abandoned, STOP, or a
signal. A worker exits nonzero when it leaves abandoned
elements (MAX_FAILURES failed attempts) or a ready batch whose merge failed MAX_FAILURES times. `merge/<batch>.ok`
is trusted only while every campaign of the batch has merged/audit.json. Checkpoints of queue-managed batches are
quarantined only through `lane8.py quarantine`, which also invalidates the element's done marker and the batch's
merge marker, so the lane recomputes the checkpoint and re-merges. Explicit recovery (quarantine, invalidate) refuses
to run while any lane job of the user exists (squeue must answer), so no active writer can republish a stale marker.
After the wave, `lane8.py finalize` (merge only, exclusive access) merges every batch whose planned checkpoints are all
present, including one whose last done marker or merge was cut off by the end of the wave.
Scheduling changes only which worker computes an element, never the samples.
"""
from __future__ import annotations
import argparse, json, os, re, signal, socket, subprocess, sys, tempfile, threading, time, uuid
from pathlib import Path
MAX_FAILURES=3;STALE_SECONDS=1800;HEARTBEAT_SECONDS=300;WAIT_SECONDS=300
JOB_PREFIX='c8x-' # every Slurm job of this package on symmetry (lane, plan, smoke, recheck, stop, finalize); other C8
                  # packages (e.g. C8(3), c8d3-*) write other directories and are not writers of these batches
DIRS=('claims','done','failed','merge','logs','invalidated')
TERMINATING=threading.Event() # set by SIGTERM/SIGINT: Slurm signals every process of the job at wall time, preemption or scancel

def on_signal(signum,frame):TERMINATING.set()

def now()->str:return time.strftime('%Y-%m-%dT%H:%M:%S%z')

def publish(path:Path,obj:dict)->bool:
    """Atomic no-clobber publish of complete JSON; False when path already exists."""
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.tmp.',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:f.write(json.dumps(obj)+'\n');f.flush();os.fsync(f.fileno())
        try:os.link(tmp,path)
        except FileExistsError:return False
        return True
    finally:os.unlink(tmp)

def readj(path:Path)->dict|None:
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return None

def age(path:Path)->float:
    try:return time.time()-path.stat().st_mtime
    except OSError:return float('inf')

class Heartbeat:
    """Refresh a file's mtime every HEARTBEAT_SECONDS while a subprocess runs."""
    def __init__(self,path:Path):self.path=path;self.stop=threading.Event();self.t=threading.Thread(target=self.beat,daemon=True)
    def beat(self):
        while not self.stop.wait(HEARTBEAT_SECONDS):
            try:os.utime(self.path)
            except OSError:pass
    def __enter__(self):self.t.start();return self
    def __exit__(self,*x):self.stop.set();self.t.join()

def squeue_jobs()->list|None:
    """[(job id, name, state)] of every job of this user in any state, from one squeue call with every SQUEUE_* filter
    variable removed from the environment; None (UNKNOWN) when the call fails or any line is malformed."""
    env={k:v for k,v in os.environ.items() if not k.startswith('SQUEUE_')}
    try:r=subprocess.run(['squeue','-h','-u',os.environ.get('USER',''),'-t','all','-o','%i|%j|%T'],capture_output=True,text=True,timeout=60,env=env)
    except (OSError,subprocess.TimeoutExpired):return None
    if r.returncode:return None
    out=[]
    for line in r.stdout.split('\n'):
        if not line.strip():continue
        t=line.split('|')
        if len(t)!=3 or not re.fullmatch(r'\d+(_\S+)?',t[0]) or not t[1] or not t[2]:return None
        out.append((t[0].split('_')[0],t[1],t[2]))
    return out

def job_states(me:dict)->dict|None:
    """{job id: state} of this user's jobs; None (UNKNOWN) when the query failed or, inside a Slurm job, when the listing
    does not even contain this worker's own running job."""
    jobs=squeue_jobs()
    if jobs is None:return None
    out={j:st for j,_,st in jobs}
    if me['job']!='local' and out.get(me['job'])!='RUNNING':return None
    return out

def deadline_passed(q:Path)->bool:
    """The wave's pre-registered deadline (deadline.json, published once before submission) has passed."""
    d=readj(q/'deadline.json')
    return bool(d) and time.time()>=float(d['epoch'])

class Queue:
    def __init__(self,q:Path):
        self.q=q.resolve();self.order=json.loads((self.q/'order.json').read_text())['elements']
        for d in DIRS:(self.q/d).mkdir(exist_ok=True)
        self.batches={}
        for e in self.order:self.batches.setdefault(e['label'],{'batch':e['batch'],'elements':[]})['elements'].append(self.key(e))
    @staticmethod
    def key(e:dict)->str:return f"{e['label']}_{int(e['index']):04d}"
    def index(self,sub:str)->tuple[dict,dict]:
        """({name: highest attempt}, {name: set of attempts with a .failed suffix or in failed/}) of claims/ or merge/."""
        top={};bad={}
        for f in os.listdir(self.q/sub):
            m=re.fullmatch(r'(.+)\.(\d+)(\.failed)?',f)
            if not m or '.tmp.' in f:continue
            n=int(m.group(2))
            if m.group(3):bad.setdefault(m.group(1),set()).add(n)
            else:top[m.group(1)]=max(n,top.get(m.group(1),-1))
        if sub=='claims':
            for f in os.listdir(self.q/'failed'):
                m=re.fullmatch(r'(.+)\.(\d+)',f)
                if m:bad.setdefault(m.group(1),set()).add(int(m.group(2)))
        return top,bad
    def done(self)->set:return {f for f in os.listdir(self.q/'done') if '.tmp.' not in f}

def mine(c:dict|None,me:dict)->bool:return bool(c) and str(c.get('job'))==me['job'] and c.get('slot')==me['slot']

def stale(path:Path,c:dict|None,states:dict|None)->bool:
    if age(path)>STALE_SECONDS:return True # no heartbeat (dead worker, or an unreadable attempt left behind)
    if c is None or states is None:return False
    return states.get(str(c.get('job')))!='RUNNING' # squeue answered: the owner job is gone or not running

def decide(top:dict,bad:dict,name:str,path_of,me:dict,states:dict|None):
    """Next attempt number for `name` and how, or None when it is in progress elsewhere or abandoned."""
    if name not in top:return (0,'claim') if len(bad.get(name,()))<MAX_FAILURES else None
    n=top[name];p=path_of(n);c=readj(p)
    if c and c.get('how')=='reset':return (n+1,'claim') # explicit recovery (invalidate/quarantine): fresh budget
    if n in bad.get(name,()):return (n+1,'retry') if len(bad[name])<MAX_FAILURES else None
    if mine(c,me):return (n,'resume')
    if stale(p,c,states):return (n+1,'takeover')
    return None

def closed(Q:Queue)->bool:return deadline_passed(Q.q) or (Q.q/'STOP').exists()

def next_element(Q:Queue,me:dict):
    if closed(Q):return None,None,None
    done=Q.done();top,bad=Q.index('claims');states=job_states(me);P=lambda k:(lambda n:Q.q/'claims'/f'{k}.{n}')
    if closed(Q):return None,None,None # the scheduler query can take up to a minute: recheck before any claim
    for e in Q.order: # own current attempts first (a restarted worker resumes what it held)
        k=Q.key(e)
        if k not in done and k in top and top[k] not in bad.get(k,()) and mine(readj(P(k)(top[k])),me):return e,top[k],'resume'
    for e in Q.order: # then the first element, in queue order, that needs work
        k=Q.key(e)
        if k in done:continue
        d=decide(top,bad,k,P(k),me,states)
        if d is None:continue
        n,how=d
        if closed(Q):return None,None,None
        if how=='resume' or publish(P(k)(n),{**me,'how':how,'time':now()}):return e,n,how
    return None,None,None

def run_tracked(cmd:list,log:Path,beat:Path)->int:
    with log.open('a') as f,Heartbeat(beat):
        f.write(f"{now()} {' '.join(cmd)}\n");f.flush()
        return subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode

def archive(Q:Queue,src:Path)->bool:
    """Move src into invalidated/ under a unique name; False when another process moved it first."""
    try:os.replace(src,Q.q/'invalidated'/f'{src.name}.{int(time.time())}.{os.getpid()}.{uuid.uuid4().hex[:8]}');return True
    except FileNotFoundError:return False

def batch_merged(Q:Queue,lab:str)->bool:
    """merge/<lab>.ok is trusted only while every campaign of the batch still has its merged audit."""
    ok=Q.q/'merge'/(lab+'.ok')
    if not ok.exists():return False
    b=Path(Q.batches[lab]['batch']);prod=json.loads((b/'production.json').read_text())
    if all((b/c/'merged'/'audit.json').is_file() for c in prod['campaigns']):return True
    if archive(Q,ok):print(now(),'merge marker of',lab,'invalidated: audit missing',flush=True)
    return False

def reconcile_merges(Q:Queue,a,me:dict)->dict:
    """Merge every batch whose elements are all done and that is not merged yet, retrying failed merges up to
    MAX_FAILURES. Returns {label: 'pending'|'unresolved'} for ready batches left unmerged: pending only while another
    worker's live attempt exists; unresolved when MAX_FAILURES attempts failed."""
    left={}
    if (Q.q/'MAINTENANCE').exists():return {lab:'pending' for lab in Q.batches if not batch_merged(Q,lab)} # recovery in progress
    for lab,b in Q.batches.items():
        while True:
            done=Q.done()
            if not all(k in done for k in b['elements']) or batch_merged(Q,lab):break
            top,bad=Q.index('merge');P=lambda n,lab=lab:Q.q/'merge'/f'{lab}.{n}'
            d=decide(top,bad,lab,P,me,job_states(me))
            if d is None:left[lab]='unresolved' if len(bad.get(lab,()))>=MAX_FAILURES else 'pending';break
            n,how=d
            if how!='resume' and not publish(P(n),{**me,'how':how,'time':now()}):continue # lost a race: re-read
            cmd=[a.python,str(Path(a.c8_root)/'tools/production8.py'),'merge',b['batch']]+(['--scratch',a.scratch] if a.scratch else [])
            t0=time.time();rc=run_tracked(cmd,Q.q/'logs'/f"merge_{lab}.{n}.{me['job']}.{me['slot']}.log",P(n))
            res={**me,'attempt':n,'returncode':rc,'seconds':round(time.time()-t0,1),'time':now()}
            if TERMINATING.is_set() or rc<0 or rc>=128:print(now(),'merge',lab,'interrupted, rc',rc,flush=True);raise SystemExit(1) # attempt goes stale
            publish(Q.q/'merge'/(lab+'.ok') if rc==0 else Q.q/'merge'/f'{lab}.{n}.failed',res)
            print(now(),'merge',lab,'attempt',n,'rc',rc,flush=True)
    return left

def lanes_quiescent(Q:Queue,own_job_name:str|None=None)->None:
    """Explicit recovery needs exclusive access to the queue-managed batches. The MAINTENANCE marker is published FIRST
    (from then on no lane worker claims, runs or merges; a worker already running belongs to a job that squeue lists),
    then squeue must answer and list no unfinished job of this package (name prefix JOB_PREFIX, except the c8x-stop
    job, which only writes STOP), including the job this command may run in (recovery is run from the login node). On symmetry
    the queue-managed batches are written only by lane8 workers (merges run inside the lanes); standalone
    production8.py run/merge on them is not supported. The marker is removed only after a successful recovery."""
    if not publish(Q.q/'MAINTENANCE',{'time':now(),'pid':os.getpid(),'host':socket.gethostname()}):raise SystemExit('MAINTENANCE marker exists: another recovery is running or was interrupted (inspect, then remove it)')
    def refuse(msg):os.unlink(Q.q/'MAINTENANCE');raise SystemExit(msg)
    jobs=squeue_jobs()
    if jobs is None:refuse('squeue failed or answered malformed lines; cannot confirm that no C8 job runs')
    mine=os.environ.get('SLURM_JOB_ID','')
    TERMINAL={'COMPLETED','CANCELLED','FAILED','TIMEOUT','NODE_FAIL','BOOT_FAIL','DEADLINE','OUT_OF_MEMORY','REVOKED'} # every other state may still write
    busy=[f'{j} {n} {st}' for j,n,st in jobs if n.startswith(JOB_PREFIX) and n!='c8x-stop' and st not in TERMINAL and not (own_job_name and j==mine and n==own_job_name)]
    if busy:refuse('C8 jobs exist ('+'; '.join(busy)+'): touch STOP, let them end or scancel them, then recover')

def checkpoints_complete(batch:Path)->tuple[bool,int,int]:
    """(complete, present, planned) checkpoints of a batch from its manifests and hash-checked task plans."""
    sys.path.insert(0,str(Path(__file__).resolve().parent));from campaign import blocks,identity
    prod=json.loads((batch/'production.json').read_text());have=need=0
    for c in prod['campaigns']:
        d=batch/c;m=json.loads((d/'manifest.json').read_text())
        for sh,part,_,_ in blocks(d,m):
            for N in m['degrees']:need+=1;have+=(d/'checkpoints'/(identity(sh['id'],part,N)+'.json')).is_file()
    return have==need,have,need

def finalize(a,Q:Queue)->int:
    """Merge-only closing step after the wave (exclusive maintenance access): every batch whose planned checkpoints are
    all present is merged with the frozen merger (resuming an interrupted merge; done markers are not required), and
    merge/<batch>.ok is published. Nothing is computed: production8.py merge only reads checkpoints, and incomplete
    batches are reported, never run. Returns 1 if a complete batch fails to merge."""
    rc_all=0
    for lab,b in Q.batches.items():
        complete,have,need=checkpoints_complete(Path(b['batch']))
        if not complete:print(f'{lab}: incomplete, {have}/{need} checkpoints ({have/need:.3f}): left unmerged');continue
        if batch_merged(Q,lab):print(f'{lab}: complete and merged');continue
        cmd=[a.python,str(Path(a.c8_root)/'tools/production8.py'),'merge',b['batch']]+(['--scratch',a.scratch] if a.scratch else [])
        t0=time.time()
        with (Q.q/'logs'/f'finalize_merge_{lab}.{os.getpid()}.log').open('a') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
        if rc==0:publish(Q.q/'merge'/(lab+'.ok'),{'how':'finalize','returncode':0,'seconds':round(time.time()-t0,1),'time':now()})
        print(f'{lab}: complete, finalize merge rc {rc}');rc_all|=rc!=0
    return 1 if rc_all else 0

def invalidate(Q:Queue,label:str,index:int,reason:str)->None:
    """Explicit recovery of one element: archive its done marker and failure records and the batch's merge marker and
    merge failure records (history kept in invalidated/), then publish 'reset' attempts so the next worker claims the
    element and the merge with a fresh retry budget."""
    k=f'{label}_{int(index):04d}'
    if not any(Q.key(e)==k for e in Q.order):raise SystemExit(f'{k} is not in this queue')
    for src in [Q.q/'done'/k,Q.q/'merge'/(label+'.ok')]+[Q.q/'failed'/f for f in os.listdir(Q.q/'failed') if re.fullmatch(re.escape(k)+r'\.\d+',f)]\
              +[Q.q/'merge'/f for f in os.listdir(Q.q/'merge') if re.fullmatch(re.escape(label)+r'\.\d+\.failed',f)]:archive(Q,src)
    rec={'how':'reset','reason':reason,'time':now(),'job':'operator','slot':-1}
    for sub,name in (('claims',k),('merge',label)):
        top,_=Q.index(sub)
        if name in top:
            n=top[name]+1
            while not publish(Q.q/sub/f'{name}.{n}',rec):n+=1
    with (Q.q/'invalidated'/'log.jsonl').open('a') as f:f.write(json.dumps({'element':k,'batch':label,'reason':reason,'time':now()})+'\n')
    print('invalidated',k,'and the merge state of',label)

def run(a)->int:
    Q=Queue(a.queue)
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,on_signal)
    me={'job':os.environ.get('SLURM_JOB_ID','local'),'restart':os.environ.get('SLURM_RESTART_COUNT','0'),'slot':a.slot,'host':socket.gethostname(),'threads':a.threads}
    aff=getattr(os,'sched_getaffinity',None)
    print(now(),'lane worker',json.dumps(me),'cpus',len(aff(0)) if aff else 'unknown',flush=True)
    reconcile_merges(Q,a,me)
    while not (Q.q/'STOP').exists() and not deadline_passed(Q.q) and not TERMINATING.is_set():
        if (Q.q/'MAINTENANCE').exists():print(now(),'MAINTENANCE marker present: waiting',flush=True);TERMINATING.wait(WAIT_SECONDS);continue
        e,n,how=next_element(Q,me)
        if e is None: # nothing claimable now: wait while unfinished work is held by others (it may go stale), else stop
            done=Q.done();_,bad=Q.index('claims')
            held=[Q.key(x) for x in Q.order if Q.key(x) not in done and len(bad.get(Q.key(x),()))<MAX_FAILURES]
            if not held and not [v for v in reconcile_merges(Q,a,me).values() if v=='pending']:break
            print(now(),'waiting: unfinished work held by other workers',len(held),flush=True)
            TERMINATING.wait(WAIT_SECONDS);continue
        k=Q.key(e)
        if closed(Q):print(now(),'deadline or STOP reached before starting',k,'(claim left unstarted)',flush=True);break
        print(now(),how,k,'attempt',n,flush=True)
        cmd=[a.python,str(Path(a.c8_root)/'tools/production8.py'),'run',e['batch'],'--index',str(e['index']),'--threads',str(a.threads),'--executable',a.executable]
        if a.scratch:cmd+=['--scratch',a.scratch]
        t0=time.time();rc=run_tracked(cmd,Q.q/'logs'/f"{k}.{n}.{me['job']}.{me['slot']}.log",Q.q/'claims'/f'{k}.{n}')
        res={**me,'attempt':n,'how':how,'returncode':rc,'seconds':round(time.time()-t0,1),'time':now()}
        if TERMINATING.is_set() or rc<0 or rc>=128:print(now(),'interrupted',k,'rc',rc,'(no failure recorded)',flush=True);return 1
        if rc==0:
            publish(Q.q/'done'/k,res) # a concurrent duplicate may have marked it first
            print(now(),'done',k,res['seconds'],'s',flush=True)
            reconcile_merges(Q,a,me)
        else:publish(Q.q/'failed'/f'{k}.{n}',res);print(now(),'FAILED',k,'attempt',n,'rc',rc,flush=True)
    if TERMINATING.is_set():print(now(),'terminating',flush=True);return 1
    print(now(),'STOP file present' if (Q.q/'STOP').exists() else 'deadline passed' if deadline_passed(Q.q) else 'no element needs this worker',flush=True)
    left=reconcile_merges(Q,a,me);done=Q.done();_,bad=Q.index('claims')
    abandoned=[Q.key(e) for e in Q.order if Q.key(e) not in done and len(bad.get(Q.key(e),()))>=MAX_FAILURES]
    pending=[lab for lab,v in left.items() if v=='pending'];unresolved=[lab for lab,v in left.items() if v=='unresolved']
    if pending:print(now(),'merges pending in other workers:',pending,flush=True)
    if abandoned:print(now(),'ABANDONED elements (failed',MAX_FAILURES,'times):',abandoned,flush=True)
    if unresolved:print(now(),'UNRESOLVED merges:',unresolved,flush=True)
    return 1 if abandoned or unresolved else 0

def queue(a)->None:
    """order.json from planned batches (in the order given) and per-index costs (JSON {index: seconds}); within a
    batch, largest predicted cost first."""
    cost={int(k):float(v) for k,v in json.loads(a.costs.read_text()).items()};els=[];labels=set()
    for b in a.batches:
        b=b.resolve();prod=json.loads((b/'production.json').read_text());n=len(prod['jobs'])
        if set(cost)!=set(range(n)):raise ValueError(f'{b}: cost table does not cover indices 0..{n-1}')
        label=prod.get('label') or b.name
        if label in labels:raise ValueError('duplicate batch label '+label)
        labels.add(label);els+=[{'batch':str(b),'label':label,'index':i,'cost':cost[i]} for i in sorted(range(n),key=lambda i:(-cost[i],i))]
    out=a.queue.resolve();out.mkdir(parents=True,exist_ok=True)
    p=out/'order.json'
    if p.exists():raise FileExistsError('order.json exists: use a new queue directory')
    for d in DIRS:(out/d).mkdir(exist_ok=True)
    p.write_text(json.dumps({'created':now(),'elements':els},indent=1)+'\n')
    print('queued',len(els),'elements of',len(a.batches),'batches')

def status(a)->None:
    Q=Queue(a.queue);done=Q.done();top,bad=Q.index('claims');mt,mb=Q.index('merge')
    for lab,b in Q.batches.items():
        ks=b['elements'];nd=sum(k in done for k in ks);act=sum(k not in done and k in top and top[k] not in bad.get(k,()) for k in ks)
        ab=sum(k not in done and len(bad.get(k,()))>=MAX_FAILURES for k in ks);fl=sum(bool(bad.get(k)) for k in ks)
        ms='merged' if batch_merged(Q,lab) else f'merge attempts {mt[lab]+1} failed {len(mb.get(lab,()))}' if lab in mt else ''
        print(f'{lab}: {nd}/{len(ks)} done, {act} in progress, {fl} with failures, {ab} abandoned {ms}')

def main()->None:
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    r=s.add_parser('run');r.add_argument('--queue',type=Path,required=True);r.add_argument('--slot',type=int,required=True);r.add_argument('--threads',type=int,required=True)
    r.add_argument('--c8-root',required=True,help='frozen production code (tools/production8.py)');r.add_argument('--executable',required=True);r.add_argument('--scratch')
    r.add_argument('--python',default=sys.executable)
    q=s.add_parser('queue');q.add_argument('--queue',type=Path,required=True);q.add_argument('--costs',type=Path,required=True);q.add_argument('batches',type=Path,nargs='+')
    t=s.add_parser('status');t.add_argument('--queue',type=Path,required=True)
    t=s.add_parser('invalidate',help='redo one element (and re-merge its batch)');t.add_argument('--queue',type=Path,required=True);t.add_argument('--label',required=True);t.add_argument('--index',type=int,required=True);t.add_argument('--reason',required=True)
    t=s.add_parser('quarantine',help='campaign.py quarantine of one checkpoint of a queue-managed batch, then invalidate its element')
    t.add_argument('--queue',type=Path,required=True);t.add_argument('--c8-root',required=True);t.add_argument('--label',required=True);t.add_argument('--campaign',required=True);t.add_argument('--identity',required=True);t.add_argument('--reason',required=True)
    t.add_argument('--python',default=sys.executable)
    t=s.add_parser('deadline',help='publish the wave deadline once (before submission): workers start no element after it')
    t.add_argument('--queue',type=Path,required=True);t.add_argument('--epoch',type=float,required=True)
    t=s.add_parser('finalize',help='after the wave: merge every batch with all planned checkpoints (merge only, exclusive access)')
    t.add_argument('--queue',type=Path,required=True);t.add_argument('--c8-root',required=True);t.add_argument('--scratch');t.add_argument('--python',default=sys.executable)
    a=p.parse_args()
    if a.action=='run':sys.exit(run(a))
    if a.action=='deadline':
        Q=Queue(a.queue)
        if not publish(Q.q/'deadline.json',{'epoch':a.epoch,'iso':time.strftime('%Y-%m-%dT%H:%M:%S%z',time.localtime(a.epoch)),'published':now()}):raise SystemExit('deadline.json exists (immutable)')
        print('deadline',readj(Q.q/'deadline.json'));return
    if a.action=='finalize':
        Q=Queue(a.queue);lanes_quiescent(Q,own_job_name='c8x-finalize');rc=finalize(a,Q)
        os.unlink(Q.q/'MAINTENANCE');sys.exit(rc)
    if a.action in ('invalidate','quarantine'):
        Q=Queue(a.queue);lanes_quiescent(Q)
        recover(a,Q) # on any failure the MAINTENANCE marker stays: workers wait until an operator inspects and removes it
        os.unlink(Q.q/'MAINTENANCE');return
    {'queue':queue,'status':status}[a.action](a)

def recover(a,Q:Queue)->None:
    if a.action=='invalidate':invalidate(Q,a.label,a.index,a.reason);return
    if a.action=='quarantine':
        b=Path(Q.batches[a.label]['batch']);prod=json.loads((b/'production.json').read_text())
        m=re.fullmatch(r's(\d{6})_p\d{6}_N\d+',a.identity)
        if not m:raise SystemExit('identity must look like s000012_p000003_N3')
        idx=[i for i,j in enumerate(prod['jobs']) if j['campaign']==a.campaign and int(j['index'])==int(m.group(1))]
        if len(idx)!=1:raise SystemExit('no unique element for that campaign shard')
        # Restartable: the queue state is invalidated first (lanes are stopped, so no worker acts in between); then the
        # checkpoint is moved. A rerun after an interruption finds it already quarantined and only re-invalidates.
        invalidate(Q,a.label,idx[0],'quarantine '+a.campaign+'/'+a.identity+': '+a.reason)
        ck=b/a.campaign/'checkpoints'/(a.identity+'.json');ql=b/a.campaign/'checkpoints'/'quarantine'/'log.jsonl'
        if ck.is_file():subprocess.run([a.python,str(Path(a.c8_root)/'tools/campaign.py'),'quarantine',str(b/a.campaign),a.identity,'--reason',a.reason],check=True)
        elif (b/a.campaign/'checkpoints'/'quarantine').is_dir() and any(f.startswith(a.identity+'.json.') for f in os.listdir(b/a.campaign/'checkpoints'/'quarantine')):
            print('checkpoint already quarantined:',a.identity,'(log entry',('present' if ql.is_file() and a.identity in ql.read_text() else 'missing: interrupted before logging')+')')
        else:raise SystemExit(f'no checkpoint {ck} and no quarantined copy')
        audit=b/a.campaign/'merged'/'audit.json' # an interrupted quarantine may have moved the checkpoint but not the audit
        if audit.is_file():
            k=0
            while (audit.parent/f'audit.json.invalidated.{k}').exists():k+=1
            os.rename(audit,audit.parent/f'audit.json.invalidated.{k}');print('audit invalidated ->',f'audit.json.invalidated.{k}')
if __name__=='__main__':main()
