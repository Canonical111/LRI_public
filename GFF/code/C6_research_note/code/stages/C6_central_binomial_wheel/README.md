# Central-binomial wheel reduction for C6(1)

Read `DERIVATION.md` first. The change is a simpler analytic representation of
one retained wheel constant, not a reduction in the number of residual inputs.
The full updated expression is in `results/updated_expression.json`.

## Reproduction

Use Python 3 with SymPy and mpmath installed. Run from this directory:

```sh
python verify.py
python certify.py
python evaluate.py 55 80 26
python evaluate.py 100 160 42
python evaluate.py 190 400 90
python validate_release.py
```

`verify.py` derives the finite exact symmetry and coefficient calculations and
rebuilds the expression. `certify.py` performs exact rational arithmetic only
(apart from informational printing of elapsed time and interval widths); the
returned interval endpoints never depend on a floating-point reference.
`evaluate.py` independently compares the new series with the original elliptic
integrands and also checks literal direct partial sums. Its asymptotic-tail
calculations are numerical checks, not certified error bounds.

## Files

- `DERIVATION.md`: definitions, analytic inputs, proof, compensation, and bounds.
- `results/exact_checks.json`: 33 exact algebra checks and collected polynomial.
- `results/rational_intervals.json`: three nested exact-rational intervals,
  their cubic-in-pi approximants, and their rigorous analytic tail bounds.
- `results/numerics_*.json`: fresh floating-point comparison results.
- `results/release_validation.json`: additional finite release/integrity checks.
- `inputs/`: exact inherited definitions and project analytic inputs.
- `MANIFEST.sha256`: hashes of the files shipped in the archive (excluding itself).

## Limits

Only the wheel evaluation and its compensating known terms change. The
primitive, logarithmic series, depth-two polylogarithm, ordinary periods, source
repair and upstream graph/RG identifications remain inherited. The interval
certifies the newly defined central series, not the complete six-loop graph
calculation. Three auxiliary quantities remain.

The explicit second-order selection identity is recorded in Bao's 2026 preprint
and follows from Mishev's established completed-L invariance; no novelty claim
is made for that identity. The proof and code spell out its exact use here.
