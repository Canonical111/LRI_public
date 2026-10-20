#!/usr/bin/env python3
"""Small mathematical and covariance tests for the pilot allocation tool."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pilot_allocation import allocate_counts, projected_graph_variances, variance_floor


def raises_value_error(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("Invalid allocation/input was accepted")


def run():
    # Exact continuous optima which also meet the integer constraints.
    counts, report = allocate_counts([16, 1], [1, 1], 80, minimum=4)
    assert counts == [64, 16]
    assert report["cost"] == 80
    counts, report = allocate_counts([4, 1], [1, 4], 128, minimum=4)
    assert counts == [64, 16]  # sigma/sqrt(cost) ratio = 4.
    assert report["cost"] == 128

    counts, report = allocate_counts([4, 1], [1, 4], 20, minimum=4)
    assert counts == [4, 4]
    raises_value_error(lambda: allocate_counts([4, 1], [1, 4], 19, minimum=4))
    raises_value_error(lambda: allocate_counts([0, 1], [1, 1], 20, minimum=4))
    raises_value_error(lambda: allocate_counts([1, 1], [1, float("nan")], 20, minimum=4))
    raises_value_error(lambda: allocate_counts([1], [1], 20, minimum=3))

    # Irregular budgets preserve powers of two, floors, and the stated budget.
    for budget in (36, 37, 65, 99, 137, 1001):
        counts, report = allocate_counts([100, 4, 0.01], [1, 3, 5], budget, minimum=4)
        assert all(n >= 4 and n & (n - 1) == 0 for n in counts)
        assert sum(n * c for n, c in zip(counts, [1, 3, 5])) <= budget
    capped, report = allocate_counts([1, 2], [1, 2], 1000, minimum=4, maximum=16)
    assert capped == [16, 16] and report["point_cap_reached"]

    assert variance_floor([0, 2, 4], 0.1, 7) == 0.3 or math.isclose(variance_floor([0, 2, 4], 0.1, 7), 0.3)
    assert math.isclose(variance_floor([0, 0], 0.1, 7), 0.7)

    with tempfile.TemporaryDirectory(prefix="c8_allocation_test_") as directory:
        path = Path(directory) / "graph_replicates.csv"
        rows = []
        totals = []
        for rep in range(4):
            x = rep + 1
            rows.extend([[rep, 10, x, x], [rep, 11, x, 2 * x]])
            totals.append([2 * x, 3 * x])

        def write(data):
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["replicate", "graph", "jet_0", "jet_1"])
                writer.writerows(data)

        cfg = {"L": 8, "replicates": 4, "counts": {"10": 8, "11": 16}}
        write(rows)
        result = projected_graph_variances(path, cfg, {10, 11}, np.array([1., -1.]), totals)
        # The two channels of graph 10 cancel exactly after projection. This
        # would fail if channel variances were added without their covariance.
        assert result[10] == 0
        assert math.isclose(result[11], 16 * (5 / 3), rel_tol=1e-14)
        write(rows[:-1])
        raises_value_error(lambda: projected_graph_variances(path, cfg, {10, 11}, np.array([1., -1.]), totals))
        write(rows + rows[:1])
        raises_value_error(lambda: projected_graph_variances(path, cfg, {10, 11}, np.array([1., -1.]), totals))
        write(rows)
        raises_value_error(lambda: projected_graph_variances(path, cfg, {10, 11, 12}, np.array([1., -1.]), totals))
        raises_value_error(lambda: projected_graph_variances(path, cfg, {10, 11}, np.array([1., -1.]), np.zeros((4, 2))))

    return {"status": "passed", "exact_Neyman_optima": 2,
            "irregular_budget_cases": 6, "floors_and_power_of_two_counts": True,
            "budget_never_exceeded": True, "projected_channel_covariance_preserved": True,
            "incomplete_duplicate_and_mismatched_graph_data_refused": True,
            "scope": "Synthetic mathematical/reader tests; no claim of an optimized C8 production design"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
