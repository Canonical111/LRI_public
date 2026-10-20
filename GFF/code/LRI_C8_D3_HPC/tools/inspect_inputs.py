#!/usr/bin/env python3
"""`make inputs-inspect` (PLAN.md B, C.7, A-KER-5): the inspect fields of inputs/inventory.json.

  python3 -B tools/inspect_inputs.py build [--threads N]     (then `make inputs` merges them; the Makefile runs both)

For every (sector, L) of inputs/inventory.json (itself verified against inputs/manifest.json):
  * bin/c8d3_inspect sizes PACK INDEX THREADS loads every member from its pack bytes with the worker's own reader and
    prepare() (kernel.hpp read_graph, rates at scale 1) and reports masks, terms, products, segments, addends,
    numerators and kernel_bytes; masks and terms must equal the row's monomials and terms (the header's M and T);
  * fmax, the maximal forest size of the class, is a property of the class and not of the payload (terms with the same
    monomial list are merged into one payload term), so it comes from gen3's size probe (bin/gen3/size_probe on
    reference/c8d1_inputs8/classes<L>.txt, the RECON 6.3.4 definition). The probe row of each kernel id must have the
    kernel's sector as its status and the same M, T, products and addends as the inspector (the cross-check of
    gen3/opcount.py's c7d3 command, here against the worker's own counts).
The result is inspect/inspect.json (schema c8-d3-inspect-data-1): per (sector, L) one row
[id, member sha256, products, segments, addends, numerators, kernel_bytes, fmax] per kernel, ascending id, one row
per line, plus the inspector's and the probe's identity. tools/prepare_inputs.py build merges it into the inventory
rows whose member sha256 matches and sets inspect_complete when every row has its fields. Native (Expanse): its
outputs are committed as a generated-data commit (Stage 3a for L <= 7; Stage 2b adds L8).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, digest  # noqa: E402
import prepare_inputs as pi  # noqa: E402
from members import inventory  # noqa: E402

INSPECT = ROOT / 'bin/c8d3_inspect'
PROBE = ROOT / 'bin/gen3/size_probe'
CLASSES = ROOT / 'reference/c8d1_inputs8'
OUT = ROOT / pi.INSPECT_DATA


def describe(exe: Path) -> dict:
    cp = subprocess.run([str(exe), '--describe'], capture_output=True, text=True, timeout=120)
    if cp.returncode:
        raise SystemExit(f'inputs-inspect: {exe} --describe failed: {cp.stderr[-500:]}')
    return json.loads(cp.stdout)


def inspect_loop(pack: Path, rows: list, L: int, threads: int, td: Path) -> dict:
    idx = td / 'index'
    idx.write_text(''.join(f'{r["id"]} {L} {r["offset"]} {r["length"]}\n' for r in rows))
    cp = subprocess.run([str(INSPECT), 'sizes', str(pack), str(idx), str(threads)], capture_output=True, text=True)
    if cp.returncode:
        raise SystemExit(f'inputs-inspect: c8d3_inspect failed on {pack}: {cp.stderr[-1500:]}')
    out = [json.loads(line) for line in cp.stdout.splitlines()]
    if [o['id'] for o in out] != [r['id'] for r in rows]:
        raise SystemExit(f'inputs-inspect: {pack}: the inspector did not report the index in order')
    return {o['id']: o for o in out}


def probe_loop(L: int, threads: int) -> tuple[dict, str]:
    cls = CLASSES / f'classes{L}.txt'
    cp = subprocess.run([str(PROBE), str(cls)], capture_output=True, text=True, env={**os.environ, 'OMP_NUM_THREADS': str(threads)})
    if cp.returncode:
        raise SystemExit(f'inputs-inspect: size_probe failed on {cls}: {cp.stderr[-800:]}')
    return {int(r['id']): r for r in csv.DictReader(io.StringIO(cp.stdout))}, digest(cls)


def build(threads: int) -> dict:
    for exe in (INSPECT, PROBE):
        if not exe.exists():
            raise SystemExit(f'inputs-inspect: build {exe.relative_to(ROOT)} first (make inspect; make gen3)')
    desc = describe(INSPECT)
    if desc.get('schema') != 'c8-d3-inspect-1' or desc.get('diagnostic') is not False:
        raise SystemExit(f'inputs-inspect: {INSPECT} is not the default inspector build ({desc.get("schema")}, diagnostic {desc.get("diagnostic")})')
    inv = inventory()
    rows_out: dict = {}
    classes_sha = {}
    errors = []
    with tempfile.TemporaryDirectory(prefix='c8d3_inspect_') as td:
        td = Path(td)
        loops = sorted({int(L) for s in pi.SECTORS for L in inv[s]})
        probes = {}
        for L in loops:
            probes[L], classes_sha[str(L)] = probe_loop(L, threads)
        for s in pi.SECTORS:
            rows_out[s] = {}
            for L in sorted(inv[s], key=int):
                rows = inv[s][L]
                got = inspect_loop(ROOT / 'inputs' / f'packs/{s}_L{L}.pack', rows, int(L), threads, td)
                out = []
                for r in rows:
                    o, p = got[r['id']], probes[int(L)].get(r['id'])
                    where = f'{s} L{L} G{r["id"]}'
                    if (o['masks'], o['terms'], o['L']) != (r['monomials'], r['terms'], int(L)):
                        errors.append(f'{where}: inspector masks/terms {o["masks"]}/{o["terms"]} != header M/T {r["monomials"]}/{r["terms"]}')
                    if p is None or p['status'] != s or (int(p['M']), int(p['T']), int(p['products']), int(p['addends'])) != (o['masks'], o['terms'], o['products'], o['addends']):
                        errors.append(f'{where}: size probe row {None if p is None else {k: p[k] for k in ("status", "M", "T", "products", "addends")}} '
                                      f'differs from the inspector ({o["masks"]}, {o["terms"]}, {o["products"]}, {o["addends"]})')
                        continue
                    out.append([r['id'], r['sha256'], o['products'], o['segments'], o['addends'], o['numerators'], o['kernel_bytes'], int(p['fmax'])])
                rows_out[s][L] = out
    if errors:
        raise SystemExit('inputs-inspect: ' + '; '.join(errors[:10]) + (f' (and {len(errors) - 10} more)' if len(errors) > 10 else ''))
    head = {'schema': pi.INSPECT_SCHEMA, 'fields': ['id', 'sha256', *pi.INSPECT_FIELDS],
            'inspector': {'path': 'bin/c8d3_inspect', 'executable_sha256': digest(INSPECT), 'describe_schema': desc['schema'],
                          'mp_backend': desc.get('mp_backend'), 'compiler': desc.get('compiler'), 'boost': desc.get('boost'),
                          'command': 'c8d3_inspect sizes PACK INDEX THREADS (rate scale 1)'},
            'fmax_source': {'tool': 'bin/gen3/size_probe', 'executable_sha256': digest(PROBE), 'classes_sha256': classes_sha,
                            'definition': 'maximal forest size of the class (gen3/size_probe.cpp, RECON 6.3.4); not derivable from the payload'},
            }
    lines = ['{'] + [f' {json.dumps(k)}: {json.dumps(v, sort_keys=True)},' for k, v in head.items()] + [' "rows": {']
    for si, s in enumerate(pi.SECTORS):
        lines.append(f'  "{s}": {{')
        loops = list(rows_out[s])
        for li, L in enumerate(loops):
            rs = rows_out[s][L]
            lines.append(f'   "{L}": [')
            lines += [f'    {json.dumps(r)}' + (',' if k < len(rs) - 1 else '') for k, r in enumerate(rs)]
            lines.append('   ]' + (',' if li < len(loops) - 1 else ''))
        lines.append('  }' + (',' if si < len(pi.SECTORS) - 1 else ''))
    lines += [' }', '}']
    text = '\n'.join(lines) + '\n'
    json.loads(text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    n = sum(len(v) for s in rows_out.values() for v in s.values())
    print(json.dumps({'written': str(OUT.relative_to(ROOT)), 'kernels': n, 'sha256': digest(OUT)}))
    return {'kernels': n}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--threads', type=int, default=int(os.environ.get('SLURM_CPUS_PER_TASK') or os.cpu_count() or 4))
    a = ap.parse_args(argv)
    build(a.threads)
    return 0


if __name__ == '__main__':
    sys.exit(main())
