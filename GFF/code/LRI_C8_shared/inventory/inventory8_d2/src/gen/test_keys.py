#!/usr/bin/env python3
"""A-INV-1: the checked 128-bit class-file reader of the d=2 payload generator (gen/c8gen.hpp).

Feeds crafted class files to bin/gen/test_keys (a driver around read_classes) and to the three generator
programs, and checks:
  * keys 2^64 and 2^70+1 are read and printed back exactly; every class file classes1..8 round-trips byte for
    byte (26,540 L8 keys, 5,068 of them above 2^64);
  * 2^128, '12a', a truncated file, a surplus row, a row with the wrong token count, a key wider than the class
    and an out-of-range header exit 2, naming the offending token and row; the builders refuse the same files
    with the same message before creating any output;
  * exactly NG rows are read;
  * compiling c8gen.hpp, and each generator source, with -Wall -Wextra gives no warning in gen/c8gen.hpp.
Pure logic, seconds. Usage: python3 -B gen/test_keys.py [--bin bin/gen] [--cxx g++] [--output FILE]"""
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


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--bin', type=Path, default=ROOT / 'bin/gen')
    ap.add_argument('--cxx', default=os.environ.get('CXX', 'g++'))
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    drv = a.bin / 'test_keys'
    results: list[dict] = []
    failed: list[str] = []

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
        # Round trip of every class file, byte for byte (exactly NG rows; 128-bit keys).
        for L in range(1, 9):
            f = CLASSES / f'classes{L}.txt'
            r = run([drv, f])
            check(f'classes{L}.txt round-trips byte for byte', r.returncode == 0 and r.stdout == f.read_text(),
                  r.stderr)
        rows = (CLASSES / 'classes8.txt').read_text().split('\n')[1:]
        big = sum(1 for line in rows if line and int(line.split()[0]) >= k64)
        check('classes8.txt holds 5,068 keys above 2^64', big == 5068, str(big))
        # -Wall -Wextra: no warning in gen/c8gen.hpp
        hdr = t / 'hdr.cpp'
        hdr.write_text('#include "c8gen.hpp"\nint main() { return 0; }\n')
        r = run([a.cxx, '-std=c++17', '-Wall', '-Wextra', '-fsyntax-only', f'-I{GEN}', hdr])
        check('c8gen.hpp alone: no warning under -Wall -Wextra', r.returncode == 0 and not r.stderr.strip(), r.stderr)
        for src in ('build_free.cpp', 'build_power.cpp', 'check_edge_forests.cpp', 'test_keys.cpp'):
            r = run([a.cxx, '-std=c++17', '-fopenmp', '-Wall', '-Wextra', '-fsyntax-only', GEN / src])
            inhdr = [line for line in r.stderr.splitlines() if 'c8gen.hpp' in line]
            check(f'{src}: no -Wall -Wextra diagnostic in c8gen.hpp', r.returncode == 0 and not inhdr, '\n'.join(inhdr))
    rec = dict(schema='c8-d2-gate-1', gate='A-INV-1 test_keys', passed=not failed, failed=failed, checks=results,
               cxx=run([a.cxx, '--version']).stdout.splitlines()[0] if shutil.which(a.cxx) else a.cxx)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'test_keys: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
