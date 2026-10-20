# Complete interval enclosure of the retained C6(1) expression

The full saved analytic representation is enclosed with width below
**1.183e-145**, including all finite arithmetic and infinite-tail errors.
Its exact endpoints share 144 digits after the decimal point.

This certifies the value of the uploaded analytic formula. It does not
independently prove the upstream physical graph/RG identification and does not
eliminate an additional auxiliary constant. The source repair and all analytic
weights are unchanged.

Read `DERIVATION.md` for the proofs and scope. `results/complete_refined.json`
contains exact dyadic endpoints, all intermediate values, and tail certificates.
`results/validation.json` records exact nesting and additional checks.

## Run

With Python 3, SymPy, and mpmath:

```sh
python certify_complete.py smoke
python certify_complete.py release
python certify_complete.py refined
python validate.py
python check_numerical.py 80
```

The main constructors use integer/Fraction arithmetic with outward rounding.
mpmath is used only for supplementary tests, never for certificate endpoints.
The tested environment was Python 3.13.5, SymPy 1.14.0, mpmath 1.3.0.

## Files

- `dyadic.py`: small audited integer-endpoint interval implementation.
- `elementary.py`: finite remainder bounds for elementary/gamma/zeta constants.
- `rational_tails.py`: exact rational telescopers for positive ordinary series.
- `primitive.py`: supplied nine-component recurrence; new last-two-state tail.
- `other_series.py`: Euler bounds for alternating periods and logarithmic sums;
  geometric half-argument and Lambda series.
- `certify_complete.py`: complete weighted assembly and certificate output.
- `validate.py`: exact finite checks and separate high-precision reference tests.
- `check_numerical.py`: independent floating-point original-kernel quadrature.
- `inputs/`: unchanged expression and previous wheel provenance.
- `wheel/`: the two retained wheel-certificate code files.
- `results/`: three complete interval runs and verification records.

`MANIFEST.sha256` records release file hashes. The JSON expression in `inputs/`
is byte-for-byte the user-uploaded expression; no previous C6 numerical value is
used in the new assembly.
