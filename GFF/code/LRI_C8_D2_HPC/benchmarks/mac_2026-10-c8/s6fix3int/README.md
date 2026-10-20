# Stage-6 fix round 3: integration on the Mac (2026-10-06)

The four owner groups of fix round 3 (G1 5c8779e, G2 f241669, G3 c082065, G4 7b54923, each from a42cfb7) were merged
into `c8` as 6ad5635, 256f4f8, d20262e and f3d0dc2 (each merge with `DELIVERY_MANIFEST.json` and `SHA256SUMS`
regenerated, `verify_delivery --strict` passing). This folder holds the Mac evidence of the integration commit: the
cross-group needs the groups listed, the same defect classes nearby, and the docs (`CHANGELOG.md`, entry "Stage-6 fix
round 3"). Mac (arm64), `<HOME>/anaconda3/bin/python3` (3.10.11), `C8_ALLOW_NO_L8=1`, `OPENBLAS_NUM_THREADS=1`.
No cluster job here: the symmetry validation of the commit is `../../symmetry_2026-10-c8/s6fix3/`.

"Before" runs: a `git archive f3d0dc2` export (the four merges) with only the changed test files copied in
(`tests/unit_orchestration.py`, `tests/test_numerics_flags.py`, `tests/test_gmp_binding.py`, and the 570241 evidence
copy of the old profile cost model); the export's path is written `<f3d0dc2-export>` in `before_f3d0dc2/`.

| Item | Fix (integration) | Test | Before (f3d0dc2's code, the new test) | After |
|---|---|---|---|---|
| Z3, G1 → G2 | `tools/production.py` `read_build_record`: every plan refuses a record that lists `macro_overrides` (even with `development` edited to false); a non-test plan also refuses one whose `macro_overrides` is not a list (null: the compiler probe did not run; absent: a record made before fix round 3). The fake build records of the tests carry `macro_overrides: []` | `unit_orchestration` `z3_build_record` (4 new cases: a listed macro, null, absent, and a test-only plan with a listed macro) | `before_f3d0dc2/unit_orchestration.*`: the plan with `macro_overrides: ['C8_NX_SHARED_BEGIN']` and `development: false` was published (`z3_13`, exit 0) | passes |
| Z19 downstream, G1 → G3 | `tests/numerics_flags.py` records `f1_baseline.reused` and the baseline's `tool_gmp_library`; `tools/design.py` `gate_gmp_library` (in `check_gate`): the profile's `F1.tool_gmp_library` and the baseline's each matched (want, tool, worker_now) to its executable's recorded libgmp, `reused` a boolean, and for a reused baseline `reused_gmp_library` matched; `check_gate` returns `gmp_library`; `tools/production.py` `gate_evidence_missing` requires it of a bundle's gate entry | `test_numerics_flags` `coverage` (570210 now refused for six reasons; 570373 refused for exactly the three libgmp-provenance reasons and accepted with them added; 6 new refusal cases), `binding` (the reused-baseline record carries `reused` and `tool_gmp_library`); `unit_orchestration` `route_b_records` (14 new refusals: 11 `check_gate` cases, 3 gate-entry cases; the 570379 bundles refused for `570373 (no gmp_library)` and accepted with it) | `before_f3d0dc2/test_numerics_flags.*` (`coverage`: the 570210 record refused for 3 reasons only; `binding`: `KeyError 'reused'`), `unit_orchestration.*` (`route_b` accepted a gate entry without `gmp_library`) | passes |
| Z9's class (G3's note on G2's reader) | `tools/design.py` `parse_counts` (the reader of `design.read_bundle`, now shared) used by `tools/production.py` `read_bundle` | `unit_orchestration` `z9_plan_counts` (new): 9 malformed counts files with re-pinned digests (repeated graph, `+n`, 0, a tab, two spaces, a negative count, an extra field, no final newline, a blank line), each refused by `read_bundle` and by `plan --design` (nothing created) | `before_f3d0dc2/unit_orchestration.*`: `read_bundle accepted a counts file with repeated graph` | passes |
| Z2's consumers (G1's note) | `tests/forced_tiers.py` `coverage(rec, source_binding=True)`; `benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py` `forced_tiers_verdict` (status 'passed' AND `coverage(..., source_binding=False)` complete: those records predate Z1), used by it and by `stage5/exp/scripts/s5e_summary.py` | `test_gmp_binding` `forced_tiers_consumers` (new): every stored forced-tiers record (5) is accepted by the summaries' rule and refused by `--check` for the missing Z1 binding only; one sector, `--scale` and a development status with 'passed' edited in are FAILED | `before_f3d0dc2/test_gmp_binding.*`: `module 'summarize_final' has no attribute 'forced_tiers_verdict'` | passes; both summaries rerun without `--write` still pass (exit 0), with `forced_tiers_coverage` complete |
| G2's cross-group patch | `tests/test_pipeline.py` part 3: fake build records for the fake workers and profile copies; fresh seeds 89012 and 89033 for refusal cases after an accepted non-test plan registered its seed (Z15) (`LRI_C8_D2_HPC_loop/artifacts/s6_fix3_g2_test_pipeline.patch`, applied as is); the synthetic gate records carry the Z19 provenance (`gate_libraries`) | `test_pipeline` 3 parts | part 3 fails at its first non-test plan (no build record) on f3d0dc2 (G2's report) | passes |
| Replaced profile cost model | `tests/test_pipeline.py` `jdes5_records` reads the 9b0dfec6 model from the job's own evidence copy, `benchmarks/symmetry_2026-10-c8/pre6/p6des.570241.0/gmp_symmetry_amd_c8_dd+mp256.json` (added; the bytes of `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` at a42cfb7), because the installed model is re-measured on the new profile build | `test_pipeline` part 1 | (an enabling change, not a defect) | passes |
| Cluster loader comparison | `tests/test_native_guards.py`: `C8_GUARDS_OLD_TREE=<export of a42cfb7>` (with `<dir>.commit` naming a42cfb7) supplies the before-fix sources where there is no `.git`, so symmetry compares the loaders of this commit and of a42cfb7 on real L8 G-files | `C8_GUARDS_OLD_TREE=<a42cfb7 export> tests/test_native_guards.py --only hooks,loader` on the Mac: both pass with `before_fix` recorded from the export (`valid_files_byte_identical: true`, pattern init: "bad denominator size"); a directory without its `.commit` is refused | (a harness capability) | `test_native_guards_oldtree.json` |
| Python 3.11 warning | `tests/unit_orchestration.py`: `0.and` → `0. and` (noted in `../s6res2`'s symmetry run) | the suite | | |

## Docs

Z14 (`docs/DESIGN.md` step 2: confirmation from a report with the higher-point campaign as `--pilot`; `--nested` feeds
only α), Z15 (README quickstart, `docs/HPC.md` "The seed log", "Plan jobs" and the pilot runbook, `docs/DESIGN.md`
step 5, `slurm/plan.sh`'s header), Z16 (README quickstart: the pilot and batch plans in plan jobs), Z17 (`docs/HPC.md`:
the symmetry start-latency probe inside the cap), Z18 (`docs/NUMERICS.md` "Another GMP"), and Z1-Z13, Z19-Z22 in
`docs/NUMERICS.md`, `docs/HPC.md`, `docs/DESIGN.md`, `docs/PERFORMANCE.md` and `README.md`; the `CHANGELOG.md` entry.
The references that the new executables supersede (the 570373 gate record and its build `d5df32ac…`, the profile cost
model of job 570240, the 570379 bundles) now point to `benchmarks/symmetry_2026-10-c8/s6fix3/`.

## Suites on the integration tree

`C8_ALLOW_NO_L8=1 make test-python PYTHON=<HOME>/anaconda3/bin/python3 OUTPUT=<out>` on the commit's tree:
**exit 0** (`make_test_python.log`, records in `test_python/`): check_venv; unit_orchestration 67 groups, 79 tests, 0
failed (G2's 6 groups, the integration's `z9_plan_counts`); test_pipeline 3 parts, 35 tests (G3's 6 and G2's part-3
patch); ast_scan over tools/ (27 files) and gen/ + tests/ (47 files), 0 findings; test_regress 97/97 (Z5's 7 new);
test_handoff_inventory 17/17; merge_scale; check_vendored 36/36; vendored_isolated 10/10; the delivery-verifier test;
check_inputs 23/23 (2 skipped: no inventory tree, no L8 packs on the Mac); test_profiling 19 (G4's 3 new);
test_gmp_prefix 8 (`targets`: every test program in a make target); test_gmp_binding 14 (G1's 3 new and
`forced_tiers_consumers`); test_omp_launch 5; test_numerics_flags 12; test_dd_profile 8; sanitize `--capture-check`;
**test_native_guards 3/3** (new: hooks, loader, syntax with Apple clang for x86_64).

Outside `test-python`: `tests/verify_result_tamper.py` 206/206, `tests/combine_core.py` 14/14,
`tests/assembly_checks.py` 32/32, `tests/compat_2026.py` passed; every stored c8-d2 result (12 under `benchmarks/`, 4
in `tests/fixtures/verify_result_cross_machine/`) verifies with the merged `tools/verify_result.py`
(`test_python/verify_all.txt`; its 17th match is G3's driver script itself, which names the schema). The stored-record
summaries `stage4b/final/scripts/summarize_final.py` and `stage5/exp/scripts/s5e_summary.py --only zen2` rerun
without `--write` exit 0 with the new coverage check. `tools/verify_delivery.py --write` then `--strict` pass.

## After the symmetry J-VAL-1 (job 570534): the fake toolchain of `tests/test_gmp_binding.py` made hermetic

J-VAL-1 on the export of 9976391 stopped in `make test-python` at `tests/test_gmp_binding.py` `source_binding` (G1's Z1
test): symmetry's `env.sh` loads the Boost 1.77 module, which puts its headers on `CPATH`, and the test's `World` passed
the caller's `CPATH` to its fake compiler, so the "worker" was built against the host's Boost 1.77 instead of the fake
system Boost 1.74 the test assumes: the CPATH refusal named `'107700' for the worker` where the test expected
`'107400'`, and the CPLUS_INCLUDE_PATH case could not have changed the Boost found either. A test defect of
portability, not of the binding (the real refusal fired, for the right reason). Fix: `World.env` drops the inherited
include and library search variables (`build_record.INCLUDE_ENV`: CPATH, CPLUS_INCLUDE_PATH, C_INCLUDE_PATH,
LIBRARY_PATH, GCC_EXEC_PREFIX, COMPILER_PATH); a case sets them explicitly. Reproduced on the Mac with
`CPATH=<dir with a Boost 1_77 version.hpp>`: `hermetic/before_9976391_test_gmp_binding_source_binding_CPATH_boost177.txt`
fails exactly as on symmetry; after the fix `test_gmp_binding` passes 14/14 with that `CPATH`, with the same directory as
`CPLUS_INCLUDE_PATH`, and without either (`hermetic/after_test_gmp_binding_CPATH_boost177.txt`). The same class
elsewhere: `tests/test_numerics_flags.py` (its fake compiler reads no include path) and `tests/test_profiling.py` pass
with the same `CPATH`; `tests/test_native_guards.py` reads `CPATH` on purpose (Homebrew's Boost on macOS).

## The final suite (the evidence commit's tree)

After the symmetry runs (`../../symmetry_2026-10-c8/s6fix3/`), with the re-measured profile cost model installed, the
docs filled in and `tests/test_gmp_binding.py` `forced_tiers_consumers` generalized to the first stored forced-tiers
record made with the Z1 binding: `C8_ALLOW_NO_L8=1 make test-python` **exit 0** again (`final_test_python/`, its
`make_test_python.log`), every stored result verifies (`final_test_python/verify_all.txt`), and `verify_delivery
--write` then `--strict` pass.
