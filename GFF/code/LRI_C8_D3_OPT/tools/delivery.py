#!/usr/bin/env python3
"""Write or verify the source/input/result inventory for this deliverable."""
from __future__ import annotations

import argparse
from pathlib import Path
import json

from io_utils import ROOT, digest, load, save

EXCLUDED_DIRS = {"bin", "tmp", "__pycache__", ".venv", "regenerated_graph_inputs"}
EXCLUDED_FILES = {"DELIVERY_MANIFEST.json", "SHA256SUMS"}


def files():
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if path.is_file() and not any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts):
            if path.name not in EXCLUDED_FILES and path.suffix not in {".pyc", ".tmp"}:
                yield path


def write_manifest():
    rows = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": digest(path)} for path in files()]
    record = {
        "schema": "lri-c8-d3-delivery-1", "dimension": 3, "order": 8,
        "files": rows, "file_count": len(rows), "total_bytes": sum(r["bytes"] for r in rows),
        "scope": "Source, generated scientific inputs, complete pilot records and verification. Build products and temporary files excluded.",
    }
    save(ROOT / "DELIVERY_MANIFEST.json", record, replace=True)
    (ROOT / "SHA256SUMS").write_text("".join(f"{r['sha256']}  {r['path']}\n" for r in rows))
    return record


def verify(strict=False):
    manifest = load(ROOT / "DELIVERY_MANIFEST.json")
    if manifest.get("schema") != "lri-c8-d3-delivery-1":
        raise ValueError("Invalid delivery inventory")
    seen = set()
    for row in manifest["files"]:
        name = row["path"]
        rel = Path(name)
        if name in seen or rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Invalid or duplicated delivery path")
        seen.add(name)
        path = ROOT / name
        if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError(f"Changed or missing delivery file: {name}")
    if strict:
        actual = {str(path.relative_to(ROOT)) for path in files()}
        if actual != seen:
            raise ValueError(f"Unlisted files: {sorted(actual - seen)[:10]}; missing files: {sorted(seen - actual)[:10]}")
    return {"verified": True, "files": len(seen), "bytes": sum(r["bytes"] for r in manifest["files"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "verify"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = write_manifest() if args.command == "write" else verify(args.strict)
    print(json.dumps({k: v for k, v in result.items() if k != "files" or isinstance(v, int)}, indent=2))


if __name__ == "__main__":
    main()
