"""Independent extraction of complete archived controls versus direct terminal functional."""
from pathlib import Path
from fractions import Fraction as F
import json,time
import sympy as s
import terminal_projection as tp
import terminal_projection_v1 as old
from hyperlog_core import *
from read_expression import parse
ROOT=Path(__file__).resolve().parent

def pi0(expr):
 ex=parse(expr)
 repl={a:s.S.Zero for a in ex.free_symbols if str(a)!='ell'}
 repl[s.pi]=s.S.Zero
 for a in s.preorder_traversal(ex):
  if a.func in (s.log,s.polylog,s.zeta):repl[a]=s.S.Zero
 return s.expand(ex.xreplace(repl))

def compute(name,n):
 st=time.time();rows=json.loads((ROOT/f'{name}_stage{n-2}.json').read_text());out=[F(0)]*5
 demands=((0,1),(-2,0),(-2,1),(-1,0),(-1,1))
 for j,(words,logs,cstr) in enumerate(rows):
  if len(logs)>1:continue
  coef=K.from_expr(cstr)
  # Coefficients have only rational functions and positive-weight zeta generators.
  for i in range(8,K.ngens):
   coef=sub(coef,i,K.zero)
  if not coef:continue
  word=tuple(tp.field_letter(K.from_expr(a),n-1,e) for a in words[-1])
  vals=tp.apply_field(coef,word,len(logs),n-1,demands,qindex=n-1)
  out=[a+b for a,b in zip(out,vals)]
  if j%250==0:print(name,j,'/',len(rows),flush=True)
 expect=[]
 for p,m in demands:
  fp=ROOT/'series'/f'{name}_p{p}.expr'
  if fp.exists():
   val=pi0(fp.read_text()).coeff(s.Symbol('ell'),m)
   expect.append(str(val))
  else:expect.append(None)
 result={'name':name,'demands':demands,'actual':list(map(str,out)),'archived_expectation':expect,'all_available_equal':all(b is None or a==F(b) for a,b in zip(out,expect)),'seconds':time.time()-st}
 print(json.dumps(result),flush=True)
 assert result['all_available_equal']
 return result
r=[]
for name,n in [('Q6_v',6),('Q6_d',6)]:r.append(compute(name,n))
(ROOT.parent/'terminal_controls.json').write_text(json.dumps(r,indent=2))
