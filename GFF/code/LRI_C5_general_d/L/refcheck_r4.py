#!/usr/bin/env python3
"""Independent spectral reference for P4(d) and L_d at extra dimensions (session L), using C63d's spectral code
(LRI_C5_general_d/refvals/hp_general_d.py: finite spins by quadrature with an analytic large-nu tail, spin tail by
Stirling + generic-d multiplicity expansion + Euler-Maclaurin Hurwitz zeta).  r = 4 only (at d = 0.6 the r = 3
spectral sum does not converge at b = d/2).  L_d = first Taylor coefficient of b -> W_4(d;b) on a Cauchy circle.
This code shares nothing with L_general.py.
usage: refcheck_r4.py OUT.json d DPS SPINS KMAX M RHO
"""
import sys
import os
import json
import time
import mpmath as mp
from multiprocessing import Pool

os.environ['HPG_NUTAIL'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hp_general_d as hp  # noqa: E402

CFG = {}


def job(k):
    c = CFG
    mp.mp.dps = c['dps']
    d = mp.mpf(c['d'])
    breaks = [0, mp.mpf('0.3'), mp.mpf('1.5'), 6, 40, mp.inf]
    b = d / 2 + mp.mpf(c['rho']) * mp.expjpi(2 * (k + mp.mpf(1) / 2) / c['M'])
    return k, str(hp.wheel(4, b, d, c['spins'], c['kmax'], breaks))


def init(c):
    CFG.update(c)


if __name__ == '__main__':
    out = sys.argv[1]
    c = dict(d=sys.argv[2], dps=int(sys.argv[3]), spins=int(sys.argv[4]), kmax=int(sys.argv[5]), M=int(sys.argv[6]),
             rho=sys.argv[7])
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 8))
    st = time.time()
    ks = list(range(c['M'] // 2))          # conjugate symmetry W(conj b) = conj W(b)
    with Pool(workers, initializer=init, initargs=(c,)) as pool:
        res = dict(pool.map(job, ks, chunksize=1))
    mp.mp.dps = c['dps']
    M = c['M']
    vals = [mp.mpmathify(res[k]) for k in ks]
    full = vals + [mp.conj(vals[M - 1 - k]) for k in range(M // 2, M)]
    rho = mp.mpf(c['rho'])
    coef = [mp.fsum(full[k] * mp.expjpi(-2 * j * (k + mp.mpf(1) / 2) / M) for k in range(M)) / M / rho ** j
            for j in range(3)]
    print('d', c['d'], 'P4 =', mp.nstr(mp.re(coef[0]), c['dps'] - 5), ' L =', mp.nstr(mp.re(coef[1]), c['dps'] - 5),
          ' [%.0f s]' % (time.time() - st))
    json.dump(dict(c, seconds=time.time() - st, P4=mp.nstr(mp.re(coef[0]), c['dps']), L=mp.nstr(mp.re(coef[1]), c['dps']),
                   a2=mp.nstr(mp.re(coef[2]), c['dps']), values={str(k): res[k] for k in ks}), open(out, 'w'), indent=1)
