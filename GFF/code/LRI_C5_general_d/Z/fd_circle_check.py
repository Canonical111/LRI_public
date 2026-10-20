#!/usr/bin/env python3
"""Consistency check (NOT independent: shares the accelerated Horn sums): Z_d from a Cauchy circle in b of the
foundation's fixed-node finite-sample W_3 (five complex nodes, all five blocks per node), wheel_general_b.bjets.
usage: fd_circle_check.py OUT.json DPS M d1,d2,..."""
import json
import os
import sys
from multiprocessing import Pool

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'foundation'))
import wheel_general_b as wg  # noqa: E402

if __name__ == '__main__':
    out, dps, M, ds = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4].split(',')
    mp.mp.dps = dps + 15
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 4))
    res = {}
    with Pool(workers) as pool:
        for dstr in ds:
            d = int(dstr) if dstr in ('1', '2', '3') else mp.mpf(dstr)
            a = wg.bjets(3, d, kmax=2, dps=dps, M=M, pool=pool)
            res[dstr] = dict(W=mp.nstr(a[0], dps), dW=mp.nstr(a[1], 5), Z=mp.nstr(2 * a[2] / 9, dps),
                             rho=mp.nstr(wg.circle_params(3, d)[1], 6))
            print(dstr, res[dstr], flush=True)
    json.dump(dict(dps=dps, M=M, engine='foundation fixed-node W, Cauchy circle', results=res), open(out, 'w'), indent=1)
