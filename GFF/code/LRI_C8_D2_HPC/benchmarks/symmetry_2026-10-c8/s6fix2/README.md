# Stage-6 fix round 2 on symmetry (2026-10-06): the merged head validated

Site rule: symmetry only (user, 2026-10-05: "symmetry is back, so for the moment only use expanse if symmetry is not
enough"); Expanse, personal desktops were not touched. Everything ran from the git-archive export of
**e914701b042b** (`<SCRATCH>/c8d2/pkg/e914701b042b`; `setup/export_check_e914701b042b.json`: 9,033 files
equal to the archive in content and mode). e914701 is the merge of the four fix-round-2 groups (G1 20cc644, G2 2bde93d,
G3 96a0e7b, G4 8544e41, merged as 0b7c180, 3070654, d7b5290, 696db78) plus the integration fixes, the G5 docs and this
folder's `scripts/`; `src/` is unchanged since 5d7586e. The two L8 packs were re-hashed against the export's
`inputs/manifest.json` and hard-linked from `pkg/7a8aad783c31/inputs/packs` (`s2build.570414.0/l8_packs.json`). The Mac
side of the integration is `../../mac_2026-10-c8/s6fix2int/`.

## Verdicts

| Item | Job(s) | Verdict |
|---|---|---|
| Build, **A-RPL-8** | 570414 | **PASS.** Every default and diagnostic executable is byte-identical to the Stage-5 symmetry build of 5d7586e (decimal `619ddf7d…`, gmp `2cc5e88e…`, prof, ratiohist, inspect, c7ref `e696d7f3…`/`7e3c8c92…`, quad differential and ranges, interleave probe); the two sanitizer builds equal 5d7586e's once the export path and build-id are normalized; `make gmp NUMERICS=dd,mp256` gives **`d5df32ac…`**, the gated build (gate records 570210 and 570373), and leaves every default executable unchanged; Boost 1_77 everywhere (`s2build.570414.0/identity.json`). |
| **J-GEN-1** (A-INV-1/2; Y3 on x86-64; the generator's OpenMP environment) | 570417 | **PASS.** `slurm/gen/regress.slurm` of the export (sharedq <NODE>, GCC 11.4): `gen/test_keys.py` **112/112, its UBSan part included**: the four programs built with `g++ -fsanitize=undefined -fno-sanitize-recover=undefined` (libubsan present), the reviewer's key 2^72−1 at n=9 refused by each with exit 2, the edge-count message, no sanitizer report and no output, and classes1..8 clean; `test_run_l8` 6/6, `test_verify_inventory` 25/25, `test_regress` 90/90, `test_handoff_inventory` 17/17, `check_sources` passed; `regress.py --threads 1,8` at L3–L7 (now in `builder_env`): A-INV-2 PASSED. |
| **J-VAL-1** (`make test` on a whole amdq node) | 570415 | **PASS.** `check_venv --strict`; `make test OUTPUT=…` exit 0 in 1,178 s as one command: validate 52 tests (class B through the Y1 binding), **unit_orchestration 60 groups / 72 tests, 0 failed, on Linux with the real worker** (Y2 `omp_env`, `omp_team`, `bench_team` with the real `/proc`; Y6 `fp_complete`; Y7 `cgroup_min`; Y8 `fp_first`; Y10 `bundle_reps`; Y12 `sweep_resume`; Y13 `sweep_seed`, `plan_seed`; Y15's atomic-plan test on Linux; the integration's `doc_examples`; the A-ORC-13 claim and X8 runtime identity with the real `ldd`), test_pipeline 3 parts / 29 tests (Y9, Y10), ast_scan 27 + 45 files 0 findings (Y14), test_regress 90/90, test_handoff_inventory 17/17, merge_scale, check_vendored 35/35 (Y4; one check fewer than the Mac's, the review record is not on the cluster), vendored_isolated 10/10 `--in-place`, the delivery-verifier test, check_inputs 22/22 with 2 skips (Y5), test_profiling 16 (`perf_team`), test_gmp_prefix 8 (`targets`), test_gmp_binding 10 (Y1 on a fake toolchain), test_numerics_flags 11, test_dd_profile 8, sanitize `--capture-check`, workflow, staging; then `assembly_checks.py --exact` 37/37, **`verify_result_tamper.py` 104/104 (Y11)** and `compat_2026.py` exit 0 (max relative difference 0.0); executables unchanged by `make test`. |
| **Y1** (precision tools bound to the worker's GMP; default GMP) | 570416 | **PASS.** `tests/forced_tiers.py --worker bin/c8d2_gmp --threads 64`: passed (154 s; free 29,284 binary128-accepted / 3,541 MP points, as in round 1), its `gmp_binding` names no `GMP_PREFIX`, the system libgmp `4dc20a90…` (`/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1`) and `linked.match` true (tool and worker resolve it). `tests/check_points.py` (450 digits, L3–L8, both backends): passed (60 s), each result with its `binding` (the gmp tool's libgmp matched). Y1's class at the integration: `sanitize.pc_tool`/`verify_pc_tool` compiled the point_checks sanitizer tools against `bin/c8d2_{decimal,gmp}_san` (gmp: no prefix, libgmp matched), and `perf_profile.build_twin(exe=bin/c8d2_gmp)` built the twin as the worker's recorded command plus `-g`, which `same_code()` accepts (every allocated section identical) (`s2prec.570416.0/y1_summary.json`, `y1_class.json`). |
| **Y2** on real Slurm (inherited `OMP_THREAD_LIMIT=1`, `OMP_DYNAMIC=true`) | 570416 (P4), 570418 (direct, array), 570420/570421 (lanes, merge), 570425 (check) | **PASS.** P4: `benchmark.py --lane-shapes 8x8,1x64 --workload p4_L8 --fraction 0.1` with the controls inherited, on amdq <NODE>: `team_sizes_verified` true, every block of both shapes `verified` (16 and 2 blocks), rows identical across shapes. A test-only campaign on sharedq (Intel; `--threads 4`, 24 indices), submitted with both controls exported: the direct `production.py run` (index 11, a_power_L8) and `slurm/run_array.sh` (index 23, b_power_L8; SLURM_ARRAY_TASK_ID set in the allocation) committed with "omp team verified: 4 of 4 threads", the direct run logging "inherited OpenMP controls not passed to the native worker (Y2): OMP_DYNAMIC=true OMP_THREAD_LIMIT=1"; the other 22 indices ran in a real `slurm/submit.sh --lanes 1` drill-mode lane worker and merge on sharedq, both jobs inheriting the two controls (recorded by `scripts/env_probe.sh`: `s2lane/omp_env_job_57042{0,1}.txt`). Of the 24 checkpoints 21 are `verified` (4 of 4) and 3 `unverified` (a_free_L3, a_free_L4, b_free_L4: workers that lived 13–18 ms, 3 samples each, gone before a sample saw their team: G2's "too short to observe", never refused); none `smaller`, no refusal; `status` exit 0, 24 groups merged (`s2chk.570425.0/teams.json`). The first check job (570422) required every verdict `verified` and failed on those three; the criterion was corrected (a run shorter than 0.1 s may be `unverified`), uploaded (`work/s2-e914701b042b/s2chk.slurm`, sha256 `f05f733d…`, the committed script) and run again (570425). |
| **Y6** (incomplete fingerprint) | 570418, 570416 | **PASS.** On a fresh campaign, the first claim with a fake `ldd` (exit 1) first on `PATH`: exit 64, "the runtime fingerprint of the worker on this node (<NODE>) is incomplete: the ldd probe failed …; ldd listed no library", `claim_io` with no native launch, and no `cpu_vendor.json`, no `runtime_identity.json`, no checkpoint. The node survey: `fingerprint_problems` is empty for `bin/c8d2_gmp`, `bin/c8d2_decimal` and `bin/c8d2_gmp_dd+mp256` on amdq <NODE> (EPYC 7532) and for `bin/c8d2_gmp` on sharedq <NODE>; J-VAL-1 ran the real-worker claim on <NODE> (EPYC 7543). The other amdq nodes are not surveyed yet (owed before the pilot, `docs/HPC.md`). |
| **Y7** (cgroup memory limit) | 570416, 570418, 570420 | **PASS.** symmetry's nodes use cgroup v1 for memory (`memory:/slurm/uid_70850/job_<id>`) beside a v2 line without `memory.max`: `lanes.cgroup_memory_limit()` = the smallest finite level, 245 GiB (263,066,746,880) on the exclusive amdq node and 15 GiB (16,106,127,360) on the 15G sharedq allocation, `memory_limit` source `cgroup`; the drill's lane worker logged "memory limit 6.0 GiB (cgroup)". Only the job level is finite there, so the minimum over ancestors equals the first finite level; the looser-step case is the Mac/Linux unit test `cgroup_min`. |
| **Y13** (sweep seed) | 570418 | **PASS.** Inside the job without a seed log, `tools/sweep.py … --plan-only` exits 1 ("give --seeds-log FILE or set C8_SEEDS … nothing planned") and creates no directory; with `--seeds-log $C8_SEEDS` it plans all graphs (16 points × 2) and adds the seed 5638617719944467077 right after the plan (source the sweep directory), then registers the ledger; a rerun says "present". The sweep is never run. |

## Jobs

`sacct -X --duplicates` (`sacct.txt`; times EDT). Core-hours = ElapsedRaw × physical cores (AMD EPYC: 64 cores, 1
thread per core; the Intel sharedq nodes: 2 threads per core, so AllocCPUS / 2). H7: at most 4 live `c8d2-` jobs on
amdq + amddebugq + amdpreq; the peak was 3 (570414-570416 from 02:25:50 to 02:27:29, two of them pending on the build;
`admission/h7_admission.jsonl`). amdq/amddebugq with `--exclude=cn112`; no longq; sharedq `--no-requeue` (the drill's
jobs by `submit.sh`); every job with `--mem` and `--time`; every job named `c8d2-*`; one CPU vendor per campaign (the
Y2 campaign on Intel sharedq only). The other <USER> jobs (`sri_eng_*`, another project) were not counted or touched.
Logs: `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); the drill's in the campaign
(`s2lane/campaign_logs/`, index logs `s2lane/index_logs/`); evidence `<SCRATCH>/c8d2/evidence/e914701b042b/`
(copied here in full).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570414 | build, A-RPL-8 (`scripts/s2build.slurm`) | amddebugq <NODE> (EPYC 7543) | COMPLETED 0:0 | 1:44 | 1.85 |
| 570415 | J-VAL-1 (`scripts/s2val1.slurm`, afterok 570414) | amdq <NODE> (EPYC 7543) | COMPLETED 0:0 | 19:55 | 21.24 |
| 570416 | Y1, Y2 P4, Y6, Y7 (`scripts/s2prec.slurm`, afterok 570414) | amdq <NODE> (EPYC 7532) | COMPLETED 0:0 | 6:28 | 6.90 |
| 570417 | J-GEN-1 (`slurm/gen/regress.slurm` of the export) | sharedq <NODE> (Xeon Gold 6148) | COMPLETED 0:0 | 2:48 | 0.19 |
| 570418 | Y2 direct and array, Y6, Y7, Y13 (`scripts/s2y2.slurm`, afterok 570414) | sharedq <NODE> | COMPLETED 0:0 | 1:22 | 0.09 |
| 570420 | the drill-mode lane worker (`slurm/submit.sh --lanes 1`) | sharedq <NODE> | COMPLETED 0:0 | 0:09 | 0.01 |
| 570421 | its merge | sharedq <NODE> | COMPLETED 0:0 | 0:06 | 0.00 |
| 570422 | the lane check, first criterion (every verdict verified) | sharedq <NODE> | FAILED 1:0 | 0:01 | 0.00 |
| 570425 | the lane check (`work/s2-e914701b042b/s2chk.slurm`) | sharedq <NODE> | COMPLETED 0:0 | 0:00 | 0.00 |
| **total** | 9 records | | | | **30.28** |

Budget: 30.28 of this task's 60 core-hours. Symmetry's total in this workflow goes from 535.6 to 565.9 core-hours.

## Seeds

Two fresh seeds, drawn on the Mac (`secrets.randbits(63)`) and checked against the mirror (`setup/seed_precheck.txt`),
then in the job against symmetry's live log (`tools/seeds.py check`): 5949820605861326415 (the Y2/Y6 test-only campaign
`<SCRATCH>/c8-d2/y2-e914701b042b`, added after its plan with `tools/seeds.py add RUN`) and
5638617719944467077 (the Y13 plan-only sweep `<SCRATCH>/c8-d2/y13sweep-e914701b042b`, added by
`tools/sweep.py` itself). symmetry's log afterwards: 105 seeds (`seeds/s2_symmetry.json`, sha256 `59ec4a58…`); the
mirror `designs/forbidden_seeds.json` was merged from it with `tools/seeds.py merge` (103 → 105, the same set; a second
merge adds nothing; `seeds/sha256.txt`). Expanse's log does not hold them yet: they are appended to
`../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` for the next two-log sync (no Expanse session was opened, by the site rule).
Both campaigns stay on BeeGFS as evidence (6.8 MB and 14 MB; test-only, never a result).

## Files

`scripts/` (`s2.sh`: export, sub, upload; `s2build.slurm`, `s2val1.slurm`, `s2prec.slurm`, `s2y2.slurm`, `s2chk.slurm`,
`env_probe.sh`; J-GEN-1 used `slurm/gen/regress.slurm` from the export), `setup/` (export check, seed pre-check),
`admission/` (the `squeue` snapshots, the H7 lines, every sbatch, the drill's `submit.sh` output and the one upload),
`logs/`, `sacct.txt`, `seeds/`, and one folder per job run: `s2build.570414.0/`, `gen1.570417.0/`, `s2val1.570415.0/`,
`s2prec.570416.0/`, `s2y2.570418.0/`, `s2chk.570422.0/` (the first criterion), `s2chk.570425.0/`, `s2lane/`.
