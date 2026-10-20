#!/bin/bash
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH --output=%x-%j.out
source $HOME/c7d3_prod/env.sh
cd $HOME/c5d3_L3
echo "host $(hostname) start $(date -Is) args $*"
OPENBLAS_NUM_THREADS=1 python3 -u pieces.py "$@" 64
echo "end $(date -Is) rc=$?"
