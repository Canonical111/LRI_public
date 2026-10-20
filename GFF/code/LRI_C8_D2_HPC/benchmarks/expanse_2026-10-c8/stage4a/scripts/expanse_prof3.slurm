#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:25:00 --no-requeue
#SBATCH -J c8d2-prof3
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# J-PROF-3 = P3 on Expanse (PLAN "Performance plan"; site deviation U1): margin distributions at the precision tests.
# tools/perf_profile.py p3 with bin/c8d2_gmp_ratiohist (make ratiohist, -DC8_RATIO_HISTOGRAM; its rows equal the release
# worker's) at 128 threads on the uniform-draw blocks random_{free,power}_L{7,8} (256 graphs x 2 replicates, ~30-55 s
# each) and the heavy L8 blocks, at rates .8 (campaign a) and .9 (campaign b): log10(|v|/err) histograms at the 1e-9
# test, at the 1e-23 test (every binary128 evaluation) and of the MP evaluations per (sector, L, rate), the consistency
# checks against the row counters, and the fractions below 10^-k (C8_DD_RATIO for R3b, C8_MP256_RATIO for R4b,
# expected escalations). Expected wall ~11 min.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL [--dependency=afterok:<build>] expanse_prof3.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=prof3.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1
grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
sha256sum bin/c8d2_gmp bin/c8d2_gmp_ratiohist | tee "$E/binaries.sha256"
status=0; t0=$(date +%s)
python3 -B tools/perf_profile.py p3 --output "$E/p3" --scratch "$S" --threads 128 --rates .8,.9 \
  --blocks random_free_L7,random_power_L7,random_free_L8,random_power_L8,heavy_free_L8,heavy_power_L8 > "$E/p3.stdout" 2>&1 || status=$?
echo "perf_profile p3 exit $status after $(( $(date +%s) - t0 )) s"; tail -15 "$E/p3.stdout" | cut -c1-300
echo "finished $(date -Is), status $status"
exit $status
