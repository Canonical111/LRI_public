#!/bin/bash
#SBATCH -N 1 --exclusive
#SBATCH --mem=245G
#SBATCH --signal=B:USR1@900
#SBATCH -o /mnt/beegfs/zzheng1/lri_dressed/logs/%x_%j.out
# One node-packing launcher. Submit with cluster/symmetry/submit.py (sets -p, -t, -J and the env).
set -euo pipefail
source "${LRI_CODE_DIR:?set LRI_CODE_DIR}/cluster/symmetry/env.sh"
echo "job $SLURM_JOB_ID on $(hostname): campaign $LRI_CAMPAIGN code $(cat "$LRI_CODE/GIT_SHA" 2>/dev/null)"
# exec: the launcher is the batch step's main process, so --signal=B:USR1 reaches it directly.
exec python "$LRI_CODE/scripts/pack_node.py" --campaign "$LRI_CAMPAIGN" --receipt "$LRI_RECEIPT" ${LRI_PACK_ARGS:-}
