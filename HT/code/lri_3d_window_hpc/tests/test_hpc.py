from pathlib import Path
import copy,json,sys
import pytest
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'code'))
from ht3d.hpc import digest,atomic_json,claim,Claimed,validate_record,parser,run

def sample():return json.loads((R/'reference/baseline/results/curve/window_L8_x0.6.json').read_text())
def resign(d):
 d.pop('record_sha256',None);d['record_sha256']=digest(d);return d

def test_record_binding():
 d=sample();validate_record(d,d['request_digest'])
 with pytest.raises(ValueError):validate_record(d,'different')
 d['Delta_thermal']+=.01
 with pytest.raises(ValueError):validate_record(d,d['request_digest'])

def test_dimension_and_numeric_gates():
 d=sample();d['spacetime_dimension']=2;resign(d)
 with pytest.raises(ValueError):validate_record(d,d['request_digest'])
 d=sample();d['tuning_residual']=1.;resign(d)
 with pytest.raises(ValueError):validate_record(d,d['request_digest'])
 d=sample();d['window_correction']['top_fixed_point_residual']=1e-7;resign(d)
 with pytest.raises(ValueError):validate_record(d,d['request_digest'])

def test_atomic_claim(tmp_path):
 p=tmp_path/'out.json'
 with claim(p,'abc'):
  with pytest.raises(Claimed):
   with claim(p,'abc'):pass
  atomic_json(p,{'yes':True})
 assert json.loads(p.read_text())=={'yes':True}
 assert not Path(str(p)+'.claim').exists()

def test_reject_two_dimensional_basis(tmp_path):
 d=sample()['basis_input']['artifact'];d['dimension']=2
 p=tmp_path/'basis.json';p.write_text(json.dumps({'basis_artifact':d,'theta':[.1,-2.]}))
 args=parser().parse_args(['--L','4','--x','.6','--nz','8','--basis',str(p),'--output',str(tmp_path/'out.json'),'--diagnostics','none'])
 with pytest.raises(ValueError,match='dimension/prescription'):run(args)

def test_cli_real_resume(tmp_path):
 args=parser().parse_args(['--L','4','--x','.6','--nz','12','--osc','96','--output',str(tmp_path/'out.json'),'--diagnostics','first'])
 assert run(args)==0
 original=(tmp_path/'out.json').read_bytes()
 args.resume=True;assert run(args)==0
 assert (tmp_path/'out.json').read_bytes()==original
 args.nz=14
 with pytest.raises(ValueError):run(args)
