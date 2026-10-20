#!/bin/bash
# make test and make replay of lri_3d_hpc on one node (about 2 min, 1 GB, 4 threads). Replace the placeholders.
#SBATCH -J lri3dhpc-test
#SBATCH -p <PARTITION>
#SBATCH -A <ACCOUNT>
#SBATCH -N 1 -c 8 --mem=8G -t 00:30:00
#SBATCH -o lri3dhpc-test_%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"                      # submit from HT_Pert/code/lri_3d_hpc
PY=${PY:-python3}                            # Python 3.12 with public/requirements.txt
export CXX=${CXX:-g++}                       # C++17 with OpenMP
export TMPDIR=${TMPDIR:-/tmp}                # node-local: the kernel library is built there
make -f public.mk test PY="$PY" WORK=.work_$SLURM_JOB_ID
make -f public.mk replay PY="$PY" WORK=.work_$SLURM_JOB_ID
