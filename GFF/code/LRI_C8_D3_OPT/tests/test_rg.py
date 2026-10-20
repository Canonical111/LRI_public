#!/usr/bin/env python3
"""Independent exact rational Lagrange inversion and C8 assembly checks."""
from fractions import Fraction as F
import json
from pathlib import Path
import random
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from rg import coefficients, fixed_point_series, high_loop_affine, top_loop_weights


def bivariate_product(a, b, max_g, max_z):
    out = {}
    for (i, j), x in a.items():
        for (k, ell), y in b.items():
            if i+k <= max_g and j+ell <= max_z:
                key = (i+k, j+ell)
                out[key] = out.get(key, F(0))+x*y
    return out


def lagrange(b, c, order=8):
    """[epsilon^n] gamma = sum_k [g^(k-1)z^(n-k)] gamma' B^(-k)/k."""
    out = [F(3, 2), -F(1, 2)]+[F(0)]*(order-1)
    for k in range(1, order+1):
        max_g, max_z = k-1, order-k
        delta = {(loop-1, j): x/3 for loop in range(2, order+1)
                 for j, x in enumerate(b.get(loop, [])) if x and loop-1 <= max_g and j <= max_z}
        derivative = {(loop-1, j): loop*x for loop in range(1, order+1)
                      for j, x in enumerate(c.get(loop, [])) if x and loop-1 <= max_g and j <= max_z}
        power, binomial = {(0, 0): F(1)}, F(1)
        for degree in range(max_g+1):
            if degree:
                power = bivariate_product(power, delta, max_g, max_z)
                binomial *= F(-k-degree+1, degree)
            product = bivariate_product(power, derivative, max_g, max_z)
            for j in range(max_z+1):
                out[k+j] += binomial*product.get((max_g, j), F(0))/(k*3**k)
    return out


def random_jets(rng, order, constant=False):
    b, c = {1: [F(3)]}, {1: [F(1)]}
    for loop in range(2, order+1):
        slots = order-loop+1
        b[loop] = [F(rng.randint(-8, 8), rng.randint(1, 7)) if not constant or j == 0 else F(0) for j in range(slots)]
        c[loop] = [F(rng.randint(-8, 8), rng.randint(1, 7)) if not constant or j == 0 else F(0) for j in range(slots)]
    return b, c


class RGChecks(unittest.TestCase):
    def test_exact_independent_lagrange(self):
        rng = random.Random(30803428)
        for i in range(64):
            b, c = random_jets(rng, 8, constant=i >= 48)
            self.assertEqual(fixed_point_series(b, c, 8), lagrange(b, c, 8), f'case {i}')

    def test_numerical_assembly_against_rationals(self):
        rng = random.Random(1830372)
        for order in (5, 6, 7, 8):
            b, c = random_jets(rng, order)
            c[2] = [x/6 for x in b[2]]
            vals = {loop: np.asarray(b[loop]+c[loop], dtype=float) for loop in range(3, order+1)}
            numeric = coefficients(vals, np.asarray(b[2], dtype=float), order=order)
            exact = np.asarray(lagrange(b, c, order), dtype=float)
            np.testing.assert_allclose(numeric, exact, rtol=3e-13, atol=5e-15)

    def test_top_sensitivities(self):
        b, c = {1: [F(3)]}, {1: [F(1)]}
        baseline = fixed_point_series(b, c, 8)
        beta = fixed_point_series({**b, 8: [F(1)]}, c, 8)
        mass = fixed_point_series(b, {**c, 8: [F(1)]}, 8)
        self.assertEqual(beta[8]-baseline[8], -F(1, 19683))
        self.assertEqual(mass[8]-baseline[8], F(1, 6561))
        self.assertEqual(top_loop_weights(8), (-F(1, 19683), F(1, 6561)))

    def test_high_loop_affinity_exact(self):
        rng = random.Random(328671)
        b, c = random_jets(rng, 8)
        low_b = {loop: value for loop, value in b.items() if loop < 5}
        low_c = {loop: value for loop, value in c.items() if loop < 5}
        base = fixed_point_series(low_b, low_c, 8)
        predicted = base.copy()
        for loop in range(5, 9):
            for channel in ('b', 'c'):
                for j, value in enumerate((b if channel == 'b' else c)[loop]):
                    jet = [F(0)]*(9-loop)
                    jet[j] = value
                    shifted_b = {**low_b, **({loop: jet} if channel == 'b' else {})}
                    shifted_c = {**low_c, **({loop: jet} if channel == 'c' else {})}
                    result = fixed_point_series(shifted_b, shifted_c, 8)
                    predicted = [x+y-z for x, y, z in zip(predicted, result, base)]
        self.assertEqual(predicted, fixed_point_series(b, c, 8))

    def test_numeric_affine_map(self):
        rng = np.random.default_rng(527868)
        vals = {loop: rng.normal(size=2*(9-loop)) for loop in range(3, 9)}
        B2 = rng.normal(size=7)
        constant, weights = high_loop_affine({loop: vals[loop] for loop in (3, 4)}, B2)
        predicted = constant+sum(weights[loop]@vals[loop] for loop in range(5, 9))
        np.testing.assert_allclose(predicted, coefficients(vals, B2), rtol=3e-13, atol=5e-15)

    def test_seventh_loop_zero_channel_must_return(self):
        # At C7, b7=3*c7 is zero. At C8 its effect mixes with b2,c2,
        # hence even this exact channel cannot be discarded at lower loops.
        b = {1: [F(3)], 2: [F(6)]}
        c = {1: [F(1)], 2: [F(1)]}
        base = fixed_point_series(b, c, 8)
        changed = fixed_point_series({**b, 7: [F(3), F(0)]}, {**c, 7: [F(1), F(0)]}, 8)
        self.assertEqual(changed[7]-base[7], 0)
        self.assertEqual(changed[8]-base[8], F(2, 6561))

    def test_missing_jets_fail_closed(self):
        vals = {loop: np.zeros(2*(9-loop)) for loop in range(3, 9)}
        with self.assertRaises(ValueError):
            coefficients({k: v for k, v in vals.items() if k != 8}, np.zeros(7))
        with self.assertRaises(ValueError):
            coefficients(vals, np.zeros(6))
        with self.assertRaises(ValueError):
            coefficients({**vals, 7: np.zeros(2)}, np.zeros(7))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RGChecks)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'status': 'passed' if result.wasSuccessful() else 'failed',
              'dimension': 3, 'order': 8, 'tests': result.testsRun,
              'exact_bivariate_lagrange_cases': 64,
              'dC8_db80': '-1/19683', 'dC8_dc80': '1/6561',
              'loops_5_to_8_affine': result.wasSuccessful()}
    (ROOT/'verification').mkdir(exist_ok=True)
    (ROOT/'verification'/'assembly_checks.json').write_text(json.dumps(report, indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
