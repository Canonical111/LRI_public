#!/usr/bin/env python3
"""A-INV-3(k): independent count of compatible log-subgraph families per class (the forest identity).

Reads C8(1)'s L{L}_inventory.txt (header "n NG"; per class a line "id key aut orbit D_G s_G nlog npow", a line
of log-subgraph vertex masks and a line of power-subgraph vertex masks) and counts, for every class, the families
of log subgraphs that are pairwise compatible: nested, or sharing at most one vertex. The empty family is
included. This is independent code: it neither calls nor mirrors the C++ builders, and it starts from C8(1)'s
masks, not from the d=2 builder's own classification.

The totals over all classes reproduce C8(1)'s `forests` (L7_summary.json 873,108; L8_summary.json 11,254,373);
gen/gates.py compares the per-class counts with the d=2 builder's `forests` field for every power-free class.

Usage: python3 -B gen/forest_counts.py INVENTORY [--summary SUMMARY.json] [--jobs N] [--output FILE]"""
from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path


def read_inventory(path: Path) -> list[dict]:
    lines = path.read_text().split('\n')
    n, ng = (int(x) for x in lines[0].split())
    rows = []
    for i in range(ng):
        head = lines[1 + 3 * i].split()
        logs = [int(x) for x in lines[2 + 3 * i].split()]
        powers = [int(x) for x in lines[3 + 3 * i].split()]
        if len(head) != 8 or int(head[0]) != i or len(logs) != int(head[6]) or len(powers) != int(head[7]):
            raise ValueError(f'{path}: malformed class {i}')
        rows.append(dict(id=i, key=head[1], D_G=int(head[4]), s_G=int(head[5]), logs=logs, powers=powers))
    if any(x.strip() for x in lines[1 + 3 * ng:]):
        raise ValueError(f'{path}: trailing data after {ng} classes')
    return rows


def compatible(a: int, b: int) -> bool:
    common = a & b
    return common == a or common == b or bin(common).count('1') <= 1


def count_families(masks: list[int]) -> int:
    """Number of sets of pairwise compatible masks, the empty set included."""
    k = len(masks)
    later = [0] * k  # later[i]: bitset of indices j > i compatible with i
    for i in range(k):
        for j in range(i + 1, k):
            if compatible(masks[i], masks[j]):
                later[i] |= 1 << j
    total = 0
    stack = [(1 << k) - 1]  # candidate sets; each popped set counts one family (its parent family)
    while stack:
        cand = stack.pop()
        total += 1
        while cand:
            low = cand & -cand
            i = low.bit_length() - 1
            cand ^= low
            stack.append(cand & later[i])
    return total


def _count(row: dict) -> tuple[int, int]:
    return row['id'], count_families(row['logs'])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('inventory', type=Path)
    ap.add_argument('--summary', type=Path, help="C8(1) L*_summary.json: its 'forests' and 'classes' must match")
    ap.add_argument('--jobs', type=int, default=1)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    rows = read_inventory(a.inventory)
    if a.jobs > 1:
        with Pool(a.jobs) as pool:
            counts = dict(pool.map(_count, rows, chunksize=64))
    else:
        counts = dict(map(_count, rows))
    total = sum(counts.values())
    rec = dict(schema='c8-d2-forest-counts-1', inventory=str(a.inventory), classes=len(rows), total=total,
               power_free_classes=sum(1 for r in rows if not r['powers']),
               per_class={str(i): counts[i] for i in sorted(counts)})
    ok = True
    if a.summary:
        s = json.loads(a.summary.read_text())
        rec['summary'] = dict(classes=s['classes'], forests=s['forests'])
        ok = s['classes'] == len(rows) and s['forests'] == total
    rec['passed'] = ok
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec) + '\n')
    print(f'{a.inventory.name}: {len(rows)} classes, {total} compatible log-subgraph families'
          + (f' (summary {rec["summary"]["forests"]}: {"match" if ok else "MISMATCH"})' if a.summary else ''))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
