# lri_3d_hpc: perturbative Hamiltonian truncation in d = 3 (C_2 to C_8 at finite level cutoff L)

This package computes the finite-cutoff coefficients C_n(L), n = 2..8, of the thermal gap of the long-range Ising
fixed point in d = 3 from the truncated Hamiltonian, by Rayleigh-Schroedinger perturbation theory on formal power
series (no Feynman graphs, nothing fitted):

    Delta_E(eps; L) = 3/2 - eps/6 + sum_{n>=2} C_n(L) eps^n,   eps = 2s - 3,   Delta_phi = x = (3 - eps)/4.

The model is the generalized free field on S^2 (modes (n, l, m), level 2n + l), H = H0 + r M + g V with
M = int dOmega :phi^2:/(4 pi), V = int dOmega :phi^4:/(48 pi); the bath (nonzero modes) is cut at
N_b = sum (2n + l) <= L, the zero mode (the local oscillator) is not truncated. r and g are tuned order by order to
the exact dimensions of phi and phi^3. Two prescriptions: `raw` (no window) and `consistent` (the vacuum window
D_L(l) = E_v(L) - E_v(L - l), the only window this package implements).

Since 2026-10-14 the paper's d = 3 values come from the exact finite-cutoff sums of `../lri_3d_c4_exact`, which use
the complete window of d = 2. This package's finite-cutoff results remain part of the release:
- they are the independent code against which the exact sums are validated: C2..C5, r, g and the seed energies agree
  at every even L <= 20, to 3e-13 or better;
- `HT/code/lri_3d_window_hpc` reads C4(20) of the consistent scheme from `HT_Pert/results/HT_3d/SUMMARY.md` (60 % of
  C4(3));
- the HT_Pert note shows them as a table.
An earlier draft of the paper quoted the ratios C_n(20)/C_n (0.995, 0.933, 0.603, 0.577, 0.507, 0.414, 0.378) and
the L = 14 agreement with the original code (about 1e-14); `make replay` still recomputes them (`results_map.md`).
The exact sums show that the consistent scheme diverges from order eps^4 on, so these values are finite-cutoff
quantities, not continuum estimates beyond C3.

## Quick start

```
make -f public.mk replay     # every quoted number from the shipped records (standard-library Python, ~1 s)
make -f public.mk test       # the package's checks + an L14 store built from scratch vs the original code
make -f public.mk smoke      # the shipped L4 fixture against the original code at 1e-16 (seconds)
```

`replay` reads `../../data/HT_3d/pert3d` (the production records, byte-identical) and `../../results/HT_3d/SUMMARY.md`.
`test` needs Linux x86-64 (80-bit long double), a C++17 compiler with OpenMP and Python 3.12 with numpy, scipy,
numba, threadpoolctl (`public/requirements.txt`); see `public/REPRODUCE.md` for the measured runtimes.

## What is where

| Path | Contents |
|---|---|
| `code/` | the optimized solver: Taylor vertices, stationary energy series, native C++/OpenMP kernels, MPI backend, vertex store |
| `reference/`, `vendor/ht3d/` | the original implementation and its SO(3) basis machinery, unchanged (the "original code" of the note's L = 14 check) |
| `results/reference_coefficients_L14.json` | the original code's results for every even L = 0..14, both schemes, C_0..C_8, r, g and all energy series |
| `fixtures/vertices_L4/` | a small vertex store for the smoke test |
| `tests/` | the package's checks (run by `public/run_tests.py`) |
| `hpc/` | generic Slurm examples of the supplied package |
| `cluster/` | the Expanse/symmetry layer that ran the production campaign (`cluster/RUNBOOK.md`): staged releases, validation receipts, stage runner, submit wrapper |
| `docs/` | `NUMERICS.md` (exact stationary reformulation, precision contract), `VERTEX_CONSTRUCTION.md`, `PERFORMANCE.md` |
| `benchmarks/`, `results/*.json` | the supplier's measurements and validation records (not used by the public targets) |
| `README.md`, `RELEASE_MANIFEST.json` | the package's own README and file manifest (sha256 of every file; checked by `make test`) |
| `public.mk`, `public/` | public targets and documents (this README, `REPRODUCE.md`, `PROVENANCE.md`, `REVIEWS.md`, `results_map.md`) |

The package's own files ship unchanged at git commit `7c8a67e`, the release the production campaign ran. In
`cluster/RUNBOOK.md` the authors' cluster paths are replaced by placeholders (`public/SCRUBBED.txt`).
