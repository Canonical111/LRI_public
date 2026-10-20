# Data: indep_d1

Shipped in `code/indep_d1/` (760 snapshot files, about 15 MB; with `public/` and the re-pinned overlay 3.8 MB packed).
22 of them are published in a scrubbed, re-pinned form (`RE-PINNED.json`, `RE-PINNED.md`: the personal desktop's name
removed; no number changed):

| record | what | read by |
|---|---|---|
| `engine/runs/prod_6digit/framework_input_final.json` | the 116 order-D4 raw scalars of phase 2, R = 6 replicates each (tier 1 with the top-up groups Q6_E, A7_v, A7_base, A5_vE) | `run_assembly.py`, `run_assembly_C8.py` |
| `engine/runs/prod_6digit/framework_input.json`, `results_final.json` | tier 1 alone (cross-check); all 439 collected coefficients (raw-coefficient comparison) | `run_assembly.py`, `compare_archive.py` |
| `engine/runs/c8tiersABC/framework_input_final.json` and the three tier files `c8tierA/`, `c8tierB_s0.01_r1/`, `c8tierC_s3_r2/framework_input_final.json` | the 85 scalars of C8 tiers A, B, C (merged per scalar; and per tier) | `run_assembly_C8.py` |
| `engine/runs/<run>/{manifest.json, *.cfg, results*.json, production_checks.*, tier_vs_*, budget_C8*, flags.json, outliers.txt, cfglist*.txt, SHA256SUMS_results.txt}` | for every production run (`prod_6digit`, `prod_6digit_topup1`, `poles1`, `c8tierA`, `c8tierA_topup1`, `c8tierB_s0.01_r1`, `c8tierB_s0.01_can`, `c8tierB_s0.01_topup1`, `c8tierC_s3_r2`, `c8tierC_s3_can`, `c8tierC_s3_topup1`; the suffix `_can` marks the tier-B/C runs on the personal desktop) the job definitions, collected results and engine-side checks (the production-check json files of the four runs on the personal desktop are not exported; their .txt summaries are) | the production rerun; `run_assembly*.py` (producers of the merged files) |
| `engine/runs/c8BC_SHA256SUMS.txt`, `c8tierA/SHA256SUMS_results.txt` | sha256 of the C8 deliverables, recorded at creation before any comparison | `run_assembly_C8.verify_inputs()`, `make test` |
| `engine/runs/poles1/results.json`, `conv1/results.json`, `engine/results/validation_*.json` | negative eps powers and convergence re-check (checks only) | `run_assembly.py` step 2 |
| `engine/runs/prod_6digit/{A3_base_k0,A3_E_k0,Z4_base_k-2,A5_base_k0}_c000.cfg.json` | four small raw chunk outputs, kept as fixtures | `make test` (engine rerun) |
| `spec/out/`, `spec/out/C8/` | archive-free targets: definitions, closed forms the note proves, higher logs, pole structure | assembly, framework tests |
| `spec/comparison/`, `spec/comparison_C8/` | sealed archive values (100-digit inputs, raw series, C8 records), with SHA256SUMS | `compare_archive*.py` only |
| `framework/out/` | symbolic derivations and the production record of B_old (`C8_production.json` + sha256) | framework tests, `run_assembly_C8.py` |
| `assembly/out/compute.json`, `direct_summary.json` | compute summary and the direct-comparison summary of phase 2 | `make_report.py`, `run_assembly.py` |
| `RESULTS*.json`, `RESULTS*.md` | the results (see README) | `compare_archive*.py`, `make_report*.py`, replay |
| `public/pooled_sector_record.json` (7.0 MB, 1.6 MB packed) | per engine job of the eleven runs: the per-replicate totals T and the sum over sectors of the replicate covariance M (exact, 25 digits) of every coefficient; jobs with at most 360 sectors also their per-sector replicate values | `public/pooled_shim.py` (the sector-pooled errors) |
| `public/RAW_SHA256SUMS.txt` | sha256 of the 293 raw chunk outputs | `make replay-raw` |

Not shipped:
* The raw per-sector chunk outputs `engine/runs/<run>/*.cfg.json` of the eleven runs (293 files, 131 MB). They are
  needed only to rebuild `public/pooled_sector_record.json` (`make replay-raw`). Hosted in the project's Zenodo data
  record (https://doi.org/10.5281/zenodo.23466766) as `SRI__indep_d1__raw_engine_outputs.tar.gz` (30,749,940 bytes, sha256 in `public/HOSTED.json`; deterministic
  tar.gz); `make -f public.mk fetch-data` downloads, checks and unpacks it into `.work/raw`, and checks every file
  against `public/RAW_SHA256SUMS.txt`. The run folders `c8tierB_s0.01_can` and `c8tierC_s3_can` keep their suffix
  (author decision); the files name no machine.
* Pilot, calibration, regression, probe and check runs (`c8val`, `c8conv`, `c8kplus1`, `c8probeBC`, `c8chkBC*`,
  `c8chkA7`, `kplus1`, `pilot*`, `regress_v2`, strict re-checks): about 300 MB; their results are summarised in
  `RESULTS*.md` and `engine/PRODUCTION_*.md`. Logs, sacct records, review folders, the direct tables (5 MB), the
  personal-desktop job scripts, the tier-B/C drivers, budget guard, core-hour ledger and submission list, and the
  production-check json files that name the personal desktop as a host. Kept in the project archive.
