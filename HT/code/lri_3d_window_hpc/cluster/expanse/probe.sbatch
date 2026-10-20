#!/bin/bash
#SBATCH -A yun124
#SBATCH -p shared
#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=1
#SBATCH --mem=128G
#SBATCH -t 02:00:00
#SBATCH -J ht3d-probe
#SBATCH -o /expanse/lustre/scratch/%u/temp_project/ht3d/logs/%x_%j.out
# Submit:  HT3D_RELEASE_TAR=<tar> HT3D_RELEASE_TAR_SHA256=<sha> HT3D_PROBE_L="14 16 18" sbatch --export=ALL probe.sbatch
set -o pipefail
: "${HT3D_RELEASE_TAR:?}" "${HT3D_RELEASE_TAR_SHA256:?}"
echo "ht3d probe job $SLURM_JOB_ID on $(hostname) start $(date -Is) L=${HT3D_PROBE_L:-14 16 18}"
[ "$(sha256sum "$HT3D_RELEASE_TAR" | cut -d' ' -f1)" = "$HT3D_RELEASE_TAR_SHA256" ] || { echo "release tarball checksum mismatch" >&2; exit 74; }
_tmp=/scratch/$USER/job_$SLURM_JOB_ID/boot; mkdir -p "$_tmp" || exit 74
tar -xf "$HT3D_RELEASE_TAR" -C "$_tmp" cluster/expanse/stage.sh || exit 74
source "$_tmp/cluster/expanse/stage.sh" || exit 74
source "$HT3D_STAGED/cluster/expanse/env.sh" || exit 70
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
# shellcheck disable=SC2086
python "$HT3D_STAGED/cluster/expanse/probe.py" --L ${HT3D_PROBE_L:-14 16 18} --x "${HT3D_PROBE_X:-0.6}" \
       --threads "$NUMBA_NUM_THREADS" --max-bath-states "${HT3D_PROBE_MAX_STATES:-200000000}" \
       --max-basis-gib "${HT3D_PROBE_MAX_GIB:-120}" --out "$HT3D_DATA/probe/$SLURM_JOB_ID"
rc=$?; echo "ht3d probe exit $rc at $(date -Is)"; exit $rc
