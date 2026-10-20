#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:10:00 --no-requeue
#SBATCH -J c8d2-r5-lanes
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# R5b development check on one exclusive Expanse compute node: r5b_lanes_probe.py (the lane worker's and the sweep's
# default shapes on the real sysfs topology) against the tools of the export C8_PACKAGE. The probe script is passed as
# C8_PROBE (a copy outside the export, sha256 recorded). Expected wall about 1 minute.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_PROBE=<path of r5b_lanes_probe.py> sbatch --export=ALL r5b_probe.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_PROBE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r5lanes.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node' "$E/node.txt"
sha256sum "$C8_PROBE" "$C8_PACKAGE/tools/lanes.py" "$C8_PACKAGE/tools/sweep.py" "$C8_PACKAGE/tools/common.py" | tee "$E/sources.sha256"
cd "$C8_PACKAGE" || exit 64
python3 -B "$C8_PROBE" --output "$E/lanes_probe.json"; status=$?
echo "finished $(date -Is), status $status"; exit $status
