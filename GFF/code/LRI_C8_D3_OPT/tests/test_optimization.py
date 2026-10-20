#!/usr/bin/env python3
"""Same-input regression on stratified real graphs, schedules, and precision levels."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
from benchmark_c8 import make_net
from io_utils import ROOT, digest

FIELDS = ("uid", "rep", "graph", "begin", "end", "total", "quad", "mp", "max_abs", "values")

def compare(a, b):
    if len(a["rows"]) != len(b["rows"]):
        raise AssertionError("Dropped native rows")
    for old, new in zip(a["rows"], b["rows"]):
        for field in FIELDS:
            if old[field] != new[field]:
                raise AssertionError(f"Changed {field} for graph {old['graph']}, rep {old['rep']}")


def main():
    inventory = json.loads((ROOT/"inputs/inventory.json").read_text())
    selection = json.loads((ROOT/"tests/optimization_graphs.json").read_text())
    report = {"status": "running", "checks": [], "points": 0, "quad": 0, "mp": 0,
              "binary_sha256": digest(ROOT/"bin/c8d3_optimized"),
              "baseline_sha256": digest(ROOT/"bin/c8d3_baseline")}
    with tempfile.TemporaryDirectory(prefix="c8_optimizer_tests_") as temp:
        d = Path(temp)
        for loop in range(3, 9):
            for sector in ("free", "power"):
                candidates = sorted(inventory[sector][str(loop)], key=lambda r: (r["cost"], r["id"]))
                # Freeze the same stratified selection on small and fully extracted installations.
                selected = {r["id"]: r["sha256"] for r in selection[sector][str(loop)]}
                candidates = [r for r in candidates if r["id"] in selected]
                for r in candidates:
                    if digest(ROOT/"inputs"/r["file"]) != selected[r["id"]]:
                        raise ValueError("Regression graph fixture changed")
                if not candidates:
                    raise RuntimeError("Extract the selected graph fixtures before running this test")
                ids = sorted(r["id"] for r in candidates)
                n = 64 if loop < 7 else 32
                tasks = [[i, rep, gid, 0, n, n] for i, (rep, gid) in enumerate((rep, gid) for rep in range(4) for gid in ids)]
                (d/"tasks").write_text(f"C8D3TASKS1 {loop} {len(tasks)}\n"+"".join(" ".join(map(str,t))+"\n" for t in tasks))
                make_net(d/"net", 4*loop-1, 60, 4, 61724190+loop)
                args = [str(ROOT/"inputs"/sector), str(ROOT/"inputs/gamma_d3_8.txt"), str(d/"net"), str(d/"tasks"), str(d/"out"),
                        "596781190237", "0", ".7", "1", "compensated", "-"]
                subprocess.run([str(ROOT/"bin/c8d3_baseline"), *args], check=True, capture_output=True)
                baseline = json.loads((d/"out").read_text())
                for threads, batch, loaders in ((1, 1, 1), (4, 3, 2)):
                    args[8] = str(threads)
                    subprocess.run([str(ROOT/"bin/c8d3_optimized"), *args], check=True, capture_output=True,
                                   env={**os.environ, "C8_GRAPH_BATCH": str(batch), "C8_LOAD_THREADS": str(loaders)})
                    new = json.loads((d/"out").read_text())
                    compare(baseline, new)
                    if new["peak_graphs_resident"] > batch:
                        raise AssertionError("Resident graph bound exceeded")
                report["checks"].append({"L": loop, "sector": sector, "graphs": ids, "replicates": 4, "points_per_replicate": n,
                    "all_values_and_promotion_counts_identical": True, "variants": ["1 thread / batch 1", "4 threads / batch 3 / 2 loaders"]})
                report["points"] += n*len(tasks)
                report["quad"] += sum(r["quad"] for r in baseline["rows"])
                report["mp"] += sum(r["mp"] for r in baseline["rows"])
                print(f"Passed {sector} L{loop}: {len(ids)} graphs", flush=True)
    report["status"] = "passed"
    dest = ROOT/"verification/performance/optimization_regression.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: report[k] for k in ("status", "points", "quad", "mp")}))

if __name__ == "__main__":
    main()
