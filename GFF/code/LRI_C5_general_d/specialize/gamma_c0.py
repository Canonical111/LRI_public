#!/usr/bin/env python3
"""Is the normalized r = 3 zero mode c0hat(d; d/2) = N_b^3 c_{3,0} a Gamma product at non-integer d?
(It is 0 at d = 1, a Gamma product at d = 2 and d = 3.)  PSLQ of log|c0hat| against
{log pi, log 2, log 5, log phi, log Gamma(1/5), log Gamma(2/5)}, which spans the logs of all Gamma values at
multiples of 1/10, of pi, and of the trigonometric numbers at multiples of pi/10 (d = 4/5, 8/5, 12/5, 16/5).
Control: the same test for Q_d.  Usage: python3 gamma_c0.py dps"""
import json
import os
import sys
from multiprocessing import Pool

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'Z'))
DPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
DIMS = ['4/5', '8/5', '12/5', '16/5']


def run(dstr):
    import Z_general as ZG
    mp.mp.dps = DPS
    r = ZG.Z(dstr, DPS + 10, full=True)
    return dstr, [str(mp.re(r['c0hat'][0])), str(r['Q']), str(mp.re(r['R'][0]))]


def main():
    with Pool(len(DIMS)) as p:
        res = dict(p.map(run, DIMS))
    mp.mp.dps = DPS
    tol = mp.mpf(10) ** (-(DPS - 10))
    phi = (1 + mp.sqrt(5)) / 2
    basis = [mp.log(mp.pi), mp.log(2), mp.log(5), mp.log(phi), mp.loggamma(mp.mpf(1) / 5), mp.loggamma(mp.mpf(2) / 5)]
    out = {}
    for dstr in DIMS:
        c0, Q, R = [mp.mpf(x) for x in res[dstr]]
        row = dict(c0hat=mp.nstr(c0, DPS - 5), Q=mp.nstr(Q, DPS - 5), R=mp.nstr(R, DPS - 5))
        for name, v in (('c0hat', c0), ('Q', Q), ('R', R)):
            rel = mp.pslq([mp.log(abs(v))] + basis, maxcoeff=10 ** 12, maxsteps=10 ** 7, tol=tol)
            row['pslq_log_' + name] = str(rel)
            if rel is not None:
                row['pslq_log_%s_maxcoeff' % name] = max(abs(c) for c in rel)
        out[dstr] = row
        print(dstr, json.dumps(row, indent=1), flush=True)
    json.dump(out, open(os.path.join(_HERE, 'results', 'gamma_c0_dps%d.json' % DPS), 'w'), indent=1)


if __name__ == '__main__':
    main()
