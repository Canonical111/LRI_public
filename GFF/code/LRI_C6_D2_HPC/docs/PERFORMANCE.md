# Performance measurements and scaling limits

## Profiling, before implementation

An instrumented copy of the original `experiment.cpp` used one thread, all
nonzero saved allocation strata, two frozen randomizations, and 256 points per
stratum. The six-loop run had 182,784 samples:

| Measured interval | Seconds | Fraction of integration interval |
|---|---:|---:|
| Total integration | 3.50637 | 100% |
| Ordinary extended-precision kernel | 2.36069 | 67.3% |
| Binary128 reevaluation | 0.123963 | 3.54% |
| 300-decimal reevaluation | 0 | 0% on this sample |
| Sampling, jets and bookkeeping | 1.02172 | 29.1% |

There were 141 binary128 calls. This sample is not a proof that multiprecision
cost is always negligible. Extreme-endpoint tests exercise the 300-decimal tier.
Timers add some overhead; matched wall-time tests below use uninstrumented code.
The instrumented source and raw logs are under `benchmarks/profile/`.

## Targeted changes

The supplied baseline already optimized monomial multiplication with a DAG.
Across all 395 six-loop kernels, its denominator expressions contained
1,078,524 ordered monomial additions. Sharing their exact prefixes reduces this
to 779,890 additions. A compressed trie stores only branch/terminal prefixes;
linear runs remain contiguous register accumulations, avoiding a scratch value
for every addition. The 8,401 numerator uses reduce to 4,691 unique coefficient
vectors. Their nonzero terms retain their original order.

Precomputed subset-choice totals remove the per-point recomputation of an
unchanged conditional normalizer. Fixed small arrays and reusable scratch remove
pointwise vector allocation. When L=6, K=0: the old unused shape logarithm and
regulator recurrence are not evaluated. At lower loops, reuse of the same sum of
edge coordinates removes duplicate exponentials. The same formulas remain in
the high-precision promotion paths; unlike C7, they were not the measured main
bottleneck and were not replaced by a new approximation.

## Matched benchmarks

`benchmarks/matched/` and `benchmarks/profile/` are the records of the original
delivery. They were produced by earlier versions of `tools/benchmark.py` and
`tools/profile.py` (different scope strings and fields; the profile directory also
holds manually collected `/usr/bin/time` outputs), under a four-CPU container quota.
They are kept unchanged as evidence; the shipped scripts write only into a new
`--output` directory. `benchmarks/matched/benchmarks.json` supplies all three repeats,
logs, graph selections, seeds, net matrices, native/reference result rows and scope.
The most expensive denominator counts selected the graph subsets, not favorable
observed output values. Both programs use strict GCC options and identical
scientific inputs. The reference's hard-coded four-thread setting is changed
ONLY to honor the requested thread count for this comparison.

| Workload | Original wall median | New wall median, 1 thread | Wall speedup | Integration-only speedup |
|---|---:|---:|---:|---:|
| 12 five-loop classes, 98,304 samples | 0.52 s | 0.37 s | 1.405x | 1.36x |
| 16 six-loop classes, 262,144 samples | 4.40 s | 2.58 s | 1.705x | 1.53x |

The wall ratios include process start-up and graph loading (about 0.04 s at five
loops, 0.5 s at six loops for the original, which loads all 395 six-loop classes);
the integration-only ratios compare the timed integration intervals of the same runs.

Six-loop peak RSS: 87,188 KiB versus 7,076 KiB. This includes selective loading:
original loads 395 classes, optimized loads the 16 assigned classes. It is not
an apples-to-apples claim about the bytes required to store one identical graph.
With all graphs loaded, memory is still dominated by graph/rate data. The
production wrapper bounds active graph count via `--checkpoint-tasks` instead.

Local optimized six-loop integration-only medians:

| Threads | Seconds | Speedup over one thread |
|---:|---:|---:|
| 1 | 2.55700 | 1.00x |
| 2 | 1.92912 | 1.33x |
| 4 | 0.96605 | 2.65x |

These are short workloads under a four-CPU cgroup quota. Timing variation,
SMT/NUMA placement and quota throttling affect them. They neither establish nor
promise linear strong scaling across large nodes. Multi-node throughput is NOT
benchmarked here; use the supplied job layout and profile your target hardware.

## Production throughput on SDSC Expanse (2026-09-28)

Measured with the shipped tooling (`benchmarks/expanse_2026-09/`), AMD EPYC 7742, GCC 13.3:

* **Per-sample cost.** A README-scale six-loop shard costs about 4.2-4.9e-9 core-seconds per estimated cost unit,
  about 11 µs per sample. `plan` uses this calibration (L6 4.7e-9, L3-L5 6.3e-9 s per unit) for its core-hour and
  wall-time estimates. At README point counts the whole campaign (both campaigns, loops 3-6) is estimated at 6.3
  core-hours of compute, and the measured L6 shards agree with the estimate to within 15%.
* **Utilisation.** Five L6 shards at 16 threads with 512-task, cost-ordered blocks:
  * OpenMP efficiency inside the native calls is 0.992-0.993;
  * overall core utilisation (task-seconds / (threads x elapsed)) is 0.825-0.926, and four of the five are >= 0.85.
  * Before this revision (8 threads, 32-task blocks in uid order) the same quantities were 0.91 and 0.67-0.73.
* **Fixed per-job cost.** Python start-up, verification of tools, inputs and executable, and staging of the
  job-private runtime take about 8-23 s per job. Choose `--shards` so that shards run for several minutes.
* **Matched benchmark on Expanse** (the shipped `tools/benchmark.py`):
  * one-thread wall speedup 1.50x (five loops) and 1.64x (six loops); integration-only speedup 1.45x for both;
  * six-loop integration with 1/2/4 threads takes 2.86/1.42/0.72 s.

## Complexity

For fixed six-loop graph inventory and K=6-L, per-point work is linear in the
shared arithmetic representation plus sampling dimension. The optimization does
not alter the asymptotic number of sample points needed for a requested accuracy.
For a checkpoint block with at most T tasks and W OpenMP threads, native memory is

    O(sum of selected graph states + W * largest numerical scratch
      + T * (jet dimension + direction-matrix size)).

It is independent of the sample count in those tasks and does not include a
replicate-by-graph result cube. Subset rate tables still have size 2^(2L); graph
and forest complexity are not magically polynomial in arbitrary loop order.
This implementation is limited to the prepared loops 3 through 6.

Planning and merging keep tasks in SQLite with an 8 MiB page cache and
file-backed sorting. Task storage remains linear in the number of chunks.
Final assembly stores only the small complete-replicate Taylor vectors. It does
not treat chunks as independent statistics. More shards do not create more
independent statistical information.

Checkpointing a handful of tiny samples is startup/I/O dominated. Choose chunks
large enough to amortize native startup, but small enough for load balancing and
bounded rework after interruption. Too many tiny checkpoints can stress a shared
filesystem. Stage immutable graph inputs on node-local storage when appropriate.

## Rebenchmark

    python3 tools/benchmark.py --output /path/to/a/new/directory

The output directory must not exist; the baseline is rebuilt there from
`reference/code/experiment.cpp` with the same compiler flags.

Run this separately from production. Use an otherwise idle allocation and collect
longer workload timings/NUMA counters on the real machine before extrapolating.
No sample-allocation change based on the final coefficient is performed.
