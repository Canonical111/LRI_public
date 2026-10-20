# Stage-6 fix round 2, verifier residuals R1-R3 (and the class-reader reservation) on the Mac (2026-10-06)

The fix-round-2 verifier (on a57e07f) listed three residuals of the defect classes Y2 and F6, and noted one LOW item.
Each is fixed with a test that fails on a57e07f's code and passes after (`CHANGELOG.md`, entry "Stage-6 residuals
after fix round 2"). No `src/` change, no job. Mac (arm64), `<HOME>/anaconda3/bin/python3` (3.10.11),
`C8_ALLOW_NO_L8=1`, `OPENBLAS_NUM_THREADS=1`; g++-16 (Homebrew GCC 16) for the generator.

"Before" runs: a `git archive a57e07f` export with only the new or changed test files copied in
(`tests/test_omp_launch.py`, `tests/verify_result_tamper.py`, the new fixture, `gen/test_keys.py`); the export's
path is written `<a57e07f-export>` below and in the `before_*` files.

| Item | Fix | Test | Before (a57e07f's code, the new test) | After |
|---|---|---|---|---|
| R1 | `tests/validate.py`: `harness_env` (`common.omp_child_env(threads, env, bind=False)`) for every native launch (`run`, `fresh_output` with `native_threads`, the refusal and inspector runs); the A-RPL-6 `invariance` runs through `team_run` (`omp_child_env(threads)`, the team watched with `common.TeamWatch`; records `teams_observed`, `team_sizes_verified`). Same class: `tests/forced_tiers.py` and `tests/numerics_flags.py` pass their tools' thread count; `tests/quad_differential.py` `run_json(..., threads)`; `tools/prepare_inputs.py` `inspect_pack`; `common.omp_child_env` gains `bind` | new `tests/test_omp_launch.py` (a stand-in worker that logs the OpenMP controls it gets and the team libgomp would give it; a simulated `/proc/<pid>/task`): `invariance`, `invariance_team`, `run_env`, `tools_env` | `before_test_omp_launch.{txt,json}`: 5/5 fail. With `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true OMP_NUM_THREADS=64 GOMP_SPINCOUNT=0 KMP_AFFINITY=none` inherited, every invariance run got those controls (the 4-thread runs a team of 1) and all 12 records said `thread_identical: true`; a runtime ignoring the request passed; `run(threads=)` and `run_json(threads=)` do not exist | `test_omp_launch.{txt,json}`: 5/5 |
| R2 | `tests/sanitize.py` `ENV` = `omp_child_env(4)` plus `ASAN_OPTIONS`, `UBSAN_OPTIONS`; record `omp_environment` | `test_omp_launch` `sanitize_env` (imports `sanitize` in a child with the controls above inherited) | `ENV` held `OMP_THREAD_LIMIT=1`, `OMP_DYNAMIC=true`, `GOMP_SPINCOUNT`, `KMP_AFFINITY` (same files) | passes |
| R3 | `tools/verify_result.py` "Pulls": `pull_bound` (the tolerance a pull's inputs' tolerances imply), `pull_bounds` in `_recompute`, `pull_problems` (a stored pull must be the pull of its stored inputs to 1e-12) | `tests/verify_result_tamper.py` (175 checks, 71 new) with the Stage-5 design-chain partial as a fourth cross-machine fixture (`tests/fixtures/verify_result_cross_machine/design_chain_k2_partial.json`) | `before_verify_result_tamper.{txt,json}`: 129/175; the fixture fails (`null_rows[1]/pull` 0.06239285349839986 against 0.062392853473700785), 22 consistent cross-machine moves (null rows 1 and 4, lower-order rows 0 and 3, result and test-only) are refused, the bound helpers are missing. `before_verify_result_design_chain_k2.txt`: the stored partial fails; `before_verify_result_all_stored_results.txt`: 2 of 16 fail (the partial and its fixture copy) | `verify_result_tamper.{txt,json}` 175/175; `verify_result_design_chain_k2.txt` verified; `verify_result_all_stored_results.txt` 16/16 |
| low | `gen/c8gen.hpp` `read_classes` reserves at most `CLASS_RESERVE_CAP` = 2^16 rows (classes8 has 26,540) | `gen/test_keys.py` `hostile_ng_checks`: an ASan build of test_keys, the header NG = 2^31-1 with one row, with and without `--generator`, under `ASAN_OPTIONS=max_allocation_size_mb=256` | `before_test_keys_gxx16.{txt,json}`: 113/115, both hostile cases abort in `read_classes` (operator new of 2^31-1 rows) | `test_keys_gxx16.{txt,json}`: 115/115 |

The generator binaries change in bytes only: `build_free` and `build_power` built with g++-16 from a57e07f and from
this commit write byte-identical outputs on classes3..6 (639 files, `diff -r`). R1-R3 have not run on symmetry: J-VAL-1
(`tests/validate.py` with `team_run`) and J-GEN-1 (the new generator bytes) are owed there.

Not changed by design (R1's search over `tests/` and `tools/`): one-thread launches (`tests/check_points.py`'s
point_checks has no parallel region; the C7-era `tools/profile.py` and `tools/benchmark_memory.py`; `gen/test_keys.py`),
compiles and `--describe` probes; `tests/thread_identity.py` keeps its own sanitized environment and team check (X3);
production, lanes, sweeps and the profilers were already controlled (Y2).

## `make test-python` on the commit's tree (`test_python/`, log `make_test_python.log`)

`C8_ALLOW_NO_L8=1 make test-python PYTHON=<HOME>/anaconda3/bin/python3 OUTPUT=<scratch>/test_python`: **exit 0** in
about 20 minutes (`make_test_python.log`, records in `test_python/`; run on the commit's code before its evidence was
added). check_venv; unit_orchestration 60 groups, 72 tests, 0 failed; test_pipeline 3 parts, 29 tests; ast_scan 27
files and gen/tests 46 files, 0 findings; test_regress 90/90; test_handoff_inventory 17/17; merge_scale;
check_vendored 36/36; vendored_isolated 10/10; the delivery-verifier test; check_inputs 23/23 (2 skipped: no
inventory tree, no L8 packs on the Mac); test_profiling 16; test_gmp_prefix 8 (its `targets` check covers the new
`tests/test_omp_launch.py`); test_gmp_binding 10; **test_omp_launch 5 (new)**; test_numerics_flags 11; test_dd_profile 8;
sanitize `--capture-check`.

Outside `test-python`: `tests/verify_result_tamper.py` 175/175; `gen/test_keys.py --bin <gen-g++-16> --cxx g++-16`
115/115 (with the UBSan part and the new ASan check). Then `tools/verify_delivery.py --write` and `--strict` pass.
