# C6(3): optimized and restartable HPC integration

This is the **three-dimensional counterpart** of the C6(2) and C7(1) HPC packages. It evaluates the existing
finite-MOM C6(3) calculation, with `epsilon = 2s - 3`; it does not reuse the d=2 kernel with a relabelled output.
The dimension-three measure `U^(-3/2)`, Gamma normalization, importance rates, two-loop Taylor data and canonical
thermal dimension are all explicit. The analytic power-subgraph compensation is retained from the original
calculation, not independently redone here.

**No new high-statistics physics estimate is claimed in this delivery.** Reassembly of the archived accepted data
reproduces C6(3) = 33.56819679857058 with sampling SE 0.02418403846814063; the retained empirical report is
33.57 +/- 0.10. Benchmark, smoke and validation samples are not added to that estimate.

This revision makes the package production-ready on SDSC Expanse (see `CHANGELOG.md`). It ports the reviewed and
Expanse-validated orchestration of the C6(2) package and fixes the d=3-specific review findings:
- every native call runs a verified job-private copy of the executable, inputs and Sobol net;
- assembly verifies its input;
- merges and assembly are resumable and idempotent;
- `status` drives recovery, and one guarded submission path, holding a per-campaign lock, submits all work;
- arrays are split for MaxArraySize, and blocks and shards are sized by estimated cost;
- seeds are hashed per group, and archived seeds are refused under the legacy scheme.

The numerical kernel is unchanged: the production binary built from this revision is byte-identical to the one
built from the delivered sources with the same compiler.

## Verified against the archived d=3 production

- **Archived streams replayed.** `make test-replay` replays all eight archived fresh production streams
  (`reference/records/new_{a,b}_d3_L3..L6.json`, 385,744,896 samples) with the built worker, on their archived nets and
  seeds:
  - the binary128 fallback counts equal the archive in every stream;
  - per-graph jets agree to about 2e-13 (summation rounding);
  - the fresh-only C6(3) assembled from the replayed streams equals the published 33.560840352429125 (bitwise on a personal desktop).
- **Archived assembly reproduced.** `tests/archived_assembly.py` reproduces the archived fresh-only, previous,
  per-campaign and four-campaign results from the archived records to relative 1e-15.

## What is different from the original code

* Profiling first: ordinary extended-precision kernel evaluation accounts for 66.1% of the measured six-loop
  integration interval; binary128 fallback accounts for 3.0%. The kernel, not Python orchestration, is the target.
* The monomial-product DAG is kept; ordered prefixes of denominator sums and identical numerator expressions are
  shared, preserving each denominator's addition order. Every square root and the original higher-precision fallback
  formulas are retained. Dead six-loop shape logarithms and Taylor work are removed.
* Tasks are `(campaign, loop, replicate, graph, point interval)`. Direct Gray-code seeking reconstructs exactly the
  original Sobol stream at any chunk boundary. OpenMP threads and Slurm array jobs do not enter the random identity.
* Only a checkpoint-sized block of graphs/results is in the native process. SQLite stores and sorts task metadata
  and merge rows on disk. Complete, nonoverlapping power-of-two nets are enforced during merging. Chunks are
  **execution units, not independent statistical replicates**.
* **Every primitive stratum is recomputed.** Unlike the d=2 retained-input workflow, there is no inherited Monte
  Carlo primitive offset or shared error floor.

## Measured performance

Median of three local runs, matched points, seeds, graphs and strict compiler flags (`benchmarks/matched/`):

| Workload | Points | Reference wall, 1 thread | Optimized wall, 1 thread | Wall speedup | Integration-only speedup |
|---|---:|---:|---:|---:|---:|
| Five loops, 12 expensive classes | 98,304 | 0.53 s | 0.36 s | 1.47x | 1.45x |
| Six loops, 16 expensive classes | 262,144 | 4.20 s | 2.58 s | 1.63x | 1.44x |

These are local x86-64 measurements under a four-CPU quota, not a multi-node benchmark. Expanse throughput and the
planning calibration are in `docs/PERFORMANCE.md` and `benchmarks/expanse_2026-09/`.

## Build and check

GNU/Linux, GCC with OpenMP/libquadmath, Boost headers and **Python >= 3.10** are required. The build requires at
least 64 significant bits and the extended exponent range in `long double`. **No executable is shipped: build on the
target architecture**, and never replace the executable inside a campaign.

```bash
cd LRI_C6_D3_HPC
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
make clean && make
make test            # validate (original d=3 code) + pure-Python tests (make test-python runs without the binary)
make test-workflow   # distributed workflow with the real worker: restart, duplicates, failures, tampering
make test-points     # independent high-precision Kirchhoff point checks (relative error)
make test-levels     # forced binary128 and 300-digit tiers vs the original d=3 code
make test-e2e        # original d=3 binary vs the complete plan/run/merge pipeline
make test-replay     # the eight archived fresh production streams and the published C6(3), about 2 min at 16 threads
```

`CXXFLAGS` may be overridden; `-fopenmp -ffp-contract=off -fno-fast-math` are always appended. No `-Ofast`,
fast-math, reduced precision or changed fallback threshold is used. See `docs/NUMERICS.md` for tested tolerances.

## Production on SDSC Expanse

```bash
# once: environment (copy and adapt slurm/expanse_env.sh.example: modules gcc/13.3.0 boost/1.86.0 + a venv)
export C6_ENV_SETUP=$HOME/c6d3_expanse_env.sh && source $C6_ENV_SETUP
make clean && make && make test

# plan on the SHARED Lustre filesystem, never on node-local /scratch; choose a fresh --seed for every campaign
export C6_PACKAGE=$PWD C6_RUN=<SCRATCH>/temp_project/c6-d3/run-$(date +%Y%m%d)
python3 tools/production.py plan "$C6_RUN" --seed <fresh 63-bit integer> \
  --replicates 64 --multiplier 4 --shards 32 --threads 16 --checkpoint-tasks 512
# plan prints: jobs, estimated core-hours, the largest shard wall time, a suggested --time,
# and the projected C6(3) sampling SE (plain MC scaling of the archived fresh campaign)

# submit: arrays split at 1000 elements with C6_INDEX_OFFSET, then an afterok merge + assembly;
# CPUs per element and wall time default to the plan's --threads and suggested time (extra sbatch args override)
C6_SBATCH_ARGS="-A <ACCOUNT> -p shared" slurm/submit.sh --mem=8G

python3 tools/production.py status "$C6_RUN"     # committed/total blocks; exit 0 when complete
```

If a work element fails (timeout, node failure), the afterok merge never starts. Recovery: `scancel` the pending
merge, then run `slurm/resubmit.sh` (same environment). It resubmits exactly the incomplete job indices reported by
`production.py status` and a merge with `afterok` on all of them and on every still-live element; complete, valid
checkpoints are verified and skipped. Live elements are recognised by the campaign tag that `submit.sh` attaches,
and never duplicated. Only one submission per campaign runs at a time (a second one exits 75). `status` also prints
one `submit.sh --window OFFSET:ARRAY` line per missing window. Every submission path is validated by
`tools/slurm_submit.py` (see `docs/HPC.md`). `slurm/merge.sh` is safe to rerun: groups already merged are validated
and skipped, and an existing identical `C6_result.json` is kept. A corrupt, missing, duplicate, overlapping, foreign,
wrong-dimensional or incompatible record is rejected, never replaced by zero or overwritten.

On Expanse an array element whose node fails at launch can stay PENDING with reason `launch_failed_requeued_held`
(held; the recovery tooling counts it as live, so the merge waits). It never ran: release it with
`scontrol release <jobid>`.

Other Slurm sites: `slurm/run_array.sh` and `slurm/merge.sh` need `C6_PACKAGE`, `C6_RUN`, optional `C6_ENV_SETUP`,
`C6_PYTHON` and `C6_INDEX_OFFSET`; pass account, partition, CPUs and wall time on the `sbatch` command line. A local
equivalent of one element is `python3 tools/production.py run "$C6_RUN" --index 0 --threads 8`.

## Planning a campaign

* **Seeds.** Every campaign needs its own fresh `--seed`. Group seeds are derived by SHA-256 of (seed, campaign,
  loop, role) (`--seed-scheme hashed`, default). The archived driver arithmetic is available only as
  `--seed-scheme legacy`, which refuses every archived base seed (both production plans and the archived d=3
  development and validation records).
* **Points.** Every stratum, the ten primitives included, uses the frozen variance-based (Neyman) production
  allocation (`inputs/counts_L*.json`; zero targets become 4 points) times `--multiplier` (a power of two).
  `--multiplier 1 --replicates 32` is exactly the archived fresh campaign. `--points` overrides every stratum,
  primitives included (tests, smoke runs). There is no separate primitive override.
* **Precision.** Plain MC scaling holds at these sizes: SE(C6(3)) ~ 0.0281 (multiplier x replicates / 32)^(-1/2);
  `plan` prints this projection. Loop 5 carries about 38% of the variance for 9% of the CPU.
* **Shards and blocks.** `--shards` is the shard count of the most expensive group; cheaper groups get proportionally
  fewer, by estimated seconds (`--shard-policy uniform` restores equal counts). Inside a shard, tasks are processed in
  estimated-cost order in blocks of `--checkpoint-tasks`; use at least 16-32 tasks per thread (run refuses more
  threads than tasks per block). Choose `--shards` so that the printed largest shard wall time is several minutes or
  more.
* **Grid.** `--grid none` is the default and matches the archived production; `--grid frozen` applies the verified
  d=3 reference map to campaign A at six loops for optional comparisons.
* **Estimates.** Core-hours and wall times come from a per-loop calibration of the d=3 worker measured on Expanse
  EPYC 7742 with `run_array.sh` elements on the shared partition (recorded in the manifest); they are estimates, not
  guarantees. A README-scale campaign (multiplier 4, 64 replicates) is about 4.7 core-hours.

## Smoke test (not a precision calculation)

```bash
python3 tools/production.py plan <SCRATCH>/temp_project/c6-d3-smoke \
  --seed <fresh seed> --points 8 --replicates 4 --shards 4 --threads 2 --checkpoint-tasks 64 --chunk-points 3
```

Submit with `slurm/submit.sh` or run every index locally, then merge and assemble. The deliberately tiny samples have
large statistical errors. The non-power-of-two chunk size is safe: the complete graph net is still power-of-two.

## Deliverables

* `src/`: optimized native d=3 sampler/kernel with strict precision checks (no prebuilt binary).
* `tools/`: input preparation, planning/execution/status/recovery/merge, guarded Slurm submission, assembly,
  reference reassembly, checksums, staging, benchmarks.
* `inputs/`: dimension-labelled per-graph kernels and rates, d=3 Gamma and two-loop data, frozen allocation, optional
  map; `inputs/manifest.json` records every source file and hash.
* `tests/`, `benchmarks/`: numerical regression against the original d=3 code, archived-stream replay, archived
  assembly, independent determinant and convention checks, forced precision tiers, end-to-end comparison, workflow and
  orchestration checks, matched timings and Expanse validation records.
* `slurm/`: array, merge, submission and recovery scripts and an Expanse environment example.
* `docs/`: numerical contract, HPC runbook, performance analysis. `CHANGELOG.md`: this revision.
* `reference/`, `reference_d3/`: the original method-refinement package and the complete original d=3 derivation,
  unchanged. `provenance/`: the verbatim d=2 predecessor source, the d=3 port diff and the fix-port diff.

Archived-data reassembly with the **archived analysis code** (does not run integrations or edit reference files; the
comparison is to relative 1e-12 because the last bits depend on the NumPy/BLAS build):

```bash
python3 tools/reassemble_reference.py /tmp/c6-d3-reference-reassembled.json
```

The final `C6_result.json` includes complete covariance, per-loop errors, independent campaigns, lower-order checks,
bootstrap diagnostics and the digests of its inputs. It deliberately leaves `empirical_allowance` unset. Narrower
sampling errors are not by themselves an independent validation of the underlying graph/renormalization framework.
The lower-order pulls are diagnostics, not gates (the archived fresh C3 pull was +2.42). Package integrity:
`python3 tools/checksums.py verify` (or `python3 tools/check_delivery.py`).
