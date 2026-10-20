#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15G
#SBATCH -t 0-12:00:00
#SBATCH -J e2e_k3
#SBATCH -o <SCRATCH>/c5_gend/joint/numerics-end-to-end/k3_%j.out
cd <SCRATCH>/c5_gend/joint/numerics-end-to-end
export SLURM_CPUS_PER_TASK=8
~/c5d2/venv/bin/python kjet3.py 1.5,2.5,3 0.08 48 30 400 72 k3_jets.json
