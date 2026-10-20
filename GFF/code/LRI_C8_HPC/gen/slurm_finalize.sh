#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=8G -t 01:00:00
#SBATCH -J c8gen_fin -o /expanse/lustre/scratch/zzheng8/temp_project/c8_hpc/gen_work/logs/%x_%j.out
# Stage 4: assemble the complete L=1..8 inventory in out8 and run the consistency checks.
module purge; module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0
set -eo pipefail
W=/expanse/lustre/scratch/zzheng8/temp_project/c8_hpc/gen_work; cd "$W"; PY=$W/venv/bin/python
for L in 1 2 3 4 5 6 7; do cp -p reg/L${L}_coord.txt reg/L${L}_coord.txt.idx reg/L${L}_inventory.txt reg/L${L}_summary.json out8/; done
$PY src/crosscheck_L8.py out8 ref/inputs ref/verification 8 # set -e: a failed cross-check fails the job
$PY src/zero_dim_check.py out8 8
cd out8 && sha256sum classes*.txt L*_coord.txt L*_coord.txt.idx L*_inventory.txt L8_summary.json exact_zero_L*.txt articulation.json forest_polynomials.json forest_polynomials.json.zero.json forest_subsets.json forest_exact_checks_N8.json > SHA256SUMS_gen && wc -l SHA256SUMS_gen
