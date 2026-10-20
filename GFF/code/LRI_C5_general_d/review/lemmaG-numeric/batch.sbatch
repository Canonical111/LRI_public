#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15000M
#SBATCH -t 04:00:00
#SBATCH -o <SCRATCH>/c5_gend/lemmaG/logs/%x_%j.out
# usage: sbatch -J name batch.sbatch listfile   (one run_case.py argument line per row; '#' comments)
source /etc/profile.d/modules.sh
module load python/3.11
cd <SCRATCH>/c5_gend/lemmaG/code
echo "host $(hostname) start $(date)"
while read -r line; do
  [[ -z "$line" || "$line" == \#* ]] && continue
  echo "=== $line  $(date +%T)"
  ~/c5d2/venv/bin/python run_case.py $line --np 8 --outdir ../results
done < "$1"
echo "done $(date)"
