#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s4c-dd-speed
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# R3b `dd` speed and routing measurement on ONE exclusive compute node (2 x EPYC 7742; Stage 4c, PLAN A-FLAG-4;
# development evidence, never a gate record):
#   0. tests/dd_accuracy.cpp (dd_dev.py accuracy, ACC_N points, 0 skips it): the dd arithmetic against 120 digits;
#   1. the development variants (dd_dev.py variants; kept when already built): dd_direct (C8_DD_ROUTING=0), and
#      dd_never (C8_DD_RATIO=1e300, C8_DD_CASCADE_LOW=0: no dd value is ever accepted and every point goes on to
#      nx::quad_tier, so the profile build, -mavx2 -mfma included, must compute the exact path's numbers bit for bit);
#   2. F4 (tests/numerics_flags.py --parts F4: the L8 sweep sample, 2,000 graphs x 2 x 512 points, 16 lanes x 8
#      threads, 3 interleaved repeats of the exact executable and the profile, medians) for every executable of
#      $SPEED (default: dd = the profile's default routing, then dd_direct): one after another on this node;
#   3. F1 at --f1-scale $F1_SCALE (default 1: the A-RPL-5 set) for bin/c8d2_gmp_dd, its exact baseline computed here,
#      when $F1_SCALE is not 0; then F1 of each executable of $F1_EXTRA (default dd_never) against that baseline;
#   4. dd_dev.py summary.
# C8_PACKAGE: an export built by s4c_build.slurm with C8_S4C_PROFILES=dd. Evidence: $C8_DATA/evidence/<sha12>/s4cddspeed.<job>.0/
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
SPEED=${SPEED:-dd dd_direct}; F1_SCALE=${F1_SCALE:-1}; ACC_N=${ACC_N:-400000}; F1_EXTRA=${F1_EXTRA:-dd_never}
VARIANTS=${VARIANTS:-dd_direct=C8_DD_ROUTING=0 dd_never=C8_DD_RATIO=1e300,C8_DD_CASCADE_LOW=0}
TAG=$(basename "$C8_PACKAGE"); RUN=s4cddspeed.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E; speed $SPEED; F1 scale $F1_SCALE"
lscpu | grep -E 'Model name'; sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || { echo "no node-local scratch $S" >&2; exit 69; }
export TMPDIR=$S/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "scratch $S"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
H=benchmarks/expanse_2026-10-c8/stage4c/dev_dd/scripts/dd_dev.py
test -x bin/c8d2_gmp_dd || { echo "no bin/c8d2_gmp_dd: build the export with C8_S4C_PROFILES=dd" >&2; exit 64; }
status=0
if [ "$ACC_N" != 0 ]; then echo "== accuracy"; python3 -B $H accuracy "$E/accuracy" "$ACC_N" 128 || status=1; fi
echo "== variants"; python3 -B $H variants $VARIANTS > "$E/variants.log" 2>&1 || { status=3; tail -40 "$E/variants.log"; }
sha256sum bin/c8d2_gmp bin/c8d2_gmp_dd* 2>/dev/null | grep -v build.json | tee "$E/binaries.sha256"
dirs=
for x in $SPEED; do
  echo "== F4 $x ($(date -Is))"
  python3 -B tests/numerics_flags.py --profile dd --profile-exe "bin/c8d2_gmp_$x" --parts F4 --output "$E/f4_$x" --scratch "$TMPDIR" || status=1
  dirs="$dirs $E/f4_$x"
done
if [ "$F1_SCALE" != 0 ]; then
  echo "== F1 dd at scale $F1_SCALE ($(date -Is))"
  python3 -B tests/numerics_flags.py --profile dd --parts F1 --f1-scale "$F1_SCALE" --output "$E/f1_dd" --scratch "$TMPDIR" || status=1
  dirs="$dirs $E/f1_dd"
  for x in $F1_EXTRA; do
    echo "== F1 $x ($(date -Is))"
    python3 -B tests/numerics_flags.py --profile dd --profile-exe "bin/c8d2_gmp_$x" --parts F1 --f1-scale "$F1_SCALE" --f1-baseline "$E/f1_dd/f1_baseline" \
      --output "$E/f1_$x" --scratch "$TMPDIR" || status=1
    dirs="$dirs $E/f1_$x"
  done
fi
python3 -B $H summary "$E/summary.json" $dirs || status=1
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
