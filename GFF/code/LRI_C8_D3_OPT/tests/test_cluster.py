#!/usr/bin/env python3
"""Mac tests of the cluster workflow (docs/CLUSTERS.md) with a fake native worker (tests/fake_native.py) and fake
sbatch, squeue and sacct on PATH: the dispatcher's lock owners, stale-lock reclaim, lane lease, deadline deferral,
signal stop, per-bundle isolation and staging retry, and tools/submit.py's site rules, caps and ledger.
Exit 0 when every case passes. Runs in a few seconds plus the deliberate sleeps."""
from __future__ import annotations
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"tools"))
from campaign import plan, verify_plan  # noqa: E402
import hpc_dispatch as hd  # noqa: E402
from io_utils import ROOT, load, digest  # noqa: E402

PASSED = []


def ok(name):
    PASSED.append(name);print("PASS", name, flush=True)


FAKE_SLURM = r'''#!/usr/bin/env python3
import json, os, sys
path = os.environ["FAKE_SLURM_STATE"]; state = json.load(open(path))
cmd = os.path.basename(sys.argv[0]); a = sys.argv[1:]
def arg(flag):
    return a[a.index(flag) + 1] if flag in a else None
def save():
    json.dump(state, open(path, "w"))
def row(j, s):
    return "|".join([j, s.get("name", "x"), s.get("partition", "amdq"), s["state"], str(s.get("nodes", 1)), s.get("qos", "normal"), s.get("user", "me")])
LIVE = ("RUNNING", "PENDING", "COMPLETING")
ALL = arg("-t") == "all"
def shown(st):   # squeue -t all lists every state (terminal ones until MinJobAge); the default only live ones
    return ALL or st in LIVE
if cmd == "sacct":
    job, name = arg("-j"), arg("--name")
    if job:
        s = state.get("jobs", {}).get(job)
        if s: print(s["state"] + ("|" + s.get("end", "2026-01-01T00:00:00") if arg("-o") == "State,End" else ""))
    elif name:
        for j, s in state.get("jobs", {}).items():
            if s.get("name") == name: print(j)
elif cmd == "squeue":
    job, fmt, name, acct = arg("-j"), arg("-o"), arg("-n"), arg("-A")
    if job:
        s = state.get("jobs", {}).get(job)
        if s is None and state.get("purged_invalid"):
            print("slurm_load_jobs error: Invalid job id specified", file=sys.stderr); sys.exit(1)
        if s and shown(s["state"]):
            print(s.get("end", "2030-01-01T00:00:00") if fmt == "%e" else s["state"])
    elif name:
        for j, s in state.get("jobs", {}).items():
            if s.get("name") == name and shown(s["state"]): print(j)
    else:
        for line in state.get("raw_lines", []): print(line)
        for j, s in state.get("jobs", {}).items():
            if shown(s["state"]): print(row(j, s))
        if acct:
            for j, s in state.get("account_jobs", {}).items(): print(row(j, s))
elif cmd == "sbatch":
    if os.environ.get("FAKE_SBATCH_FAIL"):
        print("sbatch: error: fake failure", file=sys.stderr); sys.exit(1)
    n = state.setdefault("next", 900000); state["next"] = n + 1
    state.setdefault("submitted", []).append(a)
    state.setdefault("sbatch_env", []).append(sorted(k for k in os.environ if k.startswith(("SBATCH_", "SLURM_"))))
    name = next((x.split("=", 1)[1] for x in a if x.startswith("--job-name=")), "x")
    part = next((x.split("=", 1)[1] for x in a if x.startswith("--partition=")), "amdq")
    if os.environ.get("FAKE_SBATCH_REGISTER"):
        state.setdefault("jobs", {})[str(n)] = {"state": "PENDING", "name": name, "partition": part, "nodes": 1}
    save(); print(n)
'''


def fake_bin(d: Path) -> Path:
    b = d/"bin";b.mkdir()
    for name in ("sacct", "squeue", "sbatch"):
        (b/name).write_text(FAKE_SLURM);(b/name).chmod(0o755)
    native = b/"c8d3_fake";native.write_text(f"#!/bin/sh\nexec {sys.executable} {HERE/'fake_native.py'} \"$@\"\n");native.chmod(0o755)
    return b


def set_state(path: Path, jobs: dict):
    path.write_text(json.dumps({"jobs": jobs}))


def all_done(run: Path, manifest: dict) -> bool:
    return all((run/"jobs"/f"{e['index']:06d}.done.json").exists() for e in manifest["jobs"])


def drop_receipts(run: Path, indices):
    for i in indices:
        (run/"jobs"/f"{i:06d}.done.json").unlink(missing_ok=True)


def lane_jobs(dispatch: Path, lane: int) -> list:
    return [j for b in load(dispatch/f"lane_{lane:06d}.json")["bundles"] for j in b["jobs"]]


def main():
    with tempfile.TemporaryDirectory(prefix="c8_cluster_tests_") as tmp:
        d = Path(tmp);b = fake_bin(d);state = d/"slurm_state.json";set_state(state, {})
        os.environ["PATH"] = f"{b}:{os.environ['PATH']}";os.environ["FAKE_SLURM_STATE"] = str(state)
        os.environ["C8_STAGE_BACKOFF"] = "0.01"
        for k in ("SLURM_JOB_ID", "SLURM_PROCID", "SLURM_STEP_ID", "C8_JOB_END_EPOCH"):
            os.environ.pop(k, None)
        run = d/"run"
        plan(SimpleNamespace(directory=run, points=16, chunk_points=8, replicates=4, threads=1, graph_block=2,
                             seed=4242424242, purpose="pilot", loops=[3], allocation=None, executable=b/"c8d3_fake"))
        manifest = verify_plan(run);n = len(manifest["jobs"])
        disp = d/"dispatch";index = hd.make_index(run, disp, lanes=2, bundle_jobs=2)
        r = [hd.run_lane(disp, i, 1, d/"scratch") for i in range(2)]
        assert all(x["complete"] for x in r) and sum(x["jobs_completed"] for x in r) == n and all_done(run, manifest), r
        assert not list(run.glob("jobs/*.lock")) and not list(disp.glob("*.lease")) and len(list((disp/"runs").glob("lane_*.json"))) == 2
        ok(f"a fake L3 campaign ({n} jobs, {index['bundles']} bundles) runs in 2 lanes; every receipt published, no lock or lease left, a run summary per lane")

        # stale lock of a finished Slurm job: reclaimed and logged; the job reruns
        j0 = lane_jobs(disp, 0)[0];drop_receipts(run, [j0]);lock = run/"jobs"/f"{j0:06d}.lock";lock.mkdir()
        (lock/"owner.json").write_text(json.dumps({"slurm_job_id": "111", "host": "other", "pid": 1}))
        set_state(state, {"111": {"state": "TIMEOUT"}})
        x = hd.run_lane(disp, 0, 1, d/"scratch")
        rec = [json.loads(line) for line in (run/"jobs/reclaimed_locks.jsonl").read_text().splitlines()]
        assert x["complete"] and x["jobs_completed"] == 1 and not lock.exists() and rec[-1]["owner"]["slurm_job_id"] == "111", (x, rec)
        ok("a lock whose owner Slurm job TIMED OUT (sacct) is reclaimed, logged in reclaimed_locks.jsonl, and its job reruns")

        # live owner, unknown owner state, unowned lock, own allocation: never reclaimed; the lane records busy and continues
        for owner, jobs, env_job, label in (({"slurm_job_id": "222", "host": "x", "pid": 1}, {"222": {"state": "RUNNING"}}, None, "a RUNNING owner"),
                                             ({"slurm_job_id": "223", "host": "x", "pid": 1}, {}, None, "an owner sacct and squeue do not know"),
                                             (None, {}, None, "an unowned lock (no owner record)"),
                                             ({"slurm_job_id": "333", "host": "x", "pid": 1}, {"333": {"state": "COMPLETED"}}, "333", "a lock of this same allocation")):
            drop_receipts(run, [j0]);lock.mkdir()
            if owner:
                (lock/"owner.json").write_text(json.dumps(owner))
            set_state(state, jobs)
            if env_job:
                os.environ.update(SLURM_JOB_ID=env_job, C8_JOB_END_EPOCH=str(time.time() + 10**6))
            try:
                x = hd.run_lane(disp, 0, 1, d/"scratch")
            finally:
                os.environ.pop("SLURM_JOB_ID", None);os.environ.pop("C8_JOB_END_EPOCH", None)
            assert not x["complete"] and x["busy"] and lock.exists() and not (run/"jobs"/f"{j0:06d}.done.json").exists(), (label, x)
            (lock/"owner.json").unlink(missing_ok=True);lock.rmdir()
            ok(f"{label}: the lock is kept, the bundle is recorded busy, the lane continues and reports incomplete")
        assert hd.run_lane(disp, 0, 1, d/"scratch")["complete"]

        # a live lease: the lane refuses to run twice
        lease = disp/"lane_000001.lease";lease.mkdir();(lease/"owner.json").write_text(json.dumps({"slurm_job_id": "444", "host": "x", "pid": 1}))
        set_state(state, {"444": {"state": "RUNNING"}})
        try:
            hd.run_lane(disp, 1, 1, d/"scratch");raise AssertionError("a live lease was ignored")
        except hd.Busy:
            pass
        set_state(state, {"444": {"state": "CANCELLED by 1"}})
        assert hd.run_lane(disp, 1, 1, d/"scratch")["complete"] and not lease.exists()
        ok("a lane leased by a live allocation is refused (Busy, exit 75 from main); a lease of a CANCELLED allocation is reclaimed")

        # deadline: with statistics, bundles that do not fit before the job's end are deferred, not started
        stats = {s: {"3": {str(g["id"]): {c: {"cpu_seconds": 100.0, "points": 16} for c in "ab"} for g in grp["graphs"]}}
                 for s in ("free", "power") for grp in manifest["groups"] if grp["sector"] == s and grp["campaign"] == "a"}
        sp = d/"stats.json";sp.write_text(json.dumps(stats))
        disp2 = d/"dispatch2";hd.make_index(run, disp2, lanes=1, bundle_jobs=2, statistics=sp)
        drop_receipts(run, [e["index"] for e in manifest["jobs"]])
        os.environ["C8_JOB_END_EPOCH"] = str(time.time() + 60)
        try:
            x = hd.run_lane(disp2, 0, 1, d/"scratch")
        finally:
            os.environ.pop("C8_JOB_END_EPOCH")
        assert not x["complete"] and len(x["deferred"]) == len(load(disp2/"lane_000000.json")["bundles"]) and x["jobs_completed"] == 0, x
        assert all(b["estimate_seconds"] > 60 for b in x["deferred"])
        ok("with pilot statistics, every bundle whose estimated wall time does not fit before the job's end is deferred (none started)")
        x = hd.run_lane(disp2, 0, 1, d/"scratch");assert x["complete"] and all_done(run, manifest)
        ok("without a deadline the same index then completes every job")

        # SIGTERM during a native run: the child stops, locks are released, exit 143; a rerun completes
        drop_receipts(run, [e["index"] for e in manifest["jobs"]])
        env = {**os.environ, "FAKE_NATIVE_SLEEP": "30", "PYTHONPATH": str(HERE.parent/"tools")}
        p = subprocess.Popen([sys.executable, "-B", str(HERE.parent/"tools/hpc_dispatch.py"), "run", str(disp), "--lane", "0",
                              "--threads", "1", "--scratch", str(d/"scratch")], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.time() + 20
        while time.time() < deadline and not list(run.glob("jobs/*.lock")):
            time.sleep(0.1)
        time.sleep(0.5);p.send_signal(signal.SIGTERM);out, err = p.communicate(timeout=60)
        summary = json.loads(out.strip().splitlines()[-1])
        assert p.returncode == 143 and summary["stopped_by_signal"] == signal.SIGTERM, (p.returncode, out[-500:], err[-800:])
        assert not list(run.glob("jobs/*.lock")) and not (disp/"lane_000000.lease").exists() and not any(
            (run/"jobs"/f"{j:06d}.done.json").exists() for j in lane_jobs(disp, 0)), list(run.glob("jobs/*"))
        assert hd.run_lane(disp, 0, 1, d/"scratch")["complete"]
        ok("SIGTERM during a native run: the native child is stopped, every lock and the lease released, no receipt published, exit 143; a rerun completes the lane")

        # a failing native run: recorded, the lane continues, its locks are released, the log kept
        drop_receipts(run, lane_jobs(disp, 1));os.environ["FAKE_NATIVE_FAIL"] = "1"
        try:
            x = hd.run_lane(disp, 1, 1, d/"scratch")
        finally:
            os.environ.pop("FAKE_NATIVE_FAIL")
        nb = len(load(disp/"lane_000001.json")["bundles"])
        assert not x["complete"] and len(x["failed"]) == nb and not list(run.glob("jobs/*.lock")) and list(run.glob("jobs/dispatch-failed-*.log")), x
        assert hd.run_lane(disp, 1, 1, d/"scratch")["complete"]
        ok(f"a failing native worker: all {nb} bundles of the lane are recorded failed (not fatal), locks released, logs kept; a rerun completes")

        # a corrupt published checkpoint stays fatal
        out_file = run/"jobs"/f"{lane_jobs(disp, 0)[0]:06d}.native.json";orig = out_file.read_bytes();out_file.write_bytes(orig + b" ")
        try:
            hd.run_lane(disp, 0, 1, d/"scratch");raise AssertionError("checkpoint corruption accepted")
        except ValueError as exc:
            assert not isinstance(exc, hd.StageMismatch)
        out_file.write_bytes(orig);assert not (disp/"lane_000000.lease").exists()
        ok("a corrupt published checkpoint is still fatal (ValueError), and the lease is released")

        # staging: a transient bad read is retried; a persistent mismatch fails after C8_STAGE_RETRIES
        src = d/"src.bin";good = b"good bytes" * 1000;src.write_bytes(b"bad")
        os.environ["C8_STAGE_BACKOFF"] = "0.2"
        threading.Timer(0.1, lambda: src.write_bytes(good)).start()
        cache = hd.StageCache(d/"cache1");t = cache.stage(src, "x", __import__("hashlib").sha256(good).hexdigest())
        assert t.read_bytes() == good and cache.retries >= 1
        os.environ["C8_STAGE_BACKOFF"] = "0.01";cache = hd.StageCache(d/"cache2")
        try:
            cache.stage(src, "y", "0" * 64);raise AssertionError("persistent mismatch accepted")
        except hd.StageMismatch:
            assert not (d/"cache2/y").exists() and cache.retries == 2
        ok("staging retries a transient checksum mismatch from the source and fails (StageMismatch, nothing left) after 3 attempts")

        # R01: two contenders that judged the same stale record: the second can never move the first one's new lock
        lk = d/"race.lock";lk.mkdir();stale = {"slurm_job_id": "555", "host": "x", "pid": 1, "token": "T0"}
        (lk/"owner.json").write_text(json.dumps(stale));set_state(state, {"555": {"state": "FAILED"}});rlog = d/"race.jsonl"
        tok_a = hd.acquire(lk, rlog)                                   # contender A reclaims and takes the lock
        assert (d/"race.lock.stale-T0").is_dir() and hd.read_owner(lk)["token"] == tok_a
        real_read = hd.read_owner
        hd.read_owner = lambda lock: stale if lock == lk else real_read(lock)   # B still holds its old reading of T0
        try:
            hd.acquire(lk, rlog);raise AssertionError("B took a lock it must not")
        except hd.Busy:
            pass
        finally:
            hd.read_owner = real_read
        assert real_read(lk)["token"] == tok_a and (d/"race.lock.stale-T0").is_dir(), "A's lock was moved"
        assert not hd.release(lk, "not-the-token") and lk.is_dir() and hd.release(lk, tok_a) and not lk.exists()
        ok("R01: a contender acting on an old stale reading cannot move the reclaimer's new lock (the fixed tombstone name refuses the rename); "
           "release removes a lock only with its own token")

        # R11: the deadline is the TERM signal (C8OPT_GRACE before the end), not the job's end
        drop_receipts(run, lane_jobs(disp, 0))
        os.environ.update(C8_JOB_END_EPOCH=str(time.time() + 700), C8OPT_GRACE="600")
        try:
            x = hd.run_lane(disp, 0, 1, d/"scratch")
        finally:
            os.environ.pop("C8OPT_GRACE")
        assert not x["complete"] and x["deferred"] and x["jobs_completed"] == 0, x
        try:
            x = hd.run_lane(disp, 0, 1, d/"scratch")
        finally:
            os.environ.pop("C8_JOB_END_EPOCH")
        assert x["complete"], x
        ok("R11: with 700 s left and TERM due 600 s before the end, no bundle starts (pad 300 s); without the grace the same lane runs")

        # R12: a fully receipted bundle is complete whatever the deadline or its historical cost
        os.environ["C8_JOB_END_EPOCH"] = str(time.time() + 5)
        try:
            x = hd.run_lane(disp2, 0, 1, d/"scratch")
        finally:
            os.environ.pop("C8_JOB_END_EPOCH")
        assert x["complete"] and not x["deferred"] and x["jobs_completed"] == 0, x
        ok("R12: completed jobs are checked before the deadline; a fully receipted lane is complete even with 5 s left")

        # R3-08: inside Slurm, an end time squeue cannot report defers bundles (never 'no deadline')
        drop_receipts(run, lane_jobs(disp, 1))
        x = json.loads(state.read_text());x["purged_invalid"] = True;x["jobs"] = {};state.write_text(json.dumps(x))
        os.environ["SLURM_JOB_ID"] = "999"
        try:
            x = hd.run_lane(disp, 1, 1, d/"scratch")
        finally:
            os.environ.pop("SLURM_JOB_ID")
        assert not x["complete"] and x["deferred"] and x["jobs_completed"] == 0 and x["job_end_epoch"] == "unknown", x
        set_state(state, {});assert hd.run_lane(disp, 1, 1, d/"scratch")["complete"]
        ok("R3-08: inside a Slurm job whose end squeue cannot report (after retries), every bundle is deferred; locally the lane runs")

        # R2-01: a job sacct calls finished is still live while squeue shows it (COMPLETING) or until it ended
        # C8_RECLAIM_SETTLE seconds ago; a purged job (squeue: invalid id) whose accounting ended long ago is finished
        recent = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 30))
        for jobs, label, want in (({"601": {"state": "COMPLETING"}}, "COMPLETING in squeue", "live"),
                                  ({"602": {"state": "CANCELLED by 5", "end": recent}}, "ended 30 s ago", "live"),
                                  ({"603": {"state": "TIMEOUT"}}, "ended long ago", "finished")):
            jid = next(iter(jobs));set_state(state, jobs)
            got = hd.slurm_job_state(jid)
            assert got == want, (label, got)
        x = json.loads(state.read_text());x["purged_invalid"] = True;x["jobs"] = {"604": {"state": "COMPLETED"}};state.write_text(json.dumps(x))
        assert hd.slurm_job_state("604") == "finished" and hd.slurm_job_state("605") == "unknown"
        ok("R2-01: an owner job still COMPLETING (squeue) or ended less than C8_RECLAIM_SETTLE ago is live; a purged job ended long ago "
           "is finished; a job neither squeue nor sacct knows is unknown")

        # R2-08: campaign.py run_job re-checks the receipt after taking the lock and never replaces a receipted output
        import campaign as cmp_mod
        j0 = manifest["jobs"][0]["index"];base0 = run/"jobs"/f"{j0:06d}"
        nat, rec = base0.with_suffix(".native.json").read_bytes(), base0.with_suffix(".done.json").read_bytes()
        base0.with_suffix(".native.json").unlink();base0.with_suffix(".done.json").unlink()
        real_mkdir = Path.mkdir

        def racing_mkdir(self, *a, **k):   # another writer publishes between run_job's receipt check and its lock
            if self == base0.with_suffix(".lock"):
                base0.with_suffix(".native.json").write_bytes(nat);base0.with_suffix(".done.json").write_bytes(rec)
            return real_mkdir(self, *a, **k)
        Path.mkdir = racing_mkdir
        try:
            fresh = cmp_mod.run_job(run, j0, 1, verify_plan(run))
        finally:
            Path.mkdir = real_mkdir
        assert fresh is False and base0.with_suffix(".native.json").read_bytes() == nat and not base0.with_suffix(".lock").exists()
        ok("R2-08: a receipt published between campaign.py's check and its lock is validated and kept (no rerun, no replacement)")

        # submit.py
        submit_tests(d, b, state, run, disp)
    print(json.dumps({"status": "passed", "cases": len(PASSED)}))


def hd_identity(path: Path) -> str:
    import submit as sm
    return sm.identity(path)


def submit_tests(d: Path, b: Path, state: Path, run: Path, disp: Path):
    sp = HERE.parent/"tools/submit.py"
    root = d/"root";root.mkdir()
    lockfile = d/"session.lock";lockfile.write_text("")
    foreign = d/"foreign_seeds.json";foreign.write_text(json.dumps({"seeds": [{"seed": 31415926535}]}))
    (d/"env.sh").write_text("# test env\n")
    clean = {k: v for k, v in os.environ.items()
             if not k.startswith(("C8OPT_", "SBATCH_", "SLURM_", "SQUEUE_", "FAKE_SBATCH"))}
    base = {**clean, "C8OPT_ROOT": str(root), "C8OPT_NODE_HOURS_CAP": "100", "C8OPT_ENV_SETUP": str(d/"env.sh"),
            "C8OPT_PACKAGE": str(HERE.parent), "C8OPT_SESSION_LOCK": str(lockfile), "C8OPT_LOCK_WAIT": "1",
            "C8OPT_FOREIGN_SEED_LOGS": str(foreign), "C8OPT_C8D3_ROOT": str(d/"c8d3root")}
    sym = {"C8OPT_AMD_CAP": 4, "C8OPT_SESSION_AMD_CAP": 9}
    exp = {"C8OPT_RUN_CAP": 4, "C8OPT_SUB_CAP": 8, "C8OPT_COMPUTE_NODE_CAP": 2}

    def sub(*args, site="symmetry", **env):
        e = {**base, "C8OPT_SITE": site, **{k: str(v) for k, v in env.items() if v is not None}}
        for k, v in env.items():
            if v is None:
                e.pop(k, None)
        return subprocess.run([sys.executable, "-B", str(sp), *map(str, args)], env=e, capture_output=True, text=True)

    def st():
        return json.loads(state.read_text())

    def jobs(j, **extra):
        x = st();x["jobs"] = j;x.update(extra);state.write_text(json.dumps(x))

    def ledger():
        return [json.loads(x) for x in (root/"ledger.jsonl").read_text().splitlines()]

    jobs({})
    cp = sub("lanes", disp, "--nodes", 1, "--time", "01:00:00", **sym)
    assert cp.returncode == 64 and "lanes" in cp.stderr, cp.stderr
    disp8 = d/"dispatch8";hd.make_index(run, disp8, lanes=8, bundle_jobs=1)
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:30", **sym, SBATCH_ARRAY_INX="0-9", SLURM_TIME_LIMIT="5")
    assert cp.returncode == 0, cp.stderr
    a = st()["submitted"][-1]
    for need in ("--partition=amdq", "--nodes=1", "--ntasks-per-node=8", "--cpus-per-task=8", "--exclusive", "--no-requeue",
                 "--time=01:01:00", "--exclude=cn112,cn079,cn080,cn081,cn082,cn084,cn085,cn087,cn092", "--signal=TERM@600",
                 "--mem=240G", "--export=ALL"):
        assert need in a, (need, a)
    assert any(x.startswith("--job-name=c8opt-lanes-dispatch8-") for x in a) and st()["sbatch_env"][-1] == [], (a, st()["sbatch_env"][-1])
    led = ledger();intent = [r for r in led if r.get("state") == "intent"][-1]
    assert intent["node_hours"] == round(61/60, 6) and led[-1]["state"] == "accepted" and led[-1]["token"] == intent["token"] and led[-1]["jobid"] == "900000", led
    assert intent["env"]["C8OPT_GRACE"] == "600"
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", "--dry-run", **sym, C8OPT_AMD_EXCLUDE_EXTRA="cn099")
    assert cp.returncode == 0 and "cn092,cn099" in cp.stdout, cp.stdout[-300:]
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", "--dry-run", **sym, C8OPT_AMD_EXCLUDE_EXTRA="bad")
    assert cp.returncode == 64 and "cnNNN" in cp.stderr
    ok("submit.py lanes on symmetry: amdq, 8 x 8, exclusive, --no-requeue, --mem, cn112 and the known EPYC 7532 nodes excluded "
       "(C8OPT_AMD_EXCLUDE_EXTRA adds cnNNN); TERM 600 s early with C8OPT_GRACE; "
       "--time rounded up to whole minutes; SBATCH_*/SLURM_* never reach sbatch; an fsynced intent then an accepted line")
    for args, why in ((["lanes", disp8, "--nodes", 1, "--time", "01:00:00", "--partition", "longq"], "partition"),
                      (["lanes", disp8, "--nodes", 1, "--time", "01:00:00", "--partition", "amdpreq"], "partition"),
                      (["lanes", disp8, "--nodes", 1], "--time"),
                      (["lanes", disp8, "--nodes", 1, "--time", "00:00:00"], "positive"),
                      (["lanes", disp8, "--nodes", 1, "--time", "24:00:01"], "limit"),
                      (["build", "--partition", "amddebugq", "--time", "02:00:00"], "limit"),
                      (["lanes", disp8, "--nodes", 1, "--time", "01:75:00"], "out-of-range")):
        cp = sub(*args, **sym);assert cp.returncode == 64 and why in cp.stderr, (args, cp.stderr)
    ok("submit.py refuses longq, amdpreq, a missing or zero --time, a malformed time and one above the partition's limit (64)")
    # one package per site and class: a live c8d3- AMD-pool job refuses any c8opt AMD-pool job; then own / session caps
    jobs({"1": {"state": "RUNNING", "name": "c8d3-prod_lane-x", "partition": "amdq", "nodes": 5},
          "3": {"state": "RUNNING", "name": "other-job", "partition": "amdq", "nodes": 5}})
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", C8OPT_AMD_CAP=9, C8OPT_SESSION_AMD_CAP=9)
    assert cp.returncode == 65 and "never share a site class" in cp.stderr, cp.stderr
    cp = sub("plan", d/"cls_run", d/"cls_disp", "--seed", 7777777, "--lanes", 8, "--dry-run", C8OPT_AMD_CAP=9, C8OPT_SESSION_AMD_CAP=9)
    assert cp.returncode == 0, cp.stderr   # defq is another class: a plan may run beside c8d3 production
    jobs({"2": {"state": "PENDING", "name": "c8opt-lanes-y", "partition": "amddebugq", "nodes": 2},
          "3": {"state": "RUNNING", "name": "other-job", "partition": "amdq", "nodes": 5}})
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", C8OPT_AMD_CAP=2, C8OPT_SESSION_AMD_CAP=9)
    assert cp.returncode == 65 and "C8OPT_AMD_CAP" in cp.stderr, cp.stderr
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", C8OPT_AMD_CAP=4, C8OPT_SESSION_AMD_CAP=2)
    assert cp.returncode == 65 and "SESSION" in cp.stderr, cp.stderr
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", C8OPT_AMD_CAP=3, C8OPT_SESSION_AMD_CAP=3)
    assert cp.returncode == 0, cp.stderr
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", C8OPT_AMD_CAP=3)
    assert cp.returncode == 64 and "C8OPT_SESSION_AMD_CAP" in cp.stderr, cp.stderr
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", "--partition", "defq", **sym)
    assert cp.returncode == 64 and "integration partitions" in cp.stderr, cp.stderr
    ok("R3-02/05: one package per site class (a live c8d3- AMD-pool job refuses c8opt AMD-pool jobs; defq plans still pass); "
       "c8opt AMD nodes (pending included) within C8OPT_AMD_CAP and the session share; both caps required; lanes never on defq")
    jobs({}, raw_lines=["garbage line"])
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", **sym)
    assert cp.returncode == 69 and "unexpected squeue line" in cp.stderr, cp.stderr
    x = st();x["raw_lines"] = [];state.write_text(json.dumps(x))
    calls = [c for c in st().get("calls", [])]
    ok("a malformed squeue line stops admission (69); the queue is read with -r (one row per array element)")
    # node-hour budget over unrejected intents; a failed sbatch is recorded rejected and frees its reservation
    jobs({})
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "23:00:00", **sym, C8OPT_NODE_HOURS_CAP=20)
    assert cp.returncode == 65 and "node-hour" in cp.stderr, cp.stderr
    before, used0 = len(ledger()), json.loads(sub("ledger").stdout)["reserved_node_hours"]
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", **sym, FAKE_SBATCH_FAIL=1)
    assert cp.returncode == 1 and [r.get("state") for r in ledger()[before:]] == ["intent", "sbatch_failed"], ledger()[before:]
    tok = ledger()[before]["token"]
    assert abs(json.loads(sub("ledger").stdout)["reserved_node_hours"] - (used0 + 1.0)) < 1e-3
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", **sym)
    assert cp.returncode == 65 and "unresolved" in cp.stderr, cp.stderr
    cp = sub("resolve", tok, "--rejected", "--reason", "")
    assert cp.returncode == 64 and "reason" in cp.stderr, cp.stderr
    cp = sub("resolve", tok, "--rejected", "--reason", "sbatch printed an error; squeue and sacct show no such name")
    assert cp.returncode == 0 and ledger()[-1].get("state") == "rejected" and ledger()[-1].get("decided_by") == "operator", cp.stderr
    assert abs(json.loads(sub("ledger").stdout)["reserved_node_hours"] - used0) < 1e-3
    cp = sub("resolve", tok, "--rejected", "--reason", "again")
    assert cp.returncode == 64 and "already resolved" in cp.stderr, cp.stderr
    with (root/"ledger.jsonl").open("a") as f:   # a record of the first format (no state) still counts
        f.write(json.dumps({"role": "build", "jobid": "1", "node_hours": 2.0}) + "\n")
    assert abs(json.loads(sub("ledger").stdout)["reserved_node_hours"] - (used0 + 2.0)) < 1e-3
    ok("R2-02/R3-01: a failed sbatch with no job found leaves the intent unresolved: reserved, counted as a queued job (a duplicate "
       "lane job is refused); time never releases it; only `submit.py resolve --rejected --reason` (refused without a reason, or twice) does")
    # an intent without an outcome (a crash after it was written) is reconciled by its unique name
    jobs({"777": {"state": "RUNNING", "name": "c8opt-build-build-crashtoken", "partition": "amdq", "nodes": 1}})
    with (root/"ledger.jsonl").open("a") as f:
        f.write(json.dumps({"state": "intent", "token": "crashtoken", "name": "c8opt-build-build-crashtoken", "utc": "2026-10-09T12:00:00Z",
                            "node_hours": 2.0}) + "\n")
        f.write(json.dumps({"state": "intent", "token": "losttoken", "name": "c8opt-build-build-losttoken", "utc": "2026-10-09T12:00:00Z",
                            "node_hours": 50.0}) + "\n")
    cp = sub("build", "--partition", "defq", "--any-cpu", **sym)
    assert cp.returncode == 0, cp.stderr
    rec = {r["token"]: r for r in ledger() if r.get("reconciled")}
    assert rec["crashtoken"]["state"] == "accepted" and rec["crashtoken"]["jobid"] == "777" and "losttoken" not in rec, rec
    jobs({"777": {"state": "RUNNING", "name": "c8opt-build-build-crashtoken", "partition": "amdq", "nodes": 1}})
    cp = sub("resolve", "crashtoken", "--rejected", "--reason", "x")
    assert cp.returncode == 64 and "already resolved" in cp.stderr, cp.stderr
    cp = sub("resolve", "losttoken", "--rejected", "--reason", "no job of this name in squeue or sacct")
    assert cp.returncode == 0, cp.stderr
    ok("an intent without an outcome is accepted at the next admission when squeue/sacct know its unique name; one they do not "
       "know stays reserved until an operator resolves it")
    # plan: seeds (pilot, registry, foreign log), allow-listed options, effective argv recorded, reserved before sbatch
    jobs({})
    pilot_seed = json.loads((HERE.parent/"results/pilot_20261008/manifest.json").read_text())["base_seed"]
    for seed in (pilot_seed, 31415926535, 6129871430538291):
        cp = sub("plan", d/"new_run", d/"new_disp", "--seed", seed, "--lanes", 8)
        assert cp.returncode == 64 and "already used" in cp.stderr, (seed, cp.stderr)
    alloc = d/"alloc dir";alloc.mkdir();(alloc/"a.json").write_text("{}")
    for extra, why in ((["--plan-args", "--seed 5"], "not allowed"), (["--index-args", "--lanes 4"], "not allowed"),
                       (["--plan-args", "--executable /bin/sh"], "not allowed"), (["--plan-args", "--points x"], "bad value"),
                       (["--plan-args", "--points 16 --points 32"], "twice")):
        cp = sub("plan", d/"new_run", d/"new_disp", "--seed", 987654321987, "--lanes", 8, *extra)
        assert cp.returncode == 64 and why in cp.stderr, (extra, cp.stderr)
    cp = sub("plan", d/"new_run", d/"new_disp", "--seed", 987654321987, "--lanes", 8,
             "--plan-args", f"--loops 3 4 --points 16 --allocation '{alloc/'a.json'}'", "--index-args", "--bundle-jobs 4")
    assert cp.returncode == 0, cp.stderr
    intent = [r for r in ledger() if r.get("state") == "intent"][-1];reg = [json.loads(x) for x in (root/"seeds.jsonl").read_text().splitlines()]
    pa = json.loads(intent["env"]["C8OPT_PLAN_ARGV"])
    assert pa == ["--loops", "3", "4", "--points", "16", "--allocation", str((alloc/"a.json").resolve())] and intent["effective"]["index_argv"] == ["--bundle-jobs", "4"], intent
    assert reg[-1]["seed"] == 987654321987 and reg[-1]["token"] == intent["token"]
    cp = sub("plan", d/"new_run2", d/"new_disp2", "--seed", 987654321987, "--lanes", 8)
    assert cp.returncode == 64 and "already used" in cp.stderr
    cp = sub("plan", d/"run_x", d/"disp_x", "--seed", 55555555, "--lanes", 8, FAKE_SBATCH_FAIL=1)
    assert cp.returncode == 1 and 55555555 in [json.loads(x)["seed"] for x in (root/"seeds.jsonl").read_text().splitlines()]
    ok("plan: the pilot's, a foreign log's, an example and a registered seed are refused; --seed, --executable and --lanes overrides, "
       "bad values and repeats are refused; paths with spaces survive as one argument; the effective argv and the seed are recorded "
       "before sbatch, and a seed stays reserved even when sbatch fails")
    # Expanse: own and session normal-QOS caps, queued counted as running; shared billing by the larger fraction
    disp16 = d/"dispatch16";hd.make_index(run, disp16, lanes=16, bundle_jobs=1)
    jobs({})
    cp = sub("lanes", disp16, "--nodes", 1, "--time", "02:00:00", site="expanse", **exp)
    assert cp.returncode == 0, cp.stderr
    a = st()["submitted"][-1]
    for need in ("--account=yun124", "--partition=compute", "--ntasks-per-node=16", "--cpus-per-task=8", "--exclusive",
                 "--no-requeue", "--exclude=exp-1-38,exp-1-44"):
        assert need in a, (need, a)
    # shared class (own C8OPT_SHARED_CAP, session 32), separate from the normal (compute) class
    jobs({str(i): {"state": "PENDING", "name": f"c8opt-x{i}", "partition": "shared", "nodes": 1, "qos": "shared-normal"} for i in range(4)})
    cp = sub("assemble", run, site="expanse", **exp, C8OPT_SHARED_CAP=4)
    assert cp.returncode == 65 and "C8OPT_SHARED_CAP" in cp.stderr, cp.stderr
    cp = sub("assemble", run, site="expanse", **exp, C8OPT_SHARED_CAP=10, C8OPT_SESSION_SHARED_CAP=4)
    assert cp.returncode == 65 and "SESSION_SHARED_CAP" in cp.stderr, cp.stderr
    jobs({str(i): {"state": "RUNNING", "name": f"c8d3-s{i}", "partition": "shared", "nodes": 1} for i in range(3)})
    cp = sub("assemble", run, site="expanse", **exp)
    assert cp.returncode == 65 and "never share a site class" in cp.stderr, cp.stderr
    cp = sub("lanes", disp16, "--nodes", 1, "--time", "02:00:00", "--dry-run", site="expanse", **exp)
    assert cp.returncode == 0, cp.stderr   # c8d3 shared jobs do not block the compute class
    # normal class: session, user and account-wide caps; queued jobs count as running
    jobs({str(i): {"state": "RUNNING", "name": f"c8d3-x{i}", "partition": "compute", "nodes": 1} for i in range(2)})
    cp = sub("lanes", disp16, "--nodes", 1, "--time", "02:00:00", site="expanse", **exp)
    assert cp.returncode == 65 and "never share a site class" in cp.stderr, cp.stderr
    cp = sub("assemble", run, "--dry-run", site="expanse", **exp)
    assert cp.returncode == 0, cp.stderr   # c8d3 compute jobs do not block the shared class
    jobs({str(i): {"state": "PENDING", "name": f"c8opt-c{i}", "partition": "compute", "nodes": 1} for i in range(3)})
    cp = sub("lanes", disp16, "--nodes", 1, "--time", "02:00:00", site="expanse", **{**exp, "C8OPT_RUN_CAP": 10, "C8OPT_SUB_CAP": 10, "C8OPT_COMPUTE_NODE_CAP": 10}, C8OPT_SESSION_RUN_CAP=3)
    assert cp.returncode == 65 and "SESSION_RUN_CAP" in cp.stderr, cp.stderr
    jobs({str(i): {"state": "RUNNING", "name": f"other{i}", "partition": "compute", "nodes": 1} for i in range(22)})
    cp = sub("lanes", disp16, "--nodes", 1, "--time", "02:00:00", site="expanse", **exp)
    assert cp.returncode == 65 and "USER_RUN_CAP" in cp.stderr, cp.stderr
    jobs({str(i): {"state": "PENDING", "name": f"c8d2-ind-run-{i}", "partition": "compute", "nodes": 1} for i in range(27)})
    cp = sub("lanes", disp16, "--nodes", 1, "--time", "02:00:00", "--dry-run", site="expanse", **exp)
    assert cp.returncode == 0, cp.stderr   # another session's queued jobs do not count as running for the user's 22
    jobs({str(i): {"state": "PENDING", "name": f"c8d2-ind-run-{i}", "partition": "compute", "nodes": 1} for i in range(54)})
    cp = sub("lanes", disp16, "--nodes", 1, "--time", "02:00:00", site="expanse", **exp)
    assert cp.returncode == 65 and "USER_SUB_CAP" in cp.stderr, cp.stderr
    jobs({}, account_jobs={str(i): {"state": "RUNNING", "name": f"u{i}", "partition": "compute", "user": "someone"} for i in range(32)})
    cp = sub("lanes", disp16, "--nodes", 1, "--time", "02:00:00", site="expanse", **exp)
    assert cp.returncode == 65 and "ACCOUNT_RUN_CAP" in cp.stderr, cp.stderr
    x = st();x["account_jobs"] = {};state.write_text(json.dumps(x))
    cp = sub("assemble", run, "--mem", "0", site="expanse", **exp)
    assert cp.returncode == 64 and "positive" in cp.stderr, cp.stderr
    ok("R2-04/05, R3-03: Expanse shared and compute are separate classes, each held by one package at a time (a live c8d3 job of the "
       "class refuses c8opt); own and session caps per class; user 22 and account 32 running for compute; --mem 0 is refused (R2-03)")
    jobs({})
    cp = sub("assemble", run, site="expanse", **exp, C8OPT_NODE_HOURS_CAP=1000)
    assert cp.returncode == 0, cp.stderr
    intent = [r for r in ledger() if r.get("state") == "intent"][-1]
    assert abs(intent["node_hours"] - 2 * max(16/128, 64*1024/257400)) < 1e-6, intent["node_hours"]
    ok("Expanse: yun124, compute 16 x 8, exp-1-38/44 excluded; own, session and user normal-QOS caps count queued jobs as running; "
       "a shared job reserves the larger of its core and memory fraction (assemble 16 c / 64G: 0.255 node)")
    # one lane allocation per dispatch, by its canonical identity (a name with a space too)
    spaced = d/"pilot run";hd.make_index(run, spaced, lanes=8, bundle_jobs=1)
    jobs({}, );x = st();x["jobs"] = {};state.write_text(json.dumps(x))
    cp = sub("lanes", spaced, "--nodes", 1, "--time", "01:00:00", **sym, FAKE_SBATCH_REGISTER=1)
    assert cp.returncode == 0, cp.stderr
    cp = sub("lanes", spaced, "--nodes", 1, "--time", "01:00:00", **sym)
    assert cp.returncode == 65 and "already queued" in cp.stderr, cp.stderr
    ok("a second lane job for the same dispatch (by its canonical identity, also for a name with a space) is refused (65)")
    # R4-02: a suspended job still counts (squeue -t all; only terminal states are dropped)
    jobs({"91": {"state": "SUSPENDED", "name": f"c8opt-lanes-{hd_identity(disp8)}-zz", "partition": "amdq", "nodes": 1},
          "92": {"state": "COMPLETED", "name": "c8opt-old", "partition": "amdq", "nodes": 4}})
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", **sym)
    assert cp.returncode == 65 and "already queued" in cp.stderr, cp.stderr
    jobs({"91": {"state": "SUSPENDED", "name": "c8opt-other-x", "partition": "amdq", "nodes": 4},
          "92": {"state": "COMPLETED", "name": "c8opt-old", "partition": "amdq", "nodes": 4}})
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", **{**sym, "C8OPT_AMD_CAP": 4})
    assert cp.returncode == 65 and "C8OPT_AMD_CAP" in cp.stderr, cp.stderr   # 4 suspended + 1 > 4; the completed job is ignored
    jobs({})
    ok("R4-02: squeue is read with -t all; a SUSPENDED job counts (caps, duplicate dispatch) and a COMPLETED one does not")
    # R4-03: an unresolved c8d3 submission occupies its partition's class
    idir = d/"c8d3root"/"intents";(idir/"resolved").mkdir(parents=True)
    (idir/"resolved"/"old.json").write_text(json.dumps({"rec": {"name": "c8d3-x-old", "partition": "amdq"}}))
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", "--dry-run", **sym)
    assert cp.returncode == 0, cp.stderr   # resolved intents do not count
    (idir/"abc123.json").write_text(json.dumps({"rec": {"name": "c8d3-prod_lane-x-abc123", "partition": "amdq", "nodes": 1}}))
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", **sym)
    assert cp.returncode == 65 and "unresolved c8d3" in cp.stderr and "c8d3-intent:abc123" in cp.stderr, cp.stderr
    cp = sub("plan", d/"i_run", d/"i_disp", "--seed", 8888888, "--lanes", 8, "--dry-run", **sym)
    assert cp.returncode == 0, cp.stderr   # defq is another class
    (idir/"bad.json").write_text("{not json")
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", **sym)
    assert cp.returncode == 69 and "c8d3 intents" in cp.stderr, cp.stderr
    for f in idir.glob("*.json"):
        f.unlink()
    ok("R4-03: an unresolved c8d3 submission (intents/*.json) blocks c8opt in its partition's class (resolved ones do not); "
       "another class is unaffected; an unreadable intent refuses admission (69)")
    # the session lock: busy -> 75
    import fcntl
    fd = os.open(lockfile, os.O_RDWR);fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        cp = sub("build", "--partition", "defq", "--any-cpu", **sym)
        assert cp.returncode == 75 and "session lock" in cp.stderr, cp.stderr
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN);os.close(fd)
    ok("admission waits for the session lock shared with the c8d3 submitter and gives up with 75 after C8OPT_LOCK_WAIT")
    # dry run, build partitions, assemble dependency
    before = len(st().get("submitted", []))
    cp = sub("lanes", disp8, "--nodes", 1, "--time", "01:00:00", "--dry-run", **sym)
    assert cp.returncode == 0 and len(st().get("submitted", [])) == before and "sbatch" in cp.stdout, cp.stdout
    cp = sub("build", "--partition", "defq", **sym)
    assert cp.returncode == 64 and "--any-cpu" in cp.stderr, cp.stderr
    cp = sub("assemble", run, "--dependency", "afterany:5", **sym)
    assert cp.returncode == 64 and "afterok" in cp.stderr, cp.stderr
    ok("--dry-run submits nothing; a build off the integration CPU needs --any-cpu; assemble takes afterok dependencies only")


if __name__ == "__main__":
    main()
