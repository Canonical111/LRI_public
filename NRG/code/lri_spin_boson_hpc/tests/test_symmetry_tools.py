"""Campaign ownership, packed lanes, submission and export on a shared filesystem.

Slurm is replaced by tests/fake_slurm.py; solver items are tiny, except the
few that must still be running when a stop or token change arrives.
"""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time
import fcntl
import pytest
from lri_spin import Config
from lri_spin.io import identity,source_hash,write_record,read_record
from lri_spin.campaign import (init_campaign,create_owner,replace_owner,read_owner,OwnershipError,resolve_target,
                               item_digest,seed,publish_new)
from lri_spin.manifest import validate_items,validate_item
from lri_spin.workflow import fixed

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import symmetry_lane
from symmetry_common import short_host

TINY=Config(s=.8,Lambda=3.,keep=6,nb=4,nsites=10)
LONG=Config(s=.8,Lambda=3.,keep=64,nb=10,nsites=80)
EMPTY_ROOT=['.campaign','.submit.lock']
UNSAFE=['..','a/b','/abs','../../x','','.hidden','x'*129,'SUBMITTED.jsonl','lanes']


def flow(name,cfg=TINY,alpha=.4,**kw):
    return {'id':name,'kind':'flow','alpha':alpha,'config':cfg.asdict(),'memory_limit_gib':1,**kw}


def env(**extra):
    e=os.environ.copy()
    e.update(PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for k in ('LRI_SPIN_OWNER_TOKEN','LRI_SPIN_STOP_FILE','SLURM_RESTART_COUNT','SLURM_JOB_ID'):e.pop(k,None)
    e.update({k:str(v) for k,v in extra.items()})
    return e


def run(args,timeout=60,**extra):
    return subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=env(**extra),capture_output=True,text=True,timeout=timeout)


def listing(path):
    path=Path(path)
    return sorted(str(p.relative_to(path)) for p in path.rglob('*')) if path.exists() else []


@pytest.fixture
def site(tmp_path):
    s={'login_host':short_host(),'base':str(tmp_path/'base'),'partition':'amdq','exclude':'cn112','mem':'240G',
       'mem_gib':240,'cores':64,'headroom_gib':8,'max_time':'24:00:00','signal':'B:USR1@300','require_frozen':False}
    p=tmp_path/'site.json';p.write_text(json.dumps(s));return p


@pytest.fixture
def slurm(tmp_path,monkeypatch):
    """Fake sbatch/squeue/sacct first on PATH, for subprocesses and in-process calls."""
    bindir=tmp_path/'fakebin';bindir.mkdir();state=tmp_path/'slurm.json'
    for cmd in ('sbatch','squeue','sacct'):
        w=bindir/cmd;w.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT/"tests"/"fake_slurm.py"}" {cmd} "$@"\n');w.chmod(0o755)
    monkeypatch.setenv('PATH',f'{bindir}{os.pathsep}{os.environ["PATH"]}');monkeypatch.setenv('FAKE_SLURM_STATE',str(state))

    class Fake:
        def load(self):return json.loads(state.read_text()) if state.exists() else {'next':1000,'jobs':{},'calls':[],'fail':{}}
        def save(self,st):state.write_text(json.dumps(st))
        def job(self,jid,name,state_,live):
            st=self.load();st['jobs'][str(jid)]={'name':name,'state':state_,'live':live,'args':[]};self.save(st)
        def fail(self,cmd,on=True):
            st=self.load();st['fail'][cmd]=on;self.save(st)
        def submitted(self):
            return [c for c in self.load()['calls'] if c[0]=='sbatch' and '--parsable' in c]
    return Fake()


@pytest.fixture
def receipt(tmp_path):
    ident=identity(Config(),None,'receipt');p=tmp_path/'receipt.json'
    write_record(p,ident,{'passed':True,'source_sha256':source_hash(),'runtime':ident['runtime']})
    return p


def manifest(tmp_path,items,name='manifest.json'):
    p=tmp_path/name;p.write_text(json.dumps({'schema':1,'source_sha256':source_hash(),'items':items}));return p


@pytest.fixture
def campaign(tmp_path):
    root=tmp_path/'campaign';init_campaign(root,short_host());return root


def own(root,name,token='T1',generation=1,item=None,**extra):
    create_owner(root/name,{'token':token,'generation':generation,'job_name':'lrisb-test-0',
                            'created':time.time(),'job_id':extra.pop('job_id','1001'),
                            'item_sha256':item_digest(item or flow(name)),**extra})


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_spec(path,campaign,m,receipt,entries):
    path.write_text(json.dumps({'campaign':str(campaign),'manifest':str(m),'receipt':str(receipt),
                                'manifest_sha256':sha(m),'receipt_sha256':sha(receipt),'items':entries}))


def submit(site,*args):
    return run([ROOT/'scripts/symmetry_submit.py','--site',site,*args],PATH=os.environ['PATH'],FAKE_SLURM_STATE=os.environ['FAKE_SLURM_STATE'])


# ---------------------------------------------------------------- manifest IDs

@pytest.mark.parametrize('bad',UNSAFE)
def test_unsafe_ids_rejected_before_any_write(tmp_path,site,slurm,receipt,campaign,bad):
    with pytest.raises(ValueError):validate_item(flow(bad))
    items=tmp_path/'items.json';items.write_text(json.dumps([flow(bad)]))
    out=tmp_path/'frozen.json'
    r=run([ROOT/'scripts/make_manifest.py','--items',items,'--receipt',receipt,'--output',out])
    assert r.returncode!=0 and not out.exists()
    m=manifest(tmp_path,[flow('ok'),flow(bad)])
    r=submit(site,'submit','--campaign',campaign,'--manifest',m,'--receipt',receipt)
    assert r.returncode!=0 and not slurm.submitted()
    r=run([ROOT/'scripts/symmetry_status.py','--site',site,'--campaign',campaign,'--manifest',m,'--receipt',receipt,'--no-slurm'])
    assert r.returncode!=0
    spec=tmp_path/'spec.json'
    write_spec(spec,campaign,m,receipt,[{'index':1,'id':bad,'token':'T','generation':1}])
    logs=tmp_path/'logs'
    r=run([ROOT/'scripts/symmetry_lane.py','--spec',spec,'--logs',logs,'--cores',2,'--mem-gib',16])
    assert r.returncode!=0 and not logs.exists()
    assert listing(campaign)==EMPTY_ROOT and not (tmp_path/'base').exists()


def test_symlink_item_escaping_root_is_rejected(tmp_path,campaign):
    (tmp_path/'elsewhere').mkdir();(campaign/'esc').symlink_to(tmp_path/'elsewhere')
    with pytest.raises(ValueError):validate_items([flow('esc')],campaign)


# ---------------------------------------------------------------- campaign boundary

def test_campaign_boundary_for_direct_cli(tmp_path,campaign):
    own(campaign,'x',token='T1')
    cmd=['-m','lri_spin','flow','--s',.8,'--Lambda',3,'--keep',6,'--nb',4,'--nsites',10,'--alpha',.4,'--memory-limit-gib',1]
    for target,token in ((campaign/'x',None),(campaign/'x','WRONG'),(campaign/'x'/'deeper','T1'),(campaign,'T1')):
        extra={'LRI_SPIN_OWNER_TOKEN':token} if token else {}
        r=run(cmd+['--output-dir',target],**extra)
        assert r.returncode==76,r.stderr
        assert listing(campaign)==sorted(EMPTY_ROOT+['x','x/.owner'])
    r=run(cmd+['--output-dir',campaign/'x'],LRI_SPIN_OWNER_TOKEN='T1')
    assert r.returncode==0,r.stderr
    assert read_record(campaign/'x'/'g0001'/'result.json')['records']
    # Outside campaign roots nothing changes.
    r=run(cmd+['--output-dir',tmp_path/'plain'])
    assert r.returncode==0 and (tmp_path/'plain'/'result.json').is_file()


def test_cli_item_collides_with_lane_owner(tmp_path,campaign,receipt):
    own(campaign,'a',token='LANE')
    m=manifest(tmp_path,[flow('a')])
    cmd=['-m','lri_spin','item','--manifest',m,'--index',0,'--validation-receipt',receipt,'--output-dir',campaign,'--resume']
    assert run(cmd).returncode==76
    assert run(cmd,LRI_SPIN_OWNER_TOKEN='OTHER').returncode==76
    assert listing(campaign/'a')==['.owner']
    assert run(cmd,LRI_SPIN_OWNER_TOKEN='LANE').returncode==0
    assert (campaign/'a'/'g0001'/'result.json').is_file()


def wait_for(path,proc,timeout=30):
    deadline=time.monotonic()+timeout
    while not Path(path).exists():
        assert proc.poll() is None,proc.stderr.read() if proc.stderr else ''
        assert time.monotonic()<deadline,f'timeout waiting for {path}'
        time.sleep(.02)


def test_token_change_mid_run_stops_without_writing(tmp_path,campaign):
    own(campaign,'x',token='T1')
    cmd=[sys.executable,'-m','lri_spin','flow','--s','.8','--Lambda','3','--keep','64','--nb','10','--nsites','80',
         '--alpha','.4','--memory-limit-gib','1','--output-dir',str(campaign/'x')]
    p=subprocess.Popen(cmd,cwd=ROOT,env=env(LRI_SPIN_OWNER_TOKEN='T1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        state=campaign/'x'/'g0001'/'state.npz';wait_for(state,p)
        replace_owner(campaign/'x',{'token':'T2','generation':2,'job_name':'n','created':time.time(),'job_id':None})
        assert p.wait(timeout=60)==76,p.stderr.read()
        assert not (campaign/'x'/'g0001'/'result.json').exists()
        assert not (campaign/'x'/'g0002').exists()
    finally:
        if p.poll() is None:p.kill();p.wait()


PAUSER='''
import os,sys,time
from pathlib import Path
paused,go=Path(sys.argv[1]),Path(sys.argv[2])
original=os.replace;count=[0]
def replace(a,b,*args,**kw):
    if str(b).endswith('state.npz'):
        count[0]+=1
        if count[0]==2:
            paused.touch()
            while not go.exists():time.sleep(.01)
    return original(a,b,*args,**kw)
os.replace=replace
from lri_spin.cli import main
raise SystemExit(main(sys.argv[3:]))
'''


def snapshot(folder):
    return {str(p.relative_to(folder)):p.read_bytes() for p in folder.rglob('*') if p.is_file() and p.name!='.claim.lock'}


def test_paused_old_writer_cannot_touch_new_generation(tmp_path,campaign):
    """REV-006: generation 1 passes its token check, pauses before os.replace, is superseded, then resumes."""
    cfg=Config(s=.8,Lambda=3.,keep=8,nb=4,nsites=30)
    own(campaign,'x',token='T1')
    driver=tmp_path/'pauser.py';driver.write_text(PAUSER);paused=tmp_path/'paused';go=tmp_path/'go'
    cmd=[sys.executable,str(driver),str(paused),str(go),'flow','--s','.8','--Lambda','3','--keep','8','--nb','4',
         '--nsites','30','--alpha','.4','--memory-limit-gib','1','--output-dir',str(campaign/'x')]
    p=subprocess.Popen(cmd,cwd=ROOT,env=env(LRI_SPIN_OWNER_TOKEN='T1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        wait_for(paused,p)
        # Reclaim (the submitter's step), then the new generation seeds and completes.
        replace_owner(campaign/'x',{'token':'T2','generation':2,'job_name':'n','created':time.time(),'job_id':None})
        new=fixed(.4,cfg,campaign/'x',owner_token='T2',resume=True,memory_limit_gib=1)
        g2=campaign/'x'/'g0002';before=snapshot(g2)
        assert new['resumed_at_site']==8
        go.touch()
        assert p.wait(timeout=60)==76,p.stderr.read()
        assert snapshot(g2)==before
        again=fixed(.4,cfg,campaign/'x',owner_token='T2',resume=True,memory_limit_gib=1)
        assert again['records']==new['records']
        plain=fixed(.4,cfg,tmp_path/'plain',memory_limit_gib=1)
        assert plain['records']==new['records']
    finally:
        go.touch()
        if p.poll() is None:p.kill();p.wait()


# ---------------------------------------------------------------- stop protocol

def test_stop_file_before_start_does_no_work(tmp_path,campaign,receipt):
    stop=tmp_path/'STOP';stop.touch()
    own(campaign,'a',token='T')
    m=manifest(tmp_path,[flow('a')])
    r=run(['-m','lri_spin','item','--manifest',m,'--index',0,'--validation-receipt',receipt,'--output-dir',campaign,'--resume'],
          LRI_SPIN_OWNER_TOKEN='T',LRI_SPIN_STOP_FILE=stop)
    assert r.returncode==75 and listing(campaign/'a')==['.owner']
    r=run(['-m','lri_spin','flow','--alpha',.4,'--keep',6,'--nb',4,'--nsites',10,'--memory-limit-gib',1,
           '--output-dir',tmp_path/'plain'],LRI_SPIN_STOP_FILE=stop)
    assert r.returncode==75 and not (tmp_path/'plain').exists()


def lane_setup(tmp_path,campaign,receipt,items,tokens=None):
    m=manifest(tmp_path,items)
    entries=[]
    for n,item in enumerate(items):
        token=(tokens or {}).get(item['id'],f'tok-{item["id"]}')
        own(campaign,item['id'],token=token,item=item);entries.append({'index':n,'id':item['id'],'token':token,'generation':1})
    spec=tmp_path/'spec.json';write_spec(spec,campaign,m,receipt,entries)
    return spec


@pytest.mark.parametrize('when',['before_popen','after_popen'])
def test_lane_signal_during_launch(tmp_path,campaign,receipt,monkeypatch,when):
    spec=lane_setup(tmp_path,campaign,receipt,[flow('a',LONG),flow('b',LONG)])
    original=symmetry_lane.Lane.spawn

    def spawn(self,entry):
        if when=='before_popen':os.kill(os.getpid(),signal.SIGUSR1)
        proc=original(self,entry)
        if when=='after_popen':os.kill(os.getpid(),signal.SIGUSR1)
        return proc
    monkeypatch.setattr(symmetry_lane.Lane,'spawn',spawn)
    monkeypatch.setenv('SLURM_JOB_ID',f'sig-{when}')
    lane=symmetry_lane.Lane(spec,tmp_path/'logs',cores=2,mem_gib=16,headroom_gib=0)
    assert lane.run()==75
    events=[json.loads(l) for l in (tmp_path/'logs'/f'sig-{when}.r0'/'events.jsonl').read_text().splitlines()]
    starts=[e for e in events if e['event']=='start'];ends=[e for e in events if e['event']=='end']
    assert len(starts)==1 and len(ends)==1 and ends[0]['rc']==75
    first=starts[0]['id'];other='b' if first=='a' else 'a'
    assert listing(campaign/other)==['.owner']
    assert not list((campaign/first).rglob('result.json'))
    if when=='before_popen':assert listing(campaign/first)==['.owner']


def test_lane_stop_then_resubmitted_generation_resumes(tmp_path,site,campaign,receipt):
    spec=lane_setup(tmp_path,campaign,receipt,[flow('a',LONG)])
    logs=tmp_path/'logs'
    p=subprocess.Popen([sys.executable,str(ROOT/'scripts/symmetry_lane.py'),'--spec',str(spec),'--logs',str(logs),
                        '--cores','2','--mem-gib','16','--headroom-gib','0'],cwd=ROOT,env=env(SLURM_JOB_ID='501'),
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        wait_for(campaign/'a'/'g0001'/'state.npz',p)
        p.send_signal(signal.SIGUSR1)
        assert p.wait(timeout=60)==75,p.stderr.read()
    finally:
        if p.poll() is None:p.kill();p.wait()
    assert (logs/'501.r0'/'STOP').exists() and not (campaign/'a'/'g0001'/'result.json').exists()
    # The submitter's reclaim: generation 2 with a fresh token, then a new execution.
    replace_owner(campaign/'a',{'token':'T2','generation':2,'job_name':'n','created':time.time(),'job_id':'502',
                                'item_sha256':item_digest(flow('a',LONG))})
    s=json.loads(spec.read_text());s['items'][0].update(token='T2',generation=2);spec.write_text(json.dumps(s))
    r=run([ROOT/'scripts/symmetry_lane.py','--spec',spec,'--logs',logs,'--cores',2,'--mem-gib',16,'--headroom-gib',0],
          timeout=120,SLURM_JOB_ID='502')
    assert r.returncode==0,r.stderr
    result=read_record(campaign/'a'/'g0002'/'result.json')
    assert result['resumed_at_site']>0
    end=[json.loads(l) for l in (logs/'502.r0'/'events.jsonl').read_text().splitlines() if '"end"' in l]
    assert end[0]['rc']==0 and end[0]['peak_rss_kib']>0
    assert json.loads((logs/'502.r0'/'node.json').read_text())['runtime']==read_record(receipt)['runtime']
    st=run([ROOT/'scripts/symmetry_status.py','--site',site,'--campaign',campaign,'--manifest',json.loads(spec.read_text())['manifest'],
            '--receipt',receipt,'--logs',logs,'--no-slurm'])
    line=st.stdout.splitlines()[0]
    assert ' done ' in line and 'last_rc=0' in line and 'peak_rss_kib=' in line and 'token=T2' in line and 'g0002' in line,st.stdout


def test_restarted_execution_launches_nothing(tmp_path,campaign,receipt):
    spec=lane_setup(tmp_path,campaign,receipt,[flow('a')])
    logs=tmp_path/'logs'
    r=run([ROOT/'scripts/symmetry_lane.py','--spec',spec,'--logs',logs,'--cores',2,'--mem-gib',16],
          SLURM_RESTART_COUNT=1,SLURM_JOB_ID='77')
    assert r.returncode==79 and not logs.exists() and listing(campaign/'a')==['.owner']


def test_admission_respects_threads_and_memory(tmp_path,campaign,receipt,monkeypatch):
    items=[]
    for n,(threads,mem) in enumerate([(4,10),(1,50),(2,20),(8,5),(1,1),(3,30),(2,40),(1,15),(4,4),(1,2)]):
        items.append(flow(f'i{n}',Config(s=.8,Lambda=3.,keep=6,nb=4,nsites=10,threads=threads),memory_limit_gib=mem))
    spec=lane_setup(tmp_path,campaign,receipt,items)
    monkeypatch.setattr(symmetry_lane.Lane,'command',lambda self,e:[sys.executable,'-c','import time;time.sleep(.3)'])
    monkeypatch.setenv('SLURM_JOB_ID','adm')
    lane=symmetry_lane.Lane(spec,tmp_path/'logs',cores=8,mem_gib=68,headroom_gib=8);lane.poll=.02
    assert lane.run()==0
    events=[json.loads(l) for l in (tmp_path/'logs'/'adm.r0'/'events.jsonl').read_text().splitlines()]
    starts=[e for e in events if e['event']=='start']
    assert len(starts)==len(items)
    assert max(e['threads_in_use'] for e in starts)<=8 and max(e['reserved_gib_in_use'] for e in starts)<=60
    assert max(e['threads_in_use'] for e in starts)>1   # it does pack


# ---------------------------------------------------------------- submission

def test_submit_status_and_dry_run(tmp_path,site,slurm,receipt,campaign):
    m=manifest(tmp_path,[flow('a'),flow('b'),flow('c')])
    before=listing(campaign)
    r=submit(site,'submit','--campaign',campaign,'--manifest',m,'--receipt',receipt,'--lanes',2,'--dry-run')
    assert r.returncode==0,r.stderr
    assert listing(campaign)==before and not slurm.submitted() and not (tmp_path/'base').exists()
    r=submit(site,'submit','--campaign',campaign,'--manifest',m,'--receipt',receipt,'--lanes',2)
    assert r.returncode==0,r.stderr
    calls=slurm.submitted();assert len(calls)==2
    for c in calls:
        for flag in ('--no-requeue','--exclusive'):assert flag in c
        assert c[c.index('-p')+1]=='amdq' and c[c.index('--exclude')+1]=='cn112' and c[c.index('--signal')+1]=='B:USR1@300'
    for name in 'abc':
        o=read_owner(campaign/name);assert o['generation']==1 and o['job_id'] in ('1000','1001')
    assert len((campaign/'SUBMITTED.jsonl').read_text().splitlines())==2
    r=submit(site,'submit','--campaign',campaign,'--manifest',m,'--receipt',receipt)
    assert 'owned (use resubmit)' in r.stdout and len(slurm.submitted())==2
    r=run([ROOT/'scripts/symmetry_status.py','--site',site,'--campaign',campaign,'--manifest',m,'--receipt',receipt],
          PATH=os.environ['PATH'],FAKE_SLURM_STATE=os.environ['FAKE_SLURM_STATE'])
    states=[l.split()[1] for l in r.stdout.splitlines() if l and l.split()[0] in 'abc']
    assert r.returncode==0 and states==['pending']*3,r.stdout
    own_token=read_owner(campaign/'a')['token']
    assert fixed(.4,TINY,campaign/'a',owner_token=own_token,memory_limit_gib=1)['records']
    r=run([ROOT/'scripts/symmetry_status.py','--site',site,'--campaign',campaign,'--manifest',m,'--receipt',receipt,'--no-slurm'])
    line=next(l for l in r.stdout.splitlines() if l.startswith('a '))
    assert ' done ' in line and f'result={campaign/"a"/"g0001"/"result.json"}' in line,r.stdout


def test_oversized_items_and_wrong_host_are_refused(tmp_path,site,slurm,receipt,campaign):
    big=Config(s=.8,Lambda=3.,keep=6,nb=4,nsites=10,threads=65)
    for item in (flow('t',big),flow('m',memory_limit_gib=500)):
        r=submit(site,'submit','--campaign',campaign,'--manifest',manifest(tmp_path,[item]),'--receipt',receipt)
        assert r.returncode!=0 and not slurm.submitted()
    other=json.loads(site.read_text());other['login_host']='not-'+short_host();site.write_text(json.dumps(other))
    r=submit(site,'submit','--campaign',campaign,'--manifest',manifest(tmp_path,[flow('a')]),'--receipt',receipt)
    assert r.returncode!=0 and 'Refusing' in r.stderr and not slurm.submitted()


def test_live_unknown_and_failed_queries_are_refused(tmp_path,site,slurm,receipt,campaign):
    m=manifest(tmp_path,[flow('a')])
    own(campaign,'a',job_id='1001');slurm.job(1001,'lrisb-test-0','RUNNING',True)
    args=('resubmit','--campaign',campaign,'--manifest',m,'--receipt',receipt)
    assert 'is RUNNING' in submit(site,*args).stdout
    slurm.job(1001,'lrisb-test-0','RUNNING',False)          # gone from squeue, sacct not terminal
    assert 'not terminal' in submit(site,*args).stdout
    slurm.job(1001,'lrisb-test-0','TIMEOUT',False);slurm.fail('squeue')
    r=submit(site,*args);assert r.returncode!=0 and 'Refusing' in r.stderr
    slurm.fail('squeue',False);slurm.fail('sacct')
    assert 'query failed' in submit(site,*args).stdout
    assert not slurm.submitted() and read_owner(campaign/'a')['token']=='T1'
    slurm.fail('sacct',False)
    r=submit(site,*args);assert r.returncode==0,r.stderr
    o=read_owner(campaign/'a');assert o['generation']==2 and o['previous']['job_id']=='1001'


def test_concurrent_reclaim_has_one_winner(tmp_path,site,slurm,receipt,campaign):
    m=manifest(tmp_path,[flow('a')])
    own(campaign,'a',job_id='1001');slurm.job(1001,'lrisb-test-0','TIMEOUT',False)
    args=[sys.executable,str(ROOT/'scripts/symmetry_submit.py'),'--site',str(site),'resubmit','--campaign',str(campaign),
          '--manifest',str(m),'--receipt',str(receipt)]
    e=env(PATH=os.environ['PATH'],FAKE_SLURM_STATE=os.environ['FAKE_SLURM_STATE'])
    procs=[subprocess.Popen(args,cwd=ROOT,env=e,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    outs=[p.communicate(timeout=60) for p in procs]
    assert all(p.returncode==0 for p in procs),outs
    assert len(slurm.submitted())==1
    assert read_owner(campaign/'a')['generation']==2
    assert sum('is PENDING' in o for o,_ in outs)==1


def test_reclaim_waits_for_lock_and_sees_the_other_winner(tmp_path,site,slurm,receipt,campaign):
    m=manifest(tmp_path,[flow('a')])
    own(campaign,'a',job_id='1001');slurm.job(1001,'lrisb-test-0','TIMEOUT',False)
    args=[sys.executable,str(ROOT/'scripts/symmetry_submit.py'),'--site',str(site),'resubmit','--campaign',str(campaign),
          '--manifest',str(m),'--receipt',str(receipt)]
    with open(campaign/'.submit.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        p=subprocess.Popen(args,cwd=ROOT,env=env(PATH=os.environ['PATH'],FAKE_SLURM_STATE=os.environ['FAKE_SLURM_STATE']),
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        time.sleep(1.5)
        assert p.poll() is None and read_owner(campaign/'a')['token']=='T1' and not slurm.submitted()
        # Another submitter reclaims first, while holding the lock.
        replace_owner(campaign/'a',{'token':'OTHER','generation':2,'job_name':'lrisb-other-0','created':time.time(),'job_id':'2002',
                                    'item_sha256':item_digest(flow('a'))})
        slurm.job(2002,'lrisb-other-0','PENDING',True)
        fcntl.flock(lock,fcntl.LOCK_UN)
    out,err=p.communicate(timeout=60)
    assert p.returncode==0 and 'job 2002 is PENDING' in out,(out,err)
    assert read_owner(campaign/'a')['token']=='OTHER' and not slurm.submitted()


def test_crash_after_sbatch_acceptance_is_recoverable(tmp_path,site,slurm,receipt,campaign):
    """REV-007: the owner never received its job id; reconcile by the unique job name."""
    m=manifest(tmp_path,[flow('a')]);args=('resubmit','--campaign',campaign,'--manifest',m,'--receipt',receipt)
    own(campaign,'a',job_id=None,job_name='lrisb-crash-0');slurm.job(3001,'lrisb-crash-0','RUNNING',True)
    assert 'job 3001 is RUNNING' in submit(site,*args).stdout
    assert read_owner(campaign/'a')['job_id']=='3001' and not slurm.submitted()
    slurm.job(3001,'lrisb-crash-0','TIMEOUT',False)
    assert submit(site,*args).returncode==0 and len(slurm.submitted())==1
    assert read_owner(campaign/'a')['generation']==2


def test_ambiguous_and_orphan_owners(tmp_path,site,slurm,receipt,campaign):
    m=manifest(tmp_path,[flow('a')]);args=('resubmit','--campaign',campaign,'--manifest',m,'--receipt',receipt)
    own(campaign,'a',job_id=None,job_name='lrisb-amb-0')
    slurm.job(4001,'lrisb-amb-0','TIMEOUT',False);slurm.job(4002,'lrisb-amb-0','TIMEOUT',False)
    assert 'ambiguous' in submit(site,*args).stdout and not slurm.submitted()
    st=slurm.load();st['jobs']={};slurm.save(st)
    assert 'needs --reclaim-orphans' in submit(site,*args).stdout
    assert 'old' in submit(site,*args,'--reclaim-orphans').stdout and not slurm.submitted()
    assert submit(site,*args,'--reclaim-orphans','--orphan-min-age','0').returncode==2   # no bypass exists
    o=read_owner(campaign/'a');replace_owner(campaign/'a',{**o,'created':time.time()-1000})
    r=submit(site,*args,'--reclaim-orphans')
    assert r.returncode==0 and len(slurm.submitted())==1 and read_owner(campaign/'a')['generation']==2


def test_failed_sbatch_restores_owners(tmp_path,site,slurm,receipt,campaign):
    m=manifest(tmp_path,[flow('a'),flow('b')])
    own(campaign,'b',job_id='1001');slurm.job(1001,'lrisb-test-0','CANCELLED',False);slurm.fail('sbatch')
    r=submit(site,'resubmit','--campaign',campaign,'--manifest',m,'--receipt',receipt)
    assert r.returncode!=0 and not (campaign/'a'/'.owner').exists() and read_owner(campaign/'b')['token']=='T1'


# ---------------------------------------------------------------- exports

def test_export_layout_and_overwrite_guard(tmp_path,campaign):
    for name in ('a','b'):
        own(campaign,name,token='T'+name);fixed(.4,TINY,campaign/name,owner_token='T'+name,memory_limit_gib=1)
    out=tmp_path/'out';exporter=ROOT/'scripts/export_legacy.py'
    recs=[campaign/n/'g0001'/'result.json' for n in 'ab']
    r=run([exporter,*recs,'--output-dir',out]);assert r.returncode==0,r.stderr
    for n in 'ab':
        prov=json.loads((out/n/'flow.json').read_text())['_provenance']
        assert prov['campaign_item']==n and prov['generation']==1
    r=run([exporter,recs[0],'--output-dir',out]);assert r.returncode==0 and 'Unchanged' in r.stdout
    # A reclaimed generation seeds from the old one, so its result is the same record.
    replace_owner(campaign/'a',{'token':'T2','generation':2,'job_name':'n','created':time.time(),'job_id':None})
    fixed(.4,TINY,campaign/'a',owner_token='T2',memory_limit_gib=1,resume=True)
    newer=campaign/'a'/'g0002'/'result.json';assert newer.read_bytes()==recs[0].read_bytes()
    r=run([exporter,newer,'--output-dir',out]);assert r.returncode==0 and 'Unchanged' in r.stdout
    # A different record whose destination is also 'a' is never silently replaced.
    fixed(.41,TINY,tmp_path/'other'/'a',memory_limit_gib=1);different=tmp_path/'other'/'a'/'result.json'
    r=run([exporter,different,'--output-dir',out]);assert r.returncode!=0 and 'Refusing' in r.stderr
    assert run([exporter,different,'--output-dir',out,'--replace']).returncode==0
    assert json.loads((out/'a'/'flow.json').read_text())['alpha']==.41
    fixed(.4,TINY,tmp_path/'plain',memory_limit_gib=1)
    r=run([exporter,tmp_path/'plain'/'result.json','--output-dir',out]);assert r.returncode==0
    assert (out/'plain'/'flow.json').is_file()
    r=run(['-m','lri_spin','export',recs[1],'--output',tmp_path/'all.json']);assert r.returncode==0
    assert json.loads((tmp_path/'all.json').read_text())[0]['_provenance']['campaign_item']=='b'


def test_resolve_target_outside_campaign_is_unchanged(tmp_path):
    folder,guard=resolve_target(tmp_path/'x','anything')
    assert folder==tmp_path/'x' and guard is None


# ---------------------------------------------------------------- final-inspection findings

def test_done_requires_matching_identity(tmp_path,site,slurm,receipt,campaign):
    """INS-001: a finished x(alpha=.4) is not 'done' for x(alpha=.41); the changed definition is refused."""
    own(campaign,'x',token='T1',item=flow('x'));fixed(.4,TINY,campaign/'x',owner_token='T1',memory_limit_gib=1)
    ok=manifest(tmp_path,[flow('x')],'same.json');changed=manifest(tmp_path,[flow('x',alpha=.41)],'changed.json')
    assert 'x: skipped, done' in submit(site,'resubmit','--campaign',campaign,'--manifest',ok,'--receipt',receipt).stdout
    out=submit(site,'resubmit','--campaign',campaign,'--manifest',changed,'--receipt',receipt).stdout
    assert 'conflicting result in g0001' in out and not slurm.submitted()
    st=run([ROOT/'scripts/symmetry_status.py','--site',site,'--campaign',campaign,'--manifest',changed,'--receipt',receipt,'--no-slurm'])
    assert st.stdout.split()[1]=='conflict',st.stdout
    # Without a result, a changed definition under an owned ID is refused as well.
    own(campaign,'y',item=flow('y'),job_id='1001');slurm.job(1001,'lrisb-test-0','TIMEOUT',False)
    out=submit(site,'resubmit','--campaign',campaign,'--manifest',manifest(tmp_path,[flow('y',alpha=.41)],'y.json'),'--receipt',receipt).stdout
    assert 'item definition differs' in out and not slurm.submitted()


def test_lanes_use_verified_snapshots(tmp_path,site,slurm,receipt,campaign):
    """INS-002: specs point at read-only snapshots with hashes; a changed snapshot or manifest is refused."""
    m=manifest(tmp_path,[flow('a')])
    assert submit(site,'submit','--campaign',campaign,'--manifest',m,'--receipt',receipt).returncode==0
    spec_path=next((campaign/'lanes').glob('*/lane0.json'));spec=json.loads(spec_path.read_text())
    assert Path(spec['manifest']).parent==spec_path.parent and sha(spec['manifest'])==spec['manifest_sha256']
    assert sha(spec['receipt'])==spec['receipt_sha256'] and not os.access(spec['manifest'],os.W_OK)
    m.write_text(m.read_text().replace('"alpha": 0.4','"alpha": 0.5'))      # editing the original changes nothing
    assert json.loads(Path(spec['manifest']).read_text())['items'][0]['alpha']==.4
    tampered=tmp_path/'tampered.json';tampered.write_text(Path(spec['manifest']).read_text().replace('"keep": 6','"keep": 7'))
    bad=dict(spec,manifest=str(tampered));bad_spec=tmp_path/'bad_spec.json';bad_spec.write_text(json.dumps(bad))
    logs=tmp_path/'logs'
    r=run([ROOT/'scripts/symmetry_lane.py','--spec',bad_spec,'--logs',logs,'--cores',2,'--mem-gib',16])
    assert r.returncode!=0 and 'differs from its submitted hash' in r.stderr and not logs.exists()
    # A child refuses a manifest whose hash is not the admitted one.
    r=run(['-m','lri_spin','item','--manifest',tampered,'--index',0,'--validation-receipt',spec['receipt'],
           '--output-dir',campaign,'--resume'],LRI_SPIN_OWNER_TOKEN=spec['items'][0]['token'],
          LRI_SPIN_MANIFEST_SHA256=spec['manifest_sha256'],LRI_SPIN_RECEIPT_SHA256=spec['receipt_sha256'])
    assert r.returncode!=0 and 'differs from the submitted snapshot' in r.stderr
    assert not (campaign/'a'/'g0001').exists()


def test_symlinks_cannot_redirect_generation_writes(tmp_path,campaign):
    """INS-003."""
    own(campaign,'x',token='T2',generation=2)
    (campaign/'x'/'g0001').mkdir();(campaign/'x'/'g0001'/'keep.txt').write_text('old')
    (campaign/'x'/'g0002').symlink_to(campaign/'x'/'g0001')
    with pytest.raises(OwnershipError):resolve_target(campaign/'x','T2')
    (campaign/'x'/'g0002').unlink();(tmp_path/'elsewhere').mkdir()
    (campaign/'x'/'g0001'/'state.npz').symlink_to(tmp_path/'elsewhere'/'secret')
    (tmp_path/'elsewhere'/'secret').write_text('outside')
    g2=seed(campaign/'x',2)
    assert sorted(p.name for p in g2.iterdir())==['keep.txt']                 # the symlink was not copied
    (g2/'trials').symlink_to(tmp_path/'elsewhere')
    with pytest.raises(OwnershipError):resolve_target(campaign/'x','T2')
    (campaign/'y').symlink_to(campaign/'x')
    with pytest.raises(OwnershipError):resolve_target(campaign/'y','T2')
    with pytest.raises(ValueError):validate_items([flow('y')],campaign)


def test_plain_outputs_never_land_in_a_campaign(tmp_path,campaign,receipt):
    """INS-004."""
    own(campaign,'x',token='T');fixed(.4,TINY,campaign/'x',owner_token='T',memory_limit_gib=1)
    record=campaign/'x'/'g0001'/'result.json';before=record.read_bytes()
    fixed(.4,TINY,tmp_path/'plain',memory_limit_gib=1)
    r=run(['-m','lri_spin','export',tmp_path/'plain'/'result.json','--output',record])
    assert r.returncode==76 and record.read_bytes()==before
    items=tmp_path/'items.json';items.write_text(json.dumps([flow('q')]))
    r=run([ROOT/'scripts/make_manifest.py','--items',items,'--receipt',receipt,'--output',campaign/'x'/'m.json'])
    assert r.returncode!=0 and not (campaign/'x'/'m.json').exists()
    r=run([ROOT/'scripts/export_legacy.py',tmp_path/'plain'/'result.json','--output-dir',campaign/'exports'])
    assert r.returncode!=0 and not (campaign/'exports').exists()


def test_reserved_and_non_directory_item_paths(campaign):
    """INS-005."""
    for name in ('SUBMITTED.jsonl','lanes'):
        with pytest.raises(ValueError):validate_item(flow(name))
    (campaign/'filex').write_text('not a directory')
    with pytest.raises(ValueError):validate_items([flow('filex')],campaign)


def test_owner_publication_is_atomic(tmp_path,monkeypatch):
    """INS-006: a crash before publication leaves no owner; an existing owner is never replaced."""
    item=tmp_path/'item'
    def crash(src,dst):raise OSError('simulated crash before publication')
    monkeypatch.setattr(os,'link',crash)
    with pytest.raises(OSError):create_owner(item,{'token':'T','generation':1})
    assert sorted(p.name for p in item.iterdir())==[]
    monkeypatch.undo()
    create_owner(item,{'token':'T','generation':1})
    with pytest.raises(FileExistsError):create_owner(item,{'token':'U','generation':1})
    assert read_owner(item)['token']=='T' and sorted(p.name for p in item.iterdir())==['.owner']
    root=tmp_path/'c';init_campaign(root,'h')
    with pytest.raises(FileExistsError):publish_new(root/'.campaign',b'{}')
    assert json.loads((root/'.campaign').read_text())['login_host']=='h'
    assert sorted(p.name for p in root.iterdir())==['.campaign','.submit.lock']


def test_export_destinations_are_coherent(tmp_path):
    """INS-007: one destination holds one record's components; failures write nothing."""
    exporter=ROOT/'scripts/export_legacy.py';out=tmp_path/'out'
    fixed(.4,TINY,tmp_path/'A'/'same',tangent=True,memory_limit_gib=1)
    fixed(.4,TINY,tmp_path/'B'/'same',memory_limit_gib=1)
    fixed(.4,TINY,tmp_path/'C'/'fresh',memory_limit_gib=1)
    assert run([exporter,tmp_path/'A'/'same'/'result.json','--output-dir',out]).returncode==0
    assert sorted(p.name for p in (out/'same').iterdir())==['tangent.json']
    r=run([exporter,tmp_path/'C'/'fresh'/'result.json',tmp_path/'B'/'same'/'result.json','--output-dir',out])
    assert r.returncode!=0 and not (out/'fresh').exists()                  # preflight refused before any write
    r=run([exporter,tmp_path/'B'/'same'/'result.json','--output-dir',out,'--replace'])
    assert r.returncode==0 and sorted(p.name for p in (out/'same').iterdir())==['flow.json']


def test_lane_records_node_and_explains_runtime_mismatch(tmp_path,campaign):
    """INS-009."""
    ident=identity(Config(),None,'receipt');wrong=dict(ident['runtime'],numpy='0.0-other')
    receipt=tmp_path/'other_receipt.json'
    write_record(receipt,{**ident,'runtime':wrong},{'passed':True,'source_sha256':source_hash(),'runtime':wrong})
    spec=lane_setup(tmp_path,campaign,receipt,[flow('a')]);logs=tmp_path/'logs'
    r=run([ROOT/'scripts/symmetry_lane.py','--spec',spec,'--logs',logs,'--cores',2,'--mem-gib',16],SLURM_JOB_ID='9')
    assert r.returncode!=0 and 'expected' in r.stderr and 'actual' in r.stderr and '0.0-other' in r.stderr
    node=json.loads((logs/'9.r0'/'node.json').read_text())
    assert node['runtime']==ident['runtime'] and node['host']
    assert listing(campaign/'a')==['.owner']


# ---------------------------------------------------------------- inspection round 2

def test_benchmark_outputs_refuse_campaign_state(tmp_path,campaign):
    """INS-R2-001: shipped benchmark writers check the destination before computing."""
    own(campaign,'x',token='T');fixed(.4,TINY,campaign/'x',owner_token='T',memory_limit_gib=1)
    target=campaign/'x'/'g0001'/'result.json';before=target.read_bytes()
    commands=[['benchmarks/benchmark.py','--implementation','ordered','--task','flow'],['benchmarks/long_regression.py','--quick'],
              ['benchmarks/profile_reference.py'],['benchmarks/rejected_alternatives.py']]
    for c in commands:
        r=run([ROOT/c[0],*c[1:],'--output',target])
        assert r.returncode!=0 and 'inside campaign root' in r.stderr,(c,r.stderr[-300:])
    assert target.read_bytes()==before


def test_export_destinations_resolved_and_serialized(tmp_path,campaign):
    """INS-R2-002/003: aliases, campaign links and concurrent exporters cannot mix records."""
    exporter=ROOT/'scripts/export_legacy.py';out=tmp_path/'out';out.mkdir()
    for d,alpha in (('A',.4),('B',.41)):fixed(alpha,TINY,tmp_path/d/'same',memory_limit_gib=1)
    fixed(.4,TINY,tmp_path/'C'/'other',memory_limit_gib=1)
    (out/'same').symlink_to(campaign)                                        # a destination link into a campaign
    r=run([exporter,tmp_path/'A'/'same'/'result.json','--output-dir',out]);assert r.returncode!=0 and 'symlink' in r.stderr
    (out/'same').unlink();(out/'real').mkdir();(out/'other').symlink_to(out/'real')
    r=run([exporter,tmp_path/'C'/'other'/'result.json','--output-dir',out]);assert r.returncode!=0
    assert list((out/'real').iterdir())==[]
    (out/'other').unlink()
    lock=out/'.same.export.lock';lock.write_text('held')
    r=run([exporter,tmp_path/'A'/'same'/'result.json','--output-dir',out])
    assert r.returncode!=0 and 'in progress' in r.stderr and not (out/'same').exists()
    lock.unlink()
    procs=[subprocess.Popen([sys.executable,str(exporter),str(tmp_path/d/'same'/'result.json'),'--output-dir',str(out)],
                            cwd=ROOT,env=env(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for d in 'AB']
    outs=[p.communicate(timeout=60) for p in procs]
    assert sorted(p.returncode for p in procs)[0]==0 and sum(p.returncode==0 for p in procs)==1,outs
    files=sorted((out/'same').iterdir());assert [f.name for f in files]==['flow.json']
    winner='A' if procs[0].returncode==0 else 'B'
    assert json.loads(files[0].read_text())['_record_sha256']==json.loads((tmp_path/winner/'same'/'result.json').read_text())['sha256']
    assert not list(out.glob('.*.export.lock'))


def test_status_reports_conflict_for_changed_definition(tmp_path,site,receipt,campaign):
    """INS-R2-004: no progress of x(alpha=.4) is reported for x(alpha=.41)."""
    own(campaign,'x',item=flow('x'),job_id='1001')
    (campaign/'x'/'g0001').mkdir();(campaign/'x'/'g0001'/'state.npz').write_bytes(b'checkpoint')
    m=manifest(tmp_path,[flow('x',alpha=.41)])
    r=run([ROOT/'scripts/symmetry_status.py','--site',site,'--campaign',campaign,'--manifest',m,'--receipt',receipt,'--no-slurm'])
    assert r.stdout.split()[1]=='conflict' and 'different item definition' in r.stdout,r.stdout
