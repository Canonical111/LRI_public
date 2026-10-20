"""Independent RG Lie-series checks of the seventh-insertion higher logs.
The unknown finite h^2 coefficient of C3 affects only log^2 at this order;
we keep it symbolic and test powers log^3 and higher without assuming it.
"""
import sympy as s,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
l,g,h=s.symbols('ell g h');z2,z3,z4=s.symbols('Z2 Z3 Z4');a,b,f,A,G,J,k=s.symbols('a b f A G J k')
v=(1-s.sqrt(2)*h)**2;z=v-1
bg=z*g+(1+a*z+A*z*z)*g**3+(b+G*z)*g**5+J*g**7
bh=-(1-s.sqrt(2)*h)/s.sqrt(2)*(2*g*g+(-8+f*z/2)*g**4+k*g**6/2)
C30,j3,C50,j5,H3,C70=s.symbols('C30 j3 C50 j5 H3 C70')
# A1(eta)=B(1+eta,1+eta), eta=sqrt(2)h-2h^2.
et=s.symbols('eta')
logB=-2*et+(2-z2)*et**2+(2*z3-s.Rational(8,3))*et**3
A1=s.series(s.exp(logB),et,0,4).removeO().subs(et,s.sqrt(2)*h-2*h*h)
R0=g*A1+g**3*(C30+s.sqrt(2)*j3*h+H3*h*h)+g**5*(C50+s.sqrt(2)*j5*h)+C70*g**7

def trunc(ex):
 return s.Add(*(co*g**ig*h**ih for (ig,ih),co in s.Poly(s.expand(ex),g,h).terms() if ig+2*ih<=7))
cur=trunc(R0);checks={}
for n in range(1,8):
 cur=trunc(bg*s.diff(cur,g)+bh*s.diff(cur,h))
 co=s.expand(cur.subs(h,0)).coeff(g,7)/s.factorial(n)
 checks[n]=s.expand(co)
 print('predicted log',n,s.factor(co),flush=True)
for n in range(3,8):assert H3 not in checks[n].free_symbols
C30val=3-2*z2
C30v=18-14*z2-15*z3-8*s.log(2)
j3val=-2*C30v-26+8*z2
P=4*z2+s.Rational(8,3)*z3-2+3*s.log(3)+s.log(2)**2+2*s.polylog(2,-s.Rational(1,2))
bval=-18-6*z2+s.Rational(28,3)*z3+32*s.log(2)-12*s.log(3)-4*s.log(2)**2-8*s.polylog(2,-s.Rational(1,2))
fval=32-s.Rational(136,3)*z3-64*s.log(2)+48*s.log(3)+16*s.log(2)**2+32*s.polylog(2,-s.Rational(1,2))
sub={a:-4*z2,A:-8-4*z2-2*z3+16*s.log(2),b:bval,f:fval,C30:C30val,j3:j3val}
for n in range(3,8):
 co=s.expand(checks[n].subs(sub))
 (ROOT/f'C7_log{n}_predicted.expr').write_text(str(co))
 print('known predicted',n,co,flush=True)
if (ROOT/'series'/'norm_C7_0_0.expr').exists():
 raw=s.sympify((ROOT/'series'/'norm_C7_0_0.expr').read_text()).subs(s.pi**2,6*z2)
 for n in range(3,8):
  diff=s.expand(raw.coeff(l,n)-checks[n].subs(sub))
  (ROOT/f'C7_log{n}_residual.expr').write_text(str(diff))
  print('CHECK residual',n,diff,flush=True)
