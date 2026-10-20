#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=170G
#SBATCH --time=00:30:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# usage: sbatch ce_combine.sbatch OUT CHUNK1 CHUNK2 ...   (in ce_wc/)
set -uo pipefail
cd /mnt/beegfs/zzheng1/indep2d/residual_log/ce_wc
echo "host $(hostname) start $(date)"
~/indep2d_c4/venv/bin/python ce_combine.py "$@"
echo "end $(date)"
