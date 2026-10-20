#!/usr/bin/env python3
"""External library probe of a native binary (PLAN.md C.8, HD9, A-KER-3). Linux only.

  libprobe.py BINARY            print the probe record as JSON

The record:
  (a) `readelf -d BINARY`: the NEEDED entries and RPATH/RUNPATH;
  (b) `env -i ldd BINARY`: the resolution without LD_LIBRARY_PATH (soname -> path, or "not found");
  (c) one real start, `env -i LD_DEBUG=libs BINARY --describe`: the libgmp file the loader initialized (its trace
      line "calling init: <path>");
  (d) for a resolved libgmp: its realpath and the version read from the file itself
      (ctypes.c_char_p.in_dll(ctypes.CDLL(path), "__gmp_version"), the symbol behind gmp.h's gmp_version).
`libgmp` is "not_applicable" when libgmp appears in none of (a), (b) and (c) (the decimal builds), else a block with
the three observations, the realpath and the version. tools/buildinfo.py records it at build time and
tests/check_build.py re-runs it and applies the backend-specific rules (gmp_problems / decimal_problems below).
The parsers are pure functions of the tools' text, so check_build.py --selftest runs them on canned outputs.
"""
from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import sys
from pathlib import Path

GMP_SONAME = 'libgmp.so.10'


def parse_readelf(text: str) -> dict:
    needed, rpath, runpath = [], [], []
    for line in text.splitlines():
        m = re.search(r'\((NEEDED|RPATH|RUNPATH)\)\s+[^\[]*\[(.*)\]', line)
        if not m:
            continue
        kind, value = m.group(1), m.group(2)
        if kind == 'NEEDED':
            needed.append(value)
        else:
            (rpath if kind == 'RPATH' else runpath).extend(p for p in value.split(':') if p)
    return {'needed': needed, 'rpath': rpath, 'runpath': runpath}


def parse_ldd(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = re.match(r'\s*(\S+)\s+=>\s+(not found|\S+)', line)
        if m:
            out[m.group(1)] = None if m.group(2) == 'not found' else m.group(2)
    return out


def parse_ld_debug(text: str) -> list[str]:
    """Every object the loader initialized ("calling init: <path>"), in trace order."""
    return [m.group(1) for m in re.finditer(r'calling init:\s+(\S+)', text)]


def gmp_version_of(path: str) -> str | None:
    try:
        return ctypes.c_char_p.in_dll(ctypes.CDLL(path), '__gmp_version').value.decode()
    except (OSError, ValueError, AttributeError):
        return None


def summarize(elf: dict, ldd: dict, inits: list[str], realpath=os.path.realpath, version=gmp_version_of) -> dict:
    """The probe record from parsed outputs (realpath and version injectable for the self-test)."""
    in_needed = any(n.startswith('libgmp.so') for n in elf['needed'])
    ldd_gmp = next((p for s, p in ldd.items() if s.startswith('libgmp.so')), None)
    ldd_has = any(s.startswith('libgmp.so') for s in ldd)
    init_gmp = next((p for p in inits if Path(p).name.startswith('libgmp.so')), None)
    rec = {**elf, 'ldd': ldd, 'loader_inits': inits}
    if not (in_needed or ldd_has or init_gmp):
        rec['libgmp'] = 'not_applicable'
        return rec
    real = realpath(ldd_gmp) if ldd_gmp else None
    rec['libgmp'] = {'needed': in_needed, 'ldd_path': ldd_gmp, 'loader_path': init_gmp,
                     'ldd_realpath': real, 'loader_realpath': realpath(init_gmp) if init_gmp else None,
                     'version': version(real) if real else None}
    return rec


def probe(binary) -> dict:
    binary = str(Path(binary).resolve())
    if not sys.platform.startswith('linux'):
        return {'skipped': f'not Linux ({sys.platform})'}

    def run(cmd, **kw):
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)
    elf = parse_readelf(run(['readelf', '-d', binary]).stdout)
    ldd = parse_ldd(run(['env', '-i', 'ldd', binary]).stdout)
    cp = run(['env', '-i', 'LD_DEBUG=libs', binary, '--describe'])
    rec = summarize(elf, ldd, parse_ld_debug(cp.stderr))
    rec['describe_rc'] = cp.returncode
    return rec


def gmp_problems(rec: dict, gmp_lib: str, gmp_version: str, realpath=os.path.realpath, search: str = 'rpath') -> list[str]:
    """A GMP build (C.8): libgmp.so.10 NEEDED, gmp_lib in RPATH/RUNPATH (search 'rpath', Expanse's Spack GMP; search
    'system', symmetry's system GMP, needs no RPATH: the loader's default search must find it), ldd = loader =
    realpath(gmp_lib/libgmp.so.10), the file's version gmp_version."""
    if rec.get('skipped'):
        return [f'no probe ({rec["skipped"]})']
    g = rec.get('libgmp')
    if not isinstance(g, dict):
        return ['libgmp is not linked (a GMP build needs libgmp.so.10)']
    want = realpath(str(Path(gmp_lib) / GMP_SONAME))
    bad = []
    if GMP_SONAME not in rec['needed']:
        bad.append(f'{GMP_SONAME} is not NEEDED')
    if search == 'rpath' and gmp_lib not in rec['rpath'] + rec['runpath'] and str(Path(gmp_lib)) not in rec['rpath'] + rec['runpath']:
        bad.append(f'{gmp_lib} is not in RPATH/RUNPATH ({rec["rpath"] + rec["runpath"]})')
    if g['ldd_realpath'] != want:
        bad.append(f'env -i ldd resolves libgmp to {g["ldd_path"]} (realpath {g["ldd_realpath"]}), not {want}')
    if g['loader_realpath'] != want:
        bad.append(f'the loader initialized {g["loader_path"]} (realpath {g["loader_realpath"]}), not {want}')
    if g['version'] != gmp_version:
        bad.append(f'libgmp version {g["version"]}, not {gmp_version}')
    return bad


def decimal_problems(rec: dict) -> list[str]:
    """A decimal build: libgmp in none of NEEDED, the ldd resolution and the loader trace."""
    if rec.get('skipped'):
        return [f'no probe ({rec["skipped"]})']
    return [] if rec.get('libgmp') == 'not_applicable' else [f'a decimal build links libgmp: {rec.get("libgmp")}']


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(64)
    print(json.dumps(probe(sys.argv[1]), indent=2))
