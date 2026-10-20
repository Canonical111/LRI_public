#!/bin/bash
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --exclusive
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=%x-%j.out
# usage: sbatch -J NAME d2check.slurm OUT.json key=value ...
source $HOME/c7d3_prod/env.sh
cd $HOME/c5d3_d2check
echo "host $(hostname) start $(date -Is) args $*"
OPENBLAS_NUM_THREADS=1 python3 -u hp_masters_d2.py "$@"
echo "end $(date -Is) rc=$?"
