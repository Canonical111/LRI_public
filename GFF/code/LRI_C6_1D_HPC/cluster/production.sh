#!/bin/bash
# production.sh STAGE: production submissions (PLAN.md rev 5, 4.3). Requires the current validation approval and no
# other active c6 production job (one stage at a time; campaign-wide at most 12 concurrent nodes).
#   A      L6 light (double) and hard (long double): N = 10, 12, 14, 16 as sector arrays (10 nodes max); one batch
#          node for N = 6, 8 production, the calibration runs (hard double N = 6, 8, 10, plain and perturbed) and the
#          replicates for N = 6..16; one batch node for L5 long double M = 12..40, the M40 replicate and the
#          double M40 diagnostic. At most 12 nodes.
#   N=<n>  one further L6 degree (n = 18..30), only after decisions/decision_N<n-2>.json (tools/analyze.py with
#          --resources and --decision-dir) says 'continue' for the current N-2 levels: both strata as arrays
#          throttled to 5 tasks each, plus one replicate batch node. At most 11 nodes.
# Retries are idempotent: completed levels matching the approval are skipped, missing ones (re)submitted, partial
# engine outputs resumed; a level that exists but does not match the approval stops the script.
set -euo pipefail
source "$(dirname "$0")/env.sh"
c6_lock campaign; export C6_CAMPAIGN_LOCKED=1
c6_require_approval
active=$(c6_active_jobs '^c6(_|m_|rep|cal|l5|prod|prep|val_|valsum)') || exit 1
(( active == 0 )) || { echo "$active c6 production or validation jobs still queued or running; one stage at a time" >&2; exit 1; }
SUB=$C6_CODE/cluster/submit_level.sh
chunk(){ case $1 in 10|12|14) echo 360 ;; 16) echo 180 ;; 18) echo 120 ;; 20) echo 90 ;; 22) echo 60 ;; 24) echo 45 ;; 26) echo 36 ;; *) echo 30 ;; esac; }
log(){ echo "$(date +%F_%T) $*" | tee -a "$C6_HOME/SUBMITTED.txt"; }
stem_of(){ local L=$1 N=$2 MODE=$3 S=$4 K=$5 P=$6 M=$7 s; s=L${L}_${MODE}_${S}_N${N}.${K}; (( P )) && s+=.pert$P; (( M == 10 )) && s+=.mod10; echo "$s"; }
batch(){ local id spec todo=0 st
  IFS=';' read -ra specs <<< "$2"
  for spec in "${specs[@]}"; do set +e; c6_level_status "$(stem_of $spec)"; st=$?; set -e
    (( st == 1 )) && { echo "$(stem_of $spec) exists but does not match the approval; refusing" >&2; exit 1; }
    (( st == 2 )) && todo=$((todo + 1)); done
  (( todo )) || { log "batch $1: all levels complete; skipped"; return 0; }
  id=$(sbatch --parsable -J "$1" -p "$P" --export=ALL,C6_CODE=$C6_CODE,SPECS="$2" "$C6_CODE/cluster/batch.slurm")
  log "batch $1 job=$id levels_to_do=$todo specs=$2"; }
case ${1:?stage} in
A)
  P=$(c6_partition 12); log "stage A partitions: $P"
  for N in 10 12 14 16; do
    THROTTLE=5 $SUB 6 $N H light dbl 0 1 $(chunk $N) -p $P -t 06:00:00
    THROTTLE=5 $SUB 6 $N H hard ld 0 1 $(chunk $N) -p $P -t 06:00:00
  done
  B="6 6 H light dbl 0 1;6 6 H hard ld 0 1;6 8 H light dbl 0 1;6 8 H hard ld 0 1"
  for N in 6 8 10; do B+=";6 $N H hard dbl 0 1;6 $N H hard dbl 1 1"; done
  for N in 6 8 10 12 14 16; do B+=";6 $N H light dbl 1 10;6 $N H hard ld 1 10"; done
  batch c6prod "$B"
  S5=""; for M in 12 16 20 24 28 32 36 40; do S5+="5 $M H all ld 0 1;5 $M J all ld 0 1;"; done
  S5+="5 40 H all ld 1 1;5 40 J all ld 1 1;5 40 H all dbl 0 1;5 40 J all dbl 0 1"
  batch c6l5 "$S5"
  ;;
N=*)
  N=${1#N=}; (( N >= 18 && N <= 30 && N % 2 == 0 )) || { echo "bad degree $N" >&2; exit 1; }
  c6_require_continuation $N   # the stopping rule must have decided 'continue' at N-2 on the current levels
  P=$(c6_partition 11); log "stage N=$N partitions: $P"
  THROTTLE=5 $SUB 6 $N H light dbl 0 1 $(chunk $N) -p $P -t 08:00:00
  THROTTLE=5 $SUB 6 $N H hard ld 0 1 $(chunk $N) -p $P -t 08:00:00
  batch c6rep$N "6 $N H light dbl 1 10;6 $N H hard ld 1 10"
  ;;
*) echo "unknown stage $1" >&2; exit 1 ;;
esac
