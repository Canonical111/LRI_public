#!/usr/bin/env python3
"""Review L-rigor, quick Mac numerics (30 digits):
 (a) d=1: L_1 = -(96pi+512log2)N_e - (128pi+640log2)M_e (lp:eq:MN, RESULT) vs eq:KLpsiReflected, with N_e, M_e
     from elliptic quadrature (independent of B_pm), and P4(1) = 256 N_e + 320 M_e = 13B_- - 3B_+ = 2229.522...
 (b) d=3: (2/(pi S^7)) D_L versus C63d's Phat' (L3_final_values.json): expect a difference -8 sqrt2 Y1 + 32 Y2,
     Y_k = N_b^4 c_k = (pi^2/16) c_k (so D_L is C63d's Phat' only up to elementary multiples of values)."""
import json, os
import mpmath as mp
mp.mp.dps = 30
pi, l2 = mp.pi, mp.log(2)
Kk = lambda k: pi / (2 * mp.agm(1, mp.sqrt((1 - k) * (1 + k))))   # K(k)
Kp = lambda k: pi / (2 * mp.agm(1, k))                            # K(k')
Ne = mp.quad(lambda k: Kk(k) * Kp(k), [0, mp.mpf(1) / 2, 1])
Me = mp.quad(lambda k: Kk(k) ** 2, [0, mp.mpf(1) / 2, 1])
G4 = mp.gamma(mp.mpf(1) / 4) ** 4
Bm = G4 * mp.hyper([0.25, 0.25, 0.5, 0.5], [0.75, 0.75, 1], 1)
Bp = 64 * pi ** 4 / G4 * mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
print('(a) N_e quad vs (B- - B+)/32:', mp.nstr(Ne / ((Bm - Bp) / 32) - 1, 3), '  M_e quad vs (B-+B+)/64:', mp.nstr(Me / ((Bm + Bp) / 64) - 1, 3))
P4 = 256 * Ne + 320 * Me
print('    P4(1) = 256Ne+320Me =', mp.nstr(P4, 25), ' vs 2229.5220610709419642945251997485:', mp.nstr(P4 / mp.mpf('2229.5220610709419642945251997485') - 1, 3))
L1 = -(96 * pi + 512 * l2) * Ne - (128 * pi + 640 * l2) * Me
Ad = pi + 4 * l2
L1note = -(3 * Ad - pi) / 6 * (13 * Bm - 3 * Bp) - 2 * pi / 3 * Bm
print('    L_1 (MN) =', mp.nstr(L1, 25), '  vs eq:KLpsiReflected rel.dev', mp.nstr(L1 / L1note - 1, 3))
A, B = 8 * Ne / pi, 8 * Me / pi
DL = mp.sqrt(2) * pi ** 2 / 4 * ((31 * pi / 2 - 8 * l2) * A + (19 * pi - 10 * l2) * B)
S = C = 1 / mp.sqrt(2)
Lgen = -(1 / S ** 8) * ((1 + C) ** 2 * (4 + 9 * C + 8 * C ** 2) * (pi ** 2 / 4) * (A + B) + (1 - C) ** 2 * (4 - 9 * C + 8 * C ** 2) * (pi ** 2 / 4) * (A + B)
                       - 2 * (1 + 6 * C ** 2) * (pi ** 2 / 4) * A) + 2 / (pi * S ** 7) * DL
print('    general X-form with X0=Xh=(pi^2/4)(A+B), XT=(pi^2/4)A and RESULT D_L(1): rel.dev', mp.nstr(Lgen / L1 - 1, 3))
# (b) d = 3
mp.mp.dps = 50
R = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'specialize', 'L3_final_values.json')))['values']
v = {k: mp.mpf(R[k]) for k in ('L3', 'P4', 'X0', 'c0', 'c1', 'c2', 'Phat_prime')}
N4 = pi ** 2 / 16
Y0, Y1, Y2 = (N4 * v[k] for k in ('c0', 'c1', 'c2'))
S, C = 1 / mp.sqrt(2), -1 / mp.sqrt(2)
X0, Xh, XT = Y0 + Y1 + Y2, Y0 - Y1 + Y2, Y0 - Y1 / mp.sqrt(2)
nonder = -(1 / S ** 8) * ((1 + C) ** 2 * (4 + 9 * C + 8 * C ** 2) * X0 + (1 - C) ** 2 * (4 - 9 * C + 8 * C ** 2) * Xh - 2 * (1 + 6 * C ** 2) * XT)
DLpart = v['L3'] - nonder
print('(b) d=3: (2/(pi S^7))D_L =', mp.nstr(DLpart, 20), '  Phat\' =', mp.nstr(v['Phat_prime'], 20))
print('    difference - (-8 sqrt2 Y1 + 32 Y2) =', mp.nstr(DLpart - v['Phat_prime'] - (-8 * mp.sqrt(2) * Y1 + 32 * Y2), 3))
print('    check: 4 pi P4 - 2 pi^2 X0 + Phat\' - L3 =', mp.nstr(4 * pi * v['P4'] - 2 * pi ** 2 * v['X0'] + v['Phat_prime'] - v['L3'], 3))
