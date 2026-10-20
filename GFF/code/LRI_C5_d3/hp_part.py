#!/usr/bin/env python3
"""Split high-precision run: one Cauchy circle per job, radius RHO.
usage: hp_part.py OUT.json DPS SPINS KMAX M PART(b|t) RHO   -> raw circle values; combine with hp_combine.py
Configuration reaches pool workers through the environment (safe under fork and spawn)."""
import sys, json, time, os
import mpmath as mp
from multiprocessing import Pool
import hp_masters_d3 as H

def cfg():
    c = json.loads(os.environ['C5D3_CFG'])
    H.LSP, H.KMAX, H.M, H.DPS = c['spins'], c['kmax'], c['M'], c['dps']
    return c

def job(k):
    c = cfg()
    mp.mp.dps = c['dps']
    th = 2 * mp.pi * k / c['M']
    if c['part'] == 'b':
        b = mp.mpf(3) / 2 + mp.mpf(c['rho']) * mp.expj(th)
        v = (H.wheel(3, b), H.wheel(4, b))
    else:
        v = (H.Kmixed(mp.mpf(c['rho']) * mp.expj(th)),)
    return k, [str(x) for x in v]

if __name__ == '__main__':
    out = sys.argv[1]
    c = dict(dps=int(sys.argv[2]), spins=int(sys.argv[3]), kmax=int(sys.argv[4]), M=int(sys.argv[5]), part=sys.argv[6], rho=sys.argv[7])
    os.environ['C5D3_CFG'] = json.dumps(c)
    cfg(); mp.mp.dps = c['dps']
    st = time.time()
    ks = list(range(c['M'] // 2 + 1))
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 10))
    print('part', c['part'], 'tasks', len(ks), 'workers', workers, flush=True)
    with Pool(workers) as pool:
        res = dict(pool.map(job, ks, chunksize=1))
    json.dump(dict(c, seconds=time.time() - st, values={str(k): res[k] for k in ks}), open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))
