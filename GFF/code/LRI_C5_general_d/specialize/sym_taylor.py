#!/usr/bin/env python3
"""Pole-node Taylor form (exact algebra): with r-1 Fourier modes, W_r needs only Xi^{(k)}(0), k <= r-2,
and these come from the right half-lattice alone (the left and middle parts vanish to order r at t = 0).
Writes the weights omega_k(theta) of  W_r = (N_b^r-free) sum_k omega_k Xi^{(k)}(0),  theta = pi b/2,
and the Laurent-weight polynomials G_r(lambda) with  W_r = sum_{l,n} d_l T_ln^r G_r  (b = d/2: compare the note's
F_3, F_4 of gs:Fpolys).  Conventions: Xi(t) = sum_k c_k cos(2 pi k (t + b/4)); W_3, W_4 functionals of the foundation.
"""
import sympy as sp

th, pi = sp.symbols('theta', positive=True), sp.pi
c = sp.symbols('c0:3')
s, cs = sp.sin(th), sp.cos(th)
X = sp.symbols('X0:3')   # Xi(0), Xi'(0), Xi''(0)


def modes_from_taylor(r):
    t = sp.symbols('t')
    xi = sum(c[k] * sp.cos(2 * pi * k * t + k * th) for k in range(r - 1))
    eqs = [sp.Eq(sp.diff(xi, t, k).subs(t, 0), X[k]) for k in range(r - 1)]
    sol = sp.solve(eqs, c[:r - 1], dict=True)[0]
    return sol


def functional(r):
    if r == 3:
        return -2 / (pi * s ** 5) * ((1 + 2 * cs ** 2) * c[0] + 3 * cs * c[1])
    return 4 / (pi * s ** 7) * (cs * (3 + 2 * cs ** 2) * c[0] + (1 + 4 * cs ** 2) * c[1] + 5 * cs * c[2])


out = {}
for r in (3, 4):
    sol = modes_from_taylor(r)
    W = sp.simplify(functional(r).subs(sol))
    om = [sp.simplify(sp.diff(W, X[k])) for k in range(r - 1)]
    out[r] = om
    print('r=%d  W_r = sum_k omega_k Xi^(k)(0)  (times N_b^r):' % r)
    for k, o in enumerate(om):
        print('   omega_%d =' % k, sp.simplify(sp.trigsimp(o)))
# Laurent translation: N^r Xi(u) = (-1)^r (pi s)^r sum d T^r exp(r sum Lambda_m u^m/m!) + O(u^r),
# Lambda_1 = lambda_1 + kappa, Lambda_2 = lambda_2 - 4 pi^2/3 - kappa^2, kappa = pi cot(theta)
l1, l2 = sp.symbols('lambda1 lambda2')
kap = pi * sp.cos(th) / sp.sin(th)
L1, L2 = l1 + kap, l2 - 4 * pi ** 2 / 3 - kap ** 2
for r in (3, 4):
    E = [1, r * L1, (r * L1) ** 2 + r * L2]
    G = (-1) ** r * (pi * s) ** r * sum(out[r][k] * E[k] for k in range(r - 1))
    G = sp.expand(sp.simplify(sp.expand_trig(G)))
    print('r=%d  W_r = sum d_l T_ln^r G_r,  G_r =' % r, sp.simplify(G))
    print('       collected in lambda:', sp.collect(sp.expand(sp.simplify(G)), [l1, l2]))
