# Stage-6 fix round 4 on symmetry (2026-10-06): A-RPL-8, J-VAL-1, J-GEN-1, W2/W7/W8/W9 on real nodes, the `dd+mp256` gate re-run (W18) and the route-(b) re-freeze

Site rule: symmetry only (user, 2026-10-05: "symmetry first"); Expanse, personal desktops were not
touched. Fix round 4 has **no `src/` change**, so every executable must be byte-identical to fix round 3's (A-RPL-8),
and the round's numerical evidence is the replay-free part: J-VAL-1 (`make test` with every fix-round-4 test on Linux
and the real workers), J-GEN-1 (W4-W6 on GCC 11.4 with UBSan and ASan), G-BK8 under W2's row rule, the full thread
identity under W22's coverage, a real gated claim (W7, W8), a claim's memory on a large index before and after W9, and
the `dd+mp256` J-FLAG gate again, because W18 requires an authenticated input set the 570536 record does not have
(host note in `LRI_C8_D2_HPC_loop/artifacts/s6_fix4_dispositions.md`). Budget: 120 core-hours.

**Exports.** Everything ran from git-archive exports, each checked file by file (`setup/export_check_<sha12>.json`):
- **`392ed22d1d02`** = 392ed22, the integration and docs commit (the four group merges, the cross-group fixes, these
  job scripts): 10,018 files equal to the archive in content and mode. Jobs 570572-570579.
- **`900e5906522a`** = 900e590, 392ed22 plus a tests-only fix found by J-VAL-1 here (`tests/test_numerics_flags.py`
  `w18_inputs` hard-linked the packs across file systems, below) and the corrected job scripts: 10,018 files equal.
  Jobs 570582-570583. Its build gives every executable of 570572 byte for byte.

The two L8 packs were re-hashed against each export's `inputs/manifest.json` (free `e5dd7271…`, power `3d77d0c4…`) and
hard-linked from `pkg/7a8aad783c31/inputs/packs` (`s4build.*/l8_packs.json`). The Codex round-4 worktrees
(`LRI_C8_D2_HPC_s6r4_{A..H}`) were not touched.

## Verdicts

| Step | Job | Verdict |
|---|---|---|
| **A-RPL-8** (build, identity) | 570572 (amddebugq <NODE>, 1:42); again 570582 for 900e590 | **PASS.** Every executable byte-identical to fix round 3's build of b58e9b6 (570540): decimal `a18ce425…`, gmp `7741f733…`, `dd+mp256` `a46f3060…`, prof `3fb9e777…`, ratiohist `01aef195…`, inspect `38361979…`, quad_ranges `ffa7a192…`, interleave_probe `a6841111…`, quad_differential `1e7a8d34…`, c7ref `e696d7f3…`/`7e3c8c92…`; the two sanitizer builds equal to pkg/b58e9b6f4afd's after the export tag and the GNU build-id are normalized. Every build record: `macro_overrides: []`, no override, `development: false`, required flags, Boost 1_77, and (W3) `build_directory` = the export (`s4build.570572.0/identity.json`). |
| **J-VAL-1** (`make test`, whole amdq node) | 570573 (<NODE>, 40:05): stopped; **570583** on 900e590 | 570573: `make test` stopped in `test-python` at `tests/test_numerics_flags.py` `w18_inputs`: `os.link` from the export (BeeGFS) to the test's copy on node-local `/tmp` failed with EXDEV, a test-portability defect of G3's new test, fixed in 900e590 (a symbolic-link fallback; `../../mac_2026-10-c8/s6fix4int/exdev/`: the test fails on 392ed22 and passes on 900e590 with `os.link` failing as here). Everything before it passed: validate (J-VAL-1 subset; `validate.py --check test/validate.json --gate J-VAL-1` exit 0), unit_orchestration 75 groups / 87 tests on Linux with the real worker, test_pipeline 39, ast_scan 0 findings, test_regress 129, test_handoff_inventory 17, merge_scale, check_vendored, vendored_isolated, the delivery-verifier test (W13), check_inputs, test_profiling 21, test_gmp_prefix, test_gmp_binding 16 (W3's `relative_paths`, `flags_relative`), test_omp_launch 5; then `assembly_checks --exact`, verify_result_tamper 206/206, combine_core 14/14, compat_2026. **570583 (<NODE>, 38:52) on 900e590: PASS, `make test` exit 0 as one command** (2,300 s): validate 52 (J-VAL-1 subset with the A-RPL-6 chunk merge on real rows; `validate.py --check test/validate.json --gate J-VAL-1` exit 0), unit_orchestration 75 groups / 87 tests / 0 failed on Linux with the real worker, test_pipeline 39, ast_scan 0 findings, test_regress 129/129, test_handoff_inventory 17, merge_scale, check_vendored 35/35, vendored_isolated 10/10, the delivery-verifier test (W13: every delivered result record verified), check_inputs 22/22, test_profiling 21, test_gmp_prefix 8, test_gmp_binding 16, test_omp_launch 5, **test_numerics_flags 14** (W18 `w18_inputs` with the fix, `w20_seeds`), test_dd_profile 8, **test_native_guards 7/7** (W1 `quad_coverage`, W2 `bk8_compare`, W22 `thread_coverage`, the `summaries` of both stored-record consumers), the sanitize capture check, workflow 2, staging 2; then `assembly_checks --exact` 37/37, verify_result_tamper 206/206, combine_core 14/14, compat_2026; executables unchanged. The real-node checks of steps 5, 6 and 8 (below) ran in 570573 on the same executables and were not repeated (`done_from.txt`). |
| **W2 on real rows** (G-BK8) | 570573 | **PASS.** `validate.py --only none --bk8` (400 kernels per sector at L7 and L8, decimal against gmp, 3,200 rows) under row rule `c8-d2-bk8-row-rule-2` (`max_abs`, `tail_top`, `tail_sum`, tail widths and `tail_argmax` of the MP rows; every row field covered by a rule): status passed, `validate.py --check bk8.json --gate G-BK8` exit 0, and every test's graphs, rows, MP rows, binary128 and MP points and maximum normalized difference of the MP rows (0) **equal to fix round 3's 570535 record**. The stricter A-RPL-6 `chunk_merge` (tiling, quad/mp sums, `max_abs`) passed on the real rows of `make test`'s invariance (24 rows) and of the hostile-environment rerun. |
| **W22** (thread identity) | 570573 | **PASS.** `tests/thread_identity.py` at its full default configuration: status `passed` (coverage complete: both default workers × both sectors, 1/8/16/64 threads and 8 × 8 lanes, every team observed, `team_sizes_verified`), `--check` exit 0. |
| **R1, hostile OpenMP environment** | 570573 | **PASS.** `validate.py --only invariance` with `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true OMP_NUM_THREADS=64 GOMP_SPINCOUNT=0 KMP_AFFINITY=none` exported: 24 rows, every team observed equal to its request (`teams.json` of `summary.json`). |
| **J-GEN-1** (`slurm/gen/regress.slurm`) | 570575 (sharedq <NODE>) | **PASS.** `gen/test_keys.py` 146/146 with GCC 11.4: W6's nine malformed copies of power L4 G18 each fail that graph only, with its error, in the plain, the UBSan and an ASan build (`max_allocation_size_mb=256`); `test_regress` 129/129 (W4, W5, the integration's `kirchhoff_checks`); A-INV-2 at L3-L7, 1 and 8 threads: free L3-L6 rate-line files only, free L7 and power L3-L7 identical. |
| **The `dd+mp256` J-FLAG gate** (W18) | 570574 (amdq <NODE>, 14:07) | **PASS; `design.check_gate` accepts the record** with the export's inputs manifest. Details below. |
| **W9 before and after** (a claim's memory on a large index) | 570576 (failed: the job's RSS wrapper), **570578** (sharedq <NODE>) | **PASS.** Details below. |
| **Route-(b) re-freeze, a real gated claim** (W7, W8, W9) | 570577 (cancelled while pending: the same wrapper defect), **570579** (sharedq <NODE>, 30:41) | **PASS.** Details below. |

## The `dd+mp256` J-FLAG gate (job 570574)

One whole amdq node (<NODE>, 2 × EPYC 7543); `tests/numerics_flags.py --profile dd+mp256 --seeds-log $C8_SEEDS` at full
scale with a **fresh F1 baseline** (`scripts/s4flag.slurm`), the exact binary `7741f733…` and the profile `a46f3060…`
checked before and after. Wall 846 s. Record `s4flag.570574.0/jflag_dd+mp256/numerics_flags.json`, sha256
**`42e6d2d80a484c2bddc8bba37180c400191c79722d9a11ddf9eb535429e0a800`** (`check_gate.json`).
- **Status `"passed"`**, verdicts F1, F2, F4 rows, F5 true, no development option.
- **W18:** `inputs` (schema `c8-d2-gate-inputs-1`): manifest `3813f24ac38c7d27645733a06812f890b03e21e1f0a62d9d820fcf5495d27356`
  (the export's `inputs/manifest.json`), every input, pack and vendored pin verified at the start and again at the end
  (`verified_at_end: true`), complete (no pack skipped); the fresh F1 baseline records the same manifest.
  `design.check_gate(record, 'dd+mp256', inventory, <that manifest>)` passes and returns `inputs_manifest_sha256`; the
  same check refuses 570536's record for exactly "no authenticated input-set identity", and the new record for an
  inputs manifest it did not run on.
- **X1-X3, Z19:** coverage complete, both executables rebuilt byte for byte in the source snapshot, every team
  observed, `gmp_library` {exact `4dc20a90…`, profile `4dc20a90…`, reused false}.
- **Same numbers as 570536:** F1's verdict and coverage, F2's totals (|dC8| + 3 SE_d = 4.25e-16: dC8 1.3129e-16, SE_d
  9.774e-17) and per-task statistics, F3's tiers and counters are equal field by field apart from F3's task timings
  (`vs_570536.json`); F4 ×2.574 (free ×2.551, power ×2.636) against ×2.517 (timing only; another node).
- **Seeds:** F2's 49 seeds (base 820262401) were all present in symmetry's log ("0 added, 49 present").

## W9: a claim's memory on a large index (job 570578)

The finding's shape with 8-point tasks: a test-only pilot `--pilot --points 512 --replicates 2 --test-graphs all
--bootstrap-chunk 8 --shards 1 --threads 8 --checkpoint-tasks 256` (24 indices, 6,188,288 tasks, 24,180 checkpoints),
planned once with the tools of b58e9b6 (`pkg/b58e9b6f4afd`, fix round 3: the same executables) and once with this
commit's, each with a fresh seed; then in each package ONE block of the `a_free_L8` index (2,056,192 tasks, 8,032
blocks, a 54.9 MB task file) claimed with `production.py run PLAN --index 5 --threads 8 --max-blocks 1` (the command a
lane runs, bounded to one block), its own peak RSS taken at exit with `getrusage(RUSAGE_SELF)` (`scripts/s4mem.slurm`;
`s4mem.570578.0/claim_{old,new}.json`, `w9_summary.json`):

| Tools | Claim's peak RSS | The index's `est_peak_bytes` | Ratio | Plan's memory suggestion | Claim wall |
|---|---:|---:|---:|---:|---:|
| b58e9b6 (before W9) | **747.0 MB** | 586.6 MB | **1.27** | 1,864 MB | 3.8 s |
| 392ed22 (W9) | **69.6 MB** | 640.3 MB | **0.11** | 1,940 MB | 1.4 s |

(`children_maxrss_kib` is recorded too, but a child forked from the claim, `ldd` or the native worker before its exec,
counts the claim's own pages, so it is not the native worker's peak.)

Before the fix the claim held every task row of its index and peaked above its own estimate (the lane memory guard
and the array memory suggestion consume `est_peak_bytes`); after it the claim streams one block and peaks at a tenth
of the new estimate, which adds one block of rows (256 × 16 KiB) and the plan metadata (24 job entries and 24,173
inventory rows × 2 KiB). The first attempt (570576) planned both campaigns and failed at both claims: the job's own RSS
wrapper ran `production.py` through `runpy` with the wrapper's directory as `sys.path[0]` (`ModuleNotFoundError:
common`); the wrapper sets the tool's directory since 900e590 (and in the uploaded script that 570578 ran). Each plan
directory was deleted after its claim.

## The route-(b) re-freeze and a real gated claim (job 570579)

sharedq <NODE> (8 CPUs, 15 GB), this export's `bin/` (`7741f733…`, `a46f3060…`) and cost model
`cost_models/gmp_symmetry_amd_c8_dd+mp256.json` (`18e50440…`, unchanged: its executable is the gated build), the gate
record of 570574, checked first with this export's `check_gate` and inputs manifest (`check_gate.json`). For each target
`design.py freeze --test-only --numerics dd+mp256` on the J-SWEEP-2 sweep `sweep2-5d7586e9f1ab`, compared with
570539's bundle of the same target (`compare_*.json`, `meta_diff_*.json`), then a test-only plan with a fresh seed
(added to the log with a label), measured and deleted:

| Target | `design.json` vs 570539 | `design_meta.json` fields that differ | Test-only plan: tasks / checkpoints / indices | Plan wall, peak RSS | Largest `est_peak_bytes` (index), memory suggestion |
|---|---|---|---|---|---|
| 1e-3 | byte-identical | the gate entry (sha256, job, host, CPU, path, time, `inputs_manifest_sha256`), pinned tool versions, time, seeds | 2,135,296 / 8,372 / 71 (570539: the same) | 169 s, 0.43 GB | 1.07 GB, 2,561 MB |
| 5e-4 | byte-identical | the same | 5,356,096 / 21,035 / 205 (the same) | 471 s, 0.89 GB | 1.07 GB, 2,549 MB |
| 2.5e-4 | byte-identical | the same | 5,652,928 / 22,652 / 770 (the same) | 496 s, 0.91 GB | 1.54 GB, 3,229 MB |
| 1.35e-4 | byte-identical | the same | 6,398,976 / 26,347 / 2,483 (the same) | 596 s, 0.97 GB | 1.58 GB, 3,282 MB |

Every plan exits 0 with `numerics_route` route b, the gate `42e6d2d8…`, `executable_gated: true` and
`gate_gmp_library` [`4dc20a90…`] (W8); route (b) re-checks the gate entry, now with W18's `inputs_manifest_sha256`
(equal to the bundle's and the pilot's). The bundles stay on BeeGFS in
`<SCRATCH>/c8d2/work/s4des-392ed22d1d02/bundles/` (`s4des.570579.0/bundles.tgz`, `bundles.sha256`); they are
test-only bundles of the sweep, as before (`tests/unit_orchestration.py` `route_b_records` now carries them as the
accepted ones). The lane core-hours equal 570539's (639 / 2,251 / 9,002 / 29,473).

**A real gated claim (W7, W8, W9).** In the 5e-4 plan, one block of index 101 (`a_power_L6`, 13,696 tasks, 54 blocks:
the index with the most tasks whose one block is estimated at no more than 60 core-seconds) was claimed on <NODE>
(`claim_b_5e-4.json`): exit 0 after 63 s, one checkpoint; the worker resolves libgmp `4dc20a90…`, the library the gate
validated (W8: the claim checks it before any pin); no loader override in the job environment and an empty
`preload_order` and `loader_env` in the fingerprint (W7; <NODE> preloads nothing by itself, and <NODE>, the J-VAL-1 node, has no `/etc/ld.so.preload`: `s4val1.570573.0/etc_ld_so_preload.txt`); the OpenMP
team verified (8 of 8); the claim's peak RSS 66 MB against an `est_peak_bytes` of 625 MB (W9).

## Jobs

`sacct -X --duplicates` (`sacct.txt`; times EDT). Core-hours = ElapsedRaw × physical cores (AMD EPYC: 64 cores, 1
thread per core; the Intel sharedq node: 2 threads per core, so AllocCPUS / 2). H7: at most 4 live `c8d2-` jobs on
amdq + amddebugq + amdpreq; the peak was 3 (570572-570574; `admission/h7_admission.jsonl`). Before the first
submission: no live `c8d2-` job. C63d's `c8d3-*` jobs and the other <USER> jobs (`sri_eng_*`) were neither counted
nor touched. amdq/amddebugq with `--exclude=cn112`; no longq; sharedq `--no-requeue`; every job with `--mem` and
`--time` and a `c8d2-` name. Logs: `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); evidence
`<SCRATCH>/c8d2/evidence/{392ed22d1d02,900e5906522a}/` (copied here without the five large files listed in
`large_files.sha256`: the F1 baseline's reference values and F2's rows).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570572 `c8d2-s4build` | build, A-RPL-8 (`scripts/s4build.slurm`, export `392ed22d1d02`) | amddebugq <NODE> | COMPLETED | 1:42 | 1.81 |
| 570573 `c8d2-s4val1` | J-VAL-1, G-BK8 (W2), thread identity (W22), hostile-environment invariance (`scripts/s4val1.slurm`) | amdq <NODE> | FAILED 1:0 (`make test` stopped at the test defect above; every other step passed) | 40:05 | 42.76 |
| 570574 `c8d2-s4flag` | the `dd+mp256` J-FLAG gate (`scripts/s4flag.slurm`) | amdq <NODE> | COMPLETED | 14:07 | 15.06 |
| 570575 `c8d2-gen1-regress` | J-GEN-1 (`slurm/gen/regress.slurm` of the export) | sharedq <NODE> | COMPLETED | 3:36 | 0.24 |
| 570576 `c8d2-s4mem` | W9 before and after (`scripts/s4mem.slurm`) | sharedq <NODE> | FAILED 1:0 (the wrapper's `sys.path[0]`; both plans made and deleted) | 3:20 | 0.22 |
| 570577 `c8d2-s4des` | the re-freeze, first submission | sharedq | CANCELLED while pending (the same wrapper defect) | 0:00 | 0 |
| 570578 `c8d2-s4mem` | W9 before and after, the corrected script (`work/s4-392ed22d1d02/s4mem.slurm`) | sharedq <NODE> | COMPLETED | 2:51 | 0.19 |
| 570579 `c8d2-s4des` | 4 re-freezes, 4 test-only plans, one gated claim (`work/s4-392ed22d1d02/s4des.slurm`, afterok 570574) | sharedq <NODE> | COMPLETED | 30:41 | 2.05 |
| 570582 `c8d2-s4build` | build of 900e590 (identical executables) | amddebugq <NODE> | COMPLETED | 1:40 | 1.78 |
| 570583 `c8d2-s4val1` | J-VAL-1 on 900e590 (`DONE=` 570573's evidence) | amdq <NODE> | COMPLETED | 38:52 | 41.46 |
| **total** | 10 records | | | | **105.56** |

Budget: 105.56 of this task's 120 core-hours. Symmetry's total in this workflow goes from 685.1 to 790.7 core-hours.

## Seeds

Eight fresh seeds, drawn on the Mac (`secrets.randbits(63)`) and checked against the mirror (`setup/seed_precheck.txt`),
then in the jobs against symmetry's live log and added there with labels: 4940946330635124793, 8439688650531764430,
8206153006953290833, 7793555238787648191 (the four route-(b) test-only plans of 570579), 1426164674849951575 and
2305678658136620644 (570576's two W9 plans), 7428002679483604354 and 7165359829991591804 (570578's). The gate added none.
- symmetry's log afterwards: 118 seeds (`seeds/s4_symmetry.json`, sha256 `bfb06c11…`).
- The mirror `designs/forbidden_seeds.json` was merged from it with `tools/seeds.py merge` (110 → 118, the same set;
  a second merge adds nothing; `seeds/sha256.txt`).
- Expanse's log does not hold them yet: they are appended to `../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` for the
  next two-log sync (no Expanse session was opened, by the site rule).

## After the runs (the evidence commit)

- `tests/unit_orchestration.py` `route_b_records`: the 570579 bundles are the accepted ones (frozen bytes, `design.json`
  equal to 570539's, the gate entry with the package's inputs manifest and libgmp `4dc20a90…`, plans non-final and
  final as a non-test plan; another executable and a relabelled input set refused).
- `tests/test_numerics_flags.py` `coverage`: the 570574 record passes `check_gate` as it is, for the package's inputs
  only, with the same libgmp provenance as 570536's.
- The docs name the new record (README, NUMERICS.md, DESIGN.md, HPC.md, PERFORMANCE.md) and the CHANGELOG has the run.

## Files

`scripts/` (`s4.sh`: export, sub, upload; `s4build.slurm`, `s4val1.slurm`, `s4flag.slurm`, `s4des.slurm`,
`s4mem.slurm`), `setup/` (both export checks, the seed pre-checks), `admission/` (the `squeue` snapshots, the H7 lines,
every sbatch, the scancel and the uploads), `logs/`, `sacct.txt`, `seeds/`, `large_files.sha256`, and one folder per
run: `s4build.570572.0/`, `s4val1.570573.0/` (the stopped run), `s4flag.570574.0/`, `gen1.570575.0/`,
`s4mem.570576.0/` (the failed attempt), `s4mem.570578.0/`, `s4des.570579.0/`, `s4build.570582.0/`, `s4val1.570583.0/`.
