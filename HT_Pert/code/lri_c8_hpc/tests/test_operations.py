import copy,json,os,subprocess,sys,signal,time
from pathlib import Path
import numpy as np
import pytest
from lri_c8 import io
from lri_c8.cli import validate_checkpoint,merge
from lri_c8.engine import compute
ROOT=Path(__file__).resolve().parents[1]

def test_checksum(tmp_path):
    p=tmp_path/'a.json';io.atomic_save(p,{'a':[1,2]});assert io.read(p)=={'a':[1,2]}
    e=json.loads(p.read_text());e['payload']['a'][0]=3;p.write_text(json.dumps(e))
    with pytest.raises(ValueError):io.read(p)

def test_process_lock(tmp_path):
    p=tmp_path/'claim.lock'
    with io.claim(p):
        code='from lri_c8.io import claim\nwith claim('+repr(str(p))+'):pass'
        proc=subprocess.run([sys.executable,'-c',code],env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True)
        assert proc.returncode!=0 and b'already owned' in proc.stderr
        # The CLI maps a held claim to exit 73 ("owned elsewhere"), not a failure.
        env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
        lock=p.parent/'claims'/'raw_L4_d8.lock'
        with io.claim(lock):
            r=subprocess.run([sys.executable,'-m','lri_c8','run','--cutoff','4','--memory-limit-gib','2',
                              '--output-dir',str(p.parent)],env=env,capture_output=True)
            assert r.returncode==73
    with io.claim(p):pass

def test_signal_boundary():
    with io.StopFlag() as stop:
        os.kill(os.getpid(),signal.SIGUSR1)
        with pytest.raises(io.StopRequested):stop.boundary()

def test_resume_without_basis():
    a=compute(4)
    # Prove complete scalar checkpoint finalization does not allocate either basis.
    import lri_c8.engine as e
    old=e.PackedCore
    def fail(*a,**kw):raise AssertionError('unexpected basis construction')
    e.PackedCore=fail
    try:b=compute(4,low=a['low'],saved_components={int(k):v for k,v in a['components'].items()})
    finally:e.PackedCore=old
    np.testing.assert_array_equal(a['C'],b['C'])

def test_stop_and_scalar_resume(tmp_path):
    cp={}
    def low(x):cp['low']=x
    def saved(p,c):
        cp[p]=c
        if p==1:raise io.StopRequested('test interruption')
    with pytest.raises(io.StopRequested):compute(8,on_low=low,on_component=saved)
    assert 0 in cp and 1 in cp
    a=compute(8,low=cp['low'],saved_components={k:v for k,v in cp.items() if isinstance(k,int)})
    b=compute(8)
    np.testing.assert_array_equal(a['C'],b['C'])

def test_config_mismatch():
    cfg={'scheme':'raw'};r=compute(4);r['config']=cfg
    validate_checkpoint(r,cfg)
    with pytest.raises(ValueError):validate_checkpoint(r,{'scheme':'vacuum_only'})

def test_multirank_rejected(monkeypatch):
    monkeypatch.setenv('OMPI_COMM_WORLD_SIZE','4')
    with pytest.raises(RuntimeError):io.reject_multirank()

def test_cli_and_shard_assembly(tmp_path):
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'NUMBA_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    def call(*args,ok=True):
        r=subprocess.run([sys.executable,'-m','lri_c8',*map(str,args)],env=env,capture_output=True,text=True)
        if ok:assert r.returncode==0,(r.stdout,r.stderr)
        return r
    for p in (0,1,3,2):
        args=['run','--cutoff',4,'--threads',2,'--memory-limit-gib',2,'--reference',p,'--output-dir',tmp_path]
        call(*args);call(*args,'--resume')
    files=[tmp_path/f'raw_L4_d8_ref{p}.json' for p in (0,1,3,2)]
    # A solver (any node) writing the same destination holds its owner: assemble refuses.
    t=io.acquire_owner(io.owner_path(tmp_path/'assembled.json'))
    busy=call('assemble','--inputs',*files,'--output',tmp_path/'assembled.json',ok=False)
    assert busy.returncode==73 and not (tmp_path/'assembled.json').exists()
    io.release_owner(io.owner_path(tmp_path/'assembled.json'),t)
    call('assemble','--inputs',*files,'--output',tmp_path/'assembled.json')
    call('export','--inputs',tmp_path/'assembled.json','--output',tmp_path/'list.json')
    assert json.loads((tmp_path/'list.json').read_text())[0]['C'][8]>0
    bad=call('assemble','--inputs',files[0],files[0],files[2],files[3],'--output',tmp_path/'bad.json',ok=False)
    assert bad.returncode!=0 and not (tmp_path/'bad.json').exists()

def test_supervisor_death_does_not_release_child_claim(tmp_path):
    lock=tmp_path/'owner.lock';ready=tmp_path/'ready.json'
    child_code=('import os,json,time\nfrom lri_c8.io import claim\n'
                f'with claim({str(lock)!r}):\n'
                f' open({str(ready)!r},"w").write(json.dumps({{"pid":os.getpid()}}))\n'
                ' time.sleep(60)\n')
    supervisor_code=('import subprocess,sys,time\n'
                     f'p=subprocess.Popen([sys.executable,"-c",{child_code!r}])\n'
                     'time.sleep(60)\n')
    env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
    proc=subprocess.Popen([sys.executable,'-c',supervisor_code],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    pid=None
    try:
        end=time.time()+120  # cold imports on a fresh compute node can take a while
        while time.time()<end and not ready.exists():time.sleep(.05)
        assert ready.exists();pid=json.loads(ready.read_text())['pid']
        proc.kill();proc.wait(timeout=5)
        with pytest.raises(RuntimeError):
            with io.claim(lock):pass
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        if pid:
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
    end=time.time()+30
    while True:
        try:
            with io.claim(lock):break
        except RuntimeError:
            if time.time()>end:raise
            time.sleep(.05)

def test_complete_checkpoint_bypasses_memory_allocation_gate():
    a=compute(4)
    b=compute(4,low=a['low'],saved_components={int(k):v for k,v in a['components'].items()},memory_limit_gib=1e-9)
    np.testing.assert_array_equal(a['C'],b['C'])

def test_normalised_digest_roundtrip(tmp_path):
    # int keys crossing a digit boundary used to produce unreadable manifests.
    for keys in ([8,10],[96,100],[9,10]):
        p=tmp_path/f'k{keys[0]}.json';io.atomic_save(p,{'plans':{k:{'x':k} for k in keys}})
        assert io.read(p)=={'plans':{str(k):{'x':k} for k in keys}}
    assert not list(tmp_path.glob('*.tmp.*'))

def test_owner_files(tmp_path,monkeypatch):
    o=tmp_path/'owners/lane.owner'
    monkeypatch.delenv('SLURM_JOB_ID',raising=False)
    t=io.acquire_owner(o)
    with pytest.raises(io.ClaimBusy):io.acquire_owner(o)
    io.release_owner(o,'not-the-token');assert o.exists()
    io.release_owner(o,t);assert not o.exists()
    # Never taken over, not even by the same Slurm job (only the submit wrapper clears).
    monkeypatch.setenv('SLURM_JOB_ID','111');io.acquire_owner(o)
    with pytest.raises(io.ClaimBusy):io.acquire_owner(o)
    assert json.loads(o.read_text())['slurm_job_id']=='111'

def test_signal_during_startup_is_graceful(tmp_path):
    # A Slurm warning that arrives while the solver is still importing is honoured at the
    # first boundary (exit 75) instead of killing the process with the default action.
    # The signal is sent right after the entry point installs its provisional handlers,
    # i.e. before lri_c8.cli (numpy/numba/scipy) is imported. The installed `lri-c8`
    # command and `python -m lri_c8` both use this entry point.
    assert 'lri-c8 = "lri_c8._entry:main"' in (ROOT/'pyproject.toml').read_text()
    assert 'from ._entry import main' in (ROOT/'src/lri_c8/__main__.py').read_text()
    env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
    code=('import os,signal,sys\nfrom lri_c8 import _entry,_signals\norig=_signals.install\n'
          'def install():\n orig()\n assert "lri_c8.cli" not in sys.modules\n os.kill(os.getpid(),signal.SIGUSR1)\n'
          '_signals.install=install\nsys.exit(_entry.main(sys.argv[1:]))')
    r=subprocess.run([sys.executable,'-c',code,'run','--cutoff','4','--memory-limit-gib','2','--output-dir',str(tmp_path)],
                     env=env,capture_output=True,text=True)
    assert r.returncode==75,(r.stdout,r.stderr)
    assert not (tmp_path/'raw_L4_d8.json').exists()

def test_export_mixed_threads_and_backends(tmp_path):
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'NUMBA_NUM_THREADS':'2'}
    def call(*args):
        return subprocess.run([sys.executable,'-m','lri_c8',*map(str,args)],env=env,capture_output=True,text=True)
    assert call('run','--cutoff',4,'--threads',1,'--outer-backend','stored','--memory-limit-gib',2,'--output-dir',tmp_path).returncode==0
    assert call('run','--cutoff',6,'--threads',2,'--outer-backend','ranked','--memory-limit-gib',2,'--output-dir',tmp_path).returncode==0
    assert call('run','--cutoff',8,'--scheme','vacuum_only','--memory-limit-gib',2,'--output-dir',tmp_path).returncode==0
    ok=call('export','--inputs',tmp_path/'raw_L4_d8.json',tmp_path/'raw_L6_d8.json','--output',tmp_path/'raw.json')
    assert ok.returncode==0,ok.stderr
    rows=json.loads((tmp_path/'raw.json').read_text())
    assert [r['config']['runtime']['threads'] for r in rows]==[1,2] and rows[1]['config']['outer_backend']=='ranked'
    bad=call('export','--inputs',tmp_path/'raw_L4_d8.json',tmp_path/'vacuum_only_L8_d8.json','--output',tmp_path/'mixed.json')
    assert bad.returncode!=0 and 'Mixed' in bad.stderr and not (tmp_path/'mixed.json').exists()
