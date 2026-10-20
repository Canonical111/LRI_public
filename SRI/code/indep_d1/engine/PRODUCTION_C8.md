# C8 production: log (tiers A, B and C done; section 13 for B and C)

Sections 1-11: tier A (W, S, L3, M21, M12, N2, Ndelta). Section 12: tiers B (U, Kv) and C (J9), prepared on
2026-10-04 with a budget guard. Section 13: their production, 2026-10-04 21:20 EDT to 2026-10-07 11:22 EDT.

**Tiers B and C, outcome (section 13).**
* sigma(C8 part of tier B) = 5.1e-3, so sigma(C8 without J9) = 5.1e-3 against the approved 0.01.
* sigma(C8 part of tier C) = 2.4 (largest estimator) against the approved gross target of ~3.
* The framework at order C8 is complete: C8 = 242.83 +- 2.4.
* Cost: 19,126.8 of the 20,000 amdq-equivalent core-h cap.
* Checks:
  * `validate_C8.py`: 0 checks above 3 and 0 not computable (the C9 pole at eps^-1 was confirmed at N = 4001);
  * the exact scalars PASS;
  * the strict re-checks agree, except Q8_v, which has no result: its job was cancelled from outside (13k, item 8).
* Deliverables, with SHA-256s in `runs/c8BC_SHA256SUMS.txt`:
  * `runs/c8tierB_s0.01_r1/framework_input_final.json`;
  * `runs/c8tierC_s3_r2/framework_input_final.json`;
  * `runs/c8tiersABC/framework_input_final.json`.
* No archive value was read or compared in the engine production.
* **Assembly and sealed comparison: done 2026-10-07** (`../RESULTS_C8.md`, section 13l): C8 = 242.825 +- 2.37 against the
  claim 247.381 (-1.92 sigma), the whole difference in A9[eps^0 l^1] (-20.4 +- 9.3); C8 - J9/4 agrees to -1.0e-3 +- 5.1e-3.
  One assembly check run on amdq (`runs/c8chkA7`, 10.6 core-h): phase total about 19,139 of 20,000.

2026-10-03/04. Tier A ran on **the personal desktop**, because symmetry was down for the whole run: every node, amdq, defq and
debugq included, had "unexpectedly rebooted" at 13:22 EDT on 2026-10-03, and was still down at 06:40 EDT on
2026-10-04, after the last production cfg had started. At 13:55 EDT on 2026-10-04 it was back (amdq: 7 idle nodes;
defq: 17 idle nodes). Expanse was not used. Tiers B and C were not run then (they ran 2026-10-04/06, section 13). No archive value was read or compared here.

**Outcome.**

* All 21 planned cfgs of `specs/production_C8_tierA.json` ran as planned (same spec, N, R = 6, seeds from the tier
  name `c8tierA`), every one with rc 0.
* `collect` exits 0 and `outliers.py --T 1e-5` exits 0. Seeds are disjoint from every earlier campaign.
* The WARN fraction is 0.80 % (criterion: below 1 %). The strict-tolerance re-checks of the most-warned sectors of
  A3_ddE, Q4_vdE, Q4_vvE, Q4_vdd and Q6_vv agree with production to at most 8e-17 of the sector size. The Q6_vd
  re-check is incomplete (see below).
* **sigma(C8 part of tier A) = 5.03e-7**, against the plan's 7.46e-7. With B_old (1.16e-5) in quadrature it is
  1.161e-5.
* One job missed its planned error by more than 1.5x: A3_ddE, by 1.69x. It was topped up at 2N with fresh seeds
  (tier `c8tierA_topup1`) and is now at 0.27x its budget. Every other job is at or below 1.25x.
* Cost: **183.1 allocated personal-desktop core-hours, which is 122.2 amdq-equivalent core-hours** at the plan's measured
  conversion of 0.667 amdq core-h per personal-desktop core-h.
  * Production alone (tier A plus the top-up and two lattice searches) took 154.5 personal-desktop core-h. Its engine cpu,
    converted to amdq units (101.8), is 2.4 % below the plan's prediction (104.3).
  * Strict re-checks took 28.6 personal-desktop core-h. Of that, 23.8 went to two jobs I cancelled without a result.
  * Against the 156 core-h cap: the amdq-equivalent total (122.2) is under it, but **the raw personal-desktop total
    (183.1) is over it**. See section 2 and the open items.
* **The Q6_vd strict re-check is incomplete.** The most-warned Q6_vd sector (36, one shift) ran for 5.0 h on 4
  cores. Seven of its eight point blocks finished, but the last block was still running on one thread, and the
  engine writes results only at the end. I cancelled it (job 274, 20.1 core-h) to stop the cost growing.
  Q6_vv, which has the same 4D Q6 sector geometry, passed its strict re-check at 5.6e-17.
* **Deliverables:** `runs/c8tierA/results_final.json` and **`runs/c8tierA/framework_input_final.json`** (tier A with
  the A3_ddE top-up; 26 needed scalars, R = 6). These are the tier-A input of the C8 assembly.

## 1. What ran (code identity)

| item | value |
|---|---|
| engine | `bin/lri_engine` md5 `ec238e0fa37b` on the personal desktop, built from `src/lri_engine.cpp` md5 `edfa65dce4d6`. This is the same binary md5 as on symmetry and the same one used for tier 1 and the C8 pilots. |
| sources | `src/ py/ slurm/ specs/ tests/` were md5-identical on the Mac and on the personal desktop (`<DATA>/<USER>/sri_c6c7/engine`) before launch (79 files) |
| spec | `specs/production_C8_tierA.json` (sha256 `17a35380...`), unchanged from `py/plan_C8.py` -> `py/make_spec_C8.py tier` |
| plan | `campaign.py plan specs/production_C8_tierA.json runs/c8tierA` gave 21 cfgs. They are identical to the dry run (`results/dryrun_tiers_C8.txt`) except for the two lattices that the dry run had as dummies. Manifest sha256 `77f3fc15...`, `cfglist.txt` sha256 `5e2fe2af...` |
| lattices | Two new weighted-P2 Korobov generators, searched by job 258 on a personal-desktop compute node (`lri_engine --korobov N d 2000`, 69 s): `370759_4: 336045` and `741457_4: 288024`. The top-up needed `524287_3: 152496` (job 264, 39 s). All three are in `py/korobov_db_g01.json` (md5 `23b50f2b...`) on the Mac, on the personal desktop and on symmetry. |
| seeds | hash(`c8tierA` or `c8tierA_topup1`, group, k, chunk). `campaign.py seedcheck` over c8tierA, c8tierA_topup1, prod_6digit, prod_6digit_topup1, poles1, kplus1, conv1, c8val, c8conv, c8kplus1 and regress_v2/new: 1,195,554 streams, all disjoint. A cross-check of the 1806 tier-A streams against all 26 earlier run directories (pilots, strict and regression included) found no overlap. |

Planning ran on the Mac. It needs sympy, which the personal desktop lacks in its system Python. The pilots were planned the same
way. All it did there was read the cached lattices and run the engine's `--sectors-info` cost probe, which takes about
1 s. Both lattice searches ran on the personal desktop through Slurm.

## 2. Machine choice and the core-hour cap

* **Symmetry** had every node down (`sinfo`: amdq 29 down, defq 26 down, debugq 34 down; reason "Node unexpectedly
  rebooted"). It was checked at submission (21:08 EDT, 2026-10-03), at each decision point, and every 2 min by the
  pollers. It did not come back before production ended; it was back at 13:55 EDT on 2026-10-04.
* **The personal desktop** had 16 of its 32 cores free (the user's job 155 holds the other 16).
  * The production jobs took 14 cores, which left 2 for short jobs (strict re-checks, lattice searches).
  * `--time=0` was used throughout, and `scontrol` showed `TimeLimit=UNLIMITED` for every job.
  * Data lives under `<DATA>/<USER>/sri_c6c7/engine`.
* **Order.** The 20 cheaper cfgs (job 259) ran first, and Q6_vd, which is 68% of the plan, ran second (job 260,
  `afterok`). Running them in this order left time to move Q6_vd to symmetry amdq if the cluster came back before
  it started. It did not come back, so Q6_vd ran on the personal desktop as well. Outputs are machine-independent: the
  calibration in `runs/calib_personal-desktop` reproduced amdq replicates bitwise.
* **The cap (156 core-h = 1.5 x the planned 104.3).**
  * The plan is in amdq core-hours, converted from personal-desktop pilot timings with the measured speed factor 0.667
    (`results/plan_C8.md`).
  * The same work on the personal desktop therefore costs about 1.5x more raw core-hours. The plan's own tier-A prediction in
    personal-desktop units is 156.4 core-h.
  * I applied the cap in the plan's units (amdq-equivalent = personal-desktop x 0.667) and report both numbers below.
  * In raw personal-desktop core-hours the total is over 156. Production and top-up alone stayed under it (154.5); the strict
    re-checks pushed it over (+28.6, including 23.8 for two cancelled jobs).
  * Whether this reading of the cap is acceptable is for the orchestrator to decide (open item 1).

## 3. Jobs (the personal desktop has no Slurm accounting; times from `scontrol`/job logs; core-h = allocated CPUs x wall)

| job | name | CPUs | start - end (CEST, 2026-10-04) | wall | allocated core-h | state / content |
|---|---|---|---|---|---|---|
| 258 | sri_eng_c8A_lattice | 2 | 03:12:04 - 03:13:13 | 69 s | 0.04 | COMPLETED: Korobov 370759_4, 741457_4 |
| 259 | sri_eng_c8A_can1 | 14 | 03:15:11 - 06:56:09 | 3.68 h | 51.56 | COMPLETED: 20 cfgs (`cfglist_can1.txt`: 17 small, Q4_vdE, A5_dd, Q6_vv), all rc 0 |
| 260 | sri_eng_c8A_q6vd | 14 | 06:56:09 - 14:14:57 | 7.31 h | 102.39 | COMPLETED: Q6_vd (`cfglist_q6vd.txt`), rc 0; `--dependency=afterok:259` |
| 261 | sri_eng_c8A_strict_lowdim | 2 | 04:30:07 - 06:21:55 | 1.86 h | 3.73 | CANCELLED by me (see 6) |
| 262 | sri_eng_c8A_strict_lowdim | 2 | 06:22:09 - 06:24:39 | 150 s | 0.08 | COMPLETED: 12 strict cfgs |
| 263 | sri_eng_c8A_strict_q6vv | 2 | 06:57:27 - 09:18:41 | 2.35 h | 4.71 | COMPLETED: 2 strict cfgs |
| 264 | sri_eng_c8A_lattice2 | 1 | 09:18:42 - 09:19:21 | 39 s | 0.01 | COMPLETED: Korobov 524287_3 |
| 265 | sri_eng_c8A_topup1 | 2 | 09:20:27 - 09:35:57 | 930 s | 0.52 | COMPLETED: A3_ddE at N = 524287, rc 0 |
| 274 | sri_eng_c8A_strict_q6vd | 4 | 14:52:41 - 19:54:16 | 5.03 h | 20.11 | CANCELLED by me: no result (see 6) |
| | **total** | | | | **183.1** (122.2 amdq-equivalent) | |

* Breakdown:
  * production 154.0 (258 + 259 + 260);
  * top-up 0.53 (264 + 265);
  * strict re-checks 28.6 (261 + 262 + 263 + 274), of which 23.8 is the cancelled jobs 261 and 274.
* Logs:
  * Slurm logs: `<DATA>/<USER>/sri_c6c7/engine/logs/sri_eng_c8A_*_<job>.out`, copied to `logs/personal-desktop/`.
  * Per-cfg engine logs: `runs/c8tierA/<cfg>.log`.
* Engine efficiency: the engine's cpu for the 21 tier-A cfgs is 152.7 core-h, which is 99.2 % of the 154.0
  allocated. Peak memory per process was about 8 GB (Q6_vd at 14 threads). Each job requested `--mem=60G` (strict
  jobs: 20-24G).

## 4. Timings: plan vs measured (engine cpu)

| cfg | N | wall (14 thr) | engine cpu personal-desktop core-h | x 0.667 = amdq-eq | planned amdq core-h | measured / planned |
|---|---|---|---|---|---|---|
| Q6_vd | 262139 | 26327 s | 101.79 | 67.9 | 68.39 | 0.99 |
| Q6_vv | 370759 | 9074 s | 35.05 | 23.4 | 23.93 | 0.98 |
| Q4_vdE | 741457 | 1862 s | 7.23 | 4.82 | 4.83 | 1.00 |
| A5_dd | 262139 | 1621 s | 6.09 | 4.06 | 5.53 | 0.73 |
| 17 others | | 701 s in all | 2.53 | 1.69 | 1.67 | 1.01 |
| **tier A** | | **11.0 h** | **152.7** | **101.8** | **104.3** | **0.98** |
| A3_ddE top-up | 524287 | 930 s (2 thr) | 0.52 | 0.35 | (0.35 = 2 x 0.17) | 1.0 |

The planner's personal-desktop-based cost model held to 1-2 % for the 4D groups. A5_dd ran 27 % cheaper than planned.

## 5. Collect, outliers, health

* **Collect.** `campaign.py collect runs/c8tierA --need specs/production_C8_need.json` exits 0 (log `collect.log`):
  * `results.json` holds 19 groups, 21 jobs (blocks) and 203 coefficients (all log powers >= jmin);
  * `framework_input.json` (`lri-framework-raw/1`, R = 6) holds the **26 needed scalars**;
  * none of them is a structural zero.
* **Outliers (acceptance).** `outliers.py runs/c8tierA --grad specs/gradients_C8.json --T 1e-5` exits 0:
  * 26 needed coefficients checked, 6 of them relevant at T = 1e-5;
  * 0 flagged sectors (`outliers.txt`, `flags.json`).
* **Outliers (inspection).** With `--fac 10 --share 0.2`, 9 sectors are flagged (`outliers_inspect.txt`):
  * Q4_vdE sectors 0, 2, 8, 12, 13, 14;
  * Q4_vvE sectors 3 and 15;
  * Q6_vv sector 24.
  * Each carries 30-60 % of its coefficient's error, and each coefficient contributes 1.2-1.7e-8 to sigma(C8). This
    is the known boundary-sector pattern of endpoint moments.
  * None of these is worth a refinement: their sum in quadrature is below 3e-8, while the tier total is 5.0e-7.
* **Health.** `tests/production_checks.py` exits 0 (`production_checks.{txt,json}`):
  * all 21 outputs complete, no non-finite number, no unexpected log line;
  * replicate vs sector-pooled error over the 7 needed coefficients with >= 10 sectors: ratio median 0.88, rms 1.12,
    range 0.68-1.60.
* **WARN.** 5,836,290 of 7.32e8 points are warned, i.e. **0.80 %** overall (criterion 5: < 1 %). Per cfg:
  * A3_ddE 5.0 % (sectors 8 and 9: 30 % of their points);
  * Q4_vdE 1.7 % (6 boundary sectors at 17 %);
  * Q6_vd 0.21 % (worst task 0.78 %);
  * A5_dd 0.094 %;
  * Q6_vv 0.058 %;
  * Q4_vvE 0.034 %;
  * everything else 9e-5 or less.

## 6. Strict-tolerance re-checks (`tests/strict_recheck.py`; same cfg, lattice, seed and shifts; errTarget/tailTol 1e-16, maxJet 2e6, tailMax 0.05)

| set (dir `runs/c8tierA_strict/...`) | sectors x shifts | worst coefficient difference / sector L1 | / quoted error | strict / default cpu |
|---|---|---|---|---|
| lowdim: A3_ddE 8, 9 (x6); Q4_vdE 57, 38, 32, 56, 33, 39 (x2); Q4_vvE 39, 32, 33 (x2); Q4_vdd 2 (x2) | 12 sectors | 8.0e-17 (Q4_vdd); **all A3_ddE, Q4_vdE, Q4_vvE values bitwise identical** | 9.6e-3 (Q4_vdd, inside its floor). The difference is 2.1 x E_rep, but E_rep of this 2D coefficient is itself at double rounding (1.5e-15 relative). | 1.0 (endpoint sectors), 1.2 (Q4_vdd) |
| q6vv: Q6_vv 36, 37 (the most-warned) | 2 x 1 | 5.6e-17 | 1.5e-5 | 11.6 |
| q6vd: Q6_vd 36 (the most-warned) | 1 x 1 | **not completed** (job 274 cancelled after 5.0 h; see below) | - | > 11.8 (444 cpu-min against 37.6 default) |

* The most-warned sectors of all, the endpoint boundary sectors of A3_ddE and Q4_vdE, behave the same way with strict
  numerics:
  * the warned count rises (A3_ddE sector 9: 79k to 223k points per shift);
  * the value stays **bitwise identical**, at the same cpu.
* The warning there marks a conservative jet-error estimate that no tail or jet refinement changes. It does not mark a
  numerical error.
* The cancelled job 261 contained 3 A5_dd sectors x 2 shifts and 3 Q4_vdd sectors x 6 shifts, in cost order:
  * after 1.9 h the first two A5_dd strict cfgs had passed 8x their default cpu and were still running, while the
    cheap, most-warned endpoint sectors waited behind them;
  * A5_dd has a WARN fraction of 0.09 % and a sigma_C8 of 5e-9, so I dropped it and kept one Q4_vdd sector (job 262).
* The Q6_vd re-check (job 274; 1 worker x 4 threads) did not complete.
  * The engine splits a single sector-shift into 8 point blocks of 32768 points.
  * Seven blocks finished within 71 min. They warned 113-1328 points each, 3576 in all, against 2029 for the whole
    sector at default numerics.
  * The eighth block was still running on a single thread after 5.0 h (about 310 cpu-min on that block alone).
  * The engine writes per-sector values only at the end of a cfg, so the finished blocks give no comparison.
  * I cancelled the job at 20.1 core-h. A rerun would need either the whole sector on 1 core (expected well over 7 h)
    or a per-block output in the engine.
  * This leaves criterion 5 unchecked for the Q6_vd job. That job dominates the tier-A error, and through Q6_vd its
    Ndelta, but its WARN fraction is only 0.21 %. Q6_vv, with the same 4D Q6 geometry, passed at 5.6e-17.

## 7. Budget per job: achieved vs planned sigma (`tests/budget_C8.py`, new)

The projection of every job's needed coefficients on the signed dC8/dx is computed the same way as in the planner
(`py/plan_C8.load_refs`): the larger of the replicate and sector-pooled errors, plus the floor. Output:
`runs/c8tierA/budget_C8{,_final}.{txt,json}`.

| job | N | sigma_C8 rep | pooled | achieved | planned | ratio |
|---|---|---|---|---|---|---|
| Q6_vv | 370759 | 4.03e-7 | 2.54e-7 | 4.03e-7 | 4.83e-7 | 0.84 |
| Q6_vd | 262139 | 2.12e-7 | 3.00e-7 | 3.00e-7 | 5.20e-7 | 0.58 |
| A3_ddE (tier A) | 262139 | 1.79e-8 | 2.65e-8 | 2.65e-8 | 1.57e-8 | **1.69 (MISS)** |
| A3_ddE (top-up) | 524287 | 2.56e-9 | 4.28e-9 | 4.28e-9 | 1.57e-8 | 0.27 |
| Q4_vvE | 262139 | 1.74e-8 | 1.98e-8 | 1.98e-8 | 1.02e-7 | 0.19 |
| Q4_vdE | 741457 | 1.19e-8 | 1.50e-8 | 1.50e-8 | 2.04e-7 | 0.07 |
| A5_dd | 262139 | 5.06e-9 | 4.32e-9 | 5.06e-9 | 4.05e-9 | 1.25 |
| 15 others (1-2D) | | | | <= 3.0e-9 each | | 1.00 (floor-dominated) |
| **tier A, final** | | 4.56e-7 | 3.94e-7 | **5.03e-7** | 7.46e-7 | 0.67 |

* **A3_ddE miss.** A3_ddE is a 3D endpoint moment. The plan extrapolated it from c8val at N = 64007 with the default
  3D rate 3.0. The measured rate between 64007 and 262139 is 2.3-2.6.
* **Top-up.** `specs/production_C8_tierA_topup1.json` (tier name `c8tierA_topup1`, fresh seeds) reran the whole job at
  N = 524287, which costs 0.52 personal-desktop core-h.
  * The top-up value differs from tier A by 1.65 sigma.
  * `python3 py/merge_runs.py runs/c8tierA runs/c8tierA_topup1 --tag final --need specs/production_C8_need.json`
    replaces the whole A3_ddE group. Every other group is taken from tier A unchanged.
* **No other job missed.** A5_dd is at 1.25x, inside the 1.5x margin, and contributes 5e-9.
* **Inputs.** Engine part of the tier-A inputs from these jobs (plan, main: W 1.1e-10, S 8.1e-9, L3 8.9e-11, M21
  1.2e-9, M12 6.0e-9, N2 1.7e-6, Ndelta 4.5e-6):

  | input | sigma | dominant job |
  |---|---|---|
  | W | 1.1e-10 | |
  | S | 3.4e-9 | |
  | L3 | 8.9e-11 | |
  | M21 | 1.2e-9 | |
  | M12 | 6.0e-9 | |
  | N2 | 3.9e-7 | Q4_vvE, Q6_vv |
  | Ndelta | 2.4e-6 | Q6_vd |

  Tier A's Q6_vv also carries a 1.25e-5 part of Kv. Kv belongs to tier B (whose Q8_v term dominates it, with a planned
  sigma of 0.13), so it is not a tier-A target.

## 8. Consistency with the earlier, independent runs (`tests/tier_vs_pilot_C8.py`, new; `runs/c8tierA/tier_vs_pilot.{txt,json}`)

* **Comparisons.** There are 33 comparisons of tier-A needed coefficients with the same job in c8val, c8conv (all
  sectors), c8kplus1, poles1 and kplus1. The seeds are disjoint.
* **Pulls.** With the quoted errors (stat (+) floor): rms 0.48, max 1.46 (Q6_vv[eps^0 l^1] against c8conv N = 4001).
* **Statistically resolved coefficients.** A3_ddE, Q4_vdE, Q4_vvE, A5_dd, Q6_vd and Q6_vv against the pilot sizes:
  every |pull| is at most 1.46. For example:
  * Q6_vd[eps^0 l^1] against c8conv N = 16001: +0.02;
  * Q6_vv[l^0] and [l^1] against c8conv N = 16001: -1.33 and -1.38;
  * Q4_vdE against c8conv N = 16001: -0.01.
* **1-2D groups.** Their statistical errors are at double rounding (1e-14 to 1e-15 relative), so stat-only pulls are not
  meaningful there. The one |pull_stat| > 3 is Q4_vv[eps^1 l^0] against c8val (difference 6e-13 on 160.5, and
  stat_ref = 0). The floor covers it: quoted-error pull 0.03.
* **Top-up vs tier A.** A3_ddE[eps^0 l^0]: pull +1.65.

## 9. Validation with the tier-A data (`tests/validate_C8.py`, archive-free; `results/validate_C8_tierA.{txt,json}`)

`python3 tests/validate_C8.py --run runs/c8tierA_topup1 --run runs/c8tierA --run runs/c8val --run runs/c8conv --run runs/c8kplus1 --out results/validate_C8_tierA`

* Tier A comes first so that its entries take priority: 119 of its scalars replace pilot entries.
* Results:

  | check | count | max \|pull\| | rms | notes |
  |---|---|---|---|---|
  | raw targets | 11 | 0.22 | | A3_ddd[eps^0 l^1] = -250.24866908972725 against the spec's independent three-kink value -250.24866908971532 (difference 1.2e-11, sigma 6.5e-10) |
  | pole cancellation | 996 | 2.95 | | |
  | below-tight-bound zeros | 13 | 0.00 | | |
  | C3/K4 higher logs | 120 | 0.36 | | |
  | RG second and higher logs | 97 | 2.62 | 0.81 | |

* Every check above is the same as in the pilot validation or slightly better. The C9 and d_v K8 RG logs still need
  tiers B and C.
* An earlier probe that listed tier A last picked up none of its scalars: `validate_C8.py` keeps the first entry of
  each coefficient. That probe is not kept.

## 10. Deliverables

| file | content |
|---|---|
| `runs/c8tierA/results.json`, `framework_input.json` | tier A as collected: 21 jobs, per-replicate coefficients (R = 6), errors (stat, floor, L1), blocks |
| **`runs/c8tierA/results_final.json`, `framework_input_final.json`** | **tier A + A3_ddE top-up** (`merged` records the source of each group). Input for `../framework/run_framework.py --order C8 ... --raw runs/c8tierA/framework_input_final.json` |
| `runs/c8tierA/SHA256SUMS_results.txt` | sha256 of the four files above and of the top-up's results, recorded before anyone compares them |
| `runs/c8tierA/{collect.log, outliers*.txt, flags*.json, production_checks.*, budget_C8*.{txt,json}, tier_vs_pilot.*, seedcheck.txt}` | acceptance outputs |
| `runs/c8tierA_topup1/` | top-up run: cfg, output, log, results, framework input |
| `runs/c8tierA_strict/{lowdim,q6vv,q6vd}/` | strict re-checks, `strict_compare.{txt,json}` |
| `specs/production_C8_tierA_topup1.json` | top-up spec |
| `tests/budget_C8.py`, `tests/tier_vs_pilot_C8.py` | new tools (README section 11h) |
| `logs/personal-desktop/sri_eng_c8A_*.out` | Slurm logs |
| `results/validate_C8_tierA.{txt,json}` | validation with the tier-A data |

Remote copies:
* the personal desktop: `<DATA>/<USER>/sri_c6c7/engine/runs/c8tierA{,_topup1,_strict}`;
* symmetry: `<SCRATCH>/sri_c6c7/engine/runs/` (BeeGFS is reachable through the login node while the compute
  nodes are down).

## 11. Open items

1. **The cap was applied in plan units.** The raw personal-desktop total is 183.1 core-h, which is above the 156 core-h cap;
   the amdq-equivalent total is 122.2. The orchestrator should confirm that reading. If the cap was meant in raw
   core-hours on any machine, the overrun came from the strict re-checks (production plus top-up was 154.5), and
   23.8 of it from the cancelled jobs 261 and 274.
2. **Tiers B (U, Kv) and C (J9) were not run** (prepared since, section 12; run 2026-10-04/06, section 13). By instruction, only tier A ran. Tier B (8.4k amdq core-h) cannot run on
   the personal desktop in reasonable time: about 12.7k personal-desktop core-h, i.e. about 900 h on 14 cores. Symmetry is back since
   2026-10-04 13:55 EDT.
3. **Run tier B/C on symmetry.** Each 6-7D group in tiers B and C should first get a single amdq task to confirm the
   personal-desktop-based cost model, which the 4D groups here confirmed to 1-2 %. (Done by design in section 12: the
   probe stage runs every heavy group on amdq first.)
4. **Q6_vd strict re-check missing.** Criterion 5 is not verified for Q6_vd (section 6). It can be closed by a
   strict re-run of one Q6_vd sector on one core, or of a less-warned and cheaper sector, on the personal desktop (one core, probably
   more than 8 h and 8-15 core-h). A whole amdq node (64 cores) would cost far more core-hours for a single sector,
   unless the check is packed into a tier-B strict job. I did not start it, because of the cap (open item 1).
   (Scheduled in stage P of section 12: the personal desktop, 1 core.)
5. **The endpoint-moment WARN pattern is cosmetic.** Bitwise identical under strict numerics, it inflates the WARN
   fraction (A3_ddE 5 %, Q4_vdE 1.7 %). The criterion-5 threshold could exclude sectors whose strict re-check is
   bitwise identical.

## 12. Tiers B and C: prepared 2026-10-04 (launched the same evening, section 13)

**Approval (user, 2026-10-04).** Tier B at sigma(C8 without J9) = 0.01 and tier C as a GROSS check at total
sigma(C8) ~ 3. **Hard cap for the whole phase** (production, probes, checks, strict re-checks, top-ups): **20,000
amdq-equivalent core-hours** = symmetry amdq allocated core-h + 0.667 x the personal desktop (or symmetry Intel) allocated
core-h. Before the cap would be exceeded the phase stops and reports the precision reached. Machines: symmetry amdq
(then defq, never longq; at most 8 of our nodes), the personal desktop for the cheap groups (`--time=0`, about 16 free cores);
no Expanse. At the time of writing, nothing of this section had run except one lattice search (job 276 on the personal desktop, 0.045 core-h); production: section 13.

### 12a. Specs (all regenerated from the planner, hashes recorded)

| spec | tier name (seeds) | content | amdq core-h (plan) | sha256 |
|---|---|---|---|---|
| `specs/production_C8_tierB_sigma0.01.json` | `c8tierB_s0.01` | 24 jobs, 53 cfgs; sigma(C8 w/o J9) 8.84e-3 (engine part of U 2.7e-3, Kv 0.28) | 5,904 | `da55f683ef87` |
| `specs/production_C8_tierC_sigma3.json` (**new**) | `c8tierC_s3` | 21 jobs, 59 cfgs; tier-C sigma 2.50 (J9 10.0), total sigma(C8) 2.50 | 7,641 | `c8b7b2543364` |
| `specs/production_C8_tier{B_sigma0.01,C_sigma3}_{sym,can}.json` (**new**) | same as the parent | machine split: `_sym` = jobs >= 50 core-h (B: Q8_v, Q6_vE, A7_d 5,886; C: A9, A7_E, Z8 7,609), `_can` = the rest (B: 21 jobs 18.4; C: 18 jobs 32.2) | | `9d8831c2`, `97a86a75`, `a0fd95a0`, `c634fbd3` |
| `specs/probe_C8_BC.json` (**new**) | `c8probeBC` | 7 heavy jobs at their planned N on the conv pilot's sector samples (budget guard, 12c) | ~94 | `481f6695960d` |
| `specs/checks_C8_BC.json` (**new**) | `c8chkBC` | A9 and Z8 at eps^-1, all logs, all sectors, N = 1009 (C9 pole check) | ~59 | `1a39bde2b4ce` |

* **Tier B 0.01 is current.** `py/plan_C8.py --TB 0.01 --alt 1` (the phase-3 command) reproduces
  `results/plan_C8_alt_TB0.01.json` exactly (apart from the source paths) and `make_spec_C8.py tier` reproduces
  `specs/production_C8_tierB_sigma0.01.json` byte for byte; the new tier-C plan gives the same tier-B spec. Tier A's
  achieved sigma (5.0e-7 against 7.5e-7 planned) does not change any tier-B/C allocation.
* **Tier C at sigma(C8) ~ 3.** `py/plan_C8.py --src runs/c8conv --src runs/c8val --src runs/poles1 --src runs/kplus1
  --src runs/prod_6digit --speed 0.667 --TB 0.01 --T 3 --alt 1,2,5,10 --budget-BC 19000 --out
  results/plan_C8_alt_TB0.01_T3`, then `py/make_spec_C8.py tier --plan results/plan_C8_alt_TB0.01_T3.json
  --tier-name C --tier c8tierC_s3`. Jobs (N, chunks, core-h, sigma_C8): A9[eps^0 l^1] 8009, 36, 6,828, 2.3;
  A7_E[eps^0 l^0] 11321, 4, 719, 0.92; Z8 5669, 1, 63, 0.30; Z6_E 5669, 1, 16, 0.24; A7_v 11321, 9.4, 0.073; the rest
  < 3 core-h each. Cost curve of tier C (with B at 0.01): sigma(C8) 1: 15,256; 2: 10,795; 3: 7,641; 5: 5,410;
  10: 3,837 core-h.
* **Machine split.** `py/split_C8BC.py split` (new) keeps every entry and the tier name, so the halves plan to exactly
  the cfgs and seeds of the unsplit spec (checked: 53 + 59 cfgs byte-identical). `py/split_C8BC.py order` puts the first
  chunk of every heavy job at the head of the symmetry array list.
* **Lattices.** 21 new weighted-P2 Korobov generators (all production, probe and check sizes, plus the ladder
  neighbours of every heavy group for re-plans and reductions: d = 5: 5669-91621; d = 6: 5669-185363; d = 7:
  5669-32003) were searched by job 276 on the personal desktop (`slurm/korobov_personal-desktop.sbatch`, 3 min) and merged
  (`tests/budget_guard_C8.py lattices --merge`); `py/korobov_db_g01.json` (62 entries, md5 `e295a6a4`) is identical on
  the Mac, symmetry and the personal desktop. `lattices --check` (also inside `submit_C8BC.sh`) refuses to plan a spec whose
  lattice is not cached, so no search ever runs on the Mac.
* **Seeds.** All four new campaigns planned into a scratch directory (`tests/dryrun_tiers.py`): 53 + 59 + 7 + 2 cfgs;
  459,114 new random streams against 1,372,750 of all 21 earlier run directories (tier A, its top-up and strict
  replays, pilots included): **0 overlaps**.

### 12b. The four exact tier-C scalars (mathematics verifier)

`A3[eps^3 l^1] = 0`, `A3[eps^3 l^0] = -5/9`, `A5[eps^-2 l^1] = 0`, `Z6[eps^-3 l^1] = 0` are all **computed by the engine
inside tier C** (`A3_base k=3`, `A5_base k=-2`, `Z6_base k=-3`, coeffs [0, 1], in `_can`, about 0.1 core-h). The three
l^1 entries come out of `collect` as explicit exact zeros (`zero` flag, `zeros` list, `{"value": "0", "sigma": "0",
"exact": true}`), never as absent scalars. `tests/exact_scalars_C8.py` (new; `specs/exact_scalars_C8.json`) documents and
checks why:
* **Pole bound (structural).** The engine's Hepp-sector analysis (`--sectors-info`) gives at most one subtracted
  variable in every sector of A3 at eps^3 (1 sector), A5 at eps^-2 (12) and Z6 at eps^-3 (60), so with the exact Laurent
  prefactors the lowest Laurent order is -1 and the order -2 (l^1) vanishes identically. In region language: the
  leading poles come only from 2 (A5) or 3 (Z6) disjoint opposite-charge gaps at scale eps, each a pure power 1/eps.
* **A3 closed form** (independent of the engine; the gate-review derivation, re-checked against mpmath quadrature to
  1.5e-26): sympy gives [eps^3 l^0] = -5/9 and [eps^3 l^1] = [eps^3 l^2] = 0. The engine's c8val value is
  -0.5555555555555555 +- 5.6e-16. After tier C: `python3 tests/exact_scalars_C8.py --run runs/c8tierC_s3_can` checks
  the delivered values (l^1 exact zeros, -5/9 within the quoted error).

### 12c. Budget guard (`tests/budget_guard_C8.py`, new)

Why a probe: the 6-7D rates of the pilot (N = 1009 -> 4001) were 1.0-1.8, the plan assumes 2.0. With the pilot's rates
tier B at 0.01 alone would cost about 45,900 core-h (`plan_C8.py --rate-min-N 1009`), far above the cap; with 2.0 it
costs 5,904. The asymptotic rate decides, and it is unknown. Contiguous production chunks cannot measure it (no lower-N
data on the same sectors), and a heavy group stopped half-way has no result. So:

1. **Stage P (probe, ~94 core-h of engine time on 2 amdq nodes).** Every heavy job (Q8_v, A7_d, Q6_vE | A9, A7_E, Z8,
   Z6_E) runs on exactly the sector sample of `runs/c8conv` (`sectorstride S S/2`, same sectors as the N = 1009 and
   4001 pilot entries) at its planned production N, on amdq. This measures sigma vs N on identical sectors up to the
   production N (the rate in the production range) and the amdq cost per point (the personal-desktop-based model is
   otherwise unconfirmed in 6-7D).
2. **Guard 1** (`budget_guard_C8.py probe runs/c8probeBC --write-specs`): rate table; ledger of what is spent; re-plan
   with `py/plan_C8.py` (new options: `--src-speed runs/c8probeBC=1.0`, `--lower-ref largest`, `--n-floor lower` (a
   probe-referenced job may go below the probe's N, down to the 4001 pilot size, interpolating with the measured rate),
   `--budget-BC (cap - spent - reserve 500) x efficiency 0.95`). Only the heavy (`_sym`) jobs follow the re-plan; the
   cheap ones have run in stage P at their original N, and changes the re-plan suggests for them are ignored (their
   errors are negligible). If B at 0.01 plus C at 3 do not fit, both targets are
   relaxed by the smallest common factor f (default `--priority equal`; the alternatives 'B' = keep B, relax C first,
   and 'C' = keep sigma(C8) ~ 3, relax B are printed next to it): the heavy groups are planned at a lower N, i.e.
   **stopped early, accepting a larger sigma, before their bulk cost is committed**. Changed N -> new specs with fresh
   tier names (`c8tierB_s0.01_r1`, ...) and their `_sym` parts. Exit 0 GO, 4 GO with relaxed targets, 3 STOP.
   Scenario with the pilot rates (cap 18,525 core-h of engine time for B + C): equal -> TB 0.043, T 13 (15.3k);
   priority C -> TB 0.064, T 3 (16.2k); priority B -> TB 0.043 with C at its minimum (sigma 12, 3.7k).
3. **Stage M.** Heavy B and C arrays on amdq (`%4` each, 8 nodes; first chunk of every heavy job first), about 30 h wall.
4. **Guard 2** (`budget_guard_C8.py chunks --run runs/<B> --run runs/<C> --plan <plan>`; after the first chunk of every
   heavy job and at every poll): measured cpu per chunk against the plan, the sector-pooled sigma of the completed
   chunks scaled to the whole job (sigma vs N against the probe and plan), the N and cost the job's target would need,
   and **projected phase total = spent (ledger) + projected remaining (/ efficiency) + reserve**. Above the cap: STOP
   (exit 3) naming the heavy job with the largest remaining cost and the largest ladder N for its remaining chunks that fits the cap, then
   `budget_guard_C8.py tasks` (array task ids to `scancel`, PENDING only), `budget_guard_C8.py reduce RUN JOB@k --N
   NEWN --apply` (the not-started chunks are rewritten with the same sector bounds at NEWN and fresh seeds; chunks of one
   job may differ in N: each sector's shift estimates stay unbiased and i.i.d. across replicates, as with
   `campaign.py refine`) and `submit_C8BC.sh reduced RUN`. Above 90 % of the cap: no top-ups.
5. **Guard 3.** Before any top-up or strict re-check: `budget_guard_C8.py ledger` + its estimated cost <= cap.

The ledger counts every job named `sri_eng_c8BC_*`: symmetry from `sacct -X` (AllocCPUS x Elapsed; Intel partitions x
0.667, an assumption), the personal desktop from the wrappers' `host ... threads P ... start` / `end` lines and `squeue` (no
accounting there). Tested on a partial copy of the tier-1 Q8 run (GO; STOP at a lowered cap with the reduce
recommendation; `reduce --apply` gives cfgs identical apart from N, lattice, seed and output name; collect runs) and on
pilot-built fake probes (GO; a forced relaxation writes `_r1` specs; a probe at production N with rate 1.0 and 1.2x the
cost model relaxes to f = 13.9 and lowers A9, A7_E, Z8 to N = 4001 below the probe's N); the test outputs were removed.

Projected phase total at plan rates: stage P ~250-330 (allocated) + stage M 13,495 / 0.95 = 14,205 + strict re-checks
<= 300 -> **about 14,800 of 20,000**.

### 12d. Deferred archive-free checks (scheduled)

* **C9 pole check at eps^-1:** `c8chkBC` (A9, Z8 eps^-1, all logs, all sectors, N = 1009) in stage P on one amdq node
  (~1 h). These are exactly the 24 scalars that made `C9[v0d0]` untestable at eps^-1 in `validate_C8.py`.
* **Q6_vd strict re-check** (tier-A leftover, criterion 5): `runs/c8tierA_strict/q6vd` (sector 36, one shift, strict
  numerics) on the personal desktop with 1 core in stage P (expected 10-20 h, 7-14 amdq-eq core-h; cancel at 40 personal-desktop core-h
  and report criterion 5 as unverified for Q6_vd). Afterwards: `tests/strict_recheck.py compare runs/c8tierA
  runs/c8tierA_strict/q6vd`.
* **RG higher logs of C9, d_v K8 and d_delta C7:** no extra runs. The tier runs compute every log power >= jmin: C9[v0d0]
  l^3-l^9 and the second log need A9[eps^0 l^2..], A7_E[eps^0 l^1..] and A7[eps^1 l^2..] (tier C), K8[v1d0] needs
  Q8_v[eps^0 l^2..] (tier B), C7[v0d1] gets the tier-B A7_d (its pilot-level sigma at l^3 is 1.1). Run
  `validate_C8.py` with the production tiers listed first (it keeps the first entry of each coefficient); the four
  jets `C9[v0d0]`, `C9_2[v0d0]`, `K8[v1d0]`, `K8_2[v1d0]` must become computable and pass (|pull| < 3). The
  verifier's untestable J9 lower part (A7_v[eps^0 l^0], A7[eps^1 l^1], A7_E[eps^0 l^0], A9[eps^0 l^1]) also comes
  with tier C.
* **Strict re-checks of tiers B/C** (criterion 5): most-warned sectors of Q8_v, A9, A7_E, Z8, A7_d at production N,
  `tests/strict_recheck.py prepare` + `submit_C8BC.sh strict` (packed, 8 workers on one amdq node), within the reserve
  (<= 300 core-h; Q8_v strict costs up to 37x default: one sector x one shift).

### 12e. How to run (Mac, from engine/)

```bash
bash slurm/submit_C8BC.sh sync                     # code, specs, lattice DB -> symmetry + the personal desktop (md5 check)
bash slurm/submit_C8BC.sh stageP                   # symmetry: probe1 (Q8_v), probe2 (6 others), chk; the personal desktop:
                                                   # canB, canC (6 cores each), q6vdstrict (1 core)
bash slurm/poll_C8BC.sh 600 &                      # read-only poller
bash slurm/submit_C8BC.sh pull                     # after the probes: outputs + logs back to the Mac
python3 py/campaign.py collect runs/c8probeBC --partial
python3 tests/budget_guard_C8.py probe runs/c8probeBC --write-specs      # guard 1 -> prints the stageM line
bash slurm/submit_C8BC.sh stageM [specs/..._sym.json specs/..._sym.json] # heavy arrays, %4 + %4
python3 tests/budget_guard_C8.py chunks --run runs/c8tierB_s0.01 --run runs/c8tierC_s3 \
        --plan results/plan_C8BC_replan.json                             # guard 2 (after each pull)
# acceptance per run dir (B: runs/c8tierB_s0.01{,_can}; C: runs/c8tierC_s3{,_can}):
python3 py/campaign.py collect RUN --need specs/production_C8_need.json
python3 py/outliers.py RUN --grad specs/gradients_C8.json --T 0.01   # tier C: --T 3
python3 tests/production_checks.py RUN --json RUN/production_checks.json
python3 tests/budget_C8.py RUN --plan results/plan_C8BC_replan.json --json RUN/budget_C8.json
python3 tests/tier_vs_pilot_C8.py RUN --json RUN/tier_vs_pilot.json
python3 tests/exact_scalars_C8.py --run runs/c8tierC_s3_can
python3 tests/validate_C8.py --run runs/c8tierC_s3 --run runs/c8tierC_s3_can --run runs/c8tierB_s0.01 \
        --run runs/c8tierB_s0.01_can --run runs/c8chkBC --run runs/c8tierA_topup1 --run runs/c8tierA \
        --run runs/c8val --run runs/c8conv --run runs/c8kplus1 --out results/validate_C8_tierBC
# then the framework at order C8, strict, per replicate: --raw runs/prod_6digit/framework_input_final.json
#   --raw runs/c8tierA/framework_input_final.json --raw each of the four B/C framework_input.json (--independent-files)
```

Dry run (2026-10-04, 20:40-20:45 EDT, `DRY=1`): stageP planned 7 + 2 + 21 + 18 cfgs into a scratch directory and `sbatch
--test-only` reported an immediate start for the three amdq jobs (<NODE>) and the three personal-desktop jobs; stageM planned 32
+ 41 cfgs and both arrays would start at once (<NODE>). `slurm/poll_C8BC.sh` ran once (no phase job). At that time:
amdq 9 idle, 6 allocated (the user's lri-prod2 running with 2 dependent jobs pending, lri-prod7, and two other users),
11 down, 2 not responding; defq 15 idle; personal desktop 16 of 32 cores free (the user's job 155 holds 16).

### 12f. Open items

1. **Rates.** If the probe confirms rates near 1.2 for Q8_v, tier B at 0.01 does not fit the cap (about 46k core-h); guard 1
   then relaxes the targets automatically ('equal'). Whether to prefer keeping sigma(C8) ~ 3 (priority C) or tier B
   (priority B) in that case is a decision for the orchestrator; the guard prints all three. (Resolved: the probe gave
   2.2 for Q8_v; tier B fit with margin, section 13b.)
2. **Sector-adaptive N** (Neyman cost factor 0.62 for Q8_v, 0.82 for A9, from the pilot samples) is not implemented for
   production; `campaign.py refine` of the dominant sectors is the available top-up within the cap.
3. **Intel partitions.** The ledger converts symmetry Intel (defq) core-h with 0.667, assumed equal to the personal desktop (both
   Intel Xeon); it is not calibrated. Production uses amdq unless amdq is full for a long time. (Only the N = 1009 C9
   check ran on defq: 51.8 amdq-eq.)

## 13. Tiers B and C: production (2026-10-04 to 2026-10-07; DONE)

Procedure of section 12, run from the Mac with `slurm/submit_C8BC.sh`. Cap 20,000 amdq-equivalent core-h for the whole
phase. No archive value was read or compared.

### 13a. Stage P (2026-10-04 21:20 EDT)

| job | machine | content | start - end (EDT) | allocated | state |
|---|---|---|---|---|---|
| 569828 `sri_eng_c8BC_probe1` | symmetry amdq <NODE> | probe: Q8_v N = 91621 on the c8conv sample (30 sectors) | 21:20 - 23:38 (8307 s) | 147.7 core-h | COMPLETED 0:0 |
| 569829 `sri_eng_c8BC_probe2` | symmetry amdq <NODE> | probe: A9, Z8, A7_d, Q6_vE, A7_E, Z6_E at their planned N | 21:20 - 22:02 (2518 s) | 44.8 core-h | COMPLETED 0:0 |
| 569830 `sri_eng_c8BC_chk` | symmetry **defq** <NODE> | C9 pole check: A9, Z8 at eps^-1, all logs, all sectors, N = 1009 | 21:20 - 23:16 (6983 s) | 77.6 physical core-h = 51.8 amdq-eq | COMPLETED 0:0 |
| 283 `sri_eng_c8BC_canB` | the personal desktop, 6 cores | the 21 cheap tier-B cfgs (`runs/c8tierB_s0.01_can`) | from 03:20 CEST | running | |
| 284 `sri_eng_c8BC_canC` | the personal desktop, 6 cores | the 18 cheap tier-C cfgs (`runs/c8tierC_s3_can`), incl. the four exact scalars | from 03:20 CEST | running | |
| 285 `sri_eng_c8BC_q6vdstrict` | the personal desktop, 1 core | tier-A leftover: Q6_vd sector 36 strict | from 03:20 CEST | running | |

* amdq had only 2 usable idle nodes at submission (13 allocated, 11 down), so the C9 check went to defq (rule: amdq
  first, then defq). `submit_C8BC.sh` got `CHK_PART` / `SYM_PART` for this (partition override with `--mem=180G`).
* The ledger counted symmetry Intel allocations with their 80 logical CPUs. Intel nodes have 40 physical cores (2 threads
  each), the engine runs one thread per physical core, and the cap's unit is the physical core (the personal desktop: `-c N` = N
  physical cores). `budget_guard_C8.py ledger` now counts physical cores on Intel partitions (`cpus_physical`), and guard
  2 converts the cpu of chunks computed on Intel hosts (<NODE>-076) with 0.667 (`_host_speed`).
* The personal desktop canB/canC/q6vdstrict: 13 of the 16 free cores, `--time=0`, `TimeLimit=UNLIMITED` checked by the script.

### 13b. Guard 1: probe results and the re-plan

`python3 tests/budget_guard_C8.py probe runs/c8probeBC` (sigma = C8 contribution scaled to all sectors; the same sector
sample at all three N; cost = engine cpu on amdq against the plan's personal-desktop-based model):

| job | tier | N (probe) | sigma at 1009 / 4001 / probe N | rates 1009-4001, 4001-probe | sigma probe / plan | cost amdq / plan |
|---|---|---|---|---|---|---|
| Q8_v [eps^0 l^1] | B | 91621 | 23.9 / 4.44 / 4.55e-3 | 1.22, **2.20** | 0.54 | 1.14 |
| Q6_vE [eps^0 l^0] | B | 131071 | 26.6 / 1.56 / 9.35e-3 | 2.06, **1.47** | **6.41** | 1.10 |
| A7_d [eps^0 l^1] | B | 32003 | 29.2 / 0.678 / 1.11e-3 | 2.73, 3.09 | 0.55 | 1.17 |
| A9 [eps^0 l^1] | C | 8009 | 110 / 9.18 / 2.61 | 1.80, 1.81 | 1.14 | **1.21** |
| A7_E [eps^0 l^0] | C | 11321 | 38.6 / 7.33 / 2.83 | 1.21, **0.91** | **3.09** | 1.18 |
| Z8 [eps^0 l^1] | C | 5669 | 1.68 / 0.605 / 4.58e-2 | 0.74, 7.41 | 0.15 | 1.20 |
| Z6_E [eps^0 l^0] | C | 5669 | 2.10 / 0.484 / 8.14e-2 | 1.06, 5.12 | 0.34 | 1.28 |

* **Rates.** Q8_v converges at 2.2 in the production range (the plan assumed 2.0; the pilot's 1.2 was pre-asymptotic),
  A9 at 1.8. The two endpoint moments are slow: Q6_vE 1.47 and A7_E 0.91 (boundary sectors, as for the 4D endpoint
  moments of tier 1).
* **Cost.** On amdq the 6-7D groups cost 1.10-1.28x the plan's model: the personal desktop / amdq factor for them is about 0.8,
  not the 0.667 measured on two 4D cfgs. The re-plan takes the cost from the probe itself (`--src-speed
  runs/c8probeBC=1.0`).
* **Probe efficiency** (engine cpu / 64 x wall): 0.31-0.85; Q8_v 0.52, because one sector of its 30-sector sample costs
  13.7 cpu-h (2.3 h per shift task) and set the wall time. Production chunks hold 70-80 sectors x 6 shifts each, and the
  heaviest task (2.3 h) is shorter than a chunk (about 3 h).
* **Re-plan at the approved targets** (TB 0.01, T 3, priority equal; `results/plan_C8BC_replan.json` as first written):
  GO, B 4,970 + C 10,773 engine core-h, projected phase total 17,336. It **lowered Q8_v to N = 64007** (sigma 9.3e-3),
  which puts sigma(C8 without J9) at 9.99e-3, i.e. exactly on the target.
* **Decision: tier B with a safety margin, priority B.** The Q8_v sigma comes from 30 of 2520 sectors (top-3 sectors 40 %
  of the cost, 57 % of the pilot variance); as in tier 1 (README section 10 (iii)), such a prediction is uncertain by
  about a factor 2, and a miss of tier B would need a top-up at 2N (about 9k core-h, beyond the cap). Tier B is the
  approved precise target and the instruction is "tier B first, then tier C (gross)". So the re-plan was rerun with a
  planning target TB = 0.007 (`--plan-TB 0.007`, new option; the approved target stays 0.01) and `--priority B` (keep B,
  relax C first if the cap binds). The ladder then keeps **Q8_v at its prepared N = 91621** (sigma 4.55e-3) and raises
  **Q6_vE to 370759** (sigma 2.0e-3): predicted sigma(C8 without J9) = 5.1e-3, B 7,039 + C 10,773 = 17,812 engine
  core-h, projected phase total (spent 265 + 17,812 / 0.95 + reserve 500) = **19,515**, verdict GO.
* Tier C in the re-plan: A9 8009 (44 chunks, sigma 2.61), **A7_E raised to 32003** (13 chunks, sigma 1.10 with its
  measured rate 0.91), Z8 lowered to 4001; total sigma(C8) 2.84.
* New specs (fresh tier names, fresh seeds): `specs/production_C8_tierB_replan_r1{,_sym}.json` (tier
  `c8tierB_s0.01_r1`: Q8_v 91621 x 34 chunks, Q6_vE 370759 x 3, A7_d 32003 x 1) and
  `specs/production_C8_tierC_replan_r1{,_sym}.json` (tier `c8tierC_s3_r1`: A9 8009 x 44, A7_E 32003 x 13, Z8 4001). The
  cheap jobs keep their stage-P runs (`c8tierB_s0.01_can`, `c8tierC_s3_can`, tier names of the prepared specs).
* One lattice was missing (370759_6): personal-desktop job 286 (54 s, 1 core) found `a = 169910`; merged, DB md5 `d16c6450`
  (63 entries), synced.
* Seeds: the 144 cfgs of the phase (r1 tiers, probe, checks, cheap parts) have 459,114 streams, **0 overlaps** with the
  1,372,750 streams of all earlier run directories (`results/seedcheck_c8BC_r1.txt`).

### 13c. Stage M

* **Tier B** (`bash slurm/submit_C8BC.sh array specs/production_C8_tierB_replan_r1_sym.json mainB 8`): array **569858**,
  38 tasks (`cfglist_sym.txt`: first chunks of Q8_v, Q6_vE, A7_d first), at most 8 at a time on amdq; all 8 started at
  23:45 EDT (amdq had 11 idle nodes). Logs `<SCRATCH>/sri_c6c7/engine/logs/sri_eng_c8BC_mainB_569858_<task>.out`.
* **Tier C** was submitted when tier B had no pending task left (14:08 EDT, array **570223**, `%1`), and its throttle
  was raised as tier-B nodes freed up (`scontrol update JobId=570223 ArrayTaskThrottle=n`, n = 8 - our other running
  nodes; 8 at 17:25), so at most 8 of our nodes ran at once.

### 13d. Guard 2 during tier B, and the tier-C re-plan C2

`budget_guard_C8.py chunks` after every wave (log: `results/budget_guard_C8BC_log.txt`). New: `--efficiency measured`
(engine cpu / allocated core-h over the completed one-cfg array tasks, from the ledger and the outputs).

* After the first Q8_v chunks (03:15 EDT, efficiency assumed 0.95): projected phase total 20,310 > cap, **STOP**, with
  the recommendation to finish A9 at 5669. Every chunk named by the STOP belonged to tier C, which was not yet
  submitted, so no running or queued task was affected; the decision was moved to the tier-C submission, when tier B's
  cost would be known. With the measured efficiency (0.98 then, 0.95-0.97 later) the projection fell to 19,358-19,714.
* Q8_v production chunks cost 1.12x the probe-based estimate (the 30-sector sample under-represented the expensive
  sectors); per-task efficiency 0.86-1.00 (heavy-sector tails).
* **Re-plan C2** (14:00 EDT, before submitting tier C): budget left for tier C = 20,000 - spent 7,356 - tier-B remaining
  ~2,975 - reserve 500 ~ 11,000 allocated, i.e. ~10,500 engine core-h at the measured efficiency. `py/plan_C8.py ...
  --TB 0.007 --T 3 --budget-BC 17600 --budget-priority B --out results/plan_C8BC_replan_C2` keeps tier B as running (rows
  identical) and relaxes the tier-C target by fC = 1.05 (T = 3.15): **A7_E lowered from 32003 to 22637** (9 chunks, sigma
  1.50), A9 stays at 8009 (44 chunks, sigma 2.61), Z8 at 4001. A9 at 8009 is the efficient choice: one ladder step down
  (5669) would raise its sigma by 1.9x. Spec `specs/production_C8_tierC_replan_r2{,_sym}.json`, tier **`c8tierC_s3_r2`**
  (fresh seeds; 257,040 streams, 0 overlaps with every earlier campaign). The r1 tier-C run directory had been planned
  on the Mac only, never pushed or submitted, and was deleted.
* **Array order for tier C** (`KEEP_ORDER=1`, new in `submit_C8BC.sh array`): A9 c000, Z8, A7_E c000, then all other A9
  chunks, and **the other 8 A7_E chunks last**. If the cap binds later, the cheapest sigma per core-h is to finish
  A7_E's last chunks at a lower N (`budget_guard_C8.py reduce`), not A9's (an A9 step costs 1.9x in its sigma).
* **Guard 2 during tier C** (2026-10-06; log `results/budget_guard_C8BC_log.txt`): projected phase total 19,329 (01:12
  EDT), 19,656 (02:10), 19,928 (03:11), then **STOP at 04:16 EDT: 20,079 > 20,000**. The A9 cost ratio had risen from
  0.98 to 1.09: the A9 chunks that ran 20th-23rd cost 1.26-1.74x the mean of the cost model (one ran 5.4 h).
* **Action (04:20 EDT): A7_E's 8 pending chunks reduced from N = 22637 to 16001**, as planned in C2 above. The guard's own
  recommendation (A9's not-started chunks at 5669) was not taken. Variance added per core-hour saved: A7_E 1.75 / 412 =
  0.0042; A9 (its 11 pending chunks) 3.44 / ~540 = 0.0064. Steps:
  * `scancel 570223_[47-54]`: these were the A7_E tasks, all PENDING (confirmed with `squeue -r` before the cancel).
  * `budget_guard_C8.py reduce runs/c8tierC_s3_r2 A7_E@0 --N 16001 --apply`, tag `reduced1`: the same sector bounds,
    fresh seeds, cfgs `A7_E_k0_c00{1..8}_N16001.cfg`, which differ from the old ones only in N, lattice (16001_6: 487),
    seed and output name. The 111,198 new streams have 0 overlaps with the 1,849,144 streams of every campaign. The
    manifest records the reduction.
  * Array **570513** `sri_eng_c8BC_redC` (`cfglist_reduced.txt`, 8 tasks), submitted with `--dependency=afterany:570223`.
    When 570223 had no pending task left (08:41 EDT), its throttle was set to 8 minus our other running nodes and the
    dependency was cleared. The throttle was then raised as A9 nodes freed up (1 -> 6). At most 8 of our nodes ran at once.
  * Guard 2 after the reduction: 19,669 GO. Later runs gave 19,606 (05:27) and 19,580 (07:57), both GO; A9 stayed at
    x1.07-1.09.

### 13e. Tier B results (heavy part done 2026-10-05 17:18 EDT)

* Array 569858: 38 tasks COMPLETED 0:0 on amdq, 23:45-17:18 EDT, **8,244 allocated core-h** (`logs/symmetry/
  sacct_c8BC_mainB.txt`), engine cpu 7,851.7 core-h (efficiency 0.952). Q8_v 7,177.7 engine core-h (plan 6,403), Q6_vE
  496 (476), A7_d 178 (141).
* `collect --need specs/production_C8_need.json`: exit 0 (both `runs/c8tierB_s0.01_r1` and `runs/c8tierB_s0.01_can`).
* `outliers.py --T 0.01`: exit 0 on both (inspection `--fac 10 --share 0.2`: three A7_d sectors with 30-37 % of its error).
* `production_checks.py`: exit 0; WARN 0.26 % (heavy) and 0.010 % (cheap), worst cfg 5.6 % (a Q8_v chunk); replicate vs
  sector-pooled error ratio median 0.93 (heavy), 0.98 (cheap).
* **sigma_C8 (`tests/budget_C8.py`, larger of replicate and sector-pooled, + floor):** Q8_v 4.95e-3 (plan 4.55e-3,
  1.09x), A5_dE 2.19e-3 (plan 4.4e-4, **5.0x: MISS**), A7_d 1.15e-3 (1.04x), Q6_vE 3.6e-5 (0.02x), everything else
  <= 5e-5. **sigma(C8 part of tier B) = 5.54e-3** (rep 5.52e-3, pooled 5.09e-3; plan 5.12e-3). With tier A and B_old:
  sigma(C8 without J9) = **5.5e-3, against the approved 0.01**. Engine part of the inputs: U 3.3e-3, Kv 0.158.
* **Top-up of A5_dE** (cheap part, the personal desktop): the rule (miss > 1.5x, within the cap) applies. Spec
  `specs/production_C8_tierB_topup1.json` (tier `c8tierB_s0.01_topup1`, fresh seeds, 0 overlaps), whole job at N =
  262139 (4x), personal-desktop job **287** (8 cores, `--time=0`, 23:27 CEST to 12:11 CEST on 2026-10-06; 45,877 s, rc 0).
  * The personal desktop was oversubscribed outside Slurm during the top-up by another user's processes (4 x 64-thread python, load
    200-270). That made the run take 102 engine core-h against about 71 expected from the N = 64007 run.
  * Result: A5_dE[eps^0 l^0] = 6166.4862775 +- 3.6e-5. The N = 64007 run gave 6166.4861685 +- 1.4e-3, a pull of 0.08;
    the c8val pilot gives a pull of -0.18.
  * collect, outliers (T = 0.01) and production_checks all exit 0; WARN 0.025 %.
  * sigma_C8 = 5.3e-5, 0.12x its budget.
  * `tests/budget_C8.py r1 _can topup1` (`runs/c8tierB_s0.01_topup1/budget_C8.{txt,json}`): **sigma(C8 part of tier B) =
    5.08e-3** (rep 5.07e-3, pooled 4.63e-3; plan 5.12e-3). No job misses its budget. Engine part of the inputs: U 1.5e-3,
    Kv 0.158.
* **tier_vs_pilot** (independent earlier runs, all-sector references): heavy part 2 comparisons, max |pull| 1.54; cheap part
  43 comparisons, rms pull (stat + floor) 1.08, max 3.98 (Z6_d[eps^0 l^1] against the N = 4001 pilot; sigma_C8 of this
  coefficient 1.6e-5), and one stat-only pull of 6.7 at double rounding (A3_d[eps^2 l^0] = -4, difference 1.3e-15,
  floor pull 0.02).
* **Strict re-checks** (criterion 5): the most-warned sectors Q8_v 1270 (1 shift; 30,721 warned points), Q6_vE 1511 and
  679 (1 shift), A7_d 203 and 276 (2 shifts) at production N: `runs/c8tierB_s0.01_r1_strict/s1`, personal-desktop job **288**
  (6 cores = 2 workers x 3 threads, `slurm/packed_personal-desktop.sbatch`, new), from 23:28 CEST. The personal desktop, not a whole amdq
  node, because a strict Q8_v sector-shift has only 6 point blocks of 15,270 points (planned at about a day of wall time on 3 threads; the blocks took 16 to over 41 cpu-h); one Q8_v
  sector instead of two to stay within the reserve. Results in 13g; the two A7_d cfgs were OOM-killed in 288 and rerun
  as job 298.
* Tier-A leftover: the **Q6_vd strict re-check passed** (personal-desktop job 285, 1 core, 37,805 s = 10.5 personal-desktop core-h):
  sector 36, worst coefficient difference 3.6e-17 of the sector size = 8.6e-6 of the quoted error
  (`runs/c8tierA_strict/q6vd/strict_compare.{txt,json}`). Criterion 5 is now verified for every tier-A job.

### 13f. Tier C results (heavy part done 2026-10-06 12:21 EDT)

* **Runs.**
  * Array 570223: 46 tasks COMPLETED 0:0 on amdq (44 A9 chunks, Z8, A7_E c000), 9,008.2 allocated core-h. Its tasks
    47-54 (the A7_E chunks 1-8) were cancelled while PENDING (13d).
  * Array 570513: the 8 reduced A7_E chunks, 917.4 core-h.
  * Z8 top-up, array 570320, 161.9 core-h. Z8 at N = 4001 missed its budget by 4.6x (0.425 against 0.092). The re-plan
    had lowered it from 5669 using the probe point, whose 30-sector sample gave far less variance than all sectors do.
    It was rerun whole at N = 11321 with fresh seeds (`specs/production_C8_tierC_topup1.json`, tier
    `c8tierC_s3_topup1`). The submission at 18:45 EDT on 2026-10-05 came after a guard-2 projection of 17,501 (GO).
  * sacct: `logs/symmetry/sacct_c8BC_mainC.txt`. Engine cpu of `runs/c8tierC_s3_r2`: 9,889.0 core-h (A9 8,754.1, A7_E
    1,086.3, Z8 at 4001 48.6), i.e. efficiency 0.996.
  * Cheap part: personal-desktop job 284 (`runs/c8tierC_s3_can`, 55.9 personal-desktop core-h).
* **Acceptance.**
  * `collect --need`: exit 0 for `runs/c8tierC_s3_r2` (with the mixed-N A7_E chunks), `_can` and `_topup1`.
  * `outliers.py --T 3`: exit 0, 0 flagged sectors.
  * `production_checks.py`: exit 0, no problems; replicate vs sector-pooled error ratio A9 0.52, A7_E 1.51, Z8 0.97.
* **WARN fraction: 1.03 % overall in the heavy part**, above the 1 % of criterion 5. A9 is at 2.9 % (worst cfg 9.0 %),
  A7_E at 0.14 % and Z8 at 0.48 %. Many A9 sectors carry about 940 of 8009 warned points (11.7 %) in a shift. The strict
  re-checks of the most-warned A9 sectors decide whether this matters (13g). The cheap part is at 0.039 % and the Z8
  top-up at 0.48 %.
* **sigma_C8** (`tests/budget_C8.py runs/c8tierC_s3_r2 runs/c8tierC_s3_can runs/c8tierC_s3_topup1 --plan
  results/plan_C8BC_replan_C2.json`):

  | job | N | sigma_C8 (rep / pooled / quoted) | plan (C2) | ratio |
  |---|---|---|---|---|
  | A9 [eps^0 l^1] | 8009 | 1.22 / 2.33 / **2.33** | 2.61 | 0.89 |
  | A7_E [eps^0 l^0] | c000 22637, c001-c008 16001 | 0.62 / 0.41 / 0.62 | 1.50 (at 22637) | 0.41 |
  | A7_v [eps^0 l^0] | 11321 | 0.063 | 0.073 | 0.86 |
  | Z6_E [eps^0 l^0] | 5669 | 0.056 | 0.16 | 0.34 |
  | Z8 [eps^0 l^1] (top-up) | 11321 | 0.0146 | 0.092 | 0.16 |
  | everything else | | <= 6.5e-3 | | |

  **sigma(C8 part of tier C) = 2.42** (rep 1.37, pooled 2.37; plan 3.02). No job misses its budget. Engine part of J9:
  9.7 (larger estimator). The approved gross target was total sigma(C8) ~ 3.
* **Independent comparisons.**
  * `tier_vs_pilot_C8.py` has no all-sector reference for A9, A7_E or Z8 at eps^0: the pilots and the probe sampled
    sectors.
  * The two all-sector Z8 runs, r2 at N = 4001 and the top-up at 11321 with fresh seeds, differ by 2.36, a pull of 2.69
    (`runs/c8tierC_s3_topup1/tier_vs_r2.json`). The 4001 run is the one whose error was 4.6x its planned value, i.e.
    pre-asymptotic. The delivered top-up has sigma_C8 = 0.015, so even a 3x underestimate would not matter for C8.
  * Cheap part: 38 comparisons, rms pull (stat + floor) 1.02, max 2.58.
* **Exact scalars:** `python3 tests/exact_scalars_C8.py --run runs/c8tierC_s3_can` gives RESULT PASS.
  * A3[eps^3 l^1], A5[eps^-2 l^1] and Z6[eps^-3 l^1] are explicit exact zeros (`{"value": "0", "sigma": "0", "exact":
    true}` in the framework input).
  * A3[eps^3 l^0] = -0.5555555555555555 +- 5.6e-16, i.e. -5/9.

### 13g. Strict-tolerance re-checks (criterion 5; `tests/strict_recheck.py`, same cfg, lattice, seed and shifts at production N)

| group | sectors (shifts) | run dir, job | result: worst coefficient difference |
|---|---|---|---|
| Q6_vE (B) | 1511, 679 (1) | `runs/c8tierB_s0.01_r1_strict/s1`, personal desktop 288 | 1.3e-16 of the sector size = 9.3e-10 x err |
| A7_d (B) | 203, 276 (2) | same dir, personal desktop **298** (rerun, see below) | 1.3e-16 of the sector size = 1.3e-9 x err |
| Q8_v (B) | 1270 (1; 30,721 warned points) | same dir, personal desktop 288 | **no result**: job 288 was cancelled from outside after 41.9 h (13k, item 8) |
| A9 (C) | 9032, 2360 (1; 5,504 and 5,478 warned points) | `runs/c8tierC_s3_r2_strict/a9`, personal desktop 300 (4 cores) | 1.4e-13 of the sector size = **8.8e-11 x err** |
| A7_E (C) | 1380, 1270 (N 22637), 15911 (N 16001; the most-warned sector of the reduced chunks, added by hand with the same construction) (1) | `runs/c8tierC_s3_r2_strict/a7e`, personal desktop 303 (3 cores; 7,092-15,137 s) | **0** (bitwise identical l^0 in all three sectors) |
| Z8 (C, top-up) | 1270, 2359 (1) | `runs/c8tierC_s3_topup1_strict/z8`, personal desktop 299 (2 cores) | 3.2e-13 of the sector size = 1.4e-9 x err |

* **Two A7_d re-checks were killed by the memory limit.** In job 288 the cgroup reported 2 oom_kill events at 01:15 and
  01:48 CEST: `--mem=24G` was shared by two workers, and the strict Q8_v process alone holds 12-17 GB. The A7_d pair was
  rerun as personal-desktop job 298 (`-c 6 --mem=96G`, 2 workers x 3 threads, list `cfglist_a7d.txt`), with a peak of 47 GB. It
  took 21,007 s and 30,692 s.
* The A9 sectors with about 11.7 % warned points per shift agree with the strict values to 1e-13 of their size. The A9
  WARN fraction of 2.9 % (13f) is therefore cosmetic for this tier, as the endpoint-moment pattern of tier A was.
* The personal desktop resources:
  * From 2026-10-05 about 11:40 to 2026-10-06 about 13:00 EDT, another user ran 4 x 64-thread python processes outside
    Slurm, at load 200-270. Our engines kept their allocated cores but ran slower.
  * At 13:56 EDT the user's own job 155 ended. Its continuation 302 (16 cores) could not start while our jobs held 19
    cores. The A7_E re-check (job 301, 40 min old, 2.4 core-h) was cancelled so that 302 could start; it was resubmitted
    as 303 and started at 14:43.

### 13h. Deferred archive-free checks

* **C9 pole cancellation at eps^-1.**
  * With `c8chkBC` (A9, Z8 eps^-1, N = 1009) the 12 C9[v0d0][eps^-1 l^k] checks became computable. l^3 gave pull +3.47
    with the replicate error; l^4 gave +2.87 and l^5 -2.26.
  * Sector-pooled errors for the c8chkBC inputs (`results/validate_C8_tierBC_c9pool.json`, `tests/c9pool_C8.py`, with
    `assembly/pooled_errors.py`) are 1.5x the replicate ones for A9[eps^-1 l^3] (rep/pool 0.64). With them the pulls are
    2.32, 2.52 and -2.57.
  * To decide, the same two jobs were **rerun at N = 4001 with fresh seeds**: `specs/checks_C8_BC_N4001.json`, tier
    `c8chkBC_N4001` (136,080 new streams, 0 overlaps), symmetry amdq job **570610** (3:06 h, 198.6 core-h). This was an
    addition to the prepared plan, made inside the cap; at the time the ledger stood at 18,812.
  * At N = 4001, A9[eps^-1 l^3] = -903.4307476 +- 9e-6. At 1009 it was -903.4289041 +- 5.2e-4, so the 1009 value was off
    by 1.84e-3, i.e. 3.5 of its replicate error and 2.25 of its pooled error. This one coefficient accounts for the
    whole C9 deviation (1.93e-3).
  * `validate_C8.py` with `c8chkBC_N4001` listed first (`results/validate_C8_tierBC_chk4001.{txt,json,stdout}`): every
    C9[v0d0][eps^-1 l^k] has **|pull| <= 0.90**.
* **validate_C8.py, production tiers first** (topups, r1/r2, _can, chk 4001, chk 1009, tier A, pilots):
  * raw targets: 11 checks, max |pull| 0.22;
  * pole cancellation: 1008 checks, max |pull| 2.95 (EK6[v1d0][eps^-2 l^1], pilot data, unchanged since tier A);
  * below-bound zeros: 13 checks, all exact;
  * C3/K4 higher logs: 120 checks, max 0.36;
  * RG second and higher logs: 113 checks, max 2.62.
  * **0 checks above 3 and 0 not computable.**
  * Every jet that was untestable before is now tested: C9[v0d0] at eps^-1 l^0..l^5; RG C9[v0d0] l^3..l^9 (max |pull|
    2.56, at l^6); C9_2[v0d0] (-0.60); K8[v1d0] l^3..l^9 (max 0.41); K8_2[v1d0] (+0.15).
  * The verifier's J9 lower part (A7_v[eps^0 l^0], A7[eps^1 l^1], A7_E[eps^0 l^0], A9[eps^0 l^1]) now comes from tier C.
  * The run with the N = 1009 check first is kept for the record: `results/validate_C8_tierBC.{txt,json,stdout}`.
* **Four exact tier-C scalars:** PASS (13f).
* **Q6_vd strict** (tier-A leftover): passed (13e).

### 13i. Deliverables (SHA-256 recorded at creation in `runs/c8BC_SHA256SUMS.txt`, before any comparison)

| file | content | sha256 |
|---|---|---|
| **`runs/c8tierB_s0.01_r1/framework_input_final.json`** (+ `results_final.json`) | tier B: heavy r1 (Q8_v, Q6_vE, A7_d) + cheap `_can` (16 groups) + the A5_dE top-up (`py/merge_runs.py --tag final`); 30 scalars, R = 6 | `77ed204d04ca...` (`c5670362718a...`) |
| **`runs/c8tierC_s3_r2/framework_input_final.json`** (+ `results_final.json`) | tier C: heavy r2 (A9, A7_E with chunks 1-8 at N = 16001) + cheap `_can` (11 groups, the four exact scalars included) + the Z8 top-up; 29 scalars, R = 6 | `a95d72d9aa0f...` (`3221610800e9...`) |
| **`runs/c8tiersABC/framework_input_final.json`** | tiers A + B + C merged per scalar (`tests/merge_tiers_C8.py`; blocks renamed `A:`/`B:`/`C:`; Z4_d and Z6_base have eps powers in two tiers and are kept per scalar); 85 scalars, R = 6 | `9a108caf06ae...` |
| `runs/c8tierA/framework_input_final.json` | tier A (unchanged since 2026-10-04) | `4ade69e631a5...` |

Completeness check (archive-free), at order C8, strict, with no `--allow-missing`:

`../framework/run_framework.py --order C8 --independent-files --raw runs/prod_6digit/framework_input_final.json --raw
runs/c8tiersABC/framework_input_final.json`

The run exits 0 with no MISSING. Feeding the three tier files separately gives the same numbers.

| quantity | value | linear sigma | replicate sigma |
|---|---|---|---|
| U | -1296.68755 | 0.00143 | |
| Kv | -1487.0046 | 0.158 | |
| J9 | -291.94 | 5.48 | 4.57 |
| T4 | 30.353 | | |
| **C8** | **242.83** | 1.37 | 1.15 |

* The sector-pooled estimator (`tests/budget_C8.py`) gives the largest error: sigma(C8) = 2.42, almost all of it from
  A9.
* sigma(C8 without J9) = 5.1e-3 (C8_partial with J9 left out), against the approved 0.01.
* Assembly with the three-estimator quoting (`../assembly/run_assembly_C8.py`): done 2026-10-07, section 13l and `../RESULTS_C8.md`.

### 13j. Cost per tier (ledger `tests/budget_guard_C8.py ledger` -> `runs/c8BC_ledger.json`)

The unit is the amdq-equivalent core-h: symmetry amdq allocated core-h (sacct `-X`, AllocCPUS x Elapsed), plus 0.667 x
allocated physical core-h on symmetry defq and on the personal desktop (the personal desktop from the wrapper logs and squeue).

| part | jobs | allocated | amdq-eq core-h |
|---|---|---|---|
| tier B heavy | array 569858 (38 tasks, amdq; `logs/symmetry/sacct_c8BC_mainB.txt`) | 8,244.0 | 8,244.0 |
| tier B probe | 569828 (Q8_v probe, amdq) | 147.7 | 147.7 |
| tier B cheap + top-up | personal desktop 283 (29.1 core-h), 287 (A5_dE top-up, 101.9) | 131.0 | 87.4 |
| tier B strict | personal desktop 288 (Q6_vE, Q8_v; 6 cores, 41.9 h: 251.4 core-h), 298 (A7_d rerun, 51.2) | 302.6 | 201.8 |
| **tier B** | | | **8,680.9** |
| tier C heavy | array 570223 (46 tasks), 570513 (8 reduced A7_E chunks), 570320 (Z8 top-up), all amdq (`logs/symmetry/sacct_c8BC_mainC.txt`) | 9,008.2 + 917.4 + 161.9 | 10,087.5 |
| tier C cheap | personal desktop 284 | 55.9 | 37.3 |
| tier C strict | personal desktop 299 (Z8), 300 (A9), 301 (cancelled), 303 (A7_E) | 28.5 | 19.0 |
| **tier C** | | | **10,143.8** |
| probe of B and C heavy groups | 569829 (amdq) | 44.8 | 44.8 |
| C9 pole checks | 569830 (defq, N = 1009: 77.6 physical core-h), 570610 (amdq, N = 4001; `logs/symmetry/sacct_c8BC_chk4001.txt`) | 276.2 | 250.4 |
| tier-A leftover | personal desktop 285 (Q6_vd strict) | 10.5 | 7.0 |
| lattice searches | personal desktop 276, 286 | 0.06 | 0.04 |
| **phase total** (final, 2026-10-07 11:24 EDT; no job of the phase running) | | | **19,126.8 of 20,000** |

* Including the preparation (0.03), the phase stayed inside the 20,000 cap at every guard evaluation. The highest
  projection was the 04:16 EDT STOP (20,079), which was resolved by finishing A7_E at a lower N.
* The 6-7D groups cost more than planned.
  * The 7-8 kink jobs on amdq ran at 1.10-1.28x the personal-desktop-based model; the probe measured this before the bulk.
  * Q8_v production chunks ran at 1.12x the probe estimate, and A9 at 1.07-1.09x.
  * The plan's 13,495 amdq core-h for B + C became 18,170 for the three heavy arrays (18,331 with the Z8 top-up). Tier B was raised on purpose
    (Q6_vE, margin), and tier C was trimmed to stay inside the cap.

### 13k. Open items

1. **Criterion 5 (WARN < 1 %) fails formally for the tier-C heavy part**: 1.03 % overall, with A9 at 2.9 %. The strict
   re-checks of the two most-warned A9 sectors (about 11.7 % warned points per shift) agree with production to 1.4e-13 of
   the sector size, i.e. 8.8e-11 of A9's quoted error. The A7_E endpoint sectors are bitwise identical. For a gross
   check at sigma ~ 2.4 the warnings are therefore cosmetic. The criterion could be restated as "WARN < 1 % or the
   strict re-check of the most-warned sectors agrees", as already suggested for tier A (section 11, item 5).
2. **Which error to quote for C8.** For A9 the replicate error (R = 6) is 0.52x the sector-pooled one. The framework's
   linear and replicate errors for C8 are 1.37 and 1.15, against 2.42 pooled. The assembly must quote the largest
   estimator (as `assembly/run_assembly_C8.py` does with sigma_pool).
3. **A7_E has mixed N.** Chunk c000 (sectors 0-1626) ran at 22637 and chunks c001-c008 at 16001. Each sector's
   estimate is unbiased, and the replicates stay i.i.d. across shifts. `tests/budget_C8.py` prints N = 22637 (the first
   chunk) in its table; its sigma comes from the data.
4. **No all-sector independent reference exists for A9 or A7_E at eps^0** (the pilots sampled sectors). The two
   independent Z8 runs differ by a pull of 2.69 (N = 4001 vs 11321); the 4001 run was pre-asymptotic, and the delivered
   top-up has sigma_C8 = 0.015.
5. **The C9 pole check at N = 4001 was added to the prepared plan** (198.6 amdq core-h, inside the cap) to decide the
   3.47 pull at N = 1009. At N = 4001 every C9[v0d0][eps^-1] pull is <= 0.90.
6. **The cap's conversion of the personal desktop and defq core-h with 0.667 is uncalibrated** (section 12f, item 3). Raw total:
   symmetry amdq 18,722.5 + defq 77.6 physical + personal desktop 528.6 core-h. The heavy work ran on amdq only, apart from
   the N = 1009 check.
7. **The personal desktop was shared.** Another user's unscheduled processes (2026-10-05/06, load up to 270) slowed the A5_dE
   top-up (102 engine core-h against about 71 expected) and the strict re-checks. Our 19 cores briefly blocked the user's
   own continuation job 302; we freed cores by cancelling the A7_E re-check 301, which was resubmitted as 303.
8. **The Q8_v strict re-check has no result, so criterion 5 is not verified for Q8_v.**
   * The personal desktop job 288 was cancelled at 17:22:29 CEST on 2026-10-07 by an outside `scancel` (`scontrol`: CANCELLED,
     ExitCode 0:125, "CANCELLED ... DUE to SIGNAL Terminated"), after 41.9 h. This agent did not issue it; who did is
     unknown.
   * Five of the six 15,270-point blocks of the strict sector-shift had finished. Their logs show 460-1,356 warned
     points per block even at strict tolerances. The engine writes its output only at the end, so nothing is left.
   * The job was not resubmitted, out of respect for whoever cancelled it. A rerun needs about 42 h of wall on 6 threads
     (the slowest block took more than 41 cpu-h) and about 170 amdq-eq core-h.
   * The other heavy tier-B groups passed: Q6_vE and A7_d agree to 1.3e-16 of the sector size. Q8_v's production WARN
     fraction is part of the heavy part's 0.26 % (worst Q8_v chunk 5.6 %).
   * Same cfg if wanted: `runs/c8tierB_s0.01_r1_strict/s1/Q8_v_k0_s01270_strict.cfg`, one worker with 6 threads, `--mem`
     of at least 32G (RSS 12-17 GB).

### 13l. Assembly and sealed comparison (2026-10-07; `../RESULTS_C8.md`, `../assembly/README.md`)

* **Assembly** (`../assembly/run_assembly_C8.py`, strict at order C8 on every output, per replicate, three error
  estimators, quoted = largest), on the personal desktop (job 307, in a project copy without any sealed directory, under an
  audit hook; jobs 304 and 305 before it, about 2 personal-desktop core-h in all). `RESULTS_C8_independent.json` was written
  and hashed first (SHA-256 `6265093dc6f8b709...`, 2026-10-07 18:41:42 CEST); only then did the comparison read the
  sealed archive values.
  * C8 = 242.8253 +- 2.371 (sector-pooled; linear 1.370, replicate 1.145, per-job max 2.416). U = -1296.68755 +- 0.00153,
    Kv = -1487.0046 +- 0.158, J9 = -291.94 +- 9.48. C8 - J9/4 = 315.81130 +- 0.0051.
  * Every archive-free check passes (validate_C8 with the production tiers first: 0 above 3, 0 not computable; tier
    consistency; direct flags tail-model dependent). The one pull above 3 is A7_E against the pre-asymptotic conv pilot at
    N = 4001 (-3.2); the probe at N = 11321 on the same sectors agrees (-0.09).
* **Comparison.** C8 is -1.92 sigma from the claim (quoted error; -3.3/-4.0 with the linear/replicate errors). The whole
  difference is A9_1 = A9[eps^0 l^1]: ours - archive = -20.4 +- 9.3 (-2.19 sigma, 3.3e-5 relative). C8 - J9/4 agrees to
  -1.0e-3 (-0.20 sigma); U +0.27, Kv -0.27 sigma; all other sub-pieces within 1.1 sigma.
* **Check run `c8chkA7`** (assembly phase; `specs/checks_C8_A7v_A7k1.json`, tier `c8chkA7`, fresh seeds; `campaign.py seedcheck`
  over it and the 18 production, pilot and check run directories of C8 and phase 2: 1,750,860 streams, all disjoint; over
  all 34 run directories no overlap involves `c8chkA7`): A7_v k=0 and A7 k=1 at N = 5669, the two tier-C
  scalars without any independent all-sector reference. Symmetry amdq job **571036** (<NODE>, 9:54 min, 64 cores,
  **10.6 amdq core-h**, COMPLETED 0:0; `logs/symmetry/sacct_c8BC_chkA7.txt`). collect and outliers (T = 3) exit 0; WARN
  0.36 %. Tier C minus check: A7_v[eps^0 l^0] +4.1 +- 3.2 (+1.28), A7[eps^1 l^1] -2.0e-3 +- 1.8e-3 (-1.14).
  A7_v[eps^0 l^0] has error 2.8 at N = 5669 against 0.063 at 11321 (fast convergence), so the check reaches about 3 in
  C8 units.
* **Cost addendum.** `runs/c8BC_ledger.json` (19,126.8, 11:24 EDT) predates the check run; with it and the personal desktop
  assembly jobs the phase total is about 19,138.7 amdq-equivalent core-h of the 20,000 cap. Nothing of the phase is
  running.
