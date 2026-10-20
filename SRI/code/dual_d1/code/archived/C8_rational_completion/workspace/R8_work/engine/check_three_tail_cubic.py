"""Independent one-variable computation of the inherited rational W input.
Two reflected A3 faces; the Z2 third-tail single log vanishes.
"""
import tail_boundary as b
from math import factorial
from fractions import Fraction as R
from pathlib import Path
import json
F=b.F
# Third derivative: S4/2+2 S2 S3+S2^3; S_j=L^j-K^j.
terms={(4,0):R(1,2),(0,4):R(-1,2),
       (5,0):R(2),(2,3):R(-2),(3,2):R(-2),(0,5):R(2),
       (6,0):R(1),(4,2):R(-3),(2,4):R(3),(0,6):R(-1)}
num=tuple(map(F,[4,4,1]));den=((F(-1),2),);v=F(0);contributions=[]
for (a,c),co in terms.items():
 H=b.mt.canon((tuple((F(0),F(-2)) for _ in range(a)),tuple((F(0),F(-1)) for _ in range(c))))
 z=b.functional(num,den,H,0,2,0,0)-2*b.functional(num,den,H,1,2,0,0)-b.functional((F(0),)+num,den,H,1,2,0,0)
 z*=F(co.numerator,co.denominator)*factorial(a)*factorial(c);v+=z
 contributions.append({'L_power':a,'K_power':c,'weighted_boundary_constant':str(z)})
a3=-2*v;W=a3/6+4
prior=json.loads((b.ROOT/'prior_inputs/new_six_checkpoint.json').read_text())['coefficients']['W'];assert str(W)==prior
out={'status':'new_independent_cubic_tail_check','A3_third_tail_single_log':str(a3),'Z2_third_tail_single_log':'0','W':str(W),'prior_W':prior,'exact_equal':True,'contributions':contributions,'C8_conjecture_used':False}
(b.ROOT/'three_tail_cubic_check.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
