#!/bin/bash
# v3 evaluator driver (FIT_MODEL_V3.md). Usage: run_fits_v3.sh CAMP_ROOT SNAPSHOT_T PRE_SOURCE [BOOTSTRAP] [CALIBRATION] [extra select_model_v3 args]
#   PRE_SOURCE: a pre.json (frozen beta_c/Delta_eps per s) or a fits_v2_* directory to freeze them from; use "legacy" for the
#   v2 full/c3 windows (two-point re-derivation only). Writes CAMP_ROOT/fits_v3_<T2>/ with manifest, fits, xcheck files.
set -euo pipefail
CAMP=${1:?campaign root}; T=${2:?merged snapshot timestamp}; PRE=${3:?pre.json | fits_v2 dir | legacy}; BS=${4:-300}; CAL=${5:-500}; shift 5 || shift $#
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$(dirname "$0")"
for b in 2048 4096 8192; do [ -s "$CAMP/merged_b${b}_$T/summary.json" ] || { echo "missing $CAMP/merged_b${b}_$T/summary.json" >&2; exit 1; }; done
T2=$(date +%Y%m%d_%H%M%S); OUT="$CAMP/fits_v3_$T2"
if ! mkdir "$OUT" 2>/dev/null; then T2="${T2}_$$"; OUT="$CAMP/fits_v3_$T2"; mkdir "$OUT" || { echo "cannot create a unique run directory $OUT" >&2; exit 1; }; fi   # IR18-003: never share a run directory
M="$OUT/MANIFEST.txt"
{ echo "fits_v3 snapshot $T2 from merged snapshot $T; pre source $PRE"; echo "host $(hostname) workers ${WORKERS:-$(nproc)}"
  sha256sum FIT_MODEL_V3.md select_model_v3.py select_model.py fit_fss.py quotients.py bootstrap_schedule.py equilibration.py analyze.py independence.py union_check.py merge_summaries.py registry.py completion_check.py window_filter.py run_point_v3.sh; } >> "$M"
if [ "$PRE" = legacy ]; then PREARG="--legacy-windows"; elif [ -d "$PRE" ]; then PREARG="--pre-from-v2 $PRE"; else PREARG="--pre $PRE"; fi
# snapshot lineage (§4.7): the analysis manifest of this snapshot and the completion evidence; without a manifest the run is NON-PRODUCTION
MAN=${ANALYSIS_MANIFEST:-$( [ -f "$CAMP/analysis_v3_$T.manifest" ] && echo "$CAMP/analysis_v3_$T.manifest" || ls "$CAMP"/analysis_v2_"$T".manifest 2>/dev/null | head -1)}   # the assembled manifest only (AUDIT-002)
if [ -n "${COMPLETION_EVIDENCE:-}" ]; then EVI=($COMPLETION_EVIDENCE); else EVI=($(ls "$CAMP"/completion_"$T"_*.json 2>/dev/null)); fi   # every per-host record (IR14-004)
echo "analysis manifest: ${MAN:-NONE}; completion evidence: ${EVI[*]:-NONE}" >> "$M"
python3 select_model_v3.py --merged "$CAMP/merged_b4096_$T" --reblock "$CAMP/merged_b2048_$T" "$CAMP/merged_b8192_$T" --out "$OUT" \
    --bootstrap "$BS" --calibration "$CAL" --schedule 20260916 ${WORKERS:+--workers $WORKERS} $PREARG \
    ${MAN:+--analysis-manifest "$MAN"} ${EVI[@]:+--completion-evidence "${EVI[@]}"} --registry "$CAMP/campaigns.json" "$@" 2>&1 | tee "$OUT/select_model_v3.log"
# publish the run selection (IR5-004): a production run becomes the point's selected record, bound to this snapshot
python3 - "$CAMP" "$OUT" "$T" <<'PY'
import json,sys,time,os
camp,out,T=sys.argv[1:4];r=json.load(open(os.path.join(out,'fit_v3.json')))
if r.get('legacy_windows'):print('selection not published: legacy windows are anchor reproduction only (FIT_MODEL_V3 §4.1), never a scan determination (V3-STATIC-004)')
elif r.get('production') and not r.get('errors'):
    sel=os.path.join(camp,'fits_v3_SELECTED.json');tmp=sel+'.tmp.'+str(os.getpid())   # atomic publication with a unique temp file (REV-007/IR9-002)
    json.dump(dict(selected_run=os.path.basename(out),snapshot=T,production=True,legacy_windows=r.get('legacy_windows'),points=sorted(r['points']),reason='production run published by run_fits_v3.sh',time=time.strftime('%F_%T')),open(tmp,'w'),indent=1);os.replace(tmp,sel)
    print('selection published:',os.path.basename(out))
else:print('selection unchanged (non-production or errors)')
PY
echo "done: $OUT/FIT_V3_RESULTS.md ; manifest $M"
