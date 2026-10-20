# Provenance of the HT packages

For each package: where it comes from, who wrote it (the author, Claude Code sessions, OpenAI GPT-6 astra), the commit it was exported at, and what changed afterwards.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT/`. The values themselves are in `note/README.md` and the note.

- d = 1: dressed phi^4 Hamiltonian truncation: `lri_dressed_phi4_hpc`, `lri_dressed_phi4_hpc_analysis`, `lri_dressed_phi4_independent_check`
- d = 2: dressed-window Hamiltonian truncation: `lri_2d_window_hpc`, `lri_2d_window_indep`
- d = 3: dressed-window Hamiltonian truncation: `lri_3d_window_hpc`, `lri_3d_window_indep`

## d = 1: dressed phi^4 Hamiltonian truncation

### `lri_dressed_phi4_hpc`

Folder: `code/lri_dressed_phi4_hpc/`.

#### Provenance: d = 1 finite-coupling HT (lri_dressed_phi4_hpc, its analysis, its records)

##### Code: HT/code/lri_dressed_phi4_hpc (git, shipped at 33998bba7a622a82100fb7263e2848cf7ac5bd6f)

| Commit | Date | Author | Content |
|---|---|---|---|
| e637dfd | 2026-10-02 | OpenAI GPT-6 astra (via ChatGPT), supplied by the author as `lri_dressed_phi4_hpc_optimized.zip` (sha256 423cb8f8…) | Matrix-free, parity-packed rewrite of the dressed zero-mode solver of `lri_extended_comparison_study.zip` (sha256 04bb8d30…, recorded in `provenance.json`); that solver is kept in `reference/`. Written by OpenAI GPT-6 astra (model stated by the author, 2026-10-14). |
| 157a2c6, 4dfd833 | 2026-10-02/03 | Claude Code (claude-opus-5-5) under a claudex loop | Symmetry readiness (frozen installs, staged validation receipts, the node-packing launcher, cross-node generation leases), the opt-in full-vacuum window correction (`window.py`, `--window vacuum`), the descendant-identity diagnostic. The plan was reviewed by Codex (gpt-6-astra, effort xhigh) and approved in round 4. The code was then inspected twice (REVIEWS.md). **The prod1–7 records were written by 4dfd833.** |
| 8e15875, e2ca07c | 2026-10-03 | Claude Code | Fixes for the 12 + 8 Codex inspection findings: done-marker identity, lease scope, Slurm requeue incarnation, baseline pinning and others. They change no computed number (pinned baseline equality 0.0). The fixes of e2ca07c were not re-inspected. |
| 33998bb | 2026-10-07 | OpenAI GPT-6 astra (via ChatGPT), supplied by the author as `lri_dressed_phi4_hpc_basis_integration.zip` (sha256 038c630d…); committed unmodified by Claude Code | The opt-in saved state-averaged ("density") local basis: `density.py`, `local_basis.py`, `basis_training.py`, `train-basis`, integration into campaigns and validation. Written by OpenAI GPT-6 astra (model stated by the author, 2026-10-14). A fresh Codex inspection gave REVISE with two medium findings outside the production path (REVIEWS.md). **The dens_v1 production ran this code**: symmetry install `basisint-038c630d` (the full zip; same release fingerprint 1c27376c… as the commit), validation receipt 570965. |

**Binding.** The source fingerprint of the shipped `src/lri_dressed/*.py` is 9bfef37d…. This is the `source_sha256`
of all 201 dens_v1 results, the 13 basis artifacts, the 5 manifests and receipt 570965. The release fingerprint of
the shipped tree is 1c27376c…, the `release_sha256` of the manifests and of the receipt. `make -f public.mk replay`
checks both.

**Legacy path.** The prod1–7 records carry the fingerprint 92546a9d… of 4dfd833, which is not shipped as code. With
`--window none`, and with `--window vacuum` without `--local-basis`, 33998bb is bit-identical to the baselines:

- e637dfd and e2ca07c, frozen in `reference/production_*`;
- validation stages `baseline` and `window_baseline`, both of which give 0.0.

e2ca07c differs from 4dfd833 only in the launcher, lease and receipt code and in the scripts; the numerics are the
same.

##### Analysis: HT/code/lri_dressed_phi4_hpc_analysis

- **Origin:** the scripts and inputs come verbatim from the analysis folder of the production loop
  (`lri_dressed_phi4_hpc_loop/analysis/`, not a git repo).
- **Authors:** Claude Code (the session that ran the campaign), 2026-10-03..09:
  - extrapolate.py: 2026-10-04;
  - dens_v1.py: 2026-10-08;
  - dens_v1_holdout.py: 2026-10-09.
- **Records:** the identity records were written on 2026-10-03 by `python -m lri_dressed identities` (code 4dfd833)
  on prod records.
- **Overlay:** `public/` was added on 2026-10-13 by Claude Code (phi4HT1d) for the public release.
- **Other inputs:** `nrg/ds13_final.json` is a copy of the NRG folder's final table (bosonic NRG campaign, a
  separate package).

##### Independent check: HT/code/lri_dressed_phi4_independent_check

- Written on 2026-10-08 by a Claude Code subagent from the definition of the model.
- It was forbidden to read the production code, results and analysis; it read only two definition sections of the
  spec, and its brief is summarized in REPORT.md.
- It ran on symmetry (jobs 571688 and 571710).
- The comparison with production was made afterwards by the host session, against
  `indepcheck/production_reference.json`, which had been extracted before the subagent reported.
- `public/` was added on 2026-10-13.

##### Records: HT/data/HT_1d

| Set | Written by | Where | When |
|---|---|---|---|
| dens_v1 (201 results, 5 manifests) | 33998bb (`basisint-038c630d`) | symmetry, amdq and preq | 2026-10-07 to 10-09 |
| density bases (13 artifacts) | 33998bb `train-basis` | symmetry | 2026-10-07 |
| prod1–7 (680 results) | 4dfd833 | symmetry, amdq | 2026-10-02 to 10-05 |
| seeds/dens_v1_all | copies of prod1–7 window results, chosen as starting points | | 2026-10-07 |
| validation 570965 | 33998bb install | symmetry | 2026-10-07 |

- **Fetch:** all of these were fetched from the cluster project space on 2026-10-13 with rsync (unchanged bytes).
- **Requeues:** NODE_FAIL requeues on 2026-10-03/04 and 2026-10-08 resumed from Newton checkpoints. No completed
  result was rewritten.

Later changes: none to code or records. The paper's quoted values were corrected on 2026-10-13 (REVIEWS.md,
"Public-release replay").

### `lri_dressed_phi4_hpc_analysis`

Folder: `code/lri_dressed_phi4_hpc_analysis/`.

#### Provenance: lri_dressed_phi4_hpc_analysis
See ../lri_dressed_phi4_hpc/PROVENANCE_lri_dressed_phi4_hpc.md, section "Analysis" (shared provenance of the d = 1 finite-coupling packages).

### `lri_dressed_phi4_independent_check`

Folder: `code/lri_dressed_phi4_independent_check/`.

#### Provenance: lri_dressed_phi4_independent_check
See ../lri_dressed_phi4_hpc/PROVENANCE_lri_dressed_phi4_hpc.md, section "Independent check". Author: a Claude Code subagent (claude-opus-5-5), 2026-10-08, blind to the production code; comparison by the host session afterwards; public/ added 2026-10-13. No later change to code or results.

## d = 2: dressed-window Hamiltonian truncation

### `lri_2d_window_hpc`

Folder: `code/lri_2d_window_hpc/`.

#### Provenance: lri_2d_window_hpc (d = 2 finite-coupling HT production code)

| Item | Value |
|---|---|
| Public path | `HT/code/lri_2d_window_hpc/` |
| Exported commit | **889a968276529c859852302f158b3ab280797a49** (2026-10-07), the release that ran every prod1 record (release `ht2d_889a96827652`, source hash c16207e2…, checked by `make -f public.mk replay` against every record) |
| Later commit used | afe69ab143c80d8c1905afa03b797b6cd058a8f8 (2026-10-08): opt-in FD Newton Jacobian; ran the N = 24 valley scan. Shipped as `public/afe69ab.diff` (`git apply` on 889a968 gives the afe69ab tree exactly; checked) |
| Origin of the numerics | `lri_2d_window_hpc_optimized.zip` (sha256 71b9a64a…, version 0.2.0rc1, committed unchanged as 4afd379), an optimization of the 2D dressed-window research port (`reference/`, from `lri_2d_dressed_window_basis.zip`, sha256 93b95bf1…), itself built on the earlier circle implementation `upstream/d2dressed/` and the 1D dressed-HT templates. Both deliveries were written by OpenAI GPT-6 astra (model stated by the author, 2026-10-14): `lri_2d_window_hpc_optimized.zip`, and `lri_2d_dressed_window_basis.zip` (via ChatGPT), the source of `reference/` and `upstream/` |
| Expanse layer and fixes | 914141f → 62b0c45 → a0eb92f → 889a968, a Claude Code session (Claude Opus 5.5), 2026-10-07: chain driver, frozen spec/release/env binding, continuation, claim recovery; fix of HF-01 (fixed-point fallback); review fixes (REVIEWS.md) |
| Reviews | Codex (OpenAI GPT-6 astra): plan approved in round 6 of 7; final inspections 1–3 REVISE, all findings fixed; fix round 3 (889a968) not inspected. See REVIEWS.md |
| Production | Expanse (SDSC), account <ACCOUNT>, partition shared, 64 cores / 64 GB per chain; campaign prod1 submitted 2026-10-07, collected 2026-10-09 (348 records); frozen Python 3.11.5 env (numpy 2.3.5, scipy 1.17.0, numba 0.65.1) |
| Valley scan | Expanse shared, 12 jobs 2026-10-10 (64 cores, 64 GB, 3.2–4.9 h each, ≈ 3.0k SU), release afe69ab, `public/scan_valley.py` (written by the Claude Code session; verbatim), drivers `public/valley_expanse/` |
| Data placement | by the author's instruction, campaign data lived in the Expanse home directory (Lustre problems on 2026-10-07) |
| Public layer | `public.mk`, `public/{replay_d2.py, smoke_check.py, verify_manifest.py, afe69ab.diff}`, REVIEWS.md: new for the release (2026-10-13/14, Claude Code session phi4HT2d); not reviewed by Codex |

##### What ran where
- prod1: 13 chains Δσ ∈ {0.125, 0.126, 0.135, 0.15, 0.175, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.475, 0.495}, N = 8, 10, …, 24,
  main nz = 16 (diagnostics all), nested checks nz = 20 (diagnostics all) and nz = 12; three reference points
  (nz = 32, 256-state oscillator, N = 14) at Δσ = 0.126, 0.25, 0.4. Bases: the package's `reference/results/teacher_L6_x*.json`
  for the ten reference Δσ; new N = 6, nz = 24 teachers (campaigns teach1, teach2 on the same release) for 0.135, 0.175
  and 0.125 (0.125 started from the 0.126 teacher's couplings).
- N = 24 at Δσ = 0.125 and 0.126: the production Newton stalled (residual floor 2.9e-3 / 2.0e-3); restarts from an
  extrapolated seed and with the FD Jacobian (afe69ab) also stalled. These attempts produced no record; the valley scan
  then showed that there is no root (see results). Their campaigns are not shipped.
- `cluster/expanse/collect.py` wrote `results/HT_2d/prod1/{points,nested,descendants}.csv, flags.txt` on 2026-10-09
  from the 348 records. The 1678 flags are "ambiguous descendant identification" diagnostics only.

##### Later changes
None to the exported code. `largest_N.csv` (results) and `consistent_C0_C8.csv` (data) are new extracts written for the
release by `<PAPER>/notes/public_repo/HT/d2/tools/make_overlays.py`.

### `lri_2d_window_indep`

Folder: `code/lri_2d_window_indep/`.

#### Provenance: lri_2d_window_indep

| Item | Value |
|---|---|
| Public path | `HT/code/lri_2d_window_indep/` (a folder, not a git repository; files verbatim) |
| Written | 2026-10-08 (within one hour of the author's request for "a fully independent check of the solver") by the Claude Code session (Claude Opus 5.5) that had built the production package's Expanse layer: solver and tests from `docs/ORIGINAL_METHOD.md` only, without importing, copying or reading the production code at the time; not blind (the writer knew the production design) |
| Files and sha256 (as run) | `indep_ht2d.py` 84811655…, `test_indep.py` b77e91b8…, `run_check.py` 8b877b6f… (job 571811; job 571680 ran 9b882311…, diff in `public/`), `summarize.py` b83975ba…, `compare.py` 2086c8ab… (the job logs print the first three hashes) |
| Runs | symmetry (AMD EPYC, amdq): job 571680, 2026-10-08, 143 tasks, 56 workers, 1 h 06 min, all OK; job 571811 (defq, Intel, 12 workers), 2026-10-08/09, 12 tasks, all OK; Python 3.11.4, numpy 2.3.5, scipy 1.17.0 |
| Compared with | the production records of `lri_2d_window_hpc` (prod1), read from a copy taken while prod1 ran; every embedded `record_sha256` equals the final shipped record (checked by the replay) |
| Reviews | none by Codex (REVIEWS.md) |
| Public layer | `public.mk`, `public/{replay_indep.py, smoke_compare.py, run_check_9b882311_to_8b877b6f.diff, requirements.txt}`, REVIEWS.md: new, 2026-10-14 (phi4HT2d) |
| Not shipped | `prod_records/` (a working copy of the production records; the shipped records are in `HT/data/HT_2d/prod1`), `jac_trend*` (determinant trend of the tuning Jacobian; supporting evidence for the fold, not quoted), `logs_sym/` |

## d = 3: dressed-window Hamiltonian truncation

### `lri_3d_window_hpc`

Folder: `code/lri_3d_window_hpc/`.

#### Provenance: lri_3d_window_hpc and the d = 3 production records

##### Code

| part | written by | when | commit |
|---|---|---|---|
| Numerical code 0.2.0rc1 (`code/`, `reference/`, `tests/` except the Expanse tests, `benchmarks/`, `validation/`, `cluster/` except `cluster/expanse/`, docs) | OpenAI GPT-6 astra (model stated by the author, 2026-10-14), via ChatGPT; supplied by the author as `lri_3d_window_hpc_performance_optimized.zip` | received 2026-10-07 | b5f6e1f (baseline, unmodified) |
| Expanse site layer (`cluster/expanse/`, `tests/test_expanse_lanes.py`, `EXPANSE.md`) | Claude Code (Claude Opus 5.5), under the claudex loop: plan reviewed by OpenAI GPT-6 astra (Codex CLI, effort xhigh) in 5 rounds; code inspected by fresh GPT-6 astra sessions in 2 rounds | 2026-10-07 | 77b37a6 … e895443 |
| L18/L20 projector repair 0.2.1rc1 (gesvd fallback after a failed gesdd null-space SVD, exact sizing, streamed hashing) | OpenAI GPT-6 astra (model stated by the author, 2026-10-14), via ChatGPT; supplied by the author as `lri_3d_L18_L20_fix.patch` and applied unmodified; manifest rebuilt and receipt stage added by Claude Code | 2026-10-08 | 33ef4f3 |
| Runbook caveat (inspection-3 finding L18-01) | Claude Code | 2026-10-08 | 7de47eb |
| large-shared partition in campaigns, partition-aware SU estimates | Claude Code (not inspected) | 2026-10-08 | ccd055a |
| `guard_cap_gib` opt-in (memory guard above the allocation, with a written reason) | Claude Code (not inspected) | 2026-10-09 | b330ee7 |
| Public tooling (`public.mk`, `public/*`) | Claude Code | 2026-10-13 | patches overlay |

The numerical source hash (`ht3d.hpc.source_hash()`: every `code/**/*.py` plus `inputs/prior_3d_points.json`) is
d27a3bc28838897de5f4fbee4c8d91e495161a1c9e0df17d20cd0e3478adaf8a. It is the same at 33ef4f3, 7de47eb, ccd055a and
b330ee7, and every shipped record carries it (replay check REC-SRC). Changes after 33ef4f3 touch only
`cluster/expanse/`, `tests/test_expanse_lanes.py` and docs.

`public/bp_x07.py` (the Borel–Padé value at Ds = 0.7) holds a script that Claude Code wrote and ran inline on
2026-10-08, during the independent check. The functions and coefficients are copied unchanged from the session
transcript; only the command-line wrapper is new. It reproduces the recorded output (1.4721437, spread
1.4721093–1.4721664, n = 29) exactly.

##### Production

All on SDSC Expanse (AMD EPYC 7742; allocation `<ACCOUNT>`), Python 3.11.9, numpy 2.3.5, scipy 1.17.0, numba 0.65.1,
llvmlite 0.47.0 (venv built from `cluster/expanse/requirements-expanse.txt`).

| campaign | what | release (receipt) | Slurm | dates (PDT) | charge |
|---|---|---|---|---|---|
| grid18 | 14 lanes, teacher N = 6 → N = 8 … 18, Ds = 0.52 … 0.7499 | 33ef4f35ff4b (54745249) | array 54762491, shared 16c/64G | 2026-10-08 about 08:05–09:50 | 542.4 SU |
| grid18sri | the same at Ds = 0.518149 | 33ef4f35ff4b (54745249) | 54762505 | 2026-10-08 | 45.3 SU |
| l20x06 | N = 20 at Ds = 0.6, J = 1 diagnostics | ccd055a99531 (54762738) | 54776102, large-shared 32c/1000G | 2026-10-08 19:51–23:51 | 997.4 SU |
| grid20 | N = 20, 13 Ds, scalar only | b330ee7c25c2 (54779486) | array 54780394, shared 32c/240G | 2026-10-09 07:39–09:45 | 1548.9 SU |
| grid20sri | N = 20 at Ds = 0.518149, scalar only | b330ee7c25c2 (54779486) | 54780407 | 2026-10-09 | 208.1 SU |
| (static cache) | N = 20 graph and projectors (no record shipped) | 33ef4f35ff4b | 54762506, large-shared 4c/224G | 2026-10-08 08:04–19:45 | ended out of memory in the spin-1 vertices; spin-0 parts used |

Charges are measured from Slurm accounting (billing TRES), as reported by `campaign.py status`. The physics choices
(the Ds grid, adding 0.518149, the N = 20 point at 0.6 before the grid, scalar-only N = 20) were the author's
decisions, made on Claude Code's recommendations.

The records ship byte-identical: each carries `record_sha256` over its canonical JSON, including the production
paths of its inputs, and names its seed and basis by sha256.

##### Independent check

`../lri_3d_window_indep`, written by Claude Code (Claude Opus 5.5) on 2026-10-08 from the method description
(`reference/baseline/docs/METHOD.md`) only, without reading or importing `code/ht3d`. It was run on Expanse
(campaign-free Slurm jobs, 2026-10-08). See that package's PROVENANCE.

### `lri_3d_window_indep`

Folder: `code/lri_3d_window_indep/`.

#### Provenance: lri_3d_window_indep

- **Written by:** Claude Code (Claude Opus 5.5), the session that also ran the d = 3 production. Written on
  2026-10-08 at the author's request: "do a fully independent check of the solver, to make sure it is correctly
  calculating what we want".
- **Inputs:**
  - the method description of the supplied package (`lri_3d_window_hpc/reference/baseline/docs/METHOD.md`), with the
    formulas re-derived;
  - the production records, read only through `indep_extract.json`, for the couplings to compare at.
  - The production code (`code/ht3d`) was neither read nor imported.
- **Run:** on SDSC Expanse, `shared` partition, in the production venv (Python 3.11.9, numpy 2.3.5, scipy 1.17.0),
  2026-10-08.
  - Array 54766121 (`indep.sbatch`, `tasks.txt`) and the single jobs in `l8.sbatch`, `retune*.sbatch` and
    `spin.sbatch`.
  - Three N = 12 tunings were rerun from a 2% start (54771132, 54771237, 54772616).
  - The scripts and `.sbatch` files ship as they ran. The `.sbatch` files contain the production paths; the template
    with placeholders is `public/slurm/compare.slurm`.
- **Report:** `public/INDEPENDENT_CHECK.md`, written by Claude Code on 2026-10-08 and last updated the same day with
  the N = 12 tunings; one dated wording correction on 2026-10-18 (the zero-mode basis, under question A). Its part B
  (physics against the continuum, at N ≤ 18) is the source of the HT note's statement that the d = 3 values are not
  yet close to the continuum at Ds = 0.7.
  - Its Borel–Padé numbers come from the script that ships as `lri_3d_window_hpc/public/bp_x07.py`.
  - Its perturbative cross-check (Sec. A2) compares against `lri_3d_hpc` coefficients at L ≤ 14 (HT_Pert); it is
    not quoted in the paper.
- **Not reviewed by Codex.**
- **Public tooling** (`public.mk`, `public/test_indep.py`, `public/replay_indep.py`): Claude Code, 2026-10-13.
