#!/bin/bash
#SBATCH -p defq -N 1 --exclusive --mem=180G -t 12:00:00
#SBATCH -o /mnt/beegfs/zzheng1/lri_c6_1d/logs/%x_%j.out
# Runs a list of small levels sequentially on one node, each in one engine invocation, then merges each.
# SPECS="L N MODE STRATUM KIND PERTURB MOD;L N ..." (semicolon-separated). Levels already merged are skipped.
set -euo pipefail
source "$C6_CODE/cluster/env.sh"
: "${SPECS:?}"
c6_require_approval
cd "$C6_CODE"; T=$(phys_alloc)
IFS=';' read -ra list <<< "$SPECS"
for spec in "${list[@]}"; do
  read -r L N MODE S K P M <<< "$spec"
  (( L == 6 )) && c6_require_continuation "$N"
  stem=L${L}_${MODE}_${S}_N${N}.${K}; (( P )) && stem+=.pert$P; (( M == 10 )) && stem+=.mod10
  sub=all; (( M == 10 )) && sub=mod10; bin=bin/c6sum; [[ $K == ld ]] && bin=bin/c6sum_ld
  set +e; c6_level_status "$stem"; st=$?; set -e
  (( st == 0 )) && { echo "have $stem (matches the approval)"; continue; }
  (( st == 1 )) && { echo "$stem exists but does not match the approval; refusing" >&2; exit 1; }
  mkdir -p "$C6_RUNS/$stem"; nsect=$(( L == 6 ? 360 : 60 ))
  /usr/bin/time -f "$stem %e s %M KB" $bin $L $N $T "$C6_DATA" $MODE --out "$C6_RUNS/$stem/part_000_$(printf %03d $nsect).jsonl" --first 0 --stop $nsect --mod $M --stratum $S --perturb $P 2> "$C6_RUNS/$stem/engine.err" || { tail -3 "$C6_RUNS/$stem/engine.err"; exit 1; }
  tail -1 "$C6_RUNS/$stem/engine.err"
  python tools/merge.py --leveldir "$C6_LEVELS" "$C6_RUNS/$stem"/part_*.jsonl --subset $sub
done
echo "batch done $(date)"
