#!/usr/bin/env python3
"""Submission under scheduler truth with durable intents (plan A-ORC-11, A-ORC-12, A-ORC-17; H-e..H-h). Mac only.

The stateful fake Slurm of tests/fake_slurm/ runs either in-process (fast; the seeded interleavings of A-ORC-17 (c) and
(i) and most cases) or as executables on PATH (real processes: SIGKILL, the `timeout -s KILL` shim, the exec guard,
--wrap strings byte for byte). The cases the plan states for `lanes N` and `submit` run the same admission engine
through tests/fake_slurm/driver.py, which builds exactly those job sets; since Stage 3a the real entry points
(slurm_submit.py lanes N, submit, window, resubmit, release) build them from planned campaigns, tested end to end on
the fake Slurm in tests/unit_orchestration.py and tests/test_pipeline.py.
Every case checks the fake scheduler's state as well as the files.

  python3 -B tests/test_submit.py [--quick]      (--quick: 60 instead of 500 seeded interleavings)
"""
from __future__ import annotations
import contextlib,errno,hashlib,io,json,os,random,re,secrets,shlex,shutil,signal,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import ledger,budget,slurm_submit as ss
from common import Refuse
from fake_slurm.core import Fake,InflightKill,inprocess_runner,install
from fake_slurm import driver
BASE='mode=reservation;id=H7E-R;run=11;sub=27;acct_run=32;shared=32;dev_nodes=4'
# A re-split with more development nodes (its own id and a far `until`): C8_COMPUTE_CAP never exceeds the active
# reservation's dev_nodes, so the cases that move the node cap out of the way of another share use one of these.
def WIDE(n:int)->str:return f'mode=reservation;id=TEST-WIDE;run=11;sub=27;acct_run=32;shared=32;dev_nodes={n};until=2036-01-01T00:00:00Z'
G=ledger.INTENT_GRACE
RESULTS=[];QUICK='--quick'in sys.argv
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
def hx():return secrets.token_hex(6)

SHARED=['-A','yun124','-p','shared','--nodes=1','-c','1','--mem=1G','-t','00:05:00','--wrap','date']            # 1/12 SU
SHARED8=['-A','yun124','-p','shared','--nodes=1','-c','8','--mem=16G','-t','01:00:00','--wrap','date']          # 8 SU
COMPUTE=['-A','yun124','-p','compute','--exclusive','--nodes=1','--mem=240G','-t','01:00:00','--wrap','date']    # 128 SU
DEBUG=['-A','yun124','-p','debug','--nodes=1','-c','1','--mem=1G','-t','00:10:00','--wrap','date']

class Killed(BaseException):pass
class IPH(ledger.Hooks):
    """In-process hooks: kills and stalls by step, write faults by point, switches, the fake clock, one event log
    shared with the fake (the lock and filesystem spy)."""
    def __init__(self,log):self.log=log;self.kill={};self.faults={};self.stall={};self.switches=set();self.off=0.0;self.on_point=None;self.poll=0.001
    def point(self,name,**info):
        self.log.append({'event':'point:'+name,**info,'tid':threading.get_ident()})
        if self.on_point:self.on_point(name,info)
        if name in self.stall:self.off+=self.stall.pop(name)
        if name in self.kill:
            self.kill[name]-=1
            if self.kill[name]<=0:del self.kill[name];raise Killed(name)
    def event(self,name,**info):self.log.append({'event':name,**info,'tid':threading.get_ident()})
    def write_fault(self,point,nbytes):return self.faults.pop(point,None)
    def switch(self,name):return name in self.switches
    def offset(self):return self.off
    def advance(self,s):self.off+=s
    def setting(self,name,default):return {'lock_poll':self.poll,'query_timeout':1.0}.get(name,default)

def scripts(d:Path)->Path:
    d.mkdir(parents=True,exist_ok=True)
    (d/'worker.sh').write_text('#!/bin/bash\n# fake lane worker (neutral #SBATCH defaults)\necho worker\n')
    (d/'merge.sh').write_text('#!/bin/bash\n#SBATCH --nodes=1\n#SBATCH --ntasks=1\necho merge\n')
    (d/'work.sh').write_text('#!/bin/bash\n#SBATCH --nodes=1\n#SBATCH --ntasks=1\necho work\n')
    return d

class Site:
    """One in-process site: a memory fake Slurm, C8_ROOT, the hooks; tools called through their main()."""
    def __init__(self,td:Path,name:str,**env):
        self.dir=td/name;self.root=self.dir/'c8';self.root.mkdir(parents=True);self.log=[]
        (self.root/'ledger.jsonl').write_bytes(b'')   # an empty ledger (a missing one with c8d3- jobs visible is a repair block, D.12)
        self.h=IPH(self.log);ledger.HOOKS=self.h
        self.fake=Fake(path=None,sink=self.log);self.fake.now=lambda:time.time()+self.h.off
        budget.RUNNER=inprocess_runner(self.fake)
        self.env={'C8_SITE':'fake','C8_ROOT':str(self.root),'C8_BUDGET_LINE':'dev','C8_RESERVATION':BASE,'C8_COMPUTE_CAP':'4','C8_LOCK_WAIT':'5',
                  'PATH':os.environ['PATH'],'FAKE_SCRIPTS':str(scripts(self.dir/'scripts')),'USER':'zzheng8'}
        self.env.update({k:v for k,v in env.items()if v is not None})
        for k,v in env.items():
            if v is None:self.env.pop(k,None)
    def activate(self):ledger.HOOKS=self.h;budget.RUNNER=inprocess_runner(self.fake)
    def call(self,fn,argv,env=None)->tuple[int,str,str]:
        self.activate();o,e=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(o),contextlib.redirect_stderr(e):
            try:rc=fn(argv,{**self.env,**(env or{})})
            except (Killed,InflightKill)as k:rc=-9;print(f'killed at {k}',file=sys.stderr)
        return rc,o.getvalue(),e.getvalue()
    def raw(self,role,d,*sb,env=None):return self.call(ss.main,['raw','--role',role,'--dir',str(d),'--',*sb],env)
    def lanes(self,n,d,lane_time='01:00:00',dry=False,env=None):
        return self.call(driver.main,['lanes',str(n),'--dir',str(d),'--lane-time',lane_time]+(['--dry-run']if dry else[]),env)
    def submit(self,d,windows,env=None):return self.call(driver.main,['submit','--dir',str(d)]+sum([['--window',w]for w in windows],[]),env)
    def ledger_cmd(self,argv,env=None):return self.call(lambda a,e:ledger.main(a,e),argv,env)
    def budget(self,env=None)->dict:
        self.activate();return budget.report({**self.env,**(env or{})})
    def records(self,kind=None)->list:
        led=ledger.Ledger(ledger.Settings(self.env));led.read(writer=False)
        return [r for r in led.records if kind is None or r['kind']==kind]
    def intents(self)->dict:
        led=ledger.Ledger(ledger.Settings(self.env));led.read(writer=False);return ledger.intent_state(led)
    def d(self,name,kind='runs',plan=False)->Path:
        p=self.root/kind/name if kind=='runs'else self.root/'evidence'/('e'*12)/name
        if plan:p.mkdir(parents=True,exist_ok=True);(p/'manifest.json').write_text(json.dumps({'plan':name})+'\n')
        return p
    def ours(self,n=1,role='lane',partition='compute',state='RUNNING',c=None,**kw)->list:
        out=[]
        for _ in range(n):
            t=hx();cc=c or hx();out+=self.fake.add_job(f'c8d3-{role}-{cc}-{t}',state=state,partition=partition,comment=f'c8d3:{cc}:{"0"*12}:{t}',
                                                      nodes=1,cpus=128 if partition=='compute'else kw.pop('cpus',1),**kw)
        return out
    def others(self,n,user='dsd',partition='compute',state='RUNNING',name='job'):
        return [self.fake.add_job(f'{name}{i}',user=user,partition=partition,state=state,cpus=128 if partition=='compute'else 1)[0]for i in range(n)]
    def c8d2(self,n,state='RUNNING',partition='compute'):
        return [self.fake.add_job(f'c8d2-lane-{hx()}-{hx()}',partition=partition,state=state,cpus=128 if partition=='compute'else 1)[0]for _ in range(n)]
    def spent(self,su,line='dev'):
        role=budget.LINE_PREFIX.get(line,'')+'val';t=hx();c=hx()   # val, pilot_val, prod_val
        return self.fake.add_job(f'c8d3-{role}-{c}-{t}',state='COMPLETED',partition='shared',cpus=1,mem='2G',elapsed=int(round(su*3600)),
                                 time_s=int(round(su*3600))+3600,comment=f'c8d3:{c}:{"0"*12}:{t}')[0]
    def intent(self,partition='compute',role='lane',su=None,tasks=None,line='dev',age=0.0,write=('ledger','file'))->str:
        """An unresolved intent written through the ledger API (both copies by default), as a submitter leaves it."""
        self.activate();s=ledger.Settings(self.env);t=None
        n=len(tasks)if tasks else 1;slots=ss.spec_slots({'partition':partition,'nodes':1,'site':self.env.get('C8_SITE')},n)
        b=budget.profile(self.env).billing_value(partition,1,1,1024.0);su=b*n if su is None else su   # Expanse: 128 on compute, 1 on shared; symmetry: whole nodes
        with ledger.SessionLock(s,'test intent')as lock:
            led=ledger.Ledger(s,lock);led.read(writer=True);t=led.new_token();c=hx()
            p=ledger.payload('intent',[t],token=t,name=f'c8d3-{role}-{c}-{t}',comment=f'c8d3:{c}:{"0"*12}:{t}',role=role,c=c,p='0'*12,dir=str(self.root/'runs'/t),
                             partition=partition,nodes=1,cpus=128 if partition=='compute'else 1,mem_mib=1024.0,time_s=3600,
                             array={'spec':f'0-{n-1}','tasks':list(tasks)}if tasks else None,task_count=n,billing=b,reservation_su=su,slots=slots,line=line,
                             pid=1,mono=ledger.mono(),command='test')
            p['utc']=ledger.now()-age
            ino=off=ln=0
            if 'ledger'in write:ino,off,ln=led.append(p)
            if 'file'in write:led.write_intent_file(p,ino,off,ln)
        return t
    def accept_as(self,t,partition='compute',state='RUNNING',**kw)->str:
        """The scheduler shows the job of intent T (accepted: name and comment carry T)."""
        it=self.intents()[t].payload
        return self.fake.add_job(it['name'],state=state,partition=partition,comment=it['comment'],cpus=it['cpus'],**kw)[0]
    def history(self,cmd=None)->list:return [h for h in self.fake.state()['history']if cmd is None or h['cmd']==cmd]
    def sbatches(self)->list:return [h for h in self.history('sbatch')if '--test-only'not in h['argv']]
    def counts(self)->dict:return self.fake.counts()

def must(rc_out,code,*needles):
    rc,out,err=rc_out
    assert rc==code,(code,rc,err[-1500:],out[-800:])
    for n in needles:assert n in out+err,(n,err[-1500:],out[-600:])
    return out+err

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-12: the billing function and its option resolution (HD17, R19)
def test_billing_function(td):
    P=lambda toks:ss.parse_options(toks,'t')[0]
    def R(cmd,script=(),envo=()):return ss.resolve(list(script),list(envo),P(cmd),None)
    for part,tres,want in (('shared','billing=28800,cpu=8,mem=15G,node=1',8),('shared','billing=14400,cpu=2,mem=8G,node=1',4),('compute','billing=460800,cpu=128,mem=240G,node=1',128)):
        t=budget.parse_tres(tres);assert budget.tres_billing(part,t)==want==t['billing']/3600,(tres,budget.tres_billing(part,t))
        t.pop('billing');assert budget.tres_billing(part,t)==want
    assert R(['-A','yun124','-p','shared','--nodes=1','-c','8','--mem=15G','-t','1:00:00'])['billing']==8
    assert R(['-A','yun124','-p','shared','--nodes=1','-c','2','--mem=8G','-t','1:00:00'])['billing']==4      # memory-charged as 4 cores
    assert R(['-A','yun124','-p','compute','--exclusive','--nodes=1','--mem=240G','-t','1:00:00'])['billing']==128
    r=R(['-A','yun124','-p','shared','--nodes=1','--mem-per-cpu=4G','-c','2','-t','1:00:00']);assert r['mem_mib']==8192 and r['billing']==4
    # precedence: command line, then SBATCH_*, then #SBATCH lines
    script=P(['-c','4','--mem=8G','-t','2:00:00','-p','debug','-A','yun124','--nodes=1'])
    r=ss.resolve(script,[('time','00:20:00'),('mem','6G')],P(['-p','shared','-c','2','--mem=2G']),None)
    assert (r['cpus'],r['mem_mib'],r['time_s'],r['partition'])==(2,2048,1200,'shared')
    r=ss.resolve(script,[('time','00:20:00'),('mem','6G')],P(['-p','shared']),None);assert (r['cpus'],r['mem_mib'],r['time_s'])==(4,6144,1200)
    assert ss.env_options({'SBATCH_MEM_PER_NODE':'6G','SBATCH_TIMELIMIT':'1:00:00','SBATCH_EXCLUSIVE':'1'})==[('mem','6G'),('time','1:00:00')]
    for bad in ((['-A','yun124','-p','shared','--nodes=1','--mem=2G','--mem-per-cpu=1G','-t','1:00:00'],()),       # both memory forms
                (['-A','yun124','-p','shared','--nodes=1','--mem-per-cpu=1G','-t','1:00:00'],P(['--mem=4G'])),  # both, across sources
                (['-A','yun124','-p','shared','--nodes=1','-t','1:00:00'],()),                                   # neither
                (['-A','yun124','-p','shared','--nodes=1','--mem=0','-t','1:00:00'],()),                         # --mem=0
                (['-A','yun124','-p','shared','--nodes=1','--exclusive','-c','2','--mem=4G','-t','1:00:00'],()),
                (['-A','yun124','-p','debug','--exclusive','-c','2','--mem=4G','-t','00:30:00'],()),
                (['-A','yun124','-p','shared','--nodes=1','-c','2','--mem=4G','-t','1:00:00'],P(['--exclusive'])),  # --exclusive from #SBATCH
                (['-p','shared','--nodes=1','--mem=4G','-t','1:00:00'],()),('-A other -p shared --nodes=1 --mem=4G -t 1:00:00'.split(),()),
                (['-A','yun124','-p','shared','--mem=4G','-t','1:00:00'],()),                                    # shared without --nodes=1
                (['-A','yun124','-p','debug','--mem=4G','-t','00:31:00'],()),(['-A','yun124','-p','gpu','--mem=4G','-t','1:00:00'],()),
                (['-A','yun124','-p','shared','--nodes=1','--mem=4G','-t','UNLIMITED'],()),(['-A','yun124','-p','compute','--nodes=2','--mem=4G','-t','1:00:00'],()),
                (['-A','yun124','-p','shared','--nodes=1','--mem=250G','-t','1:00:00'],()),(['-A','yun124','-p','shared','-q','normal','--nodes=1','--mem=4G','-t','1:00:00'],())):
        try:R(*bad)
        except Refuse as e:assert e.code==64,(bad,e)
        else:raise AssertionError(f'not refused: {bad}')
    try:ss.env_options({'SBATCH_REQUEUE':'1'});raise AssertionError('SBATCH_REQUEUE accepted')
    except Refuse as e:assert e.code==64
    for t,s_ in (('30',1800),('5:30',330),('1:00:00',3600),('1-0',86400),('1-02:03',93780),('2-00:00:01',172801)):assert budget.parse_duration(t)==s_,t
    ok('billing_function_f39_option_resolution_and_refusals')

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-12 per-attempt and per-task keys, pure (crafted squeue/sacct lines)
def U(jobid,state,name,part='shared',tl='1:00:00',tres='cpu=8,mem=15G,node=1,billing=28800',start='2026-10-04T10:00:00',used='10:00',comment='(null)',base=None,
      restarts='0',submit='2026-10-04T09:59:00',eligible=None):
    return '|'.join([jobid,base or jobid.split('_')[0],'zzheng8',part,'normal'if part=='compute'else'shared-normal',state,name,'1','8','15G',tl,'None',comment,tres,start,used,
                     restarts,submit,submit if eligible is None else eligible])
def S(jobid,state,name,submit,start='2026-10-04T10:00:00',el='600',tl='01:00:00',alloc='billing=28800,cpu=8,mem=15G,node=1',req='billing=28800,cpu=8,mem=15G,node=1',
      part='shared',raw=None):
    return '|'.join([jobid,raw or jobid.split('_')[0],name,part,state,submit,start,el,tl,alloc,req])
def ev_of(user_lines,rows):
    return budget.Evaluation(budget.Snapshot([],budget.parse_user('\n'.join(user_lines)),budget.parse_sacct('\n'.join(rows),'u'),[]),{})
NM=lambda role='val',t=None:f'c8d3-{role}-{"c"*12}-{t or hx()}'

def test_charges_pure(td):
    n=NM();C=lambda ev:round(ev.lines()['dev']['total'],6)
    assert C(ev_of([],[S('101','COMPLETED',n,'2026-10-04T09:00:00')]))==round(8*600/3600,6)            # 1.33 SU finished
    assert C(ev_of([U('101','RUNNING',n)],[S('101','RUNNING',n,'2026-10-04T09:00:00',el='300')]))==8.0  # 8 SU while live
    assert C(ev_of([],[S('102','COMPLETED',n,'2026-10-04T09:00:00',el='3600',alloc='billing=14400,cpu=2,mem=8G,node=1')]))==4.0  # cpu=2,mem=8G: 4
    # a live requeued lane worker with one NODE_FAIL attempt of 1.5 h: 128 x 1.5 plus its full live reservation (2 h)
    w=NM('lane');ct='billing=460800,cpu=128,mem=240G,node=1'
    ev=ev_of([U('200','RUNNING',w,part='compute',tl='2:00:00',tres=ct)],[S('200','NODE_FAIL',w,'2026-10-04T08:00:00',el='5400',alloc=ct,part='compute',tl='02:00:00'),
                                                                        S('200','RUNNING',w,'2026-10-04T09:31:00',el='60',alloc=ct,part='compute',tl='02:00:00')])
    assert C(ev)==128*1.5+128*2
    # a %8-throttled array of 20 tasks: 6 finished, 8 running, 6 pending; the collapsed pending row adds nothing
    a=NM('off0');lines=[];rows=[]
    for k in range(6):rows.append(S(f'300_{k}','COMPLETED',a,'2026-10-04T08:00:00',el='600',raw=str(400+k)))
    for k in range(6,14):lines.append(U(f'300_{k}','RUNNING',a,base='300'));rows.append(S(f'300_{k}','RUNNING',a,'2026-10-04T08:00:00',el='60',raw=str(400+k)))
    for k in range(14,20):lines.append(U(f'300_{k}','PENDING',a,base='300',tres='cpu=8,mem=15G,node=1,billing=28800',start='N/A',used='0:00'))
    coll=S('300_[14-19%8]','PENDING',a,'2026-10-04T08:00:00',start='Unknown',el='0',alloc='',raw='300')
    hand=6*8*600/3600+14*8*1.0
    assert C(ev_of(lines,rows+[coll]))==round(hand,6)and C(ev_of(lines,rows))==round(hand,6)
    assert C(ev_of([],[coll]))==6*8.0   # not listed by squeue at all: its full reservation, per task
    # a just-finished job: squeue CD after 600 s, sacct still RUNNING: billing x 600 s
    j=NM();assert C(ev_of([U('500','COMPLETED',j,used='10:00')],[S('500','RUNNING',j,'2026-10-04T09:00:00',el='590')]))==round(8*600/3600,6)
    assert C(ev_of([U('501','COMPLETED',j,used='10:00')],[]))==round(8*600/3600,6)
    # a requeue between squeue and sacct: squeue attempt 1 R; sacct attempt 1 NODE_FAIL + attempt 2 PENDING
    r=NM();ev=ev_of([U('600','RUNNING',r)],[S('600','NODE_FAIL',r,'2026-10-04T08:00:00',el='1800'),S('600','PENDING',r,'2026-10-04T08:30:01',start='Unknown',el='0',alloc='')])
    assert C(ev)==8.0+8*0.5
    ctl=ev_of([U('600','PENDING',r,start='N/A',used='0:00')],[S('600','RUNNING',r,'2026-10-04T08:00:00',el='1700')])   # the reversed order (control)
    assert C(ctl)==8.0,'control: sacct before squeue misses attempt 1'
    # a pending job with only ReqTRES, one ReqTRES without billing, and a live line priced from tres-alloc or at 128
    p=NM();assert C(ev_of([U('700','PENDING',p,start='N/A',used='0:00',tres='cpu=2,mem=8G,node=1')],[S('700','PENDING',p,'2026-10-04T09:00:00',start='Unknown',el='0',alloc='',req='cpu=2,mem=8G,node=1')]))==4.0
    assert C(ev_of([],[S('701','PENDING',p,'2026-10-04T09:00:00',start='Unknown',el='0',alloc='',req='billing=14400,cpu=2,mem=8G,node=1')]))==4.0
    q=NM();assert C(ev_of([U('800','RUNNING',q,tres='cpu=4,mem=16G,node=1')],[]))==8.0           # tres-alloc 4 cores, 16G: 8 per hour
    e=ev_of([U('801','RUNNING',q,tres='')],[]);assert C(e)==128.0 and e.lines()['dev']['unpriced']
    # lines: c8d2 never, pilot_ only in pilot, an unparseable c8d3- name in both, an unrecorded c8d3 job counts
    ev=ev_of([],[S('900','COMPLETED','c8d2-lane-'+'a'*12+'-'+'b'*12,'2026-10-04T09:00:00',el='3600'),S('901','COMPLETED',NM('pilot_val'),'2026-10-04T09:00:00',el='3600'),
                 S('902','COMPLETED','c8d3-garbled name','2026-10-04T09:00:00',el='3600'),S('903','COMPLETED',NM('val'),'2026-10-04T09:00:00',el='3600')])
    L=ev.lines();assert (L['dev']['total'],L['pilot']['total'])==(16.0,16.0)
    # a requeued job whose LAST attempt ended while sacct has only the first (NODE_FAIL): the finished squeue line is that
    # last attempt (another start) and is charged; the older attempt's finished row does not account for it
    rq=NM('val');ct='billing=460800,cpu=128,mem=240G,node=1'
    line=U('950','COMPLETED',rq,part='compute',tl='2:00:00',tres=ct,start='2026-10-04T11:00:00',used='50:00')
    row1=S('950','NODE_FAIL',rq,'2026-10-04T09:00:00',start='2026-10-04T09:00:10',el='3000',alloc=ct,part='compute',tl='02:00:00')
    assert C(ev_of([line],[row1]))==round(2*128*3000/3600,6)
    row2=S('950','COMPLETED',rq,'2026-10-04T10:50:00',start='2026-10-04T11:00:00',el='3000',alloc=ct,part='compute',tl='02:00:00')
    assert C(ev_of([line],[row1,row2]))==round(2*128*3000/3600,6)          # delivered: the same total, counted once
    tok=rq[-12:];it=ledger.Intent(tok);it.ledger={'token':tok,'reservation_su':256.0,'line':'dev','slots':{'normal_run':1},'array':None}
    ev=budget.Evaluation(budget.Snapshot([],budget.parse_user(line),budget.parse_sacct(row1,'u'),[]),{tok:it})
    assert ev.evidence(it)[0]is None and C(ev)==256.0   # (a) refuses: the attempt squeue shows has no row yet; the floor (2 h reservation) holds
    ev=budget.Evaluation(budget.Snapshot([],budget.parse_user(line),budget.parse_sacct(row1+'\n'+row2,'u'),[]),{tok:it})
    rule,charge,_=ev.evidence(it);assert rule=='terminal'and abs(charge-2*128*3000/3600)<1e-9,(rule,charge)
    # a pending-cancelled array task line (never started) is accounted by its never-started row, also with a start printed
    nc=NM('val');assert budget.accounted(budget.parse_user(U('960','CANCELLED',nc,start='2026-10-04T11:00:00',used='0:00'))[0],
                                         budget.parse_sacct(S('960','CANCELLED',nc,'2026-10-04T10:00:00',start='None',el='0'),'u'))
    ok('charges_per_attempt_per_task_requeue_order_tres_lines_last_attempt_matched')

def test_query_order_and_epoch(td):
    s=Site(td,'epoch');calls=[];real=budget.RUNNER
    def spy(argv,env,t):calls.append(argv[0]+(' -s'if '-s'in argv else''));return real(argv,env,t)
    budget.RUNNER=spy;budget.Snapshot.take(s.env,account=True);budget.RUNNER=real
    assert calls==['squeue','squeue','sacct','sacct -s'],calls
    import zoneinfo,datetime
    tz=zoneinfo.ZoneInfo('America/Los_Angeles')
    for t in [budget.BUDGET_EPOCH]+[1772960400+k*1800 for k in range(-4,5)]+[1793520000+k*1800 for k in range(-4,5)]+list(range(1767225600,1798761600,86400*7)):
        assert budget.pacific(t)==datetime.datetime.fromtimestamp(t,tz).strftime('%Y-%m-%dT%H:%M:%S'),t
    assert budget.pacific(budget.BUDGET_EPOCH)=='2026-10-02T21:00:00'
    saved=budget.BUDGET_EPOCH
    try:
        now=s.fake.now();budget.BUDGET_EPOCH=int(now-7200)
        n1=s.fake.add_job(NM(),state='COMPLETED',elapsed=3600,end_ago=9000,submit_ago=13000)[0]   # ended before the epoch
        n2=s.fake.add_job(NM(),state='COMPLETED',elapsed=3600,end_ago=60,submit_ago=4000)[0]
        r=s.budget();assert round(r['lines']['dev']['spent'],6)==1.0,r['lines']   # only the job inside the window (cpu=1, mem=2G: 1 SU/h x 1 h)
        argv=[h['argv']for h in s.history('sacct')][-1];assert argv[argv.index('-S')+1]==budget.pacific(budget.BUDGET_EPOCH)
        sel={l.split('|')[0]for l in s.fake.main('sacct',argv,{'TZ':'America/Los_Angeles'})[1].splitlines()}
        assert n2 in sel and n1 not in sel
        for v,code in ((str(budget.BUDGET_EPOCH),0),(str(budget.BUDGET_EPOCH+1),64),('0',64)):
            try:s.budget(env={'C8_BUDGET_EPOCH':v});assert code==0
            except Refuse as e:assert e.code==code==64
    finally:budget.BUDGET_EPOCH=saved
    ok('squeue_before_sacct_epoch_unix_seconds_to_pacific_window')

def test_expanse_detection(td):
    s=Site(td,'expdet');saved=ledger.MOUNTINFO
    try:
        for extra in ({'SLURM_CLUSTER_NAME':'expanse'},):
            for site in (None,'fake'):
                e={**extra,'C8_SITE':site}
                env={k:v for k,v in {**s.env,**e}.items()if v is not None}
                try:budget.report(env);raise AssertionError('budget.py ran on a fake Expanse host')
                except Refuse as r:assert r.code==64
                rc,out,err=s.call(ss.main,['raw','--role','val','--dir',str(s.d('x')),'--',*SHARED],env={**e,'C8_SITE':site or''})
                assert rc==64,(rc,err)
        mi=s.dir/'mountinfo';mi.write_text('262 30 262:8484 / /expanse/lustre/scratch rw - lustre 10.22.101.123@o2ib:/expanse/scratch rw,flock\n')
        ledger.MOUNTINFO=str(mi)
        for site in ('','fake'):
            rc,out,err=s.raw('val',s.d('x'),*SHARED,env={'C8_SITE':site});assert rc==64,(site,rc,err)
            try:budget.report({**s.env,'C8_SITE':site});raise AssertionError('budget ran')
            except Refuse as r:assert r.code==64
        assert not s.sbatches()
    finally:ledger.MOUNTINFO=saved
    ok('budget_and_admission_refuse_on_detected_expanse_without_c8_site')

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-11. Admission (fake squeue -r and sacct; the fake squeue fails any call without --all)
def test_own_share(td):
    s=Site(td,'own1',C8_COMPUTE_CAP='32',C8_RESERVATION=WIDE(32));s.ours(10)
    out=must(s.lanes(1,s.d('camp')),0,'"normal_run": "10+1/11"');assert len(s.sbatches())==2   # the worker and its shared merge
    s=Site(td,'own2',C8_COMPUTE_CAP='32',C8_RESERVATION=WIDE(32));s.ours(10)
    must(s.lanes(2,s.d('camp')),65,'Largest admissible N = 1','normal_run');assert not s.sbatches()
    s=Site(td,'own3',C8_COMPUTE_CAP='32',C8_RESERVATION=WIDE(32));s.ours(9);s.ours(2,state='PENDING')
    must(s.lanes(1,s.d('camp')),65,'normal_run');assert not s.sbatches()     # pending jobs count against the running share
    s=Site(td,'own4',C8_COMPUTE_CAP='32',C8_RESERVATION=WIDE(32));s.ours(5);t=hx();c=hx()
    arr=s.fake.add_job(f'c8d3-off0-{c}-{t}',state='PENDING',partition='compute',comment=f'c8d3:{c}:{"0"*12}:{t}',array=list(range(10)),cpus=128)
    flat=s.fake.main('squeue',['--all','-u','zzheng8','-h','-o','%i'],{})[1].split();full=s.fake.main('squeue',['--all','-u','zzheng8','-h','-r','-o','%i'],{})[1].split()
    assert f'{arr[0].split("_")[0]}_[0-9]'in flat and len([x for x in full if x.startswith(arr[0].split('_')[0]+'_')])==10
    must(s.lanes(1,s.d('camp')),65,'"normal_run": "15+1/11"');assert not s.sbatches()
    assert s.fake.main('squeue',['-u','zzheng8','-h'],{})[0]==1      # the fake refuses squeue without --all
    ok('admission_own_share_pending_counted_array_tasks_with_r')

SPY_ON=[False];SPY=[]
def _audit(ev,args):
    if SPY_ON[0]and ev=='open'and args and isinstance(args[0],(str,bytes,os.PathLike)):SPY.append(os.fsdecode(args[0]))
sys.addaudithook(_audit)

def test_scheduler_truth_spy(td):
    """The same decisions with an empty ledger and jobs submitted outside the tool; the rules and the SU gate open no
    package file but the ledger and the intent files."""
    for name,setup,n,code in (('st1',lambda s:s.ours(10),1,0),('st2',lambda s:(s.ours(9),s.ours(2,state='PENDING')),1,65),('st3',lambda s:s.ours(5,state='PENDING'),1,0)):
        s=Site(td,name,C8_COMPUTE_CAP='32',C8_RESERVATION=WIDE(32));setup(s);d=s.d('camp',plan=True)
        marks=[];s.h.on_point=lambda nm,info:marks.append((nm,len(SPY)))
        SPY.clear();SPY_ON[0]=True
        try:rc,out,err=s.lanes(n,d)
        finally:SPY_ON[0]=False
        assert rc==code,(name,rc,err[-600:])
        pos={nm:i for nm,i in marks};end=pos['su_gate']if code==0 else len(SPY)   # a refusal ends the call: its window runs to the end
        assert 'planned'in pos and(code!=0 or 'su_gate'in pos)
        assert SPY[pos['planned']:end]==[],(name,'the rules and the SU gate opened files',SPY[pos['planned']:end])
        allowed=(str(s.root/'ledger.jsonl'),str(s.root/'intents'),str(s.root/'locks'),str(s.root/'ledger_evidence'),str(s.dir/'scripts'),str(d))
        bad=[p for p in SPY if p.startswith(str(ROOT))or(p.startswith(str(s.root))and not p.startswith(allowed))]
        assert not bad,bad
    s=Site(td,'st4');s.ours(3);s.intent()
    SPY.clear();SPY_ON[0]=True
    try:r=s.budget()
    finally:SPY_ON[0]=False
    assert {Path(p).name if 'intents'not in p else 'intents'for p in SPY if p!=ledger.MOUNTINFO}<={'ledger.jsonl','intents'},SPY   # mountinfo: site detection
    ok('scheduler_truth_empty_ledger_and_open_spy')

def test_intents_count(td):
    # one unresolved intent not yet in squeue refuses lanes 1: 3 live dev nodes, 10 live normal jobs, 31 account jobs
    for name,setup,env,share in (('in1',lambda s:s.ours(3),{},'nodes'),('in2',lambda s:s.ours(10),{'C8_COMPUTE_CAP':'32','C8_RESERVATION':WIDE(32)},'normal_run'),
                                 ('in3',lambda s:s.others(31),{},'account')):
        s=Site(td,name,**env);setup(s);t=s.intent()
        must(s.lanes(1,s.d('camp')),65,share);assert not s.sbatches()
    s=Site(td,'in4');s.ours(31,partition='shared',role='val');s.intent(partition='shared',role='val')
    must(s.raw('val',s.d('x'),*SHARED),65,'shared');assert not s.sbatches()
    # counted once when its job appears; terminal sacct rows free it; never less than planned before them, at any age
    s=Site(td,'in5');s.ours(3);t=s.intent();j=s.accept_as(t)
    must(s.lanes(1,s.d('camp')),65,'"nodes": "4+1/4"')
    s.fake.set(j,sacct_hold=True);s.fake.finish(j,elapsed=600);s.h.advance(400)       # ended, purged from squeue, sacct lagging
    for adv in (0,G+1,86400):
        s.h.advance(adv);must(s.lanes(1,s.d('camp')),65,'"nodes": "4+1/4"');assert s.intents()[t].unresolved   # 3 live + the intent's planned node
    s.fake.deliver(j);out=must(s.lanes(1,s.d('camp')),0,f'intent {t} resolved (terminal')
    assert not s.intents()[t].unresolved and (s.root/'intents'/'resolved'/f'{t}.json').exists()
    # an intent present only as its file, only in the ledger (file unreadable) or resolved in one copy only counts the same
    for variant in ('file_only','ledger_only','ledger_resolved_file_pending','file_resolved_no_record'):
        s=Site(td,'cp_'+variant);s.ours(3)
        if variant=='file_only':t=s.intent(write=('file',))
        else:t=s.intent()
        sset=ledger.Settings(s.env)
        if variant=='ledger_only':(sset.intents/f'{t}.json').write_bytes(b'damaged')
        if variant=='ledger_resolved_file_pending':
            with ledger.SessionLock(sset,'t')as lock:
                led=ledger.Ledger(sset,lock);led.read(writer=True)
                h=s.h;h.kill['rename']=1
                try:led.append(ledger.payload('resolution',[t],token=t,rule='terminal',charge_su=0.0));led.rename_resolved(t)
                except Killed:pass
        if variant=='file_resolved_no_record':os.rename(sset.intents/f'{t}.json',sset.resolved/f'{t}.json')
        assert s.intents()[t].unresolved,variant
        if variant=='ledger_resolved_file_pending':
            r=s.budget();assert r['lines']['dev']['intents']>=128.0      # budget.py over-counts, never under-counts
            out=must(s.lanes(1,s.d('camp')),0,f'completed the interrupted resolution of intent {t}')   # the next admission completes it
            continue
        out=must(s.lanes(1,s.d('camp')),65,'nodes');assert not s.sbatches(),variant
        if variant=='ledger_only':assert 'counted from its ledger copy'in out
    ok('intents_count_at_every_age_until_terminal_rows_in_either_copy')

def test_independence_account_detectors(td):
    s=Site(td,'ind1',C8_COMPUTE_CAP='32',C8_RESERVATION=WIDE(32));s.c8d2(11);s.ours(10)
    s.fake.config(triggers=[{'cmd':'sacct','do':'add','jobs':[{'name':f'c8d2-lane-{hx()}-{hx()}','partition':'compute','state':'PENDING','cpus':128}for _ in range(3)]}])
    must(s.lanes(1,s.d('camp')),0);assert len(s.sbatches())==2   # c8d2- submissions between snapshot and sbatch change nothing
    s=Site(td,'acc31');s.others(31);must(s.lanes(1,s.d('camp')),0)
    s=Site(td,'acc32');s.others(32);must(s.lanes(1,s.d('camp')),65,'account');assert not s.sbatches()
    s=Site(td,'det1');ids=s.c8d2(12);out=must(s.lanes(1,s.d('camp')),65,'c8d2- jobs exceed',ids[0])
    assert not s.history('scancel')and not s.history('scontrol')and not s.sbatches()
    must(s.raw('val',s.d('x'),*SHARED),0)                                    # detectors gate normal-QOS admission only
    s=Site(td,'det2');s.fake.add_job('myjob',partition='compute',state='PENDING',cpus=128)
    must(s.lanes(1,s.d('camp')),65,'outside both prefixes','myjob');assert not s.history('scancel')
    ok('independence_from_c62d_account_total_detectors')

def test_reservation_forms(td):
    for name,res,code in (('r_unset',None,65),('r_none','mode=none',65)):
        s=Site(td,name,C8_RESERVATION=res)
        must(s.lanes(1,s.d('camp')),code,'no agreed reservation');must(s.raw('val',s.d('x'),*SHARED),0)
    # malformed (an invalid line, the withdrawn modes common-lock and turn, or a re-split without `until`): every
    # normal-QOS submission is refused (64), a shared job is still admitted under the base shared share (A-ORC-11)
    for bad in ('mode=reservation;id=H7E-R;run=11','mode=reservation;id=H7E-R;run=11;sub=27;acct_run=32;shared=32;dev_nodes=x','mode=common-lock','mode=turn',
                'mode=reservation;id=H7E-R;run=11;sub=27;acct_run=32;shared=32;dev_nodes=4;until=yesterday',BASE+';extra=1',BASE+';run=3',
                'mode=reservation;id=H7E-R;run=20;sub=27;acct_run=32;shared=32;dev_nodes=20',     # a re-split without `until`
                'mode=reservation;id=PILOT-W1;run=11;sub=27;acct_run=32;shared=32;dev_nodes=4',   # the base counts under another id, no `until`
                'mode=reservation;id=H7E-R;run=11;sub=27;acct_run=32;shared=64;dev_nodes=4'):    # a larger shared share without `until`
        s=Site(td,'r_bad_'+hx(),C8_RESERVATION=bad)
        must(s.lanes(1,s.d('camp')),64);must(s.raw('val',s.d('x'),*COMPUTE),64);assert not s.sbatches(),bad
        must(s.raw('val',s.d('x'),*SHARED),0,'"shared": "0+1/32"');assert len(s.sbatches())==1 and s.sbatches()[0]['argv'][s.sbatches()[0]['argv'].index('-p')+1]=='shared'
        must(s.raw('val',s.d('x'),*DEBUG),0,'"debug": "0+1/2"')
    s=Site(td,'r_bad_full',C8_RESERVATION='mode=turn');s.ours(32,partition='shared',role='x');must(s.raw('val',s.d('x'),*SHARED),65,'shared')   # the base share binds
    past=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()-60));fut=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()+3600))
    s=Site(td,'r_until',C8_RESERVATION='mode=reservation;id=H11-pilot;run=11;sub=27;acct_run=32;shared=32;dev_nodes=6;until='+past)
    must(s.lanes(1,s.d('camp')),65,'expired');must(s.lanes(1,s.d('camp'),env={'C8_RESERVATION':BASE}),0)
    s=Site(td,'r_fut',C8_RESERVATION='mode=reservation;id=H11-pilot;run=11;sub=27;acct_run=32;shared=32;dev_nodes=6;until='+fut,C8_COMPUTE_CAP=None)
    s.ours(5);must(s.lanes(1,s.d('camp')),0,'"nodes": "5+1/6"')
    # an expired re-split keeps no larger share: its shared=64 falls back to the base 32 after `until` (in force before it)
    big='mode=reservation;id=PILOT-W1;run=11;sub=27;acct_run=32;shared=64;dev_nodes=4;until='
    s=Site(td,'r_exp_shared',C8_RESERVATION=big+fut);s.ours(40,partition='shared',role='x');must(s.raw('val',s.d('x'),*SHARED),0,'"shared": "40+1/64"')
    s=Site(td,'r_exp_shared2',C8_RESERVATION=big+past);s.ours(40,partition='shared',role='x')
    must(s.raw('val',s.d('x'),*SHARED),65,'"shared": "40+1/32"');must(s.raw('val',s.d('x'),*COMPUTE),65,'expired');assert s.counts()['shared']==40
    ok('c8_reservation_forms_none_unset_malformed_resplit_expiry_withdrawn_modes')

def test_caps(td):
    s=Site(td,'cap1');s.ours(3);must(s.lanes(2,s.d('camp')),65,'Largest admissible N = 1','nodes')
    s=Site(td,'cap2');s.others(1,partition='debug');s.c8d2(1,partition='debug',state='PENDING')
    must(s.raw('val',s.d('x'),*DEBUG),65,'debug');assert not s.sbatches()
    s=Site(td,'cap3');s.ours(31,partition='shared',role='val')
    must(s.submit(s.d('camp'),['0:0-1']),65,'shared');assert not s.sbatches()
    s=Site(td,'cap3b');s.ours(30,partition='shared',role='val');must(s.submit(s.d('camp'),['0:0-0']),0,'"shared": "30+2/32"')   # one element + its merge
    s=Site(td,'cap4');must(s.raw('val',s.d('x'),*[a for a in SHARED if a not in('-A','yun124')]),64,'-A yun124')
    # C8_COMPUTE_CAP never exceeds the active reservation's dev_nodes: a cap left at a pilot window's count under the base
    # split binds at 4 (H7E-R); inside a re-split it binds at that split's dev_nodes
    s=Site(td,'cap5',C8_COMPUTE_CAP='8');s.ours(4);must(s.raw('val',s.d('x'),*COMPUTE),65,'"nodes": "4+1/4"','exceeds the reservation','nodes')
    must(s.lanes(1,s.d('camp')),65,'nodes');assert not s.sbatches()and s.counts()['nodes']==4
    s=Site(td,'cap6',C8_COMPUTE_CAP='8',C8_RESERVATION=WIDE(6));s.ours(5);must(s.raw('val',s.d('x'),*COMPUTE),0,'"nodes": "5+1/6"')
    must(s.raw('val',s.d('y'),*COMPUTE),65,'"nodes": "6+1/6"')
    s=Site(td,'cap7',C8_COMPUTE_CAP='2');s.ours(2);must(s.raw('val',s.d('x'),*COMPUTE),65,'"nodes": "2+1/2"')   # a lower cap still binds
    ok('caps_nodes_debug_shared_array_tasks_account_flag_cap_within_dev_nodes')

def test_names_and_records(td):
    s=Site(td,'names');d=s.d('plan1');must(s.raw('plan',d,*SHARED),0,'idle nodes','start estimate','squeue --start','sprio')
    sub=s.records('submit')[-1];it=s.records('intent')[-1];c=hashlib.sha256(str(os.path.realpath(d)).encode()).hexdigest()[:12]
    job=[j for j in s.fake.jobs()if j['id']==sub['job_id']][0]
    assert job['name']==f'c8d3-plan-{c}-{it["token"]}'and job['comment']==f'c8d3:{c}:{"0"*12}:{it["token"]}'and sub['token']==it['token']
    assert sub['reservation']==BASE and sub['counts']['shared']==0 and '--no-requeue'in job['argv']and 'to start at'in sub['start_estimate']and sub['su_projected']>0
    d2=s.d('camp2',plan=True);must(s.raw('report',d2,*SHARED),0);sub=s.records('submit')[-1]
    assert sub['p']==hashlib.sha256((d2/'manifest.json').read_bytes()).hexdigest()[:12]and f':{sub["p"]}:'in sub['comment']
    must(s.raw('val',s.d('x'),*SHARED,env={'C8_BUDGET_LINE':'pilot','C8_PILOT_SU_CAP':'100'}),0);assert s.records('submit')[-1]['role']=='pilot_val'
    must(s.lanes(1,s.d('camp3'),env={'C8_BUDGET_LINE':'pilot','C8_PILOT_SU_CAP':'1000'}),0)
    assert {r['role']for r in s.records('submit')[-2:]}=={'pilot_lane','pilot_merge'}and s.records('submit')[-1]['line']=='pilot'
    must(s.raw('pilot_val',s.d('x'),*SHARED),64,'pilot_')
    must(s.raw('Bad-Role',s.d('x'),*SHARED),64);must(s.raw('val','/tmp/elsewhere',*SHARED),64,'--dir')
    must(s.raw('val',s.root/'runs'/'a'/'b',*SHARED),64);must(s.raw('val',s.root/'evidence'/'nothex'/'b',*SHARED),64)
    n0=len(s.sbatches())
    for extra in (['-J','x'],['--job-name=x'],['--comment=x'],['--hold'],['-H'],['--begin=now+1hour'],['--requeue'],['--array=0-3'],['-a','1'],
                  ['--dependency=afterany:12'],['--ntasks-per-node=1'],['--export=NONE'],['--nodes=2'],['--arr=0-1'],['--exclusive=user']):
        must(s.raw('val',s.d('x'),*SHARED,*extra),64)
    must(s.raw('drill_dep',s.d('x'),*SHARED,'--dependency=afterok:12'),64);must(s.raw('drill_dep',s.d('x'),*[a if a!='shared'else'compute'for a in COMPUTE],'--dependency=afterany:12'),64)
    sc=s.dir/'job.sh'
    for line in ('#SBATCH -J name','#SBATCH --comment=x','#SBATCH --hold','#SBATCH --begin=now','#SBATCH --requeue','#SBATCH --array=1-2'):
        sc.write_text(f'#!/bin/bash\n{line}\necho x\n');must(s.raw('val',s.d('x'),'-A','yun124','-p','shared','--nodes=1','--mem=1G','-t','5',str(sc)),64)
    for var in ('C8_SBATCH_ARGS','C8_MERGE_SBATCH_ARGS'):
        for bad in ('-A yun124 -p compute -J x','-A yun124 -p shared -c 24 --mem=48G -t 01:00:00 --comment=x','-A yun124 -p compute --hold','-A yun124 -p compute --begin=now'):
            must(s.lanes(1,s.d('camp9'),env={var:bad}),64)
    # the campaign allowlist is the inherited one without --begin, -J/--job-name, --hold, --requeue: raw's extra options
    # (--wrap, --output/-o, --dependency/-d, --nodes/-N, --ntasks/-n, --exclusive) are refused there too, for lanes and arrays
    base={'C8_SBATCH_ARGS':'-A yun124 -p compute','C8_MERGE_SBATCH_ARGS':'-A yun124 -p shared -c 24 --mem=48G -t 01:00:00'}
    for var in ('C8_SBATCH_ARGS','C8_MERGE_SBATCH_ARGS'):
        for extra in ('--dependency=afterok:4242','-d afterok:4242','-dafterok:4242','-o /tmp/x.log','--output=/tmp/x.log','--wrap=date','--nodes=1','-N 1',
                      '--ntasks=1','-n 1','--exclusive','--requeue','--job-name x','--array=0-1'):
            must(s.lanes(1,s.d('camp9'),env={**base,var:base[var]+' '+extra}),64)
            must(s.submit(s.d('camp9'),['0:0-1'],env={'C8_SBATCH_ARGS':'-A yun124 -p shared -c 32 --mem=64G -t 01:00:00',
                                                       'C8_MERGE_SBATCH_ARGS':base['C8_MERGE_SBATCH_ARGS'],**({var:(base[var]if var=='C8_MERGE_SBATCH_ARGS'else'-A yun124 -p shared -c 32 --mem=64G -t 01:00:00')+' '+extra})}),64)
    src=(ROOT/'tools/production.py').read_text()   # the inherited allowlist (a6ce987), read without importing production (numpy)
    inh=lambda name:re.search(name+r"=frozenset\('([^']*)'",src).group(1)
    assert ss.CAMPAIGN_LONG_VALUE==frozenset(inh('SBATCH_LONG_VALUE').split())-{'begin','job-name'}
    assert ss.CAMPAIGN_LONG_FLAG==frozenset(inh('SBATCH_LONG_FLAG').split())-{'hold','requeue'}and set(ss.CAMPAIGN_SHORT)==set(inh('SBATCH_SHORT_VALUE'))-{'J'}
    # raw never carries a campaign role (lane, merge, off<N>): such a job would look like a lane worker, merge or array window
    for role in ('lane','merge','off0','off12'):
        must(s.raw(role,s.d('camp9'),*SHARED),64,'campaign role');must(s.raw(role,s.d('camp9'),*SHARED,env={'C8_BUDGET_LINE':'pilot','C8_PILOT_SU_CAP':'100'}),64,'campaign role')
    assert len(s.sbatches())==n0
    for role in ('offline','lanes','merger','off'):must(s.raw(role,s.d('x'),*SHARED),0)   # only the exact campaign roles are refused
    n0=len(s.sbatches())
    must(s.raw('drill_dep',s.d('dep',kind='evidence'),*SHARED,'--dependency=afterany:5001'),0)    # J-DRL-10's drill afterany
    sc.write_text('#!/bin/bash\n#SBATCH -A yun124 -p shared --nodes=1 --ntasks=1 -c 4 --mem=8G -t 00:10:00 --no-requeue\n#SBATCH -o /tmp/%x_%j.out\necho ok\n')
    must(s.raw('val2',s.d('x'),str(sc)),0);assert s.sbatches()[-1]['argv'][-1]==str(sc)
    ok('names_comments_roles_pilot_prefix_refused_options_everywhere_records')

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-12. The SU gate
MEMJOB=['-A','yun124','-p','shared','--nodes=1','-c','2','--mem=8G','-t','01:00:00','--wrap','date']    # 4 SU (memory-billed)
def test_su_gate_thresholds(td):
    # the joint ask and cap through the other site's carry (one site alone stays under its 2,500 sub-cap, S2-004)
    s=Site(td,'su1',C8_OTHER_SITE_SU=carry(2000));s.spent(1997);must(s.raw('val',s.d('x'),*MEMJOB),65,'4001.00','above 4000');assert not s.sbatches()
    must(s.raw('val',s.d('x'),*MEMJOB,env={'C8_SU_APPROVED':'PLAN-REVIEW-LOG.md:300 user OK 4.5k'}),0);assert s.records('submit')[-1]['su_approved'].startswith('PLAN-REVIEW')
    s=Site(td,'su2',C8_OTHER_SITE_SU=carry(2600));s.spent(2397);must(s.raw('val',s.d('x'),*MEMJOB,env={'C8_SU_APPROVED':'ok'}),65,'5001.00','above its cap 5000')
    # the cores-only control would admit both (so the test can fail): 3997+2 <= 4000, 4997+2 <= 5000
    assert 3997+2<=4000 and 4997+2<=5000 and ss.resolve([],[],ss.parse_options(MEMJOB,'t')[0],None)['billing']==4
    for spent,appr in ((3999,None),(4999,'ok')):
        s=Site(td,f'ex{spent}');s.spent(spent);e={'C8_SU_APPROVED':appr}if appr else{}
        must(s.raw('val',s.d('x'),'-A','yun124','-p','shared','--nodes=1','--exclusive','-c','2','--mem=4G','-t','01:00:00','--wrap','date',env=e),64,'--exclusive')
        must(s.raw('val',s.d('x'),'-A','yun124','-p','debug','--exclusive','-c','2','--mem=4G','-t','00:30:00','--wrap','date',env=e),64,'--exclusive')
        sc=s.dir/'ex.sh';sc.write_text('#!/bin/bash\n#SBATCH --exclusive\necho\n')
        must(s.raw('val',s.d('x'),'-A','yun124','-p','shared','--nodes=1','-c','2','--mem=4G','-t','01:00:00',str(sc),env=e),64,'--exclusive');assert not s.sbatches()
    s=Site(td,'excomp');must(s.call(ss.main,['raw','--role','val','--dir',str(s.d('x')),'--dry-run','--',*COMPUTE]),0,'new reservations 128.00')   # 128 per node-hour
    s=Site(td,'pil',C8_BUDGET_LINE='pilot',C8_PILOT_SU_CAP='100');s.spent(95,line='pilot');s.spent(3000)
    must(s.raw('val',s.d('x'),*SHARED8),65,'pilot line would reach 103.00');must(s.raw('val',s.d('x'),*MEMJOB),0)   # dev spend not in the pilot line
    must(s.raw('val',s.d('x'),*SHARED,env={'C8_PILOT_SU_CAP':None}),64,'C8_PILOT_SU_CAP')
    must(s.raw('val',s.d('x'),*SHARED,env={'C8_BUDGET_LINE':None}),64,'C8_BUDGET_LINE');must(s.raw('val',s.d('x'),*SHARED,env={'C8_BUDGET_LINE':'prod'}),64)
    # the finished job of F39: billing=28800, 1 h limit, ElapsedRaw 600: 1.33 SU; 8 SU while live
    s=Site(td,'f39');j=s.ours(1,role='val',partition='shared',cpus=8,mem='15G',time_s=3600)[0];assert round(s.budget()['lines']['dev']['live'],6)==8.0
    s.fake.finish(j,elapsed=600);assert round(s.budget()['lines']['dev']['spent'],4)==round(8*600/3600,4)
    ok('su_gate_memory_billed_thresholds_exclusive_off_compute_pilot_line')

def test_reservation_binds(td):
    s=Site(td,'binds',C8_BUDGET_LINE='pilot',C8_PILOT_SU_CAP='1300',C8_MERGE_SBATCH_ARGS='-A yun124 -p shared -c 24 --mem=48G -t 02:00:00')
    s.spent(150,line='pilot')
    out=must(s.lanes(4,s.d('pf'),lane_time='02:15:00'),65,'1350.00','largest N at this lane time = 3','largest lane time at N = 4: 2:00:00')
    assert not s.sbatches()
    must(s.lanes(4,s.d('pf'),lane_time='02:00:00'),0,'projected 1222.00')   # 150 + 4 x 128 x 2 + 48 + ... at 2:00:00 it fits
    ok('reservation_binds_lane_time_and_n_hints')

def test_query_failures(td):
    for cmd,nth in (('squeue',1),('squeue',2),('sacct',1),('sacct',2)):
        s=Site(td,f'qf_{cmd}{nth}');s.fake.config(fail_at={cmd:[nth]});must(s.raw('val',s.d('x'),*SHARED),69,'state unknown');assert not s.sbatches()
    for cmd in ('squeue','sacct'):
        s=Site(td,'qf_hang_'+cmd);s.fake.config(hang={cmd:5});must(s.raw('val',s.d('x'),*SHARED),69,'timed out');assert not s.sbatches()
    s=Site(td,'qf_budget');s.fake.config(fail_at={'sacct':[1]})
    try:s.budget();raise AssertionError('budget ran')
    except Refuse as e:assert e.code==69
    s=Site(td,'qf_resnap');s.fake.config(fail_at={'squeue':[3]});must(s.lanes(2,s.d('c')),69);n=len(s.sbatches());assert n==3   # no further sbatch
    s=Site(td,'qf_fsync');s.h.faults['lock_fsync:sbatch']={'errno':errno.EIO};must(s.raw('val',s.d('x'),*SHARED),69,'fsync check');assert not s.sbatches()
    s=Site(td,'qf_fsync2');s.h.faults['lock_fsync:ledger']={'errno':errno.EIO};must(s.raw('val',s.d('x'),*SHARED),69);assert not s.sbatches()and not s.records('intent')
    s=Site(td,'qf_fsync3');s.h.faults['lock_fsync:sbatch']={'errno':errno.EIO};must(s.lanes(2,s.d('c')),69);assert not s.sbatches()
    ok('query_failures_timeouts_resnapshot_and_lock_fsync_check')

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-17 (a), (b), (d), (e), (f), (h)
def ours_jobs(s):return [j for j in s.fake.jobs()if j['name'].startswith('c8d3-')]
def token_su(s,t):
    r=s.budget();return r
def do(s,kind,d=None):
    if kind=='raw':return s.raw('val',d or s.d('x'+hx()),*SHARED)
    if kind=='lanes2':return s.lanes(2,d or s.d('c'+hx()))
    return s.submit(d or s.d('c'+hx()),['0:0-3%2'])

def test_a_append_failure_after_sbatch(td):
    specs=[{'errno':errno.EDQUOT},{'errno':errno.ENOSPC},{'errno':errno.EIO},{'short':1},{'short':'half'},{'short':'n-1'}]
    for kind,njobs in (('raw',1),('lanes2',3),('submit',5)):
        for i,spec in enumerate(specs):
            s=Site(td,f'a_{kind}_{i}');s.h.faults['ledger:submit']=spec
            must(do(s,kind),74);jobs=ours_jobs(s)
            assert len(jobs)==njobs and not s.history('scancel')and all(j['state']!='CANCELLED'for j in jobs),(kind,spec,[j['state']for j in jobs])
            b1=s.budget()['lines']['dev'];tok_before={j['name'][-12:]for j in jobs}
            must(s.raw('val',s.d('y'),*SHARED),0)
            if 'short'in spec:assert list((s.root/'ledger_evidence').glob('tail.*'))
            ad=s.records('adopted');bases={j['base']for j in jobs}
            assert {r['job_id']for r in ad}==bases,(kind,spec,ad)
            for r in ad:
                js=[j for j in jobs if j['base']==r['job_id']];j=js[0]
                assert r['name']==j['name']and r['comment']==j['comment']and r['partition']==j['partition']and r['time_s']==j['timelimit']and r['token']==j['name'][-12:]
                if kind=='submit'and len(js)>1:assert r['task_range']==[0,1,2,3]
            b2=s.budget()['lines']['dev'];assert abs(b2['total']-b1['total']-1/12)<1e-9,(b1,b2)   # each job counted once, before and after
            if kind=='submit'and i==0:
                arr=[j for j in jobs if j['task']is not None];s.fake.finish(arr[0]['id'],elapsed=60)
                n=len(s.records('adopted'));must(s.raw('val',s.d('z'),*SHARED),0);assert len(s.records('adopted'))==n   # adopted once, never per task
    ok('a_ledger_append_failure_after_sbatch_74_jobs_run_adopted_once')

POINTS=['locked','snapshot_account','snapshot_user','sacct_unfiltered','sacct_state_selected','ledger_checked','resolutions','adopted','planned','rules','su_gate',
        'before_intent','intent_record','intent_file','age_checked','launch','after_sbatch','submit_records','resnapshot']
def test_b_sigkill_every_step(td):
    for pt in POINTS:
        s=Site(td,'b_'+pt);s.h.kill[pt]=1;rc=do(s,'raw');assert rc[0]==-9,(pt,rc)
        t0=time.time();must(s.raw('val',s.d('second'),*SHARED),0);assert time.time()-t0<2.0   # the lock is free at once
        jobs=ours_jobs(s);subs={r['job_id']for r in s.records('submit')};ad={r['job_id']for r in s.records('adopted')}
        assert {j['base']for j in jobs}<=subs|ad,(pt,jobs)
        r=s.budget()['lines']['dev']
        if pt in('launch',):assert len(jobs)==1 and r['intents']>0          # killed before sbatch: the intent stays charged (no evidence)
        if pt=='after_sbatch':assert len(jobs)==2 and any(a for a in s.records('adopted'))
    # directory not yet created: adopted with dir null; once it exists, a later admission appends the resolving annotation
    s=Site(td,'b_dir');d=s.d('notyet');s.h.kill['after_sbatch']=1;do(s,'raw',d);assert not d.exists()
    must(s.raw('val',s.d('y'),*SHARED),0);ad=s.records('adopted');assert len(ad)==1 and ad[0]['dir']is None
    d.mkdir(parents=True);must(s.raw('val',s.d('z'),*SHARED),0);an=[r for r in s.records('annotation')if r.get('about')=='dir']
    assert len(an)==1 and an[0]['dir']==os.path.realpath(d)and an[0]['job_id']==ad[0]['job_id'],an
    must(s.raw('val',s.d('w'),*SHARED),0);assert len([r for r in s.records('annotation')if r.get('about')=='dir'])==1
    ok('b_sigkill_after_every_step_lock_free_at_once_adoption_dir_null_annotation')

def test_d_torn_final_record(td):
    for kind in ledger.KINDS:
        s=Site(td,'d_'+kind);must(s.raw('val',s.d('x'),*SHARED),0)
        t='f'*12;p=ledger.payload(kind,[t],token=t,x=1);line=ledger.frame(p);torn=line[:len(line)//2]
        before=(s.root/'ledger.jsonl').read_bytes();(s.root/'ledger.jsonl').write_bytes(before+torn)
        must(s.raw('val',s.d('y'),*SHARED),0,'truncated a torn final record')
        ev=sorted((s.root/'ledger_evidence').glob('tail.*'));assert ev and ev[-1].read_bytes()==torn
        now=(s.root/'ledger.jsonl').read_bytes();assert now.startswith(before)and ledger.Scan(now).status=='clean'and len(now)>len(before)
        assert not (s.root/'intents'/f'{t}.json').exists()
    s=Site(td,'d_bad');must(s.raw('val',s.d('x'),*SHARED),0);L=s.root/'ledger.jsonl';b=bytearray(L.read_bytes());b[-30]^=1;L.write_bytes(bytes(b))
    must(s.raw('val',s.d('y'),*SHARED),69,'interior corruption');assert L.read_bytes()==bytes(b)
    s=Site(td,'d_ev');must(s.raw('val',s.d('x'),*SHARED),0);L=s.root/'ledger.jsonl';base=L.read_bytes();L.write_bytes(base+b'{"rec":{"kind"')
    s.h.faults['evidence']={'errno':errno.EDQUOT};must(s.raw('val',s.d('y'),*SHARED),74,'nothing truncated');assert L.read_bytes()==base+b'{"rec":{"kind"'
    s.h.kill['tail_evidence_written']=1;assert s.raw('val',s.d('y'),*SHARED)[0]==-9 and L.read_bytes()==base+b'{"rec":{"kind"'
    must(s.raw('val',s.d('y'),*SHARED),0);assert len(list((s.root/'ledger_evidence').glob('tail.*')))==2
    ok('d_torn_final_record_each_kind_evidence_then_truncate_bad_final_line_69')

class A:
    def __init__(self,**k):self.__dict__.update(dict(reason=None,user_decision=None,hold_su=None,hold_line=None,decision_log=None));self.__dict__.update(k)
def rebuild(s,**k):
    s.activate();o,e=io.StringIO(),io.StringIO()
    with contextlib.redirect_stdout(o),contextlib.redirect_stderr(e):
        try:rc=ledger.cmd_rebuild(A(**k),s.env)
        except Refuse as r:rc=r.code;print(r,file=sys.stderr)
    return rc,o.getvalue(),e.getvalue()

def test_e_interior_corruption(td):
    s=Site(td,'e1');twin=s.d('twin',plan=True);d=s.d('smoke',plan=True)
    must(s.raw('plan',d,*SHARED),0);t=s.records('intent')[-1]['token']
    must(s.ledger_cmd(['register',str(twin),'--role','plan'],env={'SLURM_JOB_ID':s.records('submit')[-1]['job_id'],'SLURM_JOB_NAME':s.records('submit')[-1]['name']}),0)
    p_orig=s.records('submit')[-1]['p'];(d/'manifest.json').write_text('{"replanned":1}\n')     # a re-planned directory: its original P is in the ledger
    must(s.raw('val',s.d('x'),*SHARED),0)
    L=s.root/'ledger.jsonl';old=L.read_bytes();lines=ledger.split_lines(old);dlog=decision_log(s)   # a valid decision line: resolve reaches the ledger
    mid=[i for i,(o,l) in enumerate(lines)if b'"kind":"submit"'in l][-1]      # the second job's submit record (a middle line)
    assert 0<mid<len(lines)-1
    for variant in ('middle','final','invalid_then_valid'):
        b=bytearray(old)
        if variant=='middle':b[lines[mid][0]+30]^=1
        elif variant=='final':b[lines[-1][0]+30]^=1
        else:b[lines[mid][0]:lines[mid][0]]=b'garbage line\n'
        L.write_bytes(bytes(b))
        for fn in (lambda:s.raw('val',s.d('y'),*SHARED),lambda:s.lanes(1,s.d('c')),
                   lambda:s.ledger_cmd(['register',str(twin),'--role','plan'],env={'SLURM_JOB_ID':'1','SLURM_JOB_NAME':f'c8d3-plan-{"a"*12}-{"b"*12}'}),
                   lambda:s.ledger_cmd(['resolve',t,*dlog])):
            rc,out,err=fn();assert rc==69,(variant,rc,err)
            assert str(L)in err and 'interior corruption at line'in err and 'byte offset'in err,(variant,err)
        assert L.read_bytes()==bytes(b);assert not [x for x in s.sbatches()if 'y'in x['argv'][-1]]
        try:s.budget();raise AssertionError('budget ran on a corrupt ledger')
        except Refuse as e:assert e.code==69
    must(rebuild(s,reason='x'),69,'unmatched segment')   # the inserted line holds no token and no recorded range: a repair block
    b=bytearray(old);b[lines[mid][0]+30]^=1;L.write_bytes(bytes(b))     # a flipped byte in a submit record: matched by its tokens
    must(rebuild(s),64,'--reason')
    must(rebuild(s,reason='interior corruption test'),0)
    new=L.read_bytes();kept=[l for i,(o,l) in enumerate(lines)if i!=mid]
    assert [l for _,l in ledger.split_lines(new)[:len(kept)]]==kept
    regs=s.records('register');assert regs and regs[0]['dir']==os.path.realpath(twin)and any(r['kind']=='submit'and r['p']==p_orig for r in s.records('submit'))
    assert list((s.root/'ledger_evidence').glob('invalid.*'))and list((s.root/'ledger_evidence').glob('ledger.*.jsonl'))
    must(s.raw('val',s.d('y'),*SHARED),0)
    # a deleted ledger refuses admission and budget.py, and every rebuild blocks until the user's decision
    L.unlink();must(s.raw('val',s.d('y'),*SHARED),69,'missing')
    try:s.budget();raise AssertionError
    except Refuse as e:assert e.code==69
    must(rebuild(s,reason='x'),69,'missing')
    ok('e_interior_corruption_every_writer_69_rebuild_keeps_in_order_missing_ledger_blocks')

def test_f_unattributable(td):
    for name,mk in (('nameless',lambda s:s.fake.add_job('c8d3-made by hand',partition='shared')),
                    ('nocomment',lambda s:s.fake.add_job(f'c8d3-val-{hx()}-{hx()}',partition='shared',comment=None)),
                    ('mismatch',lambda s:s.fake.add_job(f'c8d3-val-{"a"*12}-{"b"*12}',partition='shared',comment=f'c8d3:{"a"*12}:{"0"*12}:{"c"*12}'))):
        s=Site(td,'f_'+name);jid=mk(s)[0];b0=s.budget()['lines']
        must(s.raw('val',s.d('x'),*SHARED),69,'unattributable',jid);assert not s.history('scancel')and not s.history('scontrol')and not s.sbatches()
        must(rebuild(s,reason='host: a manual test job'),0)
        r=[x for x in s.records('adopted')if x['job_id']==jid];assert r and r[0]['attribution']is None and r[0]['reason']=='host: a manual test job'
        assert s.budget()['lines']==b0
        must(s.raw('val',s.d('x'),*SHARED),0)
    s=Site(td,'f_ctl');c=hx();t=hx();s.fake.add_job(f'c8d3-val-{c}-{t}',partition='shared',comment=f'c8d3:{c}:{"0"*12}:{t}')
    must(s.raw('val',s.d('x'),*SHARED),0);ad=s.records('adopted');assert len(ad)==1 and ad[0]['dir']is None and ad[0]['token']==t
    ok('f_unattributable_blocks_until_rebuild_records_it_never_cancelled')

def test_h_budget_from_sacct(td):
    s=Site(td,'h1');b8='15G'
    rq=s.ours(1,role='lane',partition='compute',time_s=7200,start_ago=1800)[0]      # three attempts: 128 x (0.5+0.25+0.1)
    s.fake.requeue(rq,start_new=True);s.h.advance(900);s.fake.requeue(rq,start_new=True);s.h.advance(360);s.fake.finish(rq)
    s.ours(1,role='val',partition='shared',state='COMPLETED',cpus=8,mem=b8,elapsed=3600)                                 # outside the tool: 8
    s.ours(1,role='val',partition='shared',state='PENDING',cpus=2,mem='8G',time_s=3600)                                  # pending, ReqTRES only: 4
    s.ours(1,role='pilot_val',partition='shared',state='COMPLETED',cpus=1,mem='2G',elapsed=7200)                         # pilot: 2
    lw=s.ours(1,role='lane',partition='compute',time_s=7200)[0];s.fake.requeue(lw,elapsed=5400,start_new=True)           # 128 x 1.5 + 128 x 2
    arr=s.fake.add_job(f'c8d3-off0-{"d"*12}-{"e"*12}',state='PENDING',partition='shared',cpus=8,mem=b8,comment=f'c8d3:{"d"*12}:{"0"*12}:{"e"*12}',array=list(range(20)))
    for k,j in enumerate(arr):
        s.fake.set(j,throttle=8)
        if k<6:s.fake.set(j,state='RUNNING',start=s.fake.now()-600,raw=str(9000+k));s.fake.finish(j,elapsed=600)
        elif k<14:s.fake.set(j,state='RUNNING',start=s.fake.now()-60,raw=str(9000+k))
    jf=s.ours(1,role='val',partition='shared',cpus=8,mem=b8)[0];s.fake.set(jf,sacct_hold=True);s.fake.finish(jf,elapsed=600)   # just finished, sacct lags: 8 x 600 s
    rb=s.ours(1,role='val',partition='shared',cpus=8,mem=b8,time_s=3600,start_ago=1200)[0]
    s.fake.config(triggers=[{'cmd':'sacct','do':'requeue','jobs':[rb],'without':['-s']}])                               # a requeue between squeue and sacct
    SPY.clear();SPY_ON[0]=True
    try:r=s.budget()
    finally:SPY_ON[0]=False
    assert {Path(p).name for p in SPY if p!=ledger.MOUNTINFO}<={'ledger.jsonl'},SPY
    hand_dev=8+128*0.85+4+(128*1.5+128*2)+(6*8*600/3600+14*8)+8*600/3600+(8+8*1200/3600)
    assert abs(r['lines']['dev']['total']-hand_dev)<0.02 and abs(r['lines']['pilot']['total']-2)<1e-6,(r['lines'],hand_dev)
    assert rq in r['repeated_attempts']and lw in r['repeated_attempts']
    # a live line without an intent, absent from sacct: priced from tres-alloc (cpu=4,mem=16G: 8 per hour), never from %m (4G)
    s=Site(td,'h_m');t=hx();c=hx()
    j=s.fake.add_job(f'c8d3-val-{c}-{t}',partition='shared',cpus=4,mem='16G',mem_per_cpu=True,sacct_hold=True,comment=f'c8d3:{c}:{"0"*12}:{t}')[0]
    line=s.fake.main('squeue',['--all','-h','-r','-u','zzheng8','-o','%i|%m'],{})[1].strip()
    assert line==f'{j}|4G'and abs(s.budget()['lines']['dev']['live']-8.0)<1e-9,(line,s.budget()['lines'])
    # a job id a submit record names but neither source shows stays charged at its intent's reservation; admission proceeds
    s=Site(td,'h2');must(s.raw('val',s.d('x'),*SHARED8),0);jid=s.records('submit')[-1]['job_id']
    st=s.fake._mem;st['jobs']=[j for j in st['jobs']if j['id']!=jid]
    s.h.advance(G+86400);assert abs(s.budget()['lines']['dev']['total']-8.0)<1e-9;must(s.raw('val',s.d('y'),*SHARED),0)
    # recorded arrays: shown only as task rows, or only as the collapsed row, are not adopted again
    s=Site(td,'h3');s.fake.config(hold_new=[True]);must(s.submit(s.d('c'),['0:0-5%2']),0);n=len(s.records('adopted'))
    must(s.raw('val',s.d('y'),*SHARED),0);arr=[j for j in s.fake.jobs()if j['task']is not None]
    s.fake.main('scancel',[arr[0]['base']],{});s.h.advance(400)       # the pending array is cancelled and purged from squeue
    view=s.fake.main('sacct',['-X','--duplicates','-u','zzheng8','-P','-n','-o','JobID','-S','2026-01-01T00:00:00'],{'TZ':'America/Los_Angeles'})[1]
    assert re.search(r'_\[0-5',view)and not s.fake.main('squeue',['--all','-u','zzheng8','-h','-r','--states=all','-o','%i'],{})[1].count(arr[0]['base']+'_')
    must(s.raw('val',s.d('z'),*SHARED),0);assert len(s.records('adopted'))==n
    ok('h_budget_from_sacct_stateful_fake_hand_values_open_spy_recorded_arrays')

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-17 (j) re-snapshot, (k) negative scans and real processes, (l) intent before sbatch
def jobs_named(s,part):return [j for j in s.fake.jobs()if part in j['name']]
def test_j_resnapshot(td):
    s=Site(td,'j1');s.others(30);late=s.others(2,state='PENDING',name='late')
    s.fake.config(hold_new=[False,True,True],triggers=[{'cmd':'squeue','with':['-A'],'nth':2,'do':'start','jobs':late}])
    out=must(s.lanes(2,s.d('c')),65,'re-snapshot violation','had started: reported, left running','cancelled while pending')
    w=jobs_named(s,'-lane-');m=jobs_named(s,'-merge-')
    assert sorted(j['state']for j in w)==['CANCELLED','RUNNING']and m[0]['state']=='PENDING'and 'kept'in out
    sc=s.history('scancel');assert sc and all('--state=PENDING'in h['argv']for h in sc)
    # repeated lanes 1 with a live earlier worker, then lanes 0: the superseded merge and every merge a live worker depends on stay pending
    s=Site(td,'j2');s.others(29);d=s.d('c');must(s.lanes(1,d),0);m0=jobs_named(s,'-merge-')[0]['id']
    late=s.others(2,state='PENDING',name='late')
    s.fake.config(hold_new=[True,True],triggers=[{'cmd':'squeue','with':['-A'],'nth':2,'do':'start','jobs':late}])
    must(s.lanes(1,d),65,'re-snapshot violation')
    ms={j['id']:j['state']for j in jobs_named(s,'-merge-')};assert ms[m0]=='PENDING'and list(ms.values()).count('PENDING')==2,ms
    s.fake.config(triggers=[{'cmd':'squeue','with':['-A'],'nth':2,'do':'add','jobs':[{'name':'late3','user':'dsd','partition':'compute','state':'RUNNING','cpus':128}]}])
    must(s.lanes(0,d),65,'re-snapshot violation');assert all(j['state']=='PENDING'for j in jobs_named(s,'-merge-'))
    must(s.lanes(0,d),65)   # still over 32: the superseded merges are kept again
    st=s.fake._mem
    for j in st['jobs']:
        if j['name'].startswith(('late','job')):j['state']='COMPLETED';j['end']=s.fake.now()
    out=must(s.lanes(0,d),0,'superseded pending merge')
    ms=jobs_named(s,'-merge-');assert sum(j['state']=='PENDING'for j in ms)==1 and sum(j['state']=='CANCELLED'for j in ms)==len(ms)-1==4,[j['state']for j in ms]
    # race: the call's merge can be cancelled (no earlier live workers), a superseded merge does not cover its workers, and the
    # fake starts a worker of the call just before the merge's cancel: "live without a merge: run `lanes 0`"
    s=Site(td,'j3');s.others(30);late=s.others(2,state='PENDING',name='late');d=s.d('c');c=ledger.dir_sha12(d);x=s.others(1,name='anchor')[0]
    t=hx();s.fake.add_job(f'c8d3-merge-{c}-{t}',state='PENDING',partition='shared',comment=f'c8d3:{c}:{"0"*12}:{t}',hold_start=False)
    s.fake.set([j for j in s.fake.jobs()if j['name'].endswith(t)][0]['id'],dep={'kind':'afterany','ids':[x]})
    s.fake.config(hold_new=[True,True],triggers=[{'cmd':'squeue','with':['-A'],'nth':2,'do':'start','jobs':late}])
    def resurrect(name,info):
        if name=='resnapshot':
            w=jobs_named(s,'-lane-')[0]['id'];s.fake.config(triggers=[{'cmd':'scancel','nth':2,'do':'start','jobs':[w]}])
    s.h.on_point=resurrect;out=must(s.lanes(1,d),65,'live without a merge: run `lanes 0`');s.h.on_point=None
    tm=[r for r in s.records('intent')if r['role']=='merge'][-1]['token']     # the call's merge, cancelled while pending: never eligible
    must(s.raw('val',s.d('x'),*SHARED),0,f'intent {tm} resolved (never_started')
    # a job of the call that starts between the re-snapshot and the cancel: a controller-side filter skips it (reported as started);
    # a client-side filter cancels it after it started ("started, then cancelled", never "never ran")
    for mode,needle in (('controller','had started: reported, left running'),('client','started, then cancelled')):
        s=Site(td,'j4'+mode);s.others(30);late=s.others(2,state='PENDING',name='late')
        trig=[{'cmd':'squeue','with':['-A'],'nth':2,'do':'start','jobs':late}]
        s.fake.config(hold_new=[True,True],triggers=trig)
        def arm(name,info,s=s,mode=mode):
            if name=='resnapshot':
                w=jobs_named(s,'-lane-')[0]['id']
                if mode=='controller':s.fake.config(triggers=[{'cmd':'scancel','do':'start','jobs':[w]}])
                else:s.fake.config(scancel_client_race='any')
        s.h.on_point=arm;out=must(s.lanes(1,s.d('c')),65,needle);s.h.on_point=None
        assert 'never ran'not in out
    ok('j_resnapshot_cancels_pending_only_merges_kept_race_reported')

class PSite:
    """A site whose tools and fake Slurm run as real processes (the fake's executables first on PATH)."""
    def __init__(self,td:Path,name:str,**env):
        self.dir=td/name;self.root=self.dir/'c8';self.root.mkdir(parents=True);(self.root/'ledger.jsonl').write_bytes(b'')
        self.events=self.dir/'events.jsonl';self.clock=self.dir/'clock.json';self.clock.write_text('{"offset":0}')
        self.fake=Fake(str(self.dir/'fake.json'),str(self.events),str(self.clock));self.hooks_path=self.dir/'hooks.json';self.hooks({})
        self.env={**os.environ,'PATH':f'{install(td/"fakebin")}:{os.environ["PATH"]}','C8_SITE':'fake','C8_ROOT':str(self.root),'C8_BUDGET_LINE':'dev',
                  'C8_RESERVATION':BASE,'C8_COMPUTE_CAP':'4','C8_LOCK_WAIT':'10','C8_TEST_HOOKS':str(self.hooks_path),'FAKE_TIMEOUT_SECONDS':'2',
                  'FAKE_SCRIPTS':str(scripts(self.dir/'scripts')),**self.fake.env(),**env}
        for k in ('C8_SBATCH_ARGS','C8_MERGE_SBATCH_ARGS','C8_SU_APPROVED','C8_TEST_FAULT','SLURM_CLUSTER_NAME','SLURM_JOB_ID'):self.env.pop(k,None)
    def hooks(self,cfg):self.hooks_path.write_text(json.dumps({'events':str(self.events),'clock':str(self.clock),'settings':{'lock_poll':0.01,'query_timeout':5},**cfg}))
    def raw(self,role,d,*sb,env=None,popen=False):
        argv=[sys.executable,'-B',str(ROOT/'tools/slurm_submit.py'),'raw','--role',role,'--dir',str(d),'--',*sb];e={**self.env,**(env or{})}
        if popen:return subprocess.Popen(argv,env=e,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        cp=subprocess.run(argv,env=e,capture_output=True,text=True,timeout=120);return cp.returncode,cp.stdout,cp.stderr
    def lanes(self,n,d,popen=False,env=None):
        argv=[sys.executable,'-B',str(ROOT/'tests/fake_slurm/driver.py'),'lanes',str(n),'--dir',str(d)];e={**self.env,**(env or{})}
        if popen:return subprocess.Popen(argv,env=e,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        cp=subprocess.run(argv,env=e,capture_output=True,text=True,timeout=120);return cp.returncode,cp.stdout,cp.stderr
    def d(self,name):return self.root/'runs'/name
    def events_list(self):return [json.loads(l)for l in self.events.read_text().splitlines()]if self.events.exists()else[]
    def sbatches(self):return [h for h in self.fake.state()['history']if h['cmd']=='sbatch'and '--test-only'not in h['argv']]
    def ours(self,n,**kw):
        out=[]
        for _ in range(n):t=hx();c=hx();out+=self.fake.add_job(f'c8d3-lane-{c}-{t}',partition='compute',comment=f'c8d3:{c}:{"0"*12}:{t}',cpus=128,**kw)
        return out

def scan_k(root:Path)->list:
    """A-ORC-17 (k), as written: tools/ and slurm/ contain no `sbatch --hold`, no mkdir lock, no journal, no start gate,
    and no job-creating sbatch launch outside D.11 step 5. Returns the violations (empty when the tree passes)."""
    bad=[];files={p:p.read_text(errors='replace')for p in sorted((root/'tools').rglob('*.py'))+sorted(f for f in (root/'slurm').rglob('*')if f.is_file())}
    for p,t in files.items():
        r=p.relative_to(root)
        if 'C8_SUBMIT_GATE'in t or 'gate.sh'in t:bad.append(f'{r}: start gate')
        if 'journal'in t.lower():bad.append(f'{r}: journal')
        if re.search(r"'--hold'\s*[,\]]",t)or 'scontrol release'in t or 'sbatch --hold'in t:bad.append(f'{r}: held submission')
        # mkdir locks: os.mkdir, the inherited campaign lock, or any line that creates a directory as a lock
        if re.search(r'\bos\.mkdir\(',t)or 'CampaignLock'in t or 'c7_submit.lock'in t:bad.append(f'{r}: mkdir lock')
        if any(re.search(r'mkdir',l)and re.search(r'lock',l,re.I)for l in t.splitlines()):bad.append(f'{r}: mkdir lock')
        if p.suffix=='.py':
            # every 'sbatch' argv in Python: only the D.11 step 5 launch (wrapped in timeout + exec guard) and --test-only
            # (an argv element 'sbatch' in a list or tuple, or a shell string run by subprocess or os)
            for m in re.finditer(r"""(?:[\[,]|=\s*\()\s*(['"])sbatch\1""",t):
                ctx=t[m.start(1):m.start(1)+40]
                if not(r==Path('tools/slurm_submit.py')and(ctx.startswith("'sbatch','--parsable'")or ctx.startswith("'sbatch','--test-only'"))):bad.append(f'{r}: sbatch launch {ctx!r}')
            if re.search(r"""\b(?:subprocess\.\w+|os\.(?:system|popen|exec\w*))\(\s*f?['"][^'"]*\bsbatch\b""",t):bad.append(f'{r}: shell launch')
        else:
            for n,l in enumerate(t.splitlines(),1):
                code=l.split('#',1)[0]if not l.lstrip().startswith('#!')else''
                if re.search(r'\bsbatch\b',code):bad.append(f'{r}:{n}: sbatch in a script')
    ss_text=files[root/'tools/slurm_submit.py']
    if len(re.findall(r"'sbatch','--parsable'",ss_text))!=1 or "['timeout','-s','KILL',str(SBATCH_KILL_AFTER),str(EXEC_GUARD),str(deadline)]+(STANDIN if standin else sb)"not in ss_text:
        bad.append('tools/slurm_submit.py: the launch is not the single timeout + exec-guard path')
    return bad

def test_k_negative_scans_and_real_processes(td):
    assert scan_k(ROOT)==[],scan_k(ROOT)
    # the scan can fail: a mkdir lock, a plain launch and a script sbatch in a scratch copy are each reported
    for name,(rel,text) in {'mkdir':('tools/x.py',"import os\nos.mkdir('/tmp/.lock')\n"),'campaign':('tools/y.py','from common import CampaignLock\n'),
                            'shell_mkdir':('slurm/z.sh','#!/bin/bash\nmkdir "$RUN/.lock" || exit 75\n'),
                            'launch':('tools/w.py',"import subprocess\nsubprocess.run(['sbatch','x.sh'])\n"),'shell':('tools/s.py',"import os\nos.system('sbatch x.sh')\n"),'tuple':('tools/t.py',"argv=('sbatch','--parsable','x.sh')\n"),'script':('slurm/v.sh','#!/bin/bash\nsbatch --parsable job.sh\n'),
                            'hold':('slurm/u.sh','#!/bin/bash\n# sbatch --hold would be refused\n'),'gate':('tools/g.py','C8_SUBMIT_GATE=1\n')}.items():
        cp=td/f'kscan_{name}';shutil.copytree(ROOT/'tools',cp/'tools');shutil.copytree(ROOT/'slurm',cp/'slurm');(cp/rel).write_text(text)
        assert scan_k(cp),name
    # Stage 3a: the campaign entry points are ported onto this admission engine (slurm_submit.py lanes|submit|window|
    # resubmit|release; c7_legacy/ is deleted). Without a planned C8_RUN (or C8_ROOT) they refuse (64) and submit nothing;
    # lanes.py queue and release-stale on a directory without a plan fail before taking the lock or writing anything.
    for cmd in (['queue',str(td)],['release-stale',str(td),'--queue',str(td/'none')]):
        cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools/lanes.py'),*cmd],env={**os.environ,'C8_SITE':'fake','C8_ROOT':str(td/'kroot')},capture_output=True,text=True)
        assert cp.returncode!=0 and not (td/'kroot').exists(),(cmd,cp.returncode,cp.stderr[-300:])
    for cmd in ('submit','window','resubmit','lanes','release'):
        for site in ({'C8_SITE':'expanse'},{'C8_SITE':'fake'},{}):
            cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools/slurm_submit.py'),cmd,'1'],env={**{k:v for k,v in os.environ.items()if k not in('C8_SITE','C8_ROOT','C8_RUN')},**site},capture_output=True,text=True)
            assert cp.returncode==64 and ('C8_ROOT'in cp.stderr or 'C8_RUN'in cp.stderr),(cmd,site,cp.returncode,cp.stderr[-300:])
    assert not (ROOT/'c7_legacy').exists(),'c7_legacy/ is deleted by the Stage-3a port (its docstring)'
    # real processes: the --wrap string byte for byte, every job-creating sbatch through the timeout shim and the exec guard
    s=PSite(td,'k1');wrap='set -eo pipefail; echo "a  b" \'c\'; x=$((1+2)); printf \'%s\\n\' "$x" | tr -d z # é ü\ttab'
    rc,out,err=s.raw('val',s.d('x'),'-A','yun124','-p','shared','--nodes=1','-c','1','--mem=1G','-t','00:05:00','--wrap',wrap);assert rc==0,err
    rc,out,err=s.raw('val',s.d('y'),'-A','yun124','-p','shared','--nodes=1','-c','1','--mem=1G','-t','00:05:00',f'--wrap={wrap}');assert rc==0,err
    sb=s.sbatches();assert len(sb)==2 and sb[0]['argv'][sb[0]['argv'].index('--wrap')+1]==wrap and f'--wrap={wrap}'in sb[1]['argv']
    ev=s.events_list();tpids={e['pid']for e in ev if e['event']=='fake:timeout_start'}
    sbe=[e for e in ev if e['event']=='fake:sbatch'and '--test-only'not in e['argv']];assert sbe and all(e['ppid']in tpids for e in sbe),(tpids,[e['ppid']for e in sbe])
    # the exec guard: a stall between the age check and the launch: exit 86 inside the timeout shim, no sbatch, not_submitted
    s.hooks({'stall_at':{'age_checked':61}});rc,out,err=s.raw('val',s.d('z'),*SHARED);assert rc==69 and 'exec guard'in err,err
    led=ledger.Ledger(ledger.Settings({'C8_SITE':'fake','C8_ROOT':str(s.root)}));led.read(writer=False);ns=[r for r in led.records if r['kind']=='not_submitted']
    assert ns and ns[-1]['exit_status']==86 and ns[-1]['launched']is False and len(s.sbatches())==2
    ok('k_negative_scans_wrap_bytes_timeout_shim_exec_guard_real_processes')

def test_l_intent_before_sbatch(td):
    for kind in ('raw','lanes2','submit'):
        s=Site(td,'l_'+kind);must(do(s,kind),0);ev=s.log;n=0
        for i,e in enumerate(ev):
            if e['event']!='fake:sbatch'or '--test-only'in e['argv']:continue
            name=[a for a in e['argv']if a.startswith('--job-name=')][0][11:];t=name[-12:];n+=1
            before=ev[:i]
            ia=[k for k,x in enumerate(before)if x['event']=='ledger_append'and x['kind']=='intent'and x['tokens']==[t]]
            fi=[k for k,x in enumerate(before)if x['event']=='intent_file'and x['token']==t]
            la=[k for k,x in enumerate(before)if x['event']=='lock_acquired'];lr=[k for k,x in enumerate(before)if x['event']=='lock_released']
            assert ia and fi and ia[0]<fi[0]and la and(not lr or lr[-1]<la[-1]),(kind,t)
            assert f':{t}'in [a for a in e['argv']if a.startswith('--comment=')][0]
        assert n=={'raw':1,'lanes2':3,'submit':2}[kind]
    faults=[{'errno':errno.EDQUOT},{'errno':errno.ENOSPC},{'errno':errno.EIO},{'short':1},{'short':'half'},{'short':'n-1'},{'fsync_errno':errno.EIO}]
    for kind in ('raw','lanes2','submit'):
        for i,f in enumerate(faults):
            # the intent record fails: 74, no sbatch; a short write leaves exactly the torn bytes; a failed fsync leaves it charged
            s=Site(td,f'lr_{kind}_{i}');s.h.faults['ledger:intent']=f;L=s.root/'ledger.jsonl'
            must(do(s,kind),74);assert not s.sbatches()and not s.records('not_submitted')and not list((s.root/'intents').glob('*.json'))
            data=L.read_bytes()
            if 'short'in f:
                assert ledger.Scan(data).status=='torn'and not data.endswith(b'\n')
                must(s.raw('val',s.d('y'),*SHARED),0,'truncated a torn final record');assert ledger.Scan(L.read_bytes()).status=='clean'
            if 'fsync_errno'in f:
                its=s.intents();assert len(its)==1 and list(its.values())[0].unresolved and s.budget()['lines']['dev']['intents']>0
            # the intent file fails after a complete record: 74, no sbatch, then not_submitted (launched false) resolves T at zero cost
            s=Site(td,f'lf_{kind}_{i}');s.h.faults['intent_file']=f
            must(do(s,kind),74);assert not s.sbatches()
            ns=s.records('not_submitted');assert len(ns)==1 and ns[0]['launched']is False and not ns[0]['ambiguous']
            t=ns[0]['token'];its=s.intents();assert not its[t].unresolved and its[t].floor_su()==0.0 and not (s.root/'intents'/f'{t}.json').exists()
    # stalls of 61 s: in the intent write, in the lock-descriptor fsync before sbatch, and between the age check and the launch
    for name,arm in (('stall_file',lambda s:s.h.faults.update({'intent_file':{'stall':61}})),('stall_lock',lambda s:s.h.faults.update({'lock_fsync:sbatch':{'stall':61}})),
                     ('stall_launch',lambda s:s.h.stall.update({'age_checked':61}))):
        s=Site(td,name);arm(s);rc=s.raw('val',s.d('x'),*SHARED);must(rc,69);assert not s.sbatches()
        ns=s.records('not_submitted');assert len(ns)==1 and ns[0]['launched']is False and not ns[0]['ambiguous'];assert not s.intents()[ns[0]['token']].unresolved
        if name=='stall_launch':assert ns[0]['exit_status']==86
        else:assert 'age check'in ns[0]['reason']
    # non-submission evidence: a listed rejection resolves T; a timeout kill and an unlisted error are ambiguous
    s=Site(td,'l_rej');s.fake.config(sbatch_rules=[{'nth':1,'action':'reject','stderr':'sbatch: error: Batch job submission failed: Invalid account or account/partition combination specified'}])
    must(s.raw('val',s.d('x'),*SHARED),69,'zero cost');t=s.records('not_submitted')[0]['token'];assert not s.intents()[t].unresolved and (s.root/'intents'/'resolved'/f'{t}.json').exists()
    s=Site(td,'l_tmo');s.fake.config(sbatch_rules=[{'nth':1,'action':'delay_timeout'}])
    must(s.raw('val',s.d('x'),*SHARED8),69,'killed by `timeout');ns=s.records('not_submitted')[0];assert ns['ambiguous']and s.intents()[ns['token']].unresolved
    assert abs(s.budget()['lines']['dev']['intents']-8.0)<1e-9
    s=Site(td,'l_sock');s.fake.config(sbatch_rules=[{'nth':1,'action':'ambiguous_create','stderr':'sbatch: error: Batch job submission failed: Socket timed out on send/recv operation'}])
    must(s.raw('val',s.d('x'),*SHARED8),69,'may exist');ns=s.records('not_submitted')[0];t=ns['token'];assert ns['ambiguous']
    jobs=ours_jobs(s);assert len(jobs)==1 and jobs[0]['name'].endswith(t)
    r=s.budget();assert abs(r['lines']['dev']['total']-8.0)<1e-9 and s.intents()[t].unresolved     # counted once, with T
    s.fake.finish(jobs[0]['id'],elapsed=600);must(s.raw('val',s.d('y'),*SHARED),0,f'intent {t} resolved (terminal')
    ok('l_intent_record_and_file_before_every_sbatch_failures_stalls_rejections')

def arm_on_intent(s,nth,faults)->dict:
    """Arm write faults when the nth job of the call reaches its intent (its nth `before_intent` point); returns the
    sizes of the faulted writes (the frame length n of a short write)."""
    n=[0];sizes={};orig=s.h.write_fault
    def on(name,info):
        if name=='before_intent':
            n[0]+=1
            if n[0]==nth:s.h.faults.update({k:dict(v)for k,v in faults.items()})
    def wf(point,nbytes):
        spec=orig(point,nbytes)
        if spec is not None:sizes[point]=nbytes
        return spec
    s.h.on_point=on;s.h.write_fault=wf
    return sizes

def multi(s,kind,d):return s.lanes(2,d)if kind=='lanes2'else s.submit(d,['0:0-1','2:0-1'])   # 3 jobs each (2 workers or arrays + merge)

def test_l_multi_job_append_failures(td):
    """D.11 step 5 and A-ORC-17 (l) for `lanes 2` and `submit`: a failed or short append of the 2nd or the last job's
    intent record, or of a `not_submitted` record after an earlier job of the call was submitted, is followed by no
    further append; the ledger ends in exactly the torn bytes, the next admission truncates them with no rebuild and
    adopts the jobs already submitted."""
    L=lambda s:s.root/'ledger.jsonl'
    def after(s,jobs,torn,case):
        out=must(s.raw('val',s.d('y'),*SHARED),0,*(['truncated a torn final record']if torn else[]))   # no rebuild
        assert ledger.Scan(L(s).read_bytes()).status=='clean',case
        assert {r['job_id']for r in s.records('adopted')}==jobs,(case,s.records('adopted'),jobs)    # adopted, each once
        return out
    for kind in ('lanes2','submit2'):
        for nth in (2,3):
            for i,f in enumerate(({'short':1},{'short':'half'},{'short':'n-1'},{'fsync_errno':errno.EIO})):
                case=(kind,nth,f);s=Site(td,f'lm_{kind}_{nth}_{i}');sizes=arm_on_intent(s,nth,{'ledger:intent':f})
                rc=multi(s,kind,s.d('c'));s.h.on_point=None;must(rc,74)
                assert len(s.sbatches())==nth-1,case                                      # no sbatch for that job or later
                assert not s.records('submit')and not s.records('not_submitted'),case    # nothing appended after the failure
                sc=ledger.Scan(L(s).read_bytes())
                if 'short'in f:
                    n=sizes['ledger:intent'];k={1:1,'half':n//2,'n-1':n-1}[f['short']]
                    assert sc.status=='torn'and len(sc.tail())==k and len(s.records('intent'))==nth-1,(case,sc.status,len(sc.tail()),k)
                else:
                    assert sc.status=='clean'and len(s.records('intent'))==nth,case    # complete, not fsynced: it stays, unresolved
                jobs={j['base']for j in ours_jobs(s)};tk=s.records('intent')[nth-1]['token']if 'fsync_errno'in f else None
                after(s,jobs,'short'in f,case)
                if tk:assert s.intents()[tk].unresolved and not any(r['token']==tk for r in s.records('not_submitted'))
        # job 2's intent file fails, then its not_submitted append is short; and job 2's sbatch is ambiguous, then the same
        s=Site(td,f'lm_{kind}_file');sizes=arm_on_intent(s,2,{'intent_file':{'errno':errno.EIO},'ledger:not_submitted':{'short':'half'}})
        must(multi(s,kind,s.d('c')),74);s.h.on_point=None
        sc=ledger.Scan(L(s).read_bytes());assert sc.status=='torn'and len(sc.tail())==sizes['ledger:not_submitted']//2 and len(s.sbatches())==1
        assert not s.records('submit');t2=s.records('intent')[1]['token'];jobs={j['base']for j in ours_jobs(s)}
        out=after(s,jobs,True,(kind,'file'));assert s.intents()[t2].unresolved and 'counted from its ledger copy'in out   # over-count only
        s=Site(td,f'lm_{kind}_amb');s.fake.config(sbatch_rules=[{'nth':2,'action':'delay_timeout'}]);sizes=arm_on_intent(s,2,{'ledger:not_submitted':{'short':1}})
        must(multi(s,kind,s.d('c')),74,'submit` records are not written');s.h.on_point=None
        sc=ledger.Scan(L(s).read_bytes());assert sc.status=='torn'and len(sc.tail())==1 and not s.records('submit')
        t2=s.records('intent')[1]['token'];jobs={j['base']for j in ours_jobs(s)};after(s,jobs,True,(kind,'amb'))
        assert s.intents()[t2].unresolved                                                     # ambiguous: still counted
    # EDQUOT at the intent file's creation (Lustre's file quota): 74, no sbatch, not_submitted (launched: false) resolves T
    s=Site(td,'lm_create');s.h.faults['intent_file:create']={'errno':errno.EDQUOT}
    must(s.raw('val',s.d('x'),*SHARED),74,'EDQUOT');assert not s.sbatches()
    ns=s.records('not_submitted');assert len(ns)==1 and ns[0]['launched']is False and not ns[0]['ambiguous']
    t=ns[0]['token'];assert not s.intents()[t].unresolved and not (s.root/'intents'/f'{t}.json').exists()
    L(s).write_bytes(L(s).read_bytes()+b'{"rec":{"torn');s.h.faults['evidence:create']={'errno':errno.EDQUOT}
    must(s.raw('val',s.d('x'),*SHARED),74,'nothing truncated');assert L(s).read_bytes().endswith(b'{"rec":{"torn')
    must(s.raw('val',s.d('x'),*SHARED),0,'truncated a torn final record')
    ok('l_multi_job_no_append_after_a_failed_or_short_intent_or_not_submitted_append_create_edquot')

def test_budget_standalone_evidence(td):
    """HD17: a standalone budget.py applies the evidence rules (a) and (c) in memory and records nothing (J-DRL-10:
    after the jobs end, it shows their intents resolved and equals the hand sum)."""
    s=Site(td,'bse')
    must(s.raw('val',s.d('a'),*SHARED8),0);ta=s.records('intent')[-1]['token'];ja=s.records('submit')[-1]['job_id']
    must(s.submit(s.d('c'),['0:0-1']),0)
    tarr=[r for r in s.records('intent')if r['role']=='off0'][0]['token'];tm=[r for r in s.records('intent')if r['role']=='merge'][0]['token']
    s.fake.main('scancel',[jobs_named(s,'-merge-')[0]['id']],{})       # the merge, cancelled while it waits on afterok (never eligible)
    s.fake.finish(ja,elapsed=600)
    for j in [j for j in s.fake.jobs()if j['task']is not None]:s.fake.finish(j['id'],elapsed=60)
    s.h.advance(400)                                                     # all have left squeue (MinJobAge); sacct holds their rows
    n0=len(s.records());r=s.budget();hand=8*600/3600+2*32*60/3600       # SHARED8 for 600 s; two 32-core tasks for 60 s; the merge 0
    assert abs(r['lines']['dev']['total']-hand)<1e-9 and abs(r['lines']['dev']['intents'])<1e-9,(r['lines'],hand)
    ev=r['resolved_by_evidence_now'];assert (ev[ta]['rule'],ev[tarr]['rule'],ev[tm]['rule'],ev[tm]['charge_su'])==('terminal','terminal','never_started',0.0),ev
    assert not r['unresolved_intents']and not any(r['slot_extras'].values())and len(s.records())==n0 and not s.records('resolution')   # nothing recorded
    must(s.raw('val',s.d('b'),*SHARED),0,f'intent {ta} resolved (terminal',f'intent {tm} resolved (never_started',f'intent {tarr} resolved (terminal')
    assert abs(s.budget()['lines']['dev']['total']-hand-1/12)<1e-9                # the same numbers once admission has recorded them
    ok('budget_standalone_applies_evidence_rules_in_memory_and_records_nothing')

def test_resnapshot_query_failures(td):
    """D.11 step 7: a failed `scancel --state=PENDING` or a failed re-query ends the call (69), names every job of the
    call that may still be pending, and claims no cancellation."""
    for name,cfg in (('scancel',{'fail_at':{'scancel':[1]}}),('requery',{'fail_at':{'squeue':[5]}})):
        s=Site(td,'jf_'+name);s.others(30);late=s.others(2,state='PENDING',name='late')
        s.fake.config(hold_new=[True,True,True],triggers=[{'cmd':'squeue','with':['-A'],'nth':2,'do':'start','jobs':late}],**cfg)
        out=must(s.lanes(2,s.d('c')),69,'re-snapshot violation','state unknown','may still be pending')
        assert 'were cancelled'not in out and 'cancelled while pending'not in out and 'started, then cancelled'not in out,out[-800:]
        w=jobs_named(s,'-lane-');assert len(w)==2
        if name=='scancel':assert all(j['state']=='PENDING'for j in w)and all(j['id']in out.split('may still be pending:')[-1]for j in w)
        else:assert all(j['id']in out.split('may still be pending:')[-1]for j in w)   # the re-query failed: every job of the call is named
    ok('resnapshot_failed_scancel_or_requery_exits_69_names_pending_jobs_claims_no_cancellation')

def test_missing_ledger_writers(td):
    """HD17/D.12: a missing ledger stays a repair block; neither `register` (inside a running plan job) nor `resolve`
    of another stuck intent re-creates it, so admission stays blocked and the node cap holds."""
    s=Site(td,'mlw');s.ours(3);t=a_inflight(s);(s.root/'ledger.jsonl').unlink();(s.root/'intents'/f'{t}.json').unlink()
    must(s.lanes(1,s.d('b')),69,'missing');d=s.d('plan1',plan=True)
    must(s.ledger_cmd(['register',str(d),'--role','plan'],env={'SLURM_JOB_ID':'4242','SLURM_JOB_NAME':f'c8d3-plan-{ledger.dir_sha12(d)}-{hx()}'}),69,'missing')
    assert not (s.root/'ledger.jsonl').exists();must(s.lanes(1,s.d('b')),69,'missing');s.fake.accept();assert s.counts()['nodes']==4
    s=Site(td,'mlw_r');s.ours(3);t=a_inflight(s)
    s.fake.config(sbatch_rules=[{'name_has':'-ambx-','action':'delay_timeout'}]);must(s.raw('ambx',s.d('amb'),*SHARED),69)
    x=s.records('not_submitted')[0]['token'];(s.root/'ledger.jsonl').unlink();(s.root/'intents'/f'{t}.json').unlink()
    must(s.lanes(1,s.d('b')),69);s.h.advance(G+1)
    must(s.ledger_cmd(['resolve',x,*decision_log(s)]),69,'missing');assert not (s.root/'ledger.jsonl').exists()
    must(s.lanes(1,s.d('b')),69);s.fake.accept();assert s.counts()['nodes']==4
    try:s.budget();raise AssertionError('budget.py ran on a missing ledger')
    except Refuse as e:assert e.code==69
    ok('missing_ledger_register_and_resolve_refuse_never_recreate_it')

def test_script_directives(td):
    """`#SBATCH` lines read as sbatch reads them (column 0 only; comment lines skipped; the first command ends the
    scan); #SLURM, #PBS and #BSUB directives, non-UTF-8 scripts, DOS line breaks and a missing #! refused (64)."""
    s=Site(td,'dirs')
    def opts(text,name='s.sh'):
        p=s.dir/name;p.write_bytes(text if isinstance(text,bytes)else text.encode());return ss.script_options(p)
    assert opts('#!/bin/bash\n#SBATCH -c 64\n  #SBATCH -c 1\necho hi\n')==[('cpus-per-task','64')]       # an indented #SBATCH is a comment
    assert opts('#!/bin/bash\n  # an indented comment\n\n#SBATCH -c 4\necho\n#SBATCH -c 2\n')==[('cpus-per-task','4')]
    for bad in ('#!/bin/bash\n#SBATCH -t 00:05:00\n#PBS -l walltime=48:00:00\n#PBS -h\necho\n','#!/bin/bash\n#BSUB -W 10\necho\n','#!/bin/bash\n#SLURM -c 2\necho\n',
                '#!/bin/bash\necho\n#PBS -a 2359\n','echo no shebang\n','#!/bin/bash\r\n#SBATCH -c 2\r\necho\r\n',b'#!/bin/bash\n# caf\xe9\n#SBATCH -c 2\necho\n'):
        try:opts(bad);raise AssertionError(bad)
        except Refuse as e:assert e.code==64,(bad,e)
    sc=s.dir/'job.sh';sc.write_text('#!/bin/bash\n#SBATCH -c 8 --mem=16G\n  #SBATCH -c 1\necho ok\n')   # the tool and the fake sbatch agree on the size
    must(s.raw('val',s.d('x'),'-A','yun124','-p','shared','--nodes=1','-t','01:00:00',str(sc)),0,'(shared, 8.00 SU reserved)')
    assert ours_jobs(s)[-1]['cpus']==8
    ok('sbatch_directives_column_zero_foreign_directives_and_bad_scripts_refused')

def test_decoding(td):
    """Scheduler output is decoded with replacement: a non-UTF-8 byte in another user's job name crashes nothing."""
    cp=budget._run([sys.executable,'-c','import sys;sys.stdout.buffer.write(b"5001|caf\\xe9|x\\n");sys.stderr.buffer.write(b"\\xff")'],dict(os.environ),30)
    assert cp.returncode==0 and '\ufffd'in cp.stdout and '\ufffd'in cp.stderr
    real=budget.RUNNER
    def bad(argv,env,t):raise UnicodeDecodeError('utf-8',b'\xff',0,1,'invalid start byte')
    budget.RUNNER=bad
    try:
        try:budget.query(['squeue','--all'],{},'test');raise AssertionError('no refusal')
        except Refuse as e:assert e.code==69
    finally:budget.RUNNER=real
    p=PSite(td,'dec');p.fake.add_job('caf\u00e9-job',user='dsd',partition='compute',state='RUNNING',cpus=128)   # printed as UTF-8 by the fake
    wrap=td/'decbin';wrap.mkdir();fb=install(td/'fakebin')
    (wrap/'squeue').write_text(f'#!/bin/sh\n"{fb}/squeue" "$@" | "{sys.executable}" -c \'import sys;sys.stdout.buffer.write(sys.stdin.buffer.read().replace(b"\\xc3\\xa9",b"\\xe9"))\'\n')
    (wrap/'squeue').chmod(0o755)
    rc,out,err=p.raw('val',p.d('x'),*SHARED,env={'PATH':f'{wrap}:{p.env["PATH"]}'});assert rc==0,err[-800:]   # latin-1 bytes in another user's job name
    ok('scheduler_output_decoded_with_replacement')

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-17 (m) parent killed during sbatch with delayed acceptance, (n) accounting delayed beyond squeue retention,
# (o) resolution and de-duplication
def decision_log(s)->list:
    log=s.dir/'PLAN-REVIEW-LOG.md';log.write_text('# log\n- **User decision (2026-10-04): close stuck intents of the drills; keep their SU.**\n')
    return ['--user-decision','PLAN-REVIEW-LOG.md:2','--decision-log',str(log)]

M_SHARES=(('nodes',lambda s:s.ours(3),{},'lanes','-lane-','nodes',('nodes',4)),
          ('normal',lambda s:s.ours(10),{'C8_COMPUTE_CAP':'32','C8_RESERVATION':WIDE(32)},'raw_compute','-val-','normal_run',('normal',11)),
          ('account',lambda s:s.others(31),{},'raw_compute','-val-','account',('account',32)),
          ('shared',lambda s:s.ours(31,partition='shared',role='x'),{},'raw_shared','-val-','shared',('shared',32)))
def test_m_killed_during_sbatch(td):
    cases=(('nodes',lambda s:s.ours(3),{},lambda s,d:s.lanes(1,d),'nodes','-lane-',('nodes',4)),
           ('normal',lambda s:s.ours(10),{'C8_COMPUTE_CAP':'32','C8_RESERVATION':WIDE(32)},lambda s,d:s.raw('val',d,*COMPUTE),'normal_run','-val-',('normal',11)),
           ('shared',lambda s:s.ours(31,partition='shared',role='x'),{},lambda s,d:s.raw('val',d,*SHARED),'shared','-val-',('shared',32)))
    for name,setup,env,sub,share,tag,(key,lim) in cases:
        s=Site(td,'m_'+name,**env);setup(s);s.fake.config(sbatch_rules=[{'name_has':tag,'action':'delay'}])
        rc=sub(s,s.d('a'));assert rc[0]==-9 and len(s.fake.state()['inflight'])==1,rc
        must(sub(s,s.d('b')),65,share);s.fake.accept();assert s.counts()[key]==lim,(name,s.counts())
    s=Site(td,'m_tmo');s.ours(3);s.fake.config(sbatch_rules=[{'name_has':'-lane-','action':'delay_timeout'}])
    must(s.lanes(1,s.d('a')),69,'killed by `timeout');must(s.lanes(1,s.d('b')),65,'nodes');s.fake.accept();assert s.counts()['nodes']==4
    s=Site(td,'m_ctl');s.ours(3);s.fake.config(sbatch_rules=[{'name_has':'-lane-','action':'delay'}]);assert s.lanes(1,s.d('a'))[0]==-9
    s.h.switches.add('no_intents');must(s.lanes(1,s.d('b')),0);s.fake.accept();assert s.counts()['nodes']==5    # control: the share is exceeded
    # acceptance between B's queries: after both squeue snapshots, before the sacct queries (R22; deterministic), for
    # each of the four shares of A-ORC-11 "Intents" (nodes, normal-QOS live, account, shared)
    def direct(s,kind,d):
        o,e=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(o),contextlib.redirect_stderr(e):
            if kind=='lanes':rc=driver.main(['lanes','1','--dir',str(d)],s.env)
            else:rc=ss.main(['raw','--role','val','--dir',str(d),'--',*(COMPUTE if kind=='raw_compute'else SHARED)],s.env)
        return rc,o.getvalue(),e.getvalue()
    for share,setup,env,kind,tag,needle,(key,lim) in M_SHARES:
        for ctl in (False,True):
            s=Site(td,f'm_between_{share}{int(ctl)}',**env);setup(s);s.fake.config(sbatch_rules=[{'name_has':tag,'action':'delay'}])
            rc=s.lanes(1,s.d('a'))if kind=='lanes'else s.raw('val',s.d('a'),*(COMPUTE if kind=='raw_compute'else SHARED));assert rc[0]==-9,rc
            s.fake.config(triggers=[{'cmd':'sacct','without':['-s'],'do':'accept'}]);seen={};real=budget.RUNNER
            def spy(argv,env,t,real=real,seen=seen):
                cp=real(argv,env,t)
                if argv[0]=='sacct':seen.setdefault('s'if '-s'in argv else'u',cp.stdout)   # the admission's own two queries
                return cp
            if ctl:s.h.switches.add('sighting_rule_r5')
            s.activate();budget.RUNNER=spy
            try:rc,out,err=direct(s,kind,s.d('b'))
            finally:budget.RUNNER=real
            assert 'RUNNING'in seen['u']and tag in seen['u']and tag not in seen['s'],(share,seen)
            if not ctl:assert rc==65 and needle in err and 'refused by admission'in err and s.counts()[key]==lim,(share,rc,err[-400:],s.counts())
            else:assert rc in(0,65)and 'refused by admission'not in err and s.counts()[key]==lim+1,(share,rc,s.counts())   # control: r5's rule admits B
    # real processes: A is SIGKILLed while its sbatch hangs in flight; the orphaned timeout shim kills the hanging sbatch
    p=PSite(td,'m_real');p.ours(3);p.fake.config(sbatch_rules=[{'name_has':'-lane-','action':'delay'}])
    a=p.lanes(1,p.d('a'),popen=True)
    for _ in range(600):
        if p.fake.state()['inflight']:break
        time.sleep(0.02)
    a.send_signal(signal.SIGKILL);a.wait();t0=time.time();rc,out,err=p.lanes(1,p.d('b'));assert rc==65 and 'nodes'in err,err
    p.fake.accept();assert p.fake.counts()['nodes']==4
    for _ in range(300):
        if any(e['event']=='fake:timeout_kill'for e in p.events_list()):break
        time.sleep(0.02)
    assert any(e['event']=='fake:timeout_kill'for e in p.events_list()),'the timeout shim did not outlive the killed submitter'
    ok('m_parent_killed_during_sbatch_delayed_acceptance_and_between_queries')

def killed_raw(s,args=COMPUTE,point='after_sbatch'):
    s.h.kill[point]=1;rc=s.raw('val',s.d('a'+hx()),*args);assert rc[0]==-9,rc
    j=[j for j in ours_jobs(s)if '-val-'in j['name']];t=s.records('intent')[-1]['token'];return (j[-1]['id']if j else None),t

N_SHARES=(('nodes',lambda s:s.ours(3),{},COMPUTE,'nodes',128.0,128.0),('normal',lambda s:s.ours(10),{'C8_COMPUTE_CAP':'32','C8_RESERVATION':WIDE(32)},COMPUTE,'normal_run',128.0,128.0),
          ('account',lambda s:s.others(31),{},COMPUTE,'account',128.0,128.0),('shared',lambda s:s.ours(31,partition='shared',role='x'),{},SHARED,'shared',1/12,1.0))
def test_n_accounting_delayed(td):
    def ended(s,args=COMPUTE):
        j,t=killed_raw(s,args);assert not s.records('submit')
        s.fake.set(j,sacct_hold=True);s.fake.finish(j,elapsed=600);s.h.advance(400)   # ended after 10 min, purged from squeue, sacct lagging
        assert j not in s.fake.main('squeue',['--all','-h','-u','zzheng8','-r','--states=all','-o','%i'],{})[1].split();return j,t
    for share,setup,env,args,needle,su,bill in N_SHARES:   # A-ORC-11 "Intents": the four refusals after the job ended, sacct lagging
        s=Site(td,'n_slots_'+share,**env);setup(s);j,t=ended(s,args)
        for adv in (20*60-400,G+1-20*60,86400):                                  # 20 min after the intent, G + 1 s, G + 1 day
            s.h.advance(adv);assert s.budget()['lines']['dev']['intents']>=su-1e-9,share
            must(s.raw('val',s.d('b'),*args),65,needle,'refused by admission')    # fits only without its slots
            assert s.intents()[t].unresolved
        s.fake.deliver(j);out=must(s.raw('val',s.d('b'),*args),0,f'intent {t} resolved (terminal')
        res=[r for r in s.records('resolution')if r['token']==t][0];assert abs(res['charge_su']-bill*600/3600)<1e-6 and (s.root/'intents'/'resolved'/f'{t}.json').exists()
    s2=Site(td,'n_su',C8_COMPUTE_CAP='8',C8_RESERVATION=WIDE(8));s2.spent(2500-128-64);j2,t2=ended(s2)   # this site's 2,500 sub-cap (S2-004)
    for adv in (20*60-400,G+1-20*60,86400):
        s2.h.advance(adv);must(s2.raw('val',s2.d('b'),*COMPUTE),65,'SU gate')   # fits only without its SU
    s2.fake.deliver(j2);must(s2.raw('val',s2.d('b'),*COMPUTE),0)
    # lost accounting: the user's decision frees the slots, never the SU
    s=Site(td,'n_lost');s.ours(3);j,t=ended(s);dl=decision_log(s)
    must(s.ledger_cmd(['resolve',t,*dl]),64,'acts only from G');s.h.advance(G)
    must(s.ledger_cmd(['resolve',t,'--user-decision','PLAN-REVIEW-LOG.md:1','--decision-log',dl[-1]]),64,'decision line')
    must(s.ledger_cmd(['resolve',t,*dl]),0,'resolved by the user decision');r=[x for x in s.records('resolution')if x['token']==t][0]
    assert r['rule']=='user_decision'and r['charge_su']==128.0 and r['decision']['sha256']
    must(s.raw('val',s.d('b'),*COMPUTE),0);live=3*128+128                          # the three live nodes and B, at their reservations
    assert abs(s.budget()['lines']['dev']['total']-live-128)<1e-6                   # slots free; its SU stays 128
    s.fake.deliver(j);assert abs(s.budget()['lines']['dev']['total']-live-128)<1e-6  # a later, smaller sacct charge never lowers it
    st=s.fake._mem;jj=[x for x in st['jobs']if x['id']==j][0];jj['attempts'].append({'submit':jj['submit']-7200,'start':jj['submit']-7200,'end':jj['submit']-1,'state':'NODE_FAIL','elapsed':7000})
    assert abs(s.budget()['lines']['dev']['total']-live-128*(7000+600)/3600)<1e-6   # a larger one replaces it
    s2=Site(td,'n_lost_su',C8_COMPUTE_CAP='8',C8_RESERVATION=WIDE(8));s2.spent(2500-128-64);j2,t2=ended(s2);s2.h.advance(G);must(s2.ledger_cmd(['resolve',t2,*decision_log(s2)]),0)
    must(s2.raw('val',s2.d('b'),*COMPUTE),65,'SU gate')
    # an ambiguous sbatch whose job is never seen: slots and SU at every age; the user's decision frees the slots only
    s=Site(td,'n_amb');s.ours(3);s.fake.config(sbatch_rules=[{'nth':1,'action':'delay_timeout'}]);must(s.raw('val',s.d('a'),*COMPUTE),69)
    t=s.records('not_submitted')[0]['token'];s.h.advance(86400+G)
    must(s.raw('val',s.d('b'),*COMPUTE),65,'nodes');assert s.budget()['lines']['dev']['intents']==128.0
    must(s.ledger_cmd(['resolve',t,*decision_log(s)]),0);must(s.raw('val',s.d('b'),*COMPUTE),0);assert s.budget()['lines']['dev']['intents']==128.0
    s=Site(td,'n_lostconn');s.ours(3)
    s.fake.config(sbatch_rules=[{'nth':1,'action':'reject','stderr':'sbatch: error: Batch job submission failed: Socket timed out on send/recv operation'}])
    must(s.raw('val',s.d('a'),*COMPUTE),69,'may exist');t=s.records('not_submitted')[0]['token'];assert s.records('not_submitted')[0]['ambiguous']
    s.h.advance(86400+G);must(s.raw('val',s.d('b'),*COMPUTE),65,'nodes');assert s.intents()[t].unresolved
    # late acceptance after G and after B's refusal: counted once by T until its terminal rows
    s=Site(td,'n_late');s.ours(3);s.fake.config(sbatch_rules=[{'name_has':'-lane-','action':'delay'}]);assert s.lanes(1,s.d('a'))[0]==-9
    s.h.advance(G+60);must(s.lanes(1,s.d('b')),65,'nodes');s.fake.accept();assert s.counts()['nodes']==4
    must(s.lanes(1,s.d('b')),65,'"nodes": "4+1/4"')
    ok('n_accounting_delayed_slots_and_su_kept_until_rows_or_decision')

def test_o_resolution_dedup(td):
    s=Site(td,'o1');must(s.raw('val',s.d('a'),*SHARED8),0);t=s.records('intent')[-1]['token'];j=s.records('submit')[-1]['job_id']
    must(s.raw('val',s.d('b'),*SHARED),0);assert s.intents()[t].unresolved                 # live: the submit record resolves nothing
    r=s.budget();assert abs(r['lines']['dev']['total']-8-1/12)<1e-9                          # a live job equal to its intent: counted once
    s.fake.finish(j,elapsed=600);must(s.raw('val',s.d('c'),*SHARED),0,f'intent {t} resolved (terminal')
    # an array resolves only when every task of its range is terminal; until then it counts all its planned tasks
    s=Site(td,'o2');must(s.submit(s.d('a'),['0:0-3%2']),0);ta=s.records('intent')[0]['token'];tasks=[j for j in s.fake.jobs()if j['task']is not None]
    for k in range(3):
        jj=[x for x in s.fake.jobs()if x['id']==tasks[k]['id']][0]
        if jj['state']=='PENDING':s.fake.set(jj['id'],state='RUNNING',start=s.fake.now()-60)
        s.fake.finish(tasks[k]['id'],elapsed=60)
    out=must(s.raw('val',s.d('b'),*SHARED),0);assert s.intents()[ta].unresolved and '"shared": "5+1/32"'in out    # 4 planned tasks + merge
    s.fake.finish(tasks[3]['id'],elapsed=60);must(s.raw('val',s.d('c'),*SHARED),0,f'intent {ta} resolved (terminal')
    # a REQUEUED latest attempt or a live squeue line keeps an intent unresolved (pure evaluation)
    it=ledger.Intent(t);it.ledger={'token':t,'array':None,'reservation_su':8.0}
    nm=f'c8d3-val-{"c"*12}-{t}'
    for lines,rows,want in (([],[S('70','REQUEUED',nm,'2026-10-04T09:00:00')],None),([U('70','RUNNING',nm)],[S('70','COMPLETED',nm,'2026-10-04T09:00:00')],None),
                            ([],[S('70','NODE_FAIL',nm,'2026-10-04T08:00:00'),S('70','COMPLETED',nm,'2026-10-04T09:00:00')],'terminal')):
        ev=budget.Evaluation(budget.Snapshot([],budget.parse_user('\n'.join(lines)),budget.parse_sacct('\n'.join(rows),'u'),[]),{t:it})
        assert ev.evidence(it)[0]==want,(lines,rows)
    # nothing resolves on age with both sources empty for T, with or without a submit record; its slot stays
    s=Site(td,'o3');s.ours(3);must(s.raw('val',s.d('a'),*COMPUTE),0);t=s.records('intent')[-1]['token'];jid=s.records('submit')[-1]['job_id']
    st=s.fake._mem;st['jobs']=[x for x in st['jobs']if x['id']!=jid];s.h.advance(G+86400)
    must(s.raw('val',s.d('b'),*COMPUTE),65,'"nodes": "4+1/4"');assert s.intents()[t].unresolved
    # a requeued worker whose charge exceeds its intent: one count per token, at the larger value
    s=Site(td,'o4');must(s.raw('val',s.d('a'),*COMPUTE),0);jid=s.records('submit')[-1]['job_id'];s.fake.requeue(jid,elapsed=1800,start_new=True)
    assert abs(s.budget()['lines']['dev']['total']-(128*0.5+128))<1e-6
    # a %8-throttled array cancelled with tasks pending: finished task rows plus one collapsed CANCELLED row resolve it
    s=Site(td,'o5');must(s.submit(s.d('a'),['0:0-19%8']),0);ta=s.records('intent')[0]['token'];base=s.records('submit')[0]['job_id']
    run=[j for j in s.fake.jobs()if j['task']is not None and j['state']=='RUNNING']
    for j in run[:6]:s.fake.finish(j['id'],elapsed=300)
    s.fake.main('scancel',[base],{});s.h.advance(400)
    view=s.fake.main('sacct',['-X','--duplicates','-u','zzheng8','-s','CA,CD','-P','-n','-o','JobID,State','-S','2026-01-01T00:00:00'],{'TZ':'America/Los_Angeles'})[1]
    assert re.search(re.escape(base)+r'_\[\d+-19%8\]\|CANCELLED',view),view
    must(s.raw('val',s.d('b'),*SHARED),0,f'intent {ta} resolved (terminal')
    # manual closing: a recorded job whose sacct record never arrives keeps its slots at every age although it was seen
    for name,args,share in (('node',COMPUTE,'nodes'),('debug',DEBUG,'debug')):
        s=Site(td,'o6'+name);s.ours(3)
        if name=='debug':s.others(1,partition='debug')
        must(s.raw('val',s.d('a'),*args),0);t=s.records('intent')[-1]['token'];jid=s.records('submit')[-1]['job_id'];dl=decision_log(s)
        s.fake.set(jid,sacct_hold=True);s.fake.finish(jid,elapsed=60);s.h.advance(400+86400+G)
        must(s.raw('val',s.d('b'),*args),65,share)
        must(s.ledger_cmd(['resolve',t,'--user-decision','PLAN-REVIEW-LOG.md:1','--decision-log',dl[-1]]),64)
        must(s.ledger_cmd(['resolve',t,*dl]),0);must(s.raw('val',s.d('b'),*args),0)
    s=Site(td,'o6live');must(s.raw('val',s.d('a'),*SHARED8),0);t=s.records('intent')[-1]['token'];s.h.advance(G+1)
    must(s.ledger_cmd(['resolve',t,*decision_log(s)]),69,'live job');assert s.intents()[t].unresolved
    s=Site(td,'o6early');must(s.raw('val',s.d('a'),*SHARED8),0);t=s.records('intent')[-1]['token'];jid=s.records('submit')[-1]['job_id']
    st=s.fake._mem;st['jobs']=[x for x in st['jobs']if x['id']!=jid];must(s.ledger_cmd(['resolve',t,*decision_log(s)]),64,'acts only from G')
    # an array's 20 planned shared slots are held although the array was seen
    s=Site(td,'o6arr');s.ours(11,partition='shared',role='x');must(s.submit(s.d('a'),['0:0-19%8']),0);ta=s.records('intent')[0]['token'];base=s.records('submit')[0]['job_id']
    for j in [j for j in s.fake.jobs()if j['task']is not None]:s.fake.set(j['id'],sacct_hold=True)
    s.fake.main('scancel',[base],{});s.h.advance(400+G+1)
    must(s.raw('val',s.d('b'),*SHARED),65,'shared');must(s.ledger_cmd(['resolve',ta,*decision_log(s)]),0);must(s.raw('val',s.d('b'),*SHARED),0)
    # never eligible: a superseded afterany merge, a call's merge cancelled on a violation, an afterok merge cancelled by scancel
    s=Site(td,'o7');d=s.d('c');must(s.lanes(1,d),0);m0=jobs_named(s,'-merge-')[0]['id'];tm0=[r for r in s.records('intent')if r['role']=='merge'][0]['token']
    must(s.lanes(1,d),0,'superseded pending merge');view_u=s.fake.main('sacct',['-X','--duplicates','-u','zzheng8','-P','-n','-o','JobID,State,Start,ElapsedRaw','-S','2026-01-01T00:00:00'],{'TZ':'America/Los_Angeles'})[1]
    view_s=s.fake.main('sacct',['-X','--duplicates','-u','zzheng8','-s','CA','-P','-n','-o','JobID,State,Start,ElapsedRaw','-S','2026-01-01T00:00:00'],{'TZ':'America/Los_Angeles'})[1]
    assert m0 not in view_u and f'{m0}|CANCELLED by 1234|Unknown|0'in view_s,(view_u,view_s)
    must(s.raw('val',s.d('x'),*SHARED),0,f'intent {tm0} resolved (never_started')
    assert [r for r in s.records('resolution')if r['token']==tm0][0]['charge_su']==0.0
    s=Site(td,'o8');must(s.submit(s.d('a'),['0:0-1']),0);tm=[r for r in s.records('intent')if r['role']=='merge'][0]['token'];mid=jobs_named(s,'-merge-')[0]['id']
    s.fake.set(mid,sacct_hold=True);s.fake.main('scancel',[mid],{})   # cancelled while waiting on afterok; sacct not delivered yet
    must(s.raw('val',s.d('x'),*SHARED),0,f'intent {tm} resolved (never_started')   # from the user snapshot alone
    # control: with the unfiltered query alone (no state-selected query) and the job purged from squeue, the intent stays after G
    s=Site(td,'o9');must(s.submit(s.d('a'),['0:0-1']),0);tm=[r for r in s.records('intent')if r['role']=='merge'][0]['token'];mid=jobs_named(s,'-merge-')[0]['id']
    s.fake.main('scancel',[mid],{});s.h.advance(400+G);real=budget.q_sacct
    budget.q_sacct=lambda env,sel:[]if sel else real(env,sel)
    try:out=must(s.raw('val',s.d('x'),*SHARED),0);assert s.intents()[tm].unresolved and f'intent {tm} resolved'not in out
    finally:budget.q_sacct=real
    must(s.raw('val',s.d('y'),*SHARED),0,f'intent {tm} resolved (never_started')
    # resolve: 0 with never-started evidence, the full reservation without it (a CANCELLED row with a Start)
    s=Site(td,'o10');s.fake.config(hold_new=[True]);must(s.raw('val',s.d('a'),*SHARED8),0);t=s.records('intent')[-1]['token'];jid=s.records('submit')[-1]['job_id']
    s.fake.main('scancel',[jid],{});s.h.advance(G+1)            # cancelled while pending; no admission has recorded it yet
    must(s.ledger_cmd(['resolve',t,*decision_log(s)]),0);assert [r for r in s.records('resolution')if r['token']==t][0]['charge_su']==0.0
    s=Site(td,'o11');must(s.raw('val',s.d('a'),*SHARED8),0);t=s.records('intent')[-1]['token'];jid=s.records('submit')[-1]['job_id']
    s.fake.set(jid,sacct_hold=True);s.fake.main('scancel',[jid],{});s.h.advance(400+G)
    must(s.ledger_cmd(['resolve',t,*decision_log(s)]),0);assert [r for r in s.records('resolution')if r['token']==t][0]['charge_su']==8.0
    # single-task case: a pending task cancelled alone leaves no record; the array keeps its 20 shared slots and its SU until the decision
    s=Site(td,'o12');s.ours(11,partition='shared',role='x');must(s.submit(s.d('a'),['0:0-19%8']),0);ta=s.records('intent')[0]['token'];base=s.records('submit')[0]['job_id']
    s.fake.main('scancel',[f'{base}_15'],{})
    for j in [j for j in s.fake.jobs()if j['task']is not None and j['task']!=15]:
        if j['state']=='PENDING':s.fake.set(j['id'],state='RUNNING',start=s.fake.now()-60)
        s.fake.finish(j['id'],elapsed=60)
    for adv in (G+1,86400):
        s.h.advance(adv);must(s.raw('val',s.d('b'),*SHARED),65,'"shared": "32+1/32"')   # 11 live + the array's 20 planned tasks + its pending merge
        r=s.budget();assert s.intents()[ta].unresolved and r['unresolved_intents'][ta]['reservation_su']>=r['unresolved_intents'][ta]['scheduler_su']
    su=s.budget()['lines']['dev']['total'];must(s.ledger_cmd(['resolve',ta,*decision_log(s)]),0);must(s.raw('val',s.d('b'),*SHARED),0)
    assert abs(s.budget()['lines']['dev']['total']-su-1/12)<1e-9
    ok('o_resolution_on_evidence_dedup_manual_closing_never_eligible_single_task')

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-17 (p) repair never loses an intent; the drill fault points of J-DRL-10 (real processes)
def a_inflight(s):
    s.fake.config(sbatch_rules=[{'name_has':'-lane-','action':'delay'}]);assert s.lanes(1,s.d('a'))[0]==-9
    return [r for r in s.records('intent')if r['role']=='lane'][-1]['token']

def test_p_repair_never_loses_an_intent(td):
    for where in ('token','elsewhere'):
        s=Site(td,'p_'+where);s.ours(3);t=a_inflight(s);L=s.root/'ledger.jsonl';data=bytearray(L.read_bytes())
        line=[(o,l)for o,l in ledger.split_lines(bytes(data))if f'"token":"{t}"'.encode()in l and b'"kind":"intent"'in l][0]
        k=line[0]+(line[1].index(f'"token":"{t}"'.encode())+10 if where=='token'else 30);data[k]=ord('#')if where=='token'else data[k]^1
        L.write_bytes(bytes(data))
        must(s.lanes(1,s.d('b')),69,'interior corruption')
        try:s.budget();raise AssertionError
        except Refuse as e:assert e.code==69
        must(rebuild(s,reason='flipped byte'),0);summ=json.loads(sorted((s.root/'ledger_evidence').glob('rebuild.*.json'))[-1].read_text())
        assert summ['restored_intents']==[t]and summ['segments_matched'][0]['by']=='byte_range'
        for adv in (0,G+1):s.h.advance(adv);must(s.lanes(1,s.d('b')),65,'nodes')
        s.fake.accept();assert s.counts()['nodes']==4;must(s.lanes(1,s.d('b')),65,'nodes')
    # control: r3's rebuild, which dropped the damaged line (and so the intent), admits B and reaches five nodes
    s=Site(td,'p_ctl');s.ours(3);t=a_inflight(s);L=s.root/'ledger.jsonl'
    L.write_bytes(b''.join(l for _,l in ledger.split_lines(L.read_bytes())if f'"token":"{t}"'.encode()not in l));(s.root/'intents'/f'{t}.json').unlink()
    must(s.lanes(1,s.d('b')),0);s.fake.accept();assert s.counts()['nodes']==5
    # missing ledger at the same point: blocked until the user's decision (from G after the block), which restores every intent
    s=Site(td,'p_missing');s.ours(3);t=a_inflight(s);(s.root/'ledger.jsonl').unlink()
    must(s.lanes(1,s.d('b')),69,'missing');must(rebuild(s,reason='x'),69,'missing')
    log=s.dir/'PLAN-REVIEW-LOG.md';log.write_text('- **User decision: rebuild the lost ledger with a 0 SU hold.**\n')
    ud=dict(reason='x',user_decision='PLAN-REVIEW-LOG.md:1',hold_su=0.0,hold_line='dev',decision_log=str(log))
    must(rebuild(s,**ud),64,'no earlier than G');s.h.advance(G+1);must(rebuild(s,**ud),0)
    assert s.intents()[t].unresolved;must(s.lanes(1,s.d('b')),65,'nodes');s.fake.accept();assert s.counts()['nodes']==4
    # both copies lost: rebuild writes nothing but evidence and blocks whatever --reason says; admission and budget stay blocked
    for variant in ('damaged+unreadable','unreadable_token+deleted','merged+deleted','missing+unreadable','missing+deleted_live'):
        s=Site(td,'p_both_'+variant.replace('+','_'));s.ours(3);t=a_inflight(s);L=s.root/'ledger.jsonl';f=s.root/'intents'/f'{t}.json'
        data=L.read_bytes();lines=ledger.split_lines(data);i=[k for k,(o,l) in enumerate(lines)if f'"token":"{t}"'.encode()in l and b'"intent"'in l][0]
        o,l=lines[i];nt=l.replace(t.encode(),b'#'*12)
        if variant=='damaged+unreadable':L.write_bytes(data[:o]+nt+data[o+len(l):]);f.write_bytes(b'garbage')
        elif variant=='unreadable_token+deleted':L.write_bytes(data[:o]+nt+data[o+len(l):]);f.unlink()
        elif variant=='merged+deleted':
            po,pl=lines[i-1];L.write_bytes(data[:po]+pl[:-1]+nt+data[o+len(l):]);f.unlink()
        elif variant=='missing+unreadable':L.unlink();f.write_bytes(b'garbage')
        else:L.unlink();f.unlink();s.fake.accept()
        before=sorted(str(p)for p in s.root.rglob('*')if 'ledger_evidence'not in str(p))
        for reason in ('a','b'):must(rebuild(s,reason=reason),69)
        assert sorted(str(p)for p in s.root.rglob('*')if 'ledger_evidence'not in str(p))==before
        must(s.lanes(1,s.d('b')),69)
        try:s.budget();raise AssertionError(f'budget.py ran with both copies lost ({variant})')
        except Refuse as e:assert e.code==69,(variant,e.code)
        log=s.dir/'PLAN-REVIEW-LOG.md';log.write_text('- **User decision: hold 128 SU for the lost intent.**\n')
        must(rebuild(s,reason='x',user_decision='PLAN-REVIEW-LOG.md:1',decision_log=str(log)),64,'go together')
        must(rebuild(s,reason='x',user_decision='PLAN-REVIEW-LOG.md:9',hold_su=1,hold_line='dev',decision_log=str(log)),64)
        ud=dict(reason='x',user_decision='PLAN-REVIEW-LOG.md:1',hold_su=128.0,hold_line='dev',decision_log=str(log))
        must(rebuild(s,**ud),64,'no earlier than G');s.h.advance(G+1);must(rebuild(s,**ud),0)
        h=[r for r in s.records('intent')if r.get('hold')];assert len(h)==1 and h[0]['decision']['sha256']and h[0]['reservation_su']==128.0
    # missing ledger, delayed acceptance: the ledger and A's file are deleted before A's job is accepted; every rebuild blocks
    for fate in ('accepted_finished_purged','never'):
        s=Site(td,'p_mda_'+fate);s.ours(3);t=a_inflight(s);(s.root/'ledger.jsonl').unlink();(s.root/'intents'/f'{t}.json').unlink()
        if fate!='never':
            s.fake.accept();j=[x for x in ours_jobs(s)if x['name'].endswith(t)][0]['id'];s.fake.set(j,sacct_hold=True);s.fake.finish(j,elapsed=60);s.h.advance(400)
        for adv in (0,G+1):s.h.advance(adv);must(rebuild(s,reason='x'),69)
    # a crash between a resolution record and its rename: over-counted, then completed once
    s=Site(td,'p_crash');must(s.raw('val',s.d('a'),*SHARED8),0);t=s.records('intent')[-1]['token'];s.fake.finish(s.records('submit')[-1]['job_id'],elapsed=60)
    s.h.kill['rename']=1;assert s.raw('val',s.d('b'),*SHARED)[0]==-9
    assert any(r['token']==t for r in s.records('resolution'))and (s.root/'intents'/f'{t}.json').exists()
    assert s.budget()['unresolved_intents'][t]['reservation_su']==8.0
    must(s.raw('val',s.d('b'),*SHARED),0,f'completed the interrupted resolution of intent {t}')
    out=must(s.raw('val',s.d('c'),*SHARED),0);assert 'interrupted'not in out and (s.root/'intents'/'resolved'/f'{t}.json').exists()
    # an unreadable intent file with a valid ledger copy: counted and reported, no block; rebuild re-writes the file
    s=Site(td,'p_unreadable');s.ours(3);t=a_inflight(s);f=s.root/'intents'/f'{t}.json';f.write_bytes(b'xx')
    must(s.lanes(1,s.d('b')),65,'counted from its ledger copy','nodes');must(rebuild(s,reason='rewrite'),0)
    assert ledger.read_intent_file(f)[0]['token']==t and list((s.root/'ledger_evidence').glob(f'intentfile.*.{t}'))
    ok('p_repair_restores_or_blocks_never_loses_an_intent')

def test_drill_faults(td):
    s=Site(td,'flt')
    for role,args in (('val',SHARED),('drill_x',COMPUTE)):must(s.raw(role,s.d('x'),*args,env={'C8_TEST_FAULT':'kill_after_sbatch'}),64,'C8_TEST_FAULT')
    must(s.raw('drill_x',s.d('x'),*SHARED,env={'C8_TEST_FAULT':'bogus'}),64);assert not s.sbatches()
    p=PSite(td,'flt_real');d=p.root/'evidence'/('e'*12)/'drl10'
    rc,out,err=p.raw('drill_kill',d,'--nodes=1','-A','yun124','-p','shared','-c','1','--mem=1G','-t','00:05:00','--wrap','date; hostname; sleep 60',env={'C8_TEST_FAULT':'kill_after_sbatch'})
    assert rc==-9 and len(p.sbatches())==1,(rc,err)
    rc,out,err=p.raw('drill_after',d,'--nodes=1','-A','yun124','-p','shared','-c','1','--mem=1G','-t','00:05:00','--wrap','date');assert rc==0,err
    assert 'adopted'in out and 'dir None'in out and not d.exists()
    t0=time.time();rc,out,err=p.raw('drill_tmo',d,'--nodes=1','-A','yun124','-p','shared','-c','1','--mem=1G','-t','00:05:00','--wrap','date',env={'C8_TEST_FAULT':'kill_during_launch'})
    assert rc==-9 and 4.5<time.time()-t0<30 and len(p.sbatches())==2,(rc,err)
    for _ in range(400):
        if any(e['event']=='fake:timeout_kill'for e in p.events_list()):break
        time.sleep(0.02)
    assert any(e['event']=='fake:timeout_kill'for e in p.events_list()),'the stand-in was not ended by the KILL of the timeout shim'
    led=ledger.Ledger(ledger.Settings({'C8_SITE':'fake','C8_ROOT':str(p.root)}));led.read(writer=False);its=ledger.intent_state(led)
    tmo=[r for r in led.records if r['kind']=='intent'and r['role']=='drill_tmo'][0]['token'];assert its[tmo].unresolved and not any(r['kind']=='not_submitted'for r in led.records)
    ok('drill_fault_points_kill_after_sbatch_and_kill_during_launch_real_processes')

# ----------------------------------------------------------------------------------------------------------------
# A-ORC-17 (c) concurrent submitters and (i) registration concurrent with submission: seeded interleavings
class Controller:
    """Cooperative scheduler over the tools' hook points: one participant thread runs at a time; a seeded RNG (or a
    policy) picks the next; per-participant kills; delayed acceptances of in-flight sbatch requests at random steps;
    the invariants are checked whenever every participant is paused."""
    def __init__(self,seed,site,check,policy=None,p_accept=0.25):
        self.rng=random.Random(seed);self.cv=threading.Condition();self.waiting={};self.done=set();self.active=None;self.parts={}
        self.site=site;self.check=check;self.policy=policy;self.p_accept=p_accept;self.kill={};self.violations=[];self.last={}
    def point(self,name,info):
        tid=threading.get_ident()
        if tid not in self.parts:return
        with self.cv:
            self.waiting[tid]=name;self.last[tid]=name;self.active=None;self.cv.notify_all()
            while self.active!=tid:self.cv.wait()
            del self.waiting[tid]
        if self.kill.get(self.parts[tid])==name:raise Killed(name)
    def run(self,fns):
        def body(label,fn):
            tid=threading.get_ident()
            with self.cv:self.parts[tid]=label
            try:self.point('start',{});fn()
            except (Killed,InflightKill):pass
            finally:
                with self.cv:self.done.add(tid);self.active=None;self.cv.notify_all()
        ths=[threading.Thread(target=body,args=(l,f),daemon=True)for l,f in fns]
        for t in ths:t.start()
        n=len(fns);steps=0
        while True:
            with self.cv:
                self.cv.wait_for(lambda:len(self.parts)==n and self.active is None and len(self.waiting)+len(self.done)==n,timeout=60)
                assert self.active is None and len(self.waiting)+len(self.done)==n,'interleaving stalled'
                self.violations+=self.check()
                if len(self.done)==n:break
                if self.site.fake._mem['inflight']and self.rng.random()<self.p_accept:self.site.fake.accept(1);self.violations+=self.check()
                ws=sorted(self.waiting,key=lambda t:self.parts[t])
                self.active=self.policy(ws,self)if self.policy else self.rng.choice(ws);self.cv.notify_all()
            steps+=1;assert steps<5000
        for t in ths:t.join()
        self.site.fake.accept();self.violations+=self.check()
        return steps

PHASE={p:i for i,p in enumerate(['start']+POINTS)}
def both_snapshot_first(ws,c):return min(ws,key=lambda t:(PHASE.get(c.last.get(t),99),c.parts[t]))   # every participant passes the rules before any submits

def lock_overlap(log)->bool:
    holder=None
    for e in log:
        if e['event']=='lock_acquired'and not e.get('disabled'):
            if holder is not None:return True
            holder=e['tid']
        elif e['event']=='lock_released'and not e.get('disabled'):holder=None
    return False

SCENARIOS={
    'nodes':(lambda s:s.ours(3),{},{'nodes':4,'normal':11,'account':32,'shared':32}),
    'normal':(lambda s:s.ours(10),{'C8_COMPUTE_CAP':'32','C8_RESERVATION':WIDE(32)},{'normal':11,'account':32,'shared':32}),
    'account':(lambda s:s.others(31),{},{'account':32,'nodes':4,'shared':32}),
    'shared':(lambda s:s.ours(31,partition='shared',role='x'),{},{'shared':32,'nodes':4}),
    'su':(lambda s:s.spent(2490),{'C8_COMPUTE_CAP':'8','C8_RESERVATION':WIDE(8)},{'su':2500.0,'nodes':8,'shared':32}),   # the site's sub-cap (S2-004)
    'reg':(lambda s:s.ours(1),{},{'nodes':4,'normal':11,'account':32,'shared':32}),     # (i): `lanes 2` is admitted (1 + 2 nodes of 4)
}
ARR_COMPUTE='-A yun124 -p compute --mem=240G -t 01:00:00'   # work.sh adds --nodes=1 --ntasks=1
def participants(s,kinds,rng):
    out=[];shared_kind='raw_shared8'
    for i,k in enumerate(kinds):
        d=s.d(f'p{i}_{hx()}',plan=True);env=dict(s.env)
        if k=='lanes':fn=lambda d=d,env=env:driver.main(['lanes','1','--dir',str(d)],env)
        elif k=='lanes2':fn=lambda d=d,env=env:driver.main(['lanes','2','--dir',str(d)],env)
        elif k=='raw_compute':fn=lambda d=d,env=env:ss.main(['raw','--role','val','--dir',str(d),'--',*COMPUTE],env)
        elif k=='raw_shared8':fn=lambda d=d,env=env:ss.main(['raw','--role','val','--dir',str(d),'--',*SHARED8],env)
        elif k=='submit_compute':
            env['C8_SBATCH_ARGS']=ARR_COMPUTE;fn=lambda d=d,env=env:driver.main(['submit','--dir',str(d),'--window','0:0-0'],env)
        elif k=='register':
            env.update(SLURM_JOB_ID=str(4000+i),SLURM_JOB_NAME=f'c8d3-plan-{ledger.dir_sha12(d)}-{hx()}',SLURM_RESTART_COUNT='0')
            fn=lambda d=d,env=env:ledger.main(['register',str(d),'--role','plan'],env)
        out.append((f'{i}:{k}',fn,d))
    return out

def interleave(td,scen,seed,kinds=None,switches=(),policy=None,faults=True):
    rng=random.Random(seed);setup,env,lim=SCENARIOS[scen]
    s=Site(td,f'il_{scen}_{seed}_{"".join(switches)}',**env);setup(s);s.h.switches.update(switches)
    pool={'nodes':['lanes','raw_compute','submit_compute'],'normal':['lanes','raw_compute','submit_compute'],'account':['lanes','raw_compute','submit_compute'],
          'shared':['lanes','raw_shared8'],'su':['raw_shared8'],'reg':['lanes2']}[scen]
    kinds=kinds or[rng.choice(pool)for _ in range(rng.choice((2,3)))]
    ps=participants(s,kinds,rng)
    def check():
        c=s.fake.counts();return [(k,c[k],v)for k,v in lim.items()if (c['su']if k=='su'else c[k])>v+1e-9]
    ctl=Controller(seed,s,check,policy=policy);s.h.on_point=ctl.point;s.h.poll=0.0   # the scheduler yields at every lock poll
    if faults:
        for label,_,d in ps:
            f=rng.random()
            if f<0.2:ctl.kill[label]='after_sbatch'
            elif f<0.4:s.fake.config(sbatch_rules=s.fake.state()['config']['sbatch_rules']+[{'name_has':ledger.dir_sha12(d),'action':'delay'}])
    o,e=io.StringIO(),io.StringIO()
    with contextlib.redirect_stdout(o),contextlib.redirect_stderr(e):ctl.run([(l,f)for l,f,_ in ps])
    s.h.on_point=None
    return ctl.violations,lock_overlap(s.log),s

def test_c_concurrent_submitters(td):
    n=60 if QUICK else 500;scen=list(SCENARIOS);bad=[];t0=time.time()
    for seed in range(n):
        v,ov,s=interleave(td,scen[seed%len(scen)],seed)
        if v or ov:bad.append((seed,v,ov))
        shutil.rmtree(s.dir,ignore_errors=True)
    assert not bad,bad[:5]
    # control: the lock disabled; the same schedules plus a fixed one (both snapshot before either submits) exceed a share
    hits=[]
    for seed in range(40 if QUICK else 100):
        v,ov,s=interleave(td,scen[seed%len(scen)],seed,switches=('no_lock',),faults=False)
        if v:hits.append(seed)
        shutil.rmtree(s.dir,ignore_errors=True)
    v,ov,s=interleave(td,'nodes',7,kinds=['lanes','raw_compute'],switches=('no_lock',),policy=both_snapshot_first,faults=False)
    assert v and ('nodes',5,4)in v,v
    ok('c_concurrent_submitters_seeded_interleavings_never_exceed_shares_or_line',interleavings=n,control_violations=len(hits)+1,seconds=round(time.time()-t0,1))

def test_i_registration_concurrent(td):
    n=60 if QUICK else 500;bad=[]
    for seed in range(n):
        v,ov,s=interleave(td,'reg',10000+seed,kinds=['lanes2','register'],faults=False)
        recs=s.records();regs=[r for r in recs if r['kind']=='register'];subs=[r for r in recs if r['kind']=='submit']
        admitted=sorted(r['role']for r in subs)==['lane','lane','merge']and len(s.sbatches())==3   # `lanes 2` admitted: 2 workers + merge
        if v or ov or len(regs)!=1 or not admitted or ledger.Scan((s.root/'ledger.jsonl').read_bytes()).status!='clean':bad.append((seed,v,ov,len(regs),admitted))
        shutil.rmtree(s.dir,ignore_errors=True)
    assert not bad,bad[:5]
    ok('i_registration_concurrent_with_lanes_2_waits_for_the_lock',interleavings=n)

def test_h_requeue_last_attempt_lags(td):
    """HD17 "Charges" and (a) per attempt: a recorded job requeued anyway (attempt 1 NODE_FAIL after 3000 s), attempt 2 runs
    3000 s and ends while sacct holds back attempt 2 only. budget.py charges both attempts; admission does not resolve the
    intent on attempt 1's row while squeue still shows attempt 2 without its row; delivered, it resolves at both."""
    s=Site(td,'h_rq');must(s.raw('val',s.d('a'),*COMPUTE),0);t=s.records('intent')[-1]['token'];j=s.records('submit')[-1]['job_id']
    s.h.advance(3000);s.fake.requeue(j,elapsed=3000);s.fake.set(j,hold_start=False)   # attempt 1: NODE_FAIL after 3000 s; attempt 2 starts
    s.h.advance(3000);s.fake.finish(j,elapsed=3000);s.fake.set(j,sacct_hold_current=True)
    true=2*128*3000/3600
    r=s.budget();assert abs(r['lines']['dev']['total']-true)<0.02 and t not in r['resolved_by_evidence_now'],(r['lines'],true)
    must(s.raw('val',s.d('b'),*SHARED),0);assert not[x for x in s.records('resolution')if x['token']==t],'resolved on the older attempt'
    assert abs(s.budget()['lines']['dev']['total']-true-1/12)<0.02
    s.fake.set(j,sacct_hold_current=False);must(s.raw('val',s.d('c'),*SHARED),0)
    res=[x for x in s.records('resolution')if x['token']==t];assert len(res)==1 and res[0]['rule']=='terminal'and abs(res[0]['charge_su']-true)<0.02,res
    ok('h_requeued_job_last_attempt_lagging_in_sacct_charged_and_not_resolved_early')

def test_c_needs_no_other_attempt_restart_count(td):
    """HD17 (c) "no other attempt" from the user snapshot alone, and "Charges" for attempts sacct lacks. Slurm may requeue
    a job despite --no-requeue; while sacct lags on it, squeue's RestartCnt is the only record that an earlier attempt
    ran. A pending-cancelled line resolves never-started from squeue alone only with RestartCnt 0 and its submit time
    equal to its eligible time (or no eligible time); a line with RestartCnt > 0 rules (c) out whatever sacct shows;
    each earlier attempt that RestartCnt shows and sacct lacks is charged its full reservation, live job or not."""
    ct='billing=460800,cpu=128,mem=240G,node=1';C=lambda ev:round(ev.lines()['dev']['total'],6)
    def ev1(lines,s_u=(),s_s=()):
        tok=lines[0].split('|')[6][-12:];it=ledger.Intent(tok);it.ledger={'token':tok,'reservation_su':128.0,'line':'dev','slots':{'normal_run':1},'array':None}
        snap=budget.Snapshot([],budget.parse_user('\n'.join(lines)),budget.parse_sacct('\n'.join(s_u),'u'),budget.parse_sacct('\n'.join(s_s),'s'))
        return budget.Evaluation(snap,{tok:it}),it
    def cancelled(n,**k):return U('980','CANCELLED',n,part='compute',tres=ct,start='N/A',used='0:00',submit='2026-10-04T10:00:00',**k)
    n=NM('val')
    for kw,want in (({},'never_started'),({'eligible':'N/A'},'never_started'),            # a dependency never satisfied: RestartCnt alone
                    ({'restarts':'1','eligible':'2026-10-04T10:02:01'},None),              # requeued: the reviewer's case
                    ({'restarts':'1'},None),({'restarts':'2','eligible':'N/A'},None),      # RestartCnt alone rules it out
                    ({'eligible':'2026-10-04T10:02:01'},None),                             # a submit time other than the eligible time
                    ({'restarts':''},None),({'restarts':'N/A'},None)):                     # no count printed: sacct decides
        ev,it=ev1([cancelled(n,**kw)]);assert ev.evidence(it)[0]==want,(kw,ev.evidence(it))
    # requeued (attempt 1 ran 3000 s, NODE_FAIL), attempt 2 cancelled while pending, sacct lagging on the whole job: unresolved,
    # and charged one full reservation for attempt 1 (not 0); the intent's floor is the same 128
    ev,it=ev1([cancelled(n,restarts='1',eligible='2026-10-04T10:02:01')]);assert ev.evidence(it)[0]is None and C(ev)==128.0,C(ev)
    a1=S('980','NODE_FAIL',n,'2026-10-04T09:00:00',start='2026-10-04T09:00:05',el='3000',alloc=ct,part='compute',tl='01:00:00')
    a2=S('980','CANCELLED',n,'2026-10-04T10:00:00',start='None',el='0',alloc='',req=ct,part='compute',tl='01:00:00')
    # the state-selected sacct lists attempt 2 only (attempt 1 still RUNNING there): RestartCnt still rules (c) out
    ev,it=ev1([cancelled(n,restarts='1',eligible='2026-10-04T10:02:01')],s_s=[a2]);assert ev.evidence(it)[0]is None and C(ev)==128.0,C(ev)
    ev,it=ev1([cancelled(n)],s_s=[a2]);assert ev.evidence(it)[0]=='never_started'                       # control: no restart
    ev,it=ev1([cancelled(n,restarts='1',eligible='2026-10-04T10:02:01')],s_u=[a1,a2])                    # delivered: terminal at the truth
    rule,charge,_=ev.evidence(it);assert rule=='terminal'and abs(charge-128*3000/3600)<1e-9,(rule,charge)
    # charges: a live requeued job (attempt 2 running) whose attempt 1 sacct lacks, or shows live still: its full reservation
    r=NM('val');live=U('981','RUNNING',r,part='compute',tres=ct,restarts='1',submit='2026-10-04T10:00:00',eligible='2026-10-04T10:02:01')
    assert C(ev_of([live],[]))==256.0 and C(ev_of([live],[S('981','RUNNING',r,'2026-10-04T09:00:00',el='3000',alloc=ct,part='compute')]))==256.0
    assert C(ev_of([live],[S('981','NODE_FAIL',r,'2026-10-04T09:00:00',el='3000',alloc=ct,part='compute',tl='01:00:00')]))==round(128+128*3000/3600,6)
    assert C(ev_of([U('981','RUNNING',r,part='compute',tres=ct)],[]))==128.0                          # control: RestartCnt 0
    # a finished third attempt (RestartCnt 2) with one earlier row delivered: its elapsed time plus one missing attempt
    f=U('982','COMPLETED',r,part='compute',tres=ct,start='2026-10-04T11:00:00',used='50:00',restarts='2',submit='2026-10-04T10:58:00',eligible='2026-10-04T11:00:00')
    one=S('982','NODE_FAIL',r,'2026-10-04T09:00:00',start='2026-10-04T09:00:05',el='600',alloc=ct,part='compute',tl='01:00:00')
    assert C(ev_of([f],[one]))==round(128*600/3600+128*3000/3600+128,6)
    # (a) waits while an earlier attempt is missing: the third attempt's row alone is not terminal evidence
    third=S('982','COMPLETED',r,'2026-10-04T10:58:00',start='2026-10-04T11:00:00',el='3000',alloc=ct,part='compute',tl='01:00:00')
    tok=r[-12:];it=ledger.Intent(tok);it.ledger={'token':tok,'reservation_su':128.0,'line':'dev','slots':{'normal_run':1},'array':None}
    ev=budget.Evaluation(budget.Snapshot([],budget.parse_user(f),budget.parse_sacct(one+'\n'+third,'u'),[]),{tok:it});assert ev.evidence(it)[0]is None
    two=S('982','NODE_FAIL',r,'2026-10-04T10:00:00',start='2026-10-04T10:00:05',el='600',alloc=ct,part='compute',tl='01:00:00')
    ev=budget.Evaluation(budget.Snapshot([],budget.parse_user(f),budget.parse_sacct('\n'.join([one,two,third]),'u'),[]),{tok:it})
    rule,charge,_=ev.evidence(it);assert rule=='terminal'and abs(charge-128*(600+600+3000)/3600)<1e-9,(rule,charge)
    # the stateful fake: the reviewer's two reproducers (probe_c_requeued_cancel_sacct_lag, probe_requeue_live_lag)
    def truth(s):return s.fake.counts()['su']
    s=Site(td,'c_rq',C8_COMPUTE_CAP='8',C8_RESERVATION=WIDE(8));s.spent(2500-128-100)   # the gate binds at this site's sub-cap (S2-004)
    must(s.raw('val',s.d('a'),*COMPUTE),0);t=s.records('intent')[-1]['token'];j=s.records('submit')[-1]['job_id']
    s.h.advance(3000);s.fake.requeue(j,elapsed=3000);s.fake.set(j,sacct_hold=True);s.fake.main('scancel',[j],{})
    line=s.fake.main('squeue',['--all','-u','zzheng8','-h','-r','--states=all','-O',budget.USER_FMT],{})[1]
    q=[x for x in budget.parse_user(line)if x.jobid==j][0];assert q.state=='CANCELLED'and q.restarts==1 and q.start=='N/A'and q.submit!=q.eligible,line
    r=s.budget();assert t not in r['resolved_by_evidence_now']and r['lines']['dev']['total']>=truth(s)-1e-6,(r['lines']['dev'],truth(s))
    must(s.raw('val',s.d('b'),*COMPUTE),65,'refused by the SU gate');assert not[x for x in s.records('resolution')if x['token']==t]
    assert truth(s)<=2500                                                                   # the gate held the line
    s.fake.deliver(j);must(s.raw('val',s.d('c'),*SHARED),0,f'intent {t} resolved (terminal')
    res=[x for x in s.records('resolution')if x['token']==t];assert len(res)==1 and abs(res[0]['charge_su']-128*3000/3600)<0.02,res
    assert abs(s.budget()['lines']['dev']['total']-truth(s))<0.02
    s=Site(td,'rq_live',C8_COMPUTE_CAP='8',C8_RESERVATION=WIDE(8));s.spent(2500-128-128-50)
    must(s.raw('val',s.d('a'),*COMPUTE),0);j=s.records('submit')[-1]['job_id']
    s.h.advance(3000);s.fake.set(j,sacct_hold=True);s.fake.requeue(j,elapsed=3000,start_new=True)
    assert s.budget()['lines']['dev']['total']>=truth(s)-1e-6
    must(s.raw('val',s.d('b'),*COMPUTE),65,'refused by the SU gate');assert truth(s)<=2500
    ok('c_needs_restart_count_0_and_unchanged_submit_missing_attempts_charged_in_full')

def test_launch_wrapper_not_started(td):
    """HD17 (b): when the launch wrapper `timeout` cannot be started at all (missing from PATH, not executable, a failed
    fork), no process ran and no sbatch can exist: `not_submitted` with `launched: false`, T resolved at zero cost, exit 69.
    An OSError after the wrapper started stays ambiguous. budget._run raises NotStarted only for a start failure."""
    with tempfile.TemporaryDirectory(prefix='nostart_')as d:   # the runner itself, with real processes
        d=Path(d);x=d/'noexec';x.write_text('#!/bin/sh\necho hi\n');x.chmod(0o644)
        for argv in ([str(d/'missing')],[str(x)]):
            try:budget._run(argv,dict(os.environ),5);raise AssertionError(argv)
            except budget.NotStarted as e:assert isinstance(e,OSError)and e.errno in(errno.ENOENT,errno.EACCES),e
        cp=budget._run([sys.executable,'-c','import sys;print("ok");sys.exit(3)'],dict(os.environ),10);assert (cp.returncode,cp.stdout)==(3,'ok\n')
        try:budget._run([sys.executable,'-c','import time;time.sleep(30)'],dict(os.environ),0.3);raise AssertionError('no timeout')
        except subprocess.TimeoutExpired:pass
    # real processes: `timeout` missing from PATH, then present without its exec bit
    s=PSite(td,'nostart');fb=install(td/'fakebin_nostart');(fb/'timeout').unlink()
    for case in ('missing','noexec'):
        if case=='noexec':(fb/'timeout').write_text('#!/bin/sh\nexec "$@"\n');(fb/'timeout').chmod(0o644)
        rc,out,err=s.raw('val',s.d(case),*SHARED,env={'PATH':str(fb)})
        assert rc==69 and 'could not be started'in err and 'resolved at zero cost'in err and 'Traceback'not in err,(case,rc,err[-800:])
        led=ledger.Ledger(ledger.Settings({'C8_SITE':'fake','C8_ROOT':str(s.root)}));led.read(writer=False)
        t=[r for r in led.records if r['kind']=='intent'][-1]['token'];ns=[r for r in led.records if r['kind']=='not_submitted'and r['token']==t]
        assert len(ns)==1 and ns[0]['launched']is False and ns[0]['ambiguous']is False and ns[0]['exit_status']is None,ns
        assert (s.root/'intents'/'resolved'/f'{t}.json').exists()and not (s.root/'intents'/f'{t}.json').exists()
        assert not ledger.intent_state(led)[t].unresolved and not s.sbatches()
    # in process: a failed fork (EAGAIN) is NotStarted; an OSError after the start (control) stays ambiguous
    for exc,launched in ((budget.NotStarted(errno.EAGAIN,'cannot start timeout: Resource temporarily unavailable'),False),(OSError(errno.EIO,'Input/output error'),True)):
        s=Site(td,f'nostart_inproc_{launched}')
        def arm(name,info,exc=exc):
            if name=='launch':
                real=budget.RUNNER
                def boom(argv,env,tmo):
                    if argv[0]=='timeout':raise exc
                    return real(argv,env,tmo)
                budget.RUNNER=boom
        s.h.on_point=arm
        try:rc,out,err=s.raw('val',s.d('a'),*SHARED)
        finally:s.h.on_point=None
        assert rc==69,(rc,err[-600:]);t=s.records('intent')[-1]['token'];ns=[r for r in s.records('not_submitted')if r['token']==t]
        assert len(ns)==1 and ns[0]['launched']is launched and ns[0]['ambiguous']is launched,ns
        assert s.intents()[t].unresolved is launched and not s.sbatches()
        r=s.budget();assert abs(r['lines']['dev']['intents']-(1/12 if launched else 0.0))<1e-9,r['lines']['dev']
    ok('launch_wrapper_not_started_is_launched_false_resolved_at_zero_after_start_ambiguous')

def test_reader_race(td):
    """D.12: a reader without the lock (budget.py, `ledger.py check`) never refuses a valid state because a submitter wrote
    an intent between its reads: the files are scanned before the ledger is read, so a file seen has its ledger copy."""
    # 'sacct_state_selected' lies between the ledger read and the intent evaluation in every version of budget.py
    for point in ('reader_files_listed','reader_ledger_read','sacct_state_selected'):
        for variant in ('partial_file','failed_write_resolved'):
            s=Site(td,f'rr_{point}_{variant}');led_box={}
            def step(name,info,point=point,variant=variant):
                if name!=point or led_box:return
                led_box['t']=1;st=ledger.Settings(s.env);led=ledger.Ledger(st);tok=led.new_token();c=hx()
                p=ledger.payload('intent',[tok],token=tok,name=f'c8d3-val-{c}-{tok}',comment=f'c8d3:{c}:{"0"*12}:{tok}',role='val',c=c,p='0'*12,dir='/x',
                                 partition='shared',nodes=1,cpus=1,mem_mib=1024.0,time_s=3600,array=None,task_count=1,billing=1.0,reservation_su=1.0,
                                 slots={'shared':1},line='dev',pid=1,mono=0.0,command='racer')
                led.append(p);st.intents.mkdir(exist_ok=True);st.resolved.mkdir(exist_ok=True)
                part=ledger.frame(p)[:20]                                    # the submitter's intent file, still being written
                if variant=='partial_file':(st.intents/f'{tok}.json').write_bytes(part)
                else:
                    led.append(ss.not_submitted(tok,False,False,'intent file write failed'));(st.resolved/f'{tok}.json').write_bytes(part)
                led_box['tok']=tok
            s.h.on_point=step
            try:r=s.budget()
            finally:s.h.on_point=None
            assert led_box.get('tok'),point;exp=1.0 if(point=='reader_files_listed'and variant=='partial_file')else 0.0
            assert abs(r['lines']['dev']['intents']-exp)<1e-9,(point,variant,r['lines']['dev'])
            led_box.clear();s.h.on_point=step
            try:rc,out,err=s.ledger_cmd(['check'])
            finally:s.h.on_point=None
            assert rc==0,(point,variant,err)
    ok('readers_scan_intent_files_before_the_ledger_no_false_repair_alarm')

def test_exec_guard_preflight(td):
    """A missing or non-executable exec guard refuses (64) before any intent; coreutils timeout's own failure to run the
    guard (125/126/127, `timeout: failed to run command`) is `launched: false`, never an ambiguous submission."""
    s=Site(td,'guard');saved=ss.EXEC_GUARD;g=s.dir/'exec_guard.sh';g.write_bytes(saved.read_bytes());g.chmod(0o644)
    try:
        for path in (g,s.dir/'missing.sh'):
            ss.EXEC_GUARD=path
            must(s.raw('val',s.d('x'),*SHARED),64,'exec guard');must(s.lanes(1,s.d('c')),64,'exec guard')
            assert not s.records('intent')and not list((s.root/'intents').glob('*.json'))and not s.sbatches()
        must(s.call(ss.main,['raw','--role','val','--dir',str(s.d('x')),'--dry-run','--',*SHARED]),0)   # a dry run launches nothing
    finally:ss.EXEC_GUARD=saved
    for rc,err in ((126,"timeout: failed to run command '/x/slurm/exec_guard.sh': Permission denied\n"),(127,"timeout: failed to run command '/x/exec_guard.sh': No such file or directory\n"),
                   (125,'timeout: failed to run command \'x\': Resource temporarily unavailable\n')):
        jid,launched,amb,why=ss.classify(rc,'',err);assert jid is None and launched is False and amb is False,(rc,why)
    assert ss.classify(127,'','sbatch: error: something else')[2]is True                                  # anything else stays ambiguous
    # the fake `timeout` shim behaves as coreutils when its command cannot be run
    fb=install(td/'fakebin_guard');cp=subprocess.run([str(fb/'timeout'),'-s','KILL','5',str(g),'99','true'],capture_output=True,text=True)
    assert cp.returncode==126 and ss.classify(cp.returncode,cp.stdout,cp.stderr)[1:3]==(False,False),(cp.returncode,cp.stderr)
    ok('exec_guard_preflight_64_nothing_written_timeout_failure_not_ambiguous')

def test_docs_hpc(td):
    """docs/HPC.md carries what the plan's G list requires of these tools, the residual race bound included (D.11)."""
    doc=(ROOT/'docs/HPC.md').read_text()
    for need in ('Residual race (stated bound)','k ≤ 11','MaxJobsPA','Δ','60 s','120 s','disjoint','11 / 27','c7_legacy/'):assert need in doc,need
    ok('docs_hpc_states_the_residual_race_bound')

# ----------------------------------------------------------------------------------------------------------------
# symmetry (Amendment A1): C8_SITE=symmetry on the Mac, the fake Slurm in its symmetry mode, the session lock's mount
# check against a fake NFS mount with local_lock=none, symmetry's /home (addendum L; tests/test_ledger.py covers the
# refusals and the lock path on a symmetry host)
SYM_BASE='mode=reservation;id=H7;amd_nodes=4;amd_total=8'
def utc_now(dt=0.0)->str:return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(ledger.now()+dt))
def carry(dev,pilot=0,dt=0.0,production=None)->str:   # A1.3: at most 24 h old; production=None: the old format, without the key
    return f'dev={dev};pilot={pilot};'+(f'production={production};'if production is not None else'')+f'asof={utc_now(dt)};ref=expanse budget.py carry (test)'
AMDJ=['-p','amdq','--mem=240G','-t','01:00:00','--wrap','date']              # 64 core-h
AMDDBG=['-p','amddebugq','--mem=8G','-t','00:30:00','--wrap','date']         # 32 core-h
DEFQ=['-p','defq','--mem=180G','-t','01:00:00','--wrap','date']              # 80 core-h (Intel: Slurm allocates 80 CPUs)
def SYM_SPLIT(n,total=8,until='2036-01-01T00:00:00Z'):return f'mode=reservation;id=H11-sym;amd_nodes={n};amd_total={total};until={until}'

class SymSite(Site):
    def __init__(self,td:Path,name:str,lock_mount='nfs',**env):
        base={'C8_SITE':'symmetry','C8_RESERVATION':SYM_BASE,'C8_COMPUTE_CAP':None,'USER':'zzheng1','C8_OTHER_SITE_SU':carry(450.7),
              'C8_SBATCH_ARGS':'-p amdq','C8_MERGE_SBATCH_ARGS':'-p amdq --mem=240G -t 01:00:00'}
        super().__init__(td,name,**{**base,**env})
        self.fake.config(site='symmetry')
        st=os.stat(self.root);dev=f'{os.major(st.st_dev)}:{os.minor(st.st_dev)}';real=os.path.realpath(self.root)
        line={'nfs':f'593 34 {dev} / {real} rw,relatime shared:211 - nfs 172.16.4.228:/HPCunixhome rw,vers=3,hard,proto=tcp,local_lock=none,addr=172.16.4.228',
              'beegfs':f'1235 34 {dev} / {real} rw,nosuid,relatime shared:526 - beegfs beegfs_nodev rw,cfgFile=/etc/beegfs/beegfs-client.conf'}[lock_mount]
        self.mi=self.dir/'mountinfo';self.mi.write_text(f'22 1 0:21 / / rw - apfs /dev/disk1 rw\n{line}\n')
    def activate(self):
        super().activate();ledger.MOUNTINFO=str(self.mi)
    def ours(self,n=1,role='lane',partition='amdq',state='RUNNING',c=None,**kw)->list:
        out=[]
        for _ in range(n):
            t=hx();cc=c or hx();out+=self.fake.add_job(f'c8d3-{role}-{cc}-{t}',state=state,partition=partition,comment=f'c8d3:{cc}:{"0"*12}:{t}',
                                                      user='zzheng1',account='zzheng1',nodes=1,cpus=kw.pop('cpus',1),**kw)
        return out
    def c8d2(self,n,state='RUNNING',partition='amdq'):
        return [self.fake.add_job(f'c8d2-lane-{hx()}-{hx()}',user='zzheng1',account='zzheng1',partition=partition,state=state)[0]for _ in range(n)]
    def others(self,n,user='zzheng1',partition='amdq',state='RUNNING',name='sri_eng_c8BC_mainB'):
        return [self.fake.add_job(f'{name}{i}',user=user,account=user,partition=partition,state=state)[0]for i in range(n)]
    def spent(self,ch,line='dev'):
        role=budget.LINE_PREFIX.get(line,'')+'val';t=hx();c=hx()   # a finished amdq job of ch core-hours (64 per node-hour)
        return self.fake.add_job(f'c8d3-{role}-{c}-{t}',state='COMPLETED',partition='amdq',user='zzheng1',account='zzheng1',elapsed=int(round(ch/64*3600)),
                                 time_s=int(round(ch/64*3600))+3600,comment=f'c8d3:{c}:{"0"*12}:{t}')[0]

SAVED_SITE=ledger.MOUNTINFO
def restore_site():ledger.MOUNTINFO=SAVED_SITE

PIN='cn079,cn080,cn081,cn082,cn084,cn085,cn087,cn092'   # budget.SYMMETRY.cpu_exclude: the AMD nodes known not to be EPYC 7543 (HD11's CPU pin)
XTOK=f'--exclude=cn112,{PIN}'               # what every symmetry AMD-pool job gets without an --exclude of its own
def test_sym_resolve(td):
    """symmetry's option resolution: the admitted partitions, the refusals (longq, preq, amdpreq, sharedq, Expanse's),
    -A only absent or zzheng1, the ceilings, --exclude=cn112 and the CPU pin's nodes (EPYC 7532: cn079-082, cn084,
    cn085, cn087, cn092; C8_AMD_EXCLUDE_EXTRA) merged into every AMD-pool job, a --nodelist naming any of them refused, whole-node
    billing; Expanse resolves without any exclude token."""
    P=lambda toks:ss.parse_options(toks,'t')[0]
    def R(*cmd,env=None):return ss.resolve([],[],P(list(cmd)),'symmetry',**({}if env is None else{'exclude':ss.amd_exclusions(budget.SYMMETRY,env)}))
    assert ss.amd_exclusions(budget.SYMMETRY,{})==['cn112',*PIN.split(',')]and tuple(budget.SYMMETRY.cpu_exclude)==tuple(PIN.split(','))
    r=R('-p','amdq','--mem=240G','-t','01:00:00');assert (r['billing'],r['unit'],r['capped'],r['site_tokens'])==(64.0,'core-h',True,[XTOK])
    assert R('-p','amdq','--mem=240G','-t','01:00:00',env={})['site_tokens']==[XTOK]   # exclude=None is the package constant alone
    assert ss.spec_slots(r,1)=={'amd_nodes':1}and ss.spec_slots(r,3)=={'amd_nodes':3}
    r=R('-p','amddebugq','-c','8','--mem=8G','-t','00:30:00');assert r['billing']==64.0 and r['site_tokens']==[XTOK]
    r=R('-p','defq','--mem=180G','-t','24:00:00');assert (r['billing'],r['capped'],r['site_tokens'])==(80.0,False,[])and ss.spec_slots(r,1)=={}
    r=R('-p','debugq','--exclusive','-c','40','--mem=16G','-t','00:59:00');assert r['billing']==80.0 and r['exclusive']and r['site_tokens']==[]
    assert R('-p','defq','--mem=1G','-t','5',env={'C8_AMD_EXCLUDE_EXTRA':'cn083'})['site_tokens']==[]   # Intel: outside the pin
    # negative control: every Expanse partition resolves without a site token (byte for byte as before the pin)
    for part,extra in (('compute',['--exclusive']),('shared',['-c','4']),('debug',['-c','4'])):
        r=ss.resolve([],[],P(['-A','yun124','-p',part,'--nodes=1',*extra,'--mem=8G','-t','00:10:00']),'expanse');assert r['site_tokens']==[],(part,r)
        assert ss.resolve([],[],P(['-A','yun124','-p',part,'--nodes=1',*extra,'--mem=8G','-t','00:10:00']),'expanse',exclude=ss.amd_exclusions(budget.EXPANSE,{}))['site_tokens']==[]
    assert R('-p','amdq','-x','cn100','--mem=1G','-t','5')['site_tokens']==[f'--exclude=cn100,cn112,{PIN}']
    tok=R('-p','amdq','--exclude=cn[079-087]','--mem=1G','-t','5')['site_tokens'];assert tok==['--exclude=cn[079-087],cn112,cn092'],tok   # pin nodes inside the range are not repeated
    assert R('-p','amdq','--exclude=cn112,cn090','--mem=1G','-t','5')['site_tokens']==[f'--exclude=cn112,cn090,{PIN}']
    assert R('-p','amdq','--mem=1G','-t','5',env={'C8_AMD_EXCLUDE_EXTRA':'cn083,cn086,cn085'})['site_tokens']==[f'{XTOK},cn083,cn086']
    assert R('-p','amdq','--mem=1G','-t','5',env={'C8_AMD_EXCLUDE_EXTRA':''})['site_tokens']==[XTOK]
    for node in ('cn085','cn[084-086]'):
        for opt in (f'--nodelist={node}',):
            try:R('-p','amdq',opt,'--mem=1G','-t','5');raise AssertionError(f'not refused: {opt}')
            except Refuse as e:assert e.code==64 and 'not AMD EPYC 7543'in str(e)and 'remove it from --nodelist'in str(e),str(e)
    try:R('-p','amddebugq','-w','cn[084-086]','--mem=1G','-t','5');raise AssertionError('not refused: -w cn[084-086]')
    except Refuse as e:assert e.code==64 and 'cn084 is not AMD EPYC 7543'in str(e),str(e)
    try:R('-p','amdq','--nodelist=cn083','--mem=1G','-t','5',env={'C8_AMD_EXCLUDE_EXTRA':'cn083'});raise AssertionError('extra node not refused in --nodelist')
    except Refuse as e:assert e.code==64 and 'cn083 is not AMD EPYC 7543'in str(e),str(e)
    assert R('-p','amdq','--nodelist=cn100','--mem=1G','-t','5')['site_tokens']==[XTOK]   # a 7543 node may be named
    try:R('-p','amdq','--nodelist=cn112','--mem=1G','-t','5');raise AssertionError('cn112 in --nodelist accepted')
    except Refuse as e:assert e.code==64 and 'AVX-512'in str(e)and 'not AMD EPYC 7543'not in str(e),str(e)   # cn112 keeps its own text
    for bad in ('cn83','cn083;x','cn083,,cn086','CN083',' cn083','exp-1-07','cn083,','cn0833'):
        try:ss.amd_exclusions(budget.SYMMETRY,{'C8_AMD_EXCLUDE_EXTRA':bad});raise AssertionError(f'not refused: {bad!r}')
        except Refuse as e:assert e.code==64 and 'C8_AMD_EXCLUDE_EXTRA'in str(e)and 'cnNNN'in str(e),(bad,str(e))
    for site in (budget.EXPANSE,'expanse','fake'):
        try:ss.amd_exclusions(site,{'C8_AMD_EXCLUDE_EXTRA':'cn083'});raise AssertionError('accepted under Expanse')
        except Refuse as e:assert e.code==64 and "applies to symmetry's AMD pool only"in str(e),str(e)
        assert ss.amd_exclusions(site,{})==[]and ss.amd_exclusions(site,{'C8_AMD_EXCLUDE_EXTRA':''})==[]
    assert R('-p','amdq','-A','zzheng1','--mem=1G','-t','5')['account']=='zzheng1'
    assert ss.hostlist_has('cn[079-082,110-112]','cn112')and not ss.hostlist_has('cn[079-082,110-111]','cn112')and not ss.hostlist_has('cn1120','cn112')
    for bad,needle in ((('-p','longq','--mem=1G','-t','5'),'never'),(('-p','preq','--mem=1G','-t','5'),'requeue'),(('-p','amdpreq','--mem=1G','-t','5'),'requeue'),
                       (('-p','sharedq','--mem=1G','-t','5'),'sharedq'),(('-p','compute','--mem=1G','-t','5'),'not allowed'),(('-p','largememq','--mem=1G','-t','5'),'not allowed'),
                       (('-p','amdq,defq','--mem=1G','-t','5'),'one partition'),(('-A','yun124','-p','amdq','--mem=1G','-t','5'),'-A yun124'),
                       (('-p','amdq','--mem=250G','-t','5'),'ceiling'),(('-p','defq','--mem=200G','-t','5'),'ceiling'),(('-p','amdq','--mem=1G','-t','24:00:01'),'limit'),
                       (('-p','amddebugq','--mem=1G','-t','01:00:01'),'limit'),(('-p','amdq','-c','65','--mem=1G','-t','5'),'CPUs'),
                       (('-p','amdq','--nodelist=cn112','--mem=1G','-t','5'),'cn112'),(('-p','amdq','-w','cn[110-112]','--mem=1G','-t','5'),'cn112'),
                       (('-p','amdq','-q','long','--mem=1G','-t','5'),'--qos'),(('-p','amdq','--mem=0','-t','5'),'--mem=0'),(('-p','amdq','-t','5'),'memory')):
        try:R(*bad)
        except Refuse as e:assert e.code==64 and needle in str(e),(bad,str(e))
        else:raise AssertionError(f'not refused: {bad}')
    # the billing of scheduler records (A1.3): a pending exclusive job's tres-alloc is its request (cpu=1, billing=1, as
    # symmetry's squeue printed it on 2026-10-05), priced at the whole node; AllocTRES cpu=64/80 as allocated
    S=budget.SYMMETRY
    for part,tres,want in (('amdq','cpu=1,mem=240G,node=1,billing=1',64),('amdq','cpu=64,mem=240G,node=1,billing=64',64),('defq','billing=80,cpu=80,mem=180G,node=1',80),
                           ('amdq,defq','cpu=1,mem=4G,node=1,billing=1',80),('largememq','cpu=128,mem=370G,node=1,billing=128',128),('unknownq','cpu=1,node=1',128)):
        assert S.tres_billing(part,budget.parse_tres(tres))==want,(part,tres,S.tres_billing(part,budget.parse_tres(tres)))
    line=('569858_34 |569858 |zzheng1 |amdq |normal |RUNNING |sri_eng_c8BC_mainB |1 |64 |240G |23:50:00 |None |(null) |cpu=64,mem=240G,node=1,billing=64 '
          '|2026-10-05T09:19:11 |0:20 |0 |2026-10-04T20:45:31 |2026-10-05T09:19:11 ')
    q=budget.parse_user(line,S)[0];assert (q.jobid,q.base,q.state,q.timelimit,q.restarts,q.task,q.tres['cpu'],q.classes())==('569858_34','569858','RUNNING',85800,0,34,64,{'amd_nodes':1})
    row=budget.parse_sacct('564501|564501|o2-L12-wolfram-smoke|amdq|FAILED|2026-09-28T07:19:11|2026-09-28T07:19:11|11|00:05:00|billing=64,cpu=64,mem=4G,node=1|billing=1,cpu=1,mem=4G,node=1','u')
    c=budget.charges([],row,prof=S);assert len(c)==1 and abs(c[0].su-64*11/3600)<1e-12
    ok('symmetry_option_resolution_partitions_exclude_cn112_and_the_cpu_pin_nodelist_refusals_extra_list_whole_node_core_hours')

def test_sym_admission(td):
    """H7 on symmetry: live c8d3- AMD-pool nodes (amdq + amddebugq + amdpreq, pending included) + intents + k <= 4;
    both sessions <= 8 (c8d2- counted); Intel outside the cap; a pilot re-split (5, total 8) with until; malformed,
    missing and expired reservations; C8_COMPUTE_CAP only lowers the cap; other users' and other sessions' jobs of
    zzheng1 never count."""
    try:
        s=SymSite(td,'sym_sa1');s.ours(3);s.others(8);must(s.raw('val',s.d('x'),*AMDJ),0,'"amd_nodes": "3+1/4"')
        job=[j for j in s.fake.jobs()if j['name'].startswith('c8d3-val-')][0];a=job['argv']
        assert XTOK in a and '--no-requeue'in a and '-A'not in a and job['user']=='zzheng1',a
        must(s.raw('val',s.d('x'),*AMDDBG),65,'"amd_nodes": "4+1/4"','amd_nodes');n=len(s.sbatches())
        must(s.raw('intel_val',s.d('x'),*DEFQ),0,'"amd_nodes": "4+0/4"');assert len(s.sbatches())==n+1   # Intel: outside the cap
        a=[j for j in s.fake.jobs()if j['name'].startswith('c8d3-intel_val-')][0]['argv'];assert not any(x.startswith(('--exclude','-x'))for x in a),a   # control: defq gets no --exclude
        # a refused C8_AMD_EXCLUDE_EXTRA: 64 before the lock, no intent record, no sbatch
        s=SymSite(td,'sym_sax');n=len(s.records('intent'))
        for bad in ('cn83','CN083','cn083,,cn086'):must(s.raw('val',s.d('x'),*AMDJ,env={'C8_AMD_EXCLUDE_EXTRA':bad}),64,'C8_AMD_EXCLUDE_EXTRA')
        must(s.lanes(1,s.d('camp'),env={'C8_AMD_EXCLUDE_EXTRA':'cn83'}),64,'C8_AMD_EXCLUDE_EXTRA')
        assert not s.sbatches()and len(s.records('intent'))==n==0 and not s.history('squeue'),(s.sbatches(),s.records('intent'))
        must(s.raw('val',s.d('x'),*AMDJ,env={'C8_AMD_EXCLUDE_EXTRA':'cn083,cn086'}),0)
        a=[j for j in s.fake.jobs()if j['name'].startswith('c8d3-val-')][0]['argv'];assert f'{XTOK},cn083,cn086'in a,a
        e=Site(td,'sym_sax_exp',C8_OTHER_SITE_SU=carry(0));must(e.raw('val',e.d('x'),*SHARED,env={'C8_AMD_EXCLUDE_EXTRA':'cn083'}),64,"applies to symmetry's AMD pool only")
        assert not e.sbatches()and not e.records('intent')
        s=SymSite(td,'sym_sa2');s.ours(2);s.ours(1,partition='amdpreq');s.ours(1,state='PENDING',partition='amddebugq')
        must(s.raw('val',s.d('x'),*AMDJ),65,'"amd_nodes": "4+1/4"')                                        # all three AMD partitions, pending included
        s=SymSite(td,'sym_sa3');s.ours(3);s.c8d2(4);must(s.raw('val',s.d('x'),*AMDJ),0,'c8d2- AMD-pool nodes 4')  # 4 + 4 = 8
        s=SymSite(td,'sym_sa4');s.ours(3);s.c8d2(5);must(s.raw('val',s.d('x'),*AMDJ),65,'detector','exceed 8');assert not s.sbatches()
        s=SymSite(td,'sym_sa5');s.ours(3);s.c8d2(5,partition='defq');must(s.raw('val',s.d('x'),*AMDJ),0)        # c8d2- Intel jobs do not count
        # lanes N: workers and the merge on amdq count; the largest admissible N
        s=SymSite(td,'sym_sa6');must(s.lanes(3,s.d('camp')),0,'"amd_nodes": "0+4/4"');ws=[j for j in s.fake.jobs()if '-lane-'in j['name']]
        assert len(ws)==3 and all('--exclusive'in j['argv']and XTOK in j['argv']for j in ws)
        mg=[j for j in s.fake.jobs()if '-merge-'in j['name']];assert len(mg)==1 and XTOK in mg[0]['argv'],mg   # the merge carries the token too
        s=SymSite(td,'sym_sa6a');must(s.submit(s.d('arr'),['0:0-1'],env={'C8_SBATCH_ARGS':'-p amdq -c 64 --mem=64G -t 01:00:00'}),0)
        ar=[j for j in s.fake.jobs()if '-off0-'in j['name']];assert ar and all(XTOK in j['argv']for j in ar),[j['argv']for j in ar]   # an array window
        s=SymSite(td,'sym_sa7');must(s.lanes(4,s.d('camp')),65,'Largest admissible N = 3','amd_nodes');assert not s.sbatches()
        s=SymSite(td,'sym_sa8');s.intent(partition='amdq',role='val');s.intent(partition='amdq',role='val');s.ours(1)
        must(s.raw('val',s.d('x'),*AMDJ),0,'"amd_nodes": "3+1/4"');must(s.raw('val',s.d('y'),*AMDJ),65,'"amd_nodes": "4+1/4"')
        # the pilot window (DECISIONS 2026-10-05): 5 for the pilot session, 8 in total; lanes 4 = 4 workers + 1 merge
        s=SymSite(td,'sym_sp1',C8_RESERVATION=SYM_SPLIT(5));s.c8d2(3);must(s.lanes(4,s.d('camp')),0,'"amd_nodes": "0+5/5"')
        s=SymSite(td,'sym_sp2',C8_RESERVATION=SYM_SPLIT(5));s.c8d2(4);must(s.lanes(4,s.d('camp')),65,'detector')
        s=SymSite(td,'sym_sp3',C8_RESERVATION=SYM_SPLIT(3));s.ours(3);must(s.raw('val',s.d('x'),*AMDJ),65,'"amd_nodes": "3+1/3"')   # the other session's 3
        s=SymSite(td,'sym_sp4',C8_RESERVATION=SYM_SPLIT(5,until='2026-10-01T00:00:00Z'));must(s.raw('val',s.d('x'),*AMDJ),65,'expired');must(s.raw('intel_val',s.d('y'),*DEFQ),0)
        s=SymSite(td,'sym_sp5',C8_RESERVATION=SYM_SPLIT(5),C8_COMPUTE_CAP='8');s.ours(5);must(s.raw('val',s.d('x'),*AMDJ),65,'"amd_nodes": "5+1/5"')
        s=SymSite(td,'sym_sp6',C8_COMPUTE_CAP='2');s.ours(2);must(s.raw('val',s.d('x'),*AMDJ),65,'"amd_nodes": "2+1/2"')
        # the production window (DECISIONS 2026-10-06, C8(2) production): the other session 9, this one 3, 12 in total, dated;
        # undated or above 12 is malformed (64); after `until` the total falls back to the base 8
        s=SymSite(td,'sym_pw1',C8_RESERVATION=SYM_SPLIT(3,total=12));s.c8d2(9);must(s.raw('val',s.d('x'),*AMDJ),0,'"amd_nodes": "0+1/3"')
        s=SymSite(td,'sym_pw2',C8_RESERVATION=SYM_SPLIT(3,total=12));s.c8d2(9);s.ours(3);must(s.raw('val',s.d('x'),*AMDJ),65,'"amd_nodes": "3+1/3"')
        s=SymSite(td,'sym_pw3',C8_RESERVATION=SYM_SPLIT(3,total=12,until='2026-10-01T00:00:00Z'));s.c8d2(9);must(s.raw('val',s.d('x'),*AMDJ),65,'expired')
        for bad in ('mode=reservation;id=H11-prod;amd_nodes=3;amd_total=12','mode=reservation;id=H11-prod;amd_nodes=3;amd_total=13;until=2036-01-01T00:00:00Z'):
            s=SymSite(td,f'sym_pw{hx()}',C8_RESERVATION=bad);must(s.raw('val',s.d('x'),*AMDJ),64,'AMD-pool')
        for bad in ('mode=reservation;id=H7;amd_nodes=4;amd_total=9','mode=reservation;id=H7;amd_nodes=5;amd_total=8','mode=reservation;id=X;amd_nodes=6;amd_total=5;until=2036-01-01T00:00:00Z',
                    'mode=reservation;id=H7E-R;run=11;sub=27;acct_run=32;shared=32;dev_nodes=4','mode=reservation;id=H7;amd_nodes=4','mode=turn'):
            s=SymSite(td,f'sym_m{hx()}',C8_RESERVATION=bad);must(s.raw('val',s.d('x'),*AMDJ),64,'AMD-pool');must(s.raw('intel_val',s.d('y'),*DEFQ),0)
        for none in ('mode=none',None):
            s=SymSite(td,f'sym_n{hx()}',C8_RESERVATION=none);must(s.raw('val',s.d('x'),*AMDJ),65,'no AMD-pool job');must(s.raw('intel_val',s.d('y'),*DEFQ),0)
        # the snapshots name zzheng1 (-u for both squeue snapshots; no -A) and sacct -u zzheng1
        s=SymSite(td,'sym_sq');calls=[];real=budget.RUNNER
        def spy(argv,env,t):calls.append(list(argv));return real(argv,env,t)
        s.activate();budget.RUNNER=spy
        try:budget.Snapshot.take(s.env,account=True)
        finally:budget.RUNNER=real
        sq=[c for c in calls if c[0]=='squeue'];sa=[c for c in calls if c[0]=='sacct']
        assert len(sq)==2 and all(c[c.index('-u')+1]=='zzheng1'and '-A'not in c for c in sq)and all(c[c.index('-u')+1]=='zzheng1'for c in sa),calls
        # Slurm 21.08 selects no row by state without an end time: the state-selected query carries -E now (Expanse's does not)
        assert len(sa)==2 and '-s'not in sa[0]and '-E'not in sa[0]and sa[1][sa[1].index('-s')+2:sa[1].index('-s')+4]==['-E','now'],sa
        exp=Site(td,'sym_sq_exp');calls.clear();exp.activate();budget.RUNNER=spy
        try:budget.Snapshot.take(exp.env,account=True)
        finally:budget.RUNNER=real
        assert all('-E'not in c for c in calls if c[0]=='sacct')and [c for c in calls if c[0]=='squeue'][0][2:4]==['-A','yun124'],calls
        s.activate()
        # drills: amddebugq/debugq; C8_TEST_FAULT honoured there only
        s=SymSite(td,'sym_sd');must(s.raw('drill_x',s.d('x'),*AMDDBG,'--dependency=afterany:12'),0);must(s.raw('drill_y',s.d('y'),*AMDJ,'--dependency=afterany:12'),64,'drill_')
        must(s.raw('drill_z',s.d('z'),*AMDJ,env={'C8_TEST_FAULT':'kill_after_sbatch'}),64,'amddebugq or debugq')
    finally:restore_site()
    ok('symmetry_admission_h7_amd_pool_cap_pilot_resplit_c8d2_total_intel_outside')

def test_sym_su_line(td):
    """A1.3: symmetry core-hours and the other site's SU (C8_OTHER_SITE_SU, required on symmetry) in one dev line under
    the 4,000 ask and the 5,000 cap; records name the site and unit; budget.py reports the carry."""
    try:
        s=SymSite(td,'sym_su0',C8_OTHER_SITE_SU=None);must(s.raw('val',s.d('x'),*AMDJ),64,'C8_OTHER_SITE_SU is required')
        try:s.budget();raise AssertionError('budget.py ran without the carry')
        except Refuse as e:assert e.code==64
        for bad in ('dev=1;pilot=0;asof=2026-10-05T15:00:00Z','dev=x;pilot=0;asof=2026-10-05T15:00:00Z;ref=r','dev=nan;pilot=0;asof=2026-10-05T15:00:00Z;ref=r',
                    'dev=1;pilot=-1;asof=2026-10-05T15:00:00Z;ref=r','dev=1;pilot=0;asof=yesterday;ref=r','dev=1;pilot=0;asof=2026-10-05T15:00:00Z;ref= ',
                    'dev=1;pilot=0;asof=2026-10-05T15:00:00Z;ref=r;extra=1','dev=1;dev=2;pilot=0;asof=2026-10-05T15:00:00Z;ref=r'):
            must(s.raw('val',s.d('x'),*AMDJ,env={'C8_OTHER_SITE_SU':bad}),64,'C8_OTHER_SITE_SU')
        assert not s.sbatches()
        s=SymSite(td,'sym_su1',C8_OTHER_SITE_SU=carry(3910));s.spent(32)
        must(s.raw('val',s.d('x'),*AMDJ),65,'4006.00','above 4000','other site 3910.00')                       # 3910 + 32 + 64
        assert 32+64<=4000 and 3910+32<=4000                                                                    # neither part alone would refuse
        must(s.raw('val',s.d('x'),*AMDJ,env={'C8_SU_APPROVED':'PLAN-REVIEW-LOG.md:1 (test)'}),0,'projected 4006.00','core-h on symmetry','64.00 core-h reserved')
        sub=s.records('submit')[-1];it=s.records('intent')[-1]
        assert (sub['site'],sub['unit'],it['site'],it['unit'],sub['reservation_su'],it['billing'])==('symmetry','core-h','symmetry','core-h',64.0,64.0)and sub['other_site']==carry(3910)
        s=SymSite(td,'sym_su2',C8_OTHER_SITE_SU=carry(4950));must(s.raw('val',s.d('x'),*AMDJ,env={'C8_SU_APPROVED':'ok'}),65,'5014.00','above its cap 5000')
        must(s.raw('val',s.d('x'),*AMDDBG,env={'C8_SU_APPROVED':'ok'}),0,'projected 4982.00')                   # amddebugq: 64 x 0.5 h
        s=SymSite(td,'sym_su3',C8_OTHER_SITE_SU=carry(100,pilot=250),C8_BUDGET_LINE='pilot',C8_PILOT_SU_CAP='300')
        must(s.raw('val',s.d('x'),*AMDJ),65,'pilot line would reach 314.00');must(s.raw('val',s.d('x'),*AMDDBG),0,'projected 282.00')
        assert s.records('submit')[-1]['role']=='pilot_val'
        s=SymSite(td,'sym_su4',C8_OTHER_SITE_SU=carry(1000.5,pilot=7));s.spent(64);j=s.ours(1,partition='defq',time_s=7200)[0]
        r=s.budget();L=r['lines']
        assert (r['site'],r['unit'])==('symmetry','core-h')and L['dev']['other_site']==1000.5 and L['pilot']['other_site']==7.0
        assert round(L['dev']['spent'],6)==64.0 and round(L['dev']['live'],6)==160.0 and round(L['dev']['total'],6)==round(1000.5+64+160,6),L   # defq: 80/h x 2 h
        s.fake.finish(j,elapsed=1800);L=s.budget()['lines'];assert round(L['dev']['spent'],6)==round(64+40,6),L
        assert round(L['dev']['own'],6)==round(64+40,6)and round(L['pilot']['own'],6)==0.0   # own: without the carry (the value the other site carries)
        rc,out,err=s.call(lambda a,e:budget.main(a,e),[]);assert rc==0 and 'other site'in out and 'core-h'in out and ' own 'in out,out
        cl=[l for l in out.splitlines()if 'C8_OTHER_SITE_SU="'in l];assert len(cl)==1 and 'dev=104.00;pilot=0.00;production=0.00;asof='in cl[0]and 'ref=symmetry tools/budget.py own totals'in cl[0],out
        r=s.budget();assert r['carry'].startswith('dev=104.00;pilot=0.00;production=0.00;asof=')and budget.other_site({'C8_OTHER_SITE_SU':r['carry']})['dev']==104.0   # the carry line parses
        # the age bound (A1.3): at most 24 h old, not in the future (10 min skew); zeros are an explicit carry
        for dt,code,needle in ((-24*3600-60,64,'h old'),(-23*3600,0,''),(3600,64,'in the future'),(300,0,'')):
            got=s.raw('val',s.d('x'),*AMDDBG,env={'C8_OTHER_SITE_SU':carry(1,dt=dt)});must(got,code,*([needle]if needle else[]))
        try:s.budget({'C8_OTHER_SITE_SU':carry(1,dt=-25*3600)});raise AssertionError('budget.py took a stale carry')
        except Refuse as x:assert x.code==64 and 'h old'in str(x),x
        # Expanse (C8_SITE=expanse, read here without the lock): the carry is required there too; explicit zeros allowed
        e=Site(td,'sym_su5',C8_SITE='expanse');e.spent(10)
        try:e.budget();raise AssertionError('budget.py ran on expanse without the carry')
        except Refuse as x:assert x.code==64 and 'required on expanse'in str(x)and "symmetry's `tools/budget.py`"in str(x),x
        n=len(e.sbatches());must(e.raw('val',e.d('x'),*SHARED),64,'C8_OTHER_SITE_SU is required on expanse');assert len(e.sbatches())==n and not e.history('squeue')
        r=e.budget({'C8_OTHER_SITE_SU':carry(0)});assert r['lines']['dev']['other_site']==0.0 and round(r['lines']['dev']['own'],6)==10.0 and r['site']=='expanse'
        assert round(e.budget({'C8_OTHER_SITE_SU':carry(25)})['lines']['dev']['total'],6)==35.0
        # the 3,990 + 8 case of the review: an Expanse line at 3,990 with symmetry's 100 core-h carried refuses an 8-SU job (ask at 4,000)
        e2=Site(td,'sym_su6',C8_SITE='expanse');e2.spent(3990);L=e2.budget({'C8_OTHER_SITE_SU':carry(100)})['lines']
        assert round(L['dev']['own'],6)==3990.0 and round(L['dev']['total'],6)==4090.0 and budget.gate('dev',L['dev']['total']+8,e2.env)and not budget.gate('dev',L['dev']['own']+8,e2.env),L
        # the fakes (C8_SITE=fake, Expanse's emulation on the Mac): optional, 0 when unset
        f=Site(td,'sym_su7');f.spent(10);assert f.budget()['lines']['dev']['other_site']==0.0
    finally:restore_site()
    ok('symmetry_core_hours_and_the_other_sites_su_in_one_line_records_name_site_and_unit_carry_required_on_both_sites_at_most_24h_old')

def test_sym_carry_asof(td):
    """A1 repair round 2: budget.py reads without the lock, so an admission whose intent is appended after its ledger
    read (and whose job is accepted after its sacct) is missing from `own`. The carry's asof is therefore stamped at the
    reader's FIRST read (the intent-file scan): the missed intent is always later than asof, which the refresh rule
    covers, and the next carry holds it (the review's fake repro: an amdq intent of 1,504 core-h at reader_ledger_read)."""
    try:
        s=SymSite(td,'sym_ca');s.spent(32);box={}
        def step(name,info):
            if name!='reader_ledger_read'or box:return
            s.h.advance(5.0)   # the submitter's admission (under the lock) runs after the reader's ledger read
            box['t']=s.intent(partition='amdq',role='val',su=1504.0);box['utc']=s.intents()[box['t']].utc   # 64 x 23.5 h
        s.h.on_point=step
        try:r=s.budget()
        finally:s.h.on_point=None
        assert box.get('t')
        own0=r['lines']['dev']['own'];asof=budget.other_site({'C8_OTHER_SITE_SU':r['carry']})['asof']
        assert round(own0,6)==32.0 and asof<=r['carry_asof_utc']<box['utc'],(own0,r['carry'],r['carry_asof_utc'],box)   # missed, and later than asof
        r2=s.budget();asof2=budget.other_site({'C8_OTHER_SITE_SU':r2['carry']})['asof']
        assert round(r2['lines']['dev']['own'],6)==1536.0 and r2['carry'].startswith('dev=1536.00;')and box['utc']<r2['carry_asof_utc']and asof2>=int(box['utc']),(r2['carry'],box)
    finally:restore_site()
    ok('carry_asof_is_the_readers_first_read_an_intent_appended_after_the_ledger_read_is_later_than_asof_and_in_the_next_carry')

def test_sym_vendor(td):
    """Repair round 1 of A1: Intel defq/debugq (AVX-512 like cn112) admit raw jobs only under intel_* and drill_* roles
    (validation, gates, replays, builds, plans elsewhere: the AMD AVX2 pool); a campaign's merge must be on its
    workers' CPU vendor (lanes N, lanes 0 with live Intel workers, array windows); the default symmetry merge takes the
    AMD node's 64 cores (-c 64, merge.sh's --jobs), and every c8_profile branch of profiles.sh sets its own merge."""
    DBGI=['-p','debugq','--mem=8G','-t','00:30:00','--wrap','date']
    try:
        s=SymSite(td,'sym_v1')
        for role in ('val','e0sym','replay','flag_check','plan','build','merge_check','in1build'):must(s.raw(role,s.d('x'),*DEFQ),64,'AVX-512','intel_')
        must(s.raw('val',s.d('x'),*DBGI),64,'AVX-512');must(s.raw('val',s.d('x'),*DEFQ,env={'C8_BUDGET_LINE':'pilot','C8_PILOT_SU_CAP':'1300'}),64,'AVX-512')
        assert not s.sbatches()
        must(s.raw('intel_sweep',s.d('x'),*DEFQ),0);must(s.raw('drill_q',s.d('y'),*DBGI),0);must(s.raw('val',s.d('z'),*AMDJ),0);must(s.raw('val',s.d('w'),*AMDDBG),0)
        assert [j['name'].split('-')[1]for j in s.fake.jobs()if j['name'].startswith('c8d3-')]==['intel_sweep','drill_q','val','val']
        # the merge's vendor: an Intel campaign with an AMD merge, and the reverse, are refused (64, nothing submitted); matching pairs pass
        s=SymSite(td,'sym_v2',C8_SBATCH_ARGS='-p defq',C8_LANE_MEM='180G')
        must(s.lanes(1,s.d('ci')),64,'different CPU vendors','one vendor per campaign');assert not s.sbatches()
        must(s.lanes(1,s.d('ci'),env={'C8_MERGE_SBATCH_ARGS':'-p defq -c 40 --mem=180G -t 01:00:00'}),0,'"amd_nodes": "0+0/4"')
        must(s.lanes(1,s.d('ca'),env={'C8_SBATCH_ARGS':'-p amdq','C8_LANE_MEM':'240G','C8_MERGE_SBATCH_ARGS':'-p defq -c 40 --mem=180G -t 01:00:00'}),64,'different CPU vendors')
        # lanes 0 (a merge alone) on a campaign whose live workers are Intel: an AMD merge is refused
        s.ours(1,role='lane',partition='defq',c=ledger.dir_sha12(s.d('cj')))
        must(s.lanes(0,s.d('cj'),env={'C8_SBATCH_ARGS':'-p amdq','C8_LANE_MEM':'240G'}),64,'different CPU vendors','defq')
        must(s.submit(s.d('arr'),['0:0-1'],env={'C8_SBATCH_ARGS':'-p defq -c 40 --mem=64G -t 01:00:00'}),64,'different CPU vendors','array windows')
        # the default merge spec on symmetry: a whole amdq node with -c 64
        P=lambda toks:ss.parse_options(toks,'t',positional=False,allow=ss.CAMPAIGN_ALLOW)[0]
        r=ss.resolve([],[],P(shlex.split(budget.SYMMETRY.merge_args)),'symmetry');assert r['cpus']==64 and r['billing']==64.0 and r['partition']=='amdq',r
        # profiles.sh: every branch sets its own merge (no merge leaks from a previous profile)
        sh=ROOT/'slurm/sites/symmetry/profiles.sh'
        out=subprocess.run(['bash','-c',f'source {shlex.quote(str(sh))};for p in intel lanes debug-intel debug intel debug;do c8_profile $p;echo "$p|$C8_SBATCH_ARGS|$C8_MERGE_SBATCH_ARGS";done'],
                           capture_output=True,text=True,check=True).stdout.split('\n')[:-1]
        for line in out:
            p,w,m=line.split('|');wp=shlex.split(w)[shlex.split(w).index('-p')+1];mp=shlex.split(m)[shlex.split(m).index('-p')+1];mt=shlex.split(m)
            assert budget.pool(budget.SYMMETRY,wp)==budget.pool(budget.SYMMETRY,mp)and int(mt[mt.index('-c')+1])>4,line
            r=ss.resolve([],[],P(mt),'symmetry');assert r['cpus']==(64 if mp=='amdq'else 40),line
    finally:restore_site()
    ok('symmetry_intel_admits_only_intel_and_drill_roles_merges_on_the_workers_vendor_merge_takes_the_node')

def test_sym_lock_refused(td):
    """A session lock on symmetry's BeeGFS (tuneUseGlobalFileLocks = 0: flock() on the local node only) stops every
    admission at the lock (69): no snapshot, no intent, no sbatch; budget.py (no lock) still reads. The lock belongs on
    the NFS home (addendum L)."""
    try:
        s=SymSite(td,'sym_sl',lock_mount='beegfs');must(s.raw('val',s.d('x'),*AMDJ),69,'tuneUseGlobalFileLocks = 0')
        must(s.call(ss.main,['raw','--role','val','--dir',str(s.d('x')),'--dry-run','--',*AMDJ]),69,'this node only')
        assert not s.history('squeue')and not s.history('sbatch')and not s.records('intent')
        must(s.lanes(1,s.d('camp')),69,'local_lock=none');assert not s.history('sbatch')
    finally:restore_site()
    ok('symmetry_admission_refused_at_the_lock_when_it_is_on_beegfs')

# ----------------------------------------------------------------------------------------------------------------
# Stage 6, group A: S2-001 (the vendor rule's pure parts), S2-003, S2-004, S2-006
def test_vendor_rule(td):
    """S2-001 (pure parts; tests/lanes_tests.py test_vendor_pin runs the entry points): the vendor of a partition (symmetry
    amd/intel by pool, Expanse amd); an admission's new jobs and the campaign's live jobs on one vendor and that the pin's:
    a resubmit whose merge (amdq) waits on live Intel elements, or new amdq jobs of an intel-pinned campaign, refuse (64);
    pin_vendor writes the record once under the lock (O_EXCL) and refuses another vendor."""
    class Q:
        def __init__(self,part,jid):self.partition=part;self.jobid=jid
    S=budget.SYMMETRY;P=lambda toks:ss.parse_options(toks,'t',positional=False,allow=ss.CAMPAIGN_ALLOW)[0]
    def spec(part,kind='merge'):return ss.JobSpec(role=kind,cdir=td,resolved=ss.resolve([],[],P(['-p',part,'--mem=8G','-t','01:00:00']),'symmetry'),kind=kind)
    assert [ss.campaign_vendor(S,p)for p in ('amdq','amddebugq','defq','debugq','amdpreq')]==['amd','amd','intel','intel','unknown']
    assert {ss.campaign_vendor(budget.EXPANSE,p)for p in ('compute','shared','debug')}=={'amd'}
    d=td/'vrule';d.mkdir()
    assert ss.vendor_check(S,d,[spec('amdq')],[Q('amdq','1_0')])=='amd'and ss.vendor_check(S,d,[spec('defq','array')],[])=='intel'
    for specs,live in (([spec('amdq')],[Q('defq','1_3')]),([spec('amdq','array'),spec('defq')],[])):   # the resubmit case: a merge on live Intel elements
        try:ss.vendor_check(S,d,specs,live);raise AssertionError('mixed vendors admitted')
        except Refuse as e:assert e.code==64 and 'several CPU vendors'in str(e)and 'S2-001'in str(e),str(e)
    class L:
        def __init__(self):self.n=0
        def check(self,what):self.n+=1
    lk=L();s=Site(td,'vrule_site');s.activate()
    doc=ss.pin_vendor(d,'intel',S,'resubmit',lk,'m'*64);assert lk.n==1 and json.loads((d/ss.VENDOR_PIN).read_text())==doc and doc['vendor']=='intel'
    assert ss.pin_vendor(d,'intel',S,'lanes 1',lk)==doc and lk.n==1   # an existing pin is read, not rewritten
    for bad in (lambda:ss.pin_vendor(d,'amd',S,'lanes 1',lk),lambda:ss.vendor_check(S,d,[spec('amdq')],[])):
        try:bad();raise AssertionError('another vendor admitted')
        except Refuse as e:assert e.code==64 and 'pinned to CPU vendor intel'in str(e),str(e)
    ok('vendor_rule_one_vendor_per_admission_live_jobs_included_pin_written_once')

def test_time_minutes(td):
    """S2-003: Slurm reserves whole minutes, so a --time with a seconds part is normalized up to the minute before the
    partition check, the pricing and the intent, and submitted as that value (a --time token after the user's); a
    whole-minute request is submitted as given; elapsed times stay unrounded. The finding's case: a joint dev total of
    4,999.90 and a one-node compute job of 1 s, priced at one minute (2.13 SU), is refused; at 1 s (0.0356 SU) it passed."""
    P=lambda toks:ss.parse_options(toks,'t')[0]
    def R(t,part='compute'):return ss.resolve([],[],P(['-A','yun124','-p',part,'--nodes=1','--mem=8G','-t',t]+(['--exclusive']if part=='compute'else[])),None)
    for tv,want,tok in (('00:00:01',60,['--time=00:01:00']),('0:30',60,['--time=00:01:00']),('5:30',360,['--time=00:06:00']),('1:00:00',3600,[]),('90',5400,[]),
                        ('1-00:00:01',86460,['--time=1-00:01:00']),('47:59:01',172800,['--time=2-00:00:00'])):
        r=R(tv);assert (r['time_s'],r['site_tokens'])==(want,tok),(tv,r['time_s'],r['site_tokens'])
    for tv,part in (('00:30:01','debug'),('2-00:00:01','compute')):
        try:R(tv,part);raise AssertionError(f'{tv} over the {part} limit admitted')
        except Refuse as e:assert e.code==64 and 'limit'in str(e)
    assert R('00:29:30','debug')['time_s']==1800 and budget.parse_duration('00:00:01')==1 and budget.parse_squeue_duration('0:01')==1   # elapsed parsing unrounded
    e={'C8_SU_APPROVED':'PLAN-REVIEW-LOG.md:1 (test)'}
    s=Site(td,'tmin',C8_OTHER_SITE_SU=carry(4999.90))
    must(s.raw('val',s.d('x'),'-A','yun124','-p','compute','--exclusive','--nodes=1','--mem=240G','-t','00:00:01','--wrap','date',env=e),65,'5002.03','above its cap 5000')
    assert not s.sbatches()
    must(s.raw('val',s.d('x'),'-A','yun124','-p','shared','--nodes=1','-c','1','--mem=1G','-t','00:00:30','--wrap','date',env={**e,'C8_OTHER_SITE_SU':carry(10)}),0)
    it=s.records('intent')[-1];sub=s.records('submit')[-1];sb=s.sbatches()[-1]['argv']
    assert it['time_s']==sub['time_s']==60 and abs(it['reservation_su']-1/60)<1e-12,(it['time_s'],it['reservation_su'])
    assert sb[sb.index('-t')+1]=='00:00:30'and [a for a in sb if a.startswith('--time=')]==['--time=00:01:00']and sb.index('--time=00:01:00')>sb.index('-t'),sb   # the last value wins
    must(s.raw('val',s.d('y'),*SHARED,env={**e,'C8_OTHER_SITE_SU':carry(10)}),0);assert not [a for a in s.sbatches()[-1]['argv']if a.startswith('--time=')]   # whole minutes: as given
    ok('time_normalized_up_to_whole_minutes_before_limits_pricing_and_intent_and_submitted')

def test_site_subcaps(td):
    """S2-004 (host decision 2026-10-06): the dev line's 5,000 is split into hard per-site sub-caps of 2,500 each
    (budget.SITE_CAPS, one place, summing to the joint cap), each enforced from the site's own ledger and scheduler with
    no carry; the joint ask (4,000) and cap stay, through C8_OTHER_SITE_SU, labelled soft; the pilot line has no split.
    The finding's race: both sites at 2,400 with fresh carries of each other each admit up to their own 2,500, so the
    joint total stays <= 5,000 whatever the carries say."""
    assert set(budget.SITE_CAPS['dev'])=={'expanse','symmetry'}and abs(sum(budget.SITE_CAPS['dev'].values())-budget.DEV_CAP)<1e-9 and budget.SITE_CAPS['pilot']is None
    assert budget.site_cap('dev',budget.SYMMETRY)==budget.site_cap('dev',budget.EXPANSE)==2500.0 and budget.site_cap('pilot',budget.SYMMETRY)is None
    e={'C8_SU_APPROVED':'PLAN-REVIEW-LOG.md:1 (test)'}
    try:
        s=SymSite(td,'sub_sym',C8_OTHER_SITE_SU=carry(2400));s.spent(2400)
        must(s.raw('val',s.d('x'),*AMDJ,env=e),0,'own 2464.00 of its hard sub-cap 2500')                       # 2,400 + 64
        must(s.raw('val',s.d('y'),*AMDJ,env=e),65,'sub-cap','2528.00','above its hard sub-cap 2500','no carry')   # joint 4,928 would pass
        must(s.raw('val',s.d('y'),*AMDJ,env={**e,'C8_OTHER_SITE_SU':carry(0)}),65,'above its hard sub-cap 2500')   # whatever the carry
        assert len(s.sbatches())==1
        x=Site(td,'sub_exp',C8_OTHER_SITE_SU=carry(2400));x.spent(2400)
        must(x.raw('val',x.d('x'),*SHARED8,env=e),0)                                                            # 2,408
        must(x.raw('val',x.d('y'),*COMPUTE,env=e),65,'expanse would reach 2536.00','above its hard sub-cap 2500');assert len(x.sbatches())==1
        assert 2400+2400+64+64<=5000 and 2400+2400+8+128<=5000   # without the sub-caps the joint (carried) check alone would admit both second jobs
        y=Site(td,'sub_ask',C8_OTHER_SITE_SU=carry(2999));y.spent(1000)                                       # the joint ask stays, soft
        must(y.raw('val',y.d('x'),*SHARED8),65,'4007.00','above 4000','soft check');must(y.raw('val',y.d('x'),*SHARED8,env=e),0)
        z=Site(td,'sub_pil',C8_BUDGET_LINE='pilot',C8_PILOT_SU_CAP='4000',C8_OTHER_SITE_SU=carry(0));z.spent(2600,line='pilot')
        must(z.raw('val',z.d('x'),*SHARED8),0)                                                                  # the pilot line: no split
        r=x.budget();assert r['site_caps']=={'dev':2500.0,'pilot':None,'production':None},r['site_caps']
        rc,out,err=x.call(lambda a,en:budget.main(a,en),[]);assert rc==0 and "hard sub-cap 2500"in out,out
    finally:restore_site()
    ok('per_site_hard_sub_caps_2500_each_sum_to_the_joint_cap_without_the_carry_joint_ask_soft_pilot_unsplit')

PROD={'C8_BUDGET_LINE':'production','C8_PRODUCTION_SU_CAP':'100'}
def test_production_line(td):
    """The production budget line (user decision 2026-10-08), mirroring the pilot line: C8_BUDGET_LINE=production needs
    C8_PRODUCTION_SU_CAP (finite, positive); every role becomes prod_<role> (a caller's prod_ role refused under every line);
    names classify by prefix (dev, pilot_, prod_; an unparseable c8d3- name in every line); admission refuses above the cap;
    budget.py reports the line; the dev and pilot lines are untouched by production jobs and vice versa; the carry gains an
    optional production= key (an old carry parses with production 0; the printed carry includes it); intents, records,
    accounting, production.py's queue parser and ledger rebuild's --hold-line know the line."""
    # classification by name (budget.name_info / line_of / base_role)
    nm=lambda role:f'c8d3-{role}-{"c"*12}-{"d"*12}'
    for role,line,base in (('val','dev','val'),('pilot_lane','pilot','lane'),('prod_lane','production','lane'),('prod_off3','production','off3'),
                           ('product','dev','product'),('production_x','dev','production_x')):
        assert budget.name_info(nm(role))['lines']==(line,)and budget.base_role(role)==base,(role,budget.name_info(nm(role)))
    assert budget.name_info('c8d3-garbled name')['lines']==('dev','pilot','production')
    ev=ev_of([],[S('901','COMPLETED',NM('pilot_val'),'2026-10-04T09:00:00',el='3600'),S('902','COMPLETED',NM('prod_val'),'2026-10-04T09:00:00',el='3600'),
                 S('903','COMPLETED',NM('val'),'2026-10-04T09:00:00',el='3600'),S('904','COMPLETED',NM('prod_lane'),'2026-10-04T09:00:00',el='1800')])
    L=ev.lines();assert (L['dev']['total'],L['pilot']['total'],L['production']['total'])==(8.0,8.0,12.0),{k:v['total']for k,v in L.items()}
    import accounting,production as prod
    assert accounting.role_class('prod_lane')==accounting.role_class('pilot_lane')=='work'and accounting.role_class('prod_merge')=='merge'
    # admission under each line: the role prefix, the intent's and the record's line
    s=Site(td,'prod_adm')
    for env,role,line in (({},'val','dev'),({'C8_BUDGET_LINE':'pilot','C8_PILOT_SU_CAP':'100'},'pilot_val','pilot'),(PROD,'prod_val','production')):
        must(s.raw('val',s.d('x'),*SHARED,env=env),0);sub=s.records('submit')[-1];it=s.records('intent')[-1]
        assert (sub['role'],sub['line'],it['line'])==(role,line,line)and sub['name'].startswith(f'c8d3-{role}-'),(sub['role'],sub['line'],it['line'])
    must(s.lanes(1,s.d('campP'),env=PROD|{'C8_PRODUCTION_SU_CAP':'1000'}),0)
    assert {r['role']for r in s.records('submit')[-2:]}=={'prod_lane','prod_merge'}and {r['line']for r in s.records('submit')[-2:]}=={'production'}
    n0=len(s.sbatches())
    for env in ({},{'C8_BUDGET_LINE':'pilot','C8_PILOT_SU_CAP':'100'},PROD):
        must(s.raw('prod_val',s.d('x'),*SHARED,env=env),64,'prod_ prefix is set by the tool');must(s.raw('pilot_val',s.d('x'),*SHARED,env=env),64,'pilot_ prefix')
    for v in (None,'nan','inf','1e999','0','-5','x'):
        must(s.raw('val',s.d('x'),*SHARED,env={**PROD,'C8_PRODUCTION_SU_CAP':v}),64,'C8_PRODUCTION_SU_CAP')
    must(s.raw('val',s.d('x'),*SHARED,env={'C8_BUDGET_LINE':'prod'}),64,'dev, pilot or production');assert len(s.sbatches())==n0
    # the cap, and isolation: dev and pilot spend do not count in production, production spend not in dev or pilot
    s=Site(td,'prod_cap',**PROD);s.spent(95,line='production');s.spent(2000);s.spent(60,line='pilot')
    must(s.raw('val',s.d('x'),*SHARED8),65,'production line would reach 103.00','above its cap 100');assert not s.sbatches()
    must(s.raw('val',s.d('x'),*MEMJOB),0,'production line','projected 99.00')                              # 95 + 4: dev's 2,000 and pilot's 60 not counted
    b0=s.budget()['lines'];assert (round(b0['dev']['total'],6),round(b0['pilot']['total'],6),round(b0['production']['total'],6))==(2000.0,60.0,99.0),b0
    must(s.raw('val',s.d('x'),*SHARED8,env={'C8_BUDGET_LINE':'pilot','C8_PILOT_SU_CAP':'65'}),65,'pilot line would reach 68.00')   # 60 + 8: production's 99 not in pilot
    must(s.raw('val',s.d('x'),*MEMJOB,env={'C8_BUDGET_LINE':'pilot','C8_PILOT_SU_CAP':'65'}),0,'projected 64.00')
    must(s.raw('val',s.d('x'),*MEMJOB,env={'C8_BUDGET_LINE':'dev'}),0,'projected 2004.00')   # dev: 2,000 + 4, no production or pilot SU
    b1=s.budget()['lines'];assert (round(b1['dev']['total'],6),round(b1['pilot']['total'],6),round(b1['production']['total'],6))==(2004.0,64.0,99.0),b1
    rc,out,err=s.call(lambda a,e:budget.main(a,e),[]);assert rc==0 and re.search(r'^  production +spent +95\.00 ',out,re.M),out
    # an intent of the production line counts in production only
    s2=Site(td,'prod_int',**PROD);s2.intent(partition='shared',su=7.0,line='production');L=s2.budget()['lines']
    assert (L['production']['intents'],L['dev']['intents'],L['pilot']['intents'])==(7.0,0.0,0.0),L
    # the carry: an old carry (no production key) parses with production 0; production= is read; malformed values refused
    try:
        assert budget.other_site({'C8_OTHER_SITE_SU':carry(5,pilot=2)})['production']==0.0
        o=budget.other_site({'C8_OTHER_SITE_SU':carry(5,pilot=2,production=33.5)});assert (o['dev'],o['pilot'],o['production'])==(5.0,2.0,33.5),o
        for bad in ('-1','nan','x',''):
            try:budget.other_site({'C8_OTHER_SITE_SU':carry(5,production=bad)});raise AssertionError(f'production={bad!r} accepted')
            except Refuse as e:assert e.code==64 and 'C8_OTHER_SITE_SU'in str(e),e
        try:budget.other_site({'C8_OTHER_SITE_SU':carry(5,production=1).replace('production=1;','production=1;production=2;')});raise AssertionError('two production keys accepted')
        except Refuse as e:assert e.code==64
        y=SymSite(td,'prod_sym',C8_OTHER_SITE_SU=carry(100,pilot=7,production=900),**PROD|{'C8_PRODUCTION_SU_CAP':'950'})
        must(y.raw('val',y.d('x'),*AMDJ),65,'production line would reach 964.00','other site 900.00')      # 900 carried + 64 (amdq 1 h)
        must(y.raw('val',y.d('x'),*AMDDBG),0,'projected 932.00');assert y.records('submit')[-1]['role']=='prod_val'
        r=y.budget();L=r['lines'];assert (L['production']['other_site'],L['production']['own'],L['dev']['other_site'],L['pilot']['other_site'])==(900.0,32.0,100.0,7.0),L
        assert r['carry'].startswith('dev=0.00;pilot=0.00;production=32.00;asof=')and budget.other_site({'C8_OTHER_SITE_SU':r['carry']})['production']==32.0,r['carry']
        assert r['other_site']['production']==900.0 and r['site_caps']['production']is None
        rc,out,err=y.call(lambda a,e:budget.main(a,e),[]);assert rc==0 and 'production 900.00'in out and 'C8_OTHER_SITE_SU="dev=0.00;pilot=0.00;production=32.00;'in out,out
        z=SymSite(td,'prod_sym_old',C8_OTHER_SITE_SU=carry(100,pilot=7),**PROD|{'C8_PRODUCTION_SU_CAP':'1000'})   # an old carry: admitted, production 0 carried
        must(z.raw('val',z.d('x'),*AMDJ),0,'projected 64.00')
    finally:restore_site()
    # production.py's queue parser (array-mode recovery) and ledger rebuild's hold line
    q=s.root/'runs'/'qp';q.mkdir(parents=True);(q/'manifest.json').write_text('{}\n');c=ledger.dir_sha12(q);p=ledger.plan_sha12(q)
    text='\n'.join(f'{j}|{k}|{st}|c8d3-{r}-{c}-{t}|c8d3:{c}:{p}:{t}'for j,k,st,r,t in (('11_2','2','RUNNING','prod_off5','a'*12),('12','N/A','PENDING','prod_merge','b'*12),
                                                                                    ('13','N/A','RUNNING','prod_lane','e'*12)))+'\n'
    qs=prod.queue_state(q,text);assert qs['refuse']is None and qs['live_indices']==[7]and qs['live_merges']==['12']and qs['live_lanes']==['13'],qs
    for line,why in (('production','go together'),('pilot','go together'),('bogus','invalid choice')):   # argparse takes the line, then cmd_rebuild's pairing rule refuses
        must(s.call(lambda a,e:ledger.main(a,e),['rebuild','--reason','x','--hold-line',line]),64,why)
    ok('production_line_cap_prefix_classification_isolation_old_and_new_carry_intents_records_accounting_queue_parser')

def test_held_release_once(td):
    """S2-006: `release` refuses a missing ledger before any scheduler call; its release_attempt record is fsynced before
    `scontrol release` (a failed append: no scontrol); an ambiguous scontrol counts as the one allowed attempt, so the
    next hold is cancelled, never released again; a clean release is reconciled with squeue (released)."""
    def held(s):
        j=s.ours(1,role='lane',partition='compute',state='PENDING')[0];s.fake.set(j,reason='launch failed requeued held',hold_start=True);return j
    def acts(s,j):return [r['action']for r in s.records('annotation')if r.get('about')=='held_release'and r.get('job_id')==j]
    def state(s,j):return next(x for x in s.fake.jobs()if x['id']==j)['state']
    rel=lambda s,j:s.call(ss.main,['release',j])
    s=Site(td,'rel_missing');j=held(s);(s.root/'ledger.jsonl').unlink()
    must(rel(s,j),69,'is missing','no scheduler command');assert not s.history('scontrol')and not s.history('squeue')and state(s,j)=='PENDING'
    s=Site(td,'rel_fault');j=held(s);s.h.faults['ledger:annotation']={'errno':errno.EDQUOT}
    must(rel(s,j),74,'quota');assert not s.history('scontrol')and state(s,j)=='PENDING'
    must(rel(s,j),0,'released held job');assert len(s.history('scontrol'))==1 and acts(s,j)==['release_attempt','released']and state(s,j)=='RUNNING'
    s=Site(td,'rel_amb');j=held(s);s.fake.config(fail_at={'scontrol':[1]})
    must(rel(s,j),69,'outcome is unknown','one allowed release');assert acts(s,j)==['release_attempt','release_unknown']and len(s.history('scontrol'))==1
    must(rel(s,j),0,'cancelled');assert len(s.history('scontrol'))==1 and state(s,j)=='CANCELLED'and acts(s,j)==['release_attempt','release_unknown','cancelled']
    s=Site(td,'rel_ok');j=held(s)
    must(rel(s,j),0,'released held job');assert acts(s,j)==['release_attempt','released']and state(s,j)=='RUNNING'
    s.fake.set(j,state='PENDING',reason='launch failed requeued held',start=None,hold_start=True)   # held a second time
    must(rel(s,j),0,'cancelled');assert len(s.history('scontrol'))==1 and state(s,j)=='CANCELLED'and acts(s,j)==['release_attempt','released','cancelled']
    ok('held_release_ledger_checked_first_attempt_recorded_before_scontrol_ambiguous_counts_reconciled')

def run_all(tests,td):
    for t in tests:t(td)

def run():
    with tempfile.TemporaryDirectory(prefix='c8d3_submit_')as td:
        td=Path(td);t0=time.time()
        run_all([test_billing_function,test_charges_pure,test_query_order_and_epoch,test_expanse_detection]+EXTRA,td)
    return {'status':'passed','seconds':round(time.time()-t0,1),'tests':RESULTS}
EXTRA=[test_sym_resolve,test_sym_admission,test_sym_su_line,test_sym_carry_asof,test_sym_vendor,test_sym_lock_refused,test_vendor_rule,test_time_minutes,test_site_subcaps,test_production_line,test_held_release_once,test_own_share,test_scheduler_truth_spy,test_intents_count,test_independence_account_detectors,test_reservation_forms,test_caps,test_names_and_records,test_su_gate_thresholds,test_reservation_binds,test_query_failures,test_a_append_failure_after_sbatch,test_b_sigkill_every_step,test_d_torn_final_record,test_e_interior_corruption,test_f_unattributable,test_h_budget_from_sacct,test_j_resnapshot,test_k_negative_scans_and_real_processes,test_l_intent_before_sbatch,test_m_killed_during_sbatch,test_n_accounting_delayed,test_o_resolution_dedup,test_p_repair_never_loses_an_intent,test_drill_faults,test_l_multi_job_append_failures,test_budget_standalone_evidence,test_resnapshot_query_failures,test_missing_ledger_writers,test_script_directives,test_decoding,test_h_requeue_last_attempt_lags,test_c_needs_no_other_attempt_restart_count,test_reader_race,test_exec_guard_preflight,test_launch_wrapper_not_started,test_docs_hpc,test_c_concurrent_submitters,test_i_registration_concurrent]
if __name__=='__main__':print(json.dumps(run(),indent=1,default=str))
