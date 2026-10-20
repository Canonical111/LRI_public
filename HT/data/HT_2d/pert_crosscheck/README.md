# Consistent-scheme coefficients for the weak-coupling check (d = 2)

`consistent_C0_C8.csv` gives the coefficients C0..C8 of the ε expansion of Δ_E at N = 8, 10, …, 24 (ε = 2 − 4Δσ), in
the consistent-window scheme of the perturbative HT calculation, which is published in `HT_Pert`. It is an extract.
`source` and `source_sha256` name the two tables it comes from:
- N ≤ 20: the perturbative package's reference table,
  `HT_Pert/code/lri_d2_coeff_hpc/reference/lri_d2_perturbative_C8/results/coefficients_C0_C8.csv` (verbatim from
  git f847d38, sha256 ee72158e…);
- N = 22 and 24: the symmetry production table, `HT_Pert/data/HT_2d/prod/prod1_symmetry/coefficients.csv` (verbatim,
  sha256 d86743c1…).

The extract was written by `<PAPER>/notes/public_repo/HT/d2/tools/make_overlays.py`.

Check `d2.pert_consistent` (`make -f public.mk replay` in `HT/code/lri_2d_window_hpc`) compares the finite-coupling
Δ_E(N) with the [4/4] Padé approximant of these coefficients:
- at Δσ = 0.495 they agree to ≤ 9.4e-12;
- at Δσ = 0.475 they agree to ≤ 7.6e-8.

So the finite-coupling model, expanded in ε, is this scheme. The scheme's C4(N) diverges like −(365/(4374π)) ln N; that
result is in `HT_Pert`, check `p2.c4_log_consistent` (`make -f public.mk replay` in
`HT_Pert/code/lri_2d_coeff_independent_check`).
