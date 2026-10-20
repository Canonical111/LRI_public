# F13, the F11 follow-up and the allow-list scope: the Mac suite (2026-10-05)

The fix before the Stage-6 inspection on `c8` (parent d8ba6a2): `tools/design.py` (the integer optimizer and route
(b)'s keep-cheaper), `tools/production.py` (the allow-lists bind every non-test plan), `tests/test_pipeline.py`, docs.
Run on the Mac (arm64, anaconda Python 3.10.11, numpy 1.23.5, scipy 1.10.0, pytest 7.1.2), `C8_ALLOW_NO_L8=1
OPENBLAS_NUM_THREADS=1`. No cluster job ran. No file under `src/` changed (D1). What the change does to J-DES-5's
designs: `docs/DESIGN.md`, "Route (b)" (the table), and `test_pipeline.json` (`F13_J-DES-5_records_…`, `table`).

## Results

| Command | Result |
|---|---|
| `tests/test_pipeline.py` | **23/23** in 6:02 (`test_pipeline.json`; 20 before). New: `F13_F11_optimizer_randomized_…` (2,000 seeded random stratum sets at a target: the optimizer feasible and never costlier than either old rule's final design, recomputed by hand; the rules differ in 561 sets and the old F11 rule alone is costlier than the Stage-5 rule in 16, up to ×1.21; 600 sets at a budget: within the budget, never less precise, 45 refused exactly as the old rules refuse them), `F13_J-DES-5_records_…` (J-DES-5's strata from the committed records of job 570241: the frozen numbers reproduced, the optimizer's exact path 1,702 / 5,740 / 22,961 / 74,573 and route (b) 638 / 2,241 / 8,963 / 29,328 lane core-hours, the keep-cheaper choice by hand), `allow_list_non_test_…` (7 non-test refusals: `plan --pilot --numerics` dd, mp256, exp1, dd+exp1, dd+mp256+exp1 and route-(a) `plan --design` under dd and dd+mp256+exp1; a test-only dd plan accepted). Changed: every target bundle is checked by `check_optimizer` (the target met; never costlier than either old rule's greedy design; no cheaper feasible single halving or halve-one-double-another move), the F11 case (the optimizer at 1.07× the continuous optimum, the F11 greedy design 1.09×, the old rule 2.85×), route (b) in process (the keep-cheaper choice recomputed independently, both branches exercised: a second profile keeps the exact allocation at one target and re-optimizes at a tighter one) and on the command line (the kept branch chosen there), the A-FLAG-6 non-test acceptance with `APPROVED_RATES` monkeypatched by a wrapper and the unpatched non-test pilot and batch under the map refused |
| `tests/unit_orchestration.py` | 41 groups, 53 tests, all passed (`unit_orchestration_status.json`), 517 s |
| `tests/ast_scan.py` | 27 files, 0 findings |
| `gen/test_regress.py` | 42/42 |
| `tests/merge_scale.py --rows 20000` | passed |
| `tests/check_vendored.py`, `tests/vendored_isolated.py` | 17/17, 10/10 |
| `tests/test_delivery_verifier.py`, `tests/check_inputs.py` | passed; 11/11 (2 skipped: no L8 packs on the Mac) |
| `tests/test_profiling.py`, `tests/test_gmp_prefix.py`, `tests/test_numerics_flags.py`, `tests/test_dd_profile.py` | 15, 7, 8, 8 passed |
| `tests/sanitize.py --capture-check` | passed (the probe's report lost on a pipe, read on the pty) |
| `tests/check_venv.py` | passed (numpy, mpmath, sympy below their minimums on the Mac: reported, not failed without `--strict`) |
| `tools/verify_delivery.py --write`, `--strict` | run before the commit (the commit message gives the counts) |

`suites_summary.txt`: exit code and seconds of each suite command. A comment-only edit of `tools/production.py` (the
`APPROVED_PROFILES` comment) landed while `unit_orchestration.py` ran; `test_pipeline.py` ran on the final tree.

## Owed on the clusters

Nothing new for the default path (no `src/` change; the default executables are unchanged). The Stage-6 inspection
covers the change. After it: J-VAL-1 on the approved commit (its `make test` runs `test_pipeline.py`), and A-EXP-3 on
Expanse from a fresh export of the post-inspection commit. `production.py` is a pinned tool: the two planned pilots
were already owed a re-plan with fresh seeds (`docs/HPC.md`, "Pilot runbook"). `tools/design.py` changed, so the H6
handoff to C8(3) is re-issued after Stage 6.
