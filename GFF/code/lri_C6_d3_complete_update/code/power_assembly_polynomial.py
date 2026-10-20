import sympy as s,json
from pathlib import Path
W=Path(__file__).resolve().parents[1]
A,R,M,N,Q,P,U,V=s.symbols('A R M N Q P U V');r=s.Rational
b3=6*Q+r(87,4)*A*A-r(9,4)*R+M;c3=r(7,2)*A*A-R/2+M/3
b4=-r(393,4)*A**3-r(11,2)*A*M-54*A*Q+r(117,4)*A*R-r(3,2)*M*N-6*P-r(165,8)*U+r(9,4)*V
c4=-r(127,8)*A**3-r(7,6)*A*M-3*A*Q+r(51,8)*A*R-M*N/2-r(57,16)*U+r(3,8)*V
bp3=M;cp3=M/3;bp4=-r(11,2)*A*M-r(3,2)*M*N;cp4=-r(7,6)*A*M-M*N/2
def L(b3,c3,b4,c4):return 2016*A**5-448*A**3*b3+672*A**3*c3-84*A*A*b4+168*A*A*c4+r(49,3)*A*b3*b3-42*A*b3*c3+r(7,3)*b3*b4-4*b3*c4-3*b4*c3
D=s.expand(L(b3,c3,b4,c4)-L(b3-bp3,c3-cp3,b4-bp4,c4-cp4))
print(s.factor(D));print(s.latex(D))
(W/'records/power_assembly_polynomial.json').write_text(json.dumps({'delta_lower_R':str(D),'delta_lower_R_tex':s.latex(D),'predicted_higher_power_combination':str(-D),'b3_power':str(bp3),'c3_power':str(cp3),'b4_power':str(bp4),'c4_power':str(cp4),'scope':'Exact assembly algebra, not by itself a graph-level proof of the higher-power identity.'},indent=2))
