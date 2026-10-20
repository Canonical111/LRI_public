#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH --mem=245G
#SBATCH -t 04:00:00
#SBATCH -J lri-dressed-calibrate
#SBATCH -o /mnt/beegfs/zzheng1/lri_dressed/logs/%x_%j.out
# Calibration of time/RSS per item; arguments after the script name go to calibrate.py, e.g.
#   sbatch --export=ALL,LRI_CODE_DIR=... calibrate.sbatch --cuts 20 24 28 --threads 1 4 --windows none vacuum:consistent --concurrent 16
set -euo pipefail
source "${LRI_CODE_DIR:?set LRI_CODE_DIR}/cluster/symmetry/env.sh"
out="$LRI_ROOT/calibration/$SLURM_JOB_ID"; mkdir -p "$out"
exec python "$LRI_CODE/scripts/calibrate.py" --workdir "$out/work" --output "$out/calibration.json" "$@"
