#!/bin/bash
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=170G
#SBATCH --time=00:59:00
#SBATCH --output=/mnt/beegfs/zzheng1/indep2d/residual_log/logs/%x_%j.out
# usage: sbatch [opts] run_ce_wcs4.sbatch "L:delta3:delta4 ..." TAG   (diagnostic scheme Wcs4, README Sec. 11.5)
set -uo pipefail
W=/mnt/beegfs/zzheng1/indep2d/residual_log
cd $W/ce_wc
mkdir -p out
PY=~/indep2d_c4/venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
LD=$1; TAG=$2; shift 2
NP=${PROCS:-${SLURM_CPUS_ON_NODE:-$(nproc)}}
echo "host $(hostname) start $(date) job ${SLURM_JOB_ID:-none} tag=$TAG procs=$NP"
sha1sum *.py | sed 's/^/# /'
for run in $LD; do
  IFS=: read L D3 D4 <<< "$run"
  echo "=== L=$L $(date)"
  /usr/bin/time -v $PY ce_run.py --L $L --schemes Wcs4 --delta3=$D3 --delta4=$D4 --desc odd:1-3,even:1-2 --procs $NP \
      --out out/${TAG}_L${L}.json "$@" 2> $W/logs/time_ce_${TAG}_L${L}.txt | grep -vE "primes done"
  grep -E "Maximum resident|Elapsed|Exit status" $W/logs/time_ce_${TAG}_L${L}.txt
done
echo "end $(date)"
