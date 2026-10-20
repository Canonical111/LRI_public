# Native kernel profiling and exact replay

This directory contains a bounded, reproducible performance study of the
unchanged C8 worker. It is separate from all production campaigns and from
candidate kernel sources. The complete scientific comparison includes every
native row identity, every Taylor coefficient, maximum point magnitude, and both
precision-promotion counters. Timing, thread count, and supplementary performance
metadata may differ.

## First measured result

The first free-L8 probe used eight graphs, two independently scrambled
replicates, and 128 points per graph/replicate. Four graph choices came from
**measured production task times** in the selected checkpoint: G23833, G18423,
G18756, and G23272. Four more cover primitive/low-promotion and high-promotion
pilot strata. The original and instrumented workers produced exactly identical
scientific fields for all 16 rows and 2,048 points, including 1,518 binary128
promotions and 609 GMP promotions.

| Quantity | Measured seconds | Share of instrumented integration |
|---|---:|---:|
| Original integration | 3.61334 | — |
| Instrumented integration | 3.95996 | 100% |
| Long-double tier, inclusive | 0.23737 | 5.99% |
| Binary128 tier, inclusive | 1.70884 | 43.15% |
| GMP tier, inclusive | 1.99215 | 50.31% |
| Binary128 ordered denominator sums | 1.48057 | 37.39% |
| GMP ordered denominator sums | 0.99701 | 25.18% |
| GMP product DAG | 0.56406 | 14.24% |
| GMP exponentials | 0.33811 | 8.54% |
| Importance mapping | 0.01718 | 0.43% |

The tier totals include their substages. Adding both would count the same work
twice. This one paired run has 9.6% profiling overhead; it is not an optimization
speedup estimate.

The denominator sums account for 62.6% of this measured integration time across
the two promoted tiers. The GMP product DAG accounts for another 14.2%.
Exponentials are a smaller application cost here. This supports targeting
ordered binary128 additions and high-precision polynomial work before changing
the exponential backend.

The GMP counters recorded 30,157,536 denominator additions, 1,701,301 product
multiplications, and 144,796 segment-local GMP temporaries. Those segment-local
temporaries caused exactly 144,796 allocations. Numerator calculations made
673,092 allocations and requested 113 MB cumulatively, but took only 0.03470
seconds (0.88% of total integration). Allocation traffic is substantial without
being the principal time cost. Persistent scratch setup took 0.000834 seconds.

No points in this first probe entered common-log rescaling or the nonmoderate LD
path. The direct regression harness explicitly exercises both paths.

The executable loaded eight graphs with 29,825,988 bytes of persistent vector
capacity; its measured peak RSS was 40,724 KiB. Vector capacity accounting
excludes allocator bookkeeping, temporary preparation structures, MP limb
storage, executable pages, and shared libraries. RSS includes them. On L8 the
original alpha, DP, and choice-total vectors alone hold 3 × 65,536 × 16 =
3,145,728 bytes per graph. L7 uses one quarter as many subsets.

Evidence is preserved in `first_free8/selection.json`, `baseline.json`,
`profile.json`, `stages.json`, and `comparison.json`. The first native executable
was built from the copied sources in `instrumented/`; original source hashes are
recorded there.

## Broader bounded matrix

`matrix/manifest.json` freezes 69 distinct sector/loop graph fixtures across all
12 combinations of free/power and L3–L8. It includes minimum, median and extreme
structural sizes; primitive graphs where available; measured pilot promotion
tails; and expensive measured production graph bundles. Production selection
examines the first checkpoint in each campaign-a shard, so it makes no claim to
find a global maximum among every production task.

Each packed graph is extracted using its byte offset and checked against its
inventory SHA-256. Graphs, task files, direction matrices, gamma input, and the
original source identities are recorded. Base cases reuse the existing pilot
direction matrices and seeds. They use 1,024 points per graph/replicate through
L6 and 128 points at L7/L8. Additional correctness cases exercise:

- All three coordinate layouts, with rates .8, .9, and .6.
- Both 32- and 60-bit direction matrices and absolute seeks crossing the
  highest useful Gray-code direction column.
- Unequal 23/41-point task splits, compared with a whole 64-point task.
- Multiple OpenMP team sizes without changing point identities or task sums.

New direction matrices use the existing baseline exporter, which verifies public
Sobol points, a fresh independently reconstructed engine, and GF(2) rank for
every reachable direction column. The matrix contains 52 total cases.

All 12 base profile cases passed exact original-versus-instrumented replay, for
75,008 points. `matrix/profile_report.json` preserves the full measured counts,
stage times, allocation traffic, source/build records and peak RSS. The broader
free-L8 sample measured 0.335 s in LD, 1.910 s in binary128 and 2.109 s in GMP;
GMP ordered sums, products, and exponentials used 1.020 s, 0.634 s, and 0.336 s,
respectively. The broader power-L8 sample shows the same ordering: GMP sums
0.637 s, products 0.464 s, and exponentials 0.381 s.

These strata intentionally include hard graphs and elevated promotion rates.
Their average cost is not an unbiased forecast of a complete campaign. The
completed campaign's loop/sector cost shares are the appropriate weights when
prioritizing work. Small low-loop cases are also too short for precise isolated
speed estimates; their main role is exact correctness coverage.

## Commands

Run from the optimized project root. Use a fresh output directory to preserve
previous results.

```bash
python tools/benchmark_native.py prepare \
  --source ../LRI_C8_D2_HPC \
  --output optimization_work/baseline_profile/matrix_new \
  --low-points 1024 --high-points 128 --matrix

python tools/benchmark_native.py profile \
  --manifest optimization_work/baseline_profile/matrix_new/manifest.json \
  --threads 1

python tools/benchmark_native.py compare \
  --manifest optimization_work/baseline_profile/matrix/manifest.json \
  --candidate bin/c8d2_gmp \
  --output optimization_work/candidate_comparison \
  --threads 1 2 --repeats 3

python tools/benchmark_native.py direct \
  --candidate-header src/kernel.hpp \
  --output optimization_work/candidate_direct
```

`compare` executes uninstrumented baseline and candidate programs in alternating
AB/BA order and summarizes their medians and ranges. Every timing run must pass
the exact scientific comparison. There is no tolerance-based fallback for
changed native rows. Unequal chunk sums may round differently when combined, so
the separate split check uses a 5e-16 normalized rounding limit and also requires
exact point extrema and promotion totals. `--base-only` restricts a comparison to
the 12 performance cases; `--case free_L8` selects a named case. Extra native
performance telemetry is intentionally excluded from scientific comparisons.

The direct test builds `tests/performance_harness.cpp` against the original and
the selected candidate header. It exercises all layouts at L2/K6 and L3/L7/L8,
severe cancellation that must reach MP, nonmoderate LD evaluation, common-log
rescaling, and four log-coordinate patterns on each existing physical L8
fixture. It compares complete binary128 values and absolute-error sums,
380-digit MP output, and all resulting LD values. Its default runs all four
rounding modes in separate processes. Compile-time candidate switches can be
passed with repeated `--candidate-flag=-DNAME` options. This complements
`tests/kernel_points.cpp`, whose 450-digit evaluator independently reconstructs
whole monomials; it does not replace that independent accuracy gate.

## Standalone reference builds and final results

The pristine original worker and kernel are included under `original/src/`.
Their byte hashes match `optimization_work/baseline_identity.json`. The minimal
reference builder uses the current destination build record's compiler and
dependency flags; it does not require the prior workspace or its graph packs.
First build the current GMP worker with the local machine's dependency flags so
that `bin/c8d2_gmp.build.json` describes that machine, then run:

```bash
python tools/benchmark_native.py build-baseline --backend gmp \
  --output bin/c8d2_reference_gmp

python tools/benchmark_native.py compare \
  --manifest optimization_work/baseline_profile/matrix/manifest.json \
  --baseline bin/c8d2_reference_gmp --candidate bin/c8d2_gmp \
  --output optimization_work/local_comparison --threads 1 2 --repeats 3
```

Frozen matrix comparisons use only the selected executable paths and bundled
fixtures. The absolute `source_root` in their manifest is provenance. To rebuild
the private instrumented reference without the previous workspace, pass
`--source optimization_work/baseline_profile/original`, an explicit `--baseline`,
and `--build-record bin/c8d2_gmp.build.json` to the profile command. Preparing new
selection strata still requires the original inventory/pilot/production evidence;
the existing frozen matrix already contains the verified graph and net bytes.

The authoritative released-default results are
`optimization_work/performance_summary.json` and `performance_summary.md`, with
raw runs in `optimization_work/scaling_release/`. They show no resolved serial
runtime gain, smaller median integration times with multiple threads, and
14.6–16.3% lower peak RSS on this fixed workload. The earlier grow-enabled
configuration is historical evidence. Its serial gain did not reproduce in the
released default; the retention switch, driver/code layout, and measurement
window are confounded. The released default leaves grow-only MP vectors opt-in.

## Instrumentation limits

Instrumentation wraps original statement boundaries in copied sources. Clocks
use `steady_clock`; counters are thread local and merge once per OpenMP thread.
There are no locks in the point loop. GMP hooks forward to malloc/realloc/free
and count allocation traffic by active phase. They do not change precision or
thresholds. `getrusage` supplies process CPU time and peak RSS without `/proc`,
perf, or privileged access. Stage times are elapsed times and can include OS
preemption. Actual speed comparisons use uninstrumented executables, several
paired repeats, fixed inputs, and otherwise idle CPUs. Scaling runs should be
coordinated with other native jobs; changing the number of simultaneously
competing jobs would undermine an OpenMP comparison.
