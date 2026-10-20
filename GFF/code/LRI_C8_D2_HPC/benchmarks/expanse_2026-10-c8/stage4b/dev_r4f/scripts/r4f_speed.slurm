#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-r4f-speed
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R4f (development probe): speed of bin/c8d2_gmp linked against the Spack GMP (the baseline in $C8_PACKAGE/bin,
# byte-identical to Stage 3), the fat GMP and the host-tuned GMP ($C8_DATA/work/<sha12>/r4f-{fat,host}/bin), all
# GMP 6.2.1 and the same worker source, on one exclusive compute node: r4f_bench.py speed, heavy_free_L8 on socket 0
# and heavy_power_L8 on socket 1 (64 threads each, NUMA-aligned), 3 repeats with the executable order rotated per
# repeat, medians and speedups; every run of a block must give the same rows (all scientific fields). No run starts
# that would end after 27 min (the record then shows it as skipped). Expected wall about 23 min.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL [--dependency=afterok:...] r4f_speed.slurm
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r4fspeed.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
P=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/scripts; WD=$C8_DATA/work/$TAG
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || L=${TMPDIR:-/tmp}; echo "node-local scratch $L"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
cd "$C8_PACKAGE"
sha256sum bin/c8d2_gmp "$WD/r4f-fat/bin/c8d2_gmp" "$WD/r4f-host/bin/c8d2_gmp" | tee "$E/binaries.sha256"
{ echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; for x in bin/c8d2_gmp "$WD/r4f-fat/bin/c8d2_gmp" "$WD/r4f-host/bin/c8d2_gmp"; do echo "# $x"; ldd "$x" | grep libgmp; done; } | tee "$E/ldd.txt"
status=0
python3 -B "$P/r4f_bench.py" speed --package "$C8_PACKAGE" --threads 64 --repeats 3 --deadline 1620 --scratch "$L" --output "$E/speed" \
  --exe "baseline=$C8_PACKAGE/bin/c8d2_gmp" --exe "fat=$WD/r4f-fat/bin/c8d2_gmp" --exe "host=$WD/r4f-host/bin/c8d2_gmp" > "$E/speed.stdout" 2>&1 || status=$?
tail -12 "$E/speed.stdout" | cut -c1-300
echo "finished $(date -Is), status $status"
exit $status
