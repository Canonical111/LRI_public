#!/usr/bin/env python3
"""Exact endpoint jets for the previously defined Gamma spectral trial.
All Gamma/polygamma values are reduced at integer/half-integer points.
The code handles the zero of reciprocal Gamma at q=0 by recurrence.
"""
import sympy as s
from pathlib import Path
import json
from functools import lru_cache
R=s.Rational
pi,L,Z=s.symbols('p l z')
MAX=3

def clean(a):return {k:s.expand(v) for k,v in a.items() if s.expand(v)!=0}
def add(*args):
 out={}
 for a in args:
  for k,v in a.items():out[k]=out.get(k,0)+v
 return clean(out)
def scale(a,c):return clean({k:c*v for k,v in a.items()})
def mul(a,b):
 out={}
 for (i,j),v in a.items():
  for (k,l),w in b.items():
   if i+j+k+l<=MAX:out[i+k,j+l]=out.get((i+k,j+l),0)+v*w
 return clean(out)
def powr(a,n):
 out={(0,0):s.Integer(1)}
 for _ in range(n):out=mul(out,a)
 return out
one={(0,0):s.Integer(1)}
y={(0,0):R(1,2),(1,0):s.Integer(1)}
t={(0,0):R(1,2),(0,1):s.Integer(1)}

def psi(q,n):
 q=R(q)
 base=1 if q.q==1 else R(1,2)
 val=([0,pi**2/6,-2*Z] if base==1 else [-2*L,pi**2/2,-14*Z])[n]
 # Euler's gamma omitted: cancels in the three logarithms, since 2ay-(ay+bt)-(ay-bt)=0.
 r=base
 while r<q:
  val+=(-1)**n*s.factorial(n)/r**(n+1)
  r+=1
 return s.expand(val)
def gam(q):
 return s.simplify(s.gamma(q)).subs(s.pi,pi)
@lru_cache(None)
def kernel(a,b):
 q0=1+R(a,2); qp=q0+R(b,2); qm=q0-R(b,2)
 factor=one
 if qm<=0:
  factor={(0,0):qm,(1,0):s.Integer(a),(0,1):-s.Integer(b)}
  qm+=1
 assert qm>0
 pref=s.cancel(gam(q0)**2/gam(qp)/gam(qm))
 Ay={(1,0):s.Integer(a)}
 plus={(1,0):s.Integer(a),(0,1):s.Integer(b)}
 minus={(1,0):s.Integer(a),(0,1):-s.Integer(b)}
 log={}
 for n in range(1,4):
  log=add(log,scale(powr(Ay,n),2*psi(q0,n-1)/s.factorial(n)),scale(powr(plus,n),-psi(qp,n-1)/s.factorial(n)),scale(powr(minus,n),-psi(qm,n-1)/s.factorial(n)))
 ex=add(one,log,scale(powr(log,2),R(1,2)),scale(powr(log,3),R(1,6)))
 return add(one,scale(mul(factor,ex),-pref))

P=[0,1,R(5,2),R(21,8),R(155,32),R(1075,128),R(8061,512)]
PS={
(0,1):[-R(508,9),-R(349,12),R(151,36),R(35,16),-R(719,16)],
(0,2):[R(2191,90),R(83,12),-R(13,36)],
(0,3):[-R(584,135)],
(1,1):[-R(56,3),R(147,2),-R(95,4),-R(419,16)],
(1,2):[R(17,3),-R(227,12)],
(2,1):[-4,-R(53,12)],(2,2):[R(3,2)]}
def poly(a):return add(*(scale(powr(y,i),v) for i,v in enumerate(a)))
base=add(powr(y,2),scale(powr(t,2),-4),mul(powr(t,2),poly(P)))
for ab,a in PS.items():base=add(base,mul(powr(t,2),mul(poly(a),kernel(*ab))))
# coefficient pair (constant, coefficient of tau)
extra={
 (8,1,None):(-R(158684509,23040),-R(2,3)),
 (10,0,None):(R(182483575,20736),R(4,3)),
 (6,1,(0,1)):(R(904279,160),R(2,3)),
 (8,0,(0,1)):(-R(8757751,1296),-R(4,3)),
 (6,1,(1,1)):(-R(3037,4),0),
 (8,0,(1,1)):(R(2852,3),0),
 (6,1,(2,1)):(R(596,3),-R(1,2)),
 (8,0,(2,1)):(0,1)}
S0=base;S1={}
for (pt,py,ab),(v0,v1) in extra.items():
 term=mul(powr(t,pt),powr(y,py))
 if ab is not None:term=mul(term,kernel(*ab))
 S0=add(S0,scale(term,v0)); S1=add(S1,scale(term,v1))
h=-R(2,3)
get=lambda j,a,b:j.get((a,b),0)*s.factorial(a)*s.factorial(b)
D=lambda j:s.factor(get(j,1,0))
B=lambda j:s.factor(get(j,0,2)+2*h*get(j,1,1)+h*h*get(j,2,0))
E=lambda j:s.factor(get(j,1,1)+h*get(j,2,0))
C=lambda j:s.factor(get(j,0,3)+3*h*get(j,1,2)+3*h*h*get(j,2,1)+h**3*get(j,3,0))
assert get(S0,0,0)==0
assert get(S1,0,0)==0
assert get(S1,1,0)==0 and get(S1,0,1)==0
assert s.expand(get(S0,0,1)+h*get(S0,1,0))==0
names={'base_endpoint':get(base,0,0),'D':D(S0),'B0':B(S0),'B1':B(S1),'E0':E(S0),'E1':E(S1),'C0':C(S0),'C1':C(S1)}
def main():
    values={pi:s.pi,L:s.log(2),Z:s.zeta(3)}
    for k,v in names.items():
     print(k,'=',v)
     print(' numerical=',s.N(v.subs(values),30))
    root=Path(__file__).resolve().parent
    (root/'endpoint_exact_expressions.json').write_text(json.dumps({k:s.sstr(v) for k,v in names.items()},indent=2)+'\n')
    # Every jet entry is kept for independently reproducing directional derivatives.
    (root/'jets_exact.json').write_text(json.dumps({label:{str(k):s.sstr(v) for k,v in j.items()} for label,j in [('S0',S0),('S1',S1)]},indent=2)+'\n')
    (root/'endpoint_exact_latex.txt').write_text('\n\n'.join(k+' = '+s.latex(v) for k,v in names.items())+'\n')

if __name__=="__main__":
    main()
