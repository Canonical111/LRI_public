"""Exact checks of the RG conversion and constrained all-order ansatz.

This does not compute new RG invariants beyond the archived order.
It verifies the organizing formulas and the Gamma-product obstruction.
"""
from pathlib import Path
import json
import sympy as s
root=Path(__file__).resolve().parent
x,t,d=s.symbols('x t delta')
Z2,Z3,Z4,Z5,Z6=s.symbols('Z2 Z3 Z4 Z5 Z6')
D4,T4=s.symbols('D4 T4')
C3=s.Rational(39,16)+2*Z2
C4=4-4*Z2-8*Z3
C5=s.Rational(11249,1024)-s.Rational(361,16)*Z2+24*Z3+s.Rational(49,2)*Z4
C6=26-38*Z2+104*Z3-80*Z4-272*Z5+112*Z2*Z3
T={1:s.Rational(1,2),2:C4/2,3:C6/4,4:T4}
D={1:-2,2:s.Rational(5,2)+2*Z2,3:s.Rational(21,4)-13*Z2+11*Z3+11*Z4,4:D4}
def reduce_even(expr):
    return s.expand(s.expand(expr).subs({Z2**3:s.Rational(35,8)*Z6,Z2*Z4:s.Rational(7,4)*Z6,Z2**2:s.Rational(5,2)*Z4}))
q={};sq={0:s.Integer(1)}
for m in range(1,4):
    q[m]=s.expand(sum(T[i]*T[m+1-i] for i in range(1,m+1))/8-D[m+1]/2)
    sq[m]=s.expand((q[m]-sum(sq[i]*sq[m-i] for i in range(1,m)))/2)
cs={1:-2,2:T[1],3:reduce_even(-4*sq[1]),4:2*T[2],5:reduce_even(-8*sq[2]),6:4*T[3],7:reduce_even(-16*sq[3])}
assert reduce_even(cs[3]-C3)==0
assert reduce_even(cs[5]-C5)==0
C7formula=4*D4-T[3]-T[2]**2+C3*C5/2
assert reduce_even(cs[7]-C7formula)==0
# Check the recurrence directly by squaring, without taking symbolic roots.
Q=1+sum(q[m]*d**m for m in q)
S=sum(sq[m]*d**m for m in sq)
assert all(s.expand(S*S-Q).coeff(d,m)==0 for m in range(4))
# Normalize 1-Delta and expand logarithm by its finite polynomial formula.
F=1-t/4-C3*t**2/2-C4*t**3/2-C5*t**4/2-C6*t**5/2
L=s.expand(sum((-1)**(k+1)*(F-1)**k/s.Integer(k) for k in range(1,6)))
logcoef={n:reduce_even(L.coeff(t,n)) for n in range(1,6)}
assert s.expand(logcoef[5]).coeff(Z2,1).coeff(Z3,1)==-52
assert s.expand(logcoef[5]).coeff(Z5,1)==136
# Inverse single-variable Gamma ansatz check, using Lagrange inversion.
# For y=1-Delta=2t F(t), log(4*x/y^2) at order y^5 equals
# (2/(5*2^5))*[t^5]F(t)^(-5). Only the finite binomial expansion is needed.
inv=s.expand(sum(s.binomial(-5,k)*(F-1)**k for k in range(6)))
invlog5=reduce_even(s.Rational(1,80)*inv.coeff(t,5))
assert invlog5.coeff(Z2,1).coeff(Z3,1)==2
report={'status':'all exact structural checks passed','C6':str(C6),
 'C7_formula':str(C7formula),'C7_known_part':str(reduce_even(C7formula-4*D4)),
 'log_normalized_series':{str(n):str(v) for n,v in logcoef.items()},
 'highest_weight_log_order_five':str(136*Z5-52*Z2*Z3),
 'inverse_log_order_five':str(invlog5),
 'new_RG_invariants_evaluated':False}
(root/'all_orders_checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
