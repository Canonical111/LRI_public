# C8(3) production runbook on symmetry

This is the production step after the Stage-7 pilot, in the form of `docs/PILOT_RUNBOOK.md`. Written 2026-10-08 from
the user's decisions of that day (`LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md`, "Production decisions"). The login node only
submits and queries. Every design, plan, combine and report step is a `c8d3-` job through `tools/slurm_submit.py raw`
(HD15). [P] marks an item still to be agreed or measured. The pilot's campaigns are on symmetry; their records are in
`benchmarks/symmetry_2026-10-c8/pilot/`. Package support: `docs/HPC.md`, section "Production".

## 0. State at writing

| Item | State | Source |
|---|---|---|
| Pilot | Complete. PA `pilotA2-s6-20261007`, PF `pilotF-s6-20261007` (pilot_full, 24 groups, `C8_pilot_result.json` verified under `OPENBLAS_CORETYPE=Zen`), PC `pilotC-s6-20261008` (pilot_subset, 710 graphs at 32,768 points, 441 confirmed). Pilot line 421.72 of 1,300 core-h | `benchmarks/symmetry_2026-10-c8/pilot/` (`PILOT_REPORT.md`, `pilot_report.json`, `pc.json`, `sigma_cost.csv`) |
| Target | SE 1 on C8(3), 0.06% of \|C8\| ≈ 1619. The pilot report's cost table gives 16,306 core-h at SE 1 (band 11,928–26,148) | `pilot_report.json` `cost_table` |
| Production line | 20,000 core-h on symmetry: `C8_BUDGET_LINE=production C8_PRODUCTION_SU_CAP=20000`. Stop and ask if a re-projection exceeds it | user decision 2026-10-08 |
| Heavy tails | The conservative rule (RECON:1373): every PC graph-campaign allocated by max(σ̂ PF 4,096, σ̂ PC 32,768); the PC-confirmed graphs stay on the monitor. In parallel, the L8 margin probe runs on the worst flagged graphs (another worktree); a real deficit leads to a pre-registered, user-approved re-run of those graphs. The ±1 is quoted with that caveat until then | user decision 2026-10-08; `tools/design_fallback.py --pc` |
| Window | `H11-prod-c63d-20261008`: C63d at most 9 AMD-pool nodes, C62d 3 (12 in total), from 2026-10-08 18:00 EDT (22:00Z), until 2026-10-10T12:00:00Z | `LRI_C8_shared/inventory/DECISIONS.md:102` |
| Precision checks | `--mp-check on`, as priced | user decision 2026-10-08 |
| Binary and model | `bin/c8d3_gmp` e9b6f6c3… (src/ unchanged since G6), model `cost_models/gmp_symmetry_epyc7543_c8.json` 01b67d0a… (measured, EPYC 7543, mp_check on) | `cost_models/README.md` |
| Export | [P] The commit with this production support (not Codex-reviewed; Mac tests and negative controls), exported to `$C8_ROOT/pkg/<sha12>`, built on an `amdq` node, and `cost_identity.py check --model $M --exe bin/c8d3_gmp --host-cpu --mp-check on` passing (the binary must still be e9b6f6c3…). `slurm_submit.py` and `production.py` changed (pinned): the production plan pins the new tools | `CHANGELOG.md` 2026-10-08 |
| Design tool | `tools/design_fallback.py` (label `fallback`), so the non-test plan needs `--approved-fallback "<user ref>"` (HD16) | `docs/HPC.md` "Production" |

**Expected cost at the target.** The pilot's `design_fallback_report.json` (no `--pc`) prices the fallback design at
1,088 core-h for a target SE of 15, 15,494 core-h at 1.5 and 61,978 at 0.75 (predicted SE including the
`--variance-margin` 1.5 factor). By the 1/SE² scaling, `--target-se 1` at the default margin is about 15,494 × 1.299² ≈
26,000 core-h before the conservative tail rule raises any σ, above the 20,000 line. The cost table's 16,306 core-h is
the E.7 projection without that margin. Step 1 therefore prices the design first and stops for the user if it does not
fit (section 4).

## 1. Preconditions

1. The production export (see the table) is built and `cost_identity.py check` passes for the symmetry model against
   its `bin/c8d3_gmp`. Its `designs/forbidden_seeds.json` mirror is current (`seeds.py mirror`; HD6).
2. The window has started (≥ 2026-10-08 22:00Z) and is recorded (DECISIONS.md:102). Before that, admission runs under
   the base split (`mode=reservation;id=H7;amd_nodes=4;amd_total=8`); the design and plan jobs fit there (one node).
3. The Expanse carry `C8_OTHER_SITE_SU` is less than 24 h old. An Expanse export before the production line prints a
   carry without `production=`; symmetry reads it with production 0.
4. Fresh seeds are checked (`seeds.py check S` exits 0) for every production plan; `slurm/plan.sh` reserves them.
5. The user's approval reference for `--approved-fallback` (the PLAN-REVIEW-LOG line of the 2026-10-08 decisions).

## 2. Commands (symmetry; exported submit lines)

```bash
ssh -T symmetry
source ~/c8d3/env.sh                                    # C8_SITE=symmetry, C8_ROOT, C8_STORE, C8_SEEDS, venv
export C8_PACKAGE=$C8_ROOT/pkg/<production sha12>; cd "$C8_PACKAGE"
source slurm/sites/symmetry/profiles.sh
export C8_BUDGET_LINE=production C8_PRODUCTION_SU_CAP=20000   # every role becomes prod_<role>; the dev and pilot lines are untouched
unset C8_COMPUTE_CAP                                    # the reservation's amd_nodes binds (slurm_submit.compute_cap)
export C8_RESERVATION='mode=reservation;id=H11-prod-c63d-20261008;amd_nodes=9;amd_total=12;until=2026-10-10T12:00:00Z'
export C8_OTHER_SITE_SU='<the carry line of Expanse budget.py, < 24 h old>'
export E=$C8_ROOT/evidence/<production sha12>/production; mkdir -p "$E"
M=$C8_PACKAGE/cost_models/gmp_symmetry_epyc7543_c8.json
PF=$C8_ROOT/runs/pilotF-s6-20261007 PC=$C8_ROOT/runs/pilotC-s6-20261008
RAW="python3 -B $C8_PACKAGE/tools/slurm_submit.py raw"
SUB="python3 -B $C8_PACKAGE/tools/slurm_submit.py"
SH="-p amdq --nodes=1 --ntasks=1 -o $C8_ROOT/logs/%x_%j.out"
JOB='set -eo pipefail; source $C8_PACKAGE/slurm/common.sh; cd $C8_PACKAGE'   # CPU guard (68 off EPYC 7543), scratch, env
python3 -B tools/budget.py | tail -8                    # the production row: spent + live + intents; its carry includes production=

# P.1 price the design with the conservative tail rule (no bundle): the rows, the target-SE-1 row and the raised graphs
$RAW --role design --dir $E -- $SH -c 64 --mem=240G -t 00:30:00 --wrap "$JOB; python3 -B tools/design_fallback.py report \
  --pilot $PF --pc $PC --cost-model $M --target-se 1 --json $E/design_report_pc.json"
#     read the last row of $E/design_report_pc.json (target_se 1: cost_total_core_hours, batches, se_total) and
#     conservative_tail_rule (raised, unchanged, monitored). Above 19,488 core-h (20,000 - the 512 below): STOP, ask the user.

# P.2 freeze the bundle: target SE 1, the line as the total cap with 512 core-h set aside for the plan, merge and
#     report jobs (8 node-hours, as the pilot priced its runbook jobs); refused (exit 1, nothing written) above the cap
$RAW --role design --dir $E -- $SH -c 64 --mem=240G -t 00:30:00 --wrap "$JOB; python3 -B tools/design_fallback.py freeze \
  --pilot $PF --pc $PC --cost-model $M --out $E/design_prod --target-se 1 --spent-core-hours 512 --total-cap 20000 \
  --seeds-log $C8_SEEDS > $E/design_freeze.json"
#     check: design_meta.json label fallback, pc.manifest_sha256 = sha256 of $PC/manifest.json, pc.pf_identity names PF;
#     design.json batches K, prediction, conservative_tail_rule; monitored_graphs = the PC-confirmed graphs
python3 -c "import json;d=json.load(open('$E/design_prod/design.json'));print(d['batches'],d['prediction'],len(d['conservative_tail_rule']['raised']),len(d['conservative_tail_rule']['monitored']))"

# P.3 the production plan(s): one per batch k = 1..K of the bundle, each with its own fresh seed (python3 -c "import secrets;print(secrets.randbits(63))")
python3 -B tools/seeds.py check <S_k>                   # exit 0: not forbidden; plan.sh reserves it before publishing (S2-002)
$RAW --role plan --dir $C8_ROOT/runs/prod<k>-<date> -- $SH -c 64 --mem=240G -t 02:00:00 --wrap "$JOB; slurm/plan.sh $C8_ROOT/runs/prod<k>-<date> \
  --design $E/design_prod --approved-fallback '<PLAN-REVIEW-LOG.md line of the 2026-10-08 production decisions>' --threads 8 \
  --index-hours 1 --backend gmp --mp-check on --cost-model $M --forbid-seeds-from $C8_SEEDS --seed <S_k>; \
  python3 -B tools/cost_identity.py check $C8_ROOT/runs/prod<k>-<date>"
#     after the plan job: production.py role prints production; the manifest's design names the bundle and
#     estimates.total_core_hours, scale.projected_files and scale.suggested_merge_time are in range [P]

# P.4 round 1: 8 lane workers + 1 merge = the window's 9 AMD-pool nodes; auto lane time (at most 23:30:00)
c8_profile lanes; unset C8_LANE_DRILL C8_LANE_CPUS C8_LANE_TIME
export C8_RUN=$C8_ROOT/runs/prod<k>-<date>
export C8_MERGE_SBATCH_ARGS="-p amdq -c 64 --mem=240G -t $(python3 -c "import json;print(json.load(open('$C8_RUN/manifest.json'))['scale']['suggested_merge_time'])")"
$SUB lanes 8 --dry-run 2>&1 | tee $E/prod<k>_lanes_dry.out   # lane time, reservation, production line projection, merge path assemble
$SUB lanes 8 2>&1 | tee $E/prod<k>_lanes_r1.out          # names c8d3-prod_lane-..., c8d3-prod_merge-...
python3 -B tools/production.py status $C8_RUN            # progress; budget.py for the line

# P.5 round 2 (and later rounds) while indices remain: short lanes that backfill around higher-priority amdq jobs
#     (C62d's advice); repeat until production.py status shows every index complete
export C8_LANE_TIME=07:30:00                             # 7-8 h; lanes skip indices longer than the lane allows
$SUB lanes 8 --dry-run 2>&1 | tee $E/prod<k>_lanes_dry_r2.out
$SUB lanes 8 2>&1 | tee $E/prod<k>_lanes_r2.out          # releases stale claims, rebuilds the queue, supersedes the pending merge

# P.6 the final merge and assembly: the last round's merge job (slurm/merge.sh: production.py merge, then
#     assemble.py --bootstrap 4096 -> $C8_RUN/C8_result.json, label production). When every index is complete and no
#     merge is pending or running (its log ended with "campaign incomplete", or it hit its time):
unset C8_LANE_TIME
$SUB lanes 0 2>&1 | tee $E/prod<k>_merge_final.out      # "every index is complete; submitting only the merge"

# P.7 K > 1 only: combine the K merged batches (assembly in float64 on the AMD pool) -> C8_final.json (final: true)
$RAW --role combine --dir $E -- $SH -c 64 --mem=240G -t 01:00:00 --wrap "$JOB; python3 -B tools/combine.py \
  $C8_ROOT/runs/prod1-<date> ... $C8_ROOT/runs/prod<K>-<date> --output $E/combined --bootstrap 4096"

# P.8 verify on the Intel login node: OpenBLAS's AMD kernels (the merge's) so the float64 gates recompute bit for bit
#     (C62d F6: the Xeon kernels differ by rounding on hard_gates.loop7.rel_deviation, a zero gate)
OPENBLAS_CORETYPE=Zen python3 -B tools/verify_result.py $C8_RUN          # K = 1: exit 0, bound to the campaign
OPENBLAS_CORETYPE=Zen python3 -B tools/verify_result.py $E/combined/C8_final.json   # K > 1
OPENBLAS_CORETYPE=Zen python3 -B tools/report.py $C8_RUN --output $E/prod<k>_report.json
python3 -B tools/budget.py | tail -8                    # the production line's spend; the dev and pilot rows unchanged
```

- **Flags.** Every flag above is in the tools' argparse: `design_fallback.py freeze|report` (`--pilot`, `--pc`,
  `--cost-model`, `--out`, `--target-se`, `--spent-core-hours`, `--total-cap`, `--seeds-log`, `--json`),
  `production.py plan` through `slurm/plan.sh` (`--design`, `--approved-fallback`, `--threads`, `--index-hours`,
  `--backend`, `--mp-check`, `--cost-model`, `--forbid-seeds-from`, `--seed`; plan.sh adds `--scratch` and
  `--reserve-seed`), `slurm_submit.py lanes N [--dry-run]`, `combine.py BATCH ... --output DIR [--bootstrap N]`,
  `verify_result.py TARGET`, `report.py DIRECTORY --output FILE`, `seeds.py check SEED`, `cost_identity.py check RUN`.
  `--target-se`, `--target-rel` and `--budget-core-hours` exclude each other: the line enters the freeze as
  `--total-cap` (with `--spent-core-hours` for the reserve), not as a budget.
- **Index size.** `--index-hours 1` (the default is 1.5) keeps an index well inside the 7:30 lanes of round 2; the plan's
  `estimates.max_index_wall_seconds` must stay below the round-2 lane time minus the lane margin [P].
- **The lane rounds.** Round 1's auto lane time is capped at 23:30:00 (`amdq` 24 h): about 8 × 64 × 23.5 ≈ 12,000
  core-h reserved, plus the merge. The rest goes in 7:30 rounds (8 × 64 × 7.5 = 3,840 core-h each). Each `lanes 8`
  is gated on the production line (spent + live reservations + unresolved intents + the new reservations ≤ 20,000).
  A round that would pass it is refused (65) with the largest admissible N and lane time: lower N or `C8_LANE_TIME`,
  never the cap.
- **Records.** Every job is `c8d3-prod_<role>-<C>-<T>`; `budget.py` shows them in the `production` row only.
- **After each round**, rsync `$E`, the jobs' logs and each campaign's `manifest.json`, `slurm_logs/`, `lanes/` and
  `groups/*/merged.json` into `benchmarks/symmetry_2026-10-c8/production/`. Bulky files go in `raw_evidence.tgz`.

## 3. Gates

- **Design** (P.1–P.2): the freeze binds PC to PF (a PC whose screen names another PF, of another executable, numerics,
  MP mode or inputs, or a non-confirm campaign, is refused); `conservative_tail_rule` lists every raised graph-campaign
  with σ̂ before, σ̂ PC at 32,768 and the factor, and the monitored (PC-confirmed) graphs; the predicted cost plus 512 is
  within 20,000.
- **Plan** (P.3): `campaign_role` production, `design.label` fallback with `approved_fallback`, measured basis,
  `cost_identity.py check` exit 0, the seed reserved.
- **Result** (P.6–P.8): all 24 groups merged; `C8_result.json` (or `C8_final.json`) label production, final; the
  coverage guard passes (the bundle's counts × s per graph, the bundle's replicates); `verify_result.py` exit 0 under
  `OPENBLAS_CORETYPE=Zen`. The tail monitor (`tail_monitor` in the result) lists L8 graphs with a two-campaign mean
  ξ > 0.44 and flags those above 3% of their group variance; read it against the bundle's `monitored_graphs`. No flag
  changes a value; flagged graphs go to the results review, with the margin probe's findings.
- **Budget**: the production row of `budget.py` within 20,000 core-h; the dev line (symmetry own) and the pilot line
  unchanged by production jobs.

## 4. Stop rules

- **Design above the line.** If P.1's target-SE-1 row costs more than 19,488 core-h, or P.2 refuses ("exceeds
  --total-cap"), STOP and ask the user. Their options include a smaller target (a larger SE), a larger line, or the best
  design within the line (`--budget-core-hours 19488` in place of `--target-se 1`; integer; it reports the predicted
  SE). The variance margin (`--variance-margin`, default 1.5) is part of the fallback's rule and changes only by the
  user's decision.
- **Re-projection above the line** at any round (the dry run's projection, or `production.py status`'s remaining
  estimate plus the spent line above 20,000): STOP and ask (user decision 2026-10-08).
- **Admission exits.** 65: wait, never stack a submission past it. 65 after `until` (2026-10-10T12:00:00Z): every
  AMD-pool admission is refused; reset `C8_RESERVATION` to the base split (`lanes 3` at most) or agree a new window. 64:
  a stale carry, a missing `C8_PRODUCTION_SU_CAP` or a malformed reservation: fix the environment, never bypass it. 75:
  the session lock is held; retry later. 69 from the lock or its NFS mount check: STOP and revise with the user.
- **68 (CPU guard).** The job landed on a non-7543 node. Add the node to `C8_AMD_EXCLUDE_EXTRA` in `~/c8d3/env.sh`,
  resubmit and record the node.
- **Heavy tails.** A margin-probe deficit on a monitored graph: report it and wait; the remedy (a lower rate for those
  graphs) is a pre-registered, user-approved re-run, never an edit of production data.
- **Findings.** A code defect: a fix round, and production resumes only on the fixed export with fresh seeds for every
  re-planned batch.
