#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 2 --mem=4G -t 00:30:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check part B (2026-10-07): nested-N analysis of the fresh runs (tc_nested_analyze.py) and the sha256 of every
# native output. Reads the nested run; writes only this job's evidence folder. Usage: sbatch -J c8d2-tcnan --export=ALL tc_nested_analyze.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck-ba68f401e46e
RUN=/mnt/beegfs/zzheng1/c8-d2/tailcheck-nested-20261007-ba68f401e46e
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tcnested.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); evidence $E"
sha256sum "$WK/tc_nested_analyze.py" "$WK/tc_nested_analyze.slurm" "$WK/tc_nested_classes.txt" "$RUN/setup.json" "$RUN"/net_*.bin | tee "$E/inputs.sha256"
(cd "$RUN" && sha256sum out/*.json) > "$E/native_outputs.sha256"; wc -l "$E/native_outputs.sha256"
cp "$RUN/setup.json" "$RUN/calls.jsonl" "$E/"
t=$(date +%s); python3 -B "$WK/tc_nested_analyze.py" "$RUN" "$WK/tc_nested_classes.txt" "$E/nested.json" > "$E/stdout.txt" 2>&1
echo "exit $? after $(( $(date +%s) - t )) s" | tee "$E/exit.txt"; grep CLASS "$E/stdout.txt"
