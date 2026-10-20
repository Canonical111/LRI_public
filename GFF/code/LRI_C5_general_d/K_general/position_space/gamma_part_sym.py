#!/usr/bin/env python3
"""Exact Laurent coefficients [t^0],[t^1],[t^2] of J_pole(t) - J^Gamma(t) in terms of polygammas at 1, q, 2q.
   J_pole = G(2q) G(t/2)^2 G(q-t/2)^4 / (G(q)^4 G(2q-t)) ;  J^Gamma = V^2 + (2/t)(V - W),
   V = B_d(d/2, d-t) = G(2q)G(t/2)G(q-t/2)/(G(2q-t/2)G(q+t/2)),  W = B_d(d/2+2t, d-t) = G(2q)G(q-t)G(t/2)G(q+t/2)/(G(q+t)G(2q-t/2)G(q-t/2))."""
import sympy as sp
t = sp.symbols('t')
K = 6
P1 = sp.symbols('p1_0:%d' % K)   # psi_k(1)
Pq = sp.symbols('pq_0:%d' % K)   # psi_k(q)
P2 = sp.symbols('p2q_0:%d' % K)  # psi_k(2q)
def lgser(P, x):  # log Gamma(a + x) - log Gamma(a) as series in x (x a polynomial in t), through t^K
    return sum(P[k - 1] * x ** k / sp.factorial(k) for k in range(1, K))
def trunc(e, n=K):
    e = sp.expand(e)
    return sum(e.coeff(t, k) * t ** k for k in range(0, n))
def expser(L):
    L = trunc(L); out = sp.Integer(1); term = sp.Integer(1)
    for k in range(1, K):
        term = trunc(term * L / k); out += term
    return trunc(out)
# Gamma(1+t/2) via psi_k(1)
g1 = lgser(P1, t / 2)
# t^2 J_pole / 4 = exp(2 g1 + 4[lnG(q - t/2)-lnG(q)] - [lnG(2q - t) - lnG(2q)])
Lp = 2 * g1 + 4 * lgser(Pq, -t / 2) - lgser(P2, -t)
Jp_t2 = 4 * expser(Lp)                         # = t^2 J_pole
# t V / 2 = exp(g1 - [lnG(2q - t/2) - lnG(2q)] + [lnG(q - t/2) - lnG(q + t/2)])
Lv = g1 - lgser(P2, -t / 2) + lgser(Pq, -t / 2) - lgser(Pq, t / 2)
Lw = g1 - lgser(P2, -t / 2) + lgser(Pq, -t) + lgser(Pq, t / 2) - lgser(Pq, t) - lgser(Pq, -t / 2)
tV = 2 * expser(Lv); tW = 2 * expser(Lw)       # t V, t W
# t^2 J^Gamma = (tV)^2 + 2 (tV - tW)   [since (2/t)(V-W) t^2 = 2 t (V - W) = 2 (tV - tW)]
JG_t2 = trunc(tV ** 2 + 2 * (tV - tW))
D = trunc(Jp_t2 - JG_t2)
for k in range(0, 5):
    print('[t^%d](J_pole - J^Gamma) =' % (k - 2), sp.simplify(D.coeff(t, k)))
import pickle
pickle.dump({k - 2: D.coeff(t, k) for k in range(5)}, open('gamma_part_sym.pkl', 'wb'))
