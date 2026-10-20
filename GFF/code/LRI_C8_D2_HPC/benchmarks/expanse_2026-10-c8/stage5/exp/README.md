# Stage 5 on Expanse: J-EXP-1..4, the zen2 GMP_PREFIX gates, J-SWEEP-2E and J-PIL-1E (2026-10-05)

Site deviation U1: Expanse is the overflow site; symmetry, the plan's site, runs the rest of Stage 5. Account <ACCOUNT>,
no other site used apart from read access to symmetry's seed log and one append to it (below). Every job ran the exact
default path (D1): no `NUMERICS`, no `--rates`; `GMP_PREFIX` only in the zen2 job, whose purpose it is.
`scripts/s5e_summary.py` recomputes every verdict and number below from the records here into `s5e_summary.json`.

**Commit and export.** 07ff5c1 is 5d7586e plus this folder's job scripts (no change under `src/`, `tools/`, `tests/`,
`Makefile`, `slurm/`, `gen/`, `inputs/`, `vendor/`). `$C8_DATA/pkg/07ff5c1975e5` is its `git archive`, checked file by
file (`../../setup/export_check_07ff5c1975e5.json`, 7,195 files equal). J-EXP-1 re-hashed the L8 packs of
`pkg/7aac898add43` against this export's `inputs/manifest.json` (free `e5dd7271…`, power `3d77d0c4…`, equal) and
hard-linked them. Scripts written after the export (`s5e_exp1b.slurm`, `s5e_nfdebug.slurm`, `s5e_exp1c.slurm`, the
`C8_SWEEP_RUN` variant of `s5e_sweep2.slurm`) ran as uploaded copies; their sha256 are in `admission/submitted.txt`.

**Admission.** Before every sbatch: a fresh `squeue -A <ACCOUNT>` and H7E-R (`admission/h7e_r_admission.jsonl`, the
snapshots beside it). J-EXP-2..4 went through `slurm/submit.sh`, whose own H7E-R admission counts every new job, merges
included, under the site lock; its output (snapshot numbers, decision, job ids) is in `admission/exp{2,3,4}_submit_*.txt`.
At most 4 nodes (compute + debug) and 3 shared jobs of this agent were live at a time. No job is live.

## Jobs

| Job | Where | Wall | Result |
|---|---|---:|---|
| 54676864 `c8d2-s5e-exp1` (J-EXP-1) | debug, exclusive, <NODE> | 6:09 | Build PASS: `make && make gmp`, `make c7ref`, `make inspect` in 33 s; decimal `99a51c1d…`, gmp `1d2a2181…`, inspect `63c194fd…`, c7ref `4537dcfd…`/`6c829386…` (the final default build); `BOOST_LIB_VERSION 1_77` in every build record. `make test` FAILED: `validate.py` passed, then `unit_orchestration.py` failed in its group `lanes` and make stopped |
| 54676866–68 | — | — | zen2, sweep and prep jobs submitted afterok on J-EXP-1; cancelled while pending (DependencyNeverSatisfied), no allocation; resubmitted without the dependency (the build had passed) |
| 54676898 `c8d2-s5e-exp1b` (J-EXP-1 follow-up) | debug, exclusive, <NODE> | 17:17 | Every command of `make test` (from `make -n test`, word for word), each to the end: 14 of 16 exit 0; `unit_orchestration.py` 1 (group `lanes` only) and `test_numerics_flags.py` 1 (group `f2_profile` only). The `lanes` group alone: refused on the whole 128-core affinity set, passes under `taskset -c 0-15` |
| 54676921 `c8d2-s5e-nfdebug` | shared 16 | 0:16 | Diagnosis of `f2_profile`: its `dse` run passes `C8_FAKE_PROFILE_DELTA=repr(delta)` with a NumPy float64; NumPy 2.3.5 (Expanse venv) prints `np.float64(0.0269…)`, which the fake profile cannot parse, so no record is written. The Mac (NumPy 1.23.5) prints the bare number, which is why the Mac suite passes |
| 54676926 `c8d2-s5e-exp1c` | shared 16 | 0:52 | The one-line fix `repr(delta)` → `repr(float(delta))`, applied in a node-local COPY only: `test_numerics_flags.py` 8/8 pass on Expanse |
| 54676897 `c8d2-s5e-prep` | shared 16 | 5:38 | The test campaigns t2, t3, t4 planned inside the job (ledger role plan, seeds added to the Expanse log); t2's 22 lightest indices run here |
| 54676902 (array, 2 elements) + 54676904 (merge) (J-EXP-2) | shared: 32 CPUs, 62G each; merge 24 CPUs, 64G | 0:16, 0:19; 0:13 | `slurm/submit.sh` in array mode on t2 (`--threads 32`): the 2 incomplete indices (5 `a_free_L8`, 11 `a_power_L8`) as one 2-element array, then the afterok merge with assembly. `status` exit 0, `C8_test_result.json` `test_partial`, `verify_result.py` verified |
| 54676924 (lane) + 54676925 (merge) (J-EXP-3) | debug: worker exclusive <NODE>, `C8_LANES=numa` = 8 × 16; merge 24 CPUs | 4:11; 0:10 | `submit.sh --lanes 1` on t3 (33 indices, all claimed and run, 0 failed); merge and assembly on debug; `status` exit 0; verified |
| 54676911 (lane) + 54676912 (merge) (J-EXP-4, mandatory) | compute: worker exclusive <NODE>, default 16 × 8; merge on a compute node | 4:14; 0:15 | `submit.sh --lanes 1` on t4 under the slot rule: k = 2, admission snapshot "c8d2 compute nodes: new 2, room 2" (2 nodes of this agent live), admitted; started 24 s after submission; `status` exit 0; verified |
| 54676895 `c8d2-s5e-zen2` | compute, exclusive, <NODE> | 9:20 | The GMP_PREFIX gates, all PASS (below) |
| 54676896 `c8d2-s5e-sweep2` (J-SWEEP-2E, first run) | compute, exclusive, <NODE> | 5:07 | Complete (48,346 keys), but the node runs L7/L8 work 14% slow (below); kept as evidence only |
| 54676908 `c8d2-s5e-sweep2` (J-SWEEP-2E) | compute, exclusive, `--exclude=<NODE>`, <NODE> | 4:54 | **The Expanse cost model** `cost_models/gmp_expanse_amd_c8.json` (`0e1ccfc9…`), every key |
| 54676927 `c8d2-s5e-pilotplan` (J-PIL-1E) | shared 8, 15G | 1:27 | The Expanse pilot planned (`slurm/plan.sh`), nothing submitted (below) |

Logs: `logs/` (job logs) and `s5ecampaigns/<t>/slurm_logs/` (the array, lane and merge logs). On Expanse:
`$C8_DATA/logs/%x_%j.out`, evidence `$C8_DATA/evidence/07ff5c1975e5/<run>/`, campaigns `$C8_DATA/s5e-07ff5c1975e5/t{2,3,4}`,
`$C8_DATA/sweep2e-07ff5c1975e5{,-r2}`, `$C8_DATA/pilot1e-20261005-07ff5c1975e5`.

## J-EXP-1..4 (A-EXP-3)

- **Allocation active** (`admission/expanse_client_before_exp4_*.txt`: 22,080,000 SU, 50,752 spent, until
  2027-09-30), so A-EXP-3 applies.
- **J-EXP-1, the build: PASS. `make test`: FAIL in two test groups, both test-harness portability defects of the
  test code, neither touching a tool, a worker or a result.**
  1. `tests/unit_orchestration.py`, group `lanes` (`test_lanes`): its lane worker runs with `C8_LANES=2` on the
     whole affinity set of the job. On a 128-core node that gives two lanes of 64 cores, more than the test plan's
     `checkpoint_tasks=8`, and `lanes.py` refuses (64), as designed. The earlier Expanse J-VAL-1 runs used 16-CPU
     shared jobs (two lanes of 8), so this is the first `make test` on a whole node. symmetry's J-VAL-1 on a 64-core
     amdq node shows the same failure. With a 16-CPU affinity the group passes (54676898). Proposed fix: pin the
     group to at most 16 CPUs (`os.sched_setaffinity` at the start of `test_lanes`, restored at its end; the children
     inherit it).
  2. `tests/test_numerics_flags.py`, group `f2_profile`: `repr(delta)` of a NumPy float64 is `np.float64(…)` under
     NumPy ≥ 2. Fix: `repr(float(delta))` (line 287), checked on Expanse in a copy (54676926: 8/8).
  Every other command of `make test` passes on the debug node (54676898: `validate.py` (the replay subset, refusals,
  invariance, inspector, class B), the other 47 groups of `unit_orchestration.py`, `test_pipeline.py`, `ast_scan.py`,
  `gen/test_regress.py`, `merge_scale.py`, `check_vendored.py`, `vendored_isolated.py --in-place`,
  `test_delivery_verifier.py`, `check_inputs.py`, `test_profiling.py`, `test_gmp_prefix.py`, `test_dd_profile.py`,
  `workflow.py`, `staging.py`), and 7 of the 8 groups of `test_numerics_flags.py`. The fixes are not applied here:
  they change `tests/` of the final commit, which the host decides (both sites' J-VAL-1 are affected).
- **J-EXP-2: PASS.** A plan always has the 24 groups, so a literal 2-element array needs 22 indices complete first:
  the prep job ran them, and plain `slurm/submit.sh` (array mode, `C8_SBATCH_ARGS="-A <ACCOUNT> -p shared --mem=62G"`)
  then submitted exactly the 2 incomplete indices as one array, CPUs per element = the plan's `--threads 32`, and a
  `shared` merge (afterok) that also assembled. t2's ledger therefore lists the prep job (role plan, with a note), so
  its accounting η (2.10) is not a lane efficiency.
- **J-EXP-3: PASS.** Debug lane worker with `C8_SBATCH_ARGS="-A <ACCOUNT> -p debug" C8_LANE_MEM=240G
  C8_LANE_TIME=00:25:00 C8_LANES=numa` (and `C8_MERGE_TIME=00:30:00`: the debug partition's limit is 30 min, and the
  merge takes the worker's partition). 8 lanes of 16 cores; t3 (1,024 stratified graphs per group, 2 × 4,096 points,
  33 indices, about 9.7 core-hours at Stage-3 costs) completed in 4:11; merge and assembly 10 s. η_node 0.83.
- **J-EXP-4: PASS (mandatory).** `C8_SBATCH_ARGS="-A <ACCOUNT> -p compute" C8_LANE_MEM=240G C8_LANE_TIME=00:30:00
  submit.sh --lanes 1`: one worker and its merge (k = 2), admitted under the slot rule with the site lock; the log
  holds the snapshot numbers and the decision (`admission/exp4_submit_*.txt`). Expanse's bank_limit plugin accepted
  the lane worker (`--exclusive --nodes=1 --ntasks=1 --mem=240G`). 16 lanes of 8 cores; t4 (the same sample as t3,
  `--threads 8`) completed in 4:14; η_node 0.80.
- Every test campaign: all checkpoint blocks committed, 24 `merged.json`, `C8_test_result.json` labelled as an
  INCOMPLETE workflow test with values only under `test_partial`, `verify_result.py` verified
  (`s5ecampaigns/<t>/`).

## GMP_PREFIX=zen2 on Expanse: the owed gates (job 54676895), all PASS

- **Build.** A node-local copy of the export built with `GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-zen2` (libgmp `4267ffeb…`):
  `bin/c8d2_gmp` `aa84cd45…` (the Stage-4b zen2 worker byte for byte), loads the prefix's libgmp (DT_RPATH; `ldd.txt`),
  build record `GMP_PREFIX` set, `development: false`, no parameter override; decimal is the default `99a51c1d…`; c7ref
  as Stage 3 (Spack GMP).
- **J-VAL-2 in full** (`make test-full GMP_PREFIX=…`): `validate.py --full` passed. G-C7 exact against `make c7ref` in
  all 39,048 rows per backend (22,212 with mp > 0), G-REF exact in 7,548 rows (gmp: 4,121 with mp > 0, exact where
  1e-30 is allowed), G-JET exact; chunks and layouts; class B; the diagnostic builds (against the same prefix). Point
  checks L3–L8: 2.1e-353 (gmp350), 1.8e-302 (decimal300). `workflow.py`, `staging.py` passed.
- **G-BK8 (A-RPL-4):** decimal against the zen2 worker, L7 and L8, 400 kernels per sector: identical counters, every
  row exact (3,200 rows, 2,779 with mp > 0).
- **Forced tiers (A-RPL-5):** passed, no doubling; free 29,284 points accepted in binary128 and 3,541 MP, power 50,625
  and 12,568; gates a–c.
- **Against the default build.** Every record above (validate_full, point_checks, workflow, staging, bk8, forced_tiers)
  equals G4b's record of the default build (`../../stage4b/final/`) once the run-specific fields are removed
  (`summarize_final.py`'s rules; only the inspector's random `mkdtemp` names differ). On the L8 sweep sample (1,600
  free + 400 power kernels × 2 × 512 points; `validate.py --l8self <default bin>`), every scientific field of the zen2
  worker equals the default worker's.
- **Verdict: `GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-zen2` is cleared for production on Expanse** (that prefix and library;
  opt-in, off by default; its use stays the user's choice). symmetry has no gated `GMP_PREFIX` build.

## J-SWEEP-2E and A-PERF-5

- **The sweep** (`s5e_sweep2.slurm`): `slurm/sweep.sh` on the final binary, all 24,173 graphs, both campaigns,
  2 × 512 points, planned with J-SWEEP-1's measured cost model and `--shards 16` (324 indices; the sweep is about
  7 core-hours at Stage-3 costs, so the default 1.5-h sizing would leave one index per group and the node idle),
  `--forbid-seeds-from $C8_SEEDS`, `--threads 8` (16 × 8 NUMA-pinned slots), merge, cost model, calibration rows (to
  a copy). Registered in its ledger (role sweep); `tools/accounting.py` complete: 10.45 core-hours allocated, 5.41 busy
  (the plan, the merge and the cost model run inside the job).
- **Node check.** The first run landed on <NODE>, the node that ran the exact binary 14% slow in the Stage-4c mp256
  gate. Its per-point costs are ×1.143 the rerun's overall: ×1.146 / ×1.152 on free L8 / L7, ×1.136 / ×1.121 on power
  L8 / L7, but ×0.97–1.01 at L3–L6 (no tier work). The rerun on <NODE> (`--exclude=<NODE>`, fresh seed) is the
  Expanse cost model. **Pilot and production jobs should pass `--exclude=<NODE>`.**
- **A-PERF-5 (default path), per (sector, L):** the final binary's per-point kernel seconds against the Stage-3
  baseline's (J-SWEEP-1 54641706, <NODE>, 8 × 16), summed over every graph of the stratum (equal points per graph):

  | Sector | L3 | L4 | L5 | L6 | L7 | L8 | all L |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | free | ×1.022 | ×1.011 | ×0.994 | ×1.013 | ×1.413 | ×1.444 | ×1.443 |
  | power | ×1.017 | ×1.012 | ×1.386 | ×1.195 | ×1.283 | ×1.261 | ×1.262 |
  | both | ×1.021 | ×1.011 | ×1.185 | ×1.126 | ×1.371 | ×1.390 | **×1.390** |

  - Per campaign at L7 / L8: a free ×1.392 / ×1.410, b free ×1.440 / ×1.485, a power ×1.253 / ×1.235, b power
    ×1.322 / ×1.294.
  - These are kernel seconds of the tasks (load and start-up excluded), so R5a's gain, which is load time, is not in
    them; R3a is (binary128 add/sub/mul). Stage 4b's ×1.646 on the L8 sample counted lane-thread seconds with
    loading. L3–L4 have almost no promoted points, so ×1.0 is expected; their tasks last microseconds.
  - Different nodes, lane shapes (8 × 16 against 16 × 8) and seeds: the factors carry a percent or two of that.
  - The L=2 graph is not a campaign stratum (its value is analytic; the L=2 control is separate), so A-PERF-5 has no
    L2 row.

## J-PIL-1E: the Expanse pilot, planned (A-PIL-1 on Expanse; nothing submitted)

- **Plan job** 54676927 (`slurm/plan.sh`, shared, `-c 8 --mem=15G -t 01:00:00 --no-requeue`; ledger role plan):
  `production.py plan $C8_DATA/pilot1e-20261005-07ff5c1975e5 --pilot --points 4096 --replicates 8 --threads 8
  --checkpoint-tasks 256 --index-hours 1.5 --backend gmp --cost-model <J-SWEEP-2E 54676908, 0e1ccfc9…>
  --forbid-seeds-from $C8_DATA/forbidden_seeds.json --forbid-seeds-from <symmetry's log, read-only copy be46236d…>
  --seed 4531889874192435105`.
- **Seed.** Fresh (`secrets.randbits(63)`), checked against both logs before use and again just before the plan
  (`admission/seed_checks_before_use.txt`), then added to the Expanse log (`tools/seeds.py add RUN`), to symmetry's
  log (`tools/seeds.py add --seed … --label <the Expanse campaign path>`, the one append on symmetry;
  `admission/symmetry_seed_append_*.txt`) and to the mirror.
- **Printed estimate** (`s5epilot.54676927.0/plan_stdout.json`): 36 indices, 386,768 tasks, 1,533 checkpoint blocks,
  **170.3 core-hours** (Expanse cost model, kernel seconds; the plan's central projection was about 220), largest
  index wall 5,329 s (1.48 h at 8 threads and the assumed 0.9), 1,865 projected files, one merge pass per group,
  **projected merge 34 s** (suggested merge time 01:00:00), manifest `ad94b94a…`. Below 300 core-hours, so the
  runbook's `--replicates 6` fallback does not apply.
- **Lanes and SU** (`s5e_summary.py`, the plan's indices heaviest first on 16 lanes of 8 cores per node): the 16 L8
  indices (1.24–1.48 h each) fill one node's 16 lanes exactly, and the 20 L3–L7 indices follow on the lanes that
  free first.

  | Nodes (lanes) | Wall | Node-hours | SU (128 per node-hour) | Lane occupancy |
  |---:|---:|---:|---:|---:|
  | **1 (16 × 8)** | **1.56 h** | 1.56 | **199** | 0.95 |
  | 2 (32) | 1.48 h | 2.96 | 379 | 0.50 |
  | 4 (64) | 1.48 h | 5.92 | 758 | 0.25 |

  One node is the choice: more nodes cannot shorten the 1.48-h indices. With the merge (one compute node for a few
  minutes) **about 205 SU**. A shorter wall needs a re-plan with a smaller `--index-hours`.
- **Submit line** (Expanse login node; after the Stage-6 Codex inspection, H11; first the agreed 5-minute 1-node
  start-latency probe):

  ```bash
  source ~/c8d2/env_expanse.sh
  export C8_ENV_SETUP=$HOME/c8d2/env_expanse.sh C8_SITE=expanse C8_PACKAGE=$C8_DATA/pkg/07ff5c1975e5 \
         C8_RUN=$C8_DATA/pilot1e-20261005-07ff5c1975e5
  # H11 probe: sbatch -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:05:00 \
  #   -J c8d2-pilot-probe -o $C8_DATA/logs/%x_%j.out --wrap 'hostname; date'
  C8_SBATCH_ARGS="-A <ACCOUNT> -p compute --exclude=<NODE>" C8_LANE_MEM=240G C8_LANE_TIME=04:00:00 \
  C8_MERGE_TIME=01:00:00 C8_EXP_RUNNING=16 C8_EXP_SUBMITTED=40 \
  C8_ADMISSION_REF="<the H11 window line in LRI_C8_shared/inventory/DECISIONS.md: pilot session 16 running / 40 submitted, the other 6 / 14; account <= 32 running>" \
    $C8_PACKAGE/slurm/submit.sh --lanes 1
  python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN
  ```

  - k = 2 (the worker and its merge), inside the window's 16 running / 40 submitted; `C8_EXP_ACCOUNT_RUNNING` (32),
    `C8_EXP_SHARED` (32) and `C8_EXP_NODES` (4) keep their H7E-R values.
  - `C8_LANE_TIME=04:00:00`: a lane claims an index only if est × f / (8 × 0.9) × 1.5 + 300 s fits the time left, so
    the 1.48-h indices need 2.3 h at claim time; 4 h also covers a slow node.
  - The campaign pins the tools and the executable of 07ff5c1. If Stage 6 changes the code, `submit.sh` refuses (64):
    re-export the approved commit and re-plan with the same arguments and a fresh seed (this one is registered).

## Seeds (the two-log rule)

New seeds, each checked against both logs before use (`admission/seed_checks_before_use.txt`) and now in the Expanse
log, symmetry's log and the mirror `designs/forbidden_seeds.json`:

| Seed | Campaign (the source string in every log) |
|---|---|
| 604064406400592787 | `$C8_DATA/s5e-07ff5c1975e5/t2` (J-EXP-2) |
| 2953464248843618050 | `$C8_DATA/s5e-07ff5c1975e5/t3` (J-EXP-3) |
| 8549950029915422195 | `$C8_DATA/s5e-07ff5c1975e5/t4` (J-EXP-4) |
| 1414971400204191440 | `$C8_DATA/sweep2e-07ff5c1975e5` (J-SWEEP-2E on <NODE>) |
| 5426680251980128385 | `$C8_DATA/sweep2e-07ff5c1975e5-r2` (J-SWEEP-2E) |
| 4531889874192435105 | `$C8_DATA/pilot1e-20261005-07ff5c1975e5` (J-PIL-1E) |

symmetry's own seed sync had already copied the first five into its log ("present"); the pilot seed is the one append
made from here. `seeds/` holds both logs as read at the end (Expanse 64 entries, `3dc0a259…`; symmetry 68,
`c5bca13c…`); the mirror is their union (68 seeds). Four symmetry-side seeds are not yet in the Expanse log: the
symmetry agent's sync adds them.

## Allocation and files

- **SU: 112.3** (`sacct.txt`; compute and debug 128 per node-hour, shared the billed CPUs): J-EXP-1 13.12, its
  follow-up 36.87, diagnostics 0.30; prep 1.50; J-EXP-2 0.43; J-EXP-3 9.01; J-EXP-4 9.56; zen2 gates 19.91; J-SWEEP-2E
  10.92 (<NODE>) + 10.45; pilot plan 0.19. The cancelled 54676866–68 never started.
- **Lustre.** The user's count went from 1,524,790 to 1,531,024 (C63d included). This agent's new entries: the export
  7,844 (kept: the pilot campaign uses it), the two sweep campaigns 1,562 each, the test campaigns 1,255, the pilot
  campaign 161, evidence 198, uploaded scripts 6, 9 logs; about 12,600 in all.
