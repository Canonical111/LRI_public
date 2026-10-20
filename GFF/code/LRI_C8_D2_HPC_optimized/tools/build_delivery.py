#!/usr/bin/env python3
"""Finish the C8 delivery ZIP from its twelve already-compressed input packs.

Run after merge, assembly, result inspection, report generation and final PDF
compilation:

    python3 tools/build_delivery.py --dry-run
    python3 tools/build_delivery.py

Use --run for the run displayed in RESULTS.md and the PDF. Additional complete
comparison runs can be retained with repeatable --include-run arguments.

The original ZIP must contain exactly the twelve input-pack members. This
script verifies their SHA-256 hashes against the input manifest pinned by the
completed run. It appends an explicit selection of deliverables to a temporary
copy, verifies every added member, and replaces the original only on success.
It never collects a whole directory tree or includes runtime scratch files.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "LRI_C8_D2_HPC"
CHUNK = 1 << 20
PACKS = tuple(f"inputs/packs/{sector}_L{loop}.pack"
              for sector in ("free", "power") for loop in range(3, 9))
GROUPS = {f"{campaign}_{sector}_L{loop}"
          for campaign in ("a", "b") for sector in ("free", "power")
          for loop in range(3, 9)}

REQUIRED = (
    "README.md", "RESULTS.md", "Makefile", "requirements.txt",
    "src/build_record.py", "src/c8d2_integrate.cpp", "src/kernel.hpp",
    "tools/analytic_inputs.py", "tools/assemble.py", "tools/build_delivery.py",
    "tools/build_record.py", "tools/common.py", "tools/inspect_result.py", "tools/make_cost_model.py",
    "tools/pilot_allocation.py", "tools/prepare_inputs.py", "tools/production.py",
    "tools/refinement_allocation.py", "tools/report_result.py", "tools/run_local.py", "tools/slurm_submit.py",
    "tools/stage_runtime.py", "tools/unpack_graphs.py",
    "slurm/env.sh.example", "slurm/run_array.sh", "slurm/merge.sh",
    "slurm/submit.sh", "slurm/resubmit.sh",
    "tests/allocation.py", "tests/assembly_formula.py", "tests/kernel_checks.py",
    "tests/kernel_points.cpp", "tests/refinement_allocation.py", "tests/workflow.py", "tests/fixtures/graphs.txt",
    "tests/fixtures/free_G319.txt", "tests/fixtures/free_G348.txt",
    "tests/fixtures/free_G360.txt", "tests/fixtures/free_G387.txt",
    "tests/fixtures/power_G3.txt", "tests/fixtures/power_G7.txt",
    "tests/fixtures/power_G58.txt", "tests/fixtures/power_G84.txt",
    "docs/THEORY.md", "docs/C8_D2_calculation.tex", "docs/C8_results_fragment.tex",
    "output/pdf/C8_D2_calculation.pdf",
    "generator/README.md", "generator/enumerate_classes.cpp",
    "generator/build_forests.cpp", "generator/check_edge_forests.cpp",
    "generator/check_kirchhoff.py", "generator/verify_classes.py",
    "generator/coverage.py", "generator/rebuild.py",
    "generator/reports/generation_summary.json",
    "generator/reports/class_verification.json",
    "generator/reports/forest_regression.json", "generator/reports/coverage.json",
    "generator/reports/edge_forests_L8.json", "generator/reports/kirchhoff_L8.json",
    "inputs/manifest.json", "inputs/inventory.json", "inputs/coverage.json",
    "inputs/two_loop.json", "inputs/gamma_d2_8.txt",
    "verification/analytic_inputs.json", "verification/assembly_covariance.json",
    "verification/assembly_formula.json", "verification/dependency_origins.json",
    "verification/kernel_checks.json", "verification/native_cost_pilot.json",
    "verification/refinement_allocation.json",
    "verification/workflow.json", "verification/native_cost_pilot/manifest.json",
)


def fail(message):
    raise ValueError(message)


def snapshot(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def sha_stream(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(CHUNK), b""):
        h.update(block)
    return h.hexdigest()


def sha_file(path):
    with path.open("rb") as stream:
        return sha_stream(stream)


def object_hash(value):
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode()).hexdigest()


def load(path):
    with path.open() as stream:
        return json.load(stream)


def checked(path, expected):
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected)) or sha_file(path) != expected:
        fail(f"SHA-256 mismatch: {path}")


def member_name(relative):
    return f"{PREFIX}/{relative}"


def safe_file(relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or not p.parts or any(x in (".", "..") for x in p.parts):
        fail(f"Unsafe relative path: {relative}")
    path = ROOT
    for part in p.parts:
        path = path / part
        if path.is_symlink():
            fail(f"Symbolic links are not deliverable members: {path}")
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        fail(f"Required regular file is missing: {path}")
    return path


def validate_run(run_relative, require_root_report=True):
    """Check saved provenance and complete coverage without recomputing C8."""
    rd = ROOT / run_relative
    m = load(safe_file(f"{run_relative}/manifest.json"))
    r = load(safe_file(f"{run_relative}/C8_result.json"))
    report = load(safe_file(f"{run_relative}/run_report.json"))
    diagnostics = load(safe_file(f"{run_relative}/result_diagnostics.json"))
    mh = sha_file(rd / "manifest.json")
    rh = sha_file(rd / "C8_result.json")
    if (m.get("schema") != "c8-d2-production-2" or m.get("dimension") != 2
            or m.get("order") != 8 or m.get("test_only") is not False
            or m.get("primitive_mode") != "recompute"):
        fail("The delivery requires a complete C8 campaign with recomputed primitives")
    if (r.get("schema") != "c8-d2-hpc-result-2" or r.get("test_only") is not False
            or r.get("source_manifest_sha256") != mh
            or not isinstance(r.get("C8_full"), (int, float))
            or not math.isfinite(r["C8_full"])):
        fail("The saved C8 result is absent, incomplete, or belongs to another plan")
    if (report.get("schema") != "c8-d2-run-report-1"
            or report.get("result_sha256") != rh or report.get("C8") != r["C8_full"]):
        fail("Regenerate the final run report from the saved C8 result")
    if (diagnostics.get("schema") != "c8-d2-result-diagnostics-1"
            or diagnostics.get("source_manifest_sha256") != mh
            or diagnostics.get("source_result_sha256") != rh
            or diagnostics.get("source_merged_sha256") != r.get("merged_sha256")):
        fail("Regenerate result_diagnostics.json from the saved C8 result and merged groups")
    if require_root_report and rh not in safe_file("RESULTS.md").read_text():
        fail("RESULTS.md does not identify the current C8_result.json")
    inputs_path = safe_file("inputs/manifest.json")
    checked(inputs_path, m["inputs_manifest_sha256"])
    inputs = load(inputs_path)
    if inputs.get("schema") != "c8-d2-hpc-inputs-1":
        fail("Wrong input manifest schema")
    core_tools = {"production.py", "assemble.py", "common.py", "prepare_inputs.py"}
    allowed_tools = core_tools | {"cluster_graph_tasks.py"}
    if not core_tools.issubset(m["tool_sha256"]):
        fail("The run is missing a pinned numerical workflow tool")
    for name, digest in m["tool_sha256"].items():
        if name not in allowed_tools:
            fail(f"Unexpected pinned tool: {name}")
        checked(safe_file(f"tools/{name}"), digest)
    for name, digest in inputs["sha256"].items():
        if not name.startswith("packs/"):
            checked(safe_file(f"inputs/{name}"), digest)
    for field, filename in (("cost_model_sha256", "cost_model.json"),
                            ("allocation_file_sha256", "allocation.json")):
        if m.get(field):
            checked(safe_file(f"{run_relative}/{filename}"), m[field])
    groups = m.get("groups", [])
    if len(groups) != len(GROUPS) or {g["name"] for g in groups} != GROUPS:
        fail("The run does not contain exactly the required 24 groups")
    if set(r.get("merged_sha256", {})) != GROUPS:
        fail("The assembled result does not cover all 24 merged groups")
    inventory = load(ROOT / "inputs/inventory.json")
    files = {f"{run_relative}/{name}" for name in
             ("manifest.json", "C8_result.json", "run_report.json", "result_diagnostics.json")}
    execution_relative = f"{run_relative}/local_execution.json"
    if (ROOT / execution_relative).exists():
        execution = load(safe_file(execution_relative))
        if (execution.get("schema") != "c8-d2-local-execution-1"
                or execution.get("run") != run_relative
                or execution.get("status") != "completed"):
            fail("Complete and update the local execution record before delivery")
        files.add(execution_relative)
    files.update(f"tools/{name}" for name in m["tool_sha256"])
    scheduling = m.get("scheduling")
    scheduling_groups = None
    if scheduling is not None:
        if (scheduling.get("schema") != "c8-d2-graph-scheduling-1"
                or scheduling.get("same_statistical_samples_as_source") is not True
                or scheduling.get("provenance_file") != "scheduling_provenance.json"
                or m.get("shard_policy") != "graph_bundle_lpt"
                or "cluster_graph_tasks.py" not in m["tool_sha256"]):
            fail("Invalid graph-scheduling provenance in the run manifest")
        source_path = safe_file(f"{run_relative}/source_manifest.json")
        provenance_path = safe_file(f"{run_relative}/scheduling_provenance.json")
        checked(source_path, scheduling["source_manifest_sha256"])
        checked(provenance_path, scheduling["provenance_sha256"])
        source = load(source_path)
        provenance = load(provenance_path)
        source_groups = {g["name"]: g["sha256"] for g in source.get("groups", [])}
        if (source.get("schema") != "c8-d2-production-2"
                or source.get("scheduling") is not None
                or set(source_groups) != GROUPS
                or provenance.get("schema") != scheduling["schema"]
                or provenance.get("method") != scheduling.get("method")
                or provenance.get("source_manifest_sha256") != scheduling["source_manifest_sha256"]
                or provenance.get("tool_sha256") != m["tool_sha256"]["cluster_graph_tasks.py"]
                or provenance.get("same_statistical_samples_as_source") is not True
                or provenance.get("execute_both_copies") is not False
                or provenance.get("checkpoint_tasks") != m["checkpoint_tasks"]
                or set(provenance.get("groups", {})) != GROUPS):
            fail("The graph-scheduling certificate does not identify this run")
        for field in ("dimension", "order", "seed", "seed_scheme", "inputs_manifest_sha256",
                      "executable_sha256", "backend", "campaign_weights", "test_only",
                      "primitive_mode", "allocation_file_sha256", "cost_model_sha256"):
            if source.get(field) != m.get(field):
                fail(f"Scheduling changed a scientific manifest field: {field}")
        if source.get("tool_sha256") != {name: digest for name, digest in m["tool_sha256"].items()
                                         if name != "cluster_graph_tasks.py"}:
            fail("The scheduling source has different numerical tool pins")
        if provenance.get("source_files_sha256", {}).get("manifest.json") != scheduling["source_manifest_sha256"]:
            fail("The scheduling source-file inventory has a different manifest")
        for name, group in provenance["groups"].items():
            if (group.get("identical_after_scheduling") is not True
                    or group.get("source_config_sha256") != source_groups[name]):
                fail(f"Invalid scheduling identity certificate: {name}")
        scheduling_groups = provenance["groups"]
        files.update(f"{run_relative}/{name}" for name in
                     ("source_manifest.json", "scheduling_provenance.json"))
        files.update(("tests/cluster_graph_tasks.py", "verification/cluster_graph_tasks.json"))
    elif "cluster_graph_tasks.py" in m["tool_sha256"]:
        fail("The run pins graph scheduling without its provenance certificate")
    checkpoint_count = 0
    for group in groups:
        name = group["name"]
        base = f"{run_relative}/groups/{name}"
        config_path = safe_file(f"{base}/config.json")
        checked(config_path, group["sha256"])
        cfg = load(config_path)
        if (cfg.get("schema") != "c8-d2-group-2" or cfg.get("name") != name
                or name != f'{cfg["campaign"]}_{cfg["sector"]}_L{cfg["L"]}'):
            fail(f"Invalid group identity: {name}")
        ids = {str(row["id"]) for row in inventory[cfg["sector"]][str(cfg["L"])]}
        if set(cfg["counts"]) != ids or any(n <= 0 for n in cfg["counts"].values()):
            fail(f"Incomplete graph coverage: {name}")
        checked(safe_file(f"{base}/tasks.sqlite"), cfg["tasks_sha256"])
        if scheduling_groups is not None and scheduling_groups[name]["tasks_sha256"] != cfg["tasks_sha256"]:
            fail(f"The scheduling certificate identifies a different task database: {name}")
        checked(safe_file(f"{base}/sobol.bin"), cfg["net"]["sha256"])
        merged_path = safe_file(f"{base}/merged.json")
        checked(merged_path, r["merged_sha256"][name])
        merged = load(merged_path)
        if (merged.get("schema") != "c8-d2-merged-1" or merged.get("complete") is not True
                or merged.get("manifest_sha256") != mh
                or merged.get("config_hash") != object_hash(cfg)
                or merged.get("replicates") != cfg["replicates"]
                or len(merged.get("batches", [])) != cfg["replicates"]):
            fail(f"Invalid or incomplete merge: {name}")
        if merged.get("payload_sha256") != object_hash(
                {k: v for k, v in merged.items() if k != "payload_sha256"}):
            fail(f"Merged payload checksum mismatch: {name}")
        checked(safe_file(f"{base}/graph_replicates.csv"), merged["graph_replicates_sha256"])
        files.update(f"{base}/{f}" for f in
                     ("config.json", "tasks.sqlite", "sobol.bin", "merged.json", "graph_replicates.csv"))
        expected = set()
        task_path = ROOT / base / "tasks.sqlite"
        with sqlite3.connect(task_path.as_uri() + "?mode=ro", uri=True) as db:
            rows = list(db.execute("SELECT shard, COUNT(*) FROM tasks GROUP BY shard"))
        if sum(count for _, count in rows) != cfg["tasks"]:
            fail(f"Task-count mismatch: {name}")
        for shard, count in rows:
            blocks = (count + m["checkpoint_tasks"] - 1) // m["checkpoint_tasks"]
            expected.update(f"s{shard:06d}_p{part:06d}.json" for part in range(blocks))
        folder = ROOT / base / "checkpoints"
        actual = {p.name for p in folder.iterdir()} if folder.is_dir() else set()
        if actual != expected:
            fail(f"Missing or unexpected checkpoint files: {name}")
        files.update(f"{base}/checkpoints/{f}" for f in expected)
        checkpoint_count += len(expected)
    if require_root_report:
        pdf = safe_file("output/pdf/C8_D2_calculation.pdf")
        fragment = safe_file("docs/C8_results_fragment.tex")
        tex = safe_file("docs/C8_D2_calculation.tex")
        if fragment.stat().st_mtime_ns < (rd / "C8_result.json").stat().st_mtime_ns:
            fail("The LaTeX results fragment predates the final C8 result")
        if pdf.stat().st_mtime_ns < max(fragment.stat().st_mtime_ns, tex.stat().st_mtime_ns):
            fail("Compile the final PDF after generating the results fragment")
        with pdf.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                fail("The final PDF is not a PDF file")
    return m, inputs, files, mh, rh, checkpoint_count


def select_files(run_relative, include_binaries, included_runs=()):
    selected_runs = (run_relative, *included_runs)
    if len(set(selected_runs)) != len(selected_runs):
        fail("A run may be selected only once across --run and --include-run")
    files = set()
    run_manifests = {}
    run_metadata = []
    for relative in selected_runs:
        m, inputs, run_files, mh, rh, checkpoints = validate_run(
            relative, require_root_report=relative == run_relative)
        run_manifests[relative] = m
        files.update(run_files)
        run_metadata.append({
            "run": relative, "role": "main" if relative == run_relative else "comparison",
            "run_manifest_sha256": mh, "result_sha256": rh,
            "result_diagnostics_sha256": sha_file(ROOT / relative / "result_diagnostics.json"),
            "input_manifest_sha256": m["inputs_manifest_sha256"],
            "purpose": m["purpose"], "backend": m["backend"], "checkpoint_files": checkpoints,
        })
    main_manifest = run_manifests[run_relative]
    manifests_by_hash = {info["run_manifest_sha256"]: run_manifests[info["run"]]
                         for info in run_metadata}
    files.update(REQUIRED)
    files.update(f"inputs/classes/classes{loop}.txt" for loop in range(1, 9))
    for sector in ("free", "power"):
        files.add(f"generator/reports/census_L8/{sector}/inventory.json")
        for loop in range(3, 9):
            files.add(f"inputs/raw/{sector}/L{loop}/inventory.json")
            files.update(f"verification/native_cost_pilot/{sector}_L{loop}.{suffix}"
                         for suffix in ("json", "net", "tasks"))
        for loop in range(3, 8):
            p = f"generator/reports/forest_regression/{sector}/L{loop}/inventory.json"
            if (ROOT / p).exists():
                files.add(p)
    summary = load(ROOT / "generator/reports/generation_summary.json")
    for name, digest in summary["certificate_sha256"].items():
        path = f"generator/reports/{name}"
        if path not in REQUIRED:
            fail(f"Unexpected generator certificate: {name}")
        checked(safe_file(path), digest)
    optional = (
        "generator/benchmark_compression.py", "generator/reports/compression_sample.json",
        "verification/allocation.json", "verification/pilot_allocation.json",
    )
    files.update(p for p in optional if (ROOT / p).exists())
    # A refinement's frozen planning files may come from a retained pilot.
    # Accept only recognized products whose source is one of the selected runs.
    for directory in ("results", *selected_runs):
        for name in ("cost_model.json", "allocation.json", "pilot_allocation.json",
                     "production_allocation.json", "refinement_allocation.json"):
            path = f"{directory}/{name}"
            if (ROOT / path).exists():
                value = load(safe_file(path))
                source_manifest = manifests_by_hash.get(value.get("source_manifest_sha256"))
                if (value.get("schema") not in ("c8-d2-cost-model-1", "c8-d2-allocation-1")
                        or value.get("dimension") != 2 or value.get("order") != 8
                        or source_manifest is None
                        or value.get("backend") != source_manifest["backend"]
                        or (directory in run_manifests
                            and value.get("backend") != run_manifests[directory]["backend"])):
                    fail(f"Planning product does not identify a compatible included source run: {path}")
                if (value["schema"] == "c8-d2-allocation-1"
                        and value.get("inputs_manifest_sha256") != source_manifest["inputs_manifest_sha256"]):
                    fail(f"Allocation input manifest mismatch: {path}")
                files.add(path)
    if include_binaries:
        for name in ("c8d2_decimal", "c8d2_gmp"):
            path = f"bin/{name}"
            recpath = path + ".build.json"
            rec = load(safe_file(recpath))
            checked(safe_file(path), rec["executable_sha256"])
            for source, digest in rec["source_sha256"].items():
                if source not in ("c8d2_integrate.cpp", "kernel.hpp"):
                    fail(f"Unexpected build-record source: {source}")
                checked(safe_file(f"src/{source}"), digest)
            files.update((path, recpath))
        for m in run_manifests.values():
            checked(ROOT / "bin" / f'c8d2_{m["backend"]}', m["executable_sha256"])
    for relative in files:
        safe_file(relative)
    return sorted(files), inputs, {
        "run": run_relative,
        "run_manifest_sha256": run_metadata[0]["run_manifest_sha256"],
        "result_sha256": run_metadata[0]["result_sha256"],
        "result_diagnostics_sha256": run_metadata[0]["result_diagnostics_sha256"],
        "input_manifest_sha256": main_manifest["inputs_manifest_sha256"],
        "purpose": main_manifest["purpose"],
        "checkpoint_files": sum(info["checkpoint_files"] for info in run_metadata),
        "included_runs": run_metadata,
        "native_binaries_included": include_binaries,
    }


def validate_pack_archive(archive, inputs, stream_hashes):
    expected = {member_name(p) for p in PACKS}
    records = {}
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            fail("The initial archive contains duplicate members")
        if set(names) != expected:
            fail("The initial archive must contain exactly the twelve input packs; refusing to append twice")
        for relative in PACKS:
            entry = z.getinfo(member_name(relative))
            path = safe_file(relative)
            if entry.is_dir() or entry.file_size != path.stat().st_size:
                fail(f"Prepacked member size mismatch: {relative}")
            digest = inputs["sha256"][relative.removeprefix("inputs/")]
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                fail(f"Invalid input-pack SHA-256: {relative}")
            if stream_hashes:
                with z.open(entry) as stream:
                    if sha_stream(stream) != digest:
                        fail(f"Prepacked member SHA-256 mismatch: {relative}")
                print(f"Verified existing pack: {relative}", flush=True)
            records[relative] = {"bytes": entry.file_size, "sha256": digest, "origin": "prepacked"}
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", type=Path, default=ROOT.parent / "deliverables/LRI_C8_D2_HPC.zip")
    ap.add_argument("--run", default="results/pilot_complete_01", help="main completed run displayed in RESULTS.md and the PDF, relative to project root")
    ap.add_argument("--include-run", action="append", default=[], metavar="COMPLETE_RUN",
                    help="additional complete comparison run to retain; repeatable, relative to project root")
    ap.add_argument("--no-binaries", action="store_true", help="omit native executables and build records")
    ap.add_argument("--dry-run", action="store_true", help="validate selection and ZIP member names without writing or streaming the packs")
    a = ap.parse_args()
    for relative in (a.run, *a.include_run):
        if not re.fullmatch(r"results/[A-Za-z0-9_-]+", relative):
            fail("--run and --include-run must name runs directly beneath results/")
    archive = a.archive.absolute()
    if archive.is_symlink() or not archive.is_file():
        fail("--archive must be an existing regular file, not a symbolic link")
    sources, inputs, metadata = select_files(a.run, not a.no_binaries, a.include_run)
    archive_snapshot = snapshot(archive)
    records = validate_pack_archive(archive, inputs, stream_hashes=not a.dry_run)
    if a.dry_run:
        print(json.dumps({"archive": str(archive), "existing_packs": len(PACKS),
                          "files_to_append": len(sources), "metadata": metadata,
                          "selected_paths": sources,
                          "pack_content_hashes_checked": False}, indent=2))
        return
    states = {}
    for relative in sources:
        path = safe_file(relative)
        before = snapshot(path)
        digest = sha_file(path)
        if snapshot(path) != before:
            fail(f"File changed during preparation: {relative}")
        states[relative] = before
        records[relative] = {"bytes": before[2], "sha256": digest, "origin": "workspace"}
    manifest = {
        "schema": "c8-d2-delivery-1", "dimension": 2, "order": 8,
        "created_utc": datetime.now(timezone.utc).isoformat(), **metadata,
        "members_excluding_this_manifest": len(records),
        "uncompressed_bytes_excluding_this_manifest": sum(v["bytes"] for v in records.values()),
        "pack_hash_verification": "Each existing ZIP payload was streamed, CRC-checked and matched to the input manifest pinned by the completed run.",
        "selection": "Explicit code, documentation, graph inventories and certificates, fixtures, verification records, selected complete runs, and final PDF; runtime scratch and raw graph payloads excluded.",
        "files": dict(sorted(records.items())),
    }
    manifest_bytes = (json.dumps(manifest, indent=2, allow_nan=False) + "\n").encode()
    manifest_name = member_name("DELIVERY_MANIFEST.json")
    fd, temporary = tempfile.mkstemp(prefix=archive.stem + ".finishing-", suffix=".zip", dir=archive.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        shutil.copyfile(archive, temporary)
        if snapshot(archive) != archive_snapshot:
            fail("The input archive changed during packaging")
        with zipfile.ZipFile(temporary, "a", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as z:
            for relative in sources:
                path = safe_file(relative)
                if snapshot(path) != states[relative]:
                    fail(f"File changed before archiving: {relative}")
                z.write(path, member_name(relative))
                if snapshot(path) != states[relative]:
                    fail(f"File changed during archiving: {relative}")
            z.writestr(manifest_name, manifest_bytes)
        with zipfile.ZipFile(temporary) as z:
            names = z.namelist()
            expected = {member_name(p) for p in records} | {manifest_name}
            if len(names) != len(set(names)) or set(names) != expected:
                fail("Final archive has duplicate, unexpected, or missing members")
            # Packs were CRC/SHA checked before the byte-for-byte archive copy.
            for relative in sources:
                with z.open(member_name(relative)) as stream:
                    if sha_stream(stream) != records[relative]["sha256"]:
                        fail(f"Final member SHA-256 mismatch: {relative}")
            if z.read(manifest_name) != manifest_bytes:
                fail("Final delivery-manifest mismatch")
        if snapshot(archive) != archive_snapshot:
            fail("The input archive changed before publication")
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, archive)
        print(json.dumps({"archive": str(archive), "sha256": sha_file(archive),
                          "archive_bytes": archive.stat().st_size, "members": len(records) + 1,
                          "manifest_member": manifest_name, "checkpoint_files": metadata["checkpoint_files"],
                          "verification": "Every member CRC and SHA-256 checked; no duplicate members"}, indent=2))
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
