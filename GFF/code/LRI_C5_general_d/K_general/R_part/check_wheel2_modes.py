#!/usr/bin/env python3
"""Control: balanced r=2 wheel with rim b < d/2 (gap gamma = d/2 - b/2 > q).  Growth bound allows |k|<=1;
if the 'top mode killed by the spin sum' phenomenon holds, the sample is CONSTANT, and then
W_2(d;b) = -Res_{t=0}[c_0 / D(t)] must equal B_d(d-b, 2b) (gs: two-wheel convolution)."""
import mpmath as mp
import rblocks as rb
mp.mp.dps = 40
def sample2(d, b, t, K=20, M=220):
    q = d / 4; g = d / 2 - b / 2; a = 1 - 2 * g
    dd = rb.dlist(q, 2 * M + 2)
    Phi = ([b / 2 + t] * 2, [d / 2 + t] * 2); Psi = ([1 - g + t] * 2, [1 + t] * 2)
    PsiM = ([1 - t] * 2, [1 + g - t] * 2); PhiL = ([2 - d / 2 - t] * 2, [2 - b / 2 - t] * 2)
    HR, _ = rb.block_toeplitz(Phi, Psi, q, a, K, M, dd)
    HM, _ = rb.block_middle(Phi, PsiM, q, a, K, M, dd)
    HL, _ = rb.block_toeplitz(PsiM, PhiL, q, a, K, M, dd)
    G, rG = mp.gamma, mp.rgamma
    P0 = (G(b / 2 + t) * rG(d / 2 + t)) ** 2; Q0 = (G(-t) * rG(g - t)) ** 2
    Pm = (G(b / 2 - 1 + t) * rG(d / 2 - 1 + t)) ** 2; Qm = (G(1 - t) * rG(1 + g - t)) ** 2
    D = mp.sin(mp.pi * t) ** 2 * mp.sin(mp.pi * (t + b / 2)) ** 2
    Nb = G(d / 2) * G((d - b) / 2) * rG(b / 2)
    return D * Nb ** 2 * (P0 * Q0 * HR + P0 * Qm * HM + Pm * Qm * HL)
def Bd(d, a, b):
    G, rG = mp.gamma, mp.rgamma
    return G(d / 2) * G((d - a) / 2) * G((d - b) / 2) * G((a + b - d) / 2) * rG(a / 2) * rG(b / 2) * rG((2 * d - a - b) / 2)
for ds, bs in (('2.5', '0.9'), ('1.25', '0.45'), ('3', '1.2')):
    d = mp.mpf(ds); b = mp.mpf(bs)
    nodes = [mp.mpf('0.0917') + mp.mpf(j) / 3 for j in range(3)]
    vals = [sample2(d, b, t) for t in nodes]
    Mx = mp.matrix([[mp.expj(2 * mp.pi * k * t) for k in range(-1, 2)] for t in nodes])
    c = mp.lu_solve(Mx, mp.matrix(vals))
    c0 = c[1]
    # W2 = -Res_{t=0} c0/D, D = sin^2(pi t) sin^2(pi(t+b/2)) -> Res = c0 * d/dt[1/sin^2(pi(t+b/2))]/pi^2 at 0
    W2 = -c0 * (-2 * mp.pi * mp.cos(mp.pi * b / 2) / mp.sin(mp.pi * b / 2) ** 3) / mp.pi ** 2
    print('d', ds, 'b', bs, '|c_k| k=-1..1:', [mp.nstr(abs(c[i]), 6) for i in range(3)], ' W2 from c0:', mp.nstr(mp.re(W2), 25),
          ' B_d(d-b,2b):', mp.nstr(Bd(d, d - b, 2 * b), 25), flush=True)
