#!/usr/bin/env python3
"""Convergence ladder for the quadrant sums of xi_direct.py (h, K, P, M, dps)."""
import sys, os, time, json
import multiprocessing as mproc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpmath as mp
from xi_direct import Wheel

CASES = [
    # (label, d, b, r, part, t)
    ('A1r3_R', '1.3', ('0.6', '0.1'), 3, 'R', ('0.2371', '0.0917')),
    ('A3r3_M', '3.2', ('1.5', '0'), 3, 'M', ('0.2371', '0.0917')),
    ('A2r5_R', '2.4', ('1.1', '0'), 5, 'R', ('0.6113', '0.0417')),
]
LADDER = [
    dict(dps=50, K=30, P=10, h='1/8', M=64),
    dict(dps=50, K=30, P=10, h='1/16', M=64),
    dict(dps=50, K=30, P=10, h='1/32', M=64),
    dict(dps=50, K=30, P=10, h='1/64', M=64),
    dict(dps=50, K=45, P=14, h='1/32', M=96),
    dict(dps=50, K=60, P=16, h='1/32', M=96),
    dict(dps=50, K=60, P=16, h='1/64', M=128),
]


def run(args):
    ci, si = args
    lab, d, b, r, part, t = CASES[ci]
    s = LADDER[si]
    mp.mp.dps = s['dps']
    w = Wheel(d, mp.mpc(*b), r)
    tt = mp.mpc(*t)
    h = mp.mpf(s['h'].split('/')[0]) / mp.mpf(s['h'].split('/')[1])
    t0 = time.time()
    if part == 'R':
        pr, Q = w._right(tt)
        v = pr * Q.total(K=s['K'], P=s['P'], h=h, M=s['M'])
    else:
        v = w._middle(tt).total(K=s['K'], P=s['P'], h=h, M=s['M'])
    return (lab, si, mp.nstr(v.real, 60), mp.nstr(v.imag, 60), time.time() - t0)


if __name__ == '__main__':
    jobs = [(ci, si) for ci in range(len(CASES)) for si in range(len(LADDER))]
    nproc = int(os.environ.get('SLURM_CPUS_PER_TASK', '8'))
    with mproc.Pool(nproc) as pool:
        res = pool.map(run, jobs, chunksize=1)
    mp.mp.dps = 60
    out = {}
    for lab, si, re_, im_, dt in res:
        out.setdefault(lab, {})[si] = (re_, im_, dt)
    for lab in out:
        best = mp.mpc(*out[lab][len(LADDER) - 1][:2])
        print(lab)
        for si in sorted(out[lab]):
            v = mp.mpc(*out[lab][si][:2])
            print('  ', LADDER[si], mp.nstr(v, 45), ' dev vs last %.2e' % float(abs(v - best) / abs(best)),
                  ' %.1fs' % out[lab][si][2])
    json.dump(dict(cases=CASES, ladder=LADDER, results=out), open('conv_test.json', 'w'), indent=1)
