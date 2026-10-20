# Running the package on symmetry and Expanse

This runbook adds site rules to the package's own workflow (`docs/HPC.md`, `docs/PERFORMANCE_AND_SCALING.md`). It does
not change the science: the native worker, inputs, sampling, campaign tools and assembly are as delivered. Every job
goes through `tools/submit.py`, which applies the site rules and the caps; nothing here is submitted automatically.

## 0. Sites at a glance

| | symmetry | Expanse |
|---|---|---|
| Integration CPU (checked in every task, exit 68 otherwise) | AMD EPYC 7543, `amdq` (cn112 is Intel and excluded) | AMD EPYC 7742, `compute` |
| Node | 64 cores, `--mem=240G`, exclusive | 128 cores, `--mem=240G`, exclusive |
| Lanes per node (default) | 8 lanes x 8 threads | 16 lanes x 8 threads |
| Light jobs (plan, assemble) | `defq` (Intel, 80 CPUs, `--mem=180G`, outside the AMD-pool cap), exclusive | `shared` (plan 4 cores / 16G, assemble 16 / 64G, build 32 / 64G) |
| Never | `longq`, `preq`, `amdpreq`; array jobs | the bad-read nodes <NODE>, <NODE> (excluded); array jobs |
| Node-local scratch | `/local1/$USER/job_<id>` | `/scratch/$USER/job_<id>` |
| Shared root (`C8OPT_ROOT`) | `<SCRATCH>/c8opt` | `<SCRATCH>/temp_project/c8opt` |
| Account | none | `<ACCOUNT>` |

Every job gets `--time`, `--mem`, `--no-requeue` and an output file `$C8OPT_ROOT/logs/c8opt-<role>-<tag>_<job>.out`.

## 1. One-time setup per site

1. Copy the package. On Expanse, avoid a recursive copy of the 32k small files across Lustre (SDSC, 2026-10-07).
   Instead, put the zip or a tar of the package on Lustre and unpack it once on the login node into
   `$C8OPT_ROOT/pkg/`. Then check the copy: `python3 -B tools/delivery.py verify --strict`.
2. Copy `slurm/sites/<site>/env.sh.example` to `~/c8opt/env.sh`, and create the venv as its comment shows.
3. Set the caps in `~/c8opt/env.sh`. **Coexistence with the c8d3 package: one package per site and class.** The c8d3
   submitter does not count `c8opt-` jobs; on Expanse it refuses normal admissions while any foreign job of the user is
   live. So `submit.py` admits nothing while a `c8d3-` job of the same class is live: symmetry's AMD pool, or
   Expanse's compute or shared class. Conversely, **do not submit c8d3 jobs in a class while c8opt jobs of that class are live**: on symmetry (the AMD
   pool) and on Expanse's shared partition the pinned c8d3 tools cannot see c8opt jobs, so this is a procedure, not
   a check. On Expanse's compute class the c8d3 submitter refuses by itself (its foreign-job rule). c8opt also treats
   every unresolved c8d3 submission (a file in the c8d3 root's `intents/`) as occupying its partition's class: a
   c8d3 submission that is still in flight blocks the handoff. A stale c8d3 intent must be resolved with the c8d3
   package's `ledger.py` before c8opt can take that class. Check with
   `squeue -u $USER -n` or `tools/submit.py ledger`. Within a class it holds, c8opt may use the session's DECISIONS
   share.
   - Both sites: `C8OPT_NODE_HOURS_CAP`, the approved node-hour budget.
   - symmetry: `C8OPT_AMD_CAP` and `C8OPT_SESSION_AMD_CAP` (H7 4, or a window's split). They have no default. Add
     `C8OPT_AMD_EXCLUDE_EXTRA` (cnNNN) for nodes later found not to be EPYC 7543.
   - Expanse:
     - compute: own `C8OPT_RUN_CAP`, `C8OPT_SUB_CAP`, `C8OPT_COMPUTE_NODE_CAP`; session 11 / 27 / 4 (H7E-R, H7E);
       the user's 22 running / 54 submitted; the <ACCOUNT> account's 32 running, other users included;
     - shared: own `C8OPT_SHARED_CAP`, session 32.
   - `C8OPT_FOREIGN_SEED_LOGS` names the c8d3 seed log, so its seeds are refused here too.
   - The env file returns at the first failed module, source or venv step. Its last line sets `C8OPT_ENV_COMPLETE`,
     which every job script clears before sourcing and then requires, together with the venv's Python 3.11, numpy
     2.3.5, scipy 1.17.0 and mpmath 1.3.0 (`slurm/site.sh` `c8opt_check_env`).
4. `source ~/c8opt/env.sh; cd $C8OPT_PACKAGE`.

## 2. Build and test on the integration CPU

```bash
python3 -B tools/submit.py build                   # symmetry amdq (one AMD-pool node) / Expanse shared, 2 h
python3 -B tools/submit.py build --partition defq --any-cpu   # symmetry: a test build on Intel, outside the AMD cap
```

`slurm/build.sh` does the following:
- verifies the delivery (`C8OPT_VERIFY_DELIVERY=0` skips it);
- builds `bin/c8d3_optimized`, `c8d3_gmp`, `c8d3_baseline`, `point_checks_gmp`, `c7d3_reference` and
  `test_positive_quad`: in place on the integration CPU, where campaigns pin it. A `--any-cpu` test build compiles
  only in its node-local copy, so the package's `bin/` never holds a binary from another CPU;
- runs the arithmetic, native, point, optimization, dispatch, streaming-assembly, RG, campaign, allocation and
  cluster tests in a node-local copy of the package, so the delivered `verification/` files are not rewritten;
- writes `$C8OPT_ROOT/evidence/build_<job>/summary.json`.

A campaign pins the binary by path and SHA256, so it runs only on the site that built it. Never rebuild over a binary
that a live campaign names: build a fresh package copy instead.

## 3. Plan a campaign (inside a job)

```bash
python3 -B tools/submit.py plan $C8OPT_ROOT/runs/<name> $C8OPT_ROOT/dispatch/<name> --seed <fresh> --lanes <nodes x lanes/node> \
  --plan-args "--purpose production --points 4096 --replicates 16 --threads 8 --graph-block 8 --chunk-points 1024 --allocation <file>" \
  --index-args "--bundle-jobs 4 --statistics results/pilot_20261008/graph_statistics.json --target-core-seconds 1800"
```

- The seed must be fresh. `submit.py` refuses any seed recorded in `$C8OPT_ROOT/seeds.jsonl`, the delivered pilot's
  seed, the documentation's example seeds, and any seed in `C8OPT_FOREIGN_SEED_LOGS`. It reserves the seed before
  sbatch, for good, even if sbatch then fails.
- `--plan-args` and `--index-args` are allow-listed: `--purpose --points --replicates --threads --graph-block
  --chunk-points --loops --allocation` and `--bundle-jobs --max-tasks --statistics --target-core-seconds`. The seed,
  executable, destinations and lane count come only from `submit.py`. Paths may contain spaces. The effective
  argument vectors are recorded in the ledger.
- A campaign meant for assembly must cover loops 3–8: both assemblers require every loop. A smoke test therefore
  plans all loops with few points (e.g. `--points 16 --replicates 4`), not a loop subset.
- The plan job runs `campaign.py plan` (with `--executable $C8OPT_PACKAGE/bin/c8d3_optimized`), which hashes every
  graph payload of the selected loops, and then `hpc_dispatch.py index`.
- Pass `--statistics` so the lanes can estimate bundle times; without it the deadline rule is weaker (section 4).
- Training on the delivered pilot and then excluding it from the estimator is the package's rule (`docs/HPC.md`).

## 4. Run the lanes

```bash
python3 -B tools/submit.py lanes $C8OPT_ROOT/dispatch/<name> --nodes 4 --time 23:30:00     # --dry-run first
```

- Lanes run only on the integration partitions (symmetry `amdq` / `amddebugq`, Expanse `compute`).
- One allocation runs every lane of the index: `srun`, with one task per lane, `--cpu-bind=cores`.
- Each task checks its node's CPU, makes its node-local scratch, and runs `hpc_dispatch.py run --lane $SLURM_PROCID`.

What a lane does (`tools/hpc_dispatch.py`):
- It holds a lease (`<dispatch>/lane_<n>.lease/`). A second live runner of the same lane is refused, and
  `submit.py` refuses a second lane job for the same dispatch.
- Every job lock (`<run>/jobs/<idx>.lock/owner.json`) records its Slurm job, step, task, host and pid.
- Completed jobs are checked first: a fully receipted bundle is complete whatever the deadline.
- Inside Slurm, a job end that squeue cannot report (after retries) defers every bundle; it is re-read before each
  bundle. It never means "no deadline".
- With statistics in the index, a bundle starts only if its unfinished work / threads x 1.5 + 300 s fits before the
  TERM signal. The signal comes `--grace` seconds (exported as `C8OPT_GRACE`) before the job's end. Without
  statistics, a bundle starts only while 300 s remain before the signal (`C8_DEADLINE_FACTOR`, `C8_DEADLINE_PAD`).
- `--signal=TERM@600` (`--grace`) stops the lane 10 minutes before the limit: the running native process is
  terminated, the locks of jobs it did not publish are released, and the lane exits 143.
- A bundle locked by a live owner (busy), a failed native run, or inputs whose checksum still fails after 3
  re-reads (failed) are recorded, and the lane continues. Such a lane exits 3.
- A corrupt published checkpoint, or a changed plan, index or lane file, stops it (fatal).
- Each run writes `<dispatch>/runs/lane_<n>_<job>_<time>_*.json` (completed, deferred, busy, failed, stage retries).

To continue, resubmit the same `lanes` command: completed checkpoints are verified and skipped.

## 5. Stale locks

Every acquisition carries a unique token, and a lock is released only by the acquisition whose token it holds. A
stale lock is reclaimed by renaming it to `<lock>.stale-<owner token>`, a name fixed by the stale record. The
tombstone is kept, so of several contenders acting on the same stale reading exactly one succeeds, and none can
ever move a newer acquisition. Tombstones are small directories: remove them only when no lane of the campaign is
queued or running.

A lock or lease is reclaimed automatically only when its owner record names a Slurm job that `sacct` reports
finished (COMPLETED, FAILED, CANCELLED, TIMEOUT, NODE_FAIL, OUT_OF_MEMORY, PREEMPTED, BOOT_FAIL, DEADLINE), or a local
process that no longer exists on this host. Each reclaim is logged to `jobs/reclaimed_locks.jsonl` or
`<dispatch>/reclaimed_leases.jsonl`.

Never reclaimed automatically:
- a lock of the same allocation;
- an owner whose state is unknown;
- a lock without an owner record: `campaign.py run` writes none (local runs), and a crash between `mkdir` and the
  record leaves none. Inspect such a lock (is any job of this campaign still queued or running?) and only then
  `rmdir` it.

## 6. Assemble

```bash
python3 -B tools/submit.py assemble $C8OPT_ROOT/runs/<name> [--dependency afterok:<lanes job>]
```

`slurm/assemble.sh` runs `campaign.py status` and then `assemble_streaming.py --bootstrap 4096` into new files:
`<run>/C8_result_<job>.json` and `graph_statistics_<job>.json`. The assembler refuses a campaign with any missing or
overlapping work.

## 7. Budget, caps and the ledger

- Admission:
  - it runs under the c8d3 package's session lock (symmetry: `<HOME>/c8d3/locks/c8d3.lock` on the NFS home,
    where flock is seen by every node; Expanse: the c8d3 root's lock on Lustre), so both submitters admit one at a
    time;
  - the queue is read with one row per array element, and a queued job counts as if running;
  - reserved node-hours are nodes x time limit, with the limit rounded up to whole minutes and kept within the
    partition's limit;
  - a shared Expanse job counts the larger of its core and memory fraction of a node.
- Submission:
  - before sbatch, an intent line (unique token, resources, node-hours, seed) is appended to
    `$C8OPT_ROOT/ledger.jsonl` and fsynced; a successful sbatch is followed by an accepted line;
  - an intent without one (a crash, or a failed sbatch) stays reserved, counting against node-hours and, as a queued
    job, against every cap and the duplicate-lane check;
  - it is accepted once squeue or sacct shows its unique job name;
  - it is rejected only by `python3 -B tools/submit.py resolve TOKEN --rejected --reason "..."`, an operator's
    recorded decision, which is refused while squeue or sacct still knows that name. Elapsed time alone never
    releases a reservation;
  - sbatch runs without any inherited `SBATCH_*` or `SLURM_*` variable (except `SLURM_CONF`).
- `python3 -B tools/submit.py ledger` prints the total.
- A production campaign needs, beforehand:
  - the user's approval of its budget (`C8OPT_NODE_HOURS_CAP`);
  - on symmetry, a DECISIONS window or share for its AMD-pool nodes;
  - on Expanse, a share within H7E-R.

## 8. Array mode

The original array mode (`slurm/run_array.sh`) is disabled on both clusters. Its elements would bypass admission, the
ledger and the lock owners, and symmetry's partitions are exclusive whole nodes. Use packed lanes. Locally,
`campaign.py run --workers W --threads T` remains the package's own workflow.
