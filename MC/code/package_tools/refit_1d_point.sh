#!/bin/bash
# Re-run the 1D v3 fitting stage (select_model_v3.py) for one point from the packaged inputs of its selected production snapshot.
# Usage: refit_1d_point.sh WORK DELTA_SIGMA [WORKERS]
# Same arguments as the production driver run_fits_v3.sh (bootstrap 300, calibration 500, schedule 20260916, frozen pre.json of the
# selected run), but the output goes to WORK/reproduced/1d_refit/ds<Δσ>/ and NO selection is published, so data/ is never written.
# The analysis manifest and completion evidence name the original cluster paths; if their lineage check cannot be satisfied here the
# run is stamped NON-PRODUCTION, which does not change any number. Compare with: compare_outputs.py WORK
set -euo pipefail
W=$(cd "${1:?workspace}" && pwd); DS=${2:?delta sigma, e.g. 0.1727335}; NW=${3:-$(nproc 2>/dev/null || sysctl -n hw.ncpu)}; PY=${PY:-python3}
CAMP=$W/lri_cluster/scanA_exp/scan_data/ds$DS
read -r T RUN < <("$PY" -c "import json;d=json.load(open('$CAMP/fits_v3_SELECTED.json'));print(d['snapshot'],d['selected_run'])")
OUT=$W/reproduced/1d_refit/ds$DS
[ -e "$OUT" ] && { echo "$OUT exists; remove it to re-run" >&2; exit 1; }
mkdir -p "$(dirname "$OUT")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$W/lri_cluster"
EVI=( "$CAMP"/completion_"$T"_*.json )
"$PY" select_model_v3.py --merged "$CAMP/merged_b4096_$T" --reblock "$CAMP/merged_b2048_$T" "$CAMP/merged_b8192_$T" --out "$OUT" \
  --bootstrap 300 --calibration 500 --schedule 20260916 --workers "$NW" --pre "$CAMP/$RUN/pre.json" \
  --analysis-manifest "$CAMP/analysis_v3_$T.manifest" --completion-evidence "${EVI[@]}" --registry "$CAMP/campaigns.json" 2>&1 | tee "$W/reproduced/1d_refit/ds${DS}.log"
echo "reference: $CAMP/$RUN ; reproduced: $OUT"
