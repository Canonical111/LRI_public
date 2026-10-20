#!/bin/bash
#SBATCH --job-name=revL2spec
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=spec_%j.out
export PYTHONPATH=<HOME>/lri5/pylib
cd $SLURM_SUBMIT_DIR
for x in 2/5 1/2 3/5; do python3 spec_job.py $x 2000 75 32; done
