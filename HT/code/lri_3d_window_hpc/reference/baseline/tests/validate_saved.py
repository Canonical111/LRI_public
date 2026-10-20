"""Audit full main records and independent comparisons, without requiring Ward closure."""
from pathlib import Path
import json,sys,importlib.util
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'code'))
from ht3d.hpc import validate_record,digest
seen=set();total=0;maxdiag=0.;teachers=0
for folder in ['curve','raw','local']:
 for p in sorted((R/f'results/{folder}').glob('*.json')):
  if p.name.endswith('.checkpoint.json'):continue
  d=json.loads(p.read_text());validate_record(d,d['request_digest']);total+=1
  assert d['request_digest']==digest(d['configuration'])
  assert d['request_digest'] not in seen;seen.add(d['request_digest'])
  assert d['spacetime_dimension']==3
  assert abs(d['epsilon']-(3-4*d['delta']))<1e-14
  assert abs(d['s']-(3-2*d['delta']))<1e-14
  assert abs(d['Delta_sigma_measured']-d['delta'])<2e-9
  assert abs(d['Delta_shadow_measured']-(3-d['delta']))<2e-9
  assert abs(d['even_gaps'][1]-d['Delta_thermal'])<1e-13
  for a in d.get('diagnostics',{}).get('checks',{}).values():
   assert a['residual']<1e-8 and a['orthogonality']<1e-9
   maxdiag=max(maxdiag,a['residual'])
  for a in d.get('diagnostics',{}).get('records',[]):
   assert a['same_primary_selected']==(a['branch']=='P2_trace' and a['rank']=={'sigma':0,'thermal':1,'chi':1}[a['family']])
   if a['same_primary_selected']:assert a['ambiguous']
  if 'basis_artifact' in d:
   teachers+=1;a=d['basis_artifact'];u=np.array(a['isometry']);assert a['dimension']==3
   assert np.max(abs(u.T@u-np.eye(u.shape[1])))<2e-10
   assert not a['metadata']['thermal_target']
assert total==86 and teachers==15
for name in ['physics_checks.json','numerical_checks.json']:
 assert json.loads((R/'validation'/name).read_text())['passed']
summary=json.loads((R/'results/SUMMARY.json').read_text())
assert summary['raw_replay_max_thermal']<1e-10 and summary['local_independent_max_thermal']<1e-8
assert summary['window_curve_records']==52 and summary['local_checks']==19
out=dict(accepted_main_records=total,teachers=teachers,max_angular_residual=maxdiag,passed=True,
 scope='Internal hashes and actual scalar/window/diagnostic gates; does not assert physical conformal closure.')
(R/'validation/saved_data_audit.json').write_text(json.dumps(out,indent=2));print(out)
