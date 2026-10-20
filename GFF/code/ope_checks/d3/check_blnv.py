#!/usr/bin/env python3
"""C63d, OPE review 2026-10-16: a^(2), a^(3) of the package at d=2,3 against the explicit values of
Behan-Lauria-Nocchi-van Vliet, arXiv:2311.02742v6, eq. (3.36) (label mean-field-1pt-num in its source).
Usage: python3 check_blnv.py OUT.json"""
import json, sys
import mpmath as mp
mp.mp.dps = 40
res = {}
def pkg(d):
    q = mp.mpf(d) / 4
    a2 = -mp.gamma(1 - q) * mp.gamma(2 * q)**3 / (54 * mp.gamma(1 + q) * mp.gamma(4 * q))
    A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
    B0 = mp.psi(0, -q) - mp.psi(0, q)
    return a2, a2 * (mp.mpf(4) / 3 * A - B0 / 4)
blnv = {2: (mp.mpf(-1) / 27, mp.mpf(1) / 54 - 8 * mp.log(4) / 81),
        3: (-mp.pi**2.5 / (576 * mp.sqrt(2) * mp.gamma(mp.mpf(7) / 4)**2),
            4 * mp.sqrt(2 * mp.pi) / 6075 * (13 * mp.pi - 28 - 64 * mp.log(2)) * mp.gamma(mp.mpf(9) / 4)**2)}
for d in (2, 3):
    for n, (x, y) in enumerate(zip(pkg(d), blnv[d])):
        ok = abs(x - y) < mp.mpf('1e-35')
        res[f'd={d} a^({n + 2})'] = {'package': mp.nstr(x, 25), 'BLNV_eq_3.36': mp.nstr(y, 25), 'pass': bool(ok)}
        print('PASS' if ok else 'FAIL', d, n + 2, mp.nstr(x, 20), mp.nstr(y, 20))
json.dump(res, open(sys.argv[1], 'w'), indent=1)
sys.exit(0 if all(v['pass'] for v in res.values()) else 1)
