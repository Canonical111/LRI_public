# Reproducing the Monte Carlo results

Read this file top to bottom before running anything. Steps 1–4 run on a workstation in minutes; steps 3 and 4 are the CI tiers.
Steps 5 and 6 describe the production campaigns: they are documented here but not run in CI. Step 7 lists the checks a result must
pass. Step 8 lists the decisions you must not make on your own. The physics and the meaning of every label are in
`note/lri_mc_note.pdf`; section numbers below refer to that note.

Ground rules:
- Run every `make` target from this folder (`MC/`).
- Never write into `data/`, `protocols/` or `results/`. Every target runs in the hidden workspace `.work/` (git-ignored). There the code is
  copied byte-identically into the layout it ran in during production and the data are linked; outputs go to `.work/reproduced/`. Call the
  make targets rather than the scripts, because the scripts expect that layout. `make clean` removes `.work/` and every output, and so does
  any change to the code, which rebuilds the workspace.
- The evaluators check the SHA-256 of the protocols, of themselves, of the calibration script and of their input records. Do not edit any
  file under `protocols/`, `code/2d/`, `code/3d/`, `code/reanalysis_p1/`, `results/2d3d_reanalysis/calibration/`, or the records under `data/`.
  A changed byte makes an evaluation non-production or makes it refuse to run, which is intended.
- The production records are byte-identical to production, except 25 records that named a personal machine and were scrubbed after the
  results (host labels, a home directory and file names; `RE-PINNED.json` maps original to published SHA-256, and the comparison applies
  the map). They name the cluster paths, user and compute nodes on which they were written. Nothing resolves those paths: the 2D/3D histogram indices are found through `--index-remap`, whose old prefix
  `code/package_tools/index_prefix.py` reads from the records. 1D refits outside the original paths are stamped NON-PRODUCTION; this changes
  no number, and the comparison strips the stamp.
- σ_sys is half the range over a family of fit models or extrapolation series: a sensitivity scale, not a standard deviation. Never add it
  to σ_stat in quadrature.

## 1. Environment

| need | production version | also tested |
|---|---|---|
| Python | 3.8.5 (1D fits), 3.8.8 (P1 evaluations and calibration) | 3.12.3; 3.8.8 with NumPy 1.20.1 and SciPy 1.6.2 |
| NumPy, SciPy | 1.19.2, 1.5.2 (1D); 1.20.1 (P1) | 1.26.4, 1.11.4 |
| pytest, matplotlib | – | 9.1.1, 3.6.3 |
| C++17 compiler, GNU make | g++ on the production cluster | g++ 13.3, make 4.3 |
| pdflatex (note only) | – | TeX Live 2021: pgfplots, booktabs, longtable, rotating, enumitem, caption, microtype, lmodern, url, hyperref |

```sh
pip install -r requirements.txt          # numpy, scipy, matplotlib, pytest (version floors in the file)
# or, with the production versions:
micromamba create -n lri-mc -c conda-forge python=3.8.5 numpy=1.19.2 scipy=1.5.2 pytest matplotlib
```
The production versions do **not** make the 1D fits bit-identical to production (§7, check C5). `make build` compiles the engines inside
`.work/` (about 5–30 s); `make test` and `make smoke` call it first.

## 2. Fast tests  (`make test`, 2.5–8 min, 1 core)

| test | checks | expected |
|---|---|---|
| 1D: `tests/test_fit_v3.py`, `tests/test_union.py` (in `code/1d`) | the 1D protocol logic: windows, ladder, gates, decision table, union of campaigns | all pass |
| P1: the 56 tests in `code/reanalysis_p1/tests`, run by `make test` inside the workspace | with the profiled rule off, the evaluators reproduce the frozen evaluators bit for bit; the profiled σ equals an independent implementation to 1e-12; every tampering case invalidates the calibration | 56 passed |

## 3. Replay: recompute the published numbers from `data/`  (`make replay`, CI tier)

`make replay` runs the steps below in order and then the comparison (§7). Each step recomputes numbers from the records in git.

| step | target | time | reproduces (note) |
|---|---|---|---|
| R1 | `eval-fixed`: `evaluate_2d.py`, `evaluate_3d.py`, frozen rule | 3 s | the 2D/3D labels under the frozen rule (Tables 15, 17) |
| R2 | `eval-p1`: the same with `--sigma-rule profiled`, the released calibration and the amendment | 4 s | the current labels: **3D s = 1.6: 1.47314 ± 0.00118 (stat) ± 0.00230 (sys), accepted only under P1, whose last code fixes are uninspected, with the suffix "σ_stat above target"**; the 2D CONDITIONAL values (Tables 15, 17; App. B) |
| R3 | `scan1d`: `scan_v3_report.py` over the per-coupling records | 1 s | the 20-point 1D table (Table 5): e.g. **0.61987(55)(220)** at Δσ = 0.05, i.e. value(σ_stat)(σ_sys) |
| R4 | `tables1d`: `make_tables_and_figure.py` | 2 s | the 1D table rows (Tables 5, 6, App. A) |
| R5 | `oned-xcheck`: `check_1d_xcheck.py` | 4 s | the 1D cross-check study (Table 8) |
| R6 | `note-tables`: `make_note_tables.py --check` | 1 s | every table body and plot coordinate of the note, including the d = 2 finite-size statement Δ_eff(U4, 512→1024) = 0.958–0.977 (Tables 14, 18); fails if any generated line is missing from the note or any input is missing |
| R7 | `refit-cited`, only after `make fetch-data` | 6–156 s per coupling on 20 cores | the full 1D fitting stage at Δσ = 0.05, 0.0875, 0.1727335 (§6.4.1) |

The basic replay, from git alone, does not cover the cited refits, the robust-ladder study or the P1 calibration. Without the archives R7 is skipped by design, and
`make verify` reports the regenerated-calibration check C3 as NOT RUN. The refits need `make fetch-data` and a multi-core node. The
calibration needs no archive but takes a 16-core node for about 7 minutes (below).

Not run in CI, but cheap enough to run before any claim:
- `make calibration WORKERS=16`: the P1 calibration from scratch, 1 780 tasks (89 ensembles × 20 chunks), ≈ 7 min on 16 cores.
- `make refit1d DS=<Δσ>` for all 20 couplings: 6–156 s each on 20 cores, ≈ 25 min in total (needs `make fetch-data`).
- The robust-ladder study (note §6.4.2, Table 11), also after `make fetch-data`. `results/1d/robust_ladder_20261013/` holds the modified
  fitter `select_model_v3_robust_ladder.py`. It differs from `code/1d/select_model_v3.py` only in the stop condition of the degree ladder
  (a flagged lower-degree fit no longer stops it) and in a field `diagnostic_variant` that it writes into every output. The folder also
  holds, per coupling, the `fit_v3.json`, `FIT_V3_RESULTS.md` and `MANIFEST.txt` of the frozen (`trimmed/`) and the modified (`robust/`)
  fitter, both run on one node. To rerun it, build the workspace, copy the modified fitter over `.work/lri_cluster/select_model_v3.py`,
  and run `bash code/package_tools/refit_1d_point.sh .work <Δσ>` for each coupling; compare the decision, n_q and σ_sys with
  `robust/ds<Δσ>/fit_v3.json`. `make verify` does not cover this study. `make clean` restores the frozen fitter.

The 1D counts quoted in the paper (20 couplings, 10 240 chains in the final fits, 2.05 × 10¹⁰ sweeps, N up to 2^19) come from the campaign
registries `data/1d/scan_data/ds*/campaigns.json` and the stage manifests. A script that recounts them is not available yet.

## 4. Smoke: a small validation run with expected output  (`make smoke`, CI tier)

`make smoke` builds the engines and runs their self-validating tests. The expected output is the tests' own assertions; the target fails
if any assertion fails. Its runtime on the public layout has not been measured yet.
- `code/1d/tests/test_runner.py`, `test_engine_1d.py`: a tiny 1D campaign (N = 1024) runs end to end through the campaign tools, resumes
  bitwise after an interrupt, and is read by the analysis.
- The 2D/3D engine tests (`make test` in `code/2d3d_engine/code`):
  - the sampler against exact enumeration of 4×4 (2D) and 2³ (3D) systems;
  - bitwise restart;
  - the extended moments m6 and m8.

Not available yet:
- S3: a statistical smoke run at Δσ = 0.1, N = 1024, with the five production temperatures and 8 chains × 10⁵ sweeps (fixed seeds),
  compared with the production values per temperature, passing if every |pull| ≤ 4. The production reference
  `data/1d/scan_data/ds0.1/merged_b4096_*/summary.json` is archive-only, so a small expected-values file must be shipped with the test.
- S4: the same for 2D at s = 1.3, L = 64, against `data/2d/prod/analysis_b2000_s1.3/`.
- `make smoke-pilots WORKERS=4` runs fresh 2D/3D pilots through prepare → run → pack → analyse (`reproduce_pilots.sh`). It has no
  expected-output file yet.

## 5. Production, stage by stage  (documented, not run in CI)

The production ran on a Slurm cluster with 128-core AMD EPYC 7742 nodes. Every chain is one process: hot or cold start, 5 × 10⁴ warm-up
sweeps, then the measured sweeps, with checkpoint/restart, a completion record and one record per sweep. Total compute, including
development and repeated runs: d = 1 9.8 × 10⁴ core-h; d = 2 and 3 together 8.4 × 10⁴ core-h. A per-stage split from the accounting is not
available. The figures below are the measured rates and layouts.

**d = 1** (`code/1d`). The final fits use 10 240 chains (stages A, B and N2), with 2 × 10⁶ measured sweeps each, 8 hot/cold replicas per
(N, β) and 5 temperatures per size:

| stage | what | engine | driver | in final fits |
|---|---|---|---|---|
| pilot, two-point | Δσ = 0.1, 1/16; 800 chains | reference `lri_mc` | `prepare.py`, `submit.py` | no |
| stage 0 | temperature centres | reference | `prepare_stage0.sh`, `stage0_centres.py` | no |
| stage A | 20 couplings, N = 2^10 … 2^16, 5 600 chains | reference | `prepare_stageA.sh`, `stageA_centres.py` | yes |
| stage B | 20 couplings, N = 2^17 … 2^19, 2 400 chains | reference | `prepare_stageB.sh`, `stageB.sh` | yes |
| N0 | diagnostic at Δσ = 0.175, 72 chains | reference | `n0_diagnostic.py` | no |
| N2 | 14 couplings, N = 2^16 … 2^19, 2 240 chains | `lri_mc_1d` | `prepare_stageBx.py`; ≈ 136 node-h | yes |

`submit.py` takes `--account` and `--partition`. The stage scripts in `code/1d` (`stage*.sh`, `prepare_stage0.sh`, …) are kept unchanged
as the record of what ran: they hard-code the original account and partitions, so edit a copy before use.

**d = 2** (`code/2d3d_engine` and `code/2d`; 2 400 chains, 154 GB raw):
- **Stage 0:** L ≤ 512, 2 replicas, 10⁵ sweeps. It fixes `data/2d/production_centers.csv`.
- **Preflight:** L = 512, 1024, 5 × 10⁴ sweeps. Every crossing must lie inside its bracket with effective sample size ≥ 0.2.
- **Production:** 12 replicas × 10⁶ sweeps × 5 temperatures × 5 sizes × 8 couplings, half-width w(L) = 0.0015 (L/64)^−0.75.
  - L = 1024 runs 96 chains per node at 88 ms per sweep, 25–31 h per chain.
  - L ≤ 512 runs in four whole-node array tasks ("node slots") of 480 chains each, about 6 h per task.

**d = 3** (same code and `code/3d`; 2 400 chains):
- Stage 0, then the preflight gate (records in `data/3d/preflight/`), then production. Same design as d = 2, with L = 8 … 128 and
  w(L) = 10⁻³ (L/16)^−1.
- **Cache rule:** an L = 128 chain (≈ 10 MB working set) runs at 105 ms per sweep alone, but at about 250 ms when four chains share a
  4-core CCX (cores sharing one 16 MB L3 cache). Pin **one L = 128 chain per CCX**, i.e. 32 per 128-core node; this gives ≈ 30 h per chain
  on 15 nodes. Run L ≤ 64 on separate nodes.

Templates: `slurm/2d/*.slurm|*.sh` and `slurm/3d/*_3d.slurm|*_3d.sh`. They have placeholders `<ACCOUNT>`, `<PARTITION_NODE>`,
`<PARTITION_SHARED>`, `<SCRATCH>`, `<CODE_2D>`, `<CODE_3D>`, `<LOAD_MODULES>` and `<DEPS>` (job ids for `--dependency`). `<CODE_2D>` and
`<CODE_3D>` are where `code/2d3d_engine/code` and `code/2d` or `code/3d` are installed. Put the 2D templates in `<CODE_2D>` and the 3D
templates in `<CODE_3D>/cluster/`, where the 3D scripts call each other; `slurm/README.md` gives the order and the site rules hard-coded in
them. The benchmark scripts and the 3D stage-0 input `reference_centers_3d.csv` are not shipped; the production temperature centres that
stage 0 produced are (`data/{2d,3d}/production_centers*.csv`). The P1 evaluation templates (`prod_evaluate*.slurm`) are described in
`slurm/README.md`.

## 6. Merge

**d = 1, per coupling** (`code/1d/run_point_v3.sh snapshot|finalize`). Every snapshot is immutable; its manifest hashes every input; every
run writes a fresh output directory.
```sh
python completion_check.py REGISTRY --campaigns … --evidence completion_T_HOST.json      # every chain complete, record format, seeds
python analyze.py POINT/STAGE --block {2048,4096,8192} --out POINT/STAGE_an_b{b}_T        # per stage, three block sizes
python union_check.py REGISTRY --tag T --point-dir POINT --out union_check_T.json        # independence of the campaigns
python merge_summaries.py REGISTRY --coverage all --suffix _an_b{b}_T --out POINT/merged_b{b}_T
python select_model_v3.py --merged merged_b4096_T --reblock merged_b2048_T merged_b8192_T --bootstrap 300 --calibration 500 \
       --schedule 20260916 --pre pre.json --analysis-manifest … --completion-evidence … --registry … --out POINT/fits_v3_TIME
python scan_v3_report.py SCAN_DIR --out FIT_V3_SCAN.md                                     # the 20-point table
```
`pre.json` holds the frozen window parameters. Use the one in the selected run (`fits_v3_<time>/pre.json`) and never re-derive it.

**d = 2, 3, per campaign:**
```sh
python pack_histograms.py CAMPAIGN --block {1000,2000,4000}           # only after all 2 400 chains are complete
python precision_analysis.py CAMPAIGN/hist_b{b}/index.json --dim D --s S --bootstrap 500 --seed 571239 --min-ess 0.2 --out analysis_b{b}_sS
python evaluate_2d.py --primary analysis_b2000_s* --reblock analysis_b1000_s* analysis_b4000_s* --plan FIT_MODEL_2D.md \
       --manifest CAMPAIGN/manifest.json --centers production_centers.csv \
       [--sigma-rule profiled --calibration CALIBRATION.json --amendment AMENDMENT_PROFILED_SIGMA.md] \
       [--index-remap OLD_PREFIX=NEW_PREFIX] --out EVAL
```
For 3D, use `evaluate_3d.py` with `--snapshot <tag>` (54387089 for the released records). Outside the original paths, pass
`--index-remap`; `make eval-*` does this automatically. Each production analysis used 4 cores and 32 GB per (s, block) task. Rerunning the
analysis from the histograms needs the 2D/3D trees, which are not hosted; they are available from the author on request.

## 7. Checks  (`code/package_tools/compare_outputs.py`, run by `make replay` and `make verify` → `.work/reproduced/VERIFY.md`)

| check | compares | tolerance | expected |
|---|---|---|---|
| C1 | R1 with the pinned production evaluations (`data/{2d,3d}/prod/evaluation_*`), all per-point fields | rtol 1e-9, paths normalised | PASS (observed ≤ 3 × 10⁻¹¹) |
| C2 | R2 with the released P1 evaluations (`results/{2d,3d}/evaluation_P1_*`) | rtol 1e-9, paths normalised | PASS (≤ 2.3 × 10⁻¹¹) |
| C3 | the regenerated calibration (only after `make calibration`): strata, adoption rule A3, information | rtol 1e-9 | PASS (≤ 2.3 × 10⁻¹¹) |
| C4 | R3 with `data/1d/scan_data/FIT_V3_SCAN.json`; R4 with `results/1d/tables/*` | rtol 1e-9; tables by text | PASS |
| C5 | each 1D refit, decision level: label, quoted configuration, Δε, σ_stat, σ_sys, the set of quotable fits | absolute 1e-6 | PASS at 18 couplings. At Δσ = 0.1625 and 0.1727335 the label (and with it σ_sys and the quotable set) may differ: reported as KNOWN-PLATFORM-SENSITIVE, not a failure. Any other difference there, or any label difference elsewhere, is FAIL. |
| C6 | each 1D refit, all fields | informational | DIFF expected: nonlinear optima agree to ~10⁻⁷ across platforms |
| C7 | R5, the cross-check study, with `results/1d/oned_xcheck/` | rtol 1e-9 | PASS |
| C8 | R6 | exit status of `make_note_tables.py --check` | 0 |

The maximum relative difference in VERIFY.md is taken over values with |reference| > 1e-9, and the report names the field where it occurs.
Smaller values, such as reproduction residuals at machine precision, are compared with the absolute tolerance only. A comparison whose
inputs were not produced shows NOT RUN and does not fail. Expected VERIFY.md off the production host: every comparison PASS, the refits
KNOWN-PLATFORM-SENSITIVE at 0.1625 and/or 0.1727335, and NOT RUN for C3 and for refits not made.

Gates already applied in the records; re-apply them to any new data:
- **Equilibration:** in each (L, β) group, block length ≥ 20 τ_int at every block size, the first and second halves of each chain agree
  (|z| ≤ 4), every chain's block mean of m² lies within |z| ≤ 4 of the group, at most 2 % of chains exceed |z| = 3, and no group loses half its
  chains.
- **Coverage:** every pre-registered size and pair is present. Otherwise the coupling is COVERAGE-LIMITED, never fitted on fewer sizes.
- **Reblocking:** σ_stat at the other block sizes stays within ±30 %.
- **Fits:**
  - d = 1: the quotable-fit gates (note §6.2);
  - d = 2, 3: χ²/dof ≤ 2, the ω′ interval inside [0.22, 1.98], σ_∞ ≤ 5 × the error of the largest pair.
- **Cross-check:**
  - d = 1: |fit − median crossing| ≤ 2σ_D, where σ_D includes the pre-registered spread term;
  - d = 2, 3: |U4 − Y| ≤ 2σ_D.

## 8. Decisions you must not make on your own

Stop and ask the author before any of these:
1. Changing a fit protocol, an acceptance rule, a gate, a threshold, the decision table or its order. This includes the 1D ladder rule,
   which is known to be fragile (note §6.4); fixing it needs a written, reviewed amendment and a rerun of all 20 couplings.
2. Choosing windows, temperature centres, sizes, minimum sizes, model variants or series after looking at the result they produce. Re-deriving
   `pre.json`.
3. Re-seeding, enlarging the bootstrap, refining a grid, or rerunning on another machine **in order to change a label**. Report a label
   that differs from production (C5) as found. Do not pick the platform that gives the preferred label.
4. Dropping chains, temperatures, sizes, pairs, crossing series or couplings, or merging campaigns that are not in the registry.
5. Editing any hash-bound file (protocols, amendment, evaluators, `calibrate_p1.py`, the calibration, the records), "repairing" the
   `FIT_MODEL_3D.md.sha256` mismatch (it records the approved revision 5; see `protocols/PROTOCOL_HISTORY.md`), or editing manifests to clear
   a NON-PRODUCTION stamp. Then regenerating the calibration so that the bindings pass again.
6. Using a preview or diagnostic switch for any reported number: `--no-index-check`, `--diagnostic`, `--legacy-windows`, `--only`,
   `--entropy`.
7. Adding σ_stat and σ_sys in quadrature, or presenting σ_sys as a standard deviation or a confidence interval.
8. Presenting a CONDITIONAL, MODEL-LIMITED or CROSS-CHECK FAILED value, or a finite-size Δ_eff, as an infinite-size value. In particular,
   d = 2 has none.
9. Citing 3D s = 1.6 without "accepted only under amendment P1", "the last P1 code fixes are uninspected" and the suffix "σ_stat above
   target".
10. Adopting another correction model in place of the protocol's estimator.
11. Spending production compute: 3D L = 256 (≈ 1.5 × 10⁴ core-h), 2D L = 2048, 1D N = 2^20, or a new campaign.
12. Deleting or overwriting any record or archive, or uploading data to a new host.
