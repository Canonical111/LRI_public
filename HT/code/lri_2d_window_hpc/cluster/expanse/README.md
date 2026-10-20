# Expanse runbook (account <ACCOUNT>, `shared` partition, no Lustre)

This layer runs the unchanged point driver (`code/hpc_run.py`) on SDSC Expanse. It adds:
- continuation chains;
- release, spec and environment binding;
- continuation after the wall limit;
- sacct-verified recovery of claims left by dead jobs.

Everything lives under `$HOME/lri2d_window` (`R` below). Expanse Lustre is not used, by the user's instruction
(2026-10-07) and because of the documented Lustre small-file and corruption problems. Each job extracts a
checksummed release tarball into node-local `/scratch/$USER/job_$SLURM_JOB_ID`, which also holds the Numba cache.

## Layout
```
R/envs/<env_id>/          immutable read-only venv (install_env.sh); env_id from envcheck.py
R/releases/ht2d_<c>.{tar,sha256,json}   release tarball, per-file manifest, record (make_release.sh)
R/validation/<job>/receipt.json         on-node validation (validate.sbatch)
R/campaigns/<name>/spec.json            frozen campaign spec (campaign.py freeze; never overwritten)
R/campaigns/<name>/inputs/<chain>/      frozen basis/seed copies
R/campaigns/<name>/chains/<chain>/      L<L>_z<nz>.json records, checkpoints, claims, state/<job>.json,
                                        history/ (archived checkpoints), logs/ (per-step driver logs)
R/campaigns/<name>/{jobs,SUBMITTED.jsonl,CONTINUATIONS.jsonl}
R/logs/                                 Slurm .out files
```

## Procedure
1. **Release.** On a machine with the git checkout, run:
   ```
   cluster/expanse/make_release.sh OUT <HOME>/lri2d_window/releases
   ```
   Then copy `OUT/*` to `R/releases/`.
2. **Environment.** Once, on the Expanse login node, run:
   ```
   install_env.sh R cluster/expanse/requirements-expanse.txt cluster/expanse/envcheck.py
   ```
   It prints the env_id.
3. **Validate:**
   ```
   sbatch -o R/logs/%x_%j.out cluster/expanse/validate.sbatch R R/releases/ht2d_<c>.json R/envs/<id>/bin/python
   ```
   The receipt must say `passed: true`. It runs pytest (inherited plus `tests/test_expanse.py`) and replays reference
   records at L=8 and 10 to ≤ 1e-9.
4. **Freeze:**
   ```
   python campaign.py freeze --request REQ.json --release R/releases/ht2d_<c>.json \
       --env-python R/envs/<id>/bin/python --receipt R/validation/<job>/receipt.json --root R/campaigns/<name>
   ```
5. **Submit:**
   ```
   python submit.py --spec R/campaigns/<name>/spec.json [--chains ...] [--dry-run]
   ```
   This submits one job per chain and prints the `tail -f` lines. Check the logs about 10 minutes after the jobs
   start.
6. **Monitor:** `python status.py --spec … [--sacct]`. **Collect:** `python collect.py --spec … --out DIR`. Read
   `flags.txt`, which lists thermal jumps, Jacobian conditions above 1e8 (over all attempts), and INVALID records,
   for a human decision.

## Seeds and continuation
- **Main step at L > L0:** seeded from the accepted record of the same chain at L−2.
- **Check step (L, nz):** seeded from the main record at the same L.
- **First step:** a frozen initial seed with a declared origin:
  - `reference_same_L` is a shipped reference record at L0;
  - `teacher_L0m2` is the chain's own basis (teacher) record at L0−2.
- **Validation.** Production predecessors must be accepted envelopes whose configuration matches the frozen step.
- **Failures.** A failed check step is recorded and the ladder continues. A failed main step stops the chain
  (exit 66).

## Stops, continuation, recovery
There are three outcomes after the USR1 at `lead_s` before the wall:
- **Graceful stop.** The point reaches a Newton boundary, writes its checkpoint and exits 75, and the chain exits 75.
- **Completed publication.** The point was already finishing: its record is published and the chain stops with
  exit 75.
- **Wall kill.** The stop arrived inside a long uninterruptible final check or diagnostics. The job is killed at
  the wall and its claims stay fail-closed. The continuation queued by the trap recovers them (sacct-confirmed)
  and resumes from the Newton checkpoint.

- **The USR1 trap** (`--signal=B:USR1@lead_s`):
  - forwards USR1 to the chain, which stops after the running point reaches a Newton boundary (exit 75);
  - submits one continuation (`afterany`; at most `slurm.max_cont`, frozen in the spec).
- **The continuation guard** (`continuation.py`):
  1. requires PREV to be terminal by sacct (UNKNOWN → exit 75);
  2. refuses if another job of the chain is queued;
  3. **always** archives and removes PREV-owned claims;
  4. then reads only PREV's state:
     - `complete` → done, if every record validates;
     - `failed` → stop for a human;
     - `stopped` or missing → resume.
- **Points.** A point whose solve and diagnostics finished while a stop was pending is published, not discarded
  (`stop_requested_at_publication`).
- **Manual recovery** of claims left by a hard-killed job:
  ```
  recover_claims.py --scope R/campaigns/<name>/chains/<chain> [--owner-job ID] [--apply]
  ```
  Dry run is the default. Only claims whose owner job is terminal by sacct are touched.

## Exit codes
| Code | Meaning |
|---|---|
| 0 | done |
| 65 | seed refused |
| 66 | main step failed |
| 73 | chain or point owned by another writer |
| 74 | spec, release or environment verification failed |
| 75 | safe stop or manual check needed (resumable) |
