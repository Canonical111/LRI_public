# Measured performance

## Symmetry (2026-10, this release)

Measured with the shipped tooling on symmetry's exclusive AMD nodes (lane mode, one 64-thread lane per node,
1024-task blocks, 2^20-point chunks, gmp backend). Evidence is in `benchmarks/symmetry_2026-10/`.

| Index (group/shard) | Node CPU | Est. core-s | Wall s | Est. wall s | Utilisation | OpenMP eff. (min) |
|---|---|---:|---:|---:|---:|---:|
| 4 (a_free_L7/0) | EPYC 7543 | 9549 | 141 | 166 | 0.90 | 0.963 |
| 5 (a_free_L7/1) | EPYC 7543 | 9549 | 143 | 166 | 0.90 | 0.966 |
| 10 (a_power_L7/0) | EPYC 7532 | 7537 | 108 | 131 | 0.93 | 0.953 |
| 21 (b_power_L7/0) | EPYC 7532 | 7537 | 132 | 131 | 0.94 | 0.955 |

The drill campaign was planned at M=64, R=8 (22 indices, 18.4 estimated core-hours).

- **Definitions.** Utilisation is the sum of native task-seconds divided by (64 × index wall). It includes Python
  start-up, verification, private-runtime staging, graph staging and the barriers of the cost-ordered blocks. OpenMP
  efficiency is per block.
- **Estimates.** The shipped cost model's estimates are 0.82–1.01 of the measured walls. The lane time guard's
  default 1.5× safety factor covers that.

## Delivered local measurements (2026-09, retained)

Fresh matched-sample measurements on the supplied d=3 code. Both compared workers use GMP350, identical strict compiler flags, graphs, seeds, Sobol matrices and intervals. Each row is the median of three runs. These are selected costly workloads, not a full production or multi-node benchmark.

| Sector | Loop | Version | Threads | Wall seconds | Integration seconds | Peak MiB |
|---|---:|---|---:|---:|---:|---:|
| free | 6 | reference | 1 | 3.4619 | 3.4391 | 8.02 |
| free | 6 | gmp | 1 | 3.3936 | 3.3694 | 7.89 |
| free | 7 | reference | 1 | 3.1427 | 3.0665 | 23.52 |
| free | 7 | gmp | 1 | 3.2690 | 3.1848 | 23.53 |
| free | 7 | gmp | 2 | 1.6563 | 1.5788 | 23.52 |
| free | 7 | gmp | 4 | 0.9715 | 0.8914 | 23.52 |
| power | 6 | reference | 1 | 9.1300 | 9.1105 | 7.27 |
| power | 6 | gmp | 1 | 9.0068 | 8.9867 | 7.41 |
| power | 7 | reference | 1 | 5.8096 | 5.7419 | 20.52 |
| power | 7 | gmp | 1 | 5.8130 | 5.7468 | 20.52 |
| power | 7 | gmp | 2 | 3.0685 | 3.0010 | 20.50 |
| power | 7 | gmp | 4 | 1.6672 | 1.5991 | 20.52 |

## What changed

The baseline already shares products, denominator prefixes, numerators and promoted scratch. Those are not new gains. The tested candidate reuses absolute quotients for sign-definite numerators. It showed no consistent single-thread gain, so the production header is restored byte-for-byte from the original GMP350 implementation. The candidate is retained only in experiments/quotient_reuse; variant `gmp` in the benchmark table denotes that candidate, not the final production default. No kernel speedup is claimed for the default. The exploratory exponential-factor cache is NOT included.

The fresh profile is benchmarks/profile/profile_summary.json; the inherited preceding profile remains separately labelled benchmarks/baseline_profile.json. Instrumented timing includes clock overhead.

## Memory and workload scope

The memory demonstration evaluates the same 590 power kernels monolithically and in blocks of 32 tasks. Peak native RSS is 486.72 MiB versus 31.19 MiB. This is not a comparison to the original driver's already-blocked default, and one point per stratum is not a scientific estimate. For a small existing graph block, memory gains may be absent.

The controller bounds graph storage by active tasks and uses disk-backed planning and merging. Evaluation work remains proportional to sample count and kernel complexity. Exponential growth in graph/rate-table complexity with loop order is not removed; the implementation supports loops 2--7 only.

## Limits

Local CPU quota and software versions are recorded in benchmarks/matched/benchmarks.json. No NUMA, GPU or actual multi-node benchmark is claimed. Benchmark on the destination cluster before choosing process/thread layout. A structural task-cost model can miss expensive precision promotions; tools/make_cost_model.py can freeze measured pilot costs for placement without altering sampling weights.

## Sources

- https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html
- https://slurm.schedmd.com/job_array.html
- https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html
- https://www.boost.org/doc/libs/latest/libs/multiprecision/doc/html/boost_multiprecision/tut/floats/gmp_float.html


## Final production default: local thread scaling

The default worker and header are byte-identical to the original scientific worker. These measurements characterize its OpenMP execution under the new workflow, not a newly invented kernel speedup.
| Sector | Threads | Integration seconds | Speedup vs one thread |
|---|---:|---:|---:|
| free | 1 | 3.1169 | 1.00 |
| free | 2 | 1.5782 | 1.97 |
| free | 4 | 0.8385 | 3.72 |
| power | 1 | 5.6418 | 1.00 |
| power | 2 | 2.8566 | 1.98 |
| power | 4 | 1.5439 | 3.65 |
## C8(3) Stage 3b: the first measured cost (J-SWEEP-1, Expanse EPYC 7742)

`tools/sweep.py` on the bootstrap basis (job 54676977; every kernel, 512 points x 2 replicates, both campaigns, 8 NUMA
lanes x 16 threads, `--mp-check on`): 49.5 million points, 7.20 busy core-hours, 0.52 ms per point on average; 95.6% of
the lane-thread time inside blocks was row time. The sweep's 612 small indices cost about 3.5 s each outside the blocks
(process start, verification, staging): 578 s of wall for 212 s of busy time per lane, so the whole sweep job's
allocated/busy is 3.26 (an artefact of the sweep's index size, not of lane mode with 0.25-1.5 h indices; Stage 4a
profiles it). The model's per-group seconds per point, promotion rates and the pilot cost it implies are in
`benchmarks/expanse_2026-10-c8/stage_3b/cost_summary_stage3b.json` (README there); at L <= 7 the order-8 seconds per point
are 0.97-1.02 x C7(3)'s order-7 symmetry model.

The merge of J-VAL-3's 1.25 million-row group (`tests/merge_scale.py`, A-ORC-6) ran phase 1 at 268,650 rows/s with 16
processes (16,790 per process) and phase 2, which is one process, at 49,083 rows/s. **These rates come from a loaded
node and are not clean merge rates.** J-VAL-3 (54676975) started its three streams together at 03:44:34. The scale merge
is merge_scale's first step: the parallel merge that gives the rates ran from about 41 s to about 75 s after the start
(after the 24 s plan and the 17 s run), and the serial reference until about 140 s. During that whole window
`forced_tiers.py` ran 128 OpenMP threads on the node's 128 cores (831 s in all), and `thread_identity.py` ran its blocks
at up to 128 threads and as 8 x 16 lane processes (until 03:48:02). With merge_scale's own 16 processes the node was
oversubscribed by up to about 2x. The rates are therefore at best lower bounds on an unloaded node's rates. Phase 1 is
still above the planner's 4,000 rows/s per process. The phase-2 figure cannot be compared with the planner's 60,000
rows/s, because one process sharing cores with that load can easily lose 20%, so these runs do not show that phase 2 is
slower than projected. `tools/production.py`'s `MERGE_PHASE1_ROWS_PER_S` and `MERGE_PHASE2_ROWS_PER_S` stay unchanged.
Before either is changed, merge_scale's scale part has to be re-measured with nothing else on the node: in Stage 4a's
J-PROF, or by running it before the forced_tiers stream starts in the Stage-5 J-VAL-3. (Done in Stage 4a, J-PROF-1:
phase 1 435,984 rows/s with 16 processes, phase 2 55,105-55,975 rows/s; "The clean merge rates" below.)

## C8(3) Stage 4a: profiles of the Stage-3 baseline (P1-P4, the f_E repeat, the clean merge; A-PERF-1)

PLAN "Performance plan", Profiling first. Every run used the c8-stage3 baseline: each job rebuilt `bin/c8d3_gmp` and
stopped unless it was `24adff54…` (`reference/baseline_c8_stage3.json`; it was, in all four jobs). Expanse, AMD EPYC
7742 (2 sockets x 4 NUMA domains x 16 cores), Spack GCC 13.3.0, Boost 1.77, Spack GMP 6.2.1, perf 4.18
(`perf_event_paranoid` 1). Evidence: `benchmarks/expanse_2026-10-c8/stage_4a/` (README there); every number below is
recomputed from the raw records by `stage_4a/derive_stage4a.py` into `stage4a_derived.json`. [V] marks a measurement,
[M] a number derived from measurements by the rule stated.

| Job | Slurm | Node | Runs | Wall | SU |
|---|---|---|---|---:|---:|
| profbuild (tool check) | 54677088 (shared, 16 c) | <NODE> | builds, baseline check, fixture staging, smoke runs of every mode (`--fake-topology`, never measurements) | 7 min 11 s | 1.92 |
| J-PROF-1 | 54677131 (compute, exclusive) | <NODE> | the clean merge (twice, first, nothing else on the node), f_E, P1, the MP self-check overhead | 30 min 44 s | 65.6 |
| J-PROF-2 | 54677133 (compute, exclusive) | <NODE> | P4, five lane shapes | 33 min 22 s | 71.2 |
| J-PROF-3 | 54677135 (compute, exclusive) | <NODE> | P2 (perf stat, interleave probe), P3 | 11 min 29 s | 24.5 |

Stage 4a used 163.2 SU (dev line 287.5 → 450.7 SU, `tools/budget.py`). The plan's two jobs became three of at most 1 h
each (its rule "each profile is one job of <= 1 h on one exclusive compute node"); P5 is J-SWEEP-1 (Stage 3b).

**Fixtures** (`benchmarks/fixtures8/`, `tools/prepare_benchmarks.py --order 8`; campaign a: rate .8, layout 0, 52-bit
nets, `--mp-check on`). The P1 blocks are the plan's: per (sector, L) 120 graphs drawn at random within 8 equal-count
bins of T (terms) plus the 8 heaviest by cost model, 2 replicates (L7: x 4 chunks, 1,024 tasks; L8: 256 tasks nominal,
heavy graphs cut so no task exceeds a quarter of the block's target wall). Each graph carries its stratum weight, and
`bin/c8d3_gmp_prof` now times the tiers per graph, so the block is re-weighted to its population [M]. `heavy_*_L8` are
the 128 heaviest graphs per sector.

### P1: time per tier and per function

Tier split [V] (tier timers, 64 threads on socket 1, passive wait policy; share of task time; µs per call). The
population columns re-weight the stratified block by its strata [M]:

| Block | First pass / binary128 / MP / rest (%) | Population (%) | µs per call (first / b128 / MP) | Population µs per call | Calls per point (b128 / MP) |
|---|---|---|---|---|---|
| strat free L7 | 16.4 / 71.9 / 10.0 / 1.7 | 17.7 / 71.5 / 8.8 / 1.9 | 18.3 / 299 / 1,218 | 17.7 / 286 / 1,189 | 0.269 / 0.0092 |
| strat power L7 | 4.0 / 42.1 / 52.8 / 1.1 | 4.1 / 41.8 / 53.0 / 1.1 | 11.8 / 164 / 893 | 11.3 / 155 / 876 | 0.759 / 0.174 |
| strat free L8 | 11.6 / 72.2 / 15.8 / 0.5 | 12.5 / 70.5 / 16.5 / 0.5 | 64.3 / 1,105 / 3,138 | 57.9 / 966 / 2,946 | 0.361 / 0.0278 |
| strat power L8 | 3.8 / 43.4 / 52.4 / 0.4 | 3.8 / 42.4 / 53.3 / 0.5 | 43.0 / 561 / 1,914 | 38.7 / 497 / 1,786 | 0.868 / 0.307 |
| heavy free L8 | 8.0 / 74.6 / 17.1 / 0.2 | — | 132 / 1,704 / 3,760 | — | 0.718 / 0.075 |
| heavy power L8 | 3.9 / 48.4 / 47.5 / 0.2 | — | 91 / 1,204 / 2,955 | — | 0.949 / 0.380 |

- **All of L8** [M] (the two sectors' populations weighted by their cost, 0.630 free : 0.370 power): first pass 9.3%,
  binary128 60.1%, MP 30.2%, rest 0.5%. The RECON projected 13 / 60 / 28 (uncorrected) and 13 / 63 / 24 (deflated).
- The population cost per point (464 µs free L8, 1,010 µs power L8, with the tier timers) is 6-7% above J-SWEEP-1's
  0.438 / 0.944 ms (16-thread lanes, no timers).

Function shares [V] (`perf record -F 999 -N`, no call graph, 64 threads on socket 0, `perf report --no-children`; % of
all samples; strat free L8 / strat power L8 / heavy free L8 / heavy power L8 / strat free L7 / strat power L7):

| Item | Shares (%) |
|---|---|
| binary128 add, sub, mul called by the kernel (libgcc + PLT) | 66.0 / 38.7 / 68.7 / 44.0 / 60.5 / 33.4 |
| the same, as a share of the binary128 tier (tier timers) | 91.4 / 89.2 / 92.0 / 90.9 / 84.2 / 79.3 |
| binary128 division called by the kernel (libgcc `__divtf3`) | 0.72 / 0.48 / 0.77 / 0.54 / 1.41 / 0.87 |
| the same, as a share of the binary128 tier | 1.0 / 1.1 / 1.0 / 1.1 / 2.0 / 2.1 |
| libquadmath (`sqrtq`, `expq` and their own binary128 add/sub/mul/div copies) | 2.4 / 2.0 / 2.3 / 1.8 / 5.6 / 4.5 |
| GMP total | 13.7 / 47.0 / 14.7 / 41.3 / 8.9 / 48.7 |
| of which `__gmpn_mul_basecase` / `__gmpn_add_n` / `__gmpf_add` / `__gmpn_copyi` | 5.2 / 2.6 / 2.1 / 1.7; 22.0 / 6.2 / 5.5 / 4.6; 4.7 / 3.2 / 2.6 / 2.0; 14.7 / 7.6 / 6.7 / 5.2; 4.2 / 0.9 / 0.9 / 0.8; 25.2 / 3.4 / 3.4 / 3.4 |
| MP temporaries (malloc/free, `__gmpf_init2/clear/set`) | 0.21 / 0.72 / 0.26 / 0.86 / 0.20 / 1.04 |
| MP → long double conversion (get_str and strtold families; with GMP's divrem_1 helpers) | 0.02-0.48 / 0.10-2.6 / 0.01-0.42 / 0.06-1.5 / 0.03-0.67 / 0.22-4.9 |
| `expl` / fenv (expq's rounding-mode save) / libgomp / kernel | 0.10 / 0.16 / 0 / 0.52 (strat free L8); all blocks: `expl` <= 0.44, fenv <= 0.52, libgomp 0, kernel <= 0.70 |
| the worker's own code (first pass, loops, sampling) | 13.8 / 8.3 / 10.4 / 9.0 / 18.2 / 7.1 |

- **Source lines** [V] (perf annotate on the worker, addr2line through a `-g` twin whose allocated sections equal
  the baseline's byte for byte): the first pass (`calculate_products`, kernel.hpp:221-233) is 3.7-15.8% of the
  samples, mostly the segment-sum loop (kernel.hpp:226: 2.5-10.4%) and the exponentials (:224); `sample()` 0.05-0.8%;
  `calculate_shared` (the binary128 and MP loop code itself, outside the library calls) 0.6-0.9%.
- **`calculate_reference<long double>` and the shift loop: 0.** No point of the P1 blocks (60.8 million points per run) was
  evaluated with a shift (`nondirect` = 0) or by `calculate_reference<ld>` (`nonmoderate` = 0), as at d=2.
- **Graph loading** is serial in the worker: 1.2-3.4% of the 64-thread blocks' node time (`load_seconds`) [V].
- Rows of the release worker and of the timer build were identical in every block [V].

### MP self-check overhead (PLAN C.4; production default and the cost table's mode correction, E.7)

`bin/c8d3_gmp_prof` with `--mp-check on`, `off` and `stride16` on the four stratified blocks (64 threads, each block's
three runs on one socket, the order rotated) [V]; values identical across the modes, no `mp_alarm`:

| Block | `on`: task-time overhead over `off` (population) | MP tier ratio on/off | `stride16`: overhead (population) |
|---|---|---|---|
| strat free L7 | 0.58% (0.48%) | 1.051 | 0.04% (0.03%) |
| strat power L7 | 2.92% (2.85%) | 1.046 | 0.45% (0.43%) |
| strat free L8 | 0.57% (0.58%) | 1.036 | 0.08% (0.06%) |
| strat power L8 | 1.96% (1.95%) | 1.034 | 0.73% (0.82%) |

- All of L8 [M] (cost-weighted as above): `on` costs 1.09% more than `off`; the whole campaign (L <= 7 is ~4% of the cost,
  at 1.5%) about 1.1%. That is below the 3% rule, so **production keeps `--mp-check on`**.
- E.7's mode correction [M]: production cost relative to the measured `on` mode, L8 cost-weighted, `off` 0.989 and
  `stride16` 0.992 (per sector: free 0.994 / 0.995, power 0.981 / 0.989). These go into the final cost model's
  `mp_check_overhead` (`make_cost_model.py` needs an option for it; Stage 4b/5).
- The `stride16` rows are noisier than their 1/16 expectation (strat power L8 0.73% against about 0.12%): one run per
  mode, and the run-to-run spread of the MP tier time is of that order. The decision does not depend on it.

### P2: is the first pass latency-bound?

`perf stat` [V] (64 threads on socket 0, passive wait policy; and one thread on the heaviest tasks):

| Block | IPC (64 threads / 1 thread) | L1d miss rate | Promotions |
|---|---|---|---|
| nopromo free L7 | 1.013 / 1.003 | 7.2% | 9,564 binary128 of 134 million points (7e-5) at 64 threads; none at 1 |
| nopromo free L8 | 1.043 / 1.054 | 7.6% | 3,677 of 67 million (5e-5) |
| strat free L8 (context: promoted tiers dominate) | 2.457 / 2.434 | 2.4% | binary128 0.36, MP 0.028 per point |

Interleave probe [V] (`benchmarks/probes/interleave_probe.cpp`, the d=3 term denominator U·sqrt(U); 4,096 moderate
points x 5 repeats per graph, one pinned core each; lock-step results bit-identical): speedup of 2 points in lock-step
over the sequential first pass, geometric mean 1.095 (all 8 graphs), 1.036 on promotion-free graphs, 1.158 on the
stratified blocks' heaviest graphs (L8 1.190-1.192, L7 1.123-1.128); 4 points: 1.091.

- The first pass runs at IPC 1.0 (x87, latency-bound); the promoted tiers at 2.4-2.5. **#6 is a go by the IPC rule
  (< 1.5)**, not by the probe rule (>= 1.2). Expected gain [M]: L8 first-pass share 9.3% x (1 - 1/1.10…1.19) =
  0.8-1.5% now, 1.2-2.2% after #4 raises the first pass's share; below A-PERF-2's 3%, so a revert is likely, as at d=2.

### P3: margins at the tests

`bin/c8d3_gmp_ratiohist` on the uniform blocks (256 graphs x 2 replicates per (sector, L)), rates .8 (a) and .7 (b),
128 threads [V]; every consistency check against the row counters passed:

| (sector, L, rate) | binary128 / MP per point | MP of binary128 | 1e-9 failures in the top decade / below 1e-12 | accepted binary128 within 1 / 2 / 3 decades of 1e-23 | binary128 below 1e-20 / 1e-21 / 1e-22 | MP below 1e-63 / 1e-77; deepest |
|---|---|---|---|---|---|---|
| free L7 .8 | 0.252 / 0.0076 | 3.0% | 19.2% / 51.4% | 1.0 / 2.2 / 3.9% | 6.8 / 5.2 / 4.0% | 0 / 0; 1e-63 |
| free L7 .7 | 0.302 / 0.0155 | 5.2% | 16.4% / 57.2% | 1.4 / 3.2 / 5.4% | 10.3 / 8.2 / 6.5% | 6.9e-5 / 0; 1e-72 |
| power L7 .8 | 0.766 / 0.172 | 22.5% | 7.7% / 76.8% | 3.6 / 7.6 / 12.1% | 31.9 / 28.4 / 25.3% | 0.0093 / 0.0018; 1e-175 |
| power L7 .7 | 0.818 / 0.235 | 28.7% | 6.1% / 81.1% | 4.3 / 9.0 / 14.2% | 38.8 / 35.1 / 31.8% | 0.0166 / 0.0040; 1e-199 |
| free L8 .8 | 0.322 / 0.0224 | 7.0% | 14.9% / 60.5% | 1.8 / 3.9 / 6.5% | 13.0 / 10.6 / 8.6% | 1.4e-4 / 5e-6; 1e-79 |
| free L8 .7 | 0.370 / 0.0386 | 10.5% | 12.9% / 65.3% | 2.3 / 5.0 / 8.2% | 17.8 / 14.9 / 12.5% | 4.8e-4 / 3.4e-5; 1e-90 |
| power L8 .8 | 0.857 / 0.291 | 33.9% | 5.0% / 84.2% | 5.0 / 10.3 / 16.2% | 44.6 / 40.7 / 37.2% | 0.0179 / 0.0042; 1e-176 |
| power L8 .7 | 0.893 / 0.370 | 41.4% | 3.9% / 87.5% | 5.7 / 11.8 / 18.3% | 52.1 / 48.3 / 44.8% | 0.0310 / 0.0088; 1e-200 |

- The promotion rates equal J-SWEEP-1's (L8 binary128 0.33 / 0.38 free, 0.85 / 0.89 power; MP 0.022 / 0.039, 0.29 /
  0.37), so the expected escalations are the cost model's.
- A dd-type tier tested at 1e-20 would add 26-124% MP calls (1e-21: 17-71%); the deepest MP evaluation is 1e-200, so
  350 digits keep >= 150. An MP tier at 77 digits accepted at 1e-63 would escalate 1.8-3.1% of power L8's MP calls
  (0.014-0.048% at free L8), ten times d=2's rate. Inputs for F1/F2 only; no flag is approved (U1).

### P4: lane shape

`tools/benchmark.py --lane-shapes` on `p4_L8` (1,142 L8 graphs drawn uniformly per sector, 2 replicates x 32,768 points
in production's <= 60 s tasks; 2,308 tasks, 42,286 cost-model s, 330 s of ideal node time), production's blocks (<= max(16T,
256) tasks and <= 900 s at width T), `--mp-check on`, every lane pinned to its NUMA-aligned cores [V]:

| Shape | Wall (s) | Throughput (cost-model s per node-s) | Relative | Busy | OpenMP eff. | Load + staging (% node time) | Peak RSS per lane | NUMA-local (min) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 16x8 | 373.0 | 113.36 | 1.000 | 0.927 | 0.955 | 0.87 | 0.41 GiB | 0.987 |
| 8x16 | 378.5 | 111.72 | 0.986 | 0.915 | 0.949 | 1.93 | 0.81 GiB | 0.993 |
| 4x32 | 381.2 | 110.92 | 0.979 | 0.908 | 0.944 | 3.39 | 1.54 GiB | 0.997 |
| 1x128 | 395.4 | 106.94 | 0.943 | 0.878 | 0.940 | 6.44 | 3.12 GiB | 1.000 |
| 2x64 | 396.2 | 106.72 | 0.941 | 0.875 | 0.940 | 6.48 | 3.05 GiB | 0.999 |

- The rows were identical across the five shapes (2,308 rows, every scientific field) [V].
- The task time was 1.047-1.051 x the cost model's prediction in every shape (busy x 128 x wall / 42,286) [M].
- Load + staging is nearly all the worker's serial graph loading (staging and hash checks <= 0.32%); it grows with the lane
  width, as at d=2.
- The node-wide peak RSS is 6.4-6.5 GB in every multi-lane shape (of 240 GB).
- The differences between 16x8, 8x16 and 4x32 are 1.4-2.1% from one run each; C62d measured the same order on the same
  CPU (16x8 best, 8x16 0.990).

### f_E (A-PERF-1) and the toolchain

C7(3)'s fixtures with symmetry's exact arguments (`benchmarks/symmetry_2026-10/validation_567197/bench/`: 16 graphs x 2
replicates, 4,096 points at L6, 512 at L7), `bin/ref/c7d3_gmp` (a6ce987's source and commands, `4ca56aa6…`) on <NODE>
with nothing else running, 3 repeats [V]. The C8 worker in order-7 mode took the same time (within 0.2%) and its rows
equal C7's (A-RPL-1):

| Group | Expanse isolated, 1 / 2 / 4 threads (s) | f_E isolated (vs symmetry 7532) | 64 single-thread copies on socket 0 (s) | Loaded-socket factor | f_E loaded vs symmetry isolated |
|---|---|---|---|---|---|
| free L6 | 3.527 | 0.990 | 3.821 | 1.084 | 1.072 |
| free L7 | 3.369 / 1.705 / 0.888 | 0.981 / 0.981 / 0.981 | 3.648 | 1.083 | 1.062 |
| power L6 | 9.851 | 0.966 | 10.774 | 1.094 | 1.057 |
| power L7 | 6.412 / 3.234 / 1.707 | 0.960 / 0.963 / 0.970 | 7.078 | 1.104 | 1.060 |

- **f_E = 0.96-0.99 core for core** (EPYC 7742 at GCC 13.3 against symmetry's EPYC 7532 at GCC 11.4, both isolated).
- A fully loaded 64-core socket costs Expanse 8-10% per thread (L3, memory bandwidth, all-core clock), so against
  symmetry's isolated runs it is 1.06-1.07. Symmetry's own loaded factor was not measured. At lane level J-SWEEP-1's L <= 7
  seconds per point are 0.97-1.02 x C7(3)'s symmetry model (both measured under full-node load).
- **f_E ≈ 1.0 (0.96-1.07)** replaces the plan's assumed 1.1 (0.95-1.3). The pilot is costed on the Expanse model
  directly, so f_E only rescales symmetry-basis figures.

### The clean merge rates (Stage 3b repair round 2)

`tests/merge_scale.py`'s scale part (1,249,792 rows, 16 shards, `--jobs 16`) as J-PROF-1's first two steps, with
nothing else on the node (load average 0.36 before; `node_load.txt`) [V]:

| Run | Phase 1 (16 processes) | Per process | Phase 2 (one process) | Parallel wall | Serial wall | Byte-identical |
|---|---:|---:|---:|---:|---:|---|
| 1 | 435,984 rows/s | 27,249 | 55,105 rows/s | 25.7 s | 59.8 s | yes |
| 2 | 435,597 rows/s | 27,225 | 55,975 rows/s | 25.4 s | 59.7 s | yes |

The loaded J-VAL-3 run gave 268,650 / 16,790 / 49,083. `production.py` plans with
`MERGE_PHASE1_ROWS_PER_S = 4,000` per process (6.8x below the clean rate: conservative, unchanged) and
`MERGE_PHASE2_ROWS_PER_S = 60,000`, **7-8% above the clean rate**. Decision below.

### Decisions for Stage 4b (the plan's decision table)

| # | Change | Profile | Decision |
|---|---|---|---|
| R5a | parallel NUMA-local graph load (C.6) | P1, P4 | **go** (low priority). Loading plus staging (nearly all serial loading) is 0.9% of node time at 16x8, 1.9% at 8x16 and 6.4% at 1x128 with 60 s tasks, and 1.2-3.4% in the 64-thread P1 blocks. A-PERF-2's L8 sweep sample (512-point tasks) is load-heavy, where C62d measured x1.154 |
| R5b | lane defaults | P4 | **16x8 on Expanse**: `C8_LANES=16`, `--threads 8`, `--checkpoint-tasks` default max(16 x 8, 256) = 256, 900 s blocks unchanged; J-SWEEP-2 runs 16 x 8; the A-PERF-3 reference is 113.4 cost-model s per node-second on the Stage-3 binary (re-measured on the final binary). Also `MERGE_PHASE2_ROWS_PER_S` 60,000 → 50,000 (0.9 x the clean 55,105-55,975), a scheduling-only change in the same `production.py` edit |
| #4 | inline binary128 add/sub/mul (C62d's R3a, H5) | P1 | **go, add/sub/mul only**: they are 89-92% of the L8 binary128 tier (79-84% at L7). The kernel's divisions are 1.0-2.1% of the tier, far below the 10% bar, so there is no div path. `sqrtq`/`expq` stay libquadmath (2-6% of samples incl. their internal ops). Projected [M]: with the tier x2.0-2.2 per call (C62d's R3a: x2.16-2.20) L8 gains x1.43-1.49 (free x1.54-1.62, power x1.27-1.30). Output class B (bitwise), as at d=2; C62d's patch files at 14d7347; this package proves its own replay and runs the differential test over the d=3 operand ranges |
| #5a | MP tier without temporaries (R4a) | P1 | **not attempted unless 4b has time**: allocation, init/clear and set are 0.2-1.0% of samples (0.7-0.9% at power L8). Only copy elision of `__gmpn_copyi` (1.7-5.2%) could reach the 3% bar, and at d=2 the same patch with copy elision gave x1.009. If attempted, measure a copy-elision prototype on power L8 first |
| #6 | first-pass interleave | P2 | **go by the IPC rule** (IPC 1.0 < 1.5); probe x1.10 (promotion-free x1.04, heavy x1.16-1.19); expected 0.8-2.2% overall, so a revert under A-PERF-2 is likely. Run it after #4 |
| #8 | `alpha` as uint8 quarter units | P4 | **go as planned, expected small**: memory is no constraint (6.5 GB per node at 16 lanes); the gain, if any, is the first pass's cache footprint (L1d miss rate 7.6% in the promotion-free first pass, first pass 9% of L8) |
| #7 | `-march=x86-64-v3`, PGO/LTO | — | optional, unchanged (unknown 0-10%); after #4, since the libgcc calls #4 removes dominate today |
| C.4 | production `--mp-check` | MP self-check | **on** (overhead 1.09% at L8, about 1.1% overall, <= 3%); the cost model's `mp_check_overhead`: `off` 0.989, `stride16` 0.992 |
| — | `calculate_reference<ld>`, shift loop, MP→ld conversion (R4d) | P1 | not worth work: 0, 0 and <= 0.22% |
| — | opt-in levers for 4c (MP tier 30% of L8, 53% of power L8) | P1, P3 | C62d's mp256 (x1.37 at d=2) would escalate ~10x more MP calls at d=3's power L8 (1.8-3.1% of them), still small. The zen2 GMP build (R4f, opt-in at d=2, x1.05) addresses the 22% `__gmpn_mul_basecase` share at power L8. Both are optional and budget-gated |

Expected default-path gain [M]: #4 x1.43-1.49 at L8, R5a/R5b a few percent, #6 <= 2%: about x1.5, the low end of the plan's
÷1.5-2.5, because the MP tier (30% of L8) is untouched on the default path.

## C8(3) Stage 4b: default-path optimizations (A-PERF-2; Expanse EPYC 7742, 2026-10-05)

Each step is one commit gated by exact checks first and timed only when all passed (`slurm/native_job.sh` `opt`,
`tools/opt_speed.py`): the L8 sweep sample of A-RPL-8, three interleaved repeats, medians of the lane-thread seconds,
B0 = the Stage-3 baseline (`c8d3_gmp` 24adff54…), PREV = the last kept step, CAND = the step. The PLAN's rule: kept
when every exact gate passed and the step's speedup is at least 1.03, else reverted. Every job's rows digest is
`223d76a9…` (the same rows as Stage 3). Records: `benchmarks/expanse_2026-10-c8/stage_4b/` (`derive_stage4b.py`
recomputes every number here from them; `stage4b_derived.json`).

| Step | Commit | Job | Exact gates | Shape | Step speedup (free / power) | Decision |
|---|---|---|---|---|---:|---|
| R5a parallel NUMA-local graph load | 36ec1c1 + 81238c8 | 54677354 | validate_full, l8self, first_error, thread_identity | 16 x 8 | **x1.186** (1.250 / 1.087) | kept |
| R5b lane default 16 x 8, `--threads 8` | 75041af | 54681216 (54677393 timed out in its copy) | same_binary, thread_identity | 8 x 16 → 16 x 8 | x1.019 (1.019 / 1.019) | reverted (02963bc) |
| #4 inline binary128 add/sub/mul (C62d's R3a) | 9fa9421 | 54677395 | validate_full, l8self, thread_identity, quaddiff, forced_tiers vs Stage 3 | 16 x 8 | **x1.452** (1.580 / 1.288) | kept |
| #6 first pass of two points in lock-step | 33f4661 | 54677397 | validate_full, l8self, thread_identity | 16 x 8 | x1.021 | reverted (46475ca) |
| #8 `alpha` as uint8 quarter units | 5b9519b (branch `opt-8`) | 54681218 | validate_full, l8self, thread_identity, inspect_check | 16 x 8 | x0.992 | not merged |

- **Cumulative** (B0 → #4, 16 x 8): 1,762 → 1,023 lane-thread s, **x1.72** (free x1.97, power x1.41; node wall
  14.1 → 8.3 s). #4's projection was x1.43-1.49 at L8 [M]; measured x1.45.
- **The lane shape after R5a.** On the Stage-3 binary 16 x 8 was x1.20 over 8 x 16 (B0 1,762 vs 2,110 s), almost all
  of it serial graph loading (load share 0.20 vs 0.33). R5a loads the graphs in parallel on each NUMA node (load share
  0.04), after which 16 x 8 gains only x1.019 over 8 x 16, so the Stage-3 default (one lane per NUMA node, `--threads
  16`) stays. At the production default shape 8 x 16, R5a alone is x1.41 over B0.
- **#6 and #8.** Both exact, both within 2.5% of no change, as their Stage-4a profiles predicted (P2: IPC 1.0 with
  <= 2.2% expected; the first pass is 9% of L8 and its cache footprint already small).
- `MERGE_PHASE2_ROWS_PER_S` is 50,000 (0.9 x the clean 55,105-55,975 rows/s): a planning estimate corrected in R5b's
  edit and kept when R5b's lane defaults were reverted.
- **Expanse's Lustre after the 2026-10-05 maintenance** slowed every opt job's export copy (6,847 files) from 51 s to
  17-55 min; the measurements themselves run in node-local memory and are unaffected (spreads of the repeats
  0.1-0.5%).
- **G4b, passed** (job 54681801 on <NODE>, `C8_OPT_STEP=final` on 02963bc, whose `src/` is 9fa9421's). Every exact
  gate passed: validate_full, l8self, thread_identity, first_error, quaddiff, and same_binary. The final `c8d3_gmp` is
  b7db88c1…, byte for byte the binary J-OPT-4 stored, so final/last-kept is x0.998, run-to-run noise. Against the
  Stage-3 baseline: 1,763.1 → 1,026.1 lane-thread s, **x1.718** (free x1.970, power x1.397; node wall 14.01 → 8.32 s,
  x1.684; spreads 0.12–0.17%), with the same rows.
- **#7, opt-in only** (`-O3 -march=x86-64-v3`, STRICT kept, the same job; never stored, never the default). It is exact
  (variant validate_full and l8self pass) and x1.023 over the final default build (free x1.029, power x1.017). That is
  below the 3% bar, so nothing more is planned for it.

## C8(3) Stage 5: the final binary on both sites (A-PERF-3, A-PERF-4, A-PERF-5; 2026-10-06)

The final default binary is `c8d3_gmp` `8f3a36aa…` on symmetry (GCC 11.4, system GMP 6.2.1) and `b7db88c1…` on Expanse
(GCC 13.3, Spack GMP 6.2.1); `src/` is 9fa9421's on both. Every symmetry number is from an EPYC 7543 node under the CPU
pin. Paths are relative to `benchmarks/symmetry_2026-10-c8/stage5_59d4922/` unless stated. [V] marks a measurement and
[M] a number derived from committed records by the rule stated.

### J-L8SELF-sym: the L8 sweep sample at 8 x 8 (A-RPL-8 on symmetry; A-PERF-5, symmetry part)

Job 570410 ran `slurm/native_job.sh opt` with `C8_OPT_STEP=final` on <NODE>, on D's export, with the gates `l8self` and
shapes 8x8 (`opt_final/`, `speed/opt_speed.json`). Its workload is `tests/validate.py` `l8self_sample`: 1,600 free and
400 power L8 graphs, 2 replicates, 512 points, gmp, `--mp-check on`, 3 interleaved repeats. B0 is the symmetry
c8-stage3 baseline `3a9a556b…` (`reference/baseline_c8_stage3_symmetry.json`) and CAND the final binary `8f3a36aa…`
[V]:

| Median of 3 | B0 | CAND | B0 → CAND |
|---|---:|---:|---:|
| lane-thread seconds | 1,529.7 | 1,120.1 | **×1.366** |
| free / power lane-thread seconds | 983.1 / 545.6 | 672.9 / 444.8 | ×1.461 / ×1.227 |
| node wall (s) | 24.28 | 17.74 | ×1.369 |
| load share / busy fraction / OpenMP efficiency | 0.174 / 0.794 / 0.987 | 0.041 / 0.918 / 0.986 | |

- l8self is exact against B0. The rows are identical, with rows digest `223d76a9…`, the same as every Expanse J-OPT
  job's. The spreads of the repeats are 1.5% (B0) and 0.7% (CAND).
- Expanse's G4b (54681801, 16 x 8, 24adff54… → b7db88c1…) gives ×1.718 on the same sample: free ×1.970, power ×1.397,
  load share 0.196 → 0.053 [V] (Stage 4b above).
- The site difference is not analysed here. C62d's opt-in dd+mp256 gate also gave different speedups on the two sites
  (×2.53 on symmetry, ×2.17 on Expanse; `LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md:400-401`).

### A-PERF-3: the throughput drill J-SMK-4 (symmetry, 64-core node)

**Current verdict (Stage 6): A-PERF-3 / A-SMK-4 SHORTFALL** under the PLAN's per-block OpenMP rule, with A-ORC-13
**PASS** and A-ORC-5 PASS (`smk4/thru_report_s6b.json`, "Stage 6 re-derivation" below). The table and bullets that
follow are Stage 5's record: their OpenMP PASS (time-weighted mean) and A-ORC-13 FAIL are **historical**.

**Setup.**
- The TP plan `thru-20261006` (J-DRL-0 570429) has 82 jobs and 114.4 estimated busy core-h at `--replicates 8` (host
  decision h1).
- `lanes 1` ran one 8 x 8 worker, 570496 on <NODE>, plus merge 570497. The auto lane time was 3:15 (W 1.99 h; largest
  index need 0.45 h); the worker reserved 208 core-h and the merge 64 (`smk4/lanes1.out`).
- The worker ran W = 6,935 s on 64 allocated cores (`sacct` AllocTRES).
- Accounting: work 123.29 core-h, plan 1.60, merge 0.18; `eta_node` (allocated/busy) 1.068
  (`smk4/accounting.json`).
- The report is R-SMK4 570554: `tools/thru_report.py --parts perf3,orc13,orc5 --strict` with `--sweep` (J-SWEEP-2
  570403) and `--reference-opt-speed opt_final/speed/opt_speed.json --reference-binary CAND --reference-shape 8x8`
  (`smk4/thru_report.json`) [V]:

| Rule (PLAN A-PERF-3; A1 sizing) | Measured | Verdict (Stage 5) |
|---|---|---|
| busy = row seconds / (64 × W) ≥ 0.90 | 415,702.8 / 443,840 = **0.937** | PASS |
| OpenMP efficiency, time-weighted, ≥ 0.95 (Stage 5's rule; the PLAN's is per block, S4-007) | all 789 blocks **0.990** (min 0.916, P10 0.982; 3 blocks below 0.95, all L3/L4 power with 8–24 tasks); L8 538 blocks **0.990** (min 0.969) | PASS (historical; per block: **SHORTFALL**, below) |
| throughput ≥ 0.95 × the J-L8SELF CAND reference (same binary, 8 x 8) | 411,913.9 cost-model s / 6,935 s = 59.40 per node-second (213,827 per node-hour) against 59.11 (1,048.58 / 17.738 s): **×1.005** | PASS |
| median L8 speed (cost-model s / row s) within 10% of the sweep's | 0.9936 (P10 0.939, P90 1.060) against the sweep's 1.000: **×0.994** | PASS |
| lane CPU = the model's | AMD EPYC 7543 32-Core Processor, both | PASS |
| sizing: L8 row seconds per core ≥ 3,600 s; busy ≥ 72 core-h on 64 cores (A1 deviation; PLAN: 140 on 128) | 6,071 s; 115.47 core-h | PASS |

- **Where the remaining 6.3% went** (`a_perf_3.causes` of the 443,840 allocated core-s). Native integration accounts
  for 419,937.8 core-s and native graph loading for 2,429.4 (0.55% of the node's core-seconds). Outside the native
  worker (Python start-up, verification, staging) there are 21,472.8 core-s (4.84%). The rest, 419,937.8 − 415,702.8
  = 4,235.0 core-s (0.95%), is integration time outside the row seconds: threads idle inside the native integration
  (efficiency 0.990) [M]. The records do not split it into imbalance between tasks and the OpenMP runtime's own costs
  (no per-thread times).
- **A-ORC-5** PASS on all 82 indices: the largest (native `max_rss_kb` + Python) / `est_peak_bytes` is 0.767, and the
  native-only ratio is 0.725.
- **A-ORC-13** FAIL in Stage 5 (historical; F13-d3; `docs/HPC.md` "Stage 5 results"); **PASS** on re-derivation
  (below).
  - Every `fingerprint_bytes` is the single value 7,008,499 (PASS).
  - The non-own medians disagree: 30.05 MB at a_free_L3 against 1,389.3 MB at a_free_L8, a size ratio of 118 (FAIL).
  - The rchar fit over 82 runs is 2.001 × staged + 32.8 MB: a slope near 2, because the reaped native child's reads
    are counted.
- **Stage 6 re-derivation** (`thru_report.py --rederive`, on the Mac from `smk4/thru_report.json` and the 82 hook
  records; `smk4/thru_report_s6b.json`, fix round 2. Fix round 1's `smk4/thru_report_s6.json` is kept as a historical
  record: it has the same verdicts and numbers but asserts the causes that S4-R2-002 corrected) [V]:
  - A-ORC-13 **PASS** under F13-d3's model (the native child's reads of its staged copy are own bytes): non-own medians
    30,046,840 and 31,734,238 bytes (without `fingerprint_bytes` 23,038,341 and 24,725,739); non-own on staged bytes
    has slope 0.0007.
  - A-PERF-3 **SHORTFALL** under the PLAN's per-block OpenMP rule (Codex S4-007; the table above gated the
    time-weighted mean): a_power_L3 index 16 at 0.929 (8 tasks, wall 5.5 ms), b_power_L3 index 57 at 0.936 (8 tasks,
    6.0 ms) and b_power_L4 index 58 at 0.916 (24 tasks, 63 ms), all on 8 threads on <NODE>; 1.4e-6 of the integration
    core-seconds; every block of 1 s or more is at least 0.9688. Every block has valid timing (S4-R2-001: an untimed
    block would keep the verdict from PASS).
  - Cause (S4-R2-002): per-launch overhead and end-of-block imbalance in these short few-task blocks are **possible**
    explanations, not measured. No record times them (no per-thread or per-launch times), so they can be neither
    confirmed nor told apart, and the records establish no cause for these blocks.
  - The job's 8 lanes of 8 cores, covering its 64 allocated cores, are the configured capacity. Whether another lane
    ran at the same moment as these blocks is not recorded, so interference from the other lanes can be neither
    confirmed nor excluded.

### A-PERF-4: the two calibration refreshes and the refined pre-pilot table

**The refreshes** (D.14; `refresh_report.json`, `refresh_record.json` and `cost_summary.json` are in each evidence
folder) [V]:

| Site | Job | Basis | PREV | Model sha256 | Executable | Busy core-h (49,506,304 points) | Busy ms per point | J-BLD |
|---|---|---|---|---|---|---:|---:|---|
| symmetry | 570403 (<NODE>, 8 x 8) | bootstrap (D10: PREV fails on cpu_model) | `gmp_expanse_epyc7742_c8.json` (J-SWEEP-1) | `0fc934e7…` | `8f3a36aa…` | 5.817 | 0.423 | 570406 pass |
| Expanse | 54694976 (<NODE>, 16 x 8) | prior_model, F = 2 | J-SWEEP-1's `fc78fc8f…` (executable `24adff54…`) | `56df9d61…` | `b7db88c1…` | 4.950 | 0.360 | 54695102 pass |

- Sources: `../stage5_e3b9252/sweep2_570403/`, `../../expanse_2026-10-c8/stage5_59d4922/sweep2_54694976/` and
  `cost_models/README.md`. J-SWEEP-1 on the Stage-3 binary took 7.200 busy core-h (0.524 ms per point).
- Both models have 48,346 keys and `mp_check` on, and both J-BLDs passed the HD11 identity.
- Not one `mp_alarm` occurred in either sweep: 0 among 4,326,366 MP-checked points on symmetry and 4,327,447 on
  Expanse. The L8 promotions on symmetry (a / b) are binary128 0.334 / 0.383 and MP 0.022 / 0.039 for free, and
  binary128 0.850 / 0.886 and MP 0.291 / 0.370 for power. These match J-SWEEP-1's rates (P3 above) to two digits.

**κ measured** [M]. κ = (mean_g √c_g at L8)² / (mean_g √c_g at L7)² per campaign and sector, the RECON's definition
(`LRI_C8_D3_HPC_loop/RECON.md` §6.3.4). c_g is the model's seconds per point. L7 counts its 2,298 free and 590 power
graphs without the zero-channel kernels (s_G = 4), as the RECON's L7 metric does. The value over all L7 kernels is in
brackets.

| κ (a / b) | symmetry final (`0fc934e7…`) | Expanse final (`56df9d61…`) | Expanse Stage 3 (`fc78fc8f…`) | RECON projection: central (band) |
|---|---|---|---|---|
| free | 3.91 / 3.92 (3.90 / 3.91) | 3.37 / 3.40 | 4.03 / 3.93 | 3.88 / 3.84 (2.87–7.10) |
| power | 3.66 / 3.50 (3.54 / 3.38) | 3.10 / 2.94 | 3.52 / 3.35 | 3.26 / 3.06 (2.20–6.77) |

All measured values lie inside the RECON's bands. On Expanse the final binary lowers κ, since #4 gains more at L8 than
at L7 (per (sector, L) below). Symmetry's final κ is close to Expanse's Stage-3 value, which fits its smaller L8 gain
(×1.366 against ×1.718) [I].

**The refined pre-pilot table** (κ measured, σ projected). It comes from `tools/design_fallback.py report` on the smoke
with the symmetry model (J-SMK-3a 570523; `smk3/report.json`, label `fallback`) [M]:
- σ_g comes from the smoke's 1,024 stratified test graphs at 4,096 points × 4 replicates. The rest of the 48,346
  graphs are imputed; the variance share they carry is in the table.
- Costs are allocated core-h at the smoke's measured η (busy/allocated) of 0.733, at α = ½.
- The design's 1.5 margin is included: the predicted total SE = 1.5 × the raw SE ≤ the target.
- |C8| = 1,500.

| Relative SE | Target SE | Predicted SE: total / raw | Batches | Allocated core-h | Imputed variance share | RECON pre-pilot central (core-h; raw SE, no margin) |
|---|---:|---|---:|---:|---:|---:|
| 1e-2 | 15 | 6.32 / 4.21 | 1 | 2,317 | 0.49 | 2.0e3 |
| 3e-3 | 4.5 | 3.04 / 2.03 | 1 | 4,410 | 0.59 | 2.1e3 |
| 1e-3 | 1.5 | 1.28 / 0.857 | 1 | 19,391 | 0.71 | 9.7e3 |
| 5e-4 | 0.75 | 0.642 / 0.428 | 1 | 77,562 | 0.71 | 3.5e4 |
| 2.5e-4 | 0.375 | 0.321 / 0.214 | 1 | 310,250 | 0.71 | 1.3e5 |
| 1.44e-4 (= C7(3)) | 0.216 | 0.211 / 0.140 | 2 | 689,352 | 0.75 | 3.6e5 |

- **Why the two columns do not compare directly.** The RECON column (`RECON.md` §6.3.5, "Cost against relative
  SE") has no margin. It uses α = 0.534, run1's ×1.086 allocated/busy, an allocation realism of ×1.140 and "today's
  kernel", before the Stage-4b optimizations (`RECON.md` §6.3.5, "Overheads"). This table's raw SE is the
  comparable one. Its η is the smoke's: small indices, 0.733. J-SMK-4 measured lane mode at busy 0.937; at that η the
  allocated figures scale by 0.733 / 0.937 = ×0.78 [M].
- **The top two rows sit at the design's floors** (≥ 4,096 points per graph, replicates in [32, 128]), so their SE is
  below target [I].
- **J-SMK-3a's own freeze** (`smk3/freeze_1e-3.json`): target 1e-3 in 2 batches, 18,945 core-h, predicted SE
  1.311 / 0.874, 128 replicates per group except power L8 (32).
- **A second σ projection: J-DES-5's three test-only freezes** (`des5/freeze_se*.json`, `des5/manifest_se*.json`).
  - σ there comes from J-SWEEP-2's 2 replicates × 512 points of every graph, so nothing is imputed. η is 0.83, a host
    value (h7).
  - Results: SE 1.5 → predicted 1.206 at 9,707 allocated core-h (plan estimate 8,056 busy); SE 0.5 → 0.426 at 77,653
    (64,452); SE 0.22 → 0.209 at 317,777 (263,755). The plan estimates are each manifest's `estimates.total_core_hours`.
  - At target SE 1.5 the two σ sources differ by ×2.0 in allocated core-h (19,391 against 9,707), or ×1.76 at equal η
    [M]. The pilot measures σ (A-PIL-2..4); neither projection is a design.

### A-PERF-5: the final binary against the Stage-3 baseline, per site

- **Symmetry.** On the L8 sweep sample at 8 x 8 (J-L8SELF-sym, above): ×1.366 overall, free ×1.461, power ×1.227. L3–L7
  have no symmetry measurement, because no Stage-3 binary was swept on symmetry (D10: A-PERF-5 per (sector, L) exists
  on Expanse only).
- **Expanse.** G4b on the L8 sample at 16 x 8: ×1.718 overall, free ×1.970, power ×1.397.
- **Expanse per (sector, L)** [M]. These are ratios of the sweeps' busy seconds per point, J-SWEEP-1 54676977 (Stage
  3, `24adff54…`, 8 x 16 lanes) over J-SWEEP-2-exp 54694976 (final, `b7db88c1…`, 16 x 8), from the two
  `cost_summary.json`. Rows are µs per point, Stage 3 → final, and the ratio.
- **What the ratios count.** Busy time is row time, so R5a's parallel graph loading, which is outside the rows, does
  not count here. At L3–L6 the groups hold 1–395 graphs at 1–100 µs per point. The ratios there (×0.81–1.16) are not
  resolved at 512 points × 2 replicates [I]. The default-path changes target the binary128 tier and graph loading,
  which matter at L7–L8.

| (sector, L) | a: µs per point | a: ratio | b: µs per point | b: ratio |
|---|---|---:|---|---:|
| free L3 | 1.311 → 1.262 | 1.039 | 1.336 → 1.362 | 0.981 |
| free L4 | 2.302 → 2.755 | 0.835 | 2.516 → 3.109 | 0.809 |
| free L5 | 6.007 → 5.550 | 1.082 | 8.533 → 8.778 | 0.972 |
| free L6 | 22.27 → 20.31 | 1.096 | 28.21 → 24.37 | 1.157 |
| free L7 | 98.78 → 73.61 | **1.342** | 121.83 → 91.12 | **1.337** |
| free L8 | 437.9 → 265.9 | **1.647** | 523.3 → 331.5 | **1.579** |
| power L3 | 1.416 → 1.471 | 0.963 | 1.635 → 1.510 | 1.083 |
| power L4 | 4.093 → 3.931 | 1.041 | 5.616 → 6.267 | 0.896 |
| power L5 | 21.20 → 19.63 | 1.080 | 29.67 → 28.23 | 1.051 |
| power L6 | 73.90 → 78.47 | 0.942 | 97.58 → 100.81 | 0.968 |
| power L7 | 271.6 → 246.2 | **1.103** | 333.4 → 310.7 | **1.073** |
| power L8 | 944.2 → 731.0 | **1.292** | 1,100.0 → 877.0 | **1.254** |
| whole sweep | 523.5 → 360.0 | **1.454** | | |

- **Per site.** On the same 49,506,304 sweep points, the final binary took 5.817 busy core-h on symmetry (EPYC 7543,
  8 x 8) and 4.950 on Expanse (EPYC 7742, 16 x 8): ×1.175 more per core on symmetry [M]. The pilot is costed on
  symmetry's own model, so this ratio only rescales Expanse-basis figures.
