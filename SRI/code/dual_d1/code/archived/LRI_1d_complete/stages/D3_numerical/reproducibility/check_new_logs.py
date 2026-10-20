"""Independent finite-tail fourth-order high-logarithm RG check."""
import sympy as s,json
from pathlib import Path
root=Path(__file__).resolve().parent
l,g,B,d=s.symbols('l g B d');Z2=s.zeta(2);Z3=s.zeta(3);Z4=s.zeta(4);rt=s.sqrt(2)
a=-4*Z2;c=-16;p=8-2*Z2-7*Z3-8*s.log(2)
f=32-s.Rational(136,3)*Z3-64*s.log(2)+48*s.log(3)+16*s.log(2)**2+32*s.polylog(2,-s.Rational(1,2))
qd=s.symbols('qd')
# Moment coefficients from quadrature: retain symbols for all genuinely new pieces.
raw={}
for pair,weight in [('01',-s.Rational(1,2)),('02',s.Rational(1,2)),('03',-s.Rational(1,4)),('12',-s.Rational(1,4))]:
 data=json.loads((root/'data'/f'm4_1_e0_vv_N16_c0_p{pair}.json').read_text())
 for j in range(1,9):raw[j-1]=raw.get(j-1,0)+weight*(-1)**(j-1)*s.Float(data['coeff'][str(-j)][0],35)/s.factorial(j-1)
Qd=sum(val*l**j for j,val in raw.items())
Kd=Qd-s.Rational(2,3)*l**4+2*l*l+8
Q=-l-1;Q2d=l**3/3+2;L2=4*l*l+10*l+10-4*Z2
L2d=-s.Rational(2,3)*l**4+2*l**3+4*l*l-16*l-60+12*Z2+12*Z3+8*Z4
G3=2*l*l-l;G3d=-l**4/3+s.Rational(5,3)*l**3+2*Z2*l*l-p*l
H2=l;H2d=-l**3/3;H4=s.Rational(4,3)*l**3-2*l*l-4*l
H4d=s.expand(-(Kd+2*Q2d*G3+2*Q*G3d+L2d*H2+L2*H2d))
physical=s.expand(-2*H4d-l*H4)
print('Raw fourth-tail response coefficients:')
for j in range(1,8):print(j,s.N(raw[j],24))
print('Beta coefficient q:',s.N(4*H4d.coeff(l,1),24))
# Lie-series prediction. Project powers after each derivative, but retain exact B dependence.
bg=(B*B-1)*g+(1+a*(B*B-1)+p*d)*g**3
bB=B*(-d/2+2*g*g+c*g**4/2+f*(B*B-1)*g**4/2+qd*d*g**4/2)
def truncate(F):
 F=s.Poly(s.expand(F),g,d)
 return s.Add(*[coef*g**ij[0]*d**ij[1] for ij,coef in F.terms() if ij[0]<=4 and ij[1]<=1])
F=B;flow=B
for n in range(1,9):
 F=truncate(s.diff(F,g)*bg+s.diff(F,B)*bB)
 flow+=(-l)**n*F/s.factorial(n)
pred=s.Poly(s.expand(flow.subs(B,1)),g,d).coeff_monomial(g**4*d)
print('Matched essential charge high-log residuals:')
for j in range(2,9):print(j,s.N(physical.coeff(l,j)-s.expand(pred).coeff(l,j),25))
print('Quadrature-based high-log checks complete; residuals must converge to zero.')
