#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 06:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-DES-5 (PLAN job table; A-DES-5): the dry run of the design at production size, on symmetry sharedq.
#  1. tools/accounting.py on the merged J-SWEEP-2 campaign (sweep2-5d7586e9f1ab: all 24,173 graphs, both campaigns,
#     2 x 512 points, final default binary; its eta_node comes from its self-registered ledger entry, R10), and on the
#     lane campaigns J-SMK-4 (smk4-20261005) and the J-SMK-3 batches desc1/desc2, for the lane-mode eta_node that the
#     refined cost table (docs/PERFORMANCE.md, A-PERF-4) quotes beside the sweep's.
#  2. tools/design.py report --test-only on the sweep (the target table with the sweep's eta_node), and again with
#     --eta-node <J-SMK-4's> (the same allocations; cost scaled by the efficiency).
#  3. tools/design.py freeze --pilot <sweep> --test-only --target-rel T for T = 1e-3, 5e-4, 2.5e-4, 1.35e-4 (costs from
#     the campaign's own checkpoints, i.e. the campaign-keyed costs of the final binary, R05; no --total-cap: the dry
#     run measures sizes, and the budget is the user's decision), into $W/bundles/des5_T.
#  4. production.py plan --design <bundle> --test-graphs all (a test-only plan of every graph: test-only bundles are
#     accepted by test-only plans only) with the symmetry cost model and the design's own sizing (--threads 8,
#     --checkpoint-tasks 256, --index-hours 1.5, gmp), a fresh seed checked against $C8_SEEDS, under GNU time -v; the
#     plan is NOT submitted. des5_measure.py records tasks, checkpoints, sqlite size, per-index task files, manifest
#     size, plan wall and RSS, index count, predicted largest index wall, merge passes and every cap; the seed is then
#     added to $C8_SEEDS with a label, and the plan directory is DELETED (A-DES-5).
# Default path only (D1): no --numerics, no --rates, no GMP_PREFIX.
# Usage: C8_PACKAGE=<SCRATCH>/c8d2/pkg/5d7586e9f1ab SEEDS="s1 s2 s3 s4" sbatch --export=ALL -J c8d2-s5des5 s5des5.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${SEEDS:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5des5.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=$D/work/des5-$TAG; mkdir -p "$W/bundles" "$W/plans"
SW=<SCRATCH>/c8-d2/sweep2-$TAG; CM=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8.json
M=$D/jobs/stage5/des5/des5_measure.py
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; sweep $SW; work $W; evidence $E"
{ hostname; lscpu; free -g; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" "$CM" "$C8_PACKAGE"/tools/{design,production,accounting,ledger,seeds}.py "$C8_PACKAGE/bin/c8d2_gmp" "$M" | tee "$E/inputs.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS
cd "$C8_PACKAGE" || exit 64
status=0
# 1. accounting
for c in sweep2-$TAG smk4-20261005 desc1-20261005 desc2-20261005; do
  python3 -B tools/accounting.py "<SCRATCH>/c8-d2/$c" --output "$E/accounting_$c.json" > "$E/accounting_$c.stdout" 2>&1
  echo "accounting $c exit $?"; tail -3 "$E/accounting_$c.stdout" | cut -c1-300
done
ETA_LANE=$(python3 -c "import json;print(json.load(open('$E/accounting_smk4-20261005.json'))['eta_node'])")
echo "J-SMK-4 lane eta_node $ETA_LANE"
# 2. report (sweep eta_node, then the lane eta_node)
t=$(date +%s); /usr/bin/time -v -o "$E/time_report.txt" python3 -B tools/design.py report --pilot "$SW" --test-only --json "$E/report_sweep_eta.json" \
  > "$E/report_sweep_eta.stdout" 2>&1; s=$?; echo "report (sweep eta) exit $s after $(( $(date +%s) - t )) s"; head -12 "$E/report_sweep_eta.stdout" | cut -c1-200
[ $s -eq 0 ] || status=$s
python3 -B tools/design.py report --pilot "$SW" --test-only --eta-node "$ETA_LANE" --json "$E/report_lane_eta.json" > "$E/report_lane_eta.stdout" 2>&1; s=$?
echo "report (lane eta $ETA_LANE) exit $s"; head -8 "$E/report_lane_eta.stdout" | cut -c1-200; [ $s -eq 0 ] || status=$s
# 3. freezes and 4. plans
set -- $SEEDS; i=0
for T in 1e-3 5e-4 2.5e-4 1.35e-4; do
  i=$((i+1)); SEED=${!i}; B=$W/bundles/des5_$T; P=$W/plans/des5_$T
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_freeze_$T.txt" python3 -B tools/design.py freeze --pilot "$SW" --test-only --target-rel "$T" --seeds-log "$C8_SEEDS" --out "$B" \
    > "$E/freeze_$T.stdout" 2>&1; s=$?
  echo "freeze $T exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || { status=$s; tail -5 "$E/freeze_$T.stdout"; continue; }
  cp -p "$B/design.json" "$E/design_$T.json"; cp -p "$B/design_meta.json" "$E/design_meta_$T.json"; sha256sum "$B"/design.json "$B"/design_meta.json >> "$E/bundles.sha256"
  python3 -B tools/seeds.py check "$SEED" > "$E/seed_check_$T.txt" 2>&1 || { echo "seed $SEED refused"; status=65; continue; }
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_plan_$T.txt" python3 -B tools/production.py plan "$P" --design "$B" --test-graphs all --cost-model "$CM" --backend gmp \
    --threads 8 --checkpoint-tasks 256 --index-hours 1.5 --forbid-seeds-from "$C8_SEEDS" --seed "$SEED" > "$E/plan_$T.stdout" 2> "$E/plan_$T.stderr"; s=$?
  wall=$(( $(date +%s) - t )); echo "plan $T exit $s after $wall s"; tail -3 "$E/plan_$T.stderr" | cut -c1-300
  if [ $s -ne 0 ]; then status=$s; continue; fi
  python3 -B tools/seeds.py add --seed "$SEED" --label "J-DES-5 dry-run plan at target-rel $T ($P; test-only, never submitted, deleted after measurement)" >> "$E/seeds_add.txt" 2>&1
  python3 -B "$M" "$P" "$B" --time "$E/time_plan_$T.txt" --wall "$wall" --out "$E/measure_$T.json"; s=$?; [ $s -eq 0 ] || status=$s
  gzip -c "$P/manifest.json" > "$E/plan_manifest_$T.json.gz"
  du -sb "$P" > "$E/du_plan_$T.txt"; find "$P" -type f | wc -l >> "$E/du_plan_$T.txt"
  rm -rf "$P"; if [ -e "$P" ]; then echo "plan directory $P NOT deleted"; status=70; else echo "deleted $P" | tee -a "$E/deleted.txt"; fi
done
ls -la "$W/plans" > "$E/plans_after.txt" 2>&1
tar -C "$W" -czf "$E/bundles.tgz" bundles
python3 -B tools/seeds.py list > "$E/seeds_after.txt" 2>&1
echo "finished $(date -Is), status $status"
exit $status
