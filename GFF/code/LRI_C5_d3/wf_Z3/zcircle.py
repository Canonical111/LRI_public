#!/usr/bin/env python3
"""Cauchy circle for Y(b) around b=3/2: Taylor coefficients a_0..a_4 of Y(3/2+delta).
usage: zcircle.py OUT.json DPS N K M RHO PHASE"""
import sys, json, time, os
import mpmath as mp
from multiprocessing import Pool
import zb

def cfg():
    return json.loads(os.environ['ZC_CFG'])

def job(k):
    c = cfg(); mp.mp.dps = c['dps']
    th = 2 * mp.pi * k / c['M'] + mp.mpf(c['phase'])
    b = mp.mpf(3) / 2 + mp.mpf(c['rho']) * mp.expj(th)
    return k, str(zb.Y(b, c['N'], c['K']))

if __name__ == '__main__':
    out = sys.argv[1]
    c = dict(dps=int(sys.argv[2]), N=int(sys.argv[3]), K=int(sys.argv[4]), M=int(sys.argv[5]), rho=sys.argv[6], phase=sys.argv[7])
    os.environ['ZC_CFG'] = json.dumps(c)
    mp.mp.dps = c['dps']
    st = time.time()
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', 4))
    with Pool(workers) as pool:
        res = dict(pool.map(job, range(c['M']), chunksize=1))
    M, rho = c['M'], mp.mpf(c['rho'])
    vals = [mp.mpmathify(res[k]) for k in range(M)]
    coef = []
    for j in range(5):
        s = mp.fsum(vals[k] * mp.expj(-j * (2 * mp.pi * k / M + mp.mpf(c['phase']))) for k in range(M)) / M / rho ** j
        coef.append(str(s))
    json.dump(dict(c, seconds=time.time() - st, taylor=coef, values={str(k): res[k] for k in range(M)}), open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st)); print('\n'.join(coef))
