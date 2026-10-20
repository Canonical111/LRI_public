# Standard bivariate-H reduction of the last C6 primitive

Main result:

    Pa = 8*pi^3*(10*BH11+21*BH12+18*BH22+15*BH23).

BHjk are the fixed unit-slope bivariate Fox H values specified in
DERIVATION.md, equation (2), and in results/updated_expression.json.
They are not project-specific infinite series. The full coefficient has no
active bespoke sum, but this is an enlarged two-variable special-function
representation, not a minimal ordinary-hypergeometric evaluation.

## Files

- DERIVATION.md: analytic identification, convergence, full substitution, scope.
- formula.py: constructs the updated complete machine expression.
- verify.py: 67 exact finite symbolic and field-preservation checks.
- numerical.py: stable beta-pairing quadrature, univariate Meijer G point checks,
  original primitive comparison; floating point, not interval arithmetic.
- inputs/: unchanged source expression, primitive derivations, prior certificate.
- results/: generated expression and recorded verification runs.

## Commands

    python formula.py
    python verify.py
    python numerical.py --digits 40
    python numerical.py --digits 100

Requires Python 3, SymPy and mpmath. No network access is needed.

The original cubic primitive definition is retained only under a legacy field.
The known polynomial, source repair, even and seventh sectors and polylogarithms
are preserved. All upstream physical graph/RG identifications remain inherited.
