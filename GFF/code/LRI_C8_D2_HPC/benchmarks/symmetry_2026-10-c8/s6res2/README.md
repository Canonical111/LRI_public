# Stage-6 residuals R1-R3 (a42cfb7) validated on symmetry (2026-10-06)

Site rule: symmetry only (user, 2026-10-05: symmetry first). Expanse, personal desktops were not touched.
Everything ran from the git-archive export of **a42cfb718e69** (`<SCRATCH>/c8d2/pkg/a42cfb718e69`;
`setup/export_check_a42cfb718e69.json`: 9,267 files equal to the archive in content and mode, no extra or missing
file). a42cfb7 is a57e07f plus the residual fixes R1-R3 and the class-reader reservation (`tests/`, `tools/`, `gen/`,
docs; no `src/` change); the Mac side is `../../mac_2026-10-c8/s6res2/`. The job scripts of this folder were written
after a42cfb7, so they are not in the export: they were uploaded read-only to
`<SCRATCH>/c8d2/work/rs-a42cfb718e69/` with both sha256 in `admission/submitted.txt`. The two L8 packs were
re-hashed against the export's `inputs/manifest.json` (free `e5dd7271…`, power `3d77d0c4…`, both equal) and
hard-linked from `pkg/7a8aad783c31/inputs/packs` (`rsbuild.570514.0/l8_packs.json`). The Codex round-3 worktrees
(`LRI_C8_D2_HPC_s6r3_{A..H}`) were not touched.

## Verdicts

| Step | Job | Verdict |
|---|---|---|
| 1. Export | Mac + login | **PASS.** `scripts/rs.sh export a42cfb7`: 9,267 files in git, the archive and the export; no content or mode mismatch; no symlink or special file (`setup/export_check_a42cfb718e69.json`, content listing sha256 `f75a4536…`). |
| 2. Build, **A-RPL-8** | 570514 | **PASS.** `scripts/rsbuild.slurm` (template s6fix2 `s2build.slurm`, unchanged steps): `make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize`, then `make c7ref`, on the exact default path. Every default and diagnostic executable is byte-identical to the Stage-5 symmetry build of 5d7586e: decimal **`619ddf7d…`**, gmp **`2cc5e88e…`**, prof `69e990c0…`, ratiohist `4f4638a2…`, inspect `10fe8133…`, c7ref `e696d7f3…`/`7e3c8c92…`, quad differential `1e7a8d34…`, quad ranges `f616b70b…`, interleave probe `b0acd9fb…`. The two sanitizer builds (`c4013f99…`, `b0e5a786…`) differ from 5d7586e's in 32 bytes each, the export path and the GNU build-id, and are equal once both are normalized. `make gmp NUMERICS=dd,mp256` gives **`d5df32ac…`** (the gated build of 570210/570373), `--describe` numerics `dd+mp256`, no development override, no stub, and leaves every default executable unchanged. Boost 1_77 in every build record (`rsbuild.570514.0/identity.json`, `ok: true`). |
| 3. **J-VAL-1** (`make test` on a whole amdq node) | 570515 | **PASS.** `scripts/rsval1.slurm` (template s6fix2 `s2val1.slurm`, plus step 5 below). No OpenMP control was inherited by the job (`omp_env_inherited.txt` empty). `check_venv --strict` passed; **`make test OUTPUT=…` exit 0 in 1,190 s as one command**: validate 52 tests (describe, bad_inputs, replay, invariance, inspector, class_b, diagnostics), unit_orchestration 60 groups / 72 tests / 0 failed on Linux with the real worker, test_pipeline 29, ast_scan 27 files and 46 files with 0 findings, test_regress 90/90, test_handoff_inventory 17/17, merge_scale, check_vendored 35/35 (one fewer than the Mac's 36: the review record is not on the cluster, as in 570415), vendored_isolated 10/10, the delivery-verifier test, check_inputs 22/22 with 2 skips (no `.git`, no inventory tree), test_profiling 16, test_gmp_prefix 8, test_gmp_binding 10, **test_omp_launch 5/5** (R1/R2: `invariance` 36 runs and 12 records, `invariance_team`, `run_env`, `tools_env`, `sanitize_env`), test_numerics_flags 11, test_dd_profile 8, sanitize `--capture-check`, workflow 2, staging 2. Then `assembly_checks.py --exact` 37/37, **`verify_result_tamper.py` 175/175** (R3) and `compat_2026.py` exit 0 (max relative difference 0.0). Executables unchanged by `make test`. |
| 3a. R1: validate's invariance with observed teams | 570515 | **PASS, every team observed.** In `make test`'s `test/validate.json` all **24** A-RPL-6 invariance rows (2 backends × 2 sectors × L7, L8 × layouts 0, 1, 2) carry `team_sizes_verified: true` and `teams_observed` `{"whole_1": 1, "chunks_4": 4, "chunks_1": 1}`, `thread_identical: true`, `omp_environment` "controlled (common.omp_child_env …; R1)". The invariance part took 23 s for 72 runs (about 0.3 s each), long enough for TeamWatch (1 ms first sample, doubling to 50 ms) to see the 4-thread teams: **no run was too short to observe** (a run whose team is not seen makes `team_run` raise, and validate passed). For the 1-thread runs, "observed 1" says only that the worker was sampled alive; the 4-thread runs are the ones that show a parallel team. The record stores the largest team seen per run, not the per-run sample counts. |
| 3b. R1 with hostile inherited controls (extra) | 570515 | **PASS.** Step 5 of `rsval1.slurm`: `tests/validate.py --only invariance` with `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true OMP_NUM_THREADS=64 GOMP_SPINCOUNT=0 KMP_AFFINITY=none` set for the command (the controls `test_omp_launch` gives its stand-in): exit 0 in 24 s, the same 24 rows, every `teams_observed` `{"whole_1": 1, "chunks_4": 4, "chunks_1": 1}` and `team_sizes_verified: true`. A 4-thread worker that inherited `OMP_THREAD_LIMIT=1` would have run with a team of 1 and failed `team_run` (`validate_invariance_hostile_env.json`, `teams.json` `ok: true`). |
| 4. **J-GEN-1** (`slurm/gen/regress.slurm` of the export) | 570516 | **PASS.** sharedq <NODE> (Xeon Gold 6148), Ubuntu GCC 11.4.0. `gen/test_keys.py` **115/115, nothing skipped**: the UBSan part (four programs with `-fsanitize=undefined -fno-sanitize-recover=undefined`) and the **new hostile-NG check**: `ASan build of test_keys (g++ -fsanitize=address)` PASS, and the header NG = 2,147,483,647 with one row refused with exit 2 and the missing row 2, with and without `--generator`, under `ASAN_OPTIONS=max_allocation_size_mb=256`, with no sanitizer report. Both runtimes (libubsan, libasan) are present on the node. `check_sources` passed, `test_run_l8` 6/6, `test_verify_inventory` 25/25, `test_regress` 90/90, `test_handoff_inventory` 17/17. **A-INV-2** (`regress.py --threads 1,8` at L3-L7 against `reference/LRI_C7_d2_progress/reference`): PASSED; in all 10 (sector, L) groups the same file set, `inventory_equal` and `inventory_bytes_identical` true, no `other` difference; free L3-L6 differ from the frozen files only in their rate lines (492 files, the accepted rate-only class), free L7 and power L3-L7 identical file by file (2,441, 1, 3, 20, 107, 709); 1 vs 8 threads identical; every control true. The `sectors` block, `threads_identical`, `controls` and `failures` equal those of 570417 (fix round 2) exactly. |
| 5. Stored results on the login node (R3) | <NODE>, no job | **PASS: 18/18 verified** with the new `tools/verify_result.py` (sha256 `569e7bee…`, a42cfb7's). Details below. |

## Step 5: every stored result re-verified on the symmetry login node

`scripts/rsverify_login.sh` on <NODE> (Intel Xeon Silver 4214R, AVX-512, the node of F6's check `../stage5/fix/fxf6.login/`;
python 3.11.3, numpy 2.3.5 from the venv; `OPENBLAS_NUM_THREADS=1`) found every `C8_*.json` result and
`*reassembled*.json` under `<SCRATCH>/c8-d2` and `<SCRATCH>/c8d2/evidence` by name (18 files) and
ran the export's `tools/verify_result.py` on each, then, for contrast, the fix-round-2 tool (`pkg/e914701b042b`,
sha256 `f4d93e3f…`, the same as a57e07f's). About 0.3 s per file (`rsverify.login/`: `exits.txt`, `summary.json`,
`new/NN.json`, `before/NN.json`, `node.txt`).

| # | Stored result (BeeGFS) | Campaign | a42cfb7 | e914701 tool |
|---|---|---|---|---|
| 15 | `c8-d2/smoke1-20261005/C8_test_result.json` | Stage-5 smoke (J-SMK-2) | verified | verified |
| 17 | `c8-d2/smoke1-20261005-twin/C8_test_result.json` | Stage-5 restart twin (J-DRL-1) | verified | verified |
| 16 | `c8-d2/smoke1-20261005-twin-2b3a92/C8_test_result.json` | Stage-5 fix twin (F7) | verified | verified |
| 14 | `c8-d2/smk4-20261005/C8_test_result.json` | Stage-5 J-SMK-4 | verified | verified |
| 01 | `c8-d2/desb1-20261005/C8_test_result.json` | design chain, K = 1 batch 1 | verified | verified |
| 02 | `c8-d2/desb2-20261005/C8_test_result.json` | design chain, K = 1 batch 2 | verified | verified |
| 03 | `c8-d2/desc1-20261005/C8_test_result.json` | design chain, K = 2 batch 1 | verified | **fails**: `/test_partial/power_null_checks/null_rows[1]/pull: 0.06239285347370077 differs from the recomputed 0.062392853498399854` |
| 04 | `c8-d2/desc2-20261005/C8_test_result.json` | design chain, K = 2 batch 2 | verified | verified |
| 12 | `c8d2/evidence/5d7586e9f1ab/design_chain_k2/C8_partial.json/C8_test_partial.json` | design chain, combined partial | verified | verified |
| 11 | `c8d2/evidence/5d7586e9f1ab/design_chain_k2/C8_final.json/C8_test_final.json` | design chain, combined final | verified | verified |
| 07 | `c8-d2/drills-5d7586e9f1ab/drA/C8_test_result.json` | drill drA | verified | verified |
| 13 | `c8d2/evidence/5d7586e9f1ab/drills/drA_recovery_reassembled.json` | drill drA, recovery | verified | verified |
| 08 | `c8-d2/drills-5d7586e9f1ab/drB/C8_test_result.json` | drill drB | verified | verified |
| 09 | `c8-d2/drl23-20261005/C8_test_result.json` | drills J-DRL-2/3 | verified | verified |
| 05 | `c8-d2/drills-2b3a9233353d/drR/C8_test_result.json` | drill drR (F8) | verified | verified |
| 06 | `c8-d2/drills-2b3a9233353d/drR/C8_test_result.superseded.8a8fd8ed8a26.json` | drill drR, superseded | verified | verified |
| 10 | `c8d2/evidence/2b3a9233353d/drl8_saved/C8_test_result.json` | drill drR, saved copy | verified | verified |
| 18 | `c8-d2/y2-e914701b042b/C8_test_result.json` | fix-round-2 Y2 test campaign (not Stage 5; found by the search) | verified | verified |

The 17 Stage-5 files and the one later test campaign all verify with the new tool. The old tool fails one file
here, desc1 (pull of null row 1, 2.5e-11 apart: the R3 class). On the Mac the old tool failed a different file, the
design-chain partial (`../../mac_2026-10-c8/s6res2/before_verify_result_all_stored_results.txt`). So which file the
old fixed pull tolerance rejects depends on the machine's BLAS kernels, which is R3's point. The new tool's
`pull_bound` accepts the partial on the Mac (16/16 there; desc1 has no copy on the Mac) and all 18 files here, while
`verify_result_tamper.py` (175/175 in 570515) still refuses a tampered stored pull and a pull changed alone by 0.5 of
its derived bound.

## Jobs

`sacct -X --duplicates` (`sacct.txt`; times EDT). Core-hours = ElapsedRaw × physical cores (AMD EPYC: 64 cores, 1
thread per core; the Intel sharedq node: 2 threads per core, so AllocCPUS / 2). Before submitting, the survey at 04:22
EDT showed 13 idle amdq and 17 idle amddebugq nodes, 72 idle CPUs on each sharedq node, and no live `c8d2-` job, so all
three were expected to start at once, and did (570515 waited only for its afterok dependency). H7: at most 4 live
`c8d2-` jobs on amdq + amddebugq + amdpreq; the peak was 2 (570514, 570515; `admission/h7_admission.jsonl`). C63d's
`c8d3-*` jobs and the other <USER> jobs (`sri_eng_*`) were neither counted nor touched. amdq/amddebugq with
`--exclude=cn112`; no longq; sharedq `--no-requeue`; every job with `--mem` and `--time` and a `c8d2-` name. Logs:
`<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); evidence
`<SCRATCH>/c8d2/evidence/a42cfb718e69/` (copied here in full).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570514 `c8d2-rsbuild` | build, A-RPL-8 (`scripts/rsbuild.slurm`) | amddebugq <NODE> (EPYC 7543) | COMPLETED 0:0 | 1:22 | 1.46 |
| 570515 `c8d2-rsval1` | J-VAL-1 + R1 hostile-env invariance (`scripts/rsval1.slurm`, afterok 570514) | amdq <NODE> (EPYC 7543) | COMPLETED 0:0 | 20:36 | 21.97 |
| 570516 `c8d2-gen1-regress` | J-GEN-1 (`slurm/gen/regress.slurm` of the export) | sharedq <NODE> (Xeon Gold 6148) | COMPLETED 0:0 | 4:09 | 0.28 |
| login | step 5 (`scripts/rsverify_login.sh`), 36 verifier runs | <NODE> | exit 0 | about 12 s | none |
| **total** | 3 job records | | | | **23.71** |

Budget: 23.71 of this task's 40 core-hours.

## Seeds

None. No step drew a seed: J-VAL-1's tests make their own seeds in temporary campaigns on the node's `/tmp`
(`C8_SEEDS` unset), the invariance runs use fixed test seeds, and J-GEN-1 and step 5 use none. symmetry's log is
unchanged (`<SCRATCH>/c8-d2/forbidden_seeds.json`, sha256 `59ec4a58…`, 105 seeds), as are the mirror
`designs/forbidden_seeds.json` (`d4db4595…`) and `../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`.

## Notes

- `tests/unit_orchestration.py:3036` makes Python 3.11 print `SyntaxWarning: invalid decimal literal` (`…==0.and …`)
  once per import, 12 times in `make_test.log`. The warning was already there in 570415, the line dates from 2bde93d
  (fix round 2, G2), and the test passes. Python 3.10 on the Mac is silent. A later Python may turn this into an error,
  so `0. and` should get a space (a cosmetic fix, not made here).
- The sanitizer executables keep differing from Stage 5's by the export path and build-id only (normalized equality),
  as in 570164 (Stage-5 fix) and 570414 (fix round 2).

## Files

`scripts/` (`rs.sh`: export, sub, upload; `rsbuild.slurm`, `rsval1.slurm`, `rsverify_login.sh`), `setup/` (the export
check), `admission/` (the `squeue` snapshots, the H7 lines, every sbatch and the three uploads), `logs/`, `sacct.txt`,
and one folder per run: `rsbuild.570514.0/`, `rsval1.570515.0/` (`exits.txt`, `make_test.log`, `test/*.json`,
`validate_invariance_hostile_env.json`, `teams.json`), `gen1.570516.0/`, `rsverify.login/`.
