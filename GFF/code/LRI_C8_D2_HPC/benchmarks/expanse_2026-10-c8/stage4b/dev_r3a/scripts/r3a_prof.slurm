#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-r3a-prof
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# R3a development profile (informative): r3a_prof.py on the first 32 tasks of heavy_free_L8 at 16 threads, baseline
# (Stage-3 c8d2_gmp) and R3a bin/c8d2_gmp under perf record -F 999 -N, P1's symbol report, and the annotation of
# calculate_shared<__float128>. perf.data and staged graphs on node-local scratch.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> R3A_SCRIPT=<path of r3a_prof.py> sbatch --export=ALL r3a_prof.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${R3A_SCRIPT:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r3aprof.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E; perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || L=${TMPDIR:-/tmp}
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE"; s=0
python3 -B "$R3A_SCRIPT" --exe baseline=baseline/c8d2_gmp --exe r3a=bin/c8d2_gmp --output "$E" --scratch "$L" --threads 16 --tasks 32 || s=$?
cp "$R3A_SCRIPT" "$E/"
echo "finished $(date -Is), status $s"; exit $s
