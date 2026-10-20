#!/bin/bash
# One comparison of the clean-room solver with a production record (run_compare.py). The shipped ones are listed in
# tasks.txt as "N scheme Ds". N = 12 needs up to about 3 h and 16-24 GB; N <= 10 a few minutes.
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION>
#SBATCH -N 1 -n 1 -c 8
#SBATCH --mem=24G
#SBATCH -t 04:00:00
#SBATCH -J ht3d-indep
#SBATCH -o ht3d-indep_%j.out
set -euo pipefail
cd <HT>/code/lri_3d_window_indep
source <VENV>/bin/activate
export OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 OMP_NUM_THREADS=4
L=${L:-12}; MODE=${MODE:-window}; X=${X:-0.6}
mkdir -p .work
python -u -B run_compare.py --L $L --x $X --mode $MODE --out .work/cmp_L${L}_${MODE}_x${X}.json
