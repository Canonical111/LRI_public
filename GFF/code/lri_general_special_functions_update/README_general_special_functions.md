# Arbitrary-dimensional LRI: fourth/fifth-order special-function reduction

## Read first

`long_range_ising_complete.pdf` is the complete 111-page note. Appendix J
(pages 99–109) contains the new reduction, including its function-class and
verification boundaries. `general_special_chapter.pdf` is a 14-page convenient
extract compiled as a standalone chapter with its bibliography. External
cross-references in that chapter retain the numbering of the full note.

The earlier one-dimensional displays and the previous arbitrary-dimensional
integral formulation are retained. The preferred one-dimensional P5 expression
(four fixed positive-rational 9F8 values and one 8F7 value) is unchanged.

## What is new

* Exact collected C4(d), C5(d), b4(d), c4(d), D4(d), and D5(d) from the
  conformal graph/forest reduction, in the normalization used in the note.
* Explicit Pochhammer/polygamma double-series definitions for K_d, L_d, Z_d,
  and the wheel periods Q_d, P4(d). No graph integral, master-parameter
  derivative, unsupplied Laurent coefficient, or fitted period occurs in those
  definitions.
* An independent common Gamma-ratio spectral kernel, the complete local
  residue-polynomial proof, and the exact dimension-two identity Z_2=4G Q_2.
* New master-level numerical values for C4(2), C5(2), C4(3), C5(3).

This is a **polygamma-weighted multiple-hypergeometric-series representation**,
not a finite combination of ordinary univariate pFq functions at general d.
It is not asserted to be a minimal master basis.

## Domains and numerical cautions

Use fixed 0<d<4. The direct Q/Z residue sums need d>2/3; P4/L need d>1/2.
Below those thresholds use the stated analytic continuation, not divergent
individual spin integrals. The K sum is iterated: pair its two residue
families, perform the n sum, then the spin sum. It is not legitimate to split
it into two independently summed double series. Dimension-one raw residue
sums converge slowly; the spectral/closed comparison is much more accurate.

Stored floating-point digits are numerical outputs, not rigorous interval
bounds. Exact reduction checks and independent master integrals were run,
but no new full generic-dimensional four/five-loop numerical graph calculation
was performed. The old one-dimensional full-graph audit remains a separate
piece of evidence. The angular-tail fits accelerate numerical integration only;
they are not inputs to the analytic identities.

## Reproduction

Python requires numpy, scipy, sympy, and mpmath. From this directory:

```sh
cd code/general_special
python exact_audit.py                 # exact algebra and master normalization
python assemble_results.py            # use saved independently calculated periods
python ordered_series_checks.py       # direct residue sums at fixed spin
python residue_checks.py              # both pole families, independent Cauchy circles
python kappa_mb.py                    # independent two-contour K master route
python spectral_evaluate.py           # common-kernel spin/node/tail controls
python hypergeometric_series.py       # raw double-series diagnostics
```

To regenerate graph reductions rather than use the saved exact rows:

```sh
python collect.py 3 0 8
python collect.py 4 0 27
python collect.py 5 0 129
python sum4.py
python sum5.py
python exact_audit.py
```

Graph reduction is appreciably more expensive than assembling the saved rows.
The primitive spectral evaluator is retained at `code/primitive_spectral.py`.
The dimension-two P5 limit is implemented by `zig2` in `spectral_evaluate.py`.

Compile with pdflatex, first the complete source (three passes), then
`general_special_chapter.tex` (two passes). The latter imports earlier equation
numbers from the complete source's aux file with an isolated label prefix.

## Records

`verification/general_special/exact_checks.json` lists all exact checks.
`spectral_master_values.json` stores the varied spin/node/tail calculations.
`coefficient_values_new.json` stores the assembled coefficients with provenance.
`kappa_mb_checks.json` stores the independent two-contour checks, including the
less accurate dimension-one runs (which are not silently promoted in accuracy).
`local_residue_checks.json` tests both pole families at integer/noninteger d.
`ordered_series_checks.json` records raw inner sums and their spectral targets.
`source_preservation.json` confirms that every original display, in order, was
retained byte-for-byte. `history/before_general_special_functions.tex` is the
unchanged source immediately before this extension.
