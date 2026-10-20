"""Cross-check of the note's done:kiteFactorization (d=2 KLT bilinear formula) against the general-index MB at a generic point."""
import numpy as np, itertools, mpmath as mp
from scipy.optimize import linprog
from kite_general import mb_value
rng = np.random.default_rng(5)
d = 2.0; h = 1.0
cands = []
for it in range(300000):
    n1, n2, n3, a3, a4 = np.round(rng.uniform(0.1, 0.95, 5), 3)
    lam = n1 + n2 + n3 - h
    A = [[1, 0, 1], [1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, 1, 1], [0, -1, 1], [-1, -1, 1], [-1, -1, 1], [1, 1, 1]]
    b = [0, n2 - lam, -(a3 - h), 0, n1 - lam, -(a4 - h), lam, n3, a3 + a4 - h]
    res = linprog([0, 0, -1], A_ub=A, b_ub=b, bounds=[(None, None), (None, None), (None, 1)])
    if res.status == 0 and -res.fun > 0.12:
        gen = min(abs(x - round(x)) for x in [n1 - lam, n2 - lam, n3 - lam, a3 + a4 - h, n1, n2, n3, a3, a4])
        if gen > 0.05: cands.append((-res.fun, (n1, n2, n3, a3, a4), res.x[:2]))
cands.sort(key=lambda x: -x[0])
delta, (n1, n2, n3, a3, a4), (c1, c2) = cands[0]
print('point: nu=(%g,%g,%g) a3,a4=(%g,%g) contour (%.4f,%.4f) delta %.3f' % (n1, n2, n3, a3, a4, c1, c2, delta))
v, info = mb_value('2', repr(n1), repr(n2), repr(n3), repr(a3), repr(a4), repr(c1), repr(c2), digits=25)
print('MB  J_2 =', v.real.str(22))
# note's formula: p1=|x| exponent = 2 nu1 (star x), p2 = 2 nu2, p5 = 2 nu3, p3 = |y| = 2 a3, p4 = |1-y| = 2 a4
mp.mp.dps = 30
p = [2 * mp.mpf(repr(n1)), 2 * mp.mpf(repr(n2)), 2 * mp.mpf(repr(a3)), 2 * mp.mpf(repr(a4)), 2 * mp.mpf(repr(n3))]
a, b, Ap, Bp, c = [-x / 2 for x in p]
B = mp.beta
def O(a, b, Ap, Bp, c):
    return B(a + 1, c + 1) * B(a + Ap + c + 2, Bp + 1) * mp.hyp3f2(-b, a + 1, a + Ap + c + 2, a + c + 2, a + Ap + Bp + c + 3, 1)
def Mf(a, b, Ap, Bp, c):
    return B(a + 1, -a - b - c - 1) * B(Bp + 1, -Ap - Bp - c - 1) * mp.hyp3f2(-c, a + 1, Bp + 1, -b - c, -Ap - c, 1)
S = mp.sin
val = (S(mp.pi * a) * S(mp.pi * Bp) * O(a, b, Ap, Bp, c) * Mf(a, b, Ap, Bp, c) + S(mp.pi * Ap) * S(mp.pi * b) * O(Ap, Bp, a, b, c) * Mf(Ap, Bp, a, b, c)) / mp.pi ** 2
print('KLT J_2 =', mp.nstr(val, 22))
