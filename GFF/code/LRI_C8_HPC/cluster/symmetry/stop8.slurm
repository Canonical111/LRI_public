#!/bin/bash
#SBATCH --job-name=c8x-stop
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --output=/mnt/beegfs/zzheng1/c8_hpc/logs/%x_%j.out
# Pre-registered end of the amendment-A1 wave: submitted together with the lanes with --begin=T0+48h; it publishes the
# queue's STOP file, after which workers finish their current element, merge completed batches and exit.
# Required: C8X_QUEUE. Partition at submission (sharedq,debugq).
set -euo pipefail
: "${C8X_QUEUE:?}"
[[ -f "$C8X_QUEUE/order.json" ]] || { echo "C8X: no queue at $C8X_QUEUE" >&2; exit 64; }
printf '{"time":"%s","job":"%s","reason":"pre-registered 48 h end of the wave"}\n' "$(date -Is)" "$SLURM_JOB_ID" > "$C8X_QUEUE/STOP.tmp.$$"
mv -n "$C8X_QUEUE/STOP.tmp.$$" "$C8X_QUEUE/STOP";rm -f "$C8X_QUEUE/STOP.tmp.$$"
echo "C8X: STOP published at $(date -Is)";ls -l "$C8X_QUEUE/STOP"
