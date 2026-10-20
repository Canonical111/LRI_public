"""Independent full-Jacobian reconstruction after fresh finite-response checks.
No guessed C8 value is used. All four formerly missing beta combinations are
assembled from the independently evaluated raw integrals and prior lower map.
"""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib,sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'prior_inputs'))
from verify_trace_fraction import calculate

def finite(tag):
 folder=ROOT/'finite_lower'/tag;manifest=json.loads((folder/'manifest.json').read_text());assert manifest['source_complete']
 total=F(0);seen=set()
 for b in manifest['blocks']:
  assert b['id'] not in seen;seen.add(b['id']);p=folder/b['id'];digest=hashlib.sha256((p/'stage1.jsonl').read_bytes()).hexdigest();assert digest==b['source_sha256']
  a=json.loads((p/'result.json').read_text());assert a['source_sha256']==digest and a['status']=='complete_block';total+=F(a['finite'])
 return total

def main():
 r6=F(json.loads((ROOT/'prior_inputs/Task_A_result.json').read_text())['R6']);r8=F(json.loads((ROOT/'prior_inputs/Task_B_result.json').read_text())['R8'])
 tail=F(json.loads((ROOT/'Task_C_result.json').read_text())['R_tail']);d=json.loads((ROOT/'Task_D_result.json').read_text());r9=F(d['R9'])
 tags=['EA5_d','EZ4_d','EZ6_base','EQ4_vd','Q4_vvd','Q6_vv','EQ6_v'];raw={t:finite(t) for t in tags}
 new={'U':tail+2*raw['EA5_d']-2*raw['EZ4_d']+F(205131,2),
      'J9':r9-2*raw['EZ6_base']-F(2868919,6),
      'Nd':-8*raw['EQ4_vd']+16*raw['Q4_vvd']-4*r6+99598,
      'Kv':-8*raw['EQ6_v']+16*raw['Q6_vv']-4*r8-F(952496,3)}
 old=json.loads((ROOT/'prior_inputs/T4_rational_reduction.json').read_text())['old_rational_beta_inputs']
 low=json.loads((ROOT/'extra_beta_input_checks.json').read_text());assert low['status']=='all_six_prior_new_beta_inputs_freshly_verified'
 coeff=dict(old);coeff.update(low['fresh_values']);coeff.update({k:str(v) for k,v in new.items()})
 wcheck=json.loads((ROOT/'three_tail_cubic_check.json').read_text());assert F(wcheck['W'])==F(coeff['W'])
 coeff['W']=wcheck['W']
 val=calculate(coeff);assert F(val['C8_rational'])==F(d['C8_weight_zero']),(val,d['C8_weight_zero'])
 report={'status':'independent_full_Jacobian_and_raw_subtraction_assembly_agree','finite_integrals':{k:str(v) for k,v in raw.items()},
  'four_new_beta_combinations':{k:str(v) for k,v in new.items()},'coefficients':coeff,'full_Jacobian':val,
  'reduced_raw_integral_result':d['C8_weight_zero'],'C8_conjecture_used_as_input':False,
  'new_cubic_tail_check':wcheck['W'],
  'six_additional_inputs_rechecked_from_new_integrals':low['fresh_values'],
  'inherited_not_reintegrated_here':['prior 25 beta coefficients','Tasks A and B','prior finite-response subtraction map']}
 (ROOT/'full_beta_C8_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
