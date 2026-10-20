# C6(3) performance and scaling

## Profiling before optimization

`tools/profile.py` instruments the **original** d=3 formulas in a scratch copy;
`reference/` is never edited. One thread is used to separate timers. The frozen
new-b reference allocation selects the active strata, with 256 points per
stratum and two randomized replicates for this test.

| Loop order | Samples | Integration (s) | Ordinary kernel (s) | binary128 (s) |
|---|---:|---:|---:|---:|
| 3 | 2,560 | 0.003818 | 0.001238 | 0 |
| 4 | 8,192 | 0.022124 | 0.006987 | 0 |
| 5 | 38,912 | 0.173814 | 0.086091 | 0.001345 |
| 6 | 187,904 | 2.147249 | 1.418433 | 0.064774 |

The six-loop test makes 115 binary128 calls and no 300-decimal calls. Ordinary
kernel evaluation is 66.1% of this interval; binary128 is 3.0%. Instrumentation
itself adds overhead, particularly in the smallest workloads. These are not
production precision runs. See `benchmarks/profile/profile_summary.json`.

## Changes that target the measured work

1. Retain the existing shared monomial-product DAG. Build a trie of ordered
   monomial-index sequences and compress its unbranched segments. Each
   denominator is reconstructed in its original addition order; prefix sums
   common to several forest terms are computed once.
2. Evaluate each distinct numerator coefficient vector once, sharing both its
   signed value and absolute-value bound. Preserve the order of the final
   signed forest sum.
3. Reuse thread-local scratch for geometry, products, prefix sums and numerators.
   Precompute the ordered-sector sampling totals, instead of rebuilding them
   at every point.
4. At loop six, compute only the required zeroth regulator coefficient. The
   shape logarithm and Taylor recurrence are dead work there, not at lower loops.
5. Selectively load the graphs named by one checkpoint block. Share immutable
   graph data among its OpenMP threads, rather than copying the full inventory.

The d=3 denominator is **U*sqrt(U)** at every precision tier. It was not replaced
with U or an approximate power. An inventory inspection found no identical
complete denominators repeated within a graph's list, so caching square roots
would not eliminate calls; no such cache was added. The 3% higher-precision
fallback path keeps its reference log-sum/exponential formula unchanged.

## Matched benchmarks

`python3 tools/benchmark.py --output /scratch/$USER/c6-d3-bench` rebuilds the
reference with the same strict flags as the new executable. The only change
in that benchmark copy is allowing its thread count to follow the environment.
The native worker uses compensated task sums; the reference uses its original
accumulation. Numerical differences are checked after every workload.

Each record is the median of three runs. Selected graphs are the 12/16 with
largest original denominator-addition counts; this is an expensive subset,
not a representative random sample of all graphs.

| Workload | Reference wall (s) | New wall (s) | Wall gain | Reference kernel (s) | New kernel (s) | Kernel gain |
|---|---:|---:|---:|---:|---:|---:|
| 98,304 points, five loops | 0.53 | 0.36 | 1.47x | 0.508809 | 0.350679 | 1.45x |
| 262,144 points, six loops | 4.20 | 2.58 | 1.63x | 3.669699 | 2.542483 | 1.44x |

The reference loads the whole loop inventory (76 or 395 graphs), whereas the
new executable loads 12 or 16 selected graphs. RSS at six loops was 87,188 KiB
versus 7,192 KiB. The reduction includes avoiding full-inventory loading; do not
interpret it as a universal per-node memory figure. Warm, long-running jobs
may see a gain closer to the kernel-only ratio.

Matched fallback counts were 21 at five loops and 386 at six loops, for both
implementations; neither workload invoked the final precision tier. Maximum
normalized matched-jet differences were 1.93e-18 and 2.91e-18.

## Local strong scaling

Same six-loop work, not a weak-scaling test:

| Threads | Integration (s) | Relative to one thread |
|---|---:|---:|
| 1 | 2.542483 | 1.00x |
| 2 | 1.352965 | 1.88x |
| 4 | 0.810918 | 3.14x |

The host is x86-64, GCC 14.2.0, under a four-CPU cgroup quota. Binding used
`OMP_PLACES=cores`, `OMP_PROC_BIND=true`. See `benchmarks/environment.json`
and the raw `/usr/bin/time -v` logs. **No multi-node, large-NUMA, GPU, or
heterogeneous-architecture performance benchmark was run.**

## Memory and work complexity

At fixed loop order the sample cost remains linear in point count. For a work
block, graph storage depends on its distinct graph count, not on the full
campaign's number of samples or replicas. Each thread has reusable scratch.
The native output holds at most `checkpoint_tasks` rows. Sobol direction data
are loaded only for the replicas referenced by that block.

The planner and merger store/sort task rows on disk in SQLite. They use an
8 MiB database cache and external temporary storage; the scheduler heap is
O(number of shards). Final uncertainty assembly retains the small
replicate-by-Taylor-coefficient arrays, O(replicates), **not** the entire
replicate-by-graph-by-point cube. Optional per-graph diagnostics stream to CSV.

The original subset rate table is still of size 2^(2L) per graph. Graph and
forest counts also grow with loop order. This package supports the existing
loops 3--6; it does not change that fundamental scaling or promise an
arbitrary-loop extension. All thread/rank replication limits refer to sample
scaling **within this finite inventory**.

## Cluster tuning

Every checkpoint block is one native process ending at an OpenMP barrier; tasks inside a shard run in frozen
estimated-cost-descending order, so a block holds tasks of similar cost. Use `--checkpoint-tasks` of at least 16-32
times the thread count (default 256; `run` refuses more threads than tasks per block), and choose `--shards` so that
the printed largest shard wall time is several minutes or more (per-job start-up, verification and staging take
seconds). Choose `chunk-points` so a slow task does not dominate the checkpoint interval. The frozen allocation is a validated starting point,
not a cost-optimal guarantee for a new CPU. Rate, allocation, precision and
mapping changes require a new frozen campaign, not mid-run edits.

Node-local staging reduces shared-filesystem reads. Rate-limit arrays and
checkpoint publication according to site policy. Cross-node arithmetic order
is deterministic at merge, but a different compiler/architecture need not
produce bitwise-identical long-double elementary functions.

## Production throughput on SDSC Expanse (2026-09-28)

Measured with the shipped tooling on AMD EPYC 7742, GCC 13.3 (`benchmarks/expanse_2026-09/`):

* **Calibration** (12 `slurm/run_array.sh` elements on the shared partition at 16 CPUs, arrays 54510585-54510591):
  seconds per estimated cost unit L3 3.01e-8, L4 1.27e-8, L5 6.18e-9, L6 3.62e-9 (`CALIBRATION` in
  `tools/production.py`); a compute-node cross-check (job 54510049) agrees within 2.4%. The cost model
  max(32,additions) omits the fixed per-sample overhead that dominates the small L3/L4 graphs. A README-scale campaign
  (multiplier 4, 64 replicates, both campaigns) is about 4.7 core-hours, L6 about 88% of it.
* **Throughput pilot** (shared partition): 8 L6 shards of about 1,860 estimated core-seconds at 16 threads with
  512-task, cost-ordered blocks: Σ task-seconds 1860-2108 per shard, OpenMP efficiency inside the native calls
  0.992-0.998, overall core utilisation (task-seconds / (threads x sacct elapsed)) 0.922-0.940 on 7 shards and 0.843
  on one. The compute-partition cross-check gave 0.886-0.945 on 7 shards and 0.746 on one (a slow first job on its
  node).
* **Matched benchmark on Expanse** (the shipped `tools/benchmark.py`, job 54510646): one-thread wall speedup 1.61x
  (five and six loops); integration-only 1.40x and 1.42x. Wall ratios of these sub-second workloads vary between runs
  (1.45x and 1.61x in the cross-check); the integration-only ratios are stable.
* **Fixed per-job cost.** Python start-up, verification and staging of the job-private runtime take seconds per job;
  choose `--shards` so shards run for minutes.
