# F11 fix and route (b): the Mac suite (2026-10-05)

Commit 23540b2 on `c8` (`tools/design.py`, `tools/production.py`, `tools/sweep.py`, `tests/test_pipeline.py`), on the
Mac (arm64, anaconda Python 3.10.11, numpy 1.23.5, scipy 1.10.0, pytest 7.1.2), `C8_ALLOW_NO_L8=1
OPENBLAS_NUM_THREADS=1`. No cluster job ran. No file under `src/` changed (D1). What the change does to J-DES-5's
designs and the cost table: `../../symmetry_2026-10-c8/stage5/pre6/README.md`.

## Results

| Command | Result |
|---|---|
| `tests/test_pipeline.py` | **20/20** in 4:44 (`test_pipeline.json`; 16 before). New: `F11_…` (a synthetic full-size pilot reproducing F11: the old rule at 2.85× the independently recomputed continuous optimum with r = 128 at free L8, the fixed rule at 1.09× with r = 32 and the primitives at s = 8; the target met; the SE recomputed from the bundle's counts), `route_b_synthetic_…` (in process: a non-uniform profile cost model re-costs the design, recomputed independently; σ kept; the record; the re-costed report; 21 refusals), `route_b_cli_test_only_…` (sweep.py `--numerics` and its two refusals, freeze, plan, run, merge, assemble under `dd+mp256`; combine refuses it with an exact batch), `route_b_non_test_…` (a non-test plan accepts the route-(b) bundle with every piece and records `numerics_route`; 6 plan refusals, the ungated build, 4 freeze refusals). The F11 rule is also checked independently on the A-DES-1, A-DES-6 (d = 3, imputed subsample) and route-(b) bundles |
| `tests/unit_orchestration.py` | 41 groups, 53 tests, all passed (`unit_orchestration_status.json`), 419 s |
| `tests/ast_scan.py` | 27 files, 0 findings |
| `gen/test_regress.py` | 42/42 |
| `tests/merge_scale.py --rows 20000` | passed |
| `tests/check_vendored.py`, `tests/vendored_isolated.py` | 17/17, 10/10 |
| `tests/test_delivery_verifier.py`, `tests/check_inputs.py` | passed; 11/11 (2 skipped: no L8 packs on the Mac) |
| `tests/test_profiling.py`, `tests/test_gmp_prefix.py`, `tests/test_numerics_flags.py`, `tests/test_dd_profile.py` | 15, 7, 8, 8 passed |
| `tests/sanitize.py --capture-check` | passed (the probe's report lost on a pipe, read on the pty) |
| `tests/check_venv.py` | passed (numpy, mpmath, sympy below their minimums on the Mac: reported, not failed without `--strict`) |
| `tools/verify_delivery.py --write`, `--strict` | 8,258 payload files, 0 errors, 0 extra (before the commit) |

`suites_summary.txt`: exit code and seconds of each suite command.

## Owed on the clusters

Nothing new for the default path (no `src/` change; the default executables are unchanged). The Stage-6 inspection
covers the change. After it: J-VAL-1 on the approved commit (its `make test` runs `test_pipeline.py`), and, before a
route-(b) production, one sweep under `dd+mp256` on symmetry for the profile cost model. The changed `production.py`
is a pinned tool: the two planned pilots were already owed a re-plan (`docs/HPC.md`, "Pilot runbook").
