#!/bin/bash
#SBATCH -J lri2d_an
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --array=0-23%12
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=32G
#SBATCH -t 12:00:00
#SBATCH -o <SCRATCH>/lri2d/logs/prod_an_%A_%a.out
# FIT_MODEL_2D §4.1: one precision_analysis per (s, block): 500 bootstrap draws, seed 571239, min-ess 0.2. Tasks 0-7 b=2000, 8-15 b=1000, 16-23 b=4000.
set -uo pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd <CODE_2D>/code || exit 1
CAMP=<SCRATCH>/lri2d/prod2d; LOGS=<SCRATCH>/lri2d/logs
S=(1.05 1.1 1.2 1.3 1.4 1.5 1.6 1.7); B=(2000 1000 4000)
i=$SLURM_ARRAY_TASK_ID; s=${S[$((i%8))]}; b=${B[$((i/8))]}; OUT=$CAMP/analysis_b${b}_s$s
[ -s $CAMP/hist_b$b/index.json ] || { echo "no packed index for b=$b; exit 65"; exit 65; }
[ -e $OUT ] && { echo "$OUT already exists (immutable record); refusing to overwrite; exit 66"; exit 66; }
echo "$(date) analysis s=$s b=$b -> $OUT"
python3 precision_analysis.py $CAMP/hist_b$b/index.json --dim 2 --s $s --bootstrap 500 --seed 571239 --min-ess 0.2 --out $OUT > $LOGS/prod_an_b${b}_s$s.log 2>&1
rc=$?; echo "$(date) analysis s=$s b=$b exit $rc"; [ -s $OUT/results.json ] && echo "results.json written" || echo "NO results.json"; exit $rc
