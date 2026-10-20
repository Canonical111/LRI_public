#!/usr/bin/env python3
"""High-precision validation of the five-Horn formula for P4(d) and L_d (session L).

Tasks (each in its own process):
  center  r=4: (P4, L_d) with exact jet derivative, plus the five Horn values/derivatives and their prefactors
  center  r=3: (3Q_d, dW_3/db) by the two-node r=3 formula (dW_3/db must vanish; skipped at r(d-b)/2 in Z)
  conv    r=4: the same with enlarged truncation (M, K, N) x 1.4 (accuracy of the accelerated sums)
  offdiag r=4, r=3: W_r(d;b) at C63d's off-diagonal b (three-node formula away from b = d/2)
usage: run_validation.py OUT.json DPS d1,d2,...
"""
import sys
import os
import json
import time
import mpmath as mp
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from L_general import Wheel3  # noqa: E402
from jet import J, val, der  # noqa: E402

GUARD = 15
OFFDIAG = {'0.8': ['0.43', '0.37'], '1.25': ['0.675', '0.575'], '1.5': ['0.8', '0.7'], '2.5': ['1.3', '1.2'],
           '2.75': ['1.425', '1.325'], '1': ['0.55', '0.45'], '2': ['1.05', '0.95'], '3': ['1.55', '1.45']}


def task(args):
    kind, r, dstr, bstr, dps = args
    mp.mp.dps = dps + GUARD
    d = mp.mpmathify(dstr)
    st = time.time()
    if kind in ('center', 'conv'):
        b = J(d / 2, 1)
        kw = {}
        if kind == 'conv':
            M0 = max(80, int(1.6 * mp.mp.dps))
            K0 = max(30, int(0.8 * mp.mp.dps) + 10)
            kw = dict(M=int(1.4 * M0), K=int(1.4 * K0), N=int(1.4 * M0) // 2)
        w = Wheel3(r, d, b, **kw)
        Wv, sm = w.W(full=True)
        out = dict(W=mp.nstr(mp.re(val(Wv)), dps + 10), dW=mp.nstr(mp.re(der(Wv)), dps + 10),
                   imW=mp.nstr(abs(mp.im(val(Wv))) + abs(mp.im(der(Wv))), 3))
        if kind == 'center':
            out['funcs'] = {k: [mp.nstr(mp.re(val(sm[k])), dps + 10), mp.nstr(mp.re(der(sm[k])), dps + 10)]
                            for k in ('hx', 'h1', 'hh', 's0', 's1')}
            out['samples_times_Nr'] = {k: [mp.nstr(mp.re(val(sm[k])), dps + 10), mp.nstr(mp.re(der(sm[k])), dps + 10)]
                                       for k in ('Xt', 'X0', 'Xh')}
            out['ck_times_Nr'] = [[mp.nstr(mp.re(val(c)), dps + 10), mp.nstr(mp.re(der(c)), dps + 10)]
                                  for c in sm['ck_times_Nr']]
            out['idcheck'] = mp.nstr(abs(val(sm['idcheck'])) + abs(der(sm['idcheck'])), 3)
    else:
        b = mp.mpmathify(bstr)
        w = Wheel3(r, d, b)
        Wv = w.W()
        out = dict(W=mp.nstr(mp.re(Wv), dps + 10), imW=mp.nstr(abs(mp.im(Wv)), 3))
    out['seconds'] = time.time() - st
    return (kind, r, dstr, bstr), out


def exceptional3(dstr):
    d = mp.mpmathify(dstr)
    v = 3 * d / 4
    integer_d = d in (1, 2, 3)
    return (not integer_d) and abs(v - mp.nint(v)) < mp.mpf(10) ** -20


if __name__ == '__main__':
    out, dps, ds = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(',')
    tasks = []
    for dstr in ds:
        tasks.append(('center', 4, dstr, None, dps))
        tasks.append(('conv', 4, dstr, None, dps))
        if not exceptional3(dstr) and mp.mpmathify(dstr) > mp.mpf(2) / 3:   # b = d/2 inside the r=3 strip
            tasks.append(('center', 3, dstr, None, dps))
        for bstr in OFFDIAG.get(dstr, []):
            tasks.append(('offdiag', 4, dstr, bstr, dps))
            tasks.append(('offdiag', 3, dstr, bstr, dps))
    tasks.sort(key=lambda t: (t[0] != 'conv', t[0] != 'center'))   # longest first
    workers = int(os.environ.get('SLURM_CPUS_PER_TASK', os.cpu_count() or 4))
    st = time.time()
    with Pool(workers) as pool:
        res = pool.map(task, tasks, chunksize=1)
    result = dict(dps=dps, guard=GUARD, seconds=time.time() - st, results={})
    for (kind, r, dstr, bstr), o in res:
        key = '%s_r%d_d%s' % (kind, r, dstr) + ('_b%s' % bstr if bstr else '')
        result['results'][key] = o
        print(key, o.get('W'), o.get('dW', ''), '[%.0f s]' % o['seconds'], flush=True)
    json.dump(result, open(out, 'w'), indent=1)
    print('done %.0f s' % (time.time() - st))
