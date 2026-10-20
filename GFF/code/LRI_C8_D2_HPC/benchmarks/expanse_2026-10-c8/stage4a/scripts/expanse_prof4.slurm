#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:50:00 --no-requeue
#SBATCH -J c8d2-prof4
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# J-PROF-4 = P4 on Expanse (PLAN "Performance plan"; site deviation U1): the lane shape. tools/benchmark.py
# --lane-shapes 1x128,2x64,4x32,8x16,16x8 on the fixed L8 workload p4_L8 of benchmarks/fixtures8 (1,582 free + 427 power
# L8 graphs drawn uniformly, 2 replicates x 16,384 points: 42,254 cost-model seconds, ~330 s of ideal node time at 128
# cores). Per shape: N lane processes pinned to disjoint NUMA-aligned core sets, production-style blocks of
# max(16 x T, 256) tasks, graph members staged per block from the packs on Lustre, bin/c8d2_gmp (5c5328af..., checked)
# at T threads; throughput in cost-model seconds per node-second, busy fraction, OpenMP efficiency, staging + load
# share (PACK_FORMAT decision), per-lane wall, RSS and NUMA placement, numastat; rows must agree across shapes.
# Expected wall ~32-36 min (5 shapes x ~6-6.5 min).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL [--dependency=afterok:<build>] expanse_prof4.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=prof4.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; command -v numastat || echo "numastat: missing (sysfs counters are read directly)"; } > "$E/node.txt" 2>&1
grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
sha256sum bin/c8d2_gmp | tee "$E/binaries.sha256"
status=0; t0=$(date +%s)
python3 -B tools/benchmark.py --lane-shapes "${C8_P4_SHAPES:-1x128,2x64,4x32,8x16,16x8}" --workload p4_L8 --fraction "${C8_P4_FRACTION:-1}" \
  --output "$E/p4" --scratch "$S" --expect-sha256 5c5328af932912bb > "$E/p4.stdout" 2>&1 || status=$?
echo "benchmark --lane-shapes exit $status after $(( $(date +%s) - t0 )) s"; tail -15 "$E/p4.stdout" | cut -c1-300
echo "finished $(date -Is), status $status"
exit $status
