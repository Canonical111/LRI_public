#!/bin/bash
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH --output=%x-%j.out
# usage: sbatch -J NAME runA.slurm DPS "d1 d2 ..." "L1 L2 ..."
cd $HOME/kgen_refcheck
DPS=$1; DS=$2; LS=$3
echo "host $(hostname) start $(date -Is) dps $DPS ds $DS Ls $LS"
for d in $DS; do for L in $LS; do
  OPENBLAS_NUM_THREADS=1 ./venv/bin/python -u routeA_spectral.py runs/A_d${d}_dps${DPS}_L${L}.json $d $DPS $L 64
  echo "--- done d=$d L=$L $(date -Is)"
done; done
echo "end $(date -Is)"
