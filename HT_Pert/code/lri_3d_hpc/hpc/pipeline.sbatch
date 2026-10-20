#!/usr/bin/env bash
# Generic example. On Expanse and symmetry use cluster/submit.py (cluster/RUNBOOK.md).
#SBATCH --job-name=ht3d-vertices
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=ht3d-vertices-%A_%a.log
set -euo pipefail
: "${HT3D_ROOT:?Set the package directory}"
: "${HT3D_INPUTS:?Set the new prepared-input directory}"
: "${HT3D_STAGE:?Choose prepare, images, matrix or finalize}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-${SLURM_TMPDIR:-$HT3D_ROOT/work}/ht3d-numba}"
case "$HT3D_STAGE" in
  prepare)
    : "${HT3D_CUTOFF:?Set the cutoff}"
    python "$HT3D_ROOT/code/taylor_pipeline.py" prepare \
      --path "$HT3D_INPUTS" --cutoff "$HT3D_CUTOFF" --degree "$((${HT3D_ORDER:-8}-2))" \
      --max-states "${HT3D_MAX_STATES:-2000000}" --max-bytes "${HT3D_MAX_BYTES:-2147483648}"
    ;;
  images|matrix)
    python "$HT3D_ROOT/hpc/pipeline_task.py" "$HT3D_STAGE" --path "$HT3D_INPUTS"
    ;;
  finalize)
    : "${HT3D_STORE:?Set the new final vertex directory}"
    python "$HT3D_ROOT/code/taylor_pipeline.py" finalize --path "$HT3D_INPUTS" --output "$HT3D_STORE"
    ;;
  *)
    echo "Unknown HT3D_STAGE: $HT3D_STAGE" >&2
    exit 2
    ;;
esac
