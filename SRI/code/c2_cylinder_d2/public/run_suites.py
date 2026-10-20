#!/usr/bin/env python3
"""The package's own test suites, run without git history and without cluster access (new tool, 2026-10-15).
Run from code/c2_cylinder_d2/.

Runs each suite through its own verbatim entry point and reads the unittest verbose output:
  code/continuum/test_continuum.py   in place (it reads the shipped records under data/ and outputs/);
  cluster/test_cluster.py, cluster/sitekit/test_sitekit.py, cluster/expanse/test_expanse.py,
  cluster/symmetry/test_symmetry.py  in a code copy under <work>/suites/lri_c2 that carries STAGE_INFO.json and
                                     STAGE_MANIFEST.sha256, the two files cluster/sitekit/make_tarball.sh adds to a
                                     staged code copy; test_sitekit builds its test tarball from them when the package
                                     is not a git checkout (its documented second path). No scheduler is contacted:
                                     the suites use a fake squeue/sbatch and dry runs.
Git is hidden from every suite (GIT_CEILING_DIRECTORIES above the package; the export has no .git), so the tests
that need the source repository's history skip, each with its own message. Accepted skips (anything else fails):
  * 'needs the git checkout (pristine commit 474487c)': test_continuum Legacy A6-2 (same-platform byte identity of the
    legacy outputs with the scripts of the pristine commit 474487c, the supplied study as received) and IR2-003 (the
    same check under an inherited LRI_TAIL_CUTOFF). They stage that commit with `git archive`; the public export has
    no history. The receipt of that check on the production machine ships as
    results/continuum_2026-10/evidence/legacy_macos/legacy_reproduction.json (same_platform_pristine: 3 of 3 files
    byte-identical) and the replay reads it; the cross-platform half of A1 runs here.
  * 'needs the git checkout': three sitekit tests of make_tarball.sh (it archives a git commit).
  * 'needs GNU coreutils (Linux)': sitekit publish/fetch tests on systems without GNU sha256sum/mv (macOS).
Usage: python3 public/run_suites.py [--work DIR] [--python PY] [--out FILE]
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

from c2cyl_common import L, PKG

ALLOWED_SKIPS = {
    'needs the git checkout (pristine commit 474487c)':
        'A6-2 needs the source repository history (git archive 474487c); its production-machine receipt ships in '
        'evidence/legacy_macos/legacy_reproduction.json',
    'needs the git checkout': 'make_tarball.sh archives a git commit; the public export is not the source repository',
    'needs GNU coreutils (Linux)': 'GNU sha256sum/mv only',
}
COPY_EXCLUDE = {'.work', 'outputs', 'results', 'note', 'public', 'public.mk'}


def code_copy(dest: Path) -> Path:
    """A copy of the package (code, cluster, scripts, data) with STAGE_INFO.json and STAGE_MANIFEST.sha256 in the format
    of cluster/sitekit/make_tarball.sh (sha256 of every other file, sorted bytewise)."""
    root = dest / 'lri_c2'
    shutil.rmtree(dest, ignore_errors=True)
    root.mkdir(parents=True)
    for p in PKG.iterdir():
        if p.name in COPY_EXCLUDE or p.name.startswith('.'):
            continue
        (shutil.copytree(p, root / p.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
         if p.is_dir() else shutil.copy2(p, root / p.name))
    files = sorted((str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()), key=lambda s: s.encode())
    digest = hashlib.sha256('\n'.join(files).encode()).hexdigest()[:12]
    info = dict(name=f'lri_c2_{digest}', commit='public export of commit 98e1935 (no git history)', archived_tree=None,
                dirty=False, created_utc='2026-10-14T00:00:00Z', created_utc_is='fixed (public export)',
                git_files=len(files), scope='Public-export code copy for the test suites (made by public/run_suites.py).')
    (root / 'STAGE_INFO.json').write_text(json.dumps(info, indent=2) + '\n')
    files = sorted((str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()), key=lambda s: s.encode())
    lines = [f'{hashlib.sha256((root / f).read_bytes()).hexdigest()}  {f}' for f in files]
    (root / 'STAGE_MANIFEST.sha256').write_text('\n'.join(lines) + '\n')
    return root


def run_suite(name, argv, cwd, env, logdir):
    t0 = time.time()
    r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    log = r.stdout + r.stderr
    (logdir / (name.replace('/', '_') + '.log')).write_text(log)
    res = {'ok': 0, 'FAIL': 0, 'ERROR': 0, 'skipped': []}
    head = re.compile(r'^(test\w+) \(([^)]*)\)')
    tail = re.compile(r' \.\.\. (ok|FAIL|ERROR|skipped \'(.*)\')$')
    pending = None
    for line in log.splitlines():         # verbose unittest: "test (id) ... ok", or "test (id)" + docstring line + " ... ok"
        h = head.match(line)
        if h:
            pending = h.group(2)
        t = tail.search(line)
        if t and pending:
            if t.group(1).startswith('skipped'):
                res['skipped'].append((pending, t.group(2)))
            else:
                res[t.group(1)] += 1
            pending = None
    ran = re.search(r'^Ran (\d+) tests? in', log, re.M)
    status = 'OK' if re.search(r'^OK\b', log, re.M) else ('FAILED' if re.search(r'^FAILED\b', log, re.M) else '?')
    return dict(exit=r.returncode, ran=int(ran.group(1)) if ran else 0, status=status, seconds=time.time() - t0, **res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG / '.work' / 'suites'))
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--out', default=str(PKG / '.work' / 'run_suites.txt'))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    logs = work / 'logs'
    shutil.rmtree(logs, ignore_errors=True)
    logs.mkdir(parents=True)
    T = L.Table('c2_cylinder_d2 test suites (git-free, no cluster)')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', MPLBACKEND='Agg', GIT_CEILING_DIRECTORIES=str(PKG.parent))
    env.pop('LRI_TAIL_CUTOFF', None)
    if (PKG / '.git').exists():
        T.add('git', 'INFO', 'this package folder is a git checkout', 'export without .git', 'suites run as in the source repository')
    suites = [('code/continuum/test_continuum.py', [a.python, 'code/continuum/test_continuum.py', '-v',
                                                    '--output', str(logs / 'test_continuum.json')], PKG)]
    copy = code_copy(work / 'copy')
    env_copy = dict(env, GIT_CEILING_DIRECTORIES=str(copy.parent))
    for s in ('cluster/test_cluster.py', 'cluster/sitekit/test_sitekit.py', 'cluster/expanse/test_expanse.py',
              'cluster/symmetry/test_symmetry.py'):
        suites.append((s, [a.python, s, '--output', str(logs / (Path(s).stem + '.json'))], copy))
    for name, argv, cwd in suites:
        r = run_suite(name, argv, cwd, env_copy if cwd == copy else env, logs)
        bad_skips = [f'{t}: {why}' for t, why in r['skipped'] if why not in ALLOWED_SKIPS]
        ok = r['exit'] == 0 and r['status'] == 'OK' and not r['FAIL'] and not r['ERROR'] and not bad_skips and r['ran'] > 0
        why = sorted({w for _, w in r['skipped']})
        T.check(name, ok, f"ran {r['ran']}, ok {r['ok']}, fail {r['FAIL']}, error {r['ERROR']}, skipped {len(r['skipped'])} "
                f"({'; '.join(why) or 'none'}), {r['seconds']:.0f} s" + (f'; unexpected skips {bad_skips[:2]}' if bad_skips else ''),
                'exit 0, no failure, only the stated skips', 'verbatim suite; log in <work>/logs/')
        for t, w in r['skipped']:
            if w in ALLOWED_SKIPS:
                T.add('  skip ' + t.split('.')[-1], 'SKIP', w, '', ALLOWED_SKIPS[w])
    sys.exit(T.report(a.out))


if __name__ == '__main__':
    main()
