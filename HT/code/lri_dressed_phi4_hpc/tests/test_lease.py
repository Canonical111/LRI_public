import json,multiprocessing as mp,os,socket,subprocess,sys
from pathlib import Path
import pytest
from lri_dressed.lease import Lease,Claimed,break_lease,break_unreadable,owner_state,identity,WIDTH
ROOT=Path(__file__).resolve().parents[1]


def dead_pid():
    p=subprocess.Popen([sys.executable,'-c','pass']);p.wait();return p.pid


def write_gen(path,g,record):
    d=Lease(path).dir;d.mkdir(parents=True,exist_ok=True)
    (d/f'{g:0{WIDTH}d}').write_text(record if isinstance(record,str) else json.dumps(record))


def dead_local(job=None):return {'nonce':'dead','host':socket.gethostname(),'pid':dead_pid(),'proc_start':None,'slurm_job':job,'time':0}


def foreign(job='4242'):return {'nonce':'f','host':'some-other-node','pid':1,'proc_start':None,'slurm_job':job,'time':0}


def test_acquire_release_and_monotonic_generations(tmp_path):
    k=tmp_path/'item';a=Lease(k);a.acquire();assert a.gen==1
    with pytest.raises(Claimed):Lease(k).acquire()
    a.release();b=Lease(k);b.acquire();assert b.gen==2          # never reuses 1
    b.release();assert sorted(p.name for p in b.dir.iterdir())==[f'{1:0{WIDTH}d}',f'{1:0{WIDTH}d}.released',f'{2:0{WIDTH}d}',f'{2:0{WIDTH}d}.released']


def test_contention_between_processes(tmp_path):
    k=tmp_path/'item';a=Lease(k);a.acquire()
    code=f"from lri_dressed.lease import Lease\nLease({str(k)!r}).acquire();print('acquired')"
    p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert p.returncode!=0 and 'Claimed' in p.stderr


def test_same_host_dead_owner_is_reclaimed(tmp_path):
    k=tmp_path/'item';write_gen(k,1,dead_local());l=Lease(k);l.acquire();assert l.gen==2


@pytest.mark.parametrize('answer,claimable',[(True,False),(None,False),(False,True)])
def test_foreign_owner_by_slurm_state(tmp_path,answer,claimable):
    k=tmp_path/'item';write_gen(k,1,foreign());l=Lease(k,slurm=lambda job,restart=None:answer)
    if claimable:l.acquire();assert l.gen==2
    else:
        with pytest.raises(Claimed):l.acquire()


def test_foreign_owner_without_job_is_unknown(tmp_path):
    k=tmp_path/'item';write_gen(k,1,foreign(job=None))
    assert owner_state(foreign(job=None),slurm=lambda j,restart=None:False)=='unknown'
    with pytest.raises(Claimed):Lease(k,slurm=lambda j,restart=None:False).acquire()


def test_unreadable_generation_stays_claimed_at_any_age(tmp_path):
    k=tmp_path/'item';write_gen(k,1,'{not json');f=Lease(k).name(1);os.utime(f,(0,0))   # very old
    with pytest.raises(Claimed):Lease(k,slurm=lambda j,restart=None:False).acquire()


def test_delayed_reclaimer_cannot_double_own(tmp_path):
    """R2-F1: A decides 'free' on a dead gen 1 and pauses; B acquires and releases; C acquires; A resumes."""
    k=tmp_path/'item';write_gen(k,1,dead_local());seen={}
    def pause(stage):
        if seen:return
        seen['B']=b=Lease(k);b.acquire();b.release()
        seen['C']=c=Lease(k);c.acquire()
    with pytest.raises(Claimed):Lease(k,hook=pause).acquire()
    top,owner,free=Lease(k).holder()
    assert top==3 and not free and owner['nonce']==seen['C'].me['nonce']


def test_yield_after_publish(tmp_path):
    k=tmp_path/'item'
    def higher(stage):write_gen(k,5,identity())
    a=Lease(k,hook=higher)
    with pytest.raises(Claimed):a.acquire()
    assert a.tombstoned(1) and Lease(k).holder()[0]==5


def _race(args):
    rounds,base,barrier,q=args
    held=[]
    for r in range(rounds):
        barrier.wait()
        try:l=Lease(f'{base}/r{r}');l.acquire();held.append(l);q.put(r)
        except Claimed:pass
    barrier.wait()


def test_simultaneous_reclaimers_race(tmp_path):
    rounds=200;n=6;dead=dead_local()
    for r in range(rounds):write_gen(tmp_path/f'r{r}',1,dead)
    ctx=mp.get_context('fork');barrier=ctx.Barrier(n);q=ctx.Queue()
    procs=[ctx.Process(target=_race,args=((rounds,str(tmp_path),barrier,q),)) for _ in range(n)]
    for p in procs:p.start()
    for p in procs:p.join(300)
    wins=[]
    while not q.empty():wins.append(q.get())
    assert all(p.exitcode==0 for p in procs)
    counts={r:wins.count(r) for r in range(rounds)}
    assert set(counts.values())=={1},{r:c for r,c in counts.items() if c!=1}


def test_break_lease_is_fenced(tmp_path):
    k=tmp_path/'item';write_gen(k,1,foreign(job='77'))
    with pytest.raises(Claimed):break_lease(k,2,'77',slurm=lambda j,restart=None:False)          # wrong generation
    with pytest.raises(Claimed):break_lease(k,1,'78',slurm=lambda j,restart=None:False)          # mismatched job
    with pytest.raises(Claimed):break_lease(k,1,'77',slurm=lambda j,restart=None:True)           # live job
    with pytest.raises(Claimed):break_lease(k,1,'77',slurm=lambda j,restart=None:None)           # unknown job
    assert 'tombstoned' in break_lease(k,1,'77',slurm=lambda j,restart=None:False)
    l=Lease(k,slurm=lambda j,restart=None:True);l.acquire();assert l.gen==2
    with pytest.raises(Claimed):break_lease(k,1,'77',slurm=lambda j,restart=None:False)          # delayed break after newer owner
    assert not Lease(k).holder()[2]


def test_unreadable_needs_maintenance_path(tmp_path):
    k=tmp_path/'item';write_gen(k,1,'garbage')
    with pytest.raises(Claimed):break_lease(k,1,'1',slurm=lambda j,restart=None:False)
    break_unreadable(k,1);l=Lease(k);l.acquire();assert l.gen==2


def test_maintenance_marker_blocks_claims(tmp_path,monkeypatch):
    from lri_dressed.io import claim
    marker=tmp_path/'MAINTENANCE';marker.write_text('x');monkeypatch.setenv('LRI_MAINTENANCE_MARKER',str(marker))
    with pytest.raises(Claimed):
        with claim(tmp_path/'k.lock'):pass
    marker.unlink()
    with claim(tmp_path/'k.lock'):pass


def test_break_unreadable_refuses_identifiable_owner(tmp_path):
    k=tmp_path/'item';write_gen(k,1,foreign(job='5'))
    with pytest.raises(Claimed):break_unreadable(k,1)


def test_status_recovery_is_confined_to_the_campaign(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('status',ROOT/'cluster/symmetry/status.py');st=importlib.util.module_from_spec(spec);spec.loader.exec_module(st)
    camp=tmp_path/'A';(camp/'items/leases').mkdir(parents=True);other=tmp_path/'B';(other/'items/leases').mkdir(parents=True)
    write_gen(other/'items/leases/it',1,'garbage')
    with pytest.raises(SystemExit):st.campaign_key(camp,other/'items/leases/it')
    write_gen(camp/'items/leases/it',1,'garbage');assert st.campaign_key(camp,camp/'items/leases/it').name=='it'


def test_slurm_incarnation(monkeypatch):
    import lri_dressed.lease as L
    class P:
        def __init__(s,rc,out,err=''):s.returncode=rc;s.stdout=out;s.stderr=err
    answers={}
    monkeypatch.setattr(L.subprocess,'run',lambda cmd,**kw:answers['p'])
    answers['p']=P(0,'JobId=7 JobState=RUNNING Restarts=0 BatchHost=cn1')
    assert L.slurm_job_alive('7',restart=0) is True
    answers['p']=P(0,'JobId=7 JobState=RUNNING Restarts=1 BatchHost=cn2')
    assert L.slurm_job_alive('7',restart=0) is False            # requeued: the recorded incarnation is dead
    answers['p']=P(0,'JobId=7 JobState=PENDING Restarts=1')
    assert L.slurm_job_alive('7',restart=1) is False
    answers['p']=P(1,'','slurm_load_jobs error: Invalid job id specified')
    assert L.slurm_job_alive('7') is False
    answers['p']=P(1,'','Socket timed out')
    assert L.slurm_job_alive('7') is None
    answers['p']=P(0,'JobId=7 JobState=WEIRD Restarts=0')
    assert L.slurm_job_alive('7') is None


def test_break_lease_requires_recorded_job_and_identity(tmp_path):
    k=tmp_path/'a';write_gen(k,1,dead_local(job=None))
    rec=Lease(k).read(1);rec['host']='elsewhere';write_gen(k,1,rec)
    with pytest.raises(Claimed):break_lease(k,1,'None',slurm=lambda j,restart=None:False)
    k2=tmp_path/'b';write_gen(k2,1,{})                          # parsed but unidentifiable
    with pytest.raises(Claimed):break_lease(k2,1,'1',slurm=lambda j,restart=None:False)
    assert 'tombstoned' in break_unreadable(k2,1)
