#!/usr/bin/env python3
"""Check the closed forms of the residue weights quoted in the foundation (after eq. explicit):
B_{4,0} = -4 pi^3 c (5c^2+3), B_{4,1} = -4 pi^3 (5c^2+1)/s, B_{4,2} = -20 pi^3 cos/s^3, B_{4,3} (multiplies the top mode),
and the r=3 weights implied by eq. (explicit): B_{3,0} = 2 pi^2 (1+2cos^2)/s^2, B_{3,1} = 6 pi^2 cos/s^2,
against eq. (weights) [u_h from polygammas, E_m of fp:BellFinite], and the elementary u_h of eq. (elementary).
c = cot(pi sigma), s = sin(pi sigma), cos = cos(pi sigma); complex sigma."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpmath as mp
from xi_direct import bell_E
mp.mp.dps = 40

def B(r, k, sig):
    u = [r * ((1 + (-1) ** h) * mp.psi(h - 1, 1) - (-1) ** (h + 1) * mp.psi(h - 1, 1 - sig) + mp.psi(h - 1, sig))
         for h in range(1, r)]
    Ep = bell_E([u[0] + 2j * mp.pi * k] + u[1:], r - 1)
    Em = bell_E([u[0] - 2j * mp.pi * k] + u[1:], r - 1)
    return (mp.expjpi(k * sig) * Ep + mp.expjpi(-k * sig) * Em) / 2, u

for sig in (mp.mpc('0.3', '0.05'), mp.mpf('0.65'), mp.mpc('0.6', '-0.15')):
    c, s, co = mp.cot(mp.pi * sig), mp.sin(mp.pi * sig), mp.cos(mp.pi * sig)
    B40, u4 = B(4, 0, sig)
    B41, _ = B(4, 1, sig)
    B42, _ = B(4, 2, sig)
    B30, u3 = B(3, 0, sig)
    B31, _ = B(3, 1, sig)
    el = [-c, c ** 2 + mp.mpf(4) / 3, -2 * c * (1 + c ** 2)]
    print('sigma=%s' % mp.nstr(sig, 4))
    print('  u_h/(r pi^h) vs elementary: %.1e' % float(max(abs(u4[h] / (4 * mp.pi ** (h + 1)) - el[h]) for h in range(3))))
    print('  B40 %.1e  B41 %.1e  B42 %.1e' % (float(abs(B40 / (-4 * mp.pi ** 3 * c * (5 * c ** 2 + 3)) - 1)),
                                           float(abs(B41 / (-4 * mp.pi ** 3 * (5 * c ** 2 + 1) / s) - 1)),
                                           float(abs(B42 / (-20 * mp.pi ** 3 * co / s ** 3) - 1))))
    print('  B30 %.1e  B31 %.1e' % (float(abs(B30 / (2 * mp.pi ** 2 * (1 + 2 * co ** 2) / s ** 2) - 1)),
                                    float(abs(B31 / (6 * mp.pi ** 2 * co / s ** 2) - 1))))
    # explicit W4 bracket: -[N/(pi s)]^4 sum B c = 4N^4/(pi s^7)[...] <=> B_{4,0} = -4 pi^3 co(3+2co^2)/s^3 etc.
    print('  W4-explicit weights: %.1e %.1e %.1e' % (
        float(abs(B40 / (-4 * mp.pi ** 3 * co * (3 + 2 * co ** 2) / s ** 3) - 1)),
        float(abs(B41 / (-4 * mp.pi ** 3 * (1 + 4 * co ** 2) / s ** 3) - 1)),
        float(abs(B42 / (-20 * mp.pi ** 3 * co / s ** 3) - 1))))
