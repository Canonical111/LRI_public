# HT_Pert data

What is in git and what is hosted (hosting planned on Zenodo, no record yet; `fetch-data` targets print where the files go and their sha256).

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT_Pert/`. The values themselves are in `../note/README.md` and the note.

- d = 1: exact C2..C5(Lambda) sums: `lri_1d_c4_exact`, `lri_1d_c5_exact`
- d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian: `lri_hpc_Hamitonian`, `lri_eh_hpc`
- d = 1: HT C8 and the complete-window coefficient flow: `lri_c8_hpc`, `lri_d1_full_coefficient_flow`, `lri_1d_dconn_refit`, `lri_d1_fullblock_tail_response`
- d = 2: coefficients C2..C8 and the independent check: `lri_d2_coeff_hpc`, `lri_2d_coeff_independent_check`
- d = 3: exact C2..C5(L) sums and the coefficients C2..C8: `lri_3d_c4_exact`, `lri_3d_hpc`

## d = 1: exact C2..C5(Lambda) sums

### `lri_1d_c4_exact`

Folder: `code/lri_1d_c4_exact/`.

#### Data: lri_1d_c4_exact

Everything is in git; nothing is hosted.
- **`data/HT_1d/exact_c4/a8b57b2e8475/`** (3.2 MB, from the package's `results/` at fa23479):
  - `c4_1d_L200.npz`, sha256 6609e144…
  - `c4_1d_L400.npz`, sha256 7bd352ac…
  - `c4_1d_L1000.npz`, sha256 6bf66da2…
  - `c4_1d_L2000.npz`, sha256 62720cf5…
  - `gates_L*.txt`
- **Record binding.**
  - Each gate record binds its result's sha256; the A6d lines bind the previous rung's result.
  - The results are record-bound and ship byte-identical.
  - The gate records carry the cluster path of the result ("result <path> sha256 …"). That path is not read by the
    replay, which uses only the sha256, so it may be scrubbed.
  - The npz provenance holds the production snapshot manifest (sha256 of 38 code files). These code files are
    therefore record-bound; any scrubbed one must be listed in `public/SCRUBBED.txt`.
- **Fit records in the package.**
  - `fits/frozen/frozen_L1000_{Dconn,raw}.json`: self-hashed via the `.sha256` files and record-bound.
  - `fits/blind_check_L1000_to_2000.txt`, `fits/explore/*.txt`: script outputs, not bound. Their header lines carry
    the cluster paths of the run and may be scrubbed.
- **Not shipped.** The task checkpoints (cache_L*, several GB, regenerable), the logs and the validation markers.

### `lri_1d_c5_exact`

Folder: `code/lri_1d_c5_exact/`.

#### Data: lri_1d_c5_exact

- **`data/HT_1d/exact_c5/040d92b3bd1d/`** (2.7 MB). It comes from the package's untracked `results/040d92b3bd1d/`,
  identical to the symmetry copy. Contents:
  - `c5_1d_L80.npz` (5e2711f6…), `L160` (ba5d4120…), `L240` (cf332ac0…), `L320` (d02f09cc…), `L400` (d94beb9c…) and
    `L500` (0c10152a…);
  - `gates_L*.txt`.
  These results are record-bound: the gate records and the next rung's A6d line bind them, and they ship
  byte-identical. Paths in "result <path>" lines may be scrubbed, since the replay reads only the sha256.
- **Code binding.** The npz provenance holds the production snapshot manifest (53 files). Files scrubbed for paths
  must be listed in `public/SCRUBBED.txt`: `validate/test_core.py`, `validate/test_kernel5.py`,
  `validate/v6_overlap.py` and the `slurm/` files carry absolute paths.
- **Fit records** (in the package, git):
  - `fits/frozen/*.json`: self-hashed by `.sha256`, record-bound.
  - `fits/blind_check_*.txt`, `fits/explore/**`: script outputs, not bound. Their header paths may be scrubbed.
- **Cited blind re-implementation.**
  - Shipped: code, tasks, summary and tables.
  - Its raw per-fit results (`results_574286.jsonl`, `results_574292.jsonl`, `results_574295.jsonl`, 71 MB) are not
    in git. They are hosted in the Zenodo data record (DOI 10.5281/zenodo.23466766) as `HT_Pert__lri_1d_c5_exact__cfit_blind_results.tar.gz`
    (28.2 MB, sha256 673f7299…, byte-identical members). `make -f public.mk fetch-data` downloads it, checks the sha256
    of the archive and of each member (`public/hosted.json`), and unpacks the three files into
    `fits/explore/constrained_L500/xchk/cfit_blind/`, where `final_table.py` reads them. `DATA_URL` defaults to
    `https://zenodo.org/records/23466766/files`. The three node jobs also regenerate them.
- **Not shipped.**
  - The task checkpoints (cache_L*, tens of GB, regenerable).
  - The gate logs (`gatelogs_*`: the outputs of the gate validators; their verdicts are in `gates_*.txt`).
  - The validation markers and logs.

## d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian

### `lri_hpc_Hamitonian`

Folder: `code/lri_hpc_Hamitonian/`.

#### Data: lri_hpc_Hamitonian

Everything is in git; nothing is hosted (`make -f public.mk fetch-data` prints that).

##### In git
| Path (under `HT_Pert/`) | Files | Size | Content | Integrity |
|---|---|---|---|---|
| `data/HT_1d/thermal_expanse/thermal_d7/` | 34 | 60 KB | thermal C0..C7 (and r, g) at even Λ = 52..118, Expanse | `source_sha256` = solver fingerprint; copies in `analysis/extended/thermal_new.json` |
| `data/HT_1d/thermal_expanse/phi6_d5/` | 44 | 111 KB | φ⁶ gap, degree 5, Λ = 52..160 (D6 raw and vacuum_subtracted) | as above; `phi6_d5_new.json` |
| `data/HT_1d/thermal_expanse/phi6_d3/` | 33 | 69 KB | φ⁶ gap, degree 3, Λ = 136..832 without 608 | as above; `phi6_d3_new.json` |
| `data/HT_1d/thermal_expanse/campaign/plan.json` | 1 | 30 KB | last campaign plan (revision, validation, fingerprint, items, memory-rejected cutoffs) | fingerprint |
| `code/lri_hpc_Hamitonian/analysis_original/` | 35 | 2.1 MB | supplied Λ ≤ 50 thermal rows (`prior_c7/`, `C7_extension.json`), φ⁶ Λ ≤ 58/128 data, original fits | own `MANIFEST_SHA256.json` (34 files) |
| `code/lri_hpc_Hamitonian/analysis/` | 639 | 9.3 MB | analysis records and outputs (extended fits, window engines, identities, phase test, g²D tables) | see below |

Record format (`<task>_d<degree>_L<cutoff>.json`): `C`, `r`, `g` (degree + 1 coefficients; for φ⁶ `D6` and the tuning
under `raw` and `vacuum_subtracted`), `tuning_residual`, `second_order_shell_residual`, `low_order_residual`,
`basis_dimension`, `caps`, `threads`, `source_sha256`, `ranks` (RSS, timings), `seconds`. The records are not self-hashed
and contain no paths or machine names.

##### Record binding (classification for the public scrub)
- **Record-bound, ship byte-identical:** the 111 records and `plan.json` (bound to the solver by the fingerprint; the
  replay compares them with the copies in `analysis/extended`); the files of `analysis_original/` (own manifest);
  `reference/*.py` (`original_source_hashes.json`); the shared files that other packages bind by sha256
  (`dC_reconciled.json`/`.csv`, `refit_rc.json`, `freelead2.json`, `d5_all.json`, `d7_all.json`,
  `extended/{thermal_new,phi6_d5_new,phi6_d3_new,extended_summary,C7_extension}.json`,
  `extended/prior_c7/C7_completed_runs.json`, `eps5_window/B/{top5.jsonl, exact5_c{16,32,33,48,49,64,65}.json}`,
  `eps5_window/reconcile/exactL2/exact5_c{8,16,24,35,43,51}.json`; replay `a1.code`); `lri_hpc/*.py` (fingerprint).
- **Checksum lists, verbatim as received:** the root `MANIFEST_SHA256.json` (stale at this commit in exactly 5 files;
  `a1.code` expects that set and accepts files listed in `public/SCRUBBED.txt`), `BUILD_INFO.json`.
- **Not bound (may be scrubbed):** about 51 analysis scripts that name the analysis session's temporary directory and
  the project folder (`public/repoint.py` maps both the original paths and the scrubbed tokens `<TMP>`, `<PROJECT>`,
  `<HOME>`; a simulated scrub with the maintainer's rules was replayed: 26 PASS, 1 INFO); `cluster/expanse/`
  (`env.sh`, `validate.slurm`, `lane.slurm`, `submit_validate.sh`, `campaign.py`), `HPC_CAMPAIGN_REPORT.md` and
  `analysis/extended/fetch_results.sh`, which name the Expanse scratch path, the cluster user, the account and
  Expanse node names (allowed names; tokenizing them does not affect any target).
- No file of the ship set names a personal machine (scan of `tools/check_public.py` patterns plus a bare-word scan).

##### Not shipped
- `results/expanse/{checkpoints/, logs/, validation/, campaign/{claims/, lanes/, events/, SUBMITTED.jsonl,
  EXHAUSTED*.jsonl, submit.lock}}`: run-time plumbing, Slurm logs, test logs and the job/revision ledger (revision
  attribution in PROVENANCE).
- `analysis/eh_review/` except four files, `analysis/stress_test/`, the workflow journals and summaries, logs,
  `eps5_window/B/{prev,old}/`, `analysis/diagnosis.json`, the untracked `analysis/eh_addon_review/` (111 MB), the
  duplicate zip: see `entries_lri_hpc_Hamitonian.json` (`not_exported`).

### `lri_eh_hpc`

Folder: `code/lri_eh_hpc/`.

#### Data: lri_eh_hpc

Everything is in git; nothing is hosted.

| Path (under `HT_Pert/code/lri_eh_hpc/`) | Files | Content | Integrity |
|---|---|---|---|
| `benchmarks/validation_local.json`, `validation_local.tests.log`, `validation_local.smoke/` | 3 | supplier's validation receipt (sealed), its pytest log, the gated smoke output | `MANIFEST_SHA256.json`; receipt seal = `BUILD_INFO.json` |
| `benchmarks/results/*.json` (30), other `benchmarks/*.json`, `*.profile.txt`, `gated_smoke/` | 40 | supplier's timing and memory measurements (old and new backends) | `MANIFEST_SHA256.json` |
| `data/reference_corrections.json` | 1 | retained incoming numerical differences (test reference) | `MANIFEST_SHA256.json` |

The g²D tables made with this package ship in `code/lri_hpc_Hamitonian/analysis/eh_review/physics-impact/`
(`d5_all.json` sha256 bd5211de…, `d7_all.json` 52192e13…, `dc4_exact.json`), where other packages' records bind them.

**Record binding.** All 102 files in `MANIFEST_SHA256.json` are record-bound (the package's `verify_package.py` and
replay `a1.eh.code`); the receipt is self-hashed and bound by `BUILD_INFO.json`. The receipt and its tests log carry the
supplier container's paths (`/mnt/data/...`) and a container id, which are not personal machine names; they ship
byte-identical. No file names a personal machine (the only pattern hits are the word "canonical" in
`lri_eh/runtime.py` (canonical JSON) and the constant pi).

**Not shipped:** `__pycache__/`, `.DS_Store` (generated); the source zip (not in the project; hash in BUILD_INFO).

## d = 1: HT C8 and the complete-window coefficient flow

### `lri_c8_hpc`

Folder: `code/lri_c8_hpc/`.

#### Data: lri_c8_hpc

Everything is in git; nothing is hosted (`make -f public.mk fetch-data` says so).

##### In git: `data/HT_1d/c8/` (92 files, 1.2 MB, from `lri_ht_c8_symmetry/results/2026-10_symmetry`)
| Path | Files | Size | Content | Integrity |
|---|---|---|---|---|
| `c8_L52-92/accepted/{raw,vacuum_only}_L{52..92}_d8.json` | 42 | 428 KB | outputs: C, r, g [0..8], 4 energy series, shell/low-order/tuning residuals, residual components, configuration (source digest, stack, backend, threads), timings, peak RSS | self-hashed (`lri-c8-sha256-v1`); hashed by the journals |
| `c8_L52-92/journals/654fb90d19a573c1/lane_{0..41}.json` | 42 | 65 KB | machine-written Slurm lane records (by `scripts/run_lane.py` inside each array task, not agent workflow journals): one record per lane attempt with Slurm job and array ids, host, binding, exit, per item status, output sha256, C8, seconds, peak RSS | self-hashed; name the campaign id; read by replay row `c8.lanes` |
| `c8_L52-92/submissions.txt` | 1 | 183 B | array 569698, job name with the campaign id, lanes 0..41 | not bound |
| `campaigns/c8_L52-92.json` | 1 | 72 KB | frozen campaign: source digest, stack, threading layer, 42 items, 42 lanes, plans, the embedded receipt | self-hashed; its sha256 prefix 654fb90d19a573c1 is the campaign id, named by every journal |
| `exports/{raw,vacuum_only}_L52-92.json` | 2 | 426 KB | flat lists of the 21 outputs per prescription (`python -m lri_c8 export`) | sha256 in the sidecar |
| `exports/*.provenance.json` | 2 | 2.7 KB | sha256_export (cf3fec9e…, dd98c5a4…) and the common configuration | self-hashed |
| `validation/receipt_dd811aca899543c4.json` | 1 | 6 KB | validation job 569659: steps, tails, stack, node | self-hashed; embedded in the campaign |
| `extrapolation/data.json` | 1 | 28 KB | C0..C8 raw and vacuum_only for Λ = 2..92 (Λ ≤ 50 from the original runs in `code/lri_c8_hpc/inputs/`), thermal C0..C7 for Λ ≤ 118, reference values | sha256 ccc77dfa… recorded elsewhere (see below); rebuilt byte for byte by `public/build_data_json.py` |

##### Record binding and scrubbing
- **Byte-identical records.** Every JSON here is record-bound and ships byte-identical (D1): self-hashed, hashed by
  another record, or recorded by sha256 elsewhere.
  - The receipt, the campaign and the 42 journals carry the symmetry user name, scratch paths
    (`/mnt/beegfs/<USER>/lri_c8/...`, `/home/<USER>/lri_c8_hpc/...`) and symmetry compute-node names (10 nodes of defq).
    They stay as recorded.
  - **The 42 lane journals** are machine-written, self-hashed Slurm records of the production array 569698, not agent
    workflow journals, review logs or transcripts. They are record-bound (D1): each is self-hashed, names the campaign
    id 654fb90d19a573c1 (the campaign's sha256 prefix) and holds the sha256 of the output it accepted; replay row
    `c8.lanes` needs them. They ship byte-identical, so the maintainer's allowlist must accept the symmetry user name and
    node names in them (as in the campaign and the receipt).
  - The outputs, exports, sidecars and data.json carry no machine or user names.
  - No personal machine names anywhere.
- **`submissions.txt`** is not bound and contains no private string.
- **data.json.**
  - Its sha256 ccc77dfa1e7d3955f3b8f22b2ea3b99ba649976605c5bac6bae39b5f2ad92faa is recorded under its original
    absolute path in the `sources` of the S1B refit outputs (`code/lri_1d_dconn_refit`).
  - It is also recorded in `inputs/MANIFEST.txt` of `code/lri_1d_c4_exact` and `code/lri_1d_c5_exact`, which vendor
    a copy as `inputs/ht_data.json`.
  - It ships once, here; consumers map the path at verify time.
- **Code-side records** (`code/lri_c8_hpc`).
  - `MANIFEST_SHA256.json` lists 164 files and ships verbatim. Files the placeholder scrub changes are listed in
    `public/SCRUBBED.txt`. The published manifest is never rewritten; a production rerun rehashes the manifest of its
    own working copy with `public/rehash_manifest.py` (REPRODUCE, section 5, step 0).
  - The expected scrub is six files: `README.md`, `docs/SYMMETRY.md`, `slurm/defq_lane.slurm`,
    `slurm/defq_validate.slurm`, `slurm/submit_defq.sh` (`/mnt/beegfs/<user>` paths, a node range) and
    `reference/HPC_CAMPAIGN_REPORT.md` (Expanse account and node names).
  - The tests and the replay were run on a scrubbed copy; see `TESTS_lri_c8_hpc.md`.
  - Nothing under `src/` may be scrubbed: its digest binds every record.
  - `inputs/*.json` and `benchmarks/REGRESSION_GRID.json` are read by the tests and the replay and ship verbatim.
    They are clean.

##### Cross-package input
The `c8.datajson` row reads three thermal records shipped by `code/lri_hpc_Hamitonian` (git_ref c55d134):
- `analysis/extended/thermal_new.json` (abd72c91…);
- `analysis/extended/C7_extension.json` (d4f50bd0…);
- `analysis/extended/prior_c7/C7_completed_runs.json` (f8a2b308…).

When they are absent, the row checks only the raw and vacuum_only tables and reports SKIP.

##### Not shipped
- `c8_L52-92/accepted/checkpoints/` (42 self-hashed scalar checkpoints, 301 KB): only `--resume` reads them.
- Claims, lock and owner files, and the empty `owners/` and `claims/` folders.
- Lane logs `logs/*.out`: the journals carry the same facts.
- The validation job log and its step logs: the receipt holds the tails, and `make test` / `make replay-full` recompute
  them.
- **`extrapolation/` except `data.json`** (67.8 MB, archive only): the four-lens extrapolation of 2026-10-04, superseded.
  Its scripts hard-code paths that no longer exist, and one lens ran on a personal desktop.

### `lri_d1_full_coefficient_flow`

Folder: `code/lri_d1_full_coefficient_flow/`.

#### Data: lri_d1_full_coefficient_flow (S10) and data/HT_1d/s10_production

##### In git
- **`data/HT_1d/s10_production/`** (15 files, 420 KB): the S10 production records of 2026-10-08.
  - `dconn_L<L>_d8.json`, L = 46, 48, ..., 72 (22.6–33.9 KB each): complete D^conn coefficients C0..C8 (degree 8) with
    the solver's diagnostics and a `provenance` block (host, Slurm job and array ids, Python/numpy/scipy versions,
    long-double mantissa bits, `code_sha256`, `max_states`).
    - Byte-identical to the cluster output (14 sha256 compared when they were copied on 2026-10-08).
    - **Code binding:** every record's `provenance.code_sha256` is 854fc763…, the sha256 of the shipped
      `code/ragged_quotient.py` (replay row s10.code).
    - No shipped file records the records' own sha256. Their `provenance.host` names symmetry compute nodes; a scrub
      of that field does not affect any check (the replay reads `C`, `cutoff`, `scheme`, `degree`, `basis_dimension`,
      `seconds`, `maxrss_kib` and the other provenance fields).
  - `dconn_minus_raw_L46_72.csv` (869 B, sha256 3105e037…): dC_k = C_k(record) − raw_k(data.json of the C8 campaign),
    k = 6, 7, 8, one row per L.
    - **Record-bound:** its sha256 is recorded in every hi = 72 delta-stage output of `code/lri_1d_dconn_refit`
      (`extra_dconn_csv.sha256`).
    - No script had been kept; `public/make_dconn_minus_raw.py` regenerates it byte for byte (replay row s10.csv).
- **The package itself** (`code/lri_d1_full_coefficient_flow/`, 86 files, 1.31 MB, commit fec60a2):
  - `results/new_coefficients/`: the archive records at L = 2..44 (raw and D^conn), the reference of the production
    gate. They are pinned by sha256 in `code/check_validation.py` and listed in `MANIFEST.sha256`.
  - `results/whole_model_coefficients.csv` (sha256 960cfb61…): also recorded by the refit package's delta outputs
    (`sources`).
  - `inputs/`, `vendor/`: the supplied earlier archives (ordinary and exact-Fraction references, prior data), pinned
    by `provenance/ENVIRONMENT.json` and `MANIFEST.sha256`.
  - `MANIFEST.sha256` lists the other 85 files. Four of them carry the cluster user name in output paths
    (`SYMMETRY_EXTENSION.md`, `slurm/production.slurm`, `slurm/validate.slurm`, `slurm/submit.sh`). If the maintainer
    scrubs them, they must go into `public/SCRUBBED.txt`; `public/verify_manifest_public.py` and the replay accept
    them then. `code/ragged_quotient.py` is record-bound and must stay byte-identical.

##### Read from other packages (shipped there, byte-identical)
- `data/HT_1d/c8/extrapolation/data.json` (sha256 ccc77dfa…, package lri_c8_hpc): the raw HT coefficients subtracted in
  the dC table.
- `code/lri_hpc_Hamitonian/analysis/eps5_window/reconcile/dC_reconciled.json` (sha256 0250b341…): the exact ε⁴ and ε⁵
  window shifts compared in row s10.match.
The replay reports SKIP for a row whose cross-folder input is absent.

##### Not shipped
- The git history (`.git`, five commits, summarized in PROVENANCE).
- On the cluster only: the Slurm logs and the validation job's own records (job 571525, 793 KB). Its result (PASS,
  maximum deviation 5.3e-15 in C, 5.1e-13 in the vacuum grid) is cited in PROVENANCE; `make -f public.mk smoke` repeats
  the same comparison.
- Nothing of this package is hosted (`make -f public.mk fetch-data` says so).

### `lri_1d_dconn_refit`

Folder: `code/lri_1d_dconn_refit/`.

#### Data: lri_1d_dconn_refit

##### In git (`code/lri_1d_dconn_refit/`, 20.2 MB raw, 280 files with public/)
- **`delta/` (1.8 MB).** Code, the lens adapters and the outputs.
  - `out/delta_v1_hi72_corrected.json` (sha256 3694e083…): the corrected C0..C8 tables with the published pointwise
    median beyond Λ = 72.
  - `out/delta_v1_hi72_variants.json` (ff2e6804…) and `out/variants_full_hi72.json` (23227701…): every kept fit.
  - The four derived tables `out/delta_v1_hi72_{medoid,floormean,floormedoid,floormean_s46}_corrected.json`.
  - `out/delta_v1_hi72_smooth.json`, the dC and smooth tables (`*.csv`), and `out/validation_hi72/` (seq, hold,
    noise6..8).
  - `archived_out_delta_v1/`: the run-1 outputs (hi = 44 rule), byte-identical to run 1. They hold the blind forecast
    `frozen_forecast_L46_72.json` (created 2026-10-08 08:35, before the production data; self-hashed by its `.sha256`,
    72e7f0a9…), `delta_v1_corrected.json` (fc43d4aa…), `delta_v1_variants.json` (f581699a…) and the dC table.
- **`joint/` (3.7 MB).** Code, the symmetry sharedq scripts, `out/r72/` (summaries `summary{,_dconn_w,_dconn_s46}.json`
  and `.txt`, `c8_summary*.json`, `low_summary*.json`, `r72_summary.json`, `analyze_*.txt`, `checks.*`, `noise.*`,
  `propagate_*.txt`), `out/noise.json`, and the run-1 summary `archived_run1/summary.json`.
- **`model-independent/` (13 MB).** Code (with the run lists), and `out/`: `headline.json`, `final72.json`,
  `final_summary.json`, `compare72.json`, `members_subset.json` with their `.txt`, `mem1/members_analysis.json`, and
  per run (`run2_fmedoid`, `run_s46`, `run_fmean`, `run_mimedoid`, `run0_repro`, `run1`, `run3_rawc8`, 27 quantile and
  floor reruns `run2_k{6,7,8}_*`) `analysis*.json/.txt` and `sel_*.json`. Logs and the 50-digit grids are not shipped.
- **`verify/` (1.6 MB).** The verifier's code and small outputs (`mycont_dC678.json`, `tabs.npz`, `mitabs.npz`,
  `tab_old.npy`, `mi_noise_mc*.json`).
- **`run1/joint/out/variants_full.json`** (257 KB, sha256 0978cdcd…): the run-1 table of every kept delta-v1 curve on
  every even L ≤ 118. It is the "dconn_old" dataset of the joint scans and an input of `smooth_central.py`.

##### Hash bindings (all verified by replay row rf.inputs; 46 bindings)
- The five `delta_v1_hi72*_corrected.json` record the sha256 of their inputs: `data.json` (ccc77dfa…),
  `dC_reconciled.json` (0250b341…), `whole_model_coefficients.csv` (960cfb61…), `d5_all.json` (bd5211de…),
  `d7_all.json` (52192e13…) and `dconn_minus_raw_L46_72.csv` (3105e037…). The run-1 `delta_v1_corrected.json` records
  the first five.
- The four derived tables record `delta_v1_hi72_corrected.json` (`derived_from`, 3694e083…).
- `delta_v1_hi72_smooth.json` records six tables: 3694e083, ff2e6804, 23227701 (hi = 72) and fc43d4aa, f581699a,
  0978cdcd (run 1).
- Off-tree only: the raw joint scan records and their logs record 3694e083 and 23227701, and the model-independent
  staging list (a log, not shipped) records the tables it read (corrected, floormean, floormean_s46, variants, run-1
  tables, data.json). No shipped file records the sha256 of the four derived tables or of `delta_v1_hi72_smooth.json`.
- **Record-bound files with personal paths (allowlist; ship byte-identical).** Only two files:
  - `delta/out/delta_v1_hi72_corrected.json` (sha256 3694e083…, recorded by the four derived tables and by
    `delta_v1_hi72_smooth.json`);
  - `delta/archived_out_delta_v1/delta_v1_corrected.json` (fc43d4aa…, recorded by `delta_v1_hi72_smooth.json`).
  Both carry absolute paths of the authors' working folder (`<PROJECT>/...`, written out in the original
  files) as the keys of `sources` and, for the first, in `extra_dconn_csv.path`. They hold no session scratch path
  and no session UUID.
- **Scrubbable (not bound): the five derived delta tables** `delta/out/delta_v1_hi72_{medoid,floormean,floormedoid,
  floormean_s46}_corrected.json` and `delta/out/delta_v1_hi72_smooth.json`. They carry the authors' working-folder
  paths and the stage's session scratch path (`/private/tmp/...` with a session UUID) in `sources`, `derived_from.path`,
  `extra_dconn_csv.path` and the smooth file's `inputs`/`files`/`sha256` keys. No shipped file records their sha256.
  The public scripts read these files by key basename and by the recorded sha256 values, which a scrub of the path
  strings leaves unchanged; `test` (all rebuilt tables bitwise) and `replay` pass on a copy with these five scrubbed
  (`TESTS_lri_1d_dconn_refit.md`).
- **Not bound** (scrubbable) as well:
  - the stage scripts, which name their inputs by absolute paths (`public/repoint.py` re-points them by variable name
    at run time);
  - the sbatch/sh files (cluster workspace and venv paths with the cluster user name);
  - the model-independent `analysis*.json`/`sel_*.json` (`meta` paths with the cluster user name; the replay reads
    only `headline.json` and `final72.json`).

##### Read from other packages (shipped there)
`data/HT_1d/c8/extrapolation/data.json`; `code/lri_hpc_Hamitonian/analysis/eps5_window/reconcile/{dC_reconciled.json,
dC_reconciled.csv, refit_rc.json}`, `.../eps5_window/challenge-theory/freelead2.json`,
`.../eh_review/physics-impact/{d5_all.json, d7_all.json}`; `code/lri_d1_full_coefficient_flow/results/
whole_model_coefficients.csv`; `data/HT_1d/s10_production/` (the dC table and records). Absent inputs make `test` fail
early and give SKIP rows in `replay`.

##### Not in git: hosted in the Zenodo data record (DOI 10.5281/zenodo.23466766; `make -f public.mk fetch-data`)
`fetch-data` (`public/fetch_hosted.py`, standard library only) downloads these files from the record, checks size and
sha256 against `public/hosted.json` (for the archive, every member too), and puts them in place. It skips files already
in place and does not overwrite a file with other content. `DATA_URL` defaults to the record's file URL,
`https://zenodo.org/records/23466766/files`. `test` and `replay` do not need these files.

| record file | size | sha256 | goes to |
|---|---|---|---|
| `HT_Pert__lri_1d_dconn_refit__scan_o8.jsonl.gz` | 44.7 MB | 53be3ed6… | `joint/out/r72/scan_o8.jsonl.gz` |
| `HT_Pert__lri_1d_dconn_refit__scan_o7.jsonl.gz` | 22.7 MB | e60aa95c… | `joint/out/r72/scan_o7.jsonl.gz` |
| `HT_Pert__lri_1d_dconn_refit__scan_o8_w.jsonl.gz` | 20.9 MB | 3db7f62a… | `joint/out/r72/scan_o8_w.jsonl.gz` |
| `HT_Pert__lri_1d_dconn_refit__scan_o7_w.jsonl.gz` | 9.3 MB | efce5f73… | `joint/out/r72/scan_o7_w.jsonl.gz` |
| `HT_Pert__lri_1d_dconn_refit__model-independent_out.tar.gz` | 318.9 MB (1.77 GB unpacked) | 5fe51314… | 71 files under `model-independent/out/`: `<run>/grid.json` (34 grids, about 50 MB each), `<run>/accel.json` (34), `mem1/{members_prop.npz, members_full.json, members_prop_index.json}` |

These are the raw records behind the summaries: 395,280 joint fits and the 50-digit model-independent grids.
- **Scans.** The four scan files are the bytes whose sha256 this package has given since 2026-10-14; the cluster copies
  and the authors' archive copy agree.
- **Model-independent archive.** It holds exactly the files that `model-independent/code/fetch72.sh` leaves on the
  cluster (`grid.json`, `*.npz`, `members_full.json`, `members_prop_index.json`, `accel.json`), so git plus the archive
  is the complete `model-independent/out/`. No checksum binds them. The scratch path in the `meta` of the 68 JSON
  members is scrubbed to `<SCRATCH>` as in the repository; the `mem1/` files are byte-identical to the cluster
  outputs. Deterministic tar (sorted list, owner 0, mtime 2026-10-18), packed on the symmetry cluster.
- **Regeneration.** The full refit regenerates all of them (REPRODUCE step 3); the arb and mpmath intercepts are
  bit-reproducible.

##### Not shipped
- The workflow journal (raw subagent results; summarized in REVIEWS and PROVENANCE).
- The stage logs (Slurm and stage logs, the model-independent code-hash lists).
- The delta exploratory diagnostics.
- The run-1 validation records and figure.
- The run-1 copies of scripts.
- The superseded first post-processing pass (`joint/out/r72_pass1`), the smoke scan, the probe runs.
- The verifier's caches (`*.pkl`, 17 MB).
- The joint propagation tables (`propagation*.json`, 3.9 MB; summarized in `propagate_*.txt` and `summary*.json`).
- The rest of run 1 (`step1_dconn_refit`, 108 MB).

### `lri_d1_fullblock_tail_response`

Folder: `code/lri_d1_fullblock_tail_response/`.

#### Data: lri_d1_fullblock_tail_response

Nothing is hosted, and the package has no `data/` or `results/` entry of its own in HT_Pert. Every record that test
and replay read is inside `code/lri_d1_fullblock_tail_response/`, in git: 109 files, 850,370 bytes, about 0.32 MB
packed. The largest file is `results/phase_response_shells.json` (134,519 bytes).

##### Records
**Binding.** `MANIFEST.sha256` binds every file of the package except itself (108 entries), so all of them are
record-bound and ship byte-identical.
- If the scrub has to change one, list it in `public/SCRUBBED.txt`. The public verifier and the replay then report it
  as scrubbed instead of failing.
- The bare-word machine-name scan flags one line, `docs/METHOD.md:103`. The word there is the ordinary English
  adjective in "its … energy/metric fold", not a machine name. Allowlist it rather than scrub it.

The records the targets read:

| Records | Content | Read by |
|---|---|---|
| `results/{dconn,raw}_full_L*_d8.json` (9 + 4) | Full-J susceptibility S_J,0..8 at low cutoff μ | replay fb.onset |
| `results/exact_full_L{2,4}_d8.json` | The same as exact rationals | replay fb.onset |
| `results/dconn_phi6_L8_d8.json`, `results/partial_assembly_example.json` | S_Φ6 and the partial two-vertex assembly (μ = 8, Λ = 1024) | replay fb.amplitude |
| `results/phase_overlap_asymptotics.json`, `phase_overlap_topologies.csv`, `phase_finite_part_N512_O6.json`, `phase_response_shells.json` | Eq. (6) coefficients, the 38 topologies, the finite part C, the shells | replay fb.B (via `code/mixing_asymptotics.py`) |
| `results/general_bath_annulus.json`, `annulus_validation.json` | The 36 annulus comparisons | replay fb.annulus |
| `docs/METHOD.md`, `REPORT.md` | Equation text and the annulus table | replay fb.power, fb.B, fb.annulus |

**Run-time products.** The package's scripts rewrite their outputs in `results/`:
- `tests/run_all.py` writes `test_run.json`;
- `tests/check_annulus.py`, `code/mixing_asymptotics.py`, `tests/validate.py` and `tests/check_finite_response.py`
  write their JSON and CSV files.

public.mk therefore runs them on a copy under `.work/`; `test` checks their exit codes, and `replay` compares the fresh outputs of check_annulus.py and mixing_asymptotics.py with the shipped ones (validate.py makes its own comparisons). Nothing is
written into the shipped tree.

##### Not shipped
- **The stray `code/__pycache__/phase_response_shell.cpython-310.pyc`.** It is byte code from a local run of the
  extraction, and it is not in the zip.
- **The rest of `lri_1d_tails_review/`:**
  - the tails bundle `lri_d1_remaining_overlap` and its upstream `lri_d1_scale_matching`, outside this folder. Nothing
    from them is used in the paper. The original zip, sha256 c4b830a3…, is the archive.
  - the raw review folder `review/`, summarised in `REVIEWS.md`. It holds lens scripts, outputs, Slurm logs and a
    workflow journal, and it names a personal machine.

## d = 2: coefficients C2..C8 and the independent check

### `lri_d2_coeff_hpc`

Folder: `code/lri_d2_coeff_hpc/`.

#### DATA for lri_d2_coeff_hpc

See `HT_Pert/data/HT_2d/DATA.md`. In short: `HT_Pert/data/HT_2d/prod/` holds the 41 production records (lri-coeff-v1
envelopes; `sha256` = sha256 of the canonical JSON of `payload`, verified by `make -f public.mk replay`), the campaign
manifests, the collected tables `coefficients.csv` and the two validation receipts. They ship byte-identical (record
bound); the cluster paths, node names and the Expanse user inside them are part of the hashed payloads and are history,
not paths to use. `prod1_symmetry/coefficients.csv` (sha256 d86743c1…) and
`reference/lri_d2_perturbative_C8/results/coefficients_C0_C8.csv` (sha256 ee72158e…) are cited by
`HT/data/HT_2d/pert_crosscheck` and must not be modified. Nothing is hosted.

### `lri_2d_coeff_independent_check`

Folder: `code/lri_2d_coeff_independent_check/`.

#### DATA for lri_2d_coeff_independent_check

See `HT_Pert/data/HT_2d/DATA.md`. In short: the records this package's replay reads are inside the code snapshot
(its results are code outputs in the folders that wrote them, so the shipped scripts run on them with their own
relative paths): exact-rational JSON (rs_exact, cauchy, zeromode_exact, complete_exact, ce_wc, results/tag), float64
npz (c4_exact/results, residual_log/results, residual_log/large_L/results) and csv/txt fit inputs and outputs.
None is self-hashed; `public/SNAPSHOT.sha256` lists them all with their sha256 as exported. Nothing is hosted. No pickle
is shipped. The npz files hold only numeric arrays (numpy.load with the default allow_pickle=False reads them).

## d = 3: exact C2..C5(L) sums and the coefficients C2..C8

### `lri_3d_c4_exact`

Folder: `code/lri_3d_c4_exact/`.

#### Data of lri_3d_c4_exact

Everything `make -f public.mk replay` and `make -f public.mk test` read is in git; nothing is hosted.

- **The package's own results (`results/`, about 3 MB, in the package's git history):** the production outputs,
  written by the package's drivers (`PROVENANCE.md` lists the job of each):
  - `c4_L200.npz`, `c4_L300.npz`, `c4_L600.npz`: C2..C4 raw and consistent, r, g, energies at every even L;
  - `windows_L8000.npz`, `offdiag_L400.npz`, `offdiag_L8000.npz`, `dchi_L120/600/1000.npz`: the window shifts;
  - `c5_L12.npz`, `c5_L20.npz`: C2..C5 in every scheme;
  - `c5raw_all_L20/L40.npz`, `c5raw_sp_L20.npz`: raw C5;
  - `dC5_L200/L600.npz`: the scheme shifts at eps^5;
  - `eps5/legw_L400.npz`: the leg response S(L);
  - `eps5/C5_schemes.npz`: C5 per scheme at L <= 40;
  - `brute/`, `brute_zm_L6.json`, `tag/`, `eps5/desc_L*.json`: brute force and descendant checks;
  - `regress/`: the regression logs of the final engine.
  None of these files is bound by a checksum. Several were written on the symmetry cluster; the text logs in
  `regress/` name its nodes and paths and are scrubbed for publication.
- **Read from the sibling package:** `../lri_3d_hpc/results/reference_coefficients_L14.json` (the original code's
  results, L <= 14) and `../lri_3d_hpc/reference/` (its operators, for the brute force).
- **Read from the records:** `../../data/HT_3d/pert3d/results` (the production campaign, L = 16..20).
- **The fit summaries** `fits/*.txt` are outputs of the package's scripts on `results/`; the replay regenerates them.

Not shipped: the job-log tails `results/eps5/joblogs/` (operational; the jobs are listed in `PROVENANCE.md`), the
memory and timing probes (`profile4.py`, `eps5/prof5.py`, `eps5/prof_heavy.py`, `eps5/memprobe*.py`,
`results/regress/memprobe_L12_20.txt`), and the engine's task caches (rebuildable, not read).

Scrubbed for publication (cluster paths, user and node names replaced by placeholders; no checksum list binds them, and
no target reads them): `README.md`, `results/regress/log_574029.txt`, `results/regress/log_574030.txt`,
`results/regress/log_574365_boxes_L40.txt`, `results/regress/L40_boxes_before_restart.txt`. Every other shipped file
is byte-identical to git commit `d5afa4f`.

### `lri_3d_hpc`

Folder: `code/lri_3d_hpc/`.

#### Data of lri_3d_hpc

Everything `make -f public.mk replay` and `make -f public.mk test` read is in git; nothing is hosted.

- Records of the production campaign: `HT_Pert/data/HT_3d/pert3d/` (194 files, 1.5 MB), described in
  `HT_Pert/data/HT_3d/DATA.md` with what is byte-identical and what was scrubbed.
- The table `HT_Pert/results/HT_3d/SUMMARY.md` (C2..C8 at L = 16, 18, 20).
- Inside the package: the original code's reference results `results/reference_coefficients_L14.json` (L = 0..14,
  bound by sha256 in every gate record) and the small vertex store `fixtures/vertices_L4/` (smoke test).

Not hosted: the production vertex stores (L16 2.6 GiB, L18 22 GiB, L20 177 GiB) and the L20 intermediate pipeline
files (363 GiB). A production rerun rebuilds them (`public/REPRODUCE.md`).
