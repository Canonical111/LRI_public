# LRI C2: complete research note and reproducibility package

**Cluster-readiness revision.** The physical calculation and preserved data are
unchanged. This revision adds resource-configurable cluster launching, shared-grid
preparation, arbitrary-cutoff record indexing, and a detailed continuation plan.
It does **not** claim any larger production runs or additional digits. Start with
[the cluster guide](cluster/README.md) for cluster use; the existing `analyze`
workflow below reproduces the preserved results, not arbitrary new cluster data.
CPU, memory, scheduler and wall-time settings are left for the user to configure.

**Expanse and symmetry revision (12-13 October 2026).** A production launch
layer for SDSC Expanse and Perimeter's symmetry cluster: site-independent code
in `cluster/sitekit/` (pinned environments, checksummed tarball staging, grid
and row jobs on node-local scratch, checked and throttled submission,
collection, cross-site merging), site profiles and wrappers in
`cluster/expanse/` and `cluster/symmetry/`, and the re-prioritised site-neutral
plan `cluster/production_plan.json`. The leading-tail auxiliary cutoff became
configurable with the historical default 2048. The science is unchanged: with
defaults, the old and new code give identical outputs (`results/expanse/`).
Only smoke tests (both sites) and an N=512 pilot (Expanse) were run; no new C2
is claimed. See [which cluster, launch, merge](cluster/sitekit/README.md),
[Expanse](cluster/expanse/README.md) and [symmetry](cluster/symmetry/README.md).

**Arbitrary-N continuum analysis (13 October 2026).** `code/continuum/`
implements the approved analysis plan (fractional spectral windows, aligned
auxiliary cutoffs, prefix/cross-N/extraction/roundoff diagnostics, regulator
fits with pre-declared admissibility, joint fit and outcome table) on the
archived and production records plus new auxiliary and extraction-check runs:
`python scripts/run.py continuum -- run --records <merged index> --diagnostic-records <merged indexes> --aux-dir <dir> --output <dir>`.
Result and caveats: [`results/continuum_2026-10/REPORT.md`](results/continuum_2026-10/REPORT.md):
C2 = -4.06705 +- 0.00236 (outcome branch 4, extraction coverage complete; plan rev 7, with the measured
extraction split replacing the superseded rev-4 worst-case rule, whose +-2.2 is archived in
`results/continuum_2026-10/evidence/rev4/`). User-approved deviation D1: the last nine extraction checks and
both N=1024 grids they need ran on symmetry because Expanse Lustre failed (see `provenance/REVISION_NOTES.md`).
Each run is published as an immutable generation under `results/continuum_2026-10/generations/`; the file
`CURRENT` names the current one, the top-level files are copies of it, and
`python code/continuum/continuum_driver.py check --output results/continuum_2026-10` verifies them.

This package records the project through 12 October 2026. Start with
[`note/lri_c2_progress.pdf`](note/lri_c2_progress.pdf). Its LaTeX source is a
**single, independently compilable file** with an embedded bibliography and no
external figures, tables, or source-file dependencies.

The problem is the thermal curvature of the **isotropic two-dimensional**
long-range Ising model, in the convention

```text
delta = (7/4 - s)/2
Delta_epsilon = 1 + C2 * delta**2 + O(delta**3).
```

The package distinguishes two different achievements:

* An independent integer-interval evaluation certifies the proposed closed
  expression to 51 decimal places. This is a statement about that expression,
  not a proof of its identification with the physical coefficient.
* A direct fourth-order Ising-CFT × generalized-free-field Hamiltonian
  calculation gives approximately **C2 = -4.07**. It computes perturbative
  coefficients at physical `delta = 0`, together with an analytic lower-order
  derivative. It does **not** fit physical dimensions at nonzero `delta`.
  Artificial cutoff and regulator extrapolations remain necessary. The
  numerical result is not a rigorous enclosure, and the third decimal place
  is not established.

The note gives the physical setup, normalization, exact second-order
continuation, fourth-order resolvents, matrix elements, six chiral spectral
generating functions, all energy denominators, local counterterm integrals,
leading spectral tails, extrapolation choices, validation results, earlier
unsuccessful prescriptions, and unresolved issues.

## 1. Directory structure

```text
LRI_C2_complete/
  README.md                         this guide
  MANIFEST.sha256                   integrity manifest for every shipped file
  requirements.txt                  broad minimum dependency versions
  requirements-tested.txt           exact versions used for this package's tests
  note/
    lri_c2_progress.tex              standalone consolidated note
    lri_c2_progress.pdf              compiled note
  scripts/
    run.py                          isolated staging and calculation entry point
    build_note.py                   build source alone; keep only PDF and receipt
    verify_manifest.py              SHA-256 check (standard library only)
    check_results.py                reporting regression check against records
  cluster/                          resource-configurable launch/cache/index tools,
                                    optional Slurm adapter, proposed run plans, tests
    sitekit/                        site-independent jobs, driver, collection, merging, tests
    expanse/                        SDSC Expanse profile, environment, wrappers, tests
    symmetry/                       Perimeter symmetry profile, environment, wrappers, tests
    production_plan.json            site-neutral PILOT/P1/P2 plan
  code/
    hamiltonian/                    current spectral solver and analysis modules
    legacy_hamiltonian/             initial finite-basis diagnostic calculation
    formula_checks/
      numerical/                    exact integer-interval formula certificate
      elliptic/                     independent period/plane/symbolic checks
      physical/                     local source, branch-contact, OPE checks
    original_study/                 supplied study's eight-stage pipeline
  data/
    hamiltonian/
      raw/                          completed, pairing-resolved spectral sequences
      auxiliary/                    independently derived leading-tail inputs
      reference/                    historical model selections and final record
      diagnostics/                  prior validation, convergence and grid records
      run_plan.json                 all production configurations; no target C2
    legacy_hamiltonian/             historical finite-cutoff diagnostic records
    formula_checks/                 earlier independent-review records
    original_study/                 exact Ising inputs, calculation configuration,
                                    and the original pipeline's reference inputs
  reference/
    original_study/                 supplied manuscript source/PDF and metadata
  results/                          selected calculations rerun during consolidation
    hamiltonian/                    fully regenerated saved-data analysis
    hamiltonian_recorded/           reproduction of the historical model selection
    validation/                    freshly rerun finite implementation checks
    second_order/                   freshly rerun slope and magnetic checks
    certificate/                    freshly rerun exact arithmetic certificate
    formula_checks/                 freshly rerun elliptic and local checks
    demo/                           fresh small-box spectral run, not a C2 estimate
    original_study/                 freshly rerun original pipeline
    reporting_regression.json       comparison of the two analysis selections
    document_build.json             standalone LaTeX compilation report
    revision/                       freshly repeated validation, saved-data analysis,
                                    certificate, wrapper tests and small integration run
    expanse/                        Expanse revision: regression, tests, smoke, probe, pilot
    symmetry/                       symmetry: tests, smoke, probes, pilot, cross-site merges
    fix_round1/                     first review round: tests, regressions, Expanse checks
    fix_round2/                     second review round: tests, traversal check, cross-site smoke
  provenance/
    SOURCE_INVENTORY.json           source archives, members, and hashes
    PACKAGING_NOTES.md              changes, rerun scope, exclusions, caveats
    packaging_environment.json      actual interpreter and library versions
    original_study_*                original source map and metadata
    REVISION_NOTES.md               new changes, tests, and unfinished analysis work
    REVISION_SOURCE.json            prior-bundle hash and unchanged science/data audit
```

`data/` is preserved input, including prior computed numerical sequences that
serve as input to the continuum analysis. `results/` contains verification
outputs made during this consolidation. New commands write to `outputs/` by
default; they do not overwrite the preserved inputs or the shipped results.

Raw spectral sequences and their pairing decomposition are retained because
reproducing the extrapolations requires them. The large deterministic coefficient
arrays are **not** input data: they can be regenerated from the analytic blocks
and are deliberately excluded. No virtual environment, bytecode, LaTeX auxiliary
files, FFT arrays, OS metadata, external research-paper PDFs, or font files are
included.

## 2. Dependencies and installation

The scientific package and the new local wrapper tests were tested on Linux with **Python 3.13.5** and the versions
in `requirements-tested.txt`:

```text
numpy       2.3.5
scipy       1.17.0
sympy       1.14.0
mpmath      1.3.0
matplotlib  3.10.8
```

The code uses Python 3.10+ syntax. Earlier supported Python/library combinations
may work but are not established by this snapshot. `requirements.txt` records
minimum API requirements; it is not a claim that every combination of versions
has been tested. For closest numerical reproduction use the tested versions:

```bash
cd LRI_C2_complete
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-tested.txt
python scripts/verify_manifest.py
```

Alternatively, on a compatible environment:

```bash
python -m pip install -r requirements.txt
```

The integer-interval certificate itself uses **only Python's standard library**.
Do not run it under `python -O`, which removes the assertions used to verify the
polynomial sign certificates.

No network access is needed to calculate results after dependencies are
installed. Set `OPENBLAS_NUM_THREADS=1` to avoid unwanted BLAS oversubscription;
the runner does this for child processes. Large FFT calculations also accept
`LRI_FFT_WORKERS` or the solver's `--workers` option. Multiple coefficient-grid
workers use `fork` where available; other systems use the serial generator.

### LaTeX

A TeX distribution with pdfLaTeX and the following standard packages suffices:
`fontenc`, `inputenc`, `lmodern`, `microtype`, `geometry`, `amsmath`, `amssymb`,
`mathtools`, `bm`, `mathrsfs`, `booktabs`, `longtable`, `array`, `enumitem`,
`xcolor`, `xurl`, `hyperref`, `fancyhdr`, `listings`, and `needspace`.
The bibliography is embedded: neither BibTeX nor a `.bib` file is required.

## 3. Recommended quick reproduction

Run these commands **from the package root**:

```bash
# Finite matrix elements, block sums, convolution, and counterterm tests.
python scripts/run.py validate

# Recompute all available tail fits and continuum models from saved raw sums.
python scripts/run.py analyze

# Reproduce the exact model availability used in the earlier numerical report.
python scripts/run.py analyze-recorded

# Rigorous evaluation of the proposed closed formula, not a physical proof.
python scripts/run.py certify

# Exact second-order formula, slope, and magnetic normalization checks.
python scripts/run.py second-order

# A fresh small spectral computation; deliberately not a continuum estimate.
python scripts/run.py demo

# Compile the note with only its .tex file in a temporary directory.
python scripts/build_note.py
```

The first six commands export JSON/CSV and `run_receipt.json` under
`outputs/<command>/`. They stage the existing flat-layout scientific code into
an isolated working directory and remove its temporary arrays after exporting
results. The receipt names the scripts actually run and hashes their output
files. A successful saved-data analysis is **not** evidence that all large
coefficient grids were regenerated.

Expected approximate continuum estimates from `analyze` are:

| Regulator order | h0 | Converted C2 |
|---:|---:|---:|
| 1 | -3.413430 | -4.066939 |
| 2 | -3.415138 | -4.068000 |
| 3 | -3.420370 | -4.071252 |

Extra digits label particular fits, not physical precision. The justified
project conclusion remains approximately **-4.07**.

### Why `analyze` and `analyze-recorded` differ slightly

The earlier saved transseries-fit file contained 11 of 12 `N=256` cases. The
missing order-3, lambda-0.35 entry therefore used the already implemented
raw-power-fit fallback. `analyze-recorded` preserves that model availability;
its order-3 result is `-4.071269861562929` and reproduces the original record.

`analyze` regenerates **all 12** tail fits, applying the fixed-leading-tail
method to the previously missing case as well. It gives
`-4.071252205780145`. The difference, about `1.77e-5`, is far below the justified
accuracy. Both selections and their complete model sensitivities are retained.
This difference is not a change of raw state sums or a fit to the proposed C2.
The lambda-0.5 tail is rebuilt with its independently fixed leading coefficient,
as in the earlier analysis.

To check the shipped verification outputs against the preserved records:

```bash
python scripts/check_results.py
```

For that same regression check on newly run outputs, use the names expected by
the report checker:

```bash
python scripts/run.py validate --output outputs/check/validation
python scripts/run.py analyze --output outputs/check/hamiltonian
python scripts/run.py analyze-recorded --output outputs/check/hamiltonian_recorded
python scripts/run.py certify --output outputs/check/certificate
python scripts/check_results.py --results outputs/check
```

## 4. Fresh Hamiltonian calculation, not just analysis of saved data

### Small example

The default `demo` computes a fresh `24^3` spectral box with mixed cutoff 64,
collapsed cutoff 4000, order 1, and lambda 0.25. To change the example:

```bash
python scripts/run.py demo --output outputs/demo64 -- \
  --cutoff 64 --order 1 --lam 0.25 \
  --mixed-cutoff 128 --collapsed-cutoff 10000
```

These small examples test the solver pipeline, not the continuum extrapolation.
The output deliberately says `physical_C2_claimed: false`.

### One production family

Use a **persistent scratch directory** to avoid regenerating the same Ising
block arrays for every regulator value:

```bash
OPENBLAS_NUM_THREADS=1 LRI_FFT_WORKERS=2 \
python scripts/run.py hamiltonian --work-dir work/main \
  --output outputs/production_order1 -- \
  --cutoff 256 --oversample 5 --radius-cost 4 \
  --order 1 --lam 0.1 0.125 0.15 0.2 0.25 \
  --mixed-cutoff 4096 --collapsed-cutoff 200000
```

Arguments after `--` are passed to `code/hamiltonian/reproduce.py`. A coefficient
cube is cached by its shape and Cauchy-grid parameters. A cache hit requires
**both the array and its JSON metadata**. The package does not pretend that
shipped metadata constitutes an existing numerical array. Paths supplied using
`--coefficients` should be absolute because execution occurs in the stage.

### Complete predefined production run

```bash
OPENBLAS_NUM_THREADS=1 \
python scripts/run.py full-hamiltonian --work-dir work/full \
  --output outputs/full_hamiltonian
```

This reads `data/hamiltonian/run_plan.json`, recomputes all required spectral
sequences and local constants, generates the auxiliary leading-tail coefficients,
and runs the complete saved-data-style analysis on the **new** records. No saved
physical C2 or reference continuum fit is needed.

The plan includes `N=256` at all twelve primary regulator points; `N=384` for
order 1 at lambda 0.075 and 0.1, order 2 at 0.125, and order 3 at 0.2; and the
additional `N=128`, order-3 lambda-0.5 point. Mixed sums run to 4096; collapsed
sums use 200,000 or 800,000 terms as recorded in the plan. `N` is a coefficient
box size, **not a Hilbert-space matrix dimension**. Level degeneracies have
already been summed by the chiral generating functions.

**Resources:** this is a substantial numerical job, not a quick test. The
`(6,385,385,385)` real array alone occupies about 2.74 GB, and its generator uses
an additional approximately 11 GB temporary memory-mapped array. FFT work
arrays, convolutions, multiple processes, and cached smaller grids increase RAM
and disk needs further. Reserve ample scratch space (tens of GB), check the
machine's memory limit, and reduce parallel workers when necessary. Wall time
is strongly hardware-dependent; no universal timing guarantee is given. The
full large-grid plan was **not rerun while assembling this package**. Its
components and the clean small-box path were tested, and prior production
records are preserved.

Interrupting a run can leave arrays in `work/`. Those are scratch files; they
may be removed, but deleting a valid cache forces regeneration. Production code
was written for research use; inspect the stored model residuals and cutoff
sensitivity rather than relying on a single successful exit code.

## 5. Other project stages

```bash
# Independent period, complex-plane, symbolic, and local-contact checks.
python scripts/run.py formula-checks

# The original supplied study's eight-stage computational pipeline.
python scripts/run.py original-study

# Earlier finite-basis checks, retained as diagnostics rather than a C2 result.
python scripts/run.py legacy-checks
```

The formula-check workflow includes elliptic quadrature orders 96, 192, and 384
and the local physical checks. The original-study workflow stages its expected
file layout, exact inputs, source map, and original manuscript before running its
own pipeline. Its regenerated outputs are separate from the independent
Hamiltonian results.

The `code/legacy_hamiltonian/` files and `data/legacy_hamiltonian/` records
preserve the initially unsuccessful cutoff extraction. Their trial coefficients
must **not** be substituted for the final renormalized `h` or `C2`. Some current
helper modules also retain old exploratory `__main__` entry points or fields;
the supported end-to-end commands are those in `scripts/run.py`.

## 6. Script-to-output map

Paths in this table are relative to the staged scientific-code directory unless
an `outputs/` prefix is shown. The runner copies final reports into the selected
output directory.

| Command or scientific module | Inputs | Principal output / role |
|---|---|---|
| `run.py validate` / `validate.py` | Analytic CFT formulas; small generated states/blocks | `validation_results.json` and separate finite-shell/convolution checks |
| `run.py analyze` | Raw sequences and leading-tail inputs | `FINAL_NUMERICAL_RESULTS.json`, all model fits, coupling-scheme check, CSV tables |
| `run.py analyze-recorded` | Same raw records and historical model availability | Historical representative estimates and CSV tables |
| `reproduce.py` | Numerical cutoffs, regulator parameters; analytic blocks | `recomputed_k*_a*_N*.json`, plus `_analysis.json` when mixed cutoff is sufficient |
| `fast_coefficients.py`, `parallel_coefficients.py` | Analytic six-block functions and grid parameters | Regenerable `.npy` arrays and grid metadata; scratch, not bundled |
| `ising_basis.py`, `spectral.py`, `block_check.py` | Exact Ising form factors and GFF modes | Explicit-basis and complex-block validation machinery |
| `lowmemory.py` | Ising coefficient cube and regulated oscillator kernel | Pairing-resolved fourth-order cube partial sums |
| `resummed_improved.py`, `second_order.py`, `slope_check.py` | Regulator kernels / analytic second-order formula | Collapsed sums, normalization term, direct slope checks |
| `mixed_sequence.py` | Two-variable kernels and finite polynomials | All mixed thermal partial sums and diagnostic fits |
| `improved_regulator.py` | Local OPE and compact kernel integrals | Planar `ct`, `kappa`, and cylinder thermal correction |
| `exact_leading_tail.py` | Analytic block face limits and collapsed norms | Leading `N^(-7/4)` tail and component sums |
| `tail_transseries_fit.py`, `analyze_extended.py` | Raw cube sequences, fixed leading coefficient | `tail_transseries_fits.json`, `extended_analysis.json` |
| `final_analysis.py` | Finite-regulator estimates, model choices, a1 and b0 | Full regulator-fit/model-sensitivity record, not merely a target decimal |
| `bundle_helpers.py` | Computed records and analytic constants | Large-lambda fixed-tail refresh, improved magnetic check, coupling sensitivity, CSV tables |
| `certify_c2.py` | Rational hypergeometric parameters and analytic beta representation | `certified_result.json`: exact enclosures and proof certificates |
| `continued_period_check.py` | Continued-period integrands; quadrature order | `continued_period_check_*.json` |
| `complex_moment*_check.py`, `identity_audit.py` | Independent convergent moments and symbolic formulas | Plane-pairing and exact identity checks |
| `local_physics_checks.py` | Gaussian/local branch kernels and charge configurations | `local_physics_results.json` |
| `run.py original-study` | Original exact inputs and settings | Original `summary.json`, raw audits, tables, and figures |
| `build_note.py` | Only `note/lri_c2_progress.tex` | Compiled PDF and `results/document_build.json` |

### Data schema and interpretation

A primary fixed-regulator record has these fields:

* `order`, `lam`, `N`: regulator order, positive artificial regulator, coefficient
  cube cutoff. The physical parameter is fixed at the endpoint.
* `raw.parts`, `raw.Xchain`: pairing-resolved and total fourth-order partial sums
  at every cube cutoff, not only the largest cube.
* `two_point.states`, `Xdisc`, `Dmixed`, `X2`: lower-order energies and norms,
  normalization subtraction, mixed Ising-Hamiltonian term, finite-regulator
  second-order observable. The old `t2` and `k2` keys are **trial diagnostics**;
  production assembly does not use them as counterterms.
* `mixed.parts`, `mixed.Xmixed`, `mixed.fits`: thermal-insertion square-cutoff
  sequences and their extrapolation records.
* `planar.ct`, `planar.kappa`, `curvature.thermal_lambda_coefficient`: independently
  computed local matching coefficients used in the final assembly.

`large_lambda_k3_a0.5.json` wraps its raw record under `data` and also retains
its derived `analysis` and `tail_fits`. The analysis helper rebuilds those fits
using the highest-cutoff independently derived leading tail, not a free leading
coefficient.

The leading-tail records include the two-index cutoff, outer/adjacent/nested
pieces, and the sign convention

```text
X_chain(infinity) - X_chain(N) = A_face * N**(-7/4) + subleading.
```

The final result record retains every tested regulator model, weighting,
window, condition number, residual, and propagated spectral half-spread. A
half-spread is a model diagnostic, **not** a statistical standard deviation or
a rigorous error bound. A four-parameter fit through four points has zero
residual by construction and is not, on that basis, a precision certificate.

## 7. Building the standalone note

The preferred build uses an isolated temporary directory and copies **only the
single `.tex` source** into it:

```bash
python scripts/build_note.py
```

It runs pdfLaTeX three times, writes `note/lri_c2_progress.pdf`, and records
undefined-reference/citation and overfull-box checks in
`results/document_build.json`. Temporary `.aux`, `.toc`, `.log`, and `.out`
files are removed with the build directory.

The source also compiles without any of this package's Python code. Copy it
into an otherwise empty directory and run:

```bash
pdflatex -interaction=nonstopmode -halt-on-error lri_c2_progress.tex
pdflatex -interaction=nonstopmode -halt-on-error lri_c2_progress.tex
pdflatex -interaction=nonstopmode -halt-on-error lri_c2_progress.tex
```

The separately retained original-study source is historical input; the
standalone guarantee here concerns **`note/lri_c2_progress.tex`**.

## 8. Validation scope, provenance, and scientific limits

`provenance/PACKAGING_NOTES.md` states exactly which workflows were rerun for
this consolidation. `results/` contains their machine-readable outputs and
receipts. The large prior production sequences remain labeled as retained data,
not as new calculations performed during document preparation.

`provenance/SOURCE_INVENTORY.json` records the source-package lineages and the
original member hashes. New packaging code is separate from the scientific
solver modules. The only correction to a retained production solver is the
cache-presence check described above. The new analysis helper also makes the
large-lambda fixed-leading-tail choice explicit. The note documents the small
historical-versus-complete-analysis difference.

`MANIFEST.sha256` checks every shipped file except itself. Run the verifier
**before editing or rebuilding**; changing a file legitimately changes its
hash. Newly generated files under `outputs/` are ignored by the verifier.
Integrity checks establish file consistency, not the correctness of a research
claim or trust in an unknown distribution.

No external research articles are redistributed. Bibliographic references are
embedded in the note. Authorship: OpenAI GPT-6 Astra (via ChatGPT) wrote both
supplied studies, the closed-form final-method study and the cylinder-Hamiltonian
study (LRI_C2_complete.zip), as stated by the project author on 14 October 2026
(see `provenance/original_study_source_map.json`). The supplied files retain their
existing status; this bundle does not assert new authorship or relicense third-party
material. The unresolved continuum/global matching and numerical remainder
issues are discussed explicitly in the note's open-issues section.


## 9. Cluster continuation and configurable resources

The standalone note now includes the cluster-scaling discussion: array-size
formulas, a proposed N=512/768/1024 progression, cache reuse, independent-job
parallelism, error budgeting, and the historical analysis limitations.
The complete instructions are in [`cluster/README.md`](cluster/README.md).

```bash
# Inspect proposed tasks and exact known array sizes without starting a large run.
python cluster/run_task.py list
python cluster/resource_estimate.py --cutoff 384 512 768 1024 --oversample 4
python cluster/run_task.py run --task-index 0 \
  --work-root work/cluster --output-root outputs/cluster --dry-run

# Test only the cluster support code.
python cluster/test_cluster.py --output outputs/cluster_tests.json
```

`cluster/extension_plan.json` is **prospective configuration, not measured input
data**. The optional Slurm adapter contains no CPU/memory/time/account/partition
requests; configure them at submission. The new launcher never runs the frozen
continuum analysis on extension records. `cluster/collect_records.py` preserves
all numerical variants and reports overlaps without claiming improved C2.

### SDSC Expanse and symmetry

The shared layer, the side-by-side "which cluster" table and the merge procedure
are in [`cluster/sitekit/README.md`](cluster/sitekit/README.md); site details in
[`cluster/expanse/README.md`](cluster/expanse/README.md) and
[`cluster/symmetry/README.md`](cluster/symmetry/README.md). On Expanse, in short
(symmetry is the same with `symmetry` in place of `expanse`, after
`export PATH=/cm/shared/apps/slurm/current/bin:$PATH`):

```bash
# On the Mac: commit, then build ONE tarball (+ sha256) and upload it.
bash cluster/expanse/make_tarball.sh --upload expanse
# On the Expanse login node, from the uploaded code copy:
cd ~/lri_c2/pkgs/lri_c2_<commit12>
bash cluster/expanse/setup_env.sh                      # once: CPython 3.13.5 + tested versions
PY=$HOME/envs/lri_c2/py3.13.5/bin/python
$PY cluster/expanse/submit.py --check                  # plan rules, limits, SU estimate
$PY cluster/expanse/submit.py --stage P1 --submit      # N=768 grid + three task rows
$PY cluster/expanse/submit.py --stage P2 --submit      # N=1024 grid + two task rows
# Back on the Mac: fetch, verify and index the published records; merge sites.
bash cluster/expanse/collect.sh
python cluster/sitekit/merge_records.py --site-dir expanse=<dir> --site-dir symmetry=<dir> --output merged.json
```

`cluster/production_plan.json` replaces the earlier proposal on both sites:
a PILOT row (N=512, order 1, lambda 0.1), P1 at N=768 and P2 at N=1024 with
lambda*N above 50/60/75 for orders 1/2/3, mixed cutoff 16384 and an explicit
leading-tail cutoff. `cluster/extension_plan.json` is kept unchanged.

The arbitrary-cutoff analysis is implemented separately in `code/continuum/` (13 October 2026).
In particular, replacing `--cutoff 384` by `--cutoff 512` and then invoking the
old `analyze` command is not a complete higher-precision workflow.

### Verification repeated in the cluster-readiness revision

The prior input bundle's 192 listed file hashes were checked before editing.
The current scientific solver and preserved input data are unchanged; their
comparison to that bundle is recorded in `provenance/REVISION_SOURCE.json`.
Fresh finite validation, saved-data analysis, exact arithmetic certification,
cluster-wrapper tests, and a small cached-grid integration run are stored in
`results/revision/`. The note is compiled from its single .tex file in isolation.
The large production plan was not recomputed, and no cluster job was submitted.

### Verification in the Expanse revision

The four scientific files touched by the configurable tail cutoff are listed,
with hashes, in `provenance/REVISION_NOTES.md`. `validate`, `analyze`,
`analyze-recorded`, `demo` and the N=12 cluster task give byte-identical
outputs (timing fields aside) for the old and new code on macOS and on an
Expanse node (`results/expanse/regression_*`). `results/expanse/` also holds
the test reports, the node/auxiliary-cutoff probe, the Expanse smoke chain and
the N=512 pilot (its partial sums agree with the archived N=384 record to
4.4e-7 on all shared cutoffs). `results/symmetry/` holds the symmetry tests,
node probe, smoke chain and a cross-site merge of the two smoke records; the
symmetry N=512 pilot (amdq node <NODE>), which agrees with the Expanse pilot to
6.9e-11 in the raw partial sums (2.1e-15 relative). `results/fix_round1/` holds
the evidence of the first review round (tests on both login nodes and macOS,
regressions, Expanse smoke, row-selection and binding checks). `results/fix_round2/` holds
the second round (tests on all three machines, the Expanse smoke chain, the
manifest-traversal job that failed closed, a symmetry smoke row on the
transferred grid and their merge). The provenance files of the earlier revisions,
including `REVISION_SOURCE.json`, describe those revisions and were not edited.

When collecting a new numerical result, distinguish inherited data from new
computations and retain the plan, source hashes, coefficient-grid metadata,
all raw cutoff sequences, and analysis model choices. Do not replace systematic
uncertainty with the fit residual or number of printed digits.
