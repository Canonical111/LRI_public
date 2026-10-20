# Reviews and checks: lri_2d_coeff_independent_check (summary; no raw logs or transcripts are shipped)

All code here was written by Claude Code sessions (2026-10-08..14), one coordinating session and subagents it
launched. There was no external (Codex) code review of this tree. Its reliability rests on redundancy: independent
implementations that agree to their working precision, exact rational arithmetic wherever possible, and checks of
every derived claim by the coordinating session from the exact output files, with its own scripts.

## Independent implementations
- **Clean room.** `rs_exact` (exact-rational RS) and `cauchy` (non-perturbative Cauchy integrals at 256 bits) were
  written by separate agents that saw neither the production package nor each other's work, only the model
  specification `SPEC.md` (written from first principles; for the consistent and literal windows the definition was
  taken from the package's METHOD.md). Agreement: RS vs package 3.9e-13 (25 scheme/cutoff pairs, all quantities), Cauchy
  vs RS 4.8e-46 (15 cases), package vs Cauchy 1.6e-14 (`compare_*.txt`).
- **Large-L codes.** Each large-cutoff code was checked against brute-force exact rationals at small cutoff:
  - `continuum/exact_low_orders.py` (C2, C3) vs the package: ≤ 4e-14;
  - `c4_exact` vs rs_exact, the package and zeromode_exact: ≤ 1.1e-13 (`c4_exact/validate_*.txt`);
  - the ε⁵ engine vs rs_exact, the package, complete_exact and brute force: ≤ 2.2e-13 (`residual_log/results/eps5/validation_*.txt`);
  - `large_L/tagchan.py` (δ⁽³⁾) vs exact rationals at L = 2..16: ≤ 4e-16 (`large_L/results/validation_small.txt`);
  - the all-order solver `ce_wc` vs complete_exact and brute force at small L (exact).
- **Two exact window implementations.** `complete_exact` and the residual_log codes implement `WINDOW_SPEC.md`
  separately; they agree exactly on C4 of W (L = 2..12) and to ≤ 7e-14 on `C4W_by_L.csv`.

## Checks of derived results by the coordinating session
- **ε⁴ complete window.** Own refit of C4^W(L): 5.0488682–5.0488685, against the derivation's 5.0488682(6).
- **ε³ external-line window (Wcs).** `residual_log/fits/parent_check_wcs`:
  - δ⁽³⁾(L) recomputed from the tagged-φ files equals the value each Wcs run used;
  - C0..C4, r, g are unchanged by Wcs;
  - C5^Wcs − C5^Wc = δ⁽³⁾(L) S(L) to 1.2e-16;
  - blind L = 16 predictions.
- **Partial ε⁴ χ-line window.** `residual_log/fits/parent_check_p5`: invariances, χ-line gaps.
- **C5 at L ≤ 300.** `residual_log/fits/parent_check_largeL/refit_c5_300`: independent refit, C4^W null test, fixed-b shifts.
  It agrees with the large-L agent's `large_L/c5_fits300.txt`.
- **Optimized engine.** `large_L/lib_opt` was regression-tested against the unmodified engine `large_L/lib` per task
  (≤ 7.3e-16 over 1448 tasks, requirement 1e-12) and on the assembled C5 (≤ 1.2e-13 at L ≤ 60; the L = 300
  assembly reproduces the L ≤ 200 production data to 7.6e-13), `large_L/results/regression_opt.txt`.

## Errors found and corrected during the work (all corrected in the shipped outputs and the note)
- **δ⁽³⁾(∞).** Extrapolations from L ≤ 16 had given −0.0159 to −0.0160 and "excluded" −4/(81π). The exact chain sums to
  L = 16000 show that δ⁽³⁾(L) is not monotone (minimum at L = 34) and tends to −4/(81π) to 3e-11.
- **"Free ln L" in C5.** The earlier free ln L coefficient (−0.014 … −0.059) came from tail towers without ln³L/L. With
  the ln³L/L tail and data to L = 300 it drifts to +0.004, consistent with 0.
- **Growth of the ε⁴ descendant residual.** It was once quoted as 0.0145 ln L; the correct value is 0.028 ln L.
- **A refit "calibration".** One that added β ln L to the data itself tested nothing (the fit is linear) and was removed.
- **First cost estimate of the L = 300 run.** It was too low by about an order of magnitude; the run was stopped
  after 130 node-hours and finished with the optimized engine (37 node-hours).

## What the checks do not establish
- The windows were derived after their effects had been seen and with the continuum values known, though with no
  fitted parameter.
- δ⁽³⁾(∞) = −4/(81π) is identified numerically (3e-11), not proven.
- A residual ln L in C5 with |b| ≲ 0.01 is not excluded at L ≤ 300.
- The ε³ identities of the φ² descendants are not settled at L ≤ 16.
- The ε⁴ window is not known completely, so C6..C8 are not reproduced in d = 2.
