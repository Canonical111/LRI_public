#!/bin/bash
#SBATCH -p debugq -N 1 --exclusive --mem=180G -t 00:59:00
#SBATCH -J c6prep -o /mnt/beegfs/zzheng1/lri_c6_1d/logs/%x_%j.out
# Build, enumerate graphs, generate and check weights: gates V1 (graphs) and V2 (weights). Owns
# $ATTEMPT_DIR/prepare.json; ends by writing $ATTEMPT_DIR/identities.json (source, executables, graphs, manifest).
set -euo pipefail
source "$C6_CODE/cluster/env.sh"
: "${ATTEMPT_DIR:?}"
cd "$C6_CODE"
mkdir -p "$ATTEMPT_DIR"; make -B all > "$ATTEMPT_DIR/build.log" 2>&1 || { tail -30 "$ATTEMPT_DIR/build.log"; exit 1; }
V=$ATTEMPT_DIR/prepare.json; mkdir -p "$ATTEMPT_DIR" "$C6_DATA" "$C6_RUNS" "$C6_LEVELS"; rm -f "$V"
L6N=$(seq -s, 6 2 30); L5M=$(seq -s, 12 4 40)
bin/enumerate 6 "$C6_DATA/graphs6.bin" > "$ATTEMPT_DIR/enum6.log"
bin/enumerate 7 "$C6_DATA/graphs7.bin" > "$ATTEMPT_DIR/enum7.log"
for nv in 6 7; do
  case $nv in 6) want='total=59145 nonzero=49605 ' ;; 7) want='total=2427005 nonzero=2137415 ' ;; esac
  line=$(head -1 "$ATTEMPT_DIR/enum$nv.log"); grep -q "$want" <<< "$line" && grep -qE "sumH=-(133200|5519062\.5)" <<< "$line" && rc=0 || rc=1
  python tools/validate.py "$V" check "V1_enumeration_nv${nv}" $rc "$line"
done
sha256sum "$C6_DATA"/graphs*.bin | tee "$ATTEMPT_DIR/graphs.sha256"
rm -f "$C6_DATA/weights_manifest.json"
python tools/weights.py "$C6_DATA" 6 "$L6N" --check
python tools/weights.py "$C6_DATA" 5 "$L5M" --check
S=$ATTEMPT_DIR/prepare80; rm -rf "$S"; mkdir -p "$S"; cp reference/prepare.py "$S/"; ln -sfn "$C6_CODE/reference/lri_numerical_resolution" "$S/lri_numerical_resolution"
(cd "$S" && python prepare.py 6 "$L6N" > /dev/null && python prepare.py 5 "$L5M" > /dev/null)
python tools/validate.py "$V" weights V2_weights_L6_vs_prepare80 "$C6_DATA" "$S" 6 "$L6N"
python tools/validate.py "$V" weights V2_weights_L5_vs_prepare80 "$C6_DATA" "$S" 5 "$L5M"
for L in 5 6; do
  ok=$(python -c "import json;r=json.load(open('$C6_DATA/weights_report_L$L.json'));print(int(all(x['check_pass'] for x in r.values())))")
  python tools/validate.py "$V" check V2_weights_selfcheck_L${L} $(( 1 - ok )) "see weights_report_L$L.json"
done
T=$(mktemp -d); SZ=$(stat -c %s "$C6_DATA/graphs7.bin")
for cut in 4 92; do
  head -c $((SZ - cut)) "$C6_DATA/graphs7.bin" > "$T/graphs7.bin"; ln -sf "$C6_DATA/w_6_6.bin" "$T/w_6_6.bin"
  set +e; bin/c6sum 6 6 2 "$T" H --out "$T/x.jsonl" --first 0 --stop 1 2> "$T/err"; rc=$?; set -e; cat "$T/err"
  [[ -e $T/x.jsonl ]] && { echo "output created before input validation"; rc=0; }
  python tools/validate.py "$V" expect-fail V1_refuse_graphs_truncated_by_$cut "$rc"
done
rm -rf "$T"
c6_identities > "$ATTEMPT_DIR/identities.json"; cat "$ATTEMPT_DIR/identities.json"
echo "prepare done $(date)"
