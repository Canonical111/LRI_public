#!/bin/bash
# Per-point v3 analysis driver (FIT_MODEL_V3.md §4.7 union schema, replaces run_point_v2.sh for v3 results).
#   run_point_v3.sh snapshot POINT_DIR T [CAMPAIGN ...]   per-host: completion check with hashed evidence for the active campaigns whose
#                                                          chains are on this host (default: all active campaigns hosted here, or all if no
#                                                          host is declared); analyze.py at blocks 2048/4096/8192 into <campaign>_an_b<b>_T
#   run_point_v3.sh finalize POINT_DIR T PRE [BS] [CAL]    gathering: every active campaign needs PASS evidence for tag T (any host) and its
#                                                          three analysis directories; union_check (independence across campaigns); merge of
#                                                          ALL active campaigns per pair at the three block sizes; then run_fits_v3.sh with
#                                                          the frozen pre-fit PRE (pre.json of the N1 record: never re-derived from the union)
#   run_point_v3.sh all POINT_DIR PRE [BS] [CAL]           both stages on one host
# Every step and every input hash (registry, manifests, DONE records, archives, summaries, evidence, union check) goes into
# POINT_DIR/analysis_v3_T.manifest, which run_fits_v3.sh binds into the fit provenance (lineage verification).
set -euo pipefail
MODE=${1:?snapshot|finalize|all}; D=${2:?point dir}; shift 2
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$(dirname "$0")"
REG="$D/campaigns.json"
run() { echo "$(date +%F_%T) $*" >> "$M"; "$@"; }
hashimpl() { sha256sum run_point_v3.sh run_fits_v3.sh registry.py completion_check.py union_check.py independence.py analyze.py merge_summaries.py window_filter.py select_model_v3.py select_model.py fit_fss.py quotients.py bootstrap_schedule.py equilibration.py n0_diagnostic.py scan_v3_report.py FIT_MODEL_V3.md >> "$M"; }
here=$(hostname -s)

snapshot() {
  T=$1; shift; M="$D/analysis_v3_${T}_$here.manifest"     # per-host snapshot manifest (AUDIT-002); finalize assembles analysis_v3_T.manifest
  RS="$D/registry_${T}_$here.json"
  for f in "$M" "$RS" "$D/completion_${T}_$here.json"; do [ -e "$f" ] && { echo "snapshot $T on $here already exists ($f): attempts are immutable — use a new tag" >&2; exit 1; }; done   # RV3-003
  cp "$REG" "$RS"       # immutable per-host registry snapshot, transferred with the snapshot (IR6-002); IR21-002: every step below reads $RS, never the live registry
  { echo "snapshot $T host $here mode snapshot (v3 union)"; sha256sum "$RS"; hashimpl; } >> "$M"
  if [ $# -gt 0 ]; then CAMPS="$*"; else
    CAMPS=$(python3 - "$RS" "$here" <<'PY'
import json,sys
sys.path.insert(0,'.')
from registry import load, active_names
r=load(open(sys.argv[1]) and __import__('pathlib').Path(sys.argv[1])); here=sys.argv[2]
names=active_names(r)
hosted=[n for n in names if not any(c['name']==n and c.get('host') and not (here.startswith(c['host']) or c['host'].startswith(here)) for c in r['campaigns'])]
print(' '.join(hosted))
PY
  ); fi
  [ -n "$CAMPS" ] || { echo "no active campaign is hosted on $here" >&2; exit 1; }
  echo "campaigns on this host: $CAMPS" | tee -a "$M"
  run python3 completion_check.py "$RS" --campaigns $CAMPS --evidence "$D/completion_${T}_$here.json"
  sha256sum "$D/completion_${T}_$here.json" >> "$M"
  for name in $CAMPS; do st=$(python3 -c "import json;r=json.load(open('$RS'));print(next(c['dir'] for c in r['campaigns'] if c['name']=='$name'))")
    for b in 2048 4096 8192; do
      run python3 analyze.py "$D/$st" --block $b --out "$D/${st}_an_b${b}_$T"
      sha256sum "$D/${st}_an_b${b}_$T/summary.json" "$D/${st}_an_b${b}_$T"/blocks_*.npz >> "$M"
    done
  done
  echo "snapshot $T complete for: $CAMPS" | tee -a "$M"
}

finalize() {
  T=$1; PRE=$2; BS=${3:-300}; CAL=${4:-500}; MF="$D/analysis_v3_$T.manifest"; M="$MF.assembling.$$"
  # assemble the provenance manifest in a temporary file from every host's snapshot manifest after verifying each listed file here
  # (AUDIT-002); it is published atomically only after the assembly and the checks succeed (RV3-003)
  [ -e "$MF" ] && { echo "finalize $T: $MF already exists — a finalize attempt is immutable; use a new tag or remove the failed attempt explicitly" >&2; exit 1; }
  ls "$D"/analysis_v3_${T}_*.manifest >/dev/null 2>&1 || { echo "no per-host snapshot manifests analysis_v3_${T}_<host>.manifest in $D" >&2; exit 1; }
  trap 'rm -f "$M"' EXIT
  : > "$M"
  for hm in "$D"/analysis_v3_${T}_*.manifest; do
    echo "== per-host snapshot manifest $(basename "$hm")" >> "$M"
    python3 - "$hm" "$D" <<'PY'
import hashlib,re,sys,os
hm,D=sys.argv[1:3];D=os.path.abspath(D);pt=os.path.basename(D);bad=0;n=0;missing=0
for l in open(hm):
    m=re.match(r'^([0-9a-f]{64})\s+(\S+)',l.strip())
    if not m or '/' not in m.group(2):continue          # implementation hashes (bare names) are not consumed-file claims
    path=m.group(2);seg=f'/{pt}/'
    local=os.path.join(D,path.split(seg,1)[1]) if seg in path else path   # IR5-002: transferred files live under this point directory
    if not os.path.exists(local):print('MISSING transferred file',local);missing+=1;continue
    n+=1
    if hashlib.sha256(open(local,'rb').read()).hexdigest()!=m.group(1):print('HASH MISMATCH',local);bad+=1
print(f'{os.path.basename(hm)}: {n} listed files verified here, {bad} mismatches, {missing} missing')
sys.exit(1 if (bad or missing) else 0)
PY
    cat "$hm" >> "$M"
  done
  # IR6-002: every per-host registry snapshot must agree with the gathering registry in its portable fields (roots may differ)
  for rs in "$D"/registry_${T}_*.json; do python3 -c "
import sys; sys.path.insert(0,'.')
from pathlib import Path
from registry import load, portable_view
a=portable_view(load(Path('$rs'))); b=portable_view(load(Path('$REG')))
if a!=b: raise SystemExit('registry snapshot $(basename $rs) differs from the gathering registry in portable fields: '+str([k for k in a if a[k]!=b.get(k)]))
print('registry snapshot $(basename $rs): portable view identical')" || exit 1; done
  { echo "finalize $T host $here (v3 union)"; sha256sum "$REG" "$PRE"; hashimpl; } >> "$M"
  run python3 union_check.py "$REG" --tag "$T" --point-dir "$D" --out "$D/union_check_$T.json"
  sha256sum "$D/union_check_$T.json" >> "$M"
  mv "$M" "$MF"; trap - EXIT; M="$MF"   # assembly and checks succeeded: publish the manifest (RV3-003)
  python3 - "$REG" "$D" "$T" <<'PY'
import json,sys,glob,os,hashlib
sys.path.insert(0,'.')
from pathlib import Path
from registry import load, active_names
reg,D,T=sys.argv[1:4]; r=load(Path(reg)); active=active_names(r); ev={}
for f in glob.glob(f'{D}/completion_{T}_*.json'):
    e=json.load(open(f))
    for name,c in e['campaigns'].items(): ev[name]=dict(file=os.path.basename(f),host=e['host'],manifest_sha256=c['manifest_sha256'])
for n in active:
    d=next(c['dir'] for c in r['campaigns'] if c['name']==n)
    man=hashlib.sha256(open(f'{D}/{d}/manifest.json','rb').read()).hexdigest()
    if man!=ev[n]['manifest_sha256']: raise SystemExit(f'{n}: manifest.json here differs from the one checked on {ev[n]["host"]}')
    for b in (2048,4096,8192):
        if not os.path.exists(f'{D}/{d}_an_b{b}_{T}/summary.json'): raise SystemExit(f'{n}: missing analysis {d}_an_b{b}_{T}')
print('manifests and analysis directories present for all active campaigns; hosts',sorted({ev[n]['host'] for n in active}))
PY
  for b in 2048 4096 8192; do
    run python3 merge_summaries.py "$REG" --coverage all --suffix "_an_b${b}_$T" --out "$D/merged_b${b}_$T"
    sha256sum "$D/merged_b${b}_$T/summary.json" >> "$M"
  done
  if [ "${RUN_POINT_V3_STOP_AFTER_MERGE:-0}" = 1 ]; then echo "finalize $T: stopped after the merge (RUN_POINT_V3_STOP_AFTER_MERGE=1, tests only)" | tee -a "$M"; return 0; fi
  ANALYSIS_MANIFEST="$M" run ./run_fits_v3.sh "$D" "$T" "$PRE" "$BS" "$CAL"
  echo "point done: $D (v3 analysis snapshot $T; manifest $M)"
}

case "$MODE" in
  snapshot) snapshot "$@";;
  finalize) finalize "$@";;
  all) PRE=${1:?pre.json}; shift; T=$(date +%Y%m%d_%H%M%S); snapshot "$T"; finalize "$T" "$PRE" "$@";;
  *) echo "unknown mode $MODE" >&2; exit 2;;
esac
