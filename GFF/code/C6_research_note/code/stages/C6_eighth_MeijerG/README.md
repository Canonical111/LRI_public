# Finite eighth-power Meijer G compression for C6(1)

This package replaces the complete already-finite eighth-power block by one
ordinary Meijer G at 1. An all-rational three-value alternative is included.
It does not solve the three remaining elliptic residual blocks.

- `DERIVATION.md`: complete exact argument, parameter convention and scope.
- `C6_eighth_MeijerG_patch.wl`: standalone finite Wolfram expressions.
- `build_and_verify.py`: exact symbolic checks and regeneration of the output.
- `numerical.py`: independent Barnes-versus-hypergeometric comparisons.
- `results/partial_expression.json`: updated partial coefficient, including all
  unchanged finite terms and explicit unresolved-status fields.
- `results/exact_checks.json`: executed finite algebra/static checks.
- `results/numerical_40.json`, `results/numerical_80.json`: numerical reports.

Run `python build_and_verify.py`, then `python numerical.py 80 192 64`.
Python dependencies are SymPy and mpmath. Wolfram code was not executed in a
Wolfram kernel. Numerical Barnes quadrature is a verification route, not a
part of the finite Wolfram formulas or an interval certificate.

The previous full C6 numerical reference is not used to choose coefficients.
