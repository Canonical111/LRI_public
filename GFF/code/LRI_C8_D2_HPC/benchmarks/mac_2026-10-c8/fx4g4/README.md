# Stage-6 fix round 4, group G4: profiling and test cleanup (2026-10-06)

Branch `fx4-g4` from 945e526, on the Mac (arm64, anaconda Python 3.10.11), `C8_ALLOW_NO_L8=1 OPENBLAS_NUM_THREADS=1`.
Items W14, W15 and W19 of `LRI_C8_D2_HPC_loop/artifacts/s6_fix4_dispositions.md` (findings S6E-R4-01, S6E-R4-02 and
S6H4-02).

Changed files: `tools/perf_profile.py`, `tests/test_profiling.py`, and in `tests/unit_orchestration.py` only the
`Owned` cleanup helper, the in-process launch-boundary case (now `launch_boundary_case`, called by
`test_signal_cleanup`), and two new tests with their `TESTS+=` line. Plus this folder. There is no `src/` change and
no cluster job. No worker command, input or numerics changed. `tools/benchkit.py` is unchanged.

## The fixes

- **W19 (S6H4-02): without perf, P1 now binds the tier timers to the release worker on every requested block.**
  - Before, without perf, the release worker did not run the blocks. The fallback compared the release worker and
    the tier-timer worker on a mini block only (16 tasks x 64 points of `heavy_power_L8`, one thread). The finding's
    counterexample (no perf, the tier-timer worker differing on `heavy_free_L8`, `--blocks heavy_free_L8`) exited 0.
  - Now the release worker runs every requested block, directly (not wrapped by perf; its OpenMP team watched), at
    `--threads` on the first set of cores, in place of the perf run (`blocks[b].release_run`). The Z20 comparison
    then applies to every block, exactly as with perf: a difference is an error naming the block and the uids, and
    P1 exits 1. `fallback.binding` lists the per-block result.
  - Because both streams now always exist, they run concurrently in the fallback too (unless `--sequential`, or one
    socket only), as they do with perf. The fallback therefore costs one more release run per block on the other
    socket, at the same wall time.
  - The mini block is now ltrace's only. When ltrace exists, a plain run of the mini block is its reference, and
    the traced rows must equal it (as before). The mini-block tier-timer run is gone: the per-block binding replaces
    it.
  - The perf path is unchanged: same runs, files, record keys and error texts.
- **W19's class, swept: P3 never bound the ratio-histogram build to the release worker.**
  - P3 measured `bin/c8d2_gmp_ratiohist` alone. Its margins fed the R3b decision (`C8_DD_RATIO`), and its Slurm script
    only asserted that "its rows equal the release worker's". A stale ratio-histogram build passed P3.
  - Now the release worker (`--worker-exe`, default `bin/c8d2_gmp`, checked as a release build before any output)
    runs every (block, rate) too, at the same rate and threads. The scientific rows must be identical. A difference
    is an error naming the block, the rate and the uids (`results[k].rows_mismatch`), and P3 exits 1.
  - A release run that fails keeps the margins in the record, unbound (`rows_identical_worker_vs_ratiohist: null`),
    and is an error.
  - P3 now runs every (block, rate) twice. Records gain `identity.worker`, `identity.worker_check`,
    `settings.worker_exe`, and per result `release_run` and `rows_identical_worker_vs_ratiohist`.
- **W14 (S6E-R4-01): `Owned` keeps the process groups of registered session leaders.**
  - Before, ownership was rebuilt from the processes visible at each call: unreaped registered children, marker
    matches, their process groups and their descendants. A registered leader that started an unmarked helper
    (output redirected) and was then reaped (`communicate()`, `wait()`) left a helper that matched nothing. It was
    reparented away and its leader was gone, so it survived the cleanup. `test_lane_sigterm` checks the worker's
    session after `communicate()`, so that check could miss such members too.
  - Now `add()` retains the group the child leads. The group is established while the child is unreaped, so its pid
    and group id cannot have been reused: the child must lead its own group (`start_new_session=True`), and the group
    must be neither the runner's nor an ancestor's. A zombie child is found through `ps`, because macOS refuses
    `getpgid` on a zombie.
  - `survivors()` includes every live member of a retained group, also after the leader's exit and reaping.
  - A retained group is retired for good (`held()`) in two cases: when its leader is reaped and no process of the
    group is left, or when a live process holds the group id as its pid (a reuse; POSIX reuses no group id as a pid
    while the group has members).
  - A child in the runner's own process group is owned by its pid only, as before.
- **W15 (S6E-R4-02): the in-process launch-boundary case runs in an unconditional cleanup scope.**
  - Before, the hook kept only the child's pid, and nothing outside production held the child (a later
    `production.run` resets `_NATIVE['children']`). If production's cleanup failed, the 120 s fake worker was left
    running.
  - Now `launch_boundary_case` registers the child's `Popen` in an `Owned` scope (also marked by the scratch path)
    before it injects SIGTERM. Whatever fails, the evidence is taken first, and the child is then killed and reaped.
  - The hook also waits, with stop signals still deferred, until the fake worker runs (its `C8_FAKE_LOG` line). The
    fake is a Python script inside the runtime that the run removes, and a fake that had not yet read its script died
    by itself. The case now proves that production stops a running worker.
  - The case also checks that production reaped the child (`returncode` set).
- **W15's class, swept in `tests/test_profiling.py`:** `tool()` used `subprocess.run(timeout=600)`, which on a timeout
  kills the tool alone and leaves its workers, fake perf or ltrace running. Now the tool runs in a session of its own.
  If it does not finish (timeout or interrupt), its whole process group is killed and reaped before the exception
  propagates. On the normal path the group is not signalled: once the tool is reaped, its id could belong to someone
  else. The refusal cases of `test_refusals` that called `subprocess.run` directly now go through `tool()`.

## Tests that fail before and pass after

| Test | Item | What it checks |
| --- | --- | --- |
| `test_profiling.py perf_binding` (extended) | W19 | The finding's counterexample: exit 1, `heavy_free_L8` and its uid named, `release_run` and `tier_run` recorded, `fallback.binding.blocks` false. With two blocks, only `heavy_free_L8` fails. A difference on an unmeasured block is no error. |
| `test_profiling.py e2e_perf` (extended) | W19 | Without perf: `release_run` at 4 threads on cores 0-3, concurrently with the tier timers on 4-7, rows bound. With a fake ltrace on PATH: the mini-block table, its rows equal to the plain mini run. A traced run that differs is an error. P3: every (block, rate) bound, `identity.worker_check`. |
| `test_profiling.py p3_binding` (new) | W19's class | A stale ratio-histogram build on one block: exit 1, both rates named, the other block accepted. A release worker with other promotion counters: exit 1. A failing release run: margins kept, unbound, an error. A diagnostic `--worker-exe`: 65. A missing one: 69, no output, no worker run. |
| `test_profiling.py perf_expect` (adjusted) | W19's class | P3 takes `--worker-exe`. The refusals are unchanged. |
| `test_profiling.py tool_cleanup` (new) | W15's class | A stand-in tool that starts a 120 s worker and hangs: a 3 s timeout raises, and the worker is gone. |
| `unit_orchestration.py w14_group_cleanup` (new) | W14 | The control from the finding: a leader starts an unmarked helper and is reaped. `survivors()` lists the helper under the leader's group. A deliberate failure follows: the failure message carries the helper, the helper is killed (independently: its pid is gone), and the group is retired. Also: a zombie leader, a child in the runner's group (never `killpg`'ed), and the `held()` retirement rules. |
| `unit_orchestration.py w15_launch_cleanup` (new) | W15 | The control from the finding, with production's cleanup made to fail (`stop_children` a no-op). (0) The pattern before the fix leaves the worker running. (1) `launch_boundary_case` fails with the worker in the failure evidence, and the worker is killed and reaped. |
| `unit_orchestration.py signals` (changed case) | W15 | The in-process case now runs through `launch_boundary_case`. |

Records:

- `before_test_profiling.{json,txt}`: the changed and new profiling tests, run with 945e526's `tools/perf_profile.py`
  and 945e526's `tool()` (`subprocess.run` with its timeout; given the `timeout` keyword so that the control reaches
  its check). All five fail:
  - `perf_binding`: the finding's counterexample exits 0.
  - `tool_cleanup`: the worker of the timed-out tool survives.
  - `e2e_perf`: no `release_run`, and the fallback is sequential.
  - `p3_binding` and `perf_expect`: P3 has no `--worker-exe` (exit 2).
- `before_unit_orchestration.{json,txt}`: `w14_group_cleanup` and `w15_launch_cleanup`, run with 945e526's `Owned`
  and the in-process case as before the fix. In that version the hook keeps only the pid and has no cleanup scope;
  it has the same readiness wait, so that the control reaches its check. Both fail:
  - `w14_group_cleanup`: `survivors()` is empty after the leader's reaping.
  - `w15_launch_cleanup`: the case fails without any cleanup.

  `before_unit_orchestration_leftovers.txt` lists what that run left running after it exited: the W14 helper and the
  W15 fake worker, both reparented to init. They were then killed by hand.
- `test_profiling.{json,txt}`: the whole suite with the fixes, 21 of 21 passed.
- `unit_orchestration.{json,txt}`: the whole suite with the fixes, 69 tests (81 results), all passed, in 15 min.
- `unit_orchestration_run1_loaded.json`: an earlier full run of nearly the same files, made while the Mac was at a
  load average of about 50 (other sessions' suites). It differs only in the `Owned` docstring and one set comparison
  in `w14_group_cleanup`. Its only failure is `omp_team` (G2's test, not changed here): under that load the 0.5 s
  team deadline stopped the fake worker before it wrote its `C8_FAKE_LOG` line, and the test's
  `log.read_text()` raised `FileNotFoundError`. Alone, `omp_team` failed once (`omp_team_rerun1.json`) and passed
  once (`omp_team_rerun2.json`). This is a load-dependent flake, reported as an issue.
- `test_gmp_prefix.json` (8 of 8) and `test_gmp_binding.json` (14 of 14): these suites import the test fakes and the
  P1 twin.
- `ast_scan.json` and `ast_scan_gen_tests.json`: 0 findings.
- `fx4g4_demo.py` shows each defect directly:
  - `demo_before.json` (945e526's files):
    - W19: exit 0 with `errors: []`, and the mini block compared instead.
    - W19's class: P3 exits 0 with a stale ratio-histogram build.
    - `tool()`: the worker survives.
    - W14: the helper is not listed, not in the evidence, and survives.
  - `demo_after.json`:
    - W19: exit 1, `heavy_free_L8` named.
    - W19's class: P3 exits 1, `random_power_L8@.8` named.
    - `tool()`: the worker is gone.
    - W14: the helper is listed, in the evidence, and killed.

## Left to other groups (not edited here)

- Docs:
  - `docs/PERFORMANCE.md` still describes the old fallback (the P1 tools paragraph and the Z20 bullet: "the fallback
    runs the release and the tier-timer workers on the mini block") and P3 without the release binding.
  - `README.md` (the profiler line) and the CHANGELOG need the W14, W15 and W19 entries.
  - The P3 record fields are `results[k].release_run`, `rows_identical_worker_vs_ratiohist` and `rows_mismatch`,
    with `identity.worker` and `worker_check` and `settings.worker_exe`. The P1 fallback fields are
    `blocks[b].release_run` and `fallback.binding.blocks`.
- `benchmarks/expanse_2026-10-c8/stage4a/scripts/expanse_prof3.slurm` is historical (Expanse is not used). P3 now runs
  every (block, rate) twice, so a rerun needs about twice its 11 min wall. Its comment "its rows equal the release
  worker's" is now checked.
- `tests/unit_orchestration.py` `test_omp_team` (G2):
  - Under load, the 0.5 s deadline of the 'smaller' case can stop the fake worker before its `C8_FAKE_LOG` line, and
    the test then fails with `FileNotFoundError` (seen once in two isolated runs at a load average of about 50).
  - The same in-process case runs its 30 s fake worker with no independent cleanup scope (W15's class; the worker
    ends by itself). An `Owned` scope around the run, with a readiness wait like `launch_boundary_case`'s, would close
    both.
- `test_lane_sigterm`'s post-`communicate()` check of the worker's session now sees the members of the exited
  worker's group, through W14's retained groups. It needs no edit.
