#!/bin/bash
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=%x-%j.out
# usage: sbatch -J NAME runlist.slurm LISTFILE   (each line: script args..., run with the venv python, 64 workers given in the line)
cd $HOME/kgen_refcheck
echo "host $(hostname) start $(date -Is) list $1"
while read -r line; do
  [ -z "$line" ] && continue
  echo ">>> $line  $(date -Is)"
  OPENBLAS_NUM_THREADS=1 ./venv/bin/python -u $line
done < "$1"
echo "end $(date -Is)"
