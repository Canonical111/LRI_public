# NRG: reproduction

Read this file top to bottom before running anything.
- Steps 1–4 run on a workstation in about two minutes. Steps 2–4 are the quick checks.
- Step 5 is the production on a Slurm cluster (178 thread-hours). It is documented here, not run in CI.
- Step 6 lists the checks every result must pass.
- The last section lists the decisions you must not make on your own.

Ground rules:
- Run every `make` target from `NRG/`.
- **Never write into `code/`, `inputs/`, `data/`, `results/`, `independent_check*/` or `method_comparison/`.** `make
  replay` and `make smoke` work in the hidden workspace `.work/`, where the analysis scripts are copied and the records
  are symlinked. Their outputs go to `.work/`, and `make clean` removes it.
- **Run the analysis only through `make`.** `code/analysis/run_all.sh` just calls `make replay`. Running the analysis
  scripts directly from `code/analysis/` would write into the released folders.
- **Do not edit any hash-bound file.** Each record in `data/records` carries a SHA-256 over its identity and payload.
  Its identity names the SHA-256 of the solver source `code/lri_spin_boson_hpc/src/lri_spin/*.py` (`3a40deb333e1…`) and
  the runtime of `inputs/validation_receipt/receipt.json`. The manifests in `inputs/manifests` name the same source hash.
  `summarize.py` refuses any record that does not match all of these, so a changed byte in a record, manifest or the
  receipt makes replay stop, which is intended. Check V0 of `verify.py` compares the solver source itself with the
  receipt, and `make test` checks every code file against `MANIFEST.sha256.json`.
- The Makefile sets `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`.

## 1. Environment

| need | production (cluster) | also tested (`make test/replay/smoke`) |
|---|---|---|
| Python | 3.13.3 (module `python/3.13-mamba` plus a venv) | 3.10.12, 3.12 |
| NumPy, SciPy, threadpoolctl | 2.1.2, 1.15.2, 3.6.0 | NumPy 1.24.4–2.3.5, SciPy 1.11.4–1.17.1, threadpoolctl 3.1–3.7 |
| BLAS | OpenBLAS 0.3.27/0.3.28, Haswell kernel | the wheels' OpenBLAS |
| pytest, mpmath | 8.4.2, 1.3.0 | 9.1.1, 1.4.1 |
| matplotlib | figures only | 3.10.9 |
| pdflatex | note only | TeX Live: geometry, amsmath, amssymb, dsfont (package doublestroke, missing from some minimal installs), booktabs, longtable, array, graphicx, xcolor, caption, microtype, enumitem, lmodern, url, hyperref |

```sh
python -m pip install -r requirements.txt
```
The production runtime is recorded in `inputs/validation_receipt/receipt.json` (runtime block) and in
`inputs/environment/ENV.json` (pip freeze of the cluster venv).

`make replay` also needs the Monte Carlo scan table of this repository, `../MC/data/1d/scan_data/FIT_V3_SCAN.json`.
Override its location with `make replay MCSCAN=<path>`.

## 2. Fast tests (`make test`, about 75 s, 1 core)

| test | checks | expected |
|---|---|---|
| `code/lri_spin_boson_hpc/tests/verify_manifest.py` | SHA-256 of every file of the code tree against its `MANIFEST.sha256.json` | `Verified 52 distribution files` |
| `pytest code/lri_spin_boson_hpc/tests` (85 tests) | chain moments; untruncated spectra against exact diagonalization; Kronecker products against block operators; bitwise equality with the reference solver of the original study; finite differences against the exact α-derivative; checkpoints, resume, corruption, signals, locks; campaign ownership, generations, lanes and submission against a simulated Slurm; exports and stopping | `85 passed` |
| `independent_check/selftest.py` (38 checks) | the second implementation: the chain reproduces the star, NRG equals exact diagonalization, parity structure, critical search, window geometry, bisection | `SELFTEST PASSED` |

## 3. Replay: recompute every published number from `data/` (`make replay`, about 20 s)

| step | script | reproduces |
|---|---|---|
| R1 | `code/analysis/summarize.py` | Verifies each of the 197 records: checksum, identity against its manifest item and the receipt, numerical gates. Writes per-item summaries and the cost table (`.work/data/summaries/`). |
| R2 | `code/analysis/build_tables.py` with `estimator.py` and `crosscheck.py` | The estimator of every item (settled value, plateau drift, extrapolation; note §3.7) and the detuning cross-check fits of the central items (not adopted), `results/ds13_final.json` and `.md` (the final table with all error components, the fits and the superseded midpoint budget), `results/lambda_study.json`, and the note tables from the build stage (`keep_nb`, `lambda`, `lambda_shift`, `example`, `resources`, `all_items`). |
| R3 | `code/analysis/make_figures.py` | Five of the note's figures (budget, K/n_b, Λ, window audit, α_c). |
| R4 | `independent_check_compare/compare.py`, `trusted_windows.py` | Second implementation against production: chain, α_c, flows, window-by-window Δ_E (note §8.1). |
| R5 | `method_comparison/compare_methods.py` | NRG against the 1D Monte Carlo table and the ε series: optimal truncation and Borel–Padé (note §8.2–8.3). |
| R6 | `code/analysis/note_numbers.py` | Every other table and every in-text number of the note (`note/tables/numbers.tex`, as `\nrg…` macros). |
| R7 | `code/analysis/check_figures.py` | The local-exponent figure `fig_flow.pdf` and the comparison figure `fig_checks.pdf`. |
| R8 | `verify/verify.py` | Compares R1–R7 with the released files and with `verify/expected.json`, recomputes every NRG number the paper prints (`verify/quoted_numbers.json`; map: `results_map.md`) and writes `.work/reproduced/VERIFY.md`. |

Expected output: `VERIFY: 77 PASS, 0 FAIL`, or `76 PASS, 0 FAIL, 1 SKIP` if `NRG/` was copied without `../paper`. The
checks are listed in §6. Tested with Python 3.10–3.12, NumPy 1.24.4–2.3.5
and SciPy 1.11.4–1.17.1 on macOS arm64 and Linux x86-64 (AMD and Intel). With Python 3.10, NumPy 2.2.6 and SciPy 1.15.3
on macOS arm64 the files are identical to the released ones; elsewhere some fitted values and rounding-level differences
change in their last bits, and every check still passes within its tolerance.

## 4. Smoke: a small validation run with expected output (`make smoke`, about 15 s)

Both solvers run one critical search at Λ = 3, s = 0.8, K = 16, n_b = 6, N = 40. This configuration is far from
converged; the run tests the code path, not physics.
- **Production solver:** `python -m lri_spin critical ...`, about 6 s.
- **Second implementation:** `independent_check/run_config.py toy40`, about 6 s.

`verify/smoke_check.py` compares both with `verify/smoke_expected.json` and with each other:

| check | expected | tolerance |
|---|---|---|
| α_c, production | 0.44159087373603123 | relative 1e-11 |
| quality range, production | [0.5436034735726518, 0.5439692843995563] | absolute 1e-7 |
| quality windows, production | 6 | exact |
| α_c, second implementation vs production | equal | relative 1e-11 |
| quality range, second implementation (h = 1e-10) vs production | equal | absolute 1e-7 |
| quality windows, second implementation vs production | equal | exact |

Expected output: `SMOKE PASS (8/8 checks)`. On the reference machines α_c agreed bitwise and the ranges agreed to 1e-8.

## 5. Production (documented; needs a Slurm cluster)

### 5.1 What ran

| campaign | item list (`inputs/items/`) | items | lanes (jobs) | thread-h | longest item | peak memory |
|---|---|---:|---|---:|---:|---:|
| example | `example_items.json` | 3 | 1 (569565) | 0.6 | 0.14 h | 93 MiB |
| ds13 | `ds13_items.json` | 146 | 5 (569572–569576) | 109.7 | 2.7 h | 310 MiB |
| Λ pilot | `pilot_items.json` | 18 | 1 (569602) | 12.9 | 0.9 h | 178 MiB |
| Λ follow-up | `followup_items.json` | 30 | 2 + 2 after a node failure (569626/7 → 569640/1) | 54.5 | 2.7 h | 495 MiB |

Notes on the table:
- **Cluster.** All jobs ran on the *symmetry* cluster (Perimeter Institute): AMD EPYC 7543 nodes, 64 cores and 240 GB
  each, whole-node allocations: validation and drills on 2 October 2026, production on 3–4 October.
- **Totals.** 178 thread-hours (sum of item wall time × threads), out of about 15 node-hours of whole-node allocations
  (including validation and smoke jobs), i.e. about 970 core-hours as charged for 64-core nodes. The longest item took
  2.7 h; the production finished within two days, including a 22-hour cluster outage.
- **Item lists.** `code/campaigns/make_*_items.py` regenerate the ds13, pilot and follow-up lists byte for byte. They write
  `<name>_items.json` into the current directory: run them in an empty directory. `example_items.json` (the package's
  example list) and `smoke_items.json` were written by hand.
- **Thread counts.** Each item uses 1 thread if K·n_b ≤ 1000, 2 if < 1600, and 4 otherwise. The three example items
  ran on 2 threads, as in the package's example list; they duplicate ds13 items run on 1 thread, with α_c equal bitwise
  at s = 0.8, 0.9 and to 3e-14 at 0.98.
- **Smoke lane.** `inputs/items/smoke_items.json` is the small item list used for the smoke lane before production.

### 5.2 Validate and freeze

1. Copy `code/lri_spin_boson_hpc` to the cluster as a **read-only** directory. Keep `GIT_SHA` in it.
2. On a compute node of the partition you will use, run the test suite and issue a receipt (`slurm/validate.sbatch`):
   `python tests/verify_manifest.py && python scripts/validate_release.py --output <dir>/receipt.json`.
   The receipt binds the source hash to that node's runtime. Every item refuses to run on a different runtime.
3. Freeze each item list against the receipt on the login node:
   `python scripts/make_manifest.py --items inputs/items/ds13_items.json --receipt <receipt> --output <manifests>/ds13.json`.
   Do the same for the example, pilot and follow-up lists. The frozen manifests in `inputs/manifests` contain exactly
   these items with the same source hash.

### 5.3 Run

- **On symmetry, as in production**, with the lane tools (`code/lri_spin_boson_hpc/docs/SYMMETRY.md`). They pack many
  items per whole node and add cross-node item ownership, because the cluster file system has node-local locks.
  1. `python scripts/symmetry_submit.py init --campaign <base>/campaigns/ds13`
  2. `python scripts/symmetry_submit.py submit --campaign … --manifest … --receipt … --lanes 5 --time 24:00:00 --dry-run`,
     then the same command without `--dry-run`. The original lane counts are in §5.1.
  3. `python scripts/symmetry_status.py --campaign … --manifest … --receipt …` to monitor.
  4. `python scripts/symmetry_submit.py resubmit …` after a timeout, node failure or interruption. It reclaims only jobs
     confirmed dead and resumes from checkpoints in a new generation.

  The settings are in `cluster/symmetry/site.json` and `env.sh`: login host, partition, the excluded AVX-512 node, and
  the environment. On another cluster with these tools, work in a copy of the repository: pass your own site file with
  `--site`, adapt `env.sh`, then regenerate `MANIFEST.sha256.json` there, or `verify_manifest.py` will refuse the edited
  file.
- **On any other Slurm cluster**, use `slurm/items_array.sbatch`, one item per array task (`slurm/README.md`). The
  solver checkpoints every 8 sites, traps Slurm's warning signal, and resumes with `--resume`. An item that is already
  complete returns at once.

### 5.4 Collect

- **Lane tools:** `python code/analysis/collect_records.py <code>/src <campaign root> <manifest> <receipt> <out>/records`
  for each campaign. It copies the newest gated record of every item and writes `INDEX.json` with its generation.
- **Array route:** copy `<OUTPUT_DIR>/<item id>/result.json` to `<out>/records/<campaign>/<item id>.json`. This route
  writes no `INDEX.json`; `summarize.py` does not need it.

Then, **in a copy of the repository** (never in this one), replace `data/records`, `inputs/manifests` and
`inputs/validation_receipt/receipt.json` with yours, and run `make replay` there. Step R1 verifies every record against
your manifests and receipt. The analysis expects all four campaigns, under exactly these names (manifests and record
folders): `example_K64_B10`, `ds13`, `lambda_pilot`, `lambda_followup`. A partial rerun cannot be replayed as it stands.

### 5.5 Expected agreement with the released results

Records are bound to the runtime: Python, NumPy, SciPy, and the BLAS version and kernel.
- **Same runtime and thread counts:** reruns are bitwise identical, and `make replay` passes unchanged.
- **Other runtime:** rounding differences grow along the relevant direction as Λ^(y_t n). So:
  - α_c moves at the 1e-13 level;
  - flows at a fixed α differ late in the chain;
  - V1/V2/V7 of `make replay` will report differences beyond their tolerances. That is expected.

  Compare `.work/results/ds13_final.json` with `results/ds13_final.json` field by field instead:
  - Δ_E typically agrees to 1e-6 or better at the plateau points;
  - if the settled window moves by one site, Δ_E can move by up to the plateau drift, and an extrapolated value by up
    to the spread of its fits;
  - a difference larger than the point's `total` is a failure to report. Report it; do not tune the estimator.

### 5.6 The second implementation

`slurm/independent_check.sbatch` reruns c1–c8 on one node: 8 single-core processes, the longest about 28 min. Copy the
resulting `out/c*.json` over `independent_check/out/` in a copy of the repository, then run `make replay`. When running
`independent_check/run_config.py` by hand, always pass `--outdir`: its default is `independent_check/out`, which holds the
released outputs. The comparison scripts write into `.work/` unless `--out` is given. R4 compares
them with the production records. Expected: chain coefficients to rounding (below 1e-15); α_c bitwise or to about 1e-13;
trusted-window Δ_E to 3e-7.

## 6. Checks

`make replay` → `.work/reproduced/VERIFY.md`. Why tolerances: the extrapolations of `estimator.py` and `crosscheck.py`
are least-squares fits. Different NumPy/SciPy builds and CPUs change their last bits, which the fits amplify to about
1e-10 in the values (and more in poorly determined fit parameters). Where a fit is not determined at all (Δσ = 0.001)
the extrapolation is reported as `null` ("n.d.") instead of a number.

| check | compares | tolerance | expected |
|---|---|---|---|
| V0 | the SHA-256 of `src/lri_spin` against the receipt | exact | PASS |
| V1 | `results/*.json` and `.md` against the recomputed files | JSON floats to 1e-8 + 1e-6 relative (fitted ω and residuals: 1e-3 relative; cross-check fits: 1e-5); `.md`: numbers within one unit of their last printed digit | PASS |
| V2 | `note/tables/*.tex` (15 files) against the recomputed files | numbers within one unit of their last printed digit | PASS |
| V3 | `independent_check_compare/*.json`, `*.md` | JSON floats to 1e-14 + 1e-12 relative; `.md` as V1 with an absolute allowance of 1e-14 (the chain comparison is recomputed with the closed form, whose last bits depend on the platform's libm) | PASS |
| V4 | `method_comparison/comparison.json` and `.md` | floats to 1e-9 + 1e-9 relative; `.md` as V1 | PASS |
| V5 | `note/figures/*.pdf` regenerated | exists, non-empty (figures are not compared byte for byte) | PASS |
| V6 | the note: every `\nrg…` macro defined, every table and figure present | exact | PASS |
| V7 | the 47 published values in `verify/expected.json`: Δ_E and total error at the 10 final points, the settled values at the 3 points not converged in chain depth, the second-implementation maxima, the series references | per value: 1e-9 for the NRG values (least-squares fits), 1e-15 to 1e-8 for the rest | PASS |
| V8 | the 14 NRG macros the paper prints and 2 statements it makes without a number (`verify/quoted_numbers.json`, `results_map.md`), each recomputed from the files of R2, R5 and R6; one more row compares the listed texts with `../paper/numbers.tex` and checks that the `\NRG` macros printed by `../paper/main.tex` and `sections/` are exactly those listed | counts and labels equal; numbers equal or within one unit of their last printed digit, exponents equal | PASS (the paper row: SKIP without `../paper`) |

Gates applied to every record at production time and re-applied by R1:
- eigen-residual ≤ 1e-8 and orthogonality error ≤ 1e-9 at sites 0, 1, 2, every 16th site and the last;
- finite observables and sorted spectra;
- boson occupation in [0, n_b − 1] and top-level probability in [0, 1];
- for the derivative, a positive gap between kept and discarded levels.

The bisection must also reach a width of 5e-14·max(1, α). The workflow enforces this at production time and rejects an
exhausted bisection. In the released records the largest relative bracket width is 4.7e-14, recorded as
`bracket_width` in the summaries.

## Decisions you must not make

Stop and ask the author before any of the following.
1. Changing the estimator (`code/analysis/estimator.py`, note §3.7): the settled-window rule, the plateau threshold
   τ = 5e-5 and the neighbourhood h = ⌈w/4⌉, the extrapolation form, its fit ranges S = 30, 25, 20 and end point; or the
   window audit (width and range, thresholds variation < 0.005 and fit residual < 0.003); or the bisection convention
   (fraction 0.3, bracket [0.01, 2], tolerance 5e-14); or the error budget (its components, the linear sum, the
   K-doubling allowance at Λ = 2.5). Going back to the superseded quality-range midpoint is such a change.
2. Choosing a different central item (Λ = 3, K = 128, n_b = 16), or dropping or adding items in the error budget, after
   seeing their effect.
3. Changing the status of Δσ = 0.249, 0.24 or 0.225 ("not converged in chain depth": settled value shown, no error, not
   used in any comparison), using them in an agreement statement, adopting their extrapolations or the detuning
   cross-check fits of `crosscheck.py`, or replacing them with series values.
4. Presenting the total error as a standard deviation or a confidence interval, or combining it in quadrature with the
   Monte Carlo σ_sys. Presenting a Monte Carlo value labelled CROSS-CHECK FAILED or CONDITIONAL as an infinite-size
   value (the MC folder's own rule).
5. Editing a hash-bound file (records, manifests, receipt, `src/lri_spin`), or re-issuing a receipt so that edited
   records pass.
6. Re-running on another machine in order to change a value, or choosing the platform whose result you prefer.
7. Spending cluster time beyond the stated cost: about 180 thread-hours for the full production and under 1 node-hour
   for the second implementation.
8. Deleting or overwriting any record.
