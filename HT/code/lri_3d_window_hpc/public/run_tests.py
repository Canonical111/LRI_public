#!/usr/bin/env python3
"""`make -f public.mk test`: the package's validation receipt without the Expanse-only stage.

Same stages as cluster/expanse/receipt.py (which needs the release tarball's RELEASE.sha256 and runs inside a Slurm
job): tests/verify_manifest.py on the shipped tree, then, in a scratch copy of the tree (the validators rewrite
validation/*.json, which MANIFEST.sha256 binds), pytest and the five validators, each of which must write a fresh
report with "passed": true. Prints a PASS/FAIL table and exits 1 on any failure. All comparisons in these tests
are within one process or against stored values with tolerances, so they hold on AMD and Intel alike.
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
VALIDATORS = [('validate_physics', 'tests/validate_physics.py', 'validation/physics_checks.json'),
              ('validate_numerics', 'tests/validate_numerics.py', 'validation/numerical_checks.json'),
              ('validate_large', 'tests/validate_large.py', 'validation/large_independent_checks.json'),
              ('validate_benchmarks', 'tests/validate_benchmarks.py', 'validation/benchmark_audit.json'),
              ('validate_l18_fix', 'tests/validate_l18_fix.py', 'validation/l18_fix/current_checks.json')]   # receipt.py VALIDATORS

def env():
    e = {k: v for k, v in os.environ.items() if not k.startswith(('PYTEST_', 'PYTHONOPTIMIZE'))}
    e['PYTHONDONTWRITEBYTECODE'] = '1'
    return e

def stage(rows, name, cmd, cwd, logs):
    t = time.time()
    with open(logs / f'{name}.log', 'w') as f:
        rc = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, env=env()).returncode
    rows.append([name, rc, time.time() - t, t]); return rc

def main():
    work = PKG / '.work' / 'test'
    if work.exists(): shutil.rmtree(work)
    logs = work / 'logs'; logs.mkdir(parents=True)
    rows = []; py = [sys.executable, '-B']
    stage(rows, 'verify_manifest', [*py, 'tests/verify_manifest.py'], PKG, logs)
    tree = work / 'tree'
    shutil.copytree(PKG, tree, ignore=shutil.ignore_patterns('.work', '__pycache__', '.pytest_cache'))
    stage(rows, 'pytest', [*py, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-o', 'addopts='], tree, logs)
    for name, script, report in VALIDATORS:
        rc = stage(rows, name, [*py, script], tree, logs)
        p = tree / report; started = rows[-1][3]
        try:
            ok = p.stat().st_mtime >= started - 1 and json.loads(p.read_text()).get('passed') is True
        except (OSError, ValueError):
            ok = False
        if rc == 0 and not ok: rows[-1][1] = 1
    print(f"{'stage':<20} {'status':<6} seconds")
    for name, rc, sec, _ in rows: print(f"{name:<20} {'PASS' if rc == 0 else 'FAIL':<6} {sec:7.1f}")
    bad = [r for r in rows if r[1] != 0]
    print(f"{len(rows) - len(bad)}/{len(rows)} stages passed; logs in {logs}")
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
