#!/usr/bin/env python3
"""Inspect a complete C8 result without changing its estimator or allowance.

Whole randomized group replicates determine the reported sampling variance.
Graph jets are projected through the same C8 Jacobian before their sample
variances are taken. These graph-level diagonal estimates are useful for
allocation and diagnosis; their finite-sample sum need not equal the variance
of the group sum. Neither diagnostic establishes point-count convergence.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP, localcontext
import json
import math
from pathlib import Path

import numpy as np

import assemble
from common import ROOT, canon, digest, dump, load
from production import group_of


SCHEMA = "c8-d2-result-diagnostics-1"


def ratio(a, b):
    return float(a / b) if b else None


def rounded_sampling_display(value, se, significant_digits=2, purpose="pilot"):
    """Round the point estimate to the place of a two-digit sampling SE.

    This is display rounding, not a statement that these digits are converged.
    """
    if not math.isfinite(value) or not math.isfinite(se) or se < 0:
        raise ValueError("Finite estimate and nonnegative sampling SE required")
    if not se:
        return {"estimate": format(value, ".12g"), "sampling_se": "0",
                "sampling_se_significant_digits": significant_digits}
    exponent = math.floor(math.log10(se)) - significant_digits + 1
    with localcontext() as ctx:
        ctx.prec = 40
        quantum = Decimal(1).scaleb(exponent)
        uncertainty = Decimal(str(se)).quantize(quantum, rounding=ROUND_HALF_UP)
        # A carry such as 9.99 -> 10 changes the last retained decimal place.
        exponent = uncertainty.adjusted() - significant_digits + 1
        quantum = Decimal(1).scaleb(exponent)
        uncertainty = uncertainty.quantize(quantum, rounding=ROUND_HALF_UP)
        central = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    estimator = "Pilot estimator" if purpose == "pilot" else "Numerical estimator"
    return {"estimate": format(central, "f"), "sampling_se": format(uncertainty, "f"),
            "sampling_se_significant_digits": significant_digits,
            "decimal_quantum": format(quantum, "f"),
            "qualification": estimator + " with estimated sampling SE; this diagnostic does not establish numerical convergence."}


def graph_projections(path, cfg, jacobian, expected_batches, active_ids):
    """Read and validate graph replicates while preserving all jet covariance."""
    ids = sorted(active_ids)
    counts = {int(k): v for k, v in cfg["counts"].items()}
    if set(counts) != set(ids) or any(type(v) is not int or v <= 0 for v in counts.values()):
        raise ValueError("Incomplete active graph counts")
    row_of = {gid: i for i, gid in enumerate(ids)}
    reps = cfg["replicates"]
    dim = 2 * (9 - cfg["L"])
    projected = np.zeros((len(ids), reps), dtype=np.longdouble)
    seen = np.zeros((len(ids), reps), dtype=bool)
    totals = np.zeros((reps, dim), dtype=np.longdouble)
    magnitudes = np.zeros_like(totals)
    jacobian = np.asarray(jacobian, dtype=np.longdouble)
    with Path(path).open(newline="") as handle:
        reader = csv.reader(handle)
        if next(reader, None) != ["replicate", "graph"] + [f"jet_{j}" for j in range(dim)]:
            raise ValueError("Wrong graph replicate header")
        for row in reader:
            if len(row) != dim + 2:
                raise ValueError("Wrong graph replicate row width")
            rep, gid = map(int, row[:2])
            if gid not in row_of or not 0 <= rep < reps:
                raise ValueError("Unexpected graph replicate")
            index = row_of[gid]
            if seen[index, rep]:
                raise ValueError("Duplicate graph replicate")
            seen[index, rep] = True
            values = np.asarray(row[2:], dtype=np.longdouble)
            if not np.isfinite(values).all():
                raise ValueError("Nonfinite graph jet")
            projected[index, rep] = jacobian @ values
            totals[rep] += values
            magnitudes[rep] += abs(values)
    if not seen.all():
        raise ValueError("Missing graph replicates")
    expected = np.asarray(expected_batches, dtype=np.longdouble)
    if expected.shape != totals.shape or np.any(abs(totals - expected) > 1e-12 * np.maximum(1, magnitudes)):
        raise ValueError("Graph jets do not reproduce merged batches")
    return ids, projected


def scalar_replicate_shape(values):
    values = np.asarray(values, dtype=np.longdouble)
    centered = values - values.mean()
    squares = centered * centered
    second = squares.mean()
    return {"descriptive_skewness": float((centered ** 3).mean() / second ** 1.5) if second else None,
            "largest_squared_deviation_share": float(squares.max() / squares.sum()) if squares.sum() else None,
            "minimum": float(values.min()), "maximum": float(values.max())}


def compare_with_run(directory, manifest, primary, primary_configs, comparison, accept_tool_change=False):
    """Compare independently randomized complete runs without pooling them."""
    comparison = Path(comparison).resolve()
    if comparison == directory:
        raise ValueError("Comparison must be a different complete run")
    baseline = load(comparison / "C8_result.json")
    if (baseline.get("schema") != assemble.RESULT_SCHEMA or baseline.get("dimension") != 2
            or baseline.get("order") != 8 or baseline.get("test_only") or baseline.get("C8_full") is None):
        raise ValueError("Comparison must be a complete assembled C8 result")
    cm, cmh, arrays, hashes, changes = assemble.load_campaign(comparison, accept_tool_change)
    if cm.get("test_only") or cm.get("primitive_mode") != "recompute":
        raise ValueError("Comparison must recompute every active graph and primitive jet")
    if baseline["source_manifest_sha256"] != cmh or baseline["merged_sha256"] != hashes:
        raise ValueError("Comparison result provenance does not match its merged data")
    if cm["inputs_manifest_sha256"] != manifest["inputs_manifest_sha256"]:
        raise ValueError("Comparison graph/analytic inputs differ from the primary run")
    if cm["backend"] != manifest["backend"] or baseline["backend"] != primary["backend"] or baseline["backend"] != cm["backend"]:
        raise ValueError("Comparison and primary numerical backends differ")
    if baseline["epsilon"] != primary["epsilon"] or cm["order"] != manifest["order"] or cm["dimension"] != manifest["dimension"]:
        raise ValueError("Comparison convention, dimension or perturbative order differs")
    if cm["seed"] == manifest["seed"]:
        raise ValueError("Comparison reuses the primary base seed")
    means = {s: {L: sum(x[L].mean(0) for x in arrays[s].values()) / 2 for L in range(3, 9)}
             for s in ("free", "power")}
    for sector in means:
        for loop, values in means[sector].items():
            if not np.array_equal(values, np.asarray(baseline["means"][sector][str(loop)])):
                raise ValueError("Comparison means differ from its merged data")
    full_means = {L: means["free"][L] + means["power"][L] for L in range(3, 9)}
    if not np.array_equal(assemble.coefficients(full_means), np.asarray(baseline["coefficients"])):
        raise ValueError("Comparison coefficients do not reproduce from its merged means")
    comparison_configs = {}
    for item in cm["groups"]:
        _, cfg = group_of(comparison, cm, item["name"])
        key = cfg["sector"], cfg["campaign"], cfg["L"]
        if key in comparison_configs:
            raise ValueError("Duplicate comparison group")
        comparison_configs[key] = cfg
    if set(primary_configs) != set(comparison_configs):
        raise ValueError("Comparison does not have identical loop/sector/campaign coverage")
    all_configs = list(primary_configs.values()) + list(comparison_configs.values())
    if any(cfg.get("seed_scheme") != "hashed" for cfg in all_configs):
        raise ValueError("Independent comparison requires the C8 hashed stream scheme")
    native_overlap = ({cfg["seed"] for cfg in primary_configs.values()}
                      & {cfg["seed"] for cfg in comparison_configs.values()})
    net_overlap = ({cfg["net"]["seed"] for cfg in primary_configs.values()}
                   & {cfg["net"]["seed"] for cfg in comparison_configs.values()})
    if native_overlap or net_overlap:
        raise ValueError("Comparison and primary share a native or net seed")
    allocation = load(directory / "allocation.json") if manifest.get("allocation_file_sha256") else None
    if allocation is not None and manifest["seed"] in allocation.get("pilot_seeds", []):
        raise ValueError("Primary integration reuses a seed from its allocation pilot")
    point_rows = []
    increased = decreased = unchanged = 0
    for loop in range(3, 9):
        for sector in ("free", "power"):
            point_ratios = []
            primary_samples = comparison_samples = 0
            row_increased = row_decreased = row_unchanged = 0
            replicate_counts = {}
            for tag in ("a", "b"):
                cfg = primary_configs[sector, tag, loop]
                old = comparison_configs[sector, tag, loop]
                if set(cfg["counts"]) != set(old["counts"]):
                    raise ValueError("Primary and comparison graph count identities differ")
                replicate_counts[tag] = {"primary": cfg["replicates"], "comparison": old["replicates"]}
                for gid, n in cfg["counts"].items():
                    previous = old["counts"][gid]
                    if n <= 0 or previous <= 0:
                        raise ValueError("A comparison graph has no samples")
                    point_ratios.append(n / previous)
                    row_increased += n > previous
                    row_decreased += n < previous
                    row_unchanged += n == previous
                    primary_samples += n * cfg["replicates"]
                    comparison_samples += previous * old["replicates"]
            increased += row_increased
            decreased += row_decreased
            unchanged += row_unchanged
            point_rows.append({"loop": loop, "sector": sector,
                "minimum_point_ratio": min(point_ratios), "median_point_ratio": float(np.median(point_ratios)),
                "maximum_point_ratio": max(point_ratios), "graph_campaign_pairs": len(point_ratios),
                "increased_graph_campaign_pairs": row_increased, "decreased_graph_campaign_pairs": row_decreased,
                "unchanged_graph_campaign_pairs": row_unchanged, "replicates": replicate_counts,
                "total_samples_ratio": primary_samples / comparison_samples})
    coefficients = []
    for order in range(3, 9):
        difference = primary["coefficients"][order] - baseline["coefficients"][order]
        denominator = math.hypot(primary["standard_errors"][order], baseline["standard_errors"][order])
        coefficients.append({"order": order, "primary": primary["coefficients"][order],
            "comparison": baseline["coefficients"][order], "difference": difference,
            "combined_sampling_se": denominator, "difference_over_combined_sampling_se": ratio(difference, denominator)})
    output = {"comparison_run": comparison.name,
        "comparison_result_sha256": digest(comparison / "C8_result.json"),
        "comparison_manifest_sha256": cmh, "comparison_merged_sha256": hashes,
        "primary_base_seed": manifest["seed"], "comparison_base_seed": cm["seed"],
        "same_inputs_order_and_backend": True,
        "same_executable": manifest["executable_sha256"] == cm["executable_sha256"],
        "fresh_stream_checks": {"distinct_base_seeds": True, "C8_hashed_stream_scheme": True,
            "shared_native_seeds": 0, "shared_net_seeds": 0,
            "primary_seed_reused_from_allocation_pilot": False},
        "adaptive_allocation_based_on_comparison": allocation is not None and cm["seed"] in allocation.get("pilot_seeds", []),
        "primary_estimator_pooled_with_comparison": False,
        "C8_primary": primary["C8_full"], "C8_comparison": baseline["C8_full"],
        "sampling_se_primary": primary["sampling_standard_error"],
        "sampling_se_comparison": baseline["sampling_standard_error"],
        "C8_difference": coefficients[-1]["difference"],
        "C8_difference_over_combined_sampling_se": coefficients[-1]["difference_over_combined_sampling_se"],
        "sampling_se_improvement_factor": ratio(baseline["sampling_standard_error"], primary["sampling_standard_error"]),
        "coefficients": coefficients, "point_ratios_by_loop_sector": point_rows,
        "point_count_refinement_performed": increased > 0,
        "all_point_counts_nondecreasing": decreased == 0,
        "all_point_counts_strictly_increased": decreased == 0 and unchanged == 0,
        "increased_graph_campaign_pairs": increased, "decreased_graph_campaign_pairs": decreased,
        "unchanged_graph_campaign_pairs": unchanged,
        "convergence_established_by_comparison": False,
        "scope": "Fresh integration streams with separate estimators. Point ratios describe points per graph-replicate; total sample ratios also include replicate counts. With allocation chosen adaptively from a pilot, differences and sampling-SE pulls are diagnostics, not a calibrated confidence test or proof of convergence."}
    if changes:
        output["accepted_comparison_tool_changes"] = changes
    return output


def inspect(directory, top=25, accept_tool_change=False, comparison=None):
    directory = Path(directory).resolve()
    result_path = directory / "C8_result.json"
    r = load(result_path)
    if (r.get("schema") != assemble.RESULT_SCHEMA or r.get("dimension") != 2 or r.get("order") != 8
            or r.get("test_only") or r.get("C8_full") is None):
        raise ValueError("A complete assembled C8 result is required")
    manifest, mh, arrays, merged_hashes, changes = assemble.load_campaign(directory, accept_tool_change)
    if manifest.get("test_only") or manifest.get("primitive_mode") != "recompute":
        raise ValueError("All active graphs and primitive jets must be recomputed")
    if r["source_manifest_sha256"] != mh or r["merged_sha256"] != merged_hashes:
        raise ValueError("Result provenance does not match the complete merged campaign")
    means = {s: {L: sum(x[L].mean(0) for x in arrays[s].values()) / 2 for L in range(3, 9)}
             for s in ("free", "power")}
    for s in means:
        for L, values in means[s].items():
            if not np.array_equal(values, np.asarray(r["means"][s][str(L)])):
                raise ValueError("Saved input means differ from merged data")
    full_means = {L: means["free"][L] + means["power"][L] for L in range(3, 9)}
    if not np.array_equal(assemble.coefficients(full_means), np.asarray(r["coefficients"])):
        raise ValueError("Saved coefficients differ from assembly of merged means")
    jac = {L: a[8] for L, a in assemble.jacobians(full_means).items()}
    total_variance = float(r["sampling_standard_error"]) ** 2
    if not math.isfinite(total_variance):
        raise ValueError("Nonfinite reported sampling variance")
    inventory = load(ROOT / "inputs/inventory.json")
    groups, graph_records, primary_configs = [], {}, {}
    expected_bootstrap_variance = 0.
    for item in manifest["groups"]:
        group, cfg = group_of(directory, manifest, item["name"])
        sector, tag, loop = cfg["sector"], cfg["campaign"], cfg["L"]
        primary_configs[sector, tag, loop] = cfg
        reps = cfg["replicates"]
        ids, projected = graph_projections(group / "graph_replicates.csv", cfg, jac[loop],
                                           arrays[sector][tag][loop], {x["id"] for x in inventory[sector][str(loop)]})
        graph_var = projected.var(axis=1, ddof=1) / (4 * reps)
        group_projection = np.asarray(arrays[sector][tag][loop], dtype=np.longdouble) @ np.asarray(jac[loop], dtype=np.longdouble)
        group_var = float(group_projection.var(ddof=1) / (4 * reps))
        diagonal = float(graph_var.sum())
        expected_bootstrap_variance += group_var * (reps - 1) / reps
        group_stats = {"name": cfg["name"], "sector": sector, "campaign": tag, "loop": loop,
                       "graphs": len(ids), "replicates": reps,
                       "minimum_points_per_graph_replicate": min(cfg["counts"].values()),
                       "maximum_points_per_graph_replicate": max(cfg["counts"].values()),
                       "bits": cfg["net"]["bits"], "importance_rate": cfg["rate"],
                       "sampling_variance": group_var, "variance_fraction": ratio(group_var, total_variance),
                       "sum_graph_diagonal_variances": diagonal,
                       "empirical_cross_graph_covariance_sum": group_var - diagonal,
                       "projected_replicates": [float(x) for x in group_projection],
                       "replicate_shape": scalar_replicate_shape(group_projection)}
        groups.append(group_stats)
        for i, gid in enumerate(ids):
            row = graph_records.setdefault((sector, loop, gid), {"sector": sector, "loop": loop, "graph": gid,
                        "diagonal_sampling_variance": 0., "campaigns": {}})
            variance = float(graph_var[i])
            row["diagonal_sampling_variance"] += variance
            row["campaigns"][tag] = {"points_per_replicate": cfg["counts"][str(gid)], "replicates": reps,
                                      "projected_mean": float(projected[i].mean()),
                                      "diagonal_sampling_variance": variance,
                                      "replicate_shape": scalar_replicate_shape(projected[i])}
    aggregate_variance = math.fsum(g["sampling_variance"] for g in groups)
    if not math.isclose(aggregate_variance, total_variance, rel_tol=1e-8, abs_tol=1e-12):
        raise ValueError("Projected replicate variance does not reproduce the reported variance")
    diagonal_total = math.fsum(row["diagonal_sampling_variance"] for row in graph_records.values())
    ranked = sorted(graph_records.values(), key=lambda row: (-row["diagonal_sampling_variance"], row["sector"], row["loop"], row["graph"]))
    for row in ranked:
        row["diagonal_variance_fraction"] = ratio(row["diagonal_sampling_variance"], diagonal_total)
        row["equivalent_sampling_se"] = math.sqrt(row["diagonal_sampling_variance"])
        row["pooled_projected_mean"] = (row["campaigns"]["a"]["projected_mean"] + row["campaigns"]["b"]["projected_mean"]) / 2
    loop_sectors = []
    for loop in range(3, 9):
        for sector in ("free", "power"):
            chosen = [g for g in groups if g["loop"] == loop and g["sector"] == sector]
            variance = math.fsum(g["sampling_variance"] for g in chosen)
            loop_sectors.append({"loop": loop, "sector": sector,
                "sampling_se": math.sqrt(variance), "sampling_variance": variance,
                "variance_fraction": ratio(variance, total_variance),
                "sum_graph_diagonal_variances": math.fsum(g["sum_graph_diagonal_variances"] for g in chosen)})
    loop_sectors.sort(key=lambda row: -row["sampling_variance"])
    sigma = float(r["sampling_standard_error"])
    campaign_a, campaign_b = (r["campaigns"][t] for t in ("a", "b"))
    campaign_difference = campaign_a["C8"] - campaign_b["C8"]
    half_values = [h[8] for h in r["half_streams"]]
    bootstrap = None
    if r["bootstrap"]:
        bs = r["bootstrap"]
        bootstrap = {"resamples": bs["replicates"], "C8_se": bs["full_se"][8], "C8_bias": bs["bias"][8],
                     "se_over_sampling_se": ratio(bs["full_se"][8], sigma),
                     "bias_over_sampling_se": ratio(bs["bias"][8], sigma),
                     "linear_empirical_resampling_expected_se": math.sqrt(expected_bootstrap_variance),
                     "se_over_linear_empirical_expectation": ratio(bs["full_se"][8], math.sqrt(expected_bootstrap_variance)),
                     "note": "Conditional replicate bootstrap; with R observations a linear empirical bootstrap variance has factor (R-1)/R relative to the unbiased covariance estimate. It cannot detect regions missed by all observations."}
    extended_means = {L: np.asarray(values, dtype=np.longdouble) for L, values in full_means.items()}
    original_two_loop = assemble.B2
    try:
        assemble.B2 = np.asarray(load(ROOT / "inputs/two_loop.json")["B2"], dtype=np.longdouble)
        extended = assemble.coefficients(extended_means)[8]
    finally:
        assemble.B2 = original_two_loop
    rounding_difference = float(extended - np.longdouble(r["C8_full"]))
    result = {"schema": SCHEMA, "purpose": r["purpose"], "source_manifest_sha256": mh,
        "source_result_sha256": digest(result_path), "source_merged_sha256": merged_hashes,
        "C8": r["C8_full"], "sampling_se": sigma,
        "rounded_display": rounded_sampling_display(r["C8_full"], sigma, purpose=r["purpose"]),
        "publication_precision_established": False,
        "point_count_refinement_assessed": False,
        "loop_sector_variance": loop_sectors, "groups": groups,
        "graph_variance_diagnostics": {"graphs": len(ranked), "sum_diagonal_variances": diagonal_total,
            "reported_group_sampling_variance": total_variance,
            "diagonal_to_reported_variance_ratio": ratio(diagonal_total, total_variance),
            "top_1_diagonal_fraction": ratio(math.fsum(row["diagonal_sampling_variance"] for row in ranked[:1]), diagonal_total),
            "top_10_diagonal_fraction": ratio(math.fsum(row["diagonal_sampling_variance"] for row in ranked[:10]), diagonal_total),
            "top_100_diagonal_fraction": ratio(math.fsum(row["diagonal_sampling_variance"] for row in ranked[:100]), diagonal_total),
            "top_graphs": ranked[:top],
            "note": "Per-graph diagonal variance estimates omit empirical cross-graph covariances and therefore do not exactly partition the reported group-replicate variance. A projected mean is a local C8 sensitivity; it is not an additive decomposition of the complete nonlinear coefficient."},
        "bootstrap": bootstrap,
        "campaigns": {"a": campaign_a, "b": campaign_b, "difference": campaign_difference,
            "difference_over_combined_se": ratio(campaign_difference, math.hypot(campaign_a["sampling_se"], campaign_b["sampling_se"])),
            "pooled_estimator_minus_average_campaign_estimator": r["C8_full"] - (campaign_a["C8"] + campaign_b["C8"]) / 2},
        "replicate_half_diagnostic": {"values": half_values,
            "largest_displacement": max(abs(x - r["C8_full"]) for x in half_values),
            "note": "The first and second halves partition randomized replicate indices, with fixed points per graph-replicate. This is not a within-stream point split or a doubled-point convergence test."},
        "assembly_rounding_check": {"longdouble_decimal_precision": int(np.finfo(np.longdouble).precision),
            "C8_extended": str(extended), "extended_minus_binary64": rounding_difference,
            "absolute_difference_over_sampling_se": ratio(abs(rounding_difference), sigma),
            "note": "Reassembles the same sampled mean jets and high-precision analytic two-loop input; this checks final assembly arithmetic only."},
        "lower_order_flags": [row for row in r["lower_order_checks"] if row["flag"]],
        "power_null_flags": [row for row in r["power_null_checks"] if row["flag"]],
        "scope": "Complete graph coverage supplies an estimator. Small randomized-replicate counts and small high-loop point counts do not establish integration convergence, a rigorous error bound, or field-theory validity."}
    if changes:
        result["accepted_tool_changes"] = changes
    if comparison is not None:
        result["comparison"] = compare_with_run(directory, manifest, r, primary_configs, comparison, accept_tool_change)
        result["point_count_refinement_assessed"] = True
        result["point_count_refinement_performed"] = result["comparison"]["point_count_refinement_performed"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--accept-tool-change", action="store_true")
    parser.add_argument("--comparison", type=Path, help="independent complete run to compare without pooling, normally the allocation pilot")
    args = parser.parse_args()
    if args.top < 1:
        raise ValueError("At least one top graph required")
    result = inspect(args.directory, args.top, args.accept_tool_change, args.comparison)
    destination = args.output or args.directory / "result_diagnostics.json"
    if destination.exists():
        if canon(load(destination)) != canon(result):
            raise ValueError(f"Different diagnostics already exist at {destination}; use another --output")
    else:
        dump(destination, result)
    summary = {"output": str(destination), "rounded_display": result["rounded_display"],
                      "bootstrap": result["bootstrap"], "loop_sector_variance": result["loop_sector_variance"],
                      "lower_order_flags": result["lower_order_flags"],
                      "top_10_graph_diagonal_fraction": result["graph_variance_diagnostics"]["top_10_diagonal_fraction"]}
    if "comparison" in result:
        summary["comparison"] = {key: result["comparison"][key] for key in
            ("comparison_run", "C8_difference", "C8_difference_over_combined_sampling_se",
             "sampling_se_improvement_factor", "point_count_refinement_performed", "all_point_counts_nondecreasing")}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
