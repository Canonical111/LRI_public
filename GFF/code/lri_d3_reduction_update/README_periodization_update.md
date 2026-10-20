# General-dimensional primitive reduction and exact d=2 factorizations

Revision date: 11 September 2026.

## Status

This revision **does not claim to have eliminated every infinite-sum structure from the full arbitrary-dimensional C5 in favor of finitely many ordinary one-variable hypergeometric values**. The previous finite multivariable Horn representation remains the specification of the nonprimitive K_d, L_d and Z_d. Its analytically continued endpoint conventions have not changed.

There are two new analytic results.

1. A finite-Fourier periodization theorem reduces Q_d, P4(d), and P5(d) to at most 15, 20, and 56 fixed function evaluations, respectively. Every function has at most two variables. The previous direct Horn encodings used 20, 56, and 15,060 values, with up to four, five, and eight variables. The new formulas contain no Barnes integrals, parameter derivatives, or polygamma-weighted summands. They still contain ordinary one-variable subblocks and genuine two-variable Horn functions; this is not advertised as a univariate reduction.
2. At d=2 the whole primitive lattice factorizes. P4(2) and P5(2) are quadratic expressions in precisely the same ordinary hypergeometric values retained for d=1. No new hypergeometric values, derivatives, or infinite outer sums are needed in those two formulas.

In the note's notation:

    P4(2) = (B_-^2 - B_+^2)/(4 pi^3)

    P5(2) = (8/pi) [25 X0^2 - 28 sqrt(2) X0 (X+ + X-)
                      + 18 (X+^2 + X-^2) + 28 X+ X-]

The B values are the two normalized 4F3(1) periods. The X values are the three finite combinations of the preferred five positive-rational-parameter Y values: four 9F8(-1) and one 8F7(-1).

All C0(d)–C5(d) coefficients remain unchanged. The remaining nonprimitive target can be collected as

    N_d = K_d + (3/8)L_d - (149/32)Z_d.

No new evaluation of this generic-dimensional combination is claimed.

## Reading the documents

- `long_range_ising_complete.tex` and `.pdf`: full updated note, including all one-dimensional definitions and proofs.
- `general_dimension_complete.pdf`: the updated general-dimensional part, extracted from the full note. Earlier appendices are retained as development history. Some proofs refer to one-dimensional lemmas in the full document.
- `primitive_periodization_chapter.pdf`: new Appendix L plus the source bibliography. This extract is not a substitute for the entire RG derivation.
- `primitive_periodization_addition.tex`: the exact new TeX fragment.
- `source_diff.patch`: source changes relative to the preceding note.

Appendix L gives the theorem and its growth proof, classwise cancellation of measure poles, the fixed cosine grid, explicit finite residue polynomials, every Horn parameter row, convergence/continuation, and the d=2 quadratic-factorization proofs. No unattached master value or unspecified parameter list is needed to interpret the formulas.

## Numerical evidence

Recorded outputs are in `verification/general_periodization/`.

- `wheel_periodization.json`: four 35-digit fixed-spin comparisons to fresh Barnes integrals, including noninteger d, with errors below 3e-30 and separate off-grid tests.
- `horn_template_checks.json`: 44 high-precision coefficient comparisons of the actual parameter arrays, and all-mode checks of the finite cosine transforms. These are numerical coefficient tests, not interval certificates.
- `p5_periodization.json`: generic-d all-spin sampling compared with freshly computed spectral quadrature. These double-precision Gamma-kernel checks have differences about -1.39e-9 at d=2.4 and +7.38e-8 at d=3. They must not be described as 50-digit agreement just because the final weights use mpmath.
- `d2_factorization.json` and `d2_control.json`: separate 55- and 70-digit calculations of the square-factorized d=2 kernels, with changed series tails and different sampling grids.
- `d2_inherited_periods.json`: fresh literal `mpmath.hyper` calls at 60 working digits for the retained one-dimensional functions. The new P4(2) and P5(2) quadratics differ from the independent 70-digit d=2 evaluations by about 6e-59 and 2e-58.
- `exact_algebra.json`: exact symbolic normalization, quadratic-polynomial, and C5-collection checks.
- `source_preservation.json`: check that every prior displayed mathematical block remains verbatim and in order.
- `arrays/primitive_r3.json`, `primitive_r4.json`, `primitive_r7.json`: finite machine-readable one-/two-variable parameter templates and fixed sampling points.

No interval enclosure, independent new physical five-loop calculation, or proof that the function counts are minimal is claimed. No full graph integral was rerun in this revision. The complete pre-existing graph and master verification records remain included.

## Reproduce

From this directory, with Python, mpmath, SymPy, NumPy and SciPy available:

```bash
python code/general_periodization/horn_templates.py
python code/general_periodization/check_exact_algebra.py
python code/general_periodization/check_horn_templates.py
python code/general_periodization/check_wheel_periodization.py
python code/general_periodization/check_two_dimensional.py
python code/general_periodization/check_d2_control.py
python code/general_periodization/check_d2_inherited_periods.py
python code/general_periodization/check_p5_periodization.py
```

The new scripts locate the supplied code and output directories relative to their own paths. The parameter-array compiler is not a general-purpose multivariate Horn numerical library. The generic-d controls evaluate the corresponding Gamma-ratio kernels; the parameter-array correspondence is separately checked coefficient by coefficient. The d=2 quadratic checks do use literal ordinary hypergeometric evaluation.

To compile the full note, run `pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex` twice (a third run can be needed after a table-of-contents change).

The stable sampling grid is shifted a fixed small distance off the real axis. Its imaginary height is not a regulator. Sampling at remote imaginary-axis Chebyshev nodes gives unnecessarily large cancellation in the seven-mode primitive; increasing only the precision of the final linear algebra does not repair a double-precision sample error.

## Preservation and scope

The original one-dimensional formulas, including the preferred five fixed positive-rational hypergeometric values for P5(1), are unchanged. The previous arbitrary-dimensional coefficients, master definitions and evidence remain. The new proofs reduce representations; they do not by themselves externally validate the inherited four-/five-loop field-theory reduction.
