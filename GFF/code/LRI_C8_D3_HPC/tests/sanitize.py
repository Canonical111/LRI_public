#!/usr/bin/env python3
"""A-KER-4 (PLAN.md; J-VAL-4): the native code under the sanitizer builds of `make sanitize` (C.7):
bin/c8d3_{decimal,gmp}_san, bin/c8d3_inspect_san, bin/test/point_checks_{gmp,decimal}_san and the coverage
self-test binary bin/selftest/c8d3_inspect_unguarded_san. Expanse.

  python3 -B tests/sanitize.py [--selftest] [--parsers] [--runs] [--max-loop 7] [--corpus 500] [--output FILE]
  (no part flag: all three parts and the self-test)

Every run uses ASAN_OPTIONS=detect_leaks=0:abort_on_error=1:handle_abort=1 and UBSAN_OPTIONS=halt_on_error=1:
print_stacktrace=1; a sanitizer or _GLIBCXX_ASSERTIONS report anywhere is a failure.
  --selftest  a one-past-the-end std::array write, compiled with the Makefile's SAN_FLAGS and STRICT, must abort.
  --runs      the workers on the L2 graph and the 2 lightest and 2 heaviest kernels (by M T) of every (sector, L) up
              to --max-loop (L <= 7 in Stage 3a, L8 in Stage 3b), 2 replicates x 64 points, layouts 0/1/2, 4 threads,
              orders 7 and 8 where valid, --mp-check on and off, both backends; the inspector (files and sizes) and
              the point checks (both backends, and --deep on the A-KER-7 fixture) on the same kernels. All exit 0.
  --parsers   the parser corpus (round-1 R11): A-INV-1's targeted G-file cases (gen3/test_gen3.targeted_cases on the
              smallest L3 kernel, magic C7D3GRAPH1) with the worker reader's expected outcome (exit 2 with the path and
              the reason, or exit 0 where the worker's reader accepts what regenerate_rates refuses: repeated or
              unordered masks and indices), through bin/c8d3_inspect_san and, as one-task files, through
              bin/c8d3_{gmp,decimal}_san; the seeded mutants (seed 8814, --corpus per base file, the 4 base files of
              gen3/test_gen3.py with magic C7D3GRAPH1) through bin/c8d3_inspect_san: exit 0, or exit 2 naming the file,
              within 10 s; A-KER-1's task, net, gamma and grid cases (tests/validate.py bad_cases) through both worker
              sanitizer builds. Then the coverage self-test (C.7): the index-M case on
              bin/selftest/c8d3_inspect_unguarded_san ends by SIGABRT with libstdc++'s "__n < this->size()", and the
              first package frame of ASan's stack trace is prepare's `g.mon_ids[tree[end].mon]` line of src/kernel.hpp;
              the same case exits 2 with the path on bin/c8d3_inspect_san (the control).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_common as nc  # noqa: E402
import validate  # noqa: E402
sys.path.insert(0, str(nc.ROOT / 'gen3'))
import test_gen3 as tg  # noqa: E402

SAN = {'gmp': nc.BIN / 'c8d3_gmp_san', 'decimal': nc.BIN / 'c8d3_decimal_san'}
INSPECT_SAN = nc.BIN / 'c8d3_inspect_san'
UNGUARDED = nc.BIN / 'selftest/c8d3_inspect_unguarded_san'
POINTS_SAN = {'gmp': nc.BIN / 'test/point_checks_gmp_san', 'decimal': nc.BIN / 'test/point_checks_decimal_san'}
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:abort_on_error=1:handle_abort=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
REPORT = tg.REPORT_PATTERNS
TIMEOUT = 10.0
RESULTS: list[dict] = []
# The worker's reader against regenerate_rates' (gen3/test_gen3.targeted_cases): the cases whose expected outcome
# differs. None = the worker's reader accepts the file (it does not require strictly increasing masks or indices).
WORKER_REASON = {'header_magic_unknown': r"magic 'C7D9GRAPH1' is not C7D3GRAPH1", 'header_id_-1': r'id -1 out of range',
                 'header_wa_nan': r'truncated or malformed wa', 'header_wa_abc': r'truncated or malformed wa',
                 'term_index_2^31': r'truncated or malformed term 0 index', 'mask_repeated': None, 'mask_out_of_order': None,
                 'term_index_repeated': None}


def record(**kw):
    RESULTS.append(kw)
    print(json.dumps(kw, default=str), flush=True)


def run(cmd, timeout=None) -> subprocess.CompletedProcess:
    t0 = time.monotonic()
    try:
        cp = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, errors='replace', env=ENV, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise AssertionError(f'{cmd[0]}: run over {timeout} s ({cmd[1:4]})')
    cp.seconds = time.monotonic() - t0
    return cp


def clean(cp, what: str, allow=(0,)):
    if cp.returncode not in allow or any(s in cp.stderr for s in REPORT):
        raise AssertionError(f'{what}: status {cp.returncode}, stderr {cp.stderr[-3000:]}')


def makefile_san_flags() -> list[str]:
    text = (nc.ROOT / 'Makefile').read_text()
    san = re.search(r'^SAN_FLAGS = (.*)$', text, re.M).group(1).split()
    strict = re.search(r'^override STRICT = (.*)$', text, re.M).group(1).split()
    return san + strict


def part_selftest(td: Path):
    src = td / 'oob.cpp'
    src.write_text('#include <array>\n#include <cstdio>\nint main(int argc,char**){std::array<int,4> a{};a[3+argc]=1;std::printf("%d\\n",a[0]);return 0;}\n')
    exe = td / 'oob'
    subprocess.run([os.environ.get('CXX', 'g++'), *makefile_san_flags(), str(src), '-o', str(exe)], check=True)
    cp = run([exe])
    if cp.returncode == 0 or not any(s in cp.stderr for s in REPORT):
        raise AssertionError(f'sanitize --selftest: a one-past-the-end std::array write did not abort ({cp.returncode}): {cp.stderr[-1000:]}')
    record(test='selftest_oob_aborts', status=cp.returncode, flags=makefile_san_flags())


def part_runs(td: Path, max_loop: int):
    nc.require(*SAN.values(), INSPECT_SAN, *POINTS_SAN.values())
    inv = nc.inventory()
    groups = [('free', 2, [0])]
    for s in nc.SECTORS:
        for L in sorted(int(x) for x in inv[s]):
            if L > max_loop:
                continue
            rows = sorted(inv[s][str(L)], key=lambda r: (r['cost'], r['id']))
            groups.append((s, L, sorted({r['id'] for r in rows[:2] + rows[-2:]})))
    sel = [(s, L, g) for s, L, ids in groups for g in ids]
    n = 0
    with nc.extracted(sel) as root:
        for s, L, ids in groups:
            for layout in (0, 1, 2):
                netf = nc.net(td, nc.dim_of(L, layout), 52, 6060 + L + 7 * layout)
                for order in (7, 8):
                    if L > order:
                        continue
                    t = nc.write_tasks(td / 'san_tasks', L, nc.task_rows(ids), order=order)
                    for b, exe in SAN.items():
                        for mode in ('off', 'on'):
                            d, cp = nc.run_worker(exe, root / s, nc.GAMMA[order], netf, t, td / 'san.json', 4242, layout, '.8', 4,
                                                  mp_check=mode, env=ENV, check=False)
                            clean(cp, f'{b} {s} L{L} layout {layout} order {order} mp-check {mode}')
                            n += 1
            paths = [str(root / s / f'L{L}' / f'G{g}.txt') for g in ids]
            clean(run([INSPECT_SAN, 'files', *paths]), f'c8d3_inspect_san files {s} L{L}')
        # L <= 7 with C7(3)'s hard gates; L8 in --contract mode, so that a precision-contract breach there (recorded by
        # tests/check_points.py in J-VAL-2) does not end a run whose purpose here is the sanitizer check.
        lists = []
        for contract, keep in ((False, lambda L: 3 <= L <= 7), (True, lambda L: L >= 8)):
            paths = [str(root / s / f'L{L}' / f'G{g}.txt') for s, L, g in sel if keep(L)]
            if paths:
                lst = td / f'points_{int(contract)}.list'
                lst.write_text('\n'.join(paths) + '\n')
                lists.append((contract, lst))
        for b, exe in POINTS_SAN.items():
            for contract, lst in lists:
                clean(run([exe, *(['--contract'] if contract else []), lst]), f'point_checks_{b}_san' + (' --contract (L8)' if contract else ''))
            clean(run([exe, '--deep', nc.ROOT / 'tests/fixtures/deep_cancellation/L3/G0.txt']), f'point_checks_{b}_san --deep')
    for s in nc.SECTORS:   # the inspector's pack path on the L3 packs
        rows = inv[s]['3']
        idx = td / f'idx_{s}'
        idx.write_text(''.join(f'{r["id"]} 3 {r["offset"]} {r["length"]}\n' for r in rows))
        clean(run([INSPECT_SAN, 'sizes', nc.ROOT / f'inputs/packs/{s}_L3.pack', idx, 4]), f'c8d3_inspect_san sizes {s} L3')
    record(test='A-KER-4 sanitizer runs', worker_runs=n, kernels=len(sel), max_loop=max_loop,
           gate='every worker, inspector and point-check run exits 0 with no sanitizer or _GLIBCXX_ASSERTIONS report')


def c7d3(data: bytes) -> bytes:
    return data.replace(b'C7D2GRAPH1', b'C7D3GRAPH1', 1)


def part_parsers(td: Path, corpus: int):
    nc.require(*SAN.values(), INSPECT_SAN, UNGUARDED)
    inv = nc.inventory()
    small3 = min(inv['free']['3'], key=lambda r: (r['length'], r['id']))['id']
    small7p = min(inv['power']['7'], key=lambda r: (r['length'], r['id']))['id']
    with nc.extracted([('free', 2, 0), ('free', 3, small3), ('power', 7, small7p)]) as root:
        bases = {'L2': (root / 'free/L2/G0.txt').read_bytes(), 'L3': (root / f'free/L3/G{small3}.txt').read_bytes(),
                 'L7p': (root / f'power/L7/G{small7p}.txt').read_bytes(), 'L8': c7d3(tg.synthetic_l8())}
    d = td / 'targeted'
    d.mkdir()
    cases = tg.targeted_cases(tg.Base(bases['L3']))
    netf = nc.net(td, nc.dim_of(3, 0), 52, 3030)
    outcomes = {}
    for name, data, reason in cases:
        reason = WORKER_REASON.get(name, reason)
        gd = d / name / 'L3'
        gd.mkdir(parents=True)
        f = gd / f'G{small3}.txt'
        f.write_bytes(data)
        cp = run([INSPECT_SAN, 'files', f], timeout=TIMEOUT)
        if reason is None:
            clean(cp, f'targeted {name} (accepted by the worker reader)')
        else:
            clean(cp, f'targeted {name}', allow=(2,))
            if not re.search(re.escape(str(f)) + r': .*' + reason, cp.stderr):
                raise AssertionError(f'targeted {name}: expected {reason!r}, got {cp.stderr[-500:]}')
        t = nc.write_tasks(d / name / 'tasks', 3, [(0, 0, small3, 0, 64, 64)], order=8)
        for b, exe in SAN.items():
            _, cpw = nc.run_worker(exe, d / name, nc.GAMMA[8], netf, t, d / name / 'out.json', 1, 0, '.8', 1, env=ENV, check=False)
            if reason is None:
                clean(cpw, f'targeted {name} via the {b} worker', allow=(0, 2))
            else:
                clean(cpw, f'targeted {name} via the {b} worker', allow=(2,))
                if not re.search(re.escape(str(f)) + r': .*' + reason, cpw.stderr):
                    raise AssertionError(f'targeted {name} via the {b} worker: expected {reason!r}, got {cpw.stderr[-500:]}')
        outcomes[name] = 'exit0' if reason is None else 'exit2'
    record(test='A-KER-4 parser corpus: targeted G-file cases', cases=len(cases), outcomes=outcomes)
    # seeded mutants
    m = td / 'mutants'
    m.mkdir()
    rng = random.Random(tg.SEED)
    work = []
    for k in ('L2', 'L3', 'L7p', 'L8'):
        for i in range(corpus):
            kind, data = tg.mutate(bases[k], rng)
            work.append((f'{k}_{i:03d}_{kind}', data))

    def one(w):
        tag, data = w
        f = m / f'{tag}.txt'
        f.write_bytes(data)
        cp = run([INSPECT_SAN, 'files', f], timeout=TIMEOUT)
        if cp.returncode not in (0, 2) or any(s in cp.stderr for s in REPORT) or (cp.returncode == 2 and not cp.stderr.startswith(f'{f}: ')):
            raise AssertionError(f'mutant {tag}: status {cp.returncode}, stderr {cp.stderr[-2000:]}')
        f.unlink()
        return tag.split('_')[0] + (':exit0' if cp.returncode == 0 else ':exit2'), cp.seconds
    workers = max(1, min(32, len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count() or 1))
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, work))
    counts: dict = {}
    for k, _ in res:
        counts[k] = counts.get(k, 0) + 1
    record(test='A-KER-4 parser corpus: seeded mutants (seed 8814)', mutants=len(work), outcomes=counts,
           max_seconds=round(max(s for _, s in res), 3))
    # A-KER-1's task, net, gamma and grid cases (and the G-file ones) under both worker sanitizer builds
    bd = td / 'bad'
    bd.mkdir()
    with nc.extracted([('free', 3, small3)]) as root:
        bcases = validate.bad_cases(bd, root / 'free', small3)
        for b, exe in SAN.items():
            for c in bcases:
                ok, cp = validate.run_bad(exe, c, bd)
                if not ok or any(s in cp.stderr for s in REPORT):
                    raise AssertionError(f'A-KER-1 case {c["name"]} under {b}_san: {cp.returncode} {cp.stderr[-800:]}')
    record(test='A-KER-1 cases under the sanitizer builds', cases=[c['name'] for c in bcases])
    # the coverage self-test (C.7)
    data = dict((n, x) for n, x, _ in cases)['term_index_M']
    f = td / 'index_M' / 'L3' / f'G{small3}.txt'
    f.parent.mkdir(parents=True)
    f.write_bytes(data)
    cp = run([UNGUARDED, 'files', f], timeout=60)
    if cp.returncode != -signal.SIGABRT or '__n < this->size()' not in cp.stderr:
        raise AssertionError(f'unguarded self-test: status {cp.returncode}, stderr {cp.stderr[-3000:]}')
    frames = [(int(x.group(1)), int(x.group(4))) for x in re.finditer(r'#(\d+) 0x[0-9a-f]+ in (.*?) ([^ ]*src/kernel\.hpp):(\d+)', cp.stderr)]
    lines = [i + 1 for i, s in enumerate((nc.ROOT / 'src/kernel.hpp').read_text().splitlines()) if 'g.mon_ids[tree[end].mon]' in s]
    if len(lines) != 1 or not frames or frames[0][1] != lines[0]:
        raise AssertionError(f'unguarded self-test: first package frame {frames[:3]} is not the site line {lines}: {cp.stderr[-3000:]}')
    cpc = run([INSPECT_SAN, 'files', f], timeout=TIMEOUT)
    clean(cpc, 'self-test control', allow=(2,))
    if not re.search(re.escape(str(f)) + r': .*term 0 index \d+ \d+ out of range', cpc.stderr):
        raise AssertionError(f'self-test control: {cpc.stderr[-500:]}')
    record(test='C.7 unguarded-index self-test', site_line=lines[0], first_package_frame=frames[0], control='exit 2 with the path and the index reason')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--parsers', action='store_true')
    ap.add_argument('--runs', action='store_true')
    ap.add_argument('--max-loop', type=int, default=7)
    ap.add_argument('--corpus', type=int, default=500)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    every = not (a.selftest or a.parsers or a.runs)
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='c8d3_sanitize_') as td:
        td = Path(td)
        if a.selftest or every:
            part_selftest(td)
        if a.parsers or every:
            part_parsers(td, a.corpus)
        if a.runs or every:
            part_runs(td, a.max_loop)
    res = dict(status='passed', tests=RESULTS, host=nc.host_info(), wall_seconds=round(time.time() - t0, 1),
               binaries={str(p): nc.digest(p) for p in (*SAN.values(), INSPECT_SAN, UNGUARDED, *POINTS_SAN.values()) if p.exists()})
    nc.dump(a.output, res)
    print(json.dumps({k: v for k, v in res.items() if k != 'tests'}, indent=2))


if __name__ == '__main__':
    main()
