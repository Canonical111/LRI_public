#!/bin/bash
# test, replay and smoke of HT_Pert/code/lri_hpc_Hamitonian and code/lri_eh_hpc on one node (generic Slurm template).
# Submit from HT_Pert/code/lri_hpc_Hamitonian:  sbatch public/slurm/acceptance.sbatch
# Measured on symmetry (Xeon Gold 6148, AMD EPYC 7532): about 5 min in all; replay-full adds 12 + 30 min.
#SBATCH --job-name=lri-hpc-accept
#SBATCH --partition=<PARTITION>
#SBATCH --account=<ACCOUNT>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=<SCRATCH>/lri_hpc/logs/accept-%j.out
set -u
PY=${PY:-python3}
rc=0
for t in test replay smoke; do make -C ../lri_eh_hpc -f public.mk $t PY=$PY THREADS=4 || rc=1; done
for t in test replay smoke; do make -f public.mk $t PY=$PY THREADS=4 || rc=1; done
exit $rc
