# Real-valued C6 representations

Recommended: the nine-value formula uses Ls3(pi/2) and the standard multiple Clausen Cl_(2,1,2)(pi/2), with no explicit Re/Im in the coefficient and no quintic parameter construction. The Clausen replacement is a real-function convention, not a new evaluation of that period.

Alternative: a ten-value formula replaces the multiple Clausen function as well, with Ls_(2,3)^(0,0)(pi/2) and Ls_(4,1)^(0,0)(pi/2). All three polylog-sector functions then belong to one established, entirely real log-sine family. One extra function value is the cost.

Neither count is an arithmetic-independence statement. The eight-call complex KdF alternative has not been proved to be an eight-dimensional independent basis.

Run with Python 3, mpmath, and SymPy:

```
python check.py 45
python check.py 90
python build.py
```

Numerical tests use 15 guard digits, but no numerical result is presented as an interval certificate. No full-C6 or physical graph/RG verification is performed. The script hpl_reference.py is adapted from the project's supplied C6_polylog_basis_audit/numerical.py, without using the new identities to initialize the original HPLs.

FORMULA.md contains the complete recommended expression and the optional all-log-sine replacement, followed by all seven unchanged non-polylogarithmic definitions. DERIVATION.md supplies the analytic proof. The JSON files under results contain exact expressions and scope metadata. No Wolfram-kernel execution is claimed. No external font or proprietary package is included.
