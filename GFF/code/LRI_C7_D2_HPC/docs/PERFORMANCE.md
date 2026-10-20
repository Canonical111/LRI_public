# Performance report: full C7(2)

> Delivery note: earlier benchmark numbers below are retained records.
> Fresh packaging checks and rebuilt benchmark fixtures are documented in
> `delivery/DELIVERY.md` and `delivery/fresh_checks.json`.

## Method and scope

The reference is the actual delivered complete C7(2) implementation in
`reference/`, not the older C6 or one-dimensional worker. Its long-double pass
already shared products and ordered denominator prefixes. Profiling identified
the higher-precision paths, not that already-optimized ordinary pass, as the
expensive part of difficult seven-loop kernels.

All numerical workloads use matched graph IDs, seeds, complete point intervals,
Sobol matrices, rates, strict GCC flags and accumulator modes. Timings below are
medians of three fresh process runs, including loading. They are selected
expensive workloads (16 graphs each), not an end-to-end production benchmark or
claim of uniform speedup across every graph. Thread tests use the same workloads.
The host is Linux x86-64, GCC 14.2.0, with a four-core cgroup CPU quota.

## Profiling before optimization

`benchmarks/profile/profile_summary.json` records separately timed original
long-double, binary128 and Boost 300-decimal calculations. Higher-precision
fallbacks account for approximately:

| Selected workload | Fraction of integration interval in quad + MP |
|---|---:|
| Free, six loops | 9.6% |
| Free, seven loops | 95.1% |
| Power, six loops | 93.3% |
| Power, seven loops | 97.3% |

At seven loops the free test makes 10,182 quad promotions and 1,096 MP promotions
in 16,384 points; the power test makes 12,957 and 2,100. This explains why an
optimization aimed only at the ordinary pass would accomplish little here.
Instrumentation overhead is present in these diagnostic ratios. Production
binaries contain no per-point clocks.

## Implemented kernel changes

1. Reuse ordered expression prefixes and identical numerators in **all** precision
   tiers. Each polynomial's arithmetic order is retained; cached values replace
   identical recomputation, not an approximate expression.
2. Reuse per-thread promoted scratch between points, removing repeated container
   construction in the fallback path. Library internals may still allocate.
3. Skip the MP error estimate that the reference computed but never used. The
   quad error estimate remains, since it decides whether to promote further.
4. Share immutable Sobol direction matrices rather than copying one per task.
5. Preserve the existing product DAG, fixed K=0 work elimination, and
   precomputed importance normalizers. These pre-existing optimizations are
   not claimed as new gains.

The optional GMP build changes the final multiprecision backend to 350 decimal
digits. The default build retains the original 300-decimal backend. This is an
explicit numerical backend change, not lower-precision arithmetic. See
`NUMERICS.md` for the contract and tests.

## Matched wall-time measurements

| Workload | Points | Original | Optimized decimal | Optimized GMP 350 | Original / GMP |
|---|---:|---:|---:|---:|---:|
| free, 6 loops | 131,072 | 1.437 s | 1.372 s | 1.368 s | 1.05x |
| free, 7 loops | 16,384 | 11.911 s | 9.042 s | 4.243 s | 2.81x |
| power, 6 loops | 131,072 | 17.341 s | 13.797 s | 7.524 s | 2.30x |
| power, 7 loops | 16,384 | 12.260 s | 9.954 s | 3.995 s | 3.07x |

The modest improvement on the free six-loop workload is consistent with its
low promotion rate. The data do not support a blanket 3x claim for all workloads.
All tested printed scientific rows and promotion counts match the reference.

## Local parallel measurements (integration time)

| Workload | Threads | Time | Speedup over optimized one thread |
|---|---:|---:|---:|
| free, 7 loops | 1 | 4.171 s | 1.00x |
| free, 7 loops | 2 | 2.339 s | 1.78x |
| free, 7 loops | 4 | 1.182 s | 3.53x |
| power, 7 loops | 1 | 3.939 s | 1.00x |
| power, 7 loops | 2 | 1.914 s | 2.06x |
| power, 7 loops | 4 | 1.051 s | 3.75x |

These are four-core local VM measurements. No multi-node, heterogeneous-node,
NUMA or network-filesystem scaling benchmark was performed. Slurm array workers
are independent by construction; actual cluster efficiency must be measured on
site. Pilot timings can be frozen into the task planner for better shard balance.

## Memory and input I/O

On the identical 590-graph seventh-order power set, a load-and-one-point-per-
stratum test measured **486.43 MiB peak RSS** for the original monolithic power
producer versus **31.13 MiB maximum RSS** with 32-task optimized blocks. Printed
values match. This is a memory test (1,180 total points), not a precision
calculation or useful runtime comparison.

On matched *small* 16-graph workloads, both implementations already use about
17--20 MiB at seven loops. The optimization is not advertised as a large memory
reduction when the old program was already given a small task block.

Runtime packs preserve original graph bytes. Indexing them avoids thousands of
shared-filesystem metadata operations; each block seeks, hashes and stages only
its assigned members. Optional node-local staging copies one whole relevant
pack to amortize shared reads. Full numerical point arrays are never stored.

For fixed loop order and checkpoint size, increasing points does not grow native
sample memory. It grows work, task/checkpoint count and disk output. Task and
merge sorting is disk-backed SQLite (8 MiB cache); graph/group metadata and
final replicate totals remain in Python RAM. Within-graph importance DP still
has O(2^(2L)) storage, and graph/forest algebra grows intrinsically with loop order.
This delivery is supported through seven loops only.

## Backend experiment that was not adopted

A Boost `cpp_bin_float<350>` fallback was also tested at the same higher precision.
It did not beat the GMP candidate: the exploratory seven-loop free/power times
were about 10.16/13.42 seconds versus 4.95/4.09 seconds for GMP in that exploratory
run. It is not enabled in the deliverable. The chosen arithmetic backend is an
explicit opt-in; the reference-decimal alternative remains supported.

The reported performance claims come from the later matched median table above,
not from these single exploratory timings. No MPFR benchmark or claim is made.

## Reproduce and extend measurements

```bash
make -j4 all gmp
python3 tools/profile.py --output /scratch/c7-profile
python3 tools/benchmark.py --output /scratch/c7-bench
python3 tools/benchmark_memory.py --output /scratch/c7-memory
```

Raw `.json`, `.log`, `.time` and task/net files are under `benchmarks/`. The
profiling subsets are fixed from original expensive workload records. Measure
new representative graph strata and costs on the actual cluster before deciding
CPU binding, processes per socket and chunk sizes. Compiler/link-library and
Python versions are recorded; `requirements-tested.txt` gives the tested Python
versions.

No full high-statistics physics campaign was rerun. The archive's accepted full
C7 value is reproduced from saved data, not improved by these timing tests.
