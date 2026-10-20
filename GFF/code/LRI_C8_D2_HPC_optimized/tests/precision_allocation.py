#!/usr/bin/env python3
"""Independent budget/count checks and refusal tests for precision protocol 03."""
from __future__ import annotations

import copy
from decimal import Decimal, localcontext
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from common import canon, digest, dump, load
from precision_allocation import generate
from refinement_allocation import problem


def main():
    allocation_path = ROOT / "precision_work/precision_allocation_03.json"
    summary_path = ROOT / "precision_work/precision_allocation_03_summary.json"
    allocation = load(allocation_path)
    summary = load(summary_path)
    sources = allocation["precision_source_pilots"]
    earlier = load(ROOT / sources["earlier"]["model"])
    latest = load(ROOT / sources["latest"]["model"])
    assert digest(allocation_path) == summary["allocation_sha256"]
    assert digest(ROOT / "tools/precision_allocation.py") == summary["generator_sha256"]
    for source in sources.values():
        assert digest(ROOT / source["model"]) == source["model_sha256"]
        assert digest(ROOT / source["run"] / "manifest.json") == source["source_manifest_sha256"]
    inventory = load(ROOT / "inputs/inventory.json")
    expected = {(sector, int(loop), str(row["id"]))
                for sector, loops in inventory.items() for loop, rows in loops.items() for row in rows}
    actual = {(sector, int(loop), gid) for sector, loops in allocation["counts"].items()
              for loop, rows in loops.items() for gid in rows}
    assert expected == actual and len(actual) == 24173
    latest_run = ROOT / sources["latest"]["run"]
    actual_source_counts = {}
    for campaign in ("a", "b"):
        for sector in ("free", "power"):
            for loop in range(3, 9):
                cfg = load(latest_run / "groups" / f"{campaign}_{sector}_L{loop}" / "config.json")
                for gid, n in cfg["counts"].items():
                    key = (sector, loop, gid)
                    actual_source_counts[key] = max(n, actual_source_counts.get(key, 0))
    assert allocation["replicates"] == 16 and allocation["campaign_count"] == 2
    total_points = 0
    min_ratios = {}
    with localcontext() as context:
        context.prec = 60
        cost = variance = Decimal(0)
        for sector, loop, gid in sorted(actual):
            n = allocation["counts"][sector][str(loop)][gid]
            assert isinstance(n, int) and n >= 4 and n & (n - 1) == 0
            floor = max(actual_source_counts[sector, loop, gid], 128 if (sector, loop) == ("free", 8) else 64)
            assert n >= floor
            assert allocation["precision_floor_policy"]["floors"][sector][str(loop)][gid] == floor
            key = f"{sector}:{loop}:{gid}"
            metric = allocation["metrics"][key]
            old, new = earlier["metrics"][key], latest["metrics"][key]
            assert metric["variance_proxy"] == max(old["variance_proxy"], new["variance_proxy"])
            assert metric["seconds_per_point"] == new["seconds_per_point"]
            cost += Decimal(str(metric["seconds_per_point"])) * n * 32 / 3600
            variance += Decimal(str(metric["variance_proxy"])) / (n * 32)
            total_points += n * 32
            group = f"{sector}:L{loop}"
            ratio = n / actual_source_counts[sector, loop, gid]
            min_ratios[group] = min(min_ratios.get(group, ratio), ratio)
        model_se = variance.sqrt()
        assert Decimal(35) >= cost > Decimal("34.9999")
        assert abs(cost - Decimal(str(allocation["estimated_kernel_core_hours"]))) < Decimal("1e-11")
        assert abs(model_se - Decimal(str(allocation["model_only_standard_error_forecast"]))) < Decimal("1e-10")
    assert total_points == summary["total_points"] == 274139136
    assert set(allocation["pilot_seeds"]) == {sources[name]["pilot_seed"] for name in ("earlier", "latest")}
    assert len(allocation["pilot_seeds"]) == 2
    assert all(summary["checks"].values())

    # The hypothetical model allocation is deliberately changed. Its measured
    # pilot point counts must still determine exactly the same retention floor.
    modified = copy.deepcopy(latest)
    for loops in modified["counts"].values():
        for rows in loops.values():
            for gid in rows:
                rows[gid] = 4
    ordinary_floor = problem(latest, 16, 64, 1)[3]
    hypothetical_floor = problem(modified, 16, 64, 1)[3]
    assert ordinary_floor == hypothetical_floor

    refusals = {}
    def refuse(name, old=None, new=None, **options):
        try:
            generate(old if old is not None else earlier, new if new is not None else latest,
                     sources["earlier"], sources["latest"], **options)
        except ValueError as error:
            refusals[name] = str(error)
        else:
            raise AssertionError(f"Malformed request was not refused: {name}")
    refuse("nonpositive_budget", target_core_hours=0)
    refuse("insufficient_retention_budget", target_core_hours=1)
    refuse("odd_replicate_count", replicates=15)
    refuse("non_power_of_two_floor", free_l8_floor=96)
    refuse("free_floor_below_general_minimum", free_l8_floor=32)
    changed_seed = dict(latest, pilot_seeds=earlier["pilot_seeds"])
    refuse("pilot_seed_reuse", new=changed_seed)
    missing = copy.deepcopy(earlier)
    del missing["metrics"][next(iter(missing["metrics"]))]
    refuse("missing_graph_metric", old=missing)

    certificate = {
        "schema": "c8-d2-precision-allocation-checks-1", "status": "passed",
        "allocation_sha256": digest(allocation_path), "test_sha256": digest(Path(__file__)),
        "graphs_verified_against_independent_inventory": len(actual),
        "actual_latest_group_configs_checked": 24,
        "total_points": total_points, "decimal_kernel_core_hours": str(cost),
        "decimal_model_only_standard_error_forecast": str(model_se),
        "minimum_point_ratio_to_latest_by_group": min_ratios,
        "hypothetical_allocation_counts_do_not_change_retention_floors": True,
        "source_model_and_manifest_hashes_verified": True,
        "exact_two_pilot_seed_exclusions": allocation["pilot_seeds"],
        "refusal_cases": refusals,
        "scope": "Allocation invariants and input refusals only; no new numerical coefficient or measured uncertainty"}
    path = ROOT / "verification/precision_allocation_checks.json"
    if path.exists():
        if canon(load(path)) != canon(certificate):
            raise FileExistsError("Refusing to overwrite a different allocation-check certificate")
    else:
        dump(path, certificate)
    print(json.dumps(certificate, indent=2))


if __name__ == "__main__":
    main()
