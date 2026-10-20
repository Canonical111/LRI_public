#!/usr/bin/env python3
"""Z_d, 3Q_d, dW3/db from a b-circle run of C63d's independent spectral code hp_general_d.py (part b):
Taylor coefficients of W_3(d; d/2 + rho e^{i theta}) (M points, conjugate symmetry), Z = 2 a_2 / 9.
usage: combine_spec.py spec_b_X.json [...]   -> prints and writes spec_refs.json"""
import json
import sys
import mpmath as mp


def combine(fn):
    D = json.load(open(fn))
    mp.mp.dps = int(D['dps']) + 10
    M = D['M']
    h = M // 2
    v = {int(k): mp.mpmathify(x[0].replace(' ', '')) for k, x in D['values'].items() if int(k) >= 0}
    W3 = [v[k] if k <= h else mp.conj(v[M - k]) for k in range(M)]
    rho = mp.mpf(D['rho'])
    coef = lambda j: mp.fsum(W3[k] * mp.expj(-2 * mp.pi * j * k / M) for k in range(M)) / M / rho ** j
    return dict(d=D['d'], dps=D['dps'], M=M, rho=D['rho'], threeQ=mp.nstr(mp.re(coef(0)), 50),
                dW3db=mp.nstr(coef(1), 5), Z=mp.nstr(mp.re(2 * coef(2) / 9), 50))


if __name__ == '__main__':
    out = {}
    for fn in sys.argv[1:]:
        r = combine(fn)
        out[r['d']] = r
        print(r)
    json.dump(out, open('spec_refs.json', 'w'), indent=1)
