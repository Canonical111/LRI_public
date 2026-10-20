#!/usr/bin/env python3
"""Quad-precision data for the finite-part extraction (FPE) by fitting.

Runs direct_moments_q (binary128 Gauss, ~33 digits) at many small cutoffs, plus an
mpmath evaluation of the two-kink source moment EQ2 (and EZ2), all single-threaded
in a process pool.  Output: one JSON line per run in results/fpe_data.jsonl.

  python3 fpe_data.py --workers 64 --out ../results/fpe_data.jsonl [--group base|n5]
"""
import argparse
import concurrent.futures as cf
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def eps_grid(lo=-9.0, hi=-4.0, n=100):
    return ['%.30e' % (10 ** (lo + (hi - lo) * i / (n - 1))) for i in range(n)]


def n_quad(eps, digits=33, margin=1.15):
    T = math.log(1.0 / float(eps))
    b = math.pi / T
    rho = b + math.sqrt(1 + b * b)
    return int(math.ceil(margin * digits * math.log(10) / (2 * math.log(rho))))


def tasks(group):
    out = []
    grid = eps_grid()
    if group == 'base':
        for e in grid:
            N = n_quad(e)
            out.append(dict(prog='q', n=2, kind='Z', ord=3, eps=e, N=N))
            out.append(dict(prog='q', n=2, kind='Q', ord=3, eps=e, N=N))
            out.append(dict(prog='q', n=3, kind='A', ord=3, eps=e, N=N))
            out.append(dict(prog='q', n=4, kind='Q', ord=2, eps=e, N=N))
            out.append(dict(prog='mp2', n=2, kind='Q', E=1, ord=3, eps=e))
            out.append(dict(prog='mp2', n=2, kind='Z', E=1, ord=3, eps=e))
        # convergence controls at 5 cutoffs with 30% more points
        for e in grid[::25]:
            N = int(1.3 * n_quad(e))
            out.append(dict(prog='q', n=3, kind='A', ord=3, eps=e, N=N, control=1))
            out.append(dict(prog='q', n=4, kind='Q', ord=2, eps=e, N=N, control=1))
    return out


def key(t):
    return '%s|%d|%s|%d|%d|%s|%s' % (t['prog'], t['n'], t['kind'], t.get('E', 0), t['ord'], t['eps'], t.get('N', 0))


def run_one(t):
    env = dict(os.environ, OMP_NUM_THREADS='1')
    if t['prog'] == 'q':
        cmd = [os.path.join(HERE, 'direct_moments_q'), '-n', str(t['n']), '-k', t['kind'], '-e', t['eps'],
               '-o', str(t['ord']), '-N', str(t['N'])]
    else:
        cmd = [sys.executable, os.path.join(HERE, 'fpe_two_kink_mp.py'), '-k', t['kind'], '-e', t['eps'],
               '-o', str(t['ord'])] + (['-E'] if t.get('E') else [])
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return t, cmd, res, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=os.cpu_count())
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'results', 'fpe_data.jsonl'))
    ap.add_argument('--group', default='base')
    a = ap.parse_args()
    have = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            if line.strip():
                have.add(json.loads(line)['key'])
    todo = [t for t in tasks(a.group) if key(t) not in have]
    # longest first
    todo.sort(key=lambda t: -(t.get('N', 50) ** (t['n'] - 1)))
    print('fpe: %d tasks to do' % len(todo), flush=True)
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for f in cf.as_completed([ex.submit(run_one, t) for t in todo]):
            t, cmd, res, dt = f.result()
            if res.returncode != 0:
                print('FAILED', key(t), res.stderr[-1500:], flush=True)
                continue
            d = json.loads(res.stdout)
            d['key'] = key(t)
            d['task'] = t
            d['wall'] = round(dt, 1)
            with open(a.out, 'a') as fh:
                fh.write(json.dumps(d) + '\n')
            print('%s  %.1fs' % (d['key'], dt), flush=True)


if __name__ == '__main__':
    main()
