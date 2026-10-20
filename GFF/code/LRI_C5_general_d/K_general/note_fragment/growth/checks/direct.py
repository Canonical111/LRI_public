#!/usr/bin/env python3
"""Independent direct evaluator of the R-family periodization and its three parts (ball arithmetic).

  S_R(t) = Gamma(2q)^2 sum_{l>=0} d_l sum_{n in Z} Phi_t(l+n) Psi_t(n)          (PROOF.md eq. (1.4))
  Phi_t(m) = G(m+q+t)^3 / [G(m+2q+t)^2 G(m+q+tau+t)],   Psi_t(n) = G(-n-t)^2 G(q-tau-n-t) / G(q-n-t)^3,
  right  = n >= 0,   middle = -l <= n <= -1,   left = n <= -l-1      (m = l+n).
Truncation |m|, |n| <= N; the neglected tail is O(N^{-eta}) relative (eta = 2 Re tau - max(0,1-4q)), so this
is accurate only for large Re tau (used for Re tau >= 2 here).  Convolutions in m are done with arb_poly
products (exact in ball arithmetic).  Shares no code with R_part/rblocks.py.
"""
from flint import arb, acb, arb_poly, acb_poly, ctx


def dl(q, L):
    """d_0..d_L from (1+z)(1-z)^{1-4q}: d_j = e_j + e_{j-1}, e_j = (4q-1)_j/j!"""
    e = [arb(1)]
    for j in range(L):
        e.append(e[-1] * (4 * q - 1 + j) / (j + 1))
    return [e[0]] + [e[j] + e[j - 1] for j in range(1, L + 1)]


def two_sided(x0, ratio, N):
    """x[m], m = -N..N, from x[0] and ratio(m) = x[m+1]/x[m]; returned as list indexed i = m + N"""
    pos = [x0]
    for m in range(N):
        pos.append(pos[-1] * ratio(m))
    neg = [x0]
    for m in range(-1, -N - 1, -1):
        neg.append(neg[-1] / ratio(m))
    return neg[::-1][:-1] + pos


def parts(q, tau, t, N, d=None):
    """returns dict(right, middle, left, S) as acb; q real arb, tau and t acb"""
    G = lambda z: z.gamma()
    Phi0 = G(q + t) ** 3 / (G(2 * q + t) ** 2 * G(q + tau + t))
    Psi0 = G(-t) ** 2 * G(q - tau - t) / G(q - t) ** 3
    rPhi = lambda m: (m + q + t) ** 3 / ((m + 2 * q + t) ** 2 * (m + q + tau + t))
    rPsi = lambda n: (q - n - 1 - t) ** 3 / ((-n - 1 - t) ** 2 * (q - tau - n - 1 - t))
    Phi = two_sided(Phi0, rPhi, N)   # index m + N
    Psi = two_sided(Psi0, rPsi, N)
    if d is None:
        d = dl(q, 2 * N + 1)
    D = acb_poly([acb(x) for x in d[:2 * N + 1]])
    Pplus = (D * acb_poly(Psi[N:])).coeffs()          # coeff m: sum_{0<=n<=m} d_{m-n} Psi(n)
    Pminus = (D * acb_poly(Psi[:N])).coeffs()         # coeff m+N: sum_{-N<=n<=min(m,-1)} d_{m-n} Psi(n)
    g2 = arb(2 * q).gamma() ** 2
    right = sum((Phi[N + m] * Pplus[m] for m in range(N + 1)), acb(0))
    middle = sum((Phi[N + m] * Pminus[m + N] for m in range(N + 1)), acb(0))
    left = sum((Phi[N + m] * Pminus[m + N] for m in range(-N, 0)), acb(0))
    return dict(right=g2 * right, middle=g2 * middle, left=g2 * left, S=g2 * (right + middle + left))


def DR(q, tau, t):
    pi = arb.pi()
    return (pi * t).sin() ** 2 * (pi * (t + q)).sin() ** 3 * (pi * (t - q + tau)).sin()


if __name__ == '__main__':
    import sys, time
    ctx.prec = 300
    q = arb(sys.argv[1]) / 4
    tau = acb(arb(sys.argv[2]), arb(sys.argv[3]) if len(sys.argv) > 3 else 0)
    for N in (1000, 2000):
        st = time.time()
        p = parts(q, tau, acb(arb('0.13'), arb('1.5')), N)
        print('N', N, {k: v.str(12, radius=False) for k, v in p.items()}, '%.1fs' % (time.time() - st))
