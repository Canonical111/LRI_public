# The quadratic energy coefficient of the 2D long-range Ising model

> Public-release edit (2026-10-17): the study's own note and its builder are not shipped (one TeX note per direction);
> passages that pointed to them now point to the SRI note, `SRI/note/sri_short_range.tex`. `public/RE-PINNED.json`
> records the original and published sha256 of this file. Everything else is verbatim.

This package contains a fresh reproduction of the project's final method for **C₂**. The definitions, regulator
matching, derivations, and intermediate identities used to reach the final three-function expression are in the SRI
note, Sec. 3 and Appendix E. Historical alternatives and calculations for other orders or dimensions are excluded.

## Result and convention

The SRI note, Sec. 3.5, gives the original `P,Q,T` expression, defines every hypergeometric parameter and the Gamma
ratio, and reports the numerical values. The full derivation and the checks are in its Appendix E.

The convention is

\[
\delta=(7/4-s)/2,\qquad
\Delta_\epsilon=1+C_2\delta^2+O(\delta^3).
\]

The final expression uses Gamma values and three ordinary, absolutely convergent
`4F3(1)` constants. Its fresh numerical evaluation is

```text
C2 = -4.06627014813252155274002760857287648752990114118661794969937395607493972
```

If the expansion parameter is `7/4-s`, the quadratic coefficient is **C₂/4**,
approximately `-1.01656753703313038819`. Fields have unit scalar two-point
normalization. The SRI note (Sec. 3.5, Appendix E) gives every hypergeometric parameter and normalization.

The physical identification is the project's formal result in the critically
tuned analytic minimal-subtraction prescription. The package reproduces the
special-function evaluation and the implemented exact/local checks. It does not
independently prove a uniform remainder bound for every global nested collision
sector. Numerical discrepancies and long decimal strings are not certified
rounding intervals. These distinctions are stated where they enter the SRI note (Secs. 3.5-3.6, Appendix E).

## Directory structure

| Path | Contents |
| --- | --- |
| `code/` | Scientific evaluators, exact checks, orchestration, and package verifier. |
| `inputs/calculation.json` | Working precision, truncations, and convergence settings for the default run. |
| `inputs/ising2d_exact_data.json` | Exact Ising CFT data and normalization conventions, copied unchanged from the supplied source. |
| `inputs/reference/` | Two unchanged archived outputs used as comparison evidence. |
| `outputs/raw/` | Fresh raw numerical and symbolic results in JSON. |
| `outputs/tables/` | Final constants, validation results, and convergence data in CSV. |
| `outputs/figures/` | Convergence figure exported as vector PDF and PNG. |
| `outputs/summary.json` | Collected result, contributions, numerical discrepancies, and qualifications. |
| `outputs/run_manifest.json` | Execution receipt, settings, script hashes, exit codes, and raw-output hashes. |
| `outputs/self_containment_check.json` | Receipt for a separate run using only copied code and inputs and an empty outputs directory. |
| `outputs/note_build.json` | Build receipt of the study's note (a record; the note itself is not shipped). |
| `outputs/document_validation.json` | Final document and archive verification record. |
| `provenance/source_map.json` | Original source paths and hashes; exact descriptions of copied, adapted, and newly written material. |
| `requirements.txt` | Pinned direct Python dependencies. |
| `DEPENDENCIES.json` | Dependency purposes, tested versions, and module relationships. |
| `MANIFEST.json` | SHA-256 inventory of the delivered files, excluding the manifest itself. |

The exact CFT JSON records the normalization input; the scientific scripts encode
those constants explicitly. Editing that JSON alone does **not** define a new
model. There is no experimental dataset or external data download.

Saved reference coefficients never determine the fresh result. The calculation
is completed before the final reference comparison. The renormalization reference
is retained as historical evidence for the local/contact checks.

## Dependencies

Use **Python 3.11 or later** with the pinned dependencies below. The complete
workflow was tested with Python **3.12.14**.

| Dependency | Version | Purpose |
| --- | --- | --- |
| mpmath | 1.3.0 | Arbitrary-precision Gamma, hypergeometric, elliptic, and contact evaluations. |
| SymPy | 1.14.0 | Exact rational identities, endpoint terms, differential certificates, and Jacobians. |
| NumPy | 2.3.5 | Array arithmetic in independent contact quadrature. |
| SciPy | 1.17.0 | Independent Gauss–Legendre contact quadrature. |
| Matplotlib | 3.10.8 | Export of the convergence figure. |

Install them in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, use `.venv\Scripts\activate` for activation. Dependency installation
can require network access; all subsequent scientific calculations run offline.

## Reproduce everything

Run the following from the extracted package root:

```bash
python code/verify_package.py
python code/reproduce.py
```

The verifier uses only the Python standard library. Run it **before** regenerating
outputs: execution times and PDF metadata can change on a later run, so hashes
of regenerated artifacts need not match the distributed inventory.

The scientific driver stops on any failed stage and writes progress to the
console. It rebuilds the raw results, summary, three CSV tables, and convergence
figure. It creates optional troubleshooting logs under `outputs/logs/` and a
Matplotlib cache under `outputs/.matplotlib/`; these generated temporary files
are not included in the delivered archive. The shipped run took under one minute
on the authoring machine; runtime depends on the system.

The default `inputs/calculation.json` selects 80 decimal digits, 400 half-interval
Frobenius terms, 20,000 direct-series terms, and the convergence sequence
`24, 40, 64, 96, 144, 224, 320, 400`. The independent endpoint-subtracted Carlson
routine internally uses 100 digits and a finite endpoint cutoff `u=200`; its
quadrature and omitted tail are not rigorously enclosed. Changing the global
precision does not automatically change that internal cutoff or subroutine.

The study's note and its builder (`code/build_note.py`) are not part of the public release; the derivation is in the
SRI note, Appendix E, which builds with `make note-pdf` from `SRI/`.

## Which scripts produce which outputs?

All paths in the table are relative to the package root. The default precision
suffix is `80dps`; it follows the configuration when changed.

| Script | Calculation | Generated outputs |
| --- | --- | --- |
| `code/reproduce.py` | Runs the scientific stages and records their execution. | `outputs/run_manifest.json`, optional per-stage logs, and all outputs below through the assembly stage. |
| `code/lri_C2_three_4F3.py` | Final three-function evaluation; six-to-three identities; half-interval Frobenius moment check; rational telescoping. | `outputs/raw/three_4f3_80dps.json` |
| `code/certificate_boundaries.py` | Exact nonzero infinite endpoint terms of all three telescoping certificates. | `outputs/raw/certificate_boundaries.json` |
| `code/analytic_bridge_checks.py` | Differential endpoint certificate, Landen coefficient reduction, cut-jump and reflection matrices, pointwise elliptic identities. | `outputs/raw/analytic_bridges.json` |
| `code/lri_C2_renormalization_checks.py` | Connected kernel, Möbius/Abel Jacobians, elliptic-cover identity, Gaussian finite term, and local OPE checks. | `outputs/raw/renormalization_80dps.json` |
| `code/source_contact_checks.py` | Source-contact identities and their regulator dependence. | `outputs/raw/source_contacts_80dps.json` |
| `code/independent_c2_checks.py` | Separate implementation of endpoint-subtracted Carlson periods, exact tail signs, coordinate/OPE checks, and direct contact quadrature. | `outputs/raw/independent_c2_80dps.json` |
| `code/convergence.py` | Fresh refinement of the half-interval evaluation against a freshly evaluated final formula. | `outputs/raw/convergence.json`, `outputs/tables/convergence.csv`, `outputs/figures/elliptic_convergence.png`, `outputs/figures/elliptic_convergence.pdf` |
| `code/assemble_outputs.py` | Collects fresh outputs and makes the explicit archived-reference comparison. | `outputs/summary.json`, `outputs/tables/final_constants.csv`, `outputs/tables/validation.csv` |
| `code/verify_package.py` | Checks every distributed file's SHA-256 digest. | Console verification result; no scientific outputs changed. |

Every scientific script also has a `--help` command. For example, a standalone
evaluation of the final formula is:

```bash
python code/lri_C2_three_4F3.py --dps 80 --terms 400 --check --symbolic --json outputs/raw/three_4f3_80dps.json
```

The isolated rerun and document-validation receipts describe checks performed
when assembling this delivery. They are provenance records and are not replaced
by the ordinary scientific runner. To repeat the self-containment check yourself,
copy `code/` and `inputs/` to an empty directory and run its `code/reproduce.py`
with the declared dependencies. This produces a new, independently populated
`outputs/` directory.

## How to interpret the validation

The final special-function expression, the six-function intermediate expression,
and the independent Frobenius periods agree to an observed absolute discrepancy
of about `2.53e-80`. The independent Carlson moment calculation agrees to about
`1.40e-61`. Exact rational checks and Gamma endpoint identities have zero symbolic
residuals. The convergence figure shows refinement down to the working-precision
floor; it is not a physical uncertainty plot.

The finite source-matching term contributes approximately
`-1.94527965797909034563` to C₂, while the elliptic integral contributes
approximately `-2.12099049015343120711`. Both are required by the stated method.

The remaining physical issue is the fully explicit global justification of the
continued-distribution comparison across all nested collision sectors. The SRI note
(Sec. 3.6, Appendix E.8) states the channel classification and local cancellations, and identifies the
uniform remainder step that was not independently reconstructed. No elementary
or Gamma-only reduction of the final three hypergeometric constants is claimed.

## Provenance and exclusions

The supplied compendium is the research source. Authorship: OpenAI GPT-6 Astra (via
ChatGPT) wrote this study and the companion cylinder-Hamiltonian study, as stated by
the project author on 14 October 2026. `provenance/source_map.json`
identifies its archive hash, the original report/addendum/audit, unchanged
scientific files, targeted removals from two audit modules, and newly written
orchestration and derivation checks. The full original archive is not a runtime
dependency and is not duplicated here.

The study's trimmed note (not shipped) excluded higher-order work, other dimensions, abandoned
summation routes, exploratory obstructions, and historical numerical detours.
The six-function intermediate identity remains because it is used to derive the
final three-function result. The necessary finite contact and telescoping
endpoint terms also remain, with explicit derivations.

The package excludes temporary build files, interpreter caches, downloaded
dependencies, old logs, and scratch derivation fragments. No result is obtained
by loading the conversation or an unshipped source module.
