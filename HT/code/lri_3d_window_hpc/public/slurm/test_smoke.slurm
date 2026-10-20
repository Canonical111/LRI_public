#!/bin/bash
# make test + make smoke of lri_3d_window_hpc on one node (about 6 min). Fill the placeholders.
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION>
#SBATCH -N 1 -n 1 -c 4
#SBATCH --mem=16G
#SBATCH -t 00:30:00
#SBATCH -J ht3d-test
#SBATCH -o ht3d-test_%j.out
set -euo pipefail
cd <HT>/code/lri_3d_window_hpc          # the published HT folder
source <VENV>/bin/activate              # Python with public/requirements.txt
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK} OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
make -f public.mk test
make -f public.mk smoke
