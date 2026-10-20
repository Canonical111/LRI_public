#!/usr/bin/env python3
"""Spot checks of printed gdr:special and gdk numbers with the dumped samples (dps 60)."""
import json, os, sys
import mpmath as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2e import basis, gdr_DL, gdk_K, jet_laurent, GDK_TABLE, ROOT, rel
from consts import note_values
mp.mp.dps = 60
pi, G, l2 = mp.pi, mp.catalan, mp.log(2)
S = json.load(open('samples_dps60.json'))['values']
nv, ex = note_values(60)
mp.mp.dps = 60
Bm, Bp = ex['Bm'], ex['Bp']
Me, Ne = (Bm + Bp) / 64, (Bm - Bp) / 32
cA, cB = 8 * Ne / pi, 8 * Me / pi
cAx, cBx = 2 * pi * cB - 2 * l2 * cA, 3 * pi / 2 * cA - 2 * l2 * cB   # gdr:landen, x-derivatives
f = lambda k, d: mp.mpf(S[d][k])
out = []
# ---- d = 2
d = '2'
out.append(('d2 X_T = A^2', rel(f('XT', d), cA ** 2)))
out.append(('d2 X_0 = (A+B)^2', rel(f('X0', d), (cA + cB) ** 2)))
out.append(('d2 X_1/2 = (A-B)^2', rel(f('Xh', d), (cA - cB) ** 2)))
out.append(('d2 X_0\' = (A+B)(A_x+B_x)', rel(f('dX0', d), (cA + cB) * (cAx + cBx))))
out.append(('d2 X_1/2\' = (A-B)(A_x-B_x)', rel(f('dXh', d), (cA - cB) * (cAx - cBx))))
out.append(('d2 X_T\' = A A_x - pi A B (derived here)', rel(f('dXT', d), cA * cAx - pi * cA * cB)))
L2 = -(6 * cA ** 2 + 8 * cB ** 2) + 2 / pi * (f('dX0', d) - f('dXh', d))
out.append(('d2 L_2 sample line vs -2log2 P4(2)', rel(L2, -2 * l2 * nv['2']['P4'])))
out.append(('d2 -16log2 AB/pi vs L2', rel(-16 * l2 * cA * cB / pi, nv['2']['L'])))
out.append(('d2 |M3|,|M3\'|,|M3\'\'|', max(abs(mp.mpf(x)) for x in S[d]['M3'])))
dixon = lambda a: mp.gamma(1 + a / 2) * mp.gamma(1 - 3 * a / 2) / (mp.gamma(1 + a) * mp.gamma(1 - a / 2) ** 2 * mp.gamma(1 - a))  # Dixon 3F2(a,a,a;1,1;1)
F2 = lambda b: dixon(b / 2) ** 2
with mp.workdps(70):
    T3d2 = [F2(mp.mpf(1)), mp.diff(F2, mp.mpf(1), 1), mp.diff(F2, mp.mpf(1), 2)]
out.append(('d2 T3 = Dixon^2 (val, d1, d2)', max(rel(T3d2[i], mp.mpf(S[d]['T3'][i])) for i in range(3))))
# ---- d = 1
d = '1'
out.append(('d1 X_0 - X_1/2 (abs)', abs(f('X0', d) - f('Xh', d))))
out.append(('d1 X_0\' - X_1/2\' (abs)', abs(f('dX0', d) - f('dXh', d))))
out.append(('d1 |c0hat jets| (abs)', max(abs(mp.mpf(x)) for x in S[d]['c0'])))
out.append(('d1 P4 = 32pi A + 40 pi B', rel(32 * pi * cA + 40 * pi * cB, nv['1']['P4'])))
out.append(('d1 L1 = -2(pi+log2)P4+52pi^2A+64pi^2B', rel(-2 * (pi + l2) * nv['1']['P4'] + 52 * pi ** 2 * cA + 64 * pi ** 2 * cB, nv['1']['L'])))
out.append(('d1 L1 = -(96pi+512log2)Ne-(128pi+640log2)Me', rel(-(96 * pi + 512 * l2) * Ne - (128 * pi + 640 * l2) * Me, nv['1']['L'])))
C1 = mp.cos(pi / 4)
DL1 = gdr_DL(C1, f('dX0', d), f('dXh', d), f('dXT', d))
out.append(('d1 D_L = sqrt2(5X0\'-XT\')', rel(DL1, mp.sqrt(2) * (5 * f('dX0', d) - f('dXT', d)))))
out.append(('d1 D_L elementary form', rel(DL1, mp.sqrt(2) * pi ** 2 / 4 * ((31 * pi / 2 - 8 * l2) * cA + (19 * pi - 10 * l2) * cB))))
F1 = lambda b: dixon(b)
with mp.workdps(70):
    T3d1 = [F1(mp.mpf(1) / 2), mp.diff(F1, mp.mpf(1) / 2, 1), mp.diff(F1, mp.mpf(1) / 2, 2)]
out.append(('d1 T3 = 3F2(b,b,b;1,1;1) (val,d1,d2)', max(rel(T3d1[i], mp.mpf(S[d]['T3'][i])) for i in range(3))))
out.append(('d1 Z1 = 4pi^2/3 T3\'\' vs QH', rel(4 * pi ** 2 / 3 * mp.mpf(S[d]['T3'][2]), nv['1']['Z'])))
# ---- d = 3
d = '3'
def c0d3(b):
    g = (3 - b) / 2
    Nb = mp.gamma(mp.mpf(3) / 2) * mp.gamma(g) / mp.gamma(b / 2)
    return -Nb ** 3 * pi ** 5 * mp.gamma(3 * g - 2) / mp.gamma(g) ** 9
b0 = mp.mpf(3) / 2
cj = [c0d3(b0), mp.diff(c0d3, b0, 1), mp.diff(c0d3, b0, 2)]
out.append(('d3 c0hat Gamma form (val,d1,d2)', max(rel(cj[i], mp.mpf(S[d]['c0'][i])) for i in range(3))))
Sd, Cd = mp.sin(3 * pi / 4), mp.cos(3 * pi / 4)
zm = (pi * (1 + Cd ** 2) / Sd ** 5 * cj[0] - 4 * Cd / Sd ** 4 * cj[1] + 4 / (pi * Sd ** 3) * cj[2]) / 9
out.append(('d3 zero-mode part = sqrt2(4pi+32G/pi) c0', rel(zm, mp.sqrt(2) * (4 * pi + 32 * G / pi) * cj[0])))
Z3 = 4 * pi ** 2 / 3 * mp.mpf(S[d]['T3'][2]) - (4 * G + pi ** 2 / 2) * mp.gamma(0.25) ** 10 / (16 * pi ** 3.5)
out.append(('d3 Z3 closed-zero-mode form vs note Z3', rel(Z3, nv['3']['Z'])))
DL3 = gdr_DL(Cd, f('dX0', d), f('dXh', d), f('dXT', d))
out.append(('d3 2/(pi S^7) D_L (printed -1332.48)', 2 / (pi * Sd ** 7) * DL3))
# ---- gdk:E2 from stored jets, and the deviations table
for dk in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    lau, js = jet_laurent(dk)
    q = mp.mpf(dk) / 4
    out.append(('gdk:E2 tE2 - 1.5 psi2(d/4) at d=' + dk, rel(mp.mpf(js['tE2']), mp.mpf(3) / 2 * mp.psi(2, q))))
mb = json.load(open(os.path.join(ROOT, 'K_general', 'position_space', 'K_d_values_mb_D100.json')))['values']
refs = json.load(open(os.path.join(ROOT, 'references', 'reference_values.json')))['values']
for dk in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    lau, js = jet_laurent(dk)
    q = mp.mpf(dk) / 4
    Kmb = mp.mpf(mb[dk]['K'])
    Kj = gdk_K(q, lau[3])
    s = 'gdk table: five-node (my Cauchy + gdk:Kr3) vs MB, d=%s: %s ; their K_d vs MB: %s' % (
        dk, mp.nstr((Kj - Kmb) / Kmb, 2), mp.nstr((mp.mpf(js['K_d']) - Kmb) / Kmb, 2))
    if 'd=' + dk in refs:
        s += ' ; spectral ref vs MB: %s' % mp.nstr((mp.mpf(refs['d=' + dk]['K']['value']) - Kmb) / Kmb, 2)
    out.append((s, mp.mpf(0)))
for k, v in out:
    print('%-62s %s' % (k, mp.nstr(v, 4)))
