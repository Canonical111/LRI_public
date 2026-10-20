# C6(2): optimized and restartable HPC integration

This is the two-dimensional counterpart of the C7(1) HPC delivery. It optimizes and distributes the **existing
finite-MOM C6(2) calculation**; it does not import the one-dimensional integration kernel or change the definition of
the physics. Convention: epsilon = 2s - 2. Loops 3–6 are integrated with their full required regulator Taylor jets;
the two-loop input and the separately audited analytic power-sector compensation are retained.

**No new high-statistics physical result is claimed in this delivery.** The archived estimate is C6(2) =
362.3489137997967 with sampling SE 0.15264446036381157; the preceding empirical report remains 362.3 +/- 0.7.
Benchmark, smoke and validation samples are not additions to that estimator.

This revision makes the package production-ready on SDSC Expanse (see `CHANGELOG.md`): every native call runs a
verified job-private copy of the executable and inputs, assembly verifies its inputs, merges and assembly are
resumable and idempotent, `status` drives recovery, arrays are split for MaxArraySize, blocks and shards are sized by
estimated cost, seeds are hashed per group, and the primitive strata get a variance-based allocation. The numerical
kernel is unchanged: the production binary built from this revision is byte-identical to the one built from the
delivered sources with the same compiler.

## What is different from the original code

* Profiling first: in an all-active-graph six-loop test, 67% of the integration interval was ordinary
  extended-precision kernel evaluation, 3.5% binary128 fallback, and the remainder sampling/Taylor/bookkeeping.
* The existing monomial-product DAG is kept; **compressed ordered-prefix sharing** of denominator sums and reuse of
  identical numerator linear forms are added. Individual polynomial summation order is preserved. Dead six-loop
  Taylor/log work and per-point vector allocations are removed. Fallback formulas and thresholds are not weakened.
* Tasks are `(campaign, loop, replicate, graph, sample interval)`. Direct Gray-code seeking reconstructs exactly the
  original Sobol stream at an arbitrary sample index. OpenMP threads and Slurm array jobs do not enter the random
  identity.
* Only a checkpoint-sized block of graphs/results is in the native process. SQLite stores and sorts task metadata
  and merge rows on disk.
* Complete, nonoverlapping power-of-two nets are enforced during merging. Chunks are **execution units, not
  independent statistical replicates**.
* New campaigns **recompute the ten primitive inputs** by default (`--primitive-mode recompute`), with a frozen
  variance-based split of their budget. `--primitive-mode retained` adds the prior primitive input and its variance
  once. The other 66 formerly shared kernels are always sampled.

## Measured performance

Matched local runs of the original delivery (median of three; `benchmarks/matched/`, produced by an earlier version
of `tools/benchmark.py`):

| Workload | Samples | Reference wall | New wall, 1 thread | Wall speedup | Integration-only speedup |
|---|---:|---:|---:|---:|---:|
| Five-loop, 12 expensive graphs | 98,304 | 0.52 s | 0.37 s | 1.41x | 1.36x |
| Six-loop, 16 expensive graphs | 262,144 | 4.40 s | 2.58 s | 1.71x | 1.53x |

On SDSC Expanse (AMD EPYC 7742, GCC 13.3) the matched one-thread speedups are 1.50x and 1.64x (1.45x
integration-only). A production L6 shard costs about 11 µs per sample per core, and the README production example
below is about 6-7 core-hours for both campaigns. At 16 threads, the measured core utilisation of production shards
is 0.83-0.93, and OpenMP efficiency is 0.99 (`benchmarks/expanse_2026-09/`, `docs/PERFORMANCE.md`).

## Build and check

GNU/Linux, GCC with OpenMP/libquadmath, Boost headers and **Python >= 3.10** are required. The build requires at
least 64 significant bits and the extended exponent range in `long double`. **No executable is shipped: build on the
target architecture**, and never replace the executable inside a campaign.

```bash
cd LRI_C6_D2_HPC
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
make clean && make
make test            # native replay vs original + pure-Python tests (make test-python runs without the binary)
make test-workflow   # distributed workflow with the real worker: restart, duplicates, failures, tampering
make test-points     # independent high-precision Kirchhoff point checks (relative error)
make test-levels     # forced binary128 and 300-digit tiers vs the original code
make test-e2e        # original binary vs the complete plan/run/merge pipeline
```

`CXXFLAGS` may be overridden; `-fopenmp -ffp-contract=off -fno-fast-math` are always appended. No `-Ofast`,
fast-math, reduced precision or changed fallback threshold is used. See `docs/NUMERICS.md` for tested tolerances.

## Production on SDSC Expanse

```bash
# once: environment (copy and adapt slurm/expanse_env.sh.example: modules gcc/13.3.0 boost/1.86.0 + a venv)
export C6_ENV_SETUP=$HOME/c6_expanse_env.sh && source $C6_ENV_SETUP
make clean && make && make test

# plan on the SHARED Lustre filesystem, never on node-local /scratch; choose a fresh --seed for every campaign
export C6_PACKAGE=$PWD C6_RUN=<SCRATCH>/temp_project/c6-d2/run-$(date +%Y%m%d)
python3 tools/production.py plan "$C6_RUN" --seed <fresh 63-bit integer> \
  --replicates 64 --multiplier 4 --primitive-points 65536 \
  --shards 32 --threads 16 --checkpoint-tasks 512
# plan prints: jobs, estimated core-hours, the largest shard wall time, a suggested --time,
# and the projected primitive-block SE of the frozen allocation

# submit: arrays split at 1000 elements with C6_INDEX_OFFSET, then an afterok merge + assembly;
# CPUs per element and wall time default to the plan's --threads and suggested time (extra sbatch args override)
C6_SBATCH_ARGS="-A <ACCOUNT> -p shared" slurm/submit.sh

python3 tools/production.py status "$C6_RUN"     # committed/total blocks; exit 0 when complete
```

If a work element fails (timeout, node failure), the afterok merge never starts. Recovery: `scancel` the pending
merge, then run `slurm/resubmit.sh` (same environment). It resubmits exactly the incomplete job indices reported by
`production.py status` (with offsets, the plan's CPU count and suggested wall time, and `C6_SBATCH_ARGS`) and a merge
with `afterok` on all of them and on every still-live element; complete, valid checkpoints are verified and skipped.
Live elements are recognised by the campaign tag that `submit.sh` attaches, and never duplicated. `status` also
prints one `submit.sh --window OFFSET:ARRAY` line per missing window. Every submission path is validated by
`tools/slurm_submit.py` (see `docs/HPC.md`). `slurm/merge.sh` is safe to rerun: groups already merged are validated and skipped, and an existing
identical `C6_result.json` is kept. A corrupt, missing, duplicate, overlapping, foreign or incompatible record is rejected,
never replaced by zero or overwritten.

Other Slurm sites: `slurm/run_array.sh` and `slurm/merge.sh` need `C6_PACKAGE`, `C6_RUN`, optional `C6_ENV_SETUP`,
`C6_PYTHON` and `C6_INDEX_OFFSET`; pass account, partition, CPUs and wall time on the `sbatch` command line. A local
equivalent of one element is `python3 tools/production.py run "$C6_RUN" --index 0 --threads 8`.

## Planning a campaign

* **Seeds.** Every campaign needs its own fresh `--seed`. Group seeds are derived by SHA-256 of (seed, campaign,
  loop, role) (`--seed-scheme hashed`, default). The archived driver arithmetic is available only as
  `--seed-scheme legacy`, which refuses the archived production base seeds.
* **Points.** Nonprimitive strata use the frozen pilot allocation times `--multiplier` (a power of two). In recompute
  mode the primitive budget is `--primitive-points x --multiplier` per primitive on average, split by a frozen Neyman
  table (`inputs/primitive_allocation_d2.json`, from archived paired records; `--primitive-allocation uniform`
  restores the equal split). `--points` overrides every stratum, primitives included (tests, smoke runs).
* **Shards and blocks.** `--shards` is the shard count of the most expensive group; cheaper groups get proportionally
  fewer (`--shard-policy uniform` restores equal counts). Inside a shard, tasks are processed in estimated-cost order
  in blocks of `--checkpoint-tasks`; use at least 16-32 tasks per thread (run refuses more threads than tasks per
  block). Choose `--shards` so that the printed largest shard wall time is several minutes or more.
* **Estimates.** Core-hours and wall times come from a calibration measured on Expanse EPYC 7742 (recorded in the
  manifest); they are estimates, not guarantees.

## Smoke test (not a precision calculation)

```bash
python3 tools/production.py plan <SCRATCH>/temp_project/c6-smoke \
  --seed <fresh seed> --points 8 --replicates 4 --shards 4 --threads 2 --checkpoint-tasks 64 --chunk-points 3
```

Submit with `slurm/submit.sh` or run every index locally, then merge and assemble. The deliberately tiny samples have large statistical errors.

## Deliverables

* `src/`: optimized native sampler/kernel, with strict precision checks (no prebuilt binary).
* `tools/`: input preparation, planning/execution/status/merge, assembly, primitive allocation, reference
  reassembly, checksums, staging, benchmarks.
* `inputs/`: immutable per-graph kernels, rates, exact two-loop data, frozen map, allocations, primitive reference
  and allocation table; `inputs/manifest.json` records every source file and hash.
* `tests/`, `benchmarks/`: numerical regression, independent determinant checks, forced precision tiers, end-to-end
  comparison, workflow and orchestration checks, matched timings and Expanse validation records.
* `slurm/`: array, merge and submission templates and an Expanse environment example.
* `docs/`: numerical contract, HPC runbook, performance analysis. `CHANGELOG.md`: this revision.
* `reference/`: the original method-refinement delivery (code, raw production data, inputs, TeX/PDF note, audits),
  unchanged and verified by its own `SHA256SUMS.json`.

Archived-data reassembly with the **archived analysis code** (does not run integrations or edit reference files; the
comparison is to relative 1e-12 because the last bits depend on the NumPy/BLAS build):

```bash
python3 tools/reassemble_reference.py /tmp/c6-reference-reassembled.json
```

The new assembly (`tools/assemble.py`) is tested separately against the archived fresh-campaign records by
`tests/archived_assembly.py`. The final `C6_result.json` includes complete covariance, per-loop errors, independent
campaigns, lower-order checks, bootstrap diagnostics and the digests of its inputs. It deliberately leaves
`empirical_allowance` unset. Narrower sampling errors are not by themselves an independent validation of the
underlying graph/renormalization framework. Package integrity: `python3 tools/checksums.py verify`.
