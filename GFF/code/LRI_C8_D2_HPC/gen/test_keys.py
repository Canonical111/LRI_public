#!/usr/bin/env python3
"""A-INV-1: the checked 128-bit class-file reader of the d=2 payload generator (gen/c8gen.hpp).

Feeds crafted class files to bin/gen/test_keys (a driver around read_classes; with --generator around
read_generator_classes) and to the three generator programs, and checks:
  * keys 2^64 and 2^70+1 are read and printed back exactly; every class file classes1..8 round-trips byte for
    byte (26,540 L8 keys, 5,068 of them above 2^64);
  * 2^128, '12a', a truncated file, a surplus row, a row with the wrong token count, a key wider than the class
    and an out-of-range header exit 2, naming the offending token and row; the builders refuse the same files
    with the same message before creating any output;
  * exactly NG rows are read;
  * the generator programs' semantic validation (validate_generator_classes, Stage-6 finding S6-B-03), kept apart
    from the syntax-only reader: a file the syntax driver round-trips but that is no generator input (a vertex of
    degree 6, the reviewer's '4 1 / 15 1 1'; a zero-edge key; n=1; too many edges; a disconnected graph; aut or orbit
    0; aut * orbit != n!; an aut whose product overflows; a repeated key; NG=0) exits 2 from `test_keys --generator`
    and from the three generator programs, naming the file, the row and the defect, before any output exists; every
    class file classes1..8 passes `test_keys --generator` with the same rows;
  * compiling c8gen.hpp, and each generator source, with -Wall -Wextra gives no warning in gen/c8gen.hpp;
  * under UBSan (Stage-6 round-2 finding S6R2-B-01): test_keys and the three generator programs, compiled with
    --cxx and -fsanitize=undefined -fno-sanitize-recover=undefined (any undefined behaviour aborts), refuse the
    reviewer's key 2^72-1 at n=9 (all 36 pair multiplicities 3, whose pair product used to overflow a long long
    before the edge count was checked) with exit 2 and the edge-count message, no sanitizer report and no output;
    every crafted file above and every class file classes1..8 runs through the sanitized test_keys without a report;
  * a hostile header NG = 2^31-1 with one row (Stage-6 residual, low): test_keys built with -fsanitize=address and run
    with ASAN_OPTIONS=max_allocation_size_mb=256 (an allocation above 256 MB aborts) refuses it, with and without
    --generator, with exit 2 and the first missing row's message and no sanitizer report: read_classes reserves at
    most CLASS_RESERVE_CAP rows up front (it used to reserve NG rows, 68 GB for this header: std::bad_alloc where
    memory is limited, an abort under ASan).
  * Stage-6 fix round 4, W6 (S6R4-B-03): check_edge_forests reads an existing power G-file with every extraction
    checked and every allocation bounded by the loader's limits. On a copy of the frozen power L4 tree
    (reference/power_mass/inputs/L4) with G18.txt cut after its magic, cut before its first term's denominator size,
    cut inside a term, with M = -1, M = 2^31-1, T = 0, a denominator size of -1 or above M, or another id: exit 1, the
    report lists the 5 power classes with exactly that graph failed (matches_induced false, an "error" naming the
    defect) and the others matching, no crash (before the fix M = -1 and k = -1 threw std::length_error out of the
    OpenMP region: std::terminate, and the cut files read uninitialized counts); the clean copy passes. The same cases
    run through the UBSan build without a report, and the hostile M = 2^31-1 through an ASan build with
    max_allocation_size_mb=256 (before: an 8 GB vector of the unchecked count).
    --no-ubsan skips the sanitizer parts (recorded as skipped; for a compiler without sanitizer support only).
Pure logic, about 10 s with the UBSan builds. Usage: python3 -B gen/test_keys.py [--bin bin/gen] [--cxx g++] [--no-ubsan]
[--output FILE]"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'gen'
CLASSES = ROOT / 'reference/c8d1_inputs8'


def run(cmd, timeout: float = 120, **kw):
    """The command's CompletedProcess; a run past `timeout` seconds is killed and reported as returncode -9 (a
    generator without the semantic validation can loop without bound on a crafted file, e.g. n=1)."""
    cmd = [str(c) for c in cmd]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, -9, '', f'killed after the {timeout} s timeout')


REVIEWER_KEY = 2 ** 72 - 1  # S6R2-B-01: n=9, all 36 pair multiplicities 3 (108 edges)
# W6 (Stage-6 fix round 4): the frozen power L4 tree (5 power classes in classes4.txt; G-files G18, G25, G26) and the
# malformed copies of its G18.txt that check_edge_forests must fail as that graph only: (name, bytes from the frozen
# lines, needle of the row's error)
EF_TREE = ROOT / 'reference/power_mass/inputs/L4'
EF_GRAPH = 18
EF_CASES = (
    ('G18.txt cut after its magic', lambda ls, h: b'C7D2GRAPH1\n', 'truncated or malformed header'),
    ("G18.txt cut before its first term's denominator size", lambda ls, h: b'\n'.join(ls[:2]) + b'\n', 'its denominator size'),
    ('G18.txt cut inside its first term', lambda ls, h: b'\n'.join(ls[:2] + [ls[2][:9]]) + b'\n', 'truncated or malformed term 0'),
    ('G18.txt with M = -1', lambda ls, h: b' '.join(h[:5] + [b'-1', h[6]]) + b'\n' + b'\n'.join(ls[1:]), 'header counts M=-1'),
    ('G18.txt with M = 2^31-1', lambda ls, h: b' '.join(h[:5] + [b'2147483647', h[6]]) + b'\n' + b'\n'.join(ls[1:]),
     'header counts M=2147483647'),
    ('G18.txt with T = 0', lambda ls, h: b' '.join(h[:6] + [b'0']) + b'\n' + b'\n'.join(ls[1:]), 'header counts M=28, T=0'),
    ('G18.txt with a denominator size of -1', lambda ls, h: b'\n'.join(ls[:2]) + b'\n-1 0\n', 'denominator size -1 outside'),
    ('G18.txt with a denominator size above M', lambda ls, h: b'\n'.join(ls[:2]) + b'\n99 0 1 2\n', 'denominator size 99 outside'),
    ('G18.txt naming another id', lambda ls, h: b' '.join(h[:2] + [b'19'] + h[3:]) + b'\n' + b'\n'.join(ls[1:]), 'header magic, L or id'),
)


def edge_forest_gfile_checks(prog: Path, t: Path, check, label: str = '', env: dict | None = None, clean=None) -> None:
    """W6: check_edge_forests (prog) on the frozen power L4 tree and on each EF_CASES copy: the clean tree passes; each
    malformed G18.txt is that graph's failure (exit 1, failures 1 of 5 graphs, its row matches_induced false with the
    error, the other four matching), never a crash. clean(r): an extra condition on each run (the sanitizer builds: no
    report)."""
    import json as _json
    env = env or {**os.environ, 'OMP_NUM_THREADS': '2'}
    frozen = (EF_TREE / f'G{EF_GRAPH}.txt').read_bytes()
    ls = frozen.split(b'\n')
    h = ls[0].split()

    def run_tree(tag: str, data: bytes | None):
        d = t / f'ef_{label.strip().replace(" ", "_")}{tag}'
        shutil.copytree(EF_TREE, d)
        if data is not None:
            (d / f'G{EF_GRAPH}.txt').write_bytes(data)
        rep = d / 'report.json'
        r = run([prog, CLASSES / 'classes4.txt', d, rep], timeout=120, env=env)
        try:
            doc = _json.loads(rep.read_text())
        except (OSError, ValueError):
            doc = None
        return r, doc

    r, doc = run_tree('clean', None)
    check(f'{label}check_edge_forests: the frozen power L4 tree passes (5 power classes, no failure)',
          r.returncode == 0 and doc is not None and doc.get('graphs') == 5 and doc.get('failures') == 0 and (clean is None or clean(r)),
          f'rc={r.returncode} doc={str(doc)[:300]} stderr={r.stderr[-300:]!r}')
    for i, (name, make, needle) in enumerate(EF_CASES):
        r, doc = run_tree(str(i), make(ls, h))
        rows = {x.get('id'): x for x in (doc or {}).get('rows', [])}
        bad = rows.get(EF_GRAPH) or {}
        ok = (r.returncode == 1 and doc is not None and doc.get('graphs') == 5 and doc.get('failures') == 1 and bad.get('matches_induced') is False
              and needle in str(bad.get('error')) and all(x.get('matches_induced') is True for k, x in rows.items() if k != EF_GRAPH)
              and len(rows) == 5 and (clean is None or clean(r)))
        check(f'{label}check_edge_forests (W6): {name} fails that graph only, with its error, and nothing crashes', ok,
              f'rc={r.returncode} row={bad} failures={(doc or {}).get("failures")} stderr={r.stderr[-300:]!r}')
UBSAN_FLAGS = ['-O1', '-g', '-std=c++17', '-fopenmp', '-fno-fast-math', '-ffp-contract=off', '-fsanitize=undefined',
               '-fno-sanitize-recover=undefined']


def ubsan_checks(cxx: str, t: Path, check, crafted_files: list[tuple[str, bool]]) -> None:
    """S6R2-B-01: build test_keys and the three generator programs with UBSan into t/ubsan and require the normal
    InputError refusal (exit 2, the edge-count message, no 'runtime error' report, no output) for the reviewer's key;
    every crafted file (text, through --generator or not) and every class file classes1..8 must run through the
    sanitized test_keys without a report and with the exit status of the plain build (2 or 0)."""
    ub = t / 'ubsan'
    ub.mkdir()
    progs = ('test_keys', 'build_free', 'build_power', 'check_edge_forests')
    procs = {p: subprocess.Popen([cxx, *UBSAN_FLAGS, f'-I{GEN}', str(GEN / f'{p}.cpp'), '-o', str(ub / p)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) for p in progs}
    built = {}
    for p, pr in procs.items():
        out, _ = pr.communicate()
        built[p] = pr.returncode == 0
        check(f'UBSan build of {p} ({cxx} -fsanitize=undefined -fno-sanitize-recover=undefined)', built[p], out[-400:])
    env = {**os.environ, 'OMP_NUM_THREADS': '1', 'UBSAN_OPTIONS': 'print_stacktrace=1:halt_on_error=1'}
    clean = lambda r: 'runtime error' not in r.stderr and 'UndefinedBehaviorSanitizer' not in r.stderr  # noqa: E731
    reviewer = t / 'ubsan_reviewer_key.txt'
    reviewer.write_text(f'9 1\n{REVIEWER_KEY} 1 362880\n')
    needles = [str(reviewer), 'row 1 of 1', f'key {REVIEWER_KEY}', '108 edges', 'exactly 16']
    for p in progs:
        if not built[p]:
            continue
        out, side = t / f'ubsan_out_{p}', t / f'ubsan_side_{p}.txt'
        cmd = [ub / p, '--generator', reviewer] if p == 'test_keys' else [ub / p, reviewer, out, side]
        r = run(cmd, timeout=60, env=env)
        check(f"UBSan {p}: the reviewer's key 2^72-1 (n=9) is refused with exit 2, the edge-count message and no "
              'sanitizer report, before any output',
              r.returncode == 2 and clean(r) and all(n in r.stderr for n in needles) and not r.stdout
              and not out.exists() and not side.exists(), f'rc={r.returncode} stderr={r.stderr[-600:]!r}')
    if built['check_edge_forests']:  # W6: the malformed G-files through the UBSan build, without a report
        edge_forest_gfile_checks(ub / 'check_edge_forests', t, check, label='UBSan ', env=env, clean=clean)
    if not built['test_keys']:
        return
    bad = []
    for i, (text, gen) in enumerate(crafted_files):
        f = t / f'ubsan_crafted_{i}.txt'
        f.write_text(text)
        r = run([ub / 'test_keys', *(['--generator'] if gen else []), f], timeout=60, env=env)
        if r.returncode != 2 or not clean(r):
            bad.append(dict(text=text[:80], generator=gen, rc=r.returncode, stderr=r.stderr[-300:]))
    check(f'UBSan test_keys: every crafted file ({len(crafted_files)}) is refused with exit 2 and no sanitizer report',
          not bad, json.dumps(bad)[:400])
    bad = []
    for L in range(1, 9):
        f = CLASSES / f'classes{L}.txt'
        r = run([ub / 'test_keys', '--generator', f], timeout=300, env=env)
        if r.returncode != 0 or not clean(r) or r.stdout != f.read_text():
            bad.append(dict(L=L, rc=r.returncode, stderr=r.stderr[-300:]))
    check('UBSan test_keys --generator: classes1..8 pass with the same rows and no sanitizer report', not bad,
          json.dumps(bad)[:400])


HOSTILE_NG = 2 ** 31 - 1  # INT_MAX: the largest header NG read_classes accepts
ASAN_FLAGS = ['-O1', '-g', '-std=c++17', '-fopenmp', '-fno-fast-math', '-ffp-contract=off', '-fsanitize=address']


def hostile_ng_checks(cxx: str, t: Path, check) -> None:
    """Stage-6 residual (low): a class file whose header promises NG = INT_MAX rows but holds one must be refused with
    the InputError of row 2 (exit 2), not by an allocation of NG rows. Under ASan with max_allocation_size_mb=256 the
    old reader's reserve(NG) (2^31-1 rows of 32 bytes) aborts with an allocation report; the capped reserve does not."""
    asan = t / 'asan'
    asan.mkdir()
    r = run([cxx, *ASAN_FLAGS, f'-I{GEN}', GEN / 'test_keys.cpp', '-o', asan / 'test_keys'], timeout=300)
    check(f'ASan build of test_keys ({cxx} -fsanitize=address)', r.returncode == 0, r.stdout[-400:] + r.stderr[-400:])
    if r.returncode != 0:
        return
    f = t / 'hostile_ng.txt'
    f.write_text(f'9 {HOSTILE_NG}\n1 1 362880\n')
    env = {**os.environ, 'OMP_NUM_THREADS': '1', 'ASAN_OPTIONS': 'max_allocation_size_mb=256:allocator_may_return_null=0:detect_leaks=0'}
    # W6: check_edge_forests built with ASan reads G18.txt with the hostile M = 2^31-1 (before: an 8 GB vector of the
    # unchecked count, above max_allocation_size_mb) and fails that graph without a report
    r = run([cxx, *ASAN_FLAGS, f'-I{GEN}', GEN / 'check_edge_forests.cpp', '-o', asan / 'check_edge_forests'], timeout=300)
    check(f'ASan build of check_edge_forests ({cxx} -fsanitize=address)', r.returncode == 0, r.stdout[-400:] + r.stderr[-400:])
    if r.returncode == 0:
        edge_forest_gfile_checks(asan / 'check_edge_forests', t, check, label='ASan (max_allocation_size_mb=256) ',
                                 env={**os.environ, 'OMP_NUM_THREADS': '2', 'ASAN_OPTIONS': 'max_allocation_size_mb=256:allocator_may_return_null=0:detect_leaks=0'},
                                 clean=lambda r: 'Sanitizer' not in r.stderr)
    for gen in (False, True):
        r = run([asan / 'test_keys', *(['--generator'] if gen else []), f], timeout=120, env=env)
        check(f'hostile header NG={HOSTILE_NG} with one row{" (--generator)" if gen else ""}: exit 2 with the missing row 2, '
              'no allocation of NG rows (ASan, max_allocation_size_mb=256), no sanitizer report',
              r.returncode == 2 and f'row 2 of {HOSTILE_NG}: missing (file truncated)' in r.stderr and 'Sanitizer' not in r.stderr
              and not r.stdout, f'rc={r.returncode} stderr={r.stderr[-600:]!r}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--bin', type=Path, default=ROOT / 'bin/gen')
    ap.add_argument('--cxx', default=os.environ.get('CXX', 'g++'))
    ap.add_argument('--no-ubsan', action='store_true',
                    help='skip the sanitizer builds, UBSan and the ASan hostile-NG check (only for a compiler without sanitizer support)')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    drv = a.bin / 'test_keys'
    results: list[dict] = []
    failed: list[str] = []
    skipped: list[str] = []

    def check(name: str, ok: bool, detail: str = '') -> None:
        results.append(dict(check=name, passed=bool(ok), detail=detail[:400]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[:200]}' if detail and not ok else ''), flush=True)

    k64, k70 = 2 ** 64, 2 ** 70 + 1
    k128 = 2 ** 128
    with tempfile.TemporaryDirectory(prefix='c8d2_test_keys_') as td:
        t = Path(td)

        def crafted(name: str, text: str) -> Path:
            p = t / name
            p.write_text(text)
            return p

        good = crafted('good.txt', f'9 2\n{k64} 1 1\n{k70} 2 3\n')
        r = run([drv, good])
        check('read and print back 2^64 and 2^70+1', r.returncode == 0 and r.stdout == f'9 2\n{k64} 1 1\n{k70} 2 3\n',
              r.stdout + r.stderr)
        bad_cases = [
            ('2^128 overflows', f'9 1\n{k128} 1 1\n', [str(k128), 'row 1', 'overflows 2^128']),
            ("'12a' is refused", '9 2\n12 1 1\n12a 1 1\n', ["'12a'", 'row 2']),
            ('truncated file', '9 3\n1 1 1\n2 1 1\n', ['row 3 of 3', 'truncated']),
            ('surplus row (exactly NG rows)', '9 1\n1 1 1\n2 1 1\n', ["trailing token '2'"]),
            ('row with two tokens', '9 1\n1 1\n', ['row 1 of 1', '2 tokens']),
            ('row with four tokens', '9 1\n1 1 1 1\n', ['row 1 of 1', '4 tokens']),
            ('key wider than an n=4 class', '4 1\n4096 1 1\n', ["'4096'", 'does not fit 12 bits']),
            ('header n out of range', '10 1\n1 1 1\n', ['n=10']),
            ("non-decimal aut", '9 1\n5 x1 1\n', ["'x1'", 'row 1']),
            ('empty file', '', ['empty file']),
        ]
        bad_files = {}
        for name, text, needles in bad_cases:
            p = crafted(name.replace(' ', '_').replace("'", '').replace('^', '').replace('(', '').replace(')', '') + '.txt', text)
            bad_files[name] = (p, needles)
            r = run([drv, p])
            check(f'driver: {name}', r.returncode == 2 and all(n in r.stderr for n in needles) and not r.stdout,
                  f'rc={r.returncode} stderr={r.stderr!r}')
        # The generator programs refuse the same files with the same message, before writing anything.
        for prog in ('build_free', 'build_power', 'check_edge_forests'):
            for name in ('2^128 overflows', "'12a' is refused", 'truncated file'):
                p, needles = bad_files[name]
                out = t / f'out_{prog}'
                cmd = [a.bin / prog, p, out] + ([t / 'report.json'] if prog == 'check_edge_forests' else [])
                r = run(cmd)
                check(f'{prog}: {name}', r.returncode == 2 and all(n in r.stderr for n in needles) and not out.exists(),
                      f'rc={r.returncode} stderr={r.stderr!r} out_exists={out.exists()}')
        # Semantic validation of the generator programs (S6-B-03): syntactically valid files that are no generator
        # input. The syntax driver round-trips them (the two checks stay separate); `test_keys --generator` and the
        # three programs refuse them with exit 2, naming the file, the row and the defect, before writing anything.
        big_aut = 2 ** 63 - 1
        semantic_cases = [
            ('vertex of degree 6 (n=4, key 15)', '4 1\n15 1 1\n', ['row 1 of 1', 'key 15', 'vertex 0 has degree 6 > 4']),
            ('zero-edge key', '4 1\n0 24 1\n', ['row 1 of 1', 'key 0', '0 edges', 'exactly 6']),
            ('n=1 (L=0)', '1 1\n0 1 1\n', ['header n=1', '2 <= n <= 9']),
            ('seven edges at n=4', '4 1\n1366 24 1\n', ['row 1 of 1', '7 edges', 'exactly 6']),
            ('disconnected graph', '4 1\n138 6 4\n', ['row 1 of 1', 'not connected (2 components)']),
            ('aut 0', '3 1\n37 0 3\n', ['row 1 of 1', 'aut=0', 'must both be >= 1']),
            ('orbit 0', '3 1\n37 2 0\n', ['row 1 of 1', 'orbit=0', 'must both be >= 1']),
            ('aut * orbit is not n!', '3 2\n37 2 3\n40 2 4\n', ['row 2 of 2', 'key 40', 'differs from n! = 6']),
            ('aut * orbit overflows', f'3 1\n37 {big_aut} 2\n', ['row 1 of 1', 'aut * orbit overflows']),
            ('repeated key', '3 2\n37 2 3\n37 2 3\n', ['row 2 of 2', 'key 37', 'the key of row 1 again']),
            ('NG=0', '3 0\n', ['header NG=0', 'at least one class']),
            # S6R2-B-01: the reviewer's key; the pair product 6^36 overflowed before the edge count was checked
            ("the reviewer's key 2^72-1 at n=9 (all 36 multiplicities 3)", f'9 1\n{REVIEWER_KEY} 1 362880\n',
             ['row 1 of 1', f'key {REVIEWER_KEY}', '108 edges', 'exactly 16']),
        ]
        for name, text, needles in semantic_cases:
            p = crafted('sem_' + ''.join(c if c.isalnum() else '_' for c in name) + '.txt', text)
            r = run([drv, p])
            check(f'syntax driver round-trips the semantically invalid file: {name}',
                  r.returncode == 0 and r.stdout == text, f'rc={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}')
            r = run([drv, '--generator', p])
            check(f'test_keys --generator refuses: {name}', r.returncode == 2 and not r.stdout
                  and all(n in r.stderr for n in [str(p)] + needles), f'rc={r.returncode} stderr={r.stderr!r}')
            for prog in ('build_free', 'build_power', 'check_edge_forests'):
                out, side = t / f'sem_out_{prog}', t / f'sem_side_{prog}.txt'
                r = run([a.bin / prog, p, out, side], timeout=10, env={**os.environ, 'OMP_NUM_THREADS': '1'})
                check(f'{prog} refuses before writing: {name}',
                      r.returncode == 2 and all(n in r.stderr for n in [str(p)] + needles) and not out.exists()
                      and not side.exists(), f'rc={r.returncode} stderr={r.stderr!r} out_exists={out.exists()}')
        # Round trip of every class file, byte for byte (exactly NG rows; 128-bit keys), with and without the
        # generator programs' semantic validation (every shipped class file is a valid generator input).
        for L in range(1, 9):
            f = CLASSES / f'classes{L}.txt'
            r = run([drv, f])
            check(f'classes{L}.txt round-trips byte for byte', r.returncode == 0 and r.stdout == f.read_text(),
                  r.stderr)
            r = run([drv, '--generator', f])
            check(f'classes{L}.txt passes the generator validation (same rows)',
                  r.returncode == 0 and r.stdout == f.read_text(), r.stderr)
        rows = (CLASSES / 'classes8.txt').read_text().split('\n')[1:]
        big = sum(1 for line in rows if line and int(line.split()[0]) >= k64)
        check('classes8.txt holds 5,068 keys above 2^64', big == 5068, str(big))
        # W6 (Stage-6 fix round 4): check_edge_forests on malformed existing G-files: that graph's failure, never a crash
        edge_forest_gfile_checks(a.bin / 'check_edge_forests', t, check)
        # -Wall -Wextra: no warning in gen/c8gen.hpp
        hdr = t / 'hdr.cpp'
        hdr.write_text('#include "c8gen.hpp"\nint main() { return 0; }\n')
        r = run([a.cxx, '-std=c++17', '-Wall', '-Wextra', '-fsyntax-only', f'-I{GEN}', hdr])
        check('c8gen.hpp alone: no warning under -Wall -Wextra', r.returncode == 0 and not r.stderr.strip(), r.stderr)
        for src in ('build_free.cpp', 'build_power.cpp', 'check_edge_forests.cpp', 'test_keys.cpp'):
            r = run([a.cxx, '-std=c++17', '-fopenmp', '-Wall', '-Wextra', '-fsyntax-only', GEN / src])
            inhdr = [line for line in r.stderr.splitlines() if 'c8gen.hpp' in line]
            check(f'{src}: no -Wall -Wextra diagnostic in c8gen.hpp', r.returncode == 0 and not inhdr, '\n'.join(inhdr))
        # S6R2-B-01: the semantic validation under UBSan (every undefined behaviour aborts the program)
        if a.no_ubsan:
            skipped.append('UBSan builds and the ASan hostile-NG check (--no-ubsan)')
            print('SKIPPED UBSan builds and the ASan hostile-NG check (--no-ubsan)', flush=True)
        else:
            ubsan_checks(a.cxx, t, check, [(text, False) for _, text, _ in bad_cases]
                         + [(text, True) for _, text, _ in semantic_cases])
            hostile_ng_checks(a.cxx, t, check)
    rec = dict(schema='c8-d2-gate-1', gate='A-INV-1 test_keys', passed=not failed, failed=failed, checks=results,
               skipped=skipped,
               cxx=run([a.cxx, '--version']).stdout.splitlines()[0] if shutil.which(a.cxx) else a.cxx)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'test_keys: {len(results) - len(failed)}/{len(results)} checks passed'
          + (f', {len(skipped)} skipped' if skipped else ''))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
