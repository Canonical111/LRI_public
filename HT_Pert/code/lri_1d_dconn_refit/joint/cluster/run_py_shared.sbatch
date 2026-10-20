#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15G
#SBATCH -J r72-joint-py
#SBATCH -o <SCRATCH>/dconn_refit72_joint/logs/%x_%j.out
# usage: sbatch -t 01:00:00 run_py_shared.sbatch SCRIPT [ARGS...]   (runs in $W/code)
set -eo pipefail
W=<SCRATCH>/dconn_refit72_joint
PY=<HOME>/kgen_vbjet/venv/bin/python
export DCONN_CORRECTED=$W/data/delta_v1_hi72_corrected.json
export DCONN_VARIANTS_FULL=$W/data/variants_full_hi72.json
export DCONN_OLD_CORRECTED=$W/data/old/delta_v1_corrected.json
export DCONN_OLD_VARIANTS_FULL=$W/data/old/variants_full.json
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
echo "host $(hostname) $(date) script $*"
cd $W/code
"$@"
date; echo DONE
