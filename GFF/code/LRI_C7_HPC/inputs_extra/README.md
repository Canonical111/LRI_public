# Degree-7 meromorphic weights (convergence check only)

`cw_L{5,6,7}_N7.txt` are the original meromorphic Chebyshev tensor weights at degree 7,
generated with `tools/regenerate_weights.py --dps 100` (same rule and layout as the
archived generator; `weights_L*_provenance.json`). They feed only the paired degree-6/7
refinement campaigns (`production.py plan --refine7 --extra-inputs inputs_extra`), which
the assembler reports as a check level and never adds to the C7 estimate.

Checks recorded here (`check_weights.json`, `validation_inputs.json`), run on x86-64
(i9-13900K, GCC 13.3) on 2026-09-25:

- 100-digit and 150-digit generations agree to 3.3e-95 relative; no long-double rounding differs.
- Exact monomial moments, including pole and negative-power cases: max normalized error 3.3e-89
  (2816/4160/5760 checks for L5/L6/L7, none skipped).
- Regenerating degree 6 with the same tool reproduces the shipped `reference/inputs/cw_L*_N6.bin`
  exactly after long-double rounding.
- Native `.bin` fixtures converted from these decimals (for the original programs) round-trip
  with 0 ulp error.

The original-versus-optimized comparison at degree 7 (`tests/check_degree.py`) and the
binary128 replay (`tests/check_quad.py --degree 7 --reference-ld`) use a separate validation
directory built by `tests/make_validation_inputs.py`; `reference/` is not modified.
