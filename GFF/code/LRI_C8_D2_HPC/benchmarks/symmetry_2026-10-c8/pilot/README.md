# C8(2) L8 pilot on symmetry: preparation (2026-10-06), NOT submitted

**Since then the pilot ran** (lane workers 570638-570640, merge 570641; C8 = 45,620 ± 214, `verify_result` clean), and
it was analysed and frozen into eight candidate bundles: `analysis/README.md` (the production cost table, accounting,
diagnostics). This README records the preparation as it was.

This folder prepares the A-PIL-2 pilot (J-PIL-1, `docs/HPC.md`, "Pilot runbook") from the final package head **ba68f40**
(Stage 6 closed without a further Codex round by the user's decision of 2026-10-06, `LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md`).
The user approved running the pilot on symmetry on the EXACT default path: no `--numerics`, no `--rates`, no `GMP_PREFIX`.
Here the export was made and built, the AMD nodes were surveyed, and the campaign was planned in a plan job. **No lane
worker, merge or start-latency probe of the pilot was submitted, and the H11 window was not opened.** The host submits
after C63d agrees (sequence below).

Site rules: symmetry only. Expanse, personal desktops were not touched. amdq/amddebugq always ran with
`--exclude=cn112`. No longq. sharedq ran with `--no-requeue`. Every job had `--mem`, `--time` and a `c8d2-` name.
H7: at most 4 live `c8d2-` AMD-pool jobs (the peak was 4, during the survey batches;
`admission/h7_admission.jsonl`). C63d had no live `c8d3-*` job at any snapshot. The other <USER> job
(`sri_eng_c8BC_chk4001`, 570610 on <NODE>) was neither counted nor touched.

## 1. Export, packs, build (A-RPL-8)

- **Export `<SCRATCH>/c8d2/pkg/ba68f401e46e`** = `git archive ba68f401e46e4071ca5593ae40ec92a1755dcc98`.
  10,385 files are equal to the archive in content and mode (`setup/export_check_ba68f401e46e.json`, listing sha256
  `5e10097f…`). The driver is `scripts/pp.sh export`. The job scripts of this folder postdate the commit, so they were
  uploaded read-only to `<SCRATCH>/c8d2/work/pilot-ba68f401e46e/` (both sha256 in `admission/submitted.txt`).
- **L8 packs.** `pkg/7a8aad783c31/inputs/packs/{free,power}_L8.pack` were re-hashed against the export's
  `inputs/manifest.json` (`3813f24a…`): free `e5dd7271…` (6,093,071,533 B) and power `3d77d0c4…` (1,402,876,509 B), both
  equal. They were then hard-linked into the export (`ppbuild.570620.0/l8_packs.json`).
- **Build, job 570620** (amddebugq <NODE>, EPYC 7532, 0:29). It ran `make -j48 all gmp inspect && make c7ref` with
  Ubuntu GCC 11.4.0, Boost 1.77 and system GMP 6.2.1 (`scripts/ppbuild.slurm`). `make inputs` (`prepare_inputs.py`)
  verified every pack, the L8 packs included.

  | Executable | sha256 | Equal to fix round 4's 570582 |
  |---|---|---|
  | `bin/c8d2_decimal` | `a18ce425fbb81a0182e15f675a984c36ef9505ce8d90ffb2629590f08112f2bc` | yes |
  | `bin/c8d2_gmp` | `7741f733fb888fd40f4bce733e41c44c76a73640d350a725ffa85be928c5ef41` | yes |
  | `bin/c8d2_inspect` | `3836197913ea7d2a90dac9b70c0b57d7637c86bb922a35b367c265c0d1cf335a` | yes |
  | `bin/ref/c7d2_decimal` | `e696d7f30cf2374e6b7051b659af334c0b2c9b385edaed2b0b55d36923124df5` | yes (the plan's symmetry hash) |
  | `bin/ref/c7d2_gmp` | `7e3c8c922bbbc70f0a15752ca23147acc360305ff4a947004484cce3024fe8c3` | yes (the plan's symmetry hash) |

  Every build record shows: `macro_overrides []`, no parameter override, `development false`, required flags,
  `NUMERICS exact`, Boost `1_77` (the inspect record too), `executable_sha256` equal to the file, and `build_directory`
  equal to the export (W3). `--describe` gives numerics exact and diagnostic false. **A-RPL-8 PASS.**
- **570620 ended FAILED (exit 3) because of a defect in its own script, not in the package.** Its last check searched
  `bin/c8d2_inspect.build.txt` for `BOOST_LIB_VERSION: 1_77`, but make writes the macro with its quotes
  (`BOOST_LIB_VERSION: "1_77"`). Every other check had passed. `scripts/ppbuild_recheck.py` repeated all the checks on
  the job's own evidence, with the inspect line parsed and the five executables hashed again in place, on the login
  node. Nothing was rebuilt. Result `ok: true` (`ppbuild.570620.0/identity_recheck.json`).

## 2. Runtime-fingerprint survey of the amdq nodes

`scripts/ppsurvey.slurm` ran one job per node: amddebugq, `--exclude=cn112 --nodelist=<node>`, `--exclusive`,
`--mem=4G`, `-t 00:05:00`, at most 4 live at a time (`scripts/ppsurvey_batch.sh`). Each job sources
`~/c8d2/env.sh`, as the lane worker does. It then computes the package's own runtime identity through the export's
tools, exactly as a claim does before any pin:
- `stage_runtime`'s job-private copy of `bin/c8d2_gmp` in a `c8d2_runtime_*` directory under `$TMPDIR`;
- `common.fingerprint(copy, counter, cpu)`, then `runtime_identity` / `runtime_identity_key`, the key that
  `runtime_identity.json` pins (X8);
- `fingerprint_problems` (Y6, Z6) and `loader_overrides` (W7).

It also records lscpu, numactl, the raw `ldd`, `/etc/ld.so.preload` and the key computed on the export path. One JSON
per node is in `survey/`, and the comparison is in `survey/survey.json` (`scripts/ppsurvey_compare.py`). Node states at
the survey are in `survey/amdq_nodes_at_survey.txt`.

**Result: all 14 reachable amdq nodes have the same runtime identity, key
`04f1e51dfc2e89b039f567261a341d5723806390bdd1a222245ac5c2584c360b`. No node differs.** On every surveyed node:
- the fingerprint is complete: `ldd` answered, with no unexplained line and no `fingerprint_problems`;
- there is no loader override, no `/etc/ld.so.preload`, and `preload_order` and `loader_env` are empty;
- the vendor is AuthenticAMD;
- the CPU has 64 cores in 8 NUMA nodes of 8;
- glibc is 2.35;
- `LD_LIBRARY_PATH` is `/cm/local/apps/boost/1.77.0//lib64` (from env.sh), and every library resolves under
  `/lib/x86_64-linux-gnu`.

The identity's libgmp is `4dc20a90…`, the gates' libgmp. The key on the export path equals the key on the staged copy.

| Node | Survey job | CPU | Runtime identity | Same as the majority |
|---|---|---|---|---|
| <NODE>, <NODE>, <NODE> | 570621, 570622, 570623 | EPYC 7532 (Zen 2) | `04f1e51dfc2e…` | yes |
| <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE> | 570624-570634 | EPYC 7543 (Zen 3) | `04f1e51dfc2e…` | yes |
| <NODE>, <NODE>, <NODE>, <NODE>, <NODE>, <NODE> | none | | **unsurveyed**: allocated to other users' 24-h jobs with 19-22 h left (<NODE>: <USER>'s own `sri_eng` job) | |
| <NODE>, <NODE> | none | 7532 / 7543 | **unsurveyed** (allocated, 19.5 h left); earlier records with the same key: <NODE> in 570416 (`../s6fix2/s2prec.570416.0/y6_y7.json`) and <NODE> as the first claim of `sweepdd-997639178c1f` (570538) | (yes, earlier) |
| <NODE>, <NODE>, <NODE>, <NODE> | none | | **unsurveyed**: reservation `shotinli_118` until 2026-11-01 | |
| <NODE>, <NODE> | none | | **unsurveyed**: `down*` (Not responding) | |
| cn112 | none | | excluded by rule | |

**`--exclude` for the pilot.** Required minimum, from the identities: `cn112` (no surveyed node differs). Recommended,
and used below: also every unsurveyed node. The first claim pins the identity of whatever node it lands on, so an
unsurveyed node that differed could pin a foreign identity, and then every surveyed node would refuse with exit 64.
None of the unsurveyed nodes can start a job in the next 19 h anyway, so excluding them costs nothing:

```
X_ID=<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,cn112
```

A further option, a judgement for the host: add the three Zen 2 nodes, `X_7543=$X_ID,<NODE>,<NODE>,<NODE>`. This keeps
the pilot on the 11 surveyed EPYC 7543 nodes, the cost model's CPU. It is not needed for correctness: the identity is
the same, and Zen 2 and Zen 3 give bitwise-equal rows (F5). It has two benefits:
- the lane deadline uses class factor 1.0 instead of the unknown-class 1.5;
- every per-graph cost in `graph_costs.csv`, which the Neyman design uses as `c_g`, is measured on one CPU model.

If a node frees up before the submission, it can be surveyed with the same script
(`scripts/ppsurvey_batch.sh <node>`) before it is dropped from the list.

## 3. The pilot plan (job 570635)

- **Seed `3049594997687674958`**, fresh (`secrets.randbits(63)` on the Mac). Before the plan it was checked against the
  mirror `designs/forbidden_seeds.json` and against symmetry's live log with `tools/seeds.py check`, both with 118
  seeds and the same set (`setup/seed_precheck.txt`).
- **Plan job 570635** ran `slurm/plan.sh` on sharedq <NODE>, `-c 8 --mem=15G -t 01:00:00 --no-requeue`, in 0:52
  (`logs/c8d2-plan-pilot_570635.out`). The arguments are the runbook's, unchanged from J-PIL-1:

  ```
  production.py plan <SCRATCH>/c8-d2/pilot1-20261006-ba68f401e46e --pilot --points 4096 --replicates 8 \
    --threads 8 --checkpoint-tasks 256 --index-hours 1.5 --backend gmp \
    --cost-model <SCRATCH>/c8d2/pkg/ba68f401e46e/cost_models/gmp_symmetry_amd_c8.json \
    --forbid-seeds-from <SCRATCH>/c8-d2/forbidden_seeds.json --seed 3049594997687674958
  ```

  The plan registered its seed in symmetry's log itself before publishing (Z15; 119 entries). `plan.sh`'s add said
  "present", and the job is in the campaign ledger (`plan/submissions.jsonl`, role plan).
- **Campaign `<SCRATCH>/c8-d2/pilot1-20261006-ba68f401e46e`.** Manifest sha256 `828fb586…` (copy in
  `plan/manifest.json`). It is non-test, numerics exact, rates default, backend gmp, executable `c8d2_gmp` `7741f733…`,
  inputs manifest `3813f24a…`, and cost model `a1b6e5d2…` (J-SWEEP-2, numerics exact).
  - The cost model was measured on the Stage-5 build `2cc5e88e…`. Fix round 3 showed that Z4 leaves the exact worker's
    speed unchanged (+0.8%, `../s6fix3/README.md`), and `load_cost_model` binds numerics, backend and rates, not the
    executable.
  - `production.py status --fast` from the export: no WARNING about pinned tools, 39 incomplete indices, CPU vendor
    and runtime identity "not pinned yet", exit 1 (`plan/status_before_submit.txt`).

**Estimate** (the plan's own output and `plan/pilot_lanes.json`, from `scripts/pilot_lanes.py`). It is identical to
J-PIL-1's: same arguments, same cost model.

| Quantity | Value |
|---|---|
| Estimated work | **179.9 core-h** (L8 173.1 over 19 indices; L7 6.7 over 4 indices; L3-L6 0.14 over 16 indices) |
| Indices / tasks / checkpoints | **39** / 386,768 / 1,534; 1,875 projected files |
| Largest index | a_free_L8, 34,531 core-s: **4,796 s (1.33 h) on an 8-core lane** at 0.9 efficiency |
| Lane-deadline need of the largest index at claim time | 7,494 s (2.08 h) at class factor 1.0 (EPYC 7543); 11,091 s (3.08 h) at 1.5 (EPYC 7532, unknown class) |
| Lanes | 8 × 8 per amdq node (8 NUMA nodes of 8 cores, the default) |
| Peak memory per lane | largest `est_peak_bytes` 1.34 GiB against 245G/8 = 30.6 GiB per lane; the lane guard (8 × peak ≤ 0.85 × 245 GiB, 26.0 GiB per lane) holds with ×19.5 headroom |
| Merge | 1 pass per group, projected 34 s; the plan suggests `--time 01:00:00` |

| amdq nodes (8 × 8 lanes) | Wall (heaviest first) | Allocated core-h (wall × 64 × nodes) |
|---|---|---|
| 1 | 3.59 h | 230 |
| 2 | 2.26 h | 289 |
| **3** | **1.33 h** | **256** |
| **4** (the agreed `--lanes 4`) | **1.33 h** | **≤ 341**: about 256 when the 19 L8 indices fill three nodes, since a worker exits once its lanes find nothing left to claim |

The merge is extra: one whole amdq node, a projected 34 s of merging plus the assembly, so under about 2 core-h. So
is the probe, about 0.1 core-h. `--lanes 3` gives the same wall (k = 4).

## 4. The submit sequence (for the host; after C63d agrees and the window's DECISIONS line is written)

Run this on the symmetry login node in a fresh `ssh symmetry` shell, inside the agreed H11 symmetry window: this
session at most 5 live AMD-pool jobs, C63d at most 3 (DECISIONS 2026-10-05, "H11 pilot window on symmetry").

```bash
# --- environment (W17: the site environment first; nothing else loaded: the survey's library stack) ---
source ~/c8d2/env.sh
export C8_ENV_SETUP=$HOME/c8d2/env.sh
export C8_PACKAGE=<SCRATCH>/c8d2/pkg/ba68f401e46e
export C8_RUN=<SCRATCH>/c8-d2/pilot1-20261006-ba68f401e46e
X_ID=<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,cn112
X=$X_ID                       # or X=$X_ID,<NODE>,<NODE>,<NODE> (EPYC 7543 only; section 2)
: "${C8_SEEDS:?source the site environment}" "${C8_PACKAGE:?}" "${C8_RUN:?}"
cat $C8_PACKAGE.commit                                   # ba68f401e46e4071ca5593ae40ec92a1755dcc98
sha256sum $C8_PACKAGE/bin/c8d2_gmp $C8_RUN/manifest.json # 7741f733fb88... and 828fb5865e6d...
echo "$LD_LIBRARY_PATH"                                  # /cm/local/apps/boost/1.77.0//lib64
env | grep -E '^(LD_PRELOAD|LD_AUDIT|LD_DYNAMIC_WEAK|GLIBC_TUNABLES)=' || echo "no loader override"   # W7

# --- 0. survey: say start-now vs queue ---
sinfo -h -p amdq -o '%t %D'
sinfo -N -h -p amdq -o '%N %t' | sort | paste -sd' '
squeue -u $USER -h -r -o '%i|%T|%P|%q|%D|%u|%j'        # no live c8d2-* line (only other projects' jobs)
squeue -h -o '%i %u %j %T %P' | grep ' c8d3-'           # C63d: at most 3 live during the window

# --- 1. the 5-minute start-latency probe (an AMD-pool c8d2- job: counts against the cap while live) ---
sbatch -p amdq --exclude=$X -N 1 --ntasks=1 --cpus-per-task=64 --exclusive --mem=245G -t 00:05:00 \
  -J c8d2-pilot-probe -o <SCRATCH>/c8d2/logs/%x_%j.out --wrap 'hostname; date'
#   -> "Submitted batch job P"; WAIT until it has ended, then record the queue wait (Start - Submit) for this README:
sacct -j P -X -o JobID,Submit,Start,End,State,NodeList  # COMPLETED; log <SCRATCH>/c8d2/logs/c8d2-pilot-probe_P.out

# --- 2. the campaign as planned ---
python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast
#   no WARNING about changed pinned tools; "39 incomplete job indices: 0-38"; vendor and runtime identity not pinned; exit 1

# --- 3. the pilot: 4 lane workers + 1 merge = k 5 = C8_AMDQ_CAP (the window) ---
C8_AMDQ_CAP=5 C8_SBATCH_ARGS="-p amdq --exclude=$X" C8_LANE_MEM=245G C8_LANE_TIME=06:00:00 C8_MERGE_TIME=01:00:00 \
  $C8_PACKAGE/slurm/submit.sh --lanes 4
```

**Expected output of step 3** (format from J-SMK-2, `../stage5/smoke/smk2_submit.out`):

```
C8: queue <SCRATCH>/c8-d2/pilot1-20261006-ba68f401e46e/lanes/queue.txt: 39 incomplete indices, 179.9 estimated core-hours
C8: admission {"amd_cap": 5, "amd_live": 0, "amd_live_jobs": [], "k": 5, "limits": {"c8d2 AMD-pool jobs (amdq, amddebugq, amdpreq)": {"new": 5, "room": 5}}, "new_jobs": {"lane": {"count": 4, "partitions": ["amdq"]}, "merge": {"count": 1, "partitions": ["amdq"]}}, "partitions": ["amdq"], "room": 5, "site": "symmetry"}
C8: partition amdq: <n> idle node(s)
C8: sbatch --test-only: sbatch: Job ... to start at ... using 64 processors on nodes cnNNN in partition amdq
lane worker <W1>; log <SCRATCH>/c8-d2/pilot1-20261006-ba68f401e46e/slurm_logs/lane-<W1>.log
lane worker <W2>; log .../slurm_logs/lane-<W2>.log
lane worker <W3>; log .../slurm_logs/lane-<W3>.log
lane worker <W4>; log .../slurm_logs/lane-<W4>.log
merge <M> (afterany:<W1>:<W2>:<W3>:<W4>); log .../slurm_logs/merge-<M>.log
status: <HOME>/c8d2/venv/bin/python3 <SCRATCH>/c8d2/pkg/ba68f401e46e/tools/production.py status ... (more workers: slurm/submit.sh --lanes N)
```

**Admission arithmetic, checked with the package's own code.** `scripts/admission_check.py` replays
`slurm_submit.admission()` with the real `Context` option and partition methods against a live `squeue -u <USER>`
snapshot (`plan/squeue_snapshot_admission.txt`; nothing submitted). Results in `plan/admission_check.json`:
- k = 4 lanes + 1 merge = 5, all counted on amdq: the merge takes the workers' partition and exclusions. Room =
  `C8_AMDQ_CAP` 5 − 0 live `c8d2-` AMD-pool jobs = 5, so the submission is **admitted**.
- With the probe still live: room 4 < 5, **refused (65), "Largest admissible N for lanes N: 3", nothing submitted**.
  Wait for the probe to end.
- Without `C8_AMDQ_CAP=5` (env.sh's default 4): refused the same way. `C8_AMDQ_CAP=5` survives the sourcing of env.sh
  (checked on the login node, X11).
- Three live C63d `c8d3-` jobs are not counted (H7 is per session): admitted.
- `--lanes 3` gives k = 4: admitted.

The `C8_SBATCH_ARGS` line passes the allowlist.

**Why `C8_LANE_TIME=06:00:00`.** A lane claims an index only if est × f / (8 × 0.9) × 1.5 + 300 s fits the job's
remaining time. For the largest index that is 2.08 h at f = 1.0 (EPYC 7543) and 3.08 h at f = 1.5 (EPYC 7532).
- With all four workers running, every L8 index is claimed at t ≈ 0 and the pilot ends after about 1.33 h.
- Six hours also covers the worst start pattern: one worker alone, the others starting late. Its schedule's latest
  claim needs 4.19 h at f = 1.0 and 4.96 h at f = 1.5 (`plan/pilot_lanes.json`, 1 node), so no index is left unclaimed
  for lack of time.
- A worker exits once its lanes find nothing left to claim, so the longer limit allocates nothing extra.

**`C8_MERGE_TIME=01:00:00`** is the plan's suggestion: the projected merge takes 34 s.

**During the run** (runbook step 3):
- `squeue -u $USER -o '%i %j %T %M %L %N'`.
- About 10 minutes after each worker starts, `tail -n 40 $C8_RUN/slurm_logs/lane-<W>.log`. Expect the lane-shape line
  (8 lanes of 8 CPUs, NUMA-aligned), claims of the L8 indices, and no `FAILED` or `refused`.
- `python3 -B $C8_PACKAGE/tools/production.py status $C8_RUN --fast`.
- `ls $C8_RUN/lanes/failures/` should be empty.
- After the first claim, two pins are expected:
  - `python3 -c "import json;print(json.load(open('$C8_RUN/runtime_identity.json'))['key'])"` should print
    `04f1e51dfc2e89b039f567261a341d5723806390bdd1a222245ac5c2584c360b`, the survey's key;
  - `$C8_RUN/cpu_vendor.json` should say `AuthenticAMD`.
- A failed or killed worker: `submit.sh --lanes N` again, with the same settings.

**After the run** (runbook step 4):
- `production.py status $C8_RUN` exits 0, and the 24 groups have `merged.json`;
- `tools/verify_result.py $C8_RUN/C8_result.json`;
- `tools/accounting.py $C8_RUN --output <evidence>/accounting.json`, once the merge has ended;
- `sacct -X --duplicates` of every ledger job;
- the window closed with a DECISIONS line;
- the seed sync checked (below).

## 5. Seeds

- `3049594997687674958` (this pilot) is now in symmetry's log: 119 seeds, sha256 `6882f30e…` (copy in
  `seeds/pilot_symmetry.json`).
- The mirror `designs/forbidden_seeds.json` was merged from it with `tools/seeds.py merge` (118 → 119, the same set;
  a second merge adds nothing; `seeds/sha256.txt`).
- Expanse's log does not hold it yet. It is appended to `../stage5/fix/seeds/PENDING_EXPANSE_SYNC.txt` for the next
  two-log sync. No Expanse session was opened, by the site rule.

## Jobs

`sacct -X --duplicates` is in `sacct.txt` (times EDT). Core-hours = ElapsedRaw × physical cores: 64 on an AMD node; on
sharedq's Intel node, AllocCPUS / 2. Logs are in `<SCRATCH>/c8d2/logs/<name>_<id>.out` (copies in `logs/`).
Evidence on BeeGFS is in `<SCRATCH>/c8d2/evidence/ba68f401e46e/{ppbuild.570620.0,ppsurvey}/` (copied here).

| Job | Role | Partition, node | State | Wall | Core-h |
|---|---|---|---|---|---:|
| 570620 `c8d2-ppbuild` | export build, A-RPL-8 (`scripts/ppbuild.slurm`) | amddebugq <NODE> | FAILED 3:0 (the script's own inspect-record check; recheck ok, section 1) | 0:29 | 0.52 |
| 570621-570634 `c8d2-ppsv-<node>` | runtime-fingerprint survey, 14 nodes (`scripts/ppsurvey.slurm`) | amddebugq <NODE>, 087, 092-094, 099-104, 108-110 | COMPLETED 0:0 (14) | 0:00-0:01 each | 0.04 |
| 570635 `c8d2-plan-pilot` | the pilot plan (`slurm/plan.sh`, role plan) | sharedq <NODE> | COMPLETED 0:0 | 0:52 | 0.06 |
| **total** | 16 records | | | | **0.61** |

Budget: 0.61 of this task's 30 core-hours. The development total stays at about 1,931 core-hours.

## Files

- Scripts in `scripts/`:
  - `pp.sh`: export, the H7-checked submit and the upload;
  - `ppbuild.slurm`, `ppbuild_recheck.py`;
  - `ppsurvey.slurm`, `ppsurvey_batch.sh`, `ppsurvey_compare.py`;
  - `pilot_lanes.py`: the schedule, the deadline needs and the memory guard;
  - `admission_check.py`.
- `setup/`: the export check and the seed pre-check.
- `admission/`: every squeue snapshot before an sbatch, `h7_admission.jsonl` and `submitted.txt`.
- `ppbuild.570620.0/`: the build evidence, `identity.json` and `identity_recheck.json`.
- `survey/`: one record per node, `survey.json` and the node states.
- `plan/`:
  - `manifest.json` and `submissions.jsonl`;
  - `pilot_lanes.json`;
  - `status_before_submit.txt`;
  - `admission_check.json` and the squeue snapshot it used.
- `seeds/`, `logs/`, `sacct.txt`.
