# HT_Pert d = 2 results: where each quoted output lives

The d = 2 outputs are code outputs inside the snapshot `HT_Pert/code/lri_2d_coeff_independent_check` (paths below are
relative to it), so that the shipped scripts regenerate them in place (`make -f public.mk replay-full`). This folder
holds the replay outputs of the release check (`replay_p2_reference.txt`, `replay_prod_reference.txt`, produced on the
exported tree on symmetry; your output should match them line by line up to platform-dependent trailing digits,
for example those of κ in `p2.c4_kappa`, which a laptop with numpy 1.24.4 prints as 2.207292996476e-04; the check compares
κ with its analytic value).

| Quoted result | Output (inside the snapshot) | Written by |
|---|---|---|
| package vs exact RS / Cauchy (HT_Pert note Sec. 4.2, App. A.2) | `compare_with_package.txt`, `compare_three_way.txt` | `compare_*.py` (and `public/replay_p2.py`) |
| C2(∞) 35 digits, C3(∞), κ | `continuum/asymptotics_C2_C3.txt` | `continuum/asymptotics_C2_C3.py` |
| C4 schemes (raw, consistent, zero-mode), ln L coefficients, blind L = 2000 test | `c4_exact/fits/fit_summary.txt` | `c4_exact/fits_c4.py` |
| C4 with the complete window W: 5.0488682(10) | `residual_log/fits/fits_final.txt`, `residual_log/C4W_by_L.csv` | `residual_log/fits_final.py`, `make_csv.py` |
| δ⁽³⁾(L) → −4/(81π), ln L/L term, minimum at L = 34 | `residual_log/large_L/fits/delta3_fits.txt` | `large_L/delta3_fits.py` |
| S(L) → 0.367187, no ln L | `residual_log/large_L/fits/legw_logs.txt`, `residual_log/fits/parent_check_wcs/fits.txt` | `legw_logs.py`, `parent_check_wcs/fits.py` |
| C5 = −38.835(13), b drift, blind tests, calibration, Wc limit | `residual_log/large_L/fits/c5_fits300.txt`, `residual_log/fits/parent_check_largeL/refit_c5_300.txt` | `large_L/c5_fits300.py`, `refit_c5_300.py` |
| optimized engine regression, L = 300 assembly | `residual_log/large_L/results/regression_opt.txt`, `compare_c5_L300_vs_L200.txt` | `large_L/lib_opt/regress_opt.py`, `large_L/compare_c5.py` |
| ε² descendant identities (W) | `complete_exact/results/descendant_fits.txt`, `descendant_summary.md` | `complete_exact/descendant_fits.py` |
| ε³ identities (Wcs vs Wc), φ² descendants | `residual_log/fits/parent_check_wcs/{verify,fits,r3zero,blind16}.txt` | `parent_check_wcs/*.py` |
| partial ε⁴ χ-line window (invariances, gaps 95 %/90 %) | `residual_log/fits/parent_check_p5/verify_p5.txt` | `parent_check_p5/verify_p5.py` |
