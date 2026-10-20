# engine: an independent numerical engine for the eps-expansion of the hard-core ordered moments

Part of the independent re-derivation of the C6/C7 inputs of `LRI_SRI_research_compendium` (read-only).
This directory contains a from-scratch numerical engine (Mellin transform in the cutoff + Hepp sectors +
Taylor subtraction with analytic pole integration + rank-1 lattice QMC), its validation, the cluster
pilots up to 8 kinks, the v2 error model with its regression, and the production plan.

**Independence.** No archived integration/evaluation code was imported, called or copied (no
hyperlog/ordered_moments/moment_series/... code was even opened). The archive was used only for
(i) definitions and conventions (the note), and (ii) *comparison* of numbers after our own numbers existed
(validation step (c), `tests/compare_archive_series.py`; the reviewer's `review/compare_archive_highmoments.py`).
The raw-coefficient list and the C6/C7 sensitivities come from the sibling `framework` agent
(`specs/framework_*.json`), and the end-to-end check calls its module. The v2 error floor is calibrated
without archive data (section 3b); archive pulls are shown afterwards, for comparison only.

**Status (2026-10-03, v2).** Phase 1 built and validated the engine (ladder (a)-(d), 255/255 archive
coefficients, pilots up to 8 kinks). The phase-1 review (verdict READY WITH FIXES) found that the error bars
of correlated combinations were wrong and that every job used the same random shifts. v2 fixes every
must-fix item of that review:

| # | review item | v2 fix | where |
|---|---|---|---|
| 1 | channel/Laurent-order errors added in quadrature; framework treats correlated inputs as independent | engine writes per-shift replicates summed over sectors per (channel, Laurent order); `collect` assembles every coefficient per replicate; sigma(C6), sigma(C7) from the framework run per replicate and from the full (block) covariance | `src/lri_engine.cpp` (`rep`), `py/lri_moments.py` (`assemble_replicates`), `py/campaign.py collect`, `tests/e2e_framework.py` |
| 2 | one seed (1234567) for every job and tier | seed = SHA-256 of (tier, group, k, chunk); `campaign.py seedcheck` proves that no two (cfg, sector, shift) random streams of one or several campaigns overlap | `py/campaign.py` |
| 3 | no error floor | floor = FLOOR_REL x L1 scale of each coefficient (engine output `abs`), FLOOR_REL = 1e-15, calibrated without archive data | section 3b, `tests/floor_calibration.py` |
| 4 | outlier criterion on raw orders; flagged endpoint sectors accepted silently | criterion on the NEEDED coefficients only (exact coefficient map, per-sector replicates), relevance against the C6/C7 budget; flagged sectors get more points (`campaign.py refine`), substituted per replicate | `py/outliers.py`, `py/campaign.py refine` |
| 5 | structurally zero coefficients omitted | explicit exact zeros (`zeros`), hard failure on genuinely missing coefficients (collect exit 2, e2e exit 2) | `assemble_replicates`, `collect`, e2e |
| 6 | non-atomic outputs | engine writes `<out>.tmp.<pid>` + fsync + rename, ends with `"complete": true`; `run_list.sh` skips only completed outputs and exits non-zero on failures; manifests, results, lattice DB written atomically; `plan` refuses to re-plan a directory with outputs | engine, `slurm/run_list.sh`, `py/` |
| 7 | OpenMP tasks in sector order (efficiency 0.57-0.81) | (sector, shift) tasks, longest first; cost-balanced sector chunks; `cfglist.txt` sorted longest first | engine, `campaign.py plan` |
| 8 | README errors | corrected (sections 3, 4b) | here |
| 9 | planner inherits quadrature errors | `plan_production.py` rewritten on replicate projections with signed framework gradients; tier 1 re-planned | section 8 |

A regression on one symmetry amdq node (job 569089, section 6) shows: phase-1 and v2 binaries give
bit-identical results; the replicate pipeline works end to end with the fixed framework (C6 = -58.6695 +-
0.0055, C7 = 51.9 +- 2.1 at regression sizes, both within 0.7 sigma of the closed forms); and the framework's
own replicate assembly reproduces the engine-side error propagation.

**Tier-1 production (6-digit target, T = 5e-5): DONE, 2026-10-03** (section 8b and `PRODUCTION_TIER1.md`).
* All 86 cfgs completed on symmetry amdq (2184.6 core-h).
* C7 was above T by two of three error estimators, so a top-up reran Q6_E, A7_v, A7_base and A5_vE one ladder
  step higher with fresh seeds (372 core-h).
* The deliverable is `runs/prod_6digit/results_final.json` / `framework_input_final.json`: sigma(C6) = 1.3-1.5e-6
  and sigma(C7) = 2.7-3.1e-5 by every estimator.
* Strict-tolerance re-evaluations of 88 most-warned sectors agree with the production values.
* Total 2942.9 allocated core-hours, including the checks.

**C8 extension (phase 3, 2026-10-03; section 11).** The engine covers every raw atom C8 = 8 T4 needs (85 scalars
beyond D4 in 50 groups, incl. A9, Z8, Q8_v, A7_E, A7_d, d^3 and d^2 E insertions) **without any change to the C++
engine**; the C6/C7 tooling reproduces tier 1 byte for byte (`tests/regress_C8.py`). Validation (archive-free) and a
cost/convergence pilot ran on the personal desktop (symmetry was down); the three production tiers are planned
(`results/plan_C8.md`, `specs/production_C8_tier{A,B,C}.json`). Tier A (W, S, L3, M21, M12, N2,
Ndelta) is cheap (~100 amdq core-h for sigma(C8 part) ~ 1e-6); tier B (U, Kv) ~ 8.4k core-h; tier C (J9) needs
~1.3e5 core-h for sigma(C8) = 0.01 and is dominated by A9[eps^0 l^1]. Already at pilot level the six 'inherited' inputs
give B_done8 = 563.4040883 +- 4.9e-5, 0.45 sigma from the archive's value quoted in the C8 brief (comparison only,
after hashing our result).

**C8 tier A production: DONE, 2026-10-04** (section 11h and `PRODUCTION_C8.md`).
* Ran on the personal desktop, because symmetry was down.
* All 21 cfgs completed with rc 0; collect, outliers and seedcheck all pass.
* sigma(C8 part) = 5.0e-7, against 7.5e-7 planned.
* A3_ddE missed its planned error by 1.69x. A 2N top-up with fresh seeds brought it to 0.27x.
* Deliverable: `runs/c8tierA/framework_input_final.json` (26 scalars, R = 6).
* Cost:
  * 183.1 allocated personal-desktop core-h, i.e. 122.2 amdq-equivalent; production alone was 154.5 personal-desktop;
  * the raw personal-desktop total is above the 156 core-h cap (`PRODUCTION_C8.md` section 2).
* Tiers B and C were not launched then (they ran 2026-10-04/06, below).

**C8 tiers B and C: DONE, 2026-10-04 to 2026-10-07** (section 11i and `PRODUCTION_C8.md` sections 12-13).
* Approved: tier B at sigma(C8 without J9) = 0.01, and tier C as a gross check at total sigma(C8) ~ 3. Hard cap 20,000
  amdq-equivalent core-h for the whole phase.
* Ran on symmetry amdq for the heavy groups (at most 8 of our nodes) and on the personal desktop for the cheap groups and the
  strict re-checks; no Expanse.
* The budget guard ran throughout:
  * an amdq probe re-planned the heavy groups: Q8_v at 91621, Q6_vE raised to 370759, A9 at 8009, A7_E at 22637;
  * guard 2 stopped once during tier C (projected 20,079), and A7_E's last 8 chunks were finished at N = 16001;
  * one top-up per tier (A5_dE 4x, Z8 2.8x), each with fresh seeds.
* **Tier B: sigma(C8 part) = 5.1e-3; sigma(C8 without J9) = 5.1e-3, against the 0.01 target.**
  * U = -1296.68755 +- 0.0014;
  * Kv = -1487.005 +- 0.16.
* **Tier C: sigma(C8 part) = 2.4** (pooled; replicate 1.4), against the target of ~3. J9 = -291.9 +- 5.5 (lin).
* **Assembly check.** The framework at order C8 (strict, production + tiers A+B+C) has no missing input: C8 = 242.83 +-
  1.37 (lin) / 1.15 (rep) / 2.42 (pooled).
* Checks:
  * `validate_C8.py`: 0 checks above 3 and 0 not computable. The C9 pole at eps^-1 was confirmed at N = 4001 (max |pull|
    0.90) after the N = 1009 check gave 3.47 (2.3 with pooled errors).
  * Exact scalars: PASS.
  * Strict re-checks of Q6_vE, A7_d, A9, A7_E and Z8 agree to <= 1.4e-13 of the sector size.
  * The Q8_v strict re-check has no result: job 288 was cancelled from outside after 41.9 h, with 5 of its 6 point
    blocks done (`PRODUCTION_C8.md` 13g and 13k item 8).
* Deliverables:
  * `runs/c8tierB_s0.01_r1/framework_input_final.json`;
  * `runs/c8tierC_s3_r2/framework_input_final.json`;
  * `runs/c8tiersABC/framework_input_final.json` (A + B + C);
  * SHA-256s in `runs/c8BC_SHA256SUMS.txt`.
* Cost: 19,126.8 of the 20,000 amdq-equivalent core-h: tier B 8,681, tier C 10,144, probe 45, C9 checks 250, tier-A
  leftover 7 (`PRODUCTION_C8.md` 13j).
* **Assembly and sealed comparison: done 2026-10-07** (`../RESULTS_C8.md`; `PRODUCTION_C8.md` 13l). C8 = 242.825 +- 2.37
  (largest of three estimators) against the claim 247.381: -1.92 sigma, the whole difference in A9[eps^0 l^1] (ours -
  archive = -20.4 +- 9.3, -2.19 sigma). C8 - J9/4 = 315.81130 +- 0.0051 agrees to -1.0e-3 (-0.20 sigma); U +0.27 and Kv
  -0.27 sigma. One assembly check run (`runs/c8chkA7`, A7_v k=0 and A7 k=1 at N = 5669, amdq 571036, 10.6 core-h):
  agrees. Phase total about 19,139 of 20,000.

## 1. What is computed

Raw moments at v=1, delta=0, unit interval, consecutive-gap hard core `X_{i+1}-X_i >= eps` (note l.255, 367-377):

    I(eps) = int_{Omega_n(eps)} W_n [D_{2m}] P(S_1..S_4, E_1..E_3) dX,     q_i = (-1)^{i+1}
    W_n = prod_{i<j} (X_j - X_i)^{2 q_i q_j}
    S_k = sum_{i<j} q_i q_j log^k(X_j - X_i),   E_k = sum_i q_i [log^k X_i +- log^k(1-X_i)]  (+ odd n, - even n)

`P` is generated from `d^nv_v d^nd_delta d^ne_eta [W(v,delta) U(eta,delta)]` with
`f_delta(r) = (r^delta-1)/delta` (`py/lri_moments.py: insertion_poly`): **raw derivatives**, the same
"derivative convention" as the framework (`d` = d/d delta, `E` = EE). E.g. `vd -> 2 S1 S2 + S2`,
`dd -> S2^2 + 2/3 S3`, `vE -> 2 S1 E1`, `dE -> S2 E1 + E2/2`.
Output: coefficients `c_{k,j}` of `eps^k log^j eps`, with QMC errors from shift replicates.

## 2. Method

1. **Mellin transform in the cutoff.** `I~(s) = int_0^inf eps^{s-1} I(eps) deps = (1/s) int F(r) m(r)^s dr`,
   `m` = smallest *internal* gap. `eps^k log^j eps` <-> pole `(-1)^j j!/(s+k)^{j+1}`, so
   `c_{k,j} = (-1)^j/j! [(s+k)^{-(j+1)}] I~(s)`; each needed coefficient is a Laurent coefficient at `s0=-k`.
2. **Geometry.**
   * `angular` (no endpoint source): translation (factor 1-R) and radial scale R are integrated analytically.
     With `log(gap sum) = log R + log(x-sum)`:
     `I~(s) = (1/s) sum_j (-1)^j [(kappa+s)^{-j-1} - (kappa+s+1)^{-j-1}] A[D^j P](s)`,
     `kappa = (n-1) + deg W (+1 for Q)`, `D S_k = k S_{k-1}`, `S_0 = sum_{i<j} q_i q_j`;
     `A[P](s) = int_{simplex} W D P(log x) m(x)^s` over the (n-2)-simplex of internal gap fractions.
   * `full` (endpoint moments, EE): all n+1 spacings `r_0..r_n` on the n-simplex, `I~ = (1/s) B(s)`.
3. **Hepp sectors, Cheng-Wu chart.** For every total order of the spacings: `x_{sigma(1)}=1`,
   `x_{sigma(i+1)} = t_1...t_i`, `t in [0,1]^{M-1}`. Every sum of spacings is `monomial*(1+P(t))`, `P` a sum
   of products of consecutive t's. The integrand is `prod_l t_l^{a_l-1+b_l e} G(t;e)`, `e=s-s0`, `G` smooth;
   `a_l = -(#neutral runs among the M-l smallest spacings) [+1 if all odd gaps are among them, Q]`;
   `b_l=1` if the variable scales an internal gap. The projective factor `Sigma^{-(kappa+s)}`
   (Sigma = sum of all spacings in the chart) and the log shifts `log x_I - log Sigma` are exact.
   Reflection folds the sectors (weight 2): 1 / 3 / 12 / 60 / 360 / 2520 sectors for 3..8 kinks (angular),
   12 / 60 / 360 / 2520 for 3..6 kinks (full).
4. **Subtraction.** Every variable with `a_l<=0` is Taylor-subtracted to order `N_l=-a_l` (power divergences
   included). Taylor terms are integrated analytically, `int t^{a+j-1+e} log^p t = (-1)^p p!/(a+j+e)^{p+1}`;
   the remainders numerically. `e` is a formal parameter; logs of subtracted variables from insertions are
   formal variables `mu_l` in the pole terms. Lower-dimensional (pole) terms drop the transform Jacobian of
   their pole variables, i.e. they are integrated exactly in those coordinates (projected lattice rule).
5. **Jets.** Taylor coefficients are computed numerically per point as truncated multivariate power series:
   multiplication/division by the sparse multilinear factors `(1+P_I)`, `W = Q^2` with
   `Q = prod_same(1+P)/prod_opp(1+P)`, a recursion for `log(1+P)`, `S_1` and `E_1` via the log of a product
   (one log instead of one per sum), formal-e expansion of `Sigma^{-e}`, and a keep/contract recursion that
   produces all pole/remainder combinations at cost ~ `size * prod(1+1/(N+1))` instead of `size * 2^|A|`.
6. **Numerical stability (essential).** Nested subtraction loses relative precision multiplicatively,
   `~ u * prod_k t_k^{-(N_k+1)}`; logarithmic insertions add `(1+sum|log t|)^D`. All jet arithmetic is in
   double-double (`src/dd.hpp`, ~32 digits), and at every QMC point an error estimate selects variables
   that are switched to *tail mode*: their remainder is summed from Taylor orders `N+1..N+m` at t=0
   (no cancellation, `(4t)^m < 1e-16`, jet size capped). Without this, the results did not converge
   (errors grew with N, e.g. Q4_vd); with it Q4_vd converges like N^-3.3 to 12 digits.
7. **QMC.** Rank-1 Korobov lattices; the generator minimizes a *weighted* P_2 criterion (product weights
   0.1), because the pole terms of every sector are integrated with low-dimensional projections of the same
   lattice (unit weights gave 2D projections 20x worse and visibly wrong error bars). Korobov r=3
   periodizing transform, R random shifts per sector (6 in production). The shift of (sector s, replicate r)
   is drawn from splitmix64 seeded with `seed ^ 0x1234567 (s+1) ^ 0x9876543 (r+1)`; since v2 the cfg seed is
   a hash of (tier, group, k, chunk), so every job, chunk and tier has its own shifts.
8. **Replicates (v2).** For every channel and Laurent order the engine writes, per replicate r, the sum over
   the cfg's sectors of the shift-r estimate (`rep[r][order]`), the per-sector per-shift values
   (`per_sector[].rep`) and the L1 scale `abs[order]` = sum over sectors of `(1/N) sum_points |f|`. Shifts of
   different sectors are independent, so the R replicates are i.i.d. unbiased estimates of the whole sector
   range; chunks of one job are merged replicate by replicate.
9. **Scheduling (v2).** OpenMP tasks are single (sector, shift) pairs (`taskshifts 1`), run longest first by
   the estimated cost `2^K prod_k (N_k+1)` over the K subtracted variables (correlation with the measured
   per-sector cpu 0.97-0.99 on the pilot5 Q8, A7_v, Q6_E, A5_vE, Q6_d sectors). Point blocks are still split
   exactly as in phase 1 when there are fewer tasks than 2 x threads, so the results are bit for bit those of
   the phase-1 engine. `campaign.py plan` cuts the sector range of a job into contiguous chunks of equal
   *estimated cost* (engine `--sectors-info`) and writes `cfglist.txt` longest first.

## 3. Validation (phase 1, all PASS)

| step | what | result |
|---|---|---|
| (a) | Z2 = 1/eps + l - 1, Q2 = -l - 1 + eps (0-dim, exact); A3 (1D) and C3 = A3 - Z2 = 2l^2 + 5l + 3 - 2z2 | exact / 1e-13; A3(eps) also checked against direct quadrature at finite eps to 4e-14 |
| (b) | K4 = Q4 - Q2 Z2: -4/3, -6, -8+4z2, P4+4z2-10;  C5 = A5 - A3Z2 + Z2^2 - Z4: 10/3, 62/3, 95/2-24z2, 96-40z2-S5; power divergences cancel; `A_{G5}(q) = 80/q^3 - 68/q^2 - (56+48z2)/q + S5` reproduced directly | all within 1-2 sigma (errors 1e-10..5e-9) |
| (b) | EE endpoint constants: d_v EE A_{3,0} = -108+60z2+22z3-34z4+16 log2; EE Q4 full expansion -2z2/eps + l^3 - (1+8z2)l^2 - (2+32z2+28z3)l + 6-12z2-54z3-25z4 | diff 2e-8 (err 3e-8), 4e-7 (err 4e-7); all logs OK |
| (c) | 255 coefficients of A3, Z4, Q4, A5 (base, v, d, vd, vv; all needed eps powers) vs the archive's exact series files evaluated with archived period tables (comparison only) | 255/255 agree within 5 sigma; e.g. Q4_vd[eps^0 l^0] = 948.048588437 +- 3e-12 vs 948.0485884370823 |
| (d) | higher logs of C7, d_vC7, K8 (note l.719-731, 1051-1063) from 7- and 8-kink runs (A7, A7_v, Q8 + lower moments) | 10/10 PASS, e.g. [l^4]C7 diff 5e-8, [l^5]d_vC7 diff 2e-7, [l^5]K8 diff 1e-7 (err 3e-7) |
| extra | angular vs full geometry (radial decomposition with log insertions vs full simplex) for A3_v, Z4 | agree within errors |

Correction (review item 8): the errors quoted in (b)-(d) are the phase-1 quadrature errors. For higher-log
coefficients of multi-channel moments they are 1.3-2.3 times too small (section 6C, review test C), so the
(d) PASS margins are smaller than printed; the v2 regression re-checks the same coefficients with replicate
errors against independent runs and the closed forms (section 6). Outputs: `results/compare_archive_series.txt`,
`results/validate_d.txt`, `results/angular_vs_full.txt`, `results/validation_c.json`, `runs/pilot_logs/`.

### 3b. Error model (v2)

* **Replicates.** A coefficient `c_{k,j}` is an exact linear map of channel Laurent coefficients
  (`coefficient_map`: prefactor series x channel orders x `(-1)^j/j!`). It is evaluated separately in each
  replicate r (all sectors, all chunks, refined sectors substituted); value = mean, `stat = sd/sqrt(R)`.
  This keeps every correlation between channels, Laurent orders and the coefficients of one job.
* **Covariance.** Different jobs (group, k) use independent seeds, so the covariance is block diagonal with
  one block per job (`results.json: errors[..].block`). `tests/e2e_framework.py` reports (i) `sigma_rep`: the
  framework run once per replicate (all jobs' replicate r together; R common), sd/sqrt(R), plus the floor;
  (ii) `sigma_cov`: g^T Sigma g with the replicate covariance of each block (any R), plus the floor;
  (iii) `sigma_indep` (phase-1 style, for comparison only). With R=8 (6 in production) the replicate error has
  R-1 degrees of freedom: pulls of a single job follow Student t (P(|t_7|>3) = 2%).
* **Floor.** `sigma_floor = FLOOR_REL * l1`, `l1 = sum |w| abs` (the size of the terms that cancel in the
  coefficient). Calibration (`tests/floor_calibration.py`, `results/floor_calibration.txt`, no archive data):
  1. strict tolerances (errTarget, tailTol 1e-16, maxJet 2e6, tailMax 0.05) on the same lattice and shifts
     change none of 52 coefficients (A3 family, Z4, Q4, Q4_vd, A3_E, A5): the tolerances leave no systematic;
  2. two independent runs (replay5 seed 1234567 vs new hashed seeds, same N, 246 coefficients): stat-only pulls
     have rms 1.15 and 24 of 213 above 2 in the precise regime (sigma/l1 < 1e-12, rounding-level coefficients);
     the smallest floor with consistent pulls (rms <= 1.2, <= 5% above 2, <= 2% above 3) is 2e-17;
  3. the systematic double rounding of the exact prefactor weights and pole factors is identical in every run
     and invisible to 1 and 2, so the floor is set a priori to ~10 ulp: **FLOOR_REL = 1e-15** (= 50 x the data
     minimum). It matters only for coefficients known to <~1e-13 relative; it is negligible for C6/C7 at both
     tiers (sigma_floor(C7) = 1e-9).
* **Zeros and missing coefficients.** A needed coefficient whose Laurent order lies below the lowest order that
  can occur is an exact structural zero (A3[eps^-1 l^1], A3[eps^2 l^1], Z4[eps^-2 l^1]): written to
  `results.json: zeros`, with no replicates. A needed coefficient that was not computed, or a missing chunk
  output, makes `collect` exit 2; `e2e_framework.py` exits 2 when any of the framework's required inputs is
  absent (the framework itself runs in strict mode).
* **Formats for the framework.** `results.json` (engine layout, read by the framework adapter
  `load_engine_results`) and `framework_input.json` (`lri-framework-raw/1`: replicates, `sys` = floor,
  `block` = job), see `../framework/INPUT_FORMAT.md`.

## 4. Pilots, cost and convergence (phase 1)

All pilots ran through Slurm: symmetry `amdq` (AMD EPYC, 64 physical cores, whole node) and the personal desktop
(Intel, 16 cores, `--time=0`, TimeLimit=UNLIMITED verified). Run directories: `runs/pilot_logs` (validation (d)),
`runs/pilot2` (full-sector runs, 6-8 kinks), `runs/pilot3` (single-sector convergence to N=1e6),
`runs/pilot4` (cost/convergence benchmark of every production group on a sector sample),
`runs/pilot5` (all 46 groups, all sectors, modest N: end-to-end input for the framework). These phase-1
outputs have no replicates; several were written by intermediate phase-1 binaries (section 6B).

**Cost per point** (one lattice point x one shift x one sector, AMD core):

| moment | geometry, dim, sectors | us/point |
|---|---|---|
| A3 family (incl. dd, vdd, vvv) | angular 1D, 1 | 1-17 |
| EA3 family (E, dE, vE, vdE, vvE) | full 3D, 12 | 10-25 |
| Q4/Z4 families | angular 2D, 3 | 2-80 |
| EQ4/EZ4 (Q4_E, Q4_dE, Q4_vE, Z4_E, Z4_vE) | full 4D, 60 | 13-50 |
| A5, A5_v, A5_vv, A5_d, A5_vd | angular 3D, 12 | 16, 46, 110, 137, 440 |
| A5_E, A5_vE | full 5D, 360 | 39, 95 |
| Z6, Z6_v, Q6, Q6_v, Q6_d | angular 4D, 60 | 35, 160, 68, 180, 1200 (before the S2 fast path) |
| Q6_E | full 6D, 2520 | 105 |
| A7, A7_v | angular 5D, 360 | 260-340, ~1000 |
| Q8 | angular 6D, 2520 | 1070 (0.4-5 ms by subtraction depth) |

**Convergence** (`results/pilot3_convergence.txt`, standard error of the finite part e^0, 8 shifts):
A7 (5D, sector 64): 4.8e-7, 3.3e-9, 1.1e-10 at N = 64007, 262139, 1048573 (rate N^-3.6 then N^-2.5);
Q8 (6D, sectors 1200-1201, the deepest class): 5.8e-3, 1.4e-4, 4.9e-6 at N = 16001, 64007, 262139 (N^-2.7, N^-2.4);
Q6_E (6D): 1.4e-3, 2.1e-5, 4.3e-7 (N^-3, N^-2.8); A7_v: 2.4e-2, 9.9e-6, 1.6e-7; A5_E (5D): N^-3.2.
Below N~1e4 (5D) and ~6e4 (6D) the lattice rules are pre-asymptotic.

**Two numerical lessons from the pilots** (both fixed in the phase-1 engine): (1) unweighted Korobov
lattices have poor 2D/3D projections, which spoil the pole terms; the weighted criterion fixed it.
(2) Points where 4-5 sector variables are small at once need large tail jets; with the jet size capped at
6000 a single point in the deepest Q8 sector produced an error of 23 on that sector; with the cap at 2e5 and
tail/cancellation tolerances 1e-13 the sector is fine. ~1e-4 (A7) to ~1e-3 (Q8) of the points of the deepest
sectors keep a conservative error estimate above 1e-11 (`WARN` lines); review test D showed that a strict
re-evaluation of the most affected Q8 and A7_v sectors agrees to double rounding (8-15 x the cost).

## 4b. End-to-end pilot through the framework (phase 1, pilot5; corrected)

`runs/pilot5` (N = 262139 (d<=3), 64007 (4D), 16001 (5D), 4001 (6D), 8 shifts, seed 1234567 everywhere,
quadrature errors) through the framework gave C5 to 4e-9, C6 = -58.6670 +- 0.0019 (closed form -58.66570,
0.7 sigma), D4 = -2.33 +- 0.14 and C7 = 51.88 +- 0.56 (closed form 51.069, 1.5 sigma). Corrections (review):
* The 1.5 sigma offset of C7 (and of K) comes from Q6_E at the pre-asymptotic N=4001 (pull 2.0 against the
  archived series) plus Q8 (0.5 sigma); with the reviewer's Q6_E at N=64007, C7 = 51.288 +- 0.48 (0.46 sigma).
* K does have an archived reference (Knew = -906.982409850918, comparison only); Phi, Psi, P, alpha, beta,
  gamma also have archived values and agree (reviewer's check).
* The phase-1 errors there are quadrature errors (wrong for correlated combinations) and all jobs shared
  shifts; the v2 end-to-end result is in section 6E.
Files: `results/e2e_pilot5.txt`, `results/e2e_pilot5_raw_flat.json`, `review/e2e_pilot5_with_Q6E_N64007.txt`.

## 5. Files

| path | content |
|---|---|
| `src/lri_engine.cpp`, `src/dd.hpp` | C++17/OpenMP engine v2 (`lri_engine job.cfg`; `--korobov N d`; `job.cfg --point sector t...`; `job.cfg --sectors-info`) |
| `legacy/lri_engine_phase1.cpp` | the phase-1 engine source (md5 e7280289...), kept for the bitwise regression |
| `py/lri_moments.py` | insertion polynomials, radial prefactors, `coefficient_map`, `merge_replicates`, `assemble_replicates`, `FLOOR_REL`; legacy quadrature `assemble_job`; local driver |
| `py/campaign.py` | `plan` (hashed seeds, cost-balanced chunks, longest-first list), `collect` (replicates, floor, zeros, `framework_input.json`), `refine`, `seedcheck` |
| `py/outliers.py` | acceptance check on the needed coefficients (per-sector replicates, relevance vs the C6/C7 budget) |
| `py/make_spec.py` | campaign spec from `specs/production_D4.json` (with the needed coefficients per group) |
| `py/plan_production.py` | production planner on replicate projections and signed framework gradients |
| `py/production_list.py`, `py/series.py`, `py/pilot_compare.py`, `py/make_benchmark_spec.py` | group list, series algebra, phase-1 helpers |
| `tests/e2e_framework.py` | engine `results.json` -> framework: values, sigma_rep, sigma_cov, gradient check, signed gradients (its fd check uses h = 1e-3 x sigma and gives a false exit 3 at production errors, see `PRODUCTION_TIER1.md` section 7) |
| `tests/production_checks.py` | run health (completion, non-finite values, WARN statistics, unexpected log lines), replicate vs sector-pooled error per needed coefficient and per job projection on C6/C7 |
| `tests/strict_recheck.py` | `prepare`: re-run the most-warned sectors of a run with strict numerics (same lattice, seed and shifts); `compare`: default vs strict through the coefficient map |
| `py/merge_runs.py` | replace whole groups of a collected run by those of top-up runs -> `results_<tag>.json`, `framework_input_<tag>.json` |
| `tests/regress_prepare.py`, `tests/regress_compare.py`, `tests/floor_calibration.py` | v2 regression set-up, report, floor calibration |
| `tests/validate_c.py`, `tests/compare_archive_series.py`, `tests/validate_d.py`, `tests/bench_local.sh` | phase-1 validation |
| `slurm/` | `build.sh` (x86-64-v3; `SRC=`/`OUT=` for the phase-1 build), `run_list.sh`, `regress_symmetry.sbatch`, `production_symmetry.sbatch`, `production_personal-desktop.sbatch`, `submit_production.sh`, `run_packed.sh` + `packed_symmetry.sbatch` (several single-sector cfgs per node, P/NPAR threads each), pilot scripts |
| `specs/` | `production_D4.json` (46 groups, 116 coefficients), `production_6digit.json`/`production_8digit.json` (v2 plan), `production_6digit_topup1.json` (tier-1 top-up), `poles_check1.json`, `kplus1_check.json`, `conv_check1.json` (assembly-phase checks, section 8c), `regress_v2.json`, `gradients_C6_C7_D4.json` (signed, engine point), framework lists, pilot specs |
| `runs/` | phase-1 pilots (`pilot*`), v2 regression (`regress_v2/{direct_v1,direct_v2,replay5,strict,new,replay4}`), tier-1 production `prod_6digit` (with `results.json`, `results_final.json`, checks), its top-up `prod_6digit_topup1`, strict re-checks `prod_6digit_strict/{lowdim,a7v,deep6}`, assembly-phase check runs `poles1`, `kplus1`, `conv1` (section 8c) |
| `PRODUCTION_TIER1.md` | tier-1 production log: jobs, timings, failures, warnings, acceptance, top-up, core-hours |
| `results/` | `regress_v2_report.txt`, `floor_calibration.txt`, `e2e_regress_v2.{txt,json}`, `production_plan.md`, `compare_archive_regress_v2.txt` (comparison only), phase-1 validation outputs |
| `review/` | the phase-1 reviewer's scripts and outputs (unchanged) |
| C8 (section 11) | `py/production_list_C8.py`, `py/make_spec_C8.py`, `py/plan_C8.py`; `tests/validate_C8.py`, `tests/direct_C8.py`, `tests/preview_C8.py`, `tests/compare_brief_C8.py` (comparison only), `tests/compare_calib.py`, `tests/dryrun_tiers.py`, `tests/regress_C8.py`; `slurm/submit_C8.sh`, `slurm/pilot_C8_{personal-desktop,symmetry}.sbatch`; specs `production_C8*.json`, `{val,conv,kplus1}_C8.json`, `gradients_C8.json`, `framework_*C8*.json`; runs `c8val`, `c8conv`, `c8kplus1`, `c8strict`, `calib_personal-desktop`; results `plan_C8*.{md,json}`, `validate_C8.*`, `direct_C8*`, `preview_C8.json`, `compare_brief_C8.json`, `calib_personal-desktop.json`, `regress_C8.txt`, `dryrun_tiers_C8.txt`, `production_checks_C8_*.json`, `strict_recheck_C8.txt` |
| C8 tier A (section 11h) | `PRODUCTION_C8.md` (log); runs `c8tierA` (deliverable `results_final.json`, `framework_input_final.json`), `c8tierA_topup1`, `c8tierA_strict/{lowdim,q6vv,q6vd}`; spec `production_C8_tierA_topup1.json`; `tests/budget_C8.py` (achieved vs planned sigma_C8 per job, the planner's projection), `tests/tier_vs_pilot_C8.py` (pulls of a tier against earlier independent runs of the same jobs); `results/validate_C8_tierA.{txt,json}`; `logs/personal-desktop/sri_eng_c8A_*.out` |

## 6. v2 regression (symmetry amdq, one node)

Prepared locally by `tests/regress_prepare.py` (`runs/regress_v2/`), run by `slurm/regress_symmetry.sbatch`
(job 569089 on <NODE>: builds the v2 and the phase-1 engine from source with the same g++ 11.4 /
x86-64-v3, then runs the six lists below; 1 h 37 min wall, ~107 core-hours, MaxRSS 37 GB), plus job 569201
(refinement round, 3 cfgs) and job 569290 (phase-1 binary on two cfgs, 5 min). Report:
`results/regress_v2_report.txt` (`tests/regress_compare.py`); logs: `logs/symmetry/sri_eng_regress_v2_*.out`
(remote `<SCRATCH>/sri_c6c7/engine/logs/`).

**A. Bit-for-bit identity, phase-1 vs v2 binary** (`direct_v1` vs `direct_v2`, same cfg, node, threads):
Q8 sectors 0-315 at N=1009 (phase 1: whole-sector tasks; v2: longest-first (sector, shift) tasks), Q6_E
chunk of 315 sectors, A7_v 60 sectors (2 channels), A3_vdE and A5_vd (point-block split), Q4_dE: **all six
BIT-IDENTICAL** (6,438 values: Laurent coefficients, errors, per-sector values). The mean of the new per-shift
replicates equals the value to <= 6e-16 of the L1 scale.

**B. Stored phase-1 outputs** (`replay5` = pilot5 cfgs without Q8/A7_v/Q6_d/A7, `replay4` = all pilot4 cfgs;
same cfgs and seeds): 60/84 and 23/40 outputs bit-identical, including Q8 N=64007 (60 sectors). Every
differing output was written before the final phase-1 binary was built (21:23 EDT; the outputs are from
20:46-21:12, i.e. from intermediate phase-1 engines with the earlier jet cap / tolerances). Differences are
negligible for replay5 (max pull 0.13); the largest are A7 N=64007/16001 and A7_v N=16001 (max pull 2.2,
1.2, 0.6, one deep sector each). Job 569290 ran the phase-1 binary on A7 and A7_v N=16001: it reproduces v2
**bit for bit** and differs from the stored files, which therefore predate the phase-1 fixes.

**C. Replicate vs phase-1 quadrature errors of the same runs** (replay5): multi-channel coefficients median
ratio 0.78; the [l^1] coefficients that feed the beta functions were overestimated (A5_vd 0.07, A5_vv 0.15,
Q6_v 0.24, Z6_v 0.17, A5_d 0.29, Q4_vd 0.31), higher logs underestimated (ratios 1.3-1.9); single-channel
median 1.00. This reproduces review test C.

**D. Statistical consistency** (`new`, hashed seeds, vs pilot5/replay5, seed 1234567): 343 coefficients,
rms pull 0.62, 8 (2.3%) above 2, 3 (0.9%) above 3 (Q6_d[eps^0 l^2] at N=16001 and Q4_E[eps^0 l^1,2], none
needed); the 113 needed coefficients: rms pull 0.43, none above 2.

**E. End to end through the fixed framework** (`new`: all 46 groups, 77 cfgs, R=8, 32 core-hours; pilot5 sizes
except Q8 N=1009, A7_v and A7 N=4001, Q6_d N=16001, A5_vd N=64007): 116/116 required inputs (3 structural
zeros); `results/e2e_regress_v2.{txt,json}`.

| output | value | sigma_rep | sigma_cov | closed form / reference | pull |
|---|---|---|---|---|---|
| a, p, A, E, c, f, b | e.g. a = -6.5797362673929056 | 5.6e-14 (floor) | 5.6e-14 | closed forms | <= 0.07 |
| V, alpha, beta, gamma | e.g. V = -19.5187410115743845 | 2.5e-12 | 2.5e-12 | framework 1D values | <= 0.03 |
| G, q, L, M, Q | 32.763409276838, -103.560357927043, -7.677303759056, 13.315217322863, -107.065481495548 | 1.1e-11 ... 1.6e-10 | | | |
| k, N, P | 104.6723927936, 210.0305972, 718.243494 | 1.1e-7, 2.4e-6, 9.3e-5 | 1.3e-7, 2.9e-6, 8.3e-5 | | |
| J, Omega, K | 32.2702, -234.431, -915.6 | 0.014, 0.19, 21.7 | 0.015, 0.19, 22.8 | | |
| C5 | 29.237811574694 | 1.4e-8 | 1.6e-8 | 29.2378115809900 | -0.40 |
| **C6** | **-58.66950** | 0.0052 | 0.0055 | -58.6656974742253 | -0.69 |
| D4 | -2.33 | 0.51 | 0.54 | -2.5346297995383 | +0.38 |
| **C7** | **51.88** | 2.05 | 2.14 | 51.0689886129281 | +0.38 |

The framework's own replicate assembly (`../framework/run_framework.py --raw runs/regress_v2/new/framework_input.json`,
`results/framework_on_regress_v2.txt`; also with `results.json` through its engine adapter) gives the same
values and sigma_lin = 0.00554 / 2.14, rep_se = 0.0052 / 2.05 for C6 / C7: two independent implementations of
the replicate propagation agree. The gradient convention check (central difference along a random +-sigma
direction) agrees to <= 8e-8. The errors at these regression sizes are dominated by J (A7, N=4001) for C6 and
by K (Q8, N=1009) for C7. Comparison only (archive, after our values existed): K = -915.6 +- 22.8 vs archived
-906.98 (0.4 sigma), Omega = -234.431 +- 0.192 vs -234.4215 (0.05 sigma), J = 32.2702 +- 0.0148 vs 32.28032
(0.7 sigma).

**F. Error floor:** section 3b, `results/floor_calibration.txt`.

**G. Acceptance check and refinement.** `outliers.py` on replay5 and new flags 3 sectors, all on
Z4_E[eps^-1 l^0] (an endpoint moment; boundary sectors 6, 48, 50 carry 2.4-2.8e-11 of its 3.8e-11 error),
none on a relevant coefficient at T=5e-5 (15 of 113 needed coefficients are relevant at regression sizes);
the old criterion's flags (A5_E sector 345, Q4_dE/Z4_vE sector 14) do not dominate any needed coefficient.
The refinement path was exercised on the cluster anyway (`refine --all`, job 569201): the three sectors at
N=262139 (4x) were substituted per replicate, Z4_E[eps^-1 l^0] = 1.2898681337303 +- 3.8e-11 ->
1.2898681336867 +- 1.8e-11 (2 z2 - 2 = 1.2898681336965: 0.9 -> 0.5 sigma); one further boundary sector (8)
now dominates that coefficient. `outliers.py` exits 0.

**H. Load balance.** replay5 total wall 1171 s (phase 1) -> 922 s (v2); 315-sector Q6_E chunks 35 -> 20 s;
Q8 N=64007 1202 -> 971 s; A7_v N=64007 822 -> 763 s. Rebuilding the evaluator contexts per (sector, shift)
task costs extra cpu only at tiny N (Q8 at N=1009: +18% cpu, wall -4%); at production N it is < 0.1%.

**I. Archive comparison of the raw coefficients (comparison only, reviewer's evaluator, after our values):**
211 coefficients of `new`; quoted relative error < 1e-12: rms pull 0.29, none above 2 (phase 1 with
quadrature errors: 25% above 3); 1e-12..1e-9: rms 1.17, 3 above 2, none above 3; >= 1e-9: rms 1.04, one above
3 (Q6_d[eps^0 l^2] = 4.0 sigma at N=16001, not needed); the 47 needed coefficients compared: rms 0.75, none
above 3. Output (stored by the gate review, same script, same numbers): `results/compare_archive_regress_v2.txt`.

## 7. How to run

```bash
# local build (macOS, Homebrew clang + libomp); cluster: bash slurm/build.sh (g++ -O3 -march=x86-64-v3)
clang++ -O3 -std=c++17 -fopenmp -I/opt/homebrew/opt/libomp/include -L/opt/homebrew/opt/libomp/lib \
        -ffp-contract=off src/lri_engine.cpp -o bin/lri_engine
python3 py/lri_moments.py Q 4 --nv 1 --nd 1 --powers 0 --N 64007 --jmin 1      # one small moment, locally
# a campaign
python3 py/make_spec.py --tier mytier --out specs/my.json --shifts 6 --N 16001 [--set Q8_base:N=...,chunks=...]
python3 py/campaign.py plan specs/my.json runs/my                 # on a compute node for large N (lattice search)
sbatch --array=1-$(wc -l < runs/my/cfglist.txt)%8 slurm/production_symmetry.sbatch runs/my 1
python3 py/campaign.py collect runs/my                            # -> results.json, framework_input.json
python3 py/outliers.py runs/my --T 5e-5 --json runs/my/flags.json # exit 1: relevant flagged sectors
python3 py/campaign.py refine runs/my runs/my/flags.json          # then run cfglist_refine.txt, collect again
python3 tests/e2e_framework.py runs/my/results.json --out results/e2e_my.json
python3 ../framework/run_framework.py --raw runs/my/framework_input.json --order D4   # framework's own replicate assembly
python3 py/campaign.py seedcheck runs/my runs/other_tier          # no shared random streams between campaigns
python3 tests/production_checks.py runs/my --json runs/my/production_checks.json   # WARN stats, rep vs pooled errors
python3 tests/strict_recheck.py prepare runs/my runs/my_strict/deep Q8_base:20:1 A7_v:20:2   # most-warned sectors
sbatch -J strict --array=1-3 slurm/packed_symmetry.sbatch runs/my_strict/deep 7 7          # 7 cfgs x 9 threads/node
python3 tests/strict_recheck.py compare runs/my runs/my_strict/deep
python3 py/merge_runs.py runs/my runs/my_topup --tag final        # top-up groups replace whole groups
```

Operational notes (gate review, 2026-10-03):
* `../framework` exists only on the Mac (not on symmetry): run `tests/e2e_framework.py` and `run_framework.py`
  locally after copying `results.json` and `framework_input.json` back (both take < 1 min).
* `campaign.py refine` calls `korobov()` for the refined N; if that (N, d) is not in `py/korobov_db_g01.json`
  the lattice search (~1-2 min for N ~ 1e6-4e6) must run on a compute node (`srun`), not on the login node.
* The personal-desktop copy `<DATA>/<USER>/sri_c6c7/engine` is a STALE pre-v2 engine (src md5 cc5f0189,
  old `run_list.sh`). Sync `src/ py/ slurm/ specs/` and rebuild there (`bash slurm/build.sh`) before using
  `slurm/production_personal-desktop.sbatch`; otherwise its outputs lack replicates and the `complete` marker and
  `collect` rejects them (exit 2).

## 8. Production plan (v2, re-planned; tier 1 launched and finished 2026-10-03, see 8b)

`python3 py/plan_production.py --src runs/regress_v2/replay4 --src runs/regress_v2/new --src runs/regress_v2/replay5`
(gradients `specs/gradients_C6_C7_D4.json`: signed dC6/dx, dC7/dx, dD4/dx of the framework at the engine's
regression point, not the archive point) -> `results/production_plan.md`, `specs/production_6digit.json`,
`specs/production_8digit.json`.

**Error model.** Per group, the replicate projection `D_r = sum_i dC/dx_i (x_{i,r} - mean_i)` of its needed
coefficients (exact correlations) at the reference run with the largest N (replay4: pilot4 sector samples at
N=64007 for the 5D/6D groups; replay5/new: full sectors at the pilot5 sizes), scaled by the sector stride,
by R_ref/6 (production uses **6 shifts for every group**, so the per-replicate framework assembly has one R),
by (N/N_ref)^-alpha, plus the floor. alpha = 2.4 (6D), 2.8 (5D), 2.3 (4D), 3 (<=3D), lowered to the measured
replicate-error rate when that is slower (endpoint moments: Q4_dE 1.41, Z4_vE 1.69, Q4_vE 1.85). Measured
rates of the expensive groups between N=16001 and 64007: Q8 3.74, A7_v 4.58, A7 4.10, A5_vE 4.25, Q6_E 2.59
(the plan keeps the conservative values). Greedy lattice allocation on the prime ladder until sigma(C6),
sigma(C7) <= T.

| group | d | sectors | N (tier 1) | core-h | chunks | sigma_C7 contribution |
|---|---|---|---|---|---|---|
| Q8_base | 6 | 2520 | 262139 | 2181 | 12 (~2.8 node-h each, cost-balanced) | 1.9e-5 |
| Q6_E | 6 | 2520 | 262139 | 97 | 1 | 2.7e-5 |
| A7_v | 5 | 360 | 64007 | 59 | 1 | 1.4e-5 |
| A7_base | 5 | 360 | 64007 | 11 | 1 | 6.1e-6 |
| A5_vE, A5_E | 5 | 360 | 131071 | 7, 3 | 1 | 5.1e-6, 1.5e-6 |
| Q6_d, Q6_v, Q4_dE, ... (40 more groups) | 1-4 | | 16001 ... 1048573 | 10 in total | 1 | <= 2e-6 each |

**Tier 1 (6 digits, T = 5e-5): 2367 core-hours, predicted sigma(C6) = 3.1e-6, sigma(C7) = 3.7e-5**
(phase-1 plan: 2442 core-hours; A7_v drops from N=131071 to 64007 because its [l^1] error was overestimated
about 4x by the quadrature model). 86 cfgs; a dry run of `campaign.py plan specs/production_6digit.json`
(dummy lattices, scratch directory) gives Q8 chunks of equal estimated cost (spread 1%) and seeds disjoint
from each other and from the regression. About 37 node-hours of symmetry amdq: ~5 h on 8 nodes
(`bash slurm/submit_production.sh 6digit 8`, which plans on a compute node, runs `seedcheck` against earlier
tiers and prints the collect / outliers / refine / e2e sequence). the personal desktop (`slurm/production_personal-desktop.sbatch`,
16 cores, `--time=0`, data under <DATA> can take groups with d <= 4. Expanse is not used.

Tier 2 (8 digits, T = 5e-7), conservative rates: 18948 core-hours, sigma(C6) = 1.0e-8, sigma(C7) = 2.3e-7;
to be re-planned from the tier-1 data (`--src runs/prod_6digit`): if Q8 keeps its measured N^-3.7 rate, its
cost falls several-fold. Tier 2 uses its own tier name, hence its own seeds.

## 8b. Tier-1 production (done 2026-10-03; full log `PRODUCTION_TIER1.md`)

**Planning and production.**
* Planning: `bash slurm/submit_production.sh 6digit 8`. Plan job 569302 added 6 lattices to `py/korobov_db_g01.json`
  (copied back to the Mac). Its 45450 streams are disjoint, from each other and from every earlier campaign.
* Production: array 569303, 86 tasks with at most 8 at a time on amdq, 01:35-06:37 EDT.
* All 86 tasks COMPLETED 0:0, with no failures, requeues or resubmissions.
* Cost: 2184.6 allocated core-h and 2168.6 engine core-h. Q8 took 1963.7 core-h in 12 chunks of 2.2-3.1 h.

**Results and acceptance.**
* `collect` exits 0: 439 coefficients, 116 needed, 3 of them structural zeros.
* `outliers.py --T 5e-5` exits 0 (3 minor flags).
* Warned points are 0.11% overall. No other log lines appeared and no output holds a non-finite number.
* C6 met the target: sigma(C6) = 2.7e-6 / 2.9e-6.
* **sigma(C7) = 5.9e-5 (rep) / 4.6e-5 (cov) / 5.9e-5 (sector-pooled), above T = 5e-5.**

**Top-up.**
* Run: `specs/production_6digit_topup1.json`, `runs/prod_6digit_topup1`, plan 569446, array 569447, 372.0 core-h.
* It raised Q6_E to N=524287, A7_v and A7_base to 131071, and A5_vE to 262139. These were chosen with the
  planner's model applied to the tier-1 data at a 3e-5 safety target, plus A7_v because its pooled error was 2.2x
  its replicate error.
* Its needed coefficients agree with tier 1 (pulls <= 2.2).
* `python3 py/merge_runs.py runs/prod_6digit runs/prod_6digit_topup1 --tag final` builds
  **`runs/prod_6digit/results_final.json` and `framework_input_final.json`**.

**Final errors.**

| estimate | sigma(C6) | sigma(C7) |
|---|---|---|
| sigma_rep | 1.45e-6 | 3.11e-5 |
| sigma_cov | 1.33e-6 | 2.66e-5 |
| sector-pooled | 1.28e-6 | 3.14e-5 |

* `run_framework.py --raw framework_input_final.json` gives the same sig_lin / sig_rep, with nonlinearity <= 1e-18.
* Q8 dominates C7.
* Error summary without values: `runs/prod_6digit/sigma_summary.json`.

**Strict re-evaluations** (criterion 5, `tests/strict_recheck.py`, jobs 569427, 569443 and 569456; 384.5 core-h
including one cancelled inefficient attempt):
* 20 Q8 + 5 Q6_E sectors (1 shift each), 20 A7_v sectors (2 shifts) and 43 low-dimensional sectors (6 shifts).
* The worst coefficient difference is 1.5e-13 of the sector size, which is 6e-7 of the error.

**Total: 2942.9 allocated core-hours** (sacct, `logs/symmetry/sacct_tier1_all.txt`).

## 8c. Check runs of the assembly phase (2026-10-03; `../assembly/README.md`)

The assembly phase (`../assembly`) ran three small campaigns with this engine on symmetry amdq. They feed only
checks, never a beta input; the production input of the assembly is `runs/prod_6digit/framework_input_final.json`
unchanged.

| run | spec | content | jobs | allocated core-h |
|---|---|---|---|---|
| `runs/poles1` | `specs/poles_check1.json` (tier `poles1`) | every negative eps power production did not compute: 29 moments, 45 jobs, jmin 0 (all logs), R = 6; N = 1048573 (1-2 dim) ... 64007 (6 dim) | 569579 (3 tasks), 569580 | 64.6 |
| `runs/kplus1` | `specs/kplus1_check.json` (tier `kplus1`) | eps^1 (all logs) of the 23 moments whose production series stop at eps^0, for complete direct-comparison series (A7, A7_v, Q8, Q6_E left out: ~400 core-h for a gross screen) | 569583-569585 | 33.5 |
| `runs/conv1` | `specs/conv_check1.json` (tier `conv1`) | Z4_E (k = -1, 0), A3_vdE, A5_vv (k = 0) at N = 262139 (4-16x production), re-check of the moments the direct test flags | 569586 | 1.8 |

* Operations:
  * planned locally, since every lattice was already in `py/korobov_db_g01.json`, which is unchanged;
  * run with `slurm/production_symmetry.sbatch` (lists `cfglist_big/rest.txt`, `cfglist_t{1,2,3}.txt`);
  * every task COMPLETED 0:0, at most 4 nodes at a time, 09:17-10:06 EDT;
  * `campaign.py collect` exit 0 on all three;
  * `tests/production_checks.py`: no problems and no unexpected log lines; WARN fractions 1.7e-6, 2.8e-4 and
    1.4e-3;
  * `seedcheck` over prod_6digit, topup1, poles1, kplus1 and conv1: all 177564 streams disjoint;
  * sacct in `logs/symmetry/sacct_assembly_phase.txt`.
* Negative powers are cheap. The costliest cfg was Q8[eps^-1] at N = 64007, 30 min on one node; eps^1 is more
  expensive than eps^0.
* Criterion 4 (section 9) is done in the assembly with these runs:
  * all higher-log checks pass;
  * all 702 input-dependent negative-power coefficients of the 37 normalized jet entries cancel (max pull 2.4).
* What conv1 shows:
  * production `Z4_E[eps^-1 l^0]` = 1.2898681327983 +- 2.2e-10 is low by 9.0e-10, i.e. 4.0 replicate sigma or
    1.6 sector-pooled sigma, against the converged 1.28986813369638 = 2 z2 - 2;
  * this is the known boundary-dominated endpoint coefficient (section 8b), and its effect on C7 is 7e-10;
  * every other re-checked coefficient agrees with production within 1.7 sigma, except Z4_E[eps^0 l^1]
    (3.5 replicate sigma, 1.7 pooled, 5e-9, not a C6/C7 input at this order);
  * replacing all conv1 values would move C6 by -3.9e-7 (0.27 sigma) and C7 by +8.8e-7.

## 9. Acceptance criteria (production)

1. Every cfg output complete (`"complete": true`); `campaign.py collect` exits 0 (no missing coefficient;
   structural zeros explicit); `seedcheck` over all tiers reports all streams disjoint.
2. `py/outliers.py RUNDIR --T <tier target>` exits 0, after `refine` rounds if needed: no sector dominates
   (> 30 x median and > 50% of the error) a needed coefficient whose error matters (sens x sigma > 1e-3 T).
3. sigma(C6), sigma(C7) <= T with both `sigma_rep` (framework per replicate) and `sigma_cov`; they agree
   within their sampling error; the framework's own `from_replicates` on `framework_input.json` agrees;
   nonlinearity << rep_se.
4. Higher-log checks of validation (d) and the cancellation of all eps^{<0} terms at the final precision,
   now with replicate errors (framework `kmax` hook).
5. A strict-tolerance re-evaluation (errTarget/tailTol 1e-16, maxJet 2e6, tailMax 0.05; same lattice and
   shifts) of the 20 deepest Q8 and A7_v sectors agrees to double rounding (review test D), and the WARN
   fraction stays below 1% of the points.
6. Tier 2 vs tier 1: pulls < 3 with replicate errors (Student t, R-1 = 5 degrees of freedom per job).
7. Only afterwards, for comparison: archived values (Knew = -906.9824098509, Omega = -234.4214552890,
   J = 32.280324973629, ...).

## 10. Open problems

* Tier 1 is done (section 8b). C7 is now limited by Q8 (2.6e-5 replicate, 3.1e-5 sector-pooled). Tier 2 must
  re-plan Q8 from `runs/prod_6digit`; the full-sector rate there (N=1009 -> 262139) is 2.06, against 3.7 in the
  pilot sample. Higher-log and pole-cancellation checks (criterion 4) and all reference comparisons were done in
  the assembly phase (`../assembly`, section 8c; results in `../RESULTS.md`).
* `tests/e2e_framework.py` should use an adaptive fd step (it exits 3 at production errors although the gradient
  convention is correct; `PRODUCTION_TIER1.md` section 7).
* Q8 dominates the cost. The plan assumes N^-2.4; the replicate errors of the pilot4 sample give N^-3.7
  between 16001 and 64007. Tier 1 measures the rate on all sectors.
* With R = 6 the replicate error of one job has 5 degrees of freedom (Student t tails); C6 and C7 combine many
  jobs, which raises the effective degrees of freedom, but single-coefficient pulls of 3-4 occur (Q6_d[l^2],
  Q4_E[l^1]). R = 8 for tier 2 would cost about 1.25x for the same error.
* Endpoint moments converge slowly in boundary sectors (measured rates 1.4-1.9 for Q4_dE, Z4_vE, Q4_vE;
  Z4_E[eps^-1 l^0] dominated by boundary sectors). They are handled by more points (planner rates, `refine`);
  a boundary-adapted variable transform is not implemented.
* The floor (1e-15 x L1) is set a priori above the data minimum (2e-17). The strict-tolerance test changed
  nothing for the 1-3D groups; deep 5D/6D sectors rely on review test D (agreement to double rounding).
* Validation (d) was not rerun with replicate errors; the regression's coefficient-level comparisons and the
  framework-level closed-form pulls cover the same coefficients at lower order only.
* Remaining review suggestions not implemented: embedded (extensible) lattices for the lower-dimensional
  pieces, a SIMD/GPU double-double kernel.
* Gate review of v2 (2026-10-03), non-blocking recommendations for the tier-1 acceptance:
  (i) with R = 6 the whole-job replicate error has 5 dof; a sector-pooled estimator
  `sum_s var_r(x_{s,r})/R` from `per_sector[].rep` (same coefficient map, hundreds of dof) is a cheap cross-check.
  On `runs/regress_v2/new` (27 needed coefficients above the floor) the ratio replicate/sector-pooled has median
  1.00 and rms 1.04 (Q8[l^1] 0.85, Q6_E[l^0] 0.94, A7_v[l^1] 1.35), i.e. consistent; report it next to
  sigma_rep/sigma_cov in tier 1. (ii) The outlier rule (> 30 x median and > 50% of the error) does not fire when
  several equivalent boundary sectors share the error (Q4_dE sectors 0/2/12/14, ~11 A5_E sectors at 20-30% each);
  those groups are covered by the measured slow rates in the planner, but inspect them with `--fac 10 --share 0.2`.
  (iii) The Q8 reference error comes from a stride-42 sample in which 2 of 60 sectors carry 53% of the variance,
  so the predicted sigma(C7) = 3.7e-5 is uncertain by roughly a factor 2; a top-up may be needed after tier 1.

## 11. C8 extension (phase 3, 2026-10-03)

C8 = 8 T4 (note Secs. 14-18) needs ten new beta inputs (W, S, U, J9, L3, M21, M12, N2, Ndelta, Kv). The framework's
requirement list (`../framework/out/required_inputs_C8.json`, copied with its SHA-256 into
`specs/framework_required_inputs_C8.json`) has 201 raw scalars; the 116 of order D4 come unchanged from the tier-1
production (`runs/prod_6digit/framework_input_final.json`), the 85 beyond D4 are new engine work: 50 groups, 66 jobs
(group, eps power), listed in `specs/production_C8.json` (`py/production_list_C8.py`) with the tier of every job and the
signed dC8/dx of every coefficient. The exact two-kink sector (A1, Z2, Q2, EZ2, EQ2) stays in the framework.

### 11a. What changed in the engine

* **The C++ engine is unchanged** (source md5 `edfa65dc`, binary md5 `ec238e0f` on symmetry and the personal desktop, g++ 11.4,
  x86-64-v3). It already covers every C8 atom: the insertion polynomials (`py/lri_moments.insertion_poly`) reach S4 and
  E3, enough for d^3 (A3_ddd: S2^3, S2 S3, S4; Dmu = 6) and d^2 E (A3_ddE: E3, S2 E2, S2^2 E1, S3 E1); n = 9 angular
  (A9: 8 gaps, 7D, 20160 folded sectors) and n = 7 full (A7_E: 8 spacings, 7D, 20160 sectors) stay inside every limit
  (MAXV = 12 jet variables, 64-term sparse sums, 64-slot buffers, 2^K pole tables with K <= 7).
* New tooling (all additive; nothing of the C6/C7 path changed behaviour):

| file | role |
|---|---|
| `py/production_list_C8.py` | `specs/production_C8.json` (+ the collect need file `specs/production_C8_need.json`, the outliers gradient file `specs/gradients_C8.json`) |
| `py/make_spec_C8.py` | campaign specs: `val` (validation run, all logs), `conv` (cost/convergence pilot), `kplus1` (eps^1 of the new 1-4D atoms), `tier` (production tier from the plan); `--keep-done` keeps entries that already ran |
| `py/plan_C8.py` | planner on the signed C8 gradients: replicate and sector-pooled projections, per-dimension rates, greedy ladder allocation, tiers, alternatives, 8-node makespan, sector-adaptive (Neyman) cost factor |
| `tests/validate_C8.py` | archive-free checks of the C8 data: raw targets, pole cancellation of all 74 C8 jets, structural zeros, C3/K4 higher-log targets, RG second/higher-log predictions (normalized jets at framework order C8, replicate errors) |
| `tests/direct_C8.py` | the C8-era series against the direct finite-cutoff table (direct agent's GLS tool) |
| `tests/compare_calib.py` | cross-machine calibration (bitwise replicates, cpu ratio personal desktop / amdq) |
| `tests/preview_C8.py` | pilot-level values of the new inputs (framework at order C8 on production + pilot data) |
| `tests/compare_brief_C8.py` | COMPARISON ONLY, after hashing our preview: B_done and U against the numbers quoted in the C8 brief |
| `tests/regress_C8.py` | regression of the C6/C7 tooling (re-plan, re-collect, outliers vs the stored tier 1) |
| `tests/dryrun_tiers.py` | plans the tier specs into a scratch directory and runs seedcheck against every earlier campaign |
| `slurm/submit_C8.sh` | production submission recipe per tier (NOT run) |
| `slurm/pilot_C8_personal-desktop.sbatch`, `slurm/pilot_C8_symmetry.sbatch` | pilot wrappers |
| `py/outliers.py` | `load_sens` also reads a `C8` gradient (`--grad specs/gradients_C8.json`); C6/C7 behaviour unchanged |
| `tests/budget_C8.py`, `tests/tier_vs_pilot_C8.py` | tier A acceptance (section 11h) |
| `py/plan_C8.py` options (2026-10-04, tiers B/C) | `--src-speed DIR=F` (per-source cost factor, e.g. an amdq probe = 1.0), `--lower-ref largest` (rate from the largest smaller N), `--n-floor lower` (a probe-referenced job may go below the probe's N), `--budget-BC X` with `--budget-priority equal|B|C` (relax the B/C targets to fit a cap); defaults reproduce every earlier plan byte for byte |
| `py/make_spec_C8.py probe`, `checks` | budget-guard probe spec (heavy jobs at production N on the conv-pilot sector samples), deferred-check spec (A9, Z8 eps^-1) |
| `py/split_C8BC.py` | machine split of a tier spec (same tier name, identical cfgs and seeds) and the symmetry array order |
| `tests/budget_guard_C8.py` | phase budget guard: `ledger`, `probe` (guard 1, re-plan under the cap), `chunks` (guard 2), `tasks`, `reduce`, `lattices --merge/--check` |
| `tests/exact_scalars_C8.py` | the four exact tier-C scalars (engine pole bound, A3 closed form, delivered values) -> `specs/exact_scalars_C8.json` |
| `slurm/submit_C8BC.sh`, `slurm/poll_C8BC.sh`, `slurm/korobov_personal-desktop.sbatch` | tiers B/C submission from the Mac (stages sync, stageP, stageM, array, reduced, strict, pull; `DRY=1`), read-only poller, lattice search on the personal desktop |
| `tests/merge_tiers_C8.py` | per-scalar merge of tier deliverables (A, B, C) into one framework input, blocks renamed `<tier>:<block>`; a scalar in two inputs is an error |
| `slurm/packed_personal-desktop.sbatch` | packed strict re-checks on the personal desktop (`-c` and `--mem` on the sbatch line; one strict Q8_v process needs 12-17 GB, A7_d up to ~25 GB) |
| `specs/checks_C8_BC_N4001.json` | the C9 eps^-1 pole check at N = 4001 (confirmation of the N = 1009 `c8chkBC`) |

* **Regression (bit-identical C6/C7 path).** (i) `campaign.py plan specs/production_6digit.json` with the current code
  reproduces all 86 tier-1 cfgs, the manifest and `cfglist.txt` byte for byte; (ii) `campaign.py collect` on a copy of
  `runs/prod_6digit` reproduces `results.json` byte for byte (`framework_input.json` differs only in the run path);
  (iii) `outliers.py runs/prod_6digit --T 5e-5` reproduces the stored `flags.json` exactly; (iv) the engine binary is
  unchanged; (v) cross-machine: two tier-1 cfgs (Q4_dE k=0, Q6_v k=0) rerun on the personal desktop (8 threads, Intel) give
  per-shift and per-sector replicates bitwise identical to the amdq production (64 threads)
  (`runs/calib_personal-desktop`, `results/calib_personal-desktop.json`).

### 11b. Pilot runs (the personal desktop; symmetry was down)

Symmetry went down at 13:22-13:35 EDT on 2026-10-03 (every node "unexpectedly rebooted"; amdq, defq, debugq all down
for the rest of the session). The pilot therefore ran on the personal desktop (`slurm/pilot_C8_personal-desktop.sbatch`, 8 of the 16
free physical cores per job, `--time=0`, TimeLimit UNLIMITED; data under `<DATA>/<USER>/sri_c6c7/engine`).
The personal desktop has no sympy, so every plan was made on the Mac (sector-cost probes and lattice searches of seconds) and
copied over. Lattices new in `py/korobov_db_g01.json`: 1009_4, 1009_7, 4001_7, 64007_1 (local), merged with the
symmetry copy's 524287_6 (the tier-1 top-up lattice that had not been copied back); the merged database is on all
three machines.

* **Calibration** (`runs/calib_personal-desktop`, job 244): the tier-1 cfgs Q4_dE k=0 and Q6_v k=0, copied byte for byte,
  reproduce the amdq production's per-shift and per-sector replicates **bitwise** on the personal desktop; cpu personal desktop / amdq
  = 1.35 and 1.64 (mean 1.50). Pilot timings are converted to amdq core-hours with `--speed 0.667`.
* **Runs** (tier names give fresh seeds; `seedcheck` over every campaign of this engine: all streams disjoint):
  * `runs/c8val` (`specs/val_C8.json`, tier `c8val`): every (new atom, eps power) the 74 pole-cancellation jets of
    `../spec/out/C8/poles_C8.json` or the C8 production jobs need and no earlier run has with all logs, plus the
    below-tight-bound zeros Q4[eps^-2], Q4_v[eps^-2], Z4_dE[eps^-2], Z6_E[eps^-3] (the last two inside the framework's
    safe structural range: the EC5_d and EC7 pole checks need them); all log powers, all sectors, R = 6; N = 262139-1048573
    (1-2D), 64007-262139 (3D), 16001-64007 (4D), 1009-16001 (5D), 1009-4001 (6-7D) (the first entries ran at the larger
    sizes before the timings forced the reduction; entries that had run keep their cfgs, `make_spec_C8.py --keep-done`).
  * `runs/c8conv` (`specs/conv_C8.json`, tier `c8conv`): every C8 production job of dimension >= 4 in its production
    configuration (eps power, jmin) at two sizes (4D: 4001, 16001 all sectors; 5-7D: 1009, 4001 on sector samples:
    A9 1/672, A7_E 1/336, Q8_v and Z8 1/84, Q6_vE and Z6_E 1/42, A7 family 1/12, A5_E/A5_dE 1/6).
  * `runs/c8kplus1` (`specs/kplus1_C8.json`, tier `c8kplus1`): eps^1, all logs, of the new 1-4D atoms (complete
    K = 1 series for the direct comparison).
  * `runs/c8strict`: strict-tolerance re-evaluation (`tests/strict_recheck.py`, same lattice and shifts, 2 shifts) of the
    most-warned sectors of the A9, Q8_v, Z8 and A7_d pilots.
  * `runs/calib_personal-desktop`: see above.
  * Deferred (too expensive for a check run on 6-8 personal-desktop cores; the production tiers compute the eps^0 ones): A9
    eps^-1 (~85 core-h with all sectors at N = 1009, scaled from the measured eps^-2 cost) and Z8 eps^-1 (~3), i.e. the C9 pole
    check at eps^-1 (one symmetry node for ~1.5 h); A9, Q8_v, Z8, A7_E, A7_v, Z6_E eps^0 with all sectors.
  * Cost: about 100 allocated personal-desktop core-hours (engine cpu 86: c8val 32.0, c8conv 37.9, c8kplus1 9.1, calibration 3.3,
    strict 3.6), jobs 239-257 with 4-8 cores each, 2026-10-03 19:59 to 2026-10-04 03:06 CEST, logs in
    `logs/personal-desktop/sri_eng_c8pilot_*.out`; the lists were reordered and the jobs resized from 8 to 6 cores to keep the
    2-CPU job of another session (h2-handoff-tests) running. Every pilot cfg completed with rc 0.


### 11c. Validation of the new groups (archive-free)

`tests/validate_C8.py` -> `results/validate_C8.{txt,json}`: production + poles1 + kplus1 + phase-1 validation files +
c8val + c8conv + c8kplus1 (all-sector entries only; for a job at several N the one with the smallest error), normalized
jets at framework order C8 (degree-5 (v, delta, E) jets, logs to l^11), R = 6 replicate re-assemblies; sigma = the
larger of linear and replicate propagation (plus 1e-25 absolute for coefficients that vanish term by term).

| check | target source | result |
|---|---|---|
| A3_ddd [eps^0 l^0..l^8] | spec independent three-kink values (1e-25) | 11 raw checks incl. A7_d: max |pull| 0.22; A3_ddd[l^1] = -250.248669089713682 vs -250.248669089715321 (diff 1.6e-12, sigma 6.5e-10) |
| A7_d [eps^0 l^8], [l^9] | note l.1355-1358 (leading log of d_delta A7) | -7.49841269841269842 +- 7.5e-15 = -2362/315 exactly (diff < 1e-18); [l^9] = 0 (structural) |
| pole cancellation, 74 jets | spec `poles_C8.json` | 996 coefficients, max |pull| 2.95, rms 0.40; the 22 jets new for C8: 492 coefficients (183 non-trivial), max |pull| 2.95; not testable: C9[v0d0] at eps^-1 (A9 and Z8 eps^-1 deferred) |
| below-tight-bound zeros | spec `raw_requirements_C8.json` | 13 checks (Q4, Q4_v, Z4_E, Z4_dE at eps^-2, Z6_E at eps^-3): all zero to 1e-34 or exact by the engine's pole analysis |
| C3/K4 higher logs (d^3, 3 derivatives), incl. closed forms in L3, M21, M12 | spec `validation_targets_C8.json` | 120 checks, max |pull| 0.36 |
| RG second and higher logs (C5, C7, C9, K6, K8 jets) | spec `rg_logs_C8.json` | 97 checks, max |pull| 2.62, rms 0.83; C9 and d_v K8 need full-sector eps^0 data (production) |

`tests/direct_C8.py` -> `results/direct_C8{.txt,_offsets.json}`: the C8-era series (c8val, the all-sector c8conv entries,
c8kplus1; completed by conv1, production, poles1, kplus1) against the direct finite-cutoff table with the direct agent's GLS tool.

Verdicts: INCONCLUSIVE 1, PASS 42, TENSION 1, UNTESTABLE 3. Every new 3-5 kink atom with a complete K = 1 series PASSES (A3_ddd, A3_vdd, A3_ddE (EA3_dd), Q4_vvv, Q4_vvd, Q4_vdd, Q4_vvE (EQ4_vv), Q4_vdE (EQ4_vd), Z4_dd, Z4_dE (EZ4_d), A5_dd, A5_dE (EA5_d), A7_d as a screen; Q6_vv, Q6_vd, Z6_d, Z6_v, Q6_vE (EQ6_v) as K = 0 screens). EQ4_vv flagged TENSION with the K = 0 series (best-BIC tail variant; the next variant gave pull 0.0) and PASSES once c8kplus1 adds eps^1. A5_d stays TENSION (individual pulls 1.2, 1.2; joint X2 12.4 from their correlation), the tail-model flag already explained in the assembly phase; EZ4_base (Z4_E) PASSES with the conv1 values, as in the assembly phase. UNTESTABLE/INCONCLUSIVE: EA7, Q8_v, Z8, EZ6 (no complete series without the deferred eps^0 / eps^-1 runs).

Run health (`tests/production_checks.py`): every pilot cfg completed (rc 0), no non-finite number, no unexpected log
line; replicate vs sector-pooled error of the needed coefficients: median ratio 0.92, rms 1.00 over 71 coefficients (c8conv). WARN
fractions (points whose estimated jet error stays > 100 x the target after tails) are 1-3 % in the deepest 7-9 kink
sectors at the default numerics (A9 2.7 %, A7_d 2.0 % (jmin 0), Q8_v 1.1 %, Z8 0.5 %; tier 1: 0.11 %);
`runs/c8strict` re-evaluates the most-warned sectors with strict numerics (`tests/strict_recheck.py`):

* 7 of the 18 prepared sectors were re-evaluated (A9 sectors 3 and 28, Q8_v 16, Z8 9 and 29, A7_d 15 and 26; 2 shifts each,
  same lattice and shifts, errTarget/tailTol 1e-16, maxJet 2e6, tailMax 0.05): every Laurent order agrees to <= 1e-13 of the
  sector size, and the needed single log moves by at most 4.4e-14 of the sector size = 7e-12 of the coefficient's error (A9
  sector 3, 694 warned points, the worst of the sample). The warned points therefore carry no error at the default numerics.
  Strict numerics cost 6-37x the default (Q8_v 37x); the other 11 sectors (incl. Q8_v sector 12, > 1.4 h on 6 cores) were
  cancelled to free the shared machine (`results/strict_recheck_C8.txt`, `runs/c8strict/strict_compare.json`).

`tests/preview_C8.py` -> `results/preview_C8.json` (pilot data, NOT a production result): W = -37.70811151495228 +-
1.1e-10 from the engine's A3_ddd, against the spec's independent three-kink value -37.70811151495255511 (difference
2.8e-13); S = 878.18373374015 +- 3.6e-7, L3 = -0.638692810584829 +- 9e-11, M21 = -171.23557656558 +- 1.2e-9, M12 = -422.71505796985 +- 6.1e-9, N2 = 189.74149 +- 6.7e-4, Ndelta = 6171.1344 +- 0.0063 and B_done8 = B_old + the six 'inherited' terms = 563.4040883 +- 4.9e-5 (U = -1324.8 +- 53 from the N = 1009 all-sector A7_d; Kv, J9 need the deferred full-sector Q8_v, A9 eps^0). **Comparison only** (`tests/compare_brief_C8.py`, after recording the preview's SHA-256 ddf42ba1...): the archive's B_done = 563.40406612 quoted in the C8 brief differs by 2.2e-5 = 0.45 sigma, so the six inherited inputs W, S, L3, M21, M12, N2 are confirmed at the pilot precision (sigma 4.9e-5, i.e. 3e-8 of their summed contribution 1425.07, dominated by N2 and B_old); U agrees to 0.5 sigma. Tier A brings their C8 contribution to ~1e-6.

### 11d. Pilot: cost and convergence (`runs/c8conv`, personal-desktop timings x 0.667 = amdq core-hours)

| job | d, sectors | jmin | ms per point, sector, shift (the personal desktop) | full-sector sigma(coefficient) at N = 1009 -> 4001 | rate | |dC8/dx| |
|---|---|---|---|---|---|---|
| A9 [eps^0 l^1] | 7, 20160 | 1 | 38 | 439 -> 36.7 | 1.80 | 0.25 |
| A7_E [eps^0 l^0] | 7, 20160 | 0 | 2.8 | 74.7 -> 14.7 | 1.18 | 0.5 |
| Q8_v [eps^0 l^1] | 6, 2520 | 1 | 22 | 146 -> 35.5 | 1.03 (pooled 1.22) | 0.125 |
| Z8 [eps^0 l^1] | 6, 2520 | 1 | 4.0 | 6.7 -> 1.6 | 1.04 | 0.25 |
| Q6_vE [eps^0 l^0] | 6, 2520 | 0 | 0.42 | 72 -> 6.3 | 1.77 | 0.25 |
| Z6_E [eps^0 l^0] | 6, 2520 | 0 | 1.04 | 4.2 -> 0.91 | 1.10 | 0.5 |
| A7_d [eps^0 l^1] | 5, 360 | 1 | 9.4 | 33.5 -> 0.76 | 2.75 | 0.75 |
| A7_v [eps^0 l^0] | 5, 360 | 0 | 2.1 | 97 -> 1.3 | 3.11 | 1.0 |
| A7 [eps^0 l^0] | 5, 360 | 0 | 0.4 | 6.8 -> 0.093 | 3.1 | 2.0 |
| A5_dE [eps^0 l^0] | 5, 360 | 0 | 0.45 | 27 -> 0.69 | 2.67 | 1.5 |
| Q6_vd [eps^0 l^1] (4001 -> 16001) | 4, 60 | 1 | 3.9 | | 3.52 | 0.5 |

Between N = 1009 and 4001 the 6-7D rules are pre-asymptotic (README section 4: the tier-1 Q8 converged at 2.06 from
1009 to 262139 on all sectors, and faster at large N). The plan therefore uses rate 2.0 for 6-7D from the N = 4001
reference (a measured rate is used only when its smaller N is >= 4001); scenarios with the measured pilot rates and
with 2.5 bracket it.

### 11e. Plan and tiers (`py/plan_C8.py` -> `results/plan_C8.{md,json}`; specs `specs/production_C8_tier{A,B,C}.json`)

Error model: per job the larger of the replicate and sector-pooled projections of its needed coefficients on the
signed dC8/dx (`specs/framework_sensitivities_C8.json`), scaled by the sector stride, R = 6 and (N/N_ref)^-alpha,
plus the floor; no extrapolation below the pilot size; greedy allocation on a sqrt(2) prime ladder; 3 node-hours per
cfg chunk; costs in amdq core-hours; B_old (tier-1 production, 1.16e-5) added in quadrature.

| tier | inputs | jobs / cfgs | amdq core-h | wall on 8 amdq nodes | sigma(C8 part) | predicted sigma of the inputs (engine part) |
|---|---|---|---|---|---|---|
| A | W, S, L3, M21, M12, N2, Ndelta | 21 / 21 | 104 | 1.1 h | 7.5e-07 | W 1e-10, S 8e-09, L3 9e-11, M21 1e-09, M12 6e-09, N2 2e-06, Ndelta 4e-06 |
| B | U, Kv | 24 / 66 | 8,439 | 17.9 h | 4.3e-03 | U 1.0e-03, Kv 0.13 |
| C | J9 | 21 / 696 | 130,308 | 255 h | 8.8e-03 | J9 0.035 |

Total sigma(C8) of the main plan: 9.7e-03 (B_old 1.16e-5 included).
Tier A cost curve: sigma 1e-04: 19 core-h; sigma 3e-05: 31 core-h; sigma 1e-05: 41 core-h; sigma 3e-06: 61 core-h; sigma 1e-06: 104 core-h; sigma 3e-07: 159 core-h.
Tier B (sigma of C8 without J9; main 0.005 leaves sqrt(0.01^2 - 0.005^2) for tier C): 0.001: 23,709 core-h; 0.0025: 11,925 core-h; 0.01: 5,904 core-h.
Tier C (total sigma(C8)): 0.01: 130,308 core-h; 0.03: 87,389 core-h; 0.1: 43,130 core-h; 0.3: 22,523 core-h; 1: 15,256 core-h; 3: 7,641 core-h.
Dominant jobs: A9 [eps^0 l^1] (tier C, N = 131071, 582 cfgs, ~112k core-h), A7_E [eps^0 l^0] (C, 262139, ~17k), Q8_v
[eps^0 l^1] (B, 131071, ~8k), Z8 (C, ~1.5k); tier A is dominated by Q6_vd and Q6_vv (4D, insertion degree 3-4, ~92 core-h).
Scenarios (`results/plan_C8_{measured,optimistic}_rates.md`): with the measured pilot rates (1.0-1.8 for 6-7D)
tier B ~65k and tier C ~2.9e5 core-h; with rate 2.5 for 6-7D tier B ~4.2k and tier C ~85k core-h. Alternative specs:
`specs/production_C8_tierB_sigma0.01.json` (5.9k core-h) and `specs/production_C8_tierC_sigma0.3.json` (22.5k core-h).

The tier specs carry the C8 coefficient lists; seeds are hashed from the tier names `c8tierA`, `c8tierB`, `c8tierC`
(alternatives `c8tierB_s0.01`, `c8tierC_s0.3`). `tests/dryrun_tiers.py` plans all five into a scratch directory
(dummy lattices for the sizes not yet searched): the main tiers give 21, 66 and 696 cfgs, the alternatives 53 and 136; seedcheck over the five tier directories and every earlier campaign (prod_6digit, topup1, poles1, kplus1, conv1, c8val, c8conv, c8kplus1): 1,777,326 random streams, all disjoint (`results/dryrun_tiers_C8.txt`).

Submission (tier A: done 2026-10-04 on the personal desktop, section 11h; tiers B and C: prepared with `slurm/submit_C8BC.sh`
and the budget guard, section 11i; run 2026-10-04/06, `PRODUCTION_C8.md` section 13). The original recipe, on the symmetry login node after syncing `src/ py/ slurm/ specs/`
and building (`bash slurm/build.sh` in a job):
```bash
cd <SCRATCH>/sri_c6c7/engine
bash slurm/submit_C8.sh A 8          # 1st call: planning job on amdq (lattice search, seedcheck); 2nd call: the array
bash slurm/submit_C8.sh B 8
bash slurm/submit_C8.sh C 8                                          # 0.01 target, ~1.3e5 core-h (see 11g)
bash slurm/submit_C8.sh C 8 specs/production_C8_tierC_sigma0.3.json  # cheaper alternative, sigma(C8) ~ 0.3
```
Acceptance per tier: collect exit 0 with `--need specs/production_C8_need.json`; `outliers.py --grad
specs/gradients_C8.json` (T = 1e-5 tier A, 1e-3 B/C); strict re-check of the most-warned sectors; `validate_C8.py`
with the tier run (pole checks, higher logs, RG logs of C9, d_v K8, d_delta C7, d_v^2 K6 from the full-sector eps^0 data);
then `../framework/run_framework.py --order C8 --independent-files --raw runs/prod_6digit/framework_input_final.json
--raw runs/c8tierA/framework_input.json ...`.

### 11f. How to run (C8)

```bash
python3 py/production_list_C8.py [--refresh]        # specs/production_C8.json, _need.json (re-copies the framework lists with --refresh)
# pilots (done 2026-10-03 on the personal desktop; symmetry: slurm/pilot_C8_symmetry.sbatch)
python3 py/make_spec_C8.py val    --out specs/val_C8.json  --keep-done runs/c8val
python3 py/make_spec_C8.py conv   --out specs/conv_C8.json --keep-done runs/c8conv
python3 py/make_spec_C8.py kplus1 --out specs/kplus1_C8.json
python3 py/campaign.py plan specs/val_C8.json runs/c8val [--force]      # locally (sympy); copy runs/<dir> to the cluster
sbatch -c 8 --mem=40G slurm/pilot_C8_personal-desktop.sbatch runs/c8val cfglist.txt            # the personal desktop
python3 py/campaign.py collect runs/c8val --partial                     # val/kplus1: all coefficients
python3 py/campaign.py collect runs/c8conv --need specs/production_C8_need.json
# checks and plan (Mac, minutes)
python3 tests/compare_calib.py                                          # the personal desktop vs amdq: bitwise + cpu ratio
python3 tests/validate_C8.py --run runs/c8val --run runs/c8conv --run runs/c8kplus1
python3 tests/direct_C8.py                                              # c8val, c8conv, c8kplus1 (+ conv1, production, poles1, kplus1)
python3 tests/preview_C8.py                                             # pilot-level values of the new inputs
python3 py/plan_C8.py --src runs/c8conv --src runs/c8val --src runs/poles1 --src runs/kplus1 --src runs/prod_6digit \
        --speed 0.667 --alt 0.03,0.1,0.3,1,3 --out results/plan_C8       # (+ --rate-min-N 1009 / --alpha6 2.5 --alpha7 2.5
                                                                        #  scenarios; --T 0.3 / --TB 0.01 alternatives)
python3 tests/compare_brief_C8.py                                       # comparison only, after the preview exists
for t in A B C; do python3 py/make_spec_C8.py tier --plan results/plan_C8.json --tier-name $t \
        --out specs/production_C8_tier$t.json; done
python3 tests/dryrun_tiers.py /tmp/c8dry                                # seeds/chunks of the three tiers (no engine run)
# production (needs the user's go-ahead; symmetry login node, after syncing src/ py/ slurm/ specs/ and building)
bash slurm/submit_C8.sh A 8      # plans on an amdq compute node (lattice search), then rerun to submit the array
```

### 11g. Open problems (C8)

* **Tier C is not affordable at sigma(C8) = 0.01 with this engine.** J9 = b9 needs A9[eps^0 l^1] (7D, 20160 sectors,
  ~3,000 amdq core-s per lattice point over all sectors and shifts) to ~1e-8 relative; the pilot gives sigma ~ 37 at
  N = 4001 (all sectors) and a pre-asymptotic rate 1.8. A7_E[eps^0 l^0] (endpoint, 7D) converges at 1.2 between
  1009 and 4001 (boundary sectors, as for the 4D endpoint moments of tier 1). Options: sector-adaptive N (Neyman
  allocation over sectors, `campaign.py refine` per sector; estimated cost factors from the pilot samples only 0.82
  (A9), 0.60 (A7_E), 0.62 (Q8_v), `results/plan_C8.md`), a
  boundary-adapted transform for the endpoint moments, a faster jet kernel (SIMD double-double), or a connected
  (cumulant) integrand for C9 that avoids the A9_1 vs lower-order cancellation. Without them, tier C is a gross check
  (sigma(C8) ~ 0.3-1 for 2-3e4 core-h).
* **WARN fractions above 1 %** in the deepest 7-9 kink sectors at the default numerics (A9 2.7 %, A7_d 2.0 %, Q8_v
  1.1 % of the points carry an estimated jet error > 100 x the target after tails; tier 1: 0.11 %). The strict re-check of
  7 most-warned sectors found no effect (<= 7e-12 of the error), but it covers N = 1009 only; production keeps
  `tests/strict_recheck.py` on the most-warned sectors as acceptance criterion 5 (budget: Q8_v strict costs up to 37x).
* Deferred checks: the C9 pole check at eps^-1 (A9 and Z8 eps^-1 with all sectors: ~85 + ~3 personal-desktop core-h at N = 1009, scaled from the measured eps^-2 runs) and the
  RG log checks of C9, d_v K8, d_v^2 K6 (full-sector eps^0 data; they come with the tier runs, which compute every
  log power >= jmin). Scheduled since 2026-10-04: `specs/checks_C8_BC.json` in stage P, the RG checks after the tiers
  (section 11i).
* The 6-7D convergence rates are measured only between N = 1009 and 4001 (pre-asymptotic: Q8_v 1.0-1.2, A9 1.8,
  A7_E 1.2); the plan uses 2.0 (the full-sector Q8 rate of tier 1) unless stated; with the measured rates tier C
  roughly doubles. Re-plan tier B/C from the first production data (`py/plan_C8.py --src runs/c8tierB ...`).
* The pilot sector samples (30-60 sectors of 360-20160) carry heavy-tailed variance (top-3 share 0.3-0.6): predicted
  sigmas of the 6-7D jobs are uncertain by about a factor 2.
* Symmetry was down during the whole pilot: the cost model is personal-desktop-based, converted with the measured
  personal desktop / amdq ratio 1.50 from two 4D cfgs; a first amdq task of each heavy group should confirm it (tier A confirmed it for the 4D groups to 1-2 %, section 11h).

### 11h. Tier-A production (2026-10-04; full log `PRODUCTION_C8.md`)

* **Machine.** Symmetry was down for the whole run (every node "unexpectedly rebooted", 2026-10-03 13:22 EDT; back on
  2026-10-04 at 13:55 EDT, after production), so tier A ran on the personal desktop:
  * `slurm/pilot_C8_personal-desktop.sbatch`, 14 of the 16 free cores, `--time=0`;
  * data in `<DATA>/<USER>/sri_c6c7/engine/runs/c8tierA`;
  * identical binary (md5 `ec238e0f`) and sources.
* **Planning.**
  * Two new 4D lattices (370759_4, 741457_4) were searched in a personal-desktop job; the plan ran on the Mac, which has sympy.
  * The 21 cfgs are identical to the dry run apart from those two lattices.
  * Seeds are disjoint from every earlier campaign.
* **Run.**
  * Job 259 ran the 20 cheaper cfgs; job 260 then ran Q6_vd (`afterok`). This kept the option of moving Q6_vd to amdq
    if symmetry returned.
  * Every cfg finished with rc 0. Engine cpu was 152.7 personal-desktop core-h = 101.8 amdq-equivalent, against 104.3 planned:
    the cost model held to 1-2 % for Q6_vd, Q6_vv and Q4_vdE.
* **Acceptance.**
  * `collect --need specs/production_C8_need.json` exit 0 (26 needed scalars);
  * `outliers.py --grad specs/gradients_C8.json --T 1e-5` exit 0;
  * WARN 0.80 %;
  * `production_checks.py` exit 0;
  * strict re-checks of the most-warned sectors (A3_ddE, Q4_vdE, Q4_vvE, Q4_vdd, Q6_vv) agree to <= 8e-17 of the
    sector size;
  * the Q6_vd strict re-check did not complete: its last point block ran > 5 h on one thread, and the job was
    cancelled;
  * the endpoint boundary sectors are bitwise identical under strict numerics;
  * 33 comparisons with earlier independent runs: rms pull 0.48, max 1.46;
  * `validate_C8.py` with tier-A priority: every check passes, unchanged from the pilot validation.
* **Budget.**
  * `tests/budget_C8.py` (new; the planner's projection on achieved data) gives sigma(C8 part) = 5.03e-7 against 7.46e-7
    planned.
  * A3_ddE missed by 1.69x (endpoint moment; measured rate 2.3-2.6 instead of 3.0). It was rerun whole at N = 524287
    with fresh seeds: `specs/production_C8_tierA_topup1.json`, `runs/c8tierA_topup1`, 0.27x.
  * `py/merge_runs.py runs/c8tierA runs/c8tierA_topup1 --tag final --need specs/production_C8_need.json` makes the
    deliverable **`runs/c8tierA/framework_input_final.json`**.
* **Cost.**
  * 183.1 allocated personal-desktop core-h, i.e. 122.2 amdq-equivalent at the plan's 0.667.
  * Production and top-up took 154.5 of that, and the strict re-checks 28.6, including 23.8 in two cancelled jobs.
  * The 156 core-h cap (1.5 x plan) was applied in plan (amdq) units. In raw personal-desktop core-h it is exceeded
    (`PRODUCTION_C8.md` section 2, open item 1).
* **How to run the C8 checks:**
  ```bash
  python3 py/campaign.py collect runs/c8tierA --need specs/production_C8_need.json
  python3 py/outliers.py runs/c8tierA --grad specs/gradients_C8.json --T 1e-5 --json runs/c8tierA/flags.json
  python3 tests/production_checks.py runs/c8tierA --json runs/c8tierA/production_checks.json   # WARN, rep vs pooled
  python3 tests/budget_C8.py runs/c8tierA [runs/c8tierA_topup1] --json runs/c8tierA/budget_C8.json   # miss > 1.5x?
  python3 tests/tier_vs_pilot_C8.py runs/c8tierA --json runs/c8tierA/tier_vs_pilot.json
  python3 tests/strict_recheck.py prepare runs/c8tierA runs/c8tierA_strict/lowdim A3_ddE:2:6 Q4_vdE:6:2 ...
  python3 tests/validate_C8.py --run runs/c8tierA_topup1 --run runs/c8tierA --run runs/c8val ... --out results/validate_C8_tierA
  ```
  `validate_C8.py` keeps the first entry of each coefficient, so a production tier must be listed before the pilots.
* **Assembly (2026-10-04, `../RESULTS_C8.md`, `../assembly/README.md`).** The tier-A deliverable went through the
  framework at order C8, strict and per replicate. Results:
  * W, L3, M21, M12 agree with the archive's inherited records to 2e-11 or better; N2 at -0.35 sigma; S at +2.1 sigma
    (7.5e-12 relative);
  * Ndelta at -0.30 sigma; B_done at -0.91 sigma.
  * `validate_C8.py` and `direct_C8.py` were rerun with tier A first (`../assembly/out/C8/`). `direct_C8.py` needs an
    absolute `--out` path, because the GLS tool runs in `../direct/src`.

### 11i. Tiers B and C: prepared 2026-10-04 (`PRODUCTION_C8.md` section 12), run 2026-10-04/06 (section 13; summary at the end of this section)

* **Targets and cap (user, 2026-10-04).** Tier B at sigma(C8 without J9) = 0.01, tier C as a gross check at total
  sigma(C8) ~ 3; at most 20,000 amdq-equivalent core-h (amdq + 0.667 x the personal desktop) for everything in this phase.
* **Specs.** `specs/production_C8_tierB_sigma0.01.json` (tier `c8tierB_s0.01`, 5,904 core-h, sigma 8.8e-3; regenerated
  byte for byte, so current) and `specs/production_C8_tierC_sigma3.json` (new, tier `c8tierC_s3`, 7,641 core-h,
  sigma(C8) 2.50; plan `results/plan_C8_alt_TB0.01_T3.{md,json}`), each split into `_sym` (heavy: Q8_v, Q6_vE, A7_d |
  A9, A7_E, Z8) and `_can` (cheap) with identical cfgs and seeds; `specs/probe_C8_BC.json` (tier `c8probeBC`) and
  `specs/checks_C8_BC.json` (tier `c8chkBC`). 21 new lattices (personal-desktop job 276); 459,114 new random streams, 0 overlaps
  with all 21 earlier run directories.
* **Exact scalars.** `A3[eps^3 l^1] = 0`, `A3[eps^3 l^0] = -5/9`, `A5[eps^-2 l^1] = 0`, `Z6[eps^-3 l^1] = 0` are computed by
  the engine in tier C (`_can`); the l^1 ones are explicit exact zeros from the engine's Hepp-sector pole bound (every
  sector of these jobs has at most one subtracted variable, so the Laurent order -2 cannot occur); -5/9 also follows from
  the A3 closed form (sympy). `tests/exact_scalars_C8.py` checks all of it (PASS) and later the delivered values.
* **Budget guard.** Stage P runs every heavy group on amdq on the conv pilot's sector sample at its production N (~94
  core-h), so sigma vs N (1009, 4001, production N on identical sectors) and the amdq cost are measured before the
  bulk. Guard 1 re-plans under the cap (`--budget-BC`, relaxing both targets by one factor if needed; at the pilot's
  pre-asymptotic rates tier B at 0.01 would cost ~46k core-h); guard 2 projects spent + remaining + reserve after the
  first chunk of every heavy job and at every poll, and stops a group (finishing its remaining chunks at a lower N with
  fresh seeds) before the cap would be passed. Projected phase total at the planned rates: ~14,800 core-h.
* **Checks scheduled.** C9 pole check at eps^-1 (`c8chkBC`, stage P, one amdq node ~1 h); the tier-A Q6_vd strict
  re-check (the personal desktop, 1 core, stage P); RG higher logs of C9, d_v K8 and d_delta C7 from the tier data
  (`validate_C8.py`, production tiers first); strict re-checks of the most-warned B/C sectors (packed, <= 300 core-h).
* **Dry run** (2026-10-04 20:40-20:45 EDT): every spec plans; `sbatch --test-only` gives an immediate start on amdq and
  the personal desktop; amdq had 9 idle nodes, defq 15. Run with `bash slurm/submit_C8BC.sh sync|stageP|stageM|...` from the Mac.
* **Production (2026-10-04/06; log `PRODUCTION_C8.md` section 13).**
  * Stage P: probe on 2 amdq nodes, C9 check, cheap parts on the personal desktop.
  * Guard 1 re-plan (`results/plan_C8BC_replan.json`, planning target TB 0.007, priority B):
    * tier B `c8tierB_s0.01_r1`: Q8_v 91621 x 34 chunks, Q6_vE 370759 x 3, A7_d 32003;
    * tier C `c8tierC_s3_r2` (re-plan C2 `results/plan_C8BC_replan_C2.json`): A9 8009 x 44, A7_E 22637 x 9, Z8 4001.
  * Stage M arrays on amdq (at most 8 of our nodes): 569858 (B), 570223 (C), and 570513 (A7_E chunks 1-8 at N = 16001,
    after the guard-2 STOP at 20,079 projected).
  * Top-ups with fresh seeds: A5_dE (B, 5.0x miss -> 0.12x) and Z8 (C, 4.6x miss -> 0.16x).
  * Strict re-checks of the most-warned sectors of Q6_vE, A7_d, A9, A7_E and Z8 on the personal desktop; they agree. The Q8_v
    re-check was cancelled from outside and has no result.
  * C9 pole check at eps^-1: N = 1009, then confirmed at N = 4001.
* **Results.**
  * sigma(C8 part): tier B 5.1e-3, tier C 2.4.
  * Deliverables: `runs/c8tierB_s0.01_r1/framework_input_final.json`, `runs/c8tierC_s3_r2/framework_input_final.json`,
    and `runs/c8tiersABC/framework_input_final.json` (A + B + C, `tests/merge_tiers_C8.py`). SHA-256s are in
    `runs/c8BC_SHA256SUMS.txt`.
  * Framework at order C8 (strict): complete, C8 = 242.83 +- 2.4 (largest estimator). No archive value was read.
  * Assembly (2026-10-07, `../RESULTS_C8.md`): C8 = 242.825 +- 2.37, -1.92 sigma from the claim (A9_1 -2.19 sigma);
    C8 - J9/4 at -0.20 sigma. Check run `runs/c8chkA7` (spec `specs/checks_C8_A7v_A7k1.json`) added in that phase.
* **New tools and files.**
  * `tests/merge_tiers_C8.py`: per-scalar merge of tier inputs.
  * `slurm/packed_personal-desktop.sbatch`: packed strict re-checks on the personal desktop.
  * `specs/checks_C8_BC_N4001.json`: the N = 4001 C9 pole confirmation.
  * `budget_guard_C8.py`: `--efficiency measured` and `reduce`, both used in production.
  * sacct records: `logs/symmetry/sacct_c8BC_{mainB,mainC,chk4001}.txt`.
