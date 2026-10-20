#!/bin/bash
#SBATCH --job-name=c8x-plan
#SBATCH --partition=debugq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=180G
#SBATCH --time=01:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/c8_hpc/logs/%x_%j.out
# Plans the extension batches of amendment A1 (labels, seeds and paths from extension.json) with the frozen
# production tools (c0ffa63) and the frozen bundle, and checks them (plan_ext.py). Required: C8X_EXTENSION.
# Optional: C8X_INPUTS (input snapshot to copy from; default b1's; every file is hash-checked against the bundle).
set -eo pipefail
source /mnt/beegfs/zzheng1/c8_hpc/code/symmetry/env_symmetry.sh
set -u
: "${C8X_EXTENSION:?}"
"$C8_PYTHON" $C8W/code/symmetry/plan_ext.py "$C8X_EXTENSION" "$C8W/runs/prod4/b1" "${C8X_INPUTS:-$C8W/runs/prod4/b1/inputs}"
