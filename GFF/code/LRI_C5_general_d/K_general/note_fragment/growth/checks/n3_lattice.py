#!/usr/bin/env python3
"""N3: the lattice-sum Lemma 3 of PROOF.md, numerically.

  A(Y) = sum_{l,n>=0} (1+l)^beta (l+n+Y)^-alpha (n+Y)^-alpha          (right/left parts)
  B(Y) = sum_{j,k>=0} (1+j+k)^beta (k+Y)^-alpha (j+Y)^-alpha          (middle part)
with beta = 4q-2.  Lemma 3:  A(Y) <= C_A Y^(1-gamma) (1+log Y)^[q=1/4],  B(Y) <= C_B Y^(beta+2-2 alpha),
gamma = 2 alpha - max(beta+1, 0), valid iff alpha > max(4q-1, 2q, 1/2).
Evaluation: both are sums over m = l+n (resp. j+k) of a convolution, computed by FFT up to m < N, plus a
power-law tail fitted on the last octave (positive terms; double precision is ample for a bound check).
Prints A Y^(gamma-1), B Y^(2 alpha-beta-2) (bounded in Y <=> the exponent is right) and the ratios to the
explicit constants (must be <= 1).
"""
import numpy as np


def conv(a, b):
    n = len(a) + len(b) - 1
    nf = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, nf) * np.fft.rfft(b, nf), nf)[:n]


def tail(h, m):
    """sum_{m'>=M} h(m') from the last octave assuming h ~ c m^-p:  approx h(M) M/(p-1) (midpoint corrected)"""
    M = len(h)
    i1, i2 = M // 2, M - 1
    p = -np.log(h[i2] / h[i1]) / np.log(m[i2] / m[i1])
    return h[-1] * (m[-1] + 0.5) / (p - 1) * ((m[-1] + 0.5) / m[-1]) ** (-p), p


def A_B(q, alpha, Y, N):
    beta = 4 * q - 2
    j = np.arange(N, dtype=float)
    dl = (1 + j) ** beta
    b = (j + Y) ** (-alpha)
    # A: sum_m (m+Y)^-alpha * sum_{n<=m} (1+m-n)^beta (n+Y)^-alpha
    cA = conv(dl, b)[:N]
    hA = (j + Y) ** (-alpha) * cA
    tA, pA = tail(hA, j + Y)
    # B: sum_m (1+m)^beta * sum_{k<=m} (k+Y)^-alpha (m-k+Y)^-alpha
    cB = conv(b, b)[:N]
    hB = (1 + j) ** beta * cB
    tB, pB = tail(hB, 1 + j)
    return hA.sum() + tA, hB.sum() + tB, tA / (hA.sum() + tA), tB / (hB.sum() + tB)


def C1(beta, alpha):
    if beta >= 0:
        cb = 1.0
    elif beta > -1:
        cb = 1 / (beta + 1)
    elif beta == -1:
        cb = 1.0
    else:
        cb = -beta / (-beta - 1)
    extra = 2 ** (alpha - beta - 1) / (alpha - beta - 1)
    return cb + extra


def constants(q, alpha):
    beta = 4 * q - 2
    gam = 2 * alpha - max(beta + 1, 0)
    CA = C1(beta, alpha) * (1 + 1 / (gam - 1) + (1 / (gam - 1) ** 2 if beta == -1 else 0))
    if beta >= 0:
        CB = 2 ** (beta + 1) * C1(beta, alpha) * (1 + 1 / (alpha - 1))
    else:
        CB = C1(beta / 2, alpha) ** 2
    return gam, CA, CB


import mpmath as mp


def limits(q, alpha):
    """exact Y -> infinity limits of A(Y) Y^eta and B(Y) Y^(2 alpha - beta - 2)"""
    beta = mp.mpf(4 * q - 2); a = mp.mpf(alpha)
    if beta > -1:
        LA = mp.beta(beta + 1, a - beta - 1) / (2 * a - beta - 2)
    elif beta < -1:
        LA = mp.zeta(-beta) / (2 * a - 1)
    else:
        LA = mp.nan   # q = 1/4: log-corrected; not printed
    LB = mp.quad(lambda u, v: (u + v) ** beta * (v + 1) ** (-a) * (u + 1) ** (-a), [0, 1, mp.inf], [0, 1, mp.inf])
    return LA, LB


N = 1 << 22
cases = [(0.2, 0.25 + 0.4 + 0.05), (0.2, 0.75), (0.25, 0.5 + 0.1), (0.3125, 0.625 + 0.1), (0.375, 0.75 + 0.05),
         (0.375, 0.75 + 0.3), (0.5, 1.0 + 0.15), (0.625, 1.25 + 0.3), (0.75, 1.5 + 0.55), (0.9, 1.8 + 0.85)]
print('N =', N)
for q, alpha in cases:
    beta = 4 * q - 2
    gam, CA, CB = constants(q, alpha)
    thr = max(4 * q - 1, 2 * q, 0.5)
    print('q=%.4f alpha=%.4f (threshold %.4f; Re tau = alpha-2q = %.3f): eta = gamma-1 = %.4f, C_A = %.3f, C_B = %.3f'
          % (q, alpha, thr, alpha - 2 * q, gam - 1, CA, CB))
    LA, LB = limits(q, alpha)
    print('   exact Y->inf limits: A Y^eta -> %s (/C_A = %s),  B Y^(2a-b-2) -> %s (/C_B = %s)'
          % (mp.nstr(LA, 6), mp.nstr(LA / CA, 3), mp.nstr(LB, 6), mp.nstr(LB / CB, 3)))
    for Y in (2, 8, 32, 128, 512):
        A, B, ta, tb = A_B(q, alpha, Y, N)
        logf = (1 + np.log(Y)) if q == 0.25 else 1.0
        sA = A * Y ** (gam - 1) / logf
        sB = B * Y ** (2 * alpha - beta - 2)
        print('   Y=%4d  A Y^eta%s = %.5f (A/bound = %.3f, tail %.1e)   B Y^(2a-b-2) = %.5f (B/bound = %.3f, tail %.1e)'
              % (Y, '/(1+logY)' if q == 0.25 else '', sA, sA / CA, ta, sB, sB / CB, tb))
