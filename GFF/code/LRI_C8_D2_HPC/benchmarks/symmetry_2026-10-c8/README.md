# C8(2) evidence on symmetry

symmetry (Perimeter) is the plan's production site. On 2026-10-03 development, validation and profiling compute moved
to SDSC Expanse (site deviation U1, `../expanse_2026-10-c8/README.md`), because symmetry's compute partitions were down
(`stage0/survey_symmetry_2026-10-03.txt`). Symmetry came back on 2026-10-04. The jobs below are the first C8(2) jobs that
ran here. The final J-VAL, the smoke and the pilot run here later.

## Environment and rules

**Environment.**
- `~/c8d2/env.sh`, sha256 `0122a133…`, is recorded by both jobs.
  - It predates the symmetry block of `slurm/env.sh.example` (ec5bae0 and later). It sets `C8_AMDQ_CAP=4`, but not
    `C8_SITE=symmetry` or `C8_SEEDS=<SCRATCH>/c8-d2/forbidden_seeds.json`.
  - J-GEN-3 and the P4 probe need neither. It must be updated from the template before J-VAL or any lane job.
- Ubuntu 22.04, GCC 11.4.0, glibc 2.35, the Boost 1.77 module headers and GMP 6.2.1.

**Data** live on BeeGFS under `<SCRATCH>/c8d2/`: `pkg/<sha12>` (exports), `logs/`, `evidence/<sha12>/` and
`ref/`, never in home. `ref/` holds two copies of the inventory:
- `ref/inventory8_d2_46341a3c0f11` is a partial copy of the published inventory, used by J-GEN-3: `MANIFEST.json`,
  `SHA256SUMS`, `MEMBERS.sha256` and the two builder inventories, 19 MB.
- `ref/inventory8_d2_full_46341a3c0f11` is the full tree: 54 files, 8.36 GB, MANIFEST `46341a3c…`, rsynced from the
  Mac's `LRI_C8_shared/inventory/inventory8_d2`.
  - Job 569788 built the L8 packs from it with `make inputs-l8`. They match the `inputs/manifest.json` pins: free
    `e5dd7271…`, power `3d77d0c4…`.
  - The packs now sit in `pkg/7a8aad783c31/inputs/packs`, and later jobs can hard-link them through `C8_L8_PACKS`.

**Rules.**
- The H7 cap: at most 4 live `c8d2-*` jobs across amdq, amddebugq and amdpreq.
- AMD partitions always with `--exclude=cn112`, and never longq.
- The other <USER> jobs (`lri-prod*`) belong to another project and were never touched.

## Exports

| Record | What it shows |
|---|---|
| `jgen3/export_check_ec5bae006d93.json` | `git archive ec5bae0` into `pkg/ec5bae006d93`: all 5,314 files equal the archive in content and mode. |
| `setup/export_check_7a8aad783c31.json` | `git archive 7a8aad7` into `pkg/7a8aad783c31`: all 5,353 files equal the archive in content and mode. 7a8aad7 is c176881 (the Expanse Stage-4a export) plus the tools-only perf-parser fix; `src/` is unchanged. |

## Jobs

| Job | Where | What it shows | Core-hours | Files |
|---|---|---|---:|---|
| 569770 `c8d2-jgen3` | debugq <NODE> (Intel Xeon Gold 6148, 40 cores), `-N 1 -n 1 --exclusive --mem=180G -t 01:00:00`; 1:43, COMPLETED 0:0 | **J-GEN-3: A-INV-4 passed, identical.** The L7+L8 inventory build on Intel with GCC 11.4 reproduces the published `inventory8_d2`, which J-GEN-2 built on Expanse (EPYC 7742, 128 threads, GCC 13.3). `MEMBERS.sha256` is byte-identical (`e1a77e0d…`), 24,839/24,839 members are equal, and both builder inventories are byte-identical. | 2.29 CPU-h as Slurm counts them (80 logical CPUs); 1.14 physical-core-hours | `jgen3/` (its own `README.md`, `verdict.json`, `compare.json`, `crossnode.json`, the log, the wrapper script) |
| 569788 `c8d2-prof4s` | amddebugq <NODE> (2 × AMD EPYC 7543, NPS4: 8 NUMA nodes × 8 cores), `--exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00`; 24:29, COMPLETED 0:0 | **P4 (J-PROF-4) on symmetry.** Details below. 8x8 is best at 63.42 cost-model s per node-second, with 4x16 at 0.981, 1x64 0.966 and 2x32 0.949. Load + staging is 1.22% of node time at 8x8. Rows are identical across shapes and byte-identical to Expanse 54661771. | 26.12 (64 cores × 1,469 s) | `stage4a/` (`prof4.569788.0/`, `logs/`, `admission/`, `prof4s_summary.json`) |

**Job 569788 in detail.**
- **Source and build.** It ran from the export of 7a8aad7. The worker was built in the job with Ubuntu GCC 11.4.0 (sha256
  `23624153…`); it differs from Expanse's `5c5328af…` by the compiler only.
- **Inputs.** The L8 packs were built from the full inventory copy, with the pins verified, and the fixtures were
  verified.
- **Workload.** `p4_L8` at fraction 0.5: 2,010 tasks, 20,619 cost-model s.

**Notes on 569788.**
- **Submission.** It was submitted by hand (export, export check, `h7_admit.py`, then `sbatch -J c8d2-prof4s`), not
  through `submit_prof4_symmetry.sh`, which would have named it `c8d2-prof4`. The job script came unchanged from the
  export (sha256 `aa1fcb64…`).
- **Queue.** The survey at 17:45 EDT showed 9 idle amddebugq nodes, and the job started at once. The H7 count was 0
  before and 1 with this job (`admission/h7_admit_prof4s.json`, `admission/squeue_before_sbatch.txt`).
- **Time.** 132 s went to the pack build, `make gmp` and the fixture checks, and 1,336 s to the four shapes.
- **Results.** The lane-shape table, the symmetry/Expanse throughput factor (1.09–1.13) and the decisions are in
  `docs/PERFORMANCE.md`, "Stage 4a: profiles on the Stage-3 baseline".
- **perf.** <NODE> has perf 5.15.193 with `perf_event_paranoid` −1, which matters for later symmetry profiling.

## Allocation used

On symmetry so far: 28.4 core-hours, 2.29 for J-GEN-3 (counted at Slurm's logical CPUs) and 26.12 for the P4 job. The
cross-site total against the plan's 5,000 core-hour development cap is in `../expanse_2026-10-c8/README.md`, "Allocation
used".

## Stage 5 site preparation (2026-10-05)

Evidence: `stage5_sites/` (README there).
- **`~/c8d2/env.sh` updated** to the symmetry block of `slurm/env.sh.example` at c8 HEAD 09e8f4a (`C8_SITE=symmetry`,
  `C8_AMDQ_CAP=4`, `C8_SEEDS=<SCRATCH>/c8-d2/forbidden_seeds.json`, the boost/1.77.0 and python/3.11 modules,
  the venv, Slurm on PATH), wrapped in the old file's nounset guard. Old sha256 `0122a133…` (kept as
  `~/c8d2/env.sh.bak-20261003`), new `e5fdb68c…`. Sourced under `set -euo pipefail`: python 3.11.3 from the venv,
  sbatch on PATH.
- **The seed log is the union of both sites' logs.** The first symmetry log (2026-10-03, sha256 `8598da66…`) held an
  empty `"entries"` list (no seed, and not the `c8-d2-seeds-1` layout). `tools/seeds.py merge` of Expanse's log (56
  entries after the J-FLAG F2 registration) rewrote it in the `c8-d2-seeds-1` layout with all 56 seeds (sha256
  `62fd303f…`); a second merge added nothing, and `tools/seeds.py check 820262401` there refuses the F2 base seed.
  `designs/forbidden_seeds.json` is the union of both logs (56 seeds). From now on every new seed goes into both logs
  and the mirror (`docs/HPC.md`, "The seed log").


## Stage 5 on symmetry (2026-10-05)

Evidence: `stage5/` (README there: item verdicts, the job table with core-hours, findings F1-F12 with their status,
deviations, seeds). What happened to the findings since: "Stage 5 fix round, close-out and pre-6" below.
All on the final commit 5d7586e (export `pkg/5d7586e9f1ab`, checked equal to `git archive`), default path only.
- **Exact gates green**: c7ref = the plan's e696d7f3…/7e3c8c92…; J-VAL-2 replays all 3,774 kernels exactly on both
  backends; J-VAL-3 (fresh L=2 seed 2699695239531018284) and G-L8SELF against the symmetry Stage-3 baseline exact;
  sanitizer runs clean.
- **J-SWEEP-2**: the symmetry AMD cost model of the final binary, 48,346 keys, with J-SWEEP-3's Intel 6148 class
  factors: `cost_models/gmp_symmetry_amd_c8.json` (sha256 `a1b6e5d2…`).
- **Smoke, twin, requeue/time-limit drills, sharedq lane drills, design chain (combine partial + final), throughput
  drill** on real Slurm inside the H7 cap; **pilot planned** (`<SCRATCH>/c8-d2/pilot1-20261005`, 179.9
  core-h estimated), NOT submitted.
- **Findings for Stage 6**: native rows differ between Intel and AMD CPUs (x87 `expl`/`logl`; F5); recovery of a
  completed index stops at stale group tables and the result's no-clobber rule (F8); scancelled lane workers leave
  their runtime directories (F7); `verify_result.py` depends on the OpenBLAS kernels (F6); no rchar log in `run` (F9);
  the Stage-4b speedup is x1.16-1.20 on symmetry against x1.39 on Expanse (F10); test-portability failures F1-F4.
- **J-DES-5** (job 570114, sharedq, after the run's commit; `stage5/des5/`): `design.py freeze --test-only` on the
  J-SWEEP-2 sweep at the four targets and `production.py plan --design` of each (not submitted, deleted): A-DES-5
  passes, every cap holds; finding F11 (the 1e-3 design over-allocates free L8, `tools/design.py`). Its freezes are
  the base of the refined cost table (`docs/PERFORMANCE.md`, "Stage 5: the refined cost table").
- Stage 5 on symmetry used 338.82 core-hours (57 job records) plus 2.32 for J-DES-5. The symmetry total so far is
  28.4 + 341.1 = 369.5.

## Stage 5 fix round, close-out and pre-6 (2026-10-05)

User rule (2026-10-05): "symmetry is back, so for the moment only use expanse if symmetry is not enough"; everything
below ran on symmetry or the Mac, on the exact default path except the user-required `dd+mp256` gate and the
`dd+mp256` profile cost sweep of `pre6/` (both with the user's approval).

| Folder | What | Jobs | Status |
|---|---|---|---|
| `stage5/fix/` | Re-validation of the G5 fixes F1-F9 (86e15f4, merged as e7e6589) from the export of 2b3a923 | 570164-570184 (16 records, 54.4 core-h) | F1-F8 **PASS**; F9 PARTIAL, cause **F12** found (pack over-read); seeds pending for Expanse in `stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` |
| `stage5/close/` | Close-out from the export of 68ee571 (F12 fixed in d5dfd38): A-ORC-13 rerun, J-VAL-1, the user-required `dd+mp256` J-FLAG gate | 570208-570212 (5 records, 55.1 core-h) | A-ORC-13 **PASS** (no correction), J-VAL-1 **PASS**, `dd+mp256` gate **PASS** (570210; F4 ×2.530) |
| `stage5/pre6/` | Mac, before the Stage-6 inspection: the F11 fix (`tools/design.py`) and route (b) for `dd+mp256` (23540b2), the cost table with symmetry's own `dd+mp256` factors | none (Mac, seconds) | F11 **fixed**: the 1e-3 design 1,738 instead of 3,963 lane core-hours; `dd+mp256` on symmetry ×0.390-0.399 |
| `pre6/` | On symmetry before the Stage-6 inspection, from the export of 3a250ea (99bbfdd plus job scripts): build and A-RPL-8, the `dd+mp256` profile cost sweep (route (b)'s cost model, J-SWEEP-2's shape), the J-DES-5 re-check with the F11-fixed `design.py` and the route-(b) freezes and plans | 570239-570241 (3 records, 12.6 core-h) | A-RPL-8 **PASS**; `cost_models/gmp_symmetry_amd_c8_dd+mp256.json` (×2.81 over exact); F11 fix **confirmed** (1e-3: 1,738 lane core-h); route (b) works end to end; finding **F13** (route-(b) freezes over-allocate) |
| `pre6b/` | On symmetry before the Stage-6 inspection, from the export of the fix commit 77fab71 itself (job scripts staged outside it): the F13 fix (`design.py`'s integer optimizer, route (b)'s keep-cheaper) on J-DES-5's real data, the eight freezes of `pre6/` and their test-only plans | 570302 (1 record, 4.1 core-h) | F13 fix **confirmed**: exact 1,702 / 5,740 / 22,961 / 74,573, route (b) keeps 638 / 2,241 / 8,963 / 29,328 lane core-h, every SE at its target, equal to the Mac recomputation; every cap holds; executables byte-identical to 570239's |

Findings F1-F12 and where each was closed: `stage5/README.md`, "Findings for the Stage-6 inspection" (Status column).
On Expanse (32e5f2b, `../expanse_2026-10-c8/pre6/`): the seed sync is done (the two logs and the mirror hold the same
90 seeds); the J-EXP-1 rerun (A-EXP-3) is partial (job 54681003, cancelled when Expanse's Lustre failed) and is to be
completed after Stage 6 on the post-inspection commit (`docs/HPC.md`, "Sites: symmetry first"); the user-approved
export deletion is done (`../expanse_2026-10-c8/README.md`). Finding F13 (`pre6/`) is fixed for the Stage-6
inspection (`docs/DESIGN.md`, "Route (b)") and the fix is confirmed on real data (`pre6b/`, job 570302). Symmetry
total so far: 369.5 + 54.4 + 55.1 + 12.6 + 4.1 = 495.7 core-hours.

## Stage-6 fix round 1 (2026-10-06)

Evidence: `s6fix1/` (README there). The merged head of fix round 1 (export of c30bfc5, `src/` unchanged), jobs
570371-570379 (8 records, 39.93 core-hours): A-RPL-8 **PASS** (every default executable byte-identical to the Stage-5
build, the profile build `d5df32ac…` again); thread identity with the observed OpenMP teams (X3) **PASS**, also under an
inherited `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true`; J-GEN-1 **PASS** (X5, X6 on x86-64); J-VAL-1 **PASS** (`make test`,
unit_orchestration 49 groups on Linux with the real worker); X8 on real Slurm **PASS** (another libgmp refused with
exit 64, at run-skip and by all three merges; another host with the same libraries accepted); the `dd+mp256` J-FLAG
gate re-run **PASS** (job 570373, record `2eaaebcf…`, accepted by the fixed `check_gate`; F1/F2/F3 equal to 570210's);
the route-(b) re-freeze with it **PASS** (job 570379: the same designs as pre6b, byte for byte, and the same plans).
`~/c8d2/env.sh` now supplies `C8_AMDQ_CAP` as a default only (X11). Five new seeds, pending for Expanse's log. Symmetry
total: 495.7 + 39.9 = 535.6 core-hours.


## Stage-6 fix round 2 (2026-10-06)

Evidence: `s6fix2/` (README there). The merged head of fix round 2 (export of e914701, `src/` unchanged), jobs
570414-570425 (9 records, 30.28 core-hours): A-RPL-8 **PASS** (every default executable byte-identical to the Stage-5
build, the profile build `d5df32ac…` again); J-GEN-1 **PASS** (Y3: `gen/test_keys.py` 112/112 with its UBSan part on GCC
11.4); J-VAL-1 **PASS** (`make test`, unit_orchestration 60 groups on Linux with the real worker, verify_result_tamper
104/104); Y1 **PASS** (forced tiers and point checks through the binding with the default GMP; the sanitizer tool and
the profiler's twin bound); Y2 **PASS** on real Slurm with `OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true` inherited (P4 8x8 and
1x64 `team_sizes_verified`; direct, array and a drill-mode lane run: 21 of 24 checkpoints verified 4 of 4, three
workers of 13-18 ms unobservable, none smaller); Y6 **PASS** (a failing ldd refused with 64, nothing pinned or run);
Y7 **PASS** (the cgroup limit on both allocations); Y13 **PASS** (the sweep registers its seed after its plan, and is
refused in a job without a log). Two new seeds, pending for Expanse's log. Symmetry total: 535.6 + 30.3 = 565.9
core-hours.


## Stage-6 fix round 3 (2026-10-06)

Evidence: `s6fix3/` (README there). Fix round 3 changed `src/kernel.hpp` (Z4, and Z3's hook refusal), so every kernel
executable changed: decimal `a18ce425…`, gmp `7741f733…`, `dd+mp256` `a46f3060…` (c7ref unchanged). Exports of 9976391
and b58e9b6 (a tests-only fix found by J-VAL-1 here), jobs 570533-570542 (10 records, 95.47 core-hours): the Z4 loader
comparison with a42cfb7 on real G-files of every (sector, L) **byte-identical**; J-VAL-2 **PASS, exact** (all 3,774
kernels, both backends, against c7ref; point checks); J-VAL-3's exact parts **PASS** (thread identity, G-BK8, forced
tiers through the new source binding); A-RPL-7 G-L8SELF **exact** against the Stage-3 baseline and against a42cfb7's
build; J-VAL-1 **PASS** (570541; 570534 stopped on a test-portability defect, fixed in b58e9b6); J-VAL-4 and J-GEN-1
**PASS**; the `dd+mp256` gate **PASS** on the new build (570536, record `a8de4037…`, the same F1/F2/F3 values as 570373);
the profile cost model re-measured (`cost_models/gmp_symmetry_amd_c8_dd+mp256.json`, `18e50440…`) and the route-(b)
bundles re-frozen (570539: the same choices, +0.1-0.5% cost). Five new seeds, pending for Expanse's log. Symmetry total:
565.9 + 23.7 (s6res2) + 95.5 = 685.1 core-hours.


## Stage-6 fix round 4 (2026-10-06)

Evidence: `s6fix4/` (README there). Fix round 4 has no `src/` change. Exports of 392ed22 and 900e590 (a tests-only fix
found by J-VAL-1 here), jobs 570572-570583 (10 records, 105.56 core-hours): A-RPL-8 **PASS** (every executable
byte-identical to fix round 3's); J-VAL-1 **PASS** (570583; 570573 stopped on a test-portability defect, fixed in
900e590); W2's G-BK8 row rule **PASS** on real rows (equal to 570535); W22's full thread identity **PASS**; J-GEN-1
**PASS** (W6 under UBSan and ASan); the `dd+mp256` gate **PASS** again with the input set W18 requires (570574, record
`42e6d2d8…`, the same F1/F2/F3 values as 570536); the route-(b) bundles re-frozen (570579, the same designs) with a real
gated claim (W7, W8: libgmp `4dc20a90…`); W9 measured before and after on a 2,056,192-task index (747 MB, 1.27× the
old estimate; 70 MB, 0.11× the new one). Eight new seeds, pending for Expanse's log. Symmetry total: 685.1 + 105.6 =
790.7 core-hours.

## L8 pilot preparation (2026-10-06; NOT submitted)

Evidence: `pilot/` (README there, with the exact submit sequence for the host). Export `pkg/ba68f401e46e` of the final
head ba68f40 (10,385 files equal), L8 packs re-hashed and hard-linked, build 570620: A-RPL-8 **PASS** (decimal
`a18ce425…`, gmp `7741f733…`, inspect, c7ref; the job's own inspect-record check misread the quoted Boost version, rechecked
from its evidence). Runtime-fingerprint survey of every reachable amdq node (570621-570634, 14 nodes): one identity,
`04f1e51dfc2e…`, on all of them (complete fingerprints, no preload, libgmp `4dc20a90…`); 14 nodes unsurveyed
(allocated for 19-22 h, reserved, down, or cn112). The exact pilot planned in sharedq job 570635 into
`<SCRATCH>/c8-d2/pilot1-20261006-ba68f401e46e` (seed 3049594997687674958; 179.9 core-h, 39 indices, largest
4,796 s on an 8-core lane). No lane worker, merge or probe submitted. 16 records, 0.61 core-hours. Symmetry total:
790.7 + 0.6 = 791.3 core-hours.
