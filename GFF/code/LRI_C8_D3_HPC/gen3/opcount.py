#!/usr/bin/env python3
"""Worker-independent op counts of the kernel's prepare(), re-derived from payload text (PLAN.md A.3 gate 2(a)).

Vendored from the C63d recon (LRI_C8_D3_HPC_loop/recon/cost_d3/opcount.py, byte copy at c8-rb; recon/c7d3_kernel.md:
357-360) and adapted for the gates: `stats` is the recon's re-derivation, unchanged in what it counts:
  products = the union of the lowest-bit peeling chains of the M spanning-tree-complement masks,
  addends  = the nodes of the prefix trie over the T forest terms' monomial-index lists,
and A = products + addends is the op count. The recon's split bound (7 + 4096*64 tokens) is too small at L8 (up to
4,032 masks and 280 terms of up to 4,032 indices), so the payload is split whole.

Commands:
  c7d3     --inputs DIR --sizes-dir DIR     the recon's original check: every C7(3) kernel of DIR/inventory.json and
                                            DIR/packs/, against size_probe's sizes_L{3..7}.csv in --sizes-dir
                                            (cd3:opcount:11: 0 mismatches on all 3,511)
  compare  --payload DIR --sizes DIR --inventory H1_TREE [--loops 7,8] --output FILE
                                            gate 2(a): every selected L7/L8 kernel (H1's selection.json) of the d=3
                                            stage DIR (L<L>_<sector>/G<id>.txt) has (M, T, products, addends) equal to
                                            size_probe's sizes_L<L>.csv row (its status the kernel's sector), and the
                                            selection counts equal 2,441 + 709 (L7) and 16,064 (248 primitive) +
                                            4,336 (L8).
Exit 0 when every check passes, 1 when one fails, 2 on bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3common as c  # noqa: E402

COUNTS = {7: dict(free=2441, power=709), 8: dict(free=16064, power=4336)}
PRIMITIVE_L8 = 248
KEYS = ('M', 'T', 'products', 'addends')


def stats(payload: str) -> dict:
    """(M, T, products, addends) of one G-file's text, as the kernel's prepare() builds them."""
    toks = payload.split()
    L, M, T = int(toks[1]), int(toks[5]), int(toks[6])
    E = 2 * L
    i = 7
    masks = [int(x) for x in toks[i:i + M]]
    i += M
    prods = set()
    for m in masks:
        while m and m not in prods:
            prods.add(m)
            m &= m - 1
    children = [{}]
    for _ in range(T):
        n = int(toks[i])
        i += 1
        ids = [int(x) for x in toks[i:i + n]]
        i += n + E
        at = 0
        for m in ids:
            ch = children[at].get(m)
            if ch is None:
                ch = len(children)
                children[at][m] = ch
                children.append({})
            at = ch
    return dict(M=M, T=T, products=len(prods), addends=len(children) - 1)


def read_sizes(p: Path) -> dict[int, dict]:
    with open(p, newline='') as f:
        rows = {int(r['id']): r for r in csv.DictReader(f)}
    if not rows:
        c.die(f'{p}: empty')
    return rows


def cmd_c7d3(a) -> int:
    root = Path(a.inputs)
    inv = json.loads((root / 'inventory.json').read_text())
    tot = bad = 0
    for s in ('free', 'power'):
        for L in sorted(inv[s], key=int):
            S = read_sizes(Path(a.sizes_dir) / f'sizes_L{L}.csv')
            nb = 0
            with open(root / f'packs/{s}_L{L}.pack', 'rb') as f:
                for r in inv[s][L]:
                    f.seek(r['offset'])
                    st = stats(f.read(r['length']).decode())
                    p = S[r['id']]
                    nb += any(int(p[k]) != st[k] for k in KEYS)
            tot += len(inv[s][L])
            bad += nb
            print(f'{s:5s} L{L}: {len(inv[s][L]):5d} payloads; size_probe (M, T, products, addends) mismatches: {nb}')
    print(f'all L3-L7 C7(3) payloads: {tot}; mismatches {bad}')
    return 0 if bad == 0 else 1


def cmd_compare(a) -> int:
    loops = [int(x) for x in a.loops.split(',')]
    sel = json.loads((Path(a.inventory) / 'selection.json').read_text())
    res = {}
    for L in loops:
        sizes = read_sizes(Path(a.sizes) / f'sizes_L{L}.csv')
        for s in ('free', 'power'):
            e = []
            ids = sel[f'L{L}'][s]
            want = (a.expect_counts or {}).get(f'L{L}_{s}', COUNTS.get(L, {}).get(s))
            if want is not None and len(ids) != want:
                e.append(f'selection L{L} {s}: {len(ids)} kernels, expected {want}')
            prim = 0
            A = []
            for gid in ids:
                p = Path(a.payload) / f'L{L}_{s}' / f'G{gid}.txt'
                try:
                    st = stats(p.read_text())
                except (OSError, ValueError, IndexError) as ex:
                    e.append(f'{p}: unreadable ({ex})')
                    continue
                row = sizes.get(gid)
                if row is None:
                    e.append(f'{p}: id {gid} not in sizes_L{L}.csv')
                    continue
                if row['status'] != s:
                    e.append(f'{p}: size_probe status {row["status"]!r}, expected {s!r}')
                diff = [k for k in KEYS if int(row[k]) != st[k]]
                if diff:
                    e.append(f'{p}: ' + ', '.join(f'{k} {st[k]} != size_probe {row[k]}' for k in diff))
                prim += row['primitive'] == '1'
                A.append(st['products'] + st['addends'])
            if L == 8 and s == 'free' and a.expect_counts is None and prim != PRIMITIVE_L8:
                e.append(f'L8 free: {prim} primitive kernels, expected {PRIMITIVE_L8}')
            res[f'L{L}_{s}'] = dict(passed=not e, kernels=len(ids), primitive=prim, op_count_mean=(sum(A) / len(A)) if A else None,
                                    op_count_max=max(A) if A else None, errors=e[:50], error_count=len(e))
    passed = all(v['passed'] for v in res.values())
    c.write_json(a.output, dict(schema='c8-d3-opcount-1', gate='2(a) census and op counts', passed=passed, sectors=res))
    for k, v in res.items():
        print(f'{k}: {"PASS" if v["passed"] else "FAIL"} kernels {v["kernels"]} A mean {v["op_count_mean"]} max {v["op_count_max"]}'
              + ('' if v['passed'] else f' {v["errors"][:3]}'))
    return 0 if passed else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('c7d3')
    p.add_argument('--inputs', required=True)
    p.add_argument('--sizes-dir', required=True)
    q = sub.add_parser('compare')
    q.add_argument('--payload', required=True)
    q.add_argument('--sizes', required=True, help='directory with size_probe sizes_L<L>.csv')
    q.add_argument('--inventory', required=True, help='the verified H1 copy (selection.json)')
    q.add_argument('--loops', default='7,8')
    q.add_argument('--expect-counts', type=json.loads, help=argparse.SUPPRESS)   # test fixtures only
    q.add_argument('--output', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'compare':
        c.refuse_c62d(a.output, 'output')
    return {'c7d3': cmd_c7d3, 'compare': cmd_compare}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
