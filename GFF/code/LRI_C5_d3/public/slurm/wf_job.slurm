#!/bin/bash
# Template (public release) for the 160-digit L3 circles and the 250-digit Z3 circles of the workflow folders.
# Production (one 64-core AMD EPYC node each, 2026-10-02):
#   cd <CODE>/wf_L3:  python3 -u pieces.py pA_dps170.json 170 280 116 208 0.04 64     130 s
#                     python3 -u pieces.py pB_dps170.json 170 320 128 240 0.05 64     120 s
#                     then python3 final_form.py pA_dps170.json L3_final_values.json; python3 tdform.py pA_dps170.json
#                     (the stored L3_final_values.json also carries m0 and descriptive fields added afterwards)
#   cd <CODE>/wf_Z3:  python3 -u zcircle.py circA2.json 260 560 170 120 0.001 0      215 s
#                     python3 -u zcircle.py circB2.json 270 700 210 128 0.0015 0.0123   163 s
#                     then python3 derive.py circA2.json derived_circA2.json (and B2)
# Placeholders: <ACCOUNT>, <PARTITION>, <ENV_SETUP>, <CODE>, <SUBDIR> (wf_L3 or wf_Z3).
# Usage: sbatch -J L3pA wf_job.slurm pieces.py pA_dps170.json 170 280 116 208 0.04 64
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=%x-%j.out
<ENV_SETUP>
cd <CODE>/<SUBDIR>
echo "start $(date -Is) args $*"
OPENBLAS_NUM_THREADS=1 python3 -u "$@"
echo "end $(date -Is) rc=$?"
