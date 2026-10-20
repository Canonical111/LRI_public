# C6 seventh sector: unit slopes and positive arguments

Result: `H7 = (Pi/2) H7unit`, with the new H at (1,1) and every slope equal to
one. The complete coefficient still contains nine fixed values. The known
polynomial and every other sector are unchanged.

## Reproduce

Python 3, SymPy and mpmath are required. From this directory run:

```text
python build_and_verify.py
python check_inner.py 40
python check_inner.py 65
python numerical.py 45
python numerical.py 80
```

The first script checks exact finite algebra/transcription and writes the
complete expression. The other scripts are floating-point cross-checks. They
are not interval arithmetic, and the double Barnes integral is not evaluated
as a single independent two-dimensional quadrature. No Mathematica kernel is
required or claimed to have been used.

`FORMULA.md` is self-contained. `DERIVATION.md` proves the transformation and
convergence. `inputs/` preserves the immediately preceding accepted expression,
formula and derivation. `results/` records the executed checks. The source
physical graph/RG identification remains inherited.

This is a function-class/branch simplification, not an arithmetic-independence
result or another decrease in the number of fixed special-function values.
