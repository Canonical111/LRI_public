#!/bin/bash
#SBATCH --job-name=indep2d-cauchy-timing
#SBATCH --partition=amddebugq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/cauchy/logs/timing_%j.log
cd /mnt/beegfs/zzheng1/indep2d/cauchy/code
PY=$HOME/indep2d_cauchy/venv/bin/python
export OMP_NUM_THREADS=1
lscpu | grep -E "Model name|^CPU\(s\)"
$PY timing.py 6 &
$PY timing.py 8 &
wait
