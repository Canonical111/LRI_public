# C6 primitive: exact cubic harmonic reduction

The main result is

    I22 - 4 I12 + 4 I02 - 4 I00 = 0,
    Pa = 2*pi**2 * PaCubic.

`DERIVATION.md` gives the full upper-half-plane contour proof and the explicit
positive two-index summand. Its harmonic degree and order are three rather
than four. `results/cubic_expression.json` is the complete current C6 expression
with only the active primitive and current-step metadata changed.

This does NOT eliminate Pa as a residual constant, remove a summation index,
or recertify the upstream graph/RG identification. Literal convergence remains
slow and is somewhat worse than the preceding quartic sum at the shown cutoffs.

## Reproduction

Python 3, SymPy and mpmath are required. The executed environment was
Python 3.13.5, SymPy 1.14.0, mpmath 1.3.0. No network access is needed.

From this directory:

    python formula.py
    python verify.py
    python numerical.py --digits 60
    python numerical.py --digits 120
    python series.py --cutoffs 1 32 128 512 --digits 45

The exact check report has 122 passing algebra/implementation checks. The
analytic proof is in the derivation; this is not a proof-assistant certificate.
The numerical files are floating-point checks, not new interval certificates.
A zero reported difference means the values round to the same working-precision
number, not a zero-error theorem.

## Files

- `formula.py`: constructs the updated expression while preserving inherited data.
- `verify.py`: exact contour-polynomial, beta-moment and preservation checks.
- `numerical.py`: independent Gauss-pairing, beta-logarithm and branch checks.
- `series.py`: literal triangular partial sums and the explicit analytic tail bound.
- `inputs/central_expression.json`: complete unmodified starting expression.
- `inputs/central_derivation.md`: previous quartic derivation.
- `inputs/primitive_reference.json`: inherited rational Pa interval for comparison.
- `results/`: executed checks, full expression, numerical reports and partial sums.

All indices begin at zero. The primitive normalization changes from Pa/pi to
Pa/(2*pi**2), so its C6 coefficient changes from 96*pi to 192*pi**2. The known
polynomial does not shift. No initial term or source correction is added twice.
The old quartic and geometric-recurrence definitions are retained in the JSON;
the previous package remains the source of the fast recurrence implementation.
