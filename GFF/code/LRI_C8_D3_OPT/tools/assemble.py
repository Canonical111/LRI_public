#!/usr/bin/env python3
"""Assemble complete C8(3) campaigns, retaining all replicate covariance.

The power correction is F(f+p)-F(f), with lower-loop nonlinear terms. No
physical lower-order reference or assumed power cancellation is fitted.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
import json
from pathlib import Path

import numpy as np

from campaign import LOOPS, SCHEMA, SECTORS, validate_native
from io_utils import ROOT, checked, digest, load, object_hash, save
from rg import coefficients, jacobians, load_two_loop

REFERENCES = {
    3: (-0.3535815204331724, 0.0),
    4: (1.2280635453276232, 0.0),
    5: (-5.85035142075, 0.0),
    6: (33.57542664131543, 0.00011854952350322613),
    7: (-220.35448047392794, 0.031818800575016494),
}


def read_replicates(directory):
    """Verify every frozen task and sum chunks before statistical analysis."""
    directory = Path(directory).resolve()
    manifest = load(directory / "manifest.json")
    mh = digest(directory / "manifest.json")
    if manifest.get("schema") != SCHEMA or manifest["campaign_weights"] != {"a": 0.5, "b": 0.5}:
        raise ValueError("Unsupported campaign schema or altered campaign weights")
    if tuple(manifest["loops"]) != LOOPS or not manifest["all_loops"]:
        raise ValueError("C8 assembly requires every loop 3..8 in both sectors")
    if not manifest.get("coverage_verified") or "coverage.json" not in manifest["inputs"]:
        raise ValueError("Physical C8 assembly requires verified complete graph coverage")
    for name, expected in manifest["inputs"].items():
        checked(ROOT / "inputs" / name, expected)
    coverage = load(ROOT / "inputs/coverage.json")
    if coverage.get("complete") is not True or coverage.get("inventory_sha256") != manifest["inputs"]["inventory.json"]:
        raise ValueError("Coverage certificate does not certify this active graph inventory")
    inventory = load(ROOT / "inputs/inventory.json")
    groups = {g["name"]: g for g in manifest["groups"]}
    expected_groups = {f"{tag}_{sector}_L{loop}" for tag in ("a", "b") for sector in SECTORS for loop in LOOPS}
    if len(manifest["groups"]) != 24 or len(groups) != 24 or set(groups) != expected_groups:
        raise ValueError("Incomplete or duplicated independent group coverage")
    for name, group in groups.items():
        if name != f"{group['campaign']}_{group['sector']}_L{group['L']}":
            raise ValueError("Group label and scientific stratum disagree")
        expected_ids = {int(row["id"]) for row in inventory[group["sector"]][str(group["L"]) ]}
        actual_ids = [int(row["id"]) for row in group["graphs"]]
        if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != expected_ids:
            raise ValueError(f"Missing, extra, or duplicate active graphs in {name}")
    values = {}
    intervals = defaultdict(list)
    stats = defaultdict(lambda: {"cpu_seconds": 0.0, "points": 0, "quad": 0, "mp": 0})
    native_hashes = {}
    total_evaluations = 0
    with localcontext() as context:
        context.prec = 50
        for entry in manifest["jobs"]:
            base = directory / "jobs" / f"{entry['index']:06d}"
            job = load(base.with_suffix(".job.json"))
            if object_hash(job) != entry["sha256"] or job["index"] != entry["index"] or job["group"] != entry["group"]:
                raise ValueError("Job plan changed")
            receipt = load(base.with_suffix(".done.json"))
            if receipt["manifest_sha256"] != mh or receipt["job_sha256"] != entry["sha256"]:
                raise ValueError("Checkpoint provenance changed")
            output = base.with_suffix(".native.json")
            checked(output, receipt["native_sha256"])
            native_hashes[str(entry["index"])] = receipt["native_sha256"]
            data = load(output)
            group = groups[job["group"]]
            if job["L"] != group["L"]:
                raise ValueError("Job loop differs from its stratum")
            validate_native(data, job, group)
            if data.get("mp_backend") != manifest["executable"]["description"]["mp_backend"]:
                raise ValueError("Changed numerical backend")
            for row in data["rows"]:
                key = (job["group"], row["rep"], row["graph"])
                vector = values.setdefault(key, [Decimal(0)] * len(row["values"]))
                for k, value in enumerate(row["values"]):
                    vector[k] += Decimal(value)
                intervals[key].append((row["begin"], row["end"], row["total"]))
                counter = stats[(job["group"], row["graph"])]
                for field in ("quad", "mp"):
                    counter[field] += row[field]
                counter["cpu_seconds"] += row["seconds"]
                counter["points"] += row["end"] - row["begin"]
                total_evaluations += row["end"] - row["begin"]
        expected_keys = set()
        arrays = {s: {t: {} for t in ("a", "b")} for s in SECTORS}
        graph_arrays = {}
        for name, group in groups.items():
            count = manifest["replicates"]
            width = 2 * (9 - group["L"])
            combined = [[Decimal(0)] * width for _ in range(count)]
            for graph in group["graphs"]:
                ga = []
                for rep in range(count):
                    key = (name, rep, graph["id"])
                    expected_keys.add(key)
                    end = 0
                    for begin, stop, total in sorted(intervals.get(key, [])):
                        if begin != end or total != graph["points"] or stop <= begin:
                            raise ValueError(f"Gap, overlap, or changed net size for {key}")
                        end = stop
                    if end != graph["points"]:
                        raise ValueError(f"Incomplete net for {key}")
                    ga.append([float(x) for x in values[key]])
                    for k, x in enumerate(values[key]):
                        combined[rep][k] += x
                graph_arrays[name, graph["id"]] = np.asarray(ga, dtype=float)
            arrays[group["sector"]][group["campaign"]][group["L"]] = np.array(combined, dtype=float)
        if set(values) != expected_keys or total_evaluations != manifest["evaluations"]:
            raise ValueError("Unexpected, missing, or duplicated scientific work")
    return arrays, graph_arrays, stats, manifest, native_hashes


def covariance_of_mean(array):
    return np.cov(array, rowvar=False, ddof=1) / len(array)


def calculate(arrays, b2=None, bootstrap=512):
    b2 = load_two_loop() if b2 is None else np.asarray(b2)
    for sector in SECTORS:
        for tag in ("a", "b"):
            if set(arrays[sector][tag]) != set(LOOPS):
                raise ValueError("All six loop strata are required")
            for loop, a in arrays[sector][tag].items():
                if a.ndim != 2 or a.shape[1] != 2 * (9 - loop) or len(a) < 4 or not np.isfinite(a).all():
                    raise ValueError("Invalid complete replicate matrix")
    means = {
        s: {L: sum(arrays[s][t][L].mean(0) for t in ("a", "b")) / 2 for L in LOOPS}
        for s in SECTORS
    }
    vc = {
        s: {L: sum(covariance_of_mean(arrays[s][t][L]) for t in ("a", "b")) / 4 for L in LOOPS}
        for s in SECTORS
    }
    full_means = {L: means["free"][L] + means["power"][L] for L in LOOPS}
    full = coefficients(full_means, b2)
    free = coefficients(means["free"], b2)
    power = full - free
    J = jacobians(full_means, b2)
    Jf = jacobians(means["free"], b2)
    Jd = {L: J[L] - Jf[L] for L in LOOPS}
    contributions = {s: {L: J[L] @ vc[s][L] @ J[L].T for L in LOOPS} for s in SECTORS}
    cov = sum(v for block in contributions.values() for v in block.values())
    covf = sum(Jf[L] @ vc["free"][L] @ Jf[L].T for L in LOOPS)
    covd = sum(Jd[L] @ vc["free"][L] @ Jd[L].T + contributions["power"][L] for L in LOOPS)
    cross = sum(Jf[L] @ vc["free"][L] @ Jd[L].T for L in LOOPS)
    if not np.allclose(cov, covf + covd + cross + cross.T, rtol=2e-9, atol=1e-7):
        raise ArithmeticError("Full/power-free/power-correction covariance identity failed")
    standard_errors = np.sqrt(np.maximum(0, np.diag(cov)))
    individual = {}
    for tag in ("a", "b"):
        m = {L: arrays["free"][tag][L].mean(0) + arrays["power"][tag][L].mean(0) for L in LOOPS}
        jj = jacobians(m, b2)
        cv = sum(jj[L] @ sum(covariance_of_mean(arrays[s][tag][L]) for s in SECTORS) @ jj[L].T for L in LOOPS)
        individual[tag] = {"coefficients": coefficients(m, b2).tolist(), "standard_errors": np.sqrt(np.maximum(0, np.diag(cv))).tolist()}
    halves = []
    for half in (0, 1):
        m = {
            L: sum(
                a[half * len(a) // 2:(half + 1) * len(a) // 2].mean(0)
                for s in SECTORS for t in ("a", "b")
                for a in (arrays[s][t][L],)
            ) / 2 for L in LOOPS
        }
        halves.append(coefficients(m, b2).tolist())
    boot = None
    if bootstrap:
        if bootstrap < 2:
            raise ValueError("Bootstrap count must be zero or >=2")
        rng = np.random.default_rng(2026100808)
        outcomes = []
        differences = []
        for _ in range(bootstrap):
            m = {
                s: {L: sum(a[rng.integers(len(a), size=len(a))].mean(0) for t in ("a", "b") for a in (arrays[s][t][L],)) / 2 for L in LOOPS}
                for s in SECTORS
            }
            x = coefficients({L: m["free"][L] + m["power"][L] for L in LOOPS}, b2)
            outcomes.append(x)
            differences.append(x - coefficients(m["free"], b2))
        outcomes = np.asarray(outcomes)
        boot = {
            "resamples": bootstrap, "seed": 2026100808,
            "standard_errors": outcomes.std(0, ddof=1).tolist(),
            "estimated_plugin_bias": (outcomes.mean(0) - full).tolist(),
            "power_difference_errors": np.asarray(differences).std(0, ddof=1).tolist(),
            "diagnostic_only": True,
        }
    checks = []
    for order, (reference, reference_se) in REFERENCES.items():
        denominator = float(np.hypot(standard_errors[order], reference_se))
        pull = float((full[order] - reference) / denominator) if denominator else None
        checks.append({"order": order, "estimate": float(full[order]), "sampling_se": float(standard_errors[order]), "reference": reference, "reference_se": reference_se, "pull": pull, "flag_abs_pull_above_3": pull is not None and abs(pull) > 3})
    ab_se = np.hypot(individual["a"]["standard_errors"][8], individual["b"]["standard_errors"][8])
    ab_pull = float((individual["a"]["coefficients"][8] - individual["b"]["coefficients"][8]) / ab_se) if ab_se else None
    result = {
        "schema": "lri-c8-d3-estimator-1", "dimension": 3, "order": 8, "epsilon": "2s-3",
        "C8_estimate": float(full[8]), "sampling_standard_error": float(standard_errors[8]),
        "coefficients": full.tolist(), "standard_errors": standard_errors.tolist(),
        "covariance": cov.tolist(), "power_free_C8": float(free[8]),
        "power_free_se": float(np.sqrt(max(0, covf[8, 8]))),
        "power_correction": float(power[8]), "power_correction_se": float(np.sqrt(max(0, covd[8, 8]))),
        "power_free_correction_covariance": float(cross[8, 8]),
        "power_differences": power.tolist(), "power_difference_errors": np.sqrt(np.maximum(0, np.diag(covd))).tolist(),
        "means": {s: {str(L): a.tolist() for L, a in means[s].items()} for s in SECTORS},
        "input_covariances": {s: {str(L): a.tolist() for L, a in vc[s].items()} for s in SECTORS},
        "error_by_loop": {str(L): {s: float(np.sqrt(max(0, contributions[s][L][8, 8]))) for s in SECTORS} for L in LOOPS},
        "individual_campaigns": individual, "campaign_difference_pull": ab_pull,
        "half_streams": halves, "bootstrap": boot, "lower_order_checks": checks,
        "empirical_allowance": None,
        "uncertainty_scope": "Replicate-sampling covariance propagated through the finite-scheme fixed point; bootstrap is diagnostic. No rigorous interval, all-orders power-cancellation assumption, or independent field-theory certification.",
    }
    return result, J


def analyze(directory, bootstrap=512):
    arrays, graph_arrays, stats, manifest, native_hashes = read_replicates(directory)
    result, J = calculate(arrays, bootstrap=bootstrap)
    pilot = {}
    group_map = {g["name"]: g for g in manifest["groups"]}
    for (name, graph), array in graph_arrays.items():
        group = group_map[name]
        loop = group["L"]
        projection = array @ J[loop][8]
        target = pilot.setdefault(group["sector"], {}).setdefault(str(loop), {}).setdefault(str(graph), {})
        target[group["campaign"]] = {
            "projected_mean": float(projection.mean()), "projected_replicate_sd": float(projection.std(ddof=1)),
            "replicates": len(array), "points_per_replicate": next(g["points"] for g in group["graphs"] if g["id"] == graph),
            **stats[name, graph],
        }
    result.update({
        "purpose": manifest["purpose"], "complete_graph_coverage": manifest["coverage_verified"],
        "reportable_precision_established": False,
        "status": "Exploratory pilot; increase complete-net sizes with fresh independent production seeds and check convergence before reporting C8." if manifest["purpose"] == "pilot" else "Complete production estimator; review numerical controls and independent convergence campaigns before assigning a reporting allowance.",
        "evaluations": manifest["evaluations"], "replicates_per_campaign": manifest["replicates"],
        "manifest_sha256": digest(Path(directory) / "manifest.json"), "native_sha256": native_hashes,
        "two_loop_sha256": manifest["inputs"]["two_loop.json"],
        "assembly_sources": {name: digest(ROOT / "tools" / name) for name in ("assemble.py", "rg.py", "io_utils.py")},
    })
    return result, pilot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--bootstrap", type=int, default=512)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--graph-statistics", type=Path)
    args = parser.parse_args()
    result, graph_statistics = analyze(args.directory, args.bootstrap)
    output = args.output or args.directory / "C8_result.json"
    save(output, result)
    save(args.graph_statistics or args.directory / "graph_statistics.json", graph_statistics)
    print(json.dumps({k: result[k] for k in ("C8_estimate", "sampling_standard_error", "purpose", "complete_graph_coverage", "status")}, indent=2))


if __name__ == "__main__":
    main()
