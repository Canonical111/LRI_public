# Expanse validation of the d=3 Expanse-readiness revision (2026-09-28)

## Setup

- **Machine and partition.** SDSC Expanse, AMD EPYC 7742, account <ACCOUNT>, **partition `shared`**, as the approved plan
  specifies.
- **Software.** Modules `cpu/0.21.2a gcc/13.3.0 boost/1.86.0`; a venv with Python 3.11.9, numpy 1.26.4, scipy 1.17.1
  and mpmath 1.3.0 (`c6d3_env.sh`).
- **Location.** Work directory `<SCRATCH>/temp_project/c6d3_fix/`, on Lustre.
- **Code under test.** A `git archive` export of commit **73d3635**, the final code, plus the baseline export 6e642ca
  for the D1 comparison.
- **Jobs.** Every job went through Slurm. The campaigns were submitted with the shipped `slurm/submit.sh` and
  `slurm/resubmit.sh`, from fresh login shells (`env -i ... bash -l`) in which only `C6_ENV_SETUP` supplies the
  environment, with `C6_SBATCH_ARGS="-A <ACCOUNT> -p shared"`.
- **Cross-check.** `compute_crosscheck/` holds an earlier run of the same validation on the `compute` partition (code
  61183bb, which differs only in the calibration constants), made while the user's shared slots were occupied. It
  gives the same outcomes and is kept as additional evidence.

## Calibration: arrays 54510585, 54510589, 54510590, 54510591 (`calib2*`, `calib2/slurm_logs/`)

- **Runs.** 12 `slurm/run_array.sh` elements at 16 CPUs, `--mem=16G`, via `submit.sh --window`: shards 0–1 of every
  L3–L6 group of a README-scale plan (multiplier 4, 64 replicates, `--threads 16 --checkpoint-tasks 512`), all
  COMPLETED.
- **Measured seconds per estimated cost unit** (Σ native task-seconds / Σ cost; `calib2_metrics.json`):

  | L3 | L4 | L5 | L6 |
  |---|---|---|---|
  | 3.01e-8 | 1.27e-8 | 6.18e-9 | 3.62e-9 |

- **OpenMP efficiency** inside the native calls: 0.987–0.998.
- **Cross-check.** These values are the `CALIBRATION` of `tools/production.py`. The compute-node cross-check (job
  54510049) agrees within 2.4% for every loop.

## Validation suite: job 54510646 (`validation_shared.slurm`: shared, 16 CPUs, 32 GB; `validation_shared-54510646.out`, `logs/validation_54510646/`)

- **D1.** The baseline (6e642ca) and final (73d3635) sources build to the identical `bin/c6_integrate`, sha256
  2f897044df1aa6ed91ca5cd70d2c1af6287a77bca16dfcad108386fcae60c698.
- **Tests.** `make test`, `make test-workflow`, `make test-points`, `make test-levels` and `make test-e2e` pass.
- **Archived-stream replay.** Passes on 16 threads:
  - 385,744,896 samples across all eight archived fresh streams;
  - equal fallback counts in every stream;
  - the replayed fresh-only C6(3) is bitwise equal to the published 33.560840352429125.
- **Reassembly.** `reassemble_reference.py` passes, bitwise for C6 and the SE.
- **Benchmark (`bench_54510646/benchmarks.json`).** Matched, one thread, median of 3:

  | Loops | Wall speedup | Integration-only speedup |
  |---|---|---|
  | Five | 1.61× | 1.40× |
  | Six | 1.61× | 1.42× |

- **Nothing written into the package.** The package tree hash is unchanged by all of the above, and `inputs/*.json`
  are 0644.
- **`make check-delivery` in this job** reported the two items expected for this deployment:
  - `COMMIT`, the deployment marker file, is unlisted;
  - `tools/production.py` changed, because the calibration commit came after the manifest was last written.

  The delivery manifest is regenerated for the final commit and verified strictly (`make check-delivery`), with
  every tracked file listed.

## Smoke campaign `smokeS3` (arrays 54510776–54510778, merge 54510779)

- **Plan.** `--points 8 --replicates 4 --shards 4 --threads 2 --checkpoint-tasks 64 --chunk-points 3`, 14 jobs.
- **Submission.** `C6_MAX_ARRAY=6 slurm/submit.sh --mem=4G` created 3 arrays with offsets 0, 6 and 12, plus an afterok
  merge.
- **Outcome.** Everything completed and `C6_result.json` was written. It is a smoke value, not a physics result.

## Status-line drill (`drill_status3/`, on the completed `smokeS3`)

1. One committed checkpoint was deleted: b_L5 shard 0 block 0, job index 9.
2. `C6_MAX_ARRAY=2 production.py status` exited 1. It printed `resubmit: C6_MAX_ARRAY=2 C6_RUN=… C6_PACKAGE=… …/slurm/submit.sh --window 8:1`.
3. That line was run from a shell holding stale `C6_RUN=/stale/run`, `C6_PACKAGE=/stale/pkg`,
   `C6_INDEX_OFFSET=999` and `C6_MAX_ARRAY=1000`. Job 54510828 ran exactly `index 9 (offset 8 + array 1)` in the right
   campaign. `status` then exited 0, and the recomputed checkpoint's scientific fields are identical to the deleted
   one's.
4. `slurm/resubmit.sh` found nothing missing and nothing live, so it submitted only merge 54510834, without a
   dependency. That merge skipped every group and kept the identical result: all 17 merged, CSV and result files are
   byte-identical to before.

## Recovery drill (`drill_recovery3/`, fresh campaign `smokeR3`)

1. **Submit.** With a stale `C6_INDEX_OFFSET=0` exported, `C6_MAX_ARRAY=6 C6_THROTTLE=1 slurm/submit.sh` created
   arrays 54510801, 54510802 and 54510804, and merge 54510805.
2. **Inject a failure.** `scancel --state=PENDING 54510804_1` was issued. The last array's two tasks were still one
   pending array record (throttle 1), and Slurm cancelled that whole record (sacct: 54510804 CANCELLED), so indices 12
   and 13 never ran. The same happened in the compute cross-check.
3. **Refusal.** `resubmit.sh` exited 65 while merge 54510805 was queued.
4. **Recovery.**
   - The pending merge was cancelled.
   - `resubmit.sh` reported indices 0–11 as live and did not resubmit them.
   - It resubmitted exactly the missing indices 12 and 13 (array 54510817, offset 12).
   - It submitted merge 54510818 with afterok on 54510817 and on each live task (54510801_0–5, 54510802_0–5).
5. **Guards.** Each refused before anything was submitted:
   - `--export-file` in `C6_SBATCH_ARGS`: exit 64;
   - an inherited `SBATCH_CLUSTERS`: exit 64;
   - an existing campaign lock: exit 75.
6. **Outcome.**
   - Every index 0–13 ran exactly once, with index = offset + task in every worker log.
   - `status` exits 0; merge 54510818 wrote `C6_result.json`.

## Throughput pilot (`pilot3/`, `pilot3_metrics.jsonl`)

- **Plan.** README-scale (multiplier 4, 64 replicates) with `--shards 4 --threads 16 --checkpoint-tasks 512`. Each L6
  shard holds about 1,860 estimated core-seconds.
- **Runs.** All 8 L6 shards, submitted with `submit.sh --window` (arrays 54510771 and 54510775) on shared at 16 CPUs,
  `--mem=16G`.
- **Measured.**
  - Σ task-seconds 1860–2108 per shard.
  - OpenMP efficiency inside the native calls 0.992–0.998.
  - Overall utilisation, Σ task-seconds / (16 × sacct elapsed), is 0.922–0.940 on 7 shards and 0.843 on one (index
    12).
- **Criterion.** Met: ≥ 3 L6 shards with overall ≥ 0.85 (here 7 of 8) and inner ≥ 0.90.
