# Partial C6 reduction in actual Mathematica built-ins

The sixth-power finite block P_b has a two-MeijerG rational-parameter formula,
and an optional one-MeijerG formula with alpha=ArcTan[11/13]/Pi.
This is NOT a finite evaluation of the unresolved primitive P_a.

- `C6_sixth_MeijerG_patch.wl`: standalone exact formulas and optional Wolfram numerical comparison.
- `DERIVATION.md`: analytic proof, normalization and limitations.
- `build_and_verify.py`: exact symbolic checks and partial-expression builder.
- `numerical.py`: independent gamma-kernel quadrature and old hypergeometric comparison.
- `results/partial_expression.json`: machine-readable partial expression.
- `results/exact_checks.json`: finite checks that actually passed.
- `results/numerical_50.json`, `results/numerical_90.json`: executed floating-point comparisons.
- `inputs/latest_partial_expression.json`: unchanged supplied input.
- `legacy/rational_tails.py`: unchanged prior ordinary hypergeometric enclosure evaluator.

The three elliptic residual blocks remain. There is no new full-C6 closed form
or rigorous MeijerG/full-C6 interval certificate. No Wolfram kernel was available;
Mathematica code was not executed here. Numerical integration in the Python test
script is a verification method, not part of the proposed finite expression.
