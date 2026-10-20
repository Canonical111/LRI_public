#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=32 --mem=64G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-s4c-dd-dev
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# R3b `dd` development run on 32 shared cores (Stage 4c; PLAN A-FLAG-4; development evidence, never a gate record):
#   1. tests/dd_accuracy.cpp (dd_dev.py accuracy): the dd arithmetic and exponential against 120 digits;
#   2. the development variants of bin/c8d2_gmp_dd (dd_dev.py variants): dd_direct (C8_DD_ROUTING=0, every dd failure
#      to MP) and dd_dens (C8_DD_GUARD=1, the denominator guard when every xs_j <= 1);
#   3. F1 (tests/numerics_flags.py --parts F1) at --f1-scale $F1_SCALE for each executable of $F1_EXES (default: dd and
#      every variant), with the dd profile's F1 checks (routes, the guards forced and at their boundary, the dd-ratio
#      decades against binary128's verdict, dd against binary128): against $F1_BASELINE (an exact baseline directory of
#      the same bin/c8d2_gmp and scale) when given, else the first one computes the baseline with 450-digit references;
#   4. dd_dev.py summary.
# C8_PACKAGE: an export built by s4c_build.slurm with C8_S4C_PROFILES=dd. Evidence: $C8_DATA/evidence/<sha12>/s4cdd.<job>.0/
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
F1_SCALE=${F1_SCALE:-0.25}; ACC_N=${ACC_N:-400000}; VARIANTS=${VARIANTS:-dd_direct=C8_DD_ROUTING=0 dd_dens=C8_DD_GUARD=1}
F1_EXES=${F1_EXES:-dd $(for v in $VARIANTS; do printf '%s ' "${v%%=*}"; done)}; F1_BASELINE=${F1_BASELINE:-}
TAG=$(basename "$C8_PACKAGE"); RUN=s4cdd.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E; F1 scale $F1_SCALE; variants $VARIANTS"
lscpu | grep -E 'Model name'; sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then S=$L; else S=$C8_DATA/work/$RUN; fi
export TMPDIR=$S/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "scratch $S"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
H=benchmarks/expanse_2026-10-c8/stage4c/dev_dd/scripts/dd_dev.py; NT=${SLURM_CPUS_PER_TASK:-32}
test -x bin/c8d2_gmp_dd || { echo "no bin/c8d2_gmp_dd: build the export with C8_S4C_PROFILES=dd" >&2; exit 64; }
status=0
if [ "$ACC_N" != 0 ]; then echo "== accuracy"; python3 -B $H accuracy "$E/accuracy" "$ACC_N" "$NT" || status=1; fi
echo "== variants"; python3 -B $H variants $VARIANTS > "$E/variants.log" 2>&1 || { status=3; tail -40 "$E/variants.log"; }
sha256sum bin/c8d2_gmp bin/c8d2_gmp_dd* 2>/dev/null | grep -v build.json | tee "$E/binaries.sha256"
mkdir -p "$E/build_records"; cp bin/c8d2_gmp_dd*.build.json "$E/build_records/"
dirs=; base=$F1_BASELINE
for x in $F1_EXES; do
  echo "== F1 $x${base:+ (baseline $base)}"
  python3 -B tests/numerics_flags.py --profile dd --profile-exe "bin/c8d2_gmp_$x" --parts F1 --f1-scale "$F1_SCALE" ${base:+--f1-baseline "$base"} \
    --output "$E/f1_$x" --scratch "$TMPDIR" || status=1
  dirs="$dirs $E/f1_$x"; [ -n "$base" ] || base=$E/f1_$x/f1_baseline
done
python3 -B $H summary "$E/summary.json" $dirs || status=1
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
