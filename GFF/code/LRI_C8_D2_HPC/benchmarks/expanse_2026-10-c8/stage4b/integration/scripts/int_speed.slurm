#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-int-speed
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b integration, the A-PERF-2 speed gate on ONE exclusive Expanse compute node: int_speed.py runs every
# cumulative gmp binary on the L8 sweep sample (16 x 8 lanes, 3 interleaved repeats, medians), then perf stat IPC of the
# two candidate default binaries on heavy_free_L8 (the R3c rule). The binaries (all built by int_build.slurm):
#   B0   Stage-3 baseline            $INT_S4/bin/baseline/c8d2_gmp (5c5328af..., checked)
#   B1   +R5 (R5a; R5b is tools)     $INT_S1/bin/c8d2_gmp
#   B2   +R3a                        $INT_S2/bin/c8d2_gmp
#   B3   +R4a                        $INT_S3/bin/c8d2_gmp
#   B4   +R4f (B3's source, GMP_PREFIX=zen2)   $C8_DATA/work/<INT_S4 sha12>/int-zen2-S3src/bin/c8d2_gmp
#   B2f  R4f without R4a (B2's source, zen2)   $C8_DATA/work/<INT_S4 sha12>/int-zen2-S2src/bin/c8d2_gmp
# Steps: R5a B0:B1, R3a B1:B2, R4a B2:B3, R4f B3:B4, R4f_without_R4a B2:B2f, R4a_with_R4f B2f:B4.
# Expected wall about 15-25 min (6 binaries x 3 repeats of ~15-35 s, staging, IPC ~2 min).
# Usage: INT_S1=... INT_S2=... INT_S3=... INT_S4=<export holding this script> sbatch --export=ALL [--dependency=...] int_speed.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${INT_S1:?}" "${INT_S2:?}" "${INT_S3:?}" "${INT_S4:?}"
TAG=$(basename "$INT_S4"); RUN=intspeed.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"
W=$C8_DATA/work/$TAG
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; perf --version 2>&1; echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"; } > "$C8_DATA/work/node_$SLURM_JOB_ID.txt" 2>&1
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || { echo "no node-local scratch $S" >&2; exit 69; }
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=$S/tmp; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
cd "$INT_S4" || exit 64
status=0
python3 -B benchmarks/expanse_2026-10-c8/stage4b/integration/scripts/int_speed.py \
  --exe B0="$INT_S4/bin/baseline/c8d2_gmp" --exe B1="$INT_S1/bin/c8d2_gmp" --exe B2="$INT_S2/bin/c8d2_gmp" --exe B3="$INT_S3/bin/c8d2_gmp" \
  --exe B4="$W/int-zen2-S3src/bin/c8d2_gmp" --exe B2f="$W/int-zen2-S2src/bin/c8d2_gmp" --expect B0=5c5328af932912bb \
  --step R5a=B0:B1 --step R3a=B1:B2 --step R4a=B2:B3 --step R4f=B3:B4 --step R4f_without_R4a=B2:B2f --step R4a_with_R4f=B2f:B4 \
  --cost-model benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json --repeats 3 --shape 16x8 --block-tasks 256 \
  --ipc B2,B3 --ipc-threads 64 --output "$E" --scratch "$S" || status=$?
mkdir -p "$E"; mv "$C8_DATA/work/node_$SLURM_JOB_ID.txt" "$E/node.txt"; sha256sum "$HOME/c8d2/env_expanse.sh" > "$E/env_expanse.sha256"
{ echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; for b in "$W/int-zen2-S3src/bin/c8d2_gmp" "$W/int-zen2-S2src/bin/c8d2_gmp" "$INT_S3/bin/c8d2_gmp"; do echo "# $b"; ldd "$b" | grep libgmp; done; } > "$E/ldd.txt"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
