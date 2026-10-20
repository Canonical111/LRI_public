#!/usr/bin/env python3
"""Memory-bounded assembly for standard monotone C8 plans.

The fixed point, covariance, bootstrap, references, and 50-digit Decimal
accumulation are unchanged. Graph Decimal accumulators are retired as soon
as their graph totals can be committed in the original order. Out-of-order chunk plans are explicitly rejected;
use assemble.py for those nonstandard plans. No missing work is tolerated.
"""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np
import assemble as reference
from campaign import LOOPS, SCHEMA, SECTORS, validate_native
from io_utils import ROOT, checked, digest, load, object_hash

LAST_DIAGNOSTICS = {}

def read_replicates_streaming(directory):
    """Preserve exact Decimal addition order for standard monotone campaign plans."""
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
    count = manifest["replicates"]
    targets = {name: {row["id"]: row["points"] for row in group["graphs"]} for name, group in groups.items()}
    positions = {name: 0 for name in groups}
    combined = {name: [[Decimal(0)] * (2*(9-group["L"])) for _ in range(count)] for name, group in groups.items()}
    active, partial, ready, graph_arrays = {}, {}, {}, {}
    stats = defaultdict(lambda: {"cpu_seconds": 0.0, "points": 0, "quad": 0, "mp": 0})
    native_hashes = {}
    total_evaluations = 0
    peak_active = peak_ready = 0
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
            name = job["group"]
            group = groups[name]
            if job["L"] != group["L"]:
                raise ValueError("Job loop differs from its stratum")
            validate_native(data, job, group)
            if data.get("mp_backend") != manifest["executable"]["description"]["mp_backend"]:
                raise ValueError("Changed numerical backend")
            for row in data["rows"]:
                gid, rep = row["graph"], row["rep"]
                key, gkey = (name, rep, gid), (name, gid)
                if gid not in targets[name] or not 0 <= rep < count or row["total"] != targets[name][gid]:
                    raise ValueError("Unexpected graph, replicate, or net size")
                if gkey in graph_arrays or (gkey in partial and partial[gkey][rep] is not None):
                    raise ValueError("Duplicate completed replicate")
                vector, end = active.get(key, ([Decimal(0)]*len(row["values"]), 0))
                if row["begin"] != end or not end < row["end"] <= row["total"]:
                    raise ValueError("Gap, overlap, or non-monotone chunks; use assemble.py for a nonstandard out-of-order plan")
                for k, value in enumerate(row["values"]):
                    vector[k] += Decimal(value)
                active[key] = vector, row["end"]
                peak_active = max(peak_active, len(active))
                counter = stats[gkey]
                for field in ("quad", "mp"):
                    counter[field] += row[field]
                counter["cpu_seconds"] += row["seconds"]
                counter["points"] += row["end"]-row["begin"]
                total_evaluations += row["end"]-row["begin"]
                if row["end"] == row["total"]:
                    del active[key]
                    per_rep = partial.setdefault(gkey, [None]*count)
                    per_rep[rep] = vector
                    if all(v is not None for v in per_rep):
                        graph_arrays[gkey] = np.asarray([[float(x) for x in v] for v in per_rep], dtype=float)
                        ready[gkey] = per_rep
                        del partial[gkey]
                        peak_ready = max(peak_ready, len(ready))
                        # Flush in the original graph order, NOT completion order.
                        graph_rows = group["graphs"]
                        while positions[name] < len(graph_rows):
                            next_key = name, graph_rows[positions[name]]["id"]
                            if next_key not in ready:
                                break
                            values = ready.pop(next_key)
                            for r, vec in enumerate(values):
                                for k, value in enumerate(vec):
                                    combined[name][r][k] += value
                            positions[name] += 1
        if active or partial or ready or total_evaluations != manifest["evaluations"]:
            raise ValueError("Unexpected, missing, duplicated, or incomplete scientific work")
        if any(positions[name] != len(group["graphs"]) for name, group in groups.items()):
            raise ValueError("Missing active graphs")
    arrays = {s: {t: {} for t in ("a", "b")} for s in SECTORS}
    for name, group in groups.items():
        arrays[group["sector"]][group["campaign"]][group["L"]] = np.asarray(combined[name], dtype=float)
    LAST_DIAGNOSTICS.clear()
    LAST_DIAGNOSTICS.update(peak_open_decimal_replicates=peak_active, peak_ready_decimal_graphs=peak_ready,
                           jobs=len(manifest["jobs"]), completed_graph_arrays=len(graph_arrays),
                           chunk_interval_lists_retained=False, decimal_precision=50)
    return arrays, graph_arrays, stats, manifest, native_hashes


def main():
    # Reuse every scientific operation from the original implementation.
    reference.read_replicates = read_replicates_streaming
    original_analyze = reference.analyze
    def analyze(*args, **kwargs):
        result, statistics = original_analyze(*args, **kwargs)
        result["assembly_sources"]["assemble_streaming.py"] = digest(Path(__file__))
        result["streaming_assembly"] = dict(LAST_DIAGNOSTICS)
        return result, statistics
    reference.analyze = analyze
    reference.main()

if __name__ == "__main__":
    main()
