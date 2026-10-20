#!/bin/bash
#SBATCH -p <PARTITION>
#SBATCH -A <ACCOUNT>
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 1-00:00:00
#SBATCH -J c7d2-node
# Whole-node worker of the 2026 C7(2) production (written by Claude Code session C62d; paths replaced by variables).
# Lanes claim job indices from RUN/lanes/queue.txt (heaviest first, estimated seconds for a 64-thread lane) with an atomic
# mkdir in RUN/claims and run the package's `production.py run`. AMD node: one lane on all physical cores. Intel node:
# one lane per socket (numactl bind). A lane never starts an index whose scaled estimate (x1.5 + 10 min) exceeds the job's
# remaining time. A failed or timed-out index keeps its claim directory: remove RUN/claims/<idx> and submit another worker.
# The 2026 run used 28 such jobs (14 nodes with 2x32-core AMD EPYC 7532/7543, 14 with 2x20-core Intel), 6.4-6.6 h each.
# Requires C7_RUN, C7_PACKAGE, C7_ENV_SETUP (exported at submission: sbatch --export=ALL node.slurm).
set -eo pipefail
source "$C7_ENV_SETUP"
set -u
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 OMP_PROC_BIND=close OMP_PLACES=cores
RUN=$C7_RUN; Q=$RUN/lanes/queue.txt; C=$RUN/claims; mkdir -p "$C" "$RUN/lanes/logs"
START=$(date +%s); LIMIT=$(squeue -h -j $SLURM_JOB_ID -o %L | awk -F'[-:]' '{if(NF==4)print $1*86400+$2*3600+$3*60+$4; else if(NF==3)print $1*3600+$2*60+$3; else print $1*60+$2}')
PHYS=$(lscpu -p=SOCKET,CORE | grep -v '^#' | sort -u | wc -l); SOCK=$(lscpu -p=SOCKET | grep -v '^#' | sort -u | wc -l)
echo "node $(hostname) job $SLURM_JOB_ID start $(date -Is) limit_s $LIMIT phys_cores $PHYS sockets $SOCK $(grep -m1 'model name' /proc/cpuinfo)"
cd "$C7_PACKAGE"
lane() {
  local k=$1 threads=$2 scale=$3; shift 3; local idx est left n=0 need
  mkdir -p "${TMPDIR:-/tmp}/c7lane_${SLURM_JOB_ID}_$k"
  while read -r idx est; do
    [[ -e "$C/$idx" ]] && continue
    need=$(( est*scale/100*3/2 + 600 )); left=$(( START + LIMIT - $(date +%s) ))
    (( left > need )) || continue
    mkdir "$C/$idx" 2>/dev/null || continue
    echo "$SLURM_JOB_ID lane$k $(hostname) threads=$threads $(date -Is)" > "$C/$idx/owner"
    if OMP_NUM_THREADS=$threads "$@" python3 -B tools/production.py run "$RUN" --index "$idx" --threads "$threads" --scratch "${TMPDIR:-/tmp}/c7lane_${SLURM_JOB_ID}_$k" > "$RUN/lanes/logs/idx$idx.$SLURM_JOB_ID.log" 2>&1
    then touch "$C/$idx/done"; n=$((n+1)); else echo "rc=$?" > "$C/$idx/failed"; echo "lane$k index $idx FAILED"; fi
  done < "$Q"
  rm -rf "${TMPDIR:-/tmp}/c7lane_${SLURM_JOB_ID}_$k"; echo "lane$k finished $n indices $(date -Is)"
}
if grep -q AMD /proc/cpuinfo; then
  lane 0 "$PHYS" $(( 6400 / PHYS * 110 / 100 )) &
else
  per=$(( PHYS / SOCK )); for s in $(seq 0 $((SOCK-1))); do lane $s $per $(( 6400 / per * 130 / 100 )) numactl --cpunodebind=$s --membind=$s & done
fi
wait; echo "node done $(date -Is)"
