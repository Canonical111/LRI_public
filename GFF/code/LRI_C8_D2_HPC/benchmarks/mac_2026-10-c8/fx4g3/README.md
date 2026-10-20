# Stage-6 fix round 4, group G3: design, calibration, gate and delivery (2026-10-06)

Branch `fx4-g3` from 945e526, on the Mac (arm64, anaconda Python 3.10.11), `C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1`.
Items W10, W11 (the calibrate and sweep side), W12, W13, W18 and W20 of
`LRI_C8_D2_HPC_loop/artifacts/s6_fix4_dispositions.md` (findings S6D-R4-01..04, S6G4-01, S6H4-01, S6H4-03). Changed:
`tools/calibrate.py`, `tools/sweep.py`, `tools/design.py`, `tools/seeds.py`, `tools/verify_delivery.py`,
`tests/numerics_flags.py` and the tests `tests/test_numerics_flags.py`, `tests/test_pipeline.py`,
`tests/test_delivery_verifier.py`, plus `DELIVERY_MANIFEST.json`/`SHA256SUMS` and this folder. No `src/` change and no
cluster job: the default and profile binaries are untouched.

## The fixes

- **W10 (S6D-R4-01): calibration from validated checkpoints only.** `calibrate.measure` streams each index's
  authenticated task file (`production.iter_job_blocks`) and validates every existing checkpoint with
  `production.validate_checkpoint` (manifest and config identity, executable, inputs, net, rates identity, the
  campaign's runtime identity, payload digest, metadata, coordinates, jets, counters, tail fields) before it reads a
  timing, as the merge does. Every row's `seconds` must be a finite non-negative number and each (campaign, sector, L)
  total positive. A refusal exits 2 and writes nothing.
- **W11 (S6D-R4-02), calibrate and sweep side: one measurement identity per calibration file.** `calibrate.update`
  (the writer, used by `--update` and the sweep) checks the destination with `check_destination`: the file's
  `identity` and every row's `source` (numerics, rates identity) must equal the new rows'; a file mixing identities is
  refused; `tools/calibration.json` takes only exact, default-rate rows. The file records `identity`. `sweep.py`
  checks the same before it plans anything, unless `--plan-only` (which writes no rows), so a `--rates` or
  `--numerics` sweep needs its own `--calibration FILE`. The planner side (`production.calibration_row` comparing the
  row identity with the plan's) is G2's.
- **W12 (S6D-R4-03): the batch search.** `design_for` searches up to `max(64, --batches)`. When no batch count meets
  the caps it says which case applies:
  - infeasible: the minimum design of one batch (r = `--min-replicates`, s = 1) breaks the caps, so no K helps;
  - a search limit: more batches would work. With `--batches` this is "--batches K is below the minimum batch count".

  The design of an explicit `--batches K` is checked against every cap before it is frozen.
- **W13 (S6D-R4-04, S6G4-01): delivered results are verified.** `DELIVERY_MANIFEST.json` gains `result_records`, the
  explicit set of delivered C8 result records. These are JSON files whose top-level schema is `c8-d2-hpc-result-1`;
  historical C7 records have another schema. The set is sticky: `--write` keeps every record an earlier manifest
  listed while the file is delivered. Both modes run the package's own `tools/verify_result.py` `verify()` on every
  listed record, in one subprocess, and fail on any problem. They also fail on:
  - a delivered record that is missing from the list;
  - a file that names the schema but does not parse;
  - a listed path that is not a payload file.

  `--write` verifies before it writes anything. Intentional negative fixtures are excluded only by name
  (`NEGATIVE_FIXTURES`, empty: none is delivered). The 16 delivered records verify.
- **W18 (S6H4-01): the gate's authenticated input set.** `tests/numerics_flags.py` records `inputs` (schema
  `c8-d2-gate-inputs-1`) before anything is built or written:
  - the sha256 of `inputs/manifest.json`'s bytes, with every listed input, pack and vendored pin hashed against it
    (`prepare_inputs.verify`). The manifest covers the payloads, gamma, two-loop data and assembly pins;
  - the L8 packs a machine lacks, as `skipped`, with `complete` false.

  The run verifies the inputs again at the end (`verified_at_end`); a change fails the record. A fresh F1 baseline
  records the same identity. A reused one must carry it, else the run refuses it before anything is written.

  `design.check_gate(path, profile, inv, inputs_manifest_sha256)` (`gate_inputs`) requires:
  - the identity of schema `c8-d2-gate-inputs-1`, verified at the start and at the end, and complete;
  - the identity equal to the expected inputs manifest: the pilot's in `freeze` (`profile_recost`), or the plan's. The
    plan's is the package's own `inputs/manifest.json` when the caller names none, as `production.gated_route` does now;
    every non-test plan uses that manifest;
  - an F1 baseline made from the same manifest.

  The returned gate entry, which a bundle records, carries `inputs_manifest_sha256`.
- **W20 (S6H4-03): one locked seed transaction.** `seeds.reserve` re-reads the log under its lock, runs the caller's
  collision check on that fresh log, and appends every missing entry with one replace before it releases the lock.
  Identical (seed, source) entries are 'present'. `register_f2_seeds` uses it (`f2_clashes`), refusing:
  - an archived C7(2) seed;
  - a seed logged under another source;
  - a derived C8 group seed of a logged campaign.

  Same class in `tools/sweep.py`: the registration is one `reserve` with `production.seed_refusal` on the fresh log
  (the sweep's own entry excluded), and a new sweep pre-checks its seed before planning.

**Job 570536** (the fix-round-3 dd+mp256 gate, record sha256 `a8de4037…`) passed `check_gate` at 945e526. Here it is
refused for exactly one reason: "no authenticated input-set identity". The same record with an identity of the
package's inputs added passes, and is refused for any other manifest. `test_coverage` checks all three. Its route-(b)
bundles (570539) carry gate entries without `inputs_manifest_sha256`. Refusing them at plan time is G2's change in
`production.route_b`. The gate must be re-run on symmetry, with a fresh F1 baseline (a reused one has no identity),
and the bundles re-frozen.

## Tests: each fails on 945e526's code and passes here

| Item | Test | Before (945e526) | After |
|---|---|---|---|
| W10 | `test_pipeline.py` `w10_calibration_checkpoints` (part 2) | `before_test_pipeline.txt`: a timing changed without its checksum is calibrated (exit 0, expected 2) | pass |
| W11 | `w11_rates_calibration` (part 2) | `sweep.py --rates` with the package calibration is planned, run, and writes the map's rows into it (exit 0, expected 1) | pass |
| W20 (sweep) | `w20_sweep_seed` (part 2) | a resumed sweep appends its seed beside another campaign's (exit 0, expected 1) | pass |
| W12 | `w12_batches` (part 1) | "no batch count up to 64 meets the per-batch caps", also with `--batches 128` | pass (K_min 92) |
| W18 | `test_numerics_flags.py` `coverage`, `w18_inputs`, `binding`; `test_pipeline.py` `route_b_synthetic`, `route_b_cli_test_only`, `pilot_exact_gated_nontest` | `before_test_numerics_flags.txt`: 570210 refused for 6 reasons, not 7, and there is no `input_identity`. `before_test_pipeline.txt`: freeze accepts a gate of the package's inputs for a fixture pilot, a plan accepts a gate of other inputs, and the gate entry has no `inputs_manifest_sha256` | pass |
| W20 (F2) | `test_numerics_flags.py` `w20_seeds` | a plan registering F2's base seed right after F2 read the log succeeds, and the log holds that seed under two sources | pass: the plan is refused under the lock |
| W13 | `tests/test_delivery_verifier.py` (7 new cases) | `before_verify_delivery_w13.txt`: `--write` and `--strict` pass a record without its gates block. `before_test_delivery_verifier.txt`: no `result_records` | pass |

"Before" runs: `before_driver.py` runs `test_pipeline.py` parts 1 to 3 on a `git archive 945e526` export with only
the new `tests/test_pipeline.py` copied in. Each new or changed test function is wrapped, so each fails or passes on
its own. `route_b_nontest` passes before as well: it gained only the gate's input identity, which the old
`check_gate` ignores. The `test_numerics_flags.py` "before" ran with 945e526's `tests/numerics_flags.py`,
`tools/design.py` and `tools/seeds.py`.

## Suites on the final tree (records in this folder)

| Suite | Result |
|---|---|
| `tests/test_pipeline.py` | 3 parts, 39 tests: the 35 of 945e526 (`base_test_pipeline.txt`) and the 4 new ones; W18 cases added to 3 existing tests; about 7 min |
| `tests/test_numerics_flags.py` | 14 tests: the 12 of 945e526 (`base_test_numerics_flags.txt`) and `w18_inputs`, `w20_seeds` |
| `tests/test_delivery_verifier.py` | passed, with the 7 W13 cases |
| `tests/unit_orchestration.py` | 67 groups, 78 tests, 77 passed. It is not this group's file, but it exercises the changed tools. The one failure is `route_b_records`: its synthetic `gate_doc` has no W18 `inputs` block, so `check_gate` refuses it as intended (cross-group; see the patch below). `omp_team` failed once while 3 suites ran in parallel; it passed alone (`unit_orchestration_affected.txt`) and in this final run |
| `tests/ast_scan.py` (tools) and over the 4 changed test files | 27 and 4 files, 0 findings |
| `tools/verify_delivery.py --write`, then `--strict` (before the commit) | passed: every payload file, 16 result records listed and verified, no extra file |
| stored results (`verify_result_all_stored_results.txt`, fx3g3's `verify_all.sh`) | 16 of 16 records verify. The 17th line is `verify_all.sh` itself: its grep matches the script, which is not a record |

`unit_orchestration_gate_doc_W18.patch`: the fix for that suite's synthetic gate record. It is not applied here,
because the file belongs to another group. With it, `route_b_records` passes (verified locally, then reverted).
