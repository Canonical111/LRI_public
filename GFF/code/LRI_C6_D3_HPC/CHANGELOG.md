# Changelog

## 2026-09-28 — Expanse readiness

This revision acts on the 2026-09-28 review (`LRI_C6_D3_HPC_review/REVIEW.md`), following a plan approved by an
independent Codex review. It ports the reviewed, Expanse-validated orchestration of the C6(2) package (its findings
M1–M3 and L1–L19 apply to this package, which was ported from the same delivered code) and fixes the d=3 findings
D3-1…D3-6. The physics is unchanged:
- the d=3 integrand, precision thresholds and fallbacks;
- the Sobol construction for a given (seed, net);
- the frozen allocation, the fixed-point assembly and the campaign weights.

With GCC 13.3, the production binary built from this revision is byte-identical to the one built from the delivered
sources. `provenance/d3_fix_port.diff` records this revision relative to the final C6(2) code (6aaf656).

### Integrity
- **Job-private runtime (M1).** Every `run` copies the executable, the Sobol net and exactly the inputs its shard
  needs into a job-private 0700 directory, verifies every copy against the plan, and runs only those copies.
  Checkpoints record the digests of the executable, inputs manifest and net that actually ran (`runtime`); restart
  and merge reject checkpoints from another executable, input set, net or plan.
- **Assembly input (M2).** `assemble` verifies the inputs manifest against the plan and `inputs/two_loop.json` (B2,
  d=3) against the manifest before loading it (no unverified import-time load remains), and records both digests in
  `C6_result.json` (schema `c6-d3-hpc-result-2`). Merge and assembly no longer need the native binary.
- **Idempotent final result.** `C6_result.json` is published idempotently: an existing identical result is kept, a
  different one is an error.
- **File modes (L16).** Published files respect the umask (0644 under umask 022), and `inputs/` is 0644.
- **Input regeneration (L17).** `prepare_inputs.prepare(dest)` regenerates `inputs/`; `tests/check_inputs.py`
  requires byte identity with the shipped tree (unchanged, schema `c6-d3-inputs-1`).

### Throughput (M3, L7)
- **Block order and size.** Checkpoint blocks follow a frozen per-shard position in estimated-cost-descending order.
  Default `--checkpoint-tasks` is 256. `run` refuses more threads than tasks per block and warns below 16 per thread.
- **Shard sizing.** `--shards` is the shard count of the most expensive group; cheaper groups get proportionally fewer
  by estimated seconds (cost x per-loop calibration) (`--shard-policy uniform` restores equal counts).
- **Estimates.** `plan` prints and records estimated core-hours, the largest shard wall time, a suggested `--time`
  (from a calibration of the d=3 worker measured on Expanse) and the projected C6(3) sampling SE.

### Operations on Expanse (L1–L6)
- **Slurm templates.** `slurm/run_array.sh` and `slurm/merge.sh` set `--nodes=1 --ntasks=1`, source an optional
  `C6_ENV_SETUP` before `set -u`, check Python >= 3.10 and support `C6_INDEX_OFFSET`.
- **Submission and recovery.** `slurm/submit.sh`, `slurm/resubmit.sh` and the `status` lines (`submit.sh --window
  OFFSET:ARRAY`) all go through one guarded module, `tools/slurm_submit.py`:
  - separate exact-spelling sbatch-option allowlists for `C6_SBATCH_ARGS` and extra arguments;
  - validated `C6_MAX_ARRAY`/`C6_THROTTLE`; refused cluster selectors; filtered `SBATCH_*`/`SQUEUE_*` inputs;
  - argument lists without shell splicing; campaign, package and window offset set in `sbatch`'s own environment;
  - **one submission at a time per campaign** (plan review R1): an atomic lock directory `$C6_RUN/.c6_submit.lock`
    held from before the recovery queue snapshot through the last `sbatch`; a second call exits 75.
  The recovery decision is the pure `production.py recover` (complete squeue snapshot, campaign tags, explicit live,
  terminal and uncertain states, refusals 65 and 69). `status` exits 0 only when complete.
- **Resumable, concurrent-safe merge.** Groups already merged are validated and skipped; an invalid existing
  `merged.json` is an error; a concurrently published identical `merged.json` is accepted (plan review R1).
- **Campaign paths (plan review R2).** SQLite read-only opens use percent-encoded `file:` URIs, so `#`, `?`, `%` and
  spaces in a campaign path work.
- **No silent index 0.** `run` without `--index` outside a Slurm array refuses.
- **Plan self-test.** `plan` runs the executable on a d=3 self-test task before freezing its hash.

### Seeds and allocation (D3-1, D3-2, L19)
- **Seeds.** Group seeds are SHA-256 functions of (seed, campaign, loop, role) with domain `c6-d3` by default. The
  archived arithmetic stays available as `--seed-scheme legacy`, which refuses every archived base seed: both
  production plans (including the previous prod_a/prod_b 2609832058 and 7406804278) and every archived d=3 record.
  `tests/archived_replay.py` shows the legacy scheme regenerates the archived new_a L6 net byte for byte.
- **Allocation.** `--primitive-points` is removed: every stratum, primitives included, keeps the frozen
  variance-based production allocation times `--multiplier`; `--points` still overrides every stratum for tests.
  The docs no longer call this a pilot allocation.

### Tests and evidence (L8–L15, D3-3, D3-4)
- **Archived-stream replay (new).** `make test-replay` replays the eight archived fresh d=3 production streams and
  reproduces the published fresh-only C6(3).
- **Archived assembly (L8).** `tests/archived_assembly.py` reproduces the archived fresh-only, previous, per-campaign
  and four-campaign d=3 results with the new `assemble.combine`.
- **Portable reassembly (L9).** `reassemble_reference.py` compares to relative 1e-12 and records bitwise identity.
- **Precision tiers (L10).** `tests/check_points.py` uses a relative criterion, with the single listed exception
  L6G160 at 1e-130 beyond the 300-digit tier (identical to the original code; see `docs/NUMERICS.md`).
  `tests/force_levels.py` forces binary128 and 300-digit evaluation in both codes.
- **Conventions (D3-3).** `tests/dimension_checks.py` also checks all five B2 entries against the independent 85-digit
  two-loop record, C0/C1 in closed form, C2 against the archived value, and the lower-order constants against the
  archived literals.
- **Workflow (L11).** `tests/workflow.py` covers restart, concurrent duplicates, forced failure, foreign-plan and
  tampered checkpoints, interrupted runs, resumable merge, idempotent assembly, node-local staging and a campaign path
  with URI-reserved characters. `tests/unit_orchestration.py` tests the orchestration with a fake worker and fake
  `squeue`/`sbatch`, including the submission lock.
- **End to end.** `tests/e2e_reference.py`: the original d=3 binary against the complete plan/run/merge pipeline.
- **Evidence (L12).** Tests and benchmarks write only to temporary directories or an explicit `--output`.
- **Portability (L13, L15).** `benchmark.py` reads the CPU quota only if a cgroup file exists. Test builds use
  `CXX`/`CPPFLAGS`/`CXXFLAGS` plus the non-droppable numerical flags; the Makefile appends them the same way.
- **Checksums.** `tools/checksums.py write|verify` maintains `SHA256SUMS_HPC.json` (format unchanged).
  `make check-delivery` (`checksums.py verify --strict`) and `tools/check_delivery.py` fail on a missing or changed
  listed file and on any package file the manifest does not list.
