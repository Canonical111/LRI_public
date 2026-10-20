#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s4c-mp256-prof
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4c R4b (mp256), development profile (informative, not a gate): where the time of the 77-digit tier goes.
# Stage 4b's r3a_prof.py (in the export) on the first 32 tasks of heavy_free_L8 and of heavy_power_L8 at 16 threads,
# bin/c8d2_gmp (exact) and bin/c8d2_gmp_mp256 under `perf record -F 999 -N`, P1's symbol report and shares; rows
# compared. perf.data and the staged graphs on node-local scratch. Worst case 16 x 0.5 = 8 SU.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL mp256_prof.slurm (submit_mp256.sh prof, from a copy of
# this script in $C8_DATA/work when the export predates it; its sha256 is recorded in the evidence)
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=mp256prof.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E; perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || L=${TMPDIR:-/tmp}
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
sha256sum "$0" > "$E/job_script.sha256" 2>/dev/null; sha256sum "$HOME/c8d2/env_expanse.sh" > "$E/env_expanse.sha256"
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp bin/c8d2_gmp_mp256 > "$E/binaries.sha256"
s=0
for b in heavy_free_L8 heavy_power_L8; do
  python3 -B benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/scripts/r3a_prof.py --exe exact=bin/c8d2_gmp --exe mp256=bin/c8d2_gmp_mp256 \
    --block "$b" --output "$E/$b" --scratch "$L" --threads 16 --tasks 32 || s=$?
done
echo "finished $(date -Is), status $s"; exit $s
