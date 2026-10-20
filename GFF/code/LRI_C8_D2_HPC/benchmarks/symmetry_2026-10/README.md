# Cluster validation of the 2026-10-02 revision (symmetry and Expanse)

Real runs made by the coordinator on the package at commit `572a956` (the revision before fix round 1), against
`fb64c47` (the package as delivered). Symmetry: GCC 11.4, `module load boost/1.77.0`, system GMP 6.2.1, Python 3.11
venv (`~/c7d2_prod/env.sh`), work directory `<SCRATCH>/c7d2_fix`. Fix round 1 changed tests, tools, the
Makefile's non-compile lines and docs, not `src/` or the compile commands; see `CHANGELOG.md` for what is re-validated.

**Packed raw evidence.** To keep the review diff small, the bulky raw files are packed in `raw_evidence.tgz`:
the campaign folders (`campaigns/`, `revalidation_c856528/campaigns/`), the `make_test*.log` files of both validations,
`evidence/drills/smoke1_{before,after}.sha256`, `evidence/drills/calibration.json` (identical to the shipped
`tools/calibration.json`) and `evidence/drills/victim_copy.json`. Run `tar xzf raw_evidence.tgz` in this folder to
restore them at the paths named in the tables below; `tar tzf` lists them.

## Jobs and what they show

| Job(s) | Where | What it shows | Files |
|---|---|---|---|
| 567518 | symmetry <NODE> (AMD EPYC 7543), `scripts/validate.slurm` | **D1:** `fb64c47` and `572a956` builds byte-identical, and equal to the 2026 production binaries (decimal `e696d7f3…`, gmp `7e3c8c92…`); `make -n` differs only by the added build-record step. Real build records (GCC 11.4, `BOOST_LIB_VERSION` 1_77, GMP 6.2.1, optimized). **make test** passed: exact replay gate with 0 difference in every subset row, orchestration suite, input regeneration, workflow and staging for both backends. **make test-full** passed: `validate --full` 3,511/3,511 kernels for both backends through the exact gate (gmp: all 1,814 rows with mp > 0 identical, 0 normalized difference), 140 + 140 point checks at 450 digits, archived reassembly (max abs error 3.6e-12). `verify_delivery --strict` passed (4424 files). Boost 1.86 headers (`-I`): base and final both compile under GCC 11.4. | `logs/c7d2-validate_567518.out`, `evidence/d1_*.txt`, `evidence/make_n_*.txt`, `evidence/make_test*.log`, `evidence/verify_strict.json`, `evidence/boost186*` |
| 54583692, 54583699 | Expanse debug (GCC 13.3) | **Boost (host finding H1):** with the real Boost 1.86 headers (`-I$BOOST_ROOT/include`) base and final both compile; with the system Boost 1.66 in `/usr/include` (what an Expanse build sees after `module load boost/1.86.0`, which sets only `BOOST_ROOT`, not `CPATH`) base fails with the `exponential<T>` error and final compiles. | `evidence/boost186_expanse.out`, `evidence/boost186b_expanse.out` |
| 567523-567526 (arrays), 567527 (merge) | symmetry `sharedq`, 2-thread test plans | **Drill 1, smoke:** `C7_MAX_ARRAY=8` gave four arrays with offsets 0/8/16/24 and an `afterok` merge; all completed; `status` exit 0; `C7_test_result.json` written. | `evidence/drills/smoke1_*`, `campaigns/smoke1/` |
| 567582 | symmetry | **Drill 4, status line:** after a checkpoint was deleted, `status` named index 4 and printed its window line; run from a shell with stale `C7_RUN`, `C7_PACKAGE`, `C7_INDEX_OFFSET` and `C7_MAX_ARRAY`, it reran exactly index 4 (offset 0 + array 4); the recomputed checkpoint is scientifically identical to the deleted one. | `evidence/drills/smoke1_window.out`, `smoke1_status_rerun.txt`, `victim_copy.json` |
| 567600 | symmetry | Merge-only `resubmit.sh`: groups skipped, identical result kept; 102 campaign outputs byte-identical before and after. | `evidence/drills/smoke1_resubmit_mergeonly.out`, `smoke1_after.sha256` |
| 567603-567606 (arrays), 567607 (merge, cancelled), 567629 (resubmitted array), 567630 (merge) | symmetry | **Drill 2, recovery:** a stale exported `C7_INDEX_OFFSET` is ignored; `resubmit.sh` refused with 65 while merge 567607 was queued; `scancel --state=PENDING` cancelled the whole unsplit throttled pending record 567605_[3-7] (Slurm 21.08); after the merge was cancelled, recovery resubmitted exactly the missing indices 20-23 with an `afterok` merge; every index 0-27 ran exactly once with index = offset + task; the guards (`--export-file` in `C7_SBATCH_ARGS`, inherited `SBATCH_CLUSTERS`) exited 64, submitted nothing and left no lock. | `evidence/drills/rec_*`, `guard_*.out`, `campaigns/recovery1/` |
| 567634-567637 (arrays, `--hold`), 567638 (merge); 567635 and 567638 cancelled; 567639 (resubmitted array), 567640 (merge) | symmetry | **Drill 3, lock and live tasks:** two `resubmit.sh` started together; one resubmitted only indices 8-15 with a merge `afterok` on the new array and on each of the 20 held live tasks; the other exited 75 with nothing submitted; the lock was released. After `scontrol release` all 29 jobs completed and each index ran exactly once. | `evidence/drills/lock_*`, `campaigns/lock1/` |
| 567667 | symmetry <NODE> (AMD EPYC 7543, 64 threads), `scripts/c7d2_calib.slurm` | **Drill 5, decimal calibration:** every job of a decimal plan (`--multiplier 16 --replicates 8 --shards 1 --checkpoint-tasks 1024`) run on one node; `tools/calibrate.py --update` filled the decimal rows, now the shipped `tools/calibration.json`. | `evidence/drills/calib_plan.json`, `calibration_decimal.json`, `calibration.json`, `logs/c7d2-calib-dec_567667.out`, `logs/calib_idx*.log` |
| 567668 | symmetry <NODE> (AMD EPYC 7532, 64 threads), `scripts/c7d2_thru.slurm` | **Drill 6, throughput (A-M4):** five L7 shards (3 free, 2 power) of about 13.3k estimated core-seconds, 1024-task blocks: busy-core utilisation sum(task seconds)/(64 x wall) = 0.909-0.947 (target >= 0.80); OpenMP efficiency inside the native calls 0.956-0.968. | `evidence/drills/throughput.json`, `logs/c7d2-thru_567668.out`, `logs/thru_idx*.log` |

| 567730 | symmetry <NODE> (AMD EPYC 7543, 64 threads), `backend_ratio/c7d2_calib_gmp.slurm` (package `c856528`; its work directory is named `calib_gmp_<NODE>` although it ran on <NODE>) | **Same-hardware backend ratio:** the drill-5 plan (same seed 6948572463051812907, same 20 jobs, `--multiplier 16 --replicates 8 --shards 1 --checkpoint-tasks 1024`) run with the gmp backend; `calibrate.py` output not applied to the shipped file. Decimal/gmp per proxy unit on EPYC 7543: free L3-L7 1.14, 1.02, 0.89, 1.00, 1.29; power L3-L7 0.82, 1.04, 1.30, 1.67, 2.00. This gmp run agrees with the production gmp rows (mixed EPYC 7532/7543 lanes, M=4096) within 4% for L >= 6 and within 11% everywhere. | `backend_ratio/` (`backend_ratio_same_hw.json`, `calibration_gmp_<NODE>.json`, `c7d2-calib-gmp_567730.out`, `calib_gmp_plan.json`, `ratio.py`, `logs/calibgmp_idx*.log`) |

**CPU models.** symmetry <NODE>-<NODE> are AMD EPYC 7532 and <NODE>-<NODE> AMD EPYC 7543 (logged in job outputs for <NODE>,
<NODE>, <NODE>-<NODE>, <NODE> and <NODE>-<NODE>, <NODE>, <NODE>-<NODE>, <NODE>-<NODE>; <NODE> and <NODE> are inferred from the
range). The 2026 production's gmp calibration rows therefore mix EPYC 7532 (<NODE>-<NODE>) and EPYC 7543 (<NODE>-<NODE>)
lanes.

`scripts/drill_env.sh` is the shell setup of drills 1-4 (`-p sharedq --mem=1900M`, plans
`--points 8 --replicates 4 --test-graphs 2 --shards 4 --threads 2 --checkpoint-tasks 64`).

## Production shares

`production_shares.py` derives the cost and variance shares of the 2026-09-30 production (the run itself is not in
the package) and the MC-scaling projections quoted in README and `docs/HPC.md`; `production_shares.json` is its
output: 8,892 task core-hours; power 59.9% of task CPU for 0.76% of Var(C7); primitives 14.4% of task CPU for 7.4e-5
of Var(C7) (primitive SE 0.0045 from `graph_replicates.csv`; the same method reproduces the free-L7 SE 0.51869).

## Re-validation of fix round 1 (commit `c856528`)

Fix round 1 changed the Makefile's compile lines (now `override`, with the exact command passed to
`build_record.py`), the tests and the submission path. All files are under `revalidation_c856528/`.

| Job(s) | Where | What it shows | Files |
|---|---|---|---|
| 567686 | symmetry <NODE> (AMD EPYC 7532), `validate2.slurm` (`scripts/validate.slurm` pointed at `final2`, a `git archive` of `c856528`) | **D1:** `fb64c47` and `c856528` builds byte-identical, and equal to the 2026 production binaries (decimal `e696d7f3…`, gmp `7e3c8c92…`). The new build records hold the real compile command, `required_flags_present: true`, `optimized: true`. Boost 1.86 headers (`-I`): base and final compile. **make test**, **make test-full** (3,511/3,511 kernels for both backends through the exact gate) and `verify_delivery --strict` passed. | `c7d2-validate2_567686.out`, `evidence/` |
| 567693, 567694, 567699, 567700 (arrays), 567701 (merge) | symmetry `sharedq` | **Smoke drill:** four offset arrays and an `afterok` merge completed; `status` exit 0; `C7_test_result.json` written. | `evidence/drills/smoke2_*`, `campaigns/smoke2/` |
| none submitted | symmetry | **HR2, changed pinned tool:** a line appended to `tools/assemble.py` after planning, with one checkpoint removed: `status` warned and exited 1, `resubmit.sh` exited 64 and submitted nothing (8 jobs in the queue before and after); after the file and the checkpoint were restored, `status` exited 0. | `evidence/drills/smoke2_status_toolchange.txt`, `smoke2_resubmit_toolchange.out` |

## Re-validation of fix round 2 (commit `d7aeaae`)

Fix round 2 changed:
- the Makefile link-word rule and the build-record probe (R1);
- signal cleanup in `production.py run` and `run_array.sh` (R2);
- the primitive budget and projections (R3);
- cost-model validation (R4);
- calibration provenance (R5).

All files are under `revalidation_d7aeaae/`. The bulky ones (campaign folders, `make_test*.log`) are packed in that
folder's `raw_evidence.tgz`.

| Job(s) | Where | What it shows | Files |
|---|---|---|---|
| 567732 | symmetry <NODE> (AMD EPYC 7543), `validate3.slurm` (on a `git archive` of `d7aeaae`) | **D1:** `fb64c47` and `d7aeaae` builds are byte-identical and equal to the 2026 production binaries. The build records show `required_flags_present: true`, `optimized: true`, `_OPENMP` 201511, `__FAST_MATH__` unset and `__FINITE_MATH_ONLY__` 0. Boost 1.86 headers (`-I`): base and final compile. **make test** passed, including `sigterm_cleanup_run_and_run_array` (26/26 orchestration tests); **make test-full** and `--strict` passed. On the login node: `~/c7d2_prod/env.sh` sets none of CPPFLAGS, CXXFLAGS, LDFLAGS, LDLIBS or LIBS; default `make -n` is unchanged; `LDFLAGS=-O0` stops make with the link-word message; `-L…`/`-Wl,…` pass. | `c7d2-validate3_567732.out`, `evidence/` |
| 567733, 567738, 567739, 567740 (arrays), 567741 (merge) | symmetry `sharedq` | **Smoke drill:** four offset arrays and an `afterok` merge completed; `status` exit 0; `C7_test_result.json` written. | `evidence/drills/smoke3_*`, `campaigns/smoke3/` (packed) |
| 567745 (scancel), 567750 (time limit), 567764 (resubmitted array), 567765 (merge) | symmetry `sharedq`, `C7_STAGE=1`, scratch on BeeGFS via `env_tmpdir.sh` | **R2 cleanup on real Slurm:** a running element was cancelled with `scancel`, and another ran past `--time=1` (TIMEOUT). Both logged "stopped by signal 15". Each element's runtime and staging directories, present before the signal, were gone afterwards. No temporary checkpoint was left, and committed blocks were kept. `status` named both indices. `resubmit.sh` completed the campaign, and index 4 resumed at its second block. | `evidence/drills/kill3_*` (`kill3_observed.txt` is the transcript), `campaigns/kill3/` (packed) |

## Re-validation of fix round 3 (commit `3cef517`)

Fix round 3 changed two things:
- **IR2-01:** the scheduler identity now comes from the real uid.
- **IR2-02:** signals arriving at the launch boundary are handled, in both `production.py` and `run_array.sh`.

The Makefile and `src/` are unchanged since `d7aeaae`. All files are under `revalidation_3cef517/`; the campaign
folders and `make_test*.log` are packed in that folder's `raw_evidence.tgz`.

| Job(s) | Where | What it shows | Files |
|---|---|---|---|
| 567788 | symmetry <NODE> (AMD EPYC 7543), `validate4.slurm` (on a `git archive` of `3cef517`) | **D1** identical to the 2026 production binaries. **make test** passed: 26/26 orchestration tests, including the foreign-USER fake-Slurm suites and both launch-boundary signal tests under bash 5.1. **make test-full** and `--strict` passed. | `c7d2-validate4_567788.out`, `evidence/` |
| 567789-567792 (held arrays), 567793 (merge, cancelled), 567794 (merge) | symmetry `sharedq`, run as uid 70850 (<USER>) with `USER=LOGNAME=nobody` | **IR2-01 on real Slurm:** a second `submit.sh` refused with 65, naming the live indices 0-27 and the queued merge. `resubmit.sh` refused with 65 while the merge was queued. After it was cancelled, resubmit skipped all 28 live indices and submitted only a merge `afterok` on each live task. After `scontrol release`, every index ran exactly once, `status` exited 0, and `C7_test_result.json` was written. | `evidence/drills/id4_*`, `campaigns/id4/` (packed) |
| 567819 (immediate scancel), 567820 (mid-run scancel), 567821, 567822 (recovery) | symmetry `sharedq`, `C7_STAGE=1`, scratch on BeeGFS | **Cleanup:** 567819_4 was cancelled the moment it reached RUNNING; the cancel landed during staging, 2 s in, and its staging directory was removed. 567820_9 was cancelled 40 s into the native work: its runtime and staging directories, listed just before, were removed, and the log reads "stopped by signal 15". No temporary checkpoint was left, recovery completed the campaign (`C7_result.json`, status 0), and nothing was left in scratch. | `evidence/drills/kill4_*` (`kill4_observed.txt`), `campaigns/kill4/` (packed) |
