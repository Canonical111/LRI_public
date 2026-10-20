# Long-range Ising: coefficients and derivations (condensed note)

This folder holds the condensed research note behind the perturbative coefficients of the paper: the epsilon expansion
of the perturbed generalized free field, C0 to C5 in closed form and C6 to C8 in d = 1, 2, 3, with the derivations, the
numerical designs, the error analysis and the independent checks. Part V adds a second observable of the same graphs and
master functions, the bulk one-point coefficient a_phi2 through eps^6 at general d.

## Files

- `long_range_ising_condensed.tex`: the LaTeX source (standalone; no figures, `.bib` database or other TeX files).
- `long_range_ising_condensed.pdf`: the compiled note, 373 pages, built from this TeX.
- `tools/check_note.py`: structural checks of the TeX (references, labels, citations) and of the file hashes; Python
  standard library only.
- `Makefile`: `make all` builds the PDF with latexmk, `make check` runs the structural checks.
- `MANIFEST.json`: SHA-256 and size of every file in this folder except itself.

## Build and check

```bash
python3 tools/check_note.py --checksums     # hashes of the delivered files, then references, labels and citations
latexmk -pdf -interaction=nonstopmode -halt-on-error long_range_ising_condensed.tex
```

Without `latexmk`, run `pdflatex long_range_ising_condensed.tex` three times. A local rebuild may change the PDF's
hash (timestamps, TeX version, fonts) without any change of content, so run `--checksums` before rebuilding.

## Reading order

| Part | Subject | Pages |
|---|---|---:|
| I | Current coefficients and their closed forms through fifth order, the special-function representation of C6(1), notation, RG inversion, graph weights, subtraction conventions (Sections 1-3) | 4-27 |
| II | One-dimensional analytic coefficients through fifth order, with complete master and period proofs and the checks of the analytic coefficient (Sections 4-14) | 27-59 |
| III | Arbitrary-dimensional coefficients through fifth order, the d = 2, 3 specializations, the closed form of C5(2) with its proofs, and the generic-dimensional reduction of the nonprimitive masters (Sections 15-21) | 59-222 |
| IV | C6(1) from exact all-graph sums and its analytic representation, C6(2), C6(3), full C7(1), C7(2), C7(3), and full C8(1), C8(2), C8(3) with their independent checks (Sections 22-32) | 222-306 |
| Section 33 | Reproduction and data dependencies: for every result, the code package, the records and the replay; the provenance of every merged block | 306-317 |
| V | The bulk one-point coefficient a_phi2 through eps^6 at general d, its values at d = 1, 2, 3, the map to the thermal coefficients, the comparison with published bootstrap figures and the checks made for this note (Section 34) | 317-334 |
| Appendix A | Complete 118-row four- and five-loop residue certificate | 334-343 |
| Appendix B | Derivation of the special-function representation of C6(1) | 343-370 |
| References | | 370-373 |

## Current numerical entries

| Coefficient | Reported value | Sampling standard error of the underlying estimator |
|---|---:|---:|
| C6(1) | 14331.68703275805 (finite special-function representation, Sections 1.2 and 22.9) | none; the independent deterministic all-graph sum gives 14331.6870328(5), i.e. 14331.68703277 ± 0.00000049 (unrounded 14331.68703276838) |
| C6(2) | 362.366 ± 0.004 | 0.0007997307 (estimator 362.36647176375726) |
| C6(3) | 33.5754 ± 0.0005 | 0.0001185495235 (estimator 33.57542664131543) |
| C7(1) | −322550 ± 41 | 10.08791295 (estimator −322549.8888129889) |
| C7(2) | −3876.1 ± 2.1 | 0.5244496691 (estimator −3876.1260927949925) |
| C7(3) | −220.35 ± 0.13 | 0.0318188006 (estimator −220.35448047392794) |
| C8(1) | (8.060 ± 0.017) × 10^6, i.e. 8059767 ± 17000 | 4209.576151 (estimator 8059766.723129955) |
| C8(2) | 45990 ± 33 | 8.216820958 (estimator 45990.00263614446) |
| C8(3) | 1602.6 ± 3.9 | 0.9516489064 (estimator 1602.6052229663408) |

The reported C6(1) is the finite special-function representation of a reduced analytic expression that is taken as an input and is derived neither in the note nor in its package (Sections 1.2, 1.3 and 22.9). The all-graph sum does not use that expression; the representation lies 1.03 × 10^-8 below its unrounded value, or 0.021 of its allowance.

C8(2) also has an independent check from a separately developed code, which shares the method and the payloads of loops three to seven (Section 31.7). It gives 46006.1 ± 13.4 (sampling SE), +1.03 combined SE from the estimator. It is not combined with the reported value.

C8(3) also has an independent check from a separately developed code, which shares the method and the seventh-order integrator (Section 32.7). It gives 1600.98 ± 3.97 (sampling SE), −0.40 combined SE from the estimator. It is not combined with the reported value.

The analytic C0–C5 formulas are unchanged from the supplied final note; Section 1.1 collects them. The reported allowances are empirical and are **not** rigorous intervals, truncation-error bounds, or independent certification of the common graph/renormalization framework. Section 1 tabulates the rule behind every allowance and when it was fixed, and Section 1.3 says what is proved, conditional or numerical. For C7(1) the ±41 is the output of the rule fixed before production, and −322550 ± 41 is the result; a post hoc truncation-aware estimate, −322524 ± 38, lies inside it and is a check (Sections 1 and 27). For C8(1) the ±17000 is the output of the rule fixed before production, set by four sampling errors (16838.3); the number of batches was raised from nine to fourteen after interim results (under the stopping rule set first, nine batches give 8061480 ± 5300 with allowance ±22000), and the degree eight to nine check step, −113, is below one per cent of the allowance (Section 30). For C8(2) the ±33 applies the rule of C7(2) after the result, since no allowance was registered with the production decision: four sampling SEs (32.87; estimator 45990.00263614446, SE 8.216820957752926), which exceed both half-stream deviations (2.39), rounded up to a multiple of 1 (Section 31). For C8(3) the ±3.9 applies the same rule after the result: four sampling SEs (3.81; estimator 1602.6052229663408, SE 0.9516489064069612), which exceed both half-stream deviations (0.046), rounded up to a multiple of 0.1; its coverage is conditional on a finite variance, for which Section 32.5 gives empirical evidence, not a bound.

## Code, records and replay

Section 33 of the note lists, for every result, the code package, the records it is recomputed from and the hosted raw
data. In this repository the packages are in `GFF/code/<package>/` (package paths in the note are relative to
`GFF/code/`), the records in `GFF/data/` and the published outputs in `GFF/results/`. In every package,
`make -f public.mk test` runs its tests and `make -f public.mk replay` recomputes every number the note quotes for that
package and compares it with the quoted digits; `GFF/REPRODUCE.md` gives the order and the cost of each level.

| Note | Result | Packages in `GFF/code/` | Records |
|---|---|---|---|
| Parts II, III; Section 1.1 | C0-C5 in closed form, d = 1 and general d | `lri_numerical_resolution`, `lri_psi_complete_update`, `lri_fixed_hypergeometric_update` (d = 1); `lri_general_special_functions_update`, `lri_general_closed_update`, `lri_general_periodization_update` (general d) | `GFF/results/closed_forms_1`, `GFF/results/closed_forms_general` |
| Sections 17-18 | closed forms of L2, K2 and C5(2) | `LRI_C5_d2_simplify`, `LRI_C5_d2_proof` | `GFF/results/closed_forms_2` |
| Sections 19-21 | d = 3 specialization; generic-dimensional reduction of L_d, Z_d, K_d | `lri_d3_reduction_update`, `lri_d3_matrix_update`, `LRI_C5_general_d`, `LRI_C5_d3` | `GFF/results/closed_forms_general`, `GFF/results/closed_forms_3` |
| Section 22, Appendix B | C6(1) and its analytic representation | `LRI_C6_1D_HPC`, `C6_research_note`, `LRI_C6_closed_form_review` | `GFF/data/C6_1`, `GFF/results/C6_1` |
| Sections 23-26 | finite kernels, power compensation, C6(2), C6(3) | `lri_C6_d2_complete_update`, `lri_C6_d3_complete_update`, `LRI_C6_D2_HPC`, `LRI_C6_D3_HPC` | `GFF/data/C6_2`, `GFF/data/C6_3`, `GFF/results/C6_2`, `GFF/results/C6_3` |
| Sections 27-29 | full C7(1), C7(2), C7(3) | `LRI_C7_HPC`, `LRI_C7_D2_HPC`, `LRI_C7_D3_HPC` | `GFF/data/C7_*`, `GFF/results/C7_*` |
| Sections 30-32 | full C8(1), C8(2), C8(3) and the independent checks of C8(2), C8(3) | `LRI_C8_HPC`, `LRI_C8_D2_HPC`, `LRI_C8_shared`, `LRI_C8_D2_HPC_optimized`, `LRI_C8_D3_HPC`, `LRI_C8_D3_OPT` | `GFF/data/C8_*`, `GFF/results/C8_*` |
| Part V (Section 34) | bulk one-point coefficient a_phi2 through eps^6 | `lri_ope_reproducibility` (supplied by the author, 16 October 2026), `ope_checks` (the checks of Section 34) | in the packages (`results/`, recorded outputs) |

Each package's `REVIEWS.md` summarizes the reviews it received (by OpenAI Codex and by Claude Code sessions), with the
recommendations that were overruled and what was never reviewed; its `PROVENANCE` fragment says who wrote it. The
earlier research archive `LRI_complete_research_bundle.zip`, from which the analytic packages above are taken, is not
part of the repository; packages of it that hold only superseded estimates are not included. The separate TeX notes that
came with the packages written by OpenAI GPT-6 astra, and the note of the bulk one-point package, are merged into this
note and are not shipped: the GFF folder has one TeX note.

## Editions

The note is a condensation of a 212-page research note, without reduction of the 11-point body font or the 23 mm margins,
updated as new calculations were completed: C6(1), C7(1), C6(2), C6(3), C7(2), C7(3) on 1 October 2026; the closed form
of C5(2) on 2 October; C8(1) and the generic-dimensional reduction on 3 October; C8(2) and the analytic representation of
C6(1) on 8 October; the independent check of C8(2) and the collected closed forms of Section 1 on 10 October; C8(3) with
its independent check on 12 October; C8(1) from fourteen batches on 13 October. This public edition (13 October 2026)
rewrites Section 33 for this repository and corrects a few digits that the replays found misprinted:

| Place | Printed before | Corrected |
|---|---|---|
| Section 20, pole-node check | 3e-21 | 5e-21 |
| Section 21.10, the two identities | 2e-13 | 1e-12 absolute (3e-15 relative) |
| Section 18.7, twelve cell quadratures | 18 to 25 digits | 18 to 24 digits |
| Section 24, Cauchy comparison | 7.39e-30 | 7.38e-30 |
| Section 24.3, power-sector correction | -8.03e-34 | -8.02e-34 |
| Section 28, three-loop power-jet SE | 0.00000043 | 0.00000042 |
| Section 31, tail-graph share of Var(C8) | 27.5% | 27.6% |
| Section 31, F2 statistic | 4.3e-16 | 4.2e-16 |
| Section 32.4, power-free entry | 0.001 | 0.010 |
| Section 32.5, median ratios | 0.82 to 0.88 | 0.82 to 0.87 |
| Section 22.6, successive changes of C6(1) | below 1e-11 from M = 24 | at most 4.4e-9 from M = 28 |
| Section 30.4, comparison with the truncation-aware C7(1) | 0.3 errors | 0.4 combined standard errors |

and a few phrases in Sections 1.2, 22, 27, 29 and 30 (what a quoted ratio refers to, what a bootstrap resamples, a cost in
physical and charged core-hours). No reported coefficient or allowance changed.

The review edition of 15 October 2026 applies a readability review of the whole note: Section 1 gains a table of the
allowance rules and when each was fixed, a status table (Section 1.3: proved here, in a companion file, conditional or
numerical) and a list of symbols with more than one meaning (Section 1.4); references a reader cannot open were
replaced, history phrasing rewritten and the spelling made American. No reported coefficient or allowance changed.
A follow-up of 16 October 2026 quotes the values of the two 64-point pilot campaigns behind the sampling hazard of
Section 30.3 (records in `GFF/data/C8_1/c8_hpc/runs/pilot8/`).

The one-note edition of 16 October 2026 adds Part V, the bulk one-point coefficient a_phi2 through eps^6 (a calculation
supplied by the author with its code and its own note, whose derivations, results and caveats Part V now contains, with
the checks made for this note), and merges the separate TeX notes of the packages into this note, as the author asked:
the derivation of the C6(1) representation becomes Appendix B; the seventh-order notes of `LRI_C7_HPC` were already
Section 27 apart from the randomization of its two point streams, now added; and from the earlier complete research note
Section 1 gains the lattice model, Section 3.1 the zero-dimensional benchmark of the graph weights (behind the sum rules
quoted in Sections 30 and 31), Section 14 the further checks of the analytic coefficient, and Sections 1.4, 8, 9 and 10 a few
values and caveats. No reported coefficient or allowance changed.

A check of the merged note by six independent readers (16 October 2026) led to a further revision by the three writers of
the merge. Status words now agree across the note; Section 33 has one provenance map of the merged blocks and says which
numbers `make replay` does not recompute; the arguments of Appendix B that were still only in files of the C6(1) package
(the S6 and S8 coefficient series, the wheel periodization identities, the M7 tail bound and the interval certificate)
are written out; material dropped from the earlier complete note is restored (the checks of the master K and the
external lattice comparison with its s = 0.8 tension, recomputed by `lri_numerical_resolution/public/lattice_comparison.py`);
the symbol list of Section 1.4 covers the merged material. No reported coefficient or allowance changed.
A recheck of that revision restored five L_d values of Section 20 to 28 digits, states wherever the C6(1) interval is
quoted that it reaches the reduced expression only through package identities not reproduced in the note, completes
the provenance map and records there that no merged source names its author.
