#!/usr/bin/env python3
"""gen3/ tests (PLAN.md F-table row `gen3/test_gen3.py`; A-INV-1, and the tool parts of A-INV-3..6 on tiny files).

regenerate_rates (A-INV-1):
  - A.1's build command gives no compiler warning (the Makefile's `make gen3`, into a temporary directory);
  - the targeted cases: each exits 2, prints '<input path>:' and the field's reason on stderr, prints nothing on
    stdout, and leaves neither an output nor a .tmp (header, masks, terms, truncation after every field, the rate
    block, files and job list, an output under C62d's tree);
  - S1-02: job lists whose inputs, outputs and temporary files collide (by path through symbolic links, or by identity),
    or whose temporary file exists, are refused before any file is touched; temporaries are created exclusively;
  - a job list mixing one bad file with good ones exits 2, names only the bad file, prints no record array and
    renames nothing;
  - the seeded mutation corpus (seed 8814): 500 mutants of each of 4 base files (reference/inputs/free/L2/G0.txt, the
    smallest L3 free file, the smallest L7 power file, a synthetic L8 G-file); each gives exit 0 (and a second pass
    over its output is byte-unchanged) or exit 2 naming the file; no signal, no sanitizer or _GLIBCXX_ASSERTIONS
    report, no other status, no run over 10 s;
  - idempotence on C7D3GRAPH1 files; the record's raw_histogram, min_raw and double_lift_subsets against an
    independent Python recomputation (g3common.d3_rates);
  - with --sanitize, everything runs under bin/gen3/regenerate_rates_san, and the coverage self-test (C.7) runs the
    index-M case under bin/selftest/regenerate_rates_unguarded_san: SIGABRT, libstdc++'s '__n < this->size()', and the
    first package frame of ASan's stack trace at the unique `dist[masks[m]]` line; the same case exits 2 naming the
    file on regenerate_rates_san (the control).
The gate tools (tools part; tiny synthetic files): see the test functions named test_tool_*. They include the
publication of the real gate-file set (gate records, supporting records, H1's raw check_edge_forests outputs) and the
builder side files, gate 1(a)'s platform rule (A-INV-2(a) only on Expanse x86-64; anything else a rehearsal), J-GEN-D3-0's
summary, the A.5 report's refusal of a rehearsal, and the job scripts slurm/gen_d3_0.sh, slurm/h1_copy.sh and
slurm/gen_d3.sh on a fake package (D.10 preamble, C8_SCRATCH and TMPDIR inside the job, inputs as environment variables).

  python3 -B gen3/test_gen3.py                    # Mac: builds into a temporary directory (CXX, default g++-16 on macOS)
  python3 -B gen3/test_gen3.py --sanitize         # J-GEN-D3-0, after `make gen3-sanitize`
Options: --cxx CXX; --bin-dir DIR (prebuilt bin/gen3 and bin/selftest layout); --output FILE (JSON record);
--only regen|tools; --corpus N (mutants per base file, default 500).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import platform
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

GEN3 = Path(__file__).resolve().parent
ROOT = GEN3.parent
sys.path.insert(0, str(GEN3))
import g3common as c  # noqa: E402

RESULTS: list[dict] = []
SEED = 8814
TIMEOUT = 10.0
REPORT_PATTERNS = ('AddressSanitizer', 'UndefinedBehaviorSanitizer', 'runtime error:', 'LeakSanitizer',
                   '__glibcxx_assert', 'Assertion', '_GLIBCXX')


def ok(name: str, **info) -> None:
    RESULTS.append({'test': name, **info})
    print('PASS', name, flush=True)


# ---- binaries ----------------------------------------------------------------------------------------------------
class Bins:
    def __init__(self, a, td: Path):
        self.sanitize = a.sanitize
        cxx = a.cxx or os.environ.get('CXX') or ('g++-16' if platform.system() == 'Darwin' else 'g++')
        env = dict(os.environ)
        for k in ('CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'LDLIBS', 'OPTFLAGS'):
            env.pop(k, None)
        if platform.system() == 'Darwin':   # Homebrew's llvm dsymutil may crash on GCC's -g links; Apple's works
            env['PATH'] = '/usr/bin:' + env.get('PATH', '')
        self.env = env
        # A.1's command, built here (warnings fail the Makefile rule; the test also asserts make printed nothing).
        tb = td / 'build'
        cp = subprocess.run(['make', '-s', '-C', str(ROOT), 'gen3', f'CXX={cxx}', f'GEN3_BIN={tb}/gen3',
                             f'SELFTEST_BIN={tb}/selftest'], capture_output=True, text=True, env=env)
        assert cp.returncode == 0 and not cp.stderr.strip() and not cp.stdout.strip(), (cp.returncode, cp.stdout, cp.stderr)
        self.build_record = (tb / 'gen3/regenerate_rates.build.txt').read_text()
        assert '-O2 -std=c++17 -fopenmp -Wall -Wextra gen3/regenerate_rates.cpp' in self.build_record, self.build_record
        self.plain = tb / 'gen3/regenerate_rates'
        self.size_probe = tb / 'gen3/size_probe'
        if a.sanitize:
            bd = Path(a.bin_dir) if a.bin_dir else ROOT / 'bin'
            if a.build_sanitize:
                bd = tb
                cp = subprocess.run(['make', '-s', '-C', str(ROOT), 'gen3-sanitize', f'CXX={cxx}', f'GEN3_BIN={tb}/gen3',
                                     f'SELFTEST_BIN={tb}/selftest'], capture_output=True, text=True, env=env)
                assert cp.returncode == 0 and not cp.stderr.strip(), (cp.returncode, cp.stderr)
            self.regen = bd / 'gen3/regenerate_rates_san'
            self.unguarded = bd / 'selftest/regenerate_rates_unguarded_san'
            for b in (self.regen, self.unguarded):
                if not os.access(b, os.X_OK):
                    raise SystemExit(f'{b}: missing; run `make gen3-sanitize` first (or pass --build-sanitize)')
        else:
            self.regen = Path(a.bin_dir) / 'gen3/regenerate_rates' if a.bin_dir else self.plain
            self.unguarded = None
        ok('build_A1_command_no_warning', compiler=self.build_record.strip().splitlines()[-1], sanitize=a.sanitize,
           binary=str(self.regen))


def run(binary: Path, joblist: Path, timeout: float = TIMEOUT, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, OMP_NUM_THREADS='1', ASAN_OPTIONS='detect_leaks=0:abort_on_error=1:handle_abort=1',
               UBSAN_OPTIONS='print_stacktrace=1:halt_on_error=1')
    if extra_env:
        env.update(extra_env)
    t0 = time.monotonic()
    try:
        cp = subprocess.run([str(binary), str(joblist)], capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise AssertionError(f'{binary} {joblist}: run over {timeout} s')
    cp.seconds = time.monotonic() - t0
    return cp


def jobs(td: Path, pairs: list[tuple[Path, Path]], name: str = 'jobs.txt') -> Path:
    p = td / name
    p.write_text(''.join(f'{a} {b}\n' for a, b in pairs))
    return p


# ---- base files --------------------------------------------------------------------------------------------------
def smallest(d: Path) -> Path:
    files = sorted(d.glob('G*.txt'), key=lambda p: (p.stat().st_size, p.name))
    assert files, d
    return files[0]


def synthetic_l8(seed: int = SEED) -> bytes:
    """A synthetic L=8 d=2 G-file (E = 16, 2^16 rate tokens): 40 masks of popcount 8, 5 terms. Not a graph: the reader
    checks counts, ranges and order, which is all this file has to satisfy."""
    rng = random.Random(seed)
    E, L = 16, 8
    masks = sorted({sum(1 << b for b in rng.sample(range(E), L)) for _ in range(60)})[:40]
    lines = [f'C7D2GRAPH1 {L} 17 0.1875 0.03125 {len(masks)} 5', ' '.join(map(str, masks)) + ' ']
    for _ in range(5):
        idx = sorted(rng.sample(range(len(masks)), rng.randint(1, 12)))
        co = [rng.choice((-1, 0, 0, 1, 2)) for _ in range(E)]
        lines.append(' '.join(map(str, [len(idx), *idx, *co])))
    lines.append(str(1 << E))
    lines.append(' '.join('0' if s in (0, (1 << E) - 1) else rng.choice(('0.5', '1', '1.5')) for s in range(1 << E)) + ' ')
    return ('\n'.join(lines) + '\n').encode()


class Base:
    """A G-file as editable token groups: header (7), masks, terms [(n, idx, co)], rate count, rates."""

    def __init__(self, data: bytes):
        g = c.parse_gfile(data)
        t = data.decode().split()
        self.header = t[:7]
        self.masks = [str(m) for m in g.masks]
        self.terms = [[str(len(i)), [str(x) for x in i], [str(x) for x in co]] for i, co in g.terms]
        self.count = str(len(g.rates))
        self.rates = list(g.rates)
        self.g = g

    def copy(self) -> 'Base':
        b = Base.__new__(Base)
        b.header, b.masks, b.count, b.rates, b.g = list(self.header), list(self.masks), self.count, list(self.rates), self.g
        b.terms = [[n, list(i), list(co)] for n, i, co in self.terms]
        return b

    def tokens(self) -> list[str]:
        out = list(self.header) + list(self.masks)
        for n, i, co in self.terms:
            out += [n, *i, *co]
        return out + [self.count] + self.rates

    def text(self) -> bytes:
        lines = [' '.join(self.header), ' '.join(self.masks) + ' ']
        lines += [' '.join([n, *i, *co]) for n, i, co in self.terms]
        lines += [self.count, ' '.join(self.rates) + ' ']
        return ('\n'.join(lines) + '\n').encode()


def truncated(b: Base, k: int) -> bytes:
    """The file cut after its first k tokens."""
    return (' '.join(b.tokens()[:k]) + ('\n' if k else '')).encode()


# ---- A-INV-1: targeted cases -------------------------------------------------------------------------------------
def targeted_cases(b: Base) -> list[tuple[str, bytes, str]]:
    """(name, file bytes, reason regex) for the L3 base (M masks, one term of n indices, E = 6)."""
    M, E = int(b.header[5]), 2 * int(b.header[1])
    cases: list[tuple[str, bytes, str]] = []

    def edit(name, fn, reason):
        x = b.copy()
        fn(x)
        cases.append((name, x.text(), reason))

    def hdr(i, v):
        def f(x):
            x.header[i] = v
        return f
    for v in ('1', '9', '-1'):
        edit(f'header_L_{v}', hdr(1, v), r'L -?\d+ out of range \[2,8\]')
    edit('header_magic_unknown', hdr(0, 'C7D9GRAPH1'), r"magic 'C7D9GRAPH1' unknown")
    for v in ('0', '-1', '16385'):
        edit(f'header_M_{v}', hdr(5, v), r'M -?\d+ out of range \[1,16384\]')
    for v in ('0', '10001'):
        edit(f'header_T_{v}', hdr(6, v), r'T \d+ out of range \[1,10000\]')
    edit('header_id_-1', hdr(2, '-1'), r"id '-1' is not a non-negative integer")
    for v in ('nan', 'abc'):
        edit(f'header_wa_{v}', hdr(3, v), rf"wa '{v}' is not a finite decimal number")

    # masks
    def mask0(v):
        def f(x):
            x.masks[0] = v
        return f
    edit('mask_ge_2^E', mask0(str(1 << E)), rf'mask 0 {1 << E} out of range \[0,{(1 << E) - 1}\]')
    low = min(v for v in range(1 << E) if bin(v).count('1') != int(b.header[1]) and 0 < v < int(b.masks[1]))
    edit('mask_popcount', mask0(str(low)), r'mask 0 \d+ has popcount \d+, expected L = 3')

    def repeat_mask(x):
        x.masks[1] = x.masks[0]
    edit('mask_repeated', repeat_mask, r'mask 1 \d+ is not above the previous mask')

    def swap_masks(x):
        x.masks[0], x.masks[1] = x.masks[1], x.masks[0]
    edit('mask_out_of_order', swap_masks, r'mask 1 \d+ is not above the previous mask')

    # terms (the base has one term)
    def length(v):
        def f(x):
            x.terms[0][0] = v
        return f
    for v in ('0', '-1', str(M + 1)):
        edit(f'term_length_{v}', length(v), rf'term 0 length -?\d+ out of range \[1,{M}\]')
    n0 = len(b.terms[0][1])

    def last_index(v):
        def f(x):
            x.terms[0][1][-1] = v
        return f
    edit('term_index_M', last_index(str(M)), rf'term 0 index {n0 - 1} {M} out of range \[0,{M - 1}\]')
    edit('term_index_2^31', last_index(str(2**31)), rf'term 0 index {n0 - 1} {2**31} out of range')

    def first_index(v):
        def f(x):
            x.terms[0][1][0] = v
        return f
    edit('term_index_-1', first_index('-1'), r'term 0 index 0 -1 out of range')

    def repeat_index(x):
        x.terms[0][1][1] = x.terms[0][1][0]
    edit('term_index_repeated', repeat_index, r'term 0 index 1 \d+ is not above the previous index')

    def drop_coef(x):
        x.terms[0][2] = x.terms[0][2][:-1]
    edit('term_E-1_coefficients', drop_coef, r'rate count \d+ out of range|term 0 coefficient')

    # truncation after every header token, after k masks, inside the terms and the rate block
    names = ['magic', 'L', 'id', 'wa', 'wb', 'M', 'T']
    for k in range(1, 8):
        nxt = names[k] if k < 7 else 'mask 0'
        cases.append((f'truncated_after_header_token_{k}', truncated(b, k), rf'truncated or malformed {nxt} \(end of file\)'))
    for k in (0, 1, M - 1):
        cases.append((f'truncated_after_mask_{k}', truncated(b, 7 + k), rf'truncated or malformed mask {k} \(end of file\)'))
    t0 = 7 + M
    cases.append(('truncated_after_term_length', truncated(b, t0 + 1), r'truncated or malformed term 0 index 0 \(end of file\)'))
    cases.append(('truncated_inside_indices', truncated(b, t0 + 1 + 3), r'truncated or malformed term 0 index 3 \(end of file\)'))
    cases.append(('truncated_inside_coefficients', truncated(b, t0 + 1 + n0 + 2),
                  r'truncated or malformed term 0 coefficient 2 \(end of file\)'))
    rc = t0 + 1 + n0 + E
    cases.append(('truncated_before_rate_count', truncated(b, rc), r'truncated or malformed rate count \(end of file\)'))
    cases.append(('truncated_inside_rate_list', truncated(b, rc + 1 + 10), r'truncated or malformed rate 10 \(end of file\)'))

    # the rate block
    for d in (-1, 1):
        def cnt(x, d=d):
            x.count = str((1 << E) + d)
        edit(f'rate_count_2^E{d:+d}', cnt, rf'rate count {(1 << E) + d} out of range')

    def rate_missing(x):
        x.rates = x.rates[:-1]
    edit('rate_token_missing', rate_missing, rf'truncated or malformed rate {(1 << E) - 1} \(end of file\)')

    def rate_extra(x):
        x.rates = x.rates + ['0']
    edit('rate_token_extra', rate_extra, r"trailing data '0' after the rate list")

    def trailing(x):
        x.rates = x.rates + ['xyz']
    edit('trailing_token', trailing, r"trailing data 'xyz' after the rate list")
    cases.append(('empty_input', b'', r'truncated or malformed magic \(end of file\)'))
    return cases


def check_failure(cp, name: str, path: str, reason: str, outs: list[Path], others: list[str] = ()) -> None:
    err = cp.stderr.decode(errors='replace')
    assert cp.returncode == 2, (name, cp.returncode, err[-2000:])
    assert cp.stdout == b'', (name, cp.stdout[:200])
    assert re.search(re.escape(path) + r': .*' + reason, err), (name, reason, err[-2000:])
    for o in outs:
        assert not o.exists() and not Path(str(o) + '.tmp').exists(), (name, o)
    for p in others:
        assert p not in err, (name, p, err)
    assert not any(s in err for s in REPORT_PATTERNS), (name, err[-3000:])


def test_targeted(B: Bins, td: Path, bases: dict) -> None:
    d = td / 'targeted'
    d.mkdir()
    b = Base(bases['L3'])
    cases = targeted_cases(b)
    for name, data, reason in cases:
        f = d / f'{name}.txt'
        f.write_bytes(data)
        out = d / f'{name}.out'
        cp = run(B.regen, jobs(d, [(f, out)], f'{name}.jobs'))
        check_failure(cp, name, str(f), reason, [out])
    # missing input
    out = d / 'missing.out'
    cp = run(B.regen, jobs(d, [(d / 'does_not_exist.txt', out)], 'missing.jobs'))
    check_failure(cp, 'missing_input', str(d / 'does_not_exist.txt'), 'cannot open', [out])
    # the job list
    good = d / 'good.txt'
    good.write_bytes(bases['L3'])
    jl = [('joblist_missing', None, 'job list cannot be opened'), ('joblist_empty', '', 'job list is empty'),
          ('joblist_odd', f'{good} {d}/o1.out {good}\n', r'job list has an odd number of tokens \(3\)'),
          ('joblist_repeated_output', f'{good} {d}/o2.out\n{good} {d}/./o2.out\n', r'output path .*o2.out is repeated'),
          ('joblist_tmp_collision', f'{good} {d}/o3.out\n{good} {d}/o3.out.tmp\n', r'is another job\'s temporary file'),
          ('joblist_output_under_c62d_c8d2', f'{good} {c.C8D2_PREFIX}/x/G1.txt\n', r"under C62d's tree /expanse/lustre"),
          ('joblist_output_under_shared_inventory', f'{good} {d}/LRI_C8_shared/inventory/G1.txt\n',
           r"under C62d's tree \.\.\./LRI_C8_shared/inventory")]
    for name, text, reason in jl:
        p = d / f'{name}.list'
        if text is not None:
            p.write_text(text)
        cp = run(B.regen, p)
        check_failure(cp, name, str(p), reason, [d / 'o1.out', d / 'o2.out', d / 'o3.out'])
    assert not (d / 'LRI_C8_shared').exists()
    ok('A-INV-1_targeted_cases', cases=len(cases) + 1 + len(jl), names=[x[0] for x in cases] + ['missing_input'] + [x[0] for x in jl])


def test_collisions(B: Bins, td: Path, bases: dict) -> None:
    """S1-02: an input that is a temporary file (its own, or another job's through a dangling symbolic link) or an output
    (by path or by identity: a hard link), two spellings of one output or temporary file (a symlinked directory), and an
    existing temporary file are each refused before any file is read or written: exit 2 naming the job list, nothing on
    stdout, no output, the existing files unchanged and no temporary file created or removed. On a case-insensitive file
    system (the Mac) two outputs differing in case share one temporary file: the second exclusive creation fails, exit 2,
    no output renamed, and only the temporary file this run created is removed."""
    d = td / 'collisions'
    (d / 'real').mkdir(parents=True)
    (d / 'alias').symlink_to(d / 'real')
    good = d / 'good.txt'
    good.write_bytes(bases['L3'])

    def put(p: Path, data: bytes = bases['L3']) -> Path:
        p.write_bytes(data)
        return p
    (d / 'dangling').symlink_to(d / 'r3.out.tmp')
    put(d / 'o5.txt')
    put(d / 'h7.txt')
    os.link(d / 'h7.txt', d / 'h7_link.txt')
    cases = [('input_is_its_own_tmp', [(put(d / 'r1.tmp'), d / 'r1')], r'temporary file .*r1\.tmp of job 0 exists', [d / 'r1']),
             ('input_is_a_tmp_via_dangling_link', [(good, d / 'r3.out'), (d / 'dangling', d / 'x3.out')],
              r'input path .*dangling of job 1 is the temporary file of job 0', [d / 'r3.out', d / 'x3.out']),
             ('outputs_one_directory_two_spellings', [(good, d / 'real/o4.out'), (good, d / 'alias/o4.out')],
              r'output of job 1 .*alias/o4\.out is the same path as the output of job 0', [d / 'real/o4.out']),
             ('output_is_a_tmp_via_symlinked_dir', [(good, d / 'real/o10.out'), (good, d / 'alias/o10.out.tmp')],
              r'output of job 1 .*alias/o10\.out\.tmp is the same path as the temporary file of job 0', [d / 'real/o10.out', d / 'real/o10.out.tmp']),
             ('input_is_an_output', [(good, d / 'o5.txt'), (d / 'o5.txt', d / 'o6.out')], r'input path .*o5\.txt of job 1 is the output of job 0',
              [d / 'o6.out']),
             ('input_is_an_output_by_identity', [(good, d / 'h7.txt'), (d / 'h7_link.txt', d / 'o8.out')],
              r'input path .*h7_link\.txt of job 1 is the same file as the output of job 0', [d / 'o8.out']),
             ('existing_tmp_never_overwritten', [(good, d / 'o9.out')], r'temporary file .*o9\.out\.tmp of job 0 exists', [d / 'o9.out'])]
    put(d / 'o9.out.tmp', b'another run\n')
    for name, pairs, reason, absent in cases:
        before = {p: p.read_bytes() for p in d.rglob('*') if p.is_file() and not p.is_symlink()}
        cp = run(B.regen, jobs(d, pairs, f'{name}.jobs'))
        err = cp.stderr.decode(errors='replace')
        assert cp.returncode == 2 and cp.stdout == b'' and re.search(re.escape(str(d / f'{name}.jobs')) + ': .*' + reason, err), (name, cp.returncode, err[-1500:])
        after = {p: p.read_bytes() for p in d.rglob('*') if p.is_file() and not p.is_symlink()}
        after.pop(d / f'{name}.jobs')
        assert after == before, (name, sorted(set(after) ^ set(before)), [p for p in before if after.get(p) != before[p]])
        assert not any(p.exists() for p in absent), (name, [p for p in absent if p.exists()])
    probe = d / 'CaseProbe'
    probe.write_text('x')
    insensitive = (d / 'caseprobe').exists()
    if insensitive:
        cp = run(B.regen, jobs(d, [(good, d / 'c11.out'), (good, d / 'C11.out')], 'case.jobs'))
        err = cp.stderr.decode(errors='replace')
        assert cp.returncode == 2 and cp.stdout == b'' and 'C11.out.tmp (it exists: never overwritten)' in err, (cp.returncode, err[-1500:])
        assert not (d / 'c11.out').exists() and not (d / 'c11.out.tmp').exists()
    ok('S1-02_job_list_collisions_and_exclusive_temporaries', cases=[c[0] for c in cases], case_insensitive_fs_checked=insensitive)


def test_mixed(B: Bins, td: Path, bases: dict) -> None:
    d = td / 'mixed'
    d.mkdir()
    goods = []
    for k in ('L2', 'L3', 'L7p'):
        f = d / f'good_{k}.txt'
        f.write_bytes(bases[k])
        goods.append(f)
    bad = d / 'bad.txt'
    bad.write_bytes(dict((n, x) for n, x, _ in targeted_cases(Base(bases['L3'])))['term_index_M'])
    pairs = [(goods[0], d / 'o0.txt'), (bad, d / 'ob.txt'), (goods[1], d / 'o1.txt'), (goods[2], d / 'o2.txt')]
    cp = run(B.regen, jobs(d, pairs))
    check_failure(cp, 'mixed', str(bad), r'term 0 index \d+ \d+ out of range', [o for _, o in pairs],
                  others=[str(g) for g in goods])
    assert not list(d.glob('*.tmp')), list(d.glob('*.tmp'))
    ok('A-INV-1_mixed_list_names_only_the_bad_file_renames_nothing')


def test_idempotent_and_records(B: Bins, td: Path, bases: dict) -> None:
    d = td / 'idem'
    d.mkdir()
    pairs = []
    for k in ('L2', 'L3', 'L7p', 'L8'):
        f = d / f'{k}.txt'
        f.write_bytes(bases[k])
        pairs.append((f, d / f'{k}.out'))
    cp = run(B.regen, jobs(d, pairs), timeout=60)
    assert cp.returncode == 0, cp.stderr.decode()[-2000:]
    recs = json.loads(cp.stdout)
    assert [r['file'] for r in recs] == [str(o) for _, o in pairs]
    for (f, o), rec in zip(pairs, recs):
        if f.read_bytes().startswith(b'C7D3GRAPH1'):
            assert o.read_bytes() == f.read_bytes(), f'{f}: a d=3 file run through again changed'
        g = c.parse_gfile(o.read_bytes(), str(o))
        assert g.magic == 'C7D3GRAPH1'
        assert c.same_body(f.read_bytes().replace(b'C7D3GRAPH1', b'C7D2GRAPH1', 1), o.read_bytes()), f
        positive, raw = c.d3_rates(g)
        ALL = (1 << g.E) - 1
        assert c.gfile_lines(o.read_bytes())[-1] == c.d3_rate_line(g), f
        inner = range(1, ALL)
        hist: dict[str, int] = {}
        for s in inner:
            if raw[s] <= 0:
                hist[str(raw[s])] = hist.get(str(raw[s]), 0) + 1
        want = dict(L=g.L, id=g.id, cancelled_nonpositive_subsets=sum(raw[s] <= 0 for s in inner),
                    minimum_rate_quarters=min(positive[s] for s in inner), raw_histogram=hist,
                    min_raw=min(raw[s] for s in inner), double_lift_subsets=sum(raw[s] <= -5 for s in inner))
        got = {k: rec[k] for k in want}
        assert got == want, (f, got, want)
        assert list(rec) == ['file', 'L', 'id', 'cancelled_nonpositive_subsets', 'minimum_rate_quarters',
                             'raw_histogram', 'min_raw', 'double_lift_subsets'], list(rec)
    # second pass over the L8 output (d=3 now) is byte-unchanged
    o8 = pairs[-1][1]
    cp = run(B.regen, jobs(d, [(o8, d / 'L8.again')], 'again.jobs'), timeout=60)
    assert cp.returncode == 0 and (d / 'L8.again').read_bytes() == o8.read_bytes()
    ok('A-INV-1_idempotent_d3_and_records_match_python_recomputation',
       records={k: {x: r[x] for x in ('raw_histogram', 'min_raw', 'double_lift_subsets')} for k, r in zip(('L2', 'L3', 'L7p', 'L8'), recs)})


# ---- the seeded mutation corpus ----------------------------------------------------------------------------------
REPLACEMENTS = None


def mutate(data: bytes, rng: random.Random) -> tuple[str, bytes]:
    kind = rng.choice(('byte_flip', 'deletion', 'insertion', 'token_swap', 'token_replace'))
    if kind in ('token_swap', 'token_replace'):
        parts = re.split(rb'(\s+)', data)
        idx = [i for i, p in enumerate(parts) if p and not p.isspace()]
        if kind == 'token_swap':
            i, j = rng.sample(idx, 2)
            parts[i], parts[j] = parts[j], parts[i]
        else:
            M = data.split()[5]
            parts[rng.choice(idx)] = rng.choice((M, b'-1', b'0', str(2**31).encode(), b'65536'))
        return kind, b''.join(parts)
    pos = rng.randrange(len(data) + (kind == 'insertion'))
    if kind == 'byte_flip':
        b = bytearray(data)
        b[pos] ^= 1 << rng.randrange(8)
        return kind, bytes(b)
    if kind == 'deletion':
        n = rng.choice((1, 1, 2, 5, 20))
        return kind, data[:pos] + data[pos + n:]
    ins = bytes(rng.choice(b'0123456789 -\n.xe') for _ in range(rng.choice((1, 1, 2, 4))))
    return kind, data[:pos] + ins + data[pos:]


def one_mutant(B: Bins, d: Path, tag: str, data: bytes) -> dict:
    f = d / f'{tag}.txt'
    f.write_bytes(data)
    out = d / f'{tag}.out'
    cp = run(B.regen, jobs(d, [(f, out)], f'{tag}.jobs'))
    err = cp.stderr.decode(errors='replace')
    if any(s in err for s in REPORT_PATTERNS) or cp.returncode not in (0, 2):
        raise AssertionError(f'{tag}: status {cp.returncode}, stderr {err[-3000:]}')
    if cp.returncode == 2:
        assert cp.stdout == b'' and err.startswith(f'{f}: ') and not out.exists() and not Path(f'{out}.tmp').exists(), (tag, err)
        res = 'exit2'
    else:
        again = d / f'{tag}.again'
        cp2 = run(B.regen, jobs(d, [(out, again)], f'{tag}.jobs2'))
        assert cp2.returncode == 0 and again.read_bytes() == out.read_bytes(), (tag, cp2.returncode, cp2.stderr[-500:])
        res = 'exit0_stable'
        again.unlink()
        out.unlink()
    for p in (f, d / f'{tag}.jobs', d / f'{tag}.jobs2'):
        if p.exists():
            p.unlink()
    return dict(result=res, seconds=cp.seconds)


def test_corpus(B: Bins, td: Path, bases: dict, per_base: int) -> None:
    d = td / 'corpus'
    d.mkdir()
    rng = random.Random(SEED)
    work = []
    for k in ('L2', 'L3', 'L7p', 'L8'):
        for i in range(per_base):
            kind, data = mutate(bases[k], rng)
            work.append((f'{k}_{i:03d}_{kind}', data))
    workers = max(1, min(32, len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count() or 1))
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda w: one_mutant(B, d, *w), work))
    counts: dict[str, int] = {}
    for (tag, _), r in zip(work, res):
        key = tag.split('_')[0] + ':' + r['result']
        counts[key] = counts.get(key, 0) + 1
    ok('A-INV-1_mutation_corpus_seed_8814', mutants=len(work), outcomes=counts,
       max_seconds=round(max(r['seconds'] for r in res), 3))


# ---- the coverage self-test (C.7) ----------------------------------------------------------------------------------
FRAME = re.compile(r'#(\d+) 0x[0-9a-f]+ in (.*?) ([^ ]*regenerate_rates\.cpp):(\d+)')


def site_line() -> int:
    lines = [i + 1 for i, s in enumerate((GEN3 / 'regenerate_rates.cpp').read_text().splitlines()) if 'dist[masks[m]]' in s]
    assert len(lines) == 1, lines
    return lines[0]


def test_selftest(B: Bins, td: Path, bases: dict) -> None:
    d = td / 'selftest'
    d.mkdir()
    data = dict((n, x) for n, x, _ in targeted_cases(Base(bases['L3'])))['term_index_M']
    f = d / 'index_M.txt'
    f.write_bytes(data)
    out = d / 'index_M.out'
    cp = run(B.unguarded, jobs(d, [(f, out)]))
    err = cp.stderr.decode(errors='replace')
    assert cp.returncode == -signal.SIGABRT, (cp.returncode, err[-3000:])
    assert '__n < this->size()' in err, err[-3000:]
    frames = [(int(m.group(1)), m.group(3), int(m.group(4))) for m in FRAME.finditer(err)]
    assert frames, err[-3000:]
    line = site_line()
    assert frames[0][2] == line, (frames, line)
    # the control: the ordinary sanitizer build exits 2 naming the file and the index reason
    cp2 = run(B.regen, jobs(d, [(f, out)], 'control.jobs'))
    check_failure(cp2, 'selftest_control', str(f), r'term 0 index \d+ \d+ out of range', [out])
    ok('C.7_unguarded_index_selftest_aborts_at_the_dist_masks_site', site_line=line, first_package_frame=frames[0])


# ---- main ----------------------------------------------------------------------------------------------------------
def load_bases() -> dict:
    ref = ROOT / 'reference/inputs'
    return {'L2': (ref / 'free/L2/G0.txt').read_bytes(), 'L3': smallest(ref / 'free/L3').read_bytes(),
            'L7p': smallest(ref / 'power/L7').read_bytes(), 'L8': synthetic_l8()}


def regen_tests(a, td: Path) -> None:
    B = Bins(a, td)
    bases = load_bases()
    test_targeted(B, td, bases)
    test_collisions(B, td, bases)
    test_mixed(B, td, bases)
    test_idempotent_and_records(B, td, bases)
    test_corpus(B, td, bases, a.corpus)
    if a.sanitize:
        test_selftest(B, td, bases)
    tool_tests.B = B


class tool_tests:   # filled by the tools part (test_tool_* functions, registered below)
    B = None
    funcs: list = []


# ==== the gate tools (tiny fixtures) =================================================================================
def tool(script: str, *args, check: int | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    cp = subprocess.run([sys.executable, '-B', str(GEN3 / script), *map(str, args)], capture_output=True, text=True,
                        env=env or dict(os.environ))
    if check is not None:
        assert cp.returncode == check, (script, args, cp.returncode, cp.stdout[-2000:], cp.stderr[-2000:])
    assert 'Traceback' not in cp.stderr, (script, args, cp.stderr[-3000:])
    return cp


def register(fn):
    tool_tests.funcs.append(fn)
    return fn


def decode(key: int, n: int) -> list[tuple[int, int]]:
    edges, k = [], 0
    for a in range(n):
        for b in range(a + 1, n):
            edges += [(a, b)] * (key >> (2 * k) & 3)
            k += 1
    return edges


def weights(key: int, aut: int, n: int):
    from fractions import Fraction
    from math import factorial
    deg = [0] * n
    den = aut
    for a, b in decode(key, n):
        deg[a] += 1
        deg[b] += 1
    k = 0
    for a in range(n):
        for b in range(a + 1, n):
            den *= factorial(key >> (2 * k) & 3)
            k += 1
    sg = sum((4 - d) * (3 - d) for d in deg)
    for d in deg:
        den *= factorial(4 - d)
    wa = Fraction(24, den)
    return den, sg, wa, wa * sg / 12


def brute_forests(subs: list[int]) -> int:
    from itertools import combinations
    def ok(a, b):
        return (a & b) == a or (a & b) == b or bin(a & b).count('1') <= 1
    n = 0
    for r in range(len(subs) + 1):
        for fam in combinations(subs, r):
            n += all(ok(a, b) for a, b in combinations(fam, 2))
    return n


def ld_text(w) -> str:
    """A JSON number with 22 significant digits, as H1's builders print long doubles (a marker, unquoted later)."""
    from decimal import Context
    return '@num:' + (format(Context(prec=22).divide(w.numerator, w.denominator), 'f') if w else '0')


def l3_fixture(td: Path) -> dict:
    """An H1-like miniature at L = 3 from the package's own files: classes3.txt, C8(1)'s L3_inventory.txt, the C7(3)
    d=3 L3 payloads (free 0, 1, 3, 5, 6; power 7). Selection with the L8 rule (finite, s_G != 4)."""
    import fractions
    ref = ROOT / 'reference'
    t = (ref / 'c8d1_inputs8/classes3.txt').read_text().split()
    n, ng = int(t[0]), int(t[1])
    side = (ref / 'c8d1_inputs8/L3_inventory.txt').read_text().split('\n')
    h1, d3 = td / 'h1', td / 'd3'
    for d in (h1, d3 / 'L3_free', d3 / 'L3_power'):
        d.mkdir(parents=True)
    finite = {'free': [0, 1, 3, 5, 6], 'power': [7]}
    inv = dict(schema='c8-inventory-d2-builder-1', L=3, free=[], power=[])
    sa = sb = fractions.Fraction(0)
    for i in range(ng):
        key, aut, orbit = int(t[2 + 3 * i]), int(t[3 + 3 * i]), int(t[4 + 3 * i])
        den, sg, wa, wb = weights(key, aut, n)
        sa, sb = sa + wa, sb + wb
        h = side[1 + 3 * i].split()
        subs = [int(x) for x in side[2 + 3 * i].split()]
        nlog, npow = int(h[6]), int(h[7])
        base = dict(id=i, L=3, key=key, denominator=den, mass_numerator=sg, orbit=orbit, wa=ld_text(wa), wb=ld_text(wb),
                    power_subgraphs=npow, log_subgraphs=nlog, primitive=nlog == 0 and npow == 0)
        for s in ('free', 'power'):
            r = dict(base)
            if s == 'free' and npow:
                r['status'] = 'power-sector-not-integrated'
            elif s == 'power' and not npow:
                r['status'] = 'not-power'
            elif i in finite[s]:
                g = c.parse_gfile((ref / f'inputs/{s}/L3/G{i}.txt').read_bytes())
                r.update(masks=g.M, terms=g.T, status='finite-kernel', file=f'L3/G{i}.txt',
                         edges=[list(e) for e in decode(key, n)])
                (d3 / f'L3_{s}' / f'G{i}.txt').write_bytes((ref / f'inputs/{s}/L3/G{i}.txt').read_bytes())
            else:
                r['status'] = 'exact-zero-kernel'
            if s == 'free' and not npow:
                r['forests'] = brute_forests(subs)
            inv[s].append(r)
    (h1 / 'inventory_L3.json').write_text(re.sub(r'"@num:([^"]+)"', r'\1', json.dumps(inv)))
    sel = {'L3': {s: [i for i in finite[s] if inv[s][i]['mass_numerator'] != 4] for s in finite}}
    (h1 / 'selection.json').write_text(json.dumps(sel))
    return dict(h1=h1, d3=d3, sums=(sa, sb), sel=sel, inv=inv)


@register
def test_tool_refuse_c62d(td: Path) -> None:
    hits = ['/expanse/lustre/scratch/zzheng8/temp_project/c8d2', '/expanse/lustre/scratch/zzheng8/temp_project/c8d2/x/y',
            '/expanse/lustre/scratch/zzheng8/temp_project/LRI_C8_shared/inventory/inventory8_d2/z',
            str(td / 'LRI_C8_shared/inventory/q'), '/expanse/lustre/scratch/zzheng8/temp_project/c8d3/../c8d2/w']
    misses = ['/expanse/lustre/scratch/zzheng8/temp_project/c8d3/store/h1/x', '/expanse/lustre/scratch/zzheng8/temp_project/c8d2x',
              str(td / 'LRI_C8_shared/assembly/H1_gates/x.json'), str(td / 'inventory/x')]
    assert all(c.under_c62d(p) for p in hits), [p for p in hits if not c.under_c62d(p)]
    assert not any(c.under_c62d(p) for p in misses), [p for p in misses if c.under_c62d(p)]
    real = td / 'LRI_C8_shared' / 'inventory'
    real.mkdir(parents=True)
    (td / 'link').symlink_to(real)
    assert c.under_c62d(td / 'link' / 'out.json'), 'a symlink into the shared inventory must be refused'
    bad = td / 'link' / 'o.json'
    for script, args in (('weights_check.py', ['--classes', 'x', '--inventory', 'x', '--output', bad]),
                         ('opcount.py', ['compare', '--payload', 'x', '--sizes', 'x', '--inventory', 'x', '--output', bad]),
                         ('kirchhoff3.py', ['--payload', 'x', '--inventory', 'x', '--output', bad]),
                         ('forest_check.py', ['--side', 'x', '--c8d1', 'x', '--inventory', 'x', '--output', bad]),
                         ('check_dimension8.py', ['--output', bad]),
                         ('gates_d3.py', ['gate1a', '--d2', 'x', '--bin', 'x', '--work', td / 'w', '--evidence', td / 'link' / 'ev']),
                         ('gates_d3.py', ['h1-copy', '--source', 'x', '--store', td / 'link' / 'h1', '--pin', '0' * 64, '--evidence', td / 'e']),
                         ('publish_d3.py', ['--stage', 'x', '--gates', 'x', '--side', 'x', '--audits', 'x',
                                            '--target', td / 'link' / 'd3_payload', '--h1-pin', '0' * 64, '--commit', 'x'])):
        cp = tool(script, *args)
        assert cp.returncode == 2 and "under C62d's tree" in cp.stderr, (script, cp.returncode, cp.stderr[-500:])
    cp = subprocess.run(['bash', str(GEN3 / 'run_d3.sh'), '--pre-h1', '--d2', 'x', '--evidence', str(td / 'link' / 'ev'),
                         '--work', str(td / 'w')], capture_output=True, text=True)
    assert cp.returncode == 2 and "under C62d's tree" in cp.stderr, (cp.returncode, cp.stderr)
    # S1-01: size_probe's masks output (a symlinked parent, a symlink to an existing file there, the lexical c8d2 prefix):
    # exit 2 before anything is computed or opened; the existing file keeps its bytes; an ordinary path is written
    classes3 = str(ROOT / 'reference/c8d1_inputs8/classes3.txt')
    other = td / 'b' / 'LRI_C8_shared' / 'inventory'
    other.mkdir(parents=True)
    (other / 'masks_L3.txt').write_text('keep\n')
    (td / 'masks_link.txt').symlink_to(other / 'masks_L3.txt')
    # R2-S1-01: dangling links whose absent targets lie in the shared inventory (absolute, relative, a chain of two links)
    # or under the c8d2 prefix are refused as such; a link to an absent file in an ordinary directory is refused as a link
    (td / 'masks_dangling.txt').symlink_to(other / 'masks_new.txt')
    (td / 'b' / 'masks_rel.txt').symlink_to(Path('LRI_C8_shared/inventory/masks_rel_new.txt'))
    (td / 'masks_hop.txt').symlink_to(td / 'b' / 'masks_rel.txt')
    (td / 'masks_c8d2.txt').symlink_to(f'{c.C8D2_PREFIX}/masks_L3.txt')
    for out in (td / 'link' / 'masks_L3.txt', td / 'masks_link.txt', f'{c.C8D2_PREFIX}/masks_L3.txt', td / 'masks_dangling.txt',
                td / 'b' / 'masks_rel.txt', td / 'masks_hop.txt', td / 'masks_c8d2.txt'):
        cp = subprocess.run([str(tool_tests.B.size_probe), classes3, str(out)], capture_output=True, text=True)
        assert cp.returncode == 2 and "under C62d's tree" in cp.stderr and not cp.stdout, ('size_probe', out, cp.returncode, cp.stderr[-500:])
    plain = td / 'plain'
    plain.mkdir()
    (td / 'masks_plain_link.txt').symlink_to(plain / 'masks_L3.txt')
    cp = subprocess.run([str(tool_tests.B.size_probe), classes3, str(td / 'masks_plain_link.txt')], capture_output=True, text=True)
    assert cp.returncode == 2 and 'is a symbolic link' in cp.stderr and not cp.stdout, (cp.returncode, cp.stderr[-500:])
    assert sorted(x.name for x in other.iterdir()) == ['masks_L3.txt'] and not any(plain.iterdir()), (list(other.iterdir()), list(plain.iterdir()))
    assert (other / 'masks_L3.txt').read_text() == 'keep\n'
    cp = subprocess.run([str(tool_tests.B.size_probe), classes3, str(td / 'masks_L3.txt')], capture_output=True, text=True)
    assert cp.returncode == 0 and cp.stdout.startswith('L,id,status') and (td / 'masks_L3.txt').read_text().startswith('4 '), (cp.returncode, cp.stderr)
    assert not any(real.iterdir()), list(real.iterdir())
    ok('A-INV-6_refusal_of_C62d_trees_every_gen3_writer', refused_tools=10, size_probe_dangling_links=4)


def mini_stage(td: Path) -> tuple[Path, Path, Path, Path]:
    """A miniature J-GEN-D3 stage: four stems of three G-files each; a gates directory holding the files the real gate
    tools write (g3common.H1_GATES' gate records, g3common.GATE_SUPPORT's supporting records: the tools' own outputs
    with "passed", and H1's raw check_edge_forests outputs, shaped {L, graphs, failures, seconds, rows}, without it);
    the four builder side files; the two rate audits."""
    stage, gates, side, audits = td / 'stage', td / 'gates', td / 'side', td / 'audits'
    for k, stem in enumerate(c.SIDE_STEMS):
        (stage / stem).mkdir(parents=True)
        for gid in (k + 1, 10 + k, 2 + 3 * k):
            (stage / stem / f'G{gid}.txt').write_text(f'C7D3GRAPH1 {stem} {gid}\n')
    gates.mkdir()
    for g in c.H1_GATES:
        (gates / f'{g}.json').write_text(json.dumps(dict(schema='c8-d3-gate-1', gate=g, passed=True, checks={'x': {'passed': True}})))
        for name in c.GATE_SUPPORT.get(g, ()):
            L = int(name.rsplit('_L', 1)[1][0]) if g == 'gate3' else None
            rec = (dict(L=L, graphs={7: 1091, 8: 7231}[L], failures=0, seconds=0.29,
                        rows=[dict(id=10, subgraphs=13, forests=1024, terms=0, matches_induced=True)])
                   if g == 'gate3' else dict(schema=f'c8-d3-{name[:-5]}', passed=True))
            (gates / name).write_text(json.dumps(rec))
    side.mkdir()
    for stem in c.SIDE_STEMS:
        (side / c.side_file(stem)).write_text(f'0 {stem}\n')
    audits.mkdir()
    for L in (7, 8):
        (audits / f'rate_audit_L{L}.json').write_text('[]\n')
    return stage, gates, side, audits


def fake_check_edge_forests(d: Path) -> Path:
    """A stand-in for H1's check_edge_forests: CLASSES PAYLOAD_DIR OUT -> H1's record shape (no "passed")."""
    d.mkdir(parents=True, exist_ok=True)
    b = d / 'check_edge_forests'
    b.write_text(f'#!{sys.executable}\n'
                 'import json, sys\n'
                 'L = int(sys.argv[1].rsplit("classes", 1)[1][0])\n'
                 'json.dump(dict(L=L, graphs={7: 1091, 8: 7231}[L], failures=0, seconds=0.01,\n'
                 '               rows=[dict(id=1, subgraphs=2, forests=4, terms=0, matches_induced=True)]), open(sys.argv[3], "w"))\n')
    b.chmod(0o755)
    return d


def flip_byte(p: Path, at: int = -2) -> None:
    b = bytearray(p.read_bytes())
    b[at] ^= 1
    p.write_bytes(bytes(b))


@register
def test_tool_publish_and_verify_d3(td: Path) -> None:
    stage, gates, side, audits = mini_stage(td)
    # gate 3 and the determinism gate written by the real gates_d3.py (gate 3 with a check_edge_forests stand-in), so
    # the gates directory holds what J-GEN-D3 writes: gate records, supporting records, H1's raw outputs (no "passed")
    for f in [gates / 'gate3.json', gates / 'determinism.json', *(gates / n for n in c.GATE_SUPPORT['gate3'])]:
        f.unlink()
    tool('gates_d3.py', 'gate3', '--bin', fake_check_edge_forests(td / 'h1bin'), '--d3', stage, '--classes', td,
         '--evidence', gates, check=0)
    tool('gates_d3.py', 'determinism', '--a', stage, '--b', stage, '--evidence', gates, check=0)
    want = sorted([f'{g}.json' for g in c.H1_GATES] + [n for v in c.GATE_SUPPORT.values() for n in v])
    assert sorted(p.name for p in gates.iterdir()) == want, sorted(p.name for p in gates.iterdir())
    raw = json.loads((gates / c.GATE_SUPPORT['gate3'][1]).read_text())
    assert 'passed' not in raw and raw['graphs'] == 7231, raw
    target = td / 'pub' / 'd3_payload'
    target.parent.mkdir()
    pub = ['--stage', stage, '--gates', gates, '--side', side, '--audits', audits, '--target', target, '--h1-pin', 'a' * 64,
           '--commit', 'test', '--tar', 'python']

    def refused(rc, text):
        cp = tool('publish_d3.py', *pub, check=rc)
        assert text in cp.stderr and not target.exists() and not list(target.parent.iterdir()), (text, cp.stderr[-800:])
    # a failed or missing gate record, a failed or missing supporting record, a non-object record, a missing side file:
    # nothing published
    keep = (gates / 'gate4.json').read_text()
    (gates / 'gate4.json').write_text(json.dumps(dict(passed=False)))
    refused(1, 'gate4.json: gate did not pass')
    (gates / 'gate4.json').unlink()
    refused(1, 'required gate record missing')
    (gates / 'gate4.json').write_text(keep)
    keep = (gates / 'gate2_weights.json').read_text()
    (gates / 'gate2_weights.json').write_text(json.dumps(dict(passed=False)))
    refused(1, 'gate2_weights.json: supporting record did not pass')
    (gates / 'gate2_weights.json').unlink()
    refused(1, 'gate2_weights.json: supporting record of gate2 missing')
    (gates / 'gate2_weights.json').write_text(keep)
    (gates / 'stray.json').write_text('[1]')
    refused(1, 'stray.json: not a JSON object')
    (gates / 'stray.json').unlink()
    keep = (side / 'L8_power.subgraphs.txt').read_bytes()
    (side / 'L8_power.subgraphs.txt').unlink()
    refused(2, 'L8_power.subgraphs.txt: missing builder side file')
    (side / 'L8_power.subgraphs.txt').write_bytes(keep)
    cp = tool('publish_d3.py', *pub, check=0)
    pin = json.loads(cp.stdout)['manifest_sha256']
    assert pin == c.sha256_file(target / 'MANIFEST_d3.json')
    tool('verify_d3.py', target, '--pin', pin, check=0)
    cp = tool('publish_d3.py', *pub)
    assert cp.returncode == 2 and 'exists' in cp.stderr, 'a second publish must refuse'
    man = json.loads((target / 'MANIFEST_d3.json').read_text())
    assert man['schema'] == 'c8-d3-d3-payload-1' and man['h1_manifest_sha256'] == 'a' * 64 and man['sha256sums_md5']
    assert man['counts'] == {s: 3 for s in c.SIDE_STEMS}
    # every gate file published unchanged (the raw gate-3 outputs among them), the side files under gates/gate5/,
    # all listed in SHA256SUMS
    listed = {ln.split('  ', 1)[1] for ln in (target / 'SHA256SUMS').read_text().splitlines()}
    for n in want:
        assert (target / 'gates' / n).read_bytes() == (gates / n).read_bytes() and f'gates/{n}' in listed, n
    for stem in c.SIDE_STEMS:
        rel = f'{c.SIDE_DIR}/{c.side_file(stem)}'
        assert (target / rel).read_bytes() == (side / c.side_file(stem)).read_bytes() and rel in listed, rel
        assert man['gate5_side_files'][rel] == c.sha256_file(side / c.side_file(stem))
    assert man['gate_records'] == [f'gates/{n}' for n in want]
    # a one-byte change at every level fails verification; so do an unlisted and a missing file
    import tarfile

    def case(name, mutate, step):
        t2 = td / f'v_{name}'
        shutil.copytree(target, t2)
        mutate(t2)
        cp = tool('verify_d3.py', t2, '--pin', pin, check=1)
        assert f'{step}: FAIL' in cp.stdout, (name, cp.stdout)

    def member(t2):
        tp = t2 / 'payload/L8_power.tar'
        with tarfile.open(tp) as tf:
            items = [(m, tf.extractfile(m).read()) for m in tf]
        with tarfile.open(tp, 'w', format=tarfile.GNU_FORMAT) as tf:
            for k, (m, data) in enumerate(items):
                if k == 0:
                    data = data[:-2] + bytes([data[-2] ^ 1]) + data[-1:]
                tf.addfile(m, io.BytesIO(data))
    case('manifest', lambda t2: flip_byte(t2 / 'MANIFEST_d3.json'), '1_external_pin')
    case('sha256sums', lambda t2: flip_byte(t2 / 'SHA256SUMS', 3), '2_manifest_pins_sha256sums')
    case('members', lambda t2: flip_byte(t2 / 'MEMBERS_d3.sha256', 3), '3_sha256sums')
    case('members_step4', lambda t2: flip_byte(t2 / 'MEMBERS_d3.sha256', 3), '4_members')
    case('tar', lambda t2: flip_byte(t2 / 'payload/L7_free.tar', 600), '3_sha256sums')
    case('member', member, '4_members')
    case('side_file', lambda t2: flip_byte(t2 / c.SIDE_DIR / 'L7_free.subgraphs.txt'), '3_sha256sums')
    case('raw_gate3', lambda t2: flip_byte(t2 / 'gates' / c.GATE_SUPPORT['gate3'][0]), '3_sha256sums')
    case('unlisted', lambda t2: (t2 / 'gates/extra.json').write_text('{}'), '3_sha256sums')
    case('missing', lambda t2: (t2 / 'rate_audit_L7.json').unlink(), '3_sha256sums')
    case('missing_side', lambda t2: (t2 / c.SIDE_DIR / 'L8_free.subgraphs.txt').unlink(), '3_sha256sums')
    cp = tool('verify_d3.py', target, '--pin', 'b' * 64, check=1)
    assert '1_external_pin: FAIL' in cp.stdout
    ok('A-INV-5_publish_atomic_refusals_and_verify_d3_four_steps_one_byte_at_every_level', pin=pin,
       gate_files=len(want), side_files=len(c.SIDE_STEMS))


@register
def test_tool_weights_check(td: Path) -> None:
    f = l3_fixture(td)
    sa, sb = f['sums']
    out = td / 'w.json'
    args = ['--classes', ROOT / 'reference/c8d1_inputs8', '--inventory', f['h1'], '--payload', f['d3'], '--loops', '3',
            '--output', out, '--expect-sums', f'3:{sa}:{sb}']
    tool('weights_check.py', *args, check=0)
    rec = json.loads(out.read_text())['loops']['L3']
    assert rec['payload_headers']['checked'] == 6 and rec['finite'] == {'free': 5, 'power': 1}, rec

    def mutated(name, fn, expect):
        h = td / f'h1_{name}'
        shutil.copytree(f['h1'], h)
        d = td / f'd3_{name}'
        shutil.copytree(f['d3'], d)
        fn(h, d)
        a2 = [h if x == f['h1'] else d if x == f['d3'] else x for x in args]
        cp = tool('weights_check.py', *a2, check=1)
        assert expect in json.dumps(json.loads(out.read_text())), (name, out.read_text()[:1500])

    def inv_edit(field, value, i=3, s='free'):
        def fn(h, d):
            inv = json.loads((h / 'inventory_L3.json').read_text())
            inv[s][i][field] = value
            (h / 'inventory_L3.json').write_text(json.dumps(inv))
        return fn
    mutated('wa', inv_edit('wa', 3.0000000001), 'differs from')
    mutated('den', inv_edit('denominator', 5), 'denominator')
    mutated('sg', inv_edit('mass_numerator', 4, i=0), 'mass_numerator')

    def hdr(h, d):
        p = d / 'L3_free/G5.txt'
        p.write_bytes(p.read_bytes().replace(b' 0.75 0.25 ', b' 0.75 0.2500000001 ', 1))
    mutated('header', hdr, 'header wb')

    def sel(h, d):
        x = json.loads((h / 'selection.json').read_text())
        x['L3']['free'].append(5)    # s_G = 4: must not be selected at the top loop
        (h / 'selection.json').write_text(json.dumps(x))
    mutated('selection', sel, 'selection.json')
    cp = tool('weights_check.py', *args[:-2], '--expect-sums', f'3:{sa + 1}:{sb}', check=1)
    ok('gate2b_weights_check_exact_on_a_miniature_and_each_alteration_fails')


@register
def test_tool_opcount_and_kirchhoff(td: Path) -> None:
    f = l3_fixture(td)
    sizes = td / 'sizes'
    sizes.mkdir()
    with open(sizes / 'sizes_L3.csv', 'w') as fh:
        subprocess.run([str(tool_tests.B.size_probe), str(ROOT / 'reference/c8d1_inputs8/classes3.txt')], stdout=fh, check=True)
    out = td / 'op.json'
    (f['h1'] / 'selection.json').write_text(json.dumps({'L3': {'free': [0, 1, 3, 5, 6], 'power': [7]}}))   # every finite kernel
    counts = json.dumps({'L3_free': 5, 'L3_power': 1})
    tool('opcount.py', 'compare', '--payload', f['d3'], '--sizes', sizes, '--inventory', f['h1'], '--loops', '3',
         '--expect-counts', counts, '--output', out, check=0)
    p = f['d3'] / 'L3_free/G3.txt'
    keep = p.read_bytes()
    g = c.parse_gfile(keep)
    p.write_bytes(keep.replace(b'\n' + ' '.join(map(str, g.masks)).encode(), b'\n' + ' '.join(map(str, g.masks[:-1])).encode(), 1)
                  .replace(f' {g.M} {g.T}\n'.encode(), f' {g.M - 1} {g.T}\n'.encode(), 1))
    tool('opcount.py', 'compare', '--payload', f['d3'], '--sizes', sizes, '--inventory', f['h1'], '--loops', '3',
         '--expect-counts', counts, '--output', out, check=1)
    p.write_bytes(keep)
    kout = td / 'k.json'
    ks = ['--sample', '3:free:1:2', '--sample', '3:power:0:1']
    tool('kirchhoff3.py', '--payload', f['d3'], '--inventory', f['h1'], '--loops', '3', *ks, '--output', kout, check=0)
    assert json.loads(kout.read_text())['kernels'] == 4
    inv = json.loads((f['h1'] / 'inventory_L3.json').read_text())
    for r in inv['free']:
        if r.get('edges'):
            r['edges'][0], r['edges'][-1] = [0, 3], [0, 1]   # a wrong graph
    (f['h1'] / 'inventory_L3.json').write_text(json.dumps(inv))
    tool('kirchhoff3.py', '--payload', f['d3'], '--inventory', f['h1'], '--loops', '3', *ks, '--output', kout, check=1)
    ok('gate2a_opcount_and_gate4_kirchhoff_on_a_miniature_with_negative_controls')


@register
def test_tool_forest_check(td: Path) -> None:
    f = l3_fixture(td)
    c8d1, side = td / 'c8d1', td / 'side'
    c8d1.mkdir()
    side.mkdir()
    src = ROOT / 'reference/c8d1_inputs8/L3_inventory.txt'
    shutil.copy(src, c8d1 / 'L3_inventory.txt')
    import forest_check as fc
    _, rows = fc.read_side(src)
    (c8d1 / 'L3_summary.json').write_text(json.dumps(dict(forests=sum(brute_forests(r['subs']) for r in rows))))
    for s in ('free', 'power'):
        shutil.copy(src, side / f'L3_{s}.subgraphs.txt')
    out = td / 'f.json'
    args = ['--side', side, '--c8d1', c8d1, '--inventory', f['h1'], '--loops', '3', '--output', out]
    tool('forest_check.py', *args, check=0)
    keep = (side / 'L3_power.subgraphs.txt').read_bytes()
    (side / 'L3_power.subgraphs.txt').write_bytes(keep.replace(b'\n6 9 14 \n', b'\n6 9 13 \n', 1))
    tool('forest_check.py', *args, check=1)
    rec = json.loads(out.read_text())
    assert rec['c_masks'] is False and rec['loops']['L3']['power']['mismatches_vs_c8d1']['log_lists'] == 1, rec
    (side / 'L3_power.subgraphs.txt').write_bytes(keep[:-3])
    tool('forest_check.py', *args, check=1)
    (side / 'L3_power.subgraphs.txt').write_bytes(keep)
    inv = json.loads((f['h1'] / 'inventory_L3.json').read_text())
    inv['free'][4]['forests'] += 1
    (f['h1'] / 'inventory_L3.json').write_text(json.dumps(inv))
    tool('forest_check.py', *args, check=1)
    assert json.loads(out.read_text())['d_forests'] is False
    ok('gate5cd_forest_check_strict_reader_and_counts_on_a_miniature')


@register
def test_tool_check_dimension8_lengths(td: Path) -> None:
    import mpmath as m
    sys.path.insert(0, str(GEN3))
    import check_dimension8 as cd
    m.mp.dps = cd.DPS
    o7 = json.loads((ROOT / 'reference/inputs/two_loop.json').read_text())
    hist = ROOT / 'reference/reference/d3_C6_two_loop.json'
    seventh = m.nstr(cd.b2_contour(m, '0.1', 160, 7)[6], 65)
    good8 = td / 'two_loop8.json'
    good8.write_text(json.dumps(dict(dimension=3, order=8, B2=o7['B2'] + [seventh])))
    o7p = td / 'two_loop7.json'
    o7p.write_text(json.dumps(o7))
    rows = []
    for L in range(2, 9):
        rows.append(' '.join([str(8 - L), '1', '0.0'] + [m.nstr(v, 60) for v in cd.log_gamma_jets(m, L)]))
    gamma = td / 'gamma.txt'
    gamma.write_text('\n'.join(rows) + '\n')
    base = ['--two-loop', good8, '--two-loop-order7', o7p, '--historical', hist, '--gamma', gamma]
    out = td / 'cd.json'
    tool('check_dimension8.py', *base, '--output', out, check=0)
    rec = json.loads(out.read_text())['checks']
    assert rec['ii_two_loop']['counts'] == dict(order8_vs_order7_strings=6, order7_vs_historical=5, order8_vs_historical=5,
                                                contour=7, taylor=7) and rec['iii_gamma_rows']['comparisons'] == 42

    def bad(name, path, content, flag, expect):
        q = td / name
        q.write_text(content)
        args = list(base)
        args[args.index(flag) + 1] = q
        tool('check_dimension8.py', *args, '--output', out, check=1)
        txt = out.read_text()
        assert str(q) in txt and expect in txt, (name, txt[:2000])
    bad('order8_six.json', good8, json.dumps(dict(B2=o7['B2'])), '--two-loop', 'expected exactly 7')
    bad('order7_five.json', o7p, json.dumps(dict(B2=o7['B2'][:5])), '--two-loop-order7', 'expected exactly 6')
    h = json.loads(hist.read_text())
    bad('hist_four.json', hist, json.dumps(dict(h, B2_decimal=h['B2_decimal'][:4])), '--historical', 'expected exactly 5')
    bad('hist_six.json', hist, json.dumps(dict(h, B2_decimal=h['B2_decimal'] + ['0'])), '--historical', 'expected exactly 5')
    bad('gamma_six.txt', gamma, '\n'.join(rows[:6]) + '\n', '--gamma', 'expected exactly 7 rows of 9')
    bad('gamma_label.txt', gamma, '\n'.join(rows[::-1]) + '\n', '--gamma', 'labels')
    eighth = json.dumps(dict(B2=o7['B2'][:5] + ['1.0', seventh]))
    bad('order8_prefix.json', good8, eighth, '--two-loop', 'B2 entries differ')
    # S4-006: a non-finite or malformed number fails explicitly (Codex's case: only the seventh B2 string "nan", whose
    # NaN differences passed every tolerance), in each file the comparisons read
    for v in ('nan', 'inf', '-Infinity', 'abc', '1e'):
        bad(f'order8_seventh_{v}.json', good8, json.dumps(dict(B2=o7['B2'] + [v])), '--two-loop', 'is not a finite decimal number')
    bad('hist_nan.json', hist, json.dumps(dict(h, B2_decimal=h['B2_decimal'][:4] + ['nan'])), '--historical', 'is not a finite decimal number')
    for k in (1, 2, 8):   # tokens 2, 3 (not compared) and 9 of the row labelled 0 (L = 8)
        rr = rows[6].split()
        rr[k] = 'nan'
        bad(f'gamma_token{k + 1}_nan.txt', gamma, '\n'.join(rows[:6] + [' '.join(rr)]) + '\n', '--gamma', f'row 0 token {k + 1}')
    ok('gate7_check_dimension8_lengths_prefixes_and_counts')


@register
def test_tool_gate5_logic(td: Path) -> None:
    """Gate 5 (a) and (b) on a synthetic H1 tree, with C8(1)'s real L7/L8 inventories as side files."""
    sys.path.insert(0, str(GEN3))
    import forest_check as fc
    ref = ROOT / 'reference/c8d1_inputs8'
    h1, gen, bin_, regen, side = td / 'h1', td / 'h1gen/src', td / 'h1gen/bin', td / 'regen', td / 'side'
    for d in (h1, gen, bin_, regen / 'regen_inv', side):
        d.mkdir(parents=True)
    (gen / 'build_free.cpp').write_text('// free\n')
    (gen / 'Makefile').write_text('all:\n')
    cmd = {'build_free': 'g++ -O3 -std=c++17 -fopenmp build_free.cpp -o /x/bin/build_free',
           'build_power': 'g++ -O3 -std=c++17 -fopenmp build_power.cpp -o /x/bin/build_power',
           'check_edge_forests': 'g++ -O3 -std=c++17 -fopenmp check_edge_forests.cpp -o /x/bin/check_edge_forests'}
    shas = {}
    for prog, cm in cmd.items():
        (bin_ / prog).write_text(prog)
        (bin_ / f'{prog}.build.txt').write_text(f'command: {cm.replace("/x/bin", str(bin_))}\ncompiler: g++\n')
        shas[prog] = c.sha256_file(bin_ / prog)
    invs = {}
    for L in (7, 8):
        shutil.copy(ref / f'L{L}_inventory.txt', side / f'L{L}_free.subgraphs.txt')
        shutil.copy(ref / f'L{L}_inventory.txt', side / f'L{L}_power.subgraphs.txt')
        _, rows = fc.read_side(ref / f'L{L}_inventory.txt')
        inv = dict(L=L, free=[], power=[])
        for r in rows:
            base = dict(id=r['gi'], key=r['key'], denominator=r['den'], mass_numerator=r['sg'], log_subgraphs=r['nlog'],
                        power_subgraphs=r['npow'])
            inv['free'].append(dict(base, **({'forests': fc.forests(r['subs'])} if not r['npow'] else {})))
            inv['power'].append(dict(base))
        invs[L] = json.dumps(inv).encode()
        (h1 / f'inventory_L{L}.json').write_bytes(invs[L])
        (regen / 'regen_inv' / f'inventory_L{L}.json').write_bytes(invs[L])
    (h1 / 'MEMBERS.sha256').write_text('0' * 64 + '  L7_free/G1.txt\n')
    shutil.copy(h1 / 'MEMBERS.sha256', regen / 'regen_MEMBERS.sha256')
    man = dict(gen_sources_sha256={f'gen/{p.name}': c.sha256_file(p) for p in gen.iterdir()},
               classes_sha256={f'classes{L}.txt': c.sha256_file(ref / f'classes{L}.txt') for L in (7, 8)},
               builders={k: dict(command=v, sha256=shas[k]) for k, v in cmd.items()})
    (h1 / 'MANIFEST.json').write_text(json.dumps(man))
    ev = td / 'ev'
    args = ['gate5', '--inventory', h1, '--h1gen', td / 'h1gen', '--regen', regen, '--side', side, '--classes', ref,
            '--evidence', ev, '--fixture']
    tool('gates_d3.py', *args, check=0)
    rec = json.loads((ev / 'gate5.json').read_text())
    assert rec['gate_5_forest_certificate'] is True and rec['checks']['a_provenance']['binaries']['build_free']['equal']

    def case(name, mutate, undo, sub, cert=False, rc=1):
        mutate()
        tool('gates_d3.py', *args, check=rc)
        r = json.loads((ev / 'gate5.json').read_text())
        undo()
        assert r['checks'][sub]['passed'] is (rc == 0) and r['gate_5_forest_certificate'] is cert, (name, r['checks'][sub])
        return r
    # a binary sha256 differing from the MANIFEST with identical outputs passes, recorded (a warning)
    assert rec['warnings'] == [], rec['warnings']
    r = case('binary', lambda: (bin_ / 'build_power').write_text('other'), lambda: (bin_ / 'build_power').write_text('build_power'),
             'a_provenance', cert=True, rc=0)
    assert r['checks']['a_provenance']['binaries']['build_power']['equal'] is False
    assert len(r['warnings']) == 1 and 'build_power' in r['warnings'][0] and 'passes' in r['warnings'][0], r['warnings']
    keep_side = (side / 'L8_free.subgraphs.txt').read_bytes()
    lines = keep_side.split(b'\n')
    k = next(2 + 3 * i for i in range(len(lines) // 3) if lines[2 + 3 * i].split())
    first = lines[k].split()[0]
    lines[k] = lines[k].replace(first, str(int(first) ^ 1).encode(), 1)   # one log-subgraph mask changed
    case('side_mask', lambda: (side / 'L8_free.subgraphs.txt').write_bytes(b'\n'.join(lines)),
         lambda: (side / 'L8_free.subgraphs.txt').write_bytes(keep_side), 'c_masks')
    keep_m = (regen / 'regen_MEMBERS.sha256').read_bytes()
    case('member_line', lambda: (regen / 'regen_MEMBERS.sha256').write_bytes(keep_m.replace(b'G1', b'G2')),
         lambda: (regen / 'regen_MEMBERS.sha256').write_bytes(keep_m), 'b_correspondence')
    case('inventory_byte', lambda: flip_byte(regen / 'regen_inv/inventory_L7.json', 5),
         lambda: (regen / 'regen_inv/inventory_L7.json').write_bytes(invs[7]), 'b_correspondence')
    case('source', lambda: (gen / 'Makefile').write_text('all:\n\n'), lambda: (gen / 'Makefile').write_text('all:\n'), 'a_provenance')
    bt = bin_ / 'build_free.build.txt'
    keep_bt = bt.read_text()
    case('command', lambda: bt.write_text(keep_bt.replace('-O3', '-O2')), lambda: bt.write_text(keep_bt), 'a_provenance')
    tool('gates_d3.py', *args, check=0)
    # S4-002 (Codex's case): after a passing run, forest_check exits before writing its record (C8(1)'s L8_summary.json
    # missing): (c) and (d) fail, the certificate is false, and the earlier passing record is neither read nor left as
    # the supporting record (set aside as .superseded); no temporary file remains
    c8d1 = td / 'c8d1'
    c8d1.mkdir()
    for L in (7, 8):
        for name in (f'classes{L}.txt', f'L{L}_inventory.txt', f'L{L}_summary.json'):
            shutil.copy(ref / name, c8d1 / name)
    args2 = [c8d1 if x == ref else x for x in args]
    tool('gates_d3.py', *args2, check=0)
    sup = ev / c.GATE_SUPPORT['gate5'][0]
    old_sup = sup.read_bytes()
    assert json.loads(old_sup)['passed'] is True
    (c8d1 / 'L8_summary.json').unlink()
    tool('gates_d3.py', *args2, check=1)
    r = json.loads((ev / 'gate5.json').read_text())
    assert r['gate_5_forest_certificate'] is False and r['checks']['c_masks']['passed'] is False and r['checks']['d_forests']['passed'] is False, r['checks']
    assert r['checks']['c_masks']['returncode'] == 2 and not sup.exists() and sup.with_name(sup.name + '.superseded').read_bytes() == old_sup
    assert not [p.name for p in ev.iterdir() if p.name.endswith('.tmp')], list(ev.iterdir())
    shutil.copy(ref / 'L8_summary.json', c8d1 / 'L8_summary.json')
    tool('gates_d3.py', *args2, check=0)
    assert json.loads(sup.read_text())['passed'] is True
    ok('gate5ab_provenance_and_correspondence_logic_with_the_certificate_and_the_binary_warning')


@register
def test_tool_zeros_and_determinism(td: Path) -> None:
    sys.path.insert(0, str(GEN3))
    import gates_d3 as gd
    stage_a = mini_stage(td / 'a')[0]
    stage_b = mini_stage(td / 'b')[0]
    ev = td / 'ev'
    tool('gates_d3.py', 'determinism', '--a', stage_a, '--b', stage_b, '--evidence', ev, check=0)
    flip_byte(stage_b / 'L8_power' / 'G4.txt')
    tool('gates_d3.py', 'determinism', '--a', stage_a, '--b', stage_b, '--evidence', ev, check=1)
    # gate 2 (c) on a miniature: free zeros = d=1 zeros on power-free classes; d=1 power zeros within d=2's
    inv = dict(free=[], power=[])
    for i in range(6):
        inv['free'].append(dict(id=i, power_subgraphs=int(i >= 3), status='exact-zero-kernel' if i in (1, 2) else 'finite-kernel'))
        inv['power'].append(dict(id=i, status='exact-zero-kernel' if i in (4, 5) else 'finite-kernel'))
    d = td / 'z'
    d.mkdir()
    (d / 'inventory_L8.json').write_text(json.dumps(inv))
    (d / 'exact_zero_L8.txt').write_text('3\n1 2 4\n')
    r = gd.zeros_check(d, d)
    assert r['errors'] == ['free zeros 2 differ from exact_zero_L8.txt on power-free classes (2; expected 2,511)'], r
    (d / 'exact_zero_L8.txt').write_text('3\n1 2 3\n')
    r = gd.zeros_check(d, d)
    assert any('d=1 power zeros are not d=2 power zeros' in e for e in r['errors']), r
    ok('A.4_determinism_gate_and_gate2c_zeros_logic')


FAKE_VERIFIER = ('import hashlib, sys, pathlib\n'
                 't = pathlib.Path(sys.argv[1]); pin = sys.argv[sys.argv.index("--pin") + 1]\n'
                 'sys.exit(0 if hashlib.sha256((t / "MANIFEST.json").read_bytes()).hexdigest() == pin else 1)\n')


def fake_h1_tree(src: Path, verifier: str = FAKE_VERIFIER, extra: dict | None = None) -> str:
    """A fake H1 tree with H1's checksum chain (S4-001): src/gen/verify_inventory.py (by default a verifier that checks
    sha256(MANIFEST.json) against --pin) and `extra` files, every file listed in SHA256SUMS, SHA256SUMS pinned by the
    MANIFEST's sha256sums_sha256, the src/ rows restated in gen_sources_sha256. Returns the MANIFEST's sha256 (the pin)."""
    files = {'src/gen/verify_inventory.py': verifier, 'src/gen/Makefile': 'all:\n', 'payload/L7_free.tar': 'x' * 100, **(extra or {})}
    for rel, text in files.items():
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(text)
    rows = ''.join(f'{c.sha256_file(src / rel)}  {rel}\n' for rel in sorted(files))
    (src / 'SHA256SUMS').write_text(rows)
    man = dict(schema='c8-inventory-d2-1', sha256sums_sha256=c.sha256_file(src / 'SHA256SUMS'),
               gen_sources_sha256={rel[4:]: c.sha256_file(src / rel) for rel in sorted(files) if rel.startswith('src/')})
    (src / 'MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')
    return c.sha256_file(src / 'MANIFEST.json')


@register
def test_tool_h1_copy(td: Path) -> None:
    """A.2 step 0 on a fake H1 tree whose own verifier checks sha256(MANIFEST.json) against --pin. S4-001: a copy whose
    code is not the pinned code (the verifier replaced, a module added next to it, in the source or in a reused copy) is
    refused before anything of it runs; gen3/run_d3.sh's verify step and `h1-auth --check` likewise."""
    src = td / 'src_tree'
    pin = fake_h1_tree(src)
    before = sorted((p.relative_to(src).as_posix(), p.stat().st_mtime_ns) for p in src.rglob('*'))
    store, ev = td / 'store/h1', td / 'ev'
    tool('gates_d3.py', 'h1-copy', '--source', src, '--store', store, '--pin', pin, '--evidence', ev, check=0)
    dest = store / pin[:12]
    assert (dest / 'payload/L7_free.tar').read_bytes() == b'x' * 100 and not list(store.glob('.*'))
    rec = json.loads((ev / 'h1_copy.json').read_text())
    assert rec['passed'] and rec['checks']['source_unchanged']['passed'] and Path(rec['dest']) == dest.resolve()
    assert sorted((p.relative_to(src).as_posix(), p.stat().st_mtime_ns) for p in src.rglob('*')) == before
    tool('gates_d3.py', 'h1-copy', '--source', src, '--store', store, '--pin', pin, '--evidence', ev, check=0)
    assert json.loads((ev / 'h1_copy.json').read_text())['checks']['copy']['note'].startswith('copy exists')
    tool('gates_d3.py', 'source-unchanged', '--source', src, '--before', ev / 'h1_source_listing_before.json',
         '--evidence', ev, check=0)
    (src / 'payload/L7_free.tar').write_bytes(b'y' * 100)    # the source changed after the intake
    tool('gates_d3.py', 'source-unchanged', '--source', src, '--before', ev / 'h1_source_listing_before.json',
         '--evidence', ev, check=1)
    tool('gates_d3.py', 'h1-copy', '--source', src, '--store', td / 'store2', '--pin', 'f' * 64, '--evidence', td / 'ev2', check=1)
    assert not (td / 'store2').exists()
    # S4-001: code that is not the pinned code never runs (each run would leave the marker)
    mark = td / 'ran'
    evil = f'import pathlib\npathlib.Path({str(mark)!r}).write_text("ran")\n'
    ver = dest / 'src/gen/verify_inventory.py'
    good = ver.read_bytes()
    for name, mutate, undo in (('reused_copy_verifier_replaced', lambda: ver.write_text(evil), lambda: ver.write_bytes(good)),
                               ('module_next_to_the_verifier', lambda: (dest / 'src/gen/hashlib.py').write_text(evil),
                                lambda: (dest / 'src/gen/hashlib.py').unlink())):
        mutate()
        cp = tool('gates_d3.py', 'h1-copy', '--source', src, '--store', store, '--pin', pin, '--evidence', td / f'ev_{name}', check=1)
        r = json.loads((td / f'ev_{name}' / 'h1_copy.json').read_text())
        assert not mark.exists() and r['checks']['h1_code_authenticated']['passed'] is False, (name, r['checks'])
        assert r['checks']['verify_inventory_copy']['passed'] is False and 'not run' in r['checks']['verify_inventory_copy']['note']
        undo()
    src2 = td / 'src_tree2'
    shutil.copytree(src, src2)
    (src2 / 'src/gen/verify_inventory.py').write_text(evil)    # the source's verifier replaced, its MANIFEST unchanged
    tool('gates_d3.py', 'h1-copy', '--source', src2, '--store', td / 'store3', '--pin', pin, '--evidence', td / 'ev_src2', check=1)
    assert not mark.exists() and (td / 'store3' / pin[:12]).is_dir()
    # gen3/run_d3.sh's verify step (the real step; every other step a test hook) and h1-auth --check
    steps = ('extract', 'builders', 'probe', 'regen', 'gate1b', 'gate2', 'gate3', 'gate4', 'gate5', 'gate7', 'determinism',
             'publish', 'verify_d3', 'source')
    env = dict(os.environ, C8_SITE='fake', C8_GEN3_TEST_HOOKS='1', **{f'C8_GEN3_STEP_{s}': 'true' for s in steps})

    def run_d3(tree, name):
        return subprocess.run(['bash', str(GEN3 / 'run_d3.sh'), '--h1', str(tree), '--pin', pin, '--d2', str(td / 'd2'),
                               '--evidence', str(td / f'ev_{name}'), '--work', str(td / f'w_{name}'), '--target', str(td / f't_{name}'),
                               '--source', str(src), '--source-before', str(td / 'b.json')], capture_output=True, text=True, env=env)
    cp = run_d3(dest, 'run_d3_ok')
    assert cp.returncode == 0 and 'step verify: exit 0' in cp.stdout, (cp.returncode, cp.stderr[-800:])
    assert json.loads((td / 'ev_run_d3_ok/h1_code_auth.json').read_text())['passed'] is True
    snap = td / 'w_run_d3_ok/h1gen/src'
    assert sorted(x.name for x in snap.iterdir()) == ['Makefile', 'verify_inventory.py']
    chk = ['h1-auth', '--tree', dest, '--pin', pin, '--snapshot', snap, '--check', '--evidence', td / 'ev_chk']
    tool('gates_d3.py', *chk, check=0)
    (snap / 'extra.py').write_text('x')
    tool('gates_d3.py', *chk, check=1)
    (snap / 'extra.py').unlink()
    (snap / 'Makefile').write_text('all:\n\techo changed\n')
    tool('gates_d3.py', *chk, check=1)
    cp = run_d3(src2, 'run_d3_evil')
    assert cp.returncode != 0 and not mark.exists() and 'step verify: start' in cp.stdout and 'step extract' not in cp.stdout, cp.stdout[-800:]
    assert not (td / 'w_run_d3_evil/h1gen/src').exists()
    (dest / 'MANIFEST.json').write_text('{}\n')                 # a damaged copy is refused (its MANIFEST is not the pin)
    tool('gates_d3.py', 'h1-copy', '--source', src, '--store', store, '--pin', pin, '--evidence', td / 'ev3', check=1)
    ok('A-INV-6_h1_copy_staging_rename_verifier_and_source_listing')


def gate1a_record(td: Path, name: str, machine: str, job: str | None, site: str | None, loops=(2, 3, 4, 5, 6, 7),
                  fail: str | None = None) -> dict:
    """gates_d3.finish() run in-process on synthetic checks, with the platform and the environment patched: the
    gate1a.json that gate 1(a) would write on that machine."""
    from unittest import mock
    sys.path.insert(0, str(GEN3))
    import gates_d3 as gd
    checks = {k: {'passed': True} for k in ('frozen_d2_pin', 'c7d3_reference_set', 'determinism_threads',
                                             'idempotence_second_pass', 'byte_reproduction_c7d3',
                                             'body_equals_d2_except_magic_and_rate_line', 'rate_audit_minimum_rates')}
    checks['byte_reproduction_c7d3'].update(identical=3512, compared=3512)
    if fail:
        checks[fail]['passed'] = False
    binary = td / 'regenerate_rates'
    binary.write_bytes(b'binary')
    ev = td / f'ev_{name}'
    env = {k: v for k, v in os.environ.items() if k not in ('SLURM_JOB_ID', 'C8_SITE')}
    env.update({k: v for k, v in (('SLURM_JOB_ID', job), ('C8_SITE', site)) if v is not None})
    from contextlib import redirect_stdout
    with mock.patch.object(gd.platform, 'machine', return_value=machine), mock.patch.dict(os.environ, env, clear=True), \
            redirect_stdout(io.StringIO()):
        rc = gd.finish(argparse.Namespace(d2=str(td)), ev, checks, {}, time.time(), binary, list(loops))
    rec = json.loads((ev / 'gate1a.json').read_text())
    assert rc == (1 if fail else 0) and rec['passed'] is (not fail), (name, rc, rec['passed'])
    return rec


@register
def test_tool_gate1a_platform_rule(td: Path) -> None:
    """A-INV-2(a) is an Expanse x86-64 gate (PLAN A.3 1(a)): gate1a.json's a_inv_2a is true only for a full pass with
    machine x86_64, a numeric SLURM_JOB_ID and C8_SITE=expanse; anything else is run_class "rehearsal"."""
    r = gate1a_record(td, 'expanse', 'x86_64', '41234567', 'expanse')
    assert r['a_inv_2a'] is True and r['run_class'] == 'expanse' and not r['not_expanse_because'], r
    assert r['environment']['site'] == 'expanse' and r['environment']['slurm_job_id'] == '41234567'
    for name, machine, job, site, why in (('mac', 'arm64', 'macdry', 'fake', 'machine'),
                                          ('arm64_real_job', 'arm64', '41234567', 'expanse', 'machine'),
                                          ('no_job', 'x86_64', None, 'expanse', 'SLURM_JOB_ID'),
                                          ('fake_job', 'x86_64', 'macdry', 'expanse', 'SLURM_JOB_ID'),
                                          ('other_site', 'x86_64', '41234567', 'symmetry', 'C8_SITE'),
                                          ('no_site', 'x86_64', '41234567', None, 'C8_SITE')):
        r = gate1a_record(td, name, machine, job, site)
        assert r['passed'] is True and r['a_inv_2a'] is False and r['run_class'] == 'rehearsal', (name, r['a_inv_2a'])
        assert any(x.startswith(why) for x in r['not_expanse_because']), (name, r['not_expanse_because'])
    r = gate1a_record(td, 'subset', 'x86_64', '41234567', 'expanse', loops=(2, 3))
    assert r['a_inv_2a'] is False and r['run_class'] == 'expanse' and r['scope'].startswith('subset')
    r = gate1a_record(td, 'failed', 'x86_64', '41234567', 'expanse', fail='byte_reproduction_c7d3')
    assert r['a_inv_2a'] is False
    ok('A-INV-2a_only_on_expanse_x86_64_else_rehearsal', cases=10)


@register
def test_tool_summary_gen_d3_0(td: Path) -> None:
    """J-GEN-D3-0's summary: passed (G1a) only for an Expanse x86-64 full pass of gate 1(a) plus A-INV-1's sanitizer
    part; an off-Expanse run is a rehearsal that exits 0 only with --rehearsal and still says passed false."""
    sys.path.insert(0, str(GEN3))
    import gates_d3 as gd
    good = gate1a_record(td, 'expanse', 'x86_64', '41234567', 'expanse')
    mac = gate1a_record(td, 'mac', 'arm64', 'macdry', 'fake')
    san = dict(status='passed', sanitize=True, tmpdir='/scratch/x/job_1/tmp', tests=[{'test': n} for n in gd.SANITIZE_NEED])

    def run(name, g1a, s, rehearsal, rc):
        ev = td / f'sum_{name}'
        ev.mkdir()
        (ev / 'gate1a.json').write_text(json.dumps(g1a))
        (ev / 'test_gen3_sanitize.json').write_text(json.dumps(s))
        cp = tool('gates_d3.py', 'summary-gen-d3-0', '--evidence', ev, *(['--rehearsal'] if rehearsal else []), check=rc)
        return json.loads((ev / 'jgen_d3_0.json').read_text()), cp.stdout
    r, out = run('expanse', good, san, False, 0)
    assert r['passed'] is True and r['a_inv_2a'] is True and r['run_class'] == 'expanse' and 'PASSED: G1a' in out, r
    assert r['sanitizer_tmpdir'] == '/scratch/x/job_1/tmp'
    r, out = run('mac', mac, san, False, 1)
    assert r['passed'] is False and r['a_inv_2a'] is False and r['rehearsal'] is True and 'FAILED' in out, r
    r, out = run('mac_rehearsal', mac, san, True, 0)
    assert r['passed'] is False and r['checks_passed'] is True and 'REHEARSAL' in out and 'NOT G1a' in out, r
    bad = dict(san, tests=san['tests'][:-1])
    r, _ = run('missing_test', good, bad, False, 1)
    assert r['passed'] is False and r['sanitizer_tests_missing'] == [gd.SANITIZE_NEED[-1]], r
    run('missing_test_rehearsal', mac, bad, True, 1)
    run('not_sanitized', good, dict(san, sanitize=False), False, 1)
    sub = gate1a_record(td, 'subset', 'x86_64', '41234567', 'expanse', loops=(2, 3))
    run('subset_rehearsal', sub, san, True, 1)
    # a gate1a.json written before the platform rule (a_inv_2a true on arm64) is not G1a either
    old = dict(mac, a_inv_2a=True, run_class=None, schema='c8-d3-gate1a-1')
    old['environment'] = {k: v for k, v in mac['environment'].items() if k != 'site'}
    r, _ = run('pre_rule', old, san, False, 1)
    assert r['passed'] is False and any('not an Expanse x86-64 run' in e for e in r['a_inv_2a_errors']), r
    ok('J-GEN-D3-0_summary_G1a_only_on_expanse_rehearsal_explicit', cases=8)


@register
def test_tool_report(td: Path) -> None:
    """A.5's gate record: assembled only when every gate, gate 1(a) (a full pass on Expanse x86-64) and verify_d3
    passed; written once."""
    ev = td / 'ev'
    (ev / 'gates').mkdir(parents=True)
    for g in ('gate1b', 'gate2', 'gate3', 'gate4', 'gate7', 'determinism'):
        (ev / 'gates' / f'{g}.json').write_text(json.dumps(dict(passed=True, slurm_job_id='1', host='h', cpu='c', checks={'x': {'passed': True}})))
    (ev / 'gates/gate5.json').write_text(json.dumps(dict(passed=True, gate_5_forest_certificate=True, checks={})))
    pin = 'd' * 64
    (ev / 'MANIFEST_d3.sha256').write_text(pin + '\n')
    (ev / 'verify_d3.json').write_text(json.dumps(dict(passed=True, pin=pin)))
    g1a = td / 'gate1a.json'
    g1a.write_text(json.dumps(gate1a_record(td, 'expanse', 'x86_64', '41234567', 'expanse')))
    out = td / 'assembly/H1_gates/inventory8_d2_46341a3c0f11_C63d_gates.json'
    args = ['report', '--evidence', ev, '--gate1a', g1a, '--h1-pin', 'e' * 64, '--commit', 'abc', '--output', out]
    (ev / 'gates/gate3.json').write_text(json.dumps(dict(passed=False)))
    tool('gates_d3.py', *args, check=1)
    assert not out.exists()
    (ev / 'gates/gate3.json').write_text(json.dumps(dict(passed=True)))
    # a rehearsal gate1a.json is refused, also one that claims a_inv_2a on arm64 (the record shape written before the
    # platform rule, as the committed Mac dry run's)
    rehearsals = [('mac', gate1a_record(td, 'mac', 'arm64', 'macdry', 'fake'))]
    pre_rule = dict(rehearsals[0][1], a_inv_2a=True, schema='c8-d3-gate1a-1')
    pre_rule.pop('run_class')
    rehearsals.append(('pre_rule', pre_rule))
    rehearsals.append(('no_site', gate1a_record(td, 'no_site', 'x86_64', '41234567', None)))
    dry = ROOT / 'benchmarks/expanse_2026-10-c8/stage_1a/mac_jgen_d3_0_dryrun/gate1a.json'
    if dry.is_file():
        rehearsals.append(('committed_mac_dry_run', json.loads(dry.read_text())))
    for name, rec in rehearsals:
        f = td / f'gate1a_{name}.json'
        f.write_text(json.dumps(rec))
        cp = tool('gates_d3.py', *[f if x == g1a else x for x in args], check=1)
        assert 'not an Expanse x86-64 run' in cp.stderr and not out.exists(), (name, cp.stderr[-600:])
    cp = tool('gates_d3.py', *args, check=0)
    rec = json.loads(out.read_text())
    assert rec['manifest_d3_sha256'] == pin and rec['handoff_c63d']['gate_5_forest_certificate'] is True
    assert rec['handoff_c63d']['pin_recorded'] == 'e' * 64 and rec['gates']['6'].startswith('pending')
    assert rec['gate1a']['machine'] == 'x86_64' and rec['gate1a']['run_class'] == 'expanse' and rec['gate1a']['job'] == '41234567'
    assert tool('gates_d3.py', *args).returncode == 2, 'a second report must refuse'
    ok('A.5_gate_record_only_after_every_gate_written_once', rehearsals_refused=len(rehearsals))


def scratch_inputs_pkg(td: Path) -> Path:
    """A scratch package for `make inputs-l8` (tools/, gen3/, the Makefile, inputs/ as committed); every write it might
    make stays inside td."""
    pkg = td / 'pkg'
    (pkg / 'tools').mkdir(parents=True)
    for f in (ROOT / 'tools').iterdir():
        if f.is_file() and f.suffix in ('.py', '.json'):
            shutil.copy2(f, pkg / 'tools' / f.name)
    (pkg / 'gen3').mkdir()
    for f in GEN3.iterdir():
        if f.is_file() and f.suffix in ('.py', '.sh'):
            shutil.copy2(f, pkg / 'gen3' / f.name)
    shutil.copy2(ROOT / 'Makefile', pkg / 'Makefile')
    def link_or_copy(src, dst):   # a hard link, or a copy across filesystems (an Expanse work copy and node-local tmp)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    shutil.copytree(ROOT / 'inputs', pkg / 'inputs', copy_function=link_or_copy,
                    ignore=shutil.ignore_patterns('free_L8.pack', 'power_L8.pack'))
    return pkg


SPY = r'''
import json, os, sys
sys.dont_write_bytecode = True
tools, payload, log = sys.argv[1], os.path.realpath(sys.argv[2]), sys.argv[3]
seen = []
def hook(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        p = os.path.realpath(os.fsdecode(args[0]))
        if p.startswith(os.path.join(payload, 'payload') + os.sep):
            seen.append(p)
    elif event == 'subprocess.Popen':
        seen.append('PROC ' + ' '.join(map(str, args[1]))[:300])
sys.addaudithook(hook)
sys.path.insert(0, tools)
import prepare_inputs as pi
rc = pi.main(sys.argv[4:])
json.dump(seen, open(log, 'w'))
sys.exit(rc)
'''


@register
def test_tool_inputs_l8_refusals(td: Path) -> None:
    """`make inputs-l8` (A.2 step 6, A-INV-5; deferred to Stage 2b by the Stage-1a host notes): refuses without D3PIN
    (the Makefile and the tool), and on a wrong pin runs verify_d3.py --pin, which fails, before opening any payload
    member: no tar opened by the tool, nothing written to inputs/ or the store."""
    stage, gates, side, audits = mini_stage(td)
    target = td / 'pub' / 'd3_payload'
    target.parent.mkdir()
    tool('publish_d3.py', '--stage', stage, '--gates', gates, '--side', side, '--audits', audits, '--target', target,
         '--h1-pin', 'a' * 64, '--commit', 'test', '--tar', 'python', check=0)
    pin = c.sha256_file(target / 'MANIFEST_d3.json')
    pkg = scratch_inputs_pkg(td)
    store = td / 'store'
    before = sorted((p.relative_to(pkg).as_posix(), p.stat().st_size, p.stat().st_mtime_ns) for p in pkg.rglob('*'))
    env = {k: v for k, v in os.environ.items() if k not in ('C8_INPUTS', 'PYTHONPYCACHEPREFIX')}
    # no D3PIN: the Makefile refuses before running anything; the tool refuses too (exit 2)
    cp = subprocess.run(['make', '-s', '-C', str(pkg), 'inputs-l8', f'D3PAYLOAD={target}', f'STORE={store}',
                         f'PYTHON={sys.executable}'], capture_output=True, text=True, env=env)
    assert cp.returncode == 2 and 'D3PIN=' in cp.stderr and 'nothing was read' in cp.stderr, (cp.returncode, cp.stderr)
    log0 = td / 'spy0.json'
    cp = subprocess.run([sys.executable, '-B', '-c', SPY, str(pkg / 'tools'), str(target), str(log0), 'l8',
                         '--d3payload', str(target), '--store', str(store)], capture_output=True, text=True, env=env)
    assert cp.returncode == 2 and 'D3PIN' in cp.stderr and json.loads(log0.read_text()) == [], (cp.returncode, cp.stderr)
    # a malformed and a wrong pin: verify_d3.py runs first and fails at step 1; no member read, nothing written
    for name, bad in (('wrong', 'b' * 64), ('malformed', 'xyz')):
        log1 = td / f'spy_{name}.json'
        cp = subprocess.run([sys.executable, '-B', '-c', SPY, str(pkg / 'tools'), str(target), str(log1), 'l8',
                             '--d3payload', str(target), '--d3pin', bad, '--store', str(store)],
                            capture_output=True, text=True, env=env)
        seen = json.loads(log1.read_text())
        opened = [x for x in seen if not x.startswith('PROC ')]
        procs = [x for x in seen if x.startswith('PROC ')]
        if name == 'wrong':
            assert cp.returncode == 1 and 'verify_d3.py --pin' in cp.stderr and '1_external_pin: FAIL' in cp.stderr \
                and 'no member was read' in cp.stderr, cp.stderr[-800:]
            assert len(procs) == 1 and 'verify_d3.py' in procs[0], procs
        else:
            assert cp.returncode == 1 and 'is not a sha256' in cp.stderr and not procs, (cp.stderr[-600:], procs)
        assert not opened, f'{name} pin: the tool opened payload members {opened[:3]}'
    # the same through make with a wrong pin
    cp = subprocess.run(['make', '-s', '-C', str(pkg), 'inputs-l8', f'D3PAYLOAD={target}', f'D3PIN={"c" * 64}',
                         f'STORE={store}', f'PYTHON={sys.executable}'], capture_output=True, text=True, env=env)
    assert cp.returncode != 0 and '1_external_pin: FAIL' in cp.stderr, cp.stderr[-600:]
    # a gate record whose pin differs from D3PIN is refused before verify_d3.py runs
    gr = td / 'gate_record.json'
    gr.write_text(json.dumps(dict(schema='c8-d3-h1-gates-1', manifest_d3_sha256='d' * 64, h1_manifest_sha256='a' * 64)))
    log2 = td / 'spy_gr.json'
    cp = subprocess.run([sys.executable, '-B', '-c', SPY, str(pkg / 'tools'), str(target), str(log2), 'l8',
                         '--d3payload', str(target), '--d3pin', pin, '--store', str(store), '--gate-record', str(gr),
                         '--fixture-h1-pin', 'a' * 64], capture_output=True, text=True, env=env)
    assert cp.returncode == 1 and 'the gate record pins' in cp.stderr and json.loads(log2.read_text()) == [], cp.stderr[-600:]
    after = sorted((p.relative_to(pkg).as_posix(), p.stat().st_size, p.stat().st_mtime_ns) for p in pkg.rglob('*'))
    assert after == before, 'a refused make inputs-l8 changed the package'
    assert not store.exists(), 'a refused make inputs-l8 created the store'
    ok('inputs_l8_refuses_without_D3PIN_and_on_a_wrong_pin_before_reading_a_member', pin_checked_by='verify_d3.py step 1')


@register
def test_tool_gate6_addendum(td: Path) -> None:
    """The gate-6 addendum (the A.5 gate record is written once): only for a passed gate6.json made on the given inputs
    manifest whose d=3 and H1 pins equal the gate record's; written once; refuses C62d's trees."""
    man = td / 'manifest.json'
    man.write_text(json.dumps(dict(d3_payload_manifest_sha256='d' * 64, inventory8_d2_manifest_sha256='e' * 64)))
    g6 = td / 'gate6.json'
    rec = dict(schema='c8-d3-gate-1', gate='6 pack identity (A.3 6, A-INV-2(b); Stage 2b)', passed=True,
               inputs_manifest_sha256=c.sha256_file(man), slurm_job_id='54670000', host='exp-1-1', cpu='AMD',
               packs={}, l8_packs={},
               checks=dict(a_c7d3_rows=dict(passed=True, members=3511), b_c7d3_payload_digest=dict(passed=True, digest='f' * 64),
                           c_l3_l6_packs_a6ce987=dict(passed=True), d_l7_members_d3=dict(passed=True, new_members={'free': 143, 'power': 119}),
                           e_l7_totals=dict(passed=True, l7={'free': 2441, 'power': 709})))
    g6.write_text(json.dumps(rec))
    gr = td / 'H1_gates/inventory8_d2_eeeeeeeeeeee_C63d_gates.json'
    gr.parent.mkdir()
    gr.write_text(json.dumps(dict(schema='c8-d3-h1-gates-1', manifest_d3_sha256='d' * 64, h1_manifest_sha256='e' * 64,
                                  gates={'6': 'pending (Stage 2b, with the C8 packs)'})))
    out = gr.parent / 'inventory8_d2_eeeeeeeeeeee_C63d_gates_addendum_gate6.json'
    args = ['addendum', '--gate6', g6, '--gate-record', gr, '--inputs-manifest', man, '--commit', 'abc1234', '--output', out]
    keep = gr.read_bytes()
    g6.write_text(json.dumps(dict(rec, passed=False)))
    tool('gates_d3.py', *args, check=1)
    g6.write_text(json.dumps(dict(rec, inputs_manifest_sha256='0' * 64)))
    tool('gates_d3.py', *args, check=1)
    g6.write_text(json.dumps(rec))
    gr.write_text(json.dumps(dict(json.loads(keep), manifest_d3_sha256='9' * 64)))
    tool('gates_d3.py', *args, check=1)
    gr.write_bytes(keep)
    assert not out.exists()
    tool('gates_d3.py', *args, check=0)
    a = json.loads(out.read_text())
    assert a['gates'] == {'6': True} and a['addendum_to']['sha256'] == c.sha256_bytes(keep) and a['jobs'] == ['54670000']
    assert a['handoff_c63d_update'] == {'gates_1_7': {'6': True}} and gr.read_bytes() == keep
    assert tool('gates_d3.py', *args).returncode == 2, 'a second addendum must refuse'
    bad = td / 'x/LRI_C8_shared/inventory/addendum.json'
    assert tool('gates_d3.py', *[bad if x == out else x for x in args]).returncode == 2
    ok('gate6_addendum_next_to_the_written_once_gate_record')


def report_back_fixture(td: Path) -> dict:
    """A miniature LRI_C8_shared: C62d's HANDOFF (handoff_inventory.py's json.dumps(indent=1) text) with the c63d block
    as the A.5 gate record wrote it, a DECISIONS.md ending in the acknowledgment log, the gate record and its gate-6
    addendum."""
    sh = td / 'LRI_C8_shared'
    (sh / 'inventory').mkdir(parents=True)
    (sh / 'assembly/H1_gates').mkdir(parents=True)
    h1, d3 = 'e' * 64, 'd' * 64
    gates = {'1a': True, '1b': True, '2': True, '3': True, '4': True, '5': True, '6': 'pending (Stage 2b, with the C8 packs)',
             '7': True}
    gr = dict(schema='c8-d3-h1-gates-1', h1='inventory8_d2', h1_manifest_sha256=h1, manifest_d3_sha256=d3,
              package='LRI_C8_D3_HPC', commit='4540d525be91', gates=dict(gates, determinism=True),
              gate_5_forest_certificate=True, jobs=['54666138'], hosts=['exp-1-16'], cpus=['AMD EPYC 7742 64-Core Processor'],
              gate1a=dict(identical=3512, job='54661738', host='exp-1-24', machine='x86_64', run_class='expanse'),
              handoff_c63d=dict(pin_recorded=h1, gates_1_7=gates, gate_5_forest_certificate=True, manifest_d3_sha256=d3))
    grp = sh / 'assembly/H1_gates/inventory8_d2_eeeeeeeeeeee_C63d_gates.json'
    grp.write_text(json.dumps(gr, indent=1) + '\n')
    ad = dict(schema='c8-d3-h1-gates-addendum-1', h1='inventory8_d2', h1_manifest_sha256=h1, manifest_d3_sha256=d3,
              package='LRI_C8_D3_HPC', commit='f499d5a42672',
              addendum_to=dict(file=grp.name, sha256=c.sha256_file(grp), note='x'), gates={'6': True},
              gate6=dict(a_c7d3_rows=True, b_c7d3_payload_digest=True, c_l3_l6_packs_a6ce987=True, d_l7_members_d3=True,
                         e_l7_totals=True),
              gate6_summary=dict(c7d3_members=3511, c7d3_payload_digest='b' * 64, new_l7_members={'free': 143, 'power': 119},
                                 l7_totals={'free': 2441, 'power': 709}),
              jobs=['54676856'], hosts=['exp-9-55'], handoff_c63d_update={'gates_1_7': {'6': True}})
    adp = sh / 'assembly/H1_gates/inventory8_d2_eeeeeeeeeeee_C63d_gates_addendum_gate6.json'
    adp.write_text(json.dumps(ad, indent=1) + '\n')
    h = dict(schema='c8-inventory-d2-handoff-1', handoff='H1', manifest_sha256=h1, manifest_md5='a' * 32,
             copies={'/x/inventory8_d2': True}, counts={'L8_free': {'finite-kernel': 16798}}, notes=['n1', 'n2'],
             c63d=dict(pin_recorded=h1, gates_1_7=dict(gates), gate_5_forest_certificate=True, note='C63d records here'))
    hp = sh / 'inventory/HANDOFF_inventory8_d2.json'
    hp.write_text(json.dumps(h, indent=1) + '\n')
    hp.chmod(0o640)
    dp = sh / 'inventory/DECISIONS.md'
    dp.write_text('# DECISIONS\n\n## A. Agreed\n\n| Id | Decision |\n|---|---|\n| A3 | H1 |\n\n'
                  '## Acknowledgment log (append-only; C63d may append here)\n\n| Date | Item | Answer | Recorded by |\n'
                  '|---|---|---|---|\n| 2026-10-04 | A3 report-back | AGREED (item 2): C63d writes ... | C63d |\n')
    h1c = td / 'h1_copy.json'
    h1c.write_text(json.dumps(dict(passed=True, pin=h1, slurm_job_id='54661740', host='exp-1-24',
                                   checks=dict(verify_inventory_copy=dict(passed=True), source_unchanged=dict(passed=True)))))
    return dict(sh=sh, gr=grp, ad=adp, hp=hp, dp=dp, h=h, h1c=h1c, d3=d3)


@register
def test_tool_report_back(td: Path) -> None:
    """The A.5 report-back (DECISIONS A3; A.2 step 6): handoff-gate6 changes exactly c63d.gates_1_7["6"] of C62d's
    HANDOFF (and refuses a mismatched record, another file, a symlink, a non-canonical text), decisions-ack appends
    exactly one log line carrying the d3 pin (only after the HANDOFF holds gate 6; refuses a log that is not the last
    section), note writes the NOTE once in assembly/ (only after both); every subcommand is idempotent and --dry-run
    writes nothing."""
    f = report_back_fixture(td)
    hp, dp, gr, ad = f['hp'], f['dp'], f['gr'], f['ad']
    rec = ['--gate-record', gr, '--addendum', ad]
    H = lambda ev, *x: ['handoff-gate6', '--handoff', hp, *rec, '--evidence', td / ev, *x]  # noqa: E731
    h0, d0 = hp.read_bytes(), dp.read_bytes()

    def unchanged():
        assert hp.read_bytes() == h0 and dp.read_bytes() == d0
        assert not [p.name for p in hp.parent.iterdir() if p.name.startswith('.')], 'a temporary file was left'
    # refusals: another file name, a symlink, a mismatched addendum or HANDOFF, a non-canonical text
    other = hp.with_name('HANDOFF_other.json')
    other.write_bytes(h0)
    tool('gates_d3.py', *[other if x == hp else x for x in H('e0')], check=2)
    link = td / 'LRI_C8_shared/inventory_link'
    link.symlink_to(hp.parent)
    tool('gates_d3.py', *[link / hp.name if x == hp else x for x in H('e0')], check=2)
    (td / 'elsewhere').mkdir()
    (td / 'elsewhere' / hp.name).symlink_to(hp)
    tool('gates_d3.py', *[td / 'elsewhere' / hp.name if x == hp else x for x in H('e0')], check=2)
    (td / 'y/LRI_C8_shared/inventory').mkdir(parents=True)
    (td / 'y/LRI_C8_shared/inventory' / hp.name).symlink_to(hp)
    cp = tool('gates_d3.py', *[td / 'y/LRI_C8_shared/inventory' / hp.name if x == hp else x for x in H('e0')], check=2)
    assert 'not a regular file' in cp.stderr, cp.stderr
    keep_ad = ad.read_bytes()
    for k, v in (('addendum_to', dict(file=gr.name, sha256='0' * 64)), ('manifest_d3_sha256', '9' * 64),
                 ('gate6', dict(json.loads(keep_ad)['gate6'], e_l7_totals=False))):
        ad.write_text(json.dumps(dict(json.loads(keep_ad), **{k: v}), indent=1) + '\n')
        tool('gates_d3.py', *H('e0'), check=1)
    ad.write_bytes(keep_ad)
    for mutate in (lambda h: h.update(manifest_sha256='1' * 64), lambda h: h['c63d']['gates_1_7'].update({'3': False}),
                   lambda h: h['c63d'].update(gate_5_forest_certificate=False)):
        h = json.loads(h0)
        mutate(h)
        hp.write_text(json.dumps(h, indent=1) + '\n')
        tool('gates_d3.py', *H('e0'), check=1)
    hp.write_text(json.dumps(json.loads(h0), indent=2) + '\n')
    cp = tool('gates_d3.py', *H('e0'), check=1)
    assert 'json.dumps(indent=1)' in cp.stderr, cp.stderr
    hp.write_bytes(h0)
    hp.chmod(0o640)
    other.unlink()
    tool('gates_d3.py', *H('e0', '--dry-run'), check=0)
    # decisions-ack and note refuse before the HANDOFF holds gate 6
    A = lambda ev, *x: ['decisions-ack', '--decisions', dp, '--handoff', hp, *rec, '--evidence', td / ev,  # noqa: E731
                        '--date', '2026-10-05', *x]
    note = f['sh'] / 'assembly/NOTE_C63d_to_C62d_2026-10-05.md'
    N = lambda *x: ['note', '--handoff', hp, '--decisions', dp, *rec, '--payload-path', '$C8_STORE/d3_payload/eeeeeeeeeeee',  # noqa: E731
                    '--h1-copy', f['h1c'], '--output', note, *x]
    tool('gates_d3.py', *A('e1'), check=1)
    tool('gates_d3.py', *N(), check=1)
    assert not (td / 'e0').exists() and not (td / 'e1').exists() and not note.exists()
    unchanged()
    # handoff-gate6: exactly one value changes; the old bytes are kept; the mode is kept; a second run writes nothing
    cp = tool('gates_d3.py', *H('e2'), check=0)
    after = hp.read_bytes()
    h_new = json.loads(after)
    want = json.loads(h0)
    want['c63d']['gates_1_7']['6'] = True
    assert h_new == want and list(h_new['c63d']['gates_1_7']) == list(want['c63d']['gates_1_7'])
    assert after == (json.dumps(want, indent=1) + '\n').encode() and (hp.stat().st_mode & 0o777) == 0o640
    r = json.loads((td / 'e2/handoff_gate6.json').read_text())
    assert (td / 'e2/HANDOFF_inventory8_d2.before.json').read_bytes() == h0
    assert (r['sha256_before'], r['sha256_after']) == (c.sha256_bytes(h0), c.sha256_bytes(after)) and len(r['changed']) == 1
    assert tool('gates_d3.py', *H('e2')).returncode == 2, 'one record per evidence directory'
    cp = tool('gates_d3.py', *H('e3'), check=0)
    assert 'already recorded' in cp.stdout and hp.read_bytes() == after and not (td / 'e3').exists()
    # decisions-ack: refuses a log that is not the last section or has no header; appends one line; idempotent
    for bad in (d0 + b'\n## Later section\n\n| x |\n', d0.replace(b'## Acknowledgment log', b'## Ack log')):
        dp.write_bytes(bad)
        tool('gates_d3.py', *A('e4'), check=1)
    dp.write_bytes(d0)
    tool('gates_d3.py', *N(), check=1)
    tool('gates_d3.py', *A('e4', '--dry-run'), check=0)
    assert dp.read_bytes() == d0
    tool('gates_d3.py', *A('e4'), check=0)
    d1 = dp.read_bytes()
    new_line = d1[len(d0):].decode()
    assert d1.startswith(d0) and new_line.count('\n') == 1 and new_line.endswith('| C63d |\n'), new_line
    assert f['d3'] in new_line and new_line.startswith('| 2026-10-05 | H1 gates 1–7 (A.5)') and '54661738' in new_line
    assert json.loads((td / 'e4/decisions_ack.json').read_text())['sha256_after'] == c.sha256_bytes(d1)
    cp = tool('gates_d3.py', *A('e5'), check=0)
    assert 'already logged' in cp.stdout and dp.read_bytes() == d1
    # note: only in assembly/ under its name pattern; written once; states the pins and the records
    for bad in (f['sh'] / 'inventory/NOTE_C63d_to_C62d_2026-10-05.md', f['sh'] / 'assembly/NOTE_x.md',
                td / 'NOTE_C63d_to_C62d_2026-10-05.md'):
        tool('gates_d3.py', *[bad if x == note else x for x in N()], check=2)
        assert not bad.exists()
    tool('gates_d3.py', *N('--dry-run'), check=0)
    assert not note.exists()
    h1c_ok = f['h1c'].read_bytes()
    f['h1c'].write_text(json.dumps(dict(json.loads(h1c_ok), checks=dict(verify_inventory_copy=dict(passed=True)))))
    tool('gates_d3.py', *N(), check=1)
    f['h1c'].write_bytes(h1c_ok)
    tool('gates_d3.py', *N(), check=0)
    t = note.read_text()
    for s in (f['d3'], 'e' * 64, c.sha256_file(gr), c.sha256_file(ad), '54661740', '54666138', '54676856', '3,512',
              'line of 2026-10-05', '143 + 119'):
        assert s in t, s
    assert tool('gates_d3.py', *N()).returncode == 2, 'a NOTE is written once'
    assert hp.read_bytes() == after and dp.read_bytes() == d1
    assert not [p.name for p in hp.parent.iterdir() if p.name.startswith('.')]
    ok('A.5_report_back_handoff_gate6_one_value_decisions_one_line_note_once_idempotent')


@register
def test_tool_report_back_concurrent_owner_writes(td: Path) -> None:
    """S4-004: C62d's writers honour no lock of ours. A concurrent write by the owner, injected in-process at the tool's
    own write (os.write / os.rename / os.replace / os.link of the shared file, whichever the tool uses), is never lost:
    decisions-ack keeps the owner's line (its one append lands once; the tool refuses, exit 1, the file not being old +
    line); handoff-gate6 refuses an owner edit made before its swap (the edit stays in place) and never overwrites a
    HANDOFF recreated during its brief window (the bytes taken aside are kept and named). Temporary directories only."""
    from contextlib import redirect_stderr, redirect_stdout
    from unittest import mock
    sys.path.insert(0, str(GEN3))
    import gates_d3 as gd
    real = {k: getattr(os, k) for k in ('write', 'rename', 'replace', 'link')}

    def run(argv, inject):
        """gates_d3.main(argv) in-process; inject(name, args) runs before every patched call (then the real one)."""
        def wrap(name):
            def f(*x):
                inject(name, x)
                return real[name](*x)
            return f
        with mock.patch.multiple(gd.os, **{k: wrap(k) for k in real}), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            try:
                return gd.main([str(x) for x in argv])
            except SystemExit as e:
                return e.code
    # decisions-ack: the owner appends a line just before the tool's own write to DECISIONS.md
    f = report_back_fixture(td / 'a')
    hp, dp, rec = f['hp'], f['dp'], ['--gate-record', f['gr'], '--addendum', f['ad']]
    tool('gates_d3.py', 'handoff-gate6', '--handoff', hp, *rec, '--evidence', td / 'a_e1', check=0)
    d0, owner = dp.read_bytes(), b'| 2026-10-06 | C62d item | written by C62d meanwhile | C62d |\n'
    done = []

    def owner_append(name, x):
        hit = (name == 'write' and f['d3'].encode() in bytes(x[1])) or (name in ('rename', 'replace') and Path(x[-1]) == dp)
        if hit and not done:
            done.append(name)
            with open(dp, 'ab') as fh:
                fh.write(owner)
    rc = run(['decisions-ack', '--decisions', dp, '--handoff', hp, *rec, '--evidence', td / 'a_e2', '--date', '2026-10-06'], owner_append)
    d1 = dp.read_bytes()
    assert done and owner in d1, ('the owner\'s concurrent line was lost', rc, done)
    assert rc == 1 and d1.startswith(d0) and d1.count(f['d3'].encode()) == 1 and d1.count(owner) == 1, (rc, d1[len(d0):])
    # handoff-gate6: the owner edits the HANDOFF just before the tool's swap
    g = report_back_fixture(td / 'b')
    hp, rec = g['hp'], ['--gate-record', g['gr'], '--addendum', g['ad']]
    h0 = hp.read_bytes()
    edited = h0.replace(b'"n2"', b'"n2 (C62d, meanwhile)"')
    done.clear()

    def owner_edit(name, x):
        if name in ('rename', 'replace') and Path(x[0 if name == 'rename' else 1]) == hp and not done:
            done.append(name)
            hp.write_bytes(edited)
    rc = run(['handoff-gate6', '--handoff', hp, *rec, '--evidence', td / 'b_e1'], owner_edit)
    assert done and hp.read_bytes() == edited, ('the owner\'s concurrent edit was overwritten', rc, done)
    assert rc == 1 and not [p.name for p in hp.parent.iterdir() if p.name.startswith('.')]
    # handoff-gate6: the HANDOFF is recreated during the window (after the take-aside, before the link)
    hp.write_bytes(h0)
    newer = h0.replace(b'"n1"', b'"n1 (recreated)"')
    done.clear()

    def recreate(name, x):
        if name == 'link' and Path(x[1]) == hp and not hp.exists() and not done:
            done.append(name)
            hp.write_bytes(newer)
    rc = run(['handoff-gate6', '--handoff', hp, *rec, '--evidence', td / 'b_e2'], recreate)
    assert done and rc == 1 and hp.read_bytes() == newer, ('a HANDOFF recreated meanwhile was overwritten', rc, done)
    kept = [p for p in hp.parent.iterdir() if p.name.endswith('.aside')]
    assert len(kept) == 1 and kept[0].read_bytes() == h0 and not [p for p in hp.parent.iterdir() if p.name.endswith('.tmp')], kept
    ok('S4-004_report_back_concurrent_owner_writes_never_lost', injected=['decisions append', 'handoff edit before swap', 'handoff recreated in window'])


@register
def test_tool_run_d3_injected_failing_gate_stops_publication(td: Path) -> None:
    mark = td / 'published'
    base = ['bash', str(GEN3 / 'run_d3.sh'), '--h1', str(td / 'h1'), '--pin', 'c' * 64, '--d2', str(td / 'd2'),
            '--evidence', str(td / 'ev'), '--work', str(td / 'w'), '--target', str(td / 'target'), '--source', str(td / 'src'),
            '--source-before', str(td / 'b.json')]
    steps = ('verify', 'extract', 'builders', 'probe', 'regen', 'gate1b', 'gate2', 'gate3', 'gate4', 'gate5', 'gate7',
             'determinism', 'publish', 'verify_d3', 'source')
    env = dict(os.environ, C8_SITE='fake', C8_GEN3_TEST_HOOKS='1', **{f'C8_GEN3_STEP_{s}': 'true' for s in steps})
    env['C8_GEN3_STEP_publish'] = f'touch {mark}'
    cp = subprocess.run(base, capture_output=True, text=True, env=env)
    assert cp.returncode == 0 and mark.exists(), (cp.returncode, cp.stdout[-1000:], cp.stderr[-1000:])
    order = re.findall(r'step (\w+): start', cp.stdout)
    assert order == list(steps), order
    for g in ('gate1b', 'gate2', 'gate3', 'gate4', 'gate5', 'gate7', 'determinism'):
        mark.unlink(missing_ok=True)
        e2 = dict(env, **{f'C8_GEN3_STEP_{g}': 'exit 1'})
        cp = subprocess.run(base, capture_output=True, text=True, env=e2)
        assert cp.returncode != 0 and not mark.exists() and f'step {g}: start' in cp.stdout and 'step publish' not in cp.stdout, (g, cp.stdout[-800:])
    # without the fake site the hooks are ignored (the real steps run, and here fail at once)
    e3 = dict(env, C8_SITE='expanse')
    mark.unlink(missing_ok=True)
    cp = subprocess.run(base, capture_output=True, text=True, env=e3)
    assert cp.returncode != 0 and not mark.exists()
    ok('A-INV-1_injected_failing_gate_in_run_d3_stops_before_publication', gates=7)


@register
def test_tool_slurm_job_scripts(td: Path) -> None:
    """slurm/gen_d3_0.sh (J-GEN-D3-0), slurm/h1_copy.sh (J-H1-COPY) and slurm/gen_d3.sh (J-GEN-D3) on a fake package
    export (a stub Makefile, run_d3.sh and test_gen3.py; the real gates_d3.py and g3common.py): the D.10 preamble
    (C8_ENV_SETUP sourced, refusals exit 64), C8_SCRATCH computed inside the job (a login-node value is ignored),
    TMPDIR=$C8_SCRATCH/tmp for make, test_gen3.py and the tools, the inputs as environment variables (no script
    arguments: slurm_submit.py raw refuses them), run_d3.sh's exact arguments, and J-GEN-D3-0's verdict."""
    sys.path.insert(0, str(GEN3))
    import gates_d3 as gd
    sha12, pin = '0123456789ab', '4' * 64
    root = td / 'root'
    store, pkg, node = root / 'store', root / 'pkg' / sha12, td / 'node'
    for d in (pkg / 'gen3', pkg / 'slurm', store / 'c7d2_frozen', td / 'shims'):
        d.mkdir(parents=True)
    for f in ('gates_d3.py', 'g3common.py'):
        shutil.copy2(GEN3 / f, pkg / 'gen3' / f)
    for f in ('gen_d3_0.sh', 'gen_d3.sh', 'h1_copy.sh', 'site.sh'):
        shutil.copy2(ROOT / 'slurm' / f, pkg / 'slurm' / f)
    calls = td / 'calls.log'
    bins = ['gen3/regenerate_rates', 'gen3/size_probe', 'gen3/regenerate_rates_san', 'selftest/regenerate_rates_unguarded_san']
    rule = lambda bs: ''.join(f'\tmkdir -p bin/{Path(b).parent} && echo stub > bin/{b} && echo "command: stub" > bin/{b}.build.txt\n' for b in bs)
    (pkg / 'Makefile').write_text('.PHONY: gen3 gen3-sanitize\ngen3:\n' + rule(bins[:2]) + '\techo "make TMPDIR=$$TMPDIR" >> "$$C8_TEST_CALLS"\n'
                                  'gen3-sanitize:\n' + rule(bins[2:]) + '\techo "make-san TMPDIR=$$TMPDIR" >> "$$C8_TEST_CALLS"\n')
    (pkg / 'gen3/run_d3.sh').write_text(
        '#!/bin/bash\nset -eu\necho "run_d3 TMPDIR=$TMPDIR ARGS=$*" >> "$C8_TEST_CALLS"\nmode=$1; ev=\n'
        'while [ $# -gt 0 ]; do case "$1" in --evidence) ev=$2; shift 2 ;; *) shift ;; esac; done\n'
        'if [ "$mode" = --pre-h1 ]; then cp "$C8_TEST_GATE1A" "$ev/gate1a.json"; else echo "$C8_TEST_PIN_D3" > "$ev/MANIFEST_d3.sha256"; fi\n')
    (pkg / 'gen3/test_gen3.py').write_text(
        'import json, os, sys, tempfile\n'
        'open(os.environ["C8_TEST_CALLS"], "a").write(f"test_gen3 TMPDIR={os.environ.get(\'TMPDIR\')} tempdir={tempfile.gettempdir()} '
        'args={\' \'.join(sys.argv[1:])}\\n")\n'
        f'tests = [dict(test=n) for n in {list(gd.SANITIZE_NEED)!r}]\n'
        'json.dump(dict(status="passed", sanitize="--sanitize" in sys.argv, tmpdir=tempfile.gettempdir(), tests=tests),\n'
        '          open(sys.argv[sys.argv.index("--output") + 1], "w"))\n')
    shims = {'python3': f'exec "{sys.executable}" "$@"'}
    if not shutil.which('lscpu'):
        shims['lscpu'] = 'echo "Model name: stand-in"'
    if not shutil.which('sha256sum'):
        shims['sha256sum'] = 'exec shasum -a 256 "$@"'
    for name, body in shims.items():
        (td / 'shims' / name).write_text(f'#!/bin/bash\n{body}\n')
        (td / 'shims' / name).chmod(0o755)
    setup = td / 'env.sh'
    setup.write_text(f'export C8_SITE=fake C8_ROOT={root} C8_STORE={store}\n')
    g1a_x86, g1a_mac = td / 'g1a_x86.json', td / 'g1a_mac.json'
    g1a_x86.write_text(json.dumps(gate1a_record(td, 'x86', 'x86_64', '4242', 'expanse')))
    g1a_mac.write_text(json.dumps(gate1a_record(td, 'mac', 'arm64', '4242', 'fake')))
    base = {k: v for k, v in os.environ.items() if not k.startswith(('SLURM_', 'C8_')) and k != 'TMPDIR'}
    base.update(PATH=f'{td / "shims"}:{os.environ.get("PATH", "")}', C8_ENV_SETUP=str(setup), C8_PACKAGE=str(pkg),
                SLURM_JOB_ID='4242', SLURM_TMPDIR=str(node), SLURM_CPUS_PER_TASK='3', C8_SCRATCH='/login/node/value',
                C8_TEST_CALLS=str(calls), C8_TEST_GATE1A=str(g1a_x86), C8_TEST_PIN_D3='5' * 64)

    def job(script, rc, drop=(), **extra):
        calls.write_text('')
        env = {k: v for k, v in dict(base, **extra).items() if k not in drop}
        cp = subprocess.run(['bash', str(pkg / 'slurm' / script)], capture_output=True, text=True, env=env)
        assert cp.returncode == rc, (script, extra, drop, cp.returncode, cp.stdout[-1500:], cp.stderr[-1500:])
        return cp, calls.read_text()
    tmp = f'TMPDIR={node}/tmp'
    # J-GEN-D3-0
    ev0 = root / 'evidence' / sha12 / 'gen_d3_0'
    cp, log = job('gen_d3_0.sh', 0)
    assert f'make {tmp}' in log and f'make-san {tmp}' in log and f'test_gen3 {tmp} tempdir={node}/tmp args=--sanitize' in log, log
    assert (f'run_d3 {tmp} ARGS=--pre-h1 --d2 {store}/c7d2_frozen --evidence {ev0} --work {node}/gen_d3_0 --threads 3'
            in log), log
    assert '/login/node/value' not in log + cp.stdout and (node / 'tmp').is_dir()
    r = json.loads((ev0 / 'jgen_d3_0.json').read_text())
    assert r['passed'] is True and r['run_class'] == 'expanse' and r['sanitizer_tmpdir'] == f'{node}/tmp', r
    assert (ev0 / 'binaries.sha256').read_text().count('bin/') == 4 and 'tmpdir: ' + f'{node}/tmp' in (ev0 / 'environment.txt').read_text()
    cp, _ = job('gen_d3_0.sh', 1, C8_TEST_GATE1A=str(g1a_mac))
    assert json.loads((ev0 / 'jgen_d3_0.json').read_text())['passed'] is False
    cp, _ = job('gen_d3_0.sh', 0, C8_TEST_GATE1A=str(g1a_mac), C8_GEN3_REHEARSAL='1')
    r = json.loads((ev0 / 'jgen_d3_0.json').read_text())
    assert r['passed'] is False and r['rehearsal'] is True and r['checks_passed'] is True and 'REHEARSAL' in cp.stdout, r
    cp, _ = job('gen_d3_0.sh', 64, drop=('C8_ENV_SETUP',))
    assert 'C8_ENV_SETUP' in cp.stderr
    # J-H1-COPY, with the real gates_d3.py h1-copy on a fake HANDOFF tree whose verifier checks the pin
    src = td / 'handoff_tree'
    hpin = fake_h1_tree(src)
    cp, _ = job('h1_copy.sh', 0, C8_H1_PIN=hpin, C8_H1_SOURCE=str(src))
    evc = root / 'evidence' / sha12 / 'h1_copy'
    assert json.loads((evc / 'h1_copy.json').read_text())['passed'] is True and (store / 'h1' / hpin[:12] / 'MANIFEST.json').is_file()
    assert (evc / 'h1_source_listing_before.json').is_file() and f'C8_H1_BEFORE={evc}/h1_source_listing_before.json' in cp.stdout
    job('h1_copy.sh', 64, C8_H1_PIN='xyz', C8_H1_SOURCE=str(src))
    job('h1_copy.sh', 64, C8_H1_PIN=hpin, C8_H1_SOURCE=str(td / 'nowhere'))
    cp, _ = job('h1_copy.sh', 1, drop=('C8_H1_PIN',), C8_H1_SOURCE=str(src))
    assert 'C8_H1_PIN' in cp.stderr
    # J-GEN-D3
    before = evc / 'h1_source_listing_before.json'
    gen = dict(C8_H1_PIN=pin, C8_H1_SOURCE=str(src), C8_H1_BEFORE=str(before))
    cp, _ = job('gen_d3.sh', 64, **gen)
    assert f'{store}/h1/{pin[:12]}: no verified H1 copy' in cp.stderr, cp.stderr
    (store / 'h1' / pin[:12]).mkdir(parents=True)
    cp, _ = job('gen_d3.sh', 64, **gen)
    assert 'inputs/two_loop.json is missing' in cp.stderr and 'after G2a' in cp.stderr, cp.stderr
    for f in ('inputs/two_loop.json', 'inputs/order7/two_loop.json', 'inputs/gamma_d3_8.txt', 'reference/reference/d3_C6_two_loop.json'):
        (pkg / f).parent.mkdir(parents=True, exist_ok=True)
        (pkg / f).write_text('{}\n')
    cp, log = job('gen_d3.sh', 0, **gen)
    ev = root / 'evidence' / sha12 / 'gen_d3'
    want = (f'run_d3 {tmp} ARGS=--h1 {store}/h1/{pin[:12]} --pin {pin} --d2 {store}/c7d2_frozen --evidence {ev} '
            f'--work {node}/gen_d3 --target {store}/d3_payload/{pin[:12]} --source {src} --source-before {before} '
            f'--threads 3 --commit {sha12}')
    assert want in log and f'make {tmp}' in log and '/login/node/value' not in log + cp.stdout, log
    assert '5' * 64 in cp.stdout and (ev / 'binaries.sha256').read_text().count('bin/') == 2
    job('gen_d3.sh', 64, **dict(gen, C8_H1_PIN='4' * 63))
    job('gen_d3.sh', 64, **dict(gen, C8_H1_BEFORE=str(td / 'none.json')))
    (store / 'd3_payload' / pin[:12]).mkdir(parents=True)
    cp, _ = job('gen_d3.sh', 64, **gen)
    assert 'exists (a published tree is frozen)' in cp.stderr
    cp, _ = job('gen_d3.sh', 1, drop=('C8_H1_BEFORE',), **gen)
    assert 'C8_H1_BEFORE' in cp.stderr
    ok('D.10_job_scripts_gen_d3_0_h1_copy_gen_d3_scratch_tmpdir_inputs_and_verdicts')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--sanitize', action='store_true')
    ap.add_argument('--build-sanitize', action='store_true', help='with --sanitize: build the sanitizer binaries here')
    ap.add_argument('--cxx')
    ap.add_argument('--bin-dir')
    ap.add_argument('--output')
    ap.add_argument('--only', choices=('regen', 'tools'))
    ap.add_argument('--corpus', type=int, default=500)
    a = ap.parse_args(argv)
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='c8d3_gen3_') as td:
        td = Path(td)
        if a.only != 'tools':
            regen_tests(a, td)
        if a.only != 'regen':
            if tool_tests.B is None:
                tool_tests.B = Bins(argparse.Namespace(**{**vars(a), 'sanitize': False}), td)
            for fn in tool_tests.funcs:
                sub = td / fn.__name__
                sub.mkdir()
                fn(sub)
    rec = dict(schema='c8-d3-test-gen3-1', status='passed', sanitize=a.sanitize, host=platform.node(),
               machine=platform.machine(), python=sys.version.split()[0], seconds=round(time.time() - t0, 1),
               tmpdir=tempfile.gettempdir(), tests=RESULTS)
    if a.output:
        c.write_json(a.output, rec, 'test record')
    print(json.dumps(dict(status='passed', tests=len(RESULTS), seconds=rec['seconds'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
