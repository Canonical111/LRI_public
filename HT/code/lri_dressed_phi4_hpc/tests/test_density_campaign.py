"""Manifest and cluster entry-point checks; scheduler execution is not simulated as real validation."""
import copy,json,os,subprocess,sys
from pathlib import Path
import pytest
from lri_dressed.cli import main
from lri_dressed.io import atomic_json,digest,envelope,runtime,source_fingerprint,release_fingerprint
from lri_dressed.local_basis import load_basis,read_basis_index
ROOT=Path(__file__).resolve().parents[1]


def invoke(script,args):
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),NUMBA_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
    return subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],env=env,cwd=ROOT,capture_output=True,text=True)


@pytest.fixture
def indexed(tmp_path):
    b=tmp_path/'basis.json'
    args=['train-basis','--bath-cut','4','--delta','.24','--teacher-nz','8','--keep','6','--osc','64',
          '--output',str(b),'--memory-limit-gib','3']
    assert main(args)==0
    index=tmp_path/'index.json';p=invoke('index_bases.py',['--files',b,'--output',index])
    assert p.returncode==0,p.stderr
    return b,index


def test_index_and_pack_manifest(tmp_path,indexed):
    b,index=indexed;entry=read_basis_index(index)[.24]
    assert entry[1]['sha256']==load_basis(b)['sha256']
    manifest=tmp_path/'manifest.json'
    p=invoke('make_campaign.py',['--pack','--campaign','basis_test','--bath-cuts','6','--deltas','.24',
          '--nz','4','--osc','64','--windows','vacuum:consistent','--split','points','--basis-index',index,
          '--mem-gib','2','--est-seconds','60','--out',manifest])
    assert p.returncode==0,p.stderr
    row=json.loads(manifest.read_text());item=row['items'][0]
    assert item['local_basis_sha256']==entry[1]['sha256']
    assert item['local_basis_path']==str(b.resolve())
    from lri_dressed.pack import check_item,command
    check_item(item)
    cmd=command(item,tmp_path/'results')
    assert '--local-basis-sha256' in cmd
    # A different expected SHA changes item identity and is rejected before running.
    bad=copy.deepcopy(row);bad['items'][0]['local_basis_sha256']='0'*64
    with pytest.raises(ValueError):check_item(bad['items'][0])
    blob=json.loads(index.read_text());blob['entries'][0]['sha256']='0'*64
    blob.pop('sha256');blob['sha256']=digest(blob);atomic_json(index,blob)
    with pytest.raises(ValueError):read_basis_index(index)


def test_training_manifest_and_receipt_rejection(tmp_path):
    request=tmp_path/'training.json'
    p=invoke('make_basis_training.py',['--deltas','.24','--bath-cut','4','--teacher-nz','8','--keep','6',
          '--osc','64','--basis-dir',tmp_path/'basis','--out',request,'--memory-limit-gib','3'])
    assert p.returncode==0,p.stderr
    rec=json.loads(request.read_text());cfg=rec['jobs'][0]['config']
    assert cfg['initial_theta'] is not None
    receipt=tmp_path/'receipt.json'
    # Deliberately failed mock receipt; never a real cluster or numerical receipt.
    atomic_json(receipt,envelope('validation',{},dict(passed=False,source_sha256=source_fingerprint(),
                release_sha256=release_fingerprint(),runtime=runtime())))
    p=invoke('run_basis_training.py',['--manifest',request,'--index','0','--receipt',receipt])
    assert p.returncode!=0 and 'receipt' in p.stderr
    assert not list((tmp_path/'basis').glob('*.json'))


def test_legacy_lane_rejects_density_keys(tmp_path):
    p=invoke('make_campaign.py',['--bath-cuts','4','--deltas','.24','--basis-index','x','--out',tmp_path/'bad.json'])
    assert p.returncode!=0 and 'without --pack' in p.stderr
    assert not (tmp_path/'bad.json').exists()


def test_nonproduction_basis_profiles_rejected(tmp_path,indexed):
    b,index=indexed
    p=invoke('make_campaign.py',['--pack','--campaign','bad','--bath-cuts','4','--deltas','.24',
          '--windows','none','--basis-index',index,'--out',tmp_path/'bad.json'])
    assert p.returncode!=0 and 'vacuum:consistent' in p.stderr
