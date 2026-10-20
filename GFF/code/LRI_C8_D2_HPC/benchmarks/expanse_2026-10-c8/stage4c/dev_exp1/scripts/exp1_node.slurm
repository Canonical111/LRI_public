#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s4c-exp1-node
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4c R4c `exp1` development run on ONE exclusive compute node (2 x EPYC 7742, 128 cores; <= 30 min; never gate
# evidence): (1) dev_exp1/scripts/exp1_probe.py (census of shifted points per tier, forced shifted points against
# 450-digit values and the exact path, per-call timing), then (2) tests/numerics_flags.py --profile exp1 --parts F1,F4
# (F1 at --f1-scale F1_SCALE, default 0.25: a development run; F4 on the full L8 sweep sample). C8_PACKAGE: an export
# built by s4c_build.slurm with the exp1 profile. PROBE_ARGS / FLAGS_ARGS: extra arguments; FLAGS2_ARGS: a second
# numerics_flags.py run (e.g. "--parts F4 --f4-loop 7") into flags2/. Evidence:
# $C8_DATA/evidence/<sha12>/s4cexp1.<job>.0/{probe,flags,flags2}/.
# Usage: C8_PACKAGE=... sbatch --export=ALL exp1_node.slurm   (dev_exp1/scripts/submit_exp1.sh node does this)
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s4cexp1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'; sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || { echo "no node-local scratch $S" >&2; exit 69; }
export TMPDIR=$S/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "scratch $S"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp bin/c8d2_gmp_exp1 | tee "$E/binaries.sha256"
status=0
echo "== exp1_probe.py ${PROBE_ARGS:-}"
python3 -B benchmarks/expanse_2026-10-c8/stage4c/dev_exp1/scripts/exp1_probe.py --output "$E/probe" --scratch "$TMPDIR" ${PROBE_ARGS:-} || status=$?
echo "== numerics_flags.py --profile exp1 --parts F1,F4 --f1-scale ${F1_SCALE:-0.25} ${FLAGS_ARGS:-}"
python3 -B tests/numerics_flags.py --profile exp1 --parts F1,F4 --f1-scale "${F1_SCALE:-0.25}" ${FLAGS_ARGS:-} --output "$E/flags" --scratch "$TMPDIR" || status=$?
if [ -n "${FLAGS2_ARGS:-}" ]; then
  echo "== numerics_flags.py --profile exp1 $FLAGS2_ARGS"
  python3 -B tests/numerics_flags.py --profile exp1 $FLAGS2_ARGS --output "$E/flags2" --scratch "$TMPDIR" || status=$?
fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
