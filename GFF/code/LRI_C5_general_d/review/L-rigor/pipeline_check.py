#!/usr/bin/env python3
"""Review L-rigor: Theorem 6 as printed (my coefficient transcription from coeff_check.printed) times the five
Horn values/derivatives of L/L_general.py (inventory), vs C63d's independent spectral references; plus the
three-node W4 off the centre (b = d/2 +- 0.05/0.03) vs C63d off-diagonal references. Mac, 25 digits."""
import json, os, sys, time
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'L'))
sys.path.insert(0, HERE)
from L_general import inventory, LP4  # noqa
from coeff_check import printed  # noqa
DPS = 25
mp.mp.dps = DPS
ref = json.load(open(os.path.join(HERE, '..', '..', 'references', 'reference_values.json')))['values']
for dstr in sys.argv[1:] or ['1.25']:
    t0 = time.time()
    with mp.workdps(DPS + 15):
        d = mp.mpf(dstr)
        inv = inventory(dstr, DPS)
        val, der = printed(d)
        P4 = mp.fsum(val[k] * mp.re(inv[k][0]) for k in val)
        L = mp.fsum(der[k] * mp.re(inv[k][0]) + val[k] * mp.re(inv[k][1]) for k in val)
    R = ref['d=' + dstr]
    mp.mp.dps = 50
    rP, rL = mp.mpf(R['P4']['value']), mp.mpf(R['L']['value'])
    print('d=%s  P4 rel.dev %s   L rel.dev %s   [%.1fs]' % (dstr, mp.nstr(abs(P4 / rP - 1), 3), mp.nstr(abs(L / rL - 1), 3),
                                                            time.time() - t0))
    mp.mp.dps = DPS
    for od in R['offdiag'][:1]:
        t0 = time.time()
        W4, dW4 = LP4(dstr, DPS, b=od['b'], r=4)
        mp.mp.dps = 50
        print('   offdiag b=%s W4 rel.dev %s [%.1fs]' % (od['b'], mp.nstr(abs(mp.re(W4) / mp.mpf(od['W4']) - 1), 3),
                                                       time.time() - t0))
    mp.mp.dps = DPS
