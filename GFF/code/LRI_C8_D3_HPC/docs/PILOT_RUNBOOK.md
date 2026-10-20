# Stage-7 pilot runbook on symmetry (A-SMK-5)

This is the symmetry form of PLAN "Pilot (Stage 7)" (`LRI_C8_D3_HPC_loop/PLAN.md:3741-3794`). Amendment A1.1 moved the
pilot from Expanse to symmetry (`LRI_C8_D3_HPC_loop/artifacts/AMENDMENT_A1_site.md`). Written 2026-10-06 in Stage 5.
**Nothing here is submitted before G6** (PLAN A-SMK-5, `PLAN.md:3427-3434`). The login node only submits and queries.
Every plan, selection and report step is a `c8d3-` job through `tools/slurm_submit.py raw` (HD15). [P] marks an item
still to be agreed or measured before the pilot. Evidence paths without a prefix (`stage5_*/`, `pil0/`, …) are under
`benchmarks/symmetry_2026-10-c8/` (`pil0/` and the other wave folders under its `stage5_59d4922/`).

## 0. State at writing

| Item | State | Source |
|---|---|---|
| Approved commit | [P] G6, Stage 6 (Codex inspection). Fixes for F8-d3 (`production.py`, `assemble.py`) and F13-d3 (`tools/thru_report.py`) are queued for Stage 6 | `LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md:590-600,639-643` |
| PA plan (J-PIL-0) | **Published.** Job 570565 on D's export `59d4922842ec`, not submitted. Valid only if the G6 commit keeps `bin/c8d3_gmp` `8f3a36aa…`, the model `0fc934e7…` and every `PINNED_TOOLS` file. F8-d3's fix changes `production.py`, a pinned tool. Stage 6 then re-runs J-SWEEP-2, the data-only commit, J-BLD and J-PIL-0 (`PLAN.md:3933-3943`), which gives a new PA directory and fresh seeds. HD11 refuses a re-plan on the old model | `benchmarks/symmetry_2026-10-c8/stage5_59d4922/wave45_logs/c8d3-plan-815700051e56-31db02f43e38_570565.out`, `pil0/` |
| J-PIL-0's `lanes 2 --dry-run` and `lanes 3 --dry-run` | [P] They wait for a quiet AMD pool: C63d holds no other AMD job or intent, and `c8d2-` AMD ≤ 4. They print the auto lane time, the reservation, the SU projection and the merge path per N | `LRI_C8_D3_HPC_loop/artifacts/STAGE5_SYMMETRY_RUNBOOK.md` W6 |
| H11 window | [P] Each session first runs a start-latency probe (7.0). Then a DECISIONS line fixes the window's nodes, dates, shares and `until`. Agreed frame: the pilot session holds 5 live AMD-pool jobs (4 lane workers + 1 merge), the other session 3, 8 in total | `LRI_C8_shared/inventory/DECISIONS.md:94` |
| Pilot line | [P] The user's line, stated in reservation terms. It counts allocated core-h, 64 per AMD node-hour, the same way as the dev line (A1.3). PLAN's request for the Expanse pilot was 1,300 SU in reservation terms (`PLAN.md:4232-4238`); the symmetry line is still to be agreed with the user | `LRI_C8_D3_HPC_loop/artifacts/AMENDMENT_A1_site.md` A1.3 |
| Design tool | `tools/design_fallback.py` (A-DES-2). C62d's post-Stage-6 `HANDOFF_design.json` re-issue is vendored before the pilot (H6, user decision "Fallback now, vendor later") | `PLAN-REVIEW-LOG.md:494-495` |
| Cost model | `cost_models/gmp_symmetry_epyc7543_c8.json`, sha256 `0fc934e7…`, executable `8f3a36aa…`, EPYC 7543, `mp_check` on, 48,346 keys, measured. J-SWEEP-2 570403 made it. It is refreshed in Stage 6 if the binary or a pinned tool changes | `cost_models/README.md`; `benchmarks/symmetry_2026-10-c8/stage5_e3b9252/sweep2_570403/` |

## 1. The PA plan (J-PIL-0, 570565)

- **Selection** (`pil0/pa_selection.json`): `pilot_select.py stage-a` with seed 2712577989054501105, registered in
  symmetry's `$C8_SEEDS` before the job. Role `stage_a`. There are 2,733 L8 graphs: free 2,008 stratified + 142
  heaviest 1%, power 544 + 39. The P1c parts are 63 (free) and 14 (power), inside the stratified part. Rule: "stage A
  1/8 per stratum (sector x T bin x M tertile) + the heaviest 1% per sector; P1c 1/32 of each stratum of the
  stratified part (E.8, HD14)". The inputs manifest is `ece2e4a4…`.
- **Plan** `$C8_ROOT/runs/pilotA-20261006`, made by `slurm/plan.sh` with `--pilot --graphs pa_selection.json
  --replicates 8 --threads 8 --index-hours 0.25 --backend gmp --mp-check on --cost-model <symmetry model>
  --forbid-seeds-from $C8_SEEDS --seed 1742322421360805476` (`pil0/job.sh`).
  - `campaign_role` `pilot_subset`, cost basis `measured`, selection `{sha256 225e0d62…, role stage_a, seed
    2712577989054501105}`. Manifest sha256 `24cf8590…`.
  - 21 jobs, 44,960 tasks, 182 checkpoints in 4 groups (a/b × free/power at L8), one merge pass each.
  - 32.13 estimated busy core-h; the largest index wall is 813.1 s.
  - 388 projected files and 0.081 GB of merge scratch. The suggested merge time is 01:00:00.
  - `cost_identity.py check`: ok (model `0fc934e7…`, executable `8f3a36aa…` on both sides).
  - The plan job registered seed 1742322421360805476. `production.py role` prints `pilot_subset`.
- **Merge path.** On a `pilot_subset` campaign, `slurm/merge.sh` runs `pilot_report.py subset-check`. It writes
  `subset_summary.json` and no `C8_*result.json`. Its `--dry-run` names "subset-check (no coefficient assembly)":
  J-DRL-9 shows this on symmetry (`stage5_59d4922/drl9/lanes1_dry.out`).

## 2. Expected spend on the symmetry model, and the reservation

Busy core-h on EPYC 7543 from the sweep's `cost_summary.json` (`stage5_e3b9252/sweep2_570403/`: its
`pilot_estimate_busy_core_hours`, `pilot_estimate_su` and `ratio_to_plan_symmetry_basis`). Allocated core-h at the
summary's nominal allocated/busy of 1.2:

| Part | Busy core-h | Allocated core-h at 1.2 | PLAN's symmetry basis (busy) |
|---|---:|---:|---:|
| PA (expectation over the seeded draw; the published plan: 32.13) | 31.86 | 38.2 | 41.5 |
| PF at R = 8: L8 178.75 + L ≤ 7 7.39 | 186.14 | 223.4 | 228.5 |
| **Default pilot (PA + PF)** | **217.99** | **261.6** | 270.0 |
| Branch: R = 16 for PF at L8 | +178.75 | +214.5 | +219.1 |
| Branch: PC, capped at 25% of PF's L8 cost | +44.69 | +53.6 | +54.8 |
| **With every pre-registered branch** | **441.43** | **529.7** | 543.9 |

- The ratios to PLAN's basis are PA 0.77, PF 0.81 and PC cap 0.82 (`ratio_to_plan_symmetry_basis`). J-SMK-4 measured
  lane mode on this model at busy 0.937 (allocated/busy 1.068; `stage5_59d4922/smk4/accounting.json`).
- **Reservation per step** is what the line gates (D.11): N × 64 × T_lane + 64 × the merge's `-t`, plus the raw jobs.
  T_lane is the auto lane time ⌈max(1.5·W + 0.25 h, need_max + 0.25 h)⌉ in 15-min steps (D.10), printed by `lanes N
  --dry-run`. [P] PA's comes from J-PIL-0's dry runs. PF's and PC's come from their own dry runs. The stage-A report
  re-projects PF and every branch from PA's measured η, f_E and per-graph cost, as both expected spend and peak
  reservation (A-PIL-2). Its six runbook jobs (the PF plan, select, PC plan and full-report raw jobs, and the PF and
  PC merges, 8 node-hours) are priced at 512 core-h on symmetry (`tools/pilot_report.py` `RUNBOOK_SHARED`;
  `docs/HPC.md`, "The pilot's re-projection").

## 3. Preconditions (A-PIL-1, `PLAN.md:3437-3443`; G6 → Stage 7, `PLAN.md:3944-3951`)

1. G6 APPROVED commit. Its export has passed J-BLD, and `cost_identity.py check --model … --exe …` passes for the
   symmetry model against that commit's `bin/c8d3_gmp`. `scheduled_with` and `refresh_report.json` are in the
   evidence.
2. The PA plan comes from J-PIL-0 on that commit's export: the measured basis, and `cost_identity.py check` ok.
   J-PIL-0's `lanes 2/3 --dry-run` were recorded.
3. The user's pilot line (`C8_PILOT_SU_CAP`, in reservation terms) and the H11 window (DECISIONS line with `until`) are
   recorded. Both sessions' start-latency probes ran first, and their queue waits are recorded.
4. Fresh seeds are checked (`seeds.py check S` exits 0) and registered. Symmetry's `$C8_SEEDS` holds Expanse's newest
   log (`seeds.py merge`, `docs/HPC.md` "The seed log").
5. The L8 packs are at the approved inputs manifest (J-BLD's `link-l8` and `verify-inputs`). `--mp-check on` is set,
   and no numerics profile is used (U1). H6 is vendored, or the fallback is recorded.
6. The Expanse carry `C8_OTHER_SITE_SU` is less than 24 h old. Expanse MFA is therefore needed at least daily.

## 4. Commands (symmetry; exported submit lines)

```bash
ssh -T symmetry
source ~/c8d3/env.sh                                    # C8_SITE=symmetry, C8_ROOT, C8_STORE, C8_SEEDS, venv
export C8_PACKAGE=$C8_ROOT/pkg/<approved sha12>; cd "$C8_PACKAGE"
source slurm/sites/symmetry/profiles.sh
export C8_BUDGET_LINE=pilot C8_PILOT_SU_CAP=<user-approved core-h, reservation terms>
unset C8_COMPUTE_CAP                                    # the reservation's amd_nodes binds (slurm_submit.compute_cap)
# C8_RESERVATION stays env.sh's base split (mode=reservation;id=H7;amd_nodes=4;amd_total=8) until the window line exists (7.0)
export C8_OTHER_SITE_SU='<the carry line of Expanse budget.py, < 24 h old>'
export E=$C8_ROOT/evidence/<approved sha12>/pilot; mkdir -p "$E"
M=$C8_PACKAGE/cost_models/gmp_symmetry_epyc7543_c8.json
RAW="python3 -B $C8_PACKAGE/tools/slurm_submit.py raw"   # under C8_BUDGET_LINE=pilot every role becomes pilot_<role>
SUB="python3 -B $C8_PACKAGE/tools/slurm_submit.py"
SH="-p amdq --nodes=1 --ntasks=1 -o $C8_ROOT/logs/%x_%j.out"
JOB='set -eo pipefail; source $C8_PACKAGE/slurm/common.sh; cd $C8_PACKAGE'   # CPU guard (68 off EPYC 7543), scratch, env
python3 -B tools/budget.py | tail -8                    # the pilot line: spent + live + intents; the dev line is untouched

# 7.0 start-latency probe before the window is agreed, under the base split (1 whole AMD node, 10-min limit, 5 min used;
#     10.7 core-h reserved on the pilot line)
$RAW --role probe --dir $E -- $SH -c 64 --mem=240G -t 00:10:00 --wrap "date; sleep 300; date"
#     record the wait: sacct -u <USER> -X -j <id> -o JobID,Submit,Start,End -P
#     then both sessions agree the window in its own DECISIONS line (nodes, dates, shares, until), in the H11 frame of
#     LRI_C8_shared/inventory/DECISIONS.md:94
export C8_RESERVATION="mode=reservation;id=<H11 window DECISIONS item>;amd_nodes=5;amd_total=8;until=<UTC YYYY-MM-DDTHH:MM:SSZ>"

# 7.1 PA: J-PIL-0's campaign, <date> = 20261006 (after a Stage-6 re-plan: the new J-PIL-0 directory); N = 3 per the
#     Stage-5 runbook, to be confirmed against J-PIL-0's lanes 2/3 dry runs
c8_profile lanes; unset C8_LANE_DRILL C8_LANE_CPUS C8_LANE_TIME
export C8_RUN=$C8_ROOT/runs/pilotA-20261006 C8_MERGE_SBATCH_ARGS='-p amdq -c 64 --mem=240G -t 01:00:00'
$SUB lanes 3 --dry-run 2>&1 | tee $E/pa_lanes_dry.out    # lane time, reservation, "subset-check (no coefficient assembly)"
$SUB lanes 3 2>&1 | tee $E/pa_lanes.out
# stage-A report (after the PA merge's subset-check): GO/NO-GO, R per sector, re-projection in expected spend and in peak reservation
$RAW --role stagea --dir $C8_ROOT/runs/pilotA-<date> -- $SH -c 16 --mem=32G -t 01:00:00 --wrap "$JOB; python3 -B tools/pilot_report.py stage-a $C8_ROOT/runs/pilotA-<date> --output $E/stageA.json"

# 7.2 PF: every L3-L8 kernel, a fresh registered seed, R from action 4 or the user's choice (the bracketed options)
python3 -B tools/seeds.py check <S_PF>                  # exit 0: not forbidden; plan.sh reserves it before publishing (S2-002)
$RAW --role plan --dir $C8_ROOT/runs/pilotF-<date> -- $SH -c 64 --mem=240G -t 01:00:00 --wrap "$JOB; slurm/plan.sh $C8_ROOT/runs/pilotF-<date> \
  --pilot --points 4096 --replicates 8 [--group-replicates free:8=16] [--group-replicates power:8=16] --threads 8 \
  --index-hours 0.25 --backend gmp --mp-check on --cost-model $M --forbid-seeds-from $C8_SEEDS --seed <S_PF>; \
  python3 -B tools/cost_identity.py check $C8_ROOT/runs/pilotF-<date>"
c8_profile lanes; unset C8_LANE_DRILL C8_LANE_CPUS C8_LANE_TIME
export C8_RUN=$C8_ROOT/runs/pilotF-<date> C8_MERGE_SBATCH_ARGS='-p amdq -c 64 --mem=240G -t 02:00:00'
$SUB lanes 4 --dry-run 2>&1 | tee $E/pf_lanes_dry.out    # 4 workers + 1 merge = the window's 5 AMD-pool nodes
$SUB lanes 4 2>&1 | tee $E/pf_lanes.out                  # the merge assembles C8_pilot_result.json (label pilot)

# 7.3 screen -> PC selection (32,768 points, nest [4096], capped at 25% of PF's L8 cost) -> PC plan -> PC lanes
python3 -B tools/seeds.py check <registered> && python3 -B tools/seeds.py add --seed <registered> --label 'pilot PC selection (pilot_select confirm)'
$RAW --role select --dir $C8_ROOT/runs/pilotF-<date> -- $SH -c 16 --mem=32G -t 01:00:00 --wrap "$JOB; python3 -B tools/pilot_select.py confirm \
  --screen $C8_ROOT/runs/pilotF-<date> --pa $C8_ROOT/runs/pilotA-<date> --seed <registered> --out $E/pc.json"
# after the select job ends: an empty PC selection is never planned (D.3); the report records its empty_reason (E.6)
PC_N=$(python3 -B tools/pilot_select.py count $E/pc.json)    # schema-checked graph count; nonzero exit if malformed
if [ "$PC_N" -gt 0 ]; then
python3 -B tools/seeds.py check <S_PC>
$RAW --role plan --dir $C8_ROOT/runs/pilotC-<date> -- $SH -c 64 --mem=240G -t 01:00:00 --wrap "$JOB; slurm/plan.sh $C8_ROOT/runs/pilotC-<date> \
  --pilot --graphs $E/pc.json --replicates 8 --threads 8 --index-hours 0.25 --backend gmp --mp-check on \
  --cost-model $M --forbid-seeds-from $C8_SEEDS --seed <S_PC>; python3 -B tools/cost_identity.py check $C8_ROOT/runs/pilotC-<date>"
# after the plan job ends
c8_profile lanes; unset C8_LANE_DRILL C8_LANE_CPUS C8_LANE_TIME
export C8_RUN=$C8_ROOT/runs/pilotC-<date> C8_MERGE_SBATCH_ARGS='-p amdq -c 64 --mem=240G -t 01:00:00'
$SUB lanes 2 --dry-run && $SUB lanes 2                   # merge path: subset-check (no assembly)
PC_ARGS="--pc-selection $E/pc.json --pc $C8_ROOT/runs/pilotC-<date>"
else
PC_ARGS="--pc-selection $E/pc.json"                                   # PC skipped: nothing selected
fi

# 7.4 full report (after the PC merge's subset-check, when PC ran); then the fallback cross-check at alpha = 1/2
$RAW --role report --dir $E -- $SH -c 32 --mem=64G -t 02:00:00 --wrap "$JOB; python3 -B tools/pilot_report.py full \
  --pa $C8_ROOT/runs/pilotA-<date> --pf $C8_ROOT/runs/pilotF-<date> $PC_ARGS \
  --output $E/pilot_report.json --markdown $E/PILOT_REPORT.md"
$RAW --role report --dir $E -- $SH -c 64 --mem=240G -t 00:30:00 --wrap "$JOB; python3 -B tools/design_fallback.py report \
  --pilot $C8_ROOT/runs/pilotF-<date> --cost-model $M --json $E/design_fallback_report.json"   # design.py report once H6 is vendored
```

- **Verbatim lines.** The stage-A, select, `count`, `PC_ARGS` and full-report lines are those of
  `tests/fixtures/runbook_stage7_pilot_tools.txt`, which `tests/test_pipeline.py` runs. Only `$SH` and `$JOB` change
  per site. On symmetry every partition is exclusive, so `-c 16 --mem=32G` still takes and is priced as a whole AMD
  node.
- **Changes from PLAN's Expanse lines.**
  - `slurm/submit.sh` does not exist; lanes go through `slurm_submit.py lanes N`.
  - Plans go through `slurm/plan.sh`, which runs `production.py plan --scratch $C8_SCRATCH --reserve-seed
    $C8_SEEDS` (the seed rechecked and reserved under the lock before anything is built or published; S2-002), then
    `ledger.py register`.
  - Merges run on whole `amdq` nodes (one CPU vendor per campaign).
  - Lane widths are 8 × 8 at `--threads 8` (`profiles.sh`).
  - There is no `-A` and no `--exclusive`. The tool adds `--no-requeue` and the CPU pin's `--exclude`.
- **After each wave**, rsync `$E`, the jobs' logs and each campaign's `manifest.json`, `slurm_logs/`, `lanes/` and
  `groups/*/merged.json` into `benchmarks/symmetry_2026-10-c8/pilot/` (A-PIL-5 adapted from
  `benchmarks/expanse_2026-10-c8/pilot/`). Bulky files go in `raw_evidence.tgz`.

## 5. Gates and stop rules

- **GO after stage A** (A-PIL-2) needs all three: no `mp_alarm`, no worker failure, and every branch's peak reservation
  inside the remaining pilot line. The branches are PF at R = 8, PF with R = 16 at L8, action 4's mixed R, each
  followed by PC at its cap. `pilot_report.py stage-a` also returns NO-GO when the worker-failure check was not
  evaluated. **NO-GO stops the pilot and the user is asked.**
- **PF** (A-PIL-3): `campaign_role` `pilot_full`. All 24 groups are complete and merged. The coverage guard passes:
  every inventory graph at 4,096 points and the planned replicates per group. `C8_pilot_result.json` is labelled
  `pilot`, and its C8 value is "for sizing only".
- **Tail actions** (A-PIL-4) use the pre-registered thresholds unchanged (PLAN F25, `PLAN.md:323-328`).
  - Screen: ξ̂ > 0.38 or largest share > 0.05 in either campaign at 4,096 points.
  - Confirm when the two-campaign mean ξ̄(32,768) > 0.44.
  - Switch to R = 16 when a sector's P̂8 > 1.13. Flag a stratum when P̂8 > 1.196 (≥ 500 graph-campaigns).
  - Apply the 3% proportional hold.
  - Zero-channel L8 graphs (s_G = 4) take part in no action.
  - For a held sector, the margin re-derivation (RECON:1357-1392) runs as short `amdq` raw jobs. Nothing changes a
    pilot value.
- **Report** (A-PIL-5): `pilot_report.json`, `PILOT_REPORT.md`, `growth_c63d.csv` and `sigma_cost.csv`, a
  `PERF_NOTES.md` entry for C62d, and the user's decisions: target SE, R, any held sector, and the MP tier policy
  (RECON D2).
- **Budget** (A-PIL-6): the pilot's core-h from `budget.py` (roles `pilot_*`) stay within the approved line, and the
  dev line is untouched. **G7** is A-PIL-1..6. The user then decides the production target; no production job is
  planned or submitted.
- **Stop rules.**
  - **Admission exits.**
    - 65 from admission: wait, and never stack a submission past it.
    - 65 after the window's `until`: every AMD-pool admission is refused ("the re-split … expired …: reset
      C8_RESERVATION to the base split (H7)"; `slurm_submit.Reservation.normal_refusal`). Reset it to
      `mode=reservation;id=H7;amd_nodes=4;amd_total=8`, where `lanes 4` (5 nodes) no longer fits, or agree a new
      window line.
    - 64: a carry older than 24 h or a malformed reservation. Fix the environment; never bypass it.
    - 75: the session lock is held past `C8_LOCK_WAIT`; the message names the holder (J-DRL-4). Retry later.
    - 69 from the session lock or its NFS mount check: STOP and revise with the user.
  - **68 (CPU guard).** The job landed on a non-7543 node. Add the node to `C8_AMD_EXCLUDE_EXTRA` in `~/c8d3/env.sh`,
    resubmit and record the node.
  - **Unattributable `c8d3-` job.** The host decides; no tool cancels it.
  - **Findings.**
    - An L8 precision-contract finding: report it and wait.
    - A code defect found by the pilot: a new fix round and inspection (within U4's counts). The pilot resumes only on
      the new approved commit, with fresh seeds for every re-planned campaign.
    - Until F8-d3's fix is in the approved commit, do not invalidate a merged index of a pilot campaign: the group
      re-merge after a recovery stops at "Checksum mismatch: graph_costs.csv" (`docs/HPC.md` "Stage 5 results").
