#!/bin/bash
#SBATCH --job-name=indep2d-cauchy-interior
#SBATCH --partition=amddebugq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/cauchy/logs/interior_%j.log
# usage: sbatch jobs/interior.sbatch "<L list>"
cd /mnt/beegfs/zzheng1/indep2d/cauchy/code
PY=$HOME/indep2d_cauchy/venv/bin/python
export OMP_NUM_THREADS=1
for L in $1; do for s in raw consistent literal; do
  f=/mnt/beegfs/zzheng1/indep2d/cauchy/runs/${s}_L${L}_base.json
  [ -s $f ] && $PY check_interior.py $f &
done; done
wait
echo interior finished
