#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=170G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# usage: sbatch [opts] run_ce_wc.sbatch "L-list" SCHEMES TAG [extra ce_run.py options]
# exact multi-modular runs of the residual_log copy of complete_exact (ce_wc/: scheme Wc = outer-referenced aux windows)
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/ce_wc
mkdir -p out
PY=~/indep2d_c4/venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
LS=$1; SCH=$2; TAG=$3; shift 3
NP=${PROCS:-${SLURM_CPUS_ON_NODE:-$(nproc)}}
echo "host $(hostname) start $(date) job ${SLURM_JOB_ID:-none} L='$LS' schemes=$SCH tag=$TAG extra='$*' procs=$NP"
sha1sum *.py | sed 's/^/# /'
for L in $LS; do
  echo "=== L=$L $(date)"
  /usr/bin/time -v $PY ce_run.py --L $L --schemes $SCH --procs $NP --out out/${TAG}_L${L}.json "$@" \
      2> $W/logs/time_ce_${TAG}_L${L}.txt | grep -vE "primes done"
  grep -E "Maximum resident|Elapsed|Exit status" $W/logs/time_ce_${TAG}_L${L}.txt
done
echo "end $(date)"
