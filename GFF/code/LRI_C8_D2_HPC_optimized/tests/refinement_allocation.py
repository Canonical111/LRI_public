#!/usr/bin/env python3
"""Focused checks of graph-specific floors in the refinement allocation."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from refinement_allocation import allocate_with_floors


def rejected(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("Invalid refinement accepted")


def run():
    # Independent continuous optima lie on the power-of-two lattice in both cases.
    n, report = allocate_with_floors([64, 4], [1, 1], [16, 4], 80)
    assert n == [64, 16] and report["cost"] == 80
    n, report = allocate_with_floors([16, 4], [1, 4], [16, 4], 128)
    assert n == [64, 16] and report["cost"] == 128
    # A binding graph-specific floor changes the unconstrained equal allocation.
    n, report = allocate_with_floors([1, 1], [1, 1], [64, 4], 80)
    assert n == [64, 16] and report["floor_cost"] == 68
    rejected(lambda: allocate_with_floors([1, 1], [1, 1], [64, 4], 67))
    rejected(lambda: allocate_with_floors([1, 1], [1, 1], [3, 4], 80))
    rejected(lambda: allocate_with_floors([1, 1], [1, 1], [16, 4], 80, maximum=8))
    rejected(lambda: allocate_with_floors([0, 1], [1, 1], [16, 4], 80))
    # The advertised common multiplier cap preserves every graph's point period.
    n, report = allocate_with_floors([1, 1], [1, 1], [16, 4], 1000, maximum=64)
    assert n == [64, 16] and report["common_multiplier_cap"] == 4
    assert report["point_cap_reached"] and max(n) <= 64
    v, c, floors = [100, 7, .125], [1, 3, 5], [8, 16, 4]
    for budget in (76, 77, 128, 511):
        n, report = allocate_with_floors(v, c, floors, budget)
        assert all(k >= f and k & (k - 1) == 0 for k, f in zip(n, floors))
        assert math.fsum(k * cost for k, cost in zip(n, c)) <= budget
        physical_objective = math.fsum(var / k for var, k in zip(v, n))
        transformed_objective = math.fsum((var / f) / (k / f) for var, f, k in zip(v, floors, n))
        assert physical_objective == transformed_objective
    return {"status": "passed", "exact_continuous_and_integer_optima": 2,
            "binding_graph_specific_floor": True, "insufficient_budget_refused": True,
            "powers_of_two_and_safe_common_cap": True, "irregular_budget_cases": 4,
            "objective_preserved_by_floor_substitution": True,
            "scope": "Focused mathematical checks of the floor substitution; no accuracy claim for a C8 refinement"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
