"""Independent Fraction-only fixed-point trace calculation through delta^4.
No hypothesized value of C8 enters this program.
"""
from fractions import Fraction as Q
from pathlib import Path
import json
N=4

def plus(a,b):
 return [a[i]+b[i] for i in range(N+1)]
def scale(a,c):return [c*x for x in a]
def times(a,b):
 return [sum(a[j]*b[i-j] for j in range(i+1)) for i in range(N+1)]
def power(a,k):
 out=[Q(1)]+[Q(0)]*N
 for _ in range(k):out=times(out,a)
 return out
def evaluate(poly,u,z,d):
 out=[Q(0)]*(N+1)
 for (i,j,k),c in poly.items():out=plus(out,scale(times(times(power(u,i),power(z,j)),power(d,k)),c))
 return out
def diff(poly,var):
 out={}
 for mon,c in poly.items():
  p=mon[var]
  if p:
   new=list(mon);new[var]-=1;out[tuple(new)]=c*p
 return out

def calculate(coeff):
 q={key:Q(str(val)) for key,val in coeff.items()}
 F={(0,1,0):Q(1),(1,0,0):Q(1)}
 # u^i z^j delta^k coefficients, excluding the exactly known tree terms.
 fterms={'a':(1,1,0),'p':(1,0,1),'A':(1,2,0),'E':(1,1,1),'V':(1,0,2),'alpha':(1,3,0),'beta':(1,2,1),'gamma':(1,1,2),'W':(1,0,3),
         'b':(2,0,0),'G':(2,1,0),'R':(2,0,1),'Phi':(2,2,0),'Psi':(2,1,1),'S':(2,0,2),'J':(3,0,0),'Omega':(3,1,0),'U':(3,0,1),'J9':(4,0,0)}
 H={(0,0,1):Q(-1),(1,0,0):Q(4)}
 hterms={'c':(2,0,0),'f':(2,1,0),'q':(2,0,1),'L':(2,2,0),'M':(2,1,1),'Q':(2,0,2),'L3':(2,3,0),'M21':(2,2,1),'M12':(2,1,2),
         'k':(3,0,0),'N':(3,1,0),'P':(3,0,1),'N2':(3,2,0),'Nd':(3,1,1),'K':(4,0,0),'Kv':(4,1,0)}
 F.update({mon:q[key] for key,mon in fterms.items()});H.update({mon:q[key] for key,mon in hterms.items()})
 u=[Q(0)]*5;z=u.copy();d=u.copy();d[1]=Q(1)
 for order in range(1,5):
  rh=evaluate(H,u,z,d)[order];rf=evaluate(F,u,z,d)[order]
  u[order]=-rh/4;z[order]=-rf-u[order]
  assert not any(evaluate(H,u,z,d)[:order+1])
  assert not any(evaluate(F,u,z,d)[:order+1])
 # Full Jacobian, including pieces that vanish only at the fixed point.
 fulltrace=plus(plus(scale(evaluate(F,u,z,d),2),scale(times(u,evaluate(diff(F,0),u,z,d)),2)),
                plus(evaluate(H,u,z,d),times(plus([Q(1)]+[Q(0)]*4,z),evaluate(diff(H,1),u,z,d))))
 return {'u':u,'z':z,'trace':fulltrace,'C8':8*fulltrace[4]}
