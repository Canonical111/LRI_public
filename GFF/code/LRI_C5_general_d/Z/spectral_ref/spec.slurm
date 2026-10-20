#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive --mem=200G
#SBATCH -t 04:00:00
#SBATCH -J zspec_ref
#SBATCH -o <SCRATCH>/c5_gend/Z/spectral_ref/spec_%j.out
# independent spectral references (C63d's hp_general_d.py, copied unchanged) at extra dimensions
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5_gend/Z/spectral_ref
PY=~/c5d2/venv/bin/python
echo "host $(hostname) start $(date)"
run() { SLURM_CPUS_PER_TASK=32 OPENBLAS_NUM_THREADS=1 $PY -u hp_general_d.py spec_b_$1.json $2 45 48 52 64 b $3 0.05 > log_$1.txt 2>&1; }
run 4o3 4/3 0.055 & run 1.75 1.75 0.07 & wait
run 8o3 8/3 0.11 & run 3.5 3.5 0.14 & wait
run 3.75 3.75 0.15 & run 0.7 0.7 0.004 & wait
echo "end $(date)"
