# Data: c2_cylinder_d2

Everything `test`, `replay` and `replay-full` need ships in the package: 295 files, 78 MB unpacked. Packed it is
16.4 MB as `tar czf` and 28.7 MiB as a git pack; without the cluster records under `outputs/`, the git pack is
2.5 MiB. The records ship because the package stays under the SRI budget of about 30 MB packed. Nothing is hosted, so
there is no `fetch-data` target. No file exceeds 2 MB.

## What ships

| Path (under `SRI/code/c2_cylinder_d2/`) | Size | Content | Bound by |
|---|---|---|---|
| `outputs/merged_production_plan_20261013.json`, `outputs/merged_analysis_checks_plan_20261013.json`, `outputs/merged_analysis_checks_plan_rev6_20261014.json` | 176 kB | merged indexes of the cluster records (`cluster/sitekit/merge_records.py`): path, sha256, configuration, plan and science-source digest of every record | `C2_estimate.json` `meta.inputs_sha256`; `public/SNAPSHOT.sha256` |
| `outputs/{expanse,symmetry}/production_plan_20261013/outputs/production_plan/<task>/` | 16 records | PRIMARY production records (PILOT N = 512 on both sites, P1 N = 768 on symmetry, P2 N = 1024 on Expanse): `cluster_k<r>_a<lambda>_N<N>.json` (pairing-resolved partial sums at every cutoff, two-point, mixed and planar terms), the analysis sidecar `*_analysis.json` (leading tail at cutoff 8192), `task_receipt.json` (configuration, science-source hashes, command), `SHA256SUMS` | merged index sha256 and the task `SHA256SUMS`, both checked at run time by `code/continuum/continuum_records.py` |
| `outputs/expanse/analysis_checks_plan_20261013/...`, `outputs/symmetry/analysis_checks_plan_rev6_final/...` | 5 + 20 records | DIAGNOSTIC extraction-check records (the same points computed on a different Cauchy grid); same files per task | as above |
| `outputs/symmetry/c2aux_574247/` | 29 files | aligned auxiliary inputs per (order, lambda): mixed sums to 16384, collapsed norms at 400000 and 800000, leading-tail coefficients at 2048 and 8192; receipt, environment check, staged-package info | its `SHA256SUMS`, every file checked at run time |
| `data/hamiltonian/raw/` | 17 + 1 records, 6.8 MB | archived records of the supplied study (N = 128, 256, 384) and the small demo record | `MANIFEST.sha256`, checked at run time |
| `data/hamiltonian/auxiliary/`, `reference/`, `run_plan.json` | | archived leading-tail inputs; the historical analysis (legacy-mode reference); the archived configurations | `MANIFEST.sha256` |
| `results/continuum_2026-10/CURRENT`, `generations/20261015T000632Z_99019_1e66b9/` | 2 MB | the result: `C2_estimate.json`, `continuum_points.json`, `regulator_fits.json`, `REPORT.md` (one immutable generation; `CURRENT` names it) | `MANIFEST.sha256` (verbatim list) |
| `results/continuum_2026-10/evidence/rev4/{C2_estimate.json, continuum_points.json, README.txt}` | 1 MB | the superseded rev-4 result. The driver reads it: frozen extraction values for a failed completion row (none failed) and the superseded numbers it reports | `meta.inputs_sha256` |
| `results/continuum_2026-10/evidence/legacy_macos/` | 300 kB | legacy-mode (A1) receipt and outputs from the production machine, read by the driver (`--legacy-receipt`) | `meta.inputs_sha256`, `legacy_validation.sha256` |
| `results/continuum_2026-10/evidence/DEVIATIONS_ANALYSIS.md` | 1.5 kB | deviation D1 (the N = 1024 extraction checks moved from Expanse to symmetry) | `deviations[].sha256` |

The tracked files at 98e1935 that are not shipped (654 entries of `MANIFEST.sha256`) are listed in
`public/NOT_EXPORTED.txt`:
- the evidence of earlier revisions and review rounds (`results/{expanse,symmetry,fix_round1,fix_round2,revision,...}`);
- the superseded rev-4 report and fits;
- the top-level copies of the current generation (identical bytes);
- the closed-form study and its certificate (`code/original_study`, `code/formula_checks`, `reference/`; covered by
  the sibling package `c2_closed_d2`);
- the initial finite-basis diagnostics;
- the repository's own manifest tools, replaced by `public/verify_manifest_public.py`;
- `.gitignore`, which ignores `outputs/` and would hide the records in the public repository.

Not shipped from `outputs/`:
- the code tarballs staged for the clusters (`site_pkg/`, `expanse_pkg/`, `*.tar`);
- per-task job and run receipts and run logs (`job_receipt.json`, `expanse_job.json`, `run_receipt.json`,
  `run_log.txt`). They are still listed in the task `SHA256SUMS`, and `verify_manifest_public.py` reports them as not
  exported;
- collection receipts and logs;
- a superseded collection directory.

## Not shipped and not needed for any replay

The Cauchy coefficient grids are deterministic functions of (N, oversample, radius_cost, science sources):
- N = 768: about 33 min to build on one symmetry Intel node;
- N = 1024: about 40 min on an Expanse large-shared node, or 2.7 h with 16 workers on a symmetry Intel node;
- each N = 1024 grid is about 52 GB.

`cluster/sitekit/grid_job.sbatch` regenerates them for a production rerun (see `REPRODUCE_c2_cylinder_d2.md`). They
are not records and are not hosted.

## Names in shipped records

Kept byte for byte because a checksum checked at run time binds them:
- the task receipts (20 files) name the authors' cluster user names on symmetry and SDSC Expanse (`<USER>` in new
  text) in their home, `/local1` and scratch paths;
- `outputs/symmetry/c2aux_574247/env_check.json` names the symmetry home directory of that user.

No shipped record names a personal machine. Three result files carry an absolute path of the authors' desktop as one
JSON key: `meta.inputs_sha256` of `C2_estimate.json`, `continuum_points.json` and `regulator_fits.json`. That path is
the deviation record's original location; the replays match the key by file name, so it can carry a placeholder.
