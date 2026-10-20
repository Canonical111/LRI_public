#!/usr/bin/env python3
"""C8(2) orchestration tests (PLAN component F; A-ORC-1..7, A-ORC-9..13, A-KER-1 grep, A-KER-3 plan side, A-EXP-2,
A-FLAG-6 provenance, A-IN-4 refusals) with a fake native worker (tests/fake_worker.py) and fake squeue, sbatch,
scontrol, sinfo, scancel and sacct: pure Python, no C++ build, runs anywhere (Python >= 3.10, numpy, scipy).

The tools run from an isolated copy of the package (tools/, slurm/, src/, vendor/, the inputs with hard-linked packs,
tests/fixtures, the archived records the seed registry reads, the pinned C7(2) calibration copy, fake bin/c8d2_decimal
and bin/c8d2_gmp), so nothing in the real package is written; files shared by hard link are never modified in place.
Plans use the test fixture tests/fixtures/inputs_mini (C8_INPUTS) unless a test says otherwise. On Linux with a built
bin/c8d2_gmp, A-ORC-13 runs the claim with the real worker (the Linux fingerprint path, J-VAL-1).
--only NAME,... runs the named tests of TESTS; an unknown name or an empty list is refused before any setup (exit 2),
a run that executes no test fails, and the record lists the requested and the executed tests. The test `drivers`
checks that, with test_pipeline.py's and validate.py's selections and vendored_isolated.py's records of an early stop
(checkpoint review T-02, T-03).
Usage: python3 -B tests/unit_orchestration.py [--output FILE] [--only NAME,...]
"""
from __future__ import annotations
import argparse,concurrent.futures,contextlib,errno,hashlib,io,json,math,os,re,shutil,signal,sqlite3,stat,struct,subprocess,sys,tempfile,threading,time
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
for k in list(os.environ):
    if k.startswith(('C7_','C8_','SBATCH_','SQUEUE_','SLURM_'))or k in('FAKE_LOG',):os.environ.pop(k)
os.umask(0o022)  # before common.py reads it
SEED=771100231

# ---------------------------------------------------------------- isolated package copy (tests/pkgcopy.py)
sys.path.insert(0,str(ROOT/'tests'))
from pkgcopy import FAKE_SHEBANG,link_or_copy,make_package  # noqa: E402

def replace_bytes(path:Path,data:bytes):
    """Write a NEW inode (never through a hard link shared with the real package)."""
    path.unlink();path.write_bytes(data)

MODULES=('common','prepare_inputs','production','assemble','lanes','slurm_submit','ledger','seeds','accounting','make_cost_model','calibrate','design','combine','verify_result','stage_runtime')
def load_modules(pkg:Path):
    """Import the COPIED tools in-process (their ROOT is the package copy)."""
    for name in MODULES+('validate',):sys.modules.pop(name,None)
    sys.path[:0]=[str(pkg/'tools'),str(pkg/'tests')]
    import production,assemble,slurm_submit,common,lanes,ledger,seeds,accounting,make_cost_model,calibrate,design,combine
    return NS(prod=production,asm=assemble,ss=slurm_submit,common=common,lanes=lanes,ledger=ledger,seeds=seeds,acc=accounting,mcm=make_cost_model,cal=calibrate,
              des=design,comb=combine)

def cli(mod,*argv,expect=0):
    """Run mod.main() in-process with argv; return code/stdout/stderr. expect=None accepts any outcome."""
    out,err=io.StringIO(),io.StringIO();code=0
    with mock.patch.object(sys,'argv',[mod.__file__,*map(str,argv)]),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
        try:
            rv=mod.main()
            if isinstance(rv,int):code=rv
        except SystemExit as e:
            code=e.code if isinstance(e.code,int)else(0 if e.code is None else 1)
            if e.code is not None and not isinstance(e.code,int):err.write(str(e.code))
        except Exception as e:code=1;err.write(f'{type(e).__name__}: {e}')
    r=NS(returncode=code,stdout=out.getvalue(),stderr=err.getvalue())
    if expect is not None and (code==0)!=(expect==0):raise AssertionError(f'{Path(mod.__file__).name} {argv}: exit {code}, expected {expect}\n{r.stderr[-3000:]}\n{r.stdout[-1500:]}')
    return r

def tool(pkg,script,*args,env=None,check=True,timeout=None):
    e={k:v for k,v in os.environ.items()};e['PYTHONDONTWRITEBYTECODE']='1';e.update(env or{})
    cp=subprocess.run([PY,'-B',str(pkg/'tools'/script),*map(str,args)],capture_output=True,text=True,env=e,timeout=timeout)
    if check and cp.returncode:raise AssertionError(f'{script} {args} failed ({cp.returncode}):\n{cp.stderr[-3000:]}\n{cp.stdout[-1000:]}')
    return cp

def manifest(d):return json.loads((Path(d)/'manifest.json').read_text())
def config(d,g):return json.loads((Path(d)/'groups'/g/'config.json').read_text())
def tree(d):return {str(p.relative_to(d)):digest(p)for p in sorted(Path(d).rglob('*'))if p.is_file()and '.c8_submit.lock'not in p.parts}
def digest(p:Path)->str:return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def roq(path:Path)->sqlite3.Connection:return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
def gone(d:Path)->bool:return not Path(d).exists()and not list(Path(d).parent.glob(Path(d).name+'.tmp.*'))

class Env:
    def __init__(self,pkg,M,td):
        self.pkg=pkg;self.M=M;self.td=td;self.scratch=td/'scratch';self.scratch.mkdir(exist_ok=True);self.fixture=pkg/'tests/fixtures/inputs_mini'
    def plan(self,d,*extra,expect=0,seed=SEED):
        return cli(self.M.prod,'plan',d,'--seed',seed,'--threads',2,'--checkpoint-tasks',8,*extra,expect=expect)
    def small(self,d,*extra,expect=0,seed=SEED,points=8,tg=2):
        """A tiny test-only pilot: P points, 2 replicates, the 2 cheapest graphs per group, fixed 4-point tasks, 2 shards."""
        return self.plan(d,'--pilot','--points',points,'--replicates',2,'--test-graphs',tg,'--bootstrap-chunk',4,'--shards',2,*extra,expect=expect,seed=seed)
    def run(self,d,i,*extra,expect=0):return cli(self.M.prod,'run',d,'--index',i,'--threads',2,'--scratch',self.scratch,*extra,expect=expect)
    def run_all(self,d):
        for j in manifest(d)['jobs']:self.run(d,j['id'])

def cost_model_for(E,d_or_inv,scale=None,backend='gmp',rates='default',keys=None):
    """A synthetic campaign-keyed cost model (seconds per point) for every graph of the fixture inventory."""
    inv=json.loads((E.fixture/'inventory.json').read_text())if keys is None else None;sp={}
    for c in ('a','b'):
        for s in ('free','power'):
            for L in range(3,9):
                for r in (inv[s][str(L)]if inv else[]):sp[f'{c}:{s}:{L}:{r["id"]}']=(scale(c,s,L,r)if scale else 1e-6)
    if keys:sp.update(keys)
    return {'schema':'c8-d2-cost-model-1','dimension':2,'order':8,'backend':backend,'numerics':'exact','rates_identity':rates,'seconds_per_point':sp,
            'cpu_models':['Synthetic CPU'],'cpu_class_factors':{},'lane_width':2,'executable_sha256':'0'*64}

# ---------------------------------------------------------------- fake Slurm (JSON-line queue file; every command logs its arguments)
FAKE_SQUEUE=r'''import json,os,pwd,sys
e=os.environ;args=sys.argv[1:];owner=pwd.getpwuid(os.getuid()).pw_name
open(e['FAKE_LOG'],'a').write(json.dumps({'cmd':'squeue','args':args,'SQUEUE_STATES':e.get('SQUEUE_STATES')})+'\n')
if e.get('FAKE_SQUEUE_FAIL'):sys.exit(1)
fmt=args[args.index('-o')+1]if '-o'in args else''
def opt(f):return args[args.index(f)+1]if f in args else None
if fmt=='%L':
    if e.get('FAKE_TIMELEFT'):print(e['FAKE_TIMELEFT']);sys.exit(0)
    sys.exit(1)
recs=[json.loads(l)for l in open(e['FAKE_SQUEUE_LINES'])if l.strip()]if os.path.exists(e['FAKE_SQUEUE_LINES'])else[]
u=opt('-u');acct=opt('-A');states=e.get('SQUEUE_STATES')
for r in recs:
    r={'comment':'x','task':'N/A','state':'PENDING','user':owner,'name':'job','partition':'part','qos':'normal','nodes':1,'account':'acct',**r}
    if u is not None and r['user']!=u:continue
    if acct is not None and r['account']!=acct:continue
    if states and r['state']not in states.split(','):continue
    if '--states=all'not in args and r['state']in('COMPLETED','CANCELLED','FAILED','TIMEOUT'):continue
    if r.get('hidden')and '--all'not in args:continue
    if r.get('raw')is not None:  # a verbatim admission line (the unparsable-line test)
        if fmt=='%i|%T|%P|%q|%D|%u|%j':print(r['raw'])
        continue
    if fmt=='%200k|%K|%T|%i':print(f"{r['comment']:<200}|{r['task']}|{r['state']}|{r['jobid']}")
    elif fmt=='%i|%T|%P|%q|%D|%u|%j':print(f"{r['jobid']}|{r['state']}|{r['partition']}|{r['qos']}|{r['nodes']}|{r['user']}|{r['name']}")
'''
FAKE_SBATCH=r'''import json,os,stat,sys
e=os.environ;args=sys.argv[1:];b=e.get('FAKE_SBATCH_BLOCK')
if '--test-only'in args:print('sbatch: Job 999 to start at 2026-10-04T00:00:00 using 1 processors (fake)',file=sys.stderr);sys.exit(0)
if b and os.path.exists(b)and stat.S_ISFIFO(os.stat(b).st_mode):
    with open(b)as f:f.readline()
    os.unlink(b)
script=os.path.basename(args[-1])
cnt=e['FAKE_COUNTER'];n=(int(open(cnt).read())if os.path.exists(cnt)else 700)+1
if e.get('FAKE_SBATCH_FAIL')or(e.get('FAKE_SBATCH_FAIL_MERGE')and script=='merge.sh')or(e.get('FAKE_SBATCH_FAIL_AFTER')and n>700+int(e['FAKE_SBATCH_FAIL_AFTER'])):
    print('sbatch: error: fake failure',file=sys.stderr);sys.exit(1)
open(cnt,'w').write(str(n))
if e.get('FAKE_SBATCH_RUN_ON_MERGE')and script=='merge.sh'and os.path.exists(e['FAKE_SQUEUE_LINES']):
    # a superseded merge starts while the new merge is being submitted (the O08 race)
    recs=[json.loads(l)for l in open(e['FAKE_SQUEUE_LINES'])if l.strip()]
    for r in recs:
        if r['jobid']==e['FAKE_SBATCH_RUN_ON_MERGE']:r['state']='RUNNING'
    open(e['FAKE_SQUEUE_LINES'],'w').write(''.join(json.dumps(r)+'\n'for r in recs))
last=lambda o:([a.split('=',1)[1]for a in args if a.startswith(o+'=')]or[None])[-1]
open(e['FAKE_SBATCH_LOG'],'a').write(json.dumps({'jobid':str(n),'args':args,'script':script,'env':{k:e.get(k)for k in('C8_RUN','C8_PACKAGE','C8_INDEX_OFFSET','C8_TEST_MARK','SBATCH_ACCOUNT','SBATCH_ARRAY_INX','SBATCH_DEPENDENCY','SBATCH_EXPORT','SBATCH_MEM_PER_CPU','SBATCH_MEM_PER_NODE')}})+'\n')
if e.get('FAKE_REGISTER'):
    c=last('--comment');arr=last('--array');part=last('--partition')or(args[args.index('-p')+1]if '-p'in args else'part');name=last('--job-name')
    acct=last('--account')or(args[args.index('-A')+1]if '-A'in args else'acct')
    with open(e['FAKE_SQUEUE_LINES'],'a')as q:
        if arr:
            for p in arr.split('%')[0].split(','):
                lo,_,hi=p.partition('-')
                for t in range(int(lo),int(hi or lo)+1):q.write(json.dumps({'comment':c,'task':str(t),'state':'PENDING','jobid':f'{n}_{t}','name':name,'partition':part,'account':acct})+'\n')
        else:q.write(json.dumps({'comment':c,'task':'N/A','state':'PENDING','jobid':str(n),'name':name,'partition':part,'account':acct})+'\n')
print(n)
'''
FAKE_SCONTROL=r'''import json,os,sys
e=os.environ;a=sys.argv[1:];open(e['FAKE_LOG'],'a').write(json.dumps({'cmd':'scontrol','args':a})+'\n')
if e.get('FAKE_SCONTROL_FAIL'):sys.exit(1)
if a[0:2]==['show','node']:print(f"NodeName={a[2]} Arch=x86_64 CoresPerSocket=20 ThreadsPerCore={json.loads(e.get('FAKE_TPC','{}')).get(a[2],1)} RealMemory=1");sys.exit(0)
q=e.get('FAKE_SQUEUE_LINES','');recs=[json.loads(l)for l in open(q)if l.strip()]if q and os.path.exists(q)else[]
rec=next((r for r in recs if r.get('jobid')==a[-1]),None)
if a[0]in('hold','release'):  # hold succeeds only for a pending job (slurmctld refuses a started one)
    if rec is None:print(f'Invalid job id specified for job {a[-1]}',file=sys.stderr);sys.exit(1)
    if a[0]=='hold'and rec.get('state','PENDING')!='PENDING'and not e.get('FAKE_HOLD_ACCEPTS_STARTED'):print(f'Job is no longer pending execution for job {a[-1]}',file=sys.stderr);sys.exit(1)
    rec['held']=a[0]=='hold';open(q,'w').write(''.join(json.dumps(r)+'\n'for r in recs));sys.exit(0)
lim=e.get('FAKE_TIMELIMIT','UNLIMITED')
if e.get('FAKE_TIMELIMIT_JOBS'):lim='1-00:00:00'if a[-1]in e['FAKE_TIMELIMIT_JOBS'].split(',')else'UNLIMITED'
print(f"JobId={a[-1]} JobName=x\n   UserId=t(1) JobState={(rec or{}).get('state','PENDING')} TimeLimit={lim} TimeMin=N/A")
'''
FAKE_SINFO=r'''import json,os,sys
e=os.environ;open(e['FAKE_LOG'],'a').write(json.dumps({'cmd':'sinfo','args':sys.argv[1:]})+'\n');print(e.get('FAKE_IDLE','3'))
'''
FAKE_SCANCEL=r'''import json,os,sys
e=os.environ;a=sys.argv[1:];open(e['FAKE_LOG'],'a').write(json.dumps({'cmd':'scancel','args':a})+'\n')
only=next((x.split('=',1)[1]for x in a if x.startswith('--state=')),None)  # --state=PENDING: the scheduler cancels only jobs in that state
q=e['FAKE_SQUEUE_LINES']
if os.path.exists(q):
    recs=[json.loads(l)for l in open(q)if l.strip()]
    for r in recs:
        if r['jobid']in a and (only is None or r.get('state','PENDING')==only):r['state']='CANCELLED'
    open(q,'w').write(''.join(json.dumps(r)+'\n'for r in recs))
'''
FAKE_SACCT=r'''import json,os,sys
e=os.environ;open(e['FAKE_LOG'],'a').write(json.dumps({'cmd':'sacct','args':sys.argv[1:]})+'\n')
if e.get('FAKE_SACCT_FAIL'):sys.exit(1)
ids=sys.argv[sys.argv.index('-j')+1].split(',')
for l in open(e['FAKE_SACCT_LINES']):
    if l.strip()and l.split('|')[1].split('_')[0]in ids:print(l.rstrip())
'''
import pwd
REAL_USER=pwd.getpwuid(os.getuid()).pw_name
FOREIGN=next(n for n in ('nobody','daemon','root','bin')if n!=REAL_USER and any(e.pw_name==n for e in pwd.getpwall()))

def fake_bin(td:Path)->Path:
    fb=td/'fakebin';fb.mkdir(exist_ok=True)
    for name,src in (('squeue',FAKE_SQUEUE),('sbatch',FAKE_SBATCH),('scontrol',FAKE_SCONTROL),('sinfo',FAKE_SINFO),('scancel',FAKE_SCANCEL),('sacct',FAKE_SACCT)):
        (fb/name).write_text(f'#!{PY}\n'+src);(fb/name).chmod(0o755)
    return fb

class Slurm:
    """The fake-Slurm environment of one test: queue file, logs and a call() helper running slurm/*.sh."""
    def __init__(self,E,name,**base):
        self.E=E;self.td=E.td/f'slurm_{name}';self.td.mkdir();fb=fake_bin(self.td);envsh=self.td/'env.sh'
        envsh.write_text(f'export C8_PYTHON={PY}\nexport C8_TEST_MARK=sourced\n')
        inherited={k:v for k,v in os.environ.items()if k not in('SBATCH_CLUSTERS','SLURM_CLUSTERS','SQUEUE_CLUSTERS','C8_TIME_POLICY','C8_SITE','C8_AMDQ_CAP')}
        self.base={**inherited,'PATH':f'{fb}:{os.environ["PATH"]}','C8_PACKAGE':str(E.pkg),'C8_ENV_SETUP':str(envsh),'C8_SBATCH_ARGS':'-A acct -p part',
                   'PYTHONDONTWRITEBYTECODE':'1','FAKE_LOG':str(self.td/'fake.log'),'FAKE_SQUEUE_LINES':str(self.td/'queue.jsonl'),'FAKE_SBATCH_LOG':str(self.td/'sbatch.log'),
                   'FAKE_COUNTER':str(self.td/'counter'),'FAKE_SACCT_LINES':str(self.td/'sacct.txt'),'USER':FOREIGN,'LOGNAME':FOREIGN,'HOME':str(self.td),
                   'C8_INPUTS':str(E.fixture),**base}
    def queue(self,*recs):(self.td/'queue.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in recs))
    def add(self,*recs):
        with (self.td/'queue.jsonl').open('a')as f:f.write(''.join(json.dumps(r)+'\n'for r in recs))
    def calls(self)->list:return [json.loads(l)for l in (self.td/'sbatch.log').read_text().splitlines()]if (self.td/'sbatch.log').exists()else[]
    def log(self)->list:return [json.loads(l)for l in (self.td/'fake.log').read_text().splitlines()]if (self.td/'fake.log').exists()else[]
    def call(self,script,args=(),keep=False,cmd=None,**extra):
        if not keep:(self.td/'sbatch.log').unlink(missing_ok=True)
        cp=subprocess.run(cmd or['bash',str(self.E.pkg/'slurm'/script),*map(str,args)],capture_output=True,text=True,env={**self.base,**extra})
        return cp,self.calls()

def last(args,opt):
    v=[a.split('=',1)[1]for a in args if a.startswith(opt+'=')]
    return v[-1]if v else None

# ---------------------------------------------------------------- Z13: unconditional cleanup of subprocess-based cases
def proc_table()->list[tuple[int,int,int,str,str]]:
    """(pid, ppid, pgid, state, command line) of every process (ps -A, Linux and macOS)."""
    cp=subprocess.run(['ps','-A','-o','pid=,ppid=,pgid=,stat=,args='],capture_output=True,text=True)
    rows=[]
    for line in cp.stdout.splitlines():
        f=line.split(None,4)
        if len(f)>=4 and f[0].isdigit()and f[1].isdigit()and f[2].isdigit():rows.append((int(f[0]),int(f[1]),int(f[2]),f[3],f[4]if len(f)>4 else''))
    return rows

def ancestry()->set[int]:
    """This process and its ancestors: never signalled by a cleanup."""
    up={pid:ppid for pid,ppid,*_ in proc_table()};out=set();p=os.getpid()
    while p and p not in out:out.add(p);p=up.get(p,0)
    return out

def release_fifo(fifo:Path)->None:
    """Wake a reader still blocked on the FIFO (in open or in its read) without ever blocking: a non-blocking writer
    (ENXIO when no reader has it open) writes one line; then the FIFO is removed."""
    try:
        fd=os.open(fifo,os.O_WRONLY|os.O_NONBLOCK)
        try:os.write(fd,b'cleanup\n')
        finally:os.close(fd)
    except OSError:pass
    with contextlib.suppress(FileNotFoundError):Path(fifo).unlink()

def fifo_go(fifo:Path,timeout:float=120.)->None:
    """Release the fake sbatch blocked on FAKE_SBATCH_BLOCK without blocking the test: a non-blocking writer, retried
    while no reader has the FIFO open (ENXIO; an AssertionError after the timeout instead of an open() that never
    returns), writes 'go' and stays open until the reader has consumed it (the fake removes the FIFO after its read)."""
    t0=time.time()
    while True:
        try:fd=os.open(fifo,os.O_WRONLY|os.O_NONBLOCK);break
        except OSError as e:
            if e.errno!=errno.ENXIO or time.time()-t0>timeout:raise AssertionError(f'no reader on the FIFO {fifo} after {time.time()-t0:.0f} s ({e})')from None
            time.sleep(0.05)
    try:os.write(fd,b'go\n');wait_for(lambda:not Path(fifo).exists(),timeout)
    finally:os.close(fd)

class Owned:
    """Z13 (S6E-R3-01): the processes a subprocess-based case owns, cleaned up unconditionally on every exit path (the
    test runner records a failure and continues, so nothing may outlive its case). add(proc) registers a direct child
    (a Popen, started with start_new_session=True so that its whole process group can be signalled); markers are
    strings unique to the case (its campaign or scratch path) that identify the processes it started indirectly in
    other sessions (lanes.py starts every production run in a session of its own, which the run's native worker
    inherits); fifos are its FIFO synchronization points. survivors(): the live (not zombie) owned processes: the
    unreaped children, every process whose command line holds a marker, the members of their process groups and all
    their descendants; never this process, its ancestors or its process group. On exit, if the case failed, the
    survivors are appended to the exception's message (failure evidence, taken before any cleanup); then every owned
    process group and process is killed (SIGKILL, repeated until none is left; an AssertionError after `grace` s),
    the direct children are reaped and their pipes closed, and each FIFO is released without blocking and removed.
    killed lists what had to be killed.
    W14 (Stage-6 fix round 4, S6E-R4-01): ownership was rebuilt from the processes visible at each call, so an unmarked
    helper (output redirected) of a registered session leader that had exited and been reaped (communicate(), wait())
    was neither an unreaped child, nor a marker match, nor a descendant of one (reparented away), and survived. add()
    now also retains the process group the child leads, established while the child is unreaped (its pid, and so the
    group's id, cannot have been reused yet): the child is its group's leader (start_new_session=True) and the group is
    neither this process's nor an ancestor's (a child in the runner's own group is owned by its pid only, as before).
    survivors() then includes every live member of a retained group, also after the leader's exit and reaping. A
    retained group is retired for good once its leader is reaped and no process of the group is left (from then on its
    id may be reused), or when a live process holds the id as its pid (a reuse: while the group has members POSIX
    reuses its id for no process). Out of reach, by design: an unmarked process that has left its group (setsid) once
    its owned parent has exited; the cases mark whatever starts sessions of its own (lanes.py's runs: the campaign or
    scratch path)."""
    def __init__(self,markers=(),fifos=(),grace:float=30.):
        self.markers=[str(m)for m in markers];self.fifos=[Path(f)for f in fifos];self.procs=[];self.grace=grace;self.killed=[]
        self.groups={}  # W14: retained process group id -> the registered child that leads it
    def add(self,proc):
        self.procs.append(proc)
        if proc.returncode is None:  # W14: unreaped, so proc.pid is still this child's (alive or a zombie)
            try:pg=os.getpgid(proc.pid)
            except OSError:pg=next((g for pid,_,g,_,_ in proc_table()if pid==proc.pid),None)  # a zombie (macOS refuses getpgid on it)
            if pg==proc.pid and pg!=os.getpgrp()and pg not in ancestry():self.groups[pg]=proc
        return proc
    def held(self,table)->set[int]:
        """W14: the retained groups still owned, given the process table (zombies included); retires the others."""
        out=set()
        for pg,p in list(self.groups.items()):
            if p.returncode is None:out.add(pg);continue  # the leader is unreaped: the id cannot have been reused
            if any(pid==pg for pid,*_ in table)or not any(g==pg for _,_,g,_,_ in table):del self.groups[pg];continue  # reused, or empty
            out.add(pg)
        return out
    def survivors(self)->list[tuple[int,int,str]]:
        table=proc_table();rows=[r for r in table if 'Z'not in r[3]];keep=ancestry();mypg=os.getpgrp();kids={}
        for pid,ppid,*_ in rows:kids.setdefault(ppid,[]).append(pid)
        roots={p.pid for p in self.procs if p.returncode is None}
        own={pid for pid,_,_,_,args in rows if pid in roots or any(m in args for m in self.markers)}
        groups=({pg for pid,_,pg,_,_ in rows if pid in own}|self.held(table))-{mypg}-keep
        own|={pid for pid,_,pg,_,_ in rows if pg in groups};todo=list(own)
        while todo:
            for c in kids.get(todo.pop(),[]):
                if c not in own:own.add(c);todo.append(c)
        return [(pid,pg,args[:200])for pid,_,pg,_,args in rows if pid in own and pid not in keep]
    def kill(self)->list:
        t0=time.time();killed=[];keep=ancestry();mypg=os.getpgrp()
        while True:
            left=self.survivors()
            if not left:return killed
            if time.time()-t0>self.grace:raise AssertionError(f'Z13: owned processes survive SIGKILL after {self.grace:g} s: {left[:10]}')
            for pid,pg,args in left:
                killed.append((pid,args))
                if pg>1 and pg!=mypg and pg not in keep:
                    with contextlib.suppress(OSError):os.killpg(pg,signal.SIGKILL)
                with contextlib.suppress(OSError):os.kill(pid,signal.SIGKILL)
            for p in self.procs:
                with contextlib.suppress(Exception):p.poll()  # reap a direct child, so that it is no zombie
            time.sleep(0.05)
    def __enter__(self):return self
    def __exit__(self,et,ev,tb):
        if isinstance(ev,Exception):
            try:left=self.survivors()
            except Exception as x:left=[f'(ps failed: {x})']
            if left:ev.args=((str(ev.args[0])if ev.args else'')+f' [Z13 cleanup: owned processes at the failure, before cleanup: {left[:12]}]',*ev.args[1:])
        try:self.killed=self.kill()
        finally:
            for p in self.procs:
                with contextlib.suppress(Exception):
                    if p.poll()is None:p.kill()
                with contextlib.suppress(Exception):p.wait(timeout=30)
                for f in (p.stdin,p.stdout,p.stderr):
                    if f is not None:
                        with contextlib.suppress(Exception):f.close()
            for f in self.fifos:release_fifo(f)
        return False

# ================================================================ pure checks
def test_literal_sizes():
    """A-KER-1: no literal C7(2) array size (6, 12, 14 or 28) remains in src/ or tests/point_checks.cpp, and
    kernel.hpp holds the one-order constants block with its static_asserts (PLAN component C)."""
    pat=re.compile(r'std::array<[^<>;]*?,\s*(?:6|12|14|28)\s*>|\b(?:ld|long double|double|float|int|unsigned|char|size_t|uint32_t|uint64_t|Q|MP|T)\s+[A-Za-z_]\w*\s*\[\s*(?:6|12|14|28)\s*\]')
    files=sorted((ROOT/'src').glob('*.[ch]pp'))+[ROOT/'tests/point_checks.cpp']
    hits=[f'{f.relative_to(ROOT)}:{n}: {line.strip()}'for f in files for n,line in enumerate(f.read_text().splitlines(),1)if pat.search(line)]
    assert not hits,hits
    old={f.name:sum(bool(pat.search(l))for l in f.read_text().splitlines())for f in (ROOT/'reference/c7d2_hpc_a55958f/src').glob('*.[ch]pp')}
    assert old=={'kernel.hpp':5,'c7d2_integrate.cpp':3},old
    assert pat.search('        ld lx[14],shift=0;')and not pat.search('uint64_t seed=std::stoull(argv[6]);')
    k=(ROOT/'src/kernel.hpp').read_text()
    for need in ('constexpr int LMAX=8;','constexpr int ORDER_MIN=7, ORDER_MAX=8;','constexpr int EMAX=2*LMAX;','constexpr int KMAX=ORDER_MAX-2;','constexpr int NLOGS=KMAX+1;',
                 'constexpr int NVALUES=2*NLOGS;','constexpr int DIMMAX=4*LMAX-1;','static_assert(EMAX<=31','static_assert(DIMMAX>=2*EMAX-1','static_assert(NLOGS==KMAX+1 && NVALUES==2*(KMAX+1)',
                 'static_assert(std::tuple_size<decltype(Scratch::x)>::value==EMAX'):
        assert need in k,need
    ok('literal_sizes_and_constants',files=[str(f.relative_to(ROOT))for f in files])

def test_static(M):
    p=M.prod
    good=[[],['-A','acct','-p','amdq'],['-Aacct','--partition=defq','--time=00:10:00','-c','4','--mem=8G','--qos=normal','--requeue','-J','x','--exclude=cn112']]
    bad=[['--nice','--export-file=f'],['--nice'],['--nice=5'],['--export-file=f'],['--export-f=f'],['--export=ALL'],['--arr=0-3'],['--array','0-3'],['-a','0-3'],['-a0-3'],['--dep','x'],['-d','afterok:1'],
         ['--comment=x'],['--comm=x'],['-o','x'],['--output=x'],['--parsable'],['-M','other'],['--clusters=x'],['foo'],['--nodes=2'],['--wrap=cmd'],['-A'],['--time'],['--exclusive']]
    assert all(p.check_sbatch_args(g)is None for g in good),[p.check_sbatch_args(g)for g in good]
    assert all(p.check_sbatch_args(b)for b in bad),[b for b in bad if not p.check_sbatch_args(b)]
    assert p.time_option(['-A','x','--time=1:00'])=='1:00'and p.time_option(['-t','5','-p','q'])=='5'and p.time_option(['-t7'])=='7'and p.time_option(['--time','2'])=='2'and p.time_option(['-A','t','-p','x'])is None
    assert p.time_option(['--job-name','-trial'])is None  # a value is never read as an option (C7I-17)
    assert p.windows([0,1,2,5,1003],1000)==[{'offset':0,'array':'0-2,5'},{'offset':1000,'array':'3'}]and p.ranges([3,1,2,7])=='1-3,7'
    assert [p.merge_passes(n,F)for n,F in ((1,64),(64,64),(65,64),(500,64),(500,16),(500,2),(512,2),(4096,64),(4097,64))]==[1,1,2,2,3,9,9,2,3]
    with mock.patch.dict(os.environ,{},clear=False):
        for k in ('CXX','CPPFLAGS','OPTFLAGS','CXXFLAGS','LDFLAGS','LDLIBS'):os.environ.pop(k,None)
        assert M.common.cxx_command(['src/c8d2_integrate.cpp'],'bin/c8d2_decimal')==['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math','src/c8d2_integrate.cpp','-lquadmath','-o','bin/c8d2_decimal']
    mk=(ROOT/'Makefile').read_text();assert 'OPTFLAGS ?= -O3'in mk and 'override C8_REQUIRED = -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math'in mk
    for name in ('run_array.sh','merge.sh','lane_worker.sh','plan.sh'):
        t=(ROOT/'slurm'/name).read_text()
        assert '#SBATCH --nodes=1'in t and '#SBATCH --ntasks=1'in t and '#SBATCH --job-name=c8d2-'in t,name
        assert t.index('set -eo pipefail')<t.index('source "$C8_ENV_SETUP"')<t.index('set -u'),name
    assert 'C8_INDEX_OFFSET'in (ROOT/'slurm/run_array.sh').read_text()and 'OMP_PROC_BIND=close'in (ROOT/'slurm/run_array.sh').read_text()
    assert '--no-requeue'in (ROOT/'slurm/plan.sh').read_text()and 'ledger.py" register'in (ROOT/'slurm/plan.sh').read_text()
    for name in ('submit.sh','resubmit.sh'):assert 'version_info>=(3,10)'in (ROOT/'slurm'/name).read_text()and 'slurm_submit.py'in (ROOT/'slurm'/name).read_text()
    assert '--fast'in (ROOT/'slurm/merge.sh').read_text()and '--jobs "${C8_MERGE_JOBS:-24}"'in (ROOT/'slurm/merge.sh').read_text()
    # D8: plan has no --sum-mode, --seed-scheme, --chunk-points, --multiplier, --power-divisor or --primitive-* option.
    for opt in ('--sum-mode','--seed-scheme','--chunk-points','--multiplier','--power-multiplier','--power-divisor','--primitive-mode','--primitive-points','--primitive-allocation'):
        r=cli(p,'plan','/nonexistent/x','--seed',1,opt,'1',expect=2);assert 'unrecognized arguments'in r.stderr,(opt,r.stderr[-200:])
    assert len(p.GROUPS)==24 and [p.group_name(*g)for g in p.GROUPS[:2]]==['a_free_L3','a_free_L4']and p.group_name('b','power',8)=='b_power_L8'
    assert (p.SCHEMA,p.GROUP_SCHEMA,p.MERGED_SCHEMA,p.NATIVE_SCHEMA,p.COST_SCHEMA,p.RATES_SCHEMA,p.DESIGN_SCHEMA,p.BOOT_SCHEMA)==(
        'c8-d2-production-1','c8-d2-group-1','c8-d2-merged-1','c8-d2-hpc-native-1','c8-d2-cost-model-1','c8-d2-rates-1','c8-d2-design-1','c8-d2-bootstrap-proxy-1')
    assert p.COST_KEY.fullmatch('a:free:8:123')and not p.COST_KEY.fullmatch('free:8:123')and not p.COST_KEY.fullmatch('c:free:8:1')and not p.COST_KEY.fullmatch('a:free:9:1')
    ok('static_allowlist_templates_names_removed_options',refused=len(bad))

def test_seeds(E):
    """A-ORC-1: hashed seeds distinct over 24 groups and both roles; the D9 registry refuses listed seeds, base or derived;
    a non-test plan without --forbid-seeds-from refuses; tools/seeds.py add is atomic under concurrent use."""
    p=E.M.prod
    h={(c,s,L,r):p.derive_seeds(SEED,c,s,L)[r]for c,s,L in p.GROUPS for r in('native','net')};assert len(set(h.values()))==48
    assert p.derive_seeds(SEED,'a','free',3)['native']==int.from_bytes(hashlib.sha256(f'c8-d2|{SEED}|a|free|L3|native'.encode()).digest()[:8],'little')%2**63
    reg=p.seed_registry()
    for s in (8885400701634497064,326694507229394458,2765894070584243940,12983,837425,915437):assert s in reg['bases']
    derived=p._c7_legacy(8885400701634497064,'a','free',7)['native'];assert derived in reg['native']
    for s,why in ((8885400701634497064,'known archived or used base seed'),(derived,'derived group seed'),(p._c7_legacy(326694507229394458,'b','power',5)['net'],'derived group seed')):
        d=E.td/f'seed_{s}';r=E.small(d,seed=s,expect=1);assert why in r.stderr and gone(d),(s,r.stderr[-300:])
    fb=E.td/'forbid.json';fb.write_text(json.dumps({'schema':'c8-d2-seeds-1','seeds':[{'seed':4242,'source':'test'}]}))
    d=E.td/'seed_forbid';r=E.small(d,'--forbid-seeds-from',fb,seed=4242,expect=1);assert 'forbidden seed'in r.stderr and gone(d)
    assert p.seed_refusal(4243,{4242:'x'})is None
    # derived-seed collision with a forbidden base: inject the forbidden seed's own group seed as a "base"
    g=p.derive_seeds(4242,'b','power',8)['net'];assert 'derived group seed'in (p.seed_refusal(g,{4242:'x'})or'')
    d=E.td/'nonfree';r=E.plan(d,'--pilot','--replicates',2,'--shards',1,expect=1);assert '--forbid-seeds-from'in r.stderr or 'non-test plan'in r.stderr,r.stderr[-300:]
    # tools/seeds.py: atomic under concurrent use (16 processes add distinct seeds at once; all land; none twice)
    log=E.td/'seedlog.json';tool(E.pkg,'seeds.py','init','--log',log)
    with concurrent.futures.ThreadPoolExecutor(16)as ex:rcs=list(ex.map(lambda i:tool(E.pkg,'seeds.py','add','--seed',1000+i,'--label',f'c{i}','--log',log,check=False).returncode,range(16)))
    doc=json.loads(log.read_text());assert rcs==[0]*16 and sorted(e['seed']for e in doc['seeds'])==list(range(1000,1016)),(rcs,doc)
    r=tool(E.pkg,'seeds.py','add','--seed',1003,'--label','c3','--log',log);assert json.loads(r.stdout)['state']=='present'and len(json.loads(log.read_text())['seeds'])==16
    assert not Path(str(log)+'.lock').exists()
    r=tool(E.pkg,'seeds.py','check','1005','--log',log,check=False);assert r.returncode==1 and json.loads(r.stdout)['forbidden']
    # merge (two sites, two logs): the union, nothing dropped or reordered, idempotent; the first symmetry log's
    # layout ("entries") is read and rewritten as c8-d2-seeds-1; a file that is not a log is refused, the target unchanged
    leg=E.td/'sym_legacy.json';leg.write_text(json.dumps({'schema':'c8-d2-seeds-1','created':'2026-10-03','description':'d','entries':[{'seed':7,'source':'sym only'}]}))
    before=json.loads(log.read_text())['seeds']
    r=tool(E.pkg,'seeds.py','merge',log,'--log',leg);m1=json.loads(r.stdout);dl=json.loads(leg.read_text())
    assert 'entries'not in dl and dl['created']=='2026-10-03'and dl['seeds'][0]=={'seed':7,'source':'sym only'}and m1['added']==16 and m1['distinct_seeds']==17
    assert [(e['seed'],e['source'])for e in dl['seeds'][1:]]==[(e['seed'],e['source'])for e in before]and all(e['merged_from']==str(log.resolve())for e in dl['seeds'][1:])
    r=tool(E.pkg,'seeds.py','merge',leg,'--log',log);m2=json.loads(r.stdout);dx=json.loads(log.read_text())['seeds']
    assert m2['added']==1 and dx[:16]==before and dx[16]['seed']==7 and {e['seed']for e in dx}=={e['seed']for e in dl['seeds']}
    snap=log.read_bytes();r=tool(E.pkg,'seeds.py','merge',leg,'--log',log);assert json.loads(r.stdout)['added']==0 and log.read_bytes()==snap
    bad=E.td/'notalog.json';bad.write_text('[1,2]');r=tool(E.pkg,'seeds.py','merge',bad,'--log',log,check=False);assert r.returncode==2 and log.read_bytes()==snap
    assert 7 in p.read_seed_file(log)and not Path(str(log)+'.lock').exists()
    ok('seeds_hashed_registry_forbidden_concurrent_log_merge',registry_bases=len(reg['bases']))

def test_c7_refused(E):
    """A-ORC-1/D10: a C7 manifest is refused with the message naming LRI_C7_D2_HPC@a55958f by every entry point."""
    for schema in ('c7-d2-production-1','c7-d2-production-2'):
        v=E.td/f'c7run_{schema}';(v/'groups').mkdir(parents=True);(v/'manifest.json').write_text(json.dumps({'schema':schema,'dimension':2,'order':7,'jobs':[],'groups':[]}))
        for args in (('production.py','run',v,'--index',0),('production.py','merge',v),('production.py','status',v),('assemble.py',v)):
            mod=E.M.prod if args[0]=='production.py'else E.M.asm;r=cli(mod,*args[1:],expect=1);assert 'LRI_C7_D2_HPC@a55958f'in r.stderr,(args,r.stderr[-300:])
        code=E.M.ss.main(['lanes','1'],{'C8_RUN':str(v),'PATH':os.environ['PATH']});assert code==64
    ok('c7_manifest_refused_everywhere')

def test_inputs_refusals(E):
    """A-IN-4: a one-byte change to packs/free_L8.pack makes plan fail and create nothing; a non-test plan with a foreign
    C8_INPUTS refuses; C8_INPUTS outside the package is refused; a fixture plan must be test-only."""
    pack=E.fixture/'packs/free_L8.pack';orig=pack.read_bytes()
    try:
        replace_bytes(pack,orig[:-1]+bytes([orig[-1]^1]));d=E.td/'badpack';r=E.small(d,expect=1)
        assert 'Checksum mismatch in the inputs'in r.stderr and 'packs/free_L8.pack'in r.stderr and gone(d),r.stderr[-400:]
    finally:replace_bytes(pack,orig)
    d=E.td/'nontest_fixture';fs=E.td/'fs.json';fs.write_text('[]')
    r=E.plan(d,'--pilot','--replicates',2,'--shards',1,'--forbid-seeds-from',fs,'--cost-model',E.td/'none.json',expect=1)
    assert 'non-test plan uses the package\'s inputs/ only'in r.stderr and gone(d),r.stderr[-300:]
    with mock.patch.dict(os.environ,{'C8_INPUTS':str(E.td)}):
        d=E.td/'foreign_inputs';r=E.small(d,expect=1);assert 'not inside the package'in r.stderr and gone(d)
    ok('inputs_refusals_one_byte_pack_foreign_inputs')

def test_executable_identity(E):
    """A-KER-3 (plan side): plan refuses diagnostic and sanitizer executables, and a numerics profile other than exact
    without D1's explicit flag; a stale build record is refused."""
    exe=E.pkg/'bin/c8d2_gmp'
    for env,needle in (({'C8_FAKE_DIAGNOSTIC':'1'},'diagnostic build'),({'C8_FAKE_NUMERICS':'dd'},'reports numerics')):
        with mock.patch.dict(os.environ,env):d=E.td/f'diag_{len(needle)}';r=E.small(d,expect=1);assert needle in r.stderr and gone(d),r.stderr[-300:]
    d=E.td/'numerics_unapproved';r=E.small(d,'--numerics','dd',expect=1);assert '--approved-numerics-change'in r.stderr and gone(d)
    d=E.td/'numerics_missing';r=E.small(d,'--numerics','dd','--approved-numerics-change','user 2026-10-03',expect=1);assert 'c8d2_gmp_dd'in r.stderr and gone(d),r.stderr[-300:]
    br=exe.with_name('c8d2_gmp.build.json');rec={'schema':'c8-d2-build-record-1','executable_sha256':'0'*64}
    br.write_text(json.dumps(rec))
    try:d=E.td/'stale_record';r=E.small(d,expect=1);assert 'different executable'in r.stderr and gone(d)
    finally:br.unlink()
    ok('plan_refuses_diagnostic_sanitizer_and_unapproved_numerics')
    test_numerics_profile_campaign(E)

def test_development_overrides(E,exe,appr):
    """G4c D2: every profile's development variant is refused by plan through --describe (mp256 and exp1, whose
    parameter overrides now mark "development":true, and the combination, as dd's), and through the build record: a
    record whose compile command overrides a profile parameter or gives a C8_NX_* hook (build_record.py records
    parameter_overrides and "development"), also a record written before those fields existed (production.py
    recomputes them from compiler_options). The same record without the override is accepted."""
    for prof in ('mp256','exp1','dd+mp256+exp1'):
        px=E.pkg/f'bin/c8d2_gmp_{prof}';px.write_text(FAKE_SHEBANG+(ROOT/'tests/fake_worker.py').read_text());px.chmod(0o755)
        try:
            with mock.patch.dict(os.environ,{'C8_FAKE_DEVELOPMENT':'1'}):d=E.td/f'nx_dev_{prof.replace("+","_")}';r=E.small(d,'--numerics',prof,*appr,expect=1)
            assert 'development build'in r.stderr and repr([prof.split('+')[0]])[1:-1]in r.stderr and gone(d),(prof,r.stderr[-300:])
        finally:px.unlink()
    sys.modules.pop('build_record',None);import build_record as BR
    assert Path(BR.__file__).resolve().parent==(E.pkg/'tools').resolve()
    br=exe.with_name(exe.name+'.build.json');base=['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math','-DC8_USE_GMP','-DC8_NUMERICS','-DC8_NUMERICS_DD']
    tail=['src/c8d2_integrate.cpp','-lquadmath','-lgmp','-o','bin/c8d2_gmp_dd']
    try:
        for extra in (['-DC8_DD_DEVELOPMENT','-DC8_DD_RATIO=1e-21'],['-DC8_MP256_RATIO=1e-60'],['-DC8_EXP1_RANGE=4000'],['-D','C8_NX_XS_Q(e)=e']):
            rec=BR.main(exe,'gmp',base+extra+tail);want=[extra[0]+extra[1]]if extra[0]=='-D'else extra
            assert rec['parameter_overrides']==want and rec['development']is True,(extra,rec['parameter_overrides'])
            d=E.td/'nx_override';r=E.small(d,'--numerics','dd',*appr,expect=1)
            assert 'development build (profile-parameter overrides'in r.stderr and gone(d),(extra,r.stderr[-300:])
        old=json.loads(br.read_text());old.pop('parameter_overrides');old.pop('development');br.write_text(json.dumps(old))
        d=E.td/'nx_override_old';r=E.small(d,'--numerics','dd',*appr,expect=1);assert 'profile-parameter overrides'in r.stderr and gone(d),r.stderr[-300:]
        rec=BR.main(exe,'gmp',base+tail);assert rec['parameter_overrides']==[]and rec['development']is False
        d=E.td/'nx_no_override';E.small(d,'--numerics','dd',*appr);assert manifest(d)['build_record']['parameter_overrides']==[]
    finally:br.unlink(missing_ok=True)
    ok('G4c_D2_development_overrides_refused_describe_and_build_record',profiles=['mp256','exp1','dd+mp256+exp1'])

def test_numerics_profile_campaign(E):
    """A-FLAG-1/2 plumbing (Stage 4c) with a fake opt-in profile executable bin/c8d2_gmp_dd (the fake worker reports the
    profile of its file name): the canonical profile name (common.numerics_name, the Makefile's rule) and its refusals;
    plan refuses a development build of the profile; plan --numerics dd with the approval records numerics, approval and
    executable in the manifest; status prints the profile and the approval (text and --json); a checkpoint whose native
    numerics differ is refused; merge and assemble carry and print the profile; a non-test plan from a bundle frozen for
    another profile is refused (the bundle pin); combine refuses batches of different profiles (also tested on loaded
    batch records in test_pipeline.py)."""
    p=E.M.prod;nn=E.M.common.numerics_name;appr=('--approved-numerics-change','user approval 2026-10-05 (unit test)')
    assert E.M.common.NUMERICS_PROFILES==('dd','mp256','exp1')
    for raw,want in (('exact','exact'),('dd','dd'),('exp1,dd','dd+exp1'),('exp1+mp256+dd','dd+mp256+exp1'),('mp256','mp256')):assert nn(raw)==want,(raw,nn(raw))
    for raw,needle in (('mpconv','not implemented'),('dd+mpconv','not implemented'),('foo','unknown profile'),('dd+dd','named twice'),('exact+dd','does not combine'),('','name exact'),('dd+','name exact')):
        try:nn(raw);raise AssertionError(f'accepted {raw!r}')
        except ValueError as e:assert needle in str(e),(raw,str(e))
    mk=(ROOT/'Makefile').read_text();assert re.search(r'^override NX_KNOWN = dd mp256 exp1$',mk,re.M),'the Makefile and common.NUMERICS_PROFILES differ'
    hx=(ROOT/'src/numerics/numerics.hpp').read_text();hx=hx[hx.index('constexpr Name make_name()'):hx.index('inline constexpr Name profile_name')]
    assert re.findall(r'^\s+"(\w+)",$',hx,re.M)==list(E.M.common.NUMERICS_PROFILES),'src/numerics/numerics.hpp builds the name in another order'
    exe=E.pkg/'bin/c8d2_gmp_dd';exe.write_text(FAKE_SHEBANG+(ROOT/'tests/fake_worker.py').read_text());exe.chmod(0o755)
    try:
        for args,needle in ((('--numerics','exp1+dd',*appr),"canonical profile name is 'dd+exp1'"),(('--numerics','mpconv',*appr),'not implemented'),
                            (('--numerics','foo',*appr),'unknown profile'),(('--numerics','dd','--approved-numerics-change','  '),'--approved-numerics-change'),
                            (('--numerics','mp256',*appr),'c8d2_gmp_mp256')):
            d=E.td/f'nx_refused_{len(needle)}';r=E.small(d,*args,expect=1);assert needle in r.stderr and gone(d),(args,r.stderr[-300:])
        # a development build of the profile (a measurement variant, "development":true in numerics_params) is refused
        with mock.patch.dict(os.environ,{'C8_FAKE_DEVELOPMENT':'1'}):
            d=E.td/'nx_development';r=E.small(d,'--numerics','dd',*appr,expect=1)
        assert 'development build'in r.stderr and gone(d),r.stderr[-300:]
        test_development_overrides(E,exe,appr)
        d=E.td/'nx_dd';E.small(d,'--numerics','dd',*appr);m=manifest(d)
        assert m['numerics']=='dd'and m['approved_numerics_change']==appr[1]and m['executable']=='c8d2_gmp_dd'and m['executable_sha256']==digest(exe)and m['build']['numerics']=='dd'
        assert all(config(d,g['name'])['numerics']=='dd'for g in m['groups'])
        st=cli(p,'status',d,expect=1);assert f'numerics dd, rates identity default (approved numerics change: {appr[1]}) -- OPT-IN NUMERICS CHANGE (D1)'in st.stdout,st.stdout[:400]
        js=json.loads(cli(p,'status',d,'--json',expect=1).stdout);assert js['numerics']=='dd'and js['approved_numerics_change']==appr[1]and js['rates_identity']=='default'
        j0=m['jobs'][0]
        with mock.patch.dict(os.environ,{'C8_FAKE_NUMERICS':'exact'}):r=E.run(d,j0['id'],expect=1)
        assert 'native metadata mismatch: numerics'in r.stderr and not list((d/'groups'/j0['group']/'checkpoints').glob('*.json')),r.stderr[-300:]
        E.run_all(d);assert cli(p,'status',d).returncode==0
        for f in (d/'groups').glob('*/checkpoints/*.json'):assert json.loads(f.read_text())['native']['numerics']=='dd'
        cli(p,'merge',d);r=cli(E.M.asm,d,'--bootstrap',0);assert json.loads(r.stdout.splitlines()[0])['numerics']=='dd'
        assert json.loads((d/'C8_test_result.json').read_text())['numerics']=='dd'
        st=cli(p,'status',E.td/'nx_dd');assert 'numerics dd'in st.stdout
        # an exact campaign prints the exact path without the change marker
        d2=E.td/'nx_exact';E.small(d2);st=cli(p,'status',d2,expect=1);assert 'numerics exact, rates identity default\n'in st.stdout and 'OPT-IN'not in st.stdout,st.stdout[:300]
    finally:exe.unlink()
    ok('A-FLAG-1_2_profile_name_manifest_status_checkpoint_assemble',profile='dd')

def gate_doc(inv:dict,profile='dd+mp256',profile_sha='e'*64)->dict:
    """A passed full-scale J-FLAG gate record (schema c8-d2-numerics-flags-1) with every field design.check_gate reads,
    including the Stage-6 fix round 1 evidence: F1 coverage (X1), the build binding (X2), the F5 team sizes (X3)."""
    graphs={f'{c}_{s}_L{L}':len(inv[s][str(L)])for c in 'ab'for s in ('free','power')for L in range(3,9)}
    snap='5'*64;bound=lambda sha:{'sha256':sha,'reproduced_sha256':sha,'reproduced':True,'snapshot_sha256':snap}
    byL=lambda:{'7':{'graphs':200,'points_per_graph':256,'points_baseline':51200,'points_profile':51200},'8':{'graphs':400,'points_per_graph':64,'points_baseline':25600,'points_profile':25600}}
    cov={'complete':True,'why':[],'scale':1.0,'profile_checked':True,'sectors':{s:{'doublings':0,'binary128_accepted':20000,'mp_promoted':2000,'need_met':True,'by_L':byL()}for s in ('free','power')}}
    return {'schema':'c8-d2-numerics-flags-1','mode':'profile','profile_name':profile,'status':'passed','development':[],'verdicts':{'F1':True,'F2':True,'F5':True},
            'exact':{'sha256':'0'*64,'build_record':{'gmp_library':{'sha256':'1'*64}}},
            'profile':{'sha256':profile_sha,'describe':{'numerics':profile,'compiler':'fake'},'build_record':{'development':False,'parameter_overrides':[],'gmp_library':{'sha256':'1'*64}}},
            'build_binding':{'schema':'c8-d2-build-binding-1','snapshot':{'sha256':snap,'files':{}},'executables':{'exact':bound('0'*64),'profile':bound(profile_sha)}},
            'F1':{'verdict':{'passed':True,'violations':0},'coverage':cov,'tool_snapshot_sha256':snap,'baseline_binding':bound('0'*64),'tool_gmp_library':gate_libs()['_libs']['tool']},
            'F2':{'graphs':graphs,'total':{'dC8':1e-16,'se':1e-16,'bound':4e-16,'passed':True,'resolved':True}},'F5':{'passed':True,'team_sizes_verified':True},
            'environment':{'host':'fake','cpu_model':'fake CPU'},'utc_start':'2026-10-05T00:00:00Z',
            'f1_baseline':dict(gate_libs()['f1_baseline'],inputs_manifest_sha256=digest(ROOT/'inputs/manifest.json')),
            'inputs':{'schema':'c8-d2-gate-inputs-1','folder':'inputs','manifest_sha256':digest(ROOT/'inputs/manifest.json'),'verified':True,'verified_at_end':True,
                      'skipped':[],'complete':True}}

def gate_libs(w:str='1'*64)->dict:
    """Z19 downstream (fix round 3): the libgmp provenance check_gate requires; merged into gate_doc's record."""
    lib={'tool':{'sha256':w},'worker_now':{'sha256':w},'want_sha256':w,'match':True}
    return {'f1_baseline':{'path':'f1_baseline','sha256':'2'*64,'reused':False,'reused_gmp_library':None,'tool_gmp_library':dict(lib)},
            '_libs':{'exact':w,'profile':w,'tool':dict(lib)}}

def test_route_b_records(E):
    """Stage 6 (the last verifier's LOW items): every refusal branch of production.route_b (the incomplete or inconsistent
    route-(b) record: route, profile, exact pilot, approval, gates, cost model; the profile outside APPROVED_PROFILES; a
    differing pilot without the record; final: no cost model, a cost model of another numerics identity, an ungated
    executable in a non-test plan, recorded as ungated in a test-only one), of design.check_gate (not JSON, schema,
    mode and profile, status, development, F1/F2/F5 verdicts, the F2 total not passed or not resolved, the describe
    numerics, a development build, no sha256, not full scale) and of production.gated_route (a gate named twice, an
    executable no gate covers), each by its message; the complete record and gate are accepted."""
    p,D=E.M.prod,E.M.des;inv=json.loads((E.fixture/'inventory.json').read_text())
    assert p.APPROVED_PROFILE_PILOTS=={}and p.APPROVED_RATES=={}and sorted(p.APPROVED_PROFILES)==['dd+mp256']
    sha='a'*64;cm={'numerics':'dd+mp256','sha256':'c'*64}
    ev={'F1_coverage':{'free':{'binary128_accepted':29284,'mp_promoted':3541},'power':{'binary128_accepted':50625,'mp_promoted':12568}},
        'source_snapshot_sha256':'5'*64,'F5_team_sizes_verified':True,  # the X1-X3 evidence of the current check_gate
        'gmp_library':{'exact':'1'*64,'profile':'1'*64,'f1_baseline_reused':False},  # and (fix round 3, Z19 downstream) the libgmp provenance
        'inputs_manifest_sha256':'6'*64}  # and (fix round 4, W18) the inputs manifest the gate ran on: the bundle's
    rec=lambda **kw:{'route':'b','profile':'dd+mp256','approval':'user ok','exact_pilot':{'numerics':'exact','inputs_manifest_sha256':'6'*64},
                     'gates':[{'sha256':sha,'profile_executable_sha256':'e'*64,**ev}],'cost_model':dict(cm),**kw}
    meta=lambda r='default',**kw:{'numerics':'dd+mp256','pilot':{'numerics':'exact'},'inputs_manifest_sha256':'6'*64,'profile_recost':rec(**kw)if r=='default'else r}
    assert p.route_b({'numerics':'exact','pilot':{'numerics':'exact'},'profile_recost':None})is None  # the exact path
    assert p.route_b({'numerics':'dd+mp256','pilot':{'numerics':'dd+mp256'},'profile_recost':None})is None  # route (a): the pilot's own numerics
    assert p.route_b(meta())is None  # complete, not final
    n=0
    for m,needle in ((meta(route='a'),'(route)'),(meta(profile='dd'),'(profile)'),(meta(exact_pilot={'numerics':'dd+mp256'}),'(exact pilot)'),
                     (dict(meta(),pilot={'numerics':'dd+mp256'}),'(exact pilot)'),(meta(approval='  '),'(approval)'),(meta(approval=None),'(approval)'),
                     (meta(gates=[]),'(gates)'),(meta(gates=[{'sha256':'x','profile_executable_sha256':'e'*64}]),'(gates)'),
                     (meta(gates=[{'sha256':sha}]),'(gates)'),(meta(gates=['not a dict']),'(gates)'),
                     (meta(cost_model={'numerics':'exact','sha256':'c'*64}),'(cost model)'),(meta(cost_model={'numerics':'dd+mp256'}),'(cost model)'),
                     (meta(route='a',approval=''),'(route, approval)'),
                     ({'numerics':'dd+mp256','pilot':{'numerics':'exact'},'profile_recost':None},'without a route-(b) record'),
                     (meta(r=['a list']),'without a route-(b) record'),
                     (dict(meta(profile='mp256'),numerics='mp256'),'not in the user-approved set')):
        try:p.route_b(m);raise AssertionError(f'accepted {m}')
        except ValueError as e:assert needle in str(e),(needle,str(e));n+=1
    cmd={'numerics':'dd+mp256','executable_sha256':'e'*64,'cpu_models':['x']}
    for kw,needle in ((dict(cost_model=None),'needs --cost-model'),(dict(cost_model=dict(cmd,numerics='exact')),'cost model numerics identity'),
                      (dict(exe_sha='f'*64),'not a dd+mp256 build that a J-FLAG gate of the bundle passed')):
        a=dict(cost_model=cmd,cost_bytes=b'{}',exe_sha='e'*64,test_only=False,approval='ok',final=True);a.update(kw)
        try:p.route_b(meta(),**a);raise AssertionError(f'accepted {kw}')
        except ValueError as e:assert needle in str(e),(needle,str(e));n+=1
    nr=p.route_b(meta(),cmd,b'{}','f'*64,True,'ok',final=True);assert nr['route']=='b'and nr['executable_gated']is False  # test-only: recorded
    nr=p.route_b(meta(),cmd,b'{}','e'*64,False,'ok',final=True);assert nr['executable_gated']is True and nr['plan_approval']=='ok'and nr['gates'][0]['sha256']==sha
    # Stage-6 residual (fix-round-1 verifier): a gate entry without the X1-X3 evidence the current check_gate returns
    # (a bundle frozen before the fix, with a gate record check_gate now refuses) cannot plan, final or not
    g0=lambda **kw:[{'sha256':sha,'profile_executable_sha256':'e'*64,'slurm_job':'570210',**{k:v for k,v in ev.items()if k not in kw},**{k:v for k,v in kw.items()if v is not None}}]
    low=lambda s_,q,m_:dict(ev['F1_coverage'],**{s_:{'binary128_accepted':q,'mp_promoted':m_}})
    for gs,needle in ((g0(F1_coverage=None),'no F1_coverage'),(g0(F1_coverage={'free':ev['F1_coverage']['free']}),'F1_coverage'),
                      (g0(F1_coverage=low('power',50625,999)),'F1_coverage'),(g0(F1_coverage=low('free',9999,3541)),'F1_coverage'),
                      (g0(F1_coverage=low('free',True,3541)),'F1_coverage'),(g0(source_snapshot_sha256=None),'no source_snapshot_sha256'),
                      (g0(source_snapshot_sha256='5'*63),'no source_snapshot_sha256'),(g0(F5_team_sizes_verified=None),'F5_team_sizes_verified None'),
                      (g0(F5_team_sizes_verified=1),'F5_team_sizes_verified 1'),
                      (g0(gmp_library=None),'no gmp_library'),(g0(gmp_library={'exact':'1'*64,'f1_baseline_reused':False}),'gmp_library'),
                      (g0(gmp_library={'exact':'1'*64,'profile':'1'*64}),'gmp_library'),
                      (g0(inputs_manifest_sha256=None),'(no inputs_manifest_sha256)'),(g0(inputs_manifest_sha256='6'*63),'(no inputs_manifest_sha256)'),  # W18
                      ([{'sha256':sha,'profile_executable_sha256':'e'*64,'slurm_job':'570210'}],
                       'no F1_coverage; no source_snapshot_sha256; F5_team_sizes_verified None; no gmp_library; no inputs_manifest_sha256')):
        for kw in ({},dict(cost_model=cmd,cost_bytes=b'{}',exe_sha='e'*64,test_only=False,approval='ok',final=True),
                   dict(cost_model=cmd,cost_bytes=b'{}',exe_sha='e'*64,test_only=True,approval='ok',final=True)):
            try:p.route_b(meta(gates=gs),**kw);raise AssertionError(f'route_b accepted the gate entry {gs}')
            except ValueError as e:assert needle in str(e)and 'lack the evidence design.check_gate requires'in str(e)and '570210'in str(e),(needle,str(e));n+=1
    # W18 (fix round 4, integration): a complete gate entry of ANOTHER inputs manifest than the bundle's (or a bundle whose
    # exact pilot names another one) cannot plan, final or not, test-only or not
    for m,tag in ((meta(gates=g0(inputs_manifest_sha256='7'*64)),'570210 (777777777777...)'),
                  (meta(exact_pilot={'numerics':'exact','inputs_manifest_sha256':'7'*64}),'(666666666666...)')):
        for kw in ({},dict(cost_model=cmd,cost_bytes=b'{}',exe_sha='e'*64,test_only=False,approval='ok',final=True),
                   dict(cost_model=cmd,cost_bytes=b'{}',exe_sha='e'*64,test_only=True,approval='ok',final=True)):
            try:p.route_b(m,**kw);raise AssertionError(f'route_b accepted a gate of other inputs {tag}')
            except ValueError as e:assert tag in str(e)and 'ran on another inputs manifest than the bundle'in str(e),str(e);n+=1
    # the real bundles: pre6b (job 570302, frozen with the 570210 gate before the fix; test_only forced false) is refused;
    # the re-frozen bundles of job 570379 (gate 570373) are refused since fix round 3 for the libgmp provenance only
    # (Z19 downstream: the 570373 record predates Y1's tool_gmp_library), non-final and final as a non-test plan
    bench=ROOT/'benchmarks/symmetry_2026-10-c8';real=0
    for f in sorted((bench/'pre6b/p6bdes.570302.0').glob('design_meta_b_*.json')):
        m=dict(json.loads(f.read_text()),test_only=False)
        for kw in ({},dict(cost_model={'numerics':'dd+mp256'},cost_bytes=b'{}',exe_sha=m['profile_recost']['gates'][0]['profile_executable_sha256'],final=True)):
            try:p.route_b(m,**kw);raise AssertionError(f'route_b accepted the pre-fix bundle {f.name}')
            except ValueError as e:
                assert '570210 (no F1_coverage; no source_snapshot_sha256; F5_team_sizes_verified None; no gmp_library; no inputs_manifest_sha256)'in str(e),str(e);n+=1;real+=1
    fixed=sorted((bench/'s6fix1/s1des.570379.0').glob('design_meta_b_*.json'));assert len(fixed)==4,fixed
    for f in fixed:
        m=dict(json.loads(f.read_text()),test_only=False);gx=m['profile_recost']['gates'];assert [g['slurm_job']for g in gx]==['570373'],gx
        for kw in ({},dict(cost_model={'numerics':'dd+mp256'},cost_bytes=b'{}',exe_sha=gx[0]['profile_executable_sha256'],final=True)):
            try:p.route_b(m,**kw);raise AssertionError(f'route_b accepted the fix-round-1 bundle {f.name}')
            except ValueError as e:assert '570373 (no gmp_library; no inputs_manifest_sha256)'in str(e),str(e);n+=1;real+=1
        # with the libgmp provenance and the input set added (what a gate entry of the current check_gate carries) the same bundle plans
        m['profile_recost']['gates']=[dict(g,gmp_library={'exact':'1'*64,'profile':'1'*64,'f1_baseline_reused':False},
                                           inputs_manifest_sha256=m['inputs_manifest_sha256'])for g in gx]
        assert p.route_b(m)is None
        nr=p.route_b(m,{'numerics':'dd+mp256'},b'{}',gx[0]['profile_executable_sha256'],False,'ok',final=True)
        assert nr['route']=='b'and nr['executable_gated']is True;real+=1
    assert real==20,real
    # W24 (Stage-6 fix round 4, the host's residual): the re-frozen bundles of job 570539 (fix round 3: gate 570536 of the
    # dd+mp256 build a46f3060, libgmp 4dc20a90). The evidence copies are the frozen bytes (bundles.sha256). Since W18 (fix
    # round 4) they are REFUSED, non-final and final as a non-test plan, for the missing input set only (570536 predates
    # the gate's inputs block, as 570373 predated Z19). With the bundle's own inputs manifest added to the gate entry
    # (what the current check_gate returns) each plans with the gate's executable, records the gates 570539's test-only
    # plan recorded (route_b_<target>.json), and binds the executable to the gate's libgmp (W8), which the symmetry
    # nodes' runtime identity (J-VAL-1, job 570376) loads; another executable, another libgmp and another inputs
    # manifest are refused
    rb=bench/'s6fix3/s3des.570539.0';fz={}
    for line in (rb/'bundles.sha256').read_text().splitlines():
        h_,path_=line.split(None,1)
        if path_.endswith('/design_meta.json'):fz[path_.split('/')[-2]]=h_
    metas=sorted(rb.glob('design_meta_b_*.json'));assert len(metas)==4 and len(fz)==4,(metas,fz)
    ident=json.loads((bench/'s6fix1/s1x8a.570376.0/runtime_identity.json').read_text())['identity'];acc=0
    for f in metas:
        tag=f.name[len('design_meta_'):-len('.json')];assert digest(f)==fz[tag],(f.name,'not the frozen bytes')
        m=dict(json.loads(f.read_text()),test_only=False);gx=m['profile_recost']['gates']
        assert [g['slurm_job']for g in gx]==['570536']and gx[0]['profile_executable_sha256'].startswith('a46f3060')
        assert p.gate_evidence_missing(gx[0])==['no inputs_manifest_sha256'],gx  # W18: the missing input set only
        for kw in ({},dict(cost_model={'numerics':'dd+mp256'},cost_bytes=b'{}',exe_sha=gx[0]['profile_executable_sha256'],final=True)):
            try:p.route_b(m,**kw);raise AssertionError(f'route_b accepted the fix-round-3 bundle {f.name}')
            except ValueError as e:assert '570536 (no inputs_manifest_sha256)'in str(e),str(e);n+=1
        gx=m['profile_recost']['gates']=[dict(g,inputs_manifest_sha256=m['inputs_manifest_sha256'])for g in gx];assert p.gate_evidence_missing(gx[0])==[]
        assert p.route_b(m)is None
        nr=p.route_b(m,{'numerics':'dd+mp256'},b'{}',gx[0]['profile_executable_sha256'],False,'ok',final=True)
        assert nr['route']=='b'and nr['executable_gated']is True
        recd=json.loads((rb/f'route_{tag}.json').read_text())['numerics_route']
        assert [g['sha256']for g in nr['gates']]==[g['sha256']for g in recd['gates']]==[gx[0]['sha256']]and recd['executable_gated']is True,(tag,recd['gates'])
        gb=p.gate_gmp_binding({'numerics_route':nr,'executable_sha256':gx[0]['profile_executable_sha256']})
        assert gb=={gx[0]['gmp_library']['profile']}and next(iter(gb)).startswith('4dc20a90'),gb
        assert p.gate_gmp_binding({'numerics_route':recd,'executable_sha256':recd['executable_sha256']})==gb
        assert p.gmp_binding_problem(ident,gb,False)is None,'the symmetry nodes load the libgmp gate 570536 validated'
        other=dict(ident,libraries=dict(ident['libraries'],**{'libgmp.so.10':'f'*64}));assert 'not the libgmp'in p.gmp_binding_problem(other,gb,False)
        try:p.route_b(m,{'numerics':'dd+mp256'},b'{}','f'*64,False,'ok',final=True);raise AssertionError(f'accepted another executable for {f.name}')
        except ValueError as e:assert 'not a dd+mp256 build that a J-FLAG gate of the bundle passed'in str(e),str(e);n+=1
        m2=dict(m,profile_recost=dict(m['profile_recost'],gates=[dict(g,inputs_manifest_sha256='7'*64)for g in gx]))
        try:p.route_b(m2);raise AssertionError(f'accepted a gate of other inputs for {f.name}')
        except ValueError as e:assert 'ran on another inputs manifest than the bundle'in str(e),str(e);n+=1
        acc+=1
    assert acc==4
    # the bundles re-frozen in fix round 4 (job 570579, gate 570574: the W18 re-run on the same build a46f3060) are the
    # ACCEPTED ones: the frozen bytes (bundles.sha256); each plans, non-final and final as a NON-test plan, with the gate's
    # executable; the gate entry carries the package's inputs manifest and the libgmp 4dc20a90 the symmetry nodes load;
    # design.json is byte-identical to 570539's (only the gate entry changed); another executable or input set is refused
    rb4=bench/'s6fix4/s4des.570579.0';fz4={}
    for line in (rb4/'bundles.sha256').read_text().splitlines():
        h_,path_=line.split(None,1)
        if path_.endswith('/design_meta.json'):fz4[path_.split('/')[-2]]=h_
    metas=sorted(rb4.glob('design_meta_b_*.json'));assert len(metas)==4 and len(fz4)==4,(metas,fz4);pim=digest(ROOT/'inputs/manifest.json');acc4=0
    for f in metas:
        tag=f.name[len('design_meta_'):-len('.json')];assert digest(f)==fz4[tag],(f.name,'not the frozen bytes')
        assert (rb4/f'design_{tag}.json').read_bytes()==(rb/f'design_{tag}.json').read_bytes(),(tag,'design.json differs from 570539')
        m=dict(json.loads(f.read_text()),test_only=False);gx=m['profile_recost']['gates']
        assert [g['slurm_job']for g in gx]==['570574']and gx[0]['profile_executable_sha256'].startswith('a46f3060')and p.gate_evidence_missing(gx[0])==[],gx
        assert gx[0]['inputs_manifest_sha256']==m['inputs_manifest_sha256']==pim and gx[0]['sha256'].startswith('42e6d2d8'),gx[0]
        assert p.route_b(m)is None
        nr=p.route_b(m,{'numerics':'dd+mp256'},b'{}',gx[0]['profile_executable_sha256'],False,'ok',final=True);assert nr['route']=='b'and nr['executable_gated']is True
        recd=json.loads((rb4/f'route_{tag}.json').read_text())['numerics_route']
        assert [g['sha256']for g in recd['gates']]==[gx[0]['sha256']]and recd['executable_gated']is True and recd['gate_gmp_library']==[gx[0]['gmp_library']['profile']],recd
        gb=p.gate_gmp_binding({'numerics_route':nr,'executable_sha256':gx[0]['profile_executable_sha256']})
        assert gb=={gx[0]['gmp_library']['profile']}and next(iter(gb)).startswith('4dc20a90')and p.gmp_binding_problem(ident,gb,False)is None,gb
        try:p.route_b(m,{'numerics':'dd+mp256'},b'{}','f'*64,False,'ok',final=True);raise AssertionError(f'accepted another executable for {f.name}')
        except ValueError as e:assert 'not a dd+mp256 build that a J-FLAG gate of the bundle passed'in str(e),str(e);n+=1
        m2=dict(m,inputs_manifest_sha256='7'*64)
        try:p.route_b(m2);raise AssertionError(f'accepted the bundle {f.name} relabelled to other inputs')
        except ValueError as e:assert 'ran on another inputs manifest than the bundle'in str(e),str(e);n+=1
        acc4+=1
    assert acc4==4
    # design.check_gate: every branch
    gd=E.td/'gates';gd.mkdir(exist_ok=True)
    def gate(name,fn=None,raw=None):
        f=gd/name;x=gate_doc(inv)
        if fn:fn(x)
        f.write_text(raw if raw is not None else json.dumps(x));return f
    g=D.check_gate(gate('ok.json'),'dd+mp256',inv);assert g['profile_executable_sha256']=='e'*64 and g['sha256']==digest(gd/'ok.json')
    assert g['gmp_library']=={'exact':'1'*64,'profile':'1'*64,'f1_baseline_reused':False},g
    reused=lambda x:x['f1_baseline'].update(reused=True,reused_gmp_library={'match':True,'want_sha256':'1'*64,'exact_now':{'sha256':'1'*64}})
    assert D.check_gate(gate('ok_reused.json',reused),'dd+mp256',inv)['gmp_library']['f1_baseline_reused']is True  # a checked reuse is accepted
    cases=[('json',None,'{not json','is not JSON'),('schema',lambda x:x.update(schema='other'),"schema 'other'"),('mode',lambda x:x.update(mode='exact'),"(mode 'exact')"),
           ('profile',lambda x:x.update(profile_name='dd'),"a gate of profile 'dd'"),('status',lambda x:x.update(status='failed'),"status 'failed'"),
           ('development',lambda x:x.update(development=['C8_DD_DEVELOPMENT']),'development options'),
           ('F1',lambda x:x['verdicts'].update(F1=False),'F1 not passed'),('F2',lambda x:x['verdicts'].pop('F2'),'F2 not passed'),
           ('F5',lambda x:x['verdicts'].update(F5=None),'F5 not passed'),('total',lambda x:x['F2']['total'].update(passed=False),'F2 total gate'),
           ('resolved',lambda x:x['F2']['total'].update(resolved=False),'F2 total gate'),('describe',lambda x:x['profile']['describe'].update(numerics='dd'),"describes numerics 'dd'"),
           ('build_dev',lambda x:x['profile']['build_record'].update(development=True),'development build'),
           ('override',lambda x:x['profile']['build_record'].update(parameter_overrides=['-DC8_MP256_RATIO=1e-30']),'development build'),
           ('no_sha',lambda x:x['profile'].pop('sha256'),'no profile executable sha256'),('bad_sha',lambda x:x['profile'].update(sha256='E'*64),'no profile executable sha256'),
           ('small',lambda x:x['F2']['graphs'].update(a_free_L3=0),'not a full-scale gate'),('list',None,'[]',"schema None"),
           ('no_coverage',lambda x:x['F1'].pop('coverage'),'no F1 coverage record'),('one_sector',lambda x:x['F1']['coverage']['sectors'].pop('power'),'not free and power'),
           ('quota',lambda x:x['F1']['coverage']['sectors']['free'].update(mp_promoted=999,need_met=False),'not the need'),
           ('unbound',lambda x:x.pop('build_binding'),'no build binding'),('team',lambda x:x['F5'].update(team_sizes_verified=False),'OpenMP team sizes'),
           # Z19 downstream (fix round 3): the libgmp provenance of both F1 tools
           ('no_exact_lib',lambda x:x['exact'].pop('build_record'),"the exact executable's build record names no libgmp"),
           ('no_profile_lib',lambda x:x['profile']['build_record'].pop('gmp_library'),"the profile executable's build record names no libgmp"),
           ('profile_tool_lib',lambda x:x['F1'].pop('tool_gmp_library'),"the profile's F1 tool is not shown"),
           ('profile_tool_other',lambda x:x['F1']['tool_gmp_library']['tool'].update(sha256='9'*64),"the profile's F1 tool is not shown"),
           ('profile_worker_now',lambda x:x['F1']['tool_gmp_library']['worker_now'].update(sha256='9'*64),"the profile's F1 tool is not shown"),
           ('profile_no_match',lambda x:x['F1']['tool_gmp_library'].update(match=False),"the profile's F1 tool is not shown"),
           ('baseline_lib',lambda x:x['f1_baseline'].pop('tool_gmp_library'),"the F1 baseline's exact tool is not shown"),
           ('baseline_lib_other',lambda x:x['exact']['build_record']['gmp_library'].update(sha256='9'*64),"the F1 baseline's exact tool is not shown"),
           ('reused_unknown',lambda x:x['f1_baseline'].pop('reused'),'f1_baseline does not say whether'),
           ('reused_unchecked',lambda x:x['f1_baseline'].update(reused=True),"the reused F1 baseline's libgmp is not checked"),
           ('reused_other',lambda x:x['f1_baseline'].update(reused=True,reused_gmp_library={'match':True,'want_sha256':'1'*64,'exact_now':{'sha256':'9'*64}}),
            "the reused F1 baseline's libgmp is not checked")]
    for case in cases:
        name,fn,raw,needle=case if len(case)==4 else (case[0],case[1],None,case[2])
        try:D.check_gate(gate(f'{name}.json',fn,raw),'dd+mp256',inv);raise AssertionError(f'check_gate accepted {name}')
        except ValueError as e:assert needle in str(e)and (name=='json'or 'not a passed full-scale J-FLAG gate'in str(e)),(name,str(e));n+=1
    # production.gated_route (route (a) and profile pilots): a gate twice, an executable no gate covers; accepted otherwise
    ok_=gd/'ok.json'
    for paths,exe_sha,needle in (([ok_,ok_],'e'*64,'names one record twice'),([ok_],'f'*64,'is not the dd+mp256 build that the --numerics-gate record(s) passed')):
        try:p.gated_route('dd+mp256','design',paths,exe_sha,inv,'ok');raise AssertionError(f'gated_route accepted {needle}')
        except ValueError as e:assert needle in str(e),(needle,str(e));n+=1
    r=p.gated_route('dd+mp256','design',[ok_],'e'*64,inv,'ok');assert r['route']=='a'and r['executable_gated']is True and r['pilot_approval']is None
    # W18 (fix round 4, integration): gated_route checks the gate against the PLAN's inputs manifest (im_sha), not only the
    # package's: a gate of the package's inputs is refused for a plan of other inputs (a fixture), accepted for its own
    pim=digest(ROOT/'inputs/manifest.json');assert p.gated_route('dd+mp256','pilot',[ok_],'e'*64,inv,'ok',None,pim)['gates'][0]['inputs_manifest_sha256']==pim
    try:p.gated_route('dd+mp256','pilot',[ok_],'e'*64,inv,'ok',None,'7'*64);raise AssertionError('gated_route accepted a gate of other inputs')
    except ValueError as e:assert f'the gate ran on inputs manifest {pim[:12]}..., not 777777777777...'in str(e),str(e);n+=1
    r=p.gated_route('dd+mp256','pilot',[ok_],'e'*64,inv,'ok',('dd+mp256','default'));assert r['route']=='pilot'and r['pilot_approval']is None  # not in the (empty) set
    ok('Stage6_route_b_record_check_gate_gated_route_refusal_branches',refusals=n)

def test_allocation(E):
    """A-ORC-2 (D8): exactly one allocation source; --pilot gives every graph P points per replicate; P < 4096 only in
    test-only plans; stratified selection with the L7 and L8 primitives, deterministic."""
    p=E.M.prod;fs=E.td/'fs.json';fs.write_text('[]')
    d=E.td/'nosource';r=E.plan(d,'--test-graphs',2,'--bootstrap-chunk',4,'--shards',1,expect=1);assert 'exactly one allocation source'in r.stderr and gone(d)
    bun=E.td/'nobundle';d=E.td/'both';r=E.plan(d,'--pilot','--design',bun,'--test-graphs',2,'--bootstrap-chunk',4,'--shards',1,expect=1);assert 'exactly one allocation source'in r.stderr and gone(d)
    d=E.td/'p2048';r=E.plan(d,'--pilot','--points',2048,'--replicates',2,'--shards',1,'--forbid-seeds-from',fs,expect=1);assert 'needs a test-only plan'in r.stderr and gone(d),r.stderr[-300:]
    d=E.td/'p2048t';E.plan(d,'--pilot','--points',2048,'--replicates',2,'--test-graphs',1,'--bootstrap-chunk',512,'--shards',1)
    m=manifest(d);assert m['allocation']=={'source':'pilot','points':2048,'replicates':2,'label':None}and m['test_only']
    for g in m['groups']:
        c=config(d,g['name']);assert c['counts']and all(v==2048 for v in c['counts'].values())and c['replicates']==2,g['name']
    d=E.td/'p_npow2';r=E.plan(d,'--pilot','--points',3000,'--replicates',2,'--test-graphs',1,'--bootstrap-chunk',512,'--shards',1,expect=1);assert 'power of two'in r.stderr and gone(d)
    # stratified selection on the full inventory: N/2 cheapest + N/2 heaviest + all 44 L7 primitives + >= 16 L8 primitives
    inv=json.loads((ROOT/'inputs/inventory.json').read_text())
    for L in (7,8):
        rows=[{**r,'_L':L}for r in inv['free'][str(L)]];cost=lambda r:float(r['cost'])
        a1=p.select_graphs(rows,32,'stratified',cost);a2=p.select_graphs(list(reversed(rows)),32,'stratified',cost)
        prim=sorted(r['id']for r in rows if r['primitive']);by=sorted(rows,key=lambda r:(cost(r),r['id']))
        assert a1==a2 and {r['id']for r in by[:16]}|{r['id']for r in by[-16:]}<=a1
        if L==7:assert len(prim)==44 and set(prim)<=a1
        else:
            pr=sorted((r for r in rows if r['primitive']),key=lambda r:(cost(r),r['id']));assert len(prim)==248 and {r['id']for r in pr[:8]}|{r['id']for r in pr[-8:]}<=a1
            assert len(set(prim)&a1)>=16
    # plan-level stratified (fixture): every free L7 group carries the 44 primitives
    d=E.td/'strat';E.plan(d,'--pilot','--points',8,'--replicates',2,'--test-graphs',4,'--test-selection','stratified','--bootstrap-chunk',4,'--shards',1)
    fx=json.loads((E.fixture/'inventory.json').read_text());prim7={str(r['id'])for r in fx['free']['7']if r['primitive']}
    assert prim7<=set(config(d,'a_free_L7')['counts'])and prim7<=set(config(d,'b_free_L7')['counts'])and manifest(d)['test_selection']=='stratified'
    d=E.td/'strat_nontest';r=E.plan(d,'--pilot','--replicates',2,'--test-selection','stratified','--shards',1,'--forbid-seeds-from',fs,expect=1);assert 'needs --test-graphs'in r.stderr
    ok('allocation_sources_pilot_points_stratified')



# ================================================================ chunking, sizing, atomicity (A-ORC-3)
def test_chunking_sizing(E):
    """A-ORC-3 with a synthetic cost model: power-of-two chunks in [min-chunk, n_g], tasks <= --max-task-seconds (else a
    refusal naming the graph), shards from --index-hours, est_core_seconds equal to an independent cost-model x counts
    recomputation, est_peak_bytes equal to the hand value of a two-block shard, per-campaign costs (campaign b at 3x),
    the caps (--max-tasks, --max-checkpoints, the Expanse file cap) and an atomic plan surviving SIGKILL."""
    p=E.M.prod;fx=json.loads((E.fixture/'inventory.json').read_text())
    ca=lambda c,s,L,r:2e-4*(1+r['id']%3)*(3 if c=='b'else 1)
    cm=E.td/'cm_b3.json';cm.write_text(json.dumps(cost_model_for(E,None,ca)))
    d=E.td/'chunk';args=('--pilot','--points',8192,'--replicates',2,'--test-graphs',3,'--cost-model',cm,'--task-seconds',1,'--min-chunk',256,'--index-hours',0.005,'--checkpoint-tasks',16)
    out=json.loads(E.plan(d,*args).stdout);m=manifest(d);T=16
    est_by_group={};H=0.005;thr=2
    for g in m['groups']:
        c=config(d,g['name']);n=c['counts']
        for gid,cnt in n.items():
            cg=cm_c=json.loads(cm.read_text())['seconds_per_point'][f'{c["campaign"]}:{c["sector"]}:{c["L"]}:{gid}']
            want=max(256,1<<int(math.floor(math.log2(1/cg))));want=min(want,cnt)
            assert c['chunks'][gid]==want and want&(want-1)==0 and 256<=want<=cnt or want==cnt,(g['name'],gid,c['chunks'][gid],want)
            assert want*cg<=120
        secs=sum(cnt*json.loads(cm.read_text())['seconds_per_point'][f'{c["campaign"]}:{c["sector"]}:{c["L"]}:{gid}']for gid,cnt in n.items())*c['replicates']
        est_by_group[g['name']]=secs;jobs=[j for j in m['jobs']if j['group']==g['name']]
        assert math.isclose(sum(j['est_core_seconds']for j in jobs),secs,rel_tol=1e-9),g['name']        # HR19: recomputed, not the planner's column
        assert math.isclose(m['estimates']['groups'][g['name']]['core_hours']*3600,secs,rel_tol=1e-9)
        assert c['shards']==len(jobs)==min(c['tasks'],max(1,math.ceil(secs/(H*3600*thr*0.9)))),(g['name'],c['shards'],secs)
        con=roq(d/'groups'/g['name']/'tasks.sqlite');rows=con.execute('SELECT hi-lo,gi FROM tasks').fetchall();con.close()
        assert all(h==int(c['chunks'][str(gi)])for h,gi in rows)
    # per-campaign costs (R05): campaign b's chunks are campaign a's / 2 or / 4 (3x cost), its estimates 3x
    for s_ in ('free','power'):
        for L in range(3,9):
            ga,gb=config(d,f'a_{s_}_L{L}'),config(d,f'b_{s_}_L{L}')
            for gid in ga['chunks']:assert ga['chunks'][gid]>=gb['chunks'][gid]and ga['chunks'][gid]//gb['chunks'][gid]in(1,2,4),(s_,L,gid)
            assert math.isclose(est_by_group[f'b_{s_}_L{L}'],3*est_by_group[f'a_{s_}_L{L}'],rel_tol=1e-9)
    # the lane deadline need per index uses the index's own (campaign-keyed) estimate and the class factor
    j=max(m['jobs'],key=lambda j:j['est_core_seconds']);need=lambda j,f:j['est_core_seconds']*f/(8*0.9)*1.5+300
    model=json.loads(cm.read_text());assert E.M.lanes.class_factor(model,'Synthetic CPU','a','free',8)==1.0 and E.M.lanes.class_factor(model,'Unknown CPU','a','free',8)==1.5
    jb=next(x for x in m['jobs']if x['group']==j['group'].replace('a_','b_',1)and x['shard']==0)if j['group'].startswith('a_')else None
    # est_peak_bytes of a two-block shard: max over its blocks of the distinct graphs' kernel bytes + threads x 4 MB + 0.5 GB,
    # and (W9, Stage-6 fix round 4) the rows of one block (min(T, tasks) x 16 KiB) and the plan metadata every claim parses
    # (2 KiB per job entry and per inventory row)
    two=[x for x in m['jobs']if x['blocks']==2]
    assert two,'need a two-block shard'
    x=two[0];rows=[tuple(map(int,l.split()))for l in (d/x['tasks_file']).read_text().splitlines()];kb={r['id']:r['kernel_bytes']for r in fx[x['sector']][str(x['L'])]}
    meta=len(m['jobs'])*2048+sum(len(v)for s_ in fx.values()for v in s_.values())*2048
    hand=max(sum(kb[g]for g in {r[2]for r in rows[b:b+T]})for b in (0,T))+thr*4*2**20+2**29+min(T,len(rows))*16*1024+meta
    assert x['est_peak_bytes']==hand,(x['est_peak_bytes'],hand)
    assert out['estimated_core_hours']==float(f'{m["estimates"]["total_core_hours"]:.4g}')and 'projected_files'in out and 'manifest_bytes'in out and 'merge_passes'in out
    # a task above --max-task-seconds refuses, naming the graph
    heavy=dict(json.loads(cm.read_text()));g8=int(next(iter(config(d,'a_free_L8')['counts'])));heavy['seconds_per_point']=dict(heavy['seconds_per_point'],**{f'a:free:8:{g8}':1.0})
    hc=E.td/'cm_heavy.json';hc.write_text(json.dumps(heavy));d2=E.td/'chunk_heavy';r=E.plan(d2,*[a if a!=cm else hc for a in args],expect=1)
    assert f'graph {g8}'in r.stderr and '--max-task-seconds'in r.stderr and gone(d2),r.stderr[-300:]
    # caps refuse before anything is created, and (O03) every cap the task counts alone decide refuses before the LPT
    # allocates any task-sized array: _lpt is a trap there
    lpt_trap=mock.patch.object(p,'_lpt',side_effect=AssertionError('the LPT ran before the task-count caps'))
    for extra,needle in ((('--max-tasks',10),'--max-tasks'),(('--max-checkpoints',3),'--max-checkpoints')):
        d2=E.td/f'cap_{extra[0][2:]}'
        with lpt_trap:r=E.plan(d2,*args,*extra,expect=1)
        assert needle in r.stderr and 'LPT ran'not in r.stderr and gone(d2),r.stderr[-300:]
    with mock.patch.object(p,'EXPANSE_FILE_CAP',50),mock.patch.dict(os.environ,{'C8_SITE':'expanse'}),lpt_trap:
        d2=E.td/'cap_files';r=E.plan(d2,*args,expect=1);assert 'Lustre file quota'in r.stderr and 'LPT ran'not in r.stderr and gone(d2),r.stderr[-300:]
    with mock.patch.object(p,'PLAN_TASKS_IN_JOB',10):
        with lpt_trap:d2=E.td/'cap_login';r=E.plan(d2,*args,expect=1)
        assert 'plan inside a job'in r.stderr and 'LPT ran'not in r.stderr and gone(d2),r.stderr[-300:]
        with mock.patch.dict(os.environ,{'SLURM_JOB_ID':'4242'}):E.plan(E.td/'cap_injob',*args)
    # the exact block count after the LPT still refuses when only the real per-index counts exceed the cap: one block per
    # group (lower bound) but more after the split into shards
    mm=manifest(d);lo=sum(-(-config(d,g['name'])['tasks']//T)for g in mm['groups']if config(d,g['name'])['tasks']);ex=sum(j['blocks']for j in mm['jobs'])
    assert ex>lo,(ex,lo)
    d2=E.td/'cap_exact';r=E.plan(d2,*args,'--max-checkpoints',lo,expect=1);assert f'{ex:,} checkpoint blocks > --max-checkpoints'in r.stderr and gone(d2),r.stderr[-300:]
    # a pooled cost key, another backend and another rates identity
    for name,doc,needle in (('pooled',{**model,'seconds_per_point':{'free:3:1':1e-3}},'pooled'),('backend',{**model,'backend':'decimal'},'differs from --backend')):
        f=E.td/f'cm_{name}.json';f.write_text(json.dumps(doc));d2=E.td/f'chunk_{name}';r=E.plan(d2,*[a if a!=cm else f for a in args],expect=1);assert needle in r.stderr and gone(d2),(name,r.stderr[-300:])
    f=E.td/'cm_rates.json';f.write_text(json.dumps({**model,'rates_identity':'f'*64}));fs=E.td/'fs.json';fs.write_text('[]')
    d2=E.td/'chunk_rates_test';r=E.plan(d2,*[a if a!=cm else f for a in args]);assert 'rates identity'in r.stderr  # test-only: warning, accepted
    with mock.patch.dict(os.environ,{'C8_INPUTS':''}):
        with mock.patch.object(p,'inputs_rel_from_env',return_value='inputs'):
            pass
    r=cli(p,'plan',E.td/'chunk_rates_prod','--seed',SEED,'--pilot','--replicates',2,'--cost-model',f,'--forbid-seeds-from',fs,expect=1)
    assert ('rates identity'in r.stderr or 'test fixture'in r.stderr or "inputs/ only"in r.stderr),r.stderr[-300:]
    ok('chunking_sizing_estimates_per_campaign_caps',groups=len(m['groups']),jobs=len(m['jobs']))

def test_atomic_plan(E):
    """A plan killed (SIGKILL) inside its write phase leaves no target directory, and a rerun of the same plan succeeds
    (A-ORC-3, HR26). Stage-6 Y15 (S6E-R2-03): the kill must land in the write phase. The child runs in its own session
    and is inspected only while frozen (SIGSTOP, then waitpid(WUNTRACED) until it has stopped; SIGCONT and 20 ms
    between looks), so no look races the publication: SIGKILL is sent only to a live, stopped child whose staging
    directory holds a group while the target does not exist. The child must die by SIGKILL and leave its staging
    directory unpublished. An exit before the write phase is seen, a target that exists while the plan runs, or no
    write phase within 120 s fails at once; the child (and its session) is killed and reaped on every failure path. The
    rerun uses the same arguments and must publish the whole campaign."""
    d=E.td/'atomic';log=E.td/'atomic_plan.log';env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    argv=[PY,'-B',str(E.pkg/'tools/production.py'),'plan',str(d),'--seed',str(SEED),'--pilot','--points','64','--replicates','2','--test-graphs','all',
          '--bootstrap-chunk','8','--shards','2','--threads','2','--checkpoint-tasks','8']
    def staged():return sorted(d.parent.glob(d.name+'.tmp.*'))
    def tail():return log.read_text(errors='replace')[-1500:]if log.exists()else''
    def reap(flags):
        """waitpid on the child; an exit is recorded in proc.returncode (so Popen never waits for it again)."""
        _,st=os.waitpid(proc.pid,flags)
        if not os.WIFSTOPPED(st):proc.returncode=os.waitstatus_to_exitcode(st)
        return st
    def signal_child(sig):
        """The child's session (the child and any helper it started); once only the exited, unreaped child is left,
        macOS refuses killpg (EPERM), so then the child itself (never signalled after it is reaped)."""
        try:os.killpg(proc.pid,sig)
        except(ProcessLookupError,PermissionError):
            with contextlib.suppress(ProcessLookupError):os.kill(proc.pid,sig)
    assert not d.exists()and not staged(),'leftover target or staging before the plan starts'
    with open(log,'wb')as out:proc=subprocess.Popen(argv,stdout=out,stderr=subprocess.STDOUT,env=env,start_new_session=True)
    try:
        t0=time.monotonic();looks=0
        while True:
            signal_child(signal.SIGSTOP);st=reap(os.WUNTRACED);looks+=1
            assert os.WIFSTOPPED(st),f'the plan exited ({proc.returncode}) before its write phase was observed:\n{tail()}'
            assert not d.exists(),f'the target exists while the plan runs (not one rename at the end):\n{tail()}'
            stage=staged()
            if len(stage)==1 and (stage[0]/'groups').is_dir()and any((stage[0]/'groups').iterdir()):break  # frozen in the write phase
            assert time.monotonic()-t0<120,f'no write phase within 120 s ({looks} looks):\n{tail()}'
            signal_child(signal.SIGCONT);time.sleep(0.02)
        groups_at_kill=len(list((stage[0]/'groups').iterdir()))
        signal_child(signal.SIGKILL);st=reap(0)
        assert os.WIFSIGNALED(st)and os.WTERMSIG(st)==signal.SIGKILL,f'the plan did not die by SIGKILL (wait status {st})'
    finally:
        if proc.returncode is None:  # a failure path: kill the stopped or running child and its session, and reap it
            signal_child(signal.SIGKILL)
            with contextlib.suppress(ChildProcessError):reap(0)
    assert not d.exists(),'target exists after SIGKILL'
    assert staged()==stage,('the killed plan must leave its staging directory',staged(),stage)
    # the rerun: the same planning arguments, the whole campaign published
    cp=subprocess.run(argv,capture_output=True,text=True,env=env)
    assert cp.returncode==0,f'the rerun of the same plan failed ({cp.returncode}):\n{cp.stderr[-2000:]}'
    m=manifest(d);assert m['test_only']and m['test_graphs']=='all'and m['jobs'],(m.get('test_only'),m.get('test_graphs'))
    assert {g['name']for g in m['groups']}=={p.name for p in (d/'groups').iterdir()},'published groups differ from the manifest'
    ok('atomic_plan_sigkill_in_write_phase_then_same_plan_rerun_Y15',looks=looks,groups_at_kill=groups_at_kill,groups_published=len(m['groups']),
       left_staging=len(staged()))

def synth_fixture(E,name='inputs_synth')->Path:
    """A copy of inputs_mini whose first free L8 graph has M = 4,032 and T = 280 (the heaviest L8 shape), manifest updated."""
    dst=E.pkg/'tests/fixtures'/name
    if dst.exists():return dst
    shutil.copytree(E.fixture,dst,copy_function=lambda a,b:link_or_copy(Path(a),Path(b)))
    inv=json.loads((dst/'inventory.json').read_text());r=inv['free']['8'][0];r.update(monomials=4032,terms=280,cost=4032*280)
    replace_bytes(dst/'inventory.json',json.dumps(inv,separators=(',',':')).encode()+b'\n')
    m=json.loads((dst/'manifest.json').read_text());m['sha256']['inventory.json']=digest(dst/'inventory.json');replace_bytes(dst/'manifest.json',(json.dumps(m,indent=1)+'\n').encode())
    return dst

def test_bootstrap(E):
    """A-ORC-3, the first-sweep bootstrap (R13) and its regeneration (R18)."""
    p=E.M.prod;syn=synth_fixture(E);heavy_id=json.loads((syn/'inventory.json').read_text())['free']['8'][0]['id']
    boot=json.loads((E.pkg/'tools/bootstrap_proxy.json').read_text());hand=512*4032*280*boot['rows']['gmp']['free']['8']
    assert math.isclose(hand,512*4032*280*3*6.859350117917584e-09,rel_tol=1e-12)and 11.8<hand<12.0
    with mock.patch.dict(os.environ,{'C8_INPUTS':str(syn)}):
        # the C7(2) calibration has no campaign-keyed row: the plan without --bootstrap-chunk refuses, naming the group
        d=E.td/'sweep_nobasis';r=E.plan(d,'--pilot','--points',512,'--replicates',2,'--test-graphs','all','--shards',8,expect=1)
        assert 'no cost basis'in r.stderr and 'a_free_L3'in r.stderr and '--bootstrap-chunk'in r.stderr and gone(d),r.stderr[-300:]
        cm=E.td/'cm_any.json';cm.write_text(json.dumps(cost_model_for(E,None)))
        for extra,needle in ((('--cost-model',cm),'exclude each other'),(('--index-hours',1),'refuses --index-hours'),(('--task-seconds',30),'refuses --index-hours, --task-seconds')):
            d=E.td/f'sweep_bad_{extra[0][2:]}';r=E.plan(d,'--pilot','--points',512,'--replicates',2,'--test-graphs','all','--bootstrap-chunk',512,'--shards',8,*extra,expect=1)
            assert needle in r.stderr and gone(d),(extra,r.stderr[-300:])
        fs=E.td/'fs.json';fs.write_text('[]');d=E.td/'sweep_nontest'
        r=E.plan(d,'--pilot','--replicates',2,'--bootstrap-chunk',512,'--shards',8,'--forbid-seeds-from',fs,expect=1);assert 'test-only plan only'in r.stderr and gone(d)
        d=E.td/'sweep_toolong';r=E.plan(d,'--pilot','--points',8192,'--replicates',2,'--test-graphs','all','--bootstrap-chunk',8192,'--shards',8,expect=1)
        assert f'graph {heavy_id}'in r.stderr and 'preliminary seconds'in r.stderr and gone(d),r.stderr[-300:]
        # the J-SWEEP-1 plan step of tools/sweep.py
        d=E.td/'sweep1';r=tool(E.pkg,'sweep.py',d,'--seed',SEED+7,'--points',512,'--replicates',2,'--threads',2,'--bootstrap-chunk',512,'--shards',8,'--plan-only',env={'C8_INPUTS':str(syn)})
        m=manifest(d);assert m['test_only']and m['test_graphs']=='all'and m['cost_basis']=='bootstrap'and m['estimates']['estimate']=='unavailable (bootstrap)'
        assert all(j['est_core_seconds']is None for j in m['jobs'])and all(c==512 for g in m['groups']for c in config(d,g['name'])['chunks'].values())
        c8=config(d,'a_free_L8');assert math.isclose(c8['preliminary_max_task_seconds'],hand,rel_tol=1e-12)
        assert all(config(d,g['name'])['preliminary_max_task_seconds']<=120 for g in m['groups'])
        assert m['estimates']['predicted_max_task_seconds']['a_free_L8']['label'].startswith('preliminary_proxy')
        con=roq(d/'groups/a_free_L8/tasks.sqlite');assert {x[0]for x in con.execute('SELECT hi-lo FROM tasks')}=={512};con.close()
        assert 'unavailable (bootstrap)'in r.stdout or 'sweep: not inside a Slurm job'in r.stdout
        # lane mode refuses it
        cp=tool(E.pkg,'lanes.py','queue',d,check=False);assert cp.returncode==64 and 'per-index time estimates'in cp.stderr
    # calibrate.py --bootstrap: byte for byte from the pinned copy; a one-byte change to the copy refuses, naming it
    out=E.td/'boot_regen.json';tool(E.pkg,'calibrate.py','--bootstrap','--output',out);assert out.read_bytes()==(E.pkg/'tools/bootstrap_proxy.json').read_bytes()
    pin=E.pkg/'reference/c7d2_hpc_a55958f/tools/calibration.json';orig=pin.read_bytes()
    try:
        replace_bytes(pin,orig.replace(b'"gmp"',b'"gmq"',1));cp=tool(E.pkg,'calibrate.py','--bootstrap','--output',E.td/'boot_bad.json',check=False)
        assert cp.returncode and 'reference/c7d2_hpc_a55958f/tools/calibration.json'in (cp.stderr+cp.stdout)and not (E.td/'boot_bad.json').exists()
    finally:replace_bytes(pin,orig)
    # a small bootstrap sweep run end to end by the fake integrator: first measured cost model and campaign-keyed rows
    d=E.td/'sweep_small';tool(E.pkg,'sweep.py',d,'--seed',SEED+8,'--points',16,'--replicates',2,'--threads',2,'--bootstrap-chunk',8,'--shards',2,'--plan-only')
    # (the --test-graphs all fixture plan is small enough to run in full here)
    E.run_all(d);cli(E.M.prod,'merge',d,'--jobs',2)
    calcopy=E.td/'calibration_copy.json';shutil.copy2(E.pkg/'tools/calibration.json',calcopy)
    sp_env={'C8_INPUTS':str(E.fixture)}
    cmo=E.td/'cm_measured.json'
    cps=[spied([PY,'-B',str(E.pkg/'tools/make_cost_model.py'),str(d),str(cmo)],sp_env,E.td,'mcm'),
         spied([PY,'-B',str(E.pkg/'tools/calibrate.py'),str(d),'--update',str(calcopy)],sp_env,E.td,'cal'),
         spied([PY,'-B',str(E.pkg/'tools/design.py'),'report','--pilot',str(d),'--test-only'],sp_env,E.td,'des')]
    bp=os.path.realpath(E.pkg/'tools/bootstrap_proxy.json')
    for cp,recs in cps:
        assert cp.returncode==0,cp.stderr[-800:]
        assert recs and not any(o[0]==bp for r in recs for o in r['opens']),'tools/bootstrap_proxy.json opened'
    cmd=json.loads(cmo.read_text());assert len(cmd['seconds_per_point'])==sum(len(config(d,g['name'])['counts'])for g in manifest(d)['groups'])
    assert {k.split(':')[0]for k in cmd['seconds_per_point']}=={'a','b'}and cmd['rates_identity']=='default'
    cal=json.loads(calcopy.read_text());assert cal['schema']=='c8-d2-calibration-1'and p.calibration_row(cal,'gmp','a','free',8)and p.calibration_row(cal,'gmp','b','power',8)
    assert p.calibration_row(json.loads((E.pkg/'tools/calibration.json').read_text()),'gmp','a','free',8)is None  # the active C7(2) file has no campaign row
    # a test-only lane-mode plan with the first measured cost model: accepted, chunks from 60/c_g, estimates available
    d2=E.td/'after_sweep';E.plan(d2,'--pilot','--points',4096,'--replicates',2,'--test-graphs',2,'--cost-model',cmo,'--index-hours',0.01)
    m2=manifest(d2);assert m2['cost_basis']=='measured'and all(j['est_core_seconds']is not None for j in m2['jobs'])
    for g in m2['groups']:
        c=config(d2,g['name'])
        for gid,ch in c['chunks'].items():
            cg=cmd['seconds_per_point'][f'{c["campaign"]}:{c["sector"]}:{c["L"]}:{gid}'];want=min(max(256,1<<int(math.floor(math.log2(60/cg)))),c['counts'][gid]);assert ch==want
    tool(E.pkg,'lanes.py','queue',d2)
    ok('first_sweep_bootstrap_R13',heavy_preliminary_seconds=hand,measured_keys=len(cmd['seconds_per_point']))
    test_bootstrap_export(E)

def export_copy(E,dest:Path)->str:
    """A scratch copy of a git archive export of HEAD (no .git); on a cluster export (no .git) a copy of the package.
    Uncommitted changes to tools/ or tests/ make it a copy of the working tree, which has no .git either."""
    dest.mkdir()
    if (ROOT/'.git').exists()and shutil.which('git'):
        dirty=subprocess.run(['git','-C',str(ROOT),'status','--porcelain','tools','tests','inputs','reference'],capture_output=True,text=True).stdout.strip()
        if not dirty:
            arch=subprocess.run(['git','-C',str(ROOT),'archive','--format=tar','HEAD'],capture_output=True,check=True).stdout
            subprocess.run(['tar','-x','-C',str(dest)],input=arch,check=True);src='git archive HEAD'
        else:src='working-tree copy without .git (uncommitted changes)'
    else:src='copy of the cluster export (no .git)'
    if src!='git archive HEAD':
        def ign(d,names):
            out={n for n in names if n in('.git','bin','__pycache__','build')or n.endswith('.pyc')}
            if Path(d).resolve()==(ROOT/'inputs/packs').resolve():out|={n for n in names if n in('free_L8.pack','power_L8.pack')}  # multi-GB, not in git
            return out
        shutil.copytree(ROOT,dest,dirs_exist_ok=True,ignore=ign)
    (dest/'bin').mkdir(exist_ok=True)
    for b in ('c8d2_decimal','c8d2_gmp'):
        f=dest/'bin'/b;f.write_text(FAKE_SHEBANG+(ROOT/'tests/fake_worker.py').read_text());f.chmod(0o755)
    return src

def test_bootstrap_export(E):
    """R18: in a scratch copy of an export (no .git), calibrate.py --update changes the active calibration; --bootstrap
    then regenerates tools/bootstrap_proxy.json byte for byte, opening neither the active calibration nor .git and
    starting no git process."""
    x=E.td/'export';src=export_copy(E,x);env={'C8_INPUTS':str(x/'tests/fixtures/inputs_mini')}
    committed=(x/'tools/bootstrap_proxy.json').read_bytes();before=digest(x/'tools/calibration.json')
    d=E.td/'export_run'
    def xt(*a,**k):return subprocess.run([PY,'-B',str(x/'tools'/a[0]),*map(str,a[1:])],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',**env},**k)
    for args in (('production.py','plan',d,'--seed',SEED+11,'--pilot','--points',8,'--replicates',2,'--test-graphs',1,'--bootstrap-chunk',4,'--shards',1,'--threads',2,'--checkpoint-tasks',8),):
        cp=xt(*args);assert cp.returncode==0,cp.stderr[-800:]
    for j in manifest(d)['jobs']:cp=xt('production.py','run',d,'--index',j['id'],'--threads',2);assert cp.returncode==0,cp.stderr[-500:]
    cp=xt('production.py','merge',d);assert cp.returncode==0,cp.stderr[-500:]
    cp=xt('calibrate.py',d,'--update',x/'tools/calibration.json');assert cp.returncode==0,cp.stderr[-500:]
    assert digest(x/'tools/calibration.json')!=before!=None  # the update changed the active calibration (C7(2)'s a6696eb3... before the first sweep)
    before_is_c7=before==hashlib.sha256((ROOT/'reference/c7d2_hpc_a55958f/tools/calibration.json').read_bytes()).hexdigest()
    (x/'tools/bootstrap_proxy.json').unlink()
    cp,recs=spied([PY,'-B',str(x/'tools/calibrate.py'),'--bootstrap'],env,E.td,'boot_export')
    assert cp.returncode==0,cp.stderr[-500:]
    assert (x/'tools/bootstrap_proxy.json').read_bytes()==committed
    active=os.path.realpath(x/'tools/calibration.json')
    opened=[o[0]for r in recs for o in r['opens']];launched=[pp for r in recs for pp in r['popen']]
    assert active not in opened and not any('/.git/'in o or o.endswith('/.git')for o in opened),[o for o in opened if 'calibration'in o or '.git'in o]
    assert not any((pp[0]or'').endswith('git')or(pp[1]and Path(pp[1][0]).name=='git')for pp in launched),launched
    ok('bootstrap_regenerated_from_export_after_update_R18',export=src,active_calibration_was_c7=before_is_c7)


# ================================================================ execution, status, recovery, merge (A-ORC-6, A-ORC-7)
def test_pipeline(E):
    p=E.M.prod;d=E.td/'camp';E.small(d,'--checkpoint-tasks',4,'--shards',1);m=manifest(d);scratch=E.td/'scratch_spy';scratch.mkdir();log=E.td/'fake.log'
    # job-private runtime: every native call uses private copies of the executable, gamma, net and graphs
    with mock.patch.dict(os.environ,{'C8_FAKE_LOG':str(log)}):cli(p,'run',d,'--index',0,'--threads',2,'--scratch',scratch)
    calls=[json.loads(x)for x in log.read_text().splitlines()];rt=str(scratch/'c8d2_runtime_')
    assert calls and all(c['executable'].startswith(rt)and c['sha256']==m['executable_sha256']and all(c['args'][i].startswith(rt)for i in(0,1,2,3))for c in calls)
    assert not any(scratch.iterdir())
    g0=m['jobs'][0]['group'];cp0=json.loads(next((d/'groups'/g0/'checkpoints').glob('*.json')).read_text())
    assert {k:cp0['runtime'][k]for k in('executable_sha256','inputs_manifest_sha256','net_sha256','rates_identity')}=={'executable_sha256':m['executable_sha256'],
        'inputs_manifest_sha256':m['inputs_manifest_sha256'],'net_sha256':config(d,g0)['net']['sha256'],'rates_identity':'default'}
    assert cp0['runtime']['fingerprint']['host']and list(cp0)[0]=='runtime'and isinstance(cp0['runtime']['fingerprint_bytes'],int)and cp0['native']['order']==8
    assert cp0['index_tasks_sha256']==m['jobs'][0]['tasks_sha256']
    j=m['jobs'][-1];gp=d/'groups'/j['group'];before=set(gp.glob('checkpoints/*.json'))
    r=tool(E.pkg,'production.py','run',d,'--index',j['id'],'--scratch',scratch,env={'C8_FAKE_FAIL':'1'},check=False)
    assert r.returncode and 'forced native failure'in r.stderr and not any(scratch.iterdir())and set(gp.glob('checkpoints/*.json'))==before and list(gp.glob('logs/*.failure.*.log'))
    r=E.run(d,0,'--threads',128,expect=1);assert 'exceed checkpoint_tasks'in r.stderr
    r=tool(E.pkg,'production.py','run',d,check=False);assert r.returncode and 'give --index'in r.stderr
    E.run_all(d)
    tool(E.pkg,'production.py','run',d,env={'SLURM_ARRAY_TASK_ID':'0','C8_INDEX_OFFSET':str(len(m['jobs'])-1)})
    st=cli(p,'status',d);assert 'complete: every checkpoint block is committed'in st.stdout
    T=m['checkpoint_tasks']
    for g in m['groups']:
        con=roq(d/'groups'/g['name']/'tasks.sqlite');rows=con.execute('SELECT uid,shard,pos FROM tasks').fetchall();con.close()
        for f in (d/'groups'/g['name']/'checkpoints').glob('*.json'):
            sh,k=int(f.stem[1:7]),int(f.stem[9:]);want=[u for u,s_,q in sorted(rows,key=lambda x:x[2])if s_==sh and k*T<=q<(k+1)*T]
            assert [r['uid']for r in json.loads(f.read_text())['native']['rows']]==want,f
    js=json.loads(cli(p,'status',d,'--json').stdout);host=cp0['runtime']['fingerprint']['host']
    fps=js['groups'][g0]['fingerprints'];assert len(fps)==1 and next(iter(fps.values()))['hosts']==[host]
    ok('run_private_runtime_failure_threads_offset_fingerprints',native_calls=len(calls))
    # status, recovery lines, --max-blocks and recompute of deleted checkpoints (the C7(2) recovery contract)
    g=max(m['groups'],key=lambda x:config(d,x['name'])['tasks'])['name'];cps=sorted((d/'groups'/g/'checkpoints').glob('s000000_p*.json'))
    assert len(cps)>=2,f'group {g} needs >= 2 blocks in shard 0'
    saved={q:q.read_bytes()for q in cps[:2]}
    for q in saved:q.unlink()
    jid=next(x['id']for x in m['jobs']if x['group']==g and x['shard']==0);st=cli(p,'status',d,expect=1)
    want=f'resubmit: C8_MAX_ARRAY=1000 C8_RUN={d.resolve()} C8_PACKAGE={E.pkg.resolve()} {E.pkg.resolve()/"slurm/submit.sh"} --window {jid//1000*1000}:{jid%1000}'
    assert want in st.stdout,st.stdout[-800:]
    js=json.loads(cli(p,'status',d,'--json',expect=1).stdout)
    assert js['complete']is False and js['missing_jobs']==[jid]and js['resubmit']==[{'offset':0,'array':str(jid)}]
    assert js['campaign_tag']=='c8:'+hashlib.sha256(f'{d.resolve()}\n{digest(d/"manifest.json")}'.encode()).hexdigest()[:12]
    js=json.loads(cli(p,'status',d,'--json','--exclude',f'{jid},99999',expect=1).stdout);assert js['active_not_resubmitted']==[jid]and js['resubmit']==[]
    E.run(d,jid,'--max-blocks',1);assert cps[0].exists()and not cps[1].exists()
    E.run(d,jid,'--threads',1);assert cli(p,'status',d).returncode==0
    for q,data in saved.items():
        x,y=json.loads(q.read_text()),json.loads(data)
        assert [{k:r[k]for k in p.SCIENTIFIC}for r in x['native']['rows']]==[{k:r[k]for k in p.SCIENTIFIC}for r in y['native']['rows']]
    ok('status_recovery_lines_max_blocks_recompute')
    victim=cps[0];data=victim.read_bytes();victim.unlink();real=p.run_native
    def racing(cmd,log):
        real(cmd,log)
        if not victim.exists():victim.write_bytes(data)
    with mock.patch.object(p,'run_native',side_effect=racing):out=E.run(d,jid).stdout
    assert f'verified duplicate {g}/{victim.stem}'in out and f'committed {g}/{victim.stem}'not in out,out
    for q in cps[:2]:q.unlink()
    with concurrent.futures.ThreadPoolExecutor(2)as ex:rcs=list(ex.map(lambda _:tool(E.pkg,'production.py','run',d,'--index',jid,check=False).returncode,range(2)))
    assert rcs==[0,0],rcs
    ok('duplicate_runs_verified_duplicate')
    # merge (parallel) equals the serial reference byte for byte; resume; idempotent assembly; test-only keys; permissions
    ser=E.td/'camp_serial';shutil.copytree(d,ser)
    with mock.patch.dict(os.environ,{}):cli(p,'merge',ser,'--serial')
    cli(p,'merge',d,'--group','a_free_L3');cli(p,'merge',d,'--jobs',4)
    for g_ in m['groups']:
        for f in ('merged.json','graph_replicates.csv','graph_tails.csv','graph_costs.csv'):
            assert (d/'groups'/g_['name']/f).read_bytes()==(ser/'groups'/g_['name']/f).read_bytes(),(g_['name'],f)
    cli(E.M.asm,d,'--bootstrap',16);snap=tree(d);cli(p,'merge',d);r=cli(E.M.asm,d,'--bootstrap',16)
    assert 'identical result already present'in r.stdout and tree(d)==snap and not (d/'C8_result.json').exists()
    res=json.loads((d/'C8_test_result.json').read_text());phys=[k for k in res['test_partial']]
    assert res['test_only']and all(res[k]is None for k in phys)and {'C8_full','coefficients','power_free_C8','power_correction','campaigns','half_streams','lower_order_checks'}<=set(phys)
    for f in (d/'manifest.json',d/'C8_test_result.json',d/'groups/a_free_L3/merged.json',d/'groups/a_free_L3/graph_replicates.csv',victim):
        assert stat.S_IMODE(f.stat().st_mode)==0o644,(f,oct(f.stat().st_mode))
    ok('merge_jobs_equals_serial_resume_idempotent_assembly_permissions',physical_keys_nulled=len(phys))
    # altered runtime digests and foreign checkpoints are rejected by run and merge
    def rejected(path:Path,edit,args,needle,mod=None):
        orig=path.read_bytes();path.write_bytes(edit(orig))
        try:r=cli(mod or p,*args,expect=1);assert needle in r.stderr,(path,needle,r.stderr[-500:])
        finally:path.write_bytes(orig)
    def rt_edit(key,val):
        def f(b):x=json.loads(b);x['runtime'][key]=val;return json.dumps(x).encode()
        return f
    (d/'groups'/g/'merged.json').unlink()
    rejected(victim,rt_edit('executable_sha256','0'*64),('run',d,'--index',jid,'--scratch',E.scratch),'different executable')
    rejected(victim,rt_edit('executable_sha256','0'*64),('merge',d,'--group',g),'different executable')
    rejected(victim,rt_edit('net_sha256','1'*64),('merge',d,'--group',g),'different Sobol net')
    rejected(victim,rt_edit('inputs_manifest_sha256','2'*64),('run',d,'--index',jid,'--scratch',E.scratch),'different inputs')
    rejected(victim,rt_edit('rates_identity','3'*64),('merge',d,'--group',g),'another rates identity')
    def tail_edit(b):x=json.loads(b);x['native']['rows'][0]['tail_top']=x['native']['rows'][0]['tail_top'][::-1];x['payload_sha256']=E.M.common.object_hash(x['native']);return json.dumps(x).encode()
    rejected(victim,tail_edit,('merge',d,'--group',g),'tail fields')
    def bump(b):x=json.loads(b);x['batches'][0][0]+=1.0;return (json.dumps(x,indent=2)+'\n').encode()
    rejected(d/'groups/b_power_L4/merged.json',bump,('merge',d),'merged payload checksum mismatch')
    cli(p,'merge',d,'--group',g)
    rejected(d/'C8_test_result.json',lambda b:json.dumps({**json.loads(b),'x':1}).encode(),(d,'--bootstrap',16),'differs from the recomputed result',E.M.asm)
    cli(p,'merge',d,'--group',g);assert tree(d)==snap
    other=E.td/'other';E.small(other,'--checkpoint-tasks',4,'--shards',1,seed=SEED+1);E.run(other,0)
    foreign=next((other/'groups'/manifest(other)['jobs'][0]['group']/'checkpoints').glob('*.json'))
    target=d/'groups'/manifest(other)['jobs'][0]['group']/'checkpoints'/foreign.name
    rejected(target,lambda b:foreign.read_bytes(),('run',d,'--index',0,'--scratch',E.scratch),'checkpoint identity mismatch')
    ok('runtime_digest_rates_tail_tamper_and_foreign_checkpoint_rejected')
    # merge and assemble without bin/; a changed pinned tool (run refuses; merge/assemble only with --accept-tool-change)
    (E.pkg/'bin').rename(E.pkg/'bin_away')
    try:
        (d/'groups/a_power_L5/merged.json').unlink();cli(p,'merge',d);cli(E.M.asm,d,'--bootstrap',16,'--output',E.td/'nobin.json')
        assert json.loads((E.td/'nobin.json').read_text())['test_only']
        r=cli(p,'run',d,'--index',0,'--scratch',E.scratch,expect=1);assert 'No such file'in r.stderr or 'FileNotFoundError'in r.stderr
    finally:(E.pkg/'bin_away').rename(E.pkg/'bin')
    ap=E.pkg/'tools/assemble.py';orig=ap.read_bytes();planned=digest(ap)
    try:
        ap.write_bytes(orig+b'\n# local change\n');now=digest(ap)
        r=cli(p,'run',d,'--index',0,'--scratch',E.scratch,expect=1);assert 'tools/assemble.py'in r.stderr
        (d/'groups/b_free_L3/merged.json').unlink()
        r=cli(p,'merge',d,expect=1);assert '--accept-tool-change'in r.stderr
        cli(p,'merge',d,'--accept-tool-change');mg=json.loads((d/'groups/b_free_L3/merged.json').read_text())
        assert mg['accepted_tool_changes']=={'assemble.py':{'planned':planned,'current':now}}
    finally:ap.write_bytes(orig)
    ok('merge_assemble_without_bin_and_tool_change_provenance')
    return d

def wait_for(pred,timeout=60):
    t0=time.time()
    while time.time()-t0<timeout:
        if pred():return True
        time.sleep(0.05)
    return False

def alive(pid):
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True

def fake_running(flog:Path,pid:int,timeout:float=60.)->bool:
    """The fake native worker `pid` has started (its C8_FAKE_LOG line is written after its script is read)."""
    def seen():
        try:return any(json.loads(l).get('pid')==pid for l in Path(flog).read_text().splitlines()if l.strip())
        except (OSError,ValueError):return False
    return wait_for(seen,timeout)

def launch_boundary_case(E,d,j,scr,seen=None):
    """The in-process launch-boundary case of test_signal_cleanup: production.run in this process, SIGTERM from the test
    seam right after the native child is launched and registered (stop signals deferred); the run must stop that
    child, remove its runtime and exit 143, with the SIGTERM handler restored. W15 (Stage-6 fix round 4, S6E-R4-02):
    the hook registers the child's Popen in an independent cleanup scope (Owned, also marked by the scratch path)
    before it injects the signal, so that whatever fails (production's cleanup, an assertion, the run) the evidence is
    taken first and then the 120 s fake worker is killed and reaped on the way out; before, the hook kept only the
    pid, nothing outside production held the child (a later run resets _NATIVE['children']), and a failed case left
    it running. The hook also waits (signals still deferred) until the fake worker runs (its C8_FAKE_LOG line, written
    once its script is read): production must stop a running worker, never one that dies by itself because the
    runtime holding its script is removed. seen (a dict) receives the scope and the children, for
    test_launch_boundary_cleanup's control."""
    pids=[];prev=signal.getsignal(signal.SIGTERM);flog=E.td/f'{scr.name}.fake.log'
    with Owned(markers=(str(scr),))as own:
        if seen is not None:seen.update(own=own,children=pids)
        def hook(child):
            own.add(child);pids.append(child)
            assert fake_running(flog,child.pid),('the fake native worker never started',child.pid)
            os.kill(os.getpid(),signal.SIGTERM)
        with mock.patch.dict(os.environ,{'C8_FAKE_SLEEP':'120','C8_FAKE_LOG':str(flog)}),mock.patch.object(E.M.prod,'_after_launch',side_effect=hook):
            r=cli(E.M.prod,'run',d,'--index',j['id'],'--threads',2,'--scratch',scr,expect=None)
        assert r.returncode==143 and 'stopped by signal 15'in r.stderr and pids and not alive(pids[0].pid),(r.returncode,r.stderr[-500:])
        assert pids[0].returncode is not None and not any(scr.iterdir())and signal.getsignal(signal.SIGTERM)==prev,(pids[0].returncode,list(scr.iterdir()))
    assert not own.killed,own.killed

TERM_IGNORED=r'''import os,signal,sys
signal.signal(signal.SIGTERM,signal.SIG_IGN)  # a TERM that arrives now is lost, as one between fork and exec can be
open(os.environ['C8_TEST_READY'],'w').close();os.execv(sys.executable,[sys.executable]+sys.argv[1:])
'''

def test_signal_cleanup(E):
    """C7(2) R2/IR2-02, ported: SIGTERM during a running native task, to production.py run and to slurm/run_array.sh
    (C8_STAGE=1, member staging); the launch boundary in Python (test seam) and in the shell (before `child=$!`), and
    (checkpoint review, test robustness) a TERM lost at the shell's launch boundary: the job ignores the first TERM, as
    one reaching the job between its fork and its exec can be lost (seen with bash 3.2 under load; the leaked
    c8d2_runtime_* of the flaky stage-0 case), and run_array.sh must stop it by repeating TERM, not by the KILL after
    30 s that leaves its runtime behind. The waits are generous (a loaded node), the assertions unchanged: exit
    143, the launched job gone, no KILL, the scratch empty."""
    d=E.td/'sig';E.small(d,'--shards',1);m=manifest(d);j=m['jobs'][0];g=d/'groups'/j['group']
    for mode in ('python','run_array.sh'):
        scr=E.td/f'sig_scratch_{mode}';scr.mkdir();log=E.td/f'sig_{mode}.log';before={f.name for f in g.glob('checkpoints/*.json')}
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','C8_FAKE_SLEEP':'120','C8_FAKE_LOG':str(log)}
        if mode=='python':cmd=[PY,'-B',str(E.pkg/'tools/production.py'),'run',str(d),'--index',str(j['id']),'--threads','2','--scratch',str(scr)]
        else:
            cmd=['bash',str(E.pkg/'slurm/run_array.sh')]
            env.update(SLURM_ARRAY_TASK_ID='0',C8_INDEX_OFFSET=str(j['id']),C8_PACKAGE=str(E.pkg),C8_RUN=str(d),C8_PYTHON=PY,C8_STAGE='1',SLURM_TMPDIR=str(scr),SLURM_CPUS_PER_TASK='2')
        with Owned(markers=(str(scr),))as own:  # Z13: the run and its native child are cleaned up whatever fails
            proc=own.add(subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,start_new_session=True))
            assert wait_for(lambda:log.exists()and log.read_text().strip(),180),(mode,'native task never started')
            child=json.loads(log.read_text().splitlines()[0])['pid'];assert alive(child)
            proc.send_signal(signal.SIGTERM);out,err=proc.communicate(timeout=180)
            assert proc.returncode==143,(mode,proc.returncode,err[-800:])
            assert wait_for(lambda:not alive(child),60),(mode,'native child still running')
            assert not any(scr.iterdir()),(mode,list(scr.iterdir()))
        assert not own.killed,(mode,own.killed)
        assert {f.name for f in g.glob('checkpoints/*.json')}==before and not list(g.glob('checkpoints/*.tmp.*'))
    scr=E.td/'sig_scratch_launch';scr.mkdir();launch_boundary_case(E,d,j,scr)
    src=(E.pkg/'slurm/run_array.sh').read_text();assert src.count('\nchild=$!\n')==1
    launch='\n"$PY" -B "$package/tools/production.py" run ';assert src.count(launch)==1
    hooked=E.pkg/'slurm/run_array_boundary.sh';hooked.write_text(src.replace('\nchild=$!\n','\necho $! > "$C8_TEST_PIDFILE"; kill -TERM $$; child=$!\n'))
    # the lost TERM: the job starts with TERM ignored (a wrapper that execs Python, which installs its own handler
    # later); the shell sends its TERM only once the job is in that state, so the first TERM is lost every time
    lost=E.pkg/'slurm/run_array_lost_term.sh';wrapper=E.td/'term_ignored.py';wrapper.write_text(TERM_IGNORED)
    lost.write_text(src.replace(launch,'\n"$PY" "$C8_TEST_WRAPPER" -B "$package/tools/production.py" run ').replace('\nchild=$!\n',
        '\necho $! > "$C8_TEST_PIDFILE"; for w in $(seq 1 2400); do [[ -e "$C8_TEST_READY" ]] && break; sleep 0.05; done; kill -TERM $$; child=$!\n'))
    for case,script,stage in (('boundary0',hooked,'0'),('boundary1',hooked,'1'),('lost_term0',lost,'0')):
        scr=E.td/f'sig_scratch_{case}';scr.mkdir();pidf=E.td/f'{case}.pid'
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','C8_FAKE_SLEEP':'120','SLURM_ARRAY_TASK_ID':'0','C8_INDEX_OFFSET':str(j['id']),'C8_PACKAGE':str(E.pkg),
             'C8_RUN':str(d),'C8_PYTHON':PY,'C8_STAGE':stage,'SLURM_TMPDIR':str(scr),'SLURM_CPUS_PER_TASK':'2','C8_TEST_PIDFILE':str(pidf),
             'C8_TEST_WRAPPER':str(wrapper),'C8_TEST_READY':str(E.td/f'{case}.ready')}
        # the script's output goes to a file (a pipe would also wait for any orphan holding it); bash and its children
        # run in their own session, so that a failure can be cleaned up and described. Generous waits: the script
        # itself bounds the stop at 30 s (then KILL), which the assertions below rule out.
        outf=E.td/f'{case}.out'
        # Z13: the evidence is taken inside the cleanup scope (a cleanup first would hide a launched job that survived);
        # leaving the scope kills and reaps whatever is left, on every exit path
        with outf.open('w')as fo,Owned(markers=(str(scr),))as own:
            sh=own.add(subprocess.Popen(['bash',str(script)],stdout=fo,stderr=subprocess.STDOUT,env=env,start_new_session=True))
            try:rc=sh.wait(timeout=180)
            except subprocess.TimeoutExpired:rc=None
            launched=int(pidf.read_text())if pidf.exists()else None
            ok_gone=launched is not None and wait_for(lambda:not alive(launched),30)
            empty=ok_gone and wait_for(lambda:not any(scr.iterdir()),30)
            output=outf.read_text();killed='still running after 30 s'in output
            if rc!=143 or not ok_gone or not empty or killed:
                ps=subprocess.run(['ps','-eo','pid,ppid,pgid,stat,etime,args'],capture_output=True,text=True).stdout
                mine=[l for l in ps.splitlines()if str(E.td)in l or (launched is not None and str(launched)in l.split()[:3])or str(sh.pid)in l.split()[:3]]
                raise AssertionError(dict(case=case,returncode=rc,launched=launched,launched_gone=ok_gone,scratch=[x.name for x in scr.iterdir()],
                                          killed_after_30s=killed,output=output[-3000:],processes=mine[:20]))
        assert not own.killed,(case,own.killed)
    hooked.unlink();lost.unlink();E.run(d,j['id'])
    ok('sigterm_cleanup_run_and_run_array',exit_status=143,shell_cases=['boundary0','boundary1','lost_term0'])

def test_uri_concurrent_merge(E):
    """A '#?% ' campaign path; two concurrent merges both succeed, the collision branch runs (an identical
    merged.json is kept), and a different concurrent merged.json is refused (HR17)."""
    d=E.td/'we#ird?dir %41 x';E.small(d,'--test-graphs',1);E.run_all(d)
    assert cli(E.M.prod,'status',d).returncode==0
    with concurrent.futures.ThreadPoolExecutor(2)as ex:cps=list(ex.map(lambda _:tool(E.pkg,'production.py','merge',d,'--jobs',2,check=False),range(2)))
    assert [c.returncode for c in cps]==[0,0],[c.stderr[-400:]for c in cps]
    snap=tree(d);cli(E.M.prod,'merge',d);assert tree(d)==snap
    # force the collision: a merge that publishes after another merge of the same group already did
    g='a_free_L3';p=d/'groups'/g;saved=(p/'merged.json').read_bytes();(p/'merged.json').unlink();real=E.M.prod.dump;hits=[]
    def racing(path,obj):
        if Path(path).name=='merged.json'and not Path(path).exists():Path(path).write_bytes(saved);hits.append(1)
        return real(path,obj)
    with mock.patch.object(E.M.prod,'dump',side_effect=racing):r=cli(E.M.prod,'merge',d,'--group',g)
    assert hits and 'identical merged.json published concurrently; kept'in r.stdout,r.stdout[-300:]
    (p/'merged.json').unlink();bad=json.loads(saved);bad['integration_seconds_sum']+=1;bad['payload_sha256']=E.M.common.object_hash({k:v for k,v in bad.items()if k!='payload_sha256'})
    def racing2(path,obj):
        if Path(path).name=='merged.json'and not Path(path).exists():Path(path).write_text(json.dumps(bad,indent=2)+'\n')
        return real(path,obj)
    with mock.patch.object(E.M.prod,'dump',side_effect=racing2):r=cli(E.M.prod,'merge',d,'--group',g,expect=1)
    assert 'different merged.json was published concurrently'in r.stderr,r.stderr[-300:]
    (p/'merged.json').write_bytes(saved)
    cli(E.M.asm,d,'--bootstrap',16);assert json.loads((d/'C8_test_result.json').read_text())['test_only']
    ok('uri_reserved_path_concurrent_merge_collision_and_refusal',path=d.name)

def test_zero_task(E):
    """Zero-task groups (C8_ALLOW_NO_L8 without L8 packs): no jobs, zero batches, test-only result."""
    pk=E.pkg/'inputs/packs';assert not (pk/'free_L8.pack').exists()
    with mock.patch.dict(os.environ,{'C8_INPUTS':'','C8_ALLOW_NO_L8':'1'}):
        os.environ.pop('C8_INPUTS')
        d=E.td/'zero';r=E.small(d,'--test-graphs',1);m=manifest(d)
        assert 'SKIPPED'in r.stderr and sorted(m['skipped_packs'])==['free_L8','power_L8']
        for name in ('a_free_L8','b_power_L8'):
            c=config(d,name);assert c['tasks']==0 and c['shards']==0 and not any(j['group']==name for j in m['jobs'])
        E.run_all(d);cli(E.M.prod,'merge',d);cli(E.M.asm,d,'--bootstrap',16)
        z=json.loads((d/'groups/a_free_L8/merged.json').read_text());assert z['batches']==[[0.,0.],[0.,0.]]and (d/'C8_test_result.json').exists()
    ok('zero_task_groups_without_l8_packs')

def test_fan_in(E):
    """A-ORC-6 bounded fan-in on a small campaign: --fan-in 2 forces several passes; RLIMIT_NOFILE leaving F < 2 refuses."""
    d=E.td/'fanin';E.small(d,'--shards',6,'--test-graphs',3,points=16);E.run_all(d)
    a=E.td/'fanin_a';b=E.td/'fanin_b';shutil.copytree(d,a);shutil.copytree(d,b)
    cli(E.M.prod,'merge',a,'--serial');r=cli(E.M.prod,'merge',b,'--fan-in',2,'--jobs',1)
    assert 'pass(es), fan-in 2'in r.stdout and re.search(r'\((\d+) pass',r.stdout)
    for g in manifest(d)['groups']:
        for f in ('merged.json','graph_replicates.csv','graph_tails.csv','graph_costs.csv'):assert (a/'groups'/g['name']/f).read_bytes()==(b/'groups'/g['name']/f).read_bytes()
    import resource
    hard=resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    cp=subprocess.run([PY,'-B',str(E.pkg/'tools/production.py'),'merge',str(d)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},
                      preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_NOFILE,(33,hard)))
    assert cp.returncode and 'fan-in'in cp.stderr and '< 2'in cp.stderr,cp.stderr[-300:]
    assert not (b/'merge_work').exists()  # the intermediate runs are removed after publication
    ok('bounded_fan_in_passes_identical_and_refusal')

def test_merge_resume(E):
    """PLAN D, phase 2 "resumable per output run": with --fan-in 2 over 6 shards every group needs intermediate passes.
    A merge killed in phase 2 (after k output runs, the next one torn mid-write) keeps the completed runs of the
    interrupted group in the persistent per-campaign work directory (<campaign>/merge_work; BASE/c8d2_merge_<manifest
    sha256 prefix> with --work-dir BASE), and has already removed those of the groups it published. The rerun skips
    the published groups, reuses every complete run (no second _merge_runs for it: total - k calls), rewrites the torn
    one, publishes tables byte-identical to the serial reference, and removes the work directory."""
    d=E.td/'resume';E.small(d,'--shards',6,'--test-graphs',3,points=16);E.run_all(d)
    ref=E.td/'resume_ref';shutil.copytree(d,ref);cli(E.M.prod,'merge',ref,'--serial')
    prod=E.M.prod;real=prod._merge_runs;calls=[]
    def counting(inputs,out):calls.append(Path(out).name);return real(inputs,out)
    cnt=E.td/'resume_count';shutil.copytree(d,cnt)
    with mock.patch.object(prod,'_merge_runs',side_effect=counting):cli(prod,'merge',cnt,'--fan-in',2,'--jobs',1)
    total=len(calls);assert total>=6 and not (cnt/'merge_work').exists(),total
    grp=lambda x:x.split('.')[0]
    k=next(i for i in range(total//2,total)if grp(calls[i])==grp(calls[i-1])==grp(calls[i-2]))  # interrupt inside a group, after two of its runs
    class Killed(BaseException):"""a kill of the merge process (not an Exception: nothing in merge catches it)"""
    mh=hashlib.sha256((d/'manifest.json').read_bytes()).hexdigest();out={}
    for label,extra,W in (('default',(),d/'merge_work'),('work_dir',('--work-dir',E.td/'mw_base'),E.td/'mw_base'/f'c8d2_merge_{mh[:16]}')):
        c=E.td/f'resume_{label}';shutil.copytree(d,c);W=Path(str(W).replace(str(d),str(c)))if label=='default'else W
        done=[]
        def killing(inputs,o):
            if len(done)==k:Path(o).write_text('0\t0\t0\t4\n');raise Killed()  # a torn output: no '#end' line
            res=real(inputs,o);done.append(Path(o).name);return res
        with mock.patch.object(prod,'_merge_runs',side_effect=killing):
            try:cli(prod,'merge',c,'--fan-in',2,'--jobs',1,*extra);raise AssertionError('not interrupted')
            except Killed:pass
        kept=sorted(W.glob('*.run'));complete={f.name for f in kept if prod._complete_run(f)};torn=[f.name for f in kept if not prod._complete_run(f)]
        merged=[g['name']for g in manifest(c)['groups']if (c/'groups'/g['name']/'merged.json').exists()]
        assert len(torn)==1 and complete and complete<=set(done)and len({x.split('.')[0]for x in complete|set(torn)})==1,(torn,complete,done)
        assert merged and not any(f.name.startswith(tuple(n+'.'for n in merged))for f in W.iterdir()),(merged,sorted(f.name for f in W.iterdir()))
        calls.clear()
        with mock.patch.object(prod,'_merge_runs',side_effect=counting):r=cli(prod,'merge',c,'--fan-in',2,'--jobs',1,*extra)
        assert not set(calls)&complete and torn[0]in calls and len(calls)==total-k,(len(calls),total,k,sorted(set(calls)&complete))
        assert f'{len(complete)} intermediate run(s) reused from {os.path.realpath(W)}'in r.stdout and sum(f'{n}: already merged and valid; skipped'in r.stdout for n in merged)==len(merged),r.stdout[-800:]
        for g in manifest(d)['groups']:
            for f in ('merged.json','graph_replicates.csv','graph_tails.csv','graph_costs.csv'):
                assert (c/'groups'/g['name']/f).read_bytes()==(ref/'groups'/g['name']/f).read_bytes(),(label,g['name'],f)
        assert not W.exists()and (label=='default'or W.parent.is_dir()),label
        out[label]=dict(total=total,interrupted_after=k,reused=len(complete),groups_published_before=len(merged),rerun_calls=len(calls))
    ok('merge_phase2_resumes_from_complete_runs_after_interrupt',**out)


def test_merge_cached_runs_verified(E):
    """Checkpoint review O01: a cached intermediate run of an interrupted merge is reused only when it holds exactly the
    merge of its inputs. After an interrupt that leaves complete runs in merge_work, each of these edits to one complete
    run (its name, coordinates and '#end' footer kept) is detected on the rerun, reported, and the run rebuilt, so the
    published tables equal the serial reference: a changed value digit, two rows swapped, a row removed, and a row
    added after the '#end' line. Untouched runs are still reused."""
    d=E.td/'cached';E.small(d,'--shards',6,'--test-graphs',3,points=16,seed=SEED+81);E.run_all(d)
    ref=E.td/'cached_ref';shutil.copytree(d,ref);cli(E.M.prod,'merge',ref,'--serial')
    prod=E.M.prod;real=prod._merge_runs;done=[]
    class Killed(BaseException):"""a kill of the merge process"""
    def killing(inputs,o):
        if len(done)==4:raise Killed()
        res=real(inputs,o);done.append(Path(o));return res
    base=E.td/'cached_cut';shutil.copytree(d,base)
    with mock.patch.object(prod,'_merge_runs',side_effect=killing):
        try:cli(prod,'merge',base,'--fan-in',2,'--jobs',1);raise AssertionError('not interrupted')
        except Killed:pass
    runs=sorted((base/'merge_work').glob('*.run'));assert len(runs)>=2 and all(prod._complete_run(f)for f in runs),runs
    def edit_digit(lines):
        f=lines[0].rstrip('\n').split('\t');v=f[-1].split(' ');x=v[0];i=max(j for j,ch in enumerate(x)if ch.isdigit())
        v[0]=x[:i]+str((int(x[i])+1)%10)+x[i+1:];f[-1]=' '.join(v);lines[0]='\t'.join(f)+'\n';return lines
    edits={'value digit':edit_digit,'rows swapped':lambda l:[l[1],l[0]]+l[2:],'row removed':lambda l:l[1:],'row after #end':None}
    out={}
    for name,f in edits.items():
        c=E.td/f'cached_{name.replace(" ","_").replace("#","")}';shutil.copytree(base,c);target=sorted((c/'merge_work').glob('*.run'))[0]
        body=target.read_text();lines=body.splitlines(keepends=True);assert lines[-1]=='#end\n'and len(lines)>=3
        new=body+lines[0]+'#end\n'if f is None else ''.join(f(lines[:-1]))+'#end\n'
        assert new!=body and prod._complete_run(target)
        target.write_text(new);assert prod._complete_run(target)  # still looks complete: only the verification can tell
        r=cli(prod,'merge',c,'--fan-in',2,'--jobs',1)
        assert f'{target.name}'in r.stderr and 'fails verification'in r.stderr and 'rebuilt'in r.stderr,(name,r.stderr[-600:])
        assert re.search(r'1 rebuilt after failing verification',r.stdout)and 'reused'in r.stdout,(name,r.stdout[-600:])
        for g in manifest(d)['groups']:
            for t in ('merged.json','graph_replicates.csv','graph_tails.csv','graph_costs.csv'):
                assert (c/'groups'/g['name']/t).read_bytes()==(ref/'groups'/g['name']/t).read_bytes(),(name,g['name'],t)
        out[name]='rebuilt'
    # the digest is keyed by a secret each merge draws afresh: the same run verifies under its own key only
    kd=E.td/'keyed';kd.mkdir();rows=[((0,g,0),f'0\t{g}\t0\t1\t1\t0\t0\t1e-06\t0.1\t0\t0.1\t0.1 0.2\n')for g in range(5)]
    k1,k2=prod.merge_key(),prod.merge_key();res=prod._write_run(rows,kd/'x.run',hashed=True,key=k1)
    assert k1!=k2 and len(k1)==32 and prod._verify_run(kd/'x.run',5,res['mset'],k1)is None and prod._verify_run(kd/'x.run',5,res['mset'],k2)is not None
    # O02 on a unit scale: shards of many blocks (2 tasks each) under fan-in 2, so phase 1 merges its spill runs in
    # several passes; the tables equal the serial reference, and no spill file outlives the merge
    m2=E.td/'spills';E.small(m2,'--shards',1,'--test-graphs',3,'--checkpoint-tasks',2,points=16,seed=SEED+82);E.run_all(m2)
    assert max(j['blocks']for j in manifest(m2)['jobs'])>4
    s2=E.td/'spills_ser';shutil.copytree(m2,s2);cli(prod,'merge',s2,'--serial');scr=E.td/'spills_scratch';scr.mkdir()
    cli(prod,'merge',m2,'--fan-in',2,'--jobs',2,'--scratch',scr)
    for g in manifest(m2)['groups']:
        for t in ('merged.json','graph_replicates.csv','graph_tails.csv','graph_costs.csv'):assert (m2/'groups'/g['name']/t).read_bytes()==(s2/'groups'/g['name']/t).read_bytes(),(g['name'],t)
    assert not list(scr.iterdir()),list(scr.iterdir())
    ok('merge_cached_runs_verified_rebuilt_on_tamper_O01_multiblock_phase1_spills_O02',**out)


# ================================================================ array mode on fake Slurm (A-ORC-7 carried over; A-ORC-5 memory)
def expand(spec):
    out=[]
    for part in spec.split('%')[0].split(','):
        lo,_,hi=part.partition('-');out.extend(range(int(lo),int(hi or lo)+1))
    return out

def incomplete_campaign(E,name,n_missing=4,extra=()):
    """A small campaign run to completion, then the last checkpoint of n_missing jobs deleted."""
    d=E.td/name;E.small(d,'--shards',1,*extra);E.run_all(d);m=manifest(d);picked=[]
    for j in m['jobs']:
        cps=sorted((d/'groups'/j['group']/'checkpoints').glob(f's{j["shard"]:06d}_p*.json'))
        if cps and len(picked)<n_missing:cps[-1].unlink();picked.append(j['id'])
    return d,m,picked

def Q(tag,task,state,jobid,**kw):return {'comment':tag,'task':str(task),'state':state,'jobid':str(jobid),**kw}

def test_recovery_plan(E):
    prod=E.M.prod;d,m,(A,B,C,D)=incomplete_campaign(E,'rp');tag=prod.campaign_tag(d)
    twin=E.td/'rp_twin';E.small(twin,'--shards',1)
    assert (d/'manifest.json').read_bytes()==(twin/'manifest.json').read_bytes()and prod.campaign_tag(twin)!=tag
    R=lambda lines,size=1000:prod.recovery_plan(d,'\n'.join(lines),size);k=f'{tag}:off=0'
    r=R([f'{k}|{A}|RUNNING|900_{A}',f'{k}|{B}|SUSPENDED|900_{B}',f'{k}|{C}|CANCELLED|900_{C}',f'{tag}:merge|N/A|COMPLETED|901',
         f'{prod.campaign_tag(twin)}:off=0|{D}|RUNNING|950_{D}',f'{prod.campaign_tag(twin)}:merge|N/A|PENDING|951','other|N/A|RUNNING|5'])
    assert r['refuse']is None and sorted(i for w in r['arrays']for i in expand(w['array']))==sorted([C,D])and r['merge_waits_on_live_tasks']==sorted([f'900_{A}',f'900_{B}']),r
    for lines,code in (([f'{tag}:merge|N/A|PENDING|902'],65),([f'{tag}:lane|N/A|RUNNING|903'],65),([f'{k}|{A}|COMPLETING|900_{A}'],69),([f'{k}|{A}|PREEMPTED|900_{A}'],69),
                       ([f'{k}|{A}|WEIRDSTATE|900_{A}'],69),([f'{k}|2-3%64|PENDING|900_[2-3%64]'],69)):
        r=R(lines);assert r['refuse']and r['refuse']['code']==code,(lines,r)
    assert cli(prod,'tag',d).stdout.strip()==tag
    q=E.td/'queue.txt';q.write_text(f'{k}|{A}|RUNNING|900_{A}\n');r=json.loads(cli(prod,'recover',d,'--queue',q).stdout)
    assert r['refuse']is None and r['merge_waits_on_live_tasks']==[f'900_{A}']
    cli(prod,'check-sbatch-args','--','-A','acct','--time=1:00');r=cli(prod,'check-sbatch-args','--','--array=0-3',expect=1);assert 'not allowed'in r.stderr
    ok('recovery_plan_and_cli',tag=tag)

def test_slurm_arrays(E):
    prod=E.M.prod;d,m,(A,B,C,D)=incomplete_campaign(E,'fs');tag=prod.campaign_tag(d);S=Slurm(E,'arrays',C8_RUN=str(d),C8_MAX_ARRAY='2',C8_THROTTLE='3',
        SQUEUE_STATES='PENDING',SBATCH_ARRAY_INX='0-3',SBATCH_DEPENDENCY='afterok:1',SBATCH_EXPORT='NONE',SBATCH_ACCOUNT='site',C8_INDEX_OFFSET='0')
    k=f'{tag}:off=0';lines=[Q(k,A,'RUNNING',f'900_{A}'),Q(k,B,'PENDING',f'900_{B}',hidden=True),Q(k,C,'CANCELLED',f'900_{C}'),Q(f'{tag}:merge','N/A','COMPLETED','901')]
    S.queue(*lines);cp,calls=S.call('resubmit.sh',['--time=00:05:00']);assert cp.returncode==0,cp.stderr[-800:]
    q=[x for x in S.log()if x['cmd']=='squeue'][0];assert q['SQUEUE_STATES']is None and q['args'][q['args'].index('-u')+1]==REAL_USER!=FOREIGN and '--all'in q['args']and '-r'in q['args']
    works=[c for c in calls if c['script']=='run_array.sh'];merge=[c for c in calls if c['script']=='merge.sh']
    eff=lambda c:int(c['env']['C8_INDEX_OFFSET'])
    assert len(merge)==1 and sorted(eff(c)+i for c in works for i in expand(last(c['args'],'--array')))==sorted([C,D]),(works,merge)
    for c in calls:
        assert c['env']['C8_TEST_MARK']=='sourced'and c['env']['SBATCH_ARRAY_INX']is None and c['env']['SBATCH_DEPENDENCY']is None and c['env']['SBATCH_EXPORT']is None and c['env']['SBATCH_ACCOUNT']=='site'
        assert c['env']['C8_RUN']==str(d.resolve())and c['env']['C8_PACKAGE']==str(E.pkg.resolve())
    for c in works:
        w=c['args'];off=eff(c)
        assert last(w,'--comment')==f'{tag}:off={off}'and last(w,'--array').endswith('%3')and off%2==0 and last(w,'--job-name')=='c8d2-array'
        assert last(w,'--time')=='00:05:00'and last(w,'--cpus-per-task')==str(m['threads'])and w[:4]==['--parsable','-A','acct','-p']
        assert last(w,'--mem')==f'{m["estimates"]["mem_suggestion_mb"]}M'  # A-ORC-5: the plan's suggestion
    mw=merge[0]['args'];assert merge[0]['env']['C8_INDEX_OFFSET']is None and last(mw,'--comment')==f'{tag}:merge'and last(mw,'--job-name')=='c8d2-merge'
    assert last(mw,'--dependency')=='afterok:'+':'.join([c['jobid']for c in works]+sorted([f'900_{A}',f'900_{B}']))
    led=[json.loads(l)for l in (d/'submissions.jsonl').read_text().splitlines()];assert [x['jobid']for x in led]==[c['jobid']for c in calls]and {x['role']for x in led}=={'array','merge'}
    assert all(x['schema']=='c8-d2-ledger-1'and x['source']=='slurm_submit'for x in led)
    # A-ORC-5: a user --mem below the suggestion is refused (64), a larger one is used
    cp,calls=S.call('resubmit.sh',['--time=00:05:00'],C8_SBATCH_ARGS='-A acct -p part --mem=100M');assert cp.returncode==64 and not calls and 'below the plan'in cp.stderr
    cp,calls=S.call('resubmit.sh',['--time=00:05:00'],C8_SBATCH_ARGS='-A acct -p part --mem=900G');assert cp.returncode==0
    assert all(last(c['args'],'--mem')in('900G',None)or c['script']=='merge.sh'for c in calls)and last([c for c in calls if c['script']=='merge.sh'][0]['args'],'--mem')=='64G'
    # every refusal submits nothing
    for script in ('resubmit.sh','submit.sh'):
        for bad in ('-A acct --array=0-3','-a0-3 -p part','-A acct -d afterok:1','-A acct --export=NONE','-A acct --comment=x','-A acct -o /tmp/x','-A acct --exclusive',
                    '-A acct --export-f=x','-A acct --arr=0-3','-A acct --nice --export-file=x','-A acct -M other','-A acct stray','-A acct --job-name','-A acct "unbalanced'):
            cp,calls=S.call(script,C8_SBATCH_ARGS=bad);assert cp.returncode==64 and not calls,(script,bad,cp.returncode,cp.stderr[-300:],calls)
        for envbad in ({'SBATCH_CLUSTERS':'other'},{'SLURM_CLUSTERS':'other'},{'C8_THROTTLE':'64 --dependency=afterok:1'},{'C8_THROTTLE':'0'},{'C8_MAX_ARRAY':'x'},
                       {'C8_SBATCH_ARGS':'-A acct\n-p part'},{'C8_TIME_POLICY':'forever'},{'C8_SITE':'mars'}):
            cp,calls=S.call(script,**envbad);assert cp.returncode==64 and not calls,(script,envbad,cp.stderr[-300:],calls)
    S.queue(Q(f'{tag}:merge','N/A','SPECIAL_EXIT','903'));cp,calls=S.call('resubmit.sh',['--time=00:05:00']);assert cp.returncode==65 and not calls
    S.queue(Q(k,A,'COMPLETING',f'900_{A}'));cp,calls=S.call('resubmit.sh',['--time=00:05:00']);assert cp.returncode==69 and not calls
    cp,calls=S.call('resubmit.sh',['--time=00:05:00'],FAKE_SQUEUE_FAIL='1');assert cp.returncode==69 and not calls
    # a pinned tool that differs from the plan: every entry point refuses (64) before any Slurm call
    tp=E.pkg/'tools/lanes.py';orig=tp.read_bytes()
    try:
        tp.write_bytes(orig+b'\n# changed\n')
        for script,args in (('submit.sh',['--time=00:05:00']),('resubmit.sh',['--time=00:05:00']),('submit.sh',['--window','0:0','--time=00:05:00']),('submit.sh',['--lanes','1'])):
            cp,calls=S.call(script,args);assert cp.returncode==64 and not calls and 'pinned tools differ'in cp.stderr,(script,cp.returncode,cp.stderr[-300:])
    finally:tp.write_bytes(orig)
    # submit and window also snapshot first (the bootstrap plan has no wall-time estimate: --time is given)
    t5='--time=00:05:00'
    S.queue(Q(k,A,'RUNNING',f'900_{A}'));cp,calls=S.call('submit.sh',[t5]);assert cp.returncode==65 and not calls
    S.queue(Q(f'{tag}:lane','N/A','RUNNING','910'));cp,calls=S.call('submit.sh',[t5]);assert cp.returncode==65 and not calls and 'lane worker'in cp.stderr
    S.queue(Q(k,A,'PENDING',f'900_{A}'));cp,calls=S.call('submit.sh',['--window',f'0:{A}',t5]);assert cp.returncode==65 and not calls,(A,cp.returncode,cp.stderr[-400:])
    S.queue();cp,calls=S.call('submit.sh',['--window',f'0:{A}']);assert cp.returncode==64 and not calls and 'no wall-time estimate'in cp.stderr
    full=[j['id']for j in m['jobs']if j['id']not in (A,B,C,D)][0]
    cp,calls=S.call('submit.sh',['--window',f'{full//2*2}:{full%2}',t5]);assert cp.returncode==0 and not calls and 'nothing to submit'in cp.stdout
    for spec in ('x:1','0:','0:3-1','-1:0',f'0:{len(m["jobs"])}','0:0-5'):
        cp,calls=S.call('submit.sh',['--window',spec,t5]);assert cp.returncode==64 and not calls,(spec,cp.stderr[-200:])
    cp,calls=S.call('submit.sh',['--time=00:07:00']);assert cp.returncode==0,cp.stderr[-600:]
    works=[c for c in calls if c['script']=='run_array.sh'];merge=[c for c in calls if c['script']=='merge.sh']
    assert len(merge)==1 and sorted(eff(c)+i for c in works for i in expand(last(c['args'],'--array')))==sorted([A,B,C,D])
    assert 'idle node'in cp.stdout and 'sbatch --test-only'in cp.stdout or 'idle node'in cp.stdout
    rs=[l.split('resubmit: ',1)[1]for l in tool(E.pkg,'production.py','status',d,env={'C8_MAX_ARRAY':'2'},check=False).stdout.splitlines()if l.startswith('resubmit: ')]
    assert rs and all(int(x.split('--window ')[1].split(':')[0])%2==0 for x in rs)
    cp,calls=S.call(None,cmd=['bash','-c',rs[0]+' --time=00:05:00'],C8_RUN='/stale/run',C8_PACKAGE='/stale/pkg',C8_INDEX_OFFSET='999')
    assert cp.returncode==0 and len(calls)==1 and calls[0]['env']['C8_RUN']==str(d.resolve()),cp.stderr[-300:]
    ok('slurm_arrays_recovery_refusals_windows_status_lines_memory')
    # sequential repeats submit once
    fresh=E.td/'seq';E.small(fresh,'--shards',1);nf=len(manifest(fresh)['jobs']);S.queue()
    cp,c1=S.call('submit.sh',['--time=00:05:00'],C8_RUN=str(fresh),FAKE_REGISTER='1');assert cp.returncode==0,cp.stderr[-400:]
    cp,c2=S.call('submit.sh',['--time=00:05:00'],C8_RUN=str(fresh),FAKE_REGISTER='1');assert cp.returncode==65 and c2==[],cp.stderr[-300:]
    assert sorted(eff(c)+i for c in c1 if c['script']=='run_array.sh'for i in expand(last(c['args'],'--array')))==list(range(nf))
    us={x['args'][x['args'].index('-u')+1]for x in S.log()if x['cmd']=='squeue'and '-u'in x['args']};assert us=={REAL_USER},us
    ok('sequential_repeats_submit_once',fresh_jobs=nf,squeue_user=REAL_USER,foreign_USER=FOREIGN)
    # time policy
    t1=E.td/'time_unl';E.small(t1,'--shards',1);S.queue()
    cp,calls=S.call('submit.sh',C8_RUN=str(t1),C8_TIME_POLICY='unlimited',C8_SBATCH_ARGS='-A acct -p part');assert cp.returncode==0,cp.stderr[-400:]
    assert calls and all(c['args'][-2]=='--time=0'for c in calls)
    for x in ({'C8_SBATCH_ARGS':'-A acct -t 5'},{'C8_SBATCH_ARGS':'-A acct --time=01:00:00'}):
        cp,calls=S.call('submit.sh',C8_RUN=str(t1),C8_TIME_POLICY='unlimited',**x);assert cp.returncode==64 and not calls
    cp,calls=S.call('submit.sh',C8_RUN=str(t1),C8_TIME_POLICY='unlimited',FAKE_TIMELIMIT='01:00:00');assert cp.returncode==70 and len(calls)==1 and 'NOT cancelled'in cp.stderr
    assert not (t1/'.c8_submit.lock').exists()
    S.queue();cp,calls=S.call('submit.sh',C8_RUN=str(t1));assert cp.returncode==64 and not calls and 'no wall-time estimate'in cp.stderr  # bootstrap plan: give --time
    cp,calls=S.call('submit.sh',['--time=00:30:00'],C8_RUN=str(t1));assert cp.returncode==0 and all(last(c['args'],'--time')=='00:30:00'for c in calls)
    ok('time_policy_unlimited_and_finite')
    # the campaign lock: one submission at a time, removed on every exit path; '%' escaped in log paths
    lock=d/'.c8_submit.lock';fifo=S.td/'block.fifo';os.mkfifo(fifo);S.queue(*lines)
    with Owned(markers=(str(S.td/'fakebin'),),fifos=(fifo,))as own:  # Z13: the blocked submission is cleaned up whatever fails
        first=own.add(subprocess.Popen(['bash',str(E.pkg/'slurm/resubmit.sh'),'--time=00:05:00'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                       env={**S.base,'FAKE_SBATCH_BLOCK':str(fifo)},start_new_session=True))
        assert wait_for(lambda:(lock/'owner.json').exists()and any(x['cmd']=='squeue'for x in S.log()),60),'first resubmit did not take the lock'
        for script,args in (('resubmit.sh',['--time=00:05:00']),('submit.sh',['--time=00:05:00']),('submit.sh',['--window','0:0','--time=00:05:00']),('submit.sh',['--lanes','1'])):
            cp=subprocess.run(['bash',str(E.pkg/'slurm'/script),*args],capture_output=True,text=True,env=S.base);assert cp.returncode==75 and 'holds'in cp.stderr,(script,cp.returncode,cp.stderr[-300:])
        fifo_go(fifo)
        out,err=first.communicate(timeout=300);assert first.returncode==0,err[-500:]
    assert not lock.exists()and not own.killed,own.killed
    cp,calls=S.call('resubmit.sh',['--time=00:05:00'],FAKE_SBATCH_FAIL='1');assert cp.returncode not in(0,75)and not lock.exists()
    lock.mkdir();(lock/'owner.json').write_text('{"host":"elsewhere","pid":1}\n');n_sq=sum(1 for x in S.log()if x['cmd']=='squeue')
    cp,calls=S.call('resubmit.sh',['--time=00:05:00']);assert cp.returncode==75 and 'elsewhere'in cp.stderr and sum(1 for x in S.log()if x['cmd']=='squeue')==n_sq
    shutil.rmtree(lock)
    pct=E.td/'run%jdir%%x';E.small(pct,'--shards',1);S.queue()
    cp,calls=S.call('submit.sh',['--time=00:10:00'],C8_RUN=str(pct));assert cp.returncode==0 and calls,cp.stderr[-400:]
    esc=str(pct.resolve()/'slurm_logs').replace('%','%%');outs=[last(c['args'],'--output')for c in calls]
    assert all(o.startswith(esc+'/')for o in outs)and any('/work-%A_%a.log'in o for o in outs)and any('/merge-%j.log'in o for o in outs),outs
    ok('submission_lock_and_percent_escape')


# ================================================================ lane mode (A-ORC-4, A-ORC-5, A-ORC-10, A-ORC-11, A-ORC-12)
def lanes_plan(E,d,*extra,seed=SEED,points=4096,tg=2,hours=0.002):
    """A test-only lane-mode plan (measured basis from a synthetic cost model, so every index has an estimate)."""
    cm=E.td/'cm_lanes.json'
    if not cm.exists():cm.write_text(json.dumps(cost_model_for(E,None,lambda c,s,L,r:2e-5*(1+r['id']%3))))
    return E.plan(d,'--pilot','--points',points,'--replicates',2,'--test-graphs',tg,'--cost-model',cm,'--index-hours',hours,*extra,seed=seed)

def fake_sysfs(td:Path,name:str,sockets:int,cores:int,nodes:int,smt:int=1,vendor='AuthenticAMD',cgroup_bytes=None)->Path:
    """A fake /sys and /proc: sockets x cores physical cores (x smt logical), split into `nodes` NUMA nodes."""
    root=td/f'sysfs_{name}';n=sockets*cores
    for c in range(n*smt):
        phys=c%n;t=root/f'sys/devices/system/cpu/cpu{c}/topology';t.mkdir(parents=True)
        (t/'physical_package_id').write_text(str(phys//cores));(t/'core_id').write_text(str(phys%cores))
    per=n//nodes
    for k in range(nodes):
        cl=[str(x)for x in range(k*per,(k+1)*per)]+[str(x+n)for x in range(k*per,(k+1)*per)if smt>1]
        nd=root/f'sys/devices/system/node/node{k}';nd.mkdir(parents=True);(nd/'cpulist').write_text(','.join(cl)+'\n')
    (root/'proc/self').mkdir(parents=True);(root/'proc/cpuinfo').write_text(f'vendor_id\t: {vendor}\nmodel name\t: Fake CPU\n')
    if cgroup_bytes is not None:
        (root/'proc/self/cgroup').write_text('0::/slurm/job_1\n');g=root/'sys/fs/cgroup/slurm/job_1';g.mkdir(parents=True);(g/'memory.max').write_text(f'{cgroup_bytes}\n')
    return root

def test_lane_units(E):
    L=E.M.lanes
    # lane shapes from fake sysfs trees: symmetry AMD 8 x 8, Intel 2 x 20 (SMT siblings idle), Expanse 8 x 16
    for name,(sk,co,nn,smt,vend,spec,want) in {'amd':(2,32,8,1,'AuthenticAMD',None,[8]*8),'intel':(2,20,2,2,'GenuineIntel',None,[20,20]),
                                                'expanse':(2,64,8,1,'AuthenticAMD','numa',[16]*16 if False else[16]*8),'parts':(2,32,8,1,'AuthenticAMD','3',[22,21,21])}.items():
        root=fake_sysfs(E.td,name,sk,co,nn,smt,vend)
        with mock.patch.dict(os.environ,{'C8_SYSFS':str(root/'sys'),'C8_PROC':str(root/'proc')}):
            got=L.cpu_lanes(list(range(sk*co*smt)),spec);assert [len(x)for x in got]==want,(name,[len(x)for x in got])
            assert len({c for l in got for c in l})==sum(want)
            if name=='intel':assert all(c<40 for l in got for c in l)  # one logical CPU per physical core
    assert [len(x)for x in L.cpu_lanes(list(range(6)),'3',drill=True)]==[2,2,2]and [len(x)for x in L.cpu_lanes([4,5,6,7],None,drill=True)]==[4]
    try:L.cpu_lanes(list(range(4)),'numa',drill=False,nodes={0:[0,1],1:[2,3]});L.cpu_lanes(list(range(4)),'5')
    except E.M.common.Refuse as r:assert r.code==64
    else:raise AssertionError('5 lanes on 4 cores accepted')
    assert L.parse_timeleft('1-02:03:04')==93784 and L.parse_timeleft('05:06')==306 and L.parse_timeleft('UNLIMITED')==math.inf and L.parse_timeleft('INVALID')is None
    # the memory guard: lanes reduced, or a refusal when not even one fits
    assert L.memory_guard(8,10*2**30,100*2**30)==8 and L.memory_guard(8,20*2**30,100*2**30)==4
    try:L.memory_guard(8,90*2**30,100*2**30);raise AssertionError('accepted')
    except E.M.common.Refuse as r:assert r.code==64
    root=fake_sysfs(E.td,'cg',1,4,1,cgroup_bytes=10*2**30)
    with mock.patch.dict(os.environ,{'C8_SYSFS':str(root/'sys'),'C8_PROC':str(root/'proc')}):
        assert L.memory_limit({})==(10*2**30,'cgroup')
        assert L.memory_limit({'SLURM_MEM_PER_NODE':'2048'})==(10*2**30,'cgroup')  # a visible cgroup limit wins
    # T-06: with no cgroup limit visible, SLURM_MEM_PER_NODE (MiB) is the limit, exactly, and it drives the guard
    with mock.patch.object(L,'cgroup_memory_limit',return_value=None):
        assert L.memory_limit({'SLURM_MEM_PER_NODE':'2048'})==(2048*2**20,'SLURM_MEM_PER_NODE')
        assert L.memory_limit({})==(None,'none')and L.memory_limit({'SLURM_MEM_PER_NODE':'2G'})==(None,'none')
        lim=L.memory_limit({'SLURM_MEM_PER_NODE':'2048'})[0]
        assert L.memory_guard(8,600*2**20,lim)==2 and L.memory_guard(8,100*2**20,lim)==8  # floor(0.85 x 2048 / 600) = 2
        try:L.memory_guard(8,1800*2**20,lim);raise AssertionError('accepted')
        except E.M.common.Refuse as r:assert r.code==64 and 'the job memory limit 2.0 GiB'in str(r),str(r)
    # the class factor of the deadline: 1 on the reference CPU, the measured factor, 1.5 unknown
    cm={'cpu_models':['Ref CPU'],'cpu_class_factors':{'Slow CPU':{'a':{'free':{'6':1.4,'8':2.0}}}}}
    assert (L.class_factor(cm,'Ref  CPU','a','free',8),L.class_factor(cm,'Slow CPU','a','free',8),L.class_factor(cm,'Slow CPU','a','free',4),L.class_factor(cm,'Other','a','free',8))==(1.0,2.0,1.4,1.5)
    ok('lane_shapes_timeleft_memory_guard_class_factor')

def test_p4_defaults(E):
    """R5b (Stage 4b; docs/PERFORMANCE.md, the P4 decisions): the scheduling defaults. A plan given none of the sizing
    options has --threads 8, --checkpoint-tasks 256 (max(16 x 8, 256), the P4 block), 60 s tasks bounded by 120 s and
    indices of 1.5 h of the lane width. With C8_LANES unset the lanes are the best P4 shapes, NUMA-aligned lanes of the
    plan's 8 threads: 8 x 8 on symmetry's AMD nodes (8 NUMA nodes of 8 cores) and 16 x 8 on Expanse compute (8 NUMA
    nodes of 16 cores), every lane inside one NUMA node. C8_LANES=numa keeps one lane per NUMA node (8 x 16 on Expanse),
    C8_LANES=16 gives 16 x 8, Intel nodes keep one lane per socket, checkpoint_tasks still caps the width, drill mode
    ignores it, and the sweep's default process slots follow the same rule at its --threads."""
    p=E.M.prod;L=E.M.lanes;Refuse=E.M.common.Refuse
    cm=E.td/'cm_p4_defaults.json';cm.write_text(json.dumps(cost_model_for(E,None,lambda c,s,L_,r:2e-4*(1+r['id']%3))))
    d=E.td/'p4_defaults';cli(p,'plan',d,'--seed',SEED,'--pilot','--points',4096,'--replicates',2,'--test-graphs',2,'--cost-model',cm);m=manifest(d)
    assert (m['threads'],m['checkpoint_tasks'])==(8,256),(m['threads'],m['checkpoint_tasks'])
    assert m['chunking']=={'task_seconds':60.0,'min_chunk':256,'max_task_seconds':120.0},m['chunking']
    assert m['index_sizing']=={'index_hours':1.5,'shards':None,'assumed_efficiency':0.9},m['index_sizing']
    assert all(v is None or v<=120 for v in m['estimates']['predicted_max_task_seconds'].values()),m['estimates']['predicted_max_task_seconds']
    for g in m['groups']:
        c=config(d,g['name'])
        if not c['tasks']:continue
        secs=c['replicates']*sum(n*json.loads(cm.read_text())['seconds_per_point'][f'{c["campaign"]}:{c["sector"]}:{c["L"]}:{gid}']for gid,n in c['counts'].items())
        assert c['shards']==min(c['tasks'],max(1,math.ceil(secs/(1.5*3600*8*0.9)))),(g['name'],c['shards'])
    # lane shapes on fake sysfs trees (CPUs numbered socket-major, NUMA node k = CPUs k*per .. (k+1)*per-1)
    roots={}
    def shape(name,sk,co,nn,vend,spec,mm,smt=1,drill=False):
        if name not in roots:roots[name]=fake_sysfs(E.td,f'p4_{name}',sk,co,nn,smt,vend)
        root=roots[name];per=sk*co//nn
        with mock.patch.dict(os.environ,{'C8_SYSFS':str(root/'sys'),'C8_PROC':str(root/'proc')}):lanes,what=L.worker_lanes(list(range(sk*co*smt)),spec,mm,drill=drill)
        assert len({c for l in lanes for c in l})==sum(map(len,lanes)),name
        if not drill and vend=='AuthenticAMD':assert all(len({c//per for c in l})==1 for l in lanes),(name,spec,'a lane crosses a NUMA node')
        return [len(l)for l in lanes],what
    P8={'threads':8,'checkpoint_tasks':256}
    assert shape('symmetry',2,32,8,'AuthenticAMD',None,P8)[0]==[8]*8
    got,what=shape('expanse',2,64,8,'AuthenticAMD',None,P8);assert got==[8]*16 and 'default lanes'in what and '--threads 8'in what,(got,what)
    assert shape('expanse',2,64,8,'AuthenticAMD','numa',P8)[0]==[16]*8 and shape('expanse',2,64,8,'AuthenticAMD','16',P8)[0]==[8]*16
    assert shape('expanse',2,64,8,'AuthenticAMD',None,{'threads':16,'checkpoint_tasks':256})[0]==[16]*8  # J-SWEEP-1's --threads 16
    got,what=shape('expanse',2,64,8,'AuthenticAMD',None,{'threads':8,'checkpoint_tasks':4});assert got==[4]*32 and 'checkpoint_tasks=4'in what,(got,what)
    try:shape('expanse',2,64,8,'AuthenticAMD','8',{'threads':8,'checkpoint_tasks':4});raise AssertionError('C8_LANES=8 lanes of 16 > checkpoint_tasks 4 accepted')
    except Refuse as r:assert r.code==64 and 'checkpoint_tasks=4'in str(r),str(r)
    assert shape('intel',2,20,2,'GenuineIntel',None,P8,smt=2)[0]==[20,20]
    assert shape('odd',1,12,1,'AuthenticAMD',None,P8)[0]==[6,6]
    assert shape('expanse',2,64,8,'AuthenticAMD','2',P8,drill=True)[0]==[64,64]
    with mock.patch.dict(os.environ,{'C8_SYSFS':str(roots['expanse']/'sys'),'C8_PROC':str(roots['expanse']/'proc')}):
        for bad in (0,-8,True,'8'):
            try:L.cpu_lanes(list(range(128)),None,width=bad);raise AssertionError(f'lane width {bad!r} accepted')
            except Refuse as r:assert r.code==64
        assert [len(x)for x in L.cpu_lanes(list(range(128)),None)]==[16]*8  # no width: one lane per NUMA node, as before
    # the sweep's default process slots: the same rule at the sweep's --threads
    sys.modules.pop('sweep',None);import sweep
    assert Path(sweep.__file__).resolve().is_relative_to(E.pkg.resolve()),sweep.__file__
    run=E.td/'p4_sweep';run.mkdir();(run/'manifest.json').write_text(json.dumps({'jobs':[]}))
    for th,want in ((8,[8]*16),(16,[16]*8)):
        out=io.StringIO()
        with mock.patch.dict(os.environ,{'C8_SYSFS':str(roots['expanse']/'sys'),'C8_PROC':str(roots['expanse']/'proc')}),\
             mock.patch.object(os,'sched_getaffinity',create=True,return_value=set(range(128))),contextlib.redirect_stdout(out):
            assert sweep.run_indices(run,NS(threads=th,procs=None,scratch=None),{})==[]
        assert f'{len(want)} process slots of {want} CPUs'in out.getvalue(),(th,out.getvalue())
    ok('p4_defaults_plan_sizing_and_lane_shapes',expanse_default='16x8',symmetry_default='8x8')

@contextlib.contextmanager
def at_most_cpus(n:int):
    """Pin this process to at most n CPUs of its affinity set for the block (Linux; restored afterwards), so that the
    tools it starts, which inherit the mask, see a lane test's intended CPU count on any node. F1 (Stage 5): on a whole
    64- or 128-core node test_lanes' C8_LANES=2 gave lanes of 32 or 64 cores, wider than the test plan's
    checkpoint_tasks=8, which lanes.py refuses (64) as designed. Without sched_setaffinity (macOS) nothing changes."""
    get=getattr(os,'sched_getaffinity',None);put=getattr(os,'sched_setaffinity',None)
    if get is None or put is None:yield None;return
    old=get(0)
    if len(old)<=n:yield sorted(old);return
    new=set(sorted(old)[:n]);put(0,new)
    try:yield sorted(new)
    finally:put(0,old)

@contextlib.contextmanager
def keep_affinity():
    """Restore this process's CPU affinity after the block: lanes.cmd_lane, called in-process, pins the calling thread to
    its lane's CPUs (Linux), which would leave every later test on those CPUs."""
    get=getattr(os,'sched_getaffinity',None);old=get(0)if get else None
    try:yield
    finally:
        if old is not None:os.sched_setaffinity(0,old)

def test_lanes(E):
    """The lane worker tests, run on at most 16 CPUs (F1): two lanes of at most 8 cores, the test plan's checkpoint_tasks."""
    with at_most_cpus(16)as cpus:_test_lanes(E,cpus)

def _test_lanes(E,cpus):
    L=E.M.lanes;p=E.M.prod;fb=fake_bin(E.td/'lanesbin'if (E.td/'lanesbin').mkdir()is None else E.td/'lanesbin')
    sq=E.td/'fakesq';sq.mkdir(exist_ok=True);(sq/'squeue').write_text('#!/bin/bash\n[[ -n "${SQUEUE_STATES:-}" ]] && exit 0\n[[ -n "${FAKE_TIMELEFT:-}" ]] && { echo "$FAKE_TIMELEFT"; exit 0; }\nexit 1\n');(sq/'squeue').chmod(0o755)
    d=E.td/'lanes';lanes_plan(E,d);m=manifest(d);n=len(m['jobs']);env={'SLURM_JOB_ID':'4242','C8_LANE_SECONDS':'36000','C8_LANES':'2','PATH':f'{sq}:{os.environ["PATH"]}'}
    assert n>4,n
    tool(E.pkg,'lanes.py','queue',d);q=L.read_queue(d);ests=[e for _,e in q]
    assert sorted(i for i,_ in q)==list(range(n))and ests==sorted(ests,reverse=True)
    assert (d/'lanes/queue.txt').read_text().startswith('# c8d2-lanes-queue generation=')
    L.claim(d,q[0][0],{'job':'4242','lane':0});L.claim(d,q[1][0],{'job':'777','lane':0})
    cp=tool(E.pkg,'lanes.py','worker',d,env=env);assert cp.returncode==0,cp.stderr[-800:]
    assert f'released own stale claim {q[0][0]}'in cp.stdout
    st=json.loads(tool(E.pkg,'production.py','status',d,'--json',check=False).stdout)
    assert st['missing_jobs']==[q[1][0]]and st['lanes']['claimed']==[q[1][0]]and st['lanes']['owners']==['777'],st
    logs=list((d/'lanes/logs').glob('idx*.4242.*.log'));assert len(logs)==n-1 and all(len(x.name.split('.'))==6 for x in logs)  # idx<i>.<job>.<restart>.<lane>.<ns>.log
    assert sorted(int(x)for x in os.listdir(d/'lanes/done'))==sorted(set(range(n))-{q[1][0]})
    snap=E.td/'snap.txt'
    for state,code,kept in (('RUNNING',0,True),('PENDING',0,True),('REQUEUED',0,True),('COMPLETING',69,True),('PREEMPTED',69,True),('TIMEOUT',0,False)):
        snap.write_text(f'x|N/A|{state}|777\n');os.utime(snap,None)
        cp=tool(E.pkg,'lanes.py','release-stale',d,'--queue',snap,check=False);assert cp.returncode==code,(state,cp.returncode,cp.stderr[-300:])
        assert L.claim_path(d,q[1][0]).exists()==kept,state
        if not kept:break
    L.claim(d,q[1][0],{'job':'778','lane':0});snap.write_text('');t=time.time()+400;os.utime(snap,(t,t))
    cp=tool(E.pkg,'lanes.py','release-stale',d,'--queue',snap,'--dry-run');assert L.claim_path(d,q[1][0]).exists()and json.loads(cp.stdout)['release']
    cp=tool(E.pkg,'lanes.py','release-stale',d,'--queue',snap);assert not L.claim_path(d,q[1][0]).exists()
    # time guard: nothing fits in 10 s; Slurm's answer wins over the fallback; inherited SQUEUE_* cannot hide the job
    cp=tool(E.pkg,'lanes.py','worker',d,env={**env,'C8_LANE_SECONDS':'10'});assert cp.returncode==0 and 'finished, 0 indices run'in cp.stdout and 'C8_LANE_SECONDS'in cp.stdout
    cp=tool(E.pkg,'lanes.py','worker',d,env={**env,'C8_LANE_SECONDS':'86400','FAKE_TIMELEFT':'00:00:20'});assert '(squeue)'in cp.stdout and 'finished, 0 indices run'in cp.stdout
    cp=tool(E.pkg,'lanes.py','worker',d,env={k:v for k,v in {**env,'FAKE_TIMELEFT':'00:00:20','SQUEUE_STATES':'PENDING'}.items()if k!='C8_LANE_SECONDS'});assert '(squeue)'in cp.stdout
    cp=tool(E.pkg,'lanes.py','worker',d,env={k:v for k,v in env.items()if k!='C8_LANE_SECONDS'},check=False);assert cp.returncode==69 and 'C8_LANE_SECONDS'in cp.stderr
    # UNLIMITED: no deadline under the unlimited policy; under the finite policy it falls back (C7(3)) or refuses
    cp=tool(E.pkg,'lanes.py','worker',d,env={**{k:v for k,v in env.items()if k!='C8_LANE_SECONDS'},'FAKE_TIMELEFT':'UNLIMITED','C8_TIME_POLICY':'finite'},check=False)
    assert cp.returncode==69 and "'UNLIMITED'"in cp.stderr
    cp=tool(E.pkg,'lanes.py','worker',d,env={**env,'FAKE_TIMELEFT':'UNLIMITED','C8_LANE_SECONDS':'10'});assert 'C8_LANE_SECONDS'in cp.stdout and 'finished, 0 indices run'in cp.stdout
    # the deadline uses the CPU-class factor: with 20000 s left the index fits at factor 1 but not at a measured factor 50
    host=E.M.common.cpu_model_noprobe();cmj=json.loads((d/'cost_model.json').read_text())
    est=q[1][0]and dict(q)[q[1][0]];need1=est*1/(2*0.9)*1.5+300;assert need1<20000,need1
    # failure limits and a consecutive-failure stop
    cp=tool(E.pkg,'lanes.py','worker',d,env={**env,'C8_FAKE_FAIL':'1','C8_LANE_MAX_FAILURES':'1'},check=False);assert cp.returncode==3,cp.stderr[-300:]
    assert L.failure_counts(d)=={q[1][0]:1}and not L.claim_path(d,q[1][0]).exists()
    assert all(len(f.name.split('.'))==6 for f in (d/'lanes/failures').iterdir())  # <idx>.<job>.<restart>.<lane>.<ns>.json
    cp=tool(E.pkg,'lanes.py','worker',d,env=env);assert cp.returncode==0 and 'finished, 1 indices run'in cp.stdout
    assert tool(E.pkg,'production.py','status',d).returncode==0
    # two concurrent workers: every index runs exactly once
    d2=E.td/'lanes_race';lanes_plan(E,d2,seed=SEED+3);tool(E.pkg,'lanes.py','queue',d2)
    with concurrent.futures.ThreadPoolExecutor(2)as ex:
        out=list(ex.map(lambda j:tool(E.pkg,'lanes.py','worker',d2,env={**env,'SLURM_JOB_ID':j,'C8_FAKE_SLEEP':'0.2'},check=False),['5001','5002']))
    assert [c.returncode for c in out]==[0,0],[c.stderr[-300:]for c in out]
    logs=list((d2/'lanes/logs').glob('idx*.log'));idx=sorted(int(x.name[3:].split('.')[0])for x in logs)
    assert idx==list(range(len(manifest(d2)['jobs'])))and tool(E.pkg,'production.py','status',d2).returncode==0 and not list((d2/'lanes/claims').glob('*.json'))
    # lanes never exceed checkpoint_tasks (C7I-12): an explicit too-wide C8_LANES refuses before any claim
    d4=E.td/'lanes_narrow';lanes_plan(E,d4,'--checkpoint-tasks',2,'--threads',1,seed=SEED+4);tool(E.pkg,'lanes.py','queue',d4)
    ncpu=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else os.cpu_count()
    if ncpu>2:
        cp=tool(E.pkg,'lanes.py','worker',d4,env={**env,'C8_LANES':'1'},check=False)
        assert cp.returncode==64 and 'checkpoint_tasks=2'in cp.stderr and not list((d4/'lanes/claims').glob('*.json'))and not L.failure_counts(d4),cp.stderr[-300:]
    # the deadline class factor in a worker run (margin 0, safety 1, lanes of 2-3 cores): a measured factor of 50 for this
    # host's class makes every index skip, where the reference class (factor 1) runs
    cmj=cost_model_for(E,None,lambda c,s_,L_,r:2e-3*(1+r['id']%3));cmj['cpu_class_factors']={host:{c:{s_:{str(x):50.0 for x in range(3,9)}for s_ in('free','power')}for c in('a','b')}}
    cmj['cpu_models']=['Other CPU'];d5=E.td/'lanes_factor';cmf=E.td/'cm_factor.json';cmf.write_text(json.dumps(cmj))
    E.plan(d5,'--pilot','--points',4096,'--replicates',2,'--test-graphs',2,'--cost-model',cmf,'--index-hours',0.002,seed=SEED+5);tool(E.pkg,'lanes.py','queue',d5)
    est_min=min(j['est_core_seconds']for j in manifest(d5)['jobs']);left=max(1,math.ceil(5*est_min/1.8))
    fenv={**env,'C8_LANES':str(max(1,ncpu//2)),'C8_LANE_SECONDS':str(left),'C8_LANE_MARGIN':'0','C8_LANE_SAFETY':'1'}
    cp=tool(E.pkg,'lanes.py','worker',d5,env=fenv);assert 'finished, 0 indices run'in cp.stdout and cp.stdout.count('finished, 0 indices run')==max(1,ncpu//2),cp.stdout[-400:]
    cmj['cpu_models']=[host];cmj['cpu_class_factors']={};d6=E.td/'lanes_factor1';cmf.write_text(json.dumps(cmj))
    E.plan(d6,'--pilot','--points',4096,'--replicates',2,'--test-graphs',2,'--cost-model',cmf,'--index-hours',0.002,seed=SEED+6);tool(E.pkg,'lanes.py','queue',d6)
    cp=tool(E.pkg,'lanes.py','worker',d6,env=fenv);assert 'class factor 1'in cp.stdout,cp.stdout[-400:]
    # T-06, in a worker run: no cgroup limit visible (a fake /proc without self/cgroup), SLURM_MEM_PER_NODE alone sets the
    # memory limit; one that holds 1.5 lanes' largest est_peak_bytes runs 1 of 2 lanes; one below a lane refuses (64)
    d7=E.td/'lanes_slurm_mem';lanes_plan(E,d7,seed=SEED+7);tool(E.pkg,'lanes.py','queue',d7)
    peak=max(j['est_peak_bytes']for j in manifest(d7)['jobs']);fp=E.td/'proc_nocgroup';(fp/'self').mkdir(parents=True,exist_ok=True)
    mib=math.ceil(1.5*peak/0.85/2**20);assert int(0.85*mib*2**20//peak)==1,(peak,mib)
    menv={**env,'C8_LANES':'2','C8_PROC':str(fp),'SLURM_MEM_PER_NODE':str(mib)}
    cp=tool(E.pkg,'lanes.py','worker',d7,env=menv)
    assert f'memory guard: 2 lanes x {peak/2**30:.1f} GiB > 0.85 x {mib*2**20/2**30:.1f} GiB (SLURM_MEM_PER_NODE); running 1 lanes'in cp.stdout,cp.stdout[-600:]
    assert '1 lane(s)'in cp.stdout and f'memory limit {round(mib*2**20/2**30,1)} GiB (SLURM_MEM_PER_NODE)'in cp.stdout,cp.stdout[-600:]
    assert tool(E.pkg,'production.py','status',d7).returncode==0
    d8=E.td/'lanes_slurm_mem_refused';lanes_plan(E,d8,seed=SEED+8);tool(E.pkg,'lanes.py','queue',d8)
    small=max(1,math.floor(0.5*max(j['est_peak_bytes']for j in manifest(d8)['jobs'])/2**20))
    cp=tool(E.pkg,'lanes.py','worker',d8,env={**menv,'SLURM_MEM_PER_NODE':str(small)},check=False)
    assert cp.returncode==64 and 'the job memory limit'in cp.stderr and not list((d8/'lanes/claims').glob('*.json')),(cp.returncode,cp.stderr[-400:])
    ok('lanes_worker_claims_requeue_stale_timeguard_unlimited_class_factor_failures_race_width_slurm_memory_limit',indices=n,slurm_mem_mib=mib,
       cpus=None if cpus is None else len(cpus))

def test_lane_scan_cost(E):
    """A-ORC-4 scale test: a synthetic queue of 10^5 indices with 64 lanes holding claims; filesystem calls per scan
    and claim stay below a constant (spy), one scan takes < 1 s; a new queue generation replaces the done set."""
    L=E.M.lanes;run=E.td/'scan';ld=run/'lanes';(ld/'claims').mkdir(parents=True);(ld/'done').mkdir();(ld/'failures').mkdir()
    entries=[(i,1e5-i)for i in range(10**5)];L.write_queue(run,entries,generation=1)
    for k in range(64):(ld/'claims'/f'{k}.json').write_text('{}')
    for k in range(64,5064):(ld/'done'/str(k)).write_text('{}')
    (ld/'failures'/'5100.1.0.0.1.json').write_text('{}');(ld/'failures'/'5100.1.0.0.2.json').write_text('{}')
    clock=[1000.]
    calls={'stat':0,'listdir':0,'open':0}
    real_stat,real_list,real_rt=os.stat,os.listdir,Path.read_text
    def cstat(*a,**k):calls['stat']+=1;return real_stat(*a,**k)
    def clist(*a,**k):calls['listdir']+=1;return real_list(*a,**k)
    def crt(self,*a,**k):calls['open']+=1;return real_rt(self,*a,**k)
    view=L.LaneView(run,clock=lambda:clock[0])
    with mock.patch.object(os,'stat',cstat),mock.patch.object(os,'listdir',clist),mock.patch.object(Path,'read_text',crt):
        t0=time.perf_counter();view.refresh();first=next(view.candidates(2));t1=time.perf_counter()-t0
        c1=dict(calls)
        for k in calls:calls[k]=0
        clock[0]+=5;t0=time.perf_counter();view.refresh();nxt=next(view.candidates(2));t2=time.perf_counter()-t0;c2=dict(calls)
    assert first[0]==5064 and nxt[0]==5064 and t1<1 and t2<1,(first,nxt,t1,t2)
    assert sum(c1.values())<=5 and sum(c2.values())<=3,(c1,c2)  # first scan: stat, read, 3 listings; later: stat + 2 listings
    (ld/'done'/'5064').write_text('{}');clock[0]+=5;view.refresh();assert next(view.candidates(2))[0]==5064  # done listed at most every 60 s
    L.write_queue(run,entries[1:],generation=2);clock[0]+=1;view.refresh();assert view.gen==2 and next(view.candidates(2))[0]==5065  # new generation: done set replaced
    (ld/'done'/'5064').unlink();L.write_queue(run,entries,generation=3);view.refresh();assert 5064 not in view.done  # replaced, never merged
    clock[0]+=61;(ld/'done'/'5065').write_text('{}');view.refresh();assert 5065 in view.done
    ok('lane_scan_cost_bounded_and_generations',first_scan_calls=c1,later_scan_calls=c2,scan_seconds=round(max(t1,t2),4))

def test_done_markers(E):
    """A-ORC-12 (R03): markers are hints. The queue rebuild of `lanes 1` removes the marker of an index whose checkpoint
    was deleted and logs it; a lane recomputes the index with scientific fields equal to the saved checkpoint; status
    exits 0. A lane started before the rebuild sees the index after the new generation. A claim holder removes a stale
    marker. status and merge never read markers."""
    L=E.M.lanes;p=E.M.prod;d=E.td/'markers';lanes_plan(E,d,seed=SEED+21);m=manifest(d)
    ncpu=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else(os.cpu_count()or 1)
    env={'SLURM_JOB_ID':'6100','C8_LANE_SECONDS':'36000','C8_LANES':str(max(1,-(-ncpu//8)))};sq=E.td/'fakesq'  # lanes of at most 8 CPUs (checkpoint_tasks 8)
    if sq.exists():env['PATH']=f'{sq}:{os.environ["PATH"]}'
    tool(E.pkg,'lanes.py','queue',d);tool(E.pkg,'lanes.py','worker',d,env=env);assert tool(E.pkg,'production.py','status',d).returncode==0
    j=max(m['jobs'],key=lambda j:j['blocks']);idx=j['id'];cp=d/'groups'/j['group']/'checkpoints'/f'{p.block_name(j["shard"],0)}.json'
    assert L.done_path(d,idx).exists();saved=json.loads(cp.read_text());cp.unlink()
    st=tool(E.pkg,'production.py','status',d,check=False);assert st.returncode==1  # the marker is not evidence
    with mock.patch.dict(os.environ,{'C8_INPUTS':str(E.fixture)}):
        r=cli(p,'merge',d,expect=1);assert 'Incomplete campaign'in r.stderr
    old_view=L.LaneView(d);old_view.refresh();assert idx in old_view.done and idx not in [i for i,_ in old_view.candidates(2)]  # the marker hides it
    S=Slurm(E,'markers',C8_RUN=str(d),FAKE_REGISTER='1');S.queue()
    out,calls=S.call('submit.sh',['--lanes','1']);assert out.returncode==0,out.stderr[-500:]
    inv=[json.loads(l)for l in (d/'lanes/done_invalidated.jsonl').read_text().splitlines()];assert [x['index']for x in inv]==[idx]and 'queue rebuild'in inv[0]['reason']
    assert not L.done_path(d,idx).exists()and [i for i,_ in L.read_queue(d)]==[idx]
    old_view.refresh();assert idx not in old_view.done and [i for i,_ in old_view.candidates(2)]==[idx]  # the stale view re-reads the new generation
    tool(E.pkg,'lanes.py','worker',d,env=env);assert tool(E.pkg,'production.py','status',d).returncode==0
    new=json.loads(cp.read_text());assert [{k:r[k]for k in p.SCIENTIFIC}for r in new['native']['rows']]==[{k:r[k]for k in p.SCIENTIFIC}for r in saved['native']['rows']]
    # a stale marker found by the claim holder: the holder removes it and runs the index
    cp.unlink();L.write_queue(d,[(idx,1.)],generation=99);assert L.done_path(d,idx).exists()
    real=L._listdir
    def stale_done(path):return []if Path(path).name=='done'else real(path)
    args=NS(directory=d,lane=0,cpus='0',deadline='inf',job='6200',restart='0')
    with keep_affinity(),mock.patch.object(L,'_listdir',side_effect=stale_done),mock.patch.dict(os.environ,{'C8_INPUTS':str(E.fixture)}):L.cmd_lane(args)
    inv=[json.loads(l)for l in (d/'lanes/done_invalidated.jsonl').read_text().splitlines()]
    assert inv[-1]['index']==idx and 'claim holder'in inv[-1]['reason']and cp.exists()and L.done_path(d,idx).exists()
    assert tool(E.pkg,'production.py','status',d).returncode==0
    ok('done_markers_hints_rebuild_stale_view_claim_holder_not_evidence',index=idx)

def test_recovery_merge(E):
    """F8 (A-ORC-12; J-DRL-8 run unattended on fake Slurm, the Stage-5 failure reproduced): a lane-mode campaign is
    completed and its merge job (slurm/merge.sh: status, merge, assemble) publishes the result. One checkpoint of a
    completed index and its group's merged.json are deleted; `submit.sh --lanes 1` rebuilds the queue (the marker is
    dropped and logged) and a lane recomputes the index with other timings (C8_FAKE_SECONDS), so the group's
    graph_costs.csv and merged.json differ in timing only. The merge job then succeeds: merged.json is the commit point,
    so the uncommitted graph_costs.csv is replaced (reported, timing only) while the scientific tables are identical,
    the new merged.json batches equal the saved ones bitwise, and assemble supersedes the result whose only change is
    that group's merged_sha256 (the old one kept as C8_test_result.superseded.<sha12>.json; the new one verifies). A
    rerun of the merge job keeps everything. Real conflicts are still refused: a changed table of a committed group
    (merged.json present) stops the merge, a stale uncommitted scientific table is replaced and reported as such, and
    a result whose science differs is not overwritten."""
    p=E.M.prod;L=E.M.lanes;d=E.td/'recmerge';lanes_plan(E,d,seed=SEED+41);m=manifest(d)
    ncpu=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else(os.cpu_count()or 1)
    env={'SLURM_JOB_ID':'6300','C8_LANE_SECONDS':'36000','C8_LANES':str(max(1,-(-ncpu//8)))}
    tool(E.pkg,'lanes.py','queue',d);tool(E.pkg,'lanes.py','worker',d,env=env);assert tool(E.pkg,'production.py','status',d).returncode==0
    S=Slurm(E,'recmerge',C8_RUN=str(d),FAKE_REGISTER='1');S.queue();menv=dict(C8_MERGE_JOBS='2',C8_BOOTSTRAP='16')
    cp,_=S.call('merge.sh',**menv);assert cp.returncode==0,(cp.stdout[-800:],cp.stderr[-800:])
    res=d/'C8_test_result.json';saved_res=res.read_bytes()
    j=max(m['jobs'],key=lambda j:j['blocks']);idx=j['id'];g=d/'groups'/j['group'];ck=g/'checkpoints'/f'{p.block_name(j["shard"],0)}.json'
    saved={f:(g/f).read_bytes()for f in('merged.json','graph_replicates.csv','graph_tails.csv','graph_costs.csv')};saved_ck=json.loads(ck.read_text())
    ck.unlink();(g/'merged.json').unlink()
    out,_=S.call('submit.sh',['--lanes','1']);assert out.returncode==0,out.stderr[-600:]
    inv=[json.loads(l)for l in (d/'lanes/done_invalidated.jsonl').read_text().splitlines()];assert [x['index']for x in inv]==[idx],inv
    tool(E.pkg,'lanes.py','worker',d,env={**env,'SLURM_JOB_ID':'6301','C8_FAKE_SECONDS':'1.5'});assert tool(E.pkg,'production.py','status',d).returncode==0
    new_ck=json.loads(ck.read_text())
    assert [{k:r[k]for k in p.SCIENTIFIC}for r in new_ck['native']['rows']]==[{k:r[k]for k in p.SCIENTIFIC}for r in saved_ck['native']['rows']]
    assert [r['seconds']for r in new_ck['native']['rows']]!=[r['seconds']for r in saved_ck['native']['rows']]  # other timings
    # the merge job of J-DRL-8: before F8 it stopped at the stale graph_costs.csv, then at the result's no-clobber rule
    cp,_=S.call('merge.sh',**menv);assert cp.returncode==0,(cp.stdout[-1500:],cp.stderr[-1500:])
    assert f'{j["group"]}: replaced the uncommitted graph_costs.csv'in cp.stdout and 'timing only'in cp.stdout and 'SCIENTIFIC'not in cp.stdout,cp.stdout[-1200:]
    new_m=json.loads((g/'merged.json').read_text());old_m=json.loads(saved['merged.json'])
    assert new_m['batches']==old_m['batches']and new_m['graph_costs_sha256']!=old_m['graph_costs_sha256']
    assert all((g/f).read_bytes()==saved[f]for f in('graph_replicates.csv','graph_tails.csv'))and (g/'graph_costs.csv').read_bytes()!=saved['graph_costs.csv']
    sha=hashlib.sha256(saved_res).hexdigest();keep=d/f'C8_test_result.superseded.{sha[:12]}.json'
    assert 'superseded: scientific content unchanged'in cp.stdout and keep.read_bytes()==saved_res,(cp.stdout[-800:],sorted(x.name for x in d.iterdir()))
    new_r=json.loads(res.read_text());old_r=json.loads(saved_res)
    assert {k for k in new_r if new_r[k]!=old_r[k]}=={'merged_sha256'}and {x for x in new_r['merged_sha256']if new_r['merged_sha256'][x]!=old_r['merged_sha256'][x]}=={j['group']}
    sys.modules.pop('verify_result',None);sys.path.insert(0,str(E.pkg/'tools'))
    import verify_result as vr
    assert vr.verify(new_r)==[],vr.verify(new_r)[:3]
    snap=tree(d);cp,_=S.call('merge.sh',**menv);assert cp.returncode==0 and 'identical result already present; kept'in cp.stdout and tree(d)==snap,cp.stdout[-600:]
    # real conflicts: a committed group's table changed; a stale uncommitted scientific table; a result whose science differs
    other=next(x['name']for x in m['groups']if x['name']!=j['group']and config(d,x['name'])['tasks']);og=d/'groups'/other;c0=(og/'graph_costs.csv').read_bytes()
    replace_bytes(og/'graph_costs.csv',c0+b'0,0,0,0,0,0\n')
    with mock.patch.dict(os.environ,{'C8_INPUTS':str(E.fixture)}):r=cli(p,'merge',d,expect=1)
    assert 'Checksum mismatch'in r.stderr,r.stderr[-400:]
    replace_bytes(og/'graph_costs.csv',c0);rep0=(og/'graph_replicates.csv').read_bytes();m0=(og/'merged.json').read_bytes()
    (og/'merged.json').unlink();replace_bytes(og/'graph_replicates.csv',rep0.replace(b',',b', ',1))
    with mock.patch.dict(os.environ,{'C8_INPUTS':str(E.fixture)}):r=cli(p,'merge',d,'--group',other)
    assert f'{other}: replaced the uncommitted graph_replicates.csv'in r.stdout and 'SCIENTIFIC TABLE CHANGED'in r.stdout,r.stdout[-600:]
    assert (og/'graph_replicates.csv').read_bytes()==rep0 and (og/'merged.json').read_bytes()==m0
    bad=json.loads(res.read_text());bad['test_partial']['C8_full']+=1.;res.write_text(json.dumps(bad,indent=2)+'\n')
    with mock.patch.dict(os.environ,{'C8_INPUTS':str(E.fixture)}):r=cli(E.M.asm,d,'--bootstrap',16,expect=1)
    assert 'exists and differs from the recomputed result'in r.stderr,r.stderr[-400:]
    ok('recovery_of_a_completed_index_merges_and_assembles_F8',index=idx,group=j['group'],superseded=keep.name)

def test_lane_sigterm(E):
    """F7 (A-ORC-8a cleanup, fakes): SIGTERM to the lane worker alone, as slurmstepd delivers a scancel to the batch
    process, while two lanes run native tasks. The worker forwards it to its lanes and each lane to its `production.py
    run`, which stops its native worker and removes its runtime; the lanes remove their scratch and the worker exits 143
    within C8_LANE_STOP_SECONDS. Nothing of the job is left in TMPDIR, no native worker survives, the claims stay (stale)
    with no failure record, and each index log shows the stop. A rerun of the same job id releases its own stale claims
    and completes the campaign. With a native worker that ignores SIGTERM and C8_LANE_STOP_SECONDS=4, the lane kills its
    run's session after 0.8 x 4 s and still removes its scratch, and the worker still exits 143 in time."""
    with at_most_cpus(16):
        out={}
        for case,extra,limit in (('forwarded',{},40.),('stuck_native',{'C8_FAKE_IGNORE_TERM':'1','C8_LANE_STOP_SECONDS':'4'},12.)):
            d=E.td/f'lanesig_{case}';lanes_plan(E,d,seed=SEED+61+len(out));tool(E.pkg,'lanes.py','queue',d)
            scr=E.td/f'lanesig_tmp_{case}';scr.mkdir();flog=E.td/f'lanesig_{case}.log'
            env={k:v for k,v in os.environ.items()if k not in('SLURM_TMPDIR',)}
            env.update(PYTHONDONTWRITEBYTECODE='1',SLURM_JOB_ID='6500',C8_LANE_SECONDS='36000',C8_LANES='2',TMPDIR=str(scr),C8_FAKE_SLEEP='120',C8_FAKE_LOG=str(flog),**extra)
            # Z13 (S6E-R3-01): whatever happens, nothing of the case outlives it: the worker's session (its lanes) AND the
            # production runs, which lanes.py starts in sessions of their own, and their native workers (markers: the
            # campaign and the scratch paths), killed and reaped on every exit path
            with Owned(markers=(str(d),str(scr)))as own:
                proc=own.add(subprocess.Popen([PY,'-B',str(E.pkg/'tools/lanes.py'),'worker',str(d)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,start_new_session=True))
                assert wait_for(lambda:flog.exists()and len(flog.read_text().splitlines())>=2,120),(case,'two native tasks never started')
                natives=[json.loads(l)['pid']for l in flog.read_text().splitlines()];assert all(alive(x)for x in natives)
                assert len(list(scr.glob('c8d2_lane_6500_*/c8d2_runtime_*')))==2 and len(list((d/'lanes/claims').glob('*.json')))==2,(case,list(scr.rglob('*'))[:10])
                t0=time.time();proc.send_signal(signal.SIGTERM);so,se=proc.communicate(timeout=120);took=time.time()-t0
                stray=[(pid,args)for pid,pg,args in own.survivors()if pg==proc.pid]  # the worker's session right after it exited
                assert proc.returncode==143 and took<limit,(case,proc.returncode,took,so[-800:],se[-800:])
                assert not stray,(case,'processes of the worker session were still running',stray)
                assert wait_for(lambda:not any(alive(x)for x in natives),30),(case,'a native worker survived')
                assert wait_for(lambda:not own.survivors(),30),(case,'processes of the case survived the worker (production runs in their own sessions?)',own.survivors())
            assert not own.killed,(case,own.killed)
            assert not list(scr.iterdir()),(case,[x.name for x in scr.rglob('*')][:10])
            assert 'stopping on signal 15: SIGTERM forwarded to 2 lane(s)'in so and 'lane exit codes [143, 143]'in so,(case,so[-800:])
            assert len(list((d/'lanes/claims').glob('*.json')))==2 and not list((d/'lanes').glob('failures/*.json')),case
            logs=sorted((d/'lanes/logs').glob('idx*.6500.*.log'));assert len(logs)==2,logs
            if case=='forwarded':
                assert all('stopped by signal 15'in x.read_text()and '"status": "signal 15"'in x.read_text()for x in logs),[x.read_text()[-300:]for x in logs]
            else:assert 'killed after 3.2 s'in so,(so[-800:])
            # the same job id again (a requeued job): its own stale claims are released and the campaign completes
            cp=tool(E.pkg,'lanes.py','worker',d,env={'SLURM_JOB_ID':'6500','C8_LANE_SECONDS':'36000','C8_LANES':'2','TMPDIR':str(scr)})
            assert cp.stdout.count('released own stale claim')==2 and tool(E.pkg,'production.py','status',d).returncode==0,(case,cp.stdout[-600:])
            assert not list(scr.iterdir())
            out[case]=round(took,2)
    ok('lane_worker_sigterm_forwarded_runtime_removed_claims_stale_F7',stop_seconds=out)

def test_cpu_vendor(E):
    """F5: the first claim pins the campaign's CPU vendor in cpu_vendor.json (with family, model name and the claim) and
    records its CPU in every checkpoint; status reports the pin. A claim on another vendor (the pin rewritten) stops
    before any block with exit 64 and a message naming both vendors; a lane worker refuses (64) before any claim; a lane
    whose run is refused releases the claim, writes no failure record and stops with 64. env.sh.example no longer
    advises a mixed AMD/Intel partition list, and docs/HPC.md no longer says that nothing depends on the node."""
    p=E.M.prod;L=E.M.lanes;me=E.M.common.read_cpu_identity();other='GenuineIntel'if me['vendor']!='GenuineIntel'else'AuthenticAMD'
    d=E.td/'vendor';lanes_plan(E,d,seed=SEED+71);m=manifest(d);pin=d/'cpu_vendor.json'
    assert not pin.exists();E.run(d,0);doc=json.loads(pin.read_text())
    assert doc['schema']=='c8-d2-cpu-vendor-1'and doc['vendor']==me['vendor']and doc['first_claim']['index']==0 and doc['model_name']==me['model_name'],doc
    ck=next((d/'groups'/m['jobs'][0]['group']/'checkpoints').glob('*.json'));assert json.loads(ck.read_text())['runtime']['cpu']['vendor']==me['vendor']
    st=cli(p,'status',d,expect=None);assert f'cpu vendor: {me["vendor"]}'in st.stdout and 'pinned by the first claim'in st.stdout,st.stdout[-500:]
    E.run(d,1);assert json.loads(pin.read_text())==doc  # a later claim on the same vendor reads the pin and runs
    replace_bytes(pin,json.dumps({**doc,'vendor':other,'model_name':'Other CPU'}).encode())
    j=m['jobs'][2];before={f.name for f in (d/'groups'/j['group']/'checkpoints').glob('*.json')}if (d/'groups'/j['group']/'checkpoints').exists()else set()
    r=E.run(d,2,expect=1);assert r.returncode==64 and 'Native rows differ between CPU vendors'in r.stderr and other in r.stderr and me['vendor']in r.stderr,(r.returncode,r.stderr[-500:])
    assert {f.name for f in (d/'groups'/j['group']/'checkpoints').glob('*.json')}==before and '"status": "cpu vendor refused"'in r.stdout
    tool(E.pkg,'lanes.py','queue',d)
    ncpu=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else(os.cpu_count()or 1)
    cp=tool(E.pkg,'lanes.py','worker',d,env={'SLURM_JOB_ID':'6600','C8_LANE_SECONDS':'36000','C8_LANES':str(max(1,-(-ncpu//8)))},check=False)
    assert cp.returncode==64 and 'CPU vendor'in cp.stderr and not list((d/'lanes/claims').glob('*.json')),(cp.returncode,cp.stderr[-400:])
    args=NS(directory=d,lane=0,cpus='0,1',deadline='inf',job='6601',restart='0',stop_seconds=None)
    out=io.StringIO()
    with keep_affinity(),contextlib.redirect_stdout(out),mock.patch.dict(os.environ,{'C8_INPUTS':str(E.fixture)}):rc=L.cmd_lane(args)
    assert rc==64 and 'refused'in out.getvalue()and 'claim released'in out.getvalue(),(rc,out.getvalue()[-400:])
    assert not list((d/'lanes/claims').glob('*.json'))and not list((d/'lanes').glob('failures/*.json'))
    ex=(E.pkg/'slurm/env.sh.example').read_text();hpc=(ROOT/'docs/HPC.md').read_text()
    assert 'amdq,defq'not in ex and 'Nothing depends on the node'not in hpc and 'CPU vendor'in hpc
    ok('cpu_vendor_pinned_by_first_claim_refused_elsewhere_F5',vendor=me['vendor'])

def test_lane_submission(E):
    """A-ORC-10 and lane-mode submission on fake Slurm: workers + one afterany merge on all live workers; repeated
    `lanes N` cancels the superseded PENDING merge only after the new merge is accepted; a RUNNING merge is never
    cancelled; `lanes 0` submits only a merge on the live workers; memory options; mixed-mode refusal."""
    p=E.M.prod;d=E.td/'lsub';lanes_plan(E,d,seed=SEED+31);tag=p.campaign_tag(d);S=Slurm(E,'lsub',C8_RUN=str(d),FAKE_REGISTER='1');S.queue()
    cp,c1=S.call('submit.sh',['--lanes','2']);assert cp.returncode==0,cp.stderr[-600:]
    lw=[c for c in c1 if c['script']=='lane_worker.sh'];mg=[c for c in c1 if c['script']=='merge.sh']
    assert len(lw)==2 and len(mg)==1 and all(last(c['args'],'--comment')==f'{tag}:lane'and '--exclusive'in c['args']and last(c['args'],'--mem')=='180G'and last(c['args'],'--job-name')=='c8d2-lanes'
                                             and last(c['args'],'--time')=='24:00:00'and c['env']['C8_INDEX_OFFSET']is None for c in lw)
    m1=mg[0]['jobid'];assert last(mg[0]['args'],'--dependency')==f'afterany:{lw[0]["jobid"]}:{lw[1]["jobid"]}'and last(mg[0]['args'],'--mem')=='64G'and last(mg[0]['args'],'--time')=='02:00:00'
    cp,c2=S.call('submit.sh',['--lanes','1']);assert cp.returncode==0,cp.stderr[-600:]
    lw2=[c for c in c2 if c['script']=='lane_worker.sh'];mg2=[c for c in c2 if c['script']=='merge.sh']
    assert len(lw2)==1 and len(mg2)==1 and last(mg2[0]['args'],'--dependency')=='afterany:'+':'.join(sorted([lw[0]['jobid'],lw[1]['jobid']])+[lw2[0]['jobid']])
    log=S.log();i_merge=next(i for i,x in enumerate(log)if x['cmd']=='scancel');sb=[json.loads(l)for l in (S.td/'sbatch.log').read_text().splitlines()]
    assert [x['args']for x in log if x['cmd']=='scancel']==[['--state=PENDING',m1]],'the superseded pending merge is cancelled, by the scheduler only while pending'
    assert [x['args']for x in log if x['cmd']=='scontrol'and x['args'][0]=='hold']==[['hold',m1]]  # held first (O08)
    q=[json.loads(l)for l in (S.td/'queue.jsonl').read_text().splitlines()];pend=[r for r in q if r['comment']==f'{tag}:merge'and r['state']=='PENDING']
    assert [r['jobid']for r in pend]==[mg2[0]['jobid']],pend  # exactly one pending merge, on all three workers
    led=[json.loads(l)for l in (d/'submissions.jsonl').read_text().splitlines()];assert any(x.get('type')=='note'and x['jobid']==m1 for x in led)
    # a RUNNING merge is never cancelled
    for r in q:
        if r['jobid']==mg2[0]['jobid']:r['state']='RUNNING'
    S.queue(*q);n_cancel=sum(1 for x in S.log()if x['cmd']=='scancel')
    cp,c3=S.call('submit.sh',['--lanes','0']);assert cp.returncode==0 and [c['script']for c in c3]==['merge.sh'],cp.stderr[-400:]
    assert sum(1 for x in S.log()if x['cmd']=='scancel')==n_cancel and 'left alone'in cp.stdout
    assert last(c3[0]['args'],'--dependency')=='afterany:'+':'.join(sorted([lw[0]['jobid'],lw[1]['jobid'],lw2[0]['jobid']]))
    # memory: C8_LANE_MEM and C8_MERGE_MEM; a --mem in the options is refused for lanes (option-name parsing)
    cp,c4=S.call('submit.sh',['--lanes','1'],C8_LANE_MEM='245G',C8_MERGE_MEM='32G');assert cp.returncode==0
    assert last([c for c in c4 if c['script']=='lane_worker.sh'][0]['args'],'--mem')=='245G'and last([c for c in c4 if c['script']=='merge.sh'][0]['args'],'--mem')=='32G'
    for bad in ({'C8_SBATCH_ARGS':'-A acct -p part --mem=10G'},{'C8_SBATCH_ARGS':'-A acct -p part --mem-per-cpu=1G'}):
        cp,c5=S.call('submit.sh',['--lanes','1'],**bad);assert cp.returncode==64 and not c5 and 'C8_LANE_MEM'in cp.stderr
    cp,c5=S.call('submit.sh',['--lanes','1','--mem','10G']);assert cp.returncode==64 and not c5
    cp,c5=S.call('submit.sh',['--lanes','1'],C8_SBATCH_ARGS='-A acct -p part --job-name --mem=10G');assert cp.returncode==0 and c5  # '--mem=10G' is the VALUE of --job-name (C7I-17)
    assert last([c for c in c5 if c['script']=='lane_worker.sh'][0]['args'],'--job-name')=='c8d2-lanes'  # the tool's name is last
    # mixed mode: live array elements refuse lanes (65)
    S.add(Q(f'{tag}:off=0','0','RUNNING','990_0'));cp,c6=S.call('submit.sh',['--lanes','1']);assert cp.returncode==65 and not c6
    # a plan without estimates (bootstrap) is refused (64)
    db=E.td/'lsub_boot';E.small(db,seed=SEED+32);cp,c7=S.call('submit.sh',['--lanes','1'],C8_RUN=str(db));assert cp.returncode==64 and not c7
    # the stale-claim snapshot uses the uid-derived scheduler name: a stale USER/LOGNAME still sees the live owner's jobs
    n0=sum(1 for x in S.log()if x['cmd']=='squeue')
    cp=subprocess.run([PY,'-B',str(E.pkg/'tools/lanes.py'),'release-stale',str(d),'--dry-run'],capture_output=True,text=True,env={**S.base,'USER':FOREIGN,'LOGNAME':FOREIGN})
    assert cp.returncode==0,cp.stderr[-300:]
    q=[x for x in S.log()if x['cmd']=='squeue'][n0:];assert q and all(x['args'][x['args'].index('-u')+1]==REAL_USER for x in q),q
    ok('lane_submission_merge_replacement_running_merge_lanes0_memory_mixed_mode_uid_snapshot',merges=[m1,mg2[0]['jobid']])

def test_drill_mode(E):
    """Lane drill mode (C8_LANE_DRILL=1, test-only plans on a shared partition): no --exclusive; -c, --mem from
    C8_LANE_CPUS/C8_LANE_MEM; --no-requeue; the merge's -c and --mem from C8_MERGE_JOBS/C8_MERGE_MEM; refusals (64)."""
    p=E.M.prod;d=E.td/'drill';lanes_plan(E,d,seed=SEED+41);S=Slurm(E,'drill',C8_RUN=str(d),C8_SBATCH_ARGS='-p sharedq',C8_LANE_DRILL='1',C8_LANE_CPUS='2',
                                                                        C8_LANE_MEM='3G',C8_MERGE_JOBS='2',C8_MERGE_MEM='3G');S.queue()
    cp,c=S.call('submit.sh',['--lanes','1']);assert cp.returncode==0,cp.stderr[-500:]
    lw=[x for x in c if x['script']=='lane_worker.sh'][0]['args'];mg=[x for x in c if x['script']=='merge.sh'][0]['args']
    assert '--exclusive'not in lw and last(lw,'--cpus-per-task')=='2'and last(lw,'--mem')=='3G'and '--no-requeue'in lw and last(lw,'--nodes')=='1'
    assert last(mg,'--cpus-per-task')=='2'and last(mg,'--mem')=='3G'and '--no-requeue'in mg
    # CK-K01/O05: the EFFECTIVE options count, the submitted script's #SBATCH directives included (an option left off the
    # command line does not cancel a directive): no --exclusive anywhere for a drill worker or its merge
    import shlex
    def directives(script):
        out=[]
        for line in (E.pkg/'slurm'/script).read_text().splitlines():
            if line.startswith('#SBATCH'):out+=shlex.split(line[len('#SBATCH'):])
            elif line.strip()and not line.startswith('#'):break
        return out
    excl=lambda toks:[t for t in toks if t=='--exclusive'or t.startswith('--exclusive=')]
    assert not excl(directives('lane_worker.sh')+lw)and not excl(directives('merge.sh')+mg),(directives('lane_worker.sh'),lw)
    # the submitter reads the directives: a script that carries one refuses the drill (64) before any sbatch
    lwsh=E.pkg/'slurm/lane_worker.sh';orig=lwsh.read_bytes()
    try:
        replace_bytes(lwsh,orig.replace(b'#SBATCH --nodes=1\n',b'#SBATCH --nodes=1\n#SBATCH --exclusive\n',1));lwsh.chmod(0o755)
        cp,c=S.call('submit.sh',['--lanes','1']);assert cp.returncode==64 and not c and 'exclusive'in cp.stderr and 'directive'in cp.stderr,(cp.returncode,cp.stderr[-400:])
    finally:replace_bytes(lwsh,orig);lwsh.chmod(0o755)
    # the precedence the submitter uses (sbatch's): directives < SBATCH_* inputs < command line; a set flag stays set
    scr=E.td/'eff_probe.sh';scr.write_text('#!/bin/bash\n#SBATCH --mem=180G\n#SBATCH --exclusive\n#SBATCH -p dirq\n\necho x\n#SBATCH --qos=late\n')
    eff=E.M.ss.effective_options(['--mem=3G','--no-requeue',str(scr)],{'SBATCH_PARTITION':'envq'})
    assert eff['mem']=='3G'and eff['exclusive']is True and eff['partition']=='envq'and eff['no-requeue']is True and 'qos'not in eff,eff
    assert E.M.ss.effective_options(['-p','cliq',str(scr)],{'SBATCH_PARTITION':'envq'})['partition']=='cliq'
    for bad in ({'C8_LANE_MEM':'5G'},{'C8_LANE_CPUS':'9'},{'C8_LANE_CPUS':'1'},{'C8_MERGE_JOBS':'9'},{'C8_MERGE_MEM':'5G'},{'C8_SBATCH_ARGS':'-p sharedq --exclusive'}):
        cp,c=S.call('submit.sh',['--lanes','1'],**bad);assert cp.returncode==64 and not c,(bad,cp.stderr[-300:])
    nt=E.td/'drill_nontest';shutil.copytree(d,nt);mm=manifest(nt);mm['test_only']=False;(nt/'manifest.json').write_text(json.dumps(mm))
    cp,c=S.call('submit.sh',['--lanes','1'],C8_RUN=str(nt));assert cp.returncode==64 and not c and 'test-only plans only'in cp.stderr
    # the worker side: drill mode splits the job's own CPU set into C8_LANES parts
    assert [len(x)for x in E.M.lanes.cpu_lanes([10,11,12,13],'2',drill=True)]==[2,2]
    cp=tool(E.pkg,'lanes.py','worker',nt,env={'SLURM_JOB_ID':'1','C8_LANE_SECONDS':'100','C8_LANE_DRILL':'1'},check=False);assert cp.returncode==64 and 'test-only'in cp.stderr
    ok('lane_drill_mode_shapes_and_refusals_effective_options_no_exclusive_directive')

def test_admission(E):
    """A-ORC-11 (R12, H7, H7E-R) on fake squeue/sbatch: every new job counted, merges included; superseded merges;
    the site lock; the AMD-pool cap with amddebugq and multi-partition jobs; job names containing '|' counted, and an
    squeue line that does not parse refusing admission (69) instead of being skipped."""
    p=E.M.prod;d=E.td/'adm';lanes_plan(E,d,seed=SEED+51);tag=p.campaign_tag(d)
    S=Slurm(E,'adm',C8_RUN=str(d),C8_SITE='expanse',C8_SBATCH_ARGS='-A yun124 -p compute');me=REAL_USER
    def mine(n,state='PENDING',part='compute',qos='normal',name='c8d2-lanes'):return [{'jobid':str(3000+i),'name':name,'state':state,'partition':part,'qos':qos,'user':me,'account':'yun124'}for i in range(n)]
    def others(n,state='RUNNING'):return [{'jobid':str(4000+i),'name':'other','state':state,'partition':'compute','qos':'normal','user':'someone','account':'yun124'}for i in range(n)]
    win={'C8_EXP_NODES':'64','C8_ADMISSION_REF':'test: DECISIONS line of a pilot window'}
    # submitted: 25 + k = 2 admitted; 26 refused, largest N 0
    S.queue(*mine(25));cp,c=S.call('submit.sh',['--lanes','1'],**win);assert cp.returncode==0 and len(c)==2,cp.stderr[-500:]
    S.queue(*mine(26));cp,c=S.call('submit.sh',['--lanes','1'],**win);assert cp.returncode==65 and not c and 'Largest admissible N for lanes N: 0'in cp.stderr,(cp.returncode,cp.stdout[-800:],cp.stderr[-500:])
    # running: 9 + 2 admitted, 10 refused
    S.queue(*mine(9,'RUNNING'));cp,c=S.call('submit.sh',['--lanes','1'],**win);assert cp.returncode==0
    S.queue(*mine(10,'RUNNING'));cp,c=S.call('submit.sh',['--lanes','1'],**win);assert cp.returncode==65 and not c
    # the whole account at most 32 running: 30 running (others) + 2 admitted, 31 refused
    S.queue(*others(30));cp,c=S.call('submit.sh',['--lanes','1'],**win);assert cp.returncode==0
    S.queue(*others(31));cp,c=S.call('submit.sh',['--lanes','1'],**win);assert cp.returncode==65 and 'yun124 running'in cp.stderr
    # compute nodes during development (no window): 2 live + 2 admitted, 3 refused
    S.queue(*mine(2));cp,c=S.call('submit.sh',['--lanes','1']);assert cp.returncode==0
    S.queue(*mine(3));cp,c=S.call('submit.sh',['--lanes','1']);assert cp.returncode==65 and 'compute nodes'in cp.stderr and 'N for lanes N: 0'in cp.stderr
    # a superseded PENDING merge still listed counts until a snapshot shows it gone
    S.queue(*mine(2),{'jobid':'3999','name':'c8d2-merge','state':'PENDING','partition':'compute','qos':'normal','user':me,'account':'yun124','comment':f'{tag}:merge'})
    cp,c=S.call('submit.sh',['--lanes','1']);assert cp.returncode==65 and not c
    # the shared partition: at most 32 live c8d2 jobs
    S.queue(*mine(31,part='shared',qos='shared-normal'));cp,c=S.call('submit.sh',['--lanes','1'],C8_SBATCH_ARGS='-A yun124 -p shared');assert cp.returncode==65
    S.queue(*mine(30,part='shared',qos='shared-normal'));cp,c=S.call('submit.sh',['--lanes','1'],C8_SBATCH_ARGS='-A yun124 -p shared');assert cp.returncode==0
    # a cap that differs from H7E-R needs the DECISIONS reference
    cp,c=S.call('submit.sh',['--lanes','1'],C8_EXP_NODES='8');assert cp.returncode==64 and 'DECISIONS'in cp.stderr and not c
    led=[json.loads(l)for l in (d/'submissions.jsonl').read_text().splitlines()];assert any(x.get('admission_ref')for x in led)
    # the site lock serializes admission across campaigns: held -> 75; after release the second sees the first's jobs
    d2=E.td/'adm2';lanes_plan(E,d2,seed=SEED+52);S.queue()
    lock=S.td/'.c8_site_expanse.lock';lock.mkdir();(lock/'owner.json').write_text('{"pid":1}')
    cp,c=S.call('submit.sh',['--lanes','1'],C8_RUN=str(d2));assert cp.returncode==75 and not c
    shutil.rmtree(lock)
    fifo=S.td/'adm.fifo';os.mkfifo(fifo);S.queue()
    with Owned(markers=(str(S.td/'fakebin'),),fifos=(fifo,))as own:  # Z13
        first=own.add(subprocess.Popen(['bash',str(E.pkg/'slurm/submit.sh'),'--lanes','2'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                       env={**S.base,'FAKE_SBATCH_BLOCK':str(fifo),'FAKE_REGISTER':'1'},start_new_session=True))
        assert wait_for(lambda:lock.exists(),60)
        second=subprocess.run(['bash',str(E.pkg/'slurm/submit.sh'),'--lanes','1'],capture_output=True,text=True,env={**S.base,'C8_RUN':str(d2),'FAKE_REGISTER':'1'})
        assert second.returncode==75,second.stderr[-300:]
        fifo_go(fifo)
        out,err=first.communicate(timeout=120);assert first.returncode==0,err[-300:]
    assert not own.killed,own.killed
    third=subprocess.run(['bash',str(E.pkg/'slurm/submit.sh'),'--lanes','1'],capture_output=True,text=True,env={**S.base,'C8_RUN':str(d2),'FAKE_REGISTER':'1'})
    assert third.returncode==65 and '"my_compute_nodes_live": 3'in third.stdout,third.stdout[-500:]  # sees the first campaign's two workers and merge
    # symmetry: the AMD-pool cap counts amdq, amddebugq and amdpreq together, and multi-partition jobs listing one
    S2=Slurm(E,'amd',C8_RUN=str(d),C8_SITE='symmetry',C8_AMDQ_CAP='4',C8_SBATCH_ARGS='-p amdq --exclude=cn112')
    for parts in (('amdq','amdq'),('amdq','amddebugq'),('amdq','amdq,defq')):
        S2.queue(*[{'jobid':str(5000+i),'name':'c8d2-val2','state':'RUNNING','partition':pp,'user':me}for i,pp in enumerate(parts)],
                 {'jobid':'5100','name':'other-job','state':'RUNNING','partition':'amdq','user':me},{'jobid':'5101','name':'c8d2-x','state':'RUNNING','partition':'defq','user':me})
        cp,c=S2.call('submit.sh',['--lanes','1']);assert cp.returncode==0 and len(c)==2,(parts,cp.stderr[-400:])
        cp,c=S2.call('submit.sh',['--lanes','2']);assert cp.returncode==65 and not c and 'AMD-pool'in cp.stderr and 'N for lanes N: 1'in cp.stderr,(parts,cp.stderr[-400:])
    cp,c=S2.call('submit.sh',['--lanes','2'],C8_SBATCH_ARGS='-p defq');assert cp.returncode==0  # Intel defq is outside the AMD-pool cap
    ok('admission_h7er_superseded_merges_site_lock_amd_pool_cap')
    # job names may hold '|': the name is the last squeue field and the line is split at the first six '|', so such jobs
    # are counted (with a '|'-split of seven fields these lines would have been skipped, admitting --lanes 2)
    assert E.M.ss.SQUEUE_ADMISSION_FORMAT=='%i|%T|%P|%q|%D|%u|%j'
    S2.queue({'jobid':'5300','name':'c8d2-a|b','state':'RUNNING','partition':'amdq','user':me},{'jobid':'5301','name':'c8d2-|x|y|z|','state':'PENDING','partition':'amdq','user':me},
             {'jobid':'5302','name':'other|c8d2-','state':'RUNNING','partition':'amdq','user':me})
    cp,c=S2.call('submit.sh',['--lanes','2']);assert cp.returncode==65 and not c and 'N for lanes N: 1'in cp.stderr,(cp.returncode,cp.stderr[-400:])
    rec=json.loads(next(l for l in cp.stdout.splitlines()if l.startswith('C8: admission '))[len('C8: admission '):])
    assert rec['amd_live']==2 and sorted(rec['amd_live_jobs'])==['5300','5301'],rec
    recs=E.M.ss._squeue_records({**S2.base},['-u',me]);assert [r['name']for r in recs]==['c8d2-a|b','c8d2-|x|y|z|','other|c8d2-'],recs
    # a line that does not parse refuses admission (69) and nothing is submitted; it is never skipped
    for raw in ('garbage without separators','5400|RUNNING|amdq|normal|1','|RUNNING|amdq|normal|1|someone|c8d2-x'):
        S2.queue({'jobid':'5400','raw':raw},*[{'jobid':str(5500+i),'name':'c8d2-ok','state':'RUNNING','partition':'defq','user':me}for i in range(2)])
        cp,c=S2.call('submit.sh',['--lanes','1']);assert cp.returncode==69 and not c and 'does not parse'in cp.stderr and 'nothing submitted'in cp.stderr,(raw,cp.returncode,cp.stderr[-400:])
    ok('admission_squeue_job_names_with_pipes_counted_unparsable_line_refused')

def partition_of(args):
    """The last partition option of an sbatch argument list (-p X, -pX or --partition=X), else None."""
    v=None
    for i,a in enumerate(args):
        if a=='-p'and i+1<len(args):v=args[i+1]
        elif a.startswith('-p')and not a.startswith('--')and len(a)>2:v=a[2:]
        elif a.startswith('--partition='):v=a.split('=',1)[1]
    return v

def test_submission_roles(E):
    """Checkpoint review O04 on fake Slurm: every job role has its own effective options. A merge keeps the partition,
    account, QOS and exclusions of C8_SBATCH_ARGS and the extra options (a later -p wins for it as for the workers) and
    takes only memory, CPUs and time from its own settings; admission counts each role on its own partitions (here the
    AMD pool is full, and nothing lands on it) and the ledger records them."""
    p=E.M.prod;ss=E.M.ss;me=REAL_USER
    # ---- O04: C8_SBATCH_ARGS '-p amdq ...' and the extra '-p defq': workers AND merge on defq; the AMD pool is full
    d=E.td/'roles';lanes_plan(E,d,seed=SEED+71);tag=p.campaign_tag(d)
    S=Slurm(E,'roles',C8_RUN=str(d),C8_SITE='symmetry',C8_AMDQ_CAP='4',C8_SBATCH_ARGS='-p amdq --exclude=cn112 -q devel',FAKE_REGISTER='1')
    full=[{'jobid':str(7000+i),'name':'c8d2-other','state':'RUNNING','partition':'amdq','user':me}for i in range(4)]
    S.queue(*full);cp,c=S.call('submit.sh',['--lanes','1','-p','defq']);assert cp.returncode==0,cp.stderr[-600:]
    lw=[x for x in c if x['script']=='lane_worker.sh'];mg=[x for x in c if x['script']=='merge.sh']
    assert len(lw)==1 and len(mg)==1 and partition_of(lw[0]['args'])=='defq'and partition_of(mg[0]['args'])=='defq',(lw[0]['args'],mg[0]['args'])
    assert all('--exclude=cn112'in x['args']and ('-q'in x['args']and x['args'][x['args'].index('-q')+1]=='devel')for x in lw+mg),mg[0]['args']
    rec=json.loads(next(l for l in cp.stdout.splitlines()if l.startswith('C8: admission '))[len('C8: admission '):])
    assert rec['new_jobs']=={'lane':{'count':1,'partitions':['defq']},'merge':{'count':1,'partitions':['defq']}}and rec['amd_live']==4,rec
    led={x['jobid']:x for x in map(json.loads,(d/'submissions.jsonl').read_text().splitlines())}
    assert led[lw[0]['jobid']]['partition']=='defq'and led[mg[0]['jobid']]['partition']=='defq'and led[mg[0]['jobid']]['role']=='merge'
    # the merge takes memory, CPUs and time only from its own settings, whatever the extra options say (array mode)
    da=E.td/'roles_arr';E.small(da,'--shards',1,seed=SEED+72);m=manifest(da)
    Sa=Slurm(E,'roles_arr',C8_RUN=str(da),C8_SBATCH_ARGS='-A acct -p part',C8_MERGE_MEM='7G',C8_MERGE_JOBS='3',C8_MERGE_TIME='00:30:00')
    big=int(m['estimates']['mem_suggestion_mb'])+100;Sa.queue()
    cp,c=Sa.call('submit.sh',['-p','other','--mem',f'{big}M','-c','5','--time=00:07:00','-x','cn9']);assert cp.returncode==0,cp.stderr[-600:]
    mg=[x for x in c if x['script']=='merge.sh'][0]['args'];wk=[x for x in c if x['script']=='run_array.sh'][0]['args']
    assert partition_of(mg)==partition_of(wk)=='other'and '-x'in mg and mg[mg.index('-x')+1]=='cn9','the merge keeps the overrides'
    assert last(mg,'--mem')=='7G'and last(mg,'--cpus-per-task')=='3'and '-c'not in mg and '--mem'not in mg,mg  # its own resources only
    assert last(mg,'--time')=='00:07:00'and sum(a.startswith('--time')for a in mg)==1,mg  # a user --time applies to every job, once
    assert last(wk,'--mem')is None and wk[wk.index('--mem')+1]==f'{big}M'and wk[wk.index('-c')+1]=='5'  # the workers keep the user's
    # admission counts each role on its own partitions: a merge that would land on the full AMD pool refuses even
    # when the workers do not (white-box: the per-role options of the submission are made to differ)
    S.queue(*full)
    cx=ss.Context({**S.base,'C8_RUN':str(d),'C8_SITE':'symmetry','C8_AMDQ_CAP':'4','C8_SBATCH_ARGS':'-p defq'},[])
    with mock.patch.object(cx,'partitions',side_effect=lambda role='array':['amdq']if role=='merge'else['defq']):
        try:ss.admission(cx,[('lane',1),('merge',1)],'lanes');raise AssertionError('admitted a merge on a full AMD pool')
        except ss.Refuse as r:assert r.code==65 and 'AMD-pool'in str(r)and 'N for lanes N: -1'in str(r),str(r)
        assert ss.admission(cx,[('array',3)],'jobs')['room']is None  # no new job on the AMD pool: no AMD limit applies
    ok('submission_roles_merge_keeps_overrides_admission_and_ledger_per_role_O04')

def test_unverified_stop(E):
    """Checkpoint review O07 on fake Slurm: under C8_TIME_POLICY=unlimited a worker accepted without TimeLimit=UNLIMITED
    stops the submission at once (no merge that would not wait for it, no cancellation), the message names every
    accepted job, and `--lanes 0` then submits a merge on every live worker, the unverified one included; an unverified
    merge stops the cancellation of the superseded one."""
    p=E.M.prod
    # ---- O07: the second worker is accepted without TimeLimit=UNLIMITED: stop at once
    d7=E.td/'unverified';lanes_plan(E,d7,seed=SEED+73);t7=p.campaign_tag(d7)
    S7=Slurm(E,'unverified',C8_RUN=str(d7),FAKE_REGISTER='1',C8_TIME_POLICY='unlimited')
    S7.queue(Q(f'{t7}:lane','N/A','RUNNING','650',name='c8d2-lanes'),Q(f'{t7}:merge','N/A','PENDING','651',name='c8d2-merge'))
    cp,c=S7.call('submit.sh',['--lanes','3'],FAKE_TIMELIMIT_JOBS='702')
    assert cp.returncode==70 and [x['script']for x in c]==['lane_worker.sh','lane_worker.sh']and [x['jobid']for x in c]==['701','702'],(cp.returncode,[x['script']for x in c],cp.stderr[-600:])
    assert '701'in cp.stderr and '702'in cp.stderr and '--lanes 0'in cp.stderr and 'no merge was submitted'in cp.stderr,cp.stderr[-600:]
    assert not [x for x in S7.log()if x['cmd']=='scancel'or (x['cmd']=='scontrol'and x['args'][0]in('hold','release'))],'nothing cancelled after O07'
    led=[json.loads(l)for l in (d7/'submissions.jsonl').read_text().splitlines()];assert [(x['jobid'],x['role'])for x in led]==[('701','lane'),('702','lane')]
    cp,c=S7.call('submit.sh',['--lanes','0']);assert cp.returncode==0 and [x['script']for x in c]==['merge.sh'],cp.stderr[-400:]
    assert last(c[0]['args'],'--dependency')=='afterany:650:701:702','the recovery merge waits on every live worker, the unverified one included'
    # an unverified merge: stopped, the superseded merge is not touched, and the message says the merge was accepted
    S7.queue(Q(f'{t7}:lane','N/A','RUNNING','650',name='c8d2-lanes'),Q(f'{t7}:merge','N/A','PENDING','651',name='c8d2-merge'))
    n0=len(S7.log());cp,c=S7.call('submit.sh',['--lanes','1'],FAKE_TIMELIMIT_JOBS='705')
    assert cp.returncode==70 and [x['script']for x in c]==['lane_worker.sh','merge.sh']and 'merge 705 was accepted'in cp.stderr,(cp.returncode,cp.stderr[-500:])
    assert not [x for x in S7.log()[n0:]if x['cmd']=='scancel'or (x['cmd']=='scontrol'and x['args'][0]=='hold')]
    ok('unverified_job_stops_the_submission_recovery_waits_on_every_live_worker_O07')

def test_conditional_cancel(E):
    """Checkpoint review O08 on fake Slurm: a superseded merge that starts between the snapshot and the cancellation step
    is left alone (scontrol hold refuses a started job; scancel only with --state=PENDING), a scheduler that accepts the
    hold of a started job gets it released, and a still-pending one is held and cancelled; each outcome is recorded."""
    p=E.M.prod
    # ---- O08: the superseded merge starts while the new merge is submitted: left alone, outcome recorded
    d8=E.td/'race';lanes_plan(E,d8,seed=SEED+74);t8=p.campaign_tag(d8);S8=Slurm(E,'race',C8_RUN=str(d8),FAKE_REGISTER='1')
    S8.queue(Q(f'{t8}:lane','N/A','RUNNING','660',name='c8d2-lanes'),Q(f'{t8}:merge','N/A','PENDING','661',name='c8d2-merge'))
    cp,c=S8.call('submit.sh',['--lanes','1'],FAKE_SBATCH_RUN_ON_MERGE='661');assert cp.returncode==0,cp.stderr[-500:]
    q8={r['jobid']:r for r in map(json.loads,(S8.td/'queue.jsonl').read_text().splitlines())}
    assert q8['661']['state']=='RUNNING','a merge that started after the snapshot was cancelled'
    assert not [x for x in S8.log()if x['cmd']=='scancel'],'scancel ran on a started merge'
    note=[x for x in map(json.loads,(d8/'submissions.jsonl').read_text().splitlines())if x.get('type')=='note'and x['jobid']=='661']
    assert note and note[0]['cancel']['cancelled']is False and 'left alone'in note[0]['note']and 'left alone'in cp.stdout,(note,cp.stdout[-400:])
    # a scheduler that accepts the hold of a started job: the state is read again, the hold released, nothing cancelled
    S8.queue(Q(f'{t8}:lane','N/A','RUNNING','660',name='c8d2-lanes'),Q(f'{t8}:merge','N/A','PENDING','662',name='c8d2-merge'))
    cp,c=S8.call('submit.sh',['--lanes','0'],FAKE_SBATCH_RUN_ON_MERGE='662',FAKE_HOLD_ACCEPTS_STARTED='1');assert cp.returncode==0,cp.stderr[-400:]
    q8={r['jobid']:r for r in map(json.loads,(S8.td/'queue.jsonl').read_text().splitlines())}
    assert q8['662']['state']=='RUNNING'and q8['662'].get('held')is False and not [x for x in S8.log()if x['cmd']=='scancel']
    assert [x['args']for x in S8.log()if x['cmd']=='scontrol'and x['args'][0]=='release']==[['release','662']]
    # still PENDING at the cancellation step: held, then cancelled by the scheduler's state filter, recorded as cancelled
    S8.queue(Q(f'{t8}:lane','N/A','RUNNING','660',name='c8d2-lanes'),Q(f'{t8}:merge','N/A','PENDING','663',name='c8d2-merge'))
    cp,c=S8.call('submit.sh',['--lanes','0']);assert cp.returncode==0
    q8={r['jobid']:r for r in map(json.loads,(S8.td/'queue.jsonl').read_text().splitlines())}
    note=[x for x in map(json.loads,(d8/'submissions.jsonl').read_text().splitlines())if x.get('type')=='note'and x['jobid']=='663']
    assert q8['663']['state']=='CANCELLED'and note and note[0]['cancel']['cancelled']is True and note[0]['cancel']['held']is True,(q8['663'],note)
    ok('superseded_merge_cancelled_only_while_pending_by_the_scheduler_O08')

def test_ledger_accounting(E):
    """A-ORC-9: ledger registration exactly once (twice or after a requeue adds no job record), allocated core-hours
    over every sacct -X --duplicates attempt in physical cores, an unknown allocation refused, local work reported."""
    p=E.M.prod;d=E.td/'acct';E.small(d,'--shards',1,seed=SEED+61);m=manifest(d)
    for j in m['jobs']:
        with mock.patch.dict(os.environ,{'SLURM_JOB_ID':'801','SLURM_RESTART_COUNT':'0'}):E.run(d,j['id'])
    reg=lambda *a,**env:tool(E.pkg,'ledger.py','register',d,'--role','sweep',*a,env=env)
    assert json.loads(reg(SLURM_JOB_ID='801',SLURM_RESTART_COUNT='0').stdout)['state']=='added'
    assert json.loads(reg(SLURM_JOB_ID='801',SLURM_RESTART_COUNT='0').stdout)['state']=='present'
    assert json.loads(reg(SLURM_JOB_ID='801',SLURM_RESTART_COUNT='1').stdout)['state']=='attempt'
    jobs=E.M.ledger.jobs(d);assert list(jobs)==['801']and len(E.M.ledger.read(d))==2
    with (d/'submissions.jsonl').open('a')as f:
        for jid,role in (('802','array'),('806','merge'),('807','plan')):f.write(json.dumps({'schema':'c8-d2-ledger-1','jobid':jid,'role':role,'source':'slurm_submit'})+'\n')
    S=Slurm(E,'acct');(S.td/'sacct.txt').write_text('\n'.join(['801|801|3600|64|cn083|REQUEUED|amdq','801|801|1800|64|cn083|COMPLETED|amdq',
        '805|802_0|100|8|cn001|COMPLETED|defq','806|802_1|50|8|cn[001-002]|FAILED|defq','808|806|600|24|cn090|COMPLETED|amdq','809|807|60|8|exp-1-01|COMPLETED|shared'])+'\n')
    env={**S.base,'FAKE_TPC':json.dumps({'cn001':2})}
    with mock.patch.dict(os.environ,env):r=E.M.acc.account(d)
    hand={'sweep':(3600+1800)*64,'array':100*4+50*4,'merge':600*24,'plan':60*8}
    assert {k:round(v*3600,6)for k,v in r['core_hours_by_role'].items()}=={k:float(v)for k,v in hand.items()},r['core_hours_by_role']
    assert math.isclose(r['work_core_hours']*3600,hand['sweep']+hand['array'])and math.isclose(r['overhead_core_hours']*3600,hand['merge']+hand['plan'])
    busy=sum(float(json.loads(f.read_text())['native']['integration_seconds'])*int(json.loads(f.read_text())['native']['threads'])for f in d.rglob('checkpoints/*.json'))
    assert math.isclose(r['eta_node'],busy/(hand['sweep']+hand['array']),rel_tol=1e-9)and r['unaccounted_local_checkpoints']==0
    # O06: incomplete accounting fails closed: eta_node unavailable (null) and design.py refuses, never a value computed
    # from the records that came back. (a) a ledger job without any sacct record, (b) an sacct line that does not parse,
    # (c) an array element without a record, (d) fewer records than the attempts its checkpoints show (a requeued job
    # whose earlier, failed allocation sacct did not return), each against its complete counterpart.
    sacct0=(S.td/'sacct.txt').read_text();led0=(d/'submissions.jsonl').read_text()
    def acc(sacct_extra=(),ledger_extra=(),run=d):
        (S.td/'sacct.txt').write_text(sacct0+''.join(l+'\n'for l in sacct_extra))
        (run/'submissions.jsonl').write_text((led0 if run==d else'')+''.join(json.dumps({'schema':'c8-d2-ledger-1','source':'slurm_submit',**x})+'\n'for x in ledger_extra))
        with mock.patch.dict(os.environ,env):return E.M.acc.account(run)
    def refused_by_design(run=d):
        with mock.patch.dict(os.environ,env):
            try:E.M.des.eta_node(run,True,None);return False
            except ValueError as e:return 'eta_node unavailable'in str(e)
    r=acc(ledger_extra=[{'jobid':'810','role':'lane'}]);assert refused_by_design(),'design.py accepted incomplete accounting'
    assert r['complete']is False and r['eta_node']is None and any('job 810: 0 sacct record'in x for x in r['incomplete']),r['incomplete']
    r=acc(['810|810|100|8|cn2|COMPLETED|defq'],[{'jobid':'810','role':'lane'}]);assert r['complete'],r['incomplete']
    r0=acc();assert r0['complete']is True and r0['incomplete']==[]and r0['hours_are']=='exact'and r0['eta_node']is not None,r0['incomplete']
    # W10's class (Stage-6 fix round 4, integration): the busy time of a group that is not merged is counted only from checkpoints
    # production.validate_checkpoint accepts, as the merges and calibrate.measure validate them: one whose integration_seconds
    # was changed without its checksum, and one copied from another campaign, make the accounting incomplete and design.py
    # refuses (before: eta_node from the changed time); restored, it is complete again with the same eta_node
    f0=sorted(d.rglob('checkpoints/*.json'))[0];raw=f0.read_bytes();x=json.loads(raw);x['native']['integration_seconds']=float(x['native']['integration_seconds'])*1000+1
    try:
        f0.write_text(json.dumps(x));r=acc()
        assert r['complete']is False and r['eta_node']is None and any('not a valid checkpoint'in w and f0.name in w and 'W10'in w for w in r['incomplete'])and refused_by_design(),r['incomplete']
        dx=E.td/'acct_foreign';E.small(dx,'--shards',1,seed=SEED+65);jx=manifest(dx)['jobs'][0];E.run(dx,jx['id'])
        fx=sorted((dx/'groups'/jx['group']/'checkpoints').glob('*.json'))[0];f0.write_bytes(fx.read_bytes());r=acc()
        assert r['complete']is False and any('not a valid checkpoint'in w for w in r['incomplete']),r['incomplete']
    finally:f0.write_bytes(raw)
    assert acc()['eta_node']==r0['eta_node']
    r=acc(['810|810|1x0|8|cn2|COMPLETED|defq'],[{'jobid':'810','role':'lane'}])
    assert r['complete']is False and r['malformed_sacct_lines']and any('do not parse'in x for x in r['incomplete'])and refused_by_design(),r['incomplete']
    r=acc(['810|810|100|8|cn2|COMPLETED|defq|extra'],[{'jobid':'810','role':'lane'}]);assert r['complete']is False  # 8 fields
    r=acc(ledger_extra=[{'jobid':'815','role':'array','array':'0-2','elements':3}],sacct_extra=['816|815_0|10|8|cn3|COMPLETED|defq','817|815_1|10|8|cn3|COMPLETED|defq'])
    assert r['complete']is False and any('array job 815 element 2'in x for x in r['incomplete'])and refused_by_design(),r['incomplete']
    r=acc(ledger_extra=[{'jobid':'815','role':'array','array':'0-2','elements':3}],
          sacct_extra=['816|815_0|10|8|cn3|COMPLETED|defq','817|815_1|10|8|cn3|COMPLETED|defq','815|815_[2]|0|0|None assigned|CANCELLED by 1|defq'])
    assert r['complete'],r['incomplete']  # a never-started element is covered by its range record, at zero time
    d4=E.td/'acct4';E.small(d4,'--shards',1,seed=SEED+64)
    for j in manifest(d4)['jobs']:
        with mock.patch.dict(os.environ,{'SLURM_JOB_ID':'812','SLURM_RESTART_COUNT':'1'}):E.run(d4,j['id'])
    r=acc(['812|812|900|8|cn4|COMPLETED|defq'],[{'jobid':'812','role':'lane'}],run=d4)
    assert r['complete']is False and r['eta_node']is None and any('job 812: 1 sacct record(s), 2 attempt(s)'in x for x in r['incomplete'])and refused_by_design(d4),r['incomplete']
    r=acc(['812|812|300|8|cn4|NODE_FAIL|defq','812|812|900|8|cn4|COMPLETED|defq'],[{'jobid':'812','role':'lane'}],run=d4)
    assert r['complete']and r['eta_node']is not None and not refused_by_design(d4),r['incomplete']
    cp=tool(E.pkg,'accounting.py',d4,env=env,check=False)  # the CLI on complete accounting: exit 0
    assert cp.returncode==0,cp.stderr[-300:]
    acc(['812|812|900|8|cn4|COMPLETED|defq'],[{'jobid':'812','role':'lane'}],run=d4)
    cp=tool(E.pkg,'accounting.py',d4,env=env,check=False);assert cp.returncode==4 and 'eta_node unavailable'in cp.stderr,(cp.returncode,cp.stderr[-300:])
    (S.td/'sacct.txt').write_text(sacct0);(d/'submissions.jsonl').write_text(led0)
    # an unknown allocation: a checkpoint names a job id that is not in the ledger
    d2=E.td/'acct2';E.small(d2,'--shards',1,seed=SEED+62)
    with mock.patch.dict(os.environ,{'SLURM_JOB_ID':'990'}):E.run(d2,0)
    with mock.patch.dict(os.environ,env):
        try:E.M.acc.account(d2);raise AssertionError('accepted')
        except E.M.acc.AllocationUnknown as e:assert 'allocation unknown'in str(e)and '990'in str(e)
    cp=tool(E.pkg,'accounting.py',d2,env=env,check=False);assert cp.returncode==3 and 'allocation unknown'in cp.stderr
    d3=E.td/'acct3';E.small(d3,'--shards',1,seed=SEED+63);E.run(d3,0)
    with mock.patch.dict(os.environ,env):r3=E.M.acc.account(d3)
    assert r3['unaccounted_local_checkpoints']>=1 and r3['eta_node']is None
    ok('ledger_register_once_accounting_attempts_physical_cores_unknown_allocation_incomplete_fails_closed',core_hours=r['allocated_core_hours'])


# ================================================================ frozen rate maps (A-FLAG-6 provenance, R04)
def rates_doc(E,a='.75',b='.85',inv=None):
    inv=inv or json.loads((E.fixture/'inventory.json').read_text())
    tab=lambda v:{s:{str(L):{str(r['id']):v for r in inv[s][str(L)]}for L in range(3,9)}for s in('free','power')}
    return {'schema':'c8-d2-rates-1','inputs_manifest_sha256':digest(E.fixture/'manifest.json'),'rates':{'a':tab(a),'b':tab(b)}}

def test_rates(E):
    p=E.M.prod;base=rates_doc(E);rf=E.td/'rates_src.json';rf.write_text(json.dumps(base));ident=digest(rf);appr=('--approved-numerics-change','user approval 2026-10-03 (test)')
    def plan_r(d,f,*extra,expect=0):return E.small(d,'--rates',f,*appr,*extra,expect=expect)
    d=E.td/'rates_noappr';r=E.small(d,'--rates',rf,expect=1);assert '--approved-numerics-change'in r.stderr and gone(d)
    g0=next(iter(base['rates']['a']['free']['8']))
    bad={'missing':lambda x:x['rates']['b']['power']['3'].pop(next(iter(x['rates']['b']['power']['3']))),'unknown':lambda x:x['rates']['a']['free']['3'].__setitem__('99999999','.7'),
         'range':lambda x:x['rates']['a']['free']['8'].__setitem__(g0,'1.5'),'notdecimal':lambda x:x['rates']['a']['free']['8'].__setitem__(g0,'abc'),
         'number':lambda x:x['rates']['a']['free']['8'].__setitem__(g0,0.7),'equal':lambda x:x['rates']['a']['free']['8'].__setitem__(g0,'.85'),
         'schema':lambda x:x.__setitem__('schema','c8-d2-rates-0'),'inputs':lambda x:x.__setitem__('inputs_manifest_sha256','0'*64)}
    for name,edit in bad.items():
        x=json.loads(json.dumps(base));edit(x);f=E.td/f'rates_bad_{name}.json';f.write_text(json.dumps(x));d=E.td/f'rates_{name}'
        r=plan_r(d,f,expect=1);assert 'rate map'in r.stderr and gone(d),(name,r.stderr[-300:])
    d=E.td/'rates_ok';plan_r(d,rf,'--shards',1);m=manifest(d)
    assert m['rates_identity']==ident==digest(d/'rates.json')and all(config(d,g['name'])['rates_identity']==ident and config(d,g['name'])['rate']=='file'for g in m['groups'])
    assert m['allocation']['source']=='pilot'and m['allocation']['points']==8 and ident in m['allocation']['label']
    rf.write_text(json.dumps(rates_doc(E,'.5','.6')))  # editing the source FILE after planning changes nothing
    E.run_all(d);cps=list(d.rglob('checkpoints/*.json'));assert cps
    for f in cps:
        x=json.loads(f.read_text());c=json.loads((f.parent.parent/'config.json').read_text());tab=base['rates'][c['campaign']][c['sector']][str(c['L'])]
        assert x['runtime']['rates_identity']==ident and x['native']['rate']=='file'and all(r['rate']==tab[str(r['graph'])]for r in x['native']['rows'])
    cli(p,'merge',d);cli(E.M.asm,d,'--bootstrap',16);res=json.loads((d/'C8_test_result.json').read_text());assert res['rates_identity']==ident
    # editing the campaign's rates.json: run, status, merge and assemble refuse
    orig=(d/'rates.json').read_bytes();(d/'rates.json').write_bytes(orig.replace(b'.75',b'.74',1))
    try:
        for mod,args in ((p,('run',d,'--index',0)),(p,('status',d)),(p,('merge',d,'--group','a_free_L3')),(E.M.asm,(d,'--bootstrap',0,'--output',E.td/'r.json'))):
            if args[0]=='merge':(d/'groups/a_free_L3/merged.json').unlink(missing_ok=True)
            r=cli(mod,*args,expect=1);assert 'rates.json'in r.stderr or 'Checksum mismatch'in r.stderr,(args,r.stderr[-300:])
    finally:(d/'rates.json').write_bytes(orig)
    cli(p,'merge',d)
    # a staged private copy that differs from the identity is refused before the native starts
    real=shutil.copyfile;log=E.td/'rates_native.log'
    def tamper(src,dst,*a,**k):
        out=real(src,dst,*a,**k)
        if Path(dst).name=='rates.json':Path(dst).write_bytes(Path(dst).read_bytes().replace(b'.75',b'.73',1))
        return out
    j=manifest(d)['jobs'][0];ck=sorted((d/'groups'/j['group']/'checkpoints').glob('*.json'))[0];saved=ck.read_bytes();ck.unlink()
    with mock.patch.object(shutil,'copyfile',side_effect=tamper),mock.patch.dict(os.environ,{'C8_FAKE_LOG':str(log)}):
        r=E.run(d,j['id'],expect=1)
    assert 'staged copy of rates.json differs'in r.stderr and not log.exists(),r.stderr[-300:]
    ck.write_bytes(saved)
    # a checkpoint with another rates identity, or a row whose echoed rate is off the map, is rejected
    def redo(edit):
        x=json.loads(saved);edit(x);x['payload_sha256']=E.M.common.object_hash(x['native']);ck.write_text(json.dumps(x))
        (d/'groups'/j['group']/'merged.json').unlink(missing_ok=True);r=cli(p,'merge',d,'--group',j['group'],expect=1);ck.write_bytes(saved);return r.stderr
    assert 'another rates identity'in redo(lambda x:x['runtime'].__setitem__('rates_identity','default'))
    assert 'off the frozen rate map'in redo(lambda x:x['native']['rows'][0].__setitem__('rate','.76'))
    cli(p,'merge',d)
    # the native (fake: the same checks) refuses a derived rate file with a missing, extra or duplicate graph, or a bad value
    fk=E.pkg/'bin/c8d2_gmp';td=E.td/'ratefile';(td/'L3').mkdir(parents=True);(td/'L3/G1.txt').write_text('x');(td/'L3/G2.txt').write_text('x')
    net=td/'net.bin';p.make_net(net,2,11,60,77,8);(td/'g.txt').write_text('x');tasks=td/'t.txt';tasks.write_text('C8D2TASKS1 8 3 2\n0 0 1 0 4 4\n1 0 2 0 4 4\n')
    for name,text,want in (('ok','1 .7\n2 .8\n',0),('missing','1 .7\n',2),('extra','1 .7\n2 .8\n3 .9\n',2),('dup','1 .7\n1 .7\n2 .8\n',2),('range','1 .7\n2 1.2\n',2)):
        rfile=td/f'{name}.txt';rfile.write_text(text)
        cp=subprocess.run([str(fk),str(td),str(td/'g.txt'),str(net),str(tasks),str(td/f'out_{name}.json'),'5','0','@'+str(rfile),'1','compensated','-'],capture_output=True,text=True)
        assert cp.returncode==want,(name,cp.returncode,cp.stderr)
    # a cost model measured under another rates identity is refused by a non-test plan (D15)
    cm=E.td/'cm_map.json';cm.write_text(json.dumps(cost_model_for(E,None,rates=ident)))
    try:p.load_cost_model(cm,'gmp','default',test_only=False);raise AssertionError('accepted')
    except ValueError as e:assert 'rates identity'in str(e)
    assert p.load_cost_model(cm,'gmp',ident,test_only=False)['rates_identity']==ident
    ok('frozen_rate_maps_validation_identity_staging_checkpoints_native_D15',identity=ident[:12])
    return d,ident

# ================================================================ staging and Sobol nets (A-ORC-7)
def test_staging(E):
    """Staging (A-ORC-7): only the members of the index's blocks are staged, verified against the inventory, and only
    their bytes are read from the shared pack (os.pread, counted; F12); the staged runtime runs the index with scientific
    fields equal to a run from the shared package; a whole pack above 1 GB is refused."""
    sr=sys.modules.get('stage_runtime')or __import__('stage_runtime')
    d=E.td/'stage';E.small(d,'--shards',1,'--test-graphs',2);m=manifest(d);j=next(x for x in m['jobs']if x['group']=='a_free_L7')
    out=E.td/'staged';real_pread=os.pread;preads=[]
    def counting(fd,n,off):b=real_pread(fd,n,off);preads.append(len(b));return b
    with mock.patch.object(os,'pread',counting):r=sr.stage(d,out,j['id'])
    I=E.M.prod.Inputs(m['inputs'],json.loads((E.pkg/m['inputs']/'manifest.json').read_text()))
    src=Path(os.path.realpath(I.pack('free',7)));pack=Path(os.path.realpath(out))/src.relative_to(os.path.realpath(E.pkg))
    rows=[tuple(map(int,l.split()))for l in (d/j['tasks_file']).read_text().splitlines()];gids={x[2]for x in rows};assert len(rows)==j['tasks']if 'tasks'in j else rows
    inv={x['id']:x for x in json.loads((E.fixture/'inventory.json').read_text())['free']['7']}
    data=pack.read_bytes();full=src.read_bytes();assert len(data)==len(full)and r['members_staged']==len(gids)<len(inv),(r,len(gids),len(inv))
    staged=bytearray(len(full))
    for g in gids:x=inv[g];staged[x['offset']:x['offset']+x['length']]=full[x['offset']:x['offset']+x['length']]
    assert data==bytes(staged),'only the members of the index are staged'
    assert sum(preads)==sum(inv[g]['length']for g in gids),('bytes read from the shared pack',sum(preads),sum(inv[g]['length']for g in gids))
    assert not (Path(out)/'vendor').exists()and not (Path(out)/'reference').exists()
    tool(out,'production.py','run',d,'--index',j['id'],'--threads',2,'--scratch',E.scratch)
    ckd=d/'groups'/j['group']/'checkpoints';cks={f.name:json.loads(f.read_text())for f in ckd.glob('*.json')};assert cks
    for f in ckd.glob('*.json'):f.unlink()
    E.run(d,j['id']);sci=lambda x:[{k:r_[k]for k in E.M.prod.SCIENTIFIC}for r_ in x['native']['rows']]
    assert {f.name:sci(json.loads(f.read_text()))for f in ckd.glob('*.json')}=={n:sci(x)for n,x in cks.items()}
    # a corrupted member is refused; a whole pack above the limit is refused
    with mock.patch.object(sr,'WHOLE_PACK_LIMIT',1000):
        try:sr.stage(d,E.td/'staged_whole',j['id'],whole_pack=True);raise AssertionError('accepted')
        except ValueError as e:assert '> 1 GB'in str(e)
    sr.stage(d,E.td/'staged_whole_ok',j['id'],whole_pack=True)
    try:sr.stage(d,out,j['id']);raise AssertionError('accepted')
    except FileExistsError:pass
    ok('staging_members_only_runs_equal_whole_pack_refused',members=len(gids),inventory=len(inv))

def test_nets(E):
    p=E.M.prod;from scipy.stats import qmc;import numpy as np
    assert (p.reachable_columns(2**27),p.reachable_columns(2**28),p.reachable_columns(2**27+1),p.reachable_columns(1),p.reachable_columns(2))==(27,28,28,0,1)
    rng=np.random.default_rng(5);sv=rng.integers(1,2**52,size=(4,52),dtype=np.uint64);sh=rng.integers(0,2**52,size=4,dtype=np.uint64)
    st=p.gray_states(sv,sh,9);assert all(np.array_equal(st[n],p.gray_state(sv,sh,n))for n in range(512))
    def catches(fn,*args):
        try:fn(*args);return False
        except RuntimeError:return True
    results={}
    for top,bits in ((2**27,60),(2**28,52),(2**28,60)):
        m=p.reachable_columns(top);seed=91823+m+bits;eng=qmc.Sobol(d=31,scramble=True,bits=bits,seed=seed);sv0=eng._sv.copy();sh=eng._shift.copy()
        fresh=qmc.Sobol(d=31,scramble=True,bits=bits,seed=seed);fsv,fsh=fresh._sv.copy(),fresh._shift.copy()
        b=lambda s_:catches(p.check_fresh,s_,sh,fsv,fsh,m);c=lambda s_:catches(p.check_structure,s_,m,bits)
        assert not b(sv0)and not c(sv0)
        def mut(f):s_=sv0.copy();f(s_);return s_
        cases={'bit0':mut(lambda s_:s_.__setitem__((3,7),s_[3,7]^np.uint64(1))),'top_col':mut(lambda s_:s_.__setitem__((30,m-1),s_[30,m-1]^np.uint64(1<<(bits-3)))),
               'col_last_zero':mut(lambda s_:s_.__setitem__((1,m-1),np.uint64(0))),'col5_xor':mut(lambda s_:s_.__setitem__((0,5),s_[0,2]^s_[0,3])),'col_m_zero':mut(lambda s_:s_.__setitem__((1,m),np.uint64(0)))}
        got={k:(b(s_),c(s_))for k,s_ in cases.items()};results[f'{top}:{bits}']=got
        assert got['bit0'][0]and got['top_col'][0]and got['col_last_zero']==(True,True)and got['col5_xor']==(True,True),got
        assert got['col_m_zero']==(False,False),got
    # known-good fresh nets for every order-8 shape (dimension 4L-1, L = 2..8; bits 52 and 60), all columns, byte for byte
    for L in range(2,9):
        for bits in (52,60):
            f=E.td/f'net_{L}_{bits}.bin';info=p.make_net(f,2,4*L-1,bits,1000+L*bits,None);assert info['columns_checked']==bits
            r=np.random.default_rng(1000+L*bits);seeds=[int(r.integers(1,2**32-1))for _ in range(2)]
            want=struct.pack('<III',2,4*L-1,bits)+b''.join(qmc.Sobol(d=4*L-1,scramble=True,bits=bits,seed=s_)._sv.astype('<u8').tobytes()for s_ in seeds)
            assert f.read_bytes()==want,(L,bits)
    # bounded work: B = 128, dimension 31, a 2^40-point stratum; no fast_forward, at most 2^16 public points per replicate
    drawn=[];orig=qmc.Sobol.random_base2
    def spy(self,mm):drawn.append(1<<mm);return orig(self,mm)
    with mock.patch.object(qmc.Sobol,'fast_forward',side_effect=AssertionError('fast_forward called')),mock.patch.object(qmc.Sobol,'random_base2',spy):
        t0=time.perf_counter();info=p.make_net(E.td/'big.bin',128,31,60,4242,2**40);elapsed=time.perf_counter()-t0
    assert info['columns_checked']==40 and len(drawn)==128 and max(drawn)<=2**16
    d=E.td/'nets_plan';E.small(d,points=64,tg=1);c=config(d,'a_free_L8');assert c['net']['columns_checked']==p.reachable_columns(64)==6 and c['net']['dim']==31
    ok('sobol_export_checks_all_order8_shapes',mutations=results,bounded_2e40_seconds=round(elapsed,3))

# ================================================================ exact pack reads (F12)
BEEGFS_BLKSIZE=524288  # os.stat(pack).st_blksize on symmetry's BeeGFS (2026-10-05): the buffer size Python's open() picks there

class CountingRaw(io.RawIOBase):
    """A raw file that counts the bytes it reads; under io.BufferedReader it sees every byte the buffered reader reads."""
    def __init__(s,path):super().__init__();s._f=io.FileIO(path,'r');s.nbytes=0
    def readable(s):return True
    def seekable(s):return True
    def readinto(s,b):n=s._f.readinto(b);s.nbytes+=n or 0;return n
    def seek(s,pos,whence=0):return s._f.seek(pos,whence)
    def tell(s):return s._f.tell()
    def close(s):
        if not s.closed:s._f.close()
        super().close()

def buffered_model(members,B:int)->int:
    """Bytes a CPython BufferedReader with buffer size B reads for seek(offset); read(length) over sorted members: a seek
    inside the buffer is served from it, otherwise read() reads the whole B blocks of what it still needs directly and
    then refills one B buffer (the replay of benchmarks/symmetry_2026-10-c8/stage5/fix/scripts/claim_io_overread.py)."""
    tot=0;bs=be=None
    for off,ln in members:
        if not(bs is not None and bs<=off<=be):bs=be=None
        avail=(be-off)if bs is not None else 0
        if ln<=avail:continue
        rem=ln-avail;pos=off+avail;direct=rem-rem%B;tot+=direct;pos+=direct;rem-=direct
        if rem>0:tot+=B;bs,be=pos,pos+B
        else:bs=be=None
    return tot

def open_fds()->int:
    return len(os.listdir('/proc/self/fd'if os.path.isdir('/proc/self/fd')else'/dev/fd'))

def test_pack_reads(E):
    """F12: production.stage_graphs reads exactly the members' bytes from the pack (os.pread, no Python buffer), and the
    staged bytes are unchanged. A fake pack of 48 members with gaps (every fifth adjacent to the one before), of 1 B to
    1.2 MB (around and above the 524,288-byte BeeGFS buffer), and a block naming 30 of them (five twice): every os.pread
    is counted through a wrapper; the bytes read equal the members' bytes and the returned count, every read lies inside
    a member, the staged files equal the members byte for byte (hence their sha256 checks, which stage_graphs applies,
    are unchanged); with an os.pread that returns at most 4,097 bytes per call (short reads) the same bytes are staged
    and counted; read_member stops at the end of the file; a pack truncated inside a member is refused ('Packed graph
    content mismatch') and leaves no descriptor open. Control: the pre-fix read (seek, read through a BufferedReader
    with BeeGFS's 512 KiB buffer, over a counting raw file) of the same members reads exactly what the replay model of
    the F12 evidence predicts, at least one 512 KiB buffer more than the members. On Linux, rchar of /proc/self/io
    across one stage_graphs call equals the members' bytes exactly (and the pre-fix read on the same file is recorded)."""
    p=E.M.prod;import random
    t=E.td/'f12';t.mkdir();rng=random.Random(12);B=BEEGFS_BLKSIZE
    lengths=[1,7,349,2728,4096,4097,33416,94344,B-1,B,B+1,1200000]+[rng.randrange(1,200000)for _ in range(36)];rng.shuffle(lengths)
    rows=[];buf=bytearray()
    for i,n in enumerate(lengths):
        buf+=rng.randbytes(0 if i%5==0 else rng.randrange(1,300000));data=rng.randbytes(n)
        rows.append({'id':i,'offset':len(buf),'length':n,'sha256':hashlib.sha256(data).hexdigest()});buf+=data
    buf+=rng.randbytes(2*B);buf=bytes(buf)  # beyond the last member, so the control's refills are never cut by the end
    pack=t/'free_L8.pack';pack.write_bytes(buf);inv={r['id']:r for r in rows};member=lambda g:buf[inv[g]['offset']:inv[g]['offset']+inv[g]['length']]
    I=NS(pack=lambda sector,L:pack);cfg={'sector':'free','L':8}
    pick=sorted(rng.sample(range(len(rows)),30));block=[(k,0,g,0,4,4)for k,g in enumerate(pick+pick[:5])]
    want=sum(inv[g]['length']for g in pick);spans=[(inv[g]['offset'],inv[g]['offset']+inv[g]['length'])for g in pick]
    real_pread=os.pread;calls=[]
    def counting(fd,n,off):b=real_pread(fd,n,off);calls.append((off,len(b)));return b
    def short(fd,n,off):b=real_pread(fd,min(n,4097),off);calls.append((off,len(b)));return b
    staged=lambda root:{f.name:f.read_bytes()for f in (root/'L8').iterdir()}
    expect={f'G{g}.txt':member(g)for g in pick}
    with mock.patch.object(os,'pread',counting):root,nread,nm=p.stage_graphs(t/'a',I,cfg,block,inv)
    assert nread==want and nm==len(pick)and sum(n for _,n in calls)==want,(nread,nm,want,sum(n for _,n in calls))
    assert all(any(a<=off and off+n<=b for a,b in spans)for off,n in calls),'a read outside the members'
    assert staged(root)==expect and all(hashlib.sha256(v).hexdigest()==inv[int(k[1:-4])]['sha256']for k,v in staged(root).items())
    ncalls=len(calls);calls.clear()
    with mock.patch.object(os,'pread',short):root2,nread2,_=p.stage_graphs(t/'b',I,cfg,block,inv)
    assert nread2==want and sum(n for _,n in calls)==want and len(calls)>ncalls and staged(root2)==expect,(nread2,len(calls),ncalls)
    fd=os.open(pack,os.O_RDONLY)
    try:assert p.read_member(fd,len(buf)-10,100)==buf[-10:]and p.read_member(fd,5,0)==b''and p.read_member(fd,len(buf),7)==b''
    finally:os.close(fd)
    # a pack cut inside the last picked member is refused, and stage_graphs closes its descriptor
    cut=t/'cut.pack';cut.write_bytes(buf[:inv[pick[-1]]['offset']+inv[pick[-1]]['length']//2]);n0=open_fds()
    try:p.stage_graphs(t/'c',NS(pack=lambda s_,L:cut),cfg,block,inv);raise AssertionError('accepted a truncated pack')
    except ValueError as e:assert 'Packed graph content mismatch'in str(e)
    assert open_fds()==n0,(open_fds(),n0)
    # control: the pre-fix read (Python's buffered reader, BeeGFS's 512 KiB buffer) over-reads, exactly as the model says
    raw=CountingRaw(pack)
    with io.BufferedReader(raw,buffer_size=B)as f:
        for g in pick:f.seek(inv[g]['offset']);assert f.read(inv[g]['length'])==member(g)
        old=raw.nbytes
    model=buffered_model([(inv[g]['offset'],inv[g]['length'])for g in pick],B)
    assert old==model and old-want>=B,(old,model,want)
    info=dict(members=len(pick),member_bytes=want,preads=ncalls,short_preads=len(calls),prefix_buffered_bytes=old,prefix_overread_per_staged_byte=round((old-want)/want,3),
              st_blksize_here=os.stat(pack).st_blksize)
    if p.proc_rchar()is not None:  # Linux: rchar is the kernel's count of every byte this process read
        def rc():
            with open('/proc/self/io','rb')as f:d=f.read()
            return int(re.search(rb'^rchar:\s*(\d+)',d,re.M).group(1)),len(d)
        p.stage_graphs(t/'warm',I,cfg,block,inv)
        r0,n0=rc();p.stage_graphs(t/'d',I,cfg,block,inv);r1,_=rc()
        assert r1-r0-n0==want,('rchar across stage_graphs',r1-r0-n0,want)
        r0,n0=rc()
        with open(pack,'rb')as f:
            for g in pick:f.seek(inv[g]['offset']);f.read(inv[g]['length'])
        r1,_=rc();info.update(rchar_stage_graphs=want,rchar_prefix_default_open=r1-r0-n0)
    ok('pack_reads_exact_members_only_short_reads_truncation_F12',**info)

# ================================================================ per-index task data and bytes per claim (A-ORC-13)
def test_per_claim_reads(E,real:bool):
    """A-ORC-13 (R07, R17, R20). Two test-only campaigns with equal job counts, whose group a_free_L3 holds 1,024 and
    1,048,576 tasks. One claim (`run --index 0 --max-blocks 1`) runs in a fresh process under the read/launch spy
    (sitecustomize, a cold platform cache). Its reads, minus its own task file, checkpoints and the job-private runtime
    (staged members and copies), fall into the campaign-data allowlist and the platform/runtime class; no read grows
    with the other indices' tasks; tasks.sqlite and vendor/ are never read; the subprocesses are those of the platform
    contract; the platform bytes equal the checkpoint's fingerprint_bytes; the pack is opened only with os.open and the
    bytes read from it (os.pread, counted by the spy) equal the claim's own staged-member bytes (F12).
    Not covered by this spy: the reads that libc and OpenSSL make by themselves inside the claim process (on Linux
    /proc/sys/crypto/fips_enabled at OpenSSL initialization through hashlib, glibc's locale.alias when the locale is
    set up, the zoneinfo file for local time). They happen in C below the Python layer, so neither the audit hook nor
    the open/read wrappers see them, and the platform-byte equality above therefore excludes them. They are a constant
    set of small system files, independent of the task count of any index (docs/HPC.md, "Reads per claim"); rchar on
    real Slurm (J-SMK-4) includes them."""
    p=E.M.prod;assert p.fingerprint is E.M.common.fingerprint
    # on Linux with a built bin/c8d2_gmp the claims run the REAL worker from a second package copy (the Linux fingerprint
    # path: ELF interpreter and libraries); on the Mac the fake worker of the main copy (the documented fallback)
    P=make_package(E.td,real_exe=True,name='pkg_real')if real else E.pkg;fx=P/'tests/fixtures/inputs_mini'
    def runP(d,i,*extra,expect=0):
        cp=tool(P,'production.py','run',d,'--index',i,'--threads',2,'--scratch',E.scratch,*extra,env={'C8_INPUTS':str(fx)},check=False)
        assert (cp.returncode==0)==(expect==0),(d,i,cp.returncode,cp.stderr[-800:]);return cp
    cm=E.td/'cm_claim.json';cm.write_text(json.dumps(cost_model_for(E,None,lambda c,s,L,r:40. if (s,L)==('free',3)else 1e-9)))
    camps={}
    for name,npts in (('small',128),('large',131072)):
        d=E.td/f'claim_{name}'
        tool(P,'production.py','plan',d,'--seed',SEED+70,'--threads',2,'--pilot','--points',npts,'--replicates',2,'--test-graphs',4,'--cost-model',cm,'--shards',4,
             '--min-chunk',1,'--checkpoint-tasks',1024,env={'C8_INPUTS':str(fx),'SLURM_JOB_ID':'12'})
        m=manifest(d);camps[name]=(d,m)
        # the per-index task files equal the SQLite rows by (shard, pos)
        for j in m['jobs']:
            if j['group']!='a_free_L3':continue
            con=roq(d/'groups'/j['group']/'tasks.sqlite');want=''.join(f'{u} {r} {g} {lo} {hi} {t}\n'for u,r,g,lo,hi,t in con.execute('SELECT uid,rep,gi,lo,hi,total FROM tasks WHERE shard=? ORDER BY pos',(j['shard'],)));con.close()
            assert (d/j['tasks_file']).read_text()==want
    (ds,ms),(dl,ml)=camps['small'],camps['large'];assert len(ms['jobs'])==len(ml['jobs'])and ms['jobs'][0]['group']==ml['jobs'][0]['group']=='a_free_L3'
    nl=config(dl,'a_free_L3')['tasks'];ns=config(ds,'a_free_L3')['tasks'];assert nl>=10**6 and ns<=1100,(ns,nl)
    assert (dl/'groups/a_free_L3/tasks.sqlite').stat().st_size>10*(ds/'groups/a_free_L3/tasks.sqlite').stat().st_size
    pyroots=[os.path.realpath(x)for x in {sys.prefix,sys.base_prefix,sys.exec_prefix,os.path.dirname(os.__file__)}]
    recs={};cp_out={};cios={}
    def ck_fp_bytes(d):return json.loads(next((d/'groups/a_free_L3/checkpoints').glob('*.json')).read_text())['runtime']['fingerprint_bytes']
    for name,(d,m) in camps.items():
        scr=E.td/f'claim_scratch_{name}';scr.mkdir()
        cp,spy=spied([PY,'-B',str(P/'tools/production.py'),'run',str(d),'--index','0','--max-blocks','1','--threads','2','--scratch',str(scr)],{'C8_INPUTS':str(fx)},E.td,f'claim_{name}')
        assert cp.returncode==0,cp.stderr[-800:];cp_out[name]=cp.stdout
        main=[r for r in spy if r['argv'][:1]and r['argv'][0].endswith('production.py')];assert len(main)==1,[r['argv']for r in spy]
        recs[name]=(main[0],d,m,scr)
    def classify(rec,d,m,scr):
        own=os.path.realpath(d/m['jobs'][0]['tasks_file']);dr=os.path.realpath(d);pk=os.path.realpath(P);sr=os.path.realpath(scr)
        allow={os.path.realpath(d/'manifest.json'):'manifest',os.path.realpath(d/'cost_model.json'):'cost_model.json',os.path.realpath(fx/'manifest.json'):'inputs manifest',
               os.path.realpath(d/'groups/a_free_L3/config.json'):'group config',os.path.realpath(d/'groups/a_free_L3/sobol.bin'):'sobol.bin',
               os.path.realpath(P/'bin/c8d2_gmp'):'executable',os.path.realpath(fx/'inventory.json'):'inventory.json',
               os.path.realpath(P/'inputs/gamma_d2_8.txt'):'gamma_d2_8.txt',os.path.realpath(P/'inputs/two_loop.json'):'two_loop.json',
               os.path.realpath(d/'cpu_vendor.json'):'cpu_vendor.json',  # F5: the campaign's CPU-vendor pin, read by every claim after the first
               os.path.realpath(d/'runtime_identity.json'):'runtime_identity.json'}  # X8: the runtime-identity pin, likewise
        for n in m['tool_sha256']:allow[os.path.realpath(P/'tools'/n)]=f'tools/{n}'
        cls={'campaign':{},'platform':{},'measurement':{},'excluded':{},'violations':{}}
        # rec['reads'] holds the Python-level reads only; the constant libc/OpenSSL reads (fips_enabled, locale.alias,
        # zoneinfo) are invisible here and independent of the task count (see the docstring)
        for key,nbytes in rec['reads'].items():
            path,origin=key.rsplit('|',1)
            if PROC_IO.fullmatch(path):cls['measurement'][path]=cls['measurement'].get(path,0)+nbytes  # R07/F9: /proc/self/io, the claim's own rchar
            elif origin=='fingerprint':cls['platform'][path]=cls['platform'].get(path,0)+nbytes
            elif path==own or path.startswith(sr+os.sep)or '/checkpoints/'in path or path.endswith('.pack'):cls['excluded'][path]=nbytes
            elif path in allow:cls['campaign'][allow[path]]=cls['campaign'].get(allow[path],0)+nbytes
            elif path.startswith('pipe:'):cls['violations'][path]=nbytes
            else:cls['violations'][path]=nbytes
        opened=[o[0]for o in rec['opens']]
        bad_open=[o for o in opened if (o.startswith(pk+os.sep)or o.startswith(dr+os.sep))and not(o in allow or o==own or '/checkpoints/'in o or o.endswith('.pack')or o.startswith(sr+os.sep)
                  or '/logs/'in o or o.startswith(os.path.realpath(P/'tools')+os.sep)or o.endswith('.tmp')or '.tmp.'in o)]  # the claim's own tools (imports)
        roots=tuple(r+os.sep for r in pyroots);spylogs=os.path.realpath(E.td)+os.sep+'spylog_'
        rel=[x for x in rec['opens']if x[0].startswith('rel:')]
        assert all((x[3]or'').startswith('shutil._rmtree')for x in rel),rel  # only the cleanup's fd walk opens relative names
        stray=sorted({o for o in opened if not(o.startswith('rel:')or o.startswith(roots)or o in('/dev/null','/proc/cpuinfo')or PROC_IO.fullmatch(o)
                                                or o.startswith((pk+os.sep,dr+os.sep,sr+os.sep,spylogs))or o in cls['platform'])})
        return cls,opened,bad_open+[('outside the package, the campaign, the job-private runtime, Python and the platform class',x)for x in stray]
    out={}
    for name,(rec,d,m,scr) in recs.items():
        cls,opened,bad_open=classify(rec,d,m,scr)
        assert not cls['violations'],(name,cls['violations'])
        assert not bad_open,(name,bad_open[:10])
        # R07/F9: /proc/self/io is opened at the claim's start, around the fingerprint, around each native launch and at
        # exit (1 + 2 + 2 x 1 + 1 for this one-block claim), and only there; each read is a few hundred bytes
        nio=sum(1 for o in opened if PROC_IO.fullmatch(o));assert nio==6,(name,nio)
        assert all(v<=1024*nio for v in cls['measurement'].values()),cls['measurement']
        cio=[json.loads(l.split(' ',1)[1])for l in cp_out[name].splitlines()if l.startswith('claim_io ')]
        assert len(cio)==1 and cio[0]['status']=='ok'and cio[0]['native']['launches']==1 and cio[0]['fingerprint_bytes']==ck_fp_bytes(d),(name,cio)
        own=cio[0]['own'];assert own['task_file']['bytes']==m['jobs'][0]['tasks_bytes']and own['staged_members']['bytes']>0,(name,own)
        # F12: the claim reads exactly its members' bytes from the pack (os.pread, counted by the spy), equal to its own
        # staged-member bytes, and opens the pack only with os.open (audit mode None), never through a buffered reader
        packread=sum(n for k,n in rec['reads'].items()if k.rsplit('|',1)[0].endswith('.pack'))
        pack_opens=[o for o in rec['opens']if o[0].endswith('.pack')]
        assert packread==own['staged_members']['bytes']and pack_opens and all(o[1]=='None'for o in pack_opens),(name,packread,own['staged_members'],pack_opens)
        if sys.platform.startswith('linux'):
            assert cio[0]['rchar']>0 and cio[0]['native']['rchar']>0 and cio[0]['non_own_bytes']>0 and cio[0]['fingerprint_rchar']>=cio[0]['fingerprint_bytes'],(name,cio[0])
        else:assert cio[0]['rchar']is None and cio[0]['non_own_bytes']is None,(name,cio[0])  # no /proc/self/io
        cios[name]=cio[0]
        assert not rec['sqlite']and not any('tasks.sqlite'in o for o in opened),(name,rec['sqlite'])
        assert not any('/vendor/'in o for o in opened),[o for o in opened if '/vendor/'in o]
        assert rec['platform_cache_cold'],'the platform cache was warm in the fresh claim process (R20)'
        ck=json.loads(next((d/'groups/a_free_L3/checkpoints').glob('*.json')).read_text());fp=ck['runtime']['fingerprint']
        assert sum(cls['platform'].values())==ck['runtime']['fingerprint_bytes'],(name,cls['platform'],ck['runtime']['fingerprint_bytes'])
        launches=rec['popen'];exe=[x for x in launches if x[1]and x[1][0].endswith('c8d2_gmp')]
        probes=[x for x in launches if x[1]and Path(x[1][0]).name in('ldd','uname')]
        assert len(exe)==1 and len(launches)==len(exe)+len(probes),launches
        if sys.platform=='darwin':
            assert sorted(Path(x[1][0]).name for x in probes)==['ldd','uname']and [x[1]for x in probes if Path(x[1][0]).name=='uname']==[['uname','-p']]
            assert fp['ldd_error']and fp['interpreter']is None and fp['cpu_model']==subprocess.run(['uname','-p'],capture_output=True,text=True).stdout.strip()
        else:
            assert [Path(x[1][0]).name for x in probes]==['ldd'],probes
            assert fp['cpu_model']and fp['glibc']
            if real:assert fp['interpreter']and fp['interpreter']['sha256']and all(fp[k]and fp[k]['sha256']for k in('libgomp','libquadmath','libgmp')),fp
        rt=[x for x in cls['platform']if not x.startswith('pipe:')and os.path.realpath(scr)+os.sep in x]
        assert all(re.fullmatch(re.escape(os.path.realpath(scr))+r'/c8d2_runtime_[^/]+/c8d2_gmp',x)for x in rt),rt  # the staged executable is the job-private copy
        assert not any(x.startswith((os.path.realpath(P)+os.sep,os.path.realpath(d)+os.sep))for x in cls['platform']),cls['platform']
        norm={}
        for x,n in cls['platform'].items():  # the job-private runtime directory and the probe pipe's descriptor number vary
            k=re.sub(r'^pipe:\d+$','pipe',re.sub(r'c8d2_runtime_[^/]+','c8d2_runtime_*',x.replace(os.path.realpath(scr),'<scratch>')));norm[k]=norm.get(k,0)+n
        sizes={'manifest':(d/'manifest.json').stat().st_size,'group config':(d/'groups/a_free_L3/config.json').stat().st_size}
        def shape(x):  # the document with every number, digest and net seed blanked: what is left is independent of the task counts
            if isinstance(x,dict):return {k:shape(v)for k,v in x.items()}
            if isinstance(x,list):return [shape(v)for v in x]
            if isinstance(x,(int,float))and not isinstance(x,bool):return 0
            if isinstance(x,str)and re.fullmatch(r'[0-9a-f]{64}',x):return 'sha'
            return x
        shapes={'manifest':shape(json.loads((d/'manifest.json').read_text())),'group config':shape(config(d,'a_free_L3'))}
        out[name]=dict(campaign=cls['campaign'],sizes=sizes,shapes=shapes,platform=norm,platform_bytes=sum(cls['platform'].values()),excluded_bytes=sum(cls['excluded'].values()),
                       fingerprint_bytes=ck['runtime']['fingerprint_bytes'],launches=[[Path(x[1][0]).name,*x[1][1:2]]for x in launches],tasks=config(d,'a_free_L3')['tasks'])
    cs,cl=out['small']['campaign'],out['large']['campaign']
    assert sorted(cs)==sorted(cl),(sorted(cs),sorted(cl))
    if sys.platform.startswith('linux'):  # R07 with rchar (F9): the non-own bytes of the two claims agree as the plan asks
        for v in ('non_own_bytes','non_own_minus_fingerprint_bytes','non_own_minus_fingerprint_rchar'):
            x,y=cios['small'][v],cios['large'][v];assert abs(x-y)<=max(0.1*min(x,y),2e6),(v,x,y)
        for k in out:out[k]['claim_io']={v:cios[k][v]for v in ('rchar','non_own_bytes','fingerprint_rchar','own_bytes')}
    for k in cs:
        if k in('manifest','group config'):
            # these two hold per-index numbers (tasks, blocks, bytes, estimates, points): one read of the whole file in both
            # campaigns, with the same structure once numbers and digests are blanked, so the sizes differ only by the
            # digits of those numbers (here a few %) while the task counts differ 1000x
            zs,zl=out['small']['sizes'][k],out['large']['sizes'][k]
            assert cs[k]==zs and cl[k]==zl and out['small']['shapes'][k]==out['large']['shapes'][k]and abs(zl-zs)<=0.05*zs,(k,cs[k],zs,cl[k],zl)
        else:assert cs[k]==cl[k],(k,cs[k],cl[k])
    # the same platform files with the same byte counts in both campaigns; /proc/cpuinfo is read live (its MHz fields
    # change between reads), so its two sizes need only agree within 1%
    ps_,pl_=out['small']['platform'],out['large']['platform'];cpu='/proc/cpuinfo'
    assert sorted(ps_)==sorted(pl_)and all(ps_[k]==pl_[k]for k in ps_ if k!=cpu)and (cpu not in ps_ or abs(ps_[cpu]-pl_[cpu])<=0.01*ps_[cpu]),(out['small'],out['large'])
    assert out['large']['tasks']>=1000*out['small']['tasks']//2,(out['small']['tasks'],out['large']['tasks'])
    # one byte changed in an index's task file: run of that index refuses, and only that index
    tf=ds/ms['jobs'][1]['tasks_file'];orig=tf.read_bytes();tf.write_bytes(orig[:-2]+bytes([orig[-2]^1])+orig[-1:])
    try:
        r=runP(ds,1,'--max-blocks',1,expect=1);assert 'differs from the manifest pin'in r.stderr
        runP(ds,2,'--max-blocks',1)
    finally:tf.write_bytes(orig)
    # an unreadable tasks.sqlite does not stop a claim
    db=ds/'groups/a_free_L3/tasks.sqlite';os.chmod(db,0)
    try:runP(ds,0,'--max-blocks',2)
    finally:os.chmod(db,0o644)
    for x in out.values():x.pop('shapes')
    ok('per_claim_reads_bounded_platform_contract_fingerprint_bytes',linux_real_worker=real,small=out['small'],large=out['large'])

def test_claim_io(E):
    """R07/F9: the claim_io record of `production.py run` and tools/claim_io.py. In-process with a stand-in rchar counter
    (+1000 per read of /proc/self/io): the record has schema c8-d2-claim-io-2 (exact pack reads, F12), the fingerprint's
    rchar and each native launch's rchar are the deltas around them, the own bytes per category equal the files' sizes
    (task file, staged members: the bytes read from the pack, equal to the inventory lengths, each block's task file,
    the native outputs; a rerun reads only its checkpoints), and non_own_bytes = rchar - own - native. The tool on
    synthetic logs: pass, the read path per run (records of schema -1, the buffered pack reads before the F12 fix,
    counted and named in the notes), a non-own read growing with the other indices (fail), fingerprint_bytes differing
    within one key (fail), groups less than 10x apart and unmeasured runs (undecided). A lane-mode campaign logs one
    record per index (on Linux with measured values; on the Mac rchar is null and the tool is undecided)."""
    p=E.M.prod;d=E.td/'claimio';E.small(d,'--shards',1,'--test-graphs',2,seed=SEED+51);m=manifest(d);j=max(m['jobs'],key=lambda j:j['blocks']);idx=j['id']
    calls=[0]
    def fake():calls[0]+=1;return 1000*calls[0]
    with mock.patch.object(p,'proc_rchar',side_effect=fake):r=E.run(d,idx)
    rec=[json.loads(l.split(' ',1)[1])for l in r.stdout.splitlines()if l.startswith('claim_io ')];assert len(rec)==1,r.stdout[-600:]
    rec=rec[0];nb=j['blocks'];assert rec['status']=='ok'and rec['index']==idx and calls[0]==4+2*nb and rec['schema']=='c8-d2-claim-io-2',(rec,calls)
    assert rec['fingerprint_rchar']==1000 and rec['native']=={'launches':nb,'rchar':1000*nb,'unmeasured':0}and rec['rchar']==1000*calls[0],rec
    g=d/'groups'/j['group'];cfg=config(d,j['group']);inv={x['id']:x for x in json.loads((E.fixture/'inventory.json').read_text())[cfg['sector']][str(cfg['L'])]}
    rows=[tuple(map(int,l.split()))for l in (d/j['tasks_file']).read_text().splitlines()];T=m['checkpoint_tasks'];blocks=[rows[i:i+T]for i in range(0,len(rows),T)]
    own=rec['own'];assert own['task_file']=={'files':1,'bytes':j['tasks_bytes']},own
    assert own['task_file_snapshot']=={'files':1,'bytes':j['tasks_bytes']},own  # W9: the job-private snapshot, streamed once
    assert own['staged_members']['bytes']==sum(inv[gi]['length']for b in blocks for gi in {x[2]for x in b}),own
    assert own['native_outputs']['files']==nb and own['block_task_files']['files']==nb and 'checkpoints'not in own,own
    assert rec['own_bytes']==sum(v['bytes']for v in own.values())and rec['non_own_bytes']==rec['rchar']-rec['own_bytes']-rec['native']['rchar']
    assert rec['non_own_minus_fingerprint_bytes']==rec['non_own_bytes']-rec['fingerprint_bytes']and rec['non_own_minus_fingerprint_rchar']==rec['non_own_bytes']-1000
    calls[0]=0
    with mock.patch.object(p,'proc_rchar',side_effect=fake):r=E.run(d,idx)  # a rerun: every block present, read and validated
    rec2=json.loads(next(l for l in r.stdout.splitlines()if l.startswith('claim_io ')).split(' ',1)[1])
    cks=sum(f.stat().st_size for f in (g/'checkpoints').glob(f's{j["shard"]:06d}_p*.json'))
    assert rec2['native']['launches']==0 and rec2['own']['checkpoints']=={'files':nb,'bytes':cks}and calls[0]==4,(rec2,calls)
    # the tool on synthetic logs
    t=E.td/'claimio_syn';(t/'lanes/logs').mkdir(parents=True)
    (t/'manifest.json').write_text(json.dumps({'jobs':[{'id':i,'group':'g_small'if i<2 else 'g_large'}for i in range(4)]}))
    for gname,size in (('g_small',1000),('g_large',20000)):(t/'groups'/gname).mkdir(parents=True);(t/'groups'/gname/'tasks.sqlite').write_bytes(b'x'*size)
    def logs(vals,fpb=(7000000,)*4,status='ok',measured=True,schema='c8-d2-claim-io-2'):
        for f in (t/'lanes/logs').glob('*.log'):f.unlink()
        for i,v in enumerate(vals):
            r={'schema':schema,'index':i,'status':status,'fingerprint_key':'k1','fingerprint_bytes':fpb[i],'fingerprint_rchar':fpb[i]+1000,'native':{'launches':1,'rchar':5*10**6,'unmeasured':0},
               'own':{'staged_members':{'files':3,'bytes':10**6}},'non_own_bytes':v if measured else None,
               'non_own_minus_fingerprint_bytes':v-fpb[i]if measured else None,'non_own_minus_fingerprint_rchar':v-fpb[i]-1000 if measured else None}
            (t/'lanes/logs'/f'idx{i}.1.0.0.{i}.log').write_text('fingerprint x\nclaim_io '+json.dumps(r)+'\n')
        return tool(E.pkg,'claim_io.py',t,'--output',t/'report.json',check=False)
    cp=logs([30*10**6,30.4*10**6,31*10**6,30.9*10**6]);rep=json.loads((t/'report.json').read_text())
    assert cp.returncode==0 and rep['verdict']=='pass'and rep['smallest']=='g_small'and rep['largest']=='g_large'and rep['tasks_sqlite_ratio']==20,rep
    assert rep['native_rchar_per_staged_byte']['g_small']==[5.0,5.0],rep['native_rchar_per_staged_byte']
    assert rep['pack_reads']=={'exact':4,'buffered (pre-F12)':0,'unknown schema':0}and rep['notes']==[],(rep['pack_reads'],rep['notes'])
    # records of the tools before the F12 fix (schema -1, buffered pack reads): counted and named, the comparison as computed
    cp=logs([30*10**6,30.4*10**6,31*10**6,30.9*10**6],schema='c8-d2-claim-io-1');rep=json.loads((t/'report.json').read_text())
    assert cp.returncode==0 and rep['pack_reads']=={'exact':0,'buffered (pre-F12)':4,'unknown schema':0}and len(rep['notes'])==1 and 'F12'in rep['notes'][0],rep
    assert '"pack_reads"'in cp.stdout and 'F12'in cp.stdout,cp.stdout[-800:]
    cp=logs([30*10**6,30*10**6,700*10**6,30*10**6]);rep=json.loads((t/'report.json').read_text())
    assert cp.returncode==1 and rep['verdict']=='fail'and not rep['comparison']['non_own_bytes']['passed'],rep
    cp=logs([30*10**6]*4,fpb=(7000000,7000000,7000001,7000000));rep=json.loads((t/'report.json').read_text())
    assert cp.returncode==1 and not rep['fingerprint_bytes_identical'],rep
    (t/'groups/g_large/tasks.sqlite').write_bytes(b'x'*5000);cp=logs([30*10**6]*4);rep=json.loads((t/'report.json').read_text())
    assert cp.returncode==2 and rep['verdict']=='undecided'and 'not more than 10x'in rep['reason'],rep
    cp=logs([30*10**6]*4,measured=False);rep=json.loads((t/'report.json').read_text());assert cp.returncode==2 and rep['skipped']['unmeasured']==4,rep
    # a lane-mode campaign: one record per index log
    dl=E.td/'claimio_lanes';lanes_plan(E,dl,seed=SEED+52);tool(E.pkg,'lanes.py','queue',dl)
    ncpu=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else(os.cpu_count()or 1)
    tool(E.pkg,'lanes.py','worker',dl,env={'SLURM_JOB_ID':'6400','C8_LANE_SECONDS':'36000','C8_LANES':str(max(1,-(-ncpu//8)))})
    recs=[json.loads(next(l for l in f.read_text().splitlines()if l.startswith('claim_io ')).split(' ',1)[1])for f in (dl/'lanes/logs').glob('idx*.log')]
    assert len(recs)==len(manifest(dl)['jobs'])and all(x['status']=='ok'for x in recs),len(recs)
    cp=tool(E.pkg,'claim_io.py',dl,'--output',dl/'claim_io.json',check=False);rep=json.loads((dl/'claim_io.json').read_text())
    if sys.platform.startswith('linux'):  # /proc/cpuinfo is read live (its MHz fields change), so fingerprint_bytes agree within 1% here
        fpb=[x['fingerprint_bytes']for x in recs];assert rep['measured']==len(recs)and max(fpb)-min(fpb)<=0.01*min(fpb)and rep['verdict']in('pass','fail','undecided'),rep
        assert rep['pack_reads']=={'exact':len(recs),'buffered (pre-F12)':0,'unknown schema':0},rep['pack_reads']
    else:assert cp.returncode==2 and rep['skipped']['unmeasured']==len(recs),rep
    ok('claim_io_record_arithmetic_and_tool',blocks=nb,lane_verdict=rep['verdict'])

# ================================================================ the read/launch spy (sitecustomize, a fresh process)
PROC_IO=re.compile(r'/proc/(self|\d+)/io')  # the claim's measurement read (R07, F9): its own /proc/self/io
SPY_SITE=r"""
import os,sys
_d=os.environ.get('C8_READ_SPY')
if _d:
    import atexit,builtins,io,json,platform,shutil
    _c=getattr(platform,'_uname_cache',None)
    _E={'pid':os.getpid(),'argv':None,'platform_cache_cold':_c is None,'opens':[],'reads':{},'popen':[],'sqlite':[],'listdir':[]}
    shutil._HAS_FCOPYFILE=False;shutil._USE_CP_SENDFILE=False  # copies read through Python, so they are counted
    _FP=('fingerprint','cpu_model','elf_interpreter','_digest_counted','processor','from_subprocess','_get','get','uname')
    def _origin():
        f=sys._getframe(2);fp=False;inner=None
        while f is not None:
            fn=f.f_code.co_filename;nm=f.f_code.co_name
            if fn.endswith('common.py')and nm in('fingerprint','cpu_model','elf_interpreter','_digest_counted'):fp=True
            if inner is None and os.sep+'tools'+os.sep in fn:inner=f'{os.path.basename(fn)}:{nm}'
            f=f.f_back
        return ('fingerprint'if fp else'other'),inner
    _ro=io.open
    class _C:
        __slots__=('_f','_k')
        def __init__(s,f,k):s._f=f;s._k=k
        def _a(s,n):
            if n:_E['reads'][s._k]=_E['reads'].get(s._k,0)+n
        def read(s,*a):d=s._f.read(*a);s._a(len(d)if d else 0);return d
        def read1(s,*a):d=s._f.read1(*a);s._a(len(d)if d else 0);return d
        def readline(s,*a):d=s._f.readline(*a);s._a(len(d)if d else 0);return d
        def readlines(s,*a):d=s._f.readlines(*a);s._a(sum(len(x)for x in d));return d
        def readinto(s,b):n=s._f.readinto(b);s._a(n or 0);return n
        def __iter__(s):
            for x in s._f:s._a(len(x));yield x
        def __next__(s):x=next(s._f);s._a(len(x));return x
        def __enter__(s):s._f.__enter__();return s
        def __exit__(s,*a):return s._f.__exit__(*a)
        def __getattr__(s,n):return getattr(s._f,n)
    _PIPES={}  # descriptor -> read key of the pipes subprocess opens (communicate with a timeout reads them with os.read)
    class _Opener:
        # a callable object, not a function: pathlib (3.10) stores io.open as a class attribute, and a function there
        # would be bound as a method
        def __call__(self,file,mode='r',*a,**k):
            f=_ro(file,mode,*a,**k)
            if any(c in mode for c in 'wax')and '+'not in mode:return f
            o,inner=_origin();key=(f'pipe:{file}'if isinstance(file,int)else os.path.realpath(os.fsdecode(file)))+'|'+o
            if isinstance(file,int):_PIPES[file]=key
            return _C(f,key)
    io.open=builtins.open=_Opener()
    _oread=os.read
    def _read(fd,n):
        d=_oread(fd,n);k=_FDS.get(fd)or _PIPES.get(fd)  # W9: a claim reads its task file with os.read on an os.open descriptor
        if k and d:_E['reads'][k]=_E['reads'].get(k,0)+len(d)
        return d
    os.read=_read
    # files opened with os.open: production.stage_graphs reads the pack members with os.pread (F12), counted here; the
    # task-file snapshot (W9, Stage-6 fix round 4) reads with os.read. A descriptor number os.open returns may be one a
    # closed subprocess pipe had: its stale pipe key is dropped, so the read is counted under the file it is
    _FDS={};_oopen=os.open;_oclose=os.close;_opread=os.pread
    def _os_open(path,flags,*a,**k):
        fd=_oopen(path,flags,*a,**k)
        if k.get('dir_fd')is None and not isinstance(path,int):
            _PIPES.pop(fd,None);o,inner=_origin();_FDS[fd]=os.path.realpath(os.fsdecode(path))+'|'+o
        return fd
    def _os_close(fd):_FDS.pop(fd,None);_PIPES.pop(fd,None);return _oclose(fd)
    def _pread(fd,n,off):
        d=_opread(fd,n,off);k=_FDS.get(fd)
        if k and d:_E['reads'][k]=_E['reads'].get(k,0)+len(d)
        return d
    os.open=_os_open;os.close=_os_close;os.pread=_pread
    def _hook(ev,args):
        try:
            if ev=='open':
                if args and not isinstance(args[0],int):
                    o,inner=_origin();raw=os.fsdecode(args[0])
                    if os.path.isabs(raw):_E['opens'].append([os.path.realpath(raw),str(args[1])if len(args)>1 else'',o,inner])
                    else:  # relative to a dir_fd (shutil.rmtree's fd walk) or to the cwd: kept as given, with the opener
                        f=sys._getframe(1);via=None
                        while f is not None and via is None:
                            if f.f_code.co_filename.endswith('shutil.py'):via='shutil.'+f.f_code.co_name
                            f=f.f_back
                        _E['opens'].append(['rel:'+raw,str(args[1])if len(args)>1 else'',o,via or inner])
            elif ev=='subprocess.Popen':_E['popen'].append([os.fsdecode(args[0])if args[0]else None,[os.fsdecode(x)for x in args[1]]])
            elif ev=='sqlite3.connect':_E['sqlite'].append(str(args[0]))
            elif ev in('os.listdir','os.scandir'):_E['listdir'].append(os.fsdecode(args[0])if args and args[0]is not None else'.')
        except Exception:pass
    sys.addaudithook(_hook)
    def _dump():
        _E['argv']=list(sys.argv)
        with _ro(os.path.join(_d,f'spy.{os.getpid()}.json'),'w')as f:json.dump(_E,f)
    atexit.register(_dump)
"""

def spied(cmd,env,td:Path,name:str)->tuple:
    """Run cmd in a fresh Python process with the spy installed through sitecustomize before any other import; returns
    (completed process, [spy record of every spied Python process])."""
    site=td/f'spysite_{name}';site.mkdir(exist_ok=True);(site/'sitecustomize.py').write_text(SPY_SITE);logs=td/f'spylog_{name}';logs.mkdir(exist_ok=True)
    e={**os.environ,**env,'C8_READ_SPY':str(logs),'PYTHONPATH':str(site),'PYTHONDONTWRITEBYTECODE':'1'}
    cp=subprocess.run(cmd,capture_output=True,text=True,env=e)
    return cp,[json.loads(f.read_text())for f in sorted(logs.glob('spy.*.json'))]

# ---------------------------------------------------------------- the test drivers' own evidence (T-02, T-03)
def test_drivers(E):
    """--only NAME,... refuses unknown names and empty selections before any setup (exit 2, no record): this file and
    tests/test_pipeline.py; tests/validate.py refuses a run that selects nothing; a valid selection records what was
    requested and executed (T-03). tests/vendored_isolated.py writes "passed": false with "completed": false and the
    error when it stops early: --in-place in a tree with .git, a tree without the HANDOFF, a HANDOFF whose test counts
    do not parse (T-02). Each case ran nothing and reported "passed" (or wrote passed=true) on 601b102."""
    t=E.td/'drivers';t.mkdir()
    def py(script,*args):
        return subprocess.run([PY,'-B',str(script),*map(str,args)],capture_output=True,text=True,timeout=600,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    rec=t/'rec.json'
    for script,good,bad in ((E.pkg/'tests/unit_orchestration.py','literal_sizes','alocation'),(E.pkg/'tests/test_pipeline.py','part1','part9')):
        for sel in (bad,f'{good},{bad}',',',''):
            t0=time.time();cp=py(script,'--only',sel,'--output',rec)
            assert cp.returncode==2 and '--only'in cp.stderr and (bad in cp.stderr or 'no test'in cp.stderr or 'no part'in cp.stderr),(script.name,sel,cp.returncode,cp.stderr[-400:],cp.stdout[-400:])
            assert not rec.exists()and 'PASS'not in cp.stdout and time.time()-t0<60,(script.name,sel,'ran something')
    for args in (('--only',),('--only','none')):
        cp=py(E.pkg/'tests/validate.py',*args,'--output',rec)
        assert cp.returncode==2 and 'no test selected'in cp.stderr and not rec.exists(),(args,cp.returncode,cp.stderr[-400:])
    cp=py(E.pkg/'tests/unit_orchestration.py','--only','literal_sizes','--output',rec)
    r=json.loads(rec.read_text());rec.unlink()
    assert cp.returncode==0 and r['status']=='passed'and r['requested']==['literal_sizes']and r['executed']==['literal_sizes'],(cp.returncode,r.get('requested'),r.get('executed'),cp.stderr[-400:])
    # vendored_isolated.py stopping early: the record says so
    src=(E.pkg/'tests/vendored_isolated.py').read_text()
    def tree(name,git=False,handoff=None):
        d=t/name;(d/'tests').mkdir(parents=True);(d/'tests/vendored_isolated.py').write_text(src)
        if git:(d/'.git').mkdir()
        if handoff is not None:(d/'vendor/c8_assembly').mkdir(parents=True);(d/'vendor/c8_assembly/HANDOFF_assembly.json').write_text(json.dumps(handoff))
        return d/'tests/vendored_isolated.py'
    for name,script,needle in (('git',tree('vi_git',git=True),'--in-place needs a git archive export'),
                               ('no_handoff',tree('vi_no_handoff'),'FileNotFoundError'),
                               ('bad_handoff',tree('vi_bad_handoff',handoff={'checks_at_handoff':{'tests':'no counts here'},'files':[]}),'cannot read the test counts')):
        out=t/f'vi_{name}.json';cp=py(script,'--in-place','--output',out)
        r=json.loads(out.read_text())
        assert cp.returncode!=0 and r['passed']is False and r['completed']is False and needle in(r['error']or''),(name,cp.returncode,r)
        assert r['failed']==['the verification ran to completion']and r['checks'][-1]['passed']is False,(name,r['failed'])
    ok('drivers_only_refuses_unknown_and_empty_selections_vendored_isolated_records_early_stops',selections_refused=8)

# ================================================================ Stage-6 fix round 1, group G2 (X8-X13, X21)
def test_runtime_identity(E):
    """X8 (S6-C-01): the campaign's runtime compatibility identity (common.runtime_identity): glibc and the content hashes
    of the interpreter and every loaded library, not the host, the Slurm ids, the CPU model or the library paths. The
    first claim pins it (runtime_identity.json); a checkpoint of another library stack is refused by run-skip, the
    parallel merge (--jobs 1 and 2) and the serial merge, also in a campaign without the pin (claims before X8: the
    first checkpoint's identity), while another host and CPU model with the same libraries are accepted; a claim under
    another pinned identity stops with 64 before any block, and a pin whose key is not its identity's hash refuses."""
    p=E.M.prod;C=E.M.common
    lib=lambda path,sha:{'path':path,'resolved':path+'.3.2','sha256':sha}
    fp={'host':'n1','cpu_model':'AMD EPYC 7742 64-Core Processor','glibc':'glibc 2.28','ldd_error':None,'slurm':{'SLURM_JOB_ID':'1'},
        'interpreter':{'path':'/lib64/ld-linux-x86-64.so.2','resolved':'/usr/lib64/ld-2.28.so','sha256':'1'*64},
        'libraries':{'libgmp.so.10':lib('/usr/lib64/libgmp.so.10','2'*64),'libgomp.so.1':lib('/usr/lib64/libgomp.so.1','3'*64)}}
    k=C.runtime_identity_key(fp);assert k==C.object_hash(C.runtime_identity(fp))and C.runtime_identity_key(None)is None
    same=json.loads(json.dumps(fp));same.update(host='n2',cpu_model='AMD EPYC 7763 64-Core Processor',slurm={'SLURM_JOB_ID':'2','SLURM_ARRAY_TASK_ID':'5'})
    same['libraries']['libgmp.so.10'].update(path='/opt/gmp/lib/libgmp.so.10',resolved='/opt/gmp/lib/libgmp.so.10.4.1')  # same bytes elsewhere
    assert C.runtime_identity_key(same)==k
    edits={'library content':lambda x:x['libraries']['libgmp.so.10'].update(sha256='4'*64),'glibc':lambda x:x.update(glibc='glibc 2.34'),
           'interpreter':lambda x:x['interpreter'].update(sha256='5'*64),'library missing':lambda x:x['libraries'].pop('libgomp.so.1'),
           'library added':lambda x:x['libraries'].update({'libquadmath.so.0':lib('/usr/lib64/libquadmath.so.0','6'*64)}),'ldd':lambda x:x.update(ldd_error='ldd failed')}
    for name,f in edits.items():
        y=json.loads(json.dumps(fp));f(y);assert C.runtime_identity_key(y)!=k,name
    # the campaign: the first claim pins its identity; status reports it
    d=E.td/'rtid';E.small(d,'--checkpoint-tasks',4,'--shards',1,seed=SEED+93);m=manifest(d);pinf=d/'runtime_identity.json'
    assert not pinf.exists();E.run(d,0);pin=json.loads(pinf.read_text())
    ck=sorted((d/'groups'/m['jobs'][0]['group']/'checkpoints').glob('*.json'))[0];fp0=json.loads(ck.read_text())['runtime']['fingerprint']
    assert pin['schema']=='c8-d2-runtime-pin-1'and pin['key']==C.runtime_identity_key(fp0)==C.object_hash(pin['identity'])and pin['first_claim']['index']==0,pin
    E.run_all(d);assert json.loads(pinf.read_text())==pin
    st=json.loads(cli(p,'status',d,'--json').stdout);assert st['runtime_identity']==pin
    assert 'runtime identity: '+pin['key'][:12]in cli(p,'status',d).stdout
    j=m['jobs'][0];g=j['group'];victim=d/'groups'/g/'checkpoints'/f'{p.block_name(j["shard"],0)}.json';orig=victim.read_bytes()
    assert len(list((d/'groups'/g/'checkpoints').glob('*.json')))>=2,g  # the merge without the pin compares the others with this one
    def with_fp(fn):
        x=json.loads(orig);fn(x['runtime']['fingerprint']);victim.write_text(json.dumps(x))
    # the same library stack on another node and CPU model (Zen 2 / Zen 3 of one image): accepted by run-skip and merge
    with_fp(lambda f:f.update(host='other-node',cpu_model='Other CPU model',slurm={'SLURM_JOB_ID':'99'}))
    E.run(d,j['id']);ok_=E.td/'rtid_ok';shutil.copytree(d,ok_);cli(p,'merge',ok_,'--group',g);cli(p,'merge',ok_,'--group',g,'--serial')
    # another library stack: refused by run-skip, both merges (jobs 1 and 2) and the serial merge
    with_fp(lambda f:f['libraries'].update({'libgmp.so.10':lib('/x/libgmp.so.10','f'*64)}))
    n=0
    for args in (('run',d,'--index',j['id'],'--threads',2,'--scratch',E.scratch),('merge',d,'--group',g),('merge',d,'--group',g,'--jobs',2),('merge',d,'--group',g,'--serial')):
        r=cli(p,*args,expect=1);assert 'another runtime library stack'in r.stderr and not (d/'groups'/g/'merged.json').exists(),(args,r.stderr[-600:]);n+=1
    # a campaign without the pin (claims before X8): every checkpoint must carry the identity of its first checkpoint
    pinf.unlink()
    r=cli(p,'merge',d,'--group',g,expect=1);assert 'another runtime library stack'in r.stderr and 'no runtime_identity.json'in r.stderr,r.stderr[-600:];n+=1
    victim.write_bytes(orig);cli(p,'merge',d,'--group',g);(d/'groups'/g/'merged.json').unlink()
    pinf.write_text(json.dumps(pin,indent=2)+'\n')
    # a claim under another pinned identity stops before any block (64); a pin whose key is not its identity's hash refuses
    other=dict(pin['identity'],glibc='glibc 9.99');pinf.write_text(json.dumps({**pin,'identity':other,'key':C.object_hash(other)}))
    jx=m['jobs'][-1];cps=sorted((d/'groups'/jx['group']/'checkpoints').glob(f's{jx["shard"]:06d}_p*.json'));gone_=cps[-1];saved=gone_.read_bytes();gone_.unlink()
    r=E.run(d,jx['id'],expect=1)
    assert r.returncode==64 and 'another run-time library stack'in r.stderr and 'glibc'in r.stderr and not gone_.exists()and '"status": "runtime identity refused"'in r.stdout,(r.returncode,r.stderr[-500:])
    pinf.write_text(json.dumps({**pin,'key':'0'*64}));r=E.run(d,jx['id'],expect=1);assert 'not a valid c8-d2-runtime-pin-1 pin'in r.stderr,r.stderr[-400:];n+=2
    pinf.write_text(json.dumps(pin,indent=2)+'\n');E.run(d,jx['id'])
    sci=lambda b:[{k:r[k]for k in p.SCIENTIFIC}for r in json.loads(b)['native']['rows']];assert sci(gone_.read_bytes())==sci(saved)
    cli(p,'merge',d)
    ok('runtime_identity_pinned_by_first_claim_enforced_by_run_skip_and_both_merges_X8',refusals=n)

def synth_bundle(E,dest:Path,batches:int=2,count:int=8,reps:int=2)->Path:
    """A frozen --test-only design bundle (schema c8-d2-design-1) over every fixture graph: counts `count`, s = 1."""
    inv=json.loads((E.fixture/'inventory.json').read_text());dest.mkdir(parents=True);(dest/'counts').mkdir()
    strata={f'{s}_L{L}':{'s':1}for s in ('free','power')for L in range(3,9)};strata['free_L8_primitive']={'s':1}
    (dest/'design.json').write_text(json.dumps({'strata':strata,'replicates':{f'{s}_L{L}':reps for s in ('free','power')for L in range(3,9)},'batches':batches}))
    cs={}
    for c in 'ab':
        for s in ('free','power'):
            for L in range(3,9):
                name=f'counts/{c}_{s}_L{L}.txt';data=''.join(f'{r["id"]} {count}\n'for r in inv[s][str(L)]).encode();(dest/name).write_bytes(data);cs[name]=hashlib.sha256(data).hexdigest()
    meta={'schema':'c8-d2-design-1','provisional':False,'test_only':True,'design_sha256':digest(dest/'design.json'),'counts_sha256':cs,
          'inputs_manifest_sha256':digest(E.fixture/'manifest.json'),'rates_identity':'default','numerics':'exact','pilot':{'numerics':'exact'},
          'profile_recost':None,'forbidden_seeds':[]}
    (dest/'design_meta.json').write_text(json.dumps(meta,indent=1)+'\n');return dest

def test_bundle_relocation(E):
    """X9 (S6-C-02, S6D-03): a plan --design keeps a verified copy of the bundle files (<campaign>/design_bundle, recorded
    as design.pinned_copy), and combine.py and assemble.py read the bundle through production.design_bundle: two
    batches copied to another place combine after the original bundle path is gone, with the same result; a tampered
    pinned copy (a counts file, design_meta.json) is refused; without a pinned copy the refusal names --bundle, and
    --bundle DIR is accepted only when its design_meta.json has the pinned sha256; assemble.evaluate of a non-test
    campaign uses the pinned copy or the override (coverage guard spied)."""
    p=E.M.prod;comb=E.M.comb;A=E.M.asm;B=synth_bundle(E,E.td/'reloc_B')
    bs={}
    for name,seed in (('b1',SEED+100),('b2',SEED+101)):
        d=E.td/f'reloc_{name}';E.plan(d,'--design',B,'--test-graphs',2,'--bootstrap-chunk',4,'--shards',1,seed=seed);E.run_all(d);cli(p,'merge',d);bs[name]=d
    cli(comb,bs['b1'],bs['b2'],'--output',E.td/'reloc_out0','--test-only','--bootstrap',0)
    site=E.td/'reloc_site2';site.mkdir();c1,c2=site/'b1',site/'b2';shutil.copytree(bs['b1'],c1);shutil.copytree(bs['b2'],c2)
    moved=E.td/'reloc_B_moved';B.rename(moved)  # the planned bundle path is gone (another site)
    cli(comb,c1,c2,'--output',E.td/'reloc_out1','--test-only','--bootstrap',0)
    r0,r1=(json.loads((E.td/f'reloc_out{i}/C8_test_final.json').read_text())for i in (0,1))
    assert r1['test_partial']['batches']['count']==2 and r0['test_partial']['C8_full']==r1['test_partial']['C8_full']and r0['test_partial']['design']==r1['test_partial']['design']
    for d in bs.values():  # the pinned copy: the bundle's files, byte for byte, recorded in the manifest
        m=manifest(d);pc=d/'design_bundle'
        assert m['design']['pinned_copy']=='design_bundle'and digest(pc/'design_meta.json')==m['design']['meta_sha256']==digest(moved/'design_meta.json')
        files=sorted(str(x.relative_to(pc))for x in pc.rglob('*')if x.is_file());assert files==sorted(str(x.relative_to(moved))for x in moved.rglob('*')if x.is_file()),files
        assert all((pc/f).read_bytes()==(moved/f).read_bytes()for f in files)
    n=0
    def refused(*args,needle):
        nonlocal n;r=cli(comb,*args,'--output',E.td/'reloc_rej','--test-only','--bootstrap',0,expect=1)
        assert needle in r.stderr and not (E.td/'reloc_rej/C8_test_final.json').exists(),(needle,r.stderr[-500:]);n+=1
    t=site/'b1_counts';shutil.copytree(c1,t);f=t/'design_bundle/counts/a_free_L3.txt';f.write_text(f.read_text().replace(' 8\n',' 16\n',1))
    refused(t,c2,needle='differs from the digest in design_meta.json')
    t=site/'b1_meta';shutil.copytree(c1,t);f=t/'design_bundle/design_meta.json';f.write_text(f.read_text()+' ')
    refused(t,c2,needle='differs from the design_meta.json the campaign was planned with')
    nopin=site/'b1_nopin';shutil.copytree(c1,nopin);shutil.rmtree(nopin/'design_bundle')
    refused(nopin,c2,needle='give --bundle DIR')
    cli(comb,nopin,c2,'--output',E.td/'reloc_out2','--test-only','--bootstrap',0,'--bundle',moved)
    assert json.loads((E.td/'reloc_out2/C8_test_final.json').read_text())['test_partial']['C8_full']==r0['test_partial']['C8_full']
    other=synth_bundle(E,E.td/'reloc_B_other',count=16);refused(nopin,c2,'--bundle',other,needle="not the campaign's bundle")
    # assemble.evaluate of a NON-test campaign (the test-only view reads no bundle): load_campaign relabelled, the
    # coverage guard spied for the bundle it is given
    seen=[];real=A.load_campaign
    def nontest(directory,accept_tool_change=False):
        m_,*rest=real(directory,accept_tool_change);return (dict(m_,test_only=False),*rest)
    with mock.patch.object(A,'load_campaign',nontest),mock.patch.object(A,'coverage_guard',lambda groups,inv,order,bundle,s,**kw:seen.append(bundle)):
        A.evaluate(c1,0);A.evaluate(nopin,0,bundle_override=moved)
        for args,needle in (((nopin,0),'give --bundle DIR'),((nopin,0,False,other),"not the campaign's bundle")):
            try:A.evaluate(*args);raise AssertionError(f'accepted {args}')
            except ValueError as e:assert needle in str(e),(needle,str(e));n+=1
    assert seen==[c1/'design_bundle',moved.resolve()],seen
    ok('design_bundle_pinned_in_campaign_relocated_batches_combine_override_verified_X9',refusals=n)

def test_cost_model_numerics(E):
    """X10 (S6-C-03, S6D-04, S6-F-02), production.py side: a non-test plan refuses a cost model measured under other
    numerics (or recording none), with the cost-model numerics named; a test-only plan keeps it with a warning and the
    recorded exception in its manifest (cost_model_numerics_exception); a matching model records none; without the
    plan's numerics (design.py's route-(b) re-costing, which checks the profile itself) nothing is compared."""
    p=E.M.prod;cmf=E.td/'cmn.json'
    def write(**kw):
        x=cost_model_for(E,None);x.update(kw);x={k:v for k,v in x.items()if v is not None};cmf.write_text(json.dumps(x));return cmf
    write(numerics='dd+mp256');n=0
    for kw in (dict(numerics='exact'),):
        try:p.load_cost_model(cmf,'gmp','default',False,**kw);raise AssertionError('accepted')
        except ValueError as e:assert 'cost model numerics identity'in str(e)and "'dd+mp256'"in str(e)and "'exact'"in str(e),str(e);n+=1
    exc=[];err=io.StringIO()
    with contextlib.redirect_stderr(err):p.load_cost_model(cmf,'gmp','default',True,numerics='exact',exceptions=exc)
    assert exc==[{'cost_model_numerics':'dd+mp256','plan_numerics':'exact','scope':'test-only plan',
                  'rule':'non-test plans refuse a cost model of other numerics (production.load_cost_model, X10)'}]and 'warning'in err.getvalue(),(exc,err.getvalue())
    assert p.load_cost_model(cmf,'gmp','default',False,numerics='dd+mp256')['numerics']=='dd+mp256'
    assert p.load_cost_model(cmf,'gmp','default',False)['numerics']=='dd+mp256'
    write(numerics=None)
    try:p.load_cost_model(cmf,'gmp','default',False,numerics='exact');raise AssertionError('accepted a cost model without numerics')
    except ValueError as e:assert 'cost model numerics identity None'in str(e),str(e);n+=1
    # plan level (test-only): the exception is recorded; a matching model records none
    for name,cmn,want in (('other','dd+mp256','dd+mp256'),('same','exact',None)):
        write(numerics=cmn);d=E.td/f'cmn_plan_{name}'
        r=E.plan(d,'--pilot','--points',8,'--replicates',2,'--test-graphs',2,'--cost-model',cmf,'--shards',1,seed=SEED+110+len(name));mm=manifest(d)
        assert mm['cost_model_numerics']==cmn and (mm['cost_model_numerics_exception']or{}).get('cost_model_numerics')==want,(name,mm['cost_model_numerics_exception'])
        assert ('cost model numerics identity'in r.stderr)==(want is not None),r.stderr[-400:]
    ok('cost_model_numerics_refused_for_non_test_plans_recorded_exception_for_test_only_X10',refusals=n)

def test_amd_cap_template(E):
    """X11 (S6-C-04, S6-F-03): the whole shell path slurm/submit.sh -> C8_ENV_SETUP (the export lines of the symmetry
    block of slurm/env.sh.example; its module and venv lines need the cluster) -> slurm_submit.py: the template supplies
    C8_AMDQ_CAP=4 only as a default; an explicit agreed window survives the setup, higher (5: four workers and the
    merge admitted) and lower (3: three workers and the merge refused)."""
    d=E.td/'capt';lanes_plan(E,d,seed=SEED+94)
    block=(E.pkg/'slurm/env.sh.example').read_text().split('# ---- symmetry',1)[1].split('\n# ----',1)[0]
    lines=[l for l in block.splitlines()if l.startswith('export ')and not l.startswith(('export PATH=','export C8_PYTHON='))]
    assert any('C8_AMDQ_CAP'in l for l in lines)and any('C8_SITE=symmetry'in l for l in lines),lines
    envsh=E.td/'capt_env.sh';envsh.write_text(f'export C8_PYTHON={PY}\n'+'\n'.join(lines)+'\n')
    S=Slurm(E,'capt',C8_RUN=str(d),C8_ENV_SETUP=str(envsh),C8_SBATCH_ARGS='-p amdq --exclude=cn112',C8_LANE_MEM='245G')
    def adm(cp):return json.loads(next(l for l in cp.stdout.splitlines()if l.startswith('C8: admission '))[len('C8: admission '):])
    out={}
    for name,n,extra,code in (('default_fits',3,{},0),('default_full',4,{},65),('higher',4,{'C8_AMDQ_CAP':'5'},0),('lower',3,{'C8_AMDQ_CAP':'3'},65)):
        S.queue();cp,c=S.call('submit.sh',['--lanes',str(n)],**extra);a=adm(cp)
        assert cp.returncode==code and a['amd_cap']==int(extra.get('C8_AMDQ_CAP',4))and a['site']=='symmetry',(name,cp.returncode,a,cp.stderr[-400:])
        assert len(c)==(n+1 if code==0 else 0),(name,len(c));out[name]=a['amd_cap']
    ok('amd_cap_template_default_only_explicit_window_kept_higher_and_lower_X11',caps=out)

def test_account_partition_selection(E):
    """X12 (S6-C-05): the account and partition that admission queries and the ledger records are passed to every
    sbatch explicitly: C8_ACCOUNT without -A (Expanse lanes: workers and merge get --account; admission's squeue -A
    and the ledger name the same account), Expanse's inferred 'shared' partition in array mode (work array and merge
    get --partition=shared), no --account where none is selected (symmetry); a job whose effective account differs
    from the counted one is refused (64)."""
    p=E.M.prod;ss=E.M.ss
    d=E.td/'xsel';lanes_plan(E,d,seed=SEED+95)
    S=Slurm(E,'xsel',C8_RUN=str(d),C8_SITE='expanse',C8_SBATCH_ARGS='-p compute',C8_ACCOUNT='yun124');S.queue()
    cp,c=S.call('submit.sh',['--lanes','1']);assert cp.returncode==0 and len(c)==2,cp.stderr[-600:]
    assert all(last(x['args'],'--account')=='yun124'and partition_of(x['args'])=='compute'for x in c),[x['args']for x in c]
    led=[json.loads(l)for l in (d/'submissions.jsonl').read_text().splitlines()];ids={x['jobid']for x in c}
    assert {x['account']for x in led if x.get('jobid')in ids}=={'yun124'}and {x['partition']for x in led if x.get('jobid')in ids}=={'compute'}
    sq=[x['args']for x in S.log()if x['cmd']=='squeue'and '-A'in x['args']];assert sq and all(a[a.index('-A')+1]=='yun124'for a in sq),sq
    da=E.td/'xsel_arr';E.small(da,'--shards',1,seed=SEED+96)
    Sa=Slurm(E,'xsel_arr',C8_RUN=str(da),C8_SITE='expanse',C8_SBATCH_ARGS='--time=00:10:00',C8_ACCOUNT='yun124');Sa.queue()
    cp,c=Sa.call('submit.sh');assert cp.returncode==0 and {x['script']for x in c}=={'run_array.sh','merge.sh'},cp.stderr[-600:]
    assert all(partition_of(x['args'])=='shared'and last(x['args'],'--account')=='yun124'for x in c),[x['args']for x in c]
    led=[json.loads(l)for l in (da/'submissions.jsonl').read_text().splitlines()];assert {(x['partition'],x['account'])for x in led if x.get('jobid')}=={('shared','yun124')}
    Sy=Slurm(E,'xsel_sym',C8_RUN=str(d),C8_SITE='symmetry',C8_SBATCH_ARGS='-p amdq');Sy.queue()
    cp,c=Sy.call('submit.sh',['--lanes','1']);assert cp.returncode==0 and c and all(last(x['args'],'--account')is None and partition_of(x['args'])=='amdq'for x in c),cp.stderr[-400:]
    cx=ss.Context({**S.base,'C8_RUN':str(d)},[])
    try:cx.check_effective('lane',{'nodes':'1','ntasks':'1','mem':cx.lane_mem,'exclusive':True,'partition':'compute','account':'other'});raise AssertionError('accepted')
    except ss.Refuse as r:assert r.code==64 and 'admission counted yun124'in str(r),str(r)
    ok('account_and_partition_passed_to_every_sbatch_as_admitted_and_ledgered_X12')

def test_lane_failure_recheck(E):
    """X13 (S6-C-06): the stale-snapshot interleaving. A lane scans the queue (index i has one failure record, limit 2);
    before it claims i, another lane claims i, fails, records the second failure and releases. The first lane then
    gets the claim, rechecks the failure count under it, releases and launches nothing: no third attempt."""
    L=E.M.lanes;d=E.td/'lfail';lanes_plan(E,d,seed=SEED+97);m=manifest(d);idx=m['jobs'][0]['id'];fd=d/'lanes/failures'
    L.write_queue(d,[(idx,1.0)]);fd.mkdir(parents=True,exist_ok=True);L.publish(fd/f'{idx}.900.0.0.1.json','{}\n')
    real_claim=L.claim;launched=[]
    def interleaved(run,i,owner):
        if i==idx and not (fd/f'{idx}.901.0.0.2.json').exists():  # lane B: claim, fail, record, release (after A's scan)
            assert real_claim(run,i,{'job':'901','lane':0});L.publish(fd/f'{idx}.901.0.0.2.json','{}\n');L.release(run,i)
        return real_claim(run,i,owner)
    class Child:
        pid=2**22;returncode=1
        def wait(self,timeout=None):return 1
        def poll(self):return 1
        def send_signal(self,s):pass
        def kill(self):pass
    def popen(cmd,*a,**k):launched.append(cmd);return Child()
    args=NS(directory=d,lane=0,cpus='0',deadline='inf',job='6900',restart='0',stop_seconds=None);out=io.StringIO()
    with keep_affinity(),contextlib.redirect_stdout(out),mock.patch.object(L,'claim',interleaved),mock.patch.object(L.subprocess,'Popen',popen):rc=L.cmd_lane(args)
    assert not launched and L.failure_counts(d)=={idx:2}and not L.claim_path(d,idx).exists()and rc==0,(launched,L.failure_counts(d),out.getvalue()[-500:])
    assert f'index {idx} skipped: 2 failure records'in out.getvalue()and 'rechecked under its claim'in out.getvalue(),out.getvalue()[-500:]
    assert L.index_failures(d,idx)==2 and L.index_failures(d,idx+1)==0
    ok('lane_failure_limit_rechecked_under_the_claim_stale_snapshot_X13')

FAKE_SSH=r'''import json,os,re,subprocess,sys
e=os.environ;a=sys.argv[1:];root=e['FAKE_SITES']
open(e['FAKE_LOG'],'a').write(json.dumps({'cmd':'ssh','args':a})+'\n')
if a[:1]==['-O']:print('Master running (pid=1)',file=sys.stderr);sys.exit(0)
if a[:1]==['-T']:a=a[1:]
host,cmd=a[0],' '.join(a[1:])
cmd=re.sub(r'~/|/mnt/beegfs/|/expanse/',lambda m:f'{root}/{host}'+('/home/'if m.group(0)=='~/'else m.group(0)),cmd)
mode=e.get('FAKE_INJECT')  # a concurrent `seeds.py add` on symmetry while Expanse merges: once, or every time
if mode and host=='expanse'and ' merge 'in cmd:
    f=root+'/injected';k=int(open(f).read())if os.path.exists(f)else 0
    if mode=='always'or k==0:
        open(f,'w').write(str(k+1))
        subprocess.run([sys.executable,'-B',e['FAKE_SEEDS_TOOL'],'add','--seed',str(700001+k),'--label',f'concurrent symmetry add {k+1}',
                        '--log',f'{root}/symmetry/mnt/beegfs/zzheng1/c8-d2/forbidden_seeds.json'],check=True,stdout=subprocess.DEVNULL)
sys.exit(subprocess.run(['bash','-c',cmd]).returncode)
'''
FAKE_SCP=r'''import json,os,shutil,sys
e=os.environ;a=[x for x in sys.argv[1:]if x!='-q'];root=e['FAKE_SITES']
open(e['FAKE_LOG'],'a').write(json.dumps({'cmd':'scp','args':a})+'\n')
def loc(x):
    if ':'in x and not x.startswith('/'):h,q=x.split(':',1);return f'{root}/{h}{q}'
    return x
src,dst=map(loc,a);shutil.copyfile(src,dst)
'''

def test_seedsync(E):
    """X21 (S6-F-01): benchmarks/.../stage5/scripts/seedsync.sh on fake ssh/scp (each site a directory tree; remote
    commands run locally with the site paths mapped). Symmetry, Expanse and the package mirror each hold a seed the
    others lack, and a seed is added on symmetry while the sync runs (after its snapshot): the script merges the union of
    all three logs until a snapshot of both logs and the mirror hold the same seeds, then exits 0. With an addition on
    every round the logs never agree and the script exits 1 after C8_SEEDSYNC_ROUNDS rounds, naming what each lacks."""
    sd=E.M.seeds;script=ROOT/'benchmarks/symmetry_2026-10-c8/stage5/scripts/seedsync.sh';results={}
    for case,inject,rounds,code in (('converges','once','5',0),('diverges','always','2',1)):
        t=E.td/f'seedsync_{case}';sites=t/'sites';pkg=t/'pkg';fb=t/'fakebin';fb.mkdir(parents=True)
        for name,src in (('ssh',FAKE_SSH),('scp',FAKE_SCP)):(fb/name).write_text(f'#!{PY}\n'+src);(fb/name).chmod(0o755)
        (fb/'python3').write_text(f'#!/bin/bash\nexec {PY} "$@"\n');(fb/'python3').chmod(0o755)
        sym=sites/'symmetry/mnt/beegfs/zzheng1/c8-d2/forbidden_seeds.json';xd=sites/'expanse/expanse/lustre/scratch/zzheng8/temp_project/c8d2'
        exp=xd/'forbidden_seeds.json';mirror=pkg/'designs/forbidden_seeds.json'
        for tools in (sites/'symmetry/mnt/beegfs/zzheng1/c8d2/pkg/5d7586e9f1ab/tools',xd/'work/s5sym-seeds-5d7586e9f1ab/tools',pkg/'tools'):
            tools.mkdir(parents=True)
            for f in ('seeds.py','common.py'):shutil.copy2(E.pkg/'tools'/f,tools/f)
        for h,f in (('symmetry','env.sh'),('expanse','env_expanse.sh')):(sites/h/'home/c8d2').mkdir(parents=True);(sites/h/'home/c8d2'/f).write_text('')
        sp=pkg/'benchmarks/symmetry_2026-10-c8/stage5/scripts';sp.mkdir(parents=True);shutil.copy2(script,sp/'seedsync.sh');(sp.parent/'seeds').mkdir()
        for log,seeds in ((sym,(11,22)),(exp,(22,33)),(mirror,(22,44))):
            log.parent.mkdir(parents=True,exist_ok=True)
            for s_ in seeds:sd.add(log,s_,f'{log.parent.name} seed {s_}')
        env={**os.environ,'PATH':f'{fb}:{os.environ["PATH"]}','FAKE_SITES':str(sites),'FAKE_LOG':str(t/'fake.log'),'FAKE_SEEDS_TOOL':str(E.pkg/'tools/seeds.py'),
             'FAKE_INJECT':inject,'C8_SEEDSYNC_PYTHON':PY,'C8_SEEDSYNC_ROUNDS':rounds,'TMPDIR':str(t),'PYTHONDONTWRITEBYTECODE':'1'}
        cp=subprocess.run(['bash',str(sp/'seedsync.sh'),'lbl'],capture_output=True,text=True,env=env,timeout=600)
        sets=[{e_['seed']for e_ in sd.read_log(f)['seeds']}for f in (sym,exp,mirror)]
        assert cp.returncode==code,(case,cp.returncode,cp.stdout[-800:],cp.stderr[-800:])
        if code==0:
            assert sets[0]==sets[1]==sets[2]=={11,22,33,44,700001},(case,sets)
            assert 'equal sets: True'in cp.stdout and (pkg/'benchmarks/symmetry_2026-10-c8/stage5/seeds/lbl_symmetry.json').exists()
            assert {e_['seed']for e_ in sd.read_log(pkg/'benchmarks/symmetry_2026-10-c8/stage5/seeds/lbl_expanse.json')['seeds']}==sets[1]
        else:
            assert {11,22,33,44}<=sets[0]&sets[1]&sets[2]and not sets[0]==sets[1]==sets[2],(case,sets)
            assert 'still differ'in cp.stderr and 'lacks'in cp.stdout,(cp.stdout[-600:],cp.stderr[-400:])
        assert not list(t.glob('c8d2_seedsync.*')),list(t.glob('c8d2_seedsync.*'))  # the temporary directory is removed
        results[case]={'exit':cp.returncode,'seeds':[len(s_)for s_ in sets]}
    ok('seedsync_union_of_three_logs_concurrent_additions_nonzero_unless_equal_X21',**results)

# ================================================================ Stage-6 fix round 2, G2 (Y2, Y6, Y7, Y8, Y10, Y12, Y13)
# Each group fails on 2ae3db7 (the tools before the fix) and passes after it.
OMP_DIRTY={'OMP_THREAD_LIMIT':'1','OMP_DYNAMIC':'true','OMP_NUM_THREADS':'7','OMP_PROC_BIND':'spread','OMP_PLACES':'threads','GOMP_SPINCOUNT':'0','KMP_AFFINITY':'compact'}
# prepended to the fake worker: one JSON line per invocation with its arguments and every OpenMP control it was given
ENV_DUMP=("import json as _j,os as _o,sys as _s\n"
          "if _o.environ.get('C8_TEST_ENV_LOG'):open(_o.environ['C8_TEST_ENV_LOG'],'a').write(_j.dumps({'argv':_s.argv[1:],"
          "'omp':{k:v for k,v in _o.environ.items()if k.startswith(('OMP_','GOMP_','KMP_'))}})+'\\n')\n")
def omp_of(e:dict)->dict:return {k:v for k,v in e.items()if k.startswith(('OMP_','GOMP_','KMP_'))}
def omp_want(t)->dict:return {'OMP_NUM_THREADS':str(t),'OMP_DYNAMIC':'FALSE','OMP_PROC_BIND':'close','OMP_PLACES':'cores'}
def tools_module(E,name:str):
    """A tool of the package copy imported in-process (it shares the copy's common module with E.M)."""
    sys.modules.pop(name,None)
    if str(E.pkg/'tools')not in sys.path:sys.path.insert(0,str(E.pkg/'tools'))
    return __import__(name)

def test_omp_env(E):
    """Y2 (S6A2-02, S6-C-R2-02): common.omp_child_env drops every inherited OMP_*, GOMP_* and KMP_* control
    (OMP_THREAD_LIMIT=1, OMP_DYNAMIC=true, OMP_NUM_THREADS, GOMP_SPINCOUNT, KMP_AFFINITY, ...) and sets the requested
    team, OMP_DYNAMIC=FALSE and close binding on cores; benchkit.omp_env (P4 lane shapes, profiles) is the same. With
    all those controls inherited, the native worker of every entry point receives exactly the controlled environment
    at its requested width: production.py run (direct), slurm/run_array.sh, a lane (lanes.py lane, width 2) and
    tools/sweep.py (process slots of 2); the claim names the controls it did not pass on."""
    C=E.M.common;n=0
    # every entry point, from a package copy whose worker logs the OpenMP controls it receives
    P=make_package(E.td,name='pkg_ompenv');w=P/'bin/c8d2_gmp';w.write_text(FAKE_SHEBANG+ENV_DUMP+(ROOT/'tests/fake_worker.py').read_text());w.chmod(0o755)
    fx=P/'tests/fixtures/inputs_mini';base={'C8_INPUTS':str(fx),**OMP_DIRTY}
    cm=E.td/'cm_ompenv.json';cm.write_text(json.dumps(cost_model_for(E,None,lambda c,s,L,r:2e-5*(1+r['id']%3))))
    d=E.td/'ompenv';tool(P,'production.py','plan',d,'--seed',SEED+110,'--threads',2,'--checkpoint-tasks',8,'--pilot','--points',64,'--replicates',2,'--test-graphs',1,
                         '--cost-model',cm,'--index-hours',0.002,env=base)
    jobs=manifest(d)['jobs'];assert len(jobs)>=4,len(jobs)
    logs={};outs={}
    def native(name):
        recs=[json.loads(l)for l in logs[name].read_text().splitlines()]if logs[name].exists()else[]
        return [r for r in recs if len(r['argv'])==11]
    # direct
    logs['direct']=E.td/'ompenv_direct.jsonl';scr=E.td/'ompenv_scr';scr.mkdir()
    cp=tool(P,'production.py','run',d,'--index',jobs[0]['id'],'--threads',2,'--scratch',scr,env={**base,'C8_TEST_ENV_LOG':str(logs['direct'])});outs['direct']=cp.stdout
    # slurm/run_array.sh (array element 0 at the offset of index 1)
    logs['array']=E.td/'ompenv_array.jsonl'
    cp=subprocess.run(['bash',str(P/'slurm/run_array.sh')],capture_output=True,text=True,
                      env={**os.environ,**base,'C8_TEST_ENV_LOG':str(logs['array']),'SLURM_ARRAY_TASK_ID':'0','C8_INDEX_OFFSET':str(jobs[1]['id']),'C8_PACKAGE':str(P),
                           'C8_RUN':str(d),'C8_PYTHON':PY,'SLURM_TMPDIR':str(scr),'SLURM_CPUS_PER_TASK':'2','PYTHONDONTWRITEBYTECODE':'1'})
    assert cp.returncode==0,cp.stderr[-800:]
    # one lane of 2 CPUs over a queue of two indices
    logs['lane']=E.td/'ompenv_lane.jsonl';E.M.lanes.write_queue(d,[(jobs[2]['id'],1.),(jobs[3]['id'],1.)])
    cp=tool(P,'lanes.py','lane',d,'--lane',0,'--cpus','0,1','--deadline','inf','--job','4310',env={**base,'C8_TEST_ENV_LOG':str(logs['lane'])})
    assert 'finished, 2 indices run'in cp.stdout,cp.stdout[-600:]
    # a sweep in slots of 2 (its own test-only campaign; every index, merge, cost model and calibration)
    logs['sweep']=E.td/'ompenv_sweep.jsonl';cal=E.td/'ompenv_cal.json';shutil.copy2(P/'tools/calibration.json',cal)
    cp=tool(P,'sweep.py',E.td/'ompenv_sweep','--seed',SEED+111,'--points',16,'--replicates',2,'--threads',2,'--procs',2,'--bootstrap-chunk',8,'--shards',1,'--merge-jobs',1,
            '--cost-model-out',E.td/'ompenv_cm_out.json','--calibration',cal,env={**base,'C8_TEST_ENV_LOG':str(logs['sweep'])})
    seen={}
    for name in ('direct','array','lane','sweep'):
        recs=native(name);assert recs,(name,'no native launch logged')
        bad=[(r['argv'][8],r['omp'])for r in recs if r['omp']!=omp_want(int(r['argv'][8]))or (name!='sweep'and r['argv'][8]!='2')]
        assert not bad,(name,bad[:3]);seen[name]=len(recs)
    assert 'not passed to the native worker (Y2)'in outs['direct']and 'OMP_THREAD_LIMIT=1'in outs['direct'],outs['direct'][-600:]
    # the helpers: common.omp_child_env and benchkit.omp_env (P4 lane shapes, profiles)
    bk=tools_module(E,'benchkit')
    with mock.patch.dict(os.environ,OMP_DIRTY):
        assert omp_of(bk.omp_env(8))==omp_want(8)and omp_of(bk.omp_env(8,base=dict(OMP_DIRTY)))==omp_want(8)
        assert omp_of(bk.omp_env(1,wait_policy='passive'))=={**omp_want(1),'OMP_WAIT_POLICY':'passive'}
        assert omp_of(C.omp_child_env(5))==omp_want(5)and C.omp_inherited()==dict(sorted(OMP_DIRTY.items()))
    e=C.omp_child_env(4,{**OMP_DIRTY,'PATH':'/bin','C8_X':'y'})
    assert omp_of(e)==omp_want(4)and e['PATH']=='/bin'and e['C8_X']=='y'and e['OPENBLAS_NUM_THREADS']=='1'and e['MKL_NUM_THREADS']=='1',e
    assert C.omp_child_env(2,{},'passive')['OMP_WAIT_POLICY']=='passive'and omp_of(C.omp_child_env(3,{}))==omp_want(3)
    for bad in (0,-2,True,1.5,'2'):
        try:C.omp_child_env(bad,{});raise AssertionError(f'team size {bad!r} accepted')
        except ValueError:n+=1
    ok('Y2_controlled_openmp_environment_every_native_launch_direct_array_lane_sweep_benchkit',launches=seen,refusals=n)

def test_omp_team(E):
    """Y2 (S6-C-R2-02): production.py run watches the OpenMP team of an ELF worker while it runs (common.TeamWatch,
    the /proc/<pid>/task count; here elf_kind and the count are stubbed, the worker is the fake one). The requested
    team seen: verdict 'verified', recorded in the checkpoint (runtime.omp_team) and the claim's log line. A worker that
    shows a smaller team (a serial run under an OpenMP limit) and computes (CPU time, stubbed) is stopped at the
    deadline and the claim refused with exit 64 (lanes release and stop): no checkpoint of the block, a failure log
    naming Y2, claim_io status 'omp team refused', the worker gone long before its natural end. One that waits past the
    deadline without CPU time (a stall before its first parallel region) is not stopped: it completes 'unverified' and
    is kept, as is a run that ends before the deadline without showing the team; a worker that is not ELF (the
    stand-in) is 'unavailable'."""
    p=E.M.prod;C=E.M.common;d=E.td/'omp_team';E.small(d,'--checkpoint-tasks',4,'--shards',1,seed=SEED+112);m=manifest(d);me=os.getpid()
    jobs=[j for j in m['jobs']];team={'n':2};cpu={'s':100.}
    def count(pid):return 1 if pid==me else team['n']
    def ck(j):return sorted((d/'groups'/j['group']/'checkpoints').glob(f's{j["shard"]:06d}_p*.json'))
    stub=lambda:(mock.patch.object(p,'elf_kind',lambda path:'dynamic',create=True),mock.patch.object(p,'fingerprint_problems',lambda fp,kind,cpu=None:[],create=True),
                 mock.patch.object(C,'proc_task_count',count,create=True),mock.patch.object(C,'proc_cpu_seconds',lambda pid:cpu['s'],create=True))
    # verified
    with contextlib.ExitStack()as st:
        for cm_ in stub():st.enter_context(cm_)
        r=E.run(d,jobs[0]['id']);t=json.loads(ck(jobs[0])[0].read_text())['runtime'].get('omp_team')or{}
        assert t['verdict']=='verified'and t['requested']==2 and t['observed']==2,t
        assert 'omp team verified: 2 of 2 threads'in r.stdout,r.stdout[-400:]
        # smaller: a serial team that computes (100 CPU-s), the worker sleeping 30 s; the deadline 0.5 s
        # W15's class (Stage-6 fix round 4, integration; G4's note): the 30 s fake worker is registered in an independent
        # cleanup scope (Owned) by the launch seam, so it is killed and reaped whatever fails; the seam also waits (stop
        # signals deferred, the team watch not started yet) until the worker runs, so the 0.5 s deadline never stops it
        # before its C8_FAKE_LOG line (before: under load, log.read_text() raised FileNotFoundError and the worker was
        # nobody's)
        team['n']=1;log=E.td/'omp_team_fake.log';kids=[]
        with Owned()as own:
            def hook(child):
                own.add(child);kids.append(child)
                assert fake_running(log,child.pid),('the fake native worker never started',child.pid)
            with mock.patch.object(C,'TEAM_DEADLINE_SECONDS',0.5,create=True),mock.patch.dict(os.environ,{'C8_FAKE_SLEEP':'30','C8_FAKE_LOG':str(log)}),\
                 mock.patch.object(p,'_after_launch',side_effect=hook):
                t0=time.time();r=E.run(d,jobs[1]['id'],expect=1);el=time.time()-t0
            assert r.returncode==64 and 'asked for an OpenMP team of 2 threads but showed at most 1'in r.stderr and el<20,(r.returncode,el,r.stderr[-600:])
            assert not ck(jobs[1])and '"status": "omp team refused"'in r.stdout,(ck(jobs[1]),r.stdout[-300:])
            fl=list((d/'groups'/jobs[1]['group']/'logs').glob('*.failure.*.log'));assert fl and 'C8 (Y2)'in fl[-1].read_text(),fl
            pid=json.loads(log.read_text().splitlines()[0])['pid'];assert kids and kids[0].pid==pid,(kids,pid)
            assert wait_for(lambda:not alive(pid),10)and kids[0].returncode is not None,'the worker still runs (or production did not reap it)'
        assert not own.killed,own.killed
        # unverified: the same serial team, a run shorter than the deadline
        r=E.run(d,jobs[1]['id']);t=json.loads(ck(jobs[1])[0].read_text())['runtime']['omp_team']
        assert t['verdict']=='unverified'and t['observed']==1,t
        # stalled: the serial count past the deadline without CPU time (a wait, not a computation): not stopped, kept
        cpu['s']=0.
        with mock.patch.object(C,'TEAM_DEADLINE_SECONDS',0.5,create=True),mock.patch.dict(os.environ,{'C8_FAKE_SLEEP':'1.5'}):
            t0=time.time();r=E.run(d,jobs[3]['id'],'--max-blocks',1);el3=time.time()-t0
        t=json.loads(ck(jobs[3])[0].read_text())['runtime']['omp_team']
        assert t['verdict']=='unverified'and t['cpu_seconds']==0. and t['seconds']>=1.4 and el3>=1.4 and 'omp team unverified'in r.stdout,(t,el3)
    # unavailable: the stand-in worker is no ELF executable; nothing is watched
    E.run(d,jobs[2]['id']);t=json.loads(ck(jobs[2])[0].read_text())['runtime']['omp_team'];assert t['verdict']=='unavailable'and t['observed']is None,t
    assert p.elf_kind(E.pkg/'bin/c8d2_gmp')is None
    # post hoc: status counts the recorded teams of the committed blocks (JSON and text)
    r=cli(p,'status',d,'--json',expect=None);st=json.loads(r.stdout);want={'verified':len(ck(jobs[0])),'unverified':len(ck(jobs[1]))+len(ck(jobs[3])),'unavailable':len(ck(jobs[2]))}
    assert st['omp_teams']==want and st['groups'][jobs[0]['group']]['omp_teams']=={'verified':want['verified']},(st['omp_teams'],want)
    assert 'omp teams of the committed blocks (Y2'in cli(p,'status',d,expect=None).stdout
    ok('Y2_live_team_check_verified_smaller_refused_64_unverified_unavailable',deadline_stop_seconds=round(el,2))

def bench_block(part,threads,team,t0=0.):
    return {'part':part,'tasks':4,'cost_model_seconds':1.,'t_start':t0,'t_native_start':t0,'t_end':t0+2.,'stage_seconds':.1,'stage_bytes':10,'graphs':1,'native_wall_seconds':1.5,
            'points':64,'quad':0,'mp':0,'task_seconds':2.*threads,'load_seconds':.1,'integration_seconds':1.,'threads':threads,'openmp_efficiency':1.,'max_rss_kb':100,
            'numa_kb_max':None,'numa_kb_last':None,'rows':[[part,1,'h']],'team':team}

def test_bench_team(E):
    """Y2 (S6A2-02), the P4 side: benchkit.run_watched starts a worker in omp_env (the controlled environment) and
    watches its team: one that shows the requested team is 'verified'; one that does not within the deadline and
    computes (CPU time, stubbed) is stopped ('smaller', long before its natural end); one that waits past the deadline
    without CPU time completes 'unverified'; without the check 'unavailable'. benchkit.team_errors and
    benchmark.shape_summary make a shape with any block not 'verified' an error (a measurement whose team is unknown
    or smaller is not accepted), and record team_sizes_verified; without the check (a stand-in worker) no error."""
    C=E.M.common;bk=tools_module(E,'benchkit');bm=tools_module(E,'benchmark');me=os.getpid();team={'n':4};cpu={'s':100.}
    with mock.patch.dict(os.environ,OMP_DIRTY):assert omp_of(bk.omp_env(4))==omp_want(4),omp_of(bk.omp_env(4))  # the P4 workers' environment
    sl=E.td/'bench_sleeper.py';sl.write_text('import os,sys,time\nopen(sys.argv[1],"w").write(os.environ.get("OMP_THREAD_LIMIT","-"));time.sleep(float(sys.argv[2]))\n')
    def count(pid):return 1 if pid==me else team['n']
    with mock.patch.object(C,'proc_task_count',count),mock.patch.object(C,'proc_cpu_seconds',lambda pid:cpu['s'],create=True),mock.patch.dict(os.environ,OMP_DIRTY):
        w=bk.run_watched([PY,sl,E.td/'bench_env1.txt',0.3],4,E.td/'bench1.log',True,deadline=5,poll=.05)
        assert w['returncode']==0 and w['team']['verdict']=='verified'and w['team']['observed']==4 and (E.td/'bench_env1.txt').read_text()=='-',w
        team['n']=1;t0=time.time();w=bk.run_watched([PY,sl,E.td/'bench_env2.txt',30],4,E.td/'bench2.log',True,deadline=.4,poll=.05);el=time.time()-t0
        assert w['team']['verdict']=='smaller'and w['returncode']!=0 and el<15 and w['team']['cpu_seconds']==100.,(w,el)
        assert 'showed at most 1 after 0.4 s, with 100.0 s of CPU time'in C.team_message(w['team']),C.team_message(w['team'])
        cpu['s']=0.;w=bk.run_watched([PY,sl,E.td/'bench_env4.txt',1.2],4,E.td/'bench4.log',True,deadline=.4,poll=.05)  # a wait, not a computation
        assert w['team']['verdict']=='unverified'and w['returncode']==0 and w['team']['seconds']>=1.1,w
        w=bk.run_watched([PY,sl,E.td/'bench_env3.txt',0.1],4,E.td/'bench3.log',False,poll=.05);assert w['team']['verdict']=='unavailable'and w['returncode']==0,w
    good,short=bench_block('x',4,{'verdict':'verified','observed':4,'requested':4}),bench_block('x',4,{'verdict':'unverified','observed':1,'requested':4},1.)
    assert bk.team_errors([good],True)==[]and len(bk.team_errors([good,short],True))==1 and bk.team_errors([good,short],False)==[]
    cores=[(0,0,0),(0,0,1),(0,0,2),(0,0,3)]
    s=bm.shape_summary(1,4,[{'lane':0,'blocks':[good,short],'error':None}],cores,[[0,1,2,3]],{},3.,True)
    assert s['errors']and 'unverified'in s['errors'][0]and s['team_sizes_verified']is False,s['errors']
    s=bm.shape_summary(1,4,[{'lane':0,'blocks':[good],'error':None}],cores,[[0,1,2,3]],{},3.,True);assert not s['errors']and s['team_sizes_verified']is True
    s=bm.shape_summary(1,4,[{'lane':0,'blocks':[good,short],'error':None}],cores,[[0,1,2,3]],{},3.,False);assert not s['errors']
    assert bk.team_check(E.pkg/'bin/c8d2_gmp')is False
    ok('Y2_p4_team_watched_smaller_stopped_shape_refused_unless_verified',deadline_stop_seconds=round(el,2))

def cgroup_tree(td:Path,name:str,lines:list,limits:dict)->Path:
    """A fake /proc/self/cgroup and /sys/fs/cgroup tree: limits {relative dir: (file name, value)}."""
    root=td/f'cgroup_{name}';(root/'proc/self').mkdir(parents=True);(root/'proc/self/cgroup').write_text(''.join(l+'\n'for l in lines))
    for rel,(fname,val)in limits.items():g=root/'sys/fs/cgroup'/rel;g.mkdir(parents=True,exist_ok=True);(g/fname).write_text(f'{val}\n')
    return root

def test_cgroup_minimum(E):
    """Y7 (S6-C-R2-03): lanes.cgroup_memory_limit is the smallest finite limit over the process's cgroup and every
    visible ancestor (v2 memory.max, v1 memory.limit_in_bytes, both in a hybrid), not the first finite one: a looser
    step limit under a tighter job limit, unlimited ('max', v1's 2^63-4096) intermediates, a tighter grandparent; the
    memory guard then sizes the lanes by the binding limit (8 lanes of 4 GiB under a 16 GiB job: 3, not 8). A line of
    /proc/self/cgroup that is no 'id:controllers:path' entry is skipped, not a crash of the lane."""
    L=E.M.lanes;G=2**30;V1MAX=9223372036854771712;cases={
        'step_looser':(['0::/slurm/job_1/step_0'],{'slurm/job_1/step_0':('memory.max',64*G),'slurm/job_1':('memory.max',16*G),'slurm':('memory.max','max')},16*G),
        'unlimited_between':(['0::/slurm/job_1/step_0'],{'slurm/job_1/step_0':('memory.max','max'),'slurm/job_1':('memory.max','max'),'slurm':('memory.max',32*G)},32*G),
        'grandparent':(['0::/slurm/job_1/step_0'],{'slurm/job_1/step_0':('memory.max',64*G),'slurm/job_1':('memory.max','max'),'slurm':('memory.max',8*G)},8*G),
        'none':(['0::/slurm/job_1/step_0'],{'slurm/job_1/step_0':('memory.max','max'),'slurm/job_1':('memory.max','max')},None),
        'v1':(['7:memory:/slurm/uid_5/job_1/step_0','3:cpu,cpuacct:/slurm/uid_5/job_1'],{'memory/slurm/uid_5/job_1/step_0':('memory.limit_in_bytes',V1MAX),
               'memory/slurm/uid_5/job_1':('memory.limit_in_bytes',20*G),'memory/slurm/uid_5':('memory.limit_in_bytes',10*G)},10*G),
        'hybrid':(['0::/a/b','4:memory:/c/d'],{'a/b':('memory.max',12*G),'a':('memory.max','max'),'memory/c/d':('memory.limit_in_bytes',V1MAX),'memory/c':('memory.limit_in_bytes',6*G)},6*G),
        'malformed_line':(['garbage','0::/slurm/job_1/step_0'],{'slurm/job_1/step_0':('memory.max',64*G),'slurm/job_1':('memory.max',16*G)},16*G)}
    got={}
    for name,(lines,limits,want)in cases.items():
        root=cgroup_tree(E.td,name,lines,limits)
        with mock.patch.dict(os.environ,{'C8_SYSFS':str(root/'sys'),'C8_PROC':str(root/'proc')}):
            v=L.cgroup_memory_limit();got[name]=v;assert v==want,(name,v,want)
            if name=='step_looser':assert L.memory_limit({})==(16*G,'cgroup')and L.memory_guard(8,4*G,v)==3
    ok('Y7_cgroup_limit_minimum_over_all_ancestors',limits_gib={k:(v/G if v else None)for k,v in got.items()})

def elf_bytes(cls:int=2,interp:bool=True,interp_path:str|None=None)->bytes:
    """A minimal ELF header with a PT_LOAD and (interp) a PT_INTERP program header; interp_path: its string."""
    types=[1,3]if interp else[1];s=(interp_path.encode()+b'\0')if interp_path else b'';off=64+56*len(types)
    ph=b''.join(struct.pack('<II6Q',t,0,off if t==3 and s else 0,0,0,len(s)if t==3 else 0,0,0)for t in types)
    head=b'\x7fELF'+bytes([cls,1,1,0])+bytes(8)+struct.pack('<HHIQQQIHHHHHH',2,62,1,0,64,0,0,64,56,len(types),0,0,0)
    return head+ph+s

def test_fingerprint_complete(E):
    """Y6 (S6-C-R2-01): common.elf_kind classifies the worker (dynamic, static, other ELF, not ELF); common.fingerprint_problems
    refuses, for a dynamic ELF worker, a failed or timed-out ldd probe, an empty or partial library map (a library not
    resolved to a hashed file) and an unhashed interpreter, and accepts a complete one, a static ELF and a non-ELF
    worker (macOS, the test stand-ins). production.py run of a (stubbed) dynamic ELF worker whose probe failed, or gave
    a partial map, stops with 64 before any pin is published or block run (no runtime_identity.json, no
    cpu_vendor.json, no checkpoint; claim_io 'incomplete runtime fingerprint'); with a complete fingerprint it runs and
    pins ldd 'ok'. The kernel's virtual DSO, which older glibc's ldd lists as 'linux-vdso.so.1 =>  (0x...)', is no
    unresolved library: common.fingerprint of an ELF worker with that ldd output (stubbed) is complete, and the same
    output with a 'not found' library is not."""
    C=E.M.common;p=E.M.prod;n=0;t=E.td/'elf';t.mkdir()
    lib=lambda path,sha:{'path':path,'resolved':path+'.1','sha256':sha}
    fp={'host':'n1','cpu_model':'X','glibc':'glibc 2.28','ldd_error':None,'slurm':{},'interpreter':{'path':'/lib64/ld.so','resolved':'/lib64/ld-2.28.so','sha256':'1'*64},
        'libraries':{'libgmp.so.10':lib('/usr/lib64/libgmp.so.10','2'*64),'libc.so.6':lib('/lib64/libc.so.6','3'*64)},'libgmp':None,'libquadmath':None,'libgomp':None}
    edits={'ldd failed':lambda x:x.update(ldd_error='Command ldd timed out after 120 seconds',libraries={}),
           'ldd failed, partial map':lambda x:x.update(ldd_error='ldd: exited with 1'),
           'not found':lambda x:x['libraries'].update({'libquadmath.so.0':{'path':None,'resolved':None,'sha256':None,'note':'not found'}}),
           'no libraries':lambda x:x.update(libraries={}),'no interpreter':lambda x:x.update(interpreter=None),
           'interpreter unhashed':lambda x:x['interpreter'].update(sha256=None)}
    # the claim: a dynamic ELF worker (stubbed) with a failed probe, then a partial map, refuses before anything
    d=E.td/'fpc';E.small(d,'--checkpoint-tasks',4,'--shards',1,seed=SEED+113);m=manifest(d);j=m['jobs'][0];real=p.fingerprint
    def faked(edit):
        def fake(exe,counter=None,identity=None):
            x=real(exe,counter,identity);x.update(json.loads(json.dumps({k:fp[k]for k in ('glibc','ldd_error','interpreter','libraries')})));edit(x);return x
        return fake
    for name in ('ldd failed','not found'):
        with mock.patch.object(p,'elf_kind',lambda path:'dynamic',create=True),mock.patch.object(p,'fingerprint',faked(edits[name])):r=E.run(d,j['id'],expect=1)
        assert r.returncode==64 and 'runtime fingerprint of the worker on this node'in r.stderr and 'incomplete'in r.stderr,(name,r.returncode,r.stderr[-500:])
        assert '"status": "incomplete runtime fingerprint"'in r.stdout and not (d/'runtime_identity.json').exists()and not (d/'cpu_vendor.json').exists(),name
        assert not list((d/'groups'/j['group']).glob('checkpoints/*.json')),name;n+=1
    with mock.patch.object(p,'elf_kind',lambda path:'dynamic',create=True),mock.patch.object(p,'fingerprint',faked(lambda x:None)):E.run(d,j['id'])
    pin=json.loads((d/'runtime_identity.json').read_text());assert pin['identity']['ldd']=='ok'and pin['identity']['interpreter_sha256']=='1'*64,pin
    # the helpers
    for name,data,want in (('dyn',elf_bytes(),'dynamic'),('static',elf_bytes(interp=False),'static'),('elf32',elf_bytes(cls=1),'elf'),('script',b'#!/bin/sh\necho\n',None),
                           ('short',b'\x7fELF\x02\x01',  'elf'),('macho',bytes.fromhex('cffaedfe07000001')+bytes(56),None)):
        (t/name).write_bytes(data);assert C.elf_kind(t/name)==want,(name,C.elf_kind(t/name),want)
    if sys.platform.startswith('linux'):assert C.elf_kind(Path(os.path.realpath(sys.executable)))in('dynamic','static')
    assert C.fingerprint_problems(fp,'dynamic')==[]and C.fingerprint_problems(fp,'elf')
    with mock.patch.object(C.sys,'platform','linux'):  # the F5 vendor: the uname fallback is no vendor on Linux
        assert C.fingerprint_problems(fp,'dynamic',{'vendor':f'linux-{os.uname().machine}'})==['the CPU vendor could not be read from /proc/cpuinfo']
        assert C.fingerprint_problems(fp,'dynamic',{'vendor':'AuthenticAMD'})==[]and C.fingerprint_problems(fp,None,{'vendor':None})==[];n+=1
    for name,f in edits.items():
        y=json.loads(json.dumps(fp));f(y);pr=C.fingerprint_problems(y,'dynamic');assert pr,name;n+=1
        assert C.fingerprint_problems(y,'static')==[]and C.fingerprint_problems(y,None)==[],name
    vd={'path':None,'resolved':None,'sha256':None,'note':'(0x00007ffd5a1f2000)'}
    y=json.loads(json.dumps(fp));y['libraries'].update({'linux-vdso.so.1':vd,'linux-gate.so.1':dict(vd,note='(0xf7f2e000)')});assert C.fingerprint_problems(y,'dynamic')==[],y
    for note in ('(0x)','(0xzz)','not found','',None):
        y=json.loads(json.dumps(fp));y['libraries']['linux-vdso.so.1']=dict(vd,note=note);assert C.fingerprint_problems(y,'dynamic'),note;n+=1
    # end to end: common.fingerprint parses an older glibc's ldd output (stubbed) for an ELF worker whose interpreter exists
    (t/'ld-linux-x86-64.so.2').write_bytes(b'ld.so');(t/'libgmp.so.10').write_bytes(b'gmp');(t/'libc.so.6').write_bytes(b'libc')
    exe=t/'worker';exe.write_bytes(elf_bytes(interp_path=str(t/'ld-linux-x86-64.so.2')));real_run=subprocess.run
    for name,extra,want in (('old glibc vdso','',[]),('not found',f'\tlibquadmath.so.0 => not found\n',['library libquadmath.so.0']) ):
        out=(f'\tlinux-vdso.so.1 =>  (0x00007ffd5a1f2000)\n\tlibgmp.so.10 => {t}/libgmp.so.10 (0x00007f2b1c000000)\n{extra}'
             f'\tlibc.so.6 => {t}/libc.so.6 (0x00007f2b1b000000)\n\t{t}/ld-linux-x86-64.so.2 (0x00007f2b1d000000)\n').encode()
        def fake_run(cmd,*a_,**k_):
            if list(cmd)[:1]==['ldd']:return subprocess.CompletedProcess(cmd,0,out,None)
            return real_run(cmd,*a_,**k_)
        with mock.patch.object(C.subprocess,'run',fake_run):f=C.fingerprint(exe)
        assert f['ldd_error']is None and f['interpreter']['sha256']==digest(t/'ld-linux-x86-64.so.2')and f['libraries']['libgmp.so.10']['sha256']==digest(t/'libgmp.so.10'),f
        assert C.elf_kind(exe)=='dynamic'and [x[:len(w)]for x,w in zip(C.fingerprint_problems(f,'dynamic'),want)]==want and len(C.fingerprint_problems(f,'dynamic'))==len(want),(name,C.fingerprint_problems(f,'dynamic'))
    ok('Y6_incomplete_runtime_fingerprint_refused_before_any_pin_or_block',refusals=n)

def test_first_fingerprint(E):
    """Y8 (S6E-R2-01): without runtime_identity.json both merges take the campaign's runtime identity from its first
    checkpoint; a first checkpoint whose fingerprint is missing, null, lacks its fields or has a malformed library map
    makes the serial merge and the parallel merge (--jobs 1 and 2) refuse (naming it) instead of disabling the check
    while a later checkpoint carries a conflicting library stack. With the pin, a checkpoint with a malformed fingerprint
    is refused as carrying no runtime identity (not a crash). A merge of the repaired campaign succeeds."""
    p=E.M.prod;d=E.td/'fpfirst';E.small(d,'--checkpoint-tasks',4,'--shards',1,seed=SEED+114);m=manifest(d);E.run_all(d)
    j=m['jobs'][0];g=j['group'];cdir=d/'groups'/g/'checkpoints';first=cdir/f'{p.block_name(j["shard"],0)}.json';later=cdir/f'{p.block_name(j["shard"],1)}.json'
    assert first.exists()and later.exists(),sorted(x.name for x in cdir.iterdir())
    f0,l0=first.read_bytes(),later.read_bytes();pin=(d/'runtime_identity.json').read_bytes();(d/'runtime_identity.json').unlink()
    def edit(path,orig,fn):x=json.loads(orig);fn(x['runtime']);path.write_text(json.dumps(x))
    edit(later,l0,lambda rt:rt['fingerprint']['libraries'].update({'libgmp.so.10':{'path':'/x/libgmp.so.10','resolved':'/x/libgmp.so.10','sha256':'f'*64}}))
    n=0
    for name,fn in (('missing',lambda rt:rt.pop('fingerprint')),('null',lambda rt:rt.update(fingerprint=None)),('fields',lambda rt:rt.update(fingerprint={'host':'n1'})),
                    ('library map',lambda rt:rt['fingerprint'].update(libraries=['libgmp.so.10']))):
        edit(first,f0,fn)
        for args in (('--jobs',1),('--jobs',2),('--serial',)):
            r=cli(p,'merge',d,'--group',g,*args,expect=1)
            assert 'cannot be established'in r.stderr and first.name in r.stderr and not (d/'groups'/g/'merged.json').exists(),(name,args,r.stderr[-500:]);n+=1
    # with the pin: a malformed fingerprint is refused as carrying no identity (serial and parallel merges, run-skip)
    first.write_bytes(f0);later.write_bytes(l0);(d/'runtime_identity.json').write_bytes(pin)
    edit(later,l0,lambda rt:rt['fingerprint'].update(libraries=['libgmp.so.10']))
    for args in (('--jobs',2),('--serial',)):
        r=cli(p,'merge',d,'--group',g,*args,expect=1);assert 'carries no runtime identity'in r.stderr and 'AttributeError'not in r.stderr,(args,r.stderr[-500:]);n+=1
    r=E.run(d,j['id'],expect=1);assert 'carries no runtime identity'in r.stderr,r.stderr[-400:];n+=1
    later.write_bytes(l0);cli(p,'merge',d,'--group',g)
    ok('Y8_first_checkpoint_without_fingerprint_refused_by_both_merges',refusals=n)

def bundle_with(E,dest:Path,reps,test_only=True)->Path:
    """synth_bundle with a replicates map (an int for every (sector, L), or a dict) and test_only, digests consistent."""
    B=synth_bundle(E,dest);dj=json.loads((B/'design.json').read_text())
    dj['replicates']=reps if isinstance(reps,dict)else{k:reps for k in dj['replicates']};(B/'design.json').write_text(json.dumps(dj))
    meta=json.loads((B/'design_meta.json').read_text());meta.update(design_sha256=digest(B/'design.json'),test_only=test_only)
    (B/'design_meta.json').write_text(json.dumps(meta,indent=1)+'\n');return B

def test_bundle_replicates(E):
    """Y10 (S6D-R2-02), production.py side: plan --design validates the bundle's replicates before anything is read or
    created: a production (non-test) bundle's must be powers of two in [32, 128] (16, 48 and 256 refused; 32 accepted),
    any bundle's integers of at least 2 (a --test-only bundle of 1 replicate refused, of 2 accepted), exactly the twelve
    (sector, L) entries (a missing one and a boolean or float value refused). Nothing is created by a refusal."""
    keys=[f'{s}_L{L}'for s in('free','power')for L in range(3,9)];n=0;seed=SEED+115
    def plan(B,expect):
        nonlocal seed;seed+=1;d=E.td/f'reps_{B.name}'
        r=E.plan(d,'--design',B,'--test-graphs',1,'--bootstrap-chunk',4,'--shards',1,seed=seed,expect=expect);return d,r
    for name,reps,test,needle in (('t1',1,True,'fewer than 2'),('p16',16,False,'production bounds'),('p48',48,False,'production bounds'),('p256',256,False,'production bounds'),
                                  ('missing',{k:2 for k in keys[1:]},True,'must list exactly'),('bool',{**{k:2 for k in keys},keys[0]:True},True,'not an integer'),
                                  ('float',{**{k:2 for k in keys},keys[3]:2.0},True,'not an integer'),('p32one',{**{k:32 for k in keys},keys[5]:16},False,'production bounds')):
        B=bundle_with(E,E.td/f'repsB_{name}',reps,test);d,r=plan(B,1)
        assert needle in r.stderr and 'Y10'in r.stderr and gone(d),(name,r.stderr[-400:]);n+=1
    for name,reps,test in (('t2',2,True),('p32',32,False)):
        B=bundle_with(E,E.td/f'repsB_{name}',reps,test);d,_=plan(B,0);mm=manifest(d)
        assert mm['design']['r']=={k:reps for k in keys}and all(config(d,g['name'])['replicates']==reps for g in mm['groups']),name
    ok('Y10_plan_validates_bundle_replicates_production_bounds_test_only_floor_2',refusals=n)

def test_sweep_resume_identity(E):
    """Y12 (S6D-R2-04): an existing sweep campaign is continued only with the arguments it was planned with: a rerun with
    another rates identity (default -> map, map -> default, map -> another map), another bootstrap chunk, shard count or
    checkpoint size is refused naming the difference, and the campaign is unchanged; the same arguments continue."""
    rf1,rf2=E.td/'sw_rates1.json',E.td/'sw_rates2.json';rf1.write_text(json.dumps(rates_doc(E)));rf2.write_text(json.dumps(rates_doc(E,'.7','.9')))
    appr=('--approved-numerics-change','user approval 2026-10-03 (test)');n=0
    base=lambda seed:('--seed',seed,'--points',16,'--replicates',2,'--threads',2,'--bootstrap-chunk',8,'--shards',2,'--plan-only')
    def sweep(d,*args,check=True):return tool(E.pkg,'sweep.py',d,*args,check=check)
    dd=E.td/'swr_default';sweep(dd,*base(SEED+120));dm=E.td/'swr_map';sweep(dm,*base(SEED+121),'--rates',rf1,*appr)
    assert manifest(dm)['rates_identity']==digest(rf1)and manifest(dd)['rates_identity']=='default'
    for d,extra,needle in ((dd,('--rates',rf1,*appr),'rates_identity'),(dm,(),'rates_identity'),(dm,('--rates',rf2,*appr),'rates_identity'),
                           (dd,('--bootstrap-chunk',4),'bootstrap_chunk'),(dd,('--shards',3),'shards'),(dd,('--checkpoint-tasks',64),'checkpoint_tasks')):
        before=tree(d);args=list(base(SEED+120 if d==dd else SEED+121))
        for k in range(0,len(extra),2):
            if extra[k]in args:i=args.index(extra[k]);args[i+1]=extra[k+1]
            else:args+=[extra[k],extra[k+1]]
        cp=sweep(d,*args,check=False);assert cp.returncode and needle in cp.stderr and 'Y12'in cp.stderr and tree(d)==before,(d.name,extra,cp.stderr[-400:]);n+=1
    assert 'continuing the existing plan'in sweep(dd,*base(SEED+120)).stdout and 'continuing the existing plan'in sweep(dm,*base(SEED+121),'--rates',rf1,*appr).stdout
    ok('Y12_sweep_resume_requires_same_rates_identity_and_cost_basis',refusals=n)

def test_sweep_seed(E):
    """Y13 (S6R2-F-01): tools/sweep.py registers its base seed in the seed log (--seeds-log, default C8_SEEDS) right after
    the plan is published or validated, before any index runs: with --plan-only, and in a sweep whose every index fails
    (the seed is in the log although the sweep failed); a rerun finds it 'present' (no second entry), as does
    `seeds.py add RUN` after it (the same source). Inside a Slurm job without a seed log, or with a log that does not
    exist, the sweep is refused before anything is planned."""
    sd=E.M.seeds;log=E.td/'sweep_seeds.json';sd.add(log,1,'initial entry');n=0
    args=lambda seed:('--seed',seed,'--points',16,'--replicates',2,'--threads',2,'--bootstrap-chunk',8,'--shards',1)
    entries=lambda seed:[e for e in sd.read_log(log)['seeds']if e['seed']==seed]
    for name,env,needle in (('nolog',{'SLURM_JOB_ID':'9310'},'--seeds-log'),('missing',{'C8_SEEDS':str(E.td/'no_such_log.json')},'does not exist')):
        d=E.td/f'swseed_{name}';cp=tool(E.pkg,'sweep.py',d,*args(SEED+130),'--plan-only',env=env,check=False)
        assert cp.returncode and needle in cp.stderr and gone(d)and not entries(SEED+130),(name,cp.stderr[-300:]);n+=1
    d=E.td/'swseed_plan';cp=tool(E.pkg,'sweep.py',d,*args(SEED+131),'--plan-only',env={'C8_SEEDS':str(log)})
    assert [e['source']for e in entries(SEED+131)]==[str(d.resolve())]and 'added'in cp.stdout,cp.stdout[-300:]
    d=E.td/'swseed_fail';cp=tool(E.pkg,'sweep.py',d,*args(SEED+132),'--procs',2,'--seeds-log',log,env={'C8_FAKE_FAIL':'1'},check=False)
    assert cp.returncode and 'indices failed'in cp.stderr and [e['source']for e in entries(SEED+132)]==[str(d.resolve())],(cp.returncode,cp.stderr[-300:])
    cp=tool(E.pkg,'sweep.py',d,*args(SEED+132),'--plan-only',env={'C8_SEEDS':str(log)});assert 'present'in cp.stdout and len(entries(SEED+132))==1
    r=tool(E.pkg,'seeds.py','add',d,'--log',log);assert json.loads(r.stdout)['state']=='present'and len(entries(SEED+132))==1
    d=E.td/'swseed_local';cp=tool(E.pkg,'sweep.py',d,*args(SEED+133),'--plan-only');assert 'NOT registered'in cp.stdout and not entries(SEED+133)
    ok('Y13_sweep_registers_seed_before_any_index_runs',refusals=n)

def test_plan_seed(E):
    """The Y13 class for plans (S6R2-F-01): slurm/plan.sh adds the new campaign's base seed to $C8_SEEDS right after the
    plan, before its ledger registration and before any index can run (tools/seeds.py add RUN; the source is the
    campaign); without C8_SEEDS it plans and asks for the seed to be added by hand; a seed add that fails (a log that
    is not a seed log) still registers the plan job in the ledger, then exits with the add's status, naming the command."""
    sd=E.M.seeds;log=E.td/'plansh_seeds.json';sd.add(log,1,'initial entry');entries=lambda seed:[e for e in sd.read_log(log)['seeds']if e['seed']==seed]
    def plansh(d,seed,**env):
        return subprocess.run(['bash',str(E.pkg/'slurm/plan.sh'),str(d),'--seed',str(seed),'--threads','2','--checkpoint-tasks','8','--pilot','--points','8','--replicates','2',
                               '--test-graphs','2','--bootstrap-chunk','4','--shards','2'],capture_output=True,text=True,
                              env={**os.environ,'C8_PACKAGE':str(E.pkg),'C8_PYTHON':PY,'SLURM_JOB_ID':'9401','PYTHONDONTWRITEBYTECODE':'1',**env})
    d=E.td/'plansh_seed';cp=plansh(d,SEED+134,C8_SEEDS=str(log))
    assert cp.returncode==0 and [e['source']for e in entries(SEED+134)]==[str(d.resolve())],(cp.returncode,cp.stderr[-400:])
    assert [x['role']for x in map(json.loads,(d/'submissions.jsonl').read_text().splitlines())]==['plan']
    d=E.td/'plansh_noseeds';cp=plansh(d,SEED+135);assert cp.returncode==0 and 'C8_SEEDS is not set'in cp.stderr and not entries(SEED+135),cp.stderr[-300:]
    bad=E.td/'plansh_bad_seeds.json';bad.write_text('{"schema": "other"}\n');d=E.td/'plansh_badlog';cp=plansh(d,SEED+136,C8_SEEDS=str(bad))
    assert cp.returncode==2 and 'was NOT added to'in cp.stderr and f'tools/seeds.py add {d}'in cp.stderr,(cp.returncode,cp.stderr[-400:])
    assert [x['role']for x in map(json.loads,(d/'submissions.jsonl').read_text().splitlines())]==['plan']and bad.read_text()=='{"schema": "other"}\n'
    ok('Y13_class_plan_sh_registers_the_campaign_seed_after_planning')

def test_doc_examples(E):
    """Stage-6 fix round 2, integration: documented commands that must work as written. Y16 (S6R2-F-02): the lane example
    of docs/HPC.md ("Lane mode") replayed command by command on the fake scheduler, with the symmetry block of
    slurm/env.sh.example (C8_SITE=symmetry and the default C8_AMDQ_CAP of 4), the example's own C8_SBATCH_ARGS and
    C8_LANE_MEM, and every accepted job listed afterwards as the scheduler lists it: each submit.sh line is admitted
    (before the fix the second was refused with 65: the three jobs of `--lanes 2` plus a worker and a merge are five).
    Y13 (S6R2-F-01): every documented direct tools/sweep.py command (README.md, docs/*.md) names its seed log with
    --seeds-log (slurm/sweep.sh passes $C8_SEEDS itself), so the documented sweep registers its seed."""
    import shlex
    text=(ROOT/'docs/HPC.md').read_text();block=text.split('\n## Lane mode',1)[1].split('```bash\n',1)[1].split('```',1)[0]
    env={};subs=[]
    for line in block.splitlines():
        code=line.split('#',1)[0].strip()
        if code.startswith('export '):
            for w in shlex.split(code)[1:]:
                k,_,v=w.partition('=')
                if k in('C8_SBATCH_ARGS','C8_LANE_MEM'):env[k]=v
        elif 'slurm/submit.sh'in code:subs.append(shlex.split(code)[1:])
    assert set(env)=={'C8_SBATCH_ARGS','C8_LANE_MEM'}and len(subs)>=2,(env,subs)
    d=E.td/'docl';lanes_plan(E,d,seed=SEED+140)
    sym=(E.pkg/'slurm/env.sh.example').read_text().split('# ---- symmetry',1)[1].split('\n# ----',1)[0]
    lines=[l for l in sym.splitlines()if l.startswith('export ')and not l.startswith(('export PATH=','export C8_PYTHON='))]
    envsh=E.td/'docl_env.sh';envsh.write_text(f'export C8_PYTHON={PY}\n'+'\n'.join(lines)+'\n')
    S=Slurm(E,'docl',C8_RUN=str(d),C8_ENV_SETUP=str(envsh),FAKE_REGISTER='1',**env);S.queue();seen=[]
    for i,args in enumerate(subs):
        cp,c=S.call('submit.sh',args)
        adm=json.loads(next(l for l in cp.stdout.splitlines()if l.startswith('C8: admission '))[len('C8: admission '):])
        assert cp.returncode==0 and adm['amd_cap']==4 and adm['site']=='symmetry',(i,args,cp.returncode,adm,cp.stderr[-400:])
        seen.append({'args':args,'amd_live_before':adm['amd_live'],'new_jobs':len(c)})
    bad=[]
    for f in [ROOT/'README.md',*sorted((ROOT/'docs').glob('*.md'))]:
        ls=f.read_text().splitlines()
        for i,l in enumerate(ls):
            if re.search(r'python3? -B \S*tools/sweep\.py ',l):
                cmd,j=l,i
                while cmd.rstrip().endswith('\\')and j+1<len(ls):j+=1;cmd+=ls[j]
                if '--seeds-log'not in cmd:bad.append(f'{f.relative_to(ROOT)}:{i+1}')
    assert not bad,f'documented sweep commands without --seeds-log: {bad}'
    ok('Y16_Y13_docs_lane_example_fits_the_default_cap_sweep_commands_register_their_seed',submissions=seen)


DOC_SITE_VARS=('C8_SEEDS','C8_DATA')  # set by the site environment (slurm/env.sh.example, ~/c8d2/env*.sh)
def doc_block_problems(block:list)->list:
    """W16/W17 (Stage-6 fix round 4): what a fenced bash block of the docs gets wrong, [(line index, why)]: a command
    that expands C8_SEEDS or C8_DATA before an earlier line of the block sources the site environment, or without an
    earlier `: "${VAR:?...}"` guard; one that expands C8_PACKAGE neither exported in the block nor guarded; a direct
    `production.py plan ... --design` (a production batch: millions of tasks, a plan job's work)."""
    out=[];sourced=False;guards=set();exported=set()
    for n,l in block:
        if l.strip().startswith('#'):continue
        code=re.split(r'\s#',l,1)[0]
        if re.search(r'(^|[;&|]\s*)(source|\.)\s+\S',code.strip()):sourced=True
        guards|=set(re.findall(r'\$\{(\w+):\?',code))
        for m in re.finditer(r'\bexport\s+(.*)',code):exported|={w.split('=',1)[0]for w in m.group(1).split()if '='in w}
        for v in (*DOC_SITE_VARS,'C8_PACKAGE'):
            if not re.search(r'\$\{?'+v+r'\b(?!:\?)',code):continue
            if v in DOC_SITE_VARS and not sourced:out.append((n,f'${v} expanded before the site environment is sourced'))
            if v not in guards and v not in exported:out.append((n,f'${v} expanded without a guard (: "${{{v}:?}}")'))
        if re.search(r'tools/production\.py plan\b',code)and '--design'in code:out.append((n,'a production batch planned outside a plan job (slurm/plan.sh)'))
    return out

def test_doc_site_env(E):
    """W16 (S6R4-F-01) and W17 (S6R4-F-02), Stage-6 fix round 4: the documented commands must work as written in a fresh
    submitting shell. Every fenced bash block of README.md and docs/*.md that expands $C8_SEEDS or $C8_DATA sources
    the site environment earlier in the block and guards the variable (`: "${VAR:?...}"`); $C8_PACKAGE is exported in
    the block or guarded; no block plans a production batch with a direct `production.py plan --design` (a batch is
    above the 10^6 tasks a plan outside a job may have; slurm/plan.sh in a plan job). Before the fix: DESIGN.md's
    batch example planned on the login node, HPC.md's sweep and pilot examples expanded C8_DATA and C8_SEEDS before
    sourcing (/logs/%x_%j.out, /sweep1, a --forbid-seeds-from without argument), and README's and DESIGN.md's freeze and
    plan lines did the same. The rule's own controls: each fault is found in a minimal block, the fixed form is not."""
    bad=[];blocks=0
    for f in [ROOT/'README.md',*sorted((ROOT/'docs').glob('*.md'))]:
        blk=None
        for i,l in enumerate(f.read_text().splitlines()):
            st=l.strip()
            if st.startswith('```'):
                if blk is None and st.startswith('```bash'):blk=[];continue
                if blk is not None:bad+=[f'{f.relative_to(ROOT)}:{n+1}: {w}'for n,w in doc_block_problems(blk)];blocks+=1;blk=None
                continue
            if blk is not None:blk.append((i,l))
    assert blocks>=10 and not bad,(blocks,bad)
    B=lambda *ls:list(enumerate(ls))
    for blk,needle in ((B('sbatch -o $C8_DATA/logs/x.out job.sh'),'before the site environment is sourced'),
                       (B('source ~/c8d2/env.sh','plan --forbid-seeds-from "$C8_SEEDS"'),'without a guard'),
                       (B('"$C8_PACKAGE/slurm/plan.sh" RUN'),'C8_PACKAGE expanded without a guard'),
                       (B('python3 -B tools/production.py plan B --design BUNDLE --seed 1'),'outside a plan job')):
        got=doc_block_problems(blk);assert any(needle in w for _,w in got),(blk,got)
    assert doc_block_problems(B('source ~/c8d2/env.sh',': "${C8_SEEDS:?}" "${C8_PACKAGE:?}"','sbatch "$C8_PACKAGE/slurm/plan.sh" B --forbid-seeds-from "$C8_SEEDS"'))==[]
    ok('W16_W17_documented_commands_source_and_guard_the_site_environment',blocks=blocks)

# ================================================================ Stage-6 fix round 3, group G2 (Z3, Z6, Z7, Z11, Z13, Z15; Z5 in gen/test_regress.py)
def fake_build_record(exe:Path,backend:str='gmp',numerics:str='exact',**over)->dict:
    """The build record `make` writes beside a real build (tools/build_record.py), with the fields production.py's
    read_build_record checks, for a fake worker of a test package: a NON-test plan needs a valid one (Z3)."""
    rec={'schema':'c8-d2-build-record-1','executable':exe.name,'backend':backend,'executable_sha256':digest(exe),'NUMERICS':numerics,
         'command':['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math','src/c8d2_integrate.cpp','-o',f'bin/{exe.name}'],
         'compiler_options':['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math'],'compiler':'fake (tests/unit_orchestration.py)',
         'parameter_overrides':[],'macro_overrides':[],'development':False,'diagnostic':None,'required_flags_present':True,'optimized':True,**over}
    exe.with_name(exe.name+'.build.json').write_text(json.dumps(rec,indent=2)+'\n');return rec

def nontest_package(E)->NS:
    """A scratch package for NON-test plans (Z3, Z15), made once: minimal non-test inputs as tests/test_pipeline.py's
    nontest_inputs makes them (the two cheapest fixture graphs per (sector, L), the fixture's L8 packs linked, the
    manifest rehashed, no test_fixture), the fake gmp worker with a valid build record (fake_build_record), a seed log
    (tools/seeds.py init) and a synthetic exact cost model; plan(d, *extra, seed=, forbid=, expect=) runs its
    production.py plan as a subprocess (--pilot, 4,096 points, 2 replicates, one shard per group)."""
    if getattr(E,'_nontest',None)is not None:return E._nontest
    pkg=make_package(E.td,name='pkg_nontest');fx=pkg/'tests/fixtures/inputs_mini';inv=json.loads((fx/'inventory.json').read_text())
    small={s:{L:sorted(rows,key=lambda r:(r['cost'],r['id']))[:2]for L,rows in inv[s].items()}for s in inv}
    for s in ('free','power'):link_or_copy(fx/f'packs/{s}_L8.pack',pkg/f'inputs/packs/{s}_L8.pack')
    (pkg/'inputs/inventory.json').write_text(json.dumps(small,indent=1)+'\n')
    m=json.loads((pkg/'inputs/manifest.json').read_text());assert not m.get('test_fixture')
    m['sha256']={name:digest(pkg/'inputs'/name)for name in m['sha256']};m['counts']={s:{L:len(v)for L,v in small[s].items()}for s in small}
    m['scope']='tests/unit_orchestration.py (Z3, Z15): a minimal non-test inputs folder of a scratch package (never the delivered inputs)'
    (pkg/'inputs/manifest.json').write_text(json.dumps(m,indent=1)+'\n')
    fake_build_record(pkg/'bin/c8d2_gmp');log=E.td/'nontest_seeds.json';tool(pkg,'seeds.py','init','--log',log)
    cm=E.td/'nontest_cm.json';cm.write_text(json.dumps(cost_model_for(E,None)));env={'C8_INPUTS':''}
    def args(d,seed,*extra,forbid=None):
        fb=[x for f in (forbid if forbid is not None else[log])for x in ('--forbid-seeds-from',f)]
        return ['plan',d,'--seed',seed,'--pilot','--points',4096,'--replicates',2,'--threads',2,'--checkpoint-tasks',8,'--shards',1,'--cost-model',cm,*fb,*extra]
    def plan(d,*extra,seed,forbid=None,expect=0):
        cp=tool(pkg,'production.py',*args(d,seed,*extra,forbid=forbid),env=env,check=False)
        if (cp.returncode==0)!=(expect==0):raise AssertionError(f'non-test plan {d.name}: exit {cp.returncode}, expected {expect}\n{cp.stderr[-2500:]}')
        return cp
    E._nontest=NS(pkg=pkg,log=log,cm=cm,env=env,args=args,plan=plan);return E._nontest

def test_build_record_required(E):
    """Z3 (S6A3-03): a NON-test plan runs only an executable whose build record is a valid record of that very build. On
    a scratch package with non-test inputs (nontest_package) each plan below is refused, creates nothing and leaves the
    seed log unchanged: no record (before the fix: a warning, and the plan was published), a record that is not JSON or
    not an object, of another schema, naming another executable, of another backend or NUMERICS, of a diagnostic build,
    without the required flags in effect, of another executable (sha256), with an injected C8_NX_* hook in its compile
    options, marked development. The valid record plans and is recorded in the manifest. A test-only plan keeps a
    missing record with the warning (unchanged)."""
    N=nontest_package(E);exe=N.pkg/'bin/c8d2_gmp';br=exe.with_name(exe.name+'.build.json');good=json.loads(br.read_text());log0=N.log.read_bytes();n=0
    cases=[('missing',None,'has no build record'),('not JSON',b'{"schema": ','not a readable build record'),('a list',b'[]','not a build record'),
           ('schema',dict(good,schema='c8-d2-build-0'),'not a valid build record'),('executable name',dict(good,executable='c8d2_decimal'),'names the executable'),
           ('backend',dict(good,backend='decimal'),"backend 'decimal'"),('NUMERICS',dict(good,NUMERICS='dd'),"NUMERICS 'dd'"),
           ('diagnostic',dict(good,diagnostic='tier_timers'),'a diagnostic build'),('flags',dict(good,required_flags_present=False),'required_flags_present is False'),
           ('flags unknown',{k:v for k,v in good.items()if k!='required_flags_present'},'required_flags_present is None'),
           ('another executable',dict(good,executable_sha256='0'*64),'describes a different executable'),
           ('injected hook',dict(good,compiler_options=good['compiler_options']+['-DC8_NX_SHARED_BEGIN(T)=s.products[0]=2;']),'development build'),
           ('development',dict(good,development=True),'development build'),
           # Z3 integration (G1's macro_overrides): a listed macro refuses even with development edited to false; a non-test plan needs the list
           ('macro override',dict(good,macro_overrides=['C8_NX_SHARED_BEGIN'],development=False),'macro overrides'),
           ('macro overrides null',dict(good,macro_overrides=None),'macro_overrides is None, not a list'),
           ('macro overrides absent',{k:v for k,v in good.items()if k!='macro_overrides'},'macro_overrides is None, not a list')]
    try:
        for name,rec,needle in cases:
            if rec is None:br.unlink()
            else:br.write_bytes(rec if isinstance(rec,bytes)else json.dumps(rec).encode())
            d=E.td/f'z3_{n}';cp=N.plan(d,seed=SEED+200,expect=1)
            assert needle in cp.stderr and gone(d)and N.log.read_bytes()==log0,(name,needle,cp.stderr[-600:]);n+=1
    finally:br.write_text(json.dumps(good,indent=2)+'\n')
    d=E.td/'z3_valid';N.plan(d,seed=SEED+200);m=manifest(d);assert m['build_record']==good and m['test_only']is False
    mb=E.pkg/'bin/c8d2_gmp.build.json';saved=mb.read_bytes()if mb.exists()else None;mb.unlink(missing_ok=True)
    try:r=E.small(E.td/'z3_test_only',seed=SEED+201)
    finally:
        if saved is not None:mb.write_bytes(saved)
    assert 'warning: no build record'in r.stderr and manifest(E.td/'z3_test_only')['build_record']is None
    # Z3 integration: a test-only plan refuses a record that lists macro overrides too (every plan refuses a development build)
    fake_build_record(E.pkg/'bin/c8d2_gmp',macro_overrides=['NO_SUM_SHARING'],development=False)
    try:d=E.td/'z3_test_only_macro';r=E.small(d,seed=SEED+202,expect=1);assert 'macro overrides'in r.stderr and gone(d),r.stderr[-400:];n+=1
    finally:
        if saved is not None:mb.write_bytes(saved)
        else:mb.unlink(missing_ok=True)
    ok('Z3_non_test_plan_requires_a_valid_matching_build_record',refusals=n)

def test_plan_registers_seed(E):
    """Z15 (S6R3-F-02): a NON-test production.py plan registers its base seed in the seed log of its first
    --forbid-seeds-from itself, so that no direct command can skip it: the entry (source = the campaign directory, as
    `seeds.py add RUN` writes it) is in the log when the plan returns (before the fix: no entry), the manifest names the
    log, and `seeds.py add RUN` after it (slurm/plan.sh) finds it present. A first --forbid-seeds-from that is not a seed
    log is refused before anything is created. Registration and publication are one step under the log's lock: with the
    lock held by another writer the plan builds its staging directory and waits, publishing nothing (before the fix it
    published at once); a seed registered meanwhile (here by the lock holder) is refused when the plan gets the lock
    (nothing published, the log keeps only the other entry); without one, it registers and publishes. A test-only plan
    leaves the log unchanged."""
    N=nontest_package(E);log=N.log;sd=E.M.seeds;lock=log.with_name(log.name+'.lock')
    entries=lambda seed:[e for e in sd.read_log(log)['seeds']if e['seed']==seed]
    d=E.td/'z15_plan';cp=N.plan(d,seed=SEED+210)
    assert [e['source']for e in entries(SEED+210)]==[str(d.resolve())]and manifest(d)['seed_log']==str(log.resolve())and 'registered in'in cp.stderr,cp.stderr[-400:]
    assert json.loads(cp.stdout)['seed_log']==str(log.resolve())
    r=tool(N.pkg,'seeds.py','add',d,'--log',log);assert json.loads(r.stdout)['state']=='present'and len(entries(SEED+210))==1
    d2=E.td/'z15_again';cp=N.plan(d2,seed=SEED+210,expect=1);assert 'forbidden seed'in cp.stderr and gone(d2)and len(entries(SEED+210))==1
    lst=E.td/'z15_list.json';lst.write_text('[]');d3=E.td/'z15_not_a_log';cp=N.plan(d3,seed=SEED+211,forbid=[lst,log],expect=1)
    assert 'must be a tools/seeds.py seed log'in cp.stderr and gone(d3)and not entries(SEED+211),cp.stderr[-400:]
    n=0
    for name,seed,inject in (('refused',SEED+212,True),('registered',SEED+213,False)):
        d4=E.td/f'z15_lock_{name}';lock.mkdir();(lock/'owner.json').write_text('{"test":"Z15 interleaving (unit_orchestration)"}\n')
        staged=lambda:[x for x in d4.parent.glob(d4.name+'.tmp.*')if (x/'manifest.json').exists()]
        with Owned(markers=(str(d4),))as own:
            try:
                pr=own.add(subprocess.Popen([PY,'-B',str(N.pkg/'tools/production.py'),*map(str,N.args(d4,seed))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',**N.env},start_new_session=True))
                assert wait_for(lambda:staged()or d4.exists()or pr.poll()is not None,240),(name,'the plan never reached its publication')
                time.sleep(1.0)
                assert not d4.exists(),(name,'the campaign was published while another writer held the seed log\'s lock: its seed was not registered under it')
                assert pr.poll()is None and staged(),(name,'the plan did not wait for the seed log\'s lock',pr.poll())
                if inject:  # what a concurrent plan or `seeds.py add` holding the lock would have written
                    doc=json.loads(log.read_text());doc['seeds'].append({'seed':seed,'source':'concurrent registration (unit test)'});log.write_text(json.dumps(doc,indent=1)+'\n')
            finally:shutil.rmtree(lock,ignore_errors=True)
            out,err=pr.communicate(timeout=240)
        if inject:
            assert pr.returncode!=0 and 're-checked under the seed log'in err and 'forbidden seed'in err and gone(d4),(name,pr.returncode,err[-600:])
            assert [e['source']for e in entries(seed)]==['concurrent registration (unit test)'],entries(seed)
        else:assert pr.returncode==0 and manifest(d4)['seed']==seed and [e['source']for e in entries(seed)]==[str(d4.resolve())],(name,pr.returncode,err[-600:])
        n+=1
    snap=log.read_bytes();E.small(E.td/'z15_test_only','--forbid-seeds-from',log,seed=SEED+214);assert log.read_bytes()==snap and manifest(E.td/'z15_test_only')['seed_log']is None
    ok('Z15_non_test_plan_registers_its_seed_under_the_log_lock_before_publication',interleavings=n)

def test_seeds_init_locked(E):
    """Z11 (S6D-R3-04): tools/seeds.py init holds the lock add and merge hold, re-checks under it and never overwrites.
    With the lock held by another writer, init waits and writes nothing (before the fix it wrote the empty log at once);
    the lock holder creates the log with its seed and releases, and init then refuses (64), the seed kept. The
    post-check race (the existence check stale: patched to answer False while the log exists) refuses (64) instead of
    replacing the log (before the fix the seed was erased). Plain init creates the log; a second init refuses (64)."""
    sd=E.M.seeds;log=E.td/'z11_log.json';lock=log.with_name(log.name+'.lock');lock.mkdir();(lock/'owner.json').write_text('{"test":"Z11 (unit_orchestration)"}\n')
    with Owned(markers=(str(log),))as own:
        try:
            pr=own.add(subprocess.Popen([PY,'-B',str(E.pkg/'tools/seeds.py'),'init','--log',str(log)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True))
            wait_for(lambda:log.exists()or pr.poll()is not None,5)
            assert not log.exists()and pr.poll()is None,('seeds.py init wrote the log while another writer held its lock',pr.poll(),log.exists())
            log.write_text(json.dumps({'schema':'c8-d2-seeds-1','seeds':[{'seed':4711,'source':'add holding the lock (unit test)'}]},indent=1)+'\n')
        finally:shutil.rmtree(lock,ignore_errors=True)
        out,err=pr.communicate(timeout=240)
    assert pr.returncode==64 and 'exists'in err and [e['seed']for e in sd.read_log(log)['seeds']]==[4711],(pr.returncode,err[-300:])
    race=E.td/'z11_race.json';race.write_text(json.dumps({'schema':'c8-d2-seeds-1','seeds':[{'seed':4712,'source':'x'}]},indent=1)+'\n');real=Path.exists
    with mock.patch.object(Path,'exists',lambda self:False if str(self)==str(race)else real(self)):r=cli(sd,'init','--log',race,expect=1)
    assert r.returncode==64 and 'exists'in r.stderr and [e['seed']for e in sd.read_log(race)['seeds']]==[4712]and not Path(str(race)+'.lock').exists(),(r.returncode,r.stderr[-300:])
    fresh=E.td/'z11_fresh.json';r=tool(E.pkg,'seeds.py','init','--log',fresh);assert json.loads(r.stdout)['state']=='created'and sd.read_log(fresh)['seeds']==[]
    r=tool(E.pkg,'seeds.py','init','--log',fresh,check=False);assert r.returncode==64 and not Path(str(fresh)+'.lock').exists()
    ok('Z11_seeds_init_under_the_lock_never_overwrites')

def test_fingerprint_absolute_entries(E):
    """Z6 (S6-C-R3-01): common.fingerprint accounts for every ldd line (stubbed output, an ELF worker whose PT_INTERP is
    a symlink to the loader): an absolute-path entry without '=>' (an LD_PRELOAD library: '/path/liboverride.so
    (0x...)') is hashed and keyed by its path; the loader listed by its realpath is the interpreter (hashed once, not a
    library); the vDSO is left out; the fingerprint is complete. Changing the preloaded library's bytes changes the
    runtime identity (before the fix it did not: the entry was dropped). An unexplained line (a relative path, a loader
    error about LD_PRELOAD) is refused for a dynamic ELF worker; a static worker's 'statically linked' gives no entry.
    End to end: the first claim pins an identity holding the preload, and after its bytes change the next claim stops
    with 64 naming that library, no checkpoint written (before the fix it ran)."""
    C=E.M.common;p=E.M.prod;t=E.td/'z6';t.mkdir()
    (t/'ld-2.28.so').write_bytes(b'ld.so');os.symlink('ld-2.28.so',t/'ld-linux-x86-64.so.2')
    (t/'libgmp.so.10').write_bytes(b'gmp');(t/'libc.so.6').write_bytes(b'libc');pre=t/'liboverride.so';pre.write_bytes(b'override v1')
    exe=t/'worker';exe.write_bytes(elf_bytes(interp_path=str(t/'ld-linux-x86-64.so.2')));static=t/'static';static.write_bytes(elf_bytes(interp=False))
    def text(extra=''):
        return (f'\tlinux-vdso.so.1 (0x00007ffd5a1f2000)\n\t{pre} (0x00007f2b1e000000)\n\tlibgmp.so.10 => {t}/libgmp.so.10 (0x00007f2b1c000000)\n'
                f'\tlibc.so.6 => {t}/libc.so.6 (0x00007f2b1b000000)\n{extra}\t{t}/ld-2.28.so (0x00007f2b1d000000)\n').encode()
    real_fp=C.fingerprint
    def probed(out,target,counter=None,identity=None):
        real_run=subprocess.run
        def fake_run(cmd,*a,**k):
            if list(cmd)[:1]==['ldd']:return subprocess.CompletedProcess(cmd,0,out,None)
            return real_run(cmd,*a,**k)
        with mock.patch.object(C.subprocess,'run',fake_run):return real_fp(target,counter,identity)
    f1=probed(text(),exe)
    assert set(f1['libraries'])=={str(pre),'libgmp.so.10','libc.so.6'}and f1['libraries'][str(pre)]['sha256']==digest(pre),sorted(f1['libraries'])
    assert f1['interpreter']['sha256']==digest(t/'ld-2.28.so')and C.fingerprint_problems(f1,'dynamic')==[],(f1['interpreter'],C.fingerprint_problems(f1,'dynamic'))
    k1=C.runtime_identity_key(f1);pre.write_bytes(b'override v2');f2=probed(text(),exe);pre.write_bytes(b'override v1')
    assert C.runtime_identity_key(f2)!=k1 and C.runtime_identity(f2)['libraries'][str(pre)]==hashlib.sha256(b'override v2').hexdigest()
    n=0
    for extra in ('\t./librelative.so (0x00007f2b1a000000)\n',"ERROR: ld.so: object 'x.so' from LD_PRELOAD cannot be preloaded (cannot open shared object file): ignored.\n"):
        f=probed(text(extra),exe);pr=C.fingerprint_problems(f,'dynamic');assert pr and 'unexplained ldd line'in ' '.join(pr),(extra,pr)
        assert C.fingerprint_problems(f,None)==[]and C.fingerprint_problems(f,'static')==[];n+=1
    f=probed(b'\tstatically linked\n',static);assert f['libraries']=={}and f['interpreter']is None and f['ldd_error']is None,f
    # end to end: the claim pins the preload; another preload stops the next claim (64)
    d=E.td/'z6run';E.small(d,'--checkpoint-tasks',4,'--shards',1,seed=SEED+220);m=manifest(d)
    stub=lambda target,counter=None,identity=None:probed(text(),target,counter,identity)
    with mock.patch.object(p,'fingerprint',stub):E.run(d,m['jobs'][0]['id'])
    pin=json.loads((d/'runtime_identity.json').read_text());assert pin['identity']['libraries'][str(pre)]==digest(pre),pin['identity']
    pre.write_bytes(b'override v2');j=m['jobs'][1]
    with mock.patch.object(p,'fingerprint',stub):r=E.run(d,j['id'],expect=1)
    assert r.returncode==64 and 'another run-time library stack'in r.stderr and f'library {pre}'in r.stderr,(r.returncode,r.stderr[-600:])
    assert not list((d/'groups'/j['group']/'checkpoints').glob(f's{j["shard"]:06d}_p*.json'));n+=1
    ok('Z6_absolute_path_ldd_entries_hashed_interpreter_and_vdso_explained_unexplained_refused',refusals=n)

def test_memory_env(E):
    """Z7 (S6-C-R3-02): an inherited SBATCH_MEM_PER_CPU (or SBATCH_MEM_PER_NODE, or both) no longer breaks a
    submission: every job's command line (or its script) sets its memory, so sbatch resets the inherited one, the
    effective options follow that rule, and the variables are removed from sbatch's environment. submit gives the work
    arrays and their merge (before the fix: the arrays were submitted, then the merge was refused, 64), lanes 1 the lane
    worker and its merge (before: refused, 64). A user --mem-per-cpu for the array jobs, against the array script's
    #SBATCH --mem, is refused (64) with nothing submitted, as sbatch refuses mutually exclusive memory options. Preflight:
    a merge whose contract breaks (its script made exclusive) refuses submit, resubmit and lanes (64) before ANY job is
    submitted (before: the work jobs were accepted first)."""
    d=E.td/'z7';E.small(d,'--shards',1,seed=SEED+230);m=manifest(d);S=Slurm(E,'z7',C8_RUN=str(d));t5='--time=00:05:00';n=0
    dl=E.td/'z7_lanes';lanes_plan(E,dl,seed=SEED+231);SL=Slurm(E,'z7l',C8_RUN=str(dl))
    for envx in ({'SBATCH_MEM_PER_CPU':'2000'},{'SBATCH_MEM_PER_NODE':'1000'},{'SBATCH_MEM_PER_CPU':'2000','SBATCH_MEM_PER_NODE':'1000'}):
        S.queue();cp,calls=S.call('submit.sh',[t5],**envx);assert cp.returncode==0,(envx,cp.returncode,cp.stderr[-600:])
        scripts=[c['script']for c in calls];assert scripts.count('merge.sh')==1 and 'run_array.sh'in scripts and scripts[-1]=='merge.sh',(envx,scripts)
        for c in calls:
            assert c['env']['SBATCH_MEM_PER_CPU']is None and c['env']['SBATCH_MEM_PER_NODE']is None,(envx,c['script'],c['env'])
            assert last(c['args'],'--mem')==(f'{m["estimates"]["mem_suggestion_mb"]}M'if c['script']=='run_array.sh'else'64G'),(envx,c['args'])
        SL.queue();cp,calls=SL.call('submit.sh',['--lanes','1'],**envx);assert cp.returncode==0,(envx,cp.returncode,cp.stderr[-600:])
        assert [c['script']for c in calls]==['lane_worker.sh','merge.sh']and all(c['env']['SBATCH_MEM_PER_CPU']is None for c in calls),(envx,calls)
        assert last(calls[0]['args'],'--mem')=='180G'and last(calls[1]['args'],'--mem')=='64G';n+=2
    S.queue();cp,calls=S.call('submit.sh',[t5],C8_SBATCH_ARGS='-A acct -p part --mem-per-cpu=64G')
    assert cp.returncode==64 and not calls and 'mutually exclusive'in cp.stderr,(cp.returncode,cp.stderr[-400:]);n+=1
    ms=E.pkg/'slurm/merge.sh';orig=ms.read_bytes()
    try:
        replace_bytes(ms,orig.replace(b'#SBATCH --nodes=1\n',b'#SBATCH --nodes=1\n#SBATCH --exclusive\n',1))
        for SS,script,args in ((S,'submit.sh',[t5]),(S,'resubmit.sh',[t5]),(SL,'submit.sh',['--lanes','1'])):
            SS.queue();cp,calls=SS.call(script,args)
            assert cp.returncode==64 and not calls and 'merge job refused before submission'in cp.stderr and 'exclusive is set'in cp.stderr,(script,cp.returncode,calls,cp.stderr[-400:]);n+=1
    finally:replace_bytes(ms,orig)
    ok('Z7_inherited_memory_variables_reset_by_the_job_memory_preflight_before_any_sbatch',cases=n)

def test_cleanup_harness(E):
    """Z13 (S6E-R3-01): the unconditional cleanup (Owned) checked by cases that fail on purpose. (0) The pattern before
    the fix (a Popen in the runner's process group, a failure before the FIFO release, no cleanup scope) leaves the
    submission blocked in the fake sbatch; the cleanup then removes it. (1) Before the FIFO
    release: a submission blocked in the fake sbatch on its FIFO (its own session), then an assertion fails: the
    failure message carries the owned processes (evidence taken before the cleanup), the blocked sbatch and the
    submission are killed and reaped, the FIFO is removed, nothing of the case survives. (2) During lane startup: a lane
    worker with two runs of 120 s native tasks; killing only the worker's process group (the cleanup before the fix)
    leaves the production runs, each in a session of its own, and their native workers running; the case then fails on
    purpose and the cleanup kills the runs and the natives too: none survives."""
    d=E.td/'z13_fifo';E.small(d,'--shards',1,seed=SEED+240);S=Slurm(E,'z13',C8_RUN=str(d));fifo=S.td/'z13.fifo';os.mkfifo(fifo);marks=(str(S.td/'fakebin'),)
    # the pattern before the fix (no cleanup scope, the runner's own process group): a failure before the release
    # leaves the submission blocked in the fake sbatch; then the cleanup removes it
    d0=E.td/'z13_old';E.small(d0,'--shards',1,seed=SEED+242);fifo0=S.td/'z13_old.fifo';os.mkfifo(fifo0)
    old=subprocess.Popen(['bash',str(E.pkg/'slurm/submit.sh'),'--time=00:05:00'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                         env={**S.base,'C8_RUN':str(d0),'FAKE_SBATCH_BLOCK':str(fifo0)})
    with Owned(markers=marks,fifos=(fifo0,))as own0:
        own0.add(old)
        try:
            assert wait_for(lambda:any('fakebin/sbatch'in a for _,_,a in own0.survivors()),120),'the fake sbatch never started (old pattern)'
            raise AssertionError('deliberate failure, old pattern')
        except AssertionError as e:assert 'deliberate'in str(e),str(e)
        time.sleep(0.5);leaked=[a for _,_,a in own0.survivors()if 'fakebin/sbatch'in a]
        assert leaked and old.poll()is None,('the old pattern was expected to leave the blocked submission running',own0.survivors())
    assert not Owned(markers=marks).survivors()and old.returncode is not None;shutil.rmtree(d0/'.c8_submit.lock',ignore_errors=True)
    caught=None;first=None;own=Owned(markers=marks,fifos=(fifo,))
    try:
        with own:
            first=own.add(subprocess.Popen(['bash',str(E.pkg/'slurm/submit.sh'),'--time=00:05:00'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                           env={**S.base,'FAKE_SBATCH_BLOCK':str(fifo)},start_new_session=True))
            assert wait_for(lambda:any('fakebin/sbatch'in a for _,_,a in own.survivors()),120),('the fake sbatch never started',own.survivors())
            raise AssertionError('deliberate failure before the FIFO release (Z13 harness check)')
    except AssertionError as e:caught=e
    assert caught is not None and 'deliberate failure before the FIFO release'in str(caught)and 'Z13 cleanup: owned processes at the failure'in str(caught)and 'sbatch'in str(caught),str(caught)[-600:]
    assert first is not None and first.returncode is not None and any('fakebin/sbatch'in a for _,a in own.killed)and not Owned(markers=marks).survivors()and not fifo.exists(),(first.returncode,own.killed)
    assert not [r for r in proc_table()if r[2]==first.pid and 'Z'not in r[3]]
    shutil.rmtree(d/'.c8_submit.lock',ignore_errors=True)  # the killed submission's campaign lock, removed by hand as documented
    d2=E.td/'z13_lane';lanes_plan(E,d2,seed=SEED+241);tool(E.pkg,'lanes.py','queue',d2);scr=E.td/'z13_lane_tmp';scr.mkdir();flog=E.td/'z13_lane.log'
    env={k:v for k,v in os.environ.items()if k!='SLURM_TMPDIR'}
    env.update(PYTHONDONTWRITEBYTECODE='1',SLURM_JOB_ID='6600',C8_LANE_SECONDS='36000',C8_LANES='2',TMPDIR=str(scr),C8_FAKE_SLEEP='120',C8_FAKE_LOG=str(flog))
    caught=None;natives=[];runs=[];marks=(str(d2),str(scr));own=Owned(markers=marks)
    with at_most_cpus(16):
        try:
            with own:
                proc=own.add(subprocess.Popen([PY,'-B',str(E.pkg/'tools/lanes.py'),'worker',str(d2)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,start_new_session=True))
                assert wait_for(lambda:flog.exists()and len(flog.read_text().splitlines())>=2,120),'two native tasks never started'
                natives=[json.loads(l)['pid']for l in flog.read_text().splitlines()]
                os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=60);time.sleep(0.5)  # the cleanup before Z13: the worker's session only
                runs=[(pid,a)for pid,_,a in own.survivors()if 'production.py'in a and ' run 'in a]
                assert runs and all(alive(x)for x in natives),('the production runs and natives were expected to outlive the worker session',own.survivors())
                raise AssertionError('deliberate failure during lane startup (Z13 harness check)')
        except AssertionError as e:caught=e
    assert caught is not None and 'deliberate failure during lane startup'in str(caught)and 'production.py'in str(caught),str(caught)[-800:]
    assert not Owned(markers=marks).survivors()and wait_for(lambda:not any(alive(x)for x in natives),30),Owned(markers=marks).survivors()
    assert {pid for pid,_ in runs}<={pid for pid,_ in own.killed},(runs,own.killed)
    ok('Z13_cleanup_kills_and_reaps_owned_processes_on_failure_fifo_and_detached_sessions',old_pattern_leaked=len(leaked),runs_outliving_the_worker_session=len(runs),natives=len(natives))

# ================================================================ driver
# Every test in run order, by name (--only NAME,...). The table is fixed before any setup, so a selection is checked
# against it before the package copy is made (checkpoint review T-03).
TESTS=(('literal_sizes',lambda c:test_literal_sizes()),('static',lambda c:test_static(c.M)),('seeds',lambda c:test_seeds(c.E)),('c7',lambda c:test_c7_refused(c.E)),
       ('inputs',lambda c:test_inputs_refusals(c.E)),('exe',lambda c:test_executable_identity(c.E)),('route_b_records',lambda c:test_route_b_records(c.E)),
       ('allocation',lambda c:test_allocation(c.E)),
       ('chunking',lambda c:test_chunking_sizing(c.E)),('atomic',lambda c:test_atomic_plan(c.E)),('bootstrap',lambda c:test_bootstrap(c.E)),
       ('pipeline',lambda c:test_pipeline(c.E)),('signals',lambda c:test_signal_cleanup(c.E)),('uri',lambda c:test_uri_concurrent_merge(c.E)),('zero',lambda c:test_zero_task(c.E)),
       ('fanin',lambda c:test_fan_in(c.E)),('resume',lambda c:test_merge_resume(c.E)),('cached',lambda c:test_merge_cached_runs_verified(c.E)),('recovery',lambda c:test_recovery_plan(c.E)),
       ('arrays',lambda c:test_slurm_arrays(c.E)),('lane_units',lambda c:test_lane_units(c.E)),('p4_defaults',lambda c:test_p4_defaults(c.E)),('lanes',lambda c:test_lanes(c.E)),('scan',lambda c:test_lane_scan_cost(c.E)),
       ('markers',lambda c:test_done_markers(c.E)),('recovery_merge',lambda c:test_recovery_merge(c.E)),('lane_sigterm',lambda c:test_lane_sigterm(c.E)),('cpu_vendor',lambda c:test_cpu_vendor(c.E)),('lsub',lambda c:test_lane_submission(c.E)),('drill',lambda c:test_drill_mode(c.E)),('admission',lambda c:test_admission(c.E)),
       ('roles',lambda c:test_submission_roles(c.E)),('unverified',lambda c:test_unverified_stop(c.E)),('cancel',lambda c:test_conditional_cancel(c.E)),
       ('ledger',lambda c:test_ledger_accounting(c.E)),('rates',lambda c:test_rates(c.E)),('staging',lambda c:test_staging(c.E)),('nets',lambda c:test_nets(c.E)),
       ('pack_reads',lambda c:test_pack_reads(c.E)),('claim',lambda c:test_per_claim_reads(c.E,c.real)),('claim_io',lambda c:test_claim_io(c.E)),
       ('runtime_identity',lambda c:test_runtime_identity(c.E)),('bundle_relocation',lambda c:test_bundle_relocation(c.E)),('cost_numerics',lambda c:test_cost_model_numerics(c.E)),
       ('amd_cap_template',lambda c:test_amd_cap_template(c.E)),('acct_partition',lambda c:test_account_partition_selection(c.E)),
       ('lane_fail_recheck',lambda c:test_lane_failure_recheck(c.E)),('seedsync',lambda c:test_seedsync(c.E)),('drivers',lambda c:test_drivers(c.E)))
# Stage-6 fix round 2, G2 (Y2, Y6, Y7, Y8, Y10, Y12, Y13)
TESTS+=(('omp_env',lambda c:test_omp_env(c.E)),('omp_team',lambda c:test_omp_team(c.E)),('bench_team',lambda c:test_bench_team(c.E)),
        ('cgroup_min',lambda c:test_cgroup_minimum(c.E)),('fp_complete',lambda c:test_fingerprint_complete(c.E)),('fp_first',lambda c:test_first_fingerprint(c.E)),
        ('bundle_reps',lambda c:test_bundle_replicates(c.E)),('sweep_resume',lambda c:test_sweep_resume_identity(c.E)),('sweep_seed',lambda c:test_sweep_seed(c.E)),
        ('plan_seed',lambda c:test_plan_seed(c.E)))
# Stage-6 fix round 2, integration (Y16, Y13: the documented commands)
TESTS+=(('doc_examples',lambda c:test_doc_examples(c.E)),)
# Stage-6 fix round 3, G2 (Z3, Z6, Z7, Z11, Z13, Z15; Z5 is checked by gen/test_regress.py)
TESTS+=(('z3_build_record',lambda c:test_build_record_required(c.E)),('z15_plan_seed',lambda c:test_plan_registers_seed(c.E)),
        ('z11_seeds_init',lambda c:test_seeds_init_locked(c.E)),('z6_ldd_absolute',lambda c:test_fingerprint_absolute_entries(c.E)),
        ('z7_mem_env',lambda c:test_memory_env(c.E)),('z13_cleanup',lambda c:test_cleanup_harness(c.E)))
# Stage-6 fix round 4, G4 (W14, W15): the cleanup controls
W14_LEADER=r'''import subprocess,sys
h=subprocess.Popen([sys.executable,'-c','import time;time.sleep(300)','w14-unmarked-helper'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
open(sys.argv[1],'w').write(str(h.pid))
'''
def test_group_cleanup(E):
    """W14 (S6E-R4-01): Owned retains the process group a registered session leader leads. The control: a leader
    (start_new_session) starts an unmarked helper with its output redirected and exits; the case reaps it (wait), checks
    that the helper is unmarked, reparented and still in the leader's group, and that survivors() lists it under that
    group (the check test_lane_sigterm makes after communicate()), then fails on purpose: the failure message carries
    the helper (evidence before cleanup), the helper is killed (independently: its pid is gone) and the group retired.
    Also: a leader that is already a zombie when registered (macOS refuses getpgid on it) is retained through ps; a child
    in the runner's own process group is owned by pid only; held() keeps a group while its leader is unreaped or while
    members survive its reaping, and retires it when it is empty or its id is a live pid again (reused)."""
    src=E.td/'w14_leader.py';src.write_text(W14_LEADER);pidf=E.td/'w14_helper.pid';dn=subprocess.DEVNULL
    caught=None;helper=None;leader=None;own=Owned(markers=(str(pidf),))  # the marker is in the leader's command line only
    try:
        with own:
            leader=own.add(subprocess.Popen([PY,'-S',str(src),str(pidf)],stdin=dn,stdout=dn,stderr=dn,start_new_session=True))
            assert leader.wait(timeout=60)==0 and pidf.exists(),'the leader did not start its helper'
            helper=int(pidf.read_text());row=next((r for r in proc_table()if r[0]==helper),None)
            assert row is not None and 'Z'not in row[3]and row[2]==leader.pid and row[1]!=leader.pid and str(pidf)not in row[4],('an unmarked, reparented helper in the leader\'s group',row)
            assert [pid for pid,pg,_ in own.survivors()if pg==leader.pid]==[helper]and leader.pid in own.groups,(own.survivors(),getattr(own,'groups',None))
            raise AssertionError('deliberate failure after the leader was reaped (W14 control)')
    except AssertionError as e:caught=e
    assert caught is not None and 'deliberate failure after the leader was reaped'in str(caught)and 'Z13 cleanup: owned processes at the failure'in str(caught)and str(helper)in str(caught),str(caught)[-800:]
    assert helper is not None and wait_for(lambda:not alive(helper),30)and any(pid==helper for pid,_ in own.killed)and not own.groups,(own.killed,own.groups)
    # a leader registered as a zombie (exited, unreaped): the group is found through ps and its helper cleaned up
    pidz=E.td/'w14_helper_z.pid';z=subprocess.Popen([PY,'-S',str(src),str(pidz)],stdin=dn,stdout=dn,stderr=dn,start_new_session=True);hz=None
    try:
        assert wait_for(lambda:any(r[0]==z.pid and 'Z'in r[3]for r in proc_table()),60)and pidz.exists(),'the leader did not become a zombie'
        hz=int(pidz.read_text())
        with Owned()as oz:
            oz.add(z);assert z.pid in oz.groups and any(pid==hz for pid,_,_ in oz.survivors()),(oz.groups,oz.survivors())
        assert wait_for(lambda:not alive(hz),30)and any(pid==hz for pid,_ in oz.killed)and z.returncode is not None,oz.killed
    finally:  # this sub-case's own cleanup, whatever failed above
        if z.poll()is None:z.kill();z.wait(timeout=30)
        if hz is not None and alive(hz):
            with contextlib.suppress(OSError):os.kill(hz,signal.SIGKILL)
    # a child in the runner's own process group: owned by its pid, its group never retained (never killpg'ed)
    with Owned()as og:
        c=og.add(subprocess.Popen([PY,'-c','import time;time.sleep(60)'],stdin=dn,stdout=dn,stderr=dn));assert not og.groups and os.getpgid(c.pid)==os.getpgrp()
    assert c.returncode is not None and {pid for pid,_ in og.killed}=={c.pid},og.killed
    # held(): the retirement rules on a synthetic table (pid, ppid, pgid, state, args)
    o=Owned();o.groups={4242:NS(pid=4242,returncode=None),4343:NS(pid=4343,returncode=0),4444:NS(pid=4444,returncode=0),4545:NS(pid=4545,returncode=-9)}
    table=[(4242,1,4242,'Z',''),(5000,1,4343,'S','helper'),(4444,1,4444,'S','a new leader with the old id'),(6000,1,9999,'S','other')]
    assert o.held(table)=={4242,4343}and set(o.groups)=={4242,4343},(o.groups,)
    ok('W14_owned_retains_registered_process_groups_after_their_leaders_exit',helper_killed=helper,zombie_leader_helper=hz)

def test_launch_boundary_cleanup(E):
    """W15 (S6E-R4-02): the in-process launch-boundary case (launch_boundary_case, as test_signal_cleanup runs it)
    checked by a control that fails on purpose: production's cleanup is made to fail (stop_children a no-op), so the
    120 s fake worker outlives the run. (0) The pattern before the fix (the hook keeps only the pid, no cleanup scope):
    the case's assertion fails and the worker is left running (only production's _NATIVE['children'] still holds it;
    this control cleans it up itself). (1) The case itself: its assertion fails, the failure message carries the
    worker (evidence taken before any cleanup), and on the way out the worker is killed and reaped (its Popen has a
    return code; independently, its pid is gone)."""
    p=E.M.prod;d=E.td/'w15';E.small(d,'--shards',1,seed=SEED+291);j=manifest(d)['jobs'][0];nop=lambda:None
    scr0=E.td/'w15_scratch_old';scr0.mkdir();pids=[];leaked=None;flog0=E.td/'w15_scratch_old.fake.log'
    with Owned(markers=(str(scr0),))as own0:  # (0): only this control's own cleanup of what the old pattern leaves
        def hook0(child):pids.append(child.pid);assert fake_running(flog0,child.pid);os.kill(os.getpid(),signal.SIGTERM)
        with mock.patch.dict(os.environ,{'C8_FAKE_SLEEP':'120','C8_FAKE_LOG':str(flog0)}),mock.patch.object(p,'_after_launch',side_effect=hook0),mock.patch.object(p,'stop_children',nop):
            r=cli(p,'run',d,'--index',j['id'],'--threads',2,'--scratch',scr0,expect=None)
        for c in p._NATIVE['children']:own0.add(c)
        try:
            assert r.returncode==143 and pids and not alive(pids[0]),(r.returncode,r.stderr[-500:])
            raise RuntimeError('the old pattern passed: production stopped the worker although stop_children was a no-op')
        except AssertionError:leaked=pids[0]if pids and alive(pids[0])else None
        assert leaked is not None,('the old pattern was expected to leave the worker running',pids)
    assert wait_for(lambda:not alive(leaked),30)and any(pid==leaked for pid,_ in own0.killed),own0.killed
    scr=E.td/'w15_scratch';scr.mkdir();seen={};caught=None
    with mock.patch.object(p,'stop_children',nop):
        try:launch_boundary_case(E,d,j,scr,seen)
        except AssertionError as e:caught=e
    kids=seen.get('children')or[]
    assert caught is not None and kids and 'Z13 cleanup: owned processes at the failure'in str(caught)and str(kids[0].pid)in str(caught),str(caught)[-800:]
    assert kids[0].returncode is not None and wait_for(lambda:not alive(kids[0].pid),30)and any(pid==kids[0].pid for pid,_ in seen['own'].killed),(kids[0].returncode,seen['own'].killed)
    assert not Owned(markers=(str(scr),)).survivors();p._NATIVE.update(children=[])
    ok('W15_inprocess_launch_boundary_child_cleaned_up_on_failure',old_pattern_leaked=leaked,cleaned=kids[0].pid)

TESTS+=(('w14_group_cleanup',lambda c:test_group_cleanup(c.E)),('w15_launch_cleanup',lambda c:test_launch_boundary_cleanup(c.E)))
TESTS+=(('w17_doc_env',lambda c:test_doc_site_env(c.E)),)  # W16, W17 (fix round 4, integration)
# Stage-6 fix round 3, integration (Z9's class in production.read_bundle)
def test_plan_bundle_counts_strict(E):
    """Fix round 3 integration (G3's note, Z9's class): production.read_bundle, which plan --design uses, parses each
    counts file's verified bytes with design.parse_counts, the reader design.read_bundle uses: a counts file whose
    digest is re-pinned in design_meta.json but which repeats a graph (before: the last line silently won), writes a
    count as '+8' or 0, has another separator, a negative or extra field, or no final newline is refused, by
    read_bundle and by plan (nothing created); the synthetic bundle as freeze writes it is accepted."""
    p=E.M.prod;B=synth_bundle(E,E.td/'z9p_B');n=0
    assert all(len(v)>0 for v in p.read_bundle(B)['counts'].values())
    name='counts/a_free_L3.txt';orig=(B/name).read_bytes();g,c=orig.split(b'\n',1)[0].split(b' ')
    cases=[('repeated graph',orig+g+b' 99\n'),('plus sign',orig.replace(b' '+c+b'\n',b' +'+c+b'\n',1)),('zero count',orig.replace(b' '+c+b'\n',b' 0\n',1)),
           ('tab',orig.replace(b' ',b'\t',1)),('two spaces',orig.replace(b' ',b'  ',1)),('negative',orig.replace(b' '+c+b'\n',b' -'+c+b'\n',1)),
           ('extra field',orig.replace(b'\n',b' 1\n',1)),('no final newline',orig[:-1]),('blank line',orig+b'\n')]
    meta0=(B/'design_meta.json').read_bytes()
    try:
        for what,data in cases:
            (B/name).write_bytes(data);m=json.loads(meta0);m['counts_sha256'][name]=hashlib.sha256(data).hexdigest();(B/'design_meta.json').write_text(json.dumps(m,indent=1)+'\n')
            try:p.read_bundle(B);raise AssertionError(f'read_bundle accepted a counts file with {what}')
            except ValueError as e:assert 'a_free_L3.txt'in str(e)and ('is not "<graph> <positive count>"'in str(e)or 'newline-terminated'in str(e)),(what,str(e));n+=1
            d=E.td/f'z9p_plan_{n}';r=E.plan(d,'--design',B,'--test-graphs',2,'--bootstrap-chunk',4,'--shards',1,seed=SEED+220+n,expect=1)
            assert 'a_free_L3.txt'in r.stderr and gone(d),(what,r.stderr[-400:]);n+=1
    finally:(B/name).write_bytes(orig);(B/'design_meta.json').write_bytes(meta0)
    assert p.read_bundle(B)['counts'][('a','free',3)][int(g)]==int(c)
    ok('fix3_integration_plan_design_bundle_counts_parsed_strictly',refusals=n)

TESTS+=(('z9_plan_counts',lambda c:test_plan_bundle_counts_strict(c.E)),)

# ================================================================ Stage-6 fix round 4, group G2 (W4-W9, W11, W23, W24)
def ldd_probe(C,out:bytes,target,counter=None,identity=None):
    """common.fingerprint of `target` with the ldd probe's output replaced by `out` (the Z6 stub)."""
    real_run=subprocess.run
    def fake_run(cmd,*a,**k):
        if list(cmd)[:1]==['ldd']:return subprocess.CompletedProcess(cmd,0,out,None)
        return real_run(cmd,*a,**k)
    with mock.patch.object(C.subprocess,'run',fake_run):return C.fingerprint(target,counter,identity)

def test_loader_overrides(E):
    """W7 (S6-C-R4-01): the runtime identity did not show WHICH implementation of an interposed function runs. (a) A
    claim refuses (64) to run under LD_PRELOAD, LD_AUDIT or LD_DYNAMIC_WEAK (set, even empty), naming it, before
    anything is pinned or run (no runtime_identity.json, cpu_vendor.json or checkpoint; claim_io 'loader override
    refused'); without it the claim runs. (b) The lane worker refuses (64) at once, before any claim. (c) Objects that
    ldd lists by path (preloaded through /etc/ld.so.preload) in another ORDER give another runtime identity (before the
    fix the sorted library map made A,B and B,A equal); GLIBC_TUNABLES, when set, is part of it; the identity of a node
    with neither is the pre-fix one, field for field; a fingerprint without preload_order takes its path entries in
    their recorded order. (d) End to end: the first claim pins the order A,B; a claim with B,A stops with 64 naming
    preload_order."""
    C=E.M.common;p=E.M.prod;n=0
    d=E.td/'w7';E.small(d,'--checkpoint-tasks',4,'--shards',1,seed=SEED+300);m=manifest(d);j=m['jobs'][0]
    for var,val in (('LD_PRELOAD','/x/A.so:/x/B.so'),('LD_AUDIT','/x/audit.so'),('LD_DYNAMIC_WEAK','')):
        with mock.patch.dict(os.environ,{var:val}):r=E.run(d,j['id'],expect=1)
        assert r.returncode==64 and var in r.stderr and 'dynamic-loader override'in r.stderr and '"status": "loader override refused"'in r.stdout,(var,r.returncode,r.stderr[-500:])
        assert not (d/'runtime_identity.json').exists()and not (d/'cpu_vendor.json').exists()and not list((d/'groups'/j['group']).glob('checkpoints/*.json')),var;n+=1
    E.run(d,j['id']);assert (d/'runtime_identity.json').exists()
    assert C.loader_overrides({'PATH':'/bin','GLIBC_TUNABLES':'x'})=={}
    assert C.loader_overrides({'LD_PRELOAD':'/x/A.so:/x/B.so','LD_DYNAMIC_WEAK':'','LD_AUDIT':'/x/au.so'})=={'LD_PRELOAD':'/x/A.so:/x/B.so','LD_AUDIT':'/x/au.so','LD_DYNAMIC_WEAK':''}
    dl=E.td/'w7_lanes';lanes_plan(E,dl,seed=SEED+302);tool(E.pkg,'lanes.py','queue',dl)
    cp=tool(E.pkg,'lanes.py','worker',dl,env={'SLURM_JOB_ID':'7300','C8_LANE_SECONDS':'36000','LD_PRELOAD':'/nonexistent/libw7.so'},check=False)
    assert cp.returncode==64 and 'LD_PRELOAD'in cp.stderr and 'nothing was claimed or run'in cp.stderr,(cp.returncode,cp.stderr[-500:])
    assert not list((dl/'lanes/claims').glob('*.json'))and not list((dl/'lanes/logs').glob('*.log'))and not list(dl.glob('groups/*/checkpoints/*.json'));n+=1
    # (c) the identity: the order of path-listed (preloaded) objects and GLIBC_TUNABLES
    t=E.td/'w7_ldd';t.mkdir();(t/'ld-2.28.so').write_bytes(b'ld.so');(t/'libgmp.so.10').write_bytes(b'gmp');(t/'libc.so.6').write_bytes(b'libc')
    A_,B_=t/'libA.so',t/'libB.so';A_.write_bytes(b'interposes expl (A)');B_.write_bytes(b'interposes expl (B)')
    exe=t/'worker';exe.write_bytes(elf_bytes(interp_path=str(t/'ld-2.28.so')))
    def text(order):
        return (f'\tlinux-vdso.so.1 (0x00007ffd5a1f2000)\n'+''.join(f'\t{x} (0x00007f2b1e000000)\n'for x in order)+f'\tlibgmp.so.10 => {t}/libgmp.so.10 (0x00007f2b1c000000)\n'
                f'\tlibc.so.6 => {t}/libc.so.6 (0x00007f2b1b000000)\n\t{t}/ld-2.28.so (0x00007f2b1d000000)\n').encode()
    with mock.patch.dict(os.environ):
        os.environ.pop('GLIBC_TUNABLES',None);fab,fba,f0=(ldd_probe(C,text(o),exe)for o in ([A_,B_],[B_,A_],[]))
    assert fab['preload_order']==[str(A_),str(B_)]and fba['preload_order']==[str(B_),str(A_)]and f0['preload_order']==[]and C.fingerprint_problems(fab,'dynamic')==[]
    assert C.runtime_identity(fab)['preload_order']==[str(A_),str(B_)]and C.runtime_identity(fab)['libraries']==C.runtime_identity(fba)['libraries']
    assert C.runtime_identity_key(fab)!=C.runtime_identity_key(fba),'the same preloaded objects in reversed order gave one runtime identity';n+=1
    old={'schema':'c8-d2-runtime-identity-1','glibc':f0['glibc'],'interpreter_sha256':f0['interpreter']['sha256'],
         'libraries':{k:v['sha256']for k,v in sorted(f0['libraries'].items())},'ldd':'ok'}
    assert C.runtime_identity(f0)==old,(C.runtime_identity(f0),old)  # an ordinary node keeps its pre-fix identity and key
    legacy=dict(fab);legacy.pop('preload_order');assert C.runtime_identity(legacy)==C.runtime_identity(fab)
    with mock.patch.dict(os.environ,{'GLIBC_TUNABLES':'glibc.cpu.hwcaps=-AVX2_Usable'}):ft=ldd_probe(C,text([]),exe)
    assert ft['loader_env']=={'GLIBC_TUNABLES':'glibc.cpu.hwcaps=-AVX2_Usable'}and C.runtime_identity(ft)['loader_env']==ft['loader_env']
    assert C.runtime_identity_key(ft)!=C.runtime_identity_key(f0)and 'loader_env'not in C.runtime_identity(f0);n+=1
    # (d) end to end: the first claim pins A,B; B,A stops with 64
    d2=E.td/'w7run';E.small(d2,'--checkpoint-tasks',4,'--shards',1,seed=SEED+301);m2=manifest(d2)
    stub=lambda order:(lambda target,counter=None,identity=None:ldd_probe(C,text(order),target,counter,identity))
    with mock.patch.object(p,'fingerprint',stub([A_,B_])):E.run(d2,m2['jobs'][0]['id'])
    pin=json.loads((d2/'runtime_identity.json').read_text());assert pin['identity']['preload_order'][:2]==[str(A_),str(B_)],pin['identity']
    j1=m2['jobs'][1]
    with mock.patch.object(p,'fingerprint',stub([B_,A_])):r=E.run(d2,j1['id'],expect=1)
    assert r.returncode==64 and 'another run-time library stack'in r.stderr and 'preload_order'in r.stderr,(r.returncode,r.stderr[-600:])
    assert not list((d2/'groups'/j1['group']/'checkpoints').glob(f's{j1["shard"]:06d}_p*.json'));n+=1
    with mock.patch.object(p,'fingerprint',stub([A_,B_])):E.run(d2,j1['id'])
    ok('W7_loader_overrides_refused_preload_order_and_tunables_in_the_runtime_identity',refusals=n)

def route_b_bundle(dest:Path,inv:dict,im_sha:str,exe_sha:str,gmp:str,test_only:bool=True,reps:int=2,count:int=8,batches:int=2)->Path:
    """A frozen route-(b) design bundle (design.py freeze --numerics dd+mp256 of an exact pilot) over every graph of
    `inv`, its one gate entry (job 570536's form, with the X1-X3 evidence and gmp_library {exact, profile: gmp})
    admitting the executable exe_sha; counts `count`, s = 1."""
    dest.mkdir(parents=True);(dest/'counts').mkdir()
    strata={f'{s}_L{L}':{'s':1}for s in ('free','power')for L in range(3,9)};strata['free_L8_primitive']={'s':1}
    (dest/'design.json').write_text(json.dumps({'strata':strata,'replicates':{f'{s}_L{L}':reps for s in ('free','power')for L in range(3,9)},'batches':batches}))
    cs={}
    for c in 'ab':
        for s in ('free','power'):
            for L in range(3,9):
                name=f'counts/{c}_{s}_L{L}.txt';data=''.join(f'{r["id"]} {count}\n'for r in inv[s][str(L)]).encode();(dest/name).write_bytes(data);cs[name]=hashlib.sha256(data).hexdigest()
    gate={'sha256':'a'*64,'slurm_job':'570536','profile_executable_sha256':exe_sha,
          'F1_coverage':{'free':{'binary128_accepted':29284,'mp_promoted':3541},'power':{'binary128_accepted':50625,'mp_promoted':12568}},
          'source_snapshot_sha256':'5'*64,'F5_team_sizes_verified':True,'gmp_library':{'exact':gmp,'profile':gmp,'f1_baseline_reused':False},
          'inputs_manifest_sha256':im_sha}  # W18 (fix round 4): the gate ran on the bundle's inputs
    meta={'schema':'c8-d2-design-1','provisional':False,'test_only':test_only,'design_sha256':digest(dest/'design.json'),'counts_sha256':cs,
          'inputs_manifest_sha256':im_sha,'rates_identity':'default','numerics':'dd+mp256','pilot':{'numerics':'exact'},'forbidden_seeds':[],
          'profile_recost':{'route':'b','profile':'dd+mp256','approval':'unit test (W8)','exact_pilot':{'numerics':'exact','inputs_manifest_sha256':im_sha},'gates':[gate],
                            'cost_model':{'numerics':'dd+mp256','sha256':'c'*64}}}
    (dest/'design_meta.json').write_text(json.dumps(meta,indent=1)+'\n');return dest

def test_gate_gmp_binding(E):
    """W8 (S6-C-R4-02): a gated profile executable is bound to the libgmp its J-FLAG gate validated. gate_gmp_binding:
    None on the exact path and for an ungated build, the gates' gmp_library.profile for this executable, refused for a
    gated campaign whose gates record none. gmp_binding_problem: the gate's libgmp accepted; another one (also a second
    libgmp by path) refused; an identity without libgmp refused, except for a test-only stand-in (no ELF: ldd
    unavailable, no library); libgmpxx is not libgmp. A test-only route-(b) campaign (fake dd+mp256 build, gate libgmp
    X) records numerics_route.gate_gmp_library [X]; a claim whose (stubbed, dynamic ELF) worker loads libgmp Y stops
    with 64 before anything is pinned or run (before: it ran); with X every claim runs; a campaign whose checkpoints
    were all made with Y (no pin: their identity agrees with itself) is refused by the parallel merge (jobs 1 and 2)
    and the serial merge (before: merged). A NON-test plan refuses a build record whose libgmp is not the gate's and
    accepts the gate's (or no recorded libgmp)."""
    p=E.M.prod;n=0;X='4'*64;Y='9'*64;ex='e'*64
    nr=lambda gated=True,gl='default',exe=ex:{'route':'b','executable_gated':gated,'gates':[{'slurm_job':'570536','sha256':'a'*64,'profile_executable_sha256':exe,
                                                                                         **({'gmp_library':{'exact':X,'profile':X,'f1_baseline_reused':False}}if gl=='default'else({'gmp_library':gl}if gl is not None else{}))}]}
    # a test-only route-(b) campaign of a fake dd+mp256 build
    fx=json.loads((E.fixture/'inventory.json').read_text());exe=E.pkg/'bin/c8d2_gmp_dd+mp256';exe.write_text(FAKE_SHEBANG+(ROOT/'tests/fake_worker.py').read_text());exe.chmod(0o755)
    cmd_=cost_model_for(E,None);cmd_['numerics']='dd+mp256';cmf=E.td/'w8_cm_dd.json';cmf.write_text(json.dumps(cmd_))
    try:
        B=route_b_bundle(E.td/'w8_B',fx,digest(E.fixture/'manifest.json'),digest(exe),X)
        d=E.td/'w8';E.plan(d,'--design',B,'--test-graphs',2,'--cost-model',cmf,'--shards',1,'--numerics','dd+mp256','--approved-numerics-change','unit test (W8)',seed=SEED+310)
        m=manifest(d);assert m['numerics_route']['executable_gated']is True,m['numerics_route']
        lib=lambda path,sha:{'path':path,'resolved':path,'sha256':sha}
        def fp_with(sha):
            real=p.fingerprint
            def fake(target,counter=None,identity=None):
                x=real(target,counter,identity)
                x.update(glibc='glibc 2.35',ldd_error=None,interpreter={'path':'/lib64/ld.so','resolved':'/lib64/ld.so','sha256':'1'*64},preload_order=[],loader_env={},
                         libraries={'libgmp.so.10':lib('/usr/lib/libgmp.so.10',sha),'libc.so.6':lib('/lib/libc.so.6','3'*64)})
                return x
            return fake
        j0=m['jobs'][0]
        with mock.patch.object(p,'elf_kind',lambda path:'dynamic'),mock.patch.object(p,'fingerprint',fp_with(Y)):r=E.run(d,j0['id'],expect=1)
        assert r.returncode==64 and '"status": "gate libgmp binding refused"'in r.stdout and '570536'in r.stderr and 'not the libgmp'in r.stderr,(r.returncode,r.stderr[-600:])
        assert not (d/'runtime_identity.json').exists()and not (d/'cpu_vendor.json').exists()and not list(d.glob('groups/*/checkpoints/*.json'));n+=1
        with mock.patch.object(p,'elf_kind',lambda path:'dynamic'),mock.patch.object(p,'fingerprint',fp_with(X)):E.run_all(d)
        ck=sorted(d.glob('groups/*/checkpoints/*.json'));assert ck
        # every checkpoint made with libgmp Y and no pin (claims before W8): one consistent identity, refused by both merges
        (d/'runtime_identity.json').unlink()
        for f in ck:
            x=json.loads(f.read_text());x['runtime']['fingerprint']['libraries']['libgmp.so.10']['sha256']=Y;f.write_text(json.dumps(x))
        g=m['jobs'][0]['group']
        for args in (('--jobs',1),('--jobs',2),('--serial',)):
            r=cli(p,'merge',d,'--group',g,*args,expect=1)
            assert 'not bound to its gate\'s libgmp'in r.stderr and not (d/'groups'/g/'merged.json').exists(),(args,r.stderr[-500:]);n+=1
        # W8 with W10 (fix round 4, integration): calibrate.measure validates checkpoints as the merges do, the gate's libgmp
        # included (before: measured the Y checkpoints' timings)
        try:E.M.cal.measure(d);raise AssertionError('calibrate.measure accepted checkpoints of another libgmp')
        except ValueError as e:assert 'not bound to its gate\'s libgmp'in str(e)and 'nothing calibrated'in str(e),str(e);n+=1
        for f in ck:
            x=json.loads(f.read_text());x['runtime']['fingerprint']['libraries']['libgmp.so.10']['sha256']=X;f.write_text(json.dumps(x))
        cli(p,'merge',d,'--group',g)
        cm_=E.M.cal.measure(d);assert cm_['source']['numerics']=='dd+mp256'and cm_['rows'],cm_  # the gate's libgmp: measured
        assert m['numerics_route']['gate_gmp_library']==[X],m['numerics_route']  # recorded by the plan
    finally:exe.unlink()
    assert p.gate_gmp_binding({'numerics_route':None,'executable_sha256':ex})is None and p.gate_gmp_binding({'numerics_route':nr(False),'executable_sha256':ex})is None
    assert p.gate_gmp_binding({'numerics_route':nr(),'executable_sha256':ex})=={X}
    for bad in (nr(gl=None),nr(gl={'exact':X}),nr(gl={'profile':'X'}),nr(exe='f'*64)):
        try:p.gate_gmp_binding({'numerics_route':bad,'executable_sha256':ex});raise AssertionError(f'accepted {bad}')
        except ValueError as e:assert 'record no libgmp'in str(e),str(e);n+=1
    I=lambda libs,ldd='ok':{'libraries':libs,'ldd':ldd}
    assert p.gmp_binding_problem(I({'libgmp.so.10':X,'libc.so.6':'1'*64}),{X},False)is None
    assert p.gmp_binding_problem(I({'libgmpxx.so.4':Y,'libgmp.so.10':X}),{X},False)is None
    for ident,test_only,needle in ((I({'libgmp.so.10':Y}),False,'not the libgmp its J-FLAG gate validated'),(I({'libgmp.so.10':X,'/opt/b/libgmp.so.10':Y}),True,'not the libgmp'),
                                   (I({'libc.so.6':'1'*64}),True,'names no libgmp'),(I({},'unavailable'),False,'names no libgmp'),(None,True,'names no libgmp')):
        why=p.gmp_binding_problem(ident,{X},test_only);assert why and needle in why,(ident,why);n+=1
    assert p.gmp_binding_problem(I({},'unavailable'),{X},True)is None
    # a NON-test plan: the build record's libgmp against the gate's
    N=nontest_package(E);nexe=N.pkg/'bin/c8d2_gmp_dd+mp256';nexe.write_text(FAKE_SHEBANG+(ROOT/'tests/fake_worker.py').read_text());nexe.chmod(0o755)
    ninv=json.loads((N.pkg/'inputs/inventory.json').read_text())
    NB=route_b_bundle(E.td/'w8_NB',ninv,digest(N.pkg/'inputs/manifest.json'),digest(nexe),X,test_only=False,reps=32,count=256)
    ncm=cost_model_for(E,None);ncm['numerics']='dd+mp256';ncmf=E.td/'w8_ncm.json';ncmf.write_text(json.dumps(ncm))
    def nplan(dd,seed,expect):
        cp=tool(N.pkg,'production.py','plan',dd,'--seed',seed,'--design',NB,'--threads',2,'--checkpoint-tasks',8,'--shards',1,'--cost-model',ncmf,'--forbid-seeds-from',N.log,
                '--numerics','dd+mp256','--approved-numerics-change','unit test (W8)',env=N.env,check=False)
        assert (cp.returncode==0)==(expect==0),(dd.name,cp.returncode,cp.stderr[-800:]);return cp
    log0=N.log.read_bytes()
    fake_build_record(nexe,'gmp','dd+mp256',gmp_library={'soname':'libgmp.so.10','sha256':Y})
    dd=E.td/'w8_nontest_other';cp=nplan(dd,SEED+311,1)
    assert 'names libgmp'in cp.stderr and 'W8'in cp.stderr and gone(dd)and N.log.read_bytes()==log0,cp.stderr[-500:];n+=1
    fake_build_record(nexe,'gmp','dd+mp256',gmp_library={'soname':'libgmp.so.10','sha256':X})
    dd=E.td/'w8_nontest_gate';nplan(dd,SEED+312,0);mm=manifest(dd)
    assert mm['test_only']is False and mm['numerics_route']['gate_gmp_library']==[X]and mm['numerics_route']['executable_gated']is True,mm['numerics_route']
    ok('W8_gated_executable_bound_to_the_gate_libgmp_at_plan_claim_and_merge',refusals=n)

def task_file(path:Path,rows:int,uid0:int=0)->dict:
    """A synthetic per-index task file of `rows` six-integer lines (W9) and its manifest job entry."""
    h=hashlib.sha256();nb=0
    with path.open('wb')as f:
        for k in range(0,rows,100000):
            piece=''.join(f'{u} {u%2} {u%7} {u%997} {u%997+1} 4096\n'for u in range(uid0+k,uid0+min(rows,k+100000))).encode();f.write(piece);h.update(piece);nb+=len(piece)
    return {'id':0,'tasks_file':path.name,'tasks':rows,'tasks_bytes':nb,'tasks_sha256':h.hexdigest()}

def test_stream_tasks(E):
    """W9 (S6-C-R4-03): a claim no longer reads, decodes and keeps every task row of its index. (a) snapshot_tasks copies
    and verifies the task file into the job-private runtime (refusing a changed byte), snapshot_blocks streams it in
    blocks of T: on synthetic files of 100,000 and 1,000,000 rows the traced Python peak of the whole stream is below 4
    MiB and grows by less than 1 MiB with the 10x larger index (job_rows held every row); a 5-field line, an
    unterminated last line and a wrong row count are refused. (b) production.py run --max-blocks 1 of an index of 1,024
    and of 131,072 tasks (T = 1,024, one full block each): the traced peaks differ by less than 8 MiB (before: the
    131,072 rows materialized). (c) tools/stage_runtime.py stage of the same two indices: likewise (before: job_rows). (d) The
    per-task Python peak of a block, measured as the difference of one-block claims at T = 256 and T = 2048, is below
    production.TASK_ROW_PEAK_BYTES (16 KiB), the allowance est_peak_bytes adds per task of a block."""
    import tracemalloc
    p=E.M.prod;n=0
    def peak(fn):
        tracemalloc.start()
        try:tracemalloc.reset_peak();fn();return tracemalloc.get_traced_memory()[1]
        finally:tracemalloc.stop()
    # (b), (c): one-block claims and staging of a small and a large index
    cm=E.td/'w9_cm.json';cm.write_text(json.dumps(cost_model_for(E,None,lambda c,s,L,r:40. if (c,s,L)==('a','free',3)else 1e-9)))
    camps={}
    for name,npts,T in (('small',512,1024),('large',65536,1024),('t256',1024,256),('t2048',1024,2048)):
        d=E.td/f'w9_{name}'
        cli(p,'plan',d,'--seed',SEED+320+len(camps),'--threads',2,'--pilot','--points',npts,'--replicates',2,'--test-graphs',4,'--cost-model',cm,
            '--shards',4,'--min-chunk',1,'--checkpoint-tasks',T)
        m=manifest(d);j=next(x for x in m['jobs']if x['group']=='a_free_L3');camps[name]=(d,j)
    assert camps['small'][1]['tasks']==1024 and camps['large'][1]['tasks']==131072 and camps['t2048'][1]['tasks']==2048,{k:v[1]['tasks']for k,v in camps.items()}
    runp={k:peak(lambda d=d,j=j:E.run(d,j['id'],'--max-blocks',1))for k,(d,j) in camps.items()}
    assert runp['large']-runp['small']<8*2**20,runp;n+=1
    import stage_runtime as SR
    stp={}
    for k in ('small','large'):
        d,j=camps[k];dest=E.td/f'w9_stage_{k}';stp[k]=peak(lambda d=d,j=j,dest=dest:SR.stage(d,dest,j['id']))
    assert stp['large']-stp['small']<8*2**20,stp;n+=1
    per_row=(runp['t2048']-runp['t256'])/(2048-256)
    assert 0<per_row<p.TASK_ROW_PEAK_BYTES,(per_row,runp);n+=1
    t=E.td/'w9';t.mkdir();peaks={}
    for rows in (100000,1000000):
        j=task_file(t/f'tasks_{rows}.tsv',rows);snap=t/f'snap_{rows}.tsv';T=1000
        def stream():
            p.snapshot_tasks(t,j,snap);c=0
            for b in p.snapshot_blocks(snap,j,T):assert len(b)<=T;c+=len(b)
            assert c==rows
        peaks[rows]=peak(stream);snap.unlink()
    assert peaks[1000000]<4*2**20 and peaks[1000000]-peaks[100000]<2**20,peaks;n+=1
    j=task_file(t/'tasks_bad.tsv',1000);data=(t/'tasks_bad.tsv').read_bytes()
    (t/'tasks_bad.tsv').write_bytes(data[:10]+bytes([data[10]^1])+data[11:])
    try:p.snapshot_tasks(t,j,t/'snap_bad.tsv');raise AssertionError('a changed task file was snapshot')
    except ValueError as e:assert 'differs from the manifest pin'in str(e);n+=1
    for what,body,rows in (('a 5-field line',b'1 2 3 4 5\n',1),('an unterminated last line',b'1 2 3 4 5 6',1),('a wrong row count',b'1 2 3 4 5 6\n',2)):
        f=t/'snap_x.tsv';f.write_bytes(body);jx={'id':9,'tasks_file':'x','tasks':rows}
        try:list(p.snapshot_blocks(f,jx,4));raise AssertionError(f'accepted {what}')
        except ValueError as e:assert 'malformed task file'in str(e),what;n+=1
    ok('W9_task_rows_streamed_from_a_verified_snapshot_memory_bounded_in_the_index_size',checks=n,stream_peaks=peaks,run_peaks=runp,stage_peaks=stp,
       per_task_row_bytes=round(per_row),allowance=p.TASK_ROW_PEAK_BYTES)

def test_calibration_identity(E):
    """W11 (S6D-R4-02), production.calibration_row: a calibration row is used only under the numerics and rates
    identity it was measured with (its source). Direct: an exact/default row is returned for an exact/default plan and
    refused, naming both identities, for a dd+mp256 plan or a rate map; a row without a recorded identity is refused;
    C7(2)'s pooled rows are never found. Plan: with tools/calibration.json holding campaign-keyed rows of every group
    measured under a rate map (an exact sweep under --rates that updated the default file), a default-rate test-only
    plan on the calibrated-proxy basis is refused, nothing created (before: planned with the map's speed); with rows of
    its own identity it plans."""
    p=E.M.prod;n=0;src=lambda nx,ri:{'run':'/x/sweep','numerics':nx,'rates_identity':ri}
    row=lambda nx='exact',ri='default':{'seconds_per_proxy_unit':2e-8,'source':src(nx,ri)}
    cal=lambda **kw:{'schema':'c8-d2-calibration-1','backends':{'gmp':{c:{s:{str(L):row(**kw)for L in range(3,9)}for s in ('free','power')}for c in 'ab'}}}
    rid='7'*64
    f=E.pkg/'tools/calibration.json';orig=f.read_bytes()
    try:
        replace_bytes(f,json.dumps(cal(ri=rid),indent=1).encode())
        d=E.td/'w11_map_rows';r=E.plan(d,'--pilot','--points',8,'--replicates',2,'--test-graphs',2,'--shards',1,expect=1,seed=SEED+330)
        assert 'W11'in r.stderr and rid in r.stderr and gone(d),r.stderr[-500:];n+=1
        replace_bytes(f,json.dumps(cal(),indent=1).encode())
        d=E.td/'w11_own_rows';E.plan(d,'--pilot','--points',8,'--replicates',2,'--test-graphs',2,'--shards',1,seed=SEED+331)
        assert manifest(d)['cost_basis']=='calibrated_proxy'
    finally:replace_bytes(f,orig)
    assert p.calibration_row(cal(),'gmp','a','free',8)['seconds_per_proxy_unit']==2e-8 and p.calibration_row(cal(),'gmp','a','free',8,'exact','default')
    for doc,args,needle in ((cal(),('dd+mp256','default'),"numerics 'exact'"),(cal(),('exact',rid),"rates identity 'default'"),(cal(ri=rid),('exact','default'),f"rates identity '{rid}'"),
                            (cal(nx='dd+mp256'),('exact','default'),"numerics 'dd+mp256'")):
        try:p.calibration_row(doc,'gmp','b','power',5,*args);raise AssertionError(f'accepted {args}')
        except ValueError as e:assert needle in str(e)and 'W11'in str(e),(args,str(e));n+=1
    nos=cal();nos['backends']['gmp']['a']['free']['3'].pop('source')
    try:p.calibration_row(nos,'gmp','a','free',3);raise AssertionError('accepted a row without a source')
    except ValueError as e:assert 'None'in str(e);n+=1
    assert p.calibration_row(json.loads((ROOT/'reference/c7d2_hpc_a55958f/tools/calibration.json').read_text()),'gmp','a','free',7)is None
    ok('W11_calibration_rows_used_only_under_their_numerics_and_rates_identity',refusals=n)

def test_no_reread(E):
    """W23 (host residual) and its class: nothing assemble and combine checked is read again. (a) assemble.evaluate of
    a NON-test campaign whose pinned design_meta.json changes right after production.design_bundle checked it (here: a
    trailing space, the same counts digests) is refused, naming the campaign's sha256 (before: the coverage guard
    parsed the second read). (b) combine.load_batch of a test-only batch likewise (combine.test_coverage). (c) The
    coverage guard parses each counts file with design.parse_counts: a verified file with '+8' or a repeated graph is
    refused (before: int() took them). (d) evaluate's inventory and (e) load_batch's group seeds come from bytes
    verified against the campaign's pins: a whitespace change after load_campaign is refused (before: re-read
    unverified). (f) The order-8 module is executed from the bytes whose sha256 was checked (a loader re-read is never
    used) and the result records that sha256; (g) two_loop() returns the sha256 of the bytes it parsed. The same class in
    production and lanes: (h) the serial merge reads a verified private copy of tasks.sqlite (a file changed after
    merge's digest check is refused); (i) a lane reads cost_model.json from bytes verified against the manifest pin."""
    p,A,CB=E.M.prod,E.M.asm,E.M.comb;n=0
    B=synth_bundle(E,E.td/'w23_B')
    d=E.td/'w23';E.plan(d,'--design',B,'--test-graphs','all','--bootstrap-chunk',4,'--shards',1,seed=SEED+340);E.run_all(d);cli(p,'merge',d)
    m=manifest(d);pinned=d/'design_bundle/design_meta.json';meta0=pinned.read_bytes()
    real_load=A.load_campaign
    def nontest(directory,accept_tool_change=False):
        m_,*rest=real_load(directory,accept_tool_change);return (dict(m_,test_only=False),*rest)
    assert A.evaluate(d,0)['test_only']is True
    with mock.patch.object(A,'load_campaign',nontest):A.evaluate(d,0)  # the coverage guard passes on the untouched campaign
    real_db=p.design_bundle
    def swapped(directory,m_,override=None):
        b=real_db(directory,m_,override);(b/'design_meta.json').write_bytes(meta0+b' ');return b
    try:
        with mock.patch.object(A,'load_campaign',nontest),mock.patch.object(p,'design_bundle',swapped):
            try:A.evaluate(d,0);raise AssertionError('evaluate used a design_meta.json other than the one design_bundle checked')
            except ValueError as e:assert m['design']['meta_sha256']in str(e)and 'design_meta.json'in str(e),str(e);n+=1
        pinned.write_bytes(meta0)
        with mock.patch.object(p,'design_bundle',swapped):
            try:CB.load_batch(d,True);raise AssertionError('load_batch used a design_meta.json other than the one design_bundle checked')
            except ValueError as e:assert m['design']['meta_sha256']in str(e),str(e);n+=1
    finally:pinned.write_bytes(meta0)
    CB.load_batch(d,True)
    # (c) the counts parsed strictly (a bundle whose meta pins the edited counts file)
    inv=json.loads((E.fixture/'inventory.json').read_text())
    groups={(c,s,L):{int(r['id']):8 for r in inv[s][str(L)]}for c in 'ab'for s in ('free','power')for L in range(3,9)}
    C2=synth_bundle(E,E.td/'w23_C');assert A.coverage_guard(groups,inv,8,C2,1,meta_sha256=digest(C2/'design_meta.json'))['groups']==24
    name='counts/a_free_L3.txt';orig=(C2/name).read_bytes();g0=orig.split(b' ',1)[0]
    for what,data in (('+8',orig.replace(b' 8\n',b' +8\n',1)),('a repeated graph',orig+g0+b' 8\n')):
        (C2/name).write_bytes(data);mm=json.loads((C2/'design_meta.json').read_text());mm['counts_sha256'][name]=hashlib.sha256(data).hexdigest()
        (C2/'design_meta.json').write_text(json.dumps(mm))
        try:A.coverage_guard(groups,inv,8,C2,1);raise AssertionError(f'the coverage guard parsed {what}')
        except ValueError as e:assert 'a_free_L3.txt'in str(e),(what,str(e));n+=1
    # (d), (e): the inventory and the group configs re-read after load_campaign
    invf=E.fixture/'inventory.json';inv0=invf.read_bytes();cfgf=d/'groups/a_free_L3/config.json';cfg0=cfgf.read_bytes()
    def then(fn):
        def wrapped(directory,accept_tool_change=False):
            out=real_load(directory,accept_tool_change);fn();return out
        return wrapped
    def nontest_then(fn):
        def wrapped(directory,accept_tool_change=False):
            m_,*rest=real_load(directory,accept_tool_change);fn();return (dict(m_,test_only=False),*rest)
        return wrapped
    try:
        with mock.patch.object(A,'load_campaign',nontest_then(lambda:replace_bytes(invf,inv0+b' '))):
            try:A.evaluate(d,0);raise AssertionError('evaluate parsed a re-read inventory.json')
            except ValueError as e:assert 'Checksum mismatch'in str(e)and 'inventory.json'in str(e),str(e);n+=1
    finally:replace_bytes(invf,inv0)
    try:
        with mock.patch.object(A,'load_campaign',then(lambda:replace_bytes(cfgf,cfg0+b' '))):
            try:CB.load_batch(d,True);raise AssertionError('load_batch took a seed from a re-read config.json')
            except ValueError as e:assert 'Checksum mismatch'in str(e)and 'config.json'in str(e),str(e);n+=1
    finally:replace_bytes(cfgf,cfg0)
    # (f) the module is executed from the verified bytes; (g) two_loop's sha256 is of the bytes parsed
    import importlib.machinery
    real_get=importlib.machinery.SourceFileLoader.get_data
    def tampered(self,path):
        data=real_get(self,path)
        return data+b'\nW23_TAMPERED = True\n'if str(path).endswith('order8_assembly.py')else data
    saved=(A._OA,getattr(A,'_OA_SHA',None))
    try:
        A._OA=None
        with mock.patch.object(importlib.machinery.SourceFileLoader,'get_data',tampered):mod=A.vendored()
        assert not hasattr(mod,'W23_TAMPERED'),'the order-8 module was executed from a re-read of its file';n+=1
        pin=next(x['sha256']for x in json.loads((E.pkg/'tools/VENDORED.json').read_text())['files']if x['path']=='order8_assembly.py');assert A._OA_SHA==pin
    finally:A._OA,A._OA_SHA=saved
    tl=E.pkg/'inputs/two_loop.json';real_rb=Path.read_bytes;alt=json.dumps({'B2':[0.0]*len(json.loads(tl.read_text())['B2'])}).encode()
    with mock.patch.object(Path,'read_bytes',lambda self:alt if self.resolve()==tl.resolve()else real_rb(self)):b2,sha=A.two_loop()
    assert sha==hashlib.sha256(alt).hexdigest()and not b2.any(),'two_loop recorded the sha256 of another read than the one it parsed';n+=1
    # (h) the serial (reference) merge reads a private copy of tasks.sqlite verified against its pin: a file changed after
    # merge's check_tasks_db (trailing bytes, which SQLite ignores) is refused (before: the shared file was opened again)
    ds=E.td/'w23_serial';E.small(ds,'--checkpoint-tasks',4,'--shards',1,seed=SEED+341);E.run_all(ds);gs=manifest(ds)['groups'][0]['name']
    tdb=ds/'groups'/gs/'tasks.sqlite';tdb0=tdb.read_bytes();real_chk=p.check_tasks_db
    def chk_then_change(pp,cfg):
        real_chk(pp,cfg)
        if pp.name==gs:replace_bytes(pp/'tasks.sqlite',tdb0+b'\0'*4096)
    try:
        with mock.patch.object(p,'check_tasks_db',chk_then_change):r=cli(p,'merge',ds,'--group',gs,'--serial',expect=1)
        assert 'Checksum mismatch'in r.stderr and 'tasks.sqlite'in r.stderr and not (ds/'groups'/gs/'merged.json').exists(),r.stderr[-400:];n+=1
    finally:replace_bytes(tdb,tdb0)
    cli(p,'merge',ds,'--group',gs,'--serial')
    # (i) a lane reads the campaign's cost model from the bytes the manifest pins: a changed cost_model.json is refused
    # before any claim (before: its class factors were used unverified)
    dl=E.td/'w23_lane';lanes_plan(E,dl,seed=SEED+342);tool(E.pkg,'lanes.py','queue',dl);cmf_=dl/'cost_model.json';cm0=cmf_.read_bytes()
    replace_bytes(cmf_,cm0+b' ')
    try:
        cp=tool(E.pkg,'lanes.py','lane',dl,'--lane',0,'--cpus',0,'--deadline','inf','--job','7400','--stop-seconds',5,check=False)
        assert cp.returncode!=0 and 'Checksum mismatch'in cp.stderr and 'cost_model.json'in cp.stderr,(cp.returncode,cp.stderr[-400:])
        assert not list((dl/'lanes/claims').glob('*.json'))and not list(dl.glob('groups/*/checkpoints/*.json'));n+=1
    finally:replace_bytes(cmf_,cm0)
    ok('W23_assemble_and_combine_never_reread_checked_files',refusals=n)

# Stage-6 fix round 4, G2 (W7, W8, W9, W11, W23; W24 in route_b_records; W4-W6 in gen/test_regress.py and gen/test_keys.py)
TESTS+=(('w7_loader',lambda c:test_loader_overrides(c.E)),('w8_gmp_binding',lambda c:test_gate_gmp_binding(c.E)),('w9_stream',lambda c:test_stream_tasks(c.E)),
        ('w11_calibration',lambda c:test_calibration_identity(c.E)),('w23_no_reread',lambda c:test_no_reread(c.E)))
TEST_NAMES=tuple(n for n,_ in TESTS)

def selection(only:str|None)->list[str]|None:
    """--only NAME,...: the names in table order. None runs every test. Unknown names and an empty list raise ValueError
    (T-03: a misspelled targeted rerun ran nothing and reported "passed")."""
    if only is None:return None
    names=[x.strip()for x in only.split(',')if x.strip()]
    unknown=sorted(set(names)-set(TEST_NAMES))
    if unknown:raise ValueError(f'unknown test name(s) {", ".join(unknown)}; the tests are {", ".join(TEST_NAMES)}')
    if not names:raise ValueError(f'no test named; the tests are {", ".join(TEST_NAMES)}')
    return [n for n in TEST_NAMES if n in names]

def run(only=None):
    """Run the selected tests (None: all) and return the record: status, the requested and the executed selections,
    the passing sub-tests and the failures. A run that executes no test fails."""
    want=None if only is None else selection(only if isinstance(only,str)else ','.join(only))
    executed=[];failed=[]
    with tempfile.TemporaryDirectory(prefix='c8d2_orch_')as td:
        td=Path(td);real=sys.platform.startswith('linux')and (ROOT/'bin/c8d2_gmp').exists()
        pkg=make_package(td)
        # the pre-sweep state the R13 tests assume, whatever the package's active calibration holds by now: the pinned
        # C7(2) calibration (pooled rows only, no campaign-keyed row)
        c7cal=(ROOT/'reference/c7d2_hpc_a55958f/tools/calibration.json').read_bytes()
        if (pkg/'tools/calibration.json').read_bytes()!=c7cal:replace_bytes(pkg/'tools/calibration.json',c7cal)
        M=load_modules(pkg);E=Env(pkg,M,td);os.environ['C8_INPUTS']=str(E.fixture);ctx=NS(E=E,M=M,real=real)
        for name,fn in TESTS:
            if want is not None and name not in want:continue
            executed.append(name)
            try:fn(ctx)
            except Exception as e:  # record and continue: one cluster run reports every failing test
                import traceback;tb=traceback.format_exc();failed.append({'test':name,'error':f'{type(e).__name__}: {e}'[:2000],'traceback':tb[-4000:]})
                print(f'FAIL {name}: {type(e).__name__}: {str(e)[:500]}',flush=True);print(tb[-3000:],flush=True)
    if not executed:failed.append({'test':'(selection)','error':'no test executed'})
    return {'status':'failed'if failed or not executed else'passed','requested':want if want is not None else 'all','executed':executed,
            'tests':RESULTS,'failed':failed,'python':sys.version.split()[0],'platform':sys.platform}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);ap.add_argument('--only',help='NAME,... of: '+', '.join(TEST_NAMES));a=ap.parse_args()
    try:only=selection(a.only)
    except ValueError as e:ap.error(f'--only: {e}')  # exit 2 before any setup (T-03)
    rec=run(only)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1,default=str)+'\n')
    print(json.dumps({'status':rec['status'],'requested':rec['requested'],'executed':len(rec['executed']),'tests':len(rec['tests']),'failed':[f['test']for f in rec['failed']]}))
    sys.exit(0 if rec['status']=='passed'else 1)
