#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=8G -t 02:00:00
#SBATCH -J c8gen_reg -o /expanse/lustre/scratch/zzheng8/temp_project/c8_hpc/gen_work/logs/%x_%j.out
# Stage 1: build the generalized programs and regenerate L=1..7 for the byte-for-byte regression.
module purge; module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0
set -eo pipefail
W=/expanse/lustre/scratch/zzheng8/temp_project/c8_hpc/gen_work; cd "$W"
PY=$W/venv/bin/python
mkdir -p bin reg
CXXFLAGS="-O3 -std=c++17"
g++ $CXXFLAGS src/enumerate_classes.cpp -o bin/enumerate_classes
g++ $CXXFLAGS src/build_coordinate_forests.cpp -o bin/build_coordinate_forests
g++ $CXXFLAGS -I"$BOOST_ROOT/include" src/forest_audit.cpp -o bin/forest_audit
g++ --version | head -1; echo "BOOST_ROOT=$BOOST_ROOT"; hostname; date
for L in 1 2 3 4 5 6 7; do
  /usr/bin/time -f "enumerate L=$L wall %e s maxrss %M KB" bin/enumerate_classes $((L+1)) reg/classes$L.txt 2> reg/enum_L$L.err; tail -2 reg/enum_L$L.err
done
for L in 1 2 3 4 5 6 7; do
  /usr/bin/time -f "forests L=$L wall %e s maxrss %M KB" bin/build_coordinate_forests reg/classes$L.txt reg/L$L 2> reg/build_L$L.err; tail -2 reg/build_L$L.err
done
/usr/bin/time -f "forest_audit Lmax=7 wall %e s maxrss %M KB" bin/forest_audit reg reg/forest_polynomials.json 7 reg/forest_subsets_L7.json 2> reg/audit_L7.err; tail -12 reg/audit_L7.err
$PY src/make_zero_txt.py reg/forest_polynomials.json.zero.json reg 5 6 7
$PY src/index_coord.py reg/L?_coord.txt
$PY src/check_articulation.py reg 2 7 reg/articulation.json
$PY src/compare_regression.py reg ref/inputs ref/verification 7 # set -e: a failed comparison fails the job
/usr/bin/time -f "check_forest_exact N=7 wall %e s maxrss %M KB" $PY src/check_forest_exact.py reg/forest_polynomials.json 7 reg/forest_exact_checks_N7.json
date
