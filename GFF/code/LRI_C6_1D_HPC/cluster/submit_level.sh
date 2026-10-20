#!/bin/bash
# submit_level.sh L N MODE STRATUM KIND PERTURB MOD CHUNK [sbatch options...]
# Submits an array of c6sum tasks (CHUNK sectors each) and a dependent merge into $C6_LEVELS (canonical name).
# Requires the current validation approval (cluster/validate_all.sh). THROTTLE (default 5) caps concurrent tasks.
# Standalone use (not from production.sh) takes the campaign lock and requires an otherwise idle campaign, so that it
# can neither duplicate nor overlap a stage.
set -euo pipefail
source "$(dirname "$0")/env.sh"
if [[ ${C6_CAMPAIGN_LOCKED:-0} != 1 ]]; then
  c6_lock campaign
  a=$(c6_active_jobs '^c6(_|m_|rep|cal|l5|prod|prep|val_|valsum)') || exit 1
  (( a == 0 )) || { echo "$a c6 jobs queued or running; standalone submission needs an idle campaign (use production.sh)" >&2; exit 1; }
fi
c6_require_approval
L=$1 N=$2 MODE=$3 STRATUM=$4 KIND=$5 PERTURB=$6 MOD=$7 CHUNK=$8; shift 8
(( L == 6 )) && c6_require_continuation "$N"   # degrees above 16 (and their replicates) need a 'continue' decision
NSECT=$(( L == 6 ? 360 : 60 )); NT=$(( (NSECT + CHUNK - 1) / CHUNK ))
STEM=L${L}_${MODE}_${STRATUM}_N${N}.${KIND}; (( PERTURB )) && STEM+=.pert$PERTURB; (( MOD == 10 )) && STEM+=.mod10
SUBSET=all; (( MOD == 10 )) && SUBSET=mod10
set +e; c6_level_status "$STEM"; st=$?; set -e
case $st in
  0) echo "level $STEM already merged and matches the approval; skipping"; exit 0 ;;
  1) echo "level $STEM exists but does not match the approval or is corrupt; refusing" >&2; exit 1 ;;
esac
n=$(c6_active_jobs "^c6(_|m_)$STEM\$") || exit 1
(( n == 0 )) || { echo "jobs for $STEM are still queued or running; not resubmitting" >&2; exit 1; }
# Missing level: submit; existing partial outputs in $C6_RUNS/$STEM are resumed by the engine (same fingerprint).
J=$(sbatch --parsable -J c6_$STEM --array=0-$((NT-1))%${THROTTLE:-5} \
     --export=ALL,C6_CODE=$C6_CODE,L=$L,N=$N,MODE=$MODE,STRATUM=$STRATUM,KIND=$KIND,PERTURB=$PERTURB,MOD=$MOD,CHUNK=$CHUNK,STEM=$STEM \
     "$@" "$C6_CODE/cluster/task.slurm")
M=$(sbatch --parsable -J c6m_$STEM -p sharedq -N 1 -n 1 -c 2 --mem=4G -t 00:30:00 --dependency=afterok:$J --kill-on-invalid-dep=yes \
     -o "$C6_LOGS/%x_%j.out" --export=ALL,C6_CODE=$C6_CODE \
     --wrap "source $C6_CODE/cluster/env.sh; python $C6_CODE/tools/merge.py --leveldir $C6_LEVELS $C6_RUNS/$STEM/part_*.jsonl --subset $SUBSET")
echo "$(date +%F_%T) $STEM array=$J tasks=$NT chunk=$CHUNK merge=$M opts=$*" | tee -a "$C6_HOME/SUBMITTED.txt"
