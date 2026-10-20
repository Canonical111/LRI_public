"""Exact cancellation of two genuinely unknown finite core coefficients.
The raw core is NOT evaluated and is NOT set to zero in the physical target.
"""
import sympy as s,json
from pathlib import Path
W=Path(__file__).resolve().parents[1]
A,F0,F1=s.symbols('A F0 F1')
# Known pole terms are deliberately left out: they are evaluated separately.
# B_d(d-5z,d/2-z/2)=2/(5z)+A+O(z)
# B_d(d-z,d/2-9z/2)=2/z+A+O(z).
r5=s.Rational(2,5)*F0
r6a=s.Rational(1,3)*(s.Rational(2,5)*F1+A*F0)
r6b=s.Rational(1,3)*(2*F1+A*F0)-s.Rational(4,5)*F1
physical=s.expand(s.Rational(9,2)*(r6a+r6b)-s.Rational(15,2)*A*r5)
# Independently derive the displayed weights, including the odd/even loop signs.
w5=s.Rational(3,4);v5=s.Rational(1,4)
w6=s.Rational(3,2);v6=s.Rational(1,4)
assert (-1)**7*6*(3*v6-w6)==s.Rational(9,2)
assert (-1)**6*5*(-12*A*w5+30*A*v5)==-s.Rational(15,2)*A
assert physical==0
out={'five_loop_graph':'L5G086','six_loop_graphs':['L6G332','L6G333'],'definition_F':'renormalization-unsubtracted four-loop two-terminal core times its two external chain convolutions','r5_unknown':str(r5),'r6_332_unknown':str(r6a),'r6_333_unknown':str(r6b),'physical_unknown_combination':str(physical),'coefficient_F0':str(s.expand(physical).coeff(F0)),'coefficient_F1':str(s.expand(physical).coeff(F1)),'status':'exact rational-polynomial identity','scope':'This eliminates unknown finite and linear core jets, not the known pole terms of the core or other power graphs.'}
(W/'records/unknown_core_cancellation.json').write_text(json.dumps(out,indent=2));print(out)
