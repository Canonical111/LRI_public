# Cluster runbook

> Revision 2026-10-02: job-private runtime, status and recovery tooling, one guarded
> submission path with a campaign lock, wall-time policies, cost-proportional
> shards and estimates, opt-in allocation options. See `CHANGELOG.md`. Earlier
> benchmark numbers below are retained records; packaging checks are in
> `delivery/DELIVERY.md`.

## Execution model

A scientific stratum is (campaign, sector, loop, graph, replicate). Its full
power-of-two Sobol net may be partitioned into arbitrary nonoverlapping sample
intervals for execution. The scheduler assigns intervals, not new replicates.
The resulting scientific stream is independent of rank, thread and node IDs.

Twenty groups cover two campaigns x two sectors x loops 3--7. Slurm arrays run
independent shards with OpenMP inside each process. MPI is not required.
There is no shared mutable counter/random stream or central worker-server in
the hot integration path. All filesystem publication is checkpoint-level.

The planner uses a disk-backed SQLite table. Tasks are assigned to shards by
longest-processing-time on estimated cost; each shard gets a frozen position
order `pos` (estimated cost descending, then uid), and a work block is a run of
`--checkpoint-tasks` consecutive positions, so a block holds tasks of similar
cost. `run`, `merge` and `status` all read blocks in `pos` order. Stream
identities do not depend on blocking.

**Block barriers.** Each block is one native process: its graphs load
serially, then OpenMP runs the block's tasks with dynamic scheduling, longest
first, and the process ends when its slowest task ends. Cores idle while the
last tasks of a block finish and during the start-up of the next block. Keep
`--checkpoint-tasks` at least 16 x threads (default 512); `plan` and `run`
refuse threads > checkpoint_tasks and warn below 16 x threads. Larger blocks
lose more work on an interruption (one block per job at most).

**Job-private runtime.** `run` copies the plan's executable, `gamma_d2_7.txt` and
the group's Sobol net into a mode-0700 directory under `--scratch`, else
`$SLURM_TMPDIR`, else `$TMPDIR`, else `/tmp`; it verifies every copy against the
plan and runs only the copies. Each block's graph members are read from the
shared pack, hash-checked and staged there. The directory is removed also after
errors. Rebuilding `bin/` during a campaign cannot leak into it: a changed
executable fails the copy check. Each checkpoint records
`runtime = {executable_sha256, inputs_manifest_sha256, net_sha256, fingerprint}`;
the fingerprint is the node's host name, CPU model, glibc, `ld.so` and every
library `ldd` resolves (with sha256), libgmp, libquadmath and libgomp included.
`merge` and `assemble` need neither `bin/` nor the native toolchain.

## Build and pin the environment

Use one environment file for building and for every job, passed to the Slurm
scripts as `C7_ENV_SETUP` (sourced with errexit on, before nounset).
`slurm/env.sh.example` has verified lines for symmetry (system GCC 11.4,
`module load boost/1.77.0 python/3.11`, system GMP 6.2.1, a venv) and for an
Expanse-type Spack stack. `make` builds the 300-digit backend, `make gmp` the
opt-in 350-digit one; each writes `bin/<exe>.build.json` (compiler, flags, Boost
and GMP versions, sha256), which `plan` records. Check its `BOOST_LIB_VERSION`:
a module that sets only `BOOST_ROOT` (Expanse's `boost/1.86.0`) leaves the
compiler on the system Boost in `/usr/include` unless you add
`CPATH=$BOOST_ROOT/include` (see `slurm/env.sh.example` and `docs/NUMERICS.md`).
Run `make test` and `make test-full` on the target nodes before a long
campaign (`benchmarks/symmetry_2026-10/` has the symmetry records). Do not change the
compiler, flags or module stack during a run; new executable bytes require a new
plan. `status` lists the distinct library fingerprints per group.

## Plan

```bash
export C7_PACKAGE=/path/to/LRI_C7_D2_HPC
export C7_RUN=<SCRATCH>/c7-d2/run1          # a SHARED filesystem; never node-local
source "$C7_ENV_SETUP"
python3 tools/production.py plan "$C7_RUN" \
  --seed <FRESH_RANDOM_SEED> --backend gmp --replicates 64 --multiplier 4 \
  --primitive-mode recompute --primitive-points 16384 \
  --shards 32 --threads 32 --checkpoint-tasks 1024 --chunk-points 65536
```

Use a fresh random seed for every campaign (never one from documentation).
`plan` verifies every file in `inputs/manifest.json` (the ten packs included)
before creating anything, refuses invalid sizes and infeasible allocation
options, and prints:
- estimated core-hours per group and in total;
- the largest shard's wall time at `--threads` (assuming 80% busy cores) and a
  suggested `--time` (3 x the largest shard, at least 15 minutes);
- the effect of `--power-divisor`, the primitive points per replicate the plan
  really uses and their projected primitive-block SE, and, for uniform or Neyman
  plans, the other allocation at the same budget, labelled hypothetical
  (projections; under `--points` only the override is shown).

**Shards.** `--shards N` is the shard count of the most expensive group; every
other group gets `max(1, round(N x s_g / s_max))`, with `s_g` its estimated
core-seconds, so shards of every group run similarly long (`--shard-policy
uniform` keeps N everywhere). A group with no tasks (e.g. free L7 in
`--primitive-mode retained --test-graphs 1`) gets no work jobs, zero estimates
and still a merged zero-contribution record.

**Estimates.** Without `--cost-model` the task cost is the inventory proxy cost
per point (max(1, terms x monomials)) times points, in proxy units; core-hours
use `tools/calibration.json`, seconds per proxy unit per (backend, sector, L).
Both backends are measured on symmetry's AMD nodes at 64 threads; every row lists
its Slurm job ids, hosts, threads and CPU models:
- `gmp`: the 2026-09-30 production (M=4096, R=64; jobs 566259-566272) on 14 nodes,
  <NODE>-<NODE> (AMD EPYC 7532) and <NODE>-<NODE> (AMD EPYC 7543);
- `decimal`: every job of a small plan (M=16, R=8, one shard per group; job 567667
  on <NODE>, AMD EPYC 7543; `benchmarks/symmetry_2026-10/`).

The backend comparison comes from matched hardware: job 567730 ran the same
M=16 plan (same seed and jobs) with gmp on <NODE> (AMD EPYC 7543). Per proxy unit
decimal costs 0.82-1.14x gmp up to L6 except power L5 (1.30x) and power L6
(1.67x), and 1.29x (free L7) and 2.00x (power L7) at seven loops. That gmp run
agrees with the mixed-hardware production rows within 4% for L >= 6 and within
11% everywhere (`benchmarks/symmetry_2026-10/backend_ratio/`).

A backend or (sector, L) without a row prints and records `estimate: unavailable`
(never another backend's number), and its shard sizes use uncalibrated proxy
units. One rate per (sector, L) is a planning approximation: the free-L7 row
blends the primitive classes (about 1.1e-8 s per unit in the production) with the
non-primitive ones (about 5.3e-9) at the production's primitive share, so free-L7
estimates are biased (by up to about 30%) when `--primitive-points` or
`--primitive-allocation` changes that share; the 3x suggested `--time` absorbs it.
To measure a backend or new hardware, run real shards of a small plan at every
(sector, L) and merge the measurement into a copy of the file:

```bash
python3 tools/calibrate.py "$CALIB_RUN" --threads 64 --host-regex 'cn(079|08[0-9]|09[0-9]|10[0-9]|110)' \
  --update calibration.json --note '<backend>: <node type>, job <id>'
```

`calibrate.py` refuses a selection (host pattern, thread count) that misses any
(sector, L) of the run, and drops a backend's `unavailable` note only when all ten
of its rows are filled.

With `--cost-model` (from `tools/make_cost_model.py` on an independent pilot of the
same backend and hardware) the cost column is already in seconds and no
calibration factor applies; the manifest records which path was used. The cost
model affects placement and estimates only, never sample counts or estimator
weights.

## Submit, monitor, recover

```bash
export C7_ENV_SETUP=/path/to/env.sh
export C7_SBATCH_ARGS="-p amdq"            # site options; allowlisted (account, partition, qos, constraint, mem, time, ...)
slurm/submit.sh                            # extra arguments: allowlisted sbatch options for the work arrays
python3 tools/production.py status "$C7_RUN"           # add --json, --exclude IDS, --max-array N
slurm/resubmit.sh                          # recovery
```

`slurm/submit.sh` submits work arrays of at most `C7_MAX_ARRAY` elements (default
1000) with their own `C7_INDEX_OFFSET` and at most `C7_THROTTLE` running
elements (default 64), then `slurm/merge.sh` with an `afterok` dependency on all
of them. Logs go to `$C7_RUN/slurm_logs/` (a `%` in the path is escaped). Every
job carries the Slurm comment `<tag>:off=<offset>` or `<tag>:merge`, where the
tag (`production.py tag`) is derived from the campaign path and manifest.

Every submission goes through `tools/slurm_submit.py`, which:
- checks `C7_SBATCH_ARGS` and the extra options separately against an
  exact-spelling allowlist (array, dependency, export, comment, output and
  cluster options are refused: the tool owns them);
- refuses inherited cluster selectors (`SBATCH_CLUSTERS`, `SLURM_CLUSTERS`,
  `SQUEUE_CLUSTERS`). Of the other inherited `SBATCH_*` variables it keeps only
  `SBATCH_ACCOUNT`, `SBATCH_PARTITION`, `SBATCH_QOS`, `SBATCH_RESERVATION`,
  `SBATCH_CONSTRAINT`, `SBATCH_MEM_PER_CPU`, `SBATCH_MEM_PER_NODE`,
  `SBATCH_WCKEY`, `SBATCH_REQUEUE` and `SBATCH_NO_REQUEUE` (they still apply, so
  unset them or override them in `C7_SBATCH_ARGS`), and removes every other
  `SBATCH_*` and all `SQUEUE_*` inputs;
- refuses (64) when a pinned tool differs from the plan, because the work and
  merge jobs would refuse it (after a deliberate post-processing fix, merge and
  assemble by hand with `--accept-tool-change`);
- builds argument lists without shell splicing, and sets `C7_RUN`, `C7_PACKAGE`
  and the offset in sbatch's own environment;
- holds the campaign lock `$C7_RUN/.c7_submit.lock` (atomic `mkdir`, with an
  `owner.json`) from the queue snapshot through the last `sbatch`. A second
  submission meanwhile exits 75 and submits nothing. A lock left by a killed
  process is never broken automatically: check `owner.json`, then remove it;
- takes a complete `squeue` snapshot of the campaign first, for the account of the
  process's real uid (the identity sbatch submits under; never `USER`/`LOGNAME`, so a
  stale or foreign `USER` cannot hide live jobs), so no entry point
  duplicates live work: `submit` refuses (65) if any work or merge job of the
  campaign is live; `submit.sh --window` refuses (65) if an index of its window
  or a merge is live; `resubmit` refuses (65) while a merge is live and never
  resubmits a live index. Indices whose blocks are all committed are skipped;
  if nothing remains, nothing is submitted (exit 0). Completing, preempted or
  unknown states, or a failed `squeue`, refuse with 69: rerun later.

`status` prints committed/total blocks per job index and group, the library
fingerprints per group, and for missing indices ready-to-run lines of the form
`C7_MAX_ARRAY=<n> C7_RUN=... C7_PACKAGE=... slurm/submit.sh --window O:ARRAY`
(they bind the campaign and package, so a shell with stale variables reruns the
right indices). `--all` also lists complete job indices, `--json` gives the same
report (with `tool_changes`) for scripts, and a changed pinned tool is printed as a
warning. It exits 0 only when every block is committed.

`slurm/resubmit.sh` is the recovery: it resubmits every missing index that is not
live and a merge that waits (`afterok`) for those arrays and for every live
element. With nothing missing it submits a merge only. If a work element fails,
the pending merge stays pending forever (afterok): `scancel` it, then run
`resubmit.sh`. Exit codes: 64 invalid input, 65 live merge or work, 69
uncertain state, 70 wall-time verification failed, 75 lock held.

`run` without `--index` refuses outside a Slurm array; inside one the index is
`C7_INDEX_OFFSET + SLURM_ARRAY_TASK_ID` (the old `C7_ARRAY_OFFSET` is not used).
A run that finds a block already published by another process checks that the
scientific rows are identical and logs `verified duplicate`. There is no
per-block lock; the submission lock and the queue checks prevent duplicate
submissions. `run --max-blocks N` commits at most N new blocks and stops (time
slicing by hand; a later run resumes). On SIGTERM (scancel, time limit), SIGINT or SIGHUP, `run` stops the native
worker, removes its job-private runtime and exits 128+signal (143); a signal that arrives while a native worker is
being launched is deferred until the worker is registered, so it is always stopped and reaped. `run_array.sh`
forwards the signal to every background job (also one launched an instant before) and removes
its staging directory. The block in progress is simply redone by the next run (checkpoints are published
atomically). SIGKILL, a node failure or an expired Slurm KillWait cannot be cleaned up: leftovers are directories
named `c7d2_runtime_*`/`c7d2_stage_*` under the scratch directory, safe to delete when no job of the campaign runs. Published files (checkpoints, merged
records, results, manifests) get mode 0666 minus the umask, i.e. 0644 under the
usual umask 022, readable by other users of a shared filesystem; set a stricter
umask (e.g. 077) in `C7_ENV_SETUP` if that is not wanted.

### Wall-time policy

`C7_TIME_POLICY` selects how jobs get their wall time:
- `finite` (default): work arrays get the plan's suggested time, the merge
  `02:00:00`; a `--time`/`-t` in `C7_SBATCH_ARGS` or the extra options overrides
  both. A plan without an estimate (uncalibrated backend) needs an explicit
  `--time`. Use it on symmetry, personal desktop and Expanse-type sites, whose partitions
  have finite limits.
- `unlimited`: every job is submitted with `--time=0` as its last option; any
  other `--time` is refused (64). After each `sbatch`, `scontrol show job` must
  report `TimeLimit=UNLIMITED`, otherwise the tool reports the mismatch and
  exits 70 without cancelling anything (job management stays with the user).
  Required on a personal desktop, personal desktop and canonical, whose rule is no wall-time cap.

### Templates

`slurm/run_array.sh` and `slurm/merge.sh` set `--nodes=1 --ntasks=1` (Expanse's
shared partition rejects jobs without them), run with `set -eo pipefail`, source
`C7_ENV_SETUP` before `set -u`, check Python >= 3.10, export `OMP_NUM_THREADS`
from `SLURM_CPUS_PER_TASK` with `OMP_PLACES=cores OMP_PROC_BIND=close`, and pass
`--scratch` from `SLURM_TMPDIR` (else `TMPDIR`, else `/tmp`). Account and
partition go in `C7_SBATCH_ARGS` (examples are commented in the scripts).
`C7_STAGE=1` makes a work element run from a verified node-local copy of the
tools, inputs, executable and its group's pack (`tools/stage_runtime.py`),
removed at exit; only worthwhile when the pack is reused by much work.

## Merge and assembly

`slurm/merge.sh` runs `status` (exit 65 if incomplete), `merge` and
`assemble.py --bootstrap $C7_BOOTSTRAP` (default 4096). It is safe to resubmit:
groups whose `merged.json` fully validates are skipped, an invalid one is never
overwritten, two merges racing on a group are accepted only if their records are
canonically identical, and an identical `C7_result.json` is kept. Each group can
be merged on its own with `merge --group NAME`. A plan made with `--test-graphs`
writes `C7_test_result.json`.

`merge` and `assemble` verify the pinned tool hashes; after a deliberate fix of a
post-processing tool, `--accept-tool-change` lets them proceed and records the
planned and current hashes in `merged.json`/`C7_result.json`. `run` always
refuses a changed tool. Campaigns planned by the delivered tools (schema
`c7-d2-production-1`) are handled only by a checkout of `fb64c47`.

## Allocation: measured shares and the opt-in options

The 2026 symmetry production (M=4096, R=64, gmp, recompute primitives at
16384 points; 8,892 task core-hours on 64-thread AMD and 20-thread Intel lanes;
C7 SE 0.524) spent:

| Part | Task CPU | Share of Var(C7) |
|---|---:|---:|
| power sector (L3-L7) | 59.9% (L7 alone 48.3%) | 0.76% |
| 44 seven-loop primitive classes | 14.4% | 7.4e-5 (primitive SE 0.0045) |
| free non-primitive strata | 25.7% | 99.2% |

CPU shares are sums of per-task native seconds over the run's checkpoints;
variance shares are the per-sector, per-loop contributions (`error_by_loop`)
of its `C7_result.json`, and for the primitive block the replicate scatter of
its classes in `groups/{a,b}_free_L7/graph_replicates.csv` (the same method
reproduces the free-L7 SE 0.51869). Script and output:
`benchmarks/symmetry_2026-10/production_shares.{py,json}`. The review had
estimated about 55% and 0.5% for the power sector and 12-27% for the
primitives; the archived-variance projection of the primitive share (SE 0.0064)
is about twice the measured one.

Two opt-in plan options change only the allocation, never the integrand or the
estimator (every stratum stays an independent stratum):
- `--power-divisor K` divides every power-sector count by K (after
  `--multiplier` and `--power-multiplier`; floor 4). `plan` refuses a K that would
  take a stratum below 4 and names it.
- `--primitive-allocation neyman` splits the primitive budget
  `primitive_points x M x 44` as n_g ~ sd_g / sqrt(c_g) from the frozen table
  `inputs/primitive_allocation_c7d2.json`, rounded to powers of two; budgets with
  primitive_points x M < 64 are refused. `--points` still overrides it, and
  `--primitive-mode retained` ignores it.

Projections by MC scaling from the measured shares (not measurements), at M=4096
and R=64 (power variance x K and cost / K; primitive cost and variance scaled by
the frozen table); the last column is the core-hours needed for the production's
SE 0.524:

| Plan | Core-hours | C7 SE | SE x sqrt(core-hours) | Core-hours at SE 0.524 |
|---|---:|---:|---:|---:|
| 2026 production (measured) | 8,892 | 0.524 | 49.5 | 8,892 |
| `--primitive-allocation neyman` (budget unchanged) | 8,716 | 0.524 | 49.0 | 8,715 |
| `--power-divisor 16` | 3,895 | 0.554 | 34.6 | 4,342 |
| `--power-divisor 16 --primitive-allocation neyman` (the plan's recipe) | 3,719 | 0.554 | 33.8 | 4,145 |
| `--power-divisor 16 --primitive-points 512` (uniform) | 2,656 | 0.554 | 28.6 | 2,967 |
| `--power-divisor 16 --primitive-allocation neyman --primitive-points 512` | 2,650 | 0.554 | 28.5 | 2,959 |

**Recommended efficient recipe:** `--power-divisor 16 --primitive-allocation neyman
--primitive-points 512`: a given SE with about one third of the core-hours
(`--power-divisor 16` alone: one half). The primitive saving comes from the
smaller primitive budget; Neyman adds under 1% there. At an unchanged budget
Neyman cuts the primitive cost by about 14% and its projected primitive SE from
0.0064 to 0.0056. The power correction's own SE grows by sqrt(16) = 4.
`plan` prints its own core-hour estimate from `tools/calibration.json`; with a
changed primitive share it differs from these projections (see Estimates).

## Memory and filesystem behaviour

Kernel packs replace thousands of independent shared-filesystem graph opens with
indexed reads from one pack per sector/loop. Per-block staging reads and hashes
only required members and materializes their unchanged text in the job-private
directory. No entire pack is loaded into Python RAM. The largest pack is about
207 MiB (seven-loop power-free).

Default memory is bounded by the native task block, its distinct graphs,
per-thread arithmetic scratch and a small task result array. Growth in point
count increases runtime and checkpoint/disk output, not a stored point array.
Within a graph, exact importance tables still require O(2^(2L)) entries; the
code is supported through L=7. Planning/merging use an 8 MiB SQLite cache plus
Python graph/group metadata and the final O(replicates x jet_width) arrays.

The checkpoint, merge and lock protocols use POSIX hard links and atomic
`mkdir` on the campaign's shared filesystem. Hard-link publication ran on
symmetry's BeeGFS in the 2026 production (and on Expanse Lustre in the C6
campaigns); the submission lock and concurrent merges are exercised there by the
validation drills. It is not an object-store protocol.

## Tune on the actual cluster

1. Run `tools/profile.py --output /scratch/profile-new` and
   `tools/benchmark.py --output /scratch/benchmark-new` (fixed graph subsets,
   matched original/optimized samples, compiled with the Makefile's flags).
2. One process per node or NUMA domain, `OMP_PROC_BIND=close`, `OMP_PLACES=cores`,
   no BLAS oversubscription. Compare thread counts on the target nodes.
3. Choose chunk sizes so graph loading and process start-up are small against
   integration, and `--checkpoint-tasks` >= 16 x threads.
4. Measure a pilot's per-graph costs for shard balance:

```bash
python3 tools/make_cost_model.py /scratch/completed-pilot /scratch/costs.json
python3 tools/production.py plan /scratch/new-run --seed <FRESH_RANDOM_SEED> \
  --backend gmp --replicates 64 --multiplier 4 --cost-model /scratch/costs.json
```

Freeze new sample allocations from independent pilots rather than adapting
production counts to final outputs. Keep a pilot independent of production.

## Remaining limits

There is no global runtime work-stealing across nodes; the slowest shard still
determines completion. Tasks and checkpoints grow with total samples at fixed
chunk size. Final shard sorting/merging is disk-backed, not O(1) disk. The
arithmetic fallback can still be costly at rare severe cancellations. There is
no separate L3-L5 control mode (finding L20): the L3-L5 groups can be merged
early with `merge --group` and their coefficients computed with
`assemble.coefficients` on loops 3-5 by hand.

Official Slurm array documentation:
https://slurm.schedmd.com/job_array.html
