#!/usr/bin/env python3
"""Check packaging integrity and refusal paths using tiny synthetic ZIPs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_delivery as original
import build_precision_delivery as packaging


def sha(data):
    return hashlib.sha256(data).hexdigest()


class PackagingChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="precision_delivery_", dir=ROOT / "verification")
        self.root = Path(self.temp.name)
        self.old_root = original.ROOT
        original.ROOT = self.root

    def tearDown(self):
        original.ROOT = self.old_root
        self.temp.cleanup()

    def base(self):
        packs = {p: (p + "\n") .encode() * 3 for p in original.PACKS}
        inputs = {"schema": "c8-d2-hpc-inputs-1", "sha256": {
            p.removeprefix("inputs/"): sha(data) for p, data in packs.items()}}
        raw_inputs = json.dumps(inputs).encode()
        records = {p: {"bytes": len(data), "sha256": sha(data)} for p, data in packs.items()}
        records["inputs/manifest.json"] = {"bytes": len(raw_inputs), "sha256": sha(raw_inputs)}
        manifest = {"schema": "c8-d2-delivery-1", "dimension": 2, "order": 8,
                    "input_manifest_sha256": sha(raw_inputs), "files": records}
        archive = self.root / "base.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p, data in packs.items():
                z.writestr(original.member_name(p), data)
            z.writestr(original.member_name("inputs/manifest.json"), raw_inputs)
            z.writestr(original.member_name("DELIVERY_MANIFEST.json"), json.dumps(manifest))
        return archive, inputs, sha(raw_inputs), packs, raw_inputs

    def source(self):
        relative = "docs/result.txt"
        target = self.root / relative
        target.parent.mkdir(parents=True)
        target.write_text("reproducible finite-assembly result\n" * 50)
        records, states = packaging.prepare_sources([relative])
        manifest_bytes = b'{"synthetic": true}\n'
        return relative, records, states, manifest_bytes

    def test_base_identity_and_pack_agreement(self):
        archive, inputs, input_hash, packs, _ = self.base()
        dep, records, compressed, snapshot = packaging.validate_base_archive(
            archive, original.sha_file(archive), inputs, input_hash)
        self.assertEqual(set(dep["required_files"]), set(original.PACKS))
        self.assertEqual(snapshot[2], archive.stat().st_size)
        self.assertEqual(set(records), set(compressed))
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            packaging.validate_base_archive(archive, "0" * 64, inputs, input_hash)
        altered_inputs = json.loads(json.dumps(inputs))
        altered_inputs["sha256"][original.PACKS[0].removeprefix("inputs/")] = "a" * 64
        with self.assertRaisesRegex(ValueError, "Base pack does not match"):
            packaging.validate_base_archive(archive, original.sha_file(archive), altered_inputs, input_hash)

    def test_duplicate_base_refused(self):
        archive, inputs, input_hash, _, _ = self.base()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "a") as z:
                z.writestr(original.member_name("inputs/manifest.json"), b"duplicate")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            packaging.validate_base_archive(archive, original.sha_file(archive), inputs, input_hash)

    def test_publish_verify_no_clobber_and_no_pack_payloads(self):
        relative, records, states, manifest = self.source()
        archive = self.root / "update.zip"
        report = packaging.publish_archive(archive, [relative], states, records, {}, manifest, 1_000_000)
        self.assertEqual(report["members"], 2)
        packaging.verify_update_archive(archive, records, manifest)
        old = archive.read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            packaging.publish_archive(archive, [relative], states, records, {}, manifest, 1_000_000)
        self.assertEqual(archive.read_bytes(), old)
        with self.assertRaisesRegex(ValueError, "Forbidden update source"):
            packaging.prepare_sources([original.PACKS[0]])

    def test_changed_source_and_size_cap_are_atomic(self):
        relative, records, states, manifest = self.source()
        archive = self.root / "update.zip"
        with self.assertRaisesRegex(ValueError, "exceeding"):
            packaging.publish_archive(archive, [relative], states, records, {}, manifest, 1)
        self.assertFalse(archive.exists())
        (self.root / relative).write_text("modified after preparation")
        with self.assertRaisesRegex(ValueError, "changed before"):
            packaging.publish_archive(archive, [relative], states, records, {}, manifest, 1_000_000)
        self.assertFalse(archive.exists())
        self.assertEqual(list(self.root.glob("*.building-*.zip")), [])

    def test_changed_base_is_atomic(self):
        base, _, _, _, _ = self.base()
        before = original.snapshot(base)
        relative, records, states, manifest = self.source()
        base.write_bytes(base.read_bytes() + b"changed")
        archive = self.root / "update.zip"
        with self.assertRaisesRegex(ValueError, "base archive changed"):
            packaging.publish_archive(archive, [relative], states, records, {}, manifest,
                                      1_000_000, base, before)
        self.assertFalse(archive.exists())

    def test_duplicate_update_refused(self):
        relative, records, states, manifest = self.source()
        archive = self.root / "update.zip"
        packaging.publish_archive(archive, [relative], states, records, {}, manifest, 1_000_000)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "a") as z:
                z.writestr(original.member_name(relative), b"duplicate")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            packaging.verify_update_archive(archive, records, manifest)

    def test_installed_payloads_and_pack_corruption(self):
        _, inputs, input_hash, packs, raw_inputs = self.base()
        for relative, data in {**packs, "inputs/manifest.json": raw_inputs}.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        relative, records, _, _ = self.source()
        records["inputs/manifest.json"] = {"bytes": len(raw_inputs), "sha256": input_hash}
        manifest = {"schema": packaging.SCHEMA, "dimension": 2, "order": 8,
                    "format": "overlay_without_immutable_graph_packs",
                    "members_excluding_this_manifest": len(records), "files": records,
                    "base_dependency": {"required_files": {
                        p: {"bytes": len(data), "sha256": sha(data)} for p, data in packs.items()}},
                    "input_manifest_sha256": input_hash, "run": "results/synthetic",
                    "result_sha256": records[relative]["sha256"]}
        (self.root / packaging.MANIFEST).write_text(json.dumps(manifest))
        report = packaging.verify_installed()
        self.assertTrue(report["verified"])
        self.assertEqual(report["immutable_packs"], 12)
        first = self.root / original.PACKS[0]
        original_data = first.read_bytes()
        first.write_bytes(b"X" + original_data[1:])
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            packaging.verify_installed()

    def test_paths_and_duplicate_sources_refused(self):
        for relative in ("../escape", "/absolute", "docs/../escape", "docs//ambiguous", "docs\\escape", "./local"):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                packaging.check_relative(relative)
        relative, _, _, _ = self.source()
        with self.assertRaisesRegex(ValueError, "Duplicate source"):
            packaging.prepare_sources([relative, relative])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "verification/precision_delivery.json")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PackagingChecks)
    names = [case.id().rsplit(".", 1)[-1] for case in suite]
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"schema": "c8-d2-precision-delivery-checks-1", "passed": result.wasSuccessful(),
              "checks": names, "tests_run": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "tool_sha256": {name: original.sha_file(ROOT / "tools" / name)
                              for name in ("build_delivery.py", "build_precision_delivery.py")},
              "test_sha256": original.sha_file(Path(__file__))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
