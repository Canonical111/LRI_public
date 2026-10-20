#!/usr/bin/env python3
"""High-precision Q3/P4(3) pieces from inputs/general_d3/d3_reduction.py (unchanged code), parallel over pieces.
usage: hp_periods.py OUT.json DPS N K"""
import sys, json, time, os
import mpmath as mp
from multiprocessing import Pool
import d3_reduction as R

def job(name):
    c = json.loads(os.environ['HP_CFG']); mp.mp.dps = c['dps']; N, K = c['N'], c['K']
    if name == 'x30': v = R.Xi(3, 0, N, K)
    elif name == 'x40': v = R.Xi(4, 0, N, K)
    elif name == 'x4h': v = R.Xi(4, mp.mpf(1) / 8, N, K)
    elif name == 'a4': v = R.Psi(4, 0, 1, mp.mpf(1) / 4, N, K)
    elif name == 'b4': v = R.Psi(4, 1, 1, mp.mpf(1) / 8, N, K) / mp.sin(mp.pi / 4)
    elif name == 'a3': v = R.Psi(3, 0, 1, mp.mpf(1) / 8, N, K) / mp.cos(mp.pi / 8)
    elif name == 'b3': v = R.Psi(3, 1, 1, mp.mpf(1) / 8, N, K) / mp.sin(mp.pi / 8)
    return name, str(v)

if __name__ == '__main__':
    out = sys.argv[1]
    c = dict(dps=int(sys.argv[2]), N=int(sys.argv[3]), K=int(sys.argv[4]))
    os.environ['HP_CFG'] = json.dumps(c)
    st = time.time()
    names = ['x30', 'x40', 'x4h', 'a4', 'b4', 'a3', 'b3']
    with Pool(len(names)) as pool:
        res = dict(pool.map(job, names, chunksize=1))
    json.dump(dict(c, seconds=time.time() - st, values=res), open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))
    for k in names: print(k, res[k][:60])
