#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 24:00:00
#SBATCH --mem=240G
#SBATCH -J indep-ht-main
#SBATCH -o <SCRATCH>/lri_dressed/independent_check/logs/%x_%j.out
# Independent HT check: N=12 continuation chains, weak-coupling chains, and
# N=16 -> 20 at the target deltas (these wait for the N=12 chain records).
# One process per task; threads sized so that all processes fit the physical cores.
set -u
BASE=<SCRATCH>/lri_dressed/independent_check
PY=<HOME>/lri_dressed/venv/bin/python
CODE=$BASE/code
TASKS=$BASE/tasks
RES=$BASE/results
LOGS=$BASE/logs
mkdir -p $RES $LOGS
cd $BASE

phys_alloc() {
  local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" '
    BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}}
    ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'
}
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-1}
BUDGET=$(( PA < CAP ? PA : CAP ))
echo "job $SLURM_JOB_ID host $(hostname) phys_alloc=$PA cpus_on_node=$CAP budget=$BUDGET start $(date)"

# task list: name threads
LIST=$(cat <<'EOT'
chain_raw_N12 1
chain_consistent_N12 1
chain_literal_N12 1
weak_raw_N0 1
weak_raw_N2 1
weak_raw_N4 1
weak_raw_N8 1
weak_consistent_N0 1
weak_consistent_N2 1
weak_consistent_N4 1
weak_consistent_N8 1
weak_raw_N16 2
weak_consistent_N16 2
hiN_raw_d0p249 4
hiN_raw_d0p2 4
hiN_raw_d0p1 4
hiN_raw_d0p05 4
hiN_raw_d0p025 4
hiN_raw_d0p01 4
hiN_consistent_d0p249 4
hiN_consistent_d0p2 4
hiN_consistent_d0p1 4
hiN_consistent_d0p05 4
hiN_consistent_d0p025 4
hiN_consistent_d0p01 4
EOT
)
NEED=$(echo "$LIST" | awk '{s+=$2} END{print s}')
if (( NEED > BUDGET )); then echo "refusing: need $NEED threads > $BUDGET physical cores"; exit 64; fi
echo "threads needed $NEED of $BUDGET"

# unit tests first (seconds)
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 $PY $CODE/tests/test_indep_ht.py > $LOGS/unit_tests_${SLURM_JOB_ID}.log 2>&1
echo "unit tests exit $? ($(tail -1 $LOGS/unit_tests_${SLURM_JOB_ID}.log))"

while read -r name th; do
  [[ -z "$name" ]] && continue
  OPENBLAS_NUM_THREADS=$th OMP_NUM_THREADS=$th MKL_NUM_THREADS=$th \
    $PY $CODE/indep_ht.py --task $TASKS/$name.json --out $RES/$name.json --log $LOGS/$name.log \
    > $LOGS/$name.stdout 2>&1 &
  echo "launched $name threads=$th pid $!"
done <<< "$LIST"
wait
echo "all done $(date)"
