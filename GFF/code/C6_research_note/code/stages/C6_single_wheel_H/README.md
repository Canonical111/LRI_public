# One bivariate wheel value in the finite C6(1) representation

Read `FORMULA.md` for the complete 17-value formula and `DERIVATION.md` for the new wheel reduction. It changes only

    -9432*pi**3*F4 - 5895*pi**4*F6

into

    -393*pi*sqrt(89)*Hw,

where the fixed standard bivariate Fox H value Hw is fully specified in both documents and `results/expression.json`. All slopes are one. Its parameter alphaW=atan(5/8)/pi contains no unknown period.

## Reproduce

Python 3 with SymPy and mpmath:

```
python build_verify.py
python numerical.py 35 --inner
python numerical.py 65 --inner
python propagate_interval.py
python make_formula.py
```

The first script checks finite algebra and preservation of source fields. The second/third scripts perform empirical numerical checks. The fourth script propagates an inherited rational certificate; it is not a certification of numerical Barnes integration. The last script regenerates the self-contained formula.

The inherited global wheel identity is essential and stated verbatim in the derivation. This package does not rederive the physical six-loop graph/RG coefficient and does not claim an elementary/gamma-zeta evaluation or arithmetic independence. No fresh all-sector C6 numerical assembly was performed.
