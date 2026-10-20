#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-r3a-dev
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# R3a development check (not a gate): in a scratch copy R3A_DEV of the working tree's src/ and tests/quad_*.cpp,
# (1) the differential test at the worker's flags on a small sample (--pairs per op) with --bench, and the same under
# ASan+UBSan; (2) the worker's translation unit (both backends) compiled to assembly from the baseline
# source (the 4a export) and from R3A_DEV and compared function by function (asm_compare.py): the MP and worker code
# must be identical.
# Usage: R3A_DEV=<dir> [R3A_PAIRS=N] sbatch --export=ALL r3a_dev.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${R3A_DEV:?}"; PAIRS=${R3A_PAIRS:-67108864}
BASE=$C8_DATA/pkg/c17688158e2b/bin
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); dev $R3A_DEV"; lscpu | grep 'Model name'; g++ --version | head -1
cd "$R3A_DEV"; mkdir -p out bin; status=0
F="-O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math"
t0=$(date +%s)
g++ $F tests/quad_differential.cpp -o bin/qd || exit 3
g++ -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=all -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math tests/quad_differential.cpp -o bin/qd_san || exit 3
echo "differential builds in $(( $(date +%s) - t0 )) s"
t0=$(date +%s); ./bin/qd --pairs "$PAIRS" --threads 16 --bench > out/qd.json || status=$?
echo "qd exit $status in $(( $(date +%s) - t0 )) s"; python3 -c "
import json;d=json.load(open('out/qd.json'))
print({op:(v['pairs'],v['fast'],v['mismatches'])for op,v in d['random'].items()});print({op:(v['pairs'],v['fast'],v['mismatches'])for op,v in d['edges'].items()})
print(d.get('bench'),d['random_seconds'],d['edge_seconds']);print(d['first_mismatches'][:4])"
t0=$(date +%s); ./bin/qd --pairs 1048576 --threads 16 > out/qd_san.json 2> out/qd_san.stderr; s=$?
echo "qd_san exit $s in $(( $(date +%s) - t0 )) s"; tail -3 out/qd_san.stderr; [ $s -eq 0 ] || status=$s
python3 -c "
import json;d=json.load(open('out/qd_san.json'))
print('san',{op:(v['pairs'],v['fast'],v['mismatches'])for op,v in d['random'].items()},{op:(v['pairs'],v['mismatches'])for op,v in d['edges'].items()})"
./bin/qd --pairs 4194304 --threads 16 --inject 4099 --no-edges > out/qd_inject.json; python3 -c "
import json;d=json.load(open('out/qd_inject.json'));print('inject',{op:v['mismatches']for op,v in d['random'].items()})"
t0=$(date +%s); BP=$C8_DATA/pkg/c17688158e2b
g++ $F -S "$BP/src/c8d2_integrate.cpp" -o out/base_decimal.s & q1=$!
g++ $F -DC8_USE_GMP -S "$BP/src/c8d2_integrate.cpp" -o out/base_gmp.s & q2=$!
g++ $F -S src/c8d2_integrate.cpp -o out/new_decimal.s & q3=$!
g++ $F -DC8_USE_GMP -S src/c8d2_integrate.cpp -o out/new_gmp.s & q4=$!
g++ $F -DC8_USE_GMP tests/quad_ranges.cpp -lquadmath -lgmp -o bin/c8d2_quad_ranges & q5=$!
for q in $q1 $q2 $q3 $q4 $q5; do wait $q || status=4; done
echo "assembly builds in $(( $(date +%s) - t0 )) s"
for b in gmp decimal; do python3 scripts/asm_compare.py out/base_$b.s out/new_$b.s --output out/asm_$b.json | head -60; done
echo "finished $(date -Is), status $status"; exit $status
