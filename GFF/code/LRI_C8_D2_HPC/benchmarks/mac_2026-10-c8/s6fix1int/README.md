# Stage-6 fix round 1: integration on the Mac (2026-10-05/06)

The four group branches `fx1-g1` (5b8caf5), `fx1-g2` (38b47ee), `fx1-g3` (73501f1) and `fx1-g4` (824fa75), each from
e88bf4f, merged into `c8` as 2741bc2, 8494fd2, cd7e5de and 997eb6a. Only `DELIVERY_MANIFEST.json` and `SHA256SUMS`
conflicted; each merge commit regenerated them (`tools/verify_delivery.py --write`, then `--strict`). `src/` is
unchanged against e88bf4f (`git diff e88bf4f -- src/` is empty). The integration commit c30bfc5 adds the cross-group
fixes below. Mac (arm64), `<HOME>/anaconda3/bin/python3` (3.10.11), `C8_ALLOW_NO_L8=1`, `OPENBLAS_NUM_THREADS=1`.

## Cross-group fixes (c30bfc5), each with its before/after test

| Fix | Test | Before | After |
|---|---|---|---|
| G3's patch: `tests/unit_orchestration.py` `route_b_records`' synthetic gate record carries the X1/X2/X3 evidence (+5 refusals) | `unit_orchestration.py --only route_b_records` | fails on 997eb6a (`check_gate`: no F1 coverage, no build binding, no verified team sizes) | passes (44 refusals) |
| ast_scan over `gen/*.py` and `tests/*.py` (G4's analyser on G1/G3 code): `gen/regress.py` (`threads`/`loops` after `ap.error`), `tests/numerics_flags.py` (`snap`/`info`/`ex` under `want_f1`), `tests/validate.py:297` (`free8`/`g8` under `have8`, pre-existing) restructured; the scan added to `make test-python` | `tests/ast_scan.py gen/*.py tests/*.py` | `ast_scan_gen_tests_before_997eb6a.json`: 20 findings in 44 files | `ast_scan_gen_tests_after.json`: 0 findings |
| `gen/test_handoff_inventory.py` added to `make test-python` (G1's suggestion) | the target itself | not run by `make test-python` | 17/17 |
| `tools/verify_delivery.py` `safe_file`: every component of a listed path checked for a symlink (G4's observation) | `tests/test_delivery_verifier.py` `dir_symlink_component_listed_rejected_{strict,default}` | `test_delivery_verifier_before.txt`: the strict case sees only "1 unexpected files", default mode passes | `test_delivery_verifier_after.json`: 33 cases pass |

## `make test-python` on c30bfc5's tree (`test_python/`)

All passed (`exit 0`): check_venv; unit_orchestration 49 groups / 61 tests, 0 failed (the new G2 groups
`runtime_identity`, `bundle_relocation`, `cost_numerics`, `amd_cap_template`, `acct_partition`, `lane_fail_recheck`,
`seedsync`, and `route_b_records` with G3's patch); test_pipeline 3 parts / 27 tests; ast_scan (tools/*.py, 27 files,
0 findings) and ast_scan over gen/ and tests/ (44 files, 0 findings); test_regress 86/86; test_handoff_inventory 17/17;
merge_scale; check_vendored 29/29; vendored_isolated 10/10; the delivery-verifier test; check_inputs 17/17;
test_profiling 15; test_gmp_prefix 7; test_numerics_flags 11/11; test_dd_profile 8/8; sanitize `--capture-check`.

The cluster side (J-VAL-1 `make test`, J-GEN-1 with `gen/test_keys.py` under GCC 11.4, the build and A-RPL-8, the
re-run gate, the X8 real-Slurm check, the route-(b) re-freeze) is in `../../symmetry_2026-10-c8/s6fix1/`.
