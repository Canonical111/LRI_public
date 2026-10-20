# Changelog

## 2026-09-28 — Expanse readiness

This revision fixes the findings of the 2026-09-28 review (`LRI_C6_D2_HPC_review/REVIEW.md`, IDs M1–M3, L1–L19),
following a plan approved by an independent Codex review. The physics is unchanged:
- the integrand, precision thresholds and fallbacks;
- the Sobol construction for a given (seed, net);
- the fixed-point assembly and the campaign weights.

With GCC 13.3, the production binary built from this revision is byte-identical to the one built from the delivered
sources.

### Integrity
- **Job-private runtime (M1).** Every `run` copies the executable and exactly the inputs its shard needs into a
  job-private 0700 directory, verifies every copy against the plan, and runs only those copies. Checkpoints record
  the digests of the executable that actually ran and of the inputs manifest (`runtime`). Restart and merge reject
  checkpoints from another executable, input set or plan. Rebuilding inside a campaign can no longer mix binaries
  silently. The group's Sobol net is staged the same way: native calls read only the verified private copy, and
  checkpoints record its digest (`runtime.net_sha256`).
- **Assembly inputs (M2).** Assembly verifies `inputs/two_loop.json` (B2) and `inputs/primitive_reference.json`
  (P10) against the inputs manifest frozen by the plan before using them, and records their digests in
  `C6_result.json` (schema `c6-d2-hpc-result-2`).
- **Idempotent final result.** `C6_result.json` is published idempotently: an existing identical result is kept, a
  different one is an error.
- **File modes (L16).** Published files respect the umask (0644 under umask 022), and `inputs/` is 0644.
- **Input provenance (L17).** `inputs/manifest.json` (schema `c6-d2-inputs-2`) records the path and digest of every
  source file. `two_loop.json` and `primitive_reference.json` carry their source digests.
  `tests/check_inputs.py` requires byte-identical regeneration.

### Throughput (M3, L7)
- **Block order.** Checkpoint blocks follow a frozen per-shard position in estimated-cost-descending order, so each
  OpenMP barrier idles few threads. Shard and position assignment stream from SQLite in bounded batches, so Python
  memory does not grow with the number of tasks.
- **Block size.** Default `--checkpoint-tasks` is 256. `run` refuses more threads than tasks per block and warns
  below 16 tasks per thread.
- **Shard sizing.** `--shards` is the shard count of the most expensive group; cheaper groups get proportionally
  fewer (`--shard-policy uniform` restores the old behaviour).
- **Estimates.** `plan` prints and records estimated core-hours, the largest shard wall time and a suggested
  `--time`, from a calibration measured on Expanse.

### Operations on Expanse (L1–L6)
- **Slurm templates.** `slurm/run_array.sh` and `slurm/merge.sh`:
  - set `--nodes=1 --ntasks=1`, which Expanse's `bank_limit` plugin requires;
  - source an optional `C6_ENV_SETUP` before `set -u`;
  - check Python >= 3.10;
  - support `C6_INDEX_OFFSET`.
- **Submission.** `slurm/submit.sh` splits arrays at `C6_MAX_ARRAY` (default 1000) with offsets and submits the
  afterok merge. `slurm/expanse_env.sh.example` gives the verified modules.
- **Paths.** Examples use the shared Lustre tier for campaign directories; node-local storage is used only for
  scratch.
- **Resumable merge.** Groups already merged are validated and skipped; an invalid existing `merged.json` is an
  error. `merge.sh` can be resubmitted.
- **Status and recovery.**
  - `production.py status` reports committed/total blocks and lists incomplete job indices with complete `sbatch`
    lines (tag, throttle, offset, plan CPUs and time). `--json` serves scripts, and `--max-array` must be positive. It
    exits 0 only when complete.
  - `slurm/resubmit.sh` resubmits exactly the missing indices that are not live, plus a merge that waits on the new
    arrays and on every live element. The decision comes from the pure `production.py recover`: a complete squeue
    snapshot (`--all --states=all -r`, inherited `SQUEUE_*` cleared), campaign tags that include the resolved
    campaign path (`production.py tag`), explicit live, terminal and uncertain state classes, and refusals for live
    merges (65) and for completing, preempted or unknown states or a failed query (69).
  - Every submission goes through one guarded path, `tools/slurm_submit.py`: `submit.sh`, `resubmit.sh`, and the
    `status` lines, which call `submit.sh --window OFFSET:ARRAY`. It sources nothing itself; the wrappers source
    `C6_ENV_SETUP`. It:
    - checks `C6_SBATCH_ARGS` and extra arguments separately against an exact-spelling sbatch-option allowlist;
    - validates `C6_MAX_ARRAY` and `C6_THROTTLE`;
    - refuses cluster selectors;
    - removes non-allowlisted `SBATCH_*` inputs;
    - builds argument lists without shell splicing;
    - sets `C6_RUN`, `C6_PACKAGE` and the window offset in `sbatch`'s own environment, since `--export=ALL` would
      otherwise let inherited values win.
    CPUs and wall time default to the plan.
  - Unit tests cover `recover` directly, and both scripts against fake `squeue`/`sbatch`.
  - `merge.sh` writes no files into the working directory. `run --max-blocks` supports time slicing.
- **No prebuilt binary.** The Debian-built binary is no longer shipped. `plan` runs the executable on a self-test
  task before freezing its hash, and refuses a binary that does not run.

### Tests and evidence (L8–L15)
- **Archived assembly (L8).** `tests/archived_assembly.py`: the new `assemble.combine` reproduces the archived
  fresh-only and per-campaign results. `assemble.py` is split into `load_campaign`, `verified_inputs` and a pure
  `combine`.
- **Portable reassembly (L9).** `tools/reassemble_reference.py` compares at relative 1e-12 (it failed bitwise on
  other NumPy builds), records the differences, and states that it runs the archived analysis code.
- **Precision tiers (L10).**
  - `tests/force_levels.py` compares the binary128 and 300-digit tiers with the original, with promotion forced in
    both codes (test-only `C6_FORCE_LEVEL` hook).
  - `tests/check_points.py` now compares long-double strings by relative error (<= 1e-9); the old `max(1,|ref|)`
    check was vacuous for scaled points.
    - It found one point beyond the 300-digit tier's resolution: L6G160 with edge variables at 1e-130 has a
      395-digit cancellation. The kernel returns noise of 2.3e-321 A (A = forest-term magnitude).
    - That point, and only that point, is an explicit exception. The test requires it to be level 2, deeper than 300
      digits, with |value| <= 1e-290 A, and identical to the ORIGINAL code's value at the same point.
    - The plan's strict criterion ("relative 1e-9 for every check") is therefore not met for this one point.
      Changing the kernel instead would break the frozen-numerics rule. See docs/NUMERICS.md.
- **Real-worker workflow (L11).** `tests/workflow.py` adds:
  - restart with another thread count;
  - concurrent duplicate runs;
  - a forced native failure;
  - a foreign-plan checkpoint;
  - interrupted vs uninterrupted runs;
  - resumable merge and idempotent assembly;
  - the private runtime;
  - runtime and identity tampering.
- **New test suites.**
  - `tests/unit_orchestration.py` covers the orchestration with a fake worker and needs no build (`make test-python`).
  - `tests/e2e_reference.py` compares the original binary with the whole pipeline.
  - `tests/archived_replay.py` checks the legacy seed scheme against the archived net.
- **Evidence (L12).** Tests and benchmarks never write into `benchmarks/`. `benchmark.py` requires a new `--output`
  directory and rebuilds its baseline there.
- **Benchmark (L13, L14).** `benchmark.py` reads the cgroup quota only if present (v2 or v1) and records the full
  `CXX` invocation and its version (e.g. `ccache g++`). `docs/PERFORMANCE.md`
  labels the older records and adds integration-only speedups; new Expanse records are in `benchmarks/expanse_2026-09/`.
- **Build flags (L15).** The Makefile keeps `CXXFLAGS` user-adjustable but always appends (`override`)
  `-fopenmp -ffp-contract=off -fno-fast-math`. Python compile helpers honour `CXX`, `CPPFLAGS` and `CXXFLAGS` plus
  the required flags.
- **Checksums.** `tools/checksums.py write|verify` maintains `SHA256SUMS_HPC.json`.

### Statistics and planning (L18, L19)
- **Primitive allocation.** Recompute mode splits the primitive budget by a frozen Neyman table
  (`inputs/primitive_allocation_d2.json`, from archived paired d2 L6 records). The split uses powers of two, stays
  within 1.1× the uniform cost, and has about 1.4× lower projected variance. `plan` records a projected
  primitive-block SE and warns above the retained input's 0.041. `--primitive-allocation uniform` restores the equal
  split; `--points` still overrides every stratum. Budgets below 4 points per primitive are rejected in recompute
  mode for both allocation strategies.
- **Seeds.** Group seeds are SHA-256 functions of (seed, campaign, loop, role) by default (`--seed-scheme hashed`).
  The archived arithmetic (`--seed-scheme legacy`) refuses the archived production base seeds. The manifest records
  the scheme.
- **Schemas.** Manifest schema `c6-d2-production-2` and group schema `c6-d2-group-2`. Plans made by older tools are
  refused; re-plan them.
