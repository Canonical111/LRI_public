#!/bin/bash
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
#SBATCH --mem=180G
#SBATCH --time=24:00:00
#SBATCH --signal=B:USR1@1800
#SBATCH --output=<SCRATCH>/lri_c8/logs/%x_%A_%a.out
# One campaign lane (array task) per exclusive defq node, one solver process at a time:
# its threads run on the first hardware thread of each physical core and its memory is
# interleaved over both sockets. exec keeps the batch shell's pid, so Slurm's B:USR1
# warning reaches run_lane.py, which forwards it to the solver (stop at the next scalar
# boundary, exit 75, resume on resubmission). Submit with: slurm/submit_defq.sh lanes ...
set -euo pipefail
: "${C8_ROOT:?}" "${C8_DATA:?}" "${CAMPAIGN:?}" "${C8_OUTPUT:?}"
export C8_CACHE_ROLE=node
source "$C8_ROOT/slurm/symmetry_env.sh"
[[ $- == *e* ]] || { echo "[lane] errexit lost" >&2; exit 70; }
[[ -d $NUMBA_CACHE_DIR ]] || echo "[lane] WARNING: $NUMBA_CACHE_DIR missing (validation not run for this source?); compiling cold"
PHYS=$(c8_phys_cpus); NPHYS=$(c8_count "$PHYS")
export C8_BINDING="numactl --physcpubind=$PHYS --interleave=all"
echo "[lane] job ${SLURM_JOB_ID} array ${SLURM_ARRAY_JOB_ID:-}_${SLURM_ARRAY_TASK_ID} on $(hostname) $(date '+%Y-%m-%dT%H:%M:%S%z'); $NPHYS physical cores"
exec numactl --physcpubind="$PHYS" --interleave=all python "$C8_ROOT/scripts/run_lane.py" \
  --manifest "$CAMPAIGN" --lane "$SLURM_ARRAY_TASK_ID" --output-dir "$C8_OUTPUT"
