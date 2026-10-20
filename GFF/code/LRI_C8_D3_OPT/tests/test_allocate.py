#!/usr/bin/env python3
"""Check the concrete cost/count invariants of the pilot allocation helper."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from allocate import allocate
from io_utils import power_of_two


class AllocationChecks(unittest.TestCase):
    def data(self):
        return {"free": {"8": {
            "1": {t: {"projected_replicate_sd": 2.0, "points_per_replicate": 16,
                       "cpu_seconds": 0.032, "points": 32} for t in ("a", "b")},
            "2": {t: {"projected_replicate_sd": 1.0, "points_per_replicate": 16,
                       "cpu_seconds": 0.064, "points": 32} for t in ("a", "b")},
        }}}

    def test_budget_minimum_rounding_and_neyman_order(self):
        allocation, report = allocate(self.data(), .1, 16, minimum=64)
        values = allocation["free"]["8"]
        self.assertTrue(all(power_of_two(n) and n >= 64 for n in values.values()))
        self.assertLessEqual(report["estimated_core_hours"], .1)
        self.assertGreaterEqual(values["1"], values["2"])
        self.assertFalse(report["pilot_included_in_production_estimator"])

    def test_invalid_budget_or_counts_rejected(self):
        for budget, minimum in ((.0001, 64), (float("inf"), 64), (.1, 63)):
            with self.subTest(budget=budget, minimum=minimum), self.assertRaises(ValueError):
                allocate(self.data(), budget, 16, minimum=minimum)


if __name__ == "__main__":
    unittest.main(verbosity=2)
