#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-r3a-dev
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# R3a development check (not a gate) of a revised src/quadfast.hpp in the scratch copy R3A_DEV: the differential test
# (R3A_PAIRS per op, edges, --bench), its ASan+UBSan build, the injection self-test; then the gmp worker built from
# R3A_DEV with the Makefile's command and r3a_prof.py (run from the export R3A_PKG, whose bin/c8d2_gmp is the
# committed R3a and baseline/c8d2_gmp the Stage-3 baseline) on the first 32 tasks of heavy_free_L8 at 16 threads:
# integration seconds of the three executables, rows digests compared, perf symbol reports.
# Usage: R3A_DEV=<dir> R3A_PKG=<export> [R3A_PAIRS=N] sbatch --export=ALL r3a_dev2.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"; : "${R3A_DEV:?}" "${R3A_PKG:?}"; PAIRS=${R3A_PAIRS:-268435456}
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); dev $R3A_DEV; package $R3A_PKG"
cd "$R3A_DEV"; mkdir -p out bin; status=0
F="-O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math"
g++ $F tests/quad_differential.cpp -o bin/qd || exit 3
g++ -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=all -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math tests/quad_differential.cpp -o bin/qd_san || exit 3
g++ $F -DC8_USE_GMP src/c8d2_integrate.cpp -lquadmath -lgmp -o bin/c8d2_gmp & pw=$!
t0=$(date +%s); ./bin/qd --pairs "$PAIRS" --threads 16 --bench > out/qd.json || status=$?
echo "qd exit $status in $(( $(date +%s) - t0 )) s"; python3 -c "
import json;d=json.load(open('out/qd.json'))
print({op:(v['pairs'],v['fast'],v['mismatches'])for op,v in d['random'].items()});print({op:(v['pairs'],v['fast'],v['mismatches'])for op,v in d['edges'].items()})
print(d.get('bench'));print(d['first_mismatches'][:4])"
./bin/qd_san --pairs 4194304 --threads 16 > out/qd_san.json 2> out/qd_san.stderr; s=$?; echo "qd_san exit $s"; tail -3 out/qd_san.stderr; [ $s -eq 0 ] || status=$s
python3 -c "
import json;d=json.load(open('out/qd_san.json'));print('san',{op:(v['pairs'],v['mismatches'])for op,v in d['random'].items()},{op:(v['pairs'],v['mismatches'])for op,v in d['edges'].items()})"
./bin/qd --pairs 4194304 --threads 16 --inject 4099 --no-edges > out/qd_inject.json; python3 -c "
import json;d=json.load(open('out/qd_inject.json'));print('inject',{op:v['mismatches']for op,v in d['random'].items()})"
wait $pw || exit 4; sha256sum bin/c8d2_gmp
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || L=${TMPDIR:-/tmp}
cd "$R3A_PKG"; rm -rf "$R3A_DEV/out/prof"
python3 -B "$R3A_DEV/scripts/r3a_prof.py" --exe baseline=baseline/c8d2_gmp --exe r3a=bin/c8d2_gmp --exe r3a_v2="$R3A_DEV/bin/c8d2_gmp" --output "$R3A_DEV/out/prof" --scratch "$L" --threads 16 --tasks 32 || status=$?
echo "finished $(date -Is), status $status"; exit $status
