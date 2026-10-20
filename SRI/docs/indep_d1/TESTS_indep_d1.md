# Tests: indep_d1 (simulated export, 2026-10-15)

Simulated export: the repository's .maintainer/export.py copied into a scratch sim/.maintainer/ with source_root
<PROJECT>, the real global_exclude and the entries of `maint/entries_indep_d1.json` (base snapshot, the repinned overlay,
the public overlay), plus SRI/verify and SRI/results from the SRI patches and, for the two framework tests that read
the compendium, the two sibling files of `SRI/code/dual_d1` (note/LRI_perturbation_compendium.tex,
data/archived/C8_full_numerical_completion/data/F3_final_100.json); `export.py --apply`. Package: 772 files, 21 MB,
3.8 MB packed (`tar czf` of SRI/code/indep_d1); no file over 10 MB, no symlink, no case-colliding paths. The tree was
copied to symmetry and unpacked into node-local storage /local1/<USER>/<job>/SRI/code/indep_d1 (a path containing
"local1"); the scripts the replay runs contain no path-substring filter. Interpreter: the acceptance venv
(<SCRATCH>/lri_public_test/venv_all/bin/python: Python 3.12.9, mpmath 1.3.0, sympy 1.14.0, scipy 1.17.1), read-only;
g++ 11.4 (system). Commands from SRI/code/indep_d1: `make -f public.mk test PY=<venv python>`, `make -f public.mk replay
PY=...`, `make -f public.mk replay-raw PY=... RAW=<SCRATCH>/sri_test/indep_d1/raw` (a copy of the 293 raw chunk outputs).

| Job | Partition, node | CPU | make test | make replay | make replay-raw |
|---|---|---|---|---|---|
| 575645 (final tree) | sharedq, <NODE> | Intel Xeon Gold 6148 | PASS: 25 PASS, 258 s | PASS: 26 PASS, 2 INFO, 229 s | |
| 575646 (final tree) | sharedq, <NODE> | Intel Xeon Gold 6148 | | | PASS: 28 PASS, 2 INFO, 349 s |
| 575647 (final tree) | amddebugq, <NODE> | AMD EPYC 7532 | PASS: 25 PASS, 308 s | PASS: 26 PASS, 2 INFO, 264 s | |
| 575638, 575639, 575640, 575642 (previous tree) | sharedq <NODE>/<NODE>, amddebugq <NODE> | Intel, AMD | PASS | FAIL: 2 per-job diagnostics of the input q outside 1e-3 of sigma (Python 3.12 compensated sum vs the 3.10 that wrote the records; same on the raw path); tolerance for diagnostics set to 1e-2 | FAIL (same 2 leaves) |
| 575617, 575619 (earlier tree) | sharedq <NODE>/<NODE> | Intel | PASS (25) | FAIL: report/comparison tolerances and the value rule of C7, D4 (cut, not rounded); fixed | |
| 575605, 575606 (first tree) | sharedq <NODE> | Intel | FAIL: test_c8 needs the compendium note (sibling dual_d1 added) | FAIL: rounding-noise of 3-5 kink jobs (record extended with per-sector values of small jobs), tier-A report note, missing log directory | |

Other jobs: 575597 and 575616 (sharedq, Intel) built `public/pooled_sector_record.json` from the raw chunk outputs
(16 s); 575618 (stale snapshot list) and 575630-575632 (the re-pin cascade had left one stale hash; the re-pin tool now
iterates to a fixed point and checks it) were cancelled by me.

**test (575645, Intel):** snapshot (760 files; 22 re-pinned files match RE-PINNED.json), the eight recorded sha256 lists
(engine deliverables, spec, sealed comparison files, framework production record, RESULTS json files) and the sha256
recorded in the results; the framework tests test_strict_missing, test_error_model, test_replicates, test_pmax,
test_module_vs_sympy, test_normalization, test_vs_spec, test_c8 (with the sibling note), test_archive_pipeline
(re-pointed to the sibling dual_d1 record) and the critic's note-direct check; the engine built from source
(binary md5 ec238e0fa37b, the production binary's) and four production chunks (3 and 5 kinks, angular and full
geometry) rerun from their .cfg: values within 2.4e-16 of their L1 scale (not bitwise: 8 threads instead of 64).

**replay (575645, Intel; the same on AMD, 575647):**
| check | result |
|---|---|
| RESULTS.md, RESULTS_C8.md | byte-identical (published make_report*.py on the published json) |
| RESULTS_C8_tierA.md | identical except its hand-added status note |
| run_assembly.py main() -> RESULTS_independent.json | 13,602 leaves within tolerance (values exact; pooled 1.5e-7 of sigma) |
| run_assembly_C8.py step1() + W three ways + separate tier files | 2,883 leaves within tolerance (pooled 2.5e-8 of sigma) |
| compare_archive.py, compare_archive_C8.py | 3,968 and 454 leaves within tolerance |
| eq:sr-closed, eq:sr-C8 vs the claims tested | 3.1e-29, 4.1e-38 |
| C5, C6, C7, D4 | 29.237811563 +- 1.35e-7 (-0.13); -58.66569861 +- 1.45e-6 (-0.78); 51.0689860 +- 3.14e-5 (-0.08); -2.53463048 +- 7.85e-6 (-0.09) |
| \SRindepPullMax | 0.784 -> 0.8 PASS (jobs above, macro 0.8 = max over C5..C7). Macro redefined 2026-10-15 as the max over the 25 inputs (0.9 in numbers.tex): 0.915 -> 0.9; rerun in the full SRI export test (see the top-level TESTS) |
| 25 inputs | rms pull 0.34, max 0.91 (Omega) PASS; INFO: the literal bound 0.8 holds for C5..C7, not for every input |
| \SRCeightIndep | 242.825 +- 2.371 -> 242.8\pm2.4 PASS (quoted estimator: sector-pooled) |
| \SRCeightPull | -1.922 -> 1.9 PASS (below the claim) |
| J9, A9[eps^0 l^1] | -291.9 +- 9.5 vs -273.72 (-1.92); ours - archive -20.4 +- 9.3 (-2.19 sigma, 3.3e-5 relative) |
| single input integral | A9_1 -2.19; Z8_1 +0.14, (EA7)_0 +0.95, (EZ6)_0 -0.24, D9_lower -0.71; U +0.27, Kv -0.27; C8 - J9/4 -0.20 PASS |
| chunk-pooled pull | INFO -2.09 (not recomputed) |

**replay-raw (575646):** the 293 raw chunk outputs match RAW_SHA256SUMS.txt; the pooled record rebuilt from them with
the verbatim job_sector_values() equals the shipped one exactly; the shim reproduces the verbatim pooled_projection
(1,196 projections: unit gradients 1.8e-16, random gradients 7.7e-9, replicate projections 3.9e-6 relative); every
replay step with the verbatim pooled_errors.py on the raw outputs passes with the same tolerances.
