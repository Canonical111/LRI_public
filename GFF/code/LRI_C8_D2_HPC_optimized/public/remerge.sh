#!/bin/bash
# Re-merge the 24 groups of the independent check's production from their checkpoints, with the production's own
# tools/production.py merge, and compare each new merged.json with the shipped one byte for byte; then recompute the kernel
# time from the checkpoint rows. Usage (from the package folder): bash public/remerge.sh HOSTED_RUN SHIPPED_RUN OUT
#   HOSTED_RUN   the unpacked hosted campaign directory (manifest.json, cost_model.json, allocation.json, groups/*/...)
#   SHIPPED_RUN  ../../data/C8_2_check/prod1 (the merged records that `replay` uses)
#   OUT          a scratch directory with room for a copy of HOSTED_RUN (1.7 GB); it is created and may be deleted afterwards
set -euo pipefail
HOSTED=${1:?hosted run directory}; SHIPPED=${2:?shipped run directory}; OUT=${3:?output directory}
PY=${PY:-python3}; WORKERS=${WORKERS:-8}
[[ -f $HOSTED/manifest.json ]] || { echo "remerge: $HOSTED/manifest.json not found; run make -f public.mk fetch-data first" >&2; exit 2; }
cmp "$HOSTED/manifest.json" "$SHIPPED/manifest.json"
mkdir -p "$OUT"; W=$OUT/prod1
[[ -e $W ]] && { echo "remerge: $W exists; remove it first" >&2; exit 2; }
cp -a "$HOSTED" "$W"
rm -f "$W"/groups/*/merged.json "$W"/C8_result.json
"$PY" -B tools/production.py merge "$W" --workers "$WORKERS" --scratch "$OUT"
fail=0
for f in "$SHIPPED"/groups/*/merged.json; do
  g=$(basename "$(dirname "$f")")
  if cmp -s "$f" "$W/groups/$g/merged.json"; then echo "PASS  $g merged.json identical"; else echo "FAIL  $g merged.json differs"; fail=1; fi
done
"$PY" -B public/kernel_time.py "$W" | tee "$OUT/kernel_time.txt"
exit $fail
