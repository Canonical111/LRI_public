#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:20:00 --no-requeue
#SBATCH -J c8d2-prof2
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# J-PROF-2 = P2 on Expanse (PLAN "Performance plan"; site deviation U1): is the long-double first pass latency-bound?
# (1) tools/perf_profile.py p2: `perf stat -x, -e cycles,instructions,branches,branch-misses,L1-dcache-loads,
# L1-dcache-load-misses,task-clock` of bin/c8d2_gmp (sha256 5c5328af... checked) on the promotion-free fixture blocks
# (free L7: 1,024 tasks, ~27 s; free L8: 256 tasks, ~39 s at 64 threads on socket 0) and, for context, heavy_free_L8
# (~150 s), each also on one thread over ~30 s of its heaviest tasks; OMP_WAIT_POLICY=passive (barrier spinning is not
# counted as work). (2) tools/benchmark.py --interleave-probe (the plan's fallback, run in any case): 2 and 4 points in
# lock-step against kernel.hpp's calculate_products on the 2 heaviest graphs of four blocks, one pinned core each.
# Rule: R6 go if IPC < 1.5 or the probe speedup >= 1.2. Expected wall ~8 min.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL [--dependency=afterok:<build>] expanse_prof2.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=prof2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; perf --version 2>&1; echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)";
  for t in perf numastat; do echo "$t: $(command -v $t || echo missing)"; done; } > "$E/node.txt" 2>&1
grep -E 'Model name|NUMA node\(s\)|perf_event_paranoid|missing' "$E/node.txt"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
sha256sum bin/c8d2_gmp $( [ -e bin/c8d2_interleave_probe ] && echo bin/c8d2_interleave_probe ) | tee "$E/binaries.sha256"
status=0; t0=$(date +%s)
python3 -B tools/perf_profile.py p2 --output "$E/p2" --scratch "$S" --threads 64 --expect-sha256 5c5328af932912bb > "$E/p2.stdout" 2>&1 || status=$?
echo "perf_profile p2 exit $status after $(( $(date +%s) - t0 )) s"; tail -15 "$E/p2.stdout" | cut -c1-300
if [ -x bin/c8d2_interleave_probe ]; then
  s2=0; python3 -B tools/benchmark.py --interleave-probe --output "$E/interleave" --scratch "$S" > "$E/interleave.stdout" 2>&1 || s2=$?
  echo "interleave probe exit $s2"; tail -5 "$E/interleave.stdout" | cut -c1-300; [ $s2 -eq 0 ] || status=$s2
else echo "bin/c8d2_interleave_probe is missing (make probes failed in the build job): probe not run"; fi
echo "finished $(date -Is), status $status"
exit $status
