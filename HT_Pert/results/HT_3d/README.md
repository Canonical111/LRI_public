# HT_Pert/results/HT_3d: d = 3 perturbative Hamiltonian truncation

The paper's d = 3 values (Table 2, `tab:htpert`, Sec. 3.1; final commit `a6772872`) come from the exact finite-cutoff
sums of `code/lri_3d_c4_exact`:
C2(3) = 0.181221785405554 (15 digits), C3(3) = -0.353581479(20), C4(3) = 1.228070(21) (complete window of d = 2,
carried over unchanged), and C5(3) = -6.0 +- 0.3 (delta 3e-2; marked provisional in the caption, L <= 40).

- `quoted_numbers.json`: these printed macros with their values, where they are printed and the replay check that
  recomputes each (`make replay` in `code/lri_3d_c4_exact`).

- `replay_exact3d_reference.txt`: the PASS/FAIL table of `make replay` in `code/lri_3d_c4_exact` (14 rows), as
  produced on 2026-10-19 for comparison (the fit summaries regenerate byte-identically on the platform that
  wrote them).
- `SUMMARY.md`: C2..C8 at the level cutoffs L = 16, 18, 20, raw and with the vacuum window only (consistent), from the
  Expanse campaign `pert3d` of the production package `code/lri_3d_hpc`. It was written 2026-10-09 from the result
  records and is shipped byte-identical; `make replay` in `code/lri_3d_hpc` rebuilds every row from
  `HT_Pert/data/HT_3d/pert3d/results` (check TABLE).
  - The exact sums reproduce these values at every even L <= 20, to about 1e-13.
  - They also show that the vacuum-window scheme diverges from order eps^4 on: C4 peaks at 0.759 near L = 32 and is
    -0.75 at L = 600. So these finite-cutoff values are not continuum estimates beyond C3.
  - `HT/code/lri_3d_window_hpc` reads the `| 20 | consistent |` row: C4(20) = 0.7400078407092003721, i.e. 60.26 % of
    C4(3).
