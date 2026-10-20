#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s4c-mp256-speed
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4c R4b (mp256), development: mp256_speed.py on one exclusive node: bin/c8d2_gmp (exact) against
# bin/c8d2_gmp_mp256 on heavy_free_L8 (socket 0) and heavy_power_L8 (socket 1) at 64 pinned threads, 3 rounds of
# both, medians; rows compared; then both tier-timer variants (compiled in the job) for the per-call tier times.
# Expected wall ~15 min (worst case 128 x 0.5 = 64 SU).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL [--dependency=afterok:<build>] mp256_speed.slurm
#        (dev_mp256/scripts/submit_mp256.sh speed does this after the H7E-R admission and the agent share)
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=mp256speed.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
status=0
python3 -B benchmarks/expanse_2026-10-c8/stage4c/dev_mp256/scripts/mp256_speed.py --output "$E" --scratch "$S" --threads 64 --repeats 3 \
  --budget-seconds 1300 || status=$?
sha256sum "$HOME/c8d2/env_expanse.sh" > "$E/env_expanse.sha256"; sha256sum bin/c8d2_gmp bin/c8d2_gmp_mp256 > "$E/binaries.sha256"
echo "finished $(date -Is), status $status"; exit $status
