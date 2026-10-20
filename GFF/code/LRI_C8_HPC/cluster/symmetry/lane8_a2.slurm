#!/bin/bash
#SBATCH --job-name=c8x-lane
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=180G
#SBATCH --time=1-00:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/c8_hpc/logs/%x_%j.out
# Amendment A2 lane job (docs/EXTENSION_A2.md). A2 lane jobs may be submitted before the A2 queue exists (so that they
# take over the nodes the A1 lanes release); the A2 queue is published (atomic rename) only after the A1 wave has ended
# and its close snapshot is recorded. This job waits for runs/ext1/queue_a2/order.json, polling every 60 s for at most
# C8X_WAIT_MAX seconds (default 14400), exits without work if runs/ext1/A2_CANCEL exists, and then runs the unchanged A1
# launcher code/symmetry/lane8.slurm (tools 15a110e) on queue_a2. Required: C8X_QUEUE (must be runs/ext1/queue_a2),
# C8X_TOOLS, C8X_MODE. Partition at submission.
set -eo pipefail
set -u
: "${C8X_QUEUE:?}" "${C8X_TOOLS:?}" "${C8X_MODE:?}"
W=/mnt/beegfs/zzheng1/c8_hpc;R=$W/runs/ext1
[[ "$C8X_QUEUE" == "$R/queue_a2" ]] || { echo "C8X: an A2 lane job serves only $R/queue_a2" >&2; exit 64; }
[[ "$(readlink $W/code/symmetry)" == "15a110e/cluster/symmetry" ]] || { echo "C8X: code/symmetry is not 15a110e" >&2; exit 64; }
waited=0;max=${C8X_WAIT_MAX:-14400}
while [[ ! -f "$C8X_QUEUE/order.json" ]]; do
  [[ ! -e $R/A2_CANCEL ]] || { echo "C8X: $(date -Is) A2_CANCEL present: no work started";exit 0; }
  (( waited < max )) || { echo "C8X: $(date -Is) queue_a2 not published after ${waited}s: exiting without work" >&2;exit 64; }
  (( waited % 900 )) || echo "C8X: $(date -Is) lane job $SLURM_JOB_ID waiting for queue_a2 (${waited}s)"
  sleep 60;waited=$((waited+60))
done
[[ ! -e $R/A2_CANCEL ]] || { echo "C8X: $(date -Is) A2_CANCEL present: no work started";exit 0; }
echo "C8X: $(date -Is) lane job $SLURM_JOB_ID: queue_a2 published, waited ${waited}s"
exec bash $W/code/symmetry/lane8.slurm
