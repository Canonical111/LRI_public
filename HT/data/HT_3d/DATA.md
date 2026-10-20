# HT_3d data: d = 3 production records

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
