# Reproducing the d = 3 exact-sum numbers (lri_3d_c4_exact)

Run everything from `HT_Pert/code/lri_3d_c4_exact` with relative paths. The sibling `../lri_3d_hpc` (the production
package; its reference operators and reference results) and `../../data/HT_3d/pert3d/results` (its campaign records)
must be present, as they are in the repository. Order: environment, `test`, `replay`, production.

## 1. Environment

Python >= 3.10 with numpy, scipy, numba and mpmath (`public/requirements.txt`); `replay` needs only numpy. Production:
CPython 3.12.9, numpy 2.5.3, scipy 1.17.0, numba 0.68.0, mpmath 1.3.0 on the symmetry cluster; the analysis scripts
(fits) ran on a personal desktop. Caches (numba, the engine's task cache) go to node-local temporary storage.

## 2. `make -f public.mk test` (1-3.5 min, 0.25 GB, up to 8 worker processes)

`public/run_tests.py` recomputes the sums from scratch at small cutoffs and compares (scaled difference
|a - b| / max(1, |b|)):

| Stage | Recomputes | Compared with | Tolerance |
|---|---|---|---|
| windows | `windows3d.py --Lmax 400` | `results/windows_L8000.npz` | 1e-12 |
| offdiag | `offdiag3d.py --Lmax 200` | `results/offdiag_L400.npz` | 1e-12 |
| dchi | `dchi3d.py --Lmax 120` | `results/dchi_L120.npz` | 1e-10 (r2, about 10 in size, summed on another platform: 2e-11) |
| c4 | `c4_run3d.py --Lmax 40` | `results/c4_L600.npz` | 1e-9 (production at Lmax = 600, other angular quadrature) |
| c4_vs_pkg | `validate_pkg.py` on it | the package, L <= 20 | 1e-12 |
| c5 | `eps5/prod5.py --Lmax 12`, every scheme | `results/c5_L20.npz` | 1e-12 |
| c5_vs_pkg | `eps5/validate5.py` on it | the package (L <= 12), the brute force (`results/brute`) | 1e-12 |
| delta5, legw | `eps5/delta5.py --Lmax 20`, `eps5/legw3d.py --Lmax 40` | `results/dC5_L200.npz`, `results/eps5/legw_L400.npz` | 1e-11 |
| brute_W5 | `eps5/brute3d_W5.py --L 4` (package operators, explicit windows) | `results/brute/brute_L4.json` | 1e-12 |
| brute_zm | `brute_zm.py --cutoffs 0 2 4` (package reference solver) | `results/brute_zm_L6.json` | 1e-12 |

Measured on the symmetry cluster (2026-10-14; Python 3.12.9), 11/11 stages passed in each run:

| Job | Node | Stack | `make test` |
|---|---|---|---|
| 575156 | Intel Xeon Gold 6148 | numpy 2.5.3, scipy 1.17.0, numba 0.68.0 | 74 s |
| 575157 | AMD EPYC 7532 | numpy 2.3.5, scipy 1.16.3, numba 0.62.1 | 83 s |
| 575158 | AMD EPYC 7532 | numpy 2.5.3, scipy 1.17.0, numba 0.68.0 | 67 s |
| 575159 | Intel Xeon Gold 6148 (8 of 40 cores, shared node) | numpy 2.3.5, scipy 1.16.3, numba 0.62.1 | 197 s |

## 3. `make -f public.mk replay` (about 3 s, numpy only)

`public/replay_exact3d.py` copies the package to `.work/replay/pkg`, reruns `fits_c4.py`, `eps5/fits5.py`, `eps5/t3.py`
on the shipped results, recomputes every quoted number with the rule in `results_map.md`, and repeats the validation
against the package. 14/14 passed on the four nodes above and on a personal desktop (numpy 1.24).

Platform note: `fits/fit_summary.txt` is reproduced byte for byte on the platform that wrote it (a personal desktop).
On the cluster, nine lines differ in their last digits: ill-conditioned subleading coefficients of the window-shift
fits, the C2 fit at the 1e-16 level, and the C3 fit with Lmin = 300, which moves by about 1e-9. None of these changes a
quoted number beyond its stated uncertainty. The C3 central value moves by at most 3e-10 against its uncertainty of
2e-8, and on some platforms its ninth decimal rounds to -0.353581480. The replay therefore checks the quoted lines with
stated tolerances (FITS-QUOTED) and the C3 central value to 1/10 of its uncertainty.

## 4. Production rerun

All on the symmetry cluster. Times are for one node or for an 8-core share of one; the jobs are listed in
`PROVENANCE.md`.

```
python3 c4_run3d.py --Lmax 600 --workers 20 --threads 2 --cache <node-local> --out results/c4_L600.npz      # 33 min, one node
python3 windows3d.py --Lmax 8000 --out results/windows_L8000.npz; python3 offdiag3d.py --Lmax 8000 --out results/offdiag_L8000.npz
python3 dchi3d.py --Lmax 1000 --out results/dchi_L1000.npz
python3 fits_c4.py                                                                                          # seconds; writes fits/fit_summary.txt
cd eps5
python3 prod5.py --Lmax 20 --workers 8 --cache <node-local> --out ../results/c5_L20.npz                     # every scheme; ~10 min x 4 shards (--shard)
python3 prod5.py --Lmax 40 --raw_only --workers 20 --cache <node-local> --out ../results/c5raw_all_L40.npz  # 1 h 45 min, one 80-thread node, ~6 GB per worker
python3 delta5.py --Lmax 600 --workers 8 --cache <node-local> --out ../results/dC5_L600.npz                 # 3 h, 8 cores
python3 legw3d.py --Lmax 400 --out ../results/eps5/legw_L400.npz
python3 fits5.py; python3 t3.py                                                                             # seconds
```

Memory grows like L^4.5 in the 7-line parallel merges of `prod5.py` (about 6.3 GB per worker at L = 40, 18 GB at
L = 56), and the cost grows like L^8.4. Going beyond L = 40 needs a new angular-channel representation (README Sec. 7.5).

## Decisions you must not make

- The windows: the complete window W for C4 and Wc for C5, as defined in the d = 2 package and applied unchanged.
  The chi window stays in its leading-order linear form.
- The extrapolation rules: tower T4 and the 12 fit windows for C4 (value = median, uncertainty = half-range including
  the blind fit); the mean and half-range of the three windows for C3; for C5, towers A and D with the calibration on
  C4^W (provisional; Table 2 of the paper marks it so in its caption). PDG rounding.
- The continuum values the deviations are measured against are those of the paper's Table 1 (`tab:pt`).
