#!/usr/bin/env python3
"""Allocate an independent C8 refinement from an existing frozen pilot allocation.

The graph-specific floor is f_g=max(min_points, pilot_multiplier*max(N_pilot)).
With N_g=f_g*m_g, the objective sum(v_g/N_g) and cost sum(c_g*N_g)
become sum((v_g/f_g)/m_g) and sum((c_g*f_g)*m_g). The existing audited
power-of-two allocator therefore applies directly with m_g >= 1. The source
allocation's regularized graph variances, costs and pilot provenance are kept.

Examples:
  python tools/refinement_allocation.py pilot_allocation.json --show-floor
  python tools/refinement_allocation.py pilot_allocation.json refinement.json \
    --target-core-hours 6 --replicates 8 --min-points 32 --pilot-multiplier 1

This writes an allocation only. It never starts a campaign, incorporates pilot
samples into a new estimator, or claims that its MC scaling forecast is a
measured error bar.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from common import ROOT, canon, digest, dump, load, pow2
from pilot_allocation import SCHEMA, MAX_POINTS, LOOPS, SECTORS, CAMPAIGNS, allocate_counts


def allocate_with_floors(variances, costs, floors, budget, maximum=MAX_POINTS):
    """Apply the exact floor substitution to one campaign/replicate budget."""
    v, c, f = list(variances), list(costs), list(floors)
    if not v or len(v) != len(c) or len(v) != len(f):
        raise ValueError("Matching nonempty variance, cost and floor vectors required")
    if type(maximum) is not int or not pow2(maximum):
        raise ValueError("Maximum points must be a positive power of two")
    if any(type(n) is not int or not pow2(n) or n > maximum for n in f):
        raise ValueError("Every graph floor must be a positive power of two no larger than the cap")
    if any(not math.isfinite(float(x)) or float(x) <= 0 for x in v + c):
        raise ValueError("Finite positive variances and costs required")
    multiplier_cap = maximum // max(f)
    multipliers, allocation = allocate_counts(
        [float(x) / n for x, n in zip(v, f)],
        [float(x) * n for x, n in zip(c, f)],
        budget, minimum=1, maximum=multiplier_cap)
    counts = [n * m for n, m in zip(f, multipliers)]
    actual_cost = math.fsum(float(x) * n for x, n in zip(c, counts))
    if any(n < floor or n > maximum or not pow2(n) for n, floor in zip(counts, f)):
        raise ArithmeticError("Refinement violated a floor, power-of-two constraint, or point cap")
    if actual_cost > budget * (1 + 1e-12):
        raise ArithmeticError("Refinement exceeds its kernel budget")
    allocation.update(cost=actual_cost, floor_cost=math.fsum(float(x) * n for x, n in zip(c, f)),
                      unspent=max(0., budget - actual_cost), common_multiplier_cap=multiplier_cap)
    return counts, allocation


def problem(source, replicates, minimum, pilot_multiplier):
    """Validate a complete frozen allocation and recover its unchanged metrics."""
    if source.get("schema") != SCHEMA or source.get("dimension") != 2 or source.get("order") != 8:
        raise ValueError("Source must be a c8-d2-allocation-1 allocation for dimension two, order eight")
    if type(replicates) is not int or replicates < 4 or replicates % 2:
        raise ValueError("Use at least four, and an even number of, complete replicates")
    if type(minimum) is not int or minimum < 4 or not pow2(minimum) or minimum > MAX_POINTS:
        raise ValueError("Minimum points must be a power of two in [4, 2^52]")
    if type(pilot_multiplier) is not int or not pow2(pilot_multiplier):
        raise ValueError("Pilot multiplier must be a positive power of two")
    if source.get("campaign_count") != 2:
        raise ValueError("Source must include both independent campaigns")
    if source.get("inputs_manifest_sha256") != digest(ROOT / "inputs/manifest.json"):
        raise ValueError("Source allocation belongs to different graph inputs")
    for field in ("source_manifest_sha256", "source_groups", "pilot_seeds", "metrics", "jacobian_C8"):
        if not source.get(field):
            raise ValueError("Missing frozen pilot provenance or metrics: " + field)
    if any(type(seed) is not int or not 0 <= seed < 2**63 for seed in source["pilot_seeds"]):
        raise ValueError("Invalid pilot seed provenance")
    expected_groups = {f"{tag}_{sector}_L{loop}" for tag in CAMPAIGNS for sector in SECTORS for loop in LOOPS}
    if set(source["source_groups"]) != expected_groups:
        raise ValueError("Pilot provenance must identify all 24 loop/sector/campaign groups")
    inventory = load(ROOT / "inputs/inventory.json")
    expected = {(sector, int(loop), row["id"]) for sector in SECTORS
                for loop, rows in inventory[sector].items() for row in rows}
    metrics = {}
    for identity, item in source["metrics"].items():
        parts = identity.split(":")
        if len(parts) != 3:
            raise ValueError("Malformed graph metric identity")
        sector, loop, gid = parts[0], int(parts[1]), int(parts[2])
        key = sector, loop, gid
        if identity != f"{sector}:{loop}:{gid}" or key in metrics:
            raise ValueError("Noncanonical or repeated graph metric identity")
        if set(item.get("pilot_points", {})) != set(CAMPAIGNS):
            raise ValueError("Every graph needs both pilot point counts")
        if any(type(n) is not int or n < 4 or not pow2(n) or n > MAX_POINTS
               for n in item["pilot_points"].values()):
            raise ValueError("Invalid pilot graph point count")
        for field in ("variance_proxy", "seconds_per_point"):
            value = item.get(field)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError("Every frozen graph variance and cost must be finite and positive")
        metrics[key] = item
    if set(metrics) != expected:
        raise ValueError("Frozen metrics do not cover the exact complete graph inventory")
    counts = source.get("counts", {})
    if set(counts) != set(SECTORS) or any(set(counts[sector]) != {str(L) for L in LOOPS} for sector in SECTORS):
        raise ValueError("Incomplete source allocation sectors or loop orders")
    source_keys = {(sector, int(loop), int(gid)) for sector, loops in counts.items()
                   for loop, rows in loops.items() for gid in rows}
    if source_keys != expected:
        raise ValueError("Source count inventory differs from its frozen metric inventory")
    keys = sorted(metrics)
    floors = [max(minimum, pilot_multiplier * max(metrics[key]["pilot_points"].values())) for key in keys]
    if max(floors) > MAX_POINTS:
        raise ValueError("Pilot retention floor exceeds the 2^52-point period")
    variances = [metrics[key]["variance_proxy"] for key in keys]
    costs = [metrics[key]["seconds_per_point"] for key in keys]
    floor_cost = math.fsum(c * f for c, f in zip(costs, floors))
    loop_floors = []
    for sector in SECTORS:
        for loop in LOOPS:
            selected = [i for i, key in enumerate(keys) if key[:2] == (sector, loop)]
            loop_floors.append({"sector": sector, "loop": loop, "graphs": len(selected),
                "minimum_floor": min(floors[i] for i in selected),
                "maximum_floor": max(floors[i] for i in selected),
                "kernel_core_hours": math.fsum(costs[i] * floors[i] for i in selected) * 2 * replicates / 3600})
    summary = {"graphs": len(keys), "replicates": replicates, "campaign_count": 2,
               "minimum_points": minimum, "pilot_multiplier": pilot_multiplier,
               "minimum_kernel_core_hours": floor_cost * 2 * replicates / 3600,
               "floor_samples": sum(floors) * 2 * replicates,
               "floor_by_loop_sector": loop_floors,
               "basis": "Frozen measured per-point kernel costs, including both campaigns and all replicates; loading and other fixed overhead excluded"}
    return keys, variances, costs, floors, summary


def generate(source, source_hash, source_name, target_core_hours, replicates=8, minimum=32, pilot_multiplier=1):
    if not math.isfinite(target_core_hours) or target_core_hours <= 0:
        raise ValueError("Positive finite total kernel core-hour budget required")
    keys, variances, costs, floors, floor_summary = problem(source, replicates, minimum, pilot_multiplier)
    if floor_summary["minimum_kernel_core_hours"] > target_core_hours * (1 + 1e-13):
        raise ValueError(f"Retaining the requested pilot floors needs {floor_summary['minimum_kernel_core_hours']:.12g} kernel core-hours; budget is {target_core_hours:.12g}")
    counts, allocation = allocate_with_floors(variances, costs, floors, target_core_hours * 3600 / (2 * replicates))
    nested = {sector: {str(loop): {} for loop in LOOPS} for sector in SECTORS}
    nested_floors = copy.deepcopy(nested)
    for (sector, loop, gid), n, f in zip(keys, counts, floors):
        nested[sector][str(loop)][str(gid)] = n
        nested_floors[sector][str(loop)][str(gid)] = f
    result = copy.deepcopy(source)
    result.update(replicates=replicates, campaign_count=2, minimum_points=minimum, maximum_points=MAX_POINTS,
        counts=nested, target_core_hours=target_core_hours,
        estimated_kernel_core_hours=allocation["cost"] * 2 * replicates / 3600,
        minimum_kernel_core_hours=allocation["floor_cost"] * 2 * replicates / 3600,
        unspent_kernel_core_hours=allocation["unspent"] * 2 * replicates / 3600,
        model_only_standard_error_forecast=math.sqrt(math.fsum(v / n for v, n in zip(variances, counts)) / (2 * replicates)),
        method="Exact substitution N_g=f_g*m_g followed by the existing power-of-two Neyman allocator applied to v_g/f_g and c_g*f_g with m_g>=1",
        refinement_source_allocation={"sha256": source_hash, "filename": source_name,
            "target_core_hours": source.get("target_core_hours"), "replicates": source.get("replicates")},
        refinement_floor_policy={"formula": "max(min_points, pilot_multiplier*max(pilot_points_a,pilot_points_b))",
            "minimum_points": minimum, "pilot_multiplier": pilot_multiplier, "floors": nested_floors,
            "common_multiplier_cap": allocation["common_multiplier_cap"],
            "common_multiplier_cap_reached": allocation["point_cap_reached"],
            "floor_by_loop_sector": floor_summary["floor_by_loop_sector"],
            "note": "Retains points per graph-replicate, with the chosen new replicate count; the common safe cap can cap smaller-floor graphs below 2^52 points"},
        scope="Frozen independent-refinement allocation only. Requires fresh seeds and excludes every pilot sample from the new estimator. Point-count refinement and the MC forecast do not establish production precision. Multipliers or another replicate count change the recorded budget.")
    warnings = list(source.get("warnings", []))
    warnings.append("Refinement uses noisy pilot graph variances and an unvalidated 1/N variance model; retained positive point floors do not bound rare-region sampling error")
    result["warnings"] = warnings
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("allocation", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--target-core-hours", type=float)
    parser.add_argument("--replicates", type=int, default=8)
    parser.add_argument("--min-points", type=int, default=32)
    parser.add_argument("--pilot-multiplier", type=int, default=1)
    parser.add_argument("--show-floor", action="store_true", help="show the retained-pilot floor cost without allocating or writing")
    args = parser.parse_args()
    raw = args.allocation.read_bytes()
    source = json.loads(raw)
    source_hash = hashlib.sha256(raw).hexdigest()
    if args.show_floor:
        *_, summary = problem(source, args.replicates, args.min_points, args.pilot_multiplier)
        summary["source_allocation_sha256"] = source_hash
        if args.target_core_hours is not None:
            if not math.isfinite(args.target_core_hours) or args.target_core_hours <= 0:
                parser.error("--target-core-hours must be positive and finite")
            summary["target_core_hours"] = args.target_core_hours
            summary["floor_fits_budget"] = summary["minimum_kernel_core_hours"] <= args.target_core_hours * (1 + 1e-13)
        print(json.dumps(summary, indent=2))
        return
    if args.output is None or args.target_core_hours is None:
        parser.error("output and --target-core-hours are required unless --show-floor is used")
    result = generate(source, source_hash, args.allocation.name, args.target_core_hours, args.replicates,
                      args.min_points, args.pilot_multiplier)
    if args.output.exists():
        if canon(load(args.output)) != canon(result):
            raise FileExistsError(f"Refusing to overwrite a different allocation: {args.output}")
        state = "identical allocation already present"
    else:
        dump(args.output, result)
        state = "written"
    print(json.dumps({"output": str(args.output), "state": state,
        "graphs": len(result["metrics"]), "source_allocation_sha256": source_hash,
        "minimum_kernel_core_hours": result["minimum_kernel_core_hours"],
        "estimated_kernel_core_hours": result["estimated_kernel_core_hours"],
        "target_core_hours": result["target_core_hours"],
        "model_only_standard_error_forecast": result["model_only_standard_error_forecast"]}, indent=2))


if __name__ == "__main__":
    main()
