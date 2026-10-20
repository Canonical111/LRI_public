# Three-dimensional primitive periods: rank-two identification

## Status

This revision does **not** complete the requested reduction to finite ordinary one-variable hypergeometric values. It proves that the residual primitive Horn functions are standard real matrix-argument hypergeometric functions of rank two, with Jack parameter alpha = 2. The spatial dimension is d = 3; it must not be confused with the Jack parameter or matrix size.

The nonprimitive combination N_3 is unchanged. No full-graph calculation or independent endpoint master integration was rerun in this revision. The earlier d=1 and d=2 formulas, and all previous physical coefficient formulas, are preserved.

## Documents

- `long_range_ising_complete.tex`: full updated source, with the new Appendix N.
- `long_range_ising_complete.pdf`: full 144-page note.
- `rank_two_identification.pdf`: Appendix N, pages 138–141 of the full note.
- `general_dimension_complete.pdf`: general-dimensional portion, full-note pages 89–144.
- `proofs/rank_two_appendix.tex`: source of the new addition.
- `source_diff.patch`: exact change against the preceding d=3 note.

## New exact results

1. A coefficientwise hook-product identification of the wheel residuals with standard rank-two matrix hypergeometric functions.
2. A matrix-argument 3F2 representation of Q_3 and short matrix 4F3/5F4 arrays for the two four-loop residual blocks.
3. A three-term contiguous matrix-function dictionary for each five-loop residual block; this standardizes the arrays but increases the number of displayed functions per block.
4. A check that the standard matrix Kummer transformation fixes the tetrahedron array and has prefactor one. This is not a non-reducibility theorem.

These are matrix-argument functions, not ordinary scalar hypergeometric functions. Passing their arrays directly to an ordinary `hyper` routine would give the wrong answer.

## Reproduction

New Python scripts require Python 3, mpmath and SymPy. From this directory:

```sh
python code/rank_two_checks.py verification/rank_two_checks_rerun.json
python code/recompute_d3_periods.py
python code/scalar_catalog_search.py
```

The first command performs 1107 exact checks, independent finite coefficient constructions and interior partial-series comparisons at 90 working digits. The second reevaluates the retained primitive formulas at 100 working digits; it is formula-side consistency, not an independent integral. The third reproduces the bounded 6479-entry ordinary-3F2/4F3 catalogue search (85 working digits, relation tolerance 1e-57, coefficient budget 1e6). The completed recorded search returned no relation with a nonzero coefficient of the target. This finite search proves neither independence nor impossibility of a scalar reduction.

Compile the note with an ordinary LaTeX distribution containing the packages named in its preamble:

```sh
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
```

## Verification records

New records are `verification/rank_two_checks.json`, `fresh_primitive_values.json`, `scalar_catalog_search.json`, `rank_two_preservation.json`, and `rank_two_pdf_checks.json`. All 747 preceding mathematical display blocks are preserved verbatim and in order. The rendered new appendix was visually checked; the final build has no overfull boxes or undefined references.

Historical code and records are retained under the other subdirectories. They document earlier revisions and are not assertions that those calculations were rerun now.
