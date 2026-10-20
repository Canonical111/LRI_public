# Stage 4b integration on Expanse: J-OPT gates and the A-PERF-2 speed gate (branch `c8`, 2026-10-04)

The developer branches were merged into `c8` in plan order, and each cumulative step was gated and timed here. Results
and decisions are in `docs/PERFORMANCE.md`, "Stage 4b integration". `scripts/summarize_int.py` recomputes them from the
records in this folder into `int_summary.json`.

**Merges.**
- 138d486 merges `opt-r5`.
- d46e736 merges `opt-r3a`.
- bc0bedc merges `opt-r4a`.
- 7b9aa9c merges `opt-r4f`.
- d0f0e05 adds these scripts.
- ea59445 reverts R4a's code (A-PERF-2: ×1.0093).

**Environment.** `~/c8d2/env_expanse.sh` `6f85cb50…`, Spack GCC 13.3.0, Spack GMP 6.2.1, and Boost 1.77 headers. The
opt-in zen2 GMP is `~/c8d2/opt/gmp-6.2.1-zen2`, with libgmp sha256 `4267ffeb…`, built by R4f's development job
54666321.

**Exports.** Each is `git archive` of its commit, checked equal file by file and mode by mode:

| Commit | Record | Files |
|---|---|---:|
| 138d486 | `../../setup/export_check_138d4866c7e4.json` | 5,615 |
| d46e736 | `../../setup/export_check_d46e7360fe88.json` | 5,820 |
| bc0bedc | `../../setup/export_check_bc0bedc3d72b.json` | 5,927 |
| d0f0e05 | `../../setup/export_check_d0f0e05a4c21.json` | 6,183 |

The L8 packs were hard-linked from the c17688158e2b export and re-hashed by `make`.

**Scripts** (`scripts/`):
- `submit_int.sh` is the Mac driver. It makes the exports and their checks. Before every sbatch it runs H7E-R
  (`../../stage4a/scripts/h7_admit.py` on a fresh `squeue -A <ACCOUNT>`) and this workflow's own limit: at most 4 compute
  nodes and 8 shared jobs named `c8d2-int-*`.
- `int_build.slurm` builds one step in its export and copies the Stage-3 baseline into `bin/baseline/`, checking its
  hashes. It then runs `validate.py`'s default parts. With `INT_VARIANTS=1` it also does three things:
  - checks that the R4f merge's default build equals +R4a's;
  - makes the zen2 `GMP_PREFIX` builds of the +R3a and +R4a sources;
  - makes a default build of the +R3a source with the R4f Makefile, which must equal +R3a's.

  It can also run a speed smoke test.
- `int_gate.slurm` runs G-L8SELF against `bin/baseline`, thread identity and, optionally, the replay subset and the quad
  differential.
- `int_speed.py` and `int_speed.slurm` are the A-PERF-2 measurement and the IPC run for the R3c rule. Its docstring
  fixes the workload and the metric.
- `summarize_int.py` writes the tables.

**Admission records** (`admission/`): the H7E-R line before every sbatch (`h7e_r_admission.jsonl`), the squeue
snapshots, `submitted.txt`, the `lfs quota` lines and the sacct records.

| Job | Where | What it shows | Files |
|---|---|---|---|
| 54669703 `c8d2-int-build` | `shared` 16 CPUs, 32 GB, 2:08 | +R5 (138d486) build: decimal `b36bf334…`, gmp `f4ad369c…`; `validate.py` default parts passed | `intbuild.54669703.0/` |
| 54669704 `c8d2-int-build` | `shared`, 2:10 | +R3a (d46e736) build: decimal `99a51c1d…`, gmp `1d2a2181…`, `make quaddiff`; default parts passed | `intbuild.54669704.0/` |
| 54669705 `c8d2-int-build` | `shared`, 2:12 | +R4a (bc0bedc) build: decimal `99a51c1d…`, gmp `8b296ddb…`; default parts passed | `intbuild.54669705.0/` |
| 54669706 `c8d2-int-build` | `shared`, 2:36 | d0f0e05 (the R4f merge and the scripts): default build byte-identical to +R4a (`default_vs_S3.json`); zen2 builds `int-zen2-S2src` (B2f, gmp `aa84cd45…`) and `int-zen2-S3src` (B4, `accb36ca…`), both loading the zen2 libgmp through DT_RPATH; the default build of the +R3a source with this Makefile equals +R3a's gmp (`variants_check.json`); default parts passed; speed smoke passed | `intbuild.54669706.0/` |
| 54669707 `c8d2-int-gate` | `compute` exclusive, <NODE>, 9:32 | +R5 and +R3a: G-L8SELF exact (both backends, 4,000 rows each) and thread identity identical | `intgate.54669707.0/` (`S1/`, `S2/`, `gate_summary.json`) |
| 54669708 `c8d2-int-gate` | `compute` exclusive, <NODE>, 14:11 | +R4a, B2f and B4: G-L8SELF exact and thread identity identical; replay subset passed (22 tests) for both zen2 builds | `intgate.54669708.0/` (`S3/`, `B2f/`, `B4/`) |
| 54669709 `c8d2-int-speed` | `compute` exclusive, <NODE>, 5:25 | A-PERF-2 on the L8 sweep sample, 6 binaries × 3 repeats, rows identical in all 18 runs; IPC 3.04 (+R3a) and 3.05 (+R4a) on heavy_free_L8 | `intspeed.54669709.0/` (`int_speed.json`, perf stat CSVs) |

| 54672108 `c8d2-int-build` | `shared`, <NODE>, 2:11 | Final candidate e7ef98d (export check `../../setup/export_check_e7ef98d90487.json`, 6,317 files): decimal `99a51c1d…` and gmp `1d2a2181…`, byte-identical to +R3a; the zen2 worker `int-zen2-final` `aa84cd45…`, byte-identical to B2f and loading the zen2 libgmp; default parts passed | `intbuild.54672108.0/` |
| 54672109 `c8d2-int-gate` | `compute` exclusive, <NODE>, 9:38 | Final: G-L8SELF exact, thread identity identical, and quad differential passed (2^32 pairs per operation, edge lists, injection and ASan+UBSan, 0 mismatches). Final zen2: G-L8SELF exact, thread identity identical, replay subset passed | `intgate.54672109.0/` (`FINAL/`, `FINALzen2/`) |

The Slurm logs are in `logs/`. Staged graphs, native outputs and package copies stayed on node-local
`/scratch/$USER/job_<id>`.

**Allocation.** 85.8 SU in all.
- The seven step jobs used 64.6 SU (`admission/sacct_steps.txt`): the builds 0.58, 0.59, 0.60 and 0.71, and the
  compute jobs 20.34, 30.26 and 11.56.
- The final candidate used 21.1 SU (`admission/sacct_final.txt`): 0.60 and 20.55.

Shared jobs are charged at the larger of the CPUs and memory/1.95 GB, and compute jobs at 128 SU per node-hour. At
most 3 compute nodes and 4 shared jobs of this workflow were live at a time.

**Lustre.** <USER> went from 1,263,333 to 1,312,566 files, a count shared with C63d's session. This workflow added
about 30,500 of them, nearly all in the five exports.
