import json,os,signal,subprocess,sys,time
from pathlib import Path
import pytest
from lri_eh.runtime import config,seal,validate_result,AcceptanceError,atomic_json,fingerprint,Preempted,load_checkpoint
from lri_eh.runner import run,paths


def test_resume_and_rejection(tmp_path):
    r=run(8,7,tmp_path,4,2.)
    assert run(8,7,tmp_path,4,2.,True)['payload_sha256']==r['payload_sha256']
    path=paths(tmp_path,8,7)['result']
    bad=json.loads(path.read_text());bad['delta_C'][7]+=1
    atomic_json(path,bad)
    with pytest.raises(AcceptanceError):run(8,7,tmp_path,4,2.,True)
    for update in [lambda x:x['validation'].update(max_tuning_residual=float('nan')),
                   lambda x:x.update(delta_C=x['delta_C'][:-1]),
                   lambda x:x['delta_r'].__setitem__(2,.1),
                   lambda x:x['delta_C'].__setitem__(4,.1),
                   lambda x:x.update(acceptance='pending')]:
        b=json.loads(json.dumps(r));update(b)
        with pytest.raises((AcceptanceError,ValueError)):validate_result(seal(b))


def test_checkpoint_resume_after_interrupt(tmp_path,monkeypatch):
    import lri_eh.numerics as n
    original=n.components_for_reference
    calls=[]
    def fail(space,psi,p,degree,g1):
        calls.append(p)
        if p==1:raise Preempted('test injected interruption')
        return original(space,psi,p,degree,g1)
    monkeypatch.setattr(n,'components_for_reference',fail)
    with pytest.raises(Preempted):run(8,7,tmp_path,4,2.)
    cp=load_checkpoint(paths(tmp_path,8,7)['checkpoint'],config(8,7))
    assert set(cp['components'])=={'0'}
    monkeypatch.setattr(n,'components_for_reference',original)
    resumed=run(8,7,tmp_path,4,2.,True)
    fresh=run(8,7,tmp_path/'fresh',4,2.)
    import numpy as np
    for k in ('delta_C','delta_r','delta_g'):np.testing.assert_array_equal(resumed[k],fresh[k])
    assert resumed['attempt']==2


def test_source_mismatch_and_retry_budget(tmp_path):
    run(4,5,tmp_path,4,2.)
    p=paths(tmp_path,4,5);p['result'].unlink()
    cp=json.loads(p['checkpoint'].read_text());cp['config']['source_sha256']='0'*64;atomic_json(p['checkpoint'],seal(cp))
    with pytest.raises(AcceptanceError):run(4,5,tmp_path,4,2.,True)
    cp['config']=config(4,5);atomic_json(p['checkpoint'],seal(cp))
    with pytest.raises(RuntimeError,match='budget'):run(4,5,tmp_path,4,2.,True,max_attempts=1)


def test_lock_and_supervisor_death(tmp_path):
    # Solver child keeps its own flock if its launching supervisor is killed.
    lock=tmp_path/'held.lock';ready=tmp_path/'ready';pidfile=tmp_path/'pid'
    childcode=f"from lri_eh.runtime import claim;from pathlib import Path;import time,os\nwith claim({str(lock)!r}):\n Path({str(ready)!r}).write_text('ready');time.sleep(60)"
    supervise=f"import subprocess,sys,time;from pathlib import Path\np=subprocess.Popen([sys.executable,'-c',{childcode!r}]);Path({str(pidfile)!r}).write_text(str(p.pid));p.wait()"
    env=os.environ.copy();env['PYTHONPATH']=str(Path(__file__).resolve().parents[1])
    supervisor=subprocess.Popen([sys.executable,'-c',supervise],env=env)
    try:
        for _ in range(200):
            if ready.exists():break
            time.sleep(.02)
        assert ready.exists()
        os.kill(supervisor.pid,signal.SIGKILL);supervisor.wait()
        from lri_eh.runtime import claim,BusyError
        with pytest.raises(BusyError):
            with claim(lock):pass
    finally:
        if pidfile.exists():os.kill(int(pidfile.read_text()),signal.SIGKILL)
        if supervisor.poll() is None:supervisor.kill();supervisor.wait()
    # No stale lock persists after process death. Never unlink/recreate its inode.
    for _ in range(100):
        try:
            with claim(lock):return
        except BusyError:time.sleep(.01)
    pytest.fail('lock not released')


def test_stopflag_signal():
    from lri_eh.runtime import StopFlag
    with StopFlag() as flag:
        os.kill(os.getpid(),signal.SIGUSR1)
        with pytest.raises(Preempted):flag.check()


def test_stale_atomic_temporary_cannot_block_new_writer(tmp_path):
    target=tmp_path/'data.json'
    stale=target.with_name(target.name+f'.tmp.{os.getpid()}');stale.write_text('old crashed writer')
    atomic_json(target,{'ok':True})
    assert json.loads(target.read_text())=={'ok':True}
    assert stale.read_text()=='old crashed writer'


def test_completed_components_need_no_basis(monkeypatch):
    import lri_eh.numerics as n
    state={}
    def save(cp):state.update(json.loads(json.dumps(cp)))
    a=n.compute(8,7,2.,save=save)
    def forbidden(*a,**kw):raise AssertionError('Complete scalar checkpoint rebuilt the basis')
    monkeypatch.setattr(n,'Space',forbidden)
    b=n.compute(8,7,2.,checkpoint=state)
    assert b['ladder_calls']==0 and b['reused_completed_components']
    for k in ('delta_C','delta_r','delta_g'):assert a[k]==b[k]
