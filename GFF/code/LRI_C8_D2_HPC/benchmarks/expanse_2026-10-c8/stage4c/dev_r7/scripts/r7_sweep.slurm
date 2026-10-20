#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-s4c-r7-sweep
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4c R7 (A-FLAG-6), the two unpaired sweeps on ONE whole compute node each (site deviation U1; 2 x EPYC 7742 in
# 8 NUMA nodes of 16 cores), exactly the J-SWEEP-1 shape: slurm/sweep.sh -> tools/sweep.py, a test-only plan of all
# 24,173 graphs, both campaigns, 2 replicates x 512 points, --bootstrap-chunk 512 --shards 8 (R13: no cost model), the
# ledger registration (role sweep) before any index, 8 NUMA-pinned slots of 16 threads, heaviest first, merge, the
# measured cost model (every campaign:sector:L:graph key) and the campaign-keyed calibration rows (written to a copy in
# the evidence, never to the export's tools/calibration.json); slurm/sweep.sh then adds the base seed to $C8_SEEDS.
#   R7_ARM=map:   --rates $R7_DIR/prov/rates.json --approved-numerics-change "$R7_APPROVAL" (the provisional map; the
#                 campaign freezes it, its rates identity is the map's sha256)
#   R7_ARM=exact: the default .8/.9 rates (rates identity default), a fresh seed
# tools/accounting.py runs in the analysis job, after this job has ended.
# Usage: C8_PACKAGE=<export> R7_DIR=<work> R7_ARM=map|exact R7_SEED=<fresh> [R7_APPROVAL=<text>] sbatch --export=ALL r7_sweep.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${R7_DIR:?}" "${R7_ARM:?}" "${R7_SEED:?}" "${C8_SEEDS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r7sweep_${R7_ARM}.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=$R7_DIR/sweep_$R7_ARM
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; arm $R7_ARM; campaign $W; seed $R7_SEED; evidence $E"
lscpu | grep -E 'Model name|NUMA node\(s\)'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp | tee "$E/binaries.sha256"
extra=()
case $R7_ARM in
  map) : "${R7_APPROVAL:?}"; test -s "$R7_DIR/prov/rates.json" || { echo "no provisional map in $R7_DIR/prov"; exit 64; }
       sha256sum "$R7_DIR/prov/rates.json" | tee "$E/rates.sha256"
       extra=(--rates "$R7_DIR/prov/rates.json" --approved-numerics-change "$R7_APPROVAL");;
  exact) ;;
  *) echo "R7_ARM must be map or exact"; exit 64;;
esac
cp tools/calibration.json "$E/calibration_before.json"; cp tools/calibration.json "$E/calibration.json"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
t0=$(date +%s); status=0
bash slurm/sweep.sh "$W" --seed "$R7_SEED" --points 512 --replicates 2 --threads 16 --bootstrap-chunk 512 --shards 8 \
  --merge-jobs 32 --forbid-seeds-from "$C8_SEEDS" "${extra[@]}" --cost-model-out "$E/cost_model.json" --calibration "$E/calibration.json" \
  --scratch "$S" > "$E/sweep.stdout" 2>&1 || status=$?
echo "sweep exit $status after $(( $(date +%s) - t0 )) s"; tail -25 "$E/sweep.stdout"
cp "$W/manifest.json" "$E/manifest.json"; cp "$W/submissions.jsonl" "$E/submissions.jsonl"; cp "$C8_SEEDS" "$E/seeds_after.json"
[ "$R7_ARM" = map ] && cp "$W/rates.json" "$E/campaign_rates.json"
python3 -B tools/production.py status "$W" --json > "$E/status.json" 2>&1 || true
echo "finished $(date -Is), status $status"
exit $status
