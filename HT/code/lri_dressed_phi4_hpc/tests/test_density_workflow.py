import copy
import json
from pathlib import Path
import pytest
import numpy as np
from lri_dressed.io import atomic_json,read_envelope,envelope,validate_result,digest,claim
from lri_dressed.local_basis import load_basis,validate_basis,for_configuration,descriptor,density_plan
from lri_dressed.cli import main


def training_args(path):
    return ['train-basis','--bath-cut','4','--delta','.24','--teacher-nz','8','--keep','6','--osc','64',
            '--threads','1','--output',str(path),'--memory-limit-gib','3']


@pytest.fixture(scope='module')
def basis(tmp_path_factory):
    path=tmp_path_factory.mktemp('basis')/'basis.json'
    assert main(training_args(path))==0
    return path,load_basis(path)


def sign_again(record):
    obj=copy.deepcopy(record);obj.pop('sha256',None);obj['sha256']=digest(obj);return obj


def run_args(out,basis):
    return ['run','--bath-cut','6','--deltas','.24','--nz','4','--osc','64','--threads','1',
            '--window','vacuum','--local-basis',str(basis[0]),'--local-basis-sha256',basis[1]['sha256'],
            '--output-dir',str(out),'--memory-limit-gib','2']


def test_artifact_nested_space_and_reuse(basis):
    path,rec=basis;data=path.read_bytes()
    assert main(training_args(path)+['--resume'])==0;assert path.read_bytes()==data
    small,_=for_configuration(rec,delta=.24,nz=4,osc=64,window='vacuum',window_mode='consistent')
    large,_=for_configuration(rec,delta=.24,nz=6,osc=64,window='vacuum',window_mode='consistent')
    assert np.max(abs(small.T@small-np.eye(8)))<2e-12
    assert np.max(abs(large@large.T@small-small))<2e-12


@pytest.mark.parametrize('damage',['checksum','parity','dimension','source','nan','target','weights','gates'])
def test_artifact_rejects_damage(basis,damage):
    _,original=basis;r=copy.deepcopy(original)
    if damage=='checksum':r['payload']['scale']*=1.01
    if damage=='parity':
        u=np.array(r['payload']['isometry']);u[:,[0,6]]=u[:,[6,0]];r['payload']['isometry']=u.tolist()
    if damage=='dimension':r['payload']['isometry'].pop()
    if damage=='source':r['config']['source_sha256']='bad'
    if damage=='nan':r['payload']['scale']=float('nan')
    if damage=='target':r['payload']['density']['thermal_target']=True
    if damage=='weights':r['payload']['density']['targets'][0]['weight']=.2
    if damage=='gates':r['payload']['gates']['teacher_primary_residual']=1.
    with pytest.raises((ValueError,TypeError)):
        if damage not in ('checksum','nan'):r=sign_again(r)
        validate_basis(r,current=True)


@pytest.mark.parametrize('overrides',[{'delta':.2},{'nz':7},{'osc':80},{'window':'none'},
                                     {'window_mode':'literal'},{'zero_scale':1.1}])
def test_basis_configuration_mismatch(basis,overrides):
    cfg=dict(delta=.24,nz=4,osc=64,window='vacuum',window_mode='consistent',zero_scale=1.)
    cfg.update(overrides)
    with pytest.raises(ValueError):for_configuration(basis[1],**cfg)


def test_cli_checkpoint_export_and_self_contained_diagnostics(tmp_path,basis):
    out=tmp_path/'runs';argv=run_args(out,basis)
    assert main(argv)==0
    path=next(out.glob('*.json'));raw=path.read_bytes();rec=read_envelope(path,'result')
    validate_result(rec['payload'],rec['config'])
    assert rec['config']['local_basis']==descriptor(basis[1])
    assert rec['payload']['local_basis_record']==basis[1]
    assert main(argv+['--resume'])==0;assert path.read_bytes()==raw
    path.unlink();assert main(argv+['--resume'])==0
    assert read_envelope(path,'result')['payload']['execution']['checkpoint_recovered']
    assert main(['export','--input-dir',str(out),'--output',str(tmp_path/'export.json')])==0
    # Result is independently portable: the original basis file need not exist.
    bpath=basis[0];blob=bpath.read_bytes();bpath.unlink()
    try:
        assert main(['identities','--result',str(path),'--output',str(tmp_path/'id.json'),'--k','6'])==0
    finally:bpath.write_bytes(blob)
    diag=json.loads((tmp_path/'id.json').read_text())
    assert diag['local_basis']==descriptor(basis[1])
    assert 'directly projected a0' in diag['generator']
    # A checksummed envelope alone is not enough if the basis identity is stripped.
    bad=copy.deepcopy(rec);bad['config'].pop('local_basis')
    with pytest.raises(ValueError):validate_result(bad['payload'],bad['config'])
    bad=copy.deepcopy(rec);bad['payload'].pop('local_basis_record')
    with pytest.raises(ValueError):validate_result(bad['payload'],bad['config'])


def test_manifest_sha_prevents_changed_basis(tmp_path,basis):
    path=tmp_path/'changed.json';r=copy.deepcopy(basis[1]);r['payload']['scale']*=1.001;r=sign_again(r);atomic_json(path,r)
    args=run_args(tmp_path/'out',(path,basis[1]))
    with pytest.raises(ValueError,match='changed'):main(args)
    assert not list((tmp_path/'out').glob('*.json'))


def test_stop_and_resume_training(tmp_path,monkeypatch):
    import lri_dressed.cli as cli
    path=tmp_path/'train.json';args=training_args(path)
    monkeypatch.setattr(cli,'STOP',True)
    assert main(args)==75;assert not path.exists()
    cp=path.with_name(path.name+'.checkpoint.json')
    assert read_envelope(cp,'basis-training-checkpoint')['payload']['phase']=='select'
    monkeypatch.setattr(cli,'STOP',False)
    assert main(args+['--resume'])==0
    assert load_basis(path)['payload']['checkpoint_recovered']


def test_stop_and_resume_inner_basis(tmp_path,monkeypatch):
    import lri_dressed.cli as cli
    from lri_dressed.density import DensitySolver
    orig=DensitySolver.solve
    def stop_first(self,*args,**kwargs):
        old=self.checkpoint
        def hook(theta,history):
            cli.STOP=True;old(theta,history)
        self.checkpoint=hook
        return orig(self,*args,**kwargs)
    monkeypatch.setattr(cli,'STOP',False)
    monkeypatch.setattr(DensitySolver,'solve',stop_first)
    path=tmp_path/'train.json';args=training_args(path)
    assert main(args)==75
    cp=read_envelope(path.with_name(path.name+'.checkpoint.json'),'basis-training-checkpoint')
    assert cp['payload']['phase']=='inner' and 'candidate' in cp['payload']
    monkeypatch.setattr(DensitySolver,'solve',orig);monkeypatch.setattr(cli,'STOP',False)
    assert main(args+['--resume'])==0
    assert load_basis(path)['payload']['checkpoint_recovered']


def test_stop_run_and_recover_without_basis_change(tmp_path,basis,monkeypatch):
    import lri_dressed.cli as cli
    args=run_args(tmp_path/'run',basis);monkeypatch.setattr(cli,'STOP',True)
    assert main(args)==75
    assert not list((tmp_path/'run').glob('*.json'))
    cp=read_envelope(next((tmp_path/'run/checkpoints').glob('*.json')),'checkpoint')
    assert cp['config']['local_basis']['sha256']==basis[1]['sha256']
    monkeypatch.setattr(cli,'STOP',False)
    assert main(args+['--resume'])==0


def test_pack_basis_binding(tmp_path,basis):
    from lri_dressed.pack import item_id,item_digest,check_item,command,check_record,completion,completion_valid
    from lri_dressed.planning import plan
    from lri_dressed.io import source_fingerprint
    pl=density_plan(plan(6,4,64,window='vacuum'),basis[1])
    item=dict(bath_cut=6,nz=4,osc=64,backend='tensor',window='vacuum',window_mode='consistent',window_tol=1e-12,
              window_maxiter=50,deltas=[.24],seed_dir=None,eig_tol=3e-11,residual_tol=2e-7,tuning_tol=5e-10,
              maxiter=30,max_eig_iter=10000,ncv=28,threads=1,mem_gib=2.,est_seconds=120.,resource_origin='test',
              plan_envelope_gib=pl['memory_envelope_gib'],local_basis_path=str(basis[0]),local_basis_sha256=basis[1]['sha256'])
    item['id']=item_id(item);check_item(item)
    args=command(item,tmp_path/'run')[3:];assert main(args)==0
    path=next((tmp_path/'run').glob('*.json'));check_record(item,path,source_fingerprint())
    done=completion(item,[path],source_fingerprint());assert completion_valid(item,done,source_fingerprint())
    bad=dict(item,local_basis_sha256='0'*64);bad['id']=item_id(bad)
    assert item_digest(bad)!=item_digest(item)
    assert not completion_valid(bad,done,source_fingerprint())
    with pytest.raises(ValueError):check_item(bad)
    old={k:v for k,v in item.items() if k not in ('local_basis_path','local_basis_sha256')};old['id']=item_id(old)
    with pytest.raises(ValueError):check_record(old,path,source_fingerprint())


def test_training_claim_held_by_solver(tmp_path):
    path=tmp_path/'basis.json'
    with claim(path.with_name(path.name+'.lock')):
        assert main(training_args(path))==73
    assert not path.exists()


def test_complete_training_checkpoint_finalizes_without_eigensolve(tmp_path,monkeypatch):
    import lri_dressed.basis_training as training
    path=tmp_path/'basis.json';args=training_args(path)
    assert main(args)==0
    blob=path.read_bytes();path.unlink()
    def forbidden(*a,**kw):raise AssertionError('Complete checkpoint must not retrain')
    monkeypatch.setattr(training,'train',forbidden)
    assert main(args+['--resume'])==0
    assert path.read_bytes()==blob
