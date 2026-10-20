#!/usr/bin/env python3
"""Smoke of HT_Pert/code/lri_hpc_Hamitonian: four production items of the Expanse campaign rerun with the shipped
solver and compared with their records in ../../data/HT_1d/thermal_expanse.

Items (the smallest cutoff of each lane family): thermal degree 7 at Lambda = 52 and 60, phi6 degree 5 at 52, phi6
degree 3 at 136; `python -m lri_hpc --task T --degree D --cutoffs L --threads N --output-dir <work>/smoke/...` run
from a copy of the package (the solver writes checkpoints next to its output). Comparison per item:
  C, r, g (and D6, raw and vacuum_subtracted, for phi6)   |new - rec| <= 1e-7 + 2e-11 |rec|  (the package's own
        regression tolerance; the production stack was Python 3.11.9, numpy 2.3.5, numba 0.65.1 on AMD EPYC 7742 with
        16-48 threads, so the sums are not bitwise across thread counts); the maximum difference is reported
  basis_dimension, source_sha256                          exact
  gates                                                   shell residual <= 1e-10, tuning residuals <= 1e-6
About 1-3 min on 4 threads with JIT, < 5 GB (thermal Lambda = 60: 4.7 GB on the production node).
usage: python3 public/smoke_hpcham.py [--data ../../data/HT_1d] [--work .work] [--threads 4]"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ITEMS = (('thermal', 7, 52), ('thermal', 7, 60), ('phi6', 5, 52), ('phi6', 3, 136))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=os.path.join(PKG, '..', '..', 'data', 'HT_1d'))
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    cp = os.path.join(work, 'smoke_pkg')
    if os.path.exists(cp):
        shutil.rmtree(cp)
    os.makedirs(cp)
    shutil.copytree(os.path.join(PKG, 'lri_hpc'), os.path.join(cp, 'lri_hpc'),
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    out = os.path.join(work, 'smoke')
    if os.path.exists(out):
        shutil.rmtree(out)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OMP_NUM_THREADS='1', NUMBA_NUM_THREADS=str(a.threads))
    env.setdefault('NUMBA_CACHE_DIR', os.path.join(work, 'numba_cache'))
    rows = []
    for task, deg, L in ITEMS:
        t0 = time.time()
        od = os.path.join(out, f'{task}_d{deg}')
        r = subprocess.run([sys.executable, '-m', 'lri_hpc', '--task', task, '--degree', str(deg), '--cutoffs', str(L),
                            '--threads', str(a.threads), '--output-dir', od], cwd=cp, env=env, capture_output=True,
                           text=True)
        name = f'{task}_d{deg}_L{L}'
        if r.returncode:
            rows.append((name, 'FAIL', f'solver failed: {r.stderr[-600:]}'))
            continue
        new = json.load(open(os.path.join(od, name + '.json')))
        rec = json.load(open(os.path.join(a.data, 'thermal_expanse', f'{task}_d{deg}', name + '.json')))
        subs = [('', new, rec)] if task == 'thermal' else [(p + '.', new[p], rec[p]) for p in ('raw', 'vacuum_subtracted')]
        keys = ('C', 'r', 'g') + (('D6',) if task == 'phi6' else ())
        worst, bad, bitwise = 0.0, [], True
        for pre, n, f in subs:
            for k in keys:
                if len(n[k]) != len(f[k]):
                    bad.append(pre + k + ' length')
                    continue
                for x, y in zip(n[k], f[k]):
                    worst = max(worst, abs(x - y))
                    bitwise &= x == y
                    if abs(x - y) > 1e-7 + 2e-11 * abs(y):
                        bad.append(pre + k)
        if new['basis_dimension'] != rec['basis_dimension'] or new['source_sha256'] != rec['source_sha256']:
            bad.append('dimension/source')
        gates = abs(new['second_order_shell_residual']) <= 1e-10 and all(
            abs(s['tuning_residual']) <= 1e-6 for _, s, _ in subs)
        v = 'PASS' if not bad and gates else 'FAIL'
        rows.append((name, v, f'dim {new["basis_dimension"]}; max |new - rec| over {", ".join(keys)} = {worst:.1e} '
                     f'(<= 1e-7 + 2e-11|rec|; bitwise {bitwise}); gates {gates}{"; bad " + str(bad[:4]) if bad else ""}'
                     f' ({time.time() - t0:.0f} s)'))
        print(f'smoke  {name:16s} {rows[-1][1]}  {rows[-1][2]}', flush=True)
    nf = sum(r[1] == 'FAIL' for r in rows)
    summ = f'# smoke lri_hpc_Hamitonian: {len(rows) - nf} PASS, {nf} FAIL'
    print(summ)
    open(os.path.join(work, 'smoke_lri_hpc_Hamitonian.txt'), 'w').write(
        '\n'.join(f'{n:16s} {v} {d}' for n, v, d in rows) + '\n' + summ + '\n')
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
