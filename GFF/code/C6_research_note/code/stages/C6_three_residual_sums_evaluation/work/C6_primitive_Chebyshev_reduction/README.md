# Cubic primitive: genuine two-index to one-index reduction

Read DERIVATION.md for the exact single-series formula and its proof.
Only ordinary univariate MeijerG coefficients occur. One infinite series remains;
this is not a finite closed form in fixed built-in values.

Reproduce the executed finite and floating-point checks with:

```text
python verify.py
python numerical.py --digits 35 --cutoff 2048
python numerical.py --digits 45 --cutoff 2048
```

Requirements: Python 3, SymPy, mpmath. No network access or Wolfram kernel is
needed for these checks. C6_primitive_Chebyshev.wl gives the corresponding native
Wolfram definitions. It was statically checked but not executed here.

The old current C6 source in inputs is unchanged. Its one replacement is
192*pi^2*PaCubic -> 768*pi^3*(Phi0+2*sum(n>=1,(-1)^n*Phi_n)).
No other sector or source correction is modified.
