"""Independent rational-polynomial check of delivered F2 scalar identities."""
import ast,json,hashlib
from pathlib import Path
from fractions import Fraction as Q
from functools import lru_cache
def terms(text):
 depth=0;start=0
 for i,c in enumerate(text):
  if c in '([':depth+=1
  elif c in ')]':depth-=1
  elif c in '+-' and depth==0 and i and text[i-1].isspace():
   if text[start:i].strip():yield text[start:i].strip()
   start=i
 if text[start:].strip():yield text[start:].strip()

ROOT=Path(__file__).resolve().parents[1]
def add(a,b,f=Q(1)):
 for k,v in b.items():
  val=a.get(k,Q(0))+f*v
  if val:a[k]=val
  else:a.pop(k,None)
 return a
def mul(a,b):
 o={}
 for m,c in a.items():
  for n,d in b.items():
   ex=dict(m)
   for k,p in n:ex[k]=ex.get(k,0)+p
   add(o,{tuple(sorted((k,p) for k,p in ex.items() if p)):c*d})
 return o
@lru_cache(None)
def atom(nm):return (((nm,1),),Q(1))
def ev(n):
 if isinstance(n,ast.Constant) and isinstance(n.value,int):return {():Q(n.value)}
 if isinstance(n,ast.Name):return dict([atom(n.id)])
 if isinstance(n,ast.Call):
  if isinstance(n.func,ast.Name) and n.func.id=='Rational':
   aa=[next(iter(ev(x).values())) for x in n.args];return {():aa[0]/aa[1]}
  return dict([atom(ast.unparse(n))])
 if isinstance(n,ast.UnaryOp):
  return {k:(-v if isinstance(n.op,ast.USub) else v) for k,v in ev(n.operand).items()}
 if isinstance(n,ast.BinOp):
  a,b=ev(n.left),ev(n.right)
  if isinstance(n.op,ast.Add):return add(a,b)
  if isinstance(n.op,ast.Sub):return add(a,b,-1)
  if isinstance(n.op,ast.Mult):return mul(a,b)
  if isinstance(n.op,ast.Div) and set(b)<={()}:return {k:v/b.get((),Q(0)) for k,v in a.items()}
  if isinstance(n.op,ast.Pow) and set(b)<={()}:
   m=b.get((),Q(0));assert m.denominator==1 and m>=0
   out={():Q(1)}
   for _ in range(int(m)):out=mul(out,a)
   return out
 raise ValueError(ast.dump(n))
def parse(text):
 out={}
 for t in terms(text):add(out,ev(ast.parse(t,mode='eval').body))
 return out

def main():
 names=['U','A7_tail_log','EA5_tail_finite','F2_known_with_endpoint','F2_lower_shift','Z6_tail_log','EZ4_tail_finite']
 pp={};info={}
 for name in names:
  p=ROOT/'data'/f'{name}.expr';pp[name]=parse(p.read_text());info[name]={'terms':len(pp[name]),'rational_part':str(pp[name].get((),0)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}; print('PARSED',name,info[name]['terms'],flush=True)
 check1={};add(check1,pp['U']);add(check1,pp['A7_tail_log'],-1);add(check1,pp['F2_known_with_endpoint'],-1)
 check2={};add(check2,pp['F2_known_with_endpoint']);
 for name,c in [('EA5_tail_finite',-2),('F2_lower_shift',-1),('Z6_tail_log',1),('EZ4_tail_finite',2)]:add(check2,pp[name],c)
 assert not check1 and not check2
 assert pp['U'].get(())==Q(16534,3) and pp['A7_tail_log'].get(())==Q(-468683,3)
 record={'check_U_equals_A7_plus_known':True,'check_known_from_four_components':True,'independent_standard_library_rational_arithmetic':True,'input_info':info,'higher_logarithms_tested':False,'reason':'Only scalar finite-log outputs and historical source-coverage metadata are present, not the complete boundary logarithmic polynomials.'}
 (ROOT/'verification/exact_assembly.json').write_text(json.dumps(record,indent=2));print('EXACT F2 ASSEMBLY PASS',flush=True)
if __name__=='__main__':main()
