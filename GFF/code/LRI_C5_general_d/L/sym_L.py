#!/usr/bin/env python3
"""Explicit coefficients of the five-Horn formula for P4(d) and L_d (session L).

W_4(d;b) = a_x hx + a_1 h1 + a_h hh + b_0 s0 + b_h s1   (normalized Horn functions of L_general.py), with
   a_x = -4 pi^3 c/s^3,
   b_0 = 2 (1+c)^2 (1+2c) k0^4/(pi s^7),   a_1 = 2 rho0^4 b_0,
   b_h = -2 (1-c)^2 (1-2c) kh^4/(pi s^7),  a_h = 2 rhoh^4 b_h,
   s = sin(pi b/2), c = cos(pi b/2), x = b/4, y = d/2 - b/4, N = Gamma(d/2)Gamma(y-x)/Gamma(2x),
   k0 = N sin^2(pi x) Gamma(x)^2/Gamma(y)^2,   rho0 = x(1-y)/(y(1-x)),
   kh = N cos^2(pi x) Gamma(1/2+x)^2/Gamma(1/2+y)^2,   rhoh = (1-2y)/(1-2x).
L_d = sum_i [a_i' f_i + a_i f_i'] at b = d/2.  This script derives a_i and a_i' (sympy, exact) and evaluates the
explicit formula numerically from separately computed f_i, f_i' (L_general.inventory), as a check of the algebra.
"""
import sys
import os
import sympy as sp
import mpmath as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

b, d = sp.symbols('b d', positive=True)
pi = sp.pi
x = b / 4
y = d / 2 - b / 4
s = sp.sin(pi * b / 2)
c = sp.cos(pi * b / 2)
N = sp.gamma(d / 2) * sp.gamma(y - x) / sp.gamma(2 * x)
k0 = N * sp.sin(pi * x) ** 2 * sp.gamma(x) ** 2 / sp.gamma(y) ** 2
kh = N * sp.cos(pi * x) ** 2 * sp.gamma(sp.Rational(1, 2) + x) ** 2 / sp.gamma(sp.Rational(1, 2) + y) ** 2
rho0 = x * (1 - y) / (y * (1 - x))
rhoh = (1 - 2 * y) / (1 - 2 * x)
coef = dict(
    hx=-4 * pi ** 3 * c / s ** 3,
    s0=2 * (1 + c) ** 2 * (1 + 2 * c) * k0 ** 4 / (pi * s ** 7),
    s1=-2 * (1 - c) ** 2 * (1 - 2 * c) * kh ** 4 / (pi * s ** 7),
)
coef['h1'] = 2 * rho0 ** 4 * coef['s0']
coef['hh'] = 2 * rhoh ** 4 * coef['s1']
ORDER = ('hx', 'h1', 'hh', 's0', 's1')


def coeffs_at(dval, dps=30):
    """numeric (a_i, a_i') at b = d/2."""
    out = {}
    with mp.workdps(dps + 10):
        for k in ORDER:
            e = coef[k]
            de = sp.diff(e, b)
            f0 = sp.lambdify((b, d), e, 'mpmath')
            f1 = sp.lambdify((b, d), de, 'mpmath')
            dv = mp.mpmathify(dval)
            out[k] = (f0(dv / 2, dv), f1(dv / 2, dv))
    return out


def logderivs_symbolic():
    """d log a_i/db at b = d/2, simplified (for the write-up)."""
    q = sp.symbols('q', positive=True)
    res = {}
    for k in ORDER:
        if k == 'hx':
            res[k] = sp.simplify(sp.diff(coef[k], b).subs(b, d / 2).subs(d, 4 * q))
            continue
        lg = sp.expand_log(sp.log(coef[k] if k in ('s0', 'h1') else -coef[k]), force=True)
        dl = sp.diff(lg, b).subs(b, d / 2).subs(d, 4 * q)
        res[k] = sp.simplify(dl)
    return res


if __name__ == '__main__':
    from L_general import inventory, LP4
    dv = sys.argv[1] if len(sys.argv) > 1 else '1.5'
    dps = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    mp.mp.dps = dps
    dd = mp.mpmathify(dv)
    inv = inventory(dd, dps)
    cf = coeffs_at(dd, dps)
    with mp.workdps(dps + 10):
        P4 = mp.fsum(cf[k][0] * inv[k][0] for k in ORDER)
        L = mp.fsum(cf[k][1] * inv[k][0] + cf[k][0] * inv[k][1] for k in ORDER)
    P4j, Lj = LP4(dd, dps)
    print('d =', dv)
    for k in ORDER:
        print('  %-3s  f = %s   f\' = %s   a = %s   a\' = %s' % (k, mp.nstr(mp.re(inv[k][0]), 20), mp.nstr(mp.re(inv[k][1]), 20),
                                                        mp.nstr(cf[k][0], 15), mp.nstr(cf[k][1], 15)))
    print('  explicit P4 =', mp.nstr(mp.re(P4), dps), '  jet P4 =', mp.nstr(mp.re(P4j), dps), '  diff', mp.nstr(abs(P4 - P4j), 3))
    print('  explicit L  =', mp.nstr(mp.re(L), dps), '  jet L  =', mp.nstr(mp.re(Lj), dps), '  diff', mp.nstr(abs(L - Lj), 3))
    if len(sys.argv) > 3:
        for k, v in logderivs_symbolic().items():
            print('  dlog a_%s/db at b=d/2 (d=4q):' % k, v)
