#!/usr/bin/env python3
"""d = 3 dictionary between the generic three-node formula (L/L_general.py) and C63d's L3 constants
(LRI_C5_d3/wf_L3/L3_final_values.json): Fourier modes c_k, X0, a4 (from c1 = 2 a4 b4 with Dougall's b4),
dH = d/db[N (4c0+5c2)], da = d/db[N^{1/2} a4], N(b) = [Gamma(3/2-b/2)/Gamma(b/2)]^4 = 16 N_b^4/pi^2.
Quick Mac check at 30 digits."""
import json
import os
import sys

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'L'))
from jet import J, val, der  # noqa: E402
from L_general import Wheel3  # noqa: E402

DPS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
mp.mp.dps = DPS
ref = json.load(open(os.path.join(_HERE, 'L3_final_values.json')))['values']
R = {k: mp.mpf(v) for k, v in ref.items()}


def rel(a, b):
    return abs(a - b) / abs(b)


with mp.workdps(DPS + 15):
    b = J(mp.mpf(3) / 2, 1)
    w = Wheel3(4, 3, b)
    Wv, sm = w.W(full=True)
    c0h, c1h, c2h = sm['ck_times_Nr']          # N_b^4 c_k as jets
    Nb4 = val(sm['N']) ** 4
    pi = mp.pi
    k = 16 / pi ** 2                           # N(b) c_k = (16/pi^2) N_b^4 c_k
    c0, c1, c2 = [mp.re(val(c)) / Nb4 for c in (c0h, c1h, c2h)]
    X0 = mp.re(val(sm['Xt'])) / Nb4
    b4 = mp.gamma(mp.mpf(1) / 4) ** 6 / (16 * pi ** (mp.mpf(5) / 2))
    a4 = c1 / (2 * b4)
    dH = k * mp.re(der(4 * c0h + 5 * c2h))
    da = k * mp.re(der(c1h)) / (2 * b4) - (pi / 2 - mp.log(2)) * a4
    P4, L3 = mp.re(val(Wv)), mp.re(der(Wv))
    L3_c63d = 4 * pi * P4 - 2 * pi ** 2 * X0 + 6 * mp.sqrt(2) * pi * (pi - 2 * mp.log(2)) * a4 * b4 \
        - 2 * pi * dH + 12 * mp.sqrt(2) * pi * b4 * da
    for name, v in (('c0', c0), ('c1', c1), ('c2', c2), ('X0', X0), ('a4', a4), ('b4', b4), ('dH', dH), ('da', da),
                    ('P4', P4), ('L3', L3)):
        print('%-4s %-40s rel.dev vs C63d %s' % (name, mp.nstr(v, 30), mp.nstr(rel(v, R[name]), 3)))
    print('C63d L3 formula with our dictionary vs our L3: %s' % mp.nstr(rel(L3_c63d, L3), 3))
