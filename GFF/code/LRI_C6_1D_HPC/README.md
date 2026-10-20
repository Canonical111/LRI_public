# LRI_C6_1D_HPC — C6(1) from exact all-graph sums

Deterministic, high-degree evaluation of the six-loop coefficient C6(1) of the 1D long-range Ising model
(epsilon = 2s - 1). It extends the original calculation in `reference/` (verbatim copy of
`lri_C6_numerical_update/reproduction`, C6(1) = 14331.8 +- 0.5): every Monte Carlo level is replaced by exact sums over
all 2,137,415 graphs and 360 reversal classes at quadrature degrees N = 6, 8, 10, ...

Specification: `../LRI_C6_1D_HPC_loop/PLAN.md` (rev 8, Codex-approved). Layout:
- `src/c6sum.cpp` engine; `make` builds `bin/c6sum` (AVX-512 double, light stratum) and `bin/c6sum_ld` (long
  double, hard stratum and L5 inputs), plus `bin/enumerate`.
- `tools/`: `weights.py` (weights + manifest), `merge.py`, `levelio.py` (shared level validation), `levelcheck.py`,
  `assemble.py`, `rounding.py`, `analyze.py` (pre-registered estimate and allowance), `validate.py`.
- `cluster/` (symmetry): `validate_all.sh` (gates V1-V10 -> validation/APPROVED.json), `production.sh A` then
  `production.sh N=18`, ... under the stopping rule.
- `tests/test_tools.py`: local tests of the tools (`~/anaconda3/bin/python tests/test_tools.py`).
