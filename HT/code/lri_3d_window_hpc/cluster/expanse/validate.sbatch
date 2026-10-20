#!/bin/bash
#SBATCH -A yun124
#SBATCH -p shared
#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 02:00:00
#SBATCH -J ht3d-validate
#SBATCH -o /expanse/lustre/scratch/%u/temp_project/ht3d/logs/%x_%j.out
# Submit:  HT3D_RELEASE_TAR=<tar> HT3D_RELEASE_TAR_SHA256=<sha> sbatch --export=ALL validate.sbatch
# Writes $HT3D_DATA/validation/$SLURM_JOB_ID/receipt.json. No `set -u` (site init).
set -o pipefail
: "${HT3D_RELEASE_TAR:?}" "${HT3D_RELEASE_TAR_SHA256:?}"
echo "ht3d validate job $SLURM_JOB_ID on $(hostname) start $(date -Is)"
[ "$(sha256sum "$HT3D_RELEASE_TAR" | cut -d' ' -f1)" = "$HT3D_RELEASE_TAR_SHA256" ] || { echo "release tarball checksum mismatch" >&2; exit 74; }
_tmp=/scratch/$USER/job_$SLURM_JOB_ID/boot; mkdir -p "$_tmp" || exit 74
tar -xf "$HT3D_RELEASE_TAR" -C "$_tmp" cluster/expanse/stage.sh || exit 74
source "$_tmp/cluster/expanse/stage.sh" || exit 74
source "$HT3D_STAGED/cluster/expanse/env.sh" || exit 70
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
python "$HT3D_STAGED/cluster/expanse/receipt.py" --work "/scratch/$USER/job_$SLURM_JOB_ID/work" \
       --out "$HT3D_DATA/validation/$SLURM_JOB_ID"
rc=$?
echo "ht3d validate exit $rc at $(date -Is)"
exit $rc
