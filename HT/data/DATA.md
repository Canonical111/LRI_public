# HT data

What is in git and what is hosted (hosting planned on Zenodo, no record yet; `fetch-data` targets print where the files go and their sha256).

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT/`. The values themselves are in `../note/README.md` and the note.

- d = 1: dressed phi^4 Hamiltonian truncation: `lri_dressed_phi4_hpc`, `lri_dressed_phi4_hpc_analysis`, `lri_dressed_phi4_independent_check`
- d = 2: dressed-window Hamiltonian truncation: `lri_2d_window_hpc`, `lri_2d_window_indep`
- d = 3: dressed-window Hamiltonian truncation: `lri_3d_window_hpc`, `lri_3d_window_indep`

## d = 1: dressed phi^4 Hamiltonian truncation

### `lri_dressed_phi4_hpc`

Folder: `code/lri_dressed_phi4_hpc/`.

#### Data: d = 1 finite-coupling HT (HT/data/HT_1d)

##### (a) In git: everything needed by `test`, `replay` and `smoke`

| Path | Files | Size (raw) | Content | Integrity |
|---|---|---|---|---|
| `dens_v1/campaigns/dens16_{lo,mid,hi8,hi16}/` | 195 results + 4 manifests | 46 MB | Production results: 16 density states per parity, consistent window, 13 Ds × even N = 12..40 | each JSON self-hashed (`sha256` = sha256 of its canonical JSON without that field; `lri_dressed.io.digest`) |
| `dens_v1/campaigns/dens24_ctl/` | 6 results + manifest | 1.5 MB | 24-state controls at N = 36, 40 | self-hashed |
| `dens_v1/campaigns/{make_dens_v1.sh, dump_dens_v1.py}` | 2 | 4 KB | Manifest builder; row dump (its cluster path may carry a placeholder) | not hash-bound |
| `dens_v1/bases/dens_v1/` | 13 artifacts + index.json + training_request.json | 3.2 MB | Keep-24 density-basis artifacts, trained at L = 24 against nz 48, osc 384 | self-hashed; every result names its artifact by sha256 |
| `dens_v1/seeds/dens_v1_all/` | 185 | 0.9 MB | Starting points of the production runs (copies of prod1–7 window results) | self-hashed |
| `dens_v1/validation/570965/receipt.json` | 1 | 5 KB | Release validation of the production install (6 stages passed) | self-hashed; binds source and release fingerprints |
| `prod_window/campaigns/prod{1,2,4,5,6,7}/` | 680 results + 6 manifests | 3.1 MB | First campaign (code 4dfd833): raw, consistent and literal, nz 24..56. Used for the identity inputs, the N = 32 references, the blind-solver references and `collected.json` | self-hashed |

- **Totals:** 1106 JSON envelopes, about 58 MB raw. The d = 1 HT part of the git pack (code, data, results) is
  about 28 MB in a test repository. Each dens result embeds the ~260 KB record of its basis, which delta-compresses
  well.
- **Verification.** `make -C code/lri_dressed_phi4_hpc_analysis -f public.mk replay` verifies every envelope (check
  R1).
- **Paths inside records.** The records keep the cluster paths, host names and user name of the original runs
  (`payload.execution`, `local_basis_path`, `seed_dir`, and the receipt's `baseline` and `host`), because these sit
  inside the hashed content. They describe where the production ran and are not paths to use.

##### (b) Hosted or archive only

None. Nothing for d = 1 is hosted.

Not shipped at all:

- the Newton checkpoints, claim and lease files, and launcher and item logs of the campaigns;
- the basis-training checkpoints (`*.checkpoint.json`);
- the exploratory basis test and the calibration, probe and drill folders.

None of them is needed by a target (`export_entries.json`, `not_exported`).

### `lri_dressed_phi4_hpc_analysis`

Folder: `code/lri_dressed_phi4_hpc_analysis/`.

#### Data: lri_dressed_phi4_hpc_analysis

All inputs are in git: the folder itself (116 files, about 2 MB) and `HT/data/HT_1d`
(`../lri_dressed_phi4_hpc/DATA_lri_dressed_phi4_hpc.md`). Nothing is hosted.

- **Paths in rows.** The `path` fields of `dens_v1_rows.json` and `collected.json` name the records' cluster paths.
  These files are not hash-bound, and the replay ignores those fields.
- **Identity records.** The 104 records in `identities/` have no self-hash. Each binds its input record by
  `record_sha256`, which the replay checks (I0).

### `lri_dressed_phi4_independent_check`

Folder: `code/lri_dressed_phi4_independent_check/`.

#### Data: lri_dressed_phi4_independent_check

All data is in git, inside the package: `results/raw_runs/` (1.5 MB, the per-task outputs) and
`results/indep_results.json` (0.6 MB, merged). The production reference comes from `HT/data/HT_1d`. Nothing is
hosted. The run logs (`results/logs/`, 0.5 MB) are not shipped.

These files are not hash-bound. Host names may be replaced by `<NODE>` consistently in both files; the replay ignores
`host`.

## d = 2: dressed-window Hamiltonian truncation

### `lri_2d_window_hpc`

Folder: `code/lri_2d_window_hpc/`.

#### DATA for lri_2d_window_hpc

See `HT/data/HT_2d/DATA.md` (generated from the export; copy below).

#### HT_2d data and results: what is where (d = 2 finite-coupling HT)

Everything needed by `test`, `smoke` and `replay` of `HT/code/lri_2d_window_hpc` and `HT/code/lri_2d_window_indep` is in
git; nothing is hosted (`make -f public.mk fetch-data` says so). Per-file SHA-256: `SHA256SUMS_HT_2d.txt` (paths from the
repository root; the last column below is the SHA-256 of that folder's lines).

| Folder | Contents | Files | Size | Largest | Used by | SHA-256 of list |
|---|---|---|---|---|---|---|
| `HT/data/HT_2d/prod1` | prod1 records (348 self-hashed JSON), frozen spec, inputs (bases, seeds) | 375 | 38.36 MiB | 0.18 MiB | replay, smoke, rerun | `e48edb4ee9f6d785…` |
| `HT/data/HT_2d/pert_crosscheck` | consistent-scheme C0..C8(N), N = 8..24 (extract) | 2 | 0.00 MiB | 0.00 MiB | replay (d2.pert_consistent) | `995137c96cda2809…` |
| `HT/results/HT_2d/prod1` | collected tables (collect.py) and largest_N.csv | 6 | 0.55 MiB | 0.23 MiB | replay | `62b12c579dd45f6b…` |
| `HT/results/HT_2d/valley_N24` | 12 valley-scan outputs | 13 | 0.02 MiB | 0.00 MiB | replay (d2.valley.*, d2.no_root, d2.fold) | `a6ca8dd2bd64ab25…` |
| `HT/results/HT_2d/independent_check` | 155 independent-solver outputs | 156 | 0.77 MiB | 0.01 MiB | replay (i2.*), smoke | `683f1653a252b95d…` |

Binding: the prod1 records carry `record_sha256` (SHA-256 of their canonical JSON without that key) and bind the code
(`configuration.source_sha256`, = `source_hash()` of `HT/code/lri_2d_window_hpc` at 889a968), their basis and their
seed. They ship byte-identical, with the original cluster paths inside: these are history, not paths to use. The
independent-check outputs embed the `record_sha256` of the records they were compared with. The valley outputs and the
independent-check outputs are not self-hashed; their machine identifiers are replaced by placeholders.

Archive only (not published): the Slurm logs, Newton checkpoints and claims of prod1, the stalled N = 24 restarts at
Δσ = 0.125, 0.126, the drill campaigns, and the review transcripts.

### `lri_2d_window_indep`

Folder: `code/lri_2d_window_indep/`.

#### DATA for lri_2d_window_indep

See `HT/data/HT_2d/DATA.md` (generated from the export; copy below).

#### HT_2d data and results: what is where (d = 2 finite-coupling HT)

Everything needed by `test`, `smoke` and `replay` of `HT/code/lri_2d_window_hpc` and `HT/code/lri_2d_window_indep` is in
git; nothing is hosted (`make -f public.mk fetch-data` says so). Per-file SHA-256: `SHA256SUMS_HT_2d.txt` (paths from the
repository root; the last column below is the SHA-256 of that folder's lines).

| Folder | Contents | Files | Size | Largest | Used by | SHA-256 of list |
|---|---|---|---|---|---|---|
| `HT/data/HT_2d/prod1` | prod1 records (348 self-hashed JSON), frozen spec, inputs (bases, seeds) | 375 | 38.36 MiB | 0.18 MiB | replay, smoke, rerun | `e48edb4ee9f6d785…` |
| `HT/data/HT_2d/pert_crosscheck` | consistent-scheme C0..C8(N), N = 8..24 (extract) | 2 | 0.00 MiB | 0.00 MiB | replay (d2.pert_consistent) | `995137c96cda2809…` |
| `HT/results/HT_2d/prod1` | collected tables (collect.py) and largest_N.csv | 6 | 0.55 MiB | 0.23 MiB | replay | `62b12c579dd45f6b…` |
| `HT/results/HT_2d/valley_N24` | 12 valley-scan outputs | 13 | 0.02 MiB | 0.00 MiB | replay (d2.valley.*, d2.no_root, d2.fold) | `a6ca8dd2bd64ab25…` |
| `HT/results/HT_2d/independent_check` | 155 independent-solver outputs | 156 | 0.77 MiB | 0.01 MiB | replay (i2.*), smoke | `683f1653a252b95d…` |

Binding: the prod1 records carry `record_sha256` (SHA-256 of their canonical JSON without that key) and bind the code
(`configuration.source_sha256`, = `source_hash()` of `HT/code/lri_2d_window_hpc` at 889a968), their basis and their
seed. They ship byte-identical, with the original cluster paths inside: these are history, not paths to use. The
independent-check outputs embed the `record_sha256` of the records they were compared with. The valley outputs and the
independent-check outputs are not self-hashed; their machine identifiers are replaced by placeholders.

Archive only (not published): the Slurm logs, Newton checkpoints and claims of prod1, the stalled N = 24 restarts at
Δσ = 0.125, 0.126, the drill campaigns, and the review transcripts.

## d = 3: dressed-window Hamiltonian truncation

### `lri_3d_window_hpc`

Folder: `code/lri_3d_window_hpc/`.

#### DATA: lri_3d_window_hpc (d = 3 production records)

This is the text of `HT/data/HT_3d/DATA.md` (shipped via the overlay `patches/data/HT_3d/`). The per-file sha256 list is `HT/data/HT_3d/MANIFEST.sha256`.


Everything the d = 3 targets read is in git; nothing is hosted.

| path | files | size | role |
|---|---|---|---|
| `campaigns/grid18/` | manifest.json; per Ds (14): teacher_L6, window_L8 … window_L18, raw_L10 | 11.3 MB (113 files) | N = 6 → 18 ladders, 0.52 ≤ Ds ≤ 0.7499 |
| `campaigns/grid18sri/` | the same at Ds = 0.518149 | 0.80 MB (9 files) | |
| `campaigns/l20x06/` | manifest.json, window_L20 at Ds = 0.6 (with J = 1 diagnostics) | 0.13 MB (2 files) | |
| `campaigns/grid20/` | manifest.json, window_L20 at 13 Ds (scalar only) | 1.61 MB (14 files) | |
| `campaigns/grid20sri/` | manifest.json, window_L20 at Ds = 0.518149 | 0.13 MB (2 files) | |
| `MANIFEST.sha256` | sha256 of every file above (140 lines) | 13.9 MB in all; largest file 0.13 MB | checked by `make replay` (REC-MANIFEST) |

- **Byte-identical.** The records ship byte-identical to the production files. Each record holds `record_sha256`, the
  sha256 of its canonical JSON (`ht3d.hpc.digest`), computed over content that includes the production paths of its
  continuation inputs and static cache. It names those inputs by sha256 (`configuration.seed_sha256`, `basis_sha256`).
  These paths are history (`<SCRATCH>/ht3d/campaigns/...`), not paths to use: `make replay` and `make smoke` map them to
  this folder.
- **Manifests.** Each campaign's `manifest.json` is its frozen plan: the release and receipt, the lanes, and the exact
  argv of every step. It has its own sha256 over its content.
- **Not shipped:**
  - checkpoints, claims and the `window_L10_k12` side step;
  - logs and journals;
  - the calibration, regression and drill campaigns of the Expanse port.
  See `HT/d3` export notes and `code/lri_3d_window_hpc/public/PROVENANCE.md`.
- **Not hosted.** The N = 20 static cache (bath graph, SO(3) projectors and per-Ds vertices; 193 GB on
  Expanse scratch) is not hosted and is not needed by test, replay or smoke. A production rerun rebuilds it in about
  9 h on one 192G node; see `code/lri_3d_window_hpc/public/REPRODUCE.md`.

### `lri_3d_window_indep`

Folder: `code/lri_3d_window_indep/`.

#### Data: lri_3d_window_indep

Everything is in git; nothing is hosted.

| file | size | role |
|---|---|---|
| `indep_extract.json` | 0.7 MB | production values extracted from 181 records (2026-10-08); the 23 entries the comparisons use are verified against the shipped records in `HT/data/HT_3d` by `make replay`; the others (calibration and regression campaigns) are not shipped as records |
| `results/cmp_*.json` (23) | 92 KB in all | the comparisons quoted in the HT note |
