#!/usr/bin/env python3
"""Fast tests of lri_3d_hpc (make -f public.mk test): the package's own checks, as the production validation
receipt (cluster/receipt.py) ran them, without the site-specific stages (filesystems, MPI launcher, drills).

Stages, each a subprocess with its log in .work/test/logs/:
  manifest          every file against the package's RELEASE_MANIFEST.json (files listed in public/SCRUBBED.txt
                    count as scrubbed; any other difference fails)
  native, stationary, solver, local_bands, vertex_store
                    tests/check_*.py: native kernels, stationary vs recurrence energy series, optimized vs
                    reference solver (cutoffs 0, 2, 4; orders 2..8), banded local products, vertex store
  driver            tests/check_hpc_driver.py on the shipped L4 fixture (serial; MPI only with MPIEXEC=...)
  fixture_raw, fixture_consistent
                    solve the shipped L4 fixture, both schemes, against the original code's reference results
                    (results/reference_coefficients_L14.json) at tolerance 1e-16 (x87 long double)
  build_L14         build the L = 14 vertex store from scratch (code/ht3d_coefficients.py build)
  grid_L14          tests/check_saved_coefficients.py on that store: cutoffs 0..14, both schemes, stationary and
                    recurrence, against the reference within 5e-13 and every recursion residual <= 1e-16. This
                    reruns the check quoted in the HT_Pert note (\\HTpThreeGateL = 14, \\HTpThreeGate about 1e-14).
  mpi2, mpi4        only with MPIEXEC set (a launcher taking "-n N"): tests/check_mpi_backend.py on 2 and 4 ranks

The native library and the numba cache are built in node-local temporary storage (TMPDIR; or set
HT3D_NATIVE_CACHE), as in production. Run from code/lri_3d_hpc. Needs Linux x86-64 (80-bit long double), a C++17 compiler with OpenMP (CXX), Python 3.12
with numpy, scipy, numba, threadpoolctl (public/requirements.txt). Exit status 1 if any stage fails.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get('HT3D_PUBLIC_WORK', PKG / '.work' / 'test')).resolve()
PY = [sys.executable, '-B']
THREADS = str(min(4, len(os.sched_getaffinity(0)))) if hasattr(os, 'sched_getaffinity') else '1'
# The compiled kernel library and the numba cache go to node-local temporary storage (TMPDIR), as in production
# (cluster/env.sh): publishing the library on a parallel file system can fail (BeeGFS: EBUSY on the atomic rename).
NODE = Path(os.environ['HT3D_NATIVE_CACHE']).parent if os.environ.get('HT3D_NATIVE_CACHE') else \
    Path(tempfile.mkdtemp(prefix='lri_3d_hpc_test_'))
NATIVE = Path(os.environ.get('HT3D_NATIVE_CACHE', NODE / 'native'))


def env():
    e = dict(os.environ)
    e.update(OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMBA_NUM_THREADS='1', OMP_NUM_THREADS=THREADS,
             OMP_WAIT_POLICY='PASSIVE', GOMP_SPINCOUNT='0', HT3D_NATIVE_CACHE=str(NATIVE),
             NUMBA_CACHE_DIR=str(NODE / 'numba'), PYTHONDONTWRITEBYTECODE='1')
    return e


def manifest_check():
    """RELEASE_MANIFEST.json (sha256-file-manifest-v1) against the shipped files, honouring public/SCRUBBED.txt."""
    m = json.loads((PKG / 'RELEASE_MANIFEST.json').read_text())
    scrubbed = {l.strip() for l in (PKG / 'public/SCRUBBED.txt').read_text().splitlines()
                if l.strip() and not l.startswith('#')} if (PKG / 'public/SCRUBBED.txt').exists() else set()
    bad, missing, seen = [], [], 0
    for name, e in sorted(m['files'].items()):
        p = PKG / name
        if not p.is_file():
            missing.append(name)
            continue
        seen += 1
        b = p.read_bytes()
        if (hashlib.sha256(b).hexdigest() != e['sha256'] or len(b) != e['bytes']) and name not in scrubbed:
            bad.append(name)
    stale = sorted(n for n in scrubbed if n not in m['files'])
    print(f'  {len(m["files"])} files in RELEASE_MANIFEST.json, {seen} present, {len(scrubbed)} scrubbed, '
          f'{len(bad)} differ, {len(missing)} missing, {len(stale)} SCRUBBED entries not in the manifest')
    for n in (bad + missing + stale)[:10]:
        print('   ', n)
    return not bad and not missing and not stale


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / 'logs').mkdir(parents=True)
    rep = WORK / 'reports'
    rep.mkdir()
    native, fixture, ref = NATIVE, PKG / 'fixtures/vertices_L4', PKG / 'results/reference_coefficients_L14.json'
    stages = [
        ('native', PY + ['tests/check_native_backend.py', '--cache-dir', native, '--output', rep / 'native.json']),
        ('stationary', PY + ['tests/check_stationary_independent.py', '--cache-dir', native, '--output', rep / 'stationary.json']),
        ('solver', PY + ['tests/check_optimized_solver.py', '--backend', 'native', '--native-cache', native,
                         '--output', rep / 'solver.json']),
        ('local_bands', PY + ['tests/check_local_bands.py', '--native-cache', native, '--output', rep / 'local_bands.json']),
        ('vertex_store', PY + ['tests/check_vertex_store.py']),
        ('driver', PY + ['tests/check_hpc_driver.py', '--store', fixture, '--native-cache', native,
                         '--work', WORK / 'driver', '--output', rep / 'driver.json']
                   + (['--mpiexec', os.environ['MPIEXEC']] if os.environ.get('MPIEXEC') else [])),
    ]
    for scheme in ('raw', 'consistent'):
        stages.append((f'fixture_{scheme}', PY + ['code/ht3d_coefficients.py', 'solve', '--store', fixture, '--cutoff', '4',
                                                  '--scheme', scheme, '--threads', THREADS, '--native-cache', native,
                                                  '--output', rep / f'fixture_{scheme}.json', '--compare-reference', ref,
                                                  '--tolerance', '1e-16', '--lock-dir', WORK / 'locks']))
    stages += [
        ('build_L14', PY + ['code/ht3d_coefficients.py', 'build', '--cutoff', '14', '--order', '8',
                            '--store', WORK / 'stores/L14', '--spill', WORK / 'spill']),
        ('grid_L14', PY + ['tests/check_saved_coefficients.py', '--store', WORK / 'stores/L14', '--threads', THREADS,
                           '--strategies', 'stationary', 'recurrence', '--output', rep / 'grid.json']),
    ]
    if os.environ.get('MPIEXEC'):
        for n in ('2', '4'):
            stages.append((f'mpi{n}', [os.environ['MPIEXEC'], '-n', n, sys.executable, '-B', '-m', 'mpi4py',
                                       'tests/check_mpi_backend.py', '--native-cache', native, '--output', rep / f'mpi{n}.json']))
    results = []
    t0 = time.time()
    print('stage manifest')
    results.append(('manifest', manifest_check(), 0.0))
    for name, cmd in stages:
        t = time.time()
        with open(WORK / 'logs' / f'{name}.log', 'w') as log:
            rc = subprocess.run([str(c) for c in cmd], cwd=PKG, env=env(), stdout=log, stderr=subprocess.STDOUT).returncode
        dt = time.time() - t
        results.append((name, rc == 0, dt))
        status = 'PASS' if rc == 0 else 'FAIL (rc=%d, log %s)' % (rc, WORK / 'logs' / (name + '.log'))
        print(f'stage {name:<20} {status}  {dt:.1f} s', flush=True)
    # grid_L14 facts, as the receipt's grid_facts: 32 cases passed, every recursion residual <= 1e-16
    ok = False
    if (rep / 'grid.json').exists():
        g = json.loads((rep / 'grid.json').read_text())
        res = max(float(r['result']['max_scaled_seed_recursion_residual']) for r in g['rows'])
        by = {s: max(float(r['validation']['max_scaled_error']) for r in g['rows'] if r['strategy'] == s)
              for s in ('stationary', 'recurrence')}
        ok = g.get('passed') is True and g.get('cases') == 32 and res <= 1e-16
        print(f'  grid_L14: {g.get("cases")} cases, max scaled error vs the original code {float(g["max_scaled_error"]):.2e} '
              f'(stationary {by["stationary"]:.1e}, recurrence {by["recurrence"]:.1e}; tolerance 5e-13), '
              f'max recursion residual {res:.1e} (limit 1e-16)')
    results.append(('grid_L14_facts', ok, 0.0))
    print(f'stage {"grid_L14_facts":<20} {"PASS" if ok else "FAIL"}')
    fails = [n for n, ok, _ in results if not ok]
    print(f'\n{len(results) - len(fails)}/{len(results)} stages passed in {time.time() - t0:.0f} s'
          + (f'; FAIL: {" ".join(fails)}' if fails else '') + f'  (logs and reports in {WORK})')
    if not os.environ.get('HT3D_NATIVE_CACHE'):
        shutil.rmtree(NODE, ignore_errors=True)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
