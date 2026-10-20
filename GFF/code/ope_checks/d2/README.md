# Checks of the bulk one-point coefficient at d = 2

These scripts check the two-dimensional statements of Section 34 of the note. That section covers the bulk one-point coefficient a_phi2 of :Phi^2: through eps^6, with its d = 2 subsection, the d = 2 rows of the bootstrap comparison and the five-loop item of the checks list. They were written for the note and do not reuse the code of `GFF/code/lri_ope_reproducibility`. Every d = 2 input comes from the note's closed forms or from this repository's own production records. The checks are internal to the shared graph and master-integral framework; they do not rederive the six-vertex calculation.

`make -f public.mk replay` in `GFF/code/lri_ope_reproducibility` runs the commands in `commands.json`: the first three rows of the table below. Each command passes if it exits 0. Python 3.11 or newer is required, with mpmath 1.3.0, sympy 1.14.0 and numpy 2.3.5.

| Script | What it checks | Inputs | Runtime | Recorded output |
|---|---|---|---|---|
| `ope_d2_check.py` | 18 exact identities (sympy) and 60-digit numerics. The exact identities are: the elimination of Q_2 and P_4(2) through C_3(2) and C_4(2); the closed d = 2 log map; the general log map at d = 2; the d = 2 form of 13Z_2 - L_2 - 12K_2; the external-leg ratio; the two forms of C_5(2); and the exact a^(3)..a^(6)(2). The numerics are: the masters from the closed forms; a^(2)..a^(6)(2); and the Borel-Pade rows at (Delta_phi, eps) = (0.425, 0.3), (0.35, 0.6), (0.275, 0.9) and (0.2, 1.2), including the diagnostic [5/3] through C_8(2). It exits 1 if an exact identity fails. | none | about 15 s | `ope_d2_check.json` |
| `ms_b5_from_jets.py` (order 8) | The constant-coefficient (minimal-subtraction) b_3, c_3, b_4, c_4, b_5, c_5 at d = 2, from the finite-scheme Taylor jets of the eighth-order production, against the formulas of Section 34. Errors are propagated linearly from the replicate covariance. With `--expect` it exits 1 unless every value and standard error reproduces the recorded output to 1e-9 relative. | `GFF/data/C8_2/prod1-.../groups`, `GFF/code/LRI_C8_D2_HPC/inputs/two_loop.json` | about 20 s | `ms_b5_c8d2.json` |
| `ms_b5_from_jets.py` (order 7) | The same, from the seventh-order production. | `GFF/data/C7_2/run1-20260930-m4096/groups`, the same two-loop input | about 20 s | `ms_b5_c7d2.json` |
| `check_fig7.py` | The kinks and the authors' Pade points of Figure 7 of Behan, Lauria, Nocchi and van Vliet (arXiv:2311.02742v6), read from the vector paths of the figure file. | an SVG made with `pdftocairo -svg fig/plot_pade_comparison.pdf` from the arXiv source of 2311.02742v6; the figure itself is not shipped | under 1 s | `check_fig7.json` |

`check_fig7.py` is not in `commands.json`, because its input is not shipped.

The recorded runs were made on the symmetry cluster (Intel nodes, sharedq partition) with Python 3.11.3, mpmath 1.3.0, sympy 1.14.0 and numpy 2.3.5. The JSON files above are those runs' outputs. All numbers are coefficients or diagnostics of a finite-order calculation, not error bounds. The spread between Borel-Pade prescriptions is not an uncertainty, and the kink readings are not bootstrap data.
