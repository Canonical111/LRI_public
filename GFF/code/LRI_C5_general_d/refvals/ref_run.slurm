#!/bin/bash
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --exclusive
#SBATCH --mem=96G
#SBATCH --time=06:00:00
#SBATCH --output=%x-%j.out
# usage: sbatch -J NAME ref_run.slurm OUT.json d DPS SPINS KMAX M PART RHO [RHO_OFF]
source $HOME/c7d3_prod/env.sh
cd $HOME/c5gd_ref
echo "host $(hostname) start $(date -Is) args $*"
OPENBLAS_NUM_THREADS=1 python3 -u hp_general_d.py "$@"
echo "end $(date -Is) rc=$?"
