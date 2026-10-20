# Three-dimensional half-shift reduction

This is a revision of the existing long-range Ising research note, not an independently published field-theory result. The new derivation is Appendix M, pages 130–137 of the 140-page full note.

## What is new

At d=3 the angular multiplicity is 2 ell + 1. The half-period shift exchanges two offset lattices and gives determinants of ordinary hypergeometric moments, rather than the dimension-two square. These identities determine one Fourier-parity sector. The remaining sector is explicitly evaluated by the two-variable Horn functions whose full arrays are printed in the note and stored in `verification/general_d3/horn_arrays.json`.

The real positive-rational formulas require:

| Period | Two-variable values | Ordinary values |
| --- | ---: | ---: |
| Q_3 | 1 | 0 |
| P_4(3) | 2 | 3 |
| P_5(3) | 5 | 18 |

Gamma factors and finite arithmetic are not counted. Fixed-complex-node variants reduce the two-variable counts to one for P_4 and two for P_5. These counts are upper bounds, not minimality assertions.

The particularly short tetrahedron formula is

`Q_3 = 4*pi^2*H_3(0) - Gamma(1/4)^10/(48*pi^(7/2))`.

Here H_3 is a fully specified **two-variable** Horn function, not an ordinary generalized hypergeometric function. Dixon and Rogers–Dougall sums analytically evaluate the Gamma term and a four-loop amplitude. No integer-relation fit is used in the proof.

**Not achieved:** a complete reduction to ordinary one-variable pFq values for d=3; a new reduction of K_3, L_3 or Z_3; a new independent full-graph determination of C_5(3); rigorous interval error bounds. The previous nonprimitive representation and physical assembly are retained. No claim of impossibility or minimality is made.

## Files

- `long_range_ising_complete.tex` and `.pdf`: updated main note, all 705 previous displayed mathematical blocks retained verbatim and in order.
- `three_dimension_reduction.pdf`: new eight-page appendix followed by provenance/references.
- `general_dimension_complete.pdf`: current general-dimensional portion of the main note.
- `three_dimension_addition.tex`: the exact new appendix source.
- `history/before_d3_reduction.tex`: the input main source.
- `source_diff_d3.patch`: this revision's source diff.
- `code/general_d3/`: fresh evaluators and exact verification scripts.
- `verification/general_d3/`: machine-readable raw results, complete Horn rows, comparisons, preservation and PDF checks.

Older supplementary chapters and records remain explicitly named and are retained from the input package. `source_diff.patch` belongs to the preceding revision; use `source_diff_d3.patch` for the current one.

## Reproduction

The new numerical code was run with Python 3.13.5, mpmath 1.3.0 and SymPy 1.14.0. From the package root:

```sh
python code/general_d3/check_exact.py
python code/general_d3/verify_d3.py
python code/general_d3/check_spectral.py
```

The exact checker verifies 25 finite identities and 288 rational Horn coefficients. It also generates the eight real-node arrays.

The formula-side script calculates the finite formulas at 55 and 90 working digits, checks off-grid determinant identities and the complex-node variants at 75 digits, and makes six literal ordinary `mpmath.hyper` evaluations at 40 digits. The numerical asymptotic tails are used to evaluate the specified functions; they are not additional operations in the analytic formulas. They are asymptotic accelerations, not certified enclosures.

The spectral script recomputes the positive-real-axis Gamma kernels independently of the formula-side evaluator. It uses an analytically derived integrated wheel tail and a separate Euler-accelerated alternating primitive sum. It changes quadrature breakpoints, spin cutoffs and tail orders between 45- and 60-digit runs. It does not read saved period values as inputs.

At the higher settings, the new formulas minus fresh spectral kernels were approximately:

- Q_3: -1.4661e-51;
- P_4(3): -1.5266e-52;
- P_5(3): -2.4054e-53.

These are observed residuals and master-level checks, not numerical proof of a full physical coefficient. The formula-side runs agree beyond 49 digits; the stored 90-digit output is not an independently certified 90-digit result.

The main TeX is self-contained and uses standard LaTeX packages:

```sh
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
```

No old coefficient formula, one-dimensional five-positive-rational-function answer or dimension-two quadratic factorization was changed.
