#!/usr/bin/env python3
"""Diagnostic: is c_{+-2} = 0 tied to the matching between the multiplicities d_l(d) and the eigenvalue parameter q = d/4?
Use multiplicities of dimension d_m = 4 q_m (generating function (1+z)(1-z)^{1-4q_m}) with eigenvalue sequences at q."""
import mpmath as mp
import rblocks as rb
mp.mp.dps = 40
def sample_mm(q, qm, t, tau, K=20, M=220):
    a = 1 - 2 * q - tau
    d = rb.dlist(qm, 2 * M + 2)
    Phi, Psi, PsiM, PhiL = rb.seqs(q, t, tau)
    HR, _ = rb.block_toeplitz(Phi, Psi, qm, a, K, M, d)
    HM, _ = rb.block_middle(Phi, PsiM, qm, a, K, M, d)
    HL, _ = rb.block_toeplitz(PsiM, PhiL, qm, a, K, M, d)
    D, PR, PM, PL = rb.prefactors(q, t, tau)
    return D * mp.gamma(2 * q) ** 2 * (PR * HR + PM * HM + PL * HL)
q = mp.mpf('2.5') / 4; tau = mp.mpf('0.3')
for qm in (mp.mpf('2.5') / 4, mp.mpf('2.2') / 4, mp.mpf('2.9') / 4, mp.mpf('1') / 4 + mp.mpf('2.5')/4 - mp.mpf('1')/4):
    nodes = rb.default_nodes(mp.mpf('0.0917'))
    vals = [sample_mm(q, qm, t, tau) for t in nodes]
    Mx = mp.matrix([[mp.expj(2 * mp.pi * k * t) for k in range(-2, 3)] for t in nodes])
    c = mp.lu_solve(Mx, mp.matrix(vals))
    print('d_eig', 4 * q, 'd_mult', mp.nstr(4 * qm, 4), '|c_k|', [mp.nstr(abs(c[i]), 6) for i in range(5)], flush=True)
