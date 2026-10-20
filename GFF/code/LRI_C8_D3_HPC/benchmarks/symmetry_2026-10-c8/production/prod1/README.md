# C8(3) production prod1-20261008 on symmetry (2026-10-08 to 2026-10-12)

Copied on 2026-10-12 from symmetry. Decisions and readings are in `LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md`, entries
2026-10-08 to 2026-10-12.

- **Campaign:** `$C8_ROOT/runs/prod1-20261008` (`C8_ROOT=<SCRATCH>/c8d3`, 13 GB, 33,776 files).
- **Export:** D_P `4fbd1bae5a88`.
- **Plan:** job 571488, 1,941 indices, design A (bundle 60a87d5a).
- **Seed:** 7204841255549554256.

## Result

**C8(3) = 1602.6052 ± 0.9516 (sampling SE).**

- `C8_result.json`: sha256 b0776258…; label production, final true.
  - Written by merge 573345 at 2026-10-12 04:31 EDT. Every later merge logged "identical result already present;
    kept".
- **Parts:** power-free 1601.9999 ± 0.7279, power correction 0.6053 ± 0.6129 (diagnostic pull +0.99).
- **verify_result.py RUN:** verified, rc 0 (`c8d3_prod1_verify.json`). It ran under OPENBLAS_CORETYPE=Zen, the AMD
  kernels the merge used (C62d F6).
- **Lower orders:**

  | Order | Estimate | Reference | Pull |
  |---|---|---|---|
  | C3 | −0.3535809 ± 0.0000014 | −0.3535815 | +0.43 |
  | C4 | 1.228045 ± 0.000039 | 1.228064 | −0.49 |
  | C5 | −5.84999 ± 0.00049 | −5.85035 | +0.74 |
  | C6 | 33.57637 ± 0.00509 | 33.57543 ± 0.00012 | +0.19 |
  | C7 | −220.3848 ± 0.0529 | −220.3545 ± 0.0318 | −0.49 |

- **Other checks:**
  - power nulls: pulls ≤ 1.17;
  - b_3^p(0) control: pull +1.30;
  - bootstrap/covariance SE ratio: 0.988;
  - campaigns a/b: 1604.684 and 1600.527, pull +2.18.
- **Tail monitor:** 10,034 L8 graphs listed (two-campaign Hill ξ̂ > 0.44), 0 flagged (variance share > 3%), 0
  undefined.
- **Independent check:** the c8opt package on Expanse (`LRI_C8_D3_OPT_loop/production/`) gives 1600.98 ± 3.97. The
  difference is −1.63 ± 4.08, a pull of −0.40.

## Cost

Production line: **15,101.6 core-h** of the user's 20,000 (`c8d3_prod1_budget.txt`); design A predicted 15,492.

- **Lanes:** 65 lane jobs, 36 of them longer than 10 min. 8 lanes with C8_LANE_TIME 07:30:00, first start
  2026-10-09 01:26, last end 2026-10-12 04:28. 14,970 core-h.
- **Merges:** 36 merges, 105.9 core-h. 34 of them (573347–573504, 97.9 core-h) are redundant: they ran after
  completion.
  - Cause: the host's replenish loop (`production/prod_replenish.sh`). It read the incomplete count from `production.py
    status` and did not stop when the count disappeared. A complete campaign prints "complete: every checkpoint block
    is committed".
  - Fixed in the script: DONE on that line, and stop on an unknown count. The merges are idempotent, so the result is
    unaffected.
- **Job list:** `jobs_sacct.psv`.

## Operations

- **Window:** H11-prod-c63d-20261008 (DECISIONS lines 104–105 and 2026-10-10/12; 9 AMD-pool jobs for C63d). Extended
  twice; closed 2026-10-12 08:27 EDT.
- **amdq outage:** 11 nodes went down on 2026-10-10 07:48 and came back.
- **<NODE> admitted 2026-10-11:** it is EPYC 7543 by lscpu in job 567732. It was removed from C8_AMD_EXCLUDE_EXTRA, and
  lane 573151 ran on it.
  - <NODE> is EPYC 7532 (lscpu in C62d job 570574).
  - <NODE>–091 are in another user's reservation.

## Files

| file | what |
|---|---|
| `C8_result.json`, `manifest.json`, `cost_model.json`, `cpu_vendor.json` | the run's top-level files |
| `slurm_logs/` | every lane worker's and merge's log (101) |
| `lanes/` | lane queue, claims, done markers, logs |
| `production/` | `$C8_ROOT/evidence/4fbd1bae5a88/production/` (prod_env.sh, design freeze, lanes outputs r1–r3 and the auto loop's), plus the host loop script and its log |
| `c8d3_prod1_status.txt`, `c8d3_prod1_verify.json`, `c8d3_prod1_budget.txt` | `production.py status`, `verify_result.py RUN`, `budget.py` on 2026-10-12 |
| `jobs_sacct.psv` | sacct of every c8d3-prod_lane/merge job |

The full run tree, checkpoints and merged groups included, is archived to Google Drive (see `CATALOG.tsv`).
