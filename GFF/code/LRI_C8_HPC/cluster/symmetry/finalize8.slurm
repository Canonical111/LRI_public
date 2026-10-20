#!/bin/bash
#SBATCH --job-name=c8x-finalize
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=180G
#SBATCH --time=06:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/c8_hpc/logs/%x_%j.out
# Merge-only closing step of amendment A1, after every lane job of the wave has ended: lane8.py finalize merges every
# batch whose planned checkpoints are all present (exclusive maintenance access; nothing is computed). Required:
# C8X_TOOLS, C8X_QUEUE. Partition at submission (defq).
set -eo pipefail
source /mnt/beegfs/zzheng1/c8_hpc/code/symmetry/env_symmetry.sh
set -u
: "${C8X_TOOLS:?}" "${C8X_QUEUE:?}"
S=/local1/zzheng1_c8x_finalize_$SLURM_JOB_ID;mkdir -p "$S";trap 'rm -rf "$S"' EXIT
"$C8_PYTHON" "$C8X_TOOLS/tools/lane8.py" finalize --queue "$C8X_QUEUE" --c8-root "$C8_ROOT" --scratch "$S"
