import json,os,multiprocessing,time
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from lri_spin import Config,run
from lri_spin.io import identity,save_state,load_state,Interrupted,IntegrityError,claim,AlreadyRunning,read_record,write_record
from lri_spin.workflow import fixed,critical,plan,check_allocation
from lri_spin.validation import validate_result,audit_tangent

@pytest.mark.parametrize('tangent,observers',[(False,True),(True,True),(False,False)])
def test_restart_exact(tmp_path,tangent,observers):
    c=Config(keep=8,nb=4,nsites=12);args=dict(tangent=tangent,observers=observers)
    ident=identity(c,.4,'test');cp=tmp_path/'state.npz';box={}
    def checkpoint(s,force):
        if s['meta']['next_site']==6:
            save_state(cp,ident,s);raise Interrupted('test')
    expected=run(.4,c,**args)
    with pytest.raises(Interrupted):run(.4,c,checkpoint=checkpoint,**args)
    state=load_state(cp,ident);actual=run(.4,c,resume_state=state,**args)
    assert actual['records']==expected['records']
    with pytest.raises(IntegrityError):load_state(cp,identity(c,.41,'test'))


def test_gate_resume_corruption(tmp_path):
    c=Config(keep=8,nb=4,nsites=10)
    a=fixed(.4,c,tmp_path/'a');b=fixed(.4,c,tmp_path/'a',resume=True)
    assert a['records']==b['records']
    with pytest.raises(FileExistsError):fixed(.4,c,tmp_path/'a')
    with pytest.raises(IntegrityError):fixed(.41,c,tmp_path/'a',resume=True)
    p=tmp_path/'a'/'result.json';v=json.loads(p.read_text());v['payload']['records'][0]['odd_gap']+=.1;p.write_text(json.dumps(v))
    with pytest.raises(IntegrityError):fixed(.4,c,tmp_path/'a',resume=True)


def test_checkpoint_corruption(tmp_path):
    cp=tmp_path/'c.npz';c=Config();i=identity(c,.4,'test');state={'en0':np.ones(2),'meta':{'a':2}}
    save_state(cp,i,state);z=bytearray(cp.read_bytes());z[len(z)//2]^=3;cp.write_bytes(z)
    with pytest.raises(IntegrityError):load_state(cp,i)


def hold_lock(path,event):
    with claim(path):
        event.set();time.sleep(5)


def test_lock(tmp_path):
    ctx=multiprocessing.get_context('spawn');ev=ctx.Event();p=ctx.Process(target=hold_lock,args=(tmp_path/'l',ev));p.start()
    try:
        assert ev.wait(3)
        with pytest.raises(AlreadyRunning):
            with claim(tmp_path/'l'):pass
    finally:p.terminate();p.join()
    with claim(tmp_path/'l'):pass


def test_plan_guards(monkeypatch):
    p=plan(Config(keep=128,nb=16));assert p['max_dimension_per_parity']==2048
    with pytest.raises(MemoryError):check_allocation(Config(),.001)
    monkeypatch.setenv('OMPI_COMM_WORLD_SIZE','2')
    with pytest.raises(ValueError):check_allocation(Config())


def test_critical_midpoint_and_resume(tmp_path):
    c=Config(s=.8,Lambda=3,keep=8,nb=4,nsites=12)
    d=critical(c,tmp_path/'r',atol=1e-10,maxiter=48)
    lo,hi=d['critical_flow']['critical_tuning']['bracket']
    assert d['critical_flow']['alpha']==(lo+hi)/2
    d2=critical(c,tmp_path/'r',atol=1e-10,maxiter=48,resume=True)
    assert d2['tangent']['records']==d['tangent']['records']
    assert read_record(tmp_path/'r'/'result.json')['tuning']['flo']>0
    assert read_record(tmp_path/'r'/'result.json')['tuning']['fhi']<0


def test_critical_exhaustion(tmp_path):
    with pytest.raises(RuntimeError,match='exhausted'):
        critical(Config(keep=4,nb=3,nsites=8),tmp_path/'r',maxiter=1)
    assert not (tmp_path/'r'/'result.json').exists()


def test_invalid_output():
    c=Config(keep=4,nb=3,nsites=8);r=run(.4,c)
    r['records'][-1]['odd_gap']=float('nan')
    with pytest.raises(ValueError):validate_result(r,c)


def test_completed_checkpoint_finalizes_without_eigensolve(tmp_path,monkeypatch):
    import lri_spin.compat as co
    c=Config(keep=8,nb=4,nsites=12)
    a=fixed(.4,c,tmp_path/'a',tangent=True)
    (tmp_path/'a'/'result.json').unlink()
    def fail(*args,**kwargs):raise AssertionError('Should not diagonalize a completed checkpoint')
    monkeypatch.setattr(co,'eigh',fail)
    b=fixed(.4,c,tmp_path/'a',tangent=True,resume=True)
    assert a['records']==b['records']
    assert b['resumed_at_site']==c.nsites


def test_source_mismatch_rejected(tmp_path,monkeypatch):
    import lri_spin.io as io
    c=Config(keep=4,nb=3,nsites=8)
    fixed(.4,c,tmp_path/'a')
    monkeypatch.setattr(io,'source_hash',lambda:'not-the-same-solver')
    with pytest.raises(IntegrityError):fixed(.4,c,tmp_path/'a',resume=True)


def test_cli_signal_and_resume(tmp_path):
    import subprocess,sys,signal
    root=Path(__file__).resolve().parents[1]
    env=os.environ.copy();env['PYTHONPATH']=str(root/'src');env['OPENBLAS_NUM_THREADS']='1';env['MKL_NUM_THREADS']='1'
    command=[sys.executable,'-m','lri_spin','flow','--alpha','.4','--s','.8','--Lambda','3',
             '--keep','64','--nb','10','--nsites','80','--checkpoint-every','2',
             '--output-dir',str(tmp_path/'run')]
    with open(tmp_path/'log','w') as log:
        child=subprocess.Popen(command,env=env,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+15
            while not (tmp_path/'run'/'state.npz').exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            assert child.poll() is None
            child.send_signal(signal.SIGUSR1)
            assert child.wait(timeout=15)==75
        finally:
            if child.poll() is None:child.kill();child.wait()
        result=subprocess.run(command+['--resume'],env=env,stdout=log,stderr=log,timeout=30)
        assert result.returncode==0,(tmp_path/'log').read_text()
    r=read_record(tmp_path/'run'/'result.json')
    assert 0<r['resumed_at_site']<80 and len(r['records'])==80
