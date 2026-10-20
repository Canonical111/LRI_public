#!/usr/bin/env python3
"""Freeze a pilot-derived per-graph allocation for a NEW C8 campaign.

The provisional cost model uses the conservative Monte Carlo scaling
Var(mean) proportional to 1/n, not a claimed RQMC convergence rate. The pilot
is excluded from the resulting production estimator. Power-of-two rounding
and minimum counts are applied after Neyman allocation.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from io_utils import ROOT, digest, load, power_of_two, save


def rounded_power_two(x):
    return 1 << max(0, math.ceil(math.log2(max(1, x))))


def allocate(statistics, budget_core_hours, replicates, minimum=4096):
    if not math.isfinite(budget_core_hours) or budget_core_hours <= 0 or replicates < 4 or not power_of_two(minimum):
        raise ValueError("Invalid budget, replicates, or minimum")
    rows = []
    for sector, loops in statistics.items():
        for loop, graphs in loops.items():
            for graph, campaigns in graphs.items():
                if set(campaigns) != {"a", "b"}:
                    raise ValueError("Pilot requires both independent campaigns for every graph")
                # Recover a per-point variance proxy from the randomized-net
                # replicate variances. Replicate shifts are independent across
                # graphs; final uncertainty still uses graph-summed replicates.
                variance = sum(v["projected_replicate_sd"]**2 * v["points_per_replicate"] for v in campaigns.values()) / 2
                seconds = sum(v["cpu_seconds"] for v in campaigns.values())
                samples = sum(v["points"] for v in campaigns.values())
                if samples <= 0 or not math.isfinite(seconds) or seconds <= 0 or not math.isfinite(variance):
                    raise ValueError("Pilot variance and timing must be finite and its sample count positive")
                cost = max(seconds / samples, 1e-12)
                rows.append((sector, loop, graph, max(variance, 0), cost))
    baseline = 2 * replicates * minimum * sum(row[4] for row in rows)
    budget = budget_core_hours * 3600
    if budget < baseline:
        raise ValueError(f"Budget is below the estimated minimum-count cost ({baseline / 3600:.3f} core-hours)")
    def counts(scale):
        return [max(minimum, rounded_power_two(scale * math.sqrt(variance / cost))) for _, _, _, variance, cost in rows]
    def total(ns):
        return 2 * replicates * sum(n * row[4] for n, row in zip(ns, rows))
    low, high = 0.0, 1.0
    while total(counts(high)) < budget:
        high *= 2
        if high > 1e100:
            raise ValueError("All observed variances vanish; use a fixed conservative allocation")
    for _ in range(100):
        middle = (low + high) / 2
        if total(counts(middle)) <= budget:
            low = middle
        else:
            high = middle
    ns = counts(low)
    output = {}
    for (sector, loop, graph, _, _), count in zip(rows, ns):
        output.setdefault(sector, {}).setdefault(loop, {})[graph] = count
    report = {
        "budget_core_hours": budget_core_hours, "replicates_per_campaign": replicates,
        "minimum_points": minimum, "estimated_core_hours": total(ns) / 3600,
        "estimated_minimum_count_core_hours": baseline / 3600,
        "minimum_allocated": min(ns), "maximum_allocated": max(ns),
        "kernel_evaluations": 2 * replicates * sum(ns),
        "cost_scope": "Pilot timing extrapolation; excludes input loading and queueing, and assumes Monte Carlo variance scaling. It is not a precision guarantee.",
        "pilot_included_in_production_estimator": False,
    }
    return output, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pilot_statistics", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--core-hours", type=float, required=True)
    parser.add_argument("--replicates", type=int, default=32)
    parser.add_argument("--minimum-points", type=int, default=4096)
    args = parser.parse_args()
    data = load(args.pilot_statistics)
    inventory = load(ROOT / "inputs/inventory.json")
    if set(data) != set(inventory):
        raise ValueError("Pilot sector coverage differs from the active inventory")
    for sector in inventory:
        if set(data[sector]) != set(inventory[sector]):
            raise ValueError("Pilot loop coverage differs from the active inventory")
        for loop, rows in inventory[sector].items():
            if set(data[sector][loop]) != {str(row["id"]) for row in rows}:
                raise ValueError("Pilot graph coverage differs from the active inventory")
    allocation, report = allocate(data, args.core_hours, args.replicates, args.minimum_points)
    save(args.output, allocation)
    report.update({"pilot_statistics_sha256": digest(args.pilot_statistics), "allocation_sha256": digest(args.output), "inventory_sha256": digest(ROOT / "inputs/inventory.json")})
    save(args.output.with_suffix(".report.json"), report)
    import json
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
