# Stage-6 fix round 1, verifier residuals V1-V4 on the Mac (2026-10-06)

The fix-round-1 verifier (READY) listed four LOW residuals on bc23eee. Each is fixed with a test that fails on
bc23eee's code and passes after (`CHANGELOG.md`, entry "Stage-6 fix round 1, verifier residuals"). No `src/` change,
no job. Mac (arm64), `<HOME>/anaconda3/bin/python3` (3.10.11), `C8_ALLOW_NO_L8=1`, `OPENBLAS_NUM_THREADS=1`.

| Item | Fix | Test | Before (bc23eee's code, the new test) | After |
|---|---|---|---|---|
| V1 | `tools/production.py` `gate_evidence_missing`, called by `route_b` for every plan of a route-(b) bundle: each gate entry needs `F1_coverage` (free and power at the need), `source_snapshot_sha256`, `F5_team_sizes_verified` true | `tests/unit_orchestration.py --only route_b_records`: 10 synthetic gate entries x 3 call modes, the 4 pre6b bundles (gate 570210, `test_only` forced false) x 2 refused; the 4 bundles of 570379 (gate 570373) plan, non-final and final | `before_route_b_records.{txt,json}`: route_b accepts a gate entry without `F1_coverage` | passes, 82 refusals (44 before the residual) |
| V2 | `tests/numerics_flags.py`: a reused `--f1-baseline` must name this run's source snapshot (checked right after the snapshot, before any build or output); `tools/design.py` `gate_binding`: `F1.baseline_binding.snapshot_sha256` = `build_binding.snapshot.sha256` | `tests/test_numerics_flags.py --only coverage,binding`: two `check_gate` refusals, the real 570373 record accepted; a baseline bound through another or no snapshot refused with no output, the same baseline from this snapshot passes the check | `before_numerics_flags_coverage_binding.{txt,json}`: `check_gate accepted baseline_snapshot`; the harness ran on (`b_snap`) | both pass |
| V3 | `tests/ast_scan.py`: an annotated attribute or subscript target without a value loads its base and index | self-test, 5 new probes | `before_ast_scan_selftest.{txt,json}`: 3 probes missed | self-test passes; 27 tools files and 44 gen/tests files, 0 findings |
| V4 | `tools/vendor_assembly.py`: the vendored module is executed from its staged bytes and its interface checked before the first write | `tests/check_vendored.py` sandbox: a module lacking `slots`, a module that raises at import | `before_check_vendored.{txt,json}`: both refused only after writing `vendor/` (29/31) | 31/31 |

## `make test-python` on the commit's tree (`test_python/`, log `make_test_python.log`)

`C8_ALLOW_NO_L8=1 make test-python PYTHON=<HOME>/anaconda3/bin/python3`: exit 0. check_venv; unit_orchestration
49 groups / 61 tests, 0 failed; test_pipeline 3 parts / 27 tests; ast_scan (27 files) and ast_scan over gen/ and
tests/ (44 files), 0 findings, self-test passed; test_regress 86/86; test_handoff_inventory 17/17; merge_scale;
check_vendored 31/31; vendored_isolated 10/10; test_delivery_verifier 33 cases; check_inputs 17/17 (2 skipped: the L8 packs
and the inventory8_d2 regeneration); test_profiling 15; test_gmp_prefix 7; test_numerics_flags 11/11; test_dd_profile 8/8; sanitize
`--capture-check`. Then `tools/verify_delivery.py --write` and `--strict` pass.
