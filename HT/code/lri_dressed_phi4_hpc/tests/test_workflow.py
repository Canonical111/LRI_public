import json,subprocess,sys,os,time
from pathlib import Path
import pytest
from lri_dressed.io import envelope,atomic_json,read_envelope,claim,digest,validate_result
from lri_dressed.planning import plan,guard


def test_record_integrity(tmp_path):
    p=tmp_path/'data.json';cfg={'a':1};atomic_json(p,envelope('checkpoint',cfg,{'theta':[1.,2.]}))
    assert read_envelope(p,'checkpoint',cfg)['payload']['theta']==[1.,2.]
    with pytest.raises(ValueError):read_envelope(p,'checkpoint',{'a':2})
    r=json.loads(p.read_text());r['payload']['theta'][0]=3;p.write_text(json.dumps(r))
    with pytest.raises(ValueError):read_envelope(p)
    with pytest.raises(ValueError):atomic_json(tmp_path/'bad.json',{'x':float('nan')})


def test_lock_contention(tmp_path):
    path=tmp_path/'item.lock'
    with claim(path):
        code="from lri_dressed.io import claim\nimport sys\nwith claim(sys.argv[1]): print('acquired')"
        p=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True,text=True)
        assert p.returncode!=0 and 'already claimed' in p.stderr
    with claim(path):pass


def test_planning_guard():
    p=plan(20,24,192)
    assert p['backend']=='ladder'
    with pytest.raises(MemoryError):guard(p,1e-6)


def test_cli_resume_and_export(tmp_path):
    from lri_dressed.cli import main
    root=Path(__file__).resolve().parents[1]
    argv=['run','--bath-cut','4','--nz','4','--osc','32','--deltas','.24',
       '--threads','1','--output-dir',str(tmp_path/'run'),'--memory-limit-gib','2']
    assert main(argv)==0
    result=list((tmp_path/'run').glob('*.json'))[0];record=read_envelope(result,'result')
    validate_result(record['payload'],record['config'])
    before=result.read_bytes();assert main(argv+['--resume'])==0;assert result.read_bytes()==before
    assert main(['export','--input-dir',str(tmp_path/'run'),'--output',str(tmp_path/'export.json')])==0
    assert len(json.loads((tmp_path/'export.json').read_text()))==1
    # Complete solve recovery from the last accepted Newton point, without final result.
    result.unlink();assert main(argv+['--resume'])==0
    record=read_envelope(result,'result');assert record['payload']['execution']['checkpoint_recovered']
    bad=record['payload'].copy();bad['Delta_thermal']+=1
    with pytest.raises(ValueError):validate_result(bad,record['config'])


def test_multi_rank_rejected(monkeypatch):
    from lri_dressed.cli import setup_runtime
    monkeypatch.setenv('OMPI_COMM_WORLD_SIZE','2')
    with pytest.raises(RuntimeError):setup_runtime(1)


def test_safe_boundary_stop(tmp_path,monkeypatch):
    import lri_dressed.cli as cli
    args=['run','--bath-cut','4','--nz','4','--osc','32','--deltas','.24',
          '--threads','1','--output-dir',str(tmp_path/'run'),'--memory-limit-gib','2']
    monkeypatch.setattr(cli,'STOP',True)
    assert cli.main(args)==75
    assert not list((tmp_path/'run').glob('*.json'))
    assert len(list((tmp_path/'run/checkpoints').glob('*.json')))==1
    monkeypatch.setattr(cli,'STOP',False)
    assert cli.main(args+['--resume'])==0
    assert len(list((tmp_path/'run').glob('*.json')))==1


def test_baseline_pin_rejects_other_trees(tmp_path):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
    from baseline_equality import check_baseline,BASELINE_SOURCE_SHA256
    with pytest.raises(SystemExit):check_baseline(Path(__file__).resolve().parents[1])     # the current tree
    base=os.environ.get('LRI_BASELINE')
    if base and Path(base).is_dir():assert check_baseline(base)==BASELINE_SOURCE_SHA256
