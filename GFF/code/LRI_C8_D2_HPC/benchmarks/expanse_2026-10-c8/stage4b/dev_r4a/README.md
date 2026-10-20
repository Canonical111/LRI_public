# R4a development evidence (Stage 4b, branch opt-r4a)

**Integration outcome (2026-10-04): reverted.** On `c8`, A-PERF-2 measured ×1.0093 on the L8 sweep sample (job 54669709), below the 3% bar. The
code was reverted in ea59445; this folder stays as the record (`../integration/`, `docs/PERFORMANCE.md` "Stage 4b integration").

**Verdict.**
- R4a is exact: the mpf calls that produce values are the baseline's, call for call, and every gate run here is
  bitwise.
- R4a is far below A-PERF-2's 3% bar. The MP tier gets 1.8% faster (micro-benchmark), which is +0.6% (free) and +1.2%
  (power) on the heavy L8 blocks, socket-paired. About +0.5% is expected over the whole L8 population.
- Under A-PERF-2 it is reverted. This folder records the numbers.

## What changed

R4a is defined in PLAN "Performance plan", in the Stage-4b table.

**Code.** All of it is in `src/kernel.hpp`, under `#ifdef C8_USE_GMP`. The decimal build keeps the generic template, and
its preprocessed source and binary are unchanged.
- `calculate_shared_gmp<NeedError>` holds the MP tier's new body.
- Two explicit specializations, `calculate_shared<MP,false>` (the release build) and `calculate_shared<MP,true>` (the
  ratio-histogram build), forward to it.

**How it works.**
- The temporaries are per-thread and preallocated: `GmpScratch` holds `S`, `c`, `p`, `q`, `a`, `val` and `err` beside
  the arrays.
- The mpf calls are made directly, in place: `mpf_add`, `mpf_mul`, `mpf_div` and `mpf_set_si` on the same operands and
  into destinations of the same precision (20 limbs), in the order the Boost 1.77 expression templates make them.
  `kernel.hpp` lists that order.

**Host-approved deviation: copy elision.** These copies are gone:
- the exact same-precision copies `T v=sums[parent]`, `sums[j+1]=v`, `numerator[j]=n` and `abs_numerator[j]=ab`;
- the copy and swap of `xs[j]=x[j]` when shift = 0 (the products then read `x[j]`).

The first add of a segment reads `sums[parent]` directly. This is exact for two reasons:
- Every mpf result has at most prec+1 limbs, so `mpf_set` copies it exactly.
- An mpf result depends only on the operands' sign, size, exponent and limbs and on the destination's precision. It
  does not depend on where they live or on aliasing.

**Kept as they were.**
- The calls to `set_si(0)` on the unused `ab` and `err`, so that the value-producing call sequence is the same call for
  call.
- Boost's division-by-zero check.
- The MP exponentials, their arguments and the MP → long double conversion.

**Commits.**
- 6bdc081: the code, the tracer, the differential test and the scripts.
- 964f39d: tracer classes; see "Call sequence".
- The final commit adds this folder, the CHANGELOG entry and the delivery manifest.

## Jobs (Expanse; account <ACCOUNT>; site deviation U1)

| Job | Where | What | Result |
|---|---|---|---|
| 54666232 `c8d2-r4a-build` | shared, 16 CPUs, 32 GB, <NODE>, 3:25 | Build of the export of 6bdc081 (`setup/export_check_6bdc081cc8bd.json`: 5,573 files equal), the trace (first tracer) and `r4a_mpdiff` | Decimal `3dbd51bb…` byte-identical to Stage 3. Gmp `2fab1328…`, prof `081b134c…`, ratiohist `6edf48d5…`. Mpdiff: 0 mismatches. Trace: the V digests are identical, but the job exits FAILED, because the first tracer filed `get_prec`, Boost's copy-constructor precision query, under queries (see "Call sequence") |
| 54666233 `c8d2-r4a-node` | compute | The first node job, afterok on 54666232 | Cancelled: the dependency could never be satisfied. It never ran |
| 54666291 `c8d2-r4a-node` | compute exclusive, <NODE>, 18:51 | Speed (`r4a_speed.py`), G-L8SELF, and the validate parts describe, replay and diagnostics, on the 6bdc081 export | All passed |
| 54666315 `c8d2-r4a-trace` | shared, 4 CPUs, 8 GB, <NODE>, 2:18 | The trace again, with the 964f39d tracer (export `setup/export_check_964f39d13aec.json`: 5,579 files equal), on the executables of 54666232 (sha256 checked) | 11/11 rules pass |

**Bookkeeping.**
- Before every sbatch, the H7E-R admission and this agent's caps (1 compute node, 8 shared jobs) were checked:
  `admission/h7e_r_admission.jsonl` and the squeue snapshots beside it. Every job started on submission or within
  20 minutes.
- Final states are in `admission/sacct_r4a.txt`.
- Cost: about 41.3 SU (0.9 + 40.2 + 0.2).
- Lustre files: 1,199,640 before and 1,241,067 after; the count includes other agents' jobs.
- Slurm logs are in `logs/`; evidence directories are named after their job.

## Call sequence (r4atrace.54666315.0/trace/)

**Method: an LD_PRELOAD tracer.** `mpf_trace.c` interposes the 26 `__gmpf_*` functions the worker imports (`nm -D`),
plus `mpf_abs`.
- For each top-level call it records:
  - the operation;
  - the destination's precision and its representation after the call (sign and size, exponent, and an FNV-64 hash
    of the limbs);
  - the representation of every operand before the call.
- Addresses are never recorded.
- Calls fall into four classes:
  - L, lifetime: `init2`, `clear`;
  - C, copies: `set`, `swap`, and `get_prec`, the precision query Boost's copy constructor and copy assignment make
    before their `mpf_set`;
  - Q, queries;
  - V, value-producing: everything else.

The first job, 54666232, had `get_prec` under Q. Its V digests already matched in 8/8 runs. Its point logs are not
kept: their sha256s are in `r4abuild.54666232.0/trace/point_logs_first_run.sha256`.

**One MP point.** The point is graph 24401 of `heavy_power_L8`, point 0, net replicate 0, the first MP point of the
graph. It is traced at 1 thread, with the full logs in `point_{base,new}.log.gz`.
- The V and Q records are identical: 72,999 records in the same order, with sequence sha256 `5ae5142b…` on both
  sides.
- R4a adds no call of any kind.
- The process makes these mpf calls. The point's single MP evaluation dominates, plus the one-time Boost constants:

| Call | Baseline `5c5328af…` | R4a `2fab1328…` |
|---|---:|---:|
| `add` | 65,431 | 65,431 |
| `mul` | 4,114 | 4,114 |
| `div_ui`, `cmp` (the exponentials' series) | 1,051 each | 1,051 each |
| `set_si` | 709 | 709 |
| `div` | 207 | 207 |
| other V and Q calls (`sub`, `mul_2exp`, `set_ui`, `add_ui`, `div_2exp`, `cmp_si`, `neg`, `fits_slong_p`, `get_si`, `sub_ui`, `trunc`, `mul_ui`, `ui_div`, `get_str`, `set_str`) | 436 | 436 |
| `init2` / `clear` | 4,764 / 4,764 | 2,940 / 2,940 (the rest: the exponentials' temporaries) |
| `set` | 801 | 45 |
| `get_prec` | 1,202 | 46 |
| `swap` | 33 | 17 |

**Digest traces.** These cover the 4 heaviest graphs of each heavy L8 block and the 2 heaviest of each heavy L7 block,
64 points per graph, 1 thread.
- In both the release build (NeedError = false) and the ratio-histogram build (NeedError = true), the V, Q and VQ
  digests are identical (VQ is the interleaved order), and so are the per-operation counts of every V and Q call.
- The rows are identical.

| Block | MP points | V records |
|---|---:|---:|
| `heavy_power_L8` | 107 | 7,409,256 (release), 7,547,738 (ratiohist) |
| `heavy_free_L8` | 51 | 4,723,801 / 4,788,750 |
| `heavy_power_L7` | 39 | 573,577 / 604,902 |
| `heavy_free_L7` | 24 | 409,494 / 428,877 |

**Why the gain is small.** Per MP evaluation at heavy L8 there are about 65,000 `mpf_add` calls, from the segment sums.
R4a removes about 750 copies and 1,800 init/clear pairs, which is little next to the adds.

## Exactness

| Check | Scope | Result |
|---|---|---|
| Decimal build | `bin/c8d2_decimal` (54666232) | sha256 `3dbd51bb…`, byte-identical to Stage 3 |
| Differential test `r4a_mpdiff.cpp` (54666232) | Every graph of the four heavy blocks (512 graphs), 32 points each. Points are drawn as `sample()` draws them, and every 4th is pushed below −600, so that the shift is nonzero. In all: 16,384 points, 4,095 of them shifted. The verbatim pre-R4a body is compared against R4a for NeedError false and true | 0 mismatches in precision, size, exponent and every limb |
| Call sequence (54666315) | Above | Identical V/Q sequence and digests |
| Speed blocks (54666291) | `heavy_free_L8` (1,003,400 MP points) and `heavy_power_L8` (1,504,626), 256 tasks × 16,384 points, 64 threads | All 12 runs give one rows digest per block (`92eec91c…`, `c9b8e059…`) |
| G-L8SELF, A-RPL-7 (54666291) | 2,000 L8 kernels (1,600 free, 400 power), 2 × 512 points, both backends, against `bin/baseline` = Stage 3 | Exact in every scientific field; 114,648 + 99,884 MP points per backend |
| Replay subset, A-RPL-1/2/3 (54666291) | `validate.py --only describe replay diagnostics`: the L=2 graph plus the first 8 and the 8 heaviest kernels per (sector, L) at L3–L7, 2 × 64 points, both backends | G-C7 exact in 554 rows per backend, 366 of them with mp > 0 (1,712 MP points). G-REF exact, including 96 gmp rows with mp > 0. G-JET exact. The diagnostic builds write the release rows |

## Speed

**Micro-benchmark** (`r4a_mpdiff`, 54666232, 16 threads on a shared node). The time of `calculate_shared<MP,false>`
itself, exponentials included, over 3 repeats of every point. The MP tier gets **1.0179×** faster overall:
- L7 free 1.0218, L7 power 1.0181;
- L8 free 1.0167, L8 power 1.0176.

A prefetch variant, which prefetches the next products' mpf structs and limbs in the segment and product loops, gives
1.0101×, worse than plain R4a. It stays in the test only and is not in the kernel.

**One node** (`r4a_speed.py`, 54666291, <NODE>, 2 × EPYC 7742). Setup:
- Workload: `heavy_free_L8` and `heavy_power_L8` at 64 threads, 3 repeats per binary.
- Two streams run at once, one per socket.
- The metric is the worker's `integration_seconds`.

| Block | Stage-3 baseline: socket 0, socket 1 | R4a: socket 0, socket 1 | Median-of-3 speedup | Socket-paired speedup | Implied by the MP-tier 1.0179 |
|---|---|---|---:|---:|---:|
| `heavy_free_L8` | 156.02, 155.66 / 153.09 | 155.05 / 151.92, 152.05 | 1.0238 | **1.0062** | 1.0061 (MP share 34.7%) |
| `heavy_power_L8` | 151.97, 151.87 / 149.19 | 149.99 / 147.70, 147.58 | 1.0282 | **1.0117** | 1.0075 (MP share 42.1%) |

**Socket bias.** Socket 1 ran about 2% faster than socket 0 for both binaries. The rotation in `r4a_speed.py` (3
repeats, 2 variants) put the baseline twice on socket 0 in both blocks, so the plain median of 3 also counts the socket
difference. `speed_paired.py` compares runs on the same socket (`r4anode.54666291.0/speed/speed_paired.json`): +0.6%
free and +1.2% power. These agree with what the micro-benchmark implies, and even the biased medians (+2.4%, +2.8%;
+2.6% over both blocks) are below 3%.

**Projection to the L8 population.** The MP tier is 30.7% of L8 time in campaign a (Stage-4a model), which gives
about +0.55% overall.

**Conclusion: clearly below 3% overall.**

## Files

- `mpf_trace.c`: the LD_PRELOAD tracer.
- `r4a_trace.py`: the call-sequence comparison.
- `r4a_mpdiff.cpp`: the differential test and micro-benchmark.
- `r4a_speed.py` and `speed_paired.py`: the speed check and its socket-paired analysis.
- `scripts/`:
  - the jobs `expanse_r4a_{build,node,trace}.slurm`;
  - the Mac driver `submit_r4a.sh` (H7E-R and agent caps before every sbatch).
- Evidence: one directory per job. The trace directory of 54666315 holds the two gzipped point logs (3.5 MB).
