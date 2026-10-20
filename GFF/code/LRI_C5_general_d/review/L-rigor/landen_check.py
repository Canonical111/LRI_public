#!/usr/bin/env python3
"""Review L-rigor: independent numeric check of the 'Landen system' normalization (Mac, ~20 digits).
Omega(t;x) = sin^4 pi(t+x) sum_{n>=0} phi_x(n+t)^4 + sin^4(pi t) sum_{j>=0} [Gamma(j+1-t)/Gamma(j+2-x-t)]^4,
phi_x(s) = Gamma(s+x)/Gamma(s+1), N_x = Gamma(1-x)/Gamma(x); modes N_x^2 Omega = A + B cos 2pi(t + x/2) (gc:L2modes).
Raw modes (no N_x^2): a(x) = A/N_x^2, b(x) = B/N_x^2.  Expect at x = 1/2:
  normalized:  A' = 2 pi B - 2 log2 A,          B' = (3pi/2) A - 2 log2 B      (note gc:L2proof, RESULT.md)
  raw:         a' = 2 pi b - (10 log2 + 4 gamma) a, b' = (3pi/2) a - (10 log2 + 4 gamma) b  (PROOF_STATUS L9)."""
import mpmath as mp
mp.mp.dps = 34


def ssum(a, b):
    f = lambda n: (mp.gamma(n + a) / mp.gamma(n + b)) ** 4
    return mp.nsum(f, [0, mp.inf], method='e')


def Omega(t, x):
    return mp.sinpi(t + x) ** 4 * ssum(t + x, t + 1) + mp.sinpi(t) ** 4 * ssum(1 - t, 2 - x - t)


def raw_modes(x):
    a = Omega(mp.mpf(1) / 4 - x / 2, x)
    b = Omega(-x / 2, x) - a
    return a, b


def Nx(x):
    return mp.gamma(1 - x) / mp.gamma(x)


x0 = mp.mpf(1) / 2
h = mp.mpf('2e-5')
vals = {}
for k in (-2, -1, 1, 2):
    vals[k] = raw_modes(x0 + k * h)
a0, b0 = raw_modes(x0)
der = lambda i, w: (8 * (w[1][i] - w[-1][i]) - (w[2][i] - w[-2][i])) / (12 * h)   # O(h^4)
ap, bp = der(0, vals), der(1, vals)
norm = {k: (Nx(x0 + k * h) ** 2 * vals[k][0], Nx(x0 + k * h) ** 2 * vals[k][1]) for k in vals}
Ap, Bp = der(0, norm), der(1, norm)
pi, l2, eg = mp.pi, mp.log(2), mp.euler
print('A=a at 1/2:', mp.nstr(a0, 15), ' 8N_e/pi check later; B:', mp.nstr(b0, 15))
print("normalized: A' - (2pi B - 2log2 A) =", mp.nstr(Ap - (2 * pi * b0 - 2 * l2 * a0), 3),
      "   B' - (3pi/2 A - 2log2 B) =", mp.nstr(Bp - (3 * pi / 2 * a0 - 2 * l2 * b0), 3))
print("raw:        a' - (2pi b - (10log2+4g) a) =", mp.nstr(ap - (2 * pi * b0 - (10 * l2 + 4 * eg) * a0), 3),
      "   b' - (3pi/2 a - (10log2+4g) b) =", mp.nstr(bp - (3 * pi / 2 * a0 - (10 * l2 + 4 * eg) * b0), 3))
print("(scale: A' =", mp.nstr(Ap, 10), ", a' =", mp.nstr(ap, 10), ")")
