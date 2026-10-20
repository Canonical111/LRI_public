#!/usr/bin/env bash
# Generic example. On Expanse and symmetry use cluster/submit.py (cluster/RUNBOOK.md).
# Submit the four construction stages with explicit scheduler dependencies.
# Resource options can be changed in pipeline.sbatch for the target cutoff.
set -euo pipefail
: "${HT3D_ROOT:?Set the package directory}"
: "${HT3D_INPUTS:?Set a new prepared-input directory}"
: "${HT3D_STORE:?Set a new final vertex directory}"
: "${HT3D_CUTOFF:?Set the even bath cutoff}"
HT3D_ORDER="${HT3D_ORDER:-8}"
export HT3D_ORDER
HT3D_SCRIPT="$HT3D_ROOT/hpc/pipeline.sbatch"
HT3D_PREP_JOB=$(sbatch --parsable --export=ALL,HT3D_STAGE=prepare "$HT3D_SCRIPT")
HT3D_PREP_JOB="${HT3D_PREP_JOB%%;*}"
HT3D_IMAGE_JOB=$(sbatch --parsable --dependency="afterok:$HT3D_PREP_JOB" \
  --array="0-$HT3D_CUTOFF" --export=ALL,HT3D_STAGE=images "$HT3D_SCRIPT")
HT3D_IMAGE_JOB="${HT3D_IMAGE_JOB%%;*}"
HT3D_MATRIX_JOB=$(sbatch --parsable --dependency="afterok:$HT3D_IMAGE_JOB" \
  --array="0-$((4*(HT3D_ORDER-1)-1))" --export=ALL,HT3D_STAGE=matrix "$HT3D_SCRIPT")
HT3D_MATRIX_JOB="${HT3D_MATRIX_JOB%%;*}"
HT3D_FINISH_JOB=$(sbatch --parsable --dependency="afterok:$HT3D_MATRIX_JOB" \
  --export=ALL,HT3D_STAGE=finalize "$HT3D_SCRIPT")
printf 'Preparation %s\nImages %s\nMatrices %s\nFinalization %s\n' \
  "$HT3D_PREP_JOB" "$HT3D_IMAGE_JOB" "$HT3D_MATRIX_JOB" "$HT3D_FINISH_JOB"
