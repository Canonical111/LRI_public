# lri_1d_c4_exact — exact finite-cutoff C4(Λ) of the d = 1 LRI Hamiltonian truncation

Plan, acceptance criteria and method: `PLAN.md` (Codex-approved round 3, sha256 a6373014…); review log
`PLAN-REVIEW-LOG.md`. Method ported from the 2D project (`lri_2d_coeff_expanse/independent_check/c4_exact/`,
HT2dPert session; zero-mode paths and pattern enumeration copied, 1D densities/cutoff/functionals new).

| file | role |
|---|---|
| `c4lib1d.py` | engine: line series, zero-mode paths, patterns, even-parity densities (dense reference, 3-vertex fast path, streaming 4-vertex kernel with in-place BLAS accumulation), shells, exact per-key functional reduction, two-vertex chains with ε-derivatives |
| `c4_compute1d.py` | RS assembly of r2..r4, g2..g4, C2..C4 on the quarter grid; per-p X_p; ε⁴ vacuum window; `masked()` export |
| `c4_run1d.py` | production driver (`run`, `assemble`, `list`, `bench`): one task per (chain, pattern representative), checkpoints, static multi-node partition |
| `windows1d.py` | ΔR4 (cancellation-free), own g2D window sum; `vendor/exact_fast.py` = `lri_eh_hpc/lri_eh/exact.py` (verbatim) |
| `validate/` | `test_kernels.py` (A6a–c + series), `v1_exact.py` (A1, A2), `v3_brute.py` (A3; `vendor/brute_rs_cut4.py`), `v4_ht.py` (A4), `v5_windows.py` (A5), `v6_overlap.py` (A6d) |
| `inputs/` | vendored reference data, sha256 in `inputs/MANIFEST.txt` |
| `slurm/` | symmetry: `env.sh`, `validate.slurm`, `bench.slurm`, `node.slurm`, `assemble.slurm`, `submit.sh` |

Local proofs (seconds): `python -m pytest -q validate/test_kernels.py`, `python validate/v1_exact.py`,
`python validate/v3_brute.py --cut4max 48`.

## Validation status (symmetry job 573811, code sha 57860989…, snapshot 28c9236, 2026-10-12)
All gates PASS (`<SCRATCH>/lri_1d_c4/validation/<sha>/PASS`):
pytest 12/12 (incl. A6a/A6b at Λmax = 40); A1/A2 ≤ 2.1e-14 rel (incl. Dconn C4 at cut4 = 8..64); A3 945
comparisons ≤ 8e-13 (cut4 = 4..48); A4 vs HT raw (Λ ≤ 92) and thermal_d7 (Λ ≤ 118): |ΔC4| ≤ 1.4e-12, |ΔC3| ≤ 1.6e-13;
A5 shift4 vs dC_reconciled (67 rows) ≤ 4.4e-16, ΔR4 = H_odd(Λ-1)/2916 to 1.1e-15, own g2D = fast(Λ) to 8.8e-16
(Λ ≤ 400); A6d Λmax 200 vs 400: |ΔC4| ≤ 1.9e-13. Wall time: Λmax = 400 in 48 s on one Intel node.
