"""Explicit quadratic form of the rotated region sum:
   I = -(1/4) sum_{R,R'} e^{i pi phi(R,R')} A(R)A(R'),  A(R) = 2 I_{j(R)},
with e^{i pi phi} = (-i)^n (-q)^m, q = e^{i pi tau}, n = number of exponent-(-1/2) factors whose sign differs
between R and R', m = 1 if the sign of 1-y differs.  Then reduction by the moment relations."""
import sympy as sp
from region_sum import regions
q, s, c = sp.symbols('q s c')
I = sp.symbols('I1:7')
expo_half = [0, 1, 2, 4]          # factors x, 1-x, y, y-x carry exponent -1/2;  factor 3 (1-y) carries -1+tau
M = sp.zeros(6, 6)
for k1, (s1, j1) in regions.items():
    for k2, (s2, j2) in regions.items():
        n = sum(1 for f in expo_half if s1[f] != s2[f])
        m = 1 if s1[3] != s2[3] else 0
        M[j1-1, j2-1] += sp.Rational(-1, 4)*4*(-sp.I)**n*(-q)**m
M = M.applyfunc(sp.expand)
print('M (I = sum_jk M_jk I_j I_k), rows/cols I1..I6:')
for i in range(6):
    print('  ', [M[i, j] for j in range(6)])
Q = sp.expand(sum(M[i, j]*I[i]*I[j] for i in range(6) for j in range(6)))
print('I =', sp.collect(Q, [I[0]*I[1], I[0]*I[2]]))
# reduce: q = c + i s, with the moment relations
red = Q.subs({I[0]: c*I[2]+s*I[3], I[4]: s*I[2]-c*I[3], I[1]: s*I[2], I[5]: s*I[3]}).subs(q, c+sp.I*s)
red = sp.expand(red)
red = sp.expand(red.subs(c**2, 1-s**2))
red = sp.expand(red.subs(c**3, c*(1-s**2)))
print('after moment relations and c^2 = 1 - s^2:  I =', sp.factor(red))
