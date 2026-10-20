from pathlib import Path
from decimal import Decimal,localcontext
import json
ROOT=Path(__file__).resolve().parent
names=['gfull_n6_N24_s48_r.31_q0_quad.json','gfull_n6_N28_s64_r.43_q0_quad.json','gfull_n6_N32_s64_r.43_q0_quad_kahan.json']
control_path=ROOT.parent/'verification/full_controls.json';refs=json.loads(control_path.read_text())['values']
rows=[]
with localcontext() as ctx:
 ctx.prec=65
 for name in names:
  d=json.loads((ROOT/'data'/name).read_text());assert d['complete_sectors']==60 and d['complete_groups']==5
  errs={}
  for der in ['base','v','d']:
   for suffix,key in [('finite','volume_finite'),('log','volume_log')]:
    errs[f'{der}_{suffix}']=str(abs(Decimal(d[key][der])-Decimal(refs[f'Q6_{der}_{suffix}'])))
  rows.append({'file':name,'nodes_per_direction':d['settings']['N'],'samples':d['settings']['samples'],'radius':d['settings']['radius'],'Xvv':d['volume_finite']['vv'],'control_absolute_errors':errs})
 diff=abs(Decimal(rows[-1]['Xvv'])-Decimal(rows[-2]['Xvv']))
 r={'definition':'Xvv = [epsilon^0 log(epsilon)^0] d_v^2 Q6 at v=1,delta=0','status':'empirical_complete_sector_numerical_estimate','latest_estimate':rows[-1]['Xvv'],'last_two_absolute_difference':str(diff),'rigorous_error_bound':None,'constant_period_projection_used':False,'rational_part_not_inferred_from_decimal':True,'runs':rows,'F3_still_missing':['P8','XE']}
 (ROOT.parent/'verification/Xvv_estimate.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
