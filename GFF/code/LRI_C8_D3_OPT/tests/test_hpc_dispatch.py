#!/usr/bin/env python3
"""Test fusion, complete coverage, exact row preservation, resume, and tamper rejection."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
from campaign import plan, verify_plan, run_job
from hpc_dispatch import make_index, run_lane, StageCache
from io_utils import ROOT, load, digest
from test_optimization import compare


def main():
    with tempfile.TemporaryDirectory(prefix="c8_dispatch_tests_") as tmp:
        d = Path(tmp);run=d/"run"
        plan(SimpleNamespace(directory=run, points=64, chunk_points=8, replicates=4, threads=2,
             graph_block=2, seed=1927138071, purpose="pilot", loops=[3], allocation=None,
             executable=ROOT/"bin/c8d3_optimized"))
        manifest = verify_plan(run)
        expected = {}
        t0 = time.perf_counter()
        for e in manifest["jobs"]:
            run_job(run, e["index"], 2, manifest)
            base=run/"jobs"/f"{e['index']:06d}"
            expected[e["index"]] = load(base.with_suffix(".native.json"))
            base.with_suffix(".native.json").unlink()
            base.with_suffix(".done.json").unlink()
        old_seconds = time.perf_counter()-t0
        index = make_index(run, d/"dispatch", lanes=3, bundle_jobs=8)
        if index["bundles"] >= index["jobs"]:
            raise AssertionError("Fixture did not fuse any jobs")
        t0 = time.perf_counter()
        reports = [run_lane(d/"dispatch", i, 2, d/"scratch") for i in range(3)]
        new_seconds = time.perf_counter()-t0
        if sum(r["jobs_completed"] for r in reports) != len(manifest["jobs"]):
            raise AssertionError("Coverage mismatch")
        for e in manifest["jobs"]:
            result = load(run/"jobs"/f"{e['index']:06d}.native.json")
            compare(expected[e["index"]], result)
        resume = [run_lane(d/"dispatch", i, 2, d/"scratch") for i in range(3)]
        if sum(r["native_invocations"] for r in resume) != 0:
            raise AssertionError("Resume repeated completed integrations")
        # Corruption must fail before reusing a checkpoint.
        output=run/"jobs/000000.native.json";original=output.read_bytes();output.write_bytes(original+b" ")
        rejected=False
        try:
            for i in range(3):run_lane(d/"dispatch", i, 2, d/"scratch")
        except ValueError:
            rejected=True
        if not rejected:raise AssertionError("Checkpoint corruption was accepted")
        output.write_bytes(original)
        # Staging validates the byte stream, not just its filename.
        source=d/"changed";source.write_text("not the expected content")
        rejected=False
        try:StageCache(d/"cache").stage(source,"input", "0"*64)
        except ValueError:rejected=True
        if not rejected:raise AssertionError("Stage-cache corruption was accepted")
        # Tampering with the assignment is rejected by its hash.
        lane_file=d/"dispatch/lane_000000.json";lane_file.write_bytes(lane_file.read_bytes()+b" ")
        rejected=False
        try:run_lane(d/"dispatch",0,2,d/"scratch")
        except ValueError:rejected=True
        if not rejected:raise AssertionError("Dispatch corruption was accepted")
        report = {"status":"passed", "jobs":len(expected), "fused_invocations":index["bundles"],
                  "lanes":3, "all_scientific_rows_exact":True, "resume_invocations":0,
                  "checkpoint_stage_and_dispatch_tampering_rejected":True,
                  "unbundled_wall_seconds":old_seconds,"bundled_wall_seconds":new_seconds,
                  "timing_scope":"L3 process/startup fixture; lanes executed sequentially, not a cluster scaling benchmark"}
        out=ROOT/"verification/performance/dispatch_test.json";out.write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report,indent=2))

if __name__ == "__main__":main()
