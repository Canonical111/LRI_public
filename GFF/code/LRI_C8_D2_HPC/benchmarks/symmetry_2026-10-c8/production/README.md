# C8(2) production on symmetry: preparation (2026-10-06), NOT submitted

This folder prepares the C8(2) production campaign chosen by the user on 2026-10-06
(`LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`, "USER DECISION (2026-10-06)"): relative SE 2.5e-4 under the approved `dd+mp256`
profile, route (b), on 8 symmetry AMD nodes. One batch (K = 1) of the bundle
`<SCRATCH>/c8-d2/designs/pilot1-20261006-ddmp256-2.5e-4` (`design_meta.json` `6afb6dd6…`; the exact pilot's
allocation kept and re-costed under the profile; predicted SE 11.50, 14,465 lane core-h at the pilot's η_node 0.837).

Here the gated profile executable was built in the pilot's export, the AMD nodes were surveyed with the production
executable, and the campaign was planned in a plan job. **No lane worker, merge or start-latency probe was submitted,
and no window was opened.** The host submits (section 6) after C63d agrees to the 8-node window (k = 9 live AMD-pool
jobs for this session) and the window's DECISIONS line is written.

Site rules: symmetry only. Expanse, personal desktops were not touched. amdq/amddebugq always ran with
`--exclude=cn112`. No longq. sharedq ran with `--no-requeue`. Every job had `--mem`, `--time` and a `c8d2-` name. H7: at
most 4 live `c8d2-` AMD-pool jobs (the peak was 4, during the survey batches; `admission/h7_admission.jsonl`). C63d's
`c8d3-val1-*` jobs (570678 on <NODE>, then 570736) were neither counted nor touched. The pilot campaign and the bundle
were only read.

## 1. The profile executable (job 570719)

`scripts/prbuild.slurm` ran `make gmp NUMERICS=dd,mp256` in the export `<SCRATCH>/c8d2/pkg/ba68f401e46e`
(commit ba68f40) on amddebugq <NODE> (EPYC 7543, Ubuntu GCC 11.4.0), 20 s. Evidence: `prbuild.570719.0/`
(`identity.json`; BeeGFS `<SCRATCH>/c8d2/evidence/ba68f401e46e/prbuild.570719.0/`).

| Check | Result |
|---|---|
| `bin/c8d2_gmp_dd+mp256` | **`a46f3060a27f4d5e3af19023fc5bb67a7ca2dc6c4242e671ef4bdb9427254c8c`**, the build the `dd+mp256` J-FLAG gate 570574 passed |
| default executables | unchanged: `bin/c8d2_decimal` `a18ce425…`, `bin/c8d2_gmp` `7741f733…`, `bin/c8d2_inspect` `38361979…`, `bin/ref/c7d2_decimal` `e696d7f3…`, `bin/ref/c7d2_gmp` `7e3c8c92…`, and every build record (`bin_before.sha256` = `bin_after.sha256` on them) |
| new files | exactly `bin/c8d2_gmp_dd+mp256` and its `.build.json` (`905917a6…`) |
| export outside `bin/` | unchanged (size and mtime of all 10,400 files; `prbuild.570719.0/tree_listings.sha256.txt`; the listings stay on BeeGFS) |
| build record | equal to the gated build's record (`s6fix4/s4build.570582.0`) in every field but `build_directory`, `host` and `created_utc`; NUMERICS `dd+mp256`, `macro_overrides []`, no development, Boost `1_77`, `build_directory` = this export (W3) |
| the plan's own checks | `production.describe(exe, 'dd+mp256')` and `production.read_build_record(..., required=True)` (Z3) accept it |
| gate | `design.check_gate` on `s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json` (sha256 `42e6d2d8…`, against this export's inputs `3813f24a…`) passes; its profile executable is this build; its libgmp `4dc20a90…` is this build record's (W8) |
| runtime fingerprint on <NODE> | complete, no loader override, key **`04f1e51d…`** = the pilot's pin |

## 2. Node survey with the production executable

`scripts/prsurvey.slurm` (the pilot's survey with the executable `bin/c8d2_gmp_dd+mp256` and its sha256 swapped in)
computed the package's runtime identity of a staged copy, as a claim does, on every reachable candidate node: 12 jobs
570723-570734 on amddebugq, `--nodelist`, at most 4 live. With the build job's fingerprint on <NODE> that is 13 nodes.
Comparison: `scripts/prsurvey_compare.py` → `survey/survey.json`; node states at the survey in
`survey/amdq_nodes_at_survey.txt`.

**All 13 have the same runtime identity `04f1e51dfc2e89b039f567261a341d5723806390bdd1a222245ac5c2584c360b`** (libgmp
`4dc20a90…`, glibc 2.35, complete fingerprint, no loader override, no `/etc/ld.so.preload`), the key the pilot pinned.

| Node | Survey job | CPU | Production pool |
|---|---|---|---|
| <NODE> | 570719 (build) | EPYC 7543 | **yes** |
| <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE> | 570725-570734 | EPYC 7543 | **yes** (also in the pilot's survey) |
| <NODE> | 570724 | EPYC 7543 | **yes, new**: `down*` at the pilot's survey, back since its reboot at 15:27 EDT today |
| <NODE> | 570723 | EPYC 7532 (Zen 2) | no: newly reachable, but Zen 2 |
| <NODE>, <NODE>, <NODE> | (pilot 570621-570623) | EPYC 7532 | no: Zen 2 |
| <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE> | none | | no: allocated to other users (<NODE>-091: reservation `shotinli_118` until 2026-11-01) |
| <NODE> | none | | no: `resv` |
| <NODE> | none | | no: `down*` (Not responding) |
| cn112 | none | | no: excluded by rule |

**Usable production nodes (12 surveyed EPYC 7543):** <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>,
<NODE>, <NODE>, <NODE>. Eight are needed; 11 were idle at the survey (<NODE> held a C63d job).
The pool is EPYC 7543 only for the pilot's reasons: lane class factor 1.0 against 1.5 on an unknown class (the profile
cost model lists only the 7543), and one CPU model for every measured cost. Zen 2 nodes would be correct (same identity,
bitwise equal rows, F5), only slower to schedule.

```
X=<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,cn112
```

This is the given list with <NODE> taken out (surveyed now, EPYC 7543, the same identity). The given list (<NODE>
excluded, 11 pool nodes) is equally valid; <NODE> was `down*` until its reboot today, so keeping it out is the host's
judgement.

## 3. The plan (job 570722)

- **Seed `6274393056071737300`**, fresh (`secrets.randbits(63)` on the Mac, 20:12:54Z), checked against the mirror and
  symmetry's log (both 119 seeds; `setup/seed_precheck.txt`).
- `scripts/prplan.slurm` on sharedq <NODE> (`-c 8 --mem=15G -t 01:00:00 --no-requeue`), 9:21; the plan itself 9:13, peak
  RSS 0.86 GiB. It ran, with the arguments in the file so the approval reaches the tool byte for byte:

  ```
  slurm/plan.sh <SCRATCH>/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e \
    --design <SCRATCH>/c8-d2/designs/pilot1-20261006-ddmp256-2.5e-4 --numerics dd+mp256 \
    --approved-numerics-change "user check-in 2026-10-05 (dd+mp256 approved for production after the pilot) and user decision 2026-10-06 (production at 2.5e-4, dd+mp256, 8 nodes)" \
    --cost-model <SCRATCH>/c8d2/pkg/ba68f401e46e/cost_models/gmp_symmetry_amd_c8_dd+mp256.json \
    --backend gmp --threads 8 --checkpoint-tasks 256 --index-hours 1.5 \
    --forbid-seeds-from <SCRATCH>/c8-d2/forbidden_seeds.json --seed 6274393056071737300
  ```

  Task length, smallest chunk and task cap at their defaults (60 s, 256 points, 120 s): the freeze's caps sizing, as in
  J-DES-5 and the route-(b) re-freeze 570579.
- **Campaign `<SCRATCH>/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e`**, manifest sha256
  **`be215e0e89bd5c323b725770dcdcbba4c4063628b7bd1373406e1ed9b12a1a70`** (copy `plan/prplan.570722.0/manifest.json`),
  774 MB and 1,282 files on BeeGFS. The plan registered its seed in symmetry's log before publishing (Z15; 120 entries,
  sha256 `7660055d…`); `plan.sh`'s add said "present"; the job is in the ledger with role plan.
- **Recorded** (`plan/prplan.570722.0/plan_checks.json`, all 20 checks true): non-test; numerics `dd+mp256`;
  `numerics_route.route` **b**; **`executable_gated` true**; executable `c8d2_gmp_dd+mp256` `a46f3060…`; gate 570574
  (`42e6d2d8…`, inputs `3813f24a…`, libgmp `4dc20a90…` for both tools) and `gate_gmp_library` [`4dc20a90…`]; bundle
  `6afb6dd6…` (design `4b9b6416…`, K = 1, r = 128 everywhere, pinned copy in `design_bundle/`); the bundle's approval
  ("user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)") and the
  plan's (the reference above, also `approved_numerics_change`); the exact pilot (`pilot1-20261006-ba68f401e46e`,
  manifest `828fb586…`, seed 3049594997687674958); cost model `18e50440…` (numerics `dd+mp256`, executable `a46f3060…`,
  EPYC 7543); seed and seed log; threads 8, checkpoint tasks 256, index hours 1.5.
- `production.py status --fast` (in the job): exit 1, "1129 incomplete job indices: 0-1128", the approval printed, no
  WARNING about pinned tools (`plan/prplan.570722.0/status_before_submit.txt`).

## 4. The estimate and the schedule

From the plan's own index estimates (`scripts/prod_lanes.py plan` → `plan/prod_lanes.json`).

| Quantity | Value |
|---|---|
| Indices / tasks / checkpoints | **1,129** / **6,192,256** / **24,848**; 28,485 projected files |
| Estimated work | **12,025 core-h** (free L8 8,345 over 774 indices; free L7 2,518 over 234; power L8 752 over 70; power L7 230 over 22; L3-L6 180 over 29); 1,670 lane-h at the planner's 0.9, 1,518 at the pilot's measured 0.990 |
| Largest index | a_power_L8 index 596, 38,848 core-s: **5,396 s (1.50 h) on an 8-core lane** (4,905 s at 0.990); median index 38,796 core-s, so almost every index is a full 1.5-h index |
| Claim requirement | est / (8 × 0.9) × 1.5 + 300 s = 8,393 s (2.33 h) for a full index (f = 1.0 on EPYC 7543): a lane stops taking full indices 21.67 h into a 24-h job |
| Peak memory per lane | largest `est_peak_bytes` **1.48 GiB** against 245G / 8 = 30.6 GiB per lane; the guard (8 × peak ≤ 0.85 × 245 GiB, 26.0 GiB per lane) holds with ×17.6 headroom |
| Merge | 24 groups, 6,192,256 rows, 1 pass (2 for free L7 and L8, fan-in 64); projected **583 s** for the largest group (a_free_L8) at the planner's conservative rates; the plan suggests `--time 01:00:00`. The Expanse merge-scale run (54643361) measured 40,000 rows/s per process in phase 1 (planner: 4,000) and **86 MB peak RSS per merge process** (24 processes ≈ 2 GB) |
| Merge job | `C8_MERGE_TIME=02:00:00` (the runbook default, above the plan's suggestion, for the assembly of 6.19 million graph-replicate rows, which the projection leaves out), `C8_MERGE_MEM` 64G and `C8_MERGE_JOBS` 24 (defaults), on one amdq node |

**Wall-time schedule on 8 nodes (8 × 8 lanes), symmetry's 24-h limit.** The simulation applies the lane rule of
`tools/lanes.py`: a free lane takes the heaviest unclaimed index whose claim requirement fits the job's time left; a
lane with nothing that fits stops; a worker ends when its 8 lanes have stopped. All workers start at t = 0. Three speed
models: planner (est / (8 × 0.9)), pilot (est / (8 × 0.990), the pilot's measured in-index efficiency) and stress (pilot,
with free L8 ×1.08, the exact cost model's free-L8 under-estimate in the pilot).

| Model | No 24-h limit: wall on 8 nodes | Round 1 (8 workers × 24 h) | Left after round 1 | Round 2 (N = min(8, ⌈left/16⌉)) | Total |
|---|---:|---|---|---|---|
| planner | 26.9 h | workers end at 22.5-23.3 h; 974 indices; 11,654 core-h | **155 indices, 1,645 core-h** (a_free_L7 92, b_power_L8 32, power L7 22, L6 9) | 8 nodes: **4.5 h**, ≤ 1,980 core-h | about 27.7 h, ≤ 13,634 core-h |
| pilot | 24.5 h | 21.8-23.1 h; 1,057 indices; 11,494 core-h | **72 indices, 770 core-h** (a_free_L7 28, b_power_L8 32, a_power_L7 12) | 5 nodes: **2.7 h**, ≤ 779 core-h | about 25.8 h, ≤ 12,273 core-h |
| stress | 25.8 h | 21.7-23.0 h; 993 indices; 11,511 core-h | 136 indices, 1,458 core-h | 8 nodes: 4.1 h, ≤ 1,558 core-h | about 27.1 h, ≤ 13,069 core-h |

- **Two submit rounds.** Round 1 does 86-94% of the work. Its workers end on their own 0.7-2.3 h before the 24-h limit,
  when no full index fits the time left; the afterany merge then runs, finds the campaign incomplete and exits 65 in
  seconds (expected). Round 2 is `submit.sh --lanes N` for the remainder (section 6): 72-155 indices, 2.7-4.5 h on 5-8
  nodes. `prod_lanes.py remaining RUN` (uploaded to `<SCRATCH>/c8d2/work/prod-ba68f401e46e/`) prints the real
  remainder and the wall of `--lanes 1..8` from the checkpoint blocks; tested read-only on the fresh campaign (2.6 s).
- Round 2 can start earlier, as round-1 workers end (from about 21.7 h), within the cap: N ≤ 9 − live c8d2 jobs − 1.
- **Allocated core-hours** about 12,300-13,600 for the two rounds plus two merges, below the design's 14,465 (whose
  η_node 0.837 carries the pilot's 3-node tail). The queue waits, the probe and the round-2 turnaround add wall time.
- The schedule does not depend on the node order. A worker that starts late only shifts its own lanes.

**Admission (`scripts/admission_check.py` → `plan/admission_check.json`).** `slurm_submit.admission()` with the real
`Context` methods against a live `squeue -u <USER>` snapshot (`plan/squeue_snapshot_admission.txt`; nothing submitted).
`C8_SBATCH_ARGS="-p amdq --exclude=$X"` passes the allowlist.

| Scenario | Result |
|---|---|
| a. `C8_AMDQ_CAP=9`, nothing of this session live, `--lanes 8` | **admitted: k = 8 + 1 = 9, room 9** (the merge takes the workers' partition and exclusions) |
| b. the same, start-latency probe still live | refused (65), "Largest admissible N for lanes N: 7"; nothing submitted |
| c. no window (env.sh's default cap 4) | refused (65), largest N 3 |
| d. three C63d `c8d3-` jobs live on amdq | admitted (another session's jobs are not counted) |
| e. round 2 after round 1 ended, `--lanes 2` | admitted, k 3 |
| f. round 2 with two round-1 workers live and the round-1 merge pending, `--lanes 6` / `--lanes 5` | refused (room 6, largest N 5) / admitted, k 6 |

`C8_AMDQ_CAP=9` survives the sourcing of `env.sh` (checked on the login node: "cap after sourcing: 9").

## 5. Seeds

- `6274393056071737300` is in symmetry's log (120 seeds, sha256 `7660055d…`; copy `seeds/production_symmetry.json`).
- The mirror `designs/forbidden_seeds.json` was merged from it with `tools/seeds.py merge` (119 → 120, the same set; a
  second merge adds nothing; `seeds/sha256.txt`, mirror `28a83219…`).
- Expanse's log does not hold it yet: appended to `../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt`. No Expanse session
  was opened (site rule).

## 6. The submit sequence (for the host)

`submit_sequence.sh`, block by block, on the symmetry login node, after C63d agrees and the window's DECISIONS line is
written. Its environment block was run read-only on the login node (commit ba68f40; `a46f3060…` and `be215e0e…`;
`LD_LIBRARY_PATH=/cm/local/apps/boost/1.77.0//lib64`; no loader override; modules boost/1.77.0 and python/3.11; the venv
python). In short:

```bash
source ~/c8d2/env.sh
export C8_ENV_SETUP=$HOME/c8d2/env.sh
export C8_PACKAGE=<SCRATCH>/c8d2/pkg/ba68f401e46e
export C8_RUN=<SCRATCH>/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e
X=<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,cn112
# checks: commit, sha256 of the executable and manifest, LD_LIBRARY_PATH, no LD_PRELOAD/LD_AUDIT/LD_DYNAMIC_WEAK/GLIBC_TUNABLES, module list
# survey: sinfo -p amdq; squeue -u $USER (no live c8d2- AMD job); C63d's c8d3- jobs within their share
sbatch -p amdq --exclude=$X -N 1 --ntasks=1 --cpus-per-task=64 --exclusive --mem=245G -t 00:05:00 \
  -J c8d2-prod-probe -o <SCRATCH>/c8d2/logs/%x_%j.out --wrap 'hostname; date'
# wait until it ended; sacct -j P -X -o JobID,Submit,Start,End,State,NodeList (record the queue wait)
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast      # 1129 incomplete, no WARNING, exit 1
C8_AMDQ_CAP=9 C8_SBATCH_ARGS="-p amdq --exclude=$X" C8_LANE_MEM=245G C8_LANE_TIME=24:00:00 C8_MERGE_TIME=02:00:00 \
  $C8_PACKAGE/slurm/submit.sh --lanes 8
```

Logs: workers `$C8_RUN/slurm_logs/lane-<jobid>.log`, merge `$C8_RUN/slurm_logs/merge-<jobid>.log`, per-index attempts
`$C8_RUN/lanes/logs/`. The expected output, monitoring, the round-2 resubmission after the 24-h limit (confirm every
round-1 job terminal with `sacct`; `prod_lanes.py remaining`; `submit.sh --lanes N` with the same settings) and the
final status, verify, accounting, combine (K = 1: `C8_final.json`) and heavy-tail report commands are in
`submit_sequence.sh`. At 2.5e-4 every free L8 graph gets at least 32,768 points per replicate, so
`design.py report --pilot $C8_RUN` confirms or clears the pilot's free-L8 heavy-tail screen (`../pilot/analysis/README.md`).

## Jobs

`sacct -X --duplicates` in `sacct.txt` (EDT). Core-hours = ElapsedRaw × physical cores (64 on an AMD node; sharedq's Intel
node AllocCPUS / 2). Logs `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`); evidence on BeeGFS
`<SCRATCH>/c8d2/evidence/ba68f401e46e/{prbuild.570719.0,prsurvey,prplan.570722.0}/` (copied here). The job
scripts were uploaded read-only to `<SCRATCH>/c8d2/work/prod-ba68f401e46e/` (sha256 of both copies in
`admission/submitted.txt`).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570719 `c8d2-prbuild` | profile build and checks (`scripts/prbuild.slurm`) | amddebugq <NODE> | COMPLETED 0:0 | 0:20 | 0.36 |
| 570722 `c8d2-plan-prod` | the production plan (`scripts/prplan.slurm` → `slurm/plan.sh`, role plan) | sharedq <NODE> | COMPLETED 0:0 | 9:21 | 0.62 |
| 570723-570734 `c8d2-prsv-<node>` | runtime-fingerprint survey, 12 nodes (`scripts/prsurvey.slurm`) | amddebugq <NODE>, 094, 098-104, 108-110 | COMPLETED 0:0 (12) | 0:00-0:01 each | 0.02 |
| **total** | 14 records | | | | **1.00** |

Budget: 1.00 of this task's 20 core-hours.

## Files

- `scripts/`: `pr.sh` (upload and the H7-checked submit), `prbuild.slurm`, `prsurvey.slurm`, `prsurvey_batch.sh`,
  `prsurvey_compare.py`, `prplan.slurm`, `prod_lanes.py` (estimate, schedule, remaining work), `admission_check.py`.
- `prbuild.570719.0/` (`identity.json`, build record, describe, ldd, make log, bin hashes, `tree_listings.sha256.txt`).
- `survey/`: one record per node, `survey.json`, the node states.
- `plan/prplan.570722.0/`: `manifest.json` (the plan copy), `plan_checks.json`, the plan's stdout/stderr and
  `/usr/bin/time`, `status_before_submit.txt`, `submissions.jsonl`, the seed log after; `plan/prod_lanes.json`,
  `plan/admission_check.json` and its squeue snapshot.
- `setup/seed_precheck.txt`, `seeds/`, `admission/`, `logs/`, `sacct.txt`, `submit_sequence.sh`.
