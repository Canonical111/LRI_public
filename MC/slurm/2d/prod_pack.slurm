#!/bin/bash
#SBATCH -J lri2d_pack
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=48G
#SBATCH -t 08:00:00
#SBATCH -o <SCRATCH>/lri2d/logs/prod_pack_%j.out
# FIT_MODEL_2D §4.1/§5.2: pack every DONE chain of prod2d at b = 2000 (primary), 1000 and 4000 (reblocking). Gate: all 2400 chains DONE.
set -uo pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd <CODE_2D>/code || exit 1
CAMP=<SCRATCH>/lri2d/prod2d; LOGS=<SCRATCH>/lri2d/logs
N=$(find $CAMP/chains -maxdepth 2 -name DONE.json | wc -l); echo "$(date) DONE chains $N/2400"
[ "$N" -eq 2400 ] || { echo "gate: not every chain is DONE; nothing packed; exit 64"; exit 64; }
for b in 2000 1000 4000; do
  if [ -e $CAMP/hist_b$b ]; then echo "hist_b$b already exists (immutable record); not repacking"; continue; fi
  python3 pack_histograms.py $CAMP --block $b > $LOGS/prod_pack_b$b.log 2>&1; echo "pack b=$b exit $? ($(date))"
done
for b in 2000 1000 4000; do [ -s $CAMP/hist_b$b/index.json ] || { echo "missing $CAMP/hist_b$b/index.json; exit 65"; exit 65; }; done
echo "$(date) PACK DONE"; ls -la $CAMP/hist_b2000/index.json
