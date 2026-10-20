# Reviews of the GFF packages

Summaries of the code and results reviews of each package (reviewer, rounds, verdict, what changed). Raw review logs are not published.

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

#### REVIEWS: one-dimensional analytic C5 (lri_numerical_resolution, lri_psi_complete_update, lri_fixed_hypergeometric_update)

**No review exists for these three packages.** No Codex inspection, Claude review loop or results review was run
on them: no `*_review/` or `*_loop/` folder, review log or memory entry refers to them (searched 2026-10-13 in
`<PROJECT>/`, the note repository, `LRI_1d_through_C6/` and the project memory). So each package gets no
`REVIEWS.md` of its own; this file states that once for the row.

What exists instead, none of it a review:

* **Self-checks delivered with the packages** (by the authoring sessions): the exact SymPy certificates
  (`symbolic_audit.py`, `symbolic_checks.py`), the multi-precision numerical checks and their records, and the
  package's own clean-extraction audit (`verification/records/clean_package_audit.json` of
  lri_numerical_resolution, not exported).
* **Bundle consolidation (22 September 2026):** saved-data reassembly of C5(1) by `tools/reproduce.py c5` in a
  scratch copy, `validation/c5_reassembly.json` of the bundle: span and maxgap C5 reproduced with absolute
  difference 0.0 (tolerance 1e-10). The bundle states that this is not a proof audit.
* **Public-edition replay (this export, 2026-10-13, C71d helper):** every original script of the three packages
  rerun from the shipped files on macOS/arm64 with two mpmath/SymPy/NumPy versions; every regenerated record
  equal to the shipped one in every numeric field; 125 checks, 0 FAIL. Added independent checks: the unlabelled
  class audit (129 = 92 + 6 + 3 + 28, certificate words and weights, Section 12 table), the Section 1.1 closed
  forms evaluated as printed, and the Section 10.4 kernel identity. These are reproduction checks, not a review of
  the proofs.
* **Other agreement in the note:** the generic-dimensional reduction of Section 20.7 (`LRI_C5_general_d`, C62d)
  reproduces C5(1) to 3e-34. The C7(1) campaign's uncalibrated degree-six lower-order value, -731.174185 with
  sampling error 0.008355, lies -4.15 sampling errors from it, which Section 27.9 attributes to the radial
  truncation. An independent Claude-session five-loop calculation of September 2026
  (`eps5_derivation/`, memory `lri-five-loop-status`) is not cited by the note and is not part of this row.

### `lri_psi_complete_update`

Folder: `code/lri_psi_complete_update/`.

_same as the section above (one text for the whole unit)._

### `lri_fixed_hypergeometric_update`

Folder: `code/lri_fixed_hypergeometric_update/`.

_same as the section above (one text for the whole unit)._

## C0-C5 in closed form, general d

### `lri_general_special_functions_update`

Folder: `code/lri_general_special_functions_update/`.

#### Reviews of lri_general_special_functions_update

This package (general-dimensional C0..C5: graph reduction, fixed-point assembly, spectral masters and coefficient values (note Sections 12-13)) was written by OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the research bundle (model stated by the author, 2026-10-13), outside the logged
Claude Code sessions, and delivered on 7 September 2026 as `LRI_general_dimension_special_functions.zip`; it is a member of the research bundle
`LRI_complete_research_bundle.zip` (sha256 3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0, consolidated
on 22 September 2026). No file of it was changed afterwards. The public release ships the package's own layer
(see README) plus new files under `public/`, `public.mk` and this file, written by the Claude Code session C62d on
13 October 2026.

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Code | none | 0 | not reviewed | The code was never given a Codex or Claude code review. |
| Bundle consolidation (22 Sep 2026) | the delivering session | 1 | byte integrity only | Nothing; the bundle's reassembly wrapper (`tools/reproduce.py`) does not run this package. |
| Public release (13 Oct 2026) | Claude Code session C62d | 1 | records reproduced | Nothing in the package. Every delivered SymPy and mpmath record was regenerated byte for byte (timing fields aside) on macOS with two library versions, numpy records within the tolerances of `public/replay.py`. |

Independent checks of the results (by other means, in other folders of the project):
- d=2: the closed forms of the nonprimitive masters L2 = -2 log2 P4(2) and K2 = 32 G^2 - 28 zeta(3) log2 were proved by
  Claude Code sessions C62d and C63d (five proof routes, each passed by three review lenses, `LRI_C5_d2_proof/`; three
  further proofs, `LRI_C5_d2_simplify/proof/`), giving C5(2) in closed form. The master-level values of C4(2),
  C5(2) of the special-functions package agree with the closed forms to 5.6e-13 and 3.5e-13 (checked by `public/replay.py` of the special-functions and
  periodization packages).
- d=3: 43- to 50-digit masters and C5(3) to 50 digits (session C63d, `LRI_C5_d3/`, two cluster runs agreeing to 1e-45)
  agree with this bundle's d=3 masters to 3e-14 to 2e-13 relative and with its C5(3) to 2.2e-13.
- generic d: reference values of P4, Q, L, Z, K at d = 0.8, 1.25, 1.5, 2.5, 2.75 (44-50 digits) and K_d to 100 digits
  (`LRI_C5_general_d/`) confirm the master definitions, not the C4(d), C5(d) assembly.
- d=1: the general formula reproduces the analytic C4(1) and C5(1), which a Claude Code session rederived (C4) and
  confirmed (C5); Hamiltonian truncation, a method that shares nothing with the graph framework, gives
  C4(2) = 5.0488682(10) and C5(2) = -38.800(38) (provisional).

What was never reviewed or checked independently: the generic-dimensional graph sum and minimal-subtraction assembly
behind the formulas for C4(d) and C5(d) (note eqs. gs:C0C4, gs:C5) were not rederived at generic d; they are checked
exactly at d=1 and only through the masters at d=2 and d=3.

No recommendation was overruled (there were no review rounds).

### `lri_general_closed_update`

Folder: `code/lri_general_closed_update/`.

#### Reviews of lri_general_closed_update

This package (finite multivariable Horn arrays of the six C5 masters and the Q2, Z2 identities (note Section 14)) was written by OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the research bundle (model stated by the author, 2026-10-13), outside the logged
Claude Code sessions, and delivered on 10 September 2026 as `LRI_general_dimension_closed_forms.zip`; it is a member of the research bundle
`LRI_complete_research_bundle.zip` (sha256 3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0, consolidated
on 22 September 2026). No file of it was changed afterwards. The public release ships the package's own layer
(see README) plus new files under `public/`, `public.mk` and this file, written by the Claude Code session C62d on
13 October 2026.

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Code | none | 0 | not reviewed | The code was never given a Codex or Claude code review. |
| Bundle consolidation (22 Sep 2026) | the delivering session | 1 | byte integrity only | Nothing; the bundle's reassembly wrapper (`tools/reproduce.py`) does not run this package. |
| Public release (13 Oct 2026) | Claude Code session C62d | 1 | records reproduced | Nothing in the package. Every delivered SymPy and mpmath record was regenerated byte for byte (timing fields aside) on macOS with two library versions, numpy records within the tolerances of `public/replay.py`. |

Independent checks of the results (by other means, in other folders of the project):
- d=2: the closed forms of the nonprimitive masters L2 = -2 log2 P4(2) and K2 = 32 G^2 - 28 zeta(3) log2 were proved by
  Claude Code sessions C62d and C63d (five proof routes, each passed by three review lenses, `LRI_C5_d2_proof/`; three
  further proofs, `LRI_C5_d2_simplify/proof/`), giving C5(2) in closed form. The master-level values of C4(2),
  C5(2) of the special-functions package agree with the closed forms to 5.6e-13 and 3.5e-13 (checked by `public/replay.py` of the special-functions and
  periodization packages).
- d=3: 43- to 50-digit masters and C5(3) to 50 digits (session C63d, `LRI_C5_d3/`, two cluster runs agreeing to 1e-45)
  agree with this bundle's d=3 masters to 3e-14 to 2e-13 relative and with its C5(3) to 2.2e-13.
- generic d: reference values of P4, Q, L, Z, K at d = 0.8, 1.25, 1.5, 2.5, 2.75 (44-50 digits) and K_d to 100 digits
  (`LRI_C5_general_d/`) confirm the master definitions, not the C4(d), C5(d) assembly.
- d=1: the general formula reproduces the analytic C4(1) and C5(1), which a Claude Code session rederived (C4) and
  confirmed (C5); Hamiltonian truncation, a method that shares nothing with the graph framework, gives
  C4(2) = 5.0488682(10) and C5(2) = -38.800(38) (provisional).

What was never reviewed or checked independently: the generic-dimensional graph sum and minimal-subtraction assembly
behind the formulas for C4(d) and C5(d) (note eqs. gs:C0C4, gs:C5) were not rederived at generic d; they are checked
exactly at d=1 and only through the masters at d=2 and d=3.

No recommendation was overruled (there were no review rounds).

### `lri_general_periodization_update`

Folder: `code/lri_general_periodization_update/`.

#### Reviews of lri_general_periodization_update

This package (finite periodization of the primitive sector and the d=2 factorization of P4(2), P5(2) (note Sections 15.1-15.5)) was written by OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the research bundle (model stated by the author, 2026-10-13), outside the logged
Claude Code sessions, and delivered on 11 September 2026 as `LRI_general_periodization_and_d2_factorization.zip`; it is a member of the research bundle
`LRI_complete_research_bundle.zip` (sha256 3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0, consolidated
on 22 September 2026). No file of it was changed afterwards. The public release ships the package's own layer
(see README) plus new files under `public/`, `public.mk` and this file, written by the Claude Code session C62d on
13 October 2026.

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Code | none | 0 | not reviewed | The code was never given a Codex or Claude code review. |
| Bundle consolidation (22 Sep 2026) | the delivering session | 1 | byte integrity only | Nothing; the bundle's reassembly wrapper (`tools/reproduce.py`) does not run this package. |
| Public release (13 Oct 2026) | Claude Code session C62d | 1 | records reproduced | Nothing in the package. Every delivered SymPy and mpmath record was regenerated byte for byte (timing fields aside) on macOS with two library versions, numpy records within the tolerances of `public/replay.py`. |

Independent checks of the results (by other means, in other folders of the project):
- d=2: the closed forms of the nonprimitive masters L2 = -2 log2 P4(2) and K2 = 32 G^2 - 28 zeta(3) log2 were proved by
  Claude Code sessions C62d and C63d (five proof routes, each passed by three review lenses, `LRI_C5_d2_proof/`; three
  further proofs, `LRI_C5_d2_simplify/proof/`), giving C5(2) in closed form. The master-level values of C4(2),
  C5(2) of the special-functions package agree with the closed forms to 5.6e-13 and 3.5e-13 (checked by `public/replay.py` of the special-functions and
  periodization packages).
- d=3: 43- to 50-digit masters and C5(3) to 50 digits (session C63d, `LRI_C5_d3/`, two cluster runs agreeing to 1e-45)
  agree with this bundle's d=3 masters to 3e-14 to 2e-13 relative and with its C5(3) to 2.2e-13.
- generic d: reference values of P4, Q, L, Z, K at d = 0.8, 1.25, 1.5, 2.5, 2.75 (44-50 digits) and K_d to 100 digits
  (`LRI_C5_general_d/`) confirm the master definitions, not the C4(d), C5(d) assembly.
- d=1: the general formula reproduces the analytic C4(1) and C5(1), which a Claude Code session rederived (C4) and
  confirmed (C5); Hamiltonian truncation, a method that shares nothing with the graph framework, gives
  C4(2) = 5.0488682(10) and C5(2) = -38.800(38) (provisional).

What was never reviewed or checked independently: the generic-dimensional graph sum and minimal-subtraction assembly
behind the formulas for C4(d) and C5(d) (note eqs. gs:C0C4, gs:C5) were not rederived at generic d; they are checked
exactly at d=1 and only through the masters at d=2 and d=3.

No recommendation was overruled (there were no review rounds).

## Closed forms of L2, K2 and C5(2)

### `LRI_C5_d2_simplify`

Folder: `code/LRI_C5_d2_simplify/`.

#### Reviews of LRI_C5_d2_simplify (discovery and three further proofs of the d = 2 closed forms)

Claude Code session C62d wrote this package on 2026-10-01 and 02. It has two parts, reviewed differently.

##### 1. The discovery (top level)

The discovery is:
- the exact square-lattice factorizations;
- the 70-digit Euler-Maclaurin single sums (job 567346, `confirm_dps70.json`);
- the PSLQ identification of L2 and K2.

No review lens examined it as such. It was checked independently twice:
- Session C63d evaluated L2 and K2 from the spectral kernel with a separate code. These are `GFF/code/LRI_C5_d3/wf_d2check` and the note's residuals 1.7e-79 and 3.1e-62. A first pass agreed to about 1e-12.
- Session C63d's five proof routes (`../LRI_C5_d2_proof`) compared their closed forms with the 70-digit record, to 3e-70 and better.

The note uses the discovery only as a numerical confirmation, not as a proof step.

##### 2. The three further proofs (`proof/`)

Workflow `wf_6fd83950-f9b` of session C62d (2026-10-02, about 10:15 to 12:15) used three prover subagents:
- `L2-fourier`, by a Fourier (Cauchy beta) representation;
- `L2-elliptic`, by Hardy-space Parseval pairings and Landen;
- `K2-parseval`, by rim regularization of the spectral form.

Each route had two verifier subagents with fresh contexts. All six verdicts are ACCEPT:

| Route | Rigor verifier | Numerics verifier |
|---|---|---|
| L2-fourier | ACCEPT, no fatal or major gap | accept, every lemma to 1e-37..1e-41 at 40 digits (job 567989) |
| L2-elliptic | ACCEPT, no fatal or major gap; minor points m1, m2, m4, m5 | every displayed identity at 30 to 50 digits (job 567970) |
| K2-parseval | ACCEPT as a conditional theorem: the statements for `gs:Kseries` and `gs:Kdefinition` are conditional on the per-spin residue identity (S) and the mixed-trace step (T) | accept; per-spin families 1.2e-38, Laurent coefficients 5e-43, direct spectral sums 1e-31..1e-35 (job 568005) |

A synthesizer subagent then:
- wrote the synthesis `proof/PROOF_STATUS.md` and the merge-ready fragment `proof/proof_d2.tex` (both now merged into
  note Section 18 and not shipped);
- re-did the exact algebra (`proof/synth/`, all residuals 0);
- corrected the finder. Its PSLQ collapse form of L2 holds only through two lemmas, so the structural, lemma-free form is the one to quote.

The four minor points of the L2-elliptic rigor verifier were resolved in the fragment:
- the uniform Stirling citation;
- the chain rule in the collapse;
- the wording "Z-linear relation";
- the gs:* definitions listed as inputs.

Other terse points, which do not affect the claims, were listed in that synthesis.

**What happened to the fragment.** It was not merged into the note as text. The note merged C63d's insert and cites
these as "three further proofs". C63d's proof of the mixed-trace step at d = 2 (note Section 18.7) removes the condition
(T). C63d's merge review (`wf_8e8ab059-5ad`, see `../LRI_C5_d2_proof/REVIEWS.md`) corrected the note's sentence
describing these routes.

##### Recommendations overruled

None.

##### Never reviewed

- **The discovery scripts.** `factor_*.py`, `parallel_eval.py` and `emsum.py` were not code-reviewed. Their outputs are
  checked independently (see part 1), and the factorizations are re-derived term by term by
  `../LRI_C5_d2_proof/L2_singlesums/verify_symbolic.py` (48 terms identical).
- **The release overlay.** `public.mk` and `public/*` were not reviewed by another model. They were tested by running
  them:
  - test PASS with Python 3.10.11, mpmath 1.2.1 and 1.3.0, sympy 1.11.1 and 1.12;
  - replay PASS with Python 3.9.6 and 3.10.11, mpmath 1.2.1, 1.3.0 and 1.4.1.

##### Not shipped

The verifier reports and the verifiers' numerical scripts and outputs:
- `proof/*/verify_rigor.md`, `verify_numeric.md`;
- `proof/*/verify_numeric/`, `verify_rigor_*.py`.

The note quotes none of their numbers. The verdicts are summarized above.

### `LRI_C5_d2_proof`

Folder: `code/LRI_C5_d2_proof/`.

#### Reviews of LRI_C5_d2_proof (proofs of the d = 2 closed forms of L2 and K2)

Claude Code session C63d wrote this package on 2026-10-02 in workflow `wf_2604cddc-2ec`. Five independent subagents each
wrote a proof route:
- `L2_singlesums`
- `L2_structural`
- `K2_selberg`
- `K2_d1template`
- `K2_gauss`

All reviewers below were Claude subagents of the same session, each with one lens and a fresh context. No OpenAI Codex
or other external reviewer was involved. The raw review material is not shipped: the lens folders, the verdict file and
the merge review. The exception is the check records listed at the end, which are computations, not prose.

##### Stages

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Proof routes | three lenses per route: algebra, numerics, rigor | 1 per route; `K2_d1template` 2 | all 15 final verdicts "sound" | see below |
| Merged note text | five lenses of workflow `wf_8e8ab059-5ad`: rigor, consistency, numerics, crosscheck, typesetting; then two rechecks | 1 + 2 rechecks | all "minor-fixes"; recheck 1 "minor-fixes"; recheck 2 "ready" | see below |

###### Proof routes

- **`K2_d1template` revision.** Round 0 led to the revision `K2_d1template_fix1/` and `proof_v2.md` (merged into note
  Section 18, not shipped), which supersedes
  `PROOF_K2.md` (not shipped):
  - Theorem 1 is now proved from the position-space integral alone (Riemann bilinear relation, Stokes);
  - the kite factorization is no longer an input;
  - the spectral derivation became Corollary 2.
  Round 1 found no gap.
- **Minor points raised and fixed in the note text:**
  - the domain of the exponential form in Lemma 1.1, |u| < min(x, 1-x);
  - uniform Stirling bounds cited (DLMF 5.11);
  - closing arcs of the K2_gauss contours stated;
  - Thomae at negative argument justified by the identity theorem;
  - the boundary value K(1-x-i0) on the negative axis displayed;
  - the domain of the well-poised Barnes integral stated.
- **Reviewers' own numerics.** The reviewers re-ran the checks at higher precision than the provers: 1e-82 for the L2
  jets; 54 to 68 digits for the K2 master. The note quotes these numbers.
- **Choice of main proofs.** `L2_singlesums` for L2 and `K2_selberg` for K2; the note reproduces both in Sections 18.6
  and 18.7. The other three routes are cited as companion proofs.

###### Merged note text

- **Issues raised:** 46, of which 4 major:
  - the series bullet counted -AU/4 twice (rigor 1, consistency 2);
  - a stale sentence after `fp:P5two` (consistency 1);
  - the description of session C62d's three further proofs (crosscheck 1).
- **Fixes:** 44 applied.
- **Rechecks:** recheck 1 found 5 wording points, which were fixed; recheck 2 returned "ready". C63d then merged the
  text into the condensed note.

##### Recommendations overruled

One, in the review of the merged text. The numerics lens proposed (optional item 2) to say that the 70-digit K2 check
ran "after the rim deformation". This was rejected because it would misdescribe the computation: that value comes from
the theta -> 0 strip limit of the factorized single sums (`LRI_C5_d2_simplify`). The concern behind it was addressed
by the strip-limit wording proposed by the rigor and crosscheck lenses.

##### Never reviewed

- The three further proofs of session C62d (`../LRI_C5_d2_simplify/proof/`) were not reviewed in this workflow. They had
  their own verifiers; see that package's REVIEWS.md.
- The note's own residue proof of the series (`gs:Kseries`) and the identification of `gs:Lseries` with the
  wheel-derivative master were not re-audited as such. The note proves both readings at d = 2 through the routes
  above.
- The release overlay (`public.mk`, `public/*`) was not reviewed by another model. It was tested by running it:
  - replay PASS with Python 3.9.6 and 3.10.11, mpmath 1.2.1, 1.3.0 and 1.4.1, sympy 1.11.1 and 1.12;
  - test PASS with Python 3.10.11, mpmath 1.2.1 and sympy 1.11.1.

##### Check records shipped from the review folders

These are reviewers' computations (scripts and their outputs, no prose) that back numbers the note quotes.
`public/replay.py` reads them, or re-runs them where that is cheap.

| Folder (files) | Backs | Replay |
|---|---|---|
| `review_L2_singlesums_numerics_r0/` (`s3_modes.wl`, `s3.log`, `em.wl`, `s1_values.m`, `s3_residuals.m`) | note l.5145-5146 "hold to 10^-82" | read `s3.log`; Mathematica re-run in `replay-wl` |
| `review_L2_structural_numerics_r0/` (`spec_job.py`, `spec_job.sh`, `spec_analyze.py`, `spec_{2_5,1_2,3_5}.json`, `spec_568067.out`) | note l.5181-5182 "2x10^-70" | re-run with `public/spec_analyze_scaled.py`. The shipped `spec_analyze.py` stops with a singular matrix; the scaled copy reproduces the reviewer's 1.5e-71, 1.6e-70 and 5.6e-71 |
| `review_K2_d1template_numerics_r0/` (scripts, `run.sb`, and the `logs/` that the merged proof cites; 10 uncited round-0 logs are not shipped) | note l.5444-5446 "between 38 and 68 digits at seven values of tau"; the `rev/` rows of the merged proof's checks | read `logs/rC*.log` |
| `review_K2_selberg_numerics_r0/` (`partA2_direct2d.py`, `.out`, `partA2_0.3.log`, `spectral_hp.py`, `spectral_hp55*.out`) | note l.5448-5450 "between 18 and 25 digits", "54 digits" | read the outputs; `spectral_hp.py` needs `../LRI_C5_d3/wf_d2check` |

## d = 3 specialization and the generic-dimensional reduction of L_d, Z_d, K_d

### `lri_d3_reduction_update`

Folder: `code/lri_d3_reduction_update/`.

#### Reviews: the three d = 3 research-bundle packages

Summary for `GFF/code/lri_d3_reduction_update`, `GFF/code/lri_d3_matrix_update` and `GFF/code/lri_C6_d3_complete_update`.
No raw review logs are shipped.

##### Reviews of the packages themselves

**None recorded.** The packages were written in September 2026 by OpenAI GPT-6 astra in the ChatGPT research conversation that
produced the bundle. No human referee or second AI system reviewed them as packages. The bundle's own consolidation (22 September
2026, `validation/` of the bundle) re-ran the saved-data reassemblies of C5(1), C6(1), C6(2, 3) and C7(1); it did not run
these three packages. Their READMEs state the scope themselves:
- observed residuals, not interval bounds;
- no reduction of the remaining values to ordinary scalar pFq values;
- the two unknown core coefficients cancel exactly but are not evaluated.

##### Later independent checks of their results (Claude Code sessions, not reviews of the code)

| what | by, when | outcome | where |
|---|---|---|---|
| Q_3, P_4(3) and the d = 3 nonprimitive masters, from a separate spectral representation | `LRI_C5_d3` (C5(3) closed form), 2026-10-02 | It reports its inputs good to about 10⁻⁸⁰, except P_5(3), which is independently confirmed only to about 10⁻⁵³ (by this package's own fresh Gamma-kernel integration). The note says so for C5(3). | `LRI_C5_d3/WORKFLOW_RESULT.md` §2; note, Sec. "Three dimensions", last subsection |
| d = 3 specialization of the generic-d reduction against 160-digit values | `LRI_C5_general_d` checks and their independent review, 2026-10-03 | c_{4,k}, X_0, 𝔞₄, 𝔟₄, P_4(3) and others agree to 1.2 × 10⁻⁵¹ (50 digits). The review accepted the d = 3 dictionary with one wording finding: D_L is not literally P̂′; this is already in the note. | note, Sec. "Generic-dimensional reduction", subsection "Checks"; `LRI_C5_general_d/review/VERIFICATION.md` rows C1, C4, C10, E4 |
| C6(3) production that uses the power compensation | `LRI_C6_D3_HPC` package review, 2026-09-28; Codex (gpt-6-astra) results review, 2026-10-01, APPROVED | The results review states that the result relies on the retained analytic power-sector compensation, "which the package does not redo", and that its allowance does not cover it; the package review does not examine it. The power audit of `lri_C6_d3_complete_update` has therefore not been independently reviewed. Its own evidence is its checks: an exact proof of the core cancellation and three high-precision runs with different trial values. | `LRI_C6_D3_results_review/RESULTS_REVIEW.md` §1, §4; `LRI_C6_D3_HPC/tools/assemble.py` (`power_correction` field) |

##### Public-release replay (2026-10-13, Claude Code session C63d)

Not a review: a mechanical rerun of the packages' own scripts in a copy of each package, with every output compared with
the delivered records and with the note's quoted numbers.

| package | result | tier |
|---|---|---|
| `lri_d3_reduction_update` | 69 PASS, 0 FAIL | replay |
| `lri_d3_matrix_update` | 22 PASS, 0 FAIL | replay |
| `lri_d3_matrix_update` | 3 PASS | search |
| `lri_C6_d3_complete_update` | 68 PASS, 0 FAIL | replay |

Every rerun record was bitwise equal to the delivered one (macOS, Python 3.10.12, mpmath 1.3.0, against the delivered
Linux Python 3.13.5 runs). The output is in `replay_local_run.txt` of the drafting folder.

Overruled recommendations: none (no review was made).

### `lri_d3_matrix_update`

Folder: `code/lri_d3_matrix_update/`.

_same as the section above (one text for the whole unit)._

### `LRI_C5_general_d`

Folder: `code/LRI_C5_general_d/`.

#### Reviews of LRI_C5_general_d (note Sections 20 and 21)

This package holds the generic-dimensional reduction of 𝓛_d and Z_d with the reduced C5(d) (note Section 20; Claude
Code session C62d) and the master 𝒦_d at generic d (note Section 21, `K_general/`; Claude Code session C63d).

**Who reviewed.** Every reviewer was a Claude agent, launched as a workflow subagent by session C62d or C63d on
2026-10-02 and 2026-10-03. There was no OpenAI Codex/GPT review and no human referee.

**What ships.** Raw reviewer outputs do not ship: `review/reviews_raw.json`, `review/joint/joint_reviews_raw.json`, and
the workflow transcripts and review folders under `K_general/`. Three kinds of material ship:

- **Two synthesized check reports that the note text cites**, as records:
  - `review/VERIFICATION.md`, the claims table with fixes F1–F23 and O1–O3;
  - `review/lemmaG-proof/review.json`, the verdict record. It is the only record of the numerical tests of that review,
    because those scripts saved no logs.
- **The check code and outputs behind numbers the note quotes:**
  - `review/{foundation-rigor,topmode-numeric,L-rigor,Z-rigor,formula-from-text}/`;
  - `review/lemmaG-numeric/` and `review/lemmaG-proof/*.py`;
  - `review/joint/{numerics-end-to-end,status-consistency,conventions}/`.
- **The cited K_general check files**, listed in the second part below.

##### Section 20 (𝓛_d, Z_d, reduced C5(d); session C62d)

###### 1. Five-lens independent review

Workflow wf_1498e507-418, 2026-10-03, 00:00–02:08. Record: `review/VERIFICATION.md`.

**Lenses:**

| key | lens | method |
|---|---|---|
| FR | foundation-rigor | proofs, checked against brute-force lattice sums |
| TN | topmode-numeric | own 50-digit lattice code |
| LR | L-rigor | |
| ZR | Z-rigor | |
| FT | formula-from-text | sympy rederivation and exact big-integer samples |

**Verdict.** All five ACCEPT: "ready for the note after the listed fixes". No printed formula was wrong. The top-mode
theorem was confirmed at about 50 digits by independent code.

**Errors found:**

- One false intermediate estimate, the endpoint exponent in Steps 3–4 of the top-mode proof (F1). It was corrected, and
  the same strip b < b_max suffices.
- Wrong control numbers in a remark (F2). The true value is 1.7% of the largest mode.

**Other findings:**

- rigor gaps for complex b;
- a missing citation of Pattern T for ∂_bW_3 = 0;
- the wording of 𝔇_L against C63d's P̂′;
- an overcount in the Z inventory (4 → 3);
- status labels.

**What changed.**

- All fixes F1–F23 and O1–O3 were applied by the fix-and-draft workflow wf_a382bd41-c4f.
- A separate fix check, by an agent of that workflow, found every item applied, with one wording slip that was fixed at
  the merge.
- The fix check's record, `review/fixcheck/`, is not shipped; the note no longer cites it (joint-review item G10).

**Caveats.**

- The proof had one full reader and one spot read.
- The corrected Steps 3–4 are the reviewer's own wording. They were re-reviewed later in product form (review 2 below).

###### 2. Proof review of the product-form top-mode theorem

The theorem is gdr:topG, which is foundation Theorem 6(a)–(d). Folder: `review/lemmaG-proof/`.

**Verdict.** ACCEPT, with no fatal or major issue. Every step was rederived by hand. Steps 1–6 were tested numerically in
unbalanced cases: 2e-13 to 2e-8, and 3e-12 in the lower half-plane.

**What changed.** Seven minor wording and documentation items, all applied. They were not re-read after insertion.

**Not covered:**

- C63d's proof text `K_general/note_fragment/topmode/PROOF.md` (merged into the note, not shipped), as such;
- the sharpness of ℍ_q;
- the explicit constants of `K_general/note_fragment/growth/PROOF.md` (merged into the note, not shipped).

###### 3. Numerical probe of gdr:topG

Folder: `review/lemmaG-numeric/`. Independent 48-digit lattice-sum code, run on the symmetry cluster (jobs
569336–569347 and 569461).

**Verdict.** PASS.

**Results:**

- top modes 2.8e-48 to 4.7e-44 at 12 mixed wheels;
- 6.5e-47 to 5.2e-45 at four R kernels;
- at most 9.3e-54 in the 54-digit reruns;
- controls switch on linearly with the per-factor imbalance.

###### 4. Joint review of the Section 20 and Section 21 fragments (gdr + gdk)

Folder: `review/joint/`. Four lenses (status consistency, conventions, end-to-end numerics, note integration) plus a
synthesis.

**Verdict.** "Ready after fixes", with no numerical mismatch:

- 10 major items: 6 for gdr, 1 for gdk, 3 for the note merge;
- about 35 minor items.

**End-to-end results:**

| quantity | agreement |
|---|---|
| C5(1) | 3.2e-34 |
| C5(2) | 2.0e-50 |
| C5(3) | 7.8e-46 |

The code for these sits in `review/joint/numerics-end-to-end/` and is rerun by `make -f public.mk replay`.

**Decisions D1–D6:**

- the layout: two sections pasted inline;
- one home for the product theorem, gdr:topG;
- one copy of the correction to the note's d = 3 section;
- symbol renames;
- one vocabulary for the 𝒦_d conditions (M), (J), (H);
- one review-status statement.

**What changed:**

- The gdr items G1–G16 were applied by C62d.
- The gdk items were applied by C63d (see the second part below).
- The note items N2–N10 were applied in the merge (C63d, 2026-10-03).

**Not applied:**

- G-H, which was needed only for the fallback layout, which was not used.

**Kept against the editorial rule that removes exploratory searches:**

- Section 20.6, "Further reductions tried" (G15), because Section 17 cites it.

The synthesized report `JOINT_REVIEW.md` is not shipped; only a TeX comment of the note cites it.

###### 5. Post-merge check

Session C62d, read-only, 2026-10-03.

- Sections 20–21 equal the final fragments apart from comments.
- An independent build is clean (179 pages).
- `check_note` passes.

Re-verified on 2026-10-13 against note commit fa71533: Section 20 differs from the fragment `general_d.tex` in no
non-comment line.

###### 6. Public-release replay (2026-10-13)

`public/replay.py` runs 115 checks, all PASS. Every number Section 20 quotes for this package is recomputed from the
records at its printed digits, and e2e.py, e2e_k3.py, check_d3.py, check_special.py, check_topG.py and the lemmaG
summaries are rerun.

It found two problems in the note:

- Section 20.7 prints 3·10⁻²¹ as the upper end of the pole-node check, but the record reaches 4.76·10⁻²¹. The text
  change is N9.
- The 10⁻⁵⁷ identity 𝔇_L = P̂′ − … of Section 20.4 had no record. `public/check_DL_Phat.py` now gives 2.2e-65.

###### Recommendations not followed

None in substance. Where reviewers offered options, two choices were made:

- F23: the general-b theorems are stated and proved in Section 20 itself, rather than added to the note's
  periodization appendix.
- G-H: not needed under the layout chosen in D1.

###### Never independently reviewed

- the derivation steps that the fragment only sketches (full derivations in L/, Z/, specialize/; rederived symbolically by
  the review);
- the literal summation of the differentiated pole-node series gdr:taylorLZ (confirmed only through b-derivatives);
- the d = 3 inputs from LRI_C5_d3: the Gamma form of ĉ₀ and the half-shift extension. These are numerical
  confirmations, not proofs (note Section 20.8).

##### Section 21 (𝒦_d, `K_general/`; session C63d)

*This part was written by session C63d (`GFF/d3/K_general_for_C62d/REVIEWS_K_d.md`) and is merged unchanged.*

The dropped folders are:

- `K_general/*verify*`, `R_part_v*`, `refcheck_adv*`, `refverify`;
- `note_fragment/review_*`, `note_fragment/test_build_joint/verify_*`;
- the `workflow_result_raw.json` files.

All reviewers were Claude agents launched as workflow subagents by sessions C63d and C62d. There was no Codex review and
no human referee.

| review | reviewers, rounds | scope | verdict | what changed |
|---|---|---|---|---|
| Workflow wf_cdc3d90c-0ba (2026-10-02) | research agents for the S part, the R part, position space and the reference check, with three adversarial verifiers per claim (`R_part_verify*`, `R_part_vmodes`, `R_part_vnumK`, `S_part_verify`, `refverify`, `refcheck_adv*`, `refcheck_verify*`, `verify_*`) | S closed form, lattice and product forms, sample formula and arrays, finite-mode theorem, position-space representation gdk:KMB, the reference values of `references/reference_values.json`, 100-digit 𝒦_d | three verifiers per item failed to refute the exact items. One verifier refuted the per-spin two-mode periodization; the synthesizer rechecked it with controlled tails (agreement 1e-21..1e-28; at d = 0.8, 1e-11..1e-13). | Interim values were found wrong and superseded before use: 𝒦(1.25) = 17.2251… (relative error 1.3e-3), 𝒦(1.5) (3.8e-16), P4(0.8) (16 good digits) and Q(0.8) (8 good digits). The cause was the per-spin ν-tail with `HPG_NUTAIL=0`. The off-diagonal W3/W4 strings in `reference_values.json` are good to only 50 digits (flagged in `K_general/RESULT.md`). |
| Fragment reviews, three lenses (2026-10-03 03:00–03:14) | rigor (`note_fragment/review_rigor`), numerics (`review_numerics`, own Mathematica and Python checks), consistency (`review_consistency`, three independent test builds); then a recheck of the fixes (rigor and consistency, 12 items) | `note_fragment/K_d_fragment.tex` | fixes required (status labels, (M) as an identity of meromorphic functions, (H), several numbers); the recheck found 12 minor or typo items | Fix round 1 changed the d = 0.8 and d = 2 jets, the Abel–Plana claim at d = 2.75, the per-spin top modes and the position-space contours. Fix round 2 added the d ≤ 4/7 caveat, made r3(1) conditional on (M) only, and set the scope of "order at most three". |
| Joint review of gdr + gdk (2026-10-03; `review/joint/`, C62d's folder) | four lenses (status consistency, conventions, numerics end to end, note integration) and a synthesis | Sections 20 and 21 together, against the note | "Ready after fixes": no fatal issue, no numerical mismatch; for gdk, items K1–K12 (one major: the fragment's own Lemma duplicated gdr:topG); decisions D1–D6 | K1: the Lemma and its proof were deleted; the fragment cites gdr:topG (foundation Theorem 6), whose proof was independently reviewed (`review/lemmaG-proof`, ACCEPT) and probed (`review/lemmaG-numeric`, PASS). K6: r3 column to 34 digits (`check_r3_34.py`); three-node column at d = 1.5, 2.5, 3 from the joint review's circles; "exact" relabelled. Other items: wording and labels. |
| Repair rounds 1 and 2 of the joint-review fixes (2026-10-03 09:47 and 10:05) | Claude verifier agents on the fixed fragment (13 items, then 10 items) | the fixed fragment, `topmode/PROOF.md`, `K_general/RESULT.md` | all items resolved | All jet entries extracted through gdk:Ktau (`check_k3_routes.py`); the "A caution" paragraph quantified (`check_kbracket_d08_huge.py`; the old figure "relative error 0.96" corrected); r3 of 21.8 to 34 digits (`check_r3_special.py`). Then final nits (10:15). |
| Post-merge check (2026-10-03) | session C62d, read-only | note Sections 20 and 21 against the final fragments | PASS: identical up to comments, independent build clean, check_note passes | none |
| Public-release replay (2026-10-13) | `public/replay_K_d.py` (C63d) | every quoted 𝒦_d number of Section 21 | 70/70 PASS; 73/73 with `--recompute` | one body-text correction in 21.10: the "2e-13" of the double-precision identities |

Not independently reviewed, as note Section 21.11 states:

- the sharpness of H_q and the explicit constants of `note_fragment/growth/PROOF.md`;
- the proof text of `note_fragment/topmode/PROOF.md` as such;
- the position-space derivation gdk:MB and gdk:KMB.

Recommendations not acted on: none recorded.

### `LRI_C5_d3`

Folder: `code/LRI_C5_d3/`.

#### Reviews of LRI_C5_d3 (C5(3) and the d = 3 masters)

No raw review transcript is shipped. This file summarizes every review that touched the package's results. All reviewers
were Claude agents: workflow subagents or separate Claude Code sessions. No Codex review and no human referee was involved.

| review | reviewer and form | scope | verdict | what changed |
|---|---|---|---|---|
| Adversarial verification inside workflow wf_d8d88d50-343 (2026-10-02) | Three independent Claude verifier agents per positive claim; each wrote its own code (`wf_V_L3_b4/` and `wf_Z3_gamma_verify/` ship; the dropped folders `wf_vL3*`, `wf_vZ3*`, `wf_Z3verify*`, `wf_K3verify_*`, `wf_spur*`, `wf_verify*`, `wf_vK2deriv`, `wf_k2refute`, ...) | the L3 and Z3 reductions, the general-b wheel and amplitude formulas, S'(3/2), the 430-digit K3, the d = 2 identities L2 = −2 log 2 P4(2) and K2 = 32G² − 28ζ(3) log 2, the by-product Bailey-type identity, and the integer-relation claims | every positive claim confirmed 3/3. The verifiers rejected candidate integer relations as spurious when they failed a second precision. | The final values and formulas in `WORKFLOW_RESULT.md`. A defect of mpmath 1.3 found during the work: `zeta(s, a)` with complex s has an absolute error floor of about 10^−dps. It led to own Euler–Maclaurin Hurwitz sums and to discarding the Z3 circles 567519–567520 and the d = 2 run 1. |
| PSLQ hygiene (2026-10-02, C63d) | session C63d, by its own rule: n·log10(max coefficient) at least ten digits below the established accuracy; a relation counts only if it reappears at a second precision | `pslq_d3.py`, `wf_K3/final_battery.py`, `wf_L3/battery_final.py`, `wf_Z3/pslq_z3.py` | A first search with coefficients up to 10⁵ found only chance relations; the bounds were then set honestly. A 49-term CM L-value relation at 300 digits failed at 420 digits and was rejected. | All "no relation" statements are quoted as bounds in the stated bases, not as proofs of independence. |
| Joint review of the generic-d sections (2026-10-03; LRI_C5_general_d/review/joint) | four Claude reviewer agents (status consistency, conventions, numerics end to end, note integration) and a synthesis | Sections 20 and 21 of the note, including the d = 3 specializations taken from this package | "Ready after fixes", with no numerical mismatch. C5(3) by the generic-d route agrees with `c5_value.json` to 7.8 × 10⁻⁴⁶ and 5.2 × 10⁻⁴⁵. | Status wording only. The d = 3 Gamma form of ĉ0 and the extension of c41 = 2𝔞4𝔟4 to every b < 2 are labelled "derived in LRI_C5_d3, not a written proof" (note 20.8). |
| Independent check of the d = 2 closed forms (2026-10-02, this package for C62d) | `wf_d2check/`, an independent spectral representation | L2 = −2 log 2 P4(2) (70 digits, residual 1.7 × 10⁻⁷⁹) and K2 = 32G² − 28ζ(3) log 2 (59 digits, residual 3.1 × 10⁻⁶²) | confirmed. Both identities were proved afterwards by C62d (note 18.6, 18.7). | It corrected two earlier low-accuracy values that C63d had quoted (P4(2) and K2 at about 10⁻¹¹). |
| Public-release replay (2026-10-13) | `public/replay_c5_d3.py` (this draft) | regeneration of every script output, every quoted number, the printed formulas | 56 PASS, 0 FAIL (`replay_local_run.txt`) | no change to the package |

Recommendations not acted on: none recorded. Open items, as stated in the note and in `WORKFLOW_RESULT.md` §5:
- written proofs of the general-b half-shift steps behind the L3 and Z3 formulas;
- whether 𝔰, 𝔡_H, 𝔡_a or K3 reduce further (a complete level-8 basis for K3 would need about 121 elements and over 1000 digits).

The reviews of the K_d work in `LRI_C5_general_d/K_general/` are summarized in `../K_general_for_C62d/REVIEWS_K_d.md`.

## C6(1) and its analytic representation

### `LRI_C6_1D_HPC`

Folder: `code/LRI_C6_1D_HPC/`.

#### Reviews: C6(1) from exact all-graph sums (`LRI_C6_1D_HPC`)

All reviews ran through the claudex-loop workflow. The host, planner and builder was Claude Code (claude-opus-5-5,
1M context). The reviewer and inspector was Codex CLI 0.158.0 with model gpt-6-astra at effort xhigh, in
read-only mode, as static reviews.

The raw logs and artifacts (`LRI_C6_1D_HPC_loop/PLAN-REVIEW-LOG.md`, `artifacts/`, and the results-review dossier
and log) are not shipped. The plan that was approved ships as `GFF/results/C6_1/PLAN.md`: rev 8 plus the Sec 9
build-phase amendments.

##### 1. Plan review: 8 rounds, APPROVED in round 8 (2026-09-28/29)

| Round | Verdict | Findings | Main subjects |
|---|---|---|---|
| 1 | REVISE | 12 (4 high, 7 medium, 1 low) | assembly file discovery, degree validation, mandatory inputs for a headline, unmeasured L5 rounding, deterministic group order, merge coverage, graph reader, weight self-check, 12−10 diagnostic, perturbation definition |
| 2 | REVISE | 5 (1 high) | provenance between rounding and assembly, pair checks and a weights manifest, light diagnostics from the production vectors, zero-proxy calibration policy, a wrong conditioning claim |
| 3 | REVISE | 5 (1 high) | draft scripts: build naming, fail-fast gate order, concurrent record writes, a single entry point, provisional mode |
| 4 | REVISE | 4 (1 high) | validation evidence bound to code/data identities, approval bypass, node budget, unchecked batch submissions |
| 5 | REVISE | 3 medium | superseded collector restoring approval, queue guard failing open, non-idempotent retries |
| 6 | REVISE | 2 medium | one strict merged-level validator, stranded dependent jobs |
| 7 | REVISE | 1 medium | NaN totals accepted by the validator |
| 8 | **APPROVED** | 0 | "R7-01 is resolved … No additional material defects found in this revision review." |

- **What changed.** Every finding was accepted and fixed in the next revision. Round 1 also brought in a new
  measurement: the binary64 error of the hard stratum grows with N. As a result the design became mixed precision,
  with the hard stratum and all five-loop inputs in long double, and the allowance gained the calibrated rounding
  term ρ.
- **Budget.** The configured limit was 5 rounds. The user allowed a sixth ("One more round") and then rounds 7 and
  8 ("two more rounds").
- **Reviewer limitations, stated at approval.** The review was static. Host-reported test results and the
  cluster validation were not verified independently, and the numerical kernel was not revalidated in the last
  round.

##### 2. Code inspections: 3 rounds, all REVISE, every finding fixed (2026-09-29)

| Inspection | Snapshot | Verdict | Findings |
|---|---|---|---|
| 1 | 33ecb6f | REVISE | REV-001, REV-002 high (an unlocked standalone submitter; validation not isolated from production); REV-003 to REV-005 medium (a non-atomic merge publish; the final report dropped the L5 identities; the resource stopping rules were not recorded) |
| 2 | b67122a | REVISE | REV2-001 to REV2-003 medium (no stopping guard in the standalone submitter; resource evidence unvalidated; reports hashed in a second read) |
| 3 | 88626f1 | REVISE | REV3-001 to REV3-003 medium, all in the resource accounting `c6_resources` (a recovered timeout blocked coverage; task counts not reconciled; requeued attempts hidden without `--duplicates`) |

- **What changed.**
  - Inspection 1 led to one campaign lock and isolated validation attempts, atomic write-once merges, a final
    report that keeps all level identities, and `--resources` and `--decision-dir` in `analyze.py` (commit
    b67122a).
  - Inspection 2 led to the shared continuation guard `c6_require_continuation`, the `coverage_complete`
    evidence, and read-once hashing (88626f1).
  - Inspection 3 led to a rewrite of `c6_resources` from the job ledger with `sacct --duplicates` (b0763b4).
- **Budget.** The configured limit was 2 inspections. The user approved a third.
- **Changes never inspected:**
  - the inspection-3 fixes (b0763b4), by the user's standing choice to fix small findings and report them as
    uninspected;
  - the portable AVX2 / x86-64-v3 engines and the amdq-first routing (38f8847), made at the user's request
    ("prioritize amdq") after the inspections;
  - the V11 tolerance change (8680864);
  - the operator driver `ops/driver.sh`, which is not part of the package.

  All of these were covered empirically by the validation attempt at 8680864, which passed V1–V11. V11 shows that
  AMD and Intel give bitwise-equal double results and long double agreeing to ≤ 1.7e-16.

##### 3. Results review: 2 rounds, APPROVED in round 2 (2026-10-01)

One dossier covered both C6(1) and C7(1).

| Round | Verdict | Findings |
|---|---|---|
| 1 | REVISE | RR-001 medium: rounding of the inherited L2–L4 amplitudes not assessed. RR-002 medium: the "C7 by-product 14331.62 ± 0.31" was a tail-extrapolated value, hardcoded and unlabelled. RR-003 medium and RR-004 low concern C7(1) only |
| 2 | **APPROVED** | "The four prior findings are addressed within the revised empirical and model-dependent scope. The headline arithmetic remains consistent with the committed evidence. No material unresolved defects were found." |

The reviewer reproduced every C6 level value, U = 4.9e-7 and the stopping decision from the committed JSON.

**What changed for C6:**
- **RR-001 (commit cef6fa7).** The lower amplitudes were rerun at degree 28 in long double and in float64 on
  symmetry, and the result was propagated through R6 (`tools/lowercheck.py`, `tools/lowercmp.py`,
  `lower_amplitude_precision/`, REPORT addendum). Long-double rounding is about 2.9e-11 in C6, and U is unchanged.
- **RR-002 (commit ee2e013).** `tools/c7_crosscheck.py` derives three labelled stages from `C7_final.json` and
  binds its inputs by hash: degree 6 at +2.46σ, plus the degree-7 step at +0.97σ, plus the tail at −0.22σ
  (model-dependent). The hardcoded constant was removed from `analyze.py`, and REPORT identifies the old
  `C6_final.json` field as the tail stage.
- **C6 numbers unchanged.** No C6 number changed in either round.

**Reviewer limitations, recorded at approval:**
- the review was static, and the remote records and executables were not reproduced;
- the lower-amplitude long-double error is inferred by roundoff scaling, not measured against a higher-precision
  truth;
- the other C6 rounding proxies are empirical too.

##### 4. Recommendations not applied as written

- **RR-001.** The reviewer proposed comparing the lower amplitudes with a *higher-precision* evaluation. The host
  measured the float64-versus-long-double sensitivity instead, and scaled it by the unit-roundoff ratio 2^-11. The
  reviewer accepted this in round 2 and recorded the limitation above. No Ulow_round term was added to the formula
  for U: it would be 1.2e-10, and U = ceil_2sf(4.8853e-7 + 1.2e-10) stays 4.9e-7.
- **Process limits.** The plan-round and inspection budgets were exceeded with the user's approval, and some
  changes were never inspected (Sec 2). No other finding was declined.

##### 5. This export (2026-10-13)

The public scripts (`public.mk`, `public/`) were written by a C71d helper and were not reviewed by Codex.
`make -f public.mk replay` regenerates every shipped record bitwise. It found one wording error in the condensed
note, Sec 22.4: "from M = 24 onward, successive changes of C6 are below 1e-11". The records give up to 4.35e-9,
which is U5/2. The error is reported in SUMMARY.md, and the replay marks it FLAG.

### `C6_research_note`

Folder: `code/C6_research_note/`.

#### Reviews: analytic representation of C6(1)

##### 1. Independent review, 8 October 2026 (shipped: `GFF/code/LRI_C6_closed_form_review/REVIEW.md`)

- **Reviewer.** Claude Code session C71d, with three independent check agents (Claude). One round; the package was
  not modified. Target: `note/C6_progress_note.tex` (28 pages, sha256 `2f6d7f9d...`), `outputs/reassembly.json` and
  the package's integrity records.
- **Verdict.** No mathematical error found. The value 14331.68703275805432044546... was reproduced independently,
  from the reduced input (eq. 2.7 of the package note) and from the final nine-value formula (eq. 3.5).
- **Checks** (scripts and recorded outputs in `checks/`; replayed by `make -f public.mk replay` there):
  - reduced input re-evaluated from its definitions with the reviewer's own summation codes, at least two methods per
    input: C6(1) to about 65 digits (difference 2e-66), all eight blocks to 69-81 digits;
  - the inherited identities (coefficient series for the sixth- and eighth-power blocks, wheel periodization and core
    identities, the primitive contour relation) hold to 1e-63 or better;
  - the nine final values by separate one-dimensional codes to 40-64 digits, the three bivariate H values as genuine
    two-fold Mellin-Barnes integrals in double precision to 9-14 digits; eq. 3.5 rebuilt from them gives the
    reference to 4e-50 relative;
  - every exact claim of Sections 2-10 and Appendix A (sympy, or numerics at 30+ digits); the Appendix A recurrence
    implemented as printed gives P_a(N=48) equal to the table value to 3e-33;
  - the package's own `audit_package.py` and `audit_final_note.py` pass (on a scratch copy); the TeX builds to 28
    pages without warnings.
- **Most important finding, not in the package note.** The independent all-graph sum (`LRI_C6_1D_HPC`, unrounded
  14331.68703276838, allowance 4.9e-7) lies 1.03e-8 above the representation, 0.021 of the allowance. The source
  repair contributes +659.278983198744; without it the value would be 13672.408. The graph sum therefore confirms the
  corrected reduced input numerically (not a proof).
- **Nature of the result.** A finite formula in nine specified values, not a closed form in standard periods: the
  three bivariate values carry W0, M7 and P_a, for which the package's PSLQ attempt found no reduction; "nine" is a
  packaging count (angle parameters merge pairs of G values; alpha_4 and eta_7 depend on Gamma(1/4), log 2 and pi).
- **Gaps listed (none changes a result).** F1 the Bailey-Mishev representation of U6 used as a black box; F2 the
  supplied identities are not listed in one place; F3 the Euler-weight tail allowance 2^(100-N) is asserted without
  its hypothesis; F4/F4b left contour closures and the H* contour convergence not justified (true numerically); F5-F9
  unclear passages (slope table row 3, Appendix A gives data not derivation, boundary table, two constants); cosmetic
  items; process-style wording and file-path bibliography entries.
- **What changed because of it.** The package was not changed. The condensed note took the review's recommendations
  into its own text: the graph-sum agreement (Sections 1, 1.2, 22.9), the list of supplied identities and the
  conditional status of the enclosure (Section 22.9), and the "nine values describe packaging" caveat.
- **Recommendations not applied.** The fixes F1-F9 and the presentation changes were addressed to the package note;
  no revised package note was produced, so `note/C6_progress_note.tex` ships as delivered.

###### Is REVIEW.md a raw log or a citable report?

It is a citable report: a dated, structured document with a verdict, the list of checks and their results, numbered
findings with line references, and a file index; it is not a transcript of a session and contains no prompts or
tool output. Condensed note Section 33 cites it by path. It is therefore shipped verbatim beside its scripts. It contains
one machine path (`<HOME>/envs/sage/bin/python3`, last line) and the session name C71d; neither is bound by a
checksum, so the path may be scrubbed. **Open question for the author:** keep REVIEW.md as shipped, or replace it by
the summary above.

##### 2. Self-checks of the delivering session (records inside the package)

Not reviews by a second party, listed for completeness: `outputs/package_audit.json` (structural audit: 31 task
records passed, 193 Python files parse), `outputs/final_note_audit.json` (no missing references, 22 protected
equations unchanged), `outputs/final_pdf_qa.json` (all 28 pages inspected), `outputs/portability_check.json` and
`outputs/visual_review.json` (both from the earlier 34-page edition), `provenance/reference_metadata_check.json`
(bibliography metadata). No Codex review of this package or of the review is recorded.

##### 3. Public overlay (2026-10-13)

`public.mk`, `public/verify_c6_analytic.py`, `public/verify_review.py`, `public/rerun_checks.py` were written for the
public release and tested on a scratch export (test and replay PASS in both packages); they have not been reviewed
by a second model.

### `LRI_C6_closed_form_review`

Folder: `code/LRI_C6_closed_form_review/`.

_same as the section above (one text for the whole unit)._

## Finite kernels, power compensation, C6(2) and C6(3)

### `lri_C6_d2_complete_update`

Folder: `code/lri_C6_d2_complete_update/`.

#### Reviews of lri_C6_d2_complete_update (analytic d = 2 power-sector compensation)

The package was written by OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the research bundle (model stated by the author, 2026-10-13), dated 14 September 2026, as the
first complete numerical C6(2) (362.2 +- 2.0, later superseded). The model received the preceding packages of the same
session and built on them: the exact Gamma sector and the classified graph inventory of the two-forest package. On
22 September 2026 it was consolidated, unchanged, into `LRI_complete_research_bundle.zip`. This release ships only the
part that the current C6(2) still uses: the power-sector compensation, the audits that the note cites, and the two-loop
input. No human or later AI edited any shipped file.

| Stage | Reviewer | Rounds | Verdict | What it covered |
|---|---|---|---|---|
| Bundle consolidation (22 Sep 2026) | the same ChatGPT session | 1 | archive hashes OK | Archive-member hashes, the manifest, and saved-data reassembly of the then-latest C6(2) and C6(3). The power-sector scripts were not rerun (bundle `PROVENANCE.md` Sec 4). |
| Code review of the C6(2) HPC package (28 Sep 2026) | Claude Code, 50 agents (six dimensions, refute and impact verifiers) | 1 | numerics sound; no critical or high finding | The HPC package that consumes this package's two-loop input and fixed-point map. The review lists "the retained analytic power-sector compensation and the finite-kernel framework" as shared-framework uncertainties it does not address. |
| C6(2) results review (1 Oct 2026) | OpenAI Codex, gpt-6-astra, effort xhigh | 2 | REVISE, then APPROVED | The C6(2) value, error and provenance. The dossier states that the compensation is inherited and input-hash-verified, "not re-derived or independently validated". The two round-1 findings concerned other note text. |
| C7(2) production (30 Sep 2026) | numerical cross-check, not a review | n/a | consistent | The seventh-order calculation integrates the power sector explicitly. At sixth order its measured power correction is (3.3 +- 11.8)e-4 against the analytic Delta_p of about 1e-33 (pull +0.28; note Sec 28.7). |
| Public-release build (13 Oct 2026) | Claude Code session C62d | 1 | reruns identical; 2 errata | Every shipped check script was rerun on the saved records (`make -f public.mk replay`; 64 rows PASS on two mpmath/sympy stacks). Each output is string-identical to its published record. Two pieces of the counterterm regeneration were rerun as well (sp_ms.py 90, position_ms.py, and position_kite_leaf_ms.py at 32/45/.02 with the shipped kite cache), also identical. Two rounding errors in the note text were found (note_changes.md): 7.39e-30 should be 7.38e-30, and -8.03e-34 should be -8.02e-34. On symmetry (Python 3.12.9, mpmath 1.3.0), test, replay and the warm regen passed string-identically. In the cold regen all 164 kite jets were equal; three diagnostic fields moved at rounding level, and the comparison policy for such fields was relaxed to max(100 x recorded, note bound). A second cold run without gmpy2 moved the vanishing simple pole of L5G121 (about 3e-41) by 7e-58; value fields are now compared at the working precision times the magnitude of their graph entry (CLUSTER_CHECKS.md). |

What was never reviewed:
- the derivation of the bookkeeping identity (done:powerCorrection);
- the split-contour kite factorization and its contour argument (Sec 24.2);
- the scaleless-leaf rule;
- the recursive MS counterterm code (sp_ms.py, position_ms.py, position_kite_leaf_ms.py), beyond the numerical consistency
  checks it records itself (two Cauchy settings, admissible roots, Gamma-only counterterms, the KLT tests).

No recommendation of any review was overruled.

### `lri_C6_d3_complete_update`

Folder: `code/lri_C6_d3_complete_update/`.

_same as the section above (one text for the whole unit)._

### `LRI_C6_D2_HPC`

Folder: `code/LRI_C6_D2_HPC/`.

#### Reviews of LRI_C6_D2_HPC (C6(2), note Sections 24.6 and 33)

The numerical code (kernel, sampler, fixed-point assembly, inputs) and `reference/` (the earlier method-refinement
calculation) were written by OpenAI GPT-6 astra (model stated by the author, 2026-10-13), in a ChatGPT session and delivered on 28 September 2026
as `LRI_C6_D2_HPC_optimized.zip` (git baseline 3e643c8). The same day a Claude Code session reviewed it, made it ready
for SDSC Expanse under OpenAI Codex review (commits 7293480..6aaf656), ran the production on 28 September and wrote the
note text on 1 October; Codex then reviewed the result. Raw review logs and transcripts are not part of the release.

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Code review of the delivery (2026-09-28) | Claude Code, multi-agent (six review dimensions, each finding checked by a refutation and an impact verifier, plus a completeness critic; 50 agents) with native runs on Expanse | 1 | numerics sound, nothing critical or high | 3 medium findings (M1 the executable and inputs hashed once per job but used for every block; M2 assembly did not hash-check the two-loop input B2 and the primitive reference P10; M3 checkpoint-block overheads cap parallel efficiency) and 19 low (Expanse templates, resumable merge, status and recovery, array offsets, seeds, primitive allocation, test gaps, file modes). Verified on Expanse: new and original code agree on all 492 kernels to 8.7e-20 (normalized) with equal fallback counts, end to end to 1.1e-16. Four claims were rejected after verification. |
| Fix plan | OpenAI Codex (gpt-6-astra, effort xhigh) | 5 | APPROVED in round 2; amendment rounds 3–5 REVISE | Round 1: 7 findings (idempotent assembly in merge.sh, archived replay vs the seed guard, self-test net size, --points precedence, Neyman feasibility, reference thresholds, Python >= 3.10), all accepted. Rounds 3–5 reviewed amendments to the recovery tooling (AM1–AM4), all accepted. |
| Code inspections | OpenAI Codex (gpt-6-astra, xhigh), a fresh session each time | 7 | 1–6 REVISE, 7 BLOCKED | 7, 3, 3, 2, 2 and 4 findings, all accepted and fixed (job-private executable, inputs and Sobol nets with recorded digests; submission guards and an sbatch-option allowlist; environment handling of the scripts; one guarded submission path, tools/slurm_submit.py). None concerned the numerics: the production binary stayed byte-identical to the build of the delivered sources (sha256 5818340b...). Inspection 7: R1 (low) status lines did not carry an explicit array size; R2 (medium) no Expanse drill of the final submission layer. |
| After the loop | none | – | – | R1 fixed in 6aaf656 with a regression test; R2 closed by real-Slurm recovery and status-line drills on a personal workstation and then on Expanse (validation records not shipped). |
| Results (2026-10-01) | OpenAI Codex (gpt-6-astra, xhigh) | 2 | APPROVED in round 2 | Round 1 REVISE: C62-001 the 0.0015 projection was described with the wrong scaling (variance 1/n vs SE 1/√n); C62-002 archived Lagrange and delete-one checks of the previous estimator were presented as checks of the new production. Both fixed in the note and the campaign record. Round 2: no findings. The reviewer re-verified the 996 checkpoints and 865,664 task identities, all record, tool and input hashes, the zero C6 projection of the 28 floor-sampled kernels, and the pulls (a/b 0.31, bootstrap ratio 1.002, previous estimator 0.12, C7(2) by-product 0.73). |

Recommendations overruled or decided by the author:
- The plan's acceptance criterion for the independent Kirchhoff point checks (every check relative 1e-9) was amended by
  the author ("amend the criterion and re-review", rather than "report as not met" or "change the numerics"): one point
  of 516, graph L6G160 at scale 1e-130, needs about 395 digits and lies beyond the 300-digit tier; it is required instead
  to equal the original code's value, which it does.
- The plan-review budget (5 rounds) ran out with amendment AM4 reviewed only as code: the author chose to go on to the
  code inspection. The author extended the inspection budget twice (inspections 6 and 7); the fix rounds exceeded their
  budget by two.
- The author chose the variance-based (Neyman) split of the primitive budget, hashed per-group seeds, and the
  validation scope (tests, smoke run, throughput pilot).
- The quoted allowance: the four-SE rule was written before the result; after it, the author changed the rounding step
  from 0.01 to 0.001 (disclosed in note Section 24.6).

What was never reviewed:
- the two last code changes (6aaf656, the status-line fix of R1, and the drill evidence) by any Codex inspection;
- the inherited physics: the graph and renormalization framework and the analytic power-sector compensation (the note
  says so; the seventh-order calculation, which integrates the power sector explicitly, checks the latter at sixth order);
- the four defects of the submission and merge layer found on 29 September by the review of the three-dimensional sibling
  package (no submission lock, a concurrent-merge crash, an unescaped SQLite URI, `%` in Slurm log paths). They are fixed
  there, not here; the production was not affected (see `GFF/results/C6_2/CAMPAIGN.md`). The release ships the code as it
  ran and only warns.

### `LRI_C6_D3_HPC`

Folder: `code/LRI_C6_D3_HPC/`.

#### Reviews of the C6(3) package and result

There were three independent reviews: of the delivered code, of the plan and code for production, and of the result.
The raw logs, transcripts and reviewer artifacts are not published; this file summarizes them.
- Reviewers: Claude (Anthropic) sessions and OpenAI Codex CLI 0.158.0 with `--model gpt-6-astra --effort xhigh`.
- Every Codex review was static (read-only).
- There was no human referee.

##### 1. Review of the delivered package (2026-09-28)

**Reviewers.** Three read-only Claude reviewers:
1. the d=3 kernel against the reference code;
2. the assembly and inputs against the archived d=3 derivation;
3. a map of the C6(2) review findings onto this port.

There were also runs on a project workstation (Slurm jobs 946–951).

**Verdict.** The d=3 numerics are sound; nothing critical or high was found.
- **Kernel.** The worker computes the same integrand, measure and precision fallbacks as the original code built with
  `-DSPATIAL_D=3`. This was checked line by line in all three precision tiers.
- **Graph files.** They equal the forest and rate inputs token for token.
- **Archived streams.** Replaying the eight archived production streams (385,744,896 samples) gives equal fallback
  counts, per-graph jets equal to 2.2e-13, and the published refinement-only C6(3) = 33.560840352429125 bit for bit.
- **Assembly.** It is a line-for-line copy of the archived one. B2 matches an independent 85-digit record to 1e-54.

**Findings.**
- Carried over from the C6(2) review:
  - M1: binary and inputs hashed once for all blocks;
  - M2: unverified assembly inputs;
  - M3: the block structure caps efficiency;
  - L1–L19: Slurm templates, resumability, recovery, seed hygiene, tests rewriting evidence, file modes, and others.
- New for d=3:
  - D3-1 (medium): legacy seed arithmetic could replay archived streams;
  - D3-2 (medium): `--primitive-points` would destroy the variance-based allocation;
  - D3-3 (low): no regression test of the assembly on archived data;
  - D3-4 (low): the 300-digit tier was effectively untested. 515 of 516 relative point checks pass; the exception
    (graph L6G160 at scale 1e-130, 395 digits of cancellation) is identical to the original code.
  - D3-5 (low): untested layouts and branches;
  - D3-6 (info): zero-weight graphs, and the lower-order pull gate needs care.

**Author decisions.**
- Remove `--primitive-points` and keep the frozen allocation.
- Use hashed seeds, and in legacy mode refuse every archived seed.
- Apply the C6(2) rule to the single point beyond the 300-digit tier.
- Validation: the tests, the archived-stream replay, an Expanse smoke campaign, recovery and status drills, and a
  throughput pilot.

**Overruled recommendation.** The review suggested optional per-loop multipliers (1, 4, 2, 1), worth about 18% of
CPU at equal SE. The author chose a single multiplier and kept the frozen cross-loop split (plan decision D7).

##### 2. Production readiness: claudex loop (2026-09-28)

Roles: Claude (Opus 5.5) planned and built; Codex gpt-6-astra reviewed the plan and inspected the code, each time in
a fresh session.

| round | verdict | findings | what changed |
|---|---|---|---|
| plan review 1 | REVISE | R1 (medium): no campaign-level serialization of submit/resubmit; concurrent merges collide. R2 (medium): an unescaped path in the SQLite URI. | Per-campaign submission lock, concurrent-safe merge, URI-safe database open |
| plan review 2 | **APPROVED** (plan sha256 14c089fa…) | none | — |
| inspection 1 (b3bdbb0) | REVISE | R-SLURM-01: `%` in `--output`. R-LOCK-02: lock left behind after an `owner.json` failure. R-MODE-03: 0600 input files. R-DOC-04: docs claimed pending Expanse evidence. | Fix round 1 (`382e752`) |
| inspection 2 (0fef6b8) | REVISE | R-PKG-05: checksum list omitted 98 evidence files. R-VAL-06: the Expanse validation ran on the compute partition instead of the planned shared partition. R-DOC-07: sample count. | Fix round 2 (`d3fb81d`); the calibration (`73d3635`) and the whole validation redone on the shared partition (job 54510646, smoke, drills, pilot); the compute-partition runs kept as a cross-check |
| inspection 3 (1c6dfb3) | **APPROVED** | none | — |

- The production ran `1c6dfb3`. There were no uninspected edits after the approval.
- The binary built from the final sources is byte-identical to the delivered one: `e22809aa…` on a workstation and
  `2f897044…` on Expanse.
- The reviewer stated these limits:
  - the review was static, and results and binary identity were judged from the saved records;
  - the remote campaign databases were not available to it;
  - the L6G160 exception was not rederived.
- The reviewer's Codex configuration kept a write-capable MCP server enabled (the author's earlier choice), and the
  reviewer was instructed to stay read-only.

##### 3. Results review of C6(3) = 33.5754 ± 0.0005 (2026-10-01)

Reviewer: Codex gpt-6-astra, review mode. Coordinator: Claude. The claim was the result after Amendment 1.

- **Round 1: REVISE**, two low findings: "Static inspection identified no defect requiring a change to C6 or its
  stated sampling allowance."
  - C6-REPORT-01: "RQMC does better than 1/N" is unsupported, because the projection scales as 1/√N.
  - C6-REPORT-02: the C4 pull is −1.09, not −1.10.
  - The reviewer confirmed:
    - 4 × SE = 0.000474… → 0.0005;
    - all eight allocations equal the frozen tables × 8192;
    - the 64 replicates, the coordinate widths and the equal weights;
    - every production hash.
- **Changes.** Both findings were accepted. A dated Errata section was appended to `CAMPAIGN.md` (the original text is
  kept), and the note's sentence was corrected. The coordinator recomputed the estimator from the merged records on
  Apple arm64: it agrees with `C6_result.json` to 1 ulp.
- **Round 2: APPROVED.** "Both prior findings are resolved by the dated errata. No material unresolved defect was
  identified. C6(3) = 33.5754 ± 0.0005 is supported within its explicitly stated empirical sampling-only scope."
- **Limits** stated by the reviewer:
  - the coordinator's recomputation was not reproduced;
  - the raw checkpoints were not re-merged;
  - the analytic compensation and the framework were not re-derived;
  - digital resolution is controlled only empirically (52 vs 60 bits);
  - the preregistration chronology and the thread-identity check rest on the written log.

The public replay (`make -f public.mk replay`) recomputes the estimator and every quoted number from the merged
records. `make -f public.mk replay-full` (not yet run) re-merges the checkpoints from the hosted tarball and would
close the second limit.

##### 4. Known open points

- **Amendment 1 was post hoc.** It changed the rounding step after the result was known. Under the registered step the
  allowance is ±0.001.
- **Thread identity.** The 64- vs 16-thread identity check (141,994 binary128 promotions) is documented only in
  `CAMPAIGN.md`; its logs stayed on the cluster.
- **Scope.** The allowance is sampling-only. The analytic power-sector compensation and the finite-MOM framework are
  taken over from the reference calculation and not redone. The independent C7(3) by-product (−0.79σ) shares that
  framework.

## Full C7(1), C7(2), C7(3)

### `LRI_C7_HPC`

Folder: `code/LRI_C7_HPC/`.

#### Reviews of LRI_C7_HPC and of the C7(1) result

Summary of three review processes. The raw logs, plans and reviewer outputs are not published.

##### 0. First review of the delivered package (2026-09-25)

- **Reviewer:** Claude Code (Claude Opus 5.5), multi-agent review with live tests on a personal desktop and an Expanse
  launch probe.
- **Result:** 41 verified findings, which became the fix list of the plan below. The high-severity one was the Slurm
  launch: on Slurm 22.05–23.02 the `srun` step did not inherit the job's CPUs per task, so every OpenMP thread ran on
  one CPU (effective parallelism 0.99 of 8 threads on Expanse). Others concerned build portability, checkpoint
  integrity (no content digest, silent default index, no coverage check at merge), missing production tooling for
  independent batches, and documentation errors (srun statement, replay-record provenance, benchmark weighting).

##### 1. Code plan and inspections (claudex-loop, 2026-09-25 to 2026-09-26)

- **Roles:** host, planner and builder: Claude Code (Claude Opus 5.5) with Claude helper agents. Plan reviewer and
  inspector: Codex CLI 0.157.0, model gpt-6-astra, effort xhigh (fast mode from inspection 2). Every inspection used a
  fresh Codex session. The reviewer had a write-capable REPL tool enabled by the user's explicit choice and was
  instructed to stay read-only.
- **Plan (fix the package, add a degree 6→7 check, run fresh-seed batches on Expanse):** round 1 REVISE (12 findings:
  5 high, 7 medium), round 2 REVISE (3: 1 high, 1 medium, 1 low), round 3 **APPROVED** with no findings. All findings
  were accepted.
- **Acceptance criteria:** A1 `make test` on a personal desktop and Expanse PASS; A2 kernels bitwise identical to the delivered source
  (23 workloads, 0 differing rows, on a personal desktop and Expanse) PASS; A3 archived reassembly reproduced exactly, diagnostics to
  2e-15 PASS; A4 launch fix proven (15.74 of 16 CPUs effective) PASS; **A5 NOT MET** (see below); A6 pilot PASS;
  A7 production PASS.
- **Inspections:**
  1. REVISE, 6 findings (primitive-sector guard, quarantine/merge interplay, an explicit accuracy criterion in
     `check_quad.py`, estimator-only design prediction, template strict mode, checksum list). Fixed.
  2. REVISE, 3 findings (verify must rebuild coverage, design must reject non-unit pilot multipliers, primitive-class
     metadata). Commit **3213ce0** is the state this inspection covered, including the round-1 fixes; the production
     workers ran a frozen copy of it. The three fixes came after it.
  3. (Quota raised from 2 to 5 inspections by the user.) REVISE, 3 findings: accuracy must be judged per element, not
     by slot maxima; the rounding-floor exception was not in the approved plan; the design accepted incomplete pilots.
     Fixed. The per-element evaluation showed that the optimized power quadrature is less accurate than the original
     on 9 of 112 degree-7 replay elements (worst 18×, 4.2e-14 relative), although its aggregate projected C7 error is
     smaller (2.8e-12 against 1.9e-11).
  4. REVISE: A5 (acknowledged, no code change, see below) and two design-validation findings (fixed).
  5. REVISE: A5 (acknowledged) and three validation findings (exact pilot counts, source identity, missing archived
     variances), fixed in a fifth fix round that is **uninspected** (inspection budget exhausted). Commit 3129a97 holds
     fix rounds 2–5; the frozen design reproduces byte-identically under every version.
- **Recommendation not adopted:** the element-wise accuracy criterion A5. By the user's decision (2026-09-26) it is
  reported as not met instead of being amended; the strict criterion stays the default gate of `check_quad.py`, and
  the rounding-floor criterion (whose 64·2^-64 threshold was chosen after seeing the data, as the log discloses) is a
  diagnostic only. The deviations are about 1e-10 of the sampling noise.

##### 2. Direct primitive campaign and parallel combine (PLAN2, 2026-09-26)

- **Roles:** as above (Claude builds, Codex gpt-6-astra xhigh reviews and inspects).
- **Plan:** round 1 REVISE (4 findings, 1 high: source metadata must be bound to verified manifests), round 2 REVISE
  (archived power records lack counts), round 3 REVISE (high: the guarded primitive sector is primitive && !power,
  44 classes, not the 64 raw flags), round 4 **APPROVED**.
- **Inspections:** 1 REVISE (2 high: primitive inputs not compared with the batches; class support read from the merged
  file instead of the manifest; 1 medium: the baseline test needed git history), fixed; 2 REVISE (1 high: a mixed
  archived/direct assembly did not bind a new campaign's Gamma input to the authenticated archive), fixed;
  3 **APPROVED**, committed as b0d2cd3; 4 (the added `combine.py --jobs`, byte-identical output) **APPROVED**, committed
  as **7320afc**, the code of the final combination.

##### 3. Results review (2026-10-01)

- **Reviewer:** Codex CLI, gpt-6-astra, effort xhigh, read-only, on a results dossier for C6(1) and C7(1) prepared by
  Claude Code.
- **Round 1 REVISE**, 4 findings, all accepted: input rounding of the C6 lower amplitudes (measured, allowance
  unchanged); an unlabelled C7 by-product in the C6 report; **C7 overclaim**: ±41 is the registered policy output, not
  a total accuracy, since it does not add the modelled truncation bias to the sampling error; combination wording. The
  C7 report was revised (commit 68dc6be): conditional-consistency wording and the post hoc truncation-aware estimate
  −322524 ± 38 shown alongside.
- **Round 2 APPROVED.** Reviewer limitations, recorded: static review, remote records and executables not reproduced;
  the 100 % tail-model uncertainty has no established coverage; first-order propagation through the data-derived tail
  gives 18.8 instead of 18.6 (the doubled value stays 38); the A5 failure and the absence of degree-8 data remain, so
  the approval does not establish the total C7 accuracy at the ±40 level.

##### 4. Public export (2026-10-13)

The public replay scripts (`public/replay7.py`, `public/replay7_full.py`, `public/make_data_archive.py`) were written
by a Claude Code helper session for this export. They have not been reviewed by Codex. Tier 1 was run (214 checks,
no FAIL); Tier 2 has not been run yet.

Update 2026-10-14: the archive was built and Tier 2 run on Expanse on 2026-10-13 (Slurm job 54901438, by C71d):
`make_data_archive.py` selected 35,115 files and checked 14,365 merged streams against `C7_final.json`; Tier 2, run from
the unpacked tarball, passed all 14 checks (`combined_assembly.json` and `C7_final.json` byte-identical, C7_full,
sampling and bootstrap SE, half splits, 399 per-batch results). On 2026-10-14 it was repeated from the export on symmetry:
byte-identical on Intel; on AMD two fields that assemble.py forms as differences of nearly equal numbers missed the
1e-12 self-relative tolerance (by 1.6e-12 and 2.7e-12), so replay7_full.py now compares those two to 1e-12 of their
inputs, and the AMD rerun passed. That change is not Codex-reviewed. These are runs, not reviews.

### `LRI_C7_D2_HPC`

Folder: `code/LRI_C7_D2_HPC/`.

#### Reviews of LRI_C7_D2_HPC (full C7(2), note Section 28)

The package was written by OpenAI GPT-6 astra (model stated by the author, 2026-10-13), in a ChatGPT session and delivered on 2026-09-30 as an
optimized, restartable reimplementation of that model's earlier two-dimensional seventh-order calculation, which it
carries unchanged under `reference/`. A Claude Code session (C62d) committed it unchanged as git commit `fb64c47`, built
and tested it on the production cluster, and ran the production with it on 2026-09-30. Three reviews followed. No raw
review log or transcript is shipped.

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Code review of the delivered package (`fb64c47`), 2026-09-30, in parallel with the production | Claude Code multi-agent workflow (72 agents: kernel, sampler, assembly, orchestration, inputs and tests, cluster use; every finding checked by independent refute and impact verifiers; a completeness critic) | 1 | Numerics sound; no critical or high finding; 4 medium and 21 low findings; GO for the running production | Nothing in the code that ran. The production was judged with manual lower-order pulls, as the review asked (finding M2). |
| Results review of the production, 2026-10-01 | OpenAI Codex (model gpt-6-astra, reasoning effort xhigh), claudex-loop review mode, on a dossier of the result | 1 of 5 | APPROVED, no findings | Nothing. Codex rebuilt all 1,275,008 task rows of the 2,048 checkpoints with Decimal arithmetic (1,094,688,178,176 samples, no gap or overlap), checked the hashes of all 20 groups and of the 3,511 packed kernels against the reference files, reconstructed C7 = -3876.126092794993 with sampling SE 0.524449669095692 and every pull, and found no sign of heavy tails (largest standardized replicate deviations 2.72 and 2.88 in the dominant groups). It called +-2.1 "defensible as an empirical four-SE allowance, not a certified error bound". |
| Fix loop on the package, 2026-10-01/02 (`fb64c47` -> code `3cef517`, evidence `a55958f`) | Plan and code: Claude Code (C62d and a builder subagent); plan review and code inspection: OpenAI Codex (gpt-6-astra, xhigh), each inspection in a fresh session; host review: Claude Code workflow (42 agents) | plan 4, inspections 3 | Plan APPROVED in round 4; host review 1 medium and 27 low; inspections REVISE (5 findings), REVISE (2 findings), APPROVED in round 3 | Job-handling layer (status, recovery, guarded submission with a lock, resumable merge), opt-in allocation flags, lower-order pulls in the result, build records, tests. **Not part of this release**: the production ran `fb64c47`, and the revised tools refuse campaigns planned by `fb64c47`. Its only change to `src/` is one line that lets the kernel compile with Boost 1.66; with Boost 1.77 the binaries of both commits are byte-identical to the production binaries (checked four times on the production cluster). |

Findings of the code review that were not acted on for the production, and why:
- M1 (the power sector takes 55-62% of the CPU for under 1% of the variance) and M3 (the 44 primitive classes get a flat
  allocation): the production had already been planned with the delivered defaults when the review reported; changing the
  allocation would only have saved cost, not changed the estimator. The review estimated SE 0.45-0.5 instead of about 0.7
  for the same cost; the production reached 0.52.
- M2 (the emitted lower-order checks carry no pull and compare C6 with the old archived value 362.3489 +- 0.153): the
  record `C7_result.json` keeps that block as written (it is hash-bound); the note's pulls are computed against the C6(2)
  production and are recomputed by `make -f public.mk replay`.
- M4 and the 21 low findings concern throughput and orchestration; the fix loop addressed them in code that is not shipped.

Deviations in the fix loop: one acceptance criterion assumed the delivered kernel fails with Boost 1.86; the host found
that the failure seen on one cluster came from the system Boost 1.66 (the Boost 1.86 module there sets no include path),
so the criterion could not be met as written and the documentation was corrected instead. The builder used a deferred
signal handler instead of `pthread_sigmask`, which a child process would inherit. Deferred test-strength items (HR17,
HR19-HR23, HR25, HR27, HR28) remain open in that unshipped revision.

What was never reviewed:
- the graph construction, the local mass subtraction and the renormalization argument, which this package inherits from
  the earlier calculation (its method note is merged into note Section 28); the reviews checked the software against that
  construction, and the note's checks (three-loop analytic value, lower orders) share it;
- the native kernel beyond reading and the package's own bitwise and point checks (no reviewer built it; the coordinator
  ran the builds and tests on the clusters);
- the bootstrap regeneration (the results review inspected the stored bootstrap; `make -f public.mk replay` now regenerates
  it).

### `LRI_C7_D3_HPC`

Folder: `code/LRI_C7_D3_HPC/`.

#### C7(3): reviews

Summary of every review of the C7(3) code and result. The raw review logs, transcripts and loop folders are not
published; this file replaces them. Reviewers were AI systems: Claude (Anthropic) subagents and OpenAI Codex
(gpt-6-astra, reasoning effort xhigh). There was no human referee. The coordinator in every case was a Claude Code
session (C63d). Dates are 2026, times EDT.

| # | what | reviewer | rounds | verdict | date |
|---|---|---|---|---|---|
| 1 | delivered package before and during production | three read-only Claude subagents | 1 | GO (numerics sound) | 30 Sep |
| 2 | fix-loop plan for a symmetry-ready package | Codex | 3 | APPROVED (round 3) | 1 Oct |
| 3 | fix-loop code (the symmetry-ready package) | Codex, a fresh session each round | 5 | APPROVED (round 5, c71cc56) | 1 Oct |
| 4 | the result C7(3) = -220.35 +- 0.13 | Codex | 2 | APPROVED (round 2) | 1 Oct |

##### 1. Code review of the delivered package (GO)

- **Scope.** The package as delivered (`code/LRI_C7_D3_HPC`, local git baseline 4de9412; `verify_delivery --strict`
  passed on 4,909 payload files). The user chose a focused review running alongside production: one reviewer for the d=3
  kernel against the original d=3 code, one for assembly, inputs and sizing, and one mapping the 25 findings of the
  earlier C7(2) review onto the d=3 port.
- **Verdict (30 Sep, 18:05, before the campaign finished).** The d=3 numerics are sound; nothing biases the result;
  GO for the running campaign, to be judged with manual gates.
- **Evidence** (symmetry cluster):
  - build and delivered tests, job 566376: all seven suites pass; thread identity 5,776 rows, 0 mismatches
    (`results/C7_3/evidence/buildtest-566376.out`);
  - AMD vs Intel, job 566410: same rows and promotion counts, values differ by at most 2.0e-11 normalized
    (`evidence/intelcheck-566410.out`; the maximum is recorded in `CAMPAIGN.md`);
  - archived-stream replay, job 566411: all 168,528 archived rows of the previous calculation reproduce, 162,044 bit for
    bit and the rest within 1.0e-11; promotion counts identical in all 20 groups; the previous C7(3) rebuilt as
    -227.61810947469922 against the published -227.61810947469945 (`evidence/replay_report.json`; script
    `code/LRI_C7_D3_HPC/public/replay_archived.py`, rerun with `make -f public.mk archived-replay`);
  - an independent mpmath re-implementation of the sampler and integrand reproduced 13 archived rows across L3-L7 and
    both sectors: free rows to 1e-17-1e-19, power rows to <= 9e-13 (script `public/indep_rows.py`; the row list was
    not archived);
  - line-by-line check of every dimension-dependent expression of `src/kernel.hpp`; `src/` is byte-identical to
    `reference/src/`; `gamma_d3_7.txt` recomputed to 4e-58; rate tables recomputed for 140 graphs; all 3,511 pack
    members byte-identical to `reference/inputs`; reassembly of the archived records reproduces the archive to 4e-13.
- **Findings and what changed.**
  - D3-1 (info): results are not bit-reproducible across CPU types (glibc long-double transcendental functions); about
    1e-7 of the relative statistical error. Recorded per index in the claims; documented in `CAMPAIGN.md`.
  - D3-2 (medium): the package had no independent physics test of the d=3 port. The replay above is that test; it ships
    as `public/replay_archived.py` with its record.
  - D3-3 (medium): the delivered assembly's C6 reference (33.5682) is stale and it emits no pulls. Production was judged
    with manual gates against the new C6(3) = 33.57543 +- 0.00012 (the reporting rule in `CAMPAIGN.md`); the fix loop
    made them the package's scored gates (`reverify_a6ce987`).
  - D3-4 (medium): flat allocation of the 44 seven-loop primitive classes. Production used `--primitive-points 1024` (a
    plan flag; 1.1% of the CPU for 0.4% of the variance) instead of the default 16384. It changes only the variance.
  - Carried over from C7(2): M1 (power sector over-allocated) does not apply in d=3; M4 (idle cores at block barriers)
    applies (about 0.96 utilisation); the 21 low findings (merge not resumable, Slurm templates, seed hygiene, Boost
    >= 1.86 fails, and others) apply and were handled operationally. None biases a correctly run campaign.

##### 2-3. Codex fix loop: the symmetry-ready package (APPROVED)

- **Request.** The user asked for a Codex fix loop "for the C7(3) results", with decisions: fix every finding by porting
  the reviewed C6(3) design; native numerics frozen; frozen Neyman counts for the primitives; lane mode for exclusive
  nodes plus a read-only report tool; Boost documented only. Claude planned and built; Codex reviewed and inspected.
- **Plan review.** Round 1 REVISE (5 findings, 2 high: report scope; assembly inputs not bound to the campaign's inputs
  manifest), round 2 REVISE (3 medium), round 3 APPROVED. All findings accepted.
- **Code inspection** (a fresh Codex session each round): round 1 REVISE with 10 findings (2 high: retained primitives
  could be counted twice with `--points`; the rounding tolerance ignored most floats), round 2 REVISE with 4, round 3
  REVISE with 2, round 4 REVISE with 1, round 5 APPROVED with 0 findings at c71cc56 (code bb9d2ca). Every finding was
  accepted and fixed; symmetry validation jobs 567149, 567180, 567184, 567197 passed after each fix round.
- **What ships from it.** Only the read-only re-verifier: `code/LRI_C7_D3_HPC/reverify_a6ce987/` (`tools/report.py`,
  `assemble.py`, `common.py`, the gate references and run1's cost model, at a6ce987). It re-verified run1 bitwise on
  symmetry with the gates of `CAMPAIGN.md` (`results/C7_3/run1_report_bb9d2ca.json`, job 567197).
  `src/`, `inputs/` and `reference/` are byte-identical to the production commit.
- **Not verified by the reviewer.** Static review: live Slurm and BeeGFS behaviour, and Intel lane execution, were not
  exercised; the physics was not re-derived.

##### 4. Codex results review of C7(3) = -220.35 +- 0.13 (APPROVED)

- **Round 1: REVISE**, two low findings, neither changing the result.
  - C7-RESULT-01: the dossier said run1's group seeds were hashed; the delivered planner uses arithmetic offsets from one
    base seed. The dossier was corrected (`public/replay_C7_3.py` checks the offsets, row `n.seed`).
  - C7-RESULT-02: the package flagged the archived value by the combined pull instead of the rule's "3 archived SE".
    Fixed in commit a6ce987 with a regression test; run1's gates are unchanged (+1.90 archived SE, no flags). This commit
    had no separate Codex code inspection; the round-2 reviewer inspected its diff.
- **Round 2: APPROVED.** "C7(3) = -220.35 +- 0.13 is supported within its stated empirical sampling-only scope."
- **Reviewer coverage.** All 7,022 allocation entries and the sample total; the identities of the manifest, configs,
  merged files and archive; three production checkpoints; the seed, sampling, promotion, merge, covariance, bootstrap and
  reporting paths. Limitation: static; the reviewer did not recompute the estimator (`make replay` now does).

##### Reporting rule

The coordinator wrote the rule (estimator with sampling SE; allowance four SE rounded up to 0.01; gates on the a/b
campaigns, bootstrap, archived value, C3-C6 and the power differences) at launch, before any result, in
`results/C7_3/CAMPAIGN.md`. The user confirmed it unchanged on 1 Oct, after the result was known. The same file carries an
erratum written before the results review: a caveat about a retained analytic power compensation, copied from C6(3), was
wrong (both sectors are integrated explicitly), and the flat seven-loop primitive allocation is clarified.

##### Overruled or open recommendations

- None overruled.
- Open: the archived replay ran only on AMD EPYC 7532; an Intel lane run of the symmetry-ready tooling was never
  exercised (not used for the result). As in C7(1), a quadrature-truncation effect, if present in d=3, is outside the
  sampling allowance (`CAMPAIGN.md`, reporting rule item 4).

## Full C8(1), C8(2), C8(3) and the independent checks

### `LRI_C8_HPC`

Folder: `code/LRI_C8_HPC/`.

#### REVIEWS: LRI_C8_HPC (C8(1), one-dimensional long-range Ising model, eighth order)

This file summarizes every independent review of the package. The raw review logs, transcripts and runner outputs
are not published, so this summary replaces them. Finding identifiers (C8-R01, A1-R2-03, ...) are the original ones.
They match the commit messages and the per-round disposition tables in `docs/EXTENSION_A1.md`, `EXTENSION_A2.md` and
`EXTENSION_A3.md`, which ship with the code.

**Setup common to all stages.** The package author and coordinator was a Claude Code session. It wrote the code, the
amendments and every fix. The reviewer was OpenAI's Codex CLI in a read-only sandbox. Every round requested model
`gpt-6-astra` at reasoning effort `xhigh`. The runner did not record which model actually served a round (its
observed-model field is empty in all 45 rounds), so the served model is "not recorded". Each code or amendment
inspection round was a fresh Codex session. It saw the plan plus every changed file against a fixed base commit. The
results review used one session (round 1), resumed for rounds 2 to 4. All reviews were static: the reviewers ran no
tests, numerics or jobs, and they did not inspect live cluster state or checkpoints. The approvals say this in their
stated limitations. The reviewed commit of each round was identified from the runner snapshot, which lists the
SHA-256 of every reviewed file. These hashes equal the files of the named commit (checked with git for every amendment
round and for code rounds 1, 8, 9 and 10). For the code inspection, the `c8-review` branch also names each round's tree.

##### 1. Stages

| Stage | Dates (2026) | Reviewer | Rounds | Final verdict | Reviewed commit / plan SHA-256 | Findings |
|---|---|---|---|---|---|---|
| Code inspection of the C8 package (plan `PLAN.md`, base bbb3338 = C7 package + verified C8 inventory) | 10-02 | Codex CLI 0.158.0; gpt-6-astra, xhigh requested; served model not recorded | 10 | APPROVED r8 (1c9a6f3); after post-approval changes REVISE r9, APPROVED r10 | c0ffa63 (production code); PLAN.md 7dbf2469… | 26 (10 high, 15 medium, 1 low) |
| Amendment A1: extension batches b5–b14 on symmetry (`docs/EXTENSION_A1.md`, base 78e6a8a) | 10-10 | Codex CLI 0.162, Fast mode; gpt-6-astra, xhigh requested; served model not recorded | 12 | APPROVED r12 | 15a110e; plan 7efa851c… | 38 (8 high, 27 medium, 3 low) |
| Amendment A2: complete b10–b14 in a second wave (`docs/EXTENSION_A2.md`, base 15a110e) | 10-12 | as A1 | 9 | APPROVED r9 | 4adf719; plan 3f958f71… | 15 (7 high, 7 medium, 1 low) |
| Amendment A3: b12–b14 on Expanse (`docs/EXTENSION_A3.md`, base 4adf719) | 10-12 | as A1 | 10 | APPROVED r6 (eb25c8e); after the early-export change REVISE r7–r9, APPROVED r10 | bd13a63; plan 1cb32f78… | 27 (2 high, 25 medium): 19 before r6, 8 after |
| Results review of the K = 14 result (dossier `RESULTS_REVIEW.md`) | 10-13 | as A1 | 4 | APPROVED r4 | dossier rev 4 a5a3e5cf…; REPORT.md at 1282e37 (r1 read HEAD 9dd3a6b) | 8 (4 medium, 4 low) |

In total there were 45 rounds and 114 findings. Every finding was accepted (Section 3 gives the exceptions in how
they were resolved).

##### 2. Findings and what changed

**Code inspection.** The rounds reviewed these trees (findings in brackets): r1 d9f300b (11), r2 3c29000 (4),
r3 8b5a690 (3), r4 0f4ff50 (3), r5 f57a3c1 (1), r6 b195a0c (2), r7 6c048f0 (1), r8 1c9a6f3 (0, APPROVED),
r9 5ff54ae (1), r10 c0ffa63 (0, APPROVED).
- Assembly completeness and binding (R01, R02, R06, R19, R21, R23). Fixed list of sampled loops and levels, including
  the 8→9 check. One canonical level/degree table. Exact inputs must be complete. The loop-5 input is frozen in the
  design. Loop 5 runs in one campaign only. A final combination needs the frozen batch count, and partial results are
  labelled as partial.
- Input and design integrity (R03, R08, R12, R16). Input hashes must be identical across sources. The frozen pilot
  input hashes are enforced at planning and at assembly. The design bundle is written atomically with digests and
  re-verified at final assembly.
- Independence of random streams (R04, R13). Pilot and control-training seeds are forbidden in production, and a seed
  shared by two campaigns is rejected.
- Budget and work sizing (R09, R14, R17, R26). Integer allocation under the budget. Costs are in allocated core-hours
  from the measured pilot efficiency over all submission attempts. Power-mode tasks have a bounded length.
- Failure propagation (R05, R07, R10, R11, R15, R20). Long-double test output is parsed exactly as Decimal (the
  validation was rerun on Expanse and all checks passed). Failed checks give nonzero exits. The weights job derives
  every required degree from the designs and checks each child process. Deterministic campaigns are merged before
  the affine map. The weight files generated earlier were kept: all required files exist and are hash-bound in every
  campaign manifest.
- Code defects and documentation (R22, R24, R25, R18). An uninitialized variable on the assembly path; an unreachable
  assignment in the combiner; a bootstrap whose memory is now bounded by resampling only the C8 column in blocks; a
  new C8 README, with the C7 documents moved to a historical folder.
- After approval r8, running `design8` on the real pilot asked for an infeasible number of replicates. Commit 5ff54ae
  split the multiplier into replicates and a sample multiplier. It also added a QMC per-graph point floor, because
  the pilot's L7 QMC distribution at 64 points per graph was skewed. Round 9 found unbounded power tasks (R26), fixed
  in c0ffa63, which round 10 approved.

**Amendment A1.** Rounds: r1 79d348b (8), r2 769dd4a (7), r3 ad373bd (5), r4 cb86c79 (3), r5 527f72f (4),
r6 8a84105 (3), r7 2413ec0 (2), r8 91fd099 (2), r9 da0aad0 (1), r10 2ed1941 (2), r11 fa82268 (1),
r12 15a110e (0, APPROVED).
- Inclusion rule and combination integrity (A1-R7, R8, R2-01, R2-02, R2-06, R2-07, R3-01, R4-01, R4-02, R6-03). Base
  batches are bound to the frozen count and records. Every declared extension batch needs validated metadata.
  Omitted batches are checked against the combined configuration, including the shard layout, and are reported with
  their completion fractions. Campaign seeds must derive from the batch seed and differ from base and pilot seeds.
  Reused plans have their task files hash-checked.
- Lane runner ownership and recovery (A1-R1, R3–R6, R2-03–R2-05, R3-02–R3-04, R4-03, R5-04, R6-02, R7-01, R8-01,
  R10-01). Queue directories are created up front. Ownership is attempt-based, with a heartbeat and takeover. Claims
  are atomic. Merges are reconciled and retried. Abandoned work gives a nonzero exit. Markers are trusted only together
  with their audits. Signal-interrupted attempts are not counted as failures. Recovery runs only under an exclusive
  maintenance marker, with a sanitized all-state scheduler query and a fixed package job-name prefix.
- Deadline and closing (A1-R9-01, R10-02, R11-01). A merge-only finalize step runs after the wave. Every worker enforces
  an immutable deadline, rechecked after scheduler queries and again just before an element starts.
- Smoke replay comparison (A1-R2, R3-05, R5-01–R5-03, R6-01, R7-02, R8-02). Per-process exit status. The full expected
  checkpoint set is required. Long doubles are parsed exactly. Comparator bugs were fixed. The bound is on the
  estimator scale. The qualifying element set is fixed, with no environment bypass.
- User decisions folded into the revisions were inspected in later rounds: the 48-hour window and batches b13–b14
  (round-7 revision), and 7-day longq requests with a pre-registered stop at T0 + 48 h (round-9 revision).

**Amendment A2.** Rounds: r1 bea184d (3), r2 3f0e071 (3), r3 2b642f0 (1), r4 92377ad (1), r5 e191f4c (1),
r6 e42cdf8 (3), r7 b52b19f (1), r8 28d28c7 (2), r9 4adf719 (0, APPROVED).
- Preserving the A1 result (A2-R2, IR-01, IR-03, REVIEW-01, R4-01, R7-01, R8-01, R8-02). An immutable A1-close
  snapshot and a derived inclusion file. Inclusion follows A1's checkpoint-completeness rule, with claim-based wave
  attribution and a two-pass scan (checkpoints first, then claims). Publication is restartable. The A1 record is made
  whatever happens to A2. The combination verifies the snapshot. One shared job body runs both steps.
- Separating the waves (A2-R3, R5-01, R6-01–R6-03). After rounds 5 and 6, A2 was made sequential. Its single queue is
  published atomically only after every A1 lane has ended and the snapshot is recorded. One stop mechanism covers the
  whole wave, and one queue handles recovery.
- Submission environment (A2-R1, IR-02). Inherited `C8X_*` and `SBATCH_*` variables are cleared, the job name is
  explicit, and submissions are checked afterwards.

**Amendment A3.** Rounds: r1 8d2df66 (5), r2 4f24314 (6), r3 46727b4 (2), r4 124e54f (2), r5 3a36737 (4),
r6 eb25c8e (0, APPROVED), r7 b9a9bf6 (2), r8 9e5ed07 (4), r9 6096b92 (2), r10 bd13a63 (0, APPROVED).
- Expanse submission and scheduler handling (A3-01–A3-03, R8-02). Journaled submission with validated job ids.
  Sanitized all-state queries that fail closed. Retry accounting over all retried states. Lane8's set of terminal
  states.
- Closing on symmetry (A3-04, R2-01, R2-03, R2-04, R4-01, R4-02, R5-02). The close is complete-only: it requires all
  of b5–b14 and K = 14. The close lock and the quiescence check apply on every run. Imports are registered. The close
  job verifies each staged copy itself, with receipts, before installing it. A stop/publication handshake. An atomic
  closing record.
- Stop barrier and locks (R2-02, R3-01, R5-03, R8-04, R9-02). A submit lock serializes run, resubmit, merge and stop.
  A durable stop marker is honored by submission and by tasks. The export holds the lock. Merges honor the stop and
  require a journaled array and a complete batch.
- Transfer integrity (R3-02, IR-02, R8-01, R8-03). Manifest digests are computed and validated in Python. Remote
  shells use pipefail. Tree traversal is strict and rejects symlinks. Symmetry submission is pinned.
- The early export (b9a9bf6, a user request after approval r6) was inspected in r7–r10. A3-IR-01 led to stating it as
  a speculative start, with a failure-free gate and a discard policy. For A3-R9-01, see Section 3.
- Withdrawn features (A3-05, R2-05, R2-06, R5-01, R5-04): the stopped close and the Expanse quarantine path; see
  Section 3.

**Results review.** Rounds: r1 dossier rev 1 (170b44d0…) with HEAD 9dd3a6b (5); r2 rev 2 (ad3dab33…) with REPORT.md
at 1bccd7c (2); r3 rev 3 (9a4fd78e…) with REPORT.md at 4fe7f05 (1); r4 rev 4 (a5a3e5cf…) with REPORT.md at 1282e37
(0, APPROVED). Rounds 1–3 identified no numerical correction to the headline estimate, round 2 confirmed that the
result file was unchanged, and round 4 found nothing outstanding. All eight findings concern wording or disclosure.
- Controls (C8-REV-01, C8-R2-01). The pole columns enter the estimate through the frozen controls. Their C8
  projection, +11,078 ± 24,734, is now reported. Finite-degree control error lies inside the allowance (through the
  R8 and R9 terms). A failure of the exact pole identity would be a framework error outside it.
- Statistics (C8-REV-02). The χ²₃₀ p-value was removed, because the columns are correlated. Σz² = 39.8 is descriptive
  only.
- Chronology (C8-REV-03, C8-R2-02, C8-R3-01). The report now states A1's deadline rule as executed, and A2's decision,
  taken after the K = 5–8 interims were visible. The b10 completion fraction is attributed to the A1 closing snapshot.
- Wording (C8-REV-04, C8-REV-05). The early-export reach bound is a scheduling estimate, not a guarantee. Seven
  batches (b5–b11) ran on Intel, not ten.

##### 3. Recommendations not adopted / overruled

No finding was rejected or deferred in any stage. Every disposition file and amendment table records each of the 114
findings as accepted. Five points need stating:
- **A3 stopped-campaign close (A3-05, A3-R2-02, A3-R2-05).** A3-05 asked for a close procedure after a user stop, and
  round 1 implemented one. A3-R2-05 then showed that it could not handle a stop before queue publication or export.
  The coordinator withdrew the stopped close rather than extend it phase by phase. Halting stays implemented (A3-R2-02
  was adopted only for halting) and the result rule after a stop is fixed in advance. However, no stopped result will
  be published until a procedure for the actual state has been written and independently reviewed. Round 6 approved
  the amendment with the stopped close withdrawn. The campaign closed complete (K = 14), so this path was never needed.
- **A3 Expanse quarantine path (A3-R2-06, A3-R5-01, A3-R5-04).** The quarantine support added for A3-R2-06 was found
  to be non-restartable and to leave identities unvalidated. Instead of the suggested fixes, the path was withdrawn: a
  corrupt Expanse checkpoint halts that batch's Expanse work until a reviewed recovery procedure exists. Round 6
  approved this.
- **A3 early-start tripwire (A3-R9-01).** The reviewer offered two options: implement a persistent failure watcher, or
  disable the early export. The coordinator chose neither. It removed the tripwire and kept the early export. The
  stated reason: the tripwire only limited wasted compute; correctness is enforced by the close-time snapshot and
  installation checks; and the stated worst case is about 6k SU discarded per overlapped batch. Round 10 approved
  this. The A1-close snapshot later recorded b12–b14 as untouched by A1 workers, so no Expanse copy was discarded.
- **A1 smoke threshold.** A1-R2 asked for the pre-set row bound of 1e-12 to be enforced, and it was. The first
  symmetry replay then failed it: L8 QMC rows differed from Expanse by up to 6.0e-12 of the row scale, a deterministic
  platform effect (the two thread modes agreed bitwise). Before production, the coordinator replaced the bound with a
  row bound of 1e-10 plus an estimator-scale bound of 1e-6 of the per-batch SE. Rounds 4–6 inspected the change, and
  round 6 corrected its first statistical form.
- One registered rule was overridden by the user, not by a reviewer. A1 allowed a finishing wave only for batches
  already in progress. A2 runs all of b10–b14. The user took this decision after interims of five to eight batches
  had been seen. A2 discloses it and was inspected with it, and the results review required the chronology to be
  stated (C8-REV-03).

##### 4. Not reviewed

- **Code inspection.** The production code c0ffa63 is the tree approved in round 10. Commit 78e6a8a (the K = 4
  result) changes only files under `results/`. Some work ran before approval, on intermediate trees. The exact stage
  and the pilot were planned before the round-1 fixes (disposition of C8-R03). The pilot ran from code copy ce5074e
  (= commit 4666608), the tree inspected in round 1. The post-pilot job (merges, affine map, controls, preview) ran
  b195a0c, the tree of round 6. The kernel sources `src/` are identical in 4666608 and c0ffa63. `affine8.py`,
  `controls8.py`, `campaign.py` and `production8.py` are identical in b195a0c and c0ffa63. The sources contain no
  separate results review of the K = 4 result. The K = 14 results review covers the final result.
- **A1.** Approved at 15a110e, and the A1 lanes ran tools 15a110e. `tools/`, `src/`, `tests/` and `gen/` do not change
  from 15a110e to bd13a63.
- **A2.** Approved at 4adf719. The only later change to an A2 file (`cluster/symmetry/submit_a2.sh`, queue reduced to
  b10–b11) came with A3 and was inspected there.
- **A3.** The final A3 tools bd13a63 were approved: round 10 returned APPROVED, and its snapshot matches bd13a63 file
  by file. The A1-close job ran the eb25c8e copy (approved r6), whose `cluster/symmetry/` scripts are identical in
  bd13a63. The Expanse export (15:12 EDT) followed the round-10 verdict.
- **After bd13a63.** Commit 9dd3a6b adds results and records only (`results/2026-10_ext1/`). Commits 1bccd7c, 4fe7f05
  and 1282e37 change only `REPORT.md`. The results review covers all four: round 1 read HEAD 9dd3a6b, and REPORT.md
  at 1282e37 was an input of the approving round 4. Outside `results/`, the exported code tree (1282e37) is identical
  to bd13a63.
- **Limits of the results review.** The review was static. Remote checkpoints, merged replicate data and detailed
  incident logs were not inspected, and the physics framework was not validated. The reviewer read the
  condensed-note merge script but did not run it and did not compile the note. The note commit (fa71533, 11:49 EDT)
  followed the round-4 verdict, so the merged note text itself was not reviewed. The script file was last written at
  11:49, and the sources do not record whether its content changed after rev 4.

##### 5. Public-edition files

The files written for this release (`public/replay8.py`, `public/verify8.py`, `public/test_tools_portable.py`, with
`public.mk` and the Slurm environment template) were added after all reviews. No second model reviewed them, and no
review artifact mentions them.

### `LRI_C8_D2_HPC`

Folder: `code/LRI_C8_D2_HPC/`.

#### Reviews of LRI_C8_D2_HPC (full C8(2), note Section 31)

The package extends the seventh-order d = 2 package (LRI_C7_D2_HPC, whose root commit is the code as delivered by an AI
model in a ChatGPT session, OpenAI GPT-6 astra (model stated by the author, 2026-10-13), hardened by Claude Code and approved by Codex in round 3 at a55958f)
to eighth order. The eighth-order code, its tests and all evidence were written by Claude Code session C62d and its
subagent workflows (2026-10-03 to 2026-10-09). The reviewer in every round below was OpenAI Codex (model gpt-6-astra,
reasoning effort xhigh), each round in fresh sessions. No raw review log or transcript is shipped.

**There is no Codex approval of the code.** The user stopped the code inspection after round 4 (2026-10-06); round 5
was prepared but not run, and the pilot and the production went ahead without an APPROVED verdict.

| Stage | Rounds | Verdict | What changed |
|---|---|---|---|
| Plan | 4 | APPROVED in round 4 (plan only, static) | Rounds 1-3 (REVISE): 3 high and 9 medium, then 5 and 3 medium findings, all accepted: dependencies of the vendored tests, invalidation of completion markers, a frozen and pinned rate map, an acyclic checksum hierarchy, per-campaign cost keys, bounded merge fan-in, the calibration bootstrap, the platform contract. |
| Stage-3 checkpoint (3 parallel sessions) | 1 | REVISE, 20 findings (4 high) | All fixed (merged-run authentication, partition overrides of merges, accounting that fails closed on missing scheduler records, no submission after a failed time policy, and 16 medium/low); worker binaries byte-identical; re-validated on Expanse. |
| Stage-6 code inspection (6-8 parallel sessions per round) | 4 | REVISE in every round: 23, 16, 22 and 21 distinct findings | Four fix rounds, each validated on symmetry: gate records bound to their F1 coverage, build and input set; OpenMP team sizes controlled and observed; generator input validation; contained vendoring; runtime fingerprints enforced; cost-model numerics checked; seed registration; memory estimate of a claim; strict G-file readers. One fix changed the kernel source (round 3, Z4: refuse truncated graph files; valid inputs give the same output bit for bit; the full exact replay of all 3,773 L3-L7 kernels passed again and the double-double/77-digit gate was re-run). No default-path number changed in any round. |
| Heavy-tail question (results side) | 2 consultations | (1) the confirmations apply a warning rule and do not establish an infinite second moment; (2) "sound with caveats" | The caveats were all addressed before the result was quoted: four random primes and two random points per prime instead of two fixed primes, an error bound; nine archived controls with failing exit codes; joint resampling on a common window; a targeted test of the double-lift class; the SE wording ("estimated sampling standard error"; inflation figures are scenarios, not bounds). |
| Results | none | not reviewed | No separate Codex results review of the C8(2) production was run. The independent eighth-order code (GFF/code/LRI_C8_D2_HPC_optimized) is the external check. |

Recommendations overruled or not done, and why:
- The Stage-6 approval gate (the plan tied the pilot to Codex approval): waived by the user after round 4, because the
  later rounds found mostly hardening against misuse and no numerical defect.
- Codex's proposed tail test from checkpoint prefixes: not possible (one checkpoint row per replicate); replaced by a
  fresh nested-sampling test.
- Never run (owed after Stage 6, not needed because production stayed on symmetry): the J-EXP-1 rerun on Expanse
  (acceptance A-EXP-3; the first attempt was cut short by a Lustre failure), the zen2 `GMP_PREFIX` precision re-run on
  Expanse (so builds with `GMP_PREFIX` are not cleared for production), and the Expanse copy of the forbidden-seed log
  (seeds of fix rounds 1-4 and of the pilot and production are pending there).
- Not approved for production: the `exp1` numerics profile (inert) and the R7 rate maps.
- Deferred: undefined behaviour of the frozen-grid reader on a truncated optional grid file (production passes '-').

What was never reviewed by Codex: the fix of inspection round 4 (W1-W24; no source change; validated on symmetry), the
evidence and analysis scripts under benchmarks/, the report-caps fix aafa8a4 (not part of this release), and the public
release files (public.mk, public/).

The order-8 assembly under vendor/c8_assembly/ was written by Claude Code session C63d and reviewed by C62d's Claude
workflow (four lenses: independent derivation, order-7 regression, numerics, handoff tests): ACCEPT_WITH_MINOR, no
required change (see ../LRI_C8_shared/REVIEWS.md).

### `LRI_C8_shared`

Folder: `code/LRI_C8_shared/`.

#### Reviews of LRI_C8_shared (shared eighth-order inputs of C8(2) and C8(3))

Two Claude Code sessions wrote this folder: C62d (the C8(2) package) the inventory and payloads `inventory/inventory8_d2/`,
C63d (the C8(3) package) the order-8 assembly `assembly/`. Each checked the other's part. No raw review log ships (the
review records and the coordination notes stay in the project archive).

| Item | Reviewer | Verdict | What was checked |
|---|---|---|---|
| `assembly/` (handoff H2/H3, `HANDOFF_assembly.json` sha256 f5ff6a35..., 2026-10-03) | C62d's Claude workflow, four lenses (independent derivation of the eighth-order RG polynomial, order-7 regression against the published C7(2) assembly, numerics of the two-loop and Gamma inputs, handoff tests) | ACCEPT_WITH_MINOR; no required change | every delivered file at its sha256; the eighth-order polynomial derived twice and equal; 64 random eighth-order cases against two exact inversions (7.0e-16); order 7 reproduces C7(2) to 2 ulp; the vendored tests (30 passed) and exact_check. Minor suggestions (documentation, test bounds) were left for a later revision, which never happened. |
| `assembly/` | C63d's own workflows (builder plus three adversarial lenses, two repair rounds; fixer plus two verifiers) | ready | as recorded in `HANDOFF_assembly.json` (`verification`) |
| `inventory/inventory8_d2/` (handoff H1, pin 46341a3c...) | C62d's independent verifier (Stage 1-2 of the C8(2) plan) and C63d's gates on the published tree | passed | the eleven gates of the tree (`gates/`), plus C63d's gate records in `assembly/H1_gates/` (counts against an independent enumeration, weight sums, reproduction of the L <= 7 packs at d = 2 and d = 3) |
| both | OpenAI Codex (gpt-6-astra, xhigh) | not reviewed as such | the assembly was out of scope of the C8(2) Codex inspection (reviewed separately as above); the generator code under `inventory8_d2/src/gen/` was inspected as part of the C8(2) package (`LRI_C8_D2_HPC/gen/`, rounds 1-4, REVISE, fixed; no Codex approval, see that package's REVIEWS.md). The tree itself was published before those rounds and never changed; the generator regression re-run after each fix round (J-GEN-1, A-INV-2 on symmetry) still found the regenerated loops equal to the published inventory. |

### `LRI_C8_D2_HPC_optimized`

Folder: `code/LRI_C8_D2_HPC_optimized/`.

#### Reviews of LRI_C8_D2_HPC_optimized (independent check of C8(2))

The code was written by OpenAI GPT-6 astra (model stated by the author, 2026-10-13), independently of the eighth-order extension that Claude Code built for the main calculation, as an
eighth-order extension of the seventh-order package of Section 28 of the note. It was delivered as
`LRI_C8_D2_HPC_optimized.zip` together with the original package `LRI_C8_D2_HPC.zip` (graph packs and earlier runs). Its numerical files (`src/`, `Makefile`, the tools pinned by a campaign plan) were not changed afterwards.
A Claude Code session added a cluster layer for Expanse and symmetry (whole-node runner, admission and seed checks, a gate
job, tests and docs; commits 300a1ca..a791a1f) and ran the pilot and the production. The reviewer in every round below was
OpenAI Codex (model gpt-6-astra, reasoning effort xhigh), each inspection in a fresh session.

| Stage | Rounds | Verdict | What changed |
|---|---|---|---|
| Port plan | 4 | APPROVED in round 4 | Rounds 1-3 (REVISE): 8 + 7 + 4 findings, all accepted. Job arrays replaced by one whole-node runner per node; production seeds reserved in the seed registry of the main C8(2) calculation; one site lock and admission check shared with the other campaigns; scheduler states such as COMPLETING handled; exhausted work indices retried; the deadline measured in wall time. |
| Code inspection 1 | 1 | REVISE, 4 findings | All fixed in 71a7844: claim tokens under a claims lock; the seed synchronisation compares (seed, source) pairs; quoted owner paths in remote shells; the plan comparison fails on any differing manifest key. |
| Code inspection 2 | 1 | REVISE, 1 finding | Fixed in a791a1f: the runtime identity refuses `LD_PRELOAD`, `LD_AUDIT` and `GLIBC_TUNABLES` and hashes absolute-path library entries. |
| Results | none | not reviewed | The result was not given a separate results review. |

What was not reviewed:
- the fix of the second inspection (a791a1f), because the inspection budget of two rounds was used up. It touches only the
  cluster layer's identity check, not the numerics. The production ran this commit.
- the numerical code itself, beyond the checks the package ships: it was delivered as is, and the port's acceptance gate
  required its numerical files to be byte-identical to the delivery (gate step AC1) and its kernel to reproduce 52 frozen
  fixture cases bit for bit against the delivered reference kernel (AC2), on both clusters.

No recommendation of any review round was overruled.

Scope of the check (note Section 31.7): the code shares with the main calculation the seventh-order kernel construction
and its precision policy, the importance sampler, the digital nets and seed hashing, the renormalization scheme and the
payloads of loops three to seven, so an error in those would be common to both.

### `LRI_C8_D3_HPC`

Folder: `code/LRI_C8_D3_HPC/`.

#### Reviews of the C8(3) calculation (LRI_C8_D3_HPC)

All reviewers were AI systems. There was no human referee. The builder and coordinator was a Claude Code session (C63d).
The reviewer was OpenAI Codex (CLI 0.158–0.162) with model gpt-6-astra at reasoning effort xhigh, in read-only review mode.
The raw logs, transcripts and review artifacts are not published; this file summarizes them.

##### 1. Plan review: APPROVED in round 7

- **What was reviewed.** The implementation plan of the package (`PLAN.md`, 2,503 lines in round 1, 5,283 lines when
  approved), generalizing the C7(3) package `LRI_C7_D3_HPC@a6ce987` to eighth order, with the recon of the inherited code,
  the shared nine-vertex inventory (H1) and the shared order-8 assembly.
- **Rounds.** Rounds 1–6 REVISE with 11, 5, 3, 2, 2 and 2 findings; round 7 APPROVED (2026-10-04), bound to the plan's
  sha256 `00a25729…`. The user raised the round limit from 5 to 8 after round 5.
- **What changed.** All findings were accepted and applied. The main ones:
  - pilot subset campaigns that cannot be assembled (R01): a separate pilot_subset role, merged without assembly;
  - Gate 5 needed subgraph mask lists that the published inventory does not hold (R02);
  - a cost-model refresh path for a changed binary (R03);
  - the two-loop reference path and its five-entry overlap (R04);
  - report inputs that lost the prefix boundaries of nested samples (R06), the same-data variance correction for 8 and
    16 replicates (R07);
  - submission safety: the shared lock, ledger-before-acceptance, durable submission intents, slot accounting of
    unresolved intents (R08, R09, R17, R20–R22);
  - block balancing under both checkpoint maxima (R10) and the input-parser guards of the rate converter (R11).
- **Limitations stated by the reviewer.** Static plan review; implementation conformity, live cluster behaviour and the
  unchanged numerics were not revalidated.

##### 2. Code inspection: two rounds; Stage 6 closed on the user's acceptance of the residuals

- **Round 1 (2026-10-06).** Four scopes (native worker; orchestration; assembly, statistics and delivery; inputs,
  performance and gen3), each diffed against the C7(3) base. All REVISE, 33 findings (14 high). All 33 accepted and fixed
  in one fix round, with two departures from Codex's proposed fixes (per-site budget sub-caps instead of a shared
  admission coordinator, S2-004; an append-only decision acknowledgment instead of a lock that the other session's
  writers do not honour, S4-004).
- **Round 2 (2026-10-06, the last allowed by the user).** All four scopes REVISE, 23 findings. Codex confirmed most
  round-1 fixes; nine were partial; three findings were new.
- **Decision (user, 2026-10-06): "Targeted fix, no 3rd Codex".** Fix round 2 fixed the reachable gaps (S3-R2-001..007,
  -009, S2-R2-005, S4-R2-001..003, S1-R2-01, -02, -05 and a uniqueness check for S1-R2-03). **Fix round 2 and the host's
  change of the symmetry admission cap are not Codex-reviewed.**
- **Accepted residuals** (G6 closed 2026-10-07): concurrency races outside the operating procedure (S2-R2-002, -003,
  -004 = S3-R2-008, -006); defense in depth behind working guards (S2-R2-001, S1-R2-04); S1-R2-03 beyond uniqueness; and
  three unit tests that cannot run on a real cluster site by design (they pass on the Mac). One per-block throughput
  shortfall (three of 789 blocks below 0.95) is reported, not fixed.
- **Validation of the final code (K6 a914db2)** on symmetry and Expanse: val1, val2 (order 7 bit for bit against the
  unchanged C7(3) worker on every L <= 7 kernel; `benchmarks/symmetry_2026-10-c8/stage6_a914db2/val2/`), val3, the
  bitwise L8 proof against the Stage-3 binary, cost sweeps and campaign-build checks.

##### 3. Production support after Stage 6: not inspected

Added on 2026-10-08 by the builder, tested on the Mac and on symmetry, **not Codex-reviewed**: the production budget line
(`tools/budget.py`), the conservative tail rule of the design (`tools/design_fallback.py --pc`), the margin probe
(`tools/margin_probe8.py`) and the production support of `tools/production.py` and `tools/slurm_submit.py`. The worker
source `src/` did not change after Stage 6 (production binary e9b6f6c3…). The production export 4fbd1bae passed val1
(571477: 38 PASS, 19 SITE_REFUSED by design, 0 FAIL) and J-BLD (571482).

##### 4. Results review: APPROVED in round 3

- **What was reviewed.** A results dossier (C8(3) = 1602.6 ± 3.9, the campaign split, the tail N-trend, the margin
  probes, the lower-order checks) against the stored result, the local copy of the production records (50 hashes matched
  symmetry), the package at 6dd4a75a and the independent package's records.
- **Round 1 (2026-10-12): REVISE.** "The stored result and campaign provenance are consistent with the inspected records.
  The uncertainty justification overstates what the diagnostics establish, and the N-trend analysis contains two
  concrete comparison errors." Findings: χ²/dof ≈ 1 does not show calibrated SEs nor exclude a diffuse rate effect
  (C8D3-R1); the a/b shift of ξ̂ was taken at unmatched N (C8D3-R2); coincident predictions at N = 32,768 were counted
  as decisions (C8D3-R3). All accepted: `ntrend.py` and both READMEs revised (package commit 8adedace), the a/b reading
  narrowed to "no concentrated discrepancy".
- **Round 2: not counted.** The reply was APPROVED with one low finding (C8D3-R4, quoted bands), but a transport failure
  left the turn unrecorded; C8D3-R4 was applied anyway.
- **Round 3 (2026-10-12): APPROVED.** "Rev 3 resolves C8D3-R1–R4. No material unresolved defects were found in the
  inspected evidence. The result stands within its stated scope: ±3.9 is a conditional, heuristic sampling allowance,
  without established confidence coverage."
- **Limitations stated by the reviewer.** Static review; remote checkpoints, promotion tables, raw tails and the archives
  were not audited; inventory and field theory not re-derived; finite variance and four-SE coverage not established.
- **Reporting rule.** 4 × SE rounded up to a multiple of 0.1 was proposed in the dossier and confirmed by the user after
  the approval ("yes use 1602.6 ± 3.9"). No allowance was registered before the production.

##### 5. Recommendations not followed

- Codex's shared admission coordinator (S2-004) and shared-file lock (S4-004): replaced as stated in section 2.
- A third inspection round after fix round 2: declined by the user.

##### 6. Independent check

A separately developed code (package LRI_C8_D3_OPT, by OpenAI GPT-6 astra) gives 1600.98 ± 3.97, −0.40 combined SE from this
result. It is documented with its own reviews in the `C8_3_check` folder.

### `LRI_C8_D3_OPT`

Folder: `code/LRI_C8_D3_OPT/`.

#### Reviews: LRI_C8_D3_OPT (independent check of C8(3))

Summary of the independent reviews. The transcripts, findings files and plan are not shipped.

##### What was reviewed and what was not

- **Reviewed:** the cluster layer that C63d (Claude) added to the delivered package for Expanse and symmetry: the
  dispatcher's locks, leases, deadlines and signal handling (`tools/hpc_dispatch.py`), the admission and submission
  rules (`tools/submit.py`, `slurm/*.sh`, `slurm/sites/*`), the one change to a pinned tool (`tools/campaign.py
  run_job`), and their tests (`tests/test_cluster.py`). Scope of every round: `git diff dafa312..<head>`.
- **Not reviewed by an independent reviewer:** the delivered science code (worker, graph generation, low-loop
  inputs, assembly, fixed point), which the delivering AI (OpenAI GPT-6 astra) checked with its own tests and evidence (`verification/`,
  `tests/`), and **the production number 1600.98 +- 3.97: there was no results review.** Its checks are the replayed
  lower-order pulls (all |pull| <= 1.73), the a/b campaign split (0.64) and the comparison with the separately reviewed
  main C8(3) result (-0.40 combined standard errors; that result's results review is summarized in the main package's `REVIEWS.md`, `GFF/code/LRI_C8_D3_HPC`).

##### Codex inspections of the cluster layer

Reviewer: Codex, model gpt-6-astra, reasoning effort xhigh, a fresh session each round. Builder of every fix: Claude
(C63d). All findings were accepted; no recommendation was overruled.

| round | head inspected | verdict | findings | fixed in | what changed |
|---|---|---|---|---|---|
| r1 (2026-10-09) | `f0f0cd5` | REVISE | 16 (R01-R10 high, R11-R16 medium) and one limitation | `a3b6b07` (+ `2470de1`, `704b148`) | token locks with fixed-name tombstone reclaim and token release; seed check and reservation inside the session lock; intents written before sbatch and reconciled afterwards; allow-listed plan and index arguments; queued jobs counted as running; strict squeue parsing; scheduler variables scrubbed; shared-partition billing; time validation and partition limits; grace-aware deadline; receipts checked before the deadline test; build tests only in a copy; canonical dispatch identity; array mode disabled; a controlled test environment. The limitation (assembly needs loops 3-8) went into the runbook. |
| r2 (2026-10-09) | `9583eca` | REVISE | 8 (3 high) | `6e3f139` | stale-lock reclaim only when squeue shows no active or completing allocation, sacct is terminal and a settle time has passed, with the token re-checked before publication; unresolved intents stay reserved; `--mem 0` refused; separate Expanse compute and shared classes; the account-wide running cap; node exclusions on symmetry; an environment check in every job script; **R2-08: `campaign.py run_job` re-checks the receipt after its lock and never replaces a receipted output** (a hash-pinned tool; accepted as a plan deviation, so only plans made after `6e3f139` can run, as `prod1` did) |
| r3 (2026-10-09) | `6e3f139` | REVISE | 8 (1 high) | `f7264e7` | no time-based release of intents (an operator's recorded resolve instead); one package per site and partition class instead of disjoint shares, because the main package's submitter cannot see this package's jobs; lanes only on the integration partitions; fail-fast environment files; one account value; an unknown job end defers bundles |
| r4 (2026-10-09) | `f7264e7` | REVISE | 3 medium, no high; r1-r3 fixes confirmed | `6fb5b5f` | the class handoff procedure covers Expanse shared jobs; `squeue -t all` so suspended jobs count; unresolved submissions of the main package occupy their class |
| (none) | | | | `d5deeb9` (2026-10-10) | **the production commit**: the user's 22-running-jobs cap counted only this package's queued jobs among the user's pending ones. Uninspected when production ran. |
| r5 (2026-10-12) | `d5deeb9` | REVISE | 3 (R5-01 high, R5-02 and R5-03 medium) | `3961865` | R5-01 reverts `d5deeb9`'s loosening (every non-terminal normal job of the user counts; other users' allocated jobs count for the account cap); SPECIAL_EXIT is live, not terminal; the reader of the main package's intents fails closed and validates every frame |
| r6 (2026-10-12) | `3961865` | REVISE | 1 medium (R6-01); R5-01 and R5-02 confirmed resolved | `6edcc9e` | the intent reader also reads the main package's ledger under the shared lock; any hold refuses. **Not inspected.** |

Consequences for the published result: every finding concerned admission, locking or restart safety. None touches
the integrand, the sampling, the allocation or the assembly. R5-01 means that `prod1` was admitted under a cap rule
that was looser than intended for the user's other jobs; the rule decides which jobs may run, not what they compute.
The production commit `d5deeb9` is exported; the fixes `3961865` and `6edcc9e` are not (they change only the
admission layer, which a public rerun replaces by the templates in `public/slurm/`).

##### Validation runs (not reviews)

- Expanse builds 54781591, 54783728 and 54786481 (AMD EPYC 7742, 2026-10-09): all 14 steps PASS (delivery check,
  build, worker description, test copy, positive binary128 adder, native regression, point checks, optimization
  regression, dispatcher, streaming assembly, fixed point, campaign, allocation, cluster tests).
- Expanse smoke campaign `smoke1` (all loops, 16 points, 4 replicates, 772 jobs): killed by its deadline once,
  resumed, assembled (exploratory C8 = 2075 +- 396).
- symmetry: Intel test builds 572278 (one failure, the test-environment leak fixed as R16) and 572321 (all PASS); AMD
  EPYC 7543 build 573730 on `6edcc9e`, all 14 steps PASS (2026-10-12); smoke campaign `smoke_sym1`: deadline deferral,
  forced TERM stop with nothing left behind, resume and assembly (exploratory C8 = 550.8 +- 327, lower-order pulls
  <= 1.98).
- These exploratory 16-point estimates test the workflow, not the number.

##### Replay added for the public release

`public/replay_check.py` (2026-10-13, not reviewed) recomputes the estimator, its standard error and every quoted
check from the stored records (`REPRODUCE.md`, section 3). It passed locally (76 PASS, 1 SKIP without the hosted pilot,
1 documented row; 79 PASS with the pilot statistics) and fails on a deliberately altered record.
