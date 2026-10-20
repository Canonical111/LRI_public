# C6(3) production campaign, M = 8192 (SDSC Expanse, started 2026-09-29)

## Setup

- **Package.** `~/c6d3_prod/pkg` on Expanse, a `git archive` export of LRI_C6_D3_HPC `1c6dfb3` (Codex-APPROVED;
  final code 73d3635).
  - Binary sha256 2f897044df1aa6ed91ca5cd70d2c1af6287a77bca16dfcad108386fcae60c698, identical to the validated build.
  - `checksums.py verify --strict`: 1780/0/0/0.
  - Env: `<SCRATCH>/temp_project/c6d3_fix/c6d3_env.sh`.
- **Run directory.** `<SCRATCH>/temp_project/c6-d3/run-20260929-m8192`.
- **Seed and tag.** Seed 3864037981285414462 (fresh, from `secrets.randbits(63)`). Tag `c6:624815e78a23`.
- **Plan (srun job 54515878, 93 s).** `--replicates 64 --multiplier 8192 --chunk-points 8388608 --threads 64
  --checkpoint-tasks 1024 --shards 200`.
  - 458 jobs:
    - a_L3 0, a_L4 1–4, a_L5 5–28, a_L6 29–228;
    - b_L3 229, b_L4 230–233, b_L5 234–257, b_L6 258–457.
  - 6.32e12 samples; estimated 9,653 core-h; largest shard about 28 min; suggested time 1:25:00.
- **Projected C6(3) sampling SE.** 0.00022, plain MC scaling of the archived fresh-only 0.0281, versus the archived
  primary SE 0.0242.
- **Submission.** `C6_SBATCH_ARGS="-A <ACCOUNT> -p shared"`; `--mem` as an extra argument (work elements only). Elements
  get 64 CPUs, so the 64-job per-user cap on the shared partition allows at most 64 concurrent elements.

## Launch log

- 2026-09-29 07:08 PDT:
  - preflight element index 29 (a_L6 shard 0), array 54515885;
  - thread-identity check, job 54515886 (same-seed throwaway plans; one a_L6 and one b_L6 block at 64 vs 16
    threads; the scientific fields must be identical).

## Reporting rule (pre-registered; confirmed by the user 2026-09-29 09:06 PDT)

The user confirmed this rule, unchanged from the proposal written at launch (07:08 PDT). At the time of
confirmation no production result existed: 670 checkpoint blocks were committed, and no `merged.json` or
`C6_result.json` had been written. The result is reported by this rule as written. Any later change must be recorded
as a separate, dated amendment and must not replace this text.


1. **Primary estimate.** The frozen equal-weight a/b combination (`C6_result.json`); the bootstrap is diagnostic
   only.
2. **Quoted allowance.** 4 × SE rounded up to 0.001. This follows the archived four-SE convention; the archive rounded
   in steps of 0.05, which is too coarse at this precision.
3. **Consistency gates.** These are checked, never used to tune or select:
   - **a/b campaigns.** |C6_a − C6_b| / sqrt(se_a² + se_b²) ≤ 3. Otherwise report both, flag the result, and widen the
     allowance to cover |a−b|/2.
   - **Bootstrap.** The bootstrap SE must be within ±20% of the covariance SE.
   - **Archived value.** Agreement with the archived 33.5682 ± 0.0242 (SE) within 3 of the archived SE.
   - **Lower orders.** C3–C5 pulls against the published constants must satisfy |pull| ≤ 4. A larger pull is
     flagged, investigated and reported, and does not alter C6. The archived fresh C3 pull was already +2.42, and at
     about 110× the precision these pulls are very stringent.

## Preflight results (2026-09-29 07:08–07:25 PDT)

- **Thread identity (job 54515886).** One a_L6 and one b_L6 block of 1024 tasks each were run at 64 and at 16
  threads. All 2048 rows have identical scientific fields; the blocks include 141,994 binary128 promotions.
- **Production preflight (index 29, a_L6 shard 0, <NODE>).** The first block (the heaviest 1024 tasks) ran in 975 s
  native integration, with 61,093 task-seconds (utilisation 0.979). MaxRSS was 121 MB; the block had 3.28M binary128
  and 0 cpp_dec_float promotions.

## Release (2026-09-29 07:26 PDT)

- `slurm/resubmit.sh --mem=8G` excluded the live index 29 and submitted array 54516761 (`0-28,30-457%64`).
- Merge 54516762 runs `afterok` on 54516761 and 54515885_0.
- Tasks 53 and 54 failed at launch (node side; `launch_failed_requeued_held`, never ran) and were released with
  `scontrol release` at 07:27.
- A monitor auto-releases such never-run held tasks and logs each release.

## Completion (2026-09-29 10:15 PDT)

- **Jobs.** All 459 jobs COMPLETED: preflight 54515885_0, array 54516761 (457 elements) and merge 54516762 (1 m 30 s).
  Work ran 07:08–10:14 PDT. `status`: every checkpoint block committed; 8 groups merged; 0 failure logs.
- **Held tasks.** Only tasks 53 and 54 (never ran) were released; the monitor made no further releases.
- **Data.** Local copies:
  - `results_run-20260929-m8192/`: `C6_result.json`, `manifest.json`, group configs, `merged.json`,
    `graph_replicates.csv`, merge log;
  - `run-20260929-m8192_full.tgz`: the complete run directory including checkpoints and task databases, 74 MB,
    sha256 b11b7874… in `.sha256`.

## Result, reported by the pre-registered rule

**C6(3) = 33.5754 ± 0.001.**
- Underlying estimator 33.57542664131543; sampling SE 0.00011854952350322613.
- Allowance 4 × SE = 0.00047, rounded up to 0.001.
- **Precision.** The sampling SE is 204× below the archived 0.0242, and 1.85× below the plain-MC projection 0.00022:
  RQMC does better than 1/N at this scale.
- **Error by loop:** L3 1.1e-6, L4 2.1e-5, L5 5.8e-5, L6 1.0e-4.
- **Consistency gates** (all PASS):
  - **a/b campaigns.** a = 33.57562307 ± 0.00015062, b = 33.57523021 ± 0.00018311; pull 1.66 (≤ 3).
  - **Bootstrap.** Bootstrap SE 0.00011534, ratio 0.973 (within ±20%); mean − estimate 2.1e-8.
  - **Archived value.** 33.5754 − 33.5682 = +0.0072 = 0.30 archived SE (≤ 3). The previous report 33.57 ± 0.10 is
    consistent.
  - **Lower orders**, against the published constants (|pull| ≤ 4):

    | Order | Estimate | Pull |
    |---|---|---|
    | C3 | −0.3535815650 (SE 2.6e-8) | −1.69 |
    | C4 | 1.2280621550 (SE 1.3e-6) | −1.10 |
    | C5 | −5.8503379659 (SE 1.5e-5) | +0.92 |

- **Inputs** (from `C6_result.json`): `inputs/manifest.json` e8c60c1c…, `inputs/two_loop.json` f60e2064….
- **Scope.** This is a sampling allowance only. As before, it relies on the retained analytic power-sector
  compensation and the finite-MOM framework, which this package does not redo (`empirical_allowance` in the file is
  deliberately unset).

## Amendment 1 (2026-10-01, made after the result was known, at the user's request)

- **Change.** The rounding step of the quoted allowance goes from 0.001 to 0.0001. The allowance is still 4 × SE:
  4 × 0.00011855 = 0.00047, rounded up to **0.0005**.
- **Reported result.** **C6(3) = 33.5754 ± 0.0005.** Under the rule as registered it was 33.5754 ± 0.001; that text
  above is kept unchanged.
- **Reason.** At this precision a 0.001 step more than doubles the four-SE allowance, to about 8.4 SE. The estimator,
  the 4 × SE multiplier and the consistency gates are unchanged, and all gates still pass. This is a post hoc change of
  rounding granularity only.

## Errata (2026-10-01, from Codex results review round 1)

- **Precision bullet.** "RQMC does better than 1/N at this scale" overstates the evidence. The projection scales
  the SE as 1/√N (plain Monte Carlo). What is supported is that the measured SE is about 0.54 times that plain-MC
  projection (0.00022); no convergence rate is claimed.
- **Lower-order table.** The C4 pull is **−1.09** (`C6_result.json`: −1.0948740666819077), not −1.10. The gate outcome
  is unchanged.
