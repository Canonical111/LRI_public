#!/usr/bin/env python3
"""Review check C (foundation-rigor): an INDEPENDENT double-precision evaluation of the periodized wheel
    Xi_r(t;b) = D_b(t)^r sum_l d_l sum_{n in Z} g_l(a_l+n+t;b)^r
by direct lattice summation (numpy/scipy; no hypsums, no Horn blocks), split as in Lemma 1:
right part (n>=0), left part (= right part at 1-sigma-t, eq:left) and middle part (eq:middle).
Inner sums: direct to L, then an Euler-Maclaurin tail  int_L^inf h + h(L)/2 - h'(L)/12 + h'''(L)/720,
the integral by Gauss-Legendre in w after x = L w^{-1/(p-1)} (h continued in the summation index by Gamma
functions; log-Gamma ratios by Stirling for large arguments).
Outer sums: direct to N, plus a fitted power-law tail (error ~ tail x O(1/N)); convergence checked by halving.
From 4r+1 nodes the DFT gives all modes |m| <= 2r: tests Theorem 4 (modes |m| >= r vanish), Theorem 6
(|m| = r-1 vanishes), the reflection gamma_m = gamma_{-m} e^{2 pi i m sigma}, and Prop. 9 (W_r from the residue
functional, compared elsewhere with spectral.py and the finite-sample code).

usage: python3 brute_xi.py r d b_re [b_im] [L] [N]
"""
import sys
import math
import numpy as np
from scipy.special import loggamma, gamma as Gfun, bernoulli, comb
from numpy.polynomial.legendre import leggauss

XG, WG = leggauss(48)
XG = (XG + 1) / 2
WG = WG / 2
_BN = bernoulli(24)


def _bernpoly(n, x):
    return sum(comb(n, k, exact=True) * _BN[k] * x ** (n - k) for k in range(n + 1))


def lgratio(z, a, b, K=12, zsw=150.0):
    """log Gamma(z+a) - log Gamma(z+b): direct for |z| < zsw, Stirling (DLMF 5.11.8 difference) beyond."""
    z = np.asarray(z, dtype=complex)
    out = np.empty_like(z)
    big = np.abs(z) >= zsw
    if np.any(~big):
        zz = z[~big]
        out[~big] = loggamma(zz + a) - loggamma(zz + b)
    if np.any(big):
        zz = z[big]
        acc = (a - b) * np.log(zz)
        iz = 1.0 / zz
        pw = iz.copy()
        for k in range(1, K + 1):
            acc = acc + (-1) ** (k + 1) * (_bernpoly(k + 1, a) - _bernpoly(k + 1, b)) / (k * (k + 1)) * pw
            pw = pw * iz
        out[big] = acc
    return out


class Brute:
    def __init__(self, r, d, b, L=4000, N=3000, gprime=None):
        self.r, self.d = int(r), float(d)
        self.b = complex(b)
        q = self.d / 4
        self.q = q
        self.sig = self.b / 2
        self.g = 2 * q - self.sig if gprime is None else complex(gprime)   # gprime: unbalanced control
        self.L, self.N = int(L), int(N)
        M = self.L + self.N + 8
        j = np.arange(M, dtype=float)
        ratio = (2 * q + 1 + j) * (4 * q - 1 + j) / ((2 * q + j) * (2 + j))
        D = np.concatenate([[1.0], np.cumprod(ratio[:-1])])
        self.dl = np.concatenate([[1.0], 4 * q * D])            # d_0..d_M  (fp:degeneracy)
        self.isint1 = abs(self.d - 1) < 1e-15
        self.pdecay = (self.r * self.g + 2 - self.d).real      # inner summand ~ l^{d-2-rg}
        self.tails = []

    def dcont(self, x):
        """d_l continued to real l (large)."""
        d = self.d
        if abs(d - 2) < 1e-15:
            return 2.0 + 0 * x
        if abs(d - 3) < 1e-15:
            return 2 * x + 1.0
        return ((2 * x + d - 2) * np.exp(lgratio(x, d - 2, 1.0)) / Gfun(d - 1)).real

    def Fpos(self, z):
        """f(z)^r, f(z) = Gamma(z)/Gamma(z+g), Re z > 0."""
        return np.exp(self.r * lgratio(z, 0.0, self.g))

    def Fneg(self, n, t):
        """f(-n-t)^r by reflection (eq:right)."""
        pre = -np.sin(np.pi * (self.g - t)) / np.sin(np.pi * t)
        return (pre * np.exp(lgratio(n + 1 + t, -self.g, 0.0))) ** self.r

    def em_tail(self, h, L):
        """sum_{x=L}^inf h(x) by Euler-Maclaurin; int_L^inf h via x = L w^{-a}, a = 1/(p-1)."""
        a = 1.0 / (self.pdecay - 1)
        x = L * XG ** (-a)
        integ = np.sum(WG * h(x) * a * L * XG ** (-a - 1))
        hd = h(np.array([L - 2.0, L - 1.0, L, L + 1.0, L + 2.0]))
        d1 = (hd[3] - hd[1]) / 2
        d3 = (hd[4] - 2 * hd[3] + 2 * hd[1] - hd[0]) / 2
        return integ + hd[2] / 2 - d1 / 12 + d3 / 720

    def right(self, t):
        """sum_{l>=0} d_l sum_{n>=0} f(l+sigma+n+t)^r f(-n-t)^r"""
        L, N = self.L, self.N
        if self.isint1:                                          # d = 1: only l = 0, 1
            n = np.arange(N + 2, dtype=float)
            G = self.Fpos(n + self.sig + t)
            terms = self.Fneg(n[:N], t) * (G[:N] + G[1:N + 1])
            return self._outer(terms)
        m = np.arange(L + N + 2, dtype=float)
        G = self.Fpos(m + self.sig + t)                          # G[m] = f(m+sigma+t)^r
        dl = self.dl[:L]
        terms = np.empty(N, dtype=complex)
        Phi = self.Fneg(np.arange(N, dtype=float), t)
        for n in range(N):
            inner = np.dot(dl, G[n:n + L])
            inner += self.em_tail(lambda x, n=n: self.dcont(x) * self.Fpos(x + n + self.sig + t), float(L))
            terms[n] = inner * Phi[n]
        return self._outer(terms)

    def middle(self, t):
        """sum_{j,k>=0} d_{j+k+1} f(k+sigma+t)^r f(j+1-t)^r"""
        L, N = self.L, self.N
        if self.isint1:                                          # d = 1: only j = k = 0 (d_1 = 1)
            return complex(self.Fpos(self.sig + t) * self.Fpos(1 - t))
        k = np.arange(L, dtype=float)
        Q = self.Fpos(k + self.sig + t)
        P = self.Fpos(np.arange(N, dtype=float) + 1 - t)
        terms = np.empty(N, dtype=complex)
        for j in range(N):
            inner = np.dot(self.dl[j + 1:j + 1 + L], Q)
            inner += self.em_tail(lambda x, j=j: self.dcont(x + j + 1) * self.Fpos(x + self.sig + t), float(L))
            terms[j] = inner * P[j]
        return self._outer(terms)

    def _outer(self, terms):
        """direct sum + fitted tail sum_{n>=N} A n^{-p}, complex p from the last terms."""
        N = len(terms)
        n1, n2 = N - 1, (3 * N) // 4
        p = -np.log(terms[n1] / terms[n2]) / np.log(n1 / n2)
        A = terms[n1] * n1 ** p
        tail = A * (N - 0.5) ** (1 - p) / (p - 1)
        self.tails.append(abs(tail))
        return np.sum(terms) + tail

    def Db(self, t):
        return np.sin(np.pi * t) * np.sin(np.pi * (t + self.sig))

    def S(self, t):
        tp = 1 - self.sig - t
        return self.right(t) + self.right(tp) + self.middle(t)

    def Xi(self, t):
        return self.Db(t) ** self.r * self.S(t)

    def nodes(self, eta=0.06, tau0=0.0137, Nn=None):
        Nn = Nn or 4 * self.r + 1
        return [tau0 + j / Nn + 1j * eta for j in range(Nn)]

    def modes(self, ts=None):
        ts = ts or self.nodes()
        Nn = len(ts)
        X = np.array([self.Xi(t) for t in ts])
        M = (Nn - 1) // 2
        tt = np.array(ts)
        gam = {m: np.sum(X * np.exp(-2j * np.pi * m * tt)) / Nn for m in range(-M, M + 1)}
        return gam, X, ts

    def W_from_modes(self, gam):
        """Prop. 9, exponential form (all modes |m| <= r-1 kept, so Theorem 6 is not assumed)."""
        from mpmath import psi as mpsi
        r, s = self.r, self.sig
        u = [r * ((1 + (-1) ** h) * complex(mpsi(h - 1, 1)) - (-1) ** (h + 1) * complex(mpsi(h - 1, 1 - s))
                  + complex(mpsi(h - 1, s))) for h in range(1, r)]

        def bellE(xs):
            E = [1 + 0j]
            for m in range(1, len(xs) + 1):
                E.append(sum(xs[h - 1] / math.factorial(h - 1) * E[m - h] for h in range(1, m + 1)) / m)
            return E
        Nb = Gfun(2 * self.q) * np.exp(loggamma(self.g) - loggamma(s))
        lead = (Nb / (np.pi * np.sin(np.pi * s))) ** r
        W = sum(gm * bellE([u[0] + 2j * np.pi * m] + u[1:])[r - 1] for m, gm in gam.items() if abs(m) <= r - 1)
        return complex(-lead * W)


def summarize(r, gam, sig):
    scale = max(abs(v) for v in gam.values())
    refl = max(abs(gam[m] - gam[-m] * np.exp(2j * np.pi * m * sig)) for m in gam) / scale
    hi = max(abs(gam[m]) for m in gam if abs(m) >= r) / scale
    top = max(abs(gam[r - 1]), abs(gam[1 - r])) / scale
    return dict(refl=float(refl), boundary=float(hi), top=float(top),
                top_abs=[float(abs(gam[r - 1])), float(abs(gam[1 - r]))])


if __name__ == '__main__':
    r = int(sys.argv[1])
    d = float(sys.argv[2])
    b = complex(float(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) > 4 else 0.0)
    L = int(sys.argv[5]) if len(sys.argv) > 5 else 4000
    N = int(sys.argv[6]) if len(sys.argv) > 6 else 3000
    B = Brute(r, d, b, L, N)
    gam, X, ts = B.modes()
    for m in sorted(gam):
        print('   gamma_%+d = %s   |.|/max = %.2e' % (m, np.round(gam[m], 12), abs(gam[m]) / max(abs(v) for v in gam.values())))
    print(summarize(r, gam, B.sig))
    print('W from residue functional:', B.W_from_modes(gam), ' max outer tail:', max(B.tails))
