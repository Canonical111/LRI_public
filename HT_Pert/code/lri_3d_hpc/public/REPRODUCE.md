# Reproducing the d = 3 perturbative HT numbers (lri_3d_hpc)

Run everything from `HT_Pert/code/lri_3d_hpc` with relative paths. Order: environment, `test`, `replay`, the small
validation run, production.

## 1. Environment

- `replay`: Python >= 3.9, standard library only, any OS.
- `test`, `smoke` and production: Linux x86-64 (the arithmetic is x87 80-bit long double; other long-double formats
  are refused), a C++17 compiler with OpenMP (`CXX`, default `c++`), Python 3.12 with `public/requirements.txt`
  (numpy, scipy, numba, threadpoolctl). The production stack was CPython 3.12.9, numpy 2.5.3, scipy 1.17.0,
  numba 0.68.0, llvmlite 0.50.0, g++ 13.3.0; `cluster/requirements.lock` pins it with hashes.
- The compiled kernel library and the numba cache are built in node-local temporary storage (`TMPDIR`), as in
  production. On a parallel file system the library's atomic publish can fail (BeeGFS: `EBUSY`); do not point
  `HT3D_NATIVE_CACHE` there.

## 2. `make -f public.mk test` (about 2 min, 1 GB, 4 threads)

`public/run_tests.py`: the package's own checks as the production validation receipt ran them, without the
site-specific stages:

1. every file against `RELEASE_MANIFEST.json`, the files in `public/SCRUBBED.txt` excepted;
2. `tests/check_*.py`: native kernels, stationary against recurrence energy series, optimized against reference solver
   (cutoffs 0, 2, 4, orders 2..8), banded local products, vertex store, the stage driver on the L4 fixture;
3. the shipped L4 fixture solved in both schemes against the original code at 1e-16;
4. an L = 14 vertex store built from scratch and solved at every even cutoff 0..14, both schemes, both strategies
   (32 cases), against the original code's results within 5e-13 and with every recursion residual <= 1e-16.
   This reruns the L = 14 check that the HT_Pert note quotes for d = 3 (about 1e-14).

`MPIEXEC=<launcher taking -n N> make -f public.mk test` adds the 2- and 4-rank MPI tests (mpi4py built against the
site MPI; not part of the default target).

Measured on the symmetry cluster (2026-10-14, the simulated export of this folder, 12/12 stages passed in each):

| Job | Node | Stack | `make test` | L14 grid vs original code | recursion residual |
|---|---|---|---|---|---|
| 574907 | Intel Xeon Gold 6148 | production (numpy 2.5.3, scipy 1.17.0, numba 0.68.0) | 106 s | 6.6e-17 | 6.9e-18 |
| 574908 | Intel Xeon Gold 6148 | numpy 2.3.5, scipy 1.16.3, numba 0.62.1 | 127 s | 6.6e-17 | 6.9e-18 |
| 574909 | AMD EPYC 7532 | numpy 2.3.5, scipy 1.16.3, numba 0.62.1 | 112 s | 1.16e-14 | 1.4e-17 |
| 574910 | AMD EPYC 7532 | production | 92 s | 1.16e-14 | 1.4e-17 |

All used Python 3.12.9 and g++ 11.4, with peak memory about 1 GB. The difference between Intel and AMD, about 1e-14,
comes from the float64 SO(3) projector (BLAS, libm). It is the same as in production: the Expanse stores differ from
the reference by up to 1.25e-14.

## 3. `make -f public.mk replay` (about 1 s)

`public/replay_pert3d.py` recomputes every quoted number from the shipped records (`results_map.md`): the integrity of
the records and of the chain code -> store -> gate -> solve -> result, the table `HT_Pert/results/HT_3d/SUMMARY.md`,
the ratios C_n(20)/C_n (n = 2..8), the 60.26 % C4 ratio read by `HT/`, the L = 14 gates (recomputed from the gate
records and the reference file), the L = 16 recurrence crosscheck and the cross-store check. It prints a PASS/FAIL
table (17 rows), writes it and `ratios_L20.csv` to `.work/replay/`, and exits 1 on any FAIL. 17/17 passed on all four
nodes above.

## 4. Small validation run (`make -f public.mk smoke`, seconds)

The shipped L4 fixture, consistent scheme, against the original code at 1e-16. Before using cluster time, also build
and solve one small cutoff by hand:

```
python3 code/ht3d_coefficients.py build --cutoff 12 --order 8 --store .work/stores/L12 --spill .work/spill
python3 code/ht3d_coefficients.py solve --store .work/stores/L12 --cutoff 12 --order 8 --scheme consistent \
  --threads 4 --output .work/C8_L12.json --compare-reference results/reference_coefficients_L14.json
```

## 5. Production rerun (L = 16, 18, 20)

The production ran through the package's two-site layer, `cluster/` (`cluster/RUNBOOK.md`), on SDSC Expanse. That
layer has staged and authenticated releases, a validation receipt per node class, campaigns frozen to a release and an
environment, a restartable stage runner (prepare, images, matrix, finalize, verify, gate, solve, crosscheck) and a
submit wrapper. The same layer was validated on the symmetry cluster. For other sites, `hpc/` has the supplier's
generic Slurm examples (not used in production), and `public/slurm/test.slurm` runs `make test` on one node.

Measured cost of the production campaign (Expanse AMD EPYC 7742; per stage, from `HT_Pert/data/HT_3d/pert3d/records`):

| L | scalar bath states | store | prepare (projector) | images (sum) | matrix (sum; peak) | solve per scheme | job, request | charge |
|---|---|---|---|---|---|---|---|---|
| 16 | 15,815 | 2.6 GiB | 6.4 min, 1.5 GiB | 36 min, 0.8 GiB | 12 min; 3.4 GiB | 16 s, 3.9 GiB | 18.5 min on 16 cores, 32 GB | about 10 SU |
| 18 | 55,859 | 22 GiB | 13.5 min, 7.3 GiB | 28 min, 4.7 GiB | 69 min; 26 GiB | 73 s, 31 GiB | 36 min on 64 cores, 200 GB | about 60 SU |
| 20 | 196,585 | 177 GiB | 10.0 h, 39 GiB | 42 min, 32 GiB | 15.2 h; 209 GiB | 546 s, 244 GiB | 10.2 h on 64 cores, 200 GB, then 3.4 h on 64 cores, 1700 GB (large-shared) | about 2480 SU |

In total, about 2550 SU. The L = 20 projector is the bottleneck: 9.9 h with 77 gesdd -> gesvd fallbacks, all
repaired. L = 22 is not feasible this way: it needs about 18 times the SVD work and about 1.5 TB per k = 4 matrix task.
Ask before spending more than this.

## Decisions you must not make

- The quoted scheme is `consistent`, the vacuum window D_L(l) = E_v(L) - E_v(L - l). Order 8, x87 long double, nz = 10
  local states per parity. `raw` is shipped for comparison only.
- Acceptance: gates against `results/reference_coefficients_L14.json` at 5e-13 (scaled error over C, r, g, all seed
  energies and subcutoff vacua); recursion residual <= 1e-16; crosscheck <= 1e-15. These are the production
  tolerances.
- The denominators of the ratios are the paper's Table 1 values (`tab:pt`; `GFF/note/README.md`): C2..C5 exact, C6..C8 the
  reported estimators. The ratios are rounded to 3 decimals.
- No extrapolation from this package: three cutoffs and no complete window. The paper's extrapolated d = 3 values come
  from `../lri_3d_c4_exact`. Do not add one here.
