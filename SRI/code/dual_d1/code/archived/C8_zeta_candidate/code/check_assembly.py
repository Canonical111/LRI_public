"""Independent exact arithmetic for the thermal assembly. Decimal inputs are data, not exact integral evaluations."""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext
import ast,json
from full_jacobian import calculate
ROOT=Path(__file__).resolve().parent.parent

def parse(text,values):
 def ev(n):
  if isinstance(n,ast.Expression):return ev(n.body)
  if isinstance(n,ast.Constant) and isinstance(n.value,int):return F(n.value)
  if isinstance(n,ast.Name):return values[n.id]
  if isinstance(n,ast.UnaryOp):return -ev(n.operand) if isinstance(n.op,ast.USub) else ev(n.operand)
  if isinstance(n,ast.BinOp):
   a,b=ev(n.left),ev(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
   if isinstance(n.op,ast.Pow):assert b.denominator==1;return a**int(b)
  raise ValueError(ast.dump(n))
 return ev(ast.parse(text,mode='eval'))
def dec(x,prec=100):
 with localcontext() as ctx:
  ctx.prec=prec;return str(Decimal(x.numerator)/Decimal(x.denominator))
def assemble():
 load=lambda f:json.loads((ROOT/'inherited'/f).read_text())
 p8=load('F3_final_100.json')['values'];f4=load('F4_data_100.json')['values'];six=load('six_new_inputs.json')['coefficients'];uv=load('U_record.json')['values']['U'];tr=load('full_trace.json')
 coeff={k[5:]:F(v) for k,v in p8.items() if k.startswith('beta_')};coeff.update({k:F(v) for k,v in six.items()});coeff.update(U=F(uv),Kv=F(p8['Kv']),J9=F(f4['J9']))
 old=parse(tr['old_part'],coeff);assert abs(old-F(f4['B_old_full']))<F(1,10**75)
 done=old+4*coeff['W']+2*coeff['S']+F(3,32)*coeff['L3']-coeff['M21']/4+coeff['M12']/2-coeff['N2']/16
 fixed=done+F(p8['F1_known'])/8+3*coeff['U']/4+coeff['Kv']/32+coeff['J9']/4
 reports=[]
 for digits in [70,100]:
  P6=F(json.loads((ROOT/'data'/f'P6_eval{digits}.json').read_text())['values']['P6']);coeff['Nd']=F(p8['F1_known'])-4*P6
  calc=calculate(coeff);literal=parse(tr['C8'],coeff);short=fixed-P6/2
  assert calc['C8']==literal==short
  reports.append({'input':f'P6_eval{digits}.json','P6':dec(P6),'C8':dec(short),'T4':dec(short/8),'N_delta':dec(coeff['Nd']),'all_three_algebraic_assemblies_exactly_equal':True})
 report={'known_fixed_term':dec(fixed),'B_done':dec(done),'runs':reports,'old_numeric_B_difference':dec(old-F(f4['B_old_full'])),'scope':'Exact algebra on supplied decimal input strings; no removal of numerical uncertainty.'}
 return report
if __name__=='__main__':
 r=assemble();(ROOT/'verification/new_full_Jacobian.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
