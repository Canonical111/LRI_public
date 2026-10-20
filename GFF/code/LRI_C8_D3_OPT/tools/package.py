#!/usr/bin/env python3
"""Create the reproducible ZIP of scientific inputs, source and saved results."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from delivery import write_manifest
from io_utils import ROOT, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("Use a new archive path")
    if ROOT == output or ROOT in output.parents:
        raise ValueError("Create the archive outside the package directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = write_manifest()
    names = [row["path"] for row in manifest["files"]] + ["DELIVERY_MANIFEST.json", "SHA256SUMS"]
    temporary = output.with_suffix(output.suffix + ".partial")
    if temporary.exists():
        raise FileExistsError("An unfinished archive is present; inspect it before retrying")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for index, name in enumerate(names):
            archive.write(ROOT / name, ROOT.name + "/" + name)
            if (index + 1) % 2500 == 0:
                print(f"Archived {index + 1}/{len(names)} files", flush=True)
    # Validate the exact member inventory, sizes and non-duplication before
    # publishing. ZIP CRCs are checked by ordinary extraction; scientific
    # contents have the independent per-file SHA-256 manifest.
    with ZipFile(temporary) as archive:
        info = archive.infolist()
        expected = {ROOT.name + "/" + name: (ROOT / name).stat().st_size for name in names}
        actual = {row.filename: row.file_size for row in info}
        if len(info) != len(expected) or actual != expected:
            raise ValueError("Archive member inventory or sizes differ from the deliverable")
    temporary.rename(output)
    print(json.dumps({"archive": str(output), "bytes": output.stat().st_size,
                      "sha256": digest(output), "members": len(names),
                      "uncompressed_bytes": sum(expected.values())}, indent=2))


if __name__ == "__main__":
    main()
