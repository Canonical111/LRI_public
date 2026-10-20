#!/usr/bin/env python3
"""Driver: Xi(t_j) = D(t_j) S(t_j) on t_j = t0 + j/N (N = 2r+1 by default), all Fourier modes, JSON output.

usage: run_case.py CASE [--dps 48] [--D 44] [--hden 14] [--K 26] [--ngl 28] [--np 8] [--imag 0]
                        [--N 0] [--cont] [--tag x] [--outdir results]
Parallel over (node, part) with multiprocessing; each task is single-threaded mpmath.
"""
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


def build(name):
    c = cases.get(name)
    return E.LemmaG(c['d'], c['sigma'], c['g'], c['alpha'], c['beta'], c['dmult'])


def worker(task):
    name, tstr, part, cfgd, dps, cont = task
    mp.mp.dps = dps
    model = build(name)
    cfg = E.Cfg(**cfgd)
    t = mp.mpmathify(tstr)
    t0 = time.time()
    v = model.parts(t, cfg, which=(part,), cont=cont)[part]
    return (tstr, part, str(v), time.time() - t0)


def s(x, n=None):
    return mp.nstr(x, n) if n else str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('case')
    ap.add_argument('--dps', type=int, default=48)
    ap.add_argument('--D', type=int, default=44)
    ap.add_argument('--hden', type=int, default=14)
    ap.add_argument('--K', type=int, default=26)
    ap.add_argument('--ngl', type=int, default=28)
    ap.add_argument('--np', type=int, default=8)
    ap.add_argument('--imag', type=float, default=0.0)
    ap.add_argument('--N', type=int, default=0)
    ap.add_argument('--cont', action='store_true')
    ap.add_argument('--altnodes', action='store_true', help='node set disjoint from the default one')
    ap.add_argument('--tag', default='')
    ap.add_argument('--outdir', default='results')
    a = ap.parse_args()
    mp.mp.dps = a.dps
    model = build(a.case)
    r = model.r
    N = a.N if a.N else 2 * r + 1
    t0, mind = E.choose_t0(model, N, imag=a.imag)
    if a.altnodes:
        t0, mind = E.choose_t0(model, N, imag=a.imag, avoid=t0)
    ts = [t0 + mp.mpf(j) / N for j in range(N)]
    cfgd = dict(K=a.K, D=a.D, hden=a.hden, ngl=a.ngl)
    tasks = [(a.case, str(t), part, cfgd, a.dps, a.cont) for t in ts for part in ('right', 'left', 'middle')]
    T0 = time.time()
    with Pool(a.np) as pool:
        res = pool.map(worker, tasks, chunksize=1)
    wall = time.time() - T0
    parts = {}
    cpu = 0
    for tstr, part, v, dt in res:
        parts.setdefault(tstr, {})[part] = mp.mpmathify(v)
        cpu += dt
    S = [mp.fsum(parts[str(t)].values()) for t in ts]
    Xi = [model.Dfac(t) * Sv for t, Sv in zip(ts, S)]
    kmax = (N - 1) // 2
    modes = E.dft(ts, Xi, kmax)
    lower = [k for k in modes if abs(k) < r - 1]
    scale = max(abs(modes[k]) for k in modes)
    scale_low = max(abs(modes[k]) for k in lower)
    al, bound = model.condC()
    out = dict(
        case=a.case, r=r, d=s(model.d), dmult=s(model.dm), sigma=s(model.sigma),
        g=[s(x) for x in model.g], alpha=[s(x) for x in model.alpha], beta=[s(x) for x in model.beta],
        G=s(model.G), condC=dict(alpha=s(al, 12), bound=s(bound, 12), inside=bool(al > bound),
                                 margins=dict(alpha_minus_dm1=s(al - (model.d - 1), 6), two_alpha_minus_d=s(2 * al - model.d, 6),
                                              two_alpha_minus_1=s(2 * al - 1, 6))),
        balance_defects=[s(x, 6) for x in model.balance_defects()],
        min_Re_g=s(min(mp.re(x) for x in model.g), 6),
        cfg=dict(cfgd, dps=a.dps, cont=a.cont, altnodes=a.altnodes, imag=a.imag), N=N, t0=s(t0), min_sin_to_classes=s(mind, 6),
        nodes=[s(t) for t in ts], S=[s(x) for x in S], Xi=[s(x) for x in Xi],
        parts={k: {p: s(v) for p, v in d.items()} for k, d in parts.items()},
        modes={str(k): s(v) for k, v in sorted(modes.items())},
        abs_modes={str(k): s(abs(v), 6) for k, v in sorted(modes.items())},
        top_minus=s(abs(modes[-(r - 1)]) / scale, 6), top_plus=s(abs(modes[r - 1]) / scale, 6),
        top_minus_vs_lower=s(abs(modes[-(r - 1)]) / scale_low, 6), top_plus_vs_lower=s(abs(modes[r - 1]) / scale_low, 6),
        beyond=({'minus': s(abs(modes[-r]) / scale, 6), 'plus': s(abs(modes[r]) / scale, 6)} if kmax >= r else None),
        scale_max_abs_c=s(scale, 8), wall_s=round(wall, 1), cpu_s=round(cpu, 1), np=a.np,
    )
    os.makedirs(a.outdir, exist_ok=True)
    fn = os.path.join(a.outdir, '%s%s.json' % (a.case, ('_' + a.tag) if a.tag else ''))
    with open(fn, 'w') as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ('case', 'condC', 'balance_defects', 'abs_modes', 'top_minus', 'top_plus',
                                          'beyond', 'wall_s', 'cpu_s')}, indent=1))


if __name__ == '__main__':
    main()
