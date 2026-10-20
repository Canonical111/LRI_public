#!/bin/bash
#SBATCH --job-name=c8-weights
#SBATCH --account=yun124
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=%x-%j.out
# Order-eight meromorphic weights (C8WEIGHTS1, 100 digits) and Gamma jets for every (loop, degree) that the unit
# designs in designs/*_unit.json require. One generator per loop; every child's exit status is checked, and the job
# fails unless every required file exists. Required: C8_ENV_SETUP, C8_ROOT, C8_OUT.
set -eo pipefail
source "${C8_ENV_SETUP:?}"
set -u
: "${C8_ROOT:?}" "${C8_OUT:?}"
cd "$C8_ROOT"
mkdir -p "$C8_OUT"
REQ="$C8_OUT/required_weights.$$.txt"
"$C8_PYTHON" - > "$REQ" <<'EOF' # foreground: a malformed or missing unit design fails the job (set -e)
import json,glob,sys
files=sorted(glob.glob('designs/*_unit.json'))
if not files:sys.exit('no designs/*_unit.json found')
need={}
for f in files:
    for s in json.load(open(f))['campaigns']:
        for N in s['degrees']:
            if N:need.setdefault(int(s['L']),set()).add(int(N))
if not need:sys.exit('the unit designs require no weights')
for L in sorted(need):print(L,*sorted(need[L]))
EOF
mapfile -t LINES < "$REQ"
(( ${#LINES[@]} > 0 )) || { echo "C8: empty required-weight set" >&2; exit 1; }
pids=();labels=()
for line in "${LINES[@]}"; do
  read -r L degs <<<"$line"
  "$C8_PYTHON" tools/regenerate_weights.py --out "$C8_OUT" --L "$L" --degrees $degs --dps 100 > "$C8_OUT/log_L$L.txt" 2>&1 &
  pids+=($!);labels+=("L$L")
done
fail=0
for i in "${!pids[@]}"; do
  if ! wait "${pids[$i]}"; then echo "C8: weight generator ${labels[$i]} FAILED (see $C8_OUT/log_${labels[$i]}.txt)" >&2; fail=1; fi
done
missing=0
for line in "${LINES[@]}"; do
  read -r L degs <<<"$line"
  [[ -s "$C8_OUT/cgamma_L$L.txt" ]] || { echo "C8: missing cgamma_L$L.txt" >&2; missing=1; }
  for N in $degs; do [[ -s "$C8_OUT/cw_L${L}_N${N}.txt" ]] || { echo "C8: missing cw_L${L}_N${N}.txt" >&2; missing=1; }; done
done
(( fail == 0 && missing == 0 )) || exit 1
echo "C8: all required weights present"
