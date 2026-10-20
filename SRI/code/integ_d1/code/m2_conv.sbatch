#!/bin/bash
#SBATCH --job-name=integ-m2conv
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --exclude=cn112
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=<SCRATCH>/lri_integ/logs/%x_%j.out
cd <SCRATCH>/lri_integ/code
export OMP_NUM_THREADS=1
<HOME>/envs/lri_c2/py3.13-mamba/bin/python m2_conv_driver.py ../results/m2_conv_${SLURM_JOB_ID}.jsonl
