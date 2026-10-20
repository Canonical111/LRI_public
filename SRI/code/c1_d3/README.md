# First-order 3d long-range/short-range Ising crossover

This is a self-contained research and reproducibility snapshot for **C₁⁽³⁾ only**. Start with [`note/ising3d_C1_note.pdf`](note/ising3d_C1_note.pdf). Its LaTeX source is one standalone file: all equations, input tables, and bibliography are embedded. No prior conversation, companion document, external image, bibliography file, or unpublished database is needed to understand or reproduce this snapshot.


## Review revision: interpretation, derivations and executable checks

This revision addresses the attached review in [`review/RESPONSE_TO_REVIEW.md`](review/RESPONSE_TO_REVIEW.md). It preserves the final method and all conformal-block recurrence and retained-spectrum table bodies, adds its missing folding/normalization/sign derivations, and puts the necessary input-feasibility and assumption-sensitivity tests directly in the note. These tests are part of interpreting the final method, not abandoned approaches.

**The central input vector is infeasible in the nominal final LP:** 68 of 552 rows fail, all in the spin four-point channel. The minimum maximum displacement in that fixed LP is 0.5735097802 nominal box units, or 1.1470195604 quoted-error units. This is neither a common displacement of every input nor a statistical significance. It does not exclude the *number* C1_retained from the final interval.

The revised code loads the main reference coefficients and denominator allowance from current results, checks the required sign conditions, protects the full receipt against default side-profile overwrites, and reports incomplete verification runs without crashing. The complete 20-stage scientific workflow has been rerun from scratch with these changes. Numerical values are unchanged at the reported precision; 23 expanded regression checks pass. Additional isolated gap/padding and regenerated input-box sensitivity runs are supplied under `outputs/review_validation/`.

The single `.tex` remains independently compilable. Compiler auxiliaries and rendered inspection images are not included. The full supplied review is retained for attribution; unavailable reviewer cluster scripts are not represented as part of this package.

## Scientific result and status

The convention is

```text
Delta_epsilon_LR = Delta_epsilon_SR + C1*delta + O(delta^2)
delta = (s_star - s)/2
s_star = 3 - 2*Delta_sigma_SR
C1 = a0/b0
```

The retained 60-primary calculation gives

```text
a0 = 3.3474594916917857
b0 = 12.254914105481044
C1_retained = 0.27315242382601645
```

The current nominal **conditional numerical interval** is `[0.2697959227069642, 0.27521350074603207]`. Doubling nonlinear crossing allowances gives `[0.2692738234303526, 0.27541036263294777]`. The outward-rounded range for this particular scenario is **[0.2690, 0.2760]**. Report it next to the retained value **0.27315242**, not as a new symmetric best-fit measurement. Its offsets from 0.2732 are about −0.0042 and +0.0028.

The midpoint 0.2725 is not a new best-fit correlator evaluation. **The range is not robust to modest gap or box changes**: matched ten-update runs with gaps (8,6.5) or (7,7) already extend outside it. The note and generated sensitivity tables expose this dependence. The interval is **not a certified physical bound and not a statistical confidence interval**. Its principal assumptions are that all relevant unlisted even primaries have dimension at least 8, all relevant unlisted odd primaries have dimension at least 7, retained inputs lie inside twice their quoted error ranges, the stated sparse-bootstrap constraint on the nondegenerate epsilon-prime coupling applies, and the numerical nonlinear/tail allowances are adequate. The note explains each assumption and its limitations. A weaker-gap `(6,6)` scenario gives `[0.26400063878666075, 0.2784178764133668]` and remains conditional.

**Current machine-readable summary:** [`outputs/tables/current_summary.json`](outputs/tables/current_summary.json). Its certified-interval and statistical-confidence fields are explicitly null.

**Historical results:** files under `outputs/reference/precision/`, and the regenerated `outputs/reproduced/precision/SUMMARY_RESULTS.json`, preserve an earlier gap-eight-in-both-sectors estimate. The old odd gap-eight assumption is superseded by the current odd gap-seven scenario. Do not mistake that legacy `SUMMARY_RESULTS.json` for the current headline result. The old central selection is also retained to reproduce the T-prime correction and crossing improvements.

## Directory structure

```text
ising3d_C1_reproducibility/
├── README.md
├── requirements.txt                 # compatible minimum direct dependencies
├── requirements-pinned.txt          # exact direct versions used for this release
├── Makefile                         # optional convenience targets
├── SHA256SUMS                       # hashes of all delivered files except itself
├── note/
│   ├── ising3d_C1_note.tex           # single-file, independently compilable source
│   └── ising3d_C1_note.pdf           # compiled research note
├── code/
│   ├── c1_precision/                # block recurrences, first-order functionals,
│   │                                # data loader, input/crossing/domain tests
│   ├── c1_refinement/               # affine crossing, LP, remainder optimization
│   └── workflow/                    # reproduction, verification, assets, PDF build
├── data/
│   ├── inputs/                      # raw and updated spectrum, low inputs,
│   │                                # original selection and assumptions
│   └── provenance/                  # source bibliography, source archive hashes,
│                                    # extraction/refactoring/documentation changes
└── outputs/
    ├── reference/
    │   ├── precision/               # selected supplied numerical evidence
    │   └── refinement/              # supplied bases, LP arrays and checks
    ├── reproduced/
    │   ├── precision/               # fresh first-order and legacy diagnostics
    │   ├── refinement/              # fresh current scenarios and validation
    │   ├── verification/            # this run's regression report
    │   └── run_receipt.json          # exact scripts, arguments, dependencies,
    │                                # exit status, outputs, elapsed times
    ├── review_validation/           # fixed-LP audit and isolated sensitivity runs
    ├── tables/                      # generated CSVs and current summary JSON
    ├── figures/                     # generated vector PDFs and PNG previews
    └── verification/                # regression, environment, PDF build,
                                     # layout, assets and relocation checks
```

`reference/` and `reproduced/` are intentionally separate. The former is a regression baseline; the latter is evidence from a fresh computation. The `.npz` conformal-block bases and final LP arrays are reusable scientific data needed by targeted checks, not disposable intermediates. Iteration checkpoints, bytecode, unused fitting experiments, unrelated research, TeX logs/auxiliaries, and rendering contact sheets are not distributed.

## Dependencies

The tested interpreter is Python 3.13.5 on Linux. The source uses Python 3.10+ syntax. The tested direct packages are NumPy 2.3.5, SciPy 1.17.0, mpmath 1.3.0, threadpoolctl 3.6.0, and matplotlib 3.10.8. The exact environment is recorded in `outputs/verification/environment.json`.

NumPy, SciPy, mpmath, and threadpoolctl are required for numerical reproduction. Matplotlib is required only for separately generated figures. SciPy includes the HiGHS linear-program solver; no SDPB installation, proprietary solver, solver license, GPU, or network service is used. After installation, reproduction is offline. Results may vary in the last floating-point digits across platforms and solver versions; the regression checks use numerical tolerances, not byte identity.

Install in a virtual environment:

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell alternative:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For the exact tested direct dependency versions, use `requirements-pinned.txt` instead. That file is a tested direct-package snapshot, not a complete operating-system or transitive-dependency lock. An older interpreter may need the unpinned requirements if the newest pinned package wheels do not support it.

PDF compilation needs `pdflatex` and the following standard TeX packages: `fontenc`, `lmodern`, `geometry`, `amsmath`, `amssymb`, `mathtools`, `bm`, `booktabs`, `longtable`, `array`, `microtype`, `enumitem`, `fancyhdr`, `xcolor`, `listings`, `hyperref`, and `bookmark`. A sufficiently complete TeX Live or MiKTeX installation is suitable. The provided PDF was built with pdfTeX 1.40.26 / TeX Live 2025-dev. No shell escape, custom font files, external bibliography processor, or Internet access is required at compilation time.

## Full numerical reproduction

Run from the extracted top-level folder:

```sh
python code/workflow/reproduce.py full --from-scratch
python code/workflow/verify.py results
python code/workflow/make_assets.py
python code/workflow/build_pdf.py
```

The full scientific run contains **20 computational steps** and regenerates all numerical dependencies rather than reading archived numerical seeds. The driver resolves paths relative to itself, sets `C1_INPUT_DIR`, creates a temporary pair of sibling scientific directories, and sets BLAS/OpenMP thread counts to one. It then copies final JSON/NPZ outputs into `outputs/reproduced/` and deletes the temporary workspace. No files under `outputs/reference/` are overwritten.

`run_receipt.json` records every script and argument, exit status, generated file, elapsed time, and any dependency seeds. The delivered full-run receipt has `status: "passed"`, `from_scratch: true`, and an empty `cached_dependencies` list. The numerical regression report checks the central coefficients, independent block/folding implementations, all three current intervals, known numerical/nonlinear tests, LP residuals, spectrum counts, and the full-run provenance. Passing this report means numerical regression succeeded; it does not certify the physical interval.

The stochastic-looking nonlinear tests are deterministic finite tests with seed 6087. They are not Monte Carlo confidence calculations.

### Smaller profiles

Use an alternative output folder for exploratory runs so the main full-run receipt is preserved:

```sh
python code/workflow/reproduce.py smoke --output outputs/smoke_run
python code/workflow/reproduce.py central --from-scratch --output outputs/central_run
python code/workflow/reproduce.py refinement --output outputs/refinement_cached
python code/workflow/reproduce.py refinement --from-scratch --output outputs/refinement_clean
python code/workflow/reproduce.py validation --from-scratch --output outputs/validation_clean
```

| Profile | Requested computation | Dependency behavior |
|---|---|---|
| `smoke` | Central ratio, blocks, baseline, T-prime, cutoffs and two-point crossing diagnostics; omits larger numerical sweeps | No archived result is needed for the calculation |
| `central` | Full diagnostics, family errors/crossing, global low-input propagation and retained-input box | All required calculations run |
| `legacy` | Historical tail scenarios/summary, exact-GFF tests and alternative-domain tests | Uses archived sensitivity dependencies unless `--from-scratch` is set |
| `refinement` | Current nominal, doubled-padding and weaker-gap scenarios | Uses archived basis/sensitivity dependencies unless `--from-scratch` is set |
| `validation` | Nonlinear, radial, numerical-tail, LP and cap-tail checks | Uses archived bases/final LP dependencies unless `--from-scratch` is set |
| `full --from-scratch` | All of the above, with basis levels 32, 40 and 48 | No archived numerical inputs are loaded |

The runner does not substitute a saved final result for a requested computation. In cached mode it stages numerical **dependencies**, records them, and recomputes the requested stage. Default output collection copies newly created/changed numerical files; seeded unchanged references remain in the reference directory. The full `verify.py results` suite expects a complete full run, not a smoke profile.

`--keep-workspace` retains the working directories for debugging; it is not required for reproduction and should not be used when creating a clean release. The numerical scripts are research modules that write beside themselves. Prefer the workflow driver over calling them inside `code/` directly: it stages their dependencies correctly and avoids mixing output files with source.


## Review diagnostics and sensitivity reproduction

Run these from the package root after installation:

```sh
python code/workflow/review_diagnostics.py --results outputs/reproduced
python code/workflow/review_stress.py gaps --iterations 10
python code/workflow/review_stress.py boxes --iterations 10
python code/workflow/make_review_tables.py --update-note
python code/workflow/check_revision_guards.py
```

`review_diagnostics.py` audits the *fixed* nominal saved LP, records violating rows, computes its minimax displacement, and checks ratio/real-axis signs. It writes `outputs/review_validation/fixed_lp_diagnostics.json`.

`review_stress.py gaps` reuses the explicitly identified reference level-40 basis and rebuilds the gap-dependent LP/tail calculation. It includes nominal, weaker-gap and matched ten-update padding runs. `review_stress.py boxes` rescales all quoted input errors, regenerates the affected precision sensitivities and denominator box, rebuilds the level-40 basis, then reruns the envelope with the **fixed physical** epsilon-prime window. It does not merely rescale a saved matrix. The integrated-objective allowance is held at 5e-5; wider-box outputs are sensitivity diagnostics, not uniformly validated alternative bounds. Default box multipliers are 0.5, 0.6, 0.7, 0.8, 0.9, 1.5, 2 and 3; the nominal case is supplied by the gap scan. A custom `--multipliers` list is accepted.

Each case has its own directory, raw JSON/NPZ outputs and execution receipt; infeasibility is explicitly recorded. These files are not silently substituted for a newly requested calculation. `make_review_tables.py` generates the three CSV and LaTeX sensitivity tables from the completed runs. With `--update-note`, it copies those tables into named markers in the standalone source; no external table file is needed to compile the note.

`check_revision_guards.py` tests the ratio guards under Python `-O`, runs an isolated smoke profile, verifies that the incomplete profile fails cleanly rather than crashing, and checks that the principal receipt/report are unchanged. Its report is `outputs/verification/revision_guard_checks.json`.

The main reproduction should have its own destination:

```sh
python code/workflow/reproduce.py refinement --from-scratch --output outputs/refinement_clean
python code/workflow/reproduce.py full --from-scratch --output outputs/reproduced
python code/workflow/verify.py results --results outputs/reproduced
```

The full verifier expects all 20 stages. A refinement-only or smoke run is deliberately incomplete for that suite. Its report now lives in `<results>/verification/regression_checks.json`, or the explicit `--report` destination. Non-full profiles default to `outputs/<profile>_run`; they no longer default to the principal `outputs/reproduced` directory.

`verify.py integrity` detects both incorrect listed hashes and unexpected delivered files, including `.DS_Store`; it ignores local virtual-environment and Python-bytecode directories. Use `--allow-extra` only to permit intentionally added files after extraction, not to excuse changed listed hashes. Delivery hashes describe the shipped bytes, so run integrity verification before regenerating receipts, assets or PDFs, or use a fresh extracted copy. Scientific regression checks use tolerances and remain the appropriate comparison after a rerun.

## Script-to-output map

In the following table, precision outputs live under `outputs/reproduced/precision/` and refinement outputs under `outputs/reproduced/refinement/`. The driver preserves these names.

| Script/module | Arguments used | Main outputs or role |
|---|---|---|
| `c1_precision/blocks.py` | Imported | Casimir radial and small-z recurrences; tensor normalization; alternative bookkeeping for the same folded integral |
| `c1_precision/spectrum.py` | Imported | Loads `published_spectrum.json`, replaces leading inputs coherently, derives stress couplings, converts f to historical tensor convention |
| `c1_precision/kernels.py` | Imported | Linear integrated family kernels, constants, and three direct/crossed correlators |
| `c1_precision/run_diagnostics.py` | None; `--quick` for smoke | `diagnostics_results.json`: retained value, original selection, T-prime contribution, cutoff and quadrature checks, shared-domain functional consistency (legacy JSON key: independent_folding), analytic block tests |
| `c1_precision/errors_and_crossing.py` | None | `expanded_spectrum.json`, `analysis_results.json`: all per-family contributions/sensitivities and crossing grid |
| `c1_precision/complete_input_errors.py` | `global`, then `box` | `global_input_results.json`, `input_box_results.json` |
| `c1_precision/compute_tail_scenarios.py` | None | `tail_estimates.json`, `tail_gap8_results.json`: historical remainder scenarios |
| `c1_precision/finalize_results.py` | None | Historical `SUMMARY_RESULTS.json`; **not the current headline interval** |
| `c1_precision/tail_probe.py`, `tail_integral_probe.py` | Imported | Legacy pointwise/ integrated conditional tail machinery |
| `c1_precision/tail_validation.py` | None | `tail_validation_results.json`: exact-GFF positivity/prefactor and envelope quadrature checks |
| `c1_precision/alternative_domain.py` | None | `cap_results.json`: alternative disk/cap integral sweep |
| `c1_precision/validate_cap.py` | None | `cap_validation.json`: exact-GFF and boundary-derivative checks |
| `c1_refinement/build_crossing.py` | `32`, `40`, `48` | `basis_L*.json` and `.npz`: parameter metadata, residuals, Jacobians, paddings, integrated objective |
| `c1_refinement/crossing_envelope.py` | Imported | Repeated crossing/input LP constraints, radial reference bounds and missing-tail integral |
| `c1_refinement/angular_tail.py` | Imported | Sign-aware odd angular/exponent optimization with high-spin and exponent remainders |
| `c1_refinement/final_run.py` | `8 7 1 10`; `8 7 2 8`; `6 6 1 8` | For each scenario: `final_*.json`, `final_*_lp.npz`, `final_*_angular.json`, `final_*_summary.json` |
| `c1_refinement/check_nonlinear.py` | None | `nonlinear_crossing_validation.json`: 34 exact nonlinear retained-input evaluations |
| `c1_refinement/validate_refinement.py` | `objective`; `radial` | `validation_objective.json`, `validation_radial.json` |
| `c1_refinement/run_numerical_checks.py` | None | `final_numerical_checks.json`, `lp_optimality_checks.json` |
| `c1_refinement/cap_tail_check.py` | None | `alternative_domain_tail_checks.json`: five alternate domains with tail-only sensitivities |
| `workflow/reproduce.py` | Profile plus options | Isolated execution and `run_receipt.json` |
| `workflow/verify.py` | `results`; `integrity` | 23-check full-run regression report next to --results; or checks manifest hashes and unlisted delivery files |
| `workflow/make_assets.py` | Optional `--results PATH` | CSV tables, `current_summary.json`, four PDF/PNG figures, `assets_manifest.json` |
| `workflow/build_pdf.py` | None | `note/ising3d_C1_note.pdf` and `outputs/verification/pdf_build.json` |

The final scenario's iteration history contains its symmetric-tail envelope during refinement. Its `_summary.json` contains the **final sign-aware** ratio interval. Those arrays describe different stages of the calculation. The reference `weaker_gap_6_6_results.json` was supplied from an earlier resumed run; `final_run.py 6 6 1 8` regenerates the same eight total updates from scratch and writes a complete fresh history.

## Inputs and numerical conventions

`published_spectrum.json` is the raw transcribed selection. Each row specifies the internal sector, trajectory label, spin, dimension, quoted errors, f-convention couplings and source table. Even rows include two couplings, `f` and `h`; odd rows use `f` for the sigma-epsilon coefficient. Names retain the historical rounded dimension for identification: calculations use the numeric `Delta` field, not the dimension embedded in the name.

`low_inputs.json` supplies `S`, `E`, `sse`, `eee`, and `ct`, including quoted errors. `retained_spectrum.json` is the explicit snapshot produced after the common replacements. `run_diagnostics.py` verifies exact agreement between that snapshot and the loader. The zero independent errors stored in the stress row do **not** mean exact stress couplings: their uncertainty is propagated through shared `S`, `E`, and `ct`.

The tensor conversion used here is `lambda = 2**(ell/2) * f` (the KPS/Reehorst tensor convention); the f-product block weight is `ell!/(1/2)_ell`. Mixed-product signs must be preserved. Original baseline selection values are in `baseline_selected_spectrum.json`; its stress row is replaced by the same Ward inputs for baseline comparisons.

**Correct folded domain:** `|z| < 1` and `Re(z) < 1/2`, equivalently `|z| < |1-z|`. The earlier prose statement `|1-z| > 1` was incorrect. The code already used the correct limits, so this documentation correction does not change numerical values. The note derives the radial/angular limits and the analytic continuation at the origin.

The current gap/padding hypotheses are documented in `assumptions.json`, but it is **metadata, not a complete executable configuration file**. The main reference ratio and denominator are loaded from current `analysis_results.json` and `input_box_results.json`. Chosen allowances and the physical epsilon-prime window live in `c1_refinement/runtime_config.py`; the nonlinear padding prescription remains in `build_crossing.py`. Historical-only diagnostic scripts retain their archival conventions and are not configurations for a new physical input model. Changing physics inputs requires updating the retained snapshot, reference constants, objective, coherent variations, crossing bases and scenario assumptions, then rebuilding the entire calculation. Merely editing one JSON field does not automatically produce a validated new physical interval. Changes to inputs should also trigger a review of the frozen numerical tables embedded in the LaTeX note.

## Tables and figures

`make_assets.py` reads **reproduced** results, not silently substituted archived final answers. It generates:

- `current_summary.json`, `central_progress.csv`, `family_contributions.csv`, `cutoff_convergence.csv`, and `crossing_comparison.csv`;
- `retained_spectrum.csv`, `low_inputs.csv`, `known_input_sensitivities.csv`, and `numerical_stability.csv`;
- `conditional_intervals.csv`, `error_budget.csv`, and `alternative_domain_sensitivity.csv`;
- `cutoff_convergence`, `conditional_intervals`, `known_input_sensitivity`, and `alternative_domain_sensitivity`, each as a vector PDF and a PNG.

The input hashes for these assets are recorded in `assets_manifest.json`. Cutoff convergence is not a completeness test. Input sensitivity is not a physical standard deviation. Alternative-domain error bars are tail-only sensitivity scales, not independent measurements or complete physical confidence intervals. The titles of the archived figures make these distinctions explicit; the trimmed note uses only the final-method tables, not the historical diagnostic figures.

## Compiling the source by itself

The source is genuinely single-file. As a direct test, copy only `note/ising3d_C1_note.tex` into an otherwise empty directory and run:

```sh
pdflatex -interaction=nonstopmode -halt-on-error ising3d_C1_note.tex
pdflatex -interaction=nonstopmode -halt-on-error ising3d_C1_note.tex
pdflatex -interaction=nonstopmode -halt-on-error ising3d_C1_note.tex
```

Three passes resolve the table of contents and cross-references. `build_pdf.py` performs precisely this source-only test in a temporary folder, rejects compilation errors, unresolved-reference warnings and overfull boxes, copies the final PDF into `note/`, records the source/PDF hashes, and discards all auxiliary files. The document contains its own tables and bibliography. The previously generated matplotlib plots remain reusable archive assets, but no figure is a compilation dependency of the trimmed note.

## Integrity, verification, and provenance

Immediately after extraction, verify the shipped snapshot with:

```sh
python code/workflow/verify.py integrity
```

The manifest covers every delivered file except itself. After rerunning calculations or rebuilding the PDF, checksums of generated files may change; that is expected. Use the numerical regression check to assess a recomputation rather than demanding byte identity. `verify.py results` uses a central-value tolerance of `5e-10` and interval-endpoint tolerance of `2e-8`, and validates additional structural/numerical conditions.

`data/provenance/package_sources.json` identifies the source archives and the limited changes in this consolidation. The first-order block bodies were extracted without numerical changes; the unused higher-order machinery is not part of this package. The main precision/refinement scientific algorithms are retained, with a JSON input loader and workflow/validation/reporting wrappers added. `source_registry.json` records the primary bibliography and its role. The note contains citations and all information needed to reproduce the reported snapshot; full external papers are not redistributed.

The delivered verification folder contains a successful full from-scratch execution receipt, 15 passing scientific regression checks, a standalone compilation record, environment and assets records, a visual PDF review, and a relocation test. These certify what was actually run or inspected—not the completeness of the Ising spectrum or the physical coverage of the conditional interval.

## Open research issues

The principal unresolved issues are low-dimensional omitted spectral weight, validity and joint dependence of the retained input ranges, and uniform rather than sampled certification of nonlinear and numerical remainder bounds. More quadrature points will not substantially reduce those uncertainties. These are open issues beyond the implemented method. The trimmed note retains their consequences for the conditional status of its result, without the earlier prospective research discussion.
