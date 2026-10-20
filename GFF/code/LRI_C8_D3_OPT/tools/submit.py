#!/usr/bin/env python3
"""Submit the independent C8(3) package's jobs on symmetry or Expanse, with the site rules applied (docs/CLUSTERS.md).

  submit.py build    [--partition P] [--time T] [--mem M] [--any-cpu] [--dry-run]
  submit.py plan     RUN DISPATCH --seed S --lanes N [--plan-args "..."] [--index-args "..."] [--time T] [--dry-run]
  submit.py lanes    DISPATCH --nodes N --time T [--lanes-per-node K] [--grace SECONDS] [--partition P] [--dry-run]
  submit.py assemble RUN [--dependency afterok:ID] [--time T] [--mem M] [--dry-run]
  submit.py ledger
  submit.py resolve TOKEN --rejected --reason "what was checked"

Run it on a login node after sourcing the site env file (~/c8opt/env.sh, from slurm/sites/<site>/env.sh.example).

Every job gets:
- a partition from the site's allow-list (longq, preq and amdpreq are refused);
- --time (positive, rounded up to whole minutes, within the partition's limit), --mem and --no-requeue;
- the site's node exclusions: symmetry cn112, an Intel node in amdq; Expanse exp-1-38 and exp-1-44, whose Lustre
  reads corrupted copies;
- the Expanse account yun124;
- an output file in $C8OPT_ROOT/logs/;
- a unique name c8opt-<role>-<identity>-<token>, where <identity> is the sanitized basename of the target directory
  plus 8 hex digits of its resolved path.
sbatch runs with every SBATCH_*, SALLOC_*, SRUN_* and SLURM_* variable removed except SLURM_CONF (Expanse needs it),
so an inherited variable cannot add an array, change resources or change the cluster. Every option is passed
explicitly.

Lanes take whole nodes. symmetry has 64 cores, as 8 lanes x 8 threads; Expanse has 128, as 16 x 8 (--lanes-per-node
changes the split). The dispatch's lane count must equal nodes x lanes per node. A lane job gets --signal=TERM@<grace>
(default 600 s) and C8OPT_GRACE: its lanes start a bundle only if it can finish before the signal, then stop and
release their locks (tools/hpc_dispatch.py). A second lane job for a dispatch whose lane job is queued or running is
refused.

Admission runs under the session lock that the c8d3 package's submitter also takes: symmetry
/home/zzheng1/c8d3/locks/c8d3.lock (NFS, flock seen by every node); Expanse
$C8D3_ROOT/locks/c8d3.lock (Lustre, mounted with flock). C8OPT_SESSION_LOCK overrides this for tests. It exits 65
over a cap or the class rule, 64 for a malformed request or an unset cap, 69 when the queue cannot be read, and 75
when the lock is busy. Lanes run only on the integration partitions: symmetry amdq / amddebugq (EPYC 7543; cn112 and
the known EPYC 7532 nodes excluded, plus C8OPT_AMD_EXCLUDE_EXTRA), Expanse compute.

One package per site and class. The c8d3 submitter does not count c8opt- jobs (on Expanse it refuses normal
admissions while any foreign job of the user is live). So c8opt admits nothing while a c8d3- job of the same class is
live (queued, running, suspended or completing), or while an unresolved c8d3 submission (a file in $C8D3_ROOT/intents/)
names a partition of that class. The classes are symmetry's AMD pool (amdq, amddebugq, amdpreq), and Expanse's compute
(normal QOS) and shared. Conversely, c8d3 must not be submitted in a class while c8opt jobs of it are live (symmetry's
AMD pool, Expanse's shared partition): this is a procedure, because the pinned c8d3 tools cannot see them
(docs/CLUSTERS.md). Within that rule:
- symmetry AMD pool, nodes: c8opt + new <= C8OPT_AMD_CAP, and c8d3 + c8opt + new <= C8OPT_SESSION_AMD_CAP (the
  session's DECISIONS share, H7 / H11);
- Expanse compute (normal QOS, H7E-R):
  - c8opt + 1 <= C8OPT_RUN_CAP and C8OPT_SUB_CAP; session caps 11 / 27;
  - the user's running normal jobs (every session) plus c8opt's queued ones + 1 <= 22; all queued or running + 1 <= 54;
  - the yun124 account's running normal jobs (other users included) plus this user's queued ones + 1 <= 32;
  - compute nodes: own C8OPT_COMPUTE_NODE_CAP, session 4 in development (H7E);
- Expanse shared: c8opt + 1 <= C8OPT_SHARED_CAP, session 32 live;
- both sites, node-hour budget: the reserved node-hours of every unrejected submission in $C8OPT_ROOT/ledger.jsonl plus
  the new one <= C8OPT_NODE_HOURS_CAP, the approved budget of this package.
  - Reserved means nodes x time limit. A shared Expanse job counts the larger of its core and memory fraction of a
    257,400 MB, 128-core node, as Expanse bills shared jobs.
  - It is a bound on reservations; nothing is refunded.
The queue is read with one row per array element, and a queued job counts as if running.

Durability. Before sbatch, an intent line (unique token, resources, node-hours, seed) is appended to ledger.jsonl and
fsynced, and a plan's seed is appended to seeds.jsonl, where it stays reserved for good. After a successful sbatch comes
an accepted line. An intent without one (a crash, or a failed sbatch) stays reserved, counting against node-hours and,
as a queued job, against every cap and the duplicate-lane check. It is accepted when squeue or sacct shows its
unique name. It is rejected only by `submit.py resolve TOKEN --rejected --reason "..."`, an operator's recorded
decision, which is refused while squeue or sacct still knows that name. Elapsed time alone never releases a
reservation.

Seeds (plan): a seed is refused if it is
- in $C8OPT_ROOT/seeds.jsonl;
- the delivered pilot's;
- one of the documentation's examples;
- in any JSON seed log named by C8OPT_FOREIGN_SEED_LOGS (colon-separated, e.g. the c8d3 package's forbidden_seeds.json).

Plan and index options are allow-listed: --seed, --executable, the destinations and --lanes come only from
submit.py. The effective argument vectors are recorded.
"""
from __future__ import annotations
import argparse
import calendar
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_SEEDS = {6129871430538291, 5744183710640629, 680432977503981207}
SITES = {
    "symmetry": {
        "allowed": {"amdq", "amddebugq", "defq", "debugq"}, "forbidden": {"longq", "preq", "amdpreq"},
        "amd_pool": {"amdq", "amddebugq", "amdpreq"}, "account": None,
        "cores": {"amdq": 64, "amddebugq": 64, "defq": 80, "debugq": 80},   # Slurm CPUs per node (sinfo %c, 2026-10-09)
        "mem": {"amdq": "240G", "amddebugq": "240G", "defq": "180G", "debugq": "180G"},   # nodes: 256000 / 191488 MB
        "max_minutes": {"amdq": 1440, "amddebugq": 60, "defq": 1440, "debugq": 60},
        # cn112 is Intel (AVX-512); the others are AMD EPYC 7532, not the integration CPU 7543 (the c8d3 package's
        # recorded list, LRI_C8_D3_HPC/tools/budget.py cpu_exclude). C8OPT_AMD_EXCLUDE_EXTRA adds nodes found later.
        "exclude": {p: "cn112,cn079,cn080,cn081,cn082,cn084,cn085,cn087,cn092" for p in ("amdq", "amddebugq")},
        "whole_node": {"amdq", "amddebugq", "defq", "debugq"},
        "defaults": {"lanes": "amdq", "build": "amdq", "plan": "defq", "assemble": "defq"}, "lanes_per_node": 8,
        "lanes_partitions": {"amdq", "amddebugq"},   # the integration CPU (EPYC 7543); Intel defq/debugq never run lanes
        "lock": "/home/zzheng1/c8d3/locks/c8d3.lock", "c8d3_root": "/mnt/beegfs/zzheng1/c8d3",
    },
    "expanse": {
        "allowed": {"compute", "shared", "debug"}, "forbidden": set(), "amd_pool": set(), "account": "yun124",
        "cores": {"compute": 128, "shared": 128, "debug": 128}, "node_mem_mb": 257400,
        "mem": {"compute": "240G", "debug": "240G"},
        "max_minutes": {"compute": 2880, "shared": 2880, "debug": 30},
        "exclude": {p: "exp-1-38,exp-1-44" for p in ("compute", "shared", "debug")}, "whole_node": {"compute", "debug"},
        "defaults": {"lanes": "compute", "build": "shared", "plan": "shared", "assemble": "shared"}, "lanes_per_node": 16,
        "lanes_partitions": {"compute"},
        "shared_shape": {"build": (32, "64G"), "plan": (4, "16G"), "assemble": (16, "64G")},
        "classes": {"compute": "normal", "shared": "shared", "debug": "debug"},
        "lock": "/expanse/lustre/scratch/zzheng8/temp_project/c8d3/locks/c8d3.lock",
        "c8d3_root": "/expanse/lustre/scratch/zzheng8/temp_project/c8d3",
    },
}
DEFAULT_TIME = {"build": "02:00:00", "plan": "02:00:00", "assemble": "02:00:00"}
PLAN_OPTS = {"--purpose": ("choice", ("pilot", "production")), "--points": ("int",), "--replicates": ("int",),
             "--threads": ("int",), "--graph-block": ("int",), "--chunk-points": ("int",), "--loops": ("ints",),
             "--allocation": ("path",)}
INDEX_OPTS = {"--bundle-jobs": ("int",), "--max-tasks": ("int",), "--statistics": ("path",), "--target-core-seconds": ("float",)}
KEEP_ENV = {"SLURM_CONF"}
TERMINAL = {"BOOT_FAIL", "CANCELLED", "COMPLETED", "DEADLINE", "FAILED", "NODE_FAIL", "OUT_OF_MEMORY", "PREEMPTED",
            "TIMEOUT", "REVOKED", "SPECIAL_EXIT"}


class Refuse(Exception):
    def __init__(self, code, text):
        super().__init__(text);self.code = code


def env(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and (v is None or v == ""):
        raise Refuse(64, f"{name} is not set (source the site env file; docs/CLUSTERS.md)")
    return v


def int_env(name, default=None):
    v = env(name, default)
    if v is None:
        raise Refuse(64, f"{name} is not set: set this package's share from LRI_C8_shared/inventory/DECISIONS.md first")
    try:
        return int(v)
    except ValueError:
        raise Refuse(64, f"{name}={v!r} is not an integer") from None


def scheduler_env() -> dict:
    """The environment for sbatch, squeue and sacct: no inherited scheduler option variables."""
    return {k: v for k, v in os.environ.items()
            if k in KEEP_ENV or not k.startswith(("SBATCH_", "SALLOC_", "SRUN_", "SLURM_", "SQUEUE_", "SACCT_"))}


def minutes(t: str, partition: str, cfg: dict) -> int:
    m = re.fullmatch(r"(?:(\d+)-)?(\d+):(\d\d):(\d\d)", t or "")
    if not m:
        raise Refuse(64, f"--time {t!r} is not D-HH:MM:SS or HH:MM:SS")
    d, h, mi, s = (int(x or 0) for x in m.groups())
    if mi > 59 or s > 59 or (m.group(1) and h > 23):
        raise Refuse(64, f"--time {t!r} has an out-of-range component")
    total = math.ceil((d*86400 + h*3600 + mi*60 + s) / 60)   # Slurm rounds limits up to whole minutes
    if total <= 0:
        raise Refuse(64, "--time must be positive (0 means unlimited to Slurm)")
    if total > cfg["max_minutes"][partition]:
        raise Refuse(64, f"--time {t} exceeds {partition}'s limit of {cfg['max_minutes'][partition]} minutes")
    return total


def slurm_time(total_minutes: int) -> str:
    d, rem = divmod(total_minutes, 1440)
    return (f"{d}-" if d else "") + f"{rem // 60:02d}:{rem % 60:02d}:00"


def mem_mb(text: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([KMGT]?)", text or "")
    if not m:
        raise Refuse(64, f"--mem {text!r} is not a number with an optional K, M, G or T suffix")
    mb = float(m.group(1)) * {"K": 1/1024, "": 1, "M": 1, "G": 1024, "T": 1024**2}[m.group(2)]
    if mb <= 0:
        raise Refuse(64, "--mem must be positive (Slurm reads 0 as the whole node's memory)")
    return mb


def queue(selector: list) -> list:
    """Queued and running jobs for a squeue selector, one row per array element: id, name, partition, state, nodes,
    qos, user. A failed query or a malformed line refuses admission (69)."""
    out = subprocess.run(["squeue", "-h", "-r", "-t", "all", *selector, "-o", "%i|%j|%P|%T|%D|%q|%u"],
                         capture_output=True, text=True, env=scheduler_env())
    if out.returncode != 0:
        raise Refuse(69, f"squeue {' '.join(selector)} failed ({out.stderr.strip()[:200]}): admission needs the queue")
    rows = []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split("|")
        if len(parts) != 7 or not parts[4].isdigit():
            raise Refuse(69, f"unexpected squeue line {line!r}: admission refuses to guess")
        jid, name, part, state, nodes, qos, user = parts
        if state.split()[0] in TERMINAL:
            continue                          # every other state (suspended, requeued, held, completing, ...) counts
        rows.append({"id": jid, "name": name, "partition": part, "state": state, "nodes": int(nodes), "qos": qos, "user": user})
    return rows


def live_jobs() -> list:
    return queue(["-u", os.environ.get("USER", "")])


def c8d3_intents(cfg: dict) -> list:
    """The c8d3 package's unresolved submissions on this site (files in $C8D3_ROOT/intents/, resolved ones are moved to
    intents/resolved/), as queue rows of their partition. An intent may be a job not yet visible in squeue, so it
    occupies its class like a live c8d3 job. An unreadable store refuses admission (69)."""
    d = Path(env("C8OPT_C8D3_ROOT", cfg["c8d3_root"]))/"intents"
    if not d.exists():
        return []
    rows = []
    try:
        for f in sorted(d.glob("*.json")):
            rec = json.loads(f.read_text()).get("rec") or {}
            rows.append({"id": f"c8d3-intent:{f.stem}", "name": str(rec.get("name") or f"c8d3-intent-{f.stem}"),
                         "partition": str(rec.get("partition") or "?"), "state": "PENDING",
                         "nodes": int(rec.get("nodes") or 1), "qos": "?", "user": os.environ.get("USER", "")})
    except (OSError, ValueError, AttributeError) as exc:
        raise Refuse(69, f"cannot read the c8d3 intents in {d} ({exc}): the class handoff needs them") from None
    return rows


def family(row) -> str | None:
    return "c8opt" if row["name"].startswith("c8opt-") else "c8d3" if row["name"].startswith("c8d3-") else None


def ledger_path() -> Path:
    return Path(env("C8OPT_ROOT", required=True))/"ledger.jsonl"


def ledger_rows() -> list:
    p = ledger_path()
    rows = []
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    raise Refuse(69, f"{p}: an unreadable line; repair the ledger before admitting more work") from None
    return rows


def append_durable(path: Path, record: dict):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, (json.dumps(record, sort_keys=True) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def find_job(name: str, since_utc: str) -> str | None:
    """The job id submitted under this unique name (squeue, then sacct), else None. Raises Refuse(69) if unknown."""
    q = subprocess.run(["squeue", "-h", "-t", "all", "-u", os.environ.get("USER", ""), "-n", name, "-o", "%i"],
                       capture_output=True, text=True, env=scheduler_env())
    if q.returncode == 0 and q.stdout.strip():
        return q.stdout.split()[0]
    start = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(calendar.timegm(time.strptime(since_utc, "%Y-%m-%dT%H:%M:%SZ")) - 3600))
    a = subprocess.run(["sacct", "-n", "-X", "-P", "--name", name, "-S", start, "-o", "JobID"], capture_output=True,
                       text=True, env=scheduler_env())
    if a.returncode != 0 or q.returncode != 0:
        raise Refuse(69, f"cannot tell whether intent {name} was submitted (squeue/sacct failed)")
    ids = [x for x in a.stdout.split() if x.strip()]
    return ids[0].split(".")[0] if ids else None


def reconcile(rows: list) -> list:
    """Resolve intents without an outcome when squeue or sacct shows their unique job name (accepted). Nothing else
    resolves an intent automatically. An absent record is no proof that a submission never happened: an orphaned
    sbatch may still be in flight, and accounting may lag. Such an intent stays reserved until `submit.py resolve`
    records an explicit decision."""
    done = {r["token"] for r in rows if r.get("state") in ("accepted", "rejected")}
    for r in rows:
        if r.get("state") == "intent" and r["token"] not in done:
            jid = find_job(r["name"], r["utc"])
            if not jid:
                continue
            outcome = {"state": "accepted", "token": r["token"], "jobid": jid,
                       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "reconciled": True}
            append_durable(ledger_path(), outcome);rows.append(outcome);done.add(r["token"])
    return rows


def resolve(token: str, reason: str) -> int:
    """An operator's recorded decision that an unresolved intent was never submitted. Refused while squeue or sacct
    knows its name (then it is accepted instead)."""
    rows = ledger_rows()
    intents = {r["token"]: r for r in rows if r.get("state") == "intent"}
    if token not in intents:
        raise Refuse(64, f"no intent {token} in the ledger")
    if any(r.get("token") == token and r.get("state") in ("accepted", "rejected") for r in rows):
        raise Refuse(64, f"intent {token} is already resolved")
    if not reason.strip():
        raise Refuse(64, "--reason is required (what was checked)")
    r = intents[token];jid = find_job(r["name"], r["utc"])
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if jid:
        append_durable(ledger_path(), {"state": "accepted", "token": token, "jobid": jid, "utc": now, "reconciled": True})
        raise Refuse(65, f"intent {token} is job {jid} (found by its name): recorded accepted, not rejected")
    append_durable(ledger_path(), {"state": "rejected", "token": token, "utc": now, "decided_by": "operator",
                                   "reason": reason, "checked": "squeue and sacct show no job named " + r["name"]})
    print(json.dumps({"rejected": token, "name": r["name"], "reason": reason}))
    return 0


def unresolved(rows: list) -> list:
    """Intents with no outcome yet, as queue rows (they count against every cap as queued jobs)."""
    done = {r["token"] for r in rows if r.get("state") in ("accepted", "rejected")}
    return [{"id": f"intent:{r['token']}", "name": r["name"], "partition": r.get("partition", "?"), "state": "PENDING",
             "nodes": max(1, math.ceil(float(r.get("nodes", 1)))), "qos": "?", "user": os.environ.get("USER", "")}
            for r in rows if r.get("state") == "intent" and r["token"] not in done]


def reserved_node_hours(rows: list) -> float:
    """Every unrejected intent, plus records written before intents existed (no state: a submitted job)."""
    rejected = {r["token"] for r in rows if r.get("state") == "rejected"}
    return sum(float(r.get("node_hours", 0)) for r in rows
               if (r.get("state") == "intent" and r["token"] not in rejected) or "state" not in r)


def identity(path: Path) -> str:
    p = path.resolve()
    return f"{re.sub(r'[^A-Za-z0-9_.]', '_', p.name)[:40]}-{hashlib.sha256(str(p).encode()).hexdigest()[:8]}"


def admit(site: str, cfg: dict, role: str, partition: str, nodes: float, node_hours: float, ident: str) -> dict:
    ledger = reconcile(ledger_rows())
    pending_intents = unresolved(ledger)
    foreign_intents = c8d3_intents(cfg)
    rows = live_jobs() + pending_intents + foreign_intents   # an unresolved intent may be a real job: it counts everywhere
    info = {"live": {f: [r["id"] for r in rows if family(r) == f] for f in ("c8d3", "c8opt")},
            "unresolved_intents": [r["id"] for r in pending_intents]}
    if role == "lanes" and any(r["name"].startswith(f"c8opt-lanes-{ident}-") for r in rows):
        raise Refuse(65, f"a lane job for this dispatch ({ident}) is already queued, running or unresolved: one allocation per dispatch")
    whole = math.ceil(nodes)
    # One package per site and class: the c8d3 submitter does not count c8opt- jobs (and on Expanse refuses normal
    # admissions while they exist), so c8opt admits nothing while a c8d3- job of the same class is live.
    klass = (lambda r: "amd" if r["partition"] in cfg["amd_pool"] else "other") if site == "symmetry" else \
        (lambda r: cfg["classes"].get(r["partition"], "other"))
    mine = klass({"partition": partition})
    c8d3_live = [r["id"] for r in rows if (family(r) == "c8d3" or r["id"].startswith("c8d3-intent:")) and klass(r) == mine and mine != "other"]
    if c8d3_live:
        raise Refuse(65, f"c8d3- jobs or unresolved c8d3 submissions are live in the {mine} class on {site} "
                         f"({', '.join(c8d3_live[:8])}): c8opt and c8d3 never share a site class (docs/CLUSTERS.md, coexistence)")
    if site == "symmetry" and partition in cfg["amd_pool"]:
        own_cap, session_cap = int_env("C8OPT_AMD_CAP"), int_env("C8OPT_SESSION_AMD_CAP")
        own = sum(r["nodes"] for r in rows if family(r) == "c8opt" and r["partition"] in cfg["amd_pool"])
        both = own + sum(r["nodes"] for r in rows if family(r) == "c8d3" and r["partition"] in cfg["amd_pool"])
        info["amd_nodes"] = f"own {own}+{whole}/{own_cap}, session {both}+{whole}/{session_cap}"
        if own + whole > own_cap:
            raise Refuse(65, f"AMD-pool share: {own} c8opt nodes + {whole} new > C8OPT_AMD_CAP={own_cap}")
        if both + whole > session_cap:
            raise Refuse(65, f"AMD-pool session share: {both} c8d3/c8opt nodes + {whole} new > C8OPT_SESSION_AMD_CAP={session_cap}")
    if site == "expanse":
        cls = cfg["classes"][partition]
        if cls == "normal":   # H7E-R: compute jobs, normal QOS
            normal = [r for r in rows if klass(r) == "normal"]
            own = sum(1 for r in normal if family(r) == "c8opt");both = own + sum(1 for r in normal if family(r) == "c8d3")
            caps = {"C8OPT_RUN_CAP": (own, int_env("C8OPT_RUN_CAP")), "C8OPT_SUB_CAP": (own, int_env("C8OPT_SUB_CAP")),
                    "C8OPT_SESSION_RUN_CAP": (both, int_env("C8OPT_SESSION_RUN_CAP", "11")),
                    "C8OPT_SESSION_SUB_CAP": (both, int_env("C8OPT_SESSION_SUB_CAP", "27")),
                    # the user's running normal jobs over every session, plus this package's queued ones (they may
                    # start); other sessions' queued jobs are held by their own submitters' running caps
                    "C8OPT_USER_RUN_CAP": (sum(1 for r in normal if r["state"] == "RUNNING") + sum(
                        1 for r in normal if r["state"] != "RUNNING" and family(r) == "c8opt"), int_env("C8OPT_USER_RUN_CAP", "22")),
                    "C8OPT_USER_SUB_CAP": (len(normal), int_env("C8OPT_USER_SUB_CAP", "54"))}
            # the whole account, other users included: running normal jobs, plus this user's queued ones (they may start)
            account = [r for r in queue(["-A", cfg["account"]]) if klass(r) == "normal"]
            acct_n = sum(1 for r in account if r["state"] == "RUNNING") + sum(
                1 for r in normal if r["state"] != "RUNNING")
            caps["C8OPT_ACCOUNT_RUN_CAP"] = (acct_n, int_env("C8OPT_ACCOUNT_RUN_CAP", "32"))
            own_n = sum(r["nodes"] for r in normal if family(r) == "c8opt")
            both_n = own_n + sum(r["nodes"] for r in normal if family(r) == "c8d3")
            info["normal"] = {k: f"{n}+1/{c}" for k, (n, c) in caps.items()}
            info["compute_nodes"] = f"own {own_n}+{whole}/{env('C8OPT_COMPUTE_NODE_CAP')}, session {both_n}+{whole}/{env('C8OPT_SESSION_COMPUTE_NODE_CAP', '4')}"
            for k, (n, c) in caps.items():
                if n + 1 > c:
                    raise Refuse(65, f"Expanse normal-QOS share: {n} counted + 1 > {k}={c} (queued jobs count as running)")
            if own_n + whole > int_env("C8OPT_COMPUTE_NODE_CAP") or both_n + whole > int_env("C8OPT_SESSION_COMPUTE_NODE_CAP", "4"):
                raise Refuse(65, f"Expanse compute nodes: {info['compute_nodes']}")
        elif cls == "shared":   # H7E-R: the shared partition, at most 32 live jobs per session
            shared = [r for r in rows if klass(r) == "shared"]
            own = sum(1 for r in shared if family(r) == "c8opt");both = own + sum(1 for r in shared if family(r) == "c8d3")
            caps = {"C8OPT_SHARED_CAP": (own, int_env("C8OPT_SHARED_CAP", "8")),
                    "C8OPT_SESSION_SHARED_CAP": (both, int_env("C8OPT_SESSION_SHARED_CAP", "32"))}
            info["shared"] = {k: f"{n}+1/{c}" for k, (n, c) in caps.items()}
            for k, (n, c) in caps.items():
                if n + 1 > c:
                    raise Refuse(65, f"Expanse shared-partition share: {n} live + 1 > {k}={c}")
    cap = env("C8OPT_NODE_HOURS_CAP")
    if cap is None:
        raise Refuse(64, "C8OPT_NODE_HOURS_CAP (the approved node-hour budget of this package) is not set")
    used = reserved_node_hours(ledger)
    info["node_hours"] = f"{used:.2f}+{node_hours:.2f}/{cap}"
    if used + node_hours > float(cap) + 1e-9:
        raise Refuse(65, f"node-hour budget: {used:.2f} reserved + {node_hours:.2f} new > C8OPT_NODE_HOURS_CAP={cap}")
    return info


def used_seeds() -> set:
    used = set(EXAMPLE_SEEDS)
    for p in (ROOT/"inputs/pilot_design.json", ROOT/"results/pilot_20261008/manifest.json"):
        if p.exists():
            d = json.loads(p.read_text())
            for k in ("seed", "base_seed"):
                if isinstance(d.get(k), int):
                    used.add(d[k])
    reg = Path(env("C8OPT_ROOT", required=True))/"seeds.jsonl"
    if reg.exists():
        used |= {json.loads(x)["seed"] for x in reg.read_text().splitlines() if x.strip()}
    for name in filter(None, (env("C8OPT_FOREIGN_SEED_LOGS", "") or "").split(":")):
        d = json.loads(Path(name).read_text())
        rows = d.get("seeds", d) if isinstance(d, dict) else d
        used |= {int(r["seed"]) if isinstance(r, dict) else int(r) for r in rows}
    return used


def allow_listed(text: str, allowed: dict, what: str) -> list:
    """shlex-split options, keeping only allow-listed ones with valid values; paths are resolved."""
    argv, out, i = shlex.split(text or ""), [], 0
    while i < len(argv):
        opt = argv[i]
        if opt not in allowed:
            raise Refuse(64, f"{what}: option {opt!r} is not allowed (allowed: {sorted(allowed)}; the seed, executable, "
                             "destinations and lane count come from submit.py)")
        kind = allowed[opt][0];i += 1;vals = []
        while i < len(argv) and not argv[i].startswith("--"):
            vals.append(argv[i]);i += 1
        if kind != "ints" and len(vals) != 1 or not vals:
            raise Refuse(64, f"{what}: {opt} takes {'one or more values' if kind == 'ints' else 'one value'}")
        try:
            if kind == "int" or kind == "ints":
                vals = [str(int(v)) for v in vals]
            elif kind == "float":
                vals = [repr(float(vals[0]))]
            elif kind == "choice" and vals[0] not in allowed[opt][1]:
                raise ValueError
            elif kind == "path":
                if not Path(vals[0]).exists():
                    raise Refuse(64, f"{what}: {opt} {vals[0]} does not exist")
                vals = [str(Path(vals[0]).resolve())]
        except ValueError:
            raise Refuse(64, f"{what}: bad value for {opt}: {vals}") from None
        if opt in out:
            raise Refuse(64, f"{what}: {opt} given twice")
        out += [opt, *vals]
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="role", required=True)
    for role in ("build", "plan", "lanes", "assemble"):
        q = sub.add_parser(role)
        if role == "plan":
            q.add_argument("run", type=Path);q.add_argument("dispatch", type=Path)
            q.add_argument("--seed", type=int, required=True);q.add_argument("--lanes", type=int, required=True)
            q.add_argument("--plan-args", default="");q.add_argument("--index-args", default="")
        if role == "lanes":
            q.add_argument("dispatch", type=Path);q.add_argument("--nodes", type=int, required=True)
            q.add_argument("--lanes-per-node", type=int);q.add_argument("--grace", type=int, default=600)
        if role == "assemble":
            q.add_argument("run", type=Path);q.add_argument("--dependency")
        if role == "build":
            q.add_argument("--any-cpu", action="store_true", help="allow a test build on another CPU (C8OPT_ANY_CPU=1)")
        q.add_argument("--partition");q.add_argument("--time");q.add_argument("--mem");q.add_argument("--dry-run", action="store_true")
    sub.add_parser("ledger")
    q = sub.add_parser("resolve", help="record that an unresolved intent was never submitted (after checking)")
    q.add_argument("token");q.add_argument("--rejected", action="store_true", required=True);q.add_argument("--reason", required=True)
    a = p.parse_args(argv)
    try:
        if a.role == "resolve":
            fd = session_lock(SITES[env("C8OPT_SITE", required=True)])
            try:
                return resolve(a.token, a.reason)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN);os.close(fd)
        if a.role == "ledger":
            rows = ledger_rows()
            print(json.dumps({"entries": len(rows), "reserved_node_hours": round(reserved_node_hours(rows), 3),
                              "cap": os.environ.get("C8OPT_NODE_HOURS_CAP"), "last": rows[-6:]}, indent=1))
            return 0
        return submit(a)
    except Refuse as e:
        print(f"c8opt submit: {e}", file=sys.stderr)
        return e.code


def session_lock(cfg: dict):
    path = Path(env("C8OPT_SESSION_LOCK", cfg["lock"]))
    if not path.parent.is_dir():
        raise Refuse(69, f"the session lock directory {path.parent} does not exist (the c8d3 package creates it)")
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.time() + float(env("C8OPT_LOCK_WAIT", "600"))
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError as exc:
            if exc.errno not in (errno.EAGAIN, errno.EACCES) or time.time() > deadline:
                os.close(fd)
                raise Refuse(75, f"the session lock {path} is busy or failed ({exc})") from exc
            time.sleep(2)


def submit(a) -> int:
    site = env("C8OPT_SITE", required=True)
    if site not in SITES:
        raise Refuse(64, f"C8OPT_SITE={site!r} is not symmetry or expanse")
    cfg = SITES[site];role = a.role
    root = Path(env("C8OPT_ROOT", required=True));package = Path(env("C8OPT_PACKAGE", str(ROOT)))
    env("C8OPT_ENV_SETUP", required=True)
    partition = a.partition or cfg["defaults"][role]
    if partition in cfg["forbidden"] or partition not in cfg["allowed"]:
        raise Refuse(64, f"partition {partition!r} is not allowed on {site} (allowed: {sorted(cfg['allowed'])}; never {sorted(cfg['forbidden'])})")
    if role == "lanes" and not a.time:
        raise Refuse(64, "--time is required for lanes (the lane deadline and the budget use it)")
    mins = minutes(a.time or DEFAULT_TIME[role], partition, cfg);t = slurm_time(mins);h = mins/60
    cores = cfg["cores"][partition];whole = partition in cfg["whole_node"]
    extra, shape, effective = {}, [], {}
    if whole:
        mem = a.mem or cfg["mem"][partition]
    else:
        c, default_mem = cfg["shared_shape"][role];mem = a.mem or default_mem
    mem_mb(mem)
    if role == "lanes":
        if partition not in cfg["lanes_partitions"]:
            raise Refuse(64, f"lanes run only on {site}'s integration partitions {sorted(cfg['lanes_partitions'])}, not {partition}")
        lpn = a.lanes_per_node or cfg["lanes_per_node"]
        if lpn < 1 or cores % lpn:
            raise Refuse(64, f"--lanes-per-node {lpn} does not divide the {cores} cores of a {partition} node")
        idx = json.loads((a.dispatch/"index.json").read_text())
        if a.nodes < 1 or len(idx["lanes"]) != a.nodes*lpn:
            raise Refuse(64, f"the dispatch has {len(idx['lanes'])} lanes; {a.nodes} nodes x {lpn} lanes per node = {a.nodes*lpn}")
        if a.grace < 60 or a.grace >= mins*60:
            raise Refuse(64, "--grace must be at least 60 s and below the time limit")
        nodes, node_hours, ident = a.nodes, a.nodes*h, identity(a.dispatch)
        shape = [f"--nodes={a.nodes}", f"--ntasks-per-node={lpn}", f"--cpus-per-task={cores//lpn}", "--exclusive",
                 f"--signal=TERM@{a.grace}"]
        extra.update(C8OPT_DISPATCH=str(a.dispatch.resolve()), C8OPT_GRACE=str(a.grace))
        script = package/"slurm/run_hpc.sh"
    else:
        if whole:
            nodes, node_hours = 1, h
            shape = ["--nodes=1", "--ntasks=1", f"--cpus-per-task={cores}", "--exclusive"]
        else:
            frac = max(c/cores, mem_mb(mem)/cfg["node_mem_mb"])   # Expanse bills a shared job by the larger fraction
            nodes, node_hours = frac, frac*h
            shape = ["--nodes=1", "--ntasks=1", f"--cpus-per-task={c}"]
        if role == "build":
            ident, script = "build", package/"slurm/build.sh"
            if a.any_cpu:
                extra["C8OPT_ANY_CPU"] = "1"
            elif site == "symmetry" and partition not in cfg["amd_pool"]:
                raise Refuse(64, f"{partition} is not the integration CPU: build there only as a test (--any-cpu)")
        elif role == "plan":
            if a.run.exists() or a.dispatch.exists():
                raise Refuse(64, "the campaign and dispatch directories must be new")
            if not 0 <= a.seed < 2**63 or a.lanes < 1:
                raise Refuse(64, "the seed must lie in [0, 2^63) and --lanes must be positive")
            plan_argv = allow_listed(a.plan_args, PLAN_OPTS, "--plan-args")
            index_argv = allow_listed(a.index_args, INDEX_OPTS, "--index-args")
            ident, script = identity(a.run), package/"slurm/plan.sh"
            effective = {"plan_argv": plan_argv, "index_argv": index_argv}
            extra.update(C8OPT_RUN=str(a.run.resolve()), C8OPT_DISPATCH=str(a.dispatch.resolve()), C8OPT_SEED=str(a.seed),
                         C8OPT_LANES=str(a.lanes), C8OPT_PLAN_ARGV=json.dumps(plan_argv), C8OPT_INDEX_ARGV=json.dumps(index_argv))
        else:
            if a.dependency and not re.fullmatch(r"afterok:\d+(:\d+)*", a.dependency):
                raise Refuse(64, "--dependency takes afterok:<job id>[:<job id>...] only")
            ident, script = identity(a.run), package/"slurm/assemble.sh"
            extra["C8OPT_RUN"] = str(a.run.resolve())
            if a.dependency:
                shape.append(f"--dependency={a.dependency}")
    token = uuid.uuid4().hex[:10]
    name = f"c8opt-{role}-{ident}-{token}"
    args = ["sbatch", "--parsable", f"--job-name={name}", f"--partition={partition}", f"--time={t}", f"--mem={mem}",
            "--no-requeue", f"--output={root}/logs/%x_%j.out", "--export=ALL", *shape]
    if cfg["account"]:
        args.append(f"--account={cfg['account']}")
    exclude = [x for x in (cfg["exclude"].get(partition) or "").split(",") if x]
    extra_ex = env("C8OPT_AMD_EXCLUDE_EXTRA", "") if site == "symmetry" and partition in cfg["amd_pool"] else ""
    for x in filter(None, extra_ex.split(",")):
        if not re.fullmatch(r"cn\d{3}", x):
            raise Refuse(64, f"C8OPT_AMD_EXCLUDE_EXTRA item {x!r} is not cnNNN")
        if x not in exclude:
            exclude.append(x)
    if exclude:
        args.append(f"--exclude={','.join(exclude)}")
    args.append(str(script))
    record = {"state": "intent", "token": token, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "site": site,
              "role": role, "name": name, "partition": partition, "nodes": nodes, "time": t, "mem": mem,
              "node_hours": round(node_hours, 6), "env": extra, "effective": effective, "sbatch": args}
    (root/"logs").mkdir(parents=True, exist_ok=True)
    fd = session_lock(cfg)   # the c8d3 submitter's session lock: one admission at a time across both packages
    try:
        if role == "plan" and a.seed in used_seeds():
            raise Refuse(64, f"seed {a.seed} is already used (registry, delivered pilot, documentation example or a foreign seed log): use a fresh one")
        record["admission"] = admit(site, cfg, role, partition, nodes, node_hours, ident)
        if a.dry_run:
            print(json.dumps({"dry_run": True, **record}, indent=1));print(" ".join(shlex.quote(x) for x in args))
            return 0
        append_durable(ledger_path(), record)
        if role == "plan":
            append_durable(root/"seeds.jsonl", {"seed": a.seed, "run": extra["C8OPT_RUN"], "token": token, "utc": record["utc"]})
        out = subprocess.run(args, capture_output=True, text=True, env={**scheduler_env(), **extra})
        jid = out.stdout.strip().split(";")[0] if out.returncode == 0 and out.stdout.strip() else find_job(name, record["utc"])
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not jid:
            # No proof either way (the request may still be in flight): the intent stays unresolved and reserved
            # until a later admission finds the job or `submit.py resolve` records a checked decision.
            append_durable(ledger_path(), {"state": "sbatch_failed", "token": token, "utc": now, "sbatch_rc": out.returncode,
                                           "sbatch_stderr": out.stderr.strip()[:500]})
            raise Refuse(1, f"sbatch failed: {out.stderr.strip()[:500]} (intent {token} stays reserved until found or resolved: submit.py resolve)")
        append_durable(ledger_path(), {"state": "accepted", "token": token, "jobid": jid, "utc": now,
                                       "sbatch_rc": out.returncode})
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN);os.close(fd)
    print(json.dumps({"submitted": jid, "name": name, "partition": partition, "nodes": nodes, "time": t,
                      "admission": record["admission"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
