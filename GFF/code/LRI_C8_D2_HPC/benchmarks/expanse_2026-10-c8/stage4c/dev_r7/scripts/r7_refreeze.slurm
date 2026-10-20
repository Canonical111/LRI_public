#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=16G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-s4c-r7-refreeze
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4c R7 (A-FLAG-6), follow-up of r7_analysis.slurm (added after its results; run from a verified copy of this
# committed file, with the tools of the export ebf01f62e833):
#   1. The freezes of r7_analysis used each sweep's own eta_node from tools/accounting.py: 0.136 for the map sweep, whose
#      plan step took about 11 minutes longer on Lustre, against 0.481 for the exact sweep, although its integration
#      work was smaller. The allocated core-hours of the two freezes therefore differ by that planning time. Here both
#      sweeps are frozen again at the four targets with ONE eta_node (--eta-node, test-only: the exact sweep's measured
#      0.4807242866987714), so the core-hour ratio is the variance x cost change with the integer allocation.
#   2. Plan timing: the sweep's test-only plan (all graphs, 2 x 512, bootstrap chunk 512, 8 shards) with --rates, without,
#      and with --rates again, back to back on this job's node; each plan directory is removed after its manifest is
#      recorded (never run; the seed is the plan-only check seed already in $C8_SEEDS).
#   3. r7_compare.py again with the equal-eta bundles (compare_eqeta.json).
# Usage: C8_PACKAGE=<export> R7_DIR=<work> R7_SOURCE=<J-SWEEP-1> R7_SEED_PLANCHECK=<seed> R7_APPROVAL=<text> sbatch --export=ALL r7_refreeze.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${R7_DIR:?}" "${R7_SOURCE:?}" "${R7_SEED_PLANCHECK:?}" "${R7_APPROVAL:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r7refreeze.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; work $R7_DIR; evidence $E"
sha256sum "$0" "$HOME/c8d2/env_expanse.sh" | tee "$E/script_env.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE" || exit 64
SC=benchmarks/expanse_2026-10-c8/stage4c/dev_r7/scripts; M=$R7_DIR/sweep_map; X=$R7_DIR/sweep_exact; PROV=$R7_DIR/prov; ETA=0.4807242866987714
fail() { echo "FAILED: $*"; exit 3; }
echo "== $(date -Is) 1. equal-eta freezes (eta_node $ETA)"
FRESH=(); EXACT=()
for t in 1e-3 5e-4 2.5e-4 1.35e-4; do
  python3 -B tools/design.py freeze --pilot "$M" --rates-bundle "$PROV" --test-only --eta-node $ETA --target-rel $t --out "$R7_DIR/fresh_eqeta_$t" > "$E/freeze_fresh_eqeta_$t.json" 2>&1 || { cat "$E/freeze_fresh_eqeta_$t.json"; fail "fresh $t"; }
  python3 -B tools/design.py freeze --pilot "$X" --test-only --eta-node $ETA --target-rel $t --out "$R7_DIR/exact_eqeta_$t" > "$E/freeze_exact_eqeta_$t.json" 2>&1 || { cat "$E/freeze_exact_eqeta_$t.json"; fail "exact $t"; }
  for k in fresh exact; do cp "$R7_DIR/${k}_eqeta_$t/design_meta.json" "$E/${k}_eqeta_${t}_design_meta.json"; cp "$R7_DIR/${k}_eqeta_$t/design.json" "$E/${k}_eqeta_${t}_design.json"; done
  FRESH+=("$R7_DIR/fresh_eqeta_$t"); EXACT+=("$R7_DIR/exact_eqeta_$t")
done
echo "== $(date -Is) 2. plan timing"
for k in rates1 default rates2; do
  d=$R7_DIR/plantime_$k; extra=(); [ $k = default ] || extra=(--rates "$PROV/rates.json" --approved-numerics-change "$R7_APPROVAL")
  t0=$(date +%s.%N)
  python3 -B tools/production.py plan "$d" --pilot --points 512 --replicates 2 --test-graphs all --backend gmp --threads 16 --seed "$R7_SEED_PLANCHECK" \
    --bootstrap-chunk 512 --shards 8 "${extra[@]}" > "$E/plantime_$k.txt" 2>&1 || { cat "$E/plantime_$k.txt"; fail "plan $k"; }
  t1=$(date +%s.%N); echo "{\"plan\": \"$k\", \"seconds\": $(python3 -c "print(round($t1-$t0,1))"), \"files\": $(find "$d" -type f | wc -l)}" | tee -a "$E/plan_timing.jsonl"
  cp "$d/manifest.json" "$E/plantime_${k}_manifest.json"; rm -rf "$d"
done
echo "== $(date -Is) 3. comparison with the equal-eta freezes"
python3 -B $SC/r7_compare.py --package . --map "$M" --exact "$X" --map-pilot "$R7_DIR/pilot_map" --exact-pilot "$R7_DIR/pilot_exact" --source "$R7_SOURCE" \
  --rates "$PROV/rates.json" --fresh-bundles "${FRESH[@]}" --exact-bundles "${EXACT[@]}" --out "$E/compare_eqeta.json" > "$E/compare_eqeta.txt" 2>&1 || { cat "$E/compare_eqeta.txt"; fail "compare"; }
grep "^freeze" "$E/compare_eqeta.txt"
echo "finished $(date -Is), status 0"
