#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15G
#SBATCH -t 0-04:00:00
#SBATCH -J e2e_dump
#SBATCH -o <SCRATCH>/c5_gend/joint/numerics-end-to-end/dump_%j.out
module load python/3.11
cd <SCRATCH>/c5_gend/joint/numerics-end-to-end
~/c5d2/venv/bin/python dump_samples.py <SCRATCH>/c5_gend 60 samples_dps60.json
