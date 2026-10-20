#!/usr/bin/env python3
"""Gate 2(b): the exact weights of every L7 and L8 class (PLAN.md A.3 gate 2(b), A-INV-3). Standard library only.

w_A and w_B multiply every row (c7d3_integrate.cpp:59) and decide the s_G = 4 exclusion, so they are recomputed with
exact Fractions from each class's key and automorphism count in classes{7,8}.txt (re-coded here from the logic of
reference/c8d1_gen/zero_dim_check.py:44-52, not imported):
  den = aut * prod_e m_e! * prod_v (4 - d_v)!,   s_G = sum_v (4 - d_v)(3 - d_v),   w_A = 24/den,   w_B = w_A s_G / 12,
with m_e the multiplicity of vertex pair e (2 key bits per pair, pairs (a,b), a < b, in lexicographic order) and d_v
the degrees. Checks, per L in {7, 8}:
  - H1's inventory_L.json lists every class of classesL.txt in order, in both sectors, with id, key, orbit, the exact
    integers `denominator` (= den) and `mass_numerator` (= s_G), and floats wa, wb within one binary64 ulp of w_A, w_B
    (|x - w| <= 2^-52 |w| for the binary64 value x a JSON reader gets; the record counts how many are the correctly
    rounded double), and their text within long-double rounding (2^-63 relative; H1 prints long doubles);
  - every d=3 payload header's wa/wb strings equal w_A, w_B to long-double rounding (|x - w| <= 2^-63 |w|, and exactly
    for dyadic w), for the payloads given with --payload (directories <stem>/G<id>.txt, stem L<L>_<sector>);
  - s_G = 4 <=> 3 w_B = w_A exactly;
  - selection.json: the L7 sets are all finite kernels, the L8 sets exactly the finite kernels with s_G != 4;
  - at L8, sum w_A = 49985915/768 and sum w_B = 33994099/6912 over H1's 26,540 classes.
Usage: weights_check.py --classes DIR --inventory H1_TREE [--payload DIR] [--loops 7,8] --output FILE
       [--expect-sums L:A_NUM/A_DEN:B_NUM/B_DEN] (test fixtures only; the gate uses the constants above)
Exit 0 when every check passes, 1 when one fails, 2 on bad input.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from fractions import Fraction
from math import factorial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3common as c  # noqa: E402

SUMS = {8: (Fraction(49985915, 768), Fraction(33994099, 6912))}
SECTORS = ('free', 'power')


def read_classes(p: Path) -> tuple[int, list[tuple[int, int, int]]]:
    t = p.read_text().split()
    if len(t) < 2:
        c.die(f'{p}: truncated header')
    n, ng = int(t[0]), int(t[1])
    if len(t) != 2 + 3 * ng:
        c.die(f'{p}: {len(t) - 2} tokens for {ng} classes (3 per class expected)')
    return n, [(int(t[2 + 3 * i]), int(t[3 + 3 * i]), int(t[4 + 3 * i])) for i in range(ng)]


def exact(n: int, key: int, aut: int) -> tuple[int, int, Fraction, Fraction]:
    deg = [0] * n
    den = aut
    k = 0
    for a in range(n):
        for b in range(a + 1, n):
            m = key >> (2 * k) & 3
            k += 1
            den *= factorial(m)
            deg[a] += m
            deg[b] += m
    if key >> (2 * k):
        raise c.Gen3Error(f'key {key}: bits beyond the {k} vertex pairs of n = {n}')
    if any(d > 4 for d in deg):
        raise c.Gen3Error(f'key {key}: a vertex of degree > 4')
    sg = sum((4 - d) * (3 - d) for d in deg)
    for d in deg:
        den *= factorial(4 - d)
    wa = Fraction(24, den)
    return den, sg, wa, wa * sg / 12


def dyadic(w: Fraction) -> bool:
    q = w.denominator
    return q & (q - 1) == 0


def within(x: Fraction, w: Fraction, bits: int) -> bool:
    return abs(x - w) <= abs(w) / (1 << bits) if w else x == 0


def header_weights(p: Path) -> tuple[str, str, int]:
    with open(p, 'rb') as f:
        head = f.readline().split()
    if len(head) != 7 or head[0] not in (b'C7D3GRAPH1', b'C7D2GRAPH1'):
        raise c.Gen3Error(f'{p}: not a G-file header')
    return head[3].decode(), head[4].decode(), int(head[2])


def check(a) -> dict:
    loops = [int(x) for x in a.loops.split(',')]
    sums = dict(SUMS)
    for spec in a.expect_sums or []:
        L, A, B = spec.split(':')
        sums[int(L)] = (Fraction(A), Fraction(B))
    inv_dir = Path(a.inventory)
    sel = json.loads((inv_dir / 'selection.json').read_text())
    out: dict = {}
    for L in loops:
        e: list[str] = []
        n, rows = read_classes(Path(a.classes) / f'classes{L}.txt')
        if n != L + 1:
            e.append(f'classes{L}.txt: n = {n}, expected {L + 1}')
        inv = json.loads((inv_dir / f'inventory_L{L}.json').read_text(), parse_float=Decimal)
        if inv.get('L') != L:
            e.append(f'inventory_L{L}.json: L = {inv.get("L")}')
        sa = sb = Fraction(0)
        n_round = dict(wa=0, wb=0)
        worst = dict(wa=Fraction(0), wb=Fraction(0))
        sg4 = 0
        finite = {s: set() for s in SECTORS}
        weights = {}
        sgs = {}
        for s in SECTORS:
            if len(inv.get(s, [])) != len(rows):
                e.append(f'inventory_L{L}.json {s}: {len(inv.get(s, []))} rows, classes{L}.txt has {len(rows)}')
        for i, (key, aut, orbit) in enumerate(rows):
            den, sg, wa, wb = exact(n, key, aut)
            weights[i] = (wa, wb)
            sgs[i] = sg
            sa += wa
            sb += wb
            if (sg == 4) != (3 * wb == wa):
                e.append(f'L{L} class {i}: s_G = {sg} but 3 w_B {"=" if 3 * wb == wa else "!="} w_A')
            sg4 += sg == 4
            for s in SECTORS:
                if i >= len(inv.get(s, [])):
                    continue
                r = inv[s][i]
                bad = [k for k, v in (('id', i), ('L', L), ('key', key), ('orbit', orbit), ('denominator', den),
                                      ('mass_numerator', sg)) if r.get(k) != v]
                if bad:
                    e.append(f'L{L} {s} class {i}: {", ".join(f"{k} {r.get(k)!r} != {dict(id=i, L=L, key=key, orbit=orbit, denominator=den, mass_numerator=sg)[k]}" for k in bad)}')
                for nm, w in (('wa', wa), ('wb', wb)):
                    text = Fraction(r.get(nm))          # the JSON text, exactly (H1 prints long doubles, 22 digits)
                    x = Fraction(float(text))           # what a binary64 JSON reader gets
                    if not within(x, w, 52):
                        e.append(f'L{L} {s} class {i}: {nm} {r.get(nm)} differs from {w} by more than one binary64 ulp')
                    if not within(text, w, 63):
                        e.append(f'L{L} {s} class {i}: {nm} text {r.get(nm)} is not {w} to long-double rounding')
                    n_round[nm] += float(x) == float(w)
                    if w:
                        worst[nm] = max(worst[nm], abs(text - w) / abs(w))
                if r.get('status') == 'finite-kernel':
                    finite[s].add(i)
        # selection.json
        for s in SECTORS:
            want = sorted(finite[s]) if L == 7 else sorted(i for i in finite[s] if sgs[i] != 4)
            got = sel.get(f'L{L}', {}).get(s)
            if got != want:
                e.append(f'selection.json L{L} {s}: {len(got or [])} ids differ from the {len(want)} '
                         f'{"finite kernels" if L == 7 else "finite kernels with s_G != 4"}')
        if L in sums:
            A, B = sums[L]
            if sa != A or sb != B:
                e.append(f'L{L}: sum w_A = {sa}, sum w_B = {sb}; expected {A}, {B}')
        # payload headers
        hdr = dict(checked=0, exact=0)
        if a.payload:
            for s in SECTORS:
                d = Path(a.payload) / f'L{L}_{s}'
                if not d.is_dir():
                    e.append(f'{d}: missing payload directory')
                    continue
                for p in sorted(d.glob('G*.txt')):
                    try:
                        xa, xb, gid = header_weights(p)
                    except c.Gen3Error as ex:
                        e.append(str(ex))
                        continue
                    if gid not in weights or p.name != f'G{gid}.txt':
                        e.append(f'{p}: id {gid} is not a class of classes{L}.txt or differs from the file name')
                        continue
                    for nm, x, w in (('wa', xa, weights[gid][0]), ('wb', xb, weights[gid][1])):
                        fx = Fraction(Decimal(x))
                        if (dyadic(w) and fx != w) or not within(fx, w, 63):
                            e.append(f'{p}: header {nm} {x} is not {w} to long-double rounding (2^-63 relative)')
                        hdr['exact'] += fx == w
                    hdr['checked'] += 1
        out[f'L{L}'] = dict(passed=not e, classes=len(rows), sum_wa=str(sa), sum_wb=str(sb), sums_checked=L in sums,
                            s_g_4=sg4, finite={s: len(finite[s]) for s in SECTORS},
                            inventory_binary64_correctly_rounded=n_round,
                            inventory_text_worst_relative_error={k: float(v) for k, v in worst.items()},
                            payload_headers=hdr, errors=e[:50], error_count=len(e))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--classes', required=True, help='reference/c8d1_inputs8 (classes7.txt, classes8.txt)')
    ap.add_argument('--inventory', required=True, help="the verified H1 copy (inventory_L*.json, selection.json)")
    ap.add_argument('--payload', help='d=3 payload directories L<L>_<sector>/G<id>.txt (the d3 stage)')
    ap.add_argument('--loops', default='7,8')
    ap.add_argument('--expect-sums', action='append', help=argparse.SUPPRESS)
    ap.add_argument('--output', required=True)
    a = ap.parse_args(argv)
    c.refuse_c62d(a.output, 'output')
    try:
        res = check(a)
    except (c.Gen3Error, OSError, ValueError, KeyError, TypeError) as ex:
        c.die(f'weights_check: {ex}')
    passed = all(v['passed'] for v in res.values())
    c.write_json(a.output, dict(schema='c8-d3-weights-1', gate='2(b) exact weights', passed=passed, loops=res))
    for k, v in res.items():
        print(f'{k}: {"PASS" if v["passed"] else "FAIL"} classes {v["classes"]} sum_wa {v["sum_wa"]} sum_wb {v["sum_wb"]}'
              + ('' if v['passed'] else f' {v["errors"][:3]}'))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
