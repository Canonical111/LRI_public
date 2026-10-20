#!/usr/bin/env python3
"""Pack frozen jobs without changing their samples, sums, or checkpoint schema.

Build the index ONCE (on symmetry and Expanse inside a plan job: slurm/plan.sh). Run one lane per Slurm task. A lane
reuses a verified node-local input cache and fuses consecutive point chunks
of the same graph block into one native invocation. No MPI is required.

Cluster operation (2026-10-09, docs/CLUSTERS.md):
* A lane holds a lease (<index>/lane_<n>.lease/), and every job lock holds an owner record
  (jobs/<idx>.lock/owner.json: Slurm job, step, task, host, pid, start). A lock or lease whose owner is a Slurm job
  that sacct reports finished (or a local process that no longer exists on this host) is stale and reclaimed, logged
  to jobs/reclaimed_locks.jsonl. A lock without an owner record (a crash between mkdir and the record, or a lock of
  `campaign.py run`) is never reclaimed automatically. An unknown owner state counts as live.
* With pilot statistics in the index, a bundle starts only if its estimated wall time (work / threads x
  C8_DEADLINE_FACTOR, default 1.5, plus C8_DEADLINE_PAD seconds, default 300) fits before the Slurm job's end
  (squeue %e). Without statistics, a bundle starts only while at least C8_DEADLINE_PAD seconds remain. A bundle that
  does not fit is deferred, not started.
* SIGTERM, SIGUSR1 and SIGINT stop the lane: the native child is terminated, the locks of unpublished jobs are
  released, and the lane exits 143. Published checkpoints are never touched.
* A bundle whose jobs are locked by a live owner, whose native run fails, or whose inputs keep failing their
  checksum after C8_STAGE_RETRIES re-reads (default 3) is recorded and the lane continues. The lane then exits 3 so
  the allocation is resubmitted. A corrupt published checkpoint or a changed plan, index or lane file stays fatal.
* Every lane run writes a summary to <index>/runs/.
"""
from __future__ import annotations
import argparse
from collections import OrderedDict, defaultdict
import datetime
import errno
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

from campaign import task_text, validate_native, verify_plan
from io_utils import ROOT, checked, digest, load, object_hash, save

SCHEMA = "c8-hpc-dispatch-1"
SELF = Path(__file__).resolve()


def make_index(directory: Path, destination: Path, lanes: int, bundle_jobs: int = 16,
               max_tasks: int = 65536, statistics: Path | None = None,
               target_core_seconds: float | None = None) -> dict:
    if lanes < 1 or bundle_jobs < 1 or not 1 <= max_tasks <= 100000:
        raise ValueError("Invalid lane or bundle size")
    if target_core_seconds is not None and (statistics is None or not math.isfinite(target_core_seconds) or target_core_seconds <= 0):
        raise ValueError("A positive target-core-seconds requires pilot statistics")
    if destination.exists():
        raise FileExistsError("Dispatch indices are immutable; choose a new directory")
    directory = directory.resolve()
    manifest = verify_plan(directory)
    costs = load(statistics) if statistics else None
    group_map = {g["name"]: g for g in manifest["groups"]}
    # Group only equal graph blocks: each compiled graph can serve every fused chunk.
    blocks: dict[tuple, list] = defaultdict(list)
    job_work: dict[int, float] = {}
    for entry in manifest["jobs"]:
        job = load(directory / "jobs" / f"{entry['index']:06d}.job.json")
        if object_hash(job) != entry["sha256"] or job["group"] != entry["group"]:
            raise ValueError("Job plan changed")
        if len(job["tasks"]) > max_tasks:
            raise ValueError("A frozen job exceeds --max-tasks; raise the bound (at most 100000)")
        group = group_map[job["group"]]
        work = 0.0
        for _, _, gid, start, stop, _ in job["tasks"]:
            per_point = 1.0
            if costs is not None:
                row = costs[group["sector"]][str(group["L"])][str(gid)][group["campaign"]]
                per_point = float(row["cpu_seconds"]) / int(row["points"])
                if not 0 < per_point < float("inf"):
                    raise ValueError("Invalid pilot cost")
            work += (stop-start)*per_point
        identity = job["group"], tuple(sorted({r[2] for r in job["tasks"]}))
        blocks[identity].append((entry["index"], len(job["tasks"]), work))
        job_work[entry["index"]] = work
    bundles = []
    for (group, graphs), entries in blocks.items():
        current, count, work = [], 0, 0.0
        for index, n, cost in sorted(entries):
            if current and (len(current) >= bundle_jobs or count+n > max_tasks or
                            (target_core_seconds is not None and work+cost > target_core_seconds)):
                bundles.append({"group": group, "jobs": current, "task_count": count, "work": work,
                                "job_work": [job_work[j] for j in current]})
                current, count, work = [], 0, 0.0
            current.append(index);count += n;work += cost
        if current:
            bundles.append({"group": group, "jobs": current, "task_count": count, "work": work,
                            "job_work": [job_work[j] for j in current]})
    # Longest-processing-time scheduling uses pilot timings, not graph index.
    lane_jobs: list[list] = [[] for _ in range(lanes)]
    heap = [(0.0, i) for i in range(lanes)]
    heapq.heapify(heap)
    for bundle in sorted(bundles, key=lambda b: (-b["work"], b["group"], b["jobs"][0])):
        weight, lane = heapq.heappop(heap)
        lane_jobs[lane].append(bundle)
        heapq.heappush(heap, (weight+bundle["work"], lane))
    assigned = [j for bs in lane_jobs for b in bs for j in b["jobs"]]
    if sorted(assigned) != sorted(e["index"] for e in manifest["jobs"]):
        raise AssertionError("Dispatch has missing or duplicate jobs")
    destination.mkdir(parents=True)
    files = []
    for lane, bs in enumerate(lane_jobs):
        path = destination / f"lane_{lane:06d}.json"
        save(path, {"lane": lane, "bundles": bs})
        files.append({"file": path.name, "sha256": digest(path), "work": sum(b["work"] for b in bs)})
    result = {"schema": SCHEMA, "run": str(directory), "manifest_sha256": digest(directory/"manifest.json"),
              "dispatcher_sha256": digest(SELF), "lanes": files, "jobs": len(assigned),
              "bundles": len(bundles), "bundle_jobs": bundle_jobs, "max_tasks": max_tasks,
              "target_core_seconds": target_core_seconds,
              "max_bundle_work": max(b["work"] for b in bundles),
              "cost_unit": "pilot-estimated task seconds" if costs else "integrand evaluations",
              "statistics_sha256": digest(statistics) if statistics else None,
              "scientific_tasks_modified": False}
    save(destination/"index.json", result)
    return result


class StageMismatch(ValueError):
    """A staged copy whose bytes do not hash to the planned value (after every retry)."""


class LaneStopped(Exception):
    """A stop signal arrived; the lane releases what it holds and exits 143."""


class Busy(Exception):
    """A job of the bundle is locked by a live (or not provably finished) owner."""


STOP = {"signal": None}


def _on_signal(signum, frame):
    STOP["signal"] = signum


def owner_record() -> dict:
    env = os.environ
    return {"slurm_job_id": env.get("SLURM_JOB_ID"), "slurm_step_id": env.get("SLURM_STEP_ID"),
            "slurm_procid": env.get("SLURM_PROCID"), "host": platform.node(), "pid": os.getpid(),
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "token": uuid.uuid4().hex}


def owner_token(owner: dict) -> str:
    """The acquisition's token (a record without one, written by hand or by an older dispatcher, gets a digest of its
    content, the same for every reader of that record)."""
    return str(owner.get("token") or hashlib.sha256(json.dumps(owner, sort_keys=True).encode()).hexdigest()[:32])


TERMINAL = ("BOOT_FAIL", "CANCELLED", "COMPLETED", "DEADLINE", "FAILED", "NODE_FAIL", "OUT_OF_MEMORY", "PREEMPTED",
            "TIMEOUT", "REVOKED")


def _scheduler_env() -> dict:
    return {k: v for k, v in os.environ.items()
            if k == "SLURM_CONF" or not k.startswith(("SQUEUE_", "SACCT_"))}


def slurm_job_state(job_id: str) -> str:
    """'finished', 'live' or 'unknown' for a Slurm job id. Never raises.

    'finished' needs three things. squeue lists no active or completing allocation: Slurm records a cancelled job's
    completion before its nodes are released and their processes killed, so a COMPLETING job is live. sacct shows
    only terminal states. And the job ended at least C8_RECLAIM_SETTLE seconds ago (default 300). A failed or
    inconsistent query is 'unknown'."""
    try:
        env = _scheduler_env()
        q = subprocess.run(["squeue", "-h", "-t", "all", "-j", str(job_id), "-o", "%T"], capture_output=True, text=True,
                           timeout=60, env=env)
        if q.returncode == 0:
            if any(x.strip() and x.split()[0] not in TERMINAL for x in q.stdout.splitlines()):
                return "live"                 # pending, running, completing, suspended, configuring, ...
        elif "invalid job id" not in (q.stderr or "").lower():
            return "unknown"                  # the controller did not answer
        a = subprocess.run(["sacct", "-j", str(job_id), "-X", "-n", "-P", "-o", "State,End"], capture_output=True,
                           text=True, timeout=60, env=env)
        rows = [x.split("|") for x in a.stdout.splitlines() if x.strip()] if a.returncode == 0 else []
        if not rows or any(len(r) < 2 for r in rows):
            return "unknown"
        if not all(any(r[0].split()[0].startswith(t) for t in TERMINAL) for r in rows):   # "CANCELLED by 123"
            return "live"
        settle = float(os.environ.get("C8_RECLAIM_SETTLE", "300"))
        ends = [datetime.datetime.fromisoformat(r[1]).timestamp() for r in rows]
        return "finished" if time.time() - max(ends) >= settle else "live"
    except (OSError, subprocess.SubprocessError, ValueError):
        return "unknown"


def owner_state(owner: dict | None) -> str:
    """'stale' only when the owner provably no longer runs; 'unowned' without a record; else 'live'."""
    if not owner:
        return "unowned"
    me = os.environ.get("SLURM_JOB_ID")
    job = owner.get("slurm_job_id")
    if job:
        if me and str(job) == str(me):
            return "live"   # this allocation: another lane of it, or this lane's own record; never reclaimed here
        return "stale" if slurm_job_state(job) == "finished" else "live"
    if owner.get("host") == platform.node():
        try:
            os.kill(int(owner["pid"]), 0)
        except ProcessLookupError:
            return "stale"
        except (OSError, ValueError, KeyError, TypeError):
            return "live"
        return "live"
    return "live"


def read_owner(lock: Path) -> dict | None:
    try:
        return json.loads((lock/"owner.json").read_text())
    except (OSError, ValueError):
        return None


def acquire(lock: Path, log: Path) -> str:
    """Take a lock directory and return this acquisition's token.

    mkdir is atomic on BeeGFS and Lustre. A held lock is reclaimed only when its owner provably no longer runs
    (owner_state 'stale'), and only by renaming it to <lock>.stale-<owner token>. That name is fixed by the stale
    record, so of several contenders that judged the same record stale exactly one rename succeeds. The tombstone is
    kept, never deleted: a later contender holding the same old judgement then fails its rename (the target exists)
    instead of moving the lock a newer acquisition made. It re-reads the lock and finds it live (Busy) or free. A lock
    without an owner record, or in an unknown state, is never reclaimed."""
    me = owner_record()
    for _ in range(4):
        try:
            lock.mkdir()
        except FileExistsError:
            owner = read_owner(lock)
            state = owner_state(owner)
            if state != "stale":
                raise Busy(f"{lock} is held ({state}; owner {owner})")
            tomb = lock.with_name(f"{lock.name}.stale-{owner_token(owner)}")
            try:
                os.rename(lock, tomb)
            except FileNotFoundError:
                continue                      # another contender moved it first; look again
            except OSError as exc:
                if exc.errno in (errno.EEXIST, errno.ENOTEMPTY):
                    continue                  # this record was reclaimed already; the lock is someone else's now
                raise Busy(f"{lock}: stale but not movable ({exc})") from exc
            moved = read_owner(tomb)
            if moved != owner:                # impossible under the tombstone rule; keep the evidence and stop
                raise Busy(f"{lock}: the reclaim moved an unexpected record {moved} (kept at {tomb})")
            with log.open("a") as f:
                f.write(json.dumps({"lock": str(lock), "owner": owner, "tombstone": str(tomb), "reclaimed_by": me,
                                    "rule": "owner Slurm job finished (sacct) or local pid gone"}, sort_keys=True) + "\n")
            continue
        try:
            save(lock/"owner.json", me)
        except BaseException:
            try:
                lock.rmdir()
            except OSError:
                pass
            raise
        return me["token"]
    raise Busy(f"{lock}: still contended after reclaim attempts")


def release(lock: Path, token: str) -> bool:
    """Remove the lock only if it is still this acquisition's (never another holder's)."""
    owner = read_owner(lock)
    if not owner or owner.get("token") != token:
        return False
    (lock/"owner.json").unlink(missing_ok=True)
    try:
        lock.rmdir()
    except FileNotFoundError:
        pass
    return True


UNKNOWN_END = object()   # inside a Slurm job whose end time could not be read


def job_end_epoch(attempts: int = 3):
    """The running Slurm job's end time (squeue %e, the cluster's local time) as epoch seconds; None outside Slurm
    (a local run has no deadline); UNKNOWN_END inside Slurm when the query keeps failing (bundles are then deferred,
    never started blind)."""
    job = os.environ.get("SLURM_JOB_ID")
    override = os.environ.get("C8_JOB_END_EPOCH")   # tests and debugging only
    if override:
        return float(override)
    if not job:
        return None
    for attempt in range(attempts):
        try:
            out = subprocess.run(["squeue", "-h", "-j", job, "-o", "%e"], capture_output=True, text=True, timeout=60,
                                 env=_scheduler_env())
            text = out.stdout.strip().splitlines()[0] if out.returncode == 0 and out.stdout.strip() else ""
            if text and text[0].isdigit():
                return datetime.datetime.fromisoformat(text).timestamp()
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            pass
        time.sleep(min(5 * (attempt + 1), 30) * float(os.environ.get("C8_STAGE_BACKOFF", "1")))
    return UNKNOWN_END


class StageCache:
    """Bounded file cache in private node-local storage; one hash-checked copy per miss."""
    def __init__(self, root: Path, limit: int = 128):
        if limit < 1:
            raise ValueError("Stage-cache limit must be positive")
        self.root, self.limit = root, limit
        self.items: OrderedDict[str, tuple[Path, str]] = OrderedDict()
        self.bytes_read = 0
        self.hits = 0
        self.retries = 0

    def stage(self, source: Path, relative: str, expected: str) -> Path:
        rel_path = Path(relative)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise ValueError("Stage-cache paths must be relative and remain inside scratch")
        target = self.root / rel_path
        if relative in self.items:
            _, old = self.items.pop(relative)
            if old != expected:
                raise ValueError("Attempt to reuse a staged path with a different hash")
            self.items[relative] = (target, expected)
            self.hits += 1
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        attempts = max(1, int(os.environ.get("C8_STAGE_RETRIES", "3")))
        for attempt in range(1, attempts+1):
            h = hashlib.sha256()
            try:
                with source.open("rb") as src, target.open("xb") as dst:
                    for chunk in iter(lambda: src.read(1 << 20), b""):
                        h.update(chunk);dst.write(chunk);self.bytes_read += len(chunk)
                if h.hexdigest() != expected:
                    raise StageMismatch(f"Input checksum changed: {source}")
            except StageMismatch:
                # A transient bad read of a shared filesystem (seen on Expanse Lustre) is retried from the source;
                # a mismatch on every attempt is a changed input.
                target.unlink(missing_ok=True)
                self.retries += attempt < attempts
                if attempt == attempts:
                    raise
                time.sleep(min(2**attempt, 30) * float(os.environ.get("C8_STAGE_BACKOFF", "1")))
                continue
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            break
        self.items[relative] = (target, expected)
        return target

    def trim(self):
        # Evict BETWEEN bundles, never while a native process is using a file.
        while len(self.items) > self.limit:
            _, (path, _) = self.items.popitem(last=False)
            path.unlink(missing_ok=True)


def check_done(directory: Path, entry: dict, job: dict, group: dict, manifest_hash: str) -> bool:
    base = directory/"jobs"/f"{entry['index']:06d}"
    receipt_path = base.with_suffix(".done.json")
    if not receipt_path.exists():
        return False
    receipt = load(receipt_path)
    if receipt["job_sha256"] != entry["sha256"] or receipt["manifest_sha256"] != manifest_hash:
        raise ValueError("Checkpoint provenance mismatch")
    output = base.with_suffix(".native.json")
    checked(output, receipt["native_sha256"])
    validate_native(load(output), job, group)
    return True


def run_native(command: list, env: dict, log_path: Path) -> None:
    """Run the native worker; poll for a stop signal and terminate it (then kill after 20 s) when one arrives."""
    with log_path.open("w") as log:
        child = subprocess.Popen(command, stdout=log, stderr=log, env=env)
        try:
            while True:
                try:
                    rc = child.wait(timeout=1.0)
                    break
                except subprocess.TimeoutExpired:
                    if STOP["signal"] is not None:
                        child.terminate()
                        try:
                            child.wait(timeout=20)
                        except subprocess.TimeoutExpired:
                            child.kill();child.wait()
                        raise LaneStopped(f"signal {STOP['signal']} during a native run")
        except BaseException:
            if child.poll() is None:
                child.kill();child.wait()
            raise
    if rc != 0:
        raise subprocess.CalledProcessError(rc, command)


def pending_jobs(directory: Path, bundle: dict, group: dict, manifest_hash: str, entries: dict) -> list:
    """The bundle's jobs without a valid receipt, as (entry, job). A corrupt receipt or output is fatal (ValueError)."""
    pending = []
    for index in bundle["jobs"]:
        entry = entries[index]
        job = load(directory/"jobs"/f"{index:06d}.job.json")
        if object_hash(job) != entry["sha256"] or job["group"] != group["name"] or job["L"] != group["L"]:
            raise ValueError("Job plan changed or bundle mixes sampling groups")
        if not check_done(directory, entry, job, group, manifest_hash):
            pending.append((entry, job))
    return pending


def run_bundle(directory: Path, manifest: dict, bundle: dict, cache: StageCache,
               threads: int, manifest_hash: str, group_map: dict, entries: dict, pending: list | None = None) -> dict:
    group = group_map[bundle["group"]]
    if pending is None:
        pending = pending_jobs(directory, bundle, group, manifest_hash, entries)
    if not pending:
        return {"jobs": 0, "native_invocations": 0}
    held = []   # (lock, token)
    try:
        for entry, job in pending:
            lock = directory/"jobs"/f"{entry['index']:06d}.lock"
            held.append((lock, acquire(lock, directory/"jobs"/"reclaimed_locks.jsonl")))  # Busy when a live owner holds it
        # A checkpoint published between the done check and the lock (by a finished owner) is not redone.
        still = []
        for entry, job in pending:
            if check_done(directory, entry, job, group, manifest_hash):
                lock = directory/"jobs"/f"{entry['index']:06d}.lock"
                for pair in [x for x in held if x[0] == lock]:
                    release(*pair);held.remove(pair)
            else:
                still.append((entry, job))
        pending = still
        if not pending:
            return {"jobs": 0, "native_invocations": 0}
        remapped, ranges = [], []
        for entry, job in pending:
            first = len(remapped)
            remapped.extend([[first+i, *row[1:]] for i, row in enumerate(job["tasks"])])
            ranges.append((first, len(remapped)))
        if len(remapped) > 100000:
            raise ValueError("Native task bound exceeded")
        for gid in sorted({r[2] for r in remapped}):
            rel = f"{group['sector']}/L{group['L']}/G{gid}.txt"
            cache.stage(ROOT/"inputs"/rel, "inputs/"+rel, manifest["graph_hashes"][rel])
        gamma = cache.stage(ROOT/"inputs/gamma_d3_8.txt", "gamma.txt", manifest["inputs"]["gamma_d3_8.txt"])
        net = cache.stage(directory/"groups"/group["name"]/"sobol.bin", "nets/"+group["name"]+".bin", group["net"]["sha256"])
        task_path, output = cache.root/"bundle.tasks", cache.root/"bundle.native.json"
        output.unlink(missing_ok=True)
        task_path.write_text(task_text(group["L"], remapped))
        command = [manifest["executable"]["path"], str(cache.root/"inputs"/group["sector"]),
                   str(gamma), str(net), str(task_path), str(output), str(group["seeds"]["shift"]),
                   "0", str(group["rate"]), str(threads), "compensated", "-"]
        env = dict(os.environ)
        env.setdefault("OMP_PROC_BIND", "close")
        env.setdefault("OMP_PLACES", "cores")
        env["OPENBLAS_NUM_THREADS"] = "1"
        started = time.monotonic()
        try:
            run_native(command, env, cache.root/"bundle.log")
        except subprocess.CalledProcessError as exc:
            failure = directory/"jobs"/f"dispatch-failed-{pending[0][0]['index']:06d}-{os.getpid()}.log"
            shutil.copyfile(cache.root/"bundle.log", failure)
            raise RuntimeError(f"Native bundle failed; log retained at {failure}") from exc
        elapsed = time.monotonic()-started
        data = load(output)
        validate_native(data, {"L": group["L"], "tasks": remapped}, group)
        if data["mp_backend"] != manifest["executable"]["description"]["mp_backend"]:
            raise ValueError("Numerical backend changed")
        published, skipped = 0, []
        for (entry, job), (begin, end) in zip(pending, ranges):
            restored = []
            for row, original in zip(data["rows"][begin:end], job["tasks"]):
                row = dict(row);row["uid"] = original[0];restored.append(row)
            part = {k: v for k, v in data.items() if k != "rows"}
            part.update(rows=restored, dispatch_bundle={"jobs": [e["index"] for e, _ in pending],
                         "shared_invocation_seconds": elapsed, "row_order_and_sums_preserved": True})
            validate_native(part, job, group)
            base = directory/"jobs"/f"{entry['index']:06d}"
            lock = directory/"jobs"/f"{entry['index']:06d}.lock"
            token = next(t for l, t in held if l == lock)
            if (read_owner(lock) or {}).get("token") != token:
                raise RuntimeError(f"{lock} is no longer this lane's ({token}); job {entry['index']} not published")
            if base.with_suffix(".done.json").exists():
                # Defence in depth: the lock excludes a second publisher, but a receipted output is never replaced.
                skipped.append(entry["index"]);continue
            # Existing unreceipted outputs can be left by a publication crash.
            # This rerun revalidates and atomically replaces only that unfinished output.
            save(base.with_suffix(".native.json"), part, replace=True)
            save(base.with_suffix(".done.json"), {"index": entry["index"], "job_sha256": entry["sha256"],
                 "manifest_sha256": manifest_hash, "native_sha256": digest(base.with_suffix(".native.json")),
                 "seconds": elapsed, "seconds_scope": "shared bundle wall time, not per-job CPU time",
                 "node": platform.node(), "threads": threads, "dispatcher_sha256": digest(SELF),
                 "slurm_job_id": os.environ.get("SLURM_JOB_ID")})
            published += 1
        cache.trim()
        return {"jobs": published, "native_invocations": 1, "seconds": elapsed, "skipped_receipted": skipped,
                "load_seconds": data["load_seconds"], "integration_seconds": data["integration_seconds"]}
    finally:
        for lock, token in reversed(held):
            release(lock, token)


def bundle_fits(bundle: dict, pending: list, index: dict, threads: int, end: float | None) -> tuple[bool, float | None]:
    """Whether the bundle's unfinished jobs may start before the lane must stop, and their estimated wall seconds
    (None without statistics). The lane must stop C8OPT_GRACE seconds before the job's end (submit.py sends TERM
    then) and leave C8_DEADLINE_PAD seconds for publication and cleanup."""
    pad = float(os.environ.get("C8_DEADLINE_PAD", "300"))
    grace = float(os.environ.get("C8OPT_GRACE", "0"))
    estimate = None
    if index.get("statistics_sha256"):
        work = dict(zip(bundle["jobs"], bundle.get("job_work") or []))
        if len(work) == len(bundle["jobs"]):
            todo = sum(work[e["index"]] for e, _ in pending)
        else:   # an index without per-job work: the bundle's work by the share of pending tasks
            todo = bundle["work"] * sum(len(j["tasks"]) for _, j in pending) / max(bundle["task_count"], 1)
        estimate = todo / max(threads, 1) * float(os.environ.get("C8_DEADLINE_FACTOR", "1.5")) + pad
    if end is None:
        return True, estimate
    if end is UNKNOWN_END:
        return False, estimate                # a Slurm job whose deadline cannot be read starts nothing
    remaining = end - grace - time.time()
    return (remaining >= (estimate if estimate is not None else pad)), estimate


def run_lane(index_directory: Path, lane: int, threads: int, scratch: Path | None,
             cache_graphs: int = 128) -> dict:
    index = load(index_directory/"index.json")
    if index["schema"] != SCHEMA or index["dispatcher_sha256"] != digest(SELF):
        raise ValueError("Dispatch schema or dispatcher changed")
    if not 0 <= lane < len(index["lanes"]) or threads < 1:
        raise ValueError("Invalid lane or thread count")
    directory = Path(index["run"])
    checked(directory/"manifest.json", index["manifest_sha256"])
    manifest = verify_plan(directory)
    record = index["lanes"][lane]
    path = index_directory/record["file"]
    checked(path, record["sha256"])
    work = load(path)
    if work["lane"] != lane:
        raise ValueError("Lane identity mismatch")
    groups = {g["name"]: g for g in manifest["groups"]}
    entries = {e["index"]: e for e in manifest["jobs"]}
    STOP["signal"] = None
    previous = {sig: signal.signal(sig, _on_signal) for sig in (signal.SIGTERM, signal.SIGUSR1, signal.SIGINT)}
    lease = index_directory/f"lane_{lane:06d}.lease"
    lease_token = None
    end = job_end_epoch()
    reports, outcomes = [], {"completed": 0, "deferred": [], "busy": [], "failed": []}
    stopped = None
    started = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    try:
        lease_token = acquire(lease, index_directory/"reclaimed_leases.jsonl")   # Busy: the lane runs in a live allocation
        if scratch:
            scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"c8_lane_{lane}_", dir=scratch) as tmp:
            cache = StageCache(Path(tmp), cache_graphs+26)
            for number, bundle in enumerate(work["bundles"]):
                if STOP["signal"] is not None:
                    stopped = STOP["signal"];break
                tag = {"bundle": number, "group": bundle["group"], "jobs": bundle["jobs"]}
                pending = pending_jobs(directory, bundle, groups[bundle["group"]], index["manifest_sha256"], entries)
                if not pending:
                    continue                  # fully receipted: complete whatever the deadline
                if end is UNKNOWN_END:
                    end = job_end_epoch()     # refresh: a transient scheduler failure must not cost the whole lane
                fits, estimate = bundle_fits(bundle, pending, index, threads, end)
                if not fits:
                    outcomes["deferred"].append({**tag, "pending": [e["index"] for e, _ in pending], "estimate_seconds": estimate})
                    continue
                try:
                    report = run_bundle(directory, manifest, bundle, cache, threads, index["manifest_sha256"], groups,
                                        entries, pending)
                except LaneStopped:
                    stopped = STOP["signal"];break
                except Busy as exc:
                    outcomes["busy"].append({**tag, "why": str(exc)});continue
                except (RuntimeError, StageMismatch) as exc:
                    outcomes["failed"].append({**tag, "why": str(exc)});continue
                reports.append(report)
                outcomes["completed"] += report["jobs"]
                print(json.dumps({"lane": lane, **report}), flush=True)
            result = {"lane": lane, "jobs_completed": sum(r["jobs"] for r in reports),
                      "native_invocations": sum(r["native_invocations"] for r in reports),
                      "source_bytes_read": cache.bytes_read, "stage_cache_hits": cache.hits,
                      "stage_retries": cache.retries, "deferred": outcomes["deferred"], "busy": outcomes["busy"],
                      "failed": outcomes["failed"], "stopped_by_signal": stopped,
                      "slurm_job_id": os.environ.get("SLURM_JOB_ID"), "host": platform.node(), "threads": threads,
                      "job_end_epoch": "unknown" if end is UNKNOWN_END else end}
    finally:
        if lease_token:
            release(lease, lease_token)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    result["complete"] = not (result["deferred"] or result["busy"] or result["failed"] or stopped)
    # The log line first: after a stop signal Slurm may kill the task before a slow shared-filesystem write ends.
    print(json.dumps(result), flush=True)
    save(index_directory/"runs"/f"lane_{lane:06d}_{os.environ.get('SLURM_JOB_ID', 'local')}_{started}_{os.getpid()}_{time.monotonic_ns()}.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("index")
    p.add_argument("run", type=Path);p.add_argument("destination", type=Path)
    p.add_argument("--lanes", type=int, required=True)
    p.add_argument("--bundle-jobs", type=int, default=16)
    p.add_argument("--max-tasks", type=int, default=65536)
    p.add_argument("--statistics", type=Path)
    p.add_argument("--target-core-seconds", type=float, help="Soft bundle cost bound; requires --statistics")
    p = sub.add_parser("run")
    p.add_argument("index", type=Path)
    p.add_argument("--lane", type=int, required=True)
    p.add_argument("--threads", type=int, default=int(os.getenv("SLURM_CPUS_PER_TASK", "1")))
    p.add_argument("--scratch", type=Path, default=Path(os.environ["TMPDIR"]) if "TMPDIR" in os.environ else None)
    p.add_argument("--cache-graphs", type=int, default=128)
    a = parser.parse_args()
    if a.command == "index":
        r = make_index(a.run, a.destination, a.lanes, a.bundle_jobs, a.max_tasks, a.statistics, a.target_core_seconds)
        print(json.dumps({k: r[k] for k in ("jobs", "bundles", "cost_unit")}, indent=2))
        return 0
    try:
        r = run_lane(a.index, a.lane, a.threads, a.scratch, a.cache_graphs)
    except Busy as exc:
        print(json.dumps({"lane": a.lane, "error": "lane busy", "why": str(exc)}), flush=True)
        return 75
    if r["stopped_by_signal"] is not None:
        return 143
    return 0 if r["complete"] else 3

if __name__ == "__main__":
    raise SystemExit(main())
