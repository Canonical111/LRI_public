#!/usr/bin/env python3
"""Freeze a C8 Neyman variance/cost allocation from a complete independent pilot.

Example:
  python tools/pilot_allocation.py results/pilot allocation.json \
      --target-core-hours 2000 --replicates 64 --min-points 4096

The budget covers both production campaigns, each with --replicates complete
replicates. It uses measured per-task kernel time; loading, scheduler idle
time, and other fixed overhead are excluded. Counts are shared by campaigns
a and b and are rounded to powers of two. This changes allocation only;
pilot samples never enter a subsequently generated production estimate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import itertools
import json
import math
from pathlib import Path
import statistics
import sys

import numpy as np

from common import ROOT, canon, digest, dump, load, pow2
from assemble import coefficients, jacobians, load_campaign
from production import blocks_of, dbopen, group_of, task_blocks, validate_checkpoint, verify_base


SCHEMA = "c8-d2-allocation-1"
LOOPS = tuple(range(3, 9))
SECTORS = ("free", "power")
CAMPAIGNS = ("a", "b")
MAX_POINTS = 1 << 52


def allocate_counts(variances, costs, budget, minimum=4096, maximum=MAX_POINTS):
    """Power-of-two allocation for one production campaign/replicate.

    Minimize the heuristic sum v_i/n_i with sum c_i*n_i <= budget. First
    solve the continuous floored Neyman allocation n_i = lambda*sqrt(v_i/c_i),
    round down, then add affordable doublings by marginal variance gain/cost.
    This is a deterministic allocation heuristic, not an exact integer solver.
    """
    v = list(map(float, variances))
    c = list(map(float, costs))
    if not v or len(v) != len(c):
        raise ValueError("Equal nonempty variance and cost vectors required")
    if any(not math.isfinite(x) or x <= 0 for x in v + c):
        raise ValueError("Every variance proxy and point cost must be positive and finite")
    if not math.isfinite(budget) or budget <= 0:
        raise ValueError("Positive finite budget required")
    if not pow2(minimum) or not pow2(maximum) or minimum > maximum:
        raise ValueError("Minimum/maximum counts must be ordered positive powers of two")
    floor_cost = math.fsum(x * minimum for x in c)
    if floor_cost > budget * (1 + 1e-13):
        raise ValueError(f"Minimum counts alone need {floor_cost:.12g} seconds per campaign/replicate, budget is {budget:.12g}")
    cap_cost = math.fsum(x * maximum for x in c)
    if cap_cost <= budget:
        counts = [maximum] * len(v)
        return counts, {"cost": cap_cost, "floor_cost": floor_cost, "unspent": budget - cap_cost,
                        "continuous_cost": cap_cost, "point_cap_reached": True}
    weights = [math.sqrt(x) / math.sqrt(y) for x, y in zip(v, c)]

    def continuous(scale):
        return [min(maximum, max(minimum, scale * w)) for w in weights]

    def spent(counts):
        return math.fsum(x * y for x, y in zip(c, counts))

    lo = 0.
    hi = max(budget / math.fsum(math.sqrt(x) * math.sqrt(y) for x, y in zip(v, c)), 1e-300)
    while spent(continuous(hi)) < budget:
        hi *= 2
        if not math.isfinite(hi):
            raise ArithmeticError("Cannot bracket finite Neyman multiplier")
    for _ in range(90):
        mid = (lo + hi) / 2
        if spent(continuous(mid)) <= budget:
            lo = mid
        else:
            hi = mid
    continuous_counts = continuous(lo)
    floor_exp = minimum.bit_length() - 1
    counts = [min(maximum, 1 << max(floor_exp, int(math.floor(math.log2(x))))) for x in continuous_counts]
    cost = spent(counts)
    heap = []
    for i, n in enumerate(counts):
        if n < maximum:
            heapq.heappush(heap, (-v[i] / (2 * c[i] * n * n), i))
    remaining = max(0., budget - cost)
    while heap:
        _, i = heapq.heappop(heap)
        increment = c[i] * counts[i]
        if increment > remaining:
            continue  # Remaining budget can only decrease.
        remaining -= increment
        counts[i] *= 2
        if counts[i] < maximum:
            heapq.heappush(heap, (-v[i] / (2 * c[i] * counts[i] * counts[i]), i))
    cost = spent(counts)
    if cost > budget * (1 + 1e-12):
        raise ArithmeticError("Rounded allocation exceeds its budget")
    return counts, {"cost": cost, "floor_cost": floor_cost, "unspent": max(0., budget - cost),
                    "continuous_cost": spent(continuous_counts), "point_cap_reached": any(n == maximum for n in counts)}


def variance_floor(values, fraction, fallback):
    """A positive regularizer for noisy or zero pilot variance estimates."""
    if not math.isfinite(fraction) or fraction <= 0:
        raise ValueError("Positive variance-floor fraction required")
    positive = [x for x in values if math.isfinite(x) and x > 0]
    scale = statistics.median(positive) if positive else fallback
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("No positive variance scale for the pilot")
    return max(fraction * scale, 1e-300)


def projected_graph_variances(path, cfg, active_ids, jacobian, merged_batches):
    """Stream the graph CSV; Welford scalar variance preserves each jet covariance.

    Projecting the complete graph jet before taking its variance is exactly
    J Cov(graph_jets) J^T. No regulator/channel covariance is discarded.
    """
    dim = 2 * (9 - cfg["L"])
    reps = cfg["replicates"]
    if reps < 4 or reps % 2:
        raise ValueError("Pilot needs at least four even complete replicates")
    active_ids = set(active_ids)
    counts = {int(k): v for k, v in cfg["counts"].items()}
    if set(counts) != active_ids or any(type(n) is not int or n < 1 for n in counts.values()):
        raise ValueError("Pilot graph counts do not cover every active graph")
    states = {gid: [0, 0., 0., 0] for gid in active_ids}  # n, mean, M2, replicate bitmask
    totals = np.zeros((reps, dim), dtype=np.longdouble)
    total_magnitudes = np.zeros_like(totals)
    expected_header = ["replicate", "graph"] + [f"jet_{j}" for j in range(dim)]
    with Path(path).open(newline="") as handle:
        reader = csv.reader(handle)
        if next(reader, None) != expected_header:
            raise ValueError(f"Wrong graph-replicate CSV header: {path}")
        for row in reader:
            if len(row) != dim + 2:
                raise ValueError("Invalid graph-replicate row width")
            rep, gid = int(row[0]), int(row[1])
            if gid not in active_ids or not 0 <= rep < reps:
                raise ValueError("Unexpected graph/replicate in pilot CSV")
            values = np.asarray(row[2:], dtype=np.longdouble)
            if not np.isfinite(values).all():
                raise ValueError("Nonfinite pilot graph jet")
            state = states[gid]
            bit = 1 << rep
            if state[3] & bit:
                raise ValueError("Duplicate pilot graph/replicate")
            state[3] |= bit
            projected = float(np.dot(np.asarray(jacobian, dtype=np.longdouble), values))
            if not math.isfinite(projected):
                raise ValueError("Nonfinite C8-projected pilot graph jet")
            state[0] += 1
            delta = projected - state[1]
            state[1] += delta / state[0]
            state[2] += delta * (projected - state[1])
            totals[rep] += values
            total_magnitudes[rep] += np.abs(values)
    full_mask = (1 << reps) - 1
    if any(s[0] != reps or s[3] != full_mask for s in states.values()):
        raise ValueError("Incomplete pilot graph-replicate CSV")
    expected = np.asarray(merged_batches, dtype=np.longdouble)
    if expected.shape != totals.shape or np.any(np.abs(totals - expected) > 1e-12 * np.maximum(1., total_magnitudes)):
        raise ValueError("Graph-replicate sums differ from merged pilot batches")
    ans = {}
    for gid, state in states.items():
        value = max(0., state[2] / (reps - 1)) * counts[gid]
        if not math.isfinite(value):
            raise ValueError("Nonfinite pilot variance proxy")
        ans[gid] = value
    return ans


def measured_graph_costs(group, cfg, manifest, manifest_hash, active_ids):
    """Verify every expected checkpoint and accumulate its per-row task time."""
    totals = {gid: [0., 0] for gid in active_ids}
    timing_digest = hashlib.sha256()
    db = dbopen(group / "tasks.sqlite", True)
    try:
        for shard in range(cfg["shards"]):
            for part, block in enumerate(task_blocks(db, shard, manifest["checkpoint_tasks"])):
                path = group / "checkpoints" / f"s{shard:06d}_p{part:06d}.json"
                raw = path.read_bytes()
                checkpoint = json.loads(raw)
                native = validate_checkpoint(checkpoint, block, cfg, manifest, manifest_hash)
                timing_digest.update(path.name.encode() + b"\0" + hashlib.sha256(raw).digest())
                for row in native["rows"]:
                    gid = row["graph"]
                    seconds = row.get("seconds")
                    if isinstance(seconds, bool) or not isinstance(seconds, (float, int)) or not math.isfinite(seconds) or seconds < 0:
                        raise ValueError(f"Missing/invalid kernel task timing: {path}")
                    if gid not in totals:
                        raise ValueError("Checkpoint graph is outside the active inventory")
                    totals[gid][0] += seconds
                    totals[gid][1] += row["end"] - row["begin"]
    finally:
        db.close()
    ans = {}
    for gid, (seconds, samples) in totals.items():
        expected = cfg["replicates"] * cfg["counts"][str(gid)]
        if samples != expected or expected <= 0:
            raise ValueError("Checkpoint timing does not cover the complete pilot")
        ans[gid] = seconds / samples
    return ans, timing_digest.hexdigest()


def generate(pilot, target_core_hours, replicates=64, minimum=4096, floor_fraction=0.1, accept_tool_change=False):
    pilot = Path(pilot).resolve()
    if replicates < 4 or replicates % 2:
        raise ValueError("Production needs at least four even replicates")
    if not pow2(minimum) or minimum > MAX_POINTS:
        raise ValueError("Minimum points must be a power of two no larger than 2^52")
    if not math.isfinite(target_core_hours) or target_core_hours <= 0:
        raise ValueError("Positive finite total kernel core-hour budget required")
    if not math.isfinite(floor_fraction) or not 0 < floor_fraction <= 1:
        raise ValueError("Variance-floor fraction must lie in (0,1]")
    manifest, _, manifest_hash, _ = verify_base(pilot, check_executable=False, accept_tool_change=accept_tool_change)
    if manifest.get("test_only") or manifest.get("purpose") != "pilot":
        raise ValueError("Allocation requires a complete, explicitly labelled pilot; incomplete workflow tests are refused")
    if manifest.get("primitive_mode") != "recompute":
        raise ValueError("Pilot must recompute all primitive jets")
    m, mh, arrays, merged_hashes, changes = load_campaign(pilot, accept_tool_change)
    if mh != manifest_hash:
        raise ValueError("Pilot manifest changed during inspection")
    for sector in SECTORS:
        if set(arrays[sector]) != set(CAMPAIGNS) or any(set(arrays[sector][tag]) != set(LOOPS) for tag in CAMPAIGNS):
            raise ValueError("Pilot must contain both complete campaigns in every loop/sector")
    means = {loop: sum(arrays[s][t][loop].mean(0) for s in SECTORS for t in CAMPAIGNS) / 2 for loop in LOOPS}
    jac = {loop: row[8] for loop, row in jacobians(means).items()}
    if any(not np.isfinite(x).all() for x in jac.values()):
        raise ValueError("Pilot produced a nonfinite C8 assembly Jacobian")
    inventory = load(ROOT / "inputs" / "inventory.json")
    records = {}
    warnings = []
    source_groups = {}
    expected_groups = {(sector, tag, loop) for sector in SECTORS for tag in CAMPAIGNS for loop in LOOPS}
    seen = set()
    for item in m["groups"]:
        group, cfg = group_of(pilot, m, item["name"])
        sector, tag, loop = cfg["sector"], cfg["campaign"], cfg["L"]
        identity = (sector, tag, loop)
        if identity not in expected_groups or identity in seen:
            raise ValueError("Unexpected or duplicated pilot group")
        seen.add(identity)
        ids = {row["id"] for row in inventory[sector][str(loop)]}
        variances = projected_graph_variances(group / "graph_replicates.csv", cfg, ids, jac[loop], arrays[sector][tag][loop])
        costs, timing_hash = measured_graph_costs(group, cfg, m, mh, ids)
        for gid in sorted(ids):
            key = (sector, loop, gid)
            records.setdefault(key, {})[tag] = {"variance_proxy": variances[gid], "cost": costs[gid],
                                               "points": cfg["counts"][str(gid)], "replicates": cfg["replicates"]}
        low = sum(cfg["counts"][str(gid)] < 4096 for gid in ids)
        if low:
            warnings.append(f"{item['name']}: {low}/{len(ids)} pilot strata have fewer than 4096 points; rare endpoint events may be missed")
        if cfg["replicates"] < 32:
            warnings.append(f"{item['name']}: only {cfg['replicates']} pilot replicates; per-graph variance estimates are noisy")
        source_groups[item["name"]] = {"merged_sha256": merged_hashes[item["name"]],
                                        "graph_replicates_sha256": digest(group / "graph_replicates.csv"),
                                        "checkpoint_timing_sha256": timing_hash}
    if seen != expected_groups:
        raise ValueError("Pilot group coverage is incomplete")

    # Upper envelope of the two campaigns. At unequal pilot counts, n*Var is
    # the quantity with constant-per-point Monte Carlo scaling; this is a
    # budgeting approximation for scrambled Sobol sampling, not an error law.
    raw_v = {key: max(item[t]["variance_proxy"] for t in CAMPAIGNS) for key, item in records.items()}
    raw_c = {key: max(item[t]["cost"] for t in CAMPAIGNS) for key, item in records.items()}
    positive_v = [x for x in raw_v.values() if x > 0]
    global_v = statistics.median(positive_v) if positive_v else 1e-24
    if not positive_v:
        warnings.append("Every projected pilot variance was zero; allocation uses a positive fallback scale and has no measured precision forecast")
    positive_c = [x for x in raw_c.values() if x > 0]
    if not positive_c:
        raise ValueError("No positive measured kernel times; a core-hour allocation cannot be determined")
    global_c = max(positive_c)
    floors = {}
    metrics = {}
    for sector in SECTORS:
        for loop in LOOPS:
            keys = [key for key in records if key[:2] == (sector, loop)]
            floor = variance_floor([raw_v[key] for key in keys], floor_fraction, global_v)
            group_c = max((raw_c[key] for key in keys if raw_c[key] > 0), default=global_c)
            floors[f"{sector}:{loop}"] = floor
            for key in keys:
                missing_cost = raw_c[key] <= 0
                item = records[key]
                metrics[key] = {"variance_proxy": max(raw_v[key], floor), "raw_variance_proxy": raw_v[key],
                                "seconds_per_point": raw_c[key] if not missing_cost else group_c,
                                "variance_floor_applied": raw_v[key] < floor, "timing_floor_applied": missing_cost,
                                "pilot_points": {t: item[t]["points"] for t in CAMPAIGNS},
                                "pilot_replicates": {t: item[t]["replicates"] for t in CAMPAIGNS}}
    zero_costs = sum(item["timing_floor_applied"] for item in metrics.values())
    if zero_costs:
        warnings.append(f"{zero_costs} graph costs were zero at timer precision; the maximum positive group cost was substituted")
    keys = sorted(metrics)
    v = [metrics[key]["variance_proxy"] for key in keys]
    c = [metrics[key]["seconds_per_point"] for key in keys]
    budget_seconds = target_core_hours * 3600 / (2 * replicates)
    counts, allocation = allocate_counts(v, c, budget_seconds, minimum)
    nested = {sector: {str(loop): {} for loop in LOOPS} for sector in SECTORS}
    for (sector, loop, gid), n in zip(keys, counts):
        nested[sector][str(loop)][str(gid)] = n
    expected = {(s, int(loop), row["id"]) for s in SECTORS for loop, rows in inventory[s].items() for row in rows}
    if set(keys) != expected:
        raise ArithmeticError("Allocation does not contain the exact complete active graph inventory")
    # This is explicitly a forecast under MC scaling and neglected cross-graph
    # covariances. It must never be substituted for a production sampling SE.
    variance_forecast = math.fsum(x / n for x, n in zip(v, counts)) / (2 * replicates)
    return {"schema": SCHEMA, "dimension": 2, "order": 8,
            "inputs_manifest_sha256": m["inputs_manifest_sha256"],
            "source_manifest_sha256": mh, "pilot_seeds": [m["seed"]],
            "backend": m["backend"], "source_groups": source_groups,
            "accepted_tool_changes": changes, "replicates": replicates, "campaign_count": 2,
            "minimum_points": minimum, "maximum_points": MAX_POINTS,
            "counts": nested,
            "target_core_hours": target_core_hours,
            "estimated_kernel_core_hours": allocation["cost"] * 2 * replicates / 3600,
            "minimum_kernel_core_hours": allocation["floor_cost"] * 2 * replicates / 3600,
            "unspent_kernel_core_hours": allocation["unspent"] * 2 * replicates / 3600,
            "budget_basis": "Both campaigns times replicates; sum of measured per-task kernel wall times, approximating core time; loading, scheduler idle time and fixed overhead excluded",
            "method": "Floored continuous Neyman allocation sigma/sqrt(cost), rounded down to powers of two, then affordable marginal-gain doublings",
            "variance_model": "v_g=max over campaigns of n_pilot*Var(J_C8 dot complete graph jet); used for allocation only; no lower-order coefficient is imposed",
            "variance_floor_fraction": floor_fraction, "variance_floors_by_group": floors,
            "model_only_standard_error_forecast": math.sqrt(variance_forecast),
            "forecast_limitations": "Unvalidated Monte Carlo 1/n variance scaling for randomized Sobol sampling; marginal graph variances neglect cross-graph covariance; this is not a production error estimate",
            "jacobian_C8": {str(loop): row.tolist() for loop, row in jac.items()},
            "pilot_C8_used_only_to_locate_jacobian": float(coefficients(means)[8]),
            "metrics": {f"{s}:{loop}:{gid}": metrics[s, loop, gid] for s, loop, gid in keys},
            "warnings": warnings,
            "scope": "Frozen allocation only. Requires fresh production seeds; pilot samples must not enter the production estimate. Multipliers or a different replicate count change the recorded budget."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pilot", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target-core-hours", type=float, required=True,
                        help="total kernel core-hour budget for BOTH campaigns at the chosen replicate count")
    parser.add_argument("--replicates", type=int, default=64, help="production replicates per campaign")
    parser.add_argument("--min-points", type=int, default=4096)
    parser.add_argument("--variance-floor-fraction", type=float, default=0.1)
    parser.add_argument("--accept-tool-change", action="store_true", help="record accepted changes to the pilot's pinned post-processing tools")
    args = parser.parse_args()
    result = generate(args.pilot, args.target_core_hours, args.replicates, args.min_points,
                      args.variance_floor_fraction, args.accept_tool_change)
    if args.output.exists():
        if canon(load(args.output)) != canon(result):
            raise FileExistsError(f"Refusing to overwrite a different allocation: {args.output}")
        state = "identical allocation already present"
    else:
        dump(args.output, result)
        state = "written"
    for warning in result["warnings"]:
        print("pilot-allocation warning: " + warning, file=sys.stderr)
    print(json.dumps({"output": str(args.output), "state": state,
                      "graphs": sum(len(rows) for loops in result["counts"].values() for rows in loops.values()),
                      "estimated_kernel_core_hours": result["estimated_kernel_core_hours"],
                      "target_core_hours": result["target_core_hours"],
                      "model_only_standard_error_forecast": result["model_only_standard_error_forecast"],
                      "warnings": len(result["warnings"])}))


if __name__ == "__main__":
    main()
