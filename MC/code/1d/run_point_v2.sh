#!/bin/bash
# Per-point v2 analysis driver for the scan (FIT_PLAN.md §6).
#   run_point_v2.sh snapshot POINT_DIR T [CAMPAIGN ...]   per-host stage: completion check with hashed evidence for the
#                                                          campaigns whose chains are on this host (default: all whose
#                                                          registry 'host' is this machine, or all if no host is declared),
#                                                          analyze.py at blocks 2048/4096/8192 into <campaign>_an_b<b>_T
#   run_point_v2.sh finalize POINT_DIR T [BS] [CAL]        gathering stage: every active campaign must have its snapshot
#                                                          (analysis dirs + PASS evidence) for tag T, transferred if needed;
#                                                          coverage is validated, then merge -> c3 window -> run_fits_v2.sh
#   run_point_v2.sh all POINT_DIR [BS] [CAL]               both stages on one host (Expanse points)
# Every step, every input hash (registry, campaign manifests, DONE records, raw samples, analysis summaries) and the
# pipeline implementation hashes go into POINT_DIR/analysis_v2_T.manifest; finalize links it into the fit provenance.
set -euo pipefail
MODE=${1:?snapshot|finalize|all}; D=${2:?point dir}; shift 2
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$(dirname "$0")"
REG="$D/campaigns.json"
run() { echo "$(date +%F_%T) $*" >> "$M"; "$@"; }
hashimpl() { sha256sum run_point_v2.sh run_fits_v2.sh registry.py completion_check.py analyze.py merge_summaries.py window_filter.py select_model.py fit_fss.py quotients.py bootstrap_schedule.py equilibration.py FIT_PLAN.md >> "$M"; }
here=$(hostname -s)

snapshot() {
  T=$1; shift; M="$D/analysis_v2_$T.manifest"
  { echo "snapshot $T host $here mode snapshot"; sha256sum "$REG"; hashimpl; } >> "$M"
  if [ $# -gt 0 ]; then CAMPS="$*"; else
    CAMPS=$(python3 - "$REG" "$here" <<'PY'
import json,sys,socket
r=json.load(open(sys.argv[1])); here=sys.argv[2]
act={n for v in r['active'].values() for n in ([v] if isinstance(v,str) else v)}   # list-aware (IR5-003)
names=[c['name'] for c in r['campaigns'] if c['name'] in act]
hosted=[n for n in names if not any(c['name']==n and c.get('host') and not (here.startswith(c['host']) or c['host'].startswith(here)) for c in r['campaigns'])]
print(' '.join(hosted))
PY
  ); fi
  [ -n "$CAMPS" ] || { echo "no active campaign is hosted on $here" >&2; exit 1; }
  echo "campaigns on this host: $CAMPS" | tee -a "$M"
  run python3 completion_check.py "$REG" --campaigns $CAMPS --evidence "$D/completion_${T}_$here.json"   # exit 1 => abort
  sha256sum "$D/completion_${T}_$here.json" >> "$M"
  for name in $CAMPS; do st=$(python3 -c "import json;r=json.load(open('$REG'));print(next(c['dir'] for c in r['campaigns'] if c['name']=='$name'))")
    for b in 2048 4096 8192; do
      run python3 analyze.py "$D/$st" --block $b --out "$D/${st}_an_b${b}_$T"
      sha256sum "$D/${st}_an_b${b}_$T/summary.json" "$D/${st}_an_b${b}_$T"/blocks_*.npz >> "$M"
    done
  done
  echo "snapshot $T complete for: $CAMPS" | tee -a "$M"
}

finalize() {
  T=$1; BS=${2:-300}; CAL=${3:-500}; M="$D/analysis_v2_$T.manifest"
  { echo "finalize $T host $here"; sha256sum "$REG"; hashimpl; } >> "$M"
  # every active campaign needs PASS evidence for tag T (from any host) and the three analysis directories
  run python3 - "$REG" "$D" "$T" <<'PY'
import json,sys,glob,os
reg,D,T=sys.argv[1:4]; r=json.load(open(reg)); active=sorted({n for v in r['active'].values() for n in ([v] if isinstance(v,str) else v)})   # list-aware (IR5-003)
ev={}
for f in glob.glob(f'{D}/completion_{T}_*.json'):
    e=json.load(open(f))
    if e['result']!='PASS': raise SystemExit(f'{f}: completion evidence is {e["result"]}')
    for name,c in e['campaigns'].items(): ev[name]=dict(file=os.path.basename(f),host=e['host'],pairs=c['pairs'],manifest_sha256=c['manifest_sha256'])
missing=[n for n in active if n not in ev]
if missing: raise SystemExit(f'no PASS completion evidence for tag {T} for campaigns {missing} (run the snapshot stage on their host and transfer completion_{T}_<host>.json and the _an_b*_{T} directories)')
import hashlib
for n in active:
    d=next(c['dir'] for c in r['campaigns'] if c['name']==n)
    man=hashlib.sha256(open(f'{D}/{d}/manifest.json','rb').read()).hexdigest()
    if man!=ev[n]['manifest_sha256']: raise SystemExit(f'{n}: manifest.json here differs from the one checked on {ev[n]["host"]}')
    for b in (2048,4096,8192):
        if not os.path.exists(f'{D}/{d}_an_b{b}_{T}/summary.json'): raise SystemExit(f'{n}: missing analysis {d}_an_b{b}_{T}')
acts={p:([v] if isinstance(v,str) else v) for p,v in r['active'].items()}
covered=sorted({p for n in active for p in ev[n]['pairs'] if n in acts.get(p,[])}); expected=sorted(r['expected_pairs'])
if covered!=expected: raise SystemExit(f'completion evidence covers {covered} but the registry expects {expected}')
print('completion evidence: PASS for all active campaigns; hosts',sorted({ev[n]["host"] for n in active}))
PY
  for b in 2048 4096 8192; do
    run python3 merge_summaries.py "$REG" --coverage all --suffix "_an_b${b}_$T" --out "$D/merged_b${b}_$T"
    run python3 window_filter.py "$D/merged_b${b}_$T/summary.json" "$REG" --keep 1 2 3 --out "$D/merged_b${b}_$T/summary_c3.json"
    sha256sum "$D/merged_b${b}_$T/summary.json" "$D/merged_b${b}_$T/summary_c3.json" >> "$M"
  done
  ANALYSIS_MANIFEST="$M" run ./run_fits_v2.sh "$D" "$T" "$BS" "$CAL"
  echo "point done: $D (analysis snapshot $T; manifest $M)"
}

case "$MODE" in
  snapshot) snapshot "$@";;
  finalize) finalize "$@";;
  all) T=$(date +%Y%m%d_%H%M%S); snapshot "$T"; finalize "$T" "$@";;
  *) echo "unknown mode $MODE" >&2; exit 2;;
esac
