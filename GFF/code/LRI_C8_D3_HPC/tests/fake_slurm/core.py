"""A stateful fake Slurm for the Mac tests of LRI_C8_D3_HPC (plan A-ORC-17's preamble).

One state (a JSON file under an flock for the executables in bin/, or memory for the in-process runner) serves
sbatch, squeue, sacct, scancel, scontrol, sinfo, sprio and a `timeout` shim. Its behaviour is the worst case the plan
names: every eligible job starts at once after each command; sacct keeps no comment (F45); squeue fails without
--all; finished jobs leave squeue after a fake MinJobAge (300 s); sacct can deliver late (held per job) and, without
-s, omits a job that never became eligible in the window; with -s it selects by state. On request, an sbatch's
acceptance is delayed (the request stays in flight, the fake sbatch hangs until a `timeout` kills it, and the
controller accepts it later, also from a trigger on another command), sbatch rejects or fails ambiguously, a query
fails or hangs, and scancel filters PENDING in the client (a job may start between its load and its cancel). A
requeue adds an attempt as Slurm does: squeue's RestartCnt counts it, SubmitTime is reset and EligibleTime moves 121 s
later (the begin-time delay). squeue reads SQUEUE_STATES like --states.
Times are real time plus the offset in the clock file (shared with the tools' test hooks).
"""
from __future__ import annotations
import calendar,contextlib,copy,fcntl,json,math,os,re,shlex,sys,threading,time
from pathlib import Path

LIVE=('PENDING','RUNNING','SUSPENDED','CONFIGURING','COMPLETING','REQUEUED','SPECIAL_EXIT','REQUEUE_HOLD')
SHORT={'PD':'PENDING','R':'RUNNING','CF':'CONFIGURING','CG':'COMPLETING','S':'SUSPENDED','ST':'STOPPED','RQ':'REQUEUED','RH':'REQUEUE_HOLD',
       'RF':'REQUEUE_FED','RS':'RESIZING','SI':'SIGNALING','SO':'STAGE_OUT','SE':'SPECIAL_EXIT','CD':'COMPLETED','CA':'CANCELLED','F':'FAILED',
       'TO':'TIMEOUT','NF':'NODE_FAIL','OOM':'OUT_OF_MEMORY','PR':'PREEMPTED','BF':'BOOT_FAIL','DL':'DEADLINE'}
FINISHED=('COMPLETED','CANCELLED','FAILED','TIMEOUT','NODE_FAIL','OUT_OF_MEMORY','PREEMPTED','BOOT_FAIL','DEADLINE')
USER='zzheng8';ACCOUNT='yun124'

def pacific_to_epoch(text:str)->float:
    import zoneinfo,datetime
    d=datetime.datetime.strptime(text,'%Y-%m-%dT%H:%M:%S').replace(tzinfo=zoneinfo.ZoneInfo('America/Los_Angeles'))
    return d.timestamp()
def epoch_to_pacific(t:float)->str:
    import zoneinfo,datetime
    return datetime.datetime.fromtimestamp(t,zoneinfo.ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%dT%H:%M:%S')

def hms(s:int|None)->str:
    if s is None:return 'UNLIMITED'
    s=int(s);d,s=divmod(s,86400);h,s=divmod(s,3600);m,s=divmod(s,60)
    return (f'{d}-{h:02d}:{m:02d}:{s:02d}'if d else f'{h}:{m:02d}:{s:02d}'if h else f'{m}:{s:02d}')
def sacct_limit(s:int)->str:
    d,r=divmod(int(s),86400);h,r=divmod(r,3600);m,sec=divmod(r,60)
    return f'{d}-{h:02d}:{m:02d}:{sec:02d}'if d else f'{h:02d}:{m:02d}:{sec:02d}'
def parse_time(t:str)->int:
    m=re.fullmatch(r'(?:(\d+)-)?(\d+)(?::(\d+))?(?::(\d+))?',t)
    d,a,b,c=m.groups()
    if d is not None:return ((int(d)*24+int(a))*60+int(b or 0))*60+int(c or 0)
    if c is not None:return (int(a)*60+int(b))*60+int(c)
    if b is not None:return int(a)*60+int(b)
    return int(a)*60
def mem_mib(t:str)->float:
    m=re.fullmatch(r'(\d+(?:\.\d+)?)([KMGT]?)',t.strip(),re.I);u=(m.group(2)or'M').upper()
    return float(m.group(1))*{'K':1/1024,'M':1,'G':1024,'T':1024**2}[u]
def fmt_mem(mib:float)->str:return f'{int(mib//1024)}G'if mib%1024==0 else f'{int(mib)}M'
# symmetry mode (config site='symmetry'; Amendment A1): user zzheng1, every CPU partition EXCLUSIVE (whole nodes:
# 64 CPUs on the AMD partitions, 80 on the Intel ones), qos normal, tres-alloc of a pending job = its request (cpu=1,
# billing=1, as Slurm 21.08 prints it), AllocTRES of a started one = the node (billing = cpu, not cpu x 3600).
SYM_NODE_CPUS={'amdq':64,'amddebugq':64,'amdpreq':64,'defq':80,'debugq':80,'preq':80,'longq':80,'largememq':64}
SYM_USER='zzheng1'
def billing(part:str,nodes:int,cpus:int,mem:float,site:str='expanse')->int:
    if site=='symmetry':return max(cpus,SYM_NODE_CPUS.get(part,cpus)*nodes)*3600
    if part=='compute':return 128*3600*nodes
    return max(cpus,math.ceil(mem/2048-1e-9))*3600
def tasks_of(spec:str)->list:
    body=spec.split('%')[0];out=[]
    for p in body.split(','):
        lo,_,hi=p.partition('-');out+=list(range(int(lo),int(hi or lo)+1))
    return out
def ranges(ks:list)->str:
    ks=sorted(ks);out=[];i=0
    while i<len(ks):
        j=i
        while j+1<len(ks)and ks[j+1]==ks[j]+1:j+=1
        out.append(f'{ks[i]}'if i==j else f'{ks[i]}-{ks[j]}');i=j+1
    return ','.join(out)

class Fake:
    """The fake controller. path=None keeps the state in memory (the in-process runner of the interleaving tests)."""
    def __init__(self,path:str|None=None,events:str|None=None,clock:str|None=None,sink=None):
        self.path=path;self.events=events;self.clock=clock;self.sink=sink;self._mem=None;self._tlock=threading.RLock();self.inproc_kills=set()
        if path and not os.path.exists(path):self.save(self.fresh())
        if not path:self._mem=self.fresh()
    @staticmethod
    def fresh()->dict:
        return {'next_id':5000,'jobs':[],'inflight':[],'history':[],'config':{'min_job_age':300,'fail':{},'hang':{},'sbatch_rules':[],'triggers':[],
                'idle':{'compute':7,'shared':12,'debug':2,'amdq':13,'amddebugq':2,'defq':5,'debugq':3},'scancel_client_race':None,'scancel_drop':[],'site':'expanse'}}
    @classmethod
    def from_env(cls,env=None):
        e=env or os.environ
        return cls(e['FAKE_SLURM_STATE'],e.get('FAKE_SLURM_EVENTS'),e.get('FAKE_SLURM_CLOCK'))
    def env(self)->dict:
        out={'FAKE_SLURM_STATE':self.path}
        if self.events:out['FAKE_SLURM_EVENTS']=self.events
        if self.clock:out['FAKE_SLURM_CLOCK']=self.clock
        return out
    # -- state
    def load(self)->dict:return json.loads(Path(self.path).read_text())if self.path else self._mem
    def save(self,st):
        if self.path:
            tmp=self.path+'.tmp';Path(tmp).write_text(json.dumps(st));os.replace(tmp,self.path)
        else:self._mem=st
    @contextlib.contextmanager
    def tx(self):
        with self._tlock:
            if self.path:
                fd=os.open(self.path+'.lock',os.O_RDWR|os.O_CREAT,0o600)
                try:
                    fcntl.flock(fd,fcntl.LOCK_EX);st=self.load();yield st;self.save(st)
                finally:os.close(fd)
            else:yield self._mem
    def now(self)->float:
        off=0.0
        if self.clock:
            try:off=float(json.loads(Path(self.clock).read_text()).get('offset',0.0))
            except (OSError,ValueError):pass
        return time.time()+off
    def log(self,event,**info):
        rec={'t':time.time(),'pid':os.getpid(),'tid':threading.get_ident(),'event':event,**info}
        if self.sink is not None:self.sink.append(rec)
        if self.events:
            with open(self.events,'a')as f:f.write(json.dumps(rec)+'\n')

    # -- control API (tests)
    def config(self,**kw):
        with self.tx()as st:st['config'].update(kw)
    def add_job(self,name,state='RUNNING',user=USER,partition='shared',qos=None,cpus=1,mem='2G',time_s=3600,nodes=1,comment=None,elapsed=0,
                start_ago=None,array=None,hold_start=True,sacct_hold=False,submit_ago=10,account=ACCOUNT,tres_alloc=True,jid=None,end_ago=None,
                eligible=True,start_unknown=False,mem_per_cpu=False)->list:
        """A job made outside the tools (other users, C62d, unrecorded ones of ours). Returns its job id(s)."""
        with self.tx()as st:return self._add(st,name,state,user,partition,qos,cpus,mem,time_s,nodes,comment,elapsed,start_ago,array,hold_start,sacct_hold,
                                             submit_ago,account,tres_alloc,jid,end_ago,eligible,start_unknown,mem_per_cpu)
    def _add(self,st,name,state='RUNNING',user=USER,partition='shared',qos=None,cpus=1,mem='2G',time_s=3600,nodes=1,comment=None,elapsed=0,
             start_ago=None,array=None,hold_start=True,sacct_hold=False,submit_ago=10,account=ACCOUNT,tres_alloc=True,jid=None,end_ago=None,
             eligible=True,start_unknown=False,mem_per_cpu=False):
        if True:
            now=self.now();base=jid or str(self._next(st));out=[]
            for k in (array if array is not None else[None]):
                j=self._job(st,base,k,name,user,account,partition,qos,cpus,mem_mib(mem),time_s,nodes,comment,now-submit_ago,hold_start)
                j['sacct_hold']=sacct_hold;j['mem_per_cpu']=mem_per_cpu
                if not eligible:j['eligible']=None
                if state!='PENDING':
                    if j['raw']is None:j['raw']=str(self._next(st))
                    j['state']=state;j['start']=None if start_unknown else(now-(start_ago if start_ago is not None else elapsed))
                    if state in FINISHED:
                        j['end']=now-(end_ago or 0);j['elapsed']=elapsed if not start_unknown else 0
                st['jobs'].append(j);out.append(j['id'])
            return out
    def _next(self,st)->int:
        st['next_id']+=1;return st['next_id']
    def _job(self,st,base,task,name,user,account,part,qos,cpus,mem,tlim,nodes,comment,submit,hold_start,argv=None,dep=None,throttle=None,wrap=None,excl=False):
        jid=base if task is None else f'{base}_{task}';site=st['config'].get('site','expanse')
        return {'id':jid,'raw':base if task is None else None,'base':base,'task':task,'user':user,'account':account,'partition':part,'site':site,
                'qos':qos or{'compute':'normal','shared':'shared-normal','debug':'debug-normal'}.get(part,'normal'),'name':name,'comment':comment,
                'state':'PENDING','reason':'Priority','submit':submit,'eligible':None if dep else submit,'start':None,'end':None,'elapsed':0,
                'timelimit':tlim,'cpus':128 if part=='compute'and excl else cpus,'nodes':nodes,'mem':mem,'dep':dep,'throttle':throttle,'hold_start':hold_start,
                'attempts':[],'sacct_hold':False,'no_record':False,'argv':argv,'wrap':wrap,'requeue':False}
    def finish(self,jid,state='COMPLETED',elapsed=None,ago=0):
        with self.tx()as st:
            for j in st['jobs']:
                if j['id']==jid or j['base']==jid and j['task']is not None and jid==j['base']:
                    now=self.now()-ago
                    if j['state']=='PENDING':j['start']=None;j['elapsed']=0
                    else:
                        if elapsed is not None:j['start']=now-elapsed
                        j['elapsed']=int(now-j['start'])if j['start']is not None else 0
                    j['state']=state;j['end']=now
            self._schedule(st)
    def requeue(self,jid,failed_state='NODE_FAIL',elapsed=None,start_new=False):
        """The current attempt ends in failed_state and the job is pending again (a new attempt with a new Submit)."""
        with self.tx()as st:
            for j in st['jobs']:
                if j['id']==jid:
                    now=self.now();start=j['start']if elapsed is None else now-elapsed
                    j['attempts'].append({'submit':j['submit'],'start':start,'end':now,'state':failed_state,'elapsed':int(now-start)if start else 0})
                    j.update(state='PENDING',start=None,end=None,elapsed=0,submit=now+0.001,hold_start=not start_new,reason='BeginTime',eligible=now+121)
            self._schedule(st)
    def set(self,jid,**kw):
        with self.tx()as st:
            for j in st['jobs']:
                if j['id']==jid:j.update(kw)
            self._schedule(st)
    def deliver(self,jid=None):
        with self.tx()as st:
            for j in st['jobs']:
                if jid is None or j['id']==jid or j['base']==jid:j['sacct_hold']=False
    def accept(self,n=None)->list:
        """slurmctld accepts in-flight requests (all, or the first n): the jobs exist and every eligible one starts."""
        with self.tx()as st:return self._accept(st,n)
    def _accept(self,st,n=None):
        out=[];keep=[]
        for i,req in enumerate(st['inflight']):
            if n is None or len(out)<n:out+=self._create(st,req)
            else:keep.append(req)
        st['inflight']=keep;self._schedule(st);self.log('fake:accept',jobs=out);return out
    def advance(self,seconds:float):
        import ledger;ledger._advance_clock(self.clock,seconds)
    def jobs(self)->list:
        with self.tx()as st:return copy.deepcopy(st['jobs'])
    def state(self)->dict:
        with self.tx()as st:return copy.deepcopy(st)

    # -- scheduling (worst case: every eligible job starts at once)
    def _schedule(self,st):
        now=self.now();byid={j['id']:j for j in st['jobs']}
        running={}
        for j in st['jobs']:
            if j['task']is not None and j['state']=='RUNNING':running[j['base']]=running.get(j['base'],0)+1
        for j in st['jobs']:
            if j['state']!='PENDING':continue
            if j['dep']:
                kind,ids=j['dep']['kind'],j['dep']['ids'];deps=[x for i in ids for x in st['jobs']if x['id']==i or x['base']==i]   # an array: every task
                if not deps or any(d['state']in LIVE for d in deps):continue
                if kind=='afterok'and any(d['state']!='COMPLETED'for d in deps):j['reason']='DependencyNeverSatisfied';continue
                if j['eligible']is None:j['eligible']=now
            if j['eligible']is None:continue
            if j['hold_start']:continue
            if j['throttle']and running.get(j['base'],0)>=j['throttle']:continue
            j['state']='RUNNING';j['start']=now;j['reason']='None'
            if j['task']is not None:running[j['base']]=running.get(j['base'],0)+1
            if j['raw']is None:j['raw']=str(self._next(st))
        for j in st['jobs']:
            if j['state']=='RUNNING'and j['start']is not None:j['elapsed']=int(now-j['start'])

    # -- commands
    def main(self,cmd:str,argv:list,env:dict)->tuple[int,str,str]:
        with self.tx()as st:
            self.log('fake:'+cmd,argv=argv,ppid=os.getppid(),wrap=next((a.split('=',1)[1]for a in argv if a.startswith('--wrap=')),None))
            st['history'].append({'t':self.now(),'cmd':cmd,'argv':argv})
            calls=st.setdefault('calls',{});calls[cmd]=calls.get(cmd,0)+1
            for trig in list(st['config']['triggers']):
                if trig['cmd']==cmd and all(a in argv for a in trig.get('with',[]))and not any(a in argv for a in trig.get('without',[])):
                    trig['seen']=trig.get('seen',0)+1
                    if trig['seen']<trig.get('nth',1):continue
                    st['config']['triggers'].remove(trig);self.log('fake:trigger',trigger=trig)
                    if trig['do']=='accept':self._accept(st,trig.get('n'))
                    elif trig['do']=='start':
                        for j in st['jobs']:
                            if j['id']in trig['jobs']:j.update(state='RUNNING',start=self.now(),hold_start=False,raw=j['raw']or str(self._next(st)))
                    elif trig['do']=='add':
                        for kw in trig['jobs']:self._add(st,**kw)
                    elif trig['do']=='requeue':
                        for j in st['jobs']:
                            if j['id']in trig['jobs']:
                                now=self.now();j['attempts'].append({'submit':j['submit'],'start':j['start'],'end':now,'state':'NODE_FAIL','elapsed':int(now-j['start'])})
                                j.update(state='PENDING',start=None,end=None,elapsed=0,submit=now+0.001,hold_start=True,eligible=now+121)
                    elif trig['do']=='finish':
                        for j in st['jobs']:
                            if j['id']in trig['jobs']:
                                now=self.now();j.update(state=trig.get('state','COMPLETED'),end=now,elapsed=int(now-j['start'])if j['start']else 0)
            fail=st['config']['fail'].get(cmd,0)
            if fail or calls[cmd]in st['config'].get('fail_at',{}).get(cmd,[]):
                if fail:st['config']['fail'][cmd]=fail-1
                return 1,'',f'{cmd}: error: Socket timed out on send/recv operation (fake failure)'
            hang=st['config']['hang'].get(cmd)
        if hang:
            with self.tx()as st:st['config']['hang'].pop(cmd,None)
            time.sleep(hang)
        if cmd=='sbatch':return self.sbatch(argv,env)
        with self.tx()as st:
            r=getattr(self,'c_'+cmd)(st,argv,env)
            self._schedule(st)
        return r

    def c_sinfo(self,st,argv,env):
        p=argv[argv.index('-p')+1]if '-p'in argv else'shared'
        return 0,f'idle {st["config"]["idle"].get(p,0)}\nmix 3\nalloc 40\n',''
    def c_sprio(self,st,argv,env):
        return 0,'JOBID PARTITION PRIORITY\n'+''.join(f'{i} shared 1180\n'for i in argv[argv.index('-j')+1].split(','))if '-j'in argv else'',''
    def c_scontrol(self,st,argv,env):
        if argv[:2]==['show','job']:
            j=next((x for x in st['jobs']if x['id']==argv[2]),None)
            if not j:return 1,'','slurm_load_jobs error: Invalid job id specified'
            return 0,f'JobId={j["id"]} JobName={j["name"]} Requeue=0 Partition={j["partition"]} TimeLimit={hms(j["timelimit"])} Comment={j["comment"]}\n',''
        if argv[:1]==['release']and len(argv)==2:   # a held job loses its hold (and starts at the next schedule, as eligible jobs do here)
            for j in st['jobs']:
                if j['id']==argv[1]and j['state']=='PENDING'and 'held'in str(j.get('reason','')).lower():j.update(reason='None',hold_start=False)
        return 0,'',''

    def c_scancel(self,st,argv,env):
        pending_only='--state=PENDING'in argv or('--state'in argv and argv[argv.index('--state')+1]=='PENDING')
        ids=[a for a in argv if re.fullmatch(r'\d+(_\d+)?',a)]
        race=st['config'].get('scancel_client_race')
        now=self.now()
        sel=[j for j in st['jobs']if j['id']in ids or(j['base']in ids and j['task']is not None)]
        if pending_only and race:   # the client loads the job list, then a job starts, then the cancels go out
            loaded={j['id']:j['state']for j in sel}
            for j in sel:
                if race=='any'and j['state']=='PENDING'or j['id']in race:j.update(state='RUNNING',start=now,hold_start=False,raw=j['raw']or str(self._next(st)))
            st['config']['scancel_client_race']=None
            sel=[j for j in sel if loaded[j['id']]=='PENDING']
        for j in sel:
            if j['id']in st['config'].get('scancel_drop',[]):continue
            if pending_only and not race and j['state']!='PENDING':continue
            if j['state']in FINISHED:continue
            single=j['task']is not None and j['id']in ids
            if j['state']=='PENDING':j['start']=None;j['elapsed']=0
            else:j['elapsed']=int(now-j['start'])
            j['state']='CANCELLED';j['end']=now
            if single and j['start']is None:j['no_record']=True   # a pending task cancelled alone leaves no record (D.11)
        self.log('fake:scancel_done',ids=ids)
        return 0,'',''

    def _visible(self,st,j,now):
        return now-(j['end']or now)<=st['config']['min_job_age']if j['state']in FINISHED else True
    def c_squeue(self,st,argv,env):
        if '--all'not in argv:return 1,'','fake squeue: called without --all (refused by the fake: hidden partitions would be missed)'
        now=self.now()
        if '--start'in argv:
            ids=argv[argv.index('-j')+1].split(',')if '-j'in argv else[]
            return 0,''.join(f'{i} shared c8d3 zzheng8 PD {epoch_to_pacific(now+60)} 1 (Priority)\n'for i in ids),''
        states=env.get('SQUEUE_STATES')or None   # as squeue: the variable stands for --states, an option overrides it
        for a in argv:
            if a.startswith('--states='):states=a.split('=',1)[1]
        if '-t'in argv:states=argv[argv.index('-t')+1]
        if states is None:want=set(LIVE)
        elif states.lower()=='all':want=None
        else:want={SHORT.get(x,x)for x in states.split(',')}
        users=argv[argv.index('-u')+1].split(',')if '-u'in argv else None
        accts=argv[argv.index('-A')+1].split(',')if '-A'in argv else None
        jids=argv[argv.index('-j')+1].split(',')if '-j'in argv else None
        rows=[]
        for j in st['jobs']:
            if j['no_record']and j['state']=='CANCELLED':continue
            if not self._visible(st,j,now):continue
            if want is not None and j['state']not in want:continue
            if users and j['user']not in users:continue
            if accts and j['account']not in accts:continue
            if jids and j['id']not in jids and j['base']not in jids:continue
            rows.append(j)
        if '-r'not in argv:   # pending tasks of one array collapse into one record
            out=[];pend={}
            for j in rows:
                if j['task']is not None and j['state']=='PENDING':pend.setdefault(j['base'],[]).append(j)
                else:out.append(j)
            for b,js in pend.items():
                c=dict(js[0]);thr=f'%{js[0]["throttle"]}'if js[0]['throttle']else'';c['id']=f'{b}_[{ranges([x["task"]for x in js])}{thr}]';out.append(c)
            rows=out
        fmt=None;long=None;self._st_cache=st
        if '-o'in argv:fmt=argv[argv.index('-o')+1]
        if '-O'in argv:long=argv[argv.index('-O')+1]
        lines=[]
        for j in rows:
            if fmt is not None:lines.append(self._fmt_o(fmt,j,now))
            elif long is not None:lines.append(self._fmt_O(long,j,now))
            else:lines.append(f'{j["id"]} {j["partition"]} {j["name"]} {j["user"]} {j["state"]}')
        return 0,''.join(l+'\n'for l in lines),''
    def _field(self,j,key,now):
        tres=self._tres(j,alloc=j['state']!='PENDING')
        used=0 if j['start']is None else int((j['end']or now)-j['start'])
        dep='(null)'
        if j['dep']:
            un=[i for i in j['dep']['ids']if any((x['id']==i or x['base']==i)and x['state']in LIVE for x in self._st_cache['jobs'])]
            dep=','.join(f'{j["dep"]["kind"]}:{i}(unfulfilled)'for i in un)or'(null)'
        return {'i':j['id'],'F':j['base'],'K':str(j['task'])if j['task']is not None else'N/A','u':j['user'],'P':j['partition'],'q':j['qos'],'T':j['state'],
                'j':j['name'],'D':str(j['nodes']),'C':str(j['cpus']),'m':fmt_mem(j['mem']/(j['cpus']if j.get('mem_per_cpu')else 1)),'l':hms(j['timelimit']),
                'r':j['reason']if j['state']=='PENDING'else'None','k':j['comment']or'(null)','L':hms(max(0,j['timelimit']-used)),'M':hms(used),
                'S':epoch_to_pacific(j['start'])if j['start']else'N/A','E':dep,'tres':tres,
                'restarts':str(len(j['attempts'])),'V':epoch_to_pacific(j['submit']),   # RestartCnt counts the requeues
                'eligible':epoch_to_pacific(j['eligible'])if j.get('eligible')is not None else'N/A'}[key]
    _st_cache={'jobs':[]}
    def _fmt_o(self,fmt,j,now):
        out=[];i=0
        while i<len(fmt):
            if fmt[i]=='%':
                m=re.match(r'%(\.?)(\d*)([A-Za-z])',fmt[i:])
                v=self._field(j,m.group(3),now);w=int(m.group(2))if m.group(2)else 0
                v=v[:w]if w else v;out.append(v.rjust(w)if m.group(1)else v.ljust(w));i+=len(m.group(0))
            else:out.append(fmt[i]);i+=1
        return ''.join(out)
    NAMES={'JobArrayID':'i','ArrayJobID':'F','ArrayTaskID':'K','UserName':'u','Partition':'P','QOS':'q','State':'T','Name':'j','NumNodes':'D','NumCPUs':'C',
           'MinMemory':'m','TimeLimit':'l','Reason':'r','Comment':'k','tres-alloc':'tres','StartTime':'S','TimeUsed':'M','TimeLeft':'L','Dependency':'E',
           'RestartCnt':'restarts','SubmitTime':'V','EligibleTime':'eligible'}
    def _fmt_O(self,spec,j,now):
        out=[]
        for f in spec.split(','):
            name,_,rest=f.partition(':');m=re.fullmatch(r'(\.?)(\d*)(.*)',rest)
            v=self._field(j,self.NAMES[name],now);w=int(m.group(2))if m.group(2)else 20
            v=v[:w];out.append((v.rjust(w)if m.group(1)else v.ljust(w))+m.group(3))
        return ''.join(out)
    def _tres(self,j,alloc=True)->str:
        if j.get('site')=='symmetry':
            c=SYM_NODE_CPUS.get(j['partition'],j['cpus'])*j['nodes']if alloc else j['cpus']   # requested until allocated (exclusive nodes)
            return f'cpu={c},mem={fmt_mem(j["mem"])},node={j["nodes"]},billing={c}'
        b=billing(j['partition'],j['nodes'],j['cpus'],j['mem'])
        if j['partition']=='compute':return f'billing={b},cpu={128*j["nodes"]},mem={fmt_mem(j["mem"])},node={j["nodes"]}'
        return f'billing={b},cpu={j["cpus"]},mem={fmt_mem(j["mem"])},node=1'

    def c_sacct(self,st,argv,env):
        if env.get('TZ')not in(None,'America/Los_Angeles'):return 1,'','fake sacct: TZ must be America/Los_Angeles for -S'
        now=self.now();S=pacific_to_epoch(argv[argv.index('-S')+1])if '-S'in argv else 0
        sel=None
        if '-s'in argv:sel={SHORT[x]for x in argv[argv.index('-s')+1].split(',')}
        jids=argv[argv.index('-j')+1].split(',')if '-j'in argv else None
        fields=argv[argv.index('-o')+1].split(',')if '-o'in argv else['JobID','JobName','State']
        if '-X'not in argv:return 1,'','fake sacct: -X expected'
        rows=[];pend={}
        for j in st['jobs']:
            if j['sacct_hold']or j['no_record']:continue
            if jids and j['id']not in jids and j['base']not in jids:continue
            if '-u'in argv and j['user']!=argv[argv.index('-u')+1]:continue
            atts=[dict(a,current=False)for a in j['attempts']]+[{'submit':j['submit'],'start':j['start'],'end':j['end'],'state':j['state'],'elapsed':j['elapsed'],'current':True}]
            if j.get('sacct_hold_current'):atts=atts[:-1]   # accounting lags on the current attempt only (an earlier one is delivered)
            if '--duplicates'not in argv:atts=atts[-1:]
            for a in atts:
                if sel is None:   # the eligibility window (no state clause)
                    if j['eligible']is None:continue
                    if max(a['end']or now,j['eligible'])<S:continue
                else:
                    if a['state']not in sel:continue
                    if (a['end']or a['submit'])<S:continue
                if j['task']is not None and a['start']is None and a['current']and(a['state']=='PENDING'or a['state']=='CANCELLED'):
                    pend.setdefault((j['base'],a['state']),[]).append(j);continue
                rows.append(self._srow(j,a,fields,now))
        for (b,state),js in pend.items():
            j=js[0];thr=f'%{j["throttle"]}'if j['throttle']else''
            c=dict(j,id=f'{b}_[{ranges([x["task"]for x in js])}{thr}]',raw=b)
            rows.append(self._srow(c,{'submit':j['submit'],'start':None,'end':j['end'],'state':state,'elapsed':0},fields,now))
        rows.sort(key=lambda r:r[0])
        return 0,''.join('|'.join(r[1])+'\n'for r in rows),''
    def _srow(self,j,a,fields,now):
        el=a['elapsed']if a['state']not in('RUNNING',)else int(now-a['start'])
        started=a['start']is not None
        v={'JobID':j['id'],'JobIDRaw':j['raw']or j['base'],'JobName':j['name'],'Partition':j['partition'],
           'State':a['state']+(' by 1234'if a['state']=='CANCELLED'else''),'Submit':epoch_to_pacific(a['submit']),
           'Start':epoch_to_pacific(a['start'])if started else'Unknown','ElapsedRaw':str(el),'Timelimit':sacct_limit(j['timelimit']),
           'AllocTRES':self._tres(j)if started else'','ReqTRES':self._tres(j,alloc=False),'Comment':''}
        return (a['submit'],[v[f]for f in fields])

    def sbatch(self,argv,env):
        """sbatch with the options the tools use; reads #SBATCH lines and SBATCH_* like sbatch; --test-only creates nothing."""
        opts={};script=None;i=0;args=list(argv)
        def take(name,val):opts[name]=val
        short={'A':'account','p':'partition','q':'qos','t':'time','c':'cpus-per-task','o':'output','N':'nodes','n':'ntasks','d':'dependency','J':'job-name','a':'array'}
        def parse(tokens,src):
            nonlocal script
            k=0
            while k<len(tokens):
                t=tokens[k]
                if t.startswith('--'):
                    n,eq,v=t[2:].partition('=')
                    if n in('parsable','test-only','exclusive','no-requeue','requeue','hold'):take(n,True);k+=1;continue
                    if not eq:v=tokens[k+1];k+=1
                    take(n,v);k+=1
                elif t.startswith('-')and len(t)>=2:
                    n=short[t[1]];v=t[2:]if len(t)>2 else tokens[k+1];k+=1 if len(t)>2 else 2;take(n,v)
                else:
                    if src=='cmd':script=t;break
                    k+=1
        parse(args,'cmd')
        cmdopts=dict(opts);opts.clear()
        if script:   # as sbatch: a directive only at column 0; blank and comment lines skipped; the first command ends the scan
            for line in Path(script).read_text().split('\n'):
                if line.startswith('#SBATCH'):parse(shlex.split(line[7:],comments=True),'script');continue
                s=line.lstrip()
                if s and not s.startswith('#'):break
        sopts=dict(opts);opts.clear()
        envmap={'SBATCH_ACCOUNT':'account','SBATCH_PARTITION':'partition','SBATCH_MEM_PER_NODE':'mem','SBATCH_MEM_PER_CPU':'mem-per-cpu','SBATCH_TIMELIMIT':'time',
                'SBATCH_QOS':'qos','SBATCH_EXCLUSIVE':'exclusive','SBATCH_REQUEUE':'requeue'}
        eopts={o:env[k]for k,o in envmap.items()if env.get(k)}
        o={**sopts,**eopts,**cmdopts}
        part=o.get('partition','shared');cpus=int(o.get('cpus-per-task',1))*int(o.get('ntasks',1))
        mem=mem_mib(o['mem'])if 'mem'in o else mem_mib(o['mem-per-cpu'])*cpus if 'mem-per-cpu'in o else 1024*cpus
        tl=parse_time(o.get('time','60'));nodes=int(o.get('nodes',1))
        if o.get('test-only'):
            return 0,'',f'sbatch: Job 99999 to start at {epoch_to_pacific(self.now()+30)} using {cpus} processors on nodes exp-1-01 in partition {part}\n'
        with self.tx()as st:
            n=sum(1 for h in st['history']if h['cmd']=='sbatch'and '--test-only'not in h['argv'])
            rule=None
            for r in st['config']['sbatch_rules']:
                if r.get('nth')==n or r.get('name_has')and r['name_has']in o.get('job-name',''):rule=r;break
            if rule:st['config']['sbatch_rules'].remove(rule)
            req={'opts':o,'argv':argv,'script':script,'part':part,'cpus':cpus,'mem':mem,'tl':tl,'nodes':nodes,'submit':self.now(),
                 'user':SYM_USER if st['config'].get('site')=='symmetry'else USER}
            if rule and rule['action']=='reject':return rule.get('rc',1),'',rule['stderr']+'\n'
            if rule and rule['action']=='ambiguous_create':   # e.g. a lost connection after slurmctld created the job
                self._create(st,req);self._schedule(st);return rule.get('rc',1),'',rule['stderr']+'\n'
            if rule and rule['action']in('delay','delay_timeout'):   # slurmctld got the request; the reply never comes
                st['inflight'].append(req);self.log('fake:inflight',name=o.get('job-name'))
                if rule['action']=='delay_timeout':return 137,'',''   # in-process: the 120 s KILL of `timeout` fired
                hang=True
            else:
                hang=False;ids=self._create(st,req);self._schedule(st)
        if hang:
            if threading.current_thread()is not threading.main_thread()or not self.path:raise InflightKill()
            time.sleep(3600);return 1,'',''
        return 0,ids[0].split('_')[0]+'\n',''
    def _create(self,st,req):
        o=req['opts'];base=str(self._next(st))
        dep=None
        if o.get('dependency'):
            kind,_,ids=o['dependency'].partition(':');dep={'kind':kind,'ids':ids.split(':')}
        tasks=tasks_of(o['array'])if o.get('array')else[None]
        thr=int(o['array'].split('%')[1])if o.get('array')and '%'in o['array']else None
        out=[]
        for k in tasks:
            j=self._job(st,base,k,o.get('job-name','sbatch'),req['user'],o.get('account'),req['part'],o.get('qos'),req['cpus'],req['mem'],req['tl'],
                        req['nodes'],o.get('comment'),req['submit'],False,argv=req['argv'],dep=dep,throttle=thr,wrap=o.get('wrap'),excl=bool(o.get('exclusive')))
            j['requeue']=bool(o.get('requeue'))and not o.get('no-requeue');j['mem_per_cpu']='mem-per-cpu'in o and 'mem'not in o
            hn=st['config'].get('hold_new')or[]
            if hn:j['hold_start']=bool(hn[0])
            st['jobs'].append(j);out.append(j['id'])
        if st['config'].get('hold_new'):st['config']['hold_new']=st['config']['hold_new'][1:]
        self.log('fake:created',ids=out,name=o.get('job-name'),wrap=o.get('wrap'),argv=req['argv'])
        return out

    # -- invariants of the interleaving tests (in-flight requests counted as jobs)
    def counts(self,prefix='c8d3-')->dict:
        with self.tx()as st:
            if st['config'].get('site')=='symmetry':return self._sym_counts(st,prefix)
            jobs=[j for j in st['jobs']if j['state']in LIVE]
            fl=[{'partition':r['part'],'nodes':r['nodes'],'name':r['opts'].get('job-name',''),'state':'PENDING','user':USER,'cpus':r['cpus'],'mem':r['mem'],'timelimit':r['tl']}
                for r in st['inflight']for _ in (tasks_of(r['opts']['array'])if r['opts'].get('array')else[None])]
            ours=[j for j in jobs+fl if j['name'].startswith(prefix)]
            normal=[j for j in ours if j['partition']=='compute']
            others_run=[j for j in jobs if j['partition']=='compute'and not j['name'].startswith(prefix)and j['state']!='PENDING']
            spent=0.0;live=0.0
            for j in st['jobs']:
                if not j['name'].startswith(prefix):continue
                b=billing(j['partition'],j['nodes'],j['cpus'],j['mem'])/3600
                for a in j['attempts']:spent+=b*a['elapsed']/3600
                if j['state']in LIVE:live+=b*j['timelimit']/3600
                else:spent+=b*j['elapsed']/3600
            for r in fl:
                if r['name'].startswith(prefix):live+=billing(r['partition'],r['nodes'],r['cpus'],r['mem'])/3600*r['timelimit']/3600
            return {'normal':len(normal),'nodes':sum(j['nodes']for j in normal),'shared':sum(1 for j in ours if j['partition']=='shared'),
                    'account':len(others_run)+len(normal),'su':spent+live,'inflight':len(st['inflight'])}

    def _sym_counts(self,st,prefix)->dict:
        """symmetry's invariants: live AMD-pool nodes of the prefix (in-flight requests counted as jobs) and the
        core-hours (whole nodes) of the prefix."""
        amd=('amdq','amddebugq','amdpreq')
        jobs=[j for j in st['jobs']if j['state']in LIVE]
        fl=[{'partition':r['part'],'nodes':r['nodes'],'name':r['opts'].get('job-name',''),'cpus':r['cpus'],'mem':r['mem'],'timelimit':r['tl']}
            for r in st['inflight']for _ in (tasks_of(r['opts']['array'])if r['opts'].get('array')else[None])]
        ours=[j for j in jobs+fl if j['name'].startswith(prefix)]
        spent=0.0;live=0.0
        for j in st['jobs']:
            if not j['name'].startswith(prefix):continue
            b=billing(j['partition'],j['nodes'],j['cpus'],j['mem'],'symmetry')/3600
            for a in j['attempts']:spent+=b*a['elapsed']/3600
            if j['state']in LIVE:live+=b*j['timelimit']/3600
            else:spent+=b*j['elapsed']/3600
        for r in fl:
            if r['name'].startswith(prefix):live+=billing(r['partition'],r['nodes'],r['cpus'],r['mem'],'symmetry')/3600*r['timelimit']/3600
        return {'amd_nodes':sum(j['nodes']for j in ours if j['partition']in amd),'intel':sum(1 for j in ours if j['partition']not in amd),
                'su':spent+live,'inflight':len(st['inflight'])}

class InflightKill(BaseException):
    """Raised by the in-process sbatch whose acceptance is delayed: its caller dies during sbatch."""

def main(cmd:str|None=None)->int:
    cmd=cmd or os.path.basename(sys.argv[0])
    fake=Fake.from_env()
    rc,out,err=fake.main(cmd,sys.argv[1:],dict(os.environ))
    sys.stdout.write(out);sys.stderr.write(err)
    return rc

def timeout_main()->int:
    """The `timeout -s KILL N cmd...` shim: FAKE_TIMEOUT_SECONDS replaces N in tests (the KILL then comes in seconds)."""
    import signal,subprocess
    a=sys.argv[1:]
    if a[:2]!=['-s','KILL']:sys.stderr.write('fake timeout: only -s KILL N is supported\n');return 125
    n=float(os.environ.get('FAKE_TIMEOUT_SECONDS',a[2]));cmd=a[3:]
    try:p=subprocess.Popen(cmd)
    except OSError as e:   # as coreutils: 126 if the command cannot be invoked, 127 if it is not found
        sys.stderr.write(f"timeout: failed to run command '{cmd[0]}': {e.strerror}\n");return 127 if isinstance(e,FileNotFoundError)else 126
    fake=Fake.from_env()if os.environ.get('FAKE_SLURM_STATE')else None
    if fake:fake.log('fake:timeout_start',pid=os.getpid(),child=p.pid,ppid=os.getppid())
    try:return p.wait(timeout=n)
    except subprocess.TimeoutExpired:
        p.send_signal(signal.SIGKILL);p.wait()
        if fake:fake.log('fake:timeout_kill',pid=os.getpid(),child=p.pid)
        return 137

def install(bindir:Path)->Path:
    """Write the executables (with this interpreter) into bindir; put it first on PATH."""
    bindir=Path(bindir);bindir.mkdir(parents=True,exist_ok=True);here=Path(__file__).resolve().parents[1];tools=Path(__file__).resolve().parents[2]/'tools'
    for c in ('sbatch','squeue','sacct','scancel','scontrol','sinfo','sprio'):
        (bindir/c).write_text(f'#!{sys.executable} -B\nimport sys;sys.path[:0]=[{str(here)!r},{str(tools)!r}]\nfrom fake_slurm.core import main\nsys.exit(main({c!r}))\n')
    (bindir/'timeout').write_text(f'#!{sys.executable} -B\nimport sys;sys.path[:0]=[{str(here)!r},{str(tools)!r}]\nfrom fake_slurm.core import timeout_main\nsys.exit(timeout_main())\n')
    for f in bindir.iterdir():f.chmod(0o755)
    return bindir

def inprocess_runner(fake:Fake):
    """budget.RUNNER for the in-process interleaving tests: the launch wrapper (timeout, exec guard) is emulated."""
    import subprocess
    def run(argv,env,timeout):
        argv=list(argv)
        if argv[0]=='timeout':
            deadline=int(argv[5]);argv=argv[6:]
            if time.time()>deadline:return subprocess.CompletedProcess(argv,86,'','c8d3-exec-guard: late\n')
        hang=fake.state()['config']['hang'].get(argv[0])
        if hang and hang>timeout:
            fake.config(hang={k:v for k,v in fake.state()['config']['hang'].items()if k!=argv[0]})
            raise subprocess.TimeoutExpired(argv,timeout)
        rc,out,err=fake.main(argv[0],argv[1:],env)
        return subprocess.CompletedProcess(argv,rc,out,err)
    return run
