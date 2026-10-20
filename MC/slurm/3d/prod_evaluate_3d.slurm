#!/bin/bash
#SBATCH -J lri3d_eval
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=16G
#SBATCH -t 02:00:00
#SBATCH -o <SCRATCH>/lri3d/logs/prod_eval_%j.out
# FIT_MODEL_3D §4: evaluator over the 8 primary (b=2000) and 16 reblock (b=1000, 4000) records of snapshot SNAP (required env); passes the registered
# extensions.json when present (FIT3D-014); a missing primary is labelled by the evaluator, not fatal (FIT3D-015); fresh immutable output directory.
set -uo pipefail
: "${SNAP:?snapshot id required}"
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd <CODE_3D> || exit 1
CAMP=<SCRATCH>/lri3d/prod3d
[ -s $CAMP/snapshots/$SNAP.json ] || { echo "no snapshot record for $SNAP; exit 63"; exit 63; }
P=(); R=(); for s in 1.55 1.6 1.7 1.75 1.8 1.85 1.9 1.95; do P+=($CAMP/analysis_${SNAP}_b2000_s$s); R+=($CAMP/analysis_${SNAP}_b1000_s$s $CAMP/analysis_${SNAP}_b4000_s$s); done
for d in "${P[@]}" "${R[@]}"; do [ -s $d/results.json ] && [ -s $d/bootstrap.npy ] || echo "record missing/incomplete: $d"; done
PX=(); for d in "${P[@]}"; do [ -s $d/results.json ] && PX+=($d); done   # FIT3D-020: may be empty — the evaluator then emits one NON-PRODUCTION row per point
# FIT3D-019: evaluate against the extension ledger FROZEN with this snapshot (verified against the snapshot record), never the mutable campaign file
REC=$CAMP/snapshots/$SNAP.json
python3 - "$REC" "$CAMP/manifest.json" <<'PY' || { echo "snapshot record does not match the manifest / frozen extensions; exit 68"; exit 68; }
import json,sys,hashlib,os
r=json.load(open(sys.argv[1])); sha=lambda f: hashlib.sha256(open(f,'rb').read()).hexdigest()
ok=r.get('manifest_sha256')==sha(sys.argv[2])
if r.get('extensions_frozen'): ok=ok and os.path.exists(r['extensions_frozen']) and sha(r['extensions_frozen'])==r.get('extensions_sha256')
print('snapshot record check:', 'OK' if ok else 'MISMATCH'); sys.exit(0 if ok else 1)
PY
FROZEN=$(python3 -c "import json;print(json.load(open('$REC')).get('extensions_frozen') or '')")
EXT=(); [ -n "$FROZEN" ] && EXT=(--extensions $FROZEN)
OUT=$CAMP/evaluation_${SNAP}_$(date +%Y%m%d_%H%M%S)
python3 evaluate_3d.py --primary "${PX[@]}" --reblock "${R[@]}" --plan <CODE_3D>/FIT_MODEL_3D.md --manifest $CAMP/manifest.json --centers <CODE_3D>/production_centers_3d.csv "${EXT[@]}" --snapshot $SNAP --out $OUT
rc=$?; echo "$(date) evaluate exit $rc -> $OUT"; ls $OUT 2>/dev/null; exit $rc
