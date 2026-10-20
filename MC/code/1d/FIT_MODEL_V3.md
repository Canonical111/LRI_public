# Fitting model v3 for Δ_ε(Δ_σ): what the scan taught us and the numerics needed to finish

Status: revision 14 — UNREVIEWED, prepared for review round 11 (round 10 on revision 13 returned REVISE with V3-032/033: noiseless
vs noisy expectation for the null-space fixture, versioned synthetic generators and source snapshots; round 9 on revision 12: V3-028…031; round 8 on revision 11: V3-026/027; the N0 test
of §5.0 is the joint polynomial test (j), amendment record at the end of §5.0; all seven earlier plan-review rounds used; revision 8 implemented the single round-7
finding V3-025; revisions 9 and 10 are post-build clarifications from the two code inspections — §5.0 independence of the
N0 validation sets and the data-null gross band (FITV3-006), §8 item 4 aligned with it (R2-009); the user authorised N0 and
N1 to start after the reviews). Revision 6 implemented V3-022/023; revision 7 addressed V3-024 (calibration: statistical smoothness exclusions are
distinguished from numerical failures, a minimum number of conclusive replicates replaces the 5 % cap, and the outcome
probabilities are specified conditionally and unconditionally). History: reviewer Codex gpt-6-astra/xhigh; revision 2
addressed V3-001 … V3-008; revision 3 V3-009 … V3-016 and added the estimator-consistency evidence (§2.5) and the
diagnostic run N0; revision 4 V3-018/019; revision 5 addresses V3-017 (N0 statistic with the full residual covariance,
calibrated under the correlated null), V3-020 (polynomial-referenced derivative check instead of a Richardson "bound";
unresolved truncation ⇒ INCONCLUSIVE) and V3-021 (deduplication test expectations). This plan is a PLAN ONLY: it does not authorise re-analysis code changes
or new simulations; both need the user's go after review.
Data: the completed 20-point scan (SCAN_PLAN.md grid, stage A 2^10–2^16 + stage B 2^17–2^19, 5 temperatures × 8 replicas
× 2·10⁶ sweeps per size), analysed with the v2 protocol (FIT_PLAN.md); table scanA_exp/scan_v2/FIT_V2_SCAN.md, per-point
records scanA_exp/scan_v2/ds*/fits_v2_*/ (Expanse: $C/scan/ds*/fits_v2_*/).

## 1. Goal
Finish the determination of Δ_ε on the 20-point grid: at every point a value with σ_stat and σ_sys under a decision label
from the complete table of §4.6 — never a silent gap — using (i) a revised fitting model that keeps the v2 gates but fixes
the design flaws the scan exposed, and (ii) the smallest set of additional simulations that makes the model
well-determined where the present data cannot be.

Acceptance criteria for this plan's execution (measured by the v3 evaluator on the union of old and new data):
1. Δ_σ ∈ [0.0625, 0.1875] (10 grid points incl. 0.1727335): ACCEPTED or ACCEPTED (σ_sys-dominated) at every point (§4.6),
   with a passing cross-check on ≥ 2 eligible crossing series.
2. Δ_σ ≥ 0.2 (4 points) and Δ_σ ≤ 0.05 (4 points): one of the labelled outcomes of §4.6 with a quoted number and its
   uncertainty; MODEL-LIMITED and EXTRAPOLATION UNAVAILABLE are allowed outcomes there (regime physics, §2.3), never a gap.
3. Reproducibility from manifests as in v2; the two anchor results of the two-point campaign (1/16, 0.1) are re-derived by
   the v3 evaluator in its legacy-window mode and agree with v2 within 1σ_stat (their labels under the v3 rule are
   pre-stated in §4.3).

## 2. What the numerics showed (recon, 2026-09-18; all numbers from the v2 production records)

### 2.1 Three regimes
| regime | points | v2 outcome | least-bad fit |
|---|---|---|---|
| A: Δ_σ ≤ 0.05 | 4 | 31–36 quotable fits each, σ_sys 0.0022–0.0133 > cap 0.0015 | χ²/dof 0.8–1.0, d* 3–6; spread driven by the correction variant ('second' r^{−2ω}) and window; fitted ω 0.09–0.6, poorly determined |
| B: 0.0625–0.1375 | 7 | 3 ACCEPTED (0.075, 0.1, 0.1125); 0.0625, 0.125, 0.1375 cross-check unavailable / single fit; 0.0875, 0.125 equilibration gate | χ²/dof 0.8–1.1 |
| C: Δ_σ ≥ 0.15 | 9 | MODEL-LIMITED (no quotable fit); 0.175 one fit | always c3/second/Nmin16384/K2 at the ceiling d = 7; χ²/dof 0.99 (0.15) → 2.2 (0.2) → 4–22 (≥ 0.2125); ω 0.26 → 0.005 |

### 2.2 The dominant design flaw: temperature windows too wide at large N
Stage B simulated 5 temperatures with half-width h(N) = 0.005 (N/1024)^{−0.35}. The FSS scaling variable is
x = 100 (β − β_c) (N/1024)^{1−Δ_ε}, so the x half-range covered at size N grows like N^{0.65−Δ_ε}:
- Δ_σ = 0.0125 (Δ_ε 0.79): x range 0.88 → 0.39 from N = 4096 to 2^19 (shrinks; degree 3–4 suffices, d* = 3–4 observed).
- Δ_σ = 0.1 (Δ_ε 0.53): 0.62 → 1.08.
- Δ_σ ≥ 0.15 (Δ_ε ≤ 0.49): 0.67 → 1.35–1.59 (full window), 0.36 → 0.7–0.85 (c3 window).
Consequences seen in the data: (a) the polynomial degree needed to describe F over the widening x range climbs to the
ceiling d = 7 (F-test ladder), where the degree-8 comparator is rank-deficient in the 3-temperature window, so nothing is
quotable; (b) at Δ_σ = 0.2 the c3 window fits to χ²/dof 2.2 while the same model on the full window gives 72; at 0.15:
0.99 vs 6.3; (c) the local temperature polynomials of the crossing analysis fail (local χ²/dof > 2 at N ≥ 32768 for every
point with Δ_σ ≥ 0.1), which is why the cross-check has < 2 eligible series at 0.1–0.175 (and only deg4_c3 at 0.0625).

Diagnostic what-if on the existing data (Expanse login node, 2026-09-18, second/K2/Nmin 16384, points restricted to
|x| ≤ 0.45 with β_c, Δ_ε from the least-bad fit; NOT a production configuration — §4.1's coverage guard would reject it):
| point | β points kept per size (16k…512k) | d5 χ²/dof, Δ_ε | d6 χ²/dof, Δ_ε | v2 least-bad |
|---|---|---|---|---|
| 0.15 | 3,2,2,1,1,1 | 0.82, 0.4934 | 0.75, 0.4962 | 0.99 (d7) |
| 0.175 | 3,2,1,1,1,1 | 0.93, 0.4826 | 0.95, 0.4835 | 1.02 (d7) |
| 0.2 | 3,2,2,1,1,1 | 1.39, 0.4845 | 1.44, 0.4839 | 2.16 (d7) |
| 0.2125 | 2,2,2,1,1,1 | 1.47, 0.4803 | 1.49, 0.4786 | 21.5 (d7) |
A uniform x window makes the model fit at degree 5–6 with a resolvable comparator, but it leaves ONE temperature at each
of the three largest sizes: the large-N information the campaign paid for is mostly outside the scaling window. That is a
numerics gap, not a model gap. The same holds for the crossing analysis: restricted to in-window temperatures (|x| ≤ 0.6,
3 points per size at 16k–128k for 0.175), local fits of degree ≤ 4 still give χ²/dof 12–99 at 0.175 and 4–12 at 0.15
(≤ 2.2 at 0.0625); with 3 points × (value + 2 derivatives) per observable a local degree up to 6–8 is admissible and
needed, or more in-window points — again N2. The what-if is reproduced by the v3 evaluator's `--diagnostic` mode (§8.1), which is
labelled NON-PRODUCTION and bypasses the coverage guard only.

### 2.3 Regime A (Δ_σ ≤ 0.05): corrections are slow and unresolved
The U-crossing series still drift at the largest pairs: Δ_ε,eff(U) = 0.7376(26), 0.7411(36), 0.7556(44), 0.7544(49),
0.7616(56), 0.7690(75) for pairs 8k→…→256k at Δ_σ = 0.0125 (Δ_ε(fit) ≈ 0.78–0.79); at 0.025: 0.690 → 0.7085 (extrap.
0.709, ω′ 0.49); at 0.0375 and 0.05 the drift is ≈ 0.005–0.01; eligible crossing series: one at 0.0125, none at 0.0375
(ω′ at the 0.2 bound), two at 0.025 and 0.05. Fitted ω of quotable fits: 0.16–0.26 (0.0125), 0.09–0.40 (0.025). As s → 1
the transition approaches the inverse-square (Thouless) point where ν → ∞ and corrections become logarithmic, so slow
corrections are expected; the family's variants disagree by 0.02 because none is right. What is missing is either larger N
or a correction model with a theoretically fixed exponent; the fixed cap 0.0015 is not the right yardstick (§4.3).

### 2.4 Regime B: the protocol works; two gates are miscalibrated at scan scale
- Equilibration: 0.0875 and 0.125 fail on ONE group of 50 with hot/cold |z| = 3.04 / 3.05 (all else fine). With 50 groups
  per point a ≥ 3σ excursion occurs in ≈ 13 % of points by chance; the per-group rule needs a population form.
- σ_sys cap: the v2 rule (0.0015 ≤ 1/16, linear to 0.004 at 0.1, 0.04·Δ_σ above) was anchored on two points; observed
  σ_sys at accepted/near points: 0.0008 (0.0625), 0.0016 (0.075), 0.0020 (0.0875), 0.0028 (0.1), 0.0014 (0.1125);
  median σ_stat of quotable fits ≈ 0.0005–0.0006 everywhere.
- Independent replication: scan 0.0625 → 0.59046(46)(84) vs two-point 0.59071(46)(72); scan 0.1 → 0.53054(41)(275) vs
  0.52972(46)(356).

### 2.5 Estimator consistency (why the derivatives are trusted; recon 2026-09-18)
Two tests on the existing summaries: (i) cumulant derivatives Y′, U′, Y″ against central finite differences over the
neighbouring temperatures: pulls ≤ 2–3 at Δ_σ = 0.0625 and 0.025 for every size, but 5–50 (growing with N) at 0.175 and
0.2125, with the antisymmetric sign pattern of a truncation error ∝ h²Y‴; (ii) weighted quadratic/cubic fits to the five
VALUES of Y and U at one size: χ²/dof ≤ 3 at 0.0625 (N ≥ 16k), but 10²–10⁴ (quadratic) and 3–2000 (cubic) at 0.175 and
0.2125. The values alone are therefore not low-order polynomials across the wide windows at large Δ_σ, so the derivative
pulls there test the window, not the estimator; where the window is narrow the derivatives are consistent with the values
at the 1–3σ level (interior points). Conclusion: no evidence against the estimators; strong evidence that the large-Δ_σ
windows span far more of the scaling function than a degree-≤ 7 polynomial can describe at 10⁻⁴ relative precision. A
cheap direct test at small spacing is included as N0 (§5.0) so that N2 is not built on an untested premise.

### 2.6 Compute facts (measured)
Expanse packed exclusive nodes: 2^16: ≈ 2.4 h/chain at 40 per node; 2^17: 4.9 h at 40 per node; 2^18: 8.7–10 h at 60 per
node; 2^19: 25.6 sweeps/s (22 h/chain) at 32 per node, 14.5 sweeps/s at 40 per node (the wave-1 shortfall). 2^20
(extrapolated): ≈ 45 h/chain at 32 per node — one checkpoint continuation under the 48-h limit. Allocation yun124:
≈ 5.6 M SU available, expires 2026-09-30; queue waits for exclusive nodes 2–3 h recently. symmetry Intel nodes run 2^18 at
26 sweeps/s (half of Expanse).

## 3. Decision map
| decision | recommendation | why | cost of guessing wrong |
|---|---|---|---|
| D1 window definition | replace β-index windows (full/c3) by a uniform scaling window \|x\| ≤ x_max, x_max ∈ {0.35, 0.45, 0.6} as a family dimension, from (β_c, Δ_ε) frozen per point before the v3 fits | it is what the data need (§2.2) | if all x_max too small, σ_stat grows; too large, degree ceiling — the three values bracket it |
| D2 new simulations | x-matched narrow windows at N = 2^16…2^19 for the 13 grid points Δ_σ ≥ 0.1, plus 0.0625 (§5.1) | the only way to give the large sizes ≥ 3 temperatures inside the window; 0.0625 needs crossing coverage | without them regime C stays one point per large size (coverage guard fails) |
| D3 larger N | 2^20 at 4 points (0.0125, 0.025, 0.2, 0.2375) as an optional third phase | tests convergence of the slow-correction regimes | expensive (≈ 90 node-h per point); skip if N2 already yields the labels of criterion 1–2 |
| D4 gates | population form of the hot/cold test; σ_sys ratio label instead of an absolute cap (§4.3) | §2.4 | none if written before the v3 fits run |
| D5 regime-A model | add a log-corrected variant, only for Δ_σ ≤ 0.05 | theory near s → 1 | if wrong it is another variant in the spread |
| D6 union data | registry, merge and validation extended to several campaigns per (s, N) (§4.7) | new narrow-window campaigns must coexist with the old ones, not replace them | without it the new data cannot be used with the old |

## 4. The v3 model (changes relative to FIT_PLAN.md; everything else unchanged)

### 4.1 Global-fit windows (replaces full/c3 for the scan)
Family dimension window ∈ {x0.35, x0.45, x0.6}: keep the simulated points with |x_pre| ≤ x_max, where
x_pre = 100 (β − β_c^pre) (N/1024)^{1−Δ_ε^pre} with (β_c^pre, Δ_ε^pre) frozen per point from the v2 least-bad fit (recorded
in the v3 manifest before any v3 fit). Coverage guard, applied AFTER both the x selection and the Nmin cut of the
configuration: the configuration is admissible only if ≥ 4 distinct sizes retain ≥ 3 temperatures and every retained size
has ≥ 1; otherwise it is "COVERAGE-LIMITED" (not quotable; counted separately from model failures). Legacy mode: the
full/c3 windows remain available only for the two-point campaign re-derivation (§1.3).

### 4.2 Degrees and quotation ordering
Degrees 3–7 with the same F-test ladder and comparator rule; a flagged or missing degree stops the ladder (as
implemented). Quotation (V3-016): among quotable fits, smallest Nmin → fewest nonlinear+linear parameters → window
x0.45 < x0.6 < x0.35 → variant leading < background < second < log → field order 1 < 2 → lower degree → lexical
configuration name (deterministic final tie-break). Legacy mode keeps the historical ordering (full < c3, leading <
background < second, K 1 < 2).

### 4.3 σ_sys: ratio label instead of an absolute cap
σ_sys (half-range over quotable fits, coverage rule unchanged: ≥ 4 fits, ≥ 2 Nmin, ≥ 2 variants) is always reported and
added in quadrature to σ_stat for the total uncertainty. The label is ACCEPTED if σ_sys ≤ 3 × median σ_stat of the
quotable fits, ACCEPTED (σ_sys-dominated) otherwise; the absolute cap is dropped (the two-point caps stay in the historical
record). Pre-stated anchor labels under this rule, from the v2 records: 1/16: σ_sys 0.00072 vs 3 × 0.00054 = 0.0016 →
ACCEPTED; two-point 0.1: 0.00356 vs 3 × 0.00057 = 0.0017 → ACCEPTED (σ_sys-dominated) if its cross-check passes, else
CROSS-CHECK UNAVAILABLE as in v2. Scan 0.1: 0.00275 vs 0.0012 → σ_sys-dominated.

### 4.4 Equilibration (population form)
Per group: hot/cold |z| ≤ 4 and half-chain |z| ≤ 4 (hard limits); population: ≤ 2 % of groups with hot/cold |z| > 3 and
≤ 2 % of replicas with half-chain |z| > 3; τ < block/20 per group unchanged. Failure ⇒ EQUILIBRATION FAILED (as v2).

### 4.5 Crossing analysis (in-window, explicit series family; V3-009, V3-010)
Inputs per size: the temperatures of all campaigns active at that (s, N) (union, §4.7) that lie inside the crossing
window |x_pre| ≤ x_c (the wide-window observations are thereby excluded, V3-010). Series family (pre-registered): crossing
window x_c ∈ {0.45, 0.6} × local-degree rule ∈ {ladder d*, ladder d*+1} — up to four series. Local degrees: for a size
with n in-window temperatures the admissible degrees are 2 ≤ d ≤ d_max(n) with 2(d+1) ≤ 6n − 2, i.e. residual dof ≥ 2
for the fit and for every F-test comparator (n = 3 ⇒ d ≤ 7; a saturated interpolant is never admissible, V3-018); the
ladder runs over admissible degrees with the F-test (p < 0.01) and stops at the first non-significant, flagged or
inadmissible step; a size is usable in the "d*" rule if its chosen fit is unflagged with dof ≥ 2 and local χ²/dof ≤ 2,
and in the "d*+1" rule only if d*+1 is admissible and its fit passes the same conditions — otherwise that size, and every
pair using it, is unusable for that rule. A doubling pair is usable if both sizes are usable and the U-crossing lies inside
the common β bracket (quotients.py rule). Deduplication (V3-019): before counting or aggregating, the eligible series are
reduced to distinct configurations, two series being identical if they select the same measurement identities at every
used size, the same per-size degrees and the same pair set; |E| counts distinct configurations only, so identical window
selections (e.g. no observation in 0.45 < |x_pre| ≤ 0.6) cannot double-count; |E| < 2 ⇒ CROSS-CHECK UNAVAILABLE.
Pairs: the four largest usable doubling pairs at the point (with 2^20 present: 64k–128k … 512k–1M; covariance 8×8, dof
4, gates as v2 §3.5); the pair set, the per-size degrees and the frozen (β_c^pre, Δ_ε^pre) are recorded in the manifest,
and the per-draw refits reuse the frozen degrees on the shared bootstrap draws. Feasibility on the existing data: at
0.175 the in-window sizes with ≥ 3 temperatures stop at 131072 (§2.2), so the four largest pairs cannot be formed before
N2 — the recovery path is N2 itself, not a re-analysis; at 0.0625 the existing 5 temperatures satisfy |x_pre| ≤ 0.6 at all
sizes (local cubic χ²/dof ≤ 2.2), so N2 there adds coverage but is not the only route.

### 4.6 Decision table (complete; applied in this order)
Prerequisites checked first: valid production inputs (§4.7 validation, block sizes 2048/4096/8192 with identical
measurement identities) — otherwise NON-PRODUCTION; then, in this order:
| # | condition | label | quoted number |
|---|---|---|---|
| 1 | equilibration population rule fails | EQUILIBRATION FAILED | none (diagnostics listed) |
| 2 | no admissible configuration because of the coverage guard | COVERAGE-LIMITED | crossing value if ≥ 2 eligible series with ≥ 270 common-valid draws (standalone aggregation below), else finite-size estimates |
| 3 | admissible configurations but no quotable fit; ≥ 2 eligible series with ≥ 270 common-valid draws | MODEL-LIMITED (crossing value) | Δ_ε∞ ± σ_∞ ± Δ_ω′ |
| 4 | admissible configurations but no quotable fit; otherwise | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | the two largest usable pairs' Δ_ε,eff(U), Δ_ε,eff(Y) with errors |
| 5 | quotable fits exist but σ_sys coverage absent (< 4 fits, < 2 Nmin or < 2 variants) | CONDITIONAL | Δ_ε ± σ_stat, range of quotable fits, plus crossing value if available |
| 6 | quotable fits, σ_sys estimable, reblocking of the quoted fit unavailable (inputs missing) or failed (reblocked fit not converged/unflagged, < 270 valid draws, or σ_stat outside ±30 %) | REBLOCKING UNAVAILABLE / REBLOCKING FAILED | Δ_ε ± σ_stat ± σ_sys, both reblocked σ_stat listed |
| 7 | quotable fits, σ_sys estimable, reblocking passes, cross-check has < 2 eligible series OR < 270 paired common-valid draws | CROSS-CHECK UNAVAILABLE | Δ_ε ± σ_stat ± σ_sys, plus largest-pair Δ_ε,eff |
| 8 | … cross-check evaluable and \|Δ_ε − Δ_ε∞\| > 2σ_D | CROSS-CHECK FAILED | Δ_ε ± σ_stat ± σ_sys, plus crossing value |
| 9 | … cross-check passes, σ_sys ≤ 3 × median σ_stat of the quotable fits | ACCEPTED | Δ_ε ± σ_stat ± σ_sys |
| 10 | … cross-check passes, σ_sys > 3 × median σ_stat | ACCEPTED (σ_sys-dominated) | Δ_ε ± σ_stat ± σ_sys |
Every combination of (equilibration, coverage, quotable set, σ_sys coverage, reblocking, cross-check) reaches exactly one
row; σ_sys is only quoted in rows 6–10 where it is estimable (V3-013).
Standalone crossing aggregation (no global fit involved): E frozen from the central fits; common-valid draws = draws on
which every member of E converged (existence/convergence only); Δ_ε∞ = median over E of the central extrapolations;
σ_∞ = half the 16–84 % range of the per-draw median over E; Δ_ω′ = half-range of the central extrapolations over E,
enlarged by the half-range of Δ_ε∞ over the grid minima with Δχ² ≤ 1 (ω′ systematic). Requires ≥ 270 of 300 common-valid
draws, else EXTRAPOLATION UNAVAILABLE.

### 4.7 Union data schema (V3-001)
- Registry: `active[pair]` becomes a list of campaign names (one or more); every listed campaign must be complete for the
  pair. `expected_pairs` unchanged. Legacy registries (string values) are read as one-element lists.
- Completion evidence, analysis snapshots and merging operate per campaign as now; merge_summaries.py concatenates the
  entries of all active campaigns of a pair, requires ≥ 3 entries per pair (no longer exactly 5), keeps coincident
  temperatures (|Δβ| < 10⁻⁹) as separate entries, and stamps every entry with (campaign, task id).
- Chain identity for the shared bootstrap schedule: key = (seed, s, N, β, campaign index, replica, draw), the campaign
  index being the position of the campaign name in the registry's `campaigns` list (recorded in the manifest), so
  coincident temperatures from different campaigns never collide.
- Input validation (select_model.window_consistency, V3-011): within each input a uniform block size; the three inputs
  carry exactly 2048, 4096 and 8192; identical sets of measurement identities (campaign, task) across the three inputs and
  unique identities within each; the 5/3-temperature rule is replaced by the x-window coverage guard of §4.1 (legacy mode
  keeps the old rule).
- Reblocking: unchanged in content (quoted configuration refitted on the 2048 and 8192 inputs, σ_stat within ±30 %,
  reblocked fit converged/unflagged with ≥ 270 valid draws) and now an explicit prerequisite of both ACCEPTED labels
  (§4.6 rows 6–10; V3-012).
- Independent chains (V3-015): every added campaign gets its own `seed_base` recorded in the registry, and prepare.py
  derives MC seeds from (seed_base, campaign name, N, β, replica) so that campaigns never share a seed stream; before
  merging, the finalize stage verifies across the whole active union that no two chains share (seed, N, β) and that no
  two samples.bin archives share a SHA-256 (from the completion evidence), and refuses otherwise. The campaign index in the
  bootstrap key is a separate requirement (schedule identity), not a substitute for this check.
- expected_pairs (V3-014): the schema is preserved; for each approved N3 point the registry's `expected_pairs` is
  extended with `<s>:1048576` BEFORE the new campaign is activated, and the new pair is carried through completion
  evidence, snapshots, merging, coverage checks and provenance like any other pair.
- Provenance: all campaigns' manifests, completion evidence and block archives are hashed (as now, per campaign).

### 4.8 Regime-A variant
Variant 'log': F(x) + r^{−ω}G(x) + F(x) c_Q / ln(N/N₀) with N₀ = 256 fixed; admitted only for Δ_σ ≤ 0.05; enters σ_sys like
the others; reduces to 'leading' at c_Q = 0 (test).

### 4.9 Unchanged
Bootstrap 300 with the shared schedule, calibrated residual gate, paired cross-check for quotable fits, reblocking,
provenance, equilibration data, order-stability comparator.

## 5. Numerics needed (costs from §2.6; all on Expanse before 2026-09-30, overflow to symmetry defq/preq)
5.0 **N0 — dense-window diagnostic (≈ 4 node-hours, run first):** at Δ_σ = 0.175, N = 2^16 and 2^18, 9 temperatures
    β_j = β_c^pre + j·δ, j = −4…4, δ = h′(N)/4 (so |x_pre| ≤ 0.45), 4 replicas, 5·10⁵ sweeps (independent seed namespace,
    own campaign). Test (V3-017; design revised in revision 12 after review round 8 and the N0 data — amendment record below),
    per size N:
    (j) **Joint polynomial consistency (replaces (b) and (a) of revisions ≤ 11; revision 13 after review round 9).** For each size
        the six observables of the 9 temperatures — (Y, Y′, Y″, U, U′, U″): values and cumulant first and second β-derivatives — are
        fitted jointly, with the full per-temperature 6×6 covariance (temperatures independent), by ONE polynomial per observable
        family, P_Y(β) and P_U(β) of common degree d — the production local-fit construction (quotients.LocalCurve; 2(d+1) linear
        parameters, dof = 54 − 2(d+1)). Every admissible degree 2 ≤ d ≤ 9 (dof ≥ 34) is fitted (no ladder, no early stop, V3-022);
        every χ² and p-value is recorded, and a numerical failure of any fit is recorded per degree (V3-031). Calibration: for a KNOWN
        covariance χ²_d is exactly χ²_dof-distributed under the Gaussian null for a smooth polynomial of degree ≤ d (linear weighted
        least squares); the summaries' covariances are block estimates (≈ 488 blocks per temperature), so for the real data the χ²
        calibration is an approximation whose actual rejection rate is measured by the block-level validation below (V3-029).
        Selection: d* = the LOWEST degree with P(χ²_dof ≥ χ²_d) ≥ 0.01. Per-observable mean |pull| at d* is reported (diagnostic).
        Outcomes per size: PASS(d*) if d* ≤ 7; INCONCLUSIVE if d* ∈ {8, 9} (a polynomial description exists but its degree is
        unresolved at this spacing — retest with δ/2, same budget) or if the values alone are not fitted by any degree ≤ 9 (smoothness
        unresolved — same retest); FAIL if no joint polynomial of degree ≤ 9 reaches p ≥ 0.01: the data are incompatible with every
        smooth polynomial of that order over the window, which — after numerical failure is excluded — is treated as evidence against
        the mutual consistency of the three estimators WITHIN the polynomial approximation (the test itself cannot exclude a smooth
        function needing degree > 9 over |x| ≤ 0.45; only the δ/2 retest can) → N2 is not submitted and the plan returns to review;
        NUMERICAL FAILURE if any fit at or below the selection point failed (non-production; the run is repeated after the cause is
        fixed). Diagnostic outcome: PASS only if every size PASSes; NUMERICAL FAILURE if any size has one; else FAIL if any size FAILs;
        else INCONCLUSIVE. Window rule (the intent of the former (b), unchanged): if max_N d* ≥ 5 the x_max of N2 is reduced to 0.35
        and the N2 fit degrees must include d*; if max_N d* ≤ 4 the window |x| ≤ 0.45 stands.
        Error budget (V3-028): the false-FAIL rate is bounded by 1 % per size (the true-degree fit is rejected with probability 0.01);
        the diagnostic FAILs if any size FAILs, so the combined bound for n sizes is 1 − 0.99^n (1.99 % for two sizes). Per-size and
        combined rates are reported.
        Validation of the procedure (V3-017/026/028/029/030): independently specified synthetic models with Σ from the summaries,
        10⁴ datasets each, the COMPLETE procedure (all degrees, selection, classification, failure bookkeeping) repeated on every
        dataset — nulls (i) degree-5 cancellation polynomial with consistent derivatives, (ii) degree-6 polynomial, (vii) degree-7
        polynomial (all with maximum excursion 20 % of the mean |Q|, i.e. well resolved); (iii) model (i) with every first derivative
        shifted by +5 σ(Q′); (iv) boundary model (V3-026): the data's own quadratic plus a weak cubic whose amplitude puts the noiseless
        quadratic VALUE fit at the 5 % critical value of χ²₆; (viii) interpolation null-space fixture (V3-030): model (i) plus
        a·∏_j(β − β_j) over the nine sampled temperatures, values unchanged and first derivatives shifted by ≈ 20 σ(Q′) — a smooth
        degree-9 function with correct estimators: its NOISELESS fixture must come out INCONCLUSIVE at d* = 9 (never FAIL); noisy
        realisations may FAIL only at the declared false-FAIL rate, checked by the same Monte Carlo acceptance test as the null models
        (V3-032); and block-level variants of (i), (ii)
        and (iv) in which every dataset is generated as B independent Gaussian blocks per temperature (B = the summary's block
        count) whose mean and re-estimated covariance enter the procedure (V3-029). Sensitivity record, reported and not gated: (v)
        model (i) with every first derivative scaled by 1.005, (vi) with every second derivative scaled by 1.05. Acceptance (one-sided
        Monte Carlo tests at the 1 % level, V3-028): for every null model and for (viii) the observed FAIL count must not exceed the
        declared combined bound significantly (P(X ≥ x | n, 1 − 0.99^n) ≥ 0.01); for (iii) the FAIL count must not fall short of 95 %
        significantly (P(X ≤ x | n, 0.95) ≥ 0.01); the noiseless fixtures of (i), (ii), (vii), (iv) PASS with χ² = 0 at d* = 5, 6, 7, 3
        and the noiseless (viii) is INCONCLUSIVE at d* = 9; numerical failures < 1 % of datasets for every model. Outcome and
        validation are computed by n0_diagnostic.py --rule joint; the same program still evaluates the superseded rules
        (--rule preregistered | rev11) with their ORIGINAL synthetic-model generators (versioned by protocol, V3-033) so that every
        recorded attempt is reproducible; each run stores an executable source snapshot of the diagnostic beside its manifest, and
        N0_COMPARISON.md distinguishes historical reproduction (superseded rule, original generator) from validation with the revised
        models.
        Superseded rules, kept for dual reporting: the pre-registered values-only rule (revisions ≤ 10: per (size, Q) the lowest
        degree with χ²/dof ≤ 1.5 on the 9 values, then T = rᵀC⁺r of the first-derivative residuals against a mixture-calibrated
        99 % threshold) and the revision-11 rule (value-fit p ≥ 0.01 instead of χ²/dof ≤ 1.5). On the N0 data they give
        INCONCLUSIVE (Y at 2^18: χ²/dof 1.63–2.06 for degrees 2–6) and FAIL (T = 117.5 against 38.5) respectively; the FAIL is a
        false one by degree under-selection — with U at degree 3 the same statistic is 25.8 for rank 20 (p = 0.17) — which is the
        defect V3-026 identifies: a values-only polynomial cannot resolve the degree the derivatives require.
    **Amendment record (post hoc; both amendments were written after the N0 data had been seen).** Revision 11 (2026-09-18;
    review round 8 → REVISE with V3-026/027) replaced χ²/dof ≤ 1.5 by the value-fit p ≥ 0.01 screen because the pre-registered cut
    excluded 39–54 % of perfectly smooth synthetic replicates in the two-size layout (four fits with 2–6 dof). Revision 12
    (2026-09-18/19; review round 9 → REVISE with V3-028…031) replaced the values-referenced derivative test by the joint test (j);
    revision 13 (2026-09-19; review round 10 → REVISE with V3-032/033) corrected its error budget, stated the calibration as approximate
    for block-estimated covariances with a block-level validation, routed unresolved truncation (d* ≥ 8) to INCONCLUSIVE and booked
    numerical failures; revision 14 (2026-09-19; for review round 11) restricts the never-FAIL expectation of fixture (viii) to its
    noiseless form and versions the synthetic generators by protocol with per-run source snapshots. Every
    attempt on the N0 data is recorded immutably with plan and implementation hashes, rule, seed and input hashes (V3-027) and
    linked from scanA_exp/n0/run_20260918_211926/N0_COMPARISON.md: pre-registered (INCONCLUSIVE), fresh-seed re-validation,
    exploratory χ²/dof ≤ 2.0 (non-production), revision 11 (FAIL, provisional), revision 12 (PASS, pre-round-9), revision 13 (PASS,
    pre-round-10), historical reproduction of the pre-registered rule with the current code, revision 14. The amended test is chosen for its
    exact calibration and its power, not for its effect on these data; it applies unchanged to any δ/2 retest.
5.1 **N2 — x-matched stage B′.** Points (14): 0.0625 (crossing coverage), 0.1, 0.1125, 0.125, 0.1375, 0.15, 0.1625,
    0.1727335, 0.175, 0.1875, 0.2, 0.2125, 0.225, 0.2375. Sizes 2^16, 2^17, 2^18, 2^19; 5 temperatures at
    β_c^pre + k·h′(N)/2, k = −2…2, with h′(N) = 0.45/(100 (N/1024)^{1−Δ_ε^pre}) (the 5 points cover |x_pre| ≤ 0.45);
    8 replicas, 2·10⁶ sweeps, 50 000 warmup. Chains per point 160 (2240 total); per point ≈ 41 node-hours (2^16: 2.4,
    2^17: 4.9, 2^18: 6, 2^19: 27.5 at 32 per node); total ≈ 575 node-hours ≈ 74 000 SU; wall ≈ 30 h per 2^19 node →
    14–28 nodes for 1.5–2 days. Packing: ≤ 32 chains of 2^19 per node, 20-h node limit with checkpoint continuation;
    completion = DONE.json count per campaign (never the Slurm state). Registered as campaigns `stageBx_<N>` with their own
    seed_base, added to the active lists (§4.7), never replacing stage A/B. Expected effect on the crossing analysis: each
    size 2^16–2^19 gains 5 in-window temperatures (plus the 1–3 old ones inside the window), so the four largest pairs
    become formable at every N2 point.
5.2 **N1 — re-analysis only (no simulations):** v3 evaluator on the existing data for all 20 points: ≈ 2 node-hours.
    Expected: regime B all quotable with the ratio label; regime C COVERAGE-LIMITED (one temperature per large size inside
    the window) with crossing values where ≥ 2 series are eligible; regime A labelled by §4.6 (most likely ACCEPTED
    (σ_sys-dominated) or CROSS-CHECK UNAVAILABLE) unless the log variant collapses the spread.
5.3 **N3 — optional larger N:** 2^20 with x-matched windows at 0.0125, 0.025 (regime A) and 0.2, 0.2375 (regime C): 40
    chains per point, 2 nodes × 45 h (+ one continuation) ≈ 90 node-hours ≈ 11 500 SU per point; crossing pairs shift to
    the four largest usable pairs (§4.5); decide after N1+N2.
5.4 Not needed: more replicas at existing temperatures (σ_stat is not the limit anywhere), 2^21 (≈ 4× 2^20, cannot finish
    before the allocation ends), new observables.
5.5 Schedule: N0 and N1 immediately after approval (N0 ≈ 6 h incl. queue; N1 ≈ 3 h incl. review of the v3 code); N2
    submission within 24 h of a passing N0 (queue 2–3 h, run ≤ 2 days, analysis 1 h) → complete ≈ 2026-09-23; N3 decision
    2026-09-23, complete ≈ 2026-09-27.

## 6. Assumptions and risks
- A1 β_c^pre is accurate to ≲ 0.2 h′(N = 2^19) at every N2 point (σ(β_c) ≈ 1–3·10⁻⁵ vs h′(2^19) ≈ 1.8·10⁻⁴). Source: fit
  records. Risk: a mis-centred window at 2^19 loses the outer points → fallback: β_c from the 2^18–2^19 U-crossing.
- A2 The what-if of §2.2 transfers to 5-point narrow windows (it removes wide-x points; it adds no information). Risk: for
  Δ_σ ≥ 0.2 where ω < 0.12 the ladder may still reach d = 7; these points are in criterion 2, where MODEL-LIMITED with a
  crossing value is an allowed outcome.
- A3 Rates of §2.5 hold within 30 %; the 20-h node limit with continuation makes the risk a delay, not a loss.
- A4 Allocation: 74 000 SU (N2) + ≤ 46 000 SU (N3) ≪ 5.6 M SU available; the binding constraint is the 2026-09-30 expiry.
- A5 Regime A may remain σ_sys-dominated even with 2^20 (logarithmic corrections); the plan then reports the labelled
  value (criterion 2), which is the honest state of the art at s → 1.

## 7. Non-goals
No change to observables or to the MC code; no Bayesian model averaging; no use of the ε-expansion in the selection.

## 8. Verification
1. N1 proof: `run_fits_v3.sh` in legacy-window mode on the two-point campaign re-derives Δ_ε(1/16) and Δ_ε(0.1) within
   1σ_stat of v2 with the labels pre-stated in §4.3; `select_model_v3.py --diagnostic` (NON-PRODUCTION, coverage guard off)
   reproduces the what-if table of §2.2 within 0.02 in χ²/dof and 0.001 in Δ_ε.
2. Unit checks (tests/test_fit_v3.py): x-window selection with frozen (β_c, Δ_ε); coverage guard applied after Nmin;
   population equilibration rule — 1 of 50 groups at hot/cold 3.5σ with the other 49 below 3σ → PASS, 2 of 50 above 3σ →
   FAIL, any group above 4σ → FAIL; ratio label at the pre-stated anchor values; union registry (two campaigns for one
   pair, coincident temperatures kept, schedule keys distinct); standalone crossing aggregation without a global fit;
   log variant reduces to 'leading' at c_Q = 0; pair selection with and without 2^20; crossing series family yields
   four distinct series on synthetic data with observations in 0.45 < |x| ≤ 0.6; with identical window selections it
   collapses to |E| = 2 when both degree rules are eligible (d* and d*+1 differ) and to |E| = 1 ⇒ CROSS-CHECK UNAVAILABLE
   when only one degree configuration is eligible (V3-021); local degree 8 with three temperatures is rejected (dof rule)
   and a d*+1 beyond d_max makes that rule's series unusable; decision table reaches exactly one row for every combination
   (exhaustive enumeration test); input validation rejects a repeated block size, a mismatched identity set and a
   duplicated seed or samples.bin hash; quotation ordering is deterministic (permutation test); N0 test (j): the joint
   χ² of n0_diagnostic.joint_polyfit equals quotients.LocalCurve's χ² for the same entries and degree; the noiseless fixtures
   (i), (ii), (vii), (iv) PASS with χ² = 0 at d* = 5, 6, 7, 3 and the noiseless null-space fixture (viii) is INCONCLUSIVE at d* = 9;
   on synthetic correlated data the complete-procedure outcome counts of every model satisfy the one-sided acceptance tests of
   §5.0 (null FAIL counts against 1 − 0.99^n, power against 95 %), with and without covariance re-estimation from blocks; a per-degree
   numerical failure at or below the selection point yields NUMERICAL FAILURE, never PASS or FAIL; a value set needing degree > 9
   gives INCONCLUSIVE; a run directory holding a record is never overwritten and every record carries its manifest (V3-027).
3. N2 completion: DONE.json count = 160 per point after the node jobs, completion_check PASS on every stageBx campaign.
4. N0 test (j) of §5.0 recorded per size with the joint χ² and p-value of every degree 2–9, the selected degree d*, the
   per-observable mean |pull| at d*, the outcome (PASS(d*) / FAIL / INCONCLUSIVE), the window decision, the validation outcome
   counts of every model (per size and combined, fixed and re-estimated covariance) with their acceptance tests, and the provenance
   manifest (V3-027) — before any N2 submission; the superseded rules' outcomes are
   listed alongside in N0_COMPARISON.md.
5. Final: FIT_V3_SCAN.md lists all 20 points with exactly one label from §4.6; criterion 1 met for 0.0625–0.1875.
