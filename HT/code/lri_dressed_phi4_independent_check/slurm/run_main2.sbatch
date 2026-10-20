#!/bin/bash
#SBATCH -p amdq,defq
#SBATCH -N 1 --exclusive
#SBATCH -t 12:00:00
#SBATCH --mem=180G
#SBATCH -J indep-ht-main2
#SBATCH -o <SCRATCH>/lri_dressed/independent_check/logs/%x_%j.out
# Resume of indep-ht-main with code v2: remaining chain points (delta<=0.011 raw,
# <=0.0225 consistent) and the unfinished N=16/20 points. Finished points are skipped
# (the driver reloads its results file). Threads sized from the physical cores.
set -u
BASE=<SCRATCH>/lri_dressed/independent_check
PY=<HOME>/lri_dressed/venv/bin/python
CODE=$BASE/code; TASKS=$BASE/tasks; RES=$BASE/results; LOGS=$BASE/logs
cd $BASE
phys_alloc() {
  local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" '
    BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}}
    ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'
}
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-1}
BUDGET=$(( PA < CAP ? PA : CAP ))
SMALL="chain_raw_N12 chain_consistent_N12"
BIG="hiN_raw_d0p2 hiN_raw_d0p05 hiN_raw_d0p025 hiN_raw_d0p01 hiN_consistent_d0p1 hiN_consistent_d0p05 hiN_consistent_d0p025 hiN_consistent_d0p01"
NB=$(echo $BIG | wc -w); NS=$(echo $SMALL | wc -w)
T=$(( (BUDGET - NS) / NB ))
(( T >= 1 )) || { echo "refusing: budget $BUDGET too small"; exit 64; }
echo "job $SLURM_JOB_ID host $(hostname) partition $SLURM_JOB_PARTITION phys_alloc=$PA cpus=$CAP budget=$BUDGET threads/big=$T start $(date)"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 $PY $CODE/tests/test_indep_ht.py > $LOGS/unit_tests_${SLURM_JOB_ID}.log 2>&1
echo "unit tests exit $? ($(tail -1 $LOGS/unit_tests_${SLURM_JOB_ID}.log))"
run() { local name=$1 th=$2
  OPENBLAS_NUM_THREADS=$th OMP_NUM_THREADS=$th MKL_NUM_THREADS=$th \
    $PY $CODE/indep_ht.py --task $TASKS/$name.json --out $RES/$name.json --log $LOGS/$name.log >> $LOGS/$name.stdout 2>&1 &
  echo "launched $name threads=$th pid $!"; }
for n in $SMALL; do run $n 1; done
for n in $BIG; do run $n $T; done
wait
echo "all done $(date)"
