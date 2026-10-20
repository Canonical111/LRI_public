#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-r4a-node
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b, R4a development on one exclusive compute node (2 x EPYC 7742), in the export built by expanse_r4a_build.slurm:
#  1. speed: r4a_speed.py, Stage-3 baseline (bin/baseline/c8d2_gmp) against R4a (bin/c8d2_gmp) [and C8_R4A_EXTRA
#     variants NAME=DIR], heavy_free_L8 and heavy_power_L8 (256 tasks x 16,384 points each) at 64 threads, 3 repeats,
#     two pinned streams (one per socket) at a time; median integration seconds; rows identical in every run;
#  2. G-L8SELF (A-RPL-7): tests/validate.py --l8self bin/baseline (2,000 L8 kernels, 2 x 512 points, both backends);
#  3. the default validate parts describe, replay (A-RPL-1/2/3 subset: G-REF, G-C7, G-JET) and diagnostics (the
#     tier-timer and ratio-histogram builds write the release rows).
# Expected wall ~20 min. Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL expanse_r4a_node.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r4anode.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; export TMPDIR=$S; echo "node-local scratch $S"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/baseline/* | tee "$E/binaries.sha256"
D=benchmarks/expanse_2026-10-c8/stage4b/dev_r4a
extra=(); for v in ${C8_R4A_EXTRA:-}; do extra+=(--variant "$v"); done
st=0; t0=$(date +%s)
python3 -B "$D/r4a_speed.py" --variant base=bin/baseline --variant r4a=bin "${extra[@]}" --output "$E/speed" --scratch "$S" --threads 64 --repeats 3 > "$E/speed.stdout" 2>&1 || st=$?
echo "speed exit $st after $(( $(date +%s) - t0 )) s"; tail -40 "$E/speed.stdout" | cut -c1-200
s8=0; t0=$(date +%s)
python3 -B tests/validate.py --only none --l8self bin/baseline --jobs 32 --threads 4 --output "$E/l8self.json" > "$E/l8self.stdout" 2>&1 || s8=$?
echo "l8self exit $s8 after $(( $(date +%s) - t0 )) s"; grep -E 'passed|Error|differ' "$E/l8self.stdout" | head -5
sv=0; t0=$(date +%s)
python3 -B tests/validate.py --only describe replay diagnostics --jobs 32 --threads 4 --output "$E/validate_subset.json" > "$E/validate_subset.stdout" 2>&1 || sv=$?
echo "validate subset exit $sv after $(( $(date +%s) - t0 )) s"; grep -E 'passed in|Error' "$E/validate_subset.stdout" | head -8
echo "finished $(date -Is): speed $st, l8self $s8, validate $sv"
[ "$st" = 0 ] && [ "$s8" = 0 ] && [ "$sv" = 0 ]
