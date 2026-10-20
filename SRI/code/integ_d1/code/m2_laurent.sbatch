#!/bin/bash
#SBATCH --job-name=integ-m2laur
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --exclude=cn112
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=<SCRATCH>/lri_integ/logs/%x_%j.out
# usage: sbatch m2_laurent.sbatch LEVEL DPS RAD NPTS PARITY
cd <SCRATCH>/lri_integ/code || { echo 'FAIL: cannot cd'; exit 1; }
export OMP_NUM_THREADS=1
<HOME>/envs/lri_c2/py3.13-mamba/bin/python m2_laurent_driver.py ../results/m2_laurent_L$1_d$2_r$3_n$4_p$5.jsonl $1 $2 $3 $4 40 $5
rc=$?
if [ $rc -ne 0 ]; then echo "FAIL: driver exit $rc"; exit $rc; fi
echo "done $(date)"
