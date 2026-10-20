# Optimized C8(2) calculation for HPC

This is a separate optimized source release of the two-dimensional long-range
Ising C8 calculation. It targets the measured native bottlenecks and improves
memory control, graph locality, checkpointing, and multi-node job execution.
The graph kernels, sample identities, numerical precision, cancellation
thresholds, and deterministic result assembly are preserved.

**Start with [docs/PERFORMANCE.md](docs/PERFORMANCE.md)** for the profile,
measured performance, numerical contract, scaling limits, and cluster recipes.
Machine-readable timing and validation evidence is in `verification/` and
`optimization_work/`. This release contains no new full C8 sampling campaign;
`RESULTS.md` describes the previously completed calculation.

## Measured result

The released default reduced median peak RSS by **14.6–16.3%** on the bounded
L8 benchmark. Serial runtime was unchanged within run variability. Median
integration times were about 5% lower at two and four threads and about 4%
lower at eight threads; the four- and eight-thread timing ranges overlap.
[docs/BENCHMARK_RESULTS.md](docs/BENCHMARK_RESULTS.md) gives all repeats, the
measured thread scaling, and the limits of those comparisons.

## Changes

- An exact binary128 addition specialization targets promoted denominator sums,
  the largest measured arithmetic bottleneck. It preserves the 113-bit rounded
  value and original addition order. Directed rounding and exceptional operands
  retain the compiler operation. Floating-point exception flags are not
  synthesized by the specialization; the integrator does not read those flags.
- Exact L8 rate palettes reduce alpha storage by 93.7% in the focused physical
  graph test, or about 31.2% across the three main sampling tables. Whole-process
  memory also includes graph polynomials and per-thread scratch.
- Reusable high-precision scalar workspaces reduce allocation churn. Retaining
  constructed vector tails is opt-in: it showed no clear benefit in the bounded
  attribution test, so the default keeps the original vector-resize behavior.
- New plans group a graph's tasks and freeze checkpoint boundaries. Independent
  task, graph-count, and measured-cost limits make memory and restart exposure
  controllable without changing assigned sample intervals.
- Planning and coordinate checks stream task data; merge inserts are batched.
  Independent groups can be merged concurrently with the same Decimal order.
- Optional verified node-local pack reuse amortizes repeated full-pack staging.
  Ordinary execution continues to stage only graph members needed by a block.
- Native output adds actual team size, process CPU/RSS, and task-occupancy
  telemetry outside the point loop. Build and workflow identities remain pinned.

Each kernel change has a compile-time disable switch for measured comparison.
No reduced-precision, fast-math, altered proposal, or algebraic reassociation is
used. See the detailed numerical boundaries and regression evidence in the guide.

## Install next to the original C8 package

Unzip this release as `LRI_C8_D2_HPC_optimized/` beside the previously delivered
`LRI_C8_D2_HPC/` folder. The optimized ZIP includes runtime sources, small input
metadata, tests, frozen benchmark graph fixtures, and evidence. It does not
repeat the twelve unchanged full graph packs or previous production samples.
Do not overlay an existing campaign's pinned source tree.

```bash
cd LRI_C8_D2_HPC_optimized
python3 tools/attach_inputs.py ../LRI_C8_D2_HPC/inputs
```

The attachment command first verifies byte-identical input manifests and every
source pack. It creates relative links and never replaces existing files. Keep
both folders together, or use `--mode copy` for a self-contained installation
(about 7.80 GB of graph packs) or `--mode hardlink` on the same filesystem.
The pack contents and input manifest are unchanged from the original C8 package.

## Build and verify

Requirements: GNU C++17 with OpenMP and libquadmath, Boost headers, Python 3.10
or later, NumPy and SciPy. The GMP backend additionally needs GMP development
headers/library. Build on the target cluster and retain one binary per planned
campaign. Local build records are evidence, not portable compiler settings.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
make -j2 gmp
make -j2 decimal
make test
python3 tests/hpc_scheduler.py --output verification/local_scheduler.json
python3 tests/attach_inputs.py
```

If dependencies are in nonstandard locations, set `CPPFLAGS` and `LDFLAGS` to
the site's include and library directories. The Makefile preserves
`-ffp-contract=off -fno-fast-math`. Arithmetic tiers remain long double,
binary128, and GMP at 350 decimal digits (or Boost decimal at 300 digits).
Both precision backends were checked against an independent 450-digit evaluator.

A frozen local comparison can build its baseline from the included unmodified
reference sources, using the optimized worker's current compiler settings:

```bash
python3 tools/benchmark_native.py build-baseline --backend gmp \
  --output verification/local_baseline_gmp
python3 tools/benchmark_native.py compare \
  --manifest optimization_work/baseline_profile/scaling/manifest.json \
  --baseline verification/local_baseline_gmp --candidate bin/c8d2_gmp \
  --output verification/local_scaling --threads 1 2 4 8 --repeats 3
```

The reference helper uses the rebuilt candidate's build record, keeping the
same target compiler and required arithmetic flags. Use idle allocated CPUs
and keep the frozen input tasks.
The guide includes the broader 52-case replay and direct numerical checks.

## Launch a fresh campaign

Start with an independent pilot on the intended hardware to recalibrate graph
costs. Example counts and resource settings below are starting values to
measure, not a forecast of precision or runtime:

```bash
python3 tools/production.py plan /shared/project/c8-optimized-pilot \
  --seed "$(python3 -c 'import secrets; print(secrets.randbelow(2**63))')" \
  --backend gmp --purpose pilot --replicates 16 \
  --loop-points 3:16384,4:4096,5:1024,6:256,7:64,8:16 \
  --shards 64 --threads 16 --checkpoint-tasks 512 --checkpoint-graphs 32

export C8_PACKAGE="$PWD"
export C8_RUN=/shared/project/c8-optimized-pilot
export C8_ENV_SETUP=/path/to/cluster-env.sh
export C8_SBATCH_ARGS="-A your_project -p your_partition --time=08:00:00"
bash slurm/submit.sh
python3 tools/production.py status "$C8_RUN"
```

`--task-order graph` is the default. Add `--checkpoint-seconds` only with a
measured `--cost-model`; its unit is summed modeled kernel core-seconds,
not block wall seconds. `slurm/resubmit.sh` submits missing work with checkpoint
validation. `C8_MERGE_WORKERS` optionally parallelizes independent-group merge
and requests matching CPUs. `C8_STAGE=1` and `C8_PACK_CACHE` enable reusable
node-local full-pack staging where appropriate.

For one node without Slurm, use `tools/run_local.py` and keep workers times
threads within the allocated cores. Cluster parallelism uses independent array
jobs plus OpenMP inside each worker; no MPI communication is needed during
integration. Multi-node performance must be measured on the actual cluster.

## Running on SDSC Expanse and symmetry (site layer)

On these two managed sites campaigns run through the site layer instead of
job arrays: `tools/site_submit.py runners RUN --nodes N --time HH:MM:SS`
submits N whole-node runner jobs (`slurm/node_runner.sh`, which runs the
unchanged `production.py run` index by index) and one merge job (the unchanged
`slurm/merge.sh`), within the sites' admission budgets, with one CPU vendor per
campaign and a seed reserved in our forbidden-seed registry. With `C8_SITE`
set, `slurm/submit.sh` and `slurm/resubmit.sh` refuse unless
`C8_ALLOW_ARRAYS=1`. Installation, the per-site gate (`slurm/site_gate.sh`),
the seed workflow (`tools/seed_sync.sh`), the budgets and recovery are in
[docs/SITES.md](docs/SITES.md); the tests are `python3 tests/site_layer.py`.
The site layer changes no file that a plan pins.

## Scientific context and scope

The order-eight extension integrates all required free and power forest sectors
and regulator jets at loops three through eight, with the analytic two-loop
jet through degree six. The complete active inventory contains 24,173 kernels.
See `docs/THEORY.md`, `docs/C8_D2_calculation.tex`, `inputs/coverage.json`, and the
original package for the derivation and completed numerical records.

The existing precision estimate is retained as historical context. Optimizing
the worker does not itself reduce its sampling uncertainty. More independently
validated samples and convergence diagnostics are required for higher precision.
This implementation supports the existing C7/C8 kernel orders; further orders
need new scientific inputs and validation.
