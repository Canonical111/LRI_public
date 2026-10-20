#!/bin/bash
# Template (public release) of the job that produced spectral runs A and B of K3, L3, Z3 (hp_masters_d3.py).
# Production: one 64-core AMD EPYC node, run A 471 s (args run_A_dps50.json 50 64 44 64),
#             run B 657 s (args run_B_dps56.json 56 80 52 72), 2026-10-02.
# Placeholders: <ACCOUNT>, <PARTITION>, <ENV_SETUP> (a command that puts python3 with mpmath on PATH),
#               <CODE> (a copy of GFF/code/LRI_C5_d3).
# Usage: sbatch -J c5d3-A c5d3_masters.slurm run_A_dps50.json 50 64 44 64
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --exclusive
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=%x-%j.out
<ENV_SETUP>
cd <CODE>
echo "start $(date -Is) args $*"
OPENBLAS_NUM_THREADS=1 python3 -u hp_masters_d3.py "$@"
echo "end $(date -Is) rc=$?"
