#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=32G -t 06:00:00
#SBATCH -J c8gen_for8 -o /expanse/lustre/scratch/zzheng8/temp_project/c8_hpc/gen_work/logs/%x_%j.out
# Stage 3: L=8 coordinate forests, index, articulation list; then forest_audit through L=8 with the
# subset sums, the exact-zero lists and the exact Lagrange-inversion certificate through N=8.
module purge; module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0
set -eo pipefail
W=/expanse/lustre/scratch/zzheng8/temp_project/c8_hpc/gen_work; cd "$W"; PY=$W/venv/bin/python
hostname; date
for L in 1 2 3 4 5 6 7; do cp -p reg/classes$L.txt out8/; done
/usr/bin/time -f "forests L=8 wall %e s maxrss %M KB" bin/build_coordinate_forests out8/classes8.txt out8/L8 2> out8/build_L8.err; tail -2 out8/build_L8.err; cat out8/L8_summary.json
$PY src/index_coord.py out8/L8_coord.txt
$PY src/check_articulation.py out8 2 8 out8/articulation.json
/usr/bin/time -f "forest_audit Lmax=8 wall %e s maxrss %M KB" bin/forest_audit out8 out8/forest_polynomials.json 8 out8/forest_subsets.json 2> out8/audit_L8.err; grep -E "subset|completed|wall" out8/audit_L8.err
$PY src/make_zero_txt.py out8/forest_polynomials.json.zero.json out8 5 6 7 8
for L in 5 6 7; do cmp out8/exact_zero_L$L.txt ref/inputs/exact_zero_L$L.txt && echo "exact_zero_L$L identical to reference"; done
/usr/bin/time -f "check_forest_exact N=8 wall %e s maxrss %M KB" $PY src/check_forest_exact.py out8/forest_polynomials.json 8 out8/forest_exact_checks_N8.json
date
