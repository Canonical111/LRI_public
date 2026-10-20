#!/usr/bin/env python3
"""Check foundation eq. (laplace): Gamma(z)/Gamma(z+g) = (-i/Gamma(g)) int_0^inf e^{izv}(1-e^{iv})^{g-1} dv, Im z>0,
and the conjugate form for Im z<0, at complex z (incl. Re z<0) and complex g; principal powers.
Each period [2pi k, 2pi(k+1)] is split at the midpoint and the singular endpoint is always put at the left end,
with 1-e^{+-iw} = -+2i sin(w/2) e^{+-iw/2} evaluated without cancellation."""
import mpmath as mp
mp.mp.dps = 30

def one_minus_exp(w, s):   # 1 - e^{s i w}, accurate for small w
    return -s * 2j * mp.sin(w / 2) * mp.expj(s * w / 2)

def lap(z, g, s=+1):
    Y = abs(mp.im(z))
    nper = int(mp.ceil((mp.mp.dps + 5) * mp.log(10) / (2 * mp.pi * Y))) + 2
    tot = 0
    for k in range(nper):
        base = 2 * mp.pi * k
        # left half: v = base + w, w in (0, pi):  (1-e^{s i v}) = 1-e^{s i w}
        fl = lambda w: mp.expj(s * z * (base + w)) * one_minus_exp(w, s) ** (g - 1)
        # right half: v = base + 2pi - w, w in (0, pi): (1-e^{s i v}) = 1-e^{-s i w}
        fr = lambda w: mp.expj(s * z * (base + 2 * mp.pi - w)) * one_minus_exp(w, -s) ** (g - 1)
        tot += mp.quad(fl, [0, mp.pi]) + mp.quad(fr, [0, mp.pi])
    return (-1j if s > 0 else 1j) / mp.gamma(g) * tot

for z, g in [(mp.mpc('0.7', '0.5'), mp.mpf('0.35')), (mp.mpc('-1.3', '0.8'), mp.mpc('0.45', '-0.05')),
             (mp.mpc('2.2', '0.3'), mp.mpf('0.85')), (mp.mpc('0.2', '1.1'), mp.mpc('0.65', '0.2'))]:
    ex = mp.gamma(z) / mp.gamma(z + g)
    exc = mp.gamma(mp.conj(z)) / mp.gamma(mp.conj(z) + g)
    print('z=%s g=%s  rel dev (Im z>0 form) %.2e   (Im z<0 form at conj z) %.2e' % (
        mp.nstr(z, 4), mp.nstr(g, 4), float(abs(lap(z, g) - ex) / abs(ex)), float(abs(lap(mp.conj(z), g, -1) - exc) / abs(exc))))
