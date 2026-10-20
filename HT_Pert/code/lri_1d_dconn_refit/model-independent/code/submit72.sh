#!/bin/bash
# refit72: stage code + data on symmetry and submit the two list jobs (main + members, quantile reruns).
# usage: bash submit72.sh PARTITIONS   (e.g. amdq,defq)
set -eo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
B=$(cd $HERE/../.. && pwd)                       # .../dconn_refit72
ARCH=<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit/delta/out
R=<SCRATCH>/dconn_refit72_mi
PART=${1:-amdq,defq}
ssh symmetry "mkdir -p $R/{code,data,out,logs,delta_code}"
scp -q $HERE/{common.py,grid.py,accel.py,members_full.py,members_prop.py,run_list72.sbatch,runlist72_main.txt,runlist72_q.txt} symmetry:$R/code/
scp -q $B/delta/code/{ensemble.py,fitlib.py} symmetry:$R/delta_code/
scp -q $B/delta/out/delta_v1_hi72_corrected.json symmetry:$R/data/corrected.json
scp -q $B/delta/out/delta_v1_hi72_variants.json symmetry:$R/data/variants.json
scp -q $B/delta/out/delta_v1_hi72_floormean_corrected.json symmetry:$R/data/floormean.json
scp -q $B/delta/out/delta_v1_hi72_floormean_s46_corrected.json symmetry:$R/data/floormean_s46.json
scp -q $ARCH/delta_v1_corrected.json symmetry:$R/data/arch_corrected.json
scp -q $ARCH/delta_v1_variants.json symmetry:$R/data/arch_variants.json
scp -q <PROJECT>/lri_ht_c8_symmetry/results/2026-10_symmetry/extrapolation/data.json symmetry:$R/data/ht_data.json
ssh symmetry "cd $R/code && sha256sum ../data/*.json *.py ../delta_code/*.py > $R/logs/staged_sha256.txt && \
  export PATH=/cm/shared/apps/slurm/current/bin:\$PATH && \
  sbatch --parsable -p $PART -t 00:55:00 -J mi72-main -o $R/logs/%x_%j.out --export=ALL,W=$R,MI_MEMBERS=mem1 run_list72.sbatch $R/code/runlist72_main.txt && \
  sbatch --parsable -p $PART -t 00:55:00 -J mi72-q -o $R/logs/%x_%j.out --export=ALL,W=$R run_list72.sbatch $R/code/runlist72_q.txt"
