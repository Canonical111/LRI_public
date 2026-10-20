#!/usr/bin/env python3
"""Build a verified C8 precision-update ZIP without duplicating immutable packs.

The previously delivered LRI_C8_D2_HPC.zip is the exact base dependency. Its
twelve graph packs are unchanged. The update contains current code, inputs
other than the packs, documentation, certificates, and every selected complete
run, including all checkpoints. Extract the original archive, then this update
into the same parent directory. No original archive is modified.

Example (after final report/PDF generation):

  python3 tools/build_precision_delivery.py \
    --run results/precision_complete_03 \
    --include-run results/refinement_complete_02 \
    --include-run results/pilot_complete_01 --dry-run

Repeat without --dry-run to publish a new archive. Existing output files are
refused. --verify-installed validates all installed update files and graph packs.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

import build_delivery as delivery

ROOT = delivery.ROOT
PREFIX = delivery.PREFIX
MANIFEST = "PRECISION_DELIVERY_MANIFEST.json"
README = "PRECISION_UPDATE_README.txt"
SCHEMA = "c8-d2-precision-delivery-1"
DEFAULT_BASE_SHA256 = "14b0a4a6df74bade4f5842ee04d7879706f7b82d8bd76a6a440e036d3a8e0494"
DEFAULT_LIMIT = 500_000_000
REQUIRED = ("tools/build_precision_delivery.py", "tests/precision_delivery.py")
OPTIONAL = (
    "tools/precision_allocation.py", "tests/precision_allocation.py",
    "verification/precision_allocation_checks.json", "verification/precision_delivery.json",
    "verification/precision_allocation_independent.json",
)
PRECISION_RECORDS = (
    "precision_work/precision_allocation_03.json",
    "precision_work/precision_allocation_03_summary.json",
    "precision_work/precision_protocol_03.txt",
    "precision_work/cost_model_refinement.json",
    "tools/precision_allocation.py", "tests/precision_allocation.py",
    "verification/precision_allocation_checks.json",
)


def check_relative(relative):
    p = PurePosixPath(relative)
    if (p.is_absolute() or not p.parts or "\\" in relative
            or relative != p.as_posix() or any(part in (".", "..") for part in p.parts)):
        delivery.fail(f"Unsafe archive-relative path: {relative}")
    return p


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def validate_base_archive(archive, expected_sha256, inputs, input_manifest_sha256):
    """Pin the exact previously verified base; inspect its directory and manifest.

    The entire compressed base is hashed. Re-expanding 7.8 GB of pack payloads
    adds no evidence when the hash is identical to the earlier CRC/SHA-verified
    deliverable. The update explicitly records this distinction.
    """
    if archive.is_symlink() or not archive.is_file():
        delivery.fail("The base archive must be an existing regular file")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        delivery.fail("A valid SHA-256 of the previously verified base is required")
    before = delivery.snapshot(archive)
    delivery.checked(archive, expected_sha256)
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            delivery.fail("The base archive contains duplicate members")
        manifest_name = delivery.member_name("DELIVERY_MANIFEST.json")
        raw_manifest = z.read(manifest_name)
        manifest = json.loads(raw_manifest)
        if (manifest.get("schema") != "c8-d2-delivery-1"
                or manifest.get("dimension") != 2 or manifest.get("order") != 8
                or manifest.get("input_manifest_sha256") != input_manifest_sha256):
            delivery.fail("The base archive does not identify these C8 inputs")
        records = manifest.get("files", {})
        expected_names = {delivery.member_name(p) for p in records} | {manifest_name}
        if set(names) != expected_names:
            delivery.fail("The base directory differs from its delivery manifest")
        compressed = {}
        for relative, record in records.items():
            check_relative(relative)
            info = z.getinfo(delivery.member_name(relative))
            mode = (info.external_attr >> 16) & 0xFFFF
            if (info.is_dir() or stat.S_ISLNK(mode) or info.flag_bits & 1
                    or info.file_size != record.get("bytes")
                    or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256")))):
                delivery.fail(f"Invalid base archive member: {relative}")
            compressed[relative] = info.compress_size
        packs = {}
        for relative in delivery.PACKS:
            expected = inputs["sha256"][relative.removeprefix("inputs/")]
            record = records.get(relative, {})
            if record.get("sha256") != expected:
                delivery.fail(f"Base pack does not match the current input manifest: {relative}")
            packs[relative] = {"bytes": record["bytes"], "sha256": expected}
        if records.get("inputs/manifest.json", {}).get("sha256") != input_manifest_sha256:
            delivery.fail("Base input-manifest payload hash is inconsistent")
    if delivery.snapshot(archive) != before:
        delivery.fail("The base archive changed while being verified")
    dependency = {
        "archive_file_name": archive.name,
        "archive_bytes": before[2], "archive_sha256": expected_sha256,
        "delivery_manifest_sha256": digest_bytes(raw_manifest),
        "input_manifest_sha256": input_manifest_sha256,
        "required_files": packs,
        "verification": "Entire compressed base SHA-256 matches the supplied, previously CRC/SHA-verified archive identity; the twelve pack hashes and sizes agree with its delivery manifest and the run-pinned input manifest. Pack payloads were not redundantly decompressed during update packaging.",
    }
    return dependency, records, compressed, before


def prepare_sources(sources):
    records, states = {}, {}
    if len(sources) != len(set(sources)):
        delivery.fail("Duplicate source selection")
    for relative in sources:
        check_relative(relative)
        if relative in delivery.PACKS or relative in (MANIFEST, README):
            delivery.fail(f"Forbidden update source: {relative}")
        path = delivery.safe_file(relative)
        before = delivery.snapshot(path)
        digest = delivery.sha_file(path)
        if delivery.snapshot(path) != before:
            delivery.fail(f"File changed during preparation: {relative}")
        states[relative] = before
        records[relative] = {"bytes": before[2], "sha256": digest, "origin": "workspace"}
    return records, states


def precision_provenance_files(metadata):
    """Retain and cross-check both actual source runs behind precision plan 03."""
    run_manifests = {row["run"]: delivery.load(delivery.safe_file(row["run"] + "/manifest.json"))
                     for row in metadata["included_runs"]}
    current = run_manifests[metadata["run"]]
    allocation_path = f"{metadata['run']}/allocation.json"
    if not (ROOT / allocation_path).is_file():
        return set()
    allocation = delivery.load(delivery.safe_file(allocation_path))
    pilots = allocation.get("precision_source_pilots")
    if pilots is None:
        return set()
    if set(pilots) != {"earlier", "latest"}:
        delivery.fail("The precision allocation must identify both source pilots")
    files = set(PRECISION_RECORDS)
    checked = delivery.checked
    checked(delivery.safe_file(PRECISION_RECORDS[0]), current["allocation_file_sha256"])
    checked(delivery.safe_file("precision_work/cost_model_refinement.json"), current["cost_model_sha256"])
    summary = delivery.load(delivery.safe_file(PRECISION_RECORDS[1]))
    if (summary.get("schema") != "c8-d2-precision-allocation-summary-1"
            or summary.get("allocation") != PRECISION_RECORDS[0]
            or summary.get("allocation_sha256") != current["allocation_file_sha256"]):
        delivery.fail("The precision summary identifies a different frozen allocation")
    checked(delivery.safe_file("tools/precision_allocation.py"), summary.get("generator_sha256"))
    pilot_seeds = set()
    for role, provenance in pilots.items():
        run = provenance.get("run")
        if run not in run_manifests or run == metadata["run"]:
            delivery.fail(f"The {role} precision source is not an included independent earlier run")
        source = run_manifests[run]
        checked(delivery.safe_file(f"{run}/manifest.json"), provenance.get("source_manifest_sha256"))
        for field in ("backend", "executable_sha256"):
            if provenance.get(field) != source[field] or source[field] != current[field]:
                delivery.fail(f"The {role} precision source has a different {field}")
        if provenance.get("pilot_seed") != source["seed"]:
            delivery.fail(f"The {role} precision source has a different pilot seed")
        pilot_seeds.add(source["seed"])
        model_path = provenance.get("model", "")
        p = check_relative(model_path)
        if p.suffix != ".json" or p.parts[0] not in ("precision_work", "results"):
            delivery.fail("The precision source model must be an explicit project JSON file")
        checked(delivery.safe_file(model_path), provenance.get("model_sha256"))
        model = delivery.load(delivery.safe_file(model_path))
        if (model.get("schema") != "c8-d2-allocation-1"
                or model.get("dimension") != 2 or model.get("order") != 8
                or model.get("source_manifest_sha256") != provenance["source_manifest_sha256"]
                or model.get("inputs_manifest_sha256") != current["inputs_manifest_sha256"]
                or model.get("source_groups") != provenance.get("source_groups")):
            delivery.fail(f"The {role} frozen model has inconsistent source provenance")
        result = delivery.load(delivery.safe_file(f"{run}/C8_result.json"))
        if set(provenance.get("source_groups", {})) != delivery.GROUPS:
            delivery.fail(f"The {role} precision source does not cover all 24 groups")
        for group, group_record in provenance["source_groups"].items():
            if group_record.get("merged_sha256") != result["merged_sha256"][group]:
                delivery.fail(f"Precision planning identifies a different merged group: {run}/{group}")
            merged = delivery.load(delivery.safe_file(f"{run}/groups/{group}/merged.json"))
            if group_record.get("graph_replicates_sha256") != merged["graph_replicates_sha256"]:
                delivery.fail(f"Precision planning identifies different graph replicates: {run}/{group}")
        files.add(model_path)
    if (len(pilot_seeds) != 2 or set(allocation.get("pilot_seeds", [])) != pilot_seeds
            or current["seed"] in pilot_seeds):
        delivery.fail("The precision run and its two planning pilots must use distinct seeds")
    return files


def compression_category(relative):
    if "/checkpoints/" in relative:
        return "checkpoint_json"
    if relative.startswith("results/") or relative.startswith("precision_work/"):
        name = PurePosixPath(relative).name
        if name in ("tasks.sqlite", "sobol.bin", "graph_replicates.csv"):
            return name
        return "result_json"
    return "other" + PurePosixPath(relative).suffix


def estimate_bytes(records, base_records, compressed):
    """Estimate only; actual compressed output is checked before publication."""
    categories = defaultdict(lambda: [0, 0])
    for relative, record in base_records.items():
        if relative not in delivery.PACKS:
            values = categories[compression_category(relative)]
            values[0] += record["bytes"]
            values[1] += compressed[relative]
    total, exact, modeled = 0, 0, 0
    by_run = defaultdict(lambda: {"files": 0, "uncompressed_bytes": 0, "estimated_zip_bytes": 0})
    for relative, record in records.items():
        base = base_records.get(relative)
        if base and all(base.get(key) == record[key] for key in ("bytes", "sha256")):
            size = compressed[relative]
            exact += 1
        else:
            n, compressed_n = categories[compression_category(relative)]
            size = round(record["bytes"] * compressed_n / n) if n else record["bytes"]
            modeled += 1
        # Two copies of the UTF-8 filename plus conservative local/central header space.
        size += 180 + 2 * len(delivery.member_name(relative).encode())
        total += size
        parts = relative.split("/")
        category = "/".join(parts[:2]) if parts[0] == "results" else "code_inputs_docs_certificates"
        row = by_run[category]
        row["files"] += 1
        row["uncompressed_bytes"] += record["bytes"]
        row["estimated_zip_bytes"] += size
    # Allow for the generated manifest, which scales with the selected file count.
    total += 100_000 + 65 * len(records)
    return {"estimated_archive_bytes": total, "same_payload_as_base_files": exact,
            "estimated_new_or_changed_files": modeled,
            "note": "Planning estimate based on exact base compression for unchanged files and observed per-format ratios for new files; the final byte limit is enforced on the actual ZIP.",
            "categories": dict(sorted(by_run.items()))}


def instructions(metadata, dependency):
    runs = "\n".join(f"  {r['run']} ({r['role']})" for r in metadata["included_runs"])
    return (f"C8 in d=2: precision update\n\n"
            f"Primary result: {metadata['run']}/C8_result.json\n"
            f"Primary result SHA-256: {metadata['result_sha256']}\n\n"
            f"This update includes current code, analytic inputs, graph inventories,\n"
            f"certificates, documentation, and these complete saved calculations:\n{runs}\n"
            f"All selected runs retain their task databases, Sobol nets, merged graph\n"
            f"replicates, frozen plans, and individual checkpoint records.\n\n"
            f"Required unchanged graph packs are in the previously delivered archive:\n"
            f"  {dependency['archive_file_name']}\n"
            f"  SHA-256 {dependency['archive_sha256']}\n"
            f"  Size {dependency['archive_bytes']} bytes\n\n"
            f"Installation\n"
            f"1. Extract the original archive into a directory of your choice.\n"
            f"2. Extract this update into that same directory, allowing its current\n"
            f"   code and documentation to replace the earlier versions. Both ZIPs\n"
            f"   use the top-level directory {PREFIX}.\n"
            f"3. From {PREFIX}, run:\n"
            f"     python3 tools/build_precision_delivery.py --verify-installed\n"
            f"   This checks every update payload and every required pack by SHA-256.\n"
            f"   It streams approximately 8 GB of inputs and needs no network access.\n"
            f"4. Follow README.md and RESULTS.md to inspect or reassemble the result.\n\n"
            f"{MANIFEST} describes this current update. The original\n"
            f"DELIVERY_MANIFEST.json remains a record of the earlier archive and is\n"
            f"not a checksum inventory of the overlaid current working directory.\n"
            f"The original ZIP is unchanged and can be kept as the reusable input\n"
            f"dependency. This update intentionally contains no graph-pack payloads.\n").encode()


def verify_update_archive(archive, records, manifest_bytes):
    expected = {delivery.member_name(relative) for relative in records}
    expected.add(delivery.member_name(MANIFEST))
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != expected:
            delivery.fail("The update ZIP has duplicate, unexpected, or missing members")
        for relative, record in records.items():
            info = z.getinfo(delivery.member_name(relative))
            if info.file_size != record["bytes"]:
                delivery.fail(f"Update member size mismatch: {relative}")
            with z.open(info) as stream:
                if delivery.sha_stream(stream) != record["sha256"]:
                    delivery.fail(f"Update member SHA-256 mismatch: {relative}")
        if z.read(delivery.member_name(MANIFEST)) != manifest_bytes:
            delivery.fail("Update manifest content mismatch")


def publish_archive(archive, sources, states, records, generated, manifest_bytes,
                    max_bytes, base_archive=None, base_snapshot=None):
    """Write, verify, and publish with no replacement of an existing artifact."""
    if max_bytes <= 0:
        delivery.fail("The archive byte limit must be positive")
    if archive.exists() or archive.is_symlink():
        delivery.fail("The output archive already exists; choose a new --archive path")
    if not archive.parent.is_dir():
        delivery.fail("The output archive's parent directory must already exist")
    fd, temp_name = tempfile.mkstemp(prefix=archive.stem + ".building-", suffix=".zip", dir=archive.parent)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as z:
            for relative in sources:
                path = delivery.safe_file(relative)
                if delivery.snapshot(path) != states[relative]:
                    delivery.fail(f"File changed before archiving: {relative}")
                z.write(path, delivery.member_name(relative))
                if delivery.snapshot(path) != states[relative]:
                    delivery.fail(f"File changed during archiving: {relative}")
            for relative, payload in sorted(generated.items()):
                z.writestr(delivery.member_name(relative), payload)
            z.writestr(delivery.member_name(MANIFEST), manifest_bytes)
        if temporary.stat().st_size > max_bytes:
            delivery.fail(f"The complete update is {temporary.stat().st_size} bytes, exceeding --max-bytes {max_bytes}; no archive was published")
        verify_update_archive(temporary, records, manifest_bytes)
        if base_archive is not None and delivery.snapshot(base_archive) != base_snapshot:
            delivery.fail("The base archive changed during update packaging")
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        # Hard-link publication is atomic and refuses an intervening existing file.
        os.link(temporary, archive)
        return {"archive": str(archive), "archive_bytes": archive.stat().st_size,
                "sha256": delivery.sha_file(archive), "members": len(records) + 1,
                "verification": "Every update member was CRC-checked and SHA-256 matched; no duplicate members, no graph-pack payloads, and the exact base archive remained unchanged."}
    finally:
        temporary.unlink(missing_ok=True)


def verify_installed():
    manifest = delivery.load(delivery.safe_file(MANIFEST))
    if (manifest.get("schema") != SCHEMA or manifest.get("dimension") != 2
            or manifest.get("order") != 8 or manifest.get("format") != "overlay_without_immutable_graph_packs"):
        delivery.fail("This is not a C8 precision-update manifest")
    records = manifest.get("files", {})
    packs = manifest.get("base_dependency", {}).get("required_files", {})
    if set(packs) != set(delivery.PACKS) or set(records) & set(packs):
        delivery.fail("The installed manifest has an invalid immutable-pack boundary")
    if len(records) != manifest.get("members_excluding_this_manifest"):
        delivery.fail("The installed manifest has an inconsistent file count")
    for relative, record in {**records, **packs}.items():
        check_relative(relative)
        path = delivery.safe_file(relative)
        if path.stat().st_size != record.get("bytes"):
            delivery.fail(f"Installed file size mismatch: {relative}")
        delivery.checked(path, record.get("sha256"))
    inputs = delivery.load(delivery.safe_file("inputs/manifest.json"))
    for relative, record in packs.items():
        if record["sha256"] != inputs["sha256"].get(relative.removeprefix("inputs/")):
            delivery.fail(f"Installed pack/input-manifest mismatch: {relative}")
    if delivery.sha_file(delivery.safe_file("inputs/manifest.json")) != manifest["input_manifest_sha256"]:
        delivery.fail("Installed input manifest differs from the completed run")
    return {"verified": True, "update_files": len(records), "immutable_packs": len(packs),
            "run": manifest["run"], "result_sha256": manifest["result_sha256"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", help="primary completed run, relative to the project root")
    ap.add_argument("--include-run", action="append", default=[], metavar="COMPLETE_RUN")
    ap.add_argument("--base-archive", type=Path, default=ROOT.parent / "deliverables/LRI_C8_D2_HPC.zip")
    ap.add_argument("--base-sha256", default=DEFAULT_BASE_SHA256,
                    help="SHA-256 of the previously verified exact base archive")
    ap.add_argument("--archive", type=Path, default=ROOT.parent / "deliverables/LRI_C8_D2_precision_update.zip")
    ap.add_argument("--extra-file", action="append", default=[], metavar="RELATIVE_PATH",
                    help="additional explicitly selected planning, protocol, or verification file")
    ap.add_argument("--max-bytes", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--no-binaries", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify-installed", action="store_true")
    a = ap.parse_args()
    if a.verify_installed:
        if a.run or a.include_run or a.extra_file or a.dry_run:
            ap.error("--verify-installed cannot be combined with build options")
        print(json.dumps(verify_installed(), indent=2))
        return
    if a.run is None:
        ap.error("--run is required for an update build")
    for relative in (a.run, *a.include_run):
        if not re.fullmatch(r"results/[A-Za-z0-9_-]+", relative):
            delivery.fail("Runs must be named directly beneath results/")
    archive = a.archive.absolute()
    base_archive = a.base_archive.absolute()
    if archive == base_archive or archive.resolve() == base_archive.resolve():
        delivery.fail("The output must be a new archive, separate from the immutable base")
    if archive.exists() or archive.is_symlink():
        delivery.fail("The output archive already exists; choose a new --archive path")
    sources, inputs, metadata = delivery.select_files(a.run, not a.no_binaries, a.include_run)
    sources = set(sources) | set(REQUIRED)
    sources.update(precision_provenance_files(metadata))
    sources.update(relative for relative in OPTIONAL if (ROOT / relative).exists())
    for relative in a.extra_file:
        check_relative(relative)
        if PurePosixPath(relative).parts[0] not in ("precision_work", "verification", "tools", "tests", "docs"):
            delivery.fail("--extra-file must be an explicit planning, verification, source, test, or documentation file")
        sources.add(relative)
    sources = sorted(sources)
    dependency, base_records, compressed, base_snapshot = validate_base_archive(
        base_archive, a.base_sha256, inputs, metadata["input_manifest_sha256"])
    records, states = prepare_sources(sources)
    estimate = estimate_bytes(records, base_records, compressed)
    if a.dry_run:
        print(json.dumps({"dry_run": True, "archive": str(archive), "files": len(sources),
                          "maximum_archive_bytes": a.max_bytes, "estimate": estimate,
                          "base_dependency": dependency, "metadata": metadata}, indent=2))
        return
    generated = {README: instructions(metadata, dependency)}
    for relative, payload in generated.items():
        records[relative] = {"bytes": len(payload), "sha256": digest_bytes(payload), "origin": "generated"}
    manifest = {"schema": SCHEMA, "dimension": 2, "order": 8,
                "format": "overlay_without_immutable_graph_packs",
                "created_utc": datetime.now(timezone.utc).isoformat(), **metadata,
                "base_dependency": dependency,
                "members_excluding_this_manifest": len(records),
                "uncompressed_bytes_excluding_this_manifest": sum(row["bytes"] for row in records.values()),
                "selection": "Current explicit code/docs/certificates and every selected complete run; all task databases, nets, graph replicates, checkpoints and scheduling provenance retained. Only twelve unchanged input packs are external, in the identified original archive. Runtime scratch and raw graph payloads excluded.",
                "files": dict(sorted(records.items()))}
    manifest_bytes = (json.dumps(manifest, indent=2, allow_nan=False) + "\n").encode()
    result = publish_archive(archive, sources, states, records, generated, manifest_bytes,
                             a.max_bytes, base_archive, base_snapshot)
    result.update(run=a.run, checkpoint_files=metadata["checkpoint_files"],
                  required_base_archive_sha256=dependency["archive_sha256"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
