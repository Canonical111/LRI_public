#!/usr/bin/env python3
"""d=3 (q=3/4) half-shift structure of the R-family sample:
   Xi(t) + Xi(t+1/2) = -(Gamma(3/2)^2/4) cos^3(2 pi t) [ S_o^1 S_e^0 - S_o^0 S_e^1 ],
   S_e^k = sum_{n in Z} (n+u_e)^k Phi1(n+u_e), u_e = t+1/8;  S_o^k: u_o = t+5/8;
   Phi1(w) = G(w+1/8)^3 / [G(w+7/8)^2 G(w+1/8+tau)].            (strip 1/2 < tau < 9/8)
Bilateral sums by model subtraction: sum_{n>=0} (n+c)^k Gamma(n+al)/n! = 0 (k=0,1; Re al < -k), so only the
remainders delta X are summed (fast).  Also prints the observed c_{+-2} = 0 (t-independence of the left side)."""
import mpmath as mp
import rblocks as rb
mp.mp.dps = 40
e8 = mp.mpf(1) / 8

def half_sum(ups, downs, shift, k, tau, K=24, M=400):
    """sum_{n>=0} (n+shift)^k X(n), X = prod(u)_n/prod(v)_n ~ n^{a-1}, a = -1/2-tau"""
    a = -mp.mpf(1) / 2 - tau
    X = rb.poch_seq(ups, downs, M); x = rb.model_coeffs(ups, downs, a, K); B = rb.basis_seq(a, K, M)
    dX = rb.delta_seq(X, x, B, M)
    return mp.fsum((n + shift) ** k * dX[n] for n in range(M + 1))

def bilat(u, k, tau):
    G, rG, pi, sin = mp.gamma, mp.rgamma, mp.pi, mp.sin
    Phi1u = G(u + e8) ** 3 * rG(u + 7 * e8) ** 2 * rG(u + e8 + tau)
    right = Phi1u * half_sum([u + e8] * 3, [u + 7 * e8] * 2 + [u + e8 + tau], u, k, tau)
    T1 = sin(pi * (u + 7 * e8)) ** 2 * sin(pi * (u + e8 + tau)) / sin(pi * (u + e8)) ** 3
    Y0 = G(9 * e8 - u) ** 2 * G(15 * e8 - u - tau) * rG(15 * e8 - u) ** 3
    left = T1 * Y0 * (-1) ** k * half_sum([9 * e8 - u] * 2 + [15 * e8 - u - tau], [15 * e8 - u] * 3, 1 - u, k, tau)
    return right + left

q = mp.mpf(3) / 4
for tau in (mp.mpf('0.8'), mp.mpf('0.65')):
    for t in (mp.mpf('0.0917'), mp.mpf('0.2311'), mp.mpf('0.37')):
        lhs = rb.sample(q, t, tau, 24, 300) + rb.sample(q, t + mp.mpf(1) / 2, tau, 24, 300)
        ue, uo = t + e8, t + 5 * e8
        det = bilat(uo, 1, tau) * bilat(ue, 0, tau) - bilat(uo, 0, tau) * bilat(ue, 1, tau)
        rhs = -(mp.pi / 4) / 4 * mp.cos(2 * mp.pi * t) ** 3 * det
        print('tau', tau, 't', t, 'Xi(t)+Xi(t+1/2) =', mp.nstr(mp.re(lhs), 30), ' determinant form =', mp.nstr(rhs, 30), ' diff', mp.nstr(abs(lhs - rhs), 3), flush=True)
