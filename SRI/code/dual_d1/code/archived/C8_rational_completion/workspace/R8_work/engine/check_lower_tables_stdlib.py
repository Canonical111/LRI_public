"""Standalone regeneration of the lower-moment singular controls.
Uses a restricted rational-expression AST and Fraction polynomial arithmetic;
no SymPy, native modules, new raw residues, or C8 conjecture is needed.
"""
from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
from math import comb,factorial
import ast,json,sys,time,hashlib
sys.setrecursionlimit(50000)
ROOT=Path(__file__).resolve().parent.parent
ARCH=ROOT.parent/'old_C7/C7_completion/engine'

def trim(a):
 a=list(a)
 while a and not a[-1]:a.pop()
 return tuple(a)
def add(a,b):
 out=list(a)+[F(0)]*max(0,len(b)-len(a))
 for j,c in enumerate(b):out[j]+=c
 return trim(out)
def scale(a,c):return trim([c*v for v in a])
def mul(a,b):
 if not a or not b:return ()
 out=[F(0)]*(len(a)+len(b)-1)
 for j,c in enumerate(a):
  for k,d in enumerate(b):out[j+k]+=c*d
 return trim(out)
def power(a,n):
 assert n>=0
 ans=(F(1),)
 while n:
  if n&1:ans=mul(ans,a)
  a=mul(a,a);n//=2
 return ans

def read_fraction(node):
 if isinstance(node,ast.Constant) and isinstance(node.value,int):return (F(node.value),),(F(1),)
 if isinstance(node,ast.Name) and node.id=='e':return (F(0),F(1)),(F(1),)
 if isinstance(node,ast.UnaryOp):
  n,d=read_fraction(node.operand)
  if isinstance(node.op,ast.USub):return scale(n,-1),d
  if isinstance(node.op,ast.UAdd):return n,d
 if isinstance(node,ast.BinOp):
  n,d=read_fraction(node.left)
  if isinstance(node.op,ast.Pow):
   b,c=read_fraction(node.right);assert len(b)<=1 and len(c)==1 and c[0];k=(b[0] if b else F(0))/c[0];assert k.denominator==1;k=int(k)
   return (power(n,k),power(d,k)) if k>=0 else (power(d,-k),power(n,-k))
  m,e=read_fraction(node.right)
  if isinstance(node.op,ast.Add):return add(mul(n,e),mul(m,d)),mul(d,e)
  if isinstance(node.op,ast.Sub):return add(mul(n,e),scale(mul(m,d),-1)),mul(d,e)
  if isinstance(node.op,ast.Mult):return mul(n,m),mul(d,e)
  if isinstance(node.op,ast.Div):return mul(n,e),mul(d,m)
 raise ValueError('Unsupported rational expression: '+ast.dump(node))

@lru_cache(None)
def rational_series(text,maxp):
 n,d=read_fraction(ast.parse(text,mode='eval').body);n=trim(n);d=trim(d)
 if not n:return {}
 assert d
 sn=next(i for i,c in enumerate(n) if c);sd=next(i for i,c in enumerate(d) if c);shift=sn-sd
 if shift>maxp:return {}
 n=n[sn:];d=d[sd:];out=[]
 for j in range(maxp-shift+1):
  rhs=(n[j] if j<len(n) else F(0))-sum((d[k]*out[j-k] for k in range(1,min(j,len(d)-1)+1)),F(0));out.append(rhs/d[0])
 return {j+shift:c for j,c in enumerate(out) if c}

def integrate_polynomial(rhs,a):
 assert a
 out=[F(0)]*len(rhs)
 for j in range(len(rhs)-1,-1,-1):out[j]=(rhs[j]-(j+1)*(out[j+1] if j+1<len(out) else F(0)))/a
 return trim(out)
@lru_cache(None)
def large(w,n):
 if not w:return (F(1),) if not n else ()
 if not n:return (F(0),)*len(w)+(F(1,factorial(len(w))),)
 rhs=()
 for j in range(n+1):rhs=add(rhs,scale(large(w[1:],n-j),w[0]**j))
 return integrate_polynomial(rhs,-n)
@lru_cache(None)
def shift_coeff(N,k,d,h):
 if h>d:return F(0)
 l=(F(0),)+tuple(F(-N**j,j) for j in range(1,d+1));prod=(F(1),)
 for _ in range(h):prod=mul(prod,l)[:d+1]
 return sum((c*(F(comb(k+d-j-1,d-j))*N**(d-j) if k else F(int(d==j))) for j,c in enumerate(prod) if j<=d),F(0))
@lru_cache(None)
def gjet(w,N,d):
 out=()
 for k in range(d+1):
  p=large(w,k)
  for deg,c in enumerate(p):
   if not c:continue
   for m in range(deg+1):
    val=c*comb(deg,m)*(-1)**m*shift_coeff(N,k,d-k,deg-m)
    if val:out=add(out,(F(0),)*m+(val,))
 return out

def raw(n,kind,deriv,mx):
 path=ARCH/f'{kind}{n}_{deriv}_negative.json';out={}
 for w,logs,c in json.loads(path.read_text()):
  for p,a in rational_series(c,mx).items():
   for j in range(mx-p+1):
    q=gjet(tuple(map(F,w)),n-1,j)
    if q:out[p+j]=add(out.get(p+j,()),(F(0),)*len(logs)+scale(q,a))
 return {p:a for p,a in out.items() if a}

def tabmul(a,b):
 out={}
 for p,u in a.items():
  for q,v in b.items():out[p+q]=add(out.get(p+q,()),mul(u,v))
 return {p:a for p,a in out.items() if a}
def tadd(a,b,f=1):
 out=dict(a)
 for p,u in b.items():out[p]=add(out.get(p,()),scale(u,f))
 return {p:a for p,a in out.items() if a}
def encode(t):return {str(p):list(map(str,v)) for p,v in sorted(t.items()) if v}

def main():
 st=time.time();checks=[];all_hash={}
 tail={}
 for k,n,mx in [('A',3,1),('A',5,0),('Z',2,0),('Z',4,0)]:
  for der in ['base','d']:
   tail[k,n,der]=raw(n,k,der,mx)
 terms=[(1,[('A',5),('Z',2)]),(-1,[('A',3),('Z',2),('Z',2)]),(1,[('A',3),('Z',4)]),(1,[('Z',2)]*3),(-2,[('Z',2),('Z',4)])]
 pt={}
 for sign,fs in terms:
  for ider in range(len(fs)):
   v={0:(F(1),)}
   for j,(k,n) in enumerate(fs):v=tabmul(v,tail[k,n,'d' if j==ider else 'base'])
   pt=tadd(pt,{p:a for p,a in v.items() if p<0},sign)
 ref=json.loads((ROOT/'tail_lower_controls.json').read_text())
 expected={int(p):trim(list(map(F,a))) for p,a in ref['singular_tail_difference'].items()}
 assert {p:trim(a) for p,a in pt.items() if a}=={p:a for p,a in expected.items() if a},(encode(pt),encode(expected))
 checks.append({'identity':'tail singular difference','polynomials':encode(pt),'exact_equal':True})
 # Reconstruct every old base/charge polynomial used for scale restoration.
 restoration={}
 for k,n in [('A',7),('Z',6)]:
  for d in ['base','v']:
   v=raw(n,k,d,0);key=f'{k}{n}_{d}';expected={int(p):trim(list(map(F,a))) for p,a in ref['archived_base_and_charge_polynomials'][key].items()}
   assert v=={p:a for p,a in expected.items() if a},(key,encode(v),encode(expected));restoration[key]=encode(v)
 ninth={}
 for k,n,mx in [('A',3,2),('A',5,1),('A',7,0),('Z',2,0),('Z',4,1),('Z',6,0)]:ninth[k,n]=raw(n,k,'base',mx)
 terms=[(1,[('A',7),('Z',2)]),(-1,[('A',5),('Z',2),('Z',2)]),(1,[('A',5),('Z',4)]),(1,[('A',3),('Z',2),('Z',2),('Z',2)]),(-2,[('A',3),('Z',2),('Z',4)]),(1,[('A',3),('Z',6)]),(-1,[('Z',2)]*4),(3,[('Z',2),('Z',2),('Z',4)]),(-1,[('Z',4),('Z',4)]),(-2,[('Z',2),('Z',6)])]
 pn={}
 for sign,fs in terms:
  v={0:(F(1),)}
  for key in fs:v=tabmul(v,ninth[key])
  pn=tadd(pn,{p:a for p,a in v.items() if p<0},sign)
 nr=json.loads((ROOT/'ninth_lower_controls.json').read_text());expected={int(p):trim(list(map(F,a))) for p,a in nr['polynomials'].items()}
 assert pn=={p:a for p,a in expected.items() if a},(encode(pn),encode(expected))
 checks.append({'identity':'ninth singular difference','polynomials':encode(pn),'exact_equal':True})
 result={'status':'independent_standard_library_lower_controls_pass','checks':checks,'restoration_polynomials':restoration,
         'new_residues_read_as_inputs':False,'C8_conjecture_used':False,'seconds':time.time()-st}
 (ROOT/'stdlib_lower_controls.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
