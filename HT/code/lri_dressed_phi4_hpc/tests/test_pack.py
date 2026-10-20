import json,os,signal,subprocess,sys,time
from pathlib import Path
import pytest
from lri_dressed.io import envelope,atomic_json,source_fingerprint,release_fingerprint,runtime,digest
from lri_dressed.lease import Lease

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pack_node


def fake_launcher(tmp_path,max_attempts=1,items=()):
    L=object.__new__(pack_node.Launcher)
    L.campaign=tmp_path;L.job='test';L.host=os.uname().nodename;L.running={};L.backoff={};L.forwarded=False
    L.dirs={k:tmp_path/'items'/k for k in ('leases','done','failed')};L.dirs['superseded']=L.dirs['failed']/'superseded'
    for d in L.dirs.values():d.mkdir(parents=True,exist_ok=True)
    L.items={i['id']:i for i in items};L.source=source_fingerprint();L.verdicts={};L.failed_here=set();L.slurm=None
    L.events=tmp_path/'events.jsonl';L.a=type('A',(),{'claim_backoff':60.,'max_attempts':max_attempts})();return L


def start(L,iid,code):
    lease=Lease(L.dirs['leases']/iid);lease.acquire();log=L.campaign/f'{iid}.log';fh=open(log,'w')
    proc=subprocess.Popen([sys.executable,'-c',code],stdout=fh,stderr=subprocess.STDOUT,start_new_session=True)
    L.running[iid]={'proc':proc,'item':{'id':iid,'threads':1,'mem_gib':1,'deltas':[.2]},'lease':lease,'start':time.time(),'sent':[],'log':log,'fh':fh,'offset':0}
    return L.running[iid]


def outcome(L,iid):
    rec=L.running[iid];rec['proc'].wait(30);L.reap()
    ev=[json.loads(l) for l in L.events.read_text().splitlines()][-1]
    assert ev['item']==iid and not Lease(L.dirs['leases']/iid).holder()[1]   # lease released after reaping
    return ev['event']

SLEEPER='import signal,time\nsignal.signal(signal.SIGUSR1,lambda *a:None)\nsignal.signal(signal.SIGTERM,lambda *a:None)\ntime.sleep(60)'


def test_outcome_classification(tmp_path):
    L=fake_launcher(tmp_path)
    start(L,'safe','import sys;sys.exit(75)');assert outcome(L,'safe')=='interrupted'
    start(L,'claimed','import sys;sys.exit(73)');assert outcome(L,'claimed')=='claimed'
    # rc 0 without validated result envelopes is not completion
    start(L,'no_results','pass');assert outcome(L,'no_results')=='failed' and not (L.dirs['done']/'no_results.json').exists()
    assert 'completion check' in json.loads((L.dirs['failed']/'no_results.json').read_text())['error']
    r=start(L,'killed',SLEEPER);time.sleep(.5);L.signal_group(r,signal.SIGUSR1);L.signal_group(r,signal.SIGKILL)
    assert outcome(L,'killed')=='interrupted' and not (L.dirs['failed']/'killed.json').exists()
    r=start(L,'error_after_usr1','import sys,time;time.sleep(.5);sys.exit(1)');L.signal_group(r,signal.SIGUSR1)
    assert outcome(L,'error_after_usr1')=='failed'
    r=start(L,'oom_after_usr1',SLEEPER);time.sleep(.5);L.signal_group(r,signal.SIGUSR1);os.kill(r['proc'].pid,signal.SIGKILL)
    assert outcome(L,'oom_after_usr1')=='failed'
    r=start(L,'external_term','import time;time.sleep(60)');time.sleep(.5);os.kill(r['proc'].pid,signal.SIGTERM)
    assert outcome(L,'external_term')=='failed' and (L.dirs['failed']/'external_term.json').exists()


def receipt(path):
    atomic_json(path,envelope('validation',{},{'passed':True,'release_sha256':release_fingerprint(),'source_sha256':source_fingerprint(),'runtime':runtime()}))


def test_pack_campaign_end_to_end_and_schema_dispatch(tmp_path):
    camp=tmp_path/'camp';camp.mkdir();env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),NUMBA_NUM_THREADS='1')
    mk=[sys.executable,str(ROOT/'scripts/make_campaign.py'),'--pack','--campaign','t1','--bath-cuts','4','--nz','4','--osc','32',
        '--deltas','.24','.2','--windows','none','vacuum:consistent','--mem-gib','.01','--est-seconds','30','--seed-dir',str(ROOT/'inputs'),
        '--out',str(camp/'manifest.json')]
    subprocess.run(mk,check=True,env=env)
    p=subprocess.run(mk,env=env,capture_output=True,text=True);assert p.returncode!=0 and 'never replaced' in p.stderr
    m=json.loads((camp/'manifest.json').read_text());assert m['schema']=='lri-dressed-pack-v1' and len(m['items'])==4
    from lri_dressed.pack import item_id,completion_valid
    for it in m['items']:
        assert it['id']==item_id(it) and it['mem_gib']>=it['plan_envelope_gib'] and Path(it['seed_dir']).is_absolute()
    receipt(tmp_path/'receipt.json')
    p=subprocess.run([sys.executable,str(ROOT/'scripts/pack_node.py'),'--campaign',str(camp),'--receipt',str(tmp_path/'receipt.json'),
        '--cores','3','--mem-gib','8','--no-warmup','--poll','.2'],env=env,capture_output=True,text=True,timeout=600)
    assert p.returncode==0,p.stderr
    assert len(list((camp/'items/done').glob('*.json')))==4 and not list((camp/'items/failed').glob('*.json'))
    results=list((camp/'results').glob('*.json'));assert len(results)==4
    for it in m['items']:
        rec=json.loads((camp/'items/done'/f"{it['id']}.json").read_text())
        assert completion_valid(it,rec,source_fingerprint()) and len(rec['results'])==1
    # Tampering with a result invalidates the completion (also through the launcher's cache).
    it=m['items'][0];rec=json.loads((camp/'items/done'/f"{it['id']}.json").read_text());r=Path(rec['results'][0]['path'])
    L=fake_launcher(camp,items=m['items']);assert L.done_valid(it['id'])
    raw=json.loads(r.read_text());raw['payload']['Delta_thermal']+=1e-6;r.write_text(json.dumps(raw))
    assert not completion_valid(it,rec,source_fingerprint()) and not L.done_valid(it['id']) and L.eligible(it['id'])
    st=json.loads(subprocess.run([sys.executable,str(ROOT/'cluster/symmetry/status.py'),'--campaign',str(camp)],env=env,
        capture_output=True,text=True).stdout)
    assert st['done']==3 and st['invalid_completions']==[it['id']]      # the tampered item is not reported done
    # A pack manifest is rejected by the legacy lane runner, as is a stale receipt.
    p=subprocess.run([sys.executable,str(ROOT/'scripts/run_lane.py'),'--manifest',str(camp/'manifest.json'),'--index','0','--output',str(tmp_path/'o'),
        '--threads','1','--memory-limit-gib','1','--receipt',str(tmp_path/'receipt.json')],env=env,capture_output=True,text=True)
    assert p.returncode!=0 and 'pack_node.py' in p.stderr
    subprocess.run([sys.executable,str(ROOT/'scripts/make_campaign.py'),'--bath-cuts','4','--nz','4','--osc','32','--deltas','.24',
        '--out',str(tmp_path/'legacy.json')],check=True,env=env)
    stale=tmp_path/'stale.json';atomic_json(stale,envelope('validation',{},{'passed':True,'source_sha256':source_fingerprint(),'runtime':runtime()}))
    p=subprocess.run([sys.executable,str(ROOT/'scripts/run_lane.py'),'--manifest',str(tmp_path/'legacy.json'),'--index','0','--output',str(tmp_path/'o'),
        '--threads','1','--memory-limit-gib','1','--receipt',str(stale)],env=env,capture_output=True,text=True)
    assert p.returncode!=0 and 'stale' in p.stderr
    # Legacy lanes may not carry window options.
    r=json.loads((tmp_path/'legacy.json').read_text());r.pop('sha256');r['lanes'][0]['window']='vacuum';r['sha256']=digest(r)
    (tmp_path/'legacy_bad.json').write_text(json.dumps(r))
    p=subprocess.run([sys.executable,str(ROOT/'scripts/run_lane.py'),'--manifest',str(tmp_path/'legacy_bad.json'),'--index','0','--output',str(tmp_path/'o'),
        '--threads','1','--memory-limit-gib','1','--receipt',str(tmp_path/'receipt.json')],env=env,capture_output=True,text=True)
    assert p.returncode!=0 and 'raw prescription' in p.stderr


def test_cli_reports_claimed_point(tmp_path,monkeypatch):
    from lri_dressed.cli import main
    import lri_dressed.lease as lease_mod
    args=['run','--bath-cut','4','--nz','4','--osc','32','--deltas','.24','--threads','1','--output-dir',str(tmp_path/'run')]
    assert main(args+['--resume'])==0
    lock=next((tmp_path/'run/claims').glob('*.lock'))
    d=Lease(lock);g=d.generations()[-1]+1
    d.dir.joinpath(f'{g:012d}').write_text(json.dumps({'nonce':'x','host':'elsewhere','pid':1,'slurm_job':'99','proc_start':None}))
    monkeypatch.setattr(lease_mod,'slurm_job_alive',lambda job,restart=None:True)
    assert main(args+['--resume'])==73


def test_bounded_retry_and_supersede(tmp_path):
    item={'id':'flaky','threads':1,'mem_gib':1,'deltas':[.2]}
    L=fake_launcher(tmp_path,max_attempts=2,items=[item])
    start(L,'flaky','import sys;sys.exit(1)');assert outcome(L,'flaky')=='failed'
    assert L.attempts('flaky')==1 and not L.eligible('flaky')          # never twice in the same run
    L2=fake_launcher(tmp_path,max_attempts=2,items=[item]);assert L2.eligible('flaky')
    start(L2,'flaky','import sys;sys.exit(1)');assert outcome(L2,'flaky')=='failed' and L2.attempts('flaky')==2
    L3=fake_launcher(tmp_path,max_attempts=2,items=[item]);assert not L3.eligible('flaky')
    L3.supersede_failure('flaky');assert L3.attempts('flaky')==0 and list(L3.dirs['superseded'].glob('flaky.*.json'))


def test_stop_rechecked_before_each_launch(tmp_path,monkeypatch):
    item={'id':'x','threads':1,'mem_gib':1,'deltas':[.2]}
    L=fake_launcher(tmp_path,items=[item]);L.maintenance=lambda:False
    monkeypatch.setattr(pack_node,'STOP',True)
    assert L.launch(item) is False and not L.running and not Lease(L.dirs['leases']/'x').generations()


def test_make_campaign_rejects_bad_requests(tmp_path):
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
    base=[sys.executable,str(ROOT/'scripts/make_campaign.py'),'--bath-cuts','4','--nz','4','--osc','32']
    p=subprocess.run(base+['--deltas','.24','--windows','vacuum:consistent','--out',str(tmp_path/'l.json')],env=env,capture_output=True,text=True)
    assert p.returncode!=0 and 'without --pack' in p.stderr
    p=subprocess.run(base+['--deltas','.24','--eig-tol','1e-12','--out',str(tmp_path/'l.json')],env=env,capture_output=True,text=True)
    assert p.returncode!=0 and 'without --pack' in p.stderr
    p=subprocess.run(base+['--pack','--campaign','c','--deltas','.123','--seed-dir',str(ROOT/'inputs'),'--mem-gib','1','--est-seconds','5',
        '--out',str(tmp_path/'p.json')],env=env,capture_output=True,text=True)
    assert p.returncode!=0 and 'no accepted seed' in p.stderr
    subprocess.run(base+['--pack','--campaign','c','--deltas','.123','--seed-dir',str(ROOT/'inputs'),'--mem-gib','1','--est-seconds','5',
        '--allow-bridges','--out',str(tmp_path/'p.json')],env=env,check=True,capture_output=True)


def test_stop_during_child_startup_is_a_safe_interrupt(tmp_path):
    """INSPECT2-02: USR1 sent immediately after spawn (before handlers exist) must give rc 75, not death."""
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),NUMBA_NUM_THREADS='1')
    cmd=[sys.executable,'-m','lri_dressed','run','--bath-cut','4','--nz','4','--osc','32','--deltas','.24','--threads','1',
         '--output-dir',str(tmp_path/'r'),'--seed-dir',str(ROOT/'inputs')]
    p=subprocess.Popen(cmd,env=env,start_new_session=True,preexec_fn=pack_node.block_shutdown_signals,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.killpg(p.pid,signal.SIGUSR1)
    assert p.wait(120)==75 and list((tmp_path/'r/checkpoints').glob('*.json'))
    # A numerical failure after a stop request is still a failure (rc 1), not an interrupt: covered by
    # test_outcome_classification (error_after_usr1).
