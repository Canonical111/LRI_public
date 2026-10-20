# Independent check of C8(3): the LRI_C8_D3_OPT package

This folder (`GFF/code/LRI_C8_D3_OPT`) holds a separately developed code for the eighth-order coefficient C8(3) of the
thermal dimension of the three-dimensional long-range Ising model, with epsilon = 2s - 3. The paper's value of C8(3)
comes from a different package, `GFF/code/LRI_C8_D3_HPC` (records in `GFF/results/C8_3`). This code was run once at
production size as a cross-check; its result is quoted next to the main value and is not combined with it.

## Result

| quantity | value | record |
|---|---|---|
| C8(3), sampling standard error | **1600.98 +- 3.97** (estimator 1600.9770046710833, SE 3.967937252893955) | `GFF/results/C8_3_check/runs/prod1/C8_result_54838171.json` |
| difference from the main estimator 1602.6052 +- 0.9516 | -0.40 combined standard errors | main record `GFF/results/C8_3/C8_result.json` |
| campaigns a and b (independent seeds and sampler rates 0.8 and 0.7) | 1603.53 +- 4.91 and 1598.42 +- 6.24, pull 0.64 | same result record |
| power-free part and power correction | 1602.61 +- 2.96 and -1.63 +- 2.64 | same |
| lower-order by-products, pulls against the references | C3 -1.41, C4 -1.55, C5 -0.10, C6 33.599 +- 0.014 (+1.73), C7 -220.40 +- 0.19 (-0.21) | same |
| design | 24,173 kernels per campaign, 16 replicates per campaign, at least 4,096 points per graph, 1,994 jobs, 3.71 x 10^10 evaluations | `runs/prod1/manifest.json`, `allocations/prod1_2000.json` |
| cost | about 76.7 node-hours of AMD EPYC 7742 (128 cores), about 9,800 service units, 10 and 11 October 2026 | `GFF/results/C8_3_check/README.md` |

The error is the replicate-sampling covariance propagated through the fixed point. The package itself marks the
result `reportable_precision_established = false`: no allowance for numerical controls was assigned, and there was no
results review of this number (see `REVIEWS.md`). It shares with the main calculation the three-dimensional mixed-forest
kernel and precision policy of the seventh-order integrator, the importance sampler, the digital nets and the finite
renormalization scheme; an error in those shared parts would not be detected by this comparison. It regenerates the
graph inputs, derives its own low-loop inputs (its `inputs/two_loop.json` differs from the main package's), extends the
regulator jets and solves the eighth-order fixed point with its own assembly (`tools/rg.py`, `tools/assemble.py`).

## Quick start

```sh
cd GFF/code/LRI_C8_D3_OPT
pip install -r public/requirements.txt     # numpy, scipy, mpmath (sympy, pynauty only for regeneration)
make -f public.mk replay                   # about 3 s, any OS: every quoted number, PASS/FAIL table, exit 1 on FAIL
make -f public.mk test                     # Linux x86-64 node with GCC, GMP, Boost headers: build and package tests, 2-3 min
make -f public.mk test-py                  # the Python-only tests, seconds, any OS
```

`make replay` needs only files in git: the result record stores, per loop (3 to 8) and sector (power-free and
power-containing), the pooled replicate means and the covariance of those means. The replay recomputes the estimator
and its standard error from them with the package's own fixed-point code and covariance propagation, runs the package's
`assemble.calculate()` on replicate matrices with exactly those moments, recomputes the two campaign values from the
per-graph statistics, the job and evaluation counts from the allocation by the planner's rule, and checks every hash
binding between records and code. Its table is in `.work/replay/replay_report.txt`; the rows and tolerances are
described in `REPRODUCE.md`. The native outputs of the campaign (per-job checkpoints) are not shipped.

## What is here

- The package as it ran in production (git commit `d5deeb9`), verbatim: `src/` (native worker), `tools/` (planner,
  dispatcher, assembly, fixed point, allocation, graph generation and audits), `tests/`, `slurm/` and `tools/submit.py`
  (the site layer used on Expanse; it encodes one user's allocation and caps), `docs/` (numerics, HPC and cluster
  runbooks), `reference_c7/` (C7 regression fixtures), `baseline/` (the unoptimized worker for the regression
  test), `verification/` (the delivered evidence), `inputs/` (analytic jets, the active-graph inventory, the coverage
  certificate, the delivered pilot design) and `SHA256SUMS`.
- `inputs/free/` and `inputs/power/` hold only 179 of the 24,173 graph payloads: the fixtures read by
  `tests/test_optimization.py` and `tests/check_c8_points.py`. The full set (9.15 GB) is hosted (`make -f public.mk
  fetch-data`; `GFF/data/C8_3_check/DATA.md`).
- `public/` (new, not part of the package): `replay_check.py`, `README.md`, `REPRODUCE.md`, `PROVENANCE.md`,
  `REVIEWS.md`, `requirements.txt`, the Slurm templates `slurm/` for a production rerun, and
  `make_data_bundles.sh` with `data_bundles.sha256` for the hosted bundles. `public.mk` holds the targets.
- Not shipped: `DELIVERY_MANIFEST.json`, `regeneration/` and `inputs/complete_inventory_L*.json` (hosted, for graph
  regeneration only), and the TeX notes named in `public/dropped_paths.txt`: the code author's derivation and
  calculation notes (`derivation.tex`, `docs/DERIVATION.tex`, `docs/C8_3D_calculation.tex` and `.pdf`) and
  `reference_study/` (an earlier version of the condensed note given to the code's author). The derivation of this
  check is in the condensed note (`GFF/note/`), Section 32.7 ("An independent code"); the package's own `README.md`
  still names the notes. `tools/write_report.py` reads `docs/DERIVATION.tex`; it ships verbatim and no public target
  runs it. Also not shipped: the
  delivered pilot's raw checkpoints (hosted), compiled binaries, the port's plan, review transcripts, logs and
  admission ledgers (summarized in `REVIEWS.md` and `PROVENANCE.md`).

The package's own `README.md` describes the code as delivered, including its pilot (C8(3) = 1514.6 +- 161.7 from
16-point nets, an exploratory estimate superseded by the production). Its build instructions name GCC 13.3 / 14.2,
Boost 1.77 / 1.83 and GMP 6.3; the production build used GCC 13.3.0, Boost 1.77 and GMP 6.2.1.

## Known limitations

1. Sampling error only. No reporting allowance, no tail or convergence campaign beyond the a/b and half-stream
   splits, and no results review of the number.
2. Shared method: the comparison with the main result cannot detect an error in the shared kernel, sampler, nets or
   renormalization scheme.
3. The production commit `d5deeb9` contains one uninspected admission change; the two later fix commits (`3961865`,
   `6edcc9e`) change only the admission layer and are not shipped (`REVIEWS.md`).
4. The native worker builds only on x86-64 Linux (`__float128`, libquadmath). A rerun with a fresh seed reproduces the
   estimate statistically, not bit for bit; `make test` checks the worker against fixed-input regressions.

Licence: TBD (the package carries no licence of its own). Citation: the paper.
