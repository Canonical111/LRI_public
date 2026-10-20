#!/usr/bin/env python3
"""Fast tests of lri_3d_c4_exact (make -f public.mk test): recompute the exact finite-cutoff sums at small cutoffs
from scratch and compare them with the shipped production results, the production package lri_3d_hpc and the
brute force on the package's own operators.

Stages (each a subprocess; logs and outputs in .work/test/):
  windows     windows3d.py  --Lmax 400   vs results/windows_L8000.npz (C2, vacuum and zero-mode windows), L <= 400
  offdiag     offdiag3d.py  --Lmax 200   vs results/offdiag_L400.npz (full zero-mode window, every class), L <= 200
  dchi        dchi3d.py     --Lmax 120   vs results/dchi_L120.npz (chi-attached sunset window)
  c4          c4_run3d.py   --Lmax 40    vs results/c4_L600.npz (C2, C3, C4 raw and consistent, r, g), L <= 40;
              then validate_pkg.py on it: against the package (reference L <= 14, campaign records L = 16..20)
  c5          eps5/prod5.py --Lmax 12    (C2..C5 in every scheme) vs results/c5_L20.npz, L <= 12; then
              eps5/validate5.py on it: against the package and the brute force (results/brute)
  shifts      eps5/delta5.py --Lmax 20 vs results/dC5_L200.npz; eps5/legw3d.py --Lmax 40 vs results/eps5/legw_L400.npz
  brute       eps5/brute3d_W5.py --L 4 (package operators, explicit windows) vs results/brute/brute_L4.json;
              brute_zm.py --cutoffs 0 2 4 vs results/brute_zm_L6.json
Comparisons use the scaled difference |a - b| / max(1, |b|) over every array both files have, at their common L.
Tolerances: 1e-12 where the same arithmetic is repeated (windows, offdiag, c5 and its validations, brute force);
1e-11 for the window shifts (delta5, legw: production with Lmax 200/400, other angular quadrature); 1e-10 for dchi
(r2, |r2| ~ 10, summed on another platform: 2e-11 measured); 1e-9 for c4 (production Lmax 600: the README measures
7e-10 between runs with different Lmax).

Run from code/lri_3d_c4_exact. Needs Python >= 3.10 with numpy, scipy, mpmath (public/requirements.txt), and the
sibling package ../lri_3d_hpc (its reference operators need numba). Exit status 1 if any stage fails.
"""
import contextlib, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get('C4X_PUBLIC_WORK', PKG / '.work' / 'test')).resolve()
PERT = Path(os.environ.get('C4X_PERT', PKG / '../lri_3d_hpc')).resolve()
RECORDS = Path(os.environ.get('C4X_RECORDS', PKG / '../../data/HT_3d/pert3d/results')).resolve()
WORKERS = str(max(1, min(8, len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else 1)))
NODE = Path(tempfile.mkdtemp(prefix='lri_3d_c4_exact_test_'))   # caches: node-local (TMPDIR)


def env():
    e = dict(os.environ)
    e.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMBA_NUM_THREADS='1',
             NUMBA_CACHE_DIR=str(NODE / 'numba'), PYTHONDONTWRITEBYTECODE='1')
    return e


def npz_diff(new, ref, keys=None, Lmax=None):
    import numpy as np
    a, b = np.load(new), np.load(ref)
    La, Lb = [int(x) for x in a['L']], [int(x) for x in b['L']]
    common = [l for l in La if l in Lb and (Lmax is None or l <= Lmax)]
    ia, ib = [La.index(l) for l in common], [Lb.index(l) for l in common]
    names = sorted(k for k in set(a.files) & set(b.files) if k != 'L' and (keys is None or k in keys))
    worst, where = 0.0, ''
    for k in names:
        x, y = np.asarray(a[k], dtype=float), np.asarray(b[k], dtype=float)
        if x.ndim == 0 or x.shape[-1] != len(La):        # arrays indexed by L in their last axis only
            continue
        d = float(np.max(np.abs(x[..., ia] - y[..., ib]) / np.maximum(1.0, np.abs(y[..., ib]))))
        if d > worst:
            worst, where = d, k
    return worst, where, len(common), len(names)


def json_brute(new, ref):
    a, b = json.loads(Path(new).read_text()), json.loads(Path(ref).read_text())
    worst = 0.0
    for v, r in b['results'].items():
        for x, y in zip(a['results'][v]['C'], r['C']):
            worst = max(worst, abs(x - y) / max(1.0, abs(y)))
    return worst


def json_zm(new, ref):
    a = {r['L']: r for r in json.loads(Path(new).read_text())}
    b = {r['L']: r for r in json.loads(Path(ref).read_text())}
    worst = 0.0
    for L in a:
        for k in ('C4raw', 'C4cons', 'C4zm'):
            worst = max(worst, abs(a[L][k] - b[L][k]) / max(1.0, abs(b[L][k])))
    return worst, sorted(a)


def validate(script, argv):
    """Run validate_pkg.py / eps5/validate5.py with their package paths pointed to the public layout."""
    spec = importlib.util.spec_from_file_location(Path(script).stem + '_t', PKG / script)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.PKG, m.CAMP = str(PERT / 'results/reference_coefficients_L14.json'), str(RECORDS)
    buf, old = io.StringIO(), sys.argv
    sys.argv = [script] + [str(x) for x in argv]
    try:
        with contextlib.redirect_stdout(buf):
            m.main()
    finally:
        sys.argv = old
    return buf.getvalue()


def main():
    import re
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / 'logs').mkdir(parents=True)
    R = PKG / 'results'
    results = []

    def run(name, cmd, cwd=PKG):
        t = time.time()
        with open(WORK / 'logs' / f'{name}.log', 'w') as log:
            rc = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env(), stdout=log, stderr=subprocess.STDOUT).returncode
        return rc, time.time() - t

    def check(name, ok, detail, dt):
        results.append((name, ok))
        print(f'stage {name:<14} {"PASS" if ok else "FAIL"}  {dt:6.1f} s  {detail}', flush=True)

    py = [sys.executable, '-B']
    # windows, offdiag, dchi
    for name, cmd, new, ref, Lm, tol in (
            ('windows', py + ['windows3d.py', '--Lmax', 400, '--out', WORK / 'windows_L400.npz'],
             WORK / 'windows_L400.npz', R / 'windows_L8000.npz', 400, 1e-12),
            ('offdiag', py + ['offdiag3d.py', '--Lmax', 200, '--out', WORK / 'offdiag_L200.npz'],
             WORK / 'offdiag_L200.npz', R / 'offdiag_L400.npz', 200, 1e-12),
            ('dchi', py + ['dchi3d.py', '--Lmax', 120, '--out', WORK / 'dchi_L120.npz'],
             WORK / 'dchi_L120.npz', R / 'dchi_L120.npz', 120, 1e-10)):
        rc, dt = run(name, cmd)
        if rc:
            check(name, False, f'rc={rc}', dt)
            continue
        d, k, nL, nk = npz_diff(new, ref, Lmax=Lm)
        check(name, d <= tol, f'{nk} arrays, {nL} cutoffs: max scaled diff {d:.1e} ({k}); tol {tol:g}', dt)
    # c4 and its package validation
    rc, dt = run('c4', py + ['c4_run3d.py', '--Lmax', 40, '--workers', WORKERS, '--cache', NODE / 'c4cache',
                             '--out', WORK / 'c4_L40.npz'])
    if rc:
        check('c4', False, f'rc={rc}', dt)
    else:
        d, k, nL, nk = npz_diff(WORK / 'c4_L40.npz', R / 'c4_L600.npz', Lmax=40)
        check('c4', d <= 1e-9, f'{nk} arrays, {nL} cutoffs vs c4_L600: max scaled diff {d:.1e} ({k}); tol 1e-9', dt)
        t = time.time()
        v = validate('validate_pkg.py', [WORK / 'c4_L40.npz'])
        w = [float(l.split()[2]) for l in v.split('per quantity:')[1].splitlines() if l.strip()]
        (WORK / 'validate_pkg.txt').write_text(v)
        check('c4_vs_pkg', max(w) <= 1e-12, f'C2..C4, r, g, seed energies vs package L <= 20: {max(w):.1e}; tol 1e-12',
              time.time() - t)
    # c5 (every scheme) and its validation
    rc, dt = run('c5', py + ['prod5.py', '--Lmax', 12, '--workers', WORKERS, '--cache', NODE / 'c5cache',
                             '--out', WORK / 'c5_L12.npz'], cwd=PKG / 'eps5')
    if rc:
        check('c5', False, f'rc={rc}', dt)
    else:
        d, k, nL, nk = npz_diff(WORK / 'c5_L12.npz', R / 'c5_L20.npz', Lmax=12)
        check('c5', d <= 1e-12, f'{nk} arrays, {nL} cutoffs vs c5_L20: max scaled diff {d:.1e} ({k}); tol 1e-12', dt)
        t = time.time()
        v = validate('eps5/validate5.py', [WORK / 'c5_L12.npz', R / 'brute'])
        (WORK / 'validate5.txt').write_text(v)
        w = [float(x) for x in re.findall(r'worst (?:raw|consistent) +C\d: ([0-9.e-]+)', v)]
        wb = [float(x) for x in re.findall(r'worst \|diff\| +\w+ +C\d: ([0-9.e-]+)', v)]
        ok = bool(w) and bool(wb) and max(w) <= 1e-12 and max(wb) <= 1e-12
        check('c5_vs_pkg', ok, f'vs package {max(w or [9]):.1e}, vs brute force {max(wb or [9]):.1e}; tol 1e-12', time.time() - t)
    # window shifts of C5 and the leg response S(L)
    for name, cmd, new, ref, Lm, tol in (
            ('delta5', py + ['delta5.py', '--Lmax', 20, '--workers', WORKERS, '--cache', NODE / 'dcache',
                             '--out', WORK / 'dC5_L20.npz'], WORK / 'dC5_L20.npz', R / 'dC5_L200.npz', 20, 1e-11),
            ('legw', py + ['legw3d.py', '--Lmax', 40, '--out', WORK / 'legw_L40.npz'],
             WORK / 'legw_L40.npz', R / 'eps5/legw_L400.npz', 40, 1e-11)):
        rc, dt = run(name, cmd, cwd=PKG / 'eps5')
        if rc:
            check(name, False, f'rc={rc}', dt)
            continue
        d, k, nL, nk = npz_diff(new, ref, Lmax=Lm)
        check(name, d <= tol, f'{nk} arrays, {nL} cutoffs: max scaled diff {d:.1e} ({k}); tol {tol:g}', dt)
    # brute force on the package's own operators
    rc, dt = run('brute_W5', py + ['brute3d_W5.py', '--L', 4, '--out', WORK / 'brute_L4.json'], cwd=PKG / 'eps5')
    check('brute_W5', rc == 0 and json_brute(WORK / 'brute_L4.json', R / 'brute/brute_L4.json') <= 1e-12,
          f'rc={rc}' + (f', C2..C5 of raw, W2, W3m, Wb, Wc, Zb vs brute_L4.json: '
                        f'{json_brute(WORK / "brute_L4.json", R / "brute/brute_L4.json"):.1e}; tol 1e-12' if rc == 0 else ''), dt)
    rc, dt = run('brute_zm', py + ['brute_zm.py', '--cutoffs', 0, 2, 4, '--out', WORK / 'brute_zm.json'])
    if rc:
        check('brute_zm', False, f'rc={rc}', dt)
    else:
        d, Ls = json_zm(WORK / 'brute_zm.json', R / 'brute_zm_L6.json')
        check('brute_zm', d <= 1e-12, f'C4 raw, consistent, zero-mode window at L = {Ls} vs brute_zm_L6.json: {d:.1e}; tol 1e-12', dt)

    shutil.rmtree(NODE, ignore_errors=True)
    fails = [n for n, ok in results if not ok]
    print(f'\n{len(results) - len(fails)}/{len(results)} stages passed' + (f'; FAIL: {" ".join(fails)}' if fails else '')
          + f'  (logs in {WORK / "logs"})')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
