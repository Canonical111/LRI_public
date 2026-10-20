#!/bin/bash
#SBATCH -A <ACCOUNT> --nodes=1 --ntasks-per-node=1
#SBATCH -o <SCRATCH>/temp_project/lri_ht/logs/%x_%j.out
# One campaign lane. Partition, QOS, cores, memory, wall limit and name come from submit_cutoffs.py on the sbatch
# command line; CODE (the frozen checkout) and LANE (the lane JSON) come through --export.
[[ -n "${CODE:-}" && -f "$CODE/GIT_SHA" && -f "${LANE:-}" ]] || { echo "CODE and LANE required (submit with submit_cutoffs.py)" >&2; exit 2; }
source "$CODE/cluster/expanse/env.sh"
cd "$CODE"
echo "lane $LANE rev $(cat GIT_SHA) node $(hostname) cpus ${SLURM_CPUS_PER_TASK:-?} mem ${SLURM_MEM_PER_NODE:-?}M"
exec python cluster/expanse/run_lane.py "$LANE"
