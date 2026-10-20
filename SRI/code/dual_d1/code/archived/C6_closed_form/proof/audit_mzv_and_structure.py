"""Independent exact derivation of the small MZV table and RG series rules."""
from pathlib import Path
from fractions import Fraction as Q
from collections import Counter
import sympy as s,json
from c6_relations import PHI,sh
root=Path(__file__).resolve().parent
Z2,Z3,Z4,Z5=s.symbols('Z2 Z3 Z4 Z5');z={2:Z2,3:Z3,4:Z4,5:Z5}
u,v=s.symbols('u v')
# Expansion of Gamma(1-u)Gamma(1-v)/Gamma(1-u-v), total degree <=5.
L=s.expand(sum(z[k]*(u**k+v**k-(u+v)**k)/k for k in range(2,6)))
E=s.expand(-L-L**2/2) # higher powers have total degree at least six.
height41=s.expand(E.coeff(u,3).coeff(v,2));height31=s.expand(E.coeff(u,2).coeff(v,2)).subs(Z2**2,s.Rational(5,2)*Z4)
assert s.expand(height41-(2*Z5-Z2*Z3))==0
assert height31==Z4/4
# Independently enumerate the shuffle zeta(2)*zeta(3).
shuffle53=sh((0,1),(0,0,1));assert shuffle53=={(0,1,0,0,1):1,(0,0,1,0,1):3,(0,0,0,1,1):6}
a=height41;b,c=s.symbols('b c');sol=s.solve([b+c-(Z2*Z3-Z5),3*b+c-(Z2*Z3-6*a)],(b,c))
assert s.expand(sol[b]-(3*Z2*Z3-s.Rational(11,2)*Z5))==0
assert s.expand(sol[c]-(s.Rational(9,2)*Z5-2*Z2*Z3))==0
values5={(0,0,0,0,1):-Z5,(0,0,0,1,1):a,(0,0,1,0,1):sol[b],(0,1,0,0,1):sol[c]}
for w,expr in list(values5.items()):
    dual=tuple(1-b for b in reversed(w));sign=(-1)**(sum(dual)-sum(w));values5[dual]=sign*expr
for w,expr in values5.items():
    alpha,beta=PHI[w];assert s.expand(expr-(s.Rational(alpha.numerator,alpha.denominator)*Z5+s.Rational(beta.numerator,beta.denominator)*Z2*Z3))==0,(w,expr)
# Confluent zero-intercept example: G(0,T+b;T)=-G(0,-b;T)+G(-b,-b;T).
from c6_relations import fib
assert fib(((0,0),(1,3)))=={(0,3):-1,(3,3):1}
# The fixed-point recursion is nonsingular in u=g^2,z, although g~sqrt(delta).
Jac=s.Matrix([[1,1],[4,0]]);assert Jac.det()==-4
report={'status':'all exact checks passed','height_one_41':str(height41),'height_one_31':str(height31),'weight_five_binary_values':{''.join(map(str,w)):str(s.expand(expr)) for w,expr in values5.items()},'shuffle_zeta2_zeta3':{'00011':6,'00101':3,'01001':1},'zero_intercept_confluence_check':True,'fixed_point_formal_jacobian_det':-4}
(root/'mzv_structure_checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
