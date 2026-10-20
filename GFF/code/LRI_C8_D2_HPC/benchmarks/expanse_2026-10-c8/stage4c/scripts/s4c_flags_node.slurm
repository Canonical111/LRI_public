#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 01:30:00 --no-requeue
#SBATCH -J c8d2-s4c-gate
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4c: tests/numerics_flags.py (A-FLAG-3 F-gates, J-FLAG-<profile>) on ONE exclusive compute node (2 x EPYC 7742,
# 128 cores): the full-scale F1 baseline (--f1-baseline-only) and the gate runs (--profile P --f1-baseline DIR).
# C8_PACKAGE: an export built by s4c_build.slurm; FLAGS_ARGS: the numerics_flags.py arguments (e.g. "--profile dd
# --f1-scale 0.05 --f2-graphs 16 ..."), FLAGS_NAME: the record's directory name in the evidence directory. Evidence:
# $C8_DATA/evidence/<sha12>/s4cgate.<job>.0/<FLAGS_NAME>/. A second run in the same job: FLAGS_ARGS2, FLAGS_NAME2
# (run after the first, which it may reuse: the literal @OUT1 in FLAGS_ARGS2 is replaced by the first run's directory).
# Usage: C8_PACKAGE=... FLAGS_ARGS="..." FLAGS_NAME=... sbatch --export=ALL s4c_flags_node.slurm (submit_s4c.sh)
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${FLAGS_ARGS:?}" "${FLAGS_NAME:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s4cgate.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'; sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || { echo "no node-local scratch $S" >&2; exit 69; }
export TMPDIR=$S/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "scratch $S"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp bin/c8d2_gmp_* 2>/dev/null | grep -v build.json | tee "$E/binaries.sha256"
status=0
echo "== numerics_flags.py $FLAGS_ARGS"
python3 -B tests/numerics_flags.py $FLAGS_ARGS --output "$E/$FLAGS_NAME" --scratch "$TMPDIR" || status=$?
if [ -n "${FLAGS_ARGS2:-}" ]; then
  A2=${FLAGS_ARGS2//@OUT1/$E/$FLAGS_NAME}; echo "== numerics_flags.py $A2"
  python3 -B tests/numerics_flags.py $A2 --output "$E/${FLAGS_NAME2:?}" --scratch "$TMPDIR" || status=$?
fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
