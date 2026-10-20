"""Exact rational audit of every tail insertion, including its scalar prefactor."""
from pathlib import Path
from fractions import Fraction
import json, math
import sympy as s
import horn_compiler as h
Q=s.Rational(3,10)
def ev(x):
 z=s.cancel(s.sympify(x,locals={'q':h.q}).subs(h.q,Q));return Fraction(int(z.p),int(z.q))
def rf(a,k):
 a=ev(a);x=Fraction(1)
 for j in range(k):x*=a+j
 return x
def term(t,k):
 x=ev(t.pref)
 for a,v in t.upper:x*=rf(a,sum(i*j for i,j in zip(v,k)))
 for a,v in t.lower:x/=rf(a,sum(i*j for i,j in zip(v,k)))
 for z,j in zip(t.z,k):x*=int(z)**j
 x*=ev(s.sympify(t.poly).subs({s.Symbol('N'+str(i)):v for i,v in enumerate(k)}))
 return x
count=0
for block in [0,1]:
 for vec in [(1,1),(0,1),(1,2)]:
  atoms=[h.Atom('D',r,h.q,2*h.q,vec) for r in range(6)]+[h.Atom('J',r,1-h.q,None,vec) for r in range(1,6)]+[h.Atom('H',0,h.q,None,vec),h.Atom('B',0,2*h.q,None,vec)]
  for at in atoms:
   for choice in range(at.order+1) if at.kind=='D' else [0]:
    for k in [0,3]:
     old=h.base(h.Master('test',3,s.Integer(1),alternating=True),block)
     idx=(2,) if block==0 else (2,1)
     ell=0 if block==0 else idx[0]+1;nn=idx[0] if block==0 else idx[1]
     N=vec[0]*ell+vec[1]*nn;a=ev(at.a);u=Fraction(N)+a+k;q=ev(h.q)
     if at.kind=='D':
      b=ev(at.b);r=at.order;ratio=(-1)**(r+1)*math.factorial(r)*(b-a)/(u**(r+1-choice)*(Fraction(N)+b+k)**(choice+1))
     elif at.kind=='J':ratio=(-1)**(at.order+1)*math.factorial(at.order)/u**(at.order+1)
     elif at.kind=='H':ratio=Fraction(N)/((a+k)*u)
     else:ratio=-q*q*rf(1-h.q,k)*rf(1+h.q,k)/(rf(2,k)*rf(at.a+N,k+1))
     new=old.copy();h.insert(new,at,choice,block)
     assert term(new,idx+(k,))==term(old,idx)*ratio,(block,at,choice,k)
     count+=1
# The displayed E6 equals the independently recursive coefficient polynomial.
x=s.symbols('x1:7');a,b,c,d,e,f=x
explicit=(a**6+15*a**4*b+20*a**3*c+45*a*a*b*b+15*a*a*d+60*a*b*c+6*a*e+15*b**3+15*b*d+10*c*c+f)/720
assert s.expand(explicit-h.ecoeff(x,6))==0
# Recheck all d=2 collected substitutions without using saved numeric coefficients.
A,R,U,V,X,Qsym,P4,P5,K,L,Z,a,G,z3=s.symbols('A R U V X Q P4 P5 K L Z a G z3')
C4=16*P4-A**3-8*A*Qsym-3*A*R+s.Rational(53,2)*U-3*V
C5=-1536*(P5+K)+384*A*P4-576*L-1728*Qsym**2+720*A*A*Qsym+1008*Qsym*R+7152*Z-15*A**4-90*A*A*R+414*A*U-108*A*V-117*R**2-75*X
sub={A:4*a,R:0,U:-14*z3,V:-4*z3,X:0,Z:4*G*Qsym}
r4=16*P4-64*a**3-32*a*Qsym-359*z3
r5=-1536*(P5+K)+1536*a*P4-576*L-1728*Qsym**2+(11520*a*a+28608*G)*Qsym-3840*a**4-21456*a*z3
assert s.expand(C4.subs(sub)-r4)==0
assert s.expand(C5.subs(sub)-r5)==0
out=dict(exact_rational_insertion_checks=count,all_passed=True,E6_polynomial_identity=True,d2_C4_substitution=True,d2_C5_substitution=True)
p=Path(__file__).resolve().parents[2]/'verification/general_closed/insertion_prefactor_checks.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2));print(out)
