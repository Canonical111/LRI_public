#!/usr/bin/env python3
"""Recompute the external lattice comparison of Section 14 of the GFF note (cnm:latticeComparison).

The series y_t = 1 - Delta_E = 1/2 + eps/6 - C2 eps^2 - ... - C5 eps^5 of the one-dimensional long-range Ising model,
with the closed-form C0..C5 (Section 1.1), is resummed in six Borel-Pade-Leroy forms ([3/2] and [2/3] approximants of
sum_k c_k t^k / Gamma(k+b+1), b = 0, 1, 2, then the Laplace integral int_0^inf e^-t t^b [L/M](eps t) dt), at
s = 0.6, 0.7, 0.8 (eps = 2s - 1). It checks the ranges quoted in the note to their printed digits, that no approximant
has a positive real Borel pole, and that with C5 scaled by 0.8 or 1.2 the pole-free values at s = 0.6 stay inside the
Monte Carlo interval 0.50 +- 0.02 of Uzelac, Glumac and Anicic, Phys. Rev. E 63 (2001) 037101. Exit status 1 on any
mismatch. Needs mpmath. Runtime: seconds.
"""
import sys
import mpmath as m

m.mp.dps = 40
# C0..C5 of the one-dimensional model (closed forms of Section 1.1, 64 digits)
C = [m.mpf('0.5'), -m.mpf(1) / 6,
     m.mpf('0.6571312639810638306812857632346899062776855485351252041619627367'),
     m.mpf('-3.7198563229018334224898857126627769261620897859102304640296904728'),
     m.mpf('45.424880103556755406149859341587348790703973637605433408075143709'),
     m.mpf('-731.13947662453982585386912658252723066247889754436000363581411278')]
QUOTED = {'0.6': ('0.51738', '0.51774'), '0.7': ('0.51518', '0.51886'), '0.8': ('0.50021', '0.51231')}
MC = {'0.6': (0.48, 0.52), '0.7': (0.49, 0.53), '0.8': (0.45, 0.49)}


def bpl(c, eps, L, M, b):
    bc = [c[k] / m.gamma(k + b + 1) for k in range(len(c))]
    p, q = m.pade(bc, L, M)
    roots = m.polyroots(q[::-1], maxsteps=200, extraprec=50)
    pos = [r for r in roots if abs(m.im(r)) < 1e-15 and m.re(r) > 0]
    f = lambda t: m.exp(-t) * t ** b * m.polyval(p[::-1], eps * t) / m.polyval(q[::-1], eps * t)
    return m.quad(f, [0, 1, 10, m.inf]), len(pos)


def six(c, s):
    eps = 2 * m.mpf(s) - 1
    return [bpl(c, eps, L, M, b) for (L, M) in ((3, 2), (2, 3)) for b in (0, 1, 2)]


yt = [1 - C[0]] + [-x for x in C[1:]]
bad = 0
for s, (lo, hi) in QUOTED.items():
    vals = six(yt, s)
    ys = [v for v, _ in vals]
    npos = sum(n for _, n in vals)
    got = (m.nstr(min(ys), 5, min_fixed=-10, max_fixed=10), m.nstr(max(ys), 5, min_fixed=-10, max_fixed=10))
    ok = (f"{float(min(ys)):.5f}", f"{float(max(ys)):.5f}") == (lo, hi) and npos == 0
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  s={s}: range {float(min(ys)):.5f}-{float(max(ys)):.5f} "
          f"(quoted {lo}-{hi}); positive Borel poles {npos}")
lo08 = min(v for v, _ in six(yt, '0.8'))
ok = lo08 > MC['0.8'][1]
bad += not ok
print(f"{'PASS' if ok else 'FAIL'}  s=0.8: all six above the Monte Carlo interval; lowest exceeds it by {float(lo08) - MC['0.8'][1]:.3f}")
for fac in (0.8, 1.2):
    c = list(yt)
    c[5] = c[5] * fac
    vals = six(c, '0.6')
    inside = [MC['0.6'][0] <= float(v) <= MC['0.6'][1] for v, n in vals if n == 0]
    ok = bool(inside) and all(inside)
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  C5 x {fac}: pole-free values at s=0.6 inside 0.50+-0.02 ({sum(inside)} of {len(inside)})")
print('lattice comparison:', 'PASS' if not bad else f'{bad} FAIL')
sys.exit(1 if bad else 0)
