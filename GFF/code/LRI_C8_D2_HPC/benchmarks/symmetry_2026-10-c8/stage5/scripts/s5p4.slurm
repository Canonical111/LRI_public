#!/bin/bash
#SBATCH -p amdq,amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 00:40:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# A-PERF-3 reference for J-SMK-4: the best P4 lane shape (8x8 on symmetry, Stage 4a job 569788 on the Stage-3 binary)
# rerun with the FINAL default binary (export 5d7586e9f1ab, bin/c8d2_gmp of s5build) on the same P4 workload
# (tools/benchmark.py --lane-shapes 8x8 --workload p4_L8 --fraction 0.5), on the node of the J-SMK-4 lane job when
# possible (-w), so that the drill's node throughput is compared with the same binary on the same CPU model.
# Usage: C8_PACKAGE=... sbatch --export=ALL [-w NODE] -J c8d2-s5p4 s5p4.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5p4.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
S=/tmp/c8d2_p4_$SLURM_JOB_ID; mkdir -p "$S"; export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp | tee "$E/binaries.sha256"
python3 -B tools/prepare_benchmarks.py --order 8 > "$E/fixtures_verify.json" 2>&1 || { echo "fixtures do not verify"; exit 65; }
t0=$(date +%s); status=0
python3 -B tools/benchmark.py --lane-shapes 8x8 --workload p4_L8 --fraction 0.5 --output "$E/p4" --scratch "$S" > "$E/p4.stdout" 2>&1 || status=$?
echo "benchmark exit $status after $(( $(date +%s) - t0 )) s"; tail -4 "$E/p4.stdout" | cut -c1-300
rm -rf "$S"
echo "finished $(date -Is), status $status"
exit $status
