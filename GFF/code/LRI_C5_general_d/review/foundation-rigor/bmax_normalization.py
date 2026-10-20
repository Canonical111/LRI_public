#!/usr/bin/env python3
"""Review check D2 (foundation-rigor), Mac-sized: normalization of the reviewer's b_max residue formula
    Res_{b=b_max} Xi_r = -4/(r Gamma(d-1)) D_b^r [Phi(-t) + Phi(sigma+t)]
against the foundation's continued (zeta-regularized) code, d=2.5, r=4, b_max=1.75:
    rho_k = (delta/2)[c_k(b_max+delta) - c_k(b_max-delta)] -> predicted, error O(delta^2)."""
import mpmath as mp
import wheel_general_b as wg
from bmax_residue import Phi
mp.mp.dps = 15
d, r = mp.mpf('2.5'), 4
bm = d - 2 * (d - 1) / r
sig, g = bm / 2, (d - bm) / 2
Nn = 2 * r - 1
ts = [-d / 8 + mp.mpf(j) / Nn + 1j / (8 * mp.pi * r) for j in range(Nn)]
R = []
for t in ts:
    Db = mp.sin(mp.pi * t) * mp.sin(mp.pi * (t + sig))
    R.append(-4 / (r * mp.gamma(d - 1)) * Db ** r * (Phi(-t, g, r, M0=20) + Phi(sig + t, g, r, M0=20)))
gam = {m: mp.fsum(R[j] * mp.exp(-2j * mp.pi * m * ts[j]) for j in range(Nn)) / Nn for m in range(-(r - 1), r)}
pred = [gam[0]] + [(2 * gam[k] * mp.expjpi(-k * sig) + 2 * gam[-k] * mp.expjpi(k * sig)) / 2 for k in range(1, r)]
print('predicted residues of c_k:', [mp.nstr(mp.re(x), 10) for x in pred])
mp.mp.dps = 25
for delta in (mp.mpf('1e-3'), mp.mpf('1e-4')):
    cs = []
    for s in (1, -1):
        W, info = wg.Wheel(r, d, bm + s * delta).W_fixed(full=True)
        cs.append(info['c'])
    rho = [delta / 2 * (cs[0][k] - cs[1][k]) for k in range(r)]
    print('delta=%s: residues from continued code' % mp.nstr(delta, 2), [mp.nstr(mp.re(x), 10) for x in rho],
          ' rel.dev', [mp.nstr(abs(rho[k] - pred[k]) / abs(pred[0]), 2) for k in range(r)])
