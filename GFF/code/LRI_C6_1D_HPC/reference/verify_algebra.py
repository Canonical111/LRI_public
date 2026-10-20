"""Independent exact derivation of the sixth fixed-point coefficient."""
from pathlib import Path
import json
import sympy as s
z,A=s.symbols('z A'); b3,b4,b5,b6,c3,c4,c5,c6=s.symbols('b3 b4 b5 b6 c3 c4 c5 c6')
v=(-6*A*z+b3*z**2+b4*z**3+b5*z**4+b6*z**5)/3
Bminus6=s.Integer(0);term=s.Integer(1)
for k in range(6):
 Bminus6+=(-1)**k*s.binomial(5+k,k)*term
 term=s.Poly(s.expand(term*v),z)
 term=sum(coef*z**mon[0]for mon,coef in term.terms()if mon[0]<=5)
gp=1-2*A*z+3*c3*z**2+4*c4*z**3+5*c5*z**4+6*c6*z**5
C=s.expand(gp*Bminus6).coeff(z,5)/s.Integer(6*3**6)
low=2016*A**5-448*A**3*b3+672*A**3*c3-84*A**2*b4+168*A**2*c4+s.Rational(49,3)*A*b3**2-42*A*b3*c3-12*A*b5+30*A*c5+s.Rational(7,3)*b3*b4-4*b3*c4-3*b4*c3
assert s.expand(2187*C-low-3*c6+b6)==0
# a50,e50 are new five-loop finite terms; a61,e61 the new six-loop simple residues.
a50,e50,a61,e61=s.symbols('a50 e50 a61 e61')
newpart=s.expand((3*(96*e50-6*e61)-(108*a50-6*a61))/2187)
expected=s.Rational(4,243)*(8*e50-3*a50)-s.Rational(2,729)*(3*e61-a61)
assert s.expand(newpart-expected)==0
out={'C6_R6_RG_numerator':str(low),'dC6_dc6':str(s.diff(C,c6)),'dC6_db6':str(s.diff(C,b6)),'dC6_dH6':'-2/729','dC6_dJ5':'4/243','exact_checks_passed':True,'method':'Lagrange inversion, independently expanded over exact rational polynomials'}
p=Path(__file__).resolve().parent
(p/'six_loop_algebra_checks.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
