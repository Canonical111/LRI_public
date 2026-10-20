#!/bin/bash
#SBATCH --job-name=xchk-c5
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -c 64
#SBATCH --mem=200G
#SBATCH -t 04:00:00
#SBATCH -o <SCRATCH>/xchk_c5/cfit_blind/slurm-%j.out
set -euo pipefail
cd <SCRATCH>/xchk_c5/cfit_blind
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
echo "host $(hostname) start $(date)"
sha256sum data/*.npz xfit.py tasks3.jsonl
NP=$(nproc); echo nproc $NP
/cm/shared/apps/anaconda3/2023.07-2/bin/python xfit.py tasks3.jsonl results_${SLURM_JOB_ID}.jsonl data $NP
echo "end $(date)"
