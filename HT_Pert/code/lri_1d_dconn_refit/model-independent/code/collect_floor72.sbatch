#!/bin/bash
#SBATCH -N 1 --exclusive
#SBATCH --mem=180G
#SBATCH -J mi72-collect-floor
# refit72: light analysis of the floor-level member reruns (runlist72_qfloor.txt).
source /etc/profile.d/modules.sh
module load anaconda3/2023.07-2
set -eo pipefail
W=${W:-<SCRATCH>/dconn_refit72_mi}; O=$W/out; C=$W/code
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
while read -r TAG CEN REST; do
  [ -z "$TAG" ] && continue
  env DCONN_CENTRAL=$CEN DCONN_CORRECTED=$W/data/corrected.json DCONN_VARIANTS=$W/data/variants.json MI_LIGHT=1 MI_OUT=analysis_light python3 $C/analyze.py $O/$TAG > $O/$TAG/analysis_light.txt 2>&1 &
done < $C/runlist72_qfloor.txt
wait; date; echo DONE
