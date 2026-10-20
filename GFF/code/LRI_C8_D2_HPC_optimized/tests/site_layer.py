#!/usr/bin/env python3
"""Site-layer tests (docs/SITES.md): option resolution and every refusal, environment scrubbing for sbatch and squeue,
admission arithmetic and the site lock, the bidirectional classifier check against LRI_C8_D2_HPC and LRI_C8_D3_HPC,
claims (order, done, history, exhaustion, retry, stale and requeue release, TERM forwarding), the deadline, seeds
(reserve, check, pins, corrupt log, lock contention, seed_sync.sh, receipts), the runtime identity and the squeue
UNKNOWN path. sbatch, squeue, scontrol, ldd, ssh and scp are PATH shims and every campaign is synthetic: nothing is
submitted, no native code runs and no cluster is contacted.

Our tools/seeds.py and common.py (LRI_C8_D2_HPC aafa8a4, pinned) come from C8_SEEDS_TOOL_DIR when its files match the
pins, else from `git archive aafa8a4` of ../LRI_C8_D2_HPC. The classifier check imports LRI_C8_D2_HPC aafa8a4 and
LRI_C8_D3_HPC bce1c7a tools from `git archive` (C8_TEST_OURS_REPO, C8_TEST_C63D_REPO; default ../<name>). A source
that is unavailable (e.g. on a cluster node) skips its tests and is named in the report; --require-all fails instead.
"""
from __future__ import annotations
import argparse,hashlib,json,os,pwd,shutil,signal,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import node_runner as nr
import production as prod
import site_submit as ss
from common import digest,dump,load
from task_schedule import freeze_blocks

PY=sys.executable;ME=pwd.getpwuid(os.getuid()).pw_name;F={}  # fixtures, set by setUpModule
SKIPPED={}

# ---------------------------------------------------------------- shims
SQUEUE=r'''import fcntl,json,os,re,sys
e=os.environ;a=sys.argv[1:]
with open(e['FAKE_LOG'],'a')as f:f.write(json.dumps({'cmd':'squeue','args':a,'scrubbed_env':sorted(k for k in e if k.startswith('SQUEUE_')or k.endswith('_CLUSTERS'))})+'\n')
if e.get('FAKE_SQUEUE_FAIL'):print('squeue: error: Unable to contact slurm controller',file=sys.stderr);sys.exit(1)
if e.get('FAKE_SQUEUE_GARBAGE'):print('this is not a squeue line');sys.exit(0)
st=json.load(open(e['FAKE_SLURM']));fmt=a[a.index('-o')+1]
def opt(k):return a[a.index(k)+1]if k in a else None
recs=st['jobs']
if opt('-u'):recs=[r for r in recs if r['user']==opt('-u')]
if opt('-A'):recs=[r for r in recs if r.get('account')==opt('-A')]
if opt('-j'):recs=[r for r in recs if r['jobid']==opt('-j')]
if e.get('SQUEUE_NAMES'):recs=[r for r in recs if r['name']in e['SQUEUE_NAMES'].split(',')]
seq=e.get('FAKE_LEFT_SEQ')
if seq and opt('-j'):
    p=e['FAKE_SLURM']+'.left';k=int(open(p).read())if os.path.exists(p)else 0;open(p,'w').write(str(k+1));vals=seq.split(',')
    recs=[dict(r,left=vals[min(k,len(vals)-1)])for r in recs]
F={'i':'jobid','T':'state','P':'partition','q':'qos','D':'nodes','u':'user','L':'left','k':'comment','j':'name','a':'account','C':'cpus','m':'minmem','l':'timelimit','r':'reason'}
def field(r,c):
    if c=='F':return r['jobid'].split('_')[0]
    v=r.get(F[c]);return '(null)'if v is None else str(v)
for r in recs:print(re.sub(r'%\.?\d*([a-zA-Z])',lambda m:field(r,m.group(1)),fmt))
'''
SBATCH=r'''import fcntl,json,os,sys,time
e=os.environ;a=sys.argv[1:];test='--test-only'in a;par='--parsable'in a
def opt(n):
    for x in a:
        if x.startswith(n+'='):return x[len(n)+1:]
    return None
watched=sorted(k for k in e if(k.startswith(('SBATCH_','SALLOC_','SLURM_'))or k.endswith('_CLUSTERS'))and k!='SLURM_CONF')
with open(e['FAKE_LOG'],'a')as f:f.write(json.dumps({'cmd':'sbatch','args':a,'scrubbed_env':watched,'SLURM_CONF':e.get('SLURM_CONF'),'C8_MERGE_WORKERS':e.get('C8_MERGE_WORKERS'),
    'C8_RUN':e.get('C8_RUN'),'C8_PACKAGE':e.get('C8_PACKAGE'),'C8_SITE':e.get('C8_SITE'),'C8_ENV_SETUP':e.get('C8_ENV_SETUP')})+'\n')
role='merge'if a[-1].endswith('merge.sh')else'run'
if test:
    if e.get('FAKE_TESTONLY_FAIL')==role:print(f'sbatch: error: fake test-only refusal of the {role} request',file=sys.stderr);sys.exit(1)
    print('sbatch: Job 4242 to start at 2026-10-09T00:00:00 using 1 processors on nodes n1 in partition '+str(opt('--partition')),file=sys.stderr)
    if e.get('FAKE_PREEMPTS'):print('sbatch:   Preempts: 4141',file=sys.stderr)
    sys.exit(0)
with open(e['FAKE_SLURM']+'.lock','w')as lk:
    fcntl.flock(lk,fcntl.LOCK_EX)
    st=json.load(open(e['FAKE_SLURM']))
    if e.get('FAKE_SBATCH_FAIL_AT')and st.get('accepted',0)>=int(e['FAKE_SBATCH_FAIL_AT']):print('sbatch: error: QOSMaxSubmitJobPerUserLimit',file=sys.stderr);sys.exit(1)
    st['next']=st.get('next',5000)+1;st['accepted']=st.get('accepted',0)+1;jid=str(st['next']);part=opt('--partition')
    st['jobs'].append({'jobid':jid,'state':'PENDING','partition':part,'qos':opt('--qos')or{'compute':'normal','shared':'shared-normal'}.get(part,'normal'),
                       'nodes':1,'user':e['FAKE_ME'],'name':opt('--job-name'),'comment':opt('--comment'),'account':opt('--account'),'left':opt('--time')})
    json.dump(st,open(e['FAKE_SLURM']+'.tmp','w'));os.replace(e['FAKE_SLURM']+'.tmp',e['FAKE_SLURM'])
    time.sleep(float(e.get('FAKE_SBATCH_DELAY','0')))
print(jid)
'''
SCONTROL=r'''import json,os,sys
a=sys.argv[1:];st=json.load(open(os.environ['FAKE_SLURM']))
r=[x for x in st['jobs']if a[:2]==['show','job']and x['jobid']==a[2]]
if not r:print('slurm_load_jobs error: Invalid job id specified',file=sys.stderr);sys.exit(1)
r=r[0];print(f'JobId={r["jobid"]} JobName={r["name"]}\n   UserId={r["user"]} Account={r.get("account")} QOS={r["qos"]}\n   JobState={r["state"]} Partition={r["partition"]} Comment={r.get("comment")}')
'''
LDD=r'''import os,sys
if os.environ.get('FAKE_LDD_FAIL'):print('ldd: not a dynamic executable',file=sys.stderr);sys.exit(1)
print('\tlinux-vdso.so.1 (0x00007ffd)')
for p in filter(None,os.environ.get('FAKE_LDD_LIBS','').split(':')):print(f'\t{os.path.basename(p)} => {p} (0x00007f00)')
for p in filter(None,os.environ.get('FAKE_LDD_ABS','').split(':')):print(f'\t{p} (0x00007f00)')  # e.g. /etc/ld.so.preload entries
for n in filter(None,os.environ.get('FAKE_LDD_MISSING','').split(':')):print(f'\t{n} => not found')
'''
SSH=r'''import json,os,re,subprocess,sys
e=os.environ;a=sys.argv[1:];root=e['FAKE_SITES']
open(e['FAKE_SSH_LOG'],'a').write(json.dumps({'cmd':'ssh','args':a})+'\n')
if a[:1]==['-O']:print('Master running (pid=1)',file=sys.stderr);sys.exit(0)
if a[:1]==['-T']:a=a[1:]
host,cmd=a[0],' '.join(a[1:])
cmd=re.sub(r'~/|/mnt/beegfs/|/expanse/',lambda m:f'{root}/{host}'+('/home/'if m.group(0)=='~/'else m.group(0)),cmd)
mode=e.get('FAKE_INJECT')  # a concurrent seeds.py add on symmetry while Expanse merges: once, or every time
if mode and host=='expanse'and ' merge 'in cmd:
    f=root+'/injected';k=int(open(f).read())if os.path.exists(f)else 0
    if mode=='always'or k==0:
        open(f,'w').write(str(k+1))
        subprocess.run([sys.executable,'-B',e['FAKE_SEEDS_TOOL'],'add','--seed',str(700001+k),'--label',f'concurrent symmetry add {k+1}',
                        '--log',f'{root}/symmetry/mnt/beegfs/zzheng1/c8-d2/forbidden_seeds.json'],check=True,stdout=subprocess.DEVNULL)
sys.exit(subprocess.run(['bash','-c',cmd]).returncode)
'''
SCP=r'''import json,os,shutil,sys
e=os.environ;a=[x for x in sys.argv[1:]if x!='-q'];root=e['FAKE_SITES']
open(e['FAKE_SSH_LOG'],'a').write(json.dumps({'cmd':'scp','args':a})+'\n')
def loc(x):
    if ':'in x and not x.startswith('/'):h,q=x.split(':',1);return f'{root}/{h}{q}'
    return x
src,dst=map(loc,a);shutil.copyfile(src,dst)
'''
# production.py run stand-in: commits the index's uncommitted blocks in order (up to --max-blocks), per fake_control.json.
FAKE_PRODUCTION=r'''import json,os,signal,sqlite3,sys,time
from pathlib import Path
sys.path.insert(0,os.environ['REAL_TOOLS'])
from task_schedule import block_count
a=sys.argv[1:];run=Path(a[1]);i=int(a[a.index('--index')+1]);k=int(a[a.index('--max-blocks')+1])if '--max-blocks'in a else None
def event(**kw):
    with open(run/'fake_calls.jsonl','a')as f:f.write(json.dumps({'index':i,**kw})+'\n')
def stop(s,f):signal.signal(signal.SIGTERM,signal.SIG_IGN);print('fake production: TERM received, native stopped, runtime removed',flush=True);event(event='term');sys.exit(143)
signal.signal(signal.SIGTERM,stop)
event(event='start',max_blocks=k,threads=int(a[a.index('--threads')+1]),scratch=a[a.index('--scratch')+1],job=os.environ.get('SLURM_JOB_ID'))
ctl=json.loads((run/'fake_control.json').read_text())if (run/'fake_control.json').exists()else{}
if str(i)in ctl.get('fail',[]):print('fake production: native work block failed',flush=True);sys.exit(1)
m=json.loads((run/'manifest.json').read_text());j=m['jobs'][i];p=run/'groups'/j['group']
db=sqlite3.connect(p.joinpath('tasks.sqlite').resolve().as_uri()+'?mode=ro',uri=True);nb=block_count(db,j['shard'],m['checkpoint_tasks']);db.close()
(p/'checkpoints').mkdir(exist_ok=True);n=0
for part in range(nb):
    f=p/'checkpoints'/f's{j["shard"]:06d}_p{part:06d}.json'
    if f.exists():continue
    if k is not None and n>=k:print(f'stopped after {n} blocks (--max-blocks)',flush=True);break
    time.sleep(float(ctl.get('sleep',0)));f.write_text('{}\n');n+=1;print(f'committed {j["group"]}/{f.stem}',flush=True)
'''
WRAPPER=r'''import os,sys
from pathlib import Path
sys.path.insert(0,os.environ['REAL_TOOLS'])
import node_runner as nr
nr.PRODUCTION=Path(os.environ['FAKE_PRODUCTION']);nr.campaign_executable=lambda m:Path(os.environ['FAKE_EXE'])
sys.exit(nr.main())
'''

def shim(path:Path,code:str):path.write_text(f'#!{PY}\n'+code);path.chmod(0o755)

def git_archive(repo:Path,rev:str,paths:list,dest:Path)->str|None:
    """None, or why `git archive rev paths` of repo could not be extracted into dest."""
    if not (repo/'.git').exists():return f'{repo} is not available'
    dest.mkdir(parents=True,exist_ok=True)
    a=subprocess.run(['git','-C',str(repo),'archive',rev,*paths],capture_output=True)
    if a.returncode:return f'git archive {rev} of {repo} failed: {a.stderr.decode()[-200:]}'
    t=subprocess.run(['tar','-x','-C',str(dest)],input=a.stdout,capture_output=True)
    return None if t.returncode==0 else f'tar failed: {t.stderr.decode()[-200:]}'

def setUpModule():
    t=Path(tempfile.mkdtemp(prefix='c8_site_layer_',dir=ROOT/'verification'));F['T']=t;fb=t/'fakebin';fb.mkdir()
    for n,c in (('squeue',SQUEUE),('sbatch',SBATCH),('scontrol',SCONTROL),('ldd',LDD),('ssh',SSH),('scp',SCP)):shim(fb/n,c)
    (fb/'python3').write_text(f'#!/bin/bash\nexec {PY} "$@"\n');(fb/'python3').chmod(0o755)
    if not shutil.which('sha256sum'):(fb/'sha256sum').write_text('#!/bin/bash\nexec shasum -a 256 "$@"\n');(fb/'sha256sum').chmod(0o755)
    F['fakebin']=fb;F['exe']=t/'c8d2_gmp';F['exe'].write_bytes(b'fake campaign executable\n')
    F['libs']=[t/'libquadmath.so.0',t/'libgmp.so.10']
    for p in F['libs']:p.write_bytes(p.name.encode())
    pkg=t/'fakepkg';(pkg/'tools').mkdir(parents=True);(pkg/'tools/node_runner.py').write_text(WRAPPER);F['pkg']=pkg
    (t/'fake_production.py').write_text(FAKE_PRODUCTION);F['production']=t/'fake_production.py'
    F['envfile']=t/'env_site.sh';F['envfile'].write_text('# synthetic C8_ENV_SETUP of the tests\n')
    # our pinned seed tools
    st=None
    for d in [os.environ.get('C8_TEST_SEEDS_TOOL_DIR'),os.environ.get('C8_SEEDS_TOOL_DIR')]:
        if d and all((Path(d)/n).is_file()and digest(Path(d)/n)==h for n,h in nr.SEED_PINS.items()):st=Path(d);break
    if st is None:
        why=git_archive(Path(os.environ.get('C8_TEST_OURS_REPO')or ROOT.parent/'LRI_C8_D2_HPC'),'aafa8a4',['tools/seeds.py','tools/common.py'],t/'seedtool')
        if why is None:st=t/'seedtool/tools'
        else:SKIPPED['seeds']=why
    F['seedtool']=st
    why=git_archive(Path(os.environ.get('C8_TEST_OURS_REPO')or ROOT.parent/'LRI_C8_D2_HPC'),'aafa8a4',['tools'],t/'ours')
    if why:SKIPPED['classifier_ours']=why
    else:F['ours']=t/'ours/tools'
    why=git_archive(Path(os.environ.get('C8_TEST_C63D_REPO')or ROOT.parent/'LRI_C8_D3_HPC'),'bce1c7a',['tools'],t/'c63d')
    if why:SKIPPED['classifier_c63d']=why
    else:F['c63d']=t/'c63d/tools'

def tearDownModule():
    for _ in range(5):  # a file-sync daemon (e.g. on a synced Mac home) can briefly hold directory entries
        shutil.rmtree(F['T'],ignore_errors=True)
        if not F['T'].exists():return
        time.sleep(0.5)

def need(*keys):
    for k in keys:
        if k not in F or F[k]is None:raise unittest.SkipTest(SKIPPED.get(k.replace('ours','classifier_ours').replace('c63d','classifier_c63d'),f'{k} unavailable'))

# ---------------------------------------------------------------- synthetic campaigns and scheduler state
_N={'n':0}
def campaign(groups=(('a_free_L8',1),),tasks=4,cost=1.,checkpoint_tasks=4,threads=4,cost_model=False,test_only=True,seed=None,backend='gmp',graphs=1):
    """A planned-campaign stand-in: manifest.json, groups/<g>/config.json and tasks.sqlite with frozen blocks
    (task_schedule.freeze_blocks). tasks: tasks per graph and shard; cost: task cost (seconds with a cost model), or a
    callable (group, shard, task) -> cost."""
    _N['n']+=1;run=F['T']/'runs'/f'c{_N["n"]:03d}';(run/'groups').mkdir(parents=True);jobs=[];gl=[]
    for g,nsh in groups:
        p=run/'groups'/g;p.mkdir();db=sqlite3.connect(p/'tasks.sqlite')
        db.executescript('CREATE TABLE tasks(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,cost REAL,shard INTEGER,pos INTEGER);'
                         'CREATE TABLE expected(rep INTEGER,gi INTEGER,total INTEGER,PRIMARY KEY(rep,gi));')
        uid=0
        for s in range(nsh):
            pos=0
            for gi in range(graphs):
                for r in range(tasks):
                    c=cost(g,s,uid)if callable(cost)else cost
                    db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)',(uid,r,s*graphs+gi,0,4,4,float(c),s,pos));uid+=1;pos+=1
        db.execute('CREATE INDEX shard_order ON tasks(shard,pos)');db.commit();freeze_blocks(db,nsh,checkpoint_tasks);db.close()
        dump(p/'config.json',{'schema':prod.GROUP_SCHEMA,'name':g,'synthetic':True});gl.append({'name':g,'sha256':digest(p/'config.json')})
        jobs+=[{'id':len(jobs)+s,'group':g,'shard':s}for s in range(nsh)]
    m={'schema':prod.SCHEMA,'dimension':2,'order':8,'tool_sha256':{n:digest(ROOT/'tools'/n)for n in prod.TOOLS},'backend':backend,
       'executable_sha256':digest(F['exe']),'threads':threads,'checkpoint_tasks':checkpoint_tasks,'groups':gl,'jobs':jobs,'test_only':test_only,
       'seed':seed if seed is not None else 900000000000+_N['n'],'cost_model_sha256':'0'*64 if cost_model else None,'estimates':{},'synthetic':True}
    dump(run/'manifest.json',m);return run

def job(jobid,name,state='RUNNING',partition='compute',user=None,qos='normal',nodes=1,account='yun124',comment=None,left='1:00:00'):
    return {'jobid':str(jobid),'name':name,'state':state,'partition':partition,'user':user or ME,'qos':qos,'nodes':nodes,'account':account,'comment':comment,'left':left}

def slurm(jobs=(),path=None)->Path:
    p=path or F['T']/f'slurm_{time.time_ns()}.json';p.write_text(json.dumps({'jobs':list(jobs)}));return p

def records(jobs)->list:
    """Parse jobs exactly as the helper does (through the QUERY_FORMAT rendering of the fake squeue)."""
    st=slurm(jobs);log=F['T']/'rec.log';e={**os.environ,'PATH':f'{F["fakebin"]}:{os.environ["PATH"]}','FAKE_SLURM':str(st),'FAKE_LOG':str(log)}
    return nr.squeue(e,[],'test')

def calls(log:Path,cmd:str)->list:
    return [json.loads(x)for x in log.read_text().splitlines()if json.loads(x)['cmd']==cmd]if log.exists()else[]

def base_env(st:Path,log:Path,**kw)->dict:
    e={k:v for k,v in os.environ.items()if not k.startswith(('SBATCH_','SALLOC_','SLURM_','SQUEUE_','C8_'))}
    e.update(PATH=f'{F["fakebin"]}:{os.environ["PATH"]}',FAKE_SLURM=str(st),FAKE_LOG=str(log),FAKE_ME=ME,PYTHONDONTWRITEBYTECODE='1',REAL_TOOLS=str(ROOT/'tools'),
             FAKE_PRODUCTION=str(F['production']),FAKE_EXE=str(F['exe']),FAKE_LDD_LIBS=':'.join(map(str,F['libs'])))
    e.update({k:str(v)for k,v in kw.items()});return e

EXP_RUN='-A yun124 -p compute -N1 -n1 -c 128 --mem 240G';EXP_MERGE='-A yun124 -p shared -c 8 --mem 32G'
SYM_RUN='-p amdq --exclude=cn112 -N1 -n1 -c 64 --mem 245G';SYM_MERGE='-p sharedq -c 8 --mem 16000M'

def submit_env(site,st,log,home=None,**kw)->dict:
    home=home or F['T']/f'home_{time.time_ns()}';home.mkdir(exist_ok=True)
    seeds=F['T']/'seeds_empty.json'
    if not seeds.exists():seeds.write_text(json.dumps({'schema':'c8-d2-seeds-1','seeds':[]}))
    e=base_env(st,log,C8_SITE=site,C8_ENV_SETUP=F['envfile'],HOME=home,C8_SEEDS=seeds,C8_SEEDS_TOOL_DIR=F['seedtool']or'/nonexistent',
               C8_SBATCH_ARGS=EXP_RUN if site=='expanse'else SYM_RUN,C8_MERGE_SBATCH_ARGS=EXP_MERGE if site=='expanse'else SYM_MERGE)
    if site=='symmetry':e.update(C8_AMD_CAP='3',C8_AMD_POOL_TOTAL='12')
    e.update({k:str(v)for k,v in kw.items()});return e

def submit(args,env,timeout=120)->subprocess.CompletedProcess:
    return subprocess.run([PY,'-B',str(ROOT/'tools/site_submit.py'),*map(str,args)],capture_output=True,text=True,env=env,timeout=timeout)

def runner(run,env,job_id='7001',restart=0,threads=4,timeout=120)->subprocess.CompletedProcess:
    e=dict(env,SLURM_JOB_ID=str(job_id),SLURM_RESTART_COUNT=str(restart),SLURM_CPUS_PER_TASK=str(threads))
    sc=F['T']/f'scratch_{job_id}_{restart}';sc.mkdir(exist_ok=True)
    return subprocess.run([PY,'-B',str(F['pkg']/'tools/node_runner.py'),'run',str(run),'--threads',str(threads),'--scratch',str(sc)],capture_output=True,text=True,env=e,timeout=timeout)

def fake_calls(run)->list:
    p=run/'fake_calls.jsonl';return [json.loads(x)for x in p.read_text().splitlines()]if p.exists()else[]

def started(run)->list:return [c['index']for c in fake_calls(run)if c['event']=='start']

def refuses(code,fn,*a,**k)->str:
    try:fn(*a,**k)
    except nr.Refuse as r:
        if r.code!=code:raise AssertionError(f'refused with {r.code}, not {code}: {r}')
        return str(r)
    raise AssertionError(f'not refused (expected {code})')

# ================================================================ option resolution and refusals
class Options(unittest.TestCase):
    def test_profiles_resolve_to_canonical_requests(self):
        r=ss.resolve('expanse','run',ss.parse_options(EXP_RUN,'x'),128);a=ss.sbatch_argv(r,'12:00:00','c8ind:c8:abc',Path('/r/slurm_logs'))
        for x in ('--account=yun124','--partition=compute','--nodes=1','--ntasks=1','--cpus-per-task=128','--mem=240G','--time=12:00:00','--job-name=c8d2-ind-run',
                  '--comment=c8ind:c8:abc','--output=/r/slurm_logs/run-%j.log','--open-mode=append','--export=ALL'):self.assertIn(x,a)
        self.assertEqual(a[-1],str(ROOT/'slurm/node_runner.sh'))
        m=ss.resolve('expanse','merge',ss.parse_options(EXP_MERGE,'x'),128);a=ss.sbatch_argv(m,ss.MERGE_TIME,'c',Path('/r'),['11','12'])
        self.assertIn('--dependency=afterany:11:12',a);self.assertIn('--partition=shared',a);self.assertIn('--cpus-per-task=8',a);self.assertIn('--time=04:00:00',a)
        self.assertEqual(a[-1],str(ROOT/'slurm/merge.sh'))
        for spec in (SYM_RUN,'-p amdpreq --requeue -x cn[079-082,112] -c 64 --mem=250880M','-p amddebugq --exclude=cn110,cn112 -c64 --mem 245G'):
            r=ss.resolve('symmetry','run',ss.parse_options(spec,'x'),64);self.assertIn(r['partition'],ss.PROFILES['symmetry']['run']['partitions'])
        self.assertEqual(ss.resolve('symmetry','merge',ss.parse_options(SYM_MERGE,'x'),64)['partition'],'sharedq')
        self.assertEqual(ss.resolve('expanse','run',ss.parse_options(EXP_RUN+' -q normal','x'),128)['qos'],'normal')
        self.assertEqual(ss.hostlist('cn[079-082,112],gpu1'),{'cn079','cn080','cn081','cn082','cn112','gpu1'})

    def test_every_option_refusal(self):
        cases=[('expanse','run','-A yun124 -p compute -N1 -n1 -c 128 --mem 240G --exclusive','not allowed'),
               ('expanse','run',EXP_RUN+' --array=0-3','not allowed'),('expanse','run',EXP_RUN+' -w exp-1-01','not allowed'),
               ('expanse','run',EXP_RUN+' --dependency=afterok:1','not allowed'),('expanse','run',EXP_RUN+' --time=01:00:00','not allowed'),
               ('expanse','run',EXP_RUN+' --job-name=x','not allowed'),('expanse','run',EXP_RUN+' --clusters=x','not allowed'),
               ('expanse','run','-A yun124 -p compute -N2 -n1 -c 128 --mem 240G','one node'),('expanse','run','-A yun124 -p compute --nodes 2 -c 128 --mem 240G','one node'),
               ('expanse','run',EXP_RUN+' -q debug','not allowed'),('expanse','run','-A other -p compute -c 128 --mem 240G','-A yun124'),
               ('expanse','run','-A yun124 -p shared -c 128 --mem 240G','not allowed'),('expanse','run','-A yun124 -p compute,debug -c 128 --mem 240G','exactly one'),
               ('expanse','run','-A yun124 -p compute -c 64 --mem 240G','threads'),('expanse','run','-A yun124 -p compute -c 128 --mem 200G','--mem 240G'),
               ('expanse','run','-A yun124 -p compute -c 128','--mem 240G'),('expanse','run','-A yun124 -p compute --mem 240G','-c is required'),
               ('expanse','run',EXP_RUN+' -p compute','twice'),('expanse','merge','-A yun124 -p compute -c 8 --mem 32G','not allowed'),
               ('expanse','merge','-A yun124 -p shared -c 16 --mem 32G','-c 8'),('expanse','merge','-A yun124 -p shared -c 8 --mem 32G -q normal','give no -q'),
               ('symmetry','run','-p defq --exclude=cn112 -c 64 --mem 245G','Intel'),('symmetry','run','-p amdq,defq --exclude=cn112 -c 64 --mem 245G','exactly one'),
               ('symmetry','run','-p amdq -c 64 --mem 245G','cn112'),('symmetry','run','-p amdq --exclude=cn100 -c 64 --mem 245G','cn112'),
               ('symmetry','run','-p amdpreq --exclude=cn112 -c 64 --mem 245G','--requeue'),('symmetry','run','-A zzheng1 -p amdq --exclude=cn112 -c 64 --mem 245G','default account'),
               ('symmetry','merge','-p sharedq -c 8 --mem 32G','2,000 MB'),('symmetry','merge','-p amdq -c 8 --mem 16000M','not allowed'),('symmetry','merge','-p sharedq -c 16 --mem 16000M','-c 8')]
        for site,role,spec,word in cases:
            with self.subTest(spec=spec):
                msg=refuses(64,lambda:ss.resolve(site,role,ss.parse_options(spec,'x'),128 if site=='expanse'else 64));self.assertIn(word,msg)
        self.assertIn('re-plan with --threads 64',refuses(64,lambda:ss.resolve('symmetry','run',ss.parse_options(SYM_RUN,'x'),32)))
        for bad in ('12:00','1:2:3','24:60:00','0:00:00','abc'):refuses(64,ss.wall_seconds,bad)
        self.assertEqual(ss.wall_seconds('1-00:00:00'),86400)

    def test_submission_refusals_submit_nothing(self):
        cases=[('expanse',dict(),['--time','49:00:00'],64,'limit'),
               ('symmetry',dict(C8_SBATCH_ARGS='-p amddebugq --exclude=cn112 -c 64 --mem 245G'),['--time','02:00:00'],64,'limit'),
               ('expanse',dict(C8_MERGE_SBATCH_ARGS=''),['--time','01:00:00'],64,'C8_MERGE_SBATCH_ARGS'),
               ('symmetry',dict(C8_MERGE_SBATCH_ARGS='-p sharedq -c 8 --mem 20000M'),['--time','01:00:00'],64,'2,000 MB'),
               ('expanse',dict(C8_SBATCH_ARGS=EXP_RUN+' -q debug'),['--time','01:00:00'],64,'-q'),
               ('symmetry',dict(C8_SBATCH_ARGS='-p defq --exclude=cn112 -c 64 --mem 245G'),['--time','01:00:00'],64,'Intel'),
               ('symmetry',dict(C8_AMD_CAP=''),['--time','01:00:00'],64,'C8_AMD_CAP'),('expanse',dict(C8_SITE='pi'),['--time','01:00:00'],64,'C8_SITE'),
               ('expanse',dict(C8_ENV_SETUP=''),['--time','01:00:00'],64,'C8_ENV_SETUP'),('expanse',dict(),[],64,'--time')]
        for site,kw,extra,code,word in cases:
            with self.subTest(site=site,kw=kw):
                run=campaign(threads=128 if site=='expanse'else 64);log=F['T']/f'log_{time.time_ns()}';st=slurm()
                cp=submit(['runners',run,'--nodes',1,*extra],submit_env(site,st,log,**kw));self.assertEqual(cp.returncode,code,cp.stderr);self.assertIn(word,cp.stderr)
                self.assertFalse([c for c in calls(log,'sbatch')if '--parsable'in c['args']])
        run=campaign(threads=128,backend='decimal');log=F['T']/'log_dec';cp=submit(['runners',run,'--nodes',1,'--time','01:00:00'],submit_env('expanse',slurm(),log))
        self.assertEqual(cp.returncode,64);self.assertIn('backend',cp.stderr);self.assertFalse(calls(log,'sbatch'))
        run=campaign(threads=128);m=load(run/'manifest.json');m['tool_sha256']['production.py']='0'*64;(run/'manifest.json').unlink();dump(run/'manifest.json',m)
        cp=submit(['runners',run,'--nodes',1,'--time','01:00:00'],submit_env('expanse',slurm(),F['T']/'log_pin'));self.assertEqual(cp.returncode,64);self.assertIn('pinned tools',cp.stderr)

    def test_preflight_refusal_submits_nothing(self):
        need('seedtool')
        for role in ('run','merge'):
            run=campaign(threads=128);log=F['T']/f'log_pre_{role}';cp=submit(['runners',run,'--nodes',1,'--time','01:00:00'],submit_env('expanse',slurm(),log,FAKE_TESTONLY_FAIL=role))
            self.assertEqual(cp.returncode,64,cp.stderr);self.assertIn('--test-only',cp.stderr)
            self.assertFalse([c for c in calls(log,'sbatch')if '--parsable'in c['args']])

# ================================================================ environment scrubbing and the UNKNOWN path
class Scrubbing(unittest.TestCase):
    def test_forged_sbatch_environment_is_ignored_and_recorded(self):
        need('seedtool')
        run=campaign(threads=128,groups=(('a_free_L8',2),));log=F['T']/'log_forged';st=slurm()
        env=submit_env('expanse',st,log,SBATCH_PARTITION='defq',SBATCH_ACCOUNT='other',SALLOC_PARTITION='debug',SLURM_CLUSTERS='other',SBATCH_CLUSTERS='other',SLURM_JOB_ID='99',SBATCH_EXCLUSIVE='1',
                       SLURM_CONF='/cm/fake/etc/slurm.conf',FAKE_PREEMPTS='1')
        cp=submit(['runners',run,'--nodes',2,'--time','02:00:00'],env);self.assertEqual(cp.returncode,0,cp.stderr)
        self.assertIn('ignoring inherited',cp.stderr)
        sb=calls(log,'sbatch');self.assertTrue(sb)
        for c in sb:self.assertEqual((c['scrubbed_env'],c['SLURM_CONF']),([],'/cm/fake/etc/slurm.conf'),c)  # SLURM_CONF kept: Expanse needs it
        sub=[c for c in sb if '--parsable'in c['args']];runs=[c for c in sub if c['args'][-1].endswith('node_runner.sh')];merges=[c for c in sub if c['args'][-1].endswith('merge.sh')]
        self.assertEqual((len(runs),len(merges)),(2,1))
        for c in runs:self.assertIn('--partition=compute',c['args']);self.assertIn('--open-mode=append',c['args']);self.assertEqual(c['C8_RUN'],str(run.resolve()))
        self.assertEqual(merges[0]['C8_MERGE_WORKERS'],'8');self.assertEqual(merges[0]['C8_ENV_SETUP'],str(F['envfile']))
        jobs=json.loads(st.read_text())['jobs'];rid=[j['jobid']for j in jobs if j['name']=='c8d2-ind-run']
        self.assertIn(f'--dependency=afterany:{":".join(rid)}',merges[0]['args'])
        for j in jobs:self.assertEqual(j['comment'],nr.campaign_comment(run))
        sc=subprocess.run(['scontrol','show','job',rid[0]],capture_output=True,text=True,env=env);self.assertIn('Partition=compute',sc.stdout)
        rec=[json.loads(x)for x in (run/'site_submissions.jsonl').read_text().splitlines()][-1]
        self.assertTrue({'SBATCH_PARTITION','SALLOC_PARTITION','SLURM_CLUSTERS','SBATCH_CLUSTERS','SLURM_JOB_ID'}<=set(rec['ignored_environment']))
        self.assertNotIn('SLURM_CONF',rec['ignored_environment'])
        self.assertIn('to start at',rec['preflight']['run']);self.assertIn('Preempts',rec['preflight']['run'])  # the estimate survives a trailing line
        self.assertEqual(rec['runner_ids'],rid)

    def test_inherited_squeue_filters_cannot_hide_jobs(self):
        need('seedtool')
        st=slurm([job(101+k,'c8d2-lanes',comment='c8:other:lane')for k in range(3)]);log=F['T']/'log_names'
        direct=subprocess.run(['squeue','-h','-o','%i','-u',ME],capture_output=True,text=True,env=base_env(st,log,SQUEUE_NAMES='nomatch'))
        self.assertEqual(direct.stdout.strip(),'')  # the shim honours SQUEUE_NAMES: an unscrubbed query would see no job
        run=campaign(threads=128,groups=(('a_free_L8',2),))
        cp=submit(['runners',run,'--nodes',2,'--time','01:00:00'],submit_env('expanse',st,log,SQUEUE_NAMES='nomatch',SQUEUE_STATES='PD',SQUEUE_ACCOUNT='x',SQUEUE_CLUSTERS='x'))
        self.assertEqual(cp.returncode,65,cp.stderr);self.assertIn('nodes on compute',cp.stderr)
        for c in calls(log,'squeue')[1:]:self.assertEqual(c['scrubbed_env'],[],c)
        self.assertFalse([c for c in calls(log,'sbatch')if '--parsable'in c['args']])

    def test_unknown_scheduler_state_refuses(self):
        need('seedtool')
        for kw,word in ((dict(FAKE_SQUEUE_FAIL=1),'UNKNOWN'),(dict(FAKE_SQUEUE_GARBAGE=1),'does not parse')):
            run=campaign(threads=128);log=F['T']/f'log_u{time.time_ns()}';cp=submit(['runners',run,'--nodes',1,'--time','01:00:00'],submit_env('expanse',slurm(),log,**kw))
            self.assertEqual(cp.returncode,69,cp.stderr);self.assertIn(word,cp.stderr);self.assertFalse(calls(log,'sbatch'))
        refuses(69,records,[job(1,'my|odd|name',comment='a')])  # one of the user's own jobs whose name cannot be told
        self.assertEqual(records([job(2,'x|y',user='other',comment='c|d')])[0]['name'],None)  # another user's: fixed fields suffice
        e=base_env(slurm(),F['T']/'log_x',FAKE_SQUEUE_FAIL=1);refuses(69,nr.time_left,e,'7')

    def test_completing_session_job_refuses_69(self):
        need('seedtool')
        st=slurm([job(301,'c8d2-lanes',state='COMPLETING')]);run=campaign(threads=128);log=F['T']/'log_cg'
        cp=submit(['runners',run,'--nodes',1,'--time','01:00:00'],submit_env('expanse',st,log));self.assertEqual(cp.returncode,69,cp.stderr);self.assertIn('settled',cp.stderr)
        refuses(69,ss.admission,'symmetry',records([job(302,'c8d3-lane-x',state='PREEMPTED',partition='amdq',account=None)]),ME,1,{'C8_AMD_CAP':'3','C8_AMD_POOL_TOTAL':'12'})
        # an uncertain job that is never counted does not refuse
        ss.admission('symmetry',records([job(303,'sri-570610',state='COMPLETING',partition='amdq',account=None)]),ME,1,{'C8_AMD_CAP':'3','C8_AMD_POOL_TOTAL':'12'})

# ================================================================ admission arithmetic and locks
class Admission(unittest.TestCase):
    def test_expanse_limits(self):
        E={'C8_EXP_NODES':'1000'};mine=lambda n,**k:[job(1000+i+k.pop('base',0),'c8d2-lanes',**k)for i in range(n)]
        ok=lambda rs,n,E=E:ss.admission('expanse',records(rs),ME,n,E)
        r=ok(mine(10),1);self.assertEqual(r['limits']['session c8d2-* normal-QOS running']['counted'],10)
        self.assertIn('session c8d2-* normal-QOS running',refuses(65,ok,mine(10)+mine(1,base=50,state='PENDING'),2))
        ok(mine(26,state='PENDING',nodes=0),1);refuses(65,ok,mine(27,state='PENDING',nodes=0),1)
        ok(mine(2),2,{});msg=refuses(65,ok,mine(3),2,{});self.assertIn('Largest admissible --nodes now: 1',msg);self.assertIn('C8_EXP_NODES',msg)
        self.assertEqual(ok(mine(2),2,{})['limits']['session c8d2-* nodes on compute/debug (C8_EXP_NODES)']['counted'],2)
        ok(mine(1,partition='debug'),3,{});refuses(65,ok,mine(1,partition='debug'),4,{});ok(mine(3),5,{'C8_EXP_NODES':'8'})
        user=[job(2000+i,'sdpb-x',state='RUNNING')for i in range(20)];ok(user,2);self.assertIn(f'user {ME} normal-QOS running',refuses(65,ok,user,3))
        acct=[job(3000+i,'other',user='colleague')for i in range(30)];ok(acct,2);self.assertIn('account yun124 normal-QOS running',refuses(65,ok,acct,3))
        ok([job(3100+i,'other',user='colleague',state='PENDING')for i in range(40)],2)  # pending jobs of others never count as running
        shared=[job(4000+i,'c8d2-merge',partition='shared',qos='shared-normal',state='PENDING')for i in range(31)];ok(shared,1)
        self.assertIn('merge itself does not fit',refuses(65,ok,shared+[job(4100,'c8d2-merge',partition='shared',qos='shared-normal')],1))
        ok([job(5000+i,'c8d3-lane',user=ME)for i in range(11)],2)  # C63d's c8d3-* share is its own
        self.assertEqual(ok([],0)['new_runners'],0)

    def test_symmetry_share_and_pool_total(self):
        E={'C8_AMD_CAP':'3','C8_AMD_POOL_TOTAL':'12'};c3=lambda n,b=0:[job(6000+b+i,'c8d3-lane-1-x',partition='amdq',account=None)for i in range(n)]
        ok=lambda rs,n:ss.admission('symmetry',records(rs),ME,n,E)
        r=ok(c3(9)+[job(6100,'sri-570610',partition='amdq',account=None),job(6101,'c8d2-ind-merge',partition='sharedq',account=None)],3)
        self.assertEqual(r['limits']['c8d2-* and c8d3-* AMD-pool nodes (C8_AMD_POOL_TOTAL)']['counted'],9);self.assertEqual(len(r['listed_not_counted']),2)
        self.assertIn('C8_AMD_CAP',refuses(65,ok,c3(9),4))
        self.assertIn('C8_AMD_POOL_TOTAL',refuses(65,ok,c3(10),3))
        mine=[job(6200,'c8d2-lanes',partition='amdpreq',account=None,state='PENDING'),job(6201,'c8d2-ind-run',partition='amddebugq,amdq',account=None)]
        ok(c3(8)+mine,1);refuses(65,ok,c3(8)+mine,2)
        for k in ('C8_AMD_CAP','C8_AMD_POOL_TOTAL'):refuses(64,ss.admission,'symmetry',[],ME,1,{**E,k:''})

    def test_second_campaign_against_the_development_cap(self):
        need('seedtool')
        st=slurm();log=F['T']/'log_dev';a=campaign(threads=128,groups=(('a_free_L8',3),));b=campaign(threads=128,groups=(('a_free_L8',3),))
        cp=submit(['runners',a,'--nodes',3,'--time','01:00:00'],submit_env('expanse',st,log));self.assertEqual(cp.returncode,0,cp.stderr)
        cp=submit(['runners',b,'--nodes',2,'--time','01:00:00'],submit_env('expanse',st,log));self.assertEqual(cp.returncode,65,cp.stderr)
        self.assertIn('C8_EXP_NODES',cp.stderr);self.assertIn('Largest admissible --nodes now: 1',cp.stderr)
        cp=submit(['runners',b,'--nodes',1,'--time','01:00:00'],submit_env('expanse',st,log));self.assertEqual(cp.returncode,0,cp.stderr)

    def test_concurrent_requests_serialize_on_the_site_lock(self):
        need('seedtool')
        st=slurm();log=F['T']/'log_conc';home=F['T']/'home_conc';home.mkdir()
        runs=[campaign(threads=128,groups=(('a_free_L8',3),))for _ in range(2)]
        procs=[subprocess.Popen([PY,'-B',str(ROOT/'tools/site_submit.py'),'runners',str(r),'--nodes','3','--time','01:00:00'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                env=submit_env('expanse',st,log,home=home,FAKE_SBATCH_DELAY='0.4'))for r in runs]
        out=[p.communicate(timeout=180)for p in procs];codes=sorted(p.returncode for p in procs)
        self.assertEqual(codes,[0,65],out)
        self.assertEqual(sum(j['name']=='c8d2-ind-run'for j in json.loads(st.read_text())['jobs']),3)
        self.assertFalse((home/'.c8_site_expanse.lock').exists())

    def test_held_locks_refuse_75(self):
        need('seedtool')
        run=campaign(threads=128);st=slurm();log=F['T']/'log_lock';home=F['T']/'home_lock';(home/'.c8_site_expanse.lock').mkdir(parents=True)
        (home/'.c8_site_expanse.lock/owner.json').write_text('{"host": "elsewhere", "pid": 1}')
        old=ss.SITE_LOCK_WAIT;ss.SITE_LOCK_WAIT=0.6
        try:
            t0=time.time();code=ss.main(['runners',str(run),'--nodes','1','--time','01:00:00'],submit_env('expanse',st,log,home=home))
            self.assertEqual(code,75);self.assertGreaterEqual(time.time()-t0,0.5)
        finally:ss.SITE_LOCK_WAIT=old
        self.assertTrue((home/'.c8_site_expanse.lock').exists())  # never broken
        self.assertFalse(calls(log,'squeue')or[c for c in calls(log,'sbatch')if '--parsable'in c['args']])
        (run/nr.CAMPAIGN_LOCK).mkdir();cp=submit(['runners',run,'--nodes',1,'--time','01:00:00'],submit_env('expanse',st,log))
        self.assertEqual(cp.returncode,75,cp.stderr);(run/nr.CAMPAIGN_LOCK).rmdir()

    def test_live_campaign_jobs_add_and_merge(self):
        need('seedtool')
        run=campaign(threads=128,groups=(('a_free_L8',4),));st=slurm();log=F['T']/'log_add';env=submit_env('expanse',st,log)
        self.assertEqual(submit(['runners',run,'--nodes',1,'--time','01:00:00'],env).returncode,0)
        jobs=json.loads(st.read_text())['jobs'];merge=[j for j in jobs if j['name']=='c8d2-ind-merge'][0];r1=[j['jobid']for j in jobs if j['name']=='c8d2-ind-run']
        cp=submit(['runners',run,'--nodes',1,'--time','01:00:00','--add'],env);self.assertEqual(cp.returncode,65);self.assertIn('merge job',cp.stderr)
        merge['state']='CANCELLED';st.write_text(json.dumps({'jobs':jobs,'next':json.loads(st.read_text())['next']}))
        cp=submit(['runners',run,'--nodes',1,'--time','01:00:00'],env);self.assertEqual(cp.returncode,65);self.assertIn('--add',cp.stderr)
        cp=submit(['runners',run,'--nodes',1,'--time','01:00:00','--add'],env);self.assertEqual(cp.returncode,0,cp.stderr)
        jobs=json.loads(st.read_text())['jobs'];r=[j['jobid']for j in jobs if j['name']=='c8d2-ind-run'];self.assertEqual(len(r),2)
        last=[c for c in calls(log,'sbatch')if '--parsable'in c['args']and c['args'][-1].endswith('merge.sh')][-1]
        self.assertIn(f'--dependency=afterany:{r1[0]}:{r[1]}',last['args'])
        cp=submit(['runners',run,'--nodes',3,'--time','01:00:00','--add','--dry-run'],env);self.assertEqual(cp.returncode,65)  # a live merge again
        for j in jobs:j['state']='COMPLETED'
        st.write_text(json.dumps({'jobs':jobs,'next':9000}));n=len(calls(log,'sbatch'))
        cp=submit(['runners',run,'--nodes',5,'--time','01:00:00','--dry-run'],env);self.assertEqual(cp.returncode,64);self.assertIn('eligible',cp.stderr)
        cp=submit(['runners',run,'--nodes',2,'--time','01:00:00','--dry-run'],env);self.assertEqual(cp.returncode,0,cp.stderr);self.assertIn('dry run',cp.stdout)
        self.assertFalse([c for c in calls(log,'sbatch')[n:]if '--parsable'in c['args']])

    def test_partial_submission_failure_reports_accepted_jobs(self):
        need('seedtool')
        run=campaign(threads=128,groups=(('a_free_L8',3),));st=slurm();log=F['T']/'log_part'
        cp=submit(['runners',run,'--nodes',3,'--time','01:00:00'],submit_env('expanse',st,log,FAKE_SBATCH_FAIL_AT=2))
        self.assertEqual(cp.returncode,1,cp.stderr);self.assertIn('accepted so far',cp.stderr)
        rec=[json.loads(x)for x in (run/'site_submissions.jsonl').read_text().splitlines()][-1];self.assertEqual(len(rec['runner_ids']),2);self.assertIsNone(rec['merge_id'])

# ================================================================ the bidirectional classifier check (V2-01)
CLASSIFY_OURS=r'''import json,sys,types
sys.path.insert(0,sys.argv[1]);import slurm_submit as s
site=sys.argv[2];user='zzheng8'if site=='expanse'else'zzheng1';s.scheduler_user=lambda:user
import os
caps={'C8_EXP_RUNNING':11,'C8_EXP_SUBMITTED':27,'C8_EXP_ACCOUNT_RUNNING':32,'C8_EXP_NODES':4,'C8_EXP_SHARED':32}
c=types.SimpleNamespace(site_name=site,env=dict(os.environ),caps=caps,admission_ref=None,amd_cap=12 if site=='symmetry'else None,
    partitions=lambda role=None:(['compute']if site=='expanse'else['amdq'])if role=='lane'else(['shared']if site=='expanse'else['sharedq']),account=lambda role=None:'yun124'if site=='expanse'else None)
import io,contextlib
out=io.StringIO()
with contextlib.redirect_stdout(out):rec=s.admission(c,[('lane',0),('merge',1)],'lanes')
print(json.dumps(rec))
'''
CLASSIFY_C63D=r'''import json,sys,types
sys.path.insert(0,sys.argv[1]);import budget,slurm_submit as s
site=sys.argv[2];prof=budget.EXPANSE if site=='expanse'else budget.SYMMETRY
snap=budget.Snapshot(budget.parse_account(open(sys.argv[3]).read(),prof),[],[],[],prof)
ev=types.SimpleNamespace(slot_extras=lambda unresolved:({},{}))
print(json.dumps(s.counts(snap,ev,{})))
'''
ACCT_KEYS=('jobid','base','user','partition','qos','state','name','nodes','cpus','minmem','timelimit','reason','comment')

class Bidirectional(unittest.TestCase):
    def snapshot(self,site):
        u='zzheng8'if site=='expanse'else'zzheng1';p='compute'if site=='expanse'else'amdq';a='yun124'if site=='expanse'else None;c='c8ind:c8:0123456789ab'
        return [job(8001,'c8d2-ind-run',user=u,partition=p,account=a,comment=c),job(8002,'c8d2-ind-run',user=u,partition=p,account=a,comment=c),
                job(8003,'c8d2-ind-run',state='PENDING',user=u,partition=p,account=a,comment=c),
                job(8004,'c8d2-ind-merge',state='PENDING',user=u,partition='shared'if site=='expanse'else'sharedq',qos='shared-normal'if site=='expanse'else'normal',account=a,comment=c)]
    def port(self,site,rs):
        rec=ss.admission(site,[dict(nr.parse_record('|'.join(str(r[k])if r.get(k)is not None else'(null)'for k in('jobid','state','partition','qos','nodes','user','left','comment','name')),r['user'],'t'))for r in rs],
                         rs[0]['user'],0,{'C8_AMD_CAP':'12','C8_AMD_POOL_TOTAL':'12'})
        return rec['limits']
    def theirs(self,code,tools,site,rs,extra=()):
        st=slurm(rs);e=base_env(st,F['T']/'log_bidi')
        cp=subprocess.run([PY,'-B','-c',code,str(tools),site,*map(str,extra)],capture_output=True,text=True,env=e,timeout=120,cwd=str(F['T']))
        self.assertEqual(cp.returncode,0,cp.stderr[-2000:]);return json.loads(cp.stdout.strip().splitlines()[-1])
    def acct_text(self,rs):
        return ''.join('|'.join({'base':r['jobid'],'cpus':'128','minmem':'240G','timelimit':'1:00:00','reason':'None'}.get(k,str(r.get(k)if r.get(k)is not None else'(null)'))for k in ACCT_KEYS)+'\n'for r in rs)
    def test_expanse(self):
        need('ours','c63d');rs=self.snapshot('expanse');lim=self.port('expanse',rs)
        self.assertEqual((lim['session c8d2-* normal-QOS submitted']['counted'],lim['session c8d2-* normal-QOS running']['counted'],
                          lim['session c8d2-* nodes on compute/debug (C8_EXP_NODES)']['counted'],lim['session c8d2-* shared-partition jobs']['counted']),(3,2,3,1))
        ours=self.theirs(CLASSIFY_OURS,F['ours'],'expanse',rs)
        self.assertEqual((ours['my_submitted_normal'],ours['my_running_normal'],ours['my_compute_nodes_live'],ours['my_shared_live']),(3,2,3,1),ours)
        f=F['T']/'acct_exp.txt';f.write_text(self.acct_text(rs));c=self.theirs(CLASSIFY_C63D,F['c63d'],'expanse',rs,[f])['detectors']
        self.assertEqual((sorted(c['c8d2_live']),sorted(c['c8d2_run']),c['foreign']),(['8001','8002','8003'],['8001','8002'],[]),c)
    def test_symmetry(self):
        need('ours','c63d');rs=self.snapshot('symmetry');lim=self.port('symmetry',rs)
        self.assertEqual(lim['session c8d2-* AMD-pool nodes (C8_AMD_CAP)']['counted'],3)
        ours=self.theirs(CLASSIFY_OURS,F['ours'],'symmetry',rs);self.assertEqual((ours['amd_live'],sorted(ours['amd_live_jobs'])),(3,['8001','8002','8003']),ours)
        f=F['T']/'acct_sym.txt';f.write_text(self.acct_text(rs));c=self.theirs(CLASSIFY_C63D,F['c63d'],'symmetry',rs,[f])['detectors']
        self.assertEqual((sorted(c['c8d2_amd']),c['c8d2_amd_nodes']),(['8001','8002','8003'],3),c)

# ================================================================ claims, history, identity, signals
GROUPS6=(('a_free_L3',1),('a_power_L8',1),('a_free_L8',2),('b_free_L8',1),('b_power_L7',1))

class Claims(unittest.TestCase):
    def test_order_done_identity_publish_and_match(self):
        run=campaign(groups=GROUPS6);env=base_env(slurm(),F['T']/'log_c1')
        cp=runner(run,env);self.assertEqual(cp.returncode,0,cp.stderr+cp.stdout)
        # loop descending, free before power, then shard (then campaign): a_free_L8 s0, b_free_L8 s0, a_free_L8 s1, a_power_L8, b_power_L7, a_free_L3
        self.assertEqual(started(run),[2,4,3,1,5,0])
        for i in range(6):
            self.assertTrue(nr.marker(run,'done',i).exists());h=nr.read_attempts(run,i);self.assertEqual([x['outcome']for x in h],['done'])
            self.assertEqual((h[0]['blocks_before'],h[0]['blocks_after'],h[0]['rc']),(0,h[0]['blocks'],0));self.assertTrue(Path(h[0]['log']).exists())
        self.assertFalse(list((run/'claims').iterdir()));ident=load(run/'site_identity.json')
        self.assertEqual(set(ident['libraries']),{'libquadmath.so.0','libgmp.so.10'});self.assertIn('node_hours=',cp.stdout);self.assertIn('identity published',cp.stdout)
        cp=runner(run,env,job_id='7002');self.assertEqual(cp.returncode,0,cp.stderr);self.assertIn('identity match',cp.stdout);self.assertEqual(len(started(run)),6)
        st=json.loads(subprocess.run([PY,'-B',str(ROOT/'tools/node_runner.py'),'status',str(run),'--json'],capture_output=True,text=True,env=env).stdout)
        self.assertEqual((len(st['done']),st['exhausted'],st['remaining']),(6,[],[]))

    def test_identity_mismatch_refuses_before_any_claim(self):
        word={'vendor':'mismatch','library':'mismatch','ldd':'ldd','preload':'LD_PRELOAD','tunables':'GLIBC_TUNABLES','missing':'not found','abs':'abs:'}
        for what in ('vendor','library','ldd','preload','tunables','missing','abs'):  # IR2-001: the last four
            run=campaign(groups=GROUPS6);env=base_env(slurm(),F['T']/'log_id')
            if what=='vendor':dump(run/'site_identity.json',{'schema':nr.IDENTITY_SCHEMA,'vendor':'GenuineOtherVendor','libraries':{'libgmp.so.10':'x'},'job':'1','host':'elsewhere'})
            elif what=='library':
                self.assertEqual(runner(run,env,job_id='7100').returncode,0);(run/'done').rename(run/'done_old');lib=F['T']/'libgmp.so.10'
                env=dict(env,FAKE_LDD_LIBS=f'{F["libs"][0]}:{F["T"]/"other"/"libgmp.so.10"}');(F['T']/'other').mkdir(exist_ok=True);(F['T']/'other/libgmp.so.10').write_bytes(b'another gmp')
            elif what=='ldd':env=dict(env,FAKE_LDD_FAIL='1')
            elif what=='preload':env=dict(env,LD_PRELOAD=str(F['T']/'no_such_interposer.so'))
            elif what=='tunables':env=dict(env,GLIBC_TUNABLES='glibc.cpu.hwcaps=-AVX2_Usable')
            elif what=='missing':env=dict(env,FAKE_LDD_MISSING='libinterposer.so.1')
            else:  # an absolute-path entry (a system-wide preload) that the published identity did not have
                self.assertEqual(runner(run,env,job_id='7100').returncode,0);(run/'done').rename(run/'done_old')
                pre=F['T']/'preload_lib.so';pre.write_bytes(b'interposer');env=dict(env,FAKE_LDD_ABS=str(pre))
            n=len(started(run));cp=runner(run,env,job_id='7101')
            with self.subTest(what=what):
                self.assertEqual(cp.returncode,64,cp.stderr+cp.stdout);self.assertIn(word[what],cp.stderr)
                self.assertEqual(len(started(run)),n);self.assertFalse(list((run/'claims').iterdir())if (run/'claims').exists()else[])
                if what=='vendor':self.assertFalse((run/'runner_logs').exists()or(run/'attempts').exists())

    def test_exhausted_across_submissions_and_retry(self):
        run=campaign(groups=(('a_free_L8',3),));(run/'fake_control.json').write_text(json.dumps({'fail':['1']}));env=base_env(slurm(),F['T']/'log_ex')
        cp=runner(run,env,job_id='7201');self.assertEqual(cp.returncode,1,cp.stderr);self.assertEqual(started(run),[0,1,2])
        self.assertEqual(nr.failures(nr.read_attempts(run,1)),1);self.assertFalse(nr.marker(run,'exhausted',1).exists())
        runner(run,env,job_id='7202');self.assertEqual(started(run),[0,1,2,1]);self.assertTrue(nr.marker(run,'exhausted',1).exists())
        runner(run,env,job_id='7203');self.assertEqual(started(run),[0,1,2,1])  # exhausted: never launched again
        cp=subprocess.run([PY,'-B',str(ROOT/'tools/node_runner.py'),'retry',str(run),'--index','1','--reason','test'],capture_output=True,text=True,env=env)
        self.assertEqual(cp.returncode,0,cp.stderr);self.assertTrue(json.loads(cp.stdout)['was_exhausted']);self.assertFalse(nr.marker(run,'exhausted',1).exists())
        runner(run,env,job_id='7204');self.assertEqual(started(run)[-1],1);self.assertFalse(nr.marker(run,'exhausted',1).exists())  # launched again
        runner(run,env,job_id='7205');self.assertEqual(started(run).count(1),4);self.assertTrue(nr.marker(run,'exhausted',1).exists())
        h=[x['outcome']for x in nr.read_attempts(run,1)];self.assertEqual(h,['failed','failed','reset','failed','failed'])
        t=nr.take_claim(run,1,nr.owner_record('7999',0,'test'));refuses(75,nr.retry,run,1,'held');self.assertTrue(nr.drop_claim(run,1,t))

    def test_stale_release_history_and_requeue_self_release(self):
        need('seedtool')
        run=campaign(groups=(('a_free_L8',6),));env=base_env(slurm(),F['T']/'log_rel')
        for i in range(6):nr.append_attempt(run,i,{'outcome':'partial','job':'old','utc':'2026-10-08T00:00:00Z'})
        owners={0:'201',1:'202',2:'203',4:'300'}
        for i,j in owners.items():nr.take_claim(run,i,nr.owner_record(j,0,'test'))
        nr.take_claim(run,5,nr.owner_record(None,0,'test'));os.utime(nr.claim_dir(run,5),(time.time()-3600,)*2)
        st=slurm([job(201,'c8d2-ind-run'),job(202,'c8d2-ind-run',state='COMPLETED'),job(300,'c8d2-ind-run'),job(204,'c8d2-ind-run',state='COMPLETING')])
        e=base_env(st,F['T']/'log_rel2');t3=nr.take_claim(run,3,nr.owner_record('204',0,'test'))
        cp=submit(['release',run],e);self.assertEqual(cp.returncode,69,cp.stderr)  # an owner in COMPLETING: nothing released
        self.assertEqual(sorted(nr.claims_of(run)),[0,1,2,3,4,5]);self.assertTrue(nr.drop_claim(run,3,t3))
        cp=submit(['release',run],e);self.assertEqual(cp.returncode,0,cp.stderr);r=json.loads(cp.stdout)
        self.assertEqual((r['released'],r['kept_live']),([1,2,5],[0,4]));self.assertEqual(sorted(nr.claims_of(run)),[0,4])
        for i in (1,2,5):self.assertEqual([x['outcome']for x in nr.read_attempts(run,i)],['partial','released'])
        self.assertEqual([x['outcome']for x in nr.read_attempts(run,0)],['partial'])
        cp=runner(run,dict(env,FAKE_SLURM=str(st)),job_id='300',restart=1);self.assertEqual(cp.returncode,0,cp.stderr)
        self.assertIn('earlier incarnation',cp.stdout);h=nr.read_attempts(run,4);self.assertEqual([x['outcome']for x in h],['partial','released','done'])
        self.assertEqual(sorted(started(run)),[1,2,3,4,5])  # 0 stays claimed by the live job 201
        self.assertEqual(sorted(nr.claims_of(run)),[0])

    def test_release_never_removes_a_newer_claim(self):
        # IR1-001: the releaser reads claim 0 (owner job 401), 401 finishes and drops it, runner 402 claims 0, then 401
        # ends; a release decided on the old owner record must leave 402's claim alone, and so must 401's late cleanup.
        run=campaign(groups=(('a_free_L8',2),))
        ta=nr.take_claim(run,0,nr.owner_record('401',0,'test'));seen=nr.claims_of(run)
        self.assertTrue(nr.drop_claim(run,0,ta));tb=nr.take_claim(run,0,nr.owner_record('402',0,'test'));self.assertNotEqual(ta,tb)
        r=nr.release_stale(run,[job(401,'c8d2-ind-run',state='COMPLETED'),job(402,'c8d2-ind-run')],seen,'test')
        self.assertEqual((r['released'],r['changed_since_read']),([],[0]));self.assertEqual(nr.claims_of(run)[0]['job'],'402')
        self.assertFalse(nr.drop_claim(run,0,ta));self.assertEqual(nr.claims_of(run)[0]['token'],tb)  # stale token: no-op
        self.assertEqual(nr.read_attempts(run,0),[])  # no `released` line for a claim that was not released
        # requeue self-release likewise checks the token it read: a claim retaken meanwhile under another job stays
        t1=nr.take_claim(run,1,nr.owner_record('403',0,'test'));self.assertEqual(nr.self_release(run,'403',1),[1]);self.assertNotIn(1,nr.claims_of(run))
        self.assertFalse(nr.drop_claim(run,1,t1))
        # a lock left by a killed holder: transitions wait, then refuse 75 without touching the claim
        lk=run/'claims'/nr.CLAIMS_LOCK;lk.mkdir();(lk/'owner.json').write_text('{"host": "elsewhere"}')
        old=nr.CLAIMS_LOCK_WAIT;nr.CLAIMS_LOCK_WAIT=0.3
        try:refuses(75,nr.drop_claim,run,0,tb);refuses(75,nr.take_claim,run,1,nr.owner_record('404',0,'test'))
        finally:nr.CLAIMS_LOCK_WAIT=old;(lk/'owner.json').unlink();lk.rmdir()
        self.assertEqual(sorted(nr.claims_of(run)),[0]);self.assertTrue(nr.drop_claim(run,0,tb))

    def test_term_is_forwarded_and_recorded(self):
        run=campaign(groups=(('a_free_L8',1),),tasks=8,checkpoint_tasks=4);(run/'fake_control.json').write_text(json.dumps({'sleep':30}))
        sc=F['T']/'scratch_term';sc.mkdir()
        env=base_env(slurm(),F['T']/'log_term',C8_PACKAGE=F['pkg'],C8_RUN=run,C8_ENV_SETUP='',C8_PYTHON=PY,SLURM_JOB_ID='7301',SLURM_CPUS_PER_TASK='4',TMPDIR=sc)
        p=subprocess.Popen(['bash',str(ROOT/'slurm/node_runner.sh')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
        t0=time.time()
        while not started(run)and time.time()-t0<60:time.sleep(0.1)
        self.assertEqual(started(run),[0]);time.sleep(0.5);p.send_signal(signal.SIGTERM);out,err=p.communicate(timeout=60)
        self.assertEqual(p.returncode,143,out+err);self.assertIn('forwarding TERM',err)
        self.assertEqual([c['event']for c in fake_calls(run)],['start','term'])
        h=nr.read_attempts(run,0);self.assertEqual([x['outcome']for x in h],['term']);self.assertEqual(h[0]['blocks_after'],0)
        self.assertIn('TERM received',Path(h[0]['log']).read_text())
        self.assertFalse(nr.claim_dir(run,0).exists());self.assertFalse(nr.marker(run,'done',0).exists());self.assertFalse(list((run/'groups/a_free_L8/checkpoints').iterdir()))
        self.assertFalse((sc/'idx0').exists())

# ================================================================ deadline
def deadline_campaign(**kw):
    # one index, 6 blocks of 4 tasks x 80 s at T=4: wall(block) = max(80, 320/(4 x 0.8)) = 100 s
    return campaign(groups=(('a_free_L8',1),),tasks=24,cost=80.,checkpoint_tasks=4,threads=4,cost_model=True,**kw)

class Deadline(unittest.TestCase):
    def test_wall_estimate_and_admissible_blocks(self):
        self.assertEqual(nr.block_wall((4,320.,80.),4),100.);self.assertEqual(nr.block_wall((4,320.,500.),4),500.)
        w=[100.]*6;self.assertEqual(nr.admissible_blocks(w,1200),4);self.assertEqual(nr.admissible_blocks(w,749),0);self.assertEqual(nr.admissible_blocks(w,float('inf')),6)
        for t in ('1:00:00','01:00','45','1-00:00:00'):self.assertIsNotNone(nr.duration(t))
        self.assertEqual(nr.duration('UNLIMITED'),float('inf'));self.assertIsNone(nr.duration('INVALID'))

    def test_max_blocks_partial_progress_skip_and_fresh_runner(self):
        run=deadline_campaign();st=slurm([job(7401,'c8d2-ind-run'),job(7402,'c8d2-ind-run')])
        cp=runner(run,base_env(st,F['T']/'log_dl',FAKE_LEFT_SEQ='00:20:00,10:50'),job_id='7401');self.assertEqual(cp.returncode,0,cp.stderr)
        self.assertEqual([(c['event'],c.get('max_blocks'))for c in fake_calls(run)],[('start',4)]);self.assertIn('skipped in this job',cp.stdout)
        h=nr.read_attempts(run,0);self.assertEqual([(x['outcome'],x['blocks_before'],x['blocks_after'],x['max_blocks'])for x in h],[('partial',0,4,4)])
        self.assertFalse(nr.marker(run,'done',0).exists())
        cp=runner(run,base_env(st,F['T']/'log_dl2',FAKE_LEFT_SEQ='2-00:00:00'),job_id='7402');self.assertEqual(cp.returncode,0,cp.stderr)
        self.assertEqual([c.get('max_blocks')for c in fake_calls(run)],[4,None]);self.assertTrue(nr.marker(run,'done',0).exists())
        self.assertEqual([x['outcome']for x in nr.read_attempts(run,0)],['partial','done'])

    def test_cost_model_order_is_heaviest_remaining_first(self):
        run=campaign(groups=(('a_free_L3',1),('a_free_L8',1),('b_free_L8',1)),tasks=4,cost=lambda g,s,u:{'a_free_L3':50.,'a_free_L8':5.,'b_free_L8':20.}[g],cost_model=True)
        st=slurm([job(7501,'c8d2-ind-run',left='2-00:00:00')]);cp=runner(run,base_env(st,F['T']/'log_ord'),job_id='7501');self.assertEqual(cp.returncode,0,cp.stderr)
        self.assertEqual(started(run),[0,2,1])

    def test_unschedulable_block_refused_parallel_block_admitted(self):
        need('seedtool')
        # 128 parallel tasks of 100 s at T=128: summed 12,800 s > --time, wall max(100, 12800/102.4) = 125 s fits
        par=campaign(groups=(('a_free_L8',1),),tasks=128,cost=100.,checkpoint_tasks=128,threads=128,cost_model=True)
        cp=submit(['runners',par,'--nodes',1,'--time','00:20:00','--dry-run'],submit_env('expanse',slurm(),F['T']/'log_us1'));self.assertEqual(cp.returncode,0,cp.stderr)
        one=campaign(groups=(('a_free_L8',1),),tasks=128,cost=lambda g,s,u:1000. if u==5 else 1.,checkpoint_tasks=128,threads=128,cost_model=True)
        cp=submit(['runners',one,'--nodes',1,'--time','00:20:00'],submit_env('expanse',slurm(),F['T']/'log_us2'));self.assertEqual(cp.returncode,64,cp.stderr)
        self.assertIn('--checkpoint-tasks',cp.stderr);self.assertIn('block 0',cp.stderr)

# ================================================================ seeds
def seed_log(entries=())->Path:
    p=F['T']/f'seeds_{time.time_ns()}.json';p.write_text(json.dumps({'schema':'c8-d2-seeds-1','seeds':[{'seed':s,'source':src}for s,src in entries]},indent=1));return p

class Seeds(unittest.TestCase):
    def setUp(self):need('seedtool');self.env={'C8_SEEDS_TOOL_DIR':str(F['seedtool'])}
    def test_reserve_hit_miss_idempotent_and_derived(self):
        run=campaign(test_only=False,seed=424242424242);S=424242424242;src=nr.seed_source(run)
        log=seed_log([(11,'symmetry run1')]);e={**self.env,'C8_SEEDS':str(log)}
        r=nr.seed_reserve(run,e);self.assertEqual((r['state'],r['added']),('added',1));self.assertIn({'seed':S,'source':src},[{k:x[k]for k in('seed','source')}for x in json.loads(log.read_text())['seeds']])
        r=nr.seed_reserve(run,e);self.assertEqual((r['state'],r['present']),('present',1));self.assertEqual(len(json.loads(log.read_text())['seeds']),2)
        hit=seed_log([(S,'our C8(2) production')]);self.assertIn('base seed',refuses(64,nr.seed_reserve,run,{**self.env,'C8_SEEDS':str(hit)}))
        self.assertEqual(len(json.loads(hit.read_text())['seeds']),1)
        d=sorted(nr.derived(S))[0];self.assertIn('derived seed',refuses(64,nr.seed_reserve,run,{**self.env,'C8_SEEDS':str(seed_log([(d,'x')]))}))
        B=31337;up=campaign(test_only=False,seed=sorted(nr.derived(B))[3])  # its base seed is a derived seed of a logged one
        self.assertIn('derived seed',refuses(64,nr.seed_reserve,up,{**self.env,'C8_SEEDS':str(seed_log([(B,'y')]))}))
        reg=campaign(test_only=False,seed=next(iter(prod.USED_2026)));self.assertIn('registry',refuses(64,nr.seed_reserve,reg,e))
        self.assertIn('never reserved',refuses(64,nr.seed_reserve,campaign(test_only=True),e))
        t=campaign(test_only=True,seed=S);self.assertTrue(nr.seed_check(t,e)['collisions']);self.assertFalse(nr.seed_check(campaign(test_only=True,seed=5),e)['collisions'])
        self.assertEqual(nr.ownership(S,src,json.loads(log.read_text())['seeds']),[])
        self.assertTrue(nr.ownership(S,src,json.loads(log.read_text())['seeds']+[{'seed':S,'source':'other'}]))

    def test_pins_corrupt_log_and_lock_contention(self):
        run=campaign(test_only=False);bad=F['T']/'badtool';bad.mkdir(exist_ok=True)
        for n in ('seeds.py','common.py'):shutil.copy2(F['seedtool']/n,bad/n)
        with open(bad/'seeds.py','a')as f:f.write('\n# edited\n')
        self.assertIn('pinned',refuses(64,nr.seed_tools,{'C8_SEEDS_TOOL_DIR':str(bad)}))
        cor=F['T']/'seeds_corrupt.json';cor.write_text('{"schema": "c8-d2-seeds-1", "seeds": [')
        refuses(64,nr.seed_reserve,run,{**self.env,'C8_SEEDS':str(cor)});refuses(64,nr.seed_check,run,{**self.env,'C8_SEEDS':str(cor)})
        log=seed_log();lock=log.with_name(log.name+'.lock');lock.mkdir();(lock/'owner.json').write_text('{"host": "elsewhere"}')
        sm=nr.seed_tools(self.env);old=sm.LOCK_WAIT;sm.LOCK_WAIT=0.5
        try:self.assertIn('holds',refuses(75,nr.seed_reserve,run,{**self.env,'C8_SEEDS':str(log)}))
        finally:sm.LOCK_WAIT=old
        self.assertEqual(json.loads(log.read_text())['seeds'],[]);self.assertTrue(lock.exists())
        self.assertIn('common',sys.modules);self.assertTrue(hasattr(sys.modules['common'],'fingerprint'))  # this package's common.py is untouched

    def test_submission_receipt_checks(self):
        S=515151515151;run=campaign(test_only=False,seed=S,threads=128);src=nr.seed_source(run);log=seed_log([(S,src)]);st=slurm()
        env=submit_env('expanse',st,F['T']/'log_rc',C8_SEEDS=log)
        def rcpt(**kw):
            d={'schema':nr.RECEIPT_SCHEMA,'seed':S,'owner':src,'site':'expanse','utc':nr.utc(),**kw};(run/'seed_receipt.json').write_text(json.dumps(d))
        def go():return submit(['runners',run,'--nodes',1,'--time','01:00:00','--dry-run'],env)
        cp=go();self.assertEqual(cp.returncode,64);self.assertIn('seed receipt',cp.stderr)
        rcpt(seed=S+1);cp=go();self.assertEqual(cp.returncode,64);self.assertIn('does not belong',cp.stderr)
        rcpt(owner='c8ind:/elsewhere:000000000000');self.assertEqual(go().returncode,64)
        rcpt(utc='2020-01-01T00:00:00Z');cp=go();self.assertEqual(cp.returncode,64);self.assertIn('older than the plan',cp.stderr)
        rcpt();cp=go();self.assertEqual(cp.returncode,0,cp.stderr);self.assertIn('single ownership re-checked',cp.stdout)
        log.write_text(json.dumps({'schema':'c8-d2-seeds-1','seeds':[{'seed':S,'source':src},{'seed':S,'source':'c8ind:/mnt/beegfs/other:abcdefabcdef'}]}))
        cp=go();self.assertEqual(cp.returncode,64);self.assertIn('single owner',cp.stderr)
        t=campaign(test_only=True,seed=S,threads=128);cp=submit(['runners',t,'--nodes',1,'--time','01:00:00','--dry-run'],env)
        self.assertEqual(cp.returncode,64);self.assertIn('test plan seed',cp.stderr)
        self.assertEqual(json.loads(log.read_text())['seeds'][-1]['source'],'c8ind:/mnt/beegfs/other:abcdefabcdef')  # nothing written

    def test_seed_sync_union_ownership_and_receipt(self):
        tool=F['seedtool'];results={}
        for case,inject,rounds,code in (('converges','once','5',0),('diverges','always','2',1),('owner','','5',0),('conflict','','5',1),('owners','','5',0),('badowner','','5',64)):
            t=F['T']/f'sync_{case}';sites=t/'sites';mirror=t/'mirror/forbidden_seeds.json'
            sym=sites/'symmetry/mnt/beegfs/zzheng1/c8-d2/forbidden_seeds.json';exp=sites/'expanse/expanse/lustre/scratch/zzheng8/temp_project/c8d2/forbidden_seeds.json'
            for h in ('symmetry','expanse'):
                d=sites/h/'home/c8ind/c8d2_seedtool/tools';d.mkdir(parents=True)
                for n in ('seeds.py','common.py'):shutil.copy2(tool/n,d/n)
                (sites/h/'home/c8ind/LRI_C8_D2_HPC_optimized/slurm').mkdir(parents=True);(sites/h/f'home/c8ind/LRI_C8_D2_HPC_optimized/slurm/env_{h}.sh').write_text('')
            rd='/expanse/lustre/scratch/zzheng8/temp_project/c8-d2-indep/runs/pilotT';rl=sites/'expanse'/rd.lstrip('/');rl.mkdir(parents=True)
            (rl/'manifest.json').write_text('{"synthetic": true}\n');S=616161616161;src=f'c8ind:{rd}:{digest(rl/"manifest.json")[:12]}'
            logs={sym:[(11,'sym seed 11'),(22,'sym seed 22')],exp:[(22,'exp seed 22'),(33,'exp seed 33')],mirror:[(22,'mirror 22'),(44,'mirror 44')]}
            if case in('owner','conflict'):logs[exp].append((S,src))
            if case=='conflict':logs[sym].append((S,'c8ind:/mnt/beegfs/zzheng1/c8-d2-indep/runs/other:aaaaaaaaaaaa'))
            if case=='owners':  # IR1-002: equal seed sets, but symmetry alone knows a second owner of seed 22
                base=[(11,'s11'),(22,'s22'),(33,'s33'),(44,'s44')];logs={sym:base+[(22,'second owner of 22')],exp:list(base),mirror:list(base)}
            for p,es in logs.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'schema':'c8-d2-seeds-1','seeds':[{'seed':s,'source':x}for s,x in es]}))
            env={**base_env(slurm(),t/'fake.log'),'FAKE_SITES':str(sites),'FAKE_SSH_LOG':str(t/'ssh.log'),'FAKE_SEEDS_TOOL':str(tool/'seeds.py'),'FAKE_INJECT':inject,
                 'C8_SEEDSYNC_PYTHON':PY,'C8_SEEDSYNC_ROUNDS':rounds,'C8_SEEDS_TOOL_DIR':str(tool),'C8_SEEDS_MIRROR':str(mirror),'C8_SEEDSYNC_OUT':str(t/'out'),'TMPDIR':str(t)}
            args=['--owner',src,'--seed',str(S)]if case in('owner','conflict')else[]
            if case=='badowner':args=['--owner','c8ind:/expanse/x;touch${IFS}'+str(t/'pwned')+';#:aaaaaaaaaaaa','--seed',str(S)]  # IR1-003
            cp=subprocess.run(['bash',str(ROOT/'tools/seed_sync.sh'),*args],capture_output=True,text=True,env=env,timeout=300)
            sets=[{e['seed']for e in json.loads(p.read_text())['seeds']}for p in (sym,exp,mirror)]
            pairs=[{(e['seed'],e['source'])for e in json.loads(p.read_text())['seeds']}for p in (sym,exp,mirror)]
            with self.subTest(case=case):
                self.assertEqual(cp.returncode,code,cp.stdout[-1500:]+cp.stderr[-1500:])
                if case=='badowner':
                    self.assertIn('--owner must be',cp.stderr);self.assertFalse((t/'pwned').exists());self.assertFalse((t/'ssh.log').exists());continue
                if case=='diverges':self.assertIn('still differ',cp.stderr);self.assertIn('lacks',cp.stdout)
                else:self.assertTrue(sets[0]==sets[1]==sets[2]and{11,22,33,44}<=sets[0],sets);self.assertTrue(pairs[0]==pairs[1]==pairs[2],pairs)
                if case=='owners':self.assertIn((22,'second owner of 22'),pairs[1]);self.assertIn('lacks 1',cp.stdout)
                if case=='converges':self.assertIn(700001,sets[0])
                receipt=rl/'seed_receipt.json'
                if case=='owner':
                    r=json.loads(receipt.read_text());self.assertEqual((r['seed'],r['owner'],r['schema'],r['site']),(S,src,nr.RECEIPT_SCHEMA,'expanse'))
                    self.assertEqual(set(r['logs']),{'symmetry','expanse','mirror'});self.assertTrue(r['union_sha256'])
                else:self.assertFalse(receipt.exists())
                if case=='conflict':self.assertIn('single owner',cp.stderr)
                self.assertFalse(list(t.glob('c8ind_seedsync.*')))
            results[case]=cp.returncode
        bad=F['T']/'sync_badpin';bad.mkdir();shutil.copy2(tool/'common.py',bad/'common.py');(bad/'seeds.py').write_text('# not ours\n')
        cp=subprocess.run(['bash',str(ROOT/'tools/seed_sync.sh')],capture_output=True,text=True,env={**env,'C8_SEEDS_TOOL_DIR':str(bad)},timeout=60)
        self.assertEqual(cp.returncode,64);self.assertIn('pinned',cp.stderr)

# ================================================================ scripts
class Scripts(unittest.TestCase):
    def test_shell_syntax_and_array_refusal(self):
        for s in ('slurm/node_runner.sh','slurm/site_gate.sh','slurm/env_expanse.sh','slurm/env_symmetry.sh','slurm/submit.sh','slurm/resubmit.sh','tools/seed_sync.sh'):
            cp=subprocess.run(['bash','-n',str(ROOT/s)],capture_output=True,text=True);self.assertEqual(cp.returncode,0,(s,cp.stderr))
        log=F['T']/'log_arr';env=base_env(slurm(),log,C8_PACKAGE=ROOT,C8_RUN=F['T'],C8_ENV_SETUP='',C8_PYTHON=PY)
        for s in ('submit.sh','resubmit.sh'):
            cp=subprocess.run(['bash',str(ROOT/'slurm'/s)],capture_output=True,text=True,env=dict(env,C8_SITE='expanse'))
            self.assertEqual(cp.returncode,64,cp.stderr);self.assertIn('site_submit.py',cp.stderr)
            cp=subprocess.run(['bash',str(ROOT/'slurm'/s)],capture_output=True,text=True,env=dict(env,C8_SITE='expanse',C8_ALLOW_ARRAYS='1'))
            self.assertNotIn('managed site',cp.stderr)
        self.assertFalse(calls(log,'sbatch'))

    def test_gate_helpers_on_shipped_evidence(self):
        cp=subprocess.run(['bash',str(ROOT/'slurm/site_gate.sh'),'--check-replay',str(ROOT/'optimization_work/final_release_comparison')],capture_output=True,text=True,
                          env=dict(os.environ,C8_PYTHON=PY),timeout=300)
        self.assertEqual(cp.returncode,0,cp.stderr);r=json.loads(cp.stdout)
        self.assertTrue(r['passed']and r['equals_sandbox_digest']);self.assertEqual(r['science_digest'][:8],'366421b2')
        a=campaign(groups=(('a_free_L3',1),));(a/'groups/a_free_L3/sobol.bin').write_bytes(b'net');b=F['T']/'plan_copy';shutil.copytree(a,b)
        cp=subprocess.run(['bash',str(ROOT/'slurm/site_gate.sh'),'--compare-plans',str(a),str(b)],capture_output=True,text=True,env=dict(os.environ,C8_PYTHON=PY))
        r=json.loads(cp.stdout);self.assertEqual((r['problems'],r['files_compared']),([],3));self.assertFalse(r['passed'])  # identical, but not 24 groups
        (b/'groups/a_free_L3/config.json').write_text('{}');r=json.loads(subprocess.run(['bash',str(ROOT/'slurm/site_gate.sh'),'--compare-plans',str(a),str(b)],
                                                                                   capture_output=True,text=True,env=dict(os.environ,C8_PYTHON=PY)).stdout)
        self.assertTrue(r['problems'])
        # IR1-004: identical group files, but a manifest key other than `package` differs: AC4 fails
        c=F['T']/'plan_copy2';shutil.copytree(a,c);mc=json.loads((c/'manifest.json').read_text());mc['package']='/elsewhere';mc['test_only']=not mc.get('test_only')
        (c/'manifest.json').write_text(json.dumps(mc));r=json.loads(subprocess.run(['bash',str(ROOT/'slurm/site_gate.sh'),'--compare-plans',str(a),str(c)],
                                                                                capture_output=True,text=True,env=dict(os.environ,C8_PYTHON=PY)).stdout)
        self.assertEqual(r['manifest_keys_differing'],['package','test_only']);self.assertEqual([x for x in r['problems']if'manifest key'in x],[r['problems'][0]])
        self.assertIn("'test_only'",r['problems'][0])
        d=F['T']/'gate_results';d.mkdir();(d/'steps.tsv').write_text('ac1_x\t0\t1\t/l\nac2_y\t1\t2\t/m\n');(d/'check_ac2_replay.json').write_text('{"passed": false}')
        cp=subprocess.run(['bash',str(ROOT/'slurm/site_gate.sh'),'--summary',str(d)],capture_output=True,text=True,env=dict(os.environ,C8_PYTHON=PY))
        r=json.loads(cp.stdout);self.assertEqual((cp.returncode,r['status'],r['failed_steps']),(1,'failed',['ac2_y','check_ac2_replay']));self.assertIn('ac2_replay',r['checks'])
        (d/'steps.tsv').write_text('ac1_x\t0\t1\t/l\n');(d/'check_ac2_replay.json').write_text('')  # an empty check (its step died) is a failure, not a crash
        cp=subprocess.run(['bash',str(ROOT/'slurm/site_gate.sh'),'--summary',str(d)],capture_output=True,text=True,env=dict(os.environ,C8_PYTHON=PY))
        r=json.loads(cp.stdout);self.assertEqual((cp.returncode,r['status'],r['failed_steps']),(1,'failed',['check_ac2_replay']));self.assertIn('unreadable',r['checks']['ac2_replay']['error'])

# ================================================================
def main()->int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path);ap.add_argument('--require-all',action='store_true',help='fail when an optional source is unavailable')
    a=ap.parse_args()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)for c in (Options,Scrubbing,Admission,Bidirectional,Claims,Deadline,Seeds,Scripts))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    ok=result.wasSuccessful()and not(a.require_all and result.skipped)
    report={'schema':'c8ind-site-layer-tests-1','status':'passed'if ok else'failed','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'skipped':{t.id().rsplit('.',2)[-2]+'.'+t.id().rsplit('.',1)[-1]:why for t,why in result.skipped},'sources_unavailable':SKIPPED,'python':sys.version.split()[0],
            'scope':'Pure-logic site-layer checks on synthetic campaigns; sbatch/squeue/scontrol/ldd/ssh/scp are PATH shims. No submission, no native code.'}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
