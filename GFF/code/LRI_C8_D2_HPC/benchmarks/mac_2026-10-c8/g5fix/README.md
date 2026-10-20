# G5 fixes F1-F9 and A-PERF-4: the Mac suite (2026-10-05)

Branch `fix-g5` from 950ecbb, on the Mac (arm64, anaconda Python 3.10.11, numpy 1.23.5, scipy 1.10.0, pytest 7.1.2),
`C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1`. No cluster job ran. No file under `src/` changed (D1).

## Results

| Command | Result |
|---|---|
| `tests/check_venv.py` | passed (numpy, mpmath, sympy below their minimums on the Mac: reported, not failed without `--strict`) |
| `tests/unit_orchestration.py` | 40 tests, 52 sub-tests, all passed (`unit_orchestration.json`); new: `recovery_merge` (F8), `lane_sigterm` (F7), `cpu_vendor` (F5), `claim_io` (F9); `claim` extended (F9), `lanes` pinned (F1) |
| `tests/test_pipeline.py` | 16/16 (with the J-SWEEP-2 rows in `tools/calibration.json`) |
| `tests/ast_scan.py` | 27 files, 0 findings |
| `gen/test_regress.py`, `gen/test_verify_inventory.py` | 42/42, 25/25 |
| `tests/merge_scale.py --rows 20000` | passed |
| `tests/check_vendored.py`, `--standalone` | 17/17, 14/14 |
| `tests/vendored_isolated.py` | 10/10 |
| `tests/test_delivery_verifier.py`, `tests/check_inputs.py` | passed; 11/11 (2 skipped: no L8 packs on the Mac) |
| `tests/test_profiling.py`, `tests/test_gmp_prefix.py`, `tests/test_numerics_flags.py`, `tests/test_dd_profile.py` | 15, 7, 8, 8 passed |
| `tests/sanitize.py --capture-check` | passed: the probe's report is lost on a pipe and read on the pty (F4) |
| `tests/assembly_checks.py --exact`, `tests/compat_2026.py` | 37/37, passed |
| `tests/verify_result_tamper.py` | 69/69 (`verify_result_tamper.json`) |

## The Stage-5 failures reproduced on the earlier code

- **F8.** `recovery_merge` with 950ecbb's `tools/production.py` fails at the merge job's
  "Checksum mismatch: .../groups/a_free_L3/graph_costs.csv"; with 950ecbb's `tools/assemble.py` (and the fixed merge)
  at "C8_test_result.json exists and differs from the recomputed result; not overwritten": the two J-DRL-8 stops.
- **F7.** `lane_sigterm` with 950ecbb's `tools/lanes.py`: the worker dies on SIGTERM while its lanes keep running, so
  the test times out (120 s). With the fix the worker exits 143 after 0.03 s (forwarded), or 3.26 s when the native
  ignores SIGTERM and the lane kills its run's session after 0.8 × 4 s.
- **F6.** `f6_residual_spread.json`: 13 Stage-5 results assembled on AMD Zen 2/3 nodes (the symmetry
  `raw_evidence.tgz` campaigns and the Expanse t2-t4), recomputed here: 950ecbb's `verify_result.py` rejects 8 of them
  on the Mac; the fixed one accepts all 13. The largest spread is 6.50 eps M_k (drill drA), and 0.47 eps M_8 for the
  smoke on the symmetry Cascade Lake login node, against the bound of 64. Three of the results are now test fixtures
  (`tests/fixtures/verify_result_cross_machine/`).

## Owed on the clusters

J-VAL-1 (`make test`, a whole amdq node: F1-F4 and the Linux paths of the F5/F9 tests, the cross-campaign non-own
comparison included) and J-EXP-1 (Expanse debug); `sanitize.py --selftest` on GCC 11.4 (F4); the smoke result
re-verified on the symmetry login node (F6); a scancelled lane-worker drill (F7); J-DRL-8 (F8); a J-SMK-4-type run
evaluated with `tools/claim_io.py` (F9); a cross-vendor refusal drill (F5); the J-VAL-3 assembly checks on the final
commit. Both planned pilots pin the earlier tools: re-export, then re-plan with fresh seeds.
