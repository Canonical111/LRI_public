# GFF packages

What each package in `code/` contains and computes.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `GFF/`. The values themselves are in `note/README.md` and the note.

- C0-C5 in closed form, d = 1: `lri_numerical_resolution`, `lri_psi_complete_update`, `lri_fixed_hypergeometric_update`
- C0-C5 in closed form, general d: `lri_general_special_functions_update`, `lri_general_closed_update`, `lri_general_periodization_update`
- Closed forms of L2, K2 and C5(2): `LRI_C5_d2_simplify`, `LRI_C5_d2_proof`
- d = 3 specialization and the generic-dimensional reduction of L_d, Z_d, K_d: `lri_d3_reduction_update`, `lri_d3_matrix_update`, `LRI_C5_general_d`, `LRI_C5_d3`
- C6(1) and its analytic representation: `LRI_C6_1D_HPC`, `C6_research_note`, `LRI_C6_closed_form_review`
- Finite kernels, power compensation, C6(2) and C6(3): `lri_C6_d2_complete_update`, `lri_C6_d3_complete_update`, `LRI_C6_D2_HPC`, `LRI_C6_D3_HPC`
- Full C7(1), C7(2), C7(3): `LRI_C7_HPC`, `LRI_C7_D2_HPC`, `LRI_C7_D3_HPC`
- Full C8(1), C8(2), C8(3) and the independent checks: `LRI_C8_HPC`, `LRI_C8_D2_HPC`, `LRI_C8_shared`, `LRI_C8_D2_HPC_optimized`, `LRI_C8_D3_HPC`, `LRI_C8_D3_OPT`

## C0-C5 in closed form, d = 1

### `lri_numerical_resolution`

Folder: `code/lri_numerical_resolution/`.

#### GFF/code/lri_numerical_resolution (draft for GFF/README.md)

**Row:** one-dimensional analytic C5 (note Section 33), principal package. **Origin:** research bundle, September 2026
(see PROVENANCE_lri_numerical_resolution.md).

Independent full-graph numerical control of the closed form C5(1) = -731.13947662453982585... (note Section 14):
the raw Laurent amplitudes of all 59,145 ordered five-loop graphs, integrated without analytic periods as input,
are reassembled at 80 digits through minimal subtraction and the fixed point and agree with the closed form to
6.4e-13 (span cutoff) and 3.0e-12 (largest gap) at degree 24. The package also holds the exact residue
certificate (26 four-loop and 92 five-loop rows, note Appendix A) and its exact SymPy check against the RG
assembly of the closed form (note Sections 4 and 13), and the C++ kernels and drivers that produced the raw
records.

Principal record: `verification/records/resolution_audit.json`. Inputs: `verification/records/combined5_*.json`,
`amplitude5_*.json`, `lower_*_32.json`, `verification/inputs/`. Code: `verification/*.py`, `verification/source/`.

    make -C code/lri_numerical_resolution -f public.mk test     # ~1 s, one core
    make -C code/lri_numerical_resolution -f public.mk replay   # ~25 s, one core

`replay` also recomputes the 80-digit special-function reference (K, L, P4, P5, closed-form C5(1)), regenerates the
graph inputs against the SHA-256 hashes of the executed inputs, and audits the unlabelled classes
(129 = 92 + 6 + 3 + 28, note Section 13). Details and the production rerun: `code/lri_numerical_resolution/public/README.md`.
The package's own `README.md` is its original final report; files it names that are not exported are listed there.

### `lri_psi_complete_update`

Folder: `code/lri_psi_complete_update/`.

#### GFF/code/lri_psi_complete_update (draft for GFF/README.md)

**Row:** one-dimensional analytic C5 (note Section 33), check of the compact master K. **Origin:** research bundle,
September 2026 (see PROVENANCE_lri_psi_complete_update.md).

Checks of the proved evaluation K = [psi1(1/4)(3 psi1(1/4) - psi1(3/4)) + A psi2(1/4)]/2 = 39.3315691282590390575...
(note Section 8) and of the reflected-quarter polygamma forms of C0..C5(1) (note Sections 1.1 and 4): an exact SymPy
certificate of the proof steps and of every rewriting, the original endpoint-subtracted master integral at 110 digits
(residual 6.4e-109), the coefficient values at 70 digits, and finite-parameter and complex bilinear tests.

    make -C code/lri_psi_complete_update -f public.mk test     # ~2 s, one core
    make -C code/lri_psi_complete_update -f public.mk replay   # ~15 s, one core

Details: `code/lri_psi_complete_update/public/README.md`. The proof itself is Section 8 of the note.

### `lri_fixed_hypergeometric_update`

Folder: `code/lri_fixed_hypergeometric_update/`.

#### GFF/code/lri_fixed_hypergeometric_update (draft for GFF/README.md)

**Row:** one-dimensional analytic C5 (note Section 33), check of the five-value P5. **Origin:** research bundle,
September 2026 (see PROVENANCE_lri_fixed_hypergeometric_update.md).

Verifier of the preferred finite form of the five-loop primitive period, P5 = 28599.2931765621035366464770214...,
as four 9F8(-1) values and one 8F7(-1) value with fixed positive rational parameters (note Sections 1.1, 4.1 and
10), against a fresh positive Gamma quadrature at 100 and 125 digits (residual 3.6e-121), with its record
`verification/fixed_hypergeometric_checks.json`. Two public-edition checks are added in `public/`: the d = 1 closed
forms of note Section 1.1 evaluated as printed (C2..C5(1), K, L, P4, P5 at 70 digits) and the exact Barnes kernel
identity of note Section 10.

    make -C code/lri_fixed_hypergeometric_update -f public.mk test     # ~3 s, one core
    make -C code/lri_fixed_hypergeometric_update -f public.mk replay   # ~6 s, one core

Details: `code/lri_fixed_hypergeometric_update/public/README.md`. The proof is Section 10 of the note.

## C0-C5 in closed form, general d

### `lri_general_special_functions_update`

Folder: `code/lri_general_special_functions_update/`.

#### lri_general_special_functions_update: C0..C5 at general dimension

This package gives the coefficients C0..C5 of Delta_E(d, epsilon) at any fixed 0 < d < 4 (note Sections 12-13):

    C0 = d/2,  C1 = -1/6,  C2 = A/9,  C3 = (A^2 + R - 8Q)/108,
    648 C4  = 16 P4 - A^3 - 8AQ - 3AR + (53/2) U - 3V,
    46656 C5 = -1536 (P5 + K_d) + 384 A P4 - 576 L_d - 1728 Q^2 + 720 A^2 Q + 1008 Q R + 7152 Z_d
               - 15 A^4 - 90 A^2 R + 414 A U - 108 A V - 117 R^2 - 75 X,

with the polygamma combinations A, R, U, V, X of q = d/4 and six masters (the tetrahedron Q_d, the primitive periods
P4(d), P5(d), and the nonprimitive K_d, L_d, Z_d), and evaluates them at d = 1, 2, 3. The Section 1 table entries
C4(2) = 5.048868431, C5(2) = -38.833645896, C4(3) = 1.228063545, C5(3) = -5.850351421 and C2, C3 at d = 2, 3 are these
values at the printed digits.

##### What it contains

- `code/general_special/`: the conformal graph reduction (`analytic_core.py`, `series_engine.py`, `ct_engine.py`,
  `collect.py`; the graph classes in `C5_wheel_nonprimitive/reduced_classes.json`), the saved residue rows
  (`rows_3_0_8.json`, `rows_4_0_27.json`, `rows_5_0_129.json`), the exact fixed-point assembly (`sum4.py`, `sum5.py`,
  `exact_audit.py`), the spectral evaluation of the masters (`wheel_spectrum.py`, `spectral_evaluate.py`), the
  coefficient assembly (`assemble_results.py`) and independent master checks (`kappa_mb.py`, `residue_checks.py`,
  `ordered_series_checks.py`, `hypergeometric_series.py`).
- `code/{graph_inventory,inventory_checks,symbolic_checks,tetrahedron,two_loop_master,primitive_spectral}.py` and their
  records in `verification/`: the general-dimensional C0..C3, the graph inventory through five loops, the tetrahedron, the
  two-loop master and the primitive spectral sums (note Section 12). They come byte-identical from the earlier bundle
  package `lri_general_dimension_update`, which is not shipped separately.
- `verification/general_special/`: the delivered records (the scripts write identical copies into `code/general_special/`).

##### Scope (read before using the formulas)

The formulas for C4(d) and C5(d) come from a single graph-by-graph minimal-subtraction calculation by the delivering
model; it has not been rederived independently at generic d. At d = 1 the formulas reproduce the analytic C4(1) and C5(1)
exactly; at d = 2 and 3 they are confirmed only through the six masters (the d = 2 closed forms of L2, K2 and the 50-digit
d = 3 values of other units agree with this package's masters to about 1e-13). The masters are evaluated here by spectral
sums in double precision with angular-tail acceleration, accurate to about 1e-13 relative; the coefficient values are
quoted to ten digits. C5(d) has been evaluated only at d = 1, 2, 3.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk replay` | reruns the exact assembly, the C0..C5 values from the saved masters and the C1..C3 Lagrange inversion in a copy and compares them with the delivered records; checks the note's formulas symbolically; recomputes every quoted number at its printed digits and the cross-checks with the d = 1, 2, 3 units (78 rows) | about 5 s, one core; Python >= 3.10 with numpy, scipy, sympy, mpmath; macOS or Linux |
| `make -f public.mk test` | replay, then regenerates in a second copy everything the replay reads (graph reduction through five loops, the masters, the reassembly) and runs the remaining delivered checks (115 rows) | about 2.5 min, one core, < 1 GB |

##### Files added for the release

`public.mk`, `public/replay.py`, `public/common.py` (shared with the two other general-d packages), `public/SOURCE_SHA256SUMS`
(bundle MANIFEST.json hashes of the 71 shipped source files; complete, checked by both targets), `REVIEWS.md`. Everything
else is the package as delivered in `LRI_complete_research_bundle.zip` (sha256 3715f545...).

`code/general_special/check_A_d1.py` ships verbatim but cannot run: it reads `/mnt/data/lri_special_function_work/...`, a
folder of the delivering session that is not part of the delivery. Its output `A_d1_checks.json` ships as delivered. The
path is a sandbox path, not a personal one (allowlist it in the privacy scan; the file is bound by SOURCE_SHA256SUMS).

##### Not shipped

The package's `history/`, its snapshots of the canonical note and chapter PDFs (superseded by `GFF/note`), the
one-dimensional files it carries from earlier bundle packages (C5 numerical audit, P5 hypergeometric representations;
shipped by the d = 1 unit from their own packages), and two stale records (`verification/general_dimension_manifest.json`,
`verification/source_preservation.json`).

### `lri_general_closed_update`

Folder: `code/lri_general_closed_update/`.

#### lri_general_closed_update: finite Horn arrays of the C5 masters

This package writes every master of C4(d) and C5(d) (Q_d, P4(d), P5(d) = P5a + P5b, L_d, Z_d, K_d) as an explicit finite
list of multivariable Horn hypergeometric values at fixed arguments (note Section 14), and proves the d = 2 normalization

    Q2 = Gamma(1/4)^8 / (24 pi^4) = 12.7713811986469576577497636845240084220372849859347...,   Z2 = 4 G Q2.

The note quotes Q2 (Sections 1.1 and 14.1) and the numbers of Horn values of L_d, Z_d and K_d: 244, 318 and 386, with
at most six summation variables each (Section 14.6). The package README also lists Q 20, P4 56, P5a 6024 and P5b 9036
(16084 values, 450409 parameter rows in all).

##### What it contains

- `code/general_closed/horn_compiler.py`: the compiler that produces the arrays from the finite residue polynomials;
  `read_horn_arrays.py` reads one array entry and evaluates its coefficients.
- `verification/general_closed/horn_arrays/`: the seven arrays (`*_horn.json.gz`), the scalar-parameter and atom
  dictionaries and `summary.json`; `array_manifest.json` holds their SHA-256.
- The checks: `check_new_identities.py` (60-digit Q2, Z2, K-term identities, P5 residues on Cauchy circles, measure-pole
  antisymmetry, a fresh d = 1 Gamma integral), `check_horn_compiler.py` (1038 exact normalized coefficients, 12 shift
  identities), `check_insertion_prefactors.py` (336 exact rational checks), `kappa_regularization.py` (the K_d
  cancellation polynomial), `check_primitive_sums.py` and `primitive_series.py` (double-precision residue sums of P5
  against spectral quadrature at d = 1, 2, 2.6, 3).
- `code/primitive_spectral.py`, the spectral evaluator imported by `check_primitive_sums.py` (the only file kept from the
  layers this package inherited; the others ship in `GFF/code/lri_general_special_functions_update`).

##### Scope

The arrays are a function-class statement, deliberately not minimal: the common convergence strip is 1/6 < d/4 < 1/2,
outside it the complete finite combination is continued in d (some K_d series at unit argument diverge individually for
d >= 2). They are not a reduction to ordinary hypergeometric values, and the reader evaluates coefficients, not the
continued functions. The general formulas for C4(d), C5(d) that use these masters carry the caveat stated in the
special-functions package: one graph calculation, checked exactly at d = 1 and through the masters at d = 2, 3.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk replay` | integrity (SOURCE_SHA256SUMS complete, `array_manifest.json` complete, `release_manifest.json` ignore-missing); reruns the identities, the prefactor checks, the K_d polynomial and the compiler for Q, P4, L, Z, K in a copy and compares with the delivered records (arrays on their decompressed bytes); Q2, Z2 and the Horn counts (35 rows) | about 25 s, one core; Python >= 3.10 with numpy, scipy, sympy, mpmath; macOS or Linux |
| `make -f public.mk test` | replay plus the full compiler (P5a, P5b), `check_horn_compiler.py`, `check_primitive_sums.py`, `primitive_series.py` | about 4 min, one core, 0.25 GB |

##### Files added for the release

`public.mk`, `public/replay.py`, `public/common.py` (shared with the two other general-d packages), `public/SOURCE_SHA256SUMS`
(bundle MANIFEST.json hashes of the 31 shipped source files), `REVIEWS.md`.
`verification/general_closed/release_manifest.json` still lists the delivered note snapshot `long_range_ising_complete.tex`
and `.pdf`, which are not shipped (checked with ignore-missing).

##### Not shipped

`history/`, the note snapshots and chapter PDFs (superseded by `GFF/note`), and the 126 other files inherited from the
special-functions package: byte-identical to files of that export, or one-dimensional material shipped by the d = 1 unit
from its own packages.

### `lri_general_periodization_update`

Folder: `code/lri_general_periodization_update/`.

#### lri_general_periodization_update: primitive periodization and the d = 2 factorization

This package reduces the primitive periods Q_d, P4(d), P5(d) at any d to at most 15, 20 and 56 fixed evaluations of
functions with at most two summation variables (finite Fourier periodization; note Sections 15.1-15.4), and proves that
at d = 2 the primitive periods are quadratic in the one-dimensional hypergeometric values (Section 15.5):

    P4(2) = (B-^2 - B+^2) / (4 pi^3)                 = 250.48731558186728553185175688791140716835571092358...
    P5(2) = (8/pi) [25 X0^2 - 28 sqrt2 X0 (X+ + X-) + 18 (X+^2 + X-^2) + 28 X+ X-]  = 1548.082640233120615132439...

with B-+ the two normalized 4F3(1) values and X0, X+-, the three combinations of the four 9F8(-1) and one 8F7(-1) values of
the d = 1 calculation. The note quotes P4(2) to 50 digits (Section 14.2) and the exact vector
(B_{7,0}, ..., B_{7,6}) = pi^6 (20, 0, 28, 0, 84, 0, 924) at q = 1/2 (Section 15.5); the paper gives the closed forms of P4(2), P5(2)
(eq. cf:d2-P), without digits. These two values enter the d = 2 closed form of C5(2), which belongs to `GFF/results/closed_forms_2`.

##### What it contains

- `code/general_periodization/`: `horn_templates.py` (the one- and two-variable parameter templates, written to
  `verification/general_periodization/arrays/`), `gamma_series.py`, and the checks `check_exact_algebra.py` (SymPy),
  `check_two_dimensional.py` (55-digit d = 2 kernels), `check_d2_control.py` (70 digits, other tails and grid),
  `check_d2_inherited_periods.py` (60-digit literal `mpmath.hyper` of the d = 1 values; the quadratics agree with the
  70-digit d = 2 values to 6e-59 and 2e-58), `check_horn_templates.py`, `check_wheel_periodization.py` (35-digit Barnes
  integrals) and `check_p5_periodization.py` (double-precision generic-d sampling against spectral quadrature).
- `code/primitive_spectral.py`, imported by `check_p5_periodization.py` (the only file kept from the inherited layers).
- `archive_manifest.json`: SHA-256 of all 205 files of the delivered package.

##### Scope

The generic-d formulas still contain genuine two-variable Horn functions; they are not a reduction to one-variable
values. The nonprimitive masters K_d, L_d, Z_d are not reduced here. The d = 2 factorizations are proved; the numerical
records are consistency checks, not interval bounds.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk replay` | integrity (SOURCE_SHA256SUMS complete; `archive_manifest.json` ignore-missing, 182 of its 205 files are not shipped); reruns the exact algebra, the d = 2 chain and the templates in a copy and compares with the delivered records; P4(2), P5(2), B7 and the cross-checks of the closed forms of C4(2), C5(2), L2 (30 rows) | about 10 s, one core; Python >= 3.10 with numpy, scipy, sympy, mpmath; macOS or Linux |
| `make -f public.mk test` | replay plus `check_wheel_periodization.py` and `check_p5_periodization.py` (34 rows) | about 50 s, one core |

##### Files added for the release

`public.mk`, `public/replay.py`, `public/common.py` (shared with the two other general-d packages), `public/SOURCE_SHA256SUMS`
(bundle MANIFEST.json hashes of the 24 shipped source files), `REVIEWS.md`.

##### Not shipped

`history/`, the note snapshots, chapter PDFs and `source_diff.patch` (superseded by `GFF/note`), and the 156 other files
inherited from the closed-forms package: byte-identical to files of the two other general-d exports, or one-dimensional
material shipped by the d = 1 unit from its own packages.

## Closed forms of L2, K2 and C5(2)

### `LRI_C5_d2_simplify`

Folder: `code/LRI_C5_d2_simplify/`.

#### LRI_C5_d2_simplify: discovery and numerical confirmation of the d = 2 closed forms

This package found the closed forms of the two nonprimitive five-loop masters at d = 2 (note Section 17.2):

    L2 = -2 log2 P4(2),        K2 = 32 G^2 - 28 zeta(3) log2,

and therefore the closed form of the five-loop coefficient

    972 C5(2) = -32 P5(2) + 56 log2 P4(2) - 36 Q2^2 + (240 log^2 2 + 596 G) Q2 - 1024 G^2 + 449 zeta(3) log2 - 80 log^4 2,
    C5(2) = -38.83364589622536055293698...

The identities are proved in note Sections 18.6 and 18.7 (package `../LRI_C5_d2_proof`). This package supplies two
things:
- the 70-digit numerical confirmation that the note quotes (residuals 4.5e-69 and 2.0e-70, record `confirm_dps70.json`);
- three further proofs (`proof/`), which the note cites.

##### What it is

- **Discovery (top level; Claude Code session C62d, 2026-10-01/02).**
  - Exact square-lattice factorization at q = 1/2: L2 becomes 48 products of 21 single sums, K2 81 products of 27
    single sequences (`factor_L2.py`, `factor_K2.py`, giving `L2_factorized.json`, `K2_factorized.json`).
  - The single sums by a robust Euler-Maclaurin summation (`emsum.py`).
  - The strip limit theta -> 0 for the K2 series (`eval_K2.py`).
  - All identities at once (`parallel_eval.py`). It ran at 70 digits on one 64-core node of the symmetry cluster (job
    567346, 1852 s), with result `confirm_dps70.json`; `confirm_dps18.json` is the same run at 18 digits.
  - `RESULT.md` describes the discovery.
  - The shipped `parallel_eval.py` is the version after that run: a per-sum cache was added 2.5 h later. The replay
    uses this cache to re-run the assembly on the stored sums.
- **Three further proofs (`proof/`; workflow `wf_6fd83950-f9b` of the same session).**
  - `L2-fourier/` and `L2-elliptic/` prove L2; `K2-parseval/` proves the spectral form of K2.
  - Each holds its prover scripts and their logs. The proofs themselves are written out in note Section 18.
    Their TeX and PDF write-ups, the synthesis `PROOF_STATUS.md` and the fragment `proof_d2.tex` are merged into the
    note and not shipped (one TeX note per direction).
  - `synth/` holds the synthesizer's exact checks.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk test` | regenerates both factorizations byte for byte; recomputes all 50 single sums and every identity at 18 digits and compares with `confirm_dps18.json`; runs the exact sympy checks of the proof fragment; evaluates the closed forms at 30 digits | 30 s wall (48 s CPU, uses all cores for 8 s); Python >= 3.9, mpmath >= 1.2.1, sympy >= 1.11 |
| `make -f public.mk replay` | the package's own assembly re-run on the 50 stored 70-digit sums (no sum recomputed); the recorded residuals; L2, K2, C5(2) from the closed forms at 80 digits in all stated forms; every decimal the note and the paper quote for them; the independent spectral record `../LRI_C5_d3/wf_d2check/d2check_results.json` (70 rows) | 4 s; one core |
| `make -f public.mk checks` | optional: the prover scripts of the three further proofs, each in a work copy, compared with their shipped logs | not timed in full: `collapse.py` 29 s, `collapse_sympy.py` 39 s, `e2check.py` 6 min on 8 cores (CLUSTER_CHECKS.md) |
| `make -f public.mk rerun70` | optional production rerun: all 50 sums at 70 digits, compared with `confirm_dps70.json` | 31 min on one 64-core node (REPRODUCE.md) |

##### Files added for the release

`public.mk`, `public/test.py`, `public/replay.py`, `public/closed_forms_d2.py` (the closed forms with mpmath),
`public/cf2common.py` (shared helpers; runs every shipped script unchanged in a work copy under `public/out/work/`
and maps the hard-coded research-tree paths to `GFF/code`), and `REVIEWS.md`. Everything else is the package as it
was on 2026-10-02.

Expected values: `../../results/closed_forms_2/closed_forms_2.json`. It holds the 70-digit L2, K2 and C5(2) and the
sha256 pins of the records.

##### Not shipped

- The verifier reports and the verifiers' numerical scripts of the three further proofs (`verify_rigor.md`,
  `verify_numeric.md`, `verify_numeric/`); see REVIEWS.md.
- LaTeX by-products, an early PSLQ script (`idfy.py`), two unused job scripts and two empty logs.

### `LRI_C5_d2_proof`

Folder: `code/LRI_C5_d2_proof/`.

#### LRI_C5_d2_proof: proofs of the d = 2 closed forms of L2 and K2

This package holds the proofs of

    L2 = -2 log2 P4(2) = -log2 (B-^2 - B+^2)/(2 pi^3),      K2 = 32 G^2 - 28 zeta(3) log2,

which make C5(2) a closed form (note Section 17.2). Claude Code session C63d wrote it on 2026-10-02 in workflow
`wf_2604cddc-2ec`: five independent proof routes, each reviewed by three lenses (REVIEWS.md).

| Route | Folder | In the note (Section 18) |
|---|---|---|
| L2 by single sums (main proof) | `L2_singlesums/` | the proof of the closed form of L2 |
| L2 by rim-spoke reflection | `L2_structural/` | the second proof, by rim-spoke reflection |
| K2 from the master path by a KLT rotation (main proof) | `K2_selberg/` | the proof of the closed form of K2 |
| K2 by the Riemann bilinear relation; proves the mixed-trace step at d = 2 | `K2_d1template/`, `K2_d1template_fix1/` | the subsection on the spectral and series forms of K2 and the mixed-trace step |
| K2 from the series, by Gauss's theorem | `K2_gauss/` | the same subsection (series form and strip limit) |

The written proofs (`L2_singlesums/L2_proof.md`, `L2_structural/PROOF_L2.md`, `K2_selberg/PROOF.md`,
`K2_d1template/proof_v2.md`, `K2_gauss/proof_K2.md`) are merged into the note and not shipped (one TeX note per
direction); the folders keep their machine checks.

Each route folder also holds the machine checks and check outputs its proof names. In particular it holds the ones
the note cites:
- `L2_singlesums/verify_symbolic.py` (l.4899);
- `K2_selberg/region_sum_matrix.py` (l.5295);
- `K2_selberg/laurent_K2_sympy.py` and `laurent_K2.wl` (l.5390-5391).

`drafter/` has the exact check of the C5(2) algebra (`check_algebra.py`) and the Mathematica end-to-end evaluation of
C5(2) (`check_series.wl`).

Four folders named `review_*` are check records: reviewers' computations (scripts and outputs, no prose) behind numbers
the note quotes in the "Checks" paragraphs of Sections 18.6 and 18.7. They keep their original names because
the merged K2 proof's checks refer to one of them.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk test` | the exact checks the note cites (verify_symbolic.py: 31 PASS, report byte-identical; region_sum_matrix.py; laurent_K2_sympy.py) and drafter/check_algebra.py, outputs equal to the shipped ones | 8 s; Python >= 3.9, sympy >= 1.11, mpmath >= 1.2.1 |
| `make -f public.mk replay` | `test` plus every check number the note quotes for the proofs (23 rows), as listed below | 11-18 s; one core |
| `make -f public.mk replay-wl` | optional: the Mathematica checks (`laurent_K2.wl`, `jgamma_series.wl`, `check_series.wl`, `checks_all.wl`), result lines compared with the shipped outputs | minutes; needs wolframscript (CLUSTER_CHECKS.md) |
| `make -f public.mk checks` | optional: the other numerical checks the proofs cite, in work copies | minutes to an hour |

What `replay` recomputes or reads:
- **Re-run from shipped inputs:**
  - the 75-digit elliptic cross-check (JSON byte-identical; note "3x10^-70");
  - the spectral tail fit behind note "2x10^-70", with `public/spec_analyze_scaled.py`;
  - the 3F2 value at tau = 3/10.
- **Read from the shipped outputs:** 10^-82, about 35 digits, 38-68 digits, 56 digits, 18-25 digits, 54 digits and
  37 digits.

##### Files added for the release

`public.mk`, `public/replay.py`, `public/replay_wl.py`, `public/spec_analyze_scaled.py`, `public/cf2common.py`,
`REVIEWS.md`. Everything else is the package as it was on 2026-10-02. The shipped scripts hard-code the research
tree's absolute paths. `public/cf2common.py` runs each one unchanged in a work copy under `public/out/work/`, with that
prefix (or its scrubbed token) mapped to `GFF/code`. Inputs from `../LRI_C5_d2_simplify` (the 70-digit record, the
factorization) and `../LRI_C5_d3/wf_d2check` (the spectral code imported by two optional checks) are read there.

`public/spec_analyze_scaled.py` is a column-scaled copy of `review_L2_structural_numerics_r0/spec_analyze.py`. The
original stops with "matrix is numerically singular" under mpmath 1.2.1, 1.3.0 and 1.4.1. The copy fits the same model
to the same data and reproduces the reviewer's residuals 1.5e-71, 1.6e-70 and 5.6e-71.

##### Not shipped

- The merge folder: scratch builds of the merged note and the 5-lens review of the merged text (9.7 MiB).
- The other review lenses and the workflow verdict file; see REVIEWS.md.
- Scratch LaTeX builds, note-insert drafts, the superseded first version `K2_d1template/PROOF_K2.md`, and exploration
  folders.

## d = 3 specialization and the generic-dimensional reduction of L_d, Z_d, K_d

### `lri_d3_reduction_update`

Folder: `code/lri_d3_reduction_update/`.

#### lri_d3_reduction_update: the d = 3 half-shift reduction of the primitive periods

This folder is package 14 of the research bundle `LRI_complete_research_bundle.zip`, shipped byte-identical without
its TeX/PDF note revisions and its `history/` drafts (see "Not shipped" below). Only `public.mk` and `public/` were added
for the public release. The bundle's own documentation is
`README_d3_reduction.md`. The scripts in `code/general_d3/` and their records in `verification/general_d3/` are the
three-dimensional part. The rest of the tree was inherited from earlier bundle revisions (general-d closed forms,
periodization, P5 hypergeometric forms) and is kept so that the package stays self-contained. No public target runs it.

##### Not shipped

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

##### What it gives

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

##### Run

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

##### Files used by the public targets

| file | role |
|---|---|
| `code/general_d3/d3_reduction.py` | evaluators of the ordinary moments, the ordered Horn sums and the period formulas |
| `code/general_d3/check_exact.py` | 25 exact SymPy identities and 288 rational Horn coefficients; writes `exact_algebra.json`, `horn_arrays.json` |
| `code/general_d3/verify_d3.py` | Q_3, P_4(3), P_5(3) at 55 and 90 digits; projections, mode identities and complex-node variants at 75 digits; six literal `mpmath.hyper` calls at 40 digits |
| `code/general_d3/check_spectral.py` | fresh real-axis Gamma-kernel integrals at 45 and 60 digits, with changed breakpoints and tail settings |
| `verification/general_d3/*.json` | the delivered records. `comparison_summary.json` (residuals, and C2–C4(3) assembled with the new periods) is not written by any shipped script. The replay recomputes its residuals from `period_values.json` and `fresh_spectral.json` |
| `archive_manifest.json` | the package's own checksum list (225 files), verified by `make test`: every shipped file matches, and only the 28 paths of `public/dropped_paths.txt` are absent |
| `public/BUNDLE_SHA256SUMS` | the bundle's SHA-256 of all 226 files, verified by `make test` in the same way (198 shipped) |

##### Overlap with other GFF packages

202 of the bundle package's 226 files are byte-identical to `lri_general_periodization_update` (shipped by the generic-d
part, trimmed to its own layer). Another 177 overlap with `lri_general_closed_update`, and 191 with
`lri_d3_matrix_update`. They are kept, so that this package is a self-contained bundle tree (less the notes above).

##### Caveats

- No interval arithmetic. The asymptotic tails are numerical accelerations, and the agreement figures are observed
  residuals.
- `code/general_special/check_A_d1.py` (inherited, not run) hard-codes a path of the sandbox in which it was generated
  (`/mnt/data/...`). It is kept byte-identical because the checksum lists bind it.

### `lri_d3_matrix_update`

Folder: `code/lri_d3_matrix_update/`.

#### lri_d3_matrix_update: rank-two (Jack α = 2) identification of the d = 3 Horn functions

This folder is package 15 of the research bundle `LRI_complete_research_bundle.zip`, shipped byte-identical without
its TeX/PDF note revisions (see "Not shipped" below). Only `public.mk` and `public/` were added for the public release.
The bundle's own documentation is `README.md`. The new
scripts of this revision are `code/rank_two_checks.py`, `code/recompute_d3_periods.py` and
`code/scalar_catalog_search.py`, and their records are in `verification/`. The rest of the tree was inherited from the
preceding revisions (it includes the d = 3 half-shift code of `GFF/code/lri_d3_reduction_update`) and is kept so that the
package stays self-contained.

##### Not shipped

Author rule (2026-10-16): one TeX note per direction. The package's rank-two appendix `proofs/rank_two_appendix.tex`
and its build `rank_two_identification.pdf` are merged into the condensed note (`GFF/note/`), Section 19, subsections
"The real rank-two hypergeometric normalization" to "Five loops: an exact three-term standard-function dictionary".
`long_range_ising_complete.tex`/`.pdf` and `general_dimension_complete.pdf` are full builds of the earlier research
note. These 5 files are named in `public/dropped_paths.txt`. No test or replay reads them. `public/BUNDLE_SHA256SUMS`
ships unchanged and still lists them; the replay accepts exactly these paths as absent and fails on any other missing
or changed file. The package's own `README.md` still names the notes.

##### What it gives

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

##### Run

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

##### Files used by the public targets

| file | role |
|---|---|
| `code/rank_two_checks.py` | hook-product weights, wheel and five-loop partition coefficients, the matrix Kummer fixed point, interior partial sums; writes the record named on its command line |
| `code/recompute_d3_periods.py` | imports `code/general_d3/d3_reduction.py` of this tree; writes `verification/fresh_primitive_values_rerun.json` |
| `code/scalar_catalog_search.py` | reads `verification/fresh100_input.json`, writes `verification/scalar_catalog_search.json` |
| `verification/rank_two_checks.json`, `fresh_primitive_values.json`, `scalar_catalog_search.json` | the delivered records |
| `public/BUNDLE_SHA256SUMS` | the bundle's SHA-256 of all 207 files, verified by `make test` (the package has no list of its own): every shipped file matches, and only the 5 paths of `public/dropped_paths.txt` are absent |

##### Overlap with other GFF packages

177 of the bundle package's 207 files are byte-identical to `lri_general_periodization_update`, and 191 to
`lri_d3_reduction_update`. They are kept, so that this package is a self-contained bundle tree (less the notes above).

`GFF/code/LRI_C5_d3/assemble_c5_d3.py` reads `../lri_d3_matrix_update/code/general_special/coefficient_values_new.json`
(the archived 11-digit nonprimitive master values). This folder must therefore keep its name, sit next to `LRI_C5_d3`
under `GFF/code/`, and keep that file.

##### Caveats

- The partial-sum comparisons are finite truncations at 90 digits, not enclosures. The coefficientwise identities are
  exact.
- `code/general_special/check_A_d1.py` (inherited, not run) hard-codes a path of the sandbox in which it was generated
  (`/mnt/data/...`).

### `LRI_C5_general_d`

Folder: `code/LRI_C5_general_d/`.

#### LRI_C5_general_d: the nonprimitive masters 𝓛_d, Z_d and 𝒦_d at generic dimension

This package holds the work behind Sections 20 and 21 of the note. The five-loop coefficient (gs:C5) needs three
nonprimitive masters:

    46656 C5(d) = −1536[P5 + 𝒦_d] + 384A P4 − 576 𝓛_d − 1728 Q² + 720A²Q + 1008QR + 7152 Z_d − …

Here 𝓛_d and Z_d are rim jets of the balanced four- and three-wheel graphs. The note's Section 17 expresses them through
244 and 318 six-variable Horn values.

**Section 20 (session C62d)** extends the finite periodization to a general rim exponent b and proves the top-mode theorem:
the top Fourier modes of every product of balanced kernels vanish, in every dimension. With these two results:

- 𝓛_d becomes a three-node sample of five two-variable Horn functions at unit argument, plus one derivative combination 𝔇_L;
- Z_d needs two ₇F₆(1) values and three Horn values, with their first and second b-derivatives;
- C5(d) is written in these terms for 2/3 < d < 4;
- at d = 1 and 2 the formulas reduce to the known closed forms, and at d = 3 they reduce to the constants of LRI_C5_d3.

**End to end, the generic route reproduces**, with P5(d) and 𝒦_d:

| d | C5(d) | agreement |
|---|---|---|
| 1 | −731.139476624539825853869126582527231 | 3·10⁻³⁴ |
| 2 | −38.8336458962253605529369824675329232 | 2·10⁻⁵⁰ |
| 3 | −5.850351420751327229217944230497744300111 | 5·10⁻⁴⁵ |

**Section 21 (K_general/, session C63d)** treats 𝒦_d: a polygamma part plus one Laurent coefficient r₃ of a three-node
sample, or one two-fold Mellin–Barnes integral; 𝒦_d is given to 100 digits at eight values of d.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk test` | the package's own quick checks: jet engine, closed-form coefficients of the 𝓛_d formula vs sympy, the sympy derivations, P4/𝓛_d at 20 digits and Z_d at 30 digits against closed forms and references, the product-form top-mode check (12 checks) | about 90 s, one core; Python ≥ 3.10, mpmath, sympy |
| `make -f public.mk replay` | Section 20: every number the note quotes for this package recomputed from the records at its printed digits, the hashes of the records and of the pinned code, the quoted TeX against the note, and a fast recompute (C5(1..3) end to end, three-node 𝒦_d, d = 3 dictionary, d = 1, 2 identities, the 𝔇_L identity, top-mode summaries), 115 checks. Section 21 (C63d): every quoted 𝒦_d number, 70 checks | about 45 s, one core |
| `make -f public.mk replay-records` | the record part only, plus the 𝒦_d replay | a few seconds |
| `make -f public.mk smoke-Kd` | the 𝒦_d replay plus the position-space code at 40 digits (C63d) | about 15 s; python-flint |
| `make -f public.mk replay-full` | recomputes the Section 20 records themselves: 60-digit samples, five-Horn and two-node codes at 50–90 digits, the C5 assembly at 8 dimensions, the pole-node check; compares each with the shipped record | about 1 core-hour; a cluster node (CLUSTER_CHECKS.md) |

The independent spectral references and the top-mode probes can be rerun from their scripts (about 170 core-hours). They
are described in REPRODUCE.md and are not a make target.

##### Files

**Added for the release** (overlay, new files only):

- `public.mk`;
- `public/replay.py` and `public/replay_full.py`;
- `public/run_tests.py`;
- `public/check_DL_Phat.py`, which recomputes the d = 3 identity of Section 20.4. The 2026-10-03 run of that check left
  no record.
- `public/e2e_k3_public.py`, a path-fixed copy of `review/joint/numerics-end-to-end/e2e_k3.py`;
- `public/replay_K_d.py` and `public/expected_K_d.json` (C63d);
- `REVIEWS.md`;

Everything else is the package as it was on 2026-10-03.

**Expected values:** `GFF/results/closed_forms_general/reduction_d/expected.json`.

**Not shipped, merged into the note (one TeX note per direction):** the derivations
`foundation/general_b_periodization.tex` (with `validation_section.tex`), `L/L_general_d.tex` (with `tables.tex` and
`cfd_table.tex`), `Z/Z_general_d.tex` (with `z_validation.tex`) and their PDFs, and `K_general/note_fragment/K_d_fragment.tex`,
`growth/PROOF.md` and `topmode/PROOF.md`. Their substance is in note Sections 20 and 21. The scripts that wrote the table
fragments (`make_tables.py`) ship and regenerate them.

**Shipped as cited records:**

- the scripts and results in `specialize/`, `L/`, `Z/`, `foundation/`;
- the review records `review/VERIFICATION.md` and `review/lemmaG-proof/review.json`. Both are model-written check
  reports that the note text cites.
- the review check code: `review/{lemmaG-numeric,topmode-numeric,foundation-rigor,L-rigor,Z-rigor,formula-from-text}/`,
  `review/joint/{numerics-end-to-end,status-consistency,conventions}/`;
- `references/reference_values.json` and the code that produced it (`refvals/`, C63d);
- C63d's `K_general/` whitelist: proofs, records and check scripts.

**Not shipped:**

- `general_d.tex`: the fragment that became note Section 20, identical to it in every non-comment line;
- `draft/` (previews, backups);
- `merge/`: the one-time merge into the note, which is git now;
- `lemmaG_statement.md`, `REFERENCES_PATH.txt`;
- `specialize/gdr_test.*` (old test build);
- the raw reviewer outputs (`review/reviews_raw.json`, `review/joint/joint_reviews_raw.json`) and the joint review's
  synthesized report `JOINT_REVIEW.md`; these are summarized in REVIEWS.md;
- the fix-check record and the merge trials;
- TeX build products;
- the parts of `K_general/` outside C63d's whitelist: superseded fragments, verifier folders, review transcripts.

**Absolute paths.** The scripts with absolute paths that are not used by any target are listed in REPRODUCE.md. The job
scripts (`*.slurm`, `*.sbatch`) name the symmetry cluster and are kept as documentation; they are scrubbed in the public
copy.

### `LRI_C5_d3`

Folder: `code/LRI_C5_d3/`.

#### LRI_C5_d3: the five-loop coefficient C5(3) and the d = 3 nonprimitive masters

This package evaluates the fifth-order coefficient of the ε expansion of Δ_ε at d = 3, C5(3), from the general-dimension
formula of the note (gs:C5, note Section 1.1) with the d = 3 values of its masters. It also reduces two of the three
nonprimitive masters, L3 and Z3, to parameter derivatives of the primitive two-variable Horn functions, and gives the third,
K3, to 430 digits.
The physics and the proofs are in the note (`GFF/note/`), Sections 1.1, 19.8, 20.4 and 21.8. The package's own `README.md` and `WORKFLOW_RESULT.md` are kept as written on
2026-10-02. This file (`public/README.md`) describes what the public copy contains.

##### Results

| quantity | value | status | record |
|---|---|---|---|
| C5(3) | −5.8503514207513272292179442304977443001109973463783… (50 digits) | exact in the six masters; numerical value | `c5_value.json`, `WORKFLOW_RESULT.md` |
| C4(3) | 1.2280635453276230799666561680749… | exact in Q3, P4(3) | recomputed by `make replay` |
| K3 | 1.14859464952717933655664631081067318763… (430 digits) | no closed form known; no relation in the bases tried | `wf_K3/K3_value.json` |
| L3 | −62.7105849683876693472961734335348… (about 158 digits) | reduced to 𝔡_H, 𝔡_a (derived, not a written proof) | `wf_L3/L3_final_values.json` |
| Z3 | 8.82092489306009248553686732817408… (about 250 digits) | reduced to 𝔱₃''(3/2) (derived, not a written proof) | `wf_Z3/Z3_values.json` |
| 𝔡_H, 𝔡_a | 2539.52445251775601935…, 11.38885029910005086619… | new derivative constants | `wf_L3/L3_final_values.json` |

The d = 3 form used everywhere is

    46656 C5(3) = −1536[P5(3) + N3] + 384 A P4(3) − 1728 Q3² + (720A² + 336π² − 4032) Q3 + S(A),
    S(A) = −15A⁴ + (360 − 30π²)A² + (828π³ − 1728 − 21456 ζ(3))A − 83π⁴ + 312π² + 5328,
    N3 = K3 + (3/8) L3 − (149/32) Z3,   A = 2 + 4 log 2 − π.

Q3, P4(3) and P5(3) are the proved rank-two forms of note Section 19; their values come from the research bundle's
package `lri_d3_reduction_update`, of which `inputs/general_d3/` is a byte-identical copy (code and three records). That
package is exported separately as `GFF/code/lri_d3_reduction_update`.

Accuracy. The digits of C5(3) are limited by P5(3), whose independent confirmation reaches about 10⁻⁵³. The other inputs
are good to about 10⁻⁸⁰. The digits of K3, L3 and Z3 rest on two independent evaluations each:
- K3: two Arb runs of the residue series agree to 2.5 × 10⁻⁴³³, and the 100-digit position-space value of `LRI_C5_general_d` agrees to 3.6 × 10⁻¹⁰⁰.
- L3: two Cauchy circles agree to all 165 stored digits.
- Z3: two circles agree to 8.6 × 10⁻²⁵⁴.
- All three agree with independent spectral runs (runs A and B at 43 digits, run C at about 96 digits).

None of these figures is an interval bound.

Status, as in the note (20.8, 21.11) and `WORKFLOW_RESULT.md`. The reduced forms of L3 and Z3 rest on general-b half-shift
steps that are derived, not written out as proofs, and are confirmed numerically to 10⁻⁵¹ and beyond. The 430-digit K3
rests on the mixed-trace step (M) and on taking [τ²] under the trace; the position-space route uses neither. All
statements that a constant does not reduce further are integer-relation bounds in the bases tried, not proofs.

##### Layout of the public copy

```
README.md, WORKFLOW_RESULT.md   the package's own summary (2026-10-02) and the workflow result cited by the note
hp_masters_d3.py                spectral K3, L3, Z3 at 50-56 digits (runs A, B): finite spins + Stirling-Hurwitz tail, Cauchy derivatives
hp_part.py, hp_combine.py       the same split into one Cauchy circle per job (run C, 110 digits) and their combination
pslq_d3.py                      masters_d3.json (43 established digits from runs A and B) and the integer-relation tests (pslq_d3.log)
compute_c5.py                   c5_value.json: C5(3) from masters_d3.json and the period values
assemble_c5_d3.py               the symbolic d = 3 assembly (needs the research bundle's paths; see REPRODUCE.md)
run_A_dps50.json, run_B_dps56.json, run_C_{b,t,combined}.json, masters_d3.json, c5_value.json, pslq_d3.log
inputs/general_d3/              d3_reduction.py, check_exact.py, verify_d3.py, check_spectral.py; period_values.json,
                                horn_arrays.json, identities.json (byte-identical to lri_d3_reduction_update)
wf_K3/                          K3: k3flint.py (Arb residue series), runs hp1-hp4, K3_value.json (430 digits), K3_results.json,
                                the integer-relation battery (final_battery.py, bases.py, consts.py, lvals.py, irel.py, pslq_K3_*)
                                and the agent's exploratory scripts, kept whole because the note cites the folder
wf_L3/                          L3: pieces.py + gen3.py (Cauchy circles pA/pB at 170 digits), load.py, final_form.py, tdform.py,
                                L3_final_values.json (+ runB), the lattice-reduction battery (battery*.py, lllrel.py, *_dig155.json);
                                kept whole (cited as a folder), with its Slurm script and logs
wf_Z3/                          Z3: zcircle.py + zb.py (circles circA2/circB2 at 260/270 digits), derive.py, derived_circ*.json,
                                Z3_values.json, hp_periods.py + perA/perB.json, the PSLQ battery (pslq_z3.py, pslq_z3_results.json),
                                the d = 4 side check z4check.py
wf_d2check/                     an independent spectral check of the d = 2 closed forms of L2 and K2 (note 17.2), read by
                                LRI_C5_general_d; kept whole
wf_V_L3_b4/, wf_Z3_gamma_verify/  the verifier checks cited by note 20.8: c41(b) = 2 a4(b) b4(b) away from b = 3/2, and the
                                Gamma form of the zero-mode amplitude (also at complex b); each script has an absolute
                                sys.path line to edit before a rerun
public.mk, public/              added for the public release: test, replay, smoke targets, their scripts, this README,
                                REPRODUCE.md, Slurm templates (public/slurm/)
```

`LRI_C5_general_d` reads `wf_K3/K3_value.json`, `wf_L3/L3_final_values.json`, `wf_Z3/Z3_values.json` and `wf_d2check/` through
sibling paths (`../LRI_C5_d3/...`). The two packages must therefore sit side by side under `GFF/code/`.

##### Targets (run from this folder)

| target | what | time, node |
|---|---|---|
| `make -f public.mk test` | `inputs/general_d3/check_exact.py` (25 exact identities, 288 Horn coefficients) in a copy, regenerated `horn_arrays.json` compared byte for byte; SymPy check of the d = 3 specialization of gs:C5 and of C4(3) | 2 s, any machine |
| `make -f public.mk replay` | reruns the package's scripts on the shipped records (pslq_d3.py, compute_c5.py, hp_combine.py, wf_L3/final_form.py and tdform.py, wf_Z3/derive.py, wf_d2check/combine_d2.py) and compares their outputs byte for byte; recomputes every quoted number of `../../results/closed_forms_3/LRI_C5_d3_quoted.json`; checks the printed formulas and the accuracy statements. Table: `.work/replay/REPLAY_c5_d3.md` | 4 s, one core |
| `make -f public.mk smoke` | fresh Q3, P4(3), P5(3) at 90 digits and K3 to about 110 digits (Arb), compared with the stored values | 15 s, one core |

Requirements: Python ≥ 3.8 with mpmath (1.3.0 tested) and SymPy; python-flint for `smoke` and for the K3 and lattice
batteries. The production runs (about 120 core-hours) are described in `public/REPRODUCE.md`.

##### Not in the public copy

- The 43-digit write-up `C5_d3.tex`/`.pdf` (superseded the same day by `WORKFLOW_RESULT.md` and note 19.8), the root Slurm
  wrappers and logs, `run_dps30.json`, and the raw workflow output `workflow_result_raw.json`. The package `README.md`
  still names some of these.
- The other 38 verifier workspaces of the workflow (`wf_v*`, `wf_*verify*`, `wf_spur*`, ...). `WORKFLOW_RESULT.md` still
  names some of them. Their verdicts are summarized in `REVIEWS.md`.
- `inputs/*.tex`. These copies of the bundle's TeX additions are now note Sections 18 and 19 (one TeX note per
  direction, author rule 2026-10-16). No script reads them. `public/dropped_paths.txt` names them with `C5_d3.tex`/`.pdf`.

Records are released byte-identical. The shipped `wf_*` folders contain Slurm scripts and logs that name the cluster, its
partition and compute nodes. No checksum list or manifest binds any file of this package.

## C6(1) and its analytic representation

### `LRI_C6_1D_HPC`

Folder: `code/LRI_C6_1D_HPC/`.

#### C6(1) from exact all-graph sums (`GFF/code/LRI_C6_1D_HPC`)

**Result (FINAL): C6(1) = 14331.68703277 ± 0.00000049**, i.e. 14331.6870328(5), for the one-dimensional long-range
Ising model with ε = 2s − 1 and Δ_E = ½ − ε/6 + Σ_{n≥2} C_n(1) εⁿ (condensed note, Sections 1, 1.2 and 22).

- The value is the mean of the two infrared cutoffs (maxgap, span) at quadrature degree N* = 22. Every six-loop
  term is summed exactly: 2,137,415 nonzero-weight graphs × 360 reversal classes × all (N+1)⁵ Chebyshev nodes, at
  N = 6, 8, …, 22. No Monte Carlo enters.
- The ± is the pre-registered empirical convergence-and-rounding allowance U (PLAN.md Sec 4.5). It is dominated by
  floating-point rounding at N = 22 (U_round = 3.5e-7). It is **not** a rigorous bound, and not a bound on the
  omitted orders of the ε series.
- The degree sequence stopped by rule (a), convergence to the floating-point floor.
- It supersedes the Monte Carlo value 14331.8 ± 0.5 (`lri_C6_numerical_update`, not included in the public
  repository). The finite special-function representation of Section 1.2 (`GFF/code/C6_research_note`) lies
  1.0e-8 below the unrounded value 14331.68703276838.

##### Where things are

| Path | Content |
|---|---|
| `GFF/code/LRI_C6_1D_HPC/` | The package at git commit `cef6fa7`, as it ran (see PROVENANCE): engine `src/c6sum.cpp`, tools, tests, symmetry Slurm scripts `cluster/`, and the part of `reference/` that the tools read |
| `GFF/code/LRI_C6_1D_HPC/public.mk`, `public/` | Public targets and scripts (added for the release) |
| `GFF/results/C6_1/` | Final records, byte-identical: `C6_final.json`, `assembled.json`, `rounding.json`, `decisions/`, `validation/`, `weights_manifest.json`, `resources_N22.json`, `C7_crosscheck.json`, `lower_amplitude_precision/`, `REPORT.md`, and the pre-registered plan `PLAN.md` |
| `GFF/data/C6_1/levels/` | The 62 merged level records (per-sector values and totals) |
| `GFF/data/C6_1/runs/` | The 84 engine output files the levels were merged from |
| `GFF/data/C6_1/analysis/` | Resource records of the stopping decisions at N* = 16, 18, 20 |

`GFF/results/C6_1/analytic/` belongs to the analytic representation (another package).

##### Quick start (from `GFF/code/LRI_C6_1D_HPC`)

```sh
make -f public.mk test      # about 10 s: package tests + every hash binding
make -f public.mk replay    # about 40 s: regenerate the records bitwise and check every quoted number
```

Both need Python 3.10+ with mpmath, numpy and sympy (`public/requirements.txt`), run on one core, and write only
to `.work/`. The table is in `.work/replay_table.txt`. Expected result on the authors' Mac: `replay` gives 124 PASS,
0 FAIL, 0 SKIP and 1 FLAG.

- **FLAG** marks one place where the condensed note's wording disagrees with the records. Note Sec 22.4 says
  successive five-loop changes are below 1e-11 from M = 24 on; the records give up to 4.35e-9, which is U5/2. The
  record is authoritative.
- **SKIP** rows appear when `C7_final.json` of `LRI_C7_HPC` is not found. It is searched at
  `../../results/C7_1/` and `../LRI_C7_HPC/results/2026-09_expanse_v2/`; set `C7_FINAL=<path>` to point elsewhere.

On x86-64 Linux there are two more targets:
- `make -f public.mk smoke` (1–3 min, g++ ≥ 11 with OpenMP) builds the engines and reruns the five-loop degree-12
  levels.
- `make -f public.mk rerun-lower` (about 30 s) repeats the RR-001 precision check of the lower-loop amplitudes.

The production rerun (≈ 45 node-hours on 64-core nodes) is in `REPRODUCE.md`.

##### Decisions you must not make

These are fixed by the pre-registration (`GFF/results/C6_1/PLAN.md` Sec 4.5, implemented in `tools/analyze.py`):
- the estimator, the mean of the two cutoffs at the last computed degree N*;
- the allowance formula and its six terms;
- ρ(N), its calibration factor and the 36-sector subset;
- the stopping rule (a)–(d), and N ≥ 16 unconditional;
- the validation gates V1–V11 and their tolerances.

Quote the headline ± U at N* = 22. Do not extrapolate (the Aitken and geometric-tail values in `C6_final.json`
are diagnostics). Any rerun needs a fresh campaign directory and a fresh validation attempt.

##### Caveats

- **The allowance is empirical.** ρ is a perturbation proxy (±1 ulp on a 36-sector subset, scaled to 360 sectors).
  It is calibrated in binary64 against extended precision, not against a higher-precision truth.
- **The L2–L4 inputs are inherited.** Their amplitudes are the degree-28 values of the original package. Their
  rounding was estimated by a float64-versus-long-double rerun (RR-001) and does not change U.
- **The C7 cross-check is conditional.** The C7 package's six-loop by-product agrees only after a model-dependent
  tail. Its stages are +2.46σ at degree 6, +0.97σ after the measured degree-7 step and −0.22σ with the tail.
- **Shared framework.** The errors here do not cover mistakes in the graph and renormalization framework that
  this calculation shares with the other packages.

### `C6_research_note`

Folder: `code/C6_research_note/`.

#### C6(1): finite special-function representation (`GFF/code/C6_research_note`)

**Status: FINAL as the reported value of C6(1)** (condensed note, Sections 1, 1.2, 22.9). The analytic route is
**conditional**: it starts from a reduced analytic expression for the six-loop coefficient that was derived outside
the package (eq. (c6:reduced) of the note, including two restored Laurent coefficients), and some conversions rest on
identities supplied with that input. The independent all-graph sum of `LRI_C6_1D_HPC` does not use the reduced
expression and agrees to 1.0e-8, which confirms it numerically; it is not a proof.

    C6(1) = 14331.68703275805432044546325524621711831732...

The value is a finite formula in nine values: Ls3(pi/2), Cl_{2,1,2}(pi/2), four Meijer G values at unit argument and
three bivariate H values (two-fold Mellin-Barnes integrals) that carry the wheel sum W0, the seventh-sector sum M7 and
the primitive pairing P_a. "Nine" describes the packaging, not a count of independent constants; no reduction of W0,
M7 or P_a to standard constants is known (the package's PSLQ search in three bases found none).

##### What is shipped

| Path | What | Size |
|---|---|---|
| `GFF/code/C6_research_note/` | the delivered package, byte for byte, minus 25 historical stage folders and 9 run records (`public/dropped_paths.txt`) | 614 files, 9.97 MB |
| `GFF/code/C6_research_note/public.mk`, `public/` | public targets and the verifier (new files) | 5 files, 38 kB |
| `GFF/code/LRI_C6_closed_form_review/` | the independent review: `REVIEW.md` and `checks/` (scripts and recorded outputs) | 95 files, 0.19 MB |
| `GFF/code/LRI_C6_closed_form_review/public.mk`, `public/` | public targets, verifier, rerun driver (new files) | 5 files, 21 kB |
| `GFF/results/C6_1/analytic/quoted_numbers.json` | the numbers the note quotes, as comparison targets | 3 kB |

Inside the package: `note/C6_progress_note.tex` and `.pdf` (28-page standalone note), `outputs/reassembly.json`
(110-digit reassembly, the eight sector blocks, the nine values), `outputs/rerun/complete_refined/` (the exact dyadic
interval certificate, 1280 bits, width 1.18e-145), `outputs/rerun/<task>/` (the 22 run records), `code/reproduce_final.py`
(task runner), `code/make_outputs.py` (reassembly), `code/stages/` (17 stage folders), `inputs/` (the supplied reduced
setup, source snapshots and canonical formula files), `provenance/`, `MANIFEST.sha256`.

The outputs stay inside the package tree: `MANIFEST.sha256` binds them at their relative paths and `make_outputs.py`
reads them from there, so `GFF/results/C6_1/analytic/` holds only the quoted-number file.

##### Targets

From `GFF/code/C6_research_note/` (`GFF/Makefile` runs `make -C code/<pkg> -f public.mk <target>`):

| Target | Does | Runtime, node |
|---|---|---|
| `test` | `MANIFEST.sha256` (shipped lines bitwise; absent lines exactly the dropped paths), `provenance/source_manifest.json` origin hashes, stage-local checksum lists, the 22 run records and summaries, note build hashes and the 22 protected equations; then 3 exact stage tasks in a scratch copy | seconds, any machine |
| `replay` | `make_outputs.py` rerun from the shipped records and compared with the shipped reassembly, tables and canonical files; every quoted number recomputed (value, sector table, interval certificate, graph-sum comparison, repair, PSLQ rerun) | seconds, any machine |
| `rerun-final` | fresh run of the 22 final-method tasks (no `--resume`), reassembly, comparison with the shipped records | 2-4 min, 1 core (personal desktop) |
| `note` | three pdflatex passes in a scratch copy | about 5 s, needs TeX Live |

From `GFF/code/LRI_C6_closed_form_review/`: `test` (seconds), `replay` (seconds: the review's agreements from its
recorded outputs, plus `checks/c6_repair.py`), `rerun` (all 49 check commands afresh, 10-25 min on one core of pi).

Each target prints a PASS/FAIL table and writes it to `.work/<target>_report.txt` (and `.json`); exit status 1 on FAIL.
Nothing in the shipped trees is written. Add `.work/` to the repository's `.gitignore`.

##### Do not

- run the package's own commands (`python code/reproduce_final.py`, `python code/make_outputs.py`,
  `python code/build_note.py`) in the shipped tree: they rewrite `outputs/`, `inputs/canonical/` and `note/*.pdf`,
  which `MANIFEST.sha256` binds. The public targets run them in copies.
- add the source repair again: `E` already contains the restored coefficients R_{147,-3} = R_{148,-3} = 2/5.
- read `delta_n` as a Kronecker delta (it is a trigamma difference), or confuse `Wcentral` (from n = 1) with `W0`
  (from n = 0).

### `LRI_C6_closed_form_review`

Folder: `code/LRI_C6_closed_form_review/`.

_no separate text._

## Finite kernels, power compensation, C6(2) and C6(3)

### `lri_C6_d2_complete_update`

Folder: `code/lri_C6_d2_complete_update/`.

#### lri_C6_d2_complete_update: the analytic power-sector compensation of C6(2)

This folder is a subset of package 21 of the research archive `LRI_complete_research_bundle.zip`, shipped as delivered.
It holds the one ingredient of the reported two-dimensional sixth-order coefficient that the C6(2) package does not
compute, and the audits of the finite-scheme construction that note Sections 24 and 25 cite.

##### What it is

The 2026 C6(2) production (`GFF/code/LRI_C6_D2_HPC`, `GFF/results/C6_2`) integrates the power-free finite-scheme kernels
and adds no power term. That is justified by the exact bookkeeping identity of note Sec 24.3, C6^full(2) =
C6^power-free(2) + Delta_p. Delta_p is evaluated here from the minimal-subtraction counterterms of every
power-containing graph:
- a Gamma-reducible sector in exact arithmetic (Sec 24.1);
- a coordinate-space Riesz/Selberg closure and a split-contour kite formula (Sec 24.2);
- two sunset contractions (Sec 24.3).

The result is Delta_p = −8.02e-34 and 6.91e-47 in two Cauchy settings, numerically zero. The explicit power-sector
integration of the C7(2) package confirms it at the 1e-3 level: (3.3 ± 11.8)e-4 at sixth order, note Sec 28.7.

The folder also holds:
- the two-loop finite-MOM jets that the C6(2) assembly uses as input (Sec 25.3);
- the exact-rational fixed-point and Lagrange checks (Sec 25.3);
- the records of the forest-identity and kernel-map checks (Secs 25.1–25.2).

The other inputs of the C6(2) production (forest kernels, rates, the fixed-point map) were derived in this and the
preceding bundle packages. They ship byte-identical inside `GFF/code/LRI_C6_D2_HPC/reference/`, so the three earlier
packages (primitive, local subtraction, two-forest) are not part of the repository.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk test` | binds the shipped files and the expected records to the package's own `SHA256SUMS.json`, reruns the two-loop jets, the 192 fixed-point checks and the kite normalization checks, and compares each output with its record | about 3 s; any machine with Python ≥ 3.8 and mpmath, sympy, networkx; no compiler |
| `make -f public.mk replay` | reruns every delivered check script on the saved counterterms in a copy (`public/out/work/`): Delta_p in both Cauchy settings, the 2699-coefficient audit, the exact Gamma sector, the KLT tests, the two-loop jets and the fixed-point checks. It compares every output field with `GFF/results/C6_2/power_compensation/`, checks every number the note quotes from these records at its printed digits, and ties Delta_p to the C6(2) and C7(2) results and to the C6(2) package's two-loop input (64 rows) | about 5 s; same; 64 PASS on macOS (two stacks) and on symmetry |
| `make -f public.mk regen` | regenerates the counterterms of all power-containing graphs from the classified graph inventory (Gamma sector at 90 digits and exactly, coordinate closure, kite extension in both settings) with the shipped kite cache, then recomputes Delta_p, and compares each record | about 4 min; 4 processes; 20/20 PASS, string-identical, on symmetry |
| `make -f public.mk regen-cold` | the same with the kite cache deleted, so the 164 kite Taylor jets are recomputed from the split-contour formula | about 6-7 min on symmetry (the two cold kite steps took 108 s and 148 s); 4 processes (see CLUSTER_CHECKS.md) |

All outputs go to `public/out/` (`replay.json`, `test.json`, `regen.json` with every row and the library versions).

##### Files

- **Added for the public release:** `public.mk`, `public/{common,test,replay,regen}.py`, `REVIEWS.md`.
- **Shipped as delivered (192 files, 4.6 MiB):** `README.md` and `SHA256SUMS.json` of the package (both describe the whole
  package; the README's reassembly and rerun commands refer to files that are not shipped). Under `reproduction/`:
  - the counterterm chain: `power_cancellation.py`, `audit_analytic_extension.py`, `position_ms.py`,
    `position_kite_leaf_ms.py`, `scaleless_leaf.py`, `kite_klt_fast.py`, `hyper3_fast.py`;
  - the check scripts: `klt_checks.py` with `master_symmetry.py` and `position_reduction.json`, `fresh_two_loop_mom.py`,
    `check_mom_lagrange.py`;
  - the saved counterterms `position_kite_leaf_ms_{32_45_.02,48_55_.016}.json` and `position_ms_results.json`;
  - `kite_cache/` (164 files) and `requirements.txt`;
  - from the nested copy of the two-forest package: `classified_inventory.json`, `verification/{reference_periods,
    C6_d2_continuation_result}.json`, `analytic/code/{sp_classify,sp_ms,sp_exact,check_gamma_coverage}.py` and
    `analytic/verification/{sp_exact,sp_ms_90,two_loop_extended_reference}.json`.
- **Expected values:** `GFF/results/C6_2/power_compensation/` (10 records, package-relative paths, bound by
  `SHA256SUMS.json`).
- **Not shipped:**
  - the first complete C6(2) campaign of this package (362.2 ± 2.0, superseded): run records, samplers, allocations, rates;
  - forests that the C6(2) package carries itself;
  - the package's TeX/PDF note;
  - diagnostics;
  - the nested `data/inventory6.json`;
  - packages 18–20 of the archive.

  They remain in `LRI_complete_research_bundle.zip`.

### `lri_C6_d3_complete_update`

Folder: `code/lri_C6_d3_complete_update/`.

#### lri_C6_d3_complete_update: d = 3 power-sector compensation of C6(3) (audit subset)

This folder is a subset of package 22 of the research bundle `LRI_complete_research_bundle.zip`: 37 of its 165 files
(7.7 of 55.1 MB), all byte-identical. Only `public.mk` and `public/` were added for the public release. The bundle's own
documentation is `README.md`; it also describes files that are not shipped (see below).

##### What it gives

The six-loop coefficient C6(3) is computed in a finite (zero-momentum) scheme for the power-free graphs, plus an
analytically evaluated correction Δp for the graphs that contain a proper power-divergent subgraph. This package holds
that analytic correction and the d = 3 inputs of the finite-scheme assembly. The production value
C6(3) = 33.5754 ± 0.0005 (`GFF/code/LRI_C6_D3_HPC`, results in `GFF/results/C6_3/`) uses this compensation and does not
redo it.

The condensed note quotes, in the section "Analytic power-sector compensation at d = 2, 3":
- the sunset factor M_3 = −16π/15 (d3six:sunset);
- the counts of power classes: 1, 5, 31 at loops 3–5; at six loops 121 with nonzero weight and 52 with zero weight;
- the exact cancellation of the two unknown four-loop core coefficients (d3six:coreResidues,
  d3six:unknownCancellation). Two trial assignments change the residues as predicted, to better than 4 × 10⁻⁷³;
- the lower-order power pieces (d3six:lowerPower) and the assembly polynomial δR (d3six:deltaR);
- Δp,higher = −Δp,lower = 0.0736516970441648694692229455611… at 90 digits (d3six:powerNumbers). Their sum is
  −1.02 × 10⁻⁸⁹. A 75-digit run with other core assignments gives −1.94 × 10⁻⁷⁵. A stress test with arbitrary masters
  gives 1.52 × 10⁻⁶⁵.

It quotes, in the section "Finite-scheme sixth-order assembly", subsection "The changes required by dimension three":
- 660 sixth-order classes (487 power-free, 173 with a power subgraph) and 1, 5, 16, 76, 395 kernels at L = 2–6;
- the 20 Gamma logarithmic jets and 5 normalizations, checked to 2.27 × 10⁻⁵⁹ (d3six:GammaJets);
- the two-loop beta jets b_{2,0…4} (d3six:twoLoopValues);
- 256 exact fixed-point/Lagrange checks (d3six:lagrange).

These are high-precision consistency checks plus an exact proof of the core cancellation. They are not an all-orders
theorem and not interval bounds.

##### Run

From this folder (Python 3 with `pip install -r public/requirements.txt`; no compiler):

```sh
make -f public.mk test     # about 10 s: checksums, the seven light audit scripts, the shipped records against the note
make -f public.mk replay   # about 2 min on one core: also the three graph-recursion audits and analyze_power.py
```

Each target copies the package to `.work/pkg/` (git-ignored) and runs the commands of `README.md` ("Reproduce the
analytic power-target audit", "Independent numerical and algebraic checks") unchanged there:
- the three `power_ms_d3.py` runs (75 digits with core (0, 0), 90 digits with core (101, −37), and 65 digits with
  arbitrary masters Q = 7, P = 11, K = 5, Z = 13 and core (−17, 29));
- `analyze_power.py` on each;
- `check_core_propagation.py`, `check_coverage.py`, `check_unknown_core.py`, `power_assembly_polynomial.py`,
  `check_mom_d3.py`, `check_gamma_d3.py` and `two_loop_d3.py`.

In `replay` the three audits overwrite the copy's power records, so that the later scripts read the reruns. Everything is
compared with the shipped `records/` and with `../../results/C6_3/power_compensation_quoted.json`. The table goes to
`.work/REPLAY.md`, and any FAIL exits non-zero. Locally (macOS, Python 3.10.12, mpmath 1.3.0) the replay gave 68 PASS,
0 FAIL. All 931 per-graph numbers of each audit were bitwise equal to the delivered records.

##### What is shipped and what is not

Shipped:
- the nine audit scripts in `code/`;
- `vendor/` (the position-space engine and graph parser of the preceding d = 2 calculation, vendored by the package);
- `inputs/classified_inventory.json` and `inputs/forest_L2..6.txt`;
- the audit records in `records/`;
- `verification/file_checksums.json` (the package's own list, verified with ignore-missing) and `environment.json`.

Not shipped (47.4 MB):
- the first full C6(3) Monte Carlo run of this package: estimate 33.50 ± 0.6, sampling SE 0.13. It is superseded and not
  quoted by the note. Its C++ sampler, rates, allocations, batch vectors, pilots and endpoint valuations are left out;
- the run and TeX logs;
- the TeX notes (author rule 2026-10-16: one TeX note per direction): `C6_d3_complete.tex`/`.pdf` and
  `C6_d3_appendix.tex`, the d = 3 power-compensation chapter, now the condensed note's Sections 24 and 25 (d = 3 parts),
  and the snapshots `long_range_ising_complete.tex`/`.pdf` and `provenance/previous_note.tex` of the earlier full
  research note;
- the copies in `verification/` of files that are in `records/`.

`public/BUNDLE_SHA256SUMS` lists all 165 files of the bundle package. `make test` checks that every shipped file is on it
and byte-identical, and counts the 128 that are not shipped. The full tree is also tracked, byte-identical, as
`reference_d3/` in `LRI_C6_D3_HPC` at commit 1c6dfb3 (not shipped there either). Shipping the full tree here instead
needs only the removal of the entry's `keep_only` (55.1 MB, largest file 16.3 MB; the notes would then need excludes),
and the replay runs unchanged.

##### Caveats

- The two unknown core coefficients are not evaluated. They cancel exactly from the physical target. The individual MS
  sums in the audit records were obtained with trial values for them and are not physical.
- The audit uses Q_3 and P_4(3) to 38 to 39 decimals as common inputs (`code/power_ms_d3.py`); they agree with
  `GFF/code/lri_d3_reduction_update`.

### `LRI_C6_D2_HPC`

Folder: `code/LRI_C6_D2_HPC/`.

#### LRI_C6_D2_HPC: the two-dimensional sixth-order coefficient C6(2)

This package produced the value in Sections 1, 24.6 and 24.9 of the note:

    C6(2) = 362.366 +- 0.004   (estimator 362.36647176375726, sampling standard error 0.0007997307;
                                allowance = four sampling standard errors, rounded up to a multiple of 0.001)

##### What it is

A restartable HPC implementation of the finite-MOM calculation of C6 at d = 2 (epsilon = 2s - 2). It integrates the
finite forest kernels of all 5, 16, 76 and 395 nonzero graph classes at loops 3 to 6 with randomized Sobol nets,
carries the regulator jets, and solves the fixed-point equation for the coefficients; the two-loop input and the
analytic power-sector compensation are inherited from the earlier calculation. The production (SDSC Expanse,
28 September 2026) ran two independent campaigns of 64 replicates, 7.23e12 kernel samples, 12,535 core-hours.

The code is shipped at git commit 6aaf656, the code that ran the production (the frozen plan pins its tools). The kernel,
sampler, assembly and inputs were delivered by OpenAI GPT-6 astra (model stated by the author, 2026-10-13), in a ChatGPT session; a Claude Code
session made the package production-ready under OpenAI Codex review without changing the numerics (the production binary
is byte-identical to the build of the delivered sources). `reference/` is the earlier method-refinement calculation as
delivered (code, raw records, the superseded estimator 362.3489138 ± 0.1526445 in
`reference/verification/method_precision_results.json`); the tests build its original kernel and compare against it.
The three-dimensional package `GFF/code/LRI_C6_D3_HPC` uses this `reference/` too. The package's own `README.md`,
`docs/` and `CHANGELOG.md` describe the code as delivered and made ready; links there to `benchmarks/` and to review
folders point to material not in the release.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk test` | build + the package's `make test`: archived assembly, byte-identical regeneration of `inputs/`, archived net replay, 12 orchestration groups, and the native replay of all 492 kernels against the original code (normalized differences below 9e-20, equal fallback counts) | about 1 min on 8-16 cores; x86-64 Linux, g++ with OpenMP and libquadmath, Boost headers |
| `make -f public.mk test-all` | + forced binary128 and 300-digit tiers, 516 independent Kirchhoff point checks, the full workflow with the real worker, original binary vs the plan/run/merge pipeline | about 3 min, same node |
| `make -f public.mk test-python` | the pure-Python suites only | about 40 s CPU, any OS (numpy, scipy) |
| `make -f public.mk smoke` | a tiny campaign through plan, run, merge and assemble with the real worker (`make test-workflow`) | about 40 s, Linux node |
| `make -f public.mk replay` | recombines the 8 merged records with the production's own assembler (4,096 bootstrap resamples), compares all 257 fields of `C6_result.json`, and recomputes every number the note quotes for C6(2) (78 rows) | about 1 s; Python >= 3.10 and numpy |
| `make -f public.mk integrity` | the shipped files against the package's checksum list (ignoring files not released) and `reference/SHA256SUMS.json` | seconds |
| `make -f public.mk fetch-data` | downloads the hosted run directory from the paper's Zenodo data record (https://doi.org/10.5281/zenodo.23466766) (79 MB, 392 MiB unpacked), checks its size and sha256, and unpacks it into `../../data/C6_2/hosted/` | about 1 min plus the download |
| `make -f public.mk remerge` | after `fetch-data`: re-merges the 8 groups from the 996 hosted checkpoints with the unmodified tools (byte-identical), runs the unmodified `tools/assemble.py` and the replay on the result | about 20 s, 0.8 GB disk |

A production rerun (428 elements of 64 cores, about 12,500 core-hours) is described in REPRODUCE.md.

##### Files

- Added for the release (new files only): `public.mk`, `public/replay.py`, `public/remerge.py`, `public/integrity.py`,
  `public/fetch.py`, `public/hosted.json`, `REVIEWS.md`. Everything else is the code at 6aaf656.
- Records: `../../data/C6_2/run-20260928-m8192/` (plan, 8 configs, 8 merged records, 8 per-graph replicate tables);
  hosted: the complete run directory (checkpoints, task tables, Sobol nets; `../../data/C6_2/DATA.md`). Results:
  `../../results/C6_2/` (`C6_result.json`, `CAMPAIGN.md`, the thread-identity record). Cross-check:
  `../../results/C7_2/C7_result.json`.
- Not shipped: `benchmarks/` (timings, profiles, validation and drill logs of the release engineering) and a stray
  duplicate checksum list; `SHA256SUMS_HPC.json` still names them, and `public/integrity.py` accounts for that.
- Not shipped, merged into the note (one TeX note per direction): the TeX notes of `reference/` and of
  `reference/baseline_previous/` (methods note and appendix, complete note, previous note, templates, LaTeX build
  artifacts). Both checksum lists ship unchanged; `public/integrity.py` accepts exactly these paths (`MERGED_NOTES`) as
  absent. The rest of `baseline_previous/` ships, because the tests read it.

### `LRI_C6_D3_HPC`

Folder: `code/LRI_C6_D3_HPC/`.

#### LRI_C6_D3_HPC: the sixth-order coefficient C6(3)

This package computes C6(3), the ε⁶ coefficient of Δε(d = 3, ε) of the long-range Ising model, with ε = 2s − 3.
It integrates the finite forest kernels of all six-loop graphs by randomized quasi–Monte Carlo (RQMC) and assembles
the result with the regulator-dependent fixed-point map. The method is described in the note (`GFF/note/`), Section 26,
"The three-dimensional production of September 2026" (label `prec:d3production2026`).

**Result.** C6(3) = 33.5754 ± 0.0005.
- Estimator 33.57542664131543, sampling standard error 0.0001185495235.
- The allowance is four sampling standard errors (0.00047) rounded up to a multiple of 0.0001. This rounding step is
  Amendment 1 (2026-10-01), made after the result was known. Under the step registered before the result, 0.001, the
  allowance would be ±0.001.
- The allowance covers sampling only. It is not a rigorous bound, and it does not cover the analytic power-sector
  compensation or the graph/renormalization framework, which this package takes over from the earlier calculation
  without redoing them.

| check (pre-registered gate) | value | gate |
|---|---|---|
| campaigns a and b: 33.57562307 ± 0.00015062 and 33.57523021 ± 0.00018311 | 1.66 combined SE apart | ≤ 3 |
| bootstrap SE / covariance SE (4096 resamples) | 0.973 | within ±20% |
| distance from the previous estimate 33.5681968 ± 0.0241840 | 0.30 previous SE | ≤ 3 |
| C3, C4, C5 against their special-function values | pulls −1.69, −1.09, +0.92 | \|pull\| ≤ 4 |

An independent seventh-order calculation in d = 3 (`GFF/code/LRI_C7_D3_HPC`) gives, as a by-product,
C6(3) = 33.57387 ± 0.00198, −0.79 combined standard errors away. It shares the graph and renormalization framework.

##### What is where

| path (in `GFF/`) | content |
|---|---|
| `code/LRI_C6_D3_HPC/` | the production code: commit `1c6dfb3`, unchanged, pruned of history and evidence nobody reads |
| `code/LRI_C6_D3_HPC/public.mk`, `public/` | the public targets, the replay and verification scripts, Slurm templates (added for this release) |
| `code/LRI_C6_D2_HPC/reference/` | the archived refinement and baseline calculation that the tests and the replay read. It is shared with the C6(2) package: `make -f public.mk setup` links it as `reference/` |
| `results/C6_3/` | `CAMPAIGN.md` (log, pre-registered rule, result, Amendment 1, errata); `results_run-20260929-m8192/` with `C6_result.json`, `manifest.json` and per group `config.json`, `merged.json`, `graph_replicates.csv` |
| `data/C6_3/` | hosted, not in git (`make -f public.mk fetch-data`): `run-20260929-m8192_full.tgz`, the complete run directory with every checkpoint (74 MB) |

**`../LRI_C6_D2_HPC` must be present.** This package's `reference/` tree (148 MiB) is byte-identical to that of
`LRI_C6_D2_HPC` (the same git tree, `d4203b17…`, at both production commits), so the repository ships it once. The 75
files of it that the C6(3) tests and the replay read are listed in `public/REFERENCE_REQUIRED.txt`. The export of
`LRI_C6_D2_HPC` leaves out the TeX notes of that tree (the method notes of the earlier C6 calculations, copies of the
earlier research note, their templates and LaTeX artifacts; author rule 2026-10-16: one TeX note per direction; their
substance is in the condensed note, Section 26 and Sections 22-25). `public/dropped_paths.txt` names these 21 files, and
no test or replay reads them.

##### Quick start

```bash
cd GFF/code/LRI_C6_D3_HPC
python3 -m pip install -r requirements.txt      # Python >= 3.10
make -f public.mk replay        # ~2 s, any OS: recomputes every quoted number, PASS/FAIL table in .work/replay/
make -f public.mk test-python   # ~1-2 min, any OS: pure-Python tests and the shipped-file check
make -f public.mk test          # Linux + GCC/OpenMP/libquadmath/Boost: builds the worker, then the same plus validate.py
make -f public.mk test-all      # ~6 min on 16 cores: every test target, including the archived-stream replay
```

`replay` uses the package's own code: `tools/production.py` checks every hash binding of the records, and
`tools/assemble.py` recomputes the estimator, the covariance, the campaign values, the lower-order pulls and the
bootstrap. It then applies the reporting rule and the gates, and recomputes the superseded estimates and the archived
values that the note compares with. `REPRODUCE.md` (GFF level) lists every step; `results_map.md` maps every quoted
number to its row.

##### Changes from the production commit

None to any file of `1c6dfb3` that ships. The public copy:
- adds `public.mk` and `public/`;
- leaves out `reference/` (linked instead), most of `reference_d3/`, `provenance/`, and the benchmark and drill logs
  (`public/NOT_SHIPPED.txt` lists every file of the package checksum list that is not shipped);
- keeps `SHA256SUMS_HPC.json` verbatim. `tools/checksums.py verify` and `make check-delivery` therefore report the
  pruned files as missing; `public/verify_shipped.py` (run by `make -f public.mk test`) checks the shipped files
  against the same list and accepts exactly the documented omissions: `public/NOT_SHIPPED.txt` (including the TeX notes
  of `reference_d3/`) and `public/dropped_paths.txt` (the 21 TeX notes of the linked `reference/` tree, reported in
  one INFO line). Any other missing or changed file fails.

Reviews: `public/REVIEWS.md`.

## Full C7(1), C7(2), C7(3)

### `LRI_C7_HPC`

Folder: `code/LRI_C7_HPC/`.

#### C7(1): full seventh order of the one-dimensional long-range Ising model

This folder is the public layer of `GFF/code/LRI_C7_HPC`, the package that computed

> **C7(1) = −322550 ± 41** (estimator −322549.8888129889, sampling standard error 10.08791295; the ±41 is the output
> of a pre-registered empirical policy, not a rigorous bound). A post hoc truncation-aware assessment gives
> −322524 ± 38.
>
> The paper quotes −322550 ± 40: it rounds the allowance candidate 40.35 (four sampling standard errors) by the PDG rule. The condensed note and this package keep the pre-registered rule, which rounds it up to two significant figures, ±41.

in the convention ε = 2s − 1, Δ_ε = ½ − ε/6 + Σ C_n(1) εⁿ (condensed note, Section "Full seventh order in one
dimension"). The estimator combines 399 independent fresh-seed batches of one frozen design (SDSC Expanse, September
2026, about 2.6×10^5 core-hours) with a direct integration of the 44 seven-loop primitive classes. The records are in
`GFF/results/C7_1/` (final) and `GFF/results/C7_1/v1_46batches/` (the earlier 46-batch combination).

The package's own documentation is `../README.md` (build, campaign tools, cluster recipe), `../docs/NUMERICS.md`,
`../docs/HPC.md`, `../docs/ARCHITECTURE.md`, `../CHANGELOG.md`. `../reference/` is the inherited September 2026
calculation (graph inventory, forest arrays, the archived streams, the retained primitive input and the TeX
derivation), authenticated by `../reference/SHA256SUMS`. The delivery benchmarks cited in `../README.md` and
`../docs/PERFORMANCE.md` (`benchmarks/`) are not part of this public copy.

##### Targets (run from `GFF/code/LRI_C7_HPC`)

| Command | What it does | Needs | Time |
|---|---|---|---|
| `make -f public.mk test` | the package's own `make test`: builds `bin/c7_integrate`, then oracle, multithread/shard, malformed-input, pipeline and inventory tests | x86-64 Linux, GCC ≥ 9 with `__float128`/quadmath, OpenMP, Boost multiprecision headers (`CPPFLAGS=-I...`), Python ≥ 3.8 with numpy, scipy, mpmath | about 10–20 min on 16 cores |
| `make -f public.mk replay` | Tier 1: recomputes every quoted number from `GFF/results/C7_1` and `reference/` (214 checks; table in `.work/replay7_tier1.txt`) | Python ≥ 3.8, numpy | about 5 s, one core |
| `make -f public.mk fetch-data` | downloads the merged records (`C7_1_merged_records.tar.gz`, 338 MB) from the project's Zenodo data record ([doi:10.5281/zenodo.23466766](https://doi.org/10.5281/zenodo.23466766)), checks the sha256 in `public/data_C7_1.json` and unpacks them into `GFF/data/C7_1/`; a copy already placed there is used if its sha256 matches | network | |
| `make -f public.mk replay-full` | Tier 2: reruns the production `tools/combine.py` on the hosted records and compares with `GFF/results/C7_1` byte for byte (to 1e-12 where the platform differs in the last bits; see REPRODUCE.md) | the hosted records (0.97 GB unpacked) | about 7 min, one core, < 2 GB (Expanse, 2026-10-13: 409 s, peak 1.7 GB) |

The production rerun is documented in `REPRODUCE.md` (Slurm, placeholders, node sizes, core-hours).

###### What Tier 1 recomputes

`C7_final.json` stores, for each of its 9577 sources (24 campaigns × 399 batches, plus the primitive campaign), the
mean and covariance of the replicate values projected through the frozen affine map. From these and the map's
constant K (`reference/verification/full_affine_assembly.json`, whose SHA-256 the result records), the replay rebuilds
in the production order the estimator, its covariance and standard error (bitwise), every quadrature level and the
degree 6→7 check, the telescoped resolution sequence, the lower-order checks, the allowance candidates and the
allowance, the flag, the 399 per-batch values and the inter-batch χ², the primitive cross-check and the post hoc
truncation-aware estimate. It reruns the archived reassembly (`tools/assemble.py --original`, 1 s), checks the
inventory counts of the note from `reference/inputs`, the inherited exact checks in `reference/verification`, both
checksum lists, the batch seeds and the campaign structure. Five quantities need the raw replicate streams and are
checked only as recorded (RECORDED rows): the replicate bootstrap standard error, the half-split estimates, the
spurious-pole means, the zero-pole control terms and the uncontrolled estimator; Tier 2 recomputes them.

###### What Tier 2 substitutes

`public/replay7_full.py` imports the shipped `tools/combine.py`, `assemble.py` and `campaign.py` unchanged. Two things
are substituted in memory: the campaign verifier skips the re-reading of checkpoint and task files, which are not
hosted, but keeps every other check and requires the audit's checkpoint list to match the manifest's plan; and
`inputs/L7_coord.txt`, the only input file the combination reads, is rebuilt from `reference/inputs` after a SHA-256
check against every L7 campaign manifest. Every hosted merged stream is checked against the SHA-256 recorded in the
published `C7_final.json`.

##### Files of this folder

- `replay7.py`, `replay7_full.py`: the two replay tiers.
- `fetch_data.py`, `data_C7_1.json`: hosted-data pointer.
- `make_data_archive.py`: builds the hosted archive from a production tree (maintainer tool).
- `slurm/archive_and_replay.sbatch`: archive build plus Tier 2 on one node; `slurm/rerun_production.sh`: full rerun.
- `diff_3213ce0_to_shipped.patch`: the production workers ran commit 3213ce0; this diff (tools and tests only) is the
  whole difference to the shipped code (`patch -R -p1` from the package root restores the 3213ce0 files).
- `REPRODUCE.md`, `PROVENANCE.md`, `REVIEWS.md`, `results_map.md`, `requirements.txt`.

##### Checksums

`../SHA256SUMS` (515 lines) ships unchanged. The replay verifies it with the `results/` lines mapped to
`GFF/results/C7_1/`; 155 lines name files that are not shipped (`benchmarks/`, two v1 files). A mismatch in code,
`reference/`, the degree-7 weights or the bound result records fails; a mismatch in a documentation or provenance file
is reported as a warning. `../reference/SHA256SUMS` (286 lines) must verify completely, since `tools/assemble.py`
authenticates the archive against it.

##### Scope

The allowance is empirical. Plan criterion A5 (optimized radial quadrature no less accurate than the original,
element by element) is reported as not met: 9 of 112 replay elements are less accurate, worst 18× at 4.2e-14 relative,
about 1e-10 of the sampling noise. The degree-6 truncation, not sampling, now limits the precision; the lower orders
agree with their references only after the measured degree 6→7 step and a geometric tail (see `REVIEWS.md`).

### `LRI_C7_D2_HPC`

Folder: `code/LRI_C7_D2_HPC/`.

#### LRI_C7_D2_HPC: the full seventh-order coefficient C7(2)

This package computed the two-dimensional seventh-order thermal coefficient of note Section 28:

    C7(2) = -3876.1 +- 2.1  (epsilon = 2s - 2; estimator -3876.1260927949925, sampling SE 0.5244496691)

It integrates, at every loop from three to seven, both the power-free logarithmic forests and the mixed local-mass forests
(the power sector is measured, not set to zero), keeps the regulator jets through z^(7-L), and solves the fixed point.
The 2026 production on the symmetry cluster sampled 1,094,688,178,176 kernel evaluations in two independent campaigns of
64 replicates each. Its by-products are checks: C3-C5 against their exact values, C6 against the C6(2) production
(`GFF/results/C6_2`), and the three-loop power jet against an independent quadrature.

##### What it is

An optimized, restartable reimplementation of an earlier calculation, written by OpenAI GPT-6 astra in a ChatGPT session
(model stated by the author, 2026-10-13) and delivered on 2026-09-30. The earlier calculation (result -3950 +- 310), its graph kernels and its records
are kept unchanged under `reference/`; its method note and the progress note of its power-free campaign are merged into
note Section 28 and not shipped (one TeX note per direction). The kernel
keeps the reference addition order and the long double / binary128 tiers and replaces the 300-digit final tier by 350-digit
GMP arithmetic (`bin/c7d2_gmp`, used for the production). The package ships at git commit **fb64c47**, the code that ran
the production; the production plan pins the hashes of its planning and assembly tools, and `replay` checks them.

`reference/{LRI_C7_d2_progress,power_mass}/inputs/L*/G*.txt` (3,774 files, 290 MiB) are the d = 2 graph kernels of loops
two to seven. They are shipped once, here: the eighth-order packages (`GFF/code/LRI_C8_D2_HPC`, `GFF/code/LRI_C8_D3_HPC`)
use the same files and verify them with their own checksum lists. Do not edit them.

##### Targets (run in this folder: `make -f public.mk <target>`)

| Target | What it does | Time and node |
|---|---|---|
| `setup` | rebuilds the ten graph packs `inputs/packs/*.pack` (266 MiB, not in git) from the reference kernels and checks every pack against the SHA-256 the production pinned | about 2 s; any machine, Python 3 |
| `test-python` | `setup`, the delivery manifest and `SHA256SUMS` of all 4,405 files (the delivered verifier, run through `public/verify_delivery_public.py`, which accepts exactly the five merged notes as absent), and the delivery-verifier tests | about 10 s; any machine, Python 3.9+ |
| `test` | `test-python` and the package's own `make test`: decimal build, the optimized kernel against the original executable on a graph subset (exact), and a plan/run/merge/assemble workflow with checkpoint restart and corruption tests | about 3-5 min on one Linux x86-64 node with 4-8 cores (g++ >= 11 with OpenMP and libquadmath, Boost headers >= 1.77; Python >= 3.10, numpy, scipy) |
| `test-full` | `test` and the package's `make test-full`: the gmp backend (GMP), all 3,511 kernels against the original executable for both backends, 450-digit point checks, re-assembly of the previous result, staging | about 5-8 min, same node plus GMP |
| `replay` | recombines the production's 20 merged group records with the production's own assembly (`tools/assemble.py` of fb64c47, bootstrap included), compares all 277 fields of `C7_result.json`, recomputes every number the note quotes for C7(2) (108 rows), and re-assembles the previous calculation with `tools/reassemble_reference.py` | about 4 s; Python 3.10+ and numpy only; no compiler, no hosted data |
| `fetch-data` | prints where the hosted full run directory (640 MiB) is; only for a re-merge audit | — |

A production rerun (about 8,900 core-hours: 28 whole nodes for 6.5 h) is described in REPRODUCE.md.

##### Files added for the release (new files only)

- `public.mk`, `public/regen_packs.py`, `public/replay_c7d2.py`;
- `public/slurm/`: the node worker, merge job, planning script and queue/status helpers that ran the 2026 production
  (written by the Claude Code session that ran it; paths replaced by variables and placeholders), and an environment
  example;
- `REVIEWS.md`.

Everything else is the code as it ran (git commit fb64c47). Its own `README.md` and `docs/` describe the package as
delivered; the package `Makefile`'s `test` writes `benchmarks/validation.json`, which `public.mk` writes to `public/out/`
instead. Generated, git-ignored: `inputs/packs/`, `bin/`, `public/out/`.

Records: `GFF/data/C7_2/run1-20260930-m4096/` (frozen plan, cost model, 20 group configurations and merged records).
Results: `GFF/results/C7_2/` (`C7_result.json`, the production log `CAMPAIGN.md`, build and test evidence).

##### Not shipped

- `inputs/packs/` (rebuilt by `setup`);
- the revised package of the 2026-10-02 fix loop (commits after fb64c47 up to a55958f): a hardened job-handling layer and
  tests, reviewed by Codex, which did not run the production, refuses the 2026 run directory and leaves the numerics
  unchanged (see REVIEWS.md and PROVENANCE.md);
- the production's checkpoints, task tables, nets and per-graph tables (640 MiB; archive only, DATA.md);
- review logs and transcripts (summarized in REVIEWS.md).

### `LRI_C7_D3_HPC`

Folder: `code/LRI_C7_D3_HPC/`.

#### LRI_C7_D3_HPC: the seventh-order coefficient C7(3)

Published as `GFF/code/LRI_C7_D3_HPC/public/README.md`. The package's own `README.md` next to it is the delivered one,
unchanged.

##### What it computes

The coefficient C7 of Δ_E(3, ε) = Σ C_n(3) εⁿ, ε = 2s − 3, for the thermal operator of the long-range Ising model in
d = 3, from the finite-scheme forest kernels of loops 3 to 7 in both the power-free and the power-containing sector, by
randomized quasi-Monte Carlo. The method is condensed in Section 29 of the note (`GFF/note/`).

**Result** (production run1, symmetry cluster, 30 Sep to 1 Oct 2026):

| | value |
|---|---|
| C7(3), reported | **−220.35 ± 0.13** (allowance = 4 sampling SE rounded up to 0.01; empirical, sampling only) |
| estimator, sampling SE | −220.35448047392794, 0.0318188006 |
| power-free part, power correction | −220.3723574 ± 0.0277073, +0.0178769 ± 0.0156478 |
| previous calculation (the delivered `reference/`) | −228 ± 16 (estimator −227.6181095, SE 3.8273969); the new estimator is 1.90 of its SE away |

The by-products C3 to C6 agree with the special-function values and the C6(3) production (pulls +2.30, +1.08, +0.04,
−0.79); the two campaigns agree to 1.02 combined SE; no gate was flagged. Limits: the allowance covers sampling only;
the result shares the graph and renormalization framework with the rest of the note and does not validate it; a
quadrature-truncation effect, as found in C7(1), would lie outside it.

##### Two commits, one folder

- **The production code**: this folder is the export of git commit **4de9412** (the package as delivered on
  2026-09-30, unchanged). The run1 manifest pins `tools/{production,assemble,common,prepare_inputs}.py` by sha256, and
  `make replay` checks that the shipped files are those bytes. The production binary was built from `src/` (identical
  to `reference/src/`) with GCC 11.4 and Boost 1.77: `bin/c7d3_gmp`, sha256 635428f9….
- **The re-verification tool**: `reverify_a6ce987/` holds `tools/report.py`, `tools/assemble.py`, `tools/common.py`,
  `references/lower_order_d3.json` and run1's cost model from commit **a6ce987**, the symmetry-ready successor built and
  inspected in a Codex fix loop (approved at c71cc56; a6ce987 adds the results review's gate fix). It is a separate
  folder, not an overlay, because its `assemble.py` and `common.py` differ from the production files of the same names.
  It needs its own copy of `inputs/{manifest,two_loop,primitive_reference}.json` (byte-identical to `inputs/`). The rest
  of a6ce987 (lane mode, Slurm wrappers, its tests) is not published.
- **The public layer**: `public.mk` and `public/` (new files, Claude, 2026-10-13).

##### What is where

| path | content | in git? |
|---|---|---|
| `src/`, `tools/`, `tests/`, `slurm/`, `docs/`, `Makefile`, `requirements*.txt`, `README.md` | the delivered code and docs | yes, verbatim |
| `inputs/manifest.json`, `inventory.json`, `two_loop.json`, `gamma_d3_7.txt`, `primitive_reference.json` | the d=3 inputs; the run1 manifest pins `inputs/manifest.json` (5048b336…) | yes |
| `inputs/packs/*.pack` (10 files, 321.8 MB) | the 3,511 kernels in packed form | as `public/kernels/inputs_packs.tar.gz` (14.8 MB); `make -f public.mk setup` unpacks and verifies them |
| `reference/` | the previous calculation, byte-for-byte: its code, sources, README, verification records (result, assembly, dimension, two-loop and Gamma checks) | yes, except the three items below |
| `reference/inputs/{free,power}/L3..L7/G*.txt` | the same 3,511 kernels as single files | restored by `setup` from the packs (each checked against `inputs/inventory.json` and `SHA256SUMS`) |
| `reference/records/` (784 files, 51.6 MB) | raw streams of the previous production, pilot and control | hosted: `data/C7_3/reference_records.tar.gz` (`make -f public.mk records`) |
| `reference/reference/C7_d2_complete.tex` | a copy of the method note of the earlier d = 2 seventh-order calculation; its substance is in the condensed note, Section 28 (`GFF/note/`) | no (author rule 2026-10-16: one TeX note per direction); named in `public/dropped_paths.txt`, read by no code |
| `benchmarks/` | the 8 delivered validation records that `docs/NUMERICS.md` cites | yes; the timing, memory and profile benchmarks are not published |
| `SHA256SUMS`, `DELIVERY_MANIFEST.json` | the delivery's checksum lists, verbatim (not pruned or regenerated) | yes; `make -f public.mk checksums` verifies every present file and classifies the absent ones |
| `reverify_a6ce987/` | the re-verification tool (above) | yes |
| `public.mk`, `public/` | public targets and scripts | yes |

The production records are in `GFF/results/C7_3/` (see its `REVIEWS.md` and `results_map.md`); the complete run
directory is hosted as `GFF/data/C7_3/run1-20260930-m4096_full.tgz`.

##### Targets (`make -f public.mk <target>`, from this folder)

| target | what | needs | time |
|---|---|---|---|
| `replay` | recomputes every quoted C7(3) number from `results/C7_3` with the production assembly and the a6ce987 gates; PASS/FAIL table | Python ≥ 3.10, numpy | ~10 s, any machine |
| `test` | `setup`, then the production commit's own `make test`: builds `bin/c7d3_gmp`, `tests/validate.py` (up to 16 graphs per loop and sector against the original d=3 worker built from `reference/src`; thread and chunk independence; assembly identical to the original), `tests/workflow.py` (tiny campaigns through plan, run, restart, corruption refusal, merge, assembly) | x86-64 Linux, GCC with OpenMP and libquadmath, GMP, Boost 1.77 headers, SciPy | < 10 min on a 64-core node (validate 18 s, workflow 12 s after the builds, on AMD EPYC 7532) |
| `checksums` | verifies the tree against the delivery's checksum lists | — | seconds |
| `test-full` | the production commit's `make test-full`: every graph, 450-digit point checks, reassembly of the previous result | as `test`, plus `records` | ~3 min more (96 s, 43 s, 2 s on the same node) |
| `archived-replay` | the cited check: rerun the worker on the 168,528 archived rows | as `test`, plus `records` | 95 s at 64 threads |
| `indep-rows` | the independent mpmath re-implementation on chosen archived rows | `records`, mpmath | seconds per row |
| `reverify` | runs `reverify_a6ce987/tools/report.py` on the hosted run directory and compares with `results/C7_3/run1_report_bb9d2ca.json` | the hosted run tarball | ~1 min, 0.6 GB |
| `smoke` | re-plans run1 with its seed, flags and cost model and reruns job indices 0, 320, 192; compares with run1's checkpoints | as `test`, plus the hosted run tarball, SciPy 1.17.1 | ~3 min on 64 cores |

`fetch-data` downloads the two hosted files from the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766) and checks them. `clean` removes `.work/`, `bin/` and test output;
`distclean` also removes what `setup` and `records` restored.

##### Caveats

- Results are bit-reproducible only on the same CPU type: the worker differs across CPU types by up to 2.0e-11
  normalized, and the float64 assembly by a few ulp. The replay's tolerances allow for this.
- `src/kernel.hpp` does not compile with Boost ≥ 1.86; `public.mk` refuses such versions.
- The tests write `bin/` and `benchmarks/validation.json` (git-ignored; the shipped records in `benchmarks/` are only printed, not rewritten). Run1's nets were made with SciPy 1.17.1; a rerun with the
  same seed needs that version to reproduce the same Sobol nets.
- The delivered `tools/verify_delivery.py --strict` fails on the public tree because the bulk is restored or hosted; use
  `make -f public.mk checksums`.

## Full C8(1), C8(2), C8(3) and the independent checks

### `LRI_C8_HPC`

Folder: `code/LRI_C8_HPC/`.

#### LRI_C8_HPC: C8(1), the full eighth-order coefficient in one dimension

Thermal scaling dimension of the one-dimensional long-range Ising model,

    Delta_E = sum_n C_n(1) eps^n,  eps = 2s - 1:   C8(1) = 8059767 +- 17000  =  (8.060 +- 0.017) x 10^6.

- **Sampling error.** The sampling standard error is 4210 (bootstrap 4140).
- **Allowance.** The +-17000 is the empirical allowance of a rule fixed before production: the largest of four
  sampling errors, the refinement and check steps, the half-split shift and the loop-five degree step, rounded up to
  two significant figures. It is not a rigorous bound. The number of batches was not fixed in advance: under the
  stopping rule set first, nine batches give 8061480 +- 5300 with allowance +-22000; all fourteen planned batches
  were completed after interim results of five to eight batches had been seen (note Sec. 30.1).
- **How it is computed.** The estimator is the mean of fourteen independent production batches of one frozen design
  (498 work elements each).
  - Loops one to five are deterministic. Loops six to eight are sampled: two randomized Sobol campaigns for the
    power-free sector, and a power sector telescoped through radial degrees 1, 3, 5, 6, 7, 8, with a degree 8 to 9
    check.
  - The method and its checks are Section 30 of the note (`GFF/note/`).
- **Where the code comes from.** The code generalizes the seventh-order package `GFF/code/LRI_C7_HPC` to eight loops.

##### Layout in the public repository

| Path | Contents |
|---|---|
| `GFF/code/LRI_C8_HPC/` | the production code, verbatim at commit 1282e37 (src/, tools/, gen/, inputs8/, designs/, cluster/, tests/, validation/, docs/, PLAN.md) plus the public overlay (`public.mk`, `public/`, `REVIEWS.md`); `make -f public.mk setup` links `reference` to `../LRI_C7_HPC/reference` |
| `GFF/results/C8_1/2026-10_ext1/` | the final K = 14 result (`C8_final_A3/C8_final.json`, sha256 115d614f...), the A1 interim (`C8_A1_close/`), the records of both clusters and `REPORT.md` |
| `GFF/results/C8_1/2026-10_expanse/` | the first result, K = 4 (8066723 +- 8015, allowance 33000), with the frozen design, the batch plans, the pilot preview and `REPORT.md` |
| `GFF/data/C8_1/` | merged records of the 14 batches, the exact loop-five campaign, the affine maps, the frozen design, the 4096-point L7 test, and `inputs8/L8_coord.txt.xz` (see `DATA.md`) |

##### Commands (from `GFF/code/LRI_C8_HPC/`)

| Command | What | Time, node |
|---|---|---|
| `make -f public.mk test` | tests of the Python tooling, the pipeline and the lane runner (fake integrator) | about 7 min, 2 cores |
| `make -f public.mk replay` | reruns the three quoted combinations with the production `tools/combine8.py` and checks 122 quoted numbers (PASS/FAIL table in `.work/verify_c8.tsv`) | about 20 s, 1 core, 0.3 GB |
| `make CPPFLAGS=-I$BOOST_ROOT/include RPATH=1` | builds the integrator `bin/c8_integrate` for a production rerun (REPRODUCE) | x86-64 Linux |

Requirements: Python >= 3.8 with numpy and scipy (replay and test). A rerun also needs GCC with libquadmath and
OpenMP, Boost headers and Slurm.

##### What the replay does and does not check
- The replay recomputes, from the merged replicate streams:
  - the estimator, the covariance, the allowance candidates, the bootstrap, the half splits, the per-batch values and
    their chi-square;
  - the resolution sequence, the zero-pole controls, the pole statistics and the lower-order checks;
  - the coverage guard and the frozen-design checks.
- **Checkpoints are not re-validated.** The 83,380 checkpoint files behind the merged streams are not shipped (about
  34 GB). Their sha256 values are in every `merged/audit.json`.
- **Still checked:** the merge audit of every campaign, the sha256 of every merged stream, and the merged headers.
- **The integrals are not recomputed.** That is the production rerun.
- **Comparisons with other results** (C6(1), C7(1), HT) check consistency inside a shared framework; they do not
  validate the framework.

### `LRI_C8_D2_HPC`

Folder: `code/LRI_C8_D2_HPC/`.

#### LRI_C8_D2_HPC: the full eighth-order coefficient C8(2)

This package computes the coefficient behind Section 31 of the note and the d = 2 entry of the eighth row of its tables:

    C8(2) = 45990 +- 33  (epsilon = 2s - 2; estimator 45990.00263614446, sampling standard error 8.216820958)

The allowance +-33 is four sampling standard errors rounded up to a multiple of 1; it exceeds both half-stream deviations
(2.39). The production record quotes the estimated sampling standard error, 45990.0 +- 8.2, with the weight bounds and tail
diagnostics of Section 31.5. The C8(2) record is `../../results/C8_2/C8_final.json`.

##### What it is

The seventh-order d = 2 package (`../LRI_C7_D2_HPC`) generalized to eight loops: the same mixed local-mass forest kernel,
power-sector normalization, importance sampler, digital nets and precision policy, with sixteen propagators, regulator
jets through z^(8-L), a nine-vertex payload generator (`gen/`, whose published output is the shared inventory
`../LRI_C8_shared/inventory/inventory8_d2/`), the d-general order-8 assembly of `../LRI_C8_shared/assembly/` vendored byte for
byte in `vendor/c8_assembly/`, and an orchestration layer for Slurm clusters (lanes, merges, design, accounting, seeds).
Both sectors are integrated explicitly: C8(2) = C8^pf(2) + Delta_p C8(2), with 24,173 kernels at loops 3 to 8. The
production used the opt-in `dd+mp256` numerics profile (double-double and 77-digit tiers in front of the exact path's
binary128 and 350-digit tiers), run only by an executable whose accuracy gate passed (`docs/NUMERICS.md`).

The code is shipped at git commit 9df5b1c of branch c8. Its code is byte-identical to ba68f40, the export the pilot and the
production ran; 9df5b1c adds the evidence under `benchmarks/symmetry_2026-10-c8/` (production preparation and result,
`production/result/README.md`; the tail check, `production/tailcheck/README.md`; the pilot and its analysis,
`pilot/analysis/README.md`). The package's own `README.md`, `docs/` and `CHANGELOG.md` describe it as it was then.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk setup` | puts the C7(2) reference trees in place (hard links into `../LRI_C7_D2_HPC/reference`, every file checked against this package's `SHA256SUMS`) and rebuilds the L7 graph packs (checked against `inputs/manifest.json`) | 5 s, any machine |
| `make -f public.mk replay` | recombines the 24 merged groups of the production with the package's own assembler and combiner, compares every field of the batch result and of `C8_final.json`, and recomputes every number the note quotes for C8(2) (192 rows; 3 marked SKIP with the reason) | 10 s; Python and numpy; no compiler, no hosted data |
| `make -f public.mk test` | `setup`, then the package's `make test-python` without L8 packs (orchestration, pipeline, design, merges, vendored assembly, inputs, generator logic, profiling and numerics harnesses, native guards with the host compiler) | about 1 h (58 and 69 min in two runs on symmetry Intel nodes); Linux or macOS with a C++17 compiler, Boost and GMP headers; a CPython whose `os.urandom` calls getrandom (distribution or conda builds; `public/check_python.py` stops first otherwise, see below) |
| `make -f public.mk retest-lane-sigterm LOG=...` | only after a `test` whose single failure is the timing signature of `lane_sigterm` (see below): reruns that case once, then the 18 steps of `test-python` that make skipped | about 30 min |
| `make -f public.mk test-quick` | the steps of `test` that take under a minute each | about 2 min |
| `make -f public.mk verify-lists` | `SHA256SUMS` and `DELIVERY_MANIFEST.json` over the package (after `setup`; scrubbed files: presence only) | 5 s |
| `make -f public.mk replay-tails` | the tail table and the variance analysis from the full group tables, compared with the published ones | about 15 min, 8 GB, after `fetch-data` |
| `make -f public.mk fetch-data` | downloads the production's group tables (1.4 GB, 2.7 GB unpacked), its ledger and lane logs, and the pilot's records (90 MB) from the paper's Zenodo data record (https://doi.org/10.5281/zenodo.23466766), checks sizes and sha256, and unpacks them into `../../data/C8_2/` | a few minutes plus the download |
| `make -f public.mk jval1` | the package's cluster validation J-VAL-1 (`make test`): builds the kernels, replays C7(2) kernels bit for bit on a subset, real-worker workflow | about 40 min on a whole Linux x86-64 node, after `fetch-data` of the shared payload tars (7.8 GB) |

The production rerun (13,454 core-hours on AMD EPYC 7543 nodes) is described in REPRODUCE.md.

##### Files added for the release

`public.mk`, `public/setup.py`, `public/check_python.py`, `public/retest_lane_sigterm.py`, `public/replay.py`, `public/replay_tails.py`, `public/verify_lists.py`, `public/fetch.py`, `public/hosted.json`, `public/NOT_SHIPPED.txt`, `REVIEWS.md`, and
`public/SCRUBBED.txt` (written by the release scrub). Everything else is the code and
evidence as committed. Records: `../../data/C8_2/` (the production's plan, design bundle, merged groups); results:
`../../results/C8_2/` (C8_final.json, the pilot result, the production analysis and tail table, the tail-check summaries).

##### Not shipped

- The copies of the C7(2) reference trees under `reference/` (byte-identical to `../LRI_C7_D2_HPC/reference/`; `setup`
  restores them, except the five TeX notes of those trees, which are merged into the condensed note and shipped by
  neither package; `public/NOT_SHIPPED.txt` names them, and `setup` and `verify-lists` accept exactly these as absent) and the two L7 packs (rebuilt by `setup`). The L8 packs were never in git: `make -f public.mk setup-l8`
  builds them from the shared inventory's payload tars.
- The plan, review logs and Codex transcripts of the build (summarized in REVIEWS.md), the unused review worktrees, and the
  commits after 9df5b1c (a fix of `tools/design.py report` for production batches, which `replay-tails` works around with
  the raised caps the production analysis used, and two updates of the seed mirror).
- The campaign directories (checkpoints, tasks, logs): hosted or archived, see `../../data/C8_2/DATA.md`.
- A development check of the checkpoint fixes on a personal workstation (`benchmarks/expanse_2026-10-c8/ckpt_fix/`, 59 files): not
  cited and read by nothing; its lines are removed from `SHA256SUMS` and `DELIVERY_MANIFEST.json`, which otherwise ship as
  committed.

Known stale metadata, shipped as is because checksum lists bind it: `DELIVERY_MANIFEST.json` still carries the header of the
seventh-order package (package name, order 7, scope); its file list is current. `SHA256SUMS` and `DELIVERY_MANIFEST.json`
list the files that `setup` restores, so verify them after `setup` with `make -f public.mk verify-lists`. The release
scrubbed user names, cluster paths, node names and session ids in evidence and documentation files that no record pins
(SCRUBBED-list mode): the two lists ship verbatim with the original hashes, the scrubbed files are named in
`public/SCRUBBED.txt`, and `verify-lists` checks those for presence only. `tools/verify_delivery.py --strict` refuses the
added public files and the scrubbed ones; it is not a public target.

**Python build for `test`.** The package's test A-ORC-13 (the reads of one claim, under an audit-hook spy) refuses any
Python-level open outside the package, the campaign, the job-private runtime and the platform class. CPython builds whose
`os.urandom` calls getrandom raise no such open. Some builds instead read `/dev/urandom` through a Python-level open, for
example a python-build-standalone CPython 3.12.9 on symmetry (2026-10-16). With those, A-ORC-13 fails for that reason
alone, while a conda-based CPython 3.12.9 on the same node passes it. `public/check_python.py` detects such a build and
stops `test` before the suite runs; use another Python (`make -f public.mk test PY=...`). The delivered test is unchanged.

**One load-sensitive case.** In `test`, the case `lane_sigterm` (F7) sends SIGTERM to the lane worker while two lanes run
native tasks. In its `stuck_native` variant the native worker ignores SIGTERM, and the test sets `C8_LANE_STOP_SECONDS=4`
(the production default is 25 s). Each lane kills its run after 0.8 x 4 = 3.2 s and must exit before the worker's 4 s
deadline, a margin of 0.8 s. On a time-shared node under load, one lane can miss that margin. The worker then kills that
lane and removes its scratch, which is the designed fallback, and its output reads `lane exit codes [-9, 143]; 1 lane(s)
killed after 4 s`. The test expects `[143, 143]` and fails. make then stops `test-python` at that step, so the 18 steps
after it do not run. This happened once in a full acceptance run on symmetry (2026-10-16). Ten runs of the case alone on
the same node passed.

`make -f public.mk retest-lane-sigterm LOG=<full output of the failed test>` handles that failure only. It first checks
the log:
- `lane_sigterm` in its `stuck_native` variant is the only failure;
- the failure carries that signature;
- make stopped at the `unit_orchestration` step.

If the log passes the check, the target reruns the case once and then runs the 18 skipped steps. It takes them verbatim
from the package `Makefile`, so their variables apply unchanged; about 30 min on symmetry. Any other log is refused (exit 2); rerun
the full `test`. The delivered test is unchanged.

### `LRI_C8_shared`

Folder: `code/LRI_C8_shared/`.

#### LRI_C8_shared: shared eighth-order inputs of C8(2) and C8(3)

Two parts, each written by one of the two eighth-order calculations and checked by the other:

- `inventory/inventory8_d2/` (from the C8(2) package, `../LRI_C8_D2_HPC/gen/`): the nine-vertex class and forest
  inventory at loops 7 and 8 (26,540 classes at eight loops) and the d = 2 payloads (G-files with masks, forest terms,
  weights and importance rates) of the 3,150 seven-loop and 21,689 eight-loop finite kernels (20,400 of which are
  integrated; `selection.json`), as four payload tars, with
  the gate records of their checks (`gates/`) and the generator sources that made them (`src/`). The tree is frozen: its
  `MANIFEST.json` has the sha256 `46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099` (C8_H1_PIN), which both
  packages pin; `MANIFEST.json` pins `SHA256SUMS`, which lists every other file, and `MEMBERS.sha256` lists every tar member.
  The C8(3) package rewrites the rate line of the same G-files for d = 3.
- `assembly/` (from the C8(3) package): the d-general order-8 assembly (`order8_assembly.py`), its exact checks and tests,
  the power-sector reporting protocol (`POWER_PROTOCOL.md`) and the d = 2 / d = 3 low-loop inputs used as cross-checks,
  delivered by `HANDOFF_assembly.json` (sha256 f5ff6a35…) and vendored byte for byte in both packages; `H1_gates/` holds the
  C8(3) session's gate records on the inventory.
- `inventory/HANDOFF_inventory8_d2.json` and `inventory/HANDOFF_design.json`: the handoff records of the inventory and of
  the design tool, which the C8(3) package reads.

##### Targets (run in this folder)

| Target | What it does | Time |
|---|---|---|
| `make -f public.mk test` | the pin, `SHA256SUMS`, every non-payload file of the tree, and every delivered assembly file at its sha256 (the payload tars are reported missing until fetched) | seconds, Python only |
| `make -f public.mk verify` | the tree's own verifier, all four levels including every tar member | about 1 min, after `fetch-data` |
| `make -f public.mk fetch-data` | downloads the four payload tars (7.8 GB) from the paper's Zenodo data record (https://doi.org/10.5281/zenodo.23466766), checks their sizes and sha256, and places them in `inventory/inventory8_d2/payload/` | the download |

Nothing may be added inside `inventory/inventory8_d2/` (the verifier refuses unlisted files); the payload tars are placed in
its `payload/` folder as they are.

##### Files added for the release

`public.mk`, `public/check.py`, `public/fetch.py`, `public/hosted.json`, `REVIEWS.md`. Not shipped: the coordination notes and decision log between the two sessions,
the review records (summarized in REVIEWS.md), the superseded design handoff and its self-check, a pack-format proposal and
the shared profiling notes.

### `LRI_C8_D2_HPC_optimized`

Folder: `code/LRI_C8_D2_HPC_optimized/`.

#### LRI_C8_D2_HPC_optimized: an independent eighth-order code for d = 2

This package is the separately developed code behind the independent check of C8(2) in Section 31.7 of the note:

    C8(2) = 46006.1 +- 13.4 (sampling standard error), +1.03 combined standard errors from the reported estimator
    45990.0 +- 8.2 (GFF/results/C8_2). The two estimates are not combined; the reported value stays 45990 +- 33.

##### What it is

An eighth-order extension of the seventh-order d = 2 package of Section 28, written by another AI model, with an optimized
native kernel. It generates its own nine-vertex graphs and eight-loop payloads, extends the kernel and regulator jets to
eight loops, derives its own two-loop and Gamma inputs, assembles the eighth-order fixed point on its own, and allocates and
samples with its own streams. It shares with the main calculation the seventh-order kernel construction and its precision
policy (long double, binary128, 350-digit GMP), the importance sampler, the digital nets and seed hashing, the finite
renormalization scheme and, byte for byte, the payloads of loops three to seven. An error in those shared parts would not be
detected by this check.

The code is shipped at git commit a2a9a46: a791a1f, the commit that ran the pilot and the production, plus the final
Expanse gate record of a791a1f. The delivered numerical files (`src/`, `Makefile`, the tools that a campaign plan pins)
are byte-identical to the delivery; a cluster layer for Expanse and symmetry was added on top (`tools/node_runner.py`,
`tools/site_submit.py`, `tools/seed_sync.sh`, `slurm/site_gate.sh`, `slurm/node_runner.sh`, `slurm/env_*.sh`,
`tests/site_layer.py`, `docs/SITES.md`). The package's own `README.md` and `docs/` describe the code as delivered; its
calculation note `docs/C8_D2_calculation.tex` and results fragment `docs/C8_results_fragment.tex` are merged into note
Section 31.7 and not shipped (one TeX note per direction), so the README's pointer to the former has no target.

##### Targets (run in this folder)

| Target | What it does | Time and node |
|---|---|---|
| `make -f public.mk test` | decimal build, kernel point and Taylor checks against an independent evaluator, assembly formula, scheduler, allocation and site-layer tests | about 5 min, one Linux node (g++ with OpenMP and libquadmath, Boost headers, GMP) |
| `make -f public.mk fixtures` | the optimized GMP kernel against the unmodified reference kernel on 52 frozen fixture cases, bit for bit (the check cited in Section 31.7) | about 3 min, same node |
| `make -f public.mk replay` | recombines the production's and the pilot's 24 merged group records with the production's assembler, compares every field of both results, and recomputes every number the note quotes for this check (65 rows) | about 10 s; Python 3.10+ and numpy only |
| `make -f public.mk fetch-data` | downloads the production's campaign directory from the paper's Zenodo data record (https://doi.org/10.5281/zenodo.23466766) (933 MB, 4.3 GB unpacked), checks its size and sha256, and unpacks it into `../../data/C8_2_check/hosted/`; `ALL=1` adds the delivered package zip (484 MB) for a production rerun | a few minutes plus the download |
| `make -f public.mk remerge` | re-merges the 24 groups from the hosted checkpoints and compares the merged records byte for byte; recomputes the kernel time | about 15 min on 8 cores, after `fetch-data` (1.7 GB) |

A production rerun (about 26,500 core-hours on 11 nodes of 128 cores) needs the graph packs of the original package
(hosted, 7.8 GB) and is described in REPRODUCE.md.

##### Files

- `public.mk`, `public/replay.py`, `public/remerge.sh`, `public/kernel_time.py`, `public/fetch.py`, `public/hosted.json`,
  `REVIEWS.md`: added for the public
  release. Everything else is the code as it ran.
- Records: `../../data/C8_2_check/` (plans, configs, merged records, attempt records of the production and the pilot);
  results: `../../results/C8_2_check/` (C8_result.json of both, diagnostics, comparison).
- Not shipped: `RESULTS.md` of the delivery (earlier runs of the delivering model, whose data are not part of this
  release; the README still links to it) and optimization diagnostics under `optimization_work/` that no check uses.

### `LRI_C8_D3_HPC`

Folder: `code/LRI_C8_D3_HPC/`.

#### C8(3): the eighth-order coefficient in three dimensions (code/LRI_C8_D3_HPC)

**C8(3) = 1602.6 ± 3.9** (ε = 2s − 3), from the estimator 1602.6052229663408 with sampling standard error
0.9516489064069612. The allowance is four sampling SEs rounded up to a multiple of 0.1; it was fixed after the result and
confirmed by the author. It is empirical, conditional on finite variance (note Sec 32.5 gives evidence, not a bound), and
does not cover errors shared by the graph and renormalization framework. Note: condensed note Section 32 (`app:C8d3`).
The paper rounds the same allowance (4 SE = 3.807) by the PDG rule and quotes **C8(3) = 1603 ± 4**; the condensed note
keeps one more digit. `replay` checks both (rows S1.1, S1.2 and S1.8).

##### What is computed

Both sectors of the eight-loop calculation are integrated explicitly: 24,173 kernels in 24 groups (campaigns a and b ×
power-free and power-containing × loops 3–8), with randomized digital nets, importance rates ×0.8 and ×0.7, and the
precision policy of the seventh-order worker (long double, binary128 at 1e-9, 350-digit GMP at 1e-23). The renormalization
functions are assembled through eight loops by the shared order-8 assembly (`vendor/c8_assembly/`), with three hard gates.

| part | value | sampling SE |
|---|---|---|
| power-free C8^pf(3) | 1601.9999290 | 0.7279030 |
| power correction Δp C8(3) | 0.6052940 | 0.6129303 |
| C8(3) | 1602.6052230 | 0.9516489 |

Checks: lower orders C3–C7 within 0.74 SE of their references; campaigns a/b 1604.684 ± 1.239 and 1600.527 ± 1.445
(pull 2.18, spread over loops and graphs); bootstrap SE 0.940; tail monitor: 10,034 L8 graphs listed, none above 3% of its
group's variance; pilot 1619 ± 16. Cost: 15,102 core-hours on AMD EPYC 7543 (symmetry), 2026-10-09 to 10-12.

##### Use

```sh
cd GFF/code/LRI_C8_D3_HPC
make -f public.mk replay        # recompute every quoted number from results/C8_3 (~20 s, no hosted data)
make -f public.mk test          # pure-Python regression tests (~7-20 min, 1 core)
make -f public.mk fetch-data TIER=rerun && make -f public.mk test-native   # native build and gates (toolchain, 8.8 GB)
```

REPRODUCE.md (C8(3) part) has the tiers, the production rerun and the regeneration of the inputs. The package's own
`README.md`, `Makefile` and `docs/` ship verbatim from the production commit.

##### Layout

```
code/LRI_C8_D3_HPC/            the package at git commit 4fbd1bae (the production export), verbatim, pruned
  src/ tools/ tests/ slurm/    worker, campaign tools, tests, job scripts
  gen3/ inputs/ vendor/        d=3 payload pipeline, the inputs (L3-L6 packs in git; L7/L8 hosted), vendored assembly
  reference/                   the original C7(3) package (L7 member files and archived production hosted; its copy of
                               the d=2 method note, reference/C7_d2_complete.tex, not shipped: public/dropped_paths.txt,
                               condensed note Section 28) + baselines
  benchmarks/symmetry_2026-10-c8/
    production/prod1/          the production report, campaign split (ab_split/), tail N-trend (tail_ntrend/),
                               status/verify/budget outputs, job list, frozen design (production/design_prod/)  [6dd4a75a]
    production/margin_*/       the rate re-derivation probes (48 graphs)                                       [6dd4a75a]
    production/price/          the three priced designs
    pilot/                     pilot report, sigma table, campaign manifests and summaries
  public.mk, public/           public targets; replay_c8_3.py, fetch_data.py, SHA256SUMS.evidence_6dd4a75a, REVIEWS.md
results/C8_3/                  C8_result.json, manifest.json, cost model, CPU vendor, SHA256SUMS.symmetry,
                               groups/<group>/{merged.json, config.json}  (byte-identical production records)
data/C8_3/                     DATA.md, HOSTED.json; hosted in the Zenodo record: L7/L8 packs, C7(3) reference tars,
                               graph_replicates.csv and the L8 graph_tails.csv (two bundles)
```

##### Limitations

- The ±3.9 is a heuristic allowance, not a confidence interval. The d=3 kernel's U^(3/2) blocks the exact tail bound used
  at d = 2; finite variance rests on empirical evidence (rate probes on 48 graphs; ξ̂ falling with N).
- The campaigns differ by 2.18 combined SEs; no concentrated cause was found, but a diffuse rate effect is not excluded.
- Production-support tools added after the second code inspection (budget line, conservative tail rule, margin probe)
  were not Codex-inspected (public/REVIEWS.md).
- Off the production CPU class, `tools/verify_result.py` can stop at a rounding-level gate diagnostic; the replay
  compares every other field and reports this row as KNOWN.
- Two printed numbers of the note edition fa71533 disagree with the records in the last digit (Sec 32.4 error table,
  power-free L = 4: 0.011 vs 0.010; Sec 32.5: 0.88 vs 0.87); the replay reports them as ERRATUM.
- The independent check (1600.98 ± 3.97) is a separate package (`C8_3_check`).

### `LRI_C8_D3_OPT`

Folder: `code/LRI_C8_D3_OPT/`.

#### Independent check of C8(3): the LRI_C8_D3_OPT package

This folder (`GFF/code/LRI_C8_D3_OPT`) holds a separately developed code for the eighth-order coefficient C8(3) of the
thermal dimension of the three-dimensional long-range Ising model, with epsilon = 2s - 3. The paper's value of C8(3)
comes from a different package, `GFF/code/LRI_C8_D3_HPC` (records in `GFF/results/C8_3`). This code was run once at
production size as a cross-check; its result is quoted next to the main value and is not combined with it.

##### Result

| quantity | value | record |
|---|---|---|
| C8(3), sampling standard error | **1600.98 +- 3.97** (estimator 1600.9770046710833, SE 3.967937252893955) | `GFF/results/C8_3_check/runs/prod1/C8_result_54838171.json` |
| difference from the main estimator 1602.6052 +- 0.9516 | -0.40 combined standard errors | main record `GFF/results/C8_3/C8_result.json` |
| campaigns a and b (independent seeds and sampler rates 0.8 and 0.7) | 1603.53 +- 4.91 and 1598.42 +- 6.24, pull 0.64 | same result record |
| power-free part and power correction | 1602.61 +- 2.96 and -1.63 +- 2.64 | same |
| lower-order by-products, pulls against the references | C3 -1.41, C4 -1.55, C5 -0.10, C6 33.599 +- 0.014 (+1.73), C7 -220.40 +- 0.19 (-0.21) | same |
| design | 24,173 kernels per campaign, 16 replicates per campaign, at least 4,096 points per graph, 1,994 jobs, 3.71 x 10^10 evaluations | `runs/prod1/manifest.json`, `allocations/prod1_2000.json` |
| cost | about 76.7 node-hours of AMD EPYC 7742 (128 cores), about 9,800 service units, 10 and 11 October 2026 | `GFF/results/C8_3_check/README.md` |

The error is the replicate-sampling covariance propagated through the fixed point. The package itself marks the
result `reportable_precision_established = false`: no allowance for numerical controls was assigned, and there was no
results review of this number (see `REVIEWS.md`). It shares with the main calculation the three-dimensional mixed-forest
kernel and precision policy of the seventh-order integrator, the importance sampler, the digital nets and the finite
renormalization scheme; an error in those shared parts would not be detected by this comparison. It regenerates the
graph inputs, derives its own low-loop inputs (its `inputs/two_loop.json` differs from the main package's), extends the
regulator jets and solves the eighth-order fixed point with its own assembly (`tools/rg.py`, `tools/assemble.py`).

##### Quick start

```sh
cd GFF/code/LRI_C8_D3_OPT
pip install -r public/requirements.txt     # numpy, scipy, mpmath (sympy, pynauty only for regeneration)
make -f public.mk replay                   # about 3 s, any OS: every quoted number, PASS/FAIL table, exit 1 on FAIL
make -f public.mk test                     # Linux x86-64 node with GCC, GMP, Boost headers: build and package tests, 2-3 min
make -f public.mk test-py                  # the Python-only tests, seconds, any OS
```

`make replay` needs only files in git: the result record stores, per loop (3 to 8) and sector (power-free and
power-containing), the pooled replicate means and the covariance of those means. The replay recomputes the estimator
and its standard error from them with the package's own fixed-point code and covariance propagation, runs the package's
`assemble.calculate()` on replicate matrices with exactly those moments, recomputes the two campaign values from the
per-graph statistics, the job and evaluation counts from the allocation by the planner's rule, and checks every hash
binding between records and code. Its table is in `.work/replay/replay_report.txt`; the rows and tolerances are
described in `REPRODUCE.md`. The native outputs of the campaign (per-job checkpoints) are not shipped.

##### What is here

- The package as it ran in production (git commit `d5deeb9`), verbatim: `src/` (native worker), `tools/` (planner,
  dispatcher, assembly, fixed point, allocation, graph generation and audits), `tests/`, `slurm/` and `tools/submit.py`
  (the site layer used on Expanse; it encodes one user's allocation and caps), `docs/` (numerics, HPC and cluster
  runbooks), `reference_c7/` (C7 regression fixtures), `baseline/` (the unoptimized worker for the regression
  test), `verification/` (the delivered evidence), `inputs/` (analytic jets, the active-graph inventory, the coverage
  certificate, the delivered pilot design) and `SHA256SUMS`.
- `inputs/free/` and `inputs/power/` hold only 179 of the 24,173 graph payloads: the fixtures read by
  `tests/test_optimization.py` and `tests/check_c8_points.py`. The full set (9.15 GB) is hosted (`make -f public.mk
  fetch-data`; `GFF/data/C8_3_check/DATA.md`).
- `public/` (new, not part of the package): `replay_check.py`, `README.md`, `REPRODUCE.md`, `PROVENANCE.md`,
  `REVIEWS.md`, `requirements.txt`, the Slurm templates `slurm/` for a production rerun, and
  `make_data_bundles.sh` with `data_bundles.sha256` for the hosted bundles. `public.mk` holds the targets.
- Not shipped: `DELIVERY_MANIFEST.json`, `regeneration/` and `inputs/complete_inventory_L*.json` (hosted, for graph
  regeneration only), and the TeX notes named in `public/dropped_paths.txt`: the code author's derivation and
  calculation notes (`derivation.tex`, `docs/DERIVATION.tex`, `docs/C8_3D_calculation.tex` and `.pdf`) and
  `reference_study/` (an earlier version of the condensed note given to the code's author). The derivation of this
  check is in the condensed note (`GFF/note/`), Section 32.7 ("An independent code"); the package's own `README.md`
  still names the notes. `tools/write_report.py` reads `docs/DERIVATION.tex`; it ships verbatim and no public target
  runs it. Also not shipped: the
  delivered pilot's raw checkpoints (hosted), compiled binaries, the port's plan, review transcripts, logs and
  admission ledgers (summarized in `REVIEWS.md` and `PROVENANCE.md`).

The package's own `README.md` describes the code as delivered, including its pilot (C8(3) = 1514.6 +- 161.7 from
16-point nets, an exploratory estimate superseded by the production). Its build instructions name GCC 13.3 / 14.2,
Boost 1.77 / 1.83 and GMP 6.3; the production build used GCC 13.3.0, Boost 1.77 and GMP 6.2.1.

##### Known limitations

1. Sampling error only. No reporting allowance, no tail or convergence campaign beyond the a/b and half-stream
   splits, and no results review of the number.
2. Shared method: the comparison with the main result cannot detect an error in the shared kernel, sampler, nets or
   renormalization scheme.
3. The production commit `d5deeb9` contains one uninspected admission change; the two later fix commits (`3961865`,
   `6edcc9e`) change only the admission layer and are not shipped (`REVIEWS.md`).
4. The native worker builds only on x86-64 Linux (`__float128`, libquadmath). A rerun with a fresh seed reproduces the
   estimate statistically, not bit for bit; `make test` checks the worker against fixed-input regressions.

Licence: TBD (the package carries no licence of its own). Citation: the paper.
