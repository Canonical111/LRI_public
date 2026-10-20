# lri_2d_coeff_independent_check: the d = 2 perturbative HT coefficients, checked and extended

This folder is the independent check of the d = 2 coefficient solver (`../lri_d2_coeff_hpc`) and the work that
followed it: exact finite-cutoff coefficients C2(L)..C5(L) at large cutoff, the window corrections that make C4 and
C5 converge to the continuum, and the descendant identities that test those windows without continuum input. Every
d = 2 perturbative-HT number of the paper and of the d = 2 section of the HT_Pert note is recomputed from the files
here (and from the production records in `../../data/HT_2d/prod`) by `make -f public.mk replay`.

It is a **snapshot** (2026-10-14) of a working tree that was never a git repository. `public/SNAPSHOT.sha256` lists
every shipped file with its sha256 as exported; `make -f public.mk verify-snapshot` checks it. The files of the
snapshot are verbatim, including the READMEs of the subfolders, which carry dated status lines from the time they were
written; this README and `REVIEWS.md` are the current description, and the derivations are in Appendices A to C of the HT_Pert note (`../../note/`). Where they
differ, the replay (`public/replay_p2.py`) and the HT_Pert note are authoritative.

## The model and conventions
`SPEC.md`: GFF on the unit circle, x = Δφ = 1/2 − ε/4, mode weights (x)_a(x)_b/(a! b!), M = ⟨:φ²:⟩, V = ⟨:φ⁴:⟩/12,
level cutoff N ≤ L (the paper's L), J = 0 reflection-even sectors, tuning E1 − E0 = x and E3 − E0 = 2 − x,
Δ_ε = E2 − E0 = Σ C_n ε^n, ε = 2s − 2. Continuum values: `continuum/reference_values.csv` (C2..C5 exact,
C6..C8 numerical, from the condensed note).

## Layout (what each part is for)
| folder | content | used for |
|---|---|---|
| `rs_exact/` | clean-room Rayleigh–Schrödinger solver in exact rationals (Fraction reference + multi-modular), L = 0..18, raw/consistent/literal schemes; `results/*.json` | `\HTpTwoImplAgree` (vs the production records), check of every other code |
| `cauchy/` | clean-room non-perturbative solver: truncated H at complex ε on a circle (256-bit), Cauchy integrals, L = 0..8; `results/*.json` | agreement with rs_exact (5e-46) and the package (1.6e-14) |
| `compare_with_package.*`, `compare_three_way.*` | the original comparison scripts and outputs (absolute base path inside; `public/replay_p2.py` redoes both with relative paths) | HT_Pert note Sec. 4.2, App. A.2 |
| `continuum/` | exact C2(L), C3(L) code (`exact_low_orders.py`), its table to L = 600, asymptotics (`asymptotics_C2_C3.*`) | `\HTpCtwoTwo` (35 digits), `\HTpCthreeTwo`, κ |
| `c4_exact/` | exact fourth-order cutoff sums: C4(L) to L = 2000 in the raw, consistent and zero-mode schemes (`results/c4_L2000.npz`), exact window shifts to L = 20000, fits, the blind L = 2000 test, validations against rs_exact, the package and zeromode_exact | `\HTpTwoLfour`, `\HTnpDtwoCfourLog`, the C4 scheme table of the note |
| `zeromode_exact/` | exact-rational solver of the zero-mode window scheme, L ≤ 18 | validation of `c4_exact` |
| `complete_exact/` | exact-rational solver of the complete window W through ε⁸ (L ≤ 16) and the descendant channels | ε² descendant identities (`[ε²]v_n`, HT_Pert note Sec. 4.6) |
| `residual_log/` | the derived complete ε² window (zero-mode Bloch + χ-line mass window) at large L (`offdiag_window.py`, `nm_window.py`, `C4W_by_L.csv`), the window specification `WINDOW_SPEC.md`, exact C5(L) (`eps5/` engine; `large_L/lib` = the same engine as run, `large_L/lib_opt` = the optimized engine), the ε⁵ window shifts (`results/eps5/dC5_L1000_all.npz`), the leg response S(L) (`results/legw`), the ε³ external-line window δ⁽³⁾(L) to L = 16000 (`large_L/tagchan.py`, `large_L/results/tag3_L16000.npz`), the exact all-order window solver `ce_wc/` (schemes Wc, Wcs, Wcs4X; L ≤ 16), the parent checks `fits/parent_check_*` | `\HTpCfourTwo`, `\HTpCfiveTwo` (+Dev, Log), `\HTpTwoLfive`, `\HTpTwoIdentThree`, the C5 and ε³/ε⁴ numbers of the note |
| `public/` | replay, tests, snapshot list, Slurm templates (new files, not part of the snapshot) | |

## Results in brief (each is a replay check, `results_map.md` of the HT_Pert d = 2 entries)
- The production solver is correct for the model as defined: exact-rational RS agrees on every C_n, r_n, g_n, E_p and
  vacuum coefficient (25 scheme/cutoff pairs) to 3.9e-13; the Cauchy solver agrees with RS to 5e-46.
- C2(∞) = 4 log 2/9 to 35 digits; C3(∞) = −0.8748500(1) (exact −0.87485001265).
- C4: every scheme of the package diverges (raw linearly, κ = 2.2073e-4; consistent and zero-mode like ln L, with
  coefficients −365/(4374π) and −8/(243π)). With the derived complete window W, C4(L) has no ln L and
  C4(∞) = 5.0488682(10) (exact 5.04886843).
- C5: with nested windows referred to the outer cutoff (Wc) and the ε³ external-line window (Wcs; δ⁽³⁾ → −4/(81π)),
  exact C5(L) to L = 300 extrapolates to −38.835(13) (exact −38.8336459). A residual b ln L with |b| ≲ 0.01 is not
  excluded at L ≤ 300; it would move C5 by about 0.1.
- Descendant identities: W restores them at ε²; Wcs removes at least 95 % of the ε³ violation of single-quantum
  descendants at L ≤ 16 (all of it as L → ∞); the ε³ identities of the φ² descendants are not settled at L ≤ 16; the
  ε⁴ window is only partly known (Wcs4chi). C6..C8 are not reproduced in d = 2.

## How to run
See `REPRODUCE` of the HT_Pert d = 2 entries; in short (from this folder):
```
make -f public.mk replay        # every p2.* check, seconds (numpy, mpmath)
make -f public.mk replay-full   # rerun the shipped fit scripts on a scratch copy, compare outputs (~1 min)
make -f public.mk test          # small-cutoff reruns of every code vs the shipped outputs (~2-3 min; numba, scipy, python-flint)
```
Several codes import siblings by relative path (`residual_log/eps5` and `large_L/lib*` take `RS_EXACT_DIR`, default
`../../rs_exact`, which from `large_L/lib*` must be set explicitly: `RS_EXACT_DIR=<this folder>/rs_exact`). Scripts that
read the production records expect them at `../results/<campaign>/d8` relative to this folder (the source layout); in
the public tree they are at `../../data/HT_2d/prod/<campaign>/d8`.
