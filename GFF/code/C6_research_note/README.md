# C6(1): final-method research note

Start with **`note/C6_progress_note.pdf`**. Its corresponding **standalone
`note/C6_progress_note.tex`** contains its bibliography and all mathematical
input needed by the retained derivation. It compiles without external figures,
BibTeX, a network connection, shell escape, or files from the earlier note.

## This edition

The note is the final-method-only revision of the supplied 34-page progress
note. The new PDF has **28 pages**. It retains the agreed real log-sine / multiple
Clausen formula: two real polylogarithmic values, four ordinary Meijer G values,
and three unit-slope bivariate H values. The final coefficient, its parameter
lists and its 18-monomial known polynomial are unchanged.

The note omits unused special-function alternatives, exploratory basis searches,
companion identities, the primitive's spectral/first-moment detours, historical
progress tables and software fallback formulations. Material needed by the final
path has been moved or stated explicitly: ordinary-period input definitions,
gamma normalizations, the completed wheel symmetry, the primitive contour proof,
the seventh inner transform, wheel error-bound constants, and all primitive
recurrence matrices and seeds. Retained mathematics has not been abridged to
achieve the page reduction.

The supplied scientific **stage code, input snapshots and data are preserved**.
Some stage-local inputs describe previous representations because the original
verifiers use them as exact comparison data. Their presence in the archive does
not make those representations part of the revised method. Use the new
`code/reproduce_final.py` selection rather than the broader historical profiles.
`provenance/editorial_revision.json` records the revision and protected-formula
checks. No new physical or special-function identity is claimed by this edit.

## Mathematical scope

The supplied convention is

    Delta_E = 1/2 - epsilon/6 + sum_{n>=2} C_n(1) epsilon^n,
    r6 = 2187 C6(1).

The retained analytic value begins

    14331.6870327580543204454632552462171183173230619887904582...

The original graph/RG identification, model specification and coupling
normalizations are not independently reconstructed by the supplied downstream
code. The note states the corrected reduced expression as its analytic input
and preserves this limitation. The source correction is already included.
Do not add it again. `delta_n` is a positive trigamma difference, not a Kronecker
delta. `Wcentral` starts at n=1; the formula's `W0` includes n=0.

A fixed-value count is not a proof of a minimal or independent period basis.
The bivariate H functions are not ordinary univariate Wolfram `MeijerG` calls.
No Wolfram kernel was executed during this editorial revision.

## Structure

```
C6_research_note/
  README.md
  requirements.txt
  MANIFEST.sha256
  note/
    C6_progress_note.tex             final-method-only source
    C6_progress_note.pdf             compiled note
  code/
    reproduce_final.py              selected final-method task profile
    reproduce.py                    clean-workspace stage runner
    audit_final_note.py             reference and protected-formula audit
    make_outputs.py                 canonical formula and numerical reassembly
    build_note.py                   isolated three-pass LaTeX build
    audit_package.py                source and data integrity audit
    make_figures.py                 source-data plot (not needed by the note)
    wolfram/                       supplied ordinary-function transcriptions
    stages/                        supplied code and its transitive inputs
  inputs/
    canonical/                     formula specifications used by reassembly
    source_snapshots/               source documents/data
    upstream_reduced_setup.md       supplied analytic setup
  outputs/
    rerun/<task>/                  stdout, status, generated raw results
    tables/                        numerical CSV data
    figures/                       retained source-data plots
    reassembly.json
    build_report.json
    final_method_run.json
    final_note_audit.json
    package_audit.json
  provenance/
    editorial_revision.json
    source_manifest.json
    portability_patches.json
    environment.json
```

No TeX auxiliaries, Python caches, nested ZIP archives or font files are shipped.
Stage-local input and result files are intentional reproducibility dependencies,
not temporary build files.

## Dependencies

The supplied and rerun code uses Python 3.13.5, SymPy 1.14.0, mpmath 1.3.0 and
Matplotlib 3.10.8; the library versions are pinned in `requirements.txt`.
Calculations themselves do not require network access. Installation may.

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows instead: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

For the note, install TeX Live with `newtxtext`, `newtxmath`, `amsmath`,
`amssymb`, `mathtools`, `bm`, `geometry`, `booktabs`, `tabularx`, `array`,
`xcolor`, `microtype`, `fancyhdr`, `listings`, `hyperref`, and `cleveref`.
The build uses `pdflatex`; no external figures or pgfplots are required by
this edition. Font files are not distributed.

## Reproduce the final method

Run from the extracted archive root:

```sh
python code/reproduce_final.py
python code/make_outputs.py
python code/build_note.py
python code/audit_final_note.py
python code/audit_package.py --skip-manifest
```

`reproduce_final.py` selects 22 tasks: seven core numerical/interval tasks,
twelve exact algebra/transcription tasks and three Barnes comparisons. Every
stage runs in a temporary copy. Source inputs and recorded stage results are
not overwritten. Task commands, exit status, stdout and newly generated data
are saved under `outputs/rerun/`.

The default per-task process limit is 180 seconds. It is configurable, e.g.
`python code/reproduce_final.py --timeout 900`. A timeout is a failure, not a
numerical certificate. Use `--resume` only to retain already-passed records;
omit it when a new execution of every selected task is required. The archive
already contains the recorded results used by the note and postprocessor.

Individual stages may be selected through the lower-level runner:

```sh
python code/reproduce.py --profile core --only complete_smoke real_checks_45
python code/reproduce.py --profile exact --only cubic_exact compact_primitive_exact
python code/reproduce.py --profile numerical --only seventh_barnes
```

### Commands and outputs

| Task or command | Output | Role |
|---|---|---|
| `real_checks_45`, `real_checks_90` | `outputs/rerun/real_checks_*/generated/results/checks_*.json` | Real-function values checked against independent HPL/cosine constructions; floating point |
| `real_build` | `outputs/rerun/real_build/generated/results/all_real_representations.json` | Exact full-block and polynomial conversion; the `recommended_nine` field is used |
| `complete_smoke`, `complete_release`, `complete_refined` | `outputs/rerun/complete_*/generated/results/complete_*.json` | Dyadic enclosure of the supplied analytic assembly |
| `residual_intervals` | `outputs/rerun/residual_intervals/generated/results.json` | Wheel, seventh and primitive enclosures and normalizations |
| Twelve selected `exact` tasks | Each task's `execution.json`, stdout and generated data | Wheel symmetry, input coefficient identities, ordinary gamma kernels, primitive contour/factorization, seventh transform |
| `sixth_barnes`, `eighth_barnes`, `seventh_barnes` | `outputs/rerun/*_barnes/generated/results/numerical_40.json` | Separate numerical Barnes checks, not rigorous double-Barnes certificates |
| `make_outputs.py` | `outputs/reassembly.json`, `outputs/tables/*.csv`, canonical JSON | Full adopted-real reassembly; not subtraction from a known target |
| `build_note.py` | Final PDF and `outputs/build_report.json` | Three passes in an empty temporary directory containing only the TeX source |
| `audit_final_note.py` | `outputs/final_note_audit.json` | References, citations, removed-section checks and protected formula hashes |
| `audit_package.py` | `outputs/package_audit.json` | Code syntax, original source hashes, run records and build consistency |

The code for all selected inputs is included. The wheel certificate constructs
finite rational tail corrections; it does not sum an infinite asymptotic
expansion. The seventh evaluator uses finite Euler weights. The primitive
recurrence, its two matrices, seed polynomials, finite weights and last-two-state
tail bound are stated in Appendix A of the note.

## Execution evidence for this revision

The source package contained 31 passed task records. During this editorial
revision, six core tasks, all twelve final-method exact tasks and all three
Barnes comparison tasks were executed again: **21 new task executions**. The
previously shipped `residual_intervals` certificate and its execution record
are retained unchanged. The nine other nonselected records remain source
records. The final profile's summary was collected with `--resume`; this is
explicit in `outputs/final_method_run.json` and must not be read as 22 new
executions. A process-level time limit interrupted an attempted full-profile
rerun during the residual task; no output from that interrupted run is used
as a new result.

The real-form postprocessor was rerun and its exact polynomial checks passed.
Its discrepancy from the supplied refined interval midpoint remains about
`4.262e-93`; the 40-digit Barnes-seventh reassembly discrepancy is about
`4.144e-37`. These are floating-point cross-checks. The interval's scope remains
the supplied analytic expression, conditional on the source identities, not
an independently rederived physical six-loop coefficient.

The revised TeX was compiled independently in three passes. The final-method
formula, real known polynomial and all retained parameter-list equations were
checked against the original note. PDF layout was inspected separately; no
new mathematical proof is implied by those editorial checks.

## Compile the source by itself

Copy only `note/C6_progress_note.tex` into an empty directory, then run:

```sh
pdflatex -interaction=nonstopmode -halt-on-error C6_progress_note.tex
pdflatex -interaction=nonstopmode -halt-on-error C6_progress_note.tex
pdflatex -interaction=nonstopmode -halt-on-error C6_progress_note.tex
```

`python code/build_note.py` performs this isolated build automatically. It
copies only the PDF back, recording compiler and source/PDF hashes.

## Integrity

`MANIFEST.sha256` covers shipped files. Regenerating outputs can change timings
and hashes legitimately. Before rerunning, use `python code/audit_package.py`
to check the shipped manifest. After intentional reruns, use `--skip-manifest`
and compare the generated data and scope records.
