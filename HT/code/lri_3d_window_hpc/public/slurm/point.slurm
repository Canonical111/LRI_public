#!/bin/bash
# One production step with the point driver, outside the Expanse campaign layer. Take the argv of the step from
# data/HT_3d/campaigns/<campaign>/manifest.json (lanes[].steps[].argv) and replace its paths:
#   --basis  the lane's teacher_L6.json      --seed  the previous record of the lane
#   --cache-dir  your static cache (N = 20)  --output  a new file (the driver refuses to overwrite)
# Resources used in production: N <= 16: 4-16 cores, <= 16 GB; N = 18: 16 cores, 64 GB (34-74 min);
# N = 20 scalar only: 32 cores, 240 GB (27-104 min after the static cache exists).
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION>
#SBATCH -N 1 -n 1 -c 16
#SBATCH --mem=64G
#SBATCH -t 10:00:00
#SBATCH -J ht3d-point
#SBATCH -o ht3d-point_%j.out
set -euo pipefail
cd <HT>/code/lri_3d_window_hpc
source <VENV>/bin/activate
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK} OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
# example: grid18, Ds = 0.7, N = 18 (memory limit, bath limit and diagnostics as in that step's manifest argv)
python -B code/hpc_run.py --L 18 --x 0.7 --nz 16 --window vacuum --window-mode consistent --backend tensor \
  --diagnostics first --threads ${SLURM_CPUS_PER_TASK} --memory-limit-gib 58.0 --max-bath-states 50000000 \
  --basis <HT>/data/HT_3d/campaigns/grid18/results/t16/x0.7/teacher_L6.json \
  --seed  <HT>/data/HT_3d/campaigns/grid18/results/t16/x0.7/window_L16.json \
  --output <SCRATCH>/ht3d/rerun/x0.7/window_L18.json
