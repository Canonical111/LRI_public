#!/usr/bin/env python3
"""A-INV-2: regression of the ported d=2 builders against the frozen C7(2) payloads at L3..L7 (x86-64 only).

Regenerates every loop with bin/gen/build_free and bin/gen/build_power at each requested thread count, then checks
  * power L3..L7: every G-file byte-identical to reference/power_mass/inputs/L*/, the same file set;
  * free L7: all 2,441 finite G-files byte-identical, rate lines included (parity rule);
  * free L3..L6: header, mask, term and 2^E lines byte-identical; only the rate lines may differ (the frozen files
    keep legacy C6 rate tables, relabelled through verification/legacy_mapping.json), and their count is reported,
    with the files whose rate tokens agree and only the line's trailing space differs counted apart (the free
    builder writes the rate line as the frozen parity-rule free L7 files have it, tokens joined by single spaces
    with no trailing space; the frozen free L<=6 and power files keep the C7(2) builders' trailing space);
  * the builder inventory.json objects equal the frozen ones field by field (forests included; numbers compared
    as exact numerals, never through binary64);
  * the outputs are identical at every thread count (L7 included);
  * control for gate A-INV-3(b): the subgraph side file of both builders at L7 equals C8(1)'s L7_inventory.txt
    byte for byte, and the two builders' side files are identical at every loop.
--explain classifies every other difference (header weights, header counts, mask order or values, term order or
values, 2^E line, rate line, structure); for free L <= 6 such a difference is compared again after the
vertex/edge relabelling of legacy_mapping.json. Only a difference proven to be that relabelling is accepted.

Usage: python3 -B gen/regress.py --classes reference/LRI_C7_d2_progress/reference --threads 1,8 --explain
           [--bin bin/gen] [--work DIR] [--loops 3-7] [--output FILE]
Exit status 0 when A-INV-2 passes."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {'free': ROOT / 'reference/LRI_C7_d2_progress/inputs', 'power': ROOT / 'reference/power_mass/inputs'}
LEGACY = ROOT / 'reference/LRI_C7_d2_progress/verification/legacy_mapping.json'
C8D1 = ROOT / 'reference/c8d1_inputs8'


def parse_gfile(text: str) -> dict:
    """Split a G-file into its parts; raises ValueError if the structure is wrong."""
    lines = text.split('\n')
    if lines[-1] != '':
        raise ValueError('no final newline')
    lines = lines[:-1]
    head = lines[0].split()
    if len(head) != 7 or head[0] != 'C7D2GRAPH1':
        raise ValueError('bad header')
    M, T = int(head[5]), int(head[6])
    if len(lines) != 4 + T:
        raise ValueError(f'{len(lines)} lines for T={T}')
    masks = lines[1].split()
    if len(masks) != M:
        raise ValueError('mask count')
    return dict(lines=lines, head=head, M=M, T=T, terms=lines[2:2 + T], pow2=lines[2 + T], rate=lines[3 + T])


def classify(new: str, old: str) -> list[str]:
    """--explain: which parts of two G-files differ."""
    try:
        a, b = parse_gfile(new), parse_gfile(old)
    except ValueError as e:
        return [f'structure ({e})']
    out = []
    if a['head'] != b['head']:
        if a['head'][3:5] != b['head'][3:5]:
            out.append('header weights')
        if a['head'][:3] + a['head'][5:] != b['head'][:3] + b['head'][5:]:
            out.append('header counts or ids')
    if a['lines'][1] != b['lines'][1]:
        out.append('mask order' if sorted(a['lines'][1].split()) == sorted(b['lines'][1].split()) else 'mask values')
    if a['terms'] != b['terms']:
        out.append('term order' if Counter(a['terms']) == Counter(b['terms']) else 'term values')
    if a['pow2'] != b['pow2']:
        out.append('2^E line')
    if a['rate'] != b['rate']:
        out.append('rate line')
    return out


def canonical(text: str, perm: list[int] | None) -> tuple:
    """Order-independent form of masks and terms after relabelling edge e -> perm[e]."""
    g = parse_gfile(text)
    E = 2 * int(g['head'][1])
    p = perm if perm is not None else list(range(E))

    def pm(m: int) -> int:
        return sum(1 << p[e] for e in range(E) if m >> e & 1)

    masks = [int(x) for x in g['lines'][1].split()]
    terms = []
    for line in g['terms']:
        t = [int(x) for x in line.split()]
        k = t[0]
        basis = frozenset(pm(masks[i]) for i in t[1:1 + k])
        co = [0] * E
        for e, c in enumerate(t[1 + k:]):
            co[p[e]] = c
        terms.append((basis, tuple(co)))
    return frozenset(pm(m) for m in masks), Counter(terms)


def legacy_relabel_equal(new: str, old: str, gid: int, L: int, legacy: dict) -> str | None:
    """Return a description if new equals old after the legacy relabelling (either direction)."""
    for rec in legacy.get(L, []):
        if rec.get('new') != gid:
            continue
        perm = [int(x) for x in rec['edge_permutation']]
        inv = [0] * len(perm)
        for i, j in enumerate(perm):
            inv[j] = i
        ref = canonical(old, None)
        for name, p in (('edge_permutation', perm), ('inverse edge_permutation', inv)):
            if canonical(new, p) == ref:
                return f'equal after {name} of legacy map old={rec.get("old")}'
    return None


def exact_json(path: Path):
    return json.loads(path.read_text(), parse_float=lambda s: ('num', s), parse_int=lambda s: ('num', s))


def num_equal(x, y) -> bool:
    return isinstance(x, tuple) and isinstance(y, tuple) and Decimal(x[1]) == Decimal(y[1])


def compare_inventories(new: Path, old: Path) -> list[str]:
    a, b = exact_json(new), exact_json(old)
    diffs = []
    if len(a) != len(b):
        return [f'{len(a)} objects vs {len(b)} frozen']
    for i, (x, y) in enumerate(zip(a, b)):
        if set(x) != set(y):
            diffs.append(f'object {i}: fields {sorted(set(x) ^ set(y))}')
            continue
        for k in y:
            if x[k] != y[k]:
                kind = 'numerically equal, textually different' if num_equal(x[k], y[k]) else 'different'
                diffs.append(f'object {i} ({y.get("id")}) field {k}: {x[k]!r} vs {y[k]!r} ({kind})')
    return diffs


def same_tree(a: Path, b: Path) -> list[str]:
    fa = {p.relative_to(a).as_posix() for p in a.rglob('*') if p.is_file()}
    fb = {p.relative_to(b).as_posix() for p in b.rglob('*') if p.is_file()}
    out = [f'only in one tree: {sorted(fa ^ fb)[:5]}'] if fa != fb else []
    out += [f'differs: {n}' for n in sorted(fa & fb) if (a / n).read_bytes() != (b / n).read_bytes()]
    return out


def loops_arg(s: str) -> list[int]:
    if '-' in s:
        lo, hi = s.split('-')
        return list(range(int(lo), int(hi) + 1))
    return [int(x) for x in s.split(',')]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--classes', type=Path, required=True)
    ap.add_argument('--threads', default='1,8')
    ap.add_argument('--loops', default='3-7')
    ap.add_argument('--bin', type=Path, default=ROOT / 'bin/gen')
    ap.add_argument('--work', type=Path)
    ap.add_argument('--explain', action='store_true')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    threads = [int(x) for x in a.threads.split(',')]
    loops = loops_arg(a.loops)
    work = a.work or Path(tempfile.mkdtemp(prefix='c8d2_regress_'))
    work.mkdir(parents=True, exist_ok=True)
    legacy = {int(r['L']): r['maps'] for r in json.loads(LEGACY.read_text())}
    rec: dict = dict(schema='c8-d2-gate-1', gate='A-INV-2 regress', classes=str(a.classes), threads=threads,
                     loops=loops, work=str(work), builds=[], sectors={}, threads_identical={}, controls={})
    failures: list[str] = []
    # 1. regenerate
    for t in threads:
        for sector in ('free', 'power'):
            for L in loops:
                out = work / f't{t}' / sector / f'L{L}'
                side = work / f't{t}' / sector / f'L{L}.subgraphs.txt'
                if out.exists():
                    raise SystemExit(f'{out} exists: use a fresh --work directory')
                t0 = time.time()
                r = subprocess.run([str(a.bin / f'build_{sector}'), str(a.classes / f'classes{L}.txt'), str(out),
                                    str(side)], env={**os.environ, 'OMP_NUM_THREADS': str(t)},
                                   capture_output=True, text=True)
                rec['builds'].append(dict(threads=t, sector=sector, L=L, rc=r.returncode,
                                          seconds=round(time.time() - t0, 3), stderr_tail=r.stderr[-300:]))
                if r.returncode != 0:
                    failures.append(f'build_{sector} L{L} t{t} exited {r.returncode}')
                print(f'built {sector} L{L} threads={t} rc={r.returncode} {time.time() - t0:.1f}s', flush=True)
    if failures:
        rec.update(passed=False, failures=failures)
        return finish(rec, a.output)
    base = work / f't{threads[-1]}'
    # 2. thread identity
    for t in threads[:-1]:
        d = same_tree(work / f't{t}', base)
        rec['threads_identical'][f'{t}_vs_{threads[-1]}'] = dict(identical=not d, differences=d[:20])
        if d:
            failures.append(f'outputs differ between {t} and {threads[-1]} threads: {d[:3]}')
    # 3. against the frozen payloads
    for sector in ('free', 'power'):
        for L in loops:
            new, old = base / sector / f'L{L}', FROZEN[sector] / f'L{L}'
            gn = {p.name for p in new.glob('G*.txt')}
            go = {p.name for p in old.glob('G*.txt')}
            row = dict(frozen_gfiles=len(go), new_gfiles=len(gn), same_file_set=gn == go, identical=0,
                       rate_only=0, rate_whitespace_only=0, rate_entries_differing=0, other=[],
                       accepted_relabelling=[])
            if gn != go:
                failures.append(f'{sector} L{L}: G-file sets differ ({sorted(gn ^ go)[:5]})')
            for name in sorted(gn & go, key=lambda s: int(s[1:-4])):
                tn, to = (new / name).read_text(), (old / name).read_text()
                if tn == to:
                    row['identical'] += 1
                    continue
                parts = classify(tn, to)
                legacy_rate_ok = sector == 'free' and L <= 6
                if parts == ['rate line'] and legacy_rate_ok:
                    row['rate_only'] += 1
                    ra, rb = parse_gfile(tn)['rate'].split(), parse_gfile(to)['rate'].split()
                    nd = sum(1 for x, y in zip(ra, rb) if x != y) + abs(len(ra) - len(rb))
                    row['rate_entries_differing'] += nd
                    row['rate_whitespace_only'] += nd == 0
                    continue
                note = None
                if legacy_rate_ok:
                    note = legacy_relabel_equal(tn, to, int(name[1:-4]), L, legacy)
                if note:
                    row['accepted_relabelling'].append(dict(file=name, parts=parts, proof=note))
                else:
                    row['other'].append(dict(file=name, parts=parts if a.explain else ['(run with --explain)']))
            if row['other']:
                failures.append(f'{sector} L{L}: {len(row["other"])} G-files differ beyond the allowed rate lines')
            inv = compare_inventories(new / 'inventory.json', old / 'inventory.json')
            row['inventory_equal'] = not inv
            row['inventory_differences'] = inv[:30]
            row['inventory_bytes_identical'] = (new / 'inventory.json').read_bytes() == (old / 'inventory.json').read_bytes()
            if inv:
                failures.append(f'{sector} L{L}: inventory.json differs field by field ({len(inv)} differences)')
            rec['sectors'][f'{sector}_L{L}'] = row
            print(f'{sector} L{L}: {row["identical"]}/{len(go)} identical, rate-only {row["rate_only"]}, '
                  f'other {len(row["other"])}, inventory equal {not inv}', flush=True)
    # 4. controls for gate A-INV-3(b): subgraph side files
    for L in loops:
        sf, sp = base / 'free' / f'L{L}.subgraphs.txt', base / 'power' / f'L{L}.subgraphs.txt'
        same = sf.read_bytes() == sp.read_bytes()
        rec['controls'][f'side_files_free_eq_power_L{L}'] = same
        if not same:
            failures.append(f'L{L}: the free and power builders classify subgraphs differently')
    if 7 in loops:
        ok = (base / 'free/L7.subgraphs.txt').read_bytes() == (C8D1 / 'L7_inventory.txt').read_bytes()
        rec['controls']['side_file_L7_eq_c8d1_L7_inventory'] = ok
        if not ok:
            failures.append('L7 subgraph side file differs from C8(1) L7_inventory.txt')
    rec.update(passed=not failures, failures=failures)
    rec['free_L3_L6_rate_line_files'] = sum(rec['sectors'].get(f'free_L{L}', {}).get('rate_only', 0) for L in loops if L <= 6)
    rec['free_L3_L6_rate_whitespace_only_files'] = sum(rec['sectors'].get(f'free_L{L}', {}).get('rate_whitespace_only', 0)
                                                       for L in loops if L <= 6)
    return finish(rec, a.output)


def finish(rec: dict, output: Path | None) -> int:
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(rec, indent=1) + '\n')
    print('A-INV-2', 'PASSED' if rec['passed'] else 'FAILED', '; '.join(rec.get('failures', []))[:2000])
    return 0 if rec['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
