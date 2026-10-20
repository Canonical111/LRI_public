# Long-range Ising bulk one-point data: reproducibility package

**Release: 16 October 2026.** Start with [`note/lri_ope_note.pdf`](note/lri_ope_note.pdf), the 34-page calculation record. Its source, [`note/lri_ope_note.tex`](note/lri_ope_note.tex), has its own bibliography and compiles without another source file. Optional figures are included when available; without them, the source produces clearly labelled placeholders rather than failing.

This package collects the bulk one-point calculation through `a_6(d)`, its relationship to the thermal coefficients `C_i(d)`, the symbolic and numerical verification programs, and the comparison with published bootstrap figures. It is an auditable research record, **not an independently certified determination of all high-order physical coefficients**.

## 1. Observable, conventions, and scope

The calculated quantity is

```text
epsilon = 2 s - d,       q = d/4,       Delta_phi = (d-epsilon)/4,
< :Phi^2:(x,y) > = a_phi2(d,epsilon) / |y|^(2 Delta_phi),
a_phi2(d,epsilon) = sum(n=2,...,6) a_n(d) epsilon^n + O(epsilon^7).
```

The auxiliary bulk field has unit free two-point amplitude; the interaction on the physical `d`-dimensional defect is `lambda phi^4/4!`. Integrals requiring continuation use the critical-mass-subtracted prescription in the note. The formulas apply at fixed `0 < d < 4` near `epsilon = 0`; the `d -> 4` limit is nonuniform.

`a_phi2` is the **bulk one-point coefficient** used as the horizontal coordinate in the bootstrap comparison. It is not the thermal scaling dimension, and it is not the squared defect OPE coefficient `lambda_(phi phi E)^2`, whose free value is 2. The thermal dimension is

```text
Delta_E = d/2 - epsilon/6 + C_2(d) epsilon^2 + C_3(d) epsilon^3 + ... .
```

The main results are the Gamma-factor representation through sixth order, the explicit `a_2,...,a_6`, and the logarithmic map from the thermal coefficients. At general `d`, the map to `a_6` requires the additional combination `Omega_d = 13 Z_d - L_d - 12 K_d`. The updated two-dimensional identities eliminate this combination in terms of `C_3(2), C_4(2)` and standard constants. Here `K_d,L_d,Z_d` mean the nonprimitive master functions, not `-a_2`.

### What is not claimed

* Re-executing the graph reconstruction and changing regulator directions are internal checks using shared master identities and the same subtraction framework. They are not independent numerical integration of every original five- or six-vertex graph.
* The package includes selected **full finite-regulator** kite and Selberg checks at lower orders. The README distinguishes these from algebraic regression and analytic reconstruction.
* Arithmetic precision and small verification residuals do not bound omitted powers of `epsilon`, resummation bias, or shared mistakes in the input framework.
* The bootstrap comparison does not run a bootstrap solver or provide a continuum-positive excluding functional. The static boundary curves and kink marks are approximate figure readings.
* The selected thermal source contains additional high-loop results, but reproducing its separate `C_6`–`C_8` thermal HPC campaigns is outside the scope of this OPE package. Those data are not needed for the one-point calculation through `a_6`; displayed `C_6` values are used only for the thermal coordinate of the plots.

## 2. Directory structure

```text
lri_ope_reproducibility/
  README.md                         This guide
  requirements.txt                  Exact Python dependency versions used
  Makefile                          Optional shortcuts to the root runner
  MANIFEST.sha256                   SHA-256 of every release file except itself
  run.py                            Supported staged reproduction entry point
  note/
    lri_ope_note.tex                 Self-contained source with internal bibliography
    lri_ope_note.pdf                 Compiled calculation record
  code/
    low_order/                      Two-/three-vertex and OPE-ratio checks
    a4/                             Fourth-order assembly and full kite checks
    a5/                             Five-vertex enumeration and reconstruction
    a6/                             Six-vertex reconstruction, RG forests, masters
    relations/                      Thermal-to-one-point conversion and checks
    bootstrap/                      Rational Borel transforms, plots, HTML overlays
    evaluate_project.py             Coefficient table and exact d=2 input update
  data/
    source/                         Exact selected thermal note and provenance
    a5/                             Two-point graph inventories through five vertices
    a6/                             Two-point/vertex inventories and master inputs
    relations/                      Historical regression inputs
    bootstrap/                      Historical coefficients and figure readings
    reference/                      Stored verification baselines, explicitly labelled
    thermal_current.json            Latest thermal table, with precision qualifications
  results/
    coefficients.json               Coefficients, masters, log map, mapping residuals
    coefficient_table.csv           a_2,...,a_6 at d=1,2,3
    figures/                        Main historical-input plots used in the PDF
    bootstrap/
      historical/                   Historical inputs and all numerical/plot outputs
      current/                      Updated thermal-input sensitivity run
      thermal_input_sensitivity.json
    verification/                   Fresh reports and selected audit certificates
  scripts/
    check_manifest.py               Verify the release hashes without changing files
    check_standalone_note.py        Compile only the .tex in an empty directory
```

The versioned inventories and symbolic certificates are retained because they are test inputs or auditable calculation results. No virtual environment, font files, Python bytecode, TeX auxiliary files, reconstruction scratch directories, or unrelated HPC logs are distributed.

## 3. Dependencies and installation

### Python

The reproduction run used **Python 3.13** with:

| Package | Version | Role |
|---|---:|---|
| mpmath | 1.3.0 | Arbitrary-precision arithmetic, Gamma/polygamma/hypergeometric functions |
| sympy | 1.14.0 | Exact symbolic reduction and rational algebra |
| numpy | 2.3.5 | Quadrature arrays and plotting inputs |
| scipy | 1.17.0 | Numerical quadrature and special functions |
| matplotlib | 3.10.8 | Static comparison plots |

The pinned set requires Python **3.11 or newer**; the release was tested on 3.13, not on every supported version. The standalone coefficient and thermal-map calculators only need `mpmath`; symbolic verification adds `sympy`. Use all dependencies for the complete workflow.

From this directory:

```bash
python -m venv .venv
# POSIX shells:
source .venv/bin/activate
# Windows PowerShell alternative:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

No Mathematica, FunTable checkout, bootstrap solver, or network access is required for the calculated coefficients, checks, static plots, or PDF. The optional HTML overlay requests original arXiv images when opened online. It states explicitly whether an original image or the approximate fallback is displayed.

### LaTeX

Install `pdflatex` and `latexmk`, for example through TeX Live or MiKTeX, with the packages used in the source: `geometry`, `fontenc`, `inputenc`, `lmodern`, `microtype`, `amsmath`, `amssymb`, `mathtools`, `bm`, `mathrsfs`, `booktabs`, `array`, `longtable`, `tabularx`, `graphicx`, `xcolor`, `fancyhdr`, `enumitem`, `listings`, `needspace`, `hyperref`, `bookmark`, and `xurl`.

On Debian/Ubuntu, the relevant TeX components are normally supplied by `latexmk`, `texlive-latex-base`, `texlive-latex-recommended`, `texlive-latex-extra`, `texlive-fonts-recommended`, and `lmodern`. A full TeX installation also suffices. The PDF is already included, so TeX is only needed to rebuild it.

## 4. Reproduce the results

### Fast entry point

```bash
python run.py quick
```

This evaluates the coefficient table, checks the thermal map and low-order formulas, and runs a **stored-certificate regression**. It does not regenerate all graph reconstructions.

### Full sequence

```bash
python run.py all
```

Equivalent explicitly separated commands are:

```bash
python run.py quick
python run.py symbolic numeric integrals masters
python run.py figures
python run.py note
```

The runner stages each legacy engine in a temporary directory with its required JSON inputs and relative imports, so it does not overwrite source inputs. It checks subprocess return codes and retains named final outputs and verification reports. An exception or failed assertion terminates the task with a nonzero exit status. Working directories are cleaned automatically.

To put regenerated results elsewhere:

```bash
python run.py quick symbolic --output-dir /absolute/path/to/new_results
```

Use the same output directory across tasks to use the newly generated certificates and figures. `note` writes the compiled PDF to `note/lri_ope_note.pdf` in the package, even with a custom results directory; its build report goes under that results directory. Run `figures` before `note` to include the generated plots. Without figures, standalone fallback boxes are expected.

### Commands, scripts, and outputs

All output paths below are relative to `results/` unless otherwise stated.

| Task | Programs invoked | Main outputs and meaning |
|---|---|---|
| `quick` | `low_order/check_a_phi2.py`; `relations/relations.py --verify`; `relations/check_numeric.py`; `evaluate_project.py`; `a6/verify_a6.py` | `coefficients.json`, `coefficient_table.csv`; low-order and map checks; `verification/a6_stored_certificate_regression.json` checks supplied certificates, not fresh reconstruction |
| `symbolic` | `a5/enumerate_graphs.py`, `symbolic_kernels.py`, `symbolic_assembly.py`; `a6/enumerate_graphs.py`, `vertex_graphs.py`, `symbolic_engine.py`, `universal_assembly.py`, `collect_a6.py`, `verify_a6.py` | `verification/a5_symbolic/`, `verification/a6_symbolic/`; fresh inventories, kernels, MS assembly, pole and cancellation checks; inventories compared with `data/` |
| `numeric` | `a6/verify_a6.py --numeric --dimension 1` and its reconstruction/forest modules | `verification/a6_numeric/verification_results.json`; fresh 60-digit reconstruction with different rational regulator/reference seeds and a nonzero arbitrary crossed-kite coefficient |
| `integrals` | `a4/symbolic_check.py`, `a4/verify_a4.py`, `a5/verify_a5.py` | `verification/a4_integrals/`, `verification/a5_numeric/`; full finite-regulator fourth-order kite/Selberg checks, plus fifth-order reconstruction and a special-graph Selberg check |
| `masters` | `a6/evaluate_fixed_dimensions.py`, using `spectral_masters.py` | `verification/master_quadrature/`; varied quadrature and analytic spin tails at d=2,3; master inputs and resulting coefficients |
| `figures` | `bootstrap/compare_sixth_order.py`, twice with versioned inputs | `bootstrap/historical/`, `bootstrap/current/`, sensitivity JSON, and the main PNGs in `figures/` |
| `note` | `latexmk -pdf` on a temporary copy of `note/lri_ope_note.tex` | `note/lri_ope_note.pdf`; `verification/latex_build.json` with reference and box checks |
| `manifest` | Standard-library SHA-256 generation in `run.py` | Root `MANIFEST.sha256`; run only after intentionally updating the release |

Every executed task writes `verification/run_TASK.json`, recording the tested environment, actual command arguments, observed duration, and pass/fail status. Reports may contain original output-directory paths as provenance; the scripts locate their inputs from the package root and do **not** depend on those recorded paths.

The fresh release checks passed for `quick`, `symbolic`, `numeric`, `integrals`, `masters`, `figures`, and `note`. The actual durations are in their reports, rather than guaranteed runtimes for another machine. Small numeric changes across library/platform versions are possible, especially in machine-array quadrature; inspect convergence and assertions, not byte equality of every floating-point file.

### Build only the note

```bash
python run.py note
```

Or, without Python:

```bash
cd note
latexmk -pdf -interaction=nonstopmode -halt-on-error lri_ope_note.tex
# Remove TeX auxiliary files after a successful build, retaining PDF and source:
latexmk -c
```

To check that the source really is standalone:

```bash
python scripts/check_standalone_note.py
```

This copies only the `.tex` file into a fresh temporary directory, compiles there without any figure or bibliography files, and writes `results/verification/standalone_latex.json`. The release PDF retains the plots; this test does not replace it with the placeholder version.

## 5. Direct coefficient calculations

### Formula mode

The public sixth-order calculator accepts `d` and the six masters `T,P4,P5,K,L,Z`. In code, `T = 6 Q_d`, while `K,L,Z` denote the nonprimitive masters.

```bash
python code/a6/calculate_a6.py --dimension 1 --precision 60
python code/a6/calculate_a6.py --dimension 3 --precision 60 \
  --inputs data/a6/d3_inputs.json --output /tmp/a6_d3.json
```

For a Python call from the package root:

```python
from pathlib import Path
import json
import sys
import mpmath as mp

sys.path.insert(0, str(Path("code/a6").resolve()))
from calculate_a6 import coefficients

mp.mp.dps = 60
inputs = json.loads(Path("data/a6/d3_inputs.json").read_text())
answer = coefficients("3", **inputs)
for n, value in answer["coefficients"].items():
    print(n, mp.nstr(value, 15))
```

For `d=1`, all six masters can be evaluated from the fixed special-function representations by the calculator itself. For other `d`, provide the required masters; their **definitions** for general dimension are given in the note. The dedicated spectral evaluator in this release is tested for `d=2,3`, not as a black-box arbitrary-dimensional quadrature service.

### Thermal-coefficient mode

The simpler map uses the `from_thermal` function:

```python
from pathlib import Path
import sys
import mpmath as mp

sys.path.insert(0, str(Path("code/relations").resolve()))
from relations import from_thermal

mp.mp.dps = 50
answer = from_thermal(
    "2", C3="-0.874850012653", C4="5.048868431", C5="-38.833645896"
)
for n, value in answer["a_coefficients"].items():
    print(n, mp.nstr(value, 12))
```

These displayed thermal inputs are rounded; the output should not be expected to reproduce every digit of the high-precision master-mode table. At general `d`, pass `omega=13*Z-L-12*K` to compute `a_6`. Omit `C5` to compute only through `a_5`, without `omega`. At `d=2`, the exact identities infer `omega` from `C3,C4`. `C2` is calculated from its polygamma formula, not independently fitted.

The map is an algebraic consequence of the project-derived one-point coefficients; using it does not independently validate either underlying loop calculation.

## 6. Input provenance and precision

### Thermal archive

`data/source/thermal_note_2026-10-15.tex` is the exact selected source from the user's `GFF.zip`. `PROVENANCE.json` records the archive SHA-256, member origin, selected-file hashes, and source-normalization edits. The thermal source is preserved as an input/reference record; its own source-tree requirements and broader HPC reproductions are not the build target of this package. The **new OPE note** is the standalone document.

The full original ZIP was about 352 MB and included unrelated thermal HPC runs, repeated artifacts, binary/platform files, and caches. Those are intentionally omitted. All code and inputs needed by the OPE workflows described here are included. No access to the conversation or original ZIP is needed to run these workflows.

### Master inputs and the exact d=2 update

`data/a6/d2_inputs.json` and `d3_inputs.json` retain the historical primitive and nonprimitive input values. `evaluate_project.py` upgrades the d=2 nonprimitive values using

```text
K_2 = 32 Catalan^2 - 28 zeta(3) log(2),
L_2 = -2 log(2) P4(2),
Z_2 = 4 Catalan Q_2.
```

This changes the earlier d=2 value of `a_6` by about `-2.7e-13`, not by a physically significant amount for the plots. The current coefficient table gives approximately

```text
a_6(1) = 450.850442331799251
a_6(2) =   6.099467952385831
a_6(3) =   0.507382663943009
```

Fixed hypergeometric/Gamma representations are available in the code and note for the d=1,2 primitive periods. The stored d=2 primitive inputs have finite high precision; simply increasing `--precision` does not add information to an already stored decimal. The d=3 primitive values are supplied by the source note, and the nonprimitive inputs come from converged machine-array spectral quadrature with analytic tails. Many printed digits in JSON are arithmetic output, not certified accuracy. The `masters` task reevaluates and varies quadrature settings; it does not overwrite the historical inputs.

### Graphs and stored certificates

Graph JSON files specify canonical edge words/matrices and exact weights. They are required by numerical reconstructions and can be regenerated with the `symbolic` task. Two-point inventory counts through 2–6 vertices are 1, 1, 5, 14, 64. The sixth-vertex RG inventory contains 129 classes. Zero/scaleless contributions and mass subtractions are handled according to the conventions stated in the note.

`data/reference/` contains earlier verification baselines. These are not presented as fresh output. The quick regression deliberately reads them; `symbolic` produces fresh versions under `results/verification/a6_symbolic/`, and `numeric` uses those fresh certificates when they are present in the selected results directory.

### Historical and current bootstrap inputs

`data/bootstrap/inputs_historical.json` preserves the coefficient inputs and approximate readings from Behan–Lauria–Nocchi–van Vliet, **arXiv:2311.02742v6**, Figures 4, 7, and 11. The main static comparisons use Figure 11 in 3D and the refined Figure 7 kink positions in 2D. Figure 4 is also available in the HTML comparison with its corresponding assumptions. These are not author-supplied raw numerical bootstrap data.

The historical thermal inputs use `C6(2)=362.3`, `C6(3)=33.57`. The current sensitivity run uses the newer source table (`362.366` and `33.5754`), preserving the horizontal input and resummation prescription. `data/thermal_current.json` also retains unused higher table entries for provenance; the plot runner uses only C0–C6. The comparison does not fit a bootstrap point or a short-range endpoint.

Horizontally, factor out `epsilon^2` and Borel–Padé resum the remaining series using `[3/1]` and `[1/3]`. Both have no positive-axis Borel poles for these inputs; the `[2/2]` approximant does and is rejected. Vertically, use `[4/2]` on the full thermal series through C6. Pole diagnostics, Taylor-matching residuals, partial sums, all coordinates, and the exact input snapshots are recorded alongside each plot run. Separation between prescriptions is **not** a confidence interval.

## 7. Verification and integrity

The fresh checks include exact graph-weight/inventory reconstruction, counterterm poles through fourth order at six vertices, cancellation of mass-subgraph functions and an arbitrary crossed-kite coefficient, the independent assembly of `3 c5 - b5` within the shared master framework, outer-Gamma factorization, and both general/d=2 thermal maps. The note and reports state the limits of each check.

On the release machine, the alternate-regulator sixth-order numerical reconstruction agrees with the compact formula at roughly `1e-53`, and residual poles are of order `1e-52`. Selected full-integral checks and master convergence tests are separately recorded. These residuals must not be used as physical uncertainty estimates.

Before running commands that overwrite outputs, verify the downloaded release:

```bash
python scripts/check_manifest.py
# POSIX alternative:
# sha256sum -c MANIFEST.sha256
```

After deliberate modifications, `python run.py manifest` creates a new manifest. Regenerated reports contain new durations or paths and can legitimately change their hashes. Do not regenerate the manifest merely to conceal an unexplained input change.

## 8. Further work

The next decisive checks are independent evaluations of selected high-order finite graph parts, an independently controlled resummation error assessment, and continuum-positivity checks of the functional apparently excluding the weak-coupling point. The bootstrap grid explanation is a concrete possibility, not a proven resolution. The one-dimensional super-sum-rule route also requires OPE/mixing data and control of enhanced spectral tails; no higher-order FunTable bootstrap computation is included here.

See the note's bibliography for primary literature and its open-issues section for the detailed program. The formulas are finite-order statements: leaving the external Gamma functions or the logarithmic exponential unexpanded does not determine higher coefficients.
