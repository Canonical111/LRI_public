#!/usr/bin/env python3
"""Record the native executable and actual compiler invocation after a build."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("backend", choices=("decimal", "gmp"))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("Missing build command")
    executable = args.executable.resolve()
    root = Path(__file__).resolve().parents[1]
    description = json.loads(subprocess.check_output([str(executable), "--describe"], text=True))
    record = dict(
        schema="c8-d2-build-record-1",
        backend=args.backend,
        command=command,
        native=description,
        compiler_version=subprocess.check_output([command[0], "--version"], text=True).splitlines()[0],
        executable_sha256=sha256(executable),
        source_sha256={p.name: sha256(p) for p in (root / "src").glob("*.?pp")},
        variables={key: os.environ.get("C8B_" + key, "") for key in
                   ("CXX", "CPPFLAGS", "OPTFLAGS", "CXXFLAGS", "REQUIRED", "LDFLAGS", "LDLIBS")},
    )
    output = Path(str(executable) + ".build.json")
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"Recorded {output.name}")


if __name__ == "__main__":
    main()
