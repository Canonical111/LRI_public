# C6 lower-period Meijer G reduction

This is a **partial** reduction. It replaces the finite U4,U6 block by a smaller
ordinary Meijer G expression. It does not evaluate the wheel, seventh
logarithmic block, or primitive Pa.

- `DERIVATION.md`: exact identities, normalization, and analytic justification.
- `C6_lower_MeijerG_patch.wl`: standalone Mathematica expressions and finite-part assembly.
- `inputs/previous_expression.json`: unmodified accepted input.
- `results/updated_expression.json`: complete retained partial formula and legacy records.
- `build_verify.py`: 47 finite checks, including static Wolfram checks.
- `numerical.py`: independent hypergeometric/Barnes comparison at 40 and 80 digits.
- `results/`: executed check reports.

The `.wl` file has **not** been executed in a Mathematica kernel. No new rigorous
interval or full-C6 numerical evaluation is claimed. The one-value packing is
not an arithmetic-independence reduction.
