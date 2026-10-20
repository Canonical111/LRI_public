"""Parse exact SymPy expressions without quadratic left-associated Add construction.
Only a restricted arithmetic grammar is accepted; no Python code is executed.
"""
from pathlib import Path
import ast
import sympy as s
_FUNCS={n:getattr(s,n) for n in ['log','polylog','zeta','sqrt','exp','Rational','Integer','Float','Add','Mul','Pow']}
_CONST={'pi':s.pi,'EulerGamma':s.EulerGamma,'I':s.I}
def parse(text,locals=None):
 env=dict(_CONST);env.update(locals or {});text=text.replace('^','**')
 # Canonical exact expressions are expanded sums. Split their top-level
 # signed terms before CPython constructs a potentially 50,000-deep AST.
 pieces=[];depth=0;start=0;sign=1
 for i,ch in enumerate(text):
  if ch in '([':depth+=1
  elif ch in ')]':depth-=1
  elif depth==0 and ch in '+-' and i>0 and text[i-1:i]==' ' and text[i+1:i+2]==' ':
   pieces.append((sign,text[start:i].strip()));start=i+1;sign=1 if ch=='+' else -1
 pieces.append((sign,text[start:].strip()))
 def ev(n):
  if isinstance(n,ast.Constant):
   if isinstance(n.value,int):return s.Integer(n.value)
   if isinstance(n.value,str):return n.value
   if isinstance(n.value,float):return s.Float(str(n.value))
  if isinstance(n,ast.Name):
   if n.id not in env:env[n.id]=s.Symbol(n.id)
   return env[n.id]
  if isinstance(n,ast.UnaryOp):
   if isinstance(n.op,ast.USub):return -ev(n.operand)
   if isinstance(n.op,ast.UAdd):return ev(n.operand)
  if isinstance(n,ast.BinOp):
   if isinstance(n.op,(ast.Add,ast.Sub)):
    todo=[(n,1)];args=[]
    while todo:
     q,sgn=todo.pop()
     if isinstance(q,ast.BinOp) and isinstance(q.op,(ast.Add,ast.Sub)):
      todo.append((q.left,sgn));todo.append((q.right,sgn if isinstance(q.op,ast.Add) else -sgn))
     else:args.append(sgn*ev(q))
    return s.Add(*args)
   if isinstance(n.op,ast.Mult):
    todo=[n];args=[]
    while todo:
     q=todo.pop()
     if isinstance(q,ast.BinOp) and isinstance(q.op,ast.Mult):todo.extend((q.left,q.right))
     else:args.append(ev(q))
    return s.Mul(*args)
   if isinstance(n.op,ast.Div):return ev(n.left)/ev(n.right)
   if isinstance(n.op,ast.Pow):return ev(n.left)**ev(n.right)
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in _FUNCS and not n.keywords:
   return _FUNCS[n.func.id](*map(ev,n.args))
  raise ValueError('Unsupported exact expression syntax: '+ast.dump(n))
 return s.Add(*(sgn*ev(ast.parse(piece,mode='eval').body) for sgn,piece in pieces))
def load(path,locals=None):return parse(Path(path).read_text(),locals)
if __name__=='__main__':
 import time,json
 ROOT=Path(__file__).resolve().parent
 examples=['R_m1_m2/3 + Z2*log(2)**2 - 7*polylog(4,Rational(1,2))/9','(Z2+3)*(Z3-1)/7 - log(3)/11','2**(-7)*zeta(6)+pi**2/6']
 for text in examples:assert parse(text)==s.sympify(text),text
 records=[]
 for p in [ROOT/'series'/'norm_C5_2_0.expr',ROOT/'Phi_symbolic.expr']:
  st=time.time();text=p.read_text();ans=parse(text)
  assert str(ans)==text,(p,'canonical serialization changed')
  records.append({'file':p.name,'canonical_serialization_equal':True,'terms':len(s.Add.make_args(ans)),'seconds':time.time()-st})
 (ROOT/'exact_parser_checks.json').write_text(json.dumps(records,indent=2));print(records,flush=True)
