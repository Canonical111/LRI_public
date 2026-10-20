#!/usr/bin/env python3
"""Cauchy-circle engine: b-jets of the five sample blocks of the two-node formula (z_blocks.py) at b = d/2.

For each d the blocks are evaluated at b_k = d/2 + rho exp(i theta_k), theta_k = 2 pi (k + 1/2)/M; conjugate symmetry
(real d) halves the work.  Taylor coefficients a_j = (1/M) sum_k f(b_k) exp(-i j theta_k) / rho^j; derivative
f^(j) = j! a_j.  Aliasing error ~ (rho/R_f)^M with R_f the radius of analyticity of the block (>= 5 rho by the
choice below); roundoff ~ 10^-dps / rho^j.
usage: z_cauchy.py OUT.json DPS M d1,d2,...      (integer d = 1, 2, 3 are passed exactly)
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import mpmath as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import z_blocks as zb  # noqa: E402

GUARD = 15


def parse_d(x):
    """'1','2','3' -> exact int (polynomial multiplicities); 'a/b' -> exact rational; else decimal."""
    if x in ('1', '2', '3'):
        return int(x)
    if '/' in x:
        a, b = x.split('/')
        return mp.mpf(int(a)) / int(b)
    return mp.mpf(x)


def bmax3(d):
    d = mp.mpf(d)
    return min(d * 2 / 3, d - 2 * (d - 1) / 3, d - mp.mpf(1) / 3)


def radius(d):
    d0 = mp.mpf(d)
    b0 = d0 / 2
    R = min(bmax3(d0) - b0, 2 - b0, b0)
    rho = R / 5
    if not isinstance(d, int):
        # stay well away from the removable resonances 3(d-b)/2 in Z of the accelerated sums (real b = d - 2n/3);
        # a resonance exactly at the centre is harmless (the circle avoids it), the next ones are 2/3 away
        rg = 3 * (d0 - b0) / 2
        dists = [abs(rg - n) * 2 / 3 for n in range(0, 8)]
        dists = [x for x in dists if x > mp.mpf(10) ** (-mp.mp.dps // 2)]
        rho = min(rho, min(dists) * mp.mpf('0.6'))
    return rho


def task(args):
    dstr, k, M, dps = args
    mp.mp.dps = dps + GUARD
    d = parse_d(dstr)
    rho = radius(d)
    b = mp.mpf(d) / 2 + rho * mp.expjpi(2 * (k + mp.mpf(1) / 2) / M)
    bl = zb.blocks(d, b)
    return (dstr, k), {n: mp.nstr(bl[n], dps + 10) for n in zb.BLOCKS}


def taylor(vals, M, rho, jmax=2):
    ph = [mp.expjpi(-2 * (k + mp.mpf(1) / 2) / M) for k in range(M)]
    return [mp.fsum(vals[k] * ph[k] ** j for k in range(M)) / M / rho ** j for j in range(jmax + 1)]


def main():
    out, dps, M, ds = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4].split(',')
    mp.mp.dps = dps + GUARD
    tasks = [(dstr, k, M, dps) for dstr in ds for k in range(M // 2)]
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 4))
    st = time.time()
    with Pool(workers) as pool:
        res = dict(pool.map(task, tasks, chunksize=1))
    result = dict(dps=dps, M=M, engine='cauchy', results={})
    for dstr in ds:
        d = parse_d(dstr)
        q = mp.mpf(d) / 4
        rho = radius(d)
        jets = {}
        for n in zb.BLOCKS:
            half = [mp.mpmathify(res[(dstr, k)][n]) for k in range(M // 2)]
            full = half + [mp.conj(half[M - 1 - k]) for k in range(M // 2, M)]
            a = taylor(full, M, rho)
            jets[n] = [a[0], a[1], 2 * a[2]]          # value, first and second derivative
        Rj = [jets['R0'][j] + jets['R1'][j] for j in range(3)]
        Mj = [jets['M0'][j] + jets['M1'][j] + jets['MC'][j] for j in range(3)]
        W0, W1, Z = zb.assemble(q, Rj, Mj)
        Zred, elim = zb.assemble_reduced(q, Rj, Mj)
        Zc0, c0j = zb.zero_mode_form(q, Rj, Mj)
        rec = dict(rho=mp.nstr(rho, 8),
                   blocks={n: [mp.nstr(x, dps) for x in jets[n]] for n in zb.BLOCKS},
                   R=[mp.nstr(x, dps) for x in Rj], Mh=[mp.nstr(x, dps) for x in Mj],
                   W=mp.nstr(W0, dps), dW=mp.nstr(W1, dps), Z=mp.nstr(Z, dps),
                   Z_reduced=mp.nstr(Zred, dps), eliminated=elim, Z_zero_mode_form=mp.nstr(Zc0, dps),
                   c0hat=[mp.nstr(x, dps) for x in c0j])
        result['results'][dstr] = rec
        print('d=%s rho=%s  W=%s  dW=%s  Z=%s  Zred=%s  Zc0=%s' % (
            dstr, mp.nstr(rho, 5), mp.nstr(mp.re(W0), 30), mp.nstr(W1, 5), mp.nstr(mp.re(Z), 35),
            mp.nstr(mp.re(Zred), 35), mp.nstr(mp.re(Zc0), 35)), flush=True)
    result['seconds'] = time.time() - st
    json.dump(result, open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))


if __name__ == '__main__':
    main()
