#!/bin/bash
# One production item of the d = 1 frozen-cutoff HT solver (HT_Pert/code/lri_hpc_Hamitonian), generic Slurm template.
# Fill the placeholders; submit from HT_Pert/code/lri_hpc_Hamitonian:
#   sbatch --export=ALL,TASK=thermal,DEGREE=7,CUTOFF=60 public/slurm/item.sbatch
# Peak RSS and solver time of the production records (AMD EPYC 7742, 48-64 threads; field ranks[0].maxrss_kib):
#   thermal d7: Lambda 52 1.6 GiB 7 s; 60 4.4 GiB 17 s; 72 18 GiB 56 s; 80 44 GiB 133 s; 88 99 GiB 242 s;
#               94 175 GiB 403 s; 100 303 GiB 666 s; 108 605 GiB 22 min; 112 971 GiB 37 min; 118 1573 GiB 73 min
#   phi6 d5: Lambda 122 176 GiB, 160 1466 GiB 63 min;  phi6 d3: Lambda 480 140 GiB, 832 1454 GiB 47 min
# The production campaign used cluster/expanse/ (lanes with claims, gates and accounting; README of the package).
#SBATCH --job-name=lri-hpc-item
#SBATCH --partition=<PARTITION>
#SBATCH --account=<ACCOUNT>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=<CORES>
#SBATCH --mem=<MEMORY>
#SBATCH --time=<WALLTIME>
#SBATCH --output=<SCRATCH>/lri_hpc/logs/item-%j.out
set -euo pipefail
: "${TASK:?thermal or phi6}" "${DEGREE:?7 (thermal), 5 or 3 (phi6)}" "${CUTOFF:?even cutoff}"
OUT=${OUT:-<SCRATCH>/lri_hpc/results}
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export NUMBA_CACHE_DIR=${SLURM_TMPDIR:-/tmp}/numba-$SLURM_JOB_ID
python -m lri_hpc --task "$TASK" --degree "$DEGREE" --cutoffs "$CUTOFF" --threads "$SLURM_CPUS_PER_TASK" \
    --output-dir "$OUT/${TASK}_d${DEGREE}" --resume
# Compare with the shipped record (gates and 1e-7 + 2e-11 |rec|): see public/smoke_hpcham.py.
