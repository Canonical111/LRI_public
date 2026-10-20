# Provenance of the HT_Pert packages

For each package: where it comes from, who wrote it (the author, Claude Code sessions, OpenAI GPT-6 astra), the commit it was exported at, and what changed afterwards.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT_Pert/`. The values themselves are in `note/README.md` and the note.

- d = 1: exact C2..C5(Lambda) sums: `lri_1d_c4_exact`, `lri_1d_c5_exact`
- d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian: `lri_hpc_Hamitonian`, `lri_eh_hpc`
- d = 1: HT C8 and the complete-window coefficient flow: `lri_c8_hpc`, `lri_d1_full_coefficient_flow`, `lri_1d_dconn_refit`, `lri_d1_fullblock_tail_response`
- d = 2: coefficients C2..C8 and the independent check: `lri_d2_coeff_hpc`, `lri_2d_coeff_independent_check`
- d = 3: exact C2..C5(L) sums and the coefficients C2..C8: `lri_3d_c4_exact`, `lri_3d_hpc`

## d = 1: exact C2..C5(Lambda) sums

### `lri_1d_c4_exact`

Folder: `code/lri_1d_c4_exact/`.

#### Provenance: lri_1d_c4_exact

- **Authors.** Written by the Claude Code session HT1dPert (claude-opus-5-5) on 2026-10-12 at the author's request
  ("start the C4 port with codex review"). Two independent reviews by OpenAI GPT-6 astra (Codex CLI, reasoning effort
  xhigh), summarized in `REVIEWS.md`.
- **Method origin.** Ported from the d = 2 exact-C4 code (`lri_2d_coeff_expanse/independent_check/c4_exact`, session
  HT2dPert, shipped as HT_Pert/code/lri_2d_coeff_independent_check). Zero-mode paths and pattern enumeration were
  copied; the 1D densities, cutoff, shells and functionals are new.
- **Vendored inputs.**
  - `vendor/exact_fast.py`: `lri_eh_hpc/lri_eh/exact.py`, verbatim; the closed-form g²D window.
  - `vendor/brute_rs_cut4.py`: brute-force RS used by A3.
  - `vendor/check_lri_hamiltonian_orig.py`: the original HT reference implementation.
  - `inputs/`: reference data from the HT solver and the window analysis, with sha256 in `inputs/MANIFEST.txt`.
- **Commits.**
  - fb08bda: build.
  - d62b236: inspection round 1 fixes.
  - 5a40e72: inspection round 2 fixes; this is the production snapshot, sha256 a8b57b2e… over 38 files.
  - 16cf318: blind records frozen from the L1000 result.
  - 4e6fa9a: L2000 result and blind check.
  - fa23479: refit; shipped.
- **Production** on symmetry, 2026-10-12, all on amdq:
  - validation job 573824;
  - Λmax = 1000: jobs 573828 and 573829;
  - Λmax = 2000: array job 573837, with its assembly on sharedq as job 573894.
- No later change to code or results. `public/` was added on 2026-10-14 by HT1dPert.

### `lri_1d_c5_exact`

Folder: `code/lri_1d_c5_exact/`.

#### Provenance: lri_1d_c5_exact

- **Authors.** Written by the Claude Code session HT1dPert (claude-opus-5-5) on 2026-10-12/13 at the author's request
  ("start the C5 plan with codex review"). Reviews by OpenAI GPT-6 astra (Codex CLI, xhigh) are in `REVIEWS.md`.
- **Origin.** Extends `../lri_1d_c4_exact`. `rs5.py` is the d = 2 fifth-order RS generator (session HT2dPert),
  vendored verbatim. Reference inputs come from the HT solver, the window analysis and S10 (`inputs/MANIFEST.txt`).
- **Commits.**
  | Commit | Content |
  |---|---|
  | 1767d31 | plan approved |
  | 191613b | build |
  | f3ae8ab | inspection round 1 fixes |
  | f6f854b | inspection round 2 fixes |
  | 29a9985 | A5 validator change; production snapshot, sha256 040d92b3… over 53 files |
  | 6e15b08 | records frozen from L320 |
  | 1bf7bf5, 50143f0 | blind check against L400; records frozen from L400 |
  | 0917caa | L500 and its blind checks |
  | 91e6e80 | constrained fit |
  | 9ff34dc | cross-check records; shipped |
- **Production** on symmetry amdq, 2026-10-13: validation job 574043 (rungs L80, L160), then the rungs
  L240 (jobs 574047/574048), L320 (574063/574064), L400 (574075/574076) and L500 (574123/574124). The blind freezes ran
  as jobs 574074 and 574119.
- **Analysis jobs.** 574118, 574121–574122 and 574258 (refits, tail fits), and 574281 and 574283 (constrained fit).
- **Cited checks.** Written on 2026-10-13 by two Claude Code subagents of HT1dPert (claude-opus-5-5): a blind
  re-implementation (symmetry jobs 574286, 574292, 574295) and a theory check. Their reports ship verbatim as
  `fits/explore/constrained_L500/xchk/REPORT_*.md`.
- `public/` was added on 2026-10-14. No later change to code or results.

## d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian

### `lri_hpc_Hamitonian`

Folder: `code/lri_hpc_Hamitonian/`.

#### Provenance: lri_hpc_Hamitonian (and data/HT_1d/thermal_expanse)

##### Who wrote what
- **Baseline package** (`lri_hpc/` 1.0.0, `reference/`, the 8 original files of `tests/`, `benchmarks/`, `slurm/`,
  `validation_data/`, `export_results.py`, `pyproject.toml`, `requirements-tested.txt`, `README.md`, `PERFORMANCE.md`,
  the checksum lists `MANIFEST_SHA256.json`, `BUILD_INFO.json`, `original_source_hashes.json`): OpenAI GPT-6 astra (via
  ChatGPT), supplied by the author as `lri_hpc_optimized.zip` (sha256
  db35561208838c4d336e8d65169a30967b3f1c8cd5939c4b520b3d420cc40cca, 112 kB, 66 files, 2026-09-29). Committed as
  received at 67b009f (2026-09-29 13:32): the zip's 66 members are byte-identical to those files of the commit (checked
  2026-10-14); the commit adds only `.gitignore`, `EFFECTIVE_HAMILTONIAN_PROPOSAL.md`, `PHI6_JOINT_C7_REPORT.md`, the
  joint zip below and `analysis_original/`. The zip itself is not shipped. The archive's own records name the
  supplier's Linux container (`/mnt/data`, `/opt/pyvenv` paths, Python 3.13.5; `benchmarks/environment.json`). Five of
  its files were later changed by the review (Hash bindings below).
  - `reference/` (`check_lri_C7.py`, `check_lri_hamiltonian.py`, `compute_phi6.py`; sha256 in
    `original_source_hashes.json`) came in the same zip and is OpenAI GPT-6 astra (via ChatGPT) too; `check_lri_C7.py`
    is the original C7 check script. The package's tests use the three scripts as the reference oracle for the basis
    ranking, the operators and the solver at small cutoffs.
- **`analysis_original/`** (the joint φ⁶/C7 analysis with the Λ ≤ 50 thermal and φ⁶ data, `REPORT.md` =
  `PHI6_JOINT_C7_REPORT.md`): OpenAI GPT-6 astra (via ChatGPT), supplied by the author as
  `lri_phi6_joint_C7_results.zip` (sha256 0621eedb96cb183b21057e00d6009a0b049a30f5610ca9dac3ef1f273e36a2e7; members
  dated 2026-09-29 02:09–02:55). Extracted unchanged at 67b009f; its `MANIFEST_SHA256.json` verifies 34/34 (replay
  `a1.code`). The zip itself is not shipped (byte-identical content).
- **Review, gates, tests, Expanse layer, campaign, exports, report, analysis** (43c5c4d..c55d134, 2026-09-29..10-03):
  Claude Code (claude-opus-5-5), the session now named HT1dPert. Commits carry the author's git identity.
  - `review/CODE_REVIEW.md`, acceptance gates `lri_hpc/validate.py`, new tests, `cluster/expanse/`, `export_results.py`,
    `HPC_CAMPAIGN_REPORT.md`; the solver numerics were not changed (fingerprint c0c30783… from 6583645 on; the
    baseline fingerprints were 3a530ede (67b009f) and ba6d99db (43c5c4d, 74b0ac0)).
  - `analysis/extended/` (run_extended.py, explore_lower_edge.py, write_updated_results.py, check_identity.py,
    fetch_results.sh; the model classes in `analyze_joint.py` are byte-identical to the supplied original),
    `analysis/diagnose_systematic.py`, `analysis/audit_fits.py`, `DIAGNOSIS.md`, `UPDATED_RESULTS.md`.
  - Multi-agent workflows run by the same session on the personal desktop, in its temporary directory, then copied
    into the repository: `analysis/identity_checks/` (2026-10-02: engine A on the package kernels, engine B from
    scratch with exact rationals, a reconciler, numerical and theoretical challenge workflows), `analysis/eps5_window/`
    (2026-10-03, same structure), `analysis/eh_review/` (2026-10-02, review of lri_eh 0.2.0; only the g²D tables
    `physics-impact/{d5_all,d7_all}.json`, their generator `gen_deltas.py` and `dc4_exact.json` ship),
    `analysis/stress_test/` (2026-10-02, not shipped). DIAGNOSIS §§10–12.
  - `EFFECTIVE_HAMILTONIAN_PROPOSAL.md` (in the baseline commit 67b009f): author not recorded in the repository.
- **g²D tables** `analysis/eh_review/physics-impact/{d5_all,d7_all}.json`: made with lri_eh 0.2.0 (`code/lri_eh_hpc`,
  an unarchived copy with the same source fingerprint 2e2e8ca8…) by `gen_deltas.py` on the personal desktop (Python
  3.10.11, numpy 1.23.5, numba 0.56.4), 2026-10-02.
- **Public overlay** (`public.mk`, `public/`): Claude Code (claude-opus-5-5), session HT1dPert (builder A), 2026-10-14.

##### Commits (`lri_hpc_Hamitonian`, local git, branch main, no remote; EDT)
| Commit | Date | Content |
|---|---|---|
| 67b009f | 2026-09-29 13:32 | baseline as received, plus `analysis_original/` |
| 43c5c4d, 74b0ac0 | 09-29 13:44–13:45 | review round 1 fixes (gates, asserted full recursion, int64 test, fit audit); Expanse validation |
| 6583645, cd20385, f0a7084 | 09-29 14:00–14:26 | review rounds 2–4 fixes, campaign tooling; **f0a7084 = production revision** (gate V 54520426) |
| f984fb0, 21ac9f8, c209890 | 09-29 14:49–14:53 | campaign rule, diagnosis scaffold, CODE_REVIEW F7 |
| 6f97ba7, d9c6efd | 09-29 15:02–15:04 | inspection fix round 1 (IR-001..005), UPDATED_RESULTS generator |
| e1690e8 | 09-29 15:12 | inspection fix round 2 (IR2-001..003); **top-up revision** (gate V 54521491); uninspected |
| 008d257 … 3a55a86 | 09-29 18:27 – 10-01 21:06 | data snapshots, lower-edge study; final data 3a55a86 |
| 21fa640, 865c3b5 | 10-02 10:35–10:58 | revocation of the false d3 608 exhaustion; campaign report |
| f13784f, 9b475cf | 10-02 11:11–13:34 | stress test, lri_eh review (analysis only) |
| d379986 | 10-02 15:39 | identity checks through ε⁴, shift4 = 0.0186910 |
| c55d134 | 10-03 11:14 | complete window through ε⁵ (`eps5_window/`); **shipped** |

Outside `analysis/`, c55d134 equals e1690e8 plus `HPC_CAMPAIGN_REPORT.md` and one `.gitignore` line. From f0a7084 to
e1690e8 only `cluster/expanse/{campaign,run_lane,status,submit_cutoffs}.py`, `export_results.py`,
`tests/{run_all,test_campaign,test_extended_merge,test_validate}.py` and `review/CODE_REVIEW.md` changed; the solver is
identical (same fingerprint).

##### Records
- **Expanse campaign** (SDSC Expanse, AMD EPYC 7742, shared and large-shared partitions, 2 TB nodes; 2026-09-29..10-01;
  about 1180 core-hours). Lanes submitted 2026-09-29 11:47 PDT from the frozen checkout f0a7084 (jobs 54521089–96,
  54521313, 54522072 (resubmission after a node failure of 54521085), 54521314, 54521315): 34 thermal, 44 φ⁶ d5 and
  23 φ⁶ d3 records. Top-ups from e1690e8 (jobs 54524669, 54529459, 54529497): the 10 φ⁶ d3 records Λ = 512, 544, 576,
  640, 672, 704, 736, 768, 800, 832 (the last on the successor allocation, 2026-10-01). φ⁶ d3 Λ = 608 was not run.
- `data/HT_1d/thermal_expanse/` is the local copy that holds all 111 accepted outputs (the folder is gitignored in the
  package); `analysis/extended/{thermal,phi6_d5,phi6_d3}_new.json` are full copies (replay `a1.records`). The C8
  package's input table `data/HT_1d/c8/extrapolation/data.json` holds the same thermal rows bitwise (`a1.xcheck`).
- `campaign/plan.json` is the last plan written by `submit_cutoffs.py` (revision e1690e8, validation 54521491): the
  fingerprint, the 112 planned items and the 17 memory-rejected cutoffs (thermal ≥ 120, d5 ≥ 164, d3 ≥ 864).
- Analysis outputs were produced on the personal desktop (Python 3.10.12, numpy 1.24.4) from scratch copies and
  archived at the commits above; rerunning them there is bitwise.

##### Hash bindings
- `lri_hpc/` fingerprint c0c30783db5dd9a164fa16cb7ced5627c8dfa2cc2f1d81ab0c47ebc7518da2fb = `source_sha256` of every
  record and of `plan.json`.
- Files bound by other HT_Pert packages (sha256 in their records: `lri_1d_c4_exact`/`lri_1d_c5_exact`
  `inputs/MANIFEST.txt`, the S1B refits of `lri_1d_dconn_refit`, the C8 data table): `dC_reconciled.json` (0250b341…),
  `d5_all.json` (bd5211de…), `d7_all.json` (52192e13…), `top5.jsonl`, the 13 `exact5_c*.json`, `thermal_new.json`,
  `C7_extension.json`, `prior_c7/C7_completed_runs.json`; replay `a1.code` checks 26 such sha256.
- `analysis_original/MANIFEST_SHA256.json` (34 files) and `original_source_hashes.json` (3 reference scripts) verify.
- The root `MANIFEST_SHA256.json` (65 entries) is the as-received list of the baseline; at c55d134 it mismatches exactly
  the 5 files the review changed (`export_results.py`, `lri_hpc/__main__.py`, `lri_hpc/solver.py`, `tests/run_all.py`,
  `tests/test_full_recursion.py`); `a1.code` requires exactly that set. `BUILD_INFO.json` carries the baseline
  fingerprint. No code reads either.

### `lri_eh_hpc`

Folder: `code/lri_eh_hpc/`.

#### Provenance: lri_eh_hpc

- **Package** (lri_eh 0.2.0, dated 2026-10-02 in `BUILD_INFO.json`): OpenAI GPT-6 astra (via ChatGPT), supplied by
  the author as `lri_effective_hamiltonian_campaign_update.zip` (sha256
  3a480805e86e00d7e3dd421aea32f63091440d527d56b369372383c55d41c5e8, recorded in `BUILD_INFO.json`; the zip is not in
  the project folder and is not shipped). The folder `lri_eh_hpc/` is the snapshot built from it;
  it was never modified and is not a git repository. Its records name the supplier's build environment (a Linux
  container: `/mnt/data` paths and a container id in `benchmarks/validation_local.json` and its tests log; Python
  3.13.5).
  - `reference/original/` holds the incoming add-on and core unchanged (the oracle of the tests; part of the same
    zip); `docs/CORE_CHANGES.patch` documents the namespaced copy of the core in `lri_eh/_core/`, which is the lri_hpc
    1.0.0 baseline solver of `code/lri_hpc_Hamitonian` (`lri_hpc_optimized.zip`, also OpenAI GPT-6 astra via ChatGPT)
    with changes in `basis.py`, `kernels.py` and `operators.py` (`cache.py`, `parallel.py`, `solver.py` byte-identical
    to the baseline commit 67b009f).
  - Fingerprint: sha256 over `lri_eh/**/*.py` = 2e2e8ca899110e07997d9209437d1ca3c138275be43a3d27df498fff4b198c71
    (`BUILD_INFO.json`; recomputed by replay `a1.eh.code`).
  - Supplier's validation receipt `benchmarks/validation_local.json`, sealed (payload sha256 648fa9fb…, equal to
    `BUILD_INFO.json` validation_receipt_sha256): 32 tests passed and a gated degree-7 smoke at cutoff 20.
- **Use in this project** (Claude Code, claude-opus-5-5, the session now named HT1dPert, 2026-10-02): a multi-agent
  review of the package (archived in `code/lri_hpc_Hamitonian/analysis/eh_review/`, not shipped except the
  physics-impact tables) and the g²D tables `d5_all.json`, `d7_all.json`, made by its `gen_deltas.py` with an
  unarchived copy of this package (same fingerprint, recorded in the review's journal) on a personal desktop (Python
  3.10.11, numpy 1.23.5, numba 0.56.4). The exact shift and K were evaluated with `lri_eh/exact.py`
  (`dc4_exact.json`).
- **Later use**: `code/lri_1d_c4_exact` vendors `lri_eh/exact.py` verbatim (`vendor/exact_fast.py`).
- **Public overlay** (`public.mk`, `public/`): Claude Code (claude-opus-5-5), session HT1dPert (builder A), 2026-10-14.

## d = 1: HT C8 and the complete-window coefficient flow

### `lri_c8_hpc`

Folder: `code/lri_c8_hpc/`.

#### Provenance: lri_c8_hpc

##### Who wrote what
- **Original eighth-order code and the Λ ≤ 50 runs**: OpenAI GPT-6 astra (via ChatGPT), supplied by the author as
  `lri_phi4_C8_calculation.zip`. The archive is no longer in the project folder; its sha256 was not recorded.
  - It is kept in the package as `reference/original_code/` (solver), `reference/original_tests/`,
    `reference/C8_ORIGINAL_REPORT.md` and the 38 records in `inputs/raw/`, `inputs/vacuum_only/`.
  - These are 25 raw and 13 vacuum_only cutoffs, Λ ≤ 50, plus `inputs/exact_rational_validation.json`.
  - Its `reference/original_code/lri_hpc/` (8 files) is byte-identical to `lri_hpc/` of `lri_hpc_Hamitonian` at the
    baseline 67b009f. That baseline is OpenAI GPT-6 astra's `lri_hpc_optimized.zip` (via ChatGPT, sha256 db355612…,
    2026-09-29), not the author's code.
- **Optimized rewrite (baseline commit 7dc714d)**: OpenAI GPT-6 astra (via ChatGPT), supplied by the author as
  `lri_c8_hpc_optimized.zip` (sha256 3fa4ff6c8051d48792e0046632d66cbf9288ba7a5f97a8f4322f72167d607efd), received
  2026-10-03 11:27 EDT. It is itself a rewrite of GPT-6 astra's `lri_phi4_C8_calculation.zip` above.
  - `BUILD_INFO.json` records the supplier's sandbox: Python 3.13.5, numpy 2.3.5, numba 0.65.1, an AMD EPYC 9V74
    container.
  - The zip also carries two files it did not write: `reference/HPC_CAMPAIGN_REPORT.md`, written by Claude Code
    (byte-identical to `lri_hpc_Hamitonian` commit 865c3b5, 2026-10-02, the report of the Expanse cutoff push), and
    `reference/check_lri_hamiltonian.py`, from the `lri_hpc` baseline `lri_hpc_optimized.zip` (OpenAI GPT-6 astra;
    byte-identical to `reference/check_lri_hamiltonian.py` of `lri_hpc_Hamitonian` 67b009f).
- **The shared `lri_hpc` core.** The rewrite keeps the Fock-space and operator construction of `lri_hpc`:
  - `src/lri_c8/_core/{__init__,basis,cache,kernels,operators,parallel}.py` are byte-identical to `lri_hpc/` of
    `lri_hpc_Hamitonian` at 67b009f and at c55d134 (the shipped thermal solver);
  - `src/lri_c8/_core/solver.py` equals the 67b009f version (c55d134 later added result gates and a thread-count field,
    7 lines). The C8 engine calls its helpers (`extract`, `seed`, `sparse_reference`, `second_order_shell_value`, the
    vacuum terms);
  - the eighth-order driver is new: `engine.py`, `_reference_solver.py`, `residual.py`, `packed.py`.
  - Consequence: the thermal C0..C7 of `lri_hpc_Hamitonian` (row `c8.thermal`) come from a **separate thermal campaign
    (same `lri_hpc` core; different driver, cluster and runs)**. The 6.1e-14 agreement checks the C8 driver, the
    assembly and the runs, not the shared construction.
- **Symmetry port, fix rounds and runs** (99708a0..529f208 on 2026-10-03; validation and production on 2026-10-04):
  Claude Code (claude-opus-5-5), session HT1dPert (named "Hamitonian" at the time).
  - The commits carry the author's git identity with a Claude co-author trailer.
  - The port added the environment pin (`slurm/symmetry_env.sh`), batch scripts, the submit wrapper with its
    cross-node mutex, validation receipts, frozen campaign manifests, lane journals and O_EXCL owner files.
  - The numerics are bitwise unchanged against the supplied baseline.
  - Under `src/`, 7dc714d..529f208 changes `cli.py`, `io.py`, `__main__.py` and adds `_entry.py` and `_signals.py`
    (locks, owner files, receipts, signals).
  - The only edit in numerical code is a precondition check in `residual.py`: it raises if psi3 has support beyond
    P ≤ p + 12. It computes nothing new.
- **Code inspection**: Codex (Codex CLI, gpt-6-astra, effort xhigh), 8 rounds; see `REVIEWS.md`.
- **data.json builder**: `public/build_data_json.py` is a relative-path copy of the builder written by Claude Code on
  2026-10-05 for the LRI HT note (its `archive/c8_extrap/build_data_json.py`). `data.json` itself was written on
  2026-10-04 by the C8 extrapolation workflow; no builder was saved with it.
- **Public overlay** (`public.mk`, `public/`): Claude Code (claude-opus-5-5), session HT1dPert (builder B), 2026-10-14.
  The fix round after the independent verification (same day) added `public/rehash_manifest.py` and updated docstrings
  (costs, job ids, the wording of `c8.thermal`); no check changed.

##### Commits (`lri_ht_c8_symmetry/lri_c8_hpc`, local git, no remote; all 2026-10-03, EDT)
| Commit | Time | Content |
|---|---|---|
| 7dc714d | 11:31 | baseline: `lri_c8_hpc_optimized.zip` (OpenAI GPT-6 astra) as received |
| 99708a0 | 12:48 | port to symmetry defq (environment, batch scripts, receipts, owner files, guards) |
| 51dd066 | 13:04 | Codex round 1 fixes (C8-001..009) |
| e1abc41 | 13:21 | round 2 fixes (C8-010..014) |
| 9540e6a | 13:40 | round 3 fixes (C8-015..018) |
| 937067d | 13:54 | round 4 fixes (C8-019..022) |
| 07d39a3 | 14:13 | round 5 fixes (C8-023, C8-024) |
| 9bd5505 | 14:24 | round 6 fix (C8-025) |
| 529f208 | 14:37 | round 7 fix (C8-026); **APPROVED in round 8; shipped; production** |

No commit after 529f208. Source digest of `src/lri_c8` at 529f208:
dd811aca899543c4533e0c3f5e54cea67ae0cd06e875ceae8d68edaf4247cb81. It is recomputed by `replay`, row `c8.source`, and it
equals the value in the receipt, the campaign, every output and both export sidecars.

##### Runs (symmetry defq, author-approved, 2026-10-04 EDT)
Submitted by Claude Code (claude-opus-5-5), session HT1dPert (then named "Hamitonian").
- **Validation job 569659**: one exclusive node (Xeon Gold 6148), 11:36–11:44, PASS, 464.2 s. Receipt
  `data/HT_1d/c8/validation/receipt_dd811aca899543c4.json`, self-hashed and embedded byte for byte in the campaign.
- **Production array 569698**: campaign 654fb90d19a573c1, submitted 11:47:54; items ran 11:47:56–12:06:15 on 10 nodes.
  - 42 lanes, each with one attempt and exit 0.
  - Exports written at 12:08.
  - Records copied from the cluster to the project folder at 12:09. The copy matches the cluster archive byte for byte; this was
    re-checked on 2026-10-14 by set digests of the outputs, journals and checkpoints and the sha256 of the exports,
    the campaign and the receipt.
- **data.json** (C0..C8 for Λ = 2..92 and the thermal C0..C7 for Λ ≤ 118): built on 2026-10-04 as the common input of
  the C8 extrapolation lenses.
  - Its sha256 ccc77dfa… is recorded by the S1B refits (2026-10-09; `code/lri_1d_dconn_refit`).
  - It is also recorded by the copies vendored as `inputs/ht_data.json` in `code/lri_1d_c4_exact` and
    `code/lri_1d_c5_exact`.

##### Later changes
- None to the code or the records.
- The four-lens C8 extrapolation of 2026-10-04 (C8 = 8.0655e6) is superseded by the S1B refits and is not shipped
  (archive only).
- `public/` was added on 2026-10-14. Nothing under `src/` was added.

### `lri_d1_full_coefficient_flow`

Folder: `code/lri_d1_full_coefficient_flow/`.

#### Provenance: lri_d1_full_coefficient_flow (and data/HT_1d/s10_production)

- **Engine (supplied archive).** OpenAI GPT-6 astra (via ChatGPT), supplied by the author as
  lri_1d_full_coefficient_cutoff_flow.zip (561,529 B,
  sha256 457e154750668d07fe72bdf70e7d727b159e006f59a45dfd4ddca4b5e79b6af3), received 2026-10-08; authorship confirmed
  by the author, 2026-10-14. It was built outside this workspace: its `provenance/ENVIRONMENT.json` records Python
  3.13.5 on Linux. No file of the archive names its author.
  - It contains the archive records L = 2..44 and the forecasts frozen from older data (`results/`).
- **Vendored and input archives.** The archive's `vendor/` (`exact_window.py`, `fit_models.py`, `window_jets.py`) and
  `inputs/` (`PROTOCOL.json`, `scheme_data.json`, `asymptotic_constants.json`, `independent_gap_inputs.json`) come
  from three earlier supplied archives; the archive's `provenance/PROVENANCE.md` states that they are copied without
  alteration, and `provenance/ENVIRONMENT.json` pins the sha256 of the three archives and of these files
  (`input_archives`, `vendored_files`, `input_files`). All three archives are by OpenAI GPT-6 astra (via ChatGPT),
  supplied by the author; authorship confirmed by the author, 2026-10-14:
  - lri_1d_independent_coefficients.zip (sha256 899bf320cf5e0b0111499e5fe22dca84e2734b871ac8496e236bb1ccfbf80f8e);
  - lri_1d_asymptotic_fit_tests.zip (sha256 a6dacbff99e7f9a22c94d54e62121c4a8d7da75585a35272f2b95fe8be2defc9);
  - lri_1d_complete_order_kernel_assembly.zip
    (sha256 e83c573d238a2b9a769450d54c206c62438725172e46a6b30dab0882773d7a6f).
  The zips themselves are not shipped; the files taken from them ship under `vendor/` and `inputs/` (listed in
  `MANIFEST.sha256`).
- **Symmetry extension.** Claude Code (claude-opus-5-5), session HT1dPert (its session scratch held the plan and the
  Codex rounds), 2026-10-08, at the author's request, inspected by Codex (Codex CLI, gpt-6-astra, effort xhigh) over four rounds (REVIEWS.md).
- **Commits** (repository s10_extend, branch main; all 2026-10-08):

| Commit | Time (EDT) | Author | Content |
|---|---|---|---|
| 1ff8cfd | 08:25 | Claude Code | baseline: the zip as received, unmodified |
| 75510ad | 08:27 | Claude Code | extension to cutoffs > 44 (state guard option, O_EXCL locks, atomic writes, provenance block, compare_archive.py, slurm/, SYMMETRY_EXTENSION.md) |
| 91e7755 | 08:33 | Claude Code | Codex round-1 fixes S10-R1..R4 |
| cd3740e | 08:38 | Claude Code | Codex round-2 fixes S10-R5..R7 |
| fec60a2 | 08:43 | Claude Code | Codex round-3 fix S10-R8; round 4 APPROVED; **production commit, shipped** |

- **Production** (symmetry defq, launched by the same Claude Code session).
  - The commit was deployed as a read-only content-addressed snapshot (`code/fec60a25a2bb`). Its solver sha256
    854fc763… equals `git show fec60a2:code/ragged_quotient.py` and the provenance.code_sha256 of every record.
  - Validation job 571525 (Dconn L = 40, 42, 44 and raw L = 44 against the archive, rtol 1e-10): PASS at 08:59,
    with maximum deviations 5.3e-15 (C) and 5.1e-13 (vacuum grid).
  - Stage A, array 571531 (L = 46..60, three exclusive defq nodes): done 11:36.
  - Stage B, array 571598 (L = 62..72, tasks 571599, 571600, 571601, 571774, 571814): done 23:50.
  - The records were copied unmodified into lri_1d_coefficient_flow_review/s10_production; 14 sha256 were compared
    with the cluster copies.
  - `dconn_minus_raw_L46_72.csv` was written at 23:54 by the same session with an inline command.
    `public/make_dconn_minus_raw.py` (2026-10-14) reproduces it byte for byte.
- **Public layer.** `public.mk` and `public/` added on 2026-10-14 by a Claude Code subagent of HT1dPert (builder C).
  No later change to code or records; the documentation was corrected on 2026-10-14 after an independent verification
  (attribution of the vendored archives, wording).

### `lri_1d_dconn_refit`

Folder: `code/lri_1d_dconn_refit/`.

#### Provenance: lri_1d_dconn_refit (refits "S1B")

- **Authors.** Claude Code (claude-opus-5-5), session HT1dPert: four subagent stages of one workflow
  (wf_76420265-7dd), 2026-10-08 23:56 to 2026-10-09 01:28 EDT, at the author's request after the S10 cluster run.
  - delta-72 (agent af05daea0c7fdb1a7): the delta model on the hi = 72 data, its centrals and validation;
  - fit:joint (a236b3957b994aa1f): the joint linked-tail lens;
  - fit:model-independent (ab995b7dfd9efd4d2): the model-independent lens;
  - verify (addd19410a000c6f9): an independent re-implementation.
- **Origin of the code.** The code is that of run 1 of the refits (workflow wf_d621e067-74d, 2026-10-08, delta model
  on hi = 44 data), with small changes.
  - The delta stage copied `build_delta.py`, `ensemble.py`, `fitlib.py` and `load.py` byte for byte and changed no
    rule parameter.
  - The joint lens added the weighted fits, the S10 noise model, the hi = 72 windows and the dconn_s46/dconn_w
    datasets. Unit weights reproduce the run-1 fits exactly (`joint/code/regress_run1.py`: bit for bit on 49,284 o7
    and 62,208 o8 rows). `fitcore.py` re-implements the arb least squares of the C8 lens.
  - The model-independent lens added environment hooks (`MI_ACC_TOPS`, `MI_PRIMARY`) and a central/tag consistency
    assertion.
  - The stage scripts are verbatim copies of the session scratch; they were archived on 2026-10-09 01:28 with the
    large files excluded. The archive is not a git repository.
- **Jobs on symmetry** (2026-10-09).
  - Joint lens, sharedq: scans 572001 (o8), 572002 (o7), 572030 (o8_w), 572031 (o7_w); post-processing 572041 (an
    earlier attempt, 572025, stopped on a TypeError).
  - Model-independent lens, debugq: 571993, 571994, 572039, 572026, 572040 (572008 failed on a subshell bug and was
    resubmitted as 572026).
  - Verifier, sharedq: 572083.
- **Run 1** (superseded) is represented only by the files that S1B reads or compares with:
  - `delta/archived_out_delta_v1/`, byte-identical to the run-1 delta outputs, with the blind forecast frozen at
    2026-10-08 08:35;
  - `joint/archived_run1/summary.json`;
  - `run1/joint/out/variants_full.json`.
- **Inputs from other packages:** `data/HT_1d/c8/extrapolation/data.json` (lri_c8_hpc), `dC_reconciled.json/.csv`,
  `d5_all.json` and `d7_all.json` (lri_hpc_Hamitonian), and the S10 archive table and production dC table
  (lri_d1_full_coefficient_flow). The delta outputs record all their sha256 (replay row rf.inputs).
- **Public layer.** `public.mk` and `public/` were added on 2026-10-14 by a Claude Code subagent of HT1dPert
  (builder C). No later change to code or outputs.
- **Macros.** The C4..C8 values were read from the stage results on 2026-10-09/12. Since then:
  - `\HTpCeightOneDev` was recomputed against the final C8(1) (8,059,766.72);
  - on 2026-10-14 (author decision) the paper's C4 and C5 were switched to the exact sums (`code/lri_1d_c4_exact`,
    `code/lri_1d_c5_exact`). The solver-fit C4 and C5 of this package keep their values and checks and are quoted in
    the HT_Pert note only, as `\NOneCfourSolver`, `\NOneCfourSolverDev`, `\NOneCfiveSolver` and `\NOneCfiveSolverDev`
    (formerly `\HTpCfourOne`, `\HTpCfourOneDev`, `\HTpCfiveOne`, `\HTpCfiveOneDev`);
  - the replay re-derives every quoted value from the shipped JSON outputs, so the workflow journal is not needed.
- **Public-layer fixes** (2026-10-14, after an independent verification by a Claude Code subagent): the dataset of
  each union component is named (fixed A–F unweighted, floor+stat weighted, MI model-independent), the weighted fixed
  A–F alternative is printed as an INFO row (rf.C7w), the rounding rule of every union is stated, the fallback
  tolerance of `test` is field-scaled, and the privacy class of the derived delta tables is corrected (scrubbable). No
  change to code or outputs of the stages.

### `lri_d1_fullblock_tail_response`

Folder: `code/lri_d1_fullblock_tail_response/`.

#### Provenance: lri_d1_fullblock_tail_response

- **Authors.** Written by OpenAI GPT-6 astra (via ChatGPT) and supplied by the author. The author stated on 2026-10-14
  that the whole tails lineage was written by that model. The bundle shows the generating environment:
  - Python 3.13.5 on Linux x86-64 (`results/ENVIRONMENT.json`);
  - figure timestamps of 2026-10-07.
- **How it reached us (hash chain).**
  1. Delivered as `lri_1d_fullblock_overlap_matching.zip`, sha256
     35ff57dd93c0e4c429d537a3c5aaa65d730329edc3b200f2d98c1743d07827f2. That zip is not kept in the project; its hash
     is recorded by the next delivery.
  2. Retained unchanged as `upstream/lri_d1_fullblock_tail_response` of `lri_1d_nested_overlap_scale_matching.zip`
     (sha256 5dfd3046…), per that package's `inputs/PROVENANCE.json`.
  3. That package was in turn retained unchanged as `upstream/lri_d1_scale_matching` of
     `lri_1d_complete_phase_overlap_tails.zip`:
     - 1,339,863 bytes, sha256 c4b830a34f869c26264f2267125692f6c50af1b2dd190da0edbd826f417d623e;
     - supplied by the author on 2026-10-07 and kept in the project root.
- **Shipped copy.** The 109 shipped files are byte-identical to the members of the last zip (checked 2026-10-14).
  `MANIFEST.sha256` (108 entries) verifies.
- **Its inputs.** `inputs/PROVENANCE.json` pins the archives the authors started from:
  - HT.zip (101bcfdc…);
  - lri_1d_independent_coefficients.zip (899bf320…);
  - lri_1d_C8_boundary_counterterm_tails.zip (4e4a4379…);
  - lri_1d_C6_C7_C8_analytic_tails.zip (5765c228…).

  `vendor/window_jets.py` (8825bd05…) is copied verbatim from lri_1d_independent_coefficients.zip. No thermal C6–C8
  value enters any algorithm (README, METHOD Sec. 7).
- **Review.** A Claude Code workflow reviewed the tails bundle that contains this package on 2026-10-07 (`REVIEWS.md`).
  The review ran the package's tests but changed nothing.
- **Not git.** No later change to code or results.
- **Public overlay.** `public.mk` and `public/` were added on 2026-10-14 by builder D, a Claude Code (claude-opus-5-5)
  subagent of the session HT1dPert, for the public release.
- **Paper use.** One caveat sentence in the Hamiltonian truncation section (fact C6, `pert_facts.md`). No macro.

## d = 2: coefficients C2..C8 and the independent check

### `lri_d2_coeff_hpc`

Folder: `code/lri_d2_coeff_hpc/`.

#### Provenance: lri_d2_coeff_hpc (d = 2 eighth-order coefficient solver)

| Item | Value |
|---|---|
| Public path | `HT_Pert/code/lri_d2_coeff_hpc/` |
| Exported commit | **f847d38db8bdd25adce27852322d480a61098c2d** (2026-10-08), the release `lri2d_coeff-f847d38db8bd` (tar sha256 2e2edf6c…) that produced every record in `HT_Pert/data/HT_2d/prod` |
| Origin of the numerics | `lri_2d_coefficients_hpc_optimized.zip` (sha256 94edc677…; baseline commit 8db8f15, unchanged), an optimization of the coefficient solver of `lri_2d_C8_perturbative_check.zip` (sha256 5c0d5209…, retained verbatim in `reference/lri_d2_perturbative_C8/`, with its own `upstream/lri_2d_hpc_optimized` and exact oracle). Both were written by **OpenAI GPT-6 astra (via ChatGPT)** (stated by the author, 2026-10-14) and delivered as conversation attachments |
| Cluster layer and fixes | 0d99d55 → c606cbd → 3e2ef17 → f847d38, a Claude Code session (Claude Opus 5.5), 2026-10-08: release tar, validation receipt gate, one job per task, node-local checkpoints with verified publication, Expanse/symmetry site settings. `src/lri_coeff` unchanged (source digest 550e9266… before and after) |
| Reviews | Codex (OpenAI GPT-6 astra, effort xhigh): inspection r1 9 findings, r2 5, r3 3, all fixed; **APPROVED r4 at f847d38**. See REVIEWS.md |
| Production | symmetry (prod1, L = 16..30, jobs 571628–571643, 2026-10-08; check_small, L = 2..14) and SDSC Expanse (prod2, L = 32, 34, jobs 54765966–68, 54771256, 2026-10-08) |
| Public layer | `public.mk`, `public/{replay_prod.py, verify_manifest.py, smoke_check.py, requirements.txt}`, REVIEWS.md: new for the release (2026-10-14, Claude Code session HT2dPert); not reviewed by Codex |

##### Later changes
None to the exported code. An unreviewed branch `zeromode` (b291854, a zero-mode window in the solver) was stopped by
the author on 2026-10-08 and is not shipped; the window question was solved by exact large-L sums instead
(`lri_2d_coeff_independent_check`).

### `lri_2d_coeff_independent_check`

Folder: `code/lri_2d_coeff_independent_check/`.

#### Provenance: lri_2d_coeff_independent_check (independent check and large-L extension, d = 2)

| Item | Value |
|---|---|
| Public path | `HT_Pert/code/lri_2d_coeff_independent_check/` |
| Source | `<PROJECT>/lri_2d_coeff_expanse/independent_check/` (not a git repository); snapshot of **2026-10-14**; every shipped file with its sha256 in `public/SNAPSHOT.sha256` (594 files) |
| Method write-up | merged on 2026-10-16 into Appendices A to C of the HT_Pert note (`HT_Pert/note/`; author's rule: one TeX note per direction) from `<PROJECT>/lri_2d_coeff_expanse/LRI_2D_HT_eps4_note/LRI_2D_HT_eps4_note.tex` as of 2026-10-14 (source never edited), by HT2dPert: notation of the HT_Pert note, superseded values and the appendix on internal source inconsistencies left out, statements already in the d = 2 section of the note not repeated, the R3 cancellation worded as in the 2026-10-15 review (expected, not established beyond L <= 16), and every cited record checked to ship in this package. No separate write-up is shipped |
| Authors | Claude Code sessions (Claude Opus 5.5), 2026-10-08..14: the coordinating session (HT2dPert, forked from the session that ported the production solver) and agents it launched — two clean-room solver agents (`rs_exact`, `cauchy`; they saw only `SPEC.md`), a continuum agent (`continuum`), the exact-C4 agent (`c4_exact`), the zero-mode oracle agent (`zeromode_exact`), the complete-window agent (`complete_exact`), the window-derivation agent (`residual_log`: WINDOW_SPEC, ε⁵ engine, `ce_wc`, tagged channels), the large-L agent (`residual_log/large_L`: chain sums to L = 16000, optimized engine `lib_opt`, C5 to L = 300) and a write-up agent (the method write-up, now Appendices A to C of the HT_Pert note). Parent checks (`residual_log/fits/parent_check_*`) by the coordinating session |
| Inputs from elsewhere | the model definition and the consistent/literal windows of the delivered package (`../lri_d2_coeff_hpc/docs/METHOD.md`); the production records (`HT_Pert/data/HT_2d/prod`, for comparisons only); continuum values from the condensed note (`continuum/reference_values.csv`) |
| Runs | symmetry cluster only (amddebugq, amdq, debugq, defq; whole nodes; job names indep2d-*), 2026-10-08..14; light fits on the authors' personal desktop. Largest: exact raw C5(L) to L = 300 (≈ 167 node-hours in all, including a stopped first attempt of 130 node-hours with the unmodified engine and 37 node-hours with `lib_opt`, regression included); C4(L) to L = 2000 (≈ 1.5 node-hours) |
| Reviews | no external code review; redundancy and parent checks (REVIEWS.md) |
| Public layer | `README.md`, `REVIEWS.md`, `public.mk`, `public/{replay_p2.py, replay_full.py, test_p2.py, verify_snapshot.py, SNAPSHOT.sha256, requirements.txt, slurm/run.sbatch.in}`: new for the release (2026-10-14, Claude Code session HT2dPert); not reviewed by Codex |

##### Later changes
None to the snapshot. Not shipped (export_entries.json `not_exported`): the internal SUMMARY.md and research logs
(residual_log/README.md, large_L/README.md; their content is in Appendices A to C of the HT_Pert note), run caches and raw residues
(including 13 pickled operator caches), Slurm logs, superseded fits and runs, diagnostic window variants, two
symlinks.

## d = 3: exact C2..C5(L) sums and the coefficients C2..C8

### `lri_3d_c4_exact`

Folder: `code/lri_3d_c4_exact/`.

#### Provenance of lri_3d_c4_exact

##### Who wrote it

Written for the author by Claude Code (Claude Opus 5.5), session HT3dPert, through a forked sub-agent, on
2026-10-12 (C2..C4) and 2026-10-12/13 (C5). The model-independent eps^5 modules (`eps5/rs.py`, `chains.py`,
`assemble.py`, `windows5.py`, `windowsW.py`, `schemeW.py`, `bloch.py`), the window definitions (W, Wc, Wcs) and the fit
library were ported from the d = 2 exact-sum package written by the Claude Code session HT2dPert (shipped in
`HT_Pert/code/lri_2d_coeff_independent_check`), with the d = 3 changes listed in `README.md` Sec. 7.1. The model is
pinned to `lri_3d_hpc/reference` (supplied by the author; written by OpenAI GPT-6 astra via ChatGPT).

##### History (git)

| Commits | Date | What |
|---|---|---|
| `fa696f6` .. `07f93c0` | 2026-10-12 | C2..C4 engine, validation against the package, windows, brute force with a zero-mode window, fits |
| `667e052` | 2026-10-12 | C2..C4 results to L = 600 and window shifts to L = 8000; the complete window W converges to C4(3) |
| `bcb4b8c` .. `ef7f042` | 2026-10-12 | eps^5 engine, brute force with explicit window operators, leg response, tagged channels, C5 to L = 20 |
| `c7a23fe` .. `d45be4c` | 2026-10-12/13 | engine speed-ups (exact Racah sum, streaming, cached 4-vertex boxes) and memory fixes |
| `2e4ae6f` .. `d5afa4f` | 2026-10-13 | raw C5 to L = 40, analysis, README; regression of the final engine |

Shipped at `d5afa4f` (code identical to `d45be4c`, the engine of the L = 40 run; later commits change only results,
README and `eps5/fits5.py` output). Two production files changed after the C2..C4 runs: `c4lib3d.py` (mode tables
generalized to higher eps order for eps^5, `bcb4b8c`) and `c4_run3d.py` (selectable multiprocessing start,
`e3ab454`). `make test` recomputes C2..C4 at L <= 40 with the shipped code and compares with the production
`results/c4_L600.npz` (2.4e-12 measured; tolerance 1e-9 for the different angular quadrature).

##### Production runs (symmetry cluster)

| Job(s) | Partition | Output |
|---|---|---|
| 573804 | debugq | `results/c4_L200.npz`, `c4_L300.npz` (34 s, 174 s) |
| 573808 | debugq | `results/windows_L8000.npz`, `offdiag_L8000.npz` |
| 573812, 573817 | debugq | `results/dchi_L600.npz`, `dchi_L1000.npz` |
| 573841 | preq | `results/c4_L600.npz` (C2..C4 at every even L <= 600; 1953 s on one node) |
| 573888 | sharedq | `results/c5_L12.npz` |
| 573920-573923, 573933 | sharedq | `results/c5_L20.npz` (every scheme, L <= 20; four shards and the assembly) |
| 573948 | sharedq | `results/c5raw_sp_L20.npz` |
| 573899, 573993 | sharedq | `results/dC5_L200.npz`, `dC5_L600.npz` (scheme shifts; 3 min, 2 h 56 min) |
| 573893 | sharedq | `results/eps5/legw_L400.npz` |
| 573892, 573905, 573931, 574289 | sharedq | brute force (`results/brute`, `tag`), descendant checks (`results/eps5/desc_L*.json`, L <= 16), tagged chi channel |
| 574287 | defq | `results/c5raw_all_L40.npz` (raw C5 at every even L <= 40; 1 h 45 min on one 80-thread node, 20 workers) |
| 574029, 574030, 574365 | sharedq, defq | regressions of the final engine (`results/regress/`): L <= 20 to 5e-13; all 34 reduced L = 40 boxes bitwise |

Failed and cancelled attempts (out of memory at L = 20 and 40 before the memory fixes, and at L = 56 after them; profiling) are listed in
`README.md` Sec. 7.5; none produced a shipped result. The analysis scripts (fits) ran on a personal desktop. The
longest shipped runs are 573993 (2 h 56 min on 8 cores), 574287 (1 h 45 min on one node), the L = 16 brute force
574289 (1 h 34 min) and the regressions 574030, 574365 (1 h 18 min, 37 min); the others took minutes.

##### Later use

- 2026-10-14: the author adopted the extrapolated C2..C4(3) and the C5 footnote for the paper's d = 3 column of
  Table htpert, replacing the finite-cutoff ratios of `lri_3d_hpc`. The values were rounded by the PDG rule from the
  shipped fit summaries; `make replay` recomputes them.
- 2026-10-18: the author moved C5(3) from the footnote into Table 2 (delta 3e-2, marked provisional in the caption).
  The paper is final at `a6772872`: Table 2 (`tab:htpert`, Sec. 3.1), d = 3 column.
- The comparison with the production package (`validate_pkg.py`, `eps5/validate5.py`) is the d = 3 independent-code
  check: the package (GPT-6 astra) builds the truncated Hamiltonian explicitly; this package sums diagrams.

### `lri_3d_hpc`

Folder: `code/lri_3d_hpc/`.

#### Provenance of lri_3d_hpc and of the d = 3 perturbative records

##### The package

| What | Who | When | Commit |
|---|---|---|---|
| The original 3D finite-cutoff calculation (`reference/perturbative.py`, `reference/taylor_vertices.py`, `vendor/ht3d/`) and the optimized solver (`code/`, `tests/`, `hpc/`, `docs/`, `benchmarks/`, `results/`, `fixtures/`) | OpenAI GPT-6 astra (via ChatGPT), for the author; supplied by the author as one archive, `lri_3d_hpc_optimized.zip` | received 2026-10-08 | `14b10e2` (the archive as received) |
| Port to SDSC Expanse and the symmetry cluster: precision and residual gates, no-clobber publishing, cluster-wide output lock, rank-local MPI sortedness, the two-site `cluster/` layer (staged releases, validation receipts, stage runner, submit wrapper) | Claude Code session HT3dPert (Claude Opus 5.5), for the author | 2026-10-08 | `e85d3b7`, `feb13d4`, `ccd1eab` |
| Fix rounds 1 to 10 after Codex inspections (OpenAI GPT-6 astra, effort xhigh) | the same Claude Code session; findings by Codex | 2026-10-08 | `59a4d22`, `b4a1c11`, `f6069aa`, `22b9885`, `3fe8a52`, `5f0eeeb`, `be6060d`, `cd4832a`, `ba88b4f`, `8fa8339`, `7c8a67e` |
| Codex inspection round 11: APPROVED | Codex | 2026-10-08 | `7c8a67e` |
| This public overlay (`public.mk`, `public/`), the records manifest, the replay and these documents | Claude Code session HT3dPert (Claude Opus 5.5) | 2026-10-14 | not in the package's history |

The numerical code of the supplied archive (`code/*.py`, `code/native_kernels.cpp`, `reference/`, `vendor/`) was not
changed by the port except where the commit messages say so (gates, publishing and locking around the solver; the
solver arithmetic is unchanged). Every production result and gate record carries the sha256 of the eight files of
`code/` it ran with (`request.source_sha256`); `make replay` (check REC-SRC) compares them with the shipped files.

The package ships at `7c8a67e`, the release of the production campaign (`campaign.json`: `release.git_sha`
`7c8a67e1fe5bfc47c00d0130d0a12e657d55e49d`). No later commit exists. Before publication, the authors' cluster paths in
`cluster/RUNBOOK.md` were replaced by placeholders (`public/SCRUBBED.txt`).

##### Validation receipts of the release (not shipped; quoted here)

The production campaign is frozen to a release and to the environment a validation receipt passed on
(`cluster/receipt.py`: the package's checks, the L4 fixture at 1e-16, an L14 store built by the stage runner and its
cutoff-14 gates, the 32-case L14 grid, MPI tests and failure drills):

| Site | Job | Node class | Result |
|---|---|---|---|
| symmetry | 571711 (amddebugq) | AMD EPYC 7532 | passed, 30 stages, 334 s |
| SDSC Expanse | 54770924 (debug) | AMD EPYC 7742 | passed (the receipt the campaign is frozen to) |
| SDSC Expanse | 54771372 | AMD EPYC 7742, 2 nodes | MPI receipt, passed |

Environment of the campaign (identical stack on both sites, from the hash-pinned `cluster/requirements.lock`): CPython
3.12.9, numpy 2.5.3, scipy 1.17.0, numba 0.68.0, llvmlite 0.50.0, mpi4py 4.1.2 (built from source); g++ 13.3.0 on
Expanse. The L14 stores built on Expanse and on symmetry are value-identical (padding-free fingerprint), and their
cutoff-14 gates differ by exactly zero; both differ from the supplier's reference results by at most about 1.2e-14
(float64 SO(3) projector, BLAS/libm).

##### The production campaign `pert3d` (SDSC Expanse, 2026-10-08/09)

The author chose Expanse for production on 2026-10-08. One campaign, frozen to release `7c8a67e` and environment
fingerprint `782c2c7a...`:

| Job | Partition, request | Stages | Wall | Charge |
|---|---|---|---|---|
| 54772054 | shared, 16 cores, 32 GB | L16: prepare, images, matrix, finalize, verify, gate, solve, crosscheck | 18.5 min | about 10 SU |
| 54772079 | shared, 64 cores, 200 GB | L18: prepare .. solve | 36 min | about 60 SU |
| 54773175 | shared, 64 cores, 200 GB | L20: prepare, images | 10 h 12 min | about 1020 SU |
| 54779357 | large-shared, 64 cores, 1700 GB | L20: matrix, finalize, verify, gate, solve (L = 16, 18, 20 from the L20 store) | 3 h 26 min | about 1460 SU |

In total about 2550 SU. All gates passed; the records are in `HT_Pert/data/HT_3d/pert3d` and the table in
`HT_Pert/results/HT_3d/SUMMARY.md` (written 2026-10-09 by the same session from the result records; `make replay`
rebuilds it). The intermediate pipeline files (363 GiB) and the vertex stores (L16 2.6 GiB, L18 22 GiB, L20 177 GiB)
are not published (`HT_Pert/data/HT_3d/DATA.md`).

##### Later use

- 2026-10-10: the ratios C_n(20)/C_n were formed against the diagrammatic values (paper Table 1) and quoted in the
  paper (`\HTpRatio<n>Three`); no extrapolation was made (three cutoffs, no complete window).
- 2026-10-14: the paper replaced these ratios by the extrapolated C2..C4(3) of the exact sums (`lri_3d_c4_exact`),
  which agree with this package's results at every even L <= 20 to about 1e-13.
- 2026-10-19: the final paper (`a6772872`) prints no number of this package; `\HTpThreeLmax`, the ratios and the
  L = 14 gate stay defined, unprinted, in its `numbers.tex`. The HT_Pert note quotes the cutoffs and the gate.
- The finite-coupling package `HT/code/lri_3d_window_hpc` reads C4(20) of the consistent scheme from
  `HT_Pert/results/HT_3d/SUMMARY.md` (60.26 % of C4(3), quoted there as 60 %).
