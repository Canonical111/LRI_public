# lri_d3_reduction_update: the d = 3 half-shift reduction of the primitive periods

This folder is package 14 of the research bundle `LRI_complete_research_bundle.zip`, shipped byte-identical without
its TeX/PDF note revisions and its `history/` drafts (see "Not shipped" below). Only `public.mk` and `public/` were added
for the public release. The bundle's own documentation is
`README_d3_reduction.md`. The scripts in `code/general_d3/` and their records in `verification/general_d3/` are the
three-dimensional part. The rest of the tree was inherited from earlier bundle revisions (general-d closed forms,
periodization, P5 hypergeometric forms) and is kept so that the package stays self-contained. No public target runs it.

## Not shipped

Author rule (2026-10-16): one TeX note per direction. The package's note revisions are merged into the condensed note
(`GFF/note/`), which is the documentation:
- `three_dimension_addition.tex` and its build `three_dimension_reduction.pdf`: Section 19 ("Three dimensions:
  half-shift determinants and rank-two functions");
- `primitive_periodization_addition.tex` and `primitive_periodization_chapter.pdf`: Section 18 ("Finite periodization
  of the primitive sector");
- `general_dimension_closed_addition.tex` and `general_dimension_closed_chapter.pdf`: Section 17 ("Finite
  multivariable representations for the nonprimitive masters");
- `long_range_ising_complete.tex`/`.pdf` and `general_dimension_complete.pdf`: full builds of the earlier research note.

`history/` (19 files) holds superseded drafts of earlier note revisions and their build scripts. These 28 files are
named in `public/dropped_paths.txt`. No test or replay reads them. `public/BUNDLE_SHA256SUMS` and `archive_manifest.json`
ship unchanged and still list them; the replay accepts exactly these paths as absent and fails on any other missing or
changed file. The package's own READMEs still name the notes.

## What it gives

At d = 3 the three primitive periods of the five-loop coefficient are reduced to finitely many fixed hypergeometric values
with positive rational parameters. The condensed note covers this in the section "Three dimensions: half-shift
determinants and rank-two functions":
- Q_3 = 4π² 𝔥₃(0) − Γ(1/4)¹⁰/(48 π^{7/2}) (eq. td:Qanswer);
- P_4(3) (td:P4answer) and P_5(3) (td:P5answer);
- the half-shift determinant identities;
- the residue weights (td:residueWeights);
- the Dixon and Rogers–Dougall Gamma evaluations (td:gammaAmplitudes);
- the explicit two-variable Horn arrays (td:Hbase, td:Hseven).

The values are

| period | value (33 decimals, as in the note) | formula − fresh Gamma-kernel integration |
|---|---|---|
| Q_3 | 5.01710256455385536959085484569018… | −1.5 × 10⁻⁵¹ |
| P_4(3) | 62.0583279434066724664633885840967… | −1.5 × 10⁻⁵² |
| P_5(3) | 240.340317759083549816366546388004… | −2.4 × 10⁻⁵³ |

The residuals are observed differences between two independently written evaluations. They are not interval bounds.
Q_3 and P_4(3) enter C4(3) and C5(3), and P_5(3) enters C5(3); the closed form of C5(3) is in `GFF/code/LRI_C5_d3`. The
rank-two (matrix-argument) form of the same functions is in the sibling package `GFF/code/lri_d3_matrix_update`.

**Not achieved here, as the package says:**
- a reduction of the remaining two-variable values to ordinary one-variable pFq values;
- any new evaluation of K_3, L_3 or Z_3.

## Run

From this folder (Python 3 with `pip install -r public/requirements.txt`):

```sh
make -f public.mk test     # about 5 s:  checksums, rerun of check_exact.py, the shipped records against the note
make -f public.mk replay   # about 4 min on one core: also reruns verify_d3.py and check_spectral.py
```

Each target copies the package to `.work/pkg/` (git-ignored), runs the original commands of `README_d3_reduction.md`
unchanged there (the scripts write their records next to their inputs), and compares the results:
- each rerun record with the shipped one;
- the shipped and rerun records with the numbers quoted by the note, listed with tolerances in
  `../../results/closed_forms_3/d3_specialization_quoted.json`.

The PASS/FAIL table goes to `.work/REPLAY.md`. Any FAIL exits non-zero. Locally (macOS, Python 3.10.12, mpmath 1.3.0) the
replay gave 69 PASS, 0 FAIL, and every rerun was bitwise equal to the delivered record. Without the dropped notes
(2026-10-16; symmetry, Intel Xeon Gold 6148, Python 3.13.3, mpmath 1.3.0) it gives 69 PASS, 0 FAIL and one INFO row
that counts the 28 absent files.

## Files used by the public targets

| file | role |
|---|---|
| `code/general_d3/d3_reduction.py` | evaluators of the ordinary moments, the ordered Horn sums and the period formulas |
| `code/general_d3/check_exact.py` | 25 exact SymPy identities and 288 rational Horn coefficients; writes `exact_algebra.json`, `horn_arrays.json` |
| `code/general_d3/verify_d3.py` | Q_3, P_4(3), P_5(3) at 55 and 90 digits; projections, mode identities and complex-node variants at 75 digits; six literal `mpmath.hyper` calls at 40 digits |
| `code/general_d3/check_spectral.py` | fresh real-axis Gamma-kernel integrals at 45 and 60 digits, with changed breakpoints and tail settings |
| `verification/general_d3/*.json` | the delivered records. `comparison_summary.json` (residuals, and C2–C4(3) assembled with the new periods) is not written by any shipped script. The replay recomputes its residuals from `period_values.json` and `fresh_spectral.json` |
| `archive_manifest.json` | the package's own checksum list (225 files), verified by `make test`: every shipped file matches, and only the 28 paths of `public/dropped_paths.txt` are absent |
| `public/BUNDLE_SHA256SUMS` | the bundle's SHA-256 of all 226 files, verified by `make test` in the same way (198 shipped) |

## Overlap with other GFF packages

202 of the bundle package's 226 files are byte-identical to `lri_general_periodization_update` (shipped by the generic-d
part, trimmed to its own layer). Another 177 overlap with `lri_general_closed_update`, and 191 with
`lri_d3_matrix_update`. They are kept, so that this package is a self-contained bundle tree (less the notes above).

## Caveats

- No interval arithmetic. The asymptotic tails are numerical accelerations, and the agreement figures are observed
  residuals.
- `code/general_special/check_A_d1.py` (inherited, not run) hard-codes a path of the sandbox in which it was generated
  (`/mnt/data/...`). It is kept byte-identical because the checksum lists bind it.
