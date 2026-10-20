#!/usr/bin/env python3
"""Per-function check (session L): the jet b-derivatives of the five Horn functions hx, h1, hh, s0, s1 at b = d/2
against Cauchy-circle derivatives of their plain (non-jet) values on |b - d/2| = rho (consistency of the jet
implementation for each function separately; not an independent evaluation).
usage: check_func_derivs.py OUT.json DPS d1,d2,... [M] [rho_frac]
"""
import sys
import os
import json
import time
import mpmath as mp
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from L_general import Wheel3, bmax  # noqa: E402
from jet import J, val, der  # noqa: E402

GUARD = 15
NAMES = ('hx', 'h1', 'hh', 's0', 's1')


def funcs(w):
    half = mp.mpf(1) / 2
    return dict(hx=w.hR(w.x)[0], h1=w.hR(mp.mpf(1))[0], hh=w.hR(half)[0], s0=w.s0()[0], s1=w.s1()[0])


def task(args):
    dstr, k, M, rf, dps = args
    mp.mp.dps = dps + GUARD
    d = mp.mpmathify(dstr)
    b0 = d / 2
    rho = rf * min(b0, bmax(4, d) - b0)
    if k < 0:
        f = funcs(Wheel3(4, d, J(b0, 1)))
        return (dstr, k), {n: [mp.nstr(val(f[n]), dps + 5), mp.nstr(der(f[n]), dps + 5)] for n in NAMES}
    b = b0 + rho * mp.expjpi(2 * (k + mp.mpf(1) / 2) / M)
    f = funcs(Wheel3(4, d, b))
    return (dstr, k), {n: mp.nstr(f[n], dps + 5) for n in NAMES}


if __name__ == '__main__':
    out, dps, ds = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(',')
    M = int(sys.argv[4]) if len(sys.argv) > 4 else 32
    rf = mp.mpmathify(sys.argv[5]) if len(sys.argv) > 5 else mp.mpf('0.05')
    tasks = [(dstr, k, M, rf, dps) for dstr in ds for k in [-1] + list(range(M))]
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 4))
    st = time.time()
    with Pool(workers) as pool:
        res = dict(pool.map(task, tasks, chunksize=1))
    mp.mp.dps = dps + GUARD
    json.dump({'%s|%d' % k: v for k, v in res.items()}, open(out + '.raw', 'w'))
    result = dict(dps=dps, M=M, rho_frac=str(rf), results={})
    for dstr in ds:
        d = mp.mpmathify(dstr)
        b0 = d / 2
        rho = rf * min(b0, bmax(4, d) - b0)
        jet = res[(dstr, -1)]
        ent = {}
        for n in NAMES:
            vals = [mp.mpmathify(res[(dstr, k)][n]) for k in range(M)]
            c1 = mp.fsum(vals[k] * mp.expjpi(-2 * (k + mp.mpf(1) / 2) / M) for k in range(M)) / M / rho
            c0 = mp.fsum(vals) / M
            jv, jd = mp.mpmathify(jet[n][0]), mp.mpmathify(jet[n][1])
            # relative deviation; absolute where the derivative vanishes identically (d=1: s1 = 1)
            ent[n] = dict(value=jet[n][0], deriv=jet[n][1], value_dev=mp.nstr(abs(c0 - jv) / abs(jv), 3),
                          deriv_dev=mp.nstr(abs(c1 - jd) / max(abs(jd), 1), 3))
            print('d=%s %s  f=%s  f\'=%s   circle: value dev %s  deriv dev %s' % (
                dstr, n, mp.nstr(mp.re(jv), 20), mp.nstr(mp.re(jd), 20), ent[n]['value_dev'], ent[n]['deriv_dev']))
        result['results'][dstr] = ent
    result['seconds'] = time.time() - st
    json.dump(result, open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))
