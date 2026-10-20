#!/usr/bin/env python3
"""Fast test of the indep_d1 package (new tool, 2026-10-15). Run from code/indep_d1/. A few minutes on one node.
 1. the dated snapshot (public/SNAPSHOT.sha256): each file matches its original pin, or the published sha256 of
    RE-PINNED.json (files scrubbed of the personal desktop's name and re-pinned), or is listed in public/SCRUBBED.txt
    (presence only);
 2. the SHA-256 values the project recorded for its own records (engine deliverables, sealed comparison files, framework
    production record, RESULTS json files) against the shipped files;
 3. the framework's unit tests (framework/run_tests.sh list, run one by one in a work copy). Two of them read the
    compendium, which SRI/ ships as the sibling package ../dual_d1: test_c8 compares the derived B_old with the
    compendium's appendix (its TeX source is not shipped since 2026-10-17; a stand-in rebuilt from the verbatim blocks of
    ../dual_d1/public/compendium_extract.json, at their original lines, is placed where derive_C8.py looks for
    note/LRI_perturbation_compendium.tex), and test_archive_pipeline
    feeds the archive's raw coefficients through the framework and compares with the archived inputs
    (data/archived/C8_full_numerical_completion/data/F3_final_100.json; the script's absolute path is re-pointed in the
    work copy). Both give SKIP when ../dual_d1 is absent;
 4. the engine: built from engine/src with engine/slurm/build.sh (x86-64-v3, C++17, OpenMP), then four production
    chunks of engine/runs/prod_6digit (3 and 5 kinks, angular and full geometry, about 40 core-s) are rerun from their
    shipped .cfg (same lattice, seed, N, shifts) and compared with the shipped outputs (*.cfg.json).
Usage: python3 public/selftest_indep.py [--work DIR] [--skip-engine] [--skip-framework]
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
import sri_lib as SL  # noqa: E402

FW_TESTS = ['test_strict_missing', 'test_error_model', 'test_replicates', 'test_pmax', 'test_module_vs_sympy',
            'test_normalization', 'test_vs_spec', 'test_c8']
FIXTURES = ['A3_base_k0_c000.cfg', 'A3_E_k0_c000.cfg', 'Z4_base_k-2_c000.cfg', 'A5_base_k0_c000.cfg']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def repinned():
    """original sha256 -> published sha256 of the files re-pinned after the scrub of the personal desktop's name
    (RE-PINNED.json at the package root, from the repinned overlay)"""
    f = PKG/'RE-PINNED.json'
    if not f.exists():
        return {}
    return {r['original_sha256']: r['published_sha256'] for r in json.loads(f.read_text())['files']}


def snapshot(T):
    """public/SNAPSHOT.sha256 (original pins): a file passes if it matches its pin, or the published sha256 that
    RE-PINNED.json maps the pin to, or is listed in public/SCRUBBED.txt (written by the public repository's scrub:
    presence only)"""
    S, RP = scrubbed(), repinned()
    bad, n, nr, ns = [], 0, 0, 0
    for line in (HERE/'SNAPSHOT.sha256').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        h, rel = line.split(None, 1)
        n += 1
        p = PKG/rel
        if not p.exists():
            bad.append(rel + ' (missing)')
            continue
        g = sha(p)
        if g == h:
            continue
        if RP.get(h) == g:
            nr += 1
        elif rel in S:
            ns += 1
        else:
            bad.append(rel)
    T.check('verbatim snapshot', not bad, '%d files (%d re-pinned, %d scrubbed: presence only)%s' % (
        n, nr, ns, '; differ: %s' % bad[:4] if bad else ''), 'original or re-pinned sha256',
        'public/SNAPSHOT.sha256 (dated snapshot) with RE-PINNED.json and public/SCRUBBED.txt')


def scrubbed():
    f = HERE/'SCRUBBED.txt'
    if not f.exists():
        return set()
    return {l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')}


def recorded_hashes(T):
    """(list, base) pairs: every line '<sha256>  <path>' resolved against base"""
    S, RP = scrubbed(), repinned()
    lists = [('engine/runs/c8tierA/SHA256SUMS_results.txt', 'engine'), ('engine/runs/c8BC_SHA256SUMS.txt', 'engine'),
             ('spec/SHA256SUMS', 'spec'), ('spec/comparison/SHA256SUMS', 'spec'),
             ('spec/comparison_C8/SHA256SUMS', 'spec/comparison_C8'), ('framework/out/C8_production.json.sha256', 'framework/out'),
             ('RESULTS_C8_independent.json.sha256', '.'), ('RESULTS_C8_independent_tierA.json.sha256', '.')]
    for lst, base in lists:
        bad, n, ns = [], 0, 0
        for line in (PKG/lst).read_text().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            h, rel = line.split()[:2]
            rel = os.path.normpath(os.path.join(base, rel))
            n += 1
            if not (PKG/rel).exists():
                bad.append(rel + ' (missing)')
            elif rel in S:
                ns += 1
            elif sha(PKG/rel) != h and RP.get(h) != sha(PKG/rel):
                bad.append(rel)
        T.check('recorded sha256: ' + lst, not bad, '%d files (%d scrubbed: presence only)%s' % (n, ns, '; differ: %s' % bad if bad else ''),
                'all equal', 'hashes the project recorded when it wrote these records')
    # hashes recorded inside the result files
    c2 = json.loads((PKG/'RESULTS_archive_comparison.json').read_text())
    c8 = json.loads((PKG/'RESULTS_C8_archive_comparison.json').read_text())
    i8 = json.loads((PKG/'RESULTS_C8_independent.json').read_text())['step1']['meta']['inputs']
    pairs = [('RESULTS_independent.json', c2['results_independent_sha256'], 'RESULTS_archive_comparison.json'),
             ('RESULTS_C8_independent.json', c8['results_C8_independent_sha256'], 'RESULTS_C8_archive_comparison.json'),
             ('spec/comparison_C8/archive_C8_values.json', c8['archive_file_sha256'], 'RESULTS_C8_archive_comparison.json'),
             (i8['production']['path'], i8['production']['sha256'], 'RESULTS_C8_independent.json'),
             (i8['tiers_ABC']['path'], i8['tiers_ABC']['sha256'], 'RESULTS_C8_independent.json')]
    pairs += [(v['path'], v['sha256'], 'RESULTS_C8_independent.json') for v in i8['tier_files'].values()]
    bad = [p for p, h, _ in pairs if p not in S and sha(PKG/p) not in (h, RP.get(h))]
    T.check('sha256 recorded in the results', not bad, '%d files%s' % (len(pairs), '; differ: %s' % bad if bad else ''),
            'all equal', 'the archive-free results (and the engine inputs they read) are the files the comparison hashed')


def framework_tests(T, work):
    run = work/'fw'
    shutil.rmtree(run, ignore_errors=True)
    shutil.copytree(PKG, run, ignore=shutil.ignore_patterns('public', '.work', '__pycache__', 'public.mk'))
    fw = run/'framework'
    comp = PKG.parent/'dual_d1'                     # the compendium (sibling package of SRI/code/)
    extract = comp/'public'/'compendium_extract.json'
    f3 = comp/'data'/'archived'/'C8_full_numerical_completion'/'data'/'F3_final_100.json'
    if extract.exists():                            # derive_C8.NOTE = framework/../../LRI_SRI_research_compendium/note/...
        # The compendium's TeX source is not shipped (2026-10-17). Its stand-in is rebuilt from the verbatim blocks of
        # ../dual_d1/public/compendium_extract.json, each at its original line (blank lines elsewhere), so derive_C8.py
        # parses B_old and eq:C8assembly and reports the same line numbers as from the original.
        ex = json.loads(extract.read_text())
        lines = [''] * ex['original']['lines']
        for b in ex['blocks']:
            assert hashlib.sha256('\n'.join(b['text']).encode()).hexdigest() == b['sha256'], b['id']
            lines[b['first_line'] - 1:b['first_line'] - 1 + len(b['text'])] = b['text']
        (work/'LRI_SRI_research_compendium'/'note').mkdir(parents=True, exist_ok=True)
        (work/'LRI_SRI_research_compendium'/'note'/'LRI_perturbation_compendium.tex').write_text('\n'.join(lines))
    tests = list(FW_TESTS) + ['test_archive_pipeline']
    for t in tests:
        if (t == 'test_c8' and not extract.exists()) or (t == 'test_archive_pipeline' and not f3.exists()):
            T.add('framework ' + t, 'SKIP', 'sibling ../dual_d1 absent', '', 'needs the compendium (%s)' % (
                'public/compendium_extract.json' if t == 'test_c8' else 'data/archived/.../F3_final_100.json'))
            continue
        if t == 'test_archive_pipeline':            # re-point the absolute path of the archived inputs (work copy only)
            src = fw/'tests'/(t + '.py')
            txt = re.sub(r'(?:/Users/[^/\s"\']+/Documents/[^/\s"\']+|<PROJECT>)/LRI_SRI_research_compendium', str(comp.resolve()),
                         src.read_text())
            src.write_text(txt)
        t0 = time.time()
        r = subprocess.run([sys.executable, '-B', 'tests/%s.py' % t], cwd=fw, capture_output=True, text=True)
        (work/('%s.log' % t)).write_text(r.stdout + r.stderr)
        T.check('framework ' + t, r.returncode == 0 and '  FAIL' not in r.stdout, 'exit %d, %.0f s' % (r.returncode, time.time() - t0),
                'exit 0', 'verbatim framework unit test (framework/run_tests.sh list)' +
                ('; archive raw coefficients -> archived inputs (comparison only)' if t == 'test_archive_pipeline' else ''))
    r = subprocess.run([sys.executable, '-B', 'review/check_note_recurrence_direct.py'], cwd=fw, capture_output=True, text=True)
    (work/'check_note_recurrence_direct.log').write_text(r.stdout + r.stderr)
    T.check('framework note-direct check', 'NOTE-DIRECT CHECK PASSED' in r.stdout, 'exit %d' % r.returncode,
            'NOTE-DIRECT CHECK PASSED', 'the phase-1 critic\'s independent transcription of the note\'s recurrence (run_tests.sh)')


def engine_test(T, work):
    run = work/'eng'
    shutil.rmtree(run, ignore_errors=True)
    shutil.copytree(PKG/'engine', run/'engine', ignore=shutil.ignore_patterns('runs', '__pycache__'))
    r = subprocess.run(['bash', 'slurm/build.sh'], cwd=run/'engine', capture_output=True, text=True)
    (work/'engine_build.log').write_text(r.stdout + r.stderr)
    exe = run/'engine'/'bin'/'lri_engine'
    if r.returncode != 0 or not exe.exists():
        T.add('engine build', 'SKIP', 'build failed: %s' % (r.stdout + r.stderr).strip().splitlines()[-1:],
              'g++ -O3 -march=x86-64-v3 -std=c++17 -fopenmp', 'needs an x86-64-v3 C++17 OpenMP compiler (as on symmetry)')
        return
    T.check('engine build', True, (r.stdout.strip().splitlines() or [''])[-1][-90:], 'built', 'engine/slurm/build.sh, verbatim')
    env = dict(os.environ)
    env.setdefault('OMP_NUM_THREADS', str(min(8, os.cpu_count() or 1)))
    env['OMP_NUM_THREADS'] = os.environ.get('SLURM_CPUS_PER_TASK', env['OMP_NUM_THREADS'])
    d = run/'chunks'
    d.mkdir()
    for cfg in FIXTURES:
        shutil.copy(PKG/'engine'/'runs'/'prod_6digit'/cfg, d/cfg)
        t0 = time.time()
        rr = subprocess.run([str(exe), cfg], cwd=d, capture_output=True, text=True, env=env)
        out = d/(cfg + '.json')
        if rr.returncode != 0 or not out.exists():
            T.check('engine rerun ' + cfg, False, 'exit %d' % rr.returncode, 'exit 0', (rr.stdout + rr.stderr)[-200:])
            continue
        a = json.loads((PKG/'engine'/'runs'/'prod_6digit'/(cfg + '.json')).read_text())
        b = json.loads(out.read_text())
        worst, bitwise, nval = 0.0, True, 0
        for ch, ca in a['channels'].items():
            cb = b['channels'][ch]
            assert ca['orders'] == cb['orders']
            for key in ('value', 'rep'):
                xa = ca[key] if key == 'value' else sum(ca[key], [])
                xb = cb[key] if key == 'value' else sum(cb[key], [])
                for u, v, s in zip(xa, xb, ca['abs'] * (1 if key == 'value' else len(ca['rep']))):
                    nval += 1
                    if u != v:
                        bitwise = False
                        worst = max(worst, abs(u - v) / max(s, 1e-300))
        T.check('engine rerun ' + cfg, worst <= 1e-12, '%d values, %s, %.1f s (%s threads)' % (
            nval, 'bitwise identical' if bitwise else 'largest |diff|/L1 %.1e' % worst, time.time() - t0, env['OMP_NUM_THREADS']),
            '<= 1e-12 of the L1 scale', 'shipped production chunk (n=%d %s %s, N=%d) rerun from its .cfg' % (
                a['n'], a['type'], a['geom'], a['N']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG/'.work'))
    ap.add_argument('--skip-engine', action='store_true')
    ap.add_argument('--skip-framework', action='store_true')
    a = ap.parse_args()
    work = Path(a.work).resolve()/'test'
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    T = SL.Table('indep_d1 test')
    snapshot(T)
    recorded_hashes(T)
    if not a.skip_framework:
        framework_tests(T, work)
    if not a.skip_engine:
        engine_test(T, work)
    return T.report(work/'test_indep.txt')


if __name__ == '__main__':
    sys.exit(main())
