#!/usr/bin/env python3
"""Review check D2 (foundation-rigor): normalization of the b_max residue.
Compares the reviewer's predicted residue
    Res_{b=b_max} c_{r,k}(b)  from  -4/(r Gamma(d-1)) D_b(t)^r [Phi(-t) + Phi(sigma+t)]
with the residue read off the foundation's CONTINUED (zeta-regularized) finite-sample code:
    rho_k ~ (delta/2) [c_k(b_max+delta) - c_k(b_max-delta)]   (error O(delta^2)).
This tests the continuation of Remark rem:continuation and the reviewer's residue formula together."""
import sys
import mpmath as mp
sys.path.insert(0, '.')
import wheel_general_b as wg
from bmax_residue import Phi

d, r = mp.mpf(sys.argv[1]) if len(sys.argv) > 1 else mp.mpf('2.5'), int(sys.argv[2]) if len(sys.argv) > 2 else 4
mp.mp.dps = 30
bm = d - 2 * (d - 1) / r
sig, g = bm / 2, (d - bm) / 2


def ck_from_gamma(gam, s):
    return [gam[0]] + [(2 * gam[k] * mp.expjpi(-k * s) + 2 * gam[-k] * mp.expjpi(k * s)) / 2 for k in range(1, r)]


# predicted residue (Fourier modes of R(t) at b_max)
Nn = 2 * r - 1
ts = [-d / 8 + mp.mpf(j) / Nn + 1j / (8 * mp.pi * r) for j in range(Nn)]
R = []
for t in ts:
    Db = mp.sin(mp.pi * t) * mp.sin(mp.pi * (t + sig))
    R.append(-4 / (r * mp.gamma(d - 1)) * Db ** r * (Phi(-t, g, r) + Phi(sig + t, g, r)))
gamR = {m: mp.fsum(R[j] * mp.exp(-2j * mp.pi * m * ts[j]) for j in range(Nn)) / Nn for m in range(-(r - 1), r)}
pred = ck_from_gamma(gamR, sig)
print('d=%s r=%d b_max=%s' % (d, r, bm))
print('predicted residues of c_k:', [mp.nstr(mp.re(x), 12) for x in pred])
for delta in (mp.mpf('1e-3'), mp.mpf('1e-4')):
    cs = []
    for sgn in (1, -1):
        with mp.workdps(45):
            w = wg.Wheel(r, d, bm + sgn * delta)
            gam, X = w.fourier_fixed()
            cs.append(ck_from_gamma(gam, (bm + sgn * delta) / 2))
    rho = [delta / 2 * (cs[0][k] - cs[1][k]) for k in range(r)]
    print('delta=%s  residues from continued code:' % mp.nstr(delta, 2), [mp.nstr(mp.re(x), 12) for x in rho])
    print('             rel.dev:', [mp.nstr(abs(rho[k] - pred[k]) / max(abs(x) for x in pred), 3) for k in range(r)])
