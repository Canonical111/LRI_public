#!/bin/bash
# Amendment A2 (docs/EXTENSION_A2.md) as changed by A3 (docs/EXTENSION_A3.md): complete the planned batches b10-b14
# with no deadline. On symmetry, one queue runs/ext1/queue_a2 holding b10 and b11 only (A3: b12-b14 run on Expanse),
# published only after the A1 wave has ended and its close snapshot is recorded. Usage (login node):
#   submit_a2.sh arm                 submit the A1-close job (debugq, afterany on every A1 lane job): it runs
#                                    'submit_a2.sh close' and then, whatever close returned, the A1-close combination
#                                    (which itself requires the snapshot)
#   submit_a2.sh lanes PARTITION N [BEGIN]   submit N A2 lane jobs (lane8_a2.slurm; they wait for queue_a2), optionally
#                                    with --begin=BEGIN; repeatable; job ids appended to runs/ext1/a2_jobs_<PARTITION>.txt
# Inside the A1-close job only:
#   submit_a2.sh close               A1-close snapshot (retried while accounting catches up), then queue_a2 (b10 b11)
#                                    built in a staging directory and published by an atomic rename
# Wave-wide stop of A2: touch runs/ext1/A2_CANCEL (waiting lanes exit; 'close' still records A1 but publishes no
# queue) and, once queue_a2
# exists, also touch runs/ext1/queue_a2/STOP (running workers finish their current element and exit).
# Tools are the A1-approved 15a110e; code/symmetry must point at its cluster/symmetry.
set -eo pipefail
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
W=/mnt/beegfs/zzheng1/c8_hpc;T=$W/code/15a110e;R=$W/runs/ext1;Q=$R/queue_a2;S=$R/queue_a2.staging
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
[[ -f $T/tools/lane8.py && "$(readlink $W/code/symmetry)" == "15a110e/cluster/symmetry" ]] || { echo "tools 15a110e not deployed as code/symmetry" >&2; exit 64; }
source $W/code/symmetry/env_symmetry.sh >/dev/null 2>&1
a1jobs(){ cat $R/lane_jobs_longq.txt $R/lane_jobs_defq.txt $R/lane_jobs_preq.txt | grep -E '^[0-9]+$' | paste -sd: ; }
sanitize(){ for v in $(compgen -e | grep -E '^(C8X_|SBATCH_)' || true); do unset "$v"; done; }
case "${1:-}" in
arm)
  [[ -z "${SLURM_JOB_ID:-}" ]] || { echo "run from the login node" >&2; exit 64; }
  [[ ! -e $R/a2_close_job.txt ]] || { echo "A1-close job already submitted: $(cat $R/a2_close_job.txt)" >&2; exit 64; }
  sanitize;cd $W
  j=$(sbatch --parsable -p debugq -N 1 --exclusive --mem=180G -t 01:00:00 --job-name=c8x-a1close --dependency=afterany:$(a1jobs) \
      -o $W/logs/%x_%j.out --export=ALL --wrap "bash $HERE/a1_close_job.sh")
  echo "$j" > $R/a2_close_job.txt;echo "A1-close job $j (afterany on the A1 lane jobs)";;
close)
  [[ -n "${SLURM_JOB_ID:-}" ]] || { echo "close runs inside the A1-close job" >&2; exit 64; }
  ok=0 # the A1 record is made whatever A2's fate: A2_CANCEL only suppresses publication of the A2 queue
  for i in $(seq 1 15); do # the dependency fires when the A1 jobs end; accounting may lag by a few seconds or minutes
    if "$C8_PYTHON" "$HERE/a1_close_snapshot.py";then ok=1;break;fi
    echo "snapshot attempt $i failed; retrying in 60 s" >&2;sleep 60
  done
  (( ok )) || { echo "A1-close snapshot not published: queue_a2 stays unpublished" >&2; exit 1; }
  if [[ -e $Q ]];then echo "queue_a2 already published";exit 0;fi
  if [[ -e $R/A2_CANCEL ]];then echo "A2_CANCEL present: A1 recorded, A2 queue not published";exit 0;fi
  rm -rf $S # an interrupted earlier build; nothing reads the staging directory
  # A3: b12-b14 are not queued on symmetry (they run on Expanse); the staged queue must hold exactly b10 and b11
  "$C8_PYTHON" $T/tools/lane8.py queue --queue $S --costs $W/costs_b1to4_seconds16.json $R/b10 $R/b11
  "$C8_PYTHON" -c "import json,sys;d=json.load(open('$S/order.json'));L=sorted({e['label'] for e in d['elements']});sys.exit(0 if len(d['elements'])==996 and L==['b10','b11'] else 1)" || { echo "staged queue malformed" >&2; exit 1; }
  if [[ -e $R/A2_CANCEL ]];then rm -rf $S;echo "A2_CANCEL present: A1 recorded, A2 queue not published";exit 0;fi
  mv -T $S $Q # atomic rename on the same filesystem: workers see either no queue or the complete one
  echo "A2 queue_a2 (b10-b11; amendment A3) published $(date -Is) by job $SLURM_JOB_ID after the A1-close snapshot (sha256 $(sha256sum $W/results/C8_A1_close/a1_close_snapshot.json | cut -d' ' -f1)); tools 15a110e mode ht; no deadline" >> $R/A2_T0.txt
  cat $R/A2_T0.txt;;
lanes)
  [[ -z "${SLURM_JOB_ID:-}" ]] || { echo "run from the login node" >&2; exit 64; }
  P=${2:?partition};N=${3:?count};B=${4:-}
  [[ "$N" =~ ^[1-9][0-9]?$ ]] || { echo "count must be 1-99" >&2; exit 64; }
  [[ ! -e $R/A2_CANCEL ]] || { echo "A2_CANCEL present" >&2; exit 64; }
  [[ ! -e $Q ]] || [[ -f $Q/order.json && ! -e $Q/deadline.json && ! -e $Q/STOP && ! -e $Q/MAINTENANCE ]] || { echo "queue_a2 not ready (deadline, STOP or MAINTENANCE)" >&2; exit 64; }
  # Every inherited C8X_* and SBATCH_* variable is removed; exactly the A2 pins are exported and checked, the job name is
  # given on the command line and each submitted job's name and partition are checked with squeue.
  sanitize;export C8X_TOOLS="$T" C8X_QUEUE="$Q" C8X_MODE=ht
  [[ "$(env | grep '^C8X_' | sort | tr '\n' '|')" == "C8X_MODE=ht|C8X_QUEUE=$Q|C8X_TOOLS=$T|" ]] || { echo "C8X_* environment not as pinned" >&2; exit 64; }
  case $P in
    longq) X=(-p longq --time=7-00:00:00);;
    defq) X=(-p defq --time=1-00:00:00);;
    preq) X=(-p preq --requeue --exclude=cn[043-068] --time=1-00:00:00);;
    *) echo "partition must be longq, defq or preq" >&2; exit 64;;
  esac
  [[ -z "$B" ]] || X+=(--begin="$B")
  cd $W
  for i in $(seq 1 $N); do
    j=$(sbatch --parsable --job-name=c8x-lane "${X[@]}" --export=ALL "$HERE/lane8_a2.slurm")
    echo "$j" >> $R/a2_jobs_$P.txt
    got=$(squeue -h -j "$j" -o '%j|%P' 2>/dev/null || true)
    [[ "$got" == "c8x-lane|$P" ]] && echo "$j c8x-lane $P" || echo "WARNING: job $j shows '$got', expected 'c8x-lane|$P': inspect" >&2
  done;;
*) echo "usage: submit_a2.sh arm | lanes PARTITION N [BEGIN] | close" >&2; exit 64;;
esac
