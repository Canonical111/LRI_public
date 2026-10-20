"""Independent full-Jacobian replay using decimal inputs as exact fractions.
This checks algebra; it does not make the input integration errors vanish.
"""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext
import ast,json,hashlib,sys
from full_jacobian import calculate
ROOT=Path(__file__).resolve().parent.parent

def expr(text,values):
 def rec(n):
  if isinstance(n,ast.Expression):return rec(n.body)
  if isinstance(n,ast.Name):return values[n.id]
  if isinstance(n,ast.Constant) and isinstance(n.value,int):return F(n.value)
  if isinstance(n,ast.UnaryOp):return -rec(n.operand) if isinstance(n.op,ast.USub) else rec(n.operand)
  if isinstance(n,ast.BinOp):
   a,b=rec(n.left),rec(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
   if isinstance(n.op,ast.Pow):
    assert b.denominator==1;return a**int(b)
  raise ValueError(ast.dump(n))
 return rec(ast.parse(text,mode='eval'))
def dec(x,places=65):
 with localcontext() as c:c.prec=places;return str(Decimal(x.numerator)/Decimal(x.denominator))
def read(folder,name):return json.loads((ROOT/folder/name).read_text())

def main():
 p8=read('data','F3_final_100.json')['values'];f4=read('data','F4_data_100.json')['values'];six=read('inherited','six_new_inputs.json')['coefficients'];u=read('inherited','U_record.json')['values']['U'];trace=read('inherited','full_trace.json')
 coefficients={k[5:]:F(v) for k,v in p8.items() if k.startswith('beta_')};coefficients.update({k:F(v) for k,v in six.items()})
 coefficients.update(U=F(u),J9=F(f4['J9']),Kv=F(p8['Kv']))
 old=expr(trace['old_part'],coefficients)
 assert abs(old-F(f4['B_old_full']))<F(1,10**75)
 Bdone=old+4*coefficients['W']+2*coefficients['S']+F(3,32)*coefficients['L3']-coefficients['M21']/4+coefficients['M12']/2-coefficients['N2']/16
 Cfixed=Bdone+F(p8['F1_known'])/8+3*coefficients['U']/4+coefficients['Kv']/32+coefficients['J9']/4
 reports=[]
 files=['P6_N32_original.json','P6_N36_original.json','P6_N32_kahan.json']
 if (ROOT/'data/P6_N36_kahan_fresh.json').exists():files.append('../data/P6_N36_kahan_fresh.json')
 for name in files:
  path=ROOT/'inherited'/name
  obj=json.loads(path.read_text());P6=F(obj['volume_log']['vd']);coefficients['Nd']=-4*P6+F(p8['F1_known'])
  result=calculate(coefficients);literal=expr(trace['C8'],coefficients);short=Cfixed-P6/2
  assert result['C8']==literal==short
  reports.append({'P6_source':name,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'P6':dec(P6),'N_delta':dec(coefficients['Nd']),'C8':dec(short),'T4':dec(short/8),'full_Jacobian_minus_literal_expression_exact_zero':True,'literal_minus_short_assembly_exact_zero':True,'trace_coefficients':[dec(t) for t in result['trace']]})
 # Projection and input rational consistency (not used to replace any full term).
 rational=read('inherited','C8_rational_record.json');assert rational['C8_weight_zero']=='88'
 pair={}
 for folder in ('F3_final','F4_data'):
  first=read('data',folder+'_70.json')['values'];second=read('data',folder+'_100.json')['values']
  pair[folder]={k:dec(abs(F(first[k])-F(second[k]))) for k in first}
  assert all(abs(F(first[k])-F(second[k]))<F(1,10**49) for k in first)
 spread=abs(F(read('inherited','P6_N32_original.json')['volume_log']['vd'])-F(read('inherited','P6_N36_original.json')['volume_log']['vd']))/2
 report={'status':'all_full_C8_inputs_numerically_available_P6_limits_precision','new_P8':p8['P8'],'new_Kv':p8['Kv'],'new_J9':f4['J9'],'B_old_full':dec(old),'B_done':dec(Bdone),'C8_relation':'C8 = Cfixed - P6/2','Cfixed':dec(Cfixed),'inherited_Nd_relation':'Nd = F1_known - 4 P6','cases':reports,'C8_empirical_spread_from_original_two_P6_runs':dec(spread),'rigorous_error_bound':None,'positive_weight_C8_numerically_included':True,'compact_zeta_reduction_proved':False,'new_period_evaluations_pair_differences':pair,'scope':'exact coefficient assembly with approximate P6; matched archived RG assumptions retained'}
 (ROOT/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
