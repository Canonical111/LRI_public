#!/bin/bash
#SBATCH -p amdq,amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 00:45:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# A-PERF-5 on symmetry, owed item (per (sector, L), L3-L7 included): on ONE AMD node, the same test-only subset sweep
# (J-SWEEP-3's arguments: --pilot --points 512 --replicates 2 --test-graphs 168 --test-selection stratified --backend gmp
# --threads 8 --cost-model <J-SWEEP-1's model> --seed <J-SWEEP-2's seed>) planned, run on 8 x 8 NUMA-pinned slots
# (s5sweep3_driver.py: the package's own sweep runner) and merged twice:
#   final     with the final export (5d7586e9f1ab; bin/c8d2_gmp of s5build, GCC 11.4);
#   baseline  with the Stage-3 export (tag c8-stage3 = b4273c59e911; its bin/c8d2_gmp built by s5build, 23624153...),
#             its own tools; the two L8 packs hard-linked after a re-hash against its inputs/manifest.json;
# then each package's make_cost_model.py, and perf5_compare.py: the speedup per (campaign, sector, L).
# Usage: C8_PACKAGE=<final export> C8_BASELINE_PKG=<stage-3 export> C8_L8_PACKS=... SWEEP_SEED=... DRIVER=... CMP=<perf5_compare.py>
#        sbatch --export=ALL -J c8d2-s5perf5 s5perf5.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_BASELINE_PKG:?}" "${C8_L8_PACKS:?}" "${SWEEP_SEED:?}" "${DRIVER:?}" "${CMP:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5perf5.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
CM1=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); final $C8_PACKAGE; baseline $C8_BASELINE_PKG; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS C8_LANES
S=/tmp/c8d2_$SLURM_JOB_ID; mkdir -p "$S"; status=0
sha256sum "$C8_PACKAGE/bin/c8d2_gmp" "$C8_BASELINE_PKG/bin/c8d2_gmp" "$CM1" | tee "$E/binaries.sha256"
cd "$C8_BASELINE_PKG" || exit 64
for s in free power; do
  if [ ! -e inputs/packs/${s}_L8.pack ]; then
    want=$(python3 -c "import json;print(json.load(open('inputs/manifest.json'))['sha256']['packs/${s}_L8.pack'])"); have=$(sha256sum "$C8_L8_PACKS/${s}_L8.pack" | cut -c1-64)
    [ "$want" = "$have" ] || { echo "baseline export pins another ${s}_L8.pack ($want != $have)"; exit 3; }; ln "$C8_L8_PACKS/${s}_L8.pack" inputs/packs/${s}_L8.pack || exit 3
  fi
done
for which in final baseline; do
  P=$C8_PACKAGE; [ $which = baseline ] && P=$C8_BASELINE_PKG
  W=<SCRATCH>/c8-d2/perf5-$which-$TAG; t0=$(date +%s)
  ( cd "$P" && python3 -B tools/production.py plan "$W" --pilot --points 512 --replicates 2 --test-graphs 168 --test-selection stratified --backend gmp \
      --threads 8 --seed "$SWEEP_SEED" --cost-model "$CM1" > "$E/plan_$which.stdout" 2>&1 ) || { echo "$which plan failed"; tail -5 "$E/plan_$which.stdout"; status=3; continue; }
  ( cd "$P" && python3 -B tools/ledger.py register "$W" --role sweep ) | tee "$E/ledger_$which.txt"
  ( cd "$P" && python3 -B "$DRIVER" "$P" "$W" --threads 8 --scratch "$S" --merge-jobs 32 > "$E/driver_$which.stdout" 2>&1 ) || { echo "$which runner failed"; tail -5 "$E/driver_$which.stdout"; status=3; continue; }
  ( cd "$P" && python3 -B tools/make_cost_model.py "$W" "$E/cost_model_$which.json" --note "A-PERF-5 $which subset, job $SLURM_JOB_ID" ) || status=3
  echo "$which: plan + run + merge + model in $(( $(date +%s) - t0 )) s"; grep -E "process slots" "$E/driver_$which.stdout" | head -1
done
[ $status -eq 0 ] && { python3 -B "$CMP" "$E/cost_model_baseline.json" "$E/cost_model_final.json" "$E/perf5.json" || status=3; }
rm -rf "$S"
echo "finished $(date -Is), status $status"
exit $status
