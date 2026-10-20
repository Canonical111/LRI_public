#!/usr/bin/env python3
"""Fast tests of lri_c8_hpc in the public tree, on a run-time copy (the shipped files are never written).

1. Copies the package (without public/ and the work folder) to <work>/tree.
2. pytest tests/ in the copy, complete and unfiltered as scripts/validate_release.py runs it (-p no:cacheprovider,
   -o addopts=, no plugin autoload), with a fresh Numba cache under <work>; the production receipt (job 569659)
   recorded 74 collected, 74 passed. Required here: 74 passed, nothing failed or skipped.
   The Numba threading layer is pinned, as the production environment pins it (slurm/symmetry_env.sh forces
   NUMBA_THREADING_LAYER=tbb; the receipt records the setting 'tbb'): the caller's NUMBA_THREADING_LAYER if set, else
   tbb when this Python can load it, else workqueue. Reason: every output records its runtime configuration, including
   the threadpoolctl list of loaded BLAS/OpenMP libraries, and shard assembly and export refuse mixed configurations.
   With the layer left to Numba's default and no tbb, Numba loads libgomp, and the order in which threadpoolctl lists
   libgomp and OpenBLAS depends on whether the process compiled its kernels or loaded them from the cache. Two tests
   (test_cli_and_shard_assembly, test_export_mixed_threads_and_backends) then fail with "Checkpoint configuration,
   source, or runtime mismatch" / "Mixed source/runtime/prescription outputs" (symmetry jobs 574957, 574960; Python
   3.12.9, numpy 2.3.5, numba 0.68.0, no tbb). A pinned layer gives every process the same configuration. The layer
   does not change any number (the production outputs are bit-identical across thread counts and backends; the grid
   replay and the smoke rerun were bitwise on that stack).
3. scripts/regression_saved_grid.py --compare benchmarks/REGRESSION_GRID.json in the copy: all 38 original records
   (25 raw, 13 vacuum_only, Lambda <= 50) recomputed; the script itself asserts C, r, g and the energies against the
   records (atol 1e-7, rtol 2e-11) and C8 against the bundled grid (1e-7 + 2e-11 |ref|). The number of bitwise-equal
   points is reported: 38 of 38 in production (job 569659) and with Python 3.12.9, numpy 2.3.5, numba 0.68.0 on
   the same CPU (jobs 575003, 575032); other stacks and CPUs may differ in the last bits.
Prints PASS/FAIL per step; exit 1 on any FAIL.  About 6 min with the default 4 threads on a Xeon Gold 6148 node
(symmetry job 575032: pytest about 3.7 min with a cold cache, grid about 2 min; 4 min on the production stack).
usage: python3 public/run_tests_c8.py [--work .work] [--threads 4]"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, default=PKG / '.work')
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    work = a.work.resolve()
    tree = work / 'tree'
    shutil.rmtree(tree, ignore_errors=True)

    def ignore(d, names):
        d = Path(d).resolve()
        skip = {n for n in names if n in ('__pycache__', '.numba_cache', '.pytest_cache') or (d / n) == work}
        if d == PKG:
            skip |= {n for n in names if n in ('public', 'public.mk', '.work')}
        return skip
    shutil.copytree(PKG, tree, ignore=ignore)
    cache = work / 'numba_cache' / 'test'
    shutil.rmtree(cache, ignore_errors=True)
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', OMP_NUM_THREADS='1',
               NUMBA_NUM_THREADS=str(a.threads), NUMBA_CACHE_DIR=str(cache), PYTHONDONTWRITEBYTECODE='1')
    for k in [k for k in env if k.startswith('PYTEST_')]:
        env.pop(k)
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'   # as validate_release.py: no inherited options or plugins
    if not env.get('NUMBA_THREADING_LAYER'):
        tbb = subprocess.run([sys.executable, '-c', 'from numba.np.ufunc import tbbpool'], capture_output=True).returncode == 0
        env['NUMBA_THREADING_LAYER'] = 'tbb' if tbb else 'workqueue'
    layer = env['NUMBA_THREADING_LAYER']
    rows = []

    t = time.time()
    r = subprocess.run([sys.executable, '-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider', '-o', 'addopts=', '-rfEs'],
                       cwd=tree, env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    (work / 'pytest_c8.log').write_text(out)
    summ = [ln for ln in r.stdout.split('\n') if re.search(r'\d+ (passed|failed|error).* in [0-9.]+s', ln)]
    counts = {k: int(v) for v, k in re.findall(r'(\d+) (passed|failed|skipped|errors?|xfailed|xpassed|deselected)',
                                               summ[-1] if summ else '')}
    tail = summ[-1:] or ['no pytest summary line']
    ok = r.returncode == 0 and counts == {'passed': 74}
    rows.append(('test.pytest', ok, f'{tail[0].strip()} ({time.time() - t:.0f} s; Numba threading layer {layer}; '
                                    f'required: 74 passed, nothing else; log {work / "pytest_c8.log"})'))

    t = time.time()
    grid_out = work / 'regression_grid.json'
    if grid_out.exists():
        grid_out.unlink()
    r = subprocess.run([sys.executable, 'scripts/regression_saved_grid.py', '--threads', str(a.threads), '--compare',
                        'benchmarks/REGRESSION_GRID.json', '--output', str(grid_out)],
                       cwd=tree, env=env, capture_output=True, text=True)
    (work / 'regression_grid_c8.log').write_text(r.stdout + r.stderr)
    cmp = {}
    if grid_out.exists():
        g = json.loads(grid_out.read_text())
        cmp = g.get('comparison', {}) if g.get('completed') else {}
    ok = (r.returncode == 0 and cmp.get('points') == 38 and cmp.get('outside_tolerance') == 0)
    rows.append(('test.grid', ok, f"{cmp.get('points', '?')} points, {cmp.get('bitwise_equal', '?')} bitwise equal, "
                                  f"max |dC8| {cmp.get('max_abs_C8', '?')}, outside 1e-7 + 2e-11|ref|: "
                                  f"{cmp.get('outside_tolerance', '?')} ({time.time() - t:.0f} s)"))

    for rid, good, det in rows:
        print(f'{rid:12s}  {"PASS" if good else "FAIL"}  {det}')
    nf = sum(not r[1] for r in rows)
    print(f'# run_tests_c8: {len(rows) - nf} PASS, {nf} FAIL')
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
