#!/bin/bash
# v2 fitting protocol driver (FIT_PLAN.md §3.8). Usage: run_fits_v2.sh CAMP_ROOT SNAPSHOT_T [BOOTSTRAP] [CALIBRATION]
# Consumes the merged summaries of an existing final-analysis snapshot (merged_b{2048,4096,8192}_T, produced by
# run_prod_fits.sh after a passing completion check) and writes a fresh fits_v2_<T2> directory with a manifest,
# all family fits, cross-check series, fit_v2.json and FIT_V2_RESULTS.md. No simulation data are modified.
set -euo pipefail
CAMP=${1:?campaign root}; T=${2:?snapshot timestamp of merged_b*_T}; BS=${3:-300}; CAL=${4:-500}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$(dirname "$0")"
for b in 2048 4096 8192; do for w in summary.json summary_c3.json; do
  [ -s "$CAMP/merged_b${b}_$T/$w" ] || { echo "missing $CAMP/merged_b${b}_$T/$w" >&2; exit 1; }
done; done
T2=$(date +%Y%m%d_%H%M%S); OUT="$CAMP/fits_v2_$T2"; mkdir -p "$OUT"; M="$OUT/MANIFEST.txt"
{ echo "fits_v2 snapshot $T2 from merged snapshot $T"; echo "host $(hostname) workers ${SLURM_CPUS_ON_NODE:-$(nproc)}"
  sha256sum FIT_PLAN.md select_model.py fit_fss.py quotients.py bootstrap_schedule.py analyze.py equilibration.py; } >> "$M"
python3 select_model.py --merged "$CAMP/merged_b4096_$T" --reblock "$CAMP/merged_b2048_$T" "$CAMP/merged_b8192_$T" \
    --out "$OUT" --bootstrap "$BS" --calibration "$CAL" --schedule 20260916 ${WORKERS:+--workers $WORKERS} \
    ${ANALYSIS_MANIFEST:+--analysis-manifest "$ANALYSIS_MANIFEST"} 2>&1 | tee "$OUT/select_model.log"
echo "done: $OUT/FIT_V2_RESULTS.md ; manifest $M"
