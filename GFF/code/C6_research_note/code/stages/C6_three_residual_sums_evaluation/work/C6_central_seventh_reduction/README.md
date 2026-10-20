# C6 central seventh-power reduction

The main identity is

    -36*A*P5 - 392*pi^(3/2)*CZ - 784*pi^(3/2)*L7 = 24*pi^3*M7central.

M7central is explicitly defined with one sequence binomial(2n,n)/4^n, finite
harmonic sums, and pi/log(2)/zeta(3). See DERIVATION.md for the full proof,
complete coefficient, convergence qualification, and Euler error bound.

The active formula is in results/reduced_expression.json. The new series keeps
n=0; do not add its n=0 contribution to the known polynomial again.

This is a structural simplification, not a finite evaluation of the logarithmic
period. Harmonic degree increases from one to three. Three residual quantities
remain. Five individual Z periods are folded into the sector, not proved
independently elementary. Physical graph/RG assumptions are inherited.

Reproduce with Python 3, SymPy, and mpmath:

    python formula.py
    python verify.py
    python check_numerical.py
    python certify.py

The interval evaluator uses only integer/rational arithmetic for enclosure
construction. It initializes the new sum independently of previous results.
Unchanged constants are loaded from the preceding interval certificate only
for the comparison and full-coefficient reassembly.

Historical definitions in the input JSON, including older formula text, are
retained as provenance. Only the top-level active formula, known_polynomial,
and active auxiliary lists define the new representation.
