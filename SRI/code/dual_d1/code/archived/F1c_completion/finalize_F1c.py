#!/usr/bin/env python3
"""Propagate F1a input limitations without treating differences as rigorous error bounds."""
from pathlib import Path
from decimal import Decimal,localcontext
import json
ROOT=Path(__file__).resolve().parent
def main():
 assembly=json.loads((ROOT/'data/assembly.json').read_text())
 r70=json.loads((ROOT/'verification/full70.json').read_text())
 r100=json.loads((ROOT/'verification/full100.json').read_text())
 with localcontext() as ctx:
  ctx.prec=100;D=Decimal
  diffs={n:str(D(z)-D(r70['values'][n])) for n,z in r100['values'].items()}
  assert max(map(lambda x:abs(D(x)),diffs.values()))<D('1e-40')
  known=D(r100['values']['Nd_known_part'])
  dct=D(r100['values']['Dct']);total=D(r100['values']['total_shift'])
  estimates=[]
  for f in sorted((ROOT/'inputs/F1a').glob('*.json')):
   datum=json.loads(f.read_text());P=D(datum['volume_log']['vd'])
   N=known-4*P
   estimates.append({'source':f.name,'P6':str(P),'N_delta':str(N),
     'N_delta_over_8_contribution_to_C8':str(N/8)})
  observed=abs(D(estimates[0]['N_delta'])-D(estimates[1]['N_delta']))
  result={
   'status':'F1c_full_finite_response_shift_evaluated',
   'exact_definition':'Dct = dv ddelta [-2 Q2_f b5 -4 K4_f b3 -lambda2 h4+lambda4] at v=1,delta=0',
   'Dct_numerical':str(dct),'Dct_rational':'-190100',
   'exact_affine_relation':'N_delta = -4 P6 + Nd_known_part',
   'Nd_known_part_numerical':str(known),'Dnorm_plus_Dct_numerical':str(total),
   'N_delta_rational_check':'-20848',
   'independent_numerical_difference':diffs,'inherited_P6_estimates':estimates,
   'N_delta_observed_spread_not_error_bound':str(observed),
   'full_C8_not_evaluated':True,'F1a_not_reintegrated_or_improved':True,
   'new_raw_kernels_integrated':['Q4_vvd','EQ4_vd'],
   'rational_projection_not_used_as_integral_input':True,
   'interval_certified':False,
   'exact_period_expression':'data/Dct.expr'
  }
 (ROOT/'result.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
