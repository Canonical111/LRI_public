#!/usr/bin/env python3
"""Convergence/timing test: S(t_0) (one node) for several step sizes h=1/hden and truncations D.
usage: conv_h.py CASES(comma) HDENS(comma) [--D 44] [--dps 48] [--np 8] [--K 12] [--ngl 28] [--Dalt 0]"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import mpmath as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lg_engine as E  # noqa: E402
import cases  # noqa: E402
from run_case import build  # noqa: E402


def worker(task):
    name, tstr, part, cfgd, dps = task
    mp.mp.dps = dps
    model = build(name)
    t0 = time.time()
    v = model.parts(mp.mpmathify(tstr), E.Cfg(**cfgd), which=(part,))[part]
    return (name, cfgd['hden'], cfgd['D'], cfgd['ngl'], part, str(v), time.time() - t0)


ap = argparse.ArgumentParser()
ap.add_argument('cases')
ap.add_argument('hdens')
ap.add_argument('--D', type=int, default=44)
ap.add_argument('--dps', type=int, default=48)
ap.add_argument('--np', type=int, default=8)
ap.add_argument('--K', type=int, default=26)
ap.add_argument('--ngl', type=int, default=28)
ap.add_argument('--extra', default='')     # e.g. "D=50,ngl=36,hden=32" : one extra config per case
a = ap.parse_args()
mp.mp.dps = a.dps
tasks = []
cfgs = [dict(K=a.K, D=a.D, hden=int(h), ngl=a.ngl) for h in a.hdens.split(',')]
if a.extra:
    ex = dict(K=a.K, D=a.D, hden=int(a.hdens.split(',')[-1]), ngl=a.ngl)
    for kv in a.extra.split(','):
        k, v = kv.split('=')
        ex[k] = int(v)
    cfgs.append(ex)
for name in a.cases.split(','):
    model = build(name)
    t0, _ = E.choose_t0(model, 2 * model.r + 1)
    for cfgd in cfgs:
        for part in ('right', 'left', 'middle'):
            tasks.append((name, str(t0), part, cfgd, a.dps))
with Pool(a.np) as pool:
    res = pool.map(worker, tasks, chunksize=1)
tab = {}
for name, hd, D, ngl, part, v, dt in res:
    key = (name, hd, D, ngl)
    tab.setdefault(key, {})[part] = (mp.mpmathify(v), dt)
out = {}
for name in a.cases.split(','):
    keys = [k for k in tab if k[0] == name]
    ref = keys[-1]
    Sref = mp.fsum(v for v, _ in tab[ref].values())
    for k in keys:
        S = mp.fsum(v for v, _ in tab[k].values())
        tt = {p: round(dt, 1) for p, (v, dt) in tab[k].items()}
        diffs = {p: mp.nstr(abs(tab[k][p][0] - tab[ref][p][0]), 3) for p in tab[k]}
        print(name, 'hden=%d D=%d ngl=%d' % k[1:], 'S=', mp.nstr(S, 20), ' |S-Sref|/|S|=', mp.nstr(abs(S - Sref) / abs(Sref), 3),
              'part diffs', diffs, 'times', tt, flush=True)
        out['%s_h%d_D%d_n%d' % k] = dict(S=str(S), parts={p: str(v) for p, (v, dt) in tab[k].items()}, times=tt)
os.makedirs('diag', exist_ok=True)
with open('diag/conv_%s_%s.json' % (a.cases.replace(',', '-'), a.hdens.replace(',', '-')), 'w') as f:
    json.dump(out, f, indent=1)
