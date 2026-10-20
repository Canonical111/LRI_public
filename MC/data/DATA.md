# Data: the merged production records

`data/` holds the merged records from which every published MC number is computed. Two archives of large intermediate files are not in
git: `make fetch-data` downloads them from the project's Zenodo data record, [doi:10.5281/zenodo.23466766](https://doi.org/10.5281/zenodo.23466766), and unpacks them here (below). The raw
trajectories are not hosted; they are available from the author on request.

**Do not edit anything here.** Many records are bound by SHA-256:
- the snapshot manifests hash the summaries;
- the analysis records hash their histogram index;
- the P1 calibration and the evaluators bind the primary 2D/3D records and the pinned evaluations.

Editing one byte makes an evaluation non-production or makes it refuse to run.

**Paths inside the records.** The records are byte-identical to production, so they name the absolute cluster paths, the user and the
compute nodes on which they were written, and their hashes are the production hashes cited in the note. Exception: 25 records named a
personal machine and were scrubbed after the results: the registries, completion records, analysis manifests, union checks and selected
fit runs of Δσ = 0.225 and 0.2375 (five renamed: `*_personal-desktop.*`), `results/1d/records/points/pre_ds0.225.json` and the P1
`CALIBRATION.json`. Only host labels, a home directory (`<HOME>`) and file names were replaced; no number changed. Inside the scrubbed set
every hash of another scrubbed file was re-pinned, so the lineage, coverage and union checks of the 1D code still pass. Records outside the
set keep the original pins. `RE-PINNED.json` (top of the MC folder) gives, per file, the original and published SHA-256, the substitutions
and the count of changed fields. The code never needs those
paths to resolve: the evaluators read the histogram indices through `--index-remap`, whose old prefix the Makefile reads from the records
(`code/package_tools/index_prefix.py`). Files written for the release under `results/` (the cross-platform refits, the robust-ladder
study) are not hash-bound; in them, paths and host names are replaced by placeholders (`<HOME>`, `<SCRATCH>`, `<NODE>`, …) or by "personal
desktop".
PROVENANCE.md states the policy.

## d = 1: `data/1d/`

`scan_data/ds<Δσ>/`: one folder per coupling (20).

| file | content | in git |
|---|---|---|
| `fits_v3_SELECTED.json` | names the selected snapshot and fit run | yes |
| `fits_v3_<time>/` (the selected run): `fit_v3.json`, `FIT_V3_RESULTS.md`, `MANIFEST.txt`, `pre.json`, `quot_*.json`, `xcheck_ds*.json`, `xcheck_ds*.samples.npz`, `select_model_v3.log` | for every configuration: its degree ladder, gates and bootstrap summary; the quoted fit and the label; the frozen window parameters (β_c^pre, Δε^pre); the crossing series; the cross-check draws; the SHA-256 of the code and inputs | yes |
| `fits_v3_<time>/fits/` | per-degree fit results, 140 MB in all | no: `MC__1d_fits_per_degree.tar.gz`, for inspection; no target needs them. Kept in git: the quoted fit of each coupling, and the two degree-3 fits of `x0.45_background_Nmin8192_K2` at Δσ = 0.1625 and 0.1727335; the note's Tables 7 and 10 are generated from them. No record pins these files; in the hosted copies the cluster scratch prefix is replaced by `<SCRATCH>` |
| `analysis_v3_<snap>*.manifest`, `completion_<snap>_*.json`, `registry_<snap>_*.json`, `campaigns.json`, `union_check_<snap>.json`, `stage*/manifest.json` | the lineage of the snapshot: which campaigns, every chain complete, the hashes of every summary and block archive; the campaign manifests (sizes, temperatures, seeds) | yes |
| `merged_b{2048,4096,8192}_<snap>/summary.json` | the merged per-(N, β) summaries the fit reads, 25 MB | no: `MC__1d_refit_inputs.tar.gz`, byte-identical; **needed by `make refit1d`**, and the selected run's `MANIFEST.txt` pins their hashes |
| `stage*_an_b{2048,4096,8192}_<snap>/` | per-stage block archives (jackknife blocks of Y, U and their β-derivatives), 1.43 GB | no: `MC__1d_refit_inputs.tar.gz`, byte-identical; **needed by `make refit1d`** |

Other files:
- `scan_data/FIT_V3_SCAN.json` and `.md`: the 20-point table, which `make scan1d` rebuilds.
- `reference/published_and_epsilon_reference.csv`: the frozen pre-campaign reference (published Monte Carlo values and six-loop
  ε-expansion values). It enters no fit or label.
  - `published_MC_*`: published values from Uzelac–Glumac–Aničić 2001 and Angelini–Parisi–Ricci-Tersenghi 2014, with URLs.
  - `six_loop_GFF_only`, `six_loop_endpoint_assisted`: six-loop resummations, made with an older C6(1). The eight-loop values in
    `data/reference/` supersede them.
  - **Superseded, do not cite:** `new_MC_conditional_fit`, `new_MC_local_statistical_error`, `same_model_size_cut_scan_*`, `baseline_*`,
    `Lmin`, `Lmax`, `status`. They come from an exploratory pre-campaign analysis with N ≤ 16 384 that the production replaces; for
    example, it gives 0.4872 at Δσ = 0.2, a coupling the production rates MODEL-LIMITED.

## d = 2, 3: `data/2d/`, `data/3d/`

| file | content | in git |
|---|---|---|
| `prod/analysis_b{1000,2000,4000}_s<s>/` (3D: `analysis_54387089_b…`) | `results.json`: per doubling pair the crossing β×, Δ_eff of U4, U6, U8 and Y with errors and covariance, diagnostics, and the per-chain raw and binary hashes. `bootstrap.npy`: 500 draws × 4 pairs × [β×, Y, U4, U6, U8]. `dimensions.csv` | yes. Block 2000 is primary; 1000 and 4000 are the reblocking checks |
| `prod/manifest.json`, `prod/plan.json` | the campaign: 2 400 tasks with L, β, replica and seed | yes |
| `prod/hist_b*/index.json` | histogram indices, pinned by hash in the records; the histograms are in the raw trees (not hosted) | yes |
| `prod/evaluation_*/` | the pinned production evaluation under the frozen rule. The P1 calibration binds it, and `make eval-fixed` compares against it | yes |
| `production_centers*.csv`; `3d/preflight/GATE_*.json` | the frozen temperature centres; the 3D preflight gate records, failed first attempt and passing second attempt (note §5) | yes |
| packed histograms, chains | the full campaign trees: 2D 257.5 GiB, 3D 237.2 GiB | no; not hosted, available from the author on request |

The P1 calibration read by `make eval-p1` is in `results/2d3d_reanalysis/calibration/run_20260930_213748/`.

## Files not in git: `make fetch-data`

`data/HOSTED.json` lists the two archives of the project's Zenodo data record that belong to this folder, with their sizes and SHA-256.
`make fetch-data` (`code/package_tools/fetch_data.py`) downloads both (`FETCH=refit` or `FETCH=fits` takes one), checks each file's size
and SHA-256, and unpacks it into this folder:

| file | size | unpacks to | needed by |
|---|---|---|---|
| `MC__1d_refit_inputs.tar.gz` | 1.41 GB, 4 278 files | `data/1d/scan_data/ds*/stage*_an_b*_<snap>/` and `merged_b*_<snap>/` | `make refit1d`, `make refit-cited`, the robust-ladder study |
| `MC__1d_fits_per_degree.tar.gz` | 42 MB, 5 666 files | `data/1d/scan_data/ds*/<selected run>/fits/` | inspection only |

The script accepts only regular files in these folders, and each block archive and merged summary must have the SHA-256 that the coupling's
`analysis_v3_<snap>.manifest` pins. It never overwrites a file that is already present; the 19 per-degree fits in git are not in the archive. The files are downloaded from
`https://zenodo.org/records/23466766/files/<name>`; `--from-dir DIR` takes them from a local copy instead.

## Comparison values: `data/reference/`

These are theory values (the eight-loop resummed ε expansion of the accompanying article, with bands) and published values. They are used
only in the note's comparison tables. Provenance and caveats are in `data/reference/README.md`. The bands are sensitivity ranges over
resummation prescriptions, not confidence intervals.
