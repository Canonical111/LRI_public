#!/usr/bin/env python3
"""Does the frozen-weight derivative of L_d reduce at a non-integer dimension?  At d = 4/3 and 8/3 (q = 1/3, 2/3)
every elementary coefficient of the five-Horn formula lies in Q(sqrt3)[pi, 1/pi, log 2, log 3].  Test whether
L_d is a combination of the three samples XT, X0, Xh with coefficients in
  {1, sqrt3} x {1, log2/pi, log3/pi}   (the shape of the d = 1, 2 reductions, where Dfr is pi- and log2-linear in
  the samples),
by PSLQ at the full working precision.  Usage: python3 pslq_L.py dps"""
import json
import os
import sys
from multiprocessing import Pool

import mpmath as mp

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'L'))
DPS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
DIMS = ['4/3', '8/3']


def run(dstr):
    from L_general import LP4
    from jet import val
    mp.mp.dps = DPS
    P4, L, sm = LP4(dstr, DPS + 10, full=True)
    return dstr, [str(mp.re(x)) for x in (P4, L, val(sm['Xt']), val(sm['X0']), val(sm['Xh']))]


def main():
    with Pool(2) as p:
        res = dict(p.map(run, DIMS))
    mp.mp.dps = DPS
    tol = mp.mpf(10) ** (-(DPS - 15))
    out = {}
    s3 = mp.sqrt(3)
    coeffs = [('1', 1), ('s3', s3), ('l2/pi', mp.log(2) / mp.pi), ('l3/pi', mp.log(3) / mp.pi),
              ('s3 l2/pi', s3 * mp.log(2) / mp.pi), ('s3 l3/pi', s3 * mp.log(3) / mp.pi)]
    for dstr in DIMS:
        P4, L, Xt, X0, Xh = [mp.mpf(x) for x in res[dstr]]
        names, vec = ['L'], [L]
        for sn, sv in (('XT', Xt), ('X0', X0), ('Xh', Xh)):
            for cn, cv in coeffs:
                names.append('%s*%s' % (cn, sn))
                vec.append(cv * sv)
        row = dict(P4=mp.nstr(P4, DPS - 5), L=mp.nstr(L, DPS - 5), XT=mp.nstr(Xt, DPS - 5), X0=mp.nstr(X0, DPS - 5),
                   Xh=mp.nstr(Xh, DPS - 5), basis=names)
        # stability test: a genuine relation is found with the same coefficients at both precisions
        for lab, digs in (('hi', DPS - 15), ('lo', DPS - 40)):
            with mp.workdps(digs):
                v2 = [+v for v in vec]
                rel = mp.pslq(v2, maxcoeff=10 ** 15, maxsteps=10 ** 7, tol=mp.mpf(10) ** (-(digs - 5)))
            row['pslq_' + lab] = str(rel)
            if rel is not None:
                row['maxcoeff_' + lab] = max(abs(c) for c in rel)
                row['residual_' + lab] = mp.nstr(mp.fsum(c * v for c, v in zip(rel, vec)), 5)
        # control: P4 itself must be found (it is a sqrt3/pi-rational combination of the samples)
        vecP = [P4] + [cv * sv / mp.pi for sv in (Xt, X0, Xh) for cv in (1, s3)]
        row['control_P4'] = str(mp.pslq(vecP, maxcoeff=10 ** 15, maxsteps=10 ** 7, tol=tol))
        out[dstr] = row
        print(dstr, json.dumps(row, indent=1), flush=True)
    json.dump(out, open(os.path.join(_HERE, 'results', 'pslq_L_dps%d.json' % DPS), 'w'), indent=1)


if __name__ == '__main__':
    main()
