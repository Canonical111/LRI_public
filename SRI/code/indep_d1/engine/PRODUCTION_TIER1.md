# Tier-1 production (6-digit target, T = 5e-5): log

2026-10-03, symmetry `amdq` only (whole 64-core AMD nodes, at most 8 nodes at a time apart from about ten minutes, see 4).
The personal desktop and Expanse were not used. Archive values were not compared here.

**Outcome.**

* Tier 1 ran as planned: 86 cfgs, 46 groups, 116 needed raw coefficients, R = 6 shifts everywhere. Every job
  completed, and `collect`, `seedcheck` and `outliers.py` all pass.
* C6 met the target with a large margin. sigma(C7) = 4.6e-5 (sigma_cov), 5.9e-5 (sigma_rep) and 5.9e-5
  (sector-pooled), so two of the three estimators were above T.
* A **top-up** reran the four groups that dominated C7 one prime-ladder step higher, with fresh seeds:
  Q6_E (N=524287), A7_v and A7_base (N=131071), and A5_vE (N=262139).
* **Final** (`runs/prod_6digit/results_final.json`):
  * sigma(C6) = 1.45e-6 / 1.33e-6 / 1.28e-6 (rep / cov / pooled)
  * sigma(C7) = 3.11e-5 / 2.66e-5 / 3.14e-5
  * Both are within T = 5e-5 by every estimator. C7 is now dominated by Q8.
* Strict-tolerance re-evaluations of the most-warned sectors agree with production: the worst case is 1.5e-13 of
  the sector size and 6e-7 of the statistical error (88 Q8, Q6_E, A7_v and low-dimensional sectors in total).
* Allocated: **2942.9 core-hours**. Of these, 2184.6 were tier-1 production, 372.0 the top-up, 384.5 the strict
  checks and 1.7 planning. The engine's own CPU accounting for production plus top-up is 2539.4 core-hours.

## 1. What ran (code identity)

| item | value |
|---|---|
| engine | `bin/lri_engine` md5 `ec238e0fa37b` built from `src/lri_engine.cpp` md5 `edfa65dce4d6` (g++ 11.4, `-O3 -march=x86-64-v3 -ffp-contract=off`, regression job 569089); the same binary for every job below |
| sources | `src/ py/ slurm/ specs/ tests/` md5-identical on the Mac and on symmetry (`<SCRATCH>/sri_c6c7/engine`) before launch |
| spec / plan | `specs/production_6digit.json` from `py/plan_production.py` (`results/production_plan.md`: 2367 core-h, predicted sigma(C6) = 3.1e-6, sigma(C7) = 3.7e-5) |
| launch | `bash slurm/submit_production.sh 6digit 8`: plan on a compute node, then `sbatch --array=1-86%8 slurm/production_symmetry.sbatch runs/prod_6digit 1` |
| lattices | the plan job added 6 weighted-P2 Korobov generators to `py/korobov_db_g01.json` (copied back to the Mac): 1048573_1: 397265, 1048573_2: 409002, 131071_4: 123727, 131071_5: 29952, 32003_3: 11868, 32003_4: 7551 |
| seeds | hash(tier, group, k, chunk). `seedcheck runs/prod_6digit`: 45450 streams, all disjoint. Pairwise against `regress_v2/{new,replay5,replay4,strict,direct_v2}` and `pilot2..5`: no production stream overlaps any earlier one (the overlaps those listings report are internal to the phase-1 runs, which share seed 1234567) |

The personal desktop was not used. Its copy of the engine is stale (pre-v2), it shares no filesystem with symmetry, and the
cheap low-dimensional groups (about 3 core-h in all) ran at the tail of the symmetry array within minutes.

## 2. Jobs (sacct; `logs/symmetry/sacct_tier1_all.txt`)

| job | name | tasks | partition | start - end (EDT) | allocated core-h | state |
|---|---|---|---|---|---|---|
| 569302 | sri_eng_plan_6digit | 1 | amdq | 01:33:52 - 01:34:55 | 1.1 | COMPLETED (86 cfgs, seedcheck disjoint) |
| 569303 | sri_eng_prod | 86 (%8) | amdq | 01:35:12 - 06:36:49 | 2184.6 | 86/86 COMPLETED, exit 0:0 |
| 569427 | sri_eng_strict_lowdim | 1 | amdq | 05:09:32 - 05:21:32 | 12.8 | COMPLETED |
| 569428 | sri_eng_strict_a7v | 1 | amdq | 05:41:23 - 06:01:11 | 21.1 | CANCELLED by me (sequential 64-thread runs at 22% efficiency; 1 of 20 cfgs kept) |
| 569443 | sri_eng_strict_a7v | 2 | amdq | 06:01:28 - 06:51:22 | 100.9 | COMPLETED (packed, 10 workers x 6 threads) |
| 569446 | sri_eng_plan_6digit_topup1 | 1 | amdq | 06:40:30 - 06:41:01 | 0.6 | COMPLETED (7 cfgs, seedcheck disjoint from tier 1) |
| 569447 | sri_eng_prod_topup1 | 7 | amdq | 06:41:39 - 07:54:40 | 372.0 | 7/7 COMPLETED, exit 0:0 |
| 569448 | sri_eng_strict_deep6 | 1 (+3 pending) | amdq | 06:41:39 - 06:41:51 | 0.2 | CANCELLED by me after 12 s (would have exceeded 8 nodes); resubmitted as 569456 |
| 569456 | sri_eng_strict_deep6 | 4 (%1, raised to %3 and %4) | amdq | 06:51:22 - 08:44:47 | 249.5 | COMPLETED (packed, 7 workers x 9 threads), dependency afterany:569443 |
| | **total** | | | | **2942.9** | |

Logs: `<SCRATCH>/sri_c6c7/engine/logs/<name>_<job>_<task>.out` (copied to `logs/symmetry/`), per-cfg
engine logs `runs/<rundir>/<cfg>.log`. Peak memory (MaxRSS of a batch step) was 55 GB in production (Q8) and
35 GB in the top-up. A packed strict task reached 142 GB (7 strict Q8 processes, `maxJet 2e6`). The request was
`--mem=240G` throughout.

## 3. Timings (tier 1, engine `wall_seconds`/`cpu_seconds`; `runs/prod_6digit/production_checks.txt`)

| group | N | sectors | cfgs | engine cpu core-h | wall per cfg | planned core-h |
|---|---|---|---|---|---|---|
| Q8_base | 262139 | 2520 | 12 | 1963.7 | 2.21 - 3.08 h | 2181 |
| Q6_E | 262139 | 2520 | 1 | 116.7 | 1.82 h | 97 |
| A7_v | 64007 | 360 | 1 | 59.3 | 0.93 h | 59 |
| A7_base | 64007 | 360 | 1 | 9.6 | 9 min | 11 |
| A5_vE | 131071 | 360 | 1 | 7.0 | 6.6 min | 7 |
| Q6_d, A5_E, Q4_dE, Q6_v, ... (41 groups) | | | 70 | 12.3 | 0 s - 3.5 min | 12 |
| **all** | | | **86** | **2168.6** (99.3% of allocated) | array span 5.0 h | 2367 |

The 12 Q8 chunks (cost-balanced to 1% on the estimate) took between 7960 and 11083 s. The array ran tasks 1-8 (Q8)
first; tasks 9-12 (the other four Q8 chunks) started as those finished, so the run took two Q8 rounds.

## 4. Failures, preemption, resubmission

* No production or top-up task failed. `amdq` is not preemptible, so there were no requeues and no
  resubmissions. Every output carries `"complete": true` and no `.tmp` files were left.
* Two of my own cancellations, both of strict re-check jobs and neither a failure:
  * 569428: a single sector with 2 shifts run with 64 threads splits into point blocks, and the slowest block set
    the wall time (22% efficiency). I replaced it by `slurm/run_packed.sh` (several cfgs per node, 52-67% efficiency).
  * 569448: cancelled 12 s after it started, to stay within 8 nodes. It was resubmitted with a dependency.
* Node count: from 06:41:39 to 06:51:22, the 7-task top-up array and the 2-node A7_v strict job overlapped, so 9
  nodes ran for about 10 minutes (10 nodes for the 12 s of 569448). amdq had 13 idle nodes and nothing pending
  at that time.

## 5. Numerical warnings (engine logs)

`tests/production_checks.py` parses every `<cfg>.log`:

* No line other than the run header and the engine's `WARN sector S shift R: k of n points above the precision
  target after tails` appeared, and no output holds a non-finite number.
* Warned points are 1.11e-3 of all 9.6e9 points.
* The highest warned fractions per group:
  * A3_vdE (3D endpoint moment, sectors 8 and 9; one task has 14.6% warned): 1.6e-2
  * Q8: 2.6e-3, with the chunk of the 1040-1060 family at 1.02e-2 and the worst single task at 1.8e-2
  * A7_v: 1.7e-3
  * Q4_dE: 3.4e-4
  * A7_base: 2.4e-4
  * A3_dE and A3_vvE: 2.2e-4 and 2.1e-4
  * Q6_d: 1.4e-4
  * every other group: at most 1e-4
* The top-up groups are at 6.8e-5 overall and 2.0e-3 at most (A7_v).

A WARN marks a conservative per-point error estimate above `errTarget = 1e-13`, not an error, and section 7, criterion 5 checks this.

## 6. Collect

`python3 py/campaign.py collect runs/prod_6digit` (on the Mac after `rsync`, < 1 s) exited 0. `results.json` has
46 groups, 439 coefficients and 75 replicate blocks. It covers all 116 needed coefficients, 3 of them explicit
structural zeros (A3[eps^-1 l^1], A3[eps^2 l^1], Z4[eps^-2 l^1]), and lists no problems. `framework_input.json`
(`lri-framework-raw/1`, R = 6) has 116 scalars. `tests/e2e_framework.py` and `framework/run_framework.py` both
find all 116 required inputs.

## 7. Acceptance (README section 9), tier 1 and after the top-up

| # | criterion | tier 1 (`results.json`) | final (`results_final.json`) |
|---|---|---|---|
| 1 | complete outputs, collect exit 0, seeds disjoint | PASS | PASS (top-up collect exit 0; seedcheck top-up + tier 1 disjoint, 67050 streams) |
| 2 | `outliers.py --T 5e-5` exit 0 | PASS: 113 needed coefficients checked, 23 relevant; 3 flags, all minor (Z4_E[eps^-1 l^0], boundary sectors 8/48/50, contribution 1.7e-10 against 5e-8) | PASS on the top-up (4 coefficients, 0 flags) |
| 3 | sigma(C6), sigma(C7) <= T by sigma_rep and sigma_cov; framework's own replicate assembly agrees; nonlinearity small | C6 PASS (2.7e-6 / 2.9e-6); **C7 FAIL** (sigma_rep 5.9e-5, sigma_cov 4.6e-5, sector-pooled 5.9e-5) | **PASS**: C6 1.45e-6 / 1.33e-6 (pooled 1.28e-6); C7 3.11e-5 / 2.66e-5 (pooled 3.14e-5); `run_framework.py --raw framework_input_final.json`: C6 sig_lin 1.33e-6, sig_rep 1.45e-6; C7 2.66e-5 / 3.11e-5; nonlinearity <= 1e-18 |
| 4 | higher-log checks and cancellation of eps^{<0} terms with replicate errors | not run here: it compares with exact higher-log values, which is assembly work for the next phase | |
| 5 | strict re-evaluation of the 20 deepest Q8 and A7_v sectors agrees; WARN fraction < 1% | PASS for the numerics (68 sectors, below). WARN: 0.11% overall; A3_vdE alone is at 1.6% and its two warned sectors agree with strict numerics to 4e-16 | top-up WARN 0.007% |
| 6 | tier 2 vs tier 1 | n/a. Tier 1 vs top-up (independent seeds, N and 2N) is the analogous check: needed coefficients pull -0.89, 1.53, 2.21, 1.19 (replicate errors) and -0.63, 1.29, 1.81, 0.53 (pooled) for A5_vE, Q6_E, A7, A7_v; all 25 coefficients of the 4 groups rms 1.30, one above 3 (A5_vE[eps^0 l^2] = 3.48, not needed) | |
| 7 | archive comparison | not done here (by design) | |

**Strict re-evaluations** (`tests/strict_recheck.py`): same cfg, lattice and seed (and hence identical random
shifts) restricted to one sector and its first shifts, with `errTarget 1e-16, tailTol 1e-16, maxJet 2e6,
tailMax 0.05`. The default and strict per-sector per-shift values are compared through the exact coefficient map.
Outputs are in `runs/prod_6digit_strict/{lowdim,a7v,deep6}/strict_compare.{txt,json}`.

| set | sectors x shifts | worst coefficient difference / sector L1 size | / quoted error (stat + floor) | strict / default cpu | strict cpu |
|---|---|---|---|---|---|
| deep6: the 20 most-warned Q8 sectors (families 1047-1055, 1248-1264, 2357-2375) + 5 Q6_E | 25 x 1 | 1.5e-13 (Q8 sector 2357; the other 24 below 1e-14) | 6.1e-7 | 3.7 - 13.1 | 97.2 core-h |
| a7v: the 20 most-warned A7_v sectors | 20 x 2 | 2.5e-16 | 2.0e-8 | 11.6 - 18.9 | 38.0 core-h |
| lowdim: A3_vdE/dE/vvE (sectors 8, 9), Q4_dE, A7_base (10), Q6_d (5), Q6_v, Q6 (k=0,1), Z6, Z6_v, A5_vd, A5_vE, A5_vv, Q4_dd | 43 x 6 | 5.6e-16 | 1.4e-2 (Q4_dd[l^1], inside its floor) | 1.0 - 5.3 | 6.1 core-h |

All agree at double rounding or, for a few deep Q8 sectors, within the default per-point target of 1e-13. No
difference matters at the statistical level (at most 6e-7 of the error).

**Replicate vs sector-pooled errors** (gate-review recommendation (i), `production_checks.py`). In tier 1 the
ratio E_rep/E_pool over the 41 needed coefficients with at least 10 sectors has median 0.85, rms 0.90 and range
0.36-1.57. The pooled estimate (hundreds of degrees of freedom) is the conservative one. The largest discrepancy
was A7_v[eps^0 l^1]: 8.9e-5 replicate against 2.0e-4 pooled, with the variance spread over sectors (top 10 = 28%),
so it is a low replicate fluctuation (5 dof). For the top-up groups the ratios are 0.71-1.22.

**Inspection with `--fac 10 --share 0.2`** (gate-review recommendation (ii)):
* tier 1: 47 flags, all boundary sectors of endpoint moments. 20 are on relevant coefficients: A5_vE (11 sectors at
  20-40% each), Q4_E[eps^0 l^0] (4), A5_E (2), A3_vvE (2) and A3_dE (1). The 27 minor ones are on Z4_E[eps^-1],
  Q4_E[eps^1], Q4_dE, A3_vdE and A3_vE. Apart from A5_vE (1.2e-5), each of these coefficients contributes at most
  2e-6 to sigma(C7).
* top-up: 6 A5_vE boundary sectors (113-115 family), contributing 9.5e-7 to sigma(C7)

These are the known slow endpoint pattern, and the top-up reduced the A5_vE contribution from 1.2e-5 to 9.5e-7.

**e2e gradient check.** `tests/e2e_framework.py` exits 3 ("GRADIENT CONVENTION CHECK FAILED", relative fd/linear
mismatch 1e-4 for C6 in tier 1 and 9e-4 in the final). The cause is its fixed step h = 1e-3 x sigma: at
production errors the central difference reaches an absolute noise floor of about 1e-13 in the framework, which
does not depend on dps. Along the same random direction, h = 0.1, 1 and 10 give 1.8e-5, 1.9e-6 and 1.2e-7 (C6)
and 6e-7, 6e-8 and 2e-9 (C7) at dps 30, while the framework's nonlinearity is at most 1e-18. The gradient
convention is therefore correct. The sigma values above are unaffected, because they do not use the fd check.
The script is unchanged; making h adaptive is listed under open items.

## 8. Top-up (`runs/prod_6digit_topup1`, tier name `6digit_topup1`, fresh seeds)

**Choice.** I re-ran the planner's model with the tier-1 data as reference, in a scratch copy so the tier-1
spec and plan were not overwritten (output kept as `results/production_plan_topup1.md`). Sources were `runs/prod_6digit` plus the regression runs. With a safety target
of 3e-5 (the sampling error of a 5-dof sigma is about 30%), its greedy allocation raised Q6_E 262139 -> 524287 and
A5_vE 131071 -> 262139, predicting sigma(C7) = 3.0e-5. I also moved A7_v and A7_base 64007 -> 131071, because of
A7_v's pooled-vs-replicate discrepancy (pooled C7 projection 2.5e-5). Q8 was not topped up: one ladder step would
cost about 4000 core-h for about 2e-5.

| group | N tier 1 -> top-up | cfgs | engine cpu core-h | wall | C7 projection rep / pooled, tier 1 -> top-up |
|---|---|---|---|---|---|
| Q6_E | 262139 -> 524287 | 3 | 226.2 | 1.13 - 1.22 h | 3.3e-5 / 3.9e-5 -> 3.1e-6 / 2.5e-6 |
| A7_v | 64007 -> 131071 | 2 | 111.7 | 0.78 - 0.97 h | 1.1e-5 / 2.5e-5 -> 1.4e-6 / 1.1e-6 |
| A7_base | 64007 -> 131071 | 1 | 19.3 | 18 min | 5.3e-6 / 6.5e-6 -> 6.9e-7 / 9.7e-7 (C6: 2.5e-6 -> 3.3e-7) |
| A5_vE | 131071 -> 262139 | 1 | 13.6 | 13 min | 1.2e-5 / 1.7e-5 -> 9.5e-7 / 1.0e-6 |

`py/merge_runs.py runs/prod_6digit runs/prod_6digit_topup1 --tag final` replaces those four groups whole: every
eps power, replicate, error and covariance block. Nothing is averaged, and R = 6 is kept. I verified that every
other group is byte-identical to `results.json` and that the block set is unchanged.

**Final error budget of C7** (pooled, statistical):

| source | contribution |
|---|---|
| Q8 | 3.1e-5 (replicate 2.6e-5) |
| Q6_E | 2.5e-6 |
| Q6_v | 2.8e-6 |
| Q6 | 1.8e-6 |
| A5_E | 1.8e-6 |
| everything else | <= 1.2e-6 each |

A further reduction of C7 needs Q8 at N = 524287 (tier 2).

## 9. Deliverables

| file | content |
|---|---|
| `runs/prod_6digit/results.json`, `framework_input.json` | tier 1 as collected: per-replicate coefficients (R = 6), errors (stat, floor, L1), blocks, structural zeros |
| `runs/prod_6digit/results_final.json`, `framework_input_final.json` | **tier 1 + top-up** (the 4 groups replaced; `merged` records the source of each replaced group); input for the C6/C7 assembly |
| `runs/prod_6digit/sigma_summary.json` | error estimates only (sigma_rep, sigma_cov, floor, sector-pooled; tier 1 and final), with no values and no comparisons |
| `runs/prod_6digit/production_checks.{json,txt}`, `outliers*.txt`, `flags*.json`, `collect.log` | health, WARN and error cross-checks, acceptance outputs |
| `runs/prod_6digit_topup1/` | top-up run: cfgs, outputs, logs, `results.json`, `framework_input.json`, checks |
| `runs/prod_6digit_strict/{lowdim,a7v,deep6}/` | strict re-evaluations and `strict_compare.{txt,json}` |
| `specs/production_6digit_topup1.json` | top-up spec |
| `logs/symmetry/sri_eng_{plan_6digit,prod,prod_topup1,plan_6digit_topup1,strict_*}_*.out`, `sacct_*.txt` | Slurm logs and accounting |
| `tests/production_checks.py`, `tests/strict_recheck.py`, `py/merge_runs.py`, `slurm/run_packed.sh`, `slurm/packed_symmetry.sbatch` | new tools (README sections 5 and 7) |

Remote copies of all run directories are under `<SCRATCH>/sri_c6c7/engine/runs/`.

## 10. Open items

* C7 is now Q8-limited (sigma 2.6e-5 replicate, 3.1e-5 pooled). Tier 2 must re-plan Q8 from these data. The
  rate the planner infers from the full-sector runs is 2.06 between N = 1009 and 262139, but N = 1009 is
  pre-asymptotic. The pilot sample gave 3.7 between 16001 and 64007.
* The e2e fd check needs an adaptive step (section 7). Its exit 3 is a false alarm.
* Criterion 4 (higher logs, cancellation of eps^{<0}) belongs to the assembly phase.
* The R = 6 replicate errors run low on average against the sector-pooled ones (median ratio 0.85). Quoting
  max(sigma_rep, sigma_cov, sigma_pool) for C7 (3.1e-5) is the conservative choice.
