# Arbitrary-dimensional coefficients through C5: fixed-parameter Horn representation

The full updated note is `long_range_ising_complete.tex` / `.pdf`.
Appendix K gives the new closure. Appendices I and J retain the graph, MS,
master-reduction and weighted-series derivations. The preferred d=1 expression
in four 9F8(-1) and one 8F7(-1) values is unchanged.

## What is new

* Q2 = Gamma(1/4)^8/(24*pi^4) is exactly the earlier normalized tetrahedron.
* P5(d) has an explicit derivative-free double-residue series. The measure-pole
  family cancels by an antisymmetric spin interchange; no spectral integral
  remains in this representation.
* The common non-summable part of the two K_d residue families is removed
  explicitly by Gauss summation before they are decomposed into Horn functions.
* All six master quantities have finite parameter arrays in the conventional
  multivariable Horn/Gamma-ratio class. Parameter polygamma weights are replaced
  by additional hypergeometric indices, not by hidden parameter derivatives.

## Exact meaning of the closure

This is a finite **multivariable** special-function representation. It is NOT a
claim of a compact finite combination of ordinary one-variable pFq functions.
The direct compiler emits 20, 56, 244, 318, 386, 6024, and 9036 values for Q,
P4, L, Z, K, P5a, and P5b respectively, before any nontrivial Horn-function
relations. P5 = P5a + P5b. These counts are deliberately nonminimal.

The common convergence strip is 1/6 < q=d/4 < 1/2. Outside it, continue the
COMPLETE finite expression in q as prescribed in the note. Individual K Horn
series at unity may diverge for d>=2, and their poles must not be assigned
unrelated finite parts. The original paired sum remains useful numerically.
The physical coefficients have not been newly established by an independent
generic-d full-graph numerical computation. The prior exact graph/forest
reduction is retained as the source of the coefficient assembly.

## Files and function conventions

`verification/general_closed/horn_arrays/*_horn.json.gz` each contain a finite
list of functions. A row specifies:

- `prefactor`: a fixed scalar expression; the named scalar dictionary is in
  `scalar_parameters.json`;
- `dimension`: the number of summation variables;
- `upper`, `lower`: rows `[parameter, index_vector, multiplicity]`;
- `arguments`: the fixed argument vector (all 1 except primitive spin -1).

For index vector n, the coefficient is

    product (upper_a)_(upper_vector dot n)
    ------------------------------------  / product n_i!
    product (lower_b)_(lower_vector dot n)

with repeated rows raised to the stated multiplicity. The standard unit upper
parameters cancelling otherwise absent factorials are already included.
There are no unresolved `v...` atom symbols in the emitted arrays. The separate
`atom_dictionary.json` only explains the finite compiler input.

## Reproduction

Python with sympy, mpmath, numpy and scipy is required. From the package root:

    python code/general_closed/check_new_identities.py
    python code/general_closed/check_primitive_sums.py
    python code/general_closed/check_horn_compiler.py
    python code/general_closed/check_insertion_prefactors.py
    python code/general_closed/kappa_regularization.py
    python code/general_closed/horn_compiler.py --out verification/general_closed/horn_arrays

Inspect a recorded array:

    python code/general_closed/read_horn_arrays.py --master Q --entry 0

The reader evaluates individual coefficients on request; it is not a numerical
analytic-continuation library for all endpoint functions. The direct double
series and independent spectral programs are supplied for practical numerical
checks. Large generic Horn counts are a function-class certificate, not an
assertion of an efficient new numerical method.

Build the note with pdflatex twice (a third pass may be needed after TOC changes).
All 614 pre-existing mathematical display environments were preserved verbatim
and in order. Source hashes and the precise preservation test are recorded in
`verification/general_closed/source_preservation.json`.

## Verification boundaries

`identity_checks.json`: fresh 60-digit Q2 normalization, K polynomial/Gauss
identities, Cauchy-circle P5 residues, measure-pole antisymmetry, and a fresh
one-dimensional Gamma moment.

`primitive_sum_checks.json`: fresh d=1,2,13/5,3 primitive sums vs fresh Gamma
or spectral calculations, with radial cutoffs and spectral node counts varied.
The double-precision residuals are not interval error bounds.

`horn_compiler_checks.json`: 1038 exact normalized-coefficient comparisons,
12 finite shift checks, and fixed-polygamma normalization checks.

`insertion_prefactor_checks.json`: 336 exact rational checks including every
type of insertion prefactor, the E6 polynomial and the d=2 C4/C5 substitutions.

The checks do not claim a direct numerical sum of every eight-variable
continued Horn function, a rigorous numerical enclosure, or a new independent
four/five-loop full-graph calculation. No fonts or proprietary runtimes are
included.
