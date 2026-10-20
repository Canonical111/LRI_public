from pathlib import Path
import json,os,subprocess,sys
import numpy as np
import pytest
from lri_coeff.engine import Engine
from lri_coeff.storage import cached_graph,save_checkpoint,load_checkpoint,read_envelope,output_lock
ROOT=Path(__file__).resolve().parents[1]

def test_cache_and_corruption(tmp_path):
    a,hit=cached_graph(tmp_path,4,8,None,100000,2**30);assert not hit
    b,hit=cached_graph(tmp_path,4,8,None,100000,2**30);assert hit
    for k in a.__dict__:
        if isinstance(getattr(a,k),np.ndarray):assert np.array_equal(getattr(a,k),getattr(b,k))
    f=next(tmp_path.glob('*/amp.npy'))
    with f.open('r+b') as out:out.seek(-4,2);out.write(b'FAIL')
    with pytest.raises(ValueError):cached_graph(tmp_path,4,8,None,100000,2**30)

@pytest.mark.parametrize('stage,index',[('wave',2),('wave',4),('moments',4),('quotient',6)])
def test_resume(tmp_path,stage,index):
    ref=Engine(4,8,'consistent').solve(False);e=Engine(4,8,'consistent')
    def stop(eng,kind,k):
        if kind==stage and k==index:
            save_checkpoint(eng,tmp_path,'same');raise InterruptedError
    e.progress=stop
    with pytest.raises(InterruptedError):e.solve(False)
    other=Engine(4,8,'consistent');assert load_checkpoint(other,tmp_path,'same')
    out=other.solve(False)
    for k in ['C','r','g','energies','vacuum_coefficients']:assert np.array_equal(ref[k],out[k]),k
    assert not load_checkpoint(Engine(4,8,'raw'),tmp_path,'different')

def test_lock(tmp_path):
    out=tmp_path/'point.json'
    with output_lock(out,'abc'):
        with pytest.raises(FileExistsError):
            with output_lock(out,'abc'):pass
    assert not Path(str(out)+'.lock').exists()

def test_cli(tmp_path):
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),NUMBA_NUM_THREADS='4',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1')
    cmd=[sys.executable,'-m','lri_coeff','run','--cutoff','4','--degree','8','--output',str(tmp_path/'result.json'),'--cache',str(tmp_path/'cache'),'--checkpoint',str(tmp_path/'checkpoints')]
    a=subprocess.run(cmd+['--stop-after-wave','2'],env=env,capture_output=True,text=True);assert a.returncode==75,a.stderr
    b=subprocess.run(cmd+['--resume','--threads','2'],env=env,capture_output=True,text=True);assert b.returncode==0,b.stderr
    out=read_envelope(tmp_path/'result.json');assert out['execution']['resumed']
    c=subprocess.run(cmd,env=env,capture_output=True,text=True);assert c.returncode==0,c.stderr;assert 'skipped' in c.stdout
    bad=subprocess.run(cmd+['--scheme','raw'],env=env,capture_output=True,text=True);assert bad.returncode==1
