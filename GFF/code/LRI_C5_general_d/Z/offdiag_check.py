#!/usr/bin/env python3
"""Two-node identity W_3(d;b) = u(b) R(b) + v(b) Mh(b) at b != d/2 against C63d's independent 56-digit spectral
values (references/reference_values.json 'offdiag'), and against the foundation's fixed-node finite-sample W_3 at
further points (including complex b).  usage: offdiag_check.py OUT.json DPS"""
import json
import os
import sys
import time
from multiprocessing import Pool

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'foundation'))
import z_blocks as zb  # noqa: E402

GUARD = 15


def pd(x):
    if x in ('1', '2', '3'):
        return int(x)
    if '/' in x:
        a, b = x.split('/')
        return mp.mpf(int(a)) / int(b)
    return mp.mpf(x)


def task(a):
    dstr, bstr, ref, dps = a
    mp.mp.dps = dps + GUARD
    d = pd(dstr)
    b = mp.mpmathify(bstr)
    st = time.time()
    R, Mh, _ = zb.RM(d, b)
    u, v = zb.uv(b)
    W = u * R + v * Mh
    if ref is None:
        from wheel_general_b import W as Wfs
        refv = Wfs(3, d, b, dps)
        src = 'foundation fixed nodes'
    else:
        refv = mp.mpmathify(ref)
        src = 'C63d spectral 56 digits'
    return dict(d=dstr, b=bstr, W_two_node=mp.nstr(W, dps), ref=mp.nstr(refv, dps), src=src,
                rel=mp.nstr(abs(W - refv) / abs(refv), 3), R=mp.nstr(R, 20), Mh=mp.nstr(Mh, 20),
                sec=round(time.time() - st, 1))


if __name__ == '__main__':
    out, dps = sys.argv[1], int(sys.argv[2])
    rf = os.path.join(HERE, '..', 'references', 'reference_values.json')
    if not os.path.exists(rf):
        rf = os.path.join(HERE, 'reference_values.json')     # cluster copy kept inside this directory
    rv = json.load(open(rf))['values']
    tasks = []
    for k, v in rv.items():
        for od in v['offdiag']:
            tasks.append((k.split('=')[1], od['b'], od['W3'], min(dps, 50)))
    extra = [('1', '0.37'), ('1', '0.3+0.1j'), ('2', '0.8'), ('2', '1.2+0.05j'), ('3', '1.3'), ('3', '1.6'),
             ('3', '1.45+0.05j'), ('1.5', '0.9+0.05j'), ('2.5', '1.4'), ('3.5', '1.7'), ('0.8', '0.42')]
    tasks += [(d, b, None, dps) for d, b in extra]
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 4))
    with Pool(min(workers, len(tasks))) as pool:
        res = pool.map(task, tasks, chunksize=1)
    for r in res:
        print('d=%-4s b=%-10s rel=%-9s [%s]  W=%s' % (r['d'], r['b'], r['rel'], r['src'], r['W_two_node'][:40]))
    json.dump(res, open(out, 'w'), indent=1)
