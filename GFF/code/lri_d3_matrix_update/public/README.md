# lri_d3_matrix_update: rank-two (Jack α = 2) identification of the d = 3 Horn functions

This folder is package 15 of the research bundle `LRI_complete_research_bundle.zip`, shipped byte-identical without
its TeX/PDF note revisions (see "Not shipped" below). Only `public.mk` and `public/` were added for the public release.
The bundle's own documentation is `README.md`. The new
scripts of this revision are `code/rank_two_checks.py`, `code/recompute_d3_periods.py` and
`code/scalar_catalog_search.py`, and their records are in `verification/`. The rest of the tree was inherited from the
preceding revisions (it includes the d = 3 half-shift code of `GFF/code/lri_d3_reduction_update`) and is kept so that the
package stays self-contained.

## Not shipped

Author rule (2026-10-16): one TeX note per direction. The package's rank-two appendix `proofs/rank_two_appendix.tex`
and its build `rank_two_identification.pdf` are merged into the condensed note (`GFF/note/`), Section 19, subsections
"The real rank-two hypergeometric normalization" to "Five loops: an exact three-term standard-function dictionary".
`long_range_ising_complete.tex`/`.pdf` and `general_dimension_complete.pdf` are full builds of the earlier research
note. These 5 files are named in `public/dropped_paths.txt`. No test or replay reads them. `public/BUNDLE_SHA256SUMS`
ships unchanged and still lists them; the replay accepts exactly these paths as absent and fails on any other missing
or changed file. The package's own `README.md` still names the notes.

## What it gives

The residual two-variable Horn functions of the d = 3 primitive periods are, coefficient by coefficient, standard real
hypergeometric functions of a 2 × 2 matrix argument with Jack parameter α = 2. The condensed note covers this in the
section "Three dimensions", subsections "The real rank-two hypergeometric normalization" and "Five loops: an exact
three-term standard-function dictionary":
- Q_3 = 4π² ₃F₂^(α=2)(3/4, 3/4, 3/4; 3/2, 3/2; I₂) − Γ(1/4)¹⁰/(48 π^{7/2}) (rt:Q3);
- 𝔥₄(0) = ₄F₃^(α=2) and 𝔥₄(1/8) = ₅F₄^(α=2) at I₂ (rt:P4blocks);
- the five-loop blocks as three functions each, at −I₂ (rt:H7matrix);
- the local-coefficient check (rt:scalarDistinction):
  - ₃F₂^(α=2)(…; zI₂) = 1 + 3/8 z + 2769/12800 z² + 15113/102400 z³ + …;
  - the scalar ₃F₂ with the same parameters is 1 + 3/16 z + 1029/12800 z² + 9317/204800 z³ + …

The matrix superscript and the matrix argument cannot be dropped. Nothing here reduces these values to ordinary scalar
pFq values.

## Run

From this folder (Python 3 with `pip install -r public/requirements.txt`):

```sh
make -f public.mk test     # about 5 s:  checksums, rerun of rank_two_checks.py, the shipped records against the note
make -f public.mk replay   # about 20 s: also reruns recompute_d3_periods.py (Q_3, P_4(3), P_5(3) at 100 digits)
make -f public.mk search   # optional, about 1 min: reruns the bounded scalar catalogue search
```

`rank_two_checks.py` performs 1107 exact coefficientwise checks and compares the interior partial sums at 90 digits.
`recompute_d3_periods.py` re-evaluates the retained period formulas at 100 digits. This is a formula-side consistency
check, not an independent integral; the independent Gamma-kernel comparison is in `lri_d3_reduction_update`.
`scalar_catalog_search.py` repeats a finite PSLQ search over 6479 ordinary ₃F₂/₄F₃ values, which found no relation. The
note quotes this search in Section 19 (d3:values) as a bounded search for the two-variable value of Q_3. Its rerun is the optional
target `search` (about 1 min), not part of `replay`. It proves neither independence nor impossibility.

Each target copies the package to `.work/pkg/` (git-ignored) and runs the original commands of `README.md` unchanged
there. It then compares the results with the shipped records and with
`../../results/closed_forms_3/d3_specialization_quoted.json`. The table goes to `.work/REPLAY.md`. Any FAIL exits
non-zero. Locally (macOS, Python 3.10.12, mpmath 1.3.0) the replay gave 22 PASS, 0 FAIL, and the search 3 PASS (57 s); without the dropped notes (2026-10-16, symmetry) the replay
gives 22 PASS, 0 FAIL and one INFO row that counts the 5 absent files. Every
rerun was bitwise equal to the delivered record.

## Files used by the public targets

| file | role |
|---|---|
| `code/rank_two_checks.py` | hook-product weights, wheel and five-loop partition coefficients, the matrix Kummer fixed point, interior partial sums; writes the record named on its command line |
| `code/recompute_d3_periods.py` | imports `code/general_d3/d3_reduction.py` of this tree; writes `verification/fresh_primitive_values_rerun.json` |
| `code/scalar_catalog_search.py` | reads `verification/fresh100_input.json`, writes `verification/scalar_catalog_search.json` |
| `verification/rank_two_checks.json`, `fresh_primitive_values.json`, `scalar_catalog_search.json` | the delivered records |
| `public/BUNDLE_SHA256SUMS` | the bundle's SHA-256 of all 207 files, verified by `make test` (the package has no list of its own): every shipped file matches, and only the 5 paths of `public/dropped_paths.txt` are absent |

## Overlap with other GFF packages

177 of the bundle package's 207 files are byte-identical to `lri_general_periodization_update`, and 191 to
`lri_d3_reduction_update`. They are kept, so that this package is a self-contained bundle tree (less the notes above).

`GFF/code/LRI_C5_d3/assemble_c5_d3.py` reads `../lri_d3_matrix_update/code/general_special/coefficient_values_new.json`
(the archived 11-digit nonprimitive master values). This folder must therefore keep its name, sit next to `LRI_C5_d3`
under `GFF/code/`, and keep that file.

## Caveats

- The partial-sum comparisons are finite truncations at 90 digits, not enclosures. The coefficientwise identities are
  exact.
- `code/general_special/check_A_d1.py` (inherited, not run) hard-codes a path of the sandbox in which it was generated
  (`/mnt/data/...`).
