#!/bin/bash
# Submit one batch of pinned survey jobs (scripts/ppsurvey.slurm, one per node), each through pp.sh sub (a fresh squeue
# snapshot and the H7 check: at most 4 live c8d2-* AMD-pool jobs); prints "<node> <job id>". Batches of at most 4 nodes,
# the next batch only after the previous one ended. Usage: ppsurvey_batch.sh cnA cnB cnC cnD
set -euo pipefail
cd /Users/zheng/Documents/Agent_LRI/LRI_C8_D2_HPC
P=benchmarks/symmetry_2026-10-c8/pilot/scripts
for n in "$@"; do
  id=$(bash $P/pp.sh sub c8d2-ppsv-$n amddebugq "C8_PACKAGE=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e" -p amddebugq --exclude=cn112 --nodelist=$n /mnt/beegfs/zzheng1/c8d2/work/pilot-ba68f401e46e/ppsurvey.slurm 2>/dev/null)
  echo "$n $id"
done
