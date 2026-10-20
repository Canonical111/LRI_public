"""Full-period exact assembly of the now-known F3 terms.
P8 is deliberately not assigned a value.
"""
from pathlib import Path
from fractions import Fraction as Q
from decimal import Decimal,localcontext
import json,sys,hashlib
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT.parent/'F2_F3_delivery/F2/code'))
from period_polynomial import parse,add
from assemble_new_finite import write_poly

def main():
 dst=ROOT/'data';inp=[('Xvv',16,dst/'Xvv.expr'),('XE',-8,dst/'XE.expr'),('F3_lower_shift',1,ROOT/'inherited/F3_lower_shift.expr')]
 out={};records=[]
 for name,coef,p in inp:
  val=parse(p.read_text());add(out,{m:v*coef for m,v in val.items()});records.append({'name':name,'multiplier':coef,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'terms':len(val),'rational_projection':str(val.get((),0))})
 assert out.get(())==Q(-9017996,3)
 target=dst/'F3_known_with_six_kinks.expr';target.write_text(write_poly(out))
 a=json.loads((dst/'XE_first60.json').read_text());b=json.loads((dst/'XE_second90.json').read_text())
 with localcontext() as ctx:
  ctx.prec=100
  runs={}
  for name,r in [('first60',a),('second90',b)]:
   v={k:Decimal(x) for k,x in r['values'].items()};runs[name]={'Xvv':str(v['Xvv']),'XE':str(v['XE']),'F3_lower_shift':str(v['F3_lower_shift']),'known_F3_sum':str(16*v['Xvv']-8*v['XE']+v['F3_lower_shift'])}
  dif={k:str(abs(Decimal(runs['first60'][k])-Decimal(runs['second90'][k]))) for k in runs['second90']}
 r={'status':'full_six_kink_finite_parts_completed_P8_not_evaluated','Xvv_exact_terms':len(parse((dst/'Xvv.expr').read_text())),'XE_exact_terms':len(parse((dst/'XE.expr').read_text())),'assembly':'Kv = -4 P8 + F3_known_with_six_kinks','input_expressions':records,'known_expression_terms':len(out),'known_expression_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'known_rational_projection':str(out.get(())),'rational_P8_inherited':'-757993','rational_Kv_check':str(Q(4*757993)+out[()]),'fresh_numerical_runs':runs,'absolute_run_differences':dif,'numerical_interval_certified':False,'P8_full_value':None,'F3_complete':False,'C8_complete':False,'F1_uncertainty_resolved':False}
 (dst/'new_six_kink_result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2),flush=True)
if __name__=='__main__':main()
