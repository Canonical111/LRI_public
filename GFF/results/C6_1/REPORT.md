# C6(1) of the 1D long-range Ising model — exact all-graph sums (symmetry, 2026-09-29)

## Result (pre-registered estimator, PLAN.md §4.5)

**C6(1) = 14331.68703277 ± 0.00000049**

That is 14331.6870328(5). The allowance is an empirical convergence-and-rounding allowance, not a rigorous bound.

For comparison:
- previous value: 14331.8 ± 0.5 (estimator 14331.77075, MC SE 0.14344);
- the new value is 0.084 lower, i.e. −0.58 old SE, well inside the old ±0.5;
- the uncertainty is about 10⁶ times smaller.

The series becomes
Δ_ε = ½ − ε/6 + 0.657131263981 ε² − 3.719856322902 ε³ + 45.42488010356 ε⁴ − 731.13947662454 ε⁵
+ 14331.6870328(5) ε⁶ + O(ε⁷).

## Method
The original stratified estimator used exact sums up to degree 6, the hard stratum to degree 10, and Monte Carlo
light-stratum levels. It is replaced by **exact sums over all 2,137,415 graphs × 360 reversal classes** at
quadrature degrees N = 6, 8, …, 22, for both infrared cutoffs (maxgap, span):
- the light stratum in compensated, order-fixed 8-lane double arithmetic;
- the hard stratum (≥ 2 pole axes or a power axis) in long double, because its double-precision error grows with
  N.

The five-loop inputs (A5, B5 poles and J5) were recomputed in long double up to degree 40. The L2–L4 amplitudes
are the reference's degree-28 values.

## Degree sequence (five-loop inputs at M = 40)

| N | C6 maxgap | C6 span | maxgap − span | ρ (rounding) |
|---|---|---|---|---|
| 6 | 14334.549146861 | 14332.554509427 | 1.99 | 5.5e-10 |
| 8 | 14331.816869671 | 14331.694925294 | 0.122 | 1.9e-10 |
| 10 | 14331.694513177 | 14331.686134511 | 8.4e-3 | 7.4e-10 |
| 12 | 14331.687501161 | 14331.686917319 | 5.8e-4 | 1.9e-9 |
| 14 | 14331.687061994 | 14331.687022076 | 4.0e-5 | 4.1e-9 |
| 16 | 14331.687034432 | 14331.687031833 | 2.6e-6 | 2.9e-9 |
| 18 | 14331.687032845 | 14331.687032694 | 1.5e-7 | 3.3e-8 |
| 20 | 14331.687032736 | 14331.687032727 | 9.1e-9 | 4.5e-9 |
| 22 | 14331.687032770 | 14331.687032767 | 2.5e-9 | 8.8e-8 |

- The convergence is geometric: each 2-degree step shrinks the change by about 0.06 (maxgap) and 0.1 (span). The
  two independent cutoffs converge to the same value.
- At N = 22 both last steps (+3.3e-8, +4.0e-8) and the cutoff difference are below 2ρ. Stopping rule (a),
  convergence to the floating-point floor, ended the campaign.

**Allowance at N* = 22:** U = ceil₂(U_conv 8.0e-8 + U_cut 2.5e-9 + U_round 3.5e-7 + U5 8.7e-9 + U5_round 4.1e-8 +
Ulow 3.1e-9) = 4.9e-7.
- U_round = 4ρ(22), with ρ from the calibrated perturbation replicates (calibration factor 1.03). It dominates:
  the result is limited by floating point, not by quadrature convergence.

## Checks
- **Validation gates V1–V11 all passed** (attempt 20260929T123319_8680864, `validation/summary.json`):
  - the graph enumeration is reproduced;
  - the weights equal the reference generator bitwise, apart from exact zeros;
  - the N6 all-graph sum reproduces the reference;
  - the hard stratum at N6–10 and the L5 files are reproduced within the reference's own summation error;
  - double and long double agree;
  - results are bitwise deterministic across threads, sector splits and resumes;
  - light + hard = all;
  - AMD and Intel give bitwise-identical double results, and long double agrees to ≤ 1.7e-16.
- **Exact versus the old Monte Carlo levels**, as z-scores in the old SEs:

  | Level | maxgap | span |
  |---|---|---|
  | light 8−6 | −0.57 | −0.60 |
  | light 10−8 | +0.86 | +1.33 |
  | all-graph 12−10 | +0.09 | +1.26 |

  The old MC was unbiased within its errors; its final estimate was simply noisy.
- **Rounding.** Double minus long double on the hard stratum is 5e-9, 7.6e-8 and 1.5e-7 at N = 6, 8, 10; these
  errors are removed by the long-double production. The L5 double minus long double at M = 40 is 1.2e-6 in C6,
  which justifies long double for L5.
- **Old five-loop inputs** (retained degree-18 poles, saved J16) move C6 by −1.4e-5 and −6.6e-6. The old input
  records carried errors of order 1e-5 in C6.
- **C7 package's six-loop sector**, an independent framework: coordinate-forest RQMC/MC at radial degree ≤ 7.
  It is compared with the exact C6 in `C7_crosscheck.json` (written by `tools/c7_crosscheck.py` from the C7
  package's `C7_final.json`, with input hashes); z uses the C7 package's SE 0.305:

  | Stage | Value | Status | z |
  |---|---|---|---|
  | degree-6 estimate | 14332.43593 | measured | **+2.46** |
  | + degree 6→7 check step (−0.45383) | 14331.98210 | measured | +0.97 |
  | + post hoc geometric tail (ratio 0.443, −0.36156) | 14331.62055 | model-dependent | −0.22 |

  The degree-6 tension is the radial truncation of that framework, documented in the C7 report. Agreement beyond
  the measured degree-7 step is conditional on the tail model. `C6_final.json` field
  `diagnostics.C7_package_byproduct` (14331.62055 ± 0.305) is this tail-extrapolated stage; it was hardcoded in
  the analysis and is superseded by `C7_crosscheck.json`.

## Provenance and cost
- **Code:** `LRI_C6_1D_HPC`, commit 8680864, frozen on symmetry at `<SCRATCH>/lri_c6_1d/code/8680864`.
  Executables: c6sum sha256 4cae933b…, c6sum_ld 011ec407…. Level files and their hashes are in `assembled.json`
  and `rounding.json`; decision files for N = 16 to 22 are in `decisions/`.
- **Data:** `<SCRATCH>/lri_c6_1d/{levels,runs}` (per-sector JSONL for every level).
- **Compute:** 44.5 node-hours of production, all on amdq, plus about 10 node-hours of validation.
- **Review:** the plan was Codex-approved after 8 rounds (PLAN.md rev 8).
  - Code inspections 1–3 returned REVISE, and every finding was fixed.
  - The round-3 accounting fixes, the portable/amdq change and the ops driver were not inspected. The driver
    only calls the approved scripts.
  - The full log is in `LRI_C6_1D_HPC_loop/PLAN-REVIEW-LOG.md`.

## Addendum (2026-10-01): precision of the inherited L2–L4 amplitudes (results review RR-001)

Ulow measures only the degree change (28 vs 22) of the reference's lower amplitudes, which come from the Python
engine with numpy long double in `reference/lower_extended.py`. It does not cover their floating-point error. That
error was measured (files in `lower_amplitude_precision/`, scripts `tools/lowercheck.py` and `tools/lowercmp.py`):
- **Reproduction.** The same code at degree 28, rerun in long double on symmetry, reproduces the saved amplitudes
  to 4.7e-17 relative. R6 moves by 1.3e-13 (maxgap) and 2.7e-13 (span).
- **Precision sensitivity.** Rerun in float64, R6 (hence C6) changes by −5.95e-8 (maxgap) and −5.90e-8 (span),
  with the production five-loop inputs (L5, M = 40) held fixed.
- **Estimate.** Rounding errors scale with the unit roundoff, which is 2^-11 smaller for long double than for
  float64. The long-double rounding of the inherited amplitudes is therefore ≈ 5.95e-8 × 2^-11 = 2.9e-11 in C6.
  With the factor 4 used for the other rounding terms, Ulow_round = 1.2e-10.
- **Effect on U.** U = ceil_2sf(4.8853e-7 + 1.2e-10) = **4.9e-7, unchanged**. Even the full float64 difference,
  6e-8, would raise U only to 5.5e-7.
