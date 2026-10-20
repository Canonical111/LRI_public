"""Manifest and exports exercise the actual CLI in independent processes."""
from pathlib import Path
import json,os,subprocess,sys
import pytest
from lri_spin import Config
from lri_spin.io import identity,source_hash,write_record,read_record

ROOT=Path(__file__).resolve().parents[1]

def execute(args,check=True):
    env=os.environ.copy()
    env.update(PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    return subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=env,
                          check=check,capture_output=True,text=True,timeout=20)

def test_manifest_receipt_item_and_exports(tmp_path):
    ident=identity(Config(),None,'receipt')
    receipt=tmp_path/'receipt.json'
    write_record(receipt,ident,{'passed':True,'source_sha256':source_hash(),'runtime':ident['runtime']})
    # The fixture receipt is synthetic: this tests transport/identity, not issuance.
    cfg=Config(s=.8,Lambda=3,keep=6,nb=4,nsites=10)
    items=tmp_path/'items.json'
    items.write_text(json.dumps([{'id':'tiny','kind':'critical','config':cfg.asdict(),
        'atol':1e-9,'maxiter':48,'memory_limit_gib':1}]))
    manifest=tmp_path/'manifest.json'
    execute([ROOT/'scripts/make_manifest.py','--items',items,'--receipt',receipt,'--output',manifest])
    command=['-m','lri_spin','item','--manifest',manifest,'--index','0',
             '--validation-receipt',receipt,'--output-dir',tmp_path/'jobs']
    execute(command)
    execute(command+['--resume'])
    result=tmp_path/'jobs/tiny/result.json'
    assert len(read_record(result)['tangent']['records'])==10
    plain=tmp_path/'all.json'
    execute(['-m','lri_spin','export',result,'--output',plain])
    assert json.loads(plain.read_text())[0]['_provenance']['source_sha256']==source_hash()
    execute([ROOT/'scripts/export_legacy.py',result,'--output-dir',tmp_path/'plain'])
    assert (tmp_path/'plain/tiny/critical.json').is_file()
    assert (tmp_path/'plain/tiny/tangent.json').is_file()
    # Same destination name may never silently overwrite a second record.
    failed=execute([ROOT/'scripts/export_legacy.py',result,result,'--output-dir',tmp_path/'bad'],False)
    assert failed.returncode!=0 and 'Duplicate destination' in failed.stderr
    env=json.loads(receipt.read_text());env['payload']['passed']=False
    receipt.write_text(json.dumps(env))
    failed=execute(command+['--resume'],False)
    assert failed.returncode!=0

@pytest.mark.parametrize('kill_supervisor',[False,True])
def test_lane_signal_and_solver_owned_claim(tmp_path,kill_supervisor):
    import signal,time
    from lri_spin.io import claim,AlreadyRunning
    ident=identity(Config(),None,'receipt')
    receipt=tmp_path/'receipt.json'
    write_record(receipt,ident,{'passed':True,'source_sha256':source_hash(),'runtime':ident['runtime']})
    cfg=Config(s=.8,Lambda=3,keep=64,nb=10,nsites=80)
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'source_sha256':source_hash(),'items':[
        {'id':'long','kind':'flow','alpha':.4,'config':cfg.asdict(),'memory_limit_gib':1}]}))
    folder=tmp_path/'jobs/long';lock=folder/'.claim.lock'
    env=os.environ.copy();env.update(PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    command=[sys.executable,str(ROOT/'scripts/run_lane.py'),'--manifest',str(manifest),
             '--receipt',str(receipt),'--indices','0','--output-dir',str(tmp_path/'jobs')]
    pid=None
    with open(tmp_path/'log','w') as log:
        parent=subprocess.Popen(command,env=env,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+20
            while not (folder/'state.npz').exists() and parent.poll() is None and time.monotonic()<deadline:
                time.sleep(.02)
            assert parent.poll() is None and lock.exists(),(tmp_path/'log').read_text()
            pid=int(lock.read_text().strip())
            assert pid!=parent.pid
            if kill_supervisor:
                parent.kill();parent.wait(timeout=5)
                with pytest.raises(AlreadyRunning):
                    with claim(lock):pass
                os.kill(pid,signal.SIGUSR1)
            else:
                parent.send_signal(signal.SIGUSR1)
                assert parent.wait(timeout=15)==75,(tmp_path/'log').read_text()
            deadline=time.monotonic()+15
            while True:
                try:
                    with claim(lock):break
                except AlreadyRunning:
                    assert time.monotonic()<deadline
                    time.sleep(.05)
            assert (folder/'state.npz').exists()
            assert not (folder/'result.json').exists()
        finally:
            if parent.poll() is None:
                parent.kill();parent.wait()
            if pid is not None:
                try:os.kill(pid,signal.SIGTERM)
                except ProcessLookupError:pass
