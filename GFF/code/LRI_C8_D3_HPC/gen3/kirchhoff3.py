#!/usr/bin/env python3
"""Gate 4: exact Kirchhoff identity on sampled d=3 payloads, independent code (PLAN.md A.3 gate 4). Standard library.

For a kernel with edges e = 0..E-1 (H1's inventory_L.json `edges`, in the builders' bit order) and its masks (the
spanning-tree complements of the payload; popcount L, kernel.hpp:85), the matrix-tree theorem gives
    sum_{m in masks} prod_{e in m} x_e  =  prod_e x_e * det Lred(1/x),
with Lred the weighted Laplacian (edge weights 1/x_e, parallel edges added) with vertex 0's row and column removed.
Both sides are evaluated with exact Fractions at two random rational points per kernel.

Sample (seed 8813, one random.Random drawn in this order): for L8 free, L8 power: the 16 kernels of largest M*T
(ties by id) plus 48 random ones of the rest; for L7 free, L7 power: 8 random ones; all among H1's selection.
Usage: kirchhoff3.py --payload DIR --inventory H1_TREE --output FILE [--loops 7,8] [--sample L:sector:top:random ...]
Exit 0 when every identity holds, 1 when one fails, 2 on bad input.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3common as c  # noqa: E402

SEED = 8813
PLAN = [(8, 'free', 16, 48), (8, 'power', 16, 48), (7, 'free', 0, 8), (7, 'power', 0, 8)]


def det(m: list[list[Fraction]]) -> Fraction:
    """Exact determinant by fraction Gaussian elimination with row swaps."""
    a = [row[:] for row in m]
    n = len(a)
    d = Fraction(1)
    for k in range(n):
        p = next((i for i in range(k, n) if a[i][k] != 0), None)
        if p is None:
            return Fraction(0)
        if p != k:
            a[k], a[p] = a[p], a[k]
            d = -d
        d *= a[k][k]
        for i in range(k + 1, n):
            if a[i][k]:
                f = a[i][k] / a[k][k]
                for j in range(k, n):
                    a[i][j] -= f * a[k][j]
    return d


def identity(n: int, edges: list[tuple[int, int]], masks: list[int], x: list[Fraction]) -> tuple[Fraction, Fraction]:
    lap = [[Fraction(0)] * n for _ in range(n)]
    for (u, v), xe in zip(edges, x):
        w = 1 / xe
        lap[u][u] += w
        lap[v][v] += w
        lap[u][v] -= w
        lap[v][u] -= w
    prod = Fraction(1)
    for xe in x:
        prod *= xe
    rhs = prod * det([row[1:] for row in lap[1:]])
    lhs = Fraction(0)
    for m in masks:
        t = Fraction(1)
        e = 0
        while m:
            if m & 1:
                t *= x[e]
            m >>= 1
            e += 1
        lhs += t
    return lhs, rhs


def pick(rows: dict[int, dict], ids: list[int], top: int, nrand: int, rng: random.Random) -> list[int]:
    by = sorted(ids, key=lambda i: (-rows[i]['masks'] * rows[i]['terms'], i))
    head = by[:top]
    rest = sorted(set(ids) - set(head))
    return head + sorted(rng.sample(rest, min(nrand, len(rest))))


def run(a) -> dict:
    plan = PLAN if not a.sample else [(int(L), s, int(t), int(r)) for L, s, t, r in (x.split(':') for x in a.sample)]
    loops = {int(x) for x in a.loops.split(',')}
    sel = json.loads((Path(a.inventory) / 'selection.json').read_text())
    rng = random.Random(SEED)
    invs: dict[int, dict] = {}
    out: dict = {}
    for L, s, top, nrand in plan:
        if L not in loops:
            continue
        if L not in invs:
            invs[L] = json.loads((Path(a.inventory) / f'inventory_L{L}.json').read_text())
        rows = {r['id']: r for r in invs[L][s]}
        chosen = pick(rows, sel[f'L{L}'][s], top, nrand, rng)
        e, done = [], []
        for gid in chosen:
            r = rows[gid]
            p = Path(a.payload) / f'L{L}_{s}' / f'G{gid}.txt'
            try:
                g = c.parse_gfile(p.read_bytes(), str(p))
            except (OSError, c.Gen3Error) as ex:
                e.append(str(ex))
                continue
            edges = [tuple(x) for x in r['edges']]
            if len(edges) != g.E or g.M != r['masks'] or g.id != gid:
                e.append(f'{p}: E, M or id differ from inventory_L{L}.json')
                continue
            for k in range(2):
                x = [Fraction(rng.randint(1, 997), rng.randint(1, 997)) for _ in range(g.E)]
                lhs, rhs = identity(g.L + 1, edges, g.masks, x)
                if lhs != rhs:
                    e.append(f'{p}: Kirchhoff identity fails at point {k}')
            done.append(gid)
        out[f'L{L}_{s}'] = dict(passed=not e and len(done) == len(chosen), kernels=done, points_per_kernel=2,
                                errors=e[:50], error_count=len(e))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--payload', required=True, help='d=3 payload directories L<L>_<sector>/G<id>.txt')
    ap.add_argument('--inventory', required=True, help='the verified H1 copy')
    ap.add_argument('--loops', default='7,8')
    ap.add_argument('--sample', action='append', help=argparse.SUPPRESS)   # test fixtures: L:sector:top:random
    ap.add_argument('--output', required=True)
    a = ap.parse_args(argv)
    c.refuse_c62d(a.output, 'output')
    try:
        res = run(a)
    except (OSError, KeyError, ValueError) as ex:
        c.die(f'kirchhoff3: {ex}')
    passed = bool(res) and all(v['passed'] for v in res.values())
    c.write_json(a.output, dict(schema='c8-d3-kirchhoff-1', gate='4 Kirchhoff (exact, independent code)', seed=SEED,
                                passed=passed, sectors=res, kernels=sum(len(v['kernels']) for v in res.values())))
    for k, v in res.items():
        print(f'{k}: {"PASS" if v["passed"] else "FAIL"} {len(v["kernels"])} kernels' + ('' if v['passed'] else f' {v["errors"][:3]}'))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
