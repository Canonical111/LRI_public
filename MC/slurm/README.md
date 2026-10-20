# Slurm templates for the 2D/3D campaigns

These are the job scripts of the 2D and 3D production campaigns, with the site-specific values replaced by placeholders. The 1D campaigns
were driven by `code/1d/submit.py` and `code/1d/run_task.py`, which take the account and partition as arguments (REPRODUCE.md §5).

Replace before use:

| placeholder | meaning |
|---|---|
| `<ACCOUNT>` | Slurm account (`-A`) |
| `<PARTITION_NODE>` | partition for whole-node jobs (production chains: 128-core nodes, one L = 128 chain per 4-core CCX in 3D) |
| `<PARTITION_SHARED>` | partition for shared, partial-node jobs (packing, analysis, evaluation) |
| `<SCRATCH>` | the scratch file system root under which campaigns write (the campaign directories `lri2d/prod2d`, `lri3d/prod3d` go below it) |
| `<CODE_2D>`, `<CODE_3D>` | where the 2D/3D code is installed on the cluster (the `LRI_2d_MC`, `LRI_3d_MC` folders of the workspace) |
| `<LOAD_MODULES>` | the site's module commands for a C++17 compiler (gcc >= 10) and Python 3 with NumPy and SciPy |
| `<SNAP>` | (already in the original) the record tag of a pack/analysis snapshot |
| `<DEPS>` / `DEPS=` | the job ids of the production arrays that packing and analysis must wait for (`--dependency=afterany:…`) |

Order:
- **2D:** `prepare_stage0.sh` → `stage0.slurm` → `preflight.sh` → `submit_production.sh` (with `continue.slurm` for wall-time
  continuations) → `prod_pack.slurm` → `submit_analysis.sh` (`prod_analysis.slurm`) → `prod_evaluate.slurm`.
- **3D:** `stage0_3d.slurm` → `submit_preflight_3d.sh` (`preflight_3d.sh`, `preflight_analysis_3d.slurm`) → `submit_production_3d.sh`
  (`array_pinned.slurm`, `continue_3d.slurm`) → `prod_pack_3d.slurm` → `submit_analysis_3d.sh` (`prod_analysis_3d.slurm`) →
  `prod_evaluate_3d.slurm`.

Where the scripts go: the 2D scripts in `<CODE_2D>`, the 3D scripts in `<CODE_3D>/cluster/` (they call each other there), not in this
folder. The scripts refuse to resubmit while jobs of the same campaign are queued, and they never cancel running jobs. Costs and node layouts
are in REPRODUCE.md §5.

Not shipped, and how to do without:
- the benchmark scripts of the original campaigns (`bench.slurm`): the measured rates are in REPRODUCE.md §5;
- the 3D stage-0 input `reference_centers_3d.csv` (read by `stage0_3d.slurm`): stage 0 only fixes the production temperature centres,
  which are shipped (`data/3d/production_centers_3d.csv`), so a rerun of the production can start at the preflight.

Site rules of the original allocation that are hard-coded: `submit_production.sh` and `submit_production_3d.sh` query the `normal` QOS,
and `submit_production_3d.sh` keeps at most 22 of the user's normal-QOS jobs running (`ALLOW=$(( 22 - NSMALL - OTHER ))`). Adapt both to
your site.

The evaluation step in these scripts (`prod_evaluate*.slurm`) predates amendment P1: for the current labels add
`--sigma-rule profiled --calibration … --amendment …` as in the Makefile's `eval-p1` target.
