#!/usr/bin/env python3
"""Unlabelled graph classes behind the residue certificate (new check for the public edition, 2026-10-13).

Enumerates the labelled four- and five-loop graphs with the package's own generator
(verification/source/ising_five_loop.graphs), reduces them to unlabelled classes (canonical word = the
lexicographically smallest upper-triangular edge word over all vertex relabellings), and checks the
statements of note Sections 12, 13 and Appendix A:

  * four loops: 27 classes = 26 certificate rows + 1 primitive class (the wheel);
  * five loops: 129 classes = 92 certificate rows + 6 wheel-insertion classes + 3 primitive classes
    + 28 classes with 3 w_2 - w_4 = 0, pairwise disjoint;
  * every certificate row's class index, edge word and RG weights omega_b = L(-1)^L w_4/|Aut G|,
    omega_c = L(-1)^L w_2/|Aut G| agree exactly with the enumeration;
  * the six wheel-insertion classes of the Section 12 table (index, word, |Aut G|, d_G) are the classes
    that contain a four-loop wheel subgraph or a one-loop bubble whose contraction is the wheel, and no
    certificate row has that structure; the three primitive classes have no proper subgraph with
    e = 2v - 2 internal edges (no logarithmically divergent four-point subgraph).

Writes the result as JSON to the path given as first argument. Pure Python + NumPy, about 10 s on one core.
"""
import itertools
import json
import math
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent / 'verification'
sys.path.insert(0, str(ROOT / 'source'))
import ising_five_loop as original  # noqa: E402

WHEEL4 = '0111111011'


def classes(n):
    gg = original.graphs(n)
    pairs = list(itertools.combinations(range(n), 2))
    idx = {p: k for k, p in enumerate(pairs)}
    M = np.array([g for g, _, _ in gg], dtype=np.int64)
    best = None
    for perm in itertools.permutations(range(n)):
        cols = [idx[tuple(sorted((perm[i], perm[j])))] for i, j in pairs]
        P = np.zeros_like(M)
        P[:, cols] = M
        code = np.zeros(len(M), dtype=np.int64)
        for k in range(len(pairs)):
            code = code * 4 + P[:, k]          # multiplicities are <= 3
        best = code if best is None else np.minimum(best, code)
    groups = {}
    for k, c in enumerate(best.tolist()):
        groups.setdefault(c, []).append(k)
    out = []
    for c in sorted(groups):                  # sorted canonical words = canonical class index
        ks = groups[c]
        weights = {(gg[k][1], gg[k][2]) for k in ks}
        assert len(weights) == 1, 'weights must be class invariant'
        wa, wb = weights.pop()
        out.append(dict(word=np.base_repr(c, 4).zfill(len(pairs)), aut=math.factorial(n) // len(ks),
                        w4=wa, w2=wb, labelled=len(ks)))
    return out, len(gg)


def canon5(m5):
    pairs5 = list(itertools.combinations(range(5), 2))
    idx = {p: k for k, p in enumerate(pairs5)}
    best = None
    for perm in itertools.permutations(range(5)):
        w = [0] * 10
        for k, (i, j) in enumerate(pairs5):
            w[idx[tuple(sorted((perm[i], perm[j])))]] = m5[k]
        s = ''.join(map(str, w))
        best = s if best is None or s < best else best
    return best


PAIRS6 = list(itertools.combinations(range(6), 2))
PAIRS5 = list(itertools.combinations(range(5), 2))


def m6(word, a, b):
    return int(word[PAIRS6.index(tuple(sorted((a, b))))])


def has_wheel_subgraph(word):
    for S in itertools.combinations(range(6), 5):
        sub = [m6(word, S[a], S[b]) for a, b in PAIRS5]
        if sum(sub) == 8 and canon5(sub) == WHEEL4:
            return True
    return False


def bubble_contracts_to_wheel(word):
    for a, b in PAIRS6:
        if m6(word, a, b) != 2:
            continue
        verts = ['x'] + [v for v in range(6) if v not in (a, b)]
        sub = []
        for i, j in PAIRS5:
            vi, vj = verts[i], verts[j]
            sub.append(m6(word, a, vj) + m6(word, b, vj) if vi == 'x' else m6(word, vi, vj))
        if sum(sub) == 8 and canon5(sub) == WHEEL4:
            return True
    return False


def primitive(word, n):
    pairs = list(itertools.combinations(range(n), 2))
    m = [int(x) for x in word]
    for v in range(2, n):
        for S in itertools.combinations(range(n), v):
            if sum(m[k] for k, (i, j) in enumerate(pairs) if i in S and j in S) == 2 * v - 2:
                return False
    return True


def main():
    t0 = time.time()
    cert = json.loads((ROOT / 'inputs' / 'residue_certificate.json').read_text())
    res = {}
    for n in (5, 6):
        L = n - 1
        cl, nlab = classes(n)
        rows = cert[str(L)]
        sgn = (-1) ** L
        rows_ok = all(
            cl[r['i']]['word'] == r['word']
            and Fraction(r['wb']) == L * sgn * cl[r['i']]['w4'] / cl[r['i']]['aut']
            and Fraction(r['wc']) == L * sgn * cl[r['i']]['w2'] / cl[r['i']]['aut'] for r in rows)
        in_cert = {r['i'] for r in rows}
        zero = [k for k, c in enumerate(cl) if 3 * c['w2'] - c['w4'] == 0]
        rest = [k for k in range(len(cl)) if k not in in_cert and k not in zero]
        prim = [k for k in rest if primitive(cl[k]['word'], n)]
        r = dict(labelled_graphs=nlab, classes=len(cl), certificate_rows=len(rows),
                 certificate_rows_match_enumeration=rows_ok, zero_weight_classes=len(zero),
                 zero_weight_labelled_graphs=sum(cl[k]['labelled'] for k in zero),
                 certificate_rows_with_zero_weight=len(in_cert & set(zero)),
                 remaining_classes=rest, primitive_classes=prim,
                 primitive_words=[cl[k]['word'] for k in prim])
        if L == 5:
            wheel = [k for k in rest if k not in prim]
            r['wheel_insertion_classes'] = {str(k): [cl[k]['word'], cl[k]['aut'],
                                                     str(-5 * (3 * cl[k]['w2'] - cl[k]['w4']) / cl[k]['aut'])]
                                            for k in wheel}
            r['wheel_insertions_have_wheel_structure'] = all(
                has_wheel_subgraph(cl[k]['word']) or bubble_contracts_to_wheel(cl[k]['word']) for k in wheel)
            r['certificate_rows_with_wheel_structure'] = sum(
                has_wheel_subgraph(x['word']) or bubble_contracts_to_wheel(x['word']) for x in rows)
            r['primitive_classes_have_wheel_structure'] = sum(
                has_wheel_subgraph(cl[k]['word']) or bubble_contracts_to_wheel(cl[k]['word']) for k in prim)
        else:
            r['primitive_is_the_wheel'] = [cl[k]['word'] for k in prim] == [WHEEL4]
        res[str(L)] = r
    res['elapsed_seconds'] = time.time() - t0
    Path(sys.argv[1]).write_text(json.dumps(res, indent=2) + '\n')
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    main()
