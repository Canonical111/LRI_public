# Tests: dual_d1 (simulated export, 2026-10-15)

Simulated export: the repository's `.maintainer/export.py` copied into a scratch `sim/.maintainer/` with `source_root`
`<PROJECT>`, the real `global_exclude`, the entries of `maint/entries_dual_d1.json` and the SRI `verify/` and
`results/` folders (`maint/dual_d1/sim_export_dual_d1.sh`); `export.py --apply`. The package: 714 files, 61 MB,
8.8 MB packed (`tar czf` of the exported `SRI/`, including `verify/` and `results/`); no file over 50 MB, no symlink,
no two paths that differ only in case. The tarball was copied to `<SCRATCH>/sri_test/dual_d1/` on symmetry, and each
Slurm job (`maint/dual_d1/symmetry_test_dual_d1.sh`) unpacked it into node-local `/local1/<USER>/<job>/SRI` (a path
containing "local1") and ran, from `SRI/code/dual_d1/`: `make -f public.mk test`, `replay`, `fetch-data
ZIP=<the original archive>`, `replay-full`, with the acceptance Python (`<SCRATCH>/lri_public_test/venv_all/bin/python`:
Python 3.12.9, mpmath 1.3.0, SymPy 1.14.0), read-only. Logs: `<SCRATCH>/sri_test/dual_d1/runs/<job>.out` and
`runs/<job>/{test,replay,fetch,replay-full}.log`.

| Job | Partition, node | CPU | make test | make replay | make replay-full |
|---|---|---|---|---|---|
| 575628 (final tree) | sharedq, <NODE> | Intel Xeon Gold 6148 | PASS, 23 s (46 PASS, 7 INFO) | PASS, 65 s (63 PASS, 7 INFO) | PASS, 544 s (65 PASS, 7 INFO) |
| 575629 (final tree) | amddebugq, <NODE> | AMD EPYC 7532 | PASS, 26 s | PASS, 70 s | PASS, 556 s |
| 575610 (round 3) | sharedq, <NODE> | Intel Xeon Gold 6148 | PASS, 24 s (46 PASS, 7 INFO) | PASS, 63 s (63 PASS) | PASS, 553 s (65 PASS) |
| 575613 (round 3) | amddebugq, <NODE> | AMD EPYC 7532 | PASS, 26 s | PASS, 69 s | PASS, 558 s |
| 575600 (round 1) | sharedq, <NODE> | Intel | FAIL | FAIL | FAIL: two defects of the new tool, both fixed: the work copy's MANIFEST still listed the rewritten `layout.json` (run_checks.py hash check), and the 31-digit registry string is the record rounded, not a prefix; a third, in an INFO row, computed the C8 printing floor in a 28-digit Decimal context (fixed: exact Fractions). Every compendium task passed, including the complete C7 certificate (380 s), c8-positive-check (18 s) and c8-numerical (87 s) |
| 575607 | sharedq, <NODE> | Intel | cancelled by me after 12 s (stale tree) | | |

Between rounds 3 and 4 the tools gained the repository's SCRUBBED.txt / RE-PINNED.json conventions (no such file
exists for this package, so the checks are unchanged) and one docstring word; the snapshot did not change.

Dependency trace (symmetry job 575588, preq, <NODE>, Intel; 2026-10-15): the full original archive unpacked on a
node-local disk matched all 8,560 MANIFEST entries, and every compendium task passed with a file-access tracer
(`maint/dual_d1/trace_sitecustomize.py`; result `maint/dual_d1/trace_deps_575588.json`): run_checks.py 34 s,
reproduce_summary 2 s, c8-saved 9 s, c8-rational-algebra 3 s, low-integrals 6 s, conjectures 1 s, certificates 358 s
(0.5 GB), c8-positive-check 17 s, c8-numerical 87 s. The shipped data are the union of what the tasks run by test, replay and replay-full read (conjectures is not run).

On macOS (case-insensitive disk, Python 3.10.12, SymPy 1.12, mpmath 1.3.0): `make test` passes (46 PASS, 7 INFO); the work copy cannot hold the restored
lower-case file there, so the C6/C7 input maps (replay) report SKIP by design.

dual_d1 in the final runs: test 46 PASS, 7 INFO (the note-only and literature macros, the C8 printing floor, the wall
time); replay 63 PASS; replay-full 65 PASS. No FAIL, no SKIP on symmetry.
