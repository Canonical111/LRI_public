# C6 even-sector central-binomial normal form

This package continues the supplied central-seventh expression.

The analytic result is a one-sequence formula for the complete even-power
sector, including Bminus/Bplus, Pb, PZ6, PK, and the wheel. It removes the
separate ordinary unit-argument periods from the active formula and cancels
its explicit pi^6 monomial. It does **not** finitely evaluate those periods or
prove a reduction in the number of independent constants.

Read `DERIVATION.md` for the identities, convergence proof, direct tail bound,
limitations, and a separate checked rational-boundary obstruction for Pa.

The complete active expression is `results/reduced_expression.json`.
All original primitive, M7, polylogarithm, source-correction and historical
period definitions are retained there.

## Reproduce
Requires Python 3, `sympy`, and `mpmath`.
```
python formula.py
python verify.py
python check_numerical.py 75 128 30
python check_numerical.py 110 224 44
python check_numerical.py 190 512 85
python propagate_intervals.py
python check_boundary_obstruction.py
```
No network access is needed.

`results/propagated_intervals.json` propagates the earlier rigorous period
intervals through the new identity. It is not a new independent series
certificate. The asymptotically accelerated sums are floating-point
cross-checks, not interval proofs.

The physical identification with the six-loop Ising coefficient remains
an inherited assumption.
