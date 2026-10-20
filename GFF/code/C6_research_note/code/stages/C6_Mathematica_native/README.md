# Mathematica-native C6(1)

The final analytic representation uses Mathematica built-ins and an explicit
one-dimensional real integral. It is NOT a finite special-value-only closed form.
There are no bivariate Fox H, Kampé de Fériet, or single-valued HPL calls.

## Wolfram Language

```wolfram
Get["C6Native.wl"];
C6NativeExpression[]
report = C6NativeEvaluate[25];
report["C6"]
```

The evaluator uses standard HypergeometricPFQ, PolyLog, EllipticK, CarlsonRF,
Gamma, Zeta, Catalan, and NIntegrate. No external Mathematica package is needed.
The supplied `.wl` was NOT executed in a Wolfram kernel here. Numerical
identities were checked with Python/mpmath; static syntax checks do not replace
a Wolfram execution. Integration warnings are not suppressed. Requested precision
is not a rigorous error bound.

## Reproduce the Python checks

```text
python build.py
python verify_symbolic.py
python verify_numeric.py --digits 35
python verify_numeric.py --digits 60
python full_numeric.py 35
```

Dependencies: SymPy and mpmath. `full_numeric.py` expects the same-digit
`verify_numeric.py` report. The full 35-digit-working-precision run agreed with
the inherited reference to about 2.7e-14, not to 35 digits. See the report and
DERIVATION.md for the distinction between precision, accuracy, and certification.

The previous graph/RG identifications and source correction remain inherited.
