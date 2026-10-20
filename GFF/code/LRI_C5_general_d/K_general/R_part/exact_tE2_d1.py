#!/usr/bin/env python3
"""Exact <t^2 E_2>_1 = [tau^1] (J_{2tau} - C^2 X^4) at d=1 from eq:KproofTwoFunctions (F,G Taylor data u, sigma)."""
import sympy as sp
tau, u, v, sig, w = sp.symbols('tau u v sigma w')
pi = sp.pi
t = 2 * tau
order = 4
ser = lambda e: sp.series(e, tau, 0, order).removeO()
Fh = 1 + u * t + v * t**2
Gh = 1 + sig * t**3 + w * t**4
J = 2*pi*(1 + sp.cos(pi*t) + 2*sp.sin(pi*t)) * sp.gamma(t)**2 / sp.gamma(sp.Rational(1, 2) + t)**2 * Gh + 2*pi**2*(2 + sp.tan(pi*t/2)) * Fh
C = sp.sqrt(pi) * sp.gamma(tau) / sp.gamma(sp.Rational(1, 2) - tau)
X = sp.gamma(sp.Rational(1, 4) - tau/2) / sp.gamma(sp.Rational(1, 4) + tau/2)
F = sp.expand(ser(J) - ser(C**2 * X**4))
for k in (-2, -1, 0, 1):
    ck = sp.simplify(F.coeff(tau, k))
    print(k, ck)
G = sp.Catalan
D2 = sp.simplify(F.coeff(tau, 1).subs({u: 4*sp.log(2) - 8*G/pi, sig: 8*pi*G - 14*sp.zeta(3)}))
print('D2 =', D2, '=', sp.N(D2, 40))
