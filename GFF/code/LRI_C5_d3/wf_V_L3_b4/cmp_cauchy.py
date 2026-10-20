"""Compare the closed-form (Dougall) b4(b) and d/db[N^{1/2} b4] at b=3/2 (170 dps) with the author's
Cauchy-circle Taylor data for B = pref^2 b = (pi/4) N^{1/2} b in pA_dps170.json and pB_dps170.json."""
import sys, mpmath as mp
sys.path.insert(0, '<PROJECT>/LRI_C5_d3/wf_L3')
from load import load
for fn in ['pA_dps170.json', 'pB_dps170.json']:
    d, V, D, D2, cen = load('<PROJECT>/LRI_C5_d3/wf_L3/' + fn, 0)
    mp.mp.dps = 180
    def closed(b):
        al = b / 4 - mp.mpf(1) / 4
        return mp.sin(2 * mp.pi * al) ** 3 * al * mp.gamma(2 * al) ** 4 * mp.gamma(1 - 4 * al) / (mp.gamma(1 + 2 * al) * mp.gamma(1 - 2 * al) ** 3)
    Bf = lambda b: (mp.pi / 4) * (mp.gamma(mp.mpf(3) / 2 - b / 2) / mp.gamma(b / 2)) ** 2 * closed(b)
    b0 = mp.mpf(3) / 2
    t = mp.taylor(Bf, b0, 2)
    # data are Taylor in gamma = 3/2 - b/2: d/db = -(1/2) d/dgamma, d2/db2 = (1/4) d2/dgamma2
    print(fn, 'N', d['N'], 'K', d['K'], 'M', d['M'], 'rho', d['rho'])
    print('  B value    rel diff', mp.nstr((V['B'] - t[0]) / t[0], 3))
    print('  dB/db      rel diff', mp.nstr((-D['B'] / 2 - t[1]) / t[1], 3))
    print('  d2B/db2/2  rel diff (D2 is f''(gamma), so coeff = D2/8)', mp.nstr((D2['B'] / 8 - t[2]) / t[2], 3))
    print('  (N^1/2 b)\'/b - (pi/2-log2) from closed form', mp.nstr(t[1] / t[0] - (mp.pi / 2 - mp.log(2)), 3))
