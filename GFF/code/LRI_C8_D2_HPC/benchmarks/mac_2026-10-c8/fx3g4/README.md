# Stage-6 fix round 3, group G4: the profiling tools (2026-10-06)

Branch `fx3-g4` from a42cfb7, on the Mac (arm64, anaconda Python 3.10.11, numpy 1.23.5, scipy 1.10.0),
`C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1`. Items Z20, Z21 and Z22 of
`LRI_C8_D2_HPC_loop/artifacts/s6_fix3_dispositions.md` (findings S6H3-02, S6H3-03 and S6H3-04).

Changed files: `tools/perf_profile.py`, `tools/benchmark.py`, `tools/benchkit.py` (two helpers added, nothing changed)
and `tests/test_profiling.py`, plus this folder. There is no `src/` change and no cluster job. No worker command,
input or numerics changed. The profiling records gain fields; none is removed.

## The fixes

- **Z20 (S6H3-02): P1 now fails when the release worker's rows and the profiler's rows differ.**
  - Before, P1 recorded `rows_identical_worker_vs_prof: false` and still exited 0.
  - Now each block compares the per-row digests of the scientific fields (`benchkit.SCIENTIFIC`) of the perf run and
    the tier-timer run (`perf_profile.bind_rows`, `benchkit.rows_mismatch`).
  - A difference is an error that names the block, the number of differing rows, their uids, and any rows present in
    only one run. The block's record gets `rows_mismatch`, and P1 exits 1.
  - The other blocks stay accepted, and the measurements stay in the record.
  - **The fallback had the same defect class.** Without perf, the release worker never runs the blocks, so nothing
    bound the tier-timer worker to it. P1 now runs both workers on the fallback's mini block (16 tasks x 64 points, one
    thread) and requires identical rows (`fallback.binding`).
  - When `ltrace` exists, the traced release run must also match the plain run. The mini block is now prepared inside
    the guarded block, and its task count is recorded rather than assumed to be 16.
- **Z21 (S6H3-03): P3 now passes `--expect-sha256` to the ratio-histogram build.**
  - All three modes (P1, P2, P3) now check their executables before `Ctx.open()`. A refusal leaves no output
    directory, no scratch directory and no worker run.
  - Before, P1 and P2 had already created both directories when they refused.
  - **The same class, swept:**
    - `benchmark.py --interleave-probe` accepted `--expect-sha256` and ignored it. It now binds the probe executable.
    - The legacy C7(2) mode, which binds no executable, refuses the option (exit 2).
    - An empty or malformed value (anything but 8 to 64 hex digits) is refused with exit 64. Before, an empty string
      silently meant "no constraint" (`benchkit.expect_prefix`, `benchkit.require_sha256`).
  - The records carry `settings.expect_sha256`; P3 also carries `identity.ratiohist_check`.
  - The interleave probe's core-count refusal now comes before its output directory exists.
- **Z22 (S6H3-04): `--keep-perf-data` now keeps the data.**
  - Before, P1 removed the scratch directory unless `--keep-scratch` was also given, so the perf.data files were lost.
  - Every block's perf.data is now moved into `<output>/perf_data/`, with or without `--keep-scratch`, so it also
    survives a job-local scratch purge.
  - The block's `perf_data` records the retained path, size and sha256.
  - If a file cannot be moved, that is an error, and the scratch directory is kept (`settings.scratch_kept`).
  - The option is now P1's only. P2 and P3 write no perf.data and used to accept the option silently; they now refuse
    it (exit 2).

## Tests that fail before and pass after

The new tests are in `tests/test_profiling.py`:

| Test | Item | What it checks |
| --- | --- | --- |
| `perf_binding` | Z20 | A stale tier-timer worker (`C8_FAKE_DIAG_SKEW=heavy_power_L8` changes one value of one row): exit 1, the error and the uid name that block, the other block is accepted. The same skew on the fallback's mini block: exit 1. |
| `e2e_perf` (extended) | Z20 | The fallback records `binding.rows_identical_worker_vs_prof: true`. |
| `perf_expect` | Z21 | For p1, p2 and p3: a mismatched prefix gives 65, and empty, too short or non-hex values give 64. In each case there is no output, no scratch and no worker invocation (`C8_FAKE_LOG`). The right prefix (in upper case) runs p3. `--interleave-probe` gives 65 or 64 with no output, and the right prefix runs. `--lane-shapes` gives 65 or 64. Legacy mode gives 2. |
| `perf_keep` | Z22 | `--keep-perf-data` alone, and with `--keep-scratch`: the files are in `<output>/perf_data` with path, size and sha256 recorded, and they are moved, not copied. Without the option nothing is kept. p2 and p3 refuse the option. A move that fails (mocked quota error) is an error and keeps the scratch directory. |

Records:

- `before_test_profiling.{json,txt}`: these four tests run with a42cfb7's `tools/` (`git stash` of `tools/` only).
  All four fail.
- `test_profiling.{json,txt}`: the whole suite with the fixed tools, 19 of 19 passed.
- `test_gmp_prefix.json` (8 of 8) and `test_gmp_binding.json` (10 of 10): these suites import the test fakes and the
  P1 twin.
- `ast_scan.json` and `ast_scan_gen_tests.json`: 0 findings.
- `fx3g4_demo.py` shows each defect directly. `demo_before.json` is the run with a42cfb7's tools:
  - Z20: exit 0 with `errors: []` while `heavy_power_L8` rows differ.
  - Z21: P3 exits 0 with a wrong hash, and the worker ran.
  - Z22: no perf.data survives.
  - The probe exits 0 with a wrong hash.

  `demo_after.json` is the run with the fixed tools:
  - Z20: exit 1, the block named.
  - Z21: exit 65, no output, no worker run.
  - Z22: both files are in `<output>/perf_data`.
  - The probe exits 65 with no output.
