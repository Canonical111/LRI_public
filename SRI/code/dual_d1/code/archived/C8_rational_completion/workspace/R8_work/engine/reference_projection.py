"""Read formal weight-zero rational cutoff polynomials from archived expressions.
No expression is executed; positive-weight constants are mapped to zero.
"""
import ast,sys
sys.setrecursionlimit(300000)
from fractions import Fraction as F

def add(a,b):
 r=dict(a)
 for k,c in b.items():r[k]=r.get(k,F(0))+c
 return {k:c for k,c in r.items() if c}
def mul(a,b):
 r={}
 for i,c in a.items():
  for j,d in b.items():r[i+j]=r.get(i+j,F(0))+c*d
 return {k:c for k,c in r.items() if c}
def const(q):return {0:F(q)} if q else {}
def ev(n):
 if isinstance(n,ast.Constant):return const(n.value)
 if isinstance(n,ast.Name):return {1:F(1)} if n.id=='ell' else {}
 if isinstance(n,ast.Call):return {}
 if isinstance(n,ast.UnaryOp):return {k:(-c if isinstance(n.op,ast.USub) else c) for k,c in ev(n.operand).items()}
 if isinstance(n,ast.BinOp):
  a=ev(n.left);b=ev(n.right)
  if isinstance(n.op,ast.Add):return add(a,b)
  if isinstance(n.op,ast.Sub):return add(a,{k:-c for k,c in b.items()})
  if isinstance(n.op,ast.Mult):return mul(a,b)
  if isinstance(n.op,ast.Div):
   assert set(b)=={0} and b[0];return {k:c/b[0] for k,c in a.items()}
  if isinstance(n.op,ast.Pow):
   assert set(b)<={0};p=b.get(0,F(0));assert p.denominator==1 and p>=0
   r=const(1)
   for _ in range(p.numerator):r=mul(r,a)
   return r
 raise ValueError(ast.dump(n))
def read(p):return ev(ast.parse(p.read_text().strip(),mode='eval').body)
if __name__=='__main__':
 from pathlib import Path
 p=Path('/mnt/data/tail_work/old_C7/C7_completion/engine/series')
 for name in ['Z4_base','Z4_v','Z4_d','Z6_base','Z6_v','A5_base','A5_v','A5_d','A7_base','A7_v']:
  f=p/(name+'_p0.expr')
  if f.exists():print(name,{str(k):str(v) for k,v in sorted(read(f).items())})
