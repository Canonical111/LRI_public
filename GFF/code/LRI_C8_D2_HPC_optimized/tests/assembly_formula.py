#!/usr/bin/env python3
"""Independent exact-rational checks of the C8 regulator-dependent assembly.

The two implementations are a univariate fixed-point substitution and a
bivariate Lagrange coefficient extraction. All arithmetic in their comparison
uses fractions.Fraction. An optional production-module check also exercises
tools/assemble.py if that module is present.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as Q
import importlib.util
import json
from math import comb
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[1]
ORDER = 8


def mul(a, b, size=ORDER + 1):
    p = [Q(0)] * size
    for i, x in enumerate(a[:size]):
        for j, y in enumerate(b[:size - i]):
            p[i + j] += x * y
    return p


def fixed_point(b, c, order=ORDER):
    """Compute Delta=1-eps/2+gamma(g*(eps),eps) by formal substitution."""
    size = order + 1
    g = [Q(0)] * size
    for _ in range(size):
        powers = [Q(1)] + [Q(0)] * order
        residual = [Q(0)] * size
        for loop in range(1, size):
            powers = mul(powers, g, size)
            if loop >= 2:
                term = mul(b[loop], powers, size)
                residual = [x + y for x, y in zip(residual, term)]
        residual[1] -= 1
        g = [-x / 3 for x in residual]
    powers = [Q(1)] + [Q(0)] * order
    result = [Q(0)] * size
    for loop in range(1, size):
        powers = mul(powers, g, size)
        term = mul(c[loop], powers, size)
        result = [x + y for x, y in zip(result, term)]
    result[0] += 1
    result[1] -= Q(1, 2)
    return result


def bivariate_mul(a, b, order=ORDER):
    ans = {}
    for (g, z), x in a.items():
        for (h, w), y in b.items():
            if g + h + z + w <= order - 1:
                key = (g + h, z + w)
                ans[key] = ans.get(key, Q(0)) + x * y
    return {key: value for key, value in ans.items() if value}


def lagrange(b, c, order=ORDER):
    """C_n=-delta_n1/2+sum_k [g^(k-1)z^(n-k)] gamma' B^(-k)/k."""
    d = {(loop - 1, j): Q(value, 3) for loop, coefficients in b.items() if loop >= 2
         for j, value in enumerate(coefficients) if value and loop - 1 + j < order}
    derivative = {(loop - 1, j): loop * value for loop, coefficients in c.items()
                  for j, value in enumerate(coefficients) if value and loop - 1 + j < order}
    powers = [{(0, 0): Q(1)}]
    for _ in range(1, order):
        powers.append(bivariate_mul(powers[-1], d, order))
    result = [Q(1)] + [Q(0)] * order
    result[1] -= Q(1, 2)
    for k in range(1, order + 1):
        inverse = {}
        for m in range(k):
            scale = Q((-1) ** m * comb(k + m - 1, m), 3 ** k)
            for key, value in powers[m].items():
                inverse[key] = inverse.get(key, Q(0)) + scale * value
        product = bivariate_mul(derivative, inverse, order)
        for n in range(k, order + 1):
            result[n] += product.get((k - 1, n - k), Q(0)) / k
    return result


def random_jets(rng, order=ORDER):
    b, c = {1: [Q(3)]}, {1: [Q(1)]}
    for loop in range(2, order + 1):
        b[loop] = [Q(rng.randint(-9, 9), rng.randint(1, 7)) for _ in range(order - loop + 1)]
        c[loop] = [Q(rng.randint(-9, 9), rng.randint(1, 7)) for _ in range(order - loop + 1)]
    return b, c


def copy_jets(b, c):
    return {loop: values.copy() for loop, values in b.items()}, {loop: values.copy() for loop, values in c.items()}


def run(cases=24, production_module=None):
    rng = random.Random(82140377)
    for _ in range(cases):
        b, c = random_jets(rng)
        exact = fixed_point(b, c)
        assert exact == lagrange(b, c), "Fixed point differs from bivariate Lagrange extraction"

    b, c = random_jets(rng)
    base = fixed_point(b, c)
    bb, cc = copy_jets(b, c)
    bb[8][0] += 1
    b8_sensitivity = fixed_point(bb, cc)[8] - base[8]
    assert b8_sensitivity == -Q(1, 19683)
    bb, cc = copy_jets(b, c)
    cc[8][0] += 1
    c8_sensitivity = fixed_point(bb, cc)[8] - base[8]
    assert c8_sensitivity == Q(1, 6561)

    # A C7 top-channel zero generally contributes at the next order.
    bb, cc = copy_jets(b, c)
    bb[7][0] += 3
    cc[7][0] += 1
    shifted = fixed_point(bb, cc)
    assert shifted[7] == base[7]
    old_zero_contribution = shifted[8] - base[8]
    assert old_zero_contribution == 2 * (b[2][0] - 3 * c[2][0]) / 19683

    # The newly needed two-loop z^6 coefficient affects C8 directly.
    bb, cc = copy_jets(b, c)
    bb[2][6] += 6
    cc[2][6] += 1
    assert fixed_point(bb, cc)[8] - base[8] == -Q(1, 9)

    # At fixed loops one through four, the complete vector C0..C8 is affine
    # in loops five through eight: two such insertions begin at order nine.
    u, v = [], []
    for _ in range(2):
        db, dc = random_jets(rng)
        for loop in range(1, 5):
            db[loop] = [Q(0)] * len(db[loop])
            dc[loop] = [Q(0)] * len(dc[loop])
        u.append(db)
        v.append(dc)

    def shift(directions):
        bb, cc = copy_jets(b, c)
        for j in directions:
            for loop in range(5, 9):
                bb[loop] = [x + y for x, y in zip(bb[loop], u[j][loop])]
                cc[loop] = [x + y for x, y in zip(cc[loop], v[j][loop])]
        return fixed_point(bb, cc)

    p, q, pq = shift([0]), shift([1]), shift([0, 1])
    assert all(x - y - z + w == 0 for x, y, z, w in zip(pq, p, q, base))

    production_result = None
    if production_module is not None:
        import numpy as np
        production_module = Path(production_module)
        sys.path.insert(0, str(production_module.parent))
        spec = importlib.util.spec_from_file_location("c8_production_assembly", production_module)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        b2 = json.loads((production_module.parent.parent / "inputs" / "two_loop.json").read_text())["B2"]
        differences = []
        for _ in range(cases):
            b, c = random_jets(rng)
            b[2] = list(map(Q, b2))
            c[2] = [x / 6 for x in b[2]]
            values = {loop: np.asarray([float(x) for x in b[loop] + c[loop]]) for loop in range(3, 9)}
            observed = module.coefficients(values)
            expected = np.asarray(list(map(float, lagrange(b, c))))
            assert observed.shape == (9,)
            relative = float(np.max(np.abs(observed - expected) / np.maximum(1., np.abs(expected))))
            differences.append(relative)
            assert relative < 2e-11, f"Production assembly mismatch: {relative}"
        production_result = {"cases": cases, "maximum_normalized_difference": max(differences)}

    return {"status": "passed", "order": ORDER, "exact_rational_cases": cases,
            "fixed_point_equals_bivariate_lagrange": True,
            "dC8_db8_0": str(b8_sensitivity), "dC8_dc8_0": str(c8_sensitivity),
            "top_channel": "(3*c8_0-b8_0)/19683",
            "C7_zero_channel_reappears_at_C8": True,
            "new_two_loop_z6_required": True, "affine_in_loops_5_through_8": True,
            "production_assembly": production_result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=24)
    parser.add_argument("--production-module", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.cases < 1:
        raise ValueError("At least one rational case required")
    report = run(args.cases, args.production_module)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
