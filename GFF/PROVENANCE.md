# Provenance of the GFF packages

For each package: where it comes from, who wrote it (the author, Claude Code sessions, OpenAI GPT-6 astra), the commit it was exported at, and what changed afterwards.

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

#### PROVENANCE fragment: lri_numerical_resolution

* **Source:** `packages/lri_numerical_resolution/` of `LRI_complete_research_bundle.zip` (sha256
  3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0; consolidated 22 September 2026), unzipped
  read-only to `<PROJECT>/GFF/LRI_complete_research_bundle/` on 2026-10-13. Inside the bundle it is the unpacked
  archive `LRI_C5_numerical_resolution.zip` (sha256 ae4a39a7b2784ec010e97b4d8913d94e4346850ff3711e922c63f8ac9156c3e6,
  77 files, 1,524,883 bytes; `provenance/source_archives.json`), milestone 06 of the bundle's `PACKAGE_INDEX.md`
  ("C5 numerical discrepancy audit", status "Retained resolution of the old numerical offset"). Not under git;
  no commit. The copy in `<PROJECT>/LRI_1d_through_C6/packages_2026-09_bundle/` is identical except for the
  removed note copies.
* **Who wrote it:** the bundle's documents do not name the authoring system. `README.md` of the bundle says it
  "collects the main results, derivations, source code and delivered numerical evidence from the research
  conversation"; its `PROVENANCE.md` says "These are the files supplied/generated in this conversation" and that
  "No formula, proof, numerical record or historical README was edited inside any original package during
  consolidation". The package's run records carry the sandbox fingerprint that the project uses to recognise
  GPT-6 astra / ChatGPT deliveries (`<PAPER>/notes/agent_stats_2026-10-12.md`, Sec. 6): platform
  `Linux-6.18.35-x86_64-with-glibc2.41` and Python 3.13.5 in `verification/records/environment.json`, and
  `/mnt/data/lri_discrepancy_work/...` working paths in the run logs (not exported). The model was OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the bundle (model stated by the author, 2026-10-13; the files themselves name no model).
  The files give no model name or date.
  Filesystem dates are those of the consolidation (22 September 2026), which the bundle says are not scientific
  chronology.
* **Production:** raw five-loop amplitudes (degree 18 scalar long-double control; degrees 18, 22, 24 combined
  AVX-512 double-double kernel) and degree-32 lower-loop inputs, computed on an Intel Xeon Platinum 8573C with 4
  threads (`environment.json`); `verification/records/source_checks.json` records that the shipped C++ sources
  are the executed ones.
* **Changed afterwards:** nothing in the shipped files (byte-identical; `sha256_manifest.json` verified by
  `public/replay.py`). Not exported: note copies and builders, history, run logs, note-build records (see
  `export_entries.json`). Added for the public edition (C71d helper, Claude Code, 2026-10-13): `public.mk` and
  `public/` (replay, shared helper, the new unlabelled-class audit `graph_classes.py`, README, requirements).

### `lri_psi_complete_update`

Folder: `code/lri_psi_complete_update/`.

#### PROVENANCE fragment: lri_psi_complete_update

* **Source:** `packages/lri_psi_complete_update/` of `LRI_complete_research_bundle.zip` (sha256
  3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0; consolidated 22 September 2026), unzipped
  read-only to `<PROJECT>/GFF/LRI_complete_research_bundle/`. Inside the bundle it is the unpacked archive
  `LRI_psi_coefficients_Kappa_proved.zip` (sha256 1846fc1eb7b0af521f5ac7801e2a69d99ffee398a137d43958f7442acd3f47c5,
  24 files, 1,124,637 bytes), milestone 05 of `PACKAGE_INDEX.md` ("C0-C5 polygamma forms and Kappa proof", status
  "Retained analytic formulas and proof"). Not under git. The package carries no checksum list; the 24 lines of the
  bundle's `MANIFEST.sha256` for it are copied to `public/bundle_sha256.txt` and checked by the replay.
  `lri_numerical_resolution/previous/verification/` (not exported) is a byte-identical copy of its `verification/`.
* **Who wrote it:** as for the whole bundle, its documents name no authoring system ("files supplied/generated in
  this conversation"); the model was OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the bundle (model stated by the author, 2026-10-13; the files themselves name no model). Its records name no platform; `verification/wheel_inputs.json` says its 4F3 values were "Reused from
  Fpm_simplification/verification_240.json in the preceding conversation".
* **Changed afterwards:** nothing in the shipped files (byte-identical to the bundle). Not exported: note copies,
  TeX additions, note builder and diff, the unexecuted `CoefficientsPsi.wl`, two note-build records. Added for the
  public edition (C71d helper, Claude Code, 2026-10-13): `public.mk`, `public/`.

### `lri_fixed_hypergeometric_update`

Folder: `code/lri_fixed_hypergeometric_update/`.

#### PROVENANCE fragment: lri_fixed_hypergeometric_update

* **Source:** `packages/lri_fixed_hypergeometric_update/` of `LRI_complete_research_bundle.zip` (sha256
  3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0; consolidated 22 September 2026), unzipped
  read-only to `<PROJECT>/GFF/LRI_complete_research_bundle/`. Inside the bundle it is the unpacked archive
  `LRI_P5_fixed_hypergeometric.zip` (sha256 8d992c363168657f2e7f47428aa77dabf8f9cd086eae80010f18ddebf7bd9758,
  99 files, 2,133,082 bytes), milestone 08 of `PACKAGE_INDEX.md` ("Preferred P5(1) five-value form", status
  "Preferred ordinary-hypergeometric presentation"). Not under git.
* **Who wrote it:** the bundle's documents name no authoring system; the model was
  OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the bundle (model stated by the author, 2026-10-13; the files themselves name no model). The record names mpmath 1.3.0 and no platform.
* **Changed afterwards:** nothing in the 6 shipped files (byte-identical; `sha256_manifest.json` verified with
  ignore-missing semantics). Not exported: the duplicate of `lri_numerical_resolution/verification`, superseded P5
  evaluators and records, unexecuted Wolfram files, proof excerpts, history, note copies. Added for the public
  edition (C71d helper, Claude Code, 2026-10-13): `public.mk` and `public/`, including two new checks,
  `sec11_closed_forms.py` (note Section 1.1 as printed) and `kernel_identity.py` (note Section 10.4; the SymPy
  code the note mentions there is not in the bundle).

## C0-C5 in closed form, general d

### `lri_general_special_functions_update`

Folder: `code/lri_general_special_functions_update/`.

#### Provenance of the general-d C0..C5 packages

| Package | Written by | Delivered | Member archive (sha256) | Changed afterwards |
|---|---|---|---|---|
| `lri_general_special_functions_update` | OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the research bundle (model stated by the author, 2026-10-13) | 7 September 2026 (note date of the package) | `LRI_general_dimension_special_functions.zip` (8491dfce617740688c0196234ba875559ba4046db59013a64a9c2f6928c95d66) | no |
| `lri_general_closed_update` | the same session | 10 September 2026 ("general-dimensional closure revision"; array timestamps 2026-09-11 01:22 UTC) | `LRI_general_dimension_closed_forms.zip` (476c6441c79260a7ee3a0a2e4c232b2ff901304c1a8317c168b8f130c829b412) | no |
| `lri_general_periodization_update` | the same session | 11 September 2026 ("revision date" in its README) | `LRI_general_periodization_and_d2_factorization.zip` (82bb60c1036e8fdcc2a384f0f928fede2e6a477c34161f72147cf33eca473b3b) | no |

- The three archives were collected, unchanged, into `LRI_complete_research_bundle.zip` (sha256
  3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0, 4,064 entries, consolidated 22 September 2026 by the
  delivering session; its `MANIFEST.json` hashes every file). The author handed the bundle over; the Claude Code session
  C62d extracted it read-only into `GFF/LRI_complete_research_bundle/` on 13 October 2026. All 532 files of the three
  packages match `MANIFEST.json`.
- Evidence for the authorship: the environment records name a Linux sandbox (`/mnt/data/...`, `/opt/pyvenv`) with
  Python 3.13.5, numpy 2.3.5, scipy 1.17.0, sympy 1.14.0, mpmath 1.3.0 (`verification/general_special/build_validation.json`,
  `verification/general_closed/release_manifest.json`, `verification/general_periodization/tested_environment.json`);
  the bundle's README calls the material "the research conversation". No Claude Code session edited these packages.
- The packages are cumulative: each contains the previous one byte for byte plus a new layer, and the special-functions
  package contains the general-dimensional files of the earlier bundle package `lri_general_dimension_update` (note
  Section 12) and one-dimensional files of `lri_numerical_resolution`, `lri_hypergeometric_update`,
  `lri_fixed_hypergeometric_update`, `lri_compact_unity_update`. The release ships each package's own layer; the
  inherited general-dimensional files ship once, inside the special-functions package; the one-dimensional files ship
  with the d = 1 unit.
- Written for the release by the Claude Code session C62d (13 October 2026): `public.mk`, `public/replay.py`,
  `public/common.py`, `public/SOURCE_SHA256SUMS`, `REVIEWS.md` in each package, and
  `GFF/results/closed_forms_general/C0_C5/{expected.json, README.md}`. They add files only.
- The note text (Sections 1.1, 12-15) is the condensed edition of the canonical note of the same bundle; the later proofs
  of the d = 2 closed forms (Sections 14.2, 15.6-15.7) and the generic-d reductions (Sections 20-21) are other units.

### `lri_general_closed_update`

Folder: `code/lri_general_closed_update/`.

_same as the section above (one text for the whole unit)._

### `lri_general_periodization_update`

Folder: `code/lri_general_periodization_update/`.

_same as the section above (one text for the whole unit)._

## Closed forms of L2, K2 and C5(2)

### `LRI_C5_d2_simplify`

Folder: `code/LRI_C5_d2_simplify/`.

#### Provenance: d = 2 closed forms of L2, K2 and C5(2)

All content below, including the note text for these results, was written by Claude Code sessions (Anthropic) in the
author's project; the author chose the problem, approved the plans and decided between options. No other AI system wrote
any of this code or text.

| Item | Written by | When | Source state |
|---|---|---|---|
| `LRI_C5_d2_simplify/` top level: discovery (factorization, Euler-Maclaurin sums, strip limit, PSLQ), `RESULT.md` | Claude Code session C62d | 2026-10-01 23:50 to 2026-10-02 03:24 | plain folder (no git, not in the research bundle). No file changed after 2026-10-02 12:15 |
| `confirm_dps70.json` (the record) | `parallel_eval.py 70`, symmetry job 567346, one exclusive 64-core amdq node | 2026-10-02 00:21-00:53 (1852 s) | sha256 096193ae8ebf… |
| `confirm_dps18.json` | `parallel_eval.py 18` (machine not recorded) | 2026-10-02 00:21 (7.6 s) | sha256 154295fef4aa… |
| `LRI_C5_d2_simplify/proof/`: three further proofs, verifiers, synthesis | session C62d, workflow `wf_6fd83950-f9b` (prover, verifier and synthesizer subagents). The byline "C63d proof workflow" in the L2-elliptic TeX source is a slip: the file's timestamp, `RESULT.md` ("three routes"), the bylines of the two sibling routes and the synthesis all place it in this workflow. That source is merged into the note and not shipped. | 2026-10-02 10:15 to 12:15 | same folder |
| `LRI_C5_d2_proof/`: five proof routes, three review lenses each, the `K2_d1template` revision, `drafter/`, `merge/` | Claude Code session C63d, workflow `wf_2604cddc-2ec` (prover and reviewer subagents); merge review `wf_8e8ab059-5ad` | 2026-10-02 10:10 to 19:53 | plain folder; no file changed after 2026-10-02 19:53 |
| Note text (Sections 1.1, 17.2, 18.6, 18.7 and the Section 33 row) | session C63d merged its insert. Pre-merge state: tag `backup/C63d_pre_d2closed` of `GFF/LRI_condensed_note`; the note was put under git on 2026-10-08 | 2026-10-02 | note HEAD fa71533 |
| `LRI_C5_d3/wf_d2check/` (independent spectral evaluation; shipped by C63d's unit) | session C63d | 2026-10-02 01:16 to 01:53 (symmetry jobs 567514-567517, 567669-567672) | — |
| Release overlay: `public.mk`, `public/*.py`, `REVIEWS.md` of both packages; `results/closed_forms_2/closed_forms_2.json` | session C62d (public-release build) | 2026-10-13 | new files only |

What changed after the production run:
- **`parallel_eval.py` is shipped in its post-run state.** At 03:24, 2.5 h after job 567346 had written
  `confirm_dps70.json`, a per-sum cache was added: each finished sum is saved as `cache_dps<N>/<key>.txt` and skipped on
  a rerun. The cache code reads and writes only those files. The summation, the assembly and the checks are unchanged
  in substance, but the file is not the byte-for-byte version that ran. The `.out` of job 567346 has no "cached" line,
  which confirms the older version produced the record. `c5d2_cachetest.slurm` (not shipped) tested the cache. The
  public replay uses the cache: it prefills it from the stored sums, so the shipped `parallel_eval.py` re-runs only its
  assembly.
- **100-digit runs.** Jobs 567347 and 567787 were cancelled (more than 5 h per K2 sum; the proofs made them
  unnecessary).
- **Nothing else.** No other file of either package changed after the dates above. On 2026-10-03 only directory
  timestamps moved (cleanup of scratch files).

Software of the original runs:
- Local runs: anaconda Python 3.10.11, mpmath 1.2.1, sympy 1.11.1; Mathematica 15.
- symmetry: `module load python/3.11` with a virtual environment (mpmath version not recorded); `mathematica/15.0`.

### `LRI_C5_d2_proof`

Folder: `code/LRI_C5_d2_proof/`.

_same as the section above (one text for the whole unit)._

## d = 3 specialization and the generic-dimensional reduction of L_d, Z_d, K_d

### `lri_d3_reduction_update`

Folder: `code/lri_d3_reduction_update/`.

#### Provenance: GFF/code/lri_d3_reduction_update

| item | value |
|---|---|
| origin | package 14, "d=3 half-shift determinant", of the research bundle `LRI_complete_research_bundle.zip` (sha256 `3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0`, 4,064 entries) |
| original archive | `LRI_d3_half_shift_reduction.zip`, sha256 `7aa3221aa29cb5659db513dbfb8bccade52e54170c2b913ff57861ec671ce9ac`, 226 files, 8,365,582 bytes (bundle `provenance/source_archives.json`) |
| written by | OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the bundle (model stated by the author, 2026-10-13; the bundle's documentation does not name it). The records were made in that conversation's Linux sandbox: Python 3.13.5, mpmath 1.3.0 and SymPy 1.14.0 per `verification/general_d3/environment.json`, and working paths under `/mnt/data/`. |
| date | note revision "Three-dimensional half-shift revision: 11 September 2026" (title page of the bundle package's `long_range_ising_complete.tex`, not shipped); bundle consolidated 22 September 2026 |
| git | none. The bundle is not a git repository, so the entry has no `git_ref`. |
| extraction | unzipped read-only on 2026-10-13 by the Claude Code session C62d to `<PROJECT>/GFF/LRI_complete_research_bundle/` (its `EXTRACTED.md`) |
| changes afterwards | None to the package files. 198 of the 226 ship byte-identical; `public/BUNDLE_SHA256SUMS` (the bundle's own `MANIFEST.sha256`, pruned to this package) and the package's `archive_manifest.json` verify this in `make test`. Not shipped since 2026-10-16 (author rule: one TeX note per direction): the 9 TeX/PDF note files, merged into the condensed note Sections 17-19, and `history/` (19 superseded drafts); `public/dropped_paths.txt` names them, and the checksum lists keep their lines. Added for the release by the Claude Code session C63d (2026-10-13; dropped paths and the stricter list checks 2026-10-16): `public.mk` and `public/` (`replay.py`, `replaylib.py`, `BUNDLE_SHA256SUMS`, `dropped_paths.txt`, `README.md`, `requirements.txt`). |
| later use in the project | The three-dimensional section of the condensed note (Sec. "Three dimensions: half-shift determinants and rank-two functions") is condensed from the bundle's canonical note, whose appendices on d = 3 were added by this package (Appendix M) and by `lri_d3_matrix_update` (Appendix N). `LRI_C5_d3` (Claude, 2026-10-02) carries byte-identical copies of `code/general_d3/*.py`, `horn_arrays.json`, `identities.json` and `period_values.json` under `inputs/general_d3/` and uses the 90-digit P_5(3) for C5(3). The C6(3) power audit uses Q_3 and P_4(3) to 39 decimals (`GFF/code/lri_C6_d3_complete_update`). |
| overlap | 202 files byte-identical to `lri_general_periodization_update`, 177 to `lri_general_closed_update`, 191 to `lri_d3_matrix_update` (same relative paths) |

### `lri_d3_matrix_update`

Folder: `code/lri_d3_matrix_update/`.

#### Provenance: GFF/code/lri_d3_matrix_update

| item | value |
|---|---|
| origin | package 15, "d=3 rank-two identification", of the research bundle `LRI_complete_research_bundle.zip` (sha256 `3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0`, 4,064 entries) |
| original archive | `LRI_d3_rank_two_identification.zip`, sha256 `d4a8e3e6c1fb8d4c7eb4056859e981494f77cb9bcf31ca95e3a80db4de1a2800`, 207 files, 4,730,953 bytes (bundle `provenance/source_archives.json`) |
| written by | OpenAI GPT-6 astra, in the same ChatGPT research conversation as the rest of the bundle (model stated by the author, 2026-10-13; the bundle does not name it). No environment record exists for the new rank-two scripts; the inherited `verification/general_d3/environment.json` records Python 3.13.5 and mpmath 1.3.0. |
| date | note revision "Three-dimensional rank-two identification: 11 September 2026" (title page of the bundle package's `long_range_ising_complete.tex`, not shipped), made after the half-shift revision of `lri_d3_reduction_update`; bundle consolidated 22 September 2026 |
| git | none. The bundle is not a git repository, so the entry has no `git_ref`. |
| extraction | unzipped read-only on 2026-10-13 by the Claude Code session C62d (`<PROJECT>/GFF/LRI_complete_research_bundle/EXTRACTED.md`) |
| changes afterwards | None to the package files. 202 of the 207 ship byte-identical; `public/BUNDLE_SHA256SUMS`, the bundle's `MANIFEST.sha256` pruned to this package, verifies this in `make test`. Not shipped since 2026-10-16 (author rule: one TeX note per direction): `proofs/rank_two_appendix.tex` and `rank_two_identification.pdf` (merged into the condensed note Section 19) and the full builds `long_range_ising_complete.tex`/`.pdf` and `general_dimension_complete.pdf`; `public/dropped_paths.txt` names them, and the list keeps their lines. Added for the release by the Claude Code session C63d (2026-10-13; dropped paths 2026-10-16): `public.mk` and `public/` (`replay.py`, `replaylib.py`, `BUNDLE_SHA256SUMS`, `dropped_paths.txt`, `README.md`, `requirements.txt`). |
| later use in the project | The condensed note's subsections "The real rank-two hypergeometric normalization" and "Five loops: an exact three-term standard-function dictionary" come from this package's Appendix N, by way of the bundle's canonical note. The Supplemental Material of the paper (`app_closed_forms.tex`, eqs. cf:d3Q3, cf:d3matrixF, cf:d3h, table cf:tab:d3) restates the rank-two forms and the three period values. |
| overlap | 177 files byte-identical to `lri_general_periodization_update` and 191 to `lri_d3_reduction_update`, at the same relative paths |

### `LRI_C5_general_d`

Folder: `code/LRI_C5_general_d/`.

#### Provenance: LRI_C5_general_d (GFF/code/LRI_C5_general_d)

The package was written by Claude (Anthropic) in two Claude Code sessions on 2026-10-02 and 2026-10-03. Some of the work
was done by subagents of workflows started from those sessions. The author (Z. Zheng) directed the work and agreed the
split on 2026-10-02:

- **Session C62d** did 𝓛_d and Z_d: `foundation/`, `L/`, `Z/`, `specialize/`, `review/`, `RESULT.md`.
- **Session C63d** did the independent reference values (`refvals/`, `references/`) and 𝒦_d (`K_general/`).

No human-written code and no model other than Claude was involved. A grep for codex, gpt and openai outside `K_general/`
finds nothing; C63d reports the same for `K_general/`.

**State of the source.**

- The package is not a git repository, and it is not part of `LRI_complete_research_bundle.zip`.
- No file has changed since 2026-10-03 11:25 (`find -newermt 2026-10-04` finds no file). Only the directory entries of
  `K_general/` and `K_general/refcheck_verify/` changed, on 2026-10-12; that folder is not shipped.
- The export copies the working tree.
- The note ties itself to the package through a TeX comment (l.6091–6092 at fa71533) that gives `general_d.tex` md5
  c0c688e9 and `K_d_fragment.tex` md5 da91f60a. `general_d.tex` is not shipped; its text equals note Section 20, with 0
  differing non-comment lines. `K_d_fragment.tex` is merged into note Section 21 and not shipped either (one TeX note
  per direction).
- The md5 sums that the records pin on the code all match the shipped files:

  | file | md5 |
  |---|---|
  | `L/L_general.py` | 805c42c1 |
  | `Z/Z_general.py` | 6d2d7c59 |
  | `foundation/hypsums.py` | 9c9a4543 |
  | `review/lemmaG-numeric/lg_engine.py` | 9b5d269f |
  | `references/reference_values.json` | 905dae8d |
  | `K_general/R_part/rblocks.py` | 6652a7dd |

  `public/replay.py` checks them.

##### Section 20 part (session C62d)

| part | dates (file times) | how | changed afterwards |
|---|---|---|---|
| `foundation/` (general-b periodization and top-mode theorem; Horn engine `hypsums.py`, `wheel_general_b.py`; validation runs) | 2026-10-02 21:38 – 2026-10-03 09:33 | C62d, workflow wf_d50be76e-6af. Validation jobs 568940, 568959, 568967 on symmetry (amdq, 64-core AMD nodes). The TeX was revised for review fixes F1–F9, the product form (Theorem 6) and the lemmaG-proof items. | final 2026-10-03 09:33 |
| `L/` (five-Horn formula for 𝓛_d; jet engine) | 2026-10-02 22:47 – 2026-10-03 02:17 | same workflow; jobs 569035–569060, 569088 | TeX fixes F10–F13, 2026-10-03 02:17 |
| `Z/` (two-node formula for Z_d; exact-jet and Cauchy engines) | 2026-10-02 22:41 – 2026-10-03 02:18 | same workflow; jobs 568972, 569025–569037, 569087; `Z/spectral_ref/` runs C63d's `hp_general_d.py` unchanged | TeX fixes F14–F17, O1–O2 |
| `specialize/` (d = 1, 2, 3 specializations, C5 assembly, PSLQ probes) | 2026-10-02 23:43 – 2026-10-03 00:01 | C62d; jobs 569132, 569133; Mac checks at 30 digits | none (`gdr_test.*`, not shipped, 2026-10-03 08:02) |
| `review/` | 2026-10-03 00:00 – 11:23 | review workflow wf_1498e507-418 (five lenses; `VERIFICATION.md` written by its verifier); fix round wf_a382bd41-c4f; lemmaG-proof and lemmaG-numeric reviews (jobs 569336–569347, 569461); the joint review with C63d (four lenses and a synthesis; jobs 569478, 569482). The reviewers' check code and outputs are kept as they ran. | none |
| `RESULT.md` | 2026-10-03 09:33 | C62d, package summary | none |
| `general_d.tex`, `draft/` (not shipped) | 2026-10-03 | the fragment that became note Section 20; preview builds | merged into the note on 2026-10-03 by C63d (`merge/`, not shipped; git tag `backup/C63d_pre_gend` of the note marks the state before) |
| `refvals/`, `references/reference_values.json` | 2026-10-02 21:18 – 2026-10-03 01:21 | C63d, spectral code `hp_general_d.py` (jobs 568890–568921, 64-core nodes). `reference_values.json` (md5 905dae8d) was rebuilt by `refvals/build_refjson.py` at 01:21 with 50 printed digits; `Z/results/compare_refs.log` predates that rebuild. | none |
| `public.mk`, `public/{replay.py, replay_full.py, run_tests.py, check_DL_Phat.py, e2e_k3_public.py}`, `REVIEWS.md` | 2026-10-13 | C62d, public release (overlay, new files only) | — |

Computation:

- **symmetry cluster (Perimeter Institute), Slurm.** Partitions amdq (exclusive 64-core AMD nodes) and sharedq (8
  cores). The Python 3.11 module with a virtualenv; its mpmath version was not recorded.
- **Mac.** Quick checks.

The records reproduce byte for byte under Python 3.10.11 with mpmath 1.2.1 (macOS, 2026-10-13; `public/replay.py`).

##### Section 21 part (K_general/, session C63d)

*Written by C63d (`GFF/d3/K_general_for_C62d/PROVENANCE_K_d.md`) and merged unchanged.*


`K_general/` was written by Claude (Anthropic) in Claude Code session **C63d**, on 2026-10-02 and 2026-10-03, partly by
the subagents of one workflow run from that session. It was directed by the author (Z. Zheng). The split with C62d was
agreed by the user on 2026-10-02: C62d did L_d and Z_d (the rest of `LRI_C5_general_d`), and C63d did the reference values
and 𝒦_d. `LRI_C5_general_d` is not a git repository. No file of `K_general/` has changed since 2026-10-03 11:25. Only the
directory entry of `refcheck_verify/` changed, on 2026-10-12; that folder is not shipped.

| part | dates | how | changed afterwards |
|---|---|---|---|
| `S_part/`, `R_part/`, `position_space/`, `refcheck/` | 2026-10-02 21:40–23:11 | workflow wf_cdc3d90c-0ba (research agents). Cluster jobs: refcheck 568922–568970, R_part production 568941–568956 (τ-circles, settings A and B), on 64-core AMD EPYC Slurm nodes. The 100-digit position-space values took 20–75 s per d (`position_space/run_D100.log`; the log does not name the machine). | unchanged |
| `RESULT.md` | 2026-10-03 01:20, edited through 10:15 | workflow synthesis; "superseded in part" banner and corrections from the joint review (K10) and the repair rounds | final |
| `note_fragment/` (`K_d_fragment.tex`, `STATUS.md`, `growth/PROOF.md`, `topmode/PROOF.md`, `fragment_checks/`, `test_build_joint/check_*`) | 2026-10-03 01:39–10:16 | C63d, with fix rounds 1–2, the joint-review fix round, repair rounds 1–2 and final nits. Final fragment md5 da91f60a. Top-mode jobs 569317 (three-node jets) and the per-spin probes; the joint review's circles were job 569482. | final; merged into the note as Section 21 on 2026-10-03 (git tag `backup/C63d_pre_gend` is the state before the merge) |
| `public/replay_K_d.py`, `public/expected_K_d.json` | 2026-10-13 | C63d, public release (overlay) | new files only |

Inputs from outside `K_general/`:
- `references/reference_values.json`, produced by C63d on 2026-10-02 (21:56; updated 2026-10-03 01:21) with
  `refvals/hp_general_d.py`;
- `review/joint/numerics-end-to-end/k3_jets.json`, from the joint review;
- the 430-digit 𝒦_3 of `../LRI_C5_d3/wf_K3/K3_value.json` (session C63d, 2026-10-02).

### `LRI_C5_d3`

Folder: `code/LRI_C5_d3/`.

#### Provenance of GFF/code/LRI_C5_d3 (C5(3) and the d = 3 masters)

The work was directed by the author (Z. Zheng). Everything in the package was written by Claude (Anthropic) in one Claude Code
session, C63d, on 1–2 October 2026, and by the subagents of one workflow run from that session. The exceptions are the
inputs under `inputs/general_d3/`. No human refereed it. The package is not a git repository. Its files were last
changed on 2026-10-02 at 11:40 and have been read-only since then.

| part | origin and date | written by | changed afterwards |
|---|---|---|---|
| `assemble_c5_d3.py`, `compute_c5.py`, `pslq_d3.py`, `hp_masters_d3.py`, `hp_part.py`, `hp_combine.py`, `README.md` | 2026-10-01 23:57 to 2026-10-02 01:07, at the user's request "simplify C5(3) as much as possible" | Claude, session C63d | unchanged |
| `run_A_dps50.json`, `run_B_dps56.json` | spectral runs A and B, Slurm jobs 567344 and 567345, 2026-10-02 00:20–00:31 (one 64-core AMD EPYC node each) | produced by `hp_masters_d3.py` | unchanged |
| `run_C_b.json`, `run_C_t.json`, `run_C_combined.json` | spectral run C, jobs 567508 and 567509, 2026-10-02 01:09–02:08; combined locally | `hp_part.py`, `hp_combine.py` | unchanged |
| `masters_d3.json`, `pslq_d3.log`, `c5_value.json` | 2026-10-02 00:32 | `pslq_d3.py`, `compute_c5.py` | unchanged; regenerated byte-identically on 2026-10-13 (replay) |
| `WORKFLOW_RESULT.md`; `wf_K3/`, `wf_L3/`, `wf_Z3/`, `wf_d2check/` | workflow wf_d8d88d50-343, 2026-10-02 01:19–02:56: four research agents (L3, Z3, K3, d = 2 cross-check) and three adversarial verifiers per positive claim, 62 agents in all. Cluster jobs: wf_L3 567552–567553, wf_Z3 567521–567522, 567665–567666, 567673–567674 (and superseded 567519–567520), wf_d2check 567514–567517 and 567669–567672 | Claude subagents; synthesis by C63d | unchanged |
| `inputs/general_d3/` | byte-identical copy of `code/general_d3/` and of three files of `verification/general_d3/` of the research-bundle package `lri_d3_reduction_update` (the September 2026 research conversation that produced `LRI_complete_research_bundle.zip`, sha256 3715f545…). Copied on 2026-10-02. | as the bundle (see the bundle_d3 draft for its provenance) | unchanged |
| `public.mk`, `public/` | public release, 2026-10-13 | Claude, session C63d (closed_forms_3 draft) | new files only. No shipped file is modified. |
| `../../results/closed_forms_3/LRI_C5_d3_quoted.json` | public release, 2026-10-13; strings copied from the note at fa71533 and from the paper draft | Claude, session C63d | new |

##### How the results entered the note

- 2026-10-03: C63d merged Sections 20 (gdr, from C62d) and 21 (gdk, K_d) into the condensed note. In the same edit it
  added the 50-digit C5(3) to Section 19.8 ("value only", by the user's choice). The structural forms of Z3 and L3 entered
  only through Section 20.4. The pre-merge state is the note git tag `backup/C63d_pre_gend`.
- 2026-10-08 to 10-10: Section 1.1 gained the d = 3 status paragraph with the 50-digit C5(3), at commit 8fd41ff and
  later commits.
- Section 33 (note fa71533) cites `LRI_C5_d3/` with `WORKFLOW_RESULT.md`, `wf_L3/` and `wf_K3/K3_value.json`.
- Until 2026-10-14 the d = 3 paragraph of the paper's closed-form appendix (`paper/sections/app_closed_forms.tex`)
  quoted L3, Z3, 𝔡_H and 𝔡_a from `wf_L3/` and `wf_Z3/`; the author removed that paragraph that day. These four
  values are printed neither in the final paper (f496d39a) nor in the note; the replay still checks them against the
  records.

##### Later checks

- 2026-10-03, joint review of the generic-d sections: its end-to-end evaluation of C5(3) by the generic-d route agrees
  with `c5_value.json` to 7.8 × 10⁻⁴⁶ (five-node K3) and 5.2 × 10⁻⁴⁵ (three-node K3). The note quotes 5 × 10⁻⁴⁵.
- 2026-10-13: the public replay regenerated every record that a script writes (`masters_d3.json`, `pslq_d3.log`,
  `c5_value.json`, `run_C_combined.json`, the L3 constants, the derived Z3 data, `wf_d2check/run4_combined.json`)
  byte for byte, and recomputed every quoted number (`replay_local_run.txt`).

## C6(1) and its analytic representation

### `LRI_C6_1D_HPC`

Folder: `code/LRI_C6_1D_HPC/`.

#### Provenance: `GFF/code/LRI_C6_1D_HPC`, `GFF/results/C6_1`, `GFF/data/C6_1`

##### Authors

- **Plan, engine, tools, cluster scripts, production and report:** a Claude Code session (model claude-opus-5-5,
  1M context), 2026-09-28 to 2026-10-01. The user asked for the run ("make it as precise as you can", run on
  symmetry).
- **Reviews:** Codex CLI 0.158.0, model gpt-6-astra, effort xhigh. There were plan reviews, code inspections and
  a results review; see REVIEWS.md.
- **`reference/`:** a verbatim copy, made at the baseline commit a4d1ec8, of `lri_C6_numerical_update/reproduction`.
  That package produced the earlier Monte Carlo value 14331.8 ± 0.5. It came from the ChatGPT research
  conversation that produced the September 2026 bundle (archive `LRI_1d_C6_numerical_calculation.zip`, sha256
  `511615ec…`, recorded in `GFF/LRI_complete_research_bundle/provenance/source_archives.json`). The model was OpenAI GPT-6
  astra (stated by the author, 2026-10-13; the files name no model). The copy differs from the bundle member in three ways:
  - `C6_result_original.json` and `README_original.md` are the package's `verification/C6_result.json` and
    `README.md`, renamed;
  - `C6_stratified_analysis.json` differs from the bundle copy in the last digits of a few covariance entries,
    because the local reanalysis was rerun before the copy;
  - `l5_N12.log` was added.
- **Public scripts** (`public.mk`, `public/`): a C71d helper session (Claude Code), 2026-10-13.

##### Git history of `LRI_C6_1D_HPC` (local repository, no remote)

| Commit | Date (EDT) | Content |
|---|---|---|
| a4d1ec8 | 2026-09-28 21:20 | baseline: `reference/` copied verbatim |
| 81dd2c6, 33ecb6f | 2026-09-29 10:08 | engine, tools and symmetry scripts (plan rev 8); env fix |
| b67122a, 88626f1, b0763b4 | 2026-09-29 10:17–10:49 | inspection rounds 1–3 fixes (the last uninspected) |
| 38f8847 | 2026-09-29 11:38 | portable AVX2 / x86-64-v3 engines, amdq-first routing (uninspected; revalidated) |
| **8680864** | 2026-09-29 12:33 | V11 cross-vendor long-double tolerance. **Production revision**: validation attempt 20260929T123319_8680864 passed; every level header records `git 8680864` |
| 0fa50ca | 2026-09-29 21:28 | results committed: C6(1) = 14331.68703277 ± 0.00000049 |
| ee2e013 | 2026-10-01 15:30 | results review RR-002: `tools/c7_crosscheck.py`, `C7_crosscheck.json`, REPORT; `tools/analyze.py` loses its hardcoded C7 by-product |
| **cef6fa7** | 2026-10-01 15:31 | results review RR-001: `tools/lowercheck.py`, `tools/lowercmp.py`, `lower_amplitude_precision/`, REPORT addendum. **HEAD; shipped** |

The working tree is clean at cef6fa7. The export pins `git_ref: cef6fa7`, both for the code and for
`results/2026-09_symmetry`.

##### What changed after the production commit

`git diff 8680864 cef6fa7` touches only:
- `results/` (added);
- three new tools: `c7_crosscheck.py`, `lowercheck.py`, `lowercmp.py`;
- three lines of `tools/analyze.py`. The hardcoded constant `C7_BYPRODUCT = 14331.62055 ± 0.30500` and the
  diagnostic `C7_package_byproduct` built from it are replaced by the pointer string
  `diagnostics.C7_package_crosscheck`.

`src/`, `cluster/`, `tests/`, `reference/`, the Makefile and every other tool are identical to 8680864. The
source hash 0e94a97c… equals the approved identity. Consequences:
- `C6_final.json` was written by the 8680864 version of `analyze.py`. The shipped (cef6fa7) version reproduces it
  byte for byte once that one diagnostic entry is restored (`public/replay_c6.py`, function
  `substitute_byproduct`; check B04). Every other output, `assembled.json`, `rounding.json` and the four decision
  files included, regenerates bitwise without any substitution.
- REPORT.md was edited after 0fa50ca, in ee2e013 and cef6fa7. The two later edits added the C7 stage table and
  the RR-001 addendum.

##### Records and data

- **`GFF/results/C6_1/`** is `results/2026-09_symmetry` at cef6fa7, minus two logs (`SUBMITTED.txt`,
  `c6drv_565751.out`).
  - The records were written on symmetry on 2026-09-29 by `tools/assemble.py`, `rounding.py` and `analyze.py`,
    run by the operator script `ops/analyze_job.sh`. The validation files were written by the gate jobs of
    attempt 20260929T123319_8680864.
  - `C7_crosscheck.json` and `lower_amplitude_precision/` date from 2026-10-01. The two lower-amplitude reruns were
    symmetry jobs 566954 and 566955.
- **`GFF/results/C6_1/PLAN.md`** is `LRI_C6_1D_HPC_loop/PLAN.md`, sha256 `383df29a…`, last modified 2026-09-29
  12:33, before production began at 13:26. Its first 457 lines are byte-identical to the Codex-approved rev 8
  (`PLAN_rev8_APPROVED.md`, sha256 `afa259b7…`). The rest is Sec 9, the build-phase amendments.
- **`GFF/data/C6_1/levels/`** (62 files), **`runs/`** (84 files) and **`analysis/resources_N{16,18,20}.json`**
  were copied from symmetry `<SCRATCH>/lri_c6_1d/{levels,runs,analysis}` into
  `LRI_1d_through_C6/data/C6_exact_all_graph_sums_2026-09_symmetry/` on 2026-10-02.
  - They verify against `LRI_1d_through_C6/MANIFEST.sha256` (sha256 `9d2ed15a…`; also in `LRI_1d_through_C6.zip`,
    sha256 `87a46614…`).
  - Their hashes are bound by `assembled.json`, `rounding.json`, the decision files and the level records'
    `inputs_sha256`.
- **Not shipped, but regenerated or bound by hash:**
  - the executables `c6sum` (4cae933b…) and `c6sum_ld` (011ec407…), built on symmetry with gcc 11.2.0;
  - the graph files `graphs6.bin` (8044c4ff…) and `graphs7.bin` (f97d2f79…), which `bin/enumerate` regenerates
    bitwise (`smoke` checks graphs6);
  - the 42 weight files, which `tools/weights.py` regenerates bitwise (`replay` check B09).

##### Hash-bound files (ship byte-identical; never scrub)

| Record | Binds by sha256 |
|---|---|
| `results/C6_1/C6_final.json` | `assembled.json`, `rounding.json`, all 62 level files (by name), `weights_manifest.json`. It is itself bound by `C7_crosscheck.json` and read by the C6 analytic replay (`3ff496c2…`) |
| `assembled.json`, `rounding.json` | the level files they read (41 and 42 names), `weights_manifest.json` |
| `decisions/decision_N{16,18,20,22}.json` | the N* light and hard level files, and the stage `assembled.json`/`rounding.json` (N22: the shipped ones; N16–N20: regenerated by `replay`) |
| `validation/APPROVED.json` | `src/c6sum.cpp`, the two executables, `graphs6/7.bin`, `weights_manifest.json` (and the symmetry `code_dir`) |
| `weights_manifest.json` | the 42 weight files |
| `C7_crosscheck.json` | `C6_final.json` and `LRI_C7_HPC/results/2026-09_expanse_v2/C7_final.json` (`b44b3a13…`), keyed by project-relative labels |
| `data/C6_1/levels/*.json` | their run files in `data/C6_1/runs/` (keyed by symmetry paths), and in their headers the source, executable, graphs and weights |
| `data/C6_1/runs/*.jsonl` | in their headers the source, executable, graphs and weights |

These files also contain cluster paths (`<SCRATCH>/…`), node names (`<NODE>`…) and the user name. They
are bound and must not be scrubbed. `REPORT.md`, `PLAN.md`, `cluster/*` and `README.md` are not bound and may be
scrubbed. `public/slurm/adapt.py` matches the site lines of `cluster/` by pattern, so it works on either form.

##### Checksum lists

The package has no checksum list (SHA256SUMS or MANIFEST). `LRI_1d_through_C6/MANIFEST.sha256` is not shipped; its
150 lines for the shipped data files (62 levels, 84 run files, 4 resource records) verify. The expected sha256 of the shipped records are pinned in
`public/replay_c6.py` (`EXPECT`).

### `C6_research_note`

Folder: `code/C6_research_note/`.

#### Provenance: analytic representation of C6(1)

##### `GFF/code/C6_research_note` (the calculation)

- **Origin.** Delivered as `C6_final_method_research_package.zip` (6,627,273 bytes, sha256
  `64cea418f1e0007474c8b54dd3b688136f17e2b28922111da71947c9cb7e3ddc`, 1081 files, all members dated 2026-10-07),
  saved on 2026-10-07 21:47 and unpacked to `<PROJECT>/GFF/C6_research_note/` at 21:48. The folder is not a git
  repository; `diff -rq` against the zip shows it byte-identical apart from Finder `.DS_Store` files, and its
  `MANIFEST.sha256` (1080 lines) verifies in full. It was not modified afterwards (the review of 8 October ran its
  audits on a scratch copy).
- **Who produced it.** The files do not name an author or a model. The PDF author field reads "C6 research project:
  source-based consolidation". The package was assembled in a sandbox (Python 3.13.5, Linux, `/opt/pyvenv`,
  `provenance/environment.json`) from 42 stage archives such as `C6_complete_interval.zip` and
  `C6_central_binomial_wheel_reduction.zip` (`provenance/source_manifest.json` gives the archive and member of every
  stage file), and several stage scripts and records refer to "conversation export" paths under `/mnt/data`
  (`provenance/portability_patches.json`, `provenance/archival_tools.json`). The supplied setup
  (`inputs/upstream_reduced_setup.md`) speaks of "the corrected renormalization-group reduction supplied in this
  conversation". These are the marks of a chat-assistant code sandbox; the project memory calls it a GPT-sandbox
  package. **Open question for the author:** confirm the system (ChatGPT / GPT-6 astra?) and the dates of the stage
  sessions.
- **Editions.** `provenance/editorial_revision.json`: a "final-method-only LaTeX editorial revision" of a 34-page
  progress note (TeX sha256 `689e81ae...`) to the shipped 28-page note (`2f6d7f9d...`), with 22 protected equations
  hashed and "mathematical_result_changed": false. During that revision 21 of the 22 selected tasks were executed
  afresh; the `residual_intervals` record was kept from the source package. No Wolfram kernel was run.
- **Upstream input.** The reduced analytic expression, its two restored Laurent coefficients (R_{147,-3} =
  R_{148,-3} = 2/5) and several identities were supplied to the package, not derived in it (README "Mathematical
  scope"; `inputs/upstream_setup_provenance.json`). The graph-to-period reduction and the RG assembly are not
  reconstructed anywhere in the package.
- **Use in the condensed note.** Section 22.9 (commit `65c895c`, 2026-10-08); the value became the reported C6(1)
  in Section 1 and a new Section 1.1 on 2026-10-10 (`c053310`, then `c4209da`, `8fd41ff`, where it became Section 1.2,
  and `92b1b30`). The current note commit is `fa71533` (2026-10-13).
- **What the public export changes.** Nothing inside the shipped files. It leaves out 25 of the 42 stage folders
  and the run records of the 9 tasks outside `code/reproduce_final.py` (`public/dropped_paths.txt`), and adds
  `public.mk` and `public/` (written for the public release by a Claude Code helper of session C71d, 2026-10-13).

##### `GFF/code/LRI_C6_closed_form_review` (the independent review)

- Written on 2026-10-08 by Claude Code session C71d with three independent check agents (REVIEW.md, first line;
  file times 18:27 to 19:13). The check helpers say they were "written from scratch for this review"
  (`checks/reduced_input/tools.py`); no package code is used except reading the package's `outputs/reassembly.json`
  for comparison. Run with Python 3.10.12 (`mambaforge` "sage" environment: mpmath 1.3, scipy 1.11, sympy 1.12,
  numpy 1.24). Not a git repository; not modified after 2026-10-08 except for the `note/` merge scripts (not shipped),
  which C71d used on 2026-10-08 and 2026-10-10 to write Sections 22.9 and 1.2 of the condensed note.
- The public export leaves out `note/` and six development probes, and adds `public.mk` and `public/` (2026-10-13).

##### `GFF/results/C6_1/analytic/quoted_numbers.json`

Written for the public release (2026-10-13) by transcribing the numbers of the condensed note at commit `fa71533`
(Sections 1, 1.2, 22.1, 22.9, 22.10), the package note's `\Crefval` and REVIEW.md.

### `LRI_C6_closed_form_review`

Folder: `code/LRI_C6_closed_form_review/`.

_no separate text._

## Finite kernels, power compensation, C6(2) and C6(3)

### `lri_C6_d2_complete_update`

Folder: `code/lri_C6_d2_complete_update/`.

#### Provenance: lri_C6_d2_complete_update and the inherited d = 2 kernels

##### Who wrote what

- **Authorship.** OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the research bundle (model stated by the author, 2026-10-13) wrote all four packages of the inherited d = 2
  construction, each delivered as a zip:

  | # | Package | Delivered as | sha256 | Date |
  |---:|---|---|---|---|
  | 18 | `lri_C6_d2_primitive_update` | `LRI_C6_d2_primitive_progress.zip` | f5025a08… | ≤ 14 Sep 2026; the TeX it carries is dated 11 Sep |
  | 19 | `lri_C6_d2_subtraction_update` | `LRI_C6_d2_local_subtraction_progress.zip` | 161e17ae… | ≤ 14 Sep 2026 |
  | 20 | `lri_C6_d2_two_forest_update` | `LRI_C6_d2_two_forest_and_gamma_progress.zip` | 7fe3c5bf… | 14 Sep 2026 |
  | 21 | `lri_C6_d2_complete_update` | `LRI_C6_d2_complete_numerical.zip` | e34f5436… | 14 Sep 2026 |

  Evidence: the research archive describes them as products of "the research conversation", and three files carry the
  sandbox path `/mnt/data/...`. Neither package nor archive names the model. Each package builds on the previous ones;
  package 21 carries a nested copy of 20 (`reproduction/lri_C6_d2_two_forest_update/`, 138 of its 151 files).
- **Consolidation.** On 22 September 2026 the same conversation consolidated all its packages, unchanged, into
  `LRI_complete_research_bundle.zip` (160,075,850 bytes, sha256 3715f545…ca0). On 13 October 2026, C62d extracted it
  read-only to `GFF/LRI_complete_research_bundle/` for this export. The bundle manifest verified 754/754 lines for packages
  18–21, and package 21's `SHA256SUMS.json` verified 487/487.
- **Not git.** There is no commit. The export copies a subset of package 21 byte for byte (192 files) and adds `public.mk`,
  `public/{common,test,replay,regen}.py` and `REVIEWS.md` (written by Claude Code session C62d, 13 Oct 2026).
- **No later edits.** Nothing in the shipped files changed after delivery.

##### How the current calculation uses it

The 2026 C6(2) production (`LRI_C6_D2_HPC` at 6aaf656; its provenance is in the C6_2 unit) reads only byte copies. Its `reference/` tree is package 24 of the archive in full. That tree contains 21 files of package 21 (rates, two-loop
reference, fixed-point map, the three power records), and the forest kernels `forest_L3..L6.txt`, byte-identical to package
21's, filed under the name of the d = 3 package. Its
`inputs/manifest.json` pins nine of these by sha256, and the C6(2) result pins that manifest. The one physics input the
production takes from package 21 without recomputing it is the power-sector compensation (Delta_p ≈ 0), which this
release replays and regenerates.

##### What changed afterwards

Nothing in the shipped files. The note text that reports these results was condensed later, in the
`GFF/LRI_condensed_note` git history. Two rounding errors carried over from the package's own TeX (7.39e-30, −8.03e-34)
were found by the replay; they are corrected in `note_changes.md`.

### `lri_C6_d3_complete_update`

Folder: `code/lri_C6_d3_complete_update/`.

#### Provenance: GFF/code/lri_C6_d3_complete_update (audit subset)

| item | value |
|---|---|
| origin | package 22, "First full C6(3)", of the research bundle `LRI_complete_research_bundle.zip` (sha256 `3715f5453ffefca6cad94bbf26b5697417db17a136db933dfc74c1841c794ca0`, 4,064 entries) |
| original archive | `LRI_C6_d3_complete_numerical.zip`, sha256 `5c2925485b1a8f8c88d50ac43843310ed0d9e14a70d93f0e5ac11293ee2a93b7`, 165 files, 55,113,499 bytes (bundle `provenance/source_archives.json`) |
| written by | OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the bundle (model stated by the author, 2026-10-13; the bundle does not name it). Environment per `verification/environment.json`: Python 3.13.5, NumPy 2.3.5, mpmath 1.3.0, SymPy 1.14.0, networkx 3.6.1, g++ 14.2.0 (Debian), 4 threads. The unshipped run manifests record working paths under `/mnt/data/c6d3_work/`. |
| date | "Three-dimensional numerical sixth order: 14 September 2026" (title page of the package's note; `C6_d3_complete.tex` is dated 14 September 2026); bundle consolidated 22 September 2026 |
| git | none, so the entry has no `git_ref`. A byte-identical copy of the full package (165 files; the only difference is an untracked `.DS_Store`) is tracked as `reference_d3/` in the Claude-built `LRI_C6_D3_HPC` (commit 1c6dfb3; its `provenance/source_archives.json` gives the same archive sha256). |
| extraction | unzipped read-only on 2026-10-13 by the Claude Code session C62d (`<PROJECT>/GFF/LRI_complete_research_bundle/EXTRACTED.md`) |
| shipped | 37 files (7,678,637 bytes), byte-identical. `public/BUNDLE_SHA256SUMS` (all 165 bundle hashes) and the package's `verification/file_checksums.json` verify them in `make test`, with ignore-missing for the 128 unshipped files. |
| changes afterwards | None to the shipped files. Added for the release by the Claude Code session C63d (2026-10-13): `public.mk` and `public/` (`replay.py`, `replaylib.py`, `BUNDLE_SHA256SUMS`, `README.md`, `requirements.txt`). |
| later use in the project | The C6(3) estimators that followed all use this package's retained analytic power compensation: `lri_C6_precision_update`, `lri_C6_method_update` (33.57 ± 0.10), and the production `LRI_C6_D3_HPC` (33.5754 ± 0.0005, 2026-09-29). They do not redo it; `LRI_C6_D3_HPC/tools/assemble.py` records "Uses the retained analytic compensation of the reference finite-MOM calculation, not a fresh independent power-sector audit". The note's d = 3 power-compensation and finite-scheme subsections are condensed from this package's Appendix V, by way of the bundle's canonical note. |
| superseded content (not shipped) | the first full C6(3) estimate 33.50 ± 0.6 (raw 33.50373572295422, sampling SE 0.13085), its C++ sampler, inputs, batch vectors, pilots, valuations, logs and note snapshots |

### `LRI_C6_D2_HPC`

Folder: `code/LRI_C6_D2_HPC/`.

#### Provenance of C6(2) (GFF/code/LRI_C6_D2_HPC, GFF/data/C6_2, GFF/results/C6_2)

##### Who wrote what

| Part | Author | Evidence |
|---|---|---|
| Earlier method-refinement calculation (`reference/`: kernels, Sobol sampler, finite-MOM inputs, archived raw production records, the superseded estimator 362.3489138 ± 0.1526445, its note and audits) | OpenAI GPT-6 astra, in the ChatGPT research conversation that produced the research bundle (model stated by the author, 2026-10-13) | byte-identical to package `lri_C6_method_update` of the research bundle `LRI_complete_research_bundle.zip` (sha256 3715f545...), which consolidates the deliveries of that ChatGPT conversation |
| HPC package as delivered (`src/`, `tools/`, `tests/`, `inputs/`, `slurm/`, `docs/`, `benchmarks/`) | OpenAI GPT-6 astra (model stated by the author, 2026-10-13), delivered as `LRI_C6_D2_HPC_optimized.zip` (sha256 55ec6457fdf7b69cc934abd6d6b4b3ea368b011756b38edd4e56c66fe2d0361b, 1,391 files) on 28 September 2026 (its environment record shows a Debian sandbox with GCC 14.2, Python 3.13.5 and a 4-CPU quota, like the ChatGPT deliveries) | git baseline 3e643c8 (the delivered files, without the prebuilt executable) |
| Expanse readiness: job-private runtime, assembly input checks, resumable merge, status and recovery, array windows, hashed seeds, Neyman primitive split, submission guards, tests and docs (commits 7293480..6aaf656, 20 commits, 28 September 2026) | Claude Code (Opus 5.5) under OpenAI Codex review | `CHANGELOG.md`; REVIEWS.md |
| Production campaign (plan, preflight, submission, recovery, merge), local copy, campaign record | Claude Code session | `GFF/results/C6_2/CAMPAIGN.md` |
| Note text of Section 24.6 and the C6(2) entries (1 October 2026) | Claude Code session C62d | note git history |
| Release files (`public.mk`, `public/*.py`, `REVIEWS.md`, CAMPAIGN.md rewrite, data and results READMEs) | Claude Code session C62d (build agent), 13 October 2026 | this folder |

The numerics were not changed after delivery: between 3e643c8 and 6aaf656, `src/c6_integrate.cpp` and `reference/` are
unchanged, `src/kernel.hpp` gains only a test-only hook (`C6_FORCE_LEVEL`, compiled only in a test), and the production
executable built with GCC 13.3 on Expanse from either commit has the same sha256 (5818340b...). `inputs/` gains source
digests (`two_loop.json`, `primitive_reference.json`, `manifest.json`) and the frozen primitive allocation table.

##### Source commit and what came after

- **6aaf656** (6aaf656e6fc71e83ab6205097f98de3c4e9e6ed6, 28 September 2026 15:43 EDT): the code of the production; the
  frozen plan pins its tools. Released at this commit.
- **5545ea7** (16:34 EDT) and **bf7d0ab** (17:21 EDT): validation evidence only (real-Slurm recovery and status-line
  drills on a personal workstation and on Expanse, build identity, full test suite), with updated checksum list; no
  code, test or doc change. Not released (the evidence lives under `benchmarks/`).
- The production copy on Expanse was the 5545ea7 tree (`checksums.py verify`: 1,595 files), identical to 6aaf656 in all
  code files.

##### Dates

| Date (2026) | Event |
|---|---|
| 28 Sep, morning | delivery; code review (Claude Code, with native runs on Expanse) |
| 28 Sep, 11:32–15:43 EDT | fix loop with Codex plan reviews and code inspections; final code 6aaf656 |
| 28 Sep, 16:34–17:21 EDT | final validation on a personal workstation and on Expanse (evidence commits) |
| 28 Sep, 16:47–20:43 PDT | production on Expanse (plan, preflight, 428 elements, merge) |
| 29 Sep | run archived in two verified private copies; four submission-layer defects found by the three-dimensional sibling's review (production unaffected) |
| 1 Oct | note updated (first 362.37 ± 0.01, then the author's rounding step 0.001: 362.366 ± 0.004); Codex results review approved in round 2 |
| 13 Oct | release: replay, remerge and integrity tools added; the merge re-run byte for byte from the checkpoints |

### `LRI_C6_D3_HPC`

Folder: `code/LRI_C6_D3_HPC/`.

#### Provenance of C6(3) (fragment for GFF/PROVENANCE.md)

The author, Z. Zheng, directed all of the work. The package was written and delivered by OpenAI GPT-6 astra. Claude Code
sessions reviewed it, made it production-ready, ran the production and wrote the reports. OpenAI Codex (model
gpt-6-astra, effort xhigh) reviewed the plan, the code and the result. There was no human referee.

##### Code: `GFF/code/LRI_C6_D3_HPC`

| stage | commit / date | by | what |
|---|---|---|---|
| delivered package | `6e642ca` (2026-09-28) | OpenAI GPT-6 astra (stated by the author, 2026-10-13), received as `LRI_C6_D3_HPC_optimized.zip` (sha256 `06e5caa6b2ba108c370ca6bb48710ef01317c77cfb4c7e7a9d2f0dd7a5a3e110`; its 1,563 file names equal the commit's). The `/mnt/data/...` working paths in its records are those of a ChatGPT sandbox. | The d=3 port of the delivered C6(2) HPC package (`LRI_C6_D2_HPC_optimized.zip`, sha256 `55ec6457…`), built on the archived d=3 calculation (`LRI_C6_d3_complete_numerical.zip`, sha256 `5c292548…`). It contained `reference/` and `reference_d3/` unchanged, plus the optimized worker. |
| review | 2026-09-28 | Claude: three read-only reviewers, runs on a workstation (Slurm jobs 946–951) | Verdict: numerics sound. Findings: the d=2 findings M1–M3 and L1–L19 carried over, and the d=3 findings D3-1…D3-6. |
| Expanse readiness | `cd5ed32` … `73d3635` (final code), `1c6dfb3` (delivery: evidence, docs, checksums), 2026-09-28 | Claude (host and builder) | The reviewed C6(2) orchestration (`6aaf656`) was ported with the d=3 port re-applied. Every finding was fixed. The native numerics are frozen: the baseline and final sources build to the identical binary. |
| inspection | 1c6dfb3 | Codex gpt-6-astra | APPROVED in inspection 3; no uninspected edits after it |
| public overlay | 2026-10-13 | Claude (C63d drafting) | `public.mk` and `public/` (replay, shipped-file check, Slurm templates, README, REVIEWS). Nothing of `1c6dfb3` was changed. |

The production ran a `git archive` export of `1c6dfb3`. The four tools bound in its `manifest.json` (`production.py`,
`assemble.py`, `common.py`, `prepare_inputs.py`) and `inputs/manifest.json` are byte-identical to that commit;
`make replay` checks this.

Inherited trees (not written in this project; written by OpenAI GPT-6 astra in the research conversation that produced the bundle):
- `reference/` is the research-bundle package `lri_C6_method_update` (the refinement campaigns and the previous
  estimator). Its `baseline_previous/` is `lri_C6_precision_update`, which carries the trimmed
  `lri_C6_d3_complete_update` and `lri_C6_d2_complete_update` inputs.
- `reference_d3/` is the bundle package `lri_C6_d3_complete_update` (the first full C6(3)).
- All of them are byte-identical to the bundle `LRI_complete_research_bundle.zip` (sha256 `3715f545…`), apart from
  one `__pycache__` folder.
- `reference/` ships once, in `GFF/code/LRI_C6_D2_HPC/reference/`: its git tree `d4203b17e249ecb06ea213a59537bdd8192d803f`
  is the same at `LRI_C6_D2_HPC` `6aaf656` and at `LRI_C6_D3_HPC` `1c6dfb3`, and `diff -rq` of the two working trees
  shows no difference (2026-10-13).

The `inputs/` tree (per-graph kernels, frozen allocation, Γ and two-loop data) is generated from `reference/` by
`tools/prepare_inputs.py`. `tests/check_inputs.py` regenerates it byte for byte.

##### Records: `GFF/results/C6_3`

- Written by the production on SDSC Expanse, 2026-09-29, 07:08–10:14 PDT:
  - plan: srun job 54515878;
  - preflight element 54515885_0 and thread-identity check 54515886;
  - array 54516761;
  - merge 54516762.
- Seed 3864037981285414462; campaign tag `c6:624815e78a23`.
- The records are byte-identical to the production. `manifest.json` names the package path on the cluster
  (`/home/<user>/c6d3_prod/pkg`); it is bound by sha256 in `C6_result.json` and in every `merged.json`.
- `CAMPAIGN.md` was written by Claude. Its text has five dated parts:
  - the reporting rule, proposed at launch and confirmed by the author on 2026-09-29 at 09:06 PDT, before any
    production result existed;
  - the result (2026-09-29);
  - Amendment 1 (2026-10-01, the author's request, after the result: rounding step 0.001 → 0.0001);
  - errata from the Codex results review (2026-10-01).
- The complete run directory (`GFF/data/C6_3/run-20260929-m8192_full.tgz`, hosted) was archived on 2026-09-29. Its
  sha256 is `b11b7874…`.

##### Not exported

The package review (`LRI_C6_D3_HPC_review/`), the fix-loop plan and logs (`LRI_C6_D3_HPC_loop/`) and the results
review (`LRI_C6_D3_results_review/`) are summarized in `REVIEWS.md`. Also not exported:
- `provenance/`: the verbatim d=2 predecessor source and the port and fix-port diffs;
- `reference_d3/` apart from one file;
- the Expanse drills, smoke campaign, pilot and calibration logs.

The list is in `export_entries.json`.

## Full C7(1), C7(2), C7(3)

### `LRI_C7_HPC`

Folder: `code/LRI_C7_HPC/`.

#### Provenance: LRI_C7_HPC and the C7(1) result

##### Who wrote what

| Part | Author | When |
|---|---|---|
| `reference/`: the seven-loop calculation (graph inventory, coordinate forests, binary-cluster sampler, meromorphic radial quadrature, controls, affine assembly, archived streams, TeX derivation) | the September 2026 research bundle's package `lri_C7_complete_update`, delivered by GPT-6 astra (OpenAI; attribution by the author, the files name no system) | September 2026 (files dated 2026-09-23) |
| Optimized HPC implementation (`src/`, first versions of `tools/`, `tests/`, `cluster/`, `docs/`, `benchmarks/`) | GPT-6 astra, delivered as `LRI_C7_HPC_optimized.zip` (30,877,961 bytes, sha256 fc818c0258823237c6be0f3f35255a4ba449d050e6810b050fae2e8127dd6f4c, 479 files dated 2026-09-23); its benchmark records carry the delivering sandbox's `/mnt/data/c7_optimization_work` paths | 2026-09-23 |
| Review fixes, degree-7 check, production tooling (`tools/campaign.py` integrity layer, `production.py`, `assemble.py` diagnostics and allowance, `combine.py`, `design.py`, `toolchain.py`, new tests, Slurm fixes, `inputs_extra/` degree-7 weights, documentation) | Claude Code (Claude Opus 5.5, coordinator plus Claude helper agents), reviewed by Codex gpt-6-astra | 2026-09-25 to 2026-09-26 |
| Direct primitive sector and parallel combine (PLAN2) | Claude Code, reviewed by Codex gpt-6-astra | 2026-09-26 |
| Expanse production, results and report | Claude Code (session C71d), on SDSC Expanse | 2026-09-25 to 2026-10-01 |
| Public replay layer (`public.mk`, `public/`) | Claude Code (helper of C71d) | 2026-10-13 |

##### Repository history (`LRI_C7_HPC`, git, branch main; local only)

| Commit | Date (EDT) | Content |
|---|---|---|
| c21b9e8 | 2026-09-25 22:15 | baseline: the delivered package, byte-identical to the zip (479 files) |
| 3213ce0 | 2026-09-25 23:53 | review fixes, degree-7 check, production tooling; **frozen copy on Expanse: the workers, the batch planning and the batch merges of all 399 batches and of P1 ran this code** (executable sha256 33bab738..., GCC 13.3, Boost 1.86, AMD EPYC 7742) |
| 3129a97 | 2026-09-26 09:16 | inspection fix rounds 2–5 (verify rebuilds coverage, design-input validation, per-element replay accuracy); final combine of v1 |
| 0227dc5 | 2026-09-26 11:39 | v1 result: 46 batches, retained primitive, −322554 ± 160 |
| b0d2cd3 | 2026-09-26 16:35 | direct primitive sector (PLAN2) |
| 7320afc | 2026-09-26 16:57 | `combine.py --jobs`; **code of the final combination** (2026-09-28) |
| f923ad8 | 2026-09-28 08:01 | final result: 399 batches plus the direct primitive, −322550 ± 41 |
| e480fdc, acc3ec6, 14e6655, 68dc6be | 2026-09-28 to 2026-10-01 | REPORT corrections, the C6(1) addendum and the results-review revision (RR-003) |

**Shipped:** commit 68dc6be. Its code files are byte-identical to 7320afc (7320afc..68dc6be changes only `results/` and
`SHA256SUMS`). Against 3213ce0 the shipped code differs in `tools/campaign.py` (plan_counts and check_coverage
refactors, coverage rebuild and merged-header checks in `verify_campaign`), `tools/assemble.py` (primitive-sector guard,
input binding), `tools/combine.py` (`--primitive`, `--jobs`), `tools/design.py` (pilot validation) and tests;
`src/`, `cluster/`, `Makefile`, `tools/production.py`, `inputs_extra/` and `reference/` are identical. The worker path
(`campaign.py run` and the C++ integrator) is therefore unchanged, and the merge code differs only by a refactor that
keeps its output. `public/diff_3213ce0_to_shipped.patch` reverses to the 3213ce0 tools and tests exactly (checked).

##### Production facts (from `results/C7_1/production_run.json`, REPORT.md and the review log)

- Machine: SDSC Expanse, `shared` partition, Slurm 23.02.7; 16 CPUs and 16 GB per array element, 3 h limit.
- Design: `design_v1.json` (sha256 fd356a15...), frozen on 2026-09-25 from a multiplier-1 pilot (seed 2026092501) and the
  archived components by `tools/design.py` (estimator-only Neyman allocation; predicted SE 203 per batch).
- Seeds: batch k uses the first 8 bytes (little endian) of sha256("C7-expanse-2026-09:batch:k"); each campaign seed is
  derived from it by `production.py`; P1 uses sha256("C7-expanse-2026-09:primitive"), matrix seed XOR 0x17219317.
- Batches: 46 in the first wave (2026-09-25 20:59 to 2026-09-26 06:58 PDT, 29,725 core-hours), then extension batches
  under a pre-registered stop (2026-09-29 06:00 PDT, 400 batches, or 300,000 SU); the 400-batch cap was reached on
  2026-09-28 01:15 PDT. b215 was never submitted (its planning read a truncated Lustre copy of an input and failed
  closed), so 399 batches are included. 17 transient `srun` step failures were resubmitted once each.
- Cost: about 250,000 core-hours for the batches (55 elements × 16 CPUs per batch, about 640 core-hours each), about 20
  for P1, about 60 for the combinations; project accounting gives 255,952 SU on Expanse plus 12.5 core-hours of tests
  on a personal desktop.
- Final combination: 2026-09-28 02:56–04:45 PDT, `combine.py --jobs 16`, every campaign re-verified with its
  checkpoints.

##### Changes made for the public export

None to shipped files. New: `public.mk`, `public/` (replay, data and Slurm helpers). Not shipped: `benchmarks/`,
`results/` (moved to `GFF/results/C7_1/`), git history.

### `LRI_C7_D2_HPC`

Folder: `code/LRI_C7_D2_HPC/`.

#### Provenance: C7(2) (GFF/code/LRI_C7_D2_HPC, GFF/data/C7_2, GFF/results/C7_2)

| Part | Written by | When | Source |
|---|---|---|---|
| `reference/`: the earlier two-dimensional seventh-order calculation (power-free campaign `LRI_C7_d2_progress`, power-sector completion `power_mass`, method note `notes/C7_d2_complete.tex`, merged into note Section 28 and not shipped, result -3950 +- 310) | OpenAI GPT-6 astra (model stated by the author, 2026-10-13), in a ChatGPT session | before 2026-09-30 | restored byte for byte from that model's archive by the delivery (`delivery/DELIVERY.md`; 4,329 files, `reference/SHA256SUMS`) |
| The optimized package (`src/`, `tools/`, `tests/`, `slurm/`, `inputs/`, `docs/`, `benchmarks/`, `delivery/`) | the same model, OpenAI GPT-6 astra (model stated by the author, 2026-10-13) (its delivery records name a sandbox with `/mnt/data` paths and Linux 6.18.44 / glibc 2.41) | delivered 2026-09-30 | git commit `fb64c47096309c490392e1021eaa3e986fa7bd48`, "Baseline: LRI_C7_D2_HPC as delivered 2026-09-30" (`verify_delivery --strict`: 4,405 payload files), made by Claude Code session C62d without changes |
| Production: build, tests, plan, execution, merge, assembly; the wrappers now in `public/slurm/` | Claude Code session C62d, with the package's own tools | 2026-09-30 (results review 2026-10-01) | `GFF/data/C7_2/`, `GFF/results/C7_2/` (copied from the production cluster) |
| `public.mk`, `public/regen_packs.py`, `public/replay_c7d2.py`, `public/slurm/*` headers and placeholders, `REVIEWS.md`, the results `README.md` and `CAMPAIGN.md` | Claude Code (a build agent of session C62d) | 2026-10-13 | `<PAPER>/notes/public_repo/GFF/d2/C7_2/` |

What changed after the production commit, and why it is not shipped: 27 commits (`fb64c47..a55958f`, 2026-10-02) of a
reviewed fix loop (Claude Code builder and coordinator, OpenAI Codex as plan reviewer and code inspector; code `3cef517`,
Codex APPROVED at `a55958f`). They port a job-handling layer (status, recovery, guarded Slurm submission with a campaign
lock, resumable merge), add opt-in allocation flags, lower-order pulls in the result, build records and new
tests, regenerate the checksum lists, and add cluster validation evidence (`benchmarks/symmetry_2026-10/`). The only change to `src/` is
one line in `kernel.hpp` (an explicit type conversion so the kernel compiles with Boost 1.66); `reference/` is unchanged.
With Boost 1.77 the binaries built from `fb64c47` and from `3cef517` are byte-identical to the production binaries. The
revised tools refuse campaigns planned by `fb64c47` (schema `c7-d2-production-1`) and use a different default seed
scheme, the production plan pins the hashes of the `fb64c47` tools, and the note cites `fb64c47`; so the release ships
`fb64c47` verbatim and records the revision here and in `REVIEWS.md`.

Records: the plan, cost model, group configurations and merged records are byte-identical copies from the production run
directory; `C7_result.json` is the file written by `tools/assemble.py` in Slurm job 566530; the evidence under
`results/C7_2/evidence/buildtest-566254/` is byte-identical to the job's output, and `buildtest-566254.out` is that job's
summary with the host name replaced by `<NODE>`.

Git authorship of all commits is the project's local identity; it is not exported (`git archive`).

### `LRI_C7_D3_HPC`

Folder: `code/LRI_C7_D3_HPC/`.

#### PROVENANCE fragment: C7(3) (`code/LRI_C7_D3_HPC`, `results/C7_3`, `data/C7_3`)

For `GFF/PROVENANCE.md`. The work was directed by the author (Z. Zheng). All content is AI-generated or published
research; the reviewers were AI systems (`results/C7_3/REVIEWS.md`). Dates are 2026.

##### Code

| part | origin | written by | changed afterwards |
|---|---|---|---|
| `reference/` | The previous full numerical C7(3) calculation (C7(3) = −227.6181094747, SE 3.827; reported −228 ± 16), delivered 2026-09-30 as `LRI_C7_d3_full_numerical.zip` (50,894,194 bytes, sha256 84b2cb1f…). Preserved byte for byte inside the HPC package (`benchmarks/reference_preservation.json`: 4,349 files). Its records name `/mnt/data/LRI_C7_D3_calculation` as working directory. | OpenAI GPT-6 astra (stated by the author, 2026-10-13) | unchanged |
| everything else in `code/LRI_C7_D3_HPC/` | The HPC package `LRI_C7_D3_HPC_optimized.zip` (81,849,684 bytes, sha256 0d79b6a9…), delivered 2026-09-30: the C7(2) HPC package with a d=3 port (restartable Slurm campaigns, indexed kernel packs, merging, assembly), with the original d=3 worker unchanged. Local git baseline **4de9412** (`verify_delivery --strict`: 4,909 files). | OpenAI GPT-6 astra (stated by the author, 2026-10-13) | Unchanged. This is the code that ran: the run1 manifest pins its tools by sha256. Not published: `benchmarks/` timings, memory and profile runs, and `experiments/` (a quotient-reuse kernel that was not adopted). |
| `reverify_a6ce987/` | Five files of commit **a6ce987** (2026-10-01): the read-only re-verifier `tools/report.py` with its `assemble.py` and `common.py`, the gate references, and run1's cost model. From the Codex fix loop (plan approved in round 3, code approved in round 5 at c71cc56, code bb9d2ca); a6ce987 adds the results review's archived-gate fix. | Claude (Claude Code, Opus 5.5), inspected by Codex | byte-identical to a6ce987 |
| `public.mk`, `public/` | Public targets and scripts, 2026-10-13: `replay_C7_3.py`, `setup_kernels.py`, `check_tree.py`, `compare_report.py`, `compare_archived_replay.py`, `compare_smoke.py`. `replay_archived.py` is the code review's script (2026-09-30), unchanged; `indep_rows.py` is the review's script with the reference path made relative. `public/kernels/inputs_packs.tar.gz` is `git archive 4de9412 -- inputs/packs`, gzip-compressed. | Claude (session C63d) | new; not reviewed by Codex |

##### Records (`results/C7_3/`)

| file | origin |
|---|---|
| `run1-20260930-m4096/` | Production run1 on the symmetry cluster (Perimeter Institute), 2026-09-30 17:57 to 2026-10-01 04:03 EDT: 28 whole nodes, 1,280 job indices, 8.68 × 10¹¹ kernel samples; merge and assembly by the production tools (job 566671, after the merge job 566409 failed on a defect of the external merge script, not of the package). Local copy of `C7_result.json`, the manifest, the 20 group configs and merged records, the node and merge logs; byte-identical to the run directory. |
| `run1-20260930-m4096_full.tgz.sha256` | Checksum of the complete run directory (hosted as `data/C7_3/run1-20260930-m4096_full.tgz`), written 2026-10-01. |
| `CAMPAIGN.md` | The production log, written by the Claude session that ran the campaign (2026-09-30 to 10-01): the plan, the reporting rule written before the result, the user's confirmation after it, the gates, the erratum and the review outcomes. |
| `run1_report_bb9d2ca.json` | Re-verification of run1 by `tools/report.py` at bb9d2ca (symmetry job 567197, an AMD EPYC 7532 node, 2026-10-01): bitwise with `C7_result.json`, all gates. Four earlier re-reports of the fix loop, with the same values, are not published. |
| `evidence/` | From the code review (2026-09-30, symmetry): `buildtest-566376.out` (build, delivered tests, thread identity, pilot), `intelcheck-566410.out` (AMD vs Intel), `replay_report.json` (archived-stream replay, job 566411). |
| `REVIEWS.md`, `results_map.md` | Written for the public release, 2026-10-13 (Claude, session C63d). |

##### Environment of the production

Symmetry `defq` and `amdq` partitions: AMD EPYC 7532, 7543 and 8534P nodes and Intel Xeon Gold 6148 nodes; GCC 11.4,
Boost 1.77 headers (module), GMP 6.2.1; Python 3.11 with numpy 2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0. Binary
`bin/c7d3_gmp` sha256 635428f9f9f462b74d261185120b5ea1553fb7989196feef644dd85dd687ae5f (GMP350).

##### Hash bindings

- The run1 manifest (sha256 eefa8432…) pins the four production tools, `inputs/manifest.json` (5048b336…), the
  executable, the cost model (f815b1fa…, shipped in `reverify_a6ce987/cost_models/`) and the 20 group configs; each
  `merged.json` pins the manifest, its config, its `graph_replicates.csv` and its own payload; `C7_result.json` pins the
  manifest and the merged files. `inputs/manifest.json` pins every kernel pack; `inputs/inventory.json` pins every graph.
- `SHA256SUMS` and `DELIVERY_MANIFEST.json` (the delivery's lists of all 4,980 files) and `reference/DELIVERY_MANIFEST.json`
  ship verbatim; they still list the files restored by `setup`, hosted or not published. `make -f public.mk checksums`
  verifies every present file and classifies the absent ones. Since 2026-10-16 (author rule: one TeX note per
  direction) `reference/reference/C7_d2_complete.tex`, a copy of the earlier d = 2 method note (condensed note
  Section 28), is not published; `public/dropped_paths.txt` names it and the check accepts exactly that path as
  absent (class "merged").

## Full C8(1), C8(2), C8(3) and the independent checks

### `LRI_C8_HPC`

Folder: `code/LRI_C8_HPC/`.

#### Provenance: LRI_C8_HPC (C8(1), full eighth order in one dimension)

- **Authors.** AI-generated: written by a Claude Code session (Anthropic Claude, session "C71d") on 2026-10-02 as an
  order-eight generalization of the reviewed C7(1) package `LRI_C7_HPC`. The repository is a fork of it: its first
  commits are the C7 history, from baseline c21b9e8 on. The nine-vertex generators in `gen/` were written by a subagent
  of that session. Independent reviews are by OpenAI Codex (see REVIEWS.md). The research direction, budgets and the
  decisions recorded in the amendments are the author's.
- **Source.** Git repository `LRI_C8_HPC`, branch `c8`, exported at commit 1282e37 (2026-10-13).
  - **b1-b4 production code** (SDSC Expanse, 2-3 October 2026): commit c0ffa63, Codex APPROVED at inspection round 10.
    `src/`, `gen/` and every tool except `tools/combine8.py` and `tools/lane8.py` are unchanged from c0ffa63 to
    1282e37.
  - **Extension A1** (b5-b14 on symmetry, 10-12 October): `tools/combine8.py --extension` and `tools/lane8.py` at
    15a110e, APPROVED at round 12, unchanged afterwards.
  - **Amendments A2 and A3** (12-13 October): `cluster/symmetry/*`, `cluster/a3/*` and docs, through bd13a63.
  - **Results:** commits 9dd3a6b to 1282e37 add the K = 14 result and the report, with no code change.
- **Production.** The production ran copies of these commits:
  - Expanse: `code/c0ffa63`;
  - symmetry: `code/15a110e` and the A3 tools of bd13a63.
  The binary `bin/c8_integrate` was built from `src/` with GCC 13.3.0. Its sha256 is recorded in every campaign
  manifest (`executable_sha256`), and `tools/combine8.py` requires it to be identical across batches.
- **Dates.** Code 2026-10-02 to 2026-10-03. First result (K = 4) 2026-10-03: 8066723 +- 8015, allowance 33000. Extension
  A1 2026-10-10 to 12 (A1 interim, K = 9: 8061480 +- 5300). A2 and A3 2026-10-12 to 13. Final K = 14 on 2026-10-13:
  8059767, SE 4210, allowance 17000. The Codex results review was APPROVED at round 4 on 2026-10-13.
- **Compute.** About 9x10^4 physical core-hours in all (1.4x10^5 as charged, counting hyperthreads on symmetry). The
  extension A1-A3 used 64.6x10^3 physical core-hours: 46.8x10^3 on symmetry and 17.8x10^3 on Expanse.
- **Changed for the public copy.**
  - Inherited C7 files (benchmarks/, inputs_extra/, CHANGELOG.md, docs/c7_historical/ and a stale SHA256SUMS) and the
    second copy of `reference/` are not shipped. `make -f public.mk setup` links `reference` to `../LRI_C7_HPC/reference`, which is
    byte-identical (no symlink is committed).
  - `inputs8/L8_coord.txt` ships xz-compressed in `GFF/data/C8_1/inputs8/`.
  - New files only: `public.mk`, `public/` (replay, verify, portable test, env template, README) and `REVIEWS.md`.
  - No shipped file was edited.
- **Records.** `GFF/data/C8_1` holds byte-identical copies of the merged production records, fetched read-only on
  2026-10-13 from symmetry (`<SCRATCH>/c8_hpc/`) and Expanse (`runs/tailtest_L7`; `runs/pilot8/tprodA_L7`,
  `tprodB_L7` and the pilot batch JSON on 2026-10-16). User names, cluster paths
  and node names in records and production scripts are kept, because they are bound by hashes or ran as written.

### `LRI_C8_D2_HPC`

Folder: `code/LRI_C8_D2_HPC/`.

#### Provenance: C8(2) (LRI_C8_D2_HPC, LRI_C8_shared, data and results C8_2)

| Item | Written by | Dates | Source | After the production |
|---|---|---|---|---|
| Seventh-order base of LRI_C8_D2_HPC (root commit fb64c47 "LRI_C7_D2_HPC as delivered 2026-09-30") | OpenAI GPT-6 astra (model stated by the author, 2026-10-13), in a ChatGPT session, as delivered to the author; hardened by Claude Code (C7(2) fix loop, Codex APPROVED round 3 at a55958f) | to 2026-10-02 | `../LRI_C7_D2_HPC` | — |
| `reference/LRI_C7_d2_progress/`, `reference/power_mass/` and the other C7(2) reference files (shipped once in `GFF/code/LRI_C7_D2_HPC/reference`) | the original seventh-order research packages by OpenAI GPT-6 astra (model stated by the author, 2026-10-13), as received | before 2026-09-30 | byte copies, unchanged | — |
| Eighth-order code of LRI_C8_D2_HPC: kernel generalization (`src/`), numerics profiles, payload generator (`gen/`), inputs tools, orchestration, design, statistics, tests, docs | Claude Code session C62d and its subagent workflows; plan and code reviewed by OpenAI Codex (gpt-6-astra, xhigh) | 2026-10-03 to 2026-10-06 (code frozen at ba68f40 on 2026-10-06) | branch c8, commits after tag c8-base | evidence commits through 9df5b1c (2026-10-08); then aafa8a4 (`tools/design.py report` for production batches) and two seed-mirror updates, not shipped |
| `vendor/c8_assembly/` = `LRI_C8_shared/assembly/` (order-8 assembly) | Claude Code session C63d | 2026-10-03 (HANDOFF f5ff6a35) | byte copy | — |
| `LRI_C8_shared/inventory/inventory8_d2/` | `gen/` of LRI_C8_D2_HPC at 36043bb, run on Expanse (job 54631552, AMD EPYC 7742, GCC 13.3.0), published by C62d | 2026-10-03 | pin 46341a3c… | never changed |
| `LRI_C8_shared/assembly/H1_gates/` | Claude Code session C63d | 2026-10-04 | — | — |
| Production and pilot (symmetry cluster, AMD EPYC 7543) | run by C62d's workflows; the user chose the target (relative SE 2.5e-4), the numerics profile (dd+mp256) and the node count | pilot 2026-10-06; production 2026-10-06 16:33 to 2026-10-07 21:12 EDT | export of ba68f40 | — |
| Tail check (`benchmarks/symmetry_2026-10-c8/production/tailcheck/`) | C62d's analysis workflow, revised after two Codex consultations | 2026-10-07/08 | committed d5c7bee, 9df5b1c | — |
| `GFF/data/C8_2/` | copied read-only from the symmetry campaign directory by C62d | 2026-10-13 | the campaign directory `prod1-2.5e-4-ddmp256-20261006-ba68f401e46e/` on the symmetry cluster | — |
| `GFF/results/C8_2/` | byte copies of 9df5b1c files (`SOURCES.txt`) | 2026-10-13 | — | — |
| Public release files (`public.mk`, `public/`, `REVIEWS.md`, the C8_2 documents) | Claude Code (C62d's build agent) | 2026-10-13 | — | — |

All commits of LRI_C8_D2_HPC carry the author's git identity; the authorship above comes from the plan log, the session
memory and the delivery records. The independent eighth-order code (unit C8_2_check, `LRI_C8_D2_HPC_optimized`) is a
different provenance and is described there.

### `LRI_C8_shared`

Folder: `code/LRI_C8_shared/`.

_same as the section above (one text for the whole unit)._

### `LRI_C8_D2_HPC_optimized`

Folder: `code/LRI_C8_D2_HPC_optimized/`.

#### Provenance: independent check of C8(2)

| Part | Written by | Source | Dates | Changed afterwards |
|---|---|---|---|---|
| The code (kernel, inputs, graph generation, assembly, allocation, tools, tests, docs) | OpenAI GPT-6 astra (model stated by the author, 2026-10-13), delivered as `LRI_C8_D2_HPC_optimized.zip` (optimized release) and `LRI_C8_D2_HPC.zip` (original package with the graph packs) | imported unmodified as git commit df468f8 | delivered 2026-10-08 | no numerical file changed (src/, Makefile and the seven tools a plan pins are byte-identical to df468f8: gate AC1, on symmetry and Expanse) |
| Cluster layer for Expanse and symmetry: whole-node runner, admission, seed synchronisation, gate job, env files, site tests, `docs/SITES.md` | Claude Code (Claude Opus), session C62d | commits 300a1ca..a791a1f on top of df468f8; a2a9a46 adds the final Expanse gate record | 2026-10-08/09 | reviewed by OpenAI Codex (gpt-6-astra); see REVIEWS.md |
| Pilot and production runs, analysis | Claude Code session C62d, on Expanse (SDSC) | pilot 2026-10-09 (3 nodes, 172 core-hours); production 2026-10-09/10 (11 AMD EPYC 7742 nodes, 207 node-hours) | | — |
| Public overlay (`public.mk`, `public/replay.py`, `public/remerge.sh`, `public/kernel_time.py`, `REVIEWS.md`) | Claude Code session C62d | new files | 2026-10-13 | verified on Expanse and macOS (REPRODUCE.md) |

The shipped tree is git commit a2a9a460e81250e8d9ed366a06ce17ddd21e62e8: a791a1f (the commit that ran the pilot and the
production) plus its final gate record. Not shipped from the delivery: `RESULTS.md` (the delivering model's own earlier
campaigns) and optimization diagnostics under `optimization_work/` that no check reads.

### `LRI_C8_D3_HPC`

Folder: `code/LRI_C8_D3_HPC/`.

#### Provenance: C8(3) (code/LRI_C8_D3_HPC, results/C8_3, data/C8_3)

The work was directed by the author (Z. Zheng). The package, its plan, the pilot, the production and the analyses were
written and run by a Claude Code session (Anthropic; session C63d) between 2026-10-03 and 2026-10-12. The plan, the code
and the results were reviewed by OpenAI Codex (gpt-6-astra, effort xhigh); see `public/REVIEWS.md`. There was no human
referee. All computations ran through Slurm: development on Expanse (SDSC, AMD EPYC 7742) and symmetry (Perimeter, AMD
EPYC 7543), the pilot and the production on symmetry's AMD EPYC 7543 nodes.

##### Code: `code/LRI_C8_D3_HPC/`

| part | origin | written by | changed afterwards |
|---|---|---|---|
| the package at git commit **4fbd1bae5a88** (branch c8, 2026-10-08) | generalized from the C7(3) package `LRI_C7_D3_HPC@a6ce987` (code/LRI_C7_D3_HPC, C7_3 group) in Stages 0–6, 2026-10-03 to 10-07; production support added 2026-10-08 | Claude (C63d) | **Unchanged.** It is the export the production ran (D_P 4fbd1bae5a88; `C8_result.json` pins its tools by sha256, and the replay checks them). Later commits on the branch add only evidence, except e8468c96 (a top-up combiner, `tools/combine_results.py`, never used), which is not exported. |
| `src/` | the C7(3) worker generalized to 16 propagators, 31-dimensional nets and two orders | Claude (C63d) | final at K6 a914db2 (2026-10-07); production binary e9b6f6c3… |
| `vendor/c8_assembly/` | byte copies of the shared order-8 assembly `LRI_C8_shared/assembly/` (HANDOFF sha256 f5ff6a35…), pinned by `tools/VENDORED.json` | Claude sessions C62d and C63d; reviewed in C62d's H2 review | unchanged |
| `gen3/` | the d=3 rate conversion of the shared nine-vertex inventory H1 (Stage 1) | Claude (C63d) | unchanged |
| `inputs/` | built by `tools/prepare_inputs.py` (Stages 2a/2b) from the vendored low-loop files, the C7(3) members in `reference/inputs/`, H1's `selection.json` and the d=3 payload made by `gen3/run_d3.sh` on Expanse (J-GEN-D3) | Claude (C63d) | unchanged; the L7 packs are hosted (data/C8_3) |
| `reference/` | the original C7(3) numerical package (C7(3) = −227.6 ± 16), byte for byte, plus C8(3) baselines and fixtures (`baseline_c8_stage3*.json`, `c7d3_run1_results/`, `c8d1_inputs8/`, `c8d3_recon/`) | the original package: a separate delivery to the project (see the C7_3 group's provenance); the additions: Claude (C63d) | unchanged; its L7 member files and archived production records are hosted, its verification outputs are not exported |
| `benchmarks/` (kept part) | evidence the tests, the replay or a cited check read (list in export_entries.json) | written by the package's jobs | unchanged |
| `benchmarks/symmetry_2026-10-c8/production/{README.md, prod1/, margin_probe1/, margin_probe2/, margin_ladder/}` | production evidence, from git commit **6dd4a75a4fd4** (2026-10-12): result report, campaign split, tail N-trend, budget/status/verify outputs, job list, the frozen design, the rate probes | Claude (C63d); the analyses revised after the results review | unchanged; checked by `public/SHA256SUMS.evidence_6dd4a75a` |
| `public.mk`, `public/` | **new for the public release (2026-10-13)**: the public targets, the replay, the data fetcher, the pruned evidence checksum list, README and REVIEWS | Claude (C63d drafting agent) | new files only; no shipped file is changed |

##### Records: `results/C8_3/`

The production campaign `prod1-20261008` ran on symmetry from 2026-10-09 01:26 to 2026-10-12 04:28 (plan job 571488,
65 lane jobs, 36 merges). `results/C8_3/` is the local copy of the campaign's top-level files and per-group `merged.json`
and `config.json`, byte-identical to symmetry (`SHA256SUMS.symmetry`, written on symmetry after the run; all lines
verified 2026-10-13). The full run tree (13 GB) is on symmetry and in the authors' archive.

The records are hash-bound and ship byte-identical: `C8_result.json` binds `manifest.json` and every `merged.json`;
`manifest.json` binds every `config.json`, the cost model, the inputs manifest and the design bundle. They name cluster
paths (cluster scratch directories), node names and the job-submission host. No code resolves those paths.

##### Hosted data: `data/C8_3/`

The L7 and L8 kernel packs (built 2026-10-05 by `make inputs` and `make inputs-l8`), the C7(3) reference L7 member files
and archived production records (from the original C7(3) package), and the per-graph replicate tables of the production
(2026-10-12). Sizes and sha256 in `data/C8_3/HOSTED.json`.

##### Checksum lists

- `SHA256SUMS` and `DELIVERY_MANIFEST.json` (package, 4fbd1bae): shipped verbatim, verified by `public/replay_c8_3.py`
  row P1: every shipped file matches, and a listed file may be absent only under the export entry's excludes (not
  exported or hosted; counted) or if `public/dropped_paths.txt` names it. That list holds one file since 2026-10-16
  (author rule: one TeX note per direction): `reference/reference/C7_d2_complete.tex`, a copy of the earlier d = 2
  method note (condensed note Section 28), reported in one INFO row.
  `tools/verify_delivery.py --strict` fails on the public tree by design (it requires every listed file).
- `public/SHA256SUMS.evidence_6dd4a75a`: **pruned** from 6dd4a75a's `SHA256SUMS` to the 118 evidence files shipped.
- `results/C8_3/SHA256SUMS.symmetry`: shipped verbatim; its 24 `graph_replicates.csv` lines refer to hosted files.
- `reference/DELIVERY_MANIFEST.json` (the original C7(3) package): shipped verbatim; used to verify the hosted tar members.

### `LRI_C8_D3_OPT`

Folder: `code/LRI_C8_D3_OPT/`.

#### Provenance: LRI_C8_D3_OPT (independent check of C8(3))

##### Who wrote what

| part | author | date | source |
|---|---|---|---|
| The package: native worker, graph generation and audits, analytic low-loop inputs, planner, assembly, fixed point, allocation, tests, docs, the delivered pilot | OpenAI GPT-6 astra (stated by the author, 2026-10-13; the files do not name it), given the project's seventh-order package `LRI_C7_D3_HPC` and a version of the condensed note | delivered 2026-10-09 | `LRI_C8_D3_HPC_optimized.zip`, 451,327,106 bytes, sha256 `9de3c1d85c2c5e4103cd3de84ef7f2a07a49fcfbefc9168c451e176cf0e73000` |
| Inside that zip: the base package plus a performance patch, merged by the same author | same | 2026-10-08/09 | `OPTIMIZED_PACKAGE.json`: base `LRI_C8_D3_HPC.zip` sha256 `4cf21876...`, patch `LRI_C8_D3_optimized_patch.zip` sha256 `aafee16b...`; the patch changes `Makefile`, `src/kernel.hpp` and `src/c8d3_integrate.cpp`; `baseline/` keeps the unpatched worker for the regression test |
| Cluster layer for Expanse and symmetry: `tools/submit.py`, `tools/hpc_dispatch.py` (locks, deadlines, signals, staging), `slurm/*.sh`, `slurm/sites/*`, `docs/CLUSTERS.md`, `tests/test_cluster.py`, `tests/fake_native.py`; one receipt re-check in `tools/campaign.py run_job` | Claude Code session C63d (Claude), reviewed by Codex (`REVIEWS.md`) | 2026-10-09 to 2026-10-12 | git commits after `dafa312` |
| Production `prod1` on Expanse and its records | C63d, on the user's decisions (budget about 9,000 SU on 2026-10-10; finishing the 5-job tail on 2026-10-11) | 2026-10-10/11 | `GFF/results/C8_3_check` |
| `public.mk` and `public/` (replay, docs, Slurm templates, data-bundle tool) | the drafting agent of the public release (Claude) | 2026-10-13 | new files, not part of the package |

##### Git history of the package (repository `main`)

- `dafa312` (2026-10-09): the zip as received, unchanged. `inputs/free/`, `inputs/power/` and `results/` are untracked
  (git-ignored) and covered by the package's own `SHA256SUMS` / `DELIVERY_MANIFEST.json`.
- `a807244` ... `6fb5b5f`: the cluster layer and the fix rounds of Codex inspections r1-r4.
- **`d5deeb9` (2026-10-10 15:18 EDT): the production commit.** One admission change after r4 (the user's running-job
  cap counted differently), uninspected. Exported here.
- `3961865`, `6edcc9e` (2026-10-12): fix rounds 5 and 6 (admission rules only). They change `tools/submit.py`,
  `tests/test_cluster.py`, `docs/CLUSTERS.md`, `DELIVERY_MANIFEST.json` and `SHA256SUMS`; no file that the
  production pins or that the science reads. Not exported.

Science files unchanged since `dafa312`: `src/`, `baseline/`, `inputs/` (tracked and untracked), `regeneration/`,
`tools/assemble.py`, `assemble_streaming.py`, `rg.py`, `io_utils.py`, `sobol_net.py`, `allocate.py`,
`generate_graphs.py`, `prepare_low.py`, the package `Makefile`. `tools/campaign.py` changed once (commit `6e3f139`,
Codex finding R2-08: `run_job` re-checks the receipt after taking its lock and never replaces a receipted output); the
production manifest pins the changed file (sha256 `13a12b7c...`). `tools/hpc_dispatch.py` is pinned by the production's
dispatch index (sha256 `f36741f7...`, identical from `6fb5b5f` to `6edcc9e`).

##### Production

- Worker: `bin/c8d3_optimized`, sha256 `e6f424c5...`, built from `d5deeb9`'s sources (unchanged since `dafa312`) with
  GCC 13.3.0, Boost 1.77 headers and GMP 6.2.1 on an AMD EPYC 7742 node; three Expanse builds (jobs 54781591,
  54783728 and 54786481 on 2026-10-09, before and after the r2-r4 fixes) produced the same binary hash. Backend `gmp350`.
- Allocation `prod1_2000.json` (sha256 `fccf8969...`): `tools/allocate.py` on the delivered pilot's graph statistics,
  2,000 core-hours of the pilot's host, 16 replicates, minimum 4,096 points (the replay reproduces it byte for byte).
- Plan job 54822480 (manifest created 2026-10-10T21:00:28Z): base seed 1546835505427890396, 1,994 jobs,
  37,121,687,552 evaluations, complete coverage verified.
- Lanes job 54823471: 6 nodes x 16 lanes x 8 threads, 2026-10-10 21:59Z to 2026-10-11 10:42Z (12:43:34); 1,989 jobs.
  Lane 67 deferred two bundles (jobs 417 and 1057-1060) at its deadline, a clean stop (srun exit 3).
- Index-only job 54838167 (a hand-written sbatch; the site layer had no role for re-indexing an existing run): a
  16-lane index over the same run with the same bundling. Lanes job 54838170 (1 node, 11:31) ran the 5 jobs.
- Assembly job 54838171 (`assemble_streaming.py --bootstrap 4096`, 46 s): `C8_result_54838171.json`
  (sha256 `58de4f97...`) and `graph_statistics_54838171.json`.
- Records copied from the Expanse campaign directory to the project on 2026-10-11 (`GFF/results/C8_3_check`, byte
  identical). The native outputs and receipts of the 1,994 jobs stay on the production cluster's scratch filesystem;
  they are not archived.

##### What the export changes

- Code: `git archive d5deeb9`, minus `DELIVERY_MANIFEST.json`, `reference_study/`, `regeneration/` and
  `inputs/complete_inventory_L*.json` (the last two are hosted), and, since 2026-10-16 (author rule: one TeX note per
  direction), minus `derivation.tex`, `docs/DERIVATION.tex` and `docs/C8_3D_calculation.{tex,pdf}`, whose substance
  is in the condensed note, Section 32.7. No shipped file is modified.
- Plus 179 untracked graph payloads from the working tree (the test fixtures), byte-identical to the zip (checked
  against `SHA256SUMS`).
- `SHA256SUMS` ships unchanged. `make -f public.mk verify-data` (`public/verify_data.py`) checks every shipped file
  against it; a listed file may be absent only if it is hosted (until `fetch-data`) or named in
  `public/dropped_paths.txt` (the four notes above and `reference_study/long_range_ising_condensed.tex`).
- The package's `.gitignore` ships unchanged; it ignores `inputs/free/`, `inputs/power/`, `results/` and `bin/`, so the
  179 fixtures must be added to the public repository with `git add -f` (tracked files stay tracked; the hosted
  payloads unpacked by `fetch-data` stay ignored).
