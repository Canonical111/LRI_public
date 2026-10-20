#!/usr/bin/env python3
"""Smoke rerun of one production item: `python -m lri_c8 run --cutoff 52 --scheme raw|vacuum_only --outer-backend
stored` (the backend and caps of the production items at Lambda = 52) into <work>/smoke_c8/, compared with the shipped
outputs data/HT_1d/c8/c8_L52-92/accepted/{raw,vacuum_only}_L52_d8.json.

C, r, g and the four energy series are compared. On the production stack (symmetry module anaconda3/2023.07-2: Python
3.11.4, numpy 1.24.3, numba 0.57.0) they are expected bit for bit (thread count and backend do not change any output
bit); on other stacks the package's own cross-stack tolerance applies, atol 1e-7 + rtol 2e-11 (as
scripts/regression_saved_grid.py and scripts/compare_original.py). The solver's acceptance gates run inside `run`.
Production: 7.4 s (raw) and 9.2 s (vacuum_only) on 40 threads, peak RSS 1.6 GiB; here about 1.2 min with the default
4 threads including Numba compilation on a cold cache, 1.7 GiB (symmetry jobs 575002, 575003, 575032, Xeon Gold 6148:
bitwise on both tested stacks).
usage: python3 public/smoke_c8.py [--data ../../data/HT_1d] [--work .work] [--threads 4] [--cutoff 52]"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', type=Path, default=PKG / '..' / '..' / 'data' / 'HT_1d')
    ap.add_argument('--work', type=Path, default=PKG / '.work')
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--cutoff', type=int, default=52)
    a = ap.parse_args()
    W = a.work.resolve() / 'smoke_c8'
    shutil.rmtree(W, ignore_errors=True)
    W.mkdir(parents=True)
    env = dict(os.environ, PYTHONPATH=str(PKG / 'src'), OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OMP_NUM_THREADS='1', NUMBA_NUM_THREADS=str(a.threads), PYTHONDONTWRITEBYTECODE='1',
               NUMBA_CACHE_DIR=os.environ.get('NUMBA_CACHE_DIR', str(a.work.resolve() / 'numba_cache' / 'smoke')))
    worst, bitwise, ok, msgs = 0.0, True, True, []
    for s in ('raw', 'vacuum_only'):
        t = time.time()
        r = subprocess.run([sys.executable, '-m', 'lri_c8', 'run', '--cutoff', str(a.cutoff), '--scheme', s,
                            '--outer-backend', 'stored', '--threads', str(a.threads), '--memory-limit-gib', '8',
                            '--output-dir', str(W / s)], cwd=W, env=env, capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-3000:], sep='\n')
            ok = False
            msgs.append(f'{s}: run failed (exit {r.returncode})')
            continue
        new = json.loads((W / s / f'{s}_L{a.cutoff}_d8.json').read_text())['payload']
        ref = json.loads((a.data / 'c8' / 'c8_L52-92' / 'accepted' / f'{s}_L{a.cutoff}_d8.json').read_text())['payload']
        pairs = [(x, y) for k in ('C', 'r', 'g') for x, y in zip(new[k], ref[k])]
        pairs += [(x, y) for e, f in zip(new['energies'], ref['energies']) for x, y in zip(e, f)]
        d = max(abs(x - y) for x, y in pairs)
        within = all(abs(x - y) <= 1e-7 + 2e-11 * abs(y) for x, y in pairs)
        bit = all(x == y for x, y in pairs)
        worst, bitwise, ok = max(worst, d), bitwise and bit, ok and within
        msgs.append(f'{s}: C8 {new["C"][8]!r} vs shipped {ref["C"][8]!r}, max |d| {d:.2e}, bitwise {bit}, '
                    f'{time.time() - t:.0f} s')
    print('\n'.join(msgs))
    print(f'smoke_c8  {"PASS" if ok else "FAIL"}  Lambda = {a.cutoff} raw and vacuum_only rerun vs shipped outputs: '
          f'max |d| = {worst:.2e}, bitwise {bitwise} (tolerance atol 1e-7 + rtol 2e-11)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
