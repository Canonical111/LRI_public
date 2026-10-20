#!/usr/bin/env python3
"""Preserve strict arithmetic flags and record a native C8 build's provenance."""
from __future__ import annotations
import hashlib
import json
import platform
import shlex
import subprocess
import sys
from pathlib import Path


def strict_conflicts(tokens):
    exact = {'-ffast-math', '-Ofast', '-funsafe-math-optimizations', '-fassociative-math',
             '-freciprocal-math', '-fno-signed-zeros', '-fno-trapping-math',
             '-ffinite-math-only', '-fcx-limited-range', '-fno-openmp'}
    return [t for t in tokens if t in exact
            or (t.startswith('-ffp-contract=') and t != '-ffp-contract=off')
            or (t.startswith('-std=') and t != '-std=c++17')
            or t.startswith(('-mfpmath=', '-fexcess-precision='))]


def run(command, stdin=None):
    return subprocess.run(command, input=stdin, capture_output=True, text=True,
                          check=True, timeout=120).stdout


def main(args):
    if args[:1] == ['check']:
        bad = strict_conflicts(args[1:])
        if bad:
            raise ValueError('flags override strict numerical arithmetic: ' + ' '.join(bad))
        return
    if args[:1] == ['write'] and len(args) >= 5 and args[4] == '--':
        binary = Path(args[1]).resolve()
        cxx, cppflags = shlex.split(args[2]), shlex.split(args[3])
        boost = run([*cxx, *cppflags, '-x', 'c++', '-E', '-P', '-'],
                    '#include <boost/version.hpp>\nBOOST_VERSION\n').split()[-1]
        record = {
            'schema': 'c8-d3-buildinfo-1', 'binary': binary.name, 'command': args[5:],
            'compiler_version': run([*cxx, '--version']).splitlines()[0],
            'boost_version': int(boost), 'describe': json.loads(run([str(binary), '--describe'])),
            'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'host': {'platform': platform.platform(), 'machine': platform.machine(),
                     'python': platform.python_version(), 'libc': platform.libc_ver()},
        }
        binary.with_name(binary.name + '.buildinfo.json').write_text(json.dumps(record, indent=2) + '\n')
        return
    raise ValueError('usage: native_buildinfo.py check FLAGS... | write BINARY CXX CPPFLAGS -- COMMAND...')


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
