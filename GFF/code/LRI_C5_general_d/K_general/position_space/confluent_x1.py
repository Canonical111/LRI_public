"""Confluent K-path series S_I + S_II at unit arguments (float64, numpy), partial sums vs the MB value of J_t."""
import numpy as np
from scipy.special import gammaln, gammasgn, psi, polygamma
from confluent_check import mb_kpath
import sys
d = float(sys.argv[1]); t = float(sys.argv[2]); q = d / 4
def lg(x): return gammaln(x), gammasgn(x)
Mmax = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
m = np.arange(Mmax, dtype=float)
lf = gammaln(m + 1)
I, J = np.meshgrid(m, m, indexing='ij')         # I = m (z1), J = n (z2)
w = I + J
L = np.zeros_like(w); S = np.ones_like(w)
for x, s in [(q + w, 2), (q + J, 1), (q - J, -1), (t / 2 + I, 1), (q - t / 2 - w, 1), (2 * q - t / 2 - I, -1), (q + t / 2 + w, -1)]:
    l, sg = lg(x); L += s * l; S *= sg ** abs(s)
f = S * np.exp(L - 2 * lf[:, None] - 2 * lf[None, :])
L1 = 2 * psi(q + w) + psi(t / 2 + I) + psi(2 * q - t / 2 - I) - psi(q - t / 2 - w) - psi(q + t / 2 + w)
L2 = 2 * psi(q + w) + psi(q + J) + psi(q - J) - psi(q - t / 2 - w) - psi(q + t / 2 + w)
L12 = 2 * polygamma(1, q + w) + polygamma(1, q - t / 2 - w) - polygamma(1, q + t / 2 + w)
TI = f * ((L1 - 2 * psi(I + 1)) * (L2 - 2 * psi(J + 1)) + L12)
K_, Jn = I, J                                  # K_ = k (w-line), Jn = n (z2)
z1 = q - t / 2 + K_ - Jn; ww = q - t / 2 + K_
L = np.zeros_like(z1); S = np.ones_like(z1)
for x, s in [(-z1, 2), (q + ww, 2), (q + Jn, 1), (q - Jn, -1), (t / 2 + z1, 1), (2 * q - t / 2 - z1, -1), (q + t / 2 + ww, -1)]:
    l, sg = lg(x); L += s * l; S *= sg ** abs(s)
g = S * np.exp(L - lf[:, None] - 2 * lf[None, :])
dl = 2 * psi(-z1) + psi(q + Jn) + psi(q - Jn) - psi(t / 2 + z1) - psi(2 * q - t / 2 - z1) - 2 * psi(Jn + 1)
TII = (-1.0) ** (K_ + 1) * g * dl
N = np.exp(2 * gammaln(2 * q) - 4 * gammaln(q))
mbv = float(mb_kpath(str(d), str(t), '1', '1', repr(-t / 4), repr(-q / 3), digits=16))
print('d=%g t=%g  E2=2q-2-t=%.3f   MB J_t = %.12f' % (d, t, 2 * q - 2 - t, mbv))
for M in (125, 250, 500, 1000, Mmax):
    val = N * (TI[:M, :M].sum() + TII[:M, :M].sum())
    print('  M=%5d  series = %.12f   diff = %.3e' % (M, val, val - mbv))
