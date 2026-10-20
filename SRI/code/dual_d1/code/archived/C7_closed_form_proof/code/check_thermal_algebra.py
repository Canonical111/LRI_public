#!/usr/bin/env python3
"""Independent exact characteristic-polynomial conversion; requires SymPy.

This checks the algebra and the proposed closed-form relation between C7 and
D4. The separate free-word certificate establishes the period identity.
"""
from pathlib import Path
import json
import sympy as s
r=Path(__file__).resolve().parent.parent
z2,z3,z4,z5,z6=s.symbols('Z2 Z3 Z4 Z5 Z6')
T2=2-2*z2-4*z3
T3=(26-38*z2+104*z3-80*z4-272*z5+112*z2*z3)/4
c3=s.Rational(39,16)+2*z2
c5=s.Rational(11249,1024)-s.Rational(361,16)*z2+24*z3+s.Rational(49,2)*z4
D4=13-s.Rational(179,8)*z2+s.Rational(47,2)*z3-s.Rational(493,8)*z4+289*z5-130*z2*z3+s.Rational(499,4)*z6-76*z3**2
C7=s.Rational(1798583,32768)-s.Rational(90637,1024)*z2+s.Rational(453,4)*z3-s.Rational(16835,64)*z4+1224*z5-540*z2*z3+s.Rational(4335,8)*z6-320*z3**2
remainder=s.expand(4*D4-T3-T2**2+c3*c5/2-C7)
remainder=s.expand(remainder.subs(z2*z4,s.Rational(7,4)*z6).subs(z2**2,s.Rational(5,2)*z4))
assert remainder==0
# Direct coefficient extraction, independent of the recurrence formula.
t=s.symbols('t'); T1,Dt2,Dt3,Dt4,Tr2,Tr3,Tr4=s.symbols('T1 D2 D3 D4 T2 T3 T4')
T=t**2/2+Tr2*t**4+Tr3*t**6+Tr4*t**8
D=-2*t**2+Dt2*t**4+Dt3*t**6+Dt4*t**8
root=s.sqrt(2)*t*s.series(s.sqrt((T*T/4-D)/(2*t*t)),t,0,7).removeO()
eps=s.expand(1+T/2-root)
c3t=s.expand(eps).coeff(t,3)*2**s.Rational(3,2)
c5t=s.expand(eps).coeff(t,5)*2**s.Rational(5,2)
c7t=s.expand(eps).coeff(t,7)*2**s.Rational(7,2)
assert s.simplify(c7t-(4*Dt4-Tr3-Tr2**2+c3t*c5t/2))==0
assert Tr4 not in c7t.free_symbols
pi_form=s.expand(C7.subs({z2:s.pi**2/6,z4:s.pi**4/90,z6:s.pi**6/945}))
val=C7.subs({z2:s.zeta(2),z3:s.zeta(3),z4:s.zeta(4),z5:s.zeta(5),z6:s.zeta(6)})
result={'status':'PASS','C7_to_D4_residual':str(remainder),'direct_characteristic_polynomial_check':True,'T4_not_required':True,'C7_pi_form':str(pi_form),'C7_decimal':str(s.N(val,80)),'D4_decimal':str(s.N(D4.subs({z2:s.zeta(2),z3:s.zeta(3),z4:s.zeta(4),z5:s.zeta(5),z6:s.zeta(6)}),80))}
(r/'verification/thermal_algebra_report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
