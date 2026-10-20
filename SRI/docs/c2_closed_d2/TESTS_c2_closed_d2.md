# Tests: c2_closed_d2 (simulated export, 2026-10-15)

Simulated export: the repository's `.maintainer/export.py` copied into a scratch `sri_sim/c2_closed_d2/.maintainer/`
with `source_root` `<PROJECT>`, the real `global_exclude` and the entries of `maint/entries_c2_closed_d2.json`, plus
two entries exporting `SRI/verify/` and `SRI/results/` from the SRI patches; `export.py --apply`. The package: 341
files, 5.5 MB, 2.33 MB packed (`tar czf` of `SRI/code/c2_closed_d2`); no file over 1 MB, no symlink, no two paths
differing only in case. The tree (sha256 8bbb2ccb... of the tarball) was copied to `<SCRATCH>/sri_test/c2_closed_d2/`
and unpacked by each job into node-local storage `/local1/<USER>/<job>/SRI` (a path containing "local1").
Interpreter: the acceptance venv (`<SCRATCH>/lri_public_test/venv_all/bin/python`: Python 3.12.9, numpy 2.3.5,
scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0, matplotlib 3.11.2), read-only; gcc 11.2.0 (module) for the Monte Carlo
targets. Commands, from `SRI/code/c2_closed_d2/`: `make -f public.mk test PY=<venv python>`, `make -f public.mk replay
PY=...`, `make -f public.mk rerun-mc-smoke`, `make -f public.mk mc-batch-check PY=...`.

| Job | Partition, CPU | Tree | make test | make replay | rerun-mc-smoke | mc-batch-check |
|---|---|---|---|---|---|---|
| 575633 (final) | sharedq, Intel Xeon Gold 6148 | final export (tarball sha256 8bbb2ccb...) | PASS (6 PASS), 4 s | PASS (56 PASS, 0 FAIL, 5 INFO), 39 s | PASS, 24 s | PASS (5 PASS; B, BS within 1.6e-11 of the largest entry, BD identical), 169 s |
| 575634 (final) | amddebugq, AMD EPYC 7532 | final export | PASS (6 PASS), 4 s | PASS (56 PASS, 0 FAIL, 5 INFO), 41 s | - | - |
| 575635 (final) | sharedq, Intel | final export after a simulated publication scrub: outputs/run_manifest.json (/workspace/scratch/... -> placeholder), mc/prod.sbatch and mc/prodC.sbatch (the repository's scrub rules), listed in a public/SCRUBBED.txt as Public_repo's scrub writes it | PASS (6 PASS; snapshot 3 presence-only, verify_package.py: 1 changed, listed), 4 s | PASS (56 PASS, 0 FAIL, 5 INFO), 39 s | - | - |
| 575622, 575623, 575624 | sharedq Intel, amddebugq AMD (<NODE>), sharedq | previous iteration (its overlay still carried a SCRUBBED.txt, since removed: Public_repo writes that file) | PASS | PASS (56 PASS) | PASS | PASS (AMD: B, BS, BD bitwise identical) |
| 575614, 575615 | sharedq Intel, amddebugq AMD | previous iteration | PASS | PASS (56 PASS) | PASS | PASS (AMD bitwise identical) |
| 575602, 575608 | sharedq, Intel | probes | - | - | - | manual rerun of batch 0 of chunk A/1 (BD identical, B and BS to the 10th digit); became `mc-batch-check` |
| 575599 (first iteration) | sharedq, Intel | first export | PASS | FAIL: 55 PASS, 1 FAIL (the receipt check expected every raw hash except convergence.json to match; independent_c2_80dps.json records the software environment, so it is now compared numerically only) | PASS (compiler warnings; now -w) | - |
| 575596 | sharedq, Intel | first export | - | - | - | failed at start (`set -u` with the modules script); node-local leftovers removed by job 575603 |

Logs: `<SCRATCH>/sri_test/c2_closed_d2/logs/sri-pub-c2_closed_d2*_<job>.out`; PASS/FAIL tables of the final runs in
`<SCRATCH>/sri_test/c2_closed_d2/out_575633/`, `out_575634/` and `out_575635/`. Mac: only the closed-form and Monte Carlo parts of
the replay were run locally (about 2 s CPU).

Final replay rows: snapshot (333 files); the study's eight-stage rerun (exit 0; 5 of 7 raw outputs byte-identical,
convergence.json and independent_c2_80dps.json numerically equal; summary.json and the three tables byte-identical or
equal; the receipt hashes of the 5 others equal); 24 rows of the appendix, the note and the review's package values
at 50 digits; summ.py output identical to the three production logs and the estimator equal to it (6 rows); the
review's Monte Carlo numbers (6 rows) and two pulls (source-shape control +0.65, closed form -0.47); the frozen mc_combined.json
(0 leaves differ); `\SRtwoCtwo` PASS (-4.066270148 -> -4.06627); `\SRtwoCtwoMC` PASS (-4.075242258 +- 0.018903921 ->
-4.075 +- 0.019); tab:sr d = 2 cells PASS. INFO: raw byte-identity count, the plateau over cuts, the value without
configuration C (-4.0724 +- 0.0197), the chi^2 of the source-shape control (7.63 on 2 dof), c_1 = 0 (literature).

Path-substring filters: none in the scripts the replay runs (`code/*.py` locate files from `__file__`; `mc/summ.py`
reads the files it is given; the new tools use paths relative to the package).
