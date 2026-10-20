#!/usr/bin/env python3
"""Three-node tau-jet of <t^2 R_tau>_d (gdk:threeNodeRule, rblocks.tR3 of K_general/R_part, unchanged) on a circle
|tau| = r, N points; writes the circle values.  Laurent extraction and K via gdk:Kr3 are done in e2e_k3.py.
usage: kjet3.py d r N K M dps out.json"""
import sys, os, time, json
import mpmath as mp
from multiprocessing import Pool


def work(args):
    ds, rs, N, K, M, dps, s = args
    mp.mp.dps = dps
    import rblocks as rb
    d = mp.mpf(ds); q = d / 4; r = mp.mpf(rs)
    tau = r * mp.expj(2 * mp.pi * s / N)
    if s == 0 or s == N // 2:
        tau = mp.mpf(mp.re(tau))
    st = time.time()
    tr = rb.tR3(q, tau, K, M)
    return ds, s, str(mp.re(tr)), str(mp.im(tr)), round(time.time() - st, 1)


if __name__ == '__main__':
    dlist = sys.argv[1].split(',')
    rs, N, K, M, dps, out = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', '2'))
    st = time.time()
    jobs = [(ds, rs, N, K, M, dps, s) for ds in dlist for s in range(N // 2 + 1)]
    with Pool(workers) as pool:
        res = pool.map(work, jobs, chunksize=1)
    rec = dict(r=rs, N=N, K=K, M=M, dps=dps, points={})
    for ds, s, tr, ti, sec in res:
        rec['points'].setdefault(ds, {})[str(s)] = dict(Re_tR=tr, Im_tR=ti, sec=sec)
    rec['wall'] = round(time.time() - st, 1)
    json.dump(rec, open(out, 'w'), indent=1)
    print('done', rec['wall'])
