#!/usr/bin/env python3
"""Restartable local or Slurm-array C8(3) integration.

A plan freezes all graph identities, input hashes, counts, seeds and tasks.
Array elements write disjoint checkpoint files. Rechunking a complete net does
not create new statistical replicates. No cluster operation is submitted here.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

from io_utils import ROOT, checked, digest, load, object_hash, power_of_two, save
from sobol_net import make_net

SCHEMA = "lri-c8-d3-campaign-1"
SECTORS = ("free", "power")
LOOPS = tuple(range(3, 9))


def derive_seed(seed, campaign, sector, loop, role):
    identity = f"lri-c8-d3|{seed}|{campaign}|{sector}|{loop}|{role}"
    return int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], "little") % 2**63


def plan(args):
    directory = args.directory.resolve()
    if directory.exists():
        raise FileExistsError("Use a new campaign directory; existing plans are immutable")
    if not power_of_two(args.points) or not power_of_two(args.chunk_points):
        raise ValueError("Points and chunk-points must be positive powers of two")
    if args.replicates < 4 or args.replicates % 2:
        raise ValueError("Use an even number of at least four randomized replicates")
    if args.threads < 1 or args.graph_block < 1 or not 0 <= args.seed < 2**63:
        raise ValueError("Invalid execution sizes or seed")
    if args.purpose == "production" and (args.points < 4096 or args.replicates < 16):
        raise ValueError("Production requires at least 4096 points and 16 replicates; smaller runs are pilots")
    loops = tuple(sorted(set(args.loops)))
    if not set(loops).issubset(LOOPS) or not loops:
        raise ValueError("Loops must lie in 3..8")
    inventory = load(ROOT / "inputs/inventory.json")
    allocation = load(args.allocation) if args.allocation else None
    executable = (args.executable or ROOT / "bin/c8d3_gmp").resolve()
    description = json.loads(subprocess.check_output([str(executable), "--describe"], text=True))
    if description.get("dimension") != 3 or description.get("order") != 8:
        raise ValueError("Worker does not describe an order-eight, dimension-three build")
    if description.get("mp_backend") != "gmp350" and args.purpose == "production":
        raise ValueError("The production arithmetic contract requires the GMP350 backend")
    input_hashes = {
        name: digest(ROOT / "inputs" / name)
        for name in ("inventory.json", "gamma_d3_8.txt", "two_loop.json")
    }
    coverage = ROOT / "inputs/coverage.json"
    coverage_record = load(coverage) if coverage.exists() else {}
    coverage_verified = (
        coverage_record.get("complete") is True
        and coverage_record.get("inventory_sha256") == input_hashes["inventory.json"]
    )
    if args.purpose == "production" and not coverage_verified:
        raise ValueError("Complete independently checked graph coverage is required before production")
    if coverage.exists():
        input_hashes["coverage.json"] = digest(coverage)
    graph_hashes = {}
    selected = {}
    for sector in SECTORS:
        for loop in loops:
            records = inventory[sector][str(loop)]
            if not records:
                raise ValueError(f"Empty graph stratum: {sector} L{loop}")
            ids = [int(row["id"]) for row in records]
            if len(set(ids)) != len(ids):
                raise ValueError("Duplicate graph identity in inventory")
            rows = []
            for row in sorted(records, key=lambda r: r["id"]):
                identity = f"{sector}/L{loop}/G{row['id']}.txt"
                path = ROOT / "inputs" / identity
                actual = digest(path)
                if row.get("sha256") and actual != row["sha256"]:
                    raise ValueError(f"Graph payload changed: {identity}")
                graph_hashes[identity] = actual
                points = args.points if allocation is None else int(allocation[sector][str(loop)][str(row["id"])])
                if not power_of_two(points):
                    raise ValueError("Every active graph needs a positive complete Sobol net")
                if args.purpose == "production" and points < 4096:
                    raise ValueError("Every production graph requires at least 4096 points")
                rows.append({"id": int(row["id"]), "points": points})
            selected[f"{sector}_L{loop}"] = rows
    directory.mkdir(parents=True)
    (directory / "groups").mkdir()
    (directory / "jobs").mkdir()
    groups = []
    jobs = []
    for tag, rate, bits in (("a", 0.8, 52), ("b", 0.7, 60)):
        for sector in SECTORS:
            for loop in loops:
                name = f"{tag}_{sector}_L{loop}"
                group_path = directory / "groups" / name
                group_path.mkdir()
                seeds = {
                    role: derive_seed(args.seed, tag, sector, loop, role)
                    for role in ("net", "shift")
                }
                net = make_net(group_path / "sobol.bin", args.replicates, 4 * loop - 1, bits, seeds["net"])
                rows = selected[f"{sector}_L{loop}"]
                group = {
                    "name": name, "campaign": tag, "sector": sector, "L": loop,
                    "rate": rate, "bits": bits, "seeds": seeds, "net": net,
                    "graphs": rows,
                }
                groups.append(group)
                # One checkpoint contains a bounded graph block and one point interval.
                for offset in range(0, len(rows), args.graph_block):
                    block = rows[offset:offset + args.graph_block]
                    for begin in range(0, max(x["points"] for x in block), args.chunk_points):
                        tasks = []
                        for rep in range(args.replicates):
                            for row in block:
                                total = row["points"]
                                if begin < total:
                                    tasks.append([len(tasks), rep, row["id"], begin, min(begin + args.chunk_points, total), total])
                        if not tasks:
                            continue
                        if len(tasks) > 100000:
                            raise ValueError("Graph block exceeds native task limit")
                        index = len(jobs)
                        job = {"index": index, "group": name, "L": loop, "tasks": tasks}
                        save(directory / "jobs" / f"{index:06d}.job.json", job)
                        jobs.append({"index": index, "group": name, "sha256": object_hash(job)})
    manifest = {
        "schema": SCHEMA, "dimension": 3, "order": 8, "epsilon": "2s-3",
        "purpose": args.purpose, "base_seed": args.seed, "replicates": args.replicates,
        "threads": args.threads, "graph_block": args.graph_block,
        "chunk_points": args.chunk_points, "loops": list(loops),
        "coverage_verified": coverage_verified, "all_loops": loops == LOOPS,
        "campaign_weights": {"a": 0.5, "b": 0.5},
        "inputs": input_hashes, "graph_hashes": graph_hashes,
        "executable": {"path": str(executable), "sha256": digest(executable), "description": description},
        "tools": {name: digest(ROOT / "tools" / name) for name in ("campaign.py", "sobol_net.py", "io_utils.py")},
        "groups": groups, "jobs": jobs,
        "evaluations": 2 * args.replicates * sum(row["points"] for rows in selected.values() for row in rows),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": platform.platform(),
        "statistical_unit": "Complete graph-summed randomized replicate within one loop/sector/campaign",
        "allocation_source": {"path": str(args.allocation), "sha256": digest(args.allocation)} if args.allocation else None,
    }
    save(directory / "manifest.json", manifest)
    print(json.dumps({"jobs": len(jobs), "evaluations": manifest["evaluations"], "purpose": args.purpose, "coverage_verified": coverage_verified}))


def verify_plan(directory):
    manifest = load(directory / "manifest.json")
    if manifest.get("schema") != SCHEMA or manifest["campaign_weights"] != {"a": 0.5, "b": 0.5}:
        raise ValueError("Invalid campaign manifest")
    for name, expected in manifest["inputs"].items():
        checked(ROOT / "inputs" / name, expected)
    for name, expected in manifest["tools"].items():
        checked(ROOT / "tools" / name, expected)
    checked(manifest["executable"]["path"], manifest["executable"]["sha256"])
    return manifest


def task_text(loop, tasks):
    return f"C8D3TASKS1 {loop} {len(tasks)}\n" + "".join(" ".join(map(str, row)) + "\n" for row in tasks)


def validate_native(data, job, group):
    if data.get("schema") != "c8-d3-hpc-native-1" or data.get("L") != job["L"]:
        raise ValueError("Native output order/schema mismatch")
    if data.get("seed") != group["seeds"]["shift"] or data.get("bits") != group["bits"] or data.get("layout") != 0 or data.get("sum_mode") != "compensated":
        raise ValueError("Native sampling configuration mismatch")
    if abs(float(data["rate"]) - group["rate"]) > 1e-15:
        raise ValueError("Native importance rate mismatch")
    expected = [tuple(row) for row in job["tasks"]]
    actual = [tuple(row[k] for k in ("uid", "rep", "graph", "begin", "end", "total")) for row in data["rows"]]
    if actual != expected:
        raise ValueError("Native graph/replicate/point coverage mismatch")
    import decimal
    for row in data["rows"]:
        if len(row["values"]) != 2 * (9 - job["L"]) or not all(decimal.Decimal(x).is_finite() for x in row["values"]):
            raise ValueError("Invalid Taylor-jet width or nonfinite value")


def run_job(directory, index, threads=None, manifest=None):
    manifest = manifest or verify_plan(directory)
    if not 0 <= index < len(manifest["jobs"]):
        raise ValueError("Job index outside plan")
    entry = manifest["jobs"][index]
    base = directory / "jobs" / f"{index:06d}"
    job = load(base.with_suffix(".job.json"))
    if object_hash(job) != entry["sha256"]:
        raise ValueError("Job plan changed")
    group = next(g for g in manifest["groups"] if g["name"] == job["group"])
    final = base.with_suffix(".done.json")
    output = base.with_suffix(".native.json")
    if final.exists():
        receipt = load(final)
        if receipt["job_sha256"] != entry["sha256"] or receipt["manifest_sha256"] != digest(directory / "manifest.json"):
            raise ValueError("Checkpoint provenance mismatch")
        checked(output, receipt["native_sha256"])
        validate_native(load(output), job, group)
        return False
    lock = base.with_suffix(".lock")
    lock.mkdir()  # A crashed lock must be inspected, never silently stolen.
    try:
        if final.exists():
            # Another writer (tools/hpc_dispatch.py) published this job between the check above and the lock:
            # validate its receipt and never replace a receipted output.
            receipt = load(final)
            if receipt["job_sha256"] != entry["sha256"] or receipt["manifest_sha256"] != digest(directory / "manifest.json"):
                raise ValueError("Checkpoint provenance mismatch")
            checked(output, receipt["native_sha256"])
            validate_native(load(output), job, group)
            return False
        for graph in sorted({row[2] for row in job["tasks"]}):
            identity = f"{group['sector']}/L{job['L']}/G{graph}.txt"
            checked(ROOT / "inputs" / identity, manifest["graph_hashes"][identity])
        net = directory / "groups" / group["name"] / "sobol.bin"
        checked(net, group["net"]["sha256"])
        tasks = base.with_suffix(".tasks")
        tasks.write_text(task_text(job["L"], job["tasks"]))
        temporary = base.with_suffix(f".native.tmp-{os.getpid()}")
        command = [
            manifest["executable"]["path"], str(ROOT / "inputs" / group["sector"]),
            str(ROOT / "inputs/gamma_d3_8.txt"), str(net), str(tasks), str(temporary),
            str(group["seeds"]["shift"]), "0", str(group["rate"]),
            str(threads or manifest["threads"]), "compensated", "-",
        ]
        started = time.monotonic()
        with base.with_suffix(".log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=log, check=True, env={**os.environ, "OMP_PROC_BIND": "false"})
        data = load(temporary)
        validate_native(data, job, group)
        if data.get("mp_backend") != manifest["executable"]["description"]["mp_backend"]:
            raise ValueError("Native multiprecision backend changed")
        os.replace(temporary, output)
        save(final, {
            "index": index, "job_sha256": entry["sha256"],
            "manifest_sha256": digest(directory / "manifest.json"),
            "native_sha256": digest(output), "seconds": time.monotonic() - started,
            "node": platform.node(), "threads": threads or manifest["threads"],
        })
    finally:
        lock.rmdir()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("plan")
    p.add_argument("directory", type=Path)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--purpose", choices=("pilot", "production"), default="pilot")
    p.add_argument("--points", type=int, default=256)
    p.add_argument("--replicates", type=int, default=8)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--graph-block", type=int, default=8)
    p.add_argument("--chunk-points", type=int, default=65536)
    p.add_argument("--loops", nargs="+", type=int, default=list(LOOPS))
    p.add_argument("--allocation", type=Path)
    p.add_argument("--executable", type=Path)
    for name in ("run", "status"):
        p = commands.add_parser(name)
        p.add_argument("directory", type=Path)
        if name == "run":
            p.add_argument("--job", type=int)
            p.add_argument("--threads", type=int)
            p.add_argument("--workers", type=int, default=1,
                           help="Independent local native processes; total cores are workers times threads")
    args = parser.parse_args()
    if args.command == "plan":
        plan(args)
    elif args.command == "status":
        m = load(args.directory / "manifest.json")
        done = sum((args.directory / "jobs" / f"{j['index']:06d}.done.json").exists() for j in m["jobs"])
        print(json.dumps({"completed": done, "planned": len(m["jobs"]), "purpose": m["purpose"], "evaluations": m["evaluations"]}))
    else:
        directory = args.directory.resolve()
        manifest = verify_plan(directory)
        indices = [args.job] if args.job is not None else range(len(manifest["jobs"]))
        if args.workers < 1 or (args.threads is not None and args.threads < 1):
            raise ValueError("Workers and threads must be positive")
        if args.workers == 1:
            for index in indices:
                fresh = run_job(directory, index, args.threads, manifest)
                if fresh:
                    print(f"Completed job {index + 1}/{len(manifest['jobs'])}", flush=True)
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {pool.submit(run_job, directory, index, args.threads, manifest): index for index in indices}
                for future in as_completed(futures):
                    if future.result():
                        print(f"Completed job {futures[future] + 1}/{len(manifest['jobs'])}", flush=True)


if __name__ == "__main__":
    main()
