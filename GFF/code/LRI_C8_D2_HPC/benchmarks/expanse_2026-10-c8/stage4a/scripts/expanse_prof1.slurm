#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:35:00 --no-requeue
#SBATCH -J c8d2-prof1
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# J-PROF-1 = P1 on Expanse (PLAN "Performance plan"; site deviation U1): time per function and the tier split on the
# Stage-3 baseline. tools/perf_profile.py p1 on the four heavy fixture blocks (free/power L7: 1,024 tasks, ~50 s each;
# free/power L8: 256 tasks, ~130-150 s each, at 64 threads): `perf record -F 999 -N` of bin/c8d2_gmp (sha256 checked:
# 5c5328af...) pinned to socket 0 (NUMA nodes 0-3, 64 threads), and at the same time bin/c8d2_gmp_prof (tier timers) on
# socket 1; then `perf report --no-children --sort symbol` (+ dso,symbol and dso) parsed into the plan's shares and a
# top-40 table, and source lines through a -g twin of the worker (used only if its allocated sections equal the
# baseline's). perf.data and the staged graphs stay on node-local /scratch; only reports and JSON come back.
# Without perf: tier timers and ltrace -c on one thread (recorded as the fallback). Expected wall ~15 min.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL [--dependency=afterok:<build>] expanse_prof1.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=prof1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; perf --version 2>&1; echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)";
  echo "kptr_restrict $(cat /proc/sys/kernel/kptr_restrict)"; for t in perf ltrace readelf objcopy addr2line numastat; do echo "$t: $(command -v $t || echo missing)"; done; } > "$E/node.txt" 2>&1
grep -E 'Model name|NUMA node\(s\)|perf_event_paranoid|missing' "$E/node.txt"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
sha256sum bin/c8d2_gmp bin/c8d2_gmp_prof | tee "$E/binaries.sha256"
status=0; t0=$(date +%s)
python3 -B tools/perf_profile.py p1 --output "$E/p1" --scratch "$S" --threads 64 --expect-sha256 5c5328af932912bb > "$E/p1.stdout" 2>&1 || status=$?
echo "perf_profile p1 exit $status after $(( $(date +%s) - t0 )) s"; tail -30 "$E/p1.stdout" | cut -c1-300
echo "finished $(date -Is), status $status"
exit $status
