#!/usr/bin/env python3
"""Review check D (foundation-rigor): the pole of the continued c_{r,k} at b = b_max for d > 2
(Remarks rem:sampleradius / rem:continuation and the open point 'expected but not analysed').

Derivation (reviewer): for d > 2 the divergence at b_max comes from the endpoint l -> inf at fixed n (and the
middle endpoints), where d_l ~ 2 l^{d-2}/Gamma(d-1) and f(l+c)^r ~ l^{-rg}; sum_l l^{d-2-rg} ~ 1/(rg-d+1)
= -2/(r (b-b_max)).  Collecting the four endpoint families,
    Res_{b=b_max} Xi_r(t;b) = -4/(r Gamma(d-1)) * D_b(t)^r [Phi(-t) + Phi(sigma+t)],
    Phi(u) = sum_{m in Z} [Gamma(m+u)/Gamma(m+u+g)]^r      (converges: rg = d-1 > 1).
Predictions checked here at b = b_max:
  (1) the residue is a trigonometric polynomial with modes |m| <= r-1 (no boundary modes);
  (2) its top mode |m| = r-1 VANISHES (required by Theorem 6 + analytic continuation; analytically it is the
      condition rg + 2 - d = 1 at b_max, via Phi's first Fourier coefficient = 2 pi a'(2 pi) (i/Gamma(g))^r);
  (3) its lower modes are nonzero (so the continued c_{r,k} really have a pole, as the foundation expects);
  (4) its image under the residue functional vanishes (sum of residues of F is 0), so W_r has no pole."""
import mpmath as mp

mp.mp.dps = 20


def Phi(u, g, r, M0=40):
    F = lambda z: (mp.gamma(z) * mp.rgamma(z + g)) ** r
    sr = (mp.sin(mp.pi * (u + g)) / mp.sin(mp.pi * u)) ** r           # constant reflection factor (integer shifts)
    Fneg = lambda m: sr * (mp.gamma(1 - m - u - g) * mp.rgamma(1 - m - u)) ** r   # F(m+u) for m <= -1
    s = mp.fsum(F(m + u) for m in range(0, M0)) + mp.fsum(Fneg(m) for m in range(-M0 + 1, 0))
    s += mp.nsum(lambda m: F(m + u), [M0, mp.inf], method='euler-maclaurin')
    s += mp.nsum(lambda k: Fneg(-k), [M0, mp.inf], method='euler-maclaurin')
    return s


def bellE(xs):
    E = [mp.mpc(1)]
    for m in range(1, len(xs) + 1):
        E.append(mp.fsum(xs[h - 1] / mp.factorial(h - 1) * E[m - h] for h in range(1, m + 1)) / m)
    return E


if __name__ == "__main__":
  for d, r in ((mp.mpf('2.5'), 4), (mp.mpf('2.75'), 3), (mp.mpf('3.5'), 4), (mp.mpf('3.5'), 3)):
    bm = d - 2 * (d - 1) / r
    sig, g = bm / 2, (d - bm) / 2
    Nn = 4 * r + 1
    eta, tau0 = mp.mpf('0.06'), mp.mpf('0.0137')
    ts = [tau0 + mp.mpf(j) / Nn + 1j * eta for j in range(Nn)]
    vals = []
    for t in ts:
        Db = mp.sin(mp.pi * t) * mp.sin(mp.pi * (t + sig))
        vals.append(-4 / (r * mp.gamma(d - 1)) * Db ** r * (Phi(-t, g, r) + Phi(sig + t, g, r)))
    M = (Nn - 1) // 2
    gam = {m: mp.fsum(vals[j] * mp.exp(-2j * mp.pi * m * ts[j]) for j in range(Nn)) / Nn for m in range(-M, M + 1)}
    sc = max(abs(v) for v in gam.values())
    print('d=%s r=%d b_max=%s (rg=%s):' % (d, r, mp.nstr(bm, 6), mp.nstr(r * g, 6)))
    print('   |gamma_m|/max for m=0..%d: %s' % (M, ', '.join(mp.nstr(abs(gam[m]) / sc, 3) for m in range(0, M + 1))))
    print('   top mode |gamma_{+-(r-1)}|/max = %s, %s' % (mp.nstr(abs(gam[r - 1]) / sc, 3), mp.nstr(abs(gam[1 - r]) / sc, 3)))
    u = [r * ((1 + (-1) ** h) * mp.psi(h - 1, 1) - (-1) ** (h + 1) * mp.psi(h - 1, 1 - sig) + mp.psi(h - 1, sig))
         for h in range(1, r)]
    func = mp.fsum(gam[m] * bellE([u[0] + 2j * mp.pi * m] + u[1:])[r - 1] for m in range(-(r - 1), r))
    scale = mp.fsum(abs(gam[m] * bellE([u[0] + 2j * mp.pi * m] + u[1:])[r - 1]) for m in range(-(r - 1), r))
    print('   residue functional applied to the residue: |sum| / sum|terms| = %s' % mp.nstr(abs(func) / scale, 3))
