#!/bin/bash
#SBATCH -A yun124
#SBATCH -p shared
#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH -t 04:00:00
#SBATCH -J ht3d-setup
#SBATCH -o /expanse/lustre/scratch/%u/temp_project/ht3d/logs/%x_%j.out
# Large-cutoff setup probe (scripts/probe_large_setup.py: graph/projector/vertices with
# per-stage RSS and SVD retry/block logging; no eigensolve). Override -c/--mem/-t on the
# sbatch command line. Submit with the bindings in the environment, e.g.
#   HT3D_RELEASE_TAR=<tar> HT3D_RELEASE_TAR_SHA256=<sha> \
#   HT3D_SETUP_ARGS="--L 18 --x 0.6 --spins 0 --execute --stop-after vertices --max-bath-states 50000000 --memory-limit-gib 40" \
#   sbatch --export=ALL --mem=48G setup_probe.sbatch
# Output: $HT3D_DATA/probe/<job>/setup.json (+ setup.json.projector.jsonl, projector_log.jsonl, dumps/)
set -o pipefail
: "${HT3D_RELEASE_TAR:?}" "${HT3D_RELEASE_TAR_SHA256:?}" "${HT3D_SETUP_ARGS:?}"
echo "ht3d setup probe job $SLURM_JOB_ID on $(hostname) cpus=$SLURM_CPUS_PER_TASK start $(date -Is) args: $HT3D_SETUP_ARGS"
[ "$(sha256sum "$HT3D_RELEASE_TAR" | cut -d' ' -f1)" = "$HT3D_RELEASE_TAR_SHA256" ] || { echo "release tarball checksum mismatch" >&2; exit 74; }
_tmp=/scratch/$USER/job_$SLURM_JOB_ID/boot; mkdir -p "$_tmp" || exit 74
tar -xf "$HT3D_RELEASE_TAR" -C "$_tmp" cluster/expanse/stage.sh || exit 74
source "$_tmp/cluster/expanse/stage.sh" || exit 74
source "$HT3D_STAGED/cluster/expanse/env.sh" || exit 70
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
OUT=$HT3D_DATA/probe/$SLURM_JOB_ID; mkdir -p "$OUT/dumps" || exit 70
export HT3D_PROJECTOR_LOG=$OUT/projector_log.jsonl HT3D_PROJECTOR_DUMP_DIR=$OUT/dumps
# shellcheck disable=SC2086
python "$HT3D_STAGED/scripts/probe_large_setup.py" $HT3D_SETUP_ARGS --threads "$NUMBA_NUM_THREADS" \
       --dump-dir "$OUT/dumps" --output "$OUT/setup.json"
rc=$?; echo "ht3d setup probe exit $rc at $(date -Is)"; exit $rc
