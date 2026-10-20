# lri_3d_c4_exact: exact finite-cutoff sums of the d = 3 perturbative Hamiltonian truncation

This package computes the coefficients C_n(L), n = 2..5, of the thermal gap of the d = 3 long-range Ising fixed point
in the level-cutoff Hamiltonian truncation exactly, as sums over intermediate states (diagram sums with exact
partial-wave reductions on S^2 and exact zero-mode projections), for every even cutoff L up to L = 600 (C2..C4) and
L = 40 (C5), with the window corrections to L = 8000. The model is that of the production package `lri_3d_hpc` (same
Hamiltonian, cutoff and tuning); at L <= 20 the two agree to about 1e-13.

    Delta_E(eps; L) = 3/2 - eps/6 + sum_{n>=2} C_n(L) eps^n,   eps = 2s - 3,   Delta_phi = (3 - eps)/4.

The paper quotes, in d = 3 (Table 2, `tab:htpert`, Sec. 3.1; final commit `a6772872`), the extrapolated limits:

| | value | delta = abs(C^HT/C - 1) | from |
|---|---|---|---|
| C2(3) | 0.181221785405554 | 15 digits | fit to L <= 8000 |
| C3(3) | -0.353581479(20) | 1e-7 | fits to L <= 600, three windows |
| C4(3) | 1.228070(21) | 5e-6 | complete window W, tower T4, 12 fit windows to L <= 600 |
| C5(3) | -6.0 +- 0.3 (provisional, so marked in the caption) | 3e-2 | window Wc, L <= 40 |

The complete window W (vacuum window, full zero-mode window including the zero-mode-number-changing part, and the
chi-attached sunset window) was derived in d = 2 and is applied unchanged; without it, the truncation diverges at
order eps^4 (uncorrected like L^2, with the vacuum window alone like L and sqrt(L) ln L). Fit forms and windows were
chosen after the data were seen, with the continuum values known; the chi window is used in its leading-order linear
form, which is not derived for d = 3. `results_map.md` lists every number with its check and tolerance.

## Quick start

```
make -f public.mk replay     # every quoted number from the shipped exact sums (numpy; about 2 s)
make -f public.mk test       # recompute the sums at small L and compare (1-3.5 min on one node)
```

`replay` reruns the package's own analysis scripts (`fits_c4.py`, `eps5/fits5.py`, `eps5/t3.py`) on the shipped
results, recomputes each quoted number with its rule and repeats the validation against `../lri_3d_hpc` and its
campaign records (`../../data/HT_3d/pert3d/results`). `test` recomputes the sums from scratch at small cutoffs.

## What is where

| Path | Contents |
|---|---|
| `c4lib3d.py`, `c4_compute3d.py`, `c4_run3d.py` | the C2..C4 engine: mode tables, partial-wave bundle sums, exact zero-mode projections, assembly, production driver |
| `windows3d.py`, `offdiag3d.py`, `dchi3d.py` | the window shifts (vacuum, zero-mode diagonal and off-diagonal, chi-attached sunset), cancellation-free, to L = 8000 |
| `eps5/` | the eps^5 engine (`engine.py`; model-independent modules ported from the d = 2 package), production `prod5.py`, shifts `delta5.py`, leg response `legw3d.py`, brute force on the package operators `brute3d_*.py`, validation, analysis `fits5.py`, `t3.py` |
| `fitlib3d.py`, `fits_c4.py`, `fits/` | asymptotic fits; `fits/fit_summary.txt` (C2..C4), `fits/fits5_summary.txt` (C5), `fits/t3_summary.txt` (descendant identity) |
| `results/` | the production results (npz: C_n, r, g, energies, window shifts per L; json: brute force), regression logs |
| `brute_zm.py`, `validate_pkg.py` | brute force with the package's reference solver; comparison with the package |
| `C4_by_L.csv` | C2, C3, C4 in every scheme at every even L <= 600 |
| `README.md` | the package's own README (derivation, validation, results, cost); Sec. 7 is the eps^5 part |
| `public.mk`, `public/` | public targets and documents |

References in the verbatim files to `../../lri_2d_coeff_expanse/...` (for example `README.md` Sec. 2.1 and the
docstring of `eps5/engine.py`) point to the d = 2 counterpart, shipped here as
`HT_Pert/code/lri_2d_coeff_independent_check`.

The package ships at git commit `d5afa4f`. The memory-profiling scripts and the job-log tails are not shipped
(`public/PROVENANCE.md`).
