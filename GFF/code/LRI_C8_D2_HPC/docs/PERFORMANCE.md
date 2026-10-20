# C8(2) performance

Stage 4 (PLAN.md "Performance plan", A-PERF) fills this document with the profiles P1–P5, the optimization results
(accepted and rejected) and the final cost table. The C7(2) report is kept as `docs/c7_historical/PERFORMANCE_C7.md`.

## Stage-3 baseline (no optimization)

The kernel is C7(2)'s at order 8, bit for bit on the default path (`docs/NUMERICS.md`); `bin/c8d2_gmp` sha256
`5c5328af…` (GCC 13.3.0, GMP 6.2.1, Expanse).

### J-SWEEP-1: the first measured cost model (Expanse job 54641706, 2026-10-04)

`tools/sweep.py` in bootstrap mode (R13) on one Expanse compute node (2 × AMD EPYC 7742, 8 NUMA nodes × 16 cores):
a test-only campaign of all 24,173 graphs, both campaigns, 2 replicates × 512 points per graph, fixed 512-point tasks
(`--bootstrap-chunk 512 --shards 8`, 176 indices), 8 NUMA-pinned process slots of 16 threads, heaviest first. Wall
9:23 (allocated 20.0 core-hours); busy thread-time 7.6 core-hours (η_node 0.38 for this short job: plan, merge and the
tail of 176 indices on 8 slots). The cost model holds all 48,346 `campaign:sector:L:graph` keys
(`benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json`).

Measured seconds per point (gmp backend), summed over the graphs of each (sector, L) and campaign, the mean and the
largest graph, and the ratio of the bootstrap's preliminary proxy (C7(2) L7 rate × 3) to the measurement:

| Sector, L | Graphs | a: Σ s/pt | a: mean µs | a: max µs | b: Σ s/pt | b: mean µs | b: max µs | proxy/measured (a, b) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| free L3 | 5 | 6.07e-6 | 1.21 | 1.23 | 6.05e-6 | 1.21 | 1.25 | 2.58, 2.59 |
| free L4 | 16 | 2.87e-5 | 1.79 | 2.22 | 2.80e-5 | 1.75 | 1.87 | 3.50, 3.58 |
| free L5 | 76 | 2.30e-4 | 3.03 | 3.46 | 2.32e-4 | 3.05 | 3.66 | 4.39, 4.36 |
| free L6 | 395 | 2.69e-3 | 6.82 | 11.3 | 2.66e-3 | 6.74 | 11.1 | 4.58, 4.64 |
| free L7 | 2,441 | 0.350 | 143 | 463 | 0.291 | 119 | 414 | 3.13, 3.77 |
| free L8 | 16,064 | 9.88 | 615 | 2,670 | 8.53 | 531 | 2,330 | 3.05, 3.53 |
| power L3 | 1 | 1.41e-6 | 1.41 | 1.41 | 1.35e-6 | 1.35 | 1.35 | 2.94, 3.08 |
| power L4 | 3 | 1.01e-5 | 3.35 | 4.49 | 8.38e-6 | 2.79 | 3.74 | 2.83, 3.39 |
| power L5 | 20 | 2.83e-4 | 14.1 | 29.0 | 3.29e-4 | 16.5 | 57.6 | 1.69, 1.45 |
| power L6 | 107 | 5.90e-3 | 55.1 | 135 | 4.50e-3 | 42.0 | 105 | 1.92, 2.51 |
| power L7 | 709 | 0.154 | 218 | 520 | 0.123 | 173 | 449 | 2.29, 2.88 |
| power L8 | 4,336 | 3.63 | 837 | 2,670 | 3.03 | 699 | 2,330 | 2.60, 3.12 |

One point for every graph of both campaigns costs 26.0 core-seconds at this baseline (L8: 96%). The preliminary proxy
was conservative everywhere (ratio ≥ 1.45), so no bootstrap task exceeded its 120 s bound in fact. The calibration rows
of this sweep (`calibrate.py --update`) are kept with the evidence (`calibration.json` there).

**The active calibration (A-PERF-4; Stage-5 G5 fix).** `tools/calibration.json` holds the J-SWEEP-2 rows of the final
default binary on symmetry, the plan's native site: the byte copy of
`benchmarks/symmetry_2026-10-c8/stage5/s5sweep2.570032.0/calibration.json` (`d85dd7c0…`; job 570032 on <NODE>, EPYC
7543; schema `c8-d2-calibration-1`, 24 campaign-keyed rows (gmp, a/b, free/power, L3–L8), each with its source run,
manifest and executable). The schema keys a row by (backend, campaign, sector, L) and has no site key, so one file
holds one site's rows: the Expanse J-SWEEP-2E rows (job 54676908 on <NODE>, EPYC 7742) are kept as the pinned copy
`cost_models/calibration_expanse_amd_c8.json` (`5b039f8e…`, the byte copy of
`benchmarks/expanse_2026-10-c8/stage5/exp/s5esweep2.54676908.0/calibration.json`); pass it to a test-only plan made
on Expanse without a cost model by copying it over `tools/calibration.json` in that export. The calibration rows serve
only test-only plans without `--cost-model` (the calibrated-proxy basis); every non-test plan, the pilots included,
plans from the per-site measured cost models `cost_models/gmp_symmetry_amd_c8.json` and
`cost_models/gmp_expanse_amd_c8.json`. The C7(2) rows stay in the pinned copy
`reference/c7d2_hpc_a55958f/tools/calibration.json`, the only source of `calibrate.py --bootstrap` (R18; its
regeneration test runs in an export whose active calibration is this one, and the orchestration tests reset their
package copy to the C7(2) rows, the pre-sweep state the R13 tests assume). Since Stage-6 fix round 4 a calibration
file holds the rows of one measurement identity (numerics and rates identity, recorded as `identity`):
`tools/calibration.json` takes only exact default-rate rows, a sweep under `--rates` or `--numerics` needs its own
`--calibration FILE`, and `production.calibration_row` uses a row only under the plan's numerics and rates identity
(W11); `calibrate.py` reads timings only from checkpoints `production.validate_checkpoint` accepts (W10).

### Merge throughput (`tests/merge_scale.py`)

The planner's `MERGE_PHASE1_ROWS_PER_S` = 4,000 per process and `MERGE_PHASE2_ROWS_PER_S` = 60,000 are conservative
planning values, never a gate. Measured:

| Where | Rows | Phase 1 rows/s (per process) | Phase 2 rows/s | Peak RSS per merge process |
|---|---:|---:|---:|---:|
| Mac (M-series, 4 processes) | 39,056 | 48,000 | 168,000 | 51 MB (serial reference 75 MB) |
| J-SWEEP-1 merge (Expanse, 32 processes, 24 groups) | 96,692 | 193,000 in total | 16,400 | — |
| Expanse job 54643361 (EPYC 7742, 16 processes) | 1,249,792 | 639,000 in total (40,000 per process) | 78,000 | 86 MB (serial reference 72 MB) |

The planning constants are therefore 10× (phase 1) and 1.3× (phase 2) below the measurements. The merge of a
10^6-row group takes about 20 s with 16 processes (41 s for the serial reference), and the parallel merge is
byte-identical to the serial one (A-ORC-6).

**Merge memory (checkpoint review T-01/O02).** Phase 1 now streams each shard block by block into sorted spill runs
(the rows above were measured before). On the Mac it runs at 40,000 rows/s per process (39,056 rows, 4 processes),
still 10× the planning constant. At a fixed block (256 tasks) and fan-in (16), going from 19,528 to 156,224 rows of
one group (8× the rows per shard) leaves the peak of the Python heap unchanged (10.1 MB, tracemalloc) and raises the
peak RSS of the merge process by 4.4 MB in one shard (41.9 → 46.3 MB) and 1.7 MB in four shards; the allocator's own
retention levels off at a few blocks. A phase 1 that kept a shard's rows grows by hundreds of bytes per extra row.
The gate (`tests/merge_scale.py`) bounds the heap growth at 2 MB everywhere and the RSS growth at 16 MB on Linux
(canonical: 1.4 MB) and 48 MB on macOS, where a later Mac run grew 12.4 MB in one shard with the heap flat.

## Stage 4a: profiling tools and frozen workloads (P1–P4)

Profiling only: no change to `src/` numerics or to the default workers. Every record carries the host, build and
executable identity (sha256, `--describe`, build record, `lscpu`, kernel, perf version and `perf_event_paranoid`, Slurm
ids, OpenMP environment) and the sha256 of the fixture manifest. Results go to dated sections below once the jobs
have run.

**Frozen workloads** (`benchmarks/fixtures8/`, `tools/prepare_benchmarks.py --order 8`; committed, 0.8 MB). Chosen
from the J-SWEEP-1 cost model (seconds per point per graph, campaign a, Stage-3 baseline) with the documented master
seed 2026100408; each block has its own native and Sobol-net seed (SHA-256 of `c8-d2-bench|<seed>|<block>|<role>`),
campaign a's native settings (rate .8, layout 0, compensated sums, 52-bit nets), and points per task the power of two
whose predicted wall is closest to the target. Graph members are staged at run time from the pinned packs and verified
against the inventory sha256 (the L8 packs are not in git). `--check` rebuilds them and compares bytes (the nets come
from scipy and are compared when the scipy version is the manifest's).

| Block | Use | Tasks | Graphs | Points per task | Predicted wall |
|---|---|---:|---:|---:|---:|
| `heavy_{free,power}_L7` | P1 | 1,024 | 128 heaviest, 2 reps × 4 chunks | 8,192 | 51 s, 48 s at 64 threads |
| `heavy_{free,power}_L8` | P1 (P2/P3 context) | 256 | 128 heaviest, 2 reps | 16,384 | 146 s, 131 s at 64 threads |
| `nopromo_free_L7` | P2 | 1,024 | 64 promotion-free (40 primitives), 2 reps × 8 chunks | 131,072 | 27 s at 64 threads |
| `nopromo_free_L8` | P2 | 256 | 128 promotion-free (113 primitives) | 262,144 | 39 s at 64 threads |
| `random_{free,power}_L{7,8}` | P3 | 512 | 256 drawn uniformly, 2 reps | 16,384–65,536 | 29–53 s at 128 threads |
| `p4_{free,power}_L8` (workload `p4_L8`) | P4 | 3,164 + 854 | 1,582 + 427 drawn uniformly (sector proportions) | 16,384 | 330 s ideal at 128 cores |

"Promotion-free" means quad and MP fractions 0 in both campaigns of the cost model. Every L8 primitive is promotion-free
there; the power sector has no promotion-free graph (smallest quad fraction 0.17 at L7, 0.27 at L8), so P2's blocks are
free-sector only.

**Tools.**
- `tools/perf_profile.py p1`: `perf record -F 999 -N` of `bin/c8d2_gmp` on a block at 64 threads pinned to one socket
  (4 NUMA nodes), then the plan's `perf report --no-children --sort symbol --stdio` (with `-n`) plus `--sort dso,symbol`
  and `--sort dso`, parsed into the named shares (`__addtf3/__subtf3/__multf3/__divtf3`, the rest of libgcc's binary128
  support, `expq`, `expl`, `logl`, `__gmpf_*`, `__gmpn_*`, malloc/free, MP → long double conversion as a lower bound
  (get_str and strtold families) and a "likely" bound (plus GMP's divrem_1 helpers), `calculate_reference<long
  double>`, libgomp, kernel, the worker's own code) and a top-40 table. At the same time `bin/c8d2_gmp_prof` runs the
  same block on the other socket: the tier split (first pass / binary128 / MP seconds and calls). Source lines (the
  shift loop and other inlined code have no symbol of their own): a `-g` twin of the worker is built and used only when
  its allocated sections equal the baseline's byte for byte at the same addresses; `perf annotate` gives per-instruction
  samples and `addr2line` on the twin maps them to `src/kernel.hpp` lines and regions. `-g` call graphs are off by
  default (the self-time table does not use them; at 64 threads they cost about 1 kB per sample). Without perf: the
  release worker runs every requested block itself (at the requested threads, beside the tier timers unless
  `--sequential`; `blocks[b].release_run`), so the per-block row binding below covers every block (W19, Stage-6 fix
  round 4), plus `ltrace -c -e '__gmpf_*'` on one thread on a mini block, bound to a plain run of that block. `tools/perf_profile.py p1-reparse --input P1DIR`
  (651c56f) rebuilds the perf summaries offline from the saved report texts into `p1_reparsed.json` beside the
  untouched `p1.json`: RHEL 8's perf 4.18 appends IPC columns to the symbol reports, which the first parser did not
  strip, so the job's own `p1.json` (54661716) classified every symbol as "other". Symbols are classified without
  their version, `@plt` and `__GI_` decorations; a PLT stub counts with its target.
- `tools/perf_profile.py p2`: `perf stat -x,` (cycles, instructions, branches, branch misses, L1d loads and misses,
  task clock) on the promotion-free blocks at 64 threads (`OMP_WAIT_POLICY=passive`, so barrier spinning is not
  counted) and on one thread; IPC. `tools/benchmark.py --interleave-probe` runs the plan's fallback, the micro-benchmark
  `benchmarks/probes/interleave_probe.cpp` (`make probes`; it includes the unchanged `src/kernel.hpp` and times its
  `calculate_products` against 2 and 4 points in lock-step, results required bit-identical). R6 goes if IPC < 1.5 or the
  probe speedup ≥ 1.2.
- `tools/perf_profile.py p3`: `bin/c8d2_gmp_ratiohist` on the uniform-draw blocks (and the heavy L8 blocks) at rates .8
  and .9: the log10(|v|/err) histograms at the 1e-9 test (failing long-double points; the native histogram holds only
  those), at the 1e-23 test (every binary128 evaluation) and of the MP evaluations, per (sector, L, rate), checked
  against the row counters, with the fractions below 10^−k. Since fix round 4 (W19's class) the release worker
  (`--worker-exe`, default `bin/c8d2_gmp`, checked as a release build before any output) runs every (block, rate)
  too, and its scientific rows must equal the ratio-histogram build's (`results[k].release_run`,
  `rows_identical_worker_vs_ratiohist`, `rows_mismatch`; an error otherwise), so the histograms describe the release
  worker's computation; P3 runs each workload twice (about twice the wall time).
- `tools/benchmark.py --lane-shapes`: for each N×T shape, N lane processes pinned to disjoint NUMA-aligned sets of T
  physical cores (from sysfs inside the allocation; shapes that do not fit are refused before anything runs) work
  through deterministic LPT shares of the fixed workload, in production-style blocks of max(16 × T, 256) tasks, each
  block staged from the pack and run at T threads. Per shape: node wall, throughput in cost-model seconds per
  node-second, busy fraction, OpenMP efficiency, staging and graph-load seconds and their share of node time (the
  PACK_FORMAT decision), per-lane wall, peak RSS (VmHWM), NUMA placement from `/proc/<pid>/numa_maps` and the node
  numastat counters, and a digest of every row's scientific fields (equal across shapes).
- **The OpenMP team of every measurement (Y2, Stage-6 fix round 2).** P1–P4 start their workers in the controlled
  OpenMP environment (`benchkit.omp_env` = `common.omp_child_env`: no inherited `OMP_*`, `GOMP_*` or `KMP_*` control,
  then the requested team, `OMP_DYNAMIC=FALSE`, close binding on cores). Before the fix an inherited
  `OMP_THREAD_LIMIT=1` ran the 1x64 and 8x8 shapes with one thread per process while `native_summary` recorded the
  requested widths. P4 (`benchmark.py --lane-shapes`, `benchkit.run_watched`) watches each block's team on Linux
  (`common.TeamWatch`); a shape is accepted only when every block showed its team (`team_sizes_verified` per shape
  and in the record, the verdict per block), a block whose worker computes without its team is stopped and is an error
  of its shape. `perf_profile.py` (integration) watches its direct worker runs the same way (the tier timers, the
  ratio histograms, the serial and plain runs; `native_result` refuses a watched run without a verified team) and
  records a run wrapped by perf or ltrace as not watched (`team.wrapped`).
- **The profiler's own bindings (Z20-Z22, Stage-6 fix round 3).**
  - **Z20.** P1 compares, per block, the scientific-row digests of the release worker's run under perf and the
    tier-timer worker's run (`benchkit.rows_mismatch`, `perf_profile.bind_rows`): any difference is an error naming the
    block, the differing uids and any rows present in one run only (`blocks[b].rows_mismatch`), and P1 exits 1. Before,
    a stale `--prof-exe` gave a successful P1 record combining measurements of two computations
    (`rows_identical_worker_vs_prof` false, no error). Without perf, Z20's fallback compared the two workers on a mini
    block of `heavy_power_L8` only, so a profiler build differing on another measured block passed (S6H4-02); since fix
    round 4 (W19) the fallback runs the release worker on every requested block and the same per-block binding applies
    (`fallback.binding.blocks`); the mini block (one thread, 16 tasks × 64 points) serves only ltrace, whose run must
    match a plain run of it (`fallback.ltrace.rows_identical_plain_vs_ltrace`).
  - **Z21.** `--expect-sha256` is checked in every mode before any output, scratch or worker run (P3's
    ratio-histogram build included, which ignored it; P1 and P2 used to refuse only after creating their directories):
    a mismatched prefix exits 65, an empty or malformed one (anything but 8 to 64 hex digits) 64
    (`benchkit.expect_prefix`, `require_sha256`). The same class: `benchmark.py --interleave-probe` binds the probe
    executable to the hash it accepted and ignored, the C7(2) legacy mode refuses the option (exit 2), and the probe's
    core-count refusal comes before its output directory. Records: `settings.expect_sha256`, `identity.worker_check`
    (P2), `identity.ratiohist_check` (P3).
  - **Z22.** `--keep-perf-data` (P1 only; P2 and P3, which write no perf.data, refuse it) moves every block's
    `perf.data` into `<output>/perf_data/` and records its path, size and sha256 (`blocks[b].perf_data`), with or without
    `--keep-scratch`; a failed move is an error and keeps the scratch directory (`settings.scratch_kept`). Before, the
    option without `--keep-scratch` let the cleanup delete the data it was meant to keep. On a cluster the large
    `perf.data` files then land in the evidence directory; `expanse_prof1.slurm` does not pass the option.
  - A P1 or P3 run with a stale `--prof-exe` or a wrong ratio-histogram hash now exits nonzero where it exited 0.
    Tests: `tests/test_profiling.py` `perf_binding`, `perf_expect`, `perf_keep` and the extended `e2e_perf`
    (`benchmarks/mac_2026-10-c8/fx3g4/`).

**Jobs** (Expanse, site deviation U1; `benchmarks/expanse_2026-10-c8/stage4a/scripts/`, submitted by
`submit_prof_expanse.sh` with the H7E-R admission before every sbatch): `c8d2-prof-build` (shared, 16 CPUs: builds,
release workers checked against the Stage-3 hashes, fixtures and pack members verified), then on one exclusive compute
node each `c8d2-prof1` (P1, limit 35 min, expected ~15), `c8d2-prof2` (P2 and the probe, 20 min, ~8), `c8d2-prof3`
(P3, 25 min, ~11) and `c8d2-prof4` (P4 with shapes 1x128, 2x64, 4x32, 8x16, 16x8; 50 min, ~33). Worst case about 285
SU. The symmetry P4 (`benchmarks/symmetry_2026-10-c8/stage4a/scripts/symmetry_prof4.slurm`, amddebugq, shapes 1x64,
2x32, 4x16, 8x8, `--fraction 0.5`) is submitted by `submit_prof4_symmetry.sh` after the H7 check. Mac tests:
`tests/test_profiling.py` (in `make test-python`).

## Stage 4a: profiles on the Stage-3 baseline (2026-10-04) [A-PERF-1; J-PROF-1..4, P5 = J-SWEEP-1]

Profiling only: `src/` and the default workers are unchanged. The jobs measured the Stage-3 release worker
`bin/c8d2_gmp` sha256 `5c5328af…` (Spack GCC 13.3.0, GMP 6.2.1, Boost 1.77 headers). The Expanse build job 54661715,
from the `git archive` export of c176881 (5,353 files equal), rebuilt it byte for byte, together with `bin/c8d2_decimal`
`3dbd51bb…` and both diagnostic builds (`profbuild.54661715.0/binaries_vs_stage3.json`).

| Profile | Job | Where | Workload |
|---|---|---|---|
| P1 | 54661716 | Expanse <NODE> (2 × EPYC 7742), 8:34 | heavy free/power L7 (1,024 tasks) and L8 (256 tasks) blocks, 64 threads; `perf record` on socket 0 and the tier-timer build on socket 1 at the same time |
| P2 | 54661717 | Expanse <NODE>, 5:48 | promotion-free free L7/L8 blocks and the heavy free L8 block, 64 threads and 1 thread; then the lock-step probe |
| P3 | 54661718 | Expanse <NODE>, 11:52 | uniform-draw L7/L8 blocks of both sectors and the heavy L8 blocks at rates .8 and .9, 128 threads |
| P4 | 54661719 | Expanse <NODE>, 32:53 | `p4_L8` (4,018 tasks, 42,254 cost-model s), shapes 1x128, 2x64, 4x32, 8x16, 16x8 |
| P4 half node | 54661771 | Expanse <NODE>, 24:38 | `p4_L8` at fraction 0.5 (2,010 tasks) on socket 0, shapes 1x64, 2x32, 4x16, 8x8 |
| P4 symmetry | 569788 | symmetry amddebugq <NODE> (2 × EPYC 7543, NPS4: 8 NUMA nodes × 8 cores), 24:29 | the same 2,010 tasks, shapes 1x64, 2x32, 4x16, 8x8; worker built there from the export of 7a8aad7 with Ubuntu GCC 11.4.0 (sha256 `23624153…`, same source and flags) |
| P5 | 54641706 (Stage 3) | Expanse | J-SWEEP-1: every graph, 2 × 512 points (above, "J-SWEEP-1") |

**Deviations from the plan's P1–P4 rows.**
- Site deviation U1: P1–P4 ran on exclusive Expanse compute nodes (128 cores), not on amddebugq. The symmetry P4
  repeats the lane-shape probe on the production hardware.
- P1 recorded without call graphs (`perf record -F 999 -N`, no `-g`): the `--no-children` self-time table does not use
  them. The tier timers ran on the other socket at the same time; in every block the timer build's rows equal the
  worker's.
- The plan's line numbers `kernel.hpp:108` (calculate_reference) and `:158` (shift loop) are C7(2)'s. In this kernel
  they are lines 143–148 and 193.
- P2's promotion-free blocks had 8,777 (L7) and 956 (L8) binary128 points at 64 threads (6.5e-5 and 1.4e-5 of the
  points) and none at 1 thread. perf stat multiplexed its six counters (each counted 16.7% of the time), so the counts
  are scaled estimates.
- The perf summaries in the job's own `p1.json` are wrong: RHEL 8's perf 4.18 appends IPC columns, which the first
  parser did not strip. They were rebuilt offline (`perf_profile.py p1-reparse`, 651c56f) into `p1/p1_reparsed.json`.
  No job was rerun.

**Recomputed from the raw evidence.** `benchmarks/expanse_2026-10-c8/stage4a/writeup/derive_stage4a.py` (standard
library, with its own report parser and symbol categories) recomputes every number below from the raw evidence and
writes `writeup/stage4a_derived.json`. The raw evidence is:
- the perf report texts and perf stat CSVs;
- the tier-timer seconds and calls;
- the probe's repeat timings;
- the histogram counts;
- the per-shape P4 records;
- the J-SWEEP-1 cost model;
- the sacct records.

Where the runners' summaries give the same quantity, this section uses the recomputed value. The differences: RSS here is in GiB (the runner divided kB by 10^6); the PLT stub is inside the binary128 total, not on top of it; the MP exponential lower bound is 1.35–6.66% (runner: 1.5–7%); the half-node cross-node NUMA fraction is 1.1–1.3% node-wide (runner: < 0.1%); `kernel.hpp:154` is 2.7–4.8% (runner: 3.6–4.8%).

### Tier split

**Measured (P1 tier timers, heavy blocks, 64 threads).** Shares are of thread time (64 × integration wall). The rest,
2.4–6.0%, is sampling, the regulator recurrence and the block barrier.

| Block | Points | binary128 per point | MP per point | MP per binary128 | First pass | binary128 | MP | Tiers / thread time | µs per call: first pass, binary128, MP | OpenMP eff. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| heavy free L7 | 8,388,608 | 0.717 | 0.150 | 0.209 | 5.6% | 52.5% | 39.5% | 0.976 | 23.7, 310, 1,114 | 0.981 |
| heavy power L7 | 8,388,608 | 0.879 | 0.238 | 0.271 | 3.8% | 42.9% | 49.9% | 0.966 | 15.3, 198, 851 | 0.971 |
| heavy free L8 | 4,194,304 | 0.833 | 0.239 | 0.287 | 5.3% | 56.9% | 34.7% | 0.969 | 126, 1,609, 3,421 | 0.970 |
| heavy power L8 | 4,194,304 | 0.940 | 0.359 | 0.382 | 4.0% | 48.0% | 42.1% | 0.940 | 90.6, 1,173, 2,689 | 0.942 |

**Per-call law.** Fitting the L7 and L8 heavy blocks of each sector in two points gives:
- binary128 call ≈ 12.7 (free) / 12.9 (power) × the first-pass cost of the same graph, plus 8 / 0 µs;
- MP call ≈ 578 / 477 µs + 22.6 / 24.4 × the first-pass cost.

The fixed MP part is per call and, within this two-point fit, not separated from the graph's size (the 2E exponentials grow with L: E = 14 at L7, 16 at L8, which the L7/L8 fit cannot split from the first-pass term): mostly the 2E 350-digit exponentials, plus the conversion and the set-up. It agrees with C63d's d=3 NNLS law,
whose fixed MP part is 515 µs (`LRI_C8_shared/PERF_NOTES.md`, 2026-10-03).

**Population estimate (model).** The per-call law is applied to every graph of the J-SWEEP-1 cost model, using its
per-graph seconds per point and its binary128 and MP fractions. Each graph's first-pass cost is solved from its
measured total; no graph needed clamping. In percent, first pass and sampling / binary128 / MP:

| Sector, L | Campaign a | Campaign b | Fixed MP part (a, b) |
|---|---|---|---|
| free L7 | 11.3 / 64.0 / 24.7 | 13.7 / 68.1 / 18.2 | 14.0%, 10.3% |
| free L8 | 9.0 / 65.0 / 26.0 | 10.4 / 69.3 / 20.3 | 6.2%, 4.8% |
| power L7 | 5.0 / 51.1 / 43.9 | 6.2 / 59.1 / 34.8 | 28.5%, 22.8% |
| power L8 | 4.5 / 51.8 / 43.7 | 5.2 / 58.1 / 36.7 | 14.3%, 12.3% |
| L8, both sectors | 7.8 / 61.5 / 30.7 | 9.1 / 66.3 / 24.6 | |

The plan's projection for free L8 ("Baseline facts": 10 / 68 / 21) holds to within a few points. In campaign a the MP
tier is about 5 points larger than projected.

### µs per point (P5: J-SWEEP-1)

The cost model gives per-task thread-seconds per point on EPYC 7742 (lane width 16), per graph. The table shows
campaign a, with campaign b's mean and point-mean fractions in parentheses. The fractions are binary128 and MP
evaluations per point, averaged over graphs ("point mean") or weighted by cost.

| Sector, L | Graphs | Mean µs | p10 | p50 | p90 | p99 | Max | Cost share of the top 10% of graphs | binary128 fraction, point mean | MP fraction, point mean | binary128, cost-weighted | MP, cost-weighted | Promotion-free graphs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| free L7 | 2,441 | 143 (119) | 14.9 | 96 | 317 | 415 | 463 | 25% | 0.370 (0.325) | 0.035 (0.021) | 0.556 | 0.067 | 75 |
| free L8 | 16,064 | 615 (531) | 42.7 | 337 | 1,617 | 2,081 | 2,672 | 30% | 0.441 (0.398) | 0.066 (0.044) | 0.690 | 0.138 | 416 |
| power L7 | 709 | 218 (173) | 70.9 | 217 | 344 | 467 | 520 | 18% | 0.784 (0.732) | 0.130 (0.083) | 0.836 | 0.166 | 0 |
| power L8 | 4,336 | 837 (699) | 242 | 871 | 1,353 | 2,034 | 2,666 | 20% | 0.872 (0.836) | 0.251 (0.180) | 0.917 | 0.311 | 0 |

One point on every graph of both campaigns costs 26.0 core-seconds, and L8 is 96.4% of it. The cost is spread across
many graphs: the heaviest tenth of the L8 graphs carries 20–30% of the sector's cost.

### Time per function (P1, perf record)

Values are percent of all cycle samples (perf `--no-children` self time). The four blocks have 3.57, 3.37, 9.84 and
9.29 million samples, none lost. Symbols below perf's 0.01% cutoff total 0.51–0.57%. Rows marked ↳ are parts of the
row above. The MP-exponential and MP-temporaries rows overlap the GMP and worker rows.

| Symbols | free L7 | power L7 | free L8 | power L8 |
|---|---:|---:|---:|---:|
| `__addtf3` (libgcc and the worker's PLT stub) | 42.47 | 32.88 | 52.77 | 45.04 |
| `__multf3` | 5.16 | 5.13 | 2.78 | 2.90 |
| `__divtf3` | 1.10 | 0.95 | 0.57 | 0.54 |
| ↳ as a share of the binary128 tier (P1 timers) | 2.1% | 2.2% | 1.0% | 1.1% |
| `__subtf3` called by the kernel | <0.01 | <0.01 | <0.01 | <0.01 |
| binary128 arithmetic, all copies (with libquadmath's own add/sub/mul) | 50.41 | 41.12 | 56.53 | 48.98 |
| other libgcc soft-float (`__sfp_handle_exceptions`, conversions, compares) | 1.50 | 1.36 | 1.12 | 1.08 |
| `expq` family: libquadmath (expq and its own arithmetic) + libm fenv calls (expq's rounding-mode save/restore) | 2.24 | 2.89 | 0.53 | 0.66 |
| ↳ `expq` itself | 0.07 | 0.09 | 0.02 | 0.03 |
| GMP (libgmp) | 36.38 | 47.46 | 30.80 | 38.89 |
| ↳ `__gmpn_mul_basecase` | 17.72 | 25.31 | 10.39 | 14.64 |
| ↳ `__gmpn_add_n` + `__gmpf_add` | 8.09 | 7.65 | 12.95 | 14.54 |
| ↳ `__gmpn_copyi` | 3.19 | 3.38 | 4.28 | 4.99 |
| ↳ `mpf_div` family (`sbpi1_div_q`, `invert_limb`, `submul_1`, `div_q`, …) | 1.72 | 2.22 | 0.92 | 1.26 |
| ↳ `__gmpn_divrem_1` (`mpf_div_ui`, MP exponential series) | 2.81 | 4.67 | 0.95 | 1.50 |
| MP exponential, lower bound (`hyp0F0`, `eval_exp`, `pow_imp`, `mpf_div_ui`, `mpn_divrem_1`, `mpn_sqr_basecase`) | 4.00 | 6.66 | 1.35 | 2.13 |
| MP temporaries (malloc/free, `mpf_init2/clear/set/set_si`, GMP allocate/free, `operator=`) | 0.92 | 1.11 | 0.49 | 0.74 |
| ↳ the same with `__gmpn_copyi` (part of it is inside `mpf_add` and stays) | 4.11 | 4.49 | 4.77 | 5.73 |
| MP → long double (`get_str` family + `strtold`; upper bound, since `strtold` also parses graphs) | 0.06 | 0.11 | 0.01 | 0.03 |
| worker `main._omp_fn.0` (first pass and sampling; `calculate_products` is inlined) | 5.82 | 4.05 | 5.49 | 4.21 |
| ↳ source line `kernel.hpp:154`, the segment-sum loop of `calculate_products` | 4.30 | 2.73 | 4.83 | 3.60 |
| worker `calculate_shared<gmp_float<350>>` | 2.64 | 2.30 | 4.29 | 4.83 |
| worker `calculate_shared<__float128>` | 0.58 | 0.52 | 0.32 | 0.31 |
| `calculate_reference<long double>` (inlined; source lines 143–148) | 0.00 | 0.00 | 0.00 | 0.00 |
| shift loop (source line 193) | 0.00 | 0.00 | 0.00 | 0.00 |
| `[unknown]` (kernel addresses hidden by `kptr_restrict`) | 0.77 | 0.78 | 0.75 | 0.75 |
| libgomp | 0.04 | 0.04 | 0.01 | 0.01 |

**Notes.**
- The binary128 tier is soft-float almost entirely. The kernel's add, mul and div come to 91% (power L7) to about
  100% (L8) of the tier's timer share, and `__addtf3` alone is 84–94% of them.
- The source lines come from a `-g` twin whose allocated sections equal the release binary's byte for byte.
- No call graphs were recorded. The series `mpf_mul`/`mpf_add` calls of the MP exponential therefore cannot be told
  apart from the polynomial's, and the MP-exponential row is a lower bound. The per-call law's fixed MP part (above) is
  the corresponding upper-side estimate.

### IPC and the lock-step probe (P2)

| Block | Threads | Points | binary128 / MP points | IPC | L1d load miss rate | Branch miss rate | GHz |
|---|---:|---:|---|---:|---:|---:|---:|
| promotion-free free L7 | 64 | 134,217,728 | 8,777 / 0 | 1.009 | 7.09% | 1.23% | 3.09 |
| promotion-free free L7 | 1 | 2,228,224 | 0 / 0 | 1.004 | 7.19% | 1.17% | 3.35 |
| promotion-free free L8 | 64 | 67,108,864 | 956 / 0 | 1.037 | 7.27% | 0.56% | 3.07 |
| promotion-free free L8 | 1 | 786,432 | 0 / 0 | 1.038 | 7.04% | 0.53% | 3.35 |
| heavy free L8 | 64 | 4,194,304 | 3,494,580 / 1,003,400 | 2.712 | 2.13% | 0.36% | 3.05 |
| heavy free L8 | 1 | 16,384 | 13,727 / 4,442 | 2.757 | 1.88% | 0.35% | 3.36 |

**The first pass.** It runs on x87 long double at IPC 1.0, at any thread count. Its hottest line is the segment-sum
loop (`kernel.hpp:154`), a serial chain of x87 additions over gathered products, and 7% of its L1d loads miss.

**The promoted tiers.** The heavy block runs at IPC 2.7, with binary128 at 57% and MP at 35% of thread time. Take out
the first pass (IPC ≈ 1.0 on about 5% of the cycles), and the binary128 and MP tiers together run at about 2.8. The
soft-float and GMP code is throughput-bound, not latency-bound.

**Lock-step probe.** It compares `calculate_products` (the unchanged `src/kernel.hpp`) with 2 and 4 points in
lock-step. Each value is the median of 5 repeats of 4,096 points on one pinned core.

| Block | Graph | Terms | Addends | µs per point (1 point) | Speedup, 2 points | Speedup, 4 points |
|---|---:|---:|---:|---:|---:|---:|
| promotion-free free L8 | 17646 | 1 | 3,896 | 36.1 | 1.031 | 1.028 |
| promotion-free free L8 | 21486 | 1 | 3,968 | 36.0 | 1.033 | 1.032 |
| promotion-free free L7 | 3797 | 1 | 1,280 | 12.1 | 1.032 | 1.029 |
| promotion-free free L7 | 2459 | 1 | 1,248 | 11.9 | 1.031 | 1.029 |
| heavy free L8 | 26403 | 208 | 76,864 | 125.9 | 1.191 | 1.178 |
| heavy free L8 | 16238 | 232 | 99,844 | 160.6 | 1.200 | 1.195 |
| heavy free L7 | 3850 | 80 | 12,916 | 24.5 | 1.147 | 1.103 |
| heavy free L7 | 3330 | 64 | 10,123 | 20.2 | 1.136 | 1.088 |

- **Geometric means.** With 2 points: 1.098 over all 8 graphs, 1.032 on the promotion-free graphs and 1.168 on the
  heavy ones. With 4 points: 1.083.
- **Bit identity.** Every result is bit-identical.
- **Where it helps.** Lock-step helps graphs with many terms, where the per-term divisions are a latency chain. It
  hardly helps primitive graphs: one long gathered sum.

### Margins at the tests (P3)

The ratio is |v|/err, binned by decades. A point that fails the 1e-9 test (long double) goes to binary128, and a
binary128 evaluation that fails 1e-23 goes to MP. Values are at rate .8 / rate .9. All 12 runs pass every consistency
check:
- histogram totals equal the row counters;
- every binary128 failure equals an MP call;
- every long-double failure lies below 1e-9.

| Block | binary128 per point | MP per point | MP per binary128 (fails 1e-23) | 1e-9 failures in [1e-10, 1e-9) | 1e-9 failures below 1e-12 | binary128 passes in [1e-23, 1e-22) | in [1e-23, 1e-21) | in [1e-23, 1e-20) |
|---|---|---|---|---|---|---|---|---|
| random free L7 | 0.366 / 0.321 | 0.0345 / 0.0216 | 0.094 / 0.067 | 13.8% / 15.8% | 63.1% / 58.8% | 1.8% / 1.5% | 4.0% / 3.3% | 6.7% / 5.6% |
| random power L7 | 0.786 / 0.734 | 0.1306 / 0.0835 | 0.166 / 0.114 | 7.5% / 9.5% | 76.6% / 71.6% | 3.0% / 2.4% | 6.3% / 5.3% | 10.2% / 8.7% |
| random free L8 | 0.411 / 0.371 | 0.0611 / 0.0409 | 0.149 / 0.110 | 11.0% / 12.5% | 69.7% / 66.0% | 2.4% / 2.1% | 5.2% / 4.6% | 8.5% / 7.5% |
| random power L8 | 0.863 / 0.825 | 0.2475 / 0.1783 | 0.287 / 0.216 | 4.9% / 6.2% | 84.0% / 80.3% | 3.7% / 3.3% | 7.6% / 7.1% | 11.9% / 11.3% |
| heavy free L8 | 0.833 / 0.801 | 0.2392 / 0.1736 | 0.287 / 0.217 | 5.0% / 6.2% | 84.1% / 80.6% | 3.7% / 3.4% | 7.7% / 7.2% | 12.0% / 11.4% |
| heavy power L8 | 0.940 / 0.920 | 0.3587 / 0.2673 | 0.382 / 0.291 | 2.6% / 3.5% | 90.6% / 87.4% | 4.3% / 4.1% | 8.8% / 8.6% | 13.6% / 13.4% |

The next table gives the MP calls added by a double-double tier tested at 1e-21 or 1e-20 (the binary128 passes in the
range above, divided by the MP calls), and the depth of the MP cancellations as a fraction of MP evaluations:

| Block | MP increase, dd at 1e-21 | dd at 1e-20 | MP below 1e-50 | below 1e-60 | below 1e-63 | below 1e-66 | below 1e-77 | Deepest decade |
|---|---|---|---|---|---|---|---|---|
| random free L7 | +43% / +49% | +71% / +83% | 1.0% / 0.6% | 2.1e-3 / 1.1e-3 | 1.3e-3 / 6.4e-4 | 8.5e-4 / 4.1e-4 | 1.6e-4 / 6.2e-5 | 1e-131 / 1e-117 |
| random power L7 | +38% / +47% | +62% / +76% | 0.7% / 0.3% | 9.3e-4 / 3.6e-4 | 5.1e-4 / 2.0e-4 | 2.9e-4 / 1.1e-4 | 3.7e-5 / 9.3e-6 | 1e-108 / 1e-96 |
| random free L8 | +35% / +42% | +57% / +68% | 1.1% / 0.6% | 1.9e-3 / 7.4e-4 | 1.1e-3 / 4.0e-4 | 6.5e-4 / 2.2e-4 | 9.0e-5 / 2.6e-5 | 1e-108 / 1e-96 |
| random power L8 | +27% / +33% | +42% / +52% | 1.8% / 0.9% | 3.5e-3 / 1.4e-3 | 2.1e-3 / 7.9e-4 | 1.3e-3 / 4.5e-4 | 2.0e-4 / 5.1e-5 | 1e-115 / 1e-103 |
| heavy free L8 | +27% / +33% | +42% / +53% | 1.7% / 0.8% | 2.8e-3 / 1.1e-3 | 1.7e-3 / 6.2e-4 | 1.0e-3 / 3.3e-4 | 1.5e-4 / 2.9e-5 | 1e-100 / 1e-89 |
| heavy power L8 | +23% / +30% | +36% / +46% | 2.0% / 1.0% | 3.8e-3 / 1.5e-3 | 2.3e-3 / 8.1e-4 | 1.4e-3 / 4.5e-4 | 1.9e-4 / 5.2e-5 | 1e-115 / 1e-103 |

**Digits left at each threshold.** These follow from the unit roundoff:
- binary128 (2^-113 ≈ 9.6e-35) keeps 11.0 digits at its 1e-23 test;
- double-double (2^-106 ≈ 1.2e-32) keeps 11.9 digits at 1e-20 and 10.9 at 1e-21;
- `gmp_float<77>` (at least 256 bits, ≤ 8.6e-78) keeps 14 digits at 1e-63 and 11 at 1e-66.

The deepest MP cancellation seen, 1e-131, leaves the 350-digit tier at least 219 digits.

### Lane shapes (P4), memory per lane and load + staging

Each shape ran once on a fixed L8 workload. N lane processes, pinned to disjoint NUMA-aligned core sets, work through
LPT shares in blocks of max(16 × T, 256) tasks of 16,384 points, about 10–11 thread-seconds each.
- **Throughput** is in cost-model seconds (the J-SWEEP-1 model of the Expanse EPYC 7742) per node-second.
- **Busy** is Σ task seconds / (cores × wall).
- **Load** is the worker's single-threaded graph loading (text parse, rate tables, trie).
- **Staging** is reading the members from the pack and checking their sha256.
- **Shares** are of node time: Σ per lane / (lanes × wall).

**Expanse, full node** (54661719, 128 cores, 4,018 tasks; best 16x8):

| Shape | Throughput | vs best | Busy | OpenMP eff. | Load | Staging | Load + staging | Peak RSS per lane | Σ peak RSS | Lowest lane NUMA locality | Lane-end spread |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1x128 | 102.98 | 0.908 | 0.856 | 0.960 | 9.75% | 0.88% | 10.62% | 3.60 GiB | 3.6 GiB | 1.0000 | 0.0 s |
| 2x64 | 102.00 | 0.899 | 0.847 | 0.961 | 9.67% | 0.38% | 10.05% | 3.54 GiB | 7.1 GiB | 0.9992 | 13.4 s |
| 4x32 | 107.87 | 0.951 | 0.893 | 0.967 | 5.05% | 0.36% | 5.41% | 1.77 GiB | 7.1 GiB | 0.9971 | 16.4 s |
| 8x16 | 112.32 | 0.990 | 0.928 | 0.972 | 2.62% | 0.18% | 2.80% | 0.89 GiB | 7.1 GiB | 0.9943 | 12.4 s |
| 16x8 | **113.45** | 1.000 | 0.939 | 0.983 | 1.33% | 0.09% | 1.42% | 0.68 GiB | 10.7 GiB | 0.9923 | 20.9 s |

**Expanse, half node** (54661771, socket 0 with 64 cores, 2,010 tasks; best 8x8):

| Shape | Throughput | vs best | Busy | OpenMP eff. | Load | Staging | Load + staging | Peak RSS per lane | Σ peak RSS | Lowest lane NUMA locality | Lane-end spread |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1x64 | 54.28 | 0.935 | 0.907 | 0.968 | 5.20% | 0.94% | 6.14% | 1.80 GiB | 1.8 GiB | 0.9974 | 0.0 s |
| 2x32 | 54.80 | 0.944 | 0.914 | 0.968 | 5.27% | 0.22% | 5.50% | 1.77 GiB | 3.5 GiB | 0.9971 | 0.0 s |
| 4x16 | 56.72 | 0.978 | 0.942 | 0.972 | 2.71% | 0.16% | 2.87% | 0.89 GiB | 3.5 GiB | 0.9947 | 1.1 s |
| 8x8 | **58.03** | 1.000 | 0.965 | 0.987 | 1.40% | 0.09% | 1.48% | 0.70 GiB | 5.3 GiB | 0.9922 | 3.4 s |

**symmetry, amddebugq <NODE>** (569788, 64 cores, the same 2,010 tasks; best 8x8):

| Shape | Throughput | vs best | Busy | OpenMP eff. | Load | Staging | Load + staging | Peak RSS per lane | Σ peak RSS | Lowest lane NUMA locality | Lane-end spread | symmetry / Expanse half node |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1x64 | 61.29 | 0.966 | 0.921 | 0.968 | 4.39% | 0.31% | 4.70% | 1.80 GiB | 1.8 GiB | 1.0000 | 0.0 s | 1.129 |
| 2x32 | 60.19 | 0.949 | 0.911 | 0.968 | 4.27% | 0.32% | 4.59% | 1.77 GiB | 3.5 GiB | 0.9965 | 7.1 s | 1.098 |
| 4x16 | 62.20 | 0.981 | 0.942 | 0.973 | 2.22% | 0.18% | 2.40% | 0.89 GiB | 3.6 GiB | 0.9927 | 4.0 s | 1.097 |
| 8x8 | **63.42** | 1.000 | 0.962 | 0.987 | 1.14% | 0.08% | 1.22% | 0.70 GiB | 5.3 GiB | 0.9891 | 6.4 s | 1.093 |

**Rows.** Within each run, the rows are identical across shapes: digest `16d6ff3d…` for the full node and `937154fb…`
for the half node. The symmetry rows (GCC 11.4, Zen 3) are byte-identical to the Expanse half node's (GCC 13.3, Zen 2),
including the binary128 and MP counts.

**NUMA.** No run had a numa_miss. Cross-node pages (other_node / numa_hit, node-wide) were at most 8.3e-4 on the full
node and at most 3.0e-4 on symmetry. On the half node they were 1.1–1.3%, because numastat counts the whole node, and
there the job's lanes used only one socket. Each lane's own pages were at least 98.9% local (`numa_maps`).

**Ranking.**
- The best shape gives 8-thread lanes on both sites: 16x8 on Expanse, which is 2 lanes per 16-core NUMA node, and 8x8
  on symmetry, 1 lane per NUMA node.
- On Expanse the second shape, 8x16 (the `numa` default there), is 1.0% behind 16x8. On symmetry 4x16 is 1.9% behind
  8x8.
- symmetry ranks 1x64 above 2x32, the reverse of the Expanse half node. The two differ by 2%, inside single-run noise.
- Absolute throughput carries a symmetry/Expanse factor of 1.09–1.13, so only the ranking carries across sites.

**Load + staging.** Graph loading is nearly all of the share. At the 8-thread shapes it is 1.22% (symmetry 8x8), 1.42%
(Expanse 16x8) and 1.48% (Expanse half node 8x8) of node time. It grows as the lanes widen, because one thread loads
while the others wait: 2.4–2.9% at 16 threads and 4.6–10.6% at 32–128 threads. Staging, including the sha256
checks, is at most 0.94% at any shape and 0.08–0.09% at 8 threads. P4's tasks are about 10 s, against the production
target of 60 s, so production's share at the same shape should be smaller.

**Memory per lane.** Peak RSS per lane is 0.68–0.70 GiB at 8 threads (blocks of 256 L8 tasks) and 0.89 GiB at 16. At
32 threads, and at 64 on 64 cores, it is 1.8 GiB. The 64- and 128-thread lanes of the full Expanse node reach 3.5–3.6
GiB (blocks of 1,024–2,048 tasks). A whole 8x8 node peaks at 5.3 GiB, far inside the 245 GB of an exclusive node.

### Decisions for Stage 4b and 4c

Each row gives the plan's rule ("Performance plan" and A-PERF/A-FLAG in `LRI_C8_D2_HPC_loop/PLAN.md`) and the number
measured above. A-PERF-2 still applies to every default-path change: it must pass A-RPL-1/2/3/6/7 exactly and show at
least a 3% speedup (median of 3 runs on the same node, L8 sweep sample), or it is reverted.

| Item | Plan's rule | Measured | Decision |
|---|---|---|---|
| **R5a** parallel graph loading | Expected: load share → < 0.1%; kept only under A-PERF-2 | Load share of node time 1.14% (symmetry 8x8) and 1.33% (Expanse 16x8). It is 4.3–9.8% only with 1–2 lanes. Per-lane NUMA locality is already ≥ 0.989 | **Go, low priority** (first in 4b, cheap, bitwise). At the default shapes with P4-size tasks the gain is bounded by 1.1–1.3%, below the 3% bar. It grows as tasks shrink: about 4× at the pilot's 4,096 points per graph, and more in the 512-point sweeps. A-PERF-2 decides; report the production-shape gain separately |
| **R5b** lanes and lane shape | P4 sets the default `C8_LANES`, plan `--threads`/`--checkpoint-tasks` and the A-PERF-3 reference; expected ×1.05 | symmetry: 8x8 best at 63.42; 4x16 −1.9%, 1x64 −3.4%, 2x32 −5.1%. Expanse: 16x8 best at 113.45; 8x16 −1.0%, 4x32 −4.9%, 1x128 −9.2%, 2x64 −10.1%. Busy 0.962 / 0.939, OpenMP efficiency 0.987 / 0.983 | **Go.** `--threads 8` everywhere, so one plan runs on both sites. `--checkpoint-tasks` stays at its default, max(16 × 8, 256) = 256, the P4 block. symmetry: `C8_LANES=numa` (8 × 8, already the AMD default). Expanse: `C8_LANES=16` (16 × 8); `numa` there gives 8 × 16, −1.0%. A-PERF-3 reference: symmetry 8x8, 63.42 cost-model s per node-second (228,300 per node-hour) in J-SWEEP-1 units on the Stage-3 binary. It is re-expressed in the final cost model (J-SWEEP-2) before the smoke |
| **R3a** inline binary128 add/sub/mul (div only if ≥ 10% of the tier) | Fast paths for add, sub, mul; div only if P1 shows div ≥ 10% of the binary128 tier | The kernel's `__addtf3` + `__multf3` (libgcc + PLT) take 47.6 / 38.0 / 55.6 / 47.9% of samples (free L7 / power L7 / free L8 / power L8); `__addtf3` alone 32.9–52.8%. The kernel's `__subtf3` is < 0.01% (below perf's report cutoff; only the shift path, `T(logx[j])-T(shift)/g.L`, `kernel.hpp:179`). `__divtf3` is 0.54–1.10% of samples, i.e. 1.0–2.2% of the tier. The binary128 tier is 61.5% of L8 time (model, campaign a) | **Go** for add (with sub as signed add) and mul. **Div excluded**: 2.2% at most against the 10% rule. Add is the payoff: 84–94% of the kernel's binary128 arithmetic |
| **R3c** lock-step binary128 points | Only after R3a, and only if P1 shows the tier latency-bound | The heavy free L8 block (binary128 57%, MP 35%) runs at IPC 2.71 with 64 threads and 2.76 with 1. The promoted tiers alone run at ≈ 2.8 | **No-go** on the baseline: throughput-bound. Re-measure IPC with perf stat on the R3a binary, whose inline code changes the instruction mix. Attempt R3c only if that IPC is below 1.5 |
| **R4a** MP temporaries | Preallocated temporaries with the same mpf arithmetic sequence; expected part of ×1.15–1.25 | Allocation and lifetime (malloc/free, `mpf_init2/clear/set/set_si`, GMP allocate/free, `operator=`): 0.92 / 1.11 / 0.49 / 0.74% of samples. With `__gmpn_copyi`: 4.1 / 4.5 / 4.8 / 5.7%, but part of `copyi` runs inside `mpf_add` and stays | **Go** as planned, but small. Preallocation alone (≤ 1.1%) cannot reach 3%. Eliding the exact same-precision copies (`T v=sums[parent]` and the assignments), with the arithmetic calls unchanged, is the only route to the bar. Otherwise revert |
| **R6** lock-step first pass | Go if IPC < 1.5 or the probe speedup ≥ 1.2; expected ×1.03–1.1 | IPC 1.009 (free L7) and 1.037 (free L8) on the promotion-free blocks; 1 thread: 1.004 and 1.038. Probe with 2 points: 1.098 geometric mean, 1.032 promotion-free, 1.168 heavy (max 1.200). The first pass and sampling are 4.5–10.4% of L8 time (model) and 3.8–5.6% of heavy-block thread time | **Go by the rule** (IPC < 1.5), last in 4b. The expected overall gain is at most about 1.5% (free L8: 9.0–10.4% of the time × (1 − 1/1.17); primitives gain only 1.03), below A-PERF-2's 3%, so a revert is the likely outcome |
| **R4e** allocation-free `calculate_reference<ld>` | Go only if P1 shows ≥ 1% | 0.00% in all four blocks: inlined, no samples on lines 143–148, and all of `expl` is 0.03–0.13% | **No-go** |
| **R4c** `exp1` (flag) | Size: the expq share (~4% of the tier) and most of the MP exponential time | binary128 side: libquadmath + fenv 0.53 / 0.66% (L8) and 2.24 / 2.89% (L7) of samples, i.e. 0.9–6.7% of the tier; `expq` itself 0.02–0.09%. MP side: the exponential symbols are ≥ 1.35–6.66% (lower bound). The fixed MP part of the per-call law is 6.2% (free L8) and 14.3% (power L8) of campaign a's time | **Keep in 4c.** It replaces E of the 2E exponentials per promoted point with one exponential and E multiplications (when shift ≠ 0), saving up to about 47% of them. Expected saving: up to about 3% (free L8) and 7% (power L8) on the MP side; on the binary128 side ≤ 0.3% at L8 and ≤ 1.4% at L7 |
| **R4d** `mpconv` (flag) | Size: the string-conversion share of the MP tier | `get_str` family + `strtold`: 0.01–0.11% of samples (upper bound) | **Not worth a profile on speed.** Keep it last in 4c if at all; its only gain would be a correctly rounded conversion |
| **R3b** `dd` (flag): `C8_DD_RATIO` | Set from P3 so that at least 11 digits remain; default 1e-20 | dd keeps 11.9 digits at 1e-20 and 10.9 at 1e-21 (binary128 keeps 11.0 at 1e-23). MP calls rise by 36–83% at 1e-20 and by 23–49% at 1e-21. For the L8 uniform draws at 1e-20: free +57% / +68%, power +42% / +52% (rates .8 / .9) | **`C8_DD_RATIO` = 1e-20** (the default). 1e-21 fails the 11-digit rule. The dd range guard keeps out-of-range points on binary128, so these increases are upper bounds |
| **R4b** `mp256` (flag): `C8_MP256_RATIO` | Default 1e-63 | `gmp_float<77>` keeps 14 digits at 1e-63. Escalations to 350 digits: 2.0e-4 to 2.3e-3 of MP evaluations, against 1.1e-4 to 1.4e-3 at 1e-66. Deepest cancellation 1e-131 | **`C8_MP256_RATIO` = 1e-63** (the default). The 3 extra digits cost < 1e-3 more escalations. The 77-digit tier keeps 99.8–99.98% of MP evaluations |
| **H4** binary pack (D7) | Proposed to C63d only if load + staging > 2% of node time at L8 | 1.22% (symmetry 8x8), 1.42% (Expanse 16x8), 1.48% (Expanse half node 8x8) | **Not needed**: packs stay text (`LRI_C8_shared/inventory/PACK_FORMAT_PROPOSAL.md`) |
| Per-job graph cache (not planned) | Not planned unless P1 or P5 shows staging plus hashing ≥ 2% at L8 | Staging with its sha256 checks: 0.08% (symmetry 8x8), 0.09% (Expanse 16x8), at most 0.94% at any shape | Stays not planned |
| Persistent worker per lane (not planned) | Not planned unless load and start-up stay ≥ 2% after R5a | Already before R5a: load + native start-up 1.23% (symmetry 8x8: 1.14 + 0.09) and 1.40% (Expanse 16x8: 1.33 + 0.07) | Stays not planned |

**Stage-4b order.** These decisions leave this order: R5a (cheap; the gate decides), R5b, R3a (add and mul, the bulk of
the expected gain), R4a (only with copy elision), R6 (expected revert). R3c and R4e are not attempted. The flag order
of 4c stays R3b → R4c → R4d → R4b → R7. On these numbers R4d is the weakest item, and R4b's escalation cost is
negligible.

`LRI_C8_shared/PERF_NOTES.md` carries the C62d entry of 2026-10-04 with the numbers C63d can reuse.
`LRI_C8_shared/inventory/PACK_FORMAT_PROPOSAL.md` (H4) is the "not needed" note (sha256 `7343fb6a…`, md5
`6a030338189175bdbcde065df39c8781`).

## Stage 4b: default-path optimizations (2026-10-04) [G4b: A-PERF-2, A-RPL-1..7 on the final default binary; start of A-PERF-5]

This is the Stage-4b summary. Each optimization has its own section below: development ("Stage 4b development: R5a and
R5b", "Stage 4b R3a", "Stage 4b R4f") and the A-PERF-2 gate ("Stage 4b integration"). R4a's development record is
`benchmarks/expanse_2026-10-c8/stage4b/dev_r4a/`. Every speedup below is A-PERF-2's: Expanse job 54669709, one
exclusive node (2 × EPYC 7742), the L8 sweep sample (2,000 graphs, 2 × 512 points, gmp backend), 16 × 8 lanes,
the median of 3 interleaved runs of the lane-thread seconds. The bar is ×1.03.

**The final default binary** is +R5 +R3a. Its `src/` is d46e736's, unchanged through b47b008 (the commit G4b tested)
and the write-up after it. Expanse builds it with Spack GCC 13.3.0, GMP 6.2.1, Boost 1.77 headers and `-O3 -std=c++17
-fopenmp -ffp-contract=off -fno-fast-math`, no `-march`: `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp`
`1d2a2181…`, byte-identical in the integration builds of d46e736 and e7ef98d and in the G4b build.
`numerical_change: false` (`docs/NUMERICS.md`).

### Per optimization

| # | Change | Exact gates | A-PERF-2 speedup | Decision |
|---|---|---|---|---|
| R5a | Parallel graph loading in the worker: `omp parallel for schedule(dynamic,1)` over the block's graph ids into a pre-sized vector, so lane threads first-touch their graphs; the lowest id's error is thrown, as before (`src/c8d2_integrate.cpp`) | Replay subset, G-L8SELF and thread identity (54669703, 54669707); the first-error test (200 bad-input runs, stderr byte-identical; development 54666182) | **×1.1539** (free ×1.1749, power ×1.0997). The sample's load share falls from 16.4% to 3.0%. At P4-size tasks (about 10 s) the gain was about 1.4% (load share 1.35% → 0.20%; development 54666183); at production's 60 s tasks the load share is estimated at 0.04% (not measured) | **Kept** |
| R5b | Lane defaults: each NUMA node split into the fewest equal lanes of at most `--threads` cores, so 16 × 8 on Expanse and 8 × 8 on symmetry at `--threads 8`; plan defaults tested (`tools/lanes.py`, `tools/sweep.py`) | Scheduling only (A-RPL-6: thread identity); lane probe on the real topology (54666372) | Not a kernel change. On the sample, busy fraction 0.804 → 0.931 together with R5a; in development P4, 0.950 → 0.966 | **Kept** |
| R3a | Correctly rounded binary128 add, sub and mul as inline integer code on 64-bit words (`src/quadfast.hpp`), used by every binary128 `+`, `-`, `*` of `calculate_shared<Q>`; non-normal cases call libgcc; div excluded (1.0–2.2% of the tier, rule 10%) | `tests/quad_differential.py`: 2^32 random pairs per operation, edge lists, injection self-test, ASan+UBSan, 0 mismatches (54669012, 54672109 and G4b 54672152); G-L8SELF, thread identity and replay at each step; the full J-VAL-2/3 below | **×1.4262** (free ×1.4647, power ×1.3397). Heavy L8 blocks ×1.442 / ×1.331 (development 54669014); binary128 tier per call ×2.16 / ×2.20 | **Kept** |
| R3c | Lock-step binary128 points | Rule: only if IPC < 1.5 on the R3a binary | IPC 3.04 (+R3a) and 3.05 (+R4a) on heavy_free_L8 at 64 threads (54669709); 3.08 in development (54669014); Stage 3: 2.71 | **Not attempted** (throughput-bound) |
| R4a | MP tier: per-thread preallocated temporaries, in-place mpf calls in the expression templates' order, and the host-approved elision of exact same-precision copies (`src/kernel.hpp`, gmp only) | Exact: call-sequence trace (11/11 rules), mpdiff, G-L8SELF, replay (development 54666232–54666315; integration 54669705, 54669708) | **×1.0093** (free ×1.0085, power ×1.0106); ×1.0024 on top of R4f | **Reverted**, code only (ea59445). `src/` is again d46e736's |
| R6 | Lock-step first pass | Host decision (PLAN-REVIEW-LOG, "Host decisions for Stage 4b") | Upper bound about 0.8% overall: the lock-step probe gives ×1.098 on `calculate_products`, and the first pass is 8–9% of L8 time, so (1 − 1/1.098) × 9% ≈ 0.8% < 3% | **Not attempted** |
| R4e | Allocation-free `calculate_reference<ld>` | Rule: only if P1 shows ≥ 1% | 0.00% in all four P1 blocks (inlined; no samples on its lines; all of `expl` 0.03–0.13%) | **No-go** |
| R4f | GMP 6.2.1 built for zen2 (`--host=zen2-pc-linux-gnu`, `make check` 197/197) behind the opt-in `GMP_PREFIX` knob (host addition) | G-L8SELF, thread identity and the replay subset for B2f, B4 and the final zen2 worker `aa84cd45…` (54669708, 54672109); the default build is unchanged | **×1.0520** over the kept default (free ×1.045, power ×1.068); ×1.0449 over +R4a | **Kept as opt-in only, NOT cleared for production.** Not in the default build; each site needs its own build and gates. Expanse: the owed gates ran in Stage 5 (54676895), but its forced tiers, point checks and class-B builds linked Spack's libgmp, not the zen2 one (Y1, Stage-6 fix round 2), so the clearance is withdrawn until those checks are re-run with the bound tools, together with the A-EXP-3 J-EXP-1 rerun; symmetry: none yet |

R1+R2 (allocation) is the design tool's (Stage 3, `tools/design.py`) and is not a kernel change.

### G4b: the final J-VAL-2 and J-VAL-3 on the final default binary (Expanse jobs 54672150, 54672151, 54672152)

The commit under test is b47b008: the integration's head a2ef0a2 plus the job scripts, with `src/` and the Makefile
unchanged since e7ef98d. Its `git archive` export (6,363 files equal) was built from scratch on Expanse. Every
executable is byte-identical to e7ef98d's build, so the A-PERF-2 numbers of +R3a apply to it directly. The evidence
is in `benchmarks/expanse_2026-10-c8/stage4b/final/` (README there). `scripts/summarize_final.py` recomputes the
verdicts into `final_summary.json` and compares each record with Stage 3's.

| Job | Gate | Result |
|---|---|---|
| 54672150 (build, `shared`, 0:51) | Build and identity | `bin/c8d2_decimal` `99a51c1d…`, `bin/c8d2_gmp` `1d2a2181…`, `make c7ref` `4537dcfd…`/`6c829386…`, all equal to e7ef98d's; L8 packs re-hashed equal to the manifest |
| 54672151 (J-VAL-2, one node, 4:06) | `make test-full`: A-RPL-1/2/3 on the L=2 graph and all 3,773 L3–L7 kernels, both backends; point checks; check_inputs, workflow, staging | **All passed.** G-C7 exact in 39,048 rows per backend (22,212 with mp > 0; 1,074,943 binary128 and 111,112 MP points); G-REF exact in 7,548 rows (gmp exact also in its 4,121 mp > 0 rows); G-JET exact in 39,048 rows. Chunks and layouts (A-RPL-6) agree to 2.1e-18 normalized (bound 1e-12). Point checks L3–L8: largest scaled MP error 2.1e-353 (gmp350) and 1.8e-302 (decimal300), bound 1e-280 |
| 54672152 (J-VAL-3, one node, 14:26) | A-IN-6(b) L=2 control | **Passed** with Stage 3's registered seed (no new seed): largest pull 1.22 (bound 4 SE); rounding gaps ≤ 1.1e-19 per row (bound 2^-60) |
| | A-RPL-6 thread identity | **Identical** at 1, 8, 16, 64 threads and 8 × 8 lanes, L8 free and power, both backends |
| | A-RPL-4 G-BK8 | **Exact**: L7 and L8, 400 kernels per sector, decimal against gmp, including 2,779 mp > 0 rows |
| | A-RPL-7 G-L8SELF | **Exact** against the Stage-3 baseline on both backends: 4,000 rows each (762,395 + 359,972 binary128 and 114,648 + 99,884 MP points) |
| | A-RPL-5 forced tiers | **Passed**: (a) ≤ 3.3e-18·err_ld and ≤ 1.05e-33·err_q; (b) MP ≤ 1.3e-352 (gmp350), ≤ 3.7e-313 (decimal300); (c) 0 decision mismatches; 29,284 / 50,625 binary128-accepted and 3,541 / 12,568 MP points (free / power) |
| | R3a differential | **Passed**: 2^32 random pairs per operation, edge lists, injection self-test and ASan+UBSan, 0 mismatches |
| | A-ORC-6 merge scale | **Passed**: 1,249,792 rows, parallel merge byte-identical to serial, peak RSS 37.8 MiB per process |
| | A-ASM-4 (`assembly_checks --exact`) | **Passed**: 37/37 |

**Against Stage 3.** The same tests ran on the Stage-3 baseline in jobs 54637263 and 54637264. After removing the
run-specific fields (seconds, environment, commands, paths, the executables' digests), every one of these records is
equal: `validate_full` (50 tests), `point_checks`, `l2_control`, `bk8`, `thread_identity`, `forced_tiers` and
`l8self`. The only exceptions are the inspector tests that the checkpoint review replaced (T-04) or added (CK-K03).
**G4b is met:** A-PERF-2 (integration) and A-RPL-1..7, exact on the final default binary.

**Cost.** 39.77 SU: build 0.23, J-VAL-2 8.75, J-VAL-3 30.79. Stage 4b used 375.6 SU of its 1,300: development 250.0,
integration 85.8 and G4b 39.8.

### Speedup of the final default binary over the Stage-3 baseline per (sector, L), where measured [start of A-PERF-5]

| Sector | L | Workload (Expanse, one node) | Stage 3 | Final default | Speedup | With the opt-in zen2 GMP |
|---|---|---|---:|---:|---:|---:|
| free | 8 | L8 sweep sample, 1,600 graphs × 2 × 512 points, 16 × 8 lanes; lane-thread s, median of 3 (54669709) | 1454.0 | 845.0 | **×1.721** | ×1.798 (808.5) |
| power | 8 | the same, 400 graphs | 540.8 | 367.1 | **×1.473** | ×1.573 (343.9) |
| both | 8 | the whole sample | 1994.8 | 1212.1 | **×1.646** | ×1.731 (1152.2) |

- The sample is load-heavy (512-point tasks), so R5a's share of these factors is larger than in production. The heavy
  L8 fixture blocks (256 tasks × 16,384 points, 64 threads, integration seconds; load negligible) measured R3a alone
  at ×1.442 (free) and ×1.331 (power) (development 54669014, the add273b binary, whose kernel is the final one).
- L3–L7 and the per-graph factors are not measured in Stage 4b. J-SWEEP-2 (Stage 5) runs every graph of every
  (sector, L) on the final binary and, against J-SWEEP-1's per-graph µs on the Stage-3 baseline, completes A-PERF-5
  for the default path. The opt-in profiles (Stage 4c) add their own rows. Done on Expanse in Stage 5 (J-SWEEP-2E):
  "Stage 5 on Expanse" below.

## Stage 4c: opt-in numerics profiles (2026-10-05) [A-PERF-5 for the opt-in profiles; A-FLAG-3 F4, A-FLAG-7]

Every profile here is a numerics change, off by default (D1); the default binary stays `1d2a2181…` (A-RPL-8 on the
integrated head, build 54673898). Accuracy gates, projected core-hours at the four targets and the approval status:
`docs/NUMERICS.md`, "Stage 4c gate: J-FLAG results (A-FLAG-7)". Development: `docs/NUMERICS.md` sections R3b, R4b and
R4c, and `benchmarks/expanse_2026-10-c8/stage4c/dev_*`. R4d (`mpconv`) was not implemented (≤ 0.11% in P1).

**F4** (A-FLAG-3; the J-FLAG gate runs 54673900–54673904 on export 5569c535dcfd, one exclusive node each, the L8
sweep sample of 2,000 graphs × 2 × 512 points at rate .8, 16 × 8 lanes, the median of 3 interleaved repeats of each
binary, lane-thread seconds; every repeat of a binary gave the same rows):

| Profile | Binary | Exact (free / power / total) | Profile (free / power / total) | Speedup: free | power | total |
|---|---|---:|---:|---:|---:|---:|
| `dd` (R3b, cascade) | `51614820…` | 852.1 / 370.2 / 1222.8 | 590.6 / 289.4 / 880.0 | ×1.443 | ×1.279 | **×1.389** |
| `mp256` (R4b) | `9e884b1b…` | 978.0 / 413.8 / 1391.8 | 748.5 / 266.2 / 1014.7 | ×1.307 | ×1.555 | **×1.372** |
| `exp1` (R4c) | `0bf3f1a8…` | 843.0 / 365.9 / 1209.7 | 835.6 / 365.1 / 1201.7 | ×1.009 | ×1.002 | ×1.007 |
| `dd+mp256+exp1` | `6bc26966…` | 840.6 / 366.0 / 1206.6 | 397.8 / 158.9 / 556.6 | ×2.113 | ×2.304 | **×2.168** |
| layout control: the framework's all-stub `dd` (exact arithmetic) | `e2eb509f…` | 840.6 / 365.0 / 1205.2 | 835.6 / 363.3 / 1198.9 | ×1.006 | ×1.005 | ×1.005 |

The mp256 run's node (<NODE>) ran the exact binary about 14% slower than the other nodes; each speedup compares
the two binaries interleaved in one job. exp1's ×1.007 is code layout (the control's ×1.005; no shifted point exists
to act on).

**Speedup per (sector, L)** [A-PERF-5]. Over the final default binary, from F2's paired blocks (every graph of L3–L8,
campaigns a and b, 4 × 256 points per graph, both binaries back to back on one lane; integration seconds of the
tasks, without start-up and loading); L3–L5 tasks last milliseconds, so their ratios carry a few percent of noise:

| Sector | L | `dd` | `mp256` | `exp1` | `dd+mp256+exp1` |
|---|---|---:|---:|---:|---:|
| free | 3 | ×1.036 | ×0.944 | ×0.924 | ×0.955 |
| free | 4 | ×1.043 | ×0.993 | ×0.994 | ×1.020 |
| free | 5 | ×1.025 | ×1.000 | ×0.992 | ×1.030 |
| free | 6 | ×1.025 | ×1.027 | ×0.992 | ×1.019 |
| free | 7 | ×1.586 | ×1.272 | ×1.008 | ×2.370 |
| free | 8 | ×1.533 | ×1.297 | ×1.012 | ×2.307 |
| power | 3 | ×1.108 | ×1.008 | ×1.006 | ×1.167 |
| power | 4 | ×1.468 | ×1.024 | ×0.954 | ×1.554 |
| power | 5 | ×1.659 | ×1.289 | ×1.003 | ×2.360 |
| power | 6 | ×1.506 | ×1.488 | ×1.008 | ×2.915 |
| power | 7 | ×1.382 | ×1.651 | ×1.004 | ×3.003 |
| power | 8 | ×1.314 | ×1.640 | ×1.008 | ×2.655 |
| all | all | ×1.463 | ×1.381 | ×1.011 | ×2.404 |

Over the Stage-3 baseline at L8 (the Stage-4b factor of the final default binary on Expanse, ×1.721 free, ×1.473
power, ×1.646 on the whole sample, times the profile's F4 factor; two jobs, so an estimate): dd ×2.48 / ×1.88 / ×2.29, mp256
×2.25 / ×2.29 / ×2.26, exp1 ×1.74 / ×1.48 / ×1.66 (= the default), dd+mp256+exp1 ×3.64 / ×3.39 / ×3.57 (free /
power / whole sample). L ≤ 7 over Stage 3, and both sites: "Stage 5: the refined cost table".

**Where the gains come from** (Stage 4a/4b tier split after R3a: first pass ~14%, binary128 ~45%, MP ~40% of L8
time). dd accepts 88% of the exact path's binary128 points (F1 set) at ×5.9–8.0 lower cost per call, and its cascade
adds no MP evaluation (F3 counters unchanged). mp256 halves the MP tier (×2.0–2.1 per call; the 77-digit tier is
dominated by mpf additions' fixed per-call cost) and escalates 7.4e-4 of the F1 set's MP points (1.7e-3 to 2.3e-3 on
heavy L8 blocks). Together they remove disjoint shares, so the combination (×2.17) beats the product of its parts
(×1.91); what remains is mostly the first pass and the escalated MP evaluations. The projected core-hours (frozen
allocation of the final default binary's test-only freezes, each stratum divided by its speedup): dd ×0.68–0.70,
mp256 ×0.75–0.76, dd+mp256+exp1 ×0.46–0.47, exp1 ×1 (layout only), R7 ×0.82–0.88 (`docs/NUMERICS.md`, A-FLAG-7).

## Stage 5 on Expanse: J-SWEEP-2E, the Expanse cost model, A-PERF-5 per (sector, L) and the pilot estimate (2026-10-05) [A-PERF-5; A-PERF-4 on Expanse; J-PIL-1E]

Evidence: `benchmarks/expanse_2026-10-c8/stage5/exp/` (README and `s5e_summary.json`, which
`scripts/s5e_summary.py` recomputes). Export 07ff5c1975e5 (5d7586e plus job scripts); default binaries `99a51c1d…`
and `1d2a2181…`, exact path.

**The Expanse cost model** `cost_models/gmp_expanse_amd_c8.json` (`0e1ccfc9…`). J-SWEEP-2E, job 54676908 on
<NODE>: the final default binary on every graph of both campaigns (48,346 `campaign:sector:L:graph` keys), 2 × 512
points, 16 × 8 NUMA-pinned slots, planned with J-SWEEP-1's model and `--shards 16`; 4:54 on one node, self-registered,
`accounting.py` complete (10.45 core-hours allocated, 5.41 busy). symmetry's J-SWEEP-2/3 give
`gmp_symmetry_amd_c8.json` and the CPU-class factors.

**A slow node: <NODE>.** The first run of J-SWEEP-2E (54676896) landed on <NODE>, which already ran the exact
binary 14% slow in the Stage-4c mp256 gate. Its per-point costs are ×1.146 / ×1.152 those of <NODE> on free L8 / L7,
×1.136 / ×1.121 on power L8 / L7, and ×0.97–1.01 at L3–L6, where there is no tier work. Its model is kept as evidence
only. Expanse pilot and production jobs pass `--exclude=<NODE>`.

**A-PERF-5, default path, per (sector, L).** The final binary's per-point kernel seconds (J-SWEEP-2E) against the
Stage-3 baseline's (J-SWEEP-1, 54641706 on <NODE>), summed over every graph of the stratum with equal points per
graph:

| Sector | L3 | L4 | L5 | L6 | L7 | L8 | all L |
|---|---:|---:|---:|---:|---:|---:|---:|
| free | ×1.022 | ×1.011 | ×0.994 | ×1.013 | ×1.413 | ×1.444 | ×1.443 |
| power | ×1.017 | ×1.012 | ×1.386 | ×1.195 | ×1.283 | ×1.261 | ×1.262 |
| both | ×1.021 | ×1.011 | ×1.185 | ×1.126 | ×1.371 | ×1.390 | **×1.390** |

- Per campaign at L7 / L8: a free ×1.392 / ×1.410, b free ×1.440 / ×1.485, a power ×1.253 / ×1.235, b power
  ×1.322 / ×1.294.
- These are the tasks' kernel seconds, without load and start-up. R3a's gain is in them; R5a's, which is load time, is
  not. That is why they sit below Stage 4b's ×1.646 on the L8 sample (lane-thread seconds with loading) and near R3a's
  ×1.44 (free) and ×1.33 (power) on the heavy L8 blocks.
- L3–L4 have almost no promoted points, so ×1.0 is expected; their tasks last microseconds. Two nodes, two lane shapes
  (8 × 16 against 16 × 8) and two seeds: the factors carry a percent or two from that.
- The L=2 graph is not a campaign stratum, so there is no L2 row.

**The Expanse pilot (J-PIL-1E; planned, not submitted).** The plan of the pilot that runs after the Stage-6 inspection
(H11) with this cost model: 36 indices, 386,768 tasks, **170.3 core-hours** (the plan's central projection, from
Stage-3 numbers, was about 220), largest index 1.48 h at 8 threads, projected merge 34 s. The 16 L8 indices fill one
node's 16 lanes, and the 20 L3–L7 indices follow on the lanes that free first:

| Nodes | Wall | SU (128 per node-hour) | Lane occupancy |
|---:|---:|---:|---:|
| **1** | **1.56 h** | **199** | 0.95 |
| 2 | 1.48 h | 379 | 0.50 |
| 4 | 1.48 h | 758 | 0.25 |

One node (`submit.sh --lanes 1`) with its merge is about 205 SU; a shorter wall needs a smaller `--index-hours`. The
campaign, the seed and the exact submit line are in `benchmarks/expanse_2026-10-c8/stage5/exp/README.md`.

**GMP_PREFIX on Expanse: NOT cleared for production** (withdrawn in Stage-6 fix round 2, Y1). Job 54676895 ran the
owed gates for the opt-in zen2 GMP (×1.052 on the L8 sample in Stage 4b: free ×1.045, power ×1.068), but its forced
tiers, point checks and class-B builds compiled their tools with plain `-lgmp` (Spack's library), so they do not speak
for the zen2 worker (`docs/NUMERICS.md`, "Builds"). It stays off until those precision checks are re-run on Expanse
with the tools bound to the zen2 library (`make test-full GMP_PREFIX=…` and `tests/forced_tiers.py`), owed together
with the A-EXP-3 J-EXP-1 rerun. The cost figures above are for the default build.

## Production result (2026-10-07): measured cost against the design

The C8(2) production batch `prod1-2.5e-4-ddmp256-20261006-ba68f401e46e` ran on symmetry amdq, EPYC 7543:
- `dd+mp256`, route (b), bundle `pilot1-20261006-ddmp256-2.5e-4`;
- 1,129 indices and 6.19 million tasks;
- round 1 on 8 nodes for 22.4-23.0 h, round 2 on 6 nodes for 4.4-5.6 h, then the merge (67 s).

It gave C8(2) = 45,990.00 ± 8.22 (estimated sampling SE; quote as in
`benchmarks/symmetry_2026-10-c8/production/tailcheck/README.md`, section 1). Evidence:
`benchmarks/symmetry_2026-10-c8/production/result/` (README, section 3;
`tools/accounting.py` complete over 26 ledger records).

| Quantity | Design or plan | Measured | Ratio |
|---|---:|---:|---:|
| Allocated core-h (lanes + merge + plan) | 14,465 (design, lane core-h at η_node 0.837) | **13,453.8** (lanes 13,452.0) | **×0.930** |
| Work: busy thread core-h against the plan's cost-model estimate | 12,025 | 13,217.5 | ×1.099 (free L8 ×1.107, free L7 ×1.091, power L8 ×1.056, power L7 ×1.076) |
| η_node | 0.837 (the pilot's, 3-node tail) | **0.983** (lane occupancy 0.985 × in-index 0.997) | |
| Lane walls against the planner's estimate (est / (8 × 0.9)) | 1 | 0.992 | |
| Two-round allocation projected from the plan (`production/README.md` section 4) | 12,273-13,634 | 13,454 | inside |
| Wall, first submission to the merge's end | about 26-28 h plus turnaround | 28.7 h | |
| Predicted SE: raw / with the margin 1.5 | 7.667 / 11.50 | 8.217 | ×1.072 / ×0.714 |

Notes:
- **The `dd+mp256` cost model under-estimates L7 and L8 by 6-11%**, as the exact model did in the pilot (free L8 ×1.08).
  The lanes' 0.997 in-index efficiency against the planner's 0.9 more than hides it in the walls.
- **A long run has almost no tail.** η_node 0.983 against the pilot's 0.837 makes the design's core-hours conservative by
  about 7%. For future designs on symmetry, η_node ≈ 0.98 is the measured long-run value.
- **The realized variance per stratum against the pilot-σ prediction:**
  - free L8 ×1.16, free L7 ×1.09 and power L8 ×1.32;
  - the low loops ×0.01-0.69, because the randomized Sobol nets beat 1/n where the integrand is smooth and the design
    assumes α = 0.5;
  - the total SE came in at ×1.07 the raw prediction, inside the margin.

**This table supersedes the Stage-5/6 stand-in projections** in "Stage 5: the refined cost table" below. Those had
measured costs but stand-in variances.

Evidence and every number: `benchmarks/symmetry_2026-10-c8/pilot/analysis/` (README, `cost_table.md` and
`cost_table.json` from `scripts/pa_tables.py`). The jobs were sharedq 570669 and 570672, 0.46 core-h together.

The source is the exact L8 pilot `pilot1-20261006-ba68f401e46e`, run on symmetry amdq:
- export ba68f40, executable `7741f733…`, seed 3049594997687674958;
- every one of the 24,173 graphs of both campaigns at 8 replicates × 4,096 points;
- C8 = 45,620 ± 214;
- `verify_result` clean.

`design.py freeze` was run (non-test) at the four relative targets of |C8| = 4.6e4, with:
- `--spent-core-hours 2157`: the development total of about 1,930, plus the pilot's 226.87;
- `--total-cap 1000000`, which does not bind.

So **σ_g² and c_g are the pilot's measurements**, and the cost is lane core-hours at the pilot's measured **η_node =
0.837** (`tools/accounting.py`, complete). Every bundle has K = 1 and meets every cap.

| Numerics | Site | 1e-3 | 5e-4 | 2.5e-4 | 1.35e-4 |
|---|---|---:|---:|---:|---:|
| target SE = predicted SE (margin 1.5) | | 46.00 | 23.00 | 11.50 | 6.21 |
| **default (exact path)**, lane core-h at η_node 0.837 | **symmetry** | **2,552** | **9,698** | **38,792** | **146,517** |
| default, steady-state allocation on 4 amdq nodes (wall × 256) | symmetry | 2,390 | 8,370 | 32,942 | 123,963 |
| default, wall on 4 / 8 / 16 amdq nodes (steady model), h | symmetry | 9.3 / 5.3 / 2.7 | 32.7 / 16.4 / 8.2 | 129 / 64 / 33 | 484 / 243 / 122 |
| default, Expanse SU (× its cost-model ratio 0.939-0.943; same η_node assumed) | Expanse | 2,405 | 9,115 | 36,460 | 137,515 |
| **`dd+mp256`, route (b)** (gate 570574, profile model `18e50440…`), lane core-h | **symmetry** | **943** (kept) | **3,616** (kept) | **14,465** (kept) | **52,326** (re-optimized) |
| `dd+mp256`, steady-state allocation on 4 amdq nodes | symmetry | 1,029 | 3,122 | 12,264 | 44,477 |
| `dd+mp256`, wall on 4 / 8 / 16 amdq nodes (steady model), h | symmetry | 4.0 / 2.7 / 1.4 | 12.2 / 6.8 / 4.0 | 48 / 25 / 12 | 174 / 87 / 44 |
| stand-in projection (Stage 6, J-DES-5's strata, lane η 0.915): default / `dd+mp256` | symmetry | 1,702 / 638 | 5,740 / 2,241 | 22,961 / 8,963 | 74,573 / 29,328 |
| pilot ÷ stand-in: default / `dd+mp256` | | ×1.50 / ×1.48 | ×1.69 / ×1.61 | ×1.69 / ×1.61 | ×1.96 / ×1.78 |

Notes:
- **Route (b) is ×0.357-0.373 of the exact path.** It kept the exact allocation at the three loose targets and
  re-optimized at 1.35e-4.
- **`dd+mp256` is gated on symmetry only**, so it has no Expanse row. **`GMP_PREFIX` is not cleared for production.**
- **The steady model.** Each index runs at the pilot's in-index efficiency 0.990, and the only idle time is the
  schedule's own tail. At 5e-4 and tighter it allocates 0.85-0.87× the design's core-hours, because the design keeps
  the pilot's 3-node tail inside η_node (lane occupancy 0.845). The design figure is the conservative one, and it is
  what the freeze and the budget gate use.
- **8 or 16 nodes need a new H7/H11 window** with C63d and the user's go.

**Why the pilot costs ×1.5-2.0 the stand-in.** The per-graph continuous Neyman bound grows ×2.07, which is the product
of three factors:
- **η_node ×1.093:** 0.915 → 0.837, the pilot's tail;
- **cost ×1.036:** the pilot's measured seconds per point; free L8 ×1.062;
- **variance ×1.831:** free L8 ×1.81, free L7 ×1.57.

The variance factor is mostly the stand-in's estimator:
- the unbiased per-point sums Σσ_g² are not larger: free L8 ×0.95, free L7 ×0.85;
- J-SWEEP-2's σ_g came from 2 replicates (1 degree of freedom), which biases the Neyman weight Σσ_g√c_g low: E[σ̂]/σ =
  0.80 against 0.965 at the pilot's 8 replicates, a factor 1.46 in cost from that alone;
- the spiky L8 integrand does the rest.

The stand-in designs were also further above their own bound (×1.43-1.79, against the pilot's ×1.23-1.36). The 1.35e-4
column is the highest because of the power-of-two lattice.

**Variance and cost.**
- Free L7 carries 71% of the pilot's uniform-allocation variance at 2.4% of its cost, so the Neyman designs give it
  s = 4-256 at r = 128.
- In the 1e-3 design the cost shares are free L8 67%, free L7 18% and power L8 13%; the variance shares are 65%, 21%
  and 4.7%.

**Accounting of the pilot.**
- 226.87 core-h allocated: lanes 226.65 on 3 nodes for 0.89-1.34 h each, merge 0.16, plan 0.06.
- Busy time is 189.7 core-h, ×1.055 the plan's 179.9 estimate. The cost model under-estimates free L8 by 7-8%.
- The lanes ran at 0.99 in-index efficiency against the planner's 0.9, so the L8 index walls came in at ×0.961 of the
  estimate.

**Heavy tails (user decision).**
- C63d's L8 screen flags 9,886 of the 16,064 free L8 graphs and all 4,336 power L8 graphs. None is confirmed:
  confirmation needs 32,768 points per replicate, which bundles at 2.5e-4 and tighter give every free L8 graph.
- The power sector's P8 is 1.43, so R = 16 is advised. The bundles already give power L8 r ≥ 32.
- Details: the analysis README, section 3.

## Stage 5: the refined cost table (2026-10-05) [A-PERF-4; A-PERF-5 per site and profile; F10, F11]

**Superseded by "Pilot (2026-10-06)" above** (measured variances): the tables below keep the stand-in variances of
J-SWEEP-2 and are reference only.

Evidence: `benchmarks/symmetry_2026-10-c8/stage5/des5/` (J-DES-5, job 570114; README there), `benchmarks/symmetry_2026-10-c8/stage5/close/`
and `benchmarks/symmetry_2026-10-c8/stage5/pre6/` (the F11 fix and symmetry's own `dd+mp256` factors, Mac), then
**measured** on symmetry before Stage 6: `benchmarks/symmetry_2026-10-c8/pre6/` (the `dd+mp256` profile cost model,
job 570240; the F11-fixed and route-(b) freezes and their plans, job 570241) and `benchmarks/symmetry_2026-10-c8/pre6b/`
(the Stage-6 `design.py` of 77fab71: the same freezes and plans, job 570302). Scripts (Mac, seconds):
`des5/scripts/aperf4_table.py` (`aperf4.json`, `aperf4_table.md`), `close/aperf5_table.py` (`aperf5.json`,
`aperf5_table.md`), `stage5/pre6/pre6_tables.py` (`pre6_tables.json`, `pre6_tables.md`), `pre6/p6_tables.py`
(`p6_tables.json`, `p6_tables.md`) and `pre6b/p6b_tables.py` (`p6b_tables.json`, `p6b_tables.md`).

**What is measured and what is projected.** The base is the four test-only freezes of J-DES-5 (`design.py freeze
--test-only` at 1e-3, 5e-4, 2.5e-4 and 1.35e-4 of |C8| ≈ 4.6e4) on symmetry's J-SWEEP-2: every one of the 24,173 graphs
of both campaigns on the final default binary. **κ (seconds per point) is measured** for every graph on each site:
symmetry's `cost_models/gmp_symmetry_amd_c8.json` (`a1b6e5d2…`, EPYC 7543, GCC 11.4) and Expanse's
`cost_models/gmp_expanse_amd_c8.json` (`0e1ccfc9…`, EPYC 7742, GCC 13.3). **σ² is still projected**: it comes from the
sweep's 2 replicates × 512 points per graph, with the design margin 1.5, until the pilot measures it at 8 × 4,096.
Every row keeps the frozen allocation (counts × s, replicates r) and changes only the cost:
- the freezes' own core-hours use the sweep's η_node 0.306 (`accounting.py` on a 17-minute job with its plan, tail and
  merge inside the allocation); production runs in lanes, so the rows below use **J-SMK-4's measured lane η_node
  0.915** (one amdq node, 8 × 8 lanes, 1.4 h). Expanse's own lane campaigns (J-EXP-3/4, 4 minutes) are too short for
  an η_node, so Expanse is assumed to reach the same 0.915;
- Expanse re-costs each (sector, L) with its own κ per graph, weighted by the bundle's counts (×0.937–0.946 of
  symmetry overall; Expanse SU = core-hours on `compute`);
- each opt-in profile divides each stratum's core-hours by its measured speedup over the final default binary (F4 per
  sector at L8, F2's task seconds at L ≤ 7). On Expanse: the Stage-4c gates ("Stage 4c" above). On symmetry the
  approved `dd+mp256` row uses **symmetry's own gate of the exact `dd+mp256` build** (job 570210); the other profiles
  were not gated there, so their symmetry rows keep Expanse's factors (assumed; F10 below);
- R7 is A-FLAG-7's measured ratio, quoted.

**Projected core-hours (symmetry) and SU (Expanse) for one complete design at each relative target** (K = 1 is the
minimum batch count at every target; a design split into more batches costs the same in total). These are
**J-DES-5's freezes, made with the Stage-5 split rule**; F11 is fixed since (23540b2), which changes the 1e-3 design
only (the next table) and leaves the 5e-4, 2.5e-4 and 1.35e-4 designs identical:

| Numerics | Site | 1e-3 | 5e-4 | 2.5e-4 | 1.35e-4 |
|---|---|---:|---:|---:|---:|
| predicted SE of the freeze (target) | | 32.63 (46.00) | 22.61 (23.00) | 11.31 (11.50) | 6.08 (6.21) |
| default, the freeze as frozen (η_node 0.306 of the sweep) | symmetry | 11,832 | 17,484 | 69,934 | 228,776 |
| **default (exact path)** | **symmetry** | **3,963** | **5,856** | **23,423** | **76,623** |
| **default (exact path)** | **Expanse** | **3,748** | **5,487** | **21,949** | **72,125** |
| default, continuous Neyman bound (F11) | symmetry | 1,331 (frozen ×2.98) | 5,325 (frozen ×1.10) | 21,298 (frozen ×1.10) | 73,040 (frozen ×1.05) |
| default, continuous Neyman bound (F11) | Expanse | 1,252 | 5,007 | 20,026 | 68,676 |
| **`dd+mp256`: APPROVED after the pilot** (symmetry's own factors: gate 570210) | symmetry | 1,581 (×0.399) | 2,298 (×0.392) | 9,193 (×0.392) | 30,503 (×0.398) |
| **`dd+mp256`: APPROVED after the pilot** (measured as `dd+mp256+exp1`) | Expanse | 1,751 (×0.467) | 2,503 (×0.456) | 10,011 (×0.456) | 33,435 (×0.464) |
| `dd` (alone) | symmetry | 2,768 (×0.699) | 3,989 (×0.681) | 15,955 (×0.681) | 52,909 (×0.691) |
| `dd` (alone) | Expanse | 2,620 (×0.699) | 3,742 (×0.682) | 14,968 (×0.682) | 49,848 (×0.691) |
| `mp256` (alone) | symmetry | 2,991 (×0.755) | 4,471 (×0.763) | 17,883 (×0.763) | 58,270 (×0.760) |
| `mp256` (alone) | Expanse | 2,828 (×0.754) | 4,187 (×0.763) | 16,748 (×0.763) | 54,815 (×0.760) |
| `exp1`: not approved | symmetry | 3,931 (×0.992) | 5,810 (×0.992) | 23,241 (×0.992) | 76,023 (×0.992) |
| `exp1`: not approved | Expanse | 3,718 (×0.992) | 5,445 (×0.992) | 21,779 (×0.992) | 71,560 (×0.992) |
| R7 map (A-FLAG-7 ratio): not approved | symmetry | 3,262 (×0.823) | 5,126 (×0.875) | 20,505 (×0.875) | 66,081 (×0.862) |
| R7 map (A-FLAG-7 ratio): not approved | Expanse | 3,085 (×0.823) | 4,804 (×0.875) | 19,215 (×0.875) | 62,201 (×0.862) |

**The 1e-3 design with the F11 fix** (`pre6/pre6_tables.py`: `tools/design.py`'s `optimize()` on J-DES-5's frozen 1e-3
strata at the same target; free L8 r = 128 → 32, its primitives s = 1 → 8, and the target loop raises s at free L5,
free L7 and power L3-L5). The other three targets are unchanged:

| Numerics | Site | 1e-3, F11 fixed | Stage-5 rule (above) |
|---|---|---:|---:|
| predicted SE of the design (target 46.00) | | 44.21 | 32.63 |
| **default (exact path)** | **symmetry** | **1,738** (×1.31 the continuous bound 1,331) | 3,963 (×2.98) |
| **default (exact path)** | **Expanse** | **1,640** | 3,748 |
| **`dd+mp256`: APPROVED after the pilot** (symmetry's own factors: gate 570210) | symmetry | **678** (×0.390; measured: 669, below) | 1,581 (×0.399) |
| **`dd+mp256`: APPROVED after the pilot** (measured as `dd+mp256+exp1`) | Expanse | **742** (×0.452) | 1,751 (×0.467) |

**Measured on symmetry before Stage 6** (`benchmarks/symmetry_2026-10-c8/pre6/`, 2026-10-05; lane core-hours at
J-SMK-4's η_node 0.915). The freezes are `design.py freeze --test-only` on J-SWEEP-2 with the F11-fixed tool (job
570241); the `dd+mp256` costs come from the profile cost model `cost_models/gmp_symmetry_amd_c8_dd+mp256.json`
(`9b0dfec6…`), a J-SWEEP-2-shaped sweep of the gated build `d5df32ac…` on J-SWEEP-2's node (job 570240; speedup over
the exact model ×2.814 overall, free L8 ×2.754, power L8 ×2.965, free L7 ×2.778, power L7 ×3.448):

| Numerics, design | 1e-3 | 5e-4 | 2.5e-4 | 1.35e-4 |
|---|---:|---:|---:|---:|
| target SE | 46.00 | 23.00 | 11.50 | 6.21 |
| **default (exact path)**, F11-fixed freeze: SE | 44.21 | 22.61 | 11.31 | 6.08 |
| **default (exact path)**, F11-fixed freeze: symmetry | **1,738** | **5,856** | **23,423** | **76,623** |
| **`dd+mp256`**, the exact freeze's allocation re-costed with the profile model (same SE) | **669** (×0.385) | **2,309** (×0.394) | **9,236** (×0.394) | **30,067** (×0.392) |
| `dd+mp256`, route-(b) freeze as `design.py` makes it today: symmetry | 923 (×0.531) | 3,322 (×0.567) | 13,289 (×0.567) | 33,978 (×0.443) |
| `dd+mp256`, route-(b) freeze: SE | 35.83 | 18.53 | 9.26 | 5.91 |
| `dd+mp256`, continuous Neyman bound | 529 | 2,117 | 8,467 | 29,038 |
| **Stage-6 `design.py` (77fab71, F13 fixed), measured (570302)**: default (exact path), SE | 46.00 | 23.00 | 11.50 | 6.21 |
| **Stage-6 `design.py`, measured**: default (exact path), symmetry | **1,702** (×0.980) | **5,740** (×0.980) | **22,961** (×0.980) | **74,573** (×0.973) |
| Stage-6 `design.py`, measured: `dd+mp256` route (b), re-optimized branch (SE) | 638 (46.00) | 2,554 (23.00) | 10,215 (11.50) | 31,371 (6.21) |
| Stage-6 `design.py`, measured: `dd+mp256` route (b), exact design kept branch (SE) | 646 (46.00) | 2,241 (23.00) | 8,963 (11.50) | 29,328 (6.21) |
| **Stage-6 `design.py`, measured: `dd+mp256`, what a route-(b) freeze keeps** (branch) | **638** (×0.375; re-optimized) | **2,241** (×0.390; kept) | **8,963** (×0.390; kept) | **29,328** (×0.393; kept) |

- The F11-fixed exact freezes are the `stage5/pre6` projections exactly (1e-3), or byte-identical to J-DES-5's designs
  (5e-4, 2.5e-4, 1.35e-4).
- The re-costed exact allocation confirms the gate-factor projection (678 / 2,298 / 9,193 / 30,503) to 1.5%; it meets
  every target at the exact design's SE: **×0.385-0.394 of the exact path on symmetry** for the F11 greedy designs.
- **Finding F13** (`tools/design.py` `optimize()`; **fixed for the Stage-6 inspection**, `docs/DESIGN.md`, rule 4 and
  "Route (b)"): the 570241 route-(b) freezes re-optimized the allocation under the profile's costs and ended
  1.13-1.44× above the kept allocation, over-delivering the SE. Cause: the split starts 2.2-9.9% short of the target;
  at 1e-3, 5e-4 and 2.5e-4 the greedy loop doubles free L7, power L6 and power L5 and then free L8 (about half the
  cost, +48-56%) to close a remaining SE gap of 0.57% (1e-3) or 2.64% (5e-4, 2.5e-4); at 1.35e-4 it doubles free L6
  and then free L7 (+20%) to close 1.76%, and free L8 is not doubled (`benchmarks/symmetry_2026-10-c8/pre6/README.md`,
  "Finding F13"). The Stage-6 `design.py` searches the integer allocation from both split rules with a prune pass and
  a bounded lattice search, and a route-(b) freeze keeps the cheaper of the re-optimized design and the exact path's
  design re-costed under the profile: the last five rows, **measured on symmetry** (job 570302,
  `benchmarks/symmetry_2026-10-c8/pre6b/`: `design.py freeze --test-only` from the export of 77fab71 on J-SWEEP-2, the
  same arguments, profile model and gate record as 570241; every SE at its target). They equal the Mac recomputation
  from the committed strata (`tests/test_pipeline.py`, `jdes5_records`: r, s, branch and cost, relative difference
  ≤ 8e-15), and every bundle and every test-only plan holds every cap (the per-graph caps the Mac could not check;
  largest predicted task 60.0 s, at most 36,207 checkpoints and 4.44 × 10^6 tasks per campaign). The exact path is
  2.0-2.7% below the F11 greedy freezes (×0.980 / 0.980 / 0.980 / 0.973 in parentheses), route (b) 2.5-4.6% below the
  old exact allocation kept (669 / 2,309 / 9,236 / 30,067) and ×0.67-0.86 of 570241's route-(b) freezes.
- Expanse has no `dd+mp256` cost model yet; its rows remain the Stage-4c gate projection.

- **The default path** is the exact path of the final binary. At 1e-3 it agrees with Stage 4c's A-FLAG-7 base, which
  was frozen from R7's fresh exact sweep on Expanse (7,118 core-hours at its η_node 0.481, i.e. 3,742 at 0.915, against
  3,748 SU here).
- **`dd+mp256` is the approved production profile** (user check-in 2026-10-05, `docs/NUMERICS.md`, "User decision"):
  ×0.452–0.467 of the default on Expanse and ×0.390–0.399 on symmetry, at every target. On Expanse it was measured as
  the `dd+mp256+exp1` build; `exp1` changes no value and only the code layout (×1.007, the all-stub control ×1.005).
  The approved build's own J-FLAG gate
  passed on symmetry (2026-10-05, job 570210; `docs/NUMERICS.md`, "The `dd+mp256` J-FLAG gate on symmetry"): the same
  F1/F2 values as on Expanse, and F4 ×2.530 on symmetry (free ×2.485, power ×2.644) against ×2.168 on Expanse, with
  every L7 and L8 F2 ratio higher than Expanse's. The symmetry rows use symmetry's own factors from that gate
  (×0.390-0.399; with Expanse's factors they were 1,851 / 2,669 / 10,675 / 35,505, about 15% higher). The factors keep
  the exact path's allocation; measured with the profile cost model that allocation costs ×0.385-0.394 (the table
  above). With the 23540b2 `design.py` a route-(b) freeze re-optimized it and did worse (F13), not better as this
  paragraph said before the measurement; the Stage-6 `design.py` designs both and keeps the cheaper (×0.375-0.393 of
  its own exact path on J-DES-5's strata, the table above). **Production
  under `dd+mp256` from the exact pilot is route (b)** (implemented in 23540b2; `docs/DESIGN.md`, "Route (b)"): a sweep
  under the profile for its cost model (on symmetry: done, `cost_models/gmp_symmetry_amd_c8_dd+mp256.json`, job
  570240, re-measured in Stage-6 fix round 3 with the new profile build), then `design.py freeze --numerics dd+mp256`
  with the approval, that model and the gate record of the build (job 570373 was the fix-round-1 re-run of the 570210
  gate, the same F1/F2 values, F4 ×2.539, `benchmarks/symmetry_2026-10-c8/s6fix1/`; fix round 3 changed the build (Z4)
  and the gate ran again on it: job 570536, `benchmarks/symmetry_2026-10-c8/s6fix3/`; fix round 4 requires the gate's
  input set (W18), and the gate ran once more on the same build: job 570574, `benchmarks/symmetry_2026-10-c8/s6fix4/`,
  whose record `check_gate` requires now; the route-(b) bundles re-frozen with it, job 570579, have the same designs). **The re-measured model** (job 570538, the new build `a46f3060…`, <NODE>; sha256 `18e50440…`) is
  ×2.785 faster than the exact model overall (570240's: ×2.814), free L8 ×2.719 (×2.754), power L8 ×2.944 (×2.965),
  ×1.010 of the replaced model's summed seconds; the route-(b) re-freeze with it (job 570539) keeps the same choices
  and costs 639 / 2,251 / 9,002 / 29,473 lane core-hours at the four targets (570379: 638 / 2,241 / 8,963 / 29,328;
  +0.1-0.5%). Route (a), a `dd+mp256` pilot and freeze (about 80 core-hours), stays possible with the
  user's go: a key of `production.APPROVED_PROFILE_PILOTS` (empty, so a non-test profile pilot is refused) and a
  `--numerics-gate` record of the build at every non-test plan (Stage 6).
- `dd` and `mp256` alone are its two measured components, quoted for the record; `exp1` (inert) and R7 (needs a real
  pilot under its map) are **not approved** and stay off.
- **F11 (fixed in 23540b2): the first table's 1e-3 column is too high.** The Stage-5 `design.py` gave a (sector, L) the
  replicates of its largest stratum multiplier; at 1e-3 the free L8 primitives' multiplier set r = 128 for the whole
  free L8 group, so that freeze over-delivers (SE 32.6 against the target 46) at 2.98× the continuous Neyman cost. The
  fixed tool takes r from the group's smallest multiplier (`docs/DESIGN.md`, rule 4 and "F11"): 1,738 lane core-hours
  on symmetry for 1e-3 (SE 44.2), 1.31× the continuous bound. The other targets are within 1.10× of the continuous
  bound and unchanged. The `dd`, `mp256`, `exp1` and R7 rows (none approved) are quoted for the Stage-5 designs only.
- The core-hours scale with the pilot's σ² (every row, every site); the profile and site ratios move only through the
  strata's cost shares. L8 is 63–93% of the cost (`aperf4.json`, `l8_share_literal`).

**A-PERF-5 per (sector, L) and site: the final binary over the Stage-3 baseline** (kernel seconds per point summed
over the stratum's graphs, equal points per graph; Expanse: J-SWEEP-2E against J-SWEEP-1, every graph; symmetry: the
same node, J-SWEEP-3's stratified subset of 2,203 keys, final binary against the symmetry Stage-3 baseline built from
`c8-stage3`, job 570098). A profile over Stage 3 is the default's factor times the profile's factor over the final
binary (two measurements multiplied: an estimate): on Expanse the Stage-4c gates' factors; on symmetry `dd+mp256`
uses its own gate's factors (570210; `pre6/pre6_tables.json`, `aperf5_dd_mp256_symmetry`) and, measured later, the profile
cost model's speedup over the exact model (job 570240, every graph; `benchmarks/symmetry_2026-10-c8/pre6/`):

| Sector, L | default: Expanse | default: symmetry | `dd+mp256` (approved): Expanse | `dd+mp256`: symmetry (gate 570210 k) | `dd+mp256`: symmetry (profile sweep 570240) | `dd`: Expanse | `mp256`: Expanse | `exp1` (not approved): Expanse |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| free L3 | ×1.022 | ×0.897 | ×0.98 | ×0.80 | ×1.07 | ×1.06 | ×0.96 | ×0.94 |
| free L4 | ×1.011 | ×0.944 | ×1.03 | ×1.03 | ×0.94 | ×1.05 | ×1.00 | ×1.01 |
| free L5 | ×0.994 | ×1.063 | ×1.02 | ×1.15 | ×1.05 | ×1.02 | ×0.99 | ×0.99 |
| free L6 | ×1.013 | ×1.011 | ×1.03 | ×1.03 | ×1.06 | ×1.04 | ×1.04 | ×1.00 |
| free L7 | ×1.413 | ×1.125 | ×3.35 | ×3.07 | ×3.12 | ×2.24 | ×1.80 | ×1.42 |
| free L8 | ×1.444 | ×1.171 | ×3.05 | ×2.91 | ×3.22 | ×2.08 | ×1.89 | ×1.46 |
| power L3 | ×1.017 | ×1.057 | ×1.19 | ×1.30 | ×1.18 | ×1.13 | ×1.03 | ×1.02 |
| power L4 | ×1.012 | ×1.103 | ×1.57 | ×1.46 | ×1.62 | ×1.49 | ×1.04 | ×0.97 |
| power L5 | ×1.386 | ×1.016 | ×3.27 | ×2.43 | ×2.39 | ×2.30 | ×1.79 | ×1.39 |
| power L6 | ×1.195 | ×1.161 | ×3.48 | ×3.67 | ×3.82 | ×1.80 | ×1.78 | ×1.21 |
| power L7 | ×1.283 | ×1.121 | ×3.85 | ×3.75 | ×3.87 | ×1.77 | ×2.12 | ×1.29 |
| power L8 | ×1.261 | ×1.157 | ×2.91 | ×3.06 | ×3.43 | ×1.61 | ×1.96 | ×1.26 |

**Speedups are site-dependent (F10); quote them with the site.** In kernel seconds per point, the final default binary
is **×1.390 faster than Stage 3 on Expanse** (GCC 13.3, EPYC 7742; free L8 ×1.444, power L8 ×1.261) and **×1.157 on
symmetry** (GCC 11.4, EPYC 7543; free L8 ×1.171, power L8 ×1.157; ×1.197 in node throughput on the P4 L8 workload,
job 570099). Stage 4b's **×1.646** is a third measure: Expanse's L8 sweep sample in lane-thread seconds with graph
loading, so it includes R5a's load-time gain (×1.154), which the kernel seconds above exclude. R3a's inline binary128
arithmetic gains less under GCC 11.4 than under GCC 13.3; planning is unaffected, because each site's cost model was
measured with its own final binary.

**`tools/calibration.json` (closed in the G5 fix round).** The close-out recorded it as still holding C7(2)'s rows;
the G5 fix commit 86e15f4 replaced it with symmetry's J-SWEEP-2 rows (`d85dd7c0…`) and pinned Expanse's J-SWEEP-2E
rows as `cost_models/calibration_expanse_amd_c8.json` (see "The active calibration" under J-SWEEP-1 above). The
calibration is read only by a plan without `--cost-model`; every Stage-5 plan, the pilots and production plans pass a
measured cost model, so the cost table here is unchanged by it.

## Stage 4b integration: J-OPT gates and the A-PERF-2 decisions (2026-10-04) [A-PERF-2; A-RPL-1/2/3/6/7 per step]

The four development branches were merged into `c8` in plan order, each as a merge commit: 138d486 (`opt-r5`, R5a and
R5b), d46e736 (`opt-r3a`), bc0bedc (`opt-r4a`) and 7b9aa9c (`opt-r4f`). The job scripts are d0f0e05. Then each
cumulative step was gated on Expanse and timed on one node. The evidence is in
`benchmarks/expanse_2026-10-c8/stage4b/integration/` (README there). `scripts/summarize_int.py` recomputes every number
below from the copied records into `int_summary.json`.

**Outcome.**
- R5a, R5b and R3a are kept.
- R4a is reverted: its code only, in ea59445. Its evidence and docs stay as the record.
- R4f is kept as the opt-in `GMP_PREFIX` knob. The default build does not use it.
- R3c is not attempted (IPC 3.04).
- Every step is exact against the Stage-3 baseline.
- The default path (+R5 +R3a) is ×1.646 faster than Stage 3 on Expanse's L8 sweep sample (lane-thread seconds with
  loading; per site and in kernel seconds: "Stage 5: the refined cost table", F10). With the opt-in zen2 GMP it is ×1.731.

### The cumulative binaries

Expanse, Spack GCC 13.3.0, Boost 1.77 headers, `-O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math`, portable (no
`-march`). Each step was built in the `git archive` export of its commit (`setup/export_check_<sha12>.json`: 5,615,
5,820, 5,927 and 6,183 files equal). The Stage-3 baseline binaries were byte-copied into each export's `bin/baseline/`,
with their hashes checked.

| Name | What | Commit | `c8d2_decimal` | `c8d2_gmp` |
|---|---|---|---|---|
| B0 | Stage 3 (tag `c8-stage3`) | b4273c5 | `3dbd51bb…` | `5c5328af…` |
| B1 | +R5 (R5a; R5b is tools only) | 138d486 | `b36bf334…` | `f4ad369c…` |
| B2 | +R3a | d46e736 | `99a51c1d…` | `1d2a2181…` |
| B3 | +R4a | bc0bedc | `99a51c1d…` | `8b296ddb…` |
| (S4) | +R4f merge and the scripts, default build | d0f0e05 | `99a51c1d…` | `8b296ddb…` (byte-identical to B3) |
| B2f | B2's source with `GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-zen2` (R4f without R4a) | d46e736 `src/`, d0f0e05 Makefile | B2's | `aa84cd45…` |
| B4 | B3's source with the zen2 GMP (R4f on R4a) | d0f0e05 | B3's | `accb36ca…` |

The zen2 GMP is R4f's build: GMP 6.2.1, `--host=zen2-pc-linux-gnu`, `make check` 197/197, `libgmp.so.10.4.1`
sha256 `4267ffeb…`. For both zen2 workers, ldd resolves libgmp to that prefix through the DT_RPATH, ahead of
`env_expanse.sh`'s `LD_LIBRARY_PATH`. A default build of B2's `src/` with d0f0e05's Makefile is byte-identical to B2
(`1d2a2181…`), so the R4f knob changes nothing when unset.

### Exact gates per step (all passed)

| Step | validate.py default parts: A-RPL-1/2/3 subset and the rest (build job) | G-L8SELF, A-RPL-7 (gate job) | Thread identity, A-RPL-6 (gate job) | Replay subset, A-RPL-1/2/3 (gate job) |
|---|---|---|---|---|
| B1 +R5 | passed (54669703) | exact (54669707) | identical (54669707) | in the default parts |
| B2 +R3a | passed (54669704) | exact (54669707) | identical (54669707) | in the default parts |
| B3 +R4a | passed (54669705) | exact (54669708) | identical (54669708) | in the default parts |
| S4 default | passed (54669706), byte-identical to B3 | as B3 | as B3 | in the default parts |
| B2f zen2 | — | exact (54669708) | identical (54669708) | passed (54669708, 22 tests) |
| B4 zen2 | — | exact (54669708) | identical (54669708) | passed (54669708, 22 tests) |

**What each gate ran.**
- **G-L8SELF** is `validate.py --l8self bin/baseline`: the L8 sweep sample of A-RPL-7, 2 × 512 points per graph, both
  backends, against the Stage-3 B0. It covers 1,600 free and 400 power graphs. Each backend gives 3,200 + 800 rows,
  with 762,395 + 359,972 binary128 evaluations and 114,648 + 99,884 MP points. Every scientific field is exact, in every
  step.
- **Thread identity** is `tests/thread_identity.py`: an L8 free block and an L8 power block of 64 tasks × 256 points,
  run at 1, 8, 16 and 64 threads and as 8 lanes × 8 threads, on both backends. Every run is identical.
- **The default parts** are describe, 28 refusals, the replay subset of G-REF/G-C7/G-JET on 117 kernels, chunk and
  layout invariance, the inspector against the order-trace build, class B and the diagnostic builds.

### Speed (A-PERF-2): Expanse job 54669709, one exclusive node (<NODE>, 2 × EPYC 7742)

**Workload.** The workload is the L8 sweep sample above, run on the gmp backend with G-L8SELF's nets, seed 7738251, rate .8 and layout 0, so its rows
are G-L8SELF's. It runs in the sweep's shape on Expanse:
- 16 lanes × 8 threads (the R5b default and P4's best), each a NUMA-aligned set of cores.
- The 2,000 graphs are split over the lanes by LPT on the J-SWEEP-1 cost model.
- Each lane runs its free graphs and then its power graphs as native blocks of at most 256 tasks: about 100 free and
  25 power graphs per lane.
- The lane assignment is the same in every run.

**Runs.** Six binaries, three repeats each. The order is rotated by two places per repeat, so every binary runs early,
in the middle and late.

**Metric.** The gate's metric, fixed before the run, is the lane-thread seconds: 8 × the sum of the native blocks' wall
times, from process start to exit, so start-up, graph loading, integration and output are included. The rows digest
`17384d2a…` is the same in all 18 runs.

| Binary | Lane-thread s (median) | free | power | Node wall s | Load share | Busy | vs B0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 Stage 3 | 1994.8 | 1454.0 | 540.8 | 15.88 | 16.42% | 0.804 | 1.000 |
| B1 +R5 | 1728.7 | 1237.6 | 491.8 | 13.83 | 2.98% | 0.931 | 1.154 |
| B2 +R3a | 1212.1 | 845.0 | 367.1 | 9.77 | 4.28% | 0.906 | **1.646** |
| B3 +R4a | 1201.0 | 837.9 | 363.2 | 9.67 | 4.32% | 0.907 | 1.661 |
| B4 +R4f on B3 | 1149.4 | 807.9 | 341.4 | 9.22 | 4.48% | 0.904 | 1.736 |
| B2f +R4f on B2 | 1152.2 | 808.5 | 343.9 | 9.26 | 4.48% | 0.905 | **1.731** |

The spread of the three repeats (max − min over the median) is 0.7% for B0, 0.1% for B1 and B2, 0.3% for B2f,
0.4% for B3 and 0.5% for B4.

| Step | From → to | Speedup | free L8 | power L8 | Node wall | ≥ 1.03 |
|---|---|---:|---:|---:|---:|---|
| R5a | B0 → B1 | **1.1539** | 1.1749 | 1.0997 | 1.1485 | yes |
| R3a | B1 → B2 | **1.4262** | 1.4647 | 1.3397 | 1.4157 | yes |
| R4a | B2 → B3 | **1.0093** | 1.0085 | 1.0106 | 1.0099 | **no** |
| R4f on R4a | B3 → B4 | 1.0449 | 1.0371 | 1.0638 | 1.0494 | yes |
| R4f without R4a | B2 → B2f | **1.0520** | 1.0451 | 1.0675 | 1.0552 | yes |
| R4a on R4f | B2f → B4 | 1.0024 | 1.0007 | 1.0072 | 1.0044 | no |

**IPC (the R3c rule).** perf stat ran on heavy_free_L8 at 64 threads (OMP_WAIT_POLICY=passive), with B2 on socket 0 and
B3 on socket 1 at the same time:
- IPC is 3.04 (B2) and 3.05 (B3), against 2.71 for Stage 3 (P2).
- The two counters were multiplexed, so the values are scaled estimates.
- Integration took 110.6 s and 106.2 s.
- The rows equal Stage-4a P1's (`92eec91c…`).

### Decisions

| Item | Rule | Measured | Decision |
|---|---|---|---|
| **R5a** parallel graph loading | A-PERF-2: exact and ≥ 3% on the L8 sweep sample | ×1.154 (free ×1.175, power ×1.100). The load share of the sample's blocks falls from 16.4% to 3.0%. Exact in every gate | **Kept.** The gain is mostly load time, which is large in 512-point sweeps. At the production shape it is smaller: in development (P4 workload, about 10 s tasks, 16 × 8) the load share went from 1.349% to 0.203% and throughput rose by about 1.4% (job 54666183). The estimate for 60 s tasks is about 0.04% (not measured). The plan's "< 0.1%" holds only at production task sizes |
| **R5b** default lanes | Scheduling only (A-RPL-6); keep if it matches P4 | Defaults: 16 × 8 on Expanse and 8 × 8 on symmetry, P4's best shapes (lane probe 54666372). At 16 × 8 here, busy fraction 0.804 (B0) → 0.931 (B1); in development P4, 0.950 → 0.966 | **Kept** |
| **R3a** inline binary128 add/sub/mul | A-PERF-2 | ×1.426 (free ×1.465, power ×1.340). Exact in every gate; R3a's differential test, at least 2^32 pairs per operation, ran in development (54669012) | **Kept** |
| **R3c** lock-step binary128 points | Attempt only if IPC < 1.5 on the R3a binary | IPC 3.04 | **Not attempted** |
| **R4a** MP tier without temporaries | A-PERF-2 | ×1.0093 (free ×1.0085, power ×1.0106); ×1.0024 on top of R4f. Exact in every gate | **Reverted** (code only, ea59445): `src/` is again d46e736's |
| **R4f** zen2 GMP 6.2.1 behind `GMP_PREFIX` (host addition) | A-PERF-2 and the same exact gates | ×1.0520 over the kept default B2 (free ×1.045, power ×1.068); ×1.0449 over B3. Exact (G-L8SELF, thread identity, replay subset) | **Kept, as the opt-in knob.** The default build is unchanged. Each site needs its own `GMP_PREFIX` build, checked by `make check` and the exact gates there. On Expanse the zen2 build passed G-L8SELF, thread identity and the replay subset of A-RPL-1/2/3 here, and in Stage 5 the full J-VAL-2, G-BK8 and forced tiers (A-RPL-4/5), each record equal to the default build's (job 54676895). **NOT cleared for production** (Y1, Stage-6 fix round 2): that job's forced tiers, point checks and class-B builds linked Spack's libgmp, not the zen2 one, and are re-run with the bound tools together with the A-EXP-3 J-EXP-1 rerun. Symmetry is not built or gated |
| R6, R4e | Stage-4a decisions | — | Not attempted (R6 is bounded at about 0.8% overall; R4e measures 0%) |

**The final default binary** is +R5 +R3a, with d46e736's `src/`.

### Final candidate e7ef98d (Expanse jobs 54672108 and 54672109), all passed

- **Build (54672108).** The build was made in the export of e7ef98d (6,317 files equal to `git archive`).
  - `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…` are byte-identical to B2. The speed and gate
    numbers of B2 above are therefore this binary's.
  - The `GMP_PREFIX=zen2` worker `aa84cd45…` is byte-identical to B2f.
  - `validate.py` default parts passed: describe, 28 refusals, the A-RPL-1/2/3 replay subset, invariance, the
    inspector, class B and the diagnostic builds.
- **Gates (54672109).**
  - Default build:
    - G-L8SELF is exact against Stage 3 on both backends (4,000 rows each).
    - Thread identity is identical at 1, 8, 16 and 64 threads and in 8 lanes × 8 threads, on both backends.
    - `tests/quad_differential.py` passed at 128 threads. It took the kernel's operand ranges from the fixture blocks
      and ran 2^32 random pairs per operation, with 4,286,346,880 / 4,286,350,062 / 3,849,357,005 on the fast path for
      add / sub / mul. It also ran the edge lists (901,761 / 901,761 / 1,350,672 pairs), the injection self-test
      (detected) and an ASan+UBSan run, with 0 mismatches everywhere.
  - zen2 worker: G-L8SELF exact, thread identity identical, and the replay subset passed (22 tests).
- **Still owed then:** the full J-VAL-2 (`validate.py --full`) and J-VAL-3 reruns on the final binary. They ran and
  passed in G4b (jobs 54672150–52; "Stage 4b: default-path optimizations" above).

**Per (sector, L8), default path against Stage 3 on the L8 sweep sample (A-PERF-5).** The free sector is ×1.721 and
the power sector ×1.473; with the opt-in zen2 GMP they are ×1.798 and ×1.573. The final J-SWEEP-2 cost model will give
the per-graph figures.

**Cost.** The step jobs used 64.6 SU (`stage4b/integration/admission/sacct_steps.txt`) and the final candidate 21.1 SU
(`sacct_final.txt`): 85.8 SU in all.

## Stage 4b development: R5a and R5b (branch `opt-r5`, 2026-10-04)

**Integration outcome:** R5a and R5b are kept (R5a ×1.154 on the L8 sweep sample; see "Stage 4b integration" above).

Development measurements on Expanse (site deviation U1) for the first two Stage-4b items. They are not the plan's
J-OPT gate: A-PERF-2's median of 3 runs on the L8 sweep sample is still owed. Evidence:
`benchmarks/expanse_2026-10-c8/stage4b/dev_r5/`. The code under test is commit 2c8b28f (export `2c8b28f46538`, equal
to `git archive`).

**R5a, parallel graph loading** (`src/c8d2_integrate.cpp`). The block's graphs load in `#pragma omp parallel for
schedule(dynamic,1)` over the graph ids in ascending order, one graph per iteration, into a pre-sized
`std::vector<Graph>`. The lane's pinned threads therefore first-touch the graphs they load. Loading is pure I/O and
parsing, and no value depends on the thread. Each slot keeps its own error. After the loop the lowest graph id's error
is thrown, which is the error the serial loop threw first, whatever the timing. `loaded` maps each id to its slot. The
rest of the worker is unchanged, including the task order and the order-trace output. The release binaries are new:
`c8d2_decimal` `b36bf334…` and `c8d2_gmp` `f4ad369c…` (Spack GCC 13.3, same flags).

| Check (Expanse) | Job | Result |
|---|---|---|
| G-L8SELF, the A-RPL-7 machinery: full L8 sample (2,000 kernels, 2 × 512 points, both backends) against the Stage-3 baseline `3dbd51bb…`/`5c5328af…` | 54666183 | **Exact** in every scientific field. 4,000 rows per backend; 1,122,367 binary128 and 214,532 MP points per backend, as in Stage 3 |
| A-RPL-6 thread identity (`tests/thread_identity.py`): L8 free and power blocks of 64 tasks × 256 points at 1, 8, 16 and 64 threads, and as 8 lanes × 8 threads | 54666183 | **Identical**, both backends |
| P4 rows: all 4,018 `p4_L8` tasks at 16x8, R5a worker against the baseline worker | 54666183 | Rows digest `16d6ff3d…` in both runs, equal to Stage 4a's P4 (job 54661719) |
| `tests/validate.py` default parts: describe, the 28 refusals, the replay subset of A-RPL-1/2/3 (117 kernels, G-REF, G-C7, G-JET), invariance (chunks and layouts), inspector with the order-trace build, class B, diagnostic builds | 54666182 | All passed |
| First error (`dev_r5/scripts/r5a_first_error.py`): 8 free L4 kernels; truncated, missing and wrong-id G-files at two or three ids per case; 5 cases × 2 backends; the candidate at 1, 2, 4, 8 and 16 threads, 5 repeats each | 54666182 | In the 200 runs of the 4 bad cases: exit 2, no output, and stderr byte-identical to the serial baseline's. In the 50 runs of the valid case: rows identical to the baseline's |

**R5a load share at the P4 default shape** (job 54666183, one exclusive node <NODE>; `tools/benchmark.py
--lane-shapes 16x8` on the whole `p4_L8` workload; the baseline worker first, then the R5a worker; one run each):

| | Baseline (`5c5328af…`) | R5a (`f4ad369c…`) |
|---|---:|---:|
| Load share of node time | 1.349% | **0.203%** |
| Load seconds per block (32 blocks): median / max | 2.474 / 4.036 s | 0.365 / 0.594 s |
| Staging share | 0.352% (cold page cache) | 0.075% (warm) |
| Throughput (cost-model s per node-second) | 114.83 | 116.83 (×1.017) |
| Busy fraction / OpenMP efficiency | 0.950 / 0.983 | 0.966 / 0.983 |
| Wall | 368.0 s | 361.7 s |
| Peak RSS per lane (Σ over 16 lanes) | 0.679 GiB (10.66 GiB) | 0.707 GiB (11.12 GiB) |
| Lowest per-lane NUMA locality | 0.9925 | 0.9930 |

- Loading is 6.8 times faster per block at 8 threads. Its share of node time drops from 1.35% to 0.20%. The plan's
  "< 0.1%" is not reached with P4's tasks of about 11 s. Production's 60-second tasks carry about 5.5 times the
  integration per loaded graph, so the share there should be near 0.04% (an estimate, not measured).
- The throughput gain of 1.7% includes the staging difference of 0.28 points. That difference comes from the run
  order: the second run read the packs from a warm page cache. So R5a's own gain is about 1.4% here, which is below
  A-PERF-2's 3% bar, as Stage 4a predicted (≤ 1.1–1.3% at P4-size tasks). The gate is A-PERF-2 on the L8 sweep sample,
  whose 512-point tasks load relatively more.
- Peak RSS per lane rises by 4% (29 MB), from the per-thread malloc arenas of the loading threads.

**R5b, scheduling defaults** (`tools/lanes.py`, `tools/sweep.py`).
- **Lanes.** With `C8_LANES` unset, an AMD node's NUMA nodes are each split into the fewest equal lanes of at most
  the plan's `--threads` cores. One rule gives the best P4 shape on both sites: 8 × 8 on symmetry (NUMA nodes of 8
  cores) and 16 × 8 on Expanse compute (NUMA nodes of 16 cores; `C8_LANES=numa` there stays 8 × 16, −1.0% in P4).
  Explicit `numa`, `socket` and `n` are unchanged, Intel nodes keep one lane per socket, drill mode is unchanged, and
  `checkpoint_tasks` still caps the lane width. `worker_lanes()` holds the worker's lane decision, and the worker log
  names the shape. The sweep's default process slots follow the same rule at its `--threads`. Before this change,
  `--threads 8` on Expanse left half of each NUMA node idle.
- **Plan.** The defaults are unchanged and now tested (`tests/unit_orchestration.py`, test `p4_defaults`): `--threads
  8`, `--checkpoint-tasks` max(16 × 8, 256) = 256 (the P4 block), 60 s tasks bounded by 120 s (`--task-seconds`,
  `--max-task-seconds`), and indices of `--index-hours` 1.5 h of the lane width. Lane scans were already of bounded
  cost (`LaneView`, test `scan`).
- **On the real topology.** `dev_r5/scripts/r5b_lanes_probe.py` (job 54666372, Expanse <NODE>, 8 NUMA nodes of 16
  cores) reads the real sysfs, and every lane lies inside one NUMA node. With `C8_LANES` unset the worker makes 16 × 8
  at `--threads 8` and 8 × 16 at `--threads 16`. `numa` gives 8 × 16 and `16` gives 16 × 8. The sweep's slots are
  16 × 8 and 8 × 16 at `--threads` 8 and 16.

## Stage 4b R3a: inline binary128 add, sub and mul (2026-10-04; branch `opt-r3a`, development)

**Integration outcome:** R3a is kept (×1.426 on the L8 sweep sample; IPC 3.04, so R3c is not attempted; see "Stage 4b integration" above).

Development evidence for R3a ("Performance plan", Stage 4b table). The A-PERF-2 gate itself (A-RPL-1/2/3/6/7 exact and
the median-of-3 speed on the L8 sweep sample) belongs to the integration step. Evidence:
`benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/` (`scripts/summarize_r3a.py` recomputes every number below into
`r3a_summary.json`).

**Change.** `src/quadfast.hpp` (new) gives libgcc's `__addtf3`, `__subtf3` and `__multf3` results bit for bit in
round-to-nearest-even, as inline integer code on 64-bit words, for normal operands with a normal, finite result.
Everything else (a zero, subnormal, infinite or NaN operand, an exact zero sum, underflow, overflow) is computed by
libgcc itself through out-of-line calls on the same operands. `calculate_shared<Q>` uses it for every binary128 `+`,
`-` and `*`, in the same order (the sums S, the products, the segment sums, the numerators and their error estimate,
the term sums, and the shift path's subtraction). Division, conversions, comparisons and `expq` are unchanged. The
dispatch on T is per statement with `if constexpr`, so the MP instantiations contain exactly the original statements.
`numerical_change: false`.

**Method.** Effective addition, which is nearly all of the kernel's work, keeps the larger significand in place and
the smaller one's shifted-out bits in a separate 64-bit word. That word holds the exact fraction of an ulp below the
sum, to a sticky bit, because the larger operand has no bits there. Nearest-even then needs one comparison, and no
double-word shift sits on the dependent chain. Effective subtraction and multiplication use a 13-work-bit working value
with a sticky bit. The operations and their fallbacks take and return bit patterns (`unsigned __int128`), so no operand
passes through an SSE register. A first version with 13 work bits for the addition too (908bd9d) was exact but slower,
and is superseded (table below).

**Proof (A-RPL-5's differential part): `tests/quad_differential.py`, final version, job 54669012.**
- Kernel ranges (`tests/quad_ranges.cpp`): 256 points on each of 16 graphs of six fixture blocks (heavy and random L8,
  random L7), through kernel.hpp's own `sample()`.
  - The binary128 add/sub operands span 2^-591 to 2^386, the mul operands 2^-538 to 2^0.
  - 99.7–99.8% of the kernel's additions take the fast path; the rest are the `0 + x` starts of the accumulators.
  - 0.15–0.2% of the additions are effective subtractions.
  - Every multiplication takes the fast path.
  - The shift-path subtraction did not occur in these samples (every sampled point was direct).
- Random pairs: 2^32 = 4,294,967,296 per operation, in four streams of 2^30 each:
  - the kernel window (the observed exponent range widened by 2^±512);
  - the whole normal range;
  - cancellation (add, sub) or exact product ties (mul);
  - uniform 128-bit patterns.

  The fast path took 4,286,346,880 (add), 4,286,350,062 (sub) and 3,849,357,005 (mul) of them. **Mismatches: 0.**
- Edge lists: 901,761 pairs each for add and sub, and 1,350,672 for mul. **Mismatches: 0.** They cover:
  - specials: all ordered pairs of 100 values (signed zeros, subnormals, extreme normals, 1 ± ulp, inf, quiet and
    signaling NaNs);
  - every alignment distance 0..130 (plus larger ones) with an exact half, half ± sticky, a lone low bit, all ones and
    a power of two, against even, odd, all-ones and power-of-two larger significands;
  - cancellation in the low k bits, k = 0..112, including exact zeros;
  - carries;
  - the subnormal and overflow boundaries, including max-normal ties;
  - x − x;
  - product ties at every s = 0..111, mul results at exponents −3..3 and 0x7FFB..0x8002, and mul rounding carries.
- Injection self-test: flipping the last bit of every 4099th result of 2^22 random pairs gives 1,020 mismatches per
  operation, so the comparison bites.
- ASan+UBSan build: 4,194,304 pairs per operation plus every edge list. 0 mismatches, no report.
- Wall time: 57 s on 32 Expanse cores.

**Exactness against the Stage-3 baseline** (`c8d2_decimal` `3dbd51bb…`, `c8d2_gmp` `5c5328af…`).

| Check | Final version (add273b: decimal `156c09a9…`, gmp `dec065ee…`) | First version (908bd9d) |
|---|---|---|
| G-L8SELF (`validate.py --l8self`, 2,000 L8 kernels, 2 × 512 points, both backends) | exact in every scientific field: free 3,200 rows (762,395 binary128 / 114,648 MP evaluations), power 800 rows (359,972 / 99,884), each backend | the same, exact |
| Replay subset (`validate.py --only replay`: G-REF, G-C7, G-JET on the J-VAL-1 subset) | passed | passed |
| heavy_free_L8 and heavy_power_L8 (4,194,304 points each, gmp), 3 baseline + 3 R3a runs each | all rows identical (digests `92eec91c…`, `c9b8e059…`) | identical, same digests |

**Speed** (`r3a_speed.py`, one exclusive Expanse node with 2 × EPYC 7742; 64 threads pinned per socket; free on socket
0 and power on socket 1 at the same time; baseline and R3a alternating; medians of 3 integration times).

| Block | Final (54669014, <NODE>): baseline → R3a | Speed-up | First version (54666586, <NODE>) | Speed-up |
|---|---|---:|---|---:|
| heavy_free_L8 | 158.61 s → 110.03 s | **×1.442** (wall ×1.428) | 154.20 s → 126.35 s | ×1.220 |
| heavy_power_L8 | 148.55 s → 111.64 s | **×1.331** (wall ×1.322) | 148.04 s → 125.07 s | ×1.184 |

- The binary128 tier, from the R3a tier-timer build, run alongside: 743.5 µs per call on heavy free L8 and 532.7 µs on
  heavy power L8. The Stage-3 baseline took 1,609 and 1,173 µs (P1), so the tier is ×2.16 and ×2.20 faster.
- Its share of thread time falls to 37.0% (free) and 29.4% (power). The MP tier is now 50.4% and 56.0%, the largest.
- Microbenchmark (`--bench`, one core): a dependent chain of additions takes 6.04 ns per add, against 22.03 ns for
  libgcc (×3.6). Independent multiplications take 17.3 against 24.1 ns.

**IPC (the R3c rule).** perf stat (cycles, instructions; OMP_WAIT_POLICY=passive, as P2) on heavy_free_L8 at 64
threads, same node: R3a **3.08**, baseline 2.71. P2 measured 2.71 for the baseline as well. The tier stays
throughput-bound (IPC ≥ 1.5), so **R3c is not attempted**. The two counters were multiplexed at 50% each, so the
counts are scaled.

**Code identity of the MP and long-double paths** (`asm_compare.py`, the worker's translation unit compiled to
assembly from the 4a export's `src/` and from R3a's, function by function, labels renumbered and constants compared by
content).
- With the shipped flags, besides `calculate_shared<__float128>` and the three new libgcc fallbacks:
  - gmp: 115 of the baseline's 122 functions are identical. The others are `calculate_shared<gmp_float<350>>`,
    `main`, `main._omp_fn.0`, a `std::map` erase, and two `wrapexcept::clone` whose exception tables merely swap their
    section names;
  - decimal: 113 of 130 are identical. The others are some `cpp_dec_float` members, `eval_exp`, `hyp0F0`, two
    `stable_sort` helpers and `main`, and two small helpers are cloned or inlined differently.
- The cause is GCC's unit-wide inlining budget (`inline-unit-growth`), which reacts to the larger binary128 function.
  The development probe (`scripts/r3a_ipa_probe.slurm`, on the final source; experiment only) shows it. With that
  budget lifted on both sides, the gmp unit differs only in `calculate_shared<__float128>` and the two section-name
  artifacts. The decimal unit still differs in `pow2` and two recursive `stable_sort` helpers.
- The source of every MP and long-double statement is unchanged, and the differences are inlining and register
  choices.
- A first attempt dispatched through wrapper overloads for every T. It changed MP inlining more (e.g. `eval_add`
  outlined), and the `if constexpr` form replaced it.
- Strict machine-code identity of those paths is therefore not attainable through source changes alone. Their
  numerics are settled by the exact gates above. A-RPL-1/2/3/6/7 on the final binary are the integration step's.

**Development history** (shared node, the first 32 tasks of heavy_free_L8 at 16 threads; times in the same job):

| Version | Add chain (ns) | Slice: baseline / first version / candidate (s) |
|---|---:|---|
| first fast path (3 work bits, 128-bit variable shifts) | 15.8 | not run |
| first version (908bd9d: 13 work bits, sticky from the trailing-zero count) | 10.8–11.0 | 74.1 / 60.5 / – |
| word-based addition, words through `memcpy` | 15.9 | 74.1 / 60.5 / 64.1 (slower: store-forwarding stalls) |
| the same through `unsigned __int128` | 6.6 | 76.2 / 64.1 / 53.7 |
| **final (add273b)** | 6.0–6.1 | 72.2 / 59.5 / 50.1 |
| final + bit-pattern segment accumulator (rejected, no gain) | 6.2 | 77.8 / 66.9 / 55.5 |

Every slice run gave identical rows. Every development differential run (2^26–2^28 pairs per operation plus the edge
lists) had 0 mismatches.

**Cost.** 94.5 SU on Expanse, in 16 jobs: two development rounds of build, validation and speed, one profile, and nine
development jobs. Accounting is in `benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/admission/sacct_r3a.txt`.

## Stage 4b R4f: GMP 6.2.1 built for the node (development probe, 2026-10-04) [host deviation R4f; A-PERF-2]

**Integration outcome:** R4f is kept as the opt-in `GMP_PREFIX` knob (×1.052 over the kept default on the L8 sweep sample; see "Stage 4b integration" above).

R4f is a host addition to the Stage-4b list (`LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`, "Host decisions for Stage 4b"):
the same GMP version, built for the node. It changes no source line. It is opt-in through the Makefile knob
`GMP_PREFIX` (`docs/NUMERICS.md`, "Builds"), and the default build stays byte-identical to Stage 3. The evidence is in
`benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/` (README there). All jobs ran on Expanse (2 × EPYC 7742) from the
export of 913e56a; the layout control ran from ef705e3. They used 76.5 SU.

### What the package links today

- **Expanse.** Spack GMP 6.2.1 (`gmp-6.2.1-eywq454…`, `libgmp.so.10.4.1` sha256 `470e376a…`). Spack's recipe sets
  `force_autoreconf`, and autoreconf replaces GMP's CPU-detecting `config.guess` with the generic one. Configure
  therefore saw the host `x86_64-pc-linux-gnu`: `MPN_PATH="x86_64/k8 x86_64 generic"` and `__GMP_CFLAGS` "-O2
  -pedantic -fomit-frame-pointer -m64 -mtune=k8 -march=k8" (Spack's own build log). The build is not fat (no
  `__gmpn_cpuvec_init`). `__gmpn_mul_basecase` is `mpn/x86_64/k8/mul_basecase.asm`: 296 instructions, 26 `mul`, no
  `mulx`, `adox` or `adcx`, although the EPYC 7742 has BMI2 and ADX. This is the plain `__gmpn_mul_basecase` of P1.
- **symmetry** (read from the packaging only; symmetry was not used). Ubuntu 22.04's `libgmp10` (2:6.2.1+dfsg-3ubuntu1)
  is configured with `--disable-fat` and `--build x86_64-linux-gnu` on amd64 (`debian/rules`, the same block as
  Debian's): the same generic k8 kernels, not a fat build.

### The two builds

Both come from `gmp-6.2.1.tar.bz2` of gmplib.org. Its sha256 `eae9326b…` equals Spack's pin, so these are the bytes
the Spack GMP was built from. Its `.sig` verifies (`VALIDSIG`) with the release key `343C2FF0…28C67298`, whose
fingerprint gmplib.org publishes; the signature dates from 2020-11-14 and the key expired on 2025-01-15. Each build
uses Spack's other configure arguments (`--enable-cxx --enable-shared --enable-static --with-pic`), Spack GCC 13.3.0,
node-local scratch, and no Spack GMP on any search path (jobs 54666320 and 54666321, 1.7–1.8 min each).

| Variant | configure | `MPN_PATH` | `__GMP_CFLAGS` | `mpn_mul_basecase` on the EPYC 7742 | `make check` | `libgmp.so.10.4.1` | Prefix |
|---|---|---|---|---|---|---|---|
| fat | `--enable-fat` | `x86_64/fat x86_64 generic` | `-O2 -pedantic -fomit-frame-pointer -m64` | `__gmpn_mul_basecase_zen` through the CPU vector (family 0x17 → `CPUVEC_SETUP_zen`): 330 instructions, 71 `mulx` | 197/197 pass | `3e4c7c41…` | `~/c8d2/opt/gmp-6.2.1-fat` |
| host | `--host=zen2-pc-linux-gnu` (GMP's `config.guess` on the node) | `x86_64/zen2 x86_64/zen x86_64 generic` | the same plus `-mtune=znver2 -march=znver2` | the zen kernel itself: 330 instructions, 71 `mulx` | 197/197 pass | `4267ffeb…` | `~/c8d2/opt/gmp-6.2.1-zen2` |

`gmp.h` of both differs from Spack's only in `__GMP_CC` and `__GMP_CFLAGS`, which the worker does not use. Built with
`GMP_PREFIX`, the worker (`bin/c8d2_gmp`: fat `c0b03496…`, host `0a77b88e…`) has the default worker's machine code:
26,595 instructions, identical after normalizing absolute addresses. Only `.dynstr` grows (the rpath string, +41/+42
bytes), and every later section moves by 0x30 bytes. `bin/c8d2_decimal` built with the knob set is the Stage-3
`3dbd51bb…`.

### Exactness

Every check below is exact, in every scientific field, and includes the rows with mp > 0.
- **Default build unchanged** (A-RPL-8). With `GMP_PREFIX` unset, job 54666319 (913e56a) rebuilt `bin/c8d2_decimal`
  `3dbd51bb…`, `bin/c8d2_gmp` `5c5328af…` and `bin/c8d2_gmp_prof` `d1cc6551…`, the Stage-3 hashes. The dry-run
  commands of every worker target equal a785602's word for word (`tests/test_gmp_prefix.py`).
- **Replay subset** (G-REF, G-C7, G-JET; `validate.py --only replay`, 22 tests): pass for both variants (jobs
  54666322 and 54666323).
- **G-L8SELF** (A-RPL-7) against the default build: 2,000 L8 kernels × 2 × 512 points; 1,122,367 binary128 and 214,532
  MP points per backend. Pass for both variants.
- **Heavy L8 blocks.** In the speed job, all 9 runs of each block (3 binaries × 3 repeats) give one rows digest:
  `92eec91c…` for heavy_free_L8 (4,194,304 points, 1,003,400 MP) and `c9b8e059…` for heavy_power_L8 (1,504,626 MP),
  the digests of Stage 4a's P1 (54661716). The profile subsets agree as well.
- **Not run here:** A-RPL-6 (thread identity) and the full J-VAL-2 replay. They belong to the gate on the integrated
  binary.

### Speed

Job 54666324, <NODE>, exclusive. heavy_free_L8 ran on socket 0 and heavy_power_L8 on socket 1 at the same time, 64
threads each. Each repeat ran the three binaries in a rotated order. Medians of 3 runs:

| Block | Spack GMP (baseline) | fat | host (zen2) | Speedup, fat | Speedup, host |
|---|---:|---:|---:|---:|---:|
| heavy_free_L8 | 159.94 s (159.5, 160.2, 159.9) | 156.09 s (155.9, 156.2, 156.1) | 154.15 s (154.5, 154.1, 154.2) | ×1.0247 | ×1.0375 |
| heavy_power_L8 | 149.72 s (149.7, 149.9, 149.7) | 146.09 s (146.1, 146.0, 146.4) | 143.64 s (143.6, 144.6, 143.4) | ×1.0248 | ×1.0423 |

Integration seconds give the same ratios (×1.0251 / ×1.0385 and ×1.0254 / ×1.0433). The spread within each cell is at
most 0.9%.

**Where the time goes** (jobs 54666322/3: every 8th task of each block, 32 threads, the variant against the default
build on the same node). The tier timers leave the first pass and binary128 unchanged (×0.995–1.000). The MP tier
gets ×1.068 (fat; free and power) and ×1.125 / ×1.126 (host) per call (the layout control on another node measured
×1.10–1.13 for host). In perf, as percent of the baseline's time
(free / power):
- `mpn_mul_basecase`: 10.0 / 14.5 → 6.6 / 9.7 (fat) and 6.3 / 9.2 (host).
- `mpn_add_n` (the same `x86_64/aors_n.asm` in every build): 7.0–8.0 → 7.4–8.9.
- `mpn_copyi`: 4.1 / 5.0 → 5.1 / 6.0 (fat) and 5.1 / 5.8 (host). GMP's zen `copyi` is slower than the generic one at
  these sizes.
- `mpn_sub_n` and `mpn_toom22_mul` appear (0.7–1.3% and 0.4–0.8%). The zen thresholds send some products to
  Karatsuba.
- The worker's own `calculate_shared<gmp_float<350>>` drops from 4.2 / 4.9% to 2.7 / 3.5% (fat) and 2.2 / 2.8%
  (host), with machine code identical up to addresses. The worker's other hot functions (`main._omp_fn.0`,
  `calculate_shared<__float128>`) do not move.
  - The fat and host workers have the same layout (10 bytes differ) yet differ here. That points at the library, which
    shapes how the caller's time around each GMP call is spent and sampled, rather than at the 0x30 code shift.
  - The layout control below tests this directly.

### Layout control

Job 54668998 (export of ef705e3, shared, 32 threads, every 8th task, two rounds in opposite orders).
- **The control worker.** The Spack GMP is linked through `GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-spak`, a directory of two
  symlinks into the Spack prefix whose path has the zen2 prefix's length. The resulting `c8d2_gmp` and `c8d2_gmp_prof`
  differ from the host worker's in exactly 4 bytes (the "spak"/"zen2" characters of the rpath). They have the host
  worker's layout and the baseline's library.
- **Rebuilds in the same job.** The default worker came out at the Stage-3 `5c5328af…` and the host worker at
  `0a77b88e…`.
- **Rounds.** Round 2 shared its node with busy neighbours (binary128 per call 3–14% above round 1 for every
  binary). The comparison therefore uses each run's MP/binary128 per-call ratio, which cancels that common factor.

| Block | MP/binary128 per call: baseline (r1, r2) | control (r1, r2) | host (r1, r2) | control / baseline | baseline / host |
|---|---|---|---|---|---|
| heavy_free_L8 (32 tasks) | 2.1050, 2.1045 | 2.1119, 2.1070 | 1.9163, 1.8657 | 1.0033, 1.0012 | ×1.098, ×1.128 |
| heavy_power_L8 (32 tasks) | 2.2850, 2.2806 | 2.2900, 2.2878 | 2.0771, 2.0173 | 1.0022, 1.0032 | ×1.100, ×1.131 |

- **perf.** The control's shares equal the baseline's: `calculate_shared<gmp_float<350>>` 4.19–4.22% against
  4.18–4.21% (free) and 4.83–4.85% against 4.82–4.87% (power), `mpn_mul_basecase` 10.00–10.01% against 9.99–10.05%.
  The host worker, in the same layout, has 2.19–2.21% and 6.73–6.96% (free).
- **Conclusion.** The 0x30-byte code shift costs at most 0.3%. The R4f gain, including the drop in the worker's own MP
  function, is the library's.
- **Rows.** Every run of a block, all three binaries and both rounds, gives one rows digest.

### Projection to the L8 population

The measured MP-tier factor (host ×1.10–1.13, fat ×1.068) is applied to Stage 4a's L8 split (first pass and
sampling / binary128 / MP). Only the MP tier changes.
- Campaign a (7.8 / 61.5 / 30.7%): host ×1.029–1.037 (free L8 ×1.024–1.031, power L8 ×1.041–1.053), fat ×1.020.
- Campaign b (9.1 / 66.3 / 24.6%): host ×1.023–1.029, fat ×1.016.

The heavy blocks carry more MP time (35–42% of thread time) than the population (25–31%), which is why they measure
more. The same formula gives ×1.033–1.042 (free) and ×1.040–1.051 (power) for them, against the measured ×1.0375 and
×1.0423.

### Decision input (A-PERF-2)

- Both builds pass every exact check run here.
- **host (zen2)** clears the 3% bar on both heavy L8 blocks (×1.0375 and ×1.0423, medians of 3 on one node). The
  projection to the whole L8 population is ×1.023–1.037: above the bar for campaign a and the power sector, at or
  below it for campaign b's free sector.
- **fat** is portable to any x86-64 CPU but stays at ×1.025, below the bar.
- Recommendation: R4f as an opt-in, per-site build. Build `GMP_PREFIX=<that site's host-tuned GMP 6.2.1>` on the
  site's nodes with `make check` (the recipe is `benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/scripts/
  r4f_gmp_build.slurm`), and use the build only after A-RPL-1/2/3/6/7 pass exactly there.
  - A zen2 library uses `mulx`/`adx` kernels and `-march=znver2` C code. It suits Zen 2 and Zen 3 (Expanse, symmetry
    amdq), not the Intel nodes.
  - On symmetry, GMP's own `config.guess` on an EPYC 7543 is expected to name zen3, which configure maps to the same
    zen2/zen kernel path. That build and its gates have not been run.
- Not tested, each also exact:
  - keeping the generic `copyi` in a zen2 build, worth about 1% of time;
  - linking `libgmp.a` statically, which removes the PLT from the worker's mpf calls.
