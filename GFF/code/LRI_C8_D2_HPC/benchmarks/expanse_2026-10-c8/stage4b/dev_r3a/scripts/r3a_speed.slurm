#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-r3a-speed
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R3a, development: r3a_speed.py on one exclusive node: baseline (Stage-3 c8d2_gmp 5c5328af...) against the
# R3a bin/c8d2_gmp on heavy_free_L8 (socket 0) and heavy_power_L8 (socket 1) at 64 pinned threads, 3 repeats each,
# medians, rows compared; then perf stat IPC (cycles, instructions; OMP_WAIT_POLICY=passive as P2) of both on
# heavy_free_L8; then, within the budget, the R3a tier timers (bin/c8d2_gmp_prof). Expected wall ~20 min.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --dependency=afterok:<build> r3a_speed.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r3aspeed.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; perf --version 2>&1; echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"; } > "$C8_DATA/work/node_$SLURM_JOB_ID.txt" 2>&1
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
status=0
python3 -B benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/scripts/r3a_speed.py --baseline baseline/c8d2_gmp --candidate bin/c8d2_gmp \
  --prof bin/c8d2_gmp_prof --output "$E" --scratch "$S" --threads 64 --repeats 3 --budget-seconds 1200 || status=$?
mv "$C8_DATA/work/node_$SLURM_JOB_ID.txt" "$E/node.txt"; sha256sum "$HOME/c8d2/env_expanse.sh" > "$E/env_expanse.sha256"
echo "finished $(date -Is), status $status"; exit $status
