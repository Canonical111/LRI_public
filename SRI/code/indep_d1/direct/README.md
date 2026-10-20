# direct/ — finite-cutoff direct evaluation of the hard-core ordered kink moments

Role in the independent C6/C7 re-derivation: a **second, methodologically different
numerical check**. Every raw moment entering the C6/C7 beta inputs is evaluated
**directly at finite cutoff eps** (no eps expansion), with the v/delta log insertions
and the endpoint-source insertion, for 2..8 kinks, at 25+ cutoffs between 1/8 and 1/1000.
These numbers test (i) the engine's truncated expansions sum_k eps^k P_k(log eps),
(ii) exactly known moments, and (iii) the archive's own exact raw integrals
(through its recorded finite-cutoff evaluations).

**Status (phase 2, 2026-10-03).**
* The finite-cutoff table (phase 1) is frozen: ~1e-14 relative, independently validated. Phase 2 added
  Q8 at 10 more cutoffs in [0.00222, 0.0164] (symmetry amdq, jobs 569084-569086), so Q8 now has 18 cutoffs
  <= 0.021 like every n <= 7 moment.
* `src/compare_engine.py --offset-fit` was rewritten as a **generalized least-squares test** (engine
  coefficients as nuisance parameters with Gaussian priors, direct-only data weights, chi2 gate, tail log
  degree chosen by a scan, pulls for [eps^0 l^0] and [eps^0 l^1]), and calibrated by injected errors for
  every 5-8 kink spec moment (`src/calibrate_injections.py`, `results/injection_calibration.txt`).
* **What the engine comparison resolves** (measured by injected errors, details under Results): with
  *complete* engine series (every coefficient from the lowest eps power up to K, including c00), 3-4 kink
  finite and single-log parts at 1e-13..3e-4 relative, 5-kink ones at 5e-9..3e-7 (K = 1) or 3e-5..6e-4
  (K = 0), 6-kink Q6 (K = 1) at 2e-5..5e-4. These are thresholds for an error in one coefficient; an error
  shared by c00 and c01 is bounded only by the marginal 3-sigma size, up to about 4x larger (see the note under
  the 5-8 kink table). For 6-kink moments with K = 0 (Z6, Z6_v: 5e-2..3 relative) and for
  all 7- and 8-kink moments (no complete series exists; an ideal one would allow ~1e-3..1e-2 at best) the
  comparison is a **screen for gross errors only**. With the engine's present output format (only the
  coefficients the framework needs; no negative eps powers for most 5-8 kink moments) **none of the 16
  five-to-eight-kink spec moments is testable**: 7 are INCONCLUSIVE, 9 UNTESTABLE. All testable complete
  series PASS (19) except two K = 0 tail-model TENSIONs (A5_d, Z6_v); there is no OFFSET and no MODEL-FAIL.
  The decisive validation of the 5-8 kink inputs must come from the engine's internal checks and the
  framework's consistency checks; this comparison is a backstop.
* **Update (assembly phase, 2026-10-03):** with series completed by the assembly-phase engine runs, 44 of 47
  moments PASS, and the three flags are explained. See "Production comparison" near the end.
* Finite-part extraction from quad-precision data (a by-product) reproduces only the old inputs a and c
  (to 1e-15); for p, A, f its own variant-spread criterion (1e-3) leaves them undetermined although the
  central values happen to lie within 1e-8..5e-8 of the closed forms; E is not reproduced; the new 3- and
  4-kink inputs are not determined (see the last results section).

## Definitions (from the note, Secs. 3–6; nothing else was used)

* Kinks 0<X_1<...<X_n<1, charges q_i = (-1)^{i+1}; hard core only on consecutive gaps,
  X_{i+1}-X_i >= eps (note l.255). Kernel
  W_n(v,delta) = exp[2v sum_{i<j} q_i q_j f_delta(X_j-X_i)], f_delta(r) = (r^delta-1)/delta (l.370).
* A_n (n odd), Z_n (n even): int W_n; Q_n (n even): int D_n W_n, D_n = sum_j (X_{2j}-X_{2j-1}).
* Endpoint source (first eta derivative at eta=0, l.278–283):
  E I = int W sum_i q_i [f_delta(X_i) +- f_delta(1-X_i)] (U^odd: +, U^even: -). The Gauss code uses the
  reflection form 2 int W sum_i q_i f_delta(X_i) (valid for the first eta derivative only); the RQMC and
  mpmath codes use the two-sided form, so reflection is tested.
* Insertions: log W = 2(1+z) sum_k delta^k S_{k+1}/(k+1)!, v = 1+z, S_j = sum_{i<j} q_i q_j log^j(X_j-X_i);
  the series exp in (z,delta) reproduces eq:insertions (checked).
* **Convention of the tables: derivatives** d_v^a d_delta^b I at v=1, delta=0 (not Taylor coefficients),
  named as in `spec/out/raw_requirements.json`: `A7_v`, `Q4_dd`, `EQ4_vd`, `Z2_vvd`, base = no derivative.
  (Checked against the archive: its `Q4_dd`, `Q6_vv` are d^2, not [delta^2]; the engine's names map as
  `A5_vE` -> `EA5_v`, `Q6_E` -> `EQ6_base`.)

## Methods

### 1. Nested Gauss–Legendre in singularity-adapted coordinates (`src/direct_moments.c`, double, OpenMP)
* Translation integral done analytically (weight Lambda = 1-R; for source moments the exact
  int_0^Lambda log^k(x+c) dx). Remaining (n-1)-dimensional integral over gaps r_k >= eps, sum r <= 1.
* **form 0**: gaps nested r_1..r_{n-1}. Each middle gap r in [eps,B] uses the logistic map
  t = log(r/(B+eps-r)), which sends both the near-contact pole r = 0 (distance eps below the range) and the
  "squeeze" singularity r = B+eps (later gaps forced to eps) to t = -+infinity; the integrand is analytic in the
  strip |Im t| < pi, so Gauss–Legendre converges geometrically (~ (1.9)^(-2N) at eps=0.01) even though
  1/r^2 varies by 1/eps^2. The last gap uses the one-sided map r = eps e^s.
* **form 1** (required for source moments): the free length Lambda is the outermost variable (map with
  Lambda log Lambda endpoint handled by a truncated logistic map, tcut = 20), gaps nested inside, last gap fixed.
  Used also for no-source moments as a cross-parametrization check.
* Derivatives: all [z^a delta^b] (a+b <= 3) computed at once per point from the exact series exp.
* Neumaier-compensated sums; nested-loop incremental pair updates.
* Error estimate per entry: `err = max(|I(N_hi) - I(N_prev)|, 2e-15 * int|integrand|)`, i.e. the change
  between the two highest Gauss orders (orders N_hi-8, N_hi and, for the cheap cases n<=5 and no-source n=6,
  N_hi+8; N_hi = 4 ceil(8.7 log(1/eps)/4)) with a rounding floor. Observed convergence is geometric (about
  10^3 per +8 points at eps=0.01), so this is conservative: in every adequate fit of the engine comparison
  chi2/dof is 0.001-0.07, i.e. the actual scatter is about 0.03-0.25 of the quoted err. It is a convergence
  diagnostic, not an interval bound.

### 2. Independent cross-checks
* `src/exact_refs.py` (mpmath): closed forms Z2 = 1/eps+l-1, Q2 = -l-1+eps, and A3(eps) (dilog form,
  derived by hand in the file); **Cauchy-contour** Taylor coefficients of the *unexpanded* two-kink kernels
  in complex (v, delta) for Z2, Q2, EZ2, EQ2 (tests the insertion algebra and the two-sided source).
* `src/qmc_check.py` (numpy, independent code): Owen-scrambled Sobol RQMC, 16 scramblings x 2^22 points,
  two **different** domain maps (independent log-uniform gaps with Lambda_+, and a sequential one-sided log map),
  two-sided source term. NOTE: scipy's Sobol default `bits=30` puts all points on a 2^-30 grid and biased the
  means at the 2e-9 level (first pass, kept as `results/qmc_bits30_superseded.jsonl`); production uses `bits=52`.
  Caveat: the RQMC code was written by the same author and shares the series-in-(z, delta) insertion structure
  with the Gauss code, so it tests the integration, the domain maps and the reflection of the source, not the
  insertion algebra.
* form 0 vs form 1 Gauss runs.
* The phase-1 reviewer's fully independent check (`review/indep_cauchy.py`, `review/small_eps_check.py`,
  `review/n6_check.py`: unexpanded kernel at complex (v, delta), discrete Cauchy/FFT extraction, two-sided
  source with an exact complex-delta primitive, stick-breaking tanh-sinh coordinates) agrees with the table
  for n = 2..6 (n <= 4 at 1e-10..1e-13, n = 5 at <= 2e-7, n = 6 at <= 1.4e-6, its own quadrature being the
  limit). It covers the derivative/Taylor convention, the [delta^2] factor, the source sign and reflection and
  the Q insertion. **For n = 7, 8 the conventions rest on the archive exact-expression matches (A7 at 1/8,
  A7_v and Q8 at 1/10, to <= 3e-16) and on the RQMC**, which is adequate but not a fully independent check of
  the insertion algebra there.

### 3. Comparison tools
* `src/compare_archive.py`: the archive's recorded finite-cutoff numbers (read-only, comparison only):
  exact-expression ("hyperlog") evaluations at eps=1/8 (C6 stage: A7, Q6_v, EA5, A3_d, Z4_d, A5_d) and
  eps=1/10 (C7/F3 stages: A7_v, Q4_dd, Q8, Q6_vv; F1c: Q4_vvd, EQ4_vd), plus the archive's own direct
  cubatures (Sobol/Gauss).
* `src/compare_engine.py ENGINE.json|DIR ... [--offset-fit] [--merge]`: compares the engine's expansions with
  the direct table (full description in the module docstring).
  * Input: per moment `{"k,j": [value, err]}` (optionally wrapped in `{"results": ...}`), `{"terms": [[k,j,c],...]}`,
    or the engine's flat `{"A7_v[eps^0 l^1]": [value, err]}`; engine names are mapped to the direct names.
    Optional per-moment `"cov"` (`keys`, `matrix`) or `"replicates"` (`keys`, `values`, covariance of the
    mean = sample cov / n) are used as the prior covariance; the present engine files carry only
    per-coefficient errors (no replicates), so the priors are diagonal. `--merge` takes the union of a
    moment's coefficients over several files (smaller error wins), e.g. a production series completed by the
    negative powers of a validation run.
  * Part 1: direct - engine at every cutoff (flagged `partial` when the engine omits structural coefficients).
  * Part 2 (`--offset-fit`), per moment, over the cutoffs eps <= 0.021 (18 for every spec moment): residual
    r(eps) = direct - engine fitted by **generalized least squares**,
    `r = d0 + d1 l + sum x_kj eps^k l^j (engine nuisance shifts, prior x ~ N(0, Sigma_engine)) + sum f_kj eps^k l^j
    (structural coefficients the engine does not quote, free) + sum_{k=K+1}^{K+P} sum_{j<=J} t_kj eps^k l^j (tail)`.
    Data weights are the **direct errors only**; each engine coefficient error enters once, through its prior
    row, because it is common to all cutoffs (the phase-1 tool added it to every point as independent noise,
    which inflated u0 by 1e3-1e7 for n >= 5 and made every 5-8 kink test vacuous). Coefficients quoted with
    err = 0 are exact.
  * Structure: eps powers from p_min (spec tight bounds: A_{2m+1}, Z_{2m}, EA_{2m+1}: -m; Q_{2m}, EZ_{2m},
    EQ_{2m}: -(m-1)) to K; log degree at k = 0 the highest nonzero one the engine quotes (J0); at k != 0 the
    engine's own range where it quotes anything there, else max(0, J0 + 2k + 1) for k < 0 (satisfied by every
    complete engine series available).
  * Tail (log degree **scanned, not guessed**): J = J_K-2 ... J_K+1 (J_K = highest nonzero log degree at k = K),
    P = 1, 2, 3, each variant with >= 3 dof. **MODEL-FAIL** unless some variant has chi2/dof <= 2.5 (quoted
    direct errors; chi2 includes the prior rows). Because the quoted direct errors are conservative, the
    absolute gate alone accepts biased under-fitted tails (seen in development: 3-6 sigma false flags), so the
    central variant minimizes BIC = chi2/s2 + nfree ln(npts) with the observed noise scale s2 = min(1, smallest
    chi2/dof among variants with dof >= 4); variants within Delta BIC <= 6 are "competitive". u is inflated by
    sqrt(max(1, chi2/dof)), never deflated.
  * Reported: d0 +- u0 (data posterior), the engine's sigma e00, **pull0 = d0/sqrt(u0^2 + e00^2)**, the same for
    [eps^0 l^1], the joint 2-dof X2 = d^T (C_d + C_eng)^-1 d, chi2/dof, 3-sigma sizes 3 sqrt(u^2 + e^2).
    d = (direct-preferred value) - (engine value): an error +delta in the engine's c00 gives d0 -> d0 - delta.
  * Verdicts: **PASS**; **OFFSET** = |pull| >= 3 or X2 >= 11.83 in the central variant and in every competitive
    one; **TENSION** = flagged in the central variant only (tail-model dependent: inspect, do not quote as an
    error); **MODEL-FAIL**; **INCONCLUSIVE** = the engine omits structural coefficients other than c00, which
    then enter free and can mimic the tail (for A5, A5_v, Q6 and Z6 the pilot5 series gave raw TENSIONs this way
    while their complete counterparts PASS; for EA5, EA5_v and EQ6 there is no complete counterpart, see the
    note under the 5-8 kink table; the raw verdict is kept as `verdict_raw`); **UNTESTABLE** = no
    tail variant with >= 3 dof.
  * The rule is asymmetric. PASS means the *central* variant is not flagged; a competitive variant may still be.
    This happens for A5_v (merged, validation_c, validation_d), Q4_d and Q6_base. For Q6_base (merged), the
    variant J=2, P=3 at Delta BIC = 0.97 gives d0 = 0.0073 +- 0.0025 (pulls 2.9 and 3.0), while J=5, P=1 gives
    -0.0001 +- 0.0005. The `competitive` list in `*_offsets.json` records each variant's flag. These offsets lie
    below the quoted 3-sigma sizes, so the stated resolutions hold, but at that level such a PASS depends on the
    tail model.
* `src/calibrate_injections.py`: injected-error calibration of the above (see Results).
* `tests/test_compare_engine.py`: 20 regression checks (exact synthetic series, the phase-1 and reviewer
  injections, the reviewer's garbage series, corrupted complete series -> MODEL-FAIL, partial series ->
  INCONCLUSIVE/UNTESTABLE, exact linearity of injections). All pass (6 s).

### 4. Finite-part extraction from quad-precision direct data (by-product, `src/fpe_*.py`, `src/direct_moments_q.c`)
* `direct_moments_q.c`: binary128 (__float128) version of form 0 (no-source moments), ~28–33 digits;
  `fpe_two_kink_mp.py`: EQ2/EZ2 and n=2 moments with mpmath (45 digits).
* 100 cutoffs log-spaced in [1e-9, 1e-4]; normalized responses C3 = A3 - Z2, K4 = Q4 - Q2 Z2 (Leibniz for
  derivatives), K2 = Q2, EK2 = EE Q2 formed **at finite eps**; each fitted to
  sum_{k=kmin}^{K} sum_{j<=D} c_kj eps^k l^j (mpmath QR, 80 digits) for several (D, K, window) variants;
  [eps^0 l^0], [eps^0 l^1] and their spread are taken; inputs assembled with the framework's formulas
  (`framework/out/beta_input_formulas.json`). An input counts as **determined** only if the spread over the
  fit variants is small; by that criterion only a and c are determined.
* Five-kink and higher inputs are out of reach of this route (cancellation of eps^-2 pieces in C5 plus the
  4D quad cost). A 60-digit three-kink extraction was considered in phase 1 (estimated "1 node-hour"); that
  estimate is not credible (60 digits may not suffice for log degrees 5-7, and far more cutoffs are needed) and the item is
  **dropped as out of scope** unless a pilot shows otherwise.

## Independence
No archive engine code or exact raw data were imported, called or copied. The archive was used only for
definitions (note, stage READMEs/TeX) and, at the end, for **numbers to compare with** (`compare_archive.py`,
reference values in `fpe_fit.py`). The compendium was never written to. (The phase-1 review noticed
compendium files with mtimes during this workflow; per the orchestrator these are future-dated mtimes from
the zip, with unchanged content hashes, not modifications. direct/ has no write path there.)

## How to run
Local (quick):
```
cd src
clang -O3 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -L/opt/homebrew/opt/libomp/lib -lomp -o direct_moments direct_moments.c -lm
./direct_moments -n 7 -k A -e 0.1 -N 24 -o 1            # A7, A7_v (=[z^1]) at eps=0.1
./direct_moments -n 5 -k A -E -f 1 -e 0.125 -N 24 -o 1  # EA5 at eps=1/8
python3 qmc_check.py -n 4 -k Q -E -e 0.1 -o 1 --log2 16 --reps 8 --map seq
```
Cluster (symmetry, amdq whole AMD nodes; code under <SCRATCH>/sri_c6c7/direct):
```
gcc -O3 -march=x86-64-v3 -fopenmp -o direct_moments direct_moments.c -lm
gcc -O3 -march=x86-64-v3 -fopenmp -o direct_moments_q direct_moments_q.c -lquadmath -lm
sbatch slurm/gauss_main.sbatch; sbatch slurm/gauss_n8.sbatch; sbatch slurm/gauss_ext.sbatch; sbatch slurm/gauss_ext8.sbatch
sbatch slurm/gauss_dense.sbatch; sbatch slurm/gauss_dense8a.sbatch; sbatch slurm/gauss_dense8b.sbatch
sbatch slurm/gauss_q8xa.sbatch; sbatch slurm/gauss_q8xb.sbatch; sbatch slurm/gauss_q8xc.sbatch    # phase 2: Q8 cutoffs
sbatch slurm/qmc_only.sbatch;   sbatch slurm/qmc_refs.sbatch (exact_refs part)
sbatch slurm/fpe_base.sbatch;   sbatch slurm/fpe_fit.sbatch
```
Analysis (local, seconds, after `rsync` of results/):
```
python3 build_table.py && python3 compare_checks.py && python3 compare_archive.py
python3 ../tests/test_compare_engine.py                                     # regression tests of the GLS tool
python3 compare_engine.py ENGINE_FILE(S) --offset-fit [--merge] --out ../results/engine_comparison_X.json
python3 calibrate_injections.py                                             # injected-error calibration (~40 s)
bash run_analysis.sh       # all of the above + the four engine comparisons + summary tables (~2 min)
```
Run plan: `src/plan.py`; driver: `src/run_campaign.py` (resumable JSONL).

## Files
* `src/` code (see above); `slurm/` batch scripts; `logs/` Slurm logs; `tests/` synthetic/perturbed engine
  files and `test_compare_engine.py` (`tests/superseded_phase1/`: outputs of the phase-1 tool).
* `results/gauss_*.jsonl` raw Gauss runs (phase 2: `gauss_q8x{a,b,c}.jsonl`); `results/direct_table.{json,csv}`
  final table (all entries); `results/spec_moments_by_eps.csv` the 75 spec raw moments (rows) x cutoffs;
  `results/qmc.jsonl`, `results/exact_refs.json`, `results/internal_checks.json`, `results/crossform_check.json`;
  `results/archive_comparison.{json,txt}`;
  `results/engine_comparison_{validation_c,validation_d,pilot5,merged}{.json,_offsets.json,.txt}` (GLS tool,
  phase 2; `results/superseded_phase1/` holds the phase-1 outputs, whose 5-8 kink offsets were vacuous);
  `results/injection_calibration.{json,txt}`;
  `results/fpe_data.jsonl`, `results/fpe_atoms.json`, `results/fpe_inputs.json`.
* `review/`: the phase-1 reviewer's scripts and test inputs (kept; `gls_offset.py` was the sketch for the
  GLS rewrite).
  `review/gate2_indep_gls.py` (phase-2 gate review: independent marginalized-covariance GLS, agrees exactly with
  `compare_engine.gls_variant`) and `review/gate2_struct_probe.py` (the stability probe behind the note on
  EA5_base, EA5_v, EQ6_base).

## Results

### Direct table (`results/direct_table.{json,csv}`)
(Main cutoffs) 1080 entries = all [z^a delta^b] derivatives (a+b <= 3 for n <= 5, <= 2 for n = 6, <= 1 for
n = 7, base for n = 8 plus v, vv at eps = 1/8, 1/10) of A_n, Z_n, Q_n and their source versions at 8 cutoffs.
**All 75 raw moments of `spec/out/raw_requirements.json` are covered at every cutoff 1/8 ... 1/500** (at
1/1000 everything except Q8). A dense grid of 13 further cutoffs in [0.00122, 0.0164] (all spec moments with
n <= 7) and Q8 at 0.003, 0.004, 0.007, 0.015 (phase 1) and at 0.00222, 0.00271, 0.00331, 0.00405, 0.00603,
0.00737, 0.009, 0.011, 0.0134, 0.0164 (phase 2) serve the engine comparison: **every spec moment, Q8
included, now has 18 cutoffs <= 0.021.**
Precision: the change between the two highest Gauss orders is below the rounding floor for essentially all
entries, i.e. **relative accuracy ~1e-14 (quoted err = max(Delta_N, 2e-15 x int|f|))**; worst quoted
relative errors: n=6 4e-12, n=7 6e-13, n=8 7e-13; every entry has at least two Gauss orders.
The 10 phase-2 Q8 entries (two Gauss orders each, N = 28..56) are all at the 2e-15 rounding floor except
eps = 0.0164 (6e-15), e.g. Q8(0.00222) = 86440001.5891821 +- 1.7e-7; the table now has 2771 entries over 25 cutoffs
(no phase-1 entry changed; `crossform_check.json`, `internal_checks.json` and `archive_comparison.*` are
byte-identical after the rebuild).
Representative values (relative err in brackets):

| moment | eps=0.1 | eps=0.05 | eps=0.02 | eps=0.01 |
|---|---|---|---|---|
| A3_base | 7.05938653404232 (2e-15) | 19.6782105645387 (2e-15) | 56.354480099486 (2e-15) | 113.790405287292 (2e-15) |
| A3_vdd | 1333.16523561206 (2e-15) | 9780.44244716204 (2e-15) | 82740.1039176586 (2e-15) | 344825.101733295 (2e-15) |
| Z4_base | 13.3847827396341 (2e-15) | 112.763335860085 (2e-15) | 1020.4026301179 (2e-15) | 4543.8684618648 (2e-15) |
| Q4_dd | 324.486978038424 (2e-15) | 4038.08634663211 (2e-15) | 49485.5025745747 (2e-15) | 243104.293789561 (2e-15) |
| A5_v | 93.4942171734119 (2e-15) | 1597.29612042565 (2e-15) | 20238.5781733997 (2e-15) | 100175.268174252 (2e-15) |
| EA5_v | -325.165210763584 (2e-15) | -4491.99311168436 (2e-15) | -49131.9261634235 (2e-15) | -227875.809159665 (2e-15) |
| Q6_v | 33.679018997238 (2e-15) | 1981.28826050455 (2e-15) | 52463.1502756123 (2e-15) | 369064.718292412 (2e-15) |
| Z6_v | 73.1745938401035 (2e-15) | 6118.11538247758 (2e-15) | 286396.198254187 (2e-15) | 3323525.24567792 (2e-15) |
| EQ6_base | -10.5861312569879 (3e-14) | -371.728688672545 (7e-15) | -5590.22654670092 (2e-15) | -26461.1992326728 (2e-15) |
| A7_v | 24.3373481107903 (2e-15) | 7722.64046582703 (2e-14) | 493046.145336343 (3e-15) | 5549538.35709679 (2e-15) |
| Q8_base | 0.0871896170534513 (2e-15) | 280.418672352063 (3e-14) | 39226.6548831655 (2e-15) | 581837.732376028 (2e-15) |

### Internal validation (`results/internal_checks.json`)
* exact closed forms (Z2, Q2, A3 at 7 cutoffs) and Cauchy-contour coefficients of the unexpanded two-kink
  kernels (Z2, Q2, EZ2, EQ2, all derivatives to order 3, eps = 0.1, 0.01): 101 comparisons,
  **max relative difference 3.2e-15**;
* RQMC (independent numpy code, two different domain maps, two-sided source term), 424 comparisons at
  eps = 0.1 ... 0.01, n = 3 ... 8: **rms z = 0.86, max |z| = 2.52, none above 3**; median relative QMC
  standard error 3.7e-9 (sequential map) and 3e-7 (box map); the first pass with scipy's default 30-bit Sobol
  showed a spurious 2e-9 bias (superseded file kept);
* form 0 vs form 1 Gauss (different parametrizations), 42 pairs: max relative difference 5.3e-16;
* phase-1 review: independent unexpanded-kernel Cauchy check for n <= 6 (see Methods 2).

### Archive finite-cutoff records (`results/archive_comparison.json`)
Agreement with the archive's **exact raw expressions evaluated at finite eps** (independent test of its raw
integration):

| eps | moment | archive (exact expr.) | direct | |rel diff| |
|---|---|---|---|---|
| 1/8 | EA5 | -10.13480924936128328 | -10.134809249361282 | < 1e-16 |
| 1/8 | Q6_v | 3.61349120026724826 | 3.6134912002672483 | < 1e-16 |
| 1/8 | A3_d | -18.06288124739496638 | -18.062881247394969 | 2.0e-16 |
| 1/8 | Z4_d | -36.58665668378287372 | -36.586656683782877 | < 1e-16 |
| 1/8 | A5_d | -23.79522821848594149 | -23.795228218485938 | 1.5e-16 |
| 1/8 | A7 | 0.03557288770735261 (16 digits printed) | 0.035572887707352618 | 2.0e-16 |
| 1/10 | A7_v | 24.33734811079028777 | 24.33734811079028 | 2.9e-16 |
| 1/10 | Q4_dd | 324.4869780384239984 | 324.48697803842379 | 7.0e-16 |
| 1/10 | Q8 | 0.08718961705345130278 | 0.087189617053451282 | 1.6e-16 |
| 1/10 | Q6_vv | 425.5449632473382428 | 425.54496324733816 | 1.3e-16 |
| 1/10 | Q4_vvd | -2624.464525265052 (reconstructed) | -2624.4645252650507 | 5.2e-16 |
| 1/10 | EQ4_vd | 957.648003884333 (reconstructed) | 957.64800388433287 | 5.9e-16 |

The archive's own direct cubatures agree with ours within their stated errors (Sobol at 1/8: 0.2–1.6 sigma;
Gauss at 1/10: to 1e-16..3e-11, its order-12 n=8 control being the least converged).

### Engine comparison (GLS tool; `results/engine_comparison_*`, `results/injection_calibration.*`)

**Phase 1 vs phase 2.** The phase-1 `--offset-fit` added each engine coefficient error to every cutoff as
independent noise, although it is common to all cutoffs; this inflated u0, u1 by 1e3-1e7 for n >= 5, its
verdict ignored chi2, and its tail log degree was a guess. The phase-1 review showed that injected errors
of +1e-3 (A5), +1e-2 (A5_v), +0.1 (Q6, 230 engine sigma) and +1 (Z6) all came back "OK", that a garbage A7_v
series with chi2/dof = 8.9e25 passed, and that Q8 (8 cutoffs) could not be fitted. All phase-1 engine-comparison
numbers are therefore withdrawn (`results/superseded_phase1/`). The GLS tool (Methods 3) detects those
injections (A5, A5_v, Q6: robust OFFSET; Z6 with K = 0: TENSION), rejects corrupted complete series
(MODEL-FAIL) and refuses to conclude on partial series (`tests/test_compare_engine.py`, 20/20).

**Engine files compared** (the engine's final production series did not exist yet): the complete validation
series `engine/results/validation_c.json` (A3, Z4, Q4, A5 families, K = 0..2) and
`validation_d_inputs.json` (A3, A3_v, Z2_v, Z4, Z4_v, Q4, A5, A5_v, Z6, Z6_v, Q6), the production-format
pilot series `engine/runs/pilot5/results.json` (all 46 groups, only the coefficients the framework needs),
and `merged` = pilot5 completed by the negative powers of the two validation files (`--merge`).

#### Verdicts on the existing engine output

| engine file(s) | PASS | TENSION | OFFSET | MODEL-FAIL | INCONCLUSIVE | UNTESTABLE |
|---|---|---|---|---|---|---|
| validation_c | 15 | 1 (A5_d) | 0 | 0 | 0 | 0 |
| validation_d | 10 | 1 (Z6_v) | 0 | 0 | 0 | 0 |
| pilot5 | 6 | 0 | 0 | 0 | 30 | 10 |
| merged | 19 | 2 (A5_d, Z6_v) | 0 | 0 | 18 | 8 |

#### 5-8 kink spec moments: verdicts and injected-error thresholds

Thresholds: smallest injected |delta| (ladder 0.25..100 x D3, both signs) giving a non-PASS verdict (baseline PASS only) / a robust OFFSET; relative to |c| in brackets. "proj." = design estimate of the 3-sigma size 3 sqrt(u^2 + e^2) for a complete series with K = 1 (negative powers and k = 1 exact, fixed tail k = 2, 3 with log degree J0-1, * = J0-2 where J0-1 leaves < 3 dof; no tail selection, no joint X2): an order-of-magnitude guide, not a bound.

| moment | production format (pilot5) | complete series (merged with validation runs) | K | c00: non-PASS / OFFSET | c01: non-PASS / OFFSET | proj. c00 / c01 (K=1) |
|---|---|---|---|---|---|---|
| A5_base | INCONCLUSIVE (raw TENSION); 6 coeff. missing | PASS | 1 | 5.2e-05 (3e-07) / 5.2e-05 (3e-07) | 5.4e-06 (4e-08) / 5.4e-06 (4e-08) | 4.5e-06 / 5.2e-07 |
| A5_d | UNTESTABLE; 10 coeff. missing | TENSION | 0 | n/a / 2.1e+00 (6e-04) | n/a / 1.7e-01 (1e-04) | 7.4e-01 / 7.1e-02 |
| A5_v | INCONCLUSIVE (raw TENSION); 9 coeff. missing | PASS | 1 | 2.3e-05 (1e-08) / 4.6e-05 (3e-08) | 2.7e-06 (2e-09) / 5.4e-06 (5e-09) | 4.1e-03 / 4.3e-04 |
| A5_vd | UNTESTABLE; 12 coeff. missing | UNTESTABLE (no complete series exists) | 0 | - | - | 1.6e+01 / 1.5e+00* |
| A5_vv | UNTESTABLE; 10 coeff. missing | UNTESTABLE (no complete series exists) | 0 | - | - | 5.9e+00 / 5.7e-01 |
| A7_base | UNTESTABLE; 12 coeff. missing | UNTESTABLE (no complete series exists) | 0 | - | - | 1.9e+00 / 1.9e-01 |
| A7_v | UNTESTABLE; 15 coeff. missing | UNTESTABLE (no complete series exists) | 0 | - | - | 5.7e+01 / 5.6e+00* |
| EA5_base | INCONCLUSIVE (raw OFFSET); 6 coeff. missing | INCONCLUSIVE (no complete series exists) | 0 | - | - | 5.7e-03 / 1.5e-05 |
| EA5_v | INCONCLUSIVE (raw OFFSET); 8 coeff. missing | INCONCLUSIVE (no complete series exists) | 0 | - | - | 1.5e-01 / 9.6e-04 |
| EQ6_base | INCONCLUSIVE (raw OFFSET); 8 coeff. missing | INCONCLUSIVE (no complete series exists) | 0 | - | - | 1.2e+00 / 2.7e-01 |
| Q6_base | INCONCLUSIVE (raw TENSION); 9 coeff. missing | PASS | 1 | 2.8e-02 (1e-04) / 1.1e-01 (5e-04) | 3.5e-03 (8e-06) / 7.0e-03 (2e-05) | 8.6e-04 / 9.0e-05 |
| Q6_d | UNTESTABLE; 12 coeff. missing | UNTESTABLE (no complete series exists) | 0 | - | - | 3.9e+00 / 3.8e-01* |
| Q6_v | UNTESTABLE; 10 coeff. missing | UNTESTABLE (no complete series exists) | 0 | - | - | 1.6e+00 / 1.6e-01 |
| Q8_base | UNTESTABLE; 15 coeff. missing | UNTESTABLE (no complete series exists) | 0 | - | - | 4.6e+01 / 6.0e+00* |
| Z6_base | INCONCLUSIVE (raw TENSION); 5 coeff. missing | PASS | 0 | 5.4e+01 (4e-01) / 4.3e+02 (3e+00) | 4.5e+00 (2e-02) / 1.8e+01 (8e-02) | 1.9e-02 / 2.1e-03 |
| Z6_v | UNTESTABLE; 12 coeff. missing | TENSION | 0 | n/a / 1.3e+02 (5e-02) | n/a / 1.4e+01 (1e-01) | 4.2e+01 / 4.0e+00 |

**How to read the thresholds (gate review, 2026-10-03).** (i) They are for an error in *one* coefficient
(c00 or c01 alone). Most non-PASS thresholds sit on the lowest rung of the ladder (0.25 D3), so the true
threshold can be lower. They come from the joint X2, which, given c01, pins c00 much more tightly than its
marginal error does. An error that moves c00 and c01 together along the badly determined direction is bounded
only by the marginal 3-sigma size D3 (e.g. A5_base merged: D3(c00) = 2.1e-4 against the single-coefficient
threshold 5.2e-5). Read the relative ranges quoted in the Status section in that sense.
(ii) The **raw OFFSETs of EA5_base, EA5_v and EQ6_base** (production format and merged alike: no complete
series exists for these) are not evidence of an engine error, and not evidence against one. A probe varied the
fit window (eps_max = 0.021, 0.051, 0.11) and the assumed log degree of the free negative-power
coefficients (+0, +1, +2 over the J0 + 2k + 1 rule). Under those changes the central d0 of EQ6_base moved
between -1.1e5 and +2.2e4 (|c00| = 4.6e3), and that of EA5_base between -3.7e3 and +1.4e4 (|c00| = 1.3e2). The
formal u0 stayed about ten times smaller than this spread, which is the partial-series instability that the
INCONCLUSIVE label covers (`review/gate2_struct_probe.py`). Among source moments the J0 + 2k + 1 rule for negative powers has been checked only
on EZ4 (the one complete source series). These three moments stay open until the engine writes complete
series for them.


#### Complete series: GLS results (merged file; central tail variant)

| moment | verdict | K | tail J,P / dof | chi2/dof | d0 +- u0 (pull0) | d1 +- u1 (pull1) | X2 | 3-sigma c00 / c01 |
|---|---|---|---|---|---|---|---|---|
| A3_base | PASS | 2 | 0,3 / 13 | 0.010 | +3.8e-13 +- 3.3e-12 (+0.12) | +6.7e-14 +- 5.8e-13 (+0.12) | 0.013 | 1.0e-11 / 1.7e-12 |
| A3_v | PASS | 2 | 1,2 / 12 | 0.018 | -3.1e-11 +- 8.2e-11 (-0.38) | -4.7e-12 +- 1.3e-11 (-0.36) | 0.39 | 2.5e-10 / 4.0e-11 |
| A3_d | PASS | 2 | 2,2 / 10 | 0.022 | -1.7e-10 +- 1.4e-09 (-0.12) | -2.4e-11 +- 2.1e-10 (-0.12) | 0.016 | 4.3e-09 / 6.2e-10 |
| A3_vd | PASS | 2 | 4,1 / 11 | 0.020 | +1.5e-09 +- 9.2e-09 (+0.16) | +2.0e-10 +- 1.4e-09 (+0.15) | 0.3 | 2.8e-08 / 4.1e-09 |
| A3_vv | PASS | 2 | 2,2 / 10 | 0.023 | +2.7e-10 +- 5.8e-09 (+0.05) | +4.2e-11 +- 8.4e-10 (+0.05) | 0.011 | 1.7e-08 / 2.5e-09 |
| Z2_v | PASS | 2 | 0,1 / 15 | 0.001 | -5.2e-13 +- 8.3e-12 (-0.06) | -1.1e-13 +- 1.8e-12 (-0.06) | 0.0044 | 2.5e-11 / 5.3e-12 |
| Z4_base | PASS | 1 | 1,3 / 10 | 0.026 | -1.7e-09 +- 2.3e-08 (-0.07) | -2.5e-10 +- 3.1e-09 (-0.08) | 0.049 | 6.8e-08 / 9.4e-09 |
| Z4_v | PASS | 1 | 2,2 / 10 | 0.027 | -3.2e-08 +- 8.9e-07 (-0.04) | -5.2e-09 +- 1.2e-07 (-0.04) | 0.17 | 2.7e-06 / 3.5e-07 |
| Z4_d | PASS | 1 | 2,3 / 7 | 0.025 | -1.2e-05 +- 1.1e-04 (-0.11) | -1.4e-06 +- 1.3e-05 (-0.11) | 0.061 | 3.3e-04 / 3.9e-05 |
| Q4_base | PASS | 2 | 1,3 / 10 | 0.019 | +4.1e-12 +- 1.7e-10 (+0.02) | +7.2e-13 +- 2.4e-11 (+0.03) | 0.026 | 5.0e-10 / 7.3e-11 |
| Q4_v | PASS | 1 | 4,2 / 6 | 0.006 | -8.4e-06 +- 2.7e-05 (-0.31) | -8.7e-07 +- 2.8e-06 (-0.31) | 0.11 | 8.0e-05 / 8.4e-06 |
| Q4_d | PASS | 1 | 4,2 / 6 | 0.010 | +1.8e-05 +- 6.1e-05 (+0.29) | +1.9e-06 +- 6.4e-06 (+0.29) | 0.11 | 1.8e-04 / 1.9e-05 |
| Q4_vd | PASS | 1 | 5,2 / 4 | 0.007 | +5.6e-03 +- 8.4e-02 (+0.07) | +5.5e-04 +- 8.0e-03 (+0.07) | 0.068 | 2.5e-01 / 2.4e-02 |
| Q4_vv | PASS | 1 | 5,2 / 4 | 0.003 | -4.8e-03 +- 3.4e-02 (-0.14) | -4.6e-04 +- 3.3e-03 (-0.14) | 0.075 | 1.0e-01 / 9.9e-03 |
| EZ4_base | PASS | 0 | 2,3 / 7 | 0.044 | +1.2e-05 +- 2.9e-05 (+0.40) | +1.1e-06 +- 2.7e-06 (+0.40) | 0.17 | 8.6e-05 / 8.0e-06 |
| A5_base | PASS | 1 | 4,2 / 6 | 0.008 | -1.6e-05 +- 6.9e-05 (-0.24) | -1.7e-06 +- 7.2e-06 (-0.24) | 0.057 | 2.1e-04 / 2.2e-05 |
| A5_v | PASS | 1 | 3,2 / 8 | 0.009 | -2.7e-06 +- 3.1e-05 (-0.09) | -3.1e-07 +- 3.6e-06 (-0.09) | 0.022 | 9.2e-05 / 1.1e-05 |
| A5_d | TENSION | 0 | 4,2 / 6 | 0.021 | -4.3e+00 +- 7.2e-01 (-6.06) | -3.1e-01 +- 5.6e-02 (-5.60) | 1e+04 | 2.1e+00 / 1.7e-01 |
| Q6_base | PASS | 1 | 4,2 / 6 | 0.037 | +1.4e-02 +- 3.7e-02 (+0.38) | +2.1e-03 +- 4.6e-03 (+0.45) | 10 | 1.1e-01 / 1.4e-02 |
| Z6_base | PASS | 0 | 4,2 / 6 | 0.065 | -1.9e+01 +- 7.1e+01 (-0.27) | -1.7e+00 +- 6.0e+00 (-0.28) | 1.2 | 2.1e+02 / 1.8e+01 |
| Z6_v | TENSION | 0 | 5,1 / 10 | 0.049 | -4.0e+01 +- 2.1e+01 (-1.89) | -4.0e+00 +- 2.3e+00 (-1.74) | 26 | 6.3e+01 / 7.0e+00 |

A5_d (K = 0) and Z6_v (K = 0) are TENSIONs: the central tail flags them (pulls -6.1 and X2 = 26) but the competitive richer tails do not. A5_d is among the 255 coefficients the engine reproduced from the
archive's exact series (its validation (c)), and the validation_d and pilot5 values of Z6_v agree within 1.8
sigma, so these are tail-model artefacts of K = 0 series; they set the baseline below which the two moments
are not tested (their injection thresholds below are for a robust OFFSET only).

**What the comparison resolves.** The direct values are good to ~1e-14 relative, but the finite part is a
small remainder of large divergent terms: at eps ~ 1e-3 the absolute direct errors are 1.4e-5 (A7_v),
1.2e-5 (Z6_v), 4e-7 (A7), 3e-7 (Z6), 1.7e-7 at 0.00222 (Q8), and the omitted eps^(K+1) l^J tail (J up to 7) must be fitted
over one decade of eps. Measured on complete series (table above, injections into the engine's c00, c01):
* 3-4 kinks (complete validation series): all PASS; 3-sigma sizes from 1e-11 (A3, K = 2) and 5e-10 (Q4,
  K = 2) through 7e-8 (Z4, K = 1) to 0.1-0.25 for Q4_vv, Q4_vd (K = 1, 4 dof), i.e. 1e-13..3e-4 relative;
* 5 kinks, complete with K = 1 (A5, A5_v): robust OFFSET from 5e-5 (c00) and 5e-6 (c01), i.e. 3e-7..5e-9
  relative; with K = 0 (validation_c alone: A5, A5_v; and A5_d) 3e-5..6e-4 relative, and for A5_d the
  baseline is already a TENSION (tail-model dependent);
* 6 kinks: Q6 (K = 1) 0.11 (c00, 5e-4 rel) and 7e-3 (c01, 2e-5 rel), limited by the errors of the
  validation run's eps^-1, eps^-2 coefficients; Z6 and Z6_v (K = 0): c00 at 3 and 5e-2 relative, c01 at
  8e-2 and 1e-1 relative, i.e. a **gross-error screen**;
* 7 and 8 kinks (A7, A7_v, Q8) and A5_vd, A5_vv, Q6_v, Q6_d, EA5, EA5_v, EQ6: **no complete engine series
  exists, so nothing is tested.** Even an ideal complete K = 1 series would give 3-sigma design sizes of
  order 0.2-6 for c01 of A7, A7_v and Q8 (3e-5..4e-4 relative); measured complete-series sizes differ from
  such design estimates by factors of 0.01-100 (tail selection, prior errors, the joint X2), so for 7 and 8
  kinks the comparison could at best **screen for gross errors (roughly 1e-3..1e-2 relative)**.
With the engine's present output format (production = pilot5 format) every 5-8 kink spec moment is
INCONCLUSIVE or UNTESTABLE. The phase-1 statements "decisive" and "1e-4..1e-2 for n = 5..7" are withdrawn.

**What the engine would have to deliver** for this backstop to bite on the 5-8 kink inputs:
(a) per moment the complete series from p_min to K >= 1, every log power including structural zeros and
c00, even where the framework needs only [eps^0 l^1] (A7, A7_v, Q8, Z6_v, Q6_d, A5_d, A5_vd);
(b) the negative-power coefficients to high absolute precision (they are lower-dimensional pole terms; the
direct data constrain an eps^-1 coefficient to ~1e-11 at eps = 1e-3, while the Q6 validation run quotes its
eps^-1 l^0 to 2.7e-6: the GLS must absorb that as a prior, which limits the Q6 test to 5e-4 relative, and
with those coefficients held exact the data reject the run's values, MODEL-FAIL); (c) optionally
per-coefficient replicate values for the covariance. Then run
`python3 compare_engine.py FINAL.json [VALIDATION.json ...] --merge --offset-fit` (seconds) and
`python3 calibrate_injections.py` after adding FINAL.json to its CONFIGS.

### Finite-part extraction from quad data (`results/fpe_atoms.json`, `results/fpe_inputs.json`)
100 cutoffs in [1e-9, 1e-4], binary128 data (controls at 1.3N agree to 2.6e-28), weighted fits over several
(log degree, eps powers, window) variants. "determined" = variant spread small (the deliverable's own
criterion):

| input | FPE central value | reference | difference | variant spread | determined |
|---|---|---|---|---|---|
| C3_0 = 3 - 2 zeta(2) | -0.2898681336964528766 | -0.2898681336964528729 | 4e-18 | | yes |
| C3_1 = 5 | 4.9999999999999999996 | 5 | 4e-19 | | yes |
| a = -4 zeta(2) | -6.579736267392910006 | -6.579736267392905746 | 4e-15 | 1.5e-9 | yes |
| c = -16 | -15.99999999999999937 | -16 | 6e-16 | 1.0e-9 | yes |
| p | -9.24944388988 | -9.24944390029 | 1e-8 | 1.3e-3 | **no** |
| A | -5.89349520557 | -5.89349518475 | 2e-8 | 2.6e-3 | **no** |
| f | -20.7832823206 | -20.7832823752 | 5e-8 | 1.8e-3 | **no** |
| E | -21.6346 | -21.6639 | 0.029 | 7e4 | **no** (not reproduced) |
| alpha, q, L | within 7e-3..3e-2 of the references | | | 6e3..5e4 | no (chance level) |
| V, beta, gamma, M, Q | not determined | | | >= 1e12 | no |

So this route **independently reproduces only a and c** (to 1e-15), including the endpoint-source atom
K2_0_E and the finite-eps normalization K4 = Q4 - Q2 Z2 that enter c. The p, A, f central values lie within
1e-8..5e-8 of the closed forms, but the fit's own variant spread (1e-3) does not allow claiming them; E is
not reproduced. The new 3- and 4-kink inputs cannot be extracted this way at 28 digits (log degrees 5–7 make
the eps^k l^j fit far too ill-conditioned). They, and all 5–8 kink inputs, are covered only by the engine
comparison above, within the resolution stated there.

## Compute
symmetry amdq (whole AMD EPYC 7543 nodes, 64 cores). Phase 1: jobs 568509 (main, 360 runs), 568510 (n=8),
568515 (RQMC), 568511 (RQMC first pass + exact_refs), 568516 (eps 1/500, 1/1000), 568517 (n=8 at 1/200,
1/500; cancelled after 3 runs and split by kind into 568561/568562 to finish faster), 568539 (quad data),
568546/568558/568559/568560 (fits; 568546 = first unweighted attempt, superseded; 568558 failed on a
numerically singular variant, fixed; 568560 = final), 568715-568717 (dense grid, Q8 dense). 568502-4 failed
at start (module init vs `set -u`, fixed). About 4 node-hours (~250 core-hours, sacct CPUTimeRAW).
Phase 2: jobs 569084-569086 (Q8 at 10 cutoffs, groups q8xa/b/c; all COMPLETED, exit 0), about 2.1
node-hours (sacct CPUTimeRAW 482880 s = 134 core-hours of whole-node allocation; wall 40-44 min per node).
Results and logs are mirrored under <SCRATCH>/sri_c6c7/direct on symmetry.
Nothing ran on the Mac beyond second-scale tests and the local analysis scripts (the GLS comparison and its
calibration take seconds; `run_analysis.sh` about two minutes).

## Production comparison (assembly phase, 2026-10-03)

The engine's production series were compared with this tool by `../assembly/direct_check.py`, which calls
`src/compare_engine.py` and was not changed. Outputs are in `../assembly/out/direct_*`, the summary in
`../RESULTS.md` section (iv).

* **Production series as delivered:** 6 PASS, 30 INCONCLUSIVE, 10 UNTESTABLE, as predicted above.
* **Completed series:** production, coefficient by coefficient completed by the assembly-phase engine runs
  `engine/runs/poles1` (all negative powers) and `engine/runs/kplus1` (eps^1 of the K = 0 moments, except A7,
  A7_v, Q8, Q6_E), then by the validation runs.
  * Result: 44 PASS, 1 TENSION (A5_vv), 2 OFFSET (EA3_vd, EZ4_base).
  * The earlier K = 0 TENSIONs of A5_d and Z6_v disappear with K = 1, as anticipated.
  * EA5_base, EA5_v and EQ6_base PASS with complete series.
  * A7, A7_v and Q8 are testable for c01 (K = 0), as gross-error screens only.
* **EZ4_base:** with the engine's convergence re-check `engine/runs/conv1` it PASSES at 5e-7. The OFFSET came from
  a production nuisance coefficient, Z4_E[eps^-1 l^0], which is 9e-10 off (4 replicate sigma). With a tight
  prior, the GLS pushed that misfit into c00 and c01.
* **EA3_vd and A5_vv:** the flags change with eps_max (0.011, 0.016, 0.051) and with the tail variant. The
  OFFSET of EA3_vd stays with the conv1 values, so it is a tail-model effect, not an engine error.

## Open items
* The 7- and 8-kink moments (A7, A7_v, Q8) still lack eps^1 engine coefficients (~400 core-h). With them the
  comparison would still only screen at the 1e-3..1e-2 level.
* EA5_base, EA5_v and EQ6_base had raw OFFSETs on partial series, unstable under changes of fit window and of the
  negative-power structure (gate review 2026-10-03). With the complete series of the assembly phase they PASS.
* The PASS rule is asymmetric: a competitive tail variant may flag while the central one does not (A5_v, Q4_d,
  Q6_base; below the quoted resolutions). A symmetric rule, giving TENSION whenever any competitive variant
  flags, would be the stricter choice for the production comparison.
* Error estimates of the direct table are convergence diagnostics (change between Gauss orders plus a
  rounding floor), not interval bounds; they are conservative by a factor 4-30 (chi2/dof of adequate fits).
* Only the first eta-derivative source moments were computed (as the spec requires); second source
  derivatives are not covered.
* For n = 7, 8 the derivative/source conventions rest on the archive exact-expression matches and the RQMC
  (which shares the insertion algebra), not on a fully independent unexpanded-kernel check.
* The archive's per-moment series files were not used for any comparison; only its finite-cutoff records.
