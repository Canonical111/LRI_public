# Stage-6 fix round 4, group G2: orchestration and generator (2026-10-06)

Branch `fx4-g2` from 945e526 (the tree inspected in round 4), on the Mac (arm64, anaconda Python 3.10, numpy, scipy;
Homebrew g++-16 for the generator tools), `C8_ALLOW_NO_L8=1`. Items W4, W5, W6, W7, W8, W9, W11 (the
`production.calibration_row` side), W23 and W24 of `LRI_C8_D2_HPC_loop/artifacts/s6_fix4_dispositions.md` (findings
S6R4-B-01, S6R4-B-02, S6R4-B-03, S6-C-R4-01, S6-C-R4-02, S6-C-R4-03, S6D-R4-02, and the host's residuals). No `src/`
change and no cluster job. The worker's command line, inputs and numerics are unchanged, so valid-input outputs are
bit-identical by construction; the plan writes the same per-index task files (now in pieces).

## The fixes

- **W4 (S6R4-B-01): `gen/gates.py` check_gfile reads a G-file as the loader does.** The file is read as bytes through
  `regress.gfile_text`: LF, spaces and printable ASCII only. Before, `read_text()` turned CRLF into LF, and the Z5
  token checks ran after `str.split()`, which also splits on U+00A0, the other Unicode separators and U+001C..U+001F,
  where the loader's stream extraction stops. The header's L, M and T must be within the loader's bounds
  (2 <= L <= 8, 1 <= M <= 16384, 1 <= T <= 10000); a header and inventory row of M = T = 0 passed before. The token
  rules (MASK_TOKEN, TERM_TOKEN, INT_RANGE) now live in `gen/regress.py`, and `regress.parse_gfile` applies the same
  reading (same defect class): ASCII without CR or control bytes, plain-decimal header counts within the bounds,
  plain-decimal weights and masks, term entries within the loader's int, and plain-decimal rates. A no-break space in a
  relabelled mask line, or a rate that is not a decimal, no longer passes as 'relabelled' or 'rate_only'.
- **W5 (S6R4-B-02): `gen/regress.py` byte identity is equality of bytes.** main reads both G-files with
  `read_bytes()`. `judge()` on bytes calls only equal bytes 'identical' and decodes everything else without newline
  translation (`gfile_text`), so CRLF or a lone CR is an 'other' (structure) difference. `header_inventory_mismatches`
  reads the header the same way.
- **W6 (S6R4-B-03): `gen/check_edge_forests.cpp` reads an existing G-file with checked extraction.** Every
  extraction is checked before its value is used, and every allocation is bounded by the loader's limits (M, T, and a
  denominator of 1 <= k <= M; the magic, L and id must be the class's). A malformed file is that graph's failure
  (`matches_induced` false, with an `"error"`). Any exception of one graph's check is caught inside the OpenMP loop
  body, so none escapes the parallel region. Before, M = -1 or k = -1 threw `std::length_error` out of the region
  (`std::terminate`, exit -6), a cut file read uninitialized counts, and a header naming another id passed. This is a
  generator-side tool; the worker is untouched.
- **W7 (S6-C-R4-01): no loader override for campaign workers; preload order in the identity.**
  - `common.loader_overrides` lists LD_PRELOAD, LD_AUDIT, LD_DYNAMIC_WEAK, DYLD_INSERT_LIBRARIES and
    DYLD_FORCE_FLAT_NAMESPACE when set, even empty. `production.py run` refuses (64, claim_io 'loader override
    refused') before anything is staged, pinned or run, and the lane worker refuses (64) before any claim.
  - `common.fingerprint` records `preload_order`: the path-keyed ldd entries (objects preloaded through
    /etc/ld.so.preload) in load order. It also records `loader_env` (GLIBC_TUNABLES when set).
  - `runtime_identity` includes each only when it is not empty, so the identity and key of an ordinary node are
    unchanged (checked field for field). `production._identity_diff` names them.
- **W8 (S6-C-R4-02): a gated profile executable is bound to its gate's libgmp.**
  - `production.gate_gmp_binding(m)` returns the gates' `gmp_library.profile` for the campaign's executable (None
    when the executable is not gated). A gated campaign whose gates record no libgmp is refused.
    `gmp_binding_problem` checks a runtime identity against it.
  - Plan: the binding is recorded in `numerics_route.gate_gmp_library`. A NON-test plan refuses a build record whose
    libgmp is not the gate's; a test-only plan warns.
  - Claim: a worker that loads another libgmp stops with 64 before any pin or block.
  - `validate_checkpoint(..., gmp_binding)` is used by run-skip, the duplicate check, the parallel merge and the
    serial merge. It refuses a checkpoint of another libgmp; in a NON-test campaign, also one whose identity names no
    libgmp. A test-only stand-in (no ELF: ldd unavailable, no libraries) is accepted.
- **W9 (S6-C-R4-03): streamed task rows; est_peak_bytes counts what a claim holds.**
  - `job_rows` and `blocks_of_rows` are removed. `snapshot_tasks` copies the index's task file into the job-private
    runtime in 256 KiB pieces, hashes it while copying, verifies it against the manifest pin and makes it read-only.
    `snapshot_blocks` streams the snapshot one block of T rows at a time.
  - claim_io counts the snapshot read as own bytes (`task_file_snapshot`).
  - `stage_runtime.stage` streams the index's graph set with `iter_job_blocks`.
  - The plan writes and self-checks each per-index task file in pieces of 200,000 rows (the same bytes).
  - `est_peak_bytes` adds `min(T, tasks) x TASK_ROW_PEAK_BYTES` (16 KiB per task of a block) and the plan metadata
    every claim parses (2 KiB per job entry and per inventory row).
- **W11 (S6D-R4-02), production side: calibration rows only under their own identity.**
  `production.calibration_row(..., numerics, rates_identity)` returns a row only when its `source` records the plan's
  numerics and rates identity. A row of another identity, or one recording none, is refused with both identities
  named. Before, an exact sweep under `--rates` that updated `tools/calibration.json` silently re-timed default-rate
  plans. The calibration writer is G3's.
- **W23 (host residual) and its class: nothing checked is read again.**
  - Coverage checks: `assemble.coverage_guard` and `combine.test_coverage` parse design_meta.json from one read
    verified against the campaign's pinned sha256 (`assemble.bundle_meta`, meta_sha256 passed by evaluate and
    load_batch). They parse the counts files from their verified bytes with `design.parse_counts`
    (`assemble.bundle_counts`).
  - Inventory: evaluate and load_batch take it from the bytes the campaign's inputs manifest pins
    (`production.verified_inventory`). So do `production.py run`, staging and `plan`; plan also verifies the inputs
    manifest under the sha256 it records.
  - Seeds: load_batch's group seeds come from the verified configs (`group_of`).
  - Assembly module and inputs: the order-8 module is executed from the verified bytes (never re-read by the import
    system), and the result records that sha256. `two_loop()` hashes the bytes it parses. Plan reads a rate map once.
  - Merge and lanes: the serial merge reads a verified private copy of tasks.sqlite, and a lane reads cost_model.json
    from verified bytes.
- **W24 (host residual): the accepted 570539 bundles in `route_b_records`.** The four evidence copies of
  `s6fix3/s3des.570539.0/design_meta_b_*.json` match `bundles.sha256`, and each one:
  - plans non-final and final as a NON-test plan with the gated executable a46f3060;
  - records the gates that 570539's test-only plans recorded;
  - binds the executable to libgmp 4dc20a90, which the symmetry nodes' identity (J-VAL-1 570376) loads. Another
    libgmp and another executable are refused.

## Tests (each fails on 945e526's tools and passes here)

| Item | Test | On 945e526 (`before_945e526/`) |
|---|---|---|
| W4 | gen/test_regress.py `gfile_gate_checks`, W4 part (14 checks) and the 3 W4 `judge()` checks | 13 FAIL (`test_regress.json`): U+00A0, U+001C, tab, CRLF, a CR and M = T = 0 accepted by check_gfile; a no-break space or a non-decimal rate passed as 'relabelled' or 'rate_only' |
| W5 | gen/test_regress.py, 6 `judge()` byte checks and 2 end-to-end `regress.py --loops 3` runs with a CRLF line end | 7 FAIL: `judge()` raised on bytes; both end-to-end runs passed (the CRLF file counted as identical) |
| W6 | gen/test_keys.py `edge_forest_gfile_checks` (9 malformed G18.txt and the clean tree; also through UBSan, and through ASan with max_allocation_size_mb=256, on symmetry) | 9 FAIL with the old `check_edge_forests` (`test_keys_old_check_edge_forests.json`): M = -1 and k = -1 abort (`std::length_error` out of the OpenMP region, exit -6), another id passes, no file is failed with its error |
| W7 | unit_orchestration `w7_loader` | FAIL (`unit_orchestration.json`): the claim ran under LD_PRELOAD. Per part (`w78_parts.json`): the lane worker ran (0), reversed preload order gave one identity, the reversed-order claim ran |
| W8 | unit_orchestration `w8_gmp_binding` | FAIL: the claim with libgmp Y ran. Per part: merges with jobs 1, jobs 2 and serial accepted the checkpoints of libgmp Y; the non-test plan accepted a build record of another libgmp |
| W9 | unit_orchestration `w9_stream`; `chunking` (the new est_peak_bytes); `claim_io` (`task_file_snapshot`) | FAIL: the one-block claim of the 131,072-task index peaked at 42.4 MB of traced Python memory against 6.9 MB for the 1,024-task index (now 7.8 and 6.9 MB). `chunking`: the old estimate. `claim_io`: no snapshot read |
| W11 | unit_orchestration `w11_calibration` | FAIL: the default-rate plan was made from rows of a rate map |
| W23 | unit_orchestration `w23_no_reread` (a)-(i) | FAIL. Per part (`w23_each.json`; (h) and (i) in `unit_orchestration.json` as `w23_h_only`, `w23_i_only`): every part (a)-(i) fails |
| W24 | unit_orchestration `route_b_records` (the 570539 block) | FAIL (no `gate_gmp_binding`). The 570539 acceptance itself also held before; W24 adds the coverage |

The per-part runs are scratch variants of the committed tests (`before_945e526/scratch_*.py`), run on a `git archive`
of 945e526 with the new tests copied in. They are not part of the package's tests. Measured by W9's test with
tracemalloc (fake worker, Python 3.10):
- the whole snapshot stream of 100,000 and of 1,000,000 rows peaks at 2.4 MB;
- staging of the 1,024- and the 131,072-task index peaks at 6.5 MB each;
- a block's rows cost about 4.1 KiB per task with the fake worker's L3 rows. A realistic native row (12 jet values,
  16 tail values, 25-character decimals) measured about 10 KiB with the canonical and indented JSON, against the
  16 KiB allowance.

## Mac suites (`make -k test-python`, records in this folder)

First `make -k test-python` (`make_test_python.log`): `unit_orchestration` failed in two tests, so make stopped
the recipe there.
- `claim`: the read spy of `test_per_claim_reads` (tests/unit_orchestration.py) kept a closed subprocess pipe's
  descriptor in its pipe map. W9's snapshot then read with `os.read` on the reused descriptor 3, and the spy counted
  the task-file bytes as "platform" reads. The spy now drops a stale pipe key when `os.open` reuses the descriptor,
  and counts `os.read` on `os.open` descriptors under their file.
- `omp_team`: a timing flake under load (0.5 s deadline; the Mac was also running the before-runs). It passed alone
  and in the full re-run.

Then every line of the recipe ran one by one (`make_test_python_rest.log`), all exit 0:

| Suite | Result |
|---|---|
| `tests/check_venv.py` | passed (first run) |
| `tests/unit_orchestration.py` | 72 groups, 84 tests passed (5 new groups; W24 inside `route_b_records`) |
| `tests/test_pipeline.py` | parts 1, 2 and 3 passed (35 tests) |
| `tests/ast_scan.py` (tools; gen and tests) | 0 findings |
| `gen/test_regress.py` | 122/122 (25 new) |
| `gen/test_handoff_inventory.py` | 17/17 |
| `tests/merge_scale.py --rows 20000` | passed |
| `tests/check_vendored.py` | 36/36 |
| `tests/vendored_isolated.py` | 10/10 |
| `tests/test_delivery_verifier.py` | passed |
| `tests/check_inputs.py` | 23/23 |
| `tests/test_profiling.py`, `test_gmp_prefix.py`, `test_gmp_binding.py`, `test_omp_launch.py`, `test_numerics_flags.py`, `test_dd_profile.py`, `test_native_guards.py`, `sanitize.py --capture-check` | passed |
| `tests/verify_result_tamper.py` (the coverage guard's callers) | 206/206 |
| `tests/combine_core.py` | 14/14 |
| `gen/test_keys.py --no-ubsan` (Homebrew g++-16, `make -C gen` into the scratchpad) | 112/112 (10 new), sanitizers skipped on the Mac |

`tools/verify_delivery.py --write` and then `--strict` ran before the commit.

## Owed on symmetry (Verify phase)

- J-GEN-1 (gen/test_keys.py with GCC 11.4, UBSan and ASan): the W6 cases through the sanitizer builds. The Mac's
  g++-16 has no sanitizer runtime here.
- A real-worker claim on amdq. The job environment must set no loader override: the claim refuses LD_PRELOAD,
  LD_AUDIT and LD_DYNAMIC_WEAK with 64, and the lane worker refuses before any claim. The fingerprints of
  570376/570418 show no path-keyed library, so the identity of the existing pins is unchanged; if GLIBC_TUNABLES is
  set on the nodes it now enters the identity.
- A test-only gated dd+mp256 claim (a46f3060) on amdq: the node's libgmp 4dc20a90 must match gate 570536's binding.
- The host's W9 note: the peak RSS of a claim of a large real L8 index on symmetry, against its est_peak_bytes (now
  including 16 KiB per task of a block and 2 KiB per job entry and inventory row).
