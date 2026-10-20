#!/usr/bin/env python3
"""Test target of HT_Pert/code/lri_eh_hpc (make -f public.mk test): lri_eh 0.2.0, the isolated g^2 D window add-on.

Stages, each PASS/FAIL (SKIP only where stated):
  manifest   every file of MANIFEST_SHA256.json (102 files) has its sha256; files listed in public/SCRUBBED.txt (written
             by the public scrub, if any) are reported as scrubbed and accepted; any other mismatch or missing file
             FAILS. The verbatim scripts/verify_package.py is run as well when nothing is listed in SCRUBBED.txt (it
             knows no scrub list), otherwise it is reported SKIP with that reason.
  validate   the package's own release validation, on a copy of the package under <work>/pkg (pytest writes caches
             and the validator writes a receipt, so the shipped tree is never touched): python
             scripts/validate_release.py --threads T --output <copy>/validation/public.json = pytest tests/ (32 tests,
             including a one- versus four-thread comparison, hence >= 4 CPUs) plus a gated degree-7 smoke at cutoff
             20, then a sealed receipt. PASS iff the validator exits 0 and the receipt is sealed, passed, and carries
             the source fingerprint of BUILD_INFO.json (2e2e8ca8...).
The shipped tree is not modified. Exit 1 if any stage fails.
usage: python3 public/run_tests_eh.py [--work .work] [--threads 4]"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def scrubbed():
    p = os.path.join(HERE, 'SCRUBBED.txt')
    return {ln.strip() for ln in open(p) if ln.strip() and not ln.startswith('#')} if os.path.exists(p) else set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    rows = []

    def stage(name, fn):
        t0 = time.time()
        try:
            v, det = fn()
        except Exception as e:  # noqa: BLE001
            v, det = 'FAIL', f'{type(e).__name__}: {str(e)[-600:]}'
        rows.append((name, v, f'{det} ({time.time() - t0:.0f} s)'))
        print(f'run_tests_eh  {name:9s} {v}  {rows[-1][2]}', flush=True)

    scr = scrubbed()

    def manifest():
        man = json.load(open(os.path.join(PKG, 'MANIFEST_SHA256.json')))
        bad, sc = [], []
        for k, v in man.items():
            p = os.path.join(PKG, k)
            if not os.path.exists(p):
                bad.append(k + ' (missing)')
            elif sha(p) != v:
                (sc if k in scr else bad).append(k)
        return ('FAIL' if bad else 'PASS'), (f'{len(man) - len(bad) - len(sc)}/{len(man)} identical, {len(sc)} scrubbed '
                                             f'(public/SCRUBBED.txt){"; MISMATCH " + str(bad[:5]) if bad else ""}')

    def verbatim():
        if scr:
            return 'SKIP', f'scripts/verify_package.py not run: {len(scr)} file(s) listed in public/SCRUBBED.txt'
        r = subprocess.run([sys.executable, os.path.join(PKG, 'scripts', 'verify_package.py')], capture_output=True,
                           text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        return ('PASS' if r.returncode == 0 else 'FAIL'), (r.stdout + r.stderr).strip()[-300:]

    def validate():
        cp = os.path.join(work, 'pkg')
        if os.path.exists(cp):
            shutil.rmtree(cp)
        base = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.work*', '.pytest_cache', 'validation',
                                      'runs', 'logs')

        def ignore(d, names):   # never copy the work directory (any WORK, e.g. .work_x) or the public overlay
            out = set(base(d, names))
            out |= {n for n in names if os.path.abspath(os.path.join(d, n)) == work}
            if os.path.abspath(d) == PKG:
                out |= {'public', 'public.mk'} & set(names)
            return out
        shutil.copytree(PKG, cp, ignore=ignore)
        os.makedirs(os.path.join(cp, 'validation'))
        env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', OMP_NUM_THREADS='1',
                   NUMBA_NUM_THREADS=str(max(4, a.threads)), PYTHONDONTWRITEBYTECODE='1')
        env.setdefault('NUMBA_CACHE_DIR', os.path.join(work, 'numba_cache'))
        out = os.path.join(cp, 'validation', 'public.json')
        r = subprocess.run([sys.executable, 'scripts/validate_release.py', '--threads', str(max(4, a.threads)),
                            '--output', out], cwd=cp, env=env, capture_output=True, text=True)
        log = os.path.join(cp, 'validation', 'public.tests.log')
        tail = open(log).read().strip().split('\n')[-1] if os.path.exists(log) else '(no test log)'
        if r.returncode:
            return 'FAIL', f'validate_release.py exit {r.returncode}: {(r.stderr or r.stdout)[-500:]}; pytest: {tail}'
        rec = json.load(open(out))
        body = dict(rec)
        got = body.pop('payload_sha256', None)
        sealed = got == hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'),
                                                  allow_nan=False).encode()).hexdigest()
        build = json.load(open(os.path.join(PKG, 'BUILD_INFO.json')))
        ok = sealed and rec.get('passed') is True and rec.get('source_sha256') == build['source_sha256']
        return ('PASS' if ok else 'FAIL'), (f'pytest: {tail}; degree-7 smoke at cutoff 20 gated; receipt sealed {sealed}, '
                                            f'passed {rec.get("passed")}, source {rec.get("source_sha256", "")[:8]}... = '
                                            f'BUILD_INFO {build["source_sha256"][:8]}...; environment python '
                                            f'{rec["environment"]["python"]}, numpy {rec["environment"]["numpy"]}, numba '
                                            f'{rec["environment"]["numba"]}; receipt {os.path.relpath(out, PKG)}')

    stage('manifest', manifest)
    stage('verbatim', verbatim)
    stage('validate', validate)
    cnt = {v: sum(r[1] == v for r in rows) for v in ('PASS', 'FAIL', 'SKIP')}
    print(f"# test lri_eh_hpc: {cnt['PASS']} PASS, {cnt['FAIL']} FAIL" + (f", {cnt['SKIP']} SKIP" if cnt['SKIP'] else ''))
    open(os.path.join(work, 'test_lri_eh_hpc.txt'), 'w').write('\n'.join(f'{n:9s} {v:4s} {d}' for n, v, d in rows) + '\n')
    sys.exit(1 if cnt['FAIL'] else 0)


if __name__ == '__main__':
    main()
