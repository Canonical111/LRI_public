"""Expanse campaign layer: spec/steps, seed rules, chain driver, claims, continuation, R3 publication."""
import hashlib,json,os,shutil,signal,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'cluster/expanse'))
import common,chain,recover_claims,continuation,envcheck,collect,campaign,copy
from ht2d import hpc

TEACHER=ROOT/'reference/results/teacher_L6_x0.300.json'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def release_manifest(tmp):
    """Per-file manifest of the executing tree in release form (ht2d/... paths)."""
    lines=[]
    for sub in ('code','cluster','inputs'):
        for f in sorted((ROOT/sub).rglob('*')):
            if f.is_file() and '__pycache__' not in f.parts:
                lines.append(f"{sha(f)}  ht2d/{f.relative_to(ROOT).as_posix()}")
    m=Path(tmp)/'manifest.sha256';m.parent.mkdir(parents=True,exist_ok=True);m.write_text('\n'.join(lines)+'\n');return m


def make_spec(tmp,ladder=(6,8),checks=None,seed_src=TEACHER,origin='reference_same_L',basis_src=TEACHER,x=0.3,main_diag='none'):
    inputs=tmp/'inputs';inputs.mkdir(parents=True,exist_ok=True)
    b=inputs/'basis.json';shutil.copy2(basis_src,b);s=inputs/'seed.json';shutil.copy2(seed_src,s)
    c={'x':x,'ladder':list(ladder),'main':{'nz':12,'diagnostics':main_diag},
       'checks':checks if checks is not None else [{'nz':16,'diagnostics':'none','L':[ladder[0]]}],
       'common':{'backend':'tensor','threads':1,'memory_limit_gib':4.0,'eig_tol':1e-12,'residual_tol':1e-8,
                 'tuning_tol':3e-11,'ncv':40,'maxiter':50},
       'slurm':{'account':'<ACCOUNT>','partition':'shared','cpus':1,'mem_gb':8,'time':'01:00:00','lead_s':1800,'max_cont':2},
       'max_bath_states':{str(L):2_000_000 for L in ladder},
       'basis':{'path':str(b),'sha256':sha(b)},'initial_seed':{'path':str(s),'sha256':sha(s),'origin':origin}}
    env_id=envcheck.identity()['env_id'];man=release_manifest(tmp)
    rc=tmp/'receipt.json';rc.write_text(json.dumps({'passed':True,'tar_sha256':'-','manifest_sha256':sha(man),'source_sha256':hpc.source_hash(),'env_id':env_id}))
    spec={'schema':common.SPEC_SCHEMA,'campaign':'t','root':str(tmp/'camp'),'logs':str(tmp/'logs'),
          'release':{'commit':'x','tar':'-','tar_sha256':'-','manifest':str(man),'manifest_sha256':sha(man),'source_sha256':hpc.source_hash()},
          'env':{'python':sys.executable,'env_id':env_id},'receipt':{'path':str(rc),'sha256':sha(rc)},'chains':{'c1':c}}
    spec['sha256']=common.digest(spec)
    path=tmp/'spec.json';hpc.atomic_json(path,spec)
    return spec,path


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for k,v in {'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMBA_NUM_THREADS':'4'}.items():
        monkeypatch.setenv(k,v)
    monkeypatch.setenv('SLURM_JOB_ID','9001')
    chain.STOP.update(requested=False,child=None)


def test_spec_checksum_and_steps(tmp_path):
    spec,path=make_spec(tmp_path)
    assert common.load_spec(path,sha(path))['sha256']==spec['sha256']
    with pytest.raises(common.SpecError):common.load_spec(path,'0'*64)
    st=common.steps(spec,'c1')
    assert [(s['role'],s['L'],s['nz']) for s in st]==[('main',6,12),('check',6,16),('main',8,12)]
    assert st[0]['seed']=={'kind':'initial'}
    assert st[1]['seed']=={'kind':'step','chain':'c1','L':6,'nz':12}
    assert st[2]['seed']=={'kind':'step','chain':'c1','L':6,'nz':12}
    bad=json.loads(path.read_text());bad['chains']['c1']['x']=.31;path.write_text(json.dumps(bad))
    with pytest.raises(common.SpecError):common.load_spec(path)


def test_initial_seed_origins(tmp_path):
    spec,_=make_spec(tmp_path)          # teacher record used as an L0 reference (bath_cut 6 == L0)
    assert common.check_initial_seed(spec,'c1')
    s2,_=make_spec(tmp_path/'b',ladder=(8,10),origin='teacher_L0m2')      # teacher at L0-2, equal to the basis
    assert common.check_initial_seed(s2,'c1')
    s3,_=make_spec(tmp_path/'c',ladder=(8,10),origin='reference_same_L')  # bath_cut 6 != L0
    with pytest.raises(common.SpecError):common.check_initial_seed(s3,'c1')
    s4,_=make_spec(tmp_path/'d',ladder=(6,8),origin='teacher_L0m2')       # bath_cut 6 != L0-2
    with pytest.raises(common.SpecError):common.check_initial_seed(s4,'c1')
    other=tmp_path/'other.json';d=json.loads(TEACHER.read_text());d['theta']=[float('nan'),0.];other.write_text(json.dumps(d))
    s5,_=make_spec(tmp_path/'e',seed_src=other)
    with pytest.raises(common.SpecError):common.check_initial_seed(s5,'c1')
    d=json.loads(TEACHER.read_text());d['delta']=.31;other.write_text(json.dumps(d))
    s6,_=make_spec(tmp_path/'f',seed_src=other)
    with pytest.raises(common.SpecError):common.check_initial_seed(s6,'c1')
    d=json.loads(TEACHER.read_text());d['note']=1;other.write_text(json.dumps(d))
    s7,_=make_spec(tmp_path/'g',ladder=(8,10),origin='teacher_L0m2',seed_src=other,basis_src=TEACHER)  # teacher != basis
    with pytest.raises(common.SpecError):common.check_initial_seed(s7,'c1')
    Path(spec['chains']['c1']['initial_seed']['path']).write_text('{}')
    with pytest.raises(common.SpecError):common.check_initial_seed(spec,'c1')


@pytest.fixture
def ran_chain(tmp_path):
    spec,path=make_spec(tmp_path)
    assert chain.main(['--spec',str(path),'--chain','c1','--spec-sha256',sha(path)])==0
    return spec,path


def test_chain_runs_validates_and_reuses(ran_chain):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1')
    for s in common.steps(spec,'c1'):common.check_predecessor(spec,{'chain':'c1','L':s['L'],'nz':s['nz']})
    st=json.loads((cdir/'state'/'9001.json').read_text());assert st['status']=='complete' and st['failed_checks']==[]
    assert not common.claims_under(cdir)
    before={p:p.read_bytes() for p in cdir.glob('L*_z*.json')}
    assert chain.main(['--spec',str(path),'--chain','c1'])==0
    assert all(p.read_bytes()==b for p,b in before.items())


def test_predecessor_tamper_refused(ran_chain):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1')
    rec=cdir/'L6_z12.json';d=json.loads(rec.read_text());d['Delta_thermal']+=1e-3;rec.write_text(json.dumps(d))
    (cdir/'L8_z12.json').unlink()
    with pytest.raises(ValueError):common.check_predecessor(spec,{'chain':'c1','L':6,'nz':12})
    # The driver re-validates the tampered L6 record; hpc refuses it as an integrity failure (F19).
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_SEED
    assert not (cdir/'L8_z12.json').exists()
    st=json.loads((cdir/'state'/'9001.json').read_text());assert st['status']=='failed'


def test_predecessor_from_other_configuration_refused(ran_chain):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1')
    # A valid record of ANOTHER step placed at the predecessor path is refused (identity check).
    shutil.copy2(cdir/'L6_z16.json',cdir/'L6_z12.json')
    with pytest.raises(common.SpecError):common.check_predecessor(spec,{'chain':'c1','L':6,'nz':12})


def test_chain_claim_exclusive(tmp_path):
    spec,path=make_spec(tmp_path);cdir=common.chain_dir(spec,'c1');(cdir/'chain.claim').mkdir(parents=True)
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_CLAIMED
    assert not (cdir/'state').exists()


def test_failed_check_does_not_stop_ladder(tmp_path):
    spec,path=make_spec(tmp_path,checks=[{'nz':24,'diagnostics':'none','L':[6]}])  # 24 > basis capacity 20
    assert chain.main(['--spec',str(path),'--chain','c1'])==0
    cdir=common.chain_dir(spec,'c1');st=json.loads((cdir/'state'/'9001.json').read_text())
    assert st['status']=='complete' and st['failed_checks'][0]['nz']==24
    assert (cdir/'L8_z12.json').exists()
    assert continuation.chain_complete(spec,'c1',st['failed_checks'])
    assert not continuation.chain_complete(spec,'c1',[])


def test_failed_main_stops(tmp_path):
    spec,path=make_spec(tmp_path,checks=[])
    d=json.loads(path.read_text());d['chains']['c1']['main']['nz']=24;del d['sha256'];d['sha256']=common.digest(d)
    hpc.atomic_json(path,d)
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_MAIN


def write_claim(dirpath,job):
    dirpath.mkdir(parents=True);(dirpath/'owner.json').write_text(json.dumps({'slurm_job_id':job,'token':'t'}))


def test_recover_claims_requires_terminal_owner(tmp_path):
    write_claim(tmp_path/'a.json.claim','1');write_claim(tmp_path/'b.json.claim','2')
    write_claim(tmp_path/'c.json.claim','3');(tmp_path/'d.json.claim').mkdir()
    states={'1':'TIMEOUT','2':'RUNNING','3':None}
    removed,kept=recover_claims.recover(tmp_path,apply=False,state_fn=states.get,log=lambda *_:None)
    assert [c.name for c in removed]==['a.json.claim'] and (tmp_path/'a.json.claim').exists()
    removed,kept=recover_claims.recover(tmp_path,owner_job='2',apply=True,state_fn=states.get,log=lambda *_:None)
    assert removed==[] and (tmp_path/'a.json.claim').exists()
    removed,kept=recover_claims.recover(tmp_path,apply=True,state_fn=states.get,log=lambda *_:None)
    assert [c.name for c in removed]==['a.json.claim'] and not (tmp_path/'a.json.claim').exists()
    assert {c.name for c,_ in kept}=={'b.json.claim','c.json.claim','d.json.claim'}
    assert list((tmp_path/'claims_archive').glob('*_1_*_a.json.claim/owner.json'))


def test_continuation_guard(ran_chain):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1');q=lambda n:[]
    write_claim(cdir/'chain.claim','9001')                    # stale chain claim of the predecessor
    assert continuation.guard(spec,'c1','9001','9100','n',state_fn=lambda j:'TIMEOUT',queue_fn=q,log=lambda *_:None)==10
    assert not (cdir/'chain.claim').exists()
    assert continuation.guard(spec,'c1','9001','9100','n',state_fn=lambda j:None,queue_fn=q,log=lambda *_:None)==75
    assert continuation.guard(spec,'c1','9001','9100','n',state_fn=lambda j:'RUNNING',queue_fn=q,log=lambda *_:None)==75
    assert continuation.guard(spec,'c1','9001','9100','n',state_fn=lambda j:'TIMEOUT',queue_fn=lambda n:['9100','9200'],log=lambda *_:None)==12
    assert continuation.guard(spec,'c1','9001','9100','n',state_fn=lambda j:'TIMEOUT',queue_fn=lambda n:None,log=lambda *_:None)==75
    (cdir/'L8_z12.json').unlink()                              # complete state, missing record -> resume
    assert continuation.guard(spec,'c1','9001','9100','n',state_fn=lambda j:'TIMEOUT',queue_fn=q,log=lambda *_:None)==0
    hpc.atomic_json(cdir/'state'/'9002.json',{'status':'failed'})
    assert continuation.guard(spec,'c1','9002','9100','n',state_fn=lambda j:'FAILED',queue_fn=q,log=lambda *_:None)==11
    assert continuation.guard(spec,'c1','9003','9100','n',state_fn=lambda j:'TIMEOUT',queue_fn=q,log=lambda *_:None)==0


def test_history_archived_and_collected(tmp_path):
    spec,path=make_spec(tmp_path,ladder=(6,),checks=[])
    cdir=common.chain_dir(spec,'c1')
    assert chain.main(['--spec',str(path),'--chain','c1'])==0
    out=cdir/'L6_z12.json';r=json.loads(out.read_text())
    hist=cdir/'history';hist.mkdir(exist_ok=True)
    good={'request_digest':r['request_digest'],'theta':r['theta'],'history':[{'iteration':0,'residual':1.,'jacobian_condition':3e9}]}
    good['checkpoint_sha256']=common.digest(good);(hist/'L6_z12.7.0.checkpoint.json').write_text(json.dumps(good))
    foreign={'request_digest':'other','history':[{'jacobian_condition':9e12}]};foreign['checkpoint_sha256']=common.digest(foreign)
    (hist/'L6_z12.7.1.checkpoint.json').write_text(json.dumps(foreign))
    (hist/'L6_z12.7.2.checkpoint.json').write_text('null')
    rej=[];assert collect.attempt_conditions(cdir,str(out),r,rej)==3e9 and len(rej)==2   # IR-05
    o=tmp_path/'coll';assert collect.main(['--spec',str(path),'--out',str(o)])==0
    fl=(o/'flags.txt').read_text();assert 'Jacobian condition' in fl and fl.count('archived checkpoint ignored')==2


def _stop_after_solve(monkeypatch):
    handlers={};monkeypatch.setattr(signal,'signal',lambda sig,f:handlers.setdefault(sig,f))
    from ht2d.solver import DressedSolver
    original=DressedSolver.solve
    def solve(self,*a,**k):
        row=original(self,*a,**k);handlers[signal.SIGUSR1](signal.SIGUSR1,None);return row
    monkeypatch.setattr(DressedSolver,'solve',solve)


def test_r3_finished_solve_is_published(tmp_path,monkeypatch):
    _stop_after_solve(monkeypatch)
    out=tmp_path/'p.json'
    argv=['--L','4','--x','.3','--nz','12','--osc','96','--diagnostics','none','--threads','1','--output',str(out)]
    assert hpc.main(argv)==0
    r=json.loads(out.read_text());assert r['stop_requested_at_publication'] is True
    hpc.validate_record(r,r['request_digest'])


def test_r3_stop_with_diagnostics_pending_exits_75(tmp_path,monkeypatch):
    _stop_after_solve(monkeypatch)
    out=tmp_path/'p.json'
    argv=['--L','4','--x','.3','--nz','12','--osc','96','--diagnostics','first','--threads','1','--output',str(out)]
    assert hpc.main(argv)==75 and not out.exists() and Path(str(out)+'.checkpoint.json').exists()


def test_envcheck_mismatch():
    assert envcheck.main(['--expect','0'*16])==74
    assert envcheck.main(['--expect',envcheck.identity()['env_id']])==0


@pytest.mark.skipif(shutil.which('sha256sum') is None or not Path('/usr/bin/python3').exists(),reason='needs coreutils')
@pytest.mark.parametrize('broken',['spec','tar','manifest','env'])
def test_job_script_verifies_before_running(tmp_path,broken):
    tar=tmp_path/'r.tar';subprocess.run(['tar','-cf',str(tar),'-C',str(ROOT.parent),ROOT.name],check=True)
    man=tmp_path/'r.sha256';man.write_text('')
    spec={'release':{'tar':str(tar),'tar_sha256':sha(tar),'manifest':str(man),'manifest_sha256':sha(man)},
          'env':{'python':sys.executable,'env_id':envcheck.identity()['env_id']},'root':str(tmp_path),
          'logs':str(tmp_path),'campaign':'t',
          'chains':{'c1':{'slurm':{'account':'<ACCOUNT>','partition':'shared','cpus':1,'mem_gb':1,'time':'0-01:00:00','lead_s':1800}}}}
    if broken=='tar':spec['release']['tar_sha256']='0'*64
    if broken=='manifest':spec['release']['manifest_sha256']='0'*64
    if broken=='env':spec['env']['env_id']='0'*16
    sp=tmp_path/'spec.json';sp.write_text(json.dumps(spec));s=sha(sp) if broken!='spec' else '0'*64
    env={**os.environ,'HT2D_SPEC':str(sp),'HT2D_SPEC_SHA256':s,'HT2D_CHAIN':'c1','HT2D_CONT':'0','HT2D_MAX_CONT':'2',
         'HT2D_STAGE_ROOT':str(tmp_path/'stage'),'SLURM_JOB_ID':'777'}
    if broken=='env':
        # The env check needs the release at ht2d/; build a tar with that prefix and its manifest.
        st=tmp_path/'src';shutil.copytree(ROOT,st/'ht2d',ignore=shutil.ignore_patterns('__pycache__','.git','runs'))
        subprocess.run(['tar','-cf',str(tar),'-C',str(st),'ht2d'],check=True)
        lines=subprocess.run('find ht2d -type f | LC_ALL=C sort | xargs sha256sum',shell=True,cwd=st,capture_output=True,text=True,check=True).stdout
        man.write_text(lines);spec['release'].update(tar_sha256=sha(tar),manifest_sha256=sha(man));sp.write_text(json.dumps(spec))
        env['HT2D_SPEC_SHA256']=sha(sp)
    p=subprocess.run(['bash',str(ROOT/'cluster/expanse/chain.sbatch')],env=env,capture_output=True,text=True,timeout=600)
    assert p.returncode==74,(p.stdout,p.stderr)
    want={'spec':'spec sha256 mismatch','tar':'release tar sha256 mismatch','manifest':'release manifest sha256 mismatch',
          'env':'environment mismatch'}[broken]
    assert want in p.stdout,(p.stdout,p.stderr)


def test_recovery_is_serialized_and_checks_owner_token(tmp_path):
    write_claim(tmp_path/'a.json.claim','1')
    (tmp_path/'recovery.lock').mkdir()
    with pytest.raises(recover_claims.RecoveryBusy):recover_claims.recover(tmp_path,apply=True,state_fn=lambda j:'TIMEOUT',log=lambda *_:None)
    assert recover_claims.main(['--scope',str(tmp_path),'--apply'])==75
    (tmp_path/'recovery.lock').rmdir()
    def reacquire(job):                    # a new owner takes the path between inspection and rename
        (tmp_path/'a.json.claim'/'owner.json').write_text(json.dumps({'slurm_job_id':'2','token':'new'}));return 'TIMEOUT'
    removed,kept=recover_claims.recover(tmp_path,apply=True,state_fn=reacquire,log=lambda *_:None)
    assert removed==[] and json.loads((tmp_path/'a.json.claim'/'owner.json').read_text())['token']=='new'
    assert not (tmp_path/'recovery.lock').exists()


def test_seed_mutation_after_validation_is_refused(ran_chain,monkeypatch):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1');(cdir/'L8_z12.json').unlink()
    original=chain.seed_for
    def mutate(spec_,chain_,step,cache=None):
        res=original(spec_,chain_,step,cache)
        if step['L']==8:p=Path(res[0]);p.write_bytes(p.read_bytes()+b' ')     # same JSON, different bytes
        return res
    monkeypatch.setattr(chain,'seed_for',mutate)
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_SEED      # child integrity refusal (F19)
    assert not (cdir/'L8_z12.json').exists()
    assert 'Inputs changed' in ''.join(p.read_text() for p in (cdir/'logs').glob('L8_z12.*.log'))


def test_exact_request_required(ran_chain):
    spec,path=ran_chain
    other=copy.deepcopy(spec);other['chains']['c1']['main']['diagnostics']='first'
    with pytest.raises(common.SpecError,match='exact frozen request'):common.check_predecessor(other,{'chain':'c1','L':6,'nz':12})
    common.check_predecessor(spec,{'chain':'c1','L':6,'nz':12})


def test_seed_failure_on_check_step_is_exit_65(ran_chain,monkeypatch):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1');(cdir/'L6_z16.json').unlink()
    original=chain.seed_for
    def refuse(spec_,chain_,step,cache=None):
        if step['role']=='check':raise common.SpecError('integrity')
        return original(spec_,chain_,step,cache)
    monkeypatch.setattr(chain,'seed_for',refuse)
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_SEED
    assert json.loads((cdir/'state'/'9001.json').read_text())['status']=='failed'


def test_effective_slurm_policy():
    ok={'account':'<ACCOUNT>','partition':'shared','cpus':32,'mem_gb':64,'time':'48:00:00','lead_s':3600,'max_cont':2}
    campaign.check_slurm('c',ok)
    for k,v in (('partition','compute'),('mem_gb',300),('time','2-00:00:01'),('lead_s',100),('max_cont',4),('account','x')):
        with pytest.raises(common.SpecError):campaign.check_slurm('c',{**ok,k:v})


def test_seed_from_edges(tmp_path):
    spec,_=make_spec(tmp_path)
    ref=copy.deepcopy(spec['chains']['c1']);ref.pop('initial_seed');ref['ladder']=[6];ref['checks']=[]
    ref['seed_from']={'chain':'c1','L':6,'nz':12};spec['chains']['r']=ref
    campaign.check_edges(spec)
    bad=copy.deepcopy(spec);bad['chains']['r']['x']=.4
    with pytest.raises(common.SpecError,match='cross-x'):campaign.check_edges(bad)
    bad=copy.deepcopy(spec);bad['chains']['r']['ladder']=[8]
    with pytest.raises(common.SpecError):campaign.check_edges(bad)
    bad=copy.deepcopy(spec);bad['chains']['r']['seed_from']['nz']=14
    with pytest.raises(common.SpecError):campaign.check_edges(bad)


def test_initial_seed_replacement_breaks_lineage(ran_chain):
    spec,path=ran_chain
    s=Path(spec['chains']['c1']['initial_seed']['path']);d=json.loads(s.read_text());d['note']='x';s.write_text(json.dumps(d))
    with pytest.raises(common.SpecError):common.validate_step(spec,'c1',8,12)      # lineage reaches the initial seed
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_SEED


def test_corrupt_check_checkpoint_is_integrity_exit_65(ran_chain):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1')
    (cdir/'L6_z16.json').unlink();Path(str(cdir/'L6_z16.json')+'.checkpoint.json').write_text('{corrupt')
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_SEED
    st=json.loads((cdir/'state'/'9001.json').read_text());assert st['status']=='failed' and st['failed_checks']==[]


def test_wall_time_grammar():
    assert campaign.wall_seconds('48:00:00')==172800 and campaign.wall_seconds('1-12:00:00')==129600
    for bad in ('3600','48:00','2-48','1:2:3:4'):
        with pytest.raises(common.SpecError):campaign.wall_seconds(bad)
    cs={'account':'<ACCOUNT>','partition':'shared','cpus':4,'mem_gb':8,'time':'48:00:00','lead_s':3600,'max_cont':1}
    campaign.check_slurm('c',cs);assert cs['time']=='2-00:00:00'


def test_collect_regenerates_and_flags_ambiguity(ran_chain,tmp_path):
    spec,path=ran_chain;o=tmp_path/'coll'
    assert collect.main(['--spec',str(path),'--out',str(o)])==0
    assert len((o/'points.csv').read_text().splitlines())==4
    for p in common.chain_dir(spec,'c1').glob('L*_z*.json'):p.unlink()
    assert collect.main(['--spec',str(path),'--out',str(o)])==0
    assert (o/'points.csv').read_text().splitlines()==[','.join(collect.HEADERS['points'])]
    # A shipped record with an ambiguous identification produces an explicit flag.
    rec=json.loads((ROOT/'reference/results/window_L8_z16_x0.126.json').read_text())
    fl=collect.ambiguity_flags('x0.126',8,16,rec['diagnostics']['records'])
    assert fl and all('ambiguous' in f and 'L=8' in f for f in fl)


def test_claims_under_excludes_archive(tmp_path):
    write_claim(tmp_path/'claims_archive'/'old_a.json.claim','1');write_claim(tmp_path/'b.json.claim','2')
    assert [c.name for c in common.claims_under(tmp_path)]==['b.json.claim']


@pytest.mark.parametrize('payload',['null','[]','{"theta": null}','"x"'])
def test_malformed_check_checkpoint_values_are_exit_65(ran_chain,payload):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1')
    (cdir/'L6_z16.json').unlink();Path(str(cdir/'L6_z16.json')+'.checkpoint.json').write_text(payload)
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_SEED
    st=json.loads((cdir/'state'/'9001.json').read_text());assert st['status']=='failed' and st['failed_checks']==[]


@pytest.mark.parametrize('payload',['[]','null','{"accepted": true}'])
def test_malformed_check_output_values_are_exit_65(ran_chain,payload):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1')
    (cdir/'L6_z16.json').write_text(payload)
    # Parent-side lineage checks do not cover a check step's OWN output; the child's reuse path must refuse it.
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_SEED
    st=json.loads((cdir/'state'/'9001.json').read_text());assert st['status']=='failed' and st['failed_checks']==[]


def test_hf01_expanded_root_fallback_at_x035():
    """Reference seed at x=0.35, L=8, nz16: the ground-only path missed the gate; the fallback converges."""
    from ht2d.density import DensitySolver
    t_=json.loads((ROOT/'reference/results/teacher_L6_x0.350.json').read_text())['basis_artifact']
    ref=json.loads((ROOT/'reference/results/window_L8_z16_x0.350.json').read_text())
    import numpy as np
    u=np.asarray(t_['isometry']);cap=u.shape[1]//2;u=u[:,list(range(16))+list(range(cap,cap+16))]
    s=DensitySolver(8,u,t_['scale'],window='vacuum',window_mode='consistent',backend='tensor',ncv=40,eig_tol=1e-12,residual_tol=1e-8)
    s.set_delta(.35);row=s.solve(ref['theta'],tol=3e-11,maxiter=50)
    assert abs(row['Delta_thermal']-ref['Delta_thermal'])<1e-9
    assert row['window_correction']['top_fixed_point_residual']<=1e-11


def test_check_only_binds_expected_output_bytes(ran_chain,monkeypatch):
    spec,path=ran_chain;st=common.find_step(spec,'c1',6,12)
    seed=common.check_initial_seed(spec,'c1')[1]
    ok,_=common.exact_request_valid(spec,'c1',st,seed,output_sha=sha(st['output']));assert ok
    ok,why=common.exact_request_valid(spec,'c1',st,seed,output_sha='0'*64);assert not ok   # IR-01


def test_sbatch_command_is_explicit_and_env_clean(tmp_path):
    import submit
    spec,_=make_spec(tmp_path)
    cmd=submit.sbatch_command(spec,'c1',tmp_path/'j.sbatch',tmp_path/'spec.json','abc')
    for opt in ('-A','-p','-t','-J','-o','--nodes=1','--cpus-per-task=1','--mem=8G','--signal=B:USR1@1800'):
        assert opt in cmd
    assert cmd[cmd.index('-p')+1]=='shared'
    env=submit.clean_env({'SBATCH_PARTITION':'compute','SBATCH_SIGNAL':'x','HOME':'/h'});assert env=={'HOME':'/h'}


def test_chain_verifies_receipt_and_env_before_claiming(tmp_path):
    spec,path=make_spec(tmp_path)
    rc=Path(spec['receipt']['path']);d=json.loads(rc.read_text());d['passed']=False;rc.write_text(json.dumps(d))
    assert chain.main(['--spec',str(path),'--chain','c1'])==common.EXIT_STAGE
    assert not common.chain_dir(spec,'c1').exists()
    spec2,path2=make_spec(tmp_path/'b')
    d=json.loads(path2.read_text());d['env']['env_id']='0'*16;del d['sha256'];d['sha256']=common.digest(d);hpc.atomic_json(path2,d)
    assert chain.main(['--spec',str(path2),'--chain','c1'])==common.EXIT_STAGE


def test_parent_validators_reject_malformed_json(ran_chain,tmp_path):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1')
    (cdir/'L8_z12.json').write_text('null')
    with pytest.raises(common.SpecError):common.validate_step(spec,'c1',8,12)          # IR-04
    assert not continuation.chain_complete(spec,'c1',[])
    o=tmp_path/'coll';assert collect.main(['--spec',str(path),'--out',str(o)])==0
    assert 'INVALID' in (o/'flags.txt').read_text()
    s=Path(spec['chains']['c1']['initial_seed']['path'])
    s2,p2=make_spec(tmp_path/'s');Path(s2['chains']['c1']['initial_seed']['path']).write_text('[]')
    d=json.loads(p2.read_text());d['chains']['c1']['initial_seed']['sha256']=sha(s2['chains']['c1']['initial_seed']['path'])
    del d['sha256'];d['sha256']=common.digest(d);hpc.atomic_json(p2,d)
    assert chain.main(['--spec',str(p2),'--chain','c1'])==common.EXIT_SEED


def test_freeze_is_exclusive_and_no_clobber(tmp_path):
    rel=tmp_path/'r.tar';rel.write_bytes(b'tar');man=tmp_path/'r.sha256';man.write_bytes(b'man')
    env_id=envcheck.identity()['env_id']
    release={'commit':'c','tar':str(rel),'tar_sha256':sha(rel),'manifest':str(man),'manifest_sha256':sha(man),'source_sha256':hpc.source_hash()}
    rc=tmp_path/'rc.json';rc.write_text(json.dumps({'passed':True,'tar_sha256':sha(rel),'manifest_sha256':sha(man),'source_sha256':hpc.source_hash(),'env_id':env_id}))
    req={'campaign':'f','logs':str(tmp_path/'logs'),
         'slurm':{'account':'<ACCOUNT>','partition':'shared','cpus':1,'mem_gb':4,'time':'01:00:00','lead_s':1800,'max_cont':0},
         'common':{'backend':'tensor','threads':1,'memory_limit_gib':2,'eig_tol':1e-12,'residual_tol':1e-8,'tuning_tol':3e-11,'ncv':40,'maxiter':50},
         'chains':{'c1':{'x':.3,'ladder':[6],'main':{'nz':12,'diagnostics':'none'},'checks':[],
                         'basis_src':str(TEACHER),'initial_seed_src':str(TEACHER),'initial_seed_origin':'reference_same_L'}}}
    p,s=campaign.freeze(req,release,sys.executable,rc,tmp_path/'camp')
    before=p.read_bytes()
    with pytest.raises(FileExistsError):campaign.freeze(req,release,sys.executable,rc,tmp_path/'camp')   # IR-06
    assert p.read_bytes()==before and json.loads(before)['chains']['c1']['slurm']['time']=='0-01:00:00'
    with pytest.raises(FileExistsError):campaign.publish_noclobber(p,{'x':1})
    assert p.read_bytes()==before


def test_step_graph_must_be_executable(tmp_path):
    spec,_=make_spec(tmp_path)
    bad=copy.deepcopy(spec);bad['chains']['c1']['ladder']=[]
    with pytest.raises(common.SpecError,match='empty'):campaign.check_edges(bad)
    bad=copy.deepcopy(spec);bad['chains']['c1']['checks']=[{'nz':12,'diagnostics':'none','L':'all'}]
    with pytest.raises(common.SpecError,match='duplicate'):campaign.check_edges(bad)
    ref=copy.deepcopy(spec['chains']['c1']);ref.pop('initial_seed');ref['ladder']=[6];ref['checks']=[]
    ref['seed_from']={'chain':'c1','L':6,'nz':12};spec['chains']['r']=ref
    ref2=copy.deepcopy(ref);ref2['seed_from']={'chain':'r','L':6,'nz':12};spec['chains']['r2']=ref2
    with pytest.raises(common.SpecError,match='rooted'):campaign.check_edges(spec)          # IR-07


def test_teacher_guess_rules_and_argv(tmp_path):
    spec,_=make_spec(tmp_path)
    t_=copy.deepcopy(spec['chains']['c1']);t_.pop('initial_seed');t_.pop('basis');t_['ladder']=[6];t_['checks']=[]
    t_['main']={'nz':24,'osc':192,'diagnostics':'none','train_keep':20,'guess':[0.1,-1.6]};spec['chains']['t']=t_
    campaign.check_edges(spec)
    argv=common.steps(spec,'t')[0]['argv'];i=argv.index('--guess');assert argv[i+1:i+3]==['0.1','-1.6']
    bad=copy.deepcopy(spec);bad['chains']['c1']['main']['guess']=[0.,0.]
    with pytest.raises(common.SpecError,match='guess'):campaign.check_edges(bad)
    bad=copy.deepcopy(spec);bad['chains']['t']['main']['guess']=[float('nan'),0.]
    with pytest.raises(common.SpecError,match='finite'):campaign.check_edges(bad)


def test_jump_flag_rule():
    assert collect.jump_flags('c',[(8,1.),(10,1.+1e-8),(12,1.+1e-8+5e-7)])                       # IR-08: no 1e-6 floor
    assert not collect.jump_flags('c',[(8,1.),(10,1.+1e-14),(12,1.+1e-14+5e-13)])              # below the 1e-10 noise floor
    assert not collect.jump_flags('c',[(8,1.),(10,1.01),(12,1.015)])


def test_x_one_eighth_admitted_as_benchmark(tmp_path):
    with pytest.raises(hpc.IntegrityError):hpc.run(hpc.parser().parse_args(['--L','4','--x','0.125','--nz','12','--osc','96','--output',str(tmp_path/'n.json'),'--check-only']))
    with pytest.raises(ValueError,match='1/8'):hpc.run(hpc.parser().parse_args(['--L','4','--x','0.1249','--nz','12','--osc','96','--output',str(tmp_path/'n.json'),'--check-only']))


def test_malformed_state_and_owner_records(ran_chain,capsys):
    spec,path=ran_chain;cdir=common.chain_dir(spec,'c1');q=lambda n:[]
    (cdir/'state'/'9001.json').write_text('null')                                       # F26
    assert continuation.guard(spec,'c1','9001','9100','n',state_fn=lambda j:'TIMEOUT',queue_fn=q,log=lambda *_:None)==75
    hpc.atomic_json(cdir/'state'/'9002.json',{'status':'stopped','failed_checks':[None]})
    assert continuation.guard(spec,'c1','9002','9100','n',state_fn=lambda j:'TIMEOUT',queue_fn=q,log=lambda *_:None)==75
    import status
    capsys.readouterr();assert status.main(['--spec',str(path)])==0
    assert 'state=INVALID' in capsys.readouterr().out
    (cdir/'bad.json.claim').mkdir();(cdir/'bad.json.claim'/'owner.json').write_text('[1]')
    write_claim(cdir/'good.json.claim','5')
    removed,kept=recover_claims.recover(cdir,apply=True,state_fn=lambda j:'TIMEOUT',log=lambda *_:None)
    assert [c.name for c in removed]==['good.json.claim'] and (cdir/'bad.json.claim').exists()


def test_release_tree_bound_to_manifest(tmp_path):
    spec,path=make_spec(tmp_path)
    assert common.verify_release_tree(spec)>10
    man=Path(spec['release']['manifest']);lines=man.read_text().splitlines()
    lines=[('0'*64+'  '+l.split('  ',1)[1]) if l.endswith('cluster/expanse/chain.py') else l for l in lines]
    man.write_text('\n'.join(lines)+'\n')
    spec['release']['manifest_sha256']=sha(man)
    with pytest.raises(common.EnvUnavailable,match='differs'):common.verify_release_tree(spec)      # IR2-02


def test_status_reports_from_validated_snapshot(ran_chain,monkeypatch,capsys):
    import status
    spec,path=ran_chain
    real=common.check_predecessor
    monkeypatch.setattr(status,'check_predecessor',lambda s,ref,cache=None:(real(s,ref,cache=cache)[0],'0'*64))
    rows=status.chain_status(spec,'c1');assert all('INVALID' in r[3] and 'changed after validation' in r[3] for r in rows)   # IR2-03


def test_chain_without_basis_validates(tmp_path):
    spec,path=make_spec(tmp_path,ladder=(6,),checks=[])
    d=json.loads(path.read_text());c=d['chains']['c1'];c.pop('basis');c['main']={'nz':12,'osc':96,'diagnostics':'none'}
    del d['sha256'];d['sha256']=common.digest(d);hpc.atomic_json(path,d)
    assert chain.main(['--spec',str(path),'--chain','c1'])==0
    common.validate_step(json.loads(path.read_text()),'c1',6,12)                                       # IR2-04


def test_initial_seed_nan_delta_refused(tmp_path):
    other=tmp_path/'nan.json';d=json.loads(TEACHER.read_text());d['delta']=float('nan');other.write_text(json.dumps(d))
    s,_=make_spec(tmp_path/'n',seed_src=other)
    with pytest.raises(common.SpecError,match='non-finite'):common.check_initial_seed(s,'c1')         # IR2-06


def test_freeze_paths_are_absolute(tmp_path,monkeypatch):
    rel=tmp_path/'r.tar';rel.write_bytes(b'tar');man=tmp_path/'r.sha256';man.write_bytes(b'man')
    env_id=envcheck.identity()['env_id']
    release={'commit':'c','tar':str(rel),'tar_sha256':sha(rel),'manifest':str(man),'manifest_sha256':sha(man),'source_sha256':hpc.source_hash()}
    rc=tmp_path/'rc.json';rc.write_text(json.dumps({'passed':True,'tar_sha256':sha(rel),'manifest_sha256':sha(man),'source_sha256':hpc.source_hash(),'env_id':env_id}))
    req={'campaign':'f','logs':'logs',
         'slurm':{'account':'<ACCOUNT>','partition':'shared','cpus':1,'mem_gb':4,'time':'01:00:00','lead_s':1800,'max_cont':0},
         'common':{'backend':'tensor','threads':1,'memory_limit_gib':2,'eig_tol':1e-12,'residual_tol':1e-8,'tuning_tol':3e-11,'ncv':40,'maxiter':50},
         'chains':{'c1':{'x':.3,'ladder':[6],'main':{'nz':12,'diagnostics':'none'},'checks':[],
                         'basis_src':str(TEACHER),'initial_seed_src':str(TEACHER),'initial_seed_origin':'reference_same_L'}}}
    monkeypatch.chdir(tmp_path)
    p,_=campaign.freeze(req,release,os.path.relpath(sys.executable),'rc.json','camp')                 # IR2-05
    s=json.loads(p.read_text())
    assert all(os.path.isabs(v) for v in (s['logs'],s['env']['python'],s['receipt']['path'],s['root']))
    with pytest.raises(common.SpecError,match='absolute'):
        campaign.freeze(req,{**release,'tar':'r.tar'},sys.executable,'rc.json','camp2')


def test_receipt_must_bind_manifest(tmp_path):
    spec,_=make_spec(tmp_path)
    common.check_receipt(spec)
    rc=Path(spec['receipt']['path']);d=json.loads(rc.read_text());d['manifest_sha256']='0'*64;rc.write_text(json.dumps(d))
    spec['receipt']['sha256']=sha(rc)
    with pytest.raises(common.SpecError,match='manifest'):common.check_receipt(spec)                 # IR3-01


def test_jacobian_condition_persisted_before_line_search():
    from ht2d.solver import DressedSolver
    calls=[]
    s=DressedSolver(4,12,96,window='vacuum',window_mode='consistent',backend='tensor',ncv=40,eig_tol=1e-12,residual_tol=1e-8,
                    checkpoint=lambda th,h:calls.append(json.loads(json.dumps(h))))
    s.set_delta(.3);s.solve(None,tol=3e-11,maxiter=50)
    # Some checkpoint write must already contain the CURRENT iteration's condition (IR3-02).
    assert any(h and 'jacobian_condition' in h[-1] for h in calls)


@pytest.mark.parametrize('damage',['scale','column'])
def test_malformed_basis_artifact_is_integrity(tmp_path,damage):
    d=json.loads(TEACHER.read_text());a=d['basis_artifact']
    if damage=='scale':del a['scale']
    else:
        for row in a['isometry']:row[19]=row[19]*1.5                     # column outside nz12, inside keep 20
    bad=tmp_path/'bad.json';bad.write_text(json.dumps(d))
    argv=['--L','6','--x','.3','--nz','12','--basis',str(bad),'--diagnostics','none','--threads','1','--output',str(tmp_path/'o.json')]
    assert hpc.main(argv)==65                                                                       # IR3-03
