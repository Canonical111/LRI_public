# Performance investigation and measured scope

## 1. Profile before optimization

The archived production uses two different hot paths: continuous binary-cluster
QMC (`coordinate_tree_qmc.cpp`) and meromorphic tensor quadrature
(`coordinate_tree_integrate_safe.cpp` / `..._allocated.cpp`). Historical timings
are retained in `reference/verification/production_audit.json`. They are not
compared directly with measurements on this machine.

Fresh **single-thread phase instrumentation** on twelve nonprimitive L7 classes,
49,152 continuous points, gave:

| Phase | Measured seconds |
|---|---:|
| Draw cluster tree | 0.065926 |
| Initial long-double point evaluation | 0.539471 |
| Binary128 reevaluation | 3.816458 |
| 100-decimal-digit reevaluation | 4.536980 |
| Full integration interval | 9.327908 |

Only 6,150 points required binary128 and 59 required decimal multiprecision, yet
the fallback paths consumed roughly **89.6% of the measured integration interval**
(or 86% of total process wall time). Those are the paths worth optimizing; simply
accelerating the first long-double pass would miss the dominant cost.

For power quadrature, L7 degree 6, 24 sampled trees:

| Phase | Measured seconds |
|---|---:|
| Geometry generation/cache lookup | 6.834810 |
| Weight generation/cache lookup | 1.412470 |
| Tensor/forest contraction | 4.413530 |

There were 24 geometry misses and no hits in this workload. One full geometry
entry has

```
3 arrays × 117649 nodes × 28 distances × 16 bytes = 158120256 bytes.
```

This **single entry exceeds the old nominal 48 MiB geometry-cache limit**. The old
insertion code evicts existing entries but still inserts an oversized new entry.
Its bounded-cache comment does not imply a strict memory bound. Multiple caches,
working references, duplicate graph copies and full result arrays compound this.

The actual logs and instrumented baseline sources are in
`benchmarks/profiling/`. Re-run with:

```bash
python3 tools/profile.py --out "$C7_WORK/c7-profile"
```

The clocks add some overhead, so the performance ratios below use separate,
uninstrumented binaries. The profiling process is deliberately one-threaded;
its global diagnostic counters are not a parallel profiler.

## 2. Changes selected from the profile

### Continuous evaluation

An ordered prefix trie shares identical products and sums across forest terms.
It does not sort multiplicative factors or merge signed forest terms. The parent
path applies the factors of `base`, `H` and the log polynomial in the same order
as the original loops. Squared/cubed edge factors are computed once (`v2`, `v3`)
and used at each occurrence. Long-double and binary128 point values are bitwise
identical to the original; under Boost expression templates the precomputed
powers change the MP100 rounding order, the source of the ~3.2e-59 MP100
difference (NUMERICS.md), not the trie.

For L7, K=7-L=0: only the zeroth regulator coefficient is needed from each point.
The old code nevertheless computed logarithms and then the first, unused Taylor
term. Those operations were especially expensive at 100 digits. They are omitted.
The same optimization is applied to the binary128 and decimal fallback functions;
it is not obtained by suppressing precision promotion.

The trie and numeric scratch are built once per graph/thread, not per sample.
The sampler still generates the identical tree and ratios for each global index.

### Power quadrature

A bounded tile contains node indices, regularized distances and weights. All
`(N+1)^(L-1)` nodes are still visited. No sparse-grid approximation or reduced
degree was introduced. Weight signatures shared by forest terms are computed
once per tile; path products are reused. Logs are computed only for nodes whose
Laurent coefficient actually requires them. At degree one, exact integer q/H
arguments permit reuse of the same long-double `sqrtl`/`logl` evaluations.

Accumulation is per term and compensated. This is a changed floating-point
reduction order; see NUMERICS.md rather than assuming bitwise identity with the
old uncompensated whole-grid loop.

### Data movement and scheduling

The byte index loads only graph classes present in the current checkpoint block.
It removes multiple full-inventory copies and the global B×G×14 result allocation.
Thread tasks are graph × replicate × contiguous stream block; long tasks are
scheduled first. Each task has a unique sparse output row. Workers never compete
on a shared floating-point accumulator.

## 3. Matched, uninstrumented timings

Command:

```bash
python3 tools/benchmark.py --out "$C7_WORK/c7-bench" --repeats 3 --scaling
```

Both implementations use GCC 14.2, `-O3 -g -std=c++17 -fopenmp
-fno-fast-math -ffp-contract=off`. Only hardcoded thread counts are removed from
the reference. Seeds, graph subsets, counts and quadrature weights match.
Reference and optimized runs alternate order between repetitions. Times include
fresh-process startup; the separate internal interval is also recorded.

Hardware: AMD EPYC 9V74 virtual machine, five visible CPUs, **four-core cgroup
quota**, 4 GiB memory limit. This is not a dedicated HPC node. Reported values
are medians of three runs, not confidence limits on machine performance.

| Workload | Original wall | Optimized wall | Wall ratio | Kernel-only ratio |
|---|---:|---:|---:|---:|
| Continuous, 49,152 points | 9.09 s | 1.64 s | 5.54× | 5.33× |
| Power degree 1, 3,072 trees | 0.81 s | 0.61 s | 1.33× | **0.85×** |
| Power degree 3, 24 trees | 0.69 s | 0.30 s | 2.30× | 1.31× |
| Power degree 6, 24 trees | 13.48 s | 7.62 s | 1.77× | 1.73× |

**A real tradeoff:** the degree-one original cache already reuses a small tensor
very effectively. The new core loop is about 17% slower there. Its process time
wins through lower setup cost, but that cannot be extrapolated to a long warm-cache
job. Use the included original executable for controlled comparisons on your
site if coarse quadrature dominates. The new code's larger-degree memory bound
and scheduling advantages do not depend on calling this a universal speedup.

RSS medians in KiB are exactly 112568→4536, 217872→4160, 185888→4512,
and 545812→4484 for the four rows. Much of this reduction is from not loading and
replicating the full graph inventory for a small shard. These values are **not a
claim that every full-node production process will use 4 MiB**.

### The benchmark mix is not the production mix

The twelve continuous benchmark graphs span forest-term-count quantiles with
equal sample counts, so the workload is much heavier than the production
allocation. It averages about 80 forest terms per sample, against about 14 in the production
`tprodA_L7` campaign. In the benchmark 12.3% of points fall back to binary128
and 0.12% to MP100; in the archived `tprodA_L7` record these rates are 2.3% and
1.2e-5. The benchmark therefore weights the optimized fallback paths far more
than production does, and the **5.54× continuous ratio is not
production-representative**. Re-weighting the benchmark's own per-graph timings
by production sample counts gives roughly 3×. No separate production-mix
benchmark was run.

### Local thread scaling

| Threads | Continuous internal seconds | Speedup | Degree-six internal seconds | Speedup |
|---:|---:|---:|---:|---:|
| 1 | 1.640648 | 1.00× | 7.615872 | 1.00× |
| 2 | 0.786227 | 2.09× | 4.300077 | 1.77× |
| 4 | 0.421376 | 3.89× | 2.201479 | 3.46× |

The slightly superlinear two-thread continuous ratio is a measurement on a small
VM workload, not an asymptotic claim. No multiple-node, NUMA-node, GPU or MPI
benchmark was run. Cluster throughput must still be measured on the intended
machine, including filesystem overhead and slowest-shard completion.

### Independent re-measurement

During the 2026-09-25 review the same four workloads were re-measured on an
Intel i9-13900K workstation (GCC 13.3), single-threaded, median of three. The
original/new ratios were 5.9× (continuous), 1.65× (power degree 1), 3.0× (degree
3) and 2.3× (degree 6). Peak RSS fell from 114–548 MB to 6–7 MB. The benchmark
mix caveat above applies unchanged. These records are kept with the review, not
in `benchmarks/`.

### Whole-production cost

The complete archived design at multiplier 1 (all 21 campaigns at their
archived replicate counts) costs about **3 core-hours**: 2.98 core-hours of
summed per-row thread time on the i9-13900K, about one fifth of it in the six
continuous campaigns. Depending on the CPU, expect roughly 1.4–4 core-hours. It ran end to end through
the Slurm templates (plan, array, merge and assembly) in about 10 minutes on one
24-core node. Cost scales roughly with the sample multiplier times the replicate
multiplier. This is one measured configuration, not a site-independent cost
model.

## 4. Experiments not retained

A prefix-sharing rewrite of the **power** contraction increased degree-six time
from about 7.18 s to 9.30 s in a matched preliminary test. Its overhead outweighed
saved arithmetic. It was reverted; the continuous prefix optimization remains.

An 8-MiB bounded cache of degree-one weights gave about 0.646 s in a profiled test,
not an improvement over the uncached ~0.605 s median, and raised working memory
to about 8.4 MiB. It was also reverted. These are limited tests, not impossibility
results for better caching strategies. The delivered code is the measured
uncached/tiled version.

A full GPU port, reduced-precision arithmetic, alternative quadrature rule,
low-rank tensor compression, and a new importance distribution were not adopted:
they would require new numerical analysis or portability work rather than being
transparent performance refactors.

## 5. What still grows

Let P=(N+1)^(L-1), E=L(L+1)/2, F the number of forest terms, T tile size and S the
number of distinct weight signatures of one graph. The old geometry storage is
O(P E) per cached shape and weight storage grows with P. The new point scratch is
O(T(E+7S)+F×7), plus small grid weights O(L² N), graph data and proposal tables.
T is reduced automatically to obey the principal long-double buffer budget.
There is no P-sized geometry or index array.

The contraction still performs O(P F L) edge/term work at fixed jet width. This
algorithmic exponent was **not** removed. For higher degree, bounded memory
prevents the old cache explosion but runtime can still rise steeply.

The complete plan stores O(number of work units) metadata, and the sparse disk
output scales similarly. C++ worker RAM depends on its checkpoint block, selected
graphs and threads, not on all samples or all production replicates. The reducer
uses SQLite on disk with a 16-MiB cache and O(14×replicates) result totals; it loads
only one bounded checkpoint JSON at a time. See HPC.md for staging and chunking
tradeoffs.
