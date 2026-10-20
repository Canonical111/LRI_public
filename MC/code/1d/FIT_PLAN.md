# Fitting protocol v2 for Δ_ε from the two-point campaign (and, later, the scan)

Status: revision 6 (scan addendum §6 revised after review round 5 and inspection round 3; UNREVIEWED — review rounds exhausted) (claudex-loop, host Claude Code, reviewer Codex gpt-6-astra/xhigh); revision 2
addresses FIT-001 … FIT-006 (degree ceiling, cross-check definition and gates, paired bootstrap for the comparison,
minimum model coverage for σ_sys, residual-structure test); revision 3 addresses FIT-007 … FIT-009 (joint validity mask
and fixed combination set for the paired comparison, per-draw aggregate uncertainty, calibrated residual gate); revision 4
addresses FIT-009 (residual-gate calibration by full refits of amplitudes and nonlinear parameters) and FIT-010 (bootstrap
validity by existence/convergence only; χ² gates on central extrapolations alone). Building is
authorised by the user's request ("try to solve the fitting problem"); no new simulations are involved. Data:
`$CAMP/merged_b{2048,4096,8192}_20260916_043015/` on Expanse (100 groups × 6 observables with 6×6 covariances, plus the
block files for the bootstrap; copies of the summaries in `lri_cluster/expanse_final/merged_b4096/`).

## 1. The problem, quantified (recon on the finished fits, `expanse_final/fits_20260916_043015/`)

The pre-registered ansatz (EXPANSE_PLAN.md §4): Q_N(β) = F_Q(x) + r^{−ω} G_Q(x), x = 100(β − β_c) r^{1−Δ_ε}, r = N/1024,
F_Q a polynomial of degree 3, G_Q quadratic, fitted to Y, Y′, Y″, U, U′, U″ at 5 β × 8 sizes with full covariance.

| Δ_σ | degree of F_Q | χ²/dof (full window, Nmin 4096) | Δ_ε | ω | dominant pulls |
|---|---|---|---|---|---|
| 0.0625 | 3 | 11.40 | 0.5905 | 0.41 | Y″ 4.4σ, U″ 2.3σ, Y′ 2.1σ (mean |pull|) |
| 0.0625 | 4 | 2.06 | 0.5911 | 0.39 | all ≤ 0.9σ mean; a few 1.8σ |
| 0.0625 | 5 | 1.08 | 0.5900 | 0.42 | random |
| 0.1 | 3 | 450 | 0.5502 | 0.15 | U″ 21σ, Y″ 18σ, everything ≥ 9σ |
| 0.1 | 4 | 60.8 | 0.5430 | 0.23 | U″ 4.5σ, Y″ 5.6σ; N=4096 and 524288 worst |
| 0.1 | 5 | 3.18 | 0.5335 | 0.36 | 1.0–1.6σ mean; N=4096 carries 215 of 480 χ²; U″ up to 3.2σ at N=524288 |

Diagnosis. (i) The polynomial order of the thermal scaling function is too low for data whose second derivatives are
known to ≈10⁻³: at Δ_σ = 1/16 order 5 suffices and Δ_ε is insensitive to the order (0.5900–0.5911); at Δ_σ = 0.1 the
scaling functions are far more curved over the same x-range (larger 1 − Δ_ε, Binder cumulant closer to its inflection),
order 5 is still inadequate, and Δ_ε drifts with the order. (ii) At Δ_σ = 0.1 the smallest size (4096) contributes the
largest share of χ² even at order 5, i.e. the single-power correction r^{−ω} with quadratic G is also inadequate there.
(iii) The size-doubling estimator, which assumes no scaling form, gives Δ_ε,eff = 0.527–0.534 (Δ_σ = 0.1) and
0.586–0.594 (Δ_σ = 1/16) at the three largest pairs, still drifting at the 0.003 level: corrections are visible.

## 2. Goal and acceptance criteria

Goal: a quotation rule for Δ_ε that (a) is fixed before the extended fits are run, (b) selects the thermal polynomial
order and the correction sector by data-independent statistical rules rather than by the Δ_ε value, (c) yields a fit that
describes the data (χ²/dof ≤ 1.5, unstructured pulls), and (d) reports a model systematic honestly.

Acceptance (evaluated by the new `select_model.py`, all caps and rules fixed here):
1. For each Δ_σ the selection rule (§3.3) returns at least one *quotable* fit: χ²/dof ≤ 1.5, no boundary/rank flags,
   bootstrap valid ≥ 90 % (≥ 270 of 300), mean observable-normalised |pull| ≤ 1.2 for each of the six observables, the
   residual-structure test of §3.7 passed, and the order-stability check of §3.3 resolved.
2. Model systematic: σ_sys (§3.4) is *estimable* only if the quotable set contains ≥ 4 fits covering ≥ 2 values of Nmin
   and ≥ 2 correction variants (windows may coincide). Then σ_sys ≤ 0.0015 at Δ_σ = 0.0625 and ≤ 0.004 at Δ_σ = 0.1 is
   required. If the coverage is absent, the result is reported as "conditional on model; σ_sys unresolved" and is NOT
   accepted; if the cap is exceeded, as "model-limited" with the range. A single survivor never yields σ_sys = 0.
3. Cross-check (§3.5): evaluable only if ≥ 2 eligible (degree, window) crossing series exist; then the paired difference
   Δ_ε(quoted) − Δ_ε∞ must lie within 2σ of the paired-bootstrap distribution of that difference (§3.6), with σ enlarged in
   quadrature by the half-spread of Δ_ε∞ over eligible series. Not evaluable ⇒ not accepted (reported as "cross-check
   unavailable").
4. Reblocking: σ_stat of the quoted configuration at block 2048 and 8192 within 30 % of the block-4096 value.
5. Every number is reproducible from a manifest listing command lines and input SHA-256s.

Non-goals: new simulations; changing the observables; tuning anything on Δ_ε. The pre-registered v1 result stays in the
log as INCONCLUSIVE; v2 is reported as a second, explicitly post-hoc protocol whose rules were fixed before its fits ran.

## 3. Approach

### 3.1 Extend the fitter (fit_fss.py; backwards compatible, defaults unchanged)
- `--degree` up to 8 (now 1–5); degree 8 is admitted only as the stability comparator for d* = 7 (§3.3), never as a
  quotable degree. `--correction-degree` up to 3 (now).
- `--field-order K` (default 1): nonlinear thermal scaling field τ = (β − β_c)[1 + a₁(β − β_c) + … + a_{K−1}(β − β_c)^{K−1}],
  x = 100 τ r^{1−Δ_ε}; a₁… are additional NONLINEAR parameters (N-independent, bounded |a_k| ≤ 50), with the chain rule
  applied to the derivative rows (dx/dβ and d²x/dβ² now β-dependent). Motivation: on the lattice the thermal scaling field
  is an analytic function of β; if part of the curvature is analytic in β rather than intrinsic to F_Q, a low-order τ
  removes it with 1–2 parameters instead of 2 polynomial orders in each of F_Y, F_U.
- `--drop-second`: exclude the Q″ rows (diagnostic only; not part of the quotable family, because it discards the
  measurements that constrain the exponent most).
- Output additions: per-observable mean *observable-normalised* |pull| (residual / own standard error; used for the
  pull and residual-structure gates), per-size χ² (whitened, used for χ²), the ordered pull matrix (sizes × β × 6), the
  whitened residual vector, `field_coefficients`, `nlinear`, and the exact selection metadata (degree, field order,
  window, variant, Nmin, block).
- `--bootstrap-schedule SEED`: block resampling indices derived deterministically from (SEED, s, N, β, replica, draw)
  so that different estimators can be evaluated on identical resamples (§3.6).

### 3.2 The family F (fixed now)
Window ∈ {full, c3} × variant ∈ {leading, background, second} × Nmin ∈ {4096, 8192, 16384} × field order ∈ {1, 2} ×
degree d ∈ {3, 4, 5, 6, 7} × correction degree 2. 180 fits per Δ_σ (+ degree-8 comparators where d* = 7); bootstrap
300 for those that pass the degree selection (below), so ≈ 40 bootstrapped fits per Δ_σ.

### 3.3 Degree selection rule (data-driven, blind to Δ_ε)
For each (window, variant, Nmin, field order) run degrees 3…7 without bootstrap and pick d* by an F-test ladder:
increase d while the reduction of χ² from d to d+1 is significant at p < 0.01 (F-test on the two added amplitudes,
using the fits' dof), stop at the first non-significant step; d* is the last significant degree. A configuration is
*quotable* if the fit at d* has χ²/dof ≤ 1.5, no flags, mean |pull| ≤ 1.2 per observable, and a valid bootstrap. Order-stability
check: the fit at d*+1 (the *comparator*; for d* = 7 this is degree 8, run only for this purpose and never quotable) must
exist, converge and be unflagged, and |Δ_ε(d*) − Δ_ε(d*+1)| ≤ 3σ_stat(d*); otherwise the configuration is
"order-unstable"/"stability-unresolved" and not quotable (FIT-001). This guards against selecting d* while Δ_ε still
drifts with the order, as seen at Δ_σ = 0.1.

### 3.4 Quotation and systematics
Quoted value: the quotable fit with the fewest nonlinear+linear parameters among those at the smallest Nmin (ties: full
window before c3; leading before background before second; field order 1 before 2). σ_stat: bootstrap 16–84 %
half-range. σ_sys: half the range of Δ_ε over ALL quotable fits of F, defined only when the coverage of criterion 2 holds
(≥ 4 quotable fits, ≥ 2 Nmin values, ≥ 2 variants); otherwise "unresolved" (FIT-005). Both reported; caps in §2.

### 3.5 Model-independent cross-check (fully specified; FIT-002, FIT-003)
Series: for each combination (local degree ∈ {4, 5, 6}) × (window ∈ {full, c3}) of `quotients.py`, take the **U-crossings**
(β_× where U_N = U_2N) of the four pairs 32768–65536, 65536–131072, 131072–262144, 262144–524288 and, at each, the two
effective exponents Δ_ε,eff^U (from the U slopes) and Δ_ε,eff^Y (from the Y slopes). Eligibility of a combination: local
χ²/dof ≤ 2 at all five sizes involved; joint validity ≥ 90 % over exactly these four crossings (draws in which all four
U-crossings and both slopes exist), computed from the saved bootstrap samples (`*.samples.npz`, as forecast_centres.py
does), with the 8×8 covariance of the eight effective exponents from the same draws.
Extrapolation per eligible combination: fit the eight values jointly to Δ_ε,eff^Q(N) = Δ_ε∞ + c_Q N^{−ω′} (Q = U, Y;
shared Δ_ε∞ and ω′, two amplitudes; 4 parameters, 4 dof) by generalised least squares with the 8×8 covariance; ω′ on a
grid [0.2, 2] step 0.01 with the two linear amplitudes and Δ_ε∞ solved exactly at each ω′. Gates on the **central**
extrapolation: χ²/dof ≤ 2; ω′ not within 0.02 of either bound; the same fit repeated on each valid joint bootstrap draw
(ω′ re-selected per draw, no χ² cutoff on draws, FIT-010) gives the error of Δ_ε∞ and must have a finite unique grid
minimum in ≥ 90 % of the valid draws. A combination failing any gate is ineligible.
Aggregation: the *eligible set* E is frozen from the central fits (eligibility evaluated on the central estimates as above).
Δ_ε∞ (central) = median over E of the central extrapolations. Minimum coverage: |E| ≥ 2, else criterion 3 is "not
evaluable". The statistical uncertainty of the aggregate and its use in criterion 3 are defined in §3.6 (per-draw median
over the fixed set E on common valid draws; FIT-008); the model spread of the cross-check is the half-range of the central
extrapolations over E and is added separately.

### 3.6 Paired comparison (FIT-004, FIT-007, FIT-008, FIT-010)
Both estimators consume the same blocks. A deterministic bootstrap schedule (seed fixed in the manifest) assigns to draw
k and to each (group, replica) the same block indices in `fit_fss.py` and in `quotients.py` (both gain
`--bootstrap-schedule SEED`); the quoted global fit and every member of the fixed eligible set E are recomputed on the same
300 requested draws. Validity is defined per draw and jointly, and **only by existence/convergence conditions, never by a
goodness-of-fit cutoff** (FIT-010: bootstrap replicas fluctuate around the observed estimates including their residual, so
a χ² cutoff on draws would discard ordinary sampling fluctuations of a sound fit; the χ²/dof ≤ 2 gates of §3.5 apply to
the central extrapolations alone). Draw k is *common-valid* iff the quoted global fit on draw k converged (optimizer
success, full profile-Hessian rank, finite parameters, none of the declared boundary flags) AND, for every combination in
E, all four U-crossings and both slopes exist and are finite on draw k AND the per-draw extrapolation has a finite,
unique grid minimum in ω′ (the ω′-off-the-bounds condition is a central gate only). Missing roots (NaN), non-finite
values or declared flags invalidate the draw for everyone; the estimator never changes composition between draws. The
common-valid fraction is measured against the 300 requested draws and must be ≥ 270/300, otherwise criterion 3 is
CROSS-CHECK UNAVAILABLE.
On the common-valid draws: Δ_ε∞,k = median over E of the per-combination extrapolations of draw k (E fixed, FIT-007);
σ_∞ = half the 16–84 % range of Δ_ε∞,k (FIT-008); D_k = Δ_ε(quoted)_k − Δ_ε∞,k; σ_D = half the 16–84 % range of D_k,
enlarged in quadrature by the half-range of the central extrapolations over E (model spread). Criterion 3:
|Δ_ε(quoted, central) − Δ_ε∞(central)| ≤ 2 σ_D. Existing independent draws are never paired by array index.

### 3.7 Residual-structure test (FIT-006, FIT-009)
Evaluated only for candidate fits that already pass the other quotability conditions of §3.4 (χ²/dof, flags, bootstrap
validity, mean |pull|), so that the full refit below is affordable.
Statistics, for a candidate fit with pull matrix p[N, β, Q] (observable-normalised residuals; sizes ascending, β
ascending): for each observable Q, (a) the Wald–Wolfowitz runs statistic of the sign sequence ordered by (N, β), expressed
as its two-sided p-value p_runs(Q) under the exchangeable null; (b) the pooled lag-1 autocorrelation along β within size,
ρ₁(Q) = Σ_N Σ_{j=1}^{n_β−1} p[N,j,Q] p[N,j+1,Q] / Σ_N Σ_{j=1}^{n_β} p[N,j,Q]². Combined statistic T = min_Q p_runs(Q) paired
with R = max_Q |ρ₁(Q)|.
Calibration under the fitted-model null (fitted residuals have covariance I − P_[A,J] to first order, where A is the
linear design and J the tangent of the nonlinear parameters, so independent-sequence thresholds do not apply): for the
candidate configuration, generate 500 pseudo-datasets by drawing whitened noise ~ N(0, I) around the fitted central
prediction, colouring it with each point's Cholesky factor, and **refitting the complete model on each pseudo-dataset —
profiled linear amplitudes AND all nonlinear parameters (k, Δ_ε, ω, a_j), warm-started from the central solution with
the same bounds** (FIT-009; no fixed-parameter approximation). Pseudo-datasets whose refit does not converge are counted;
if more than 2 % of the 500 fail, the gate is "not evaluable" and the fit is not quotable. (T, R) is computed for every
converged pseudo-dataset. Gate: the observed (T, R) is rejected if T is below the 1 % quantile of the null T distribution
OR R is above the 99 % quantile of the null R distribution; because both quantiles are taken from the fully refitted null,
the predeclared combined false-exclusion rate is ≤ 2 % per candidate fit (two one-sided 1 % tests), up to the Monte Carlo
error of 500 replicates (quantile error ≈ 0.4 % absolute). A rejected fit is not quotable ("structured residuals").
Small-sample configurations (c3, Nmin = 16384: 18 pulls per observable) are covered by the same calibrated procedure, not
by asymptotic thresholds. Whitened components are not used for this test because they mix correlated observables. Cost:
≈ 0.05–0.3 s per warm-started refit → ≤ 150 s per candidate; with ≤ 60 candidates per Δ_σ this is ≤ 3 core-hours, run in
parallel on the analysis node (A4 updated).

### 3.8 Reblocking, manifest, report
Repeat the quoted configuration on merged_b2048 and merged_b8192 (criterion 4). `run_fits_v2.sh` writes a manifest;
`select_model.py` writes `FIT_V2_RESULTS.md` (per Δ_σ: the selection table d* per configuration with comparator
results, the quotable set with pull/runs statistics, quoted value, σ_stat, σ_sys or its "unresolved" status, the
cross-check series and paired-difference statistics, decision: ACCEPTED / MODEL-LIMITED / CONDITIONAL / CROSS-CHECK
UNAVAILABLE) and `fit_v2.json`.

## 4. Assumptions and risks
- A1: the 100-group merged summaries and block files of the two-point campaign are final (completion check PASS,
  2026-09-16). Source: EXPANSE_PLAN-REVIEW-LOG.md.
- A2: degree ≤ 7 with 5 temperatures per size is identifiable: 5 β × 8–10 sizes × 6 observables = 240–300 data versus
  2 × (8 + 3) + 3 + 1 = 26 parameters at d = 7 with field order 2; the design is rank-checked (existing flag) and the
  bootstrap detects instability. Risk: near-collinearity at high d → excluded by the flags.
- A3: at Δ_σ = 0.1 even the extended family may not reach χ²/dof ≤ 1.5 with Nmin = 4096 (the small-N correction sector).
  Then Nmin = 8192/16384 configurations decide; if none is quotable, criterion 1 fails and the point is reported as
  model-limited with the range of near-admissible values — an honest outcome, not a failure of the protocol.
- A4: compute: 360 fits + ≈ 80 bootstrapped fits ≈ 10 core-hours, plus ≤ 3 core-hours per Δ_σ for the fully refitted
  residual-gate calibration (§3.7); run on one exclusive Expanse compute node (normal QOS, currently 20 of my 22 allowed
  jobs running) or the debug partition in two 30-minute chunks; the summaries are 1 MB.

## 5. Verification
0. Unit checks of the new gates on synthetic data: (a) the calibrated residual gate rejects a fit whose residuals carry a
   pure sign-alternating or monotone pattern of the same |pull| distribution as random residuals, and accepts ≥ 97 % of
   independently generated, fully refitted null datasets (the gate's own calibration uses full refits, so this is a
   self-consistency check of the rejection rate, FIT-009); (a′) the common-valid mask never depends on a per-draw χ²
   (FIT-010: a synthetic sound fit with central χ²/dof ≈ 1 keeps ≥ 90 % common-valid draws); (b) the paired schedule gives identical block
   indices in fit_fss.py and quotients.py for the same (seed, group, replica, draw), and a draw invalid for one member of
   E is excluded from the common-valid set of all; (c) the crossing extrapolation
   recovers a synthetic Δ_ε∞, c_U, c_Y, ω′ within its bootstrap error and rejects an ω′-at-bound case.
1. Unit check of the nonlinear field: `fit_fss.py --field-order 2` with a₁ forced to 0 reproduces the field-order-1
   χ² and Δ_ε to 1e-8 (test added to tests/test_analysis.py); synthetic data generated with a known (Δ_ε, ω, a₁)
   recovered within 2e-6 / 2e-5 / 1e-3.
2. `run_fits_v2.sh $CAMP` on Expanse → `fits_v2_<T>/FIT_V2_RESULTS.md`; expected: at Δ_σ = 0.0625 a quotable fit with
   χ²/dof ≈ 1.1 and Δ_ε within 0.5900–0.5911 (consistency with §1); at Δ_σ = 0.1 either a quotable fit or the
   model-limited report with its range.
3. Criteria 1–5 evaluated automatically; the decision line of FIT_V2_RESULTS.md is the deliverable.

## 6. Application to the Δ_σ scan (addendum, revision 5; rules fixed before any scan fit runs)
- Scope: the same protocol (§3), unchanged, is applied to every scan point (SCAN_PLAN.md: Δ_σ = k/80, k = 1…19, and
  0.1727335) once its stage B is complete (completion_check PASS on the point's registry, all ten pairs active).
- σ_sys cap by Δ_σ (criterion 2), a pre-registered convention extending the two anchors of §2: cap(Δ_σ) = 0.0015 for
  Δ_σ ≤ 1/16; linear between the anchors (1/16, 0.0015) and (0.1, 0.004); 0.04·Δ_σ for Δ_σ > 0.1 (e.g. 0.0085 at 0.2125,
  0.0095 at 0.2375). Rationale: the tolerated model spread should grow with the size of the finite-size corrections and of
  the statistical errors, both of which increase with Δ_σ; the values are a convention, stated as such in the report.
  Implemented as `select_model.sys_cap()`; the two anchors keep their exact values.
- Per-point pipeline (`run_point_v2.sh`), in two stages so that split-machine points are handled explicitly (FIT-011,
  FITV2-015): **snapshot** (per host, tag T): `completion_check.py --campaigns <campaigns hosted here> --evidence
  completion_T_<host>.json` verifies the raw chains against the manifest and records, per task, the SHA-256 and size of
  DONE.json and samples.bin plus the campaign-manifest hash; then analyze.py at blocks 2048/4096/8192 into
  `<campaign>_an_b<b>_T`; every produced summary and block archive is hashed into `analysis_v2_T.manifest` together with
  the registry and the implementation files. **finalize** (on the gathering host): for every active campaign of the
  registry a PASS evidence file for tag T must exist (transferred with the `_an_b*_T` directories from the other hosts),
  the local campaign manifest must hash-match the one checked on the source host, and the evidence must cover exactly
  the registry's expected pairs; then merge_summaries.py (coverage all) → window_filter.py (middle three temperatures) →
  run_fits_v2.sh, with `--analysis-manifest` linking the analysis manifest into the fit provenance (FITV2-016). `all` =
  both stages on one host (the 18 Expanse points). No stage re-analyses or requires remote raw chains.
- Prerequisite gate (FITV2-013): the equilibration criterion of the v1 acceptance (accept.py criterion 2: hot/cold
  agreement ≤ 3σ, half-chain drift ≤ 4σ, τ < block/20 per group, ≤ 2 % replicas with half-chain |z| > 3) is factored into
  `equilibration.py` and evaluated by select_model.py on the point's block-4096 summary; a failing gate yields
  EQUILIBRATION FAILED and never ACCEPTED. The result is persisted in fit_v2.json.
- Input structure gate (FITV2-014): validate_reblock/window_consistency require unique coordinates, exactly five
  temperatures per (s, N) in the full window and exactly their middle three in c3, in the block-4096 input and in both
  reblocking inputs; malformed windows make the run NON-PRODUCTION.
- Scan coordinates are kept at their declared precision (7 decimals, e.g. 0.1727335) for identifiers and for the cap
  (FITV2-018).
- Scheduling on Expanse (`submit_scan_v2.py`, FITV2-017): one analysis job per point with
  `--dependency=afterany:<all stage-B job ids of the point>,singleton` and job names `v2s_<k mod W>` (W = 6), so at most W
  analysis jobs run concurrently regardless of node packing. Dependencies do NOT reduce the submitted count: the helper
  checks before submitting that (my submitted jobs + new) ≤ 54 and that the worst-case concurrency (queued jobs that are
  not dependencies of the new jobs + the final dependency wave, which is the largest set of dependency jobs that can run
  while analysis jobs run + W) ≤ 22, and refuses otherwise. Nothing running is ever cancelled.
- Reporting: `scan_v2_report.py` enumerates the DECLARED 20-point grid (FIT-012), looks up each point's directory and
  newest fits_v2 result, and requires the result's (Δ_σ, s) to match the directory's coordinate within 5e-8 (FIT-013; a
  mismatch is reported as INPUT MISMATCH, a missing directory or result as MISSING INPUT / PENDING). `scan/FIT_V2_SCAN.md`
  lists per point the decision, Δ_ε ± σ_stat ± σ_sys, the quotable count, the cross-check and equilibration status and the
  published value where one exists; no point is compared with the ε-expansion before its own decision is recorded; nothing
  is dropped.
- Verification (added to §5): (a) `sys_cap()` reproduces the two anchors exactly and is monotone on the grid (test);
  (b) `run_point_v2.sh` on the two-point campaign root reproduces the production decisions and quoted values of
  fits_v2_20260916_111300 from a fresh analysis snapshot (end-to-end check of the driver).
