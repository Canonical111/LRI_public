#!/usr/bin/env python3
"""Test target of HT_Pert/code/lri_hpc_Hamitonian (make -f public.mk test).

The package's suite rewrites three files of benchmarks/ (review finding F7) and test_lane_claims needs a frozen
checkout (a GIT_SHA file), so the suite runs on a copy: <work>/pkg (the package without analysis/ other than
analysis/extended, which tests/test_extended_merge.py needs, plus analysis_original/). Stages, each PASS/FAIL:
  suite        python tests/run_all.py in the copy (11 scripts: ranking and operators against the original reference
               scripts, solver vs reference at Lambda 4..32, uncapped full recursion, restart, simulated distribution,
               int64 shard, gates, campaign planner, two-lane claims, overlap-checked merge of the extended analysis).
               Needs >= 4 CPUs (NUMBA_NUM_THREADS=4), flock on a local file system, about 5-10 min with JIT.
  regression   the production validation V: python -m lri_hpc thermal d7 at Lambda 40, 50, phi6 d5 at 50, phi6 d3 at
               128 (THREADS threads), then cluster/expanse/check_regression.py (the package's tolerance
               1e-7 + 2e-11 |ref| against validation_data/, and the gates). Seconds each, < 2 GB.
  identity     analysis/extended/check_identity.py on the shipped tree (read only): the extended model code and saved
               rows are byte-identical to analysis_original.
  engines      public/engine_smokes.py (ht5.py 2 4, htb5_exact.py 16, topsum.py 8 16 32 64 against their records).
The shipped tree is not modified. Exit 1 if any stage fails.
usage: python3 public/run_tests.py [--work .work] [--threads 4] [--skip suite,regression,identity,engines]"""
import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
GIT_REF = 'c55d134'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--skip', default='')
    a = ap.parse_args()
    skip = set(filter(None, a.skip.split(',')))
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               BLIS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    env.setdefault('NUMBA_CACHE_DIR', os.path.join(work, 'numba_cache'))
    rows = []

    def stage(name, fn):
        if name in skip:
            rows.append((name, 'SKIP', 'skipped on request'))
            return
        t0 = time.time()
        try:
            ok, det = fn()
        except Exception as e:  # noqa: BLE001
            ok, det = False, f'{type(e).__name__}: {str(e)[-600:]}'
        rows.append((name, 'PASS' if ok else 'FAIL', f'{det} ({time.time() - t0:.0f} s)'))
        print(f"run_tests  {name:10s} {rows[-1][1]}  {rows[-1][2]}", flush=True)

    cp = os.path.join(work, 'pkg')

    def make_copy():
        if os.path.exists(cp):
            shutil.rmtree(cp)
        os.makedirs(cp)
        ign = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.work', '.numba_cache')
        for x in sorted(os.listdir(PKG)):
            s = os.path.join(PKG, x)
            if x in ('analysis', 'public', '.work', 'public.mk') or x.startswith('.'):
                continue
            (shutil.copytree if os.path.isdir(s) else shutil.copy2)(s, os.path.join(cp, x), **(
                {'ignore': ign} if os.path.isdir(s) else {}))
        shutil.copytree(os.path.join(PKG, 'analysis', 'extended'), os.path.join(cp, 'analysis', 'extended'), ignore=ign)
        open(os.path.join(cp, 'GIT_SHA'), 'w').write(GIT_REF + '\n')

    def suite():
        make_copy()
        log = os.path.join(work, 'tests.log')
        e = dict(env, NUMBA_NUM_THREADS=str(max(4, a.threads)))
        with open(log, 'w') as fh:
            r = subprocess.run([sys.executable, 'tests/run_all.py'], cwd=cp, env=e, stdout=fh, stderr=subprocess.STDOUT)
        tail = open(log).read().strip().split('\n')[-2:]
        return r.returncode == 0, f'tests/run_all.py exit {r.returncode}; log {os.path.relpath(log, PKG)}: {" | ".join(tail)}'

    def regression():
        if not os.path.exists(cp):
            make_copy()
        out = os.path.join(work, 'reg')
        if os.path.exists(out):
            shutil.rmtree(out)
        e = dict(env, NUMBA_NUM_THREADS=str(a.threads))
        for task, deg, cuts, sub in (('thermal', 7, ['40', '50'], 'thermal'), ('phi6', 5, ['50'], 'phi6_5'),
                                     ('phi6', 3, ['128'], 'phi6_3')):
            r = subprocess.run([sys.executable, '-m', 'lri_hpc', '--task', task, '--degree', str(deg), '--cutoffs'] + cuts +
                               ['--threads', str(a.threads), '--output-dir', os.path.join(out, sub)], cwd=cp, env=e,
                               capture_output=True, text=True)
            if r.returncode:
                return False, f'lri_hpc {task} d{deg} failed: {r.stderr[-400:]}'
        r = subprocess.run([sys.executable, os.path.join(PKG, 'cluster', 'expanse', 'check_regression.py'), out,
                            os.path.join(work, 'regression.json')], cwd=PKG, env=env, capture_output=True, text=True)
        lines = [ln for ln in r.stdout.split('\n') if ln.startswith(('PASS', 'FAIL'))]
        return r.returncode == 0, f'check_regression.py: {sum(ln.startswith("PASS") for ln in lines)}/{len(lines)} PASS ' \
            f'(thermal d7 L40/50 C, phi6 d5 L50 and d3 L128 D6, gates)'

    def identity():
        r = subprocess.run([sys.executable, os.path.join(PKG, 'analysis', 'extended', 'check_identity.py')],
                           cwd=PKG, env=env, capture_output=True, text=True)
        return r.returncode == 0, (r.stdout + r.stderr).strip()[-300:]

    def engines():
        r = subprocess.run([sys.executable, os.path.join(HERE, 'engine_smokes.py'), '--work', work], cwd=PKG, env=env,
                           capture_output=True, text=True)
        return r.returncode == 0, ' | '.join(ln.split('  ', 1)[-1] for ln in r.stdout.strip().split('\n'))[-600:]

    stage('identity', identity)
    stage('engines', engines)
    stage('suite', suite)
    stage('regression', regression)
    nf = sum(r[1] == 'FAIL' for r in rows)
    print(f"# test lri_hpc_Hamitonian: {sum(r[1] == 'PASS' for r in rows)} PASS, {nf} FAIL"
          f"{', ' + str(sum(r[1] == 'SKIP' for r in rows)) + ' SKIP' if any(r[1] == 'SKIP' for r in rows) else ''}")
    open(os.path.join(work, 'test_lri_hpc_Hamitonian.txt'), 'w').write(
        '\n'.join(f'{n:10s} {v:4s} {d}' for n, v, d in rows) + '\n')
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
