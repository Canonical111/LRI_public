#!/usr/bin/env python3
"""Control experiment: the r=3 balanced wheel at generic d with the same block machinery.
Does the spin-summed sample Xi_3(t) = D_w(t) sum_l d_l sum_n g_l(a_l+n+t)^3 also lose its top modes |k|=2 (as the
R-family does), or is that special to the R-deformation?   D_w = sin^3(pi t) sin^3(pi(t+q)), modes |k|<=2 (fp).
Also checks W_3 = 3Q_d against the reference via the residue functional (pole of order 3 at t=0)."""
import mpmath as mp
import rblocks as rb
mp.mp.dps = 40
def wheel_sample(q, t, K=20, M=220):
    a = 1 - 3 * q
    d = rb.dlist(q, 2 * M + 2)
    Phi = ([q + t] * 3, [2 * q + t] * 3); Psi = ([1 - q + t] * 3, [1 + t] * 3)
    PsiM = ([1 - t] * 3, [1 + q - t] * 3); PhiL = ([2 - 2 * q - t] * 3, [2 - q - t] * 3)
    HR, _ = rb.block_toeplitz(Phi, Psi, q, a, K, M, d)
    HM, _ = rb.block_middle(Phi, PsiM, q, a, K, M, d)
    HL, _ = rb.block_toeplitz(PsiM, PhiL, q, a, K, M, d)
    G, rG = mp.gamma, mp.rgamma
    P0 = (G(q + t) * rG(2 * q + t)) ** 3; Q0 = (G(-t) * rG(q - t)) ** 3
    Pm = (G(q - 1 + t) * rG(2 * q - 1 + t)) ** 3; Qm = (G(1 - t) * rG(1 + q - t)) ** 3
    D = mp.sin(mp.pi * t) ** 3 * mp.sin(mp.pi * (t + q)) ** 3
    return D * G(2 * q) ** 3 * (P0 * Q0 * HR + P0 * Qm * HM + Pm * Qm * HL)
for ds in ('2.5', '1.25'):
    q = mp.mpf(ds) / 4
    nodes = rb.default_nodes(mp.mpf('0.0917'))
    vals = [wheel_sample(q, t) for t in nodes]
    Mx = mp.matrix([[mp.expj(2 * mp.pi * k * t) for k in range(-2, 3)] for t in nodes])
    c = mp.lu_solve(Mx, mp.matrix(vals))
    # residue functional: W3 = -Res_{t=0} [Xi/D_w], D_w = sin^3(pi t) sin^3(pi(t+q))
    W3 = 0
    for k in range(-2, 3):
        f = lambda tt, k=k: mp.expj(2 * mp.pi * k * tt) / (mp.sin(mp.pi * (tt + q)) ** 3 * (mp.sin(mp.pi * tt) / tt) ** 3)
        W3 += -c[k + 2] * mp.diff(f, 0, 2, singular=True) / 2 / mp.pi ** 3
    print('d', ds, '|c_k| =', [mp.nstr(abs(c[i]), 6) for i in range(5)], ' W3 =', mp.nstr(mp.re(W3), 25), flush=True)
