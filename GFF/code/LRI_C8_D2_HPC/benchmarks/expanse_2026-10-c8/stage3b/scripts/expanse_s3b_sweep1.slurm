#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 02:00:00 --no-requeue
#SBATCH -J c8d2-sweep1
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# J-SWEEP-1 on Expanse (site deviation U1; one whole compute node, 2 x EPYC 7742 in 8 NUMA nodes of 16 cores):
# slurm/sweep.sh -> tools/sweep.py in bootstrap mode (R13): a test-only plan of all 24,173 graphs, both campaigns,
# 2 replicates x 512 points, --bootstrap-chunk 512 --shards 8, no cost model; the ledger registration (role sweep)
# before any index; 8 NUMA-pinned process slots of 16 threads, heaviest first; merge; the first measured cost model
# (every campaign:sector:L:graph key, R05) and the campaign-keyed calibration rows (written to a copy, never to the
# export's tools/calibration.json); the base seed added to $C8_SEEDS. tools/accounting.py runs after this job.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> SWEEP_SEED=<fresh> sbatch --export=ALL --dependency=afterok:<build job> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${SWEEP_SEED:?}" "${C8_SEEDS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=sweep1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
W=$C8_DATA/sweep1-$TAG
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; campaign $W; evidence $E"
lscpu | grep -E 'Model name|NUMA node\(s\)'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE"
sha256sum bin/c8d2_gmp | tee "$E/binaries.sha256"
cp tools/calibration.json "$E/calibration_before.json"; cp tools/calibration.json "$E/calibration.json"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
t0=$(date +%s); status=0
bash slurm/sweep.sh "$W" --seed "$SWEEP_SEED" --points 512 --replicates 2 --threads 16 --bootstrap-chunk 512 --shards 8 \
  --merge-jobs 32 --cost-model-out "$E/cost_model.json" --calibration "$E/calibration.json" --scratch "$S" \
  > "$E/sweep.stdout" 2>&1 || status=$?
echo "sweep exit $status after $(( $(date +%s) - t0 )) s"; tail -25 "$E/sweep.stdout"
cp "$W/manifest.json" "$E/manifest.json"; cp "$W/submissions.jsonl" "$E/submissions.jsonl"
python3 -B tools/production.py status "$W" --json > "$E/status.json" 2>&1 || true
echo "finished $(date -Is), status $status"
exit $status
