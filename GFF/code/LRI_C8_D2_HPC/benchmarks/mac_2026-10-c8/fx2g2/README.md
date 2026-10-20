# Stage-6 fix round 2, group G2: launches, identities, sweeps (2026-10-06)

Branch `fx2-g2` from 2ae3db7 (the tree inspected in round 2), on the Mac (arm64, anaconda Python 3.10.11, numpy
1.23.5, scipy 1.10.0), `C8_ALLOW_NO_L8=1`. Items Y2, Y6, Y7, Y8, Y10 (the `production.py` side), Y12 and Y13 of
`LRI_C8_D2_HPC_loop/artifacts/s6_fix2_dispositions.md` (findings S6A2-02, S6-C-R2-02, S6-C-R2-01, S6-C-R2-03,
S6E-R2-01, S6D-R2-02, S6D-R2-04, S6R2-F-01). No `src/` change and no cluster job. The default path is unchanged bit
for bit: no native argument, input or numerics changed. The worker now gets a controlled OpenMP environment, and
OpenMP placement never changes a row (A-RPL-6).

## The fixes

- **Y2 (S6A2-02, S6-C-R2-02): one controlled OpenMP environment and a live team check.**
  - `common.omp_child_env(threads, base, wait_policy)` builds the environment for every native launch. It takes the
    inherited environment, removes every `OMP_*`, `GOMP_*` and `KMP_*` control (`OMP_THREAD_LIMIT`, `OMP_DYNAMIC`,
    `OMP_NUM_THREADS`, `GOMP_SPINCOUNT`, `KMP_AFFINITY`, ...), and then sets `OMP_NUM_THREADS`, `OMP_DYNAMIC=FALSE`,
    `OMP_PROC_BIND=close`, `OMP_PLACES=cores` and one BLAS thread. `OMP_WAIT_POLICY` is set only when asked for.
  - Users:
    - `production.py run_native` (each block's worker), which covers the direct, array, lane and sweep entry points;
    - `lanes.py lane` (the claim processes);
    - `sweep.py` (its index processes);
    - `benchkit.omp_env` (P4 lane shapes, `perf_profile.py`, `numerics_flags.py`) and `benchmark.py`'s legacy mode.
  - `slurm/run_array.sh` unsets every inherited `OMP_*`/`GOMP_*`/`KMP_*` before it exports its own.
  - The claim logs the inherited controls it does not pass on.
  - `common.TeamWatch` is the live check, as `tests/thread_identity.py` does it (X3). It samples the worker's
    `/proc/<pid>/task` count, every 1 ms at first and doubling up to 50 ms, until the requested team shows.
  - It watches an ELF worker on Linux and records one of four verdicts:
    - `verified`: the requested team showed.
    - `smaller`: no team after 60 s of wall time **and** 30 s of the worker's CPU time (or unreadable CPU time). The
      worker is stopped and the claim refused with exit 64, so lanes release the claim and stop. Nothing of the block
      is kept, and a failure log names Y2.
    - `unverified`: a run that ended without showing its team, either too short or stalled without computing.
    - `unavailable`: a test stand-in or macOS.
  - The CPU condition keeps an I/O or library-loading stall before the first parallel region from being taken for a
    serial run.
  - Each checkpoint records `runtime.omp_team`, and `production.py status` counts the verdicts of the committed blocks
    (`omp_teams`; post hoc).
  - P4 (`benchmark.py --lane-shapes`) runs every block through `benchkit.run_watched`. A shape counts only when every
    block's team is `verified`; `team_sizes_verified` is in the record.
- **Y6 (S6-C-R2-01): incomplete fingerprints are refused.** `common.elf_kind` classifies the worker as dynamic ELF,
  static ELF, other ELF, or not ELF. For a dynamic ELF worker (every production build), `common.fingerprint_problems`
  refuses any of these:
  - a failed or timed-out ldd probe;
  - an empty library map;
  - a library that is not resolved to a hashed file;
  - an unhashed interpreter;
  - on Linux, a CPU vendor that is the `<platform>-<machine>` fallback (the same class for the F5 pin).

  The kernel's vDSO, which older glibc's ldd lists as `linux-vdso.so.1 =>  (0x...)`, is not an unresolved library.
  The claim checks the fingerprint before any pin is published and before any block runs, and refuses with exit 64
  (claim_io status `incomplete runtime fingerprint`). Static ELF workers, the test stand-ins and macOS keep their
  probed identity.
- **Y7 (S6-C-R2-03): the binding cgroup limit.** `lanes.cgroup_memory_limit` takes the smallest finite limit over the
  process's cgroup and every visible ancestor (v1, v2, hybrid), where it used to take the first finite one.
  - Same class: a line of `/proc/self/cgroup` that is not an `id:controllers:path` entry is now skipped, where it used
    to crash the lane.
- **Y8 (S6E-R2-01): a missing first fingerprint.** Without `runtime_identity.json`, `campaign_runtime_key` now refuses
  a first checkpoint whose fingerprint is missing, null, lacks fields or has a malformed library map. Before, it
  returned `None`, which disabled the check for every checkpoint. Both merges and run-skip are covered. With the pin,
  a checkpoint with a malformed fingerprint is refused as carrying no runtime identity, where it used to crash.
- **Y10 (S6D-R2-02), the `production.py` side.** `plan --design` checks the bundle's replicates before anything else
  is read (`bundle_replicates`):
  - exactly the twelve `<sector>_L<L>` entries, each an integer;
  - at least 2 in any bundle;
  - a power of two in [32, 128] in a non-test bundle (`PRODUCTION_REPLICATES`; PLAN component E).

  Reduced bounds come only from a `--test-only` bundle. The `design.py` side is G3's.
- **Y12 (S6D-R2-04): a sweep resumes only its own request.** `sweep.py check_existing` compares the request with the
  frozen manifest, field by field:
  - seed, backend, numerics, threads, points and replicates;
  - the rates identity (`default`, or the map's sha256);
  - the cost basis (the bootstrap chunk, or the cost model's sha256);
  - the shards and the checkpoint tasks.

  Any difference is refused, by name, before anything runs.
- **Y13 (S6R2-F-01): the sweep registers its seed.** `sweep.py` adds the campaign's base seed to the forbidden-seed log
  right after the plan is published or validated, and before the ledger registration and any index.
  - The log is `--seeds-log`, default `$C8_SEEDS`. The add is idempotent, and its source is RUN, as `seeds.py add
    RUN` writes it.
  - A sweep inside a Slurm job without a log, or with a log that does not exist, is refused before anything is
    planned. Outside a job it runs unregistered, with a note.
  - `slurm/sweep.sh` passes `--seeds-log "$C8_SEEDS"`; its own add after the sweep then reports `present`.
  - Same class: `slurm/plan.sh` adds a new campaign's seed right after the plan. A failed add still registers the
    plan job in the ledger, and then exits with the add's status, naming the command to repeat.

## Before and after

`before_2ae3db7.json`: the ten new test groups were run, each on its own, against 2ae3db7's tools (a `git archive`
with this branch's `tests/unit_orchestration.py` laid over it). All ten fail, each on its defect:

| Test | Item | Failure on 2ae3db7 |
|---|---|---|
| `omp_env` | Y2 | the direct claim's worker received `OMP_THREAD_LIMIT=1`, `OMP_DYNAMIC=true`, ... |
| `omp_team` | Y2 | no team record in the checkpoint |
| `bench_team` | Y2 | `benchkit.omp_env` kept `OMP_THREAD_LIMIT=1` |
| `cgroup_min` | Y7 | 64 GiB (the step) instead of 16 GiB (the job) |
| `fp_complete` | Y6 | the claim ran with a failed ldd probe (exit 0) |
| `fp_first` | Y8 | the merge accepted a missing first fingerprint and a conflicting later one |
| `bundle_reps` | Y10 | a one-replicate test-only bundle was planned |
| `sweep_resume` | Y12 | a default-rate sweep resumed under `--rates MAP` |
| `sweep_seed` | Y13 | a sweep in a Slurm job without a seed log planned anyway |
| `plan_seed` | Y13 class | `slurm/plan.sh` left the seed out of `$C8_SEEDS` |

After: the full Mac suite, `C8_ALLOW_NO_L8=1 make test-python PYTHON=<HOME>/anaconda3/bin/python3
OUTPUT=<dir>` (records in this folder, console output in `make_test_python.log`):

It ran for 20:14 of wall time (01:23 to 01:43 EDT) and exited 0.

| Suite | Result |
|---|---|
| `tests/check_venv.py` | passed |
| `tests/unit_orchestration.py` | 59 groups, 71 tests, all passed (the ten new G2 groups: `omp_env`, `omp_team`, `bench_team`, `cgroup_min`, `fp_complete`, `fp_first`, `bundle_reps`, `sweep_resume`, `sweep_seed`, `plan_seed`) |
| `tests/test_pipeline.py` | 27/27 passed (parts 1 to 3; its sweeps now register their seeds in the test log) |
| `tests/ast_scan.py` | 27 files, 0 findings; `gen/*.py tests/*.py`: 44 files, 0 findings |
| `gen/test_regress.py` | 86 checks passed |
| `gen/test_handoff_inventory.py` | 17 checks passed |
| `tests/merge_scale.py --rows 20000` | passed |
| `tests/check_vendored.py` | 31/31 |
| `tests/vendored_isolated.py` | 10/10 |
| `tests/test_delivery_verifier.py` | passed |
| `tests/check_inputs.py` | 17/17; 2 skipped (the L8 packs are not on the Mac) |
| `tests/test_profiling.py` | 15 passed |
| `tests/test_gmp_prefix.py` | 7 passed |
| `tests/test_numerics_flags.py` | 11 passed |
| `tests/test_dd_profile.py` | 8 passed |
| `tests/sanitize.py --capture-check` | passed |

`tools/verify_delivery.py --write` and then `--strict` ran before the commit.

## Owed on symmetry (integration phase)

- The real worker under an inherited `OMP_THREAD_LIMIT=1` and `OMP_DYNAMIC=true`, through the lane, array, sweep and
  direct entry points. Every committed block must record `omp_team` `verified` at the requested width.
- `benchmark.py --lane-shapes` with `team_sizes_verified` true.
- A real claim's fingerprint on amdq nodes: `fingerprint_problems` must be empty. Before the pilot, survey the nodes'
  ldd output, because a node with a failed probe now makes its lanes exit 64.
- `lanes.memory_limit` under the real Slurm cgroup.
