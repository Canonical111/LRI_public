"""Six-insertion counterterms checked against the independent lower-order RG flow."""
import sympy as s,json,argparse
from pathlib import Path
root=Path(__file__).resolve().parent;data=root/'data';l,g,B=s.symbols('l g B');z2=s.zeta(2);z3=s.zeta(3)
pa=argparse.ArgumentParser();pa.add_argument('--n6',type=int,default=10);pa.add_argument('--ne4',type=int,default=10);ar=pa.parse_args()
def pol(name):
 d=json.loads((data/name).read_text());return s.expand(sum((-1)**(j-1)*s.Float(d['coeff'][str(-j)][0],32)*l**(j-1)/s.factorial(j-1) for j in range(1,9)))
Q4=pol('m4_1_e0_base_N16_c0.json');Q4v=pol('m4_1_e0_v2_N16_c0.json');Q4p=pol('m4_1_e0_base_N16_c-1.json')
Z4=pol('m4_0_e0_base_N16_c0.json');Z4m=pol('m4_0_e0_base_N16_c1.json');Q6=pol(f'm6_1_e0_base_N{ar.n6}_c0.json')
eqname=f'm4_1_e1_e2_N{ar.ne4}_c0.json'
if not (data/eqname).exists():eqname=f'm4_1_e1_analytice_N{ar.ne4}_c0.json'
EQ4=pol(eqname)
K4=s.expand(Q4+l*l-2);K4v=s.expand(Q4v-2*l**3+8*l)
K6=s.expand(Q6-(l-1)*Q4-Q4p-l**3+l*l+3*l-3+(l+1)*Z4-Z4m)
EK4=s.expand(EQ4-l**3+l*l+(4*z2+2)*l-6)
L4=s.expand(-2*K4-16*l*K4-4*K4v+2*EK4)
Q=-l-1;L2=4*l*l+10*l+10-4*z2
HH2=-s.Rational(16,3)*l**3-22*l*l+(-44+16*z2)*l-44+24*z2+22*z3
G3=2*l*l-l;H4=s.Rational(4,3)*l**3-2*l*l-4*l
b=-18-6*z2+s.Rational(28,3)*z3+32*s.log(2)-12*s.log(3)-4*s.log(2)**2-8*s.polylog(2,-s.Rational(1,2))
f=32-s.Rational(136,3)*z3-64*s.log(2)+48*s.log(3)+16*s.log(2)**2+32*s.polylog(2,-s.Rational(1,2))
G5=s.Rational(10,3)*l**4-s.Rational(22,3)*l**3-(8*s.pi**2+39)*l*l/6-b*l
H6=s.expand(-(K6+4*K4*G3+Q*(2*G5+G3**2)+L2*(H4+2*l*G3)+2*HH2*l*l+L4*l))
physical=s.expand(-2*H6)
print('Sixth-order charge beta coefficient k:',s.N(4*H6.coeff(l,1),24))
print('New endpoint-response polynomial L4:')
for j in range(0,6):print(j,s.N(L4.coeff(l,j),24))
kk=s.symbols('kk');bg=(B*B-1)*g+(1-4*z2*(B*B-1))*g**3+b*g**5
bB=B*(2*g*g-8*g**4+f*(B*B-1)*g**4/2+kk*g**6/2)
def trunc(F):
 P=s.Poly(s.expand(F),g);return s.Add(*[coef*g**ij[0] for ij,coef in P.terms() if ij[0]<=6])
F=B;flow=B
for n in range(1,9):
 F=trunc(s.diff(F,g)*bg+s.diff(F,B)*bB);flow+=(-l)**n*F/s.factorial(n)
pred=s.expand(flow.subs(B,1)).coeff(g,6)
print('Six-insertion essential-charge higher-log residuals:')
res={}
for j in range(2,9):
 v=s.N(physical.coeff(l,j)-pred.coeff(l,j),25);print(j,v);res[str(j)]=str(v)
(data/f'six_log_check_{ar.n6}_{ar.ne4}.json').write_text(json.dumps(res,indent=2))
print('These residuals compare independently assembled response counterterms with the lower-order flow.')
