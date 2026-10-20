#!/bin/bash
# Template (public release) of the jobs of spectral run C (110 digits): one Cauchy circle per job (hp_part.py).
# Production: one 64-core AMD EPYC node per part, 2026-10-02:
#   part b (b-circle, W3 and W4):  run_C_b.json 110 128 110 72 b 0.02   1593 s
#   part t (tau-circle, K3):       run_C_t.json 110 128 110 72 t 0.02   3548 s
# then, on any machine:  python3 hp_combine.py run_C_b.json run_C_t.json run_C_combined.json
# Placeholders: <ACCOUNT>, <PARTITION>, <ENV_SETUP>, <CODE> as in c5d3_masters.slurm.
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --exclusive
#SBATCH --mem=96G
#SBATCH --time=24:00:00
#SBATCH --output=%x-%j.out
<ENV_SETUP>
cd <CODE>
echo "start $(date -Is) args $*"
OPENBLAS_NUM_THREADS=1 python3 -u hp_part.py "$@"
echo "end $(date -Is) rc=$?"
