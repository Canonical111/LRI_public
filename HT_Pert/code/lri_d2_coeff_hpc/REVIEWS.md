# Reviews: lri_d2_coeff_hpc (summary; no raw review logs are shipped)

## Code review of the cluster port (2026-10-08)
The delivered solver (baseline commit 8db8f15 = `lri_2d_coefficients_hpc_optimized.zip`, sha256 94edc677…, an
optimization of `lri_2d_C8_perturbative_check.zip`, kept in `reference/lri_d2_perturbative_C8/`; both written by OpenAI
GPT-6 astra via ChatGPT) was made runnable on SDSC Expanse and the symmetry cluster by a Claude Code session
(commits 0d99d55..f847d38), with OpenAI Codex as inspector (`gpt-6-astra`, effort xhigh). The solver source `src/lri_coeff` was not changed (source digest 550e9266… before and
after); every change is in the cluster layer, scripts, tests and documentation.

| round | findings | fixed in | topics |
|---|---|---|---|
| r1 | 9 (LRI-001..009) | c606cbd | private node-local job directory; staged-source PYTHONPATH; node-local checkpoints with one published archive per task; signal forwarding; site environment scrubbing; validation test count; output reservation across manifests; partition time caps; receipt fields |
| r2 | 5 (LRI-010..014) | 3e2ef17 | read-back of the checkpoint archive before rename, exit 76 for an unpublished newest checkpoint; job names from the output path; loud failure on journal-write errors; refusal of shared graph caches; umask |
| r3 | 3 (LRI-015..017) | f847d38 | digest verification of every checkpoint member (local and read back); retry/reporting of publication errors; output-path job names in dry runs; corruption tests (61 tests) |
| r4 | none | — | **APPROVED at f847d38** |

## Validation on the clusters (release lri2d_coeff-f847d38db8bd.tar, sha256 2e2edf6c…)
- symmetry, job 571623 (amdq, AMD EPYC 7532, 64 threads): 61 tests passed; replay of the archived L = 22 pilot to
  ≤ 1.6e-13 (rtol 1e-10 required). Receipt: `data/HT_2d/prod/prod1_symmetry/validation_571623/`.
- Expanse, job 54765932: the same checks, bitwise equal to symmetry. Receipt:
  `data/HT_2d/prod/prod2_expanse/2e2edf6c3153252b_expanse_54765932/`.

## Independent verification of the numbers (2026-10-08..14)
The finite-cutoff coefficients were checked by codes written without the package (`code/lri_2d_coeff_independent_check`):
a clean-room exact-rational Rayleigh–Schrödinger solver (L ≤ 18, every scheme, all C_n, r_n, g_n, E_p and vacua) agrees
with the production records to 3.9e-13 (scaled), and a clean-room non-perturbative Cauchy-integral solver (L ≤ 8)
agrees with the exact solver to 5e-46 and with the package to 1.6e-14. See that package's REVIEWS.md.

## What the reviews did not cover
The window prescriptions (raw, consistent, literal) are inputs of the delivered package; the reviews and checks verify
that the package computes them correctly, not that they give the continuum coefficients. In d = 2 they do not beyond
ε³ (see the HT_Pert note and `lri_2d_coeff_independent_check`).
