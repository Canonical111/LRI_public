#!/bin/bash
#SBATCH -p amddebugq
#SBATCH -N 1 --exclusive
#SBATCH --mem=240G
#SBATCH -t 00:55:00
#SBATCH -J lri-dressed-validate
#SBATCH -o /mnt/beegfs/zzheng1/lri_dressed/logs/%x_%j.out
# Staged release validation; the receipt is written only after every stage passes.
#   sbatch --export=ALL,LRI_CODE_DIR=$HOME/lri_dressed/code/<sha> <code>/cluster/symmetry/validate.sbatch
set -euo pipefail
source "${LRI_CODE_DIR:?set LRI_CODE_DIR to the frozen code}/cluster/symmetry/env.sh"
out="$LRI_ROOT/validation/$SLURM_JOB_ID"; mkdir -p "$out"
echo "code $LRI_CODE ($(cat "$LRI_CODE/GIT_SHA" 2>/dev/null)) -> $out"
cd "$LRI_CODE"
exec python scripts/validate_release.py --threads 8 --output "$out/receipt.json" --workdir "$out/stages" \
     --baseline "${LRI_BASELINE:-$HOME/lri_dressed/code/e637dfd}"
