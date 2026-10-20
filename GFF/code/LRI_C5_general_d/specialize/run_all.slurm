#!/bin/bash
#SBATCH -J c5spec
#SBATCH -p amdq
#SBATCH --exclusive
#SBATCH --mem=200G
#SBATCH -t 04:00:00
#SBATCH -o results/run_all_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
PY=~/c5d2/venv/bin/python
cd <SCRATCH>/c5_gend/specialize/spec
$PY check_taylor.py 30 > results/check_taylor_dps30.log 2>&1 &
$PY c5_assembly.py 50 > results/c5_assembly_dps50.log 2>&1 &
$PY gamma_c0.py 80 > results/gamma_c0_dps80.log 2>&1 &
$PY pslq_L.py 110 > results/pslq_L_dps110.log 2>&1 &
$PY check_d3.py 50 > results/check_d3_dps50.log 2>&1 &
wait
