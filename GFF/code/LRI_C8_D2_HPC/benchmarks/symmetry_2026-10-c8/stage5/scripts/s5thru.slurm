#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 2 --mem=4G -t 00:30:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-SMK-4 report (A-PERF-3, A-ORC-13 real Slurm) after the throughput drill's lane job has ended: thru_report.py.
# Usage: C8_PACKAGE=... C8_RUN=... LANEJOB=... CM2=... CM1=... RCHAR=... P4A=... P4F=... OUT=... REPORT=<thru_report.py> sbatch --export=ALL -J c8d2-s5thru s5thru.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); campaign $C8_RUN; lane job $LANEJOB"
python3 -B "$REPORT" "$C8_PACKAGE" "$C8_RUN" --job "$LANEJOB" --cost-model "$CM2" --sweep-cost-model "$CM1" --rchar-dir "$RCHAR" \
  --p4-stage4a "$P4A" --p4-final "$P4F" --output "$OUT"; s=$?
echo "finished $(date -Is), status $s"; exit $s
