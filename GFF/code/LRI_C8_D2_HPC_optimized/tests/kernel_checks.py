#!/usr/bin/env python3
"""Native extension checks; optional complete C7 package enables graph replays.

Run after make. The synthetic checks exercise 16 edge coordinates, all three
layouts, the z^6 recurrence, and cancellation requiring multiprecision. They
are algebra and memory tests, not a numerical determination of C8.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["-std=c++17", "-fopenmp", "-ffp-contract=off", "-fno-fast-math"]


def load(path):
    return json.loads(Path(path).read_text())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command):
    result = subprocess.run(list(map(str, command)), cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {shlex.join(list(map(str, command)))}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def compile_source(source, destination, backend, record, sanitizer=False, legacy=False):
    variables = record["variables"]
    compiler = shlex.split(os.environ.get("CXX", variables["CXX"]))
    flags = []
    for key in ("CPPFLAGS", "OPTFLAGS", "CXXFLAGS"):
        flags += shlex.split(os.environ.get(key, variables[key]))
    flags += REQUIRED
    if sanitizer:
        flags += ["-O1", "-g1", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    if backend == "gmp":
        flags += ["-DC7_USE_GMP" if legacy else "-DC8_USE_GMP"]
    links = shlex.split(os.environ.get("LDFLAGS", variables["LDFLAGS"])) + ["-lquadmath"]
    if backend == "gmp":
        links += ["-lgmp"]
    links += shlex.split(os.environ.get("LDLIBS", variables["LDLIBS"]))
    command = compiler + flags + [str(source)] + links + ["-o", str(destination)]
    run(command)
    return command


def scientific(row):
    return {k: row[k] for k in ("uid", "rep", "graph", "begin", "end", "total", "quad", "mp", "max_abs", "values")}


def compare_rows(reference, candidate, exact=True):
    if len(reference) != len(candidate):
        raise AssertionError("Different row counts")
    largest = Decimal(0)
    for a, b in zip(reference, candidate):
        if exact:
            if scientific(a) != scientific(b):
                raise AssertionError(f"Replay mismatch at graph {a['graph']}, replicate {a['rep']}")
        else:
            if {k: v for k, v in scientific(a).items() if k not in ("values", "max_abs")} != {
                k: v for k, v in scientific(b).items() if k not in ("values", "max_abs")
            }:
                raise AssertionError("Changed row identity or precision-promotion counts")
            for x, y in zip(a["values"] + [a["max_abs"]], b["values"] + [b["max_abs"]]):
                error = abs(Decimal(x) - Decimal(y)) / max(Decimal(1), abs(Decimal(x)))
                largest = max(largest, error)
                if error > Decimal("1e-30"):
                    raise AssertionError("Backend discrepancy exceeds 1e-30 normalized")
    return str(largest)


def replay(reference, temporary, backends, records, full, points, threads, gamma8):
    gamma7 = reference / "inputs/gamma_d2_7.txt"
    original = temporary / "c7d2_decimal"
    compile_source(reference / "src/c7d2_integrate.cpp", original, "decimal", records["decimal"])
    result = []
    old = reference / "reference/LRI_C7_d2_progress"
    for sector, graph_root in (("free", old), ("power", reference / "reference/power_mass")):
        for L in range(3, 8):
            inventory = load(graph_root / f"inputs/L{L}/inventory.json")
            rows = [g for g in inventory if g["status"] == "finite-kernel"]
            # Includes every L7 zero-channel graph restored for its C8 derivative.
            if not full:
                rows = sorted(rows, key=lambda g: (g.get("terms", 0), g["id"]))
                rows = list({g["id"]: g for g in rows[:2] + rows[-2:]}.values())
            summary = dict(sector=sector, L=L, graphs=len(rows), samples=2 * points * len(rows),
                           extra_L7_zero_channel=sum(g["mass_numerator"] == 4 for g in rows) if L == 7 else 0,
                           decimal_exact=True, gmp_max_normalized_difference="0", leading_C8_jets_exact=True,
                           mp_calls=0)
            for offset in range(0, len(rows), 64):
                group = rows[offset:offset + 64]
                tasks = temporary / f"{sector}_{L}_{offset}.tasks"
                lines = [f"C7D2TASKS1 {L} {2 * len(group)}"]
                for rep in range(2):
                    for i, graph in enumerate(group):
                        lines.append(f"{rep * len(group) + i} {rep} {graph['id']} 0 {points} {points}")
                tasks.write_text("\n".join(lines) + "\n")
                output = temporary / "native.json"
                base = [str(graph_root / "inputs"), str(gamma7), str(old / f"inputs/a_L{L}.net"),
                        str(tasks), str(output), str(17421843 + L), "0", ".8", str(threads), "compensated", "-"]
                run([original] + base)
                expected = load(output)["rows"]
                summary["mp_calls"] += sum(row["mp"] for row in expected)
                for backend in backends:
                    executable = ROOT / f"bin/c8d2_{backend}"
                    run([executable] + base + ["7"])
                    actual = load(output)["rows"]
                    discrepancy = compare_rows(expected, actual, exact=backend == "decimal")
                    if backend == "gmp":
                        summary["gmp_max_normalized_difference"] = str(max(Decimal(discrepancy), Decimal(summary["gmp_max_normalized_difference"])))
                    if gamma8.is_file():
                        extended = list(base); extended[1] = str(gamma8)
                        run([executable] + extended)
                        extended_rows = load(output)["rows"]
                        for row in extended_rows:
                            k7, k8 = 8 - L, 9 - L
                            values = row["values"]
                            if len(values) != 2 * k8:
                                raise AssertionError("Wrong C8 regulator width")
                            row["values"] = values[:k7] + values[k8:k8 + k7]
                        compare_rows(actual, extended_rows, exact=True)
            if not gamma8.is_file():
                summary["leading_C8_jets_exact"] = None
            result.append(summary)
            print(f"Passed {sector} L{L}: {len(rows)} graphs, {summary['samples']} samples", flush=True)
    return dict(reference_source_sha256=sha256(reference / "src/c7d2_integrate.cpp"),
                full_inventory=full, points_per_graph_replicate=points,
                total_graphs=sum(r["graphs"] for r in result),
                all_L7_zero_channel_graphs_restored=True if full else None,
                groups=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, help="Unpacked original LRI_C7_D2_HPC package")
    parser.add_argument("--full", action="store_true", help="Replay every finite L3-L7 kernel, including restored L7 classes")
    parser.add_argument("--points", type=int, default=8)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--graph-list", type=Path, help="Additional physical graphs for independent 450-digit point checks")
    parser.add_argument("--sanitize", action="store_true", help="Build the point checker with ASan and UBSan")
    parser.add_argument("--backend", choices=("decimal", "both"), default="both")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.points < 2 or args.points & (args.points - 1) or args.threads < 1:
        raise ValueError("Need power-of-two points >=2 and positive threads")
    backends = ["decimal"]
    if args.backend == "both" and (ROOT / "bin/c8d2_gmp").is_file():
        backends.append("gmp")
    records = {b: load(ROOT / f"bin/c8d2_{b}.build.json") for b in backends}
    for backend in backends:
        if records[backend]["executable_sha256"] != sha256(ROOT / f"bin/c8d2_{backend}"):
            raise ValueError("Executable differs from its build record")
    build = ROOT / "build"; build.mkdir(exist_ok=True)
    result = dict(status="passed", schema="c8-d2-kernel-checks-1", sanitizer=args.sanitize,
                  build=records, point_checks={})
    if args.graph_list:
        result["point_graph_sha256"] = {line: sha256(ROOT / line) for line in args.graph_list.read_text().splitlines() if line}
    with tempfile.TemporaryDirectory(prefix="kernel-checks-", dir=build) as directory:
        temporary = Path(directory)
        for backend in backends:
            executable = temporary / f"kernel_points_{backend}"
            compile_source(ROOT / "tests/kernel_points.cpp", executable, backend, records[backend], args.sanitize)
            command = [executable] + ([args.graph_list.resolve()] if args.graph_list else [])
            result["point_checks"][backend] = json.loads(run(command))
            print(f"Passed independent point and Taylor checks: {backend}", flush=True)
        if args.reference:
            result["replay"] = replay(args.reference.resolve(), temporary, backends, records, args.full,
                                      args.points, args.threads, ROOT / "inputs/gamma_d2_8.txt")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
