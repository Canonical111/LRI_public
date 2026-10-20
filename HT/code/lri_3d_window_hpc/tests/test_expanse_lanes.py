"""Expanse lane/campaign layer: chaining, binding, stop handling, recovery, submission argv.

Tiny real points (L4..L8) are used where the point driver itself must be exercised.
Slurm is replaced by stub executables on PATH; nothing is submitted.
"""
import json,os,signal,stat,sys,textwrap,threading,time
from pathlib import Path
import pytest

R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'code'));sys.path.insert(0,str(R/'cluster/expanse'))
import lanes,campaign  # noqa: E402
from ht3d.hpc import digest,source_hash,run,parser  # noqa: E402


def spec(**over):
    s={'campaign':'t','x':[0.6],'teacher':{'L':4,'nz':12,'osc':96,'keep':8,'diagnostics':'none'},
       'ladder':[6,8],'window':{'nz':8,'diagnostics':'none'},
       'side':[{'name':'k6_L8','after_L':8,'argv':['--nz','6','--diagnostics','none']}],
       'groups':[{'name':'g','cpus':2,'threads':2,'mem_gib':4,'wall':'00:10:00','lead_s':60,'partition':'shared'}]}
    s.update(over);return s


def make_manifest(tmp,s=None,runtime=None):
    s=s or spec();out=tmp/'camp';out.mkdir(exist_ok=True)
    m={'schema':lanes.SCHEMA,'campaign':s['campaign'],'source_sha256':source_hash(),'release_sha256':'test',
       'release_tar':'/nonexistent.tar','release_tar_sha256':'0'*64,'runtime':runtime or lanes.runtime_identity(),
       'account':'yun124','throttle':4,'spec':s,'lanes':campaign.build_lanes(s,out)}
    m['sha256']=digest(m);(out/'manifest.json').write_text(json.dumps(m));return out


@pytest.fixture(autouse=True)
def env(monkeypatch,tmp_path):
    # Never change NUMBA_NUM_THREADS in-process: numba refuses a different value once its
    # threads exist (seen on a fresh Expanse node). Children get theirs from the runner.
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','1')
    # The suite also runs inside a Slurm job (the Expanse receipt): the runner's campaign-binding
    # check must only see the job identity a test sets on purpose.
    for k in ('SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_ARRAY_JOB_ID','SLURM_ARRAY_TASK_ID'):monkeypatch.delenv(k,raising=False)
    yield


# ---------------------------------------------------------------- freeze / manifest
def test_build_lanes_chaining_and_paths(tmp_path):
    lanes_=campaign.build_lanes(spec(),tmp_path)
    assert len(lanes_)==1;st=lanes_[0]['steps']
    assert [s['name'] for s in st]==['teacher_L4','window_L6','window_L8','k6_L8']
    assert st[1]['seed_from']==0 and st[1]['basis_from']==0
    assert st[2]['seed_from']==1 and st[2]['basis_from']==0
    assert st[3]['seed_from']==2 and st[3]['basis_from']==0      # side check seeded by window_L8, not reused later
    assert all(Path(s['output']).is_absolute() for s in st)
    assert all('--threads' in s['argv'] and s['argv'][s['argv'].index('--threads')+1]=='2' for s in st)


def test_build_lanes_rejects_bad_resources(tmp_path):
    s=spec();s['groups'][0]['threads']=4
    with pytest.raises(ValueError,match='threads'):campaign.build_lanes(s,tmp_path)
    s=spec(per_L={'8':{'memory_limit_gib':16}})
    with pytest.raises(ValueError,match='above the lane allocation'):campaign.build_lanes(s,tmp_path)
    s=spec();s['window']['extra_argv']=['--seed','/x']
    with pytest.raises(ValueError,match='runner-owned'):campaign.build_lanes(s,tmp_path)


def test_freeze_requires_receipt_and_refuses_overwrite(tmp_path,monkeypatch):
    monkeypatch.setattr(lanes,'release_fingerprint',lambda root=None:'rel')
    tar=tmp_path/'r.tar';tar.write_bytes(b'x');sha=lanes.file_hash(tar)
    sp=tmp_path/'spec.json';sp.write_text(json.dumps(spec()))
    rc=tmp_path/'receipt.json'
    rc.write_text(json.dumps({'passed':False,'source_sha256':source_hash(),'release_sha256':'rel','runtime':lanes.runtime_identity()}))
    args=lambda out:campaign.main(['freeze','--spec',str(sp),'--receipt',str(rc),'--release-tar',str(tar),'--release-tar-sha256',sha,'--out',str(out)])
    with pytest.raises(ValueError,match='did not pass'):args(tmp_path/'c1')
    rc.write_text(json.dumps({'passed':True,'source_sha256':source_hash(),'release_sha256':'other','runtime':lanes.runtime_identity()}))
    with pytest.raises(ValueError,match='different source/release'):args(tmp_path/'c1')
    rc.write_text(json.dumps({'passed':True,'source_sha256':source_hash(),'release_sha256':'rel','runtime':lanes.runtime_identity()}))
    assert args(tmp_path/'c1')==0
    m=lanes.load_manifest(tmp_path/'c1/manifest.json');assert m['runtime']==lanes.runtime_identity()
    with pytest.raises(FileExistsError):args(tmp_path/'c1')


# ---------------------------------------------------------------- request binding
def test_expected_request_matches_real_records(tmp_path):
    t=tmp_path/'t.json';w=tmp_path/'w.json'
    a1=['--L','4','--x','0.6','--nz','12','--osc','96','--window','vacuum','--train-keep','8','--diagnostics','none','--threads','2']
    assert run(parser().parse_args([*a1,'--output',str(t)]))==0
    assert lanes.expected_request([*a1,'--output',str(t),'--resume'],{})==json.loads(t.read_text())['request_digest']
    a2=['--L','6','--x','0.6','--nz','8','--window','vacuum','--diagnostics','none','--threads','2','--seed',str(t),'--basis',str(t)]
    assert run(parser().parse_args([*a2,'--output',str(w)]))==0
    b=t.read_bytes()
    assert lanes.expected_request([*a2,'--output',str(w)],{'seed':b,'basis':b})==json.loads(w.read_text())['request_digest']
    assert lanes.expected_request([*a2,'--output',str(w)],{'seed':b+b' ','basis':b})!=json.loads(w.read_text())['request_digest']


def test_driver_rejects_input_changed_after_hashing(tmp_path,monkeypatch):
    t=tmp_path/'t.json'
    assert run(parser().parse_args(['--L','4','--x','0.6','--nz','12','--osc','96','--train-keep','8','--diagnostics','none','--output',str(t)]))==0
    monkeypatch.setenv('HT3D_FROZEN_INPUTS',json.dumps({str(t.resolve()):'0'*64}))
    with pytest.raises(ValueError,match='Inputs changed'):
        run(parser().parse_args(['--L','6','--x','0.6','--nz','8','--seed',str(t),'--basis',str(t),'--diagnostics','none','--output',str(tmp_path/'w.json')]))


# ---------------------------------------------------------------- runner
def test_lane_runs_reuses_and_rejects_tampering(tmp_path):
    camp=make_manifest(tmp_path);r=lanes.Runner(camp/'manifest.json',0,release_check=False,forward_interval=0.2)
    assert r.run()==0
    st=r.lane['steps'];assert lanes.lane_states(r.lane)==['done']*len(st)
    first=Path(st[2]['output']).read_bytes()
    assert lanes.Runner(camp/'manifest.json',0,release_check=False).run()==0      # full reuse, nothing recomputed
    assert Path(st[2]['output']).read_bytes()==first
    # A valid-JSON mutation of a predecessor (still accepted=true) is caught by the snapshot check,
    # by status/resubmit (lane_states) and by the driver's own reuse check on a rerun.
    d=json.loads(Path(st[1]['output']).read_text());d['theta'][0]+=1e-3
    Path(st[1]['output']).write_text(json.dumps(d))
    teacher=Path(st[0]['output']).read_bytes()
    with pytest.raises(lanes.Refused,match='failed validation'):
        r.snapshot(1,{'seed':teacher,'seed_path':st[0]['output'],'basis':teacher,'basis_path':st[0]['output']})
    states=lanes.lane_states(r.lane)
    assert states[0]=='done' and states[1].startswith('invalid')
    assert lanes.Runner(camp/'manifest.json',0,release_check=False).run()!=0
    assert (camp/'lane_failures'/'lane_000.json').exists()


def test_external_inputs_continuation(tmp_path):
    first=make_manifest(tmp_path)
    assert lanes.Runner(first/'manifest.json',0,release_check=False).run()==0
    s=spec(ladder=[10],side=[]);s.pop('teacher')
    s['continue_from']={'campaign_dir':str(first),'group':'g','teacher':'teacher_L4','seed':'window_L8'}
    lanes_=campaign.build_lanes(s,tmp_path/'cont')
    st=lanes_[0]['steps'];assert [x['name'] for x in st]==['window_L10']
    assert st[0]['seed_external']['path'].endswith('window_L8.json') and st[0]['basis_external']['path'].endswith('teacher_L4.json')
    m={'schema':lanes.SCHEMA,'campaign':'c','source_sha256':source_hash(),'release_sha256':'test','release_tar':'/x',
       'release_tar_sha256':'0'*64,'runtime':lanes.runtime_identity(),'account':'yun124','throttle':4,'spec':s,'lanes':lanes_}
    m['sha256']=digest(m);(tmp_path/'cont').mkdir(exist_ok=True);(tmp_path/'cont/manifest.json').write_text(json.dumps(m))
    assert lanes.Runner(tmp_path/'cont/manifest.json',0,release_check=False).run()==0
    assert lanes.lane_states(lanes_[0])==['done']
    # a mutated earlier record is refused when freezing a continuation (R21)
    d=json.loads(Path(st[0]['seed_external']['path']).read_text());d['theta'][1]+=1e-3
    keep=Path(st[0]['seed_external']['path']).read_bytes()
    Path(st[0]['seed_external']['path']).write_text(json.dumps(d))
    with pytest.raises(ValueError,match='failed validation'):campaign.build_lanes(s,tmp_path/'cont2')
    Path(st[0]['seed_external']['path']).write_bytes(keep)
    # an external input changed after freeze is refused
    p=Path(st[0]['seed_external']['path']);p.write_bytes(p.read_bytes()+b' ')
    Path(st[0]['output']).unlink()
    with pytest.raises(lanes.Refused,match='external seed changed'):lanes.Runner(tmp_path/'cont/manifest.json',0,release_check=False).run()
    bad=dict(st[0]);bad['seed_from']=0
    with pytest.raises(lanes.Refused,match='both chained and external'):lanes.resolve_inputs(bad,{})


def test_per_L_overrides_names_and_containment(tmp_path):
    s=spec(per_L={'8':{'nz':6,'diagnostics':'first','max_bath_states':123456}})
    st=campaign.build_lanes(s,tmp_path)[0]['steps']
    a8=next(x for x in st if x['name']=='window_L8')['argv']
    assert a8[a8.index('--nz')+1]=='6' and a8[a8.index('--diagnostics')+1]=='first' and a8[a8.index('--max-bath-states')+1]=='123456'
    a6=next(x for x in st if x['name']=='window_L6')['argv'];assert a6[a6.index('--nz')+1]=='8'
    with pytest.raises(ValueError,match='unsupported keys'):campaign.build_lanes(spec(per_L={'8':{'osc':10}}),tmp_path)
    for bad in ('/abs','../up','a/b','..'):
        s=spec();s['groups'][0]['name']=bad
        with pytest.raises(ValueError,match='path component'):campaign.build_lanes(s,tmp_path)
    s=spec();s['side'][0]['name']='../../escape'
    with pytest.raises(ValueError,match='path component'):campaign.build_lanes(s,tmp_path)
    (tmp_path/'outside').mkdir();(tmp_path/'results').mkdir()
    os.symlink(tmp_path/'outside',tmp_path/'results'/'g')                  # symlinked group directory escapes
    with pytest.raises(ValueError,match='escapes'):campaign.build_lanes(spec(),tmp_path)


def test_runtime_mismatch_refused(tmp_path):
    rt=lanes.runtime_identity();rt['numpy']='0.0.0'
    camp=make_manifest(tmp_path,runtime=rt)
    with pytest.raises(lanes.Refused,match='Runtime differs'):lanes.Runner(camp/'manifest.json',0,release_check=False).run()


FAKE_CHILD=textwrap.dedent('''
    import signal,sys,time
    time.sleep(float(sys.argv[1]))                  # "imports": SIGUSR1 still ignored (inherited SIG_IGN)
    flag=[]
    signal.signal(signal.SIGUSR1,lambda s,f:flag.append(s))
    t=time.time()
    while time.time()-t<20:
        if flag:sys.exit(75)
        time.sleep(0.05)
    sys.exit(3)
''')


def _fake_runner(tmp_path,delay):
    child=tmp_path/'child.py';child.write_text(FAKE_CHILD)
    camp=make_manifest(tmp_path)
    return lanes.Runner(camp/'manifest.json',0,child=[sys.executable,str(child),str(delay)],release_check=False,forward_interval=0.2)


def test_stop_before_launch(tmp_path):
    r=_fake_runner(tmp_path,0.1);r.stop=True
    assert r.run()==75
    assert not any(Path(s['output']).exists() for s in r.lane['steps'])


def test_stop_during_child_startup_window_is_redelivered(tmp_path):
    r=_fake_runner(tmp_path,1.0)
    threading.Timer(0.3,lambda:os.kill(os.getpid(),signal.SIGUSR1)).start()
    t=time.time();rc=r.run()
    assert rc==75 and time.time()-t<8      # not killed during startup, not left running for 20 s


def test_stop_during_real_step_then_resume(tmp_path):
    s=spec(ladder=[6,8,10],side=[])
    camp=make_manifest(tmp_path,s)
    r=lanes.Runner(camp/'manifest.json',0,release_check=False,forward_interval=0.2)
    threading.Timer(0.5,lambda:os.kill(os.getpid(),signal.SIGUSR1)).start()
    assert r.run()==75
    assert not Path(r.lane['steps'][-1]['output']).exists()
    assert lanes.Runner(camp/'manifest.json',0,release_check=False).run()==0


# ---------------------------------------------------------------- slurm stubs / recovery
def stub_bin(tmp_path,squeue,sacct):
    b=tmp_path/'bin';b.mkdir()
    for name,body in (('squeue',squeue),('sacct',sacct)):
        p=b/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(p.stat().st_mode|stat.S_IEXEC)
    return b


@pytest.mark.parametrize('squeue,sacct,expect',[
    ('echo "slurm_load_jobs error: Invalid job id specified" >&2; exit 1','echo "37|TIMEOUT"','TERMINAL'),
    ('exit 0','printf "37|CANCELLED by 123\\n"','TERMINAL'),
    ('echo "37|nm|36|1"','echo "37|RUNNING"','LIVE'),
    ('exit 0','echo "37|RUNNING"','LIVE'),
    ('exit 0','exit 1','UNKNOWN'),
    ('echo boom >&2; exit 1','echo "37|COMPLETED"','UNKNOWN'),
    ('exit 0','printf "36_1|COMPLETED\\n"','UNKNOWN'),          # only an array-style id: not the exact individual record
])
def test_job_state_exact_individual_id(tmp_path,monkeypatch,squeue,sacct,expect):
    monkeypatch.setenv('PATH',str(stub_bin(tmp_path,squeue,sacct))+os.pathsep+os.environ['PATH'])
    assert campaign.job_state('37',retries=2,pause=0)[0]==expect


def make_claim(path,token,job):
    c=Path(str(path)+'.claim');c.mkdir(parents=True)
    (c/'owner.json').write_text(json.dumps({'token':token,'slurm_job_id':job}));return c


def test_recover_tombstones_only_confirmed_terminal(tmp_path):
    (tmp_path/'tombstones').mkdir();log=lambda **e:None
    c=make_claim(tmp_path/'a.json','T1','37')
    assert not campaign.recover_claim(tmp_path,c,False,log,query=lambda j:('LIVE','x')) and c.exists()
    assert not campaign.recover_claim(tmp_path,c,False,log,query=lambda j:('UNKNOWN','x')) and c.exists()
    assert campaign.recover_claim(tmp_path,c,True,log,query=lambda j:('TERMINAL','TIMEOUT')) and c.exists()   # dry run
    assert campaign.recover_claim(tmp_path,c,False,log,query=lambda j:('TERMINAL','TIMEOUT')) and not c.exists()
    assert len(list((tmp_path/'tombstones').iterdir()))==1
    c2=Path(str(tmp_path/'b.json')+'.claim');c2.mkdir();(c2/'owner.json').write_text(json.dumps({'token':'T'}))
    assert not campaign.recover_claim(tmp_path,c2,False,log,query=lambda j:('TERMINAL','x')) and c2.exists()


def test_recover_never_removes_replacement_writer(tmp_path):
    """Recoverer A reads a dead owner; meanwhile B tombstones it and writer W claims the path."""
    (tmp_path/'tombstones').mkdir();log=lambda **e:None
    c=make_claim(tmp_path/'a.json','DEAD','37')
    def interleave(job):
        c.rename(tmp_path/'tombstones'/'by-B')            # recoverer B
        make_claim(tmp_path/'a.json','LIVE-W','99')       # replacement writer W
        return 'TERMINAL','COMPLETED'
    assert not campaign.recover_claim(tmp_path,c,False,log,query=interleave)
    assert json.loads((c/'owner.json').read_text())['token']=='LIVE-W'


def test_admin_lock_is_exclusive(tmp_path):
    with campaign.admin_lock(tmp_path):
        with pytest.raises(campaign.LockHeld):
            with campaign.admin_lock(tmp_path):pass
    assert not (tmp_path/'.admin.lock').exists()


# ---------------------------------------------------------------- submission argv
def test_sbatch_argv_and_resource_groups(tmp_path,monkeypatch,capsys):
    s=spec(x=[0.6,0.55]);s['groups'].append({'name':'big','cpus':8,'threads':8,'mem_gib':32,'wall':'12:00:00','lead_s':1200,'partition':'shared','x':[0.6]})
    camp=make_manifest(tmp_path,s);m=lanes.load_manifest(camp/'manifest.json')
    monkeypatch.setattr(campaign,'survey',lambda p:[])
    recs=[]
    monkeypatch.setattr(campaign.subprocess,'run',lambda *a,**k:pytest.fail('dry run must not call sbatch'))
    campaign._submit(camp,m,[0,1,2],5,True)
    out=capsys.readouterr().out.splitlines();cmds=[l for l in out if l.startswith('sbatch')]
    assert len(cmds)==2                               # one array per resource tuple
    small=next(c for c in cmds if '--cpus-per-task=2' in c);big=next(c for c in cmds if '--cpus-per-task=8' in c)
    for c in (small,big):
        for flag in ('-A yun124','-p shared','--nodes=1','--ntasks-per-node=1','--signal=B:USR1@'):assert flag in c
        assert str(camp/'logs')+'/%x_%A_%a.out' in c
    assert '--array=0,1%5' in small and '--mem=4G' in small and '-t 00:10:00' in small
    assert '--array=2%5' in big and '--mem=32G' in big


def test_intent_journal_blocks_duplicate_after_lost_job_id(tmp_path,monkeypatch):
    """sbatch accepted the array but the id never reached the journal: the job name still blocks resubmission."""
    camp=make_manifest(tmp_path);m=lanes.load_manifest(camp/'manifest.json')
    monkeypatch.setattr(campaign,'survey',lambda p:[])
    real_append=campaign._append;calls=[]
    def append(c,rec):
        if 'array_job_id' in rec:raise OSError('journal write failed after sbatch')
        calls.append(rec);real_append(c,rec)
    monkeypatch.setattr(campaign,'_append',append)
    class P:returncode=0;stdout='4242\n';stderr=''
    monkeypatch.setattr(campaign.subprocess,'run',lambda *a,**k:P())
    with pytest.raises(OSError):campaign._submit(camp,m,[0],4,False)
    name=calls[0]['name'];assert name.startswith('ht3d-t-') and 'array_job_id' not in campaign.journal(camp)[0]
    monkeypatch.undo()
    b=stub_bin(tmp_path,f'echo "4242_0|{name}|4242|0"','exit 0')
    monkeypatch.setenv('PATH',str(b)+os.pathsep+os.environ['PATH'])
    assert campaign.live_lanes(camp)=={0}
    with pytest.raises(RuntimeError,match='already have a pending/running job'):
        campaign.main(['submit',str(camp),'--dry-run'])


def test_charges_count_requeued_attempts(tmp_path,monkeypatch):
    camp=make_manifest(tmp_path)
    campaign._append(camp,{'name':'ht3d-t-abc','lanes':[0]});campaign._append(camp,{'name':'ht3d-t-abc','array_job_id':'500'})
    m=json.loads((camp/'manifest.json').read_text());m.pop('sha256');m['created']='20261007T000000Z';m['sha256']=digest(m)
    (camp/'manifest.json').write_text(json.dumps(m))
    rows=['501|500_0|ht3d-t-abc|REQUEUED|2026-10-07T01:00:00|3600|billing=7200,cpu=2,mem=4G,node=1|2|4G|shared',
          '501|500_0|ht3d-t-abc|COMPLETED|2026-10-07T03:00:00|1800|billing=7200,cpu=2,mem=4G,node=1|2|4G|shared',
          '501|500_0|ht3d-t-abc|COMPLETED|2026-10-07T03:00:00|1800|billing=7200,cpu=2,mem=4G,node=1|2|4G|shared',
          '777|777|other-job|COMPLETED|2026-10-07T03:00:00|1800|billing=7200,cpu=2,mem=4G,node=1|2|4G|shared']
    b=stub_bin(tmp_path,'exit 0','case "$*" in *--duplicates*) printf "%s\\n" '+' '.join(f"'{r}'" for r in rows)+';; *) exit 1;; esac')
    monkeypatch.setenv('PATH',str(b)+os.pathsep+os.environ['PATH'])
    ch=campaign.charges(camp)
    assert len(ch)==2 and abs(sum(c['su_measured'] for c in ch)-3.0)<1e-9     # (1 h + 0.5 h) x 7200/3600, duplicate row once
    assert abs(sum(c['su_estimated'] for c in ch)-3.0)<1e-9                   # max(2 cpus, 4G/2) = 2 SU/h
    assert all(c['su_estimated']>0 for c in ch)


def test_window_defaults_and_unknown_keys(tmp_path):
    s=spec();s['window'].update(max_bath_states=3333333,memory_limit_gib=2.5)
    st=campaign.build_lanes(s,tmp_path)[0]['steps']
    a=next(x for x in st if x['name']=='window_L8')['argv']
    assert a[a.index('--max-bath-states')+1]=='3333333' and a[a.index('--memory-limit-gib')+1]=='2.5'
    s=spec();s['window']['osc']=10
    with pytest.raises(ValueError,match='window: unsupported keys'):campaign.build_lanes(s,tmp_path)
    s=spec();s['teacher']['seed']='x'
    with pytest.raises(ValueError,match='teacher: unsupported keys'):campaign.build_lanes(s,tmp_path)


@pytest.mark.parametrize('extra,match',[
    (['--memory-limit-gib','128'],'above the lane allocation'),
    (['--seed=/tmp/x'],'runner-owned'),
    (['--see','/tmp/x'],'runner-owned'),                      # abbreviation of --seed
    (['--basis','/tmp/x'],'runner-owned'),
    (['--out','/tmp/y'],'runner-owned'),
    (['--resume'],'runner-owned'),
    (['--threads','1'],'--threads'),
])
def test_effective_argv_validation(tmp_path,extra,match):
    s=spec();s['window']['extra_argv']=extra
    with pytest.raises(ValueError,match=match):campaign.build_lanes(s,tmp_path)


def test_runner_checks_effective_inputs():
    step={'name':'s'}
    lanes.check_effective_inputs(step,['--L','6','--x','0.6','--seed','/a','--basis','/a','--output','/o'],{'/a':'h'})
    with pytest.raises(lanes.Refused):lanes.check_effective_inputs(step,['--L','6','--x','0.6','--seed','/a','--output','/o'],{})
    with pytest.raises(lanes.Refused):lanes.check_effective_inputs(step,['--L','6','--x','0.6','--output','/o'],{'/a':'h'})


def test_template_resources_refused(tmp_path):
    s=spec();s['groups'][0]['mem_gib']='FILL'
    with pytest.raises(ValueError,match='concrete'):campaign.build_lanes(s,tmp_path)
    s=spec(per_L={'8':{'max_bath_states':'FILL_FROM_PROBE'}})
    with pytest.raises(ValueError,match='positive number'):campaign.build_lanes(s,tmp_path)
    tpl=json.loads((R/'cluster/expanse/specs/calibration_L16.template.json').read_text())
    assert 16 not in json.loads((R/'cluster/expanse/specs/calibration.json').read_text())['ladder']
    with pytest.raises(ValueError):campaign.build_lanes(tpl,tmp_path)


def test_freeze_serialized_and_never_overwrites(tmp_path,monkeypatch):
    monkeypatch.setattr(lanes,'release_fingerprint',lambda root=None:'rel')
    tar=tmp_path/'r.tar';tar.write_bytes(b'x');sha=lanes.file_hash(tar)
    sp=tmp_path/'spec.json';sp.write_text(json.dumps(spec()))
    rc=tmp_path/'receipt.json'
    rc.write_text(json.dumps({'passed':True,'source_sha256':source_hash(),'release_sha256':'rel','runtime':lanes.runtime_identity()}))
    out=tmp_path/'c';out.mkdir()
    argv=['freeze','--spec',str(sp),'--receipt',str(rc),'--release-tar',str(tar),'--release-tar-sha256',sha,'--out',str(out)]
    with campaign.admin_lock(out):
        with pytest.raises(campaign.LockHeld):campaign.main(argv)
    real=campaign.build_lanes
    def racer(spec_,o):                       # a writer that bypassed the lock publishes first
        (Path(o)/'manifest.json').write_text('RACER');return real(spec_,o)
    monkeypatch.setattr(campaign,'build_lanes',racer)
    with pytest.raises(FileExistsError):campaign.main(argv)
    assert (out/'manifest.json').read_text()=='RACER'
    assert not list(out.glob('.manifest.*'))


def test_sacct_runs_in_utc(tmp_path,monkeypatch):
    camp=make_manifest(tmp_path)
    campaign._append(camp,{'name':'ht3d-t-abc','lanes':[0]})
    m=json.loads((camp/'manifest.json').read_text());m.pop('sha256');m['created']='20261007T180000Z';m['sha256']=digest(m)
    (camp/'manifest.json').write_text(json.dumps(m))
    row='501|500_0|ht3d-t-abc|COMPLETED|2026-10-07T19:00:00|3600|billing=7200,cpu=2,mem=4G,node=1|2|4G|shared'
    b=stub_bin(tmp_path,'exit 0',f'[ "$TZ" = UTC ] || exit 1; case "$*" in *"-S 2026-10-07T18:00:00"*) echo \'{row}\';; *) exit 1;; esac')
    monkeypatch.setenv('PATH',str(b)+os.pathsep+os.environ['PATH']);monkeypatch.setenv('TZ','America/Los_Angeles')
    ch=campaign.charges(camp);assert len(ch)==1 and ch[0]['su_measured']==2.0
    b2=stub_bin(tmp_path/'x','exit 0','exit 1') if (tmp_path/'x').mkdir() is None else None
    monkeypatch.setenv('PATH',str(b2)+os.pathsep+os.environ['PATH'])
    assert 'error' in campaign.charges(camp)[0]


def test_cached_campaign_side_steps(tmp_path):
    s=spec(cache_dir=str(tmp_path/'cache'));s['side'].append({'name':'raw_L8','after_L':8,'raw':True,'argv':['--nz','8','--osc','96','--diagnostics','none']})
    st=campaign.build_lanes(s,tmp_path/'c')[0]['steps']
    for x in st:assert x['argv'][x['argv'].index('--cache-dir')+1]==str((tmp_path/'cache').resolve()),x['name']


@pytest.mark.parametrize('mem',[3.9,0.5,0,True,'8'])
def test_integer_memory_only(tmp_path,mem):
    s=spec();s['groups'][0]['mem_gib']=mem
    with pytest.raises(ValueError,match='concrete'):campaign.build_lanes(s,tmp_path)


def test_runtime_identity_stable_across_imports(tmp_path):
    """Fresh interpreter: identity before and after importing the driver's operators/solver is equal."""
    import subprocess
    code=("import sys,json;sys.path[:0]=[%r,%r];import lanes;a=lanes.runtime_identity();"
          "import ht3d.operators,ht3d.solver,ht3d.density;b=lanes.runtime_identity();print(json.dumps(a==b))")%(str(R/'cluster/expanse'),str(R/'code'))
    out=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True).stdout.strip().splitlines()[-1]
    assert out=='true'


# ---------------------------------------------------------------- inspection round 1 fixes
import receipt  # noqa: E402


def test_receipt_ignores_collect_only_and_optimize(tmp_path,monkeypatch):
    w=tmp_path/'w';(w/'tests').mkdir(parents=True);(w/'validation').mkdir()
    (w/'pytest.ini').write_text('[pytest]\ntestpaths = tests\n')
    (w/'tests/test_a.py').write_text('def test_one():\n    assert 1\ndef test_two():\n    assert 2\n')
    (w/'tests/v_ok.py').write_text("import json,pathlib\nassert True\npathlib.Path('validation/r.json').write_text(json.dumps({'passed':True}))\n")
    (w/'tests/v_assert.py').write_text("import json,pathlib\nassert False,'numerical check'\npathlib.Path('validation/r2.json').write_text(json.dumps({'passed':True}))\n")
    logs=tmp_path/'logs';logs.mkdir()
    monkeypatch.setenv('PYTEST_ADDOPTS','--collect-only');monkeypatch.setenv('PYTHONOPTIMIZE','1')
    col,run=receipt.pytest_stage(w,logs)
    assert run['rc']==0 and run['collected']==2 and run['junit']['tests']==2 and run['junit']['skipped']==0
    assert receipt.validator_stage('ok','tests/v_ok.py','validation/r.json',w,logs)['rc']==0
    s=receipt.validator_stage('asserting','tests/v_assert.py','validation/r2.json',w,logs)
    assert s['rc']!=0 and not s['report_passed']                 # PYTHONOPTIMIZE did not strip the assert
    (w/'validation/stale.json').write_text(json.dumps({'passed':True}));time.sleep(1.2)
    (w/'tests/v_noop.py').write_text('pass\n')
    assert receipt.validator_stage('stale','tests/v_noop.py','validation/stale.json',w,logs)['rc']!=0


def test_squeue_counts_suspended_as_live(tmp_path,monkeypatch):
    b=stub_bin(tmp_path,'printf "9_1|n|9|1|SUSPENDED\\n9_2|n|9|2|COMPLETED\\n9_3|n|9|3|PENDING\\n"','exit 0')
    monkeypatch.setenv('PATH',str(b)+os.pathsep+os.environ['PATH']);monkeypatch.setenv('SQUEUE_STATES','RUNNING')
    rows=campaign.squeue_rows(['-n','n'],retries=1,pause=0)
    assert sorted(r.split('|')[3] for r in rows)==['1','3']


def test_failure_retired_after_success(tmp_path):
    camp=make_manifest(tmp_path)
    (camp/'lane_failures').mkdir(exist_ok=True)
    (camp/'lane_failures/lane_000.json').write_text(json.dumps({'lane':0,'step':0,'name':'teacher_L4','rc':1}))
    m=lanes.load_manifest(camp/'manifest.json')
    assert campaign.active_failure(camp,0,['pending']*4)['rc']==1
    assert lanes.Runner(camp/'manifest.json',0,release_check=False).run()==0
    assert not (camp/'lane_failures/lane_000.json').exists() and list((camp/'lane_failures/retired').iterdir())
    (camp/'lane_failures/lane_000.json').write_text(json.dumps({'lane':0,'step':1,'name':'window_L6','rc':1}))
    assert campaign.active_failure(camp,0,lanes.lane_states(m['lanes'][0])) is None        # step 1 has a validated output


@pytest.mark.parametrize('extra',[['--cache-dir','rel'],['--cache','/abs'],['--cache-dir=/abs']])
def test_cache_dir_only_from_spec(tmp_path,extra):
    s=spec();s['window']['extra_argv']=extra
    with pytest.raises(ValueError,match='cache-dir may only come'):campaign.build_lanes(s,tmp_path)
    with pytest.raises(ValueError,match='absolute'):campaign.build_lanes(spec(cache_dir='relative/cache'),tmp_path)


def test_malformed_record_is_invalid_not_fatal(tmp_path):
    camp=make_manifest(tmp_path);m=lanes.load_manifest(camp/'manifest.json')
    assert lanes.Runner(camp/'manifest.json',0,release_check=False).run()==0
    for bad in ('null','[]','"x"','{}'):
        Path(m['lanes'][0]['steps'][1]['output']).write_text(bad)
        st=lanes.lane_states(m['lanes'][0]);assert st[0]=='done' and st[1].startswith('invalid'),bad


def test_status_detail_reports_checkpoint_and_owner(tmp_path):
    out=tmp_path/'o.json';Path(str(out)+'.checkpoint.json').write_text('{}')
    make_claim(out,'T','37')
    d=campaign.step_detail({'output':str(out)},query=lambda j:('TERMINAL','TIMEOUT'))
    assert d['checkpoint'] and d['claim']['job']=='37' and d['claim']['state']==('TERMINAL','TIMEOUT')


# ---------------------------------------------------------------- inspection round 2 fixes (fix round 2)
def test_submit_env_overrides_inherited_bindings(tmp_path,monkeypatch):
    camp=make_manifest(tmp_path);m=lanes.load_manifest(camp/'manifest.json')
    monkeypatch.setattr(campaign,'survey',lambda p:[])
    for k in ('HT3D_MANIFEST','HT3D_RELEASE_TAR','HT3D_RELEASE_TAR_SHA256'):monkeypatch.setenv(k,'/stale/'+k)
    seen={}
    class P:returncode=0;stdout='77\n';stderr=''
    def fake(argv,**kw):seen.update(kw['env']);return P()
    monkeypatch.setattr(campaign.subprocess,'run',fake)
    campaign._submit(camp,m,[0],4,False)
    assert seen['HT3D_MANIFEST']==str(camp.resolve()/'manifest.json')
    assert seen['HT3D_RELEASE_TAR']==m['release_tar'] and seen['HT3D_RELEASE_TAR_SHA256']==m['release_tar_sha256']


def test_runner_refuses_unjournaled_job_name(tmp_path,monkeypatch):
    camp=make_manifest(tmp_path)
    monkeypatch.setenv('SLURM_JOB_ID','123');monkeypatch.setenv('SLURM_JOB_NAME','ht3d-other-abc')
    with pytest.raises(lanes.Refused,match='not journaled'):lanes.Runner(camp/'manifest.json',0,release_check=False).run()
    campaign._append(camp,{'name':'ht3d-other-abc','lanes':[0]})
    assert lanes.Runner(camp/'manifest.json',0,release_check=False).run()==0


def test_sparse_setting_is_part_of_runtime(tmp_path):
    import subprocess
    code=("import sys,json;sys.path[:0]=[%r,%r];import lanes;print(lanes.runtime_identity()['sparse_parallel_min_work'])")%(str(R/'cluster/expanse'),str(R/'code'))
    env=dict(os.environ,HT3D_SPARSE_PARALLEL_MIN_WORK='1')
    out=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True,env=env).stdout.strip().splitlines()[-1]
    assert out=='1' and lanes.runtime_identity()['sparse_parallel_min_work']!=1


@pytest.mark.parametrize('where,extra',[('per_L',['--L','6']),('window',['--x','0.55']),('teacher',['--L','5'])])
def test_cutoff_and_x_owned_by_expansion(tmp_path,where,extra):
    s=spec()
    if where=='per_L':s['per_L']={'8':{'extra_argv':extra}}
    else:s[where]['extra_argv']=extra
    with pytest.raises(ValueError,match='differ from the declared'):campaign.build_lanes(s,tmp_path)


def test_stop_during_preparation_launches_nothing(tmp_path,monkeypatch):
    marker=tmp_path/'launched';child=tmp_path/'c.py';child.write_text(f'open({str(marker)!r},"w").write("x")\n')
    camp=make_manifest(tmp_path)
    r=lanes.Runner(camp/'manifest.json',0,child=[sys.executable,str(child)],release_check=False)
    real=lanes.resolve_inputs
    def prep(step,produced):r.stop=True;return real(step,produced)
    monkeypatch.setattr(lanes,'resolve_inputs',prep)
    assert r.run()==75 and not marker.exists()


def test_child_handoff_exits_before_driver_work():
    import child as ch
    saved={s:signal.getsignal(s) for s in ch.STOPS}
    try:
        ch.pending.clear();ch.install()
        os.kill(os.getpid(),signal.SIGUSR1);time.sleep(0.05)
        assert ch.pending
        flag=[]
        with pytest.raises(SystemExit) as e:signal.signal(signal.SIGUSR1,lambda s,f:flag.append(s))
        assert e.value.code==75 and flag                        # driver's handler saw the stop, then we left
    finally:
        signal.signal=ch._install
        for s,h in saved.items():signal.signal(s,h)
        ch.pending.clear()


def test_guard_cap_is_explicit_opt_in(tmp_path):
    s=spec(per_L={'8':{'memory_limit_gib':6}})                  # guard above the 4G allocation
    with pytest.raises(ValueError,match='above the lane allocation'):campaign.build_lanes(s,tmp_path)
    s['groups'][0]['guard_cap_gib']=8
    with pytest.raises(ValueError,match='guard_cap_reason'):campaign.build_lanes(s,tmp_path)
    s['groups'][0]['guard_cap_reason']='  '
    with pytest.raises(ValueError,match='guard_cap_reason'):campaign.build_lanes(s,tmp_path)
    s['groups'][0]['guard_cap_reason']='measured peak below allocation'
    st=[t for t in campaign.build_lanes(s,tmp_path)[0]['steps'] if t['name']=='window_L8'][0]
    assert st['argv'][st['argv'].index('--memory-limit-gib')+1]=='6.0'
    s['groups'][0]['guard_cap_gib']=5                            # cap below the requested guard
    with pytest.raises(ValueError,match='above the lane allocation'):campaign.build_lanes(s,tmp_path)
    for bad in (4,3,True,'8'):                                  # cap must exceed mem_gib and be numeric
        s['groups'][0]['guard_cap_gib']=bad
        with pytest.raises(ValueError,match='guard_cap_gib must be'):campaign.build_lanes(s,tmp_path)


def test_large_shared_groups_and_charges(tmp_path):
    s=spec();s['groups'][0].update(partition='large-shared',mem_gib=320,cpus=16,threads=16)
    assert campaign.build_lanes(s,tmp_path)[0]['resources']['partition']=='large-shared'
    s['groups'][0]['mem_gib']=2400
    with pytest.raises(ValueError,match='concrete'):campaign.build_lanes(s,tmp_path)
    s=spec();s['groups'][0]['mem_gib']=300                       # above shared's 243G
    with pytest.raises(ValueError,match='concrete'):campaign.build_lanes(s,tmp_path)
    assert campaign.su_per_hour('large-shared',4,192*1024)==48.0 # job 54748336: billing 172800/3600
    assert campaign.su_per_hour('large-shared',16,64*1024)==64.0
    assert campaign.su_per_hour('shared',16,96*1024)==48.0       # job 54746632: billing 172800/3600
    assert campaign.su_per_hour('shared',8,32*1024)==16.0        # job 54739260: billing 57600/3600
