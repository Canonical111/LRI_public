# Performance report: full C7(2)

> Revision 2026-10-02: the kernel is unchanged (one Boost compatibility hunk).
> New below: measured production cost shares, the planning calibration of both
> backends, and the measured block throughput. Earlier benchmark numbers are retained
> records; packaging checks are in `delivery/DELIVERY.md`.

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

## The 2026 symmetry production: where the CPU went

The production campaign run1-20260930-m4096 (delivered tools, gmp, M=4096,
R=64, recompute primitives at 16384 points, 1,280 jobs) used 8,892 task
core-hours on 14 AMD nodes (one 64-thread lane each: <NODE>-<NODE> AMD EPYC 7532,
<NODE>-<NODE> AMD EPYC 7543) and 14 Intel
nodes (two 20-thread lanes each), about 6.5 h wall. The power sector took
59.9% of the task CPU (power L7 alone 48.3%) for 0.76% of Var(C7); the 44
primitive classes 14.4% for 7.4e-5 (primitive SE 0.0045). `docs/HPC.md` gives
the opt-in allocation options and the projections for the recommended recipe;
`benchmarks/symmetry_2026-10/production_shares.{py,json}` the derivation.

### Planning calibration

`tools/calibration.json` holds seconds of native task time per inventory proxy
unit (proxy cost per point = max(1, terms x monomials)), derived by
`tools/calibrate.py` from the production checkpoints of the 64-thread AMD lanes
(Slurm jobs 566259-566272; hosts <NODE>-<NODE>, AMD EPYC 7532, and <NODE>-<NODE>, AMD
EPYC 7543, where <NODE> and <NODE> are inferred from the node range, not logged;
denominators recomputed from the inventory):

| Sector | L | s per proxy unit | tasks | task core-hours |
|---|---:|---:|---:|---:|
| free | 3 | 2.609e-08 | 4,214 | 1.5 |
| free | 4 | 9.513e-09 | 11,155 | 5.5 |
| free | 5 | 4.296e-09 | 41,623 | 34.6 |
| free | 6 | 2.129e-09 | 87,874 | 140.2 |
| free | 7 | 6.859e-09 | 378,936 | 1,859.1 |
| power | 3 | 6.917e-08 | 13,440 | 5.4 |
| power | 4 | 2.575e-08 | 70,400 | 60.0 |
| power | 5 | 1.470e-08 | 99,008 | 253.5 |
| power | 6 | 1.282e-08 | 51,975 | 467.2 |
| power | 7 | 1.265e-08 | 95,366 | 2,471.3 |

Per proxy unit the Intel 20-thread lanes were between 7% faster (free L6) and 39%
slower (power L6) than these AMD lanes (power L4-L7: 30-39% slower).

The decimal rows were measured the same way on one AMD EPYC 7543 node (<NODE>,
64 threads, job 567667) from every job of a small decimal plan (`--multiplier 16
--replicates 8 --shards 1 --checkpoint-tasks 1024`). They come from a much smaller
plan than the gmp rows (M=16 against M=4096), so they carry more noise and less
cache and load realism. The backend ratio is taken on matched hardware: job
567730 ran the same plan (same seed and jobs) with gmp on <NODE>, also an AMD EPYC
7543 (`benchmarks/symmetry_2026-10/backend_ratio/`):

| Sector | L | decimal s per unit (567667) | gmp s per unit (567730) | decimal / gmp, same CPU | gmp 567730 / production gmp row | tasks |
|---|---:|---:|---:|---:|---:|---:|
| free | 3 | 2.657e-08 | 2.335e-08 | 1.14 | 0.89 | 96 |
| free | 4 | 9.310e-09 | 9.127e-09 | 1.02 | 0.96 | 256 |
| free | 5 | 4.197e-09 | 4.722e-09 | 0.89 | 1.10 | 1,280 |
| free | 6 | 2.162e-09 | 2.164e-09 | 1.00 | 1.02 | 6,320 |
| free | 7 | 8.746e-09 | 6.779e-09 | 1.29 | 0.99 | 38,880 |
| power | 3 | 5.843e-08 | 7.154e-08 | 0.82 | 1.03 | 128 |
| power | 4 | 2.657e-08 | 2.558e-08 | 1.04 | 0.99 | 640 |
| power | 5 | 1.836e-08 | 1.410e-08 | 1.30 | 0.96 | 928 |
| power | 6 | 2.111e-08 | 1.262e-08 | 1.67 | 0.98 | 1,776 |
| power | 7 | 2.503e-08 | 1.252e-08 | 2.00 | 0.99 | 9,472 |

On matched hardware decimal costs 0.82-1.14x gmp per proxy unit up to L6 except
power L5 (1.30x) and power L6 (1.67x), where the precision fallbacks dominate the
cost (see the profile above; the two backends differ only in the last fallback
tier), and 1.29x (free) and 2.00x (power) at L7, consistent with the matched
benchmarks above. The gmp rows of the production (mixed EPYC 7532/7543 lanes, M=4096)
agree with the EPYC 7543 gmp run at M=16 within 4% for L >= 6 and within 11%
everywhere. The single free-L7 rate blends primitive and non-primitive classes
(`docs/HPC.md`, Estimates).

### Block throughput

A block is one native process; its cores idle at the end of the block while
the slowest tasks finish (OpenMP barrier) and during the next start-up. The
review modelled 0.60-0.70 busy cores for the old README recipe (8 threads,
32-task blocks) and 0.83-0.875 for the production's 64 threads and 1024-task
blocks. This revision orders each shard by estimated cost (`pos`), so a block
holds tasks of similar cost, defaults to 512-task blocks, and refuses threads >
checkpoint_tasks. Acceptance criterion: for at least 3 L7 shards of about
1,500 estimated core-seconds or more at 64 (AMD) or 20 (Intel) threads with
checkpoint_tasks >= 16 x threads, sum of task-seconds / (threads x elapsed) is
reported, target >= 0.80.

Measured on symmetry (job 567668, <NODE>, AMD EPYC 7532, 64 threads, gmp,
1024-task blocks; `benchmarks/symmetry_2026-10/evidence/drills/throughput.json`):

| Index | Shard | Blocks | Tasks | Task seconds | Wall s | Busy cores | OpenMP efficiency |
|---:|---|---:|---:|---:|---:|---:|---:|
| 4 | a_free_L7 shard 0 | 12 | 12,030 | 13,916 | 238.9 | 0.910 | 0.967 |
| 5 | a_free_L7 shard 1 | 12 | 12,029 | 13,946 | 239.2 | 0.911 | 0.968 |
| 6 | a_free_L7 shard 2 | 12 | 12,030 | 13,931 | 239.6 | 0.908 | 0.966 |
| 15 | a_power_L7 shard 0 | 3 | 2,326 | 15,750 | 259.9 | 0.947 | 0.958 |
| 16 | a_power_L7 shard 1 | 3 | 2,326 | 15,857 | 262.3 | 0.945 | 0.956 |

Busy-core utilisation is 0.909-0.947 (target met) and the OpenMP efficiency
inside the native calls 0.956-0.968; the rest is per-block start-up (serial
graph loading) and the barrier. The plan estimated 13,279 task seconds per free-L7
shard and 13,562 per power-L7 shard; measured were about 13,930 (+5%) and
15,800 (+17%).

## Reproduce and extend measurements

```bash
make -j4 all gmp
python3 tools/profile.py --output /scratch/c7-profile
python3 tools/benchmark.py --output /scratch/c7-bench
python3 tools/benchmark_memory.py --output /scratch/c7-memory
```

All benchmark and profile builds use the Makefile's flags (`common.cxx_command`).
Raw `.json`, `.log`, `.time` and task/net files are under `benchmarks/`. The
profiling subsets are fixed from original expensive workload records. Measure
new representative graph strata and costs on the actual cluster before deciding
CPU binding, processes per socket and chunk sizes. Compiler/link-library and
Python versions are recorded; `requirements-tested.txt` gives the tested Python
versions.

No full high-statistics physics campaign was rerun. The archive's accepted full
C7 value is reproduced from saved data, not improved by these timing tests.
