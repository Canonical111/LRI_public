"""Independent sparse exact polynomial algebra for regularized periods.
Monomials are tuples of (printed scalar atom, exponent), coefficients Fractions.
No real constants are assigned numerical values.
"""
from fractions import Fraction as F
from functools import lru_cache
from math import factorial
import ast,json,re

def add(out,poly,scale=F(1)):
 if not scale:return
 for m,c in poly.items():
  z=out.get(m,F(0))+c*scale
  if z:out[m]=z
  else:out.pop(m,None)
def mono(a,b):
 d=dict(a)
 for k,v in b:d[k]=d.get(k,0)+v
 return tuple(sorted((k,v) for k,v in d.items() if v))
def mul(a,b):
 out={}
 for m,c in a.items():
  for n,d in b.items():
   ky=mono(m,n);out[ky]=out.get(ky,F(0))+c*d
 return {k:v for k,v in out.items() if v}
def powp(a,n):
 assert n>=0
 out={():F(1)}
 for _ in range(n):out=mul(out,a)
 return out
def atom(a):return {((a,1),):F(1)}
def log(a):
 a=F(a);assert a>0
 return {} if a==1 else atom('log('+str(a)+')')
@lru_cache(maxsize=20000)
def shuffle(a,b):
 if not a:return {b:1}
 if not b:return {a:1}
 out={}
 for w,c in shuffle(a[1:],b).items():out[(a[0],)+w]=out.get((a[0],)+w,0)+c
 for w,c in shuffle(a,b[1:]).items():out[(b[0],)+w]=out.get((b[0],)+w,0)+c
 return out
@lru_cache(maxsize=250000)
def R(w):
 w=tuple(map(F,w))
 if not w:return {():F(1)}
 if all(a==0 for a in w):return {}
 if len(set(w))==1 and w[0]<0:return {m:c*F((-1)**len(w),factorial(len(w))) for m,c in powp(log(-w[0]),len(w)).items()}
 if w[-1]==0:
  ss=shuffle((F(0),),w[:-1]).copy();mu=ss.pop(w);out={}
  for x,c in ss.items():add(out,R(x),-F(c,mu))
  return out
 if len(w)==2 and all(x<0 for x in w):
  a,b=-w[0],-w[1];out=mul(log(a),log(b));add(out,powp(log(a),2),-F(1,2))
  arg=1-b/a
  if arg: add(out,atom('polylog(2,'+str(arg)+')'),-F(1))
  return out
 if w[-1]<0 and all(a==0 for a in w[:-1]):
  m=len(w);ln={k:-v for k,v in log(-w[-1]).items()};out={}
  add(out,powp(ln,m),F(1,factorial(m)))
  for k in range(1,m//2+1):
   zname='Z'+str(2*k) if 2*k in (2,4) else 'zeta('+str(2*k)+')'
   add(out,mul(atom(zname),powp(ln,m-2*k)),F(2)*(1-F(1,2)**(2*k-1))/factorial(m-2*k))
  return out
 def name(x):
  assert x.denominator==1,x
  return ('m'+str(-x.numerator)) if x<0 else str(x.numerator)
 return atom('R_'+'_'.join(map(name,w)))

def terms(text):
 depth=0;start=0
 for i,c in enumerate(text):
  if c in '([':depth+=1
  elif c in ')]':depth-=1
  elif c in '+-' and depth==0 and i and text[i-1].isspace():
   if text[start:i].strip():yield text[start:i].strip()
   start=i
 if text[start:].strip():yield text[start:].strip()
def scalarval(n):
 if isinstance(n,ast.Constant):return F(n.value)
 if isinstance(n,ast.UnaryOp):return -scalarval(n.operand) if isinstance(n.op,ast.USub) else scalarval(n.operand)
 if isinstance(n,ast.BinOp):
  a,b=scalarval(n.left),scalarval(n.right)
  if isinstance(n.op,ast.Div):return a/b
  if isinstance(n.op,ast.Sub):return a-b
  if isinstance(n.op,ast.Add):return a+b
  if isinstance(n.op,ast.Mult):return a*b
  if isinstance(n.op,ast.Pow):return a**int(b)
 raise ValueError(ast.dump(n))
def parse_expr(text):
 def ev(n):
  if isinstance(n,ast.Constant):return {():F(n.value)}
  if isinstance(n,ast.Name):return atom(n.id)
  if isinstance(n,ast.Call):
   assert n.func.id in ('log','polylog','zeta','Rational')
   args=tuple(scalarval(a) for a in n.args)
   if n.func.id=='Rational':return {():args[0]/args[1]}
   if n.func.id=='log':return log(args[0])
   if n.func.id=='polylog' and args[1]==0:return {}
   return atom(n.func.id+'('+','.join(map(str,args))+')')
  if isinstance(n,ast.UnaryOp):
   out=ev(n.operand);return {m:-c for m,c in out.items()} if isinstance(n.op,ast.USub) else out
  if isinstance(n,ast.BinOp):
   a=ev(n.left)
   if isinstance(n.op,ast.Pow):return powp(a,int(scalarval(n.right)))
   b=ev(n.right)
   if isinstance(n.op,ast.Add):add(a,b);return a
   if isinstance(n.op,ast.Sub):add(a,b,-1);return a
   if isinstance(n.op,ast.Mult):return mul(a,b)
   if isinstance(n.op,ast.Div):
    assert set(b)=={()};return {m:c/b[()] for m,c in a.items()}
  raise ValueError(ast.dump(n))
 out={}
 for t in terms(text):add(out,ev(ast.parse(t,mode='eval').body))
 return out

def dump(poly):
 out=[]
 for m,c in sorted(poly.items()):
  if not c:continue
  body=str(abs(c))+''.join('*'+a+('**'+str(k) if k!=1 else '') for a,k in m)
  sign='-' if c<0 else ''
  if out:sign=' - ' if c<0 else ' + '
  out.append(sign+body)
 return ''.join(out) or '0'
