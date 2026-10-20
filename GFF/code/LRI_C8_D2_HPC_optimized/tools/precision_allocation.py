#!/usr/bin/env python3
"""Freeze an independent C8 precision allocation from two complete pilot runs.

The variance proxy is the upper envelope of the two already regularized pilot
proxies. Point costs come from the latest pilot. Every graph retains its latest
actual points per replicate, with a separate stronger floor for free L8.
Neither source model's hypothetical allocation counts/budget are treated as
executed work. Source graph variances, timings, counts and hashes are checked
against the complete runs before a new allocation can be published.

This tool allocates only: no integration, pooling, trimming, coefficient
constraint, or change of sampling estimator occurs here.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np

from assemble import jacobians, load_campaign
from common import ROOT, canon, digest, dump, load, pow2, publish
from pilot_allocation import (CAMPAIGNS, LOOPS, MAX_POINTS, SECTORS,
                              measured_graph_costs, projected_graph_variances)
from production import group_of
from refinement_allocation import allocate_with_floors, problem


def local_name(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def verify_source(model_path, run_path):
    """Bind a frozen single-pilot model to its complete measured source run."""
    model_path, run_path = Path(model_path).resolve(), Path(run_path).resolve()
    model = load(model_path)
    # Reuse the existing exact inventory, metric, seed and schema validation.
    problem(model, replicates=4, minimum=4, pilot_multiplier=1)
    manifest, mh, arrays, merged_hashes, changes = load_campaign(run_path)
    if changes or model.get("accepted_tool_changes"):
        raise ValueError("Precision allocation requires unchanged source tools")
    if manifest.get("test_only") or manifest.get("purpose") != "pilot":
        raise ValueError("Both sources must be complete, explicitly labelled pilots")
    if manifest.get("primitive_mode") != "recompute":
        raise ValueError("Every source must recompute all primitive jets")
    if model["source_manifest_sha256"] != mh:
        raise ValueError("Model source manifest does not match the supplied run")
    if model["inputs_manifest_sha256"] != manifest["inputs_manifest_sha256"]:
        raise ValueError("Model and source run use different graph inputs")
    if model["backend"] != manifest["backend"]:
        raise ValueError("Model and source run use different numerical backends")
    if model["pilot_seeds"] != [manifest["seed"]]:
        raise ValueError("Each source model must describe exactly its supplied pilot")
    means = {L: sum(arrays[s][t][L].mean(0) for s in SECTORS for t in CAMPAIGNS) / 2
             for L in LOOPS}
    jac = {L: value[8] for L, value in jacobians(means).items()}
    for L in LOOPS:
        if not np.array_equal(jac[L], np.asarray(model["jacobian_C8"][str(L)])):
            raise ValueError("Model C8 Jacobian differs from its source run")
    observations = {}
    samples = checkpoints = 0
    expected_groups = {f"{t}_{s}_L{L}" for t in CAMPAIGNS for s in SECTORS for L in LOOPS}
    if {g["name"] for g in manifest["groups"]} != expected_groups:
        raise ValueError("Incomplete source loop/sector/campaign coverage")
    for item in manifest["groups"]:
        group, cfg = group_of(run_path, manifest, item["name"])
        s, t, L = cfg["sector"], cfg["campaign"], cfg["L"]
        ids = {int(gid) for gid in cfg["counts"]}
        provenance = model["source_groups"][cfg["name"]]
        if provenance["merged_sha256"] != merged_hashes[cfg["name"]]:
            raise ValueError("Source model has a different merged-file hash")
        if provenance["graph_replicates_sha256"] != digest(group / "graph_replicates.csv"):
            raise ValueError("Source model has a different graph-replicate hash")
        variance = projected_graph_variances(group / "graph_replicates.csv", cfg, ids,
                                             jac[L], arrays[s][t][L])
        costs, timing_hash = measured_graph_costs(group, cfg, manifest, mh, ids)
        if provenance["checkpoint_timing_sha256"] != timing_hash:
            raise ValueError("Source model has different verified checkpoint timings")
        samples += cfg["samples"]
        checkpoints += sum(1 for _ in (group / "checkpoints").glob("*.json"))
        for gid in ids:
            key = f"{s}:{L}:{gid}"
            metric = model["metrics"][key]
            if metric["pilot_points"][t] != cfg["counts"][str(gid)]:
                raise ValueError("Model pilot points differ from actual source points")
            if metric["pilot_replicates"][t] != cfg["replicates"]:
                raise ValueError("Model pilot replicates differ from the actual run")
            observations.setdefault(key, {})[t] = (variance[gid], costs[gid])
    for key, observation in observations.items():
        if set(observation) != set(CAMPAIGNS):
            raise ValueError("Graph is missing a source campaign")
        metric = model["metrics"][key]
        raw = max(value[0] for value in observation.values())
        cost = max(value[1] for value in observation.values())
        group_key = ":".join(key.split(":")[:2])
        regularized = max(raw, model["variance_floors_by_group"][group_key])
        if metric["raw_variance_proxy"] != raw or metric["variance_proxy"] != regularized:
            raise ValueError("Source model variance differs from the verified graph jets")
        if cost <= 0 or metric["seconds_per_point"] != cost:
            raise ValueError("Source model point cost differs from verified checkpoint times")
    provenance = {
        "run": local_name(run_path), "source_manifest_sha256": mh,
        "model": local_name(model_path), "model_sha256": digest(model_path),
        "pilot_seed": manifest["seed"], "backend": manifest["backend"],
        "executable_sha256": manifest["executable_sha256"],
        "actual_source_points": samples, "verified_checkpoint_files": checkpoints,
        "source_groups": model["source_groups"], "jacobian_C8": model["jacobian_C8"],
        "source_model_hypothetical_allocation": {
            "target_core_hours": model["target_core_hours"], "replicates": model["replicates"],
            "scope": "Model allocation only; these are not the executed source-run counts or budget"},
    }
    return model, provenance


def generate(earlier, latest, earlier_provenance, latest_provenance,
             target_core_hours=35., replicates=16, minimum=64, free_l8_floor=128):
    """Pure floor-constrained allocation once the measured models are verified."""
    if not math.isfinite(target_core_hours) or target_core_hours <= 0:
        raise ValueError("Positive finite kernel core-hour budget required")
    if type(free_l8_floor) is not int or not pow2(free_l8_floor) or not minimum <= free_l8_floor <= MAX_POINTS:
        raise ValueError("Free-L8 floor must be a power of two at least the general minimum")
    keys, _, costs, floors, _ = problem(latest, replicates, minimum, pilot_multiplier=1)
    problem(earlier, replicates, minimum, pilot_multiplier=1)
    if earlier["inputs_manifest_sha256"] != latest["inputs_manifest_sha256"] or earlier["backend"] != latest["backend"]:
        raise ValueError("Source models must use the same graph inputs and backend")
    if set(earlier["metrics"]) != set(latest["metrics"]):
        raise ValueError("Source models do not cover the same graph inventory")
    if set(earlier["pilot_seeds"]) & set(latest["pilot_seeds"]):
        raise ValueError("Source models must come from distinct pilot seeds")
    result = copy.deepcopy(latest)
    values = []
    for i, (sector, L, gid) in enumerate(keys):
        key = f"{sector}:{L}:{gid}"
        old, new = earlier["metrics"][key], latest["metrics"][key]
        metric = result["metrics"][key]
        value = max(old["variance_proxy"], new["variance_proxy"])
        metric["raw_variance_proxy"] = max(old["raw_variance_proxy"], new["raw_variance_proxy"])
        metric["variance_proxy"] = value
        metric["variance_floor_applied"] = value > metric["raw_variance_proxy"]
        metric["source_variance_proxies"] = {"earlier": old["variance_proxy"], "latest": new["variance_proxy"]}
        values.append(value)
        if sector == "free" and L == 8:
            floors[i] = max(floors[i], free_l8_floor)
    counts, info = allocate_with_floors(values, costs, floors,
                                       target_core_hours * 3600 / (2 * replicates))
    nested = {s: {str(L): {} for L in LOOPS} for s in SECTORS}
    nested_floors = copy.deepcopy(nested)
    groups = []
    for (s, L, gid), n, floor in zip(keys, counts, floors):
        nested[s][str(L)][str(gid)] = n
        nested_floors[s][str(L)][str(gid)] = floor
    for s in SECTORS:
        for L in LOOPS:
            ii = [i for i, key in enumerate(keys) if key[:2] == (s, L)]
            groups.append({"sector": s, "loop": L, "graphs": len(ii),
                "minimum_points_per_graph_replicate": min(counts[i] for i in ii),
                "maximum_points_per_graph_replicate": max(counts[i] for i in ii),
                "graphs_at_retention_floor": sum(counts[i] == floors[i] for i in ii),
                "total_points_both_campaigns": sum(counts[i] for i in ii) * 2 * replicates,
                "kernel_core_hours": math.fsum(costs[i] * counts[i] for i in ii) * 2 * replicates / 3600,
                "floor_kernel_core_hours": math.fsum(costs[i] * floors[i] for i in ii) * 2 * replicates / 3600,
                "model_only_variance_contribution": math.fsum(values[i] / counts[i] for i in ii) / (2 * replicates)})
    forecast = math.sqrt(math.fsum(v / n for v, n in zip(values, counts)) / (2 * replicates))
    result.update(
        pilot_seeds=sorted(set(earlier["pilot_seeds"] + latest["pilot_seeds"])),
        replicates=replicates, campaign_count=2, minimum_points=minimum, maximum_points=MAX_POINTS,
        counts=nested, target_core_hours=target_core_hours,
        estimated_kernel_core_hours=info["cost"] * 2 * replicates / 3600,
        minimum_kernel_core_hours=info["floor_cost"] * 2 * replicates / 3600,
        unspent_kernel_core_hours=info["unspent"] * 2 * replicates / 3600,
        model_only_standard_error_forecast=forecast,
        variance_floors_by_group={k: max(earlier["variance_floors_by_group"][k], value)
                                 for k, value in latest["variance_floors_by_group"].items()},
        method="Upper envelope of two verified pilot variance proxies, latest measured costs, and exact N_g=f_g*m_g floor substitution into the existing power-of-two Neyman allocator",
        variance_model="v_g=max(earlier regularized proxy, latest regularized proxy), each formed from max_campaign N_pilot*Var(J_C8 dot graph jet); allocation only",
        precision_source_pilots={"earlier": earlier_provenance, "latest": latest_provenance},
        precision_floor_policy={"formula": "max(latest_actual_points_a, latest_actual_points_b, minimum_points, free_L8_floor_if_applicable)",
            "minimum_points": minimum, "free_L8_floor": free_l8_floor, "floors": nested_floors,
            "common_multiplier_cap": info["common_multiplier_cap"],
            "common_multiplier_cap_reached": info["point_cap_reached"]},
        precision_variance_envelope={"source": "Maximum of each source model's already regularized variance proxy",
            "equivalent_rule": "max(earlier raw proxy, latest raw proxy, earlier group floor, latest group floor)",
            "cost_source": "Latest complete pilot's per-graph max(a,b) seconds per point",
            "point_retention_source": "Latest complete pilot's measured per-graph points; not the model's hypothetical allocation counts"},
        loop_sector_summary=groups,
        scope="Precommitted independent precision allocation only. Both pilot seeds are excluded and every pilot sample is excluded from the new estimate. The 1/N forecast neglects graph covariance and is not a measured error bar. No numerical coefficient or uncertainty is reported by this tool.")
    for obsolete in ("refinement_source_allocation", "refinement_floor_policy"):
        result.pop(obsolete, None)
    result["warnings"] = list(dict.fromkeys(earlier.get("warnings", []) + latest.get("warnings", []) + [
        "Both sources have noisy graph variances; their upper envelope and positive point floors do not bound rare-region sampling error",
        "Budget counts both campaigns and all replicates but excludes loading, scheduling, and post-processing overhead",
        "Fresh independent streams are required; the integration runner must retain equal fixed campaign weights and whole-replicate covariance"]))
    summary = {"schema": "c8-d2-precision-allocation-summary-1", "graphs": len(keys),
        "replicates_per_campaign": replicates, "campaigns": 2,
        "total_points": sum(counts) * 2 * replicates,
        "target_kernel_core_hours": target_core_hours,
        "allocated_kernel_core_hours": result["estimated_kernel_core_hours"],
        "floor_kernel_core_hours": result["minimum_kernel_core_hours"],
        "model_only_standard_error_forecast": forecast, "excluded_pilot_seeds": result["pilot_seeds"],
        "loop_sector_summary": groups,
        "checks": {"exact_graph_inventory": True, "positive_power_of_two_counts": all(pow2(n) for n in counts),
            "latest_point_counts_retained": all(n >= f for n, f in zip(counts, floors)),
            "both_pilot_seeds_excluded": len(result["pilot_seeds"]) == 2,
            "within_precommitted_kernel_budget": result["estimated_kernel_core_hours"] <= target_core_hours * (1 + 1e-12)},
        "scope": "Planning statistics and invariants only; the forecast is not a measured sampling uncertainty"}
    return result, summary


def save_identical(path, value):
    path = Path(path)
    if path.exists():
        if canon(load(path)) != canon(value):
            raise FileExistsError(f"Refusing to overwrite a different allocation product: {path}")
    else:
        dump(path, value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--earlier-model", type=Path, required=True)
    parser.add_argument("--earlier-run", type=Path, required=True)
    parser.add_argument("--latest-model", type=Path, required=True)
    parser.add_argument("--latest-run", type=Path, required=True)
    parser.add_argument("--target-core-hours", type=float, default=35.)
    parser.add_argument("--replicates", type=int, default=16)
    parser.add_argument("--min-points", type=int, default=64)
    parser.add_argument("--free-l8-floor", type=int, default=128)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    earlier, ep = verify_source(args.earlier_model, args.earlier_run)
    latest, lp = verify_source(args.latest_model, args.latest_run)
    result, summary = generate(earlier, latest, ep, lp, args.target_core_hours,
                               args.replicates, args.min_points, args.free_l8_floor)
    save_identical(args.output, result)
    summary.update(allocation=local_name(args.output), allocation_sha256=digest(args.output),
                   generator_sha256=digest(Path(__file__)))
    if args.summary:
        save_identical(args.summary, summary)
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
