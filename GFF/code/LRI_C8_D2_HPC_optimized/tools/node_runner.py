#!/usr/bin/env python3
"""Whole-node runner of the site layer (docs/SITES.md), and the scheduler, claim and seed helpers site_submit.py uses.

  node_runner.py run RUN [--threads T] [--scratch DIR]     inside a runner job (slurm/node_runner.sh): claim, run, repeat
  node_runner.py status RUN [--json]                        done, exhausted and claimed indices and their histories
  node_runner.py retry RUN --index I [--reason TEXT]        make an exhausted index retryable (a `reset` history line)
  node_runner.py seed reserve RUN                           reserve a non-test campaign's base seed in this site's log
  node_runner.py seed check RUN                             a test plan's seed must collide with nothing in the log
  node_runner.py seed source RUN                            print the campaign's seed source c8ind:<abs RUN>:<sha12>
  node_runner.py seed owner-check --log F --owner SRC --seed S          exit 1 unless SRC alone owns S and its seeds
  node_runner.py seed receipt --union F --owner SRC --seed S --site X --log NAME=FILE ... --output OUT
                                                            the same check, then write seed_receipt.json (seed_sync.sh)

A runner never changes what is computed: each attempt is the unchanged `production.py run RUN --index I --threads T
--scratch S [--max-blocks k]`. Blocks are atomic and an existing valid checkpoint is skipped, so a wrong claim
decision costs time, never results. Campaign state under RUN (atomic mkdir and hard links only, no flock):
  claims/<I>/owner.json   the live claim of index I (atomic mkdir): job, restart count, host, pid, UTC and a unique
                          token; claims are created and removed only under claims/.lock (atomic mkdir), and a removal
                          must present the claim's token, so a release decided on an old owner record never removes a
                          newer claim
  attempts/<I>.jsonl      append-only history (done, partial, failed, term, released, reset); never deleted; only the
                          claim holder appends, or a releaser under claims/.lock after verifying the token
  done/<I>, exhausted/<I> markers, published no-clobber; 2 `failed` outcomes since the last `reset` exhaust an index
  site_identity.json      CPU vendor and the sha256 of every library ldd resolves for the campaign executable, published
                          no-clobber by the first runner; a runner with another identity exits 64 before any claim
  runner_logs/idx<I>.<job>.<restart>.<ns>.log   the output of one attempt
Order: heaviest remaining work first. Cost-model plans: the estimated core-seconds of the uncommitted blocks; other
plans: loop descending, free before power, then shard. Deadline (cost-model plans only): wall(block) = max(longest
task, estimated cost / (T x production.ASSUMED_EFFICIENCY)); an attempt gets --max-blocks k, the largest k whose
cumulative wall x 1.5 + 600 s fits the job's remaining time (squeue %L); k = 0 skips the index in this job.
Signals: TERM, INT and HUP are forwarded to the production.py child, which stops its native worker and removes its
runtime; the attempt is recorded `term`, the claim removed, and the runner exits 128+signal (143 for TERM).
Scheduler queries (here and in site_submit.py) go through squeue(): no inherited SQUEUE_* or *_CLUSTERS variable, the
real uid's user, all states, array tasks expanded, an explicit format; a failure or an unparsable line is UNKNOWN (69).
Exit codes: 0 no eligible work left, 1 an attempt failed, 64 invalid input or a refused identity (nothing claimed),
69 scheduler state unknown, 75 a claim or lock is held, 128+signal stopped by a signal.
"""
from __future__ import annotations
import argparse,calendar,hashlib,json,math,os,pwd,secrets,shutil,signal,socket,subprocess,sys,time,types
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import production as prod
from common import ROOT,digest,dump,fingerprint,load
from task_schedule import block_count,task_blocks

PRODUCTION=ROOT/'tools/production.py'  # every attempt runs this file, unchanged
JOB_NAMES={'run':'c8d2-ind-run','merge':'c8d2-ind-merge'}
SESSION,OTHER_SESSION,COMMENT='c8d2-','c8d3-','c8ind:'  # C62d's and C63d's job-name prefixes; this layer's comment
AMD_POOL=frozenset({'amdq','amddebugq','amdpreq'})
# The free-text fields come last (comment, then name), after seven fields that never contain '|'.
QUERY_FORMAT='%i|%T|%P|%q|%D|%u|%L|%k|%j'
# Live states that hold no allocation; every other live state counts as running.
PENDING_LIKE=frozenset('PENDING REQUEUED REQUEUE_HOLD REQUEUE_FED SPECIAL_EXIT RESV_DEL_HOLD'.split())
EXHAUST_AFTER=2;DEADLINE_FACTOR=1.5;DEADLINE_MARGIN=600.
UNOWNED_STALE=600.  # seconds after which a claim without a readable owner record counts as stale
CLAIMS_LOCK,CLAIMS_LOCK_WAIT='.lock',120.  # claims/.lock serialises every claim transition (held for milliseconds)
CAMPAIGN_LOCK='.c8_submit.lock'  # the package's campaign lock (tools/slurm_submit.py), shared with array submissions
SEED_PINS={'seeds.py':'e65d22232a828429155ae4cc959a4f2600c16e812b723f8ef6957f67f6c1669f',   # LRI_C8_D2_HPC aafa8a4
           'common.py':'643fdecfd30213a5022e344a5d6042708c78406a20d93564cd916628d395cfef'}
RECEIPT_SCHEMA='c8ind-seed-receipt-1';IDENTITY_SCHEMA='c8ind-site-identity-1'
STOP_SIGNALS=(signal.SIGTERM,signal.SIGINT,signal.SIGHUP)

class Refuse(Exception):
    """A refusal: nothing was claimed, submitted or changed. code: 64 invalid input, 65 budget or live work, 69 unknown
    or uncertain scheduler state, 75 a lock or claim is held."""
    def __init__(self,code,msg):super().__init__(msg);self.code=code

def utc(t=None)->str:return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(t))
def utc_epoch(text:str)->float:return float(calendar.timegm(time.strptime(text,'%Y-%m-%dT%H:%M:%SZ')))

def scheduler_user()->str:
    """The account sbatch submits under: the name of the real uid, never USER or LOGNAME."""
    uid=os.getuid()
    try:return pwd.getpwuid(uid).pw_name
    except KeyError:return str(uid)

class DirLock:
    """The DirLock protocol of LRI_C8_D2_HPC/tools/common.py: an atomically created directory with an owner.json
    record, removed on exit; wait > 0 retries for that many seconds, then refuses (75). A lock left by a killed process
    is never broken automatically: its owner.json names the holder; remove it by hand."""
    def __init__(self,path:Path,command:str,what:str,wait:float=0.):
        self.path=Path(path);self.command=command;self.what=what;self.wait=wait;self.held=False
    def __enter__(self):
        t0=time.time()
        while True:
            try:os.mkdir(self.path,0o700);break
            except FileExistsError:
                if time.time()-t0<self.wait:time.sleep(0.2);continue
                try:owner=(self.path/'owner.json').read_text().strip()
                except OSError:owner='unknown (owner.json not written yet or unreadable)'
                raise Refuse(75,f'another process for {self.what} holds {self.path} ({owner}); nothing changed. Rerun when it has '
                                f'finished, or remove {self.path} by hand if no such process is running')
        self.held=True
        try:(self.path/'owner.json').write_text(json.dumps({'host':socket.gethostname(),'pid':os.getpid(),'user':scheduler_user(),'started_utc':utc(),'command':self.command})+'\n')
        except BaseException:self.__exit__(None,None,None);raise
        return self
    def __exit__(self,*exc):
        if self.held:
            try:(self.path/'owner.json').unlink()
            except FileNotFoundError:pass
            os.rmdir(self.path);self.held=False
        return False

# ---------------------------------------------------------------- the scheduler-query helper
def query_env(env:dict)->tuple[dict,list]:
    """squeue's environment: env without SQUEUE_* and *_CLUSTERS (SLURM_CLUSTERS included), and the removed names."""
    drop=sorted(k for k in env if k.startswith('SQUEUE_')or k.endswith('_CLUSTERS'))
    return {k:v for k,v in env.items()if k not in drop},drop

def parse_record(line:str,me:str,what:str)->dict:
    f=line.split('|',7)
    if len(f)!=8 or not f[0].strip()or not f[1].strip()or not f[5].strip():
        raise Refuse(69,f'{what}: squeue line does not parse as {QUERY_FORMAT!r}: {line[:300]!r}; job state UNKNOWN, nothing done')
    jid,state,part,qos,nodes,user,left,rest=(x.strip()for x in f)
    if rest.count('|')==1:comment,name=(x.strip()for x in rest.split('|'))
    elif user!=me:comment=name=None  # another user's comment or name holds '|': the fixed fields are all that count
    else:raise Refuse(69,f'{what}: job {jid} of {me} has a "|" in its comment or name, so its name is unknown; nothing done')
    return {'jobid':jid,'state':state.upper(),'partitions':[p for p in part.split(',')if p],'qos':qos,'nodes':int(nodes)if nodes.isdigit()else None,
            'user':user,'left':left,'comment':comment,'name':name}

def squeue(env:dict,select:list,what:str)->list[dict]:
    """One scheduler query: every state (--states=all), array tasks expanded (-r), the explicit QUERY_FORMAT, the given
    selection (-u <real user>, -A <account> or -j <job>). A failure or an unparsable line refuses (69), never zero."""
    e,_=query_env(env);me=scheduler_user()
    try:cp=subprocess.run(['squeue','--all','--states=all','-h','-r','-o',QUERY_FORMAT,*select],capture_output=True,text=True,errors='replace',env=e,timeout=300)
    except (OSError,subprocess.SubprocessError)as x:raise Refuse(69,f'{what}: squeue could not run ({x}); job state UNKNOWN, nothing done')
    if cp.returncode:raise Refuse(69,f'{what}: squeue failed (exit {cp.returncode}): {(cp.stderr or cp.stdout).strip()[-300:]}; job state UNKNOWN, nothing done')
    return [parse_record(line,me,what)for line in cp.stdout.splitlines()if line.strip()]

def state_class(r:dict)->str:
    """production.py's own state sets: 'live', 'terminal', or 'uncertain' (COMPLETING, STAGE_OUT, PREEMPTED, unknown)."""
    return 'live'if r['state']in prod.LIVE_STATES else 'terminal'if r['state']in prod.TERMINAL_STATES else 'uncertain'
def is_running(r:dict)->bool:return r['state']in prod.LIVE_STATES and r['state']not in PENDING_LIKE
def named(r:dict,prefix:str)->bool:return (r['name']or'').startswith(prefix)

def settled(records:list,counted,what:str)->None:
    """Refuse (69) while any record that would be counted is in an uncertain state."""
    bad=[r for r in records if counted(r)and state_class(r)=='uncertain']
    if bad:raise Refuse(69,f'{what}: job(s) '+', '.join(f'{r["jobid"]}={r["state"]} ({r["name"]})'for r in bad)+
                           ' are completing, preempted or in an unrecognised state; nothing done. Rerun once Slurm has settled them')

def duration(text:str)->float|None:
    """Seconds of a Slurm duration ([D-]HH:MM:SS, MM:SS or SS); inf for UNLIMITED; None when it does not parse."""
    t=(text or'').strip()
    if t.upper()=='UNLIMITED':return math.inf
    d,_,hms=t.rpartition('-');parts=hms.split(':')
    if (d and not d.isdigit())or not 1<=len(parts)<=3 or not all(p.isdigit()for p in parts):return None
    s=0
    for p in parts:s=s*60+int(p)
    return float(s+86400*int(d or 0))

def campaign_comment(run:Path)->str:return COMMENT+prod.campaign_tag(run)

def campaign_jobs(records:list,run:Path,me:str)->dict:
    """This campaign's live runner and merge jobs (the user's jobs with its comment); an uncertain one refuses (69)."""
    c=campaign_comment(run);mine=[r for r in records if r['user']==me and r['comment']==c]
    settled(mine,lambda r:True,'campaign jobs')
    live=[r for r in mine if state_class(r)=='live'];odd=[r for r in live if r['name']not in JOB_NAMES.values()]
    if odd:raise Refuse(69,f'unexpected live job(s) with this campaign\'s comment {c}: '+', '.join(f'{r["jobid"]} ({r["name"]})'for r in odd)+'; nothing done')
    return {'comment':c,'runners':[r['jobid']for r in live if r['name']==JOB_NAMES['run']],'merges':[r['jobid']for r in live if r['name']==JOB_NAMES['merge']]}

# ---------------------------------------------------------------- campaign state: claims, history, markers
def read_plan(run:Path)->dict:
    try:m=load(Path(run)/'manifest.json')
    except (OSError,ValueError)as x:raise Refuse(64,f'cannot read the plan {run}/manifest.json: {x}')
    if m.get('schema')!=prod.SCHEMA or m.get('dimension')!=2 or m.get('order')!=8:raise Refuse(64,f'{run} is not a {prod.SCHEMA} campaign')
    return m

def claim_dir(run:Path,i:int)->Path:return run/'claims'/str(i)
def marker(run:Path,kind:str,i:int)->Path:return run/kind/str(i)

def claims_lock(run:Path,command:str)->DirLock:
    """The cross-node lock (atomic mkdir; flock is node-local on BeeGFS) under which a claim is created, verified or
    removed; never broken automatically (a holder killed inside its few-millisecond window leaves claims/.lock, which
    makes later transitions refuse 75 after CLAIMS_LOCK_WAIT: remove it by hand once no runner is live)."""
    (run/'claims').mkdir(exist_ok=True);return DirLock(run/'claims'/CLAIMS_LOCK,command,'the claims of this campaign',wait=CLAIMS_LOCK_WAIT)

def take_claim(run:Path,i:int,owner:dict)->str|None:
    """Claim index i under the claims lock (mkdir, then owner.json by rename). Returns the claim's unique token, which
    every later removal must present; None when another claim exists."""
    tok=secrets.token_hex(16);d=claim_dir(run,i)
    with claims_lock(run,f'take claim {i}: {owner.get("command")}'):
        try:os.mkdir(d,0o700)
        except FileExistsError:return None
        try:(d/'owner.json.tmp').write_text(json.dumps({**owner,'token':tok})+'\n');os.replace(d/'owner.json.tmp',d/'owner.json')
        except BaseException:_remove_claim(run,i);raise
    return tok

def _remove_claim(run:Path,i:int)->None:
    d=claim_dir(run,i)
    for n in ('owner.json','owner.json.tmp'):
        try:(d/n).unlink()
        except FileNotFoundError:pass
    try:os.rmdir(d)
    except FileNotFoundError:pass

def claim_token(run:Path,i:int):
    """The token of claim i: None for a claim without a readable owner record (or one written before tokens), and
    False when there is no claim."""
    d=claim_dir(run,i)
    if not d.exists():return False
    try:return json.loads((d/'owner.json').read_text()).get('token')
    except (OSError,ValueError,AttributeError):return None

def drop_claim(run:Path,i:int,token,history:dict|None=None)->bool:
    """Under the claims lock, remove claim i only if it still carries `token` (the value take_claim returned, or the
    token read with the owner record a release decided on), first appending `history` to attempts/<i>.jsonl. False,
    with nothing changed, when the claim is gone or now belongs to someone else."""
    with claims_lock(run,f'drop claim {i}'):
        if claim_token(run,i)!=token:return False
        if history is not None:append_attempt(run,i,history)
        _remove_claim(run,i);return True

def claims_of(run:Path)->dict:
    """{index: owner record or None (unreadable)} of every claim."""
    out={};d=run/'claims'
    for p in (sorted(d.iterdir())if d.is_dir()else[]):
        if not p.name.isdigit():continue
        try:out[int(p.name)]=json.loads((p/'owner.json').read_text())
        except (OSError,ValueError):out[int(p.name)]=None
    return out

def owner_record(job,restart:int,command:str)->dict:
    return {'job':job,'restart':restart,'host':socket.gethostname(),'pid':os.getpid(),'utc':utc(),'command':command}

def append_attempt(run:Path,i:int,rec:dict)->None:
    """One line of attempts/<I>.jsonl, appended (O_APPEND) and fsynced; the file is never rewritten or removed."""
    p=run/'attempts'/f'{i}.jsonl';p.parent.mkdir(exist_ok=True)
    fd=os.open(p,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o666)
    try:os.write(fd,(json.dumps(rec,sort_keys=True)+'\n').encode());os.fsync(fd)
    finally:os.close(fd)

def read_attempts(run:Path,i:int)->list:
    try:text=(run/'attempts'/f'{i}.jsonl').read_text()
    except FileNotFoundError:return []
    out=[]
    for line in text.splitlines():
        try:out.append(json.loads(line))
        except ValueError:out.append({'outcome':'unreadable','line':line[:200]})  # a torn last line is no failure
    return out

def failures(history:list)->int:
    """`failed` outcomes since the last `reset` (term, released and partial are not failures)."""
    n=0
    for h in history:n=0 if h.get('outcome')=='reset'else n+(h.get('outcome')=='failed')
    return n

def publish_marker(run:Path,kind:str,i:int,doc:dict)->None:
    try:dump(marker(run,kind,i),doc)
    except FileExistsError:pass  # published before (no-clobber)

def release_stale(run:Path,records:list,claims:dict,by:str,dry:bool=False)->dict:
    """Release each claim of `claims` (read BEFORE the snapshot `records` was taken) whose owner job is not live: gone
    from the scheduler, or terminal. A `released` history line is appended first; history and markers stay. An owner in
    an uncertain state refuses (69) before anything is released. Call under the campaign lock. Each removal happens
    under the claims lock and only if the claim still carries the token read with `claims` (else it is a newer claim,
    taken after the owner record was read: reported as `changed`, never removed)."""
    jobs={r['jobid']:r for r in records};todo=[];kept=[];unsure=[]
    for i,o in sorted(claims.items()):
        if not o or not o.get('job'):
            try:age=time.time()-claim_dir(run,i).stat().st_mtime
            except FileNotFoundError:continue
            if age<UNOWNED_STALE:kept.append(i);continue
            todo.append((i,o,'no owner job record'));continue
        r=jobs.get(str(o['job']))
        if r is None:todo.append((i,o,f'owner job {o["job"]} is gone from the scheduler'));continue
        k=state_class(r)
        if k=='live':kept.append(i)
        elif k=='terminal':todo.append((i,o,f'owner job {o["job"]} is {r["state"]}'))
        else:unsure.append(f'{i} (job {o["job"]} {r["state"]})')
    if unsure:raise Refuse(69,'claims whose owner job is completing, preempted or in an unrecognised state: '+', '.join(unsure)+'; nothing released. Rerun once Slurm has settled them')
    done=[];changed=[]
    for i,o,why in todo:
        if dry or not claim_dir(run,i).exists():continue
        tok=o.get('token')if isinstance(o,dict)else None
        if drop_claim(run,i,tok,{'outcome':'released','utc':utc(),'by':by,'owner':o,'why':why}):done.append(i)
        else:changed.append(i)
    return {'released':done,'stale':[i for i,_,_ in todo],'changed_since_read':changed,'kept_live':kept,'dry_run':dry}

def self_release(run:Path,job:str,restart:int)->list:
    """A requeued runner (symmetry amdpreq) releases the claims its own job id holds from a lower restart count."""
    out=[]
    for i,o in claims_of(run).items():
        if o and str(o.get('job'))==str(job)and int(o.get('restart')or 0)<restart:
            if drop_claim(run,i,o.get('token'),{'outcome':'released','utc':utc(),'by':f'runner {job} restart {restart}','owner':o,
                                                 'why':'requeued: claim of an earlier incarnation'}):out.append(i)
    return out

# ---------------------------------------------------------------- frozen layout and deadline
def group_key(name:str)->tuple:c,s,L=name.split('_');return c,s,int(L[1:])

def layouts(run:Path,m:dict,costs:bool)->list:
    """Per job index: group, shard and block count, and with costs each block's (tasks, summed estimated cost, longest
    task), from the frozen tasks.sqlite (read-only, the package's block reader)."""
    T=m['checkpoint_tasks'];by={};out={}
    for j in m['jobs']:by.setdefault(j['group'],[]).append(j)
    for g,jobs in by.items():
        p=run/'groups'/g;db=prod.dbopen(p/'tasks.sqlite',True)
        try:
            for j in jobs:
                blocks=[(len(b),math.fsum(r[6]for r in b),max(r[6]for r in b))for b in task_blocks(db,j['shard'],T,with_cost=True)]if costs else None
                out[j['id']]={'index':j['id'],'group':g,'shard':j['shard'],'dir':p,'nblocks':len(blocks)if costs else block_count(db,j['shard'],T),'blocks':blocks}
        finally:db.close()
    return [out[j['id']]for j in m['jobs']]

def listing(p:Path)->set:
    try:return set(os.listdir(p))
    except FileNotFoundError:return set()
def uncommitted(x:dict,names:set)->list:return [k for k in range(x['nblocks'])if f's{x["shard"]:06d}_p{k:06d}.json'not in names]
def committed(x:dict)->int:return x['nblocks']-len(uncommitted(x,listing(x['dir']/'checkpoints')))

def block_wall(block:tuple,threads:int)->float:
    """Wall-time estimate of one frozen block: max(longest task, summed task seconds / (T x ASSUMED_EFFICIENCY))."""
    n,cost,longest=block;return max(longest,cost/(threads*prod.ASSUMED_EFFICIENCY))

def admissible_blocks(walls:list,remaining:float)->int:
    """The largest k such that the first k walls, summed, x DEADLINE_FACTOR + DEADLINE_MARGIN fit in `remaining`."""
    k=0;cum=0.
    for w in walls:
        cum+=w
        if cum*DEADLINE_FACTOR+DEADLINE_MARGIN>remaining:break
        k+=1
    return k

def ordered(lays:list,costs:bool,names:dict)->list:
    if costs:return sorted(lays,key=lambda x:(-math.fsum(x['blocks'][k][1]for k in uncommitted(x,names[x['group']])),x['index']))
    rank={'free':0,'power':1}
    return sorted(lays,key=lambda x:(-group_key(x['group'])[2],rank[group_key(x['group'])[1]],x['shard'],group_key(x['group'])[0],x['index']))

def time_left(env:dict,job:str)->float:
    rs=[r for r in squeue(env,['-j',str(job)],'remaining-time query')if r['jobid']==str(job)]
    s=duration(rs[0]['left'])if len(rs)==1 else None
    if s is None:raise Refuse(69,f'remaining time of job {job} is UNKNOWN (squeue %L: {[r["left"]for r in rs]}); no further index started')
    return s

# ---------------------------------------------------------------- runtime identity (one vendor and library stack)
def cpu_vendor(path:Path=Path('/proc/cpuinfo'))->str:
    try:
        for line in path.read_text(errors='replace').splitlines():
            k,_,v=line.partition(':')
            if k.strip()in('vendor_id','CPU implementer'):return v.strip()
    except OSError:pass
    return f'{sys.platform}-{os.uname().machine}'

def campaign_executable(m:dict)->Path:return prod.exe_for(m['backend'])

LOADER_OVERRIDES=('LD_PRELOAD','LD_AUDIT','GLIBC_TUNABLES')  # would change the code the executable runs, invisibly to ldd hashes
VDSO=frozenset({'linux-vdso.so.1','linux-gate.so.1','linux-vdso64.so.1'})

def loader_overrides(env:dict)->list:return sorted(k for k in LOADER_OVERRIDES if env.get(k))

def ldd_extra(exe:Path)->tuple[dict,list]:
    """What common.fingerprint (an AC1 file) does not cover: ldd entries given by absolute path without '=>' (the loader,
    /etc/ld.so.preload libraries), as {'abs:<path>': sha256}, and the lines of unresolved or unexplained dependencies."""
    try:cp=subprocess.run(['ldd',str(exe)],capture_output=True,text=True,timeout=120)
    except (OSError,subprocess.SubprocessError)as x:return {},[f'ldd failed: {x}']
    extra={};bad=[]
    for line in cp.stdout.splitlines():
        parts=line.split()
        if not parts or parts[0]in VDSO:continue
        if '=>'in parts:
            i=parts.index('=>')
            if not(i+1<len(parts)and parts[i+1].startswith('/')):bad.append(line.strip())
        elif parts[0].startswith('/'):
            try:extra['abs:'+parts[0]]=digest(Path(os.path.realpath(parts[0])))
            except OSError as x:bad.append(f'{line.strip()} ({x})')
        else:bad.append(line.strip())
    return extra,bad

def node_identity(exe:Path,env:dict|None=None)->dict:
    """CPU vendor and the sha256 of every library ldd resolves for exe, with its ELF interpreter (common.fingerprint) and
    every absolute-path ldd entry. Refuses (64) a dynamic-loader override in the environment (LD_PRELOAD, LD_AUDIT,
    GLIBC_TUNABLES; inherited by production.py and its native worker) and any unresolved dependency."""
    over=loader_overrides(os.environ if env is None else env)
    if over:raise Refuse(64,f'dynamic-loader override(s) {", ".join(over)} set: they could change the numerical functions the kernel calls without changing any ldd hash; unset them. Nothing claimed')
    fp=fingerprint(exe);libs={n:v['sha256']for n,v in fp['libraries'].items()if v.get('sha256')}
    if fp.get('interpreter')and fp['interpreter'].get('sha256'):libs['ld.so']=fp['interpreter']['sha256']
    if fp.get('ldd_error')or not libs:raise Refuse(64,f'cannot establish the runtime identity of {exe}: ldd {fp.get("ldd_error")or"resolved no library"}; nothing claimed')
    extra,bad=ldd_extra(exe)
    if bad:raise Refuse(64,f'cannot establish the runtime identity of {exe}: unresolved or unexplained ldd entries {bad}; nothing claimed')
    libs.update(extra)
    return {'schema':IDENTITY_SCHEMA,'vendor':cpu_vendor(),'libraries':libs,'cpu_model':fp.get('cpu_model'),'host':fp.get('host'),'glibc':fp.get('glibc'),'executable':str(exe)}

def identity_guard(run:Path,exe:Path,job,env:dict|None=None)->str:
    """Publish site_identity.json no-clobber (os.link) on first use; afterwards refuse (64) another vendor or library set."""
    me={**node_identity(exe,env),'job':job,'utc':utc()};path=run/'site_identity.json'
    try:dump(path,me);return 'published'
    except FileExistsError:pass
    try:ref=load(path)
    except (OSError,ValueError)as x:raise Refuse(64,f'cannot read {path}: {x}; nothing claimed')
    diff=[k for k in ('vendor','libraries')if ref.get(k)!=me[k]]
    if diff:
        old=ref.get('libraries')or{};libs=sorted(n for n in set(old)|set(me['libraries'])if old.get(n)!=me['libraries'].get(n))
        raise Refuse(64,f'runtime identity mismatch with {path} (job {ref.get("job")} on {ref.get("host")}): '+
                        (f'vendor {me["vendor"]!r} != {ref.get("vendor")!r}; 'if 'vendor'in diff else'')+(f'libraries differ: {", ".join(libs)}; 'if 'libraries'in diff else'')+
                        'a campaign stays on one CPU vendor and library stack (cross-vendor duplicates conflict). Nothing claimed')
    return 'match'

# ---------------------------------------------------------------- the runner
_STOP={'signum':None,'child':None,'forwarded':None}

def forward(c)->None:
    """TERM to the production.py child, once per child (it ignores repeats; a second one is never needed)."""
    if c is not None and _STOP['forwarded']!=c.pid and c.poll()is None:
        _STOP['forwarded']=c.pid
        try:c.send_signal(signal.SIGTERM)
        except OSError:pass

def _on_signal(signum,frame):
    if _STOP['signum']is None:_STOP['signum']=signum
    forward(_STOP['child'])

def attempt(run:Path,x:dict,ctx:dict)->str|None:
    """Run the claimed index once; None when it was not launched (finished meanwhile, exhausted, or no block fits)."""
    i=x['index']
    if marker(run,'done',i).exists()or marker(run,'exhausted',i).exists():return None
    if failures(read_attempts(run,i))>=EXHAUST_AFTER:
        publish_marker(run,'exhausted',i,{'index':i,'utc':utc(),'job':ctx['job'],'failures':EXHAUST_AFTER})
        print(f'C8: index {i}: {EXHAUST_AFTER} failures since its last reset; exhausted (node_runner.py retry makes it retryable)',flush=True);ctx['stats']['exhausted']+=1;return None
    todo=uncommitted(x,listing(x['dir']/'checkpoints'));before=x['nblocks']-len(todo);k=None
    if ctx['costs']and todo:
        walls=[block_wall(x['blocks'][b],ctx['threads'])for b in todo];k=admissible_blocks(walls,ctx['remaining'])
        if k==0:
            ctx['skip'].add(i);ctx['stats']['skipped']+=1
            print(f'C8: index {i}: its next block needs {walls[0]*DEADLINE_FACTOR+DEADLINE_MARGIN:.0f} s with margin, {ctx["remaining"]:.0f} s left; skipped in this job',flush=True);return None
        if k>=len(todo):k=None
    if _STOP['signum']is not None:return None
    log=run/'runner_logs'/f'idx{i}.{ctx["job"]}.{ctx["restart"]}.{time.time_ns()}.log';log.parent.mkdir(exist_ok=True)
    sd=ctx['scratch']/f'idx{i}';sd.mkdir(parents=True,exist_ok=True)
    cmd=[sys.executable,'-B',str(PRODUCTION),'run',str(run),'--index',str(i),'--threads',str(ctx['threads']),'--scratch',str(sd)]+(['--max-blocks',str(k)]if k else[])
    start=utc()
    try:
        with log.open('ab')as f:
            child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT);_STOP['child']=child
            if _STOP['signum']is not None:forward(child)  # a signal that came before the child was registered
            rc=child.wait()
    finally:_STOP['child']=None;shutil.rmtree(sd,ignore_errors=True)
    after=committed(x)
    outcome=('done'if after==x['nblocks']else'partial')if rc==0 else'term'if _STOP['signum']is not None else'failed'
    rec={'outcome':outcome,'job':ctx['job'],'restart':ctx['restart'],'host':ctx['host'],'start':start,'end':utc(),'rc':rc,'blocks_before':before,
         'blocks_after':after,'blocks':x['nblocks'],'max_blocks':k,'threads':ctx['threads'],'log':str(log)}
    append_attempt(run,i,rec);ctx['stats'][outcome]+=1
    if outcome=='done':publish_marker(run,'done',i,{'index':i,'utc':utc(),'job':ctx['job'],'blocks':x['nblocks']})
    if outcome=='failed':
        ctx['skip'].add(i)  # another job retries it; this one does not loop on it
        if failures(read_attempts(run,i))>=EXHAUST_AFTER:publish_marker(run,'exhausted',i,{'index':i,'utc':utc(),'job':ctx['job'],'failures':EXHAUST_AFTER})
    if outcome=='partial'and after==before:ctx['skip'].add(i)
    print(f'C8: index {i} ({x["group"]} shard {x["shard"]}): {outcome}, rc {rc}, blocks {before}->{after}/{x["nblocks"]}'+(f' (--max-blocks {k})'if k else'')+f'; log {log}',flush=True)
    return outcome

def run_job(a,env:dict)->int:
    run=Path(a.directory).resolve();m=read_plan(run);job=env.get('SLURM_JOB_ID');rs=env.get('SLURM_RESTART_COUNT')or'0'
    if not job:raise Refuse(64,'node_runner.py run runs inside a Slurm job (slurm/node_runner.sh); SLURM_JOB_ID is not set')
    if not rs.isdigit():raise Refuse(64,f'SLURM_RESTART_COUNT={rs!r} is not a count')
    threads=a.threads or int(env.get('SLURM_CPUS_PER_TASK')or 0)
    if threads<1:raise Refuse(64,'give --threads or run with SLURM_CPUS_PER_TASK set')
    t0=time.time();host=socket.gethostname()
    for s in STOP_SIGNALS:signal.signal(s,_on_signal)
    # Plans whose pins no longer hold would make every attempt fail: refuse before any claim.
    changed=prod.tool_changes(run)
    if changed:raise Refuse(64,f'pinned tools differ from the plan ({", ".join(sorted(changed))}); production.py run would refuse every index; nothing claimed')
    exe=campaign_executable(m)
    if not exe.is_file()or digest(exe)!=m['executable_sha256']:raise Refuse(64,f'{exe} is missing or is not the planned executable {m["executable_sha256"][:12]}; nothing claimed')
    state=identity_guard(run,exe,job,env)
    ctx={'job':job,'restart':int(rs),'host':host,'threads':threads,'scratch':Path(a.scratch or env.get('TMPDIR')or'/tmp'),'costs':bool(m.get('cost_model_sha256')),
         'skip':set(),'remaining':math.inf,'stats':{k:0 for k in('done','partial','failed','term','skipped','exhausted')}}
    print(f'C8: runner {job} (restart {rs}) on {host}: {threads} threads, identity {state}, {len(m["jobs"])} indices, deadline '+('per block (cost model)'if ctx['costs']else'none (no cost model)'),flush=True)
    rel=self_release(run,job,ctx['restart'])
    if rel:print(f'C8: released claims of this job\'s earlier incarnation: {rel}',flush=True)
    lays=layouts(run,m,ctx['costs']);code=0
    try:
        while _STOP['signum']is None:
            names={g:listing(run/'groups'/g/'checkpoints')for g in {x['group']for x in lays}}
            cands=[x for x in ordered(lays,ctx['costs'],names)if x['index']not in ctx['skip']and not marker(run,'done',x['index']).exists()
                   and not marker(run,'exhausted',x['index']).exists()and not claim_dir(run,x['index']).exists()]
            if not cands:break
            if ctx['costs']:ctx['remaining']=time_left(env,job)
            launched=False
            for x in cands:
                if _STOP['signum']is not None:break
                tok=take_claim(run,x['index'],owner_record(job,ctx['restart'],'node_runner.py run'))
                if tok is None:continue
                try:outcome=attempt(run,x,ctx)
                finally:
                    if not drop_claim(run,x['index'],tok):print(f'C8: claim {x["index"]} no longer carries this attempt\'s token (released meanwhile); left as it is',file=sys.stderr,flush=True)
                if outcome is not None:launched=True;break
            if not launched:break
    except Refuse as r:print(f'C8: {r}',file=sys.stderr,flush=True);code=r.code
    st=ctx['stats'];el=time.time()-t0
    print(f'C8: runner summary job={job} restart={rs} host={host} threads={threads} '+' '.join(f'{k}={v}'for k,v in st.items())+
          f' elapsed_s={el:.0f} node_hours={el/3600:.4f}',flush=True)
    if _STOP['signum']is not None:return 128+_STOP['signum']
    return code or (1 if st['failed']else 0)

# ---------------------------------------------------------------- status and retry
def status(run:Path)->dict:
    m=read_plan(run);n=len(m['jobs']);out={'indices':n,'done':[],'exhausted':[],'claimed':{},'failures_since_reset':{},'last_outcome':{}}
    for i in range(n):
        if marker(run,'done',i).exists():out['done'].append(i)
        if marker(run,'exhausted',i).exists():out['exhausted'].append(i)
        h=read_attempts(run,i)
        if h:out['last_outcome'][i]=h[-1].get('outcome')
        if failures(h):out['failures_since_reset'][i]=failures(h)
    out['claimed']=claims_of(run);out['remaining']=[i for i in range(n)if i not in set(out['done'])|set(out['exhausted'])]
    return out

def retry(run:Path,i:int,reason:str)->dict:
    m=read_plan(run)
    if not 0<=i<len(m['jobs']):raise Refuse(64,f'index {i} is outside the plan ({len(m["jobs"])} indices)')
    tok=take_claim(run,i,owner_record(None,0,'node_runner.py retry'))
    if tok is None:raise Refuse(75,f'index {i} is claimed ({claim_dir(run,i)}); nothing changed. Rerun when its runner has finished, or after site_submit.py release')
    try:
        append_attempt(run,i,{'outcome':'reset','utc':utc(),'operator':scheduler_user(),'host':socket.gethostname(),'reason':reason})
        was=marker(run,'exhausted',i).exists()
        try:marker(run,'exhausted',i).unlink()
        except FileNotFoundError:pass
    finally:drop_claim(run,i,tok)
    return {'index':i,'reset':True,'was_exhausted':was}

# ---------------------------------------------------------------- seeds (our forbidden-seed registry)
_SEEDS={}
def seed_tools(env:dict)->types.ModuleType:
    """Our tools/seeds.py (and its common.py), from C8_SEEDS_TOOL_DIR (default ~/c8ind/c8d2_seedtool/tools), executed
    from the very bytes whose sha256 equal the pins, under private module names (our common.py would shadow this
    package's). A mismatch or an unreadable file refuses (64)."""
    d=Path(env.get('C8_SEEDS_TOOL_DIR')or Path.home()/'c8ind/c8d2_seedtool/tools').resolve()
    if d in _SEEDS:return _SEEDS[d]
    data={}
    for n,h in SEED_PINS.items():
        try:b=(d/n).read_bytes()
        except OSError as x:raise Refuse(64,f'cannot read our seed tool {d/n}: {x}; deploy LRI_C8_D2_HPC aafa8a4 tools/{{seeds,common}}.py there (docs/SITES.md)')
        if hashlib.sha256(b).hexdigest()!=h:raise Refuse(64,f'{d/n} has sha256 {hashlib.sha256(b).hexdigest()}, not the pinned {h} (LRI_C8_D2_HPC aafa8a4); nothing done')
        data[n]=b
    def module(name,path,code):
        mod=types.ModuleType(name);mod.__file__=str(path);sys.modules[name]=mod;exec(compile(code,str(path),'exec'),mod.__dict__);return mod
    saved=sys.modules.get('common');path=list(sys.path)
    try:
        sys.modules['common']=module('c8ind_seed_common',d/'common.py',data['common.py'])
        sm=module('c8ind_seeds',d/'seeds.py',data['seeds.py'])
    finally:
        sys.path[:]=path
        if saved is None:sys.modules.pop('common',None)
        else:sys.modules['common']=saved
    _SEEDS[d]=sm;return sm

def seed_log(env:dict)->Path:
    if not env.get('C8_SEEDS'):raise Refuse(64,"set C8_SEEDS to this site's forbidden-seed log (slurm/env_<site>.sh does)")
    return Path(env['C8_SEEDS'])

def read_seed_log(sm,log:Path)->dict:
    try:return sm.read_log(log)
    except (OSError,ValueError)as x:raise Refuse(64,f'cannot read the seed log {log}: {x}; nothing done')

def seed_source(run:Path)->str:
    run=Path(run).resolve();return f'c8ind:{run}:{digest(run/"manifest.json")[:12]}'

def derived(seed:int)->dict:
    """{derived seed: role} of every group (production.derive_seeds, the c8-d2|seed|campaign|sector|L|role domain)."""
    return {v:f'{c}_{s}_L{L}:{role}'for c,s,L in prod.GROUPS for role,v in prod.derive_seeds(seed,c,s,L,'hashed').items()}

def collisions(seed:int,entries:list,exclude:str|None=None)->list:
    """Why `seed` collides: it or one of its derived seeds is in this package's seed_registry, or equals a logged base
    seed or one of that seed's derived seeds (our seeds.py `check` semantics). Entries of source `exclude` are skipped."""
    mine=derived(seed);reg=prod.seed_registry();known={**reg['net'],**reg['native'],**reg['bases']};out=[]
    if seed in known:out.append(f'base seed {seed} is in the package seed registry ({known[seed]})')
    out+=[f'derived seed {mine[v]}={v} is in the package seed registry ({known[v]})'for v in mine if v in known]
    for e in entries:
        b=e['seed'];src=e.get('source')or e.get('label')
        if exclude is not None and e.get('source')==exclude:continue
        if b==seed:out.append(f'base seed {seed} is logged ({src})');continue
        if b in mine:out.append(f'derived seed {mine[b]}={b} is logged as a base seed ({src})');continue
        theirs=derived(b)
        if seed in theirs:out.append(f'base seed {seed} is derived seed {theirs[seed]} of logged seed {b} ({src})');continue
        hit=sorted(set(mine)&set(theirs))
        if hit:out.append(f'derived seed {mine[hit[0]]}={hit[0]} is derived seed {theirs[hit[0]]} of logged seed {b} ({src})')
    return out

def ownership(seed:int,owner:str,entries:list)->list:
    """Problems with `owner` as the single owner of `seed` and its derived seeds in a log (empty: single ownership)."""
    own=[e for e in entries if e.get('source')==owner]
    out=[]if any(e['seed']==seed for e in own)else[f'seed {seed} is not logged under {owner}']
    return out+[f'{owner} also holds seed {e["seed"]}'for e in own if e['seed']!=seed]+collisions(seed,entries,exclude=owner)

def seed_reserve(run:Path,env:dict)->dict:
    """Reserve the base seed of a non-test campaign in this site's log: one seeds.reserve() transaction under the log's
    lock, whose check refuses any collision with the fresh log (entries of this campaign's own source excepted, so a
    retry is `present`)."""
    run=Path(run).resolve();m=read_plan(run)
    if m.get('test_only'):raise Refuse(64,'a test plan (--test-graphs > 0) is never reserved; its seed is only checked (node_runner.py seed check)')
    sm=seed_tools(env);log=seed_log(env);S=int(m['seed']);src=seed_source(run)
    try:r=sm.reserve(log,[(S,src)],lambda doc:collisions(S,doc['seeds'],exclude=src),command=f'c8ind seed reserve {run}')
    except sm.Refuse as x:raise Refuse(x.code,str(x))from None
    except (OSError,ValueError)as x:raise Refuse(64,f'seed log {log}: {x}; nothing registered')from None
    return {**r,'seed':S,'source':src,'state':'added'if r['added']else'present'}

def seed_check(run:Path,env:dict)->dict:
    run=Path(run).resolve();m=read_plan(run);sm=seed_tools(env);log=seed_log(env);S=int(m['seed'])
    return {'seed':S,'log':str(log),'test_only':bool(m.get('test_only')),'collisions':collisions(S,read_seed_log(sm,log)['seeds'])}

def load_log_entries(path:Path)->list:
    try:doc=json.loads(Path(path).read_bytes())
    except (OSError,ValueError)as x:raise Refuse(64,f'cannot read the seed log {path}: {x}')
    items=doc.get('seeds',doc.get('entries'))if isinstance(doc,dict)else None
    if not isinstance(items,list)or any(not isinstance(e,dict)or type(e.get('seed'))is not int for e in items):raise Refuse(64,f'{path} is not a c8-d2-seeds-1 seed log')
    return items

def write_receipt(a)->dict:
    probs=ownership(a.seed,a.owner,load_log_entries(a.union))
    if probs:raise Refuse(1,f'seed {a.seed} is not owned by {a.owner} alone in the union {a.union}: '+'; '.join(probs[:6])+'; no receipt written. Re-plan with a new seed')
    logs={}
    for spec in a.log:
        name,_,path=spec.partition('=')
        if not path:raise Refuse(64,f'--log takes NAME=FILE, not {spec!r}')
        logs[name]={'path':path,'sha256':digest(Path(path))}
    rec={'schema':RECEIPT_SCHEMA,'seed':a.seed,'owner':a.owner,'site':a.site,'logs':logs,'union_sha256':digest(Path(a.union)),'rounds':a.rounds,'utc':utc(),
         'check':'single owner of the seed and of its derived group seeds in the converged union of the two site logs and the mirror'}
    dump(Path(a.output),rec);return rec

# ---------------------------------------------------------------- command line
class Parser(argparse.ArgumentParser):
    def error(self,message):raise Refuse(64,f'{self.prog}: {message}')

def main(argv=None,env=None)->int:
    env=dict(os.environ)if env is None else env
    p=Parser(prog='node_runner.py',description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('run');q.add_argument('directory',type=Path);q.add_argument('--threads',type=int);q.add_argument('--scratch')
    q=s.add_parser('status');q.add_argument('directory',type=Path);q.add_argument('--json',action='store_true')
    q=s.add_parser('retry');q.add_argument('directory',type=Path);q.add_argument('--index',type=int,required=True);q.add_argument('--reason',default='')
    q=s.add_parser('seed');t=q.add_subparsers(dest='seed_command',required=True)
    for n in ('reserve','check','source'):t.add_parser(n).add_argument('directory',type=Path)
    q=t.add_parser('owner-check');q.add_argument('--log',type=Path,required=True);q.add_argument('--owner',required=True);q.add_argument('--seed',type=int,required=True)
    q=t.add_parser('receipt');q.add_argument('--union',type=Path,required=True);q.add_argument('--owner',required=True);q.add_argument('--seed',type=int,required=True)
    q.add_argument('--site',required=True,choices=('expanse','symmetry'));q.add_argument('--log',action='append',default=[]);q.add_argument('--rounds',type=int,default=0);q.add_argument('--output',type=Path,required=True)
    try:
        a=p.parse_args(argv)
        if a.command=='run':return run_job(a,env)
        if a.command=='status':
            r=status(Path(a.directory).resolve())
            if a.json:print(json.dumps(r,sort_keys=True))
            else:print(f'{len(r["done"])}/{r["indices"]} indices done; exhausted: {r["exhausted"]or"none"}; claimed: {sorted(r["claimed"])or"none"}; failures since reset: {r["failures_since_reset"]or"none"}')
            return 0
        if a.command=='retry':print(json.dumps(retry(Path(a.directory).resolve(),a.index,a.reason)));return 0
        c=a.seed_command
        if c=='source':print(seed_source(a.directory));return 0
        if c=='reserve':print(json.dumps(seed_reserve(a.directory,env)));return 0
        if c=='check':
            r=seed_check(a.directory,env);print(json.dumps(r))
            return 1 if r['collisions']else 0
        if c=='owner-check':
            probs=ownership(a.seed,a.owner,load_log_entries(a.log));print(json.dumps({'seed':a.seed,'owner':a.owner,'log':str(a.log),'single_owner':not probs,'problems':probs}))
            return 1 if probs else 0
        print(json.dumps(write_receipt(a)));return 0
    except Refuse as r:print(f'C8: {r}',file=sys.stderr,flush=True);return r.code

if __name__=='__main__':sys.exit(main())
