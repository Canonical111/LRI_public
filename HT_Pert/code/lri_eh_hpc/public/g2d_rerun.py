#!/usr/bin/env python3
"""Regenerate the isolated g^2 D window tables with lri_eh 0.2.0 and compare them with the shipped ones
(HT_Pert/code/lri_eh_hpc; smoke and replay-full targets).

The tables code/lri_hpc_Hamitonian/analysis/eh_review/physics-impact/d5_all.json (degree 5, even Lambda 4..118) and
d7_all.json (degree 7, even Lambda 4..90) were made on a personal desktop by that folder's gen_deltas.py, which
calls lri_eh.numerics.compute(Lambda, degree, memory limit) from an unarchived copy of this package (same source
fingerprint 2e2e8ca8...). They are the g^2 D input of the complete window table dC_reconciled.json and of every
corrected refit. This tool copies gen_deltas.py into <work>/g2d/ (its sys.path entry HERE/pkg does not exist there;
lri_eh is served by PYTHONPATH = this package, read only), runs it into fresh output files, and compares every cutoff
with the shipped record:
  delta_C, delta_r, delta_g (orders 0..degree)  |new - ref| <= 1e-12 max(1, |ref|)   (float64, fastmath off; the
                                                 production stack was Python 3.10, numpy 1.23, numba 0.56)
  basis_dimension                                exact
  validation residuals                           the package gates (shell <= 1e-10, tuning <= 1e-6, exact delta C4
                                                 residual <= 1e-10; lower-order invariance <= 1e-12)
Modes: --smoke   degree 5 at Lambda 4..20 and degree 7 at Lambda 4..12 (about 1 min with JIT, < 1 GB)
       --full    degree 5 at Lambda 4..118 and degree 7 at Lambda 4..90 (about 10 min on 4 threads)
The solver refuses an item whose planned working set exceeds its memory guard (gen_deltas.py reads MEMLIM, in GiB;
default 12, enough for the smoke and degree 5; degree 7 above Lambda ~ 78 needs more): --memlim sets it (default 12 for
--smoke, 64 for --full). It is a guard on a conservative estimate, not an allocation; the node must have that memory.
Rows a1.eh.g2d5, a1.eh.g2d7 (PASS/FAIL); SKIP if ../lri_hpc_Hamitonian (gen_deltas.py and the tables) is absent.
usage: python3 public/g2d_rerun.py (--smoke | --full) [--work .work] [--threads 4] [--memlim GiB] [--hpcham ../lri_hpc_Hamitonian]"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
TOL = 1e-12
GATES = dict(max_raw_vacuum_shell_residual=1e-10, max_tuning_residual=1e-6, response_tuning_residual=1e-6,
             exact_delta_C4_residual=1e-10, lower_order_invariance_residual=1e-12)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--smoke', action='store_true')
    g.add_argument('--full', action='store_true')
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--hpcham', default=os.path.join(PKG, '..', 'lri_hpc_Hamitonian'))
    ap.add_argument('--memlim', type=float, default=None, help='memory guard in GiB (default 12 smoke, 64 full)')
    a = ap.parse_args()
    memlim = a.memlim if a.memlim is not None else (12.0 if a.smoke else 64.0)
    src = os.path.join(a.hpcham, 'analysis', 'eh_review', 'physics-impact')
    mode = 'smoke' if a.smoke else 'full'
    plan = {5: list(range(4, 21 if a.smoke else 119, 2)), 7: list(range(4, 13 if a.smoke else 91, 2))}
    rows = []
    if not os.path.exists(os.path.join(src, 'gen_deltas.py')):
        for d in plan:
            rows.append((f'a1.eh.g2d{d}', 'SKIP', f'{src} absent (package lri_hpc_Hamitonian)'))
    else:
        W = os.path.abspath(os.path.join(a.work, f'g2d_{mode}'))
        if os.path.exists(W):
            shutil.rmtree(W)
        os.makedirs(W)
        shutil.copy2(os.path.join(src, 'gen_deltas.py'), W)
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([PKG] + ([os.environ['PYTHONPATH']] if os.environ.get(
            'PYTHONPATH') else [])), PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
            OMP_NUM_THREADS='1', NUMBA_NUM_THREADS=str(a.threads), NTH=str(a.threads), MEMLIM=f'{memlim:g}')
        env.setdefault('NUMBA_CACHE_DIR', os.path.join(os.path.abspath(a.work), 'numba_cache'))
        for d, Ls in plan.items():
            t0 = time.time()
            out = os.path.join(W, f'd{d}_new.json')
            r = subprocess.run([sys.executable, 'gen_deltas.py', str(d), out] + [str(x) for x in Ls], cwd=W, env=env,
                               capture_output=True, text=True)
            if r.returncode:
                rows.append((f'a1.eh.g2d{d}', 'FAIL', f'gen_deltas.py {d} failed: {r.stderr[-800:]}'))
                continue
            new = json.load(open(out))
            ref = json.load(open(os.path.join(src, f'd{d}_all.json')))
            worst, bad, gate_bad = 0.0, [], []
            for L in Ls:
                n, f = new[str(L)], ref[str(L)]
                if n['basis_dimension'] != f['basis_dimension']:
                    bad.append(f'{L} dim')
                for k in ('delta_C', 'delta_r', 'delta_g'):
                    if len(n[k]) != len(f[k]):
                        bad.append(f'{L} {k} length')
                        continue
                    for x, y in zip(n[k], f[k]):
                        e = abs(x - y) / max(1.0, abs(y))
                        worst = max(worst, e)
                        if e > TOL:
                            bad.append(f'{L} {k}')
                gate_bad += [f'{L} {k}' for k, lim in GATES.items() if abs(n['validation'][k]) > lim]
            v = 'FAIL' if bad or gate_bad else 'PASS'
            rows.append((f'a1.eh.g2d{d}', v, f'degree {d}, Lambda {Ls[0]}..{Ls[-1]} ({len(Ls)} cutoffs) regenerated with '
                         f'lri_eh vs the shipped d{d}_all.json: max |new - ref|/max(1,|ref|) = {worst:.1e} (<= {TOL:g}) '
                         f'over delta_C, delta_r, delta_g; basis dimensions equal; gates pass: {not gate_bad}'
                         f'{"; bad " + str((bad + gate_bad)[:5]) if bad or gate_bad else ""} ({time.time() - t0:.0f} s)'))
    for rid, v, det in rows:
        print(f'{rid:12s} {v:4s} {det}', flush=True)
    nf = sum(r[1] == 'FAIL' for r in rows)
    summ = f'# g2d {mode} lri_eh_hpc: {sum(r[1] == "PASS" for r in rows)} PASS, {nf} FAIL' + (
        f', {sum(r[1] == "SKIP" for r in rows)} SKIP' if any(r[1] == 'SKIP' for r in rows) else '')
    print(summ)
    os.makedirs(a.work, exist_ok=True)
    open(os.path.join(a.work, f'g2d_{mode}_lri_eh_hpc.txt'), 'w').write(
        '\n'.join(f'{r} {v} {d}' for r, v, d in rows) + '\n' + summ + '\n')
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
