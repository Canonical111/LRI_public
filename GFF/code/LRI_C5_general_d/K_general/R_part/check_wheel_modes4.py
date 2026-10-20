#!/usr/bin/env python3
"""Control: r=3,4 balanced wheels at generic d: Fourier coefficients of the spin-summed sample (|k| <= r-1 by growth)."""
import mpmath as mp
import rblocks as rb
mp.mp.dps = 40
def wheel_sample(q, t, r, K=20, M=220):
    a = 1 - r * q
    d = rb.dlist(q, 2 * M + 2)
    Phi = ([q + t] * r, [2 * q + t] * r); Psi = ([1 - q + t] * r, [1 + t] * r)
    PsiM = ([1 - t] * r, [1 + q - t] * r); PhiL = ([2 - 2 * q - t] * r, [2 - q - t] * r)
    HR, _ = rb.block_toeplitz(Phi, Psi, q, a, K, M, d)
    HM, _ = rb.block_middle(Phi, PsiM, q, a, K, M, d)
    HL, _ = rb.block_toeplitz(PsiM, PhiL, q, a, K, M, d)
    G, rG = mp.gamma, mp.rgamma
    P0 = (G(q + t) * rG(2 * q + t)) ** r; Q0 = (G(-t) * rG(q - t)) ** r
    Pm = (G(q - 1 + t) * rG(2 * q - 1 + t)) ** r; Qm = (G(1 - t) * rG(1 + q - t)) ** r
    D = mp.sin(mp.pi * t) ** r * mp.sin(mp.pi * (t + q)) ** r
    return D * G(2 * q) ** r * (P0 * Q0 * HR + P0 * Qm * HM + Pm * Qm * HL)
for r in (3, 4):
    kmax = r - 1
    for ds in ('2.5', '1.25', '3'):
        q = mp.mpf(ds) / 4
        n = 2 * kmax + 1
        nodes = [mp.mpf('0.0917') + mp.mpf(j) / n for j in range(n)]
        vals = [wheel_sample(q, t, r) for t in nodes]
        Mx = mp.matrix([[mp.expj(2 * mp.pi * k * t) for k in range(-kmax, kmax + 1)] for t in nodes])
        c = mp.lu_solve(Mx, mp.matrix(vals))
        print('r', r, 'd', ds, '|c_k| k=-%d..%d:' % (kmax, kmax), [mp.nstr(abs(c[i]), 6) for i in range(n)], flush=True)
