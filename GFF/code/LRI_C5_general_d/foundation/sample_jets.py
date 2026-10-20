#!/usr/bin/env python3
"""Numerical test of the jet formula (Corollary, eq. jets of general_b_periodization.tex):
   W_r(d;b) = sum_j f_j(b) Xi_r(t_j;b),   f_j = N_b^r omega_{r,j}(b)  (elementary),  t_j b-independent;
   L_d = sum_j [f_j' Xi_j + f_j Xi_j']_{b=d/2}          (r = 4)
   Z_d = (1/9) sum_j [f_j'' Xi_j + 2 f_j' Xi_j' + f_j Xi_j'']_{b=d/2}   (r = 3)
Xi_j^{(k)} = d^k/db^k Xi_r(t_j;b) at fixed t_j, from Cauchy circles in b (radius below the distance to the
removable block singularities sigma + t_j in Z).  Also records the five blocks and their b-derivatives at the
nodes, for checking analytic parameter-derivative formulas.  Reduced node set N = 2r-3 (top-mode theorem).
usage: sample_jets.py OUT.json DPS d1,d2,...      (r = 3 and 4 for each d)"""
import sys
import os
import json
import time
import mpmath as mp
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wheel_general_b import Wheel, bmax  # noqa: E402

GUARD = 15
MC = 48


def nodes(r, d):
    Nn = 2 * r - 3
    q = mp.mpmathify(d) / 4
    eta = 1 / (8 * mp.pi * r)
    return [-q / 2 + mp.mpf(j) / Nn + 1j * eta for j in range(Nn)]


def f_weights(r, d, b, ts):
    """f_j(b) = N_b^r omega_{r,j}(b), omega = -(1/N) sum_{|m|<=r-2} e_m(b) e^{-2 pi i m t_j}."""
    w = Wheel(r, d, b)
    e = w.exp_weights()
    Nn = len(ts)
    Nr = w.Nb() ** r
    return [-Nr / Nn * mp.fsum(e[m] * mp.exp(-2j * mp.pi * m * t) for m in range(-(r - 2), r - 1)) for t in ts]


def radius(r, d, t):
    """one sixth of the distance from b0 = d/2 to the nearest singularity of b -> Xi_r(t;b) or of its blocks:
    sigma + t in Z (removable in Xi, poles of the blocks), b = 0, b_spec, and b = b_max, where the continued Horn
    values (hence the individual samples, though not W) are singular."""
    d = mp.mpmathify(d)
    b0 = d / 2
    dist = min(abs(b0 - (2 * n - 2 * t)) for n in range(-3, 4))
    return min(dist, b0, (d - max(d, 1) / mp.mpf(r)) - b0, bmax(r, d) - b0) / 6


def task(args):
    r, d, j, k, dps = args
    mp.mp.dps = dps + GUARD
    ts = nodes(r, d)
    t = ts[j]
    rho = radius(r, d, t)
    b = mp.mpmathify(d) / 2 + rho * mp.expjpi(2 * (k + mp.mpf(1) / 2) / MC)
    w = Wheel(r, d, b)
    val, blocks = w.Xi(t, parts=True)
    Dr = w.Db(t) ** r
    return (r, d, j, k), dict(Xi=mp.nstr(val, dps + 10), Dr=mp.nstr(Dr, dps + 10),
                              blocks={kk: mp.nstr(v, dps + 10) for kk, v in blocks.items()})


if __name__ == '__main__':
    out, dps, ds = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(',')
    mp.mp.dps = dps + GUARD
    tasks = [(r, d, j, k, dps) for d in ds for r in (3, 4) for j in range(2 * r - 3) for k in range(MC)]
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 4))
    st = time.time()
    with Pool(workers) as pool:
        res = dict(pool.map(task, tasks, chunksize=1))
    result = dict(dps=dps, MC=MC, results={})
    refs = {}
    for d in ds:
        for r in (3, 4):
            ts = nodes(r, d)
            b0 = mp.mpmathify(d) / 2
            # elementary weights and derivatives (numerical differentiation of an elementary function)
            fj = [lambda b, j=j: f_weights(r, d, b, ts)[j] for j in range(len(ts))]
            F0 = [f(b0) for f in fj]
            F1 = [mp.diff(f, b0, 1) for f in fj]
            F2 = [mp.diff(f, b0, 2) for f in fj]
            X = []
            per_block = []
            for j, t in enumerate(ts):
                rho = radius(r, d, t)
                vals = [mp.mpmathify(res[(r, d, j, k)]['Xi']) for k in range(MC)]
                ph = [mp.expjpi(-2 * (k + mp.mpf(1) / 2) / MC) for k in range(MC)]
                c = [mp.fsum(vals[k] * ph[k] ** n for k in range(MC)) / MC / rho ** n for n in range(3)]
                X.append((c[0], c[1], 2 * c[2]))
                bl = {}
                for name in ('A0', 'Ap', 'A0m', 'Apm', 'C'):
                    bv = [mp.mpmathify(res[(r, d, j, k)]['blocks'][name]) for k in range(MC)]
                    cb = [mp.fsum(bv[k] * ph[k] ** n for k in range(MC)) / MC / rho ** n for n in range(3)]
                    bl[name] = [mp.nstr(cb[0], dps), mp.nstr(cb[1], dps), mp.nstr(2 * cb[2], dps)]
                per_block.append(dict(t=mp.nstr(t, dps), rho=mp.nstr(rho, 6), blocks_and_b_derivs=bl,
                                      Xi=[mp.nstr(x, dps) for x in X[-1]]))
            W0 = mp.fsum(F0[j] * X[j][0] for j in range(len(ts)))
            W1 = mp.fsum(F1[j] * X[j][0] + F0[j] * X[j][1] for j in range(len(ts)))
            W2 = mp.fsum(F2[j] * X[j][0] + 2 * F1[j] * X[j][1] + F0[j] * X[j][2] for j in range(len(ts)))
            result['results']['r%d_d%s' % (r, d)] = dict(
                nodes=per_block, f=[mp.nstr(x, dps) for x in F0], f1=[mp.nstr(x, dps) for x in F1],
                f2=[mp.nstr(x, dps) for x in F2], W=mp.nstr(W0, dps), dW=mp.nstr(W1, dps), d2W=mp.nstr(W2, dps),
                L_if_r4=mp.nstr(W1, dps), Z_if_r3=mp.nstr(W2 / 9, dps))
            print('r=%d d=%s  W=%s  dW/db=%s  d2W/db2/9=%s' % (r, d, mp.nstr(mp.re(W0), 25), mp.nstr(W1, 25),
                                                            mp.nstr(W2 / 9, 25)), flush=True)
    result['seconds'] = time.time() - st
    json.dump(result, open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))
