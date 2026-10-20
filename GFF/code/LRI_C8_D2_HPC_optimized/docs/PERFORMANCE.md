# Performance and HPC operating guide

This release optimizes the existing two-dimensional C8 calculation. It preserves
the graph kernels, importance distribution, random stream identities, precision
tiers, cancellation thresholds, Taylor recurrence, and deterministic merge order.
The original project and completed sampling campaigns are the baseline; this
release does not contain a newly estimated C8 value.

## Where the work goes

The completed 274,139,136-point calculation recorded 209,248.838 seconds of native
integration and 2,431.158 seconds of graph loading across its successful native
invocations. Integration accounts for 98.85% of their sum. These are summed
elapsed times, not measured process CPU seconds, and exclude driver overhead
and interrupted work. Free L8 accounted for 87.77% of recorded integration,
power L8 for 5.82%, and free L7 for 5.42%.

The bounded profiler covers all twelve free/power groups at L3 through L8,
69 distinct physical graphs, and 75,008 points. It selects structural size
extremes, primitive graphs, observed precision-promotion tails, and expensive
graphs from a bounded subset of production checkpoints. These deliberately
challenging strata are useful for finding bottlenecks; their average cost is
not an unbiased estimate of a complete campaign.

An initial eight-graph free-L8 probe attributed its integration as follows:

| Work | Share of instrumented integration |
|---|---:|
| Binary128 ordered denominator sums | 37.39% |
| Multiprecision ordered denominator sums | 25.18% |
| Multiprecision product DAG | 14.24% |
| Multiprecision exponentials | 8.54% |
| Importance mapping | 0.43% |

The remaining time includes long-double evaluation and other promoted work.
The probe's instrumentation added 9.6% elapsed time in one pair. The broader
profile confirms the same expensive stages. Actual speed comparisons use
uninstrumented workers with identical frozen tasks and alternating AB/BA order.
See `optimization_work/baseline_profile/README.md` and
`optimization_work/baseline_profile/matrix/profile_report.json` for full counts,
allocation traffic, retained vector capacity, and stage measurements.

## Measured application performance

The released default has no resolved serial runtime improvement. Median integration times are about 5% lower at two and four threads and about 4% lower at eight threads, with overlapping timing ranges at four and eight threads. Median peak RSS is 14.6–16.3% lower across the measured thread counts.

The table measures the released default, with grow-only storage disabled. All
24 native executions matched the original scientific outputs exactly. Each
execution uses ten frozen free-L8 graphs, sixteen replicates, 160 native tasks,
and 20,480 points, including 12,595 binary128 and 4,558 MP promotions.

| Threads | Baseline integration, median s [range] | Optimized integration, median s [range] | Baseline / optimized |
|---:|---:|---:|---:|
| 1 | 31.3963 [29.7765, 31.7945] | 31.5348 [28.0362, 31.5480] | 0.996x |
| 2 | 16.6904 [16.4945, 17.3771] | 15.8634 [15.1577, 16.1334] | 1.052x |
| 4 | 8.7870 [8.6338, 9.5060] | 8.3244 [8.3115, 8.7322] | 1.056x |
| 8 | 4.7793 [4.6179, 4.9206] | 4.6032 [4.4256, 4.7891] | 1.038x |

The two-thread ranges are separated in these three repeats; the one-, four-,
and eight-thread ranges overlap. Three counterbalanced AB/BA repetitions give
observed ranges, not a formal confidence interval. Scaling to eight threads is
6.851x relative to the optimized serial median and 6.569x for the baseline.

| Threads | Baseline peak RSS, median KiB | Optimized peak RSS, median KiB | Reduction |
|---:|---:|---:|---:|
| 1 | 50,416 | 42,556 | 15.6% |
| 2 | 51,480 | 43,080 | 16.3% |
| 4 | 53,788 | 45,264 | 15.8% |
| 8 | 57,964 | 49,480 | 14.6% |

The process affinity contains nine available logical CPUs. This is not evidence
of dedicated physical cores. Each child's own `wait4` record supplies CPU time
and RSS. CPU time includes graph loading and output serialization; its ratio to
integration wall time is an approximate upper bound on integration concurrency.
The final eight-thread ratios were about 7.47 CPUs for the baseline and 7.52
for the optimized worker. Scheduling/preemption and task balance still limit
what these measurements establish about a different cluster.

An earlier grow-enabled snapshot showed a larger serial gain in another timing
window. That snapshot also used the earlier native driver. Retention, code
layout, telemetry, and window-dependent CPU scheduling are confounded; its
speedup is not established for the released default and cannot be assigned
solely to vector retention.

Full repeat ranges, child resources, scoped attribution, source identities, and
limitations are in `verification/performance_summary.json` and
`docs/BENCHMARK_RESULTS.md`. Raw runs are in
`optimization_work/scaling_release/comparison.json`. No full production campaign
or multi-node Slurm run was performed for this performance study. Do not
extrapolate this intentionally difficult graph stratum or the synthetic addition
microbenchmark into a measured complete-campaign runtime.

## Kernel changes and their numerical contract

### Exact binary128 denominator addition

`src/positive_qadd.hpp` specializes addition of positive normal IEEE binary128
values under round-to-nearest, ties-to-even. It uses integer significands and
guard/round/sticky bits, preserving the original 113-bit rounded result of each
addition. The denominator summation sequence is unchanged. Negative values,
zeros, subnormals, nonfinite values, and overflow-risk operands use the
compiler's original addition. A rounding-mode check once per promoted call
keeps the compiler operation for directed rounding modes.

This is a numerical-value contract. The integer path does not synthesize
floating-point exception flags; production code never observes those flags.
Disable the specialization if embedding the helper in a program that requires
complete floating-environment side effects. It is used only in the measured
binary128 denominator bottleneck.

The focused comparison checks 3,678,840 exact-bit operand pairs and 1,048,576
chained additions against the compiler's binary128 operation, including tie
parity, sticky bits, exponent distances, carries, subnormal and overflow
fallbacks. Undefined-behavior sanitizer execution also passed.

### Exact L8 rate palettes

The original scaled long-double rates are stored once in a palette, and each
subset uses a byte index into that palette. No rate is recomputed or rounded
differently. The `dp` and `choice_total` arrays retain their original contents.
Tables with more than 256 distinct values, nonfinite values, or negative zero
retain dense storage, as do lower loop orders.

The focused test checks 1,458,176 values and signs. Across sixteen physical
graph/rate pairs, alpha payload storage falls from 16,777,216 to 1,052,672 bytes:
93.7% less alpha storage, or about 31.2% less storage for the three main sampling
tables together. This is an array-storage measurement, not a claim that whole
process RSS falls by 31.2%. Graph polynomial data, temporary preparation data,
thread scratch, MP limbs, allocator overhead, and libraries also occupy memory.

### Reusable promoted storage

Equal-precision scalar workspaces are reused across calls, avoiding repeated
construction of GMP/decimal temporaries while keeping arithmetic expressions
and their order. By default, promoted vectors retain the original resize
behavior. Defining `C8_ENABLE_PROMOTED_GROW_ONLY` optionally retains constructed
elements when moving to a smaller graph. Every read and write remains bounded
by the current graph's sizes.

The optional retention trades memory for fewer constructions: each vector can keep its largest
size seen, and the separate maxima need not come from the same graph. This
storage is independent of the number of integration points but grows with the
OpenMP team size and graph complexity. The measured attribution and RSS tables
are the basis for judging this tradeoff on a target machine. The bounded
three-repeat attribution found no demonstrated gain from retention (incremental
median ratio 0.976x, with overlapping ranges), so it is disabled by default.

### Build switches

The disable switches restore previous behavior; the enable switch opts into
retained vector objects. Rebuild into a new
binary before making a new plan; build identities are pinned within a campaign.

| Compiler definition | Behavior |
|---|---|
| `C8_DISABLE_FAST_Q_ADD` | Compiler binary128 addition everywhere |
| `C8_DISABLE_RATE_PALETTE` | Dense alpha arrays |
| `C8_DISABLE_PROMOTED_SCALAR_REUSE` | Local promoted scalar construction |
| `C8_ENABLE_PROMOTED_GROW_ONLY` | Opt into retaining constructed vector tails |
| `C8_DISABLE_PROMOTED_GROW_ONLY` | Force the default per-graph resize behavior, even if the enable switch is present |

For example, `make -B gmp CPPFLAGS='-DC8_DISABLE_FAST_Q_ADD'` creates a comparison
build when Boost/GMP are in standard include locations. Add the site's normal
include options if necessary. The required flags remain
`-std=c++17 -fopenmp -ffp-contract=off -fno-fast-math`. Fast-math and reduced
precision are not part of this optimization. GMP remains at 350 decimal digits;
the alternate Boost decimal backend remains at 300 decimal digits.

## Scaling and memory controls

Native integration parallelizes independent graph/replicate/point-interval
tasks with OpenMP. Cluster parallelism uses independent Slurm array elements.
Workers do not communicate during integration; the merge verifies complete
coverage and combines results in the same deterministic order.

For a fixed graph set and precision, runtime is linear in the number of sampled
points, apart from fixed graph preparation and checkpoint overhead. Increasing
point count does not allocate an array of all points. Graph sampling tables
still scale as `2^(2L)`; this release reduces a constant factor at L8 and does
not remove the exponential dependence on loop order. The scientific extension
implemented here stops at C8. Higher coefficient orders need new graph inputs,
regulator terms, and validation.

A useful memory budget per native worker is

`base + loaded graph payloads + threads × retained thread scratch + block rows`.

The checkpoint task limit bounds row buffers, while the new graph limit bounds
how many distinct graph payloads are loaded simultaneously. Neither is a hard
RSS byte limit. Inspect measured peak RSS on the actual graph mix before
setting a scheduler memory request.

| Planning option | Meaning |
|---|---|
| `--task-order graph` | Default: cost-balanced whole-graph placement, then graph-local blocks |
| `--task-order legacy` | Previous per-task placement and fixed task-count blocks |
| `--checkpoint-tasks K` | Hard maximum native task rows in one checkpoint |
| `--checkpoint-graphs G` | Hard maximum distinct graphs loaded in one checkpoint |
| `--checkpoint-seconds S` | Target summed modeled kernel core-seconds in a checkpoint; requires a measured cost model |
| `--chunk-points N` | Existing maximum interval length when creating a new plan |
| `--threads T` | OpenMP threads per worker |
| `--shards S` | Requested group shard count, subject to the plan's shard policy and available work |

Graph/time checkpoint limits require graph ordering. A complete graph bundle is
kept together when it fits; larger bundles are divided only between existing
native tasks. A single task above the time target is reported and retained.
The time target is not a wall-clock deadline: actual wall time also depends on
team occupancy, promotion frequency, graph loading, and scheduling. Adjust
`--chunk-points` in a fresh plan when individual tasks are too long. The samples
retain their absolute identities, although changing chunk boundaries can change
the last rounding bits of a combined sum.

Replaying the saved `a_free_L8` task table with a 120-core-second target reduced
maximum modeled checkpoint work from 605.854 to 119.993 core-seconds. Blocks
increased from 504 to 630, while graph loads stayed exactly 16,064 and all
257,024 task identities and costs were unchanged. This is evidence of finer
modeled restart granularity, not a measured native-runtime improvement. The
saved-table replay and its scoped memory/timing measurements are in
`verification/hpc_schedule_model_comparison.json` and can be repeated with
`tools/benchmark_schedule.py`.

Whole-graph assignment reduces repeated loading but cannot distribute one
graph's bundle over multiple array workers. At extreme shard counts, or when
a few graph bundles dominate, that granularity limits load balance. Compare
the plan's maximum shard cost with its mean; `--task-order legacy` permits
finer placement at the cost of repeated graph loads. Each block should also
contain enough native tasks to keep its OpenMP team occupied. A graph cap of
32 with sixteen replicates usually permits 512 tasks if point intervals are
not further chunked; it is an example, not a universal optimum.

Planning and merging keep task rows in SQLite. Planning closes each group DB
before opening the next, avoiding accumulation of separate 8-MiB page caches.
Coordinate validation streams the expected graph/replicate order instead of
building a Python list proportional to every expected row. The focused
32,768-coordinate test peaked at 3,709 Python-traced bytes for that validation
operation; this is not whole-process RSS. Merge batches inserts into private,
disposable SQLite scratch. Durable checkpoint publication remains unchanged.

`production.py merge --workers N` merges up to N independent groups in separate
processes. Each has its own scratch DB and preserves its within-group Decimal
addition order. More merge workers increase memory and disk traffic; the
default remains one. There are only 24 groups in a complete two-campaign plan.

## A cluster workflow

Build with the cluster's compiler and dependencies, and create a new pilot
using the optimized executable. Reusing a timing model from the old kernel or
another machine can give misleading shard costs and wall-time estimates.

```bash
make -j2 gmp
python3 tools/production.py plan /shared/project/c8-optimized-pilot \
  --seed "$(python3 -c 'import secrets; print(secrets.randbelow(2**63))')" \
  --backend gmp --purpose pilot --replicates 16 \
  --loop-points 3:16384,4:4096,5:1024,6:256,7:64,8:16 \
  --shards 64 --threads 16 --task-order graph \
  --checkpoint-tasks 512 --checkpoint-graphs 32

export C8_PACKAGE="$PWD"
export C8_RUN=/shared/project/c8-optimized-pilot
export C8_ENV_SETUP=/path/to/cluster-env.sh
export C8_SBATCH_ARGS="-A your_project -p your_partition --time=08:00:00"
export C8_THROTTLE=32
bash slurm/submit.sh
python3 tools/production.py status "$C8_RUN"
```

The point counts, team size, shard count, memory cap and wall-time shown are
starting examples. The pilot must measure the graph mix and hardware that will
be used in production. Slurm array concurrency throttling applies per array;
if the plan spans multiple array windows, `C8_THROTTLE` is not a single global
limit across all windows. Respect the site's account/job limits.

After the pilot's dependent merge and assembly finish:

```bash
python3 tools/make_cost_model.py "$C8_RUN" c8_optimized_costs.json
python3 tools/pilot_allocation.py "$C8_RUN" c8_optimized_allocation.json \
  --target-core-hours 10000 --replicates 64 --min-points 4096

python3 tools/production.py plan /shared/project/c8-optimized-production \
  --seed "$(python3 -c 'import secrets; print(secrets.randbelow(2**63))')" \
  --backend gmp --purpose production --replicates 64 \
  --allocation c8_optimized_allocation.json --cost-model c8_optimized_costs.json \
  --shards 128 --threads 16 --task-order graph \
  --checkpoint-tasks 1024 --checkpoint-graphs 16 --checkpoint-seconds 1800
export C8_RUN=/shared/project/c8-optimized-production
```

The example 10,000 core-hour allocation budget covers the model's two campaigns
at the stated replicate count; it is not a forecast of certified accuracy.
The 1,800-second checkpoint target means summed modeled kernel core-seconds.
Inspect the generated plan, especially largest indivisible tasks, shard
imbalance, and block task counts, before interpreting its wall-time estimate.
Pilot samples are not pooled into the independently seeded production estimate.

The Slurm worker defaults to `OMP_DYNAMIC=FALSE`, `OMP_PLACES=cores`, and
`OMP_PROC_BIND=close`. Explicit `OMP_PLACES` and `OMP_PROC_BIND` values are
honored, allowing measured comparison of `close` and `spread` on the site's
NUMA topology. Compare one worker per socket with a whole-node team using the
same frozen benchmark tasks. Avoid oversubscribing cores with multiple workers
and nested numerical-library threads. These are tuning choices to measure,
not evidence of scaling on an untested cluster.

## Shared filesystem traffic

Ordinary execution already reads and stages only the graph members needed by
each checkpoint. Graph-local blocks reduce repeated member reads and graph
preparation. Full-pack staging is optional and can be more expensive when an
array element uses only a small part of a pack.

When many workers on the same node will reuse a pack, a persistent user-owned
node-local cache can amortize the full copy:

```bash
export C8_STAGE=1
export C8_PACK_CACHE=/local/scratch/your_user/c8-pack-cache
export C8_MERGE_WORKERS=4
bash slurm/submit.sh
```

Choose a real node-local path provided by the site; a shared filesystem path
defeats the purpose. It must outlive an individual job's disposable staging
directory and must not be inside that directory. Cache publication uses a lock,
private copy, complete SHA-256 verification, and atomic publication. A verified
receipt is bound to file metadata. Every graph member is still hashed before
use. Set `C8_REVERIFY_PACK_CACHE=1` to fully rehash hits as well. Cache corruption
recovery and concurrent reuse are covered by the workflow tests. Cache lifetime
and quota cleanup remain the site's/user's responsibility.

`C8_MERGE_WORKERS` requests the same number of CPUs for the merge allocation,
capped at the number of groups. The merge script refuses a worker count larger
than its allocated CPUs. `slurm/resubmit.sh` retains checkpoint-aware recovery;
committed blocks are checked and skipped rather than recomputed.

## Resource telemetry in native output

The new `performance` object is supplementary and does not enter scientific
results or checksums of scientific row values.

| Field | Definition |
|---|---|
| `actual_threads` | Team size observed inside the OpenMP parallel region |
| `task_wall_seconds_sum` | Sum of native task elapsed times |
| `observed_task_parallelism` | Task elapsed sum divided by integration elapsed time |
| `wall_team_utilization` | Task elapsed sum divided by integration elapsed time and team size |
| `cpu_user_seconds`, `cpu_system_seconds` | Process-lifetime CPU counters sampled after integration, summed across threads |
| `peak_rss_kib` | Process-lifetime peak resident memory in KiB, sampled after integration |

CPU and RSS include preparation/loading and exclude subsequent output
serialization. Task elapsed time can include preemption; `wall_team_utilization`
is task occupancy, not measured hardware CPU utilization. Unsupported resource
counters are null. The performance fields are reported once per native call;
there are no new timer calls inside the point loop.

## Correctness and reproduction

`verification/final_default_kernel_checks.json` and
`verification/final_native_release_checks.json` record exact native replay,
four-rounding-mode direct tests for both precision backends, source hashes,
and independent 450-digit point checks. Native replay includes all twelve
sector/loop groups, all three layouts, rates 0.6/0.8/0.9, 32/60-bit nets,
high-index seeks, and unequal split checks. Every coefficient, promotion count,
sample identity, and maximum point magnitude matches the original for identical
task shapes. The separate split-sum comparison permits a normalized 5e-16
rounding difference.

The HPC tests compare 368 native tasks across 24 groups under changed placement,
with exact replicate jets and graph-replicate tables. They cover restart,
missing and corrupt checkpoint refusal, staged execution, cache reuse/recovery,
and serial versus parallel merge. These local tests do not certify an actual
Slurm installation or predict multi-node throughput.

Run from this package root, after rebuilding the optimized binary on the target
cluster. The included pristine reference is rebuilt with that binary's recorded
compiler settings; the original input packs are not needed for frozen replay:

```bash
python3 tools/benchmark_native.py build-baseline --backend gmp \
  --output verification/local_baseline_gmp

python3 tools/benchmark_native.py compare \
  --manifest optimization_work/baseline_profile/matrix/manifest.json \
  --baseline verification/local_baseline_gmp --candidate bin/c8d2_gmp \
  --output verification/local_exact_replay --threads 1 2 --repeats 1

python3 tools/benchmark_native.py compare \
  --manifest optimization_work/baseline_profile/scaling/manifest.json \
  --baseline verification/local_baseline_gmp --candidate bin/c8d2_gmp \
  --output verification/local_scaling --threads 1 2 4 8 --repeats 3

python3 tools/benchmark_native.py direct --source ../LRI_C8_D2_HPC \
  --candidate-header src/kernel.hpp --backend gmp \
  --output verification/local_direct
python3 tests/hpc_scheduler.py --output verification/local_scheduler.json
```

Use fresh output directories and otherwise idle allocated CPUs. The frozen
fixtures are included, so replay does not require a full new production run.
Absolute paths in historical records describe provenance; use the explicit
`--baseline` and `--source` arguments when reproducing elsewhere.

## External implementation references

- GMP, [Initializing floats](https://gmplib.org/manual/Initializing-Floats):
  fixed-precision allocation and object initialization.
- Slurm, [Job arrays](https://slurm.schedmd.com/job_array.html): array concurrency
  limits and `MaxArraySize`.
- OpenMP, [OMP_PROC_BIND](https://www.openmp.org/spec-html/5.1/openmpse61.html) and
  [OMP_PLACES](https://www.openmp.org/spec-html/5.1/openmpse62.html): affinity
  controls. Site topology and binding behavior require local measurement.
