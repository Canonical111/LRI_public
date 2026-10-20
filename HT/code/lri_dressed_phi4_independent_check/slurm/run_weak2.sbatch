#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 02:00:00
#SBATCH --mem=200G
#SBATCH -J indep-ht-weak2
#SBATCH -o <SCRATCH>/lri_dressed/independent_check/logs/%x_%j.out
# Extended weak-coupling scan (15 deltas, N=0..16, raw+consistent) for the C2 fit.
set -u
BASE=<SCRATCH>/lri_dressed/independent_check
PY=<HOME>/lri_dressed/venv/bin/python
cd $BASE
echo "job $SLURM_JOB_ID host $(hostname) start $(date)"
for presc in raw consistent; do
  for N in 0 2 4 8 12 16; do
    th=1; [[ $N -ge 12 ]] && th=4
    name=weak2_${presc}_N${N}
    OPENBLAS_NUM_THREADS=$th OMP_NUM_THREADS=$th MKL_NUM_THREADS=$th \
      $PY $BASE/code/indep_ht.py --task $BASE/tasks/$name.json --out $BASE/results/$name.json --log $BASE/logs/$name.log \
      > $BASE/logs/$name.stdout 2>&1 &
    echo "launched $name threads=$th"
  done
done
wait
echo "all done $(date)"
